"""Gap taxonomy, profile definitions, and ProofContext builder for MED-001.

Gap taxonomy (MED-001):
  approximation_quality_gap      EXISTING  — score close to model's training target
  model_specification_gap        EXISTING  — training target adequate for clinical question
  clinical_utility_gap           NEW       — sensitivity/PPV sufficient at operating threshold
  distribution_shift_gap         NEW       — model holds on deployment population
  calibration_gap                EXISTING  — predicted probabilities calibrated
  blast_radius_gap               EXISTING  — scope of downstream actions per alert
  freshness_gap                  EXISTING  — inputs were current at compute time
  shadow_mode_validation_gap     NEW (v3)  — local population shadow-mode test before go-live
  post_market_monitoring_gap     NEW (v3)  — ongoing evaluation plan in place

Profile v1: naive deployment profile — does not require clinical utility at ALR.
Profile v2: corrected profile — requires clinical_utility + distribution_shift at ALR/AAA.
Profile v3: FDA+NHS strict profile — adds shadow_mode_validation + post_market_monitoring
            at ALR. Encodes NHS RCR AI Deployment Fundamentals (2024) §4.21-4.22, §2.13
            and FDA Jan 2025 Draft Guidance Appendix C operating-point requirements.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import noethers_turnstile as t

# ── Gap IDs ────────────────────────────────────────────────────────────────────

GAP_APPROXIMATION_QUALITY    = "approximation_quality_gap"
GAP_MODEL_SPECIFICATION      = "model_specification_gap"
GAP_CLINICAL_UTILITY         = "clinical_utility_gap"
GAP_DISTRIBUTION_SHIFT       = "distribution_shift_gap"
GAP_CALIBRATION              = "calibration_gap"
GAP_BLAST_RADIUS             = "blast_radius_gap"
GAP_FRESHNESS                = "freshness_gap"
GAP_SHADOW_MODE_VALIDATION   = "shadow_mode_validation_gap"   # v3: NHS RCR §4.21
GAP_POST_MARKET_MONITORING   = "post_market_monitoring_gap"   # v3: NHS §2.13 / FDA PMA

ALL_GAPS = [
    GAP_APPROXIMATION_QUALITY,
    GAP_MODEL_SPECIFICATION,
    GAP_CLINICAL_UTILITY,
    GAP_DISTRIBUTION_SHIFT,
    GAP_CALIBRATION,
    GAP_BLAST_RADIUS,
    GAP_FRESHNESS,
    GAP_SHADOW_MODE_VALIDATION,
    GAP_POST_MARKET_MONITORING,
]

# ── Profile requirement tables ─────────────────────────────────────────────────
# Keys are gap IDs; values are minimum_status strings ("open", "bounded", "closed").
# Gaps absent from a table are OPEN_ALLOWED (no requirement = open is fine).

_V1_DIA_REQS: dict[str, str] = {}  # all open allowed

_V1_REV_REQS: dict[str, str] = {
    GAP_APPROXIMATION_QUALITY: "bounded",
}

_V1_AEX_REQS: dict[str, str] = {
    GAP_APPROXIMATION_QUALITY: "bounded",
    GAP_MODEL_SPECIFICATION:   "bounded",
    GAP_CALIBRATION:           "bounded",
    GAP_FRESHNESS:             "bounded",
}

_V1_ALR_REQS: dict[str, str] = {
    GAP_APPROXIMATION_QUALITY: "bounded",
    GAP_MODEL_SPECIFICATION:   "bounded",
    # clinical_utility_gap: open allowed  ← falsification target
    # distribution_shift_gap: open allowed ← falsification target
    GAP_CALIBRATION:           "bounded",
    GAP_BLAST_RADIUS:          "bounded",
    GAP_FRESHNESS:             "bounded",
}

_V1_AAA_REQS: dict[str, str] = {
    GAP_APPROXIMATION_QUALITY: "closed",
    GAP_MODEL_SPECIFICATION:   "bounded",
    # clinical_utility_gap: open allowed  ← falsification target
    GAP_DISTRIBUTION_SHIFT:    "bounded",
    GAP_CALIBRATION:           "closed",
    GAP_BLAST_RADIUS:          "bounded",
    GAP_FRESHNESS:             "closed",
}

# Profile v2 tightens only ALR and AAA; DIA/REV/AEX inherited unchanged.
_V2_ALR_REQS: dict[str, str] = {
    GAP_APPROXIMATION_QUALITY: "bounded",
    GAP_MODEL_SPECIFICATION:   "bounded",
    GAP_CLINICAL_UTILITY:      "bounded",   # new requirement
    GAP_DISTRIBUTION_SHIFT:    "bounded",   # new requirement
    GAP_CALIBRATION:           "bounded",
    GAP_BLAST_RADIUS:          "bounded",
    GAP_FRESHNESS:             "bounded",
}

_V2_AAA_REQS: dict[str, str] = {
    GAP_APPROXIMATION_QUALITY: "closed",
    GAP_MODEL_SPECIFICATION:   "bounded",
    GAP_CLINICAL_UTILITY:      "bounded",   # new requirement
    GAP_DISTRIBUTION_SHIFT:    "bounded",   # new requirement
    GAP_CALIBRATION:           "closed",
    GAP_BLAST_RADIUS:          "closed",
    GAP_FRESHNESS:             "closed",
}

# Profile v3: FDA+NHS strict profile.
# Adds two deployment-phase gaps derived from:
#   NHS RCR "AI Deployment Fundamentals for Medical Imaging" (Nov 2024)
#     §4.21: shadow mode mandatory before go-live
#     §4.22: enriched local population test set required
#     §2.13: post-implementation evaluation plan required before deployment
#   FDA Draft Guidance (Jan 2025) Appendix C:
#     operating-point metrics with 95% CIs required (enforced via detail contract)
#     PMA devices: post-market monitoring plan may be condition of approval
#
# V3 inherits DIA/REV/AEX from v1; inherits nothing new at ALR/AAA beyond v2 —
# it adds shadow_mode_validation and post_market_monitoring as new requirements.
_V3_ALR_REQS: dict[str, str] = {
    GAP_APPROXIMATION_QUALITY:  "bounded",
    GAP_MODEL_SPECIFICATION:    "bounded",
    GAP_CLINICAL_UTILITY:       "bounded",
    GAP_DISTRIBUTION_SHIFT:     "bounded",
    GAP_CALIBRATION:            "bounded",
    GAP_BLAST_RADIUS:           "bounded",
    GAP_FRESHNESS:              "bounded",
    GAP_SHADOW_MODE_VALIDATION: "bounded",  # NHS RCR §4.21-4.22 — new requirement
    GAP_POST_MARKET_MONITORING: "bounded",  # NHS §2.13 / FDA PMA — new requirement
}

_V3_AAA_REQS: dict[str, str] = {
    GAP_APPROXIMATION_QUALITY:  "closed",
    GAP_MODEL_SPECIFICATION:    "bounded",
    GAP_CLINICAL_UTILITY:       "bounded",
    GAP_DISTRIBUTION_SHIFT:     "bounded",
    GAP_CALIBRATION:            "closed",
    GAP_BLAST_RADIUS:           "closed",
    GAP_FRESHNESS:              "closed",
    GAP_SHADOW_MODE_VALIDATION: "bounded",  # NHS RCR §4.21-4.22 — new requirement
    GAP_POST_MARKET_MONITORING: "bounded",  # NHS §2.13 / FDA PMA — new requirement
}


def _make_profile(permission: t.Permission, reqs: dict[str, str]) -> t.Profile:
    required_gaps = [
        t.GapRequirement(gap_id=gid, minimum_status=status)
        for gid, status in reqs.items()
    ]
    return t.Profile(permission=permission, required_gaps=required_gaps)


def build_profiles_v1() -> list[t.Profile]:
    """Profile v1: naive deployment profile — falsification target."""
    return [
        _make_profile(t.Permission.DIA, _V1_DIA_REQS),
        _make_profile(t.Permission.REV, _V1_REV_REQS),
        _make_profile(t.Permission.AEX, _V1_AEX_REQS),
        _make_profile(t.Permission.ALR, _V1_ALR_REQS),
        _make_profile(t.Permission.AAA, _V1_AAA_REQS),
    ]


def build_profiles_v2() -> list[t.Profile]:
    """Profile v2: corrected profile — requires clinical_utility + distribution_shift at ALR/AAA."""
    return [
        _make_profile(t.Permission.DIA, _V1_DIA_REQS),
        _make_profile(t.Permission.REV, _V1_REV_REQS),
        _make_profile(t.Permission.AEX, _V1_AEX_REQS),
        _make_profile(t.Permission.ALR, _V2_ALR_REQS),
        _make_profile(t.Permission.AAA, _V2_AAA_REQS),
    ]


def build_profiles_v3() -> list[t.Profile]:
    """Profile v3: FDA+NHS strict profile — adds shadow_mode_validation + post_market_monitoring."""
    return [
        _make_profile(t.Permission.DIA, _V1_DIA_REQS),
        _make_profile(t.Permission.REV, _V1_REV_REQS),
        _make_profile(t.Permission.AEX, _V1_AEX_REQS),
        _make_profile(t.Permission.ALR, _V3_ALR_REQS),
        _make_profile(t.Permission.AAA, _V3_AAA_REQS),
    ]


# ── Gap status helpers ─────────────────────────────────────────────────────────

def make_gaps(statuses: dict[str, str]) -> list[t.GapRecord]:
    """Build a full gap list from a status dict.

    Keys not present in statuses default to "open".
    statuses values: "open", "bounded", "closed".
    """
    records = []
    for gid in ALL_GAPS:
        status = statuses.get(gid, "open")
        records.append(t.GapRecord(gap_id=gid, gap_type=gid, status=status))
    return records


# ── ProofContext builder ───────────────────────────────────────────────────────

@dataclass
class CaseInputs:
    """All inputs needed to build a ProofContext for one benchmark case."""
    claim_id: str
    candidate_id: str
    context_id: str
    allowed_use: str = "clinical_alert"
    membership: t.Membership = t.Membership.InClass
    authority_ceiling: t.Permission = t.Permission.AAA
    expiry: Optional[t.Expiry] = None
    gap_statuses: dict[str, str] = field(default_factory=dict)
    tokens: list[t.ProofToken] = field(default_factory=list)
    profile_version: str = "v1"


def build_proof_context(inputs: CaseInputs) -> t.ProofContext:
    """Assemble a ProofContext from CaseInputs."""
    if inputs.profile_version == "v1":
        profiles = build_profiles_v1()
    elif inputs.profile_version == "v2":
        profiles = build_profiles_v2()
    else:
        profiles = build_profiles_v3()
    gaps = make_gaps(inputs.gap_statuses)
    expiry = inputs.expiry if inputs.expiry is not None else t.Expiry.never()

    return t.ProofContext(
        claim_id=inputs.claim_id,
        candidate_id=inputs.candidate_id,
        context_id=inputs.context_id,
        allowed_use=inputs.allowed_use,
        membership=inputs.membership,
        authority_ceiling=inputs.authority_ceiling,
        expiry=expiry,
        gaps=gaps,
        profiles=profiles,
        tokens=inputs.tokens,
        context_fingerprint=inputs.context_id,
    )
