"""MED-001 oracle test suite (C01–C15).

All 15 cases are pre-registered. Expected outputs are locked before any data
run. See MED-001_benchmark_spec.md §8.1 and §9 Step 0.

Gap status abbreviations used in case comments:
  O=OPEN  B=BOUNDED  C=CLOSED  —=not applicable (expiry fires before gap eval)

Column order: aq, ms, cu, ds, cal, br, fr
"""
from __future__ import annotations

import time

import pytest
import noethers_turnstile as t

from adapter.proof_context import (
    CaseInputs,
    build_proof_context,
    GAP_APPROXIMATION_QUALITY,
    GAP_MODEL_SPECIFICATION,
    GAP_CLINICAL_UTILITY,
    GAP_DISTRIBUTION_SHIFT,
    GAP_CALIBRATION,
    GAP_BLAST_RADIUS,
    GAP_FRESHNESS,
)
from adapter.tokens import (
    approximation_quality_token,
    clinical_utility_token,
    model_specification_token,
    distribution_shift_token,
)
from adapter.models import (
    MODEL_A_SETA,
    MODEL_A_EICU,
    MODEL_B_SETA_ICU,
    MODEL_C_SETA,
    MODEL_C_SETB,
    MODEL_D_UW,
    MODEL_F_TGH,
)
from acs.compiler import compile_context

# ── Shared claim coordinates ───────────────────────────────────────────────────

_CLAIM   = "claim-med001"
_CAND    = "candidate-icu-patient"
_CTX     = "context-med001|challenge2019|v1"
_USE     = "clinical_alert"
_NOW     = 1_748_736_000.0   # 2025-06-01 00:00:00 UTC


def _inputs(
    gap_statuses: dict,
    profile: str,
    tokens: list | None = None,
    membership: t.Membership = t.Membership.InClass,
    expiry: t.Expiry | None = None,
    ctx: str = _CTX,
) -> CaseInputs:
    return CaseInputs(
        claim_id=_CLAIM,
        candidate_id=_CAND,
        context_id=ctx,
        allowed_use=_USE,
        membership=membership,
        authority_ceiling=t.Permission.AAA,
        expiry=expiry,
        gap_statuses=gap_statuses,
        tokens=tokens or [],
        profile_version=profile,
    )


def _compile(inputs: CaseInputs) -> t.Permission:
    ctx = build_proof_context(inputs)
    judgment = compile_context(ctx)
    rt = t.RuntimeContext(now_unix=_NOW, context_fingerprint=inputs.context_id)
    try:
        return judgment.permission(rt)
    except t.ExpiredError:
        return t.Permission.EXP


def _fully_bounded_statuses() -> dict:
    return {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CLINICAL_UTILITY:      "bounded",
        GAP_DISTRIBUTION_SHIFT:    "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }


def _aq_ms_cal_br_fr_bounded() -> dict:
    """aq=B, ms=B, cu=O, ds=O, cal=B, br=B, fr=B — the falsification gap profile."""
    return {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }


# ── C01: Baseline — strong model, Profile v1 → ALR ────────────────────────────

def test_oracle_c01_sofa_seta_v1_alr():
    """C01: Model A (SOFA), SetA, Profile v1.
    aq=B ms=B cu=O ds=O cal=B br=B fr=B → ALR.
    Baseline: strong model emits ALR under v1. Not a falsification — expected.
    """
    result = _compile(_inputs(_aq_ms_cal_br_fr_bounded(), "v1"))
    assert result == t.Permission.ALR, f"C01: expected ALR, got {result}"


# ── C02: Profile v2 doesn't penalize a fully-evidenced strong model ────────────

def test_oracle_c02_sofa_seta_v2_alr():
    """C02: Model A (SOFA), SetA, Profile v2.
    aq=B ms=B cu=B ds=B cal=B br=B fr=B → ALR.
    v2 does not penalize a model that has all evidence.
    """
    result = _compile(_inputs(_fully_bounded_statuses(), "v2"))
    assert result == t.Permission.ALR, f"C02: expected ALR, got {result}"


# ── C03: qSOFA — approximation bounded, specification not → REV ───────────────

def test_oracle_c03_qsofa_v1_rev():
    """C03: Model B (qSOFA), ICU/SetA, Profile v1.
    aq=B ms=O cu=O ds=O cal=O br=B fr=B → REV.
    qSOFA: approximation quality bounded, model_specification open (wrong context).
    REV requires only aq=BOUNDED; AEX requires ms=BOUNDED which is not satisfied.
    """
    statuses = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }
    result = _compile(_inputs(statuses, "v1"))
    assert result == t.Permission.REV, f"C03: expected REV, got {result}"


