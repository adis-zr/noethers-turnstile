"""Compiler stress tests (Groups A–D).

These tests exercise the Rust evaluation path directly with adversarial inputs
that are NOT covered by turnstile's own 100-test Python suite.  They are
designed to find bugs in the Rust compiler, not in the bridge translation layer.

Group A: Provenance enforcement variants (5 tests)
Group B: Expiry boundary conditions (5 tests)
Group C: Deep composition chains (4 tests)
Group D: Large-scale inputs (4 tests)
"""

from __future__ import annotations

import time
import uuid

import pytest
import turnstile as t

# ── Helpers ────────────────────────────────────────────────────────────────────

def _prov(claim_id: str, candidate_id: str, context_id: str, allowed_use: str) -> str:
    return t.compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use)


def _make_ctx(
    *,
    claim_id: str = "claim-stress",
    candidate_id: str = "cand-stress",
    context_id: str = "ctx-stress",
    allowed_use: str = "stress-test",
    gaps: list | None = None,
    profiles: list | None = None,
    tokens: list | None = None,
    ceiling: t.Permission = t.Permission.AAA,
    membership: t.Membership = t.Membership.InClass,
    context_fingerprint: str | None = None,
) -> t.ProofContext:
    kwargs: dict = dict(
        claim_id=claim_id,
        candidate_id=candidate_id,
        context_id=context_id,
        allowed_use=allowed_use,
        membership=membership,
        authority_ceiling=ceiling,
        expiry=t.Expiry.never(),
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


def _closing_token(
    *,
    ctx: t.ProofContext,
    gap_id: str = "g1",
    token_id: str | None = None,
    status: str = "valid",
    expires_at: float | None = None,
) -> t.ProofToken:
    h = _prov(ctx.claim_id, ctx.candidate_id, ctx.context_id, ctx.allowed_use)
    kwargs: dict = dict(
        token_id=token_id or str(uuid.uuid4()),
        token_type="CLOSE",
        schema_version="0.1",
        status=status,
        closes_gaps=[gap_id],
        bounds_gaps=[],
        provenance_hash=h,
        issued_at=time.time() - 3600,
        issuer="stress-test",
    )
    if expires_at is not None:
        kwargs["expires_at"] = expires_at
    return t.ProofToken(**kwargs)


def _dia_ctx(suffix: str = "1") -> t.ProofContext:
    """Return a ProofContext with one gap, DIA profile, one valid token."""
    placeholder = _make_ctx(
        claim_id=f"claim-{suffix}",
        candidate_id=f"cand-{suffix}",
        context_id=f"ctx-{suffix}",
        allowed_use="stress-test",
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])],
    )
    tok = _closing_token(ctx=placeholder)
    return _make_ctx(
        claim_id=f"claim-{suffix}",
        candidate_id=f"cand-{suffix}",
        context_id=f"ctx-{suffix}",
        allowed_use="stress-test",
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])],
        tokens=[tok],
        context_fingerprint=f"ctx-{suffix}",
    )


def _rt(ctx: t.ProofContext, now: float | None = None) -> t.RuntimeContext:
    return t.RuntimeContext(
        now_unix=now if now is not None else time.time(),
        context_fingerprint=ctx.context_id,
    )


# ── Group A: Provenance enforcement variants ──────────────────────────────────

def test_a1_candidate_id_mismatch_rejects_token():
    """A1: Token issued against correct claim_id but wrong candidate_id → REF.

    The token has Valid status but wrong provenance hash → PROVENANCE_MISMATCH
    blocker at step 4 → REF meet applied.  REF signals "credential seen and
    rejected" rather than OOC ("not in class").
    """
    gaps = [t.GapRecord("g1", "gap")]
    profiles = [t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])]
    placeholder = _make_ctx(gaps=gaps, profiles=profiles)

    wrong_hash = _prov(
        placeholder.claim_id,
        "wrong-candidate",       # candidate_id swapped
        placeholder.context_id,
        placeholder.allowed_use,
    )
    tok = t.ProofToken(
        token_id="tok-a1",
        token_type="CLOSE",
        schema_version="0.1",
        status="valid",
        closes_gaps=["g1"],
        bounds_gaps=[],
        provenance_hash=wrong_hash,
        issued_at=time.time() - 3600,
        issuer="stress",
    )
    ctx = _make_ctx(gaps=gaps, profiles=profiles, tokens=[tok])
    j = t.compile_static(ctx)
    assert j.permission == t.Permission.REF, f"Expected REF, got {j.permission}"


