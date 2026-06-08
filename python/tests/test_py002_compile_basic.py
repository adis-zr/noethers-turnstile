"""PY-002 — compile() basic outcomes: OOC, DIA, EXP, MalformedContext.

   C1 — Empty context (no gaps, no profiles, no tokens) → OOC.
   C2 — Context with profile and valid closing token → DIA.
   C3 — Mismatched provenance hash → profile unsatisfied → OOC.
   C4 — compile() returns a LiveJudgment (not a Judgment).
   C5 — compile_static() returns a Judgment (snapshot, not live).
   C6 — Judgment.permission is a Permission object.
   C7 — Judgment.derivation has at least one step.
   C8 — Empty allowed_use → TurnstileError (MalformedContext).
   C9 — Duplicate gap_ids → TurnstileError (MalformedContext).
   C10 — Profile referencing unknown gap_id → TurnstileError (MalformedContext).
   C11 — Duplicate permission in profiles → TurnstileError (MalformedContext).
   C12 — authority_ceiling truncates outcome: DIA ceiling on DIA profile → DIA.
   C13 — REF ceiling on DIA profile → REF.
"""

import time
import pytest
import noethers_turnstile as t
from conftest import make_ctx, closing_token, make_dia_ctx


# ── C1: Empty context → OOC ──────────────────────────────────────────────────

def test_c1_empty_context_ooc(rt):
    ctx = make_ctx()
    live = t.compile(ctx)
    assert live.permission(rt) == t.Permission.OOC


# ── C2: Valid closing token satisfies DIA profile → DIA ──────────────────────

def test_c2_valid_token_dia():
    ctx = make_dia_ctx()
    now = time.time()
    live = t.compile(ctx)
    # The implicit fingerprint is the canonical content hash (F13).
    rt = t.RuntimeContext(now_unix=now, context_fingerprint=ctx.provenance_hash())
    assert live.permission(rt) == t.Permission.DIA


# ── C3: Wrong provenance hash → REF (structural blocker, not OOC) ────────────
#
# Post chain refactor: wrong-provenance with a profile defined emits REF
# (via the structural-blocker meet to chain.role(Refused)). OOC is reserved
# for membership-failure or no-profiles cases.

def test_c3_wrong_provenance_ref(now, rt):
    ctx = make_ctx(
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
        tokens=[t.ProofToken(
            token_id="tok-bad",
            token_type="CLOSE",
            schema_version="0.1",
            status="valid",
            closes_gaps=["g1"],
            bounds_gaps=[],
            provenance_hash="deadbeef" * 8,  # wrong hash
            issued_at=now - 3600,
            issuer="test",
        )],
    )
    live = t.compile(ctx)
    assert live.permission(rt) == t.Permission.REF


# ── C4: compile() returns LiveJudgment ───────────────────────────────────────

def test_c4_compile_returns_live_judgment():
    live = t.compile(make_ctx())
    assert isinstance(live, t.LiveJudgment)


# ── C5: compile_static() returns Judgment ────────────────────────────────────

def test_c5_compile_static_returns_judgment():
    j = t.compile_static(make_ctx())
    assert isinstance(j, t.Judgment)


# ── C6: Judgment.permission is a Permission ──────────────────────────────────

def test_c6_judgment_permission_type():
    j = t.compile_static(make_ctx())
    assert isinstance(j.permission, t.Permission)


# ── C7: Judgment.derivation has at least one step ────────────────────────────

def test_c7_derivation_has_steps():
    j = t.compile_static(make_ctx())
    d = j.derivation
    assert len(d.steps) >= 1
    step = d.steps[0]
    assert isinstance(step.phase, str) and step.phase
    assert isinstance(step.note, str)
    assert isinstance(step.token_ids, list)


# ── C8: Empty allowed_use → TurnstileError ───────────────────────────────────

def test_c8_empty_allowed_use_raises():
    ctx = make_ctx(allowed_use="")
    with pytest.raises(t.TurnstileError, match="allowed_use"):
        t.compile(ctx)


# ── C9: Duplicate gap_ids → TurnstileError ───────────────────────────────────

def test_c9_duplicate_gap_ids_raises():
    ctx = make_ctx(
        gaps=[
            t.GapRecord("g1", "type-a"),
            t.GapRecord("g1", "type-b"),  # duplicate
        ]
    )
    with pytest.raises(t.TurnstileError, match="duplicate"):
        t.compile(ctx)


# ── C10: Profile referencing unknown gap_id → TurnstileError ─────────────────

def test_c10_unknown_gap_ref_raises():
    ctx = make_ctx(
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g99", "closed")],  # g99 doesn't exist
        )],
    )
    with pytest.raises(t.TurnstileError, match="unknown gap_id"):
        t.compile(ctx)


# ── C11: Duplicate permission in profiles → TurnstileError ───────────────────

def test_c11_duplicate_profile_permission_raises():
    ctx = make_ctx(
        gaps=[t.GapRecord("g1", "gap"), t.GapRecord("g2", "gap")],
        profiles=[
            t.Profile(
                permission=t.Permission.DIA,
                required_gaps=[t.GapRequirement("g1", "closed")],
            ),
            t.Profile(
                permission=t.Permission.DIA,  # duplicate
                required_gaps=[t.GapRequirement("g2", "closed")],
            ),
        ],
    )
    with pytest.raises(t.TurnstileError, match="duplicate profile"):
        t.compile(ctx)


