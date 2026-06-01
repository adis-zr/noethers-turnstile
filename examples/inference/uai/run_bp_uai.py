"""Loopy belief propagation for UAI problem instances.

Adapts the Ising loopy BP implementation to the general UAI factor graph format:
  - Variables have arbitrary cardinalities (not just binary)
  - Factors are defined over arbitrary variable scopes (not just pairs)
  - Evidence is handled by pre-clamping observed variables

For non-binary variables, the message update generalises:
  log m_{u→v}(x_v) = log sum_{x_u} [ log_f(x_u, x_v) + sum_{w≠v} log m_{w→u}(x_u) ]

For high-arity factors (cliques of size > 2), we marginalise over all variables
in the factor scope except the target, summing the log-factor table over those axes.

Returns:
  marginals    : list of np.ndarray, one per variable, shape (card_i,)
  converged    : bool
  n_iter       : int
  max_delta    : float
  bethe_fe     : float  — Bethe free energy (proxy divergence when no ground truth)
"""
from __future__ import annotations

import numpy as np
from parse_uai import UAIGraph, apply_evidence


def _logsumexp(a: np.ndarray, axis: int) -> np.ndarray:
    mx = a.max(axis=axis, keepdims=True)
    return (mx + np.log(np.exp(a - mx).sum(axis=axis, keepdims=True))).squeeze(axis=axis)


def run_bp_uai(
    graph: UAIGraph,
    max_iter: int = 200,
    tol: float = 1e-6,
    damping: float = 0.5,
) -> dict:
    """Loopy sum-product BP on a general UAI factor graph.

    Implementation uses the factor graph formulation:
      - Variable nodes and factor nodes alternate
      - Messages: variable→factor and factor→variable
      - Belief at variable i = product of all incoming factor→variable messages

    Parameters
    ----------
    graph    : UAIGraph, evidence already applied via apply_evidence()
    max_iter : iteration limit
    tol      : convergence tolerance on max message change
    damping  : message damping in [0, 1)

    Returns
    -------
    dict with marginals, converged, n_iter, max_delta, bethe_fe
    """
    g = apply_evidence(graph)
    n_vars = g.n_vars
    cards = g.cardinalities

    # Only variables that appear in at least one factor after evidence
    active_vars: set[int] = set()
    for clique in g.cliques:
        active_vars.update(clique)

    # Variable→factor messages: msg_vf[f_idx][var] = log-message array of shape (card_var,)
    # Factor→variable messages: msg_fv[f_idx][var] = log-message array of shape (card_var,)
    msg_vf: list[dict[int, np.ndarray]] = []
    msg_fv: list[dict[int, np.ndarray]] = []
    for clique in g.cliques:
        msg_vf.append({v: np.zeros(cards[v]) for v in clique})
        msg_fv.append({v: np.zeros(cards[v]) for v in clique})

    converged = False
    n_iter = 0
    max_delta = float("inf")

    for iteration in range(max_iter):
        new_vf: list[dict[int, np.ndarray]] = []
        new_fv: list[dict[int, np.ndarray]] = []
        max_delta = 0.0

        # Step 1: variable→factor messages
        # log m_{v→f}(x_v) = sum_{f'≠f containing v} log m_{f'→v}(x_v)
        for f_idx, clique in enumerate(g.cliques):
            new_vf_f: dict[int, np.ndarray] = {}
            for v in clique:
                log_msg = np.zeros(cards[v])
                for f2_idx, clique2 in enumerate(g.cliques):
                    if f2_idx != f_idx and v in clique2:
                        log_msg += msg_fv[f2_idx][v]
                log_msg -= log_msg.max()
                new_vf_f[v] = log_msg
            new_vf.append(new_vf_f)

        # Step 2: factor→variable messages
        # log m_{f→v}(x_v) = log sum_{x_scope\v} [ log_f(x_scope) + sum_{u≠v in scope} log m_{u→f}(x_u) ]
        for f_idx, (clique, lf) in enumerate(zip(g.cliques, g.log_factors)):
            new_fv_f: dict[int, np.ndarray] = {}
            for v in clique:
                # Sum log m_{u→f}(x_u) into the factor table, then marginalise out all vars ≠ v
                log_combined = lf.copy()
                for u_pos, u in enumerate(clique):
                    if u != v:
                        # Broadcast msg along u's axis
                        shape = [1] * len(clique)
                        shape[u_pos] = cards[u]
                        log_combined = log_combined + new_vf[f_idx][u].reshape(shape)

                # Marginalise out all axes except v
                v_pos = clique.index(v)
                result = log_combined
                for ax in range(len(clique) - 1, -1, -1):
                    if ax != v_pos:
                        result = _logsumexp(result, axis=ax)
                        if ax < v_pos:
                            v_pos -= 1

                result = result.ravel()
                result -= result.max()

                # Damping
                damped = damping * msg_fv[f_idx][v] + (1 - damping) * result
                max_delta = max(max_delta, float(np.abs(damped - msg_fv[f_idx][v]).max()))
                new_fv_f[v] = damped

            new_fv.append(new_fv_f)

        msg_vf = new_vf
        msg_fv = new_fv
        n_iter = iteration + 1

        if max_delta < tol:
            converged = True
            break

    # Compute beliefs (marginals)
    marginals: list[np.ndarray] = []
    for v in range(n_vars):
        if v not in active_vars:
            # Observed or isolated variable — uniform placeholder
            log_b = np.zeros(cards[v])
        else:
            log_b = np.zeros(cards[v])
            for f_idx, clique in enumerate(g.cliques):
                if v in clique:
                    log_b += msg_fv[f_idx][v]
        log_b -= log_b.max()
        b = np.exp(log_b)
        marginals.append(b / b.sum())

    bethe_fe = _bethe_free_energy(g, marginals, msg_vf, msg_fv)

    return {
        "marginals": marginals,
        "converged": converged,
        "n_iter": n_iter,
        "max_delta": max_delta,
        "bethe_fe": bethe_fe,
    }


