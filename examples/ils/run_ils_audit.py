"""ILS blind audit entry point.

Orchestrates the full audit sequence in order:
  1. Write and seal pre-registration (geometry-only predictions)
  2. Run Sweep A (f3 absent) and Sweep B (f3 present)
  3. Open FAA thresholds and classify each boundary
  4. Write REPORT.md from actual compiler output

Usage:
  python run_ils_audit.py [--force]

  --force: delete existing pre-registration and seal before running
           (use only if you are intentionally re-running from scratch)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_WORKSPACE_PY = Path(__file__).resolve().parents[2] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

from preregistration import (
    PREREG_FILE, SEAL_FILE,
    write_preregistration, verify_seal,
)
from sweeps import run_sweep_a, run_sweep_b, format_sweep
from faa_comparison import run_comparison, format_comparison, check_seal_or_abort
from geometry import preregistration_values

REPORT_FILE = Path(__file__).parent / "REPORT.md"


def step1_preregister(force: bool = False) -> None:
    if force:
        PREREG_FILE.unlink(missing_ok=True)
        SEAL_FILE.unlink(missing_ok=True)

    if PREREG_FILE.exists():
        if not verify_seal():
            print("ERROR: Existing pre-registration seal is invalid.")
            sys.exit(1)
        print(f"Step 1: Pre-registration already sealed at {PREREG_FILE}")
    else:
        write_preregistration()
        print(f"Step 1: Pre-registration sealed at {PREREG_FILE}")


def step2_sweeps():
    print("Step 2: Running sweeps...")
    sweep_a = run_sweep_a()
    sweep_b = run_sweep_b()
    print(format_sweep(sweep_a))
    print()
    print(format_sweep(sweep_b))
    return sweep_a, sweep_b


def step3_compare(sweep_a):
    print("\nStep 3: FAA comparison...")
    check_seal_or_abort()
    classifications = run_comparison(sweep_a)
    print(format_comparison(classifications))
    return classifications


def step4_report(sweep_a, sweep_b, classifications) -> Path:
    print(f"\nStep 4: Writing {REPORT_FILE}...")
    geo = preregistration_values()

    now = datetime.now(timezone.utc).isoformat()
    prereg = json.loads(PREREG_FILE.read_text())
    sealed_at = prereg.get("sealed_at", "unknown")

    lines = [
        "# ILS Blind Audit — Report",
        "",
        f"Generated: {now}",
        f"Pre-registration sealed: {sealed_at}",
        "",
        "## Setup",
        "",
        "Pre-registration was sealed before any FAA document was opened.",
        "All geometric values were derived from constants in `geometry.py`.",
        "The compiler was run on sweeps and compared against FAA thresholds afterward.",
        "",
        "## Geometric Constants",
        "",
        f"- Glideslope: {geo['glideslope_deg']}°",
        f"- TCH: {geo['tch_ft']} ft AGL",
        f"- Roll bar distance: {geo['roll_bar_dist_ft']} ft before threshold",
        f"- Approach speed: {geo['approach_speed_kt']} kt",
        f"- Saturation DH: {geo['saturation_dh_ft']:.2f} ft",
        f"- RVR floor at DH=200 ft: {geo['rvr_floor_at_dh200_ft']:.1f} ft",
        f"- DH at RVR floor = 1800 ft: {geo['dh_at_rvr1800_ft']:.1f} ft",
        f"- Time to threshold at DH=200 ft: {geo['time_to_threshold_cat1_sec']:.1f} sec",
        f"- Time to threshold at DH=100 ft: {geo['time_to_threshold_cat2_sec']:.1f} sec",
        "",
        "## Sweep A (f3 absent)",
        "",
        "```",
        format_sweep(sweep_a),
        "```",
        "",
        "## Sweep B (f3 present)",
        "",
        "```",
        format_sweep(sweep_b),
        "```",
        "",
        "## FAA Regulatory Correspondence",
        "",
        "```",
        format_comparison(classifications),
        "```",
        "",
        "## Summary",
        "",
    ]

    # Build summary from actual classification results
    for c in classifications:
        lines.append(f"**{c.category}** ({c.classification}): {c.explanation}")
        lines.append("")

    lines += [
        "## Architectural Finding",
        "",
        prereg.get("architectural_claim", ""),
        "",
    ]

    REPORT_FILE.write_text("\n".join(lines))
    return REPORT_FILE


def main(force: bool = False) -> None:
    step1_preregister(force=force)
    sweep_a, sweep_b = step2_sweeps()
    classifications = step3_compare(sweep_a)
    report = step4_report(sweep_a, sweep_b, classifications)
    print(f"\nReport written: {report}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    main(force=force)
