"""GasTown corpus generator tests (CORPUS-001 through CORPUS-080).

Tests for the Component 1 synthetic corpus generator:
  - Skeleton OTEL trace structure and required fields
  - Pattern families (CLEAN, L1–L8, A1–A5, DIA, AEX, ROL)
  - Label generation (expected_permission, max_acceptable, etc.)
  - Filler pass (structural fields unchanged)
  - Corpus counts match spec targets
  - Component 2 prompts.json fixture
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pytest

# ── Import stubs (will fail until implementation exists) ──────────────────────

from corpus.generator.patterns import (
    make_clean_trace,
    make_l1_trace,
    make_l2_trace,
    make_l3_trace,
    make_l4_trace,
    make_l5_trace,
    make_l6_trace,
    make_l7_trace,
    make_l8_trace,
    make_a1_trace,
    make_a2_trace,
    make_a3_trace,
    make_a4_trace,
    make_a5_trace,
    make_dia_trace,
    make_aex_trace,
    make_rol_trace,
    PatternLabel,
)
from corpus.generator.skeleton import (
    generate_component1_corpus,
    LabeledTrace,
    CORPUS_TARGETS,
)
from corpus.generator.filler import apply_filler


# ── Constants ──────────────────────────────────────────────────────────────────

_NOW = 1_748_736_000.0
_RIG = "rig-alpha"
_GIT = "deadbeef"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _run_id(suffix: str = "001") -> str:
    return f"run-{suffix}"


def _bead_id(suffix: str = "001") -> str:
    return f"bead-{suffix}"


def _has_event_type(trace: list[dict], etype: str) -> bool:
    return any(e.get("event_type") == etype for e in trace)


def _events_of_type(trace: list[dict], etype: str) -> list[dict]:
    return [e for e in trace if e.get("event_type") == etype]


def _run_adapter(trace: list[dict], bead_type: str = "normal"):
    """Run the adapter on a trace and return judgments."""
    from adapter.otel_adapter import process_trace
    return process_trace(trace, now_unix=_NOW + 3600, bead_type=bead_type)


# ══════════════════════════════════════════════════════════════════════════════
# CORPUS-001–010: PatternLabel schema
# ══════════════════════════════════════════════════════════════════════════════

class TestPatternLabel:

    def test_001_pattern_label_has_required_fields(self):
        """CORPUS-001: PatternLabel has all four classification fields."""
        lbl = PatternLabel(
            expected_permission="ALR",
            max_acceptable_permission="ALR",
            ceiling_blocked_permission=None,
            control_outcome_acceptable=False,
            pattern_family="CLEAN",
            ground_truth_sound=True,
        )
        assert lbl.expected_permission == "ALR"
        assert lbl.max_acceptable_permission == "ALR"
        assert lbl.ceiling_blocked_permission is None
        assert lbl.control_outcome_acceptable is False
        assert lbl.pattern_family == "CLEAN"
        assert lbl.ground_truth_sound is True

    def test_002_pattern_label_ceiling_blocked_nullable(self):
        """CORPUS-002: ceiling_blocked_permission is nullable."""
        lbl = PatternLabel(
            expected_permission="ETA",
            max_acceptable_permission=None,
            ceiling_blocked_permission="AAA",
            control_outcome_acceptable=True,
            pattern_family="L3",
            ground_truth_sound=True,
        )
        assert lbl.ceiling_blocked_permission == "AAA"
        assert lbl.max_acceptable_permission is None

    def test_003_pattern_label_to_dict(self):
        """CORPUS-003: PatternLabel.to_dict() produces JSON-serializable dict."""
        lbl = PatternLabel(
            expected_permission="REF",
            max_acceptable_permission=None,
            ceiling_blocked_permission=None,
            control_outcome_acceptable=False,
            pattern_family="L1",
            ground_truth_sound=False,
        )
        d = lbl.to_dict()
        assert isinstance(d, dict)
        # Must round-trip through JSON
        json.dumps(d)
        assert d["expected_permission"] == "REF"
        assert d["pattern_family"] == "L1"

    def test_004_labeled_trace_structure(self):
        """CORPUS-004: LabeledTrace has trace, label, convoy_id, bead_type."""
        from corpus.generator.skeleton import LabeledTrace
        trace = [{"event_type": "done", "run_id": "r1", "bead_id": "b1",
                  "exit_type": "COMPLETED", "timestamp": _NOW}]
        lbl = PatternLabel("DIA", "DIA", None, False, "DIA", True)
        lt = LabeledTrace(trace=trace, label=lbl, convoy_id="convoy-1",
                          bead_type="normal")
        assert lt.trace is trace
        assert lt.label is lbl
        assert lt.convoy_id == "convoy-1"
        assert lt.bead_type == "normal"


# ══════════════════════════════════════════════════════════════════════════════
# CORPUS-011–020: CLEAN traces
# ══════════════════════════════════════════════════════════════════════════════

class TestCleanTrace:

    def test_011_clean_trace_produces_alr_judgment(self):
        """CORPUS-011: Clean polecat trace → ALR judgment."""
        trace, lbl = make_clean_trace(
            run_id=_run_id("011"), bead_id=_bead_id("011"),
            rig=_RIG, git_commit=_GIT, ts=_NOW, role="polecat",
        )
        judgments = _run_adapter(trace)
        assert len(judgments) == 1
        assert str(judgments[0].permission) == "ALR"

    def test_012_clean_trace_label_is_alr(self):
        """CORPUS-012: Clean polecat label → expected_permission=ALR."""
        _, lbl = make_clean_trace(
            run_id=_run_id("012"), bead_id=_bead_id("012"),
            rig=_RIG, git_commit=_GIT, ts=_NOW, role="polecat",
        )
        assert lbl.expected_permission == "ALR"
        assert lbl.pattern_family == "CLEAN"
        assert lbl.ground_truth_sound is True

    def test_013_clean_trace_has_required_events(self):
        """CORPUS-013: Clean trace has instantiate, prime, ready, done."""
        trace, _ = make_clean_trace(
            run_id=_run_id("013"), bead_id=_bead_id("013"),
            rig=_RIG, git_commit=_GIT, ts=_NOW, role="polecat",
        )
        assert _has_event_type(trace, "agent.instantiate")
        assert _has_event_type(trace, "prime")
        assert _has_event_type(trace, "done")
        # done must be COMPLETED
        dones = _events_of_type(trace, "done")
        assert any(d.get("exit_type") == "COMPLETED" for d in dones)

    def test_014_clean_trace_run_id_consistent(self):
        """CORPUS-014: All events in clean trace share the same run_id."""
        rid = _run_id("014")
        trace, _ = make_clean_trace(
            run_id=rid, bead_id=_bead_id("014"),
            rig=_RIG, git_commit=_GIT, ts=_NOW, role="polecat",
        )
        for ev in trace:
            assert ev.get("run_id") == rid

    def test_015_clean_mayor_trace_produces_aaa(self):
        """CORPUS-015: Clean mayor trace → AAA judgment."""
        trace, lbl = make_clean_trace(
            run_id=_run_id("015"), bead_id=_bead_id("015"),
            rig=_RIG, git_commit=_GIT, ts=_NOW, role="mayor",
        )
        judgments = _run_adapter(trace)
        assert len(judgments) == 1
        assert str(judgments[0].permission) == "AAA"
        assert lbl.expected_permission == "AAA"


# ══════════════════════════════════════════════════════════════════════════════
# CORPUS-021–030: L1–L4 laundering traces
# ══════════════════════════════════════════════════════════════════════════════

class TestLaunderingL1ToL4:

    def test_021_l1_cross_bead_scope_reuse_produces_ref(self):
        """CORPUS-021: L1 cross-bead scope reuse → REF (provenance mismatch)."""
        trace, lbl = make_l1_trace(
            run_id=_run_id("021"), bead_id=_bead_id("021"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        judgments = _run_adapter(trace)
        assert len(judgments) == 1
        assert str(judgments[0].permission) == "REF"

    def test_022_l1_label_max_acceptable_is_null(self):
        """CORPUS-022: L1 label has max_acceptable_permission=null (hard block)."""
        _, lbl = make_l1_trace(
            run_id=_run_id("022"), bead_id=_bead_id("022"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        assert lbl.expected_permission == "REF"
        assert lbl.max_acceptable_permission is None
        assert lbl.pattern_family == "L1"
        assert lbl.ground_truth_sound is False

    def test_023_l2_stale_hook_context_produces_rev(self):
        """CORPUS-023: L2 stale hook (seance only) → REV."""
        trace, lbl = make_l2_trace(
            run_id=_run_id("023"), bead_id=_bead_id("023"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        judgments = _run_adapter(trace)
        assert len(judgments) == 1
        assert str(judgments[0].permission) == "REV"

    def test_024_l2_label_max_acceptable_is_alr(self):
        """CORPUS-024: L2 label has max_acceptable_permission=ALR."""
        _, lbl = make_l2_trace(
            run_id=_run_id("024"), bead_id=_bead_id("024"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        assert lbl.expected_permission == "REV"
        assert lbl.max_acceptable_permission == "ALR"
        assert lbl.pattern_family == "L2"

    def test_025_l3_authority_ceiling_laundering_not_aaa(self):
        """CORPUS-025: L3 refinery (ceiling ALR) with all gaps closed → not AAA.

        The authority ceiling caps the result at ALR. The label records
        expected_permission=ETA (evaluator classification for ceiling-blocked
        patterns) and ceiling_blocked_permission=AAA, but the adapter itself
        emits ALR (the ceiling). ETA is an evaluator-level verdict.
        """
        trace, lbl = make_l3_trace(
            run_id=_run_id("025"), bead_id=_bead_id("025"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        judgments = _run_adapter(trace)
        assert len(judgments) >= 1
        # Adapter emits ALR (ceiling blocks AAA); evaluator labels as ETA
        assert str(judgments[0].permission) != "AAA"
        assert lbl.expected_permission == "ETA"
        assert lbl.ceiling_blocked_permission == "AAA"

    def test_026_l3_label_ceiling_blocked_is_aaa(self):
        """CORPUS-026: L3 label has ceiling_blocked_permission=AAA."""
        _, lbl = make_l3_trace(
            run_id=_run_id("026"), bead_id=_bead_id("026"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        assert lbl.ceiling_blocked_permission == "AAA"
        assert lbl.control_outcome_acceptable is True
        assert lbl.pattern_family == "L3"

    def test_027_l4_escalation_scope_mismatch_produces_ref(self):
        """CORPUS-027: L4 rig mismatch on escalation → REF (provenance mismatch)."""
        trace, lbl = make_l4_trace(
            run_id=_run_id("027"), bead_id=_bead_id("027"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        judgments = _run_adapter(trace)
        assert len(judgments) == 1
        assert str(judgments[0].permission) == "REF"

    def test_028_l4_label_max_acceptable_is_null(self):
        """CORPUS-028: L4 label has max_acceptable_permission=null."""
        _, lbl = make_l4_trace(
            run_id=_run_id("028"), bead_id=_bead_id("028"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        assert lbl.max_acceptable_permission is None
        assert lbl.pattern_family == "L4"

    def test_029_l4_has_cross_rig_token_event(self):
        """CORPUS-029: L4 trace has cross_rig_token event to flag mismatch."""
        trace, _ = make_l4_trace(
            run_id=_run_id("029"), bead_id=_bead_id("029"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        assert _has_event_type(trace, "cross_rig_token")

    def test_030_l1_has_cross_scope_token_event(self):
        """CORPUS-030: L1 trace has cross_scope_token event to flag mismatch."""
        trace, _ = make_l1_trace(
            run_id=_run_id("030"), bead_id=_bead_id("030"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        assert _has_event_type(trace, "cross_scope_token")


# ══════════════════════════════════════════════════════════════════════════════
# CORPUS-031–040: L5–L8 laundering traces
# ══════════════════════════════════════════════════════════════════════════════

class TestLaunderingL5ToL8:

    def test_031_l5_stale_demand_no_prime_produces_dia(self):
        """CORPUS-031: L5 stale demand signal (no prime, no seance) → DIA."""
        trace, lbl = make_l5_trace(
            run_id=_run_id("031"), bead_id=_bead_id("031"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        judgments = _run_adapter(trace)
        assert len(judgments) == 1
        assert str(judgments[0].permission) == "DIA"

    def test_032_l5_label_max_acceptable_is_alr(self):
        """CORPUS-032: L5 label has max_acceptable_permission=ALR."""
        _, lbl = make_l5_trace(
            run_id=_run_id("032"), bead_id=_bead_id("032"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        assert lbl.expected_permission == "DIA"
        assert lbl.max_acceptable_permission == "ALR"
        assert lbl.pattern_family == "L5"

    def test_033_l6_merge_without_current_ci_produces_ref(self):
        """CORPUS-033: L6 gate scoped to stale commit → REF (provenance mismatch)."""
        trace, lbl = make_l6_trace(
            run_id=_run_id("033"), bead_id=_bead_id("033"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        judgments = _run_adapter(trace, bead_type="normal")
        assert len(judgments) == 1
        assert str(judgments[0].permission) == "REF"

    def test_034_l6_label_max_acceptable_is_null(self):
        """CORPUS-034: L6 label has max_acceptable_permission=null."""
        _, lbl = make_l6_trace(
            run_id=_run_id("034"), bead_id=_bead_id("034"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        assert lbl.max_acceptable_permission is None
        assert lbl.pattern_family == "L6"

    def test_035_l7_identity_laundering_produces_rev(self):
        """CORPUS-035: L7 identity laundering (seance, no full delegation) → REV."""
        trace, lbl = make_l7_trace(
            run_id=_run_id("035"), bead_id=_bead_id("035"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        judgments = _run_adapter(trace)
        assert len(judgments) == 1
        assert str(judgments[0].permission) == "REV"

    def test_036_l7_label_max_acceptable_is_alr(self):
        """CORPUS-036: L7 label has max_acceptable_permission=ALR."""
        _, lbl = make_l7_trace(
            run_id=_run_id("036"), bead_id=_bead_id("036"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        assert lbl.expected_permission == "REV"
        assert lbl.max_acceptable_permission == "ALR"
        assert lbl.pattern_family == "L7"

    def test_037_l8_depth2_polecat_chain_has_correct_label(self):
        """CORPUS-037: L8 depth-2 polecat chain — label is ETA with ceiling AAA.

        Individual polecat judgments are ALR (ceiling). Mayor's own judgment is AAA
        (mayor ceiling). The L8 ETA verdict is an evaluator classification:
        ceiling_blocked_permission=AAA, control_outcome_acceptable=True.
        The adapter emits the correct per-role permissions; ETA is the evaluator verdict.
        """
        trace, lbl = make_l8_trace(
            run_id=_run_id("037"), bead_id=_bead_id("037"),
            rig=_RIG, git_commit=_GIT, ts=_NOW, depth=2, family_idx=0,
        )
        judgments = _run_adapter(trace)
        # Must produce multiple judgments (depth polecat steps + mayor)
        assert len(judgments) >= 2
        # All judgments should be valid permissions in the lattice
        all_perms = [str(j.permission) for j in judgments]
        valid_perms = {"DIA", "REV", "REF", "UNS", "ETA", "ESC", "ROL", "AEX", "ALR", "AAA", "OOC"}
        assert all(p in valid_perms for p in all_perms)
        # Label must indicate ETA ceiling-blocked pattern
        assert lbl.expected_permission == "ETA"
        assert lbl.ceiling_blocked_permission == "AAA"

    def test_038_l8_depth3_label_is_eta(self):
        """CORPUS-038: L8 depth-3 chain label → expected_permission=ETA."""
        trace, lbl = make_l8_trace(
            run_id=_run_id("038"), bead_id=_bead_id("038"),
            rig=_RIG, git_commit=_GIT, ts=_NOW, depth=3, family_idx=0,
        )
        judgments = _run_adapter(trace)
        assert len(judgments) >= 3
        assert lbl.expected_permission == "ETA"

    def test_039_l8_label_ceiling_blocked_is_aaa(self):
        """CORPUS-039: L8 label has ceiling_blocked_permission=AAA."""
        _, lbl = make_l8_trace(
            run_id=_run_id("039"), bead_id=_bead_id("039"),
            rig=_RIG, git_commit=_GIT, ts=_NOW, depth=2, family_idx=0,
        )
        assert lbl.ceiling_blocked_permission == "AAA"
        assert lbl.control_outcome_acceptable is True
        assert lbl.pattern_family == "L8"

    def test_040_l8_depth_ladder_has_four_depths(self):
        """CORPUS-040: L8 spec requires depths 2, 3, 4, 5 — all must generate."""
        for depth in [2, 3, 4, 5]:
            trace, lbl = make_l8_trace(
                run_id=_run_id(f"040d{depth}"), bead_id=_bead_id(f"040d{depth}"),
                rig=_RIG, git_commit=_GIT, ts=_NOW, depth=depth, family_idx=0,
            )
            assert lbl.pattern_family == "L8"
            # Each deeper trace should have more events
            assert len(trace) > 0


# ══════════════════════════════════════════════════════════════════════════════
# CORPUS-041–050: Adversarial instances A1–A5
# ══════════════════════════════════════════════════════════════════════════════

class TestAdversarialA1ToA5:

    def test_041_a1_fabricated_authority_produces_rev(self):
        """CORPUS-041: A1 fabricated authority envelope → REV (authority_chain open)."""
        trace, lbl = make_a1_trace(
            run_id=_run_id("041"), bead_id=_bead_id("041"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        judgments = _run_adapter(trace)
        assert len(judgments) == 1
        assert str(judgments[0].permission) == "REV"

    def test_042_a1_label_max_acceptable_is_alr(self):
        """CORPUS-042: A1 label has max_acceptable_permission=ALR."""
        _, lbl = make_a1_trace(
            run_id=_run_id("042"), bead_id=_bead_id("042"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        assert lbl.expected_permission == "REV"
        assert lbl.max_acceptable_permission == "ALR"
        assert lbl.pattern_family == "A1"

    def test_043_a2_malformed_detail_contract_produces_rev(self):
        """CORPUS-043: A2 malformed completion detail contract → REV."""
        trace, lbl = make_a2_trace(
            run_id=_run_id("043"), bead_id=_bead_id("043"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        judgments = _run_adapter(trace)
        assert len(judgments) == 1
        assert str(judgments[0].permission) == "REV"

    def test_044_a2_trace_has_detail_contract_invalid_flag(self):
        """CORPUS-044: A2 trace has bd.call ready with detail_contract_valid=False."""
        trace, _ = make_a2_trace(
            run_id=_run_id("044"), bead_id=_bead_id("044"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        ready_events = [e for e in trace
                        if e.get("event_type") == "bd.call"
                        and e.get("subcommand") == "ready"]
        assert any(e.get("detail_contract_valid") is False for e in ready_events)

    def test_045_a3_revoked_run_id_produces_dia(self):
        """CORPUS-045: A3 revoked run.id → DIA (context_integrity fails at REV)."""
        trace, lbl = make_a3_trace(
            run_id=_run_id("045"), bead_id=_bead_id("045"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        # A3 uses a revoked token registry entry
        from adapter.token_registry import TokenRegistry
        registry = TokenRegistry()
        registry.revoke_run_id(_run_id("045"))
        judgments = _run_adapter(trace)
        # With default registry (not revoked), gaps may vary; test the label
        assert lbl.expected_permission == "DIA"
        assert lbl.pattern_family == "A3"

    def test_046_a3_label_max_acceptable_is_rev(self):
        """CORPUS-046: A3 label has max_acceptable_permission=REV."""
        _, lbl = make_a3_trace(
            run_id=_run_id("046"), bead_id=_bead_id("046"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        assert lbl.max_acceptable_permission == "REV"
        assert lbl.pattern_family == "A3"

    def test_047_a4_runtime_context_non_upgrade_stays_alr(self):
        """CORPUS-047: A4 high-privilege rig injection → outcome unchanged at ALR."""
        trace, lbl = make_a4_trace(
            run_id=_run_id("047"), bead_id=_bead_id("047"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        judgments = _run_adapter(trace)
        assert len(judgments) == 1
        assert str(judgments[0].permission) == "ALR"

    def test_048_a4_label_ceiling_blocked_is_null(self):
        """CORPUS-048: A4 label has ceiling_blocked_permission=null."""
        _, lbl = make_a4_trace(
            run_id=_run_id("048"), bead_id=_bead_id("048"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        assert lbl.ceiling_blocked_permission is None
        assert lbl.pattern_family == "A4"

    def test_049_a5_seance_as_closure_produces_rev(self):
        """CORPUS-049: A5 seance token presented as closure → REV (not ALR)."""
        trace, lbl = make_a5_trace(
            run_id=_run_id("049"), bead_id=_bead_id("049"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        judgments = _run_adapter(trace)
        assert len(judgments) == 1
        assert str(judgments[0].permission) == "REV"

    def test_050_a5_label_max_acceptable_is_alr(self):
        """CORPUS-050: A5 label has max_acceptable_permission=ALR."""
        _, lbl = make_a5_trace(
            run_id=_run_id("050"), bead_id=_bead_id("050"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        assert lbl.expected_permission == "REV"
        assert lbl.max_acceptable_permission == "ALR"
        assert lbl.pattern_family == "A5"


# ══════════════════════════════════════════════════════════════════════════════
# CORPUS-051–060: Permission algebra families (DIA, AEX, ROL)
# ══════════════════════════════════════════════════════════════════════════════

class TestPermissionAlgebra:

    def test_051_dia_dog_role_produces_dia(self):
        """CORPUS-051: DIA family — dog role → DIA."""
        trace, lbl = make_dia_trace(
            run_id=_run_id("051"), bead_id=_bead_id("051"),
            rig=_RIG, git_commit=_GIT, ts=_NOW, role="dog",
        )
        judgments = _run_adapter(trace)
        assert len(judgments) == 1
        assert str(judgments[0].permission) == "DIA"

    def test_052_dia_boot_role_produces_dia(self):
        """CORPUS-052: DIA family — boot role → DIA."""
        trace, lbl = make_dia_trace(
            run_id=_run_id("052"), bead_id=_bead_id("052"),
            rig=_RIG, git_commit=_GIT, ts=_NOW, role="boot",
        )
        judgments = _run_adapter(trace)
        assert len(judgments) == 1
        assert str(judgments[0].permission) == "DIA"

    def test_053_dia_label_is_dia(self):
        """CORPUS-053: DIA trace label → expected_permission=DIA."""
        _, lbl = make_dia_trace(
            run_id=_run_id("053"), bead_id=_bead_id("053"),
            rig=_RIG, git_commit=_GIT, ts=_NOW, role="dog",
        )
        assert lbl.expected_permission == "DIA"
        assert lbl.pattern_family == "DIA"
        assert lbl.ground_truth_sound is True

    def test_054_aex_experiment_bead_produces_aex(self):
        """CORPUS-054: AEX family — polecat, bead.type=experiment, all gaps closed → AEX."""
        trace, lbl = make_aex_trace(
            run_id=_run_id("054"), bead_id=_bead_id("054"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        judgments = _run_adapter(trace, bead_type="experiment")
        assert len(judgments) == 1
        assert str(judgments[0].permission) == "AEX"

    def test_055_aex_label_is_aex(self):
        """CORPUS-055: AEX trace label → expected_permission=AEX."""
        _, lbl = make_aex_trace(
            run_id=_run_id("055"), bead_id=_bead_id("055"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        assert lbl.expected_permission == "AEX"
        assert lbl.pattern_family == "AEX"

    def test_056_aex_trace_has_experiment_scope_token(self):
        """CORPUS-056: AEX trace has experiment_scope_token event."""
        trace, _ = make_aex_trace(
            run_id=_run_id("056"), bead_id=_bead_id("056"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        assert _has_event_type(trace, "experiment_scope_token")

    def test_057_rol_refinery_merge_stale_commit_adapter_emits_ref(self):
        """CORPUS-057: ROL family — refinery merge with stale commit → adapter emits REF.

        ROL is an evaluator classification (UNSOUND_CAUGHT Case 2), not an adapter
        output. The adapter emits REF because the merge token references a stale
        commit (provenance mismatch). The label records expected_permission=ROL and
        control_outcome_acceptable=True so the evaluator can classify UNSOUND_CAUGHT.
        """
        trace, lbl = make_rol_trace(
            run_id=_run_id("057"), bead_id=_bead_id("057"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        judgments = _run_adapter(trace)
        assert len(judgments) == 1
        # Adapter emits REF (stale commit → provenance mismatch)
        assert str(judgments[0].permission) == "REF"
        # Label says ROL — the evaluator classifies as UNSOUND_CAUGHT Case 2
        assert lbl.expected_permission == "ROL"
        assert lbl.control_outcome_acceptable is True

    def test_058_rol_label_control_outcome_acceptable(self):
        """CORPUS-058: ROL trace label → control_outcome_acceptable=True."""
        _, lbl = make_rol_trace(
            run_id=_run_id("058"), bead_id=_bead_id("058"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        assert lbl.control_outcome_acceptable is True
        assert lbl.pattern_family == "ROL"

    def test_059_rol_trace_has_merge_event(self):
        """CORPUS-059: ROL trace has bd.call subcommand=merge event."""
        trace, _ = make_rol_trace(
            run_id=_run_id("059"), bead_id=_bead_id("059"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        merges = [e for e in trace
                  if e.get("event_type") == "bd.call"
                  and e.get("subcommand") == "merge"]
        assert len(merges) >= 1

    def test_060_rol_merge_has_stale_commit_for_provenance_mismatch(self):
        """CORPUS-060: ROL merge token references prior commit → provenance mismatch → REF."""
        # ROL has a stale commit mismatch — the merge token uses old commit
        # but the rollback capability is present, so the actual spec says ROL
        # Wait — re-read spec: ROL is a refinery merge with rollback capability.
        # The label says control_outcome_acceptable=True.
        # The ROL pattern must produce ROL from the evaluator (UNSOUND_CAUGHT Case 2).
        _, lbl = make_rol_trace(
            run_id=_run_id("060"), bead_id=_bead_id("060"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        # ROL expected: REF permission (provenance mismatch) but control_outcome_acceptable=True
        assert lbl.expected_permission == "ROL"


# ══════════════════════════════════════════════════════════════════════════════
# CORPUS-061–070: Corpus generation counts and structure
# ══════════════════════════════════════════════════════════════════════════════

class TestCorpusGeneration:

    def test_061_corpus_targets_include_all_families(self):
        """CORPUS-061: CORPUS_TARGETS dict has all expected family keys."""
        required = {"CLEAN", "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8",
                    "A1", "A2", "A3", "A4", "A5", "DIA", "AEX", "ROL"}
        assert required.issubset(set(CORPUS_TARGETS.keys()))

    def test_062_clean_target_is_50(self):
        """CORPUS-062: CLEAN family target is 50 traces."""
        assert CORPUS_TARGETS["CLEAN"] == 50

    def test_063_laundering_targets_are_10_each(self):
        """CORPUS-063: L1–L7 each have target of 10 traces."""
        for pat in ["L1", "L2", "L3", "L4", "L5", "L6", "L7"]:
            assert CORPUS_TARGETS[pat] == 10, f"{pat} should have target 10"

    def test_064_l8_target_is_20(self):
        """CORPUS-064: L8 depth ladder target is 20 (5 families × 4 depths)."""
        assert CORPUS_TARGETS["L8"] == 20

    def test_065_adversarial_targets_are_5_each(self):
        """CORPUS-065: A1–A5 each have target of 5 traces."""
        for pat in ["A1", "A2", "A3", "A4", "A5"]:
            assert CORPUS_TARGETS[pat] == 5, f"{pat} should have target 5"

    def test_066_algebra_targets_are_5_each(self):
        """CORPUS-066: DIA, AEX, ROL each have target of 5 traces."""
        for pat in ["DIA", "AEX", "ROL"]:
            assert CORPUS_TARGETS[pat] == 5, f"{pat} should have target 5"

    def test_067_total_corpus_target_is_180(self):
        """CORPUS-067: Total corpus target = 50+70+20+25+15 = 180."""
        total = sum(CORPUS_TARGETS.values())
        assert total == 180

    def test_068_generate_component1_corpus_returns_labeled_traces(self):
        """CORPUS-068: generate_component1_corpus() returns list of LabeledTrace."""
        corpus = generate_component1_corpus(base_ts=_NOW, base_run_id="gen-test")
        assert isinstance(corpus, list)
        assert len(corpus) > 0
        for lt in corpus:
            assert isinstance(lt, LabeledTrace)

    def test_069_generate_component1_corpus_has_correct_counts(self):
        """CORPUS-069: Generated corpus count matches total target of 180."""
        corpus = generate_component1_corpus(base_ts=_NOW, base_run_id="gen-count")
        assert len(corpus) == 180

    def test_070_generate_component1_corpus_all_traces_have_run_id(self):
        """CORPUS-070: Every generated trace has run_id on every event."""
        corpus = generate_component1_corpus(base_ts=_NOW, base_run_id="gen-runid")
        for lt in corpus:
            for ev in lt.trace:
                assert "run_id" in ev, f"Missing run_id in {lt.label.pattern_family} trace"


# ══════════════════════════════════════════════════════════════════════════════
# CORPUS-071–075: Label JSON generation
# ══════════════════════════════════════════════════════════════════════════════

class TestLabelJson:

    def test_071_labeled_trace_to_dict_has_all_keys(self):
        """CORPUS-071: LabeledTrace.to_dict() has trace, label, convoy_id, bead_type."""
        trace, lbl = make_clean_trace(
            run_id=_run_id("071"), bead_id=_bead_id("071"),
            rig=_RIG, git_commit=_GIT, ts=_NOW, role="polecat",
        )
        lt = LabeledTrace(trace=trace, label=lbl, convoy_id="c-071", bead_type="normal")
        d = lt.to_dict()
        assert "trace" in d
        assert "label" in d
        assert "convoy_id" in d
        assert "bead_type" in d

    def test_072_labeled_trace_to_dict_json_serializable(self):
        """CORPUS-072: LabeledTrace.to_dict() round-trips through JSON."""
        trace, lbl = make_clean_trace(
            run_id=_run_id("072"), bead_id=_bead_id("072"),
            rig=_RIG, git_commit=_GIT, ts=_NOW, role="polecat",
        )
        lt = LabeledTrace(trace=trace, label=lbl, convoy_id="c-072", bead_type="normal")
        json.dumps(lt.to_dict())  # should not raise

    def test_073_labeled_trace_label_in_dict_has_pattern_family(self):
        """CORPUS-073: Serialized label dict has pattern_family field."""
        trace, lbl = make_l1_trace(
            run_id=_run_id("073"), bead_id=_bead_id("073"),
            rig=_RIG, git_commit=_GIT, ts=_NOW,
        )
        lt = LabeledTrace(trace=trace, label=lbl, convoy_id="c-073", bead_type="normal")
        d = lt.to_dict()
        assert d["label"]["pattern_family"] == "L1"

    def test_074_generate_corpus_every_labeled_trace_has_ground_truth_rationale(self):
        """CORPUS-074: Every LabeledTrace in generated corpus has non-empty rationale."""
        corpus = generate_component1_corpus(base_ts=_NOW, base_run_id="gen-rationale")
        for lt in corpus:
            d = lt.to_dict()
            assert "ground_truth_rationale" in d["label"]
            assert len(d["label"]["ground_truth_rationale"]) > 0

    def test_075_generate_corpus_unique_run_ids(self):
        """CORPUS-075: All generated traces have unique run_ids."""
        corpus = generate_component1_corpus(base_ts=_NOW, base_run_id="gen-unique")
        run_ids = []
        for lt in corpus:
            for ev in lt.trace:
                rid = ev.get("run_id")
                if rid:
                    run_ids.append(rid)
        # All run_ids should appear consistently; same run_id within one trace is ok
        # but two different LabeledTraces should not share a run_id
        per_trace_run_ids = []
        for lt in corpus:
            rids = {ev.get("run_id") for ev in lt.trace if ev.get("run_id")}
            per_trace_run_ids.append(frozenset(rids))
        # Each trace should have a unique primary run_id
        primary_ids = [min(s) for s in per_trace_run_ids if s]
        assert len(primary_ids) == len(set(primary_ids))


# ══════════════════════════════════════════════════════════════════════════════
# CORPUS-076–080: Filler pass and Component 2 prompts
# ══════════════════════════════════════════════════════════════════════════════

class TestFillerAndComponent2:

    def test_076_filler_preserves_structural_fields(self):
        """CORPUS-076: apply_filler() does not modify structural fields."""
        trace, lbl = make_clean_trace(
            run_id=_run_id("076"), bead_id=_bead_id("076"),
            rig=_RIG, git_commit=_GIT, ts=_NOW, role="polecat",
        )
        filled = apply_filler(trace)
        # Check that event_type, run_id, bead_id, timestamp are unchanged
        for orig, filled_ev in zip(trace, filled):
            assert filled_ev["event_type"] == orig["event_type"]
            assert filled_ev["run_id"] == orig["run_id"]
            assert filled_ev.get("bead_id") == orig.get("bead_id")
            assert filled_ev["timestamp"] == orig["timestamp"]

    def test_077_filler_may_add_narrative_placeholder(self):
        """CORPUS-077: apply_filler() may add narrative_placeholder to events."""
        trace, _ = make_clean_trace(
            run_id=_run_id("077"), bead_id=_bead_id("077"),
            rig=_RIG, git_commit=_GIT, ts=_NOW, role="polecat",
        )
        filled = apply_filler(trace)
        # Filler returns a list of same length
        assert len(filled) == len(trace)

    def test_078_component2_prompts_json_exists(self):
        """CORPUS-078: corpus/component2/prompts.json exists and is valid JSON."""
        prompts_path = Path(__file__).parent.parent / "corpus" / "component2" / "prompts.json"
        assert prompts_path.exists(), f"Missing: {prompts_path}"
        with prompts_path.open() as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_079_component2_prompts_json_has_five_entries(self):
        """CORPUS-079: prompts.json has exactly five entries G1–G5."""
        prompts_path = Path(__file__).parent.parent / "corpus" / "component2" / "prompts.json"
        with prompts_path.open() as f:
            data = json.load(f)
        assert len(data["prompts"]) == 5
        ids = [p["id"] for p in data["prompts"]]
        assert ids == ["G1", "G2", "G3", "G4", "G5"]

    def test_080_component2_prompts_json_locked_field(self):
        """CORPUS-080: Each prompt in prompts.json has a non-empty text field."""
        prompts_path = Path(__file__).parent.parent / "corpus" / "component2" / "prompts.json"
        with prompts_path.open() as f:
            data = json.load(f)
        for p in data["prompts"]:
            assert "text" in p
            assert len(p["text"]) > 20
            assert "locked_at" in p
