"""PY-009 — Python binding for permission chain parameterization.

Verifies the Python surface for PermissionChain, ChainRole, ChainHash,
InMemoryChainRegistry, verify_published, and compile(chain=...).
"""
from __future__ import annotations

import time

import noethers_turnstile as t
import pytest


def _paper_5() -> t.PermissionChain:
    return t.PermissionChain.new(
        levels=["REF", "DIA", "REV", "AEX", "ALR"],
        roles={
            t.ChainRole.Bottom: 0,
            t.ChainRole.ExpiryFloor: 0,
            t.ChainRole.Refused: 0,
            t.ChainRole.Unsatisfied: 0,
            t.ChainRole.DisallowedUsesCeiling: 0,
            t.ChainRole.BlockerThreshold: 1,
            t.ChainRole.Top: 4,
        },
    )


def _simple_ctx(chain: t.PermissionChain, profile_perm: t.Permission, fp: str = "fp"):
    hash_ = t.compute_provenance_hash("c", "z", "ctx", "use")
    return t.ProofContext(
        claim_id="c",
        candidate_id="z",
        context_id="ctx",
        context_fingerprint=fp,
        allowed_use="use",
        membership=t.Membership.InClass,
        authority_ceiling=chain.role(t.ChainRole.Top),
        expiry=t.Expiry.never(),
        gaps=[t.GapRecord(gap_id="g1", gap_type="t", status="closed")],
        profiles=[
            t.Profile(
                profile_perm,
                [t.GapRequirement(gap_id="g1", minimum_status="closed")],
            )
        ],
        tokens=[
            t.ProofToken(
                token_id="tok",
                token_type="T",
                schema_version="0.1",
                status="valid",
                closes_gaps=["g1"],
                bounds_gaps=[],
                provenance_hash=hash_,
                issued_at=time.time(),
                issuer="test",
            )
        ],
    )


# ── Chain construction ────────────────────────────────────────────────────────


def test_default_chain_has_12_levels():
    c = t.PermissionChain.default_chain()
    assert len(c) == 12
    assert c.role(t.ChainRole.Bottom).as_str() == "OOC"
    assert c.role(t.ChainRole.Top).as_str() == "AAA"


def test_custom_chain_constructs_and_validates():
    c = _paper_5()
    assert len(c) == 5
    assert c.role(t.ChainRole.Bottom).as_str() == "REF"
    assert c.role(t.ChainRole.BlockerThreshold).as_str() == "DIA"
    assert c.role(t.ChainRole.Top).as_str() == "ALR"
    assert c.role(t.ChainRole.DisallowedUsesCeiling).as_str() == "REF"


def test_invalid_chain_rejected():
    # Bottom not at index 0 — violates L5.
    with pytest.raises(t.ChainError):
        t.PermissionChain.new(
            levels=["A", "B", "C"],
            roles={
                t.ChainRole.Bottom: 1,
                t.ChainRole.ExpiryFloor: 1,
                t.ChainRole.Refused: 1,
                t.ChainRole.Unsatisfied: 1,
                t.ChainRole.DisallowedUsesCeiling: 1,
                t.ChainRole.BlockerThreshold: 2,
                t.ChainRole.Top: 2,
            },
        )


def test_too_few_levels_rejected():
    with pytest.raises(t.ChainError):
        t.PermissionChain.new(
            levels=["ONLY"],
            roles={
                t.ChainRole.Bottom: 0,
                t.ChainRole.ExpiryFloor: 0,
                t.ChainRole.Refused: 0,
                t.ChainRole.Unsatisfied: 0,
                t.ChainRole.DisallowedUsesCeiling: 0,
                t.ChainRole.BlockerThreshold: 0,
                t.ChainRole.Top: 0,
            },
        )


# ── compile with chain ─────────────────────────────────────────────────────────


def test_compile_without_chain_uses_default_and_stamps_hash():
    c = t.PermissionChain.default_chain()
    ctx = _simple_ctx(c, t.Permission.DIA)
    j = t.compile_static(ctx)
    assert j.chain_hash == c.chain_hash()
    assert j.permission.as_str() == "DIA"


def test_compile_with_custom_chain_emits_domain_level():
    c = _paper_5()
    ctx = _simple_ctx(c, c.parse("REV"))
    j = t.compile_static(ctx, chain=c)
    assert j.permission.as_str() == "REV"
    assert j.chain_hash == c.chain_hash()


def test_judgment_chain_hash_differs_across_chains():
    c1 = t.PermissionChain.default_chain()
    c2 = _paper_5()
    ctx_default = _simple_ctx(c1, t.Permission.DIA)
    ctx_custom = _simple_ctx(c2, c2.parse("REV"))
    j1 = t.compile_static(ctx_default)
    j2 = t.compile_static(ctx_custom, chain=c2)
    assert j1.chain_hash != j2.chain_hash


# ── chain registry / verify_published ──────────────────────────────────────────


def test_registry_smoke_unpublished_fails_then_published_passes():
    c = _paper_5()
    ctx = _simple_ctx(c, c.parse("DIA"))
    j = t.compile_static(ctx, chain=c)

    reg = t.InMemoryChainRegistry()
    assert len(reg) == 0
    with pytest.raises(t.AuditError):
        t.verify_published(j, reg)

    h = reg.publish(c)
    assert h == c.chain_hash()
    assert len(reg) == 1
    # Now passes.
    t.verify_published(j, reg)


def test_chain_hash_hex_round_trip():
    c = t.PermissionChain.default_chain()
    h = c.chain_hash()
    h2 = t.ChainHash.from_hex(h.to_hex())
    assert h == h2
    assert str(h) == h.to_hex()
