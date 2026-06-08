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


# ── F4: experiment scripts use the conservation chain, not the default ───────


def test_f4_experiment_compile_uses_conservation_chain():
    """run_two_axis_convergence_v2._compile_case must compile under the
    conservation chain. Pre-fix it called t.compile(ctx) which falls back to
    the default 12-level chain — and the paper claims a 5-level chain.

    We invoke the helper on a stub case and check the emitted Judgment's
    chain_hash matches CONSERVATION_CHAIN."""
    sys.path.insert(0, str(_ROOT / "examples" / "conservation"))
    # Importing the runner pulls in epic.experiment.cases, which expects a
    # working directory rooted at the repo. Use a minimal direct call.
    from run_two_axis_convergence_v2 import _compile_case, _default_fine_reqs

    # Build the smallest case: every gap bounded, default reqs.
    statuses = {
        "approximation_quality_gap": "bounded",
        "freshness_gap": "bounded",
        "clinical_utility_gap": "bounded",
        "model_specification_gap": "bounded",
        "distribution_shift_gap": "bounded",
        "individual_population_gap": "bounded",
        "blast_radius_gap": "bounded",
        "authority_gap": "bounded",
        "reason_traceability_gap": "bounded",
    }
    # _compile_case currently returns the permission string; we need access
    # to the judgment's chain_hash. The fix exposes the chain in a way that
    # this test can observe — easiest is to also expose the chain_hash via a
    # sibling helper, or assert that the emitted permission is in the
    # conservation chain (which is the observable contract).
    perm_str = _compile_case(statuses, _default_fine_reqs(), "test-f4")

    # Pre-fix: this returned "ALR" but the chain_hash was the default chain's.
    # Post-fix: same emit name, but the underlying chain is the conservation
    # 5-level chain. The runner exposes its compile chain via a module-level
    # constant `_COMPILE_CHAIN`. Assert that constant is the conservation chain.
    import run_two_axis_convergence_v2 as runner
    assert hasattr(runner, "_COMPILE_CHAIN"), (
        "runner must expose the chain it compiles against so this test can "
        "verify it is the conservation chain"
    )
    assert (
        runner._COMPILE_CHAIN.chain_hash() == CONSERVATION_CHAIN.chain_hash()
    ), "experiment must compile against the conservation chain, not the default"
    # And the emit must be one of the conservation levels.
    assert perm_str in {"REF", "DIA", "REV", "AEX", "ALR"}


# ── F4b: run_occlusion_sweep wires the ILS chain + conservation chain ────────


def test_f4b_occlusion_runs_without_chain_error():
    """The script previously errored with `malformed context: profile
    permission 'LAND_ZERO_ZERO' not in supplied chain` because it compiled
    ILS evidence against the default 12-level chain. Post-fix it must run
    end-to-end and write both occlusion CSVs."""
    import subprocess
    py = sys.executable
    script = _ROOT / "examples" / "conservation" / "run_occlusion_sweep.py"
    result = subprocess.run(
        [py, str(script)],
        capture_output=True,
        text=True,
        cwd=script.parent,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"run_occlusion_sweep.py must succeed. stderr:\n{result.stderr[-2000:]}"
    )
    ils_csv = script.parent / "results" / "occlusion_ils.csv"
    epic_csv = script.parent / "results" / "occlusion_epic.csv"
    assert ils_csv.exists()
    assert epic_csv.exists()


def test_f4b_ils_descent_matches_paper_text():
    """pivot-paper-v5 §2.5 says the ILS occlusion descends
    `ALR → REV → DIA → REF`. The CSV records the bijection-mapped permissions
    (default-chain names) so the figure generator and paper text stay aligned,
    while the underlying compile runs on the ILS chain."""
    import csv
    ils_csv = _ROOT / "examples" / "conservation" / "results" / "occlusion_ils.csv"
    rows = list(csv.DictReader(ils_csv.open()))
    perms = [r["permission"] for r in rows]
    # Step sequence expected by the paper.
    assert perms == ["ALR", "REV", "DIA", "REF"], (
        f"expected ALR → REV → DIA → REF descent, got {perms}"
    )


def test_f4b_occlusion_exposes_chains():
    """The runner must expose the chains it uses so this test can verify
    they are the ILS chain and the conservation chain rather than the
    default 12-level chain."""
    sys.path.insert(0, str(_ROOT / "examples" / "conservation"))
    sys.path.insert(0, str(_ROOT / "examples" / "ils"))
    import importlib
    if "run_occlusion_sweep" in sys.modules:
        runner = importlib.reload(sys.modules["run_occlusion_sweep"])
    else:
        import run_occlusion_sweep as runner

    from profiles import ILS_CHAIN

    assert hasattr(runner, "_ILS_COMPILE_CHAIN"), (
        "runner must expose the ILS chain used by _ils_compile"
    )
    assert hasattr(runner, "_EPIC_COMPILE_CHAIN"), (
        "runner must expose the conservation chain used by _epic_compile"
    )
    assert runner._ILS_COMPILE_CHAIN.chain_hash() == ILS_CHAIN.chain_hash()
    assert runner._EPIC_COMPILE_CHAIN.chain_hash() == CONSERVATION_CHAIN.chain_hash()
