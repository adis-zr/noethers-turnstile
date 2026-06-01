"""ILS approach lighting geometry — physical floor derivation.

All values derived from engineering geometry before any FAA document is
consulted. The roll bar position (1,000 ft before threshold) is from
AC 150/5340-30 (approach lighting system design standard), not from
approach minimums documentation.

Constants
---------
GLIDESLOPE_DEG   : 3.0° — standard ILS glideslope angle
TCH              : 50 ft — standard ILS threshold crossing height
ROLL_BAR_DIST    : 1,000 ft before threshold — ALSF-2 roll bar position

Derivation
----------
On a 3° glideslope with TCH = 50 ft, at decision height H (ft AGL):

  d_thresh = (H - TCH) / tan(3°)     # horizontal distance before threshold
  d_rb     = d_thresh - ROLL_BAR_DIST # horizontal distance from aircraft to roll bar
  RVR_floor(H) = max(0, d_rb)

The roll bar is the minimum adequate visual reference for runway environment
acquisition at the decision point [FAA/AR-02-81]. The physical floor for
unaided manual landing is the RVR at which the roll bar is just visible.

Saturation: when d_rb <= 0 the aircraft has already passed the roll bar at
decision height. The roll bar visual constraint no longer applies.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

GLIDESLOPE_DEG: float = 3.0
TCH: float = 50.0          # ft AGL
ROLL_BAR_DIST: float = 1000.0  # ft before threshold

APPROACH_SPEED_KT: float = 130.0  # representative jet approach speed


@dataclass(frozen=True)
class GeometryResult:
    dh_ft: float
    rvr_floor_ft: float
    d_thresh_ft: float
    d_rb_ft: float
    saturated: bool


def rvr_floor(dh_ft: float) -> GeometryResult:
    """Compute the physical RVR floor at a given decision height."""
    gs_rad = math.radians(GLIDESLOPE_DEG)
    d_thresh = (dh_ft - TCH) / math.tan(gs_rad)
    d_rb = d_thresh - ROLL_BAR_DIST
    saturated = d_rb <= 0.0
    return GeometryResult(
        dh_ft=dh_ft,
        rvr_floor_ft=max(0.0, d_rb),
        d_thresh_ft=d_thresh,
        d_rb_ft=d_rb,
        saturated=saturated,
    )


def saturation_dh() -> float:
    """DH at which the roll bar constraint saturates (d_rb = 0)."""
    gs_rad = math.radians(GLIDESLOPE_DEG)
    return TCH + ROLL_BAR_DIST * math.tan(gs_rad)


def dh_at_rvr_floor(target_rvr_ft: float) -> float:
    """DH that produces a given RVR floor from the geometric curve."""
    gs_rad = math.radians(GLIDESLOPE_DEG)
    return TCH + (target_rvr_ft + ROLL_BAR_DIST) * math.tan(gs_rad)


def time_to_threshold(dh_ft: float, speed_kt: float = APPROACH_SPEED_KT) -> float:
    """Seconds from decision height to threshold crossing on a 3° glideslope.

    Uses the threshold crossing (TCH point) as the reference, not touchdown.
    This is the correct reference for visual acquisition time: the pilot must
    identify the runway environment and commit before passing the threshold.
    """
    gs_rad = math.radians(GLIDESLOPE_DEG)
    speed_fps = speed_kt * 6076.12 / 3600.0
    horiz_dist = (dh_ft - TCH) / math.tan(gs_rad)
    return horiz_dist / speed_fps


def preregistration_values() -> dict:
    """All values to be written to the pre-registration file.

    Called before any FAA document is opened.
    """
    cat1_geo = rvr_floor(200.0)
    h_sat = saturation_dh()
    h_at_1800 = dh_at_rvr_floor(1800.0)
    cat2_geo = rvr_floor(100.0)
    t_cat1 = time_to_threshold(200.0)
    t_cat2 = time_to_threshold(100.0)

    return {
        "glideslope_deg": GLIDESLOPE_DEG,
        "tch_ft": TCH,
        "roll_bar_dist_ft": ROLL_BAR_DIST,
        "approach_speed_kt": APPROACH_SPEED_KT,
        "rvr_floor_at_dh200_ft": cat1_geo.rvr_floor_ft,
        "dh_at_rvr1800_ft": h_at_1800,
        "saturation_dh_ft": h_sat,
        "rvr_floor_at_dh100_ft": cat2_geo.rvr_floor_ft,
        "dh100_saturated": cat2_geo.saturated,
        "time_to_threshold_cat1_sec": t_cat1,
        "time_to_threshold_cat2_sec": t_cat2,
        "predicted_sweep_a_transition_rvr_ft": 1800,
        "predicted_sweep_b_sub_boundaries": False,
        "predicted_cat1_classification": "EXACT",
        "predicted_cat2_classification": "OFFSET_DIFFERENT_AXIS",
        "predicted_cat3a_classification": "COMPILER_PERMISSIVE",
        "predicted_cat3b_classification": "COMPILER_PERMISSIVE",
        "predicted_cat3c_classification": "COMPILER_PERMISSIVE",
    }
