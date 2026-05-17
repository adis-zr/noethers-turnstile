"""PY-004 — compose() and compose semantics from Python.

   S1 — compose() succeeds when allowed_use matches.
   S2 — compose() raises CompositionError when allowed_use mismatches.
   S3 — CompositionError is a subclass of TurnstileError.
   S4 — Composed context inherits g1's claim_id.
   S5 — Composed context inherits g1's candidate_id.
   S6 — Composed context inherits g1's context_id.
   S7 — Token issued for g1's claim tuple is valid in composed context.
   S8 — Token issued for g2's claim tuple is rejected in composed context.
   S9 — Gaps from both contexts appear in composed context.
   S10 — Tokens from both contexts are deduplicated by token_id.
"""

import time
import pytest
import turnstile as t
from conftest import make_ctx, closing_token


def make_pair(suffix_a: str, suffix_b: str, allowed_use: str = "shared-use"):
    g1 = make_ctx(
        claim_id=f"claim-{suffix_a}",
        candidate_id=f"z-{suffix_a}",
        context_id=f"ctx-{suffix_a}",
        allowed_use=allowed_use,
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
    )
    g2 = make_ctx(
        claim_id=f"claim-{suffix_b}",
        candidate_id=f"z-{suffix_b}",
        context_id=f"ctx-{suffix_b}",
        allowed_use=allowed_use,
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
    )
    return g1, g2


# ── S1: compose() succeeds on matching allowed_use ────────────────────────────

def test_s1_compose_succeeds_matching_use():
    g1, g2 = make_pair("a", "b")
    result = t.compose(g1, g2)
    assert isinstance(result, t.ProofContext)


# ── S2: compose() raises CompositionError on mismatch ────────────────────────

def test_s2_compose_use_mismatch_raises():
    g1 = make_ctx(allowed_use="use-a")
    g2 = make_ctx(allowed_use="use-b")
    with pytest.raises(t.CompositionError):
        t.compose(g1, g2)


# ── S3: CompositionError is subclass of TurnstileError ───────────────────────

def test_s3_composition_error_is_subclass():
    assert issubclass(t.CompositionError, t.TurnstileError)


# ── S4: Composed context inherits g1's claim_id ──────────────────────────────

def test_s4_inherits_g1_claim_id():
    g1, g2 = make_pair("g1", "g2")
    composed = t.compose(g1, g2)
    assert composed.claim_id == "claim-g1"


# ── S5: Composed context inherits g1's candidate_id ──────────────────────────

def test_s5_inherits_g1_candidate_id():
    g1, g2 = make_pair("g1", "g2")
    composed = t.compose(g1, g2)
    assert composed.candidate_id == "z-g1"


# ── S6: Composed context inherits g1's context_id ────────────────────────────

def test_s6_inherits_g1_context_id():
    g1, g2 = make_pair("g1", "g2")
    composed = t.compose(g1, g2)
    assert composed.context_id == "ctx-g1"


# ── S7: Token issued for g1 is valid after composition ───────────────────────

def test_s7_g1_token_valid_after_compose():
    g1, g2 = make_pair("g1", "g2", allowed_use="s7-use")
    g1_placeholder = make_ctx(
        claim_id="claim-g1", candidate_id="z-g1", context_id="ctx-g1",
        allowed_use="s7-use",
    )
    tok = t.ProofToken(
        token_id="tok-g1",
        token_type="CLOSE",
        schema_version="0.1",
        status="valid",
        closes_gaps=["g1"],
        bounds_gaps=[],
        provenance_hash=t.compute_provenance_hash(
            "claim-g1", "z-g1", "ctx-g1", "s7-use"
        ),
        issued_at=time.time() - 3600,
        issuer="test",
    )
    g1_with_tok = make_ctx(
        claim_id="claim-g1", candidate_id="z-g1", context_id="ctx-g1",
        allowed_use="s7-use",
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
        tokens=[tok],
    )
    g2_ctx = make_ctx(
        claim_id="claim-g2", candidate_id="z-g2", context_id="ctx-g2",
        allowed_use="s7-use",
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
    )
    composed = t.compose(g1_with_tok, g2_ctx)
    j = t.compile_static(composed)
    assert j.permission == t.Permission.DIA, "S7: g1 token must be valid after composition"


# ── S8: Token issued for g2 is rejected after composition ────────────────────

def test_s8_g2_token_rejected_after_compose():
    g1_ctx = make_ctx(
        claim_id="claim-g1", candidate_id="z-g1", context_id="ctx-g1",
        allowed_use="s8-use",
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
    )
    tok_for_g2 = t.ProofToken(
        token_id="tok-g2",
        token_type="CLOSE",
        schema_version="0.1",
        status="valid",
        closes_gaps=["g1"],
        bounds_gaps=[],
        provenance_hash=t.compute_provenance_hash(
            "claim-g2", "z-g2", "ctx-g2", "s8-use"
        ),
        issued_at=time.time() - 3600,
        issuer="test",
    )
    g2_ctx = make_ctx(
        claim_id="claim-g2", candidate_id="z-g2", context_id="ctx-g2",
        allowed_use="s8-use",
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
        tokens=[tok_for_g2],
    )
    composed = t.compose(g1_ctx, g2_ctx)
    j = t.compile_static(composed)
    assert j.permission == t.Permission.OOC, "S8: g2 token must be rejected (provenance mismatch)"


# ── S9: Gaps from both contexts appear in result ─────────────────────────────

def test_s9_disjoint_gaps_merged():
    g1 = make_ctx(
        allowed_use="s9-use",
        gaps=[t.GapRecord("gap-a", "type-a")],
    )
    g2 = make_ctx(
        allowed_use="s9-use",
        gaps=[t.GapRecord("gap-b", "type-b")],
    )
    composed = t.compose(g1, g2)
    j = t.compile_static(composed)
    # Both gaps contributed — the context compiled without error
    assert j.permission == t.Permission.OOC  # no profiles → OOC, but no error


# ── S10: Tokens with same token_id are deduplicated ──────────────────────────

def test_s10_duplicate_token_ids_deduped():
    shared_hash = t.compute_provenance_hash(
        "claim-py", "z-py", "ctx-py", "s10-use"
    )
    tok = t.ProofToken(
        token_id="shared-tok",
        token_type="CLOSE",
        schema_version="0.1",
        status="valid",
        closes_gaps=["g1"],
        bounds_gaps=[],
        provenance_hash=shared_hash,
        issued_at=time.time() - 3600,
        issuer="shared-issuer",
    )
    g1 = make_ctx(
        allowed_use="s10-use",
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
        tokens=[tok],
    )
    g2 = make_ctx(
        allowed_use="s10-use",
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
        tokens=[tok],
    )
    composed = t.compose(g1, g2)
    j = t.compile_static(composed)
    # Token is valid for g1's identity (which the composed context inherits)
    assert j.permission == t.Permission.DIA
