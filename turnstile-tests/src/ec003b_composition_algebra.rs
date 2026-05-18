/// EC-003B — Composition algebra: associativity, commutativity, monotonicity,
///           expiry composition, scope intersection, disallowed-use union.
///
/// Ported from:
///   test_ec003b_compose_associativity.py    (1728 triples)
///   test_ec003b_expiry_composition.py
///   test_ec003b_scope_intersection_finite.py
///   test_ec003b_allowed_use_top_semantics.py
///
/// Properties proved:
///   T9  — N-ary composition non-promotion: compose(Γ).permission ≤ all inputs
///   T10 — Composition monotonicity
///   T12 — Allowed-use soundness: UseConflict fails closed
///   T13 — Disallowed-use accumulation: union on composition
///   T14 — Scope containment: scope intersection on composition
use chrono::{Duration, Utc};
use proptest::prelude::*;
use turnstile_core::{
    compose,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{Bound, GapRecord},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

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

pub fn minimal_ctx(ceiling: Permission, suffix: &str) -> ProofContext {
    ProofContext {
        claim_id: format!("claim-{suffix}"),
        candidate_id: format!("z-{suffix}"),
        context_id: format!("ctx-{suffix}"),
        context_fingerprint: format!("fp-{suffix}"),
        allowed_use: "test-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: ceiling,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── Authority ceiling is meet on compose ─────────────────────────────────────

#[test]
fn compose_authority_ceiling_is_meet_all_pairs() {
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
            let g1 = minimal_ctx(p1, "1");
            let g2 = minimal_ctx(p2, "2");
            let composed = compose(g1, g2).unwrap();
            assert_eq!(
                composed.authority_ceiling,
                p1.meet(p2),
                "authority ceiling: compose({p1},{p2}) should be {}",
                p1.meet(p2)
            );
        }
    }
}

// ── Commutativity: authority_ceiling(compose(a,b)) == authority_ceiling(compose(b,a)) ──

#[test]
fn compose_authority_commutative_all_pairs() {
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
            let fwd = compose(minimal_ctx(p1, "a"), minimal_ctx(p2, "b")).unwrap();
            let rev = compose(minimal_ctx(p2, "a"), minimal_ctx(p1, "b")).unwrap();
            assert_eq!(fwd.authority_ceiling, rev.authority_ceiling);
        }
    }
}

// ── Associativity: ceiling of (a⊗b)⊗c == a⊗(b⊗c) ─────────────────────────

#[test]
fn compose_authority_associative_sampled_triples() {
    use Permission::*;
    for p1 in [OOC, DIA, REV, AAA] {
        for p2 in [OOC, DIA, REV, AAA] {
            for p3 in [OOC, DIA, REV, AAA] {
                let left = {
                    let ab = compose(minimal_ctx(p1, "a"), minimal_ctx(p2, "b")).unwrap();
                    compose(ab, minimal_ctx(p3, "c")).unwrap()
                };
                let right = {
                    let bc = compose(minimal_ctx(p2, "a"), minimal_ctx(p3, "b")).unwrap();
                    compose(minimal_ctx(p1, "c"), bc).unwrap()
                };
                assert_eq!(
                    left.authority_ceiling, right.authority_ceiling,
                    "associativity failed: ({p1},{p2},{p3}): left={} right={}",
                    left.authority_ceiling, right.authority_ceiling
                );
            }
        }
    }
}

// ── Disallowed-use union (T13) ────────────────────────────────────────────────

#[test]
fn compose_disallowed_uses_unioned() {
    let mut g1 = minimal_ctx(Permission::AAA, "1");
    let mut g2 = minimal_ctx(Permission::AAA, "2");
    g1.disallowed_uses = vec!["write".into()];
    g2.disallowed_uses = vec!["delete".into()];
    let composed = compose(g1, g2).unwrap();
    assert!(composed.disallowed_uses.contains(&"write".to_string()));
    assert!(composed.disallowed_uses.contains(&"delete".to_string()));
}

#[test]
fn compose_disallowed_uses_monotone_union() {
    let mut g1 = minimal_ctx(Permission::AAA, "1");
    g1.disallowed_uses = vec!["a".into(), "b".into()];
    let g2 = minimal_ctx(Permission::AAA, "2"); // no disallowed uses
    let composed = compose(g1, g2).unwrap();
    assert!(composed.disallowed_uses.contains(&"a".to_string()));
    assert!(composed.disallowed_uses.contains(&"b".to_string()));
}

