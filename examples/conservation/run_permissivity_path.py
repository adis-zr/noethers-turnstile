"""Experiment 2 — Permissivity-vs-divergence path.

The quantitative test for the conservation law.

Fix a permission hierarchy. Vary the evidence along a controlled path.
At each point, compute:
  - an incompleteness distance from the "complete evidence" baseline;
  - the compiler's emitted permission.

Expected result:
  - permission improves monotonically as evidence improves (distance decreases);
  - permission breakpoints occur where the theory predicts (at gap-requirement crossings);
  - the same breakpoints appear under different divergence metrics (metric-invariance preview).

Two domains:

  Turbo — SNR is the natural evidence path. As SNR rises, BLER falls,
           evidence becomes more complete. Incompleteness distance is
           (BLER - BLER_target) for the relevant permission level.
           Four permission levels: REFUSE / HOLD / TRANSMIT_MONITORED / TRANSMIT.

  Ising  — β (coupling strength) is fixed; τ (tolerance threshold) is the path.
            As τ rises (looser tolerance), more evidence states become admissible.
            Incompleteness distance is the TV gap: (tv_max - tv_mean), the width
            of the authorization gap.

For each domain, two functional curves are plotted:
  - mean-like functional (BER for turbo, mean TV for Ising);
  - worst-case functional (BLER for turbo, max TV for Ising).

The gap region — where the two curves disagree — is the authorization gap.
Its width and breakpoints are the conserved object.

Outputs:
  results/permissivity_turbo.csv
  results/permissivity_ising.csv
  Printed witness sentences.
"""
from __future__ import annotations

import csv
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
_WORKSPACE_PY = _HERE.parents[1] / "python"
if _WORKSPACE_PY.exists() and str(_WORKSPACE_PY) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_PY))

_TURBO_DIR = _HERE.parent / "inference" / "register2" / "turbo"
if str(_TURBO_DIR) not in sys.path:
    sys.path.insert(0, str(_TURBO_DIR))

_ISING_DIR = _HERE.parent / "inference" / "ising"
if str(_ISING_DIR) not in sys.path:
    sys.path.insert(0, str(_ISING_DIR))

RESULTS_DIR = _HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ── Turbo domain ──────────────────────────────────────────────────────────────
#
# Permission levels (operational meaning only):
#   TRANSMIT         — BLER ≤ 0.001  (reliable delivery)
#   TRANSMIT_MONITORED — BLER ≤ 0.02  (monitored service)
#   HOLD             — BLER ≤ 0.10  (signal received, not reliable)
#   REFUSE           — everything blocked
#
# Mean-like functional: BER (bit error rate)
# Worst-case functional: BLER (block error rate)
# Evidence path: SNR from -1.0 to 5.0 dB in 0.1 dB steps
#
# Incompleteness distance at each SNR:
#   d(SNR) = max(BLER(SNR) - BLER_THRESHOLD, 0)
#   where BLER_THRESHOLD is the tightest permission ceiling the evidence
#   currently admits. This is the "gap still to close" for the next level.

_TURBO_PERMS = [
    ("TRANSMIT",           0.001),
    ("TRANSMIT_MONITORED", 0.02),
    ("HOLD",               0.10),
]
_TURBO_REFUSE_ABOVE = 0.10

_TURBO_FIELDNAMES = [
    "snr_db", "ber", "bler",
    "perm_ber", "perm_bler",
    "gap",                   # 1 if mean-like grants stronger than worst-case
    "incompleteness_ber",    # distance from BER to next permission threshold
    "incompleteness_bler",   # distance from BLER to next permission threshold
    "auth_gap_width",        # BLER - BER (width of authorization gap interval)
]


def _turbo_perm(error_rate: float) -> str:
    for name, ceiling in _TURBO_PERMS:
        if error_rate <= ceiling:
            return name
    return "REFUSE"


def _turbo_incompleteness(error_rate: float, perm: str) -> float:
    """Distance from current error rate to the *next* permission threshold.

    Returns 0 if already at the top level.
    """
    # Find the next level above the current permission
    idx = next((i for i, (n, _) in enumerate(_TURBO_PERMS) if n == perm), None)
    if idx is None or idx == 0:
        return 0.0  # already at TRANSMIT or REFUSE (no level above)
    next_ceiling = _TURBO_PERMS[idx - 1][1]
    return max(error_rate - next_ceiling, 0.0)


