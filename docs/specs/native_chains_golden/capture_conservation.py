"""Phase 0 golden capture for conservation — central two-axis run + emit histogram.

Captures the run_two_axis_convergence_v2.py headline numbers (resolving and
non-resolving path soundness/monotonicity counts) plus a histogram of distinct
emits across the matrix. Per §11 Q3 Option A, conservation moves from the
default 12-level chain to the paper-5-level chain. The bijection is identity
on REF/DIA/REV/AEX/ALR plus `OOC ↔ REF` for any membership-failure folding.

If the golden contains `OOC` emits, the post-rewrite verification must apply
the folding rule; if it contains none, byte-for-byte equality on the rest is
the degenerate case.
"""
from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    py = _ROOT / ".venv" / "bin" / "python"
    runner = _ROOT / "examples" / "conservation" / "run_two_axis_convergence_v2.py"
    res = subprocess.run([str(py), str(runner)], check=True, capture_output=True, text=True)

    results = _ROOT / "examples" / "conservation" / "results"
    summary_csv = results / "two_axis_convergence_v2_summary.csv"
    matrix_csv = results / "two_axis_convergence_v2_matrix.csv"

    summary_rows = []
    with summary_csv.open() as f:
        for row in csv.DictReader(f):
            summary_rows.append(dict(row))

    emit_histogram = {}
    n_rows = 0
    if matrix_csv.exists():
        with matrix_csv.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                n_rows += 1
                # The matrix has many columns; look for permission-like columns
                # and tally distinct emit values.
                for key in ("C_mn", "emit", "permission", "permission_str"):
                    if key in row:
                        v = row[key]
                        emit_histogram[v] = emit_histogram.get(v, 0) + 1
                        break

    # Parse last lines of stdout to capture the headline numbers
    stdout_tail = "\n".join(res.stdout.splitlines()[-25:])

    out = {
        "example": "conservation",
        "summary_rows": summary_rows,
        "matrix_n_rows": n_rows,
        "matrix_emit_histogram": emit_histogram,
        "distinct_emits_seen": sorted(emit_histogram.keys()),
        "headline_stdout_tail": stdout_tail,
    }
    out_path = Path(__file__).resolve().parent / "conservation.json"
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f"Wrote {out_path}")
    print(f"  summary rows: {len(summary_rows)}")
    print(f"  matrix rows: {n_rows}")
    print(f"  distinct emits: {sorted(emit_histogram.keys())}")


if __name__ == "__main__":
    main()
