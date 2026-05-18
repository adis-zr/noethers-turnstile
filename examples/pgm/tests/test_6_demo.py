"""Tests for demo/tokens.py — the translation layer from InferenceResult to ProofTokens.

Uses a tiny 3-variable model constructed directly (no BIF file required).
This covers the only genuinely new code in the demo.
"""
from __future__ import annotations

import math
import time
import uuid
from unittest.mock import MagicMock

import turnstile as t

from bridge.fingerprints import fingerprint, fingerprint_evidence, fingerprint_graph, fingerprint_query
from demo.tokens import cert_to_proof_tokens, claim_class_for_geometry


# ── Shared fixtures ───────────────────────────────────────────────────────────

_FP_GRAPH    = fingerprint_graph({"variables": {"A": [0, 1], "B": [0, 1]}, "factors": []})
_FP_QUERY    = fingerprint_query({"target": "A", "type": "marginal"})
_FP_EVIDENCE = fingerprint_evidence({})
_FP_ALGO_EXACT  = fingerprint("exact")
_FP_ALGO_HILBERT = fingerprint("hilbert")
_CONTEXT_ID  = _FP_EVIDENCE
_ISSUED_AT   = time.time()


def _make_result(geometry: str, kl: float = 0.0):
    r = MagicMock()
    r.certificate_geometry = geometry
    r.certified_kl = kl
    return r


def _prov_hash(claim_class: str) -> str:
    return t.compute_provenance_hash(_FP_GRAPH, _FP_QUERY, _CONTEXT_ID, claim_class)


# ── DEMO6-001: claim_class_for_geometry ──────────────────────────────────────

def test_demo6_001_claim_class_exact():
    assert claim_class_for_geometry("exact") == "exact_inference_result"


def test_demo6_001_claim_class_hilbert():
    assert claim_class_for_geometry("hilbert") == "certified_approximate_inference"


def test_demo6_001_claim_class_infinite():
    assert claim_class_for_geometry("infinite") == "certified_approximate_inference"


def test_demo6_001_claim_class_fkkl():
    assert claim_class_for_geometry("fkkl") == "certified_approximate_inference"


# ── DEMO6-002: exact geometry token coverage ──────────────────────────────────

def test_demo6_002_exact_geometry_closes_five_gaps():
    """exact geometry → ExactInferenceToken closes 5 gaps + FreshnessToken closes freshness_gap."""
    result = _make_result("exact", kl=0.0)
    prov = _prov_hash("exact_inference_result")
    tokens = cert_to_proof_tokens(result, _FP_GRAPH, _FP_QUERY, _FP_EVIDENCE, _FP_ALGO_EXACT, prov, _ISSUED_AT)

    assert len(tokens) == 2
    exact_tok = next(tok for tok in tokens if tok.token_type == "ExactInferenceToken")
    fresh_tok = next(tok for tok in tokens if tok.token_type == "FreshnessToken")

    assert set(exact_tok.closes_gaps) == {
        "approximation_gap",
        "model_identity_gap",
        "query_identity_gap",
        "evidence_identity_gap",
        "algorithm_reproducibility_gap",
    }
    assert exact_tok.bounds_gaps == []
    assert exact_tok.status == "valid"

    assert fresh_tok.closes_gaps == ["freshness_gap"]
    assert fresh_tok.bounds_gaps == []
    assert fresh_tok.status == "valid"


# ── DEMO6-003: hilbert geometry token coverage ────────────────────────────────

def test_demo6_003_hilbert_geometry_bounds_two_gaps():
    """hilbert geometry → CertifiedBoundToken closes bound_scope_gap, bounds 2 gaps."""
    result = _make_result("hilbert", kl=2.77)
    prov = _prov_hash("certified_approximate_inference")
    tokens = cert_to_proof_tokens(result, _FP_GRAPH, _FP_QUERY, _FP_EVIDENCE, _FP_ALGO_HILBERT, prov, _ISSUED_AT)

    assert len(tokens) == 2
    bound_tok = next(tok for tok in tokens if tok.token_type == "CertifiedBoundToken")
    fresh_tok = next(tok for tok in tokens if tok.token_type == "FreshnessToken")

    assert bound_tok.closes_gaps == ["bound_scope_gap"]
    assert set(bound_tok.bounds_gaps) == {"approximation_gap", "certifier_soundness_gap"}
    assert bound_tok.status == "valid"

    assert fresh_tok.closes_gaps == ["freshness_gap"]


# ── DEMO6-004: infinite geometry token coverage ───────────────────────────────

def test_demo6_004_infinite_geometry_no_gaps():
    """infinite geometry → InfiniteCertToken with empty gap lists, status=invalid, no freshness."""
    result = _make_result("infinite", kl=math.inf)
    prov = _prov_hash("certified_approximate_inference")
    tokens = cert_to_proof_tokens(result, _FP_GRAPH, _FP_QUERY, _FP_EVIDENCE, _FP_ALGO_HILBERT, prov, _ISSUED_AT)

    assert len(tokens) == 1
    tok = tokens[0]
    assert tok.token_type == "InfiniteCertToken"
    assert tok.closes_gaps == []
    assert tok.bounds_gaps == []
    assert tok.status == "invalid"

    # No freshness token for infinite geometry
    types = [t.token_type for t in tokens]
    assert "FreshnessToken" not in types


# ── DEMO6-005: provenance hash is threaded through ────────────────────────────

def test_demo6_005_provenance_hash_threaded():
    """All tokens in the list carry the same provenance_hash."""
    result = _make_result("exact", kl=0.0)
    prov = _prov_hash("exact_inference_result")
    tokens = cert_to_proof_tokens(result, _FP_GRAPH, _FP_QUERY, _FP_EVIDENCE, _FP_ALGO_EXACT, prov, _ISSUED_AT)

    for tok in tokens:
        assert tok.provenance_hash == prov


# ── DEMO6-006: unique token IDs ───────────────────────────────────────────────

def test_demo6_006_unique_token_ids():
    """Each call produces tokens with unique IDs."""
    result = _make_result("exact", kl=0.0)
    prov = _prov_hash("exact_inference_result")
    tokens_a = cert_to_proof_tokens(result, _FP_GRAPH, _FP_QUERY, _FP_EVIDENCE, _FP_ALGO_EXACT, prov, _ISSUED_AT)
    tokens_b = cert_to_proof_tokens(result, _FP_GRAPH, _FP_QUERY, _FP_EVIDENCE, _FP_ALGO_EXACT, prov, _ISSUED_AT)

    ids_a = {tok.token_id for tok in tokens_a}
    ids_b = {tok.token_id for tok in tokens_b}
    assert ids_a.isdisjoint(ids_b), "Token IDs should be unique across calls"