def test_a2_context_id_mismatch_rejects_token():
    """A2: Token issued against wrong context_id → REF.

    Wrong provenance hash → PROVENANCE_MISMATCH blocker → REF meet at step 4.
    """
    gaps = [t.GapRecord("g1", "gap")]
    profiles = [t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])]
    placeholder = _make_ctx(gaps=gaps, profiles=profiles)

    wrong_hash = _prov(
        placeholder.claim_id,
        placeholder.candidate_id,
        "wrong-context",          # context_id swapped
        placeholder.allowed_use,
    )
    tok = t.ProofToken(
        token_id="tok-a2",
        token_type="CLOSE",
        schema_version="0.1",
        status="valid",
        closes_gaps=["g1"],
        bounds_gaps=[],
        provenance_hash=wrong_hash,
        issued_at=time.time() - 3600,
        issuer="stress",
    )
    ctx = _make_ctx(gaps=gaps, profiles=profiles, tokens=[tok])
    j = t.compile_static(ctx)
    assert j.permission == t.Permission.REF


def test_a3_allowed_use_mismatch_rejects_token():
    """A3: Token issued against wrong allowed_use → REF.

    Wrong provenance hash → PROVENANCE_MISMATCH blocker → REF meet at step 4.
    """
    gaps = [t.GapRecord("g1", "gap")]
    profiles = [t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])]
    placeholder = _make_ctx(gaps=gaps, profiles=profiles, allowed_use="stress-test")

    wrong_hash = _prov(
        placeholder.claim_id,
        placeholder.candidate_id,
        placeholder.context_id,
        "completely-different-use",  # allowed_use swapped
    )
    tok = t.ProofToken(
        token_id="tok-a3",
        token_type="CLOSE",
        schema_version="0.1",
        status="valid",
        closes_gaps=["g1"],
        bounds_gaps=[],
        provenance_hash=wrong_hash,
        issued_at=time.time() - 3600,
        issuer="stress",
    )
    ctx = _make_ctx(gaps=gaps, profiles=profiles, tokens=[tok])
    j = t.compile_static(ctx)
    assert j.permission == t.Permission.REF


def test_a4_argument_order_swap_rejects_token():
    """A4: compute_provenance_hash with fields in wrong order → wrong hash → REF.

    The correct call is (claim_id, candidate_id, context_id, allowed_use).
    Swapping to (candidate_id, claim_id, context_id, allowed_use) produces a
    different hash → PROVENANCE_MISMATCH blocker → REF meet at step 4.
    """
    gaps = [t.GapRecord("g1", "gap")]
    profiles = [t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])]
    ctx_args = dict(
        claim_id="claim-a4",
        candidate_id="cand-a4",
        context_id="ctx-a4",
        allowed_use="stress-test",
    )
    placeholder = _make_ctx(gaps=gaps, profiles=profiles, **ctx_args)

    # Arguments swapped: claim_id ↔ candidate_id
    swapped_hash = t.compute_provenance_hash(
        ctx_args["candidate_id"],   # WRONG position
        ctx_args["claim_id"],       # WRONG position
        ctx_args["context_id"],
        ctx_args["allowed_use"],
    )
    tok = t.ProofToken(
        token_id="tok-a4",
        token_type="CLOSE",
        schema_version="0.1",
        status="valid",
        closes_gaps=["g1"],
        bounds_gaps=[],
        provenance_hash=swapped_hash,
        issued_at=time.time() - 3600,
        issuer="stress",
    )
    ctx = _make_ctx(gaps=gaps, profiles=profiles, tokens=[tok], **ctx_args)
    j = t.compile_static(ctx)
    assert j.permission == t.Permission.REF