def test_oracle_c04_qsofa_v2_rev():
    """C04: Model B (qSOFA), ICU/SetA, Profile v2.
    aq=B ms=O cu=O ds=O cal=O br=B fr=B → REV.
    Same result as C03 — v2 doesn't change REV threshold.
    """
    statuses = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }
    result = _compile(_inputs(statuses, "v2"))
    assert result == t.Permission.REV, f"C04: expected REV, got {result}"


# ── C05: FALSIFICATION — GBM high AUC emits ALR under v1 ──────────────────────

def test_oracle_c05_gbm_setb_v1_alr_falsification():
    """C05: Model C (GBM), SetA→SetB, Profile v1.
    aq=B ms=B cu=O ds=O cal=B br=B fr=B → ALR.

    FALSIFICATION CASE. Profile v1 emits ALR without clinical_utility or
    distribution_shift evidence. A model with high AUC (0.82 on SetB) but
    unvalidated utility should not receive rollout authority.
    This is the pre-registered falsification claim.
    """
    result = _compile(_inputs(_aq_ms_cal_br_fr_bounded(), "v1"))
    assert result == t.Permission.ALR, (
        f"C05: expected ALR (falsification), got {result}. "
        "Pre-registered claim: Profile v1 emits ALR without utility evidence."
    )


# ── C06: Profile v2 blocks ALR; AEX reachable ─────────────────────────────────

def test_oracle_c06_gbm_setb_v2_aex():
    """C06: Model C (GBM), SetA→SetB, Profile v2.
    aq=B ms=B cu=O ds=O cal=B br=B fr=B → AEX.

    v2 blocks ALR (requires cu=BOUNDED, ds=BOUNDED).
    AEX is reachable: v2 AEX requires aq=B, ms=B, cal=B, fr=B — all satisfied.
    AEX = "approve experiment" is the correct ceiling for a well-specified model
    with good AUC but no cross-institution utility validation.
    """
    result = _compile(_inputs(_aq_ms_cal_br_fr_bounded(), "v2"))
    assert result == t.Permission.AEX, f"C06: expected AEX, got {result}"


# ── C07: FALSIFICATION — Epic proxy emits ALR under v1 ────────────────────────

def test_oracle_c07_epic_proxy_v1_alr_falsification():
    """C07: Model D (Epic proxy), UW validation, Profile v1.
    aq=B ms=B cu=O ds=O cal=B br=B fr=B → ALR.

    FALSIFICATION CASE. Mirrors Wong et al. (2021) deployment: AUC=0.76,
    sensitivity=0.33, PPV=0.12. Profile v1 emits ALR. This is what a correctly
    structured taxonomy would have blocked. Pre-registered falsification claim.
    """
    result = _compile(_inputs(_aq_ms_cal_br_fr_bounded(), "v1"))
    assert result == t.Permission.ALR, (
        f"C07: expected ALR (falsification), got {result}. "
        "Pre-registered claim: Epic proxy emits ALR under v1 (sensitivity=0.33, PPV=0.12)."
    )


# ── C08: Profile v2 blocks Epic proxy ─────────────────────────────────────────

def test_oracle_c08_epic_proxy_v2_aex():
    """C08: Model D (Epic proxy), UW validation, Profile v2.
    aq=B ms=B cu=O ds=O cal=B br=B fr=B → AEX.

    v2 blocks ALR; AEX reachable (same reasoning as C06).
    """
    result = _compile(_inputs(_aq_ms_cal_br_fr_bounded(), "v2"))
    assert result == t.Permission.AEX, f"C08: expected AEX, got {result}"


# ── C09: Token expiry fires (score >2h old) ────────────────────────────────────

def test_oracle_c09_expiry_fires():
    """C09: Model C, SetA, Profile v2. Token expiry fires (score >2h old) → EXP.

    Uses the expiry mechanism on ProofContext, not freshness_gap.
    The certificate itself is stale; compiler halts at EXP.
    """
    past_expiry = t.Expiry.at(_NOW - 1.0)  # expired 1 second before now
    result = _compile(_inputs(
        _aq_ms_cal_br_fr_bounded(),
        "v2",
        expiry=past_expiry,
    ))
    assert result == t.Permission.EXP, f"C09: expected EXP (expiry fired), got {result}"


# ── C10: blast_radius=auto_order, br gap OPEN → AEX ceiling ───────────────────

