"""ILS permission profiles — native ILS chain, FAA category names supplied
directly as level names.

Gaps:
  ils_signal_integrity   — f1: ILS guidance signal is valid
  visual_reference       — f2: RVR adequate for visual reference at DH
  sub_cat1_authorization — f3: operator authorization for sub-CAT-I operations

Permission chain (declared explicitly; no translation to a generic chain):
  REFUSE_APPROACH     — structural refusal (membership failure, blocked credential)
  CONTINUE_APPROACH   — guidance available; remain above safe altitude
  DESCEND_TO_DH       — follow glideslope to DH; do not commit to landing
  LAND_MANUAL         — commit to landing on visual reference at DH
  LAND_ASSISTED       — commit with certified guidance assistance; reduced visual
  LAND_ZERO_ZERO      — land with no DH and no minimum visual reference

Bijection from the pre-rewrite default chain (used to verify §7.2):
    OOC ↔ REFUSE_APPROACH   (membership-failure folding; never exercised by sweeps)
    REF ↔ REFUSE_APPROACH   (structural-blocker folding; never exercised either)
    UNS ↔ CONTINUE_APPROACH  (unsatisfied profile)
    DIA ↔ DESCEND_TO_DH
    REV ↔ LAND_MANUAL
    AEX ↔ LAND_ASSISTED
    ALR ↔ LAND_ZERO_ZERO
"""
from __future__ import annotations

import sys
from pathlib import Path

_WORKSPACE_PY = Path(__file__).resolve().parents[2] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

import noethers_turnstile as t

GAP_SIGNAL    = "ils_signal_integrity"
GAP_VISUAL    = "visual_reference"
GAP_AUTH      = "sub_cat1_authorization"

GAP_TYPE_SIGNAL = "ils_signal_integrity_gap"
GAP_TYPE_VISUAL = "visual_reference_gap"
GAP_TYPE_AUTH   = "sub_cat1_authorization_gap"

# ── Native ILS chain ─────────────────────────────────────────────────────────

_ILS_LEVELS = [
    "REFUSE_APPROACH",
    "CONTINUE_APPROACH",
    "DESCEND_TO_DH",
    "LAND_MANUAL",
    "LAND_ASSISTED",
    "LAND_ZERO_ZERO",
]

# Collapsed below-threshold roles: REFUSE_APPROACH absorbs membership-failure,
# expiry-floor, structural-refusal targets. CONTINUE_APPROACH carries the
# unsatisfied-but-profile-defined branch (UNS analogue), so an unmet profile
# emits CONTINUE_APPROACH rather than collapsing to REFUSE_APPROACH.
ILS_CHAIN = t.PermissionChain.new(
    levels=_ILS_LEVELS,
    roles={
        t.ChainRole.Bottom: 0,                  # REFUSE_APPROACH
        t.ChainRole.ExpiryFloor: 0,             # REFUSE_APPROACH (collapsed)
        t.ChainRole.Refused: 0,                 # REFUSE_APPROACH (collapsed)
        t.ChainRole.Unsatisfied: 1,             # CONTINUE_APPROACH (operational fallback)
        t.ChainRole.DisallowedUsesCeiling: 0,   # REFUSE_APPROACH; never exercised
                                                # (ILS contexts have no disallowed_uses)
        t.ChainRole.BlockerThreshold: 2,        # DESCEND_TO_DH
        t.ChainRole.Top: 5,                     # LAND_ZERO_ZERO
    },
)


# Domain-named permission objects, looked up from the declared chain.
PERM_REFUSE   = ILS_CHAIN.parse("REFUSE_APPROACH")
PERM_CONTINUE = ILS_CHAIN.parse("CONTINUE_APPROACH")
PERM_DESCEND  = ILS_CHAIN.parse("DESCEND_TO_DH")
PERM_MANUAL   = ILS_CHAIN.parse("LAND_MANUAL")
PERM_ASSISTED = ILS_CHAIN.parse("LAND_ASSISTED")
PERM_ZERO     = ILS_CHAIN.parse("LAND_ZERO_ZERO")


# Bijection table from the pre-rewrite default-chain emits to the new domain
# names. Used by tests/verify_ils.py to map golden emits to expected new emits.
BIJECTION = {
    "OOC": "REFUSE_APPROACH",
    "REF": "REFUSE_APPROACH",
    "UNS": "CONTINUE_APPROACH",
    "DIA": "DESCEND_TO_DH",
    "REV": "LAND_MANUAL",
    "AEX": "LAND_ASSISTED",
    "ALR": "LAND_ZERO_ZERO",
}


def build_profiles() -> list[t.Profile]:
    """Return the four permission profiles in descending order.

    LAND_ZERO_ZERO:
      f1 clear, f3 clear — no visual constraint; full certification required.

    LAND_ASSISTED:
      f1 clear, f3 clear — autoland substitutes for visual reference.
      f2 NOT required: the constraint type changes from visual-geometric
      to system-certification at this level.

    LAND_MANUAL:
      f1 clear, f2 clear — visual reference must be adequate at DH.

    DESCEND_TO_DH:
      f1 clear only — may descend with valid ILS signal; do not commit.

    Note: LAND_ASSISTED and LAND_ZERO_ZERO have identical gap requirements in
    the historical ILS code. Descending search returns the higher (LAND_ZERO_ZERO)
    whenever both are satisfied, so LAND_ASSISTED is structurally unreachable
    on this gap taxonomy. Kept for completeness — domain authors may distinguish
    them via additional gap requirements in a later iteration.
    """
    return [
        t.Profile(
            PERM_ZERO,
            [
                t.GapRequirement(GAP_SIGNAL, "closed"),
                t.GapRequirement(GAP_AUTH,   "closed"),
            ],
        ),
        t.Profile(
            PERM_ASSISTED,
            [
                t.GapRequirement(GAP_SIGNAL, "closed"),
                t.GapRequirement(GAP_AUTH,   "closed"),
            ],
        ),
        t.Profile(
            PERM_MANUAL,
            [
                t.GapRequirement(GAP_SIGNAL, "closed"),
                t.GapRequirement(GAP_VISUAL, "closed"),
            ],
        ),
        t.Profile(
            PERM_DESCEND,
            [
                t.GapRequirement(GAP_SIGNAL, "closed"),
            ],
        ),
    ]
