/// EC-045 — Permission triples exhaustive (T8/T9/T10, EC-001 §16).
///
/// Ported from:
///   test_ec003a_permission_triples.py  (5194 tests — 1728 exhaustive triples)
///
/// ec003a_permission_order.rs samples triples but does not enumerate all 12³=1728.
/// This file provides the full exhaustive enumeration for:
///
///   TR1 — Associativity: meet(meet(a,b),c) = meet(a,meet(b,c)) for all 1728 triples
///   TR2 — meet_n order-independence: meet_n([a,b,c]) = meet_n([c,b,a]) for all 1728
///   TR3 — Left-fold = right-fold = meet_n for all 1728 triples
///   TR4 — meet_n idempotence on duplicate: meet_n([a,b,c,a,b,c]) = meet_n([a,b,c])
///   TR5 — Split-fold: meet_n([a,b,c]) = meet_n([meet_n([a,b]), c])
use turnstile_core::permission::Permission;

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

// ── TR1: Associativity over all 1728 triples ──────────────────────────────────

#[test]
fn tr1_meet_associativity_all_1728_triples() {
    let mut failures = 0u32;
    for &a in &ALL {
        for &b in &ALL {
            for &c in &ALL {
                let lhs = a.meet(b).meet(c);
                let rhs = a.meet(b.meet(c));
                if lhs != rhs {
                    eprintln!("TR1 FAIL: meet(meet({a:?},{b:?}),{c:?})={lhs:?} ≠ meet({a:?},meet({b:?},{c:?}))={rhs:?}");
                    failures += 1;
                }
            }
        }
    }
    assert_eq!(
        failures, 0,
        "TR1: associativity failed on {failures} of 1728 triples"
    );
}

// ── TR2: meet_n order-independence over all 1728 triples (all 6 permutations) ─

#[test]
fn tr2_meet_n_order_independent_all_1728_triples() {
    let mut failures = 0u32;
    for &a in &ALL {
        for &b in &ALL {
            for &c in &ALL {
                let canonical = Permission::meet_n([a, b, c]).unwrap();
                // all 6 permutations of (a, b, c)
                let perms = [
                    [a, b, c],
                    [a, c, b],
                    [b, a, c],
                    [b, c, a],
                    [c, a, b],
                    [c, b, a],
                ];
                for perm in perms {
                    let result = Permission::meet_n(perm).unwrap();
                    if result != canonical {
                        eprintln!(
                            "TR2 FAIL: meet_n({perm:?})={result:?} ≠ canonical {canonical:?}"
                        );
                        failures += 1;
                    }
                }
            }
        }
    }
    assert_eq!(
        failures, 0,
        "TR2: order-independence failed on {failures} triple-permutation checks"
    );
}

// ── TR3: Left-fold = right-fold = meet_n for all 1728 triples ─────────────────

#[test]
fn tr3_left_fold_right_fold_meet_n_all_1728() {
    let mut failures = 0u32;
    for &a in &ALL {
        for &b in &ALL {
            for &c in &ALL {
                let left_fold = a.meet(b).meet(c);
                let right_fold = a.meet(b.meet(c));
                let meet_n = Permission::meet_n([a, b, c]).unwrap();

                if left_fold != meet_n || right_fold != meet_n {
                    eprintln!(
                        "TR3 FAIL: ({a:?},{b:?},{c:?}): left={left_fold:?} right={right_fold:?} meet_n={meet_n:?}"
                    );
                    failures += 1;
                }
            }
        }
    }
    assert_eq!(
        failures, 0,
        "TR3: left-fold/right-fold/meet_n disagreed on {failures} triples"
    );
}

// ── TR4: Idempotence on duplicate inputs ──────────────────────────────────────

#[test]
fn tr4_meet_n_idempotent_on_duplicate_triples() {
    let mut failures = 0u32;
    for &a in &ALL {
        for &b in &ALL {
            for &c in &ALL {
                let base = Permission::meet_n([a, b, c]).unwrap();
                let doubled = Permission::meet_n([a, b, c, a, b, c]).unwrap();
                if base != doubled {
                    eprintln!("TR4 FAIL: meet_n([{a:?},{b:?},{c:?}])={base:?} ≠ meet_n(doubled)={doubled:?}");
                    failures += 1;
                }
            }
        }
    }
    assert_eq!(
        failures, 0,
        "TR4: idempotence on duplicates failed on {failures} triples"
    );
}

// ── TR5: Split-fold invariant ─────────────────────────────────────────────────

#[test]
fn tr5_split_fold_all_1728_triples() {
    let mut failures = 0u32;
    for &a in &ALL {
        for &b in &ALL {
            for &c in &ALL {
                let full = Permission::meet_n([a, b, c]).unwrap();
                let ab = Permission::meet_n([a, b]).unwrap();
                let split = Permission::meet_n([ab, c]).unwrap();
                if full != split {
                    eprintln!(
                        "TR5 FAIL: meet_n([{a:?},{b:?},{c:?}])={full:?} ≠ meet_n([meet_n([{a:?},{b:?}]),{c:?}])={split:?}"
                    );
                    failures += 1;
                }
            }
        }
    }
    assert_eq!(
        failures, 0,
        "TR5: split-fold failed on {failures} triples"
    );
}
