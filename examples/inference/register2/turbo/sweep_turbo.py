"""Threshold sweep for turbo codes: permission surface over (SNR, tau).

Structural mirror of Register 1 (ising/run_threshold_sweep.py).

For each SNR value from the published curves:
  - d_BER = bit error rate (analogous to mean TV)
  - d_BLER = block error rate (analogous to max TV)
  - gap(SNR, tau) = 1 if d_BER(SNR) <= tau < d_BLER(SNR)

The gap region is the SNR interval where a BER-licensed system transmits
but a BLER-licensed system refuses. It is structural: it follows from the
relationship between bit-level and block-level error accumulation.

Outputs:
  results/turbo_sweep_surface.csv  — fine sweep (200 tau points)
  results/turbo_sweep_summary.csv  — gap statistics + coarse table
  results/turbo_coarse_table.csv   — standard practitioner operating points
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from ber_bler_curves import SNR_DB, BER_PUBLISHED, BLER_DERIVED, BLOCK_LENGTH_K
from compiler_turbo import (
    compile_turbo, compile_at_tau_turbo,
    TAU_BER, TAU_BLER,
    TRANSMIT, TRANSMIT_MONITORED, HOLD, REFUSE, PERMISSION_NAMES,
)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Fine sweep: 200 tau points in [0, 1]
TAU_FINE = np.linspace(0.0, 1.0, 200)

# Coarse table: practitioner SNR operating points (dB)
# Standard 3GPP evaluation grid for AWGN channel
SNR_COARSE = [-1.0, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]

SURFACE_FIELDNAMES = [
    "snr_db", "tau",
    "ber", "bler",
    "perm_ber", "perm_bler",
    "gap",
]

SUMMARY_FIELDNAMES = [
    "snr_db",
    "ber", "bler",
    "gap_width",     # bler - ber: the tau interval in the gap
    "gap_tau_lo",    # = ber
    "gap_tau_hi",    # = bler
    "perm_ber_default",   # permission under BER at standard τ_BER[TRANSMIT]
    "perm_bler_default",  # permission under BLER at standard τ_BLER[TRANSMIT]
    "gap_at_default",     # 1 if BER grants TRANSMIT but BLER refuses
]

COARSE_FIELDNAMES = [
    "snr_db", "ber", "bler",
    "perm_ber", "perm_bler",
    "gap",
    "note",
]


def run_sweep() -> None:
    print(f"\n{'='*80}")
    print("  Register 2 — Turbo Code Threshold Sweep")
    print("  Functionals: BER (mean-like, over-authorizes) vs BLER (max-like, gap detector)")
    print(f"  Source: Berrou, Glavieux, Thitimajshima (1993) ICC; k={BLOCK_LENGTH_K} bits")
    print(f"{'='*80}\n")

    # ── Fine sweep ────────────────────────────────────────────────────────────
    surface_rows: list[dict] = []
    summary_rows: list[dict] = []

    for snr, ber, bler in zip(SNR_DB, BER_PUBLISHED, BLER_DERIVED):
        gap_taus: list[float] = []
        for tau in TAU_FINE:
            p_ber  = compile_at_tau_turbo(True, ber, float(tau))
            p_bler = compile_at_tau_turbo(True, bler, float(tau))
            gap = 1 if (p_ber == TRANSMIT and p_bler == REFUSE) else 0
            if gap:
                gap_taus.append(float(tau))
            surface_rows.append({
                "snr_db": snr,
                "tau": round(float(tau), 4),
                "ber": ber,
                "bler": round(float(bler), 8),
                "perm_ber": p_ber,
                "perm_bler": p_bler,
                "gap": gap,
            })

        gap_width = float(bler) - float(ber)
        # Default permission at standard fixed thresholds
        cr_ber  = compile_turbo(True, ber, bler, functional="BER")
        cr_bler = compile_turbo(True, ber, bler, functional="BLER")
        gap_at_default = (cr_ber.permission == TRANSMIT and
                          cr_bler.permission < TRANSMIT)

        summary_rows.append({
            "snr_db": snr,
            "ber": ber,
            "bler": round(float(bler), 8),
            "gap_width": round(max(0.0, gap_width), 6),
            "gap_tau_lo": round(float(ber), 8),
            "gap_tau_hi": round(float(bler), 8),
            "perm_ber_default": cr_ber.permission_name,
            "perm_bler_default": cr_bler.permission_name,
            "gap_at_default": int(gap_at_default),
        })

        gap_str = f"gap=[{ber:.2e}, {bler:.4f}]" if gap_taus else "no gap"
        print(f"  SNR={snr:>5.1f} dB  BER={ber:.2e}  BLER={bler:.4f}  "
              f"perm(BER)={cr_ber.permission_name:<22} perm(BLER)={cr_bler.permission_name:<22}  {gap_str}")

    # ── Coarse table ──────────────────────────────────────────────────────────
    coarse_rows: list[dict] = []
    for snr_c in SNR_COARSE:
        ber_c  = float(np.interp(snr_c, SNR_DB, BER_PUBLISHED))
        bler_c = float(np.interp(snr_c, SNR_DB, BLER_DERIVED))
        cr_ber  = compile_turbo(True, ber_c, bler_c, functional="BER")
        cr_bler = compile_turbo(True, ber_c, bler_c, functional="BLER")
        gap = cr_ber.permission > HOLD and cr_bler.permission <= HOLD

        note = ""
        if snr_c == 1.5:
            note = "BER waterfall complete, BLER still at 1.0"
        elif snr_c == 3.0:
            note = "both converge to TRANSMIT"

        coarse_rows.append({
            "snr_db": snr_c,
            "ber": f"{ber_c:.2e}",
            "bler": f"{bler_c:.4f}",
            "perm_ber": cr_ber.permission_name,
            "perm_bler": cr_bler.permission_name,
            "gap": gap,
            "note": note,
        })

    # ── Write CSVs ────────────────────────────────────────────────────────────
    surface_path = os.path.join(RESULTS_DIR, "turbo_sweep_surface.csv")
    with open(surface_path, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=SURFACE_FIELDNAMES).writeheader()
        csv.DictWriter(f, fieldnames=SURFACE_FIELDNAMES).writerows(surface_rows)
    print(f"\n  Written: {surface_path}")

    summary_path = os.path.join(RESULTS_DIR, "turbo_sweep_summary.csv")
    with open(summary_path, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=SUMMARY_FIELDNAMES).writeheader()
        csv.DictWriter(f, fieldnames=SUMMARY_FIELDNAMES).writerows(summary_rows)
    print(f"  Written: {summary_path}")

    coarse_path = os.path.join(RESULTS_DIR, "turbo_coarse_table.csv")
    with open(coarse_path, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=COARSE_FIELDNAMES).writeheader()
        csv.DictWriter(f, fieldnames=COARSE_FIELDNAMES).writerows(coarse_rows)
    print(f"  Written: {coarse_path}")

    # ── Print coarse table ────────────────────────────────────────────────────
    print(f"\n{'='*80}")
    print("  COARSE PERMISSION TABLE — standard operating points")
    print(f"  τ_BER(TRANSMIT)={TAU_BER[TRANSMIT]:.0e}  τ_BLER(TRANSMIT)={TAU_BLER[TRANSMIT]:.0e}")
    print(f"  {'SNR':>6}  {'BER':>9}  {'BLER':>9}  {'perm(BER)':>22}  {'perm(BLER)':>22}  gap?")
    print(f"  {'─'*75}")
    for row in coarse_rows:
        gap_mark = "  ← BINARY FAILURE" if row["gap"] else ""
        print(f"  {row['snr_db']:>6.1f}  {row['ber']:>9}  {row['bler']:>9}  "
              f"{row['perm_ber']:>22}  {row['perm_bler']:>22}  {str(row['gap']):>5}{gap_mark}")

    # ── Key finding ───────────────────────────────────────────────────────────
    print(f"\n{'='*80}")
    print("  THE GAP:")
    print("  At SNR = 1.5–2.5 dB, BER has dropped below 10^-3 (TRANSMIT_MONITORED).")
    print("  BLER remains at ~1.0 (every block fails) through 2.5 dB.")
    print("  A BER-licensed system transmits in this region.")
    print("  A BLER-licensed system refuses: every decoded block contains at least one error.")
    print()
    print("  The gap spans ~1 dB in SNR — practically significant.")
    print("  It is not a consequence of threshold choice: it persists across the full τ sweep.")
    print("  It is structural: it follows from 1-(1-BER)^k, the block-failure accumulation law.")
    print()
    print("  CROSS-REGISTER ANALOGY:")
    print("  d_BER  ≡  d1 (mean TV):  averages over bits/variables, hides block/worst-case failures")
    print("  d_BLER ≡  d2 (max TV):   a block fails if any bit fails — worst-case component")
    print("  The compiler does not know it is running on inference vs. communications.")
    print("  It sees a divergence functional and a permission chain. The gap is the same phenomenon.")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    run_sweep()
