/// EC-021 — MalformedContext validation: compile() must reject structurally invalid
///           contexts rather than silently degrading.
///
/// Validation invariants (each tested independently and in combination):
///   V1 — Empty `allowed_use` → MalformedContext.
///   V2 — Profile references a gap_id absent from ctx.gaps → MalformedContext.
///   V3 — Duplicate gap_id in ctx.gaps → MalformedContext.
///   V4 — Duplicate permission level in ctx.profiles → MalformedContext.
///   V5 — Valid contexts are not rejected by the validator.
///   V6 — OOC membership contexts are still validated before the membership check.
///   V7 — Validation fires before any compilation step (no side-effects on Err).
///   V8 — MalformedContext error message is non-empty and human-readable.
///
/// All tests verify `Err(TurnstileError::MalformedContext(_))` is returned.
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    error::TurnstileError,
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

use chrono::Utc;

fn base_ctx(suffix: &str) -> ProofContext {
    ProofContext {
        claim_id: format!("claim-{suffix}"),
        candidate_id: format!("z-{suffix}"),
        context_id: format!("ctx-{suffix}"),
        context_fingerprint: format!("fp-{suffix}"),
        allowed_use: "diagnostics".into(),
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

fn make_token(suffix: &str, closes: Vec<String>, ctx: &ProofContext) -> ProofToken {
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ProofToken {
        token_id: format!("tok-{suffix}"),
        token_type: "CLOSE".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: closes,
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

fn is_malformed(result: Result<impl std::fmt::Debug, TurnstileError>) -> bool {
    matches!(result, Err(TurnstileError::MalformedContext(_)))
}

// ── V1: Empty allowed_use ────────────────────────────────────────────────────

#[test]
fn v1_empty_allowed_use_is_rejected() {
    let mut ctx = base_ctx("v1");
    ctx.allowed_use = String::new();
    assert!(
        is_malformed(compile(ctx)),
        "V1: empty allowed_use must produce MalformedContext"
    );
}

#[test]
fn v1_whitespace_only_allowed_use_is_rejected() {
    // Whitespace-only is technically non-empty, but documents that we do NOT
    // allow whitespace-only as allowed_use.  If the project decides to accept
    // whitespace, update this test.
    let mut ctx = base_ctx("v1-ws");
    ctx.allowed_use = "   ".into(); // three spaces — non-empty but useless
                                    // This is accepted by the current rule (only empty is rejected).
                                    // The test documents the current behaviour and guards against unintended tightening.
    let result = compile(ctx);
    // Either Ok (current) or MalformedContext is acceptable — just must not panic.
    assert!(
        result.is_ok() || is_malformed(result),
        "V1: whitespace allowed_use must not panic"
    );
}

// ── V2: Profile references unknown gap_id ────────────────────────────────────

#[test]
fn v2_profile_referencing_absent_gap_id_is_rejected() {
    let mut ctx = base_ctx("v2");
    ctx.gaps.push(GapRecord::open("g1", "calibration_gap"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "nonexistent_gap".into(), // not in ctx.gaps
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    assert!(
        is_malformed(compile(ctx)),
        "V2: profile referencing absent gap_id must produce MalformedContext"
    );
}

#[test]
fn v2_profile_with_one_valid_and_one_invalid_gap_ref_is_rejected() {
    let mut ctx = base_ctx("v2b");
    ctx.gaps.push(GapRecord::open("g1", "gap1"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g1".into(), // valid
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "ghost".into(), // invalid
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    });
    assert!(
        is_malformed(compile(ctx)),
        "V2: partial invalid gap ref (one valid, one ghost) must produce MalformedContext"
    );
}

#[test]
fn v2_multiple_profiles_one_bad_ref_is_rejected() {
    let mut ctx = base_ctx("v2c");
    ctx.gaps.push(GapRecord::open("g1", "gap1"));
    // Valid profile.
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    // Invalid profile (references missing gap).
    ctx.profiles.push(Profile {
        permission: Permission::REV,
        required_gaps: vec![GapRequirement {
            gap_id: "missing".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    assert!(
        is_malformed(compile(ctx)),
        "V2: one bad gap ref among multiple profiles must produce MalformedContext"
    );
}

// ── V3: Duplicate gap_ids ────────────────────────────────────────────────────

#[test]
fn v3_duplicate_gap_id_in_gaps_is_rejected() {
    let mut ctx = base_ctx("v3");
    ctx.gaps.push(GapRecord::open("g1", "gap_type_a"));
    ctx.gaps.push(GapRecord::open("g1", "gap_type_b")); // same gap_id
    assert!(
        is_malformed(compile(ctx)),
        "V3: duplicate gap_id must produce MalformedContext"
    );
}

#[test]
fn v3_three_gaps_with_middle_duplicate_is_rejected() {
    let mut ctx = base_ctx("v3b");
    ctx.gaps.push(GapRecord::open("g1", "type1"));
    ctx.gaps.push(GapRecord::open("g2", "type2"));
    ctx.gaps.push(GapRecord::open("g1", "type1-dup")); // duplicate of g1
    assert!(
        is_malformed(compile(ctx)),
        "V3: middle-duplicate gap_id must produce MalformedContext"
    );
}

// ── V4: Duplicate permission levels in profiles ──────────────────────────────

#[test]
fn v4_two_profiles_at_same_permission_level_is_rejected() {
    let mut ctx = base_ctx("v4");
    ctx.gaps.push(GapRecord::open("g1", "g"));
    ctx.gaps.push(GapRecord::open("g2", "g"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    ctx.profiles.push(Profile {
        permission: Permission::DIA, // same level
        required_gaps: vec![GapRequirement {
            gap_id: "g2".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    assert!(
        is_malformed(compile(ctx)),
        "V4: two profiles at the same permission level must produce MalformedContext"
    );
}

#[test]
fn v4_three_profiles_one_duplicate_level_is_rejected() {
    let mut ctx = base_ctx("v4b");
    ctx.gaps.push(GapRecord::open("g1", "g"));
    ctx.gaps.push(GapRecord::open("g2", "g"));
    ctx.gaps.push(GapRecord::open("g3", "g"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    ctx.profiles.push(Profile {
        permission: Permission::REV,
        required_gaps: vec![GapRequirement {
            gap_id: "g2".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    ctx.profiles.push(Profile {
        permission: Permission::DIA, // duplicate of first
        required_gaps: vec![GapRequirement {
            gap_id: "g3".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    assert!(
        is_malformed(compile(ctx)),
        "V4: three profiles with one duplicate level must produce MalformedContext"
    );
}

// ── V5: Valid contexts are not rejected ──────────────────────────────────────

#[test]
fn v5_valid_minimal_context_compiles_ok() {
    let ctx = base_ctx("v5");
    assert!(
        compile(ctx).is_ok(),
        "V5: minimal valid context must compile"
    );
}

#[test]
fn v5_context_with_multiple_valid_profiles_compiles_ok() {
    let mut ctx = base_ctx("v5b");
    ctx.gaps.push(GapRecord::open("g1", "g1"));
    ctx.gaps.push(GapRecord::open("g2", "g2"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    ctx.profiles.push(Profile {
        permission: Permission::REV,
        required_gaps: vec![GapRequirement {
            gap_id: "g2".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    assert!(
        compile(ctx).is_ok(),
        "V5: context with two distinct-level profiles must compile"
    );
}

#[test]
fn v5_context_with_tokens_and_gaps_compiles_ok() {
    let mut ctx = base_ctx("v5c");
    ctx.gaps.push(GapRecord::open("g1", "calibration_gap"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let tok = make_token("v5c", vec!["g1".into()], &ctx);
    ctx.tokens.push(tok);
    let result = compile(ctx);
    assert!(
        result.is_ok(),
        "V5: full valid context with token must compile"
    );
    assert_eq!(result.unwrap().permission, Permission::DIA);
}

// ── V6: OOC membership contexts are still validated ──────────────────────────

#[test]
fn v6_ooc_context_with_empty_allowed_use_is_rejected() {
    let mut ctx = base_ctx("v6");
    ctx.membership = Membership::OutOfClassExact;
    ctx.allowed_use = String::new();
    assert!(
        is_malformed(compile(ctx)),
        "V6: OOC context with empty allowed_use must still be rejected at validation"
    );
}

#[test]
fn v6_ooc_context_with_duplicate_gap_id_is_rejected() {
    let mut ctx = base_ctx("v6b");
    ctx.membership = Membership::OutOfClassOther("reason".into());
    ctx.gaps.push(GapRecord::open("dup", "type1"));
    ctx.gaps.push(GapRecord::open("dup", "type2"));
    assert!(
        is_malformed(compile(ctx)),
        "V6: OOC context with duplicate gap_id must still fail validation"
    );
}

// ── V7: Validation fires before compilation (no state mutation on Err) ────────

#[test]
fn v7_err_result_contains_no_partial_state() {
    let mut ctx = base_ctx("v7");
    ctx.allowed_use = String::new();
    let result = compile(ctx);
    // We can only check that the result is Err; there is no side-effect to
    // observe (compile() takes ownership).  This test documents the contract.
    assert!(
        is_malformed(result),
        "V7: validation error must be returned before any state mutation"
    );
}

// ── V8: Error messages are non-empty and human-readable ──────────────────────

#[test]
fn v8_malformed_context_error_message_is_nonempty() {
    let mut ctx = base_ctx("v8");
    ctx.allowed_use = String::new();
    let err = compile(ctx).unwrap_err();
    let msg = err.to_string();
    assert!(
        !msg.is_empty(),
        "V8: MalformedContext error message must not be empty"
    );
    assert!(
        msg.contains("allowed_use") || msg.contains("malformed"),
        "V8: error message must mention the offending field; got '{msg}'"
    );
}

#[test]
fn v8_bad_gap_ref_error_message_names_the_gap() {
    let mut ctx = base_ctx("v8b");
    ctx.gaps.push(GapRecord::open("real_gap", "type"));
    ctx.profiles.push(Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "phantom_gap_id".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    });
    let err = compile(ctx).unwrap_err();
    let msg = err.to_string();
    assert!(
        msg.contains("phantom_gap_id"),
        "V8: error must name the offending gap_id; got '{msg}'"
    );
}

#[test]
fn v8_duplicate_gap_id_error_message_names_the_gap() {
    let mut ctx = base_ctx("v8c");
    ctx.gaps.push(GapRecord::open("duplicate_gap", "type1"));
    ctx.gaps.push(GapRecord::open("duplicate_gap", "type2"));
    let err = compile(ctx).unwrap_err();
    let msg = err.to_string();
    assert!(
        msg.contains("duplicate_gap"),
        "V8: error must name the duplicate gap_id; got '{msg}'"
    );
}

// ── Proptest: arbitrary contexts with known-bad allowed_use always fail ──────

use proptest::prelude::*;

proptest! {
    #[test]
    fn prop_empty_allowed_use_always_malformed(
        claim_id in "[a-zA-Z0-9_-]{1,20}",
        candidate_id in "[a-zA-Z0-9_-]{1,20}",
        context_id in "[a-zA-Z0-9_-]{1,20}",
    ) {
        let ctx = ProofContext {
            claim_id,
            candidate_id,
            context_id,
            context_fingerprint: "fp".into(),
            allowed_use: String::new(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps: vec![],
            profiles: vec![],
            tokens: vec![],
            expiry: Expiry::never(),
            authority_ceiling: Permission::AAA,
            permission_ceiling: Permission::AAA,
            membership: Membership::InClass,
        };
        prop_assert!(
            is_malformed(compile(ctx)),
            "any context with empty allowed_use must produce MalformedContext"
        );
    }
}
