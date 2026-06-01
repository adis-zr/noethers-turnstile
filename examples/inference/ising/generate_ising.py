"""Build Ising grid factor graphs at each beta.

Returns a plain dict representation usable by both the exact and loopy BP runners.
No external dependencies beyond numpy.
"""
from __future__ import annotations

import numpy as np


def make_ising_grid(n: int, beta: float) -> dict:
    """Return a factor-graph dict for an n×n periodic Ising model.

    Nodes are labelled (i, j) as integers row-major: i*n + j.
    Factors are pairwise: each neighbouring pair shares a 2×2 factor
    exp(beta * s_u * s_v) where s ∈ {-1, +1} (stored with state 0 = -1, 1 = +1).

    Returns
    -------
    dict with keys:
        n_vars    : int — total number of binary variables
        n         : int — grid side length
        beta      : float
        neighbors : list[list[int]] — adjacency list (4-connected, no periodic wrap)
        factors   : list[dict] with keys 'vars' (pair) and 'log_vals' (2×2 ndarray)
    """
    n_vars = n * n
    neighbors: list[list[int]] = [[] for _ in range(n_vars)]
    factors = []

    def idx(i: int, j: int) -> int:
        return i * n + j

    # Horizontal and vertical edges (no periodic wrap — open boundary)
    edges = set()
    for i in range(n):
        for j in range(n):
            u = idx(i, j)
            for di, dj in [(0, 1), (1, 0)]:
                ni, nj = i + di, j + dj
                if 0 <= ni < n and 0 <= nj < n:
                    v = idx(ni, nj)
                    if (u, v) not in edges:
                        edges.add((u, v))
                        neighbors[u].append(v)
                        neighbors[v].append(u)
                        # log factor: log exp(beta * s_u * s_v)
                        # state 0 = spin -1, state 1 = spin +1
                        # s(state) = 2*state - 1
                        log_vals = np.array([
                            [beta * 1,  beta * (-1)],   # (-1,-1), (-1,+1)
                            [beta * (-1), beta * 1],    # (+1,-1), (+1,+1)
                        ])
                        factors.append({"vars": (u, v), "log_vals": log_vals})

    return {
        "n_vars": n_vars,
        "n": n,
        "beta": beta,
        "neighbors": neighbors,
        "factors": factors,
    }


BETAS = [0.10, 0.20, 0.30, 0.40, 0.44, 0.50, 0.60, 0.80, 1.00, 1.50]
SIZES = [4, 6]

# Small random external field to break the +/- symmetry so single-site
# marginals are non-trivial. The field magnitude is small enough that it
# doesn't dominate, but large enough to expose BP error near beta_c.
# Murphy, Weiss, Jordan (1999) use a similar random field setup.
FIELD_H = 0.1
FIELD_SEED = 42


def make_ising_grid_with_field(n: int, beta: float, h: float = FIELD_H, seed: int = FIELD_SEED) -> dict:
    """Ising grid with random ±h external field on each site.

    The random field breaks the global spin-flip symmetry so that single-site
    marginals are non-trivial (not identically 0.5). This is necessary to
    observe approximation error in per-site marginals — in zero field all
    approximate algorithms trivially return 0.5 for each site.

    Adds key 'unary' to the graph dict: list of dicts with keys
        'vars'     : (i,) — single-element tuple
        'log_vals' : np.ndarray shape (2,) — [log_factor(x=0), log_factor(x=1)]
    """
    g = make_ising_grid(n, beta)
    rng = np.random.default_rng(seed)
    fields = rng.choice([-h, h], size=g["n_vars"]).astype(float)
    # log_factor for site i: state 0 = spin -1, log_val = -h_i; state 1 = spin +1, log_val = +h_i
    unary = [
        {"vars": (i,), "log_vals": np.array([-fields[i], fields[i]])}
        for i in range(g["n_vars"])
    ]
    g["unary"] = unary
    g["fields"] = fields
    return g


if __name__ == "__main__":
    for n in SIZES:
        for beta in BETAS:
            g = make_ising_grid_with_field(n, beta)
            print(f"n={n} beta={beta:.2f}: {g['n_vars']} vars, {len(g['factors'])} factors, "
                  f"{len(g['unary'])} unary")
