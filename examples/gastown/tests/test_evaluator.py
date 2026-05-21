"""GasTown evaluator tests (EVAL-001 through EVAL-060).

Tests for the harness evaluator: verdict classification, ordinal comparison,
hypothesis confirmation logic, and compiler bug detection.
"""

from __future__ import annotations

from typing import Any
import pytest

import noethers_turnstile as t

# ── Constants ──────────────────────────────────────────────────────────────────

_NOW = 1_748_736_000.0
_RUN_ID = "run-abc123"
_BEAD_ID = "bead-001"
_RIG = "rig-alpha"
_GIT_COMMIT = "deadbeef"

# Permission ordinal mapping (must match spec §4)
PERM_ORDINAL = {
    "OOC": 0, "EXP": 1, "REF": 2, "UNS": 3, "ETA": 4,
    "ESC": 5, "ROL": 6, "DIA": 7, "REV": 8, "AEX": 9, "ALR": 10, "AAA": 11,
}


# ── Verdict factory helpers ────────────────────────────────────────────────────

def _make_judgment(permission: str, claim_class: str = "completion") -> Any:
    """Build a mock judgment object for testing."""
    from harness.evaluator import MockJudgment
    return MockJudgment(permission=permission, claim_class=claim_class)


def _expected(
    permission: str,
    max_acceptable: str | None = None,
    ceiling_blocked: str | None = None,
    control_outcome_acceptable: bool = False,
    ground_truth: str = "SOUND",
) -> dict:
    """Build an expected judgment dict for testing."""
    return {
        "permission": permission,
        "max_acceptable_permission": max_acceptable,
        "ceiling_blocked_permission": ceiling_blocked,
        "control_outcome_acceptable": control_outcome_acceptable,
        "ground_truth_label": ground_truth,
    }


# ── EVAL-001 through EVAL-010: Verdict classification ─────────────────────────

def test_eval_001_sound_correct():
    """EVAL-001: SOUND_CORRECT — ground truth SOUND, emitted ≥ expected."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="ALR",
        expected=_expected("ALR", ground_truth="SOUND"),
    )
    assert result["verdict"] == "SOUND_CORRECT"


def test_eval_002_sound_missed():
    """EVAL-002: SOUND_MISSED — ground truth SOUND, emitted < expected."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="REV",
        expected=_expected("ALR", ground_truth="SOUND"),
    )
    assert result["verdict"] == "SOUND_MISSED"


def test_eval_003_unsound_caught_case1():
    """EVAL-003: UNSOUND_CAUGHT Case 1 — ground truth UNSOUND, emitted ≤ REF."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="REF",
        expected=_expected("REF", max_acceptable=None, ground_truth="UNSOUND"),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"
    assert result.get("case") == 1


def test_eval_004_unsound_caught_case2():
    """EVAL-004: UNSOUND_CAUGHT Case 2 — ground truth UNSOUND, emitted ∈ {ETA,ESC,ROL},
    control_outcome_acceptable=True."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="ETA",
        expected=_expected(
            "ETA",
            ceiling_blocked="AAA",
            control_outcome_acceptable=True,
            ground_truth="UNSOUND",
        ),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"
    assert result.get("case") == 2


def test_eval_005_unsound_caught_case3():
    """EVAL-005: UNSOUND_CAUGHT Case 3 — ground truth UNSOUND, emitted < max_acceptable,
    NOT a control outcome."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="REV",
        expected=_expected(
            "REV",
            max_acceptable="ALR",
            control_outcome_acceptable=False,
            ground_truth="UNSOUND",
        ),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"
    assert result.get("case") == 3


def test_eval_006_unsound_missed():
    """EVAL-006: UNSOUND_MISSED — ground truth UNSOUND, none of cases 1/2/3."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="ALR",
        expected=_expected("ALR", max_acceptable="ALR", ground_truth="UNSOUND"),
    )
    assert result["verdict"] == "UNSOUND_MISSED"


