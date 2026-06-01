"""Main runner: compute exact + BP + MF marginals for all Ising configs,
run the admissibility compiler on each result, write results/ising_NxN.csv.

Usage:
    python run_ising.py
"""
from __future__ import annotations

import csv
import os
import sys
import time

import numpy as np

from generate_ising import make_ising_grid_with_field as make_ising_grid, BETAS, SIZES
from run_exact import compute_exact_marginals
from run_bp import run_loopy_bp
from run_mf import run_mean_field
from compiler import compile_result, tv_distance, tv_distance_max, PERMISSION_NAMES

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

FIELDNAMES = [
    "n", "beta", "algorithm",
    "converged", "n_iter", "max_delta",
    "tv_mean", "tv_max", "bethe_fe", "bethe_per_var",
    "permission",
    "f_convergence", "f_tv_act", "f_tv_report", "f_tv_explore",
    "blocking_reasons",
    "elapsed_s",
]

CRITICAL_BETA = 0.44  # known Onsager critical temperature for 2D Ising


def run_all() -> None:
    rows_by_size: dict[int, list[dict]] = {n: [] for n in SIZES}

    for n in SIZES:
        print(f"\n{'='*60}")
        print(f"  {n}×{n} Ising grid")
        print(f"{'='*60}")

        for beta in BETAS:
            g = make_ising_grid(n, beta)

            # ── exact marginals ──────────────────────────────────────────
            t0 = time.time()
            exact_marg = compute_exact_marginals(g)
            exact_elapsed = time.time() - t0

            rows_by_size[n].append({
                "n": n, "beta": beta, "algorithm": "exact",
                "converged": True, "n_iter": 0, "max_delta": 0.0,
                "tv_mean": 0.0, "tv_max": 0.0, "bethe_fe": 0.0, "bethe_per_var": 0.0,
                "permission": "ACT",
                "f_convergence": False, "f_tv_act": False,
                "f_tv_report": False, "f_tv_explore": False,
                "blocking_reasons": "",
                "elapsed_s": round(exact_elapsed, 3),
            })
            print(f"  β={beta:.2f}  exact      t={exact_elapsed:.2f}s")

            # ── loopy BP ─────────────────────────────────────────────────
            t0 = time.time()
            bp = run_loopy_bp(g)
            bp_elapsed = time.time() - t0
            bp_tv_mean = tv_distance(bp["marginals"], exact_marg)
            bp_tv_max = tv_distance_max(bp["marginals"], exact_marg)
            bp_bethe = bp.get("bethe_fe", float("nan"))
            bp_cr = compile_result(bp["converged"], bp_tv_mean)

            rows_by_size[n].append({
                "n": n, "beta": beta, "algorithm": "loopy_bp",
                "converged": bp["converged"],
                "n_iter": bp["n_iter"],
                "max_delta": round(bp["max_delta"], 8),
                "tv_mean": round(bp_tv_mean, 6),
                "tv_max": round(bp_tv_max, 6),
                "bethe_fe": round(bp_bethe, 4),
                "bethe_per_var": round(bp_bethe / (n * n), 6),
                "permission": bp_cr.permission_name,
                "f_convergence": bp_cr.failure_vector.convergence_failure,
                "f_tv_act": bp_cr.failure_vector.tv_exceeds_act,
                "f_tv_report": bp_cr.failure_vector.tv_exceeds_report,
                "f_tv_explore": bp_cr.failure_vector.tv_exceeds_explore,
                "blocking_reasons": "|".join(bp_cr.blocking_reasons),
                "elapsed_s": round(bp_elapsed, 3),
            })
            print(f"  β={beta:.2f}  loopy_bp   "
                  f"conv={bp['converged']} iter={bp['n_iter']:3d} "
                  f"TV_mean={bp_tv_mean:.4f} TV_max={bp_tv_max:.4f}  → {bp_cr.permission_name}")

            # ── mean field ───────────────────────────────────────────────
            t0 = time.time()
            mf = run_mean_field(g)
            mf_elapsed = time.time() - t0
            mf_tv_mean = tv_distance(mf["marginals"], exact_marg)
            mf_tv_max = tv_distance_max(mf["marginals"], exact_marg)
            mf_cr = compile_result(mf["converged"], mf_tv_mean)

            rows_by_size[n].append({
                "n": n, "beta": beta, "algorithm": "mean_field",
                "converged": mf["converged"],
                "n_iter": mf["n_iter"],
                "max_delta": round(mf["max_delta"], 8),
                "tv_mean": round(mf_tv_mean, 6),
                "tv_max": round(mf_tv_max, 6),
                "bethe_fe": "",
                "bethe_per_var": "",
                "permission": mf_cr.permission_name,
                "f_convergence": mf_cr.failure_vector.convergence_failure,
                "f_tv_act": mf_cr.failure_vector.tv_exceeds_act,
                "f_tv_report": mf_cr.failure_vector.tv_exceeds_report,
                "f_tv_explore": mf_cr.failure_vector.tv_exceeds_explore,
                "blocking_reasons": "|".join(mf_cr.blocking_reasons),
                "elapsed_s": round(mf_elapsed, 3),
            })
            print(f"  β={beta:.2f}  mean_field "
                  f"conv={mf['converged']} iter={mf['n_iter']:3d} "
                  f"TV_mean={mf_tv_mean:.4f} TV_max={mf_tv_max:.4f}  → {mf_cr.permission_name}")

        # Write CSV for this grid size
        path = os.path.join(RESULTS_DIR, f"ising_{n}x{n}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows_by_size[n])
        print(f"\n  Written: {path}")

    # Print summary table
    print(f"\n{'='*100}")
    print(f"{'n':>4} {'beta':>6} {'algo':>12} {'conv':>5} {'TV_mean':>9} {'TV_max':>9} {'Bethe/N':>9} {'permission':>10}")
    print(f"{'='*100}")
    for n in SIZES:
        for row in rows_by_size[n]:
            if row["algorithm"] == "exact":
                continue
            bpv = f"{row['bethe_per_var']:>9.4f}" if row["bethe_per_var"] != "" else f"{'—':>9}"
            print(f"{row['n']:>4} {row['beta']:>6.2f} {row['algorithm']:>12} "
                  f"{str(row['converged']):>5} {row['tv_mean']:>9.4f} {row['tv_max']:>9.4f} "
                  f"{bpv} {row['permission']:>10}")


if __name__ == "__main__":
    run_all()
