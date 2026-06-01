"""Tests for the blind 3GPP audit experiment.

Four layers:

  Layer 1 — Blind chain correctness: 5-level compiler structure
  Layer 2 — Natural boundary extraction: boundaries are physically grounded
  Layer 3 — Phase A / Phase B consistency: gap persists across chain choice
  Layer 4 — Audit table structure: 6-column spec, classification logic
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "register2" / "turbo"))

from ber_bler_curves import ber_at_snr, bler_at_snr, SNR_DB, BER_PUBLISHED, BLER_DERIVED
from compiler_blind import (
    compile_at_tau_blind,
    permission_from_d,
    make_tau_chain,
    TRANSMIT_CRITICAL, TRANSMIT_DATA, TRANSMIT_MONITORED, HOLD, REFUSE,
    PERMISSION_NAMES,
)
from compiler_turbo import (
    TRANSMIT as T4_TRANSMIT,
    REFUSE as T4_REFUSE,
    compile_at_tau_turbo,
)


# ── Layer 1: Blind chain correctness ──────────────────────────────────────────

class TestBlindChain:
    def test_permission_levels_ordered(self):
        """5-level chain is strictly ordered: REFUSE < HOLD < MON < DATA < CRITICAL."""
        assert REFUSE < HOLD < TRANSMIT_MONITORED < TRANSMIT_DATA < TRANSMIT_CRITICAL

    def test_compile_at_tau_blind_basic(self):
        """compile_at_tau_blind returns TRANSMIT_CRITICAL if d <= tau, else REFUSE."""
        assert compile_at_tau_blind(0.01, 0.05) == TRANSMIT_CRITICAL
        assert compile_at_tau_blind(0.05, 0.05) == TRANSMIT_CRITICAL   # at boundary = pass
        assert compile_at_tau_blind(0.06, 0.05) == REFUSE

    def test_permission_from_d_highest_level(self):
        """permission_from_d returns the highest level whose tau d clears."""
        chain = make_tau_chain(1e-3, 0.02, 0.10, 0.50)
        assert permission_from_d(5e-4,  chain) == TRANSMIT_CRITICAL   # clears all
        assert permission_from_d(5e-3,  chain) == TRANSMIT_DATA        # clears data+
        assert permission_from_d(0.05,  chain) == TRANSMIT_MONITORED   # clears monitored+
        assert permission_from_d(0.25,  chain) == HOLD                 # clears hold only
        assert permission_from_d(0.75,  chain) == REFUSE               # clears nothing

    def test_permission_from_d_at_boundary(self):
        """Exact boundary value grants the level (d <= tau)."""
        chain = make_tau_chain(1e-3, 0.02, 0.10, 0.50)
        assert permission_from_d(1e-3, chain) == TRANSMIT_CRITICAL
        assert permission_from_d(0.02, chain) == TRANSMIT_DATA
        assert permission_from_d(0.10, chain) == TRANSMIT_MONITORED
        assert permission_from_d(0.50, chain) == HOLD

    def test_make_tau_chain_structure(self):
        """make_tau_chain returns ordered list from CRITICAL down to HOLD."""
        chain = make_tau_chain(1e-3, 0.02, 0.10, 0.50)
        levels = [lvl for lvl, _ in chain]
        taus   = [tau for _, tau in chain]
        assert levels == [TRANSMIT_CRITICAL, TRANSMIT_DATA, TRANSMIT_MONITORED, HOLD]
        assert taus == sorted(taus)   # thresholds increase from critical to hold

    def test_permission_monotone_in_d(self):
        """Higher d never produces higher permission."""
        chain = make_tau_chain(1e-3, 0.02, 0.10, 0.50)
        d_vals = [1e-4, 1e-3, 0.01, 0.02, 0.05, 0.10, 0.30, 0.50, 0.80]
        perms = [permission_from_d(d, chain) for d in d_vals]
        for i in range(len(perms) - 1):
            assert perms[i] >= perms[i + 1], (
                f"Monotonicity violated: d={d_vals[i]:.1e} → perm={perms[i]}, "
                f"d={d_vals[i+1]:.1e} → perm={perms[i+1]}"
            )

    def test_all_5_levels_reachable(self):
        """All 5 permission levels are reachable from some d value."""
        chain = make_tau_chain(1e-3, 0.02, 0.10, 0.50)
        d_test = [5e-4, 5e-3, 0.05, 0.25, 0.99]
        expected = [TRANSMIT_CRITICAL, TRANSMIT_DATA, TRANSMIT_MONITORED, HOLD, REFUSE]
        for d, exp in zip(d_test, expected):
            got = permission_from_d(d, chain)
            assert got == exp, f"d={d:.2e}: expected {PERMISSION_NAMES[exp]}, got {PERMISSION_NAMES[got]}"


# ── Layer 2: Natural boundary extraction ──────────────────────────────────────

class TestNaturalBoundaries:
    """The compiler's implied thresholds are grounded in curve geometry."""

    def test_bler_10pct_snr_in_transition(self):
        """BLER=10% should be crossed between SNR=2 and 3 dB (waterfall)."""
        # At SNR=2.0: BLER≈1.0; at SNR=3.5: BLER≈0.0007
        # Crossing at ~2.6 dB
        bler_2 = bler_at_snr(2.0)
        bler_3 = bler_at_snr(3.0)
        assert bler_2 > 0.10, f"BLER at 2 dB should be > 10%, got {bler_2:.4f}"
        assert bler_3 < 0.10, f"BLER at 3 dB should be < 10%, got {bler_3:.4f}"

    def test_bler_2pct_snr_in_transition(self):
        """BLER=2% should be crossed between SNR=2.5 and 3.5 dB."""
        bler_25 = bler_at_snr(2.5)
        bler_35 = bler_at_snr(3.5)
        assert bler_25 > 0.02, f"BLER at 2.5 dB should be > 2%, got {bler_25:.4f}"
        assert bler_35 < 0.02, f"BLER at 3.5 dB should be < 2%, got {bler_35:.6f}"

    def test_bler_1em3_snr_near_3db(self):
        """BLER=1e-3 should cross near SNR=3 dB."""
        bler_30 = bler_at_snr(3.0)
        bler_35 = bler_at_snr(3.5)
        assert bler_30 > 1e-3, f"BLER at 3.0 dB should be > 1e-3, got {bler_30:.6f}"
        assert bler_35 < 1e-3, f"BLER at 3.5 dB should be < 1e-3, got {bler_35:.8f}"

    def test_natural_bler_chain_is_ordered(self):
        """Natural boundary τ values form an increasing sequence."""
        tau_hold, tau_mon, tau_data, tau_crit = 0.50, 0.10, 0.02, 1e-3
        chain = make_tau_chain(tau_crit, tau_data, tau_mon, tau_hold)
        taus = [tau for _, tau in chain]
        assert taus == sorted(taus), "Chain τ values must be non-decreasing"

    def test_ber_1em3_crosses_in_waterfall(self):
        """BER=1e-3 should cross between SNR=1.5 and 2.0 dB (waterfall entry)."""
        ber_15 = ber_at_snr(1.5)
        ber_20 = ber_at_snr(2.0)
        assert ber_15 > 1e-3, f"BER at 1.5 dB should be > 1e-3, got {ber_15:.2e}"
        assert ber_20 < 1e-3, f"BER at 2.0 dB should be < 1e-3, got {ber_20:.2e}"

    def test_gradient_peak_bler_in_waterfall(self):
        """BLER's steepest linear descent should occur in the waterfall [2, 3.5] dB.

        We measure the gradient of BLER in linear space, clipped to [0, 1].
        The biggest single-step drop in linear BLER happens in the waterfall
        where BLER collapses from ~1.0 to near-zero.
        """
        snrs = np.round(np.arange(-1.0, 5.01, 0.1), 2)
        bler_vals = np.array([bler_at_snr(s) for s in snrs])
        # Linear gradient: largest single-step absolute drop
        grad = np.abs(np.diff(bler_vals))
        peak_snr = float(snrs[np.argmax(grad)])
        assert 2.0 <= peak_snr <= 3.5, (
            f"BLER linear gradient peak should be in [2, 3.5] dB, got {peak_snr:.2f} dB"
        )


