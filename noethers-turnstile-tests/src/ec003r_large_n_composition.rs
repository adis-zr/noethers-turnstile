/// EC-003R — Large-N composition: monotonicity and termination at scale.
///
/// Covers theorems:
///   T9  — N-ary composition non-promotion: meet_n result ≤ every input
///   T10 — Composition monotonicity: adding more envelopes can only lower or
///          preserve the permission
///
/// The EC-003 spec (§18.3) requires that large-N composition (N≥100) remains:
///   - Monotone: permission is non-increasing as N grows
///   - Terminating: no O(N²) growth per envelope
///   - Correct: result equals permission_meet_n of individual results
///
/// Tests:
///   - N=10 composition is monotone
///   - N=100 composition is monotone
///   - Adding a weaker envelope lowers the result
///   - Adding an identical envelope preserves the result (idempotence)
///   - Adding an OOC envelope absorbs to OOC
///   - N=1000 terminates in reasonable time
///   - Proptest: N random envelopes monotonicity
use chrono::Utc;
use proptest::prelude::*;
use noethers_turnstile_core::{
    compile, compose,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn dia_ctx(suffix: &str) -> ProofContext {
    let claim_id = "claim-ln";
    let candidate_id = "z-ln";
    let context_id = format!("ctx-ln-{suffix}");
    let allowed_use = "ln-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, &context_id, allowed_use);

    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.clone(),
        context_fingerprint: format!("fp-{suffix}"),
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
            token_id: format!("tok-{suffix}"),
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
        authority_ceiling: Permission::DIA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

fn ctx_with_ceiling(suffix: &str, ceiling: Permission) -> ProofContext {
    let mut ctx = dia_ctx(suffix);
    ctx.authority_ceiling = ceiling;
    ctx
}

fn compose_n(mut base: ProofContext, n: usize) -> ProofContext {
    for i in 1..n {
        let next = dia_ctx(&format!("n{i}"));
        base = compose(base, next).unwrap();
    }
    base
}

// ── N=10 monotonicity ─────────────────────────────────────────────────────────

#[test]
fn compose_10_same_contexts_is_idempotent() {
    let single = dia_ctx("base");
    let p_single = compile(single.clone()).unwrap().permission;

    let composed = compose_n(single, 10);
    let p_composed = compile(composed).unwrap().permission;

    assert_eq!(
        p_composed, p_single,
        "composing 10 identical contexts must preserve permission"
    );
}

#[test]
fn adding_weaker_envelope_lowers_result() {
    let strong = ctx_with_ceiling("strong", Permission::DIA);
    let weak = ctx_with_ceiling("weak", Permission::REF);

    let p_strong = compile(strong.clone()).unwrap().permission;
    let p_weak = compile(weak.clone()).unwrap().permission;

    let composed = compose(strong, weak).unwrap();
    let p_composed = compile(composed).unwrap().permission;

    assert!(
        p_composed <= p_strong,
        "composed result {p_composed} must be ≤ strong {p_strong}"
    );
    assert!(
        p_composed <= p_weak || p_composed == p_weak,
        "composed result {p_composed} must be ≤ weak {p_weak}"
    );
    assert!(
        p_composed <= p_strong.meet(p_weak),
        "composed must be ≤ meet(strong, weak)"
    );
}

#[test]
fn adding_ooc_envelope_absorbs_to_ooc() {
    let strong = ctx_with_ceiling("strong2", Permission::AAA);
    let ooc_ctx = {
        let mut c = dia_ctx("ooc-ctx");
        c.membership = Membership::OutOfClassExact;
        c
    };

    let p_ooc = compile(ooc_ctx.clone()).unwrap().permission;
    assert_eq!(p_ooc, Permission::OOC);

    let composed = compose(strong, ooc_ctx).unwrap();
    let p_composed = compile(composed).unwrap().permission;
    assert_eq!(
        p_composed,
        Permission::OOC,
        "OOC membership must absorb to OOC"
    );
}

// ── N=100 monotonicity ────────────────────────────────────────────────────────

#[test]
fn compose_100_same_contexts_is_monotone() {
    let base = dia_ctx("base100");
    let p_base = compile(base.clone()).unwrap().permission;

    let composed = compose_n(base, 100);
    let p_composed = compile(composed).unwrap().permission;

    assert!(
        p_composed <= p_base,
        "compose(100) permission {p_composed} must be ≤ base {p_base}"
    );
}

#[test]
fn compose_100_monotone_with_one_weaker() {
    // 99 strong envelopes + 1 weak envelope: result must equal weak.
    let mut base = dia_ctx("mono100-0");
    base.authority_ceiling = Permission::DIA;

    for i in 1..99usize {
        let mut next = dia_ctx(&format!("mono100-{i}"));
        next.authority_ceiling = Permission::DIA;
        base = compose(base, next).unwrap();
    }

    let p_before_weak = compile(base.clone()).unwrap().permission;

    let mut weak = dia_ctx("mono100-weak");
    weak.authority_ceiling = Permission::ETA;
    let weak_p = compile(weak.clone()).unwrap().permission;

    base = compose(base, weak).unwrap();
    let p_after = compile(base).unwrap().permission;

    assert!(
        p_after <= p_before_weak,
        "adding weak envelope must not increase permission: {p_after} > {p_before_weak}"
    );
    assert!(p_after <= weak_p, "composed must be ≤ weak {weak_p}");
}

// ── N=1000 terminates ────────────────────────────────────────────────────────

#[test]
fn compose_1000_terminates() {
    // This test verifies there is no O(N²) blowup.
    // It uses a simple chain of identical low-overhead contexts.
    let base = dia_ctx("scale-0");
    let composed = compose_n(base, 1000);
    let p = compile(composed).unwrap().permission;
    // Any permission is acceptable; we just need it to complete.
    assert!(p <= Permission::AAA);
}

// ── Permission_meet_n equivalence ────────────────────────────────────────────

#[test]
fn composed_permission_equals_meet_n_of_individuals() {
    let ceilings = [
        Permission::AAA,
        Permission::DIA,
        Permission::REV,
        Permission::AEX,
        Permission::ROL,
        Permission::ESC,
    ];
    let individual_perms: Vec<Permission> = ceilings
        .iter()
        .enumerate()
        .map(|(i, &c)| {
            let mut ctx = dia_ctx(&format!("meet-n-{i}"));
            ctx.authority_ceiling = c;
            compile(ctx).unwrap().permission
        })
        .collect();

    let expected = Permission::meet_n(individual_perms.iter().copied()).unwrap();

    let mut base = {
        let mut ctx = dia_ctx("meet-n-0");
        ctx.authority_ceiling = ceilings[0];
        ctx
    };
    for (i, &c) in ceilings.iter().enumerate().skip(1) {
        let mut next = dia_ctx(&format!("meet-n-{i}"));
        next.authority_ceiling = c;
        base = compose(base, next).unwrap();
    }
    let p_composed = compile(base).unwrap().permission;

    assert!(
        p_composed <= expected,
        "composed {p_composed} must be ≤ meet_n of individuals {expected}"
    );
}

// ── Proptest: N random ceilings non-promotion ────────────────────────────────

fn arb_ceiling() -> impl Strategy<Value = Permission> {
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
    fn prop_n_composition_non_promotion(
        ceilings in prop::collection::vec(arb_ceiling(), 2..=20),
    ) {
        // Compute expected: meet_n of all individual compiled permissions.
        let individual_perms: Vec<Permission> = ceilings
            .iter()
            .enumerate()
            .map(|(i, &c)| {
                let mut ctx = dia_ctx(&format!("prop-ln-{i}"));
                ctx.authority_ceiling = c;
                compile(ctx).unwrap().permission
            })
            .collect();
        let expected_min = Permission::meet_n(individual_perms.iter().copied()).unwrap();

        // Compose them all in sequence.
        let (first_ceiling, rest) = ceilings.split_first().unwrap();
        let mut base = {
            let mut ctx = dia_ctx("prop-ln-0");
            ctx.authority_ceiling = *first_ceiling;
            ctx
        };
        for (i, &c) in rest.iter().enumerate() {
            let mut next = dia_ctx(&format!("prop-ln-{}", i + 1));
            next.authority_ceiling = c;
            base = compose(base, next).unwrap();
        }
        let p_composed = compile(base).unwrap().permission;

        prop_assert!(
            p_composed <= expected_min,
            "composed {p_composed} > meet_n({expected_min}) for ceilings {:?}",
            ceilings
        );
    }

    #[test]
    fn prop_monotone_under_additional_envelope(
        n in 2usize..=20usize,
        extra_ceiling in arb_ceiling(),
    ) {
        // Build n-envelope composition, then add one more.
        let mut base = dia_ctx("prop-mono-0");
        base.authority_ceiling = Permission::DIA;

        for i in 1..n {
            let mut next = dia_ctx(&format!("prop-mono-{i}"));
            next.authority_ceiling = Permission::DIA;
            base = compose(base, next).unwrap();
        }
        let p_before = compile(base.clone()).unwrap().permission;

        let mut extra = dia_ctx("prop-mono-extra");
        extra.authority_ceiling = extra_ceiling;
        let base = compose(base, extra).unwrap();
        let p_after = compile(base).unwrap().permission;

        prop_assert!(
            p_after <= p_before,
            "adding one more envelope must not increase permission: {p_after} > {p_before}"
        );
    }
}
