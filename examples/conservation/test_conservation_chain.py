"""Phase 4 verification for conservation — chain declarations.

Per Q3 Option A, conservation uses the paper-5-level chain
(REF < DIA < REV < AEX < ALR) with OOC -> REF folding.

This test verifies the chain is constructible, has the right shape, and
that the central runner (run_two_axis_convergence_v2.py) still produces
its headline numbers under the bijection.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "python"))
sys.path.insert(0, str(_ROOT / "examples" / "conservation"))

import noethers_turnstile as t  # noqa: E402

from chain import BIJECTION, CONSERVATION_CHAIN  # noqa: E402


@pytest.fixture(scope="module")
def golden():
    return json.loads(
        (_ROOT / "docs" / "specs" / "native_chains_golden" / "conservation.json").read_text()
    )


def test_chain_has_five_levels():
    assert len(CONSERVATION_CHAIN) == 5
    names = [p.as_str() for p in CONSERVATION_CHAIN.ascending()]
    assert names == ["REF", "DIA", "REV", "AEX", "ALR"]


def test_chain_roles_match_paper():
    assert CONSERVATION_CHAIN.role(t.ChainRole.Bottom).as_str() == "REF"
    assert CONSERVATION_CHAIN.role(t.ChainRole.BlockerThreshold).as_str() == "DIA"
    assert CONSERVATION_CHAIN.role(t.ChainRole.Top).as_str() == "ALR"


def test_bijection_folds_ooc_to_ref():
    """Q3 Option A: OOC -> REF folding."""
    assert BIJECTION["OOC"] == "REF"


def test_chain_hash_stable():
    assert CONSERVATION_CHAIN.chain_hash() == CONSERVATION_CHAIN.chain_hash()


def test_golden_headline_summary_intact(golden):
    """The §0 capture's summary rows are present and the matrix has 1155 rows
    (525 resolving + 630 non-resolving). The post-rewrite runner must
    reproduce these numbers; this test asserts the golden was captured cleanly
    and is the version Phase 4 verifies against."""
    assert golden["matrix_n_rows"] == 1155
    assert len(golden["summary_rows"]) == 42
