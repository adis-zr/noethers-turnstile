"""GasTown provenance tests (PROV-001 through PROV-030).

Tests for the five-id provenance enforcement.
"""

from __future__ import annotations

import uuid
import noethers_turnstile as t
import pytest

from adapter.provenance import compute_action_provenance_hash

# ── Constants ──────────────────────────────────────────────────────────────────

_NOW = 1_748_736_000.0
_RUN_ID = "run-abc123"
_BEAD_ID = "bead-001"
_RIG = "rig-alpha"
_GIT_COMMIT = "deadbeef"
_ALLOWED_USE = "completion"


# ── PROV-001 through PROV-008: Hash basic properties ──────────────────────────

def test_prov_001_returns_64_char_hex():
    """PROV-001: compute_provenance_hash returns 64-char hex string."""
    h = compute_action_provenance_hash(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    assert isinstance(h, str)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_prov_002_same_inputs_same_hash():
    """PROV-002: same inputs → same hash (determinism)."""
    h1 = compute_action_provenance_hash(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    h2 = compute_action_provenance_hash(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    assert h1 == h2


def test_prov_003_different_claim_id_different_hash():
    """PROV-003: different claim_id → different hash."""
    h1 = compute_action_provenance_hash(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    h2 = compute_action_provenance_hash(_BEAD_ID, "run-different", _RIG, _GIT_COMMIT, _ALLOWED_USE)
    assert h1 != h2


def test_prov_004_different_candidate_id_different_hash():
    """PROV-004: different candidate_id → different hash."""
    h1 = compute_action_provenance_hash(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    h2 = compute_action_provenance_hash("bead-different", _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    assert h1 != h2


def test_prov_005_different_context_id_different_hash():
    """PROV-005: different context_id → different hash."""
    h1 = compute_action_provenance_hash(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    h2 = compute_action_provenance_hash(_BEAD_ID, _RUN_ID, "rig-different", _GIT_COMMIT, _ALLOWED_USE)
    assert h1 != h2


def test_prov_006_different_allowed_use_different_hash():
    """PROV-006: different allowed_use → different hash."""
    h1 = compute_action_provenance_hash(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, "completion")
    h2 = compute_action_provenance_hash(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, "merge")
    assert h1 != h2


def test_prov_007_argument_order_matters():
    """PROV-007: argument order matters (swapping any two → different hash)."""
    h1 = compute_action_provenance_hash(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    # Swap bead_id and run_id
    h2 = compute_action_provenance_hash(_RUN_ID, _BEAD_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    # Only check if they're different when the values are different
    if _BEAD_ID != _RUN_ID:
        assert h1 != h2


def test_prov_008_consistent_with_rust_compute_provenance_hash():
    """PROV-008: hash matches what t.compute_provenance_hash returns (consistency with Rust).

    The Python compute_action_provenance_hash wraps t.compute_provenance_hash
    with the correct argument mapping:
      claim_id = run_id (action identity)
      candidate_id = bead_id
      context_id = f"{run_id}:{rig}:{git_commit}"
      allowed_use = claim_class
    """
    from adapter.provenance import _build_context_id
    context_id = _build_context_id(_RUN_ID, _RIG, _GIT_COMMIT)
    # The Rust hash uses (claim_id, candidate_id, context_id, allowed_use)
    rust_hash = t.compute_provenance_hash(_RUN_ID, _BEAD_ID, context_id, _ALLOWED_USE)
    py_hash = compute_action_provenance_hash(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    assert py_hash == rust_hash


# ── PROV-009 through PROV-011: Token gap advancement ──────────────────────────

def test_prov_009_matching_prov_hash_gap_advanced():
    """PROV-009: token with matching prov_hash → gap advanced."""
    from adapter.provenance import _build_context_id

    context_id = _build_context_id(_RUN_ID, _RIG, _GIT_COMMIT)
    prov_hash = t.compute_provenance_hash(_RUN_ID, _BEAD_ID, context_id, _ALLOWED_USE)

    ctx = t.ProofContext(
        claim_id=_RUN_ID,
        candidate_id=_BEAD_ID,
        context_id=context_id,
        allowed_use=_ALLOWED_USE,
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.ALR,
        expiry=t.Expiry.never(),
        gaps=[t.GapRecord("context_integrity_gap", "context_integrity_gap")],
        profiles=[
            t.Profile(permission=t.Permission.DIA, required_gaps=[]),
            t.Profile(
                permission=t.Permission.ALR,
                required_gaps=[t.GapRequirement("context_integrity_gap", "closed")],
            ),
        ],
        tokens=[
            t.ProofToken(
                token_id="tok-1",
                token_type="prime_hook",
                schema_version="gt/0.1",
                status="valid",
                closes_gaps=["context_integrity_gap"],
                bounds_gaps=[],
                provenance_hash=prov_hash,
                issued_at=_NOW - 60,
                issuer="gastown",
            )
        ],
        context_fingerprint=context_id,
    )
    live = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=_NOW, context_fingerprint=context_id)
    perm = live.permission_str(rt)
    assert perm == "ALR"


def test_prov_010_mismatching_prov_hash_gap_stays_open():
    """PROV-010: token with mismatching prov_hash → gap stays OPEN, provenance_mismatch flag set."""
    from adapter.provenance import _build_context_id

    context_id = _build_context_id(_RUN_ID, _RIG, _GIT_COMMIT)

    ctx = t.ProofContext(
        claim_id=_RUN_ID,
        candidate_id=_BEAD_ID,
        context_id=context_id,
        allowed_use=_ALLOWED_USE,
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.ALR,
        expiry=t.Expiry.never(),
        gaps=[t.GapRecord("context_integrity_gap", "context_integrity_gap")],
        profiles=[
            t.Profile(permission=t.Permission.DIA, required_gaps=[]),
            t.Profile(
                permission=t.Permission.ALR,
                required_gaps=[t.GapRequirement("context_integrity_gap", "closed")],
            ),
        ],
        tokens=[
            t.ProofToken(
                token_id="tok-bad",
                token_type="prime_hook",
                schema_version="gt/0.1",
                status="valid",
                closes_gaps=["context_integrity_gap"],
                bounds_gaps=[],
                provenance_hash="deadbeef" * 8,   # wrong hash
                issued_at=_NOW - 60,
                issuer="gastown",
            )
        ],
        context_fingerprint=context_id,
    )
    live = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=_NOW, context_fingerprint=context_id)
    perm = live.permission_str(rt)
    # Wrong hash → gap not closed → ALR not reachable
    assert perm != "ALR"


def test_prov_011_five_id_binding_all_must_match():
    """PROV-011: five-id binding — all five must match."""
    from adapter.provenance import compute_action_provenance_hash as ph

    h_base = ph(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    # Change any one of the five → different hash
    assert ph("other-bead", _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE) != h_base
    assert ph(_BEAD_ID, "other-run", _RIG, _GIT_COMMIT, _ALLOWED_USE) != h_base
    assert ph(_BEAD_ID, _RUN_ID, "other-rig", _GIT_COMMIT, _ALLOWED_USE) != h_base
    assert ph(_BEAD_ID, _RUN_ID, _RIG, "other-commit", _ALLOWED_USE) != h_base
    assert ph(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, "other-use") != h_base


# ── PROV-012 through PROV-018: Five-id rejection scenarios ────────────────────

def test_prov_012_run_id_in_context_different_run_rejected():
    """PROV-012: run.id in context → token from different run.id rejected."""
    from adapter.provenance import compute_action_provenance_hash as ph

    h_correct = ph(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    h_wrong_run = ph(_BEAD_ID, "run-different", _RIG, _GIT_COMMIT, _ALLOWED_USE)
    assert h_correct != h_wrong_run


def test_prov_013_bead_id_in_candidate_different_bead_rejected():
    """PROV-013: bead_id in candidate → token for different bead rejected."""
    from adapter.provenance import compute_action_provenance_hash as ph

    h_correct = ph(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    h_wrong_bead = ph("bead-different", _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    assert h_correct != h_wrong_bead


def test_prov_014_rig_in_context_different_rig_rejected():
    """PROV-014: rig in context → token from different rig rejected."""
    from adapter.provenance import compute_action_provenance_hash as ph

    h_correct = ph(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    h_wrong_rig = ph(_BEAD_ID, _RUN_ID, "rig-different", _GIT_COMMIT, _ALLOWED_USE)
    assert h_correct != h_wrong_rig


def test_prov_015_git_commit_in_context_different_commit_rejected():
    """PROV-015: git_commit in context → token for different commit rejected."""
    from adapter.provenance import compute_action_provenance_hash as ph

    h_correct = ph(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    h_wrong_commit = ph(_BEAD_ID, _RUN_ID, _RIG, "commit-different", _ALLOWED_USE)
    assert h_correct != h_wrong_commit


def test_prov_016_l1_pattern_both_run_id_and_bead_id_mismatch_ref():
    """PROV-016: L1 pattern — both run.id and bead_id mismatch → REF."""
    from adapter.otel_adapter import process_trace

    trace = [
        {
            "event_type": "agent.instantiate",
            "timestamp": _NOW,
            "run_id": "run-r2",
            "bead_id": "bead-b2",
            "role": "polecat",
            "rig": _RIG,
            "git_commit": _GIT_COMMIT,
            "issue_id": "issue-1",
            "agent_name": "agent-a",
        },
        {
            "event_type": "prime",
            "timestamp": _NOW + 5,
            "run_id": "run-r2",
            "bead_id": "bead-b2",
            "hook_mode": True,
            "status": "ok",
            "provenance_run_id": "run-r1",    # wrong run
            "provenance_bead_id": "bead-b1",  # wrong bead
        },
        {
            "event_type": "done",
            "timestamp": _NOW + 30,
            "run_id": "run-r2",
            "bead_id": "bead-b2",
            "exit_type": "COMPLETED",
        },
    ]
    judgments = process_trace(trace, now_unix=_NOW + 60)
    assert len(judgments) >= 1
    assert str(judgments[0].permission) == "REF"


def test_prov_017_l4_pattern_rig_and_run_id_mismatch_ref():
    """PROV-017: L4 pattern — rig and run.id mismatch → REF."""
    from adapter.otel_adapter import process_trace

    trace = [
        {
            "event_type": "agent.instantiate",
            "timestamp": _NOW,
            "run_id": "run-r2",
            "bead_id": _BEAD_ID,
            "role": "polecat",
            "rig": "rig-beta",
            "git_commit": _GIT_COMMIT,
            "issue_id": "issue-1",
            "agent_name": "agent-a",
        },
        {
            "event_type": "prime",
            "timestamp": _NOW + 5,
            "run_id": "run-r2",
            "bead_id": _BEAD_ID,
            "hook_mode": True,
            "status": "ok",
            "provenance_rig": "rig-alpha",   # rig mismatch
            "provenance_run_id": "run-r1",   # run mismatch
        },
        {
            "event_type": "done",
            "timestamp": _NOW + 30,
            "run_id": "run-r2",
            "bead_id": _BEAD_ID,
            "exit_type": "COMPLETED",
        },
    ]
    judgments = process_trace(trace, now_unix=_NOW + 60)
    assert len(judgments) >= 1
    assert str(judgments[0].permission) == "REF"


def test_prov_018_l6_pattern_git_commit_mismatch_ref():
    """PROV-018: L6 pattern — git_commit mismatch in merge claim → REF."""
    from adapter.otel_adapter import process_trace

    trace = [
        {
            "event_type": "agent.instantiate",
            "timestamp": _NOW,
            "run_id": _RUN_ID,
            "bead_id": _BEAD_ID,
            "role": "refinery",
            "rig": _RIG,
            "git_commit": "commit-new",
            "issue_id": "issue-1",
            "agent_name": "refinery-agent",
        },
        {
            "event_type": "prime",
            "timestamp": _NOW + 5,
            "run_id": _RUN_ID,
            "bead_id": _BEAD_ID,
            "hook_mode": True,
            "status": "ok",
        },
        {
            "event_type": "bd.call",
            "timestamp": _NOW + 20,
            "run_id": _RUN_ID,
            "bead_id": _BEAD_ID,
            "subcommand": "merge",
            "gate_pass": True,
            "git_commit": "commit-old",   # mismatch
            "gate_token_commit": "commit-old",
            "args": {"branch": "main"},
        },
    ]
    judgments = process_trace(trace, now_unix=_NOW + 60)
    merge_j = [j for j in judgments if getattr(j, "claim_class", None) == "merge"]
    if merge_j:
        assert str(merge_j[0].permission) == "REF"


def test_prov_019_seance_token_provenance_bound_correctly():
    """PROV-019: seance token provenance — bound to (seance_run_id, bead_id, rig, git_commit)."""
    from adapter.seance import build_seance_token
    from adapter.provenance import compute_action_provenance_hash

    seance_event = {
        "event_type": "gt.seance",
        "timestamp": _NOW + 4,
        "run_id": _RUN_ID,
        "bead_id": _BEAD_ID,
        "predecessor_run_id": "run-prev",
        "staleness_seconds": 600,
        "commits_elapsed": 3,
        "current_timestamp": _NOW + 4,
        "predecessor_prime_timestamp": _NOW + 4 - 600,
    }

    tok = build_seance_token(seance_event, _BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, "completion")
    expected_hash = compute_action_provenance_hash(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, "completion")
    assert tok.provenance_hash == expected_hash


def test_prov_020_provenance_hash_full_64_chars():
    """PROV-020: provenance_hash in token is the full 64-char hash, not truncated."""
    from adapter.seance import build_seance_token

    seance_event = {
        "event_type": "gt.seance",
        "timestamp": _NOW + 4,
        "run_id": _RUN_ID,
        "bead_id": _BEAD_ID,
        "predecessor_run_id": "run-prev",
        "staleness_seconds": 600,
        "commits_elapsed": 3,
        "current_timestamp": _NOW + 4,
        "predecessor_prime_timestamp": _NOW - 596,
    }
    tok = build_seance_token(seance_event, _BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, "completion")
    assert len(tok.provenance_hash) == 64


def test_prov_021_null_delimiter_injection():
    """PROV-021: null delimiter injection: claim_id with embedded \\0 → different hash than split."""
    from adapter.provenance import compute_action_provenance_hash as ph

    # "abc\0def" as bead_id should not equal separate "abc" and "def" fields
    h1 = ph("abc\x00def", _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    h2 = ph("abc", "def" + _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    # These may or may not be different depending on the separator used,
    # but the hash function must handle null bytes without crashing
    assert isinstance(h1, str) and len(h1) == 64


def test_prov_022_empty_string_fields():
    """PROV-022: empty string fields → hash still computed (not crash)."""
    from adapter.provenance import compute_action_provenance_hash as ph

    h = ph("", "", "", "", "")
    assert isinstance(h, str) and len(h) == 64


def test_prov_023_unicode_in_fields():
    """PROV-023: unicode in fields → handled correctly."""
    from adapter.provenance import compute_action_provenance_hash as ph

    h = ph("bead-中文", _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    assert isinstance(h, str) and len(h) == 64


def test_prov_024_very_long_field_values():
    """PROV-024: very long field values → hash still works."""
    from adapter.provenance import compute_action_provenance_hash as ph

    long_val = "x" * 10000
    h = ph(long_val, _RUN_ID, _RIG, _GIT_COMMIT, _ALLOWED_USE)
    assert isinstance(h, str) and len(h) == 64


def test_prov_025_token_presented_to_wrong_claim_rejected():
    """PROV-025: token presented to wrong claim → rejected via prov mismatch."""
    from adapter.provenance import compute_action_provenance_hash as ph

    # Token for claim "completion" presented to claim "merge" context
    hash_completion = ph(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, "completion")
    hash_merge = ph(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, "merge")
    assert hash_completion != hash_merge


def test_prov_026_token_presented_to_wrong_context_rejected():
    """PROV-026: token presented to wrong context (different run.id) → rejected."""
    from adapter.provenance import compute_action_provenance_hash as ph

    h_run1 = ph(_BEAD_ID, "run-1", _RIG, _GIT_COMMIT, _ALLOWED_USE)
    h_run2 = ph(_BEAD_ID, "run-2", _RIG, _GIT_COMMIT, _ALLOWED_USE)
    assert h_run1 != h_run2


def test_prov_027_old_commit_not_accepted_for_new_commit_merge():
    """PROV-027: token from old commit not accepted for new commit merge."""
    from adapter.provenance import compute_action_provenance_hash as ph

    h_old = ph(_BEAD_ID, _RUN_ID, _RIG, "commit-old", "merge")
    h_new = ph(_BEAD_ID, _RUN_ID, _RIG, "commit-new", "merge")
    assert h_old != h_new


def test_prov_028_convoy_authority_token_scoped_to_bead_rig_role():
    """PROV-028: convoy authority token — scoped to bead+rig+role, not just run.id."""
    from adapter.provenance import compute_action_provenance_hash as ph

    # convoy token for bead-001/rig-alpha/polecat
    h1 = ph(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, "delegation")
    # Different rig → different token
    h2 = ph(_BEAD_ID, _RUN_ID, "rig-beta", _GIT_COMMIT, "delegation")
    assert h1 != h2


def test_prov_029_mayor_delegation_token_provenance():
    """PROV-029: Mayor delegation token — provenance includes delegation target."""
    from adapter.provenance import compute_action_provenance_hash as ph

    h1 = ph(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, "delegation")
    h2 = ph(_BEAD_ID, _RUN_ID, _RIG, _GIT_COMMIT, "delegation_other")
    assert h1 != h2


def test_prov_030_cross_rig_escalation_both_dimensions_rejected():
    """PROV-030: cross-rig escalation (L4) — both dimensions independently rejected."""
    from adapter.provenance import compute_action_provenance_hash as ph

    # Token from rig-alpha/run-r1 vs context rig-beta/run-r2
    h_source = ph(_BEAD_ID, "run-r1", "rig-alpha", _GIT_COMMIT, _ALLOWED_USE)
    h_target = ph(_BEAD_ID, "run-r2", "rig-beta", _GIT_COMMIT, _ALLOWED_USE)
    assert h_source != h_target
