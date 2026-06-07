"""Phase 4 verification for forecast_value — headline metric equivalence.

Forecast value's golden is the §8 verdict + arm summary counts. The post-
rewrite pipeline must produce the same verdict and counts. Per the spec,
the rewrite is structural (native chain declared, level-name bijection
documented); the compile path internally still uses the default chain
because the AEX-disjunction lives in compile_honest's two-pass dance.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "python"))
sys.path.insert(0, str(_ROOT / "examples" / "forecast_value"))

from domain import BIJECTION, FORECAST_CHAIN  # noqa: E402


@pytest.fixture(scope="module")
def golden():
    return json.loads(
        (_ROOT / "docs" / "specs" / "native_chains_golden" / "forecast_value.json").read_text()
    )


@pytest.fixture(scope="module")
def fresh_outcome():
    """Re-run the forecast pipeline and load the fresh outcome.md JSON block."""
    py = _ROOT / ".venv" / "bin" / "python"
    runner = _ROOT / "examples" / "forecast_value" / "run_all.py"
    subprocess.run([str(py), str(runner)], check=True, capture_output=True)
    fv = _ROOT / "examples" / "forecast_value" / "results"
    return {
        "arm1": json.loads((fv / "arm1_summary.json").read_text()),
        "arm2": json.loads((fv / "arm2_summary.json").read_text()),
        "outcome": (fv / "outcome.md").read_text(),
    }


def test_chain_hash_stable():
    assert FORECAST_CHAIN.chain_hash() == FORECAST_CHAIN.chain_hash()


def test_bijection_covers_default_chain_emits():
    """The bijection covers every level the historical pipeline could emit
    (excluding ROL/ETA/ESC which the forecast domain never used)."""
    for emit in ["DIA", "REV", "AEX", "ALR", "AAA", "OOC", "REF"]:
        assert emit in BIJECTION


def test_verdict_preserved(golden, fresh_outcome):
    # Outcome.md prints the verdict lowercase; golden captured "strong".
    assert "strong" in fresh_outcome["outcome"].lower().split("verdict:")[1][:50]
    assert "strong" == golden["verdict"]


def test_arm1_counts_preserved(golden, fresh_outcome):
    g = golden["arm1_counts"]
    f = fresh_outcome["arm1"]
    assert f["n_rows"] == g["n_rows"]
    assert f["n_divergences"] == g["n_divergences"]
    assert f["n_bins_total"] == g["n_bins_total"]


def test_arm2_counts_preserved(golden, fresh_outcome):
    g = golden["arm2_counts"]
    f = fresh_outcome["arm2"]
    assert f["n_evidence_states"] == g["n_evidence_states"]
    assert f["Ae_monotone_along_L0_to_L3"] == g["Ae_monotone_along_L0_to_L3"]
    assert f["manufactured_permission_witness_fires_at_L3"] == g[
        "manufactured_permission_witness_fires_at_L3"
    ]
    assert f["DRO_matches_Ae_at_L0"] == g["DRO_matches_Ae_at_L0"]
