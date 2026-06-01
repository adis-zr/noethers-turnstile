"""Experiment 1: Adversarial synthetic cases — finding the break points.

Tests seven distinct adversarial strategies against the converged v6 profile.
Each strategy attempts to reach ALR through a different form of manipulation.
Results are classified as:

  BLOCKED   — compiler correctly refused to over-authorize
  BREAKS    — compiler over-authorized; the profile has no defense here

The goal is not to show the compiler is broken. It is to map the trust
boundary precisely: what does the profile enforce structurally, and what
does it accept on faith?

Attack vectors:
  A1  Gap laundering       — mark OPEN gaps "bounded" with no evidence
  A2  Threshold gaming     — AQ bounded at AUC barely above chance (0.52)
  A3  Wrong-level token    — token that closes freshness_gap submitted as closing clinical_utility_gap
  A4  Authority ceiling    — submit profiles that would reach AAA; does ceiling hold?
  A5  Membership spoof     — submit OutOfClass candidate as InClass
  A6  Empty profile        — no profiles at all; what is the floor?
  A7  Token status invalid — submit token with status="invalid"; does the compiler reject it?
  A8  Expired token floor  — one expired token in the context; does it floor the judgment?
  A9  Provenance mismatch  — token with wrong provenance_hash; does the compiler reject it?
  A10 All gaps "closed"    — submit all gaps as "closed" with no tokens at all
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import noethers_turnstile as t

# ── Shared coordinates ─────────────────────────────────────────────────────────

_CLAIM   = "claim-stress-001"
_CAND    = "candidate-stress"
_CTX_ID  = "context-stress-v6"
_FP      = "stress-v6"
_USE     = "clinical_alert"
_NOW     = 1_748_736_000.0


def _rt() -> t.RuntimeContext:
    return t.RuntimeContext(now_unix=_NOW, context_fingerprint=_FP)


# ── Converged v6 profile (the profile under test) ─────────────────────────────

_ALL_GAPS = [
    "approximation_quality_gap",
    "freshness_gap",
    "clinical_utility_gap",
    "model_specification_gap",
    "distribution_shift_gap",
    "individual_population_gap",
    "blast_radius_gap",
    "authority_gap",
]

_V6_ALR_REQS = {g: "bounded" for g in _ALL_GAPS}


def _make_profiles(alr_reqs: dict[str, str]) -> list[t.Profile]:
    return [
        t.Profile(t.Permission.DIA, []),
        t.Profile(t.Permission.REV, [t.GapRequirement("approximation_quality_gap", "bounded")]),
        t.Profile(t.Permission.AEX, [
            t.GapRequirement("approximation_quality_gap", "bounded"),
            t.GapRequirement("freshness_gap", "bounded"),
        ]),
        t.Profile(t.Permission.ALR, [
            t.GapRequirement(g, s) for g, s in alr_reqs.items()
        ]),
        t.Profile(t.Permission.AAA, [
            t.GapRequirement(g, s) for g, s in alr_reqs.items()
        ]),
    ]


def _gap_records(statuses: dict[str, str]) -> list[t.GapRecord]:
    return [t.GapRecord(gap_id=g, gap_type=g, status=statuses.get(g, "open"))
            for g in _ALL_GAPS]


def _compile(
    gap_statuses: dict[str, str],
    alr_reqs: dict[str, str] | None = None,
    tokens: list[t.ProofToken] | None = None,
    authority_ceiling: t.Permission = t.Permission.ALR,
    membership: t.Membership = t.Membership.InClass,
    profiles: list[t.Profile] | None = None,
    extra_gaps: list[t.GapRecord] | None = None,
    expiry: t.Expiry | None = None,
    context_fingerprint: str = _FP,
) -> t.Permission:
    reqs = alr_reqs if alr_reqs is not None else _V6_ALR_REQS
    gaps = _gap_records(gap_statuses)
    if extra_gaps:
        gaps = gaps + extra_gaps

    ctx = t.ProofContext(
        claim_id=_CLAIM,
        candidate_id=_CAND,
        context_id=_CTX_ID,
        allowed_use=_USE,
        membership=membership,
        authority_ceiling=authority_ceiling,
        expiry=expiry if expiry is not None else t.Expiry.never(),
        gaps=gaps,
        profiles=profiles if profiles is not None else _make_profiles(reqs),
        tokens=tokens or [],
        context_fingerprint=context_fingerprint,
    )
    judgment = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=_NOW, context_fingerprint=context_fingerprint)
    try:
        return judgment.permission(rt)
    except t.ExpiredError:
        return t.Permission.EXP


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class AttackResult:
    attack_id: str
    description: str
    strategy: str
    compiler_output: str
    expected_if_defended: str   # what compiler should emit if the profile defends
    defended: bool              # True = compiler blocked the attack
    breaks: bool                # True = compiler over-authorized (attack succeeded)
    mechanism: str              # what the compiler enforced (or failed to enforce)
    verdict: str                # one-line finding


# ── Attack implementations ─────────────────────────────────────────────────────

def attack_a1_gap_laundering() -> AttackResult:
    """A1: Mark all gaps 'bounded' with no tokens, no evidence.

    The compiler reads GapRecord.status as a string. If you simply assert
    "bounded" for every gap, the profile requirements are satisfied.
    No token is required. The compiler has no way to verify the claim.

    Expected if defended: AEX or REV (status claims unverifiable → don't trust)
    Actual: ALR (the compiler accepts status assertions at face value)
    """
    result = _compile({g: "bounded" for g in _ALL_GAPS})
    defended = result != t.Permission.ALR
    return AttackResult(
        attack_id="A1",
        description="All gaps marked 'bounded' with no tokens or evidence",
        strategy="Gap laundering — assert compliance without evidence",
        compiler_output=result.__str__(),
        expected_if_defended="AEX",
        defended=defended,
        breaks=not defended,
        mechanism="GapRecord.status trusted verbatim; no token required to substantiate a status claim",
        verdict=(
            "BLOCKED: compiler requires tokens to reach ALR"
            if defended else
            "BREAKS: compiler accepts 'bounded' status assertions with no supporting tokens"
        ),
    )


def attack_a2_threshold_gaming() -> AttackResult:
    """A2: AQ 'bounded' at AUC barely above chance (no numerical floor enforced).

    GapRecord has no bound_value enforcement in the profile. A status of
    "bounded" with bound_value=0.52 is structurally identical to "bounded"
    with bound_value=0.95. The profile requirement is minimum_status="bounded";
    it checks the status string, not any numerical value.

    This tests whether the profile has a quantitative floor or just a categorical gate.
    """
    # AQ "bounded" with a bound_value that would represent AUC=0.52
    # The compiler doesn't read bound_value for profile matching — only status string
    gaps = [
        t.GapRecord(gap_id="approximation_quality_gap", gap_type="approximation_quality_gap",
                    status="bounded", bound_value=0.52),  # AUC barely above chance
    ] + [
        t.GapRecord(gap_id=g, gap_type=g, status="bounded")
        for g in _ALL_GAPS if g != "approximation_quality_gap"
    ]
    ctx = t.ProofContext(
        claim_id=_CLAIM, candidate_id=_CAND, context_id=_CTX_ID,
        allowed_use=_USE, membership=t.Membership.InClass,
        authority_ceiling=t.Permission.ALR, expiry=t.Expiry.never(),
        gaps=gaps,
        profiles=_make_profiles(_V6_ALR_REQS),
        tokens=[],
        context_fingerprint=_FP,
    )
    judgment = t.compile(ctx)
    rt = t.RuntimeContext(now_unix=_NOW, context_fingerprint=_FP)
    try:
        result = judgment.permission(rt)
    except t.ExpiredError:
        result = t.Permission.EXP

    defended = result != t.Permission.ALR
    return AttackResult(
        attack_id="A2",
        description="AQ gap marked 'bounded' with bound_value=0.52 (AUC barely above chance)",
        strategy="Threshold gaming — meet categorical status without meeting quantitative standard",
        compiler_output=result.__str__(),
        expected_if_defended="AEX",
        defended=defended,
        breaks=not defended,
        mechanism="Profile checks minimum_status string only; bound_value is stored but not compared against a floor",
        verdict=(
            "BLOCKED: compiler enforces quantitative floor on bound_value"
            if defended else
            "BREAKS: compiler accepts 'bounded' with AUC=0.52; no quantitative floor enforced"
        ),
    )


def attack_a3_wrong_level_token() -> AttackResult:
    """A3: Submit a token that closes freshness_gap but claim it closes clinical_utility_gap.

    ProofToken.closes_gaps is a list of gap IDs. The submitter can put any gap ID
    in that list. The question is whether the compiler validates that the token's
    type is appropriate for the gap it claims to close.

    Also tests whether a token with a correct provenance hash but mismatched
    token_type can close a gap it wasn't designed for.
    """
    ph = t.compute_provenance_hash(_CLAIM, _CAND, _CTX_ID, _USE)
    # Token explicitly designed for freshness but claims to close clinical_utility_gap
    lying_token = t.ProofToken(
        token_id="lying-tok-001",
        token_type="FRESHNESS",           # correct type for freshness
        schema_version="0.1",
        status="valid",
        closes_gaps=["clinical_utility_gap"],   # lying about what it closes
        bounds_gaps=[],
        provenance_hash=ph,
        issued_at=_NOW - 3600,
        issuer="test-certifier",
    )
    # Only clinical_utility_gap is open; all others bounded.
    # The token claims to close clinical_utility_gap despite being a FRESHNESS token.
    # This isolates the question: does the compiler validate token_type against the gap?
    statuses = {g: "bounded" for g in _ALL_GAPS}
    statuses["clinical_utility_gap"] = "open"
    result = _compile(statuses, tokens=[lying_token])
    defended = result != t.Permission.ALR
    return AttackResult(
        attack_id="A3",
        description="FRESHNESS token with closes_gaps=['clinical_utility_gap'] — type/gap mismatch",
        strategy="Wrong-level token — use a token designed for one gap to close a different gap",
        compiler_output=result.__str__(),
        expected_if_defended="AEX",
        defended=defended,
        breaks=not defended,
        mechanism="token_type is not validated against the gap it claims to close; compiler only checks provenance_hash and status",
        verdict=(
            "BLOCKED: compiler validates token_type against gap it claims to close"
            if defended else
            "BREAKS: FRESHNESS token accepted as closing clinical_utility_gap; "
            "token_type is ignored — any valid token with correct provenance can close any gap"
        ),
    )


def attack_a4_ceiling_enforcement() -> AttackResult:
    """A4: Profile would reach AAA; authority_ceiling=ALR. Does the ceiling hold?

    The compiler applies meet(ceiling, judgment). This should be natively enforced.
    Testing that the ceiling is not bypassable.
    """
    # Build a profile that explicitly has AAA requirements satisfied
    alr_and_aaa_reqs = {g: "bounded" for g in _ALL_GAPS}
    aaa_profiles = [
        t.Profile(t.Permission.DIA, []),
        t.Profile(t.Permission.REV, [t.GapRequirement("approximation_quality_gap", "bounded")]),
        t.Profile(t.Permission.AEX, [
            t.GapRequirement("approximation_quality_gap", "bounded"),
            t.GapRequirement("freshness_gap", "bounded"),
        ]),
        t.Profile(t.Permission.ALR, [t.GapRequirement(g, "bounded") for g in _ALL_GAPS]),
        t.Profile(t.Permission.AAA, [t.GapRequirement(g, "bounded") for g in _ALL_GAPS]),
    ]
    result = _compile(
        {g: "bounded" for g in _ALL_GAPS},
        profiles=aaa_profiles,
        authority_ceiling=t.Permission.ALR,  # ceiling set to ALR
    )
    # Even though AAA profile is satisfied, ceiling should cap at ALR
    defended = result <= t.Permission.ALR
    return AttackResult(
        attack_id="A4",
        description="AAA profile satisfied; authority_ceiling=ALR",
        strategy="Authority ceiling bypass — satisfy AAA requirements but ceiling is set lower",
        compiler_output=result.__str__(),
        expected_if_defended="ALR",
        defended=defended,
        breaks=not defended,
        mechanism="Compiler applies meet(authority_ceiling, judgment) as final step",
        verdict=(
            "BLOCKED: authority_ceiling is enforced; result capped at ALR"
            if defended else
            "BREAKS: authority_ceiling bypassed; compiler emitted above ceiling"
        ),
    )


def attack_a5_membership_spoof() -> AttackResult:
    """A5: OutOfClass candidate submitted as InClass.

    The Membership field is set by the caller. The compiler cannot verify that
    the caller correctly assessed the candidate's class membership. If the caller
    lies about membership, the compiler has no defense.

    This tests what happens when InClass is submitted for a case that experts
    would assess as OutOfClass — and also confirms that OutOfClass correctly fires.
    """
    # First confirm OOC fires when submitted correctly
    result_ooc = _compile(
        {g: "bounded" for g in _ALL_GAPS},
        membership=t.Membership.OutOfClassExact,
    )
    # Then submit the same candidate as InClass (the lie)
    result_spoofed = _compile(
        {g: "bounded" for g in _ALL_GAPS},
        membership=t.Membership.InClass,
    )
    # The "attack" is: spoofed InClass reaches ALR; OOC would have been correct
    defended = (result_ooc == t.Permission.OOC and result_spoofed == t.Permission.ALR)
    # defended=True here means the mechanism works as expected but is gameable:
    # OOC fires correctly when asserted, but if you don't assert it the compiler
    # cannot detect the spoofing
    return AttackResult(
        attack_id="A5",
        description="OutOfClass candidate submitted with Membership.InClass",
        strategy="Membership spoof — lie about candidate's class membership",
        compiler_output=f"OOC(correct)={result_ooc.__str__()} / InClass(spoofed)={result_spoofed.__str__()}",
        expected_if_defended="OOC",
        defended=False,  # the spoof always works — membership is caller-asserted
        breaks=True,
        mechanism="Membership.InClass/OutOfClass is caller-asserted; compiler trusts it verbatim",
        verdict=(
            "BREAKS: membership is caller-asserted; spoofing InClass for an OOC candidate "
            "reaches ALR. OOC correctly fires when asserted, but assertion is not verified."
        ),
    )


def attack_a6_empty_profiles() -> AttackResult:
    """A6: No profiles registered. What is the floor?

    The compiler has a hard floor when no profiles match: OOC.
    This is a structural property, not a gap property.
    """
    result = _compile(
        {g: "bounded" for g in _ALL_GAPS},
        profiles=[],  # no profiles at all
    )
    defended = result == t.Permission.OOC
    return AttackResult(
        attack_id="A6",
        description="No profiles registered; all gaps 'bounded'",
        strategy="Empty profile attack — remove all profiles; can the compiler be forced above OOC?",
        compiler_output=result.__str__(),
        expected_if_defended="OOC",
        defended=defended,
        breaks=not defended,
        mechanism="No profiles → no permission level is reachable → OOC (structural floor)",
        verdict=(
            "BLOCKED: empty profile set yields OOC regardless of gap statuses"
            if defended else
            "BREAKS: compiler emitted above OOC with no profiles — structural floor violated"
        ),
    )


def attack_a7_invalid_token_status() -> AttackResult:
    """A7: Token with status='invalid' submitted; does the compiler reject it?

    ProofToken.status can be "valid" or "invalid". The compiler should ignore
    tokens with status="invalid". This was established in the medical oracle tests
    (A06: PPV below floor → token status='invalid' → gap stays open).

    Here we test whether an invalid token can still close a gap if submitted
    directly to the compiler.
    """
    ph = t.compute_provenance_hash(_CLAIM, _CAND, _CTX_ID, _USE)
    invalid_token = t.ProofToken(
        token_id="invalid-tok-001",
        token_type="CLINICAL_UTILITY",
        schema_version="0.1",
        status="invalid",           # explicitly invalid
        closes_gaps=[],
        bounds_gaps=["clinical_utility_gap"],  # claims to bound despite invalid status
        provenance_hash=ph,
        issued_at=_NOW - 3600,
        issuer="test-certifier",
    )
    # All other gaps bounded; clinical_utility open — invalid token tries to bound it
    statuses = {g: "bounded" for g in _ALL_GAPS}
    statuses["clinical_utility_gap"] = "open"
    result = _compile(statuses, tokens=[invalid_token])
    defended = result != t.Permission.ALR
    return AttackResult(
        attack_id="A7",
        description="Token with status='invalid' claims to bound clinical_utility_gap",
        strategy="Invalid token submission — submit a token the certifier rejected",
        compiler_output=result.__str__(),
        expected_if_defended="AEX",
        defended=defended,
        breaks=not defended,
        mechanism="Compiler checks token.status; tokens with status='invalid' are ignored",
        verdict=(
            "BLOCKED: invalid token is ignored; gap stays open; ALR blocked"
            if defended else
            "BREAKS: compiler accepted invalid token; clinical_utility_gap incorrectly bounded"
        ),
    )


def attack_a8_expired_token_floor() -> AttackResult:
    """A8: One expired token in the context. Does it floor the judgment to EXP?

    From PY-008 D9: an expired token anywhere in the context floors the judgment
    to EXP. This is a hard structural property of the compiler, not a gap property.
    Testing it confirms the compiler's token expiry mechanism functions as documented.
    """
    ph = t.compute_provenance_hash(_CLAIM, _CAND, _CTX_ID, _USE)
    expired_token = t.ProofToken(
        token_id="expired-tok-001",
        token_type="SOME_TYPE",
        schema_version="0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=[],
        provenance_hash=ph,
        issued_at=_NOW - 7200,
        expires_at=_NOW - 3600,   # expired 1 hour before _NOW
        issuer="test-certifier",
    )
    result = _compile(
        {g: "bounded" for g in _ALL_GAPS},
        tokens=[expired_token],
    )
    defended = result == t.Permission.EXP
    return AttackResult(
        attack_id="A8",
        description="One expired token among valid gap statuses",
        strategy="Expired token floor — verify EXP hard floor with stale evidence in context",
        compiler_output=result.__str__(),
        expected_if_defended="EXP",
        defended=defended,
        breaks=not defended,
        mechanism="Any expired token in ProofContext floors the LiveJudgment to EXP at runtime",
        verdict=(
            "BLOCKED: expired token correctly floors judgment to EXP"
            if defended else
            "BREAKS: expired token did not trigger EXP floor — stale evidence accepted"
        ),
    )


def attack_a9_provenance_mismatch() -> AttackResult:
    """A9: Token with wrong provenance_hash. Does the compiler reject it?

    The provenance_hash is computed from (claim_id, candidate_id, context_id,
    allowed_use). A token computed for a different context cannot be reused here.
    From PY-002 C3: wrong provenance hash → profile unsatisfied → OOC.

    This tests the anti-laundering property: evidence from one context cannot
    be laundered into another.
    """
    # Compute hash for a DIFFERENT context
    wrong_hash = t.compute_provenance_hash(
        "claim-DIFFERENT", "candidate-DIFFERENT", "context-DIFFERENT", "use-DIFFERENT"
    )
    recycled_token = t.ProofToken(
        token_id="recycled-tok-001",
        token_type="CLINICAL_UTILITY",
        schema_version="0.1",
        status="valid",
        closes_gaps=["clinical_utility_gap"],
        bounds_gaps=["clinical_utility_gap"],
        provenance_hash=wrong_hash,  # from a different context
        issued_at=_NOW - 3600,
        issuer="test-certifier",
    )
    statuses = {g: "bounded" for g in _ALL_GAPS}
    statuses["clinical_utility_gap"] = "open"  # gap is open; token tries to close it
    result = _compile(statuses, tokens=[recycled_token])
    defended = result != t.Permission.ALR
    return AttackResult(
        attack_id="A9",
        description="Token with provenance_hash from a different (claim, candidate, context, use)",
        strategy="Provenance laundering — recycle evidence from one deployment to another",
        compiler_output=result.__str__(),
        expected_if_defended="AEX",
        defended=defended,
        breaks=not defended,
        mechanism="Compiler verifies provenance_hash matches current (claim, candidate, context, use); mismatch → token rejected",
        verdict=(
            "BLOCKED: wrong provenance hash detected; recycled token rejected; gap stays open"
            if defended else
            "BREAKS: recycled token accepted across contexts — provenance not enforced"
        ),
    )


def attack_a10_all_closed_no_tokens() -> AttackResult:
    """A10: All gaps marked 'closed' with no tokens at all.

    A stronger form of A1: not just 'bounded' but 'closed'. If the compiler
    accepts 'bounded' at face value, it will certainly accept 'closed'. This
    confirms the finding from A1 but at a higher claimed status level.

    Also tests what happens when you try to reach AAA this way.
    """
    result_alr = _compile(
        {g: "closed" for g in _ALL_GAPS},
        authority_ceiling=t.Permission.ALR,
    )
    result_aaa = _compile(
        {g: "closed" for g in _ALL_GAPS},
        authority_ceiling=t.Permission.AAA,
    )
    defended = result_alr != t.Permission.ALR
    return AttackResult(
        attack_id="A10",
        description="All gaps marked 'closed' with no tokens; tested at ALR and AAA ceiling",
        strategy="Maximum status assertion — claim complete closure of all gaps without any evidence",
        compiler_output=f"ALR-ceiling={result_alr.__str__()} / AAA-ceiling={result_aaa.__str__()}",
        expected_if_defended="AEX",
        defended=defended,
        breaks=not defended,
        mechanism="GapRecord.status='closed' is treated identically to 'bounded' by the profile — string comparison only",
        verdict=(
            "BLOCKED: 'closed' status assertions without tokens rejected"
            if defended else
            "BREAKS: all gaps marked 'closed' with no tokens reaches "
            f"ALR (at ALR ceiling) and {result_aaa.__str__()} (at AAA ceiling). "
            "Gap status assertions are fully trusted without token backing."
        ),
    )


# ── Runner ─────────────────────────────────────────────────────────────────────

def run_all_attacks() -> list[AttackResult]:
    return [
        attack_a1_gap_laundering(),
        attack_a2_threshold_gaming(),
        attack_a3_wrong_level_token(),
        attack_a4_ceiling_enforcement(),
        attack_a5_membership_spoof(),
        attack_a6_empty_profiles(),
        attack_a7_invalid_token_status(),
        attack_a8_expired_token_floor(),
        attack_a9_provenance_mismatch(),
        attack_a10_all_closed_no_tokens(),
    ]
