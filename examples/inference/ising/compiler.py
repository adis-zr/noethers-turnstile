"""Admissibility compiler for Ising inference results.

Permission chain (Theorem 1 instantiated):
  ACT     — TV ≤ 0.01   (feed into automated downstream pipeline)
  REPORT  — TV ≤ 0.05   (include in a paper as a point estimate)
  EXPLORE — TV ≤ 0.20   (exploratory analysis, hypothesis generation)
  REFUSE  — everything blocked

Failure vector:
  f1  convergence_failure  — BP/MF did not converge within max_iter
  f2  tv_exceeds_act       — TV > τ(ACT)   = 0.01
  f3  tv_exceeds_report    — TV > τ(REPORT) = 0.05
  f4  tv_exceeds_explore   — TV > τ(EXPLORE) = 0.20

Non-convergence sets f1 and implies f2/f3/f4 by convention — a non-converged
run blocks ACT and REPORT; EXPLORE is also blocked because we cannot bound
the error. The failure bits encode Theorem 1 directly: each is detectable
without ground truth (f1) or requires ground truth TV (f2–f4).
"""
from __future__ import annotations

from dataclasses import dataclass

# Permission levels as integers for comparison
EXPLORE = 0
REPORT = 1
ACT = 2
REFUSE = -1

PERMISSION_NAMES = {ACT: "ACT", REPORT: "REPORT", EXPLORE: "EXPLORE", REFUSE: "REFUSE"}

# Tolerance thresholds per permission level
TAU = {ACT: 0.01, REPORT: 0.05, EXPLORE: 0.20}


@dataclass
class FailureVector:
    convergence_failure: bool
    tv_exceeds_act: bool
    tv_exceeds_report: bool
    tv_exceeds_explore: bool

    @classmethod
    def from_run(cls, converged: bool, tv: float | None) -> "FailureVector":
        """Build failure vector from a run result.

        tv=None means ground truth unavailable; only convergence bit fires.
        """
        if not converged:
            # Non-convergence convention: blocks all levels
            return cls(
                convergence_failure=True,
                tv_exceeds_act=True,
                tv_exceeds_report=True,
                tv_exceeds_explore=True,
            )
        if tv is None:
            # Converged but no ground truth — only convergence bit available
            return cls(
                convergence_failure=False,
                tv_exceeds_act=False,
                tv_exceeds_report=False,
                tv_exceeds_explore=False,
            )
        return cls(
            convergence_failure=False,
            tv_exceeds_act=tv > TAU[ACT],
            tv_exceeds_report=tv > TAU[REPORT],
            tv_exceeds_explore=tv > TAU[EXPLORE],
        )


@dataclass
class CompilerResult:
    permission: int          # one of ACT, REPORT, EXPLORE, REFUSE
    permission_name: str
    failure_vector: FailureVector
    tv: float | None
    blocking_reasons: list[str]

    def __str__(self) -> str:
        tv_str = f"{self.tv:.4f}" if self.tv is not None else "N/A"
        reasons = "; ".join(self.blocking_reasons) if self.blocking_reasons else "none"
        return (
            f"permission={self.permission_name} tv={tv_str} "
            f"blocked_by=[{reasons}]"
        )


def compile_result(converged: bool, tv: float | None) -> CompilerResult:
    """Emit the strongest permission the evidence supports.

    Scans from strongest (ACT) to weakest (EXPLORE). Returns REFUSE if
    even EXPLORE is blocked.

    This is Theorem 4 (decidability) made concrete: O(n_levels * n_bits).
    """
    fv = FailureVector.from_run(converged, tv)
    blocking_reasons: list[str] = []

    # Obstruction check per level, strongest-first
    # ACT blocked by: convergence_failure OR tv_exceeds_act
    # REPORT blocked by: convergence_failure OR tv_exceeds_report
    # EXPLORE blocked by: convergence_failure OR tv_exceeds_explore

    obstructions = {
        ACT:     [("convergence_failure", fv.convergence_failure),
                  ("tv_exceeds_act",      fv.tv_exceeds_act)],
        REPORT:  [("convergence_failure", fv.convergence_failure),
                  ("tv_exceeds_report",   fv.tv_exceeds_report)],
        EXPLORE: [("convergence_failure", fv.convergence_failure),
                  ("tv_exceeds_explore",  fv.tv_exceeds_explore)],
    }

    for level in [ACT, REPORT, EXPLORE]:
        active_obstructions = [name for name, fired in obstructions[level] if fired]
        if not active_obstructions:
            return CompilerResult(
                permission=level,
                permission_name=PERMISSION_NAMES[level],
                failure_vector=fv,
                tv=tv,
                blocking_reasons=[],
            )
        if level == ACT:
            blocking_reasons = active_obstructions

    # All levels blocked
    all_reasons = [name for name, fired in obstructions[EXPLORE] if fired]
    return CompilerResult(
        permission=REFUSE,
        permission_name="REFUSE",
        failure_vector=fv,
        tv=tv,
        blocking_reasons=all_reasons,
    )


def compile_at_tau(converged: bool, tv: float | None, tau: float) -> int:
    """Emit the permission level for a single threshold tau.

    Returns the highest level p such that tv <= tau and BP converged.
    Used for threshold sweeps — caller supplies tau, compiler emits {ACT, REFUSE}.
    This is a single-level binary compiler: emit ACT if clear, else REFUSE.
    """
    if not converged:
        return REFUSE
    if tv is None:
        return REFUSE
    return ACT if tv <= tau else REFUSE


def tv_distance(approx: "np.ndarray", exact: "np.ndarray") -> float:
    """Mean total variation distance between approx and exact marginals.

    TV(q_i, p*_i) = 0.5 * sum_s |q_i(s) - p*_i(s)|, averaged over variables.

    Parameters
    ----------
    approx, exact : np.ndarray shape (n_vars, 2)
    """
    import numpy as np
    return float(0.5 * np.abs(approx - exact).sum(axis=1).mean())


def tv_distance_max(approx: "np.ndarray", exact: "np.ndarray") -> float:
    """Max (worst-case) total variation distance over variables.

    TV_max = max_i [ 0.5 * sum_s |q_i(s) - p*_i(s)| ]

    This is the structural gap detector: the over-authorization region is
    exactly the (tau, beta) pairs where tv_distance <= tau < tv_distance_max.
    """
    import numpy as np
    return float(0.5 * np.abs(approx - exact).sum(axis=1).max())