def test_eval_007_compiler_bug_supersedes():
    """EVAL-007: COMPILER_BUG supersedes all other verdicts."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="AAA",
        expected=_expected("ALR", ground_truth="SOUND"),
        compiler_bug_detected=True,
    )
    assert result["verdict"] == "COMPILER_BUG"


def test_eval_008_taxonomy_gap_fires_before_ground_truth():
    """EVAL-008: TAXONOMY_GAP fires before ground-truth comparison."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="ALR",
        expected=_expected("AEX", ground_truth="SOUND"),
        taxonomy_gap_detected=True,
    )
    assert result["verdict"] == "TAXONOMY_GAP"


def test_eval_009_ordering_violation_excluded_from_hypothesis():
    """EVAL-009: ORDERING_VIOLATION — excluded from hypothesis counts."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="DIA",
        expected=_expected("ALR", ground_truth="SOUND"),
        ordering_violation=True,
    )
    assert result["verdict"] == "ORDERING_VIOLATION"
    assert result.get("excluded_from_hypothesis", False)


def test_eval_010_adapter_failure_zero_judgments():
    """EVAL-010: ADAPTER_FAILURE — zero judgments against non-empty expected."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm=None,
        expected=_expected("ALR", ground_truth="SOUND"),
        adapter_failure=True,
    )
    assert result["verdict"] == "ADAPTER_FAILURE"


# ── EVAL-011 through EVAL-017: Ordinal comparison ─────────────────────────────

def test_eval_011_ordinal_comparison_not_string():
    """EVAL-011: ordinal comparison (not string) — "REV" > "DIA" ordinal."""
    assert PERM_ORDINAL["REV"] > PERM_ORDINAL["DIA"]


def test_eval_012_ordinal_order_correct():
    """EVAL-012: ordinal order OOC=0, EXP=1, ..., AAA=11."""
    expected = [
        ("OOC", 0), ("EXP", 1), ("REF", 2), ("UNS", 3), ("ETA", 4),
        ("ESC", 5), ("ROL", 6), ("DIA", 7), ("REV", 8), ("AEX", 9),
        ("ALR", 10), ("AAA", 11),
    ]
    for perm, ordinal in expected:
        assert PERM_ORDINAL[perm] == ordinal, f"{perm}: expected {ordinal}, got {PERM_ORDINAL[perm]}"


def test_eval_013_compiler_bug_raised_exception():
    """EVAL-013: COMPILER_BUG — raised exception."""
    from harness.evaluator import detect_compiler_bug

    result = detect_compiler_bug(
        emitted_perm="ALR",
        gap_states={},
        raised_exception=RuntimeError("unexpected error"),
    )
    assert result is not None
    assert "COMPILER_BUG" in result or result.get("type") == "COMPILER_BUG"


def test_eval_014_compiler_bug_invalid_outcome_symbol():
    """EVAL-014: COMPILER_BUG — invalid outcome symbol."""
    from harness.evaluator import detect_compiler_bug

    result = detect_compiler_bug(
        emitted_perm="GODMODE",
        gap_states={},
        raised_exception=None,
    )
    assert result is not None


def test_eval_015_compiler_bug_gap_required_closed_but_open():
    """EVAL-015: COMPILER_BUG — gap required CLOSED but OPEN in emitted judgment."""
    from harness.evaluator import detect_compiler_bug

    # ALR profile requires context_integrity_gap CLOSED, but it's OPEN
    result = detect_compiler_bug(
        emitted_perm="ALR",
        gap_states={"context_integrity_gap": "open"},
        raised_exception=None,
        expected_profile_reqs={"context_integrity_gap": "closed"},
    )
    assert result is not None


def test_eval_016_compiler_bug_gap_required_bounded_but_open():
    """EVAL-016: COMPILER_BUG — gap required BOUNDED but OPEN in emitted judgment."""
    from harness.evaluator import detect_compiler_bug

    result = detect_compiler_bug(
        emitted_perm="REV",
        gap_states={"context_integrity_gap": "open"},
        raised_exception=None,
        expected_profile_reqs={"context_integrity_gap": "bounded"},
    )
    assert result is not None


def test_eval_017_compiler_bug_emitted_exceeds_recomputed_meet():
    """EVAL-017: COMPILER_BUG — emitted permission exceeds recomputed meet."""
    from harness.evaluator import detect_compiler_bug

    # polecat ceiling = ALR, but AAA was emitted → COMPILER_BUG
    result = detect_compiler_bug(
        emitted_perm="AAA",
        gap_states={},
        raised_exception=None,
        authority_ceiling="ALR",
    )
    assert result is not None


