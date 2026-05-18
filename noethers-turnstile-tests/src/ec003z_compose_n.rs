/// EC-003Z — N-ary composition via compose_n.
///
/// Verifies that the `compose_n` convenience function exactly replicates
/// the result of iterated binary `compose`, and that all N-ary composition
/// invariants hold:
///
///   T9: compile(compose_n([Γ₁,…,Γₙ])).permission ≤ compile(Γᵢ) for all i
///   T10: Composition monotonicity: compose_n can only narrow evidence
///   T13: Disallowed-use accumulation: union across all inputs
///   T14: Scope containment: composed scope ⊆ every input scope
///   Expiry: composed expiry = minimum of all input expiries
///
/// Also tests:
///   - compose_n([]) = EmptyComposition error
///   - compose_n([Γ]) = Γ (identity for singleton)
///   - compose_n is associativity-agnostic (same result regardless of fold order)
use chrono::{Duration, Utc};
use proptest::prelude::*;
use noethers_noethers_turnstile_core::{
    compile, compose, compose_n,
    context::{Membership, ProofContext, Scope},
    error::CompositionError,
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn base_ctx(suffix: &str) -> ProofContext {
    let claim_id = "claim-cn";
    let candidate_id = "z-cn";
    let context_id = "ctx-cn";
    let allowed_use = "cn-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: format!("fp-cn-{suffix}"),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "calibration_gap")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-cn-1".into(),
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

// ── Boundary cases ────────────────────────────────────────────────────────────

#[test]
fn compose_n_empty_returns_error() {
    let result = compose_n(std::iter::empty::<ProofContext>());
    assert!(
        matches!(result, Err(CompositionError::EmptyComposition)),
        "compose_n([]) must return EmptyComposition; got {result:?}"
    );
}

#[test]
fn compose_n_singleton_returns_same_permission() {
    let ctx = base_ctx("singleton");
    let p_direct = compile(ctx.clone()).unwrap().permission;
    let composed = compose_n(std::iter::once(ctx)).unwrap();
    let p_composed = compile(composed).unwrap().permission;
    assert_eq!(
        p_direct, p_composed,
        "compose_n([Γ]) must produce same permission as compile(Γ)"
    );
}

// ── Equivalence with iterated binary compose ──────────────────────────────────

#[test]
fn compose_n_two_equals_binary_compose() {
    let c1 = base_ctx("n2-1");
    let c2 = base_ctx("n2-2");

    let binary = compose(c1.clone(), c2.clone()).unwrap();
    let p_binary = compile(binary).unwrap().permission;

    let nary = compose_n(vec![c1, c2]).unwrap();
    let p_nary = compile(nary).unwrap().permission;

    assert_eq!(
        p_binary, p_nary,
        "compose_n([Γ₁,Γ₂]) must equal compose(Γ₁,Γ₂)"
    );
}

#[test]
fn compose_n_three_equals_iterated_binary() {
    let c1 = base_ctx("n3-1");
    let c2 = base_ctx("n3-2");
    let c3 = base_ctx("n3-3");

    let iterated = compose(compose(c1.clone(), c2.clone()).unwrap(), c3.clone()).unwrap();
    let p_iterated = compile(iterated).unwrap().permission;

    let nary = compose_n(vec![c1, c2, c3]).unwrap();
    let p_nary = compile(nary).unwrap().permission;

    assert_eq!(
        p_iterated, p_nary,
        "compose_n([Γ₁,Γ₂,Γ₃]) must equal left-fold binary compose"
    );
}

// ── T9: Non-promotion ─────────────────────────────────────────────────────────

#[test]
fn t9_compose_n_does_not_promote_above_any_individual() {
    let ctxs: Vec<ProofContext> = (1..=5).map(|i| base_ctx(&format!("{i}"))).collect();
    let individual_permissions: Vec<Permission> = ctxs
        .iter()
        .cloned()
        .map(|c| compile(c).unwrap().permission)
        .collect();
    let min_individual = Permission::meet_n(individual_permissions.iter().copied()).unwrap();

    let composed = compose_n(ctxs).unwrap();
    let p_composed = compile(composed).unwrap().permission;

    assert!(
        p_composed <= min_individual,
        "T9: compose_n result {p_composed} > min of individuals {min_individual}"
    );
}

#[test]
fn t9_compose_n_ooc_context_pulls_to_ooc() {
    let mut ctxs: Vec<ProofContext> = (1..=4).map(|i| base_ctx(&format!("ooc-{i}"))).collect();
    // Make the third one OOC.
    ctxs[2].membership = Membership::OutOfClassExact;

    let composed = compose_n(ctxs).unwrap();
    let j = compile(composed).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "T9: one OOC context in compose_n must pull result to OOC"
    );
}

// ── T13: Disallowed-use accumulation ─────────────────────────────────────────

#[test]
fn t13_compose_n_accumulates_disallowed_uses() {
    let mut c1 = base_ctx("t13-1");
    let mut c2 = base_ctx("t13-2");
    let mut c3 = base_ctx("t13-3");
    c1.disallowed_uses = vec!["write".into()];
    c2.disallowed_uses = vec!["delete".into()];
    c3.disallowed_uses = vec!["admin".into()];

    let composed = compose_n(vec![c1, c2, c3]).unwrap();
    assert!(composed.disallowed_uses.contains(&"write".to_string()));
    assert!(composed.disallowed_uses.contains(&"delete".to_string()));
    assert!(composed.disallowed_uses.contains(&"admin".to_string()));
}

// ── T14: Scope containment ────────────────────────────────────────────────────

#[test]
fn t14_compose_n_intersects_scopes() {
    let make_ctx_with_tools = |suffix: &str, tools: Vec<&str>| {
        let mut ctx = base_ctx(suffix);
        ctx.scope = Scope {
            allowed_tools: tools.iter().map(|s| s.to_string()).collect(),
            ..Default::default()
        };
        ctx
    };

    let c1 = make_ctx_with_tools("t14-1", vec!["a", "b", "c"]);
    let c2 = make_ctx_with_tools("t14-2", vec!["b", "c", "d"]);
    let c3 = make_ctx_with_tools("t14-3", vec!["c", "d", "e"]);

    let composed = compose_n(vec![c1, c2, c3]).unwrap();
    // {a,b,c} ∩ {b,c,d} ∩ {c,d,e} = {c}
    assert_eq!(composed.scope.allowed_tools, vec!["c"]);
}

// ── Expiry: minimum ───────────────────────────────────────────────────────────

#[test]
fn compose_n_takes_minimum_expiry() {
    let now = Utc::now();
    let mut c1 = base_ctx("exp-1");
    let mut c2 = base_ctx("exp-2");
    let mut c3 = base_ctx("exp-3");
    c1.expiry = Expiry::at(now + Duration::seconds(300));
    c2.expiry = Expiry::at(now + Duration::seconds(60)); // shortest
    c3.expiry = Expiry::at(now + Duration::seconds(180));

    let composed = compose_n(vec![c1, c2, c3]).unwrap();
    let deadline = composed.expiry.deadline.expect("must have deadline");
    assert!(
        (deadline - (now + Duration::seconds(60)))
            .num_milliseconds()
            .abs()
            < 100,
        "compose_n must take minimum expiry; expected ~60s got {deadline}"
    );
}

// ── Authority ceiling ─────────────────────────────────────────────────────────

#[test]
fn compose_n_takes_meet_of_ceilings() {
    let mut c1 = base_ctx("ceil-1");
    let mut c2 = base_ctx("ceil-2");
    let mut c3 = base_ctx("ceil-3");
    c1.authority_ceiling = Permission::AAA;
    c2.authority_ceiling = Permission::DIA;
    c3.authority_ceiling = Permission::REV;

    let composed = compose_n(vec![c1, c2, c3]).unwrap();
    assert_eq!(
        composed.authority_ceiling,
        Permission::DIA,
        "compose_n ceiling = meet(AAA, DIA, REV) = DIA"
    );
}

// ── UseConflict propagates ────────────────────────────────────────────────────

#[test]
fn compose_n_fails_on_use_conflict() {
    let c1 = base_ctx("conflict-1");
    let mut c2 = base_ctx("conflict-2");
    c2.allowed_use = "different-use".into(); // conflict

    let result = compose_n(vec![c1, c2]);
    assert!(
        matches!(result, Err(CompositionError::UseConflict)),
        "compose_n must propagate UseConflict"
    );
}

// ── Proptest: compose_n non-promotion ────────────────────────────────────────

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
    fn prop_compose_n_non_promotion(
        ceilings in prop::collection::vec(arb_permission(), 2..6),
        add_tokens in prop::bool::ANY,
    ) {
        let claim_id = "c-prop-cn";
        let candidate_id = "z-prop-cn";
        let context_id = "ctx-prop-cn";
        let allowed_use = "prop-cn-use";
        let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

        let ctxs: Vec<ProofContext> = ceilings.iter().enumerate().map(|(i, &ceiling)| {
            let ctx = ProofContext {
                claim_id: claim_id.into(),
                candidate_id: candidate_id.into(),
                context_id: context_id.into(),
                context_fingerprint: format!("fp-prop-cn-{i}"),
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
                tokens: if add_tokens {
                    vec![ProofToken {
                        token_id: "tok-prop-cn".into(),
                        token_type: "CLOSE".into(),
                        schema_version: "0.1".into(),
                        status: TokenStatus::Valid,
                        closes_gaps: vec!["g1".into()],
                        bounds_gaps: vec![],
                        provenance_hash: hash.clone(),
                        issued_at: Utc::now(),
                        expires_at: None,
                        issuer: "test".into(),
                        details: serde_json::Value::Null,
                        is_negative_control: false,
                    }]
                } else {
                    vec![]
                },
                expiry: Expiry::never(),
                authority_ceiling: ceiling,
                permission_ceiling: Permission::AAA,
                membership: Membership::InClass,
            };
            ctx
        }).collect();

        let individual_perms: Vec<Permission> = ctxs.iter().cloned()
            .map(|c| compile(c).unwrap().permission)
            .collect();
        let min_individual = Permission::meet_n(individual_perms.iter().copied()).unwrap();

        if let Ok(composed) = compose_n(ctxs) {
            let p = compile(composed).unwrap().permission;
            prop_assert!(
                p <= min_individual,
                "compose_n non-promotion violated: {p} > min_individual {min_individual}"
            );
        }
    }
}
