"""Admissibility compiler for turbo code decoding results.

Phase A of the 3GPP audit. Phase B (5-level) lives in compiler_blind.py.

Native turbo Phase-A chain — REFUSE < HOLD < TRANSMIT_MONITORED < TRANSMIT —
is declared via the library's PermissionChain (see TURBO_PHASE_A_CHAIN below)
so a downstream auditor receives judgments with a chain_hash they can pin to
this script.

The internal compile_turbo() function continues to use integer codes + a
threshold-scan implementation for backwards compatibility with sweep_turbo.py
and audit_3gpp.py, which downstream-consume the integer codes. The integer
codes correspond 1:1 with the named levels via PERMISSION_NAMES below;
auditors who want the native chain's level objects can call
TURBO_PHASE_A_CHAIN.parse(PERMISSION_NAMES[level]).

Bijection (identity on level NAMES; integer encoding for sweep performance):
  REFUSE             ↔ chain.parse("REFUSE")
  HOLD               ↔ chain.parse("HOLD")
  TRANSMIT_MONITORED ↔ chain.parse("TRANSMIT_MONITORED")
  TRANSMIT           ↔ chain.parse("TRANSMIT")

Permission chain (3GPP TS 36.212 §5.1.3 thresholds, voice/data standards):
  TRANSMIT          — BER ≤ 10^-5 and/or BLER ≤ 10^-3  (voice: BER; data: BLER)
  TRANSMIT_MONITORED — BER ≤ 10^-3 and/or BLER ≤ 10^-1  (monitoring, flag-on-fail)
  HOLD              — above TRANSMIT_MONITORED threshold
  REFUSE            — channel too poor, no reliable communication

Failure vector:
  f1: convergence_failure    — turbo decoder iterations did not converge
  f2: ber_exceeds_threshold  — d_BER > τ_BER
  f3: bler_exceeds_threshold — d_BLER > τ_BLER
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

_WORKSPACE_PY = Path(__file__).resolve().parents[4] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

import noethers_turnstile as t  # noqa: E402

# ── Native Phase-A chain ─────────────────────────────────────────────────────

_TURBO_PHASE_A_LEVELS = ["REFUSE", "HOLD", "TRANSMIT_MONITORED", "TRANSMIT"]

TURBO_PHASE_A_CHAIN = t.PermissionChain.new(
    levels=_TURBO_PHASE_A_LEVELS,
    roles={
        t.ChainRole.Bottom: 0,                  # REFUSE
        t.ChainRole.ExpiryFloor: 0,
        t.ChainRole.Refused: 0,
        t.ChainRole.Unsatisfied: 0,
        t.ChainRole.DisallowedUsesCeiling: 0,
        t.ChainRole.BlockerThreshold: 1,        # HOLD
        t.ChainRole.Top: 3,                     # TRANSMIT
    },
)

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
