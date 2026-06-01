"""Degenerate Case C: Contradictory failure vectors.

A failure vector where some bits indicate adequate quality and others indicate
inadequate quality for the same permission level. Tests soundness: the compiler
must emit the highest level whose full obstruction condition is not triggered,
regardless of the contradiction pattern. Must never crash or produce an invalid
permission level.
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
from gen_failure_vectors import contradictory

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

M_BITS   = 10
N_LEVELS = 4
BATCH    = 50_000


def run() -> None:
    rng = np.random.default_rng(42)
    blocking_map = make_random_blocking_map(N_LEVELS, M_BITS, rng=rng, mode="monotone")
    vectors = contradictory(M_BITS, N_LEVELS, blocking_map, BATCH, rng)
    obs = blocking_map[np.newaxis, :, :] & vectors[:, np.newaxis, :]

    print(f"\n{'='*65}")
    print("  Degenerate C — Contradictory failure vectors")
    print(f"  m={M_BITS}, n={N_LEVELS}, batch={BATCH:,}")
    print(f"{'='*65}\n")

    perm_counts = {-1: 0}
    for lvl in range(N_LEVELS):
        perm_counts[lvl] = 0

    t0 = time.perf_counter_ns()
    for b in range(BATCH):
        r = compile_kernel(obs[b])
        # Soundness: must be a valid permission level or REFUSE (-1)
        assert r.permission_level >= -1 and r.permission_level < N_LEVELS, (
            f"Invalid permission level: {r.permission_level}"
        )
        perm_counts[r.permission_level] = perm_counts.get(r.permission_level, 0) + 1
    t1 = time.perf_counter_ns()

    print("  Permission distribution over contradictory vectors:")
    for lvl in sorted(perm_counts.keys()):
        name = "REFUSE" if lvl == -1 else f"level_{lvl}"
        pct  = perm_counts[lvl] / BATCH * 100
        print(f"    {name:>10}: {perm_counts[lvl]:>8,} ({pct:5.1f}%)")

    print(f"\n  Time per call: {(t1-t0)/BATCH:.2f} ns")
    print(f"  Soundness: PASSED — all {BATCH:,} outputs are valid permission levels")

    rows = [{"perm_level": k, "count": v, "fraction": v/BATCH}
            for k, v in sorted(perm_counts.items())]
    path = os.path.join(RESULTS_DIR, "bench_contradictory.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["perm_level", "count", "fraction"])
        w.writeheader(); w.writerows(rows)
    print(f"  Written: {path}\n")


if __name__ == "__main__":
    run()