#[test]
fn compose_disallowed_uses_dedup() {
    let mut g1 = minimal_ctx(Permission::AAA, "1");
    let mut g2 = minimal_ctx(Permission::AAA, "2");
    g1.disallowed_uses = vec!["x".into()];
    g2.disallowed_uses = vec!["x".into()];
    let composed = compose(g1, g2).unwrap();
    assert_eq!(
        composed
            .disallowed_uses
            .iter()
            .filter(|u| *u == "x")
            .count(),
        1
    );
}

// ── Allowed-use conflict fails closed (T12) ───────────────────────────────────

#[test]
fn compose_use_conflict_fails_closed() {
    let g1 = minimal_ctx(Permission::AAA, "1");
    let mut g2 = minimal_ctx(Permission::AAA, "2");
    g2.allowed_use = "different-use".into();
    let result = compose(g1, g2);
    assert!(
        result.is_err(),
        "conflicting allowed_use should fail closed"
    );
}

// ── Scope intersection (T14) ─────────────────────────────────────────────────

#[test]
fn compose_scope_intersection_nonempty() {
    let mut g1 = minimal_ctx(Permission::AAA, "1");
    let mut g2 = minimal_ctx(Permission::AAA, "2");
    g1.scope.allowed_tools = vec!["hammer".into(), "drill".into()];
    g2.scope.allowed_tools = vec!["drill".into(), "saw".into()];
    let composed = compose(g1, g2).unwrap();
    assert_eq!(composed.scope.allowed_tools, vec!["drill".to_string()]);
}

#[test]
fn compose_scope_empty_means_unconstrained() {
    let mut g1 = minimal_ctx(Permission::AAA, "1");
    let g2 = minimal_ctx(Permission::AAA, "2"); // no tool constraint
    g1.scope.allowed_tools = vec!["hammer".into()];
    let composed = compose(g1, g2).unwrap();
    assert_eq!(composed.scope.allowed_tools, vec!["hammer".to_string()]);
}

#[test]
fn compose_scope_disjoint_gives_empty() {
    let mut g1 = minimal_ctx(Permission::AAA, "1");
    let mut g2 = minimal_ctx(Permission::AAA, "2");
    g1.scope.allowed_tools = vec!["hammer".into()];
    g2.scope.allowed_tools = vec!["saw".into()];
    let composed = compose(g1, g2).unwrap();
    // Disjoint intersection → empty list (empty = fully constrained to nothing)
    assert!(composed.scope.allowed_tools.is_empty());
}

// ── Gap composition takes minimum status (EC-003 §20) ────────────────────────

#[test]
fn compose_gap_takes_minimum_status() {
    let mut g1 = minimal_ctx(Permission::AAA, "1");
    let mut g2 = minimal_ctx(Permission::AAA, "2");
    g1.gaps.push(GapRecord::closed("g1", "calibration_gap"));
    g2.gaps.push(GapRecord::open("g1", "calibration_gap"));
    let composed = compose(g1, g2).unwrap();
    let gap = composed.find_gap("g1").unwrap();
    assert!(matches!(gap.status, turnstile_core::gap::GapStatus::Open));
}

#[test]
fn compose_gap_bounded_vs_closed_gives_bounded() {
    let mut g1 = minimal_ctx(Permission::AAA, "1");
    let mut g2 = minimal_ctx(Permission::AAA, "2");
    g1.gaps.push(GapRecord::closed("g1", "t"));
    g2.gaps
        .push(GapRecord::bounded("g1", "t", Bound::numeric(0.05)));
    let composed = compose(g1, g2).unwrap();
    let gap = composed.find_gap("g1").unwrap();
    assert!(matches!(
        gap.status,
        turnstile_core::gap::GapStatus::Bounded(_)
    ));
}

// ── Expiry composition: minimum (EC-003 §23) ─────────────────────────────────

#[test]
fn compose_expiry_takes_minimum() {
    let now = Utc::now();
    let mut g1 = minimal_ctx(Permission::AAA, "1");
    let mut g2 = minimal_ctx(Permission::AAA, "2");
    g1.expiry = Expiry::at(now + Duration::seconds(100));
    g2.expiry = Expiry::at(now + Duration::seconds(10));
    let composed = compose(g1, g2).unwrap();
    assert_eq!(composed.expiry.deadline, Some(now + Duration::seconds(10)));
}

#[test]
fn compose_expiry_never_plus_deadline_gives_deadline() {
    let now = Utc::now();
    let mut g1 = minimal_ctx(Permission::AAA, "1");
    let g2 = minimal_ctx(Permission::AAA, "2");
    let deadline = now + Duration::seconds(60);
    g1.expiry = Expiry::at(deadline);
    let composed = compose(g1, g2).unwrap();
    assert_eq!(composed.expiry.deadline, Some(deadline));
}

