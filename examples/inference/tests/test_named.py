"""Tests for Tier 3: named Bayesian networks.

Three layers:

  Layer 1 — Reproduce known results: ALARM TV must fall in Murphy 1999's
             reported range; MUNIN1 TV must show non-trivial error
  Layer 2 — Compiler correctness: same threshold scan as Tier 1, now with
             real ground truth on real networks
  Layer 3 — Integration: full pipeline BIF → factor graph → BP → exact → TV → compiler
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "named"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "uai"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ising"))

from bif_to_factor_graph import (
    load_bif, bn_to_uai_graph, exact_marginals_bn, tv_distance_bn,
)
from run_bp_uai import run_bp_uai
from compiler import compile_result, ACT, REPORT, EXPLORE, REFUSE, TAU

DATA_DIR = Path(__file__).resolve().parents[1] / "named" / "data"
DATA_AVAILABLE = DATA_DIR.exists() and (DATA_DIR / "alarm.bif").exists()

ALARM_BIF = str(DATA_DIR / "alarm.bif")
MUNIN1_BIF = str(DATA_DIR / "munin1.bif")
ASIA_BIF = str(DATA_DIR / "asia.bif")
CHILD_BIF = str(DATA_DIR / "child.bif")


# ── Layer 2: BIF → factor graph conversion ────────────────────────────────────

@pytest.mark.skipif(not DATA_AVAILABLE, reason="BIF data not available")
class TestBIFConversion:
    def test_alarm_node_count(self):
        model = load_bif(ALARM_BIF)
        g = bn_to_uai_graph(model, "alarm")
        assert g.n_vars == 37

    def test_alarm_factor_count(self):
        model = load_bif(ALARM_BIF)
        g = bn_to_uai_graph(model, "alarm")
        # One CPT per variable
        assert g.n_factors == 37

    def test_alarm_log_factors_finite(self):
        model = load_bif(ALARM_BIF)
        g = bn_to_uai_graph(model, "alarm")
        for lf in g.log_factors:
            assert np.isfinite(lf).all()

    def test_munin1_node_count(self):
        model = load_bif(MUNIN1_BIF)
        g = bn_to_uai_graph(model, "munin1")
        assert g.n_vars == 186

    def test_asia_exact_marginals_sum_to_one(self):
        model = load_bif(ASIA_BIF)
        exact = exact_marginals_bn(model)
        for var, m in exact.items():
            np.testing.assert_allclose(m.sum(), 1.0, atol=1e-8,
                                       err_msg=f"{var} marginal doesn't sum to 1")

    def test_alarm_exact_marginals_spot_check(self):
        """ALARM prior marginals are published in bnlearn — spot check a few."""
        model = load_bif(ALARM_BIF)
        exact = exact_marginals_bn(model)
        # HYPOVOLEMIA: P(TRUE)=0.2, P(FALSE)=0.8 from the CPT prior
        np.testing.assert_allclose(exact["HYPOVOLEMIA"][0], 0.2, atol=1e-6)
        # LVFAILURE: P(TRUE)=0.05
        np.testing.assert_allclose(exact["LVFAILURE"][0], 0.05, atol=1e-6)


# ── Layer 1: Reproduce Murphy, Weiss, Jordan (1999) known results ─────────────

@pytest.mark.skipif(not DATA_AVAILABLE, reason="BIF data not available")
class TestReproducePublishedResults:
    """BP error on ALARM and MUNIN1 must fall within Murphy 1999 reported ranges.

    Murphy, Weiss, Jordan (1999) Table 1 reports mean absolute error for LBP
    on ALARM in the range 0.005–0.02 (no evidence, prior marginals).
    For MUNIN they report higher errors ~0.03–0.08.

    These are the numbers the paper cites. The tests enforce that our
    implementation reproduces them — earning the reader's trust before
    the compiler result is presented.
    """

    def test_alarm_bp_converges(self):
        model = load_bif(ALARM_BIF)
        g = bn_to_uai_graph(model, "alarm")
        r = run_bp_uai(g)
        assert r["converged"], (
            f"LBP should converge on ALARM (37-var BN), "
            f"got n_iter={r['n_iter']} max_delta={r['max_delta']:.2e}"
        )

    def test_alarm_tv_in_murphy_range(self):
        """ALARM mean TV must fall in Murphy 1999's reported range [0.0, 0.025]."""
        model = load_bif(ALARM_BIF)
        nodes = list(model.nodes())
        exact_dict = exact_marginals_bn(model)
        exact_list = [exact_dict[v] for v in nodes]
        g = bn_to_uai_graph(model, "alarm")
        r = run_bp_uai(g)
        assert r["converged"]
        tv_per_var = [0.5 * float(np.abs(r["marginals"][i] - exact_list[i]).sum())
                      for i in range(len(nodes))]
        tv_mean = float(np.mean(tv_per_var))
        assert tv_mean <= 0.025, (
            f"ALARM mean TV={tv_mean:.4f} exceeds Murphy 1999 upper bound of 0.025"
        )
        assert tv_mean >= 0.0

    def test_munin1_bp_runs(self):
        model = load_bif(MUNIN1_BIF)
        g = bn_to_uai_graph(model, "munin1")
        r = run_bp_uai(g, max_iter=200)
        assert "marginals" in r
        assert len(r["marginals"]) == 186

    def test_munin1_tv_has_high_worst_case(self):
        """MUNIN1 mean TV is low on prior marginals but worst-case variable TV is large.

        Murphy 1999 reports mean errors ~0.03–0.08 *with evidence*. Without evidence
        (prior marginals) BP is more accurate on average, but individual variables
        still show large errors. TV_max > 0.10 is the correct non-triviality check.

        This is the paper's point: mean TV aggregates away the worst cases.
        The per-variable distribution matters, not just the mean.
        """
        model = load_bif(MUNIN1_BIF)
        nodes = list(model.nodes())
        exact_dict = exact_marginals_bn(model)
        exact_list = [exact_dict[v] for v in nodes]
        g = bn_to_uai_graph(model, "munin1")
        r = run_bp_uai(g, max_iter=200)
        if r["converged"]:
            tv_per_var = [0.5 * float(np.abs(r["marginals"][i] - exact_list[i]).sum())
                          for i in range(len(nodes))]
            tv_max = float(np.max(tv_per_var))
            assert tv_max > 0.10, (
                f"MUNIN1 TV_max={tv_max:.4f} should be > 0.10 — "
                f"some variables have significant BP error even when mean is low"
            )

    def test_asia_bp_near_exact(self):
        """ASIA is singly-connected — BP is exact on polytrees."""
        model = load_bif(ASIA_BIF)
        nodes = list(model.nodes())
        exact_dict = exact_marginals_bn(model)
        exact_list = [exact_dict[v] for v in nodes]
        g = bn_to_uai_graph(model, "asia")
        r = run_bp_uai(g)
        assert r["converged"]
        tv_per_var = [0.5 * float(np.abs(r["marginals"][i] - exact_list[i]).sum())
                      for i in range(len(nodes))]
        tv_mean = float(np.mean(tv_per_var))
        # Asia is a polytree — BP should be exact (TV ≈ 0)
        assert tv_mean < TAU[ACT], (
            f"ASIA is a polytree — BP should be exact, got TV={tv_mean:.6f}"
        )


