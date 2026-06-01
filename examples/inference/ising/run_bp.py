"""Loopy belief propagation (sum-product) on Ising grids.

Implemented directly in numpy — NOT using pgmpy's junction-tree BP, which
is exact. This is the standard loopy sum-product algorithm:
  - Initialise all messages to uniform
  - Iterate: each node sends updated messages to each neighbour
  - Stop when max message change < tol or max_iter reached
"""
from __future__ import annotations

import numpy as np
from generate_ising import make_ising_grid, BETAS, SIZES


def run_loopy_bp(
    graph: dict,
    max_iter: int = 200,
    tol: float = 1e-6,
    damping: float = 0.5,
) -> dict:
    """Run loopy sum-product BP on a pairwise Ising graph.

    Parameters
    ----------
    graph    : dict from make_ising_grid
    max_iter : convergence iteration limit (spec: 200)
    tol      : message change tolerance for convergence check
    damping  : message damping coefficient ∈ [0, 1). 0 = no damping.

    Returns
    -------
    dict with keys:
        marginals       : np.ndarray shape (n_vars, 2)
        converged       : bool
        n_iter          : int — iterations actually run
        max_delta       : float — final max message delta
    """
    n_vars = graph["n_vars"]
    neighbors = graph["neighbors"]
    factors = graph["factors"]
    unary = graph.get("unary", [])

    # Build a factor lookup: (u, v) -> log_vals 2×2
    log_factor: dict[tuple, np.ndarray] = {}
    for f in factors:
        u, v = f["vars"]
        log_factor[(u, v)] = f["log_vals"]
        log_factor[(v, u)] = f["log_vals"].T

    # Unary log-potentials: node -> log_vals (2,)
    log_unary: dict[int, np.ndarray] = {}
    for f in unary:
        (i,) = f["vars"]
        log_unary[i] = f["log_vals"]

    # Messages: msg[u][v] = np.array([m(u→v, x_v=0), m(u→v, x_v=1)]) in log space
    msg: list[dict[int, np.ndarray]] = [
        {v: np.zeros(2) for v in neighbors[u]}
        for u in range(n_vars)
    ]

    converged = False
    n_iter = 0
    max_delta = float("inf")

    for iteration in range(max_iter):
        max_delta = 0.0
        new_msg: list[dict[int, np.ndarray]] = [
            {v: np.zeros(2) for v in neighbors[u]}
            for u in range(n_vars)
        ]

        for u in range(n_vars):
            for v in neighbors[u]:
                # log m_{u→v}(x_v) = log sum_{x_u} [ log_f(x_u, x_v) + sum_{w≠v} log m_{w→u}(x_u) ]
                # Shape: (2,) — one value per x_v state

                # Incoming messages to u from all neighbours except v,
                # plus unary potential at u
                log_incoming = log_unary.get(u, np.zeros(2)).copy()
                for w in neighbors[u]:
                    if w != v:
                        log_incoming += msg[w][u]

                # Pairwise log-factor: shape (2, 2) indexed [x_u, x_v]
                lf = log_factor[(u, v)]

                # log m = log sum_{x_u} exp( lf[x_u, x_v] + log_incoming[x_u] )
                # shape: (2,) over x_v
                log_m_new = np.zeros(2)
                for xv in range(2):
                    log_vals = lf[:, xv] + log_incoming  # shape (2,) over x_u
                    mx = log_vals.max()
                    log_m_new[xv] = mx + np.log(np.exp(log_vals - mx).sum())

                # Normalise in log space
                log_m_new -= log_m_new.max()

                # Damping
                log_m_damped = damping * msg[u][v] + (1 - damping) * log_m_new

                new_msg[u][v] = log_m_damped
                max_delta = max(max_delta, np.abs(log_m_damped - msg[u][v]).max())

        msg = new_msg
        n_iter = iteration + 1

        if max_delta < tol:
            converged = True
            break

    # Compute marginals from messages, including unary potentials
    marginals = np.zeros((n_vars, 2))
    for u in range(n_vars):
        log_belief = log_unary.get(u, np.zeros(2)).copy()
        for w in neighbors[u]:
            log_belief += msg[w][u]
        log_belief -= log_belief.max()
        belief = np.exp(log_belief)
        marginals[u] = belief / belief.sum()

    bethe_fe = _bethe_free_energy(marginals, msg, neighbors, log_factor, log_unary, n_vars)

    return {
        "marginals": marginals,
        "converged": converged,
        "n_iter": n_iter,
        "max_delta": max_delta,
        "bethe_fe": bethe_fe,
    }


def _bethe_free_energy(
    marginals: np.ndarray,
    msg: list[dict],
    neighbors: list[list],
    log_factor: dict,
    log_unary: dict,
    n_vars: int,
) -> float:
    """Bethe free energy for a pairwise Ising factor graph.

    F_Bethe = -U_Bethe - H_Bethe  where:
      U_Bethe  = sum_{(i,j)} sum_{xi,xj} b_ij(xi,xj) * log_f(xi,xj)
                 + sum_i sum_xi b_i(xi) * log_unary_i(xi)
      H_Bethe  = -sum_{(i,j)} sum_{xi,xj} b_ij * log b_ij
                 + sum_i (d_i - 1) * sum_xi b_i * log b_i

    Edges are counted once (i < j). Returns a scalar float.
    """
    edges_seen: set = set()
    U = 0.0
    H_pair = 0.0

    for u in range(n_vars):
        for v in neighbors[u]:
            if (min(u, v), max(u, v)) in edges_seen:
                continue
            edges_seen.add((min(u, v), max(u, v)))

            # Pairwise belief: b_uv(xu, xv) ∝ exp(log_f + log_msg_v→u + log_msg_u→v)
            lf = log_factor[(u, v)]  # shape (2, 2)
            b = np.zeros((2, 2))
            for xu in range(2):
                for xv in range(2):
                    b[xu, xv] = (lf[xu, xv]
                                 + msg[v][u][xu]
                                 + msg[u][v][xv])
            b -= b.max()
            b = np.exp(b)
            b /= b.sum()

            # Energy contribution
            with np.errstate(divide="ignore", invalid="ignore"):
                lf_clipped = np.where(b > 0, lf, 0.0)
            U += (b * lf_clipped).sum()

            # Pairwise entropy contribution (negative)
            with np.errstate(divide="ignore", invalid="ignore"):
                log_b = np.where(b > 0, np.log(np.maximum(b, 1e-300)), 0.0)
            H_pair -= (b * log_b).sum()

    # Unary contributions
    H_node = 0.0
    U_node = 0.0
    for i in range(n_vars):
        bi = marginals[i]
        di = len(neighbors[i])
        with np.errstate(divide="ignore", invalid="ignore"):
            log_bi = np.where(bi > 0, np.log(np.maximum(bi, 1e-300)), 0.0)
        H_node += (di - 1) * (-(bi * log_bi).sum())
        if i in log_unary:
            U_node += (bi * log_unary[i]).sum()

    return -(U + U_node + H_pair + H_node)


if __name__ == "__main__":
    for n in SIZES:
        for beta in BETAS:
            g = make_ising_grid(n, beta)
            r = run_loopy_bp(g)
            print(f"n={n} beta={beta:.2f}: converged={r['converged']} "
                  f"n_iter={r['n_iter']} max_delta={r['max_delta']:.2e} "
                  f"mean(p+)={r['marginals'][:,1].mean():.4f}")
