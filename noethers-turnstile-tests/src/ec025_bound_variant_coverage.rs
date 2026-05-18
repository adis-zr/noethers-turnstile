/// EC-025 — BoundKind variant coverage and Bound constructors.
///
/// `BoundKind` has three variants — `Numeric`, `SetValued`, and `Infinity` —
/// but the compile path only ever produces `Bound::infinity()` via
/// `effective_gap_status`.  This suite exercises the full variant space so
/// serialization, PartialEq, and the constructor helpers are verified.
///
///   B1 — Bound::numeric() creates a Numeric bound with the given value.
///   B2 — Bound::numeric_with_units() carries units correctly.
///   B3 — Bound::set_valued() creates a SetValued bound.
///   B4 — Bound::infinity() creates an Infinity bound.
///   B5 — PartialEq: two Numeric bounds with same value are equal.
///   B6 — PartialEq: two Numeric bounds with different values are not equal.
///   B7 — PartialEq: Numeric ≠ SetValued ≠ Infinity (cross-variant).
///   B8 — Serde round-trip for all three BoundKind variants.
///   B9 — GapRecord::bounded() carries the full Bound through.
///   B10 — GapStatus rank: Open(0) < Bounded(1) < Closed(2).
///   B11 — GapStatus::min_status correctly picks the lower rank.
///   B12 — RequiredStatus::BoundedRequired accepts Bounded(Numeric).
///   B13 — RequiredStatus::BoundedRequired accepts Bounded(SetValued).
///   B14 — RequiredStatus::BoundedRequired accepts Bounded(Infinity).
///   B15 — Bounding token upgrades gap to Bounded(Infinity) in compile().
use noethers_noethers_turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{Bound, BoundKind, GapRecord, GapRequirement, GapStatus, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

use chrono::Utc;

// ── B1: Bound::numeric() ─────────────────────────────────────────────────────

#[test]
fn b1_numeric_bound_carries_value() {
    let b = Bound::numeric(0.05);
    assert!(
        matches!(b.kind, BoundKind::Numeric(v) if (v.value() - 0.05).abs() < f64::EPSILON),
        "B1: Bound::numeric(0.05) must carry value 0.05"
    );
    assert_eq!(b.units, None, "B1: no units by default");
}

// ── B2: Bound::numeric_with_units() ──────────────────────────────────────────

#[test]
fn b2_numeric_with_units_carries_units() {
    let b = Bound::numeric_with_units(1.5, "nats");
    assert!(
        matches!(b.kind, BoundKind::Numeric(v) if (v.value() - 1.5).abs() < f64::EPSILON),
        "B2: numeric value must be 1.5"
    );
    assert_eq!(
        b.units,
        Some("nats".to_string()),
        "B2: units must be 'nats'"
    );
}

// ── B3: Bound::set_valued() ───────────────────────────────────────────────────

#[test]
fn b3_set_valued_bound_carries_values() {
    let b = Bound::set_valued(vec!["read".into(), "write".into()]);
    match &b.kind {
        BoundKind::SetValued(vals) => {
            assert_eq!(
                vals,
                &vec!["read".to_string(), "write".to_string()],
                "B3: SetValued must carry provided values"
            );
        }
        other => panic!("B3: expected SetValued, got {:?}", other),
    }
    assert_eq!(b.units, None, "B3: no units on SetValued bound");
}

// ── B4: Bound::infinity() ─────────────────────────────────────────────────────

#[test]
fn b4_infinity_bound() {
    let b = Bound::infinity();
    assert!(
        matches!(b.kind, BoundKind::Infinity),
        "B4: Bound::infinity() must have Infinity kind"
    );
}

// ── B5: PartialEq — same numeric value ───────────────────────────────────────

#[test]
fn b5_equal_numeric_bounds_are_equal() {
    let b1 = Bound::numeric(std::f64::consts::PI);
    let b2 = Bound::numeric(std::f64::consts::PI);
    assert_eq!(
        b1, b2,
        "B5: two Numeric bounds with same value must be equal"
    );
}

// ── B6: PartialEq — different numeric values ─────────────────────────────────

#[test]
fn b6_different_numeric_bounds_are_not_equal() {
    let b1 = Bound::numeric(1.0);
    let b2 = Bound::numeric(2.0);
    assert_ne!(
        b1, b2,
        "B6: Numeric bounds with different values must not be equal"
    );
}

// ── B7: PartialEq — cross-variant ────────────────────────────────────────────

#[test]
fn b7_numeric_ne_set_valued_ne_infinity() {
    let n = Bound::numeric(1.0);
    let s = Bound::set_valued(vec!["x".into()]);
    let i = Bound::infinity();

    assert_ne!(n, s, "B7: Numeric ≠ SetValued");
    assert_ne!(n, i, "B7: Numeric ≠ Infinity");
    assert_ne!(s, i, "B7: SetValued ≠ Infinity");
}

// ── B8: Serde round-trip ──────────────────────────────────────────────────────

#[test]
fn b8_serde_roundtrip_numeric() {
    let b = Bound::numeric_with_units(0.01, "KL-nats");
    let json = serde_json::to_string(&b).expect("B8: serialize numeric");
    let back: Bound = serde_json::from_str(&json).expect("B8: deserialize numeric");
    assert_eq!(b, back, "B8: serde round-trip must be lossless for Numeric");
}

#[test]
fn b8_serde_roundtrip_set_valued() {
    let b = Bound::set_valued(vec!["alpha".into(), "beta".into()]);
    let json = serde_json::to_string(&b).expect("B8: serialize set_valued");
    let back: Bound = serde_json::from_str(&json).expect("B8: deserialize set_valued");
    assert_eq!(
        b, back,
        "B8: serde round-trip must be lossless for SetValued"
    );
}

#[test]
fn b8_serde_roundtrip_infinity() {
    let b = Bound::infinity();
    let json = serde_json::to_string(&b).expect("B8: serialize infinity");
    let back: Bound = serde_json::from_str(&json).expect("B8: deserialize infinity");
    assert_eq!(
        b, back,
        "B8: serde round-trip must be lossless for Infinity"
    );
}

// ── B9: GapRecord::bounded() carries the Bound ────────────────────────────────

#[test]
fn b9_gap_record_bounded_carries_bound() {
    let bound = Bound::numeric(0.05);
    let g = GapRecord::bounded("g1", "kl_gap", bound.clone());
    assert_eq!(
        g.status,
        GapStatus::Bounded(bound),
        "B9: GapRecord::bounded must carry the bound"
    );
}

// ── B10: GapStatus rank ordering ─────────────────────────────────────────────

#[test]
fn b10_gap_status_rank_ordering() {
    assert_eq!(GapStatus::Open.rank(), 0, "B10: Open has rank 0");
    assert_eq!(
        GapStatus::Bounded(Bound::infinity()).rank(),
        1,
        "B10: Bounded has rank 1"
    );
    assert_eq!(GapStatus::Closed.rank(), 2, "B10: Closed has rank 2");
    assert!(GapStatus::Open.rank() < GapStatus::Bounded(Bound::numeric(0.0)).rank());
    assert!(GapStatus::Bounded(Bound::infinity()).rank() < GapStatus::Closed.rank());
}

// ── B11: GapStatus::min_status correctness ───────────────────────────────────

#[test]
fn b11_min_status_open_wins_over_bounded() {
    let result = GapStatus::Open.min_status(GapStatus::Bounded(Bound::infinity()));
    assert_eq!(
        result.rank(),
        0,
        "B11: Open.min_status(Bounded) must return Open (rank 0)"
    );
}

#[test]
fn b11_min_status_bounded_wins_over_closed() {
    let result = GapStatus::Closed.min_status(GapStatus::Bounded(Bound::numeric(1.0)));
    assert_eq!(
        result.rank(),
        1,
        "B11: Closed.min_status(Bounded) must return Bounded (rank 1)"
    );
}

#[test]
fn b11_min_status_idempotent_on_equal_ranks() {
    let r1 = GapStatus::Open.min_status(GapStatus::Open);
    let r2 = GapStatus::Closed.min_status(GapStatus::Closed);
    assert_eq!(r1.rank(), 0, "B11: Open.min_status(Open) = Open");
    assert_eq!(r2.rank(), 2, "B11: Closed.min_status(Closed) = Closed");
}

// ── B12-B14: RequiredStatus::BoundedRequired accepts all Bounded variants ─────

#[test]
fn b12_bounded_required_accepts_numeric() {
    let status = GapStatus::Bounded(Bound::numeric(0.001));
    assert!(
        RequiredStatus::BoundedRequired.satisfied_by(&status),
        "B12: BoundedRequired must accept Bounded(Numeric)"
    );
}

#[test]
fn b13_bounded_required_accepts_set_valued() {
    let status = GapStatus::Bounded(Bound::set_valued(vec!["allowed".into()]));
    assert!(
        RequiredStatus::BoundedRequired.satisfied_by(&status),
        "B13: BoundedRequired must accept Bounded(SetValued)"
    );
}

#[test]
fn b14_bounded_required_accepts_infinity() {
    let status = GapStatus::Bounded(Bound::infinity());
    assert!(
        RequiredStatus::BoundedRequired.satisfied_by(&status),
        "B14: BoundedRequired must accept Bounded(Infinity)"
    );
}

// ── B15: Bounding token upgrades gap to Bounded(Infinity) in compile() ────────

#[test]
fn b15_bounding_token_upgrades_gap_to_bounded() {
    let claim_id = "claim-b15";
    let candidate_id = "z-b15";
    let context_id = "ctx-b15";
    let allowed_use = "b15-use";

    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-b15".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "calibration_gap")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::BoundedRequired, // Bounded is sufficient
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "bounding-tok".into(),
            token_type: "BOUND".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![],
            bounds_gaps: vec!["g1".into()], // bounds, doesn't close
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
    };

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "B15: a bounding token with BoundedRequired profile must satisfy the requirement and emit DIA"
    );
}
