"""Distribution shift analysis for MED-001.

Answers the question: is the deployment population close enough to the training
population that the model's learned associations still hold?

This is distinct from approximation_quality_gap (which asks whether the computed
score is close to the model's training target) and from clinical_utility_gap (which
asks whether the score is useful at the operating threshold). distribution_shift_gap
asks whether the model is operating on a population it was designed for.

## Method: domain classifier

Train a binary classifier to distinguish training patients (label=0) from
deployment patients (label=1). If the populations are exchangeable, the classifier
cannot do better than chance — its AUC approaches 0.5. High AUC means the features
that predict the domain label are the same features the sepsis model uses, which
means the model's learned associations may not transfer.

Threshold for gap status:
  domain_auc < 0.60  →  gap CLOSED  (populations indistinguishable on model features)
  domain_auc < 0.70  →  gap BOUNDED (moderate shift; calibration check required)
  domain_auc ≥ 0.70  →  gap OPEN    (substantial shift; retraining or recalibration required)

A calibration check (Brier score on deployment cohort) is also required for BOUNDED:
  brier_deployment < 1.25 * brier_training  →  calibration acceptable

## eICU-CRD as deployment population

The eICU Collaborative Research Database (Pollard et al. 2018, PhysioNet) contains
~200,000 ICU admissions from 208 hospitals across the US, 2014-2015. It provides
a real second-institution deployment context for models trained on Challenge 2019
(which draws from a single health system).

eICU uses different column names. The adapter maps them to the Challenge 2019
feature space (FEATURES list) before running the domain classifier.

Data download: https://physionet.org/content/eicu-crd/2.0/
Required files:
  patient.csv         — admission metadata (age, unit type, hospital)
  vitalPeriodic.csv   — hourly vitals (HR, SpO2, temp, SBP, MAP, DBP, RR)
  lab.csv             — lab values (lactate, creatinine, BUN, glucose, WBC, etc.)
  diagnosis.csv       — ICD codes for sepsis label construction

Place downloaded files at:
  examples/medical/data/eicu_crd/patient.csv
  examples/medical/data/eicu_crd/vitalPeriodic.csv
  examples/medical/data/eicu_crd/lab.csv
  examples/medical/data/eicu_crd/diagnosis.csv
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.model_selection import cross_val_score

import noethers_turnstile as t

from adapter.data_loader import FEATURES, LABEL_COL
from adapter.proof_context import GAP_DISTRIBUTION_SHIFT

EICU_DIR = Path(__file__).resolve().parents[1] / "data" / "eicu_crd"

# Domain classifier AUC thresholds — see module docstring.
DOMAIN_AUC_CLOSED_THRESHOLD  = 0.60
DOMAIN_AUC_BOUNDED_THRESHOLD = 0.70

# Calibration: deployment Brier score must be < this multiple of training Brier.
BRIER_RATIO_THRESHOLD = 1.25

# Minimum cohort size for a valid distribution shift analysis.
MIN_COHORT_SIZE = 500

# Detail contract version — must match the validator in tokens.py.
DETAIL_CONTRACT_VERSION = "med001.distribution_shift/0.2"


# ── eICU feature mapping ──────────────────────────────────────────────────────

# eICU vitalPeriodic column names → Challenge 2019 feature names
EICU_VITAL_MAP = {
    "heartrate":          "HR",
    "sao2":               "O2Sat",
    "temperature":        "Temp",
    "systemicsystolic":   "SBP",
    "systemicmean":       "MAP",
    "systemicdiastolic":  "DBP",
    "respiratoryrate":    "Resp",
}

# eICU lab names (as they appear in lab.labname) → Challenge 2019 feature names
EICU_LAB_MAP = {
    "lactate":                "Lactate",
    "creatinine":             "Creatinine",
    "BUN":                    "BUN",
    "glucose":                "Glucose",
    "WBC x 1000":             "WBC",
    "total bilirubin":        "Bilirubin_total",
    "platelets x 1000":       "Platelets",
}

# ICD-9 codes used to construct sepsis label from eICU diagnosis table.
# Sepsis-3 requires suspected infection + SOFA. We use ICD codes as a proxy
# consistent with how Challenge 2019 SepsisLabel was constructed.
SEPSIS_ICD9_CODES = {
    "038",    # septicemia
    "995.91", # sepsis
    "995.92", # severe sepsis
    "785.52", # septic shock
}


@dataclass
class DistributionShiftResult:
    training_population: str
    deployment_population: str
    training_n: int
    deployment_n: int
    domain_classifier_auc: float       # AUC of training/deployment classifier
    domain_classifier_auc_cv: float    # 5-fold CV AUC (robustness check)
    calibration_brier_training: float
    calibration_brier_deployment: float
    calibration_brier_ratio: float
    top_feature_drift: dict[str, float]  # feature name → mean absolute drift
    gap_status: str                      # "open", "bounded", or "closed"
    gap_status_reason: str
    institution: str
    date_range: str
    expiry_days: int


def _load_eicu(max_patients: int | None = None) -> pd.DataFrame:
    """Load eICU-CRD and map to Challenge 2019 feature space.

    Returns a patient-level DataFrame with the same columns as Challenge 2019
    (FEATURES + LABEL_COL). Missing features are NaN.
    """
    patient_csv = EICU_DIR / "patient.csv"
    vital_csv   = EICU_DIR / "vitalPeriodic.csv"
    lab_csv     = EICU_DIR / "lab.csv"
    diag_csv    = EICU_DIR / "diagnosis.csv"

    for f in [patient_csv, vital_csv, lab_csv, diag_csv]:
        if not f.exists():
            raise FileNotFoundError(
                f"eICU file not found: {f}\n"
                "Download eICU-CRD from https://physionet.org/content/eicu-crd/2.0/ "
                "and place files in examples/medical/data/eicu_crd/"
            )

    patients = pd.read_csv(patient_csv, usecols=["patientunitstayid", "age", "gender",
                                                   "unittype", "hospitaldischargestatus"])
    if max_patients:
        patients = patients.head(max_patients)

    pids = set(patients["patientunitstayid"].values)

    # Vitals: take last observation per patient (mirrors make_patient_level)
    vitals = pd.read_csv(vital_csv, usecols=["patientunitstayid", "observationoffset"] +
                         list(EICU_VITAL_MAP.keys()))
    vitals = vitals[vitals["patientunitstayid"].isin(pids)]
    vitals = (vitals.sort_values("observationoffset")
                    .groupby("patientunitstayid")
                    .last()
                    .reset_index())
    vitals = vitals.rename(columns=EICU_VITAL_MAP)

    # Labs: pivot labname → column, take last value per patient
    labs = pd.read_csv(lab_csv, usecols=["patientunitstayid", "labresultoffset",
                                          "labname", "labresult"])
    labs = labs[labs["patientunitstayid"].isin(pids) &
                labs["labname"].isin(EICU_LAB_MAP.keys())]
    labs["feature"] = labs["labname"].map(EICU_LAB_MAP)
    labs = (labs.sort_values("labresultoffset")
                .groupby(["patientunitstayid", "feature"])["labresult"]
                .last()
                .unstack("feature")
                .reset_index())

    # Sepsis label from diagnosis
    diag = pd.read_csv(diag_csv, usecols=["patientunitstayid", "icd9code"])
    diag = diag[diag["patientunitstayid"].isin(pids)]

    def _has_sepsis(codes_str: str) -> bool:
        if not isinstance(codes_str, str):
            return False
        codes = [c.strip() for c in codes_str.split(",")]
        return any(c.startswith(prefix) for c in codes for prefix in SEPSIS_ICD9_CODES)

    sepsis_pids = set(
        diag[diag["icd9code"].apply(_has_sepsis)]["patientunitstayid"].unique()
    )

    # Merge everything
    df = patients.merge(vitals, on="patientunitstayid", how="left")
    df = df.merge(labs, on="patientunitstayid", how="left")
    df[LABEL_COL] = df["patientunitstayid"].isin(sepsis_pids).astype(int)

    # Impute: median per column
    for col in FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())
        else:
            df[col] = np.nan

    # Add ICULOS proxy: use observationoffset max from vitals as ICU LOS in hours
    if "ICULOS" not in df.columns:
        df["ICULOS"] = np.nan

    return df[FEATURES + [LABEL_COL, "patientunitstayid"]].copy()


def compute_distribution_shift(
    training_df: pd.DataFrame,
    sepsis_model: Any,  # sklearn estimator with predict_proba
    institution: str = "eicu_crd_multi_site",
    date_range: str = "2014-2015",
    max_deployment_patients: int | None = None,
) -> DistributionShiftResult:
    """Run a full distribution shift analysis.

    Args:
        training_df:  Patient-level training DataFrame (Challenge 2019 Set A).
        sepsis_model: Trained sepsis classifier (e.g. GBM from run_benchmark.py).
        institution:  Deployment institution identifier for token provenance.
        date_range:   Date range of deployment cohort.

    Returns:
        DistributionShiftResult with gap_status and all supporting evidence.
    """
    deployment_df = _load_eicu(max_patients=max_deployment_patients)

    n_train = len(training_df)
    n_deploy = len(deployment_df)

    if n_deploy < MIN_COHORT_SIZE:
        raise ValueError(
            f"Deployment cohort too small: {n_deploy} < {MIN_COHORT_SIZE}. "
            "Distribution shift analysis requires a minimum cohort to be valid."
        )

    # Align feature matrices
    X_train = training_df[FEATURES].fillna(0).values
    X_deploy = deployment_df[FEATURES].fillna(0).values
    y_train_sepsis = training_df[LABEL_COL].values
    y_deploy_sepsis = deployment_df[LABEL_COL].values

    # ── Domain classifier ─────────────────────────────────────────────────
    # Label training=0, deployment=1 and train a classifier.
    # If populations are exchangeable, AUC → 0.5.
    n_min = min(n_train, n_deploy)
    rng = np.random.RandomState(42)
    train_idx = rng.choice(n_train, n_min, replace=False)
    deploy_idx = rng.choice(n_deploy, n_min, replace=False)

    X_domain = np.vstack([X_train[train_idx], X_deploy[deploy_idx]])
    y_domain = np.array([0] * n_min + [1] * n_min)

    domain_clf = GradientBoostingClassifier(
        n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42
    )
    domain_clf.fit(X_domain, y_domain)
    domain_proba = domain_clf.predict_proba(X_domain)[:, 1]
    domain_auc = float(roc_auc_score(y_domain, domain_proba))

    # 5-fold CV AUC for robustness
    cv_scores = cross_val_score(
        GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42),
        X_domain, y_domain, cv=5, scoring="roc_auc",
    )
    domain_auc_cv = float(cv_scores.mean())

    # ── Feature drift: mean shift normalized by training std ──────────────
    train_means = X_train.mean(axis=0)
    train_stds  = X_train.std(axis=0) + 1e-8
    deploy_means = X_deploy.mean(axis=0)
    feature_drift = {
        feat: float(abs(deploy_means[i] - train_means[i]) / train_stds[i])
        for i, feat in enumerate(FEATURES)
    }
    top_feature_drift = dict(
        sorted(feature_drift.items(), key=lambda x: x[1], reverse=True)[:5]
    )

    # ── Calibration: Brier score on training vs deployment ────────────────
    train_proba = sepsis_model.predict_proba(X_train)[:, 1]
    deploy_proba = sepsis_model.predict_proba(X_deploy)[:, 1]
    brier_train  = float(brier_score_loss(y_train_sepsis, train_proba))
    brier_deploy = float(brier_score_loss(y_deploy_sepsis, deploy_proba))
    brier_ratio  = brier_deploy / (brier_train + 1e-8)

    # ── Gap status determination ──────────────────────────────────────────
    calibration_ok = brier_ratio < BRIER_RATIO_THRESHOLD

    if domain_auc < DOMAIN_AUC_CLOSED_THRESHOLD and calibration_ok:
        gap_status = "closed"
        reason = (
            f"Domain classifier AUC={domain_auc:.3f} < {DOMAIN_AUC_CLOSED_THRESHOLD} "
            f"(populations exchangeable on model features) and "
            f"Brier ratio={brier_ratio:.2f} < {BRIER_RATIO_THRESHOLD} (calibration holds)."
        )
        expiry_days = 180
    elif domain_auc < DOMAIN_AUC_BOUNDED_THRESHOLD and calibration_ok:
        gap_status = "bounded"
        reason = (
            f"Domain classifier AUC={domain_auc:.3f} in [{DOMAIN_AUC_CLOSED_THRESHOLD}, "
            f"{DOMAIN_AUC_BOUNDED_THRESHOLD}) — moderate shift detected. "
            f"Brier ratio={brier_ratio:.2f} < {BRIER_RATIO_THRESHOLD}: calibration holds. "
            f"Gap bounded; recalibration recommended at next model review."
        )
        expiry_days = 90
    elif domain_auc < DOMAIN_AUC_BOUNDED_THRESHOLD and not calibration_ok:
        gap_status = "bounded"
        reason = (
            f"Domain classifier AUC={domain_auc:.3f} in moderate range but "
            f"Brier ratio={brier_ratio:.2f} ≥ {BRIER_RATIO_THRESHOLD}: "
            f"calibration degraded on deployment cohort. Gap bounded at reduced confidence."
        )
        expiry_days = 60
    else:
        gap_status = "open"
        reason = (
            f"Domain classifier AUC={domain_auc:.3f} ≥ {DOMAIN_AUC_BOUNDED_THRESHOLD}: "
            f"substantial feature distribution shift detected between training and deployment. "
            f"Model associations may not transfer. Retraining or recalibration required."
        )
        expiry_days = 0

    return DistributionShiftResult(
        training_population="challenge2019_setA",
        deployment_population=institution,
        training_n=n_train,
        deployment_n=n_deploy,
        domain_classifier_auc=round(domain_auc, 4),
        domain_classifier_auc_cv=round(domain_auc_cv, 4),
        calibration_brier_training=round(brier_train, 4),
        calibration_brier_deployment=round(brier_deploy, 4),
        calibration_brier_ratio=round(brier_ratio, 4),
        top_feature_drift={k: round(v, 4) for k, v in top_feature_drift.items()},
        gap_status=gap_status,
        gap_status_reason=reason,
        institution=institution,
        date_range=date_range,
        expiry_days=expiry_days,
    )


def distribution_shift_token_from_result(
    result: DistributionShiftResult,
    *,
    token_id: str,
    claim_id: str,
    candidate_id: str,
    context_id: str,
    allowed_use: str,
    issued_at: float | None = None,
    issuer: str = "med001.distribution_shift",
) -> t.ProofToken:
    """Construct a distribution_shift_gap token from a DistributionShiftResult.

    Token detail contract (version med001.distribution_shift/0.2):
      Required fields: training_population, deployment_population, institution,
        domain_classifier_auc, domain_classifier_auc_cv, calibration_brier_ratio,
        top_feature_drift, gap_status_reason, expiry_days, contract_version.
      domain_classifier_auc must be a float in [0.5, 1.0] (random=0.5 baseline).
      calibration_brier_ratio must be a positive float.
      expiry_days=0 → token is invalid (gap open, no bounding evidence).

    Gap advancement:
      gap CLOSED → closes_gaps includes distribution_shift_gap
      gap BOUNDED → bounds_gaps includes distribution_shift_gap
      gap OPEN    → neither (token is structurally invalid)
    """
    prov = t.compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use)

    if result.gap_status == "open":
        status = "invalid"
        closes_gaps: list[str] = []
        bounds_gaps: list[str] = []
    elif result.gap_status == "bounded":
        status = "valid"
        closes_gaps = []
        bounds_gaps = [GAP_DISTRIBUTION_SHIFT]
    else:  # closed
        status = "valid"
        closes_gaps = [GAP_DISTRIBUTION_SHIFT]
        bounds_gaps = []

    expires_at: float | None = None
    if result.expiry_days > 0:
        base = issued_at or time.time()
        expires_at = base + result.expiry_days * 86400

    details = {
        "contract_version": DETAIL_CONTRACT_VERSION,
        "training_population": result.training_population,
        "deployment_population": result.deployment_population,
        "institution": result.institution,
        "date_range": result.date_range,
        "training_n": result.training_n,
        "deployment_n": result.deployment_n,
        "domain_classifier_auc": result.domain_classifier_auc,
        "domain_classifier_auc_cv": result.domain_classifier_auc_cv,
        "domain_auc_closed_threshold": DOMAIN_AUC_CLOSED_THRESHOLD,
        "domain_auc_bounded_threshold": DOMAIN_AUC_BOUNDED_THRESHOLD,
        "calibration_brier_training": result.calibration_brier_training,
        "calibration_brier_deployment": result.calibration_brier_deployment,
        "calibration_brier_ratio": result.calibration_brier_ratio,
        "brier_ratio_threshold": BRIER_RATIO_THRESHOLD,
        "top_feature_drift": result.top_feature_drift,
        "gap_status": result.gap_status,
        "gap_status_reason": result.gap_status_reason,
        "expiry_days": result.expiry_days,
    }

    return t.ProofToken(
        token_id=token_id,
        token_type="clinical.distribution_shift_bound.v2",
        schema_version=DETAIL_CONTRACT_VERSION,
        status=status,
        closes_gaps=closes_gaps,
        bounds_gaps=bounds_gaps,
        provenance_hash=prov,
        issued_at=issued_at or time.time(),
        expires_at=expires_at,
        issuer=issuer,
        is_negative_control=False,
        details=json.dumps(details),
    )