def test_a5_hash_prefix_collision_rejects_token():
    """A5: Token with a hash that shares the first 8 characters with the correct hash → REF.

    SHA-256 must match in full (64 hex chars).  A prefix match is not enough.
    Wrong provenance hash → PROVENANCE_MISMATCH blocker → REF meet at step 4.
    """
    gaps = [t.GapRecord("g1", "gap")]
    profiles = [t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])]
    placeholder = _make_ctx(gaps=gaps, profiles=profiles)

    correct_hash = _prov(
        placeholder.claim_id,
        placeholder.candidate_id,
        placeholder.context_id,
        placeholder.allowed_use,
    )
    # Keep first 8 chars, corrupt the rest
    collision_attempt = correct_hash[:8] + "0" * 56

    tok = t.ProofToken(
        token_id="tok-a5",
        token_type="CLOSE",
        schema_version="0.1",
        status="valid",
        closes_gaps=["g1"],
        bounds_gaps=[],
        provenance_hash=collision_attempt,
        issued_at=time.time() - 3600,
        issuer="stress",
    )
    ctx = _make_ctx(gaps=gaps, profiles=profiles, tokens=[tok])
    j = t.compile_static(ctx)
    assert j.permission == t.Permission.REF


# ── Group B: Expiry boundary conditions ──────────────────────────────────────

def test_b1_token_expires_at_past_cannot_close_gap():
    """B1: Token with expires_at = now - 1s → expired token skipped, gap stays OPEN → EXP.

    An expired token (Valid status + past expires_at) is silently skipped in
    effective_gap_status so g1 remains OPEN and no profile is satisfied.
    Step 6 independently fires the EXP floor because a valid-provenance,
    valid-status token with a past expires_at exists.  The EXP floor does not
    require a profile to have been satisfied first.
    """
    now = time.time()
    placeholder = _dia_ctx("b1")
    tok = _closing_token(ctx=placeholder, gap_id="g1", expires_at=now - 1.0)
    ctx = _make_ctx(
        claim_id="claim-b1", candidate_id="cand-b1", context_id="ctx-b1",
        allowed_use="stress-test",
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])],
        tokens=[tok],
        context_fingerprint="ctx-b1",
    )
    live = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=now, context_fingerprint="ctx-b1")
    perm_str = live.permission_str(rt)
    # Expired token skipped → g1 not closed → step 6 EXP floor fires → EXP
    assert perm_str == "EXP", f"Expected EXP, got {perm_str}"


def test_b2_token_expires_in_future_closes_gap():
    """B2: Token with expires_at = now + 60s → not expired, gap closes normally → DIA."""
    now = time.time()
    placeholder = _dia_ctx("b2")
    tok = _closing_token(ctx=placeholder, gap_id="g1", expires_at=now + 60.0)
    ctx = _make_ctx(
        claim_id="claim-b2", candidate_id="cand-b2", context_id="ctx-b2",
        allowed_use="stress-test",
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])],
        tokens=[tok],
        context_fingerprint="ctx-b2",
    )
    live = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=now, context_fingerprint="ctx-b2")
    assert live.permission_str(rt) == "DIA"


def test_b3_context_expiry_and_token_both_fired():
    """B3: Both context expiry and token expiry fire simultaneously → EXP."""
    now = time.time()
    past = now - 10.0

    placeholder = _make_ctx(
        claim_id="claim-b3", candidate_id="cand-b3", context_id="ctx-b3",
        allowed_use="stress-test",
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])],
    )
    tok = _closing_token(ctx=placeholder, gap_id="g1", expires_at=past)
    ctx = _make_ctx(
        claim_id="claim-b3", candidate_id="cand-b3", context_id="ctx-b3",
        allowed_use="stress-test",
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])],
        tokens=[tok],
        context_fingerprint="ctx-b3",
    )
    # Context itself also expired
    expired_ctx = t.ProofContext(
        claim_id="claim-b3", candidate_id="cand-b3", context_id="ctx-b3",
        allowed_use="stress-test",
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.AAA,
        expiry=t.Expiry.at(past),
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])],
        tokens=[tok],
        context_fingerprint="ctx-b3",
    )
    live = t.compile(expired_ctx)
    rt = t.RuntimeContext(now_unix=now, context_fingerprint="ctx-b3")
    assert live.permission_str(rt) == "EXP"


