"""Shared fixtures for the turnstile Python integration test suite."""

import time
import pytest
import noethers_turnstile as t


# ── Helpers ────────────────────────────────────────────────────────────────────

def provenance_hash_for(**kwargs) -> str:
    return t.compute_provenance_hash(
        kwargs["claim_id"],
        kwargs["candidate_id"],
        kwargs["context_id"],
        kwargs["allowed_use"],
    )


def make_ctx(
    *,
    claim_id: str = "claim-py",
    candidate_id: str = "z-py",
    context_id: str = "ctx-py",
    allowed_use: str = "py-use",
    gaps=None,
    profiles=None,
    tokens=None,
    expiry=None,
    authority_ceiling=None,
    membership=None,
    context_fingerprint: str | None = None,
) -> t.ProofContext:
    kwargs = dict(
        claim_id=claim_id,
        candidate_id=candidate_id,
        context_id=context_id,
        allowed_use=allowed_use,
        membership=membership if membership is not None else t.Membership.InClass,
        authority_ceiling=authority_ceiling if authority_ceiling is not None else t.Permission.AAA,
        expiry=expiry if expiry is not None else t.Expiry.never(),
    )
    if gaps is not None:
        kwargs["gaps"] = gaps
    if profiles is not None:
        kwargs["profiles"] = profiles
    if tokens is not None:
        kwargs["tokens"] = tokens
    if context_fingerprint is not None:
        kwargs["context_fingerprint"] = context_fingerprint
    return t.ProofContext(**kwargs)


def closing_token(
    *,
    ctx: t.ProofContext,
    token_id: str = "tok-1",
    expires_at: float | None = None,
    status: str = "valid",
) -> t.ProofToken:
    h = t.compute_provenance_hash(
        ctx.claim_id, ctx.candidate_id, ctx.context_id, ctx.allowed_use
    )
    kwargs = dict(
        token_id=token_id,
        token_type="CLOSE",
        schema_version="0.1",
        status=status,
        closes_gaps=["g1"],
        bounds_gaps=[],
        provenance_hash=h,
        issued_at=time.time() - 3600,
        issuer="test",
    )
    if expires_at is not None:
        kwargs["expires_at"] = expires_at
    return t.ProofToken(**kwargs)


def make_dia_ctx(suffix: str = "1") -> t.ProofContext:
    """Return a ProofContext with one gap, one profile, one valid closing token."""
    placeholder = make_ctx(
        claim_id=f"claim-{suffix}",
        candidate_id=f"z-{suffix}",
        context_id=f"ctx-{suffix}",
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
    )
    tok = closing_token(ctx=placeholder)
    return make_ctx(
        claim_id=f"claim-{suffix}",
        candidate_id=f"z-{suffix}",
        context_id=f"ctx-{suffix}",
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
        tokens=[tok],
    )


@pytest.fixture
def now() -> float:
    return time.time()


@pytest.fixture
def rt(now) -> t.RuntimeContext:
    return t.RuntimeContext(now_unix=now, context_fingerprint="ctx-py")
