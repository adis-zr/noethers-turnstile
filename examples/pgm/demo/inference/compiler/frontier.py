"""
Pareto-frontier DP compiler.

For each site in the envelope (bottom-up), maintains a Pareto frontier of
(memory, certificate) pairs. At the root, selects the feasible plan with
minimum certified KL bound.

The compiler never compares candidate identities — it only compares
(memory, certificate). Certificate types and memory composition are the
only mechanisms it uses to distinguish plans.

Adapted from archive/impl/compiler.py — main changes:
  - No pluggable Objective or MemoryModel (objective = certificate.kl_bound,
    memory = MemoryState.compose — this is the no-knob design)
  - Certificate is the new Certificate hierarchy, not LogInterval
  - FrontierItem.dominates uses certificate.kl_bound() for comparison
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..candidates import Candidate, CertifiedPlanCandidate, ProofToken
from ..certificates import Certificate, ExactCertificate
from ..envelope import Envelope, SiteId
from ..memory import MemoryState

if TYPE_CHECKING:
    from ..model import GraphicalModel
    from ..kernels.base import KernelFamily


@dataclass
class PlanNode:
    site_id: SiteId
    candidate: Candidate
    children: list["PlanNode"]

    def flatten(self) -> dict[SiteId, Candidate]:
        result = {self.site_id: self.candidate}
        for child in self.children:
            result.update(child.flatten())
        return result


@dataclass
class FrontierItem:
    memory: MemoryState
    certificate: Certificate
    plan_node: PlanNode

    def dominates(self, other: "FrontierItem") -> bool:
        """
        self dominates other iff:
          self.memory <= other.memory  AND
          self.certificate.kl_bound() <= other.certificate.kl_bound()
          AND at least one is strict.
        """
        mem_le = self.memory.bytes <= other.memory.bytes
        kl_self = self.certificate.kl_bound()
        kl_other = other.certificate.kl_bound()
        cert_le = kl_self <= kl_other
        strict = (self.memory.bytes < other.memory.bytes) or (kl_self < kl_other)
        return mem_le and cert_le and strict


def pareto_prune(items: list[FrontierItem]) -> list[FrontierItem]:
    """
    Remove Pareto-dominated items. Returns non-dominated set sorted by
    memory ascending.

    An item is dominated if another has memory <= AND kl_bound <= with
    at least one strict.

    Inf-kl items are kept only if no finite-kl item exists at <= memory.
    """
    if not items:
        return []

    # Sort by (memory, kl_bound) so we can do a single-pass best-kl sweep
    sorted_items = sorted(
        items,
        key=lambda x: (x.memory.bytes, x.certificate.kl_bound()),
    )

    frontier: list[FrontierItem] = []
    best_kl = math.inf

    for item in sorted_items:
        kl = item.certificate.kl_bound()
        if kl < best_kl:
            frontier.append(item)
            best_kl = kl
        elif kl == math.inf and best_kl == math.inf and not frontier:
            frontier.append(item)

    return frontier


def pareto_prune_tie_retained(items: list[FrontierItem]) -> list[FrontierItem]:
    """
    Tie-retained Pareto pruning.

    Same domination rule as pareto_prune — A dominates B iff A.memory <= B.memory
    AND A.kl_bound <= B.kl_bound with at least one strict — but when multiple items
    have IDENTICAL (memory.bytes, kl_bound()), ALL are retained rather than one
    arbitrary representative.

    This enables downstream C1 evaluation to break Hilbert ties: if several plans
    have the same Hilbert certificate value, their C1 certificates may differ, and
    the C1-optimal plan is recoverable only if all tied plans are retained.

    Inf-kl items: kept only if no finite-kl item exists at <= memory.
    """
    if not items:
        return []

    sorted_items = sorted(
        items,
        key=lambda x: (x.memory.bytes, x.certificate.kl_bound()),
    )

    frontier: list[FrontierItem] = []
    best_kl = math.inf

    for item in sorted_items:
        kl = item.certificate.kl_bound()
        if kl < best_kl:
            frontier.append(item)
            best_kl = kl
        elif kl == best_kl and best_kl < math.inf:
            # Tie at the current best finite kl: retain it
            frontier.append(item)
        elif kl == math.inf and best_kl == math.inf and not frontier:
            frontier.append(item)

    return frontier


@dataclass
class SiteStats:
    """Per-site compiler diagnostics."""
    site_id: SiteId
    candidates_seen: int      # how many candidates this family generated
    frontier_size: int        # Pareto-frontier size after pruning


@dataclass
class CompiledPlan:
    envelope: Envelope
    selected: dict[SiteId, Candidate]
    certificate: Certificate        # Phase 1 execution certificate
    memory: MemoryState             # Phase 1 execution memory
    audit_log: list[str]
    site_stats: list[SiteStats] = field(default_factory=list)
    # Phase 2 fields — populated by CertificateSelector.select(); None until then.
    phase2_candidate: "CertifiedPlanCandidate | None" = field(default=None)


# Sentinel candidate used as a placeholder during the tree-knapsack convolution.
_SENTINEL_CERT = ExactCertificate()
_SENTINEL_MEM = MemoryState(0)


def _sentinel_candidate() -> Candidate:
    return Candidate(
        implementation=None,
        memory=_SENTINEL_MEM,
        certificate=_SENTINEL_CERT,
        audit=ProofToken("sentinel"),
    )


class Compiler:
    """
    Budget-optimal certified kernel allocation compiler.

    Runs a Pareto-frontier tree-knapsack DP over the envelope.
    Selects the plan with minimum certified KL bound that fits the memory budget.

    tie_retained_root: when True (default), the root Pareto frontier uses
    pareto_prune_tie_retained so that plans tied on (memory, Hilbert cert)
    are all retained for downstream C1 tie-breaking.  Intermediate DP nodes
    still use standard pareto_prune to prevent exponential blowup.
    """

    def __init__(
        self,
        kernel_families: list["KernelFamily"],
        tie_retained_root: bool = True,
    ) -> None:
        self.kernel_families = kernel_families
        self.tie_retained_root = tie_retained_root

    def compile(
        self,
        envelope: Envelope,
        model: "GraphicalModel",
        site_factors: dict[SiteId, list[dict]],
        memory_budget: MemoryState,
    ) -> CompiledPlan:
        """
        Run Pareto-frontier DP and return the best feasible plan.

        Raises ValueError if no sound plan fits the budget.
        """
        topo = envelope.topological_order()
        frontiers: dict[SiteId, list[FrontierItem]] = {}
        audit_log: list[str] = []
        site_stats: list[SiteStats] = []

        for sid in topo:
            site = envelope.site(sid)
            factors_here = site_factors.get(sid, [])

            # Pass the total plan budget as a conservative per-site cap.
            # Any site whose operator alone exceeds the plan budget can never
            # participate in a feasible plan, so skipping it here is sound.
            # This is NOT plan-level budget enforcement — the DP handles
            # composition; this filter only eliminates the obviously infeasible.
            candidates: list[Candidate] = []
            for family in self.kernel_families:
                for c in family.candidates(site, factors_here, model,
                                           memory_budget=memory_budget.bytes):
                    candidates.append(c)

            if not candidates:
                raise ValueError(
                    f"No candidates generated at site {sid} ('{site.label}'). "
                    "Register at least one KernelFamily that covers all sites."
                )

            child_frontiers = [frontiers[dep] for dep in site.dependencies]
            site_items = self._build_site_items(sid, candidates, child_frontiers)

            if not site_items:
                raise ValueError(f"No feasible plan items at site {sid}")

            pruned = pareto_prune(site_items)
            frontiers[sid] = pruned
            audit_log.append(
                f"site {sid} ('{site.label}'): "
                f"{len(candidates)} candidates, {len(pruned)} frontier items"
            )
            site_stats.append(SiteStats(
                site_id=sid,
                candidates_seen=len(candidates),
                frontier_size=len(pruned),
            ))

        # Apply tie-retained pruning at root level so downstream C1 can break ties.
        # Intermediate sites use standard pareto_prune to prevent DP blowup.
        root_items = frontiers[envelope.root]
        if self.tie_retained_root:
            root_frontier = pareto_prune_tie_retained(root_items)
            audit_log.append(
                f"root tie-retained frontier: {len(root_items)} -> {len(root_frontier)} items"
            )
        else:
            root_frontier = root_items

        feasible = [
            item for item in root_frontier
            if item.memory.bytes <= memory_budget.bytes
        ]

        if not feasible:
            min_mem = min(item.memory.bytes for item in root_frontier)
            raise ValueError(
                f"No plan fits memory budget {memory_budget.bytes} bytes. "
                f"Minimum required: {min_mem} bytes."
            )

        best = min(feasible, key=lambda x: (x.certificate.kl_bound(), x.memory.bytes))
        selected = best.plan_node.flatten()

        global_cert = self._compose_certificate(envelope, selected)

        return CompiledPlan(
            envelope=envelope,
            selected=selected,
            certificate=global_cert,
            memory=best.memory,
            audit_log=audit_log,
            site_stats=site_stats,
        )

    def full_frontier(
        self,
        envelope: Envelope,
        model: "GraphicalModel",
        site_factors: dict[SiteId, list[dict]],
        memory_budget: MemoryState = MemoryState(0),
    ) -> list[FrontierItem]:
        """Return the full Pareto frontier at the root (all memory/KL tradeoffs)."""
        topo = envelope.topological_order()
        frontiers: dict[SiteId, list[FrontierItem]] = {}

        for sid in topo:
            site = envelope.site(sid)
            factors_here = site_factors.get(sid, [])

            candidates: list[Candidate] = []
            for family in self.kernel_families:
                for c in family.candidates(site, factors_here, model,
                                           memory_budget=memory_budget.bytes):
                    candidates.append(c)

            if not candidates:
                raise ValueError(f"No candidates at site {sid}")

            child_frontiers = [frontiers[dep] for dep in site.dependencies]
            site_items = self._build_site_items(sid, candidates, child_frontiers)
            frontiers[sid] = pareto_prune(site_items)

        root_items = frontiers[envelope.root]
        if self.tie_retained_root:
            return pareto_prune_tie_retained(root_items)
        return root_items

    def _build_site_items(
        self,
        sid: SiteId,
        candidates: list[Candidate],
        child_frontiers: list[list[FrontierItem]],
        _prune_intermediate: bool = True,
    ) -> list[FrontierItem]:
        """
        Tree-knapsack DP: enumerate candidate × child-frontier combinations.

        Merges child frontiers sequentially with intermediate Pareto pruning
        (controlled by _prune_intermediate), then cross-products with each candidate.

        _prune_intermediate=False is used by cert_aware_full_frontier to enumerate
        all execution candidates without Hilbert-dominated items being dropped.
        Only safe for small models (≤3 candidates/site, ≤5 sites).
        """
        if not child_frontiers:
            return [
                FrontierItem(
                    memory=cand.memory,
                    certificate=cand.certificate,
                    plan_node=PlanNode(sid, cand, []),
                )
                for cand in candidates
            ]

        # Each merged entry: (accumulated_memory, accumulated_certificate, [child_PlanNodes])
        # Start with the identity element.
        merged: list[tuple[MemoryState, Certificate, list[PlanNode]]] = [
            (MemoryState(0), ExactCertificate(), [])
        ]

        for child_frontier in child_frontiers:
            new_merged: list[tuple[MemoryState, Certificate, list[PlanNode]]] = []
            for m_acc, c_acc, plans in merged:
                for child_item in child_frontier:
                    new_merged.append((
                        m_acc.compose(child_item.memory),
                        c_acc.compose(child_item.certificate),
                        plans + [child_item.plan_node],
                    ))
            if _prune_intermediate:
                # Prune intermediate merged list to keep it from exploding
                sentinel = _sentinel_candidate()
                proxy = [
                    FrontierItem(
                        memory=m,
                        certificate=c,
                        plan_node=PlanNode(-1, sentinel, ps),
                    )
                    for m, c, ps in new_merged
                ]
                pruned_proxy = pareto_prune(proxy)
                merged = [
                    (pi.memory, pi.certificate, pi.plan_node.children)
                    for pi in pruned_proxy
                ]
            else:
                merged = new_merged

        items: list[FrontierItem] = []
        for cand in candidates:
            for child_mem_sum, child_cert_sum, child_plans in merged:
                total_mem = cand.memory.compose(child_mem_sum)
                total_cert = cand.certificate.compose(child_cert_sum)
                items.append(FrontierItem(
                    memory=total_mem,
                    certificate=total_cert,
                    plan_node=PlanNode(sid, cand, child_plans),
                ))
        return items

    def _compose_certificate(
        self,
        envelope: Envelope,
        selected: dict[SiteId, Candidate],
    ) -> Certificate:
        """Bottom-up certificate composition over the selected plan."""
        topo = envelope.topological_order()
        cert_map: dict[SiteId, Certificate] = {}

        for sid in topo:
            site = envelope.site(sid)
            local_cert = selected[sid].certificate
            if not site.dependencies:
                cert_map[sid] = local_cert
            else:
                composed = local_cert
                for dep in site.dependencies:
                    composed = composed.compose(cert_map[dep])
                cert_map[sid] = composed

        return cert_map[envelope.root]
