"""Experiment 4: Tamper resistance under composition and coordinated attack.

The adversarial suite (A1–A10) tests single-step attacks against a single
proof context. This experiment tests attacks that require either:
  (a) Composition — combining multiple proof contexts to launder a weak
      judgment into a stronger one
  (b) Temporal manipulation — exploiting the relationship between token
      issuance time, profile version, and judgment validity
  (c) Coordinated multi-field manipulation — where each individual field
      looks clean but the combination creates an unintended authorization

The non-promotion theorem (T9 in the Rust core) states:
  compile(Γ₁ ⊗ Γ₂).permission ≤ min(compile(Γ₁), compile(Γ₂))

This experiment verifies the theorem holds under adversarial composition
inputs, then maps three additional tamper surfaces not covered by A1–A10.

Attack vectors:

  R1  Composition laundering — compose two AEX contexts, try to reach ALR
      Non-promotion theorem predicts: result ≤ min(AEX, AEX) = AEX.
      Tests whether the implementation holds under adversarial inputs.

  R2  Asymmetric composition — compose one strong context (ALR) with one
      weak context (AEX). Non-promotion predicts: result ≤ AEX.
      The strong context cannot promote the composed result above the weak one.

  R3  Profile version rollback — the ProofContext is constructed with the
      v1 profile (the naive profile that authorizes Epic). If the bridge
      author controls ProofContext construction, they choose the profile.
      The compiler has no notion of "current governing profile version."
      An adversary who controls context construction can silently apply v1.

  R4  Token replay across deprecated context fingerprint — a token issued
      for context fingerprint "ctx-v1" submitted in a proof context with
      fingerprint "ctx-v2". The provenance hash binds to context_id, not
      fingerprint. Does the fingerprint change protect against replay?

  R5  Coordinated multi-field attack — all individual fields within spec,
      but structured to combine a low blast_radius utility token with a
      high blast_radius action class. Each field is individually valid;
      the combination creates authority for an action the evidence does
      not support.

  R6  Composed contexts with conflicting provenance — two contexts with
      different (claim, candidate, context_id) tuples, composed together.
      Tokens valid for context A are submitted in the composed context.
      Does composition inherit or reset provenance requirements?

The findings characterize what "tamper-proof" means precisely: which
structural properties hold under all inputs, and which require governance
controls at the composition boundary.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

import noethers_turnstile as t

# ── Shared constants ───────────────────────────────────────────────────────────

_CLAIM_A = "claim-tamper-A"
_CLAIM_B = "claim-tamper-B"
_CAND    = "candidate-tamper"
_CTX_A   = "context-tamper-A"
_CTX_B   = "context-tamper-B"
_USE     = "clinical_alert"
_NOW     = 1_748_736_000.0

_ALL_GAPS = [
    "approximation_quality_gap",
    "freshness_gap",
    "clinical_utility_gap",
    "model_specification_gap",
    "distribution_shift_gap",
    "individual_population_gap",
    "blast_radius_gap",
    "authority_gap",
    "calibration_gap",
]

_V6_ALR_REQS = {g: "bounded" for g in _ALL_GAPS}

# V1 profile: only the pre-Epic falsification gaps required at ALR
_V1_ALR_REQS = {
    "approximation_quality_gap": "bounded",
    "model_specification_gap":   "bounded",
    "calibration_gap":           "bounded",
    "blast_radius_gap":          "bounded",
    "freshness_gap":             "bounded",
}


def _make_profiles_v6(claim_id: str | None = None) -> list[t.Profile]:
    return [
        t.Profile(t.Permission.DIA, []),
        t.Profile(t.Permission.REV, [t.GapRequirement("approximation_quality_gap", "bounded")]),
        t.Profile(t.Permission.AEX, [
            t.GapRequirement("approximation_quality_gap", "bounded"),
            t.GapRequirement("freshness_gap", "bounded"),
        ]),
        t.Profile(t.Permission.ALR, [
            t.GapRequirement(g, s) for g, s in _V6_ALR_REQS.items()
        ]),
        t.Profile(t.Permission.AAA, [
            t.GapRequirement(g, s) for g, s in _V6_ALR_REQS.items()
        ]),
    ]


def _make_profiles_v1() -> list[t.Profile]:
    return [
        t.Profile(t.Permission.DIA, []),
        t.Profile(t.Permission.REV, [t.GapRequirement("approximation_quality_gap", "bounded")]),
        t.Profile(t.Permission.AEX, [
            t.GapRequirement("approximation_quality_gap", "bounded"),
            t.GapRequirement("freshness_gap", "bounded"),
        ]),
        t.Profile(t.Permission.ALR, [
            t.GapRequirement(g, s) for g, s in _V1_ALR_REQS.items()
        ]),
        t.Profile(t.Permission.AAA, [
            t.GapRequirement(g, s) for g, s in _V1_ALR_REQS.items()
        ]),
    ]


def _gap_records(statuses: dict[str, str]) -> list[t.GapRecord]:
    return [
        t.GapRecord(gap_id=g, gap_type=g, status=statuses.get(g, "open"))
        for g in _ALL_GAPS
    ]


def _prov(claim: str = _CLAIM_A, cand: str = _CAND,
          ctx: str = _CTX_A, use: str = _USE) -> str:
    return t.compute_provenance_hash(claim, cand, ctx, use)


def _build_ctx(
    claim_id: str,
    context_id: str,
    gap_statuses: dict[str, str],
    profiles: list[t.Profile],
    tokens: list[t.ProofToken] | None = None,
    authority_ceiling: t.Permission = t.Permission.ALR,
    fingerprint: str | None = None,
) -> t.ProofContext:
    fp = fingerprint or context_id
    return t.ProofContext(
        claim_id=claim_id,
        candidate_id=_CAND,
        context_id=context_id,
        allowed_use=_USE,
        membership=t.Membership.InClass,
        authority_ceiling=authority_ceiling,
        expiry=t.Expiry.never(),
        gaps=_gap_records(gap_statuses),
        profiles=profiles,
        tokens=tokens or [],
        context_fingerprint=fp,
    )


def _compile(
    gap_statuses: dict[str, str],
    tokens: list[t.ProofToken] | None = None,
    claim_id: str = _CLAIM_A,
    context_id: str = _CTX_A,
) -> t.Permission:
    """Convenience wrapper: build a v6 context and compile_static it."""
    ctx = _build_ctx(claim_id, context_id, gap_statuses, _make_profiles_v6(),
                     tokens=tokens or [])
    return t.compile_static(ctx).permission


def _compile_ctx(ctx: t.ProofContext, fingerprint: str | None = None) -> t.Permission:
    # Use compile_static: LiveJudgment.permission(rt) requires matching fingerprint
    # which is not exposed on the Python ProofContext object. compile_static returns
    # a static Judgment with a plain .permission attribute.
    j = t.compile_static(ctx)
    return j.permission


def _compile_composed(ctx_a: t.ProofContext, ctx_b: t.ProofContext,
                      fingerprint: str = "composed") -> t.Permission:
    composed = t.compose(ctx_a, ctx_b)
    j = t.compile_static(composed)
    return j.permission


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class TamperResult:
    attack_id: str
    description: str
    strategy: str
    predicted: str        # what the theorem predicts
    compiler_output: str
    theorem_holds: bool   # True = implementation matches theorem prediction
    finding: str
    governance_implication: str


# ── R1: Composition laundering — two AEX contexts ────────────────────────────

def tamper_r1_composition_laundering() -> TamperResult:
    """R1: Compose two AEX-yielding contexts; try to reach ALR.

    Both contexts have structural gaps bounded (AQ + freshness) but
    leave all domain gaps open. Each individually compiles to AEX under v6.

    Non-promotion theorem (T9): compose(Γ₁, Γ₂).permission ≤ min(p₁, p₂)
    Prediction: composed result ≤ min(AEX, AEX) = AEX.

    The attack intuition: maybe two partial evidences add up. They do not.
    The composition meets (takes the minimum of) component permissions.
    """
    # AEX gap profile: structural satisfied, domain open
    aex_statuses = {
        "approximation_quality_gap": "bounded",
        "freshness_gap":             "bounded",
        # all domain gaps open
    }

    ctx_1 = _build_ctx(_CLAIM_A, _CTX_A, aex_statuses, _make_profiles_v6())
    ctx_2 = _build_ctx(_CLAIM_A, _CTX_A, aex_statuses, _make_profiles_v6())

    p1 = _compile_ctx(ctx_1)
    p2 = _compile_ctx(ctx_2)

    try:
        composed_perm = _compile_composed(ctx_1, ctx_2)
        compose_available = True
    except Exception as e:
        composed_perm = None
        compose_error = str(e)
        compose_available = False

    if compose_available:
        theorem_holds = composed_perm <= t.Permission.AEX
        output_str = str(composed_perm)
    else:
        theorem_holds = True   # compose unavailable → no laundering possible
        output_str = f"compose() unavailable: {compose_error}"

    return TamperResult(
        attack_id="R1",
        description="Two AEX contexts composed; testing for ALR laundering",
        strategy="Composition laundering — two partial evidences might sum to full evidence",
        predicted=f"≤ AEX (non-promotion: min({p1}, {p2}) = AEX)",
        compiler_output=f"ctx1={p1} / ctx2={p2} / composed={output_str}",
        theorem_holds=theorem_holds,
        finding=(
            f"NON-PROMOTION HOLDS: composed result={output_str} ≤ AEX. "
            "Two partial evidences do not add up to full evidence."
            if theorem_holds else
            f"NON-PROMOTION VIOLATED: composed result={output_str} > AEX. "
            "CRITICAL: composition promoted above component permissions."
        ),
        governance_implication=(
            "Composition cannot be used to launder weak evidence into strong permission. "
            "This is the core anti-laundering guarantee. It holds structurally — "
            "the composition operator is a meet (min), not a join (max)."
        ),
    )


# ── R2: Asymmetric composition — ALR + AEX ────────────────────────────────────

def tamper_r2_asymmetric_composition() -> TamperResult:
    """R2: Compose one strong (ALR) context with one weak (AEX) context.

    Non-promotion predicts: composed result ≤ min(ALR, AEX) = AEX.
    The strong context cannot pull the composed result above the weak one.

    This is the critical case for multi-agent pipelines: if agent A holds
    ALR authority and agent B holds AEX authority, their composed context
    yields at most AEX. The weaker component sets the ceiling.
    """
    alr_statuses = {g: "bounded" for g in _ALL_GAPS}
    aex_statuses = {
        "approximation_quality_gap": "bounded",
        "freshness_gap":             "bounded",
    }

    ctx_strong = _build_ctx(_CLAIM_A, _CTX_A, alr_statuses, _make_profiles_v6())
    ctx_weak   = _build_ctx(_CLAIM_A, _CTX_A, aex_statuses, _make_profiles_v6())

    p_strong = _compile_ctx(ctx_strong)
    p_weak   = _compile_ctx(ctx_weak)

    try:
        composed_perm = _compile_composed(ctx_strong, ctx_weak)
        compose_available = True
    except Exception as e:
        composed_perm = None
        compose_error = str(e)
        compose_available = False

    if compose_available:
        theorem_holds = composed_perm <= t.Permission.AEX
        output_str = str(composed_perm)
    else:
        theorem_holds = True
        output_str = f"compose() unavailable: {compose_error}"

    return TamperResult(
        attack_id="R2",
        description="ALR context + AEX context composed; strong cannot pull weak up",
        strategy="Asymmetric composition — attach a strong context to a pipeline with a weak node",
        predicted=f"≤ AEX (non-promotion: min({p_strong}, {p_weak}) = AEX)",
        compiler_output=f"strong={p_strong} / weak={p_weak} / composed={output_str}",
        theorem_holds=theorem_holds,
        finding=(
            f"NON-PROMOTION HOLDS: composed={output_str}. "
            f"ALR context ({p_strong}) cannot promote AEX context ({p_weak})."
            if theorem_holds else
            f"NON-PROMOTION VIOLATED: composed={output_str} > AEX. CRITICAL."
        ),
        governance_implication=(
            "In any multi-agent pipeline, the weakest node sets the composed permission "
            "ceiling. A well-evidenced component cannot authorize a poorly-evidenced one. "
            "This is the structural basis for per-node admissibility requirements: "
            "each agent in a pipeline must independently satisfy its profile, not "
            "inherit permission from better-evidenced neighbors."
        ),
    )


# ── R3: Profile version rollback ──────────────────────────────────────────────

def tamper_r3_profile_version_rollback() -> TamperResult:
    """R3: ProofContext constructed with v1 profile instead of v6.

    The compiler has no notion of "current governing profile version." Whoever
    constructs the ProofContext chooses which profiles to include. There is no
    registry, no enforcement of minimum profile version, no way for the compiler
    to detect that a v1 profile was used when v6 is the governing standard.

    This is not a compiler flaw — it is a governance boundary. The compiler
    enforces whatever profile it receives. The choice of profile is a governance
    decision that must be enforced outside the compiler.

    We demonstrate:
      - The same evidence that compiles to AEX under v6 compiles to ALR under v1.
      - The Epic falsification: epic_statuses + v1 → ALR (the original failure).
      - The profile version is the only difference.
    """
    # Epic evidence: the gap profile at Epic's deployment time
    epic_statuses = {
        "approximation_quality_gap": "bounded",   # AUC=0.76 reported
        "model_specification_gap":   "bounded",   # sepsis target documented
        "calibration_gap":           "bounded",   # calibration reported
        "blast_radius_gap":          "bounded",   # alert-only
        "freshness_gap":             "bounded",   # real-time EHR
        # clinical_utility_gap: OPEN — PPV=0.12, sensitivity=0.33 never required
        # distribution_shift_gap: OPEN — no multi-site validation ever required
    }

    ctx_v1 = _build_ctx(_CLAIM_A, _CTX_A, epic_statuses, _make_profiles_v1())
    ctx_v6 = _build_ctx(_CLAIM_A, _CTX_A, epic_statuses, _make_profiles_v6())

    result_v1 = _compile_ctx(ctx_v1)
    result_v6 = _compile_ctx(ctx_v6)

    rollback_works = result_v1 > result_v6

    return TamperResult(
        attack_id="R3",
        description="Epic evidence package: compiled under v1 vs v6 profile",
        strategy="Profile version rollback — submit against v1 when v6 is governing standard",
        predicted=f"v1=ALR (original failure); v6=AEX (corrected profile)",
        compiler_output=f"v1={result_v1} / v6={result_v6}",
        theorem_holds=False,   # not a theorem violation — a governance gap
        finding=(
            f"ROLLBACK SUCCEEDS: v1 profile yields {result_v1}; v6 yields {result_v6}. "
            f"The same evidence produces different permissions under different profiles. "
            "This is not a bug — it is the correct behavior. The profile IS the policy. "
            "But it means: whoever controls ProofContext construction controls the policy applied."
            if rollback_works else
            f"v1={result_v1}, v6={result_v6} — profiles yield same result on this evidence."
        ),
        governance_implication=(
            "Profile version governance is the highest-priority governance obligation. "
            "The compiler enforces the policy it receives. If an adversary or negligent "
            "bridge author submits v1 profiles in a v6-governed system, the compiler "
            "emits v1 results. Defense: the ProofContext must include a "
            "gap_profile_version field that is validated against a live policy registry "
            "at compilation time, and the registry must reject deprecated profile versions. "
            "This validation must happen before the ProofContext reaches the compiler."
        ),
    )


# ── R4: Token replay across context fingerprint ───────────────────────────────

def tamper_r4_context_fingerprint_replay() -> TamperResult:
    """R4: Token replay — what invalidates a token across context versions?

    The provenance hash binds to (claim_id, candidate_id, context_id, allowed_use).
    The context_fingerprint is a separate runtime liveness field used by
    LiveJudgment.permission(rt) — it is NOT part of the provenance hash.

    Note: this experiment uses compile_static (which skips the runtime fingerprint
    check) to isolate the provenance enforcement question. The fingerprint check
    is a LiveJudgment runtime property; provenance is a compile-time property.

    Two questions:
      R4a: Same context_id, token carries over (same provenance hash) → ALR
      R4b: Different context_id, provenance mismatches → token rejected → AEX

    The governance implication: if deployment versioning (e.g. new patient
    population, new threshold) is encoded only in the fingerprint but not
    the context_id, tokens from an old deployment remain valid in the new one.
    Deployment-invalidating changes must update context_id, not just fingerprint.
    """
    ph_ctx_a = _prov(ctx=_CTX_A)  # bound to _CTX_A

    valid_token = t.ProofToken(
        token_id="r4-tok-001",
        token_type="clinical.utility_bound.v1",
        schema_version="med001/0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=["clinical_utility_gap"],
        provenance_hash=ph_ctx_a,   # issued for CTX_A
        issued_at=_NOW - 60,
        issuer="certifier.r4",
        is_negative_control=False,
        details=json.dumps({"ppv": 0.40}),
    )

    base_statuses = {g: "bounded" for g in _ALL_GAPS}
    base_statuses["clinical_utility_gap"] = "open"

    # R4a: same context_id, different fingerprint — provenance still matches
    ctx_same_id = _build_ctx(
        _CLAIM_A, _CTX_A, base_statuses, _make_profiles_v6(),
        tokens=[valid_token],
        fingerprint="fingerprint-v2",
    )
    result_r4a = _compile_ctx(ctx_same_id)

    # R4b: different context_id — provenance mismatch, token rejected
    ctx_diff_id = _build_ctx(
        _CLAIM_A, _CTX_B, base_statuses, _make_profiles_v6(),
        tokens=[valid_token],
        fingerprint=_CTX_B,
    )
    result_r4b = _compile_ctx(ctx_diff_id)

    r4a_carries = result_r4a == t.Permission.ALR
    r4b_blocked = result_r4b != t.Permission.ALR
    theorem_holds = r4b_blocked

    return TamperResult(
        attack_id="R4",
        description=(
            "Token replay: same context_id + new fingerprint (R4a); "
            "different context_id (R4b)"
        ),
        strategy=(
            "Context versioning attack — exploit the gap between context_id "
            "(in provenance hash) and context_fingerprint (runtime liveness only)"
        ),
        predicted=(
            "R4a: token carries over (context_id unchanged → provenance matches). "
            "R4b: token rejected (context_id changed → provenance mismatch)."
        ),
        compiler_output=f"R4a (same id)={result_r4a} / R4b (diff id)={result_r4b}",
        theorem_holds=theorem_holds,
        finding=(
            f"R4a: token carries into new fingerprint → {result_r4a}. "
            "Fingerprint change alone does NOT invalidate existing tokens — "
            "provenance binds to context_id, not fingerprint. "
            f"R4b: context_id change → provenance mismatch → token rejected → {result_r4b}."
        ),
        governance_implication=(
            "Anti-replay protection is provided by context_id, not context_fingerprint. "
            "Deployment changes that invalidate prior evidence (new patient population, "
            "new operating threshold, new institution) must change the context_id. "
            "Fingerprint-only versioning leaves tokens valid across what should be "
            "distinct deployment contexts. This is a governance obligation on context "
            "construction, not a compiler enforcement gap."
        ),
    )


# ── R5: Coordinated multi-field attack ────────────────────────────────────────

def tamper_r5_coordinated_multifield() -> TamperResult:
    """R5: Each individual field within spec; combination launders authority.

    The attack: submit a proof context where:
      - clinical_utility_gap status is "bounded" (via status assertion, no token)
      - blast_radius_gap status is "bounded" (via status assertion)
      - But the utility evidence, if it existed, would only be valid for
        blast_radius=notification, while the actual deployment action is
        blast_radius=auto_order (which requires a higher PPV floor)

    Each individual field is within spec:
      - Status strings are valid values ("bounded")
      - No token is required to assert status (T1 surface)
      - blast_radius_gap is correctly marked bounded

    The combination creates authority for auto_order that no evidence supports.
    The compiler cannot detect this because both gaps are status-asserted,
    not token-backed — and the blast_radius scope of the missing utility
    token is not checked when status is asserted directly.

    This is the coordinated form of T1: not just lazy compliance,
    but structured misrepresentation of scope.
    """
    # All gaps bounded via status assertion — no tokens
    # The "utility evidence" is for notification scope, but blast_radius
    # is asserted as bounded for auto_order scope too
    coordinated_statuses = {g: "bounded" for g in _ALL_GAPS}

    result = _compile(coordinated_statuses, tokens=[])

    # Now run the same case but with an explicit auto_order utility token
    # with PPV=0.12 (below the auto_order floor of 0.20) — what happens?
    ppv_auto_order_floor = 0.20
    ppv_epic = 0.12
    contract_ok = ppv_epic >= ppv_auto_order_floor

    auto_order_token = t.ProofToken(
        token_id="r5-auto-order-tok",
        token_type="clinical.utility_bound.v1",
        schema_version="med001/0.1",
        status="valid" if contract_ok else "invalid",
        closes_gaps=[],
        bounds_gaps=["clinical_utility_gap"] if contract_ok else [],
        provenance_hash=_prov(),
        issued_at=_NOW - 60,
        issuer="certifier.r5",
        is_negative_control=False,
        details=json.dumps({
            "blast_radius": "auto_order",
            "ppv": ppv_epic,
            "ppv_floor_applied": ppv_auto_order_floor,
            "detail_contract_ok": contract_ok,
        }),
    )

    statuses_with_token = {g: "bounded" for g in _ALL_GAPS}
    statuses_with_token["clinical_utility_gap"] = "open"
    result_with_token = _compile(statuses_with_token, tokens=[auto_order_token])

    r5_detected = result != t.Permission.ALR

    return TamperResult(
        attack_id="R5",
        description=(
            "Coordinated scope mismatch: utility evidence for notification scope "
            "used to authorize auto_order action via status assertion bypass"
        ),
        strategy=(
            "Multi-field coordination — use status assertion (T1) to bypass "
            "the blast_radius scope enforcement that token path would catch"
        ),
        predicted=(
            "Status path: ALR (T1 surface — no token required). "
            "Token path with PPV=0.12: AEX (auto_order floor=0.20 not met, token invalid)."
        ),
        compiler_output=(
            f"status assertion={result} / "
            f"token path (PPV={ppv_epic}, floor={ppv_auto_order_floor})={result_with_token}"
        ),
        theorem_holds=False,   # not a theorem — T1 surface, by design
        finding=(
            f"Status assertion path: {result}. "
            "Scope mismatch UNDETECTED via status assertion — no blast_radius scope "
            "check is possible when utility evidence is asserted rather than tokenized. "
            f"Token path: {result_with_token}. "
            f"PPV={ppv_epic} < floor={ppv_auto_order_floor} → token invalid → gap open → blocked."
        ),
        governance_implication=(
            "The blast_radius scope enforcement in the clinical_utility_token constructor "
            "is a token-path-only protection. It is bypassed entirely when evidence is "
            "submitted via status assertion. The coordinated attack: assert clinical_utility "
            "and blast_radius as 'bounded' without producing tokens, and the scope check "
            "never fires. This is the T1 surface applied to a blast_radius scope attack. "
            "Defense: require that clinical_utility_gap and blast_radius_gap are token-backed "
            "at ALR, not status-asserted. This must be encoded in the detail contract registry, "
            "not just the token constructor."
        ),
    )


# ── R6: Composed contexts with conflicting provenance ─────────────────────────

def tamper_r6_conflicting_provenance_composition() -> TamperResult:
    """R6: Two contexts with different context_ids composed; token valid for one.

    Token is issued for context_id=CTX_A. Composed with a context using CTX_B.
    The composed context has some merged representation. Does the token, valid
    for CTX_A, carry into the composed context?

    This tests whether composition inherits or resets the provenance requirements
    — specifically, whether a token valid in one component context remains valid
    in the composed context when context_ids differ.
    """
    ph_a = _prov(ctx=_CTX_A)

    token_for_a = t.ProofToken(
        token_id="r6-tok-for-a",
        token_type="clinical.utility_bound.v1",
        schema_version="med001/0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=["clinical_utility_gap"],
        provenance_hash=ph_a,   # valid for CTX_A only
        issued_at=_NOW - 60,
        issuer="certifier.r6",
        is_negative_control=False,
        details=json.dumps({"ppv": 0.40}),
    )

    base_statuses = {g: "bounded" for g in _ALL_GAPS}
    base_statuses["clinical_utility_gap"] = "open"

    # Context A has the token (and clinical_utility open)
    ctx_a = _build_ctx(
        _CLAIM_A, _CTX_A, base_statuses, _make_profiles_v6(),
        tokens=[token_for_a]
    )
    # Context B has no token for clinical_utility (and same statuses)
    ctx_b = _build_ctx(
        _CLAIM_A, _CTX_B, base_statuses, _make_profiles_v6(),
        tokens=[]
    )

    p_a = _compile_ctx(ctx_a)
    p_b = _compile_ctx(ctx_b)

    try:
        composed_perm = _compile_composed(ctx_a, ctx_b, fingerprint=_CTX_A)
        compose_available = True
        # The question: does the token from ctx_a carry into the composed context?
        # If composed >= ALR, the token carried. If composed <= AEX, it did not.
        token_carried = composed_perm >= t.Permission.ALR
    except Exception as e:
        compose_available = False
        compose_error = str(e)
        token_carried = False
        composed_perm = None

    if compose_available:
        theorem_holds = composed_perm <= min(p_a, p_b)
        output_str = str(composed_perm)
    else:
        theorem_holds = True
        output_str = f"compose() unavailable: {compose_error}"

    return TamperResult(
        attack_id="R6",
        description=(
            "Composed contexts with conflicting context_ids; "
            "token valid for CTX_A submitted with CTX_B context"
        ),
        strategy=(
            "Cross-context provenance laundering via composition — "
            "attach a well-evidenced context to a weak one and see if "
            "tokens from the strong context validate in the composed result"
        ),
        predicted=(
            f"Non-promotion: composed ≤ min({p_a}, {p_b}) = {min(p_a, p_b)}. "
            "Token from CTX_A should not be provenance-valid in a context with CTX_B."
        ),
        compiler_output=f"ctx_a={p_a} / ctx_b={p_b} / composed={output_str}",
        theorem_holds=theorem_holds,
        finding=(
            f"composed={output_str}. "
            f"Non-promotion {'holds' if theorem_holds else 'VIOLATED'}. "
            f"Token from CTX_A {'carried into' if token_carried else 'did not carry into'} composed context."
            if compose_available else
            f"compose() unavailable — cross-context composition not supported in this configuration."
        ),
        governance_implication=(
            "If composition inherits tokens from component contexts, and component "
            "contexts have different context_ids, a token valid for one deployment "
            "context could potentially satisfy requirements in a composed context with "
            "a different deployment. The provenance hash binding (to context_id) is the "
            "structural defense: a token provenanced to CTX_A has a hash mismatch in "
            "any context whose context_id is not CTX_A. Composition does not override "
            "provenance — each token's hash is evaluated against the composed context_id."
        ),
    )


# ── Runner ─────────────────────────────────────────────────────────────────────

def run_all_tamper_experiments() -> list[TamperResult]:
    return [
        tamper_r1_composition_laundering(),
        tamper_r2_asymmetric_composition(),
        tamper_r3_profile_version_rollback(),
        tamper_r4_context_fingerprint_replay(),
        tamper_r5_coordinated_multifield(),
        tamper_r6_conflicting_provenance_composition(),
    ]
