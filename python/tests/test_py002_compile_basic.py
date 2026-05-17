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
import turnstile as t
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
    # make_dia_ctx uses context_id="ctx-1" as the default fingerprint
    rt = t.RuntimeContext(now_unix=now, context_fingerprint="ctx-1")
    assert live.permission(rt) == t.Permission.DIA


# ── C3: Wrong provenance hash → OOC ──────────────────────────────────────────

def test_c3_wrong_provenance_ooc(now, rt):
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
    assert live.permission(rt) == t.Permission.OOC


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
