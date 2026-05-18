/// EC-003F — N-ary composition non-promotion and compile(compose) end-to-end.
///
/// Covers theorems:
///   T9  — N-ary composition non-promotion
///   T10 — Composition monotonicity / associativity
///   Lemma: compile(compose(Γ₁, Γ₂)).permission ≤ min(compile(Γ₁), compile(Γ₂))
///
/// The proptest_composition.rs file checks structural ceiling fields only.
/// These tests compile the composed context and verify the full compile path.
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

fn make_ctx_with_permission(target: Permission, suffix: &str) -> ProofContext {
    let claim_id = "claim-nary";
    let candidate_id = "z-nary";
    let context_id = "ctx-nary";
    let allowed_use = "nary-test";
    let gap_id = "g1";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);
    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: format!("fp-{suffix}"),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed(gap_id, "t")],
        profiles: vec![Profile {
            permission: target,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: format!("tok-{suffix}"),
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
            is_negative_control: false,
        }],
        expiry: Expiry::never(),
        authority_ceiling: target,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── Full compile after binary composition ────────────────────────────────────

#[test]
fn compile_compose_non_promotion_all_pairs() {
    use Permission::*;
    let pairs = [
        (AAA, DIA),
        (DIA, REV),
        (REV, AEX),
        (AEX, ALR),
        (ALR, AAA),
        (ROL, DIA),
        (ETA, ROL),
        (OOC, AAA),
        (EXP, DIA),
    ];
    for (p1, p2) in pairs {
        let g1 = make_ctx_with_permission(p1, "1");
        let g2 = make_ctx_with_permission(p2, "2");

        let p_g1 = compile(g1.clone()).unwrap().permission;
        let p_g2 = compile(g2.clone()).unwrap().permission;
        let expected_max = p_g1.min(p_g2); // ≤ both inputs

        if let Ok(composed) = compose(g1, g2) {
            let p_composed = compile(composed).unwrap().permission;
            assert!(
                p_composed <= expected_max,
                "compose({p1},{p2}): composed={p_composed} > min({p_g1},{p_g2})={expected_max}"
            );
        }
    }
}

// ── 3-way composition non-promotion ─────────────────────────────────────────

#[test]
fn compile_compose_three_way_non_promotion() {
    use Permission::*;
    let triples = [
        (AAA, DIA, ROL),
        (REV, AEX, ALR),
        (ESC, ROL, DIA),
        (OOC, AAA, AAA),
    ];
    for (p1, p2, p3) in triples {
        let g1 = make_ctx_with_permission(p1, "1");
        let g2 = make_ctx_with_permission(p2, "2");
        let g3 = make_ctx_with_permission(p3, "3");

        let p_g1 = compile(g1.clone()).unwrap().permission;
        let p_g2 = compile(g2.clone()).unwrap().permission;
        let p_g3 = compile(g3.clone()).unwrap().permission;
        let expected_max = p_g1.min(p_g2).min(p_g3);

        let result = compose(g1, g2).and_then(|ab| compose(ab, g3));
        if let Ok(composed) = result {
            let p_composed = compile(composed).unwrap().permission;
            assert!(
                p_composed <= expected_max,
                "3-way compose({p1},{p2},{p3}): composed={p_composed} > min={expected_max}"
            );
        }
    }
}

// ── Left vs right grouping must agree (T10 associativity) ────────────────────

#[test]
fn three_way_compose_grouping_independent() {
    use Permission::*;
    for &p1 in &[AAA, DIA, REV] {
        for &p2 in &[DIA, ROL, ETA] {
            for &p3 in &[ROL, REV, AAA] {
                let left = {
                    let ab = compose(
                        make_ctx_with_permission(p1, "a"),
                        make_ctx_with_permission(p2, "b"),
                    )
                    .unwrap();
                    compose(ab, make_ctx_with_permission(p3, "c")).unwrap()
                };
                let right = {
                    let bc = compose(
                        make_ctx_with_permission(p2, "a"),
                        make_ctx_with_permission(p3, "b"),
                    )
                    .unwrap();
                    compose(make_ctx_with_permission(p1, "c"), bc).unwrap()
                };
                let p_left = compile(left).unwrap().permission;
                let p_right = compile(right).unwrap().permission;
                assert_eq!(
                    p_left, p_right,
                    "grouping mattered: ({p1},{p2},{p3}) left={p_left} right={p_right}"
                );
            }
        }
    }
}

