"""Inverse compiler — recover requirement-map structure from emits alone.

The forward compiler takes (gaps, chain, requirements) → emit per case.
This script does the reverse: given only (case, gap_statuses, emit), it
attempts to recover:

  1. Chain length and order (distinct emits in the data).
  2. For each adjacent emit boundary, the gating gap(s).
  3. Recovered requirement: minimum gap status to reach each level.
  4. Identifiability classes: gaps the data cannot separate.
  5. Unobservable gaps: never the discriminating axis.

The procedure produces a "compass" for chosen domains: given a deployed
compiler's emit map across cases, what gap taxonomy and chain structure
is *minimally consistent* with what it does? This is the inverse of the
forward compiler — and the inverse of the induction loop, which needs
expert verdicts. This procedure needs only emits.

We test it on the 21-case Epic corpus:
  M01–M07 induction
  H01–H05 held-out
  S-REF, S-DIA, S-REV, S-AEX, S-ALR synthetic ladder
  W-currency, W-deployment, W-population, W-clinical active witnesses

The Epic requirement map is the ground truth. We hide it, feed the inverse
procedure only (case → gap_statuses → emit) tuples (with emit computed by
the honest compiler), and ask: how well does the procedure recover the
ground-truth requirement map?

Predicted result:
  Chain: recovered exactly (5 levels in standard chain + ROL where present).
  Gaps gating REV/AEX boundaries (S1, S2): recovered as distinct gates.
  Gaps gating ALR boundary (G1–G7 / blast_radius / authority etc):
    recovered as a single identifiability class — the data does not
    distinguish them because each induction case opens exactly one.
  Active witnesses: confirm individual gates because each varies one gap.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Iterable

_HERE = Path(__file__).resolve().parent
_WORKSPACE_PY = _HERE.parents[1] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

# Reuse the v2 two-axis machinery's case generation + compile rules.
sys.path.insert(0, str(_HERE))
from run_two_axis_convergence_v2 import (  # type: ignore
    _all_cases, _project_statuses, _project_requirements_join,
    _compile_case, _LEVEL_0_GROUPS, _FINE_GAPS,
)

RESULTS_DIR = _HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Permission rank ordering matches v2.
_PERM_TO_RANK = {"REF": 0, "DIA": 1, "REV": 2, "AEX": 3, "ALR": 4}
_RANK_TO_PERM = {v: k for k, v in _PERM_TO_RANK.items()}

# Status rank ordering.
_STATUS_RANK = {"open": 0, "bounded": 1, "closed": 2}
_RANK_STATUS = {v: k for k, v in _STATUS_RANK.items()}


# ── Forward step: compute emit per case (the "observed" data) ──────────────────

def compute_observed_emits(cases: list[dict]) -> list[dict]:
    """Run the honest compiler on each case at L0 to produce the emit data
    the inverse procedure will see. The requirement map is used here but
    hidden from the procedure below."""
    rows = []
    for case in cases:
        proj_statuses = _project_statuses(case["gap_statuses"], _LEVEL_0_GROUPS)
        proj_reqs = _project_requirements_join(case["fine_reqs"], _LEVEL_0_GROUPS)
        emit = _compile_case(
            proj_statuses, proj_reqs, f"compass-{case['case_id']}"
        )
        rows.append({
            "case_id": case["case_id"],
            "family": case["family"],
            "gap_statuses": dict(proj_statuses),
            "emit": emit,
        })
    return rows


# ── Inverse procedure ─────────────────────────────────────────────────────────

def recover_chain(rows: list[dict]) -> list[str]:
    """Step 1 — distinct emits observed, in rank order."""
    emits = {r["emit"] for r in rows}
    return sorted(emits, key=lambda p: _PERM_TO_RANK[p])


def find_gap_universe(rows: list[dict]) -> list[str]:
    """All gaps that appear in any case's status dict."""
    universe = set()
    for r in rows:
        universe.update(r["gap_statuses"].keys())
    return sorted(universe)


