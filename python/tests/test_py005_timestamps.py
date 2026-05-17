"""PY-005 — Timestamp precision, boundaries, and conversion edge cases.

   T1 — Expiry.at(deadline) fires at exactly the deadline integer second.
   T2 — Expiry.fired() treats fractional seconds as truncated (as i64 cast).
   T3 — Expiry.never() never fires (fired() always returns False).
   T4 — ProofToken issued_at is stored (can construct without error).
   T5 — ProofToken expires_at=None means no expiration on the token.
   T6 — ProofToken with past expires_at and Valid status triggers EXP in compile.
   T7 — ProofToken with past expires_at and Invalid status does NOT trigger EXP.
   T8 — RuntimeContext now_unix as float: fractional part is truncated to seconds.
   T9 — Derivation.compiled_at is a float (Unix timestamp).
   T10 — Very old timestamp (year 1970) is handled without error.
   T11 — Future expiry (year 2100) is handled without error.
"""

import time
import pytest
import turnstile as t
from conftest import make_ctx, closing_token


# ── T1: Expiry.at fires at exactly the deadline ───────────────────────────────

def test_t1_expiry_fires_at_deadline():
    deadline = time.time() + 100.0
    exp = t.Expiry.at(deadline)
    assert not exp.fired(deadline - 1.0), "T1: must not fire 1s before deadline"
    assert exp.fired(deadline), "T1: must fire at deadline"
    assert exp.fired(deadline + 1.0), "T1: must fire after deadline"


# ── T2: Fractional seconds are truncated (as i64 behavior) ───────────────────

def test_t2_fractional_seconds_truncated():
    # deadline = integer + 0.9
    # t.Expiry.at(deadline) → truncates to integer
    # fired(deadline - 0.5) → truncated to integer - 1 if we pass < integer
    # The key invariant: firing is determined by integer seconds, not fractional
    deadline_int = int(time.time()) + 100
    deadline_frac = deadline_int + 0.9  # truncates to deadline_int

    exp = t.Expiry.at(deadline_frac)
    # at deadline_int (same as truncated deadline_frac), should fire
    assert exp.fired(float(deadline_int)), "T2: should fire at integer part of deadline"
    # at deadline_int - 1 (one second before), should not fire
    assert not exp.fired(float(deadline_int - 1)), "T2: must not fire 1s before integer deadline"


# ── T3: Expiry.never() never fires ───────────────────────────────────────────

def test_t3_expiry_never_never_fires():
    exp = t.Expiry.never()
    now = time.time()
    assert not exp.fired(now)
    assert not exp.fired(now + 1e10)  # far future
    assert not exp.fired(0.0)


# ── T4: ProofToken issued_at constructs without error ─────────────────────────

def test_t4_proof_token_issued_at():
    tok = t.ProofToken(
        token_id="t4-tok",
        token_type="TEST",
        schema_version="0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=[],
        provenance_hash="a" * 64,
        issued_at=time.time() - 3600,
        issuer="test",
    )
    assert tok.token_id == "t4-tok"
    assert tok.status == "valid"


# ── T5: expires_at=None means no token expiration ────────────────────────────

def test_t5_no_token_expiry():
    ctx = make_ctx(
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
    )
    tok = closing_token(ctx=ctx, expires_at=None)
    full_ctx = make_ctx(
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
        tokens=[tok],
    )
    j = t.compile_static(full_ctx)
    assert j.permission == t.Permission.DIA  # No EXP floor


# ── T6: Valid token with past expires_at → EXP floor ─────────────────────────

def test_t6_valid_expired_token_triggers_exp():
    now = time.time()
    past = now - 3600
    future = now + 3600

    ctx_placeholder = make_ctx(
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
    )
    # Good token satisfies the profile (no expiry)
    good_tok = closing_token(ctx=ctx_placeholder, token_id="good", expires_at=future)
    # Expired Valid token triggers the EXP floor
    exp_tok = t.ProofToken(
        token_id="exp-tok",
        token_type="OTHER",
        schema_version="0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=[],
        provenance_hash=t.compute_provenance_hash(
            ctx_placeholder.claim_id,
            ctx_placeholder.candidate_id,
            ctx_placeholder.context_id,
            ctx_placeholder.allowed_use,
        ),
        issued_at=now - 7200,
        expires_at=past,
        issuer="test",
    )
    full_ctx = make_ctx(
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
        tokens=[good_tok, exp_tok],
    )
    j = t.compile_static(full_ctx)
    assert j.permission == t.Permission.EXP, "T6: valid expired token must trigger EXP floor"


# ── T7: Invalid token with past expires_at → no EXP floor ────────────────────

def test_t7_invalid_expired_token_no_exp():
    now = time.time()
    past = now - 3600
    future = now + 3600

    ctx_placeholder = make_ctx(
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
    )
    good_tok = closing_token(ctx=ctx_placeholder, token_id="good", expires_at=future)
    dead_tok = t.ProofToken(
        token_id="dead-tok",
        token_type="OTHER",
        schema_version="0.1",
        status="invalid",  # Invalid — should not trigger EXP
        closes_gaps=[],
        bounds_gaps=[],
        provenance_hash=t.compute_provenance_hash(
            ctx_placeholder.claim_id,
            ctx_placeholder.candidate_id,
            ctx_placeholder.context_id,
            ctx_placeholder.allowed_use,
        ),
        issued_at=now - 7200,
        expires_at=past,
        issuer="test",
    )
    full_ctx = make_ctx(
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
        tokens=[good_tok, dead_tok],
    )
    j = t.compile_static(full_ctx)
    assert j.permission == t.Permission.DIA, "T7: invalid expired token must NOT trigger EXP"


# ── T8: RuntimeContext fractional now_unix ────────────────────────────────────

def test_t8_runtime_context_fractional_now():
    now = time.time()
    rt = t.RuntimeContext(now_unix=now + 0.999, context_fingerprint="ctx-py")
    ctx = make_ctx()
    live = t.compile(ctx)
    # Should not error out — fractional part is truncated
    p = live.permission(rt)
    assert p == t.Permission.OOC


# ── T9: Derivation.compiled_at is a float ─────────────────────────────────────

def test_t9_derivation_compiled_at_is_float():
    j = t.compile_static(make_ctx())
    assert isinstance(j.derivation.compiled_at, float)
    assert j.derivation.compiled_at > 0


# ── T10: Very old timestamp (near Unix epoch) ─────────────────────────────────

def test_t10_very_old_timestamp_no_error():
    exp = t.Expiry.at(1.0)  # 1 second after epoch
    assert exp.fired(2.0)  # definitely fired
    tok = t.ProofToken(
        token_id="old-tok",
        token_type="TEST",
        schema_version="0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=[],
        provenance_hash="a" * 64,
        issued_at=1.0,
        issuer="test",
    )
    assert tok.token_id == "old-tok"


# ── T11: Far-future expiry (year ~2100) ───────────────────────────────────────

def test_t11_far_future_expiry():
    far_future = 4_102_444_800.0  # 2100-01-01 00:00:00 UTC
    exp = t.Expiry.at(far_future)
    assert not exp.fired(time.time()), "T11: far-future expiry must not fire now"
