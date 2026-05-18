"""Narrative demo tests (DEMO-001 through DEMO-004).

Run with `pytest tests/test_2_demo.py -v -s` to see the printed output.

These tests serve as executable documentation — they show exactly what the
compiler does at each step, making it easy to understand how turnstile works
when integrated with a real domain.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import turnstile as t

from bridge import (
    ExactInferenceToken,
    FreshnessToken,
    compile_pgm,
    fingerprint,
    fingerprint_evidence,
    fingerprint_graph,
    fingerprint_query,
)
from bridge.bridge import _build_profiles, _translate_token
from bridge.claims import GAP_BASIS

_NOW = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)

_GRAPH = {
    "variables": {"A": [0, 1], "B": [0, 1], "C": [0, 1]},
    "factors": [
        {"scope": ["A", "B"], "table": [0.3, 0.7, 0.6, 0.4]},
        {"scope": ["B", "C"], "table": [0.8, 0.2, 0.1, 0.9]},
    ],
}
_QUERY = {"target": "A", "type": "marginal"}
_EVIDENCE = {"C": 0}
_RUNTIME = {
    "graph_version": "v1",
    "evidence_version": "v1",
    "certifier_registry_version": "v1",
    "algorithm_implementation_fingerprint": "demo001",
    "token_registry_version": "v1",
}


def _print_derivation(label: str, result) -> None:
    j = t.compile_static(result.ctx)
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    print(f"  claim_id:        {result.ctx.claim_id[:16]}...")
    print(f"  candidate_id:    {result.ctx.candidate_id[:16]}...")
    print(f"  allowed_use:     {result.ctx.allowed_use}")
    print(f"  provenance_hash: {result.ctx.provenance_hash()[:16]}...")
    print(f"  FINAL PERMISSION: {j.permission}")


# ── DEMO-001 ──────────────────────────────────────────────────────────────────

def test_demo_001_full_derivation_walkthrough():
    """DEMO-001: Full derivation walkthrough — ExactInferenceToken + FreshnessToken → AEX.

    Shows every compilation step printed to stdout.

    AEX (not ALR) is the ceiling: ALR now requires model_specification_gap BOUNDED,
    which ExactInferenceToken does not provide.  The result proves the computation
    is correct but not that the model is adequate for the real-world target.
    """
    exact_tok = ExactInferenceToken(
        proof_token_id="tok-exact-001",
        token_type="ExactInferenceToken",
        status="VALID",
        issuer="demo-issuer",
        graph_fingerprint=fingerprint_graph(_GRAPH),
        query_fingerprint=fingerprint_query(_QUERY),
        evidence_fingerprint=fingerprint_evidence(_EVIDENCE),
        algorithm_fingerprint=fingerprint("exact"),
    )
    fresh_tok = FreshnessToken(
        proof_token_id="tok-fresh-001",
        token_type="FreshnessToken",
        status="VALID",
        issuer="demo-issuer",
        graph_fingerprint=fingerprint_graph(_GRAPH),
        query_fingerprint=fingerprint_query(_QUERY),
        evidence_fingerprint=fingerprint_evidence(_EVIDENCE),
    )
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[exact_tok, fresh_tok],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    _print_derivation("DEMO-001: Full derivation (ExactInference + Freshness → AEX)", result)
    assert result.permission() == "AEX"


# ── DEMO-002 ──────────────────────────────────────────────────────────────────

def test_demo_002_revoked_token_derivation():
    """DEMO-002: Revoked token derivation — shows token rejected, permission stays DIA.

    Even though the token would close 5 gaps if valid, REVOKED means it is
    passed with empty closes_gaps/bounds_gaps.  The derivation records the
    token as seen but the gaps never advance.
    """
    revoked_tok = ExactInferenceToken(
        proof_token_id="tok-revoked-001",
        token_type="ExactInferenceToken",
        status="REVOKED",
        issuer="demo-issuer",
        graph_fingerprint=fingerprint_graph(_GRAPH),
        query_fingerprint=fingerprint_query(_QUERY),
        evidence_fingerprint=fingerprint_evidence(_EVIDENCE),
        algorithm_fingerprint=fingerprint("exact"),
    )
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[revoked_tok],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW, ttl_seconds=None,
    )
    _print_derivation("DEMO-002: Revoked token (permission stays DIA)", result)
    assert result.permission() == "DIA"


# ── DEMO-003 ──────────────────────────────────────────────────────────────────

def test_demo_003_ceiling_enforcement():
    """DEMO-003: Authority ceiling enforcement — full evidence earns ALR, ceiling caps at REV.

    The derivation shows the permission reaching ALR after token evaluation,
    then being capped to REV by the authority_ceiling constraint.
    """
    exact_tok = ExactInferenceToken(
        proof_token_id="tok-exact-003",
        token_type="ExactInferenceToken",
        status="VALID",
        issuer="demo-issuer",
        graph_fingerprint=fingerprint_graph(_GRAPH),
        query_fingerprint=fingerprint_query(_QUERY),
        evidence_fingerprint=fingerprint_evidence(_EVIDENCE),
        algorithm_fingerprint=fingerprint("exact"),
    )
    fresh_tok = FreshnessToken(
        proof_token_id="tok-fresh-003",
        token_type="FreshnessToken",
        status="VALID",
        issuer="demo-issuer",
        graph_fingerprint=fingerprint_graph(_GRAPH),
        query_fingerprint=fingerprint_query(_QUERY),
        evidence_fingerprint=fingerprint_evidence(_EVIDENCE),
    )
    result = compile_pgm(
        graph=_GRAPH, query=_QUERY, evidence=_EVIDENCE,
        algorithm="exact", tokens=[exact_tok, fresh_tok],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="REV",  # cap at REV
        issued_at=_NOW, ttl_seconds=None,
    )
    _print_derivation("DEMO-003: Ceiling enforcement (ALR evidence → capped at REV)", result)
    assert result.permission() == "REV"


# ── DEMO-004 ──────────────────────────────────────────────────────────────────

def test_demo_004_composition_walkthrough():
    """DEMO-004: Composition walkthrough — non-upgrade guarantee illustrated.

    Context A has an ExactInferenceToken → AEX.
    Context B has a FreshnessToken → DIA (freshness alone is not enough for AEX).

    compose(A, B) produces a merged context where B's token carries A's provenance
    hash (A's claim_id).  Since B's token was issued against B's claim_id (-B suffix),
    its provenance hash doesn't match A's — turnstile rejects it.

    The composed result matches A's individual result (AEX), because A's tokens
    are still valid in the composed context.  The non-upgrade property holds:
    composed permission ≤ max(perm_a, perm_b) — composition cannot exceed the
    strongest individual context.
    """
    fp_graph = fingerprint_graph(_GRAPH)
    fp_query = fingerprint_query(_QUERY)
    fp_evidence = fingerprint_evidence(_EVIDENCE)
    fp_algo = fingerprint("exact")
    context_id = fp_evidence
    allowed_use = "exact_inference_result"
    issued_at_unix = _NOW.timestamp()

    def _make_ctx(toks, suffix=""):
        claim_id = fp_graph + suffix
        prov_hash = t.compute_provenance_hash(claim_id, fp_query, context_id, allowed_use)
        ts_tokens = [
            _translate_token(tok, prov_hash, fp_graph, fp_query, fp_evidence, fp_algo, issued_at_unix)
            for tok in toks
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

    exact_tok = ExactInferenceToken(
        proof_token_id="tok-exact-A", token_type="ExactInferenceToken", status="VALID",
        issuer="demo", graph_fingerprint=fp_graph, query_fingerprint=fp_query,
        evidence_fingerprint=fp_evidence, algorithm_fingerprint=fp_algo,
    )
    fresh_tok = FreshnessToken(
        proof_token_id="tok-fresh-B", token_type="FreshnessToken", status="VALID",
        issuer="demo", graph_fingerprint=fp_graph, query_fingerprint=fp_query,
        evidence_fingerprint=fp_evidence,
    )

    ctx_a = _make_ctx([exact_tok], suffix="-A")
    ctx_b = _make_ctx([fresh_tok], suffix="-B")

    perm_a_str = t.compile(ctx_a).permission_str(rt)
    perm_b_str = t.compile(ctx_b).permission_str(rt)

    composed = t.compose(ctx_a, ctx_b)
    j_composed = t.compile_static(composed)
    # compose() sets context_fingerprint = "<a_fp>+<b_fp>" — use it for LiveJudgment check
    composed_fp = f"{context_id}+{context_id}"
    rt_composed = t.RuntimeContext(now_unix=_NOW.timestamp(), context_fingerprint=composed_fp)
    perm_composed_str = t.compile(composed).permission_str(rt_composed)

    print(f"\n{'=' * 60}")
    print(f"  DEMO-004: Composition walkthrough")
    print(f"{'=' * 60}")
    print(f"  Context A (ExactInferenceToken): permission = {perm_a_str}")
    print(f"  Context B (FreshnessToken):      permission = {perm_b_str}")
    print(f"  Composed permission: {perm_composed_str}")
    print(f"  Composed static:     {j_composed.permission}")
    print(f"  Non-upgrade: {perm_composed_str} ≤ max({perm_a_str}, {perm_b_str})")

    p_a = t.Permission.from_str(perm_a_str)
    p_b = t.Permission.from_str(perm_b_str)
    p_composed = t.Permission.from_str(perm_composed_str)
    # Non-upgrade: composition can't exceed the strongest individual context
    p_max = p_a if p_a >= p_b else p_b
    assert p_composed <= p_max, f"Non-upgrade violated: {p_composed} > max({p_a}, {p_b})"