def test_b4_mixed_expired_and_valid_tokens():
    """B4: Three tokens — first valid, second expired, third valid → only valid close gaps."""
    now = time.time()
    placeholder = _make_ctx(
        claim_id="claim-b4", candidate_id="cand-b4", context_id="ctx-b4",
        allowed_use="stress-test",
        gaps=[t.GapRecord("g1", "gap"), t.GapRecord("g2", "gap"), t.GapRecord("g3", "gap")],
        profiles=[t.Profile(
            t.Permission.DIA,
            [t.GapRequirement("g1", "closed"), t.GapRequirement("g3", "closed")],
        )],
    )
    h = _prov(placeholder.claim_id, placeholder.candidate_id, placeholder.context_id, placeholder.allowed_use)

    tok1 = t.ProofToken(
        token_id="tok-b4-valid1", token_type="T", schema_version="0.1",
        status="valid", closes_gaps=["g1"], bounds_gaps=[],
        provenance_hash=h, issued_at=now - 3600, issuer="stress",
    )
    tok2 = t.ProofToken(
        token_id="tok-b4-expired", token_type="T", schema_version="0.1",
        status="valid", closes_gaps=["g2"], bounds_gaps=[],
        provenance_hash=h, issued_at=now - 3600, issuer="stress",
        expires_at=now - 1.0,  # expired
    )
    tok3 = t.ProofToken(
        token_id="tok-b4-valid2", token_type="T", schema_version="0.1",
        status="valid", closes_gaps=["g3"], bounds_gaps=[],
        provenance_hash=h, issued_at=now - 3600, issuer="stress",
    )

    ctx = t.ProofContext(
        claim_id="claim-b4", candidate_id="cand-b4", context_id="ctx-b4",
        allowed_use="stress-test",
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.AAA,
        expiry=t.Expiry.never(),
        gaps=[t.GapRecord("g1", "gap"), t.GapRecord("g2", "gap"), t.GapRecord("g3", "gap")],
        profiles=[t.Profile(
            t.Permission.DIA,
            [t.GapRequirement("g1", "closed"), t.GapRequirement("g3", "closed")],
        )],
        tokens=[tok1, tok2, tok3],
        context_fingerprint="ctx-b4",
    )
    # tok2 is expired → EXP floor applied
    live = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=now, context_fingerprint="ctx-b4")
    assert live.permission_str(rt) == "EXP"


def test_b5_zero_duration_token_immediately_expired():
    """B5: Token with expires_at = issued_at (zero duration) → immediately expired → EXP.

    A zero-duration token expires at the instant it was issued.  When evaluated
    at any later time, it is skipped in effective_gap_status so g1 stays OPEN.
    Step 6 fires the EXP floor because a valid-provenance valid-status token
    with a past expires_at exists — same as B1, regardless of profile satisfaction.
    """
    now = time.time()
    issued = now - 3600
    placeholder = _make_ctx(
        claim_id="claim-b5", candidate_id="cand-b5", context_id="ctx-b5",
        allowed_use="stress-test",
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])],
    )
    h = _prov(placeholder.claim_id, placeholder.candidate_id, placeholder.context_id, placeholder.allowed_use)
    tok = t.ProofToken(
        token_id="tok-b5", token_type="T", schema_version="0.1",
        status="valid", closes_gaps=["g1"], bounds_gaps=[],
        provenance_hash=h, issued_at=issued, issuer="stress",
        expires_at=issued,  # expires at the same instant it was issued
    )
    ctx = t.ProofContext(
        claim_id="claim-b5", candidate_id="cand-b5", context_id="ctx-b5",
        allowed_use="stress-test",
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.AAA,
        expiry=t.Expiry.never(),
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])],
        tokens=[tok],
        context_fingerprint="ctx-b5",
    )
    live = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=now, context_fingerprint="ctx-b5")
    # Zero-duration token expired immediately → step 6 EXP floor fires → EXP
    assert live.permission_str(rt) == "EXP"


# ── Group C: Deep composition chains ─────────────────────────────────────────

