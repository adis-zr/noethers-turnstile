/// EC-042 — Heterogeneous anti-laundering (T16, EC-001 §38).
///
/// T16: In a multi-group composition, no group can launder a stale or OOC
/// context through a fresh one.  Stale-to-fresh transitions across N contexts
/// must not promote permission.  OOC membership is absorbing under compose_n.
///
///   H1  — All four Membership variant pairwise (16 pairs): OOC absorbs
///   H2  — N=3 composition: one OOC member → result OOC
///   H3  — N=5 composition: one OOC member → result OOC
///   H4  — N=10 composition: one OOC member → result OOC
///   H5  — OOC in position 0 (leftmost) → OOC
///   H6  — OOC in position N-1 (rightmost) → OOC
///   H7  — OOC in middle position → OOC
///   H8  — 9 fresh AAA + 1 OOC → OOC (adversarial majority attack)
///   H9  — Fresh with highest authority ceiling + 1 OOC → OOC
///   H10 — InClass ∘ OutOfClassAuthorizedDeterministicWrite → OOC
///   H11 — InClass ∘ OutOfClassExact → OOC
///   H12 — InClass ∘ OutOfClassNoConsequentialUse → OOC
///   H13 — OutOfClassExact ∘ OutOfClassAuthorizedDeterministicWrite → OOC
///   H14 — Non-promotion: adding any OOC context cannot raise permission
///   H15 — All 16 Membership pairwise combinations compile to OOC or InClass
///   H16 — compose_n of all-InClass does not degrade (baseline)
///   Prop1 — Any single OOC context in compose_n makes result OOC
///   Prop2 — For any N, inserting OOC at any position makes result OOC
use chrono::Utc;
use proptest::prelude::*;
use noethers_noethers_turnstile_core::{
    compile, compose, compose_n,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

const ALL_MEMBERSHIPS: [Membership; 4] = [
    Membership::InClass,
    Membership::OutOfClassExact,
    Membership::OutOfClassAuthorizedDeterministicWrite,
    Membership::OutOfClassNoConsequentialUse,
];

fn in_class_ctx(suffix: &str) -> ProofContext {
    let gap_id = "g1";
    let hash = compute_provenance_hash(
        &format!("claim-{suffix}"),
        &format!("z-{suffix}"),
        &format!("ctx-{suffix}"),
        "het-use",
    );
    ProofContext {
        claim_id: format!("claim-{suffix}"),
        candidate_id: format!("z-{suffix}"),
        context_id: format!("ctx-{suffix}"),
        context_fingerprint: format!("fp-{suffix}"),
        allowed_use: "het-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed(gap_id, "t")],
        profiles: vec![Profile {
            permission: Permission::DIA,
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
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

fn ooc_ctx(membership: Membership, suffix: &str) -> ProofContext {
    let mut ctx = in_class_ctx(suffix);
    ctx.membership = membership;
    ctx
}

fn minimal_ctx_with_membership(membership: Membership, suffix: &str) -> ProofContext {
    ProofContext {
        claim_id: format!("claim-{suffix}"),
        candidate_id: format!("z-{suffix}"),
        context_id: format!("ctx-{suffix}"),
        context_fingerprint: format!("fp-{suffix}"),
        allowed_use: "het-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership,
    }
}

fn is_ooc(m: &Membership) -> bool {
    !matches!(m, Membership::InClass)
}

// ── H1: All 16 membership pairs — OOC absorbs ────────────────────────────────

#[test]
fn h1_all_membership_pairs_ooc_absorbs() {
    for (i, m1) in ALL_MEMBERSHIPS.iter().enumerate() {
        for (j, m2) in ALL_MEMBERSHIPS.iter().enumerate() {
            let ctx1 = minimal_ctx_with_membership(m1.clone(), &format!("h1-{i}a"));
            let ctx2 = minimal_ctx_with_membership(m2.clone(), &format!("h1-{j}b"));
            let expect_ooc = is_ooc(m1) || is_ooc(m2);

            if let Ok(composed) = compose(ctx1, ctx2) {
                let j = compile(composed).unwrap();
                if expect_ooc {
                    assert_eq!(
                        j.permission,
                        Permission::OOC,
                        "H1: ({m1:?} ∘ {m2:?}) must produce OOC"
                    );
                }
            }
        }
    }
}

// ── H2–H4: N-way composition with one OOC member ─────────────────────────────

fn compose_n_with_one_ooc_at(pos: usize, n: usize) -> Permission {
    let ctxs: Vec<ProofContext> = (0..n)
        .map(|i| {
            if i == pos {
                ooc_ctx(Membership::OutOfClassExact, &format!("ooc-{i}"))
            } else {
                in_class_ctx(&format!("fresh-{i}"))
            }
        })
        .collect();
    let composed = compose_n(ctxs).unwrap();
    compile(composed).unwrap().permission
}

#[test]
fn h2_n3_one_ooc_yields_ooc() {
    assert_eq!(
        compose_n_with_one_ooc_at(1, 3),
        Permission::OOC,
        "H2: N=3 with one OOC must yield OOC"
    );
}

#[test]
fn h3_n5_one_ooc_yields_ooc() {
    assert_eq!(
        compose_n_with_one_ooc_at(2, 5),
        Permission::OOC,
        "H3: N=5 with one OOC must yield OOC"
    );
}

#[test]
fn h4_n10_one_ooc_yields_ooc() {
    assert_eq!(
        compose_n_with_one_ooc_at(4, 10),
        Permission::OOC,
        "H4: N=10 with one OOC must yield OOC"
    );
}

// ── H5–H7: OOC position independence ─────────────────────────────────────────

#[test]
fn h5_ooc_at_position_0_yields_ooc() {
    assert_eq!(
        compose_n_with_one_ooc_at(0, 4),
        Permission::OOC,
        "H5: OOC at position 0 must yield OOC"
    );
}

#[test]
fn h6_ooc_at_last_position_yields_ooc() {
    assert_eq!(
        compose_n_with_one_ooc_at(3, 4),
        Permission::OOC,
        "H6: OOC at last position must yield OOC"
    );
}

#[test]
fn h7_ooc_at_middle_position_yields_ooc() {
    assert_eq!(
        compose_n_with_one_ooc_at(2, 5),
        Permission::OOC,
        "H7: OOC at middle position must yield OOC"
    );
}

// ── H8: Adversarial majority: 9 fresh AAA + 1 OOC ────────────────────────────

#[test]
fn h8_nine_fresh_plus_one_ooc_yields_ooc() {
    let mut ctxs: Vec<ProofContext> = (0..9)
        .map(|i| in_class_ctx(&format!("fresh-{i}")))
        .collect();
    ctxs.push(ooc_ctx(Membership::OutOfClassExact, "adversarial"));

    let composed = compose_n(ctxs).unwrap();
    let j = compile(composed).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "H8: 9 fresh AAA + 1 OOC must yield OOC (majority attack blocked)"
    );
}

// ── H9: Fresh with highest ceiling + 1 OOC → OOC ────────────────────────────

#[test]
fn h9_highest_ceiling_plus_ooc_yields_ooc() {
    let mut fresh = in_class_ctx("h9-fresh");
    fresh.authority_ceiling = Permission::AAA;

    let ooc = ooc_ctx(Membership::OutOfClassExact, "h9-ooc");

    let composed = compose(fresh, ooc).unwrap();
    let j = compile(composed).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "H9: fresh AAA ceiling + OOC must yield OOC"
    );
}

// ── H10–H13: Specific Membership combinations ────────────────────────────────

#[test]
fn h10_inclass_compose_adw_yields_ooc() {
    let ctx1 = minimal_ctx_with_membership(Membership::InClass, "h10a");
    let ctx2 =
        minimal_ctx_with_membership(Membership::OutOfClassAuthorizedDeterministicWrite, "h10b");
    let composed = compose(ctx1, ctx2).unwrap();
    let j = compile(composed).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "H10: InClass ∘ OutOfClassAuthorizedDeterministicWrite → OOC"
    );
}

#[test]
fn h11_inclass_compose_exact_yields_ooc() {
    let ctx1 = minimal_ctx_with_membership(Membership::InClass, "h11a");
    let ctx2 = minimal_ctx_with_membership(Membership::OutOfClassExact, "h11b");
    let composed = compose(ctx1, ctx2).unwrap();
    let j = compile(composed).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "H11: InClass ∘ OutOfClassExact → OOC"
    );
}

#[test]
fn h12_inclass_compose_ncu_yields_ooc() {
    let ctx1 = minimal_ctx_with_membership(Membership::InClass, "h12a");
    let ctx2 = minimal_ctx_with_membership(Membership::OutOfClassNoConsequentialUse, "h12b");
    let composed = compose(ctx1, ctx2).unwrap();
    let j = compile(composed).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "H12: InClass ∘ OutOfClassNoConsequentialUse → OOC"
    );
}

