"""Dynamic profile builder for MED-IND-001.

The profile grows as gaps are induced. Each version adds one gap to the ALR
requirement table. The structural skeleton (v0) contains only two gaps:
approximation_quality_gap and freshness_gap.

Profile semantics:
  DIA  — model exists and produces an output; nothing else known
  REV  — approximation quality bounded; suitable for expert review
  AEX  — structural skeleton fully satisfied; experiment-authorized
  ALR  — all induced domain gaps bounded; authorized for limited rollout
  AAA  — full authority (not used in this experiment — ceiling is ALR)

New domain gaps always enter ALR only, not AEX. AEX remains reachable with
structural evidence alone throughout the induction. This is the design
invariant: over-authorization signal is always "compiler emits ALR,
expert says < ALR." The new gap being open blocks ALR while AEX remains
reachable — exactly the pattern in LEG-001.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import noethers_turnstile as t

from .cases import GAP_APPROXIMATION_QUALITY, GAP_FRESHNESS

# ── Profile requirement tables ─────────────────────────────────────────────────

_DIA_REQS: dict[str, str] = {}

_REV_REQS: dict[str, str] = {
    GAP_APPROXIMATION_QUALITY: "bounded",
}

_AEX_REQS: dict[str, str] = {
    GAP_APPROXIMATION_QUALITY: "bounded",
    GAP_FRESHNESS:             "bounded",
}

# v0 ALR: structural skeleton only — same as AEX
# Any in-class case with AQ + freshness bounded emits ALR.
_V0_ALR_REQS: dict[str, str] = {
    GAP_APPROXIMATION_QUALITY: "bounded",
    GAP_FRESHNESS:             "bounded",
}


def _make_profile(permission: t.Permission, reqs: dict[str, str]) -> t.Profile:
    required_gaps = [
        t.GapRequirement(gap_id=gid, minimum_status=status)
        for gid, status in reqs.items()
    ]
    return t.Profile(permission=permission, required_gaps=required_gaps)


def build_profiles(alr_reqs: dict[str, str]) -> list[t.Profile]:
    """Build a profile set from the given ALR requirement table.

    DIA, REV, AEX requirements are fixed throughout induction.
    Only the ALR table grows as gaps are induced.
    AAA is set equal to ALR (not used as a meaningful ceiling here).
    """
    return [
        _make_profile(t.Permission.DIA, _DIA_REQS),
        _make_profile(t.Permission.REV, _REV_REQS),
        _make_profile(t.Permission.AEX, _AEX_REQS),
        _make_profile(t.Permission.ALR, alr_reqs),
        _make_profile(t.Permission.AAA, alr_reqs),  # same as ALR ceiling
    ]


def build_profiles_v0() -> list[t.Profile]:
    return build_profiles(_V0_ALR_REQS)


@dataclass
class InductionState:
    """Mutable taxonomy state during the induction loop.

    Starts with the structural skeleton (v0). Each call to add_gap() induces
    one new gap into the ALR requirement table and advances the version.
    """
    version: int = 0
    alr_reqs: dict[str, str] = field(default_factory=lambda: dict(_V0_ALR_REQS))
    induced_gaps: list[str] = field(default_factory=list)

    def version_str(self) -> str:
        return f"v{self.version}"

    def add_gap(self, gap_id: str, minimum_status: str = "bounded") -> None:
        self.alr_reqs[gap_id] = minimum_status
        self.induced_gaps.append(gap_id)
        self.version += 1

    def build_profiles(self) -> list[t.Profile]:
        return build_profiles(self.alr_reqs)

    def all_gap_ids(self) -> list[str]:
        return list(self.alr_reqs.keys())