# ── C12: DIA ceiling on DIA profile → DIA ────────────────────────────────────

def test_c12_authority_ceiling_allows_dia():
    ctx = make_dia_ctx()
    now = time.time()
    j = t.compile_static(ctx)
    assert j.permission == t.Permission.DIA


# ── C13: REF ceiling on DIA profile → REF ────────────────────────────────────

def test_c13_authority_ceiling_caps_at_ref():
    placeholder = make_ctx(
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
        authority_ceiling=t.Permission.REF,
    )
    tok = closing_token(ctx=placeholder)
    ctx = make_ctx(
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
        tokens=[tok],
        authority_ceiling=t.Permission.REF,
    )
    j = t.compile_static(ctx)
    assert j.permission == t.Permission.REF


# ── F13: context_fingerprint default is a content hash, not a copy of id ──────
#
# Previously: if context_fingerprint was omitted, it was set to a literal copy
# of context_id. That made LiveJudgment fingerprint revalidation a no-op —
# two contexts with the same id but different payloads compared equal at the
# runtime boundary.
#
# Fix: when omitted, derive the fingerprint from the context payload (claim,
# candidate, context_id, allowed_use). Two contexts that differ in any of
# those produce different fingerprints, so LiveJudgment can detect mismatch.


def _dia_ctx_implicit_fingerprint(allowed_use: str) -> t.ProofContext:
    """A context that compiles to DIA when its fingerprint is matched, and
    falls to OOC when not — so the fingerprint check is observable."""
    placeholder = t.ProofContext(
        claim_id="claim-fp",
        candidate_id="z-fp",
        context_id="ctx-fp",
        allowed_use=allowed_use,
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.AAA,
        expiry=t.Expiry.never(),
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[
            t.Profile(
                permission=t.Permission.DIA,
                required_gaps=[t.GapRequirement("g1", "closed")],
            )
        ],
        # context_fingerprint omitted on purpose
    )
    h = t.compute_provenance_hash(
        placeholder.claim_id,
        placeholder.candidate_id,
        placeholder.context_id,
        placeholder.allowed_use,
    )
    tok = t.ProofToken(
        token_id="tok",
        token_type="T",
        schema_version="0.1",
        status="valid",
        closes_gaps=["g1"],
        bounds_gaps=[],
        provenance_hash=h,
        issued_at=time.time(),
        issuer="test",
    )
    return t.ProofContext(
        claim_id="claim-fp",
        candidate_id="z-fp",
        context_id="ctx-fp",
        allowed_use=allowed_use,
        membership=t.Membership.InClass,
        authority_ceiling=t.Permission.AAA,
        expiry=t.Expiry.never(),
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[
            t.Profile(
                permission=t.Permission.DIA,
                required_gaps=[t.GapRequirement("g1", "closed")],
            )
        ],
        tokens=[tok],
        # context_fingerprint omitted on purpose
    )


def test_f13_implicit_fingerprint_is_not_literal_context_id():
    """An omitted context_fingerprint must not equal the bare context_id.
    Otherwise a runtime that supplies just the id passes fingerprint check
    even though the payload could have been swapped underneath it."""
    ctx = _dia_ctx_implicit_fingerprint("use-a")
    live = t.compile(ctx)
    # Try a runtime with the literal context_id as fingerprint.
    rt = t.RuntimeContext(now_unix=time.time(), context_fingerprint="ctx-fp")
    result = live.permission_str(rt)
    # If the implicit fingerprint were a literal copy of "ctx-fp", this would
    # match and the live read would return "DIA". Post-fix: no match,
    # returns Bottom ("OOC").
    assert result == "OOC", (
        "implicit fingerprint must not match a bare context_id at the runtime "
        f"boundary; got {result!r}"
    )


def test_f13_runtime_with_content_hash_fingerprint_is_accepted():
    """A runtime supplying the canonical provenance hash as fingerprint must
    be accepted (since that's the post-fix default)."""
    ctx = _dia_ctx_implicit_fingerprint("use-a")
    live = t.compile(ctx)
    rt = t.RuntimeContext(
        now_unix=time.time(),
        context_fingerprint=ctx.provenance_hash(),
    )
    assert live.permission_str(rt) == "DIA"


def test_f13_implicit_fingerprint_differs_when_payload_differs():
    """Two contexts identical except for allowed_use must produce different
    implicit fingerprints — so a runtime fingerprint built for one does NOT
    satisfy the other."""
    ctx_a = _dia_ctx_implicit_fingerprint("use-a")
    ctx_b = _dia_ctx_implicit_fingerprint("use-b")
    live_b = t.compile(ctx_b)
    # Build a runtime carrying ctx_a's content hash.
    rt_a = t.RuntimeContext(
        now_unix=time.time(),
        context_fingerprint=ctx_a.provenance_hash(),
    )
    # It must not validate ctx_b's live read.
    assert live_b.permission_str(rt_a) == "OOC"
