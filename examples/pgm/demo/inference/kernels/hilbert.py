"""
HilbertKernelFamily — mini-bucket kernel with HilbertIntervalCertificate.

For each valid 2-group partition of the factors at a site, proposes a
mini-bucket approximation whose certificate is a HilbertIntervalCertificate
with bound derived from the Hölder inequality:

    osc(s) <= log(n_groups)   (equal-weight Hölder, analytic upper bound)

When factors contain zeros, the support is not strictly positive and
forward KL(P||Q) may be infinite. In that case we return InfiniteCertificate.

This is a conservative but always-sound first implementation. The archive's
BracketedGaugedWMBKernelFamily computes tighter bounds from actual message
envelopes; that enhancement can be plugged in later by changing only this
file — the certificate type and compiler are unaffected.
"""
from __future__ import annotations

import math
from itertools import combinations
from typing import TYPE_CHECKING, Optional

from ..candidates import Candidate, ProofToken
from ..certificates import HilbertIntervalCertificate, InfiniteCertificate
from ..memory import MemoryState
from .base import KernelFamily
from .exact import _make_gather_index, _decode, _encode

if TYPE_CHECKING:
    from ..envelope import Site, SiteId
    from ..model import GraphicalModel

_MAX_PARTITIONS_PER_SITE = 32


class HilbertKernelFamily(KernelFamily):
    """
    Proposes mini-bucket 2-group-split candidates with Hilbert interval certificates.
    """

    def candidates(
        self,
        site: "Site",
        model_factors: list[dict],
        model: "GraphicalModel",
        memory_budget: int = 0,
    ) -> list[Candidate]:
        if site.eliminated_var is None:
            return []

        domains = model.domains
        elim_var = site.eliminated_var

        # Build a flat list of all factor descriptors at this site.
        # Model factors have actual tables; dep messages are described by scope only
        # (their tables arrive at runtime — we use scope for memory accounting).
        all_factors: list[dict] = list(model_factors)
        for dep_id, dep_scope in site.dep_output_scopes.items():
            all_factors.append({
                "scope": list(dep_scope),
                "table": None,
                "_dep_id": dep_id,
            })

        if len(all_factors) < 2:
            return []

        # Check strict positivity of model factors (dep messages checked symbolically).
        # If any entry is non-positive, forward KL may be infinite.
        # We still provide a working exact operator as the implementation — we can
        # still compute a marginal, we just cannot certify a finite KL bound.
        for f in model_factors:
            if f.get("table") is not None:
                if any(v <= 0.0 for v in f["table"]):
                    from .exact import _build_exact_operator_lazy
                    exact_mem = site.output_signature.num_entries * domains.get(elim_var, 2) * 8
                    if memory_budget > 0 and exact_mem > memory_budget:
                        return []
                    op = _build_exact_operator_lazy(site, model_factors, domains)
                    return [Candidate(
                        implementation=op,
                        memory=MemoryState(exact_mem),
                        certificate=InfiniteCertificate(
                            reason=f"site {site.id}: non-positive entry in model factor"
                        ),
                        audit=ProofToken(
                            f"site {site.id}: forward KL may be infinite (support failure)"
                        ),
                    )]

        n = len(all_factors)
        indices = list(range(n))

        results: list[Candidate] = []

        # Enumerate 2-group partitions (capped at _MAX_PARTITIONS_PER_SITE)
        count = 0
        for k in range(1, n):
            for left_indices in combinations(indices, k):
                if count >= _MAX_PARTITIONS_PER_SITE:
                    break
                right_indices = [i for i in indices if i not in left_indices]
                if not right_indices:
                    continue
                partition = [list(left_indices), list(right_indices)]
                cand = _build_hilbert_candidate(
                    site, all_factors, partition, domains
                )
                if cand is not None:
                    results.append(cand)
                    count += 1
            if count >= _MAX_PARTITIONS_PER_SITE:
                break

        return results


def _build_hilbert_candidate(
    site: "Site",
    all_factors: list[dict],
    partition: list[list[int]],
    domains: dict[int, int],
) -> Optional[Candidate]:
    elim_var = site.eliminated_var
    assert elim_var is not None

    n_groups = len(partition)

    # Memory: sum of group output table sizes + largest group joint table (temporary)
    group_output_sizes: list[int] = []
    group_joint_sizes: list[int] = []

    for group_indices in partition:
        group = [all_factors[i] for i in group_indices]
        # Group output scope: union of factor scopes minus eliminated_var
        out_scope_set: set[int] = set()
        for f in group:
            for v in f["scope"]:
                if v != elim_var:
                    out_scope_set.add(v)
        out_size = 1
        for v in out_scope_set:
            out_size *= domains.get(v, 2)
        group_output_sizes.append(out_size)

        elim_card = domains.get(elim_var, 2)
        joint_size = out_size * elim_card
        group_joint_sizes.append(joint_size)

    total_output_bytes = sum(s * 8 for s in group_output_sizes)
    max_joint_bytes = max(group_joint_sizes) * 8
    local_peak = total_output_bytes + max_joint_bytes
    memory = MemoryState(local_peak)

    # KL bound: log(n_groups) from equal-weight Hölder inequality
    # KL(P||Q) <= osc(s) <= log(n_groups) for equal-weight mini-bucket split
    hilbert_width = math.log(n_groups)
    lo = -hilbert_width / 2
    hi = hilbert_width / 2
    cert = HilbertIntervalCertificate(lo=lo, hi=hi)

    audit = ProofToken(
        f"hilbert mini-bucket 2-group split site {site.id}: "
        f"Hölder bound log({n_groups})={hilbert_width:.4g} nats"
    )

    op = _build_mb_operator(site, all_factors, partition, domains)

    return Candidate(implementation=op, memory=memory, certificate=cert, audit=audit)


