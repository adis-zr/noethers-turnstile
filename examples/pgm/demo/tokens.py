"""
Translation layer: InferenceResult → turnstile ProofToken list.

This is the only genuinely new code in the demo (everything else is copied).
"""
from __future__ import annotations

import math
import uuid

import turnstile as t


def claim_class_for_geometry(geometry: str) -> str:
    if geometry == "exact":
        return "exact_inference_result"
    return "certified_approximate_inference"


def cert_to_proof_tokens(
    result,
    fp_graph: str,
    fp_query: str,
    fp_evidence: str,
    fp_algorithm: str,
    prov_hash: str,
    issued_at_unix: float,
) -> list[t.ProofToken]:
    geometry = result.certificate_geometry

    if geometry == "exact":
        tokens = [
            t.ProofToken(
                token_id=str(uuid.uuid4()),
                token_type="ExactInferenceToken",
                schema_version="demo/0.1.0",
                status="valid",
                closes_gaps=[
                    "approximation_gap",
                    "model_identity_gap",
                    "query_identity_gap",
                    "evidence_identity_gap",
                    "algorithm_reproducibility_gap",
                ],
                bounds_gaps=[],
                provenance_hash=prov_hash,
                issued_at=issued_at_unix,
                issuer="demo-compiler",
            ),
            t.ProofToken(
                token_id=str(uuid.uuid4()),
                token_type="FreshnessToken",
                schema_version="demo/0.1.0",
                status="valid",
                closes_gaps=["freshness_gap"],
                bounds_gaps=[],
                provenance_hash=prov_hash,
                issued_at=issued_at_unix,
                issuer="demo-runtime",
            ),
        ]

    elif geometry in ("hilbert", "fkkl", "c1", "tp_c1"):
        tokens = [
            t.ProofToken(
                token_id=str(uuid.uuid4()),
                token_type="CertifiedBoundToken",
                schema_version="demo/0.1.0",
                status="valid",
                closes_gaps=["bound_scope_gap"],
                bounds_gaps=["approximation_gap", "certifier_soundness_gap"],
                provenance_hash=prov_hash,
                issued_at=issued_at_unix,
                issuer="demo-compiler",
            ),
            t.ProofToken(
                token_id=str(uuid.uuid4()),
                token_type="FreshnessToken",
                schema_version="demo/0.1.0",
                status="valid",
                closes_gaps=["freshness_gap"],
                bounds_gaps=[],
                provenance_hash=prov_hash,
                issued_at=issued_at_unix,
                issuer="demo-runtime",
            ),
        ]

    else:
        # infinite or unknown: no evidence
        tokens = [
            t.ProofToken(
                token_id=str(uuid.uuid4()),
                token_type="InfiniteCertToken",
                schema_version="demo/0.1.0",
                status="invalid",
                closes_gaps=[],
                bounds_gaps=[],
                provenance_hash=prov_hash,
                issued_at=issued_at_unix,
                issuer="demo-compiler",
            ),
        ]

    return tokens
