/// EC-005 — Domain admission contract: A1–A9 structural predicates.
///
/// Ported from:
///   test_ec005a_admission_contract_predicates.py   (A1–A9 clean + single mutations)
///   test_ec003e_negative_controls.py               (T17 negative control liveness)
///
/// Properties proved:
///   T19 — Scientific-boundary theorem: only checkable justifications pass admission
///   T6  — No proof, no license (via A1–A9 admission gates)
///
/// In Turnstile terms: the domain admission contract is encoded as structural
/// requirements on ProofContext. We test each requirement in isolation:
///
///   A1 — Candidate identity stable (claim_id + candidate_id are non-empty)
///   A2 — Adapter deterministic (same context → same compile result)
///   A3 — Finite gap basis (gap_ids are distinct, no duplicates)
///   A4 — Profile is wellformed (each profile has at least one gap requirement)
///   A5 — Tokens have typed schema_version (non-empty)
///   A6 — Authority ceiling declared (not AAA when disallowed_uses present)
///   A7 — Runtime context contract (context_fingerprint non-empty)
///   A8 — Closed under gap operations (closed gap record → not downgraded by open gap)
///   A9 — Finite checkability (compile terminates; we test this by structure)
use chrono::Utc;
use proptest::prelude::*;
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    error,
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn base_ctx() -> ProofContext {
    let claim_id = "claim-a9";
    let candidate_id = "z-a9";
    let context_id = "ctx-a9";
    let allowed_use = "use-a9";
    let gap_id = "g1";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-a9".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed(gap_id, "calibration_gap")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-a9".into(),
            token_type: "CALIBRATION_CERT".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![gap_id.into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "domain-certifier".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        }],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── A1: Candidate identity stable ────────────────────────────────────────────

#[test]
fn a1_clean_base_passes() {
    let ctx = base_ctx();
    assert!(!ctx.claim_id.is_empty(), "claim_id must be non-empty");
    assert!(
        !ctx.candidate_id.is_empty(),
        "candidate_id must be non-empty"
    );
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA);
}

#[test]
fn a1_empty_claim_id_invalidates_provenance_token() {
    // When claim_id is mutated after the token was issued, the token's
    // provenance hash no longer matches the context. If the gap record is
    // OPEN (not pre-attested), the token rejection means OOC.
    let claim_id = "";
    let candidate_id = "z-a9";
    let context_id = "ctx-a9";
    let allowed_use = "use-a9";
    let gap_id = "g1";
    // Compute hash for the ORIGINAL (non-empty) claim_id — simulates a token
    // issued under a different identity than presented.
    let original_hash = compute_provenance_hash("claim-a9", candidate_id, context_id, allowed_use);

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-a9".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open(gap_id, "calibration_gap")], // OPEN: token must close it
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-a9".into(),
            token_type: "CALIBRATION_CERT".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![gap_id.into()],
            bounds_gaps: vec![],
            provenance_hash: original_hash, // issued for "claim-a9", not ""
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "domain-certifier".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        }],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "token issued for different identity must not close gap"
    );
}

#[test]
fn a1_empty_candidate_id_invalidates_provenance_token() {
    let claim_id = "claim-a9";
    let candidate_id = ""; // empty
    let context_id = "ctx-a9";
    let allowed_use = "use-a9";
    let gap_id = "g1";
    let original_hash = compute_provenance_hash(claim_id, "z-a9", context_id, allowed_use);

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-a9".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open(gap_id, "calibration_gap")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-a9".into(),
            token_type: "CALIBRATION_CERT".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![gap_id.into()],
            bounds_gaps: vec![],
            provenance_hash: original_hash, // issued for "z-a9", not ""
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "domain-certifier".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        }],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "token issued for different candidate must not close gap"
    );
}

// ── A2: Adapter determinism ───────────────────────────────────────────────────

#[test]
fn a2_same_context_same_result_ten_times() {
    let ctx = base_ctx();
    let first = compile(ctx.clone()).unwrap().permission;
    for _ in 0..9 {
        let result = compile(ctx.clone()).unwrap().permission;
        assert_eq!(result, first, "compile is not deterministic");
    }
}

// ── A3: Finite gap basis (distinct gap_ids) ───────────────────────────────────

#[test]
fn a3_duplicate_gap_ids_produce_malformed_context() {
    let mut ctx = base_ctx();
    // Duplicate gap_id is now a structural error: compile() returns MalformedContext.
    ctx.gaps.push(GapRecord::open("g1", "calibration_gap")); // duplicate of the g1 already in base_ctx
    let result = compile(ctx);
    assert!(
        matches!(
            result,
            Err(crate::error::TurnstileError::MalformedContext(_))
        ),
        "A3: duplicate gap_id must produce MalformedContext; got {:?}",
        result
    );
}

// ── A4: Profile wellformedness ────────────────────────────────────────────────

#[test]
fn a4_empty_required_gaps_means_trivially_satisfied() {
    let mut ctx = base_ctx();
    ctx.profiles.push(Profile {
        permission: Permission::AAA,
        required_gaps: vec![], // vacuously satisfied
    });
    let j = compile(ctx).unwrap();
    // Descending search: AAA profile with no requirements → satisfied immediately
    assert_eq!(j.permission, Permission::AAA);
}

