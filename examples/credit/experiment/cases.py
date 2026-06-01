"""CRED-IND-001 induction corpus.

Each case records the gap statuses that were OPEN at deployment time,
reconstructed from public evidence or stipulated for the induction.
The compiler sees these statuses and the current profile. When it
over-authorizes, the OPEN gap not yet in the taxonomy is the gap to induce.

Design principle (same as MED-IND-001):
  Each induction case is constructed so that all gaps the *current* profile
  tracks are BOUNDED — the compiler has no structural reason to block it —
  but one or more gaps that the current profile does not yet track are OPEN.
  The compiler emits ALR; the expert says < ALR. The discrepancy forces one
  new gap into the taxonomy.

Gap status values: "open", "bounded", "closed"
Expert judgment values: "DIA", "REV", "AEX", "ALR"

The structural skeleton gaps (v0) are the same as MED-IND-001 — they are the
minimum needed to distinguish "nothing known" from "model exists and runs."
Domain gaps are discovered through induction.

This is an independent codebase. It does not import from examples/epic.
"""
from __future__ import annotations

# ── Structural skeleton gaps (v0) ─────────────────────────────────────────────
GAP_APPROXIMATION_QUALITY = "approximation_quality_gap"
GAP_FRESHNESS             = "freshness_gap"

# ── Induction cases ────────────────────────────────────────────────────────────

INDUCTION_CASES: list[dict] = [

    # ── C01: Positive control ──────────────────────────────────────────────────
    # A logistic regression scorecard with published feature weights, deployed
    # for a notification-only use case (pre-screen eligibility flag, not an
    # adverse action). All structural gaps bounded; the action class does not
    # trigger the reason traceability requirement because no adverse action is
    # taken. The v0 structural profile correctly authorizes this.
    {
        "case_id": "C01",
        "description": (
            "Positive control: interpretable logistic scorecard, "
            "pre-screen notification only (no adverse action)"
        ),
        "system": (
            "Hypothetical: logistic regression scorecard with published feature "
            "weights; pre-screen eligibility notification; no adverse action taken"
        ),
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY: "bounded",   # AUC validated on hold-out
            GAP_FRESHNESS:             "bounded",   # real-time bureau inputs
            # reason_traceability_gap: bounded (N/A) — action class is notification
            # only; the gap is scoped to adverse actions that carry a legal obligation
            # to communicate specific reasons. Notification does not trigger it.
            "reason_traceability_gap": "bounded",
        },
        "expert_judgment": "ALR",
        "blocking_gaps": [],
        "note": (
            "Positive control: compiler and expert agree — ALR is correct for an "
            "interpretable model used for notification only. reason_traceability_gap "
            "is bounded (N/A) because no adverse action is taken; the gap is scoped "
            "to action classes that carry a legal obligation to communicate specific "
            "reasons (denial, sanction, termination, benefit reduction). "
            "This case should emit ALR under every profile version."
        ),
    },

    # ── C02: Black-box adverse action — reason traceability absent ─────────────
    # A vendor-supplied gradient-boosted tree model used for credit denial and
    # account termination. All structural gaps are bounded: the model is well-
    # validated (AUC 0.78, GINI 0.42), training target matches action target,
    # distribution is covered, individual-level predictive validity certified,
    # blast radius bounded to individual decisions, authority contracted with
    # human loan officer review on every adverse action.
    #
    # But the model is a black-box. The creditor cannot reconstruct which inputs
    # drove this applicant's score. ECOA 15 U.S.C. § 1691(d) and Regulation B
    # 12 CFR § 1002.9 require a specific, accurate statement of the principal
    # reasons for adverse action. CFPB Circular 2022-03 (May 26, 2022) makes
    # explicit that model complexity is not an excuse for noncompliance.
    #
    # The evidence supports the score. It does not contain the reason the action
    # legally requires.
    #
    # Induces: reason_traceability_gap
    {
        "case_id": "C02",
        "description": (
            "Black-box credit scoring — adverse action legally requires specific, "
            "accurate reason traceable to this applicant's inputs; "
            "black-box model cannot supply it"
        ),
        "system": (
            "Hypothetical composite: vendor-supplied gradient-boosted tree credit "
            "scoring model; consumer lending; ECOA-covered adverse actions "
            "(denial, credit limit reduction, account termination)"
        ),
        "reference": (
            "CFPB Circular 2022-03 (May 26, 2022); "
            "ECOA 15 U.S.C. § 1691(d); Regulation B 12 CFR § 1002.9"
        ),
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY:   "bounded",   # AUC 0.78, GINI 0.42
            GAP_FRESHNESS:               "bounded",   # real-time bureau inputs
            # reason_traceability_gap: OPEN — black-box internals not auditable;
            # specific, accurate reason tied to this applicant's actual inputs
            # cannot be produced regardless of model quality
        },
        "expert_judgment": "REV",
        "blocking_gaps": ["reason_traceability_gap"],
        "note": (
            "At v0 (structural skeleton only), the compiler emits ALR: AQ bounded, "
            "freshness bounded, nothing else tracked. "
            "Expert says REV: ECOA requires a specific, accurate statement of the "
            "principal reasons for adverse action. The black-box model produces a "
            "score but not the reasoning. The loan officer cannot reconstruct which "
            "inputs drove this applicant's score. No traceable reason is available "
            "in the evidence package regardless of how good the model is. "
            "Gap to induce: reason_traceability_gap — the evidence package must "
            "contain a specific, accurate, individual-level reason traceable to the "
            "model's actual inputs before ALR is reachable for adverse-action "
            "permission levels. This gap is scoped to action classes that carry a "
            "legal obligation to communicate specific reasons to the affected party."
        ),
    },

]


