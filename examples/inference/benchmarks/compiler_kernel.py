"""Generic compiler kernel — the scan loop shared by all benchmarks and real compilers.

The kernel takes m failure bits and n permission levels and runs the obstruction
scan from strongest to weakest. It is the same logic as ising/compiler.py and
uai/compiler_uai.py, extracted so that:

  1. Benchmarks exercise the real scan path (not a proxy).
  2. The O(mn) cost claim is testable directly: instrument scan_count.

Input representation
--------------------
obstruction_matrix : np.ndarray shape (n, m), dtype bool
    obstruction_matrix[i, j] = True  means failure bit j blocks permission level i.
    Rows are ordered strongest-to-weakest (row 0 = highest permission).
    This is the Γ matrix from the theory.

Output
------
CompilerKernelResult with:
  permission_level : int   — index into [0, n-1]; 0 = highest, n-1 = lowest
                             -1 = REFUSE (all levels blocked)
  scan_depth       : int   — number of levels examined before termination
  bits_checked     : int   — total (level, bit) evaluations performed
  first_clear_level: int   — same as permission_level; -1 if none

Complexity
----------
Worst case:  scan_depth = n, bits_checked = m * n
Average case (density d): scan_depth ~ 1/(1-d^m) for independent bits,
             bits_checked ~ m * scan_depth
Best case:   scan_depth = 1, bits_checked = m (top level immediately clear)

The scan terminates at the first level with no active obstructions.
Early termination is the key property: average case << worst case.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class CompilerKernelResult:
    permission_level: int      # 0-indexed strongest-to-weakest; -1 = REFUSE
    scan_depth: int            # levels examined (1 = terminated immediately)
    bits_checked: int          # total (level × bit) evaluations
    first_clear_level: int     # same as permission_level


def compile_kernel(obstruction_matrix: np.ndarray) -> CompilerKernelResult:
    """Run the obstruction scan on a pre-built obstruction matrix.

    Parameters
    ----------
    obstruction_matrix : shape (n_levels, m_bits), dtype bool
        Row i contains the failure bits that block permission level i.
        Row 0 = strongest permission (e.g. ACT / TRANSMIT_CRITICAL).

    Returns
    -------
    CompilerKernelResult
    """
    n_levels, m_bits = obstruction_matrix.shape
    bits_checked = 0

    for i in range(n_levels):
        row = obstruction_matrix[i]
        bits_checked += m_bits
        if not row.any():
            return CompilerKernelResult(
                permission_level=i,
                scan_depth=i + 1,
                bits_checked=bits_checked,
                first_clear_level=i,
            )

    return CompilerKernelResult(
        permission_level=-1,     # REFUSE
        scan_depth=n_levels,
        bits_checked=bits_checked,
        first_clear_level=-1,
    )


def build_obstruction_matrix(
    failure_bits: np.ndarray,
    blocking_map: np.ndarray,
) -> np.ndarray:
    """Build the obstruction matrix from a failure vector and a blocking map.

    Parameters
    ----------
    failure_bits  : shape (m,), dtype bool  — which bits are active
    blocking_map  : shape (n, m), dtype bool — which bits block which levels

    Returns
    -------
    obstruction_matrix : shape (n, m), dtype bool
        obstruction_matrix[i, j] = blocking_map[i, j] AND failure_bits[j]
    """
    return blocking_map & failure_bits[np.newaxis, :]


def make_random_blocking_map(
    n_levels: int,
    m_bits: int,
    rng: np.random.Generator | None = None,
    mode: str = "monotone",
) -> np.ndarray:
    """Generate a blocking map for synthetic benchmarks.

    mode:
      "monotone"  — upper levels require all bits that lower levels do (nested).
                    Structurally matches the real compilers: if bit j blocks ACT,
                    it also blocks REPORT and EXPLORE.
      "arbitrary" — random blocking assignment, no monotonicity constraint.
                    Tests the kernel under worst-case structural assumptions.
      "dense"     — every bit blocks every level (maximum work per scan step).
      "sparse"    — each bit blocks exactly one level (minimum structural nesting).

    Returns shape (n_levels, m_bits), dtype bool.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    if mode == "monotone":
        # Each bit is assigned a minimum level it blocks; it blocks all levels >= that.
        # min_level[j] ~ Uniform(0, n_levels) — some bits block only top levels, others all.
        min_block = rng.integers(0, n_levels, size=m_bits)
        map_ = np.zeros((n_levels, m_bits), dtype=bool)
        for j in range(m_bits):
            map_[: min_block[j] + 1, j] = True
        return map_

    elif mode == "arbitrary":
        return rng.random((n_levels, m_bits)) > 0.5

    elif mode == "dense":
        return np.ones((n_levels, m_bits), dtype=bool)

    elif mode == "sparse":
        map_ = np.zeros((n_levels, m_bits), dtype=bool)
        levels = rng.integers(0, n_levels, size=m_bits)
        for j, lvl in enumerate(levels):
            map_[lvl, j] = True
        return map_

    else:
        raise ValueError(f"Unknown mode: {mode}")


def make_ising_obstruction_matrix(
    convergence_failure: bool,
    tv_exceeds_act: bool,
    tv_exceeds_report: bool,
    tv_exceeds_explore: bool,
) -> np.ndarray:
    """Build the obstruction matrix for the Ising compiler (3 levels × 2 bits).

    This is the concrete instantiation used in the real experiments.
    Benchmarks using this function exercise the exact same code path as Tier 1.

    Level layout (row 0 = strongest):
      Row 0: ACT     blocked by: convergence_failure, tv_exceeds_act
      Row 1: REPORT  blocked by: convergence_failure, tv_exceeds_report
      Row 2: EXPLORE blocked by: convergence_failure, tv_exceeds_explore

    Bit layout (column 0 = f1):
      Col 0: convergence_failure
      Col 1: tv_exceeds_act
      Col 2: tv_exceeds_report
      Col 3: tv_exceeds_explore
    """
    bits = np.array([
        convergence_failure,
        tv_exceeds_act,
        tv_exceeds_report,
        tv_exceeds_explore,
    ], dtype=bool)

    # blocking_map[level, bit]: which bits block which level
    blocking_map = np.array([
        [True,  True,  False, False],  # ACT:     f1, f2
        [True,  False, True,  False],  # REPORT:  f1, f3
        [True,  False, False, True ],  # EXPLORE: f1, f4
    ], dtype=bool)

    return build_obstruction_matrix(bits, blocking_map)
