"""Dynamic profile builder for CRED-IND-001.

The profile starts from the same structural skeleton as MED-IND-001 (v0:
approximation_quality + freshness) and grows as gaps are induced.

Profile semantics:
  DIA  — model exists and produces an output; nothing else known
  REV  — approximation quality bounded; suitable for expert review only
  AEX  — structural skeleton satisfied; experiment-authorized
  ALR  — all induced domain gaps bounded; authorized for limited rollout
  AAA  — full authority (ceiling not used in this experiment)

New domain gaps always enter ALR only, not AEX. AEX remains reachable
on structural evidence alone throughout the induction. Over-authorization
signal is always "compiler emits ALR, expert says < ALR."
"""
from __future__ import annotations

from dataclasses import dataclass, field
import sys
from pathlib import Path

_WORKSPACE_PY = Path(__file__).resolve().parents[3] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

import noethers_turnstile as t

from .cases import GAP_APPROXIMATION_QUALITY, GAP_FRESHNESS

# ── Native credit chain ──────────────────────────────────────────────────────
#
# Levels are the ECOA/adverse-action deployment phases, declared by name. The
# pre-rewrite code mapped these onto the default chain (DIA/REV/AEX/ALR/AAA);
# the rewrite makes the operational meaning the level name itself.

_CREDIT_LEVELS = [
    "REFUSE",
    "MODEL_EXISTS",          # output is produced; nothing else known
    "EXPERT_REVIEW",         # approximation quality bounded; review only
    "EXPERIMENT_AUTHORIZED", # structural skeleton satisfied
    "LIMITED_ROLLOUT",       # all induced domain gaps bounded
    "FULL_AUTHORITY",        # ceiling (not used by induction)
]

CREDIT_CHAIN = t.PermissionChain.new(
    levels=_CREDIT_LEVELS,
    roles={
        t.ChainRole.Bottom: 0,                   # REFUSE
        t.ChainRole.ExpiryFloor: 0,
        t.ChainRole.Refused: 0,
        t.ChainRole.Unsatisfied: 0,
        t.ChainRole.DisallowedUsesCeiling: 0,    # credit declares no disallowed_uses
        t.ChainRole.BlockerThreshold: 1,         # MODEL_EXISTS
        t.ChainRole.Top: 5,                      # FULL_AUTHORITY
    },
)

# Domain-named permissions.
PERM_REFUSE     = CREDIT_CHAIN.parse("REFUSE")
PERM_MODEL      = CREDIT_CHAIN.parse("MODEL_EXISTS")
PERM_REVIEW     = CREDIT_CHAIN.parse("EXPERT_REVIEW")
PERM_EXPERIMENT = CREDIT_CHAIN.parse("EXPERIMENT_AUTHORIZED")
PERM_ROLLOUT    = CREDIT_CHAIN.parse("LIMITED_ROLLOUT")
PERM_AUTHORITY  = CREDIT_CHAIN.parse("FULL_AUTHORITY")

# Bijection from the pre-rewrite default-chain emits (per the §0 golden).
BIJECTION = {
    "OOC":  "REFUSE",
    "REF":  "REFUSE",
    "UNS":  "REFUSE",
    "DIA":  "MODEL_EXISTS",
    "REV":  "EXPERT_REVIEW",
    "AEX":  "EXPERIMENT_AUTHORIZED",
    "ALR":  "LIMITED_ROLLOUT",
    "AAA":  "FULL_AUTHORITY",
}

_DIA_REQS: dict[str, str] = {}

_REV_REQS: dict[str, str] = {
    GAP_APPROXIMATION_QUALITY: "bounded",
}

_AEX_REQS: dict[str, str] = {
    GAP_APPROXIMATION_QUALITY: "bounded",
    GAP_FRESHNESS:             "bounded",
}

_V0_ALR_REQS: dict[str, str] = {
    GAP_APPROXIMATION_QUALITY: "bounded",
    GAP_FRESHNESS:             "bounded",
}


def _make_profile(permission: t.Permission, reqs: dict[str, str]) -> t.Profile:
    return t.Profile(
        permission=permission,
        required_gaps=[
            t.GapRequirement(gap_id=gid, minimum_status=status)
            for gid, status in reqs.items()
        ],
    )


def build_profiles(alr_reqs: dict[str, str]) -> list[t.Profile]:
    return [
        _make_profile(PERM_MODEL,      _DIA_REQS),
        _make_profile(PERM_REVIEW,     _REV_REQS),
        _make_profile(PERM_EXPERIMENT, _AEX_REQS),
        _make_profile(PERM_ROLLOUT,    alr_reqs),
        _make_profile(PERM_AUTHORITY,  alr_reqs),
    ]


def build_profiles_v0() -> list[t.Profile]:
    return build_profiles(_V0_ALR_REQS)


@dataclass
class InductionState:
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
