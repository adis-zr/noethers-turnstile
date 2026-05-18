"""KernelFamily interface."""
from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..candidates import Candidate
    from ..envelope import Site
    from ..model import GraphicalModel


class KernelFamily(abc.ABC):
    @abc.abstractmethod
    def candidates(
        self,
        site: "Site",
        model_factors: list[dict],
        model: "GraphicalModel",
        memory_budget: int = 0,
    ) -> list["Candidate"]:
        """
        Return all sound Candidates this family can propose for the given site.

        Must return [] if inapplicable. Must not raise.

        memory_budget: bytes available for this site's operator.  When > 0,
        implementations should skip candidates whose memory estimate exceeds
        the budget — the DP will never select them, and building them eagerly
        wastes time and memory.  When 0 (default), no budget filter is applied.
        """
        ...
