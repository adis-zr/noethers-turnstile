"""MED-001 profile validator tests.

The t.Profile object does not expose required_gaps at runtime, so we validate
the requirement tables directly from the source dicts in proof_context.py.

Verifies:
1. Profile v1 and v2 satisfy well-formedness (monotonicity).
2. The specific falsification delta: clinical_utility and distribution_shift are
   OPEN_ALLOWED in v1 ALR/AAA and BOUNDED_REQUIRED in v2 ALR/AAA.
3. DIA/REV/AEX are identical between v1 and v2.
"""
from __future__ import annotations

import pytest
import noethers_turnstile as t

from adapter.proof_context import (
    _V1_DIA_REQS,
    _V1_REV_REQS,
    _V1_AEX_REQS,
    _V1_ALR_REQS,
    _V1_AAA_REQS,
    _V2_ALR_REQS,
    _V2_AAA_REQS,
    build_profiles_v1,
    build_profiles_v2,
    GAP_CLINICAL_UTILITY,
    GAP_DISTRIBUTION_SHIFT,
    ALL_GAPS,
)

# ── Helpers ────────────────────────────────────────────────────────────────────

_STATUS_RANK = {"open": 0, "bounded": 1, "closed": 2}

_V1_REQS_BY_PERM = {
    t.Permission.DIA: _V1_DIA_REQS,
    t.Permission.REV: _V1_REV_REQS,
    t.Permission.AEX: _V1_AEX_REQS,
    t.Permission.ALR: _V1_ALR_REQS,
    t.Permission.AAA: _V1_AAA_REQS,
}

_V2_REQS_BY_PERM = {
    t.Permission.DIA: _V1_DIA_REQS,  # inherited
    t.Permission.REV: _V1_REV_REQS,  # inherited
    t.Permission.AEX: _V1_AEX_REQS,  # inherited
    t.Permission.ALR: _V2_ALR_REQS,
    t.Permission.AAA: _V2_AAA_REQS,
}

_PERM_ORDER = [
    t.Permission.DIA,
    t.Permission.REV,
    t.Permission.AEX,
    t.Permission.ALR,
    t.Permission.AAA,
]


def _effective(reqs: dict[str, str], gap_id: str) -> str:
    return reqs.get(gap_id, "open")


def _check_well_formed(reqs_by_perm: dict) -> list[str]:
    """Return well-formedness violations (stronger permission must require >= evidence)."""
    violations = []
    perms = _PERM_ORDER
    for i in range(len(perms)):
        for j in range(i + 1, len(perms)):
            p_weak   = perms[i]
            p_strong = perms[j]
            if p_weak not in reqs_by_perm or p_strong not in reqs_by_perm:
                continue
            for gap_id in ALL_GAPS:
                rank_weak   = _STATUS_RANK[_effective(reqs_by_perm[p_weak],   gap_id)]
                rank_strong = _STATUS_RANK[_effective(reqs_by_perm[p_strong], gap_id)]
                if rank_strong < rank_weak:
                    violations.append(
                        f"{p_strong} requires {gap_id}="
                        f"{_effective(reqs_by_perm[p_strong], gap_id)} but "
                        f"{p_weak} requires {_effective(reqs_by_perm[p_weak], gap_id)}"
                    )
    return violations


# ── Profile v1 well-formedness ─────────────────────────────────────────────────

def test_profile_v1_well_formed():
    """Profile v1 must satisfy monotonicity: stronger permission requires >= evidence."""
    violations = _check_well_formed(_V1_REQS_BY_PERM)
    assert not violations, "Profile v1 well-formedness failures:\n" + "\n".join(violations)


# ── Profile v2 well-formedness ─────────────────────────────────────────────────

def test_profile_v2_well_formed():
    """Profile v2 must satisfy monotonicity: stronger permission requires >= evidence."""
    violations = _check_well_formed(_V2_REQS_BY_PERM)
    assert not violations, "Profile v2 well-formedness failures:\n" + "\n".join(violations)


