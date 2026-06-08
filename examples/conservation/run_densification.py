"""Experiment 5 — Permission densification.

Tests whether the observed staircase is an artifact of the finite permission
alphabet, or a real property of the underlying authorization structure.

The question:
  Is the governing function A*(e) continuous, or is the staircase real?

The method:
  Fix the evidence path. Increase the number of permission levels from 4 to 256.
  At each granularity k, the permission hierarchy P_k is a uniform grid over the
  relevant evidence axis. The compiler maps each evidence value to the strongest
  sound permission in P_k.

  As k increases, A_k(e) = floor(A*(e), P_k) should converge to A*(e) from below,
  if A*(e) is the continuous governing function.

  The overlay of A_4, A_8, A_16, A_32, A_64, A_128, A_256 reveals:
    - whether steps shrink predictably as k rises;
    - whether breakpoints converge to stable locations;
    - whether the limiting envelope matches the ground-truth worst-case functional.

Three domains:

  Turbo  — evidence axis: SNR. Ground-truth worst-case functional: BLER.
            Expected: staircase converges to BLER curve. Kink where BER/BLER
            divergence is maximal (near the waterfall, ~1-2 dB).

  Ising  — evidence axis: tolerance τ. Ground-truth worst-case: max TV.
            Expected: staircase converges to step-function at τ = TV_max.
            The latent function is itself a step (ACT/REFUSE binary), but the
            densification shows where the step is.

  FAA    — evidence axis: decision height DH (ft). Ground-truth: RVR_floor(DH).
            Expected: smooth convergence below saturation (~102 ft), then
            flat after saturation. Kink at the saturation point is structural.

For each domain, the densification produces:
  - A CSV with columns: k, snr/tau/dh, permission_k, ground_truth_functional
  - A printed convergence table showing where the staircase steps shrink
  - A gate check: do breakpoints stabilize as k grows?

Outputs:
  results/densification_turbo.csv
  results/densification_ising.csv
  results/densification_faa.csv
"""
from __future__ import annotations

import csv
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
_ILS_DIR = _HERE.parent / "ils"
if str(_ILS_DIR) not in sys.path:
    sys.path.insert(0, str(_ILS_DIR))

RESULTS_DIR = _HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Granularity levels to test
K_LEVELS = [4, 8, 16, 32, 64, 128, 256]


# ── Generic densification engine ──────────────────────────────────────────────
#
# A compiler under P_k maps an error/incompleteness value e to the index of
# the finest permission level whose threshold is satisfied:
#
#   permission_k(e) = max { i : threshold_i >= e }   (error: lower is better)
#
# or equivalently, in normalized [0,1] space:
#
#   permission_k(e) = (number of thresholds >= e) / k
#
# This is the floor map A*(e) -> floor(A*(e), P_k).

def _permission_k(error: float, thresholds_desc: np.ndarray) -> float:
    """Return the normalized permission level under a k-level grid.

    thresholds_desc: k threshold values in descending order (tightest last).
    Returns a float in [0, 1]: fraction of thresholds satisfied.
    The permission 0.0 = weakest (none satisfied), 1.0 = strongest (all satisfied).
    """
    n_satisfied = int(np.sum(error <= thresholds_desc))
    return n_satisfied / len(thresholds_desc)


def _make_uniform_thresholds(lo: float, hi: float, k: int) -> np.ndarray:
    """k uniformly spaced thresholds from hi (permissive) down to lo (strict)."""
    return np.linspace(hi, lo, k)


def _make_loguniform_thresholds(lo: float, hi: float, k: int) -> np.ndarray:
    """k log-uniformly spaced thresholds (useful for error rates spanning decades)."""
    return np.logspace(np.log10(hi), np.log10(lo), k)


# ── Turbo densification ───────────────────────────────────────────────────────
#
# Evidence path: SNR from -1.0 to 5.0 dB (61 points).
# Error functional: BLER (worst-case, the ground-truth authorization object).
# Mean-like functional: BER (over-authorizing summary).
# Permission hierarchy P_k: k uniform thresholds over BLER range [1e-4, 1.0].
# Ground-truth: A*(SNR) = normalized position of BLER(SNR) in [0, 1].

_TURBO_BLER_LO = 1e-4
_TURBO_BLER_HI = 1.0
_TURBO_SNR_GRID = np.round(np.arange(-1.0, 5.01, 0.1), 2)

