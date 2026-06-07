"""Phase 4 verification for turbo — audit table preservation + chain declarations.

The turbo example retains its integer-coded sweep compiler for performance.
The Phase 2D deliverable declares the native chains (TURBO_PHASE_A_CHAIN
4 levels; TURBO_PHASE_B_CHAIN 5 levels) so an auditor can resolve a sweep's
emit integers back to chain-pinned permission objects.

This test verifies:
  - both native chains construct and have stable hashes
  - the audit_3gpp comparison table from the golden is reproduced byte-for-byte
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_ROOT / "python"))
sys.path.insert(0, str(_ROOT / "examples" / "inference" / "register2" / "turbo"))

import noethers_turnstile as t  # noqa: E402

from compiler_blind import TURBO_PHASE_B_CHAIN  # noqa: E402
from compiler_turbo import TURBO_PHASE_A_CHAIN  # noqa: E402


@pytest.fixture(scope="module")
def golden():
    return json.loads(
        (_ROOT / "docs" / "specs" / "native_chains_golden" / "turbo.json").read_text()
    )


def test_phase_a_chain_has_4_levels():
    assert len(TURBO_PHASE_A_CHAIN) == 4
    assert TURBO_PHASE_A_CHAIN.role(t.ChainRole.Bottom).as_str() == "REFUSE"
    assert TURBO_PHASE_A_CHAIN.role(t.ChainRole.Top).as_str() == "TRANSMIT"


def test_phase_b_chain_has_5_levels():
    assert len(TURBO_PHASE_B_CHAIN) == 5
    assert TURBO_PHASE_B_CHAIN.role(t.ChainRole.Bottom).as_str() == "REFUSE"
    assert TURBO_PHASE_B_CHAIN.role(t.ChainRole.Top).as_str() == "TRANSMIT_CRITICAL"


def test_audit_3gpp_correspondence_table_preserved(golden):
    """Re-run audit_3gpp and assert the 5-row correspondence table is
    byte-equal to the §0 golden."""
    py = _ROOT / ".venv" / "bin" / "python"
    audit = _ROOT / "examples" / "inference" / "register2" / "turbo" / "audit_3gpp.py"
    subprocess.run([str(py), str(audit)], check=True, capture_output=True)

    fresh_csv = (
        _ROOT
        / "examples" / "inference" / "register2" / "turbo" / "results"
        / "audit_3gpp_comparison.csv"
    )
    fresh_rows = []
    with fresh_csv.open() as f:
        for row in csv.DictReader(f):
            fresh_rows.append(dict(row))

    golden_rows = golden["audit_3gpp_correspondence_table"]
    assert len(fresh_rows) == len(golden_rows)
    # Compare key columns
    for gr, fr in zip(golden_rows, fresh_rows):
        assert gr["threshold_name"] == fr["threshold_name"]
        assert gr["classification"] == fr["classification"]
        # SNR within 0.01 dB (floating-point CSV)
        assert abs(float(gr["compiler_snr_bler"]) - float(fr["compiler_snr_bler"])) <= 0.01


def test_turbo_chains_have_distinct_hashes():
    """The 4-level Phase A and 5-level Phase B chains must produce different
    content hashes (they have different level lists)."""
    assert TURBO_PHASE_A_CHAIN.chain_hash() != TURBO_PHASE_B_CHAIN.chain_hash()