# ── v1 vs v2 delta: clinical_utility and distribution_shift ───────────────────

def test_v1_alr_clinical_utility_open_allowed():
    """Profile v1 ALR: clinical_utility_gap is OPEN_ALLOWED (falsification target)."""
    effective = _effective(_V1_ALR_REQS, GAP_CLINICAL_UTILITY)
    assert effective == "open", (
        f"v1 ALR: clinical_utility_gap must be OPEN_ALLOWED (got '{effective}'). "
        "Pre-registered falsification: v1 allows ALR without utility evidence."
    )


def test_v1_alr_distribution_shift_open_allowed():
    """Profile v1 ALR: distribution_shift_gap is OPEN_ALLOWED (falsification target)."""
    effective = _effective(_V1_ALR_REQS, GAP_DISTRIBUTION_SHIFT)
    assert effective == "open", (
        f"v1 ALR: distribution_shift_gap must be OPEN_ALLOWED (got '{effective}')."
    )


def test_v2_alr_clinical_utility_bounded_required():
    """Profile v2 ALR: clinical_utility_gap is BOUNDED_REQUIRED (the correction)."""
    effective = _effective(_V2_ALR_REQS, GAP_CLINICAL_UTILITY)
    assert effective == "bounded", (
        f"v2 ALR: clinical_utility_gap must be BOUNDED_REQUIRED (got '{effective}'). "
        "Pre-registered correction."
    )


def test_v2_alr_distribution_shift_bounded_required():
    """Profile v2 ALR: distribution_shift_gap is BOUNDED_REQUIRED (the correction)."""
    effective = _effective(_V2_ALR_REQS, GAP_DISTRIBUTION_SHIFT)
    assert effective == "bounded", (
        f"v2 ALR: distribution_shift_gap must be BOUNDED_REQUIRED (got '{effective}')."
    )


def test_v2_aaa_clinical_utility_bounded_required():
    """Profile v2 AAA: clinical_utility_gap is BOUNDED_REQUIRED."""
    effective = _effective(_V2_AAA_REQS, GAP_CLINICAL_UTILITY)
    assert effective == "bounded", (
        f"v2 AAA: clinical_utility_gap must be BOUNDED_REQUIRED (got '{effective}')."
    )


# ── DIA/REV/AEX unchanged between v1 and v2 ───────────────────────────────────

@pytest.mark.parametrize("perm", [t.Permission.DIA, t.Permission.REV, t.Permission.AEX])
def test_lower_profiles_unchanged_between_v1_and_v2(perm):
    """DIA, REV, AEX are identical between Profile v1 and v2 (explicit spec requirement)."""
    req_v1 = _V1_REQS_BY_PERM[perm]
    req_v2 = _V2_REQS_BY_PERM[perm]
    for gap_id in ALL_GAPS:
        s1 = _effective(req_v1, gap_id)
        s2 = _effective(req_v2, gap_id)
        assert s1 == s2, (
            f"{perm} {gap_id}: v1={s1}, v2={s2}. "
            "DIA/REV/AEX must be identical between profiles."
        )


# ── Each profile covers all expected permission levels ────────────────────────

def test_v1_covers_all_permission_levels():
    """Profile v1 must include DIA, REV, AEX, ALR, AAA."""
    profiles = build_profiles_v1()
    perms = {p.permission for p in profiles}
    expected = {t.Permission.DIA, t.Permission.REV, t.Permission.AEX,
                t.Permission.ALR, t.Permission.AAA}
    assert perms == expected, f"v1 profiles: expected {expected}, got {perms}"


def test_v2_covers_all_permission_levels():
    """Profile v2 must include DIA, REV, AEX, ALR, AAA."""
    profiles = build_profiles_v2()
    perms = {p.permission for p in profiles}
    expected = {t.Permission.DIA, t.Permission.REV, t.Permission.AEX,
                t.Permission.ALR, t.Permission.AAA}
    assert perms == expected, f"v2 profiles: expected {expected}, got {perms}"
