"""Degenerate Case A: m=1 failure bit, n up to 100 permission levels.

The compiler reduces to a linear scan of n levels with a single bit check per
level. Verify runtime matches O(n) prediction and scan terminates correctly.
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

M_BITS  = 1
N_RANGE = [2, 5, 10, 20, 30, 50, 75, 100]
BATCH   = 50_000


def run() -> None:
    rng = np.random.default_rng(42)

    print(f"\n{'='*65}")
    print("  Degenerate A — m=1 bit, n up to 100 permission levels")
    print(f"  Batch={BATCH:,} vectors per n")
    print(f"{'='*65}\n")
    print(f"  {'n':>5}  {'time/call(ns)':>14}  {'bits/call':>10}  {'corr vs n':>10}")
    print(f"  {'─'*46}")

    rows = []
    times = []
    n_vals = []
    for n in N_RANGE:
        blocking_map = make_random_blocking_map(n, M_BITS, rng=rng, mode="dense")
        vectors = uniform_density(M_BITS, BATCH, 0.5, rng)
        obs = blocking_map[np.newaxis, :, :] & vectors[:, np.newaxis, :]

        t0 = time.perf_counter_ns()
        total_bits = 0
        for b in range(BATCH):
            r = compile_kernel(obs[b])
            total_bits += r.bits_checked
        t1 = time.perf_counter_ns()

        time_per_call = (t1 - t0) / BATCH
        bits_per_call = total_bits / BATCH
        times.append(time_per_call)
        n_vals.append(n)

        rows.append({"n": n, "m": M_BITS, "time_per_call_ns": round(time_per_call, 3),
                     "bits_per_call": round(bits_per_call, 2)})
        print(f"  {n:>5}  {time_per_call:>14.2f}  {bits_per_call:>10.2f}", end="")
        if len(times) > 1:
            corr = np.corrcoef(n_vals, times)[0, 1]
            print(f"  {corr:>10.4f}")
        else:
            print()

    # Fit slope: time = a*n + b
    slope, intercept = np.polyfit(n_vals, times, 1)
    print(f"\n  Linear fit: time = {slope:.3f}*n + {intercept:.2f} ns")
    print(f"  Slope {slope:.3f} ns/level is the O(n) constant for m=1.")

    path = os.path.join(RESULTS_DIR, "bench_single_bit.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["n", "m", "time_per_call_ns", "bits_per_call"])
        w.writeheader(); w.writerows(rows)
    print(f"  Written: {path}\n")


if __name__ == "__main__":
    run()
