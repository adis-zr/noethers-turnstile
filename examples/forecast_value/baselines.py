"""§4 External baselines: cost-loss, DRO-over-fiber, naive-coarse compiler.

The naive-coarse compiler is implemented in domain.compile_naive_coarse and
is imported here for symmetry.

Conventions for mapping {act, don't act} to the permission lattice:
  act      → AEX  (committing cost; assisted execution or recommend)
  don't    → REV  (escalate / no action)
This is the cost-loss rule's two-output mapping. Cost-loss does not produce
ALR (autonomous action without human in loop) because cost-loss has no
representation of the autonomy boundary. Mapping its "act" to AEX is the
charitable encoding: cost-loss says trigger, AEX says assisted execution
which is the strongest action a value-only rule can defend without a
soundness obligation about the autonomy boundary itself.
"""
from __future__ import annotations

from worldgen import World, COST_C, L_BAR_SCALAR
from domain import (
    perm_rank, perm_meet,
    world_authorization, latent_authorization,
)


def cost_loss_decision(p_hat: float, c: float = COST_C, l_bar: float = L_BAR_SCALAR) -> str:
    """Cost-loss permission: act iff p_hat > c / l_bar.

    Returns a permission string. Acts → AEX. Doesn't → REV.
    """
    threshold = c / l_bar
    return "AEX" if p_hat > threshold else "REV"


def dro_over_fiber(fiber: list[World], c: float = COST_C, l_bar: float = L_BAR_SCALAR) -> str:
    """DRO over ambiguity set = F(e), oriented for action soundness.

    The spec §6.3 says A(e) coincides with DRO-over-fiber at L0. To match the
    meet's orientation, we encode DRO as: "act if acting is the worst-case-
    optimal decision for every world in the ambiguity set" — i.e. act iff
    in every world in F(e), acting yields lower cost than not acting.

    Acting cost in world w: C (committed regardless of frost).
    Not-acting cost in world w: L_real(w).

    Act iff for every w in F(e), C < L_real(w), i.e. min L_real > C.
    Equivalently, the meet over fiber of the per-world cost-comparison.

    This is the "conservative DRO" reading aligned with the meet. The
    aggressive reading (act if there exists a world with high loss) is the
    join, which is the opposite of A(e). The spec uses the former.
    """
    if not fiber:
        return "REV"
    min_loss = min(w.l_real for w in fiber)
    return "AEX" if min_loss > c else "REV"


# noethers_turnstile compiler under the inadmissible coarse profile is the
# third baseline; that lives in domain.compile_naive_coarse.
