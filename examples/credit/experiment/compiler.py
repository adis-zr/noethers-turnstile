"""Compiler bridge for CRED-IND-001.

Builds a ProofContext from a case dict and an InductionState, runs the
compiler, and returns the emitted permission.

Gaps mentioned in the case's gap_statuses are registered as GapRecords.
Gaps in the taxonomy not mentioned in the case default to "open" —
they will block ALR once induced, which is correct: a gap the case didn't
explicitly bound is treated as unaddressed.
"""
from __future__ import annotations

import sys
from pathlib import Path

_WORKSPACE_PY = Path(__file__).resolve().parents[3] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

import noethers_turnstile as t

from .profile import InductionState

_NOW = 1_748_736_000.0   # 2025-06-01 00:00:00 UTC — fixed for reproducibility


def compile_case(case: dict, state: InductionState) -> t.Permission:
    profiles = state.build_profiles()

    gap_records = []
    for gid, status in case["gap_statuses"].items():
        gap_records.append(t.GapRecord(gap_id=gid, gap_type=gid, status=status))
    for gid in state.alr_reqs:
        if gid not in case["gap_statuses"]:
            gap_records.append(t.GapRecord(gap_id=gid, gap_type=gid, status="open"))

    fingerprint = f"cred-ind-001-{state.version_str()}"
    ctx = t.ProofContext(
        claim_id=f"claim-{case['case_id']}",
        candidate_id=f"system-{case['case_id']}",
        context_id=f"context-cred-ind-001-{state.version_str()}",
        allowed_use="credit_adverse_action",
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.ALR,
        expiry=t.Expiry.never(),
        gaps=gap_records,
        profiles=profiles,
        tokens=[],
        context_fingerprint=fingerprint,
    )

    judgment = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=_NOW, context_fingerprint=fingerprint)
    try:
        perm = judgment.permission(rt)
    except t.ExpiredError:
        perm = t.Permission.EXP
    return perm