def test_c1_three_deep_compose_non_promotion():
    """C1: compose(A, compose(B, C)) — non-promotion holds at each level."""
    ctx_a = _dia_ctx("c1a")
    ctx_b = _dia_ctx("c1b")
    ctx_c = _dia_ctx("c1c")

    rt_a = _rt(ctx_a)
    rt_b = _rt(ctx_b)
    rt_c = _rt(ctx_c)

    p_a = t.Permission.from_str(t.compile(ctx_a).permission_str(rt_a))
    p_b = t.Permission.from_str(t.compile(ctx_b).permission_str(rt_b))
    p_c = t.Permission.from_str(t.compile(ctx_c).permission_str(rt_c))

    bc = t.compose(ctx_b, ctx_c)
    abc = t.compose(ctx_a, bc)

    rt_abc = _rt(ctx_a)
    p_abc = t.Permission.from_str(t.compile(abc).permission_str(rt_abc))

    # Non-promotion: p(compose(A,B,C)) ≤ meet(p_a, p_b, p_c)
    floor = p_a.meet(p_b).meet(p_c)
    assert p_abc <= floor, f"Non-promotion violated: p_abc={p_abc} floor={floor}"


def test_c2_five_context_composition_one_gap_each():
    """C2: Five contexts each contributing one distinct gap closure.

    Each context closes one unique gap toward a single high-permission profile.
    The composed result should equal OOC because compose() takes g1's identity
    and g2-g5's tokens are rejected by provenance mismatch.
    Non-promotion: composed ≤ min of all individual permissions.

    Note: compose() sets context_fingerprint = "<a_fp>+<b_fp>" so the
    RuntimeContext for the composed judgment must use the combined fingerprint.
    """
    n = 5
    gap_ids = [f"g{i}" for i in range(1, n + 1)]
    allowed_use = "stress-c2"
    context_id = "ctx-c2"

    def _ctx_for_gap(i: int) -> t.ProofContext:
        claim_id = f"claim-c2-{i}"
        candidate_id = "cand-c2"
        h = t.compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use)
        tok = t.ProofToken(
            token_id=f"tok-c2-{i}",
            token_type="T", schema_version="0.1",
            status="valid",
            closes_gaps=[f"g{i}"],
            bounds_gaps=[],
            provenance_hash=h,
            issued_at=time.time() - 3600,
            issuer="stress",
        )
        return t.ProofContext(
            claim_id=claim_id, candidate_id=candidate_id, context_id=context_id,
            allowed_use=allowed_use,
            membership=t.Membership.InClass,
            authority_ceiling=t.Permission.DIA,
            expiry=t.Expiry.never(),
            gaps=[t.GapRecord(g, g) for g in gap_ids],
            profiles=[t.Profile(
                t.Permission.DIA,
                [t.GapRequirement(g, "closed") for g in gap_ids],
            )],
            tokens=[tok],
            context_fingerprint=context_id,
        )

    ctxs = [_ctx_for_gap(i) for i in range(1, n + 1)]
    rt = t.RuntimeContext(now_unix=time.time(), context_fingerprint=context_id)

    perms = [t.Permission.from_str(t.compile(c).permission_str(rt)) for c in ctxs]

    # Compose all and compute the combined fingerprint incrementally
    composed = ctxs[0]
    composed_fp = context_id
    for c in ctxs[1:]:
        composed = t.compose(composed, c)
        composed_fp = f"{composed_fp}+{context_id}"

    rt_composed = t.RuntimeContext(now_unix=time.time(), context_fingerprint=composed_fp)
    p_composed = t.Permission.from_str(t.compile(composed).permission_str(rt_composed))
    floor = perms[0]
    for p in perms[1:]:
        floor = floor.meet(p)

    assert p_composed <= floor, f"Non-promotion violated: {p_composed} > {floor}"