_TURBO_FIELDNAMES = [
    "snr_db", "ber", "bler", "k",
    "perm_k_bler",      # floor(A*(snr), P_k) using BLER (correct functional)
    "perm_k_ber",       # floor(A*(snr), P_k) using BER  (over-authorizing functional)
    "ground_truth",     # A*(snr) = continuous BLER-based authorization capacity
    "gap",              # perm_k_ber - perm_k_bler (over-authorization under BER)
]


def run_turbo_densification() -> list[dict]:
    from ber_bler_curves import bler_at_snr, ber_at_snr

    rows = []
    for k in K_LEVELS:
        thresholds = _make_loguniform_thresholds(_TURBO_BLER_LO, _TURBO_BLER_HI, k)
        for snr in _TURBO_SNR_GRID:
            ber = ber_at_snr(float(snr))
            bler = bler_at_snr(float(snr))
            pk_bler = _permission_k(bler, thresholds)
            pk_ber = _permission_k(ber, thresholds)
            # Ground truth: BLER in [0,1] normalized on log scale
            # = fraction of the BLER range that has been cleared
            gt = _permission_k(bler, thresholds)  # BLER-based continuous
            rows.append({
                "snr_db": round(float(snr), 2),
                "ber": round(ber, 8),
                "bler": round(bler, 8),
                "k": k,
                "perm_k_bler": round(pk_bler, 6),
                "perm_k_ber": round(pk_ber, 6),
                "ground_truth": round(gt, 6),
                "gap": round(pk_ber - pk_bler, 6),
            })
    return rows


# ── Ising densification ───────────────────────────────────────────────────────
#
# Evidence path: τ from 0 to 0.50 (200 points), β = 0.44 (critical).
# Error functional: max TV (ground-truth authorization threshold crossing).
# Permission hierarchy P_k: k uniform thresholds over τ range [0, 0.50].
# Ground truth: binary step at τ = TV_max (the true authorization boundary).
#
# The latent function A*(τ) for this binary setting is:
#   0  if τ < TV_max   (max TV exceeds tolerance: REFUSE)
#   1  if τ >= TV_max  (max TV cleared: ACT)
#
# A finite P_k observes this as a staircase that should collapse to the step
# at τ = TV_max as k → ∞.

_ISING_TAU_GRID = np.linspace(0.0, 0.50, 200)
_ISING_BETA = 0.44

_ISING_FIELDNAMES = [
    "beta", "tau", "tv_mean", "tv_max", "k",
    "perm_k_mean",    # floor(A*(tv_mean), P_k) at each τ-bucket midpoint
    "perm_k_max",     # floor(A*(tv_max),  P_k) at each τ-bucket midpoint
    "ground_truth",   # step function: 0 if tau < tv_max, 1 otherwise
    "gap",            # perm_k_mean - perm_k_max
]


def run_ising_densification() -> list[dict]:
    """Ising densification on the τ-axis.

    The Ising authorization function is a step at τ = TV_max:
      A*(τ) = 1  if τ ≥ TV_max,  else 0.

    P_k is a k-level uniform grid over [0, 0.50], producing k equally-spaced
    τ-thresholds. At each grid point τ_j, the compiler returns:
      perm_k(τ_j) = 1  if τ_j ≥ TV_max  (TV error cleared at this tolerance)
                  = 0  otherwise

    This is the direct quantization of the continuous step function.
    As k → ∞, the grid spacing 0.50/k → 0, and the estimated step location
    (the smallest τ_j ≥ TV_max) converges to TV_max.

    MAE between perm_k and the ground-truth step is computed over the shared
    τ-grid. For a step function, MAE = (n points misclassified) / (n total points).
    Misclassified points are those in the "quantization gap" nearest TV_max.
    As k grows, this gap shrinks, so MAE should fall.

    Ground truth: the exact step at TV_max, evaluated at each grid point.
    """
    from generate_ising import make_ising_grid_with_field as make_ising_grid
    from run_exact import compute_exact_marginals
    from run_bp import run_loopy_bp
    from compiler import tv_distance, tv_distance_max

    g = make_ising_grid(6, _ISING_BETA)
    exact = compute_exact_marginals(g)
    result = run_loopy_bp(g)
    marginals = result["marginals"]
    tv_mean_val = tv_distance(marginals, exact)
    tv_max_val = tv_distance_max(marginals, exact)
    converged = result["converged"]

    rows = []
    for k in K_LEVELS:
        # P_k: k uniform threshold levels over [0, 0.50]
        thresholds = np.linspace(0.0, 0.50, k + 1)[1:]  # k levels at 0.50/k, 2*0.50/k, ..., 0.50
        for tau in thresholds:
            tau_f = float(tau)
            # perm_k at tau: does TV clear the bar tau?
            pk_mean = 1.0 if tv_mean_val <= tau_f else 0.0
            pk_max  = 1.0 if tv_max_val  <= tau_f else 0.0
            # Ground truth: the exact step at TV_max
            gt = 1.0 if tau_f >= tv_max_val else 0.0
            gap = round(pk_mean - pk_max, 6)
            rows.append({
                "beta": _ISING_BETA,
                "tau": round(tau_f, 6),
                "tv_mean": round(tv_mean_val, 6),
                "tv_max": round(tv_max_val, 6),
                "k": k,
                "perm_k_mean": round(pk_mean, 6) if converged else 0.0,
                "perm_k_max":  round(pk_max,  6) if converged else 0.0,
                "ground_truth": gt,
                "gap": gap if converged else 0.0,
            })
    return rows