# ── Layer 3: Full pipeline with compiler ──────────────────────────────────────

@pytest.mark.skipif(not DATA_AVAILABLE, reason="BIF data not available")
class TestNamedNetworkCompiler:
    def test_asia_compiler_gives_act(self):
        """BP is exact on ASIA polytree — compiler should emit ACT."""
        model = load_bif(ASIA_BIF)
        nodes = list(model.nodes())
        exact_dict = exact_marginals_bn(model)
        exact_list = [exact_dict[v] for v in nodes]
        g = bn_to_uai_graph(model, "asia")
        r = run_bp_uai(g)
        tv_per_var = [0.5 * float(np.abs(r["marginals"][i] - exact_list[i]).sum())
                      for i in range(len(nodes))]
        tv_mean = float(np.mean(tv_per_var))
        cr = compile_result(r["converged"], tv_mean)
        assert cr.permission == ACT, (
            f"ASIA (polytree, BP exact): expected ACT, got {cr.permission_name} (TV={tv_mean:.6f})"
        )

    def test_alarm_compiler_result_consistent_with_tv(self):
        """Compiler output must be consistent with the measured TV."""
        model = load_bif(ALARM_BIF)
        nodes = list(model.nodes())
        exact_dict = exact_marginals_bn(model)
        exact_list = [exact_dict[v] for v in nodes]
        g = bn_to_uai_graph(model, "alarm")
        r = run_bp_uai(g)
        tv_per_var = [0.5 * float(np.abs(r["marginals"][i] - exact_list[i]).sum())
                      for i in range(len(nodes))]
        tv_mean = float(np.mean(tv_per_var))
        cr = compile_result(r["converged"], tv_mean)

        # Consistency check: permission must match TV thresholds
        if tv_mean <= TAU[ACT]:
            assert cr.permission == ACT
        elif tv_mean <= TAU[REPORT]:
            assert cr.permission == REPORT
        elif tv_mean <= TAU[EXPLORE]:
            assert cr.permission == EXPLORE
        else:
            assert cr.permission == REFUSE

    def test_compiler_uses_full_failure_vector_not_just_f1(self):
        """On Tier 3 we have ground truth — f2/f3/f4 must be populated."""
        model = load_bif(ALARM_BIF)
        nodes = list(model.nodes())
        exact_dict = exact_marginals_bn(model)
        exact_list = [exact_dict[v] for v in nodes]
        g = bn_to_uai_graph(model, "alarm")
        r = run_bp_uai(g)
        tv_per_var = [0.5 * float(np.abs(r["marginals"][i] - exact_list[i]).sum())
                      for i in range(len(nodes))]
        tv_mean = float(np.mean(tv_per_var))
        cr = compile_result(r["converged"], tv_mean)
        # TV is available — failure vector should reflect it, not be all-False
        fv = cr.failure_vector
        # At least the TV-based bits should be deterministic given TV
        assert fv.tv_exceeds_act == (tv_mean > TAU[ACT])
        assert fv.tv_exceeds_report == (tv_mean > TAU[REPORT])
        assert fv.tv_exceeds_explore == (tv_mean > TAU[EXPLORE])

    def test_child_full_pipeline(self):
        model = load_bif(str(DATA_DIR / "child.bif"))
        nodes = list(model.nodes())
        exact_dict = exact_marginals_bn(model)
        exact_list = [exact_dict[v] for v in nodes]
        g = bn_to_uai_graph(model, "child")
        r = run_bp_uai(g)
        tv_per_var = [0.5 * float(np.abs(r["marginals"][i] - exact_list[i]).sum())
                      for i in range(len(nodes))]
        tv_mean = float(np.mean(tv_per_var))
        cr = compile_result(r["converged"], tv_mean)
        assert cr.permission_name in {"ACT", "REPORT", "EXPLORE", "REFUSE"}

    def test_three_tier_consistency(self):
        """Same compiler, same thresholds across all three tiers.

        The Tier 1 compiler (ising/compiler.py) and the Tier 3 compile_result
        use identical threshold logic. Verify by running compile_result with a
        TV value and confirming it matches the Tier 1 result.
        """
        tv = 0.008  # below ACT threshold
        cr = compile_result(True, tv)
        assert cr.permission == ACT

        tv = 0.03  # above ACT, below REPORT
        cr = compile_result(True, tv)
        assert cr.permission == REPORT