def detect_covariation(rows: list[dict], gaps: list[str]) -> list[set[str]]:
    """Step 6 — gaps that always have the same status across all cases form
    perfectly co-varying equivalence classes. The data cannot separate them."""
    classes: dict[tuple, set[str]] = defaultdict(set)
    for g in gaps:
        # signature: tuple of statuses across cases in deterministic order
        sig = tuple(r["gap_statuses"].get(g, "open") for r in rows)
        classes[sig].add(g)
    return [s for s in classes.values() if len(s) > 1]


def detect_invariant_gaps(rows: list[dict], gaps: list[str]) -> list[str]:
    """Gaps that never vary in status across the data. Their requirement is
    unobservable: we don't know what status they actually need."""
    invariant = []
    for g in gaps:
        statuses = {r["gap_statuses"].get(g, "open") for r in rows}
        if len(statuses) == 1:
            invariant.append(g)
    return invariant


def find_boundary_candidates(
    rows: list[dict], chain: list[str]
) -> dict[tuple[str, str], dict]:
    """Step 2-3 — for each adjacent (p_low, p_high) pair, find the gating
    gap candidates.

    Returns dict keyed by (p_low, p_high) with:
      - case_pairs: list of (case_low, case_high) pairs straddling the boundary
      - min_delta_size: smallest |gap-set Δ| observed
      - single_gap_gates: gaps for which a case pair with |Δ|=1 exists
      - candidate_gates: union of Δ across all pairs with size == min_delta_size
    """
    boundaries: dict[tuple[str, str], dict] = {}
    for i in range(len(chain) - 1):
        p_low, p_high = chain[i], chain[i + 1]
        low_cases = [r for r in rows if r["emit"] == p_low]
        high_cases = [r for r in rows if r["emit"] == p_high]
        pairs = []
        for cl in low_cases:
            for ch in high_cases:
                delta = {
                    g for g in cl["gap_statuses"]
                    if cl["gap_statuses"].get(g, "open") != ch["gap_statuses"].get(g, "open")
                }
                # Also pick up gaps in ch but not cl
                for g in ch["gap_statuses"]:
                    if cl["gap_statuses"].get(g, "open") != ch["gap_statuses"].get(g, "open"):
                        delta.add(g)
                pairs.append({"case_low": cl["case_id"], "case_high": ch["case_id"],
                              "delta": sorted(delta)})
        if not pairs:
            boundaries[(p_low, p_high)] = {"case_pairs": [], "min_delta_size": None,
                                            "single_gap_gates": [], "candidate_gates": []}
            continue
        min_delta_size = min(len(p["delta"]) for p in pairs)
        single_gap_gates = sorted({p["delta"][0] for p in pairs if len(p["delta"]) == 1})
        candidate_gates = sorted({g for p in pairs if len(p["delta"]) == min_delta_size for g in p["delta"]})
        boundaries[(p_low, p_high)] = {
            "case_pairs": pairs,
            "min_delta_size": min_delta_size,
            "single_gap_gates": single_gap_gates,
            "candidate_gates": candidate_gates,
        }
    return boundaries


def extract_requirements(
    rows: list[dict], chain: list[str], boundaries: dict
) -> dict[str, dict[str, str]]:
    """Step 4 — for each gap identified as gating a boundary, recover the
    minimum status required to reach that level, and propagate inherited
    requirements upward.

    A real permission chain is monotone in requirements: if level p requires
    gap g at status s, then every level above p also requires g at status s
    (or stricter). We recover requirements at each boundary then propagate
    upward to reflect this inheritance.
    """
    # First pass: gates per boundary (the "new" requirements at each step).
    boundary_reqs: dict[str, dict[str, str]] = {p: {} for p in chain}
    for (p_low, p_high), info in boundaries.items():
        gates = info["single_gap_gates"] or info["candidate_gates"]
        for g in gates:
            statuses_at_or_above = [
                _STATUS_RANK[r["gap_statuses"].get(g, "open")]
                for r in rows
                if _PERM_TO_RANK[r["emit"]] >= _PERM_TO_RANK[p_high]
            ]
            if statuses_at_or_above:
                min_status = _RANK_STATUS[min(statuses_at_or_above)]
                boundary_reqs[p_high][g] = min_status

    # Second pass: inherit upward.
    recovered: dict[str, dict[str, str]] = {}
    accumulated: dict[str, str] = {}
    for level in chain:
        new_at_this_level = boundary_reqs.get(level, {})
        accumulated = {**accumulated, **new_at_this_level}
        recovered[level] = dict(accumulated)
    return recovered


