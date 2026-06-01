"""Model fixtures for MED-001.

Each model returns a metrics dict suitable for populating token payloads.
Models A, B, E are rule-based (no training). Model C is a GBM stub with
hardcoded expected metrics. Model D is paper-input only (Wong et al. 2021).

Real training (Model C) and empirical pre-conditions (Models B, E for the
8-cell independence table) are handled separately; these fixtures provide
the values used in oracle and adversarial test cases.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelMetrics:
    model_id: str
    dataset_id: str
    threshold: float
    auc_roc: float
    auc_pr: float
    brier_score: float
    sensitivity: float
    specificity: float
    ppv: float
    npv: float
    # Specification metadata
    training_target: str
    action_target: str
    adequacy_argument: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "dataset_id": self.dataset_id,
            "threshold": self.threshold,
            "auc_roc": self.auc_roc,
            "auc_pr": self.auc_pr,
            "brier_score": self.brier_score,
            "sensitivity": self.sensitivity,
            "specificity": self.specificity,
            "ppv": self.ppv,
            "npv": self.npv,
        }


# ── Model A: Sepsis-3 SOFA Criteria ───────────────────────────────────────────
# Rule-based. SOFA score >= 2 from baseline plus suspected infection.
# Near-ideal specification; expected to reach ALR under both profiles.
# Metrics represent strong clinical performance on Challenge 2019 Set A.
MODEL_A_SETA = ModelMetrics(
    model_id="sofa_sepsis3",
    dataset_id="challenge2019_setA",
    threshold=2.0,  # SOFA threshold (integer score)
    auc_roc=0.82,
    auc_pr=0.74,
    brier_score=0.08,
    sensitivity=0.78,
    specificity=0.85,
    ppv=0.52,
    npv=0.95,
    training_target="Sepsis-3 SOFA >= 2 from baseline plus suspected infection (Singer et al. 2016)",
    action_target="ICU sepsis early-warning alert for nurse notification and rapid response",
    adequacy_argument="SOFA is the Sepsis-3 reference standard; target variable is the clinical definition itself",
)

MODEL_A_EICU = ModelMetrics(
    model_id="sofa_sepsis3",
    dataset_id="eicu_crd",
    threshold=2.0,
    auc_roc=0.79,
    auc_pr=0.68,
    brier_score=0.10,
    sensitivity=0.73,
    specificity=0.82,
    ppv=0.44,
    npv=0.94,
    training_target="Sepsis-3 SOFA >= 2 from baseline plus suspected infection (Singer et al. 2016)",
    action_target="ICU sepsis early-warning alert for nurse notification and rapid response",
    adequacy_argument="SOFA is the Sepsis-3 reference standard; target variable is the clinical definition itself",
)


# ── Model B: qSOFA ─────────────────────────────────────────────────────────────
# Rule-based. RR>=22 OR altered mentation OR SBP<=100 (2 of 3 criteria).
# Intended for pre-ICU screening; model_specification_gap is OPEN in ICU context.
MODEL_B_SETA_ICU = ModelMetrics(
    model_id="qsofa",
    dataset_id="challenge2019_setA_icu",
    threshold=2.0,  # qSOFA score threshold
    auc_roc=0.68,
    auc_pr=0.55,
    brier_score=0.14,
    sensitivity=0.61,
    specificity=0.74,
    ppv=0.32,
    npv=0.90,
    training_target="qSOFA: RR>=22, altered mentation, SBP<=100 (2 of 3)",
    action_target="ICU sepsis early-warning alert",
    adequacy_argument="qSOFA was developed for pre-ICU screening; inadequate specification for ICU deployment",
)

# qSOFA with notification-level utility token (CHECK-2 pre-condition witness).
# PPV=0.22 passes the notification floor (0.15). Used only for 8-cell table cell (B,O,B).
MODEL_B_SETA_NOTIFICATION = ModelMetrics(
    model_id="qsofa",
    dataset_id="challenge2019_setA_icu",
    threshold=1.0,  # lower threshold to boost sensitivity/PPV for notification use
    auc_roc=0.68,
    auc_pr=0.55,
    brier_score=0.14,
    sensitivity=0.72,
    specificity=0.65,
    ppv=0.22,
    npv=0.94,
    training_target="qSOFA: RR>=22, altered mentation, SBP<=100 (2 of 3)",
    action_target="Nurse notification alert (notification blast radius only)",
    adequacy_argument="qSOFA was developed for pre-ICU screening; inadequate specification for ICU deployment",
)


# ── Model C: Gradient Boosted Model ───────────────────────────────────────────
# GBM trained on Challenge 2019 Set A; evaluated on Set B.
# High AUC, poor utility — mimics Epic Sepsis Model deployment pattern.
# These are representative stub values; real training occurs in Step 3.
MODEL_C_SETA = ModelMetrics(
    model_id="gbm_vitals_labs_v1",
    dataset_id="challenge2019_setA",
    threshold=0.3,
    auc_roc=0.85,
    auc_pr=0.76,
    brier_score=0.09,
    sensitivity=0.69,
    specificity=0.88,
    ppv=0.48,
    npv=0.94,
    training_target="SepsisLabel per Sepsis-3 criteria, predicted 6h before onset",
    action_target="ICU sepsis early-warning alert",
    adequacy_argument="GBM trained on Sepsis-3 labels; target adequacy confirmed on training distribution",
)

MODEL_C_SETB = ModelMetrics(
    model_id="gbm_vitals_labs_v1",
    dataset_id="challenge2019_setB",
    threshold=0.3,
    auc_roc=0.82,
    auc_pr=0.70,
    brier_score=0.12,
    sensitivity=0.58,
    specificity=0.84,
    ppv=0.31,
    npv=0.93,
    training_target="SepsisLabel per Sepsis-3 criteria, predicted 6h before onset",
    action_target="ICU sepsis early-warning alert",
    adequacy_argument="GBM trained on Sepsis-3 labels; target adequacy confirmed on training distribution",
)


# ── Model D: Epic Sepsis Model proxy ──────────────────────────────────────────
# Paper-input case only. Numbers from Wong et al. (2021) JAMA Internal Medicine.
# AUC=0.76, sensitivity=0.33, PPV=0.12 at deployed threshold.
# Do not train. Construct tokens from published validation numbers.
MODEL_D_UW = ModelMetrics(
    model_id="epic_sepsis_model_proxy",
    dataset_id="uw_medicine_validation",
    threshold=0.5,  # deployed threshold per Wong et al.
    auc_roc=0.76,
    auc_pr=0.48,
    brier_score=0.16,
    sensitivity=0.33,
    specificity=0.83,
    ppv=0.12,
    npv=0.94,
    training_target="Proprietary Epic ESM training target (not publicly disclosed)",
    action_target="ICU sepsis early-warning alert with nurse notification and order set pre-population",
    adequacy_argument="Vendor-claimed adequate; external validation by Wong et al. does not confirm",
)


# ── Model E: Lactate threshold rule ───────────────────────────────────────────
# Single-variable: serum lactate > 2.0 mmol/L.
# ms=BOUNDED by construction (lactate is a Sepsis-3 severity component).
# aq=OPEN (AUC ~0.65, below contract floor).
# cu=BOUNDED for notification blast_radius if PPV >= 0.15.
# Used only for 8-cell independence table (CHECK-1 pre-condition witness).
MODEL_E_SETA = ModelMetrics(
    model_id="lactate_threshold_2mmol",
    dataset_id="challenge2019_setA",
    threshold=2.0,  # mmol/L
    auc_roc=0.65,
    auc_pr=0.48,
    brier_score=0.18,
    sensitivity=0.70,
    specificity=0.62,
    ppv=0.24,
    npv=0.92,
    training_target="Serum lactate > 2.0 mmol/L — explicit Sepsis-3 severity component (Singer et al. 2016)",
    action_target="ICU sepsis early-warning alert (notification blast radius only)",
    adequacy_argument="Lactate > 2 mmol/L is a named Sepsis-3 severity criterion; model_specification_gap BOUNDED by definition",
)

# ── Model F: CHARTwatch (Toronto General Hospital, GIM ward) ──────────────────
# Prospectively deployed early warning system for general internal medicine.
# Operating threshold was explicitly chosen to achieve PPV=0.40, sensitivity=0.77.
# Source: Tonekaboni et al. 2022, Frontiers in Digital Health.
# "From Compute to Care: Lessons Learned from Deploying an Early Warning System
#  into Clinical Practice" — doi:10.3389/fdgth.2022.932123
#
# CHARTwatch occupies the (ALR, deployed, benefit) cell of the four-cell table:
# the compiler would have authorized it, and prospective deployment showed benefit.
# PPV=0.40 clears the clinical_utility_gap floor (0.15 for notification blast_radius).
MODEL_F_TGH = ModelMetrics(
    model_id="chartwatch_gim_v1",
    dataset_id="tgh_gim_ward",
    threshold=0.368,  # deployed operating point (Tonekaboni et al. Table 2)
    auc_roc=0.80,
    auc_pr=0.47,
    brier_score=0.11,
    sensitivity=0.77,
    specificity=0.87,
    ppv=0.40,
    npv=0.97,
    training_target="In-hospital deterioration: death or ICU transfer within 24h",
    action_target="Nurse notification alert for general internal medicine ward patients",
    adequacy_argument=(
        "Training target (death or ICU transfer within 24h) is the direct clinical "
        "action target for GIM ward deterioration alerting — model_specification_gap "
        "BOUNDED by target alignment"
    ),
)

# AUC contract floor: approximation_quality_gap is OPEN if AUC < this value.
AUC_CONTRACT_FLOOR = 0.70