#[test]
fn h13_exact_compose_adw_yields_ooc() {
    let ctx1 = minimal_ctx_with_membership(Membership::OutOfClassExact, "h13a");
    let ctx2 =
        minimal_ctx_with_membership(Membership::OutOfClassAuthorizedDeterministicWrite, "h13b");
    let composed = compose(ctx1, ctx2).unwrap();
    let j = compile(composed).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "H13: OutOfClassExact ∘ OutOfClassAuthorizedDeterministicWrite → OOC"
    );
}

// ── H14: Non-promotion — adding OOC cannot raise permission ──────────────────

#[test]
fn h14_adding_ooc_cannot_raise_permission() {
    let fresh = in_class_ctx("h14-fresh");
    let p_fresh = compile(fresh.clone()).unwrap().permission;

    let ooc = ooc_ctx(Membership::OutOfClassExact, "h14-ooc");
    let composed = compose(fresh, ooc).unwrap();
    let p_composed = compile(composed).unwrap().permission;

    assert!(
        p_composed <= p_fresh,
        "H14: adding OOC context must not raise permission (got {p_composed} > {p_fresh})"
    );
}

// ── H15: All 16 membership pairs produce OOC or InClass ──────────────────────

#[test]
fn h15_all_16_pairs_produce_correct_class() {
    for (i, m1) in ALL_MEMBERSHIPS.iter().enumerate() {
        for (j, m2) in ALL_MEMBERSHIPS.iter().enumerate() {
            let ctx1 = minimal_ctx_with_membership(m1.clone(), &format!("h15-{i}a"));
            let ctx2 = minimal_ctx_with_membership(m2.clone(), &format!("h15-{j}b"));

            if let Ok(composed) = compose(ctx1, ctx2) {
                let result = compile(composed).unwrap();
                let both_in_class =
                    matches!(m1, Membership::InClass) && matches!(m2, Membership::InClass);
                if !both_in_class {
                    assert_eq!(
                        result.permission,
                        Permission::OOC,
                        "H15: ({m1:?}, {m2:?}) must yield OOC"
                    );
                }
            }
        }
    }
}

