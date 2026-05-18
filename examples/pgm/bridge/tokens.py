"""Token types for the PGM bridge.

Copied from ecds-pgm/ecds_pgm/tokens.py — no external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

CertifierType = Literal[
    "exact",
    "interval_bound",
    "residual_bound",
    "problem_class_bound",
    "empirical_comparison",
]

GuaranteeType = Literal[
    "exact",
    "marginal_interval",
    "total_variation_bound",
    "residual_bound",
    "logZ_bound",
    "map_gap_bound",
]


@dataclass
class CertifierContract:
    certifier_id: str
    certifier_version: str
    certifier_type: CertifierType
    guarantee_type: GuaranteeType
    guarantee_statement: str
    scope_binding: dict   # graph/query/evidence/algorithm fingerprints
    implementation_fingerprint: str
    issuer_id: str
    issued_at: datetime
    expires_at: datetime | None = None
    revocation_pointer: str = ""
    assumptions: list[str] = field(default_factory=list)


@dataclass
class CertifiedBoundToken:
    proof_token_id: str
    token_type: Literal["CertifiedBoundToken"]
    status: Literal["VALID", "INVALID", "EXPIRED", "REVOKED", "MALFORMED"]
    issuer: str
    certifier_contract: CertifierContract
    closes_gaps: list[str] = field(default_factory=list)
    bounds_gaps: list[str] = field(default_factory=list)


@dataclass
class ExactInferenceToken:
    proof_token_id: str
    token_type: Literal["ExactInferenceToken"]
    status: Literal["VALID", "INVALID", "EXPIRED", "REVOKED", "MALFORMED"]
    issuer: str
    graph_fingerprint: str
    query_fingerprint: str
    evidence_fingerprint: str
    algorithm_fingerprint: str
    closes_gaps: list[str] = field(default_factory=list)
    bounds_gaps: list[str] = field(default_factory=list)


@dataclass
class ModelIdentityToken:
    proof_token_id: str
    token_type: Literal["ModelIdentityToken"]
    status: Literal["VALID", "INVALID", "EXPIRED", "REVOKED", "MALFORMED"]
    issuer: str
    graph_fingerprint: str
    evidence_fingerprint: str
    closes_gaps: list[str] = field(default_factory=list)
    bounds_gaps: list[str] = field(default_factory=list)


@dataclass
class FreshnessToken:
    proof_token_id: str
    token_type: Literal["FreshnessToken"]
    status: Literal["VALID", "INVALID", "EXPIRED", "REVOKED", "MALFORMED"]
    issuer: str
    graph_fingerprint: str
    query_fingerprint: str
    evidence_fingerprint: str
    closes_gaps: list[str] = field(default_factory=list)
    bounds_gaps: list[str] = field(default_factory=list)
