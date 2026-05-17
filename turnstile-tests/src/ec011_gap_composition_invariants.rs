/// EC-011 — Gap composition invariants.
///
/// The GapStatus composition rule (used in compose()) is:
///   min_status(s1, s2) = min(rank(s1), rank(s2))
///   where Open=0, Bounded=1, Closed=2
///
/// Invariants:
///   1. min_status is idempotent: min_status(s, s) = s (for Open and Closed;
///      for Bounded the bound value is taken from self).
///   2. min_status is commutative on rank: rank(min_status(a,b)) = min(rank(a), rank(b))
///   3. min_status is associative on rank.
///   4. Closed.min_status(Bounded(v)) = Bounded(v): result is Bounded, not Open or Closed.
///   5. Open.min_status(anything) = Open.
///   6. Closed.min_status(Closed) = Closed.
///
/// Composition of gap records via compose():
///   7. Composing two contexts with the same gap takes the minimum status.
///   8. Composing N contexts with an Open gap anywhere → result is Open.
///   9. Composing N contexts where all are Closed → result is Closed.
///
/// These invariants protect the "fail-closed" semantics of gap composition.
use proptest::prelude::*;
use turnstile_core::{
    compose,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{Bound, GapRecord, GapStatus},
    permission::Permission,
};

// ── GapStatus rank-level invariants ──────────────────────────────────────────

#[test]
fn min_status_rank_open_always_wins() {
    let open = GapStatus::Open;
    let bounded = GapStatus::Bounded(Bound::numeric(0.1));
    let closed = GapStatus::Closed;

    assert_eq!(open.clone().min_status(bounded.clone()).rank(), 0);
    assert_eq!(open.clone().min_status(closed.clone()).rank(), 0);
    assert_eq!(open.clone().min_status(open.clone()).rank(), 0);
    assert_eq!(bounded.clone().min_status(open.clone()).rank(), 0);
    assert_eq!(closed.clone().min_status(open.clone()).rank(), 0);
}

#[test]
fn min_status_rank_closed_with_bounded_gives_bounded() {
    let bounded = GapStatus::Bounded(Bound::numeric(0.5));
    let closed = GapStatus::Closed;

    let result = closed.clone().min_status(bounded.clone());
    assert_eq!(result.rank(), 1, "Closed.min_status(Bounded) must have rank 1 (Bounded)");
    assert!(matches!(result, GapStatus::Bounded(_)));

    let result2 = bounded.clone().min_status(closed);
    assert_eq!(result2.rank(), 1);
    assert!(matches!(result2, GapStatus::Bounded(_)));
}

#[test]
fn min_status_closed_closed_is_closed() {
    let result = GapStatus::Closed.min_status(GapStatus::Closed);
    assert_eq!(result, GapStatus::Closed);
}

#[test]
fn min_status_open_open_is_open() {
    let result = GapStatus::Open.min_status(GapStatus::Open);
    assert_eq!(result, GapStatus::Open);
}

#[test]
fn min_status_bounded_bounded_is_bounded() {
    let b1 = GapStatus::Bounded(Bound::numeric(0.1));
    let b2 = GapStatus::Bounded(Bound::numeric(0.9));
    let result = b1.min_status(b2);
    assert_eq!(result.rank(), 1, "Bounded.min_status(Bounded) must be Bounded");
    assert!(matches!(result, GapStatus::Bounded(_)));
}

// ── Rank commutativity ────────────────────────────────────────────────────────

#[test]
fn min_status_rank_commutative_exhaustive() {
    let statuses = [
        GapStatus::Open,
        GapStatus::Bounded(Bound::numeric(0.5)),
        GapStatus::Closed,
    ];
    for s1 in &statuses {
        for s2 in &statuses {
            let r1 = s1.clone().min_status(s2.clone()).rank();
            let r2 = s2.clone().min_status(s1.clone()).rank();
            assert_eq!(
                r1, r2,
                "min_status rank must be commutative: rank({s1:?},{s2:?})={r1} vs rank({s2:?},{s1:?})={r2}"
            );
        }
    }
}

// ── Rank associativity ────────────────────────────────────────────────────────

#[test]
fn min_status_rank_associative_exhaustive() {
    let statuses = [
        GapStatus::Open,
        GapStatus::Bounded(Bound::numeric(0.5)),
        GapStatus::Closed,
    ];
    for s1 in &statuses {
        for s2 in &statuses {
            for s3 in &statuses {
                let lhs = s1
                    .clone()
                    .min_status(s2.clone())
                    .min_status(s3.clone())
                    .rank();
                let rhs = s1
                    .clone()
                    .min_status(s2.clone().min_status(s3.clone()))
                    .rank();
                assert_eq!(
                    lhs, rhs,
                    "min_status rank must be associative for ({s1:?}, {s2:?}, {s3:?})"
                );
            }
        }
    }
}

