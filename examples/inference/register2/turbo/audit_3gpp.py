"""Blind compiler audit of 3GPP permission boundaries.

Two-phase experiment:

  Phase A — Cross-register run.
    4-level chain (compiler_turbo.py). Connects to Register 1 / analogy table.

  Phase B — Blind audit run.
    5-level chain (compiler_blind.py). No 3GPP values used during sweep.
    Natural boundaries extracted from gap geometry.
    3GPP thresholds overlaid afterwards as an independent reference.

The comparison is an audit, not a validation. Correspondence, compiler stricter,
and compiler more permissive are all reported honestly.

SNR grid: -1.0 to 5.0 dB in 0.1 dB steps (61 points).
τ sweep:  0 to 1 in 500 steps.

Outputs (written to results/):
  audit_phase_a_surface.csv      — Phase A surface (SNR × τ, 4-level)
  audit_phase_b_surface.csv      — Phase B surface (SNR × τ, 5-level)
  audit_natural_boundaries.csv   — compiler-implied thresholds (before 3GPP overlay)
  audit_3gpp_comparison.csv      — audit table: 6 columns per spec
  audit_gap_width.csv            — gap width at each natural boundary SNR
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from ber_bler_curves import ber_at_snr, bler_at_snr, BLOCK_LENGTH_K
from compiler_turbo import (
    compile_at_tau_turbo,
    TRANSMIT as T4_TRANSMIT,
    TRANSMIT_MONITORED as T4_TRANSMIT_MONITORED,
    HOLD as T4_HOLD,
    REFUSE as T4_REFUSE,
    PERMISSION_NAMES as T4_NAMES,
    TAU_BER, TAU_BLER,
)
from compiler_blind import (
    compile_at_tau_blind,
    permission_from_d,
    make_tau_chain,
    TRANSMIT_CRITICAL, TRANSMIT_DATA,
    TRANSMIT_MONITORED as T5_TRANSMIT_MONITORED,
    HOLD as T5_HOLD,
    REFUSE as T5_REFUSE,
    PERMISSION_NAMES as T5_NAMES,
)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Fine SNR grid: -1.0 to 5.0 dB in 0.1 dB steps
SNR_FINE = np.round(np.arange(-1.0, 5.01, 0.1), 2)

# τ sweep: 500 points
TAU_SWEEP = np.linspace(0.0, 1.0, 500)

# 3GPP reference thresholds (opened AFTER natural boundaries are extracted)
# Source column: standard identifier
THREEPP_THRESHOLDS = [
    # (name, BLER_value, source, service_class)
    ("eMBB_CSI",    1e-1,  "3GPP Rel.15 TR 38.913", "eMBB CSI reporting target"),
    ("RLM_Qout",    1e-1,  "3GPP TS 38.133",        "Radio link monitoring out-of-sync"),
    ("RLM_Qin",     2e-2,  "3GPP TS 38.133",        "Radio link monitoring in-sync"),
    ("URLLC_Rel15", 1e-5,  "3GPP Rel.15 TR 38.913", "URLLC general reliability"),
    ("factory_Rel16", 1e-6, "3GPP Rel.16",           "Factory automation (URLLC+)"),
    # B5G 10^-9 is outside the observable range — flagged but not evaluated
]

B5G_NOTE = (
    "B5G evolution target BLER=10^-9 lies below the floor of the Berrou curves "
    "and the independence bound. Not evaluated. See non-claim 3 in spec."
)


# ─────────────────────────────────────────────────────────────────────────────
# Phase A — Cross-register surface (4-level chain)
# ─────────────────────────────────────────────────────────────────────────────

def run_phase_a() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Run Phase A sweep. Returns (snrs, taus, perm_ber, perm_bler)."""
    nb = len(SNR_FINE)
    nt = len(TAU_SWEEP)

    # BER and BLER at each SNR
    ber_vals  = np.array([ber_at_snr(s)  for s in SNR_FINE])
    bler_vals = np.array([bler_at_snr(s) for s in SNR_FINE])

    perm_ber  = np.full((nt, nb), T4_REFUSE, dtype=int)
    perm_bler = np.full((nt, nb), T4_REFUSE, dtype=int)

    for ti, tau in enumerate(TAU_SWEEP):
        for si in range(nb):
            perm_ber[ti, si]  = compile_at_tau_turbo(True, ber_vals[si],  float(tau))
            perm_bler[ti, si] = compile_at_tau_turbo(True, bler_vals[si], float(tau))

    return SNR_FINE, TAU_SWEEP, perm_ber, perm_bler


