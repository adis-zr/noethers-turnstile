"""Item 0 — Audit §2.7 case set for single-requirement-map consistency.

Load-bearing question: do all 21 cases in the v3 §2.7 matrix run under one
requirement map, or does the matrix mix objects?

The §2.7 conclusions (joint convergence, monotonicity, soundness) only make
sense if every case is evaluated against the same requirement map. If S-REF
or other cases use a custom map, the matrix mixes objects and the §2.7
boundary theorems are about a heterogeneous artifact rather than a single
calculus instance.

This script enumerates every case, compares its fine_reqs to the canonical
_default_fine_reqs(), and reports any deviation by (case, permission level,
gap, expected status, actual status).

Decision tree after audit:
  - Zero deviations: §2.7 matrix is clean; user is fully entitled to the
    boundary theorems and ledger rows about §2.7.
  - Isolated deviations confined to cases that DO NOT participate in the
    chain-comparison or boundary claims: scope the v3 text to note that
    those cases are constructed-under-custom-map and exclude them from the
    boundary claims.
  - Load-bearing deviations: §2.7 conclusions need case-by-case re-examination.
    Cases that emit under one map cannot be compared with cases that emit
    under another.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from run_two_axis_convergence_v2 import (  # type: ignore
    _all_cases, _default_fine_reqs,
)

RESULTS_DIR = _HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def _diff_reqs(actual: dict, expected: dict) -> list[dict]:
    """Return per-(level, gap) differences between actual and expected
    requirement maps. Compared key-by-key."""
    diffs: list[dict] = []
    all_levels = set(actual.keys()) | set(expected.keys())
    for level in sorted(all_levels):
        a_reqs = actual.get(level, {})
        e_reqs = expected.get(level, {})
        all_gaps = set(a_reqs.keys()) | set(e_reqs.keys())
        for gap in sorted(all_gaps):
            a_val = a_reqs.get(gap, None)
            e_val = e_reqs.get(gap, None)
            if a_val != e_val:
                diffs.append({
                    "level": level, "gap": gap,
                    "expected": e_val, "actual": a_val,
                })
    return diffs


def main() -> None:
    print("=" * 100)
    print(" Item 0 — Single-requirement-map audit of the §2.7 case set")
    print("=" * 100)

    cases = _all_cases()
    canonical = _default_fine_reqs()

    print(f"\nLoaded {len(cases)} cases.")
    print(f"Canonical (default) requirement map keys: {sorted(canonical.keys())}")
    print(f"Canonical ALR gaps ({len(canonical['ALR'])}): {sorted(canonical['ALR'].keys())}")

    print("\nPer-case deviations from the canonical requirement map:")
    print("-" * 100)
    summary = {}
    n_clean = 0
    n_deviating = 0
    for case in cases:
        cid = case["case_id"]
        family = case["family"]
        diffs = _diff_reqs(case["fine_reqs"], canonical)
        if not diffs:
            n_clean += 1
            print(f"  {cid:>12}  [{family:>16}]  ✓ clean (matches canonical)")
            summary[cid] = {"family": family, "deviates": False, "n_diffs": 0, "diffs": []}
        else:
            n_deviating += 1
            print(f"  {cid:>12}  [{family:>16}]  ✗ DEVIATES — {len(diffs)} diff(s):")
            for d in diffs:
                print(f"      [{d['level']:>3}]  {d['gap']:>32}  expected={d['expected']}  actual={d['actual']}")
            summary[cid] = {"family": family, "deviates": True, "n_diffs": len(diffs),
                             "diffs": diffs}

    print("\n" + "-" * 100)
    print(" SUMMARY")
    print("-" * 100)
    print(f"  Clean (matches canonical): {n_clean}/{len(cases)}")
    print(f"  Deviating: {n_deviating}/{len(cases)}")

    # Classify deviations
    deviating_by_family: dict[str, list[str]] = {}
    for cid, info in summary.items():
        if info["deviates"]:
            deviating_by_family.setdefault(info["family"], []).append(cid)

    print("\n  Deviating cases by family:")
    for family, cids in sorted(deviating_by_family.items()):
        print(f"    {family}: {cids}")

    # Check whether deviations affect the standard chain levels {REF, DIA, REV, AEX, ALR}.
    # AAA mirrors ALR in canonical, but witnesses sync AAA to a stricter ALR; that's
    # not a load-bearing deviation if the authority_ceiling is ALR.
    print("\n  Per-level deviation impact (load-bearing chain levels DIA / REV / AEX / ALR):")
    levels_of_interest = ["DIA", "REV", "AEX", "ALR"]
    for level in levels_of_interest:
        affected = []
        for cid, info in summary.items():
            if any(d["level"] == level for d in info["diffs"]):
                affected.append(cid)
        if affected:
            print(f"    {level}: {len(affected)} case(s) deviate — {affected}")
        else:
            print(f"    {level}: 0 cases deviate ✓")

    # The AAA deviation should be classified separately since the ceiling caps emit to ALR
    aaa_only_deviations = []
    chain_deviations = []
    for cid, info in summary.items():
        if not info["deviates"]:
            continue
        levels_touched = {d["level"] for d in info["diffs"]}
        if levels_touched == {"AAA"}:
            aaa_only_deviations.append(cid)
        elif "AAA" in levels_touched and not (levels_touched - {"AAA"}):
            aaa_only_deviations.append(cid)
        else:
            chain_deviations.append(cid)

    print(f"\n  Classification of deviations:")
    print(f"    AAA-only deviations (not load-bearing — authority_ceiling caps emit to ALR):")
    print(f"      {aaa_only_deviations}")
    print(f"    Chain-level deviations (potentially load-bearing — touch DIA/REV/AEX/ALR):")
    print(f"      {chain_deviations}")

    # Verdict
    print("\n  VERDICT:")
    if not chain_deviations:
        print("    All deviations are AAA-only or absent. The §2.7 chain-level results")
        print("    (DIA/REV/AEX/ALR) are evaluated under a single canonical requirement")
        print("    map. The matrix is CLEAN at the chain level.")
        verdict = "clean_at_chain_level"
    else:
        print(f"    {len(chain_deviations)} case(s) deviate at chain levels. These are:")
        for cid in chain_deviations:
            info = summary[cid]
            chain_diffs = [d for d in info["diffs"] if d["level"] in levels_of_interest]
            print(f"      {cid}: {len(chain_diffs)} chain-level diff(s)")
            for d in chain_diffs:
                print(f"        [{d['level']}] {d['gap']}  expected={d['expected']}  actual={d['actual']}")
        verdict = "deviates_at_chain_level"

    # Write outputs
    output = {
        "n_cases": len(cases),
        "n_clean": n_clean,
        "n_deviating": n_deviating,
        "aaa_only_deviations": aaa_only_deviations,
        "chain_level_deviations": chain_deviations,
        "verdict": verdict,
        "per_case": summary,
    }
    json_path = RESULTS_DIR / "reqmap_audit.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Wrote: {json_path}")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    main()