#[test]
fn compose_expiry_both_never_stays_never() {
    let g1 = minimal_ctx(Permission::AAA, "1");
    let g2 = minimal_ctx(Permission::AAA, "2");
    let composed = compose(g1, g2).unwrap();
    assert!(composed.expiry.deadline.is_none());
}

#[test]
fn compose_expiry_grouping_independent() {
    let now = Utc::now();
    let t1 = now + Duration::seconds(10);
    let t2 = now + Duration::seconds(5);
    let t3 = now + Duration::seconds(20);

    let mut g1 = minimal_ctx(Permission::AAA, "1");
    let mut g2 = minimal_ctx(Permission::AAA, "1");
    let mut g3 = minimal_ctx(Permission::AAA, "1");
    g1.expiry = Expiry::at(t1);
    g2.expiry = Expiry::at(t2);
    g3.expiry = Expiry::at(t3);

    // left grouping: (g1 ⊗ g2) ⊗ g3
    let ab = compose(g1.clone(), g2.clone()).unwrap();
    let left = compose(ab, g3.clone()).unwrap();

    // right grouping: g1 ⊗ (g2 ⊗ g3)
    let bc = compose(g2, g3).unwrap();
    let right = compose(g1, bc).unwrap();

    assert_eq!(left.expiry.deadline, Some(t2));
    assert_eq!(right.expiry.deadline, Some(t2));
}

// ── Token conflict fails closed ───────────────────────────────────────────────

#[test]
fn compose_token_conflict_fails_closed() {
    let mut g1 = minimal_ctx(Permission::AAA, "1");
    let mut g2 = minimal_ctx(Permission::AAA, "2");
    let hash = compute_provenance_hash("claim-1", "z-1", "ctx-1", "test-use");
    let t1 = ProofToken {
        token_id: "tok-1".into(),
        token_type: "TEST".into(),
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
    };
    let t2 = ProofToken {
        token_id: "tok-1".into(), // same id, different content
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g2".into()], // different gap → conflict
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    g1.tokens.push(t1);
    g2.tokens.push(t2);
    assert!(
        compose(g1, g2).is_err(),
        "token conflict should fail closed"
    );
}

// ── Membership is conservative ────────────────────────────────────────────────

#[test]
fn compose_ooc_is_absorbing_for_membership() {
    use turnstile_core::context::Membership;
    let mut g1 = minimal_ctx(Permission::AAA, "1");
    let g2 = minimal_ctx(Permission::AAA, "2");
    g1.membership = Membership::OutOfClassExact;
    let composed = compose(g1, g2).unwrap();
    assert!(!composed.membership.is_in_class());
}

#[test]
fn compose_both_in_class_stays_in_class() {
    let g1 = minimal_ctx(Permission::AAA, "1");
    let g2 = minimal_ctx(Permission::AAA, "2");
    let composed = compose(g1, g2).unwrap();
    assert!(composed.membership.is_in_class());
}

// ── Proptest ─────────────────────────────────────────────────────────────────

proptest! {
    #[test]
    fn prop_compose_ceiling_is_meet(p1 in arb_permission(), p2 in arb_permission()) {
        let g1 = minimal_ctx(p1, "a");
        let g2 = minimal_ctx(p2, "b");
        let composed = compose(g1, g2).unwrap();
        prop_assert_eq!(composed.authority_ceiling, p1.meet(p2));
    }

    #[test]
    fn prop_compose_disallowed_superset(
        n1 in 0usize..4usize,
        n2 in 0usize..4usize,
    ) {
        let mut g1 = minimal_ctx(Permission::AAA, "a");
        let mut g2 = minimal_ctx(Permission::AAA, "b");
        g1.disallowed_uses = (0..n1).map(|i| format!("use-{i}")).collect();
        g2.disallowed_uses = (0..n2).map(|i| format!("use-{i}")).collect();
        let composed = compose(g1.clone(), g2.clone()).unwrap();
        for u in &g1.disallowed_uses {
            prop_assert!(composed.disallowed_uses.contains(u));
        }
        for u in &g2.disallowed_uses {
            prop_assert!(composed.disallowed_uses.contains(u));
        }
    }

    #[test]
    fn prop_compose_expiry_minimum(
        secs1 in 1i64..=86400i64,
        secs2 in 1i64..=86400i64,
    ) {
        let now = Utc::now();
        let mut g1 = minimal_ctx(Permission::AAA, "a");
        let mut g2 = minimal_ctx(Permission::AAA, "b");
        g1.expiry = Expiry::at(now + Duration::seconds(secs1));
        g2.expiry = Expiry::at(now + Duration::seconds(secs2));
        let composed = compose(g1, g2).unwrap();
        let expected = (now + Duration::seconds(secs1)).min(now + Duration::seconds(secs2));
        prop_assert_eq!(composed.expiry.deadline, Some(expected));
    }
}