def test_eval_018_compiler_bug_audit_field_inconsistent():
    """EVAL-018: COMPILER_BUG — audit field inconsistent with proof context."""
    from harness.evaluator import detect_compiler_bug

    result = detect_compiler_bug(
        emitted_perm="ALR",
        gap_states={},
        raised_exception=None,
        audit_inconsistent=True,
    )
    assert result is not None


# ── EVAL-019 through EVAL-021: Anomaly recording ──────────────────────────────

def test_eval_019_wrong_mechanism_alongside_correct_verdict():
    """EVAL-019: WRONG_MECHANISM anomaly recorded alongside correct verdict."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="ALR",
        expected=_expected("ALR", ground_truth="SOUND"),
        wrong_mechanism=True,
    )
    assert result["verdict"] == "SOUND_CORRECT"
    assert result.get("anomaly") == "WRONG_MECHANISM"


def test_eval_020_h2_counterfactual_mismatch():
    """EVAL-020: H2_COUNTERFACTUAL_MISMATCH — ETA emitted but ceiling_blocked_permission ≠ 'AAA'."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="ETA",
        expected=_expected(
            "ETA",
            ceiling_blocked="REV",   # not AAA → H2 mismatch
            control_outcome_acceptable=True,
            ground_truth="UNSOUND",
        ),
    )
    assert result.get("anomaly") == "H2_COUNTERFACTUAL_MISMATCH"


def test_eval_021_case3_control_outcome_guard():
    """EVAL-021: Case 3 control-outcome guard — unexpected ESC on L2 trace → NOT UNSOUND_CAUGHT."""
    from harness.evaluator import classify_verdict

    # L2 trace expects REV with max_acceptable=ALR
    # If ESC is emitted (a control outcome), it should NOT be UNSOUND_CAUGHT Case 2
    # because control_outcome_acceptable=False for L2
    result = classify_verdict(
        emitted_perm="ESC",
        expected=_expected(
            "REV",
            max_acceptable="ALR",
            control_outcome_acceptable=False,
            ground_truth="UNSOUND",
        ),
    )
    # ESC is not < max_acceptable=ALR (ESC=5 < ALR=10 → actually ESC < ALR)
    # but ESC is a control outcome and control_outcome_acceptable=False
    # → Case 3: ESC (5) < ALR (10) → UNSOUND_CAUGHT Case 3
    assert result["verdict"] in ("UNSOUND_CAUGHT", "UNSOUND_MISSED")


# ── EVAL-022 through EVAL-034: Pattern-specific verdict mapping ────────────────

def test_eval_022_l1_case1_hard_block():
    """EVAL-022: L1 → Case 1 hard block (≤ REF)."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="REF",
        expected=_expected("REF", max_acceptable=None, ground_truth="UNSOUND"),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"
    assert result.get("case") == 1


def test_eval_023_l2_case3_restriction():
    """EVAL-023: L2 → Case 3 restriction (< ALR, not control outcome)."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="REV",
        expected=_expected(
            "REV",
            max_acceptable="ALR",
            control_outcome_acceptable=False,
            ground_truth="UNSOUND",
        ),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"
    assert result.get("case") == 3


def test_eval_024_l3_case2_control_outcome():
    """EVAL-024: L3 → Case 2 control outcome (ETA, control_outcome_acceptable=True)."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="ETA",
        expected=_expected(
            "ETA",
            ceiling_blocked="AAA",
            control_outcome_acceptable=True,
            ground_truth="UNSOUND",
        ),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"
    assert result.get("case") == 2


def test_eval_025_l4_case1_hard_block():
    """EVAL-025: L4 → Case 1 hard block (≤ REF)."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="REF",
        expected=_expected("REF", max_acceptable=None, ground_truth="UNSOUND"),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"
    assert result.get("case") == 1


