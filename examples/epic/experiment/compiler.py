"""Compiler bridge for MED-IND-001.

Builds a ProofContext from a case dict and an InductionState, runs the
compiler, and returns the emitted permission.

All gap IDs mentioned in the case's gap_statuses dict are registered as
GapRecords. Gap IDs in the case but not yet in the taxonomy are present in
the ProofContext but have no ALR requirement — they are invisible to the
profile. This is the correct behavior: the compiler cannot be told about a
gap it has not yet been shown how to track.
"""
from __future__ import annotations

import noethers_turnstile as t

from .profile import InductionState

_NOW = 1_748_736_000.0   # 2025-06-01 00:00:00 UTC — fixed for reproducibility


def _perm_str(p: t.Permission) -> str:
    return str(p)


def compile_case(case: dict, state: InductionState) -> t.Permission:
    """Compile a case against the current induction state.

    The ProofContext registers all gaps mentioned in the case (open or bounded).
    The profile only requires the gaps currently in the taxonomy. Gaps that are
    open in the case but not yet in the taxonomy are invisible to the profile —
    the compiler cannot distinguish them from gaps that simply were not mentioned.
    """
    profiles = state.build_profiles()

    # Register every gap mentioned in the case as a GapRecord.
    # Gaps absent from the case default to "open".
    gap_records = []
    for gid, status in case["gap_statuses"].items():
        gap_records.append(t.GapRecord(gap_id=gid, gap_type=gid, status=status))
    # Also register all gaps in the current taxonomy that the case didn't mention
    # (they will be "open" by default, which will block ALR once induced).
    for gid in state.alr_reqs:
        if gid not in case["gap_statuses"]:
            gap_records.append(t.GapRecord(gap_id=gid, gap_type=gid, status="open"))

    fingerprint = f"med-ind-001-{state.version_str()}"
    ctx = t.ProofContext(
        claim_id=f"claim-{case['case_id']}",
        candidate_id=f"system-{case['case_id']}",
        context_id=f"context-med-ind-001-{state.version_str()}",
        allowed_use="clinical_alert",
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
