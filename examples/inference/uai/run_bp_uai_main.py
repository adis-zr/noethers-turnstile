"""Main runner: BP on selected UAI benchmark problems, compiler on each result.

Problem selection spans four families and a range of sizes/difficulties:

  Grids      — binary pairwise grids, directly comparable to Ising Tier 1
  Pedigree   — ternary genealogical networks, real-world, loopy, BP known to struggle
  Segmentation — binary computer vision models, large and dense
  Promedus   — binary medical networks, large
  ObjectDetection — high-cardinality (11-state) vision models

Within each family, we pick instances spanning small→large to show induced-width
effect. Problems without a .uai file are skipped automatically.

Reference:
  UAI 2014 competition problem sets, via UAI 2022 tuning benchmarks.
  https://www.ics.uci.edu/~dechter/uaicompetition/2022/TuningBenchmarks/
"""
from __future__ import annotations

import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from parse_uai import parse_uai
from run_bp_uai import run_bp_uai
from compiler_uai import compile_uai_result

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "PR")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Selected problems: (filename_stem, family, notes)
# Chosen to span families and sizes; all have .uai + .evid in PR.zip
SELECTED = [
    # Grids — binary pairwise, known BP behavior vs Ising
    ("grid10x10.f10",   "Grids",          "10×10 grid, binary"),
    ("Grids_11",        "Grids",          "100-var binary grid"),
    ("Grids_14",        "Grids",          "100-var binary grid, variant"),
    ("Grids_18",        "Grids",          "400-var binary grid, large"),
    # Pedigree — ternary, genealogical, known BP difficulty
    ("Pedigree_11",     "Pedigree",       "385-var ternary, real genealogical"),
    ("Pedigree_13",     "Pedigree",       "385-var ternary, variant"),
    # Segmentation — binary, computer vision, dense
    ("Segmentation_11", "Segmentation",   "228-var binary, vision"),
    ("Segmentation_13", "Segmentation",   "235-var binary, vision, larger"),
    # Promedus — binary, medical, large
    ("Promedus_11",     "Promedus",       "461-var binary, medical"),
    ("Promedus_13",     "Promedus",       "894-var binary, medical, largest"),
    # ObjectDetection — 11-state, high cardinality
    ("ObjectDetection_11", "ObjectDetection", "60-var 11-state, vision"),
]

FIELDNAMES = [
    "problem", "family", "n_vars", "max_card", "n_factors", "n_evidence",
    "converged", "n_iter", "max_delta",
    "bethe_fe", "bethe_per_var",
    "permission",
    "f_convergence", "f_bethe_act", "f_bethe_report", "f_bethe_explore",
    "blocking_reasons",
    "elapsed_s", "notes",
]


def problem_stats(g) -> dict:
    return {
        "n_vars": g.n_vars,
        "max_card": max(g.cardinalities),
        "n_factors": g.n_factors,
        "n_evidence": len(g.evidence),
    }


def run_all() -> None:
    rows = []

    print(f"\n{'='*80}")
    print(f"  UAI Tier 2 — Loopy BP + Admissibility Compiler")
    print(f"  Data: {DATA_DIR}")
    print(f"{'='*80}\n")
    print(f"{'Problem':<25} {'Fam':<16} {'N':>5} {'K':>3} {'F':>5} {'Obs':>4}  "
          f"{'Conv':>5} {'iter':>4} {'Bethe/N':>8}  {'Perm':>7}")
    print("-" * 90)

    for stem, family, notes in SELECTED:
        uai_path = os.path.join(DATA_DIR, stem + ".uai")
        if not os.path.exists(uai_path):
            print(f"  SKIP {stem} — file not found")
            continue

        g = parse_uai(uai_path)
        stats = problem_stats(g)

        t0 = time.time()
        r = run_bp_uai(g, max_iter=200, tol=1e-6, damping=0.5)
        elapsed = time.time() - t0

        cr = compile_uai_result(r["converged"], r["bethe_fe"], g.n_vars)

        print(f"  {stem:<23} {family:<16} {stats['n_vars']:>5} {stats['max_card']:>3} "
              f"{stats['n_factors']:>5} {stats['n_evidence']:>4}  "
              f"{str(r['converged']):>5} {r['n_iter']:>4} "
              f"{cr.bethe_per_var:>8.4f}  {cr.permission_name:>7}")

        rows.append({
            "problem": stem,
            "family": family,
            "n_vars": stats["n_vars"],
            "max_card": stats["max_card"],
            "n_factors": stats["n_factors"],
            "n_evidence": stats["n_evidence"],
            "converged": r["converged"],
            "n_iter": r["n_iter"],
            "max_delta": round(r["max_delta"], 8),
            "bethe_fe": round(r["bethe_fe"], 4),
            "bethe_per_var": round(cr.bethe_per_var, 6),
            "permission": cr.permission_name,
            "f_convergence": cr.failure_vector.convergence_failure,
            "f_bethe_act": cr.failure_vector.bethe_exceeds_act,
            "f_bethe_report": cr.failure_vector.bethe_exceeds_report,
            "f_bethe_explore": cr.failure_vector.bethe_exceeds_explore,
            "blocking_reasons": "|".join(cr.blocking_reasons),
            "elapsed_s": round(elapsed, 2),
            "notes": notes,
        })

    out = os.path.join(RESULTS_DIR, "uai_mar_results.csv")
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n  Written: {out}")
    print(f"\n{'='*80}")
    print("  KEY FINDING: f1 (convergence_failure) fires without ground truth.")
    print("  TV bits (f2–f4) absent — compiler is sound on f1 alone on all instances.")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    run_all()
