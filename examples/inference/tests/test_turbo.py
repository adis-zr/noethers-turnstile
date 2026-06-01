"""Tests for Register 2: turbo code compiler and threshold sweep.

Three layers mirroring Register 1:

  Layer 1 — Published curve correctness: BER/BLER values consistent with
             Berrou 1993 and the analytical BLER derivation
  Layer 2 — Compiler correctness: permission chain, failure vector, gap detection
  Layer 3 — Structural finding: gap region is non-empty, persists across τ sweep,
             spans ~1 dB in SNR, and the analogy to Register 1 holds structurally
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "register2" / "turbo"))

from ber_bler_curves import (
    SNR_DB, BER_PUBLISHED, BLER_DERIVED, BLOCK_LENGTH_K,
    ber_at_snr, bler_at_snr,
)
from compiler_turbo import (
    compile_turbo, compile_at_tau_turbo,
    TurboFailureVector,
    TRANSMIT, TRANSMIT_MONITORED, HOLD, REFUSE,
    TAU_BER, TAU_BLER,
)


# ── Layer 1: Published curve correctness ──────────────────────────────────────

class TestBERBLERCurves:
    def test_bler_derived_from_ber(self):
        """BLER must equal 1-(1-BER)^k analytically."""
        expected = 1.0 - (1.0 - BER_PUBLISHED) ** BLOCK_LENGTH_K
        np.testing.assert_allclose(BLER_DERIVED, expected, rtol=1e-9)

    def test_bler_geq_ber_everywhere(self):
        """BLER ≥ BER for all SNR values (block error rate ≥ bit error rate)."""
        assert (BLER_DERIVED >= BER_PUBLISHED).all(), (
            "BLER must be >= BER: a block fails if any bit fails"
        )

    def test_ber_monotone_decreasing_in_snr(self):
        """BER must be non-increasing as SNR increases."""
        for i in range(len(BER_PUBLISHED) - 1):
            assert BER_PUBLISHED[i] >= BER_PUBLISHED[i + 1], (
                f"BER not monotone: SNR={SNR_DB[i]} BER={BER_PUBLISHED[i]:.2e} > "
                f"SNR={SNR_DB[i+1]} BER={BER_PUBLISHED[i+1]:.2e}"
            )

    def test_bler_monotone_decreasing_in_snr(self):
        """BLER must be non-increasing as SNR increases."""
        for i in range(len(BLER_DERIVED) - 1):
            assert BLER_DERIVED[i] >= BLER_DERIVED[i + 1], (
                f"BLER not monotone at SNR={SNR_DB[i]}"
            )

    def test_ber_near_zero_at_high_snr(self):
        """At SNR=5 dB, turbo code BER should be effectively zero."""
        ber_5db = ber_at_snr(5.0)
        assert ber_5db < 1e-10, f"BER at 5 dB should be < 1e-10, got {ber_5db:.2e}"

    def test_bler_near_one_at_low_snr(self):
        """At SNR=-1 dB, BLER should be effectively 1 (every block fails)."""
        bler_neg1 = bler_at_snr(-1.0)
        assert bler_neg1 > 0.99, f"BLER at -1 dB should be ~1.0, got {bler_neg1:.4f}"

    def test_ber_in_waterfall_at_2db(self):
        """At SNR=2 dB, BER should be in the waterfall region (< 10^-3)."""
        ber_2db = ber_at_snr(2.0)
        assert ber_2db < 1e-3, f"BER at 2 dB should be < 1e-3 (waterfall), got {ber_2db:.2e}"

    def test_bler_still_high_at_2db(self):
        """At SNR=2 dB, BLER should still be very high (>0.99) — the gap."""
        bler_2db = bler_at_snr(2.0)
        assert bler_2db > 0.99, f"BLER at 2 dB should be > 0.99 (gap region), got {bler_2db:.4f}"


# ── Layer 2: Compiler correctness ─────────────────────────────────────────────

class TestTurboCompilerLogic:
    def test_high_snr_ber_gives_transmit(self):
        """At SNR=4 dB, BER-only compiler emits TRANSMIT."""
        cr = compile_turbo(True, ber_at_snr(4.0), bler_at_snr(4.0), functional="BER")
        assert cr.permission == TRANSMIT

    def test_high_snr_bler_gives_transmit(self):
        """At SNR=4 dB, BLER-only compiler emits TRANSMIT."""
        cr = compile_turbo(True, ber_at_snr(4.0), bler_at_snr(4.0), functional="BLER")
        assert cr.permission == TRANSMIT

    def test_low_snr_both_refuse(self):
        """At SNR=-1 dB, both functionals emit REFUSE."""
        cr_ber  = compile_turbo(True, ber_at_snr(-1.0), bler_at_snr(-1.0), functional="BER")
        cr_bler = compile_turbo(True, ber_at_snr(-1.0), bler_at_snr(-1.0), functional="BLER")
        assert cr_ber.permission == REFUSE
        assert cr_bler.permission == REFUSE

    def test_gap_at_2db_ber_transmits_bler_refuses(self):
        """At SNR=2 dB, BER-compiler licenses TRANSMIT_MONITORED, BLER-compiler refuses."""
        ber = ber_at_snr(2.0)
        bler = bler_at_snr(2.0)
        cr_ber  = compile_turbo(True, ber, bler, functional="BER")
        cr_bler = compile_turbo(True, ber, bler, functional="BLER")
        assert cr_ber.permission > REFUSE, (
            f"BER compiler should grant some permission at SNR=2 dB (BER={ber:.2e})"
        )
        assert cr_bler.permission == REFUSE, (
            f"BLER compiler must refuse at SNR=2 dB (BLER={bler:.4f} >> threshold)"
        )

    def test_non_convergence_gives_refuse(self):
        """Convergence failure (f1) blocks everything."""
        cr = compile_turbo(False, 1e-8, 1e-4, functional="BER")
        assert cr.permission == REFUSE
        assert cr.failure_vector.convergence_failure

    def test_permission_monotone_in_ber(self):
        """Higher BER never produces stronger permission."""
        ber_vals = [1e-8, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1]
        perms = [compile_turbo(True, b, 0.0, functional="BER").permission for b in ber_vals]
        for i in range(len(perms) - 1):
            assert perms[i] >= perms[i + 1], (
                f"Monotonicity violated: BER={ber_vals[i]:.0e} → {perms[i]}, "
                f"BER={ber_vals[i+1]:.0e} → {perms[i+1]}"
            )

    def test_permission_monotone_in_bler(self):
        """Higher BLER never produces stronger permission."""
        bler_vals = [1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 0.5, 1.0]
        perms = [compile_turbo(True, 0.0, b, functional="BLER").permission for b in bler_vals]
        for i in range(len(perms) - 1):
            assert perms[i] >= perms[i + 1], (
                f"Monotonicity violated: BLER={bler_vals[i]:.0e} → {perms[i]}, "
                f"BLER={bler_vals[i+1]:.0e} → {perms[i+1]}"
            )

    def test_compile_at_tau_binary(self):
        """compile_at_tau_turbo is a binary ACT/REFUSE split at tau."""
        assert compile_at_tau_turbo(True, 0.01, 0.02) == TRANSMIT
        assert compile_at_tau_turbo(True, 0.01, 0.005) == REFUSE
        assert compile_at_tau_turbo(True, 0.01, 0.01) == TRANSMIT  # at threshold = ACT

    def test_compile_at_tau_non_convergence(self):
        """Non-convergence always gives REFUSE regardless of tau."""
        assert compile_at_tau_turbo(False, 0.0, 1.0) == REFUSE

    def test_failure_vector_all_bits_on_low_snr(self):
        """At SNR=-1 dB, all failure bits should be set."""
        fv = TurboFailureVector.from_run(True, ber_at_snr(-1.0), bler_at_snr(-1.0))
        assert fv.ber_exceeds_transmit
        assert fv.ber_exceeds_monitored
        assert fv.bler_exceeds_transmit
        assert fv.bler_exceeds_monitored

    def test_failure_vector_no_bits_at_high_snr(self):
        """At SNR=5 dB, no failure bits should be set."""
        fv = TurboFailureVector.from_run(True, ber_at_snr(5.0), bler_at_snr(5.0))
        assert not fv.convergence_failure
        assert not fv.ber_exceeds_transmit
        assert not fv.bler_exceeds_transmit


# ── Layer 3: Structural finding ───────────────────────────────────────────────

class TestTurboGapStructure:
    """The gap between BER-licensed and BLER-licensed operating points is structural."""

    def test_gap_exists_at_intermediate_snr(self):
        """At SNR=2 dB, d_BER < d_BLER — the gap interval [BER, BLER] is non-empty."""
        ber = ber_at_snr(2.0)
        bler = bler_at_snr(2.0)
        assert bler > ber, f"Gap must exist at SNR=2 dB: BER={ber:.2e}, BLER={bler:.4f}"

    def test_gap_width_at_2db_is_practically_significant(self):
        """Gap width at SNR=2 dB should span most of [0,1]."""
        ber = ber_at_snr(2.0)
        bler = bler_at_snr(2.0)
        gap_width = bler - ber
        assert gap_width > 0.5, (
            f"Gap width at SNR=2 dB should be > 0.5 (practically significant), "
            f"got {gap_width:.4f}"
        )

    def test_gap_spans_standard_tau_values(self):
        """The gap at SNR=2.0 dB covers the standard reporting threshold tau=0.05."""
        ber = ber_at_snr(2.0)
        bler = bler_at_snr(2.0)
        tau = 0.05  # standard reporting threshold
        in_gap = ber <= tau < bler
        assert in_gap, (
            f"tau=0.05 should be in gap at SNR=2 dB: BER={ber:.2e}, BLER={bler:.4f}"
        )

    def test_gap_closes_at_high_snr(self):
        """At SNR=5 dB, BER ≈ BLER ≈ 0 — gap should be effectively zero."""
        ber = ber_at_snr(5.0)
        bler = bler_at_snr(5.0)
        gap_width = bler - ber
        assert gap_width < 1e-6, (
            f"Gap should close at SNR=5 dB, got width={gap_width:.2e}"
        )

    def test_bler_is_max_like_functional(self):
        """BLER = 1-(1-BER)^k is always >= BER, analogous to TV_max >= TV_mean."""
        for ber, bler in zip(BER_PUBLISHED, BLER_DERIVED):
            assert bler >= ber - 1e-12, (
                f"BLER={bler:.6f} must be >= BER={ber:.2e} — structural property"
            )

    def test_cross_register_analogy_holds_structurally(self):
        """d_BLER ≥ d_BER everywhere, just as TV_max ≥ TV_mean everywhere.

        The structural analogy: BLER aggregates over bits in the worst direction
        (any failure = block failure), while BER aggregates with mean. This is
        precisely the relationship between TV_max and TV_mean.
        """
        # Check the ratio BLER/BER grows dramatically in the intermediate SNR regime
        # (this is the structural amplification, same as TV_max/TV_mean grows near β_c)
        ber_2db  = ber_at_snr(2.0)
        bler_2db = bler_at_snr(2.0)
        ratio = bler_2db / ber_2db if ber_2db > 0 else float("inf")
        assert ratio > 1000, (
            f"BLER/BER ratio at SNR=2 dB should be >> 1000 (structural amplification), "
            f"got {ratio:.1f}"
        )

    def test_compile_at_tau_gap_is_binary(self):
        """At tau in [BER, BLER), BER compiler gives TRANSMIT and BLER gives REFUSE."""
        ber = ber_at_snr(2.0)
        bler = bler_at_snr(2.0)
        assert ber < bler, "precondition: gap exists at SNR=2 dB"

        tau_in_gap = (ber + bler) / 2.0
        p_ber  = compile_at_tau_turbo(True, ber,  tau_in_gap)
        p_bler = compile_at_tau_turbo(True, bler, tau_in_gap)

        assert p_ber  == TRANSMIT, f"BER compiler must give TRANSMIT at tau={tau_in_gap:.4f}"
        assert p_bler == REFUSE,   f"BLER compiler must give REFUSE at tau={tau_in_gap:.4f}"
