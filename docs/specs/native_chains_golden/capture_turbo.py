"""Phase 0 golden capture for turbo — 3GPP audit + sweep surface signature.

Captures the audit_3gpp comparison table (5-row 3GPP correspondence matrix)
and the turbo_sweep_surface integer-coded emit histogram. The bijection in
Phase 2D is identity on level names (integer 0 → "REFUSE", 1 → "HOLD",
2 → "TRANSMIT_MONITORED", 3 → "TRANSMIT").
"""
from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_NAME_OF = {0: "REFUSE", 1: "HOLD", 2: "TRANSMIT_MONITORED", 3: "TRANSMIT"}


def main() -> None:
    py = _ROOT / ".venv" / "bin" / "python"
    audit = _ROOT / "examples" / "inference" / "register2" / "turbo" / "audit_3gpp.py"
    subprocess.run([str(py), str(audit)], check=True, capture_output=True)

    results_dir = _ROOT / "examples" / "inference" / "register2" / "turbo" / "results"

    audit_rows = []
    with (results_dir / "audit_3gpp_comparison.csv").open() as f:
        for row in csv.DictReader(f):
            audit_rows.append(dict(row))

    histogram = {}
    sample_cells = []
    with (results_dir / "turbo_sweep_surface.csv").open() as f:
        for i, row in enumerate(csv.DictReader(f)):
            perm_ber = int(row["perm_ber"])
            perm_bler = int(row["perm_bler"])
            histogram[(perm_ber, perm_bler)] = histogram.get((perm_ber, perm_bler), 0) + 1
            if i % 200 == 0:
                sample_cells.append({
                    "snr_db": float(row["snr_db"]),
                    "tau": float(row["tau"]),
                    "perm_ber": perm_ber,
                    "perm_ber_name": _NAME_OF[perm_ber],
                    "perm_bler": perm_bler,
                    "perm_bler_name": _NAME_OF[perm_bler],
                })

    hist_ser = {f"perm_ber={a},perm_bler={b}": cnt for (a, b), cnt in sorted(histogram.items())}

    out = {
        "example": "turbo",
        "audit_3gpp_correspondence_table": audit_rows,
        "surface_perm_histogram": hist_ser,
        "surface_sample_cells": sample_cells,
        "distinct_perm_ber_seen": sorted({a for (a, _) in histogram}),
        "distinct_perm_bler_seen": sorted({b for (_, b) in histogram}),
    }
    out_path = Path(__file__).resolve().parent / "turbo.json"
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f"Wrote {out_path}")
    print(f"  audit rows: {len(audit_rows)}")
    print(f"  surface histogram: {hist_ser}")


if __name__ == "__main__":
    main()
