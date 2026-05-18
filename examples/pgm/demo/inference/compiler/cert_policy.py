"""
Certificate policy for the demo compiler — trimmed copy of ecds-pgm cert_policy.py.

Parts 1 (Hilbert composition guard) and all dataclasses are copied verbatim.
Parts 2 (C1 evaluation) and 3 (TP-C1) are replaced with stubs that return
"not available" — they require experiments.residual_emitter and experiments.oracle
which are not included in this self-contained demo.

To recover finite KL bounds on the medium-budget row (where the guard fires),
replace these stubs with real implementations from the ecds-pgm experiments package.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..compiler.frontier import CompiledPlan


_C1_BYTES_PER_ENTRY: int = 16


@dataclass(frozen=True)
class BoundaryQSource:
    q_source: str
    q_validity: str
    is_proven_valid: bool
    reason: str

    @staticmethod
    def normalized_root(n_entries: int) -> "BoundaryQSource":
        return BoundaryQSource(
            q_source="normalized_root",
            q_validity="proven",
            is_proven_valid=True,
            reason=f"boundary=root scope; Q=root_output/Z_approx ({n_entries} entries); Lambda(1)=0",
        )

    @staticmethod
    def leaf_factorization(n_hilbert_leaves: int) -> "BoundaryQSource":
        return BoundaryQSource(
            q_source="leaf_boundary_factorization",
            q_validity="proven",
            is_proven_valid=True,
            reason=(
                f"all {n_hilbert_leaves} Hilbert sites are leaf nodes; "
                f"scope union = boundary; Q=Hilbert-product is the true boundary marginal"
            ),
        )

    @staticmethod
    def unproven(reason: str) -> "BoundaryQSource":
        return BoundaryQSource(
            q_source="hilbert_product_unproven",
            q_validity="unproven",
            is_proven_valid=False,
            reason=reason,
        )

    @staticmethod
    def surrogate_elimination(boundary_size: int, n_eliminated: int, max_intermediate_bytes: int) -> "BoundaryQSource":
        return BoundaryQSource(
            q_source="surrogate_boundary_elimination",
            q_validity="proven",
            is_proven_valid=True,
            reason=(
                f"exact VE over surrogate factor graph marginalized {n_eliminated} variables "
                f"to boundary ({boundary_size} entries); max_intermediate={max_intermediate_bytes}B"
            ),
        )

    @staticmethod
    def unavailable(reason: str) -> "BoundaryQSource":
        return BoundaryQSource(
            q_source="unavailable",
            q_validity="unproven",
            is_proven_valid=False,
            reason=reason,
        )


@dataclass(frozen=True)
class TiltedPartitionWitness:
    method: str
    is_proven_valid: bool
    best_alpha: float
    logZ_tilt: float
    logZ_P: float
    logZ_Q: float
    memory_bytes: int
    n_alpha: int
    reason: str

    @staticmethod
    def unavailable(reason: str) -> "TiltedPartitionWitness":
        return TiltedPartitionWitness(
            method="unavailable",
            is_proven_valid=False,
            best_alpha=float("nan"),
            logZ_tilt=float("nan"),
            logZ_P=float("nan"),
            logZ_Q=float("nan"),
            memory_bytes=0,
            n_alpha=0,
            reason=reason,
        )


@dataclass(frozen=True)
class HilbertCompositionStatus:
    n_hilbert_sites: int
    overlap_pairs: int
    composition_status: str
    hb_composition_valid: bool


def hilbert_composition_guard(plan: "CompiledPlan") -> HilbertCompositionStatus:
    from ..certificates import HilbertIntervalCertificate

    envelope = plan.envelope
    hilbert_sites: list[tuple[int, frozenset]] = []
    for sid, cand in plan.selected.items():
        if isinstance(cand.certificate, HilbertIntervalCertificate):
            site = envelope.site(sid)
            out_vars = frozenset(site.output_signature.variables)
            hilbert_sites.append((sid, out_vars))

    n = len(hilbert_sites)
    overlap_count = 0
    for i in range(n):
        for j in range(i + 1, n):
            _, sc_i = hilbert_sites[i]
            _, sc_j = hilbert_sites[j]
            if sc_i & sc_j:
                overlap_count += 1

    if n <= 1 or overlap_count == 0:
        return HilbertCompositionStatus(
            n_hilbert_sites=n,
            overlap_pairs=0,
            composition_status="scalar_safe",
            hb_composition_valid=True,
        )
    else:
        return HilbertCompositionStatus(
            n_hilbert_sites=n,
            overlap_pairs=overlap_count,
            composition_status="overlap_requires_residual_cert",
            hb_composition_valid=False,
        )


# ---------------------------------------------------------------------------
# Stubs — require experiments package (not included in self-contained demo)
# ---------------------------------------------------------------------------

def evaluate_c1(residual_model, computed, plan, **kwargs):
    # Stub: C1 not available without experiments package
    q_source = BoundaryQSource.unavailable("experiments package not available")
    return None, 0, "skipped", None, 0.0, q_source


def evaluate_tp_c1_best(residual_model, computed, plan, **kwargs):
    # Stub: TP-C1 not available without experiments package
    witness = TiltedPartitionWitness.unavailable("experiments package not available")
    return None, 0, "skipped", None, witness


def evaluate_tp_c1(residual_model, computed, plan, **kwargs):
    # Stub
    witness = TiltedPartitionWitness.unavailable("experiments package not available")
    return None, 0, "skipped", None, witness


def evaluate_tp_c1_residual_range(residual_model, plan, **kwargs):
    # Stub
    witness = TiltedPartitionWitness.unavailable("experiments package not available")
    return None, 0, "skipped", None, witness


def boundary_size(residual_model) -> int:
    return 0


def _boundary_equals_root_scope(envelope, residual_model) -> bool:
    return False
