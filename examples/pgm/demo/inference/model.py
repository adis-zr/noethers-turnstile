"""Graphical model representation."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Variable:
    id: int
    cardinality: int

    def __post_init__(self) -> None:
        if self.cardinality < 2:
            raise ValueError(
                f"Variable {self.id}: cardinality must be >= 2, got {self.cardinality}"
            )


@dataclass
class Factor:
    """
    A non-negative factor over a set of variables.

    scope: variable ids in last-variable-fastest order.
    table: flat probability/potential values, length = product(cardinalities).
    """

    scope: tuple[int, ...]
    table: tuple[float, ...]

    @property
    def num_entries(self) -> int:
        return len(self.table)


@dataclass
class GraphicalModel:
    """A finite discrete graphical model (positive factor graph)."""

    variables: list[Variable]
    factors: list[Factor]

    @property
    def domains(self) -> dict[int, int]:
        return {v.id: v.cardinality for v in self.variables}

    def factors_as_dicts(self) -> list[dict]:
        """Bridge to archive-style factor dicts for envelope builder compatibility."""
        return [{"scope": list(f.scope), "table": list(f.table)} for f in self.factors]


@dataclass(frozen=True)
class Query:
    """The query: which variables to marginalize to."""

    variables: tuple[int, ...]
