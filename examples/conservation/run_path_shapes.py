"""Item 1b — Test the non-resolving tail theorem across four path shapes.

The current v3 §2.7.4 result is N=1: it tests one path shape (canonical:
L5 → L4 → L3 → L2 → L1 → L0; inadmissible step at the start). The theorem
this experiment is supposed to support (Item 1a, "resolving tail subsumes
prefix") predicts that reconvergence depends only on the tail's properties,
not on the prefix.

To turn the experiment into a characterized boundary instead of one
anecdote, we test four path shapes:

  Path A (canonical, already tested):  L5 → L4 → L3 → L2 → L1 → L0
    - Inadmissible step: at start (L5)
    - Tail: L4 → L0 (resolving)
    - Theorem predicts: reconvergence to A(e)

  Path B (middle inadmissibility):     L4 → L5 → L4 → L3 → L2 → L1 → L0
    - Inadmissible step: in middle (L5)
    - Tail: L4 → L0 (resolving)
    - Theorem predicts: reconvergence to A(e); transient violations
      localized to L5 and its L5→L4 restoration

  Path C (double inadmissibility):     L5 → L4 → L5 → L4 → L3 → L2 → L1 → L0
    - Two inadmissible steps
    - Tail: L4 → L0 (resolving)
    - Theorem predicts: reconvergence to A(e); transient violations
      localized to each L5 and each L5→L4 restoration

  Path D (terminal inadmissibility):   L4 → L3 → L2 → L1 → L0 → L5
    - Inadmissible step: at end (L5)
    - No resolving tail beyond L5
    - Theorem predicts: final emit is L5's emit, which may not equal A(e).
      Reconvergence FAILS.

Path A is the v3 baseline. Paths B, C, D are the boundary tests.

For each path and each case, we record per-cell emit and aggregate
soundness, monotonicity, and final convergence.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
_WORKSPACE_PY = _HERE.parents[1] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

sys.path.insert(0, str(_HERE))
from run_two_axis_convergence_v2 import (  # type: ignore
    _all_cases, _project_statuses,
    _project_requirements_join,
    _project_requirements_skeleton_truncating,
    _compile_case,
    _LEVEL_0_GROUPS, _LEVEL_1_GROUPS, _LEVEL_2_GROUPS,
    _LEVEL_3_GROUPS, _LEVEL_4_GROUPS, _LEVEL_5_GROUPS,
    K_LEVELS, _grid_output,
)

RESULTS_DIR = _HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# A path is a list of (step_idx, level_id, groups, admissible) tuples.
# step_idx is the position in the path. level_id ∈ {0..5}. groups is the
# coarsening map for that level. admissible = whether to use join or
# skeleton-truncating projection.

_LEVEL_GROUPS = {
    0: _LEVEL_0_GROUPS,
    1: _LEVEL_1_GROUPS,
    2: _LEVEL_2_GROUPS,
    3: _LEVEL_3_GROUPS,
    4: _LEVEL_4_GROUPS,
    5: _LEVEL_5_GROUPS,
}


def _make_path(levels_and_admissible: list[tuple[int, bool]]) -> list[tuple]:
    """Build a path from [(level_id, admissible), ...]."""
    return [
        (step_idx, level_id, _LEVEL_GROUPS[level_id], admissible)
        for step_idx, (level_id, admissible) in enumerate(levels_and_admissible)
    ]


# Four path shapes
_PATHS = {
    "A_canonical":         _make_path([(5, False), (4, True), (3, True), (2, True), (1, True), (0, True)]),
    "B_middle":            _make_path([(4, True),  (5, False), (4, True), (3, True), (2, True), (1, True), (0, True)]),
    "C_double":            _make_path([(5, False), (4, True), (5, False), (4, True), (3, True), (2, True), (1, True), (0, True)]),
    "D_terminal":          _make_path([(4, True),  (3, True), (2, True), (1, True), (0, True), (5, False)]),
}


def _run_case_step(case: dict, level_id: int, groups, admissible: bool, fingerprint: str) -> str:
    """Compile a case at one (level, projection-mode) step."""
    proj_statuses = _project_statuses(case["gap_statuses"], groups)
    if admissible:
        proj_reqs = _project_requirements_join(case["fine_reqs"], groups)
    else:
        proj_reqs = _project_requirements_skeleton_truncating(case["fine_reqs"], groups)
    return _compile_case(proj_statuses, proj_reqs, fingerprint)


def _rank(perm: str) -> int:
    return {"REF": 0, "DIA": 1, "REV": 2, "AEX": 3, "ALR": 4}.get(perm, 0)


def main() -> None:
    print("=" * 100)
    print(" Path-shape experiment — non-resolving tail theorem")
    print("=" * 100)

    cases = _all_cases()
    print(f"\n  Loaded {len(cases)} cases.")

    # Compute reference A(e) for each case at the canonical (L0, admissible) endpoint.
    print("\n  Computing reference A(e) per case at L0 (admissible, canonical map)...")
    ref_perm: dict[str, str] = {}
    ref_norm: dict[str, float] = {}
    for case in cases:
        perm = _run_case_step(case, 0, _LEVEL_0_GROUPS, True, f"ref-{case['case_id']}")
        ref_perm[case["case_id"]] = perm
        ref_norm[case["case_id"]] = _grid_output(perm, max(K_LEVELS))

    rows = []
    for path_name, path in _PATHS.items():
        print(f"\n  ── Path {path_name} ──")
        path_summary_str = "  ".join(
            f"L{lvl}{'!' if not adm else ''}"
            for _, lvl, _, adm in path
        )
        print(f"  Shape: {path_summary_str}  (! = inadmissible)")

        # Track previous (case, k) → C_mn for monotonicity-in-m
        prev_by_step_k: dict[tuple[str, int], float] = {}

        for step_idx, level_id, groups, admissible in path:
            for case in cases:
                cid = case["case_id"]
                perm_m = _run_case_step(
                    case, level_id, groups, admissible,
                    f"{path_name}-step{step_idx}-{cid}"
                )
                ae = ref_norm[cid]
                prev_k_c = None
                for k in K_LEVELS:
                    c_mn = _grid_output(perm_m, k)
                    gap = ae - c_mn
                    sound = int(c_mn <= ae + 1e-9)
                    prev_val = prev_by_step_k.get((cid, k))
                    if step_idx == 0:
                        mon_step = 1
                    else:
                        # In path direction, we expect emit non-decreasing
                        # along an admissible refinement. Track step-by-step.
                        mon_step = int(c_mn >= (prev_val or 0.0) - 1e-9) if prev_val is not None else 1
                    mon_k = int(c_mn >= (prev_k_c or 0.0) - 1e-9) if prev_k_c is not None else 1
                    rows.append({
                        "path": path_name,
                        "case_id": cid,
                        "family": case["family"],
                        "step_idx": step_idx,
                        "level": level_id,
                        "admissible": int(admissible),
                        "k": k,
                        "perm_m": perm_m,
                        "C_mn": round(c_mn, 6),
                        "A_e_perm": ref_perm[cid],
                        "A_e": round(ae, 6),
                        "gap": round(gap, 6),
                        "sound": sound,
                        "monotone_step": mon_step,
                        "monotone_k": mon_k,
                    })
                    prev_k_c = c_mn
                # Update prev_by_step_k after the full k-sweep for this (case, step)
                for k in K_LEVELS:
                    c_mn_k = next(
                        r["C_mn"] for r in rows
                        if r["path"] == path_name and r["case_id"] == cid
                        and r["step_idx"] == step_idx and r["k"] == k
                    )
                    prev_by_step_k[(cid, k)] = c_mn_k

    # Write matrix CSV
    matrix_path = RESULTS_DIR / "path_shapes_matrix.csv"
    fields = list(rows[0].keys())
    with open(matrix_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # ── Reports ──────────────────────────────────────────────────────────────
    print("\n" + "─" * 100)
    print(" PER-PATH GATE SUMMARY")
    print("─" * 100)

    for path_name in _PATHS.keys():
        path_rows = [r for r in rows if r["path"] == path_name]
        n_cells = len(path_rows)
        n_sound = sum(r["sound"] for r in path_rows)
        n_mon_step = sum(r["monotone_step"] for r in path_rows)
        n_mon_k = sum(r["monotone_k"] for r in path_rows)
        max_step = max(r["step_idx"] for r in path_rows)
        final_rows = [r for r in path_rows if r["step_idx"] == max_step and r["k"] == max(K_LEVELS)]
        n_converged = sum(1 for r in final_rows if abs(r["gap"]) < 1e-9)
        n_final = len(final_rows)
        # Final permission for each case
        final_emit_summary = {}
        for r in final_rows:
            final_emit_summary[r["case_id"]] = (r["perm_m"], r["A_e_perm"], r["gap"])
        print(f"\n  Path {path_name}:")
        print(f"    cells: {n_cells}")
        print(f"    soundness:     {n_sound}/{n_cells}  ({'PASS' if n_sound == n_cells else 'FAIL'})")
        print(f"    monotone-step: {n_mon_step}/{n_cells}  ({'PASS' if n_mon_step == n_cells else 'FAIL'})")
        print(f"    monotone-k:    {n_mon_k}/{n_cells}  ({'PASS' if n_mon_k == n_cells else 'FAIL'})")
        print(f"    final convergence (last step, k=64): {n_converged}/{n_final}  ({'PASS' if n_converged == n_final else 'FAIL'})")
        # Show divergent finals for non-convergent paths
        if n_converged < n_final:
            print(f"    final emits that disagree with A(e):")
            for cid, (final, ae, gap) in final_emit_summary.items():
                if abs(gap) >= 1e-9:
                    print(f"      {cid}: final={final}  A(e)={ae}  gap={gap:+.4f}")

    # Theorem-prediction verification
    print("\n" + "─" * 100)
    print(" THEOREM PREDICTION VERIFICATION")
    print("─" * 100)
    print("""
  Hypothesis (Item 1a):
    Reconvergence depends only on whether the path's final tail is
    resolving and asymptotically meet-exact. The prefix sets only the
    location and size of transient soundness/monotonicity violations.

  Predictions:
    Path A (resolving tail L4→L0):       reconvergence: YES
    Path B (resolving tail L4→L0):       reconvergence: YES
    Path C (resolving tail L4→L0):       reconvergence: YES
    Path D (no resolving tail, ends L5): reconvergence: NO