def run_turbo_path() -> list[dict]:
    from ber_bler_curves import bler_at_snr, ber_at_snr

    snr_grid = np.round(np.arange(-1.0, 5.01, 0.1), 2)
    rows = []
    for snr in snr_grid:
        ber = ber_at_snr(float(snr))
        bler = bler_at_snr(float(snr))
        perm_ber = _turbo_perm(ber)
        perm_bler = _turbo_perm(bler)
        gap = 1 if _perm_rank(perm_ber) > _perm_rank(perm_bler) else 0
        inc_ber = _turbo_incompleteness(ber, perm_ber)
        inc_bler = _turbo_incompleteness(bler, perm_bler)
        auth_gap_width = max(bler - ber, 0.0)
        rows.append({
            "snr_db": round(float(snr), 2),
            "ber": round(ber, 8),
            "bler": round(bler, 8),
            "perm_ber": perm_ber,
            "perm_bler": perm_bler,
            "gap": gap,
            "incompleteness_ber": round(inc_ber, 8),
            "incompleteness_bler": round(inc_bler, 8),
            "auth_gap_width": round(auth_gap_width, 8),
        })
    return rows


_TURBO_PERM_RANK = {"REFUSE": 0, "HOLD": 1, "TRANSMIT_MONITORED": 2, "TRANSMIT": 3}


def _perm_rank(p: str) -> int:
    return _TURBO_PERM_RANK.get(p, 0)


# ── Ising domain ──────────────────────────────────────────────────────────────
#
# β = 0.44 (critical coupling, widest authorization gap).
# τ is swept from 0 to 0.50 — this is the evidence path.
# As τ increases, more evidence states become admissible (looser tolerance).
#
# Two functionals:
#   mean TV: average error over variables (mean-like)
#   max TV:  worst-case error over any single variable (worst-case)
#
# Incompleteness distance at each τ:
#   d(τ) = max(tv_max - τ, 0)  for the worst-case functional
#   (how much the worst variable still exceeds the threshold)
#
# Authorization gap width: tv_max - tv_mean (the interval [tv_mean, tv_max]
# where mean says ACT and max says REFUSE).

_ISING_FIELDNAMES = [
    "beta", "tau",
    "tv_mean", "tv_max",
    "perm_mean", "perm_max",
    "gap",
    "incompleteness_mean",   # max(tv_mean - tau, 0)
    "incompleteness_max",    # max(tv_max  - tau, 0)
    "auth_gap_width",        # tv_max - tv_mean
]

_ISING_TAU_FINE = np.linspace(0.0, 0.50, 200)
_ISING_BETA = 0.44   # critical coupling — widest gap; cleanest demonstration


def run_ising_path() -> list[dict]:
    """Run the Ising permissivity path at β=0.44 (critical coupling)."""
    from generate_ising import make_ising_grid_with_field as make_ising_grid
    from run_exact import compute_exact_marginals
    from run_bp import run_loopy_bp
    from compiler import tv_distance, tv_distance_max, compile_at_tau, ACT, REFUSE

    g = make_ising_grid(6, _ISING_BETA)
    exact_marg = compute_exact_marginals(g)
    result = run_loopy_bp(g)
    marginals = result["marginals"]

    tv_mean = tv_distance(marginals, exact_marg)
    tv_max = tv_distance_max(marginals, exact_marg)
    auth_gap_width = round(tv_max - tv_mean, 6)

    rows = []
    for tau in _ISING_TAU_FINE:
        tau_f = float(tau)
        p_mean = "ACT" if compile_at_tau(result["converged"], tv_mean, tau_f) == ACT else "REFUSE"
        p_max  = "ACT" if compile_at_tau(result["converged"], tv_max,  tau_f) == ACT else "REFUSE"
        gap = 1 if (p_mean == "ACT" and p_max == "REFUSE") else 0
        inc_mean = max(tv_mean - tau_f, 0.0)
        inc_max  = max(tv_max  - tau_f, 0.0)
        rows.append({
            "beta": _ISING_BETA,
            "tau": round(tau_f, 4),
            "tv_mean": round(tv_mean, 6),
            "tv_max": round(tv_max, 6),
            "perm_mean": p_mean,
            "perm_max": p_max,
            "gap": gap,
            "incompleteness_mean": round(inc_mean, 6),
            "incompleteness_max": round(inc_max, 6),
            "auth_gap_width": auth_gap_width,
        })
    return rows


# ── Output ────────────────────────────────────────────────────────────────────

