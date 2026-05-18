"""
ExactKernelFamily — exact dense-table sum-product at every site.

Certificate: ExactCertificate (zero KL).
Memory: combined product table size (conservative peak).

Adapted from archive/impl/kernels/exact.py — main changes:
  - Uses new Certificate/MemoryState types
  - KernelFamily signature takes GraphicalModel instead of domains dict
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from ..candidates import Candidate, ProofToken
from ..certificates import ExactCertificate
from ..memory import MemoryState
from .base import KernelFamily

if TYPE_CHECKING:
    from ..envelope import Site, SiteId
    from ..model import GraphicalModel


class ExactKernelFamily(KernelFamily):
    """Proposes one Candidate per site: exact dense sum-product elimination."""

    def candidates(
        self,
        site: "Site",
        model_factors: list[dict],
        model: "GraphicalModel",
        memory_budget: int = 0,
    ) -> list[Candidate]:
        domains = model.domains
        out_sig = site.output_signature

        elim_card = domains.get(site.eliminated_var, 1) if site.eliminated_var is not None else 1
        combined_peak = out_sig.num_entries * elim_card * 8

        # Skip if the budget is known and this candidate won't fit — avoid
        # materializing large gather-index arrays for infeasible exact sites.
        if memory_budget > 0 and combined_peak > memory_budget:
            return []

        memory = MemoryState(combined_peak)
        cert = ExactCertificate()
        audit = ProofToken("exact dense sum-product elimination")
        op = _build_exact_operator_lazy(site, model_factors, domains)

        return [Candidate(implementation=op, memory=memory, certificate=cert, audit=audit)]


# ---------------------------------------------------------------------------
# Index helpers
# ---------------------------------------------------------------------------

def _decode(idx: int, cards: tuple[int, ...]) -> tuple[int, ...]:
    assignment = []
    for c in reversed(cards):
        assignment.append(idx % c)
        idx //= c
    return tuple(reversed(assignment))


def _encode(assignment: tuple[int, ...], cards: tuple[int, ...]) -> int:
    idx = 0
    for a, c in zip(assignment, cards):
        idx = idx * c + a
    return idx


def _make_gather_index(
    combined_scope: list[int],
    combined_cards: tuple[int, ...],
    factor_scope: tuple[int, ...],
    factor_cards: tuple[int, ...],
) -> np.ndarray:
    combined_size = 1
    for c in combined_cards:
        combined_size *= c

    combined_strides = np.ones(len(combined_scope), dtype=np.int64)
    for i in range(len(combined_scope) - 2, -1, -1):
        combined_strides[i] = combined_strides[i + 1] * combined_cards[i + 1]

    factor_strides = np.ones(len(factor_scope), dtype=np.int64)
    for i in range(len(factor_scope) - 2, -1, -1):
        factor_strides[i] = factor_strides[i + 1] * factor_cards[i + 1]

    combined_pos = {v: i for i, v in enumerate(combined_scope)}

    all_indices = np.arange(combined_size, dtype=np.int64)
    gather = np.zeros(combined_size, dtype=np.int64)
    for fj, (fv, fs) in enumerate(zip(factor_scope, factor_strides)):
        pos = combined_pos[fv]
        digit = (all_indices // int(combined_strides[pos])) % combined_cards[pos]
        gather += digit * int(fs)

    return gather.astype(np.int32)


# ---------------------------------------------------------------------------
# Operator construction
# ---------------------------------------------------------------------------

def _build_exact_operator(
    site: "Site",
    model_factors: list[dict],
    domains: dict[int, int],
) -> object:
    eliminated_var = site.eliminated_var
    output_sig = site.output_signature
    dep_ids = site.dependencies
    captured_dep_scopes: dict[int, tuple[int, ...]] = dict(site.dep_output_scopes)

    seen: set[int] = set()
    combined_scope: list[int] = []
    for f in model_factors:
        for v in f["scope"]:
            if v not in seen:
                seen.add(v)
                combined_scope.append(v)
    for dep_id in dep_ids:
        dep_scope = captured_dep_scopes.get(dep_id, ())
        for v in dep_scope:
            if v not in seen:
                seen.add(v)
                combined_scope.append(v)

    combined_cards = tuple(domains[v] for v in combined_scope)
    combined_size = 1
    for c in combined_cards:
        combined_size *= c

    model_gathers: list[tuple[np.ndarray, np.ndarray]] = []
    for f in model_factors:
        scope = tuple(f["scope"])
        if not scope:
            continue
        factor_cards = tuple(domains[v] for v in scope)
        gather = _make_gather_index(combined_scope, combined_cards, scope, factor_cards)
        table_np = np.asarray(f["table"], dtype=np.float64)
        model_gathers.append((gather, table_np))

    dep_gather_indices: dict[int, np.ndarray] = {}
    for dep_id in dep_ids:
        dep_scope = captured_dep_scopes.get(dep_id, ())
        if not dep_scope:
            continue
        dep_cards = tuple(domains[v] for v in dep_scope)
        dep_gather_indices[dep_id] = _make_gather_index(
            combined_scope, combined_cards, dep_scope, dep_cards
        )

    if eliminated_var is not None and eliminated_var in combined_scope:
        elim_axis = combined_scope.index(eliminated_var)
        out_scope = [v for v in combined_scope if v != eliminated_var]
        out_cards = tuple(domains[v] for v in out_scope)
        combined_shape = tuple(combined_cards)

        canonical_vars = tuple(output_sig.variables)
        if tuple(out_scope) == canonical_vars:
            reindex = None
        else:
            canonical_cards = tuple(domains[v] for v in canonical_vars)
            reindex = _make_gather_index(
                list(canonical_vars), canonical_cards,
                tuple(out_scope), out_cards,
            )
    else:
        elim_axis = None
        out_scope = combined_scope
        combined_shape = tuple(combined_cards)
        canonical_vars = tuple(output_sig.variables)
        if tuple(out_scope) == canonical_vars:
            reindex = None
        else:
            canonical_cards = tuple(domains[v] for v in canonical_vars)
            reindex = _make_gather_index(
                list(canonical_vars), canonical_cards,
                tuple(out_scope), tuple(domains[v] for v in out_scope),
            )

    _mg = model_gathers
    _dgi = dep_gather_indices
    _dep_ids = list(dep_ids)
    _cs = combined_size
    _cshape = combined_shape
    _eaxis = elim_axis
    _reindex = reindex

    def operator(inputs: dict[int, list[float]]) -> list[float]:
        prod = np.ones(_cs, dtype=np.float64)

        for gather, table_np in _mg:
            prod *= table_np[gather]

        for dep_id in _dep_ids:
            dep_table = inputs.get(dep_id)
            if dep_table is None:
                continue
            gi = _dgi.get(dep_id)
            if gi is None:
                continue
            prod *= np.asarray(dep_table, dtype=np.float64)[gi]

        if _eaxis is not None:
            result = prod.reshape(_cshape).sum(axis=_eaxis).ravel()
        else:
            result = prod

        if _reindex is not None:
            result = result[_reindex]

        return result.tolist()

    return operator


def _build_exact_operator_lazy(
    site: "Site",
    model_factors: list[dict],
    domains: dict[int, int],
) -> object:
    """
    Lazy variant of _build_exact_operator.

    Captures only lightweight metadata at construction time — no numpy
    allocations.  Gather indices are computed on the first call and cached
    inside the closure, so unselected candidates pay no allocation cost.

    Immutability contract: model_factors and their table lists must not be
    mutated after this call.  The lazy closure holds references to the original
    table lists (not copies); mutation between construction and first invocation
    would produce silently incorrect results.  This matches the eager path's
    assumption — _build_exact_operator also holds np.asarray views of the same
    tables — so any caller that is safe for the eager variant is safe here too.
    """
    # Hold references to the original factor dicts.  Scopes are tupled for
    # immutability; tables are referenced in-place (see contract above).
    factor_descriptors = [
        {"scope": tuple(f["scope"]), "table": f["table"]}
        for f in model_factors
        if f.get("scope")
    ]

    _cache: list = []  # mutable cell: populated on first call

    def operator(inputs: dict[int, list[float]]) -> list[float]:
        if not _cache:
            # First call: build and cache the eager operator.
            # All numpy allocations happen here, not at candidate() time.
            _cache.append(_build_exact_operator(site, factor_descriptors, domains))
        return _cache[0](inputs)

    return operator


# ---------------------------------------------------------------------------
# Shared utility for mini-bucket audit
# ---------------------------------------------------------------------------

def _compute_exact_message(
    factors: list[dict],
    elim_var: int,
    elim_card: int,
    out_vars: list[int],
    domains: dict[int, int],
) -> list[float]:
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
        if not scope or not f["table"]:
            continue
        factor_cards = tuple(domains.get(v, 2) for v in scope)
        gather = _make_gather_index(combined_scope, combined_cards, scope, factor_cards)
        prod *= np.asarray(f["table"], dtype=np.float64)[gather]

    if elim_var not in combined_scope:
        return prod.tolist()

    combined_shape = tuple(combined_cards)
    elim_axis = combined_scope.index(elim_var)
    out_scope = [v for v in combined_scope if v != elim_var]
    out_cards = tuple(domains.get(v, 2) for v in out_scope)

    result = prod.reshape(combined_shape).sum(axis=elim_axis).ravel()

    if out_scope != out_vars:
        reindex = _make_gather_index(
            out_vars, tuple(domains.get(v, 2) for v in out_vars),
            tuple(out_scope), out_cards,
        )
        result = result[reindex]

    return result.tolist()
