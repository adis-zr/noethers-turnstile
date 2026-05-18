"""Minimal standalone BIF file parser.

Parses Bayesian Interchange Format (.bif) files from the bnlearn repository
into plain Python dicts usable as PGM bridge inputs.  No dependency on
certified_inference or any ecds-* package.

Public API
----------
parse_bif(path)              -> BIFGraph
bif_to_pgm_dicts(g)          -> (graph_dict, query_dict, evidence_dict)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BIFGraph:
    """Parsed BIF network, using variable names (not integer IDs)."""
    var_names: list[str]          # variables in definition order
    domains: dict[str, int]       # name -> cardinality
    factors: list[dict]           # [{"scope": [str,...], "table": [float,...]}]
    query_var: str                # last variable defined (bnlearn convention)


def parse_bif(path: str | Path) -> BIFGraph:
    """Parse a BIF file into a BIFGraph."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")

    var_names: list[str] = []
    domains: dict[str, int] = {}
    factors: list[dict] = []

    # Variables: "variable <name> { type discrete [ <k> ] { ... }; }"
    for m in re.finditer(
        r'variable\s+(\w+)\s*\{[^}]*type\s+discrete\s*\[\s*(\d+)\s*\]', text
    ):
        name, card = m.group(1), int(m.group(2))
        if name not in domains:
            var_names.append(name)
        domains[name] = card

    # Factors: "probability ( <child> [ | <parent1>, <parent2>, ... ] ) { ... }"
    for m in re.finditer(
        r'probability\s*\(\s*(\w+)\s*(?:\|\s*([^)]+?))?\s*\)\s*\{([^}]*)\}',
        text,
        re.DOTALL,
    ):
        child = m.group(1)
        parents_str = (m.group(2) or "").strip()
        table_str = m.group(3)

        parents: list[str] = (
            [p.strip() for p in parents_str.split(",") if p.strip()]
            if parents_str else []
        )
        scope = parents + [child]

        # Extract all floats from the table block
        floats = [float(x) for x in re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', table_str)]
        factors.append({"scope": scope, "table": floats})

    query_var = var_names[-1] if var_names else ""
    return BIFGraph(var_names=var_names, domains=domains, factors=factors, query_var=query_var)


def bif_to_pgm_dicts(g: BIFGraph) -> tuple[dict, dict, dict]:
    """Convert a BIFGraph into (graph_dict, query_dict, evidence_dict).

    The returned dicts are suitable as inputs to compile_pgm() in bridge.py.
    graph_dict follows the PGM adapter schema: {"variables": {...}, "factors": [...]}.
    query_dict: {"target": <query_var>, "type": "marginal"}.
    evidence_dict: {} (empty — callers can add observations as needed).
    """
    variables = {name: list(range(card)) for name, card in g.domains.items()}
    graph_dict: dict = {
        "variables": variables,
        "factors": g.factors,
    }
    query_dict: dict = {"target": g.query_var, "type": "marginal"}
    evidence_dict: dict = {}
    return graph_dict, query_dict, evidence_dict
