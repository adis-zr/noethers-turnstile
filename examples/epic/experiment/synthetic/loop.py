"""MED-STR-SYN-001: Synthetic induction loop.

The loop is structurally identical to MED-IND-001's run_induction() but
operates on SyntheticCase records instead of human-encoded case dicts.

The tie-breaking rule when multiple gaps are OPEN is: take the first one in
ground_truth_gaps order that is not yet in the taxonomy. This is the spec's
"ground truth ordering as tie-breaker" — it makes the induced set deterministic
regardless of case order (experiment C).

The loop knows ground_truth_gaps order only as a tie-breaker, not as a hint
about which gaps exist. It cannot see the ground truth set otherwise — it only
discovers gaps when the over-authorization signal fires on a case that exposes
them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import noethers_turnstile as t

from .world import SyntheticCase, SKELETON_GAPS

_NOW = 1_748_736_000.0   # 2025-06-01 fixed for reproducibility
_OVER_AUTH_CEILING = {"ALR", "AAA"}


# ── Profile state ──────────────────────────────────────────────────────────────

@dataclass
class SyntheticInductionState:
    """Mutable taxonomy state for synthetic induction."""
    version: int = 0
    alr_reqs: dict[str, str] = field(default_factory=dict)
    induced_gaps: list[str] = field(default_factory=list)

    def version_str(self) -> str:
        return f"v{self.version}"

    def add_gap(self, gap_id: str) -> None:
        self.alr_reqs[gap_id] = "bounded"
        self.induced_gaps.append(gap_id)
        self.version += 1

    def build_profiles(self) -> list[t.Profile]:
        skeleton_reqs = {g: "bounded" for g in SKELETON_GAPS}

        def _make(perm: t.Permission, reqs: dict[str, str]) -> t.Profile:
            return t.Profile(
                permission=perm,
                required_gaps=[
                    t.GapRequirement(gap_id=gid, minimum_status=s)
                    for gid, s in reqs.items()
                ],
            )

        aex_reqs = dict(skeleton_reqs)
        alr_reqs = dict(skeleton_reqs)
        alr_reqs.update(self.alr_reqs)

        return [
            _make(t.Permission.DIA, {}),
            _make(t.Permission.REV, {SKELETON_GAPS[0]: "bounded"}),
            _make(t.Permission.AEX, aex_reqs),
            _make(t.Permission.ALR, alr_reqs),
            _make(t.Permission.AAA, alr_reqs),
        ]


# ── Compiler bridge ────────────────────────────────────────────────────────────

def compile_synthetic(
    case: SyntheticCase,
    state: SyntheticInductionState,
    tracked_gaps: list[str],
) -> str:
    """Compile a synthetic case. Returns str(Permission).

    tracked_gaps: all gap IDs the current context presents to the compiler.
    Gaps in tracked_gaps but not in case.gap_statuses default to "open".
    """
    profiles = state.build_profiles()

    # Build gap records: present all tracked gaps
    gap_records: list[t.GapRecord] = []
    seen: set[str] = set()
    for gid, status in case.gap_statuses.items():
        gap_records.append(t.GapRecord(gap_id=gid, gap_type=gid, status=status))
        seen.add(gid)
    for gid in tracked_gaps:
        if gid not in seen:
            gap_records.append(t.GapRecord(gap_id=gid, gap_type=gid, status="open"))
            seen.add(gid)
    # Also add any ALR-required gaps not yet seen (so they default to open)
    for gid in state.alr_reqs:
        if gid not in seen:
            gap_records.append(t.GapRecord(gap_id=gid, gap_type=gid, status="open"))

    fingerprint = f"med-syn-001-{state.version_str()}-{case.case_id}"
    ctx = t.ProofContext(
        claim_id=f"claim-{case.case_id}",
        candidate_id=f"system-{case.case_id}",
        context_id=f"context-med-syn-001-{state.version_str()}",
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
    return str(perm)


def _is_over_authorized(compiler_out: str, expert: str) -> bool:
    return compiler_out in _OVER_AUTH_CEILING and expert not in _OVER_AUTH_CEILING


# ── Main induction loop ────────────────────────────────────────────────────────

@dataclass
class InductionTrace:
    case_id: str
    profile_before: str
    profile_after: str
    compiler_output: str
    expert_judgment: str
    over_authorized: bool
    gap_induced: str | None


def run_synthetic_induction(
    cases: list[SyntheticCase],
    ground_truth_gaps: list[str],
    tracked_gaps: list[str] | None = None,
) -> tuple[SyntheticInductionState, list[InductionTrace]]:
    """Run the synthetic induction loop.

    ground_truth_gaps: ordered list used as tie-breaker when multiple gaps
    are open. The loop only accesses these ids as candidates — not as a hint
    that they will be needed.

    tracked_gaps: the universe of gap IDs passed to compile_synthetic().
    Defaults to ground_truth_gaps (the true gap set, plus skeleton gaps
    are always added by compile_synthetic).
    """
    if tracked_gaps is None:
        tracked_gaps = list(ground_truth_gaps)

    state = SyntheticInductionState()
    trace: list[InductionTrace] = []

    for case in cases:
        profile_before = state.version_str()
        compiler_out = compile_synthetic(case, state, tracked_gaps)
        over_auth = _is_over_authorized(compiler_out, case.expert_judgment)

        gap_induced: str | None = None
        if over_auth:
            # Find the first OPEN domain gap (by ground_truth order) not yet induced
            for gid in ground_truth_gaps:
                if gid in case.true_open_gaps and gid not in state.alr_reqs:
                    state.add_gap(gid)
                    gap_induced = gid
                    break

        trace.append(InductionTrace(
            case_id=case.case_id,
            profile_before=profile_before,
            profile_after=state.version_str(),
            compiler_output=compiler_out,
            expert_judgment=case.expert_judgment,
            over_authorized=over_auth,
            gap_induced=gap_induced,
        ))

    return state, trace
