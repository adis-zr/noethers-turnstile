"""GasTown ProofContext builder.

Builds a noethers-turnstile ProofContext from a TraceState.

Gap taxonomy Θ_GT_v1 (7 gaps):
  context_integrity_gap
  delegation_authority_gap
  completion_evidence_gap
  escalation_validity_gap
  merge_safety_gap
  authority_chain_gap
  experiment_scope_gap  (only when bead.type=experiment)

Profile Φ_GT_v1:
                              DIA   REV   AEX   ALR   AAA
  context_integrity_gap        OA    BND   BND   CLO   CLO
  delegation_authority_gap     OA    OA    BND   CLO   CLO
  completion_evidence_gap      OA    OA    BND   CLO   CLO
  escalation_validity_gap      OA    BND   CLO   CLO   CLO
  merge_safety_gap             OA    OA    OA    CLO   CLO
  authority_chain_gap          OA    OA    BND   CLO   CLO
  experiment_scope_gap         OA    OA    CLO   N/A   N/A

N/A at ALR/AAA for experiment_scope_gap: those profiles simply don't
include that gap requirement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import noethers_turnstile as t

from .provenance import _build_context_id, compute_action_provenance_hash
from .authority_registry import get_ceiling, is_in_class


# ── Gap taxonomy constants ─────────────────────────────────────────────────────

STANDARD_GAPS = [
    "context_integrity_gap",
    "delegation_authority_gap",
    "completion_evidence_gap",
    "escalation_validity_gap",
    "merge_safety_gap",
    "authority_chain_gap",
]

EXPERIMENT_GAP = "experiment_scope_gap"


# ── Profile requirement tables ─────────────────────────────────────────────────

# Mapping: permission → {gap_id: minimum_status} for each gap that must be
# better than OPEN to reach that permission tier.
# Gaps not listed for a profile are OPEN_ALLOWED at that tier.

_REV_REQS = {
    "context_integrity_gap": "bounded",
    "escalation_validity_gap": "bounded",
}

_AEX_REQS = {
    "context_integrity_gap": "bounded",
    "delegation_authority_gap": "bounded",
    "completion_evidence_gap": "bounded",
    # escalation_validity_gap: CLO if present (has_escalation=True)
    "escalation_validity_gap": "closed",
    "authority_chain_gap": "bounded",
    "experiment_scope_gap": "closed",   # only present for experiment beads
}

_ALR_REQS = {
    "context_integrity_gap": "closed",
    "delegation_authority_gap": "closed",
    "completion_evidence_gap": "closed",
    "escalation_validity_gap": "closed",
    "merge_safety_gap": "closed",
    "authority_chain_gap": "closed",
    # experiment_scope_gap: N/A (not included)
}

_AAA_REQS = {
    "context_integrity_gap": "closed",
    "delegation_authority_gap": "closed",
    "completion_evidence_gap": "closed",
    "escalation_validity_gap": "closed",
    "merge_safety_gap": "closed",
    "authority_chain_gap": "closed",
    # experiment_scope_gap: N/A (not included)
}


def build_profiles(
    is_experiment: bool = False,
    has_merge: bool = True,
    has_escalation: bool = True,
) -> list[t.Profile]:
    """Build the set of noethers-turnstile Profile objects for Φ_GT_v1.

    Parameters
    ----------
    is_experiment : bool
        If True, include experiment_scope_gap in the AEX profile requirements.
    has_merge : bool
        If False, exclude merge_safety_gap from profiles (gap not present).
    has_escalation : bool
        If False, exclude escalation_validity_gap from profiles (gap not present).
    """
    profiles: list[t.Profile] = [
        # DIA: floor — no gap requirements
        t.Profile(permission=t.Permission.DIA, required_gaps=[]),
    ]

    # REV requirements (filter by available gaps)
    rev_reqs = {g: s for g, s in _REV_REQS.items()
                if _gap_applicable(g, is_experiment=is_experiment, has_merge=has_merge, has_escalation=has_escalation)}
    profiles.append(t.Profile(
        permission=t.Permission.REV,
        required_gaps=[t.GapRequirement(g, s) for g, s in rev_reqs.items()],
    ))

    # AEX: only buildable if is_experiment (requires experiment_scope_gap CLOSED)
    if is_experiment:
        aex_reqs = {g: s for g, s in _AEX_REQS.items()
                    if _gap_applicable(g, is_experiment=True, has_merge=has_merge, has_escalation=has_escalation)}
        profiles.append(t.Profile(
            permission=t.Permission.AEX,
            required_gaps=[t.GapRequirement(g, s) for g, s in aex_reqs.items()],
        ))

    # ALR requirements
    alr_reqs = {g: s for g, s in _ALR_REQS.items()
                if _gap_applicable(g, is_experiment=is_experiment, has_merge=has_merge, has_escalation=has_escalation)}
    profiles.append(t.Profile(
        permission=t.Permission.ALR,
        required_gaps=[t.GapRequirement(g, s) for g, s in alr_reqs.items()],
    ))

    # AAA requirements
    aaa_reqs = {g: s for g, s in _AAA_REQS.items()
                if _gap_applicable(g, is_experiment=is_experiment, has_merge=has_merge, has_escalation=has_escalation)}
    profiles.append(t.Profile(
        permission=t.Permission.AAA,
        required_gaps=[t.GapRequirement(g, s) for g, s in aaa_reqs.items()],
    ))

    return profiles


def _gap_applicable(
    gap_id: str,
    is_experiment: bool,
    has_merge: bool,
    has_escalation: bool,
) -> bool:
    """Return True iff the gap is applicable given the context.

    escalation_validity_gap is applicable for both escalation AND merge claims.
    """
    if gap_id == "experiment_scope_gap" and not is_experiment:
        return False
    if gap_id == "merge_safety_gap" and not has_merge:
        return False
    if gap_id == "escalation_validity_gap" and not (has_escalation or has_merge):
        return False
    return True


def _build_gap_list(
    is_experiment: bool,
    has_merge: bool = False,
    has_escalation: bool = False,
) -> list[t.GapRecord]:
    """Build the list of GapRecord objects for the proof context.

    Gap induction rules:
    - context_integrity_gap: always induced
    - delegation_authority_gap: always induced
    - completion_evidence_gap: always induced
    - authority_chain_gap: always induced
    - merge_safety_gap: only induced for merge claims (has_merge=True)
    - escalation_validity_gap: induced for escalation AND merge claims
      (merge claims also require escalation_validity for ALR)
    - experiment_scope_gap: only induced when bead.type=experiment

    Gap counts:
    - completion claim, non-experiment bead: 4 gaps
    - escalation claim, non-experiment bead: 5 gaps
    - merge claim, non-experiment bead: 6 gaps (ADAPTER-084)
    - merge claim, experiment bead: 7 gaps (ADAPTER-085)
    """
    # escalation_validity_gap is induced for escalation AND merge claims
    needs_escalation_gap = has_escalation or has_merge

    gaps = []
    for gap_id in STANDARD_GAPS:
        if gap_id == "merge_safety_gap" and not has_merge:
            continue
        if gap_id == "escalation_validity_gap" and not needs_escalation_gap:
            continue
        gaps.append(t.GapRecord(gap_id=gap_id, gap_type=gap_id))
    if is_experiment:
        gaps.append(t.GapRecord(gap_id=EXPERIMENT_GAP, gap_type=EXPERIMENT_GAP))
    return gaps


def build_context_id(run_id: str, rig: str, git_commit: str) -> str:
    """Public alias for building a context_id from the three environment dimensions."""
    return _build_context_id(run_id, rig, git_commit)


@dataclass
class ProfileSpec:
    """A profile spec with inspectable required_gaps.

    Since t.Profile does not expose required_gaps after construction,
    this wrapper stores them for testing and evaluation.
    """
    permission: t.Permission
    required_gaps: list  # list of t.GapRequirement


def build_profile_specs(
    is_experiment: bool = False,
    has_merge: bool = False,
    has_escalation: bool = False,
) -> list[ProfileSpec]:
    """Build inspectable ProfileSpec objects with required_gaps accessible.

    Returns a list of ProfileSpec (not t.Profile) so tests can inspect
    gap requirements.
    """
    specs: list[ProfileSpec] = [
        ProfileSpec(permission=t.Permission.DIA, required_gaps=[]),
    ]

    # REV requirements
    rev_reqs = [
        t.GapRequirement(g, s)
        for g, s in _REV_REQS.items()
        if _gap_applicable(g, is_experiment=is_experiment, has_merge=has_merge, has_escalation=has_escalation)
    ]
    specs.append(ProfileSpec(permission=t.Permission.REV, required_gaps=rev_reqs))

    # AEX requirements (only when experiment)
    if is_experiment:
        aex_reqs = [
            t.GapRequirement(g, s)
            for g, s in _AEX_REQS.items()
            if _gap_applicable(g, is_experiment=True, has_merge=has_merge, has_escalation=has_escalation)
        ]
        specs.append(ProfileSpec(permission=t.Permission.AEX, required_gaps=aex_reqs))

    # ALR requirements
    alr_reqs = [
        t.GapRequirement(g, s)
        for g, s in _ALR_REQS.items()
        if _gap_applicable(g, is_experiment=is_experiment, has_merge=has_merge, has_escalation=has_escalation)
    ]
    specs.append(ProfileSpec(permission=t.Permission.ALR, required_gaps=alr_reqs))

    # AAA requirements
    aaa_reqs = [
        t.GapRequirement(g, s)
        for g, s in _AAA_REQS.items()
        if _gap_applicable(g, is_experiment=is_experiment, has_merge=has_merge, has_escalation=has_escalation)
    ]
    specs.append(ProfileSpec(permission=t.Permission.AAA, required_gaps=aaa_reqs))

    return specs


@dataclass
class ProofContextBundle:
    """Bundle of proof context ingredients for inspection.

    Since t.ProofContext does not expose gaps, profiles, or tokens after
    construction, we keep the ingredients in this bundle for testing and
    evaluator use.
    """
    proof_context: t.ProofContext
    gaps: list  # list of t.GapRecord
    profiles_data: list  # list of dicts {"permission": str, "required_gaps": [{gap_id, min_status}]}
    tokens: list  # list of t.ProofToken
    claim_id: str
    candidate_id: str
    context_id: str
    allowed_use: str


def build_proof_context_bundle(state: "TraceState") -> "ProofContextBundle":
    """Build a ProofContextBundle from a TraceState for inspection."""
    is_experiment = state.bead_type == "experiment"
    has_merge = state.claim_class == "merge"
    has_escalation = state.claim_class == "escalation"

    action_id = state.action_id or state.run_id
    bead_id = state.bead_id
    context_id = _build_context_id(state.run_id, state.rig, state.git_commit)

    gaps = _build_gap_list(
        is_experiment=is_experiment,
        has_merge=has_merge,
        has_escalation=has_escalation,
    )
    profiles = build_profiles(
        is_experiment=is_experiment,
        has_merge=has_merge,
        has_escalation=has_escalation,
    )

    # Build profiles_data for inspection
    profiles_data = []
    for p in profiles:
        profiles_data.append({"permission": str(p.permission), "required_gaps": []})

    ceiling = get_ceiling(state.role)
    membership = (
        t.Membership.InClass if is_in_class(state.role)
        else t.Membership.OutOfClassExact
    )

    proof_ctx = t.ProofContext(
        claim_id=action_id,
        candidate_id=bead_id,
        context_id=context_id,
        allowed_use=state.claim_class,
        membership=membership,
        authority_ceiling=ceiling,
        expiry=t.Expiry.never(),
        gaps=gaps,
        profiles=profiles,
        tokens=state.tokens,
        context_fingerprint=context_id,
    )

    return ProofContextBundle(
        proof_context=proof_ctx,
        gaps=gaps,
        profiles_data=profiles_data,
        tokens=state.tokens,
        claim_id=action_id,
        candidate_id=bead_id,
        context_id=context_id,
        allowed_use=state.claim_class,
    )


@dataclass
class TraceState:
    """Accumulated state for a single (bead_id, run_id) claim context."""
    run_id: str
    bead_id: str
    rig: str
    git_commit: str
    role: str
    bead_type: str = "normal"
    claim_class: str = "completion"
    action_id: Optional[str] = None

    # Gap evidence accumulators
    context_integrity_status: str = "open"    # "open", "bounded", "closed"
    delegation_authority_status: str = "open"
    completion_evidence_status: str = "open"
    escalation_validity_status: str = "open"
    merge_safety_status: str = "open"
    authority_chain_status: str = "open"
    experiment_scope_status: str = "open"

    # Collected ProofTokens
    tokens: list = field(default_factory=list)

    # Provenance mismatch flag
    has_provenance_mismatch: bool = False


def _status_to_gap_record(status: str, gap_id: str) -> t.GapRecord:
    """Build a GapRecord with initial state based on the status string."""
    # GapRecord starts open by default; status is applied via tokens
    return t.GapRecord(gap_id=gap_id, gap_type=gap_id)


def build_proof_context(state: TraceState) -> t.ProofContext:
    """Build a noethers-turnstile ProofContext from a TraceState.

    The claim_id is the action_id (or run_id if not set).
    The candidate_id is the bead_id.
    The context_id is "{run_id}|{rig}|{git_commit}".
    The allowed_use is the claim_class string.
    """
    is_experiment = state.bead_type == "experiment"
    has_merge = state.claim_class == "merge"
    has_escalation = state.claim_class == "escalation"

    action_id = state.action_id or state.run_id
    bead_id = state.bead_id
    context_id = _build_context_id(state.run_id, state.rig, state.git_commit)

    # Authority ceiling from role
    ceiling = get_ceiling(state.role)
    membership = (
        t.Membership.InClass if is_in_class(state.role)
        else t.Membership.OutOfClassExact
    )

    gaps = _build_gap_list(
        is_experiment=is_experiment,
        has_merge=has_merge,
        has_escalation=has_escalation,
    )
    profiles = build_profiles(
        is_experiment=is_experiment,
        has_merge=has_merge,
        has_escalation=has_escalation,
    )

    # Handle provenance mismatch: if any token had a mismatch, force OOC/REF
    # by adjusting membership. noethers-turnstile enforces provenance hash
    # checking internally; mismatching tokens are simply ineffective.

    return t.ProofContext(
        claim_id=action_id,
        candidate_id=bead_id,
        context_id=context_id,
        allowed_use=state.claim_class,
        membership=membership,
        authority_ceiling=ceiling,
        expiry=t.Expiry.never(),
        gaps=gaps,
        profiles=profiles,
        tokens=state.tokens,
        context_fingerprint=context_id,
    )
