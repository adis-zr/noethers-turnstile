/// EC-003G — Gap status algebra: total order, min_status, bound types,
///           RequiredStatus satisfiability, composition minimum.
///
/// Covers theorems:
///   T5  — Gap requirement soundness: GapStatus order is correct
///   T6  — No proof, no license: Open satisfies nothing except trivially
///
/// Gap status total order: Open < Bounded < Closed
/// RequiredStatus: BoundedRequired accepts {Bounded, Closed}; ClosedRequired accepts {Closed}
use proptest::prelude::*;
use turnstile_core::gap::{Bound, BoundKind, GapRecord, GapStatus, RequiredStatus};

// ── GapStatus total order (Open < Bounded < Closed) ─────────────────────────

#[test]
fn gap_status_order_open_lt_bounded_lt_closed() {
    assert!(GapStatus::Open.rank() < GapStatus::Bounded(Bound::numeric(0.0)).rank());
    assert!(GapStatus::Bounded(Bound::numeric(0.0)).rank() < GapStatus::Closed.rank());
}

#[test]
fn gap_status_rank_values() {
    assert_eq!(GapStatus::Open.rank(), 0);
    assert_eq!(GapStatus::Bounded(Bound::infinity()).rank(), 1);
    assert_eq!(GapStatus::Closed.rank(), 2);
}

// ── min_status: returns the lower of two statuses ────────────────────────────

#[test]
fn min_status_open_bounded_gives_open() {
    let result = GapStatus::Open.min_status(GapStatus::Bounded(Bound::numeric(1.0)));
    assert_eq!(result.rank(), GapStatus::Open.rank());
}

#[test]
fn min_status_bounded_closed_gives_bounded() {
    let result = GapStatus::Bounded(Bound::numeric(0.05)).min_status(GapStatus::Closed);
    assert_eq!(
        result.rank(),
        GapStatus::Bounded(Bound::numeric(0.0)).rank()
    );
}

#[test]
fn min_status_open_closed_gives_open() {
    let result = GapStatus::Open.min_status(GapStatus::Closed);
    assert_eq!(result.rank(), GapStatus::Open.rank());
}

#[test]
fn min_status_commutative_all_pairs() {
    let statuses = [
        GapStatus::Open,
        GapStatus::Bounded(Bound::numeric(0.1)),
        GapStatus::Closed,
    ];
    for a in &statuses {
        for b in &statuses {
            let ab = a.clone().min_status(b.clone());
            let ba = b.clone().min_status(a.clone());
            assert_eq!(
                ab.rank(),
                ba.rank(),
                "min_status not commutative: {:?} vs {:?}",
                a,
                b
            );
        }
    }
}

#[test]
fn min_status_idempotent_all() {
    let statuses = [
        GapStatus::Open,
        GapStatus::Bounded(Bound::numeric(0.5)),
        GapStatus::Closed,
    ];
    for s in &statuses {
        let result = s.clone().min_status(s.clone());
        assert_eq!(
            result.rank(),
            s.rank(),
            "min_status not idempotent for {:?}",
            s
        );
    }
}

// ── RequiredStatus satisfiability ────────────────────────────────────────────

#[test]
fn bounded_required_accepts_bounded_and_closed() {
    assert!(RequiredStatus::BoundedRequired.satisfied_by(&GapStatus::Bounded(Bound::numeric(0.1))));
    assert!(RequiredStatus::BoundedRequired.satisfied_by(&GapStatus::Bounded(Bound::infinity())));
    assert!(RequiredStatus::BoundedRequired.satisfied_by(&GapStatus::Closed));
}

#[test]
fn bounded_required_rejects_open() {
    assert!(!RequiredStatus::BoundedRequired.satisfied_by(&GapStatus::Open));
}

#[test]
fn closed_required_accepts_only_closed() {
    assert!(RequiredStatus::ClosedRequired.satisfied_by(&GapStatus::Closed));
    assert!(!RequiredStatus::ClosedRequired.satisfied_by(&GapStatus::Open));
    assert!(!RequiredStatus::ClosedRequired.satisfied_by(&GapStatus::Bounded(Bound::numeric(0.0))));
    assert!(!RequiredStatus::ClosedRequired.satisfied_by(&GapStatus::Bounded(Bound::infinity())));
}

