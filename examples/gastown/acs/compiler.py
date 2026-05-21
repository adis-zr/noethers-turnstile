"""GasTown ACS compiler — thin wrapper around t.compile().

Exports build_candidates() for use by the evaluator.
"""

from __future__ import annotations
from typing import Any

import noethers_turnstile as t


def compile_context(proof_context: t.ProofContext) -> t.LiveJudgment:
    """Compile a ProofContext into a LiveJudgment.

    Thin wrapper around t.compile() with no additional logic.
    """
    return t.compile(proof_context)


def build_candidates(
    proof_context: t.ProofContext,
    profile: t.Profile | None = None,
    profiles: list[t.Profile] | None = None,
) -> list[t.Profile]:
    """Return the list of candidate profiles from the ProofContext.

    Used by the evaluator to recompute the permission meet independently
    (Steps 8-10 in the spec).

    Note: t.ProofContext does not expose its profiles after construction.
    Callers that need to inspect profiles should pass them via the `profiles`
    parameter (built alongside the ProofContext).

    If profiles is not given, returns an empty list (profiles not accessible).
    If profile is specified, filters to only that profile.
    """
    if proof_context is None:
        return []
    # t.ProofContext does not expose .profiles; use the provided list instead
    profile_list = profiles if profiles is not None else []
    if profile is None:
        return list(profile_list)
    return [p for p in profile_list if p.permission == profile.permission]
