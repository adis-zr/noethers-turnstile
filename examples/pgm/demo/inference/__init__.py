"""
Demo inference compiler — self-contained copy of ecds-pgm/certified_inference.

Differences from the source:
- No experiments.* imports (_try_emit_residuals, _try_exact_unnorm_root, etc. removed)
- CertificateSelector instantiated with fkkl_upgrader=None, enable_c1=False, enable_tp_c1=False
- cert_policy.py stubs evaluate_c1, evaluate_tp_c1_best, boundary_size
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .candidates import Candidate, ProofToken
from .certificates import (
    Certificate, ExactCertificate, HilbertIntervalCertificate,
    InfiniteCertificate, FKKLCertificate,
)
from .compiler import (
    Compiler, CompiledPlan, Registry, default_registry,
    CertificateSelector, SelectionResult, HilbertCompositionStatus,
)
from .envelope import Envelope, Site, Signature, SiteId, build_envelope
from .memory import MemoryState
from .model import Factor, GraphicalModel, Query, Variable


@dataclass
class InferenceResult:
    posterior: list[float]
    certificate: Certificate
    memory: MemoryState
    audit: list[str]

    certificate_geometry: str = field(default="unknown")
    certified_kl: float = field(default=math.inf)
    hilbert_guard_status: Optional[HilbertCompositionStatus] = field(default=None)
    c1_status: str = field(default="not_run")
    phase2_audit: list[str] = field(default_factory=list)
    phase2_proof_tokens: list = field(default_factory=list)


def compile_inference(
    model: GraphicalModel,
    query: Query,
    memory_budget: int,
) -> InferenceResult:
    result, _ = compile_inference_with_plan(model, query, memory_budget)
    return result


def compile_inference_with_plan(
    model: GraphicalModel,
    query: Query,
    memory_budget: int,
) -> tuple[InferenceResult, CompiledPlan]:
    envelope, site_factors = build_envelope(model, query)
    registry = default_registry()
    compiler = Compiler(kernel_families=registry.kernel_families)

    plan = compiler.compile(
        envelope=envelope,
        model=model,
        site_factors=site_factors,
        memory_budget=MemoryState(memory_budget),
    )

    computed = _execute_plan_raw(plan, model)
    posterior = _normalize(computed[envelope.root])

    selector = CertificateSelector(
        fkkl_upgrader=None,
        c1_max_boundary=65536,
        enable_c1=False,
        enable_tp_c1=False,
    )
    sel_result: SelectionResult = selector.select(
        plan=plan,
        memory_budget=memory_budget,
        instance=None,
        envelope=envelope,
        residual_model=None,
        computed=None,
    )

    selected = sel_result.selected
    result = InferenceResult(
        posterior=posterior,
        certificate=selected.certificate,
        memory=plan.memory,
        audit=plan.audit_log,
        certificate_geometry=selected.certificate_geometry,
        certified_kl=selected.certified_kl,
        hilbert_guard_status=sel_result.guard_status,
        c1_status="not_run",
        phase2_audit=[selected.audit.description],
        phase2_proof_tokens=[],
    )
    return result, plan


def _execute_plan_raw(plan: CompiledPlan, model: GraphicalModel) -> dict[SiteId, list[float]]:
    envelope = plan.envelope
    topo = envelope.topological_order()
    computed: dict[SiteId, list[float]] = {}

    for sid in topo:
        candidate = plan.selected[sid]
        inputs = {dep: computed[dep] for dep in envelope.site(sid).dependencies}
        output = candidate.implementation(inputs)
        computed[sid] = output

    return computed


def _normalize(values: list[float]) -> list[float]:
    total = sum(values)
    if total <= 0.0:
        raise RuntimeError(
            "Unnormalized marginal sums to zero — model may have support issues."
        )
    return [v / total for v in values]


__all__ = [
    "compile_inference",
    "compile_inference_with_plan",
    "InferenceResult",
    "GraphicalModel",
    "Variable",
    "Factor",
    "Query",
    "MemoryState",
    "Certificate",
    "ExactCertificate",
    "HilbertIntervalCertificate",
    "InfiniteCertificate",
    "FKKLCertificate",
    "Candidate",
    "ProofToken",
    "Compiler",
    "CompiledPlan",
    "Registry",
    "default_registry",
    "Envelope",
    "Site",
    "Signature",
    "SiteId",
    "build_envelope",
    "HilbertCompositionStatus",
    "SelectionResult",
]
