"""Admissibility compiler for turbo code decoding results.

This is the same compiler as Register 1, instantiated with the permission
vocabulary appropriate for a communications system. The structure is identical:
a failure vector, a threshold scan, and a judgment.

Permission chain (3GPP TS 36.212 §5.1.3 thresholds, voice/data standards):
  TRANSMIT          — BER ≤ 10^-5 and/or BLER ≤ 10^-3  (voice: BER; data: BLER)
  TRANSMIT_MONITORED — BER ≤ 10^-3 and/or BLER ≤ 10^-1  (monitoring, flag-on-fail)
  HOLD              — above TRANSMIT_MONITORED threshold
  REFUSE            — channel too poor, no reliable communication

Failure vector:
  f1: convergence_failure    — turbo decoder iterations did not converge
                               (structural analogue of BP non-convergence)
                               For published curves: always False (curves are converged)
  f2: ber_exceeds_threshold  — d_BER > τ_BER
  f3: bler_exceeds_threshold — d_BLER > τ_BLER

The gap is the SNR interval where f2 is False (BER acceptable) but f3 is True
(BLER still unacceptable). This is the structural analogue of the Register 1
gap: d1 (mean TV) clears while d2 (max TV) blocks.

Analogy:
  d_BER  ≡  d1 (mean TV):  averages bit errors over the block, hides block failures
  d_BLER ≡  d2 (max TV):   a block fails if any bit fails — worst-case component
"""
from __future__ import annotations

from dataclasses import dataclass

# Permission levels (ordered: REFUSE < HOLD < TRANSMIT_MONITORED < TRANSMIT)
TRANSMIT           = 3
TRANSMIT_MONITORED = 2
HOLD               = 1
REFUSE             = 0

PERMISSION_NAMES = {
    TRANSMIT:            "TRANSMIT",
    TRANSMIT_MONITORED:  "TRANSMIT_MONITORED",
    HOLD:                "HOLD",
    REFUSE:              "REFUSE",
}

# Standard operating thresholds (3GPP / Proakis conventions)
# τ_BER: bit error rate threshold per permission level
# τ_BLER: block error rate threshold per permission level
TAU_BER = {
    TRANSMIT:           1e-5,   # voice communication standard
    TRANSMIT_MONITORED: 1e-3,   # monitoring threshold
    HOLD:               1.0,    # effectively no BER threshold — BLER carries the signal
}
TAU_BLER = {
    TRANSMIT:           1e-3,   # data transmission standard
    TRANSMIT_MONITORED: 1e-1,   # 10% block failure rate — monitor and flag
    HOLD:               1.0,    # above monitored — hold
}


@dataclass
class TurboFailureVector:
    convergence_failure: bool  # f1 — structural analogue of BP non-convergence
    ber_exceeds_transmit: bool          # d_BER > τ(TRANSMIT)
    ber_exceeds_monitored: bool         # d_BER > τ(TRANSMIT_MONITORED)
    bler_exceeds_transmit: bool         # d_BLER > τ(TRANSMIT)
    bler_exceeds_monitored: bool        # d_BLER > τ(TRANSMIT_MONITORED)

    @classmethod
    def from_run(cls, converged: bool, ber: float, bler: float) -> "TurboFailureVector":
        if not converged:
            return cls(True, True, True, True, True)
        return cls(
            convergence_failure=False,
            ber_exceeds_transmit=ber > TAU_BER[TRANSMIT],
            ber_exceeds_monitored=ber > TAU_BER[TRANSMIT_MONITORED],
            bler_exceeds_transmit=bler > TAU_BLER[TRANSMIT],
            bler_exceeds_monitored=bler > TAU_BLER[TRANSMIT_MONITORED],
        )


@dataclass
class TurboCompilerResult:
    permission: int
    permission_name: str
    failure_vector: TurboFailureVector
    ber: float
    bler: float
    functional_used: str  # "BER", "BLER", or "both"
    blocking_reasons: list[str]


def compile_turbo(
    converged: bool,
    ber: float,
    bler: float,
    functional: str = "BER",
) -> TurboCompilerResult:
    """Emit the strongest permission the channel supports.

    functional: "BER" uses only d_BER; "BLER" uses only d_BLER; "both" requires both.
    This is how we separate the two functionals to expose the gap.
    """
    fv = TurboFailureVector.from_run(converged, ber, bler)
    blocking: list[str] = []

    if fv.convergence_failure:
        return TurboCompilerResult(REFUSE, "REFUSE", fv, ber, bler, functional,
                                   ["convergence_failure"])

    def ber_blocks(level: int) -> bool:
        return fv.ber_exceeds_transmit if level == TRANSMIT else fv.ber_exceeds_monitored

    def bler_blocks(level: int) -> bool:
        return fv.bler_exceeds_transmit if level == TRANSMIT else fv.bler_exceeds_monitored

    for level in [TRANSMIT, TRANSMIT_MONITORED, HOLD]:
        obstructed = False
        reasons: list[str] = []
        if functional in ("BER", "both") and ber_blocks(level):
            obstructed = True
            reasons.append(f"ber_exceeds_{PERMISSION_NAMES[level].lower()}")
        if functional in ("BLER", "both") and bler_blocks(level):
            obstructed = True
            reasons.append(f"bler_exceeds_{PERMISSION_NAMES[level].lower()}")
        if not obstructed:
            return TurboCompilerResult(level, PERMISSION_NAMES[level], fv, ber, bler,
                                       functional, [])
        if level == TRANSMIT:
            blocking = reasons

    return TurboCompilerResult(REFUSE, "REFUSE", fv, ber, bler, functional, blocking)


def compile_at_tau_turbo(
    converged: bool,
    d_val: float,
    tau: float,
) -> int:
    """Single-threshold binary compiler for threshold sweep (same API as Register 1)."""
    if not converged:
        return REFUSE
    return TRANSMIT if d_val <= tau else REFUSE