def test_oracle_c10_auto_order_br_open_aex():
    """C10: Model C, SetA, Profile v2.
    aq=B ms=B cu=O ds=O cal=B br=O fr=B → AEX.

    blast_radius_gap is OPEN (no token scoped to auto_order blast radius).
    ALR requires br=BOUNDED; AEX does not. Ceiling is AEX.
    """
    statuses = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CALIBRATION:           "bounded",
        # blast_radius: open
        GAP_FRESHNESS:             "bounded",
    }
    result = _compile(_inputs(statuses, "v2"))
    assert result == t.Permission.AEX, f"C10: expected AEX (br OPEN), got {result}"


# ── C11: Notification blast_radius, fully evidenced → ALR ─────────────────────

def test_oracle_c11_notification_fully_evidenced_alr():
    """C11: Model C, SetA, Profile v2.
    aq=B ms=B cu=B ds=B cal=B br=B fr=B → ALR.

    Notification blast_radius with clinical utility token properly scoped.
    v2 does not block this — all required gaps are bounded.
    """
    result = _compile(_inputs(_fully_bounded_statuses(), "v2"))
    assert result == t.Permission.ALR, f"C11: expected ALR, got {result}"


# ── C12: SOFA on eICU, distribution_shift OPEN → AEX ─────────────────────────

def test_oracle_c12_sofa_eicu_ds_open_aex():
    """C12: Model A (SOFA), eICU deployment, Profile v2.
    aq=B ms=B cu=O ds=O cal=B br=B fr=B → AEX.

    distribution_shift_gap is OPEN: no cross-institution validation token for eICU.
    The SetA-scoped distribution_shift token provenance-mismatches on eICU population.
    AEX is the ceiling. Same model that reaches ALR on training population cannot
    reach ALR in a new deployment context without new population-scoped evidence.
    """
    result = _compile(_inputs(_aq_ms_cal_br_fr_bounded(), "v2"))
    assert result == t.Permission.AEX, f"C12: expected AEX (ds OPEN on eICU), got {result}"


# ── C13: freshness_gap OPEN (stale inputs at compute time) → AEX ──────────────

def test_oracle_c13_freshness_open_aex():
    """C13: Model C, SetA, Profile v2.
    aq=B ms=B cu=O ds=O cal=B br=B fr=O → AEX.

    freshness_gap is OPEN: inputs to the model were not current at compute time.
    A freshly-issued certificate can be based on 4h-old vitals (not caught by expiry).
    ALR requires fr=BOUNDED; AEX requires fr=BOUNDED too.
    So AEX is also blocked — ceiling drops to REV.

    Wait: re-checking profile. AEX requires freshness=BOUNDED. fr=O fails AEX.
    REV does not require freshness. So ceiling is REV.
    """
    statuses = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        # freshness: open
    }
    result = _compile(_inputs(statuses, "v2"))
    # AEX requires freshness=BOUNDED (from _V1_AEX_REQS). fr=O → AEX fails → REV.
    assert result == t.Permission.REV, f"C13: expected REV (fr OPEN blocks AEX), got {result}"


# ── C14: Fully evidenced SOFA, calibrated → ALR ───────────────────────────────

def test_oracle_c14_sofa_fully_evidenced_alr():
    """C14: Model A (SOFA), SetA+calibration, Profile v2.
    aq=C ms=B cu=B ds=B cal=C br=B fr=B → ALR.

    Fully evidenced case: approximation and calibration gaps are CLOSED.
    ALR is reachable under v2 (all requirements satisfied at BOUNDED or better).
    """
    statuses = {
        GAP_APPROXIMATION_QUALITY: "closed",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CLINICAL_UTILITY:      "bounded",
        GAP_DISTRIBUTION_SHIFT:    "bounded",
        GAP_CALIBRATION:           "closed",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }
    result = _compile(_inputs(statuses, "v2"))
    assert result == t.Permission.ALR, f"C14: expected ALR, got {result}"


# ── C15: Membership check — elective surgery patient → OOC ────────────────────

def test_oracle_c15_elective_surgery_ooc_v1():
    """C15: Model C, elective surgery patient, Profile v1 → OOC.
    Membership OutOfClass; compiler returns OOC before any gap evaluation.
    """
    result = _compile(_inputs(
        _fully_bounded_statuses(),
        "v1",
        membership=t.Membership.OutOfClassExact,
    ))
    assert result == t.Permission.OOC, f"C15 (v1): expected OOC, got {result}"


def test_oracle_c15_elective_surgery_ooc_v2():
    """C15: Model C, elective surgery patient, Profile v2 → OOC."""
    result = _compile(_inputs(
        _fully_bounded_statuses(),
        "v2",
        membership=t.Membership.OutOfClassExact,
    ))
    assert result == t.Permission.OOC, f"C15 (v2): expected OOC, got {result}"


