"""Generate state transition sequences for Claim 4 (expiry check) benchmarks.

A transition sequence is a list of (failure_vector, expiry_flag) pairs.
expiry_flag=True means the judgment from the previous step has expired and
must be re-evaluated. The latch-false property: once expired, the state
is not re-evaluated until the next transition that clears it.

Sequence properties:
  length         : number of steps
  expiry_rate    : fraction of steps where expiry fires (0=never, 1=always)
  density        : failure vector density at each step (controls forward scan cost)
"""
from __future__ import annotations

import numpy as np


def random_sequence(
    length: int,
    m_bits: int,
    density: float = 0.3,
    expiry_rate: float = 0.1,
    rng: np.random.Generator | None = None,
) -> list[dict]:
    """Generate a random transition sequence.

    Returns a list of dicts:
      failure_bits : np.ndarray shape (m,), dtype bool
      expiry       : bool — True if judgment expired at this step
    """
    if rng is None:
        rng = np.random.default_rng(0)

    steps = []
    for _ in range(length):
        bits = rng.random(m_bits) < density
        expiry = rng.random() < expiry_rate
        steps.append({"failure_bits": bits.astype(bool), "expiry": bool(expiry)})
    return steps


def sequences_at_lengths(
    lengths: list[int],
    m_bits: int,
    density: float = 0.3,
    expiry_rate: float = 0.1,
    rng: np.random.Generator | None = None,
) -> list[tuple[int, list[dict]]]:
    """Generate one sequence at each requested length."""
    if rng is None:
        rng = np.random.default_rng(0)
    return [(L, random_sequence(L, m_bits, density, expiry_rate, rng)) for L in lengths]
