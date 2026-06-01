"""Degenerate Case B: m up to 1000 failure bits, n=2 permission levels.

Maximum work case for given m: evaluates all m bits at the single
permission threshold. Verify it is still fast and report absolute time.
"""
from __future__ import annotations

import csv
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "synthetic"))

from compiler_kernel import compile_kernel, make_random_blocking_map
from gen_failure_vectors import uniform_density

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

N_LEVELS = 2
M_RANGE  = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
BATCH    = 10_000


def run() -> None:
    rng = np.random.default_rng(42)

    print(f"\n{'='*65}")
    print("  Degenerate B — m up to 1000 bits, n=2 permission levels")
    print(f"  Batch={BATCH:,} vectors per m")
    print(f"{'='*65}\n")
    print(f"  {'m':>6}  {'time/call(ns)':>14}  {'bits/call':>10}  {'frac_refuse':>12}")
    print(f"  {'─'*48}")

    rows = []
    for m in M_RANGE:
        blocking_map = make_random_blocking_map(N_LEVELS, m, rng=rng, mode="dense")
        vectors = uniform_density(m, BATCH, 0.3, rng)
        obs = blocking_map[np.newaxis, :, :] & vectors[:, np.newaxis, :]

        t0 = time.perf_counter_ns()
        total_bits   = 0
        refuse_count = 0
        for b in range(BATCH):
            r = compile_kernel(obs[b])
            total_bits   += r.bits_checked
            refuse_count += (r.permission_level == -1)
        t1 = time.perf_counter_ns()

        time_per_call = (t1 - t0) / BATCH
        bits_per_call = total_bits / BATCH
        frac_refuse   = refuse_count / BATCH

        rows.append({"m": m, "n": N_LEVELS, "time_per_call_ns": round(time_per_call, 3),
                     "bits_per_call": round(bits_per_call, 2),
                     "frac_refuse": round(frac_refuse, 4)})
        print(f"  {m:>6}  {time_per_call:>14.2f}  {bits_per_call:>10.2f}  {frac_refuse:>12.4f}")

    path = os.path.join(RESULTS_DIR, "bench_single_level.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["m", "n", "time_per_call_ns", "bits_per_call", "frac_refuse"])
        w.writeheader(); w.writerows(rows)

    row_1000 = rows[-1]
    print(f"\n  At m=1000, n=2: {row_1000['time_per_call_ns']:.1f} ns per call")
    print(f"  Written: {path}\n")


if __name__ == "__main__":
    run()
