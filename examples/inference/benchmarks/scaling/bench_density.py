"""Claim 3: Scan depth distribution over failure vector density.

Construction:
  - m=10 bits, n=4 levels (real Ising profile).
  - Vary failure vector density from 0.0 (all clear) to 1.0 (all failed).
  - At each density: generate 100,000 vectors, measure scan depth distribution.

Expected result:
  - Density 0: scan_depth always 1 (terminates immediately at top level).
  - Density 1: scan_depth always n (scans all levels, emits REFUSE).
  - Intermediate: bimodal or right-skewed distribution.
  - Average case << worst case for densities < 0.8.

Output: results/bench_density.csv
  Columns: density, mean_depth, median_depth, p95_depth, p99_depth, max_depth,
           frac_refuse, mean_bits_checked, time_per_call_ns
"""
from __future__ import annotations

import csv
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "synthetic"))

from compiler_kernel import compile_kernel, make_random_blocking_map, build_obstruction_matrix
from gen_failure_vectors import uniform_density

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

M_BITS   = 10
N_LEVELS = 4
BATCH    = 100_000

DENSITIES = np.round(np.arange(0.0, 1.01, 0.05), 2).tolist()


def bench_density_cell(density: float, blocking_map: np.ndarray,
                        rng: np.random.Generator) -> dict:
    vectors = uniform_density(M_BITS, BATCH, density, rng)
    obs_matrices = blocking_map[np.newaxis, :, :] & vectors[:, np.newaxis, :]

    depths        = np.zeros(BATCH, dtype=int)
    bits_checked  = np.zeros(BATCH, dtype=int)
    perm_levels   = np.zeros(BATCH, dtype=int)

    t0 = time.perf_counter_ns()
    for b in range(BATCH):
        r = compile_kernel(obs_matrices[b])
        depths[b]       = r.scan_depth
        bits_checked[b] = r.bits_checked
        perm_levels[b]  = r.permission_level
    t1 = time.perf_counter_ns()

    time_per_call_ns = (t1 - t0) / BATCH

    return {
        "density": round(density, 2),
        "mean_depth": round(float(depths.mean()), 4),
        "median_depth": round(float(np.median(depths)), 4),
        "p95_depth": round(float(np.percentile(depths, 95)), 4),
        "p99_depth": round(float(np.percentile(depths, 99)), 4),
        "max_depth": int(depths.max()),
        "frac_refuse": round(float((perm_levels == -1).mean()), 4),
        "mean_bits_checked": round(float(bits_checked.mean()), 4),
        "time_per_call_ns": round(time_per_call_ns, 3),
    }


def run() -> None:
    rng = np.random.default_rng(42)
    blocking_map = make_random_blocking_map(N_LEVELS, M_BITS, rng=rng, mode="monotone")

    print(f"\n{'='*75}")
    print("  Claim 3 — Scan depth distribution over failure vector density")
    print(f"  m={M_BITS} bits, n={N_LEVELS} levels, batch={BATCH:,} per density")
    print(f"{'='*75}\n")
    print(f"  {'density':>8}  {'mean_d':>8}  {'p95_d':>7}  {'max_d':>7}  "
          f"{'refuse%':>8}  {'ns/call':>9}")
    print(f"  {'─'*58}")

    rows = []
    for d in DENSITIES:
        row = bench_density_cell(d, blocking_map, rng)
        rows.append(row)
        print(f"  {row['density']:>8.2f}  {row['mean_depth']:>8.3f}  "
              f"{row['p95_depth']:>7.2f}  {row['max_depth']:>7}  "
              f"{row['frac_refuse']*100:>7.1f}%  {row['time_per_call_ns']:>9.2f}")

    path = os.path.join(RESULTS_DIR, "bench_density.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"\n  Written: {path}")

    # Key finding: average vs worst case ratio at real operating density (0.30)
    row_30 = next(r for r in rows if abs(r["density"] - 0.30) < 0.01)
    print(f"\n  KEY FINDING at operating density=0.30:")
    print(f"  Mean scan depth: {row_30['mean_depth']:.3f} / {N_LEVELS} (worst case)")
    print(f"  Average case is {N_LEVELS/row_30['mean_depth']:.1f}× faster than worst case.")
    print(f"  p99 depth: {row_30['p99_depth']:.1f} — tail is bounded.")
    print(f"{'='*75}\n")


if __name__ == "__main__":
    run()
