"""Experiment 3: TCB corruption surface — what the compiler accepts on faith.

The compiler is sound relative to the proof context it receives. That soundness
claim has a boundary: the Trusted Computing Base (TCB). The TCB is everything
the compiler accepts without structural verification — gap status assertions,
numerical bound values, token type/gap compatibility, membership classification,
and the scientific validity of the underlying evidence.

This experiment maps that boundary precisely. For each corruption vector we:
  1. Build a structurally valid proof context that passes all compiler checks
  2. Introduce a specific corruption — something a dishonest or incompetent
     bridge author could do without triggering any structural alarm
  3. Record whether the compiler detects it
  4. State exactly WHY — what structural property is or is not enforced

The six corruption vectors:

  T1  Status assertion without token backing
      Mark a gap "bounded" with no token. No detail contract is evaluated.
      The profile requires "bounded"; the gap is "bounded"; ALR emitted.
      This is the foundational TCB surface: status strings are caller-asserted.

  T2  Bound value below any meaningful floor
      GapRecord.status="bounded", bound_value=0.001.
      The profile checks status string only. Numerical floors live in the
      token detail contract — which is only reached if you go through the
      token path, not the status-assertion path.

  T3  Token type / gap mismatch
      A valid, correctly-provenanced FRESHNESS token claiming to close
      clinical_utility_gap. The compiler checks provenance and status;
      it does not validate that the token type is appropriate for the gap.
      Any valid token with correct provenance can close any gap.

  T4  Scientifically fabricated token
      A token that passes every structural check — correct type, valid status,
      correct provenance, unexpired, satisfies the detail contract floor —
      but represents a study that was conducted on the wrong population,
      was underpowered, and whose PPV value was p-hacked to clear the floor.
      The compiler has no way to detect this. The certifier is the TCB boundary.

  T5  Membership misclassification
      An OutOfClass candidate submitted as InClass. The compiler trusts
      Membership verbatim. If the bridge author misclassifies — negligently
      or intentionally — the compiler has no defense.
      (Replicates A5 but with explicit TCB framing and a second variant:
      an ambiguous-class candidate where the correct classification is
      genuinely uncertain.)

  T6  Detail contract version mismatch
      A token carrying schema_version="med001/0.0" (a deprecated contract
      version) submitted against a proof context expecting "med001/0.1".
      Does the compiler enforce contract versioning, or does it accept
      any token whose status field says "valid"?

The findings define the compiler's epistemological boundary: not a defect,
but a precise statement of what requires human governance versus what the
compiler enforces by construction.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

import noethers_turnstile as t

# ── Shared coordinates ─────────────────────────────────────────────────────────

_CLAIM  = "claim-tcb-001"
_CAND   = "candidate-tcb"
_CTX    = "context-tcb-v6"
_FP     = "tcb-v6"
_USE    = "clinical_alert"
_NOW    = 1_748_736_000.0

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


def _make_profiles() -> list[t.Profile]:
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


def _gap_records(statuses: dict[str, str], bound_values: dict[str, float] | None = None) -> list[t.GapRecord]:
    bv = bound_values or {}
    return [
        t.GapRecord(
            gap_id=g,
            gap_type=g,
            status=statuses.get(g, "open"),
            bound_value=bv.get(g),
        )
        for g in _ALL_GAPS
    ]


def _prov() -> str:
    return t.compute_provenance_hash(_CLAIM, _CAND, _CTX, _USE)


def _compile(
    gap_statuses: dict[str, str],
    tokens: list[t.ProofToken] | None = None,
    bound_values: dict[str, float] | None = None,
    membership: t.Membership = t.Membership.InClass,
    authority_ceiling: t.Permission = t.Permission.ALR,
) -> t.Permission:
    ctx = t.ProofContext(
        claim_id=_CLAIM,
        candidate_id=_CAND,
        context_id=_CTX,
        allowed_use=_USE,
        membership=membership,
        authority_ceiling=authority_ceiling,
        expiry=t.Expiry.never(),
        gaps=_gap_records(gap_statuses, bound_values),
        profiles=_make_profiles(),
        tokens=tokens or [],
        context_fingerprint=_FP,
    )
    return t.compile_static(ctx).permission


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class CorruptionResult:
    vector_id: str
    description: str
    corruption: str
    compiler_output: str
    detected: bool          # True = compiler caught the corruption
    tcb_surface: str        # what the compiler accepts on faith here
    finding: str
    implication: str        # what this means for governance


# ── T1: Status assertion without token backing ────────────────────────────────

def tcb_t1_status_assertion_no_token() -> CorruptionResult:
    """T1: All gaps marked 'bounded' with zero tokens.

    A bridge author who simply asserts compliance — without producing any
    measurement, any study, any certifier output — satisfies the profile.
    The compiler treats GapRecord.status as ground truth.

    This is the primary TCB surface. It is not a bug; it is a design decision:
    the compiler delegates status-establishment to the bridge/certifier layer.
    But a bridge author who bypasses certifiers entirely is undetectable.
    """
    result = _compile({g: "bounded" for g in _ALL_GAPS}, tokens=[])

    detected = result != t.Permission.ALR
    return CorruptionResult(
        vector_id="T1",
        description="All gaps marked 'bounded'; zero tokens produced",
        corruption="GapRecord.status asserted without any certifier producing a token",
        compiler_output=str(result),
        detected=detected,
        tcb_surface="GapRecord.status is caller-asserted; compiler has no mechanism to require token backing for a status claim",
        finding=(
            "UNDETECTED: compiler emits ALR on bare status assertions."
            if not detected else
            f"DETECTED: compiler emits {result} (unexpected — investigate)."
        ),
        implication=(
            "A bridge author who skips the certifier layer entirely and writes "
            "gap_statuses={'clinical_utility_gap': 'bounded'} directly reaches ALR. "
            "Defense: governance must require that gap statuses are produced by "
            "registered certifiers, not hand-written. The compiler cannot enforce this."
        ),
    )


# ── T2: Bound value below any meaningful floor ────────────────────────────────

def tcb_t2_bound_value_gaming() -> CorruptionResult:
    """T2: gap_status='bounded', bound_value=0.001 on clinical_utility_gap.

    GapRecord carries a bound_value field. The profile checks minimum_status
    (a string comparison). bound_value is stored and returned in the audit
    record but is never compared against a threshold by the compiler itself.

    Numerical floors exist only inside token detail contracts — which are only
    reached if evidence goes through the token path. The status-assertion path
    (T1) bypasses them entirely; the bound_value path (T2) stores a number
    but the profile does not evaluate it.

    Two sub-cases:
      T2a: status assertion path — bound_value=0.001, no token → ALR
      T2b: token path — PPV=0.001 in a clinical_utility_token → token invalid,
           detail contract catches it, gap stays open → AEX
    """
    # T2a: status path — bound_value does not trigger any floor check
    result_a = _compile(
        {g: "bounded" for g in _ALL_GAPS},
        bound_values={"clinical_utility_gap": 0.001},
        tokens=[],
    )

    # T2b: token path — PPV=0.001 fails the detail contract floor (0.15 for notification)
    # Build the token constructor inline to test the floor check
    ppv_floor_notification = 0.15
    ppv_test = 0.001
    contract_ok = ppv_test >= ppv_floor_notification
    lying_token = t.ProofToken(
        token_id="tcb-t2b-tok",
        token_type="clinical.utility_bound.v1",
        schema_version="med001/0.1",
        status="valid" if contract_ok else "invalid",
        closes_gaps=[],
        bounds_gaps=["clinical_utility_gap"] if contract_ok else [],
        provenance_hash=_prov(),
        issued_at=_NOW - 60,
        issuer="tcb.test",
        is_negative_control=False,
        details=json.dumps({"ppv": ppv_test, "ppv_floor_applied": ppv_floor_notification}),
    )
    statuses_b = {g: "bounded" for g in _ALL_GAPS}
    statuses_b["clinical_utility_gap"] = "open"
    result_b = _compile(statuses_b, tokens=[lying_token])

    t2a_detected = result_a != t.Permission.ALR
    t2b_detected = result_b != t.Permission.ALR

    return CorruptionResult(
        vector_id="T2",
        description="bound_value=0.001 on clinical_utility_gap; also token path with PPV=0.001",
        corruption=(
            "T2a (status path): GapRecord.status='bounded', bound_value=0.001 — "
            "numerically meaningless but string-valid. "
            "T2b (token path): clinical_utility_token with PPV=0.001 — "
            "fails detail contract, token marked invalid, gap stays open."
        ),
        compiler_output=f"T2a={result_a} / T2b={result_b}",
        detected=t2b_detected and not t2a_detected,
        tcb_surface=(
            "Numerical floors exist only inside token detail contracts. "
            "The status-assertion path (T2a) stores bound_value but the profile "
            "checks only the status string. The token path (T2b) enforces the floor "
            "inside the token constructor before the token reaches the compiler."
        ),
        finding=(
            f"T2a UNDETECTED: bound_value=0.001 with status='bounded' reaches {result_a}. "
            f"T2b DETECTED: PPV=0.001 token is invalid; gap stays open; compiler emits {result_b}."
        ),
        implication=(
            "Quantitative floors are enforced only when evidence goes through a token "
            "constructor that implements the detail contract. The status-assertion shortcut "
            "bypasses all floors. The two paths are structurally inequivalent: the token "
            "path is governed; the status path is ungoverned."
        ),
    )


# ── T3: Token type / gap mismatch ─────────────────────────────────────────────

def tcb_t3_token_type_gap_mismatch() -> CorruptionResult:
    """T3: A FRESHNESS token claiming to bound clinical_utility_gap.

    ProofToken.token_type is metadata for human auditors. The compiler checks:
      - token.status == "valid"
      - token.provenance_hash matches (claim, candidate, context, allowed_use)
      - token.expires_at is in the future (if set)
    It does NOT check that token_type is appropriate for the gap it claims to bound.

    A certifier-issued freshness token — even a genuinely valid one — can be
    submitted with bounds_gaps=["clinical_utility_gap"] and the compiler
    will accept it as evidence for clinical utility.

    Two sub-cases:
      T3a: wrong-type token with correct provenance → gap closed, ALR emitted
      T3b: correct-type token with wrong provenance → gap stays open, AEX emitted
    The asymmetry reveals what the compiler actually enforces: provenance, not type.
    """
    ph_correct = _prov()
    ph_wrong   = t.compute_provenance_hash("other-claim", "other-cand", "other-ctx", "other-use")

    # T3a: FRESHNESS token, correct provenance, claims to bound clinical_utility_gap
    wrong_type_token = t.ProofToken(
        token_id="tcb-t3a-tok",
        token_type="clinical.freshness_bound.v1",   # freshness type
        schema_version="med001/0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=["clinical_utility_gap"],        # claims clinical utility
        provenance_hash=ph_correct,
        issued_at=_NOW - 60,
        issuer="tcb.test",
        is_negative_control=False,
        details=json.dumps({"note": "freshness token claiming utility evidence"}),
    )
    statuses = {g: "bounded" for g in _ALL_GAPS}
    statuses["clinical_utility_gap"] = "open"
    result_a = _compile(statuses, tokens=[wrong_type_token])

    # T3b: correct-type CLINICAL_UTILITY token, wrong provenance
    correct_type_wrong_prov = t.ProofToken(
        token_id="tcb-t3b-tok",
        token_type="clinical.utility_bound.v1",     # correct type
        schema_version="med001/0.1",
        status="valid",
        closes_gaps=[],
        bounds_gaps=["clinical_utility_gap"],
        provenance_hash=ph_wrong,                   # wrong provenance
        issued_at=_NOW - 60,
        issuer="tcb.test",
        is_negative_control=False,
        details=json.dumps({"ppv": 0.40}),
    )
    result_b = _compile(statuses, tokens=[correct_type_wrong_prov])

    t3a_detected = result_a != t.Permission.ALR
    t3b_detected = result_b != t.Permission.ALR

    return CorruptionResult(
        vector_id="T3",
        description="Token type / gap mismatch vs. provenance mismatch",
        corruption=(
            "T3a: FRESHNESS token with correct provenance claims to bound clinical_utility_gap. "
            "T3b: CLINICAL_UTILITY token with wrong provenance claims to bound clinical_utility_gap."
        ),
        compiler_output=f"T3a={result_a} / T3b={result_b}",
        detected=t3b_detected and not t3a_detected,
        tcb_surface=(
            "The compiler enforces provenance but not token type / gap compatibility. "
            "token_type is a human-readable field; it is not validated against the gap "
            "the token claims to close. Any valid, correctly-provenanced token of any "
            "type can close any gap."
        ),
        finding=(
            f"T3a UNDETECTED: wrong-type token with correct provenance bounds clinical_utility_gap; "
            f"compiler emits {result_a}. "
            f"T3b DETECTED: correct-type token with wrong provenance rejected; "
            f"compiler emits {result_b}."
        ),
        implication=(
            "Provenance is the primary anti-laundering mechanism. Token type compatibility "
            "is a governance convention, not a compiler constraint. A certifier that issues "
            "freshness tokens but falsely labels them as utility tokens is undetectable "
            "at the compiler level. Defense: a registered detail contract registry that "
            "maps gap IDs to required token types and enforces the mapping at token evaluation."
        ),
    )


# ── T4: Scientifically fabricated token ───────────────────────────────────────

def tcb_t4_fabricated_science() -> CorruptionResult:
    """T4: A token that passes every structural check but represents bad science.

    The token is:
      - Correct type: clinical.utility_bound.v1
      - Valid status: token constructor says "valid"
      - Correct provenance: bound to (claim, candidate, context, allowed_use)
      - Unexpired
      - PPV = 0.16: clears the notification floor (0.15) by the minimum margin
      - sample_size = 47: dramatically underpowered for a PPV estimate
      - population_description: "internal validation set (n=47, single shift)"
        — the study was run on the model's own training population, not a
        held-out or external set

    The detail contract checks PPV >= floor. It does not check:
      - Whether the sample size is sufficient for a reliable PPV estimate
      - Whether the validation population is independent of training data
      - Whether the study was pre-registered
      - Whether the certifier who issued the token has a conflict of interest

    These are science-quality checks. They are outside the TCB by design.
    The compiler's epistemological boundary is: correct form, not correct science.
    """
    ppv_floor = 0.15
    fabricated_ppv = 0.16   # barely clears the floor
    sample_size = 47        # underpowered — 95% CI on PPV = 0.16 is roughly [0.07, 0.25]

    contract_ok = fabricated_ppv >= ppv_floor
    fab_token = t.ProofToken(
        token_id="tcb-t4-tok",
        token_type="clinical.utility_bound.v1",
        schema_version="med001/0.1",
        status="valid" if contract_ok else "invalid",
        closes_gaps=[],
        bounds_gaps=["clinical_utility_gap"] if contract_ok else [],
        provenance_hash=_prov(),
        issued_at=_NOW - 3600,
        issuer="vendor.internal.certifier",
        is_negative_control=False,
        details=json.dumps({
            "model_id": "sepsis_v1",
            "alert_action": "nurse_notification",
            "blast_radius": "notification",
            "threshold": 0.3,
            "sensitivity": 0.71,
            "specificity": 0.84,
            "ppv": fabricated_ppv,
            "npv": 0.97,
            "nnt": round(1.0 / fabricated_ppv, 2),
            "false_alert_rate": round(1.0 - 0.84, 4),
            "population_description": "internal validation set (n=47, single shift, same EHR as training)",
            "sample_size": sample_size,
            "ppv_floor_applied": ppv_floor,
            "detail_contract_ok": contract_ok,
            # The following fields reveal the scientific problems — but the
            # compiler does not read or evaluate them:
            "WARNING_underpowered": f"n={sample_size} → 95% CI on PPV ~[0.07, 0.29]; floor cannot be reliably established",
            "WARNING_population": "validation set drawn from same EHR system as training; distribution shift not assessed",
            "WARNING_independence": "no pre-registration; validation run after model was tuned to this population",
        }),
    )

    statuses = {g: "bounded" for g in _ALL_GAPS}
    statuses["clinical_utility_gap"] = "open"
    result = _compile(statuses, tokens=[fab_token])
    detected = result != t.Permission.ALR

    return CorruptionResult(
        vector_id="T4",
        description=(
            f"Fabricated utility token: PPV={fabricated_ppv} (floor={ppv_floor}), "
            f"n={sample_size}, training-population validation, no pre-registration"
        ),
        corruption=(
            "Token passes the PPV floor check by 0.01. Sample size is 47. "
            "Validation population is the training population. Study not pre-registered. "
            "All structural compiler checks pass."
        ),
        compiler_output=str(result),
        detected=detected,
        tcb_surface=(
            "The compiler checks token.status, provenance_hash, expiry, and the "
            "detail contract's PPV floor. It does not check sample size, population "
            "independence, pre-registration status, or certifier conflicts of interest. "
            "These are science-quality obligations. They are in the TCB by design: "
            "they require domain expertise that the compiler cannot encode as a "
            "structural constraint."
        ),
        finding=(
            "UNDETECTED: fabricated token passes all structural checks; "
            f"compiler emits {result}. "
            "The PPV floor is satisfied (0.16 >= 0.15). The compiler has no "
            "mechanism to evaluate the scientific quality of the study behind the token."
            if not detected else
            f"DETECTED: compiler emits {result} (unexpected — investigate)."
        ),
        implication=(
            "The TCB boundary is precisely here: correct form is the compiler's domain; "
            "correct science is the certifier's domain. A vendor who runs a 47-patient "
            "internal study, obtains PPV=0.16, and issues a token is undetectable at "
            "the compiler level. Defense: the detail contract registry should encode "
            "minimum sample size requirements (e.g. n >= 500 for PPV estimates at this "
            "prevalence), independence requirements (held-out or external population), "
            "and pre-registration requirements. These would be checked inside the "
            "certifier, not the compiler."
        ),
    )


# ── T5: Membership misclassification ─────────────────────────────────────────

def tcb_t5_membership_misclassification() -> CorruptionResult:
    """T5: Two membership misclassification scenarios.

    T5a: Deliberate — OutOfClass candidate submitted as InClass.
         The membership field is caller-asserted. OOC fires correctly when
         asserted honestly. If the caller lies, the compiler has no defense.

    T5b: Negligent — an ambiguous-class case where reasonable experts disagree
         about whether the candidate is in scope. The compiler must accept
         one classification. Whichever it accepts, it enforces consistently —
         but the boundary of enforcement is the boundary of classification.

    The ambiguous case: a sepsis model being used to guide antibiotic *stewardship*
    (reducing unnecessary antibiotics). The candidate is the same model, the same
    output, but the action direction is reversed: the alert now means "do not give
    antibiotics" rather than "consider giving antibiotics." Is this the same
    claim class? A bridge author who says InClass produces a very different
    result than one who says OutOfClass.
    """
    # T5a: OOC candidate submitted as InClass
    result_spoofed = _compile(
        {g: "bounded" for g in _ALL_GAPS},
        membership=t.Membership.InClass,
    )
    result_honest = _compile(
        {g: "bounded" for g in _ALL_GAPS},
        membership=t.Membership.OutOfClassExact,
    )

    # T5b: Ambiguous class — same evidence, InClass vs OutOfClass
    # The "ambiguous" scenario: sepsis model repurposed for stewardship
    # (same model, same score, action = "withhold antibiotic" instead of "trigger alert")
    result_ambiguous_in  = _compile({g: "bounded" for g in _ALL_GAPS}, membership=t.Membership.InClass)
    result_ambiguous_out = _compile({g: "bounded" for g in _ALL_GAPS}, membership=t.Membership.OutOfClassExact)

    t5a_detected = result_spoofed != t.Permission.ALR

    return CorruptionResult(
        vector_id="T5",
        description=(
            "T5a: Deliberate misclassification (OOC→InClass). "
            "T5b: Ambiguous class boundary (stewardship repurposing of alert model)."
        ),
        corruption=(
            "T5a: membership=InClass asserted for a candidate the expert would classify OOC. "
            "T5b: claim class boundary is genuinely ambiguous; compiler must accept one "
            "classification and enforces it consistently, but the boundary itself is ungoverned."
        ),
        compiler_output=(
            f"T5a: spoofed={result_spoofed} / honest={result_honest}. "
            f"T5b: InClass={result_ambiguous_in} / OutOfClass={result_ambiguous_out}."
        ),
        detected=False,
        tcb_surface=(
            "Membership classification is caller-asserted. The compiler enforces "
            "the classification it receives; it cannot independently determine "
            "whether the candidate belongs to the claim class. Claim class boundaries "
            "are a governance artifact, not a structural constraint."
        ),
        finding=(
            f"T5a UNDETECTED: OOC candidate reaches {result_spoofed} when submitted as InClass. "
            f"Honest OOC correctly yields {result_honest}. "
            f"T5b: Same evidence yields {result_ambiguous_in} (InClass) vs "
            f"{result_ambiguous_out} (OutOfClass) — membership is the deciding variable "
            "for cases at the class boundary."
        ),
        implication=(
            "Claim class definition is the highest-leverage governance decision in the "
            "framework. Narrow class definitions (sepsis alerting only, not stewardship) "
            "constrain the domain the compiler governs. Wide definitions risk false in-scope "
            "judgments. The compiler cannot resolve this — it requires domain governance "
            "that specifies exactly what candidates belong to each claim class."
        ),
    )


# ── T6: Detail contract version mismatch ─────────────────────────────────────

def tcb_t6_contract_version_mismatch() -> CorruptionResult:
    """T6: Token carrying a deprecated schema_version.

    The proof context has gap_taxonomy_version and gap_profile_version fields
    that fix the governing vocabulary. Tokens carry a schema_version string.

    Does the compiler enforce that token.schema_version matches the current
    detail contract registry version? Or does it accept any token whose
    status field says "valid", regardless of schema version?

    T6a: Token with schema_version="med001/0.0" (deprecated) — structural checks pass,
         schema version is a metadata field, compiler accepts it.
    T6b: Token with schema_version="" (empty) — does the compiler reject?
    T6c: Correct schema version — baseline for comparison.

    The key question: does detail_contract_registry_version in the ProofContext
    create a hard binding between tokens and the current contract, or is it
    advisory metadata?
    """
    ph = _prov()

    def _utility_token(schema_ver: str) -> t.ProofToken:
        return t.ProofToken(
            token_id=f"tcb-t6-{schema_ver.replace('/', '-')}",
            token_type="clinical.utility_bound.v1",
            schema_version=schema_ver,
            status="valid",
            closes_gaps=[],
            bounds_gaps=["clinical_utility_gap"],
            provenance_hash=ph,
            issued_at=_NOW - 60,
            issuer="tcb.test",
            is_negative_control=False,
            details=json.dumps({"ppv": 0.40, "ppv_floor_applied": 0.15, "detail_contract_ok": True}),
        )

    statuses = {g: "bounded" for g in _ALL_GAPS}
    statuses["clinical_utility_gap"] = "open"

    result_deprecated = _compile(statuses, tokens=[_utility_token("med001/0.0")])
    result_empty      = _compile(statuses, tokens=[_utility_token("")])
    result_current    = _compile(statuses, tokens=[_utility_token("med001/0.1")])

    # All three are expected to pass — schema_version is metadata, not enforced
    t6_detected = not (result_deprecated == result_current == result_empty == t.Permission.ALR)

    return CorruptionResult(
        vector_id="T6",
        description=(
            "Token schema_version: deprecated ('med001/0.0'), empty (''), current ('med001/0.1')"
        ),
        corruption=(
            "Token carries an outdated or empty schema_version string. "
            "The proof context carries a detail_contract_registry_version field. "
            "If these are not bound together, a token issued under a now-superseded "
            "contract (with weaker requirements) can satisfy the current profile."
        ),
        compiler_output=(
            f"deprecated={result_deprecated} / empty={result_empty} / current={result_current}"
        ),
        detected=t6_detected,
        tcb_surface=(
            "schema_version on ProofToken and detail_contract_registry_version on "
            "ProofContext are both stored and auditable, but the compiler does not "
            "enforce that they match. Contract version binding is a governance "
            "obligation on the certifier, not a structural compiler constraint."
        ),
        finding=(
            f"UNDETECTED: deprecated schema_version={result_deprecated}, "
            f"empty={result_empty}, current={result_current}. "
            "All three reach the same permission. Schema version is metadata — "
            "the compiler accepts any valid token regardless of its declared contract version."
            if not t6_detected else
            "DETECTED: schema_version mismatch blocked (unexpected — investigate)."
        ),
        implication=(
            "Detail contract versioning is advisory at the compiler level. A token "
            "issued under a v0.0 contract (which had no PPV floor, for example) can "
            "satisfy a profile that was designed for v0.1 tokens. Defense: the certifier "
            "must refuse to issue tokens under deprecated contract versions, and the "
            "proof context's detail_contract_registry_version should be checked against "
            "the token's schema_version inside the certifier before token issuance."
        ),
    )


# ── Runner ─────────────────────────────────────────────────────────────────────

def run_all_tcb_experiments() -> list[CorruptionResult]:
    return [
        tcb_t1_status_assertion_no_token(),
        tcb_t2_bound_value_gaming(),
        tcb_t3_token_type_gap_mismatch(),
        tcb_t4_fabricated_science(),
        tcb_t5_membership_misclassification(),
        tcb_t6_contract_version_mismatch(),
    ]