// ── Bound types are structured ────────────────────────────────────────────────

#[test]
fn bound_numeric_stores_value() {
    let b = Bound::numeric(0.05);
    assert!(matches!(b.kind, BoundKind::Numeric(v) if (v - 0.05).abs() < f64::EPSILON));
    assert!(b.units.is_none());
}

#[test]
fn bound_numeric_with_units() {
    let b = Bound::numeric_with_units(std::f64::consts::PI, "radians");
    assert!(matches!(b.kind, BoundKind::Numeric(_)));
    assert_eq!(b.units.as_deref(), Some("radians"));
}

#[test]
fn bound_set_valued_stores_values() {
    let b = Bound::set_valued(vec!["a".into(), "b".into()]);
    assert!(
        matches!(b.kind, BoundKind::SetValued(ref v) if v == &vec!["a".to_string(), "b".to_string()])
    );
}

#[test]
fn bound_infinity_is_distinct() {
    let b = Bound::infinity();
    assert!(matches!(b.kind, BoundKind::Infinity));
}

// ── GapRecord constructors ────────────────────────────────────────────────────

#[test]
fn gap_record_open_starts_open() {
    let r = GapRecord::open("g1", "calibration_gap");
    assert!(matches!(r.status, GapStatus::Open));
    assert_eq!(r.gap_id, "g1");
    assert_eq!(r.gap_type, "calibration_gap");
}

#[test]
fn gap_record_bounded_starts_bounded() {
    let r = GapRecord::bounded("g2", "freshness_gap", Bound::numeric(0.1));
    assert!(matches!(r.status, GapStatus::Bounded(_)));
}

#[test]
fn gap_record_closed_starts_closed() {
    let r = GapRecord::closed("g3", "scope_gap");
    assert!(matches!(r.status, GapStatus::Closed));
}

// ── GapStatus composition: min_status is associative ─────────────────────────

#[test]
fn min_status_associative_all_triples() {
    let statuses = [
        GapStatus::Open,
        GapStatus::Bounded(Bound::numeric(0.1)),
        GapStatus::Closed,
    ];
    for a in &statuses {
        for b in &statuses {
            for c in &statuses {
                let left = a.clone().min_status(b.clone()).min_status(c.clone());
                let right = a.clone().min_status(b.clone().min_status(c.clone()));
                assert_eq!(
                    left.rank(),
                    right.rank(),
                    "min_status not associative: {:?} {:?} {:?}",
                    a,
                    b,
                    c
                );
            }
        }
    }
}

// ── Proptest: min_status is commutative and idempotent ────────────────────────

fn arb_gap_status() -> impl Strategy<Value = GapStatus> {
    prop_oneof![
        Just(GapStatus::Open),
        (0.0f64..=1.0f64).prop_map(|v| GapStatus::Bounded(Bound::numeric(v))),
        Just(GapStatus::Closed),
    ]
}

proptest! {
    #[test]
    fn prop_min_status_commutative(
        a in arb_gap_status(),
        b in arb_gap_status(),
    ) {
        let ab = a.clone().min_status(b.clone());
        let ba = b.min_status(a);
        prop_assert_eq!(ab.rank(), ba.rank());
    }

    #[test]
    fn prop_min_status_lower_bounds_both(
        a in arb_gap_status(),
        b in arb_gap_status(),
    ) {
        let m = a.clone().min_status(b.clone());
        prop_assert!(m.rank() <= a.rank(), "min_status exceeded a");
        prop_assert!(m.rank() <= b.rank(), "min_status exceeded b");
    }

    #[test]
    fn prop_min_status_idempotent(a in arb_gap_status()) {
        let result = a.clone().min_status(a.clone());
        prop_assert_eq!(result.rank(), a.rank());
    }

    #[test]
    fn prop_required_status_sound_for_bounded(
        value in 0.0f64..=1.0f64,
    ) {
        let status = GapStatus::Bounded(Bound::numeric(value));
        prop_assert!(RequiredStatus::BoundedRequired.satisfied_by(&status));
        prop_assert!(!RequiredStatus::ClosedRequired.satisfied_by(&status));
    }
}