def identifiability_report(boundaries: dict, covariation_classes: list[set[str]],
                            invariant_gaps: list[str], gap_universe: list[str]) -> dict:
    """Step 5-6 — produce diagnostics."""
    confirmed_gates: dict[tuple[str, str], list[str]] = {}
    ambiguous_gates: dict[tuple[str, str], list[str]] = {}
    for b_key, info in boundaries.items():
        if info["single_gap_gates"]:
            confirmed_gates[b_key] = info["single_gap_gates"]
        elif info["candidate_gates"]:
            ambiguous_gates[b_key] = info["candidate_gates"]

    # Gaps that appear in any confirmed or ambiguous boundary
    identified = set()
    for gs in confirmed_gates.values():
        identified.update(gs)
    for gs in ambiguous_gates.values():
        identified.update(gs)

    unobservable = sorted(set(gap_universe) - identified - set(invariant_gaps))
    return {
        "confirmed_gates": {f"{k[0]}→{k[1]}": v for k, v in confirmed_gates.items()},
        "ambiguous_gates": {f"{k[0]}→{k[1]}": v for k, v in ambiguous_gates.items()},
        "covarying_classes": [sorted(c) for c in covariation_classes],
        "invariant_gaps": invariant_gaps,
        "unobservable_or_inactive": unobservable,
        "identified_gaps": sorted(identified),
    }


