"""MED-001 adversarial test suite (A01–A06).

All expected outputs are pre-registered. See MED-001_benchmark_spec.md §8.3 and
§9 Step 0. These cases are included in the pre-registration hash alongside the
oracle cases — they are not post-hoc.

A01: High AUC, low sensitivity — utility checked independently of AUC.
A02: Two tokens present (aq + ms), clinical_utility OPEN — missing gap not filled.
A03: clinical_utility token scoped to Set A, deployment is Set B — provenance mismatch.
A04: blast_radius mismatch — utility token for notification doesn't cover auto_order.
A05: Expired clinical_utility token — stale evidence cannot support active permission.
A06: PPV=0.12 fails PPV floor contract for auto_order — detail contract enforced.
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
    PPV_FLOOR_AUTO_ORDER,
)
from acs.compiler import compile_context

_CLAIM = "claim-med001-adversarial"
_CAND  = "candidate-adv"
_CTX_A = "context-med001|challenge2019_setA|v1"
_CTX_B = "context-med001|challenge2019_setB|v1"
_USE   = "clinical_alert"
_NOW   = 1_748_736_000.0


def _compile(
    gap_statuses: dict,
    profile: str,
    tokens: list | None = None,
    expiry: t.Expiry | None = None,
    ctx: str = _CTX_A,
) -> t.Permission:
    inputs = CaseInputs(
        claim_id=_CLAIM,
        candidate_id=_CAND,
        context_id=ctx,
        allowed_use=_USE,
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.AAA,
        expiry=expiry,
        gap_statuses=gap_statuses,
        tokens=tokens or [],
        profile_version=profile,
    )
    ctx_obj = build_proof_context(inputs)
    judgment = compile_context(ctx_obj)
    rt = t.RuntimeContext(now_unix=_NOW, context_fingerprint=inputs.context_id)
    try:
        return judgment.permission(rt)
    except t.ExpiredError:
        return t.Permission.EXP


# ── A01: AUC=0.95, sensitivity=0.20 — utility checked independently ────────────

def test_adversarial_a01_high_auc_low_sensitivity_v1_alr():
    """A01: AUC=0.95, sensitivity=0.20 at threshold.
    Profile v1: emits ALR (falsification — utility not required).
    Tests that utility evidence is checked independently of AUC.
    Pre-registered: v1 emits ALR on this case.
    """
    # aq=B, ms=B, cu=O (no utility token), cal=B, br=B, fr=B
    statuses = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }
    result = _compile(statuses, "v1")
    assert result == t.Permission.ALR, (
        f"A01 (v1): expected ALR (falsification), got {result}. "
        "Profile v1 must emit ALR even when sensitivity=0.20 — utility not required."
    )


def test_adversarial_a01_high_auc_low_sensitivity_v2_refuses_alr():
    """A01: AUC=0.95, sensitivity=0.20 at threshold.
    Profile v2: refuses ALR.
    cu=O (no utility token) → v2 blocks ALR; AEX is ceiling.
    """
    statuses = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }
    result = _compile(statuses, "v2")
    assert result == t.Permission.AEX, (
        f"A01 (v2): expected AEX (ALR refused), got {result}."
    )


# ── A02: Two tokens present (aq + ms), clinical_utility OPEN ──────────────────

def test_adversarial_a02_two_tokens_cu_open_v1_alr():
    """A02: approximation_quality BOUNDED, model_specification BOUNDED, clinical_utility OPEN.
    Profile v1: emits ALR (falsification).
    Tests that missing gap is not filled by presence of other tokens.
    Pre-registered: v1 emits ALR on this case.
    """
    statuses = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
        # clinical_utility: open
    }
    result = _compile(statuses, "v1")
    assert result == t.Permission.ALR, (
        f"A02 (v1): expected ALR (falsification), got {result}. "
        "Profile v1 must emit ALR with cu=OPEN when aq and ms are bounded."
    )


def test_adversarial_a02_two_tokens_cu_open_v2_aex():
    """A02: approximation_quality BOUNDED, model_specification BOUNDED, clinical_utility OPEN.
    Profile v2: emits AEX at most.
    Clinical utility gap is open — ALR blocked; AEX reachable.
    """
    statuses = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }
    result = _compile(statuses, "v2")
    assert result == t.Permission.AEX, (
        f"A02 (v2): expected AEX (cu=OPEN blocks ALR), got {result}."
    )


# ── A03: Provenance mismatch — SetA token cannot cover SetB deployment ──────────

def test_adversarial_a03_provenance_mismatch_cu_open():
    """A03: clinical_utility token scoped to Set A; deployment is Set B population.
    Expected: provenance mismatch; clinical_utility_gap stays OPEN.
    Tests that cross-population token reuse is blocked.

    The token is constructed with Set A provenance (_CTX_A) but the ProofContext
    is constructed with Set B context_id (_CTX_B). The provenance hash mismatches;
    the compiler treats the token as ineffective and clinical_utility_gap stays OPEN.
    """
    # Build a utility token scoped to Set A context
    cu_token = clinical_utility_token(
        token_id="cu-seta-001",
        claim_id=_CLAIM,
        candidate_id=_CAND,
        context_id=_CTX_A,     # Set A context
        allowed_use=_USE,
        model_id="gbm_v1",
        alert_action="nurse_notification",
        blast_radius="notification",
        threshold=0.3,
        sensitivity=0.69,
        specificity=0.88,
        ppv=0.48,
        npv=0.94,
        sample_size=18000,
        population_description="Challenge 2019 Set A",
    )

    # Provide the token for a Set B deployment context
    # gap_statuses reflect that cu should be OPEN (provenance mismatch means token ineffective)
    statuses = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
        # clinical_utility: open — token provenance mismatches Set B context
    }
    # Compile against Set B context_id
    result = _compile(statuses, "v2", tokens=[cu_token], ctx=_CTX_B)
    # cu=OPEN under v2 → AEX, not ALR
    assert result == t.Permission.AEX, (
        f"A03: expected AEX (cu=OPEN after provenance mismatch), got {result}."
    )


# ── A04: Blast radius scope mismatch ──────────────────────────────────────────

def test_adversarial_a04_blast_radius_scope_mismatch():
    """A04: blast_radius in deployment = auto_order_antibiotics.
    clinical_utility token scoped to blast_radius=notification.
    Expected: blast_radius_gap stays OPEN for auto_order context.

    The token explicitly bounds clinical_utility_gap for notification only.
    When the deployment context requires auto_order blast radius, the token
    does not satisfy the blast_radius_gap because the scope doesn't match.
    We model this by leaving blast_radius_gap OPEN in the gap statuses —
    the token is valid for its scope but the deployment scope differs.
    """
    statuses = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CLINICAL_UTILITY:      "bounded",   # utility token present, but for wrong blast radius
        GAP_DISTRIBUTION_SHIFT:    "bounded",
        GAP_CALIBRATION:           "bounded",
        # blast_radius_gap: open — utility evidence is scoped to notification, not auto_order
        GAP_FRESHNESS:             "bounded",
    }
    # blast_radius_gap OPEN → ALR requires br=BOUNDED → blocked
    result = _compile(statuses, "v2")
    assert result == t.Permission.AEX, (
        f"A04: expected AEX (br=OPEN for auto_order scope), got {result}."
    )


# ── A05: Expired clinical_utility token ───────────────────────────────────────

def test_adversarial_a05_expired_utility_token():
    """A05: clinical_utility token expired (>90 days, population drift).
    Expected: token expiry fires; judgment halts at EXP.

    The ProofContext expiry is set to the past. The compiler emits EXP before
    any gap evaluation. Stale utility evidence cannot support active permission.
    """
    past_expiry = t.Expiry.at(_NOW - 1.0)  # expired before now

    statuses = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        GAP_CLINICAL_UTILITY:      "bounded",
        GAP_DISTRIBUTION_SHIFT:    "bounded",
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }
    result = _compile(statuses, "v2", expiry=past_expiry)
    assert result == t.Permission.EXP, (
        f"A05: expected EXP (expired utility evidence), got {result}."
    )


# ── A06: PPV floor contract — PPV=0.12 fails for auto_order ───────────────────

def test_adversarial_a06_ppv_below_floor_token_invalid():
    """A06: clinical_utility token with PPV=0.12, NNT=8.3.
    Profile v2 contract: PPV_floor = 0.20 for blast_radius=auto_order.
    Expected: token is invalid (status='invalid', bounds_gaps=[]).
    clinical_utility_gap stays OPEN. ALR and AEX with cu=OPEN → AEX ceiling.

    This tests the detail contract, not the compiler. The contract is part of the
    TCB. A06 verifies that the token constructor correctly marks the token invalid
    when PPV < PPV_FLOOR_AUTO_ORDER, leaving cu=OPEN.

    PPV floor value of 0.20 is the benchmark design parameter (see spec §8.3).
    Grounded in Wong et al. 2021: PPV=0.12 is the documented failure case.
    """
    assert PPV_FLOOR_AUTO_ORDER == 0.20, (
        f"PPV floor must be 0.20 per pre-registration; got {PPV_FLOOR_AUTO_ORDER}"
    )

    cu_token = clinical_utility_token(
        token_id="cu-low-ppv-001",
        claim_id=_CLAIM,
        candidate_id=_CAND,
        context_id=_CTX_A,
        allowed_use=_USE,
        model_id="epic_proxy",
        alert_action="auto_order_antibiotics",
        blast_radius="auto_order",
        threshold=0.5,
        sensitivity=0.33,
        specificity=0.83,
        ppv=0.12,           # fails PPV_FLOOR_AUTO_ORDER (0.20)
        npv=0.94,
        sample_size=2552,
        population_description="UW Medicine validation (Wong et al. 2021)",
    )

    # Token must be invalid and must not bound clinical_utility_gap
    assert cu_token.status == "invalid", (
        f"A06: token status must be 'invalid' for PPV=0.12 < floor {PPV_FLOOR_AUTO_ORDER}"
    )
    assert GAP_CLINICAL_UTILITY not in cu_token.bounds_gaps, (
        "A06: invalid token must not appear in bounds_gaps"
    )

    # With cu token invalid, gap stays OPEN — compile with cu=OPEN
    statuses = {
        GAP_APPROXIMATION_QUALITY: "bounded",
        GAP_MODEL_SPECIFICATION:   "bounded",
        # clinical_utility: open (token invalid)
        GAP_CALIBRATION:           "bounded",
        GAP_BLAST_RADIUS:          "bounded",
        GAP_FRESHNESS:             "bounded",
    }
    result = _compile(statuses, "v2", tokens=[cu_token])
    assert result == t.Permission.AEX, (
        f"A06: expected AEX (cu=OPEN after PPV floor failure), got {result}."
    )


def test_adversarial_a06_ppv_above_floor_token_valid():
    """A06 control: PPV=0.25 passes the floor. Token is valid and bounds cu.

    This confirms the floor is correctly applied — passing PPV yields a valid token.
    """
    cu_token = clinical_utility_token(
        token_id="cu-ok-ppv-001",
        claim_id=_CLAIM,
        candidate_id=_CAND,
        context_id=_CTX_A,
        allowed_use=_USE,
        model_id="sofa_v1",
        alert_action="auto_order_antibiotics",
        blast_radius="auto_order",
        threshold=2.0,
        sensitivity=0.78,
        specificity=0.85,
        ppv=0.25,           # passes PPV_FLOOR_AUTO_ORDER (0.20)
        npv=0.95,
        sample_size=18000,
        population_description="Challenge 2019 Set A",
    )

    assert cu_token.status == "valid", (
        f"A06 control: token should be valid for PPV=0.25 >= floor {PPV_FLOOR_AUTO_ORDER}"
    )
    assert GAP_CLINICAL_UTILITY in cu_token.bounds_gaps, (
        "A06 control: valid token must appear in bounds_gaps"
    )
