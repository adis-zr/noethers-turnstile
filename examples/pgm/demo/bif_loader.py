"""
BIF loader for the demo — trimmed copy of ecds-pgm/experiments/bif_loader.py.

Kept: BIFData, parse_bif, budget_tiers, make_bif_instance, ModelInstance.
Dropped: compute_budgets_from_envelope, load_bif_instances, load_tier_instances,
         bif_graph_summary — all require imports from the experiments package tree.

ModelInstance is inlined here (source: ecds-pgm/experiments/instances.py).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from demo.inference.model import Factor, GraphicalModel, Query, Variable


# ---------------------------------------------------------------------------
# ModelInstance (inlined from ecds-pgm/experiments/instances.py)
# ---------------------------------------------------------------------------

@dataclass
class ModelInstance:
    instance_id: str
    model: GraphicalModel
    query: Query
    memory_budget: int
    interest_variable: int
    description: str = ""


# ---------------------------------------------------------------------------
# BIF parser
# ---------------------------------------------------------------------------

@dataclass
class BIFData:
    var_names: list[str]
    var_ids: dict[str, int]
    domains: dict[int, int]
    factors_raw: list[dict]
    query_var: int


def parse_bif(path: str | Path) -> BIFData:
    var_id: dict[str, int] = {}
    domains: dict[int, int] = {}
    var_names: list[str] = []

    def get_id(name: str) -> int:
        if name not in var_id:
            var_id[name] = len(var_id)
            var_names.append(name)
        return var_id[name]

    text = Path(path).read_text()

    for m in re.finditer(
        r'variable\s+(\w+)\s*\{[^}]*type\s+discrete\s*\[\s*(\d+)\s*\]', text
    ):
        vid = get_id(m.group(1))
        domains[vid] = int(m.group(2))

    factors_raw: list[dict] = []
    for m in re.finditer(r'probability\s*\(([^)]+)\)\s*\{([^}]+)\}', text, re.DOTALL):
        var_part = m.group(1)
        body = m.group(2)

        parts = [v.strip() for v in var_part.split("|")]
        child_name = parts[0].strip()
        parent_names = [v.strip() for v in parts[1].split(",")] if len(parts) > 1 else []

        child_id = get_id(child_name)
        parent_ids = [get_id(p) for p in parent_names]
        scope = parent_ids + [child_id]

        _FLOAT_RE = r'[-+]?\d+(?:\.\d+)?(?:[eE][+\-]?\d+)?'
        table_m = re.match(r'\s*table\b', body)
        if table_m:
            table = [float(x) for x in re.findall(_FLOAT_RE, body[table_m.end():])]
        else:
            table = []
            for row in body.splitlines():
                paren_close = row.rfind(')')
                if paren_close == -1:
                    continue
                table.extend(float(x) for x in re.findall(_FLOAT_RE, row[paren_close + 1:]))
        factors_raw.append({"scope": scope, "table": table})

    query_var = max(var_id.values())
    return BIFData(
        var_names=var_names,
        var_ids=var_id,
        domains=domains,
        factors_raw=factors_raw,
        query_var=query_var,
    )


# ---------------------------------------------------------------------------
# Budget estimation
# ---------------------------------------------------------------------------

def _exact_memory_estimate(domains: dict[int, int], factors_raw: list[dict]) -> int:
    total = 0
    for f in factors_raw:
        entries = 1
        for vid in f["scope"]:
            entries *= domains.get(vid, 2)
        total += entries * 8
    return total


def budget_tiers(
    domains: dict[int, int],
    factors_raw: list[dict],
    tight_factor: float = 0.05,
    medium_factor: float = 0.20,
    loose_factor: float = 0.60,
) -> tuple[int, int, int]:
    est = _exact_memory_estimate(domains, factors_raw)
    tight = max(512, int(est * tight_factor))
    medium = max(512, int(est * medium_factor))
    loose = max(512, int(est * loose_factor))
    return tight, medium, loose


# ---------------------------------------------------------------------------
# ModelInstance builder
# ---------------------------------------------------------------------------

def make_bif_instance(
    name: str,
    bif_data: BIFData,
    budget: int,
    budget_label: str = "medium",
    query_var: Optional[int] = None,
    interest_var: Optional[int] = None,
    clamp_zeros: bool = True,
    clamp_floor: float = 1e-6,
) -> ModelInstance:
    if query_var is None:
        query_var = bif_data.query_var
    if interest_var is None:
        interest_var = query_var

    domains = bif_data.domains
    variables = [Variable(id=vid, cardinality=domains[vid]) for vid in sorted(domains)]

    factors = []
    for f in bif_data.factors_raw:
        table = f["table"]
        if clamp_zeros:
            table = [max(clamp_floor, v) for v in table]
        factors.append(Factor(scope=tuple(f["scope"]), table=tuple(table)))

    model = GraphicalModel(variables=variables, factors=factors)
    query = Query(variables=(query_var,))

    return ModelInstance(
        instance_id=f"{name}_q{query_var}_{budget_label}",
        model=model,
        query=query,
        memory_budget=budget,
        interest_variable=interest_var,
        description=(
            f"BIF benchmark: {name}. "
            f"Query=X{query_var} ({bif_data.var_names[query_var]}), "
            f"budget={budget_label} ({budget} B), "
            f"vars={len(domains)}, factors={len(bif_data.factors_raw)}."
        ),
    )
