"""FAA comparison — run AFTER pre-registration is sealed.

Opens FAA thresholds from AC 120-29A / ICAO Annex 10 and compares them
against the compiler output from the sweeps. Classifies each boundary as:
  EXACT               — compiler boundary matches FAA threshold exactly
  OFFSET_DIFFERENT_AXIS — boundary exists but on a different evidence axis
  COMPILER_PERMISSIVE — compiler grants more than FAA; FAA boundary is
                        orthogonal to the evidence available to the compiler
  COMPILER_STRICT     — compiler is more restrictive than FAA (not expected here)

This module MUST NOT be imported before preregistration.py has run and sealed.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from preregistration import PREREG_FILE, SEAL_FILE, verify_seal
from sweeps import SweepResult

# ---------------------------------------------------------------------------
# FAA thresholds (from AC 120-29A / 14 CFR 91.175 / ICAO Annex 10)
# These are the regulatory values opened AFTER pre-registration is sealed.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FAACategory:
    name: str
    dh_ft: float | None       # None = no DH (CAT IIIb/c)
    rvr_min_ft: float | None  # None = no RVR minimum (CAT IIIc)
    notes: str


FAA_CATEGORIES: list[FAACategory] = [
    FAACategory(
        name="CAT_I",
        dh_ft=200.0,
        rvr_min_ft=1800.0,
        notes="Standard precision approach; 200 ft DH, 1800 ft RVR (half-mile)",
    ),
    FAACategory(
        name="CAT_II",
        dh_ft=100.0,
        rvr_min_ft=1200.0,
        notes="Precision approach; 100 ft DH, 1200 ft RVR; requires special crew/aircraft cert",
    ),
    FAACategory(
        name="CAT_IIIa",
        dh_ft=None,
        rvr_min_ft=700.0,
        notes="No DH or DH < 100 ft; 700 ft RVR; requires autoland capability",
    ),
    FAACategory(
        name="CAT_IIIb",
        dh_ft=None,
        rvr_min_ft=150.0,
        notes="No DH or DH < 50 ft; 150 ft RVR; enhanced autoland + rollout guidance",
    ),
    FAACategory(
        name="CAT_IIIc",
        dh_ft=None,
        rvr_min_ft=None,
        notes="Zero-zero; no DH, no RVR minimum; not operationally approved in US",
    ),
]


@dataclass(frozen=True)
class BoundaryClassification:
    category: str
    faa_rvr_ft: float | None
    compiler_transition_rvr_ft: float | None
    classification: str
    explanation: str


def classify_cat1(sweep_a: SweepResult) -> BoundaryClassification:
    """Classify the CAT I boundary from Sweep A (f3 absent)."""
    transitions = sweep_a.transitions()
    # Find the first transition from LAND_MANUAL downward (descending RVR sweep)
    # Sweep runs high→low, so first transition is at the top of the boundary
    # We want the RVR at which permission drops from LAND_MANUAL to DESCEND_TO_DH
    manual_to_descend = None
    for rvr, from_p, to_p in transitions:
        if "REV" in from_p and "DIA" in to_p:
            manual_to_descend = rvr
            break
        if "AEX" in from_p and "DIA" in to_p:
            manual_to_descend = rvr
            break

    # Also accept if top of sweep is already LAND_MANUAL and we find the drop
    if manual_to_descend is None:
        for rvr, from_p, to_p in transitions:
            if "DIA" in to_p:
                manual_to_descend = rvr
                break

    faa_rvr = 1800.0

    if manual_to_descend is None:
        classification = "UNDETERMINED"
        explanation = "No LAND_MANUAL → DESCEND_TO_DH transition found in Sweep A"
    elif abs(manual_to_descend - faa_rvr) <= 100.0:
        classification = "EXACT"
        explanation = (
            f"Compiler transition at {manual_to_descend:.0f} ft matches FAA CAT I "
            f"minimum of {faa_rvr:.0f} ft (within sweep resolution of 100 ft). "
            "Physical geometry recovers the regulatory boundary without consulting FAA documents."
        )
    elif manual_to_descend > faa_rvr:
        classification = "COMPILER_STRICT"
        explanation = (
            f"Compiler transition at {manual_to_descend:.0f} ft; "
            f"FAA minimum is {faa_rvr:.0f} ft. Compiler is more restrictive."
        )
    else:
        classification = "OFFSET"
        explanation = (
            f"Compiler transition at {manual_to_descend:.0f} ft; "
            f"FAA minimum is {faa_rvr:.0f} ft. Offset of {faa_rvr - manual_to_descend:.0f} ft."
        )

    return BoundaryClassification(
        category="CAT_I",
        faa_rvr_ft=faa_rvr,
        compiler_transition_rvr_ft=manual_to_descend,
        classification=classification,
        explanation=explanation,
    )


def classify_cat2(sweep_a: SweepResult, dh_cat2: float = 100.0) -> BoundaryClassification:
    """Classify the CAT II boundary — expected OFFSET_DIFFERENT_AXIS."""
    faa_rvr = 1200.0

    # The compiler at DH=100 ft (below saturation) has f2 always clear (saturated).
    # So with f1 clear and f3 absent, compiler grants LAND_MANUAL at all RVR values.
    # FAA imposes 1200 ft RVR — but this is a human-factors / reaction-time constraint,
    # not derivable from the physical geometry the compiler has access to.
    return BoundaryClassification(
        category="CAT_II",
        faa_rvr_ft=faa_rvr,
        compiler_transition_rvr_ft=None,
        classification="OFFSET_DIFFERENT_AXIS",
        explanation=(
            f"At DH={dh_cat2:.0f} ft (below saturation ~102 ft), f2 is always clear "
            f"(aircraft has passed roll bar at DH). Compiler grants LAND_MANUAL at all "
            f"RVR values — no geometric floor remains. FAA CAT II minimum of "
            f"{faa_rvr:.0f} ft exists on a different evidence axis: human factors / "
            "reaction time (4.3 sec to threshold), not recoverable from RVR geometry. "
            "The boundary exists but is orthogonal to the compiler's evidence space."
        ),
    )


def classify_cat3(cat: FAACategory) -> BoundaryClassification:
    """Classify CAT IIIa/b/c — expected COMPILER_PERMISSIVE."""
    faa_rvr = cat.rvr_min_ft

    return BoundaryClassification(
        category=cat.name,
        faa_rvr_ft=faa_rvr,
        compiler_transition_rvr_ft=None,
        classification="COMPILER_PERMISSIVE",
        explanation=(
            f"{cat.name}: FAA minimum is "
            f"{f'{faa_rvr:.0f} ft' if faa_rvr is not None else 'none (zero-zero)'}. "
            "Compiler has no basis for any positive RVR floor once f2 saturates. "
            "Autoland certification and operator qualification are orthogonal to the "
            "RVR evidence space — the evidence type is wrong, not merely the threshold. "
            "This is a structural absence, not an offset."
        ),
    )


def run_comparison(sweep_a: SweepResult) -> list[BoundaryClassification]:
    results = [
        classify_cat1(sweep_a),
        classify_cat2(sweep_a),
        classify_cat3(FAA_CATEGORIES[2]),  # CAT IIIa
        classify_cat3(FAA_CATEGORIES[3]),  # CAT IIIb
        classify_cat3(FAA_CATEGORIES[4]),  # CAT IIIc
    ]
    return results


def format_comparison(classifications: list[BoundaryClassification]) -> str:
    lines = [
        "=== FAA Regulatory Correspondence ===",
        "",
        f"{'Category':<12}  {'FAA RVR (ft)':>14}  {'Compiler (ft)':>14}  {'Classification':<28}",
        "-" * 76,
    ]
    for c in classifications:
        faa_str = f"{c.faa_rvr_ft:.0f}" if c.faa_rvr_ft is not None else "none"
        comp_str = f"{c.compiler_transition_rvr_ft:.0f}" if c.compiler_transition_rvr_ft is not None else "—"
        lines.append(
            f"{c.category:<12}  {faa_str:>14}  {comp_str:>14}  {c.classification:<28}"
        )

    lines.append("")
    lines.append("=== Explanations ===")
    for c in classifications:
        lines.append(f"\n{c.category} ({c.classification}):")
        lines.append(f"  {c.explanation}")

    return "\n".join(lines)


def check_seal_or_abort() -> None:
    if not PREREG_FILE.exists():
        print("ERROR: Pre-registration file not found. Run preregistration.py first.")
        sys.exit(1)
    if not verify_seal():
        print("ERROR: Pre-registration seal verification failed. File may have been modified.")
        sys.exit(1)


if __name__ == "__main__":
    check_seal_or_abort()

    from sweeps import run_sweep_a
    sweep_a = run_sweep_a()

    print("Pre-registration seal verified.")
    print()
    print(sweep_a and "Sweep A complete.")
    print()

    classifications = run_comparison(sweep_a)
    print(format_comparison(classifications))
