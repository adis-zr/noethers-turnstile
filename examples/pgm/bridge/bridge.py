"""PGM → turnstile bridge.

Translates PGM problem inputs (graph, query, evidence, algorithm, tokens) into
a turnstile ProofContext and compiles it into a LiveJudgment.

This is the primary integration point for the example.  It demonstrates how a
domain adapter maps its evidence model onto turnstile's gap/profile/token API.

Adapted from ecds-pgm/ecds_pgm/turnstile_bridge.py.  Key differences:
- No dependency on ecds-pgm or ecds-core — uses only local bridge/ modules.
- Takes plain keyword arguments instead of PGMAdapterInput.
- Returns BridgeResult which bundles live + ctx + runtime for easy inspection.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import turnstile as t

from .claims import GAP_BASIS, PROFILE_REQUIREMENTS
from .fingerprints import fingerprint, fingerprint_evidence, fingerprint_graph, fingerprint_query
from .tokens import (
    CertifiedBoundToken,
    ExactInferenceToken,
    FreshnessToken,
    ModelIdentityToken,
)

# Required runtime keys — spec must include all of these to be IN_CLASS.
_REQUIRED_RUNTIME_KEYS = {
    "graph_version",
    "evidence_version",
    "certifier_registry_version",
    "algorithm_implementation_fingerprint",
    "token_registry_version",
}


@dataclass
class BridgeResult:
    """Output of compile_pgm(): live judgment + the compiled context + runtime context."""
    live: t.LiveJudgment
    ctx: t.ProofContext
    runtime: t.RuntimeContext

    def permission(self) -> str:
        """Return the permission string (never raises; returns 'EXP' if expired)."""
        return self.live.permission_str(self.runtime)


def _is_in_class(runtime: dict) -> bool:
    """Class predicate: all required keys present with non-empty string values.

    Key presence alone is not sufficient — None or "" would pass a key-only
    check while still indicating an unregistered or misconfigured runtime.
    """
    for key in _REQUIRED_RUNTIME_KEYS:
        val = runtime.get(key)
        if not isinstance(val, str) or not val.strip():
            return False
    return True


def build_profiles(claim_class: str) -> list[t.Profile]:
    """Build turnstile Profile objects from PROFILE_REQUIREMENTS."""
    reqs = PROFILE_REQUIREMENTS.get(claim_class, {})
    profiles: list[t.Profile] = [
        # DIA: always available for in-class specs; requires no specific gap closure.
        t.Profile(permission=t.Permission.DIA, required_gaps=[]),
    ]
    for perm_str, gap_reqs in reqs.items():
        profiles.append(t.Profile(
            permission=t.Permission.from_str(perm_str),
            required_gaps=[
                t.GapRequirement(gap_id=g, minimum_status=status.lower())
                for g, status in gap_reqs.items()
            ],
        ))
    return profiles


def _translate_token(
    token: Any,
    prov_hash: str,
    fp_graph: str,
    fp_query: str,
    fp_evidence: str,
    fp_algorithm: str,
    issued_at_unix: float,
) -> t.ProofToken:
    """Translate a PGM token into a turnstile ProofToken.

    Only VALID tokens whose fingerprints match the spec actually close/bound gaps.
    Invalid/revoked/expired tokens are passed through with empty gap lists so the
    derivation records them as rejected evidence.
    """
    raw_status = token.status.lower()
    closes: list[str] = []
    bounds: list[str] = []

    if token.status == "VALID":
        if isinstance(token, ExactInferenceToken):
            if (
                token.graph_fingerprint == fp_graph
                and token.query_fingerprint == fp_query
                and token.evidence_fingerprint == fp_evidence
                and token.algorithm_fingerprint == fp_algorithm
            ):
                closes = [
                    "approximation_gap",
                    "model_identity_gap",
                    "query_identity_gap",
                    "evidence_identity_gap",
                    "algorithm_reproducibility_gap",
                ]

        elif isinstance(token, CertifiedBoundToken):
            sb = token.certifier_contract.scope_binding
            if (
                sb.get("graph_fingerprint") == fp_graph
                and sb.get("query_fingerprint") == fp_query
                and sb.get("evidence_fingerprint") == fp_evidence
                and sb.get("algorithm_fingerprint") == fp_algorithm
            ):
                # When the contract's scope_binding exactly matches all four spec
                # fingerprints, the bound is fully scoped to this exact problem
                # instance — bound_scope_gap is CLOSED, not merely BOUNDED.
                closes = ["bound_scope_gap"]
                bounds = ["approximation_gap", "certifier_soundness_gap"]

        elif isinstance(token, ModelIdentityToken):
            if (
                token.graph_fingerprint == fp_graph
                and token.evidence_fingerprint == fp_evidence
            ):
                closes = ["model_identity_gap", "evidence_identity_gap"]

        elif isinstance(token, FreshnessToken):
            if (
                token.graph_fingerprint == fp_graph
                and token.query_fingerprint == fp_query
                and token.evidence_fingerprint == fp_evidence
            ):
                closes = ["freshness_gap"]

    return t.ProofToken(
        token_id=token.proof_token_id,
        token_type=token.token_type,
        schema_version="pgm-bridge/0.1.0",
        status=raw_status,
        closes_gaps=closes,
        bounds_gaps=bounds,
        provenance_hash=prov_hash,
        issued_at=issued_at_unix,
        issuer=token.issuer,
    )


_DEFAULT_TTL_SECONDS: float = 86_400.0  # 24 hours


def compile_pgm(
    graph: dict,
    query: dict,
    evidence: dict,
    algorithm: str,
    tokens: list,
    claim_class: str,
    runtime: dict | None = None,
    authority_ceiling: str = "ALR",
    issued_at: datetime | None = None,
    ttl_seconds: float | None = _DEFAULT_TTL_SECONDS,
) -> BridgeResult:
    """Compile a PGM inference problem into a turnstile LiveJudgment.

    Parameters
    ----------
    graph:            graph dict with "variables" and "factors" keys
    query:            query dict, e.g. {"target": "A", "type": "marginal"}
    evidence:         evidence dict, e.g. {"B": 1} or {}
    algorithm:        one of "exact", "certified_approximate", "uncertified_approximate"
    tokens:           list of ExactInferenceToken / CertifiedBoundToken / etc.
    claim_class:      one of ClaimClass (e.g. "exact_inference_result")
    runtime:          runtime dependency dict; must contain the 5 required keys for IN_CLASS
    authority_ceiling: hard cap on permission (e.g. "ALR", "REV")
    issued_at:        timestamp for token issuance (defaults to now)
    ttl_seconds:      context lifetime in seconds from issued_at (default 86400 = 24h).
                      Pass None for a never-expiring context (testing only).

    Returns
    -------
    BridgeResult with .permission() → str (e.g. "ALR", "AEX", "OOC")
    """
    if runtime is None:
        runtime = {}
    if issued_at is None:
        issued_at = datetime.now(timezone.utc)

    fp_graph = fingerprint_graph(graph)
    fp_query = fingerprint_query(query)
    fp_evidence = fingerprint_evidence(evidence)
    fp_algorithm = fingerprint(algorithm)

    # Stable IDs derived from spec fingerprints.
    claim_id = fp_graph
    candidate_id = fp_query
    context_id = fp_evidence

    prov_hash = t.compute_provenance_hash(claim_id, candidate_id, context_id, claim_class)
    issued_at_unix = issued_at.timestamp()

    membership = (
        t.Membership.InClass if _is_in_class(runtime)
        else t.Membership.OutOfClassExact
    )

    gaps = [t.GapRecord(gap_id=g, gap_type=g) for g in GAP_BASIS]
    profiles = build_profiles(claim_class)
    ts_tokens = [
        _translate_token(tok, prov_hash, fp_graph, fp_query, fp_evidence, fp_algorithm, issued_at_unix)
        for tok in tokens
    ]

    ctx = t.ProofContext(
        claim_id=claim_id,
        candidate_id=candidate_id,
        context_id=context_id,
        allowed_use=claim_class,
        membership=membership,
        authority_ceiling=t.Permission.from_str(authority_ceiling),
        expiry=(t.Expiry.at(issued_at_unix + ttl_seconds) if ttl_seconds is not None else t.Expiry.never()),
        gaps=gaps,
        profiles=profiles,
        tokens=ts_tokens,
        context_fingerprint=context_id,
    )
    live = t.compile(ctx)
    runtime_ctx = t.RuntimeContext(
        now_unix=time.time(),
        context_fingerprint=context_id,
    )
    return BridgeResult(live=live, ctx=ctx, runtime=runtime_ctx)


def make_runtime_context(evidence: dict) -> t.RuntimeContext:
    """Build a fresh RuntimeContext from an evidence dict."""
    return t.RuntimeContext(
        now_unix=time.time(),
        context_fingerprint=fingerprint_evidence(evidence),
    )


# Backward-compatible alias — existing tests may import the old private name.
_build_profiles = build_profiles
