/// EC-013 — Composition fails closed on all conflict types.
///
/// compose() is a lax monoidal operator: any conflict must block composition
/// completely.  Partial composition (silently accepting one side) would be
/// unsound.
///
/// Conflict types tested:
///   UseConflict        — allowed_use differs between contexts
///   TokenConflict      — same token_id, different content
///   EmptyComposition   — compose_n() with 0 contexts
///
/// Non-conflict cases tested:
///   Identical token_id with identical content → deduplicated (not a conflict)
///   Matching allowed_use → compose succeeds
///
/// Tests also verify the non-promotion invariant on the result of successful
/// composition (T9/T10) for a range of permission pairs.
use chrono::Utc;
use noethers_turnstile_core::{
    compile, compose, compose_n,
    context::{Membership, ProofContext, Scope},
    error::CompositionError,
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

// ── Helpers ───────────────────────────────────────────────────────────────────

fn base_ctx(suffix: &str) -> ProofContext {
    let claim_id = format!("claim-{suffix}");
    let candidate_id = format!("z-{suffix}");
    let context_id = format!("ctx-{suffix}");
    let allowed_use = "shared-use";
    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, allowed_use);

    ProofContext {
        claim_id,
        candidate_id,
        context_id,
        context_fingerprint: format!("fp-{suffix}"),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "calibration_gap")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: format!("tok-{suffix}"),
            token_type: "CLOSE".into(),
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
        }],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── UseConflict ───────────────────────────────────────────────────────────────

#[test]
fn use_conflict_blocks_composition() {
    let mut ctx1 = base_ctx("uc-1");
    let mut ctx2 = base_ctx("uc-2");
    ctx1.allowed_use = "use-A".into();
    ctx2.allowed_use = "use-B".into();

    let result = compose(ctx1, ctx2);
    assert!(
        matches!(result, Err(CompositionError::UseConflict)),
        "differing allowed_use must produce UseConflict; got {:?}",
        result
    );
}

#[test]
fn use_conflict_is_symmetric() {
    // UseConflict must fire regardless of which context is first.
    let mut ctx1 = base_ctx("uc-sym-1");
    let mut ctx2 = base_ctx("uc-sym-2");
    ctx1.allowed_use = "use-X".into();
    ctx2.allowed_use = "use-Y".into();

    let r1 = compose(ctx1.clone(), ctx2.clone());
    let r2 = compose(ctx2, ctx1);
    assert!(matches!(r1, Err(CompositionError::UseConflict)));
    assert!(matches!(r2, Err(CompositionError::UseConflict)));
}

#[test]
fn matching_allowed_use_composes_successfully() {
    let ctx1 = base_ctx("match-1");
    let ctx2 = base_ctx("match-2");
    // Both have allowed_use = "shared-use" (from base_ctx).
    let result = compose(ctx1, ctx2);
    assert!(
        result.is_ok(),
        "matching allowed_use must compose; got {:?}",
        result
    );
}

// ── TokenConflict ─────────────────────────────────────────────────────────────

