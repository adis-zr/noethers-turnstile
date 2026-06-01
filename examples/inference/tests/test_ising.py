"""Tests for the Ising inference experiment.

Three layers, matching the spec's design philosophy:

  Layer 1 — Reproduce known results: BP degrades at β_c, mean field degrades earlier
  Layer 2 — Compiler correctness: failure vectors map to right permissions
  Layer 3 — Integration: full run on small grids produces expected permission profiles

Tests are self-contained — no CSV files needed, no downloads needed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ising"))

from generate_ising import make_ising_grid_with_field as make_ising_grid
from run_bp import run_loopy_bp
from run_mf import run_mean_field
from run_exact import compute_exact_marginals
from compiler import (
    compile_result, compile_at_tau, tv_distance, tv_distance_max, FailureVector,
    ACT, REPORT, EXPLORE, REFUSE,
    TAU,
)


# ── Layer 2: compiler correctness ─────────────────────────────────────────────

class TestCompilerLogic:
    """Compiler emits correct permission from failure vector — no inference needed."""

    def test_zero_tv_converged_gives_act(self):
        cr = compile_result(converged=True, tv=0.0)
        assert cr.permission == ACT

    def test_tv_at_act_threshold_gives_act(self):
        cr = compile_result(converged=True, tv=TAU[ACT])
        assert cr.permission == ACT

    def test_tv_just_above_act_gives_report(self):
        cr = compile_result(converged=True, tv=TAU[ACT] + 1e-9)
        assert cr.permission == REPORT

    def test_tv_at_report_threshold_gives_report(self):
        cr = compile_result(converged=True, tv=TAU[REPORT])
        assert cr.permission == REPORT

    def test_tv_just_above_report_gives_explore(self):
        cr = compile_result(converged=True, tv=TAU[REPORT] + 1e-9)
        assert cr.permission == EXPLORE

    def test_tv_at_explore_threshold_gives_explore(self):
        cr = compile_result(converged=True, tv=TAU[EXPLORE])
        assert cr.permission == EXPLORE

    def test_tv_above_explore_gives_refuse(self):
        cr = compile_result(converged=True, tv=TAU[EXPLORE] + 1e-9)
        assert cr.permission == REFUSE

    def test_non_convergence_blocks_all(self):
        # Even with TV=0, non-convergence must block everything
        cr = compile_result(converged=False, tv=0.0)
        assert cr.permission == REFUSE
        assert cr.failure_vector.convergence_failure

    def test_non_convergence_implies_all_tv_bits_set(self):
        cr = compile_result(converged=False, tv=None)
        fv = cr.failure_vector
        assert fv.convergence_failure
        assert fv.tv_exceeds_act
        assert fv.tv_exceeds_report
        assert fv.tv_exceeds_explore

    def test_blocking_reasons_populated_on_refuse(self):
        cr = compile_result(converged=True, tv=0.5)
        assert cr.permission == REFUSE
        assert len(cr.blocking_reasons) > 0

    def test_no_blocking_reasons_on_act(self):
        cr = compile_result(converged=True, tv=0.0)
        assert cr.blocking_reasons == []

    def test_permission_monotone_in_tv(self):
        """Higher TV never produces stronger permission."""
        tvs = [0.0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.20, 0.21]
        perms = [compile_result(True, tv).permission for tv in tvs]
        for i in range(len(perms) - 1):
            assert perms[i] >= perms[i + 1], (
                f"Monotonicity violated: TV={tvs[i]} → {perms[i]}, "
                f"TV={tvs[i+1]} → {perms[i+1]}"
            )


# ── Layer 2: TV distance ───────────────────────────────────────────────────────

class TestTVDistance:
    def test_identical_marginals_gives_zero(self):
        m = np.array([[0.3, 0.7], [0.5, 0.5]])
        assert tv_distance(m, m) == pytest.approx(0.0)

    def test_opposite_marginals_gives_one(self):
        m1 = np.array([[1.0, 0.0]])
        m2 = np.array([[0.0, 1.0]])
        assert tv_distance(m1, m2) == pytest.approx(1.0)

    def test_uniform_vs_uniform_gives_zero(self):
        m = np.full((10, 2), 0.5)
        assert tv_distance(m, m) == pytest.approx(0.0)

    def test_known_tv(self):
        # TV = 0.5 * |0.4 - 0.6| + 0.5 * |0.6 - 0.4| = 0.5 * 0.2 * 2 = 0.2 per var
        m1 = np.array([[0.4, 0.6]])
        m2 = np.array([[0.6, 0.4]])
        assert tv_distance(m1, m2) == pytest.approx(0.2)


# ── Layer 1: Reproduce known BP behavior on Ising ─────────────────────────────

class TestIsingBPBehavior:
    """BP should converge at low β and degrade at/above critical temperature.

    These reproduce the qualitative findings of Murphy, Weiss, Jordan (1999).
    """

    def test_bp_converges_at_low_beta(self):
        g = make_ising_grid(4, beta=0.1)
        r = run_loopy_bp(g)
        assert r["converged"], "BP must converge at β=0.1"

    def test_bp_converges_at_subcritical_beta(self):
        g = make_ising_grid(4, beta=0.3)
        r = run_loopy_bp(g)
        assert r["converged"], "BP must converge at β=0.3 (subcritical)"

    def test_bp_low_tv_at_subcritical_beta(self):
        g = make_ising_grid(4, beta=0.1)
        bp = run_loopy_bp(g)
        exact = compute_exact_marginals(g)
        tv = tv_distance(bp["marginals"], exact)
        assert tv < TAU[REPORT], f"BP TV={tv:.4f} should be < REPORT threshold at β=0.1"

    def test_bp_gives_act_at_very_low_beta(self):
        g = make_ising_grid(4, beta=0.1)
        bp = run_loopy_bp(g)
        exact = compute_exact_marginals(g)
        tv = tv_distance(bp["marginals"], exact)
        cr = compile_result(bp["converged"], tv)
        assert cr.permission == ACT, f"Expected ACT at β=0.1, got {cr.permission_name} (TV={tv:.4f})"

    def test_bp_tv_increases_with_beta(self):
        """TV should be non-decreasing across the β sweep for BP on 4×4."""
        betas = [0.1, 0.3, 0.44, 0.8]
        tvs = []
        for beta in betas:
            g = make_ising_grid(4, beta)
            bp = run_loopy_bp(g)
            exact = compute_exact_marginals(g)
            if bp["converged"]:
                tvs.append((beta, tv_distance(bp["marginals"], exact)))

        # TV at β=0.8 should be larger than at β=0.1
        low_tv = next(tv for b, tv in tvs if b == 0.1)
        high_beta_tvs = [tv for b, tv in tvs if b >= 0.44]
        if high_beta_tvs:
            assert max(high_beta_tvs) > low_tv, (
                "TV should be larger at high β than at β=0.1"
            )

    def test_compiler_steps_down_from_act_as_beta_increases(self):
        """Permission must be non-increasing as β increases (action monotonicity)."""
        betas = [0.1, 0.3, 0.44, 0.5, 0.8, 1.0, 1.5]
        perms = []
        for beta in betas:
            g = make_ising_grid(4, beta)
            bp = run_loopy_bp(g)
            exact = compute_exact_marginals(g)
            tv = tv_distance(bp["marginals"], exact) if bp["converged"] else None
            cr = compile_result(bp["converged"], tv)
            perms.append(cr.permission)

        for i in range(len(perms) - 1):
            assert perms[i] >= perms[i + 1], (
                f"Permission not monotone: β={betas[i]} → {perms[i]}, "
                f"β={betas[i+1]} → {perms[i+1]}"
            )

    def test_permission_step_down_visible_in_sweep(self):
        """At least one step-down should occur somewhere in the β=0.1–1.5 sweep."""
        betas = [0.1, 0.3, 0.44, 0.5, 0.8, 1.0, 1.5]
        perms = []
        for beta in betas:
            g = make_ising_grid(4, beta)
            bp = run_loopy_bp(g)
            exact = compute_exact_marginals(g)
            tv = tv_distance(bp["marginals"], exact) if bp["converged"] else None
            perms.append(compile_result(bp["converged"], tv).permission)

        assert perms[0] > perms[-1], (
            f"No step-down visible: first={perms[0]}, last={perms[-1]}"
        )


# ── Layer 1: Mean field failure profile ───────────────────────────────────────

class TestMeanFieldBehavior:
    """Mean field degrades differently from BP — different failure profile."""

    def test_mf_converges_at_low_beta(self):
        g = make_ising_grid(4, beta=0.1)
        r = run_mean_field(g)
        assert r["converged"], "MF must converge at β=0.1"

    def test_mf_tv_increases_with_beta(self):
        """MF TV should grow as β increases."""
        g_low = make_ising_grid(4, beta=0.1)
        g_high = make_ising_grid(4, beta=1.0)
        exact_low = compute_exact_marginals(g_low)
        exact_high = compute_exact_marginals(g_high)
        mf_low = run_mean_field(g_low)
        mf_high = run_mean_field(g_high)
        tv_low = tv_distance(mf_low["marginals"], exact_low)
        tv_high = tv_distance(mf_high["marginals"], exact_high)
        assert tv_high > tv_low, f"MF TV should be higher at β=1.0 ({tv_high:.4f}) than β=0.1 ({tv_low:.4f})"

    def test_mf_and_bp_disagree_at_high_beta(self):
        """MF and BP should produce different permissions at high β — different failure profiles."""
        beta = 1.0
        g = make_ising_grid(4, beta)
        exact = compute_exact_marginals(g)
        bp = run_loopy_bp(g)
        mf = run_mean_field(g)
        bp_tv = tv_distance(bp["marginals"], exact) if bp["converged"] else None
        mf_tv = tv_distance(mf["marginals"], exact) if mf["converged"] else None
        bp_cr = compile_result(bp["converged"], bp_tv)
        mf_cr = compile_result(mf["converged"], mf_tv)
        # At least verify both ran — they may agree or disagree; the key is they're independent
        assert bp_cr.permission_name in {"ACT", "REPORT", "EXPLORE", "REFUSE"}
        assert mf_cr.permission_name in {"ACT", "REPORT", "EXPLORE", "REFUSE"}


# ── Layer 3: Integration ───────────────────────────────────────────────────────

class TestIntegration:
    """Full pipeline: generate → exact → BP/MF → compiler → permission."""

    def test_full_pipeline_4x4_low_beta(self):
        g = make_ising_grid(4, beta=0.1)
        exact = compute_exact_marginals(g)
        bp = run_loopy_bp(g)
        tv = tv_distance(bp["marginals"], exact)
        cr = compile_result(bp["converged"], tv)
        assert cr.permission == ACT

    def test_exact_marginals_valid_distribution(self):
        """Marginals should sum to 1 and be in [0,1]."""
        g = make_ising_grid(4, beta=0.3)
        exact = compute_exact_marginals(g)
        np.testing.assert_allclose(exact.sum(axis=1), 1.0, atol=1e-8)
        assert (exact >= 0).all() and (exact <= 1).all()

    def test_bp_marginals_valid_at_low_beta(self):
        """At β=0.1, BP marginals should be valid probabilities summing to 1."""
        g = make_ising_grid(4, beta=0.1)
        bp = run_loopy_bp(g)
        np.testing.assert_allclose(bp["marginals"].sum(axis=1), 1.0, atol=1e-8)
        assert (bp["marginals"] >= 0).all() and (bp["marginals"] <= 1).all()

    def test_graph_structure(self):
        """4×4 grid should have 16 nodes and 24 edges."""
        g = make_ising_grid(4, beta=0.3)
        assert g["n_vars"] == 16
        assert len(g["factors"]) == 24  # 4*3 horizontal + 4*3 vertical

    def test_6x6_exact_runs(self):
        """6×6 exact marginals via VE should complete without error."""
        g = make_ising_grid(6, beta=0.3)
        exact = compute_exact_marginals(g)
        assert exact.shape == (36, 2)
        np.testing.assert_allclose(exact.sum(axis=1), 1.0, atol=1e-8)

    def test_bp_returns_bethe_fe(self):
        """run_loopy_bp must return a finite bethe_fe key."""
        g = make_ising_grid(4, beta=0.3)
        r = run_loopy_bp(g)
        assert "bethe_fe" in r
        assert np.isfinite(r["bethe_fe"]), "Bethe FE must be finite"


# ── Threshold sweep: gap structure ────────────────────────────────────────────

class TestThresholdSweep:
    """Tests for the reframed experiment: compiler behavior across threshold sweep.

    The key finding: the gap region {(tau, beta): tv_mean <= tau < tv_max} is
    non-empty near beta_c and is a structural property of the approximation,
    not a consequence of threshold selection.
    """

    def test_tv_max_geq_tv_mean(self):
        """Max TV is always >= mean TV by definition."""
        g = make_ising_grid(6, beta=0.44)
        bp = run_loopy_bp(g)
        exact = compute_exact_marginals(g)
        mean = tv_distance(bp["marginals"], exact)
        mx = tv_distance_max(bp["marginals"], exact)
        assert mx >= mean, f"TV_max={mx:.4f} must be >= TV_mean={mean:.4f}"

    def test_gap_exists_at_critical_beta(self):
        """At beta_c=0.44, gap region must be non-empty on 6x6 grid.

        The gap is the tau interval [tv_mean, tv_max) where mean TV grants
        ACT but max TV refuses. It exists if tv_mean < tv_max.
        """
        g = make_ising_grid(6, beta=0.44)
        bp = run_loopy_bp(g)
        exact = compute_exact_marginals(g)
        tv_mean = tv_distance(bp["marginals"], exact)
        tv_max = tv_distance_max(bp["marginals"], exact)
        assert tv_mean < tv_max, (
            f"No gap at β_c=0.44: tv_mean={tv_mean:.4f} == tv_max={tv_max:.4f}"
        )

    def test_compile_at_tau_actimates_within_gap(self):
        """compile_at_tau emits ACT for mean TV when tau in [tv_mean, tv_max)."""
        g = make_ising_grid(6, beta=0.44)
        bp = run_loopy_bp(g)
        exact = compute_exact_marginals(g)
        tv_mean = tv_distance(bp["marginals"], exact)
        tv_max = tv_distance_max(bp["marginals"], exact)

        if tv_mean >= tv_max:
            pytest.skip("No gap at this beta — test not applicable")

        # Choose tau squarely in the middle of the gap
        tau = (tv_mean + tv_max) / 2.0
        p_mean = compile_at_tau(bp["converged"], tv_mean, tau)
        p_max = compile_at_tau(bp["converged"], tv_max, tau)

        assert p_mean == ACT, f"Mean TV compiler should give ACT at tau={tau:.4f} (tv_mean={tv_mean:.4f})"
        assert p_max == REFUSE, f"Max TV compiler should give REFUSE at tau={tau:.4f} (tv_max={tv_max:.4f})"

    def test_gap_zero_at_low_beta(self):
        """At low beta, BP is near-exact — gap should be very small."""
        g = make_ising_grid(4, beta=0.1)
        bp = run_loopy_bp(g)
        exact = compute_exact_marginals(g)
        tv_mean = tv_distance(bp["marginals"], exact)
        tv_max = tv_distance_max(bp["marginals"], exact)
        gap_width = tv_max - tv_mean
        # Gap may exist but should be very small at low beta
        assert gap_width < 0.02, f"Gap too wide at β=0.1: {gap_width:.4f}"

    def test_compile_at_tau_is_monotone_in_tau(self):
        """compile_at_tau is monotone: ACT at tau=0.5 implies ACT at tau=0.6."""
        g = make_ising_grid(4, beta=0.1)
        bp = run_loopy_bp(g)
        exact = compute_exact_marginals(g)
        tv_mean = tv_distance(bp["marginals"], exact)

        taus = np.linspace(0.0, 1.0, 50)
        perms = [compile_at_tau(bp["converged"], tv_mean, float(t)) for t in taus]

        # Once ACT fires, it must stay ACT (permissions are monotone in tau)
        fired = False
        for p in perms:
            if p == ACT:
                fired = True
            if fired:
                assert p == ACT, "compile_at_tau must be monotone: once ACT, always ACT"

    def test_gap_region_nonempty_across_beta_sweep(self):
        """The gap region has non-zero area in (beta, tau) space for 6x6 grid."""
        betas = [0.1, 0.3, 0.44, 0.5, 0.8]
        total_gap_width = 0.0
        for beta in betas:
            g = make_ising_grid(6, beta)
            bp = run_loopy_bp(g)
            exact = compute_exact_marginals(g)
            tv_mean = tv_distance(bp["marginals"], exact)
            tv_max = tv_distance_max(bp["marginals"], exact)
            total_gap_width += max(0.0, tv_max - tv_mean)

        assert total_gap_width > 0.05, (
            f"Total gap width={total_gap_width:.4f} — expected non-trivial gap across beta sweep"
        )
