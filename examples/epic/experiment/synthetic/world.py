"""MED-STR-SYN-001: Synthetic world generator.

W(k, p, n, seed) generates n cases over k gaps. Each gap in each case is
independently OPEN with probability p, BOUNDED otherwise. Expert judgment
is ALR iff all k gaps are BOUNDED.

No human reads these cases. Gap statuses come from the RNG. The loop's only
oracle is the over-authorization signal from the compiler.

Structural skeleton gaps (approximation_quality_gap, freshness_gap) are
always BOUNDED in every synthetic case — they are preconditions for reaching
the AEX → ALR induction zone. We are probing domain gap discovery only.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

SKELETON_GAPS = ("approximation_quality_gap", "freshness_gap")


@dataclass
class SyntheticCase:
    case_id: str
    gap_statuses: dict[str, str]          # gap_id → "open" | "bounded"
    expert_judgment: str                   # "ALR" | "AEX"
    true_open_gaps: list[str]             # ground truth: which domain gaps are OPEN
    # spurious_gaps carries extra gap ids that are correlated but non-causal
    spurious_statuses: dict[str, str] = field(default_factory=dict)


def generate_world(
    *,
    k: int,
    p: float,
    n: int,
    seed: int,
    gap_prefix: str = "gap",
    spurious_k: int = 0,
    spurious_p: float = 0.7,
    rare_gap_index: int | None = None,
    rare_p: float | None = None,
) -> tuple[list[str], list[SyntheticCase]]:
    """Generate a synthetic world.

    Returns (ground_truth_gaps, cases).

    ground_truth_gaps: ordered list of k gap IDs — G in the spec.
    cases: n SyntheticCase records.

    Parameters
    ----------
    k             : number of true domain gaps
    p             : probability each gap is OPEN (failure mode present)
    n             : number of cases to generate
    seed          : RNG seed
    gap_prefix    : prefix for gap IDs ("gap" → "gap_0", "gap_1", ...)
    spurious_k    : number of spurious correlated gaps to add (experiment E)
    spurious_p    : probability spurious gap is OPEN when any true gap is open
    rare_gap_index: if set, override that gap's open probability with rare_p
    rare_p        : the rare gap's open probability
    """
    rng = random.Random(seed)

    true_gaps = [f"{gap_prefix}_{i}" for i in range(k)]
    spurious_gaps = [f"spurious_{i}" for i in range(spurious_k)]

    cases: list[SyntheticCase] = []
    for i in range(n):
        # Sample each domain gap independently
        domain_statuses: dict[str, str] = {}
        for gi, gid in enumerate(true_gaps):
            effective_p = p
            if rare_gap_index is not None and gi == rare_gap_index:
                effective_p = rare_p  # type: ignore[assignment]
            domain_statuses[gid] = "open" if rng.random() < effective_p else "bounded"

        true_open = [gid for gid in true_gaps if domain_statuses[gid] == "open"]

        # Expert judgment: ALR iff all true gaps are BOUNDED
        expert = "AEX" if true_open else "ALR"

        # Skeleton always bounded
        gap_statuses = {g: "bounded" for g in SKELETON_GAPS}
        gap_statuses.update(domain_statuses)

        # Spurious gaps: correlated with failure but not causally required
        spurious_statuses: dict[str, str] = {}
        if spurious_gaps:
            any_true_open = bool(true_open)
            for sgid in spurious_gaps:
                if any_true_open:
                    spurious_statuses[sgid] = "open" if rng.random() < spurious_p else "bounded"
                else:
                    # When all true gaps are BOUNDED, spurious gaps are also BOUNDED
                    spurious_statuses[sgid] = "bounded"

        cases.append(SyntheticCase(
            case_id=f"S{i:04d}",
            gap_statuses=gap_statuses,
            expert_judgment=expert,
            true_open_gaps=true_open,
            spurious_statuses=spurious_statuses,
        ))

    return true_gaps, spurious_gaps, cases
