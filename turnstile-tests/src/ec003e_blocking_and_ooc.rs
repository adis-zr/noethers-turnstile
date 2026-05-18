/// EC-003E — Blocking reasons, OOC boundary, disallowed-use ceiling.
///
/// Ported from:
///   test_ec003e_blocking_reasons.py
///   test_ec003e_out_of_class_boundary.py
///   test_ec003e_rollback_without_capability.py
///
/// Properties proved:
///   T6  — No proof, no license: missing evidence → blocked, not promoted
///   T2  — Token validity soundness: only Valid tokens contribute
///   T11 — Diagnostic/action separation: disallowed_uses cap at ROL
use chrono::Utc;
use proptest::prelude::*;
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn arb_membership() -> impl Strategy<Value = Membership> {
    prop_oneof![
        Just(Membership::InClass),
        Just(Membership::OutOfClassExact),
        Just(Membership::OutOfClassAuthorizedDeterministicWrite),
        Just(Membership::OutOfClassNoConsequentialUse),
    ]
}

fn arb_permission() -> impl Strategy<Value = Permission> {
    prop_oneof![
        Just(Permission::OOC),
        Just(Permission::EXP),
        Just(Permission::REF),
        Just(Permission::UNS),
        Just(Permission::ETA),
        Just(Permission::ESC),
        Just(Permission::ROL),
        Just(Permission::DIA),
        Just(Permission::REV),
        Just(Permission::AEX),
        Just(Permission::ALR),
        Just(Permission::AAA),
    ]
}

fn minimal_ctx() -> ProofContext {
    ProofContext {
        claim_id: "c".into(),
        candidate_id: "z".into(),
        context_id: "ctx".into(),
        context_fingerprint: "fp".into(),
        allowed_use: "use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── T6: No proof, no license ──────────────────────────────────────────────────

#[test]
fn no_profiles_gives_ooc() {
    let ctx = minimal_ctx();
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::OOC);
}

#[test]
fn profile_without_token_gives_uns() {
    let mut ctx = minimal_ctx();
    ctx.gaps.push(GapRecord::open("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    // No token supplied → gap stays Open → profile not satisfied → UNS (in-class, profile defined)
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::UNS);
}

#[test]
fn open_gap_blocks_profile() {
    let mut ctx = minimal_ctx();
    ctx.gaps.push(GapRecord::open("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    // Open gap → ClosedRequired not satisfied → UNS (in-class, profile defined)
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::UNS);
}

#[test]
fn bounded_gap_satisfies_bounded_required() {
    let mut ctx = minimal_ctx();
    ctx.gaps.push(GapRecord::bounded(
        "g1",
        "t",
        turnstile_core::gap::Bound::numeric(0.05),
    ));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::BoundedRequired,
        }],
    });
    // Bounded gap satisfies BoundedRequired
    let j = compile(ctx).unwrap();
    // No token to actually bound → OOC (gap record alone doesn't satisfy; token must contribute)
    // BUT in turnstile, the gap record status IS used directly (token contributes or record status)
    // The compiler checks effective_gap_status, which starts from the record status.
    // If the gap record says Bounded and no token overrides it → BoundedRequired is met.
    // Let's verify the actual semantics by testing both cases.
    // (Gap record = Bounded, no closing token → effective = Bounded → BoundedRequired satisfied)
    assert_eq!(j.permission, Permission::DIA);
}

#[test]
fn bounded_gap_does_not_satisfy_closed_required() {
    let mut ctx = minimal_ctx();
    ctx.gaps.push(GapRecord::bounded(
        "g1",
        "t",
        turnstile_core::gap::Bound::numeric(0.05),
    ));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let j = compile(ctx).unwrap();
    // Bounded ≠ Closed → ClosedRequired not satisfied → UNS (in-class, profile defined)
    assert_eq!(j.permission, Permission::UNS);
}

// ── T2: Token validity — only Valid tokens contribute ────────────────────────

#[test]
fn malformed_token_does_not_satisfy_profile() {
    let hash = compute_provenance_hash("c", "z", "ctx", "use");
    let mut ctx = minimal_ctx();
    ctx.gaps.push(GapRecord::open("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    ctx.tokens.push(ProofToken {
        token_id: "tok-malformed".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Malformed,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    });
    // Malformed token → skipped, gap stays Open, profile not satisfied → REF
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::REF);
}

