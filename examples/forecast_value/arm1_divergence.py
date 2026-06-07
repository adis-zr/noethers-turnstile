"""§5 Arm 1 — Expectation divergence.

Sweep (C/L_bar, fiber heterogeneity) at L0 evidence. For each cell, record
cost-loss decision, A(e), DRO, and the world that pins the meet. Identify
the divergence region (cost-loss says act, A(e) says don't) and test the
preregistered prediction: the divergence boundary tracks heterogeneity, not
forecast probability.

Heterogeneity operationalization:
  The L0 fibers are indexed by (t_min_bin, regime, phenology_band). Holding
  t_min_bin fixed and varying the (regime, phenology_band) gives 4 fibers
  per t_min band, with naturally varying heterogeneity:
    advective-hardy:    most homogeneous (low loss, short dwell)
    advective-vulnerable: heterogeneous (vulnerable stage, short dwell mix)
    radiative-hardy:    heterogeneous (long dwell can occur)
    radiative-vulnerable: most damaging (long dwell + vulnerable)
  We quantify heterogeneity per fiber as the spread of L_real:
    heterogeneity = std(L_real) over the fiber.

  Holding t_min_bin fixed and ranging across the 4 fibers, p_hat is
  approximately constant (within the bin), so cost-loss output is fixed.
  Any variation in A(e) across the 4 fibers is heterogeneity-driven, not
  p_hat-driven.

Cost-loss sweep parameter: C/L_bar in the test domain. We hold C fixed and
vary L_bar to span thresholds 0.05, 0.10, 0.20, 0.50 — this changes which
fibers cost-loss authorizes without changing the world set.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

import sys
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from worldgen import sample_worlds, forecast_probability, COST_C
from domain import (
    perm_rank, latent_authorization, world_authorization,
    assemble_fibers, evidence_L0,
)
from baselines import cost_loss_decision, dro_over_fiber

RESULTS_DIR = _HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def fiber_heterogeneity(fiber: list) -> float:
    """std of L_real across the fiber."""
    if not fiber:
        return 0.0
    losses = [w.l_real for w in fiber]
    return float(np.std(losses))


def fiber_mean_p_hat(fiber: list) -> float:
    return float(np.mean([forecast_probability(w.forecast_t_min) for w in fiber]))


def run_arm1(
    n_worlds: int = 50000,
    seed: int = 12345,
    c_over_l_bars: tuple[float, ...] = (0.05, 0.10, 0.20, 0.50),
    min_fiber_size: int = 50,
) -> dict:
    """Run the Arm 1 sweep. Returns aggregate stats and writes CSV."""
    ws = sample_worlds(n=n_worlds, seed=seed)
    fibers = assemble_fibers(ws, evidence_L0)
    rows = []
    for fiber_key, fiber in fibers.items():
        if len(fiber) < min_fiber_size:
            continue
        p_hat = fiber_mean_p_hat(fiber)
        het = fiber_heterogeneity(fiber)
        Ae, pin = latent_authorization(fiber)
        # The L_bar in the spec controls the cost-loss threshold; vary it
        # across the sweep.
        for c_over_l_bar in c_over_l_bars:
            l_bar = COST_C / c_over_l_bar
            cl = cost_loss_decision(p_hat, c=COST_C, l_bar=l_bar)
            dro = dro_over_fiber(fiber, c=COST_C, l_bar=l_bar)
            divergence_cl = (perm_rank(cl) > perm_rank(Ae))  # cl acts, A(e) does not
            rows.append({
                "fiber": str(fiber_key),
                "t_min_bin": fiber_key[0],
                "regime": fiber_key[1],
                "pheno_band": fiber_key[2],
                "n_worlds": len(fiber),
                "p_hat": round(p_hat, 4),
                "heterogeneity_std_L": round(het, 4),
                "c_over_l_bar": c_over_l_bar,
                "L_bar": round(l_bar, 4),
                "A_e": Ae,
                "cost_loss": cl,
                "DRO": dro,
                "pin_t_min": round(pin.t_min, 2) if pin else None,
                "pin_L_real": round(pin.l_real, 4) if pin else None,
                "pin_phenology": pin.phenology if pin else None,
                "pin_regime": pin.regime if pin else None,
                "divergence_cl_acts_Ae_doesnt": int(divergence_cl),
            })

    csv_path = RESULTS_DIR / "arm1_divergence.csv"
    fields = list(rows[0].keys())
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # Aggregate
    n_div = sum(r["divergence_cl_acts_Ae_doesnt"] for r in rows)
    n_total = len(rows)

    # Test: at fixed t_min_bin (≈ fixed p_hat) and fixed c_over_l_bar, does
    # A(e) vary across the 4 fibers? If yes, the variation is heterogeneity-
    # driven (not p_hat-driven). This is the preregistered claim.
    from collections import defaultdict
    by_bin_clbar: dict[tuple, list] = defaultdict(list)
    for r in rows:
        by_bin_clbar[(r["t_min_bin"], r["c_over_l_bar"])].append(r)
    n_bins_with_Ae_variation = 0
    n_bins_with_cl_variation = 0
    total_bins = 0
    for k, group in by_bin_clbar.items():
        if len(group) < 2:
            continue
        total_bins += 1
        Ae_set = {r["A_e"] for r in group}
        cl_set = {r["cost_loss"] for r in group}
        if len(Ae_set) > 1:
            n_bins_with_Ae_variation += 1
        if len(cl_set) > 1:
            n_bins_with_cl_variation += 1

    summary = {
        "n_rows": n_total,
        "n_divergences": n_div,
        "divergence_rate": n_div / max(1, n_total),
        "n_bins_with_Ae_variation_at_fixed_p_hat": n_bins_with_Ae_variation,
        "n_bins_with_cl_variation_at_fixed_p_hat": n_bins_with_cl_variation,
        "n_bins_total": total_bins,
        "preregistered_check_arm1_div_exists": n_div > 0,
        "preregistered_check_boundary_tracks_heterogeneity": (
            n_bins_with_Ae_variation > 0 and n_bins_with_cl_variation == 0
        ),
        "csv_path": str(csv_path),
    }
    return summary


def main():
    print("="*90)
    print("ARM 1 — Expectation divergence sweep")
    print("="*90)
    summary = run_arm1()
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()
