"""Bridge agreement tests (BRIDGE-001 through BRIDGE-010).

Each test demonstrates a specific gap-coverage scenario and asserts the
permission that noethers-turnstile produces.  The expected permission is derived
directly from the gap closure rules in bridge/claims.py — no reference
adapter is needed.

These tests serve as documentation: each docstring explains WHY the expected
permission follows from the evidence provided.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import noethers_turnstile as t

from bridge import (
    ExactInferenceToken,
    FreshnessToken,
    ModelIdentityToken,
    compile_pgm,
    fingerprint,
    fingerprint_evidence,
    fingerprint_graph,
    fingerprint_query,
)
from bridge.claims import GAP_BASIS, PROFILE_REQUIREMENTS
from bridge.tokens import CertifiedBoundToken, CertifierContract

# ── Shared test fixtures ───────────────────────────────────────────────────────

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


def _exact_token(status: str = "VALID") -> ExactInferenceToken:
    return ExactInferenceToken(
        proof_token_id=str(uuid.uuid4()),
        token_type="ExactInferenceToken",
        status=status,
        issuer="test-issuer",
        graph_fingerprint=fingerprint_graph(_GRAPH),
        query_fingerprint=fingerprint_query(_QUERY),
        evidence_fingerprint=fingerprint_evidence(_EVIDENCE),
        algorithm_fingerprint=fingerprint("exact"),
    )


def _freshness_token(status: str = "VALID") -> FreshnessToken:
    return FreshnessToken(
        proof_token_id=str(uuid.uuid4()),
        token_type="FreshnessToken",
        status=status,
        issuer="test-issuer",
        graph_fingerprint=fingerprint_graph(_GRAPH),
        query_fingerprint=fingerprint_query(_QUERY),
        evidence_fingerprint=fingerprint_evidence(_EVIDENCE),
    )


def _model_identity_token(status: str = "VALID") -> ModelIdentityToken:
    return ModelIdentityToken(
        proof_token_id=str(uuid.uuid4()),
        token_type="ModelIdentityToken",
        status=status,
        issuer="test-issuer",
        graph_fingerprint=fingerprint_graph(_GRAPH),
        evidence_fingerprint=fingerprint_evidence(_EVIDENCE),
    )


def _certified_bound_token(status: str = "VALID") -> CertifiedBoundToken:
    contract = CertifierContract(
        certifier_id="certifier-bp",
        certifier_version="1.0.0",
        certifier_type="interval_bound",
        guarantee_type="marginal_interval",
        guarantee_statement="Marginal beliefs within epsilon of true marginals",
        scope_binding={
            "graph_fingerprint": fingerprint_graph(_GRAPH),
            "query_fingerprint": fingerprint_query(_QUERY),
            "evidence_fingerprint": fingerprint_evidence(_EVIDENCE),
            "algorithm_fingerprint": fingerprint("certified_approximate"),
        },
        implementation_fingerprint="impl-fp-001",
        issuer_id="issuer-001",
        issued_at=_NOW,
    )
    return CertifiedBoundToken(
        proof_token_id=str(uuid.uuid4()),
        token_type="CertifiedBoundToken",
        status=status,
        issuer="test-issuer",
        certifier_contract=contract,
    )


# ── BRIDGE-001 ────────────────────────────────────────────────────────────────

def test_bridge_001_exact_token_no_freshness():
    """BRIDGE-001: ExactInferenceToken alone → AEX.

    ExactInferenceToken closes: approximation_gap, model_identity_gap,
    query_identity_gap, evidence_identity_gap, algorithm_reproducibility_gap.

    ALR also requires freshness_gap CLOSED — not provided here.
    AEX requires approximation_gap CLOSED + identity gaps CLOSED → satisfied.
    """
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[_exact_token()],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    assert result.permission() == "AEX"


# ── BRIDGE-002 ────────────────────────────────────────────────────────────────

def test_bridge_002_exact_plus_freshness_earns_aex_not_alr():
    """BRIDGE-002: ExactInferenceToken + FreshnessToken → AEX, not ALR.

    ALR now requires model_specification_gap BOUNDED in addition to the
    identity/approximation/freshness gaps.  ExactInferenceToken closes the
    approximation and identity gaps; FreshnessToken closes freshness_gap.
    But model_specification_gap stays OPEN — no token provides evidence that
    the supplied model is adequate for the real-world target.
    AEX is the highest permission reachable without model adequacy evidence.
    """
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[_exact_token(), _freshness_token()],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    assert result.permission() == "AEX"


# ── BRIDGE-003 ────────────────────────────────────────────────────────────────

def test_bridge_003_certified_bound_token():
    """BRIDGE-003: CertifiedBoundToken with certified_approximate_inference → AEX.

    CertifiedBoundToken bounds: approximation_gap, certifier_soundness_gap, bound_scope_gap.
    AEX for certified_approximate_inference requires all three bounded → satisfied.
    """
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="certified_approximate",
        tokens=[_certified_bound_token()],
        claim_class="certified_approximate_inference",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    assert result.permission() == "AEX"


# ── BRIDGE-004 ────────────────────────────────────────────────────────────────

def test_bridge_004_model_identity_token_only():
    """BRIDGE-004: ModelIdentityToken alone → DIA.

    ModelIdentityToken closes model_identity_gap and evidence_identity_gap,
    but query_identity_gap stays OPEN.  REV requires all three identity gaps
    bounded — so the permission stays at DIA.
    """
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[_model_identity_token()],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    assert result.permission() == "DIA"


# ── BRIDGE-005 ────────────────────────────────────────────────────────────────

def test_bridge_005_no_tokens():
    """BRIDGE-005: No tokens → DIA.

    All 10 gaps remain OPEN.  DIA is the floor for in-class specs.
    """
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    assert result.permission() == "DIA"


# ── BRIDGE-006 ────────────────────────────────────────────────────────────────

def test_bridge_006_ooc_spec():
    """BRIDGE-006: Spec missing required runtime keys → OOC.

    An empty runtime dict fails the class predicate.  Membership.OutOfClassExact
    is set on the ProofContext, which forces OOC regardless of tokens.
    """
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[],
        claim_class="exact_inference_result",
        runtime={},  # missing all 5 required keys
        authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    assert result.permission() == "OOC"


# ── BRIDGE-007 ────────────────────────────────────────────────────────────────

def test_bridge_007_revoked_token():
    """BRIDGE-007: Revoked ExactInferenceToken must not promote above DIA.

    A REVOKED token is passed to noethers-turnstile with status="revoked" and empty
    closes_gaps/bounds_gaps.  The token is recorded in the derivation but
    cannot close any gap — permission stays at DIA.
    """
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[_exact_token(status="REVOKED")],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    assert result.permission() == "DIA"


# ── BRIDGE-008 ────────────────────────────────────────────────────────────────

def test_bridge_008_authority_ceiling_cap():
    """BRIDGE-008: Full token set earns ALR; ceiling=REV caps it at REV.

    noethers_turnstile.ProofContext.authority_ceiling is a hard cap applied at the
    end of compilation.  Even with all gaps satisfied for ALR, the result
    is the meet(ALR, REV) = REV.
    """
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[_exact_token(), _freshness_token()],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="REV", issued_at=_NOW, ttl_seconds=None,
    )
    assert result.permission() == "REV"


# ── BRIDGE-009 ────────────────────────────────────────────────────────────────

def test_bridge_009_uncertified_approximate_capped_at_rev():
    """BRIDGE-009: uncertified_approximate_inference is always capped at REV.

    ExactInferenceToken fingerprint uses algorithm="uncertified_approximate"
    to match the spec.  Closes all identity + approximation gaps.
    But uncertified_approximate_inference has no AEX/ALR profiles — REV is max.
    """
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="uncertified_approximate",
        tokens=[ExactInferenceToken(
            proof_token_id=str(uuid.uuid4()),
            token_type="ExactInferenceToken",
            status="VALID",
            issuer="test-issuer",
            graph_fingerprint=fingerprint_graph(_GRAPH),
            query_fingerprint=fingerprint_query(_QUERY),
            evidence_fingerprint=fingerprint_evidence(_EVIDENCE),
            algorithm_fingerprint=fingerprint("uncertified_approximate"),
        )],
        claim_class="uncertified_approximate_inference",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    assert result.permission() == "REV"


# ── BRIDGE-010 ────────────────────────────────────────────────────────────────

def test_bridge_010_compose_non_promotion():
    """BRIDGE-010: compose() non-promotion — composed permission ≤ min(a, b).

    Context A: ExactInferenceToken → AEX.
    Context B: FreshnessToken alone → DIA (freshness closes one gap, not enough for AEX).

    After compose(A, B), B's tokens have A's claim_id in the provenance hash,
    so B's FreshnessToken is rejected (mismatch).  Composed result ≤ min(AEX, DIA).
    The non-promotion guarantee must hold: composed ≤ meet(perm_a, perm_b).
    """
    from bridge.bridge import _build_profiles, _translate_token
    from bridge.fingerprints import fingerprint_evidence

    fp_graph = fingerprint_graph(_GRAPH)
    fp_query = fingerprint_query(_QUERY)
    fp_evidence = fingerprint_evidence(_EVIDENCE)
    fp_algorithm = fingerprint("exact")
    allowed_use = "exact_inference_result"
    context_id = fp_evidence
    issued_at_unix = _NOW.timestamp()

    def _make_ctx(extra_tokens, suffix=""):
        claim_id = fp_graph + suffix
        prov_hash = t.compute_provenance_hash(claim_id, fp_query, context_id, allowed_use)
        ts_tokens = [
            _translate_token(tok, prov_hash, fp_graph, fp_query, fp_evidence, fp_algorithm, issued_at_unix)
            for tok in extra_tokens
        ]
        return t.ProofContext(
            claim_id=claim_id,
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

    rt = t.RuntimeContext(now_unix=_NOW.timestamp(), context_fingerprint=context_id)
    ctx_a = _make_ctx([_exact_token()])
    ctx_b = _make_ctx([_freshness_token()])

    perm_a = t.Permission.from_str(t.compile(ctx_a).permission_str(rt))
    perm_b = t.Permission.from_str(t.compile(ctx_b).permission_str(rt))

    composed = t.compose(ctx_a, ctx_b)
    perm_composed = t.Permission.from_str(t.compile(composed).permission_str(rt))

    assert perm_composed <= perm_a.meet(perm_b), (
        f"Non-promotion violated: composed={perm_composed} "
        f"perm_a={perm_a} perm_b={perm_b}"
    )
