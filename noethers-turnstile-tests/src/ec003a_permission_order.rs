/// EC-003A — Permission order: reflexivity, antisymmetry, transitivity, meet table.
///
/// Ported from hilbert-flow/admissibility-atlas/tests/test_ec003a_permission_order.py
/// and test_ec003a_permission_pairwise.py.
///
/// Properties proved:
///   T8  — Permission meet non-promotion: meet(a,b) ≤ a and meet(a,b) ≤ b
///   T9  — N-ary composition non-promotion (meet_n)
///   T10 — Composition monotonicity (meet is idempotent, associative, commutative)
use proptest::prelude::*;
use noethers_turnstile_core::permission::Permission;

pub fn arb_permission() -> impl Strategy<Value = Permission> {
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

pub const ALL: [Permission; 12] = [
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

// ── Exhaustive order tests (finite domain, 12 elements) ──────────────────────

#[test]
fn chain_has_12_elements() {
    assert_eq!(Permission::descending().count(), 12);
}

#[test]
fn ooc_is_minimum() {
    for p in ALL {
        assert!(Permission::OOC <= p, "OOC should be ≤ {p}");
    }
}

#[test]
fn aaa_is_maximum() {
    for p in ALL {
        assert!(p <= Permission::AAA, "{p} should be ≤ AAA");
    }
}

#[test]
fn total_order_correct() {
    // OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA < REV < AEX < ALR < AAA
    let chain: Vec<Permission> = Permission::descending()
        .collect::<Vec<_>>()
        .into_iter()
        .rev()
        .collect();
    for i in 0..chain.len() {
        for j in 0..chain.len() {
            if i < j {
                assert!(chain[i] < chain[j], "{} should be < {}", chain[i], chain[j]);
            } else if i == j {
                assert!(chain[i] == chain[j]);
            } else {
                assert!(chain[i] > chain[j]);
            }
        }
    }
}

#[test]
fn total_order_every_pair_comparable() {
    for a in ALL {
        for b in ALL {
            assert!(a <= b || b <= a, "incomparable: {a} and {b}");
        }
    }
}

#[test]
fn reflexivity_exhaustive() {
    for p in ALL {
        assert!(p <= p, "reflexivity failed for {p}");
    }
}

#[test]
fn antisymmetry_exhaustive() {
    for a in ALL {
        for b in ALL {
            if a <= b && b <= a {
                assert_eq!(
                    a, b,
                    "antisymmetry failed: {a} ≤ {b} and {b} ≤ {a} but {a} ≠ {b}"
                );
            }
        }
    }
}

#[test]
fn transitivity_exhaustive() {
    for a in ALL {
        for b in ALL {
            for c in ALL {
                if a <= b && b <= c {
                    assert!(a <= c, "transitivity failed: {a} ≤ {b} ≤ {c} but {a} ≰ {c}");
                }
            }
        }
    }
}

// ── Specific cluster ordering from EC-003 §4 ─────────────────────────────────

#[test]
fn expired_refused_unsupported_chain() {
    assert!(Permission::EXP <= Permission::REF);
    assert!(Permission::REF <= Permission::UNS);
    assert!(Permission::EXP <= Permission::UNS);
}

#[test]
fn control_cluster_eta_esc_rol() {
    assert!(Permission::ETA <= Permission::ESC);
    assert!(Permission::ESC <= Permission::ROL);
    assert!(Permission::ETA <= Permission::ROL);
}

#[test]
fn approval_cluster_aex_alr_aaa() {
    assert!(Permission::AEX <= Permission::ALR);
    assert!(Permission::ALR <= Permission::AAA);
    assert!(Permission::AEX <= Permission::AAA);
}

// ── Pairwise meet table (144 pairs, EC-003 §6–7) ─────────────────────────────

#[test]
fn meet_all_144_pairs() {
    for a in ALL {
        for b in ALL {
            let m = a.meet(b);
            // Lower-bound both
            assert!(m <= a, "meet({a},{b})={m} not ≤ {a}");
            assert!(m <= b, "meet({a},{b})={m} not ≤ {b}");
            // Greatest lower bound
            for x in ALL {
                if x <= a && x <= b {
                    assert!(
                        x <= m,
                        "{x} is a lower bound of ({a},{b}) but {x} ≰ meet={m}"
                    );
                }
            }
        }
    }
}

#[test]
fn meet_commutative_all_pairs() {
    for a in ALL {
        for b in ALL {
            assert_eq!(a.meet(b), b.meet(a), "commutativity failed for ({a},{b})");
        }
    }
}

#[test]
fn meet_idempotent_all() {
    for a in ALL {
        assert_eq!(a.meet(a), a, "idempotence failed for {a}");
    }
}

#[test]
fn ooc_is_absorbing() {
    for p in ALL {
        assert_eq!(Permission::OOC.meet(p), Permission::OOC);
        assert_eq!(p.meet(Permission::OOC), Permission::OOC);
    }
}

#[test]
fn aaa_is_identity() {
    for p in ALL {
        assert_eq!(Permission::AAA.meet(p), p);
        assert_eq!(p.meet(Permission::AAA), p);
    }
}

#[test]
fn cross_kind_edge_cases() {
    assert_eq!(Permission::OOC.meet(Permission::EXP), Permission::OOC);
    assert_eq!(Permission::OOC.meet(Permission::REF), Permission::OOC);
    assert_eq!(Permission::EXP.meet(Permission::REF), Permission::EXP);
    assert_eq!(Permission::REF.meet(Permission::ESC), Permission::REF);
    assert_eq!(Permission::UNS.meet(Permission::ESC), Permission::UNS);
    assert_eq!(Permission::ETA.meet(Permission::ROL), Permission::ETA);
    assert_eq!(Permission::ROL.meet(Permission::AAA), Permission::ROL);
    assert_eq!(Permission::DIA.meet(Permission::AEX), Permission::DIA);
}

// ── Triple associativity (1728 triples, EC-003 §8) ───────────────────────────

#[test]
fn meet_associative_all_triples() {
    for a in ALL {
        for b in ALL {
            for c in ALL {
                let left = a.meet(b).meet(c);
                let right = a.meet(b.meet(c));
                assert_eq!(
                    left, right,
                    "associativity failed: meet(meet({a},{b}),{c})={left} ≠ meet({a},meet({b},{c}))={right}"
                );
            }
        }
    }
}

// ── N-ary meet: meet_n (EC-003 §8) ───────────────────────────────────────────

#[test]
fn meet_n_singleton() {
    for p in ALL {
        assert_eq!(Permission::meet_n(std::iter::once(p)), Some(p));
    }
}

#[test]
fn meet_n_empty_is_none() {
    assert_eq!(Permission::meet_n(std::iter::empty()), None);
}

#[test]
fn meet_n_all_ooc_gives_ooc() {
    let result = Permission::meet_n(std::iter::repeat_n(Permission::OOC, 10));
    assert_eq!(result, Some(Permission::OOC));
}

#[test]
fn meet_n_all_aaa_gives_aaa() {
    let result = Permission::meet_n(std::iter::repeat_n(Permission::AAA, 10));
    assert_eq!(result, Some(Permission::AAA));
}

#[test]
fn meet_n_single_ooc_dominates() {
    let xs: Vec<Permission> = (0..9)
        .map(|_| Permission::AAA)
        .chain(std::iter::once(Permission::OOC))
        .collect();
    assert_eq!(Permission::meet_n(xs.into_iter()), Some(Permission::OOC));
}

// ── Proptest: shuffle invariance and split-fold ───────────────────────────────

proptest! {
    #[test]
    fn prop_meet_commutative(a in arb_permission(), b in arb_permission()) {
        prop_assert_eq!(a.meet(b), b.meet(a));
    }

    #[test]
    fn prop_meet_lower_bounds_both(a in arb_permission(), b in arb_permission()) {
        let m = a.meet(b);
        prop_assert!(m <= a, "meet({a},{b})={m} not ≤ {a}");
        prop_assert!(m <= b, "meet({a},{b})={m} not ≤ {b}");
    }

    #[test]
    fn prop_meet_associative(
        a in arb_permission(),
        b in arb_permission(),
        c in arb_permission(),
    ) {
        prop_assert_eq!(a.meet(b).meet(c), a.meet(b.meet(c)));
    }

    #[test]
    fn prop_meet_n_shuffle_invariant(
        xs in prop::collection::vec(arb_permission(), 1..=20),
    ) {
        let baseline = Permission::meet_n(xs.iter().copied()).unwrap();
        // Reverse
        let reversed: Vec<_> = xs.iter().copied().rev().collect();
        let rev_result = Permission::meet_n(reversed.into_iter()).unwrap();
        prop_assert_eq!(baseline, rev_result);
    }

    #[test]
    fn prop_meet_n_idempotent_doubles(
        xs in prop::collection::vec(arb_permission(), 1..=10),
    ) {
        let baseline = Permission::meet_n(xs.iter().copied()).unwrap();
        let doubled: Vec<_> = xs.iter().copied().chain(xs.iter().copied()).collect();
        let doubled_result = Permission::meet_n(doubled.into_iter()).unwrap();
        prop_assert_eq!(baseline, doubled_result);
    }

    #[test]
    fn prop_meet_n_split_fold(
        xs in prop::collection::vec(arb_permission(), 2..=20),
        split_idx in 1usize..20usize,
    ) {
        let k = (split_idx % (xs.len() - 1)) + 1;
        let left = Permission::meet_n(xs[..k].iter().copied()).unwrap();
        let right = Permission::meet_n(xs[k..].iter().copied()).unwrap();
        let split_result = left.meet(right);
        let direct = Permission::meet_n(xs.iter().copied()).unwrap();
        prop_assert_eq!(split_result, direct);
    }

    #[test]
    fn prop_total_order(a in arb_permission(), b in arb_permission()) {
        prop_assert!(a <= b || b <= a, "incomparable: {a} and {b}");
    }
}
