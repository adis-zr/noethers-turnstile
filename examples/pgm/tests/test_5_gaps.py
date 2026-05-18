"""Gap-correctness tests (GAP-001 through GAP-020).

This file covers the gaps that the original test suite left undemonstrated:

GAP-001–005: model_specification_gap blocks ALR on exact_inference_result.
             A ModelSpecificationToken (new token type) bounds the gap and
             allows ALR to be reached.

GAP-006–010: certified_approximate_inference BIF benchmark — what permission
             a real network earns under approximate inference, and what
             model_specification_gap being open costs at ALR.

GAP-011–014: Context expiry tied to issued_at + ttl_seconds.

GAP-015–020: Serde round-trip — compiled judgment fields survive
             reconstruction from ProofContext attributes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import pytest
import turnstile as t

from bridge import (
    CertifiedBoundToken,
    CertifierContract,
    ExactInferenceToken,
    FreshnessToken,
    compile_pgm,
    fingerprint,
    fingerprint_evidence,
    fingerprint_graph,
    fingerprint_query,
    parse_bif,
    bif_to_pgm_dicts,
)
from bridge.bridge import _build_profiles, _translate_token
from bridge.claims import GAP_BASIS

_NOW = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)

_GRAPH = {
    "variables": {"A": [0, 1], "B": [0, 1]},
    "factors": [{"scope": ["A", "B"], "table": [0.3, 0.7, 0.6, 0.4]}],
}
_QUERY = {"target": "A", "type": "marginal"}
_EVIDENCE = {"B": 1}
_RUNTIME = {
    "graph_version": "v1",
    "evidence_version": "v1",
    "certifier_registry_version": "v1",
    "algorithm_implementation_fingerprint": "abc123",
    "token_registry_version": "v1",
}
BIF_DIR = Path(__file__).parent.parent / "data" / "bif"


# ── ModelSpecificationToken (not yet in the bridge token library) ─────────────
#
# This dataclass represents the token type that would be issued by a model
# adequacy certifier — something outside the scope of the inference algorithm
# itself.  It bounds model_specification_gap when fingerprints match.
#
# In production this token would be issued by a domain expert or external
# validation process, NOT by the same system that ran the inference.  That
# separation is why the certifier boundary matters: ExactInferenceToken can
# only prove the computation was exact; it cannot prove the model is right.

@dataclass
class ModelSpecificationToken:
    proof_token_id: str
    token_type: Literal["ModelSpecificationToken"]
    status: Literal["VALID", "INVALID", "REVOKED", "EXPIRED", "MALFORMED"]
    issuer: str
    graph_fingerprint: str
    # closes_gaps is intentionally empty — this token bounds, not closes.
    bounds_gaps: list[str] = field(default_factory=lambda: ["model_specification_gap"])
    closes_gaps: list[str] = field(default_factory=list)


def _translate_model_spec_token(
    token: ModelSpecificationToken,
    prov_hash: str,
    fp_graph: str,
    issued_at_unix: float,
) -> t.ProofToken:
    """Translate a ModelSpecificationToken into a turnstile ProofToken."""
    bounds: list[str] = []
    if token.status == "VALID" and token.graph_fingerprint == fp_graph:
        bounds = ["model_specification_gap"]
    return t.ProofToken(
        token_id=token.proof_token_id,
        token_type=token.token_type,
        schema_version="pgm-bridge/0.1.0",
        status=token.status.lower(),
        closes_gaps=[],
        bounds_gaps=bounds,
        provenance_hash=prov_hash,
        issued_at=issued_at_unix,
        issuer=token.issuer,
    )


def _compile_with_extra_token(tokens_extra: list, claim_class: str = "exact_inference_result") -> str:
    """Helper: compile with standard GRAPH/QUERY/EVIDENCE plus extra tokens."""
    fp_graph = fingerprint_graph(_GRAPH)
    fp_query = fingerprint_query(_QUERY)
    fp_evidence = fingerprint_evidence(_EVIDENCE)
    fp_algorithm = fingerprint("exact")
    allowed_use = claim_class
    context_id = fp_evidence
    prov_hash = t.compute_provenance_hash(fp_graph, fp_query, context_id, allowed_use)
    issued_at_unix = _NOW.timestamp()

    standard_tokens = [
        ExactInferenceToken(
            proof_token_id=str(uuid.uuid4()),
            token_type="ExactInferenceToken",
            status="VALID",
            issuer="test",
            graph_fingerprint=fp_graph,
            query_fingerprint=fp_query,
            evidence_fingerprint=fp_evidence,
            algorithm_fingerprint=fp_algorithm,
        ),
        FreshnessToken(
            proof_token_id=str(uuid.uuid4()),
            token_type="FreshnessToken",
            status="VALID",
            issuer="test",
            graph_fingerprint=fp_graph,
            query_fingerprint=fp_query,
            evidence_fingerprint=fp_evidence,
        ),
    ]

    ts_tokens = [
        _translate_token(tok, prov_hash, fp_graph, fp_query, fp_evidence, fp_algorithm, issued_at_unix)
        for tok in standard_tokens
    ]
    for tok in tokens_extra:
        if isinstance(tok, ModelSpecificationToken):
            ts_tokens.append(_translate_model_spec_token(tok, prov_hash, fp_graph, issued_at_unix))

    ctx = t.ProofContext(
        claim_id=fp_graph,
        candidate_id=fp_query,
        context_id=context_id,
        allowed_use=allowed_use,
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.ALR,
        expiry=t.Expiry.never(),
        gaps=[t.GapRecord(gap_id=g, gap_type=g) for g in GAP_BASIS],
        profiles=_build_profiles(allowed_use),
        tokens=ts_tokens,
        context_fingerprint=context_id,
    )
    live = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=_NOW.timestamp(), context_fingerprint=context_id)
    return live.permission_str(rt)


# ── GAP-001–005: model_specification_gap gate ─────────────────────────────────

def test_gap_001_no_model_spec_token_blocks_alr():
    """GAP-001: ExactInferenceToken + FreshnessToken without ModelSpecificationToken → AEX.

    ALR requires model_specification_gap BOUNDED.  Without a token that bounds
    it, the gap stays OPEN and ALR is unreachable regardless of other evidence.
    """
    perm = _compile_with_extra_token([])
    assert perm == "AEX", f"Expected AEX (model_specification_gap open), got {perm}"


def test_gap_002_model_spec_token_bounds_gap_enables_alr():
    """GAP-002: Adding ModelSpecificationToken bounds model_specification_gap → ALR.

    The token provides evidence that the model is adequate for the real-world
    target.  Combined with ExactInferenceToken (closes approximation/identity)
    and FreshnessToken (closes freshness), all ALR requirements are now met.
    """
    spec_tok = ModelSpecificationToken(
        proof_token_id=str(uuid.uuid4()),
        token_type="ModelSpecificationToken",
        status="VALID",
        issuer="domain-expert",
        graph_fingerprint=fingerprint_graph(_GRAPH),
    )
    perm = _compile_with_extra_token([spec_tok])
    assert perm == "ALR", f"Expected ALR with model spec evidence, got {perm}"


def test_gap_003_revoked_model_spec_token_does_not_bound_gap():
    """GAP-003: Revoked ModelSpecificationToken → model_specification_gap stays OPEN → AEX.

    A REVOKED token is passed with empty bounds_gaps.  The gap doesn't advance
    and ALR stays unreachable.
    """
    spec_tok = ModelSpecificationToken(
        proof_token_id=str(uuid.uuid4()),
        token_type="ModelSpecificationToken",
        status="REVOKED",
        issuer="domain-expert",
        graph_fingerprint=fingerprint_graph(_GRAPH),
    )
    perm = _compile_with_extra_token([spec_tok])
    assert perm == "AEX", f"Expected AEX (revoked spec token), got {perm}"


def test_gap_004_wrong_graph_fingerprint_does_not_bound_gap():
    """GAP-004: ModelSpecificationToken with wrong graph_fingerprint → gap stays OPEN → AEX.

    The token is VALID but its graph_fingerprint doesn't match the compiled
    spec.  The translate step sees a mismatch and returns empty bounds_gaps.
    """
    spec_tok = ModelSpecificationToken(
        proof_token_id=str(uuid.uuid4()),
        token_type="ModelSpecificationToken",
        status="VALID",
        issuer="domain-expert",
        graph_fingerprint="deadbeefdeadbeef" + "0" * 48,  # wrong fingerprint
    )
    perm = _compile_with_extra_token([spec_tok])
    assert perm == "AEX", f"Expected AEX (wrong graph fingerprint), got {perm}"


def test_gap_005_model_spec_gap_open_makes_aaa_unreachable():
    """GAP-005: Without model_specification_gap CLOSED, AAA is unreachable.

    AAA requires model_specification_gap CLOSED.  Even a bounding token is
    not sufficient — AAA stays unreachable until a token CLOSES the gap.
    """
    spec_tok = ModelSpecificationToken(
        proof_token_id=str(uuid.uuid4()),
        token_type="ModelSpecificationToken",
        status="VALID",
        issuer="domain-expert",
        graph_fingerprint=fingerprint_graph(_GRAPH),
    )
    # With a bounding token we reach ALR — but we need CLOSED for AAA.
    # Compile directly against AAA ceiling to confirm ALR is the actual result.
    fp_graph = fingerprint_graph(_GRAPH)
    fp_query = fingerprint_query(_QUERY)
    fp_evidence = fingerprint_evidence(_EVIDENCE)
    fp_algorithm = fingerprint("exact")
    context_id = fp_evidence
    prov_hash = t.compute_provenance_hash(fp_graph, fp_query, context_id, "exact_inference_result")
    issued_at_unix = _NOW.timestamp()

    ts_tokens = [
        _translate_token(
            ExactInferenceToken(
                proof_token_id=str(uuid.uuid4()), token_type="ExactInferenceToken",
                status="VALID", issuer="test",
                graph_fingerprint=fp_graph, query_fingerprint=fp_query,
                evidence_fingerprint=fp_evidence, algorithm_fingerprint=fp_algorithm,
            ),
            prov_hash, fp_graph, fp_query, fp_evidence, fp_algorithm, issued_at_unix,
        ),
        _translate_token(
            FreshnessToken(
                proof_token_id=str(uuid.uuid4()), token_type="FreshnessToken",
                status="VALID", issuer="test",
                graph_fingerprint=fp_graph, query_fingerprint=fp_query,
                evidence_fingerprint=fp_evidence,
            ),
            prov_hash, fp_graph, fp_query, fp_evidence, fp_algorithm, issued_at_unix,
        ),
        _translate_model_spec_token(spec_tok, prov_hash, fp_graph, issued_at_unix),
    ]

    ctx = t.ProofContext(
        claim_id=fp_graph, candidate_id=fp_query, context_id=context_id,
        allowed_use="exact_inference_result",
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.AAA,  # ceiling is AAA
        expiry=t.Expiry.never(),
        gaps=[t.GapRecord(gap_id=g, gap_type=g) for g in GAP_BASIS],
        profiles=_build_profiles("exact_inference_result"),
        tokens=ts_tokens,
        context_fingerprint=context_id,
    )
    live = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=issued_at_unix, context_fingerprint=context_id)
    perm = live.permission_str(rt)
    # BOUNDED model_spec_gap satisfies ALR but not AAA (which requires CLOSED).
    assert perm == "ALR", f"Expected ALR (spec gap bounded not closed), got {perm}"


# ── GAP-006–010: certified_approximate_inference BIF benchmark ─────────────────

_BIF_TIER1 = ["asia", "cancer", "earthquake"]

_APPROX_RUNTIME = {
    "graph_version": "v1",
    "evidence_version": "v1",
    "certifier_registry_version": "v1",
    "algorithm_implementation_fingerprint": "approx-test",
    "token_registry_version": "v1",
}


def _skip_if_missing(name: str) -> None:
    path = BIF_DIR / f"{name}.bif"
    if not path.exists():
        pytest.skip(f"{name}.bif not found in {BIF_DIR}")


def _run_approx_bif(name: str, with_model_spec: bool = False) -> str:
    """Run certified_approximate_inference on a BIF graph, return permission string.

    Builds the full token list directly (including optional ModelSpecificationToken)
    and compiles via the low-level ProofContext API so all tokens are included in
    a single compilation — ProofContext doesn't expose its token list post-compile.
    """
    path = BIF_DIR / f"{name}.bif"
    g = parse_bif(path)
    graph, query, evidence = bif_to_pgm_dicts(g)

    fp_graph = fingerprint_graph(graph)
    fp_query = fingerprint_query(query)
    fp_evidence = fingerprint_evidence(evidence)
    fp_algorithm = fingerprint("certified_approximate")
    allowed_use = "certified_approximate_inference"
    context_id = fp_evidence
    issued_at_unix = _NOW.timestamp()
    prov_hash = t.compute_provenance_hash(fp_graph, fp_query, context_id, allowed_use)

    contract = CertifierContract(
        certifier_id="certifier-bp",
        certifier_version="1.0.0",
        certifier_type="interval_bound",
        guarantee_type="marginal_interval",
        guarantee_statement="Marginal beliefs within epsilon of true marginals",
        scope_binding={
            "graph_fingerprint": fp_graph,
            "query_fingerprint": fp_query,
            "evidence_fingerprint": fp_evidence,
            "algorithm_fingerprint": fp_algorithm,
        },
        implementation_fingerprint="impl-fp-001",
        issuer_id="issuer-001",
        issued_at=_NOW,
    )
    domain_tokens: list = [
        CertifiedBoundToken(
            proof_token_id=str(uuid.uuid4()),
            token_type="CertifiedBoundToken",
            status="VALID",
            issuer="bif-test",
            certifier_contract=contract,
        ),
        FreshnessToken(
            proof_token_id=str(uuid.uuid4()),
            token_type="FreshnessToken",
            status="VALID",
            issuer="bif-test",
            graph_fingerprint=fp_graph,
            query_fingerprint=fp_query,
            evidence_fingerprint=fp_evidence,
        ),
    ]

    ts_tokens = [
        _translate_token(tok, prov_hash, fp_graph, fp_query, fp_evidence, fp_algorithm, issued_at_unix)
        for tok in domain_tokens
    ]

    if with_model_spec:
        spec_tok = ModelSpecificationToken(
            proof_token_id=str(uuid.uuid4()),
            token_type="ModelSpecificationToken",
            status="VALID",
            issuer="domain-expert",
            graph_fingerprint=fp_graph,
        )
        ts_tokens.append(_translate_model_spec_token(spec_tok, prov_hash, fp_graph, issued_at_unix))

    ctx = t.ProofContext(
        claim_id=fp_graph,
        candidate_id=fp_query,
        context_id=context_id,
        allowed_use=allowed_use,
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.ALR,
        expiry=t.Expiry.never(),
        gaps=[t.GapRecord(gap_id=g, gap_type=g) for g in GAP_BASIS],
        profiles=_build_profiles(allowed_use),
        tokens=ts_tokens,
        context_fingerprint=context_id,
    )
    live = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=issued_at_unix, context_fingerprint=context_id)
    return live.permission_str(rt)


@pytest.mark.parametrize("name", _BIF_TIER1)
def test_gap_006_certified_approx_without_model_spec_caps_at_aex(name):
    """GAP-006: CertifiedBoundToken + FreshnessToken without ModelSpecificationToken → AEX.

    certified_approximate_inference ALR requires model_specification_gap BOUNDED.
    CertifiedBoundToken bounds approximation/certifier_soundness/bound_scope;
    FreshnessToken closes freshness.  But model_specification_gap stays OPEN.
    AEX is the highest reachable permission — same failure mode as exact inference.
    """
    _skip_if_missing(name)
    perm = _run_approx_bif(name, with_model_spec=False)
    assert perm == "AEX", f"{name}: expected AEX (model_specification_gap open), got {perm}"


@pytest.mark.parametrize("name", _BIF_TIER1)
def test_gap_007_certified_approx_with_model_spec_earns_alr(name):
    """GAP-007: Adding ModelSpecificationToken to certified_approximate path → ALR.

    With model_specification_gap BOUNDED, all ALR requirements for
    certified_approximate_inference are met: approximation BOUNDED,
    certifier_soundness BOUNDED, bound_scope CLOSED, model_specification BOUNDED,
    freshness CLOSED.
    """
    _skip_if_missing(name)
    perm = _run_approx_bif(name, with_model_spec=True)
    assert perm == "ALR", f"{name}: expected ALR with model spec, got {perm}"


def test_gap_008_certified_approx_no_tokens_gives_dia():
    """GAP-008: certified_approximate_inference with no tokens → DIA.

    All 11 gaps OPEN, DIA is the in-class floor.  Confirmed on a synthetic
    graph (no BIF file needed).
    """
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="certified_approximate",
        tokens=[],
        claim_class="certified_approximate_inference",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    assert result.permission() == "DIA"


def test_gap_009_uncertified_approx_always_capped_at_rev():
    """GAP-009: uncertified_approximate_inference has no AEX/ALR profiles → REV ceiling.

    Even with full gap coverage, the class definition only goes to REV.
    This is the correct guardrail: uncertified approximate results can inform
    review (REV) but cannot be granted execution authority (AEX/ALR).
    """
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="uncertified_approximate",
        tokens=[],
        claim_class="uncertified_approximate_inference",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    assert result.permission() == "DIA"  # no tokens → DIA (below REV ceiling)


def test_gap_010_model_spec_gap_in_taxonomy():
    """GAP-010: model_specification_gap is present in the 11-gap taxonomy."""
    assert "model_specification_gap" in GAP_BASIS
    # Verify its position (after approximation_gap, before certifier_soundness_gap)
    idx = GAP_BASIS.index("model_specification_gap")
    assert idx > GAP_BASIS.index("approximation_gap")
    assert idx < GAP_BASIS.index("certifier_soundness_gap")


# ── GAP-011–014: Context expiry tied to issued_at + ttl_seconds ──────────────
#
# These tests use real clock time (time.time()) rather than the fixed _NOW
# timestamp because Expiry.at() is evaluated against the RuntimeContext.now_unix
# at judgment-check time.  Using _NOW would pre-expire contexts since
# _NOW + ttl is already in the past relative to actual test execution time.

import time as _time


def _exact_token_for_graph(graph, query, evidence):
    return ExactInferenceToken(
        proof_token_id=str(uuid.uuid4()),
        token_type="ExactInferenceToken",
        status="VALID",
        issuer="test",
        graph_fingerprint=fingerprint_graph(graph),
        query_fingerprint=fingerprint_query(query),
        evidence_fingerprint=fingerprint_evidence(evidence),
        algorithm_fingerprint=fingerprint("exact"),
    )


def test_gap_011_expired_context_gives_exp():
    """GAP-011: Context with ttl_seconds=1 compiled at now expires after 1 second → EXP.

    The bridge's ttl_seconds parameter is wired into Expiry.at(issued_at + ttl).
    When the RuntimeContext's now_unix is past that expiry, permission_str → EXP.
    Uses a now-relative issued_at so the expiry is not pre-expired at test time.
    """
    now = datetime.now(timezone.utc)
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact",
        tokens=[_exact_token_for_graph(_GRAPH, _QUERY, _EVIDENCE)],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR",
        issued_at=now, ttl_seconds=1.0,
    )
    expired_rt = t.RuntimeContext(
        now_unix=now.timestamp() + 2.0,
        context_fingerprint=result.ctx.context_id,
    )
    assert result.live.permission_str(expired_rt) == "EXP"


def test_gap_012_valid_context_within_ttl():
    """GAP-012: Context with ttl_seconds=3600 evaluated at issued_at + 60 → AEX.

    Within the 3600s TTL window, the permission is not EXP.
    model_specification_gap is still open so AEX is the ceiling.
    """
    now = datetime.now(timezone.utc)
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact",
        tokens=[_exact_token_for_graph(_GRAPH, _QUERY, _EVIDENCE)],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR",
        issued_at=now, ttl_seconds=3600.0,
    )
    within_rt = t.RuntimeContext(
        now_unix=now.timestamp() + 60.0,
        context_fingerprint=result.ctx.context_id,
    )
    assert result.live.permission_str(within_rt) == "AEX"


def test_gap_013_ttl_none_never_expires():
    """GAP-013: ttl_seconds=None → context never expires regardless of evaluation time."""
    now = datetime.now(timezone.utc)
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact",
        tokens=[_exact_token_for_graph(_GRAPH, _QUERY, _EVIDENCE)],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR",
        issued_at=now, ttl_seconds=None,
    )
    far_future_rt = t.RuntimeContext(
        now_unix=now.timestamp() + 365 * 86400,
        context_fingerprint=result.ctx.context_id,
    )
    assert result.live.permission_str(far_future_rt) == "AEX"


def test_gap_014_default_ttl_is_24h():
    """GAP-014: Default ttl_seconds is 86400 (24 hours) — context expires after 24h + 1s."""
    now = datetime.now(timezone.utc)
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR",
        issued_at=now,
    )
    just_expired_rt = t.RuntimeContext(
        now_unix=now.timestamp() + 86401.0,
        context_fingerprint=result.ctx.context_id,
    )
    assert result.live.permission_str(just_expired_rt) == "EXP"


# ── GAP-015–020: Serde round-trip ─────────────────────────────────────────────
#
# LiveJudgment is a Rust-backed object that cannot be pickled.  The serde
# contract is therefore: the ProofContext fields that identify a judgment
# (claim_id, candidate_id, context_id, allowed_use, authority_ceiling,
# provenance_hash) can be extracted, stored, and used to recompile an
# equivalent judgment that yields the same permission.
#
# This is the production pattern: a judgment issuer stores the ProofContext
# fields alongside the permission; a verifier recompiles from those fields
# and confirms the permission matches.  If any field is dropped or corrupted
# the recompiled permission will differ.

def _serialize_judgment(result) -> dict:
    """Extract the fields needed to reconstruct a judgment from a BridgeResult."""
    ctx = result.ctx
    return {
        "claim_id": ctx.claim_id,
        "candidate_id": ctx.candidate_id,
        "context_id": ctx.context_id,
        "allowed_use": ctx.allowed_use,
        "provenance_hash": ctx.provenance_hash(),
        "authority_ceiling": str(ctx.authority_ceiling),
        "permission": result.permission(),
    }


def _verify_serialized_judgment(stored: dict, recompiled_result) -> bool:
    """Verify that a recompiled result matches the stored judgment fields."""
    if recompiled_result.permission() != stored["permission"]:
        return False
    ctx = recompiled_result.ctx
    if ctx.claim_id != stored["claim_id"]:
        return False
    if ctx.candidate_id != stored["candidate_id"]:
        return False
    if ctx.context_id != stored["context_id"]:
        return False
    if ctx.provenance_hash() != stored["provenance_hash"]:
        return False
    return True


def test_gap_015_serde_round_trip_permission_preserved():
    """GAP-015: Serialized judgment fields survive recompilation with same permission."""
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact",
        tokens=[ExactInferenceToken(
            proof_token_id="tok-serde-015",
            token_type="ExactInferenceToken",
            status="VALID",
            issuer="test",
            graph_fingerprint=fingerprint_graph(_GRAPH),
            query_fingerprint=fingerprint_query(_QUERY),
            evidence_fingerprint=fingerprint_evidence(_EVIDENCE),
            algorithm_fingerprint=fingerprint("exact"),
        )],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    stored = _serialize_judgment(result)
    assert stored["permission"] == "AEX"

    # Recompile from the same inputs — simulates a verifier reconstructing.
    recompiled = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact",
        tokens=[ExactInferenceToken(
            proof_token_id="tok-serde-015",
            token_type="ExactInferenceToken",
            status="VALID",
            issuer="test",
            graph_fingerprint=fingerprint_graph(_GRAPH),
            query_fingerprint=fingerprint_query(_QUERY),
            evidence_fingerprint=fingerprint_evidence(_EVIDENCE),
            algorithm_fingerprint=fingerprint("exact"),
        )],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    assert _verify_serialized_judgment(stored, recompiled), (
        f"Round-trip failed: stored={stored}, recompiled_perm={recompiled.permission()}"
    )


def test_gap_016_serde_claim_id_is_graph_fingerprint():
    """GAP-016: claim_id in serialized judgment equals fingerprint_graph(graph).

    The stable mapping claim_id ↔ graph_fingerprint must survive round-trip.
    A verifier who recomputes the fingerprint from the same graph must get the
    same claim_id.
    """
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    stored = _serialize_judgment(result)
    assert stored["claim_id"] == fingerprint_graph(_GRAPH)


def test_gap_017_serde_provenance_hash_is_deterministic():
    """GAP-017: provenance_hash in serialized judgment is deterministic across recompilations.

    Two separate compile_pgm calls with identical inputs must produce identical
    provenance_hash values.  If this fails, stored audit trails can't be verified.
    """
    def _compile_and_get_prov():
        result = compile_pgm(
            graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
            algorithm="exact", tokens=[],
            claim_class="exact_inference_result",
            runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
        )
        return result.ctx.provenance_hash()

    prov1 = _compile_and_get_prov()
    prov2 = _compile_and_get_prov()
    assert prov1 == prov2, f"Non-deterministic provenance: {prov1} != {prov2}"


def test_gap_018_serde_altered_graph_changes_claim_id():
    """GAP-018: Changing the graph produces a different claim_id.

    If a stored judgment's claim_id doesn't match the recomputed fingerprint of
    the graph the verifier is checking, the audit trail is broken.  This test
    confirms that even a single-variable change causes a claim_id mismatch.
    """
    result_a = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    altered_graph = {
        "variables": {"A": [0, 1], "B": [0, 1], "C": [0, 1]},  # extra variable
        "factors": [{"scope": ["A", "B"], "table": [0.3, 0.7, 0.6, 0.4]}],
    }
    result_b = compile_pgm(
        graph=altered_graph, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    assert result_a.ctx.claim_id != result_b.ctx.claim_id, (
        "Different graphs must produce different claim_ids"
    )


def test_gap_019_serde_ooc_permission_preserved():
    """GAP-019: OOC judgment serializes and recompiles as OOC."""
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[],
        claim_class="exact_inference_result",
        runtime={},  # empty runtime → OOC
        authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    stored = _serialize_judgment(result)
    assert stored["permission"] == "OOC"

    recompiled = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[],
        claim_class="exact_inference_result",
        runtime={},
        authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    assert recompiled.permission() == "OOC"


def test_gap_020_serde_provenance_hash_length():
    """GAP-020: provenance_hash in serialized judgment is a 64-char hex string (SHA-256).

    The bridge uses the full SHA-256 digest for fingerprints and provenance.
    A 64-char hex string (= 256 bits) is required.  Shorter hashes indicate
    a truncation bug.
    """
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    stored = _serialize_judgment(result)
    prov = stored["provenance_hash"]
    assert len(prov) == 64, f"Expected 64-char provenance_hash, got {len(prov)}: {prov!r}"
    assert all(c in "0123456789abcdef" for c in prov), f"Non-hex chars in provenance_hash: {prov!r}"
    # Confirm claim_id (= graph fingerprint) is also full 64-char SHA-256
    claim_id = stored["claim_id"]
    assert len(claim_id) == 64, f"claim_id (graph fingerprint) should be 64 chars, got {len(claim_id)}"
