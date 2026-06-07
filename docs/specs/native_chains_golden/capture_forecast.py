"""Phase 0 golden capture for forecast_value — final §8 verdict + arm summaries.

Forecast value is a computational pipeline, not a per-cell emit grid. Its
golden is the §8 verdict and the arm-level summaries (Ae_monotone count,
manufactured_permission count, etc.). The post-rewrite verification asserts
these stay equal under the new chain (rewriting NO_ACTION/REPORT_EXCEEDANCE/
... shouldn't change the numerical result; only the level names emitted).

We re-run run_all.py and snapshot the outcome.md JSON block.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    # Run the pipeline.
    py = _ROOT / ".venv" / "bin" / "python"
    runner = _ROOT / "examples" / "forecast_value" / "run_all.py"
    subprocess.run([str(py), str(runner)], check=True, capture_output=True)

    # Snapshot the artifacts.
    fv = _ROOT / "examples" / "forecast_value" / "results"
    arm1 = json.loads((fv / "arm1_summary.json").read_text())
    arm2 = json.loads((fv / "arm2_summary.json").read_text())
    outcome_text = (fv / "outcome.md").read_text()

    # Extract verdict from outcome.md
    verdict = "unknown"
    for line in outcome_text.splitlines():
        if line.startswith("**Verdict:**"):
            verdict = line.split("`")[1]
            break

    out = {
        "example": "forecast_value",
        "verdict": verdict,
        "arm1_preregistered_checks": {
            k: v for k, v in arm1.items() if k.startswith("preregistered_")
        },
        "arm2_preregistered_checks": {
            k: v for k, v in arm2.items() if k.startswith("preregistered_")
        },
        "arm1_counts": {
            "n_rows": arm1.get("n_rows"),
            "n_divergences": arm1.get("n_divergences"),
            "n_bins_with_Ae_variation_at_fixed_p_hat": arm1.get(
                "n_bins_with_Ae_variation_at_fixed_p_hat"
            ),
            "n_bins_total": arm1.get("n_bins_total"),
        },
        "arm2_counts": {
            "n_evidence_states": arm2.get("n_evidence_states"),
            "Ae_monotone_along_L0_to_L3": arm2.get("Ae_monotone_along_L0_to_L3"),
            "manufactured_permission_witness_fires_at_L3": arm2.get(
                "manufactured_permission_witness_fires_at_L3"
            ),
            "DRO_matches_Ae_at_L0": arm2.get("DRO_matches_Ae_at_L0"),
        },
    }
    out_path = Path(__file__).resolve().parent / "forecast_value.json"
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f"Wrote {out_path}")
    print(f"  verdict: {verdict}")
    print(f"  arm1 n_rows={out['arm1_counts']['n_rows']}, n_divergences={out['arm1_counts']['n_divergences']}")
    print(f"  arm2 Ae_monotone={out['arm2_counts']['Ae_monotone_along_L0_to_L3']}")


if __name__ == "__main__":
    main()