// ── Self-composition is non-promoting ───────────────────────────────────────

#[test]
fn self_composition_non_promoting() {
    use Permission::*;
    for &p in &[AAA, DIA, REV, ROL, ETA, OOC] {
        let ctx = make_ctx_with_permission(p, "self");
        let p_orig = compile(ctx.clone()).unwrap().permission;

        if let Ok(composed) = compose(ctx.clone(), ctx) {
            let p_self = compile(composed).unwrap().permission;
            assert!(
                p_self <= p_orig,
                "self-composition of {p} promoted: {p_orig} → {p_self}"
            );
        }
    }
}

// ── Compile(compose) ≤ min(compile(Γ₁), compile(Γ₂)): exhaustive permission pairs ──

#[test]
fn compile_compose_exhaustive_permission_pairs() {
    const ALL: [Permission; 12] = [
        Permission::OOC,
        Permission::EXP,
        Permission::REF,
        Permission::UNS,
        Permission::ETA,
        Permission::ESC,
        Permission::ROL,
        Permission::DIA,
        Permission::REV,
        Permission::AEX,
        Permission::ALR,
        Permission::AAA,
    ];
    for p1 in ALL {
        for p2 in ALL {
            let g1 = make_ctx_with_permission(p1, "1");
            let g2 = make_ctx_with_permission(p2, "2");
            let p_g1 = compile(g1.clone()).unwrap().permission;
            let p_g2 = compile(g2.clone()).unwrap().permission;

            if let Ok(composed) = compose(g1, g2) {
                let p_composed = compile(composed).unwrap().permission;
                assert!(
                    p_composed <= p_g1.min(p_g2),
                    "compose({p1},{p2}): {p_composed} > min({p_g1},{p_g2})"
                );
            }
        }
    }
}

// ── Proptest: compile(compose) ≤ min(compile(Γ₁), compile(Γ₂)) ──────────────

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
    fn prop_compile_compose_non_promotion(
        p1 in arb_permission(),
        p2 in arb_permission(),
    ) {
        let g1 = make_ctx_with_permission(p1, "a");
        let g2 = make_ctx_with_permission(p2, "b");
        let p_g1 = compile(g1.clone()).unwrap().permission;
        let p_g2 = compile(g2.clone()).unwrap().permission;

        if let Ok(composed) = compose(g1, g2) {
            let p_composed = compile(composed).unwrap().permission;
            prop_assert!(
                p_composed <= p_g1.min(p_g2),
                "compose({p1},{p2}): {p_composed} > min({p_g1},{p_g2})"
            );
        }
    }

    #[test]
    fn prop_compile_compose_three_way_non_promotion(
        p1 in arb_permission(),
        p2 in arb_permission(),
        p3 in arb_permission(),
    ) {
        let g1 = make_ctx_with_permission(p1, "a");
        let g2 = make_ctx_with_permission(p2, "b");
        let g3 = make_ctx_with_permission(p3, "c");
        let p_g1 = compile(g1.clone()).unwrap().permission;
        let p_g2 = compile(g2.clone()).unwrap().permission;
        let p_g3 = compile(g3.clone()).unwrap().permission;

        if let Ok(ab) = compose(g1, g2) {
            if let Ok(abc) = compose(ab, g3) {
                let p_composed = compile(abc).unwrap().permission;
                prop_assert!(
                    p_composed <= p_g1.min(p_g2).min(p_g3),
                    "3-way compose({p1},{p2},{p3}): {p_composed} > min({p_g1},{p_g2},{p_g3})"
                );
            }
        }
    }
}