def _bethe_free_energy(
    g: UAIGraph,
    beliefs: list[np.ndarray],
    msg_vf: list[dict[int, np.ndarray]],
    msg_fv: list[dict[int, np.ndarray]],
) -> float:
    """Bethe free energy: F_Bethe = -log Z_Bethe.

    F_Bethe = sum_f E_f[log f] + sum_v (1 - deg_v) H(b_v)
    where deg_v = number of factors containing variable v.

    A large |F_Bethe| relative to the number of variables indicates BP is far
    from a good fixed point — used as proxy divergence on Tier 2 problems where
    no exact marginals are available.
    """
    # Factor degrees
    deg = [0] * g.n_vars
    for clique in g.cliques:
        for v in clique:
            deg[v] += 1

    # Factor energy term: sum_f sum_{x_scope} b_f(x_scope) * log_f(x_scope)
    # Approximate factor beliefs from variable beliefs (Bethe approximation)
    energy = 0.0
    for clique, lf in zip(g.cliques, g.log_factors):
        # Factor belief ≈ product of variable beliefs (Bethe)
        b_f = np.ones(lf.shape)
        for v_pos, v in enumerate(clique):
            shape = [1] * len(clique)
            shape[v_pos] = len(beliefs[v])
            b_f *= beliefs[v].reshape(shape)
        b_f = b_f / b_f.sum()
        mask = b_f > 1e-300
        energy += float((b_f[mask] * lf[mask]).sum())

    # Variable entropy term
    entropy = 0.0
    for v in range(g.n_vars):
        if deg[v] == 0:
            continue
        b = beliefs[v]
        mask = b > 1e-300
        h = -float((b[mask] * np.log(b[mask])).sum())
        entropy += (1 - deg[v]) * h

    return -(energy + entropy)


if __name__ == "__main__":
    import sys
    import os
    path = sys.argv[1] if len(sys.argv) > 1 else "data/PR/Grids_11.uai"
    sys.path.insert(0, os.path.dirname(__file__))
    g = __import__("parse_uai").parse_uai(path)
    r = run_bp_uai(g)
    print(f"{g.name}: converged={r['converged']} n_iter={r['n_iter']} "
          f"max_delta={r['max_delta']:.2e} bethe_fe={r['bethe_fe']:.2f}")
