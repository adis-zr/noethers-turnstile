"""BIF integration tests (BIF-001 through BIF-007).

Uses real Bayesian network files from the bnlearn repository to confirm that
the bridge handles real-world graph topologies correctly.

All tests skip gracefully if the BIF file is not present.
See examples/pgm/README.md for download instructions.

Tier 1 (fast):  asia, cancer, earthquake, sachs, survey
Tier 2 (medium): alarm, child, insurance, hailfinder, hepar2, win95pts
Tier 3 (large): andes, link, munin1, pigs, water
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from bridge import (
    ExactInferenceToken,
    FreshnessToken,
    compile_pgm,
    fingerprint,
    fingerprint_evidence,
    fingerprint_graph,
    fingerprint_query,
    parse_bif,
    bif_to_pgm_dicts,
)

_NOW = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)

BIF_DIR = Path(__file__).parent.parent / "data" / "bif"

_RUNTIME = {
    "graph_version": "v1",
    "evidence_version": "v1",
    "certifier_registry_version": "v1",
    "algorithm_implementation_fingerprint": "bif-test",
    "token_registry_version": "v1",
}

# Tier 1–3 names used for individual named tests
_TIER1 = ["asia", "cancer", "earthquake", "sachs", "survey"]
_TIER2 = ["alarm", "child", "insurance", "hailfinder", "hepar2", "win95pts"]
_TIER3 = ["andes", "link", "munin1", "pigs", "water"]
_INDIVIDUAL_NAMES = _TIER1 + _TIER2[:1]  # asia–alarm: 6 individual tests (BIF-001–006)


def _skip_if_missing(name: str) -> None:
    path = BIF_DIR / f"{name}.bif"
    if not path.exists():
        pytest.skip(f"{name}.bif not found in {BIF_DIR}; download from https://www.bnlearn.com/bnrepository/")


def _run_bif_round_trip(name: str, with_freshness: bool = False) -> str:
    """Parse BIF, build tokens, compile, return permission string."""
    path = BIF_DIR / f"{name}.bif"
    g = parse_bif(path)
    graph, query, evidence = bif_to_pgm_dicts(g)

    tokens: list = [ExactInferenceToken(
        proof_token_id=str(uuid.uuid4()),
        token_type="ExactInferenceToken",
        status="VALID",
        issuer="bif-test",
        graph_fingerprint=fingerprint_graph(graph),
        query_fingerprint=fingerprint_query(query),
        evidence_fingerprint=fingerprint_evidence(evidence),
        algorithm_fingerprint=fingerprint("exact"),
    )]
    if with_freshness:
        tokens.append(FreshnessToken(
            proof_token_id=str(uuid.uuid4()),
            token_type="FreshnessToken",
            status="VALID",
            issuer="bif-test",
            graph_fingerprint=fingerprint_graph(graph),
            query_fingerprint=fingerprint_query(query),
            evidence_fingerprint=fingerprint_evidence(evidence),
        ))

    result = compile_pgm(
        graph=graph, query=query, evidence=evidence,
        algorithm="exact", tokens=tokens,
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW,
        ttl_seconds=None,
    )
    return result.permission()


# ── BIF-001 through BIF-006: individual named tests ───────────────────────────

@pytest.mark.parametrize("name", _INDIVIDUAL_NAMES)
def test_bif_exact_token_earns_aex(name):
    """ExactInferenceToken on a real BIF graph → AEX (approximation closed, freshness open)."""
    _skip_if_missing(name)
    perm = _run_bif_round_trip(name, with_freshness=False)
    assert perm == "AEX", f"{name}: expected AEX, got {perm}"


@pytest.mark.parametrize("name", _INDIVIDUAL_NAMES)
def test_bif_exact_plus_freshness_earns_aex(name):
    """ExactInferenceToken + FreshnessToken on a real BIF graph → AEX, not ALR.

    ALR requires model_specification_gap BOUNDED.  ExactInferenceToken + FreshnessToken
    close the approximation, identity, and freshness gaps but provide no evidence
    that the model is adequate for the real-world target.  AEX is the ceiling.
    """
    _skip_if_missing(name)
    perm = _run_bif_round_trip(name, with_freshness=True)
    assert perm == "AEX", f"{name}: expected AEX (model_specification_gap open), got {perm}"


# ── BIF-007: parametrized sweep over all available BIF files ─────────────────

def _available_bif_names() -> list[str]:
    if not BIF_DIR.exists():
        return []
    return [p.stem for p in sorted(BIF_DIR.glob("*.bif"))]


@pytest.mark.parametrize("name", _available_bif_names() or ["_no_bif_files"])
def test_bif_007_no_tokens_gives_dia(name):
    """BIF-007: No tokens on any BIF graph → DIA (all gaps open, in-class floor)."""
    if name == "_no_bif_files":
        pytest.skip(f"No BIF files found in {BIF_DIR}")
    _skip_if_missing(name)

    path = BIF_DIR / f"{name}.bif"
    g = parse_bif(path)
    graph, query, evidence = bif_to_pgm_dicts(g)

    result = compile_pgm(
        graph=graph, query=query, evidence=evidence,
        algorithm="exact", tokens=[],
        claim_class="exact_inference_result",
        runtime=_RUNTIME, authority_ceiling="ALR", issued_at=_NOW,
        ttl_seconds=None,
    )
    perm = result.permission()
    assert perm == "DIA", f"{name}: expected DIA (no tokens), got {perm}"
