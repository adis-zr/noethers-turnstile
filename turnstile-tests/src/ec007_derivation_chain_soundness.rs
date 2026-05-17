/// EC-007 — Derivation chain soundness.
///
/// The derivation record is the full audit trail of a judgment.  For the audit
/// to be trustworthy, every step in the derivation must reflect a non-increasing
/// sequence of permissions: no step may *raise* the permission above the previous
/// step (non-promotion invariant on the derivation itself).
///
/// Formally:
///   For all i < j: derivation.steps[i].permission_after ≥ derivation.steps[j].permission_after
///
/// This is distinct from T8/T9 (composition non-promotion) — it is a structural
/// invariant on the derivation record produced by compile().
///
/// Additionally:
///   - The final step's permission_after must equal judgment.permission.
///   - The derivation's provenance_hash must match the context's provenance hash.
///   - compiled_at must be set (not None) for every compiled judgment.
///
/// Tests:
///   - OOC membership: single step, permission_after == OOC
///   - DIA with token: derivation steps are non-increasing
///   - Authority ceiling lowers: step ordering preserved
///   - Disallowed uses lower: step ordering preserved
///   - Expiry blocker: EXP is final and non-increasing
///   - Provenance hash in derivation matches context
///   - compiled_at is Some
///   - Proptest: for any context, derivation steps are always non-increasing
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

fn base_ctx() -> ProofContext {
    let claim_id = "deriv-claim";
    let candidate_id = "deriv-z";
    let context_id = "deriv-ctx";
    let allowed_use = "deriv-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "deriv-fp".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "t")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "deriv-tok".into(),
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
        }],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

fn assert_derivation_non_increasing(j: &turnstile_core::Judgment) {
    let steps = &j.derivation.steps;
    for i in 1..steps.len() {
        assert!(
            steps[i].permission_after <= steps[i - 1].permission_after,
            "derivation step {} raised permission: {} → {} (phase: {:?})",
            i,
            steps[i - 1].permission_after,
            steps[i].permission_after,
            steps[i].phase
        );
    }
    // Final step permission_after must match judgment.permission.
    if let Some(last) = steps.last() {
        assert_eq!(
            last.permission_after, j.permission,
            "last derivation step permission_after must equal judgment.permission"
        );
    }
}

// ── OOC: single step, non-increasing trivially ──────────────────────────────

#[test]
fn ooc_derivation_has_single_step_at_ooc() {
    let ctx = ProofContext {
        membership: Membership::OutOfClassExact,
        ..base_ctx()
    };
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::OOC);
    assert!(!j.derivation.steps.is_empty());
    assert_derivation_non_increasing(&j);
    assert_eq!(j.derivation.steps[0].permission_after, Permission::OOC);
}

// ── DIA: multi-step derivation is non-increasing ────────────────────────────

#[test]
fn dia_derivation_steps_non_increasing() {
    let j = compile(base_ctx()).unwrap();
    assert_eq!(j.permission, Permission::DIA);
    assert_derivation_non_increasing(&j);
}

// ── Authority ceiling lowers: derivation is non-increasing ──────────────────

#[test]
fn authority_ceiling_derivation_non_increasing() {
    let mut ctx = base_ctx();
    ctx.profiles[0].permission = Permission::AAA;
    ctx.authority_ceiling = Permission::DIA;
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA);
    assert_derivation_non_increasing(&j);
}

// ── Disallowed uses cap: derivation is non-increasing ───────────────────────

#[test]
fn disallowed_uses_derivation_non_increasing() {
    let mut ctx = base_ctx();
    ctx.profiles[0].permission = Permission::AAA;
    ctx.disallowed_uses = vec!["prod-write".into()];
    let j = compile(ctx).unwrap();
    assert!(j.permission <= Permission::ROL);
    assert_derivation_non_increasing(&j);
}

// ── Expiry blocker: derivation ends at EXP and non-increasing ────────────────

#[test]
fn expiry_blocker_derivation_non_increasing() {
    let past = Utc::now() - chrono::Duration::seconds(1);
    let mut ctx = base_ctx();
    ctx.tokens[0].expires_at = Some(past);
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::EXP);
    assert_derivation_non_increasing(&j);
}

// ── Provenance hash in derivation matches context ───────────────────────────

#[test]
fn derivation_provenance_hash_matches_context() {
    let ctx = base_ctx();
    let expected_hash = ctx.provenance_hash();
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.derivation.provenance_hash, expected_hash,
        "derivation provenance_hash must match context provenance_hash"
    );
}

// ── compiled_at is always set ────────────────────────────────────────────────

#[test]
fn derivation_compiled_at_is_some() {
    let j = compile(base_ctx()).unwrap();
    assert!(
        j.derivation.compiled_at.is_some(),
        "Derivation::compiled_at must be Some for every compiled judgment"
    );
}

// ── Proptest: derivation always non-increasing for any context ───────────────

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

proptest! {
    #[test]
    fn prop_derivation_steps_always_non_increasing(
        ceiling in arb_permission(),
        has_disallowed in proptest::bool::ANY,
    ) {
        let mut ctx = base_ctx();
        ctx.authority_ceiling = ceiling;
        if has_disallowed {
            ctx.disallowed_uses = vec!["blocked".into()];
        }
        let j = compile(ctx).unwrap();
        let steps = &j.derivation.steps;
        for i in 1..steps.len() {
            prop_assert!(
                steps[i].permission_after <= steps[i - 1].permission_after,
                "derivation step {} raised permission: {} → {}",
                i,
                steps[i - 1].permission_after,
                steps[i].permission_after
            );
        }
        if let Some(last) = steps.last() {
            prop_assert_eq!(
                last.permission_after, j.permission,
                "last derivation step must match judgment.permission"
            );
        }
    }

    #[test]
    fn prop_derivation_provenance_always_matches_context(
        ceiling in arb_permission(),
    ) {
        let mut ctx = base_ctx();
        ctx.authority_ceiling = ceiling;
        let expected_hash = ctx.provenance_hash();
        let j = compile(ctx).unwrap();
        prop_assert_eq!(
            &j.derivation.provenance_hash,
            &expected_hash,
            "derivation provenance_hash must always match context hash"
        );
    }
}