// ── Gap composition in compose(): minimum over contexts ──────────────────────

fn gap_only_ctx(gap: GapRecord) -> ProofContext {
    ProofContext {
        claim_id: "c".into(),
        candidate_id: "z".into(),
        context_id: "ctx".into(),
        context_fingerprint: "fp".into(),
        allowed_use: "test".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![gap],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

#[test]
fn compose_closed_and_open_gives_open() {
    let g1 = gap_only_ctx(GapRecord::closed("g1", "t"));
    let g2 = gap_only_ctx(GapRecord::open("g1", "t"));
    let composed = compose(g1, g2).unwrap();
    let gap = composed.find_gap("g1").unwrap();
    assert_eq!(
        gap.status,
        GapStatus::Open,
        "compose(Closed, Open) must be Open"
    );
}

#[test]
fn compose_closed_and_closed_gives_closed() {
    let g1 = gap_only_ctx(GapRecord::closed("g1", "t"));
    let g2 = gap_only_ctx(GapRecord::closed("g1", "t"));
    let composed = compose(g1, g2).unwrap();
    let gap = composed.find_gap("g1").unwrap();
    assert_eq!(
        gap.status,
        GapStatus::Closed,
        "compose(Closed, Closed) must be Closed"
    );
}

#[test]
fn compose_bounded_and_closed_gives_bounded() {
    let g1 = gap_only_ctx(GapRecord::bounded("g1", "t", Bound::numeric(0.1)));
    let g2 = gap_only_ctx(GapRecord::closed("g1", "t"));
    let composed = compose(g1, g2).unwrap();
    let gap = composed.find_gap("g1").unwrap();
    assert_eq!(
        gap.status.rank(),
        1,
        "compose(Bounded, Closed) must yield Bounded (rank 1)"
    );
}

#[test]
fn compose_n_any_open_gives_open() {
    let contexts = vec![
        gap_only_ctx(GapRecord::closed("g1", "t")),
        gap_only_ctx(GapRecord::closed("g1", "t")),
        gap_only_ctx(GapRecord::open("g1", "t")), // one Open in N
        gap_only_ctx(GapRecord::closed("g1", "t")),
    ];
    let composed = turnstile_core::compose_n(contexts).unwrap();
    let gap = composed.find_gap("g1").unwrap();
    assert_eq!(
        gap.status,
        GapStatus::Open,
        "compose_n with any Open must yield Open"
    );
}

#[test]
fn compose_n_all_closed_gives_closed() {
    let contexts = vec![
        gap_only_ctx(GapRecord::closed("g1", "t")),
        gap_only_ctx(GapRecord::closed("g1", "t")),
        gap_only_ctx(GapRecord::closed("g1", "t")),
    ];
    let composed = turnstile_core::compose_n(contexts).unwrap();
    let gap = composed.find_gap("g1").unwrap();
    assert_eq!(
        gap.status,
        GapStatus::Closed,
        "compose_n with all Closed must yield Closed"
    );
}

// ── Proptest: rank commutativity under arbitrary inputs ──────────────────────

fn arb_gap_status() -> impl Strategy<Value = GapStatus> {
    prop_oneof![
        Just(GapStatus::Open),
        (-100.0f64..100.0f64).prop_map(|v| GapStatus::Bounded(Bound::numeric(v))),
        Just(GapStatus::Closed),
    ]
}

proptest! {
    #[test]
    fn prop_min_status_rank_commutative(
        s1 in arb_gap_status(),
        s2 in arb_gap_status(),
    ) {
        let r1 = s1.clone().min_status(s2.clone()).rank();
        let r2 = s2.clone().min_status(s1.clone()).rank();
        prop_assert_eq!(r1, r2, "min_status rank must be commutative");
    }

    #[test]
    fn prop_min_status_rank_associative(
        s1 in arb_gap_status(),
        s2 in arb_gap_status(),
        s3 in arb_gap_status(),
    ) {
        let lhs = s1.clone().min_status(s2.clone()).min_status(s3.clone()).rank();
        let rhs = s1.clone().min_status(s2.clone().min_status(s3.clone())).rank();
        prop_assert_eq!(lhs, rhs, "min_status rank must be associative");
    }

    #[test]
    fn prop_min_status_rank_is_min_of_individual_ranks(
        s1 in arb_gap_status(),
        s2 in arb_gap_status(),
    ) {
        let expected_rank = s1.rank().min(s2.rank());
        let actual_rank = s1.clone().min_status(s2.clone()).rank();
        prop_assert_eq!(
            actual_rank, expected_rank,
            "min_status rank must equal min of individual ranks"
        );
    }

    #[test]
    fn prop_open_absorbs_all(s in arb_gap_status()) {
        prop_assert_eq!(GapStatus::Open.clone().min_status(s.clone()).rank(), 0);
        prop_assert_eq!(s.min_status(GapStatus::Open).rank(), 0);
    }
}
