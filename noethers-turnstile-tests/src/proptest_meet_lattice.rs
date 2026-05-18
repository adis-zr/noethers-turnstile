use noethers_turnstile_core::permission::Permission;
/// Property test: Permission lattice meet algebra.
///
/// The permission lattice is a finite total order (chain lattice).
/// The meet operator must satisfy the following algebraic laws:
///   1. Non-promotion:  meet(p, q) ≤ p  and  meet(p, q) ≤ q
///   2. Commutativity:  meet(p, q) = meet(q, p)
///   3. Associativity:  meet(meet(p, q), r) = meet(p, meet(q, r))
///   4. Idempotence:    meet(p, p) = p
///   5. Identity (AAA): meet(p, AAA) = p
///   6. Absorbing (OOC): meet(p, OOC) = OOC
///   7. Totality: meet is defined for all 12×12 = 144 pairs
///   8. Antisymmetry: meet(p, q) = p iff p ≤ q  (in a chain)
///
/// These laws collectively prove that the permission lattice is sound
/// as a proof-theoretic judgment algebra (the meet must be the infimum
/// of the partial order, not merely a minimum).
///
/// Spec reference: EC-001 §2 (Permission outcomes, total linear order).
use proptest::prelude::*;

const ALL_PERMISSIONS: [Permission; 12] = [
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

// ── Exhaustive 144-pair meet table ────────────────────────────────────────────

#[test]
fn meet_table_non_promotion_144_pairs() {
    for &p in &ALL_PERMISSIONS {
        for &q in &ALL_PERMISSIONS {
            let m = p.meet(q);
            assert!(m <= p, "meet({p}, {q}) = {m} violates m ≤ p");
            assert!(m <= q, "meet({p}, {q}) = {m} violates m ≤ q");
        }
    }
}

#[test]
fn meet_table_commutativity_144_pairs() {
    for &p in &ALL_PERMISSIONS {
        for &q in &ALL_PERMISSIONS {
            assert_eq!(p.meet(q), q.meet(p), "meet({p}, {q}) ≠ meet({q}, {p})");
        }
    }
}

#[test]
fn meet_table_idempotence_12_elements() {
    for &p in &ALL_PERMISSIONS {
        assert_eq!(p.meet(p), p, "meet({p}, {p}) ≠ {p}");
    }
}

#[test]
fn meet_table_identity_aaa() {
    for &p in &ALL_PERMISSIONS {
        assert_eq!(p.meet(Permission::AAA), p, "meet({p}, AAA) ≠ {p}");
        assert_eq!(Permission::AAA.meet(p), p, "meet(AAA, {p}) ≠ {p}");
    }
}

#[test]
fn meet_table_absorbing_ooc() {
    for &p in &ALL_PERMISSIONS {
        assert_eq!(
            p.meet(Permission::OOC),
            Permission::OOC,
            "meet({p}, OOC) ≠ OOC"
        );
        assert_eq!(
            Permission::OOC.meet(p),
            Permission::OOC,
            "meet(OOC, {p}) ≠ OOC"
        );
    }
}

/// For a total order (chain), meet(p, q) = min(p, q).
/// Verify the meet matches the natural ordering.
#[test]
fn meet_equals_min_for_all_pairs() {
    for &p in &ALL_PERMISSIONS {
        for &q in &ALL_PERMISSIONS {
            let expected = p.min(q);
            let actual = p.meet(q);
            assert_eq!(
                actual, expected,
                "meet({p}, {q}) = {actual} ≠ min({p}, {q}) = {expected}"
            );
        }
    }
}

/// Associativity: must hold for all 12³ = 1728 triples.
#[test]
fn meet_table_associativity_all_triples() {
    for &p in &ALL_PERMISSIONS {
        for &q in &ALL_PERMISSIONS {
            for &r in &ALL_PERMISSIONS {
                let left = p.meet(q).meet(r);
                let right = p.meet(q.meet(r));
                assert_eq!(
                    left, right,
                    "meet associativity failed: meet(meet({p},{q}),{r}) = {left} ≠ meet({p},meet({q},{r})) = {right}"
                );
            }
        }
    }
}

/// Antisymmetry in a chain: meet(p, q) = p iff p ≤ q.
#[test]
fn meet_antisymmetry_exhaustive() {
    for &p in &ALL_PERMISSIONS {
        for &q in &ALL_PERMISSIONS {
            if p <= q {
                assert_eq!(
                    p.meet(q),
                    p,
                    "antisymmetry: {p} ≤ {q} but meet({p},{q}) = {} ≠ {p}",
                    p.meet(q)
                );
            } else {
                assert_eq!(
                    p.meet(q),
                    q,
                    "antisymmetry: {p} > {q} but meet({p},{q}) = {} ≠ {q}",
                    p.meet(q)
                );
            }
        }
    }
}

/// meet_n over all 12 elements = OOC (bottom).
#[test]
fn meet_n_all_elements_is_ooc() {
    let result = Permission::meet_n(ALL_PERMISSIONS.iter().copied());
    assert_eq!(result, Some(Permission::OOC));
}

/// meet_n in any order produces the same result (commutativity and associativity
/// of meet imply fold-order independence).
#[test]
fn meet_n_order_independent() {
    let perms = [
        Permission::DIA,
        Permission::REV,
        Permission::AEX,
        Permission::ETA,
    ];
    let forward = Permission::meet_n(perms.iter().copied());
    let backward = Permission::meet_n(perms.iter().copied().rev());
    assert_eq!(forward, backward, "meet_n must be order-independent");
}

/// The strict ordering: OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA < REV < AEX < ALR < AAA.
#[test]
fn strict_total_order_12_elements() {
    let chain: Vec<Permission> = Permission::descending().collect();
    // descending() returns AAA first, OOC last.
    for i in 0..chain.len() - 1 {
        // chain[i] > chain[i+1] in descending order.
        assert!(
            chain[i] > chain[i + 1],
            "expected {} > {} in descending chain",
            chain[i],
            chain[i + 1]
        );
    }
}

// ── Proptest: algebraic laws ──────────────────────────────────────────────────

proptest! {
    #[test]
    fn prop_meet_non_promotion(p in arb_permission(), q in arb_permission()) {
        let m = p.meet(q);
        prop_assert!(m <= p, "meet({p},{q}) = {m} > {p}");
        prop_assert!(m <= q, "meet({p},{q}) = {m} > {q}");
    }

    #[test]
    fn prop_meet_commutative(p in arb_permission(), q in arb_permission()) {
        prop_assert_eq!(p.meet(q), q.meet(p));
    }

    #[test]
    fn prop_meet_associative(
        p in arb_permission(),
        q in arb_permission(),
        r in arb_permission(),
    ) {
        prop_assert_eq!(p.meet(q).meet(r), p.meet(q.meet(r)));
    }

    #[test]
    fn prop_meet_idempotent(p in arb_permission()) {
        prop_assert_eq!(p.meet(p), p);
    }

    #[test]
    fn prop_meet_n_never_exceeds_any_input(
        perms in prop::collection::vec(arb_permission(), 1..13),
    ) {
        let result = Permission::meet_n(perms.iter().copied()).unwrap();
        for &p in &perms {
            prop_assert!(result <= p, "meet_n result {result} exceeds input {p}");
        }
    }

    #[test]
    fn prop_meet_n_equals_sequential_fold(
        perms in prop::collection::vec(arb_permission(), 1..13),
    ) {
        let n_result = Permission::meet_n(perms.iter().copied()).unwrap();
        let fold_result = perms.iter().copied().reduce(Permission::meet).unwrap();
        prop_assert_eq!(n_result, fold_result);
    }

    /// In a total order, p.meet(q) = p iff p ≤ q.
    #[test]
    fn prop_meet_is_min_for_total_order(p in arb_permission(), q in arb_permission()) {
        let m = p.meet(q);
        if p <= q {
            prop_assert_eq!(m, p);
        } else {
            prop_assert_eq!(m, q);
        }
    }
}