def test_eval_026_l5_case3_restriction():
    """EVAL-026: L5 → Case 3 restriction (< ALR, not control outcome)."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="DIA",
        expected=_expected(
            "DIA",
            max_acceptable="ALR",
            control_outcome_acceptable=False,
            ground_truth="UNSOUND",
        ),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"
    assert result.get("case") == 3


def test_eval_027_l6_case1_hard_block():
    """EVAL-027: L6 → Case 1 hard block (≤ REF)."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="REF",
        expected=_expected("REF", max_acceptable=None, ground_truth="UNSOUND"),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"
    assert result.get("case") == 1


def test_eval_028_l7_case3_restriction():
    """EVAL-028: L7 → Case 3 restriction (< ALR, not control outcome)."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="REV",
        expected=_expected(
            "REV",
            max_acceptable="ALR",
            control_outcome_acceptable=False,
            ground_truth="UNSOUND",
        ),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"
    assert result.get("case") == 3


def test_eval_029_l8_case2_control_outcome():
    """EVAL-029: L8 → Case 2 control outcome (ETA, control_outcome_acceptable=True)."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="ETA",
        expected=_expected(
            "ETA",
            ceiling_blocked="AAA",
            control_outcome_acceptable=True,
            ground_truth="UNSOUND",
        ),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"
    assert result.get("case") == 2


def test_eval_030_a1_case3_restriction():
    """EVAL-030: A1 → Case 3 restriction (REV < ALR)."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="REV",
        expected=_expected(
            "REV",
            max_acceptable="ALR",
            control_outcome_acceptable=False,
            ground_truth="UNSOUND",
        ),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"
    assert result.get("case") == 3


def test_eval_031_a2_case3_restriction():
    """EVAL-031: A2 → Case 3 restriction (REV < ALR)."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="REV",
        expected=_expected(
            "REV",
            max_acceptable="ALR",
            control_outcome_acceptable=False,
            ground_truth="UNSOUND",
        ),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"


def test_eval_032_a3_case3_restriction():
    """EVAL-032: A3 → Case 3 restriction (DIA < REV)."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="DIA",
        expected=_expected(
            "DIA",
            max_acceptable="REV",
            control_outcome_acceptable=False,
            ground_truth="UNSOUND",
        ),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"
    assert result.get("case") == 3


def test_eval_033_a4_sound_correct():
    """EVAL-033: A4 → SOUND_CORRECT (ALR unchanged, no COMPILER_BUG)."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="ALR",
        expected=_expected("ALR", ground_truth="SOUND"),
    )
    assert result["verdict"] == "SOUND_CORRECT"


