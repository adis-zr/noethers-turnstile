"""UAI file format parser.

UAI format spec:
  Line 1: type (MARKOV | BAYES)
  Line 2: number of variables N
  Line 3: cardinalities c_0 c_1 ... c_{N-1}
  Line 4: number of cliques/factors M
  Lines 5..5+M-1: clique scope — first token is clique size, rest are variable indices
  Then: M factor tables, each preceded by a blank line and a line with the number
        of entries, followed by the factor values in order (row-major over scope).

Evidence file (.evid):
  Line 1: number of observed variables E
  Line 2: var_0 val_0 var_1 val_1 ... var_{E-1} val_{E-1}
  (E=0 means no evidence, file may be empty or contain just "0")
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np


@dataclass
class UAIGraph:
    name: str
    n_vars: int
    cardinalities: list[int]          # shape (n_vars,)
    cliques: list[list[int]]          # list of variable-index lists
    log_factors: list[np.ndarray]     # log of factor tables, one per clique
    evidence: dict[int, int]          # var_idx -> observed_value
    n_factors: int = 0

    def __post_init__(self):
        self.n_factors = len(self.cliques)


def parse_uai(path: str, evid_path: str | None = None) -> UAIGraph:
    """Parse a .uai file and optional .evid file into a UAIGraph."""
    name = os.path.basename(path).replace(".uai", "")

    with open(path) as f:
        raw = f.read().split()

    pos = 0

    def next_token() -> str:
        nonlocal pos
        tok = raw[pos]
        pos += 1
        return tok

    def next_int() -> int:
        return int(next_token())

    def next_float() -> float:
        return float(next_token())

    graph_type = next_token()  # MARKOV or BAYES
    n_vars = next_int()
    cardinalities = [next_int() for _ in range(n_vars)]
    n_cliques = next_int()

    cliques: list[list[int]] = []
    for _ in range(n_cliques):
        size = next_int()
        scope = [next_int() for _ in range(size)]
        cliques.append(scope)

    log_factors: list[np.ndarray] = []
    for clique in cliques:
        n_entries = next_int()
        values = np.array([next_float() for _ in range(n_entries)], dtype=np.float64)
        # UAI files store raw (non-log) factor values; convert to log, clamping zeros
        values = np.clip(values, 1e-300, None)
        shape = tuple(cardinalities[v] for v in clique)
        log_factors.append(np.log(values).reshape(shape))

    # Parse evidence
    evidence: dict[int, int] = {}
    evid_path = evid_path or (path + ".evid")
    if os.path.exists(evid_path):
        with open(evid_path) as f:
            evid_tokens = f.read().split()
        if evid_tokens:
            n_obs = int(evid_tokens[0])
            for i in range(n_obs):
                var = int(evid_tokens[1 + 2 * i])
                val = int(evid_tokens[2 + 2 * i])
                evidence[var] = val

    return UAIGraph(
        name=name,
        n_vars=n_vars,
        cardinalities=cardinalities,
        cliques=cliques,
        log_factors=log_factors,
        evidence=evidence,
    )


def apply_evidence(graph: UAIGraph) -> UAIGraph:
    """Return a new UAIGraph with evidence variables clamped.

    Replaces each factor containing an observed variable with a reduced factor
    (fixing the observed variable's state), then removes singleton evidence
    variables from unary factors.
    """
    if not graph.evidence:
        return graph

    new_cliques = []
    new_log_factors = []

    for clique, lf in zip(graph.cliques, graph.log_factors):
        # Slice out observed variables
        reduced_scope = list(clique)
        reduced_lf = lf.copy()

        for obs_var, obs_val in graph.evidence.items():
            if obs_var in reduced_scope:
                ax = reduced_scope.index(obs_var)
                idx = [slice(None)] * reduced_lf.ndim
                idx[ax] = obs_val
                reduced_lf = reduced_lf[tuple(idx)]
                reduced_scope = [v for v in reduced_scope if v != obs_var]

        if len(reduced_scope) == 0:
            # Scalar factor — incorporate into partition function, skip
            continue

        new_cliques.append(reduced_scope)
        new_log_factors.append(reduced_lf)

    return UAIGraph(
        name=graph.name,
        n_vars=graph.n_vars,
        cardinalities=graph.cardinalities,
        cliques=new_cliques,
        log_factors=new_log_factors,
        evidence=graph.evidence,
    )


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "data/PR/Grids_11.uai"
    g = parse_uai(path)
    print(f"name={g.name} n_vars={g.n_vars} n_factors={g.n_factors} "
          f"evidence={len(g.evidence)} max_card={max(g.cardinalities)}")