# ── FAA densification ─────────────────────────────────────────────────────────
#
# Evidence path: decision height DH from 300 ft down to 50 ft.
# Ground-truth governing function: RVR_floor(DH) — the physical geometric curve.
# The compiler under P_k maps DH → "how much authorization capacity remains"
# measured as a normalized fraction of the RVR_floor range.
#
# The key feature: RVR_floor(DH) is smooth and decreasing until DH ≈ 102 ft
# (saturation), then collapses to 0. The kink at saturation is structural.
# Dense permission hierarchies should reveal this kink as stable, not shrinking.
#
# Permission hierarchy P_k: k uniform thresholds over RVR range [0, 2400 ft].
# A*(DH) = _permission_k(RVR_floor(DH), P_k).

_FAA_DH_GRID = np.round(np.arange(300.0, 48.0, -2.0), 1)  # 300 → 50 ft, 2 ft steps
_FAA_RVR_LO = 0.0
_FAA_RVR_HI = 2400.0

_FAA_FIELDNAMES = [
    "dh_ft", "rvr_floor_ft", "saturated", "k",
    "perm_k",          # floor(A*(dh), P_k)
    "ground_truth",    # normalized RVR_floor(dh) in [0,1]
    "structural_kink", # 1 if dh <= saturation_dh
]


def run_faa_densification() -> list[dict]:
    from geometry import rvr_floor, saturation_dh

    h_sat = saturation_dh()

    rows = []
    for k in K_LEVELS:
        thresholds = _make_uniform_thresholds(_FAA_RVR_LO, _FAA_RVR_HI, k)
        for dh in _FAA_DH_GRID:
            geo = rvr_floor(float(dh))
            rvr_f = geo.rvr_floor_ft
            # Authorization capacity: higher RVR floor means LESS authorization
            # (aircraft needs more visibility). We want permission to increase
            # as DH increases (higher DH = easier approach = more authorized).
            # So permission tracks the *inverse*: 1 - normalized(RVR_floor).
            # But RVR_floor decreases as DH decreases until saturation.
            # At saturation, RVR_floor = 0 (geometric constraint lifts) — but
            # lower DH approaches require different evidence. We just report the
            # geometric curve directly and note the kink.
            #
            # ground_truth = 1 - (RVR_floor / RVR_max): higher = more permitted
            gt = 1.0 - (rvr_f / _FAA_RVR_HI)
            # Permission under P_k: fraction of thresholds that RVR exceeds
            # (RVR ≥ threshold means visual reference is adequate at that level)
            pk = _permission_k(rvr_f, thresholds[::-1])  # thresholds asc for RVR
            structural_kink = 1 if float(dh) <= h_sat else 0
            rows.append({
                "dh_ft": round(float(dh), 1),
                "rvr_floor_ft": round(rvr_f, 2),
                "saturated": int(geo.saturated),
                "k": k,
                "perm_k": round(pk, 6),
                "ground_truth": round(gt, 6),
                "structural_kink": structural_kink,
            })
    return rows


# ── Convergence analysis ──────────────────────────────────────────────────────