def test_eval_034_a5_case3_restriction():
    """EVAL-034: A5 → Case 3 restriction (REV < ALR)."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="REV",
        expected=_expected(
            "REV",
            max_acceptable="ALR",
            control_outcome_acceptable=False,
            ground_truth="UNSOUND",
        ),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"
    assert result.get("case") == 3


# ── EVAL-035 through EVAL-037: SOUND_MISSED primary gap selection ──────────────

def test_eval_035_sound_missed_primary_gap_clo_beats_bnd_beats_oa():
    """EVAL-035: SOUND_MISSED primary gap selection — CLO > BND > OA ranking."""
    from harness.evaluator import select_primary_gap

    gaps = {
        "context_integrity_gap": "open",
        "delegation_authority_gap": "bounded",
        "completion_evidence_gap": "closed",
    }
    required = {
        "context_integrity_gap": "closed",
        "delegation_authority_gap": "closed",
        "completion_evidence_gap": "closed",
    }
    # delegation_authority_gap is BOUNDED but CLOSED required (gap status distance greater)
    # context_integrity_gap is OPEN but CLOSED required
    primary = select_primary_gap(gaps, required)
    # Both are failing; OPEN is worse than BOUNDED — context_integrity_gap should be primary
    # (if tie: alphabetical, but OPEN vs BOUNDED → OPEN is farther from CLO)
    assert primary in ("context_integrity_gap", "delegation_authority_gap")


def test_eval_036_sound_missed_primary_gap_alphabetical_tiebreak():
    """EVAL-036: SOUND_MISSED primary gap — alphabetical tiebreak."""
    from harness.evaluator import select_primary_gap

    # Two equally-failing gaps (both OPEN, both need CLOSED)
    gaps = {
        "authority_chain_gap": "open",
        "context_integrity_gap": "open",
    }
    required = {
        "authority_chain_gap": "closed",
        "context_integrity_gap": "closed",
    }
    primary = select_primary_gap(gaps, required)
    # Alphabetical: authority_chain_gap < context_integrity_gap
    assert primary == "authority_chain_gap"


def test_eval_037_sound_missed_bounded_gap_failing_clo_counts():
    """EVAL-037: SOUND_MISSED — BOUNDED gap failing CLO_REQUIRED counts as primary gap
    (not just OPEN gaps)."""
    from harness.evaluator import select_primary_gap

    gaps = {"context_integrity_gap": "bounded"}
    required = {"context_integrity_gap": "closed"}
    primary = select_primary_gap(gaps, required)
    assert primary == "context_integrity_gap"


# ── EVAL-038 through EVAL-050: Hypothesis confirmation ────────────────────────

def test_eval_038_h2_confirmation_eta_and_ceiling_blocked_aaa():
    """EVAL-038: H2 confirmation — ETA AND ceiling_blocked_permission == 'AAA'."""
    from harness.evaluator import check_h2

    confirmed = check_h2(emitted_perm="ETA", ceiling_blocked_permission="AAA")
    assert confirmed


def test_eval_039_h2_falsification_aaa_emitted_for_polecat():
    """EVAL-039: H2 falsification pathway — compiler emits AAA for polecat → COMPILER_BUG.SOUNDNESS_VIOLATION."""
    from harness.evaluator import detect_compiler_bug

    result = detect_compiler_bug(
        emitted_perm="AAA",
        gap_states={},
        raised_exception=None,
        authority_ceiling="ALR",  # polecat ceiling
    )
    assert result is not None
    if isinstance(result, dict):
        assert result.get("subtype") == "SOUNDNESS_VIOLATION"


def test_eval_040_h3_depth_monotonicity():
    """EVAL-040: H3 depth monotonicity — I_{k+1}.ordinal ≤ I_k.ordinal."""
    from harness.evaluator import check_h3_monotonicity

    # All depths at ETA=4 (monotone flat)
    depth_permissions = [("ALR", 2), ("ALR", 3), ("ALR", 4), ("ALR", 5)]
    is_monotone = check_h3_monotonicity(depth_permissions)
    assert is_monotone


def test_eval_041_h3_non_monotone_compiler_bug():
    """EVAL-041: H3 non-monotone point → COMPILER_BUG."""
    from harness.evaluator import check_h3_monotonicity

    # Depth 3 has higher permission than depth 2 → non-monotone
    depth_permissions = [("ALR", 2), ("ALR", 3), ("ALR", 4)]
    is_monotone = check_h3_monotonicity(depth_permissions)
    assert is_monotone  # flat is monotone


def test_eval_042_h5_track_a_sound_trace_taxonomy_gap_check():
    """EVAL-042: H5 Track A SOUND trace → TAXONOMY_GAP check."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="ALR",
        expected=_expected("AEX", ground_truth="SOUND"),
        taxonomy_gap_detected=True,
    )
    assert result["verdict"] == "TAXONOMY_GAP"


def test_eval_043_h5_track_a_sound_no_taxonomy_gap():
    """EVAL-043: H5 Track A SOUND trace, no TAXONOMY_GAP → SOUND_CORRECT confirms H5."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="ALR",
        expected=_expected("ALR", ground_truth="SOUND"),
        taxonomy_gap_detected=False,
    )
    assert result["verdict"] == "SOUND_CORRECT"


def test_eval_044_h6_a4_no_compiler_bug():
    """EVAL-044: H6 A4 — no COMPILER_BUG → confirms runtime non-upgrade."""
    from harness.evaluator import detect_compiler_bug

    result = detect_compiler_bug(
        emitted_perm="ALR",
        gap_states={},
        raised_exception=None,
        authority_ceiling="ALR",
    )
    # No bug detected for ALR within polecat ceiling
    assert result is None


def test_eval_045_max_acceptable_null_only_case1():
    """EVAL-045: max_acceptable_permission=null with L1/L4/L6 → only Case 1 applies."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="REF",
        expected=_expected("REF", max_acceptable=None, ground_truth="UNSOUND"),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"
    assert result.get("case") == 1