""")
    print("  Observed:")
    for path_name in _PATHS.keys():
        path_rows = [r for r in rows if r["path"] == path_name]
        max_step = max(r["step_idx"] for r in path_rows)
        final_rows = [r for r in path_rows if r["step_idx"] == max_step and r["k"] == max(K_LEVELS)]
        n_converged = sum(1 for r in final_rows if abs(r["gap"]) < 1e-9)
        n_final = len(final_rows)
        reconv = n_converged == n_final
        print(f"    Path {path_name}: {n_converged}/{n_final} reconverged  ({'YES' if reconv else 'NO'})")

    # Localization: where do violations occur on each path?
    print("\n" + "─" * 100)
    print(" VIOLATION LOCALIZATION (which step indices carry the failures)")
    print("─" * 100)
    for path_name in _PATHS.keys():
        path_rows = [r for r in rows if r["path"] == path_name]
        path_shape = _PATHS[path_name]
        print(f"\n  Path {path_name}:")
        step_descs = {idx: f"L{lvl}{'!' if not adm else ''}" for idx, lvl, _, adm in path_shape}
        # Soundness violations
        unsound_by_step: dict[int, int] = {}
        mon_step_violations: dict[int, int] = {}
        for r in path_rows:
            if r["sound"] == 0:
                unsound_by_step[r["step_idx"]] = unsound_by_step.get(r["step_idx"], 0) + 1
            if r["monotone_step"] == 0:
                mon_step_violations[r["step_idx"]] = mon_step_violations.get(r["step_idx"], 0) + 1
        if unsound_by_step:
            print(f"    Unsound cells by step:")
            for idx in sorted(unsound_by_step.keys()):
                print(f"      step {idx} ({step_descs[idx]}): {unsound_by_step[idx]} unsound cells")
        else:
            print(f"    No unsound cells.")
        if mon_step_violations:
            print(f"    Monotone-step violations by step:")
            for idx in sorted(mon_step_violations.keys()):
                print(f"      step {idx} ({step_descs[idx]}): {mon_step_violations[idx]} violations")
        else:
            print(f"    No monotone-step violations.")

    print("\n" + "=" * 100)
    print(f"  Wrote: {matrix_path}")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    main()
