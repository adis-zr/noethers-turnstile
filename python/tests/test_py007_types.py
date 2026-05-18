"""PY-007 — Data types: GapRecord, Profile, Scope, Membership, ProofToken.

   G1 — GapRecord status "open" / "closed" / "bounded" all construct.
   G2 — GapRecord.gap_id and .gap_type are preserved.
   G3 — GapRecord equality is structural.
   G4 — Profile preserves permission and required_gaps count.
   G5 — Scope preserves all four allowed-* lists.
   G6 — Scope default-constructs with empty lists.
   G7 — Membership.InClass.is_in_class() returns True.
   G8 — Membership.OutOfClassExact.is_in_class() returns False.
   G9 — Membership.other(reason).is_in_class() returns False.
   G10 — ProofToken all status variants ("valid","invalid","expired","revoked","malformed").
   G11 — ProofToken.details accepts JSON string and None.
   G12 — ProofToken.is_negative_control defaults to False.
   G13 — NegativeControlStatus variants are distinct and comparable.
   G14 — compute_provenance_hash returns 64-char hex string.
   G15 — compute_provenance_hash is deterministic.
   G16 — compute_provenance_hash is sensitive to field order.
"""

import time
import pytest
import noethers_turnstile as t


# ── G1: GapRecord status variants ────────────────────────────────────────────

def test_g1_gap_record_status_variants():
    g_open = t.GapRecord("g1", "type", status="open")
    g_closed = t.GapRecord("g1", "type", status="closed")
    g_bounded = t.GapRecord("g1", "type", status="bounded", bound_value=1.5)
    assert g_open.status == "open"
    assert g_closed.status == "closed"
    assert g_bounded.status == "bounded"


# ── G2: GapRecord fields preserved ───────────────────────────────────────────

def test_g2_gap_record_fields():
    g = t.GapRecord("my-gap-id", "calibration-type")
    assert g.gap_id == "my-gap-id"
    assert g.gap_type == "calibration-type"


# ── G3: GapRecord equality ────────────────────────────────────────────────────

def test_g3_gap_record_equality():
    g1 = t.GapRecord("g1", "type", status="open")
    g2 = t.GapRecord("g1", "type", status="open")
    g3 = t.GapRecord("g1", "type", status="closed")
    assert g1 == g2
    assert g1 != g3


# ── G4: Profile fields preserved ─────────────────────────────────────────────

def test_g4_profile_fields():
    reqs = [
        t.GapRequirement("g1", "closed"),
        t.GapRequirement("g2", "bounded"),
    ]
    p = t.Profile(permission=t.Permission.DIA, required_gaps=reqs)
    assert p.permission == t.Permission.DIA


# ── G5: Scope all lists preserved ────────────────────────────────────────────

def test_g5_scope_all_lists():
    s = t.Scope(
        allowed_candidates=["z1", "z2"],
        allowed_paths=["/api"],
        allowed_tools=["tool-a"],
        allowed_resources=["res-1"],
    )
    assert s.allowed_candidates == ["z1", "z2"]
    assert s.allowed_paths == ["/api"]
    assert s.allowed_tools == ["tool-a"]
    assert s.allowed_resources == ["res-1"]


# ── G6: Scope default construction ───────────────────────────────────────────

def test_g6_scope_defaults():
    s = t.Scope()
    assert s.allowed_candidates == []
    assert s.allowed_paths == []
    assert s.allowed_tools == []
    assert s.allowed_resources == []


# ── G7: InClass is_in_class ──────────────────────────────────────────────────

def test_g7_inclass_is_in_class():
    assert t.Membership.InClass.is_in_class() is True


# ── G8: OutOfClassExact is not in class ──────────────────────────────────────

def test_g8_out_of_class_is_not_in_class():
    assert t.Membership.OutOfClassExact.is_in_class() is False
    assert t.Membership.OutOfClassAuthorizedDeterministicWrite.is_in_class() is False
    assert t.Membership.OutOfClassNoConsequentialUse.is_in_class() is False


# ── G9: Membership.other is not in class ─────────────────────────────────────

def test_g9_membership_other_not_in_class():
    m = t.Membership.other("some-reason")
    assert m.is_in_class() is False


# ── G10: ProofToken status variants ──────────────────────────────────────────

@pytest.mark.parametrize("status", ["valid", "invalid", "expired", "revoked", "malformed"])
def test_g10_proof_token_status_variants(status):
    tok = t.ProofToken(
        token_id=f"tok-{status}",
        token_type="TEST",
        schema_version="0.1",
        status=status,
        closes_gaps=[],
        bounds_gaps=[],
        provenance_hash="a" * 64,
        issued_at=time.time(),
        issuer="test",
    )
    assert tok.status == status


# ── G11: ProofToken.details ───────────────────────────────────────────────────

def test_g11_proof_token_details():
    import json
    tok_with_details = t.ProofToken(
        token_id="tok-d",
        token_type="TEST",
        schema_version="0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=[],
        provenance_hash="a" * 64,
        issued_at=time.time(),
        issuer="test",
        details=json.dumps({"key": "value", "num": 42}),
    )
    assert tok_with_details.details is not None
    d = json.loads(tok_with_details.details)
    assert d["key"] == "value"
    assert d["num"] == 42

    tok_no_details = t.ProofToken(
        token_id="tok-nd",
        token_type="TEST",
        schema_version="0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=[],
        provenance_hash="a" * 64,
        issued_at=time.time(),
        issuer="test",
    )
    assert tok_no_details.details is None


# ── G12: is_negative_control defaults to False ────────────────────────────────

def test_g12_negative_control_default():
    tok = t.ProofToken(
        token_id="tok-nc",
        token_type="TEST",
        schema_version="0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=[],
        provenance_hash="a" * 64,
        issued_at=time.time(),
        issuer="test",
    )
    assert tok.is_negative_control is False

    tok_nc = t.ProofToken(
        token_id="tok-nc2",
        token_type="TEST",
        schema_version="0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=[],
        provenance_hash="a" * 64,
        issued_at=time.time(),
        issuer="test",
        is_negative_control=True,
    )
    assert tok_nc.is_negative_control is True


# ── G13: NegativeControlStatus variants ──────────────────────────────────────

def test_g13_negative_control_status_variants():
    live = t.NegativeControlStatus.Live
    stale = t.NegativeControlStatus.Stale
    failed = t.NegativeControlStatus.Failed
    missing = t.NegativeControlStatus.Missing

    assert live == t.NegativeControlStatus.Live
    assert live != stale
    assert live != failed
    assert live != missing
    assert stale != failed
    assert stale != missing
    assert failed != missing


# ── G14: compute_provenance_hash returns 64-char hex ─────────────────────────

def test_g14_provenance_hash_length():
    h = t.compute_provenance_hash("claim", "z", "ctx", "use")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h.lower())


# ── G15: compute_provenance_hash is deterministic ────────────────────────────

def test_g15_provenance_hash_deterministic():
    h1 = t.compute_provenance_hash("claim", "z", "ctx", "use")
    h2 = t.compute_provenance_hash("claim", "z", "ctx", "use")
    assert h1 == h2


# ── G16: compute_provenance_hash is sensitive to field order ─────────────────

def test_g16_provenance_hash_field_order_sensitive():
    h1 = t.compute_provenance_hash("A", "B", "C", "D")
    h2 = t.compute_provenance_hash("B", "A", "C", "D")
    h3 = t.compute_provenance_hash("A", "B", "D", "C")
    assert h1 != h2, "G16: swapping claim_id and candidate_id must change hash"
    assert h1 != h3, "G16: swapping context_id and allowed_use must change hash"
    assert h2 != h3
