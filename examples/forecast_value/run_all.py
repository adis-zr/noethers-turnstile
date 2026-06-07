"""Driver: calibration gate → controls → Arm 1 → Arm 2 → §8 classification.

Halts if calibration or null controls fail (which indicate framework bug).
Writes:
  results/run_metadata.json    timestamp + git rev
  results/outcome.md           §8 verdict for this run
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from worldgen import sample_worlds, constants_summary
from controls import (
    calibration_gate, homogeneous_loss_null, dro_equivalence,
    cost_loss_optimality_note,
)
from arm1_divergence import run_arm1
from arm2_conservation import run_arm2

RESULTS_DIR = _HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def _git_rev() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_HERE, stderr=subprocess.DEVNULL
        ).decode().strip()
        return out
    except Exception:
        return "unknown"


def _classify(controls_passed: bool, arm1_div: bool, arm1_het: bool,
              arm2_cons: bool, arm2_witness: bool) -> str:
    """§8 decision table."""
    if not controls_passed:
        return "bug"
    if not arm2_cons:
        return "bug"
    if arm1_div and arm1_het and arm2_cons and arm2_witness:
        return "strong"
    if arm1_div and arm1_het and arm2_cons and not arm2_witness:
        return "partial"
    if arm1_div and not arm1_het and arm2_cons and arm2_witness:
        return "partial"
    if not arm1_div and arm2_cons and arm2_witness:
        return "scope"
    if not arm1_div and arm2_cons and not arm2_witness:
        return "null"
    return "ambiguous"


def main() -> int:
    print("="*100)
    print("Forecast-value experiment — driver")
    print("="*100)
    print()

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata = {
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "git_rev": _git_rev(),
        "spec_version": "meteorology-v1",
        "constants": constants_summary(),
    }
    with open(RESULTS_DIR / "run_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Git rev: {metadata['git_rev']}")
    print(f"Timestamp: {metadata['timestamp_utc']}")
    print()

    # ── Calibration gate ──────────────────────────────────────────────────────
    print("-"*100)
    print("§7.1 Calibration gate")
    print("-"*100)
    ws_for_gate = sample_worlds(n=20000, seed=2026)
    gate_passed, gate_diag = calibration_gate(ws_for_gate)
    print(f"  Passed: {gate_passed}  MAD={gate_diag['mad']:.4f}  tol={gate_diag['tolerance']}")
    with open(RESULTS_DIR / "calibration_gate.json", "w") as f:
        json.dump(gate_diag, f, indent=2)
    if not gate_passed:
        print("  GATE FAILED — experiment void.")
        _write_outcome("bug", reason="calibration gate failed", details={})
        return 1

    # ── §7.2 Homogeneous-loss null ────────────────────────────────────────────
    print()
    print("-"*100)
    print("§7.2 Homogeneous-loss null")
    print("-"*100)
    null_passed, null_diag = homogeneous_loss_null(n_worlds=10000)
    print(f"  Passed: {null_passed}  fibers={null_diag['n_fibers_checked']}  bug-fails={null_diag['n_failures']}")
    with open(RESULTS_DIR / "homogeneous_null.json", "w") as f:
        # don't write the giant rows list; keep summary + failures
        json.dump({k: v for k, v in null_diag.items() if k != "rows"}, f, indent=2)
    if not null_passed:
        print("  NULL FAILED — framework bug.")
        _write_outcome("bug", reason="homogeneous-loss null failed", details=null_diag)
        return 2

    # ── §7.3 DRO equivalence ─────────────────────────────────────────────────
    print()
    print("-"*100)
    print("§7.3 DRO-equivalence")
    print("-"*100)
    ws_for_dro = sample_worlds(n=20000, seed=2027)
    dro_passed, dro_diag = dro_equivalence(ws_for_dro)
    print(f"  Passed: {dro_passed}  fibers={dro_diag['n_fibers_checked']}  fails={dro_diag['n_failures']}")
    with open(RESULTS_DIR / "dro_equivalence.json", "w") as f:
        json.dump({k: v for k, v in dro_diag.items() if k != "rows"}, f, indent=2)
    if not dro_passed:
        print("  DRO-equivalence FAILED — framework definitional drift.")
        _write_outcome("bug", reason="DRO-equivalence failed", details=dro_diag)
        return 3

    # ── §7.4 Cost-loss optimality note ────────────────────────────────────────
    print()
    cl_note = cost_loss_optimality_note()
    print(f"§7.4 Cost-loss optimality (logged, not tested):")
    print(f"  L_bar={cl_note['L_bar']}  C={cl_note['C']}  threshold={cl_note['cost_loss_threshold']}")
    with open(RESULTS_DIR / "cost_loss_note.json", "w") as f:
        json.dump(cl_note, f, indent=2)

    controls_passed = True

    # ── Arm 1 ────────────────────────────────────────────────────────────────
    print()
    print("-"*100)
    print("§5 Arm 1 — Expectation divergence")
    print("-"*100)
    arm1_summary = run_arm1()
    with open(RESULTS_DIR / "arm1_summary.json", "w") as f:
        json.dump(arm1_summary, f, indent=2)
    arm1_div = arm1_summary["preregistered_check_arm1_div_exists"]
    arm1_het = arm1_summary["preregistered_check_boundary_tracks_heterogeneity"]
    print(f"  divergence_exists={arm1_div}, boundary_tracks_heterogeneity={arm1_het}")
    print(f"  n_rows={arm1_summary['n_rows']} n_divergences={arm1_summary['n_divergences']}")
    print(f"  bins_with_Ae_variation_at_fixed_p_hat={arm1_summary['n_bins_with_Ae_variation_at_fixed_p_hat']}/{arm1_summary['n_bins_total']}")

    # ── Arm 2 ────────────────────────────────────────────────────────────────
    print()
    print("-"*100)
    print("§6 Arm 2 — Conservation under coarsening")
    print("-"*100)
    arm2_summary = run_arm2()
    with open(RESULTS_DIR / "arm2_summary.json", "w") as f:
        json.dump(arm2_summary, f, indent=2)
    arm2_cons = arm2_summary["preregistered_check_1_Ae_conserved"]
    arm2_witness = arm2_summary["preregistered_check_2_manufactured_witness_fires"]
    print(f"  A(e) conserved={arm2_cons}, manufactured-permission witness fires={arm2_witness}")
    print(f"  Ae_monotone={arm2_summary['Ae_monotone_along_L0_to_L3']}")
    print(f"  manufactured_at_L3={arm2_summary['manufactured_permission_witness_fires_at_L3']}")
    print(f"  DRO_matches_Ae_at_L0={arm2_summary['DRO_matches_Ae_at_L0']}")

    # ── Classification ────────────────────────────────────────────────────────
    verdict = _classify(controls_passed, arm1_div, arm1_het, arm2_cons, arm2_witness)
    print()
    print("="*100)
    print(f"§8 VERDICT: {verdict.upper()}")
    print("="*100)

    _write_outcome(verdict, reason="all gates and controls passed", details={
        "calibration_mad": gate_diag["mad"],
        "null_failures": null_diag["n_failures"],
        "dro_failures": dro_diag["n_failures"],
        "arm1_summary": arm1_summary,
        "arm2_summary": arm2_summary,
    })
    return 0


def _write_outcome(verdict: str, reason: str, details: dict) -> None:
    text = f"""# Outcome — §8 verdict

**Verdict:** `{verdict}`

**Reason:** {reason}

## Details

```json
{json.dumps(details, indent=2)}
```

## §8 mapping

| Outcome | Arm 1 | Arm 2 | Verdict |
|---|---|---|---|
| Strong  | divergence tracks heterogeneity | manufactured permission, A(e) conserved | flagship |
| Partial | divergence exists               | no manufactured-permission witness      | supporting |
| Scope   | no divergence                    | A(e) conserved trivially                | stated limit |
| Null    | no divergence                    | no asymmetry                            | repo example only |
| Bug     | null control fails OR A(e) non-monotone under admissible coarsening | — | halt, fix before any paper mention |
"""
    with open(RESULTS_DIR / "outcome.md", "w") as f:
        f.write(text)


if __name__ == "__main__":
    raise SystemExit(main())
