"""ILS sweep experiments — Sweep A (f3 absent) and Sweep B (f3 present).

Each sweep runs RVR from 2,400 ft down to 0 ft at 100-ft steps with f1 clear.
Records compiler output at each step and identifies transition boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import sys
from pathlib import Path

_WORKSPACE_PY = Path(__file__).resolve().parents[2] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

import noethers_turnstile as t

from geometry import rvr_floor
from ils_compiler import compile_approach
from profiles import (
    GAP_SIGNAL, GAP_VISUAL, GAP_AUTH,
    PERM_DESCEND, PERM_MANUAL, PERM_ASSISTED, PERM_ZERO,
)

RVR_MAX_FT: int   = 2400
RVR_STEP_FT: int  = 100
DH_CAT1_FT: float = 200.0   # standard CAT I decision height


@dataclass(frozen=True)
class SweepPoint:
    rvr_ft: float
    dh_ft: float
    f1_clear: bool
    f3_present: bool
    f2_clear: bool
    permission: str
    raw: "t.Judgment" = field(compare=False, repr=False)


@dataclass
class SweepResult:
    name: str
    dh_ft: float
    f3_present: bool
    points: list[SweepPoint]

    def transitions(self) -> list[tuple[float, str, str]]:
        """Return (rvr_ft, from_permission, to_permission) at each boundary."""
        out = []
        for i in range(1, len(self.points)):
            prev = self.points[i - 1]
            curr = self.points[i]
            if prev.permission != curr.permission:
                out.append((curr.rvr_ft, prev.permission, curr.permission))
        return out

    def permission_at(self, rvr_ft: float) -> Optional[str]:
        for p in self.points:
            if p.rvr_ft == rvr_ft:
                return p.permission
        return None


def _perm_name(judgment: t.Judgment) -> str:
    return judgment.permission_str


def run_sweep(
    name: str,
    dh_ft: float,
    f3_present: bool,
    rvr_max: int = RVR_MAX_FT,
    rvr_step: int = RVR_STEP_FT,
) -> SweepResult:
    points = []
    for rvr_int in range(rvr_max, -rvr_step, -rvr_step):
        rvr_ft = float(rvr_int)
        geo = rvr_floor(dh_ft)
        f2_clear = geo.saturated or (rvr_ft >= geo.rvr_floor_ft)
        judgment = compile_approach(
            rvr_ft=rvr_ft,
            dh_ft=dh_ft,
            f1_clear=True,
            f3_present=f3_present,
        )
        points.append(SweepPoint(
            rvr_ft=rvr_ft,
            dh_ft=dh_ft,
            f1_clear=True,
            f3_present=f3_present,
            f2_clear=f2_clear,
            permission=_perm_name(judgment),
            raw=judgment,
        ))
    return SweepResult(name=name, dh_ft=dh_ft, f3_present=f3_present, points=points)


def run_sweep_a(dh_ft: float = DH_CAT1_FT) -> SweepResult:
    """Sweep A: f3 absent. Tests whether compiler finds the f2 transition."""
    return run_sweep("Sweep_A_f3_absent", dh_ft=dh_ft, f3_present=False)


def run_sweep_b(dh_ft: float = DH_CAT1_FT) -> SweepResult:
    """Sweep B: f3 present. Tests whether compiler finds sub-CAT-I structure."""
    return run_sweep("Sweep_B_f3_present", dh_ft=dh_ft, f3_present=True)


def run_all_sweeps(dh_ft: float = DH_CAT1_FT) -> dict[str, SweepResult]:
    return {
        "sweep_a": run_sweep_a(dh_ft),
        "sweep_b": run_sweep_b(dh_ft),
    }


def format_sweep(result: SweepResult) -> str:
    lines = [
        f"=== {result.name} (DH={result.dh_ft} ft, f3={'present' if result.f3_present else 'absent'}) ===",
        f"{'RVR (ft)':>10}  {'f2':>5}  {'Permission':>12}",
        "-" * 34,
    ]
    for p in result.points:
        lines.append(f"{p.rvr_ft:>10.0f}  {'Y' if p.f2_clear else 'N':>5}  {p.permission:>12}")

    transitions = result.transitions()
    if transitions:
        lines.append("")
        lines.append("Transitions (RVR where permission changes):")
        for rvr, from_p, to_p in transitions:
            lines.append(f"  {rvr:.0f} ft: {from_p} → {to_p}")
    else:
        lines.append("")
        lines.append("No transitions (permission constant across sweep)")

    return "\n".join(lines)


if __name__ == "__main__":
    results = run_all_sweeps()
    for result in results.values():
        print(format_sweep(result))
        print()
