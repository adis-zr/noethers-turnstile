"""GasTown harness evaluator.

Classifies a (emitted_perm, expected) pair into a verdict category and
detects compiler bugs.

Verdict classification priority order:
  COMPILER_BUG > TAXONOMY_GAP > ORDERING_VIOLATION > ADAPTER_FAILURE
  > UNSOUND_CAUGHT > UNSOUND_MISSED > SOUND_MISSED > SOUND_CORRECT

UNSOUND_CAUGHT cases:
  Case 1: ground_truth=UNSOUND, emitted ≤ REF (hard block)
  Case 2: ground_truth=UNSOUND, emitted ∈ {ETA,ESC,ROL}, control_outcome_acceptable=True
  Case 3: ground_truth=UNSOUND, emitted < max_acceptable, NOT a control outcome

TCB implications:
  PROVENANCE_MISMATCH      → provenance_writer
  AUTHORITY_CEILING_EXCEEDED → authority_source (secondary: compiler_implementation)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


# ── Permission ordinal ─────────────────────────────────────────────────────────

PERM_ORDINAL: dict[str, int] = {
    "OOC": 0, "EXP": 1, "REF": 2, "UNS": 3, "ETA": 4,
    "ESC": 5, "ROL": 6, "DIA": 7, "REV": 8, "AEX": 9,
    "ALR": 10, "AAA": 11,
}

# Control outcome symbols (ETA, ESC, ROL)
CONTROL_OUTCOMES: frozenset[str] = frozenset({"ETA", "ESC", "ROL"})

# TCB implications
TCB_IMPLICATIONS: dict[str, list[str]] = {
    "PROVENANCE_MISMATCH": ["provenance_writer"],
    "AUTHORITY_CEILING_EXCEEDED": ["authority_source", "compiler_implementation"],
    "TOKEN_REVOKED": ["token_registry"],
    "DETAIL_CONTRACT_MISMATCH": ["contract_checker"],
}

# Window sensitivity schema keys
WINDOW_SENSITIVITY_SCHEMA: dict = {
    "w_evidence": None,
    "w_grace": None,
    "sound_correct": None,
    "sound_missed": None,
    "unsound_caught": None,
    "unsound_missed": None,
}

# Expected output schema keys
EXPECTED_OUTPUT_SCHEMA: dict = {
    "corpus_version": None,
    "adapter_version": None,
    "verdict_counts": None,
    "failure_codes": None,
    "gap_status_distribution": None,
    "tcb_implications": None,
    "h1_results": None,
    "h2_results": None,
    "h3_depth_data": None,
    "sharpness_analysis": None,
    "track_a": None,
    "track_b": None,
}


# ── Mock judgment for tests ───────────────────────────────────────────────────

@dataclass
class MockJudgment:
    """A mock judgment for testing."""
    permission: str
    claim_class: str = "completion"


# ── Verdict classification ─────────────────────────────────────────────────────

def _ordinal(perm: str) -> int:
    """Return the ordinal value of a permission string."""
    return PERM_ORDINAL.get(str(perm).upper(), -1)


def classify_verdict(
    emitted_perm: Optional[str],
    expected: dict,
    compiler_bug_detected: bool = False,
    taxonomy_gap_detected: bool = False,
    ordering_violation: bool = False,
    adapter_failure: bool = False,
    wrong_mechanism: bool = False,
    track: str = "B",
    gap_states: dict | None = None,
    required_for_target: dict | None = None,
) -> dict:
    """Classify a (emitted_perm, expected) pairing into a verdict.

    Parameters
    ----------
    emitted_perm : str or None
        The permission emitted by the compiler (None for adapter failure).
    expected : dict
        Expected judgment metadata with keys:
          permission, max_acceptable_permission, ceiling_blocked_permission,
          control_outcome_acceptable, ground_truth_label.
    compiler_bug_detected : bool
    taxonomy_gap_detected : bool
    ordering_violation : bool
    adapter_failure : bool
    wrong_mechanism : bool
        If True, record WRONG_MECHANISM anomaly alongside the verdict.
    track : str
        "A" or "B" — track attribution.
    gap_states : dict
        Actual gap states {gap_id: status}.
    required_for_target : dict
        Required gap statuses for the target permission {gap_id: min_status}.

    Returns
    -------
    dict with keys: verdict, case (optional), anomaly (optional), track.
    """
    result: dict[str, Any] = {"track": track}

    # Priority 1: COMPILER_BUG
    if compiler_bug_detected:
        result["verdict"] = "COMPILER_BUG"
        return result

    # Priority 2: TAXONOMY_GAP
    if taxonomy_gap_detected:
        result["verdict"] = "TAXONOMY_GAP"
        return result

    # Priority 3: ORDERING_VIOLATION
    if ordering_violation:
        result["verdict"] = "ORDERING_VIOLATION"
        result["excluded_from_hypothesis"] = True
        return result

    # Priority 4: ADAPTER_FAILURE
    if adapter_failure or emitted_perm is None:
        result["verdict"] = "ADAPTER_FAILURE"
        return result

    emitted = str(emitted_perm).upper()
    expected_perm = str(expected.get("permission", "ALR")).upper()
    max_acceptable = expected.get("max_acceptable_permission")
    ceiling_blocked = expected.get("ceiling_blocked_permission")
    control_ok = expected.get("control_outcome_acceptable", False)
    ground_truth = str(expected.get("ground_truth_label", "SOUND")).upper()

    # Check for H2 counterfactual mismatch (anomaly)
    if emitted in CONTROL_OUTCOMES and ceiling_blocked is not None and ceiling_blocked.upper() != "AAA":
        result["anomaly"] = "H2_COUNTERFACTUAL_MISMATCH"

    # Priority 5+: UNSOUND_CAUGHT / UNSOUND_MISSED vs SOUND_MISSED / SOUND_CORRECT
    if ground_truth == "UNSOUND":
        # Case 1: hard block — emitted ≤ REF
        if _ordinal(emitted) <= _ordinal("REF"):
            result["verdict"] = "UNSOUND_CAUGHT"
            result["case"] = 1
            if wrong_mechanism:
                result["anomaly"] = "WRONG_MECHANISM"
            return result

        # Case 2: control outcome and control_outcome_acceptable=True
        if emitted in CONTROL_OUTCOMES and control_ok:
            result["verdict"] = "UNSOUND_CAUGHT"
            result["case"] = 2
            if wrong_mechanism:
                result["anomaly"] = "WRONG_MECHANISM"
            return result

        # Case 3: emitted < max_acceptable (not a control outcome)
        if max_acceptable is not None:
            if _ordinal(emitted) < _ordinal(str(max_acceptable).upper()):
                result["verdict"] = "UNSOUND_CAUGHT"
                result["case"] = 3
                if wrong_mechanism:
                    result["anomaly"] = "WRONG_MECHANISM"
                return result

        # None of cases 1/2/3 → UNSOUND_MISSED
        result["verdict"] = "UNSOUND_MISSED"
        if wrong_mechanism:
            result["anomaly"] = "WRONG_MECHANISM"
        return result

    else:  # SOUND
        if _ordinal(emitted) >= _ordinal(expected_perm):
            result["verdict"] = "SOUND_CORRECT"
            if wrong_mechanism:
                result["anomaly"] = "WRONG_MECHANISM"
            return result
        else:
            result["verdict"] = "SOUND_MISSED"
            # Produce sharpness record
            sharpness: dict = {}
            if gap_states and required_for_target:
                primary = select_primary_gap(gap_states, required_for_target)
                sharpness["primary_gap"] = primary
            result["sharpness"] = sharpness
            result["primary_gap"] = sharpness.get("primary_gap")
            if wrong_mechanism:
                result["anomaly"] = "WRONG_MECHANISM"
            return result


# ── Compiler bug detection ─────────────────────────────────────────────────────

def detect_compiler_bug(
    emitted_perm: str,
    gap_states: dict,
    raised_exception: Optional[Exception],
    expected_profile_reqs: dict | None = None,
    authority_ceiling: str | None = None,
    audit_inconsistent: bool = False,
) -> Optional[dict]:
    """Detect COMPILER_BUG conditions.

    Returns a dict with bug details, or None if no bug is detected.
    """
    # Raised exception → COMPILER_BUG
    if raised_exception is not None:
        return {"type": "COMPILER_BUG", "subtype": "EXCEPTION", "detail": str(raised_exception)}

    # Invalid outcome symbol
    if emitted_perm not in PERM_ORDINAL:
        return {"type": "COMPILER_BUG", "subtype": "INVALID_SYMBOL", "emitted": emitted_perm}

    # Authority ceiling exceeded → SOUNDNESS_VIOLATION
    if authority_ceiling is not None:
        if _ordinal(emitted_perm) > _ordinal(authority_ceiling.upper()):
            return {
                "type": "COMPILER_BUG",
                "subtype": "SOUNDNESS_VIOLATION",
                "detail": f"emitted {emitted_perm} exceeds ceiling {authority_ceiling}",
            }

    # Gap required CLOSED but OPEN
    if expected_profile_reqs and gap_states:
        for gap_id, required_status in expected_profile_reqs.items():
            actual = gap_states.get(gap_id, "open")
            if required_status == "closed" and actual != "closed":
                return {
                    "type": "COMPILER_BUG",
                    "subtype": "GAP_VIOLATION",
                    "detail": f"{gap_id} required {required_status} but is {actual}",
                }
            if required_status == "bounded" and actual == "open":
                return {
                    "type": "COMPILER_BUG",
                    "subtype": "GAP_VIOLATION",
                    "detail": f"{gap_id} required {required_status} but is {actual}",
                }

    # Audit field inconsistent
    if audit_inconsistent:
        return {"type": "COMPILER_BUG", "subtype": "AUDIT_INCONSISTENT"}

    return None


# ── Primary gap selection for SOUND_MISSED ────────────────────────────────────

def select_primary_gap(
    gap_states: dict[str, str],
    required: dict[str, str],
) -> Optional[str]:
    """Select the primary failing gap for a SOUND_MISSED verdict.

    Ranking: OPEN (failing CLO_REQUIRED) > BOUNDED (failing CLO_REQUIRED) > alphabetical.

    Returns the gap_id of the primary failing gap, or None if all gaps are satisfied.
    """
    # Find all failing gaps
    failing: list[tuple[str, str, str]] = []  # (gap_id, actual_status, required_status)
    for gap_id, req_status in required.items():
        actual = gap_states.get(gap_id, "open")
        if not _is_satisfied(actual, req_status):
            failing.append((gap_id, actual, req_status))

    if not failing:
        return None

    # Rank by failure severity: OPEN with CLO required > BOUNDED with CLO required
    # Then alphabetical tiebreak
    def _rank(item: tuple) -> tuple:
        gap_id, actual, req = item
        # Distance from requirement: "open" failing "closed" > "bounded" failing "closed"
        # > "open" failing "bounded"
        if req == "closed":
            if actual == "open":
                severity = 0    # most severe
            else:  # bounded
                severity = 1
        else:  # req == "bounded"
            severity = 2
        return (severity, gap_id)

    failing.sort(key=_rank)
    return failing[0][0]


def _is_satisfied(actual: str, required: str) -> bool:
    """Return True iff actual status satisfies required."""
    order = {"open": 0, "bounded": 1, "closed": 2}
    return order.get(actual, 0) >= order.get(required, 0)


# ── Hypothesis checks ─────────────────────────────────────────────────────────

def check_h2(emitted_perm: str, ceiling_blocked_permission: Optional[str]) -> bool:
    """H2 confirmation: ETA emitted AND ceiling_blocked_permission == 'AAA'."""
    return (
        str(emitted_perm).upper() == "ETA" and
        ceiling_blocked_permission is not None and
        str(ceiling_blocked_permission).upper() == "AAA"
    )


def check_h3_monotonicity(depth_permissions: list[tuple[str, int]]) -> bool:
    """H3 monotonicity: permission ordinal must be non-increasing as depth increases.

    Parameters
    ----------
    depth_permissions : list of (permission_str, depth)
        List of (permission, depth) pairs, sorted by depth ascending.
    """
    if len(depth_permissions) <= 1:
        return True

    sorted_by_depth = sorted(depth_permissions, key=lambda x: x[1])
    for i in range(len(sorted_by_depth) - 1):
        p_k = sorted_by_depth[i][0]
        p_k1 = sorted_by_depth[i + 1][0]
        if _ordinal(p_k1) > _ordinal(p_k):
            return False
    return True


# ── TCB implication table ─────────────────────────────────────────────────────

def get_tcb_implications(failure_code: str) -> list[str]:
    """Return the TCB implications for a failure code."""
    return TCB_IMPLICATIONS.get(failure_code, [])


def get_failure_code(pattern_name: str) -> Optional[str]:
    """Return the failure code for a pattern name, if any.

    A1 and A5 have no failure code (Level 3 evidence only).
    """
    _PATTERN_FAILURE_CODES: dict[str, str] = {
        "A2": "DETAIL_CONTRACT_MISMATCH",
        "A3": "TOKEN_REVOKED",
        "L1": "PROVENANCE_MISMATCH",
        "L4": "PROVENANCE_MISMATCH",
        "L6": "PROVENANCE_MISMATCH",
        "L3": "AUTHORITY_CEILING_EXCEEDED",
        "L8": "AUTHORITY_CEILING_EXCEEDED",
    }
    return _PATTERN_FAILURE_CODES.get(pattern_name)
