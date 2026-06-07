"""Conservation paper-5-level chain (REF < DIA < REV < AEX < ALR).

Per spec §11 Q3 Option A and pivot-paper-v5 §2.2 line 140. Membership failure
folds to chain.role(Bottom) = REF; `OOC -> REF` in the bijection.
"""
from __future__ import annotations

import sys
from pathlib import Path

_WORKSPACE_PY = Path(__file__).resolve().parents[2] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

import noethers_turnstile as t

_CONSERVATION_LEVELS = ["REF", "DIA", "REV", "AEX", "ALR"]

CONSERVATION_CHAIN = t.PermissionChain.new(
    levels=_CONSERVATION_LEVELS,
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

# Bijection from any default-chain emit to this paper chain.
# OOC -> REF folding (Q3 Option A): membership-failure maps to the chain's
# bottom (refusal).
BIJECTION = {
    "OOC": "REF",
    "EXP": "REF",
    "REF": "REF",
    "UNS": "REF",
    "ETA": "DIA",
    "ESC": "DIA",
    "ROL": "DIA",
    "DIA": "DIA",
    "REV": "REV",
    "AEX": "AEX",
    "ALR": "ALR",
    "AAA": "ALR",
}

PERM_REF = CONSERVATION_CHAIN.parse("REF")
PERM_DIA = CONSERVATION_CHAIN.parse("DIA")
PERM_REV = CONSERVATION_CHAIN.parse("REV")
PERM_AEX = CONSERVATION_CHAIN.parse("AEX")
PERM_ALR = CONSERVATION_CHAIN.parse("ALR")