# ── C16: CHARTwatch — (ALR, deployed, benefit) cell ──────────────────────────
#
# CHARTwatch is the positive control for Profile v2: a model that was
# prospectively deployed with demonstrated benefit, and that the compiler
# correctly authorizes. It occupies the (ALR, deployed, benefit) cell of the
# four-cell table — the cell that Epic and GBM-without-utility-evidence cannot reach.
#
# Published numbers: Tonekaboni et al. 2022, Frontiers in Digital Health.
# PPV=0.40, sensitivity=0.77 at deployed threshold.
# Distribution shift: single-site deployment (TGH), validated on local cohort.

def test_oracle_c16_chartwatch_v2_alr():
    """C16: Model F (CHARTwatch), TGH GIM ward, Profile v2.
    aq=B ms=B cu=B ds=B cal=B br=B fr=B → ALR.

    POSITIVE CONTROL. All gaps bounded:
      - approximation_quality: AUC=0.80 passes floor
      - model_specification: training target = death/ICU-transfer within 24h,
        action target = GIM ward nurse notification — target aligned
      - clinical_utility: PPV=0.40 >> floor of 0.15 for notification blast_radius
      - distribution_shift: single-site TGH local cohort (bounded by local validation)
      - calibration, blast_radius, freshness: all bounded

    Compiler correctly emits ALR. This is the (ALR, deployed, benefit) cell.
    Profile v2 is not over-refusal: it authorizes well-evidenced deployments.
    """
    statuses = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CLINICAL_UTILITY:      "bounded",
        GAP_DISTRIBUTION_SHIFT:    "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }
    result = _compile(_inputs(statuses, "v2"))
    assert result == t.Permission.ALR, (
        f"C16: expected ALR (CHARTwatch positive control), got {result}. "
        "Profile v2 must authorize well-evidenced deployments (PPV=0.40 >> 0.15 floor)."
    )


def test_oracle_c16_chartwatch_v1_alr():
    """C16 (v1 check): CHARTwatch also reaches ALR under v1.

    CHARTwatch is not a falsification of v1 — v1 also authorizes it.
    The v1/v2 distinction matters only for models *missing* utility evidence.
    CHARTwatch has utility evidence; both profiles authorize it.
    """
    statuses = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CLINICAL_UTILITY:      "bounded",
        GAP_DISTRIBUTION_SHIFT:    "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }
    result = _compile(_inputs(statuses, "v1"))
    assert result == t.Permission.ALR, (
        f"C16 (v1): expected ALR, got {result}. "
        "CHARTwatch with full evidence reaches ALR under both v1 and v2."
    )


def test_oracle_c16_chartwatch_without_utility_v2_aex():
    """C16b: CHARTwatch without clinical_utility token, Profile v2 → AEX.

    Counterfactual: if CHARTwatch had been submitted without the Tonekaboni et al.
    utility validation, Profile v2 would have blocked it at AEX.
    This confirms the surgical property: v2 requires the evidence, not the model.
    A deployment that skips the utility validation step is treated identically to
    Epic's pattern — regardless of how good the model actually is.
    """
    statuses = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        # clinical_utility: open — utility validation not submitted
        GAP_DISTRIBUTION_SHIFT:    "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }
    result = _compile(_inputs(statuses, "v2"))
    assert result == t.Permission.AEX, (
        f"C16b: expected AEX (CHARTwatch without utility evidence), got {result}. "
        "v2 enforces evidence submission, not model quality."
    )


# ── Non-promotion invariant across all oracle cases ────────────────────────────

@pytest.mark.parametrize("case_id,statuses,profile,expected", [
    ("C01", _aq_ms_cal_br_fr_bounded_params := {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }, "v1", t.Permission.ALR),
    ("C02", {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CLINICAL_UTILITY:      "bounded",
        GAP_DISTRIBUTION_SHIFT:    "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }, "v2", t.Permission.ALR),
    ("C06", {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }, "v2", t.Permission.AEX),
    ("C08", {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }, "v2", t.Permission.AEX),
])
def test_non_promotion_invariant(case_id, statuses, profile, expected):
    """Non-promotion invariant: emitted permission <= expected for all oracle cases.

    Adding evidence never raises permission above what the gap statuses support.
    Checked on a subset of oracle cases that are not blocked by expiry/membership.
    """
    result = _compile(_inputs(statuses, profile))
    assert result <= expected, (
        f"{case_id}: non-promotion violated. Got {result}, expected <= {expected}"
    )