#[test]
fn token_conflict_same_id_different_type_blocks_composition() {
    let mut ctx1 = base_ctx("tc-1");
    let mut ctx2 = base_ctx("tc-2");

    // Give both contexts a token with the same token_id but different type.
    let shared_hash = compute_provenance_hash(
        &ctx1.claim_id,
        &ctx1.candidate_id,
        &ctx1.context_id,
        &ctx1.allowed_use,
    );
    let tok_a = ProofToken {
        token_id: "shared-tok".into(),
        token_type: "TYPE-A".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: shared_hash.clone(),
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    let tok_b = ProofToken {
        token_id: "shared-tok".into(),
        token_type: "TYPE-B".into(), // different type → conflict
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: shared_hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    ctx1.tokens = vec![tok_a];
    ctx2.tokens = vec![tok_b];

    let result = compose(ctx1, ctx2);
    assert!(
        matches!(result, Err(CompositionError::TokenConflict { .. })),
        "same token_id with different type must produce TokenConflict; got {:?}",
        result
    );
}

#[test]
fn token_conflict_same_id_different_issuer_blocks_composition() {
    let mut ctx1 = base_ctx("tc-iss-1");
    let mut ctx2 = base_ctx("tc-iss-2");

    let hash = compute_provenance_hash(
        &ctx1.claim_id,
        &ctx1.candidate_id,
        &ctx1.context_id,
        &ctx1.allowed_use,
    );
    let make_tok = |issuer: &str| ProofToken {
        token_id: "shared-issuer-tok".into(),
        token_type: "SAME-TYPE".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash.clone(),
        issued_at: Utc::now(),
        expires_at: None,
        issuer: issuer.into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    ctx1.tokens = vec![make_tok("certifier-A")];
    ctx2.tokens = vec![make_tok("certifier-B")];

    let result = compose(ctx1, ctx2);
    assert!(
        matches!(result, Err(CompositionError::TokenConflict { .. })),
        "same token_id with different issuer must produce TokenConflict; got {:?}",
        result
    );
}

#[test]
fn identical_token_in_both_contexts_deduplicates_successfully() {
    let mut ctx1 = base_ctx("dedup-1");
    let mut ctx2 = base_ctx("dedup-2");

    let hash = compute_provenance_hash(
        &ctx1.claim_id,
        &ctx1.candidate_id,
        &ctx1.context_id,
        &ctx1.allowed_use,
    );
    let tok = ProofToken {
        token_id: "dedup-tok".into(),
        token_type: "SAME".into(),
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
    };
    ctx1.tokens = vec![tok.clone()];
    ctx2.tokens = vec![tok];

    let result = compose(ctx1, ctx2);
    assert!(
        result.is_ok(),
        "identical token in both contexts must deduplicate (not conflict); got {:?}",
        result
    );
    let composed = result.unwrap();
    assert_eq!(
        composed.tokens.len(),
        1,
        "deduplicated token should appear exactly once"
    );
}

// ── EmptyComposition ──────────────────────────────────────────────────────────

#[test]
fn compose_n_empty_returns_empty_composition_error() {
    let result = compose_n(std::iter::empty::<ProofContext>());
    assert!(
        matches!(result, Err(CompositionError::EmptyComposition)),
        "compose_n with 0 contexts must return EmptyComposition; got {:?}",
        result
    );
}

#[test]
fn compose_n_single_context_is_identity() {
    let ctx = base_ctx("single");
    let result = compose_n(std::iter::once(ctx.clone()));
    assert!(result.is_ok(), "compose_n with 1 context must succeed");
    let composed = result.unwrap();
    assert_eq!(composed.claim_id, ctx.claim_id);
    assert_eq!(composed.authority_ceiling, ctx.authority_ceiling);
}

// ── Non-promotion guarantee (T9/T10) ─────────────────────────────────────────

fn closed_ctx(suffix: &str, ceiling: Permission) -> ProofContext {
    let claim_id = format!("claim-np-{suffix}");
    let candidate_id = format!("z-np-{suffix}");
    let context_id = format!("ctx-np-{suffix}");
    let allowed_use = "np-use";
    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, allowed_use);

    ProofContext {
        claim_id,
        candidate_id,
        context_id,
        context_fingerprint: format!("fp-np-{suffix}"),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "gap")],
        profiles: vec![Profile {
            permission: Permission::AAA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: format!("tok-np-{suffix}"),
            token_type: "CLOSE".into(),
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
        }],
        expiry: Expiry::never(),
        authority_ceiling: ceiling,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

#[test]
fn composed_permission_never_exceeds_either_input() {
    let ceilings = [
        Permission::OOC,
        Permission::REF,
        Permission::DIA,
        Permission::REV,
        Permission::AEX,
        Permission::AAA,
    ];

    for &c1 in &ceilings {
        for &c2 in &ceilings {
            let ctx1 = closed_ctx("c1", c1);
            let ctx2 = closed_ctx("c2", c2);

            let p1 = compile(ctx1.clone()).unwrap().permission;
            let p2 = compile(ctx2.clone()).unwrap().permission;

            let composed = match compose(ctx1, ctx2) {
                Ok(c) => c,
                Err(_) => continue, // UseConflict etc. — not relevant here
            };
            let pc = compile(composed).unwrap().permission;

            assert!(
                pc <= p1,
                "T9: composed permission {pc} must be ≤ input1 {p1} (ceilings {c1}/{c2})"
            );
            assert!(
                pc <= p2,
                "T9: composed permission {pc} must be ≤ input2 {p2} (ceilings {c1}/{c2})"
            );
        }
    }
}

// ── Fail-closed: composition never produces partial output ────────────────────

#[test]
fn composition_error_yields_no_partial_result() {
    // A UseConflict must return an Err — there is no "partial" Ok that
    // silently uses one side's data.
    let mut ctx1 = base_ctx("fc-1");
    let mut ctx2 = base_ctx("fc-2");
    ctx1.allowed_use = "A".into();
    ctx2.allowed_use = "B".into();

    match compose(ctx1, ctx2) {
        Err(CompositionError::UseConflict) => {} // correct
        Ok(_) => panic!("UseConflict must not produce an Ok result"),
        Err(other) => panic!("unexpected error: {:?}", other),
    }
}