# ── Held-out cases ─────────────────────────────────────────────────────────────
# Not used in induction. Test whether the converged taxonomy generalizes.

HELD_OUT_CASES: list[dict] = [

    # H01: Interpretable model with adverse action — gap closed
    # A logistic regression scorecard deployed for adverse action decisions.
    # Feature weights are published; the creditor can produce a ranked list of
    # the specific factors that drove this applicant's score directly from the
    # model's coefficients. reason_traceability_gap is bounded.
    {
        "case_id": "H01",
        "description": (
            "Interpretable scorecard — adverse action with traceable reason "
            "(logistic regression, published weights, auditable attribution)"
        ),
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY:   "bounded",
            GAP_FRESHNESS:               "bounded",
            "reason_traceability_gap":   "bounded",  # direct from model coefficients
        },
        "expert_judgment": "ALR",
        "note": (
            "Logistic regression with published weights. The creditor can produce "
            "the exact signed contribution of each input feature for this applicant "
            "directly from the model. reason_traceability_gap is bounded. "
            "Compiler should emit ALR under converged taxonomy."
        ),
    },

    # H02: Black-box model with SHAP attributions — gap status uncertain
    # A gradient-boosted tree with SHAP explanations added post-hoc.
    # SHAP approximates feature importances by querying the model as a black box.
    # The approximation quality of the post-hoc attribution is not validated —
    # it is not known whether the attributed features correspond to what the
    # model actually weighted for this individual. reason_traceability_gap is open.
    {
        "case_id": "H02",
        "description": (
            "Black-box model with unvalidated SHAP attributions — "
            "reason traceability gap open (attribution quality not certified)"
        ),
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY:   "bounded",
            GAP_FRESHNESS:               "bounded",
            "reason_traceability_gap":   "open",   # SHAP approximation not validated
        },
        "expert_judgment": "REV",
        "note": (
            "SHAP attributions are present but their approximation quality is not "
            "validated. It is not established that the attributed features correspond "
            "to the factors the model actually weighted for this applicant. "
            "CFPB Circular 2022-03 notes that post-hoc methods 'may not be possible "
            "with less interpretable models.' reason_traceability_gap remains open. "
            "Compiler should block at REV or below."
        ),
    },

    # H03: Black-box model with validated SHAP — gap closed
    # Same architecture as H02, but the attribution method has been validated:
    # the creditor has demonstrated that SHAP attributions for this model class
    # accurately identify the features the model weighted for individual cases
    # (e.g., through ablation studies or comparison with a jointly-trained
    # interpretable surrogate). reason_traceability_gap is bounded.
    {
        "case_id": "H03",
        "description": (
            "Black-box model with validated SHAP attributions — "
            "reason traceability gap closed (attribution quality certified)"
        ),
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY:   "bounded",
            GAP_FRESHNESS:               "bounded",
            "reason_traceability_gap":   "bounded",  # SHAP validated against ablation
        },
        "expert_judgment": "ALR",
        "note": (
            "SHAP attributions validated: ablation studies confirm that the attributed "
            "features are the ones the model actually weighted for individual cases. "
            "The reason token is bounded — the creditor can produce a specific, "
            "accurate, traceable reason for this applicant. "
            "Compiler should emit ALR under converged taxonomy."
        ),
    },

    # H04: No AQ validation, adverse action — structural gap open
    # A model with no AQ validation deployed for adverse actions.
    # AQ is open. The v0 structural profile blocks this at DIA already.
    # Confirms the structural skeleton is not weakened by v1.
    {
        "case_id": "H04",
        "description": (
            "No approximation quality validation — "
            "structural gap blocks before reason traceability is reached"
        ),
        "gap_statuses": {
            GAP_APPROXIMATION_QUALITY:   "open",    # no validation
            GAP_FRESHNESS:               "bounded",
            "reason_traceability_gap":   "open",
        },
        "expert_judgment": "DIA",
        "note": (
            "AQ open: no validation evidence. Compiler should emit DIA — "
            "the structural skeleton blocks before reason_traceability_gap "
            "is reached. Confirms the v1 addition does not weaken the skeleton."
        ),
    },

]

ALL_CASES: list[dict] = INDUCTION_CASES + HELD_OUT_CASES
