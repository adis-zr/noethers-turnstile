"""Phase 4 verification for credit — case-by-case bijection-mapped check.

Loads docs/specs/native_chains_golden/credit.json and asserts that for every
(case_id, state_version) row, the post-rewrite compile_case emit maps to
the golden's old-chain emit via the §7.2 credit bijection.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "python"))
sys.path.insert(0, str(_ROOT / "examples" / "credit"))

import noethers_turnstile as t  # noqa: E402

from experiment.cases import ALL_CASES  # noqa: E402
from experiment.compiler import compile_case  # noqa: E402
from experiment.induction import run_induction  # noqa: E402
from experiment.profile import BIJECTION, CREDIT_CHAIN, InductionState  # noqa: E402


@pytest.fixture(scope="module")
def golden():
    return json.loads(
        (_ROOT / "docs" / "specs" / "native_chains_golden" / "credit.json").read_text()
    )


def test_bijection_covers_all_golden_emits(golden):
    for emit in golden["distinct_emits_seen"]:
        assert emit in BIJECTION, f"Bijection missing row for old-chain emit {emit!r}"


def test_v0_case_emits_match_bijection(golden):
    """v0 (pre-induction) case emits, under the new chain, match
    BIJECTION[old_emit] for every case."""
    state_v0 = InductionState()
    mismatches = []
    cases_by_id = {c["case_id"]: c for c in ALL_CASES}
    for row in golden["rows"]:
        if row["state_version"] != "v0":
            continue
        case = cases_by_id[row["case_id"]]
        actual = compile_case(case, state_v0).as_str()
        expected = BIJECTION[row["old_chain_emit"]]
        if actual != expected:
            mismatches.append(f"{row['case_id']} v0: expected {expected}, got {actual}")
    assert not mismatches, mismatches


def test_post_induction_case_emits_match_bijection(golden):
    """After running induction to convergence, each case's emit must still
    map under the bijection."""
    final_state, _audit = run_induction()
    cases_by_id = {c["case_id"]: c for c in ALL_CASES}
    mismatches = []
    for row in golden["rows"]:
        if row["state_version"] == "v0":
            continue
        case = cases_by_id[row["case_id"]]
        actual = compile_case(case, final_state).as_str()
        expected = BIJECTION[row["old_chain_emit"]]
        if actual != expected:
            mismatches.append(
                f"{row['case_id']} {row['state_version']}: expected {expected}, got {actual}"
            )
    assert not mismatches, mismatches


def test_collapse_invariant_credit_not_bottom_for_satisfied_case():
    """Dual-of-AM-01 (§7.4 #6): credit chain collapses DisallowedUsesCeiling
    to Bottom. A case that should reach LIMITED_ROLLOUT must not floor to
    REFUSE."""
    state = InductionState()
    # C01 is the positive control in the credit corpus.
    cases_by_id = {c["case_id"]: c for c in ALL_CASES}
    perm = compile_case(cases_by_id["C01"], state)
    assert perm != CREDIT_CHAIN.role(t.ChainRole.Bottom)
