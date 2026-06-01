"""Admissibility compiler for UAI inference results (Tier 2).

On Tier 2 problems there is no exact ground truth, so TV distance (f2–f4) is
unavailable. The compiler operates on two observable bits:

  f1  convergence_failure   — BP did not converge within max_iter
  f5  bethe_fe_large        — |F_Bethe| / n_vars > BETHE_THRESHOLD

f1 is the primary gate: non-convergence blocks everything above EXPLORE.
f5 is a proxy for approximation quality when TV is unavailable: a large
normalised Bethe free energy gap indicates BP is far from a good fixed point.

Permission chain (same as Tier 1):
  ACT     — converged AND Bethe proxy small
  REPORT  — converged AND Bethe proxy moderate
  EXPLORE — converged (Bethe proxy not checked, or within loose bound)
  REFUSE  — non-convergence or Bethe proxy extremely large

Thresholds for Bethe proxy (per variable, so scale-invariant):
  BETHE_ACT     = 0.05  — very tight; model likely well-posed
  BETHE_REPORT  = 0.20  — moderate; usable with caveats
  BETHE_EXPLORE = 1.00  — loose; only for exploration

These thresholds are calibrated against the Ising results: on the 4×4 grid
at β=0.1 (where TV=0, BP gives ACT), the normalised Bethe FE is small; at
β=0.8 (where TV>0.20, BP gives REFUSE), it is large. We use the Ising Tier 1
results to anchor the Bethe proxy scale.

The key paper claim demonstrated here (§5, "convergence_failure as detectable
failure bit"): f1 requires no ground truth and fires independently. This is
where Tier 2 shows what Tier 1 cannot — the compiler is sound on f1 alone,
even when TV is completely unobservable.
"""
from __future__ import annotations

from dataclasses import dataclass

# Same permission levels as ising/compiler.py
EXPLORE = 0
REPORT = 1
ACT = 2
REFUSE = -1

PERMISSION_NAMES = {ACT: "ACT", REPORT: "REPORT", EXPLORE: "EXPLORE", REFUSE: "REFUSE"}

# Bethe free energy proxy thresholds (normalised by n_vars)
BETHE_TAU = {ACT: 0.05, REPORT: 0.20, EXPLORE: 1.00}


@dataclass
class UAIFailureVector:
    convergence_failure: bool
    bethe_exceeds_act: bool
    bethe_exceeds_report: bool
    bethe_exceeds_explore: bool
    # TV bits always absent on Tier 2 — documented explicitly
    tv_available: bool = False

    @classmethod
    def from_run(cls, converged: bool, bethe_per_var: float) -> "UAIFailureVector":
        if not converged:
            return cls(
                convergence_failure=True,
                bethe_exceeds_act=True,
                bethe_exceeds_report=True,
                bethe_exceeds_explore=True,
            )
        return cls(
            convergence_failure=False,
            bethe_exceeds_act=bethe_per_var > BETHE_TAU[ACT],
            bethe_exceeds_report=bethe_per_var > BETHE_TAU[REPORT],
            bethe_exceeds_explore=bethe_per_var > BETHE_TAU[EXPLORE],
        )


@dataclass
class UAICompilerResult:
    permission: int
    permission_name: str
    failure_vector: UAIFailureVector
    bethe_per_var: float
    n_vars: int
    blocking_reasons: list[str]

    def __str__(self) -> str:
        reasons = "; ".join(self.blocking_reasons) if self.blocking_reasons else "none"
        return (
            f"permission={self.permission_name} "
            f"bethe/var={self.bethe_per_var:.4f} "
            f"blocked_by=[{reasons}]"
        )


def compile_uai_result(converged: bool, bethe_fe: float, n_vars: int) -> UAICompilerResult:
    """Emit the strongest permission the evidence supports on Tier 2.

    Uses only convergence_failure (f1) and Bethe proxy (f5).
    TV bits (f2–f4) are structurally absent — this is the paper's point.
    """
    bethe_per_var = abs(bethe_fe) / max(n_vars, 1)
    fv = UAIFailureVector.from_run(converged, bethe_per_var)

    obstructions = {
        ACT:     [("convergence_failure", fv.convergence_failure),
                  ("bethe_exceeds_act",   fv.bethe_exceeds_act)],
        REPORT:  [("convergence_failure", fv.convergence_failure),
                  ("bethe_exceeds_report", fv.bethe_exceeds_report)],
        EXPLORE: [("convergence_failure", fv.convergence_failure),
                  ("bethe_exceeds_explore", fv.bethe_exceeds_explore)],
    }

    for level in [ACT, REPORT, EXPLORE]:
        active = [name for name, fired in obstructions[level] if fired]
        if not active:
            return UAICompilerResult(
                permission=level,
                permission_name=PERMISSION_NAMES[level],
                failure_vector=fv,
                bethe_per_var=bethe_per_var,
                n_vars=n_vars,
                blocking_reasons=[],
            )

    all_reasons = [name for name, fired in obstructions[EXPLORE] if fired]
    return UAICompilerResult(
        permission=REFUSE,
        permission_name="REFUSE",
        failure_vector=fv,
        bethe_per_var=bethe_per_var,
        n_vars=n_vars,
        blocking_reasons=all_reasons,
    )