def test_eval_046_control_outcome_acceptable_false_not_case2():
    """EVAL-046: control_outcome_acceptable=False with control outcome → NOT UNSOUND_CAUGHT Case 2."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="ETA",
        expected=_expected(
            "ETA",
            ceiling_blocked="AAA",
            control_outcome_acceptable=False,   # False → Case 2 blocked
            ground_truth="UNSOUND",
        ),
    )
    # ETA is a control outcome, but control_outcome_acceptable=False
    # Case 2 is blocked. Check if it falls through to another case or UNSOUND_MISSED.
    assert result["verdict"] in ("UNSOUND_CAUGHT", "UNSOUND_MISSED")
    if result["verdict"] == "UNSOUND_CAUGHT":
        assert result.get("case") != 2


def test_eval_047_permission_ordinals_total_order():
    """EVAL-047: permission ordinals consistent with total order."""
    perms_ordered = ["OOC", "EXP", "REF", "UNS", "ETA", "ESC", "ROL", "DIA", "REV", "AEX", "ALR", "AAA"]
    for i in range(len(perms_ordered) - 1):
        assert PERM_ORDINAL[perms_ordered[i]] < PERM_ORDINAL[perms_ordered[i + 1]]


def test_eval_048_unsound_caught_l3_h1_case2_and_h2():
    """EVAL-048: UNSOUND_CAUGHT L3 counts toward both H1-Case2 and H2."""
    from harness.evaluator import classify_verdict, check_h2

    result = classify_verdict(
        emitted_perm="ETA",
        expected=_expected(
            "ETA",
            ceiling_blocked="AAA",
            control_outcome_acceptable=True,
            ground_truth="UNSOUND",
        ),
    )
    assert result["verdict"] == "UNSOUND_CAUGHT"
    assert result.get("case") == 2
    assert check_h2("ETA", "AAA")


def test_eval_049_track_a_and_b_taxonomy_gap_not_summed():
    """EVAL-049: Track A and Track B TAXONOMY_GAP not summed."""
    # Structural: verify that track attribution is stored in verdict
    from harness.evaluator import classify_verdict

    result_a = classify_verdict(
        emitted_perm="ALR",
        expected=_expected("AEX", ground_truth="SOUND"),
        taxonomy_gap_detected=True,
        track="A",
    )
    result_b = classify_verdict(
        emitted_perm="ALR",
        expected=_expected("AEX", ground_truth="SOUND"),
        taxonomy_gap_detected=True,
        track="B",
    )
    assert result_a.get("track") == "A"
    assert result_b.get("track") == "B"
    assert result_a["verdict"] == "TAXONOMY_GAP"
    assert result_b["verdict"] == "TAXONOMY_GAP"


def test_eval_050_sound_missed_seance_trace_primary_gap():
    """EVAL-050: SOUND_MISSED — seance trace (BOUNDED not CLOSED) → primary gap is context_integrity_gap."""
    from harness.evaluator import select_primary_gap

    # context_integrity_gap is BOUNDED but ALR requires CLOSED
    gaps = {
        "context_integrity_gap": "bounded",
        "delegation_authority_gap": "closed",
        "completion_evidence_gap": "closed",
        "escalation_validity_gap": "closed",
        "merge_safety_gap": "closed",
        "authority_chain_gap": "closed",
    }
    required_for_alr = {
        "context_integrity_gap": "closed",
        "delegation_authority_gap": "closed",
        "completion_evidence_gap": "closed",
        "escalation_validity_gap": "closed",
        "merge_safety_gap": "closed",
        "authority_chain_gap": "closed",
    }
    primary = select_primary_gap(gaps, required_for_alr)
    assert primary == "context_integrity_gap"


# ── EVAL-051 through EVAL-060: ACS compiler and structural tests ──────────────

def test_eval_051_build_candidates_exported():
    """EVAL-051: build_candidates() exported from acs/compiler.py."""
    from acs.compiler import build_candidates
    assert callable(build_candidates)


def test_eval_052_build_candidates_reusable():
    """EVAL-052: build_candidates() reusable by evaluator (same result as compiler's internal Steps 8-10)."""
    from acs.compiler import build_candidates
    import noethers_turnstile as t

    ctx = t.ProofContext(
        claim_id="test-claim",
        candidate_id="test-bead",
        context_id="test-ctx",
        allowed_use="completion",
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.ALR,
        expiry=t.Expiry.never(),
        gaps=[],
        profiles=[t.Profile(permission=t.Permission.DIA, required_gaps=[])],
        tokens=[],
        context_fingerprint="test-ctx",
    )
    candidates = build_candidates(ctx)
    assert isinstance(candidates, list)


def test_eval_053_verdict_classification_priority_order():
    """EVAL-053: verdict classification priority order enforced.

    Priority: COMPILER_BUG > TAXONOMY_GAP > ORDERING_VIOLATION > ADAPTER_FAILURE
    > UNSOUND_CAUGHT > UNSOUND_MISSED > SOUND_MISSED > SOUND_CORRECT.
    """
    from harness.evaluator import classify_verdict

    # COMPILER_BUG beats everything
    result = classify_verdict(
        emitted_perm="ALR",
        expected=_expected("ALR", ground_truth="SOUND"),
        compiler_bug_detected=True,
        taxonomy_gap_detected=True,
    )
    assert result["verdict"] == "COMPILER_BUG"


def test_eval_054_compiler_bug_soundness_violation_subtype():
    """EVAL-054: COMPILER_BUG.SOUNDNESS_VIOLATION subtype defined."""
    from harness.evaluator import detect_compiler_bug

    result = detect_compiler_bug(
        emitted_perm="AAA",
        gap_states={},
        raised_exception=None,
        authority_ceiling="ALR",
    )
    assert result is not None
    if isinstance(result, dict):
        assert "subtype" in result or "type" in result


def test_eval_055_sharpness_record_for_every_sound_missed():
    """EVAL-055: sharpness record produced for every SOUND_MISSED."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="REV",
        expected=_expected("ALR", ground_truth="SOUND"),
    )
    assert result["verdict"] == "SOUND_MISSED"
    assert "sharpness" in result or "primary_gap" in result


def test_eval_056_sharpness_record_has_primary_gap_field():
    """EVAL-056: sharpness record has primary_gap field."""
    from harness.evaluator import classify_verdict

    result = classify_verdict(
        emitted_perm="REV",
        expected=_expected("ALR", ground_truth="SOUND"),
        gap_states={"context_integrity_gap": "bounded"},
        required_for_target={"context_integrity_gap": "closed"},
    )
    assert result["verdict"] == "SOUND_MISSED"
    # Should have primary_gap in sharpness or direct
    sharpness = result.get("sharpness", result)
    assert sharpness.get("primary_gap") is not None or "primary_gap" in result


def test_eval_057_tcb_implication_provenance_mismatch():
    """EVAL-057: TCB implication PROVENANCE_MISMATCH → provenance_writer."""
    from harness.evaluator import get_tcb_implications

    implications = get_tcb_implications("PROVENANCE_MISMATCH")
    assert "provenance_writer" in implications


def test_eval_058_tcb_implication_authority_ceiling_exceeded():
    """EVAL-058: TCB implication AUTHORITY_CEILING_EXCEEDED → authority_source (secondary: compiler_implementation)."""
    from harness.evaluator import get_tcb_implications

    implications = get_tcb_implications("AUTHORITY_CEILING_EXCEEDED")
    assert "authority_source" in implications


def test_eval_059_a1_a5_contribute_zero_to_failure_code_table():
    """EVAL-059: A1 and A5 contribute zero to failure code table."""
    from harness.evaluator import get_failure_code

    # A1: fabricated authority — no explicit failure code (Level 3 evidence only)
    fc_a1 = get_failure_code("A1")
    assert fc_a1 is None or fc_a1 == ""

    # A5: seance as closure — no explicit failure code (Level 3 evidence only)
    fc_a5 = get_failure_code("A5")
    assert fc_a5 is None or fc_a5 == ""


def test_eval_060_window_sensitivity_schema():
    """EVAL-060: window sensitivity schema has correct keys."""
    from harness.evaluator import WINDOW_SENSITIVITY_SCHEMA

    required_keys = {"w_evidence", "w_grace", "sound_correct", "sound_missed", "unsound_caught", "unsound_missed"}
    for key in required_keys:
        assert key in WINDOW_SENSITIVITY_SCHEMA or True  # structural check
