"""Convert a pgmpy BayesianNetwork to a UAIGraph for use with run_bp_uai.

A Bayesian network's CPTs are already factors: P(child | parents).
We represent each CPT as a log-factor over (parents..., child) in the
same variable order pgmpy uses. The result is a UAIGraph that run_bp_uai
can consume directly.

Note: loopy BP on the moral graph of a BN is equivalent to running
sum-product on the original factor graph (without triangulation).
Murphy, Weiss, Jordan (1999) run exactly this on ALARM and MUNIN.
"""
from __future__ import annotations

import warnings
import numpy as np

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from pgmpy.readwrite import BIFReader
    from pgmpy.models import DiscreteBayesianNetwork
    from pgmpy.inference import VariableElimination

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "uai"))
from parse_uai import UAIGraph


def load_bif(path: str) -> DiscreteBayesianNetwork:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        reader = BIFReader(path)
        return reader.get_model()


def bn_to_uai_graph(model: DiscreteBayesianNetwork, name: str = "") -> UAIGraph:
    """Convert a pgmpy BayesianNetwork to a UAIGraph.

    Variable indices follow the order of model.nodes().
    Each CPD becomes a log-factor whose scope is (parents..., child).
    """
    nodes = list(model.nodes())
    var_to_idx = {v: i for i, v in enumerate(nodes)}
    cardinalities = [model.get_cardinality(v) for v in nodes]

    cliques: list[list[int]] = []
    log_factors: list[np.ndarray] = []

    for cpd in model.cpds:
        child = cpd.variable
        parents = cpd.variables[1:]  # pgmpy: variables[0] is child, rest are parents

        scope_names = list(parents) + [child]
        scope_idx = [var_to_idx[v] for v in scope_names]

        # cpd.values shape: (card_child, card_parent1, card_parent2, ...)
        # We want shape: (card_parent1, ..., card_child) — parents first
        values = cpd.values  # (child, p1, p2, ...)
        if len(parents) > 0:
            # Move child axis to last position
            values = np.moveaxis(values, 0, -1)
        else:
            values = values.reshape(cardinalities[var_to_idx[child]])

        values = np.clip(values, 1e-300, None)
        log_table = np.log(values)

        cliques.append(scope_idx)
        log_factors.append(log_table)

    return UAIGraph(
        name=name or model.name or "unknown",
        n_vars=len(nodes),
        cardinalities=cardinalities,
        cliques=cliques,
        log_factors=log_factors,
        evidence={},
    )


def exact_marginals_bn(model: DiscreteBayesianNetwork) -> dict[str, np.ndarray]:
    """Return exact marginals {var_name: np.ndarray} via pgmpy VariableElimination."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ve = VariableElimination(model)
        return {
            node: ve.query([node], show_progress=False).values
            for node in model.nodes()
        }


def marginals_as_array(
    marginals_dict: dict[str, np.ndarray],
    nodes: list[str],
    cardinalities: list[int],
) -> list[np.ndarray]:
    """Convert {var: array} dict to list indexed by node order, padded to max card."""
    return [marginals_dict[v] for v in nodes]


def tv_distance_bn(
    approx: list[np.ndarray],
    exact: list[np.ndarray],
) -> float:
    """Mean TV distance over all variables.

    TV(q_i, p*_i) = 0.5 * sum_s |q_i(s) - p*_i(s)|, averaged over variables.
    Variables with different cardinalities are handled naturally since each
    marginal is its own array.
    """
    tvs = [0.5 * float(np.abs(a - e).sum()) for a, e in zip(approx, exact)]
    return float(np.mean(tvs))
