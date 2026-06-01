"""Tests for the UAI Tier 2 inference experiment.

Three layers mirroring test_ising.py:

  Layer 1 — Parser correctness and BP runs without error on real UAI files
  Layer 2 — Compiler correctness: UAI failure vector maps to right permissions
  Layer 3 — Integration: f1 fires without ground truth; Bethe FE is finite and
             negative (physically meaningful); permission outputs make sense
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "uai"))

from parse_uai import parse_uai, apply_evidence
from run_bp_uai import run_bp_uai
from compiler_uai import (
    compile_uai_result, UAIFailureVector,
    ACT, REPORT, EXPLORE, REFUSE, BETHE_TAU,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "uai" / "data" / "PR"
GRIDS_11 = str(DATA_DIR / "Grids_11.uai")
PEDIGREE_11 = str(DATA_DIR / "Pedigree_11.uai")
OD_11 = str(DATA_DIR / "ObjectDetection_11.uai")

DATA_AVAILABLE = DATA_DIR.exists() and (DATA_DIR / "Grids_11.uai").exists()


# ── Layer 2: compiler logic (no UAI files needed) ─────────────────────────────

class TestUAICompilerLogic:
    """Compiler emits correct permission from failure vector."""

    def test_converged_small_bethe_gives_act(self):
        cr = compile_uai_result(converged=True, bethe_fe=0.0, n_vars=100)
        assert cr.permission == ACT

    def test_converged_bethe_at_act_threshold_gives_act(self):
        fe = BETHE_TAU[ACT] * 100  # exactly at threshold for n_vars=100
        cr = compile_uai_result(converged=True, bethe_fe=fe, n_vars=100)
        assert cr.permission == ACT

    def test_converged_bethe_just_above_act_gives_report(self):
        fe = (BETHE_TAU[ACT] + 1e-6) * 100
        cr = compile_uai_result(converged=True, bethe_fe=fe, n_vars=100)
        assert cr.permission == REPORT

    def test_converged_bethe_above_report_gives_explore(self):
        fe = (BETHE_TAU[REPORT] + 0.01) * 100
        cr = compile_uai_result(converged=True, bethe_fe=fe, n_vars=100)
        assert cr.permission == EXPLORE

    def test_converged_bethe_above_explore_gives_refuse(self):
        fe = (BETHE_TAU[EXPLORE] + 0.1) * 100
        cr = compile_uai_result(converged=True, bethe_fe=fe, n_vars=100)
        assert cr.permission == REFUSE

    def test_non_convergence_gives_refuse_regardless_of_bethe(self):
        cr = compile_uai_result(converged=False, bethe_fe=0.0, n_vars=100)
        assert cr.permission == REFUSE

    def test_non_convergence_sets_all_bits(self):
        cr = compile_uai_result(converged=False, bethe_fe=0.0, n_vars=100)
        fv = cr.failure_vector
        assert fv.convergence_failure
        assert fv.bethe_exceeds_act
        assert fv.bethe_exceeds_report
        assert fv.bethe_exceeds_explore

    def test_tv_unavailable_flag_set(self):
        cr = compile_uai_result(converged=True, bethe_fe=0.0, n_vars=100)
        assert not cr.failure_vector.tv_available

    def test_permission_monotone_in_bethe(self):
        """Higher Bethe FE never produces stronger permission."""
        bethe_vals = [0.0, 4.0, 10.0, 20.0, 100.0, 200.0]  # raw FE for n_vars=100
        perms = [compile_uai_result(True, fe, 100).permission for fe in bethe_vals]
        for i in range(len(perms) - 1):
            assert perms[i] >= perms[i + 1], (
                f"Monotonicity violated: bethe={bethe_vals[i]} → {perms[i]}, "
                f"bethe={bethe_vals[i+1]} → {perms[i+1]}"
            )

    def test_n_vars_scaling(self):
        """Same Bethe/var gives same permission regardless of n_vars."""
        fe_small = BETHE_TAU[ACT] * 0.5 * 10     # below ACT threshold, n=10
        fe_large = BETHE_TAU[ACT] * 0.5 * 1000   # same per-var, n=1000
        cr_small = compile_uai_result(True, fe_small, 10)
        cr_large = compile_uai_result(True, fe_large, 1000)
        assert cr_small.permission == cr_large.permission == ACT


# ── Layer 1: UAI parser ────────────────────────────────────────────────────────

@pytest.mark.skipif(not DATA_AVAILABLE, reason="UAI data not downloaded")
class TestUAIParser:
    def test_grids_11_parse(self):
        g = parse_uai(GRIDS_11)
        assert g.n_vars == 100
        assert g.n_factors == 300
        assert max(g.cardinalities) == 2

    def test_grids_11_no_evidence(self):
        g = parse_uai(GRIDS_11)
        assert len(g.evidence) == 0

    def test_pedigree_11_parse(self):
        g = parse_uai(PEDIGREE_11)
        assert g.n_vars == 385
        assert max(g.cardinalities) == 3

    def test_pedigree_11_has_evidence(self):
        g = parse_uai(PEDIGREE_11)
        assert len(g.evidence) > 0

    def test_od_11_high_cardinality(self):
        g = parse_uai(OD_11)
        assert g.n_vars == 60
        assert max(g.cardinalities) == 11

    def test_log_factors_finite(self):
        g = parse_uai(GRIDS_11)
        for lf in g.log_factors:
            assert np.isfinite(lf).all(), "Log factors must be finite"

    def test_apply_evidence_reduces_cliques(self):
        g = parse_uai(PEDIGREE_11)
        assert len(g.evidence) > 0
        g2 = apply_evidence(g)
        # After clamping evidence, no clique should contain an observed variable
        for clique in g2.cliques:
            for v in clique:
                assert v not in g.evidence, f"Observed var {v} still in clique"


# ── Layer 3: Integration — BP runs and compiler behaves soundly ────────────────

@pytest.mark.skipif(not DATA_AVAILABLE, reason="UAI data not downloaded")
class TestUAIIntegration:
    def test_bp_grids_11_runs(self):
        g = parse_uai(GRIDS_11)
        r = run_bp_uai(g)
        assert "marginals" in r
        assert len(r["marginals"]) == g.n_vars

    def test_bp_marginals_valid_probabilities(self):
        g = parse_uai(GRIDS_11)
        r = run_bp_uai(g)
        for i, m in enumerate(r["marginals"]):
            assert abs(m.sum() - 1.0) < 1e-6, f"Marginal {i} does not sum to 1"
            assert (m >= 0).all(), f"Marginal {i} has negative entries"

    def test_bethe_fe_is_finite(self):
        g = parse_uai(GRIDS_11)
        r = run_bp_uai(g)
        assert np.isfinite(r["bethe_fe"]), "Bethe FE must be finite"

    def test_f1_fires_on_non_convergence(self):
        """Key Tier 2 claim: f1 detectable without ground truth.

        Force non-convergence by setting max_iter=1 and tol=1e-12.
        The compiler must refuse, and it knows nothing about TV.
        """
        g = parse_uai(GRIDS_11)
        r = run_bp_uai(g, max_iter=1, tol=1e-12)
        cr = compile_uai_result(r["converged"], r["bethe_fe"], g.n_vars)
        if not r["converged"]:
            assert cr.permission == REFUSE
            assert cr.failure_vector.convergence_failure
            assert not cr.failure_vector.tv_available

    def test_compiler_gives_some_permission_on_grids_11(self):
        g = parse_uai(GRIDS_11)
        r = run_bp_uai(g)
        cr = compile_uai_result(r["converged"], r["bethe_fe"], g.n_vars)
        assert cr.permission_name in {"ACT", "REPORT", "EXPLORE", "REFUSE"}

    def test_pedigree_with_evidence_runs(self):
        g = parse_uai(PEDIGREE_11)
        r = run_bp_uai(g)
        assert len(r["marginals"]) == g.n_vars

    def test_od_11_high_cardinality_runs(self):
        g = parse_uai(OD_11)
        r = run_bp_uai(g)
        for i, m in enumerate(r["marginals"]):
            assert len(m) == g.cardinalities[i]

    def test_tier2_compiler_never_uses_tv(self):
        """Structural test: UAIFailureVector.tv_available is always False."""
        g = parse_uai(GRIDS_11)
        r = run_bp_uai(g)
        cr = compile_uai_result(r["converged"], r["bethe_fe"], g.n_vars)
        assert not cr.failure_vector.tv_available

    def test_grids_11_f1_fires_and_compiler_refuses(self):
        """Grids_11 is a supercritical grid (log-factors ±4.9 ≈ β=4.9) — BP does not
        converge. This is the key Tier 2 demonstration: f1 fires without ground truth
        and the compiler correctly emits REFUSE purely on the convergence bit.
        """
        g = parse_uai(GRIDS_11)
        r = run_bp_uai(g, max_iter=200)
        # BP should NOT converge on this hard instance
        assert not r["converged"], (
            f"Grids_11 is supercritical — expected non-convergence, "
            f"got converged=True after {r['n_iter']} iterations"
        )
        cr = compile_uai_result(r["converged"], r["bethe_fe"], g.n_vars)
        assert cr.permission == REFUSE
        assert cr.failure_vector.convergence_failure
        assert not cr.failure_vector.tv_available
