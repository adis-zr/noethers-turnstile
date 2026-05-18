"""PY-003 — LiveJudgment runtime evaluation: expiry, fingerprint, NC liveness.

   L1 — permission() raises ExpiredError when context expiry has fired.
   L2 — permission_str() returns "EXP" without raising when expired.
   L3 — permission() returns correct permission when not expired.
   L4 — ExpiredError is a subclass of TurnstileError.
   L5 — Fingerprint mismatch → permission() returns EXP (not DIA).
   L6 — permission() is idempotent: calling twice returns the same value.
   L7 — permission_str() never raises (safe observer pattern).
   L8 — Live non-expired context with DIA judgment → permission() returns DIA.
   L9 — Judgment expiry fires at correct Unix boundary (timestamp precision).
   L10 — Non-strict mode: NC token absent → still returns the permission.
"""

import time
import pytest
import noethers_turnstile as t
from conftest import make_ctx, closing_token, make_dia_ctx


# ── L1: ExpiredError raised when context expiry has fired ────────────────────

def test_l1_expired_context_raises():
    now = time.time()
    ctx = make_ctx(expiry=t.Expiry.at(now - 3600))  # expired 1h ago
    live = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=now, context_fingerprint="ctx-py")
    with pytest.raises(t.ExpiredError):
        live.permission(rt)


# ── L2: permission_str returns "EXP" without raising ─────────────────────────

def test_l2_expired_permission_str_no_raise():
    now = time.time()
    ctx = make_ctx(expiry=t.Expiry.at(now - 3600))
    live = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=now, context_fingerprint="ctx-py")
    result = live.permission_str(rt)
    assert result == "EXP"


# ── L3: Non-expired context returns correct permission ───────────────────────

def test_l3_not_expired_returns_permission():
    now = time.time()
    ctx = make_ctx(expiry=t.Expiry.at(now + 3600))  # expires 1h from now
    live = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=now, context_fingerprint="ctx-py")
    p = live.permission(rt)
    assert p == t.Permission.OOC  # no profiles → OOC, but not expired


# ── L4: ExpiredError is subclass of TurnstileError ───────────────────────────

def test_l4_expired_error_is_subclass():
    assert issubclass(t.ExpiredError, t.TurnstileError)


# ── L5: Fingerprint mismatch → EXP, not DIA ──────────────────────────────────

def test_l5_fingerprint_mismatch_returns_exp():
    ctx = make_dia_ctx()
    now = time.time()
    live = t.compile(ctx)
    # Wrong fingerprint
    rt = t.RuntimeContext(now_unix=now, context_fingerprint="WRONG-FP")
    # permission_str returns "EXP" on mismatch without raising
    result = live.permission_str(rt)
    assert result == "EXP"


# ── L6: permission() is idempotent ────────────────────────────────────────────

def test_l6_permission_is_idempotent():
    ctx = make_dia_ctx()
    now = time.time()
    live = t.compile(ctx)
    # make_dia_ctx uses context_id="ctx-1" which becomes the default fingerprint
    rt = t.RuntimeContext(now_unix=now, context_fingerprint="ctx-1")
    p1 = live.permission(rt)
    p2 = live.permission(rt)
    assert p1 == p2


# ── L7: permission_str() never raises ────────────────────────────────────────

def test_l7_permission_str_never_raises():
    now = time.time()
    # Expired context
    ctx1 = make_ctx(expiry=t.Expiry.at(now - 3600))
    rt1 = t.RuntimeContext(now_unix=now, context_fingerprint="ctx-py")
    assert t.compile(ctx1).permission_str(rt1) == "EXP"

    # Wrong fingerprint
    ctx2 = make_dia_ctx()
    rt2 = t.RuntimeContext(now_unix=now, context_fingerprint="bad-fp")
    result = t.compile(ctx2).permission_str(rt2)
    assert result == "EXP"

    # Normal OOC
    ctx3 = make_ctx()
    rt3 = t.RuntimeContext(now_unix=now, context_fingerprint="ctx-py")
    assert t.compile(ctx3).permission_str(rt3) == "OOC"


# ── L8: DIA judgment → permission() returns DIA ──────────────────────────────

def test_l8_dia_judgment_returns_dia():
    ctx = make_dia_ctx()
    now = time.time()
    live = t.compile(ctx)
    # make_dia_ctx context_id="ctx-1" is used as the fingerprint
    rt = t.RuntimeContext(now_unix=now, context_fingerprint="ctx-1")
    assert live.permission(rt) == t.Permission.DIA


# ── L9: Expiry fires at correct Unix boundary ─────────────────────────────────

def test_l9_expiry_fires_at_boundary():
    deadline = time.time() + 10.0
    exp = t.Expiry.at(deadline)

    # Not yet fired (1s before)
    assert not exp.fired(deadline - 1.0)
    # Fired at the deadline
    assert exp.fired(deadline)
    # Fired after
    assert exp.fired(deadline + 1.0)


# ── L10: Non-strict mode does not raise on absent NC token ────────────────────

def test_l10_non_strict_mode_nc_absent():
    ctx = make_ctx()
    now = time.time()
    live = t.compile(ctx)
    # No NC states, non-strict mode
    rt = t.RuntimeContext(
        now_unix=now,
        context_fingerprint="ctx-py",
        strict_mode=False,
    )
    p = live.permission(rt)
    assert p == t.Permission.OOC  # no profiles → OOC, not an error
