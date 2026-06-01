"""Generate random factor graphs at varying sizes for Claim 2 benchmarks.

Generates Ising-like factor graphs (pairwise, binary variables) using a
random grid or random sparse structure. The graph is used to run loopy BP
(the inference step), whose runtime is measured separately from the compiler.

Outputs are compatible with ising/run_bp.py input format.

Size parameter: n_vars (number of binary variable nodes).
"""
from __future__ import annotations

import numpy as np


def random_grid_ising(
    n_vars: int,
    beta: float = 0.30,
    rng: np.random.Generator | None = None,
) -> dict:
    """Generate a random Ising factor graph with approximately n_vars variables.

    Uses a 2D grid topology where possible; falls back to a random sparse
    graph for non-square sizes.

    Returns a dict compatible with ising/run_bp.py:
      n_vars      : int
      n_factors   : int
      unary        : np.ndarray shape (n_vars, 2) — log-potentials
      pairwise     : list of (i, j, np.ndarray shape (2,2)) — log-potentials
      beta         : float
    """
    if rng is None:
        rng = np.random.default_rng(42)

    # Try to make a square grid; if not perfect square, use nearest square
    side = int(np.sqrt(n_vars))
    actual_vars = side * side
    if actual_vars == 0:
        actual_vars = 1
        side = 1

    # Unary potentials: small random bias
    unary = rng.normal(0, 0.1, size=(actual_vars, 2))

    # Pairwise potentials: Ising coupling J * s_i * s_j
    # Encoded as 2x2 log-potential matrix
    J = beta
    pairwise_pot = np.array([
        [ J, -J],
        [-J,  J],
    ])
    pairwise = []
    for row in range(side):
        for col in range(side):
            i = row * side + col
            # Right neighbour
            if col + 1 < side:
                j = row * side + (col + 1)
                pairwise.append((i, j, pairwise_pot.copy()))
            # Down neighbour
            if row + 1 < side:
                j = (row + 1) * side + col
                pairwise.append((i, j, pairwise_pot.copy()))

    return {
        "n_vars": actual_vars,
        "n_factors": len(pairwise),
        "unary": unary,
        "pairwise": pairwise,
        "beta": beta,
        "topology": "grid",
        "side": side,
    }


def random_sparse_ising(
    n_vars: int,
    beta: float = 0.30,
    avg_degree: float = 3.0,
    rng: np.random.Generator | None = None,
) -> dict:
    """Generate a random sparse Ising graph (Erdos-Renyi edges).

    For non-grid sizes. Expected edges ≈ n_vars * avg_degree / 2.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    p_edge = avg_degree / max(n_vars - 1, 1)
    J = beta
    pairwise_pot = np.array([[J, -J], [-J, J]])

    unary = rng.normal(0, 0.1, size=(n_vars, 2))
    pairwise = []
    for i in range(n_vars):
        for j in range(i + 1, n_vars):
            if rng.random() < p_edge:
                pairwise.append((i, j, pairwise_pot.copy()))

    return {
        "n_vars": n_vars,
        "n_factors": len(pairwise),
        "unary": unary,
        "pairwise": pairwise,
        "beta": beta,
        "topology": "sparse",
        "avg_degree": avg_degree,
    }


def graphs_at_sizes(
    sizes: list[int],
    beta: float = 0.30,
    topology: str = "grid",
    rng: np.random.Generator | None = None,
) -> list[dict]:
    """Generate one graph at each requested size."""
    if rng is None:
        rng = np.random.default_rng(42)
    graphs = []
    for n in sizes:
        if topology == "grid":
            g = random_grid_ising(n, beta, rng)
        else:
            g = random_sparse_ising(n, beta, rng=rng)
        graphs.append(g)
    return graphs