# ── Driver ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 100)
    print(" Compass — inverse procedure: emit map → recovered requirement structure")
    print(" Applied to the 21-case Epic corpus")
    print("=" * 100)

    cases = _all_cases()
    print(f"\n  Loaded {len(cases)} cases")
    family_counts = defaultdict(int)
    for c in cases:
        family_counts[c["family"]] += 1
    print(f"  By family: {dict(family_counts)}")

    # Step 0: compute observed emits (forward compiler)
    rows = compute_observed_emits(cases)
    print(f"\n  Observed emits per case:")
    for r in rows:
        print(f"    {r['case_id']:>12}  [{r['family']:>16}]  emit={r['emit']}")

    # ── Inverse procedure ────────────────────────────────────────────────────
    print("\n" + "-" * 100)
    print(" INVERSE PROCEDURE")
    print("-" * 100)

    # Step 1: chain
    chain = recover_chain(rows)
    print(f"\n  Step 1 — Recovered chain ({len(chain)} levels): {' ≺ '.join(chain)}")

    # Universe of gaps in the data
    gap_universe = find_gap_universe(rows)
    print(f"\n  Gap universe in data ({len(gap_universe)} gaps): {gap_universe}")

    # Step 6: co-variation
    covariation = detect_covariation(rows, gap_universe)
    print(f"\n  Step 6 — Co-varying gap classes (cannot be separated): {len(covariation)} class(es)")
    for c in covariation:
        print(f"    {sorted(c)}")

    # Step 5: invariant gaps
    invariant = detect_invariant_gaps(rows, gap_universe)
    print(f"\n  Step 5 — Invariant gaps (never vary; requirement unobservable): {invariant}")

    # Step 2-3: boundary candidates
    boundaries = find_boundary_candidates(rows, chain)
    print(f"\n  Step 2-3 — Boundary candidates:")
    for (p_low, p_high), info in boundaries.items():
        single = info["single_gap_gates"]
        candidate = info["candidate_gates"]
        n_pairs = len(info["case_pairs"])
        min_delta = info["min_delta_size"]
        print(f"    Boundary {p_low} → {p_high}:")
        print(f"      pairs observed: {n_pairs}")
        print(f"      min |Δ| across pairs: {min_delta}")
        if single:
            print(f"      ✓ CONFIRMED single-gap gates: {single}")
        if candidate and not single:
            print(f"      ? AMBIGUOUS gating class (|Δ|={min_delta}): {candidate}")

    # Step 4: requirements
    recovered_reqs = extract_requirements(rows, chain, boundaries)
    print(f"\n  Step 4 — Recovered requirements (min status to reach each level):")
    for level in chain:
        if recovered_reqs[level]:
            print(f"    {level}: {recovered_reqs[level]}")

    # Identifiability report
    report = identifiability_report(boundaries, covariation, invariant, gap_universe)
    print(f"\n  Identifiability summary:")
    print(f"    Confirmed gates (single-gap):  {report['confirmed_gates']}")
    print(f"    Ambiguous gates (gap classes): {report['ambiguous_gates']}")
    print(f"    Identified gaps total: {len(report['identified_gaps'])} / {len(gap_universe)}")
    print(f"    Identified gaps:  {report['identified_gaps']}")
    print(f"    Unobservable / inactive: {report['unobservable_or_inactive']}")

    # ── Ground-truth comparison ──────────────────────────────────────────────
    print("\n" + "-" * 100)
    print(" GROUND-TRUTH COMPARISON")
    print("-" * 100)

    # Ground truth: default Epic requirements (skeleton + uniform-bounded ALR)
    from run_two_axis_convergence_v2 import _default_fine_reqs  # type: ignore
    truth_reqs = _default_fine_reqs()
    # Filter to only the levels in the recovered chain
    truth_for_chain = {p: truth_reqs.get(p, {}) for p in chain}

    print(f"\n  Ground-truth requirements per level (with witnesses' strict reqs ignored):")
    for level in chain:
        if truth_for_chain.get(level):
            print(f"    {level}: {truth_for_chain[level]}")

    # Per-level comparison
    print(f"\n  Per-level recovery audit:")
    for level in chain:
        gt = truth_for_chain.get(level, {})
        rec = recovered_reqs.get(level, {})
        gt_set = set(gt.keys())
        rec_set = set(rec.keys())
        matched = gt_set & rec_set
        only_in_truth = gt_set - rec_set
        only_in_recovered = rec_set - gt_set
        # Of the matched gaps, do the statuses match?
        status_matches = sum(1 for g in matched if gt.get(g) == rec.get(g))
        print(f"    {level}:")
        print(f"      truth gaps: {sorted(gt_set)}")
        print(f"      recovered:  {sorted(rec_set)}")
        if matched:
            print(f"      matched: {sorted(matched)} (status matches: {status_matches}/{len(matched)})")
        if only_in_truth:
            print(f"      missed by procedure (in truth, not recovered): {sorted(only_in_truth)}")
        if only_in_recovered:
            print(f"      false-positive (in recovered, not truth): {sorted(only_in_recovered)}")

    # Chain length comparison
    truth_chain = ["DIA", "REV", "AEX", "ALR"]  # REF and AAA not used as named emit levels in standard Epic
    # The standard Epic profile doesn't include REF, but the compiler can fall back to REF for S-REF.
    # The observed chain may include REF and DIA depending on cases.
    print(f"\n  Chain comparison:")
    print(f"    Truth chain (standard Epic, named levels): REF ≺ DIA ≺ REV ≺ AEX ≺ ALR")
    print(f"    Recovered chain: {' ≺ '.join(chain)}")

    # ── Write outputs ────────────────────────────────────────────────────────
    csv_path = RESULTS_DIR / "compass_observed_emits.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "family", "emit"] + gap_universe)
        for r in rows:
            row = [r["case_id"], r["family"], r["emit"]]
            for g in gap_universe:
                row.append(r["gap_statuses"].get(g, "open"))
            writer.writerow(row)

    output = {
        "n_cases": len(rows),
        "recovered_chain": chain,
        "gap_universe": gap_universe,
        "covarying_classes": [sorted(c) for c in covariation],
        "invariant_gaps": invariant,
        "boundaries": {
            f"{k[0]}→{k[1]}": {
                "n_pairs": len(info["case_pairs"]),
                "min_delta_size": info["min_delta_size"],
                "single_gap_gates": info["single_gap_gates"],
                "candidate_gates": info["candidate_gates"],
            }
            for k, info in boundaries.items()
        },
        "recovered_requirements": recovered_reqs,
        "identifiability_report": report,
        "ground_truth_requirements": truth_for_chain,
    }
    json_path = RESULTS_DIR / "compass_summary.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n  Wrote: {csv_path}")
    print(f"         {json_path}")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    main()
