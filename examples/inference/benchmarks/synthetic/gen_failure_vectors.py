"""Generate synthetic failure vectors with controlled properties.

All generators return np.ndarray of shape (batch, m_bits), dtype bool.
The inputs go through the same compiler_kernel.compile_kernel path as real
case-study inputs — no parallel reimplementation.

Generator catalogue
-------------------
uniform_density(m, batch, density, rng)
    Each bit is independently True with probability `density`.
    Used for: Claim 3 (scan depth distribution), Degenerate C/D.

fixed_density(m, batch, n_active, rng)
    Exactly `n_active` bits are True per vector (random positions).
    Used for: controlled density experiments, Degenerate B.

all_clear(m, batch)
    All bits False. Best-case: compiler terminates at level 0 immediately.
    Used for: Degenerate D (empty context), baseline.

all_failed(m, batch)
    All bits True. Worst-case: compiler scans all levels, finds REFUSE.
    Used for: Degenerate B upper bound.

contradictory(m, n_levels, blocking_map, batch, rng)
    Generates vectors where some bits clear some levels while others block them.
    Specifically: for each level i, half the blocking bits are active and half
    are not. The compiler should still emit a valid judgment (the first level
    where no blocking bit is active). Tests soundness under contradiction.
    Used for: Degenerate C.

graduated_density(m, batch, densities)
    Generates `batch` vectors with density linearly spaced across `densities`.
    Used for: density sweep figures.
"""
from __future__ import annotations

import numpy as np


def uniform_density(
    m: int,
    batch: int,
    density: float,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Each bit independently True with probability density."""
    if rng is None:
        rng = np.random.default_rng(0)
    return rng.random((batch, m)) < density


def fixed_density(
    m: int,
    batch: int,
    n_active: int,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Exactly n_active bits True per vector."""
    if rng is None:
        rng = np.random.default_rng(0)
    n_active = min(n_active, m)
    out = np.zeros((batch, m), dtype=bool)
    for i in range(batch):
        positions = rng.choice(m, size=n_active, replace=False)
        out[i, positions] = True
    return out


def all_clear(m: int, batch: int) -> np.ndarray:
    """All bits False — best case, compiler terminates immediately."""
    return np.zeros((batch, m), dtype=bool)


def all_failed(m: int, batch: int) -> np.ndarray:
    """All bits True — worst case, compiler scans all levels."""
    return np.ones((batch, m), dtype=bool)


def contradictory(
    m: int,
    n_levels: int,
    blocking_map: np.ndarray,
    batch: int,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Generate contradictory failure vectors.

    For each vector, for each level independently with probability 0.5:
    activate exactly HALF the blocking bits for that level (obstructs it)
    vs. activate ZERO bits for that level (clears it). This creates cases
    where some levels are blocked and others are clear in the same vector —
    the defining contradiction. The compiler must return the highest CLEAR level.

    Design: we pick a random "clear level" k for each vector, then activate
    all blocking bits for levels above k and no bits for level k. This
    guarantees a valid judgment at level k and tests that the scan terminates
    there without confusion from the blocked-above context.

    Soundness check: compile_kernel must never crash or return an
    out-of-range permission level on these inputs.
    """
    if rng is None:
        rng = np.random.default_rng(0)

    out = np.zeros((batch, m), dtype=bool)
    for i in range(batch):
        bits = np.zeros(m, dtype=bool)
        # Pick a clear level uniformly — this is where the scan should terminate
        clear_level = rng.integers(0, n_levels)
        # Block all levels strictly above clear_level by activating one blocking bit each
        for lvl in range(clear_level):
            blocking_bits = np.where(blocking_map[lvl])[0]
            if len(blocking_bits) > 0:
                chosen = rng.choice(blocking_bits, size=1)[0]
                bits[chosen] = True
        # clear_level itself: activate NO blocking bits (leave clear)
        # Levels below clear_level: don't matter (scan already terminated)
        out[i] = bits
    return out


def graduated_density(
    m: int,
    batch_per_density: int,
    densities: list[float],
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate vectors at each density level.

    Returns (vectors, density_labels):
      vectors       : shape (len(densities) * batch_per_density, m), dtype bool
      density_labels: shape (len(densities) * batch_per_density,), dtype float
    """
    if rng is None:
        rng = np.random.default_rng(0)

    all_vecs = []
    all_labels = []
    for d in densities:
        vecs = uniform_density(m, batch_per_density, d, rng)
        all_vecs.append(vecs)
        all_labels.extend([d] * batch_per_density)

    return np.vstack(all_vecs), np.array(all_labels)