// ── H16: All-InClass baseline — does not degrade ──────────────────────────────

#[test]
fn h16_all_inclass_compose_n_does_not_degrade_to_ooc() {
    let ctxs: Vec<ProofContext> = (0..5).map(|i| in_class_ctx(&format!("base-{i}"))).collect();
    let composed = compose_n(ctxs).unwrap();
    let j = compile(composed).unwrap();
    assert_ne!(
        j.permission,
        Permission::OOC,
        "H16: all-InClass composition must not degrade to OOC"
    );
}

// ── Proptests ─────────────────────────────────────────────────────────────────

fn arb_membership() -> impl Strategy<Value = Membership> {
    prop_oneof![
        Just(Membership::InClass),
        Just(Membership::OutOfClassExact),
        Just(Membership::OutOfClassAuthorizedDeterministicWrite),
        Just(Membership::OutOfClassNoConsequentialUse),
    ]
}

proptest! {
    #[test]
    fn prop_any_ooc_in_compose_n_yields_ooc(
        n in 2usize..8,
        ooc_pos in 0usize..8,
        ooc_variant in arb_membership(),
    ) {
        prop_assume!(!matches!(ooc_variant, Membership::InClass));
        let ooc_idx = ooc_pos % n;
        let ctxs: Vec<ProofContext> = (0..n)
            .map(|i| {
                if i == ooc_idx {
                    ooc_ctx(ooc_variant.clone(), &format!("ooc-{i}"))
                } else {
                    in_class_ctx(&format!("fresh-{i}"))
                }
            })
            .collect();
        if let Ok(composed) = compose_n(ctxs) {
            let j = compile(composed).unwrap();
            prop_assert_eq!(
                j.permission,
                Permission::OOC,
                "any OOC in compose_n must yield OOC"
            );
        }
    }

    #[test]
    fn prop_ooc_position_independence(
        pos1 in 0usize..5,
        pos2 in 0usize..5,
    ) {
        // Same set of contexts, OOC placed at two different positions → both OOC
        let p1 = compose_n_with_one_ooc_at(pos1 % 5, 5);
        let p2 = compose_n_with_one_ooc_at(pos2 % 5, 5);
        prop_assert_eq!(p1, Permission::OOC, "OOC at position must yield OOC");
        prop_assert_eq!(p2, Permission::OOC, "OOC at position must yield OOC");
    }
}
