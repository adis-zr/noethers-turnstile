"""Tests for BLER independence bound sensitivity analysis.

Three layers:

  Layer 1 — Bias model correctness: uniform and transition-peaked models
  Layer 2 — Breaking-point analysis: CORRESPONDENCE holds within literature range
  Layer 3 — Paper claim: quantitative bounds at δ_conservative
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "register2" / "turbo"))

from ber_bler_curves import ber_at_snr, bler_at_snr
from sensitivity_bler import (
    apply_bias, snr_at_bler_crossing, classify, transition_weight,
    SNR_FINE, BER_FINE, BLER_FINE,
    DELTA_CONSERVATIVE, CORRESPONDENCE_THRESHOLD_DB,
    RLM_THRESHOLDS,
)


# ── Layer 1: Bias model correctness ───────────────────────────────────────────

class TestBiasModels:
    def test_uniform_zero_delta_is_identity(self):
        """At δ=0, uniform bias returns the original BLER values."""
        result = apply_bias(BLER_FINE, 0.0, "uniform")
        np.testing.assert_allclose(result, BLER_FINE, rtol=1e-10)

    def test_transition_zero_delta_is_identity(self):
        """At δ=0, transition-peaked bias returns the original BLER values."""
        result = apply_bias(BLER_FINE, 0.0, "transition")
        np.testing.assert_allclose(result, BLER_FINE, rtol=1e-10)

    def test_uniform_reduces_all_values(self):
        """Uniform bias with δ>0 reduces every non-zero BLER value."""
        result = apply_bias(BLER_FINE, 0.20, "uniform")
        for i, (orig, adj) in enumerate(zip(BLER_FINE, result)):
            if orig > 0:
                assert adj < orig, f"SNR={SNR_FINE[i]}: adj={adj:.4f} not < orig={orig:.4f}"

    def test_transition_peaks_at_waterfall_snr(self):
        """Transition weight peaks near SNR=2.75 dB and is near-zero at extremes."""
        w = transition_weight(SNR_FINE)
        peak_idx = np.argmax(w)
        peak_snr = float(SNR_FINE[peak_idx])
        assert 2.0 <= peak_snr <= 3.5, f"Transition weight should peak in [2, 3.5] dB, got {peak_snr}"
        # Weight at extremes is small
        w_at_minus1 = float(transition_weight(np.array([-1.0])))
        w_at_5      = float(transition_weight(np.array([5.0])))
        assert w_at_minus1 < 0.05, f"Weight at -1 dB should be near-zero, got {w_at_minus1:.4f}"
        assert w_at_5      < 0.05, f"Weight at +5 dB should be near-zero, got {w_at_5:.4f}"

    def test_transition_less_impact_than_uniform_at_extremes(self):
        """Transition model causes less BLER reduction than uniform at low/high SNR."""
        delta = 0.30
        bler_u = apply_bias(BLER_FINE, delta, "uniform")
        bler_t = apply_bias(BLER_FINE, delta, "transition")
        # At SNR=-1 dB (index 0), transition weight is near-zero
        assert bler_t[0] > bler_u[0], "Transition model should reduce less at SNR=-1 dB"
        # At the peak (SNR≈2.75 dB), transition weight ≈ 1 so BLER_t ≈ BLER_u
        # within a 1% tolerance (weight is 0.997, not exactly 1.0)
        peak_idx = int(np.argmin(np.abs(SNR_FINE - 2.75)))
        assert abs(bler_t[peak_idx] - bler_u[peak_idx]) < 0.01 * BLER_FINE[peak_idx] + 1e-6, (
            "At the transition peak, transition and uniform models should agree within 1%"
        )

    def test_bias_clamps_to_zero(self):
        """BLER never goes below zero regardless of δ."""
        result = apply_bias(BLER_FINE, 0.99, "uniform")
        assert (result >= 0.0).all(), "BLER must be non-negative after bias"

    def test_unknown_model_raises(self):
        """Unknown model name raises ValueError."""
        with pytest.raises(ValueError):
            apply_bias(BLER_FINE, 0.10, "bogus_model")


# ── Layer 2: Breaking-point analysis ──────────────────────────────────────────

class TestBreakingPoints:
    """CORRESPONDENCE never breaks within the physically plausible δ range."""

    @pytest.mark.parametrize("model", ["uniform", "transition"])
    @pytest.mark.parametrize("name,bler_target,snr_ref", RLM_THRESHOLDS)
    def test_correspondence_holds_at_conservative_delta(self, model, name, bler_target, snr_ref):
        """At δ=0.30 (conservative literature bound), CORRESPONDENCE holds for both models."""
        bler_adj  = apply_bias(BLER_FINE, DELTA_CONSERVATIVE, model)
        snr_comp  = snr_at_bler_crossing(bler_adj, bler_target)
        assert snr_comp is not None, f"{name}: SNR crossing not found at δ={DELTA_CONSERVATIVE}"
        cls = classify(snr_comp, snr_ref)
        assert cls == "CORRESPONDENCE", (
            f"{name} ({model}): at δ={DELTA_CONSERVATIVE}, SNR={snr_comp:.3f} dB, "
            f"disc={abs(snr_comp-snr_ref):.3f} dB ≥ {CORRESPONDENCE_THRESHOLD_DB} dB threshold"
        )

    @pytest.mark.parametrize("model", ["uniform", "transition"])
    @pytest.mark.parametrize("name,bler_target,snr_ref", RLM_THRESHOLDS)
    def test_correspondence_holds_at_extreme_delta_50pct(self, model, name, bler_target, snr_ref):
        """Even at δ=0.50 (50% BLER overstatement — physically implausible), CORRESPONDENCE holds."""
        bler_adj = apply_bias(BLER_FINE, 0.50, model)
        snr_comp = snr_at_bler_crossing(bler_adj, bler_target)
        assert snr_comp is not None, f"{name}: SNR crossing not found at δ=0.50"
        cls = classify(snr_comp, snr_ref)
        assert cls == "CORRESPONDENCE", (
            f"{name} ({model}): even at δ=0.50, SNR={snr_comp:.3f} dB, "
            f"disc={abs(snr_comp-snr_ref):.3f} dB — expected CORRESPONDENCE to hold"
        )

    def test_qout_shift_bounded_at_conservative_delta(self):
        """At δ=0.30 uniform, Qout SNR shift is less than 0.1 dB."""
        snr_base = snr_at_bler_crossing(BLER_FINE, 0.10)
        snr_adj  = snr_at_bler_crossing(apply_bias(BLER_FINE, DELTA_CONSERVATIVE, "uniform"), 0.10)
        assert snr_base is not None and snr_adj is not None
        shift = abs(snr_adj - snr_base)
        assert shift < 0.10, (
            f"Qout SNR shift at δ={DELTA_CONSERVATIVE}: {shift:.4f} dB — expected < 0.1 dB"
        )

    def test_qin_shift_bounded_at_conservative_delta(self):
        """At δ=0.30 uniform, Qin SNR shift is less than 0.2 dB."""
        snr_base = snr_at_bler_crossing(BLER_FINE, 0.02)
        snr_adj  = snr_at_bler_crossing(apply_bias(BLER_FINE, DELTA_CONSERVATIVE, "uniform"), 0.02)
        assert snr_base is not None and snr_adj is not None
        shift = abs(snr_adj - snr_base)
        assert shift < 0.20, (
            f"Qin SNR shift at δ={DELTA_CONSERVATIVE}: {shift:.4f} dB — expected < 0.2 dB"
        )


# ── Layer 3: Paper claim quantification ───────────────────────────────────────

class TestPaperClaim:
    """Quantitative bounds that directly support the paper-ready claim."""

    def test_qout_disc_from_3gpp_at_delta50_below_half_db(self):
        """Even at δ=0.50, Qout 3GPP discrepancy stays below 0.5 dB threshold."""
        bler_adj = apply_bias(BLER_FINE, 0.50, "uniform")
        snr_comp = snr_at_bler_crossing(bler_adj, 0.10)
        snr_ref  = 2.95  # 3GPP Qout reference
        assert snr_comp is not None
        disc = abs(snr_comp - snr_ref)
        assert disc < CORRESPONDENCE_THRESHOLD_DB, (
            f"Qout discrepancy at δ=0.50: {disc:.4f} dB — must be < {CORRESPONDENCE_THRESHOLD_DB} dB"
        )

    def test_qin_disc_from_3gpp_at_delta50_below_half_db(self):
        """Even at δ=0.50, Qin 3GPP discrepancy stays below 0.5 dB threshold."""
        bler_adj = apply_bias(BLER_FINE, 0.50, "uniform")
        snr_comp = snr_at_bler_crossing(bler_adj, 0.02)
        snr_ref  = 3.19  # 3GPP Qin reference
        assert snr_comp is not None
        disc = abs(snr_comp - snr_ref)
        assert disc < CORRESPONDENCE_THRESHOLD_DB, (
            f"Qin discrepancy at δ=0.50: {disc:.4f} dB — must be < {CORRESPONDENCE_THRESHOLD_DB} dB"
        )

    def test_bler_curve_slope_explains_robustness(self):
        """The BLER curve slope at Qout/Qin is steep enough to absorb bound error.

        The robustness of the correspondence follows from the steep slope of the
        BLER curve in the transition regime. A large fractional change in BLER
        produces only a small shift in the crossing SNR because dBLER/dSNR is large.
        Verify that the slope at the Qout crossing is steep (|dBLER/dSNR| > 0.3 per dB).
        """
        # Find slope of BLER curve near SNR=2.95 dB
        snr_target = 2.95
        idx = np.argmin(np.abs(SNR_FINE - snr_target))
        if idx > 0 and idx < len(SNR_FINE) - 1:
            slope = abs(BLER_FINE[idx+1] - BLER_FINE[idx-1]) / (SNR_FINE[idx+1] - SNR_FINE[idx-1])
        else:
            slope = abs(BLER_FINE[idx+1] - BLER_FINE[idx]) / abs(SNR_FINE[idx+1] - SNR_FINE[idx])
        assert slope > 0.3, (
            f"BLER slope at SNR=2.95 dB should be steep (|dBLER/dSNR| > 0.3), got {slope:.4f}. "
            "Steep slope is the mechanism for bound-robustness."
        )

    def test_monotone_shift_with_delta(self):
        """SNR crossing shifts monotonically as δ increases (larger bias = lower crossing SNR)."""
        snr_prev = snr_at_bler_crossing(BLER_FINE, 0.10)
        for delta in [0.05, 0.10, 0.20, 0.30, 0.50]:
            bler_adj = apply_bias(BLER_FINE, delta, "uniform")
            snr_curr = snr_at_bler_crossing(bler_adj, 0.10)
            assert snr_curr is not None and snr_prev is not None
            assert snr_curr <= snr_prev + 1e-6, (
                f"SNR crossing at Qout should decrease monotonically with δ: "
                f"δ={delta:.2f} gives {snr_curr:.4f} > previous {snr_prev:.4f}"
            )
            snr_prev = snr_curr