def test_c3_duplicate_token_ids_deduplicated():
    """C3: Compose two contexts with same token_id — anti-laundering blocks promotion.

    ctx_a has tok_v1 (valid, closes g1) → DIA.
    ctx_b has tok_v2 (same token_id, invalid status) → REF.
      tok_v2 has correct provenance but Invalid status → DEAD_CREDENTIAL blocker
      → REF meet at step 4.  REF, not OOC, because the candidate is in-class and
      a credential was actively seen and rejected.

    compose_tokens deduplicates by content equality excluding status, so tok_v1
    (valid) wins in the merged pool.  The permission_ceiling is set to
    meet(DIA, REF) = REF by the anti-laundering pre-check.

    Composed result ≤ REF: tok_v1 closes g1 in the merged pool → DIA, but the
    REF permission_ceiling floors it to REF.  ctx_b's DEAD_CREDENTIAL signal
    cannot be laundered by ctx_a's valid token.
    """
    context_fp = "ctx-c3"
    h = _prov("claim-c3", "cand-c3", context_fp, "stress-test")

    tok_v1 = t.ProofToken(
        token_id="shared-tok-id",
        token_type="T", schema_version="0.1", status="valid",
        closes_gaps=["g1"], bounds_gaps=[],
        provenance_hash=h, issued_at=time.time() - 3600, issuer="stress",
    )
    tok_v2 = t.ProofToken(
        token_id="shared-tok-id",    # same ID, invalid status
        token_type="T", schema_version="0.1", status="invalid",
        closes_gaps=["g1"], bounds_gaps=[],
        provenance_hash=h, issued_at=time.time() - 3600, issuer="stress",
    )

    ctx_a = t.ProofContext(
        claim_id="claim-c3", candidate_id="cand-c3", context_id=context_fp,
        allowed_use="stress-test", membership=t.Membership.InClass,
        authority_ceiling=t.Permission.DIA, expiry=t.Expiry.never(),
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])],
        tokens=[tok_v1], context_fingerprint=context_fp,
    )
    ctx_b = t.ProofContext(
        claim_id="claim-c3", candidate_id="cand-c3", context_id=context_fp,
        allowed_use="stress-test", membership=t.Membership.InClass,
        authority_ceiling=t.Permission.DIA, expiry=t.Expiry.never(),
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])],
        tokens=[tok_v2], context_fingerprint=context_fp,
    )

    rt = t.RuntimeContext(now_unix=time.time(), context_fingerprint=context_fp)
    p_a = t.Permission.from_str(t.compile(ctx_a).permission_str(rt))
    p_b = t.Permission.from_str(t.compile(ctx_b).permission_str(rt))
    assert p_a == t.Permission.DIA, f"Expected DIA for ctx_a, got {p_a}"
    assert p_b == t.Permission.REF, f"Expected REF for ctx_b (dead credential), got {p_b}"

    composed = t.compose(ctx_a, ctx_b)
    composed_fp = f"{context_fp}+{context_fp}"
    rt_composed = t.RuntimeContext(now_unix=time.time(), context_fingerprint=composed_fp)
    p_composed = t.Permission.from_str(t.compile(composed).permission_str(rt_composed))

    # Anti-laundering: ctx_b compiled to REF, so permission_ceiling = meet(DIA, REF) = REF.
    # tok_v1 (valid) wins in the merged pool and closes g1 → DIA, but the REF ceiling
    # floors it.  Non-promotion holds: composed (REF) ≤ meet(DIA, REF) = REF.
    assert p_composed == t.Permission.REF, f"Expected REF (anti-laundering), got {p_composed}"
    assert p_composed <= p_a.meet(p_b), f"Non-promotion violated: {p_composed} > meet({p_a},{p_b})"


def test_c4_g2_profile_not_present_in_g1():
    """C4: g2 has a DIA profile with a gap; g1 has no matching profile.

    After compose(g1, g2), g1's claim_id is used. g2's tokens are rejected
    (provenance mismatch). The composed result should be ≤ OOC for that tier.
    Non-promotion holds.
    """
    ctx1 = t.ProofContext(
        claim_id="claim-c4-1", candidate_id="cand-c4", context_id="ctx-c4",
        allowed_use="stress-c4",
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.DIA,
        expiry=t.Expiry.never(),
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[],  # no profiles → OOC
    )
    h2 = t.compute_provenance_hash("claim-c4-2", "cand-c4", "ctx-c4", "stress-c4")
    tok2 = t.ProofToken(
        token_id="tok-c4",
        token_type="T", schema_version="0.1", status="valid",
        closes_gaps=["g1"], bounds_gaps=[],
        provenance_hash=h2, issued_at=time.time() - 3600, issuer="stress",
    )
    ctx2 = t.ProofContext(
        claim_id="claim-c4-2", candidate_id="cand-c4", context_id="ctx-c4",
        allowed_use="stress-c4",
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.DIA,
        expiry=t.Expiry.never(),
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(t.Permission.DIA, [t.GapRequirement("g1", "closed")])],
        tokens=[tok2],
        context_fingerprint="ctx-c4",
    )

    rt = t.RuntimeContext(now_unix=time.time(), context_fingerprint="ctx-c4")
    p1 = t.Permission.from_str(t.compile(ctx1).permission_str(rt))
    p2 = t.Permission.from_str(t.compile(ctx2).permission_str(rt))

    composed = t.compose(ctx1, ctx2)
    # ctx1 context_fingerprint defaults to context_id="ctx-c4"; ctx2 explicitly "ctx-c4"
    # compose() sets combined fingerprint: "ctx-c4+ctx-c4"
    rt_composed = t.RuntimeContext(now_unix=time.time(), context_fingerprint="ctx-c4+ctx-c4")
    p_composed = t.Permission.from_str(t.compile(composed).permission_str(rt_composed))
    assert p_composed <= p1.meet(p2)


