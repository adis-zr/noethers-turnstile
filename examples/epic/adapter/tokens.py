"""Token constructors for MED-001.

Four token types corresponding to the four new/adapted token sketches in the spec:
  clinical.approximation_quality_bound.v1
  clinical.utility_bound.v1
  clinical.model_specification_bound.v1
  clinical.distribution_shift_bound.v1

Provenance: each token binds to (claim_id, candidate_id, context_id, allowed_use)
via the standard noethers_turnstile provenance hash.
"""
from __future__ import annotations

import json
import time
from typing import Any

import noethers_turnstile as t

from adapter.proof_context import (
    GAP_APPROXIMATION_QUALITY,
    GAP_CLINICAL_UTILITY,
    GAP_MODEL_SPECIFICATION,
    GAP_DISTRIBUTION_SHIFT,
    GAP_SHADOW_MODE_VALIDATION,
    GAP_POST_MARKET_MONITORING,
)

# PPV floor for blast_radius=auto_order (A06 detail contract).
# Grounded in Wong et al. 2021: PPV=0.12 is the documented failure case.
# Floor set at 0.20 as benchmark design parameter.
PPV_FLOOR_AUTO_ORDER = 0.20
PPV_FLOOR_NOTIFICATION = 0.15


def _provenance(claim_id: str, candidate_id: str, context_id: str, allowed_use: str) -> str:
    return t.compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use)


def approximation_quality_token(
    *,
    token_id: str,
    claim_id: str,
    candidate_id: str,
    context_id: str,
    allowed_use: str,
    model_id: str,
    dataset_id: str,
    split: str,
    auc_roc: float,
    auc_pr: float,
    brier_score: float,
    threshold: float,
    sensitivity: float,
    specificity: float,
    ppv: float,
    npv: float,
    issued_at: float | None = None,
    issuer: str = "med001.approximation_quality",
) -> t.ProofToken:
    """Token that bounds approximation_quality_gap.

    Scope: (claim_id, candidate_id, context_id, model_id, dataset_id, split).
    A token reporting only AUC cannot bound clinical_utility_gap.
    """
    return t.ProofToken(
        token_id=token_id,
        token_type="clinical.approximation_quality_bound.v1",
        schema_version="med001/0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=[GAP_APPROXIMATION_QUALITY],
        provenance_hash=_provenance(claim_id, candidate_id, context_id, allowed_use),
        issued_at=issued_at or time.time(),
        issuer=issuer,
        is_negative_control=False,
        details=json.dumps({
            "model_id": model_id,
            "dataset_id": dataset_id,
            "split": split,
            "auc_roc": auc_roc,
            "auc_pr": auc_pr,
            "brier_score": brier_score,
            "threshold": threshold,
            "sensitivity_at_threshold": sensitivity,
            "specificity_at_threshold": specificity,
            "ppv_at_threshold": ppv,
            "npv_at_threshold": npv,
        }),
    )


def clinical_utility_token(
    *,
    token_id: str,
    claim_id: str,
    candidate_id: str,
    context_id: str,
    allowed_use: str,
    model_id: str,
    alert_action: str,
    blast_radius: str,
    threshold: float,
    sensitivity: float,
    specificity: float,
    ppv: float,
    npv: float,
    sample_size: int,
    population_description: str,
    issued_at: float | None = None,
    issuer: str = "med001.clinical_utility",
) -> t.ProofToken:
    """Token that bounds clinical_utility_gap.

    Scope includes blast_radius: a token scoped to "notification" does not
    advance clinical_utility_gap for "auto_order_antibiotics".

    Detail contract: PPV must meet the floor for the given blast_radius.
    PPV < PPV_FLOOR_AUTO_ORDER for blast_radius=auto_order → token is invalid.
    """
    ppv_floor = (
        PPV_FLOOR_AUTO_ORDER if blast_radius == "auto_order" else PPV_FLOOR_NOTIFICATION
    )
    contract_ok = ppv >= ppv_floor
    token_status = "valid" if contract_ok else "invalid"

    nnt = round(1.0 / ppv, 2) if ppv > 0 else float("inf")
    false_alert_rate = round(1.0 - specificity, 4)

    return t.ProofToken(
        token_id=token_id,
        token_type="clinical.utility_bound.v1",
        schema_version="med001/0.1",
        status=token_status,
        closes_gaps=[],
        bounds_gaps=[GAP_CLINICAL_UTILITY] if contract_ok else [],
        provenance_hash=_provenance(claim_id, candidate_id, context_id, allowed_use),
        issued_at=issued_at or time.time(),
        issuer=issuer,
        is_negative_control=False,
        details=json.dumps({
            "model_id": model_id,
            "alert_action": alert_action,
            "blast_radius": blast_radius,
            "threshold": threshold,
            "sensitivity": sensitivity,
            "specificity": specificity,
            "ppv": ppv,
            "npv": npv,
            "nnt": nnt,
            "false_alert_rate": false_alert_rate,
            "population_description": population_description,
            "sample_size": sample_size,
            "ppv_floor_applied": ppv_floor,
            "detail_contract_ok": contract_ok,
        }),
    )


