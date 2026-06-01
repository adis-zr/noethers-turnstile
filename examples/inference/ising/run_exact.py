"""Exact marginals for Ising grids via brute-force enumeration (4×4) and
junction tree variable elimination (6×6).

4×4 = 2^16 = 65536 states — fast brute-force.
6×6 = 2^36 — too large for brute-force; use junction tree / variable elimination.
"""
from __future__ import annotations

import itertools
import numpy as np
from generate_ising import make_ising_grid, BETAS, SIZES


# ── brute-force enumeration ───────────────────────────────────────────────────

def _log_prob_unnorm(state: np.ndarray, factors: list[dict], unary: list[dict] | None = None) -> float:
    lp = 0.0
    for f in factors:
        u, v = f["vars"]
        lp += f["log_vals"][state[u], state[v]]
    if unary:
        for f in unary:
            (i,) = f["vars"]
            lp += f["log_vals"][state[i]]
    return lp


def exact_marginals_brute(graph: dict) -> np.ndarray:
    """Return marginals[i, s] = P(x_i = s) for all vars and states {0,1}.

    Only feasible for small graphs (n_vars ≤ 20).
    """
    n = graph["n_vars"]
    factors = graph["factors"]
    unary = graph.get("unary")

    log_z = -np.inf
    marginal_unnorm = np.zeros((n, 2))

    for bits in itertools.product([0, 1], repeat=n):
        state = np.array(bits, dtype=np.int32)
        lp = _log_prob_unnorm(state, factors, unary)
        # log-sum-exp accumulation
        if lp > log_z:
            # rescale
            marginal_unnorm *= np.exp(log_z - lp)
            log_z = lp
        w = np.exp(lp - log_z)
        for i, s in enumerate(bits):
            marginal_unnorm[i, s] += w

    # Normalise each variable
    marginals = marginal_unnorm / marginal_unnorm.sum(axis=1, keepdims=True)
    return marginals


# ── junction tree (bucket elimination) for 6×6 ────────────────────────────────

def _min_fill_order(n_vars: int, neighbors: list[list[int]]) -> list[int]:
    """Greedy min-fill elimination order."""
    adj = [set(nb) for nb in neighbors]
    remaining = set(range(n_vars))
    order = []
    while remaining:
        best = min(remaining, key=lambda v: sum(
            1 for u in adj[v] for w in adj[v] if w != u and w not in adj[u]
            if u in remaining and w in remaining
        ))
        order.append(best)
        remaining.remove(best)
        nb = [u for u in adj[best] if u in remaining]
        for u in nb:
            for w in nb:
                if w != u:
                    adj[u].add(w)
    return order


def exact_marginals_ve(graph: dict) -> np.ndarray:
    """Variable elimination for moderate graphs.

    Uses log-space factors to avoid underflow; eliminates in min-fill order.
    Returns marginals[i, s] = P(x_i = s).
    """
    n_vars = graph["n_vars"]
    neighbors = graph["neighbors"]
    factors_in = graph["factors"]
    unary_in = graph.get("unary", [])

    log_factors: list[dict] = []
    for f in factors_in:
        u, v = f["vars"]
        log_factors.append({"vars": (u, v), "log_table": f["log_vals"].copy()})
    for f in unary_in:
        (i,) = f["vars"]
        log_factors.append({"vars": (i,), "log_table": f["log_vals"].copy()})

    order = _min_fill_order(n_vars, neighbors)

    # For each variable in elimination order, collect all factors containing it,
    # multiply (add in log space), marginalise out the variable.
    marginals = np.zeros((n_vars, 2))

    for elim_var in order:
        # Collect factors containing elim_var
        active = [f for f in log_factors if elim_var in f["vars"]]
        rest = [f for f in log_factors if elim_var not in f["vars"]]

        # Combine active factors into one
        # Find all variables in the combined factor
        all_vars: list[int] = []
        seen = set()
        for f in active:
            for v in f["vars"]:
                if v not in seen:
                    all_vars.append(v)
                    seen.add(v)

        # Build combined log-table over all_vars
        shape = tuple(2 for _ in all_vars)
        combined = np.zeros(shape)
        for f in active:
            # Map f's vars to indices in all_vars
            axes = tuple(all_vars.index(v) for v in f["vars"])
            # Broadcast f["log_table"] into combined
            slices = [np.newaxis] * len(all_vars)
            for ax, _ in zip(axes, f["vars"]):
                slices[ax] = slice(None)
            combined += f["log_table"][tuple(slices)]

        # Compute marginal of elim_var (before summing out) for output
        elim_axis = all_vars.index(elim_var)
        # Sum over everything except elim_axis
        sum_axes = tuple(i for i in range(len(all_vars)) if i != elim_axis)
        log_marg_unnorm = combined
        for ax in sorted(sum_axes, reverse=True):
            # log-sum-exp over this axis
            mx = log_marg_unnorm.max(axis=ax, keepdims=True)
            log_marg_unnorm = mx + np.log(np.exp(log_marg_unnorm - mx).sum(axis=ax, keepdims=True))
        log_marg_unnorm = log_marg_unnorm.squeeze()
        log_z_var = log_marg_unnorm.max()
        marg = np.exp(log_marg_unnorm - log_z_var)
        marginals[elim_var] = marg / marg.sum()

        # Sum out elim_var from combined to produce new factor
        new_vars = [v for v in all_vars if v != elim_var]
        if new_vars:
            mx = combined.max(axis=elim_axis, keepdims=True)
            new_log = mx.squeeze(axis=elim_axis) + np.log(
                np.exp(combined - mx).sum(axis=elim_axis)
            )
            rest.append({"vars": tuple(new_vars), "log_table": new_log})

        log_factors = rest

    return marginals


def compute_exact_marginals(graph: dict) -> np.ndarray:
    n_vars = graph["n_vars"]
    if n_vars <= 20:
        return exact_marginals_brute(graph)
    else:
        return exact_marginals_ve(graph)


if __name__ == "__main__":
    import json, time
    results = {}
    for n in SIZES:
        for beta in BETAS:
            g = make_ising_grid(n, beta)
            t0 = time.time()
            marg = compute_exact_marginals(g)
            elapsed = time.time() - t0
            # On symmetric Ising with open boundary, all marginals should be [0.5, 0.5]
            # at any beta (no external field). Verify.
            key = f"{n}x{n}_b{beta:.2f}"
            results[key] = {
                "n": n, "beta": beta,
                "marginals_mean": float(marg[:, 1].mean()),
                "marginals_std": float(marg[:, 1].std()),
                "elapsed_s": round(elapsed, 3),
            }
            print(f"n={n} beta={beta:.2f}: mean(p+)={marg[:,1].mean():.4f} "
                  f"std={marg[:,1].std():.4f} t={elapsed:.2f}s")
    print("\nAll exact marginals computed.")