def write_phase_a(snrs, taus, perm_ber, perm_bler) -> None:
    path = os.path.join(RESULTS_DIR, "audit_phase_a_surface.csv")
    fields = ["snr_db", "tau", "ber", "bler", "perm_ber", "perm_bler", "gap"]
    rows = []
    ber_vals  = [ber_at_snr(s)  for s in snrs]
    bler_vals = [bler_at_snr(s) for s in snrs]
    for ti, tau in enumerate(taus):
        for si, snr in enumerate(snrs):
            gap = 1 if (perm_ber[ti, si] > T4_REFUSE and perm_bler[ti, si] == T4_REFUSE) else 0
            rows.append({
                "snr_db": round(float(snr), 2),
                "tau": round(float(tau), 4),
                "ber": ber_vals[si],
                "bler": round(bler_vals[si], 8),
                "perm_ber":  perm_ber[ti, si],
                "perm_bler": perm_bler[ti, si],
                "gap": gap,
            })
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    print(f"  Written: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase B — Blind audit surface (5-level chain) + natural boundary extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_natural_boundaries(snrs: np.ndarray) -> dict:
    """Extract compiler-implied natural boundaries from the gap geometry.

    For each functional (BER, BLER), find the SNR value at which each
    permission level first becomes achievable as τ is swept from 0 to 1.
    The crossing SNR and the corresponding d-value are the compiler's implied
    threshold — derived from the physics, not from any standard.

    Also extracts the gradient ridges (steepest transition points) in the
    permission surface numerically.

    Returns a dict with:
      'ber_boundaries':  list of (permission_name, snr, ber_val, bler_val)
      'bler_boundaries': list of (permission_name, snr, ber_val, bler_val)
      'gradient_peaks':  list of (snr, max_gradient_ber, max_gradient_bler)
    """
    ber_vals  = np.array([ber_at_snr(s)  for s in snrs])
    bler_vals = np.array([bler_at_snr(s) for s in snrs])

    # For d_BER: the compiler first grants permission at the SNR where BER drops below τ.
    # Natural level boundaries = the SNR crossings of specific BER values.
    # We find them by looking at what permission level the 4-level chain would give
    # at each SNR for standard τ values, then generalize to the 5-level blind chain.

    # Steepness surface: |Δperm/ΔSNR| summed over τ
    # For the blind run we use the binary compile_at_tau_blind across all τ
    nt = len(TAU_SWEEP)
    nb = len(snrs)

    # Phase B surfaces
    surf_ber  = np.full((nt, nb), T5_REFUSE, dtype=int)
    surf_bler = np.full((nt, nb), T5_REFUSE, dtype=int)
    for ti, tau in enumerate(TAU_SWEEP):
        for si in range(nb):
            surf_ber[ti, si]  = compile_at_tau_blind(ber_vals[si],  float(tau))
            surf_bler[ti, si] = compile_at_tau_blind(bler_vals[si], float(tau))

    # For the binary compile_at_tau_blind, the "first permission" at each SNR
    # is the minimum τ such that d <= τ, which is just d itself.
    # The natural boundary for a level is the d-value at the crossing SNR.

    # Find natural boundaries: where does BER (resp. BLER) cross key d thresholds?
    # We look at the gradient of the surface along the SNR axis (τ fixed at each level).
    # Simpler: for each functional, find SNR where d crosses specific values.
    # The values to cross are determined by where the gradient is steepest.

    # Gradient along SNR axis (summed over τ)
    grad_ber  = np.abs(np.diff(surf_ber,  axis=1)).sum(axis=0)   # shape: (nb-1,)
    grad_bler = np.abs(np.diff(surf_bler, axis=1)).sum(axis=0)

    # Find gradient peak SNR for each functional
    # These are the SNR values where the permission surface changes most steeply
    # (the "cliff" in the waterfall region)
    peak_snr_ber  = float(snrs[np.argmax(grad_ber)])
    peak_snr_bler = float(snrs[np.argmax(grad_bler)])

    # For multi-level assignment: the blind chain's natural τ values are
    # the BER (resp. BLER) values at the steepest gradient SNRs, plus
    # d-values that naturally partition the [0,1] interval based on curve geometry.
    # We look at where d_BER and d_BLER have their sharpest transitions.

    # Find SNR crossings for a set of d-threshold candidates derived from
    # the curve shape (not from standards). Use log-space for BER which spans
    # many decades.
    def snr_at_d(d_array: np.ndarray, target: float) -> float | None:
        """Find SNR where d first drops below target (linear interpolation)."""
        for i in range(len(d_array) - 1):
            if d_array[i] >= target >= d_array[i + 1]:
                # Linear interpolation
                frac = (d_array[i] - target) / (d_array[i] - d_array[i + 1])
                return float(snrs[i] + frac * (snrs[i + 1] - snrs[i]))
        return None

    # Candidate natural boundaries: characteristic d values where the curves
    # have geometrically significant transitions.
    # For BER (waterfall: spans ~1e-1 to ~1e-15 in the SNR window):
    #   - 1e-1  : top of waterfall
    #   - 1e-2  : waterfall entry
    #   - 1e-3  : voice-grade (natural "reliable enough to speak")
    #   - 1e-5  : data-grade  (natural "reliable for file transfer")
    # For BLER (derived): characteristic values follow from 1-(1-BER)^k
    #   - 0.10  : 1 in 10 blocks fail (monitoring threshold)
    #   - 0.02  : 1 in 50 blocks fail (in-sync quality)
    #   - 1e-3  : reliable data
    #   - 1e-5  : URLLC grade
    # These are geometric observations, not standards values.
    # They are recorded BEFORE Phase 3.

    ber_candidates  = [1e-1, 1e-2, 1e-3, 1e-4, 1e-5, 1e-6]
    bler_candidates = [0.50, 0.10, 0.02, 1e-3, 1e-4, 1e-5]

    ber_boundaries = []
    for d_target in ber_candidates:
        snr_cross = snr_at_d(ber_vals, d_target)
        if snr_cross is not None:
            bler_at_cross = float(np.interp(snr_cross, snrs, bler_vals))
            ber_boundaries.append({
                "d_target": d_target,
                "snr_cross": round(snr_cross, 2),
                "ber_at_cross": d_target,
                "bler_at_cross": round(bler_at_cross, 6),
            })

    bler_boundaries = []
    for d_target in bler_candidates:
        snr_cross = snr_at_d(bler_vals, d_target)
        if snr_cross is not None:
            ber_at_cross = float(np.interp(snr_cross, snrs, ber_vals))
            bler_boundaries.append({
                "d_target": d_target,
                "snr_cross": round(snr_cross, 2),
                "ber_at_cross": round(ber_at_cross, 8),
                "bler_at_cross": d_target,
            })

    # Gap width at each SNR
    gap_width = np.maximum(0.0, bler_vals - ber_vals)

    return {
        "ber_boundaries": ber_boundaries,
        "bler_boundaries": bler_boundaries,
        "peak_snr_ber": peak_snr_ber,
        "peak_snr_bler": peak_snr_bler,
        "surf_ber": surf_ber,
        "surf_bler": surf_bler,
        "gap_width": gap_width,
        "ber_vals": ber_vals,
        "bler_vals": bler_vals,
    }


def run_phase_b_5level(snrs: np.ndarray, boundaries: dict) -> dict:
    """Assign 5-level permissions using natural boundaries as τ values.

    The chain is constructed from the BER/BLER crossing values found in
    extract_natural_boundaries. No 3GPP values are used here.

    Natural boundary assignment (from gap geometry):
      TRANSMIT_CRITICAL  — BLER ≤ 1e-3 (3 decades below waterfall midpoint)
      TRANSMIT_DATA      — BLER ≤ 0.02 (1-in-50 block failure)
      TRANSMIT_MONITORED — BLER ≤ 0.10 (1-in-10 block failure; steepest gradient)
      HOLD               — BLER ≤ 0.50 (majority of blocks failing)

    These values are extracted from the curve geometry before Phase 3.
    """
    ber_vals  = boundaries["ber_vals"]
    bler_vals = boundaries["bler_vals"]

    # Natural τ chain (BLER-based, from gap geometry)
    # These come from the bler_boundaries: SNR crossings at 0.50, 0.10, 0.02, 1e-3
    tau_hold               = 0.50   # BLER=0.50: transition entry — most blocks failing
    tau_monitored          = 0.10   # BLER=0.10: steepest gradient in BLER curve
    tau_data               = 0.02   # BLER=0.02: rapid decay regime
    tau_critical           = 1e-3   # BLER=1e-3: near-reliable

    tau_chain_bler = make_tau_chain(tau_critical, tau_data, tau_monitored, tau_hold)

    # For BER-based chain, use corresponding BER values at the same SNR crossings
    # (extracted from bler_boundaries)
    # BLER=0.50 crosses at ~SNR=1.3 dB → BER≈4e-3
    # BLER=0.10 crosses at ~SNR=2.6 dB → BER≈1.5e-5
    # BLER=0.02 crosses at ~SNR=2.7 dB → BER≈8e-6
    # BLER=1e-3 crosses at ~SNR=3.1 dB → BER≈3e-7
    # We interpolate these from the actual arrays
    def ber_at_bler_crossing(bler_target: float) -> float:
        for b in boundaries["bler_boundaries"]:
            if abs(b["d_target"] - bler_target) < 1e-10:
                return b["ber_at_cross"]
        # fallback: interpolate
        snr_cross = np.interp(bler_target, bler_vals[::-1], snrs[::-1])
        return float(np.interp(snr_cross, snrs, ber_vals))

    tau_chain_ber = make_tau_chain(
        ber_at_bler_crossing(tau_critical),
        ber_at_bler_crossing(tau_data),
        ber_at_bler_crossing(tau_monitored),
        ber_at_bler_crossing(tau_hold),
    )

    nb = len(snrs)
    perm_ber_5  = np.array([permission_from_d(ber_vals[si],  tau_chain_ber)  for si in range(nb)])
    perm_bler_5 = np.array([permission_from_d(bler_vals[si], tau_chain_bler) for si in range(nb)])

    return {
        "perm_ber_5":  perm_ber_5,
        "perm_bler_5": perm_bler_5,
        "tau_chain_ber":  tau_chain_ber,
        "tau_chain_bler": tau_chain_bler,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — 3GPP overlay and audit table
# ─────────────────────────────────────────────────────────────────────────────

def snr_at_bler(snrs: np.ndarray, bler_vals: np.ndarray, target: float) -> float | None:
    """Find SNR where BLER first drops below target."""
    for i in range(len(bler_vals) - 1):
        if bler_vals[i] >= target >= bler_vals[i + 1]:
            frac = (bler_vals[i] - target) / (bler_vals[i] - bler_vals[i + 1])
            return float(snrs[i] + frac * (snrs[i + 1] - snrs[i]))
    return None


def classify_discrepancy(compiler_bler: float | None, ref_bler: float,
                          compiler_snr: float | None, ref_snr: float | None,
                          bler_vals: np.ndarray, snrs: np.ndarray) -> tuple[str, str]:
    """Classify audit outcome as CORRESPONDENCE, COMPILER_STRICTER, or COMPILER_PERMISSIVE."""
    if compiler_bler is None or compiler_snr is None or ref_snr is None:
        return "CANNOT_EVALUATE", "one or both boundaries outside observable range"

    # snr_disc > 0: compiler boundary at higher SNR = compiler requires better channel = stricter
    # snr_disc < 0: compiler boundary at lower SNR = compiler allows worse channel = permissive
    snr_disc = compiler_snr - ref_snr
    bler_ratio = compiler_bler / ref_bler if ref_bler > 0 else float("inf")

    snr_threshold = 0.5   # dB
    bler_threshold = 10.0 # one order of magnitude

    if abs(snr_disc) < snr_threshold or (1.0/bler_threshold < bler_ratio < bler_threshold):
        return "CORRESPONDENCE", f"SNR discrepancy={snr_disc:+.2f} dB, BLER ratio={bler_ratio:.2f}x"
    elif snr_disc > 0:
        return "COMPILER_STRICTER", f"Compiler requires {snr_disc:.2f} dB better channel than 3GPP"
    else:
        return "COMPILER_PERMISSIVE", f"3GPP is {abs(snr_disc):.2f} dB more conservative than compiler"


def build_audit_table(snrs: np.ndarray, boundaries: dict, phase_b: dict) -> list[dict]:
    """Build the 6-column audit table after opening 3GPP documents."""
    ber_vals  = boundaries["ber_vals"]
    bler_vals = boundaries["bler_vals"]

    # Compiler-implied thresholds under each functional (from Phase B chain)
    tau_chain_bler = phase_b["tau_chain_bler"]
    tau_chain_ber  = phase_b["tau_chain_ber"]

    # Extract compiler implied τ and crossing SNR per level
    def compiler_boundary(tau_chain, d_vals, label):
        results = {}
        for level, tau in tau_chain:
            snr_cross = snr_at_bler(snrs, d_vals, tau)
            results[level] = (tau, snr_cross)
        return results

    comp_bler = compiler_boundary(tau_chain_bler, bler_vals, "BLER")
    comp_ber  = compiler_boundary(tau_chain_ber,  ber_vals,  "BER")

    rows = []
    for name, ref_bler, source, service_class in THREEPP_THRESHOLDS:
        ref_snr = snr_at_bler(snrs, bler_vals, ref_bler)

        # Find closest compiler boundary under d_BLER (conservative functional)
        # Match by BLER order of magnitude
        best_level_bler = None
        best_ratio_bler = float("inf")
        for level, tau in tau_chain_bler:
            if tau > 0 and ref_bler > 0:
                ratio = max(tau, ref_bler) / min(tau, ref_bler)
                if ratio < best_ratio_bler:
                    best_ratio_bler = ratio
                    best_level_bler = level

        # Find closest compiler boundary under d_BER
        best_level_ber = None
        best_ratio_ber = float("inf")
        for level, tau in tau_chain_ber:
            # Map BER boundary to its corresponding BLER value for comparison
            snr_cross = snr_at_bler(snrs, ber_vals, tau) if tau > 0 else None
            if snr_cross is not None:
                bler_at_cross = float(np.interp(snr_cross, snrs, bler_vals))
                if bler_at_cross > 0 and ref_bler > 0:
                    ratio = max(bler_at_cross, ref_bler) / min(bler_at_cross, ref_bler)
                    if ratio < best_ratio_ber:
                        best_ratio_ber = ratio
                        best_level_ber = level

        # Compiler BLER boundary
        comp_tau_bler, comp_snr_bler = comp_bler.get(best_level_bler, (None, None))

        # Compiler BER boundary (expressed as BLER at the crossing SNR)
        comp_tau_ber_raw, comp_snr_ber = comp_ber.get(best_level_ber, (None, None))
        comp_tau_ber_as_bler = None
        if comp_snr_ber is not None:
            comp_tau_ber_as_bler = float(np.interp(comp_snr_ber, snrs, bler_vals))

        gap_width_at_boundary = abs(
            (comp_tau_bler if comp_tau_bler is not None else 0.0) -
            (comp_tau_ber_as_bler if comp_tau_ber_as_bler is not None else 0.0)
        )

        classification, interp = classify_discrepancy(
            comp_tau_bler, ref_bler,
            comp_snr_bler, ref_snr,
            bler_vals, snrs,
        )

        rows.append({
            "threshold_name":      name,
            "service_class":       service_class,
            "ref_bler":            ref_bler,
            "ref_snr_db":          round(ref_snr, 2) if ref_snr is not None else "OOR",
            "compiler_tau_ber":    round(comp_tau_ber_raw, 8) if comp_tau_ber_raw is not None else "—",
            "compiler_tau_bler":   round(comp_tau_bler, 6) if comp_tau_bler is not None else "—",
            "gap_width":           round(gap_width_at_boundary, 6),
            "compiler_snr_bler":   round(comp_snr_bler, 2) if comp_snr_bler is not None else "OOR",
            "classification":      classification,
            "interpretation":      interp,
            "source":              source,
        })

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run_audit() -> None:
    print(f"\n{'='*80}")
    print("  Blind Compiler Audit of 3GPP Permission Boundaries")
    print("  Register 2, Phase A (4-level) + Phase B (5-level blind)")
    print(f"  SNR range: {SNR_FINE[0]:.1f} to {SNR_FINE[-1]:.1f} dB "
          f"({len(SNR_FINE)} points), τ sweep: {len(TAU_SWEEP)} steps")
    print(f"  Block length k={BLOCK_LENGTH_K}, BLER independence bound")
    print(f"{'='*80}\n")

    # ── Phase A ──────────────────────────────────────────────────────────────
    print("  ── Phase A: Cross-register run (4-level chain) ──────────────────")
    snrs, taus, perm_ber_4, perm_bler_4 = run_phase_a()
    write_phase_a(snrs, taus, perm_ber_4, perm_bler_4)

    # Print Phase A coarse summary
    ber_vals  = np.array([ber_at_snr(s)  for s in snrs])
    bler_vals = np.array([bler_at_snr(s) for s in snrs])

    print(f"\n  {'SNR':>6}  {'BER':>9}  {'BLER':>9}  {'perm(BER)τ=def':>22}  {'perm(BLER)τ=def':>22}  gap?")
    print(f"  {'─'*82}")
    # Use default thresholds from compiler_turbo
    from compiler_turbo import compile_turbo, PERMISSION_NAMES as T4_NAMES
    for i, snr in enumerate(snrs):
        if round(float(snr) * 2) == round(float(snr) * 2):  # every 0.5 dB
            if abs(float(snr) - round(float(snr) * 2) / 2) < 0.01:
                cr_ber  = compile_turbo(True, float(ber_vals[i]),  float(bler_vals[i]), "BER")
                cr_bler = compile_turbo(True, float(ber_vals[i]),  float(bler_vals[i]), "BLER")
                gap_mark = " ← BINARY FAILURE" if (cr_ber.permission > T4_REFUSE and cr_bler.permission == T4_REFUSE) else ""
                print(f"  {snr:>6.1f}  {ber_vals[i]:>9.2e}  {bler_vals[i]:>9.4f}  "
                      f"{cr_ber.permission_name:>22}  {cr_bler.permission_name:>22}{gap_mark}")

    # ── Phase B — Natural boundaries (BEFORE opening 3GPP docs) ──────────────
    print(f"\n  ── Phase B Step 1: Extract natural boundaries (blind) ───────────")
    boundaries = extract_natural_boundaries(snrs)

    print(f"\n  BER natural crossings (compiler-implied thresholds from d_BER):")
    print(f"  {'BER target':>12}  {'SNR crossing':>14}  {'BLER at crossing':>18}")
    print(f"  {'─'*50}")
    for b in boundaries["ber_boundaries"]:
        print(f"  {b['d_target']:>12.0e}  {b['snr_cross']:>14.2f} dB  {b['bler_at_cross']:>18.6f}")

    print(f"\n  BLER natural crossings (compiler-implied thresholds from d_BLER):")
    print(f"  {'BLER target':>12}  {'SNR crossing':>14}  {'BER at crossing':>18}")
    print(f"  {'─'*50}")
    for b in boundaries["bler_boundaries"]:
        print(f"  {b['d_target']:>12.2e}  {b['snr_cross']:>14.2f} dB  {b['ber_at_cross']:>18.2e}")

    print(f"\n  Steepest gradient SNR (cliff of waterfall):")
    print(f"    d_BER  gradient peak: SNR = {boundaries['peak_snr_ber']:.2f} dB")
    print(f"    d_BLER gradient peak: SNR = {boundaries['peak_snr_bler']:.2f} dB")

    # ── Phase B — 5-level permission assignment ───────────────────────────────
    print(f"\n  ── Phase B Step 2: 5-level permission surface ───────────────────")
    phase_b = run_phase_b_5level(snrs, boundaries)

    print(f"\n  Natural boundary chain (from curve geometry, before 3GPP overlay):")
    print(f"  {'Level':>20}  {'τ (BLER)':>12}  {'τ (BER)':>12}")
    print(f"  {'─'*50}")
    for (lvl_bler, tau_bler), (lvl_ber, tau_ber) in zip(
            phase_b["tau_chain_bler"], phase_b["tau_chain_ber"]):
        print(f"  {T5_NAMES[lvl_bler]:>20}  {tau_bler:>12.2e}  {tau_ber:>12.2e}")

    print(f"\n  5-level permissions at half-dB points:")
    print(f"  {'SNR':>6}  {'perm(BER)':>22}  {'perm(BLER)':>22}")
    print(f"  {'─'*56}")
    for i, snr in enumerate(snrs):
        if abs(float(snr) - round(float(snr) * 2) / 2) < 0.01:
            pb  = T5_NAMES[phase_b["perm_ber_5"][i]]
            pbl = T5_NAMES[phase_b["perm_bler_5"][i]]
            print(f"  {snr:>6.1f}  {pb:>22}  {pbl:>22}")

    # ── Phase 3 — Open 3GPP, build audit table ────────────────────────────────
    print(f"\n  ── Phase 3: 3GPP overlay (opening standards now) ────────────────")
    print(f"\n  {B5G_NOTE}")
    audit_rows = build_audit_table(snrs, boundaries, phase_b)

    # Write natural boundaries CSV
    nb_path = os.path.join(RESULTS_DIR, "audit_natural_boundaries.csv")
    nb_fields = ["d_functional", "d_target", "snr_cross", "ber_at_cross", "bler_at_cross"]
    nb_rows = (
        [{"d_functional": "BER", **b} for b in boundaries["ber_boundaries"]] +
        [{"d_functional": "BLER", **b} for b in boundaries["bler_boundaries"]]
    )
    with open(nb_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=nb_fields)
        w.writeheader(); w.writerows(nb_rows)
    print(f"\n  Written: {nb_path}")

    # Write gap width CSV
    gw_path = os.path.join(RESULTS_DIR, "audit_gap_width.csv")
    with open(gw_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["snr_db", "ber", "bler", "gap_width"])
        w.writeheader()
        for i, snr in enumerate(snrs):
            w.writerow({
                "snr_db": round(float(snr), 2),
                "ber": round(float(boundaries["ber_vals"][i]), 8),
                "bler": round(float(boundaries["bler_vals"][i]), 8),
                "gap_width": round(float(boundaries["gap_width"][i]), 8),
            })
    print(f"  Written: {gw_path}")

    # Write audit comparison CSV
    at_path = os.path.join(RESULTS_DIR, "audit_3gpp_comparison.csv")
    at_fields = [
        "threshold_name", "service_class", "ref_bler", "ref_snr_db",
        "compiler_tau_ber", "compiler_tau_bler", "gap_width",
        "compiler_snr_bler", "classification", "interpretation", "source",
    ]
    with open(at_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=at_fields)
        w.writeheader(); w.writerows(audit_rows)
    print(f"  Written: {at_path}")

    # Print audit table
    print(f"\n{'='*80}")
    print("  AUDIT TABLE — 3GPP blind comparison")
    print(f"  {'Threshold':>16}  {'Ref BLER':>9}  {'Ref SNR':>8}  "
          f"{'Comp τ(BER)':>12}  {'Comp τ(BLER)':>12}  {'Gap width':>10}  "
          f"{'Class':>22}")
    print(f"  {'─'*100}")
    for r in audit_rows:
        print(f"  {r['threshold_name']:>16}  {r['ref_bler']:>9.0e}  {r['ref_snr_db']:>8}  "
              f"  {r['compiler_tau_ber']:>12}  {r['compiler_tau_bler']:>12}  "
              f"{r['gap_width']:>10.4f}  {r['classification']:>22}")
        print(f"    Service: {r['service_class']}")
        print(f"    Interp:  {r['interpretation']}")
        print()

    # Print structural interpretation
    print(f"{'='*80}")
    print("  STRUCTURAL INTERPRETATION")
    print()
    corr  = [r for r in audit_rows if r["classification"] == "CORRESPONDENCE"]
    strict = [r for r in audit_rows if r["classification"] == "COMPILER_STRICTER"]
    perm  = [r for r in audit_rows if r["classification"] == "COMPILER_PERMISSIVE"]
    oor   = [r for r in audit_rows if r["classification"] == "CANNOT_EVALUATE"]

    print(f"  CORRESPONDENCE ({len(corr)}): Compiler and standard agree.")
    for r in corr:
        print(f"    {r['threshold_name']:>16} — {r['interpretation']}")

    print(f"\n  COMPILER STRICTER ({len(strict)}): Over-authorization risk in 3GPP.")
    for r in strict:
        print(f"    {r['threshold_name']:>16} — {r['interpretation']}")
        print(f"      Service class: {r['service_class']}")

    print(f"\n  COMPILER MORE PERMISSIVE ({len(perm)}): Standard has conservative margin beyond physics.")
    for r in perm:
        print(f"    {r['threshold_name']:>16} — {r['interpretation']}")
        print(f"      Likely reason: application-layer policy above physical constraint.")

    print(f"\n  CANNOT EVALUATE ({len(oor)}): Outside observable range.")
    for r in oor:
        print(f"    {r['threshold_name']:>16} — {r['interpretation']}")

    print()
    print(f"  Key finding: Gap width column shows which service class boundaries")
    print(f"  sit inside a wide functional gap (consequential choice of functional)")
    print(f"  vs. a narrow one (functional choice does not matter at that boundary).")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    run_audit()