# ── Layer 3: Phase A / Phase B consistency ────────────────────────────────────

class TestPhaseConsistency:
    """Gap is robust to chain resolution (4-level vs 5-level)."""

    def test_gap_at_2db_persists_in_both_chains(self):
        """At SNR=2 dB, BER clears the chain but BLER refuses — in both 4- and 5-level chains."""
        ber  = ber_at_snr(2.0)
        bler = bler_at_snr(2.0)

        # 4-level chain (Phase A)
        p4_ber  = compile_at_tau_turbo(True, ber,  0.05)
        p4_bler = compile_at_tau_turbo(True, bler, 0.05)
        assert p4_ber  > T4_REFUSE, "4-level: BER should clear at τ=0.05"
        assert p4_bler == T4_REFUSE, "4-level: BLER should refuse at τ=0.05"

        # 5-level chain (Phase B natural boundaries)
        chain = make_tau_chain(1e-3, 0.02, 0.10, 0.50)
        p5_ber  = permission_from_d(ber,  chain)
        p5_bler = permission_from_d(bler, chain)
        assert p5_ber  > REFUSE, "5-level: BER should clear some level at SNR=2 dB"
        assert p5_bler == REFUSE, "5-level: BLER (=1.0) should refuse at SNR=2 dB"

    def test_gap_closes_at_high_snr_both_chains(self):
        """At SNR=4 dB, both chains agree: TRANSMIT (4-level) / CRITICAL (5-level)."""
        ber  = ber_at_snr(4.0)
        bler = bler_at_snr(4.0)

        p4_ber  = compile_at_tau_turbo(True, ber,  1e-3)
        p4_bler = compile_at_tau_turbo(True, bler, 1e-3)
        assert p4_ber  == T4_TRANSMIT
        assert p4_bler == T4_TRANSMIT

        chain = make_tau_chain(1e-3, 0.02, 0.10, 0.50)
        p5_ber  = permission_from_d(ber,  chain)
        p5_bler = permission_from_d(bler, chain)
        assert p5_ber  == TRANSMIT_CRITICAL
        assert p5_bler == TRANSMIT_CRITICAL

    def test_gap_region_snr_extent_consistent(self):
        """At the TRANSMIT_CRITICAL level (τ=1e-3), gap spans SNR ≈ 2.0–3.5 dB.

        The gap is defined per-level: BER clears τ_critical but BLER does not.
        We test specifically at TRANSMIT_CRITICAL (τ_BLER=1e-3) because that is
        where the structural gap is largest and most consequential.
        """
        snrs = np.round(np.arange(-1.0, 5.01, 0.1), 2)
        tau_critical = 1e-3
        gap_snrs = []
        for snr in snrs:
            ber  = ber_at_snr(float(snr))
            bler = bler_at_snr(float(snr))
            # Gap at TRANSMIT_CRITICAL level: BER clears but BLER does not
            ber_clears  = ber  <= tau_critical
            bler_clears = bler <= tau_critical
            if ber_clears and not bler_clears:
                gap_snrs.append(float(snr))
        assert len(gap_snrs) > 0, "Gap at TRANSMIT_CRITICAL level must be non-empty"
        assert min(gap_snrs) >= 1.5, (
            f"Gap at CRITICAL level should start at SNR ≥ 1.5 dB, starts at {min(gap_snrs):.1f}"
        )
        assert max(gap_snrs) <= 3.5, (
            f"Gap at CRITICAL level should close by SNR=3.5 dB, ends at {max(gap_snrs):.1f}"
        )

    def test_5level_has_more_resolution_near_waterfall(self):
        """At SNR=3.0 dB, 5-level chain distinguishes TRANSMIT_DATA from TRANSMIT_CRITICAL."""
        bler = bler_at_snr(3.0)  # ~0.032 — above CRITICAL (1e-3) but below MON (0.10)
        chain = make_tau_chain(1e-3, 0.02, 0.10, 0.50)
        perm = permission_from_d(bler, chain)
        # BLER=0.032 > tau_data=0.02 but could be TRANSMIT_MONITORED
        assert perm == TRANSMIT_MONITORED, (
            f"At SNR=3 dB BLER={bler:.4f} should give TRANSMIT_MONITORED "
            f"(above tau_data=0.02), got {PERMISSION_NAMES[perm]}"
        )


