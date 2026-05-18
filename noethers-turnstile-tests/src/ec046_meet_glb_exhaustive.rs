/// EC-046 — Meet GLB property exhaustive (T8, EC-001 §16).
///
/// meet(a,b) is the *greatest* lower bound — not just *a* lower bound.
/// For every x such that x≤a and x≤b, it must hold that x≤meet(a,b).
///
/// ec003a verifies meet(a,b)≤a and meet(a,b)≤b (lower bound), but does not
/// verify the GLB property (≥ all common lower bounds) for all 144 pairs.
///
///   GLB1 — Lower bound: meet(a,b) ≤ a and meet(a,b) ≤ b for all 144 pairs
///   GLB2 — Greatest: ∀x. x≤a ∧ x≤b → x≤meet(a,b) for all 144 pairs
///   GLB3 — Unique: no m > meet(a,b) is also a lower bound of (a,b)
///   GLB4 — meet(a,a) = a for all 12 (idempotent GLB)
///   GLB5 — GLB of {a} is a itself (degenerate case)
///   Prop  — GLB property holds for random triples (proptest)
use proptest::prelude::*;
use noethers_noethers_turnstile_core::permission::Permission;

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

// ── GLB1: meet(a,b) ≤ a and meet(a,b) ≤ b for all 144 pairs ─────────────────

#[test]
fn glb1_meet_is_lower_bound_all_144_pairs() {
    let mut failures = 0u32;
    for &a in &ALL {
        for &b in &ALL {
            let m = a.meet(b);
            if m > a {
                eprintln!("GLB1 FAIL: meet({a:?},{b:?})={m:?} is not ≤ {a:?}");
                failures += 1;
            }
            if m > b {
                eprintln!("GLB1 FAIL: meet({a:?},{b:?})={m:?} is not ≤ {b:?}");
                failures += 1;
            }
        }
    }
    assert_eq!(failures, 0, "GLB1: lower-bound failed on {failures} checks");
}

// ── GLB2: ∀x. x≤a ∧ x≤b → x≤meet(a,b) for all 144 pairs × 12 witnesses ──────

#[test]
fn glb2_meet_is_greatest_lower_bound_all_1728_checks() {
    let mut failures = 0u32;
    for &a in &ALL {
        for &b in &ALL {
            let m = a.meet(b);
            for &x in &ALL {
                // If x is a common lower bound of a and b, then x ≤ meet(a,b)
                if x <= a && x <= b && (x > m) {
                    eprintln!("GLB2 FAIL: x={x:?} ≤ {a:?} and x ≤ {b:?} but x ≰ meet={m:?}");
                    failures += 1;
                }
            }
        }
    }
    assert_eq!(
        failures, 0,
        "GLB2: GLB property violated on {failures} of 1728 checks"
    );
}

// ── GLB3: No m > meet(a,b) is also a lower bound of (a,b) ────────────────────

#[test]
fn glb3_no_strictly_greater_lower_bound_exists() {
    let mut failures = 0u32;
    for &a in &ALL {
        for &b in &ALL {
            let m = a.meet(b);
            // Check that no m2 > m satisfies m2 ≤ a AND m2 ≤ b
            for &m2 in &ALL {
                if m2 > m && m2 <= a && m2 <= b {
                    eprintln!("GLB3 FAIL: m2={m2:?} > meet={m:?} but m2 ≤ {a:?} and m2 ≤ {b:?}");
                    failures += 1;
                }
            }
        }
    }
    assert_eq!(
        failures, 0,
        "GLB3: found {failures} pairs with a strictly greater lower bound than meet(a,b)"
    );
}

// ── GLB4: meet(a,a) = a (idempotent) ─────────────────────────────────────────

#[test]
fn glb4_meet_idempotent_all_12() {
    for &a in &ALL {
        assert_eq!(a.meet(a), a, "GLB4: meet({a:?},{a:?}) must equal {a:?}");
    }
}

// ── GLB5: GLB of singleton = identity ────────────────────────────────────────

#[test]
fn glb5_meet_n_singleton_is_identity() {
    for &a in &ALL {
        let result = Permission::meet_n([a]).unwrap();
        assert_eq!(result, a, "GLB5: meet_n([{a:?}]) must equal {a:?}");
    }
}

// ── Proptest: GLB property for random triples ─────────────────────────────────

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
    fn prop_glb_property_random_triples(
        a in arb_permission(),
        b in arb_permission(),
        x in arb_permission(),
    ) {
        let m = a.meet(b);
        // If x ≤ a and x ≤ b, then x must be ≤ meet(a,b)
        if x <= a && x <= b {
            prop_assert!(x <= m, "GLB: x={x:?} ≤ {a:?} and ≤ {b:?} but x ≰ meet={m:?}");
        }
        // meet(a,b) must be a lower bound
        prop_assert!(m <= a, "lower bound: meet({a:?},{b:?})={m:?} must be ≤ {a:?}");
        prop_assert!(m <= b, "lower bound: meet({a:?},{b:?})={m:?} must be ≤ {b:?}");
    }
}