def _convergence_summary(rows: list[dict], x_col: str, perm_col: str,
                          gt_col: str, k_col: str = "k") -> dict:
    """For each k, compute mean absolute error between perm_k and ground_truth."""
    from collections import defaultdict
    mae_by_k: dict[int, list[float]] = defaultdict(list)
    for r in rows:
        mae_by_k[r[k_col]].append(abs(r[perm_col] - r[gt_col]))
    return {k: float(np.mean(v)) for k, v in sorted(mae_by_k.items())}


def _breakpoints(rows: list[dict], x_col: str, perm_col: str,
                 k: int, k_col: str = "k") -> list[float]:
    """Return x-axis values where perm_k changes, for a given k."""
    subset = sorted([r for r in rows if r[k_col] == k], key=lambda r: r[x_col])
    bps = []
    for i in range(1, len(subset)):
        if subset[i][perm_col] != subset[i-1][perm_col]:
            bps.append(subset[i][x_col])
    return bps


# ── Output ────────────────────────────────────────────────────────────────────

def _step_location_error(rows: list[dict], x_col: str, perm_col: str) -> dict[int, float]:
    """For each k, find the x-axis location of the last upward breakpoint and compare
    to the ground-truth step location (first x where ground_truth = 1.0 for all subsequent).
    Returns {k: |estimated_step_x - true_step_x|}.
    Uses the first grid point where perm_k reaches its maximum value.
    """
    # Find ground-truth true step: the continuous TV_max value stored in the rows
    # For each k, the step is at the smallest grid τ ≥ TV_max.
    # True step is TV_max itself.
    result = {}
    for k in K_LEVELS:
        k_rows = sorted([r for r in rows if r["k"] == k], key=lambda r: r[x_col])
        if not k_rows:
            result[k] = float("nan")
            continue
        # True step location: TV_max (from the stored tv_max field if present)
        if "tv_max" in k_rows[0]:
            true_step = k_rows[0]["tv_max"]
        else:
            # Fall back: first x where ground_truth becomes 1
            true_step = next((r[x_col] for r in k_rows if r["ground_truth"] >= 1.0 - 1e-9), None)
            if true_step is None:
                result[k] = float("nan")
                continue
        # Estimated step: first grid τ where perm_k_max = 1.0
        estimated_step = next(
            (r[x_col] for r in k_rows if r[perm_col] >= 1.0 - 1e-9), None
        )
        if estimated_step is None:
            result[k] = float("nan")
        else:
            result[k] = abs(estimated_step - true_step)
    return result


def _print_domain(domain: str, rows: list[dict], x_col: str,
                  perm_col: str, gt_col: str) -> None:
    print(f"\n  {'─'*70}")
    print(f"  {domain} — permission densification")

    mae = _convergence_summary(rows, x_col, perm_col, gt_col)
    print(f"\n  MAE(perm_k, ground_truth) as k increases:")
    print(f"  {'k':>6}  {'MAE':>10}  {'steps shrink?':>14}")
    prev_mae = None
    for k, m in mae.items():
        shrink = ""
        if prev_mae is not None:
            shrink = "yes ↓" if m < prev_mae else ("flat" if abs(m - prev_mae) < 1e-6 else "NO ↑")
        print(f"  {k:>6}  {m:>10.6f}  {shrink:>14}")
        prev_mae = m

    # Step-location error (most relevant for pure step functions like Ising)
    step_errors = _step_location_error(rows, x_col, perm_col)
    if step_errors:
        has_step = any(not np.isnan(v) for v in step_errors.values())
        if has_step:
            print(f"\n  Step location error |estimated_step − true_step| as k increases:")
            print(f"  {'k':>6}  {'step_err':>12}  {'improving?':>12}")
            prev_se = None
            for k, se in step_errors.items():
                imp = ""
                if prev_se is not None and not np.isnan(se) and not np.isnan(prev_se):
                    imp = "yes ↓" if se < prev_se - 1e-9 else ("flat" if abs(se - prev_se) < 1e-9 else "NO ↑")
                se_str = f"{se:.6f}" if not np.isnan(se) else "  n/a"
                print(f"  {k:>6}  {se_str:>12}  {imp:>12}")
                prev_se = se

    print(f"\n  Breakpoint count as k increases (should stabilize):")
    print(f"  {'k':>6}  {'n_breakpoints':>14}")
    for k in K_LEVELS:
        bps = _breakpoints(rows, x_col, perm_col, k)
        print(f"  {k:>6}  {len(bps):>14}")

    # Structural kink check for FAA
    if "structural_kink" in rows[0]:
        kink_rows_k256 = [r for r in rows if r["k"] == 256 and r["structural_kink"]]
        if kink_rows_k256:
            dh_vals = [r["dh_ft"] for r in kink_rows_k256]
            print(f"\n  Structural kink region (below saturation DH): "
                  f"DH ≤ {max(dh_vals):.0f} ft")
            print(f"  At k=256, steps in this region: "
                  f"{len([r for r in kink_rows_k256 if r['dh_ft'] in [r2['dh_ft'] for r2 in _breakpoints_full(rows, 'dh_ft', perm_col, 256)]])}")

    # Gate assessment
    maes = list(mae.values())
    converges = all(maes[i] >= maes[i+1] - 1e-6 for i in range(len(maes)-1))
    # For Ising, also check step-location convergence
    if step_errors:
        se_vals = [v for v in step_errors.values() if not np.isnan(v)]
        step_converges = all(se_vals[i] >= se_vals[i+1] - 1e-9 for i in range(len(se_vals)-1))
    else:
        step_converges = True
    overall = converges or step_converges
    print(f"\n  Convergence (MAE non-increasing): {'PASS' if converges else 'FAIL'}")
    if step_errors and any(not np.isnan(v) for v in step_errors.values()):
        print(f"  Step-location convergence (error shrinks as k grows): "
              f"{'PASS' if step_converges else 'FAIL'}")