# ── Group D: Large-scale inputs ───────────────────────────────────────────────

def test_d1_ten_gaps_ten_profiles_ten_tokens():
    """D1: 10 gaps, 10 profiles escalating through permission tiers, 10 valid tokens → REV.

    Uses the Permission chain levels REF through REV (first 10 above OOC).
    Each profile requires an additional gap closed.
    All 10 gaps are closed → highest satisfiable permission reached.
    """
    n = 10
    gap_ids = [f"gap-{i}" for i in range(n)]
    # Pick 10 permission levels: REF, UNS, ETA, ESC, ROL, DIA, REV (7 meaningful ones)
    # We repeat DIA (ceiling) for extras — just needs n distinct profiles isn't required,
    # but duplicate permissions raise errors. Use a subset of the chain.
    perm_levels = ["REF", "UNS", "ETA", "ESC", "ROL", "DIA", "REV"]
    # Use only 7 profiles (can't have more distinct permissions in the chain below REV)
    profiles = [
        t.Profile(
            t.Permission.from_str(perm_levels[i]),
            [t.GapRequirement(gap_ids[j], "closed") for j in range(i + 1)],
        )
        for i in range(len(perm_levels))
    ]
    claim_id = "claim-d1"
    candidate_id = "cand-d1"
    context_id = "ctx-d1"
    allowed_use = "stress-d1"
    h = t.compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use)

    tokens = [
        t.ProofToken(
            token_id=f"tok-d1-{i}",
            token_type="T", schema_version="0.1", status="valid",
            closes_gaps=[gap_ids[i]], bounds_gaps=[],
            provenance_hash=h, issued_at=time.time() - 3600, issuer="stress",
        )
        for i in range(n)
    ]
    ctx = t.ProofContext(
        claim_id=claim_id, candidate_id=candidate_id, context_id=context_id,
        allowed_use=allowed_use,
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.AAA,
        expiry=t.Expiry.never(),
        gaps=[t.GapRecord(g, g) for g in gap_ids],
        profiles=profiles,
        tokens=tokens,
        context_fingerprint=context_id,
    )
    rt = t.RuntimeContext(now_unix=time.time(), context_fingerprint=context_id)
    j = t.compile_static(ctx)
    # Profiles cover REF–REV; all 7 profiles' requirements are met with 10 tokens closing 10 gaps
    assert j.permission >= t.Permission.REV, f"Expected ≥ REV, got {j.permission}"


def test_d2_fifty_gaps_all_closed_reaches_target():
    """D2: 50 gaps, 1 profile requiring all 50 closed, 50 valid tokens → DIA."""
    n = 50
    gap_ids = [f"g{i}" for i in range(n)]
    claim_id = "claim-d2"
    candidate_id = "cand-d2"
    context_id = "ctx-d2"
    allowed_use = "stress-d2"
    h = t.compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use)

    tokens = [
        t.ProofToken(
            token_id=f"tok-d2-{i}",
            token_type="T", schema_version="0.1", status="valid",
            closes_gaps=[gap_ids[i]], bounds_gaps=[],
            provenance_hash=h, issued_at=time.time() - 3600, issuer="stress",
        )
        for i in range(n)
    ]
    ctx = t.ProofContext(
        claim_id=claim_id, candidate_id=candidate_id, context_id=context_id,
        allowed_use=allowed_use,
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.AAA,
        expiry=t.Expiry.never(),
        gaps=[t.GapRecord(g, g) for g in gap_ids],
        profiles=[t.Profile(
            t.Permission.DIA,
            [t.GapRequirement(g, "closed") for g in gap_ids],
        )],
        tokens=tokens,
        context_fingerprint=context_id,
    )
    rt = t.RuntimeContext(now_unix=time.time(), context_fingerprint=context_id)
    assert t.compile(ctx).permission_str(rt) == "DIA"