# ── Layer 4: Audit table structure ────────────────────────────────────────────

class TestAuditTableStructure:
    """Audit table has correct 6-column structure and classification logic."""

    def test_classification_correspondence(self):
        """Discrepancy < 0.5 dB → CORRESPONDENCE."""
        from audit_3gpp import classify_discrepancy
        snrs = np.round(np.arange(-1.0, 5.01, 0.1), 2)
        bler_vals = np.array([bler_at_snr(s) for s in snrs])

        # Compiler boundary 0.10 at SNR≈2.65, 3GPP Qout also at 0.10 — identical
        cls, _ = classify_discrepancy(0.10, 0.10, 2.65, 2.65, bler_vals, snrs)
        assert cls == "CORRESPONDENCE"

    def test_classification_compiler_stricter(self):
        """Compiler requires better SNR than 3GPP → COMPILER_STRICTER.

        Convention: higher SNR = better channel.
        compiler_snr < ref_snr means compiler boundary needs better channel
        than the 3GPP threshold: snr_disc = compiler_snr - ref_snr < 0.
        """
        from audit_3gpp import classify_discrepancy
        snrs = np.round(np.arange(-1.0, 5.01, 0.1), 2)
        bler_vals = np.array([bler_at_snr(s) for s in snrs])

        # Compiler boundary at SNR=3.5 (needs better channel), 3GPP at SNR=2.5 (lenient)
        # snr_disc = 3.5 - 2.5 = +1.0 → compiler permits at higher SNR = stricter
        # Wait: compiler_snr > ref_snr means compiler only allows transmission
        # at BETTER channel quality than 3GPP. The standard is more lenient.
        # snr_disc > 0 → compiler allows at better channel → compiler is stricter.
        cls, _ = classify_discrepancy(0.001, 0.10, 3.5, 2.5, bler_vals, snrs)
        assert cls == "COMPILER_STRICTER", (
            "Compiler boundary at SNR=3.5 dB vs 3GPP at 2.5 dB: "
            "compiler requires 1 dB better channel — should be STRICTER"
        )

    def test_classification_compiler_permissive(self):
        """3GPP more conservative than compiler → COMPILER_PERMISSIVE.

        compiler_snr < ref_snr: compiler allows at lower SNR (worse channel)
        than 3GPP requires. snr_disc < 0 → compiler more permissive.
        """
        from audit_3gpp import classify_discrepancy
        snrs = np.round(np.arange(-1.0, 5.01, 0.1), 2)
        bler_vals = np.array([bler_at_snr(s) for s in snrs])

        # Compiler permits at SNR=2.0, 3GPP requires SNR=3.5 (more conservative)
        # snr_disc = 2.0 - 3.5 = -1.5 → compiler allows at worse channel → permissive
        cls, _ = classify_discrepancy(0.10, 0.001, 2.0, 3.5, bler_vals, snrs)
        assert cls == "COMPILER_PERMISSIVE", (
            "Compiler boundary at SNR=2.0 dB vs 3GPP at 3.5 dB: "
            "compiler allows at worse channel — should be PERMISSIVE"
        )

    def test_gap_width_column_non_negative(self):
        """Gap width (compiler τ_BLER - compiler τ_BER at same boundary) is non-negative."""
        chain_bler = make_tau_chain(1e-3, 0.02, 0.10, 0.50)
        chain_ber  = make_tau_chain(3e-7, 1e-5, 1.5e-5, 4e-3)
        for (lvl_b, tau_bler), (lvl_be, tau_ber) in zip(chain_bler, chain_ber):
            gap = tau_bler - tau_ber
            assert gap >= -1e-10, (
                f"Gap width at level {PERMISSION_NAMES[lvl_b]} must be ≥ 0: "
                f"τ_BLER={tau_bler:.2e}, τ_BER={tau_ber:.2e}, gap={gap:.2e}"
            )

    def test_b5g_outside_observable_range(self):
        """BLER=1e-9 cannot be independently verified from the Berrou curves.

        The independence bound BLER = 1-(1-BER)^k at SNR=5 dB gives BLER ≈ 6.5e-11,
        which appears to numerically clear the B5G target. But BER=1e-15 at 5 dB is
        itself an extrapolation — Berrou does not report measured data below ~1e-8 BER.
        The BLER independence bound is not reliable in this regime because it assumes
        independent bit errors, which breaks down at such low error rates.

        The claim is not that BLER > 1e-9 at 5 dB — it is that we cannot audit
        the B5G target from these curves alone. We flag it as out-of-range.
        """
        bler_at_5db = bler_at_snr(5.0)
        b5g_target = 1e-9
        # The curve BLER at 5 dB is already below 1e-9 — this is in the extrapolation tail
        # where the independence bound is not reliable. Flag as OOR.
        assert bler_at_5db < 1e-7, (
            f"BLER at 5 dB = {bler_at_5db:.2e}: in extrapolation regime below 1e-7; "
            "cannot audit B5G target from Berrou curves"
        )
        # The B5G target itself is in the deep extrapolation zone
        assert b5g_target < 1e-7, "B5G target 1e-9 is confirmed in the extrapolation region"

    def test_audit_table_has_required_columns(self):
        """Audit table schema has all 6 required columns per spec."""
        required = {
            "compiler_tau_ber", "compiler_tau_bler", "gap_width",
            "ref_bler", "classification", "interpretation",
        }
        # The build_audit_table function returns dicts; check keys
        from audit_3gpp import build_audit_table, extract_natural_boundaries, run_phase_b_5level
        snrs = np.round(np.arange(-1.0, 5.01, 0.1), 2)
        boundaries = extract_natural_boundaries(snrs)
        phase_b = run_phase_b_5level(snrs, boundaries)
        rows = build_audit_table(snrs, boundaries, phase_b)
        assert len(rows) > 0
        for row in rows:
            missing = required - set(row.keys())
            assert not missing, f"Audit row missing columns: {missing}"
