"""Blind 5-level permission chain for the 3GPP audit experiment.

Phase B chain — REFUSE < HOLD < TRANSMIT_MONITORED < TRANSMIT_DATA <
TRANSMIT_CRITICAL — declared via the library's PermissionChain
(TURBO_PHASE_B_CHAIN below). The internal compile path still uses integer
codes for sweep performance; auditors can look up the corresponding
PermissionChain level via TURBO_PHASE_B_CHAIN.parse(PERMISSION_NAMES[code]).

Bijection (identity on level names; integer encoding for sweep performance):
  REFUSE              ↔ chain.parse("REFUSE")
  HOLD                ↔ chain.parse("HOLD")
  TRANSMIT_MONITORED  ↔ chain.parse("TRANSMIT_MONITORED")
  TRANSMIT_DATA       ↔ chain.parse("TRANSMIT_DATA")
  TRANSMIT_CRITICAL   ↔ chain.parse("TRANSMIT_CRITICAL")


Specified by operational meaning only. No 3GPP threshold values appear here.
The τ values that map operations to permission levels are NOT set in this file —
they are discovered by the sweep from the gap geometry. This is Phase B of the
blind audit. Do not read 3GPP documents before running the sweep.

Permission chain (derived from first principles):

  p4  TRANSMIT_CRITICAL   — block used for safety-critical or real-time control
  p3  TRANSMIT_DATA       — block used for data transfer, file, or stream
  p2  TRANSMIT_MONITORED  — block transmitted with mandatory retransmission on failure
  p1  HOLD                — do not transmit; request better channel
  p0  REFUSE              — channel too poor for any licensed transmission

Structural note: 5 levels because the gap geometry may contain 5 natural
boundaries. Forcing 4 levels pre-loads the outcome.

Cross-register chain (Phase A) is in compiler_turbo.py. This file is Phase B only.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

_WORKSPACE_PY = Path(__file__).resolve().parents[4] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

import noethers_turnstile as t  # noqa: E402

# ── Native Phase-B chain ─────────────────────────────────────────────────────

_TURBO_PHASE_B_LEVELS = [
    "REFUSE", "HOLD", "TRANSMIT_MONITORED", "TRANSMIT_DATA", "TRANSMIT_CRITICAL",
]

TURBO_PHASE_B_CHAIN = t.PermissionChain.new(
    levels=_TURBO_PHASE_B_LEVELS,
    roles={
        t.ChainRole.Bottom: 0,
        t.ChainRole.ExpiryFloor: 0,
        t.ChainRole.Refused: 0,
        t.ChainRole.Unsatisfied: 0,
        t.ChainRole.DisallowedUsesCeiling: 0,
        t.ChainRole.BlockerThreshold: 1,
        t.ChainRole.Top: 4,
    },
)

# Permission levels (ordered: REFUSE < HOLD < TRANSMIT_MONITORED < TRANSMIT_DATA < TRANSMIT_CRITICAL)
TRANSMIT_CRITICAL  = 4
TRANSMIT_DATA      = 3
TRANSMIT_MONITORED = 2
HOLD               = 1
REFUSE             = 0

PERMISSION_NAMES = {
    TRANSMIT_CRITICAL:  "TRANSMIT_CRITICAL",
    TRANSMIT_DATA:      "TRANSMIT_DATA",
    TRANSMIT_MONITORED: "TRANSMIT_MONITORED",
    HOLD:               "HOLD",
    REFUSE:             "REFUSE",
}

# Threshold placeholders — to be filled after the blind sweep identifies
# natural boundaries. Set to None so any attempt to use them before Phase 2
# raises explicitly.
TAU_BLIND: dict[int, float | None] = {
    TRANSMIT_CRITICAL:  None,
    TRANSMIT_DATA:      None,
    TRANSMIT_MONITORED: None,
    HOLD:               None,
}


def compile_at_tau_blind(d_val: float, tau: float) -> int:
    """Single-threshold binary compiler for the blind sweep.

    Same API as compile_at_tau_turbo. d_val is either BER or BLER — the caller
    decides which functional to use. The compiler does not know.

    Returns TRANSMIT_CRITICAL (highest) if d_val <= tau, else REFUSE (lowest).
    The multi-level assignment is done by the sweep itself, which runs this
    function across all τ values and finds the highest level τ that d_val clears.
    """
    return TRANSMIT_CRITICAL if d_val <= tau else REFUSE


def permission_from_d(d_val: float, tau_chain: list[tuple[int, float]]) -> int:
    """Map a divergence value to a permission level given an ordered threshold chain.

    tau_chain: list of (permission_level, tau_value) in descending permission order.
    Returns the highest level whose tau d_val clears, else REFUSE.

    Example:
        tau_chain = [
            (TRANSMIT_CRITICAL,  0.001),
            (TRANSMIT_DATA,      0.01),
            (TRANSMIT_MONITORED, 0.05),
            (HOLD,               0.30),
        ]
    """
    for level, tau in tau_chain:
        if d_val <= tau:
            return level
    return REFUSE


def make_tau_chain(tau_critical: float, tau_data: float,
                   tau_monitored: float, tau_hold: float) -> list[tuple[int, float]]:
    """Construct a threshold chain from discovered natural boundary values."""
    return [
        (TRANSMIT_CRITICAL,  tau_critical),
        (TRANSMIT_DATA,      tau_data),
        (TRANSMIT_MONITORED, tau_monitored),
        (HOLD,               tau_hold),
    ]