// ── Out-of-class membership → always OOC (T6 / structural) ───────────────────

#[test]
fn out_of_class_exact_gives_ooc() {
    let mut ctx = minimal_ctx();
    ctx.membership = Membership::OutOfClassExact;
    // Even with a satisfied profile, OOC membership gives OOC
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let hash = compute_provenance_hash("c", "z", "ctx", "use");
    ctx.tokens.push(ProofToken {
        token_id: "tok".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    });
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::OOC);
}

#[test]
fn out_of_class_no_consequential_use_gives_ooc() {
    let mut ctx = minimal_ctx();
    ctx.membership = Membership::OutOfClassNoConsequentialUse;
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::OOC);
}

#[test]
fn out_of_class_authorized_deterministic_write_gives_ooc() {
    let mut ctx = minimal_ctx();
    ctx.membership = Membership::OutOfClassAuthorizedDeterministicWrite;
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::OOC);
}

// ── T11: Disallowed-use ceiling at ROL ────────────────────────────────────────

#[test]
fn disallowed_uses_caps_at_rol() {
    let mut ctx = minimal_ctx();
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::AAA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let hash = compute_provenance_hash("c", "z", "ctx", "use");
    ctx.tokens.push(ProofToken {
        token_id: "tok".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    });
    ctx.disallowed_uses = vec!["production-write".into()];

    let j = compile(ctx).unwrap();
    assert!(
        j.permission <= Permission::ROL,
        "disallowed_uses must cap at ROL"
    );
}

#[test]
fn disallowed_uses_only_cap_if_above_rol() {
    let mut ctx = minimal_ctx();
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::ETA, // ETA < ROL → should not be capped
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let hash = compute_provenance_hash("c", "z", "ctx", "use");
    ctx.tokens.push(ProofToken {
        token_id: "tok".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    });
    ctx.disallowed_uses = vec!["something".into()];

    let j = compile(ctx).unwrap();
    // ETA < ROL, so disallowed_uses ceiling does not lower it further
    assert_eq!(j.permission, Permission::ETA);
}

// ── Authority ceiling is hard cap ────────────────────────────────────────────

#[test]
fn authority_ceiling_hard_caps_outcome() {
    let mut ctx = minimal_ctx();
    ctx.gaps.push(GapRecord::closed("g1", "t"));
    ctx.profiles.push(Profile {
        permission: Permission::AAA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let hash = compute_provenance_hash("c", "z", "ctx", "use");
    ctx.tokens.push(ProofToken {
        token_id: "tok".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    });
    ctx.authority_ceiling = Permission::DIA;

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA);
}

// ── Proptest ──────────────────────────────────────────────────────────────────

proptest! {
    #[test]
    fn prop_out_of_class_always_ooc(
        membership in arb_membership(),
        ceiling in arb_permission(),
    ) {
        prop_assume!(!membership.is_in_class());
        let ctx = ProofContext {
            claim_id: "c".into(),
            candidate_id: "z".into(),
            context_id: "ctx".into(),
            context_fingerprint: "fp".into(),
            allowed_use: "use".into(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps: vec![GapRecord::closed("g1", "t")],
            profiles: vec![Profile {
                permission: Permission::AAA,
                required_gaps: vec![GapRequirement {
                    gap_id: "g1".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                }],
            }],
            tokens: vec![],
            expiry: Expiry::never(),
            authority_ceiling: ceiling,
            permission_ceiling: Permission::AAA,
            membership,
        };
        let j = compile(ctx).unwrap();
        prop_assert_eq!(j.permission, Permission::OOC);
    }

    #[test]
    fn prop_disallowed_uses_never_above_rol(
        n in 1usize..5usize,
    ) {
        let mut ctx = minimal_ctx();
        ctx.gaps.push(GapRecord::closed("g1", "t"));
        ctx.profiles.push(Profile {
            permission: Permission::AAA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        });
        let hash = compute_provenance_hash("c", "z", "ctx", "use");
        ctx.tokens.push(ProofToken {
            token_id: "tok".into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        });
        ctx.disallowed_uses = (0..n).map(|i| format!("use-{i}")).collect();
        let j = compile(ctx).unwrap();
        prop_assert!(j.permission <= Permission::ROL);
    }
}
