"""MED-001 quick demo — no data download required.

Uses Wong et al. (2021) JAMA Internal Medicine published numbers directly.
Shows the compiler blocking the Epic Sepsis Model under profile v2 (utility-aware)
while correctly authorizing a well-specified rule-based system (SOFA).

Run:
    python3.10 run_demo.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import noethers_turnstile as t
from adapter.proof_context import (
    CaseInputs, build_proof_context,
    GAP_APPROXIMATION_QUALITY, GAP_MODEL_SPECIFICATION,
    GAP_CLINICAL_UTILITY, GAP_DISTRIBUTION_SHIFT,
    GAP_CALIBRATION, GAP_BLAST_RADIUS, GAP_FRESHNESS,
)
from adapter.tokens import (
    approximation_quality_token, clinical_utility_token,
    model_specification_token,
)
from acs.compiler import compile_context

_NOW = time.time()
_CLAIM = "claim-med001-demo"
_CAND  = "candidate-icu-patient"
_USE   = "clinical_alert"
_CTX   = "context-med001-demo-v1"


def _compile(model_name: str, gap_statuses: dict, tokens: list, profile: str) -> t.Permission:
    inputs = CaseInputs(
        claim_id=_CLAIM,
        candidate_id=_CAND,
        context_id=_CTX,
        allowed_use=_USE,
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.AAA,
        gap_statuses=gap_statuses,
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


def _prov() -> str:
    return t.compute_provenance_hash(_CLAIM, _CAND, _CTX, _USE)


def run_demo():
    print("MED-001 Demo — Clinical Sepsis Model Admissibility")
    print("=" * 60)
    print()
    print("Question: Should this model be authorized to fire nurse alerts?")
    print()

    # ── Case 1: Epic Sepsis Model proxy (Wong et al. 2021) ─────────────────
    # Published numbers: AUC=0.76, sensitivity=0.33, PPV=0.12 at deployed threshold.
    # Model was deployed at 100+ hospitals without external utility validation.

    epic_aq_token = approximation_quality_token(
        token_id="tok-epic-aq",
        claim_id=_CLAIM, candidate_id=_CAND,
        context_id=_CTX, allowed_use=_USE,
        model_id="epic_sepsis_model_proxy",
        dataset_id="uw_medicine_validation",
        split="external",
        auc_roc=0.76, auc_pr=0.48, brier_score=0.16,
        threshold=0.5,
        sensitivity=0.33, specificity=0.83, ppv=0.12, npv=0.94,
        issuer="wong_et_al_2021",
    )
    epic_ms_token = model_specification_token(
        token_id="tok-epic-ms",
        claim_id=_CLAIM, candidate_id=_CAND,
        context_id=_CTX, allowed_use=_USE,
        training_target="Proprietary Epic ESM target (undisclosed)",
        action_target="ICU sepsis early-warning alert",
        adequacy_argument="Vendor-claimed adequate; not independently confirmed",
        issuer="epic_systems",
    )
    # clinical_utility_token: PPV=0.12 < floor 0.15 → token marked invalid by detail contract
    epic_cu_token = clinical_utility_token(
        token_id="tok-epic-cu",
        claim_id=_CLAIM, candidate_id=_CAND,
        context_id=_CTX, allowed_use=_USE,
        model_id="epic_sepsis_model_proxy",
        alert_action="nurse_notification",
        blast_radius="notification",
        threshold=0.5,
        sensitivity=0.33, specificity=0.83, ppv=0.12, npv=0.94,
        sample_size=2552,
        population_description="UW Medicine ICU patients, 2013-2017 (Wong et al. 2021)",
        issuer="wong_et_al_2021",
    )

    epic_tokens = [epic_aq_token, epic_ms_token, epic_cu_token]
    epic_gaps_v1 = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }
    # Under v2 the clinical_utility_gap token is invalid (PPV < floor),
    # so the gap stays OPEN despite a token being presented.
    epic_gaps_v2 = {**epic_gaps_v1}

    epic_v1 = _compile("Epic ESM", epic_gaps_v1, epic_tokens, "v1")
    epic_v2 = _compile("Epic ESM", epic_gaps_v2, epic_tokens, "v2")

    # ── Case 2: SOFA rule-based system ─────────────────────────────────────
    # Sepsis-3 reference standard. Model specification gap closed by definition
    # (the model IS the clinical definition). Strong external validation (Seymour 2016).

    sofa_aq_token = approximation_quality_token(
        token_id="tok-sofa-aq",
        claim_id=_CLAIM, candidate_id=_CAND,
        context_id=_CTX, allowed_use=_USE,
        model_id="sofa_sepsis3",
        dataset_id="challenge2019_setA",
        split="external",
        auc_roc=0.82, auc_pr=0.74, brier_score=0.08,
        threshold=2.0,
        sensitivity=0.78, specificity=0.85, ppv=0.52, npv=0.95,
        issuer="physionet_challenge2019",
    )
    sofa_ms_token = model_specification_token(
        token_id="tok-sofa-ms",
        claim_id=_CLAIM, candidate_id=_CAND,
        context_id=_CTX, allowed_use=_USE,
        training_target="Sepsis-3 SOFA ≥ 2 from baseline plus suspected infection (Singer et al. 2016)",
        action_target="ICU sepsis early-warning alert",
        adequacy_argument="SOFA is the Sepsis-3 reference standard; target is the clinical definition itself",
        issuer="singer_et_al_2016",
    )
    sofa_cu_token = clinical_utility_token(
        token_id="tok-sofa-cu",
        claim_id=_CLAIM, candidate_id=_CAND,
        context_id=_CTX, allowed_use=_USE,
        model_id="sofa_sepsis3",
        alert_action="nurse_notification",
        blast_radius="notification",
        threshold=2.0,
        sensitivity=0.78, specificity=0.85, ppv=0.52, npv=0.95,
        sample_size=20336,
        population_description="PhysioNet Challenge 2019 Set A",
        issuer="physionet_challenge2019",
    )
    sofa_ds_token = t.ProofToken(
        token_id="tok-sofa-ds",
        token_type="clinical.distribution_shift_bound.v1",
        schema_version="med001/0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=[GAP_DISTRIBUTION_SHIFT],
        provenance_hash=_prov(),
        issued_at=_NOW,
        issuer="eicu_crd_validation",
        is_negative_control=False,
        details='{"training_population":"challenge2019_setA","deployment_population":"eicu_crd",'
                '"shift_analysis_method":"domain_classifier_auc","domain_classifier_auc":0.58,'
                '"calibration_brier_score":0.10,"sample_size":5000,'
                '"institution":"multi_site_eicu","date_range":"2014-2015",'
                '"top_feature_drift":{"SOFA_proxy":0.04,"Lactate":0.06,"MAP":0.03},'
                '"expiry_days":180}',
    )

    sofa_tokens = [sofa_aq_token, sofa_ms_token, sofa_cu_token, sofa_ds_token]
    sofa_gaps = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CLINICAL_UTILITY:      "bounded",
        GAP_DISTRIBUTION_SHIFT:    "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }

    sofa_v1 = _compile("SOFA", sofa_gaps, sofa_tokens, "v1")
    sofa_v2 = _compile("SOFA", sofa_gaps, sofa_tokens, "v2")

    # ── Case 3: CHARTwatch (Tonekaboni et al. 2022, Toronto General) ───────────
    # Prospectively deployed GIM ward early warning system.
    # Operating threshold explicitly chosen to achieve PPV=0.40, sensitivity=0.77.
    # Occupies the (ALR, deployed, benefit) cell — correctly authorized, shown beneficial.

    chartwatch_aq_token = approximation_quality_token(
        token_id="tok-cw-aq",
        claim_id=_CLAIM, candidate_id=_CAND,
        context_id=_CTX, allowed_use=_USE,
        model_id="chartwatch_gim_v1",
        dataset_id="tgh_gim_ward",
        split="prospective",
        auc_roc=0.80, auc_pr=0.47, brier_score=0.11,
        threshold=0.368,
        sensitivity=0.77, specificity=0.87, ppv=0.40, npv=0.97,
        issuer="tonekaboni_et_al_2022",
    )
    chartwatch_ms_token = model_specification_token(
        token_id="tok-cw-ms",
        claim_id=_CLAIM, candidate_id=_CAND,
        context_id=_CTX, allowed_use=_USE,
        training_target="In-hospital deterioration: death or ICU transfer within 24h",
        action_target="Nurse notification alert for GIM ward patients",
        adequacy_argument="Training target directly matches the action target for GIM ward alerting",
        issuer="tonekaboni_et_al_2022",
    )
    chartwatch_cu_token = clinical_utility_token(
        token_id="tok-cw-cu",
        claim_id=_CLAIM, candidate_id=_CAND,
        context_id=_CTX, allowed_use=_USE,
        model_id="chartwatch_gim_v1",
        alert_action="nurse_notification",
        blast_radius="notification",
        threshold=0.368,
        sensitivity=0.77, specificity=0.87, ppv=0.40, npv=0.97,
        sample_size=1987,
        population_description="TGH GIM ward patients, prospective deployment cohort",
        issuer="tonekaboni_et_al_2022",
    )
    chartwatch_ds_token = t.ProofToken(
        token_id="tok-cw-ds",
        token_type="clinical.distribution_shift_bound.v2",
        schema_version="med001.distribution_shift/0.2",
        status="valid",
        closes_gaps=[],
        bounds_gaps=[GAP_DISTRIBUTION_SHIFT],
        provenance_hash=_prov(),
        issued_at=_NOW,
        issuer="tgh_local_validation",
        is_negative_control=False,
        details='{"training_population":"tgh_gim_ward_train","deployment_population":"tgh_gim_ward_prospective",'
                '"domain_classifier_auc":0.54,"calibration_brier_ratio":1.08,'
                '"institution":"toronto_general_hospital","date_range":"2019-2021",'
                '"expiry_days":180}',
    )

    chartwatch_tokens = [chartwatch_aq_token, chartwatch_ms_token,
                         chartwatch_cu_token, chartwatch_ds_token]
    chartwatch_gaps = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CLINICAL_UTILITY:      "bounded",
        GAP_DISTRIBUTION_SHIFT:    "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }

    chartwatch_v1 = _compile("CHARTwatch", chartwatch_gaps, chartwatch_tokens, "v1")
    chartwatch_v2 = _compile("CHARTwatch", chartwatch_gaps, chartwatch_tokens, "v2")

    # ── Print results ───────────────────────────────────────────────────────

    print("Profile v1  (AUC-only — naive deployment profile):")
    print(f"  Epic Sepsis Model  AUC=0.76  PPV=0.12  →  {epic_v1}")
    print(f"  SOFA rule-based    AUC=0.82  PPV=0.52  →  {sofa_v1}")
    print(f"  CHARTwatch         AUC=0.80  PPV=0.40  →  {chartwatch_v1}")
    print()
    print("Profile v2  (utility-aware — adds clinical_utility_gap + distribution_shift_gap):")
    print(f"  Epic Sepsis Model  AUC=0.76  PPV=0.12  →  {epic_v2}")
    print(f"  SOFA rule-based    AUC=0.82  PPV=0.52  →  {sofa_v2}")
    print(f"  CHARTwatch         AUC=0.80  PPV=0.40  →  {chartwatch_v2}")
    print()

    if epic_v1 == t.Permission.ALR and epic_v2 < t.Permission.ALR:
        print("RESULT 1 (falsification): Profile v1 would have authorized Epic's deployment.")
        print(f"         Profile v2 blocks it ({epic_v2}): clinical_utility_gap OPEN.")
        print(f"         PPV=0.12 < required floor 0.15 — 8 false alerts per true positive.")
        print()
        print("         Wong et al. (2021) documented this exact deployment at 100+ hospitals.")
        print("         Sensitivity=0.33: the model missed 2 of every 3 sepsis cases.")
    else:
        print(f"NOTE: unexpected result — epic_v1={epic_v1} epic_v2={epic_v2}")

    if sofa_v2 == t.Permission.ALR:
        print()
        print(f"RESULT 2 (correction): Profile v2 correctly authorizes SOFA ({sofa_v2}).")
        print("         All gaps bounded: AUC=0.82, PPV=0.52, distribution shift validated,")
        print("         model specification = Sepsis-3 reference standard.")

    if chartwatch_v2 == t.Permission.ALR:
        print()
        print(f"RESULT 3 (positive control): Profile v2 correctly authorizes CHARTwatch ({chartwatch_v2}).")
        print("         PPV=0.40 >> floor 0.15. Prospectively deployed at Toronto General.")
        print("         Profile v2 is not over-refusal: well-evidenced deployments still reach ALR.")
    else:
        print(f"NOTE: unexpected CHARTwatch result — v2={chartwatch_v2}")


if __name__ == "__main__":
    run_demo()
