"""Phase 4 verification for ILS — cell-by-cell bijection-mapped check.

Loads the pre-rewrite golden from docs/specs/native_chains_golden/ils.json
and asserts that, for every (DH, RVR, f3) cell, the post-rewrite emit maps
to the golden's old-chain emit via the §7.2 ILS bijection table.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "python"))
sys.path.insert(0, str(_ROOT / "examples" / "ils"))

import noethers_turnstile as t  # noqa: E402

from ils_compiler import compile_approach  # noqa: E402
from profiles import BIJECTION, ILS_CHAIN  # noqa: E402


@pytest.fixture(scope="module")
def golden():
    path = _ROOT / "docs" / "specs" / "native_chains_golden" / "ils.json"
    return json.loads(path.read_text())


def test_chain_hash_is_stable():
    h1 = ILS_CHAIN.chain_hash()
    h2 = ILS_CHAIN.chain_hash()
    assert h1 == h2


def test_bijection_covers_all_golden_emits(golden):
    for emit in golden["distinct_emits_seen"]:
        assert emit in BIJECTION, f"Bijection missing row for old-chain emit {emit!r}"


def test_cell_by_cell_emit_matches_bijection(golden):
    rows = golden["rows"]
    mismatches = []
    for row in rows:
        j = compile_approach(
            rvr_ft=row["rvr_ft"],
            dh_ft=row["sweep_dh_ft"],
            f1_clear=row["f1_clear"],
            f3_present=row["f3_present"],
        )
        actual = j.permission.as_str()
        expected = BIJECTION[row["old_chain_emit"]]
        if actual != expected:
            mismatches.append(
                f"DH={row['sweep_dh_ft']} RVR={row['rvr_ft']} f3={row['f3_present']}: "
                f"old emit {row['old_chain_emit']} -> expected {expected}, got {actual}"
            )
    assert not mismatches, "Bijection mismatches:\n  " + "\n  ".join(mismatches[:20])


def test_judgment_chain_hash_matches_ils_chain(golden):
    row = golden["rows"][0]
    j = compile_approach(
        rvr_ft=row["rvr_ft"],
        dh_ft=row["sweep_dh_ft"],
        f1_clear=row["f1_clear"],
        f3_present=row["f3_present"],
    )
    assert j.chain_hash == ILS_CHAIN.chain_hash()


def test_collapse_invariant_ils_emit_is_not_bottom():
    """Dual-of-AM-01 (spec §7.4 #6): ILS collapses DisallowedUsesCeiling = Bottom.
    A normal-case context must not floor to Bottom — proves the §0.4 guard
    fired and the collapse is sound.
    """
    j = compile_approach(rvr_ft=2000.0, dh_ft=200.0, f1_clear=True, f3_present=False)
    assert j.permission != ILS_CHAIN.role(t.ChainRole.Bottom)
    assert j.permission.as_str() == "LAND_MANUAL"