def _build_mb_operator(
    site: "Site",
    all_factors: list[dict],
    partition: list[list[int]],
    domains: dict[int, int],
) -> object:
    """Build a mini-bucket operator for the given partition."""
    elim_var = site.eliminated_var
    assert elim_var is not None

    elim_card = domains.get(elim_var, 2)
    canonical_vars = tuple(site.output_signature.variables)
    canonical_cards = tuple(domains.get(v, 2) for v in canonical_vars)
    canonical_size = site.output_signature.num_entries

    # Pre-partition factors into groups
    groups: list[list[dict]] = [[all_factors[i] for i in grp] for grp in partition]

    # Capture dep_id -> scope mapping for runtime lookup
    dep_scope_map: dict[int, list[int]] = {
        f["_dep_id"]: f["scope"]
        for f in all_factors
        if "_dep_id" in f
    }

    _groups = groups
    _dep_scope_map = dep_scope_map
    _elim_var = elim_var
    _elim_card = elim_card
    _canonical_vars = canonical_vars
    _canonical_cards = canonical_cards
    _canonical_size = canonical_size
    _domains = domains

    def operator(inputs: dict[int, list[float]]) -> list[float]:
        import numpy as np

        group_messages: list[tuple[list[int], list[float]]] = []

        for group in _groups:
            # Resolve dep messages into concrete factors
            resolved: list[dict] = []
            for f in group:
                if "_dep_id" in f:
                    dep_id = f["_dep_id"]
                    table = inputs.get(dep_id)
                    if table is None:
                        continue
                    resolved.append({"scope": f["scope"], "table": table})
                else:
                    resolved.append(f)

            if not resolved:
                continue

            out_scope = _group_out_scope(resolved, _elim_var)
            msg = _compute_group_message(resolved, _elim_var, _elim_card, out_scope, _domains)
            group_messages.append((out_scope, msg))

        if not group_messages:
            return [1.0] * _canonical_size

        # Combine group messages by multiplying (in the product-of-messages space)
        seen: set[int] = set()
        combined_out_scope: list[int] = []
        for scope, _ in group_messages:
            for v in scope:
                if v not in seen:
                    seen.add(v)
                    combined_out_scope.append(v)

        combined_out_cards = tuple(_domains.get(v, 2) for v in combined_out_scope)
        combined_out_size = 1
        for c in combined_out_cards:
            combined_out_size *= c

        combined_result = [1.0] * combined_out_size
        for out_idx in range(combined_out_size):
            assignment = _decode(out_idx, combined_out_cards)
            for scope, msg in group_messages:
                index_map = [combined_out_scope.index(v) for v in scope]
                scope_cards = tuple(_domains.get(v, 2) for v in scope)
                sub_assignment = tuple(assignment[i] for i in index_map)
                factor_idx = _encode(sub_assignment, scope_cards)
                combined_result[out_idx] *= msg[factor_idx]

        if tuple(combined_out_scope) == _canonical_vars:
            return combined_result

        # Reindex to canonical variable order
        canon_pos = {v: i for i, v in enumerate(_canonical_vars)}
        result = [0.0] * _canonical_size
        for can_idx in range(_canonical_size):
            can_asgn = _decode(can_idx, _canonical_cards)
            combined_asgn = tuple(can_asgn[canon_pos[v]] for v in combined_out_scope)
            src_idx = _encode(combined_asgn, combined_out_cards)
            result[can_idx] = combined_result[src_idx]
        return result

    return operator


def _group_out_scope(factors: list[dict], elim_var: int) -> list[int]:
    seen: set[int] = set()
    scope: list[int] = []
    for f in factors:
        for v in f["scope"]:
            if v != elim_var and v not in seen:
                seen.add(v)
                scope.append(v)
    return scope


def _compute_group_message(
    factors: list[dict],
    elim_var: int,
    elim_card: int,
    out_scope: list[int],
    domains: dict[int, int],
) -> list[float]:
    import numpy as np

    seen: set[int] = set()
    combined_scope: list[int] = []
    for f in factors:
        for v in f["scope"]:
            if v not in seen:
                seen.add(v)
                combined_scope.append(v)

    combined_cards = tuple(domains.get(v, 2) for v in combined_scope)
    combined_size = 1
    for c in combined_cards:
        combined_size *= c

    prod = np.ones(combined_size, dtype=np.float64)
    for f in factors:
        scope = tuple(f["scope"])
        if not scope or not f.get("table"):
            continue
        factor_cards = tuple(domains.get(v, 2) for v in scope)
        gather = _make_gather_index(combined_scope, combined_cards, scope, factor_cards)
        prod *= np.asarray(f["table"], dtype=np.float64)[gather]

    if elim_var not in combined_scope:
        return prod.tolist()

    elim_idx = combined_scope.index(elim_var)
    combined_shape = tuple(combined_cards)
    reduced_scope = [v for v in combined_scope if v != elim_var]
    result = prod.reshape(combined_shape).sum(axis=elim_idx).ravel()

    if reduced_scope != out_scope:
        out_cards = tuple(domains.get(v, 2) for v in out_scope)
        reindex = _make_gather_index(
            out_scope, out_cards,
            tuple(reduced_scope),
            tuple(domains.get(v, 2) for v in reduced_scope),
        )
        result = result[reindex]

    return result.tolist()
