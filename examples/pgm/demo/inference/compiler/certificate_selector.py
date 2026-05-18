"""
CertificateSelector — Phase 2 of the two-phase certified plan selection.

Phase 1 (Compiler.compile): selects the execution plan via Pareto-frontier DP,
comparing candidates by (exec_memory, exec_cert.kl_bound()).

Phase 2 (CertificateSelector.select): given the Phase 1 execution plan, enumerates
all registered certificate geometries that fit the residual budget
(budget - exec_memory), and selects argmin certified_kl among them.

Registered certificate geometries per execution type
------------------------------------------------------
exact execution:   exact_cert    (cert_memory=0, kl=0.0)
hilbert execution: hilbert_cert  (cert_memory=0, kl=hilbert_bound)
                               (excluded when Hilbert composition guard fires)
                   c1_cert       (cert_memory=joint_size*16, kl=c1_bound)
                   fkkl_cert     (cert_memory=2*|root|*8, kl=fkkl_bound)
infinite/support:  infinite_cert (cert_memory=0, kl=inf)

The selection is provably argmin certified_kl because:
- The registered set is small and fully enumerated
- FK-KL and C1 are checked for memory feasibility before being included
- The selector returns all_feasible so callers can verify selected_is_argmin

Hilbert composition guard:
- When multiple Hilbert sites share output variable scopes, the scalar additive
  Hilbert bound KL <= sum_i osc(s_i) is unsound.
- hilbert_composition_guard() detects this and excludes the Hilbert geometry,
  so C1 (or FK-KL, or infinite) is used instead.

Injected dependencies (no import from certified_inference.experiments at module level):
- fkkl_upgrader: Optional[FKKLCertUpgrader]
- residual_model: Optional[ResidualModel]   — supplied per-call
- computed: Optional[dict]                  — execution outputs, supplied per-call
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from ..candidates import CertifiedPlanCandidate, ProofToken
from ..certificates import (
    Certificate,
    ExactCertificate,
    FKKLCertificate,
    HilbertIntervalCertificate,
    InfiniteCertificate,
)
from ..envelope import Envelope
from .frontier import CompiledPlan
from .cert_policy import (
    hilbert_composition_guard,
    evaluate_c1,
    evaluate_tp_c1,
    evaluate_tp_c1_best,
    evaluate_tp_c1_residual_range,
    boundary_size,
    _C1_BYTES_PER_ENTRY,
    HilbertCompositionStatus,
    BoundaryQSource,
    TiltedPartitionWitness,
)

if TYPE_CHECKING:
    # Avoid circular import: experiments imports from compiler, not the other way.
    # The actual FKKLCertUpgrader instance is passed in at runtime.
    pass


@dataclass
class SelectionResult:
    """
    Result of Phase 2 certificate selection.

    selected:          the CertifiedPlanCandidate with minimum certified_kl
    all_feasible:      all registered candidates that fit peak_memory <= budget
    selected_is_argmin: True iff selected.certified_kl == min over all_feasible
    guard_status:      Hilbert composition guard result (None for non-Hilbert plans)
    proof_tokens:      the actual proof-token objects used by the selected certifier
                       (BoundaryQSource for C1, TiltedPartitionWitness for TP-C1,
                       empty list for exact/hilbert/fkkl/infinite)
    """
    selected: CertifiedPlanCandidate
    all_feasible: list[CertifiedPlanCandidate]
    selected_is_argmin: bool
    guard_status: Optional[HilbertCompositionStatus] = None
    proof_tokens: list[Any] = None  # populated post-init; list[BoundaryQSource | TiltedPartitionWitness]

    def __post_init__(self):
        if self.proof_tokens is None:
            self.proof_tokens = []


class CertificateSelector:
    """
    Phase 2: enumerate registered certificate geometries and select argmin KL.

    Injected dependencies (no experiments-level import at module load):
    - fkkl_upgrader: Optional[FKKLCertUpgrader] — pass None to disable FK-KL
    - c1_max_boundary: int — max joint boundary size for C1 (default 65536 = ~1MB)

    The Hilbert composition guard is always active: when multiple Hilbert sites
    share output variable scopes, the scalar Hilbert cert is excluded and C1
    (or FK-KL, or infinite) is used instead.
    """

    def __init__(
        self,
        fkkl_upgrader: Optional[Any] = None,
        c1_max_boundary: int = 65536,
        enable_c1: bool = False,
        enable_tp_c1: bool = True,
        tp_c1_max_joint: int = 2097152,
        tp_c1_max_bucket_entries: int = 65536,
        tp_c1_max_cutset_states: int = 4096,
        tp_c1_max_remainder_joint: int = 65536,
    ) -> None:
        # Any type to avoid importing FKKLCertUpgrader at module level
        self._upgrader = fkkl_upgrader
        self._c1_max_boundary = c1_max_boundary
        # C1 is disabled by default: the pre-normalization boundary bound is not yet
        # proven sound for all cases (normalization correction missing).
        self._enable_c1 = enable_c1
        # TP-C1: oracle-free Rényi bound via tilted partition function
        # evaluate_tp_c1_best tries exact VE, then cutset, then WMB Hölder upper
        self._enable_tp_c1 = enable_tp_c1
        self._tp_c1_max_joint = tp_c1_max_joint
        self._tp_c1_max_bucket_entries = tp_c1_max_bucket_entries
        self._tp_c1_max_cutset_states = tp_c1_max_cutset_states
        self._tp_c1_max_remainder_joint = tp_c1_max_remainder_joint

    def select(
        self,
        plan: CompiledPlan,
        memory_budget: int,
        instance: Any,       # ModelInstance — typed Any to avoid experiments import
        envelope: Envelope,
        residual_model: Optional[Any] = None,   # ResidualModel — supplied post-execution
        computed: Optional[dict] = None,        # execution outputs — supplied post-execution
        exact_unnorm_root: Optional[list] = None,     # for normalized_root C1
        exact_unnorm_boundary: Optional[list] = None, # for surrogate_boundary_elimination C1
        model: Optional[Any] = None,            # GraphicalModel, for surrogate VE
    ) -> SelectionResult:
        """
        Enumerate all feasible registered certificate geometries and return argmin.

        Parameters
        ----------
        plan:          Phase 1 CompiledPlan (execution plan + execution certificate)
        memory_budget: the user's memory budget in bytes
        instance:      ModelInstance (needed by FK-KL upgrader for exact_unnorm)
        envelope:      the elimination envelope (needed for root output size)

        Returns
        -------
        SelectionResult with selected candidate, all feasible candidates, argmin flag.
        """
        exec_cert = plan.certificate
        exec_mem = plan.memory.bytes
        residual_budget = memory_budget - exec_mem

        candidates: list[CertifiedPlanCandidate] = []
        # Parallel list: proof tokens for each candidate (by index).
        # BoundaryQSource for C1, TiltedPartitionWitness for TP-C1, empty list otherwise.
        candidate_tokens: list[list[Any]] = []
        guard_status = None  # filled below for Hilbert plans

        if isinstance(exec_cert, ExactCertificate):
            candidates.append(CertifiedPlanCandidate(
                execution_kernel="exact",
                certificate_geometry="exact",
                exec_memory=exec_mem,
                cert_memory=0,
                peak_memory=exec_mem,
                certificate=exec_cert,
                certified_kl=0.0,
                audit=ProofToken("exact execution: exact certificate, KL=0"),
            ))
            candidate_tokens.append([])

        elif isinstance(exec_cert, HilbertIntervalCertificate):
            hilbert_kl = exec_cert.kl_bound()

            # Run Hilbert composition guard
            guard_status = hilbert_composition_guard(plan)

            if guard_status.hb_composition_valid:
                # Geometry 1: hilbert_cert (sound; cert_memory=0)
                candidates.append(CertifiedPlanCandidate(
                    execution_kernel="hilbert",
                    certificate_geometry="hilbert",
                    exec_memory=exec_mem,
                    cert_memory=0,
                    peak_memory=exec_mem,
                    certificate=exec_cert,
                    certified_kl=hilbert_kl,
                    audit=ProofToken(
                        f"hilbert execution: Hölder interval certificate, "
                        f"KL≤{hilbert_kl:.4g}"
                    ),
                ))
                candidate_tokens.append([])
            # else: guard fired — scalar Hilbert cert is excluded

            # Geometry 2: C1 certificate (joint log-MGF over residual boundary)
            # Disabled by default: C1 bounds the pre-normalization boundary KL,
            # which is not a provably sound upper bound for the normalized posterior KL
            # in all cases (normalization correction needed).
            if self._enable_c1 and residual_model is not None and computed is not None:
                root_output = computed.get(plan.envelope.root)
                c1_val, c1_mem, c1_status, _, _, q_source = evaluate_c1(
                    residual_model, computed, plan,
                    max_residual_joint=self._c1_max_boundary,
                    root_output=root_output,
                    exact_unnorm_root=exact_unnorm_root,
                    exact_unnorm_boundary=exact_unnorm_boundary,
                    cert_budget=residual_budget,
                    model=model,
                )
                # Hard gate: C1 is admitted only when boundary Q is proven correct.
                # q_source.is_proven_valid is False for "skipped_wrong_q_unproven",
                # "oracle_unavailable", and any other unproven case.
                if (
                    c1_val is not None
                    and q_source.is_proven_valid
                    and c1_mem <= residual_budget
                ):
                    from ..certificates import FKKLCertificate as _FKKLCert
                    c1_cert_obj = _FKKLCert(bound=c1_val, active_h=0.0)
                    candidates.append(CertifiedPlanCandidate(
                        execution_kernel="hilbert",
                        certificate_geometry="c1",
                        exec_memory=exec_mem,
                        cert_memory=c1_mem,
                        peak_memory=exec_mem + c1_mem,
                        certificate=c1_cert_obj,
                        certified_kl=c1_val,
                        audit=ProofToken(
                            f"hilbert execution + C1 certificate ({q_source.q_source}): "
                            f"KL≤{c1_val:.4g}, boundary={boundary_size(residual_model)}"
                        ),
                    ))
                    candidate_tokens.append([q_source])

            # Geometry 3: fkkl_cert — only if upgrader registered and cert_mem fits
            if self._upgrader is not None:
                root_output_size = (
                    envelope.site(envelope.root).output_signature.num_entries
                )
                fkkl_cert_mem = 2 * root_output_size * 8
                if fkkl_cert_mem <= residual_budget:
                    upgrade = self._upgrader.try_upgrade(plan, instance, envelope)
                    if upgrade is not None:
                        fkkl_obj = FKKLCertificate(
                            bound=upgrade.fkkl_cert,
                            active_h=upgrade.active_h,
                        )
                        candidates.append(CertifiedPlanCandidate(
                            execution_kernel="hilbert",
                            certificate_geometry="fkkl",
                            exec_memory=exec_mem,
                            cert_memory=fkkl_cert_mem,
                            peak_memory=exec_mem + fkkl_cert_mem,
                            certificate=fkkl_obj,
                            certified_kl=upgrade.fkkl_cert,
                            audit=ProofToken(
                                f"hilbert execution + FK-KL root-boundary certificate: "
                                f"KL≤{upgrade.fkkl_cert:.4g}, active_h={upgrade.active_h:.4g}"
                            ),
                        ))
                        candidate_tokens.append([])

            # Geometry 4: tp_c1_cert — oracle-free Rényi bound via tilted partition
            # evaluate_tp_c1_best tries: exact VE → cutset VE → WMB Hölder upper
            if self._enable_tp_c1 and residual_model is not None and computed is not None:
                tp_kl, tp_mem, tp_status, _, tp_witness = evaluate_tp_c1_best(
                    residual_model, computed, plan,
                    model=model,
                    max_joint_size=self._tp_c1_max_joint,
                    max_bucket_entries=self._tp_c1_max_bucket_entries,
                    max_cutset_states=self._tp_c1_max_cutset_states,
                    max_remainder_joint=self._tp_c1_max_remainder_joint,
                )
                if tp_kl is not None and tp_witness.is_proven_valid and tp_status == "selected":
                    from ..certificates import FKKLCertificate as _FKKLCert2
                    tp_cert_obj = _FKKLCert2(bound=tp_kl, active_h=tp_witness.best_alpha)
                    candidates.append(CertifiedPlanCandidate(
                        execution_kernel="hilbert",
                        certificate_geometry="tp_c1",
                        exec_memory=exec_mem,
                        cert_memory=0,   # scratch-only; no residual store needed
                        peak_memory=exec_mem,
                        certificate=tp_cert_obj,
                        certified_kl=tp_kl,
                        audit=ProofToken(
                            f"hilbert execution + TP-C1 ({tp_witness.method}, oracle-free): "
                            f"KL≤{tp_kl:.4g}, alpha*={tp_witness.best_alpha:.4g}"
                        ),
                    ))
                    candidate_tokens.append([tp_witness])

            # If no finite cert available (guard fired + no C1/FK-KL/TP-C1), fall back to infinite
            if not candidates:
                reason = "Hilbert guard fired: overlapping residual scopes; no C1 available"
                candidates.append(CertifiedPlanCandidate(
                    execution_kernel="hilbert",
                    certificate_geometry="infinite",
                    exec_memory=exec_mem,
                    cert_memory=0,
                    peak_memory=exec_mem,
                    certificate=InfiniteCertificate(reason=reason),
                    certified_kl=math.inf,
                    audit=ProofToken(reason),
                ))
                candidate_tokens.append([])

        elif isinstance(exec_cert, InfiniteCertificate):
            candidates.append(CertifiedPlanCandidate(
                execution_kernel="hilbert",
                certificate_geometry="infinite",
                exec_memory=exec_mem,
                cert_memory=0,
                peak_memory=exec_mem,
                certificate=exec_cert,
                certified_kl=math.inf,
                audit=ProofToken("infinite certificate — support failure or unrepresentable"),
            ))
            candidate_tokens.append([])

        else:
            # Unknown certificate type — treat as infinite
            candidates.append(CertifiedPlanCandidate(
                execution_kernel="unknown",
                certificate_geometry="infinite",
                exec_memory=exec_mem,
                cert_memory=0,
                peak_memory=exec_mem,
                certificate=InfiniteCertificate(reason="unknown certificate type"),
                certified_kl=math.inf,
                audit=ProofToken(f"unknown certificate type: {type(exec_cert).__name__}"),
            ))
            candidate_tokens.append([])

        feasible = [c for c in candidates if c.peak_memory <= memory_budget]
        if not feasible:
            # Shouldn't happen (exec_mem <= budget was already checked by compiler),
            # but fall back to all candidates to avoid empty selection.
            feasible = candidates

        selected = min(feasible, key=lambda c: (c.certified_kl, c.cert_memory))
        min_kl = min(c.certified_kl for c in feasible)
        selected_is_argmin = abs(selected.certified_kl - min_kl) < 1e-9

        # Retrieve proof tokens for the selected candidate via index in candidates list.
        selected_idx = candidates.index(selected)
        selected_tokens = candidate_tokens[selected_idx] if selected_idx < len(candidate_tokens) else []

        # Attach phase2 result to the plan for downstream inspection
        plan.phase2_candidate = selected

        return SelectionResult(
            selected=selected,
            all_feasible=feasible,
            selected_is_argmin=selected_is_argmin,
            guard_status=guard_status,
            proof_tokens=selected_tokens,
        )
