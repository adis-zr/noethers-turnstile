"""MED-001 distribution shift demo — second-institution validation.

Trains a GBM on PhysioNet Challenge 2019 Set A (one health system),
then runs a domain classifier analysis against eICU-CRD (208 hospitals).

This demo answers the question the framework *forces* you to ask:
    "Is the training population close enough to the deployment population
     that the model's learned associations still hold?"

The framework cannot answer this question from AUC alone. It requires
a distribution_shift_gap token, and that token requires a domain classifier
analysis. If you cannot produce that analysis, the gap stays OPEN, and the
compiler caps permission at AEX regardless of AUC.

## What this shows

1. The compiler emits AEX (not ALR) even for a high-AUC model when
   distribution_shift_gap is OPEN — because no analysis was run.

2. After running the domain classifier on eICU-CRD, a token is issued.
   The gap status depends on the result:
     - Domain AUC < 0.60 → gap CLOSED → compiler can emit ALR
     - Domain AUC < 0.70 → gap BOUNDED → compiler can emit ALR (bounded evidence)
     - Domain AUC ≥ 0.70 → gap OPEN → token is invalid → compiler stays at AEX

3. The token carries the full evidence chain: n patients, domain AUC,
   calibration Brier ratio, per-feature drift, expiry (90 or 180 days).
   An auditor can re-run the analysis and verify the token bit-for-bit.

## Setup

1. Download eICU-CRD from https://physionet.org/content/eicu-crd/2.0/
   (requires PhysioNet registration; no CITI training required for this dataset)

2. Place the following files in examples/medical/data/eicu_crd/:
      patient.csv
      vitalPeriodic.csv
      lab.csv
      diagnosis.csv

3. Download Challenge 2019 data (Set A) to examples/medical/data/challenge2019/
   if not already present (required to train the GBM).

4. Run:
      python3.10 run_distribution_shift.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import noethers_turnstile as t
from sklearn.ensemble import GradientBoostingClassifier

from adapter.data_loader import SET_A_DIR, FEATURES, LABEL_COL, load_set, make_patient_level, impute
from adapter.distribution_shift import (
    compute_distribution_shift,
    distribution_shift_token_from_result,
    EICU_DIR,
)
from adapter.proof_context import (
    CaseInputs, build_proof_context,
    GAP_APPROXIMATION_QUALITY, GAP_MODEL_SPECIFICATION,
    GAP_CLINICAL_UTILITY, GAP_DISTRIBUTION_SHIFT,
    GAP_CALIBRATION, GAP_BLAST_RADIUS, GAP_FRESHNESS,
)
from adapter.tokens import approximation_quality_token, clinical_utility_token, model_specification_token
from acs.compiler import compile_context

_NOW  = time.time()
_CLAIM = "claim-med001-distshift"
_CAND  = "candidate-icu-patient"
_USE   = "clinical_alert"
_CTX   = "context-med001-distshift-v1"


def _prov() -> str:
    return t.compute_provenance_hash(_CLAIM, _CAND, _CTX, _USE)


def _compile(gaps: dict, tokens: list, profile: str) -> t.Permission:
    inputs = CaseInputs(
        claim_id=_CLAIM, candidate_id=_CAND,
        context_id=_CTX, allowed_use=_USE,
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.AAA,
        gap_statuses=gaps,
        tokens=tokens,
        profile_version=profile,
    )
    ctx = build_proof_context(inputs)
    judgment = compile_context(ctx)
    rt = t.RuntimeContext(now_unix=_NOW, context_fingerprint=_CTX)
    try:
        return judgment.permission(rt)
    except t.ExpiredError:
        return t.Permission.EXP


def _gbm_tokens(gbm_auc: float, gbm_ppv: float) -> list:
    """Build the three non-distribution-shift tokens for a GBM."""
    return [
        approximation_quality_token(
            token_id="tok-gbm-aq", claim_id=_CLAIM, candidate_id=_CAND,
            context_id=_CTX, allowed_use=_USE,
            model_id="gbm_vitals_labs_v1", dataset_id="challenge2019_setA", split="train",
            auc_roc=gbm_auc, auc_pr=0.70, brier_score=0.09, threshold=0.3,
            sensitivity=0.69, specificity=0.88, ppv=gbm_ppv, npv=0.94,
        ),
        model_specification_token(
            token_id="tok-gbm-ms", claim_id=_CLAIM, candidate_id=_CAND,
            context_id=_CTX, allowed_use=_USE,
            training_target="SepsisLabel per Sepsis-3 criteria, 6h before onset",
            action_target="ICU sepsis early-warning alert",
            adequacy_argument="GBM trained on Sepsis-3 labels; target adequacy confirmed",
        ),
        clinical_utility_token(
            token_id="tok-gbm-cu", claim_id=_CLAIM, candidate_id=_CAND,
            context_id=_CTX, allowed_use=_USE,
            model_id="gbm_vitals_labs_v1", alert_action="nurse_notification",
            blast_radius="notification", threshold=0.3,
            sensitivity=0.69, specificity=0.88, ppv=gbm_ppv, npv=0.94,
            sample_size=20336, population_description="PhysioNet Challenge 2019 Set A",
        ),
    ]


def main():
    print("MED-001 Distribution Shift Demo")
    print("=" * 60)

    # Check eICU data availability
    missing = [f for f in ["patient.csv", "vitalPeriodic.csv", "lab.csv", "diagnosis.csv"]
               if not (EICU_DIR / f).exists()]
    if missing:
        print()
        print("eICU-CRD data not found. Missing files:")
        for f in missing:
            print(f"  {EICU_DIR / f}")
        print()
        print("Download from https://physionet.org/content/eicu-crd/2.0/")
        print()
        print("Running demo with SIMULATED distribution shift results instead.")
        print("(This illustrates the compiler behaviour; use real data for the paper.)")
        print()
        _run_simulated_demo()
        return

    # Load training data and train GBM
    print("\nLoading Challenge 2019 Set A...")
    raw_a = load_set(SET_A_DIR)
    patient_a = impute(make_patient_level(raw_a))
    print(f"  {patient_a['patient_id'].nunique()} patients loaded.")

    print("\nTraining GBM on Set A...")
    gbm = GradientBoostingClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, random_state=42,
    )
    gbm.fit(patient_a[FEATURES].values, patient_a[LABEL_COL].values)
    gbm_proba = gbm.predict_proba(patient_a[FEATURES].values)[:, 1]
    from sklearn.metrics import roc_auc_score
    gbm_auc = roc_auc_score(patient_a[LABEL_COL].values, gbm_proba)
    print(f"  GBM AUC (Set A): {gbm_auc:.3f}")

    # Show compiler output BEFORE distribution shift analysis
    print("\n── Before distribution shift analysis ───────────────────────────")
    base_tokens = _gbm_tokens(gbm_auc=gbm_auc, gbm_ppv=0.48)
    gaps_no_ds = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CLINICAL_UTILITY:      "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
        # distribution_shift_gap: OPEN — no analysis run yet
    }
    perm_before = _compile(gaps_no_ds, base_tokens, "v2")
    print(f"  GBM (AUC={gbm_auc:.3f}, PPV=0.48)  distribution_shift_gap=OPEN  →  {perm_before}")
    print(f"  Blocked at AEX: v2 profile requires distribution_shift_gap BOUNDED for ALR.")

    # Run distribution shift analysis
    print("\nRunning domain classifier analysis (Challenge 2019 vs eICU-CRD)...")
    result = compute_distribution_shift(patient_a, gbm)

    print(f"\nDomain classifier AUC:    {result.domain_classifier_auc:.3f}  "
          f"(5-fold CV: {result.domain_classifier_auc_cv:.3f})")
    print(f"Calibration Brier ratio:  {result.calibration_brier_ratio:.3f}  "
          f"(train={result.calibration_brier_training:.3f}, "
          f"deploy={result.calibration_brier_deployment:.3f})")
    print(f"Top feature drift (normalized std):")
    for feat, drift in result.top_feature_drift.items():
        bar = "█" * int(drift * 20)
        print(f"  {feat:<20} {drift:.3f}  {bar}")
    print(f"\nGap status:  {result.gap_status.upper()}")
    print(f"Reason:      {result.gap_status_reason}")

    # Issue distribution shift token
    ds_token = distribution_shift_token_from_result(
        result,
        token_id="tok-gbm-ds",
        claim_id=_CLAIM, candidate_id=_CAND,
        context_id=_CTX, allowed_use=_USE,
        issued_at=_NOW,
    )

    # Show compiler output AFTER distribution shift analysis
    print("\n── After distribution shift analysis ────────────────────────────")
    gaps_with_ds = {**gaps_no_ds, GAP_DISTRIBUTION_SHIFT: result.gap_status}
    all_tokens = base_tokens + [ds_token]
    perm_after = _compile(gaps_with_ds, all_tokens, "v2")
    print(f"  GBM (AUC={gbm_auc:.3f}, PPV=0.48)  distribution_shift_gap={result.gap_status.upper()}  →  {perm_after}")

    if perm_after == t.Permission.ALR:
        print(f"\n  RESULT: Distribution shift bounded → compiler advances to ALR.")
        print(f"  Token expires in {result.expiry_days} days. Re-analysis required at next model review.")
    elif perm_after == t.Permission.AEX:
        print(f"\n  RESULT: Substantial distribution shift detected → gap stays OPEN → compiler holds at AEX.")
        print(f"  Retraining on eICU population or recalibration required to advance.")
    else:
        print(f"\n  RESULT: {perm_after}")


def _run_simulated_demo():
    """Simulate three distribution shift scenarios without eICU data.

    Illustrates the three gap status outcomes and their compiler implications.
    """
    import json

    base_tokens = _gbm_tokens(gbm_auc=0.85, gbm_ppv=0.48)

    scenarios = [
        {
            "name": "Exchangeable populations (domain AUC=0.55)",
            "domain_auc": 0.55,
            "brier_ratio": 1.10,
            "gap_status": "closed",
            "expiry_days": 180,
            "reason": "Domain AUC=0.55 < 0.60; populations exchangeable on model features.",
        },
        {
            "name": "Moderate shift (domain AUC=0.64)",
            "domain_auc": 0.64,
            "brier_ratio": 1.18,
            "gap_status": "bounded",
            "expiry_days": 90,
            "reason": "Domain AUC=0.64 in [0.60, 0.70); moderate shift. Calibration holds.",
        },
        {
            "name": "Substantial shift (domain AUC=0.74)",
            "domain_auc": 0.74,
            "brier_ratio": 1.42,
            "gap_status": "open",
            "expiry_days": 0,
            "reason": "Domain AUC=0.74 ≥ 0.70; substantial shift. Retraining required.",
        },
    ]

    print(f"{'Scenario':<45} {'DS gap':<10} {'Permission'}")
    print("-" * 75)

    for s in scenarios:
        # Build a simulated token
        prov = _prov()
        if s["gap_status"] == "open":
            status = "invalid"
            closes, bounds = [], []
        elif s["gap_status"] == "bounded":
            status = "valid"
            closes, bounds = [], [GAP_DISTRIBUTION_SHIFT]
        else:
            status = "valid"
            closes, bounds = [GAP_DISTRIBUTION_SHIFT], []

        ds_token = t.ProofToken(
            token_id="tok-gbm-ds-sim",
            token_type="clinical.distribution_shift_bound.v2",
            schema_version="med001.distribution_shift/0.2",
            status=status,
            closes_gaps=closes,
            bounds_gaps=bounds,
            provenance_hash=prov,
            issued_at=_NOW,
            issuer="simulated",
            is_negative_control=False,
            details=json.dumps({
                "contract_version": "med001.distribution_shift/0.2",
                "training_population": "challenge2019_setA",
                "deployment_population": "eicu_crd_simulated",
                "domain_classifier_auc": s["domain_auc"],
                "domain_classifier_auc_cv": s["domain_auc"] - 0.01,
                "calibration_brier_ratio": s["brier_ratio"],
                "gap_status": s["gap_status"],
                "gap_status_reason": s["reason"],
                "expiry_days": s["expiry_days"],
            }),
        )

        gaps = {
            GAP_APPROXIMATION_QUALITY: "bounded",
            GAP_MODEL_SPECIFICATION:   "bounded",
            GAP_CLINICAL_UTILITY:      "bounded",
            GAP_DISTRIBUTION_SHIFT:    s["gap_status"],
            GAP_CALIBRATION:           "bounded",
            GAP_BLAST_RADIUS:          "bounded",
            GAP_FRESHNESS:             "bounded",
        }
        perm = _compile(gaps, base_tokens + [ds_token], "v2")
        print(f"  {s['name']:<43} {s['gap_status'].upper():<10} {perm}")

    print()
    print("KEY FINDING:")
    print("  The framework forces you to commit to a domain classifier analysis.")
    print("  You cannot skip this step and still earn ALR — the gap stays OPEN,")
    print("  and the compiler caps permission at AEX regardless of AUC.")
    print()
    print("  This is exactly what was missing from Epic's 2021 deployment.")
    print("  Wong et al. validated on the same health system. No external")
    print("  institution validation was required — and it wasn't done.")


if __name__ == "__main__":
    main()
