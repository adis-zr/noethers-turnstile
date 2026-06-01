"""Mean-field inference on Ising grids.

Standard naive mean-field: factorise q(x) = prod_i q_i(x_i), minimise KL(q||p).
Update rule for Ising: m_i = tanh( beta * sum_{j in N(i)} m_j )
where m_i = E_q[s_i] = q_i(+1) - q_i(-1) = 2*q_i(1) - 1.

Converges to a fixed point; may not converge above T_c.
"""
from __future__ import annotations

import numpy as np
from generate_ising import make_ising_grid, BETAS, SIZES


def run_mean_field(
    graph: dict,
    max_iter: int = 200,
    tol: float = 1e-6,
    damping: float = 0.5,
    seed: int = 42,
) -> dict:
    """Run mean-field on a pairwise Ising graph.

    Returns
    -------
    dict with keys:
        marginals  : np.ndarray (n_vars, 2) — [P(x=0), P(x=1)]
        converged  : bool
        n_iter     : int
        max_delta  : float
    """
    n_vars = graph["n_vars"]
    neighbors = graph["neighbors"]
    beta = graph["beta"]
    # Extract external fields from unary factors; state 1 = spin +1, log_val = +h_i
    # so h_i = log_vals[1] (= log_vals[1] - log_vals[0]) / 2 in energy units
    fields = np.zeros(n_vars)
    for f in graph.get("unary", []):
        (i,) = f["vars"]
        fields[i] = f["log_vals"][1]  # h_i (already in log-space = energy units)

    rng = np.random.default_rng(seed)
    # Initialise magnetisations near 0
    m = rng.uniform(-0.01, 0.01, size=n_vars)

    converged = False
    n_iter = 0
    max_delta = float("inf")

    for iteration in range(max_iter):
        m_new = np.zeros(n_vars)
        for i in range(n_vars):
            field = fields[i] + beta * sum(m[j] for j in neighbors[i])
            m_new[i] = np.tanh(field)

        # Damping
        m_damped = damping * m + (1 - damping) * m_new
        max_delta = float(np.abs(m_damped - m).max())
        m = m_damped
        n_iter = iteration + 1

        if max_delta < tol:
            converged = True
            break

    # Convert magnetisations to marginal probabilities
    # m = P(+1) - P(-1) = 2*P(+1) - 1  =>  P(+1) = (1 + m) / 2
    p_plus = (1 + m) / 2
    marginals = np.stack([1 - p_plus, p_plus], axis=1)

    return {
        "marginals": marginals,
        "converged": converged,
        "n_iter": n_iter,
        "max_delta": max_delta,
    }


if __name__ == "__main__":
    for n in SIZES:
        for beta in BETAS:
            g = make_ising_grid(n, beta)
            r = run_mean_field(g)
            print(f"n={n} beta={beta:.2f}: converged={r['converged']} "
                  f"n_iter={r['n_iter']} max_delta={r['max_delta']:.2e} "
                  f"mean(p+)={r['marginals'][:,1].mean():.4f}")
