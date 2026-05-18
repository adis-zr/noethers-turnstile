"""Claim classes, gap taxonomy, and permission profiles for PGM inference.

Adapted from ecds-pgm/ecds_pgm/claims.py and ecds-pgm/ecds_pgm/adapter.py.
"""

from __future__ import annotations

from typing import Literal

ClaimClass = Literal[
    "exact_inference_result",
    "certified_approximate_inference",
    "uncertified_approximate_inference",
    "inference_comparison",
]

# The 11 standard gaps for the PGM adapter path.
#
# model_specification_gap: approximation_gap proves closeness to the *supplied* model;
# this gap is whether the supplied model is adequate for the real-world target.  It must
# be at least BOUNDED before granting world-facing rollout authority (ALR/AAA) on
# certified_approximate_inference — otherwise the certificate only proves closeness to
# a model whose adequacy was never checked.
GAP_BASIS: list[str] = [
    "model_identity_gap",
    "query_identity_gap",
    "evidence_identity_gap",
    "algorithm_reproducibility_gap",
    "approximation_gap",
    "model_specification_gap",
    "certifier_soundness_gap",
    "bound_scope_gap",
    "runtime_registry_gap",
    "freshness_gap",
    "provenance_gap",
]

# Minimum gap status required per permission tier per claim class.
# Only gaps whose required status > OPEN are listed.
# "BOUNDED" = evidence constrains the gap; "CLOSED" = gap fully resolved.
PROFILE_REQUIREMENTS: dict[str, dict[str, dict[str, str]]] = {
    "exact_inference_result": {
        "REV": {
            "model_identity_gap": "BOUNDED",
            "query_identity_gap": "BOUNDED",
            "evidence_identity_gap": "BOUNDED",
        },
        "AEX": {
            "model_identity_gap": "CLOSED",
            "query_identity_gap": "CLOSED",
            "evidence_identity_gap": "CLOSED",
            "algorithm_reproducibility_gap": "BOUNDED",
        },
        "ALR": {
            "model_identity_gap": "CLOSED",
            "query_identity_gap": "CLOSED",
            "evidence_identity_gap": "CLOSED",
            "algorithm_reproducibility_gap": "BOUNDED",
            "approximation_gap": "CLOSED",
            "model_specification_gap": "BOUNDED",
            "freshness_gap": "CLOSED",
        },
        "AAA": {
            "model_identity_gap": "CLOSED",
            "query_identity_gap": "CLOSED",
            "evidence_identity_gap": "CLOSED",
            "algorithm_reproducibility_gap": "CLOSED",
            "approximation_gap": "CLOSED",
            "model_specification_gap": "CLOSED",
            "freshness_gap": "CLOSED",
        },
    },
    "certified_approximate_inference": {
        "REV": {
            "model_identity_gap": "BOUNDED",
            "query_identity_gap": "BOUNDED",
            "evidence_identity_gap": "BOUNDED",
        },
        "AEX": {
            "approximation_gap": "BOUNDED",
            "certifier_soundness_gap": "BOUNDED",
            "bound_scope_gap": "BOUNDED",
        },
        # ALR and AAA require model_specification_gap: the certified bound proves closeness
        # to the supplied model, but not that the supplied model is adequate for the target.
        # Granting world-facing rollout (ALR/AAA) without bounding this gap certifies
        # the wrong thing.
        "ALR": {
            "approximation_gap": "BOUNDED",
            "certifier_soundness_gap": "BOUNDED",
            "bound_scope_gap": "CLOSED",
            "model_specification_gap": "BOUNDED",
            "freshness_gap": "CLOSED",
        },
        "AAA": {
            "approximation_gap": "CLOSED",
            "certifier_soundness_gap": "CLOSED",
            "bound_scope_gap": "CLOSED",
            "model_specification_gap": "CLOSED",
            "freshness_gap": "CLOSED",
        },
    },
    "uncertified_approximate_inference": {
        "REV": {
            "model_identity_gap": "BOUNDED",
            "query_identity_gap": "BOUNDED",
            "evidence_identity_gap": "BOUNDED",
        },
    },
    "inference_comparison": {},
}
