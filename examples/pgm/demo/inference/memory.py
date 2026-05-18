"""Memory accounting for certified inference plans."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryState:
    """
    Conservative upper bound on peak memory usage in bytes.

    Composition is additive (all outputs counted simultaneously), which is
    sound but not tight. A tighter overlap-aware model can be substituted
    later without changing this interface.
    """

    bytes: int

    def __post_init__(self) -> None:
        if self.bytes < 0:
            raise ValueError(f"MemoryState.bytes must be >= 0, got {self.bytes}")

    def compose(self, other: "MemoryState") -> "MemoryState":
        return MemoryState(self.bytes + other.bytes)

    def dominates(self, other: "MemoryState") -> bool:
        """True iff self uses no more memory than other."""
        return self.bytes <= other.bytes

    def fits_within(self, budget: "MemoryState") -> bool:
        return self.bytes <= budget.bytes

    def __add__(self, other: "MemoryState") -> "MemoryState":
        return MemoryState(self.bytes + other.bytes)

    def __le__(self, other: "MemoryState") -> bool:
        return self.bytes <= other.bytes

    def __lt__(self, other: "MemoryState") -> bool:
        return self.bytes < other.bytes
