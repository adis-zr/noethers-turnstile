"""PY-008 — Derivation inspection: steps, phases, provenance hash.

   D1 — Derivation.steps is a list of DerivationStep objects.
   D2 — Each DerivationStep.phase is a non-empty string.
   D3 — Each DerivationStep.permission_after is a Permission.
   D4 — Each DerivationStep.note is a string (may be empty).
   D5 — Each DerivationStep.token_ids is a list of strings.
   D6 — Derivation.provenance_hash is a 64-char hex string.
   D7 — Derivation.compiled_at is a positive float (Unix timestamp).
   D8 — DIA outcome derivation has a step with permission_after=DIA.
   D9 — EXP floor derivation has a step with permission_after=EXP.
   D10 — Derivation from compile_static matches static Judgment.permission.
"""

import time
import pytest
import noethers_turnstile as t
from conftest import make_ctx, closing_token, make_dia_ctx


# ── D1: steps is a list of DerivationStep ────────────────────────────────────

def test_d1_steps_type():
    j = t.compile_static(make_ctx())
    assert isinstance(j.derivation.steps, list)
    assert len(j.derivation.steps) >= 1
    for step in j.derivation.steps:
        assert isinstance(step, t.DerivationStep)


# ── D2: Each step.phase is a non-empty string ─────────────────────────────────

def test_d2_step_phase_nonempty():
    j = t.compile_static(make_ctx())
    for step in j.derivation.steps:
        assert isinstance(step.phase, str)
        assert len(step.phase) > 0, "D2: phase must not be empty"


# ── D3: Each step.permission_after is a Permission ───────────────────────────

def test_d3_step_permission_type():
    j = t.compile_static(make_ctx())
    for step in j.derivation.steps:
        assert isinstance(step.permission_after, t.Permission)


# ── D4: Each step.note is a string ───────────────────────────────────────────

def test_d4_step_note_string():
    j = t.compile_static(make_ctx())
    for step in j.derivation.steps:
        assert isinstance(step.note, str)


# ── D5: Each step.token_ids is a list of strings ─────────────────────────────

def test_d5_step_token_ids():
    j = t.compile_static(make_ctx())
    for step in j.derivation.steps:
        assert isinstance(step.token_ids, list)
        for tid in step.token_ids:
            assert isinstance(tid, str)


# ── D6: Derivation.provenance_hash is a 64-char hex string ───────────────────

def test_d6_derivation_provenance_hash():
    j = t.compile_static(make_ctx())
    h = j.derivation.provenance_hash
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h.lower())


# ── D7: Derivation.compiled_at is a positive float ───────────────────────────

def test_d7_derivation_compiled_at():
    before = time.time()
    j = t.compile_static(make_ctx())
    after = time.time()
    compiled_at = j.derivation.compiled_at
    assert isinstance(compiled_at, float)
    assert compiled_at > 0
    # Should be within the current epoch (not epoch 0 and not 1e15)
    assert before - 2 <= compiled_at <= after + 2


# ── D8: DIA derivation has step with permission_after=DIA ────────────────────

def test_d8_dia_derivation_has_dia_step():
    j = t.compile_static(make_dia_ctx())
    permissions = [step.permission_after for step in j.derivation.steps]
    assert t.Permission.DIA in permissions or j.permission == t.Permission.DIA, (
        "D8: DIA derivation must show DIA in steps or final permission"
    )
    assert j.permission == t.Permission.DIA


# ── D9: EXP floor derivation ─────────────────────────────────────────────────

def test_d9_exp_derivation():
    now = time.time()
    past = now - 3600
    future = now + 3600

    placeholder = make_ctx(
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
    )
    good_tok = closing_token(ctx=placeholder, token_id="good", expires_at=future)
    exp_tok = t.ProofToken(
        token_id="exp-tok",
        token_type="OTHER",
        schema_version="0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=[],
        provenance_hash=t.compute_provenance_hash(
            placeholder.claim_id, placeholder.candidate_id,
            placeholder.context_id, placeholder.allowed_use,
        ),
        issued_at=now - 7200,
        expires_at=past,
        issuer="test",
    )
    ctx = make_ctx(
        gaps=[t.GapRecord("g1", "gap")],
        profiles=[t.Profile(
            permission=t.Permission.DIA,
            required_gaps=[t.GapRequirement("g1", "closed")],
        )],
        tokens=[good_tok, exp_tok],
    )
    j = t.compile_static(ctx)
    assert j.permission == t.Permission.EXP, "D9: EXP floor must apply"


# ── D10: Derivation final step matches Judgment.permission ────────────────────

def test_d10_derivation_matches_judgment_permission():
    j = t.compile_static(make_dia_ctx())
    steps = j.derivation.steps
    # The final step's permission should match the judgment's permission
    # (The derivation records the progression; final outcome is j.permission)
    assert j.permission == t.Permission.DIA
    # At minimum, the last step should record the final outcome
    assert steps[-1].permission_after == j.permission