def model_specification_token(
    *,
    token_id: str,
    claim_id: str,
    candidate_id: str,
    context_id: str,
    allowed_use: str,
    training_target: str,
    action_target: str,
    adequacy_argument: str,
    issued_at: float | None = None,
    issuer: str = "med001.model_specification",
) -> t.ProofToken:
    """Token that bounds model_specification_gap."""
    return t.ProofToken(
        token_id=token_id,
        token_type="clinical.model_specification_bound.v1",
        schema_version="med001/0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=[GAP_MODEL_SPECIFICATION],
        provenance_hash=_provenance(claim_id, candidate_id, context_id, allowed_use),
        issued_at=issued_at or time.time(),
        issuer=issuer,
        is_negative_control=False,
        details=json.dumps({
            "training_target_definition": training_target,
            "action_target_definition": action_target,
            "target_adequacy_argument": adequacy_argument,
        }),
    )


def shadow_mode_validation_token(
    *,
    token_id: str,
    claim_id: str,
    candidate_id: str,
    context_id: str,
    allowed_use: str,
    deployment_site: str,
    shadow_duration_days: int,
    n_cases_evaluated: int,
    sensitivity_local: float,
    specificity_local: float,
    ppv_local: float,
    false_positive_rate_local: float,
    go_live_approved: bool,
    issued_at: float | None = None,
    issuer: str = "med001.shadow_mode_validation",
) -> t.ProofToken:
    """Token that bounds shadow_mode_validation_gap.

    Encodes NHS RCR AI Deployment Fundamentals (2024) §4.21-4.22:
    AI run in background on real local patient data; findings not used clinically;
    enriched local positive/negative cases tested; go/no-go decision recorded.
    Token is invalid (does not bound gap) if go_live_approved is False.
    """
    token_status = "valid" if go_live_approved else "invalid"
    return t.ProofToken(
        token_id=token_id,
        token_type="clinical.shadow_mode_validation.v1",
        schema_version="med001/0.1",
        status=token_status,
        closes_gaps=[],
        bounds_gaps=[GAP_SHADOW_MODE_VALIDATION] if go_live_approved else [],
        provenance_hash=_provenance(claim_id, candidate_id, context_id, allowed_use),
        issued_at=issued_at or time.time(),
        issuer=issuer,
        is_negative_control=False,
        details=json.dumps({
            "deployment_site": deployment_site,
            "shadow_duration_days": shadow_duration_days,
            "n_cases_evaluated": n_cases_evaluated,
            "sensitivity_local": sensitivity_local,
            "specificity_local": specificity_local,
            "ppv_local": ppv_local,
            "false_positive_rate_local": false_positive_rate_local,
            "go_live_approved": go_live_approved,
            "regulatory_basis": "NHS RCR AI Deployment Fundamentals 2024 §4.21-4.22",
        }),
    )


def post_market_monitoring_token(
    *,
    token_id: str,
    claim_id: str,
    candidate_id: str,
    context_id: str,
    allowed_use: str,
    monitoring_plan_id: str,
    review_frequency_days: int,
    performance_floor_sensitivity: float,
    performance_floor_ppv: float,
    drift_detection_method: str,
    escalation_procedure: str,
    issued_at: float | None = None,
    issuer: str = "med001.post_market_monitoring",
) -> t.ProofToken:
    """Token that bounds post_market_monitoring_gap.

    Encodes NHS §2.13 (ongoing post-implementation evaluation plan required
    before deployment) and FDA Draft Guidance Jan 2025 §XI (monitoring plan
    for De Novo / PMA devices). Token certifies a monitoring plan exists and
    is active — not that monitoring has completed.
    """
    return t.ProofToken(
        token_id=token_id,
        token_type="clinical.post_market_monitoring.v1",
        schema_version="med001/0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=[GAP_POST_MARKET_MONITORING],
        provenance_hash=_provenance(claim_id, candidate_id, context_id, allowed_use),
        issued_at=issued_at or time.time(),
        issuer=issuer,
        is_negative_control=False,
        details=json.dumps({
            "monitoring_plan_id": monitoring_plan_id,
            "review_frequency_days": review_frequency_days,
            "performance_floor_sensitivity": performance_floor_sensitivity,
            "performance_floor_ppv": performance_floor_ppv,
            "drift_detection_method": drift_detection_method,
            "escalation_procedure": escalation_procedure,
            "regulatory_basis": "NHS RCR AI Deployment Fundamentals 2024 §2.13; FDA Draft Guidance Jan 2025 §XI",
        }),
    )


def distribution_shift_token(
    *,
    token_id: str,
    claim_id: str,
    candidate_id: str,
    context_id: str,
    allowed_use: str,
    training_population: str,
    deployment_population: str,
    shift_method: str,
    performance_on_deployment: dict[str, Any],
    sample_size: int,
    issued_at: float | None = None,
    issuer: str = "med001.distribution_shift",
) -> t.ProofToken:
    """Token that bounds distribution_shift_gap."""
    return t.ProofToken(
        token_id=token_id,
        token_type="clinical.distribution_shift_bound.v1",
        schema_version="med001/0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=[GAP_DISTRIBUTION_SHIFT],
        provenance_hash=_provenance(claim_id, candidate_id, context_id, allowed_use),
        issued_at=issued_at or time.time(),
        issuer=issuer,
        is_negative_control=False,
        details=json.dumps({
            "training_population": training_population,
            "deployment_population": deployment_population,
            "shift_analysis_method": shift_method,
            "performance_on_deployment": performance_on_deployment,
            "sample_size": sample_size,
        }),
    )
