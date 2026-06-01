"""Claim 1: Compiler cost is O(mn) in failure bits and permission levels.

Construction:
  - Fix the underlying problem (10-variable Ising, β=0.30, known solution).
  - Vary m from 1 to 1000 failure bits.
  - Vary n from 2 to 20 permission levels.
  - Measure compiler kernel time only — inference is held constant.

Expected result:
  Runtime surface is linear in both m and n independently.
  The slope coefficient is the constant factor in the O(mn) bound.

Output: results/bench_mn_surface.csv
  Columns: m, n, time_us, bits_checked, scan_depth, time_per_mn_ns
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

# Sweep ranges
M_VALUES = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
N_VALUES = [2, 3, 4, 5, 8, 10, 15, 20]

# Benchmark settings
BATCH       = 10_000   # vectors per (m, n) cell — large enough for stable timing
DENSITY     = 0.3      # representative failure vector density
REPEATS     = 3        # repeat timing, take min (removes OS noise)


def bench_cell(m: int, n: int, rng: np.random.Generator) -> dict:
    """Benchmark one (m, n) cell."""
    blocking_map = make_random_blocking_map(n, m, rng=rng, mode="monotone")
    vectors = uniform_density(m, BATCH, DENSITY, rng)

    # Pre-build obstruction matrices for the full batch (broadcast)
    # shape: (BATCH, n, m)
    obs_matrices = blocking_map[np.newaxis, :, :] & vectors[:, np.newaxis, :]

    best_time = float("inf")
    total_bits = 0
    total_depth = 0

    for _ in range(REPEATS):
        t0 = time.perf_counter_ns()
        bits_checked_sum = 0
        depth_sum = 0
        for b in range(BATCH):
            result = compile_kernel(obs_matrices[b])
            bits_checked_sum += result.bits_checked
            depth_sum        += result.scan_depth
        t1 = time.perf_counter_ns()
        elapsed_ns = t1 - t0
        if elapsed_ns < best_time:
            best_time  = elapsed_ns
            total_bits = bits_checked_sum
            total_depth = depth_sum

    time_us     = best_time / 1e3
    time_per_mn = best_time / (BATCH * m * n)  # ns per (m*n) operation

    return {
        "m": m,
        "n": n,
        "batch": BATCH,
        "time_us": round(time_us, 3),
        "time_per_call_ns": round(best_time / BATCH, 2),
        "avg_bits_checked": round(total_bits / BATCH, 2),
        "avg_scan_depth": round(total_depth / BATCH, 3),
        "time_per_mn_ns": round(time_per_mn, 4),
    }


def run() -> None:
    rng = np.random.default_rng(42)

    print(f"\n{'='*70}")
    print("  Claim 1 — Compiler cost O(mn): m×n surface benchmark")
    print(f"  Batch={BATCH} vectors per cell, density={DENSITY}, repeats={REPEATS}")
    print(f"{'='*70}\n")

    rows = []
    print(f"  {'m':>6}  {'n':>4}  {'time/call(ns)':>14}  {'bits/call':>10}  {'depth/call':>11}  {'ns/(mn)':>9}")
    print(f"  {'─'*62}")

    for m in M_VALUES:
        for n in N_VALUES:
            row = bench_cell(m, n, rng)
            rows.append(row)
            print(f"  {m:>6}  {n:>4}  {row['time_per_call_ns']:>14.2f}  "
                  f"{row['avg_bits_checked']:>10.1f}  {row['avg_scan_depth']:>11.2f}  "
                  f"{row['time_per_mn_ns']:>9.4f}")

    path = os.path.join(RESULTS_DIR, "bench_mn_surface.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"\n  Written: {path}")

    # Print linearity check: does time_per_call grow linearly in m*n?
    print(f"\n  Linearity check (time_per_call vs m*n):")
    mn_vals = np.array([r["m"] * r["n"] for r in rows], dtype=float)
    t_vals  = np.array([r["time_per_call_ns"] for r in rows], dtype=float)
    corr = np.corrcoef(mn_vals, t_vals)[0, 1]
    print(f"  Pearson r(time, m×n) = {corr:.4f}  (1.0 = perfectly linear)")
    # Fit slope
    slope = np.polyfit(mn_vals, t_vals, 1)[0]
    print(f"  Slope: {slope:.4f} ns per (m×n) operation")
    print(f"  Interpretation: each additional (failure bit × permission level)")
    print(f"  comparison costs ~{slope:.2f} ns on this hardware.")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    run()