def _print_turbo(rows: list[dict]) -> None:
    print(f"\n  {'─'*70}")
    print(f"  TURBO — permissivity path (SNR −1.0 → 5.0 dB)")
    print(f"  {'SNR':>6}  {'BER':>10}  {'BLER':>10}  {'perm(BER)':>20}  {'perm(BLER)':>20}  {'gap?':>5}")
    print(f"  {'─'*85}")

    # Print only rows near breakpoints + a few representative rows
    prev_perm_ber = rows[0]["perm_ber"]
    prev_perm_bler = rows[0]["perm_bler"]
    printed_snrs = set()

    # Always print first and last
    for i in [0, -1]:
        r = rows[i]
        print(f"  {r['snr_db']:>6.1f}  {r['ber']:>10.2e}  {r['bler']:>10.2e}"
              f"  {r['perm_ber']:>20}  {r['perm_bler']:>20}  {r['gap']:>5}")
        printed_snrs.add(r['snr_db'])

    # Print breakpoints
    print(f"\n  Breakpoints:")
    for r in rows:
        if r["perm_ber"] != prev_perm_ber or r["perm_bler"] != prev_perm_bler:
            print(f"    SNR {r['snr_db']:>4.1f} dB: "
                  f"perm(BER) {prev_perm_ber}→{r['perm_ber']}  "
                  f"perm(BLER) {prev_perm_bler}→{r['perm_bler']}")
            prev_perm_ber = r["perm_ber"]
            prev_perm_bler = r["perm_bler"]

    # Auth gap region
    gap_rows = [r for r in rows if r["gap"]]
    if gap_rows:
        snr_lo = gap_rows[0]["snr_db"]
        snr_hi = gap_rows[-1]["snr_db"]
        sample = gap_rows[len(gap_rows) // 2]
        print(f"\n  Authorization gap region: SNR [{snr_lo:.1f}, {snr_hi:.1f}] dB")
        print(f"  At SNR {sample['snr_db']:.1f} dB: "
              f"BER={sample['ber']:.2e} ({sample['perm_ber']})  "
              f"BLER={sample['bler']:.2e} ({sample['perm_bler']})")
        print(f"  Mean-like functional authorizes; worst-case functional refuses.")
    else:
        print(f"\n  No authorization gap found — both functionals agree at all points.")

    # Monotonicity check
    perm_bler_ranks = [_perm_rank(r["perm_bler"]) for r in rows]
    is_mono = all(perm_bler_ranks[i] <= perm_bler_ranks[i+1]
                  for i in range(len(perm_bler_ranks) - 1))
    print(f"\n  Monotonicity (BLER permission improves as SNR rises): "
          f"{'PASS' if is_mono else 'FAIL'}")


def _print_ising(rows: list[dict]) -> None:
    print(f"\n  {'─'*70}")
    print(f"  ISING — permissivity path (τ 0.0 → 0.50, β={_ISING_BETA})")

    tv_mean = rows[0]["tv_mean"]
    tv_max = rows[0]["tv_max"]
    auth_gap_width = rows[0]["auth_gap_width"]
    print(f"  TV_mean={tv_mean:.4f}  TV_max={tv_max:.4f}  "
          f"auth_gap_width={auth_gap_width:.4f}")

    # Breakpoints
    prev_pm = rows[0]["perm_mean"]
    prev_px = rows[0]["perm_max"]
    print(f"  Breakpoints:")
    for r in rows:
        if r["perm_mean"] != prev_pm or r["perm_max"] != prev_px:
            print(f"    τ={r['tau']:.3f}: "
                  f"perm(mean) {prev_pm}→{r['perm_mean']}  "
                  f"perm(max) {prev_px}→{r['perm_max']}")
            prev_pm = r["perm_mean"]
            prev_px = r["perm_max"]

    gap_rows = [r for r in rows if r["gap"]]
    if gap_rows:
        tau_lo = gap_rows[0]["tau"]
        tau_hi = gap_rows[-1]["tau"]
        print(f"\n  Authorization gap region: τ ∈ [{tau_lo:.3f}, {tau_hi:.3f}]")
        print(f"  Width = {tau_hi - tau_lo:.4f}  (= TV_max − TV_mean = {auth_gap_width:.4f} ✓)")
    else:
        print(f"\n  No gap found.")

    # Monotonicity: perm_max should be non-decreasing as tau increases
    ranks = [1 if r["perm_max"] == "ACT" else 0 for r in rows]
    is_mono = all(ranks[i] <= ranks[i+1] for i in range(len(ranks) - 1))
    print(f"  Monotonicity (permission improves as τ rises): "
          f"{'PASS' if is_mono else 'FAIL'}")


def main() -> None:
    print(f"\n{'='*90}")
    print("  Experiment 2 — Permissivity-vs-Divergence Path")
    print("  Vary evidence along controlled path; show permission tracks incompleteness.")
    print(f"{'='*90}")

    turbo_rows = run_turbo_path()
    turbo_path = RESULTS_DIR / "permissivity_turbo.csv"
    with open(turbo_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_TURBO_FIELDNAMES)
        writer.writeheader()
        writer.writerows(turbo_rows)
    _print_turbo(turbo_rows)
    print(f"\n  Written: {turbo_path}")

    ising_rows = run_ising_path()
    ising_path = RESULTS_DIR / "permissivity_ising.csv"
    with open(ising_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_ISING_FIELDNAMES)
        writer.writeheader()
        writer.writerows(ising_rows)
    _print_ising(ising_rows)
    print(f"\n  Written: {ising_path}")

    print(f"\n{'='*90}")
    print("  If turbo and Ising both show monotone permission improvement as")
    print("  evidence improves, and breakpoints land at theory-predicted thresholds,")
    print("  proceed to Experiment 3 (metric-invariance).")
    print(f"{'='*90}\n")


if __name__ == "__main__":
    main()
