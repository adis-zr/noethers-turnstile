"""Degenerate Case D: Empty evidence context (Γ = ∅).

All failure bits are False. The compiler should emit the highest permission
level (level 0 = ACT / TRANSMIT_CRITICAL) immediately — best case, scan_depth=1.
This is the base case for inductive constructions.
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
from gen_failure_vectors import all_clear

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

M_VALUES = [1, 4, 10, 50, 100, 1000]
N_VALUES = [2, 4, 10, 20]
BATCH    = 100_000


def run() -> None:
    rng = np.random.default_rng(42)

    print(f"\n{'='*65}")
    print("  Degenerate D — Empty context (all bits False)")
    print(f"  Batch={BATCH:,} per (m, n) cell")
    print(f"{'='*65}\n")
    print(f"  {'m':>6}  {'n':>4}  {'perm':>8}  {'depth':>8}  {'bits':>8}  {'ns/call':>9}")
    print(f"  {'─'*50}")

    rows = []
    for m in M_VALUES:
        for n in N_VALUES:
            blocking_map = make_random_blocking_map(n, m, rng=rng, mode="monotone")
            vectors = all_clear(m, BATCH)
            obs = blocking_map[np.newaxis, :, :] & vectors[:, np.newaxis, :]

            t0 = time.perf_counter_ns()
            total_depth = 0; total_bits = 0; perm_set = set()
            for b in range(BATCH):
                r = compile_kernel(obs[b])
                total_depth += r.scan_depth
                total_bits  += r.bits_checked
                perm_set.add(r.permission_level)
            t1 = time.perf_counter_ns()

            avg_depth = total_depth / BATCH
            avg_bits  = total_bits  / BATCH
            ns_call   = (t1 - t0) / BATCH

            # Soundness: empty context must always give level 0 (top permission)
            assert perm_set == {0}, f"Empty context must give level 0, got {perm_set}"
            assert abs(avg_depth - 1.0) < 1e-9, f"Empty context scan_depth must be 1, got {avg_depth}"

            rows.append({"m": m, "n": n, "permission_level": 0, "scan_depth": 1,
                         "bits_checked": int(avg_bits), "ns_per_call": round(ns_call, 3)})
            print(f"  {m:>6}  {n:>4}  {'level_0':>8}  {avg_depth:>8.3f}  "
                  f"{avg_bits:>8.1f}  {ns_call:>9.2f}")

    path = os.path.join(RESULTS_DIR, "bench_empty_context.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["m", "n", "permission_level", "scan_depth",
                                           "bits_checked", "ns_per_call"])
        w.writeheader(); w.writerows(rows)
    print(f"\n  Soundness: PASSED — empty context always gives top permission at scan_depth=1")
    print(f"  Written: {path}\n")


if __name__ == "__main__":
    run()