#[test]
fn a4_profile_referencing_missing_gap_is_malformed() {
    let mut ctx = base_ctx();
    ctx.profiles.push(Profile {
        permission: Permission::REV,
        required_gaps: vec![GapRequirement {
            gap_id: "nonexistent-gap".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    // REV references a gap_id not in ctx.gaps → MalformedContext (validation step).
    let result = compile(ctx);
    assert!(
        matches!(
            result,
            Err(crate::error::TurnstileError::MalformedContext(_))
        ),
        "A4: profile referencing missing gap_id must produce MalformedContext; got {:?}",
        result
    );
}

// ── A5: Typed token schema versions ─────────────────────────────────────────

#[test]
fn a5_empty_schema_version_token_still_checked_for_provenance() {
    let mut ctx = base_ctx();
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ctx.tokens[0] = ProofToken {
        token_id: "tok-no-schema".into(),
        token_type: "CALIBRATION_CERT".into(),
        schema_version: String::new(), // empty schema version
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "domain-certifier".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    // Schema version is not currently checked by the compiler (certifier responsibility)
    // but the token is still valid if provenance matches.
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA);
}

// ── A6: Authority ceiling declared ───────────────────────────────────────────

#[test]
fn a6_explicit_ceiling_limits_outcome() {
    let mut ctx = base_ctx();
    ctx.authority_ceiling = Permission::ROL;
    let j = compile(ctx).unwrap();
    assert!(
        j.permission <= Permission::ROL,
        "authority_ceiling should limit outcome"
    );
}

#[test]
fn a6_disallowed_uses_with_low_ceiling() {
    let mut ctx = base_ctx();
    ctx.disallowed_uses = vec!["write".into()];
    ctx.authority_ceiling = Permission::ETA; // below ROL
    let j = compile(ctx).unwrap();
    // disallowed_uses caps at ROL, authority caps at ETA → ETA is the meet
    assert_eq!(j.permission, Permission::ETA);
}

// ── A7: Runtime context contract ─────────────────────────────────────────────

#[test]
fn a7_non_empty_fingerprint_enables_live_judgment() {
    use turnstile_core::expiry::RuntimeContext;
    let ctx = base_ctx();
    assert!(!ctx.context_fingerprint.is_empty());
    let judgment = compile(ctx).unwrap();
    let rt = RuntimeContext::new(Utc::now(), "fp-a9");
    let live = turnstile_core::expiry::LiveJudgment::new(judgment, &rt);
    assert_eq!(live.permission(), Permission::DIA);
}

#[test]
fn a7_fingerprint_mismatch_downgrades() {
    use turnstile_core::expiry::RuntimeContext;
    let ctx = base_ctx();
    let judgment = compile(ctx).unwrap();
    let rt = RuntimeContext::new(Utc::now(), "fp-wrong");
    let live = turnstile_core::expiry::LiveJudgment::new(judgment, &rt);
    assert_eq!(live.permission(), Permission::EXP);
}

// ── A8: Closed under gap operations ──────────────────────────────────────────

#[test]
fn a8_closed_gap_not_downgraded_by_adding_another_open_gap() {
    // Adding a second, unrelated open gap to a context that already satisfies a profile
    // must not lower the permission for that profile.
    let mut ctx = base_ctx();
    ctx.gaps.push(GapRecord::open("g2", "other_gap"));
    // Profile for DIA only requires g1 (not g2) → still satisfied
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA);
}

// ── A9: Finite checkability — compile always terminates ──────────────────────

#[test]
fn a9_large_profile_compiles_in_finite_time() {
    let claim_id = "c";
    let candidate_id = "z";
    let context_id = "ctx";
    let allowed_use = "use";

    let gap_count = 12; // one per permission level
    let mut ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: (0..gap_count)
            .map(|i| GapRecord::closed(format!("g{i}"), "t"))
            .collect(),
        profiles: Permission::descending()
            .zip(0..gap_count)
            .map(|(perm, i)| Profile {
                permission: perm,
                required_gaps: (0..=i)
                    .map(|j| GapRequirement {
                        gap_id: format!("g{j}"),
                        minimum_status: RequiredStatus::ClosedRequired,
                    })
                    .collect(),
            })
            .collect(),
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);
    for i in 0..gap_count {
        ctx.tokens.push(ProofToken {
            token_id: format!("tok-{i}"),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![format!("g{i}")],
            bounds_gaps: vec![],
            provenance_hash: hash.clone(),
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        });
    }

    let j = compile(ctx).unwrap();
    // AAA profile requires g0..g11 all closed → all satisfied → AAA
    assert_eq!(j.permission, Permission::AAA);
}

// ── Proptest: determinism (A2) and authority ceiling monotonicity (A6) ────────

proptest! {
    #[test]
    fn prop_determinism_same_input_same_output(
        ceiling in prop_oneof![
            Just(Permission::DIA),
            Just(Permission::REV),
            Just(Permission::AAA),
        ]
    ) {
        let mut ctx = base_ctx();
        ctx.authority_ceiling = ceiling;
        let p1 = compile(ctx.clone()).unwrap().permission;
        let p2 = compile(ctx).unwrap().permission;
        prop_assert_eq!(p1, p2, "compile must be deterministic");
    }

    #[test]
    fn prop_authority_ceiling_is_hard_cap(
        ceiling in prop_oneof![
            Just(Permission::OOC),
            Just(Permission::EXP),
            Just(Permission::DIA),
            Just(Permission::ROL),
            Just(Permission::AEX),
        ]
    ) {
        let mut ctx = base_ctx();
        ctx.authority_ceiling = ceiling;
        let j = compile(ctx).unwrap();
        prop_assert!(
            j.permission <= ceiling,
            "authority_ceiling {ceiling} not respected: got {}", j.permission
        );
    }
}
