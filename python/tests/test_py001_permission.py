"""PY-001 — Permission type: ordering, meet, string conversion, hash.

   P1 — 12 variants exist and are distinct objects.
   P2 — Total order: OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA < REV < AEX < ALR < AAA.
   P3 — meet() returns the lesser of two permissions.
   P4 — meet() is commutative.
   P5 — meet() is idempotent: p.meet(p) == p.
   P6 — str() returns the short tag (e.g. "DIA").
   P7 — repr() returns "Permission.<tag>".
   P8 — Permission.from_str() round-trips every variant.
   P9 — Permission.from_str() raises ValueError on unknown string.
   P10 — Permissions are hashable (usable as dict keys / in sets).
   P11 — Equality is structural, not identity-based.
   P12 — DIA.meet(AAA) == DIA (ceiling is correctly truncated at authority_ceiling).
"""

import pytest
import noethers_turnstile as t

ALL_PERMS = [
    t.Permission.OOC, t.Permission.EXP, t.Permission.REF, t.Permission.UNS,
    t.Permission.ETA, t.Permission.ESC, t.Permission.ROL, t.Permission.DIA,
    t.Permission.REV, t.Permission.AEX, t.Permission.ALR, t.Permission.AAA,
]

PERM_TAGS = ["OOC", "EXP", "REF", "UNS", "ETA", "ESC", "ROL", "DIA", "REV", "AEX", "ALR", "AAA"]


# ── P1: All 12 variants exist ─────────────────────────────────────────────────

def test_p1_twelve_variants_exist():
    assert len(ALL_PERMS) == 12
    # All distinct
    assert len(set(ALL_PERMS)) == 12


# ── P2: Total order is correct ────────────────────────────────────────────────

def test_p2_total_order_ascending():
    for i in range(len(ALL_PERMS) - 1):
        assert ALL_PERMS[i] < ALL_PERMS[i + 1], (
            f"P2: {ALL_PERMS[i]} should be < {ALL_PERMS[i+1]}"
        )


def test_p2_ooc_is_minimum():
    for p in ALL_PERMS[1:]:
        assert t.Permission.OOC < p


def test_p2_aaa_is_maximum():
    for p in ALL_PERMS[:-1]:
        assert p < t.Permission.AAA


def test_p2_le_ge_operators():
    assert t.Permission.DIA <= t.Permission.DIA
    assert t.Permission.DIA >= t.Permission.DIA
    assert t.Permission.OOC <= t.Permission.AAA
    assert t.Permission.AAA >= t.Permission.OOC


# ── P3: meet() returns the lesser ────────────────────────────────────────────

def test_p3_meet_returns_lesser():
    assert t.Permission.DIA.meet(t.Permission.OOC) == t.Permission.OOC
    assert t.Permission.AAA.meet(t.Permission.DIA) == t.Permission.DIA
    assert t.Permission.OOC.meet(t.Permission.AAA) == t.Permission.OOC


# ── P4: meet() is commutative ────────────────────────────────────────────────

def test_p4_meet_is_commutative():
    for i, a in enumerate(ALL_PERMS):
        for b in ALL_PERMS[i:]:
            assert a.meet(b) == b.meet(a), f"P4: {a}.meet({b}) != {b}.meet({a})"


# ── P5: meet() is idempotent ─────────────────────────────────────────────────

def test_p5_meet_is_idempotent():
    for p in ALL_PERMS:
        assert p.meet(p) == p, f"P5: {p}.meet({p}) != {p}"


# ── P6: str() returns the short tag ──────────────────────────────────────────

def test_p6_str_returns_tag():
    for perm, tag in zip(ALL_PERMS, PERM_TAGS):
        assert str(perm) == tag, f"P6: str({perm}) should be '{tag}'"


# ── P7: repr() returns Permission.<tag> ──────────────────────────────────────

def test_p7_repr_format():
    for perm, tag in zip(ALL_PERMS, PERM_TAGS):
        assert repr(perm) == f"Permission.{tag}", f"P7: repr({perm}) wrong"


# ── P8: from_str() round-trips every variant (case-insensitive) ──────────────

def test_p8_from_str_roundtrip():
    for tag in PERM_TAGS:
        p = t.Permission.from_str(tag)
        assert str(p) == tag, f"P8: from_str('{tag}') → {p} doesn't round-trip"
        # Also accepts lowercase
        p_lower = t.Permission.from_str(tag.lower())
        assert p_lower == p, f"P8: from_str is case-insensitive for '{tag}'"


# ── P9: from_str() raises ValueError on unknown string ───────────────────────

def test_p9_from_str_unknown_raises():
    with pytest.raises(ValueError, match="Unknown permission"):
        t.Permission.from_str("SUPER")
    with pytest.raises(ValueError):
        t.Permission.from_str("")
    with pytest.raises(ValueError):
        t.Permission.from_str("GODMODE")


# ── P10: Permissions are hashable ────────────────────────────────────────────

def test_p10_permissions_are_hashable():
    d = {p: str(p) for p in ALL_PERMS}
    assert len(d) == 12
    s = set(ALL_PERMS)
    assert len(s) == 12


# ── P11: Equality is structural ──────────────────────────────────────────────

def test_p11_equality_is_structural():
    assert t.Permission.DIA == t.Permission.DIA
    assert t.Permission.DIA == t.Permission.from_str("DIA")
    assert t.Permission.DIA != t.Permission.OOC


# ── P12: DIA.meet(DIA) == DIA (ceiling truncation sanity) ────────────────────

def test_p12_meet_at_ceiling():
    assert t.Permission.DIA.meet(t.Permission.AAA) == t.Permission.DIA
    assert t.Permission.AAA.meet(t.Permission.DIA) == t.Permission.DIA
