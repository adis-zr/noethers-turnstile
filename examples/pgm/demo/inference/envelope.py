"""
Variable-elimination envelope builder.

Constructs a computation DAG (Envelope) from a GraphicalModel and Query
using a min-fill elimination order. The compiler is agnostic to which
builder was used.

Adapted from archive/impl/envelope.py — main changes:
  - Accepts GraphicalModel + Query instead of raw dicts + domains
  - Removed RunLogger dependency
  - Envelope stores query_variables directly (no QuerySpec wrapper)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .model import GraphicalModel, Query

SiteId = int


@dataclass(frozen=True)
class Signature:
    variables: tuple[int, ...]
    cardinalities: tuple[int, ...]

    @property
    def num_entries(self) -> int:
        n = 1
        for c in self.cardinalities:
            n *= c
        return n

    @property
    def dense_bytes(self) -> int:
        return self.num_entries * 8


@dataclass
class Site:
    id: SiteId
    label: str
    input_signature: Signature
    output_signature: Signature
    eliminated_var: Optional[int]
    dependencies: list[SiteId]
    dep_output_scopes: dict[SiteId, tuple[int, ...]]


@dataclass
class Envelope:
    sites: list[Site]
    root: SiteId
    query_variables: tuple[int, ...]
    _site_index: dict[SiteId, Site] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._site_index = {s.id: s for s in self.sites}

    def site(self, sid: SiteId) -> Site:
        return self._site_index[sid]

    def topological_order(self) -> list[SiteId]:
        """Bottom-up topological order (leaves first, root last)."""
        visited: set[SiteId] = set()
        order: list[SiteId] = []

        def visit(sid: SiteId) -> None:
            if sid in visited:
                return
            visited.add(sid)
            for dep in self._site_index[sid].dependencies:
                visit(dep)
            order.append(sid)

        visit(self.root)
        return order


# ---------------------------------------------------------------------------
# Min-fill ordering
# ---------------------------------------------------------------------------

def _fill_count(var: int, adj: dict[int, set[int]], remaining: set[int]) -> int:
    nbrs = [u for u in adj[var] if u in remaining]
    count = 0
    for i, u in enumerate(nbrs):
        for v in nbrs[i + 1:]:
            if v not in adj[u]:
                count += 1
    return count


def _min_fill_order(
    variables: list[int],
    factors: list[dict],
    query_vars: set[int],
) -> list[int]:
    to_eliminate = [v for v in variables if v not in query_vars]

    adj: dict[int, set[int]] = {v: set() for v in variables}
    for f in factors:
        scope = f["scope"]
        for i, u in enumerate(scope):
            for v in scope[i + 1:]:
                adj[u].add(v)
                adj[v].add(u)

    remaining = set(to_eliminate)
    order: list[int] = []

    while remaining:
        best_var = min(remaining, key=lambda v: _fill_count(v, adj, remaining))
        order.append(best_var)
        nbrs = [u for u in adj[best_var] if u in remaining]
        for i, u in enumerate(nbrs):
            for w in nbrs[i + 1:]:
                adj[u].add(w)
                adj[w].add(u)
        remaining.remove(best_var)

    return order


# ---------------------------------------------------------------------------
# Envelope builder
# ---------------------------------------------------------------------------

def build_envelope(
    model: GraphicalModel,
    query: Query,
) -> tuple[Envelope, dict[SiteId, list[dict]]]:
    """
    Build a variable-elimination Envelope using min-fill ordering.

    Returns:
        envelope: the Site DAG
        site_factors: site_id -> list of model factor dicts at that site
    """
    factors = model.factors_as_dicts()
    domains = model.domains
    query_vars = list(query.variables)

    all_vars = list({v for f in factors for v in f["scope"]} | set(query_vars))
    elim_order = _min_fill_order(all_vars, factors, set(query_vars))

    sites: list[Site] = []
    site_factors: dict[SiteId, list[dict]] = {}
    next_id = 0

    available_messages: dict[SiteId, tuple[int, ...]] = {}
    unassigned = list(factors)

    for elim_var in elim_order:
        bucket_model_factors = [f for f in unassigned if elim_var in f["scope"]]
        unassigned = [f for f in unassigned if elim_var not in f["scope"]]

        dep_site_ids: list[SiteId] = []
        used_message_scopes: list[tuple[int, ...]] = []
        remaining_messages: dict[SiteId, tuple[int, ...]] = {}

        for msg_site_id, scope_key in available_messages.items():
            if elim_var in scope_key:
                dep_site_ids.append(msg_site_id)
                used_message_scopes.append(scope_key)
            else:
                remaining_messages[msg_site_id] = scope_key

        available_messages = remaining_messages

        combined_scope_set: set[int] = set()
        for f in bucket_model_factors:
            combined_scope_set.update(f["scope"])
        for scope_key in used_message_scopes:
            combined_scope_set.update(scope_key)

        combined_scope = sorted(combined_scope_set)
        combined_cards = tuple(domains.get(v, 2) for v in combined_scope)
        input_sig = Signature(tuple(combined_scope), combined_cards)

        out_scope = [v for v in combined_scope if v != elim_var]
        out_cards = tuple(domains.get(v, 2) for v in out_scope)
        output_sig = Signature(tuple(out_scope), out_cards)

        site_id = next_id
        next_id += 1

        dep_scopes = {
            dep_id: scope_key
            for dep_id, scope_key in zip(dep_site_ids, used_message_scopes)
        }

        site = Site(
            id=site_id,
            label=f"elim(x{elim_var})",
            input_signature=input_sig,
            output_signature=output_sig,
            eliminated_var=elim_var,
            dependencies=dep_site_ids,
            dep_output_scopes=dep_scopes,
        )
        sites.append(site)
        site_factors[site_id] = bucket_model_factors
        available_messages[site_id] = tuple(out_scope)

    # Root site: aggregates everything over query variables
    root_model_factors = list(unassigned)
    root_dep_ids = list(available_messages.keys())
    root_input_scopes = list(available_messages.values())

    query_scope = sorted(query_vars)
    query_cards = tuple(domains.get(v, 2) for v in query_scope)

    root_combined_set: set[int] = set()
    for f in root_model_factors:
        root_combined_set.update(f["scope"])
    for sc in root_input_scopes:
        root_combined_set.update(sc)

    root_combined = sorted(root_combined_set)
    root_combined_cards = tuple(domains.get(v, 2) for v in root_combined)

    root_id = next_id
    root_dep_scopes = {
        dep_id: scope_key
        for dep_id, scope_key in zip(root_dep_ids, root_input_scopes)
    }

    root_site = Site(
        id=root_id,
        label=f"root(query={query_vars})",
        input_signature=Signature(tuple(root_combined), root_combined_cards),
        output_signature=Signature(tuple(query_scope), query_cards),
        eliminated_var=None,
        dependencies=root_dep_ids,
        dep_output_scopes=root_dep_scopes,
    )
    sites.append(root_site)
    site_factors[root_id] = root_model_factors

    envelope = Envelope(
        sites=sites,
        root=root_id,
        query_variables=tuple(query_scope),
    )

    return envelope, site_factors