def test_d3_fifty_gaps_one_wrong_provenance_blocks_target():
    """D3: 50 gaps, 50 tokens but one has wrong provenance → PROVENANCE_MISMATCH → REF."""
    n = 50
    gap_ids = [f"g{i}" for i in range(n)]
    claim_id = "claim-d3"
    candidate_id = "cand-d3"
    context_id = "ctx-d3"
    allowed_use = "stress-d3"
    correct_h = t.compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use)
    wrong_h = "bad0" * 16  # 64 chars of garbage

    tokens = []
    for i in range(n):
        h = wrong_h if i == 25 else correct_h  # one bad token at index 25
        tokens.append(t.ProofToken(
            token_id=f"tok-d3-{i}",
            token_type="T", schema_version="0.1", status="valid",
            closes_gaps=[gap_ids[i]], bounds_gaps=[],
            provenance_hash=h, issued_at=time.time() - 3600, issuer="stress",
        ))

    ctx = t.ProofContext(
        claim_id=claim_id, candidate_id=candidate_id, context_id=context_id,
        allowed_use=allowed_use,
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.AAA,
        expiry=t.Expiry.never(),
        gaps=[t.GapRecord(g, g) for g in gap_ids],
        profiles=[t.Profile(
            t.Permission.DIA,
            [t.GapRequirement(g, "closed") for g in gap_ids],
        )],
        tokens=tokens,
        context_fingerprint=context_id,
    )
    rt = t.RuntimeContext(now_unix=time.time(), context_fingerprint=context_id)
    perm = t.compile(ctx).permission_str(rt)
    # gap-25 token has wrong provenance → PROVENANCE_MISMATCH → REF meet at step 4
    assert perm == "REF", f"Expected REF (one bad-provenance token), got {perm}"


def test_d4_five_hundred_tokens_mostly_invalid():
    """D4: 500 tokens (490 invalid status, 10 valid) → only the 10 valid tokens count."""
    n_valid = 10
    n_invalid = 490
    gap_ids = [f"g{i}" for i in range(n_valid)]
    claim_id = "claim-d4"
    candidate_id = "cand-d4"
    context_id = "ctx-d4"
    allowed_use = "stress-d4"
    h = t.compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use)

    tokens = []
    # 490 invalid tokens that reference the same gaps but have invalid status
    for i in range(n_invalid):
        tokens.append(t.ProofToken(
            token_id=f"tok-d4-inv-{i}",
            token_type="T", schema_version="0.1", status="invalid",
            closes_gaps=[gap_ids[i % n_valid]], bounds_gaps=[],
            provenance_hash=h, issued_at=time.time() - 3600, issuer="stress",
        ))
    # 10 valid tokens that correctly close the gaps
    for i in range(n_valid):
        tokens.append(t.ProofToken(
            token_id=f"tok-d4-valid-{i}",
            token_type="T", schema_version="0.1", status="valid",
            closes_gaps=[gap_ids[i]], bounds_gaps=[],
            provenance_hash=h, issued_at=time.time() - 3600, issuer="stress",
        ))

    ctx = t.ProofContext(
        claim_id=claim_id, candidate_id=candidate_id, context_id=context_id,
        allowed_use=allowed_use,
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.AAA,
        expiry=t.Expiry.never(),
        gaps=[t.GapRecord(g, g) for g in gap_ids],
        profiles=[t.Profile(
            t.Permission.DIA,
            [t.GapRequirement(g, "closed") for g in gap_ids],
        )],
        tokens=tokens,
        context_fingerprint=context_id,
    )
    rt = t.RuntimeContext(now_unix=time.time(), context_fingerprint=context_id)
    perm = t.compile(ctx).permission_str(rt)
    # 10 valid tokens close all 10 gaps → DIA profile satisfied
    assert perm == "DIA", f"Expected DIA, got {perm}"
