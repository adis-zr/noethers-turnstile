"""GasTown authority registry — role → authority ceiling mapping.

Spec §1.2:
  dog/boot → DIA
  witness  → REV
  deacon   → ESC
  polecat  → ALR
  refinery → ALR
  mayor    → AAA
  crew     → AAA
"""

from __future__ import annotations
import noethers_turnstile as t

# Role → ACS authority ceiling (string form).  AAA means no cap in practice
# because it is the maximum in the lattice.
ROLE_CEILINGS: dict[str, str] = {
    "dog": "DIA",
    "boot": "DIA",
    "witness": "REV",
    "deacon": "ESC",
    "polecat": "ALR",
    "refinery": "ALR",
    "mayor": "AAA",
    "crew": "AAA",
}


def get_ceiling(role: str) -> t.Permission:
    """Return the authority ceiling Permission for the given role.

    If the role is not in the mapping, returns OOC (out-of-class).
    """
    tag = ROLE_CEILINGS.get(role)
    if tag is None:
        return t.Permission.OOC
    return t.Permission.from_str(tag)


def is_in_class(role: str) -> bool:
    """Return True iff the role is a known GasTown role (in-class)."""
    return role in ROLE_CEILINGS