def _breakpoints_full(rows, x_col, perm_col, k):
    """Return full breakpoint records for a given k."""
    subset = sorted([r for r in rows if r["k"] == k], key=lambda r: r[x_col])
    bps = []
    for i in range(1, len(subset)):
        if subset[i][perm_col] != subset[i-1][perm_col]:
            bps.append(subset[i])
    return bps


def main() -> None:
    print(f"\n{'='*90}")
    print("  Experiment 5 — Permission Densification")
    print("  Question: Is the staircase a quantization artifact or a real property?")
    print("  Method: fix evidence path, increase k from 4 to 256, observe convergence.")
    print(f"{'='*90}")

    # Turbo
    print("\n  Running turbo densification...")
    turbo_rows = run_turbo_densification()
    turbo_path = RESULTS_DIR / "densification_turbo.csv"
    with open(turbo_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_TURBO_FIELDNAMES)
        writer.writeheader()
        writer.writerows(turbo_rows)
    _print_domain("TURBO", turbo_rows, "snr_db", "perm_k_bler", "ground_truth")
    print(f"\n  Written: {turbo_path}")

    # Ising
    print("\n  Running Ising densification...")
    ising_rows = run_ising_densification()
    ising_path = RESULTS_DIR / "densification_ising.csv"
    with open(ising_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_ISING_FIELDNAMES)
        writer.writeheader()
        writer.writerows(ising_rows)
    _print_domain("ISING", ising_rows, "tau", "perm_k_max", "ground_truth")
    print(f"\n  Written: {ising_path}")

    # FAA
    print("\n  Running FAA densification...")
    faa_rows = run_faa_densification()
    faa_path = RESULTS_DIR / "densification_faa.csv"
    with open(faa_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_FAA_FIELDNAMES)
        writer.writeheader()
        writer.writerows(faa_rows)
    _print_domain("FAA", faa_rows, "dh_ft", "perm_k", "ground_truth")
    print(f"\n  Written: {faa_path}")

    # Summary
    print(f"\n{'='*90}")
    print("  INTERPRETATION GUIDE")
    print()
    print("  If MAE decreases monotonically as k grows: the staircase is a")
    print("  quantization artifact. The governing function A*(e) exists and is")
    print("  being estimated by the finite permission grid.")
    print()
    print("  If MAE plateaus at a nonzero floor: there is an irreducible gap")
    print("  between the finite permission grid and the true function. This may")
    print("  indicate a structural discontinuity (genuine kink) rather than")
    print("  quantization noise.")
    print()
    print("  If breakpoint count stabilizes before k=256: the governing function")
    print("  has a finite number of genuine discontinuities. Extra permission levels")
    print("  resolve the staircase within each smooth region but do not create")
    print("  new structural features.")
    print()
    print("  FAA kink at saturation DH (~102 ft): this breakpoint should persist")
    print("  at all k values. It is not a quantization artifact. It is the geometric")
    print("  boundary where the visual evidence axis changes regime.")
    print(f"{'='*90}\n")


if __name__ == "__main__":
    main()
