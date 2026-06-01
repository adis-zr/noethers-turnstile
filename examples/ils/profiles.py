"""ILS permission profiles — defined by operational meaning, no FAA thresholds.

Profiles are constructed from three gap IDs:
  ils_signal_integrity   — f1: ILS guidance signal is valid
  visual_reference       — f2: RVR adequate for visual reference at DH
  sub_cat1_authorization — f3: operator authorization for sub-CAT-I operations

Permission chain (operational meaning only, no FAA category names):
  CONTINUE_APPROACH   — guidance available; remain above safe altitude
  DESCEND_TO_DH       — follow glideslope to DH; do not commit to landing
  LAND_MANUAL         — commit to landing on visual reference at DH
  LAND_ASSISTED       — commit with certified guidance assistance; reduced visual
  LAND_ZERO_ZERO      — land with no DH and no minimum visual reference
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

PERM_DESCEND  = t.Permission.DIA   # DESCEND_TO_DH
PERM_MANUAL   = t.Permission.REV   # LAND_MANUAL
PERM_ASSISTED = t.Permission.AEX   # LAND_ASSISTED
PERM_ZERO     = t.Permission.ALR   # LAND_ZERO_ZERO


def build_profiles() -> list[t.Profile]:
    """Return the four permission profiles in descending order.

    LAND_ZERO_ZERO (ALR):
      f1 clear, f3 clear — no visual constraint; full certification required.

    LAND_ASSISTED (AEX):
      f1 clear, f3 clear — autoland substitutes for visual reference.
      f2 NOT required: the constraint type changes from visual-geometric
      to system-certification at this level.

    LAND_MANUAL (REV):
      f1 clear, f2 clear — visual reference must be adequate at DH.

    DESCEND_TO_DH (DIA):
      f1 clear only — may descend with valid ILS signal; do not commit.
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
