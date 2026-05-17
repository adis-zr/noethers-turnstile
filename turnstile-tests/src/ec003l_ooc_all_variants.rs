/// EC-003L — Out-of-class variants: all four OOC membership variants project to OOC.
///
/// Covers theorems:
///   T1  — Fake-token non-promotion: OOC membership + tokens = OOC
///   H1  — Membership check is the first gate
///
/// Tests all four OutOfClass variants including OutOfClassOther(reason).
/// Confirms that no matter what evidence is in the context, non-InClass
/// membership always projects to OOC.
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

fn saturated_ctx(membership: Membership) -> ProofContext {
    // Build the most evidence-rich context possible and verify OOC still wins.
    let claim_id = "c-ooc";
    let candidate_id = "z-ooc";
    let context_id = "ctx-ooc";
    let allowed_use = "ooc-use";
    let gap_id = "g1";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);
    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-ooc".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed(gap_id, "t")],
        profiles: vec![Profile {
            permission: Permission::AAA,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-ooc".into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![gap_id.into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
        }],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership,
    }
}

// ── All four OOC variants → OOC regardless of evidence ───────────────────────

#[test]
fn out_of_class_exact_gives_ooc() {
    let j = compile(saturated_ctx(Membership::OutOfClassExact)).unwrap();
    assert_eq!(j.permission, Permission::OOC);
}

#[test]
fn out_of_class_authorized_deterministic_write_gives_ooc() {
    let j = compile(saturated_ctx(Membership::OutOfClassAuthorizedDeterministicWrite)).unwrap();
    assert_eq!(j.permission, Permission::OOC);
}

#[test]
fn out_of_class_no_consequential_use_gives_ooc() {
    let j = compile(saturated_ctx(Membership::OutOfClassNoConsequentialUse)).unwrap();
    assert_eq!(j.permission, Permission::OOC);
}

#[test]
fn out_of_class_other_gives_ooc() {
    let j = compile(saturated_ctx(Membership::OutOfClassOther("adversarial reason".into()))).unwrap();
    assert_eq!(j.permission, Permission::OOC);
}

// ── OOC with empty context also gives OOC ─────────────────────────────────────

#[test]
fn out_of_class_exact_empty_ctx_gives_ooc() {
    let ctx = ProofContext {
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
        membership: Membership::OutOfClassExact,
    };
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::OOC);
}

// ── Membership derivation step is first ──────────────────────────────────────

#[test]
fn ooc_derivation_first_step_is_membership_check() {
    let ctx = saturated_ctx(Membership::OutOfClassExact);
    let j = compile(ctx).unwrap();
    assert!(!j.derivation.steps.is_empty(), "derivation must have steps");
    let first = &j.derivation.steps[0];
    assert_eq!(first.phase, "membership_check");
    assert_eq!(first.permission_after, Permission::OOC);
}

// ── OOC membership overrides disallowed_uses (already OOC) ───────────────────

#[test]
fn ooc_with_disallowed_uses_still_ooc() {
    let mut ctx = saturated_ctx(Membership::OutOfClassNoConsequentialUse);
    ctx.disallowed_uses = vec!["write".into()];
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::OOC);
}

// ── OOC membership overrides low authority ceiling ───────────────────────────

#[test]
fn ooc_with_low_authority_ceiling_still_ooc_not_lower() {
    let mut ctx = saturated_ctx(Membership::OutOfClassExact);
    ctx.authority_ceiling = Permission::OOC;
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::OOC); // already OOC, ceiling is OOC.meet(OOC) = OOC
}

// ── InClass membership enables evidence evaluation ────────────────────────────

#[test]
fn in_class_membership_enables_aaa() {
    let j = compile(saturated_ctx(Membership::InClass)).unwrap();
    assert_eq!(j.permission, Permission::AAA);
}

// ── Proptest: all non-InClass variants project to OOC ────────────────────────

fn arb_ooc_membership() -> impl Strategy<Value = Membership> {
    prop_oneof![
        Just(Membership::OutOfClassExact),
        Just(Membership::OutOfClassAuthorizedDeterministicWrite),
        Just(Membership::OutOfClassNoConsequentialUse),
        "[a-z]{3,10}".prop_map(Membership::OutOfClassOther),
    ]
}

fn arb_permission() -> impl Strategy<Value = Permission> {
    prop_oneof![
        Just(Permission::OOC),
        Just(Permission::EXP),
        Just(Permission::DIA),
        Just(Permission::AAA),
    ]
}

proptest! {
    #[test]
    fn prop_all_ooc_variants_give_ooc(
        membership in arb_ooc_membership(),
        ceiling in arb_permission(),
    ) {
        let mut ctx = saturated_ctx(membership);
        ctx.authority_ceiling = ceiling;
        let j = compile(ctx).unwrap();
        prop_assert_eq!(j.permission, Permission::OOC,
            "OOC membership must project to OOC regardless of evidence");
    }

    #[test]
    fn prop_ooc_membership_with_arbitrary_disallowed_uses(
        n_disallowed in 0usize..5usize,
    ) {
        let mut ctx = saturated_ctx(Membership::OutOfClassExact);
        ctx.disallowed_uses = (0..n_disallowed).map(|i| format!("use-{i}")).collect();
        let j = compile(ctx).unwrap();
        prop_assert_eq!(j.permission, Permission::OOC);
    }
}
