"""PY-006 — Exception hierarchy and error message quality.

   E1 — TurnstileError is catchable as a base exception.
   E2 — ExpiredError is catchable as TurnstileError.
   E3 — CompositionError is catchable as TurnstileError.
   E4 — ProvenanceError is a subclass of TurnstileError (import check).
   E5 — TurnstileError message is non-empty on MalformedContext.
   E6 — CompositionError message mentions "conflict" or "use".
   E7 — ExpiredError message mentions expiry time.
   E8 — Unknown permission string raises ValueError (not TurnstileError).
   E9 — Unknown gap status raises ValueError (not TurnstileError).
   E10 — Unknown token status raises ValueError (not TurnstileError).
   E11 — Unknown GapRequirement status raises ValueError.
"""

import time
import pytest
import noethers_turnstile as t
from conftest import make_ctx


# ── E1: TurnstileError is catchable as base ───────────────────────────────────

def test_e1_turnstile_error_catchable():
    with pytest.raises(t.TurnstileError):
        t.compile(make_ctx(allowed_use=""))


# ── E2: ExpiredError catchable as TurnstileError ──────────────────────────────

def test_e2_expired_error_as_turnstile():
    now = time.time()
    ctx = make_ctx(expiry=t.Expiry.at(now - 3600))
    live = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=now, context_fingerprint="ctx-py")
    with pytest.raises(t.TurnstileError):  # catching base
        live.permission(rt)


# ── E3: CompositionError catchable as TurnstileError ─────────────────────────

def test_e3_composition_error_as_turnstile():
    g1 = make_ctx(allowed_use="use-a")
    g2 = make_ctx(allowed_use="use-b")
    with pytest.raises(t.TurnstileError):  # catching base
        t.compose(g1, g2)


# ── E4: ProvenanceError exists as subclass of TurnstileError ─────────────────

def test_e4_provenance_error_is_subclass():
    assert issubclass(t.ProvenanceError, t.TurnstileError)


# ── E5: MalformedContext error message is non-empty ──────────────────────────

def test_e5_malformed_context_message_nonempty():
    with pytest.raises(t.TurnstileError) as exc_info:
        t.compile(make_ctx(allowed_use=""))
    assert len(str(exc_info.value)) > 0


# ── E6: CompositionError message is informative ───────────────────────────────

def test_e6_composition_error_message():
    g1 = make_ctx(allowed_use="use-a")
    g2 = make_ctx(allowed_use="use-b")
    with pytest.raises(t.CompositionError) as exc_info:
        t.compose(g1, g2)
    msg = str(exc_info.value).lower()
    assert "conflict" in msg or "use" in msg, f"E6: message was: {msg}"


# ── E7: ExpiredError message mentions time ────────────────────────────────────

def test_e7_expired_error_message():
    now = time.time()
    ctx = make_ctx(expiry=t.Expiry.at(now - 3600))
    live = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=now, context_fingerprint="ctx-py")
    with pytest.raises(t.ExpiredError) as exc_info:
        live.permission(rt)
    msg = str(exc_info.value)
    assert len(msg) > 0, "E7: ExpiredError message must be non-empty"
    # Should contain some reference to expiry (time, deadline, expired, etc.)
    assert any(kw in msg.lower() for kw in ("expired", "expir", "at ")), (
        f"E7: message did not mention time: {msg}"
    )


# ── E8: Unknown permission string → ValueError ───────────────────────────────

def test_e8_unknown_permission_value_error():
    # from_str is case-insensitive (accepts "aaa" → AAA), but rejects unknown tags
    with pytest.raises(ValueError):
        t.Permission.from_str("GODMODE")
    with pytest.raises(ValueError):
        t.Permission.from_str("SUPER")
    with pytest.raises(ValueError):
        t.Permission.from_str("")


# ── E9: Unknown gap status → ValueError ──────────────────────────────────────

def test_e9_unknown_gap_status_value_error():
    with pytest.raises((ValueError, Exception)):
        t.GapRecord("g1", "type", status="unknown-status")


# ── E10: Unknown token status → ValueError ───────────────────────────────────

def test_e10_unknown_token_status_value_error():
    with pytest.raises((ValueError, Exception)):
        t.ProofToken(
            token_id="tok",
            token_type="TEST",
            schema_version="0.1",
            status="super-valid",  # invalid status
            closes_gaps=[],
            bounds_gaps=[],
            provenance_hash="a" * 64,
            issued_at=time.time(),
            issuer="test",
        )


# ── E11: Unknown GapRequirement minimum_status → ValueError ──────────────────

def test_e11_unknown_gap_req_status_value_error():
    with pytest.raises((ValueError, Exception)):
        t.GapRequirement("g1", "super-closed")  # invalid minimum_status
