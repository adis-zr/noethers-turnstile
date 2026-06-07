"""Experiment A — 3GPP extraction-operator stability.

Pre-registered spec: docs/papers/prereg_three_gaps.md
Timestamp: 2026-06-02T02:31:44Z

Tests whether BLER = 0.10 and BLER = 0.02 are hierarchy-independent attractors
of the BER/BLER evidence surface, or artifacts of permission placement.

Perturbation grid (fixed in spec):
  Family 1 — Granularity: m = 3,4,5,6,8 levels, log-uniform over [1e-3, 0.50]
  Family 2 — Offset: baseline 5-level shifted by 0.5x, 0.7x, 1.4x, 2.0x
  Family 3 — Random: N=50 hierarchies, m ~ Uniform{3..8}, seed=42

Tolerance: ±25% multiplicative (target t recovered if boundary in [0.75t, 1.25t])

Decision rule (from spec):
  STABLE   if min(p_010, p_002) >= 0.80
  RELATIVE if min(p_010, p_002) <  0.80

Outputs written to results/experiment_a_stability.csv and printed to stdout.
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from ber_bler_curves import bler_at_snr, ber_at_snr

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── Parameters (all fixed in pre-registration) ────────────────────────────────

SNR_FINE = np.round(np.arange(-1.0, 5.01, 0.1), 2)       # 61 points, 0.1 dB steps
BLER_RANGE_LOW  = 1e-3
BLER_RANGE_HIGH = 0.50
TARGETS = {0.10: "0.10", 0.02: "0.02"}
TOLERANCE = 0.25   # ±25% multiplicative
RANDOM_SEED = 42
N_RANDOM = 50

# ── Evidence surface ──────────────────────────────────────────────────────────

BLER_VALS = np.array([bler_at_snr(s) for s in SNR_FINE])


# ── Boundary extraction ───────────────────────────────────────────────────────

def boundary_set(ceilings: list[float]) -> list[float]:
    """Return the BLER values at which the compiler's permission changes.

    The compiler maps each SNR point to the strongest permission whose BLER
    ceiling is met. A boundary occurs where that permission level increases
    as SNR improves (BLER decreases). The boundary value is the ceiling that
    is crossed — i.e., the ceiling that becomes satisfiable at that SNR.

    ceilings: descending list of BLER ceilings [c1 > c2 > ... > cm].
    Returns: list of BLER ceiling values that are realized as transitions.
    """
    ceilings_desc = sorted(ceilings, reverse=True)

    def permission(bler: float) -> int:
        for i, c in enumerate(ceilings_desc):
            if bler <= c:
                return i
        return -1  # REFUSE

    boundaries = []
    prev_perm = permission(BLER_VALS[0])
    for bler in BLER_VALS[1:]:
        p = permission(bler)
        if p > prev_perm:
            # Transition occurred — the ceiling that was just crossed
            # is ceilings_desc[prev_perm + 1] ... but we want the BLER
            # ceiling value that enabled the new permission level.
            # That is ceilings_desc[p] (the ceiling for the new level).
            boundaries.append(ceilings_desc[p])
            prev_perm = p

    return boundaries


def recovers_target(bset: list[float], target: float, tol: float) -> bool:
    """True if any boundary in bset is within ±tol (multiplicative) of target."""
    lo = target * (1.0 - tol)
    hi = target * (1.0 + tol)
    return any(lo <= b <= hi for b in bset)


# ── Hierarchy families ────────────────────────────────────────────────────────

def family1_granularity() -> list[tuple[str, list[float]]]:
    """Log-uniform ceilings, no pin at targets. m = 3,4,5,6,8."""
    hierarchies = []
    for m in [3, 4, 5, 6, 8]:
        ceilings = list(np.logspace(
            np.log10(BLER_RANGE_LOW),
            np.log10(BLER_RANGE_HIGH),
            m
        ))
        hierarchies.append((f"gran_m{m}", ceilings))
    return hierarchies


def family2_offset() -> list[tuple[str, list[float]]]:
    """Baseline 5-level log-uniform shifted by multiplicative offsets."""
    base = list(np.logspace(
        np.log10(BLER_RANGE_LOW),
        np.log10(BLER_RANGE_HIGH),
        5
    ))
    hierarchies = []
    for factor in [0.5, 0.7, 1.4, 2.0]:
        shifted = [min(c * factor, 1.0) for c in base]
        # Remove any that collapse below the BLER surface floor
        shifted = [c for c in shifted if c >= BLER_VALS.min()]
        if len(shifted) >= 2:
            hierarchies.append((f"offset_{factor:.1f}x", shifted))
    return hierarchies


def family3_random() -> list[tuple[str, list[float]]]:
    """N=50 random hierarchies, m ~ Uniform{3..8}, seed=42."""
    rng = np.random.default_rng(RANDOM_SEED)
    hierarchies = []
    for i in range(N_RANDOM):
        m = int(rng.integers(3, 9))  # 3..8 inclusive
        ceilings = list(np.sort(rng.uniform(
            np.log10(BLER_RANGE_LOW),
            np.log10(BLER_RANGE_HIGH),
            m
        )))
        ceilings = [10 ** c for c in ceilings]
        hierarchies.append((f"rand_{i:02d}_m{m}", ceilings))
    return hierarchies


# ── Main experiment ───────────────────────────────────────────────────────────

def run() -> None:
    all_hierarchies = (
        family1_granularity() +
        family2_offset() +
        family3_random()
    )

    total = len(all_hierarchies)
    assert total == 59, f"Expected 59 hierarchies, got {total}"

    rows = []
    recoveries = {t: 0 for t in TARGETS}

    for name, ceilings in all_hierarchies:
        bset = boundary_set(ceilings)
        rec = {t: recovers_target(bset, t, TOLERANCE) for t in TARGETS}
        for t in TARGETS:
            if rec[t]:
                recoveries[t] += 1
        # Determine family
        if name.startswith("gran"):
            family = "granularity"
        elif name.startswith("offset"):
            family = "offset"
        else:
            family = "random"
        rows.append({
            "hierarchy":     name,
            "family":        family,
            "n_levels":      len(ceilings),
            "ceilings":      ";".join(f"{c:.4e}" for c in sorted(ceilings, reverse=True)),
            "boundaries":    ";".join(f"{b:.4e}" for b in bset),
            "recovers_0.10": int(rec[0.10]),
            "recovers_0.02": int(rec[0.02]),
        })

    p_010 = recoveries[0.10] / total
    p_002 = recoveries[0.02] / total
    min_p = min(p_010, p_002)
    decision = "STABLE" if min_p >= 0.80 else "RELATIVE"

    # Per-family breakdown
    family_counts: dict[str, dict] = {}
    for row in rows:
        f = row["family"]
        if f not in family_counts:
            family_counts[f] = {"n": 0, "r010": 0, "r002": 0}
        family_counts[f]["n"] += 1
        family_counts[f]["r010"] += row["recovers_0.10"]
        family_counts[f]["r002"] += row["recovers_0.02"]

    # Write CSV
    out_path = os.path.join(RESULTS_DIR, "experiment_a_stability.csv")
    fields = ["hierarchy", "family", "n_levels", "ceilings", "boundaries",
              "recovers_0.10", "recovers_0.02"]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # Print results
    print("=" * 70)
    print("  EXPERIMENT A — 3GPP EXTRACTION-OPERATOR STABILITY")
    print(f"  Pre-reg timestamp: 2026-06-02T02:31:44Z")
    print(f"  Tolerance: ±{TOLERANCE*100:.0f}% multiplicative")
    print(f"  Total hierarchies: {total}")
    print("=" * 70)

    print(f"\n  POOLED RESULTS")
    print(f"  {'Target':>8}  {'Recoveries':>12}  {'Fraction':>10}")
    print(f"  {'─'*36}")
    print(f"  {'0.10':>8}  {recoveries[0.10]:>12}/{total}  {p_010:>10.3f}")
    print(f"  {'0.02':>8}  {recoveries[0.02]:>12}/{total}  {p_002:>10.3f}")
    print(f"\n  min(p_010, p_002) = {min_p:.3f}  (threshold: 0.800)")
    print(f"\n  DECISION: {decision}")

    print(f"\n  PER-FAMILY BREAKDOWN")
    print(f"  {'Family':>14}  {'n':>4}  {'p(0.10)':>9}  {'p(0.02)':>9}")
    print(f"  {'─'*42}")
    for fname, fc in sorted(family_counts.items()):
        n = fc["n"]
        p1 = fc["r010"] / n
        p2 = fc["r002"] / n
        print(f"  {fname:>14}  {n:>4}  {p1:>9.3f}  {p2:>9.3f}")

    print(f"\n  Written: {out_path}")
    print("=" * 70)

    # Print pre-registered outcome paragraph
    print("\n  PRE-REGISTERED OUTCOME PARAGRAPH (for execution log):\n")
    if decision == "STABLE":
        print(f"""\
  The boundaries are not artifacts of permission placement. Across {total} permission
  hierarchies spanning 3–8 levels and multiplicative placements offset by up to
  2x, the extraction operator recovers BLER 0.10 and 0.02 in {p_010*100:.1f}% and
  {p_002*100:.1f}% of hierarchies respectively, without any hierarchy pinned at those
  values. The targets are attractors of the BER/BLER evidence surface: the points
  where the change from bit-level evidence to block-level reliability most strongly
  shifts the licensable permission, independent of how the permission axis is
  quantized. The 3GPP match is therefore a recovery of the evidence surface, not a
  reflection of the supplied hierarchy.""")
    else:
        print(f"""\
  The 3GPP result is representation-relative, and the perturbation experiment
  establishes this precisely rather than leaving it open. Across {total} permission
  hierarchies, the extraction operator recovers BLER 0.10 in {p_010*100:.1f}% and 0.02
  in {p_002*100:.1f}% of cases; the recovered boundaries track the placement of the
  permission ceilings rather than a hierarchy-independent feature of the surface.
  The claim the data support is the narrower one: once a BER/BLER representation and
  a block-level permission granularity are fixed without reading the standard, the
  compiler's boundaries align with the thresholds 3GPP later names. This is a blind,
  representation-relative alignment, not a free-standing discovery of the service
  thresholds. It locates the boundary of the method in this domain: the evidence
  surface constrains the boundary, but the permission granularity co-determines it.""")

    print()


if __name__ == "__main__":
    run()
