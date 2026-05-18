/// EC-023 — Permission::descending() order stability guard.
///
/// The descending iterator is the spine of the compile algorithm's step 2.
/// Any reordering of the enum variants or the iterator literal would silently
/// change compilation outcomes for tie-breaking cases.  This suite pins the
/// exact sequence so a maintainer cannot accidentally reorder without this
/// test failing loudly.
///
///   O1 — The exact 12-element sequence is [AAA, ALR, AEX, REV, DIA, ROL,
///         ESC, ETA, UNS, REF, EXP, OOC].
///   O2 — Each consecutive pair satisfies descending_prev > descending_next.
///   O3 — descending() is idempotent: two calls return identical sequences.
///   O4 — Compile algorithm visits AAA first and OOC last (top-down).
///   O5 — No duplicates appear in the iterator.
///   O6 — ascending() is the reverse of descending() (via Ord).
///   O7 — Permission total order is consistent with descending() ordering.
use noethers_turnstile_core::permission::Permission;

// ── O1: Exact sequence is pinned ─────────────────────────────────────────────

#[test]
fn o1_exact_descending_sequence() {
    let got: Vec<Permission> = Permission::descending().collect();
    let expected = vec![
        Permission::AAA,
        Permission::ALR,
        Permission::AEX,
        Permission::REV,
        Permission::DIA,
        Permission::ROL,
        Permission::ESC,
        Permission::ETA,
        Permission::UNS,
        Permission::REF,
        Permission::EXP,
        Permission::OOC,
    ];
    assert_eq!(
        got, expected,
        "O1: descending() sequence must be exactly [AAA, ALR, AEX, REV, DIA, ROL, ESC, ETA, UNS, REF, EXP, OOC]"
    );
}

// ── O2: Consecutive pairs satisfy strict descending order ─────────────────────

#[test]
fn o2_consecutive_pairs_are_strictly_descending() {
    let seq: Vec<Permission> = Permission::descending().collect();
    for i in 0..seq.len() - 1 {
        assert!(
            seq[i] > seq[i + 1],
            "O2: descending()[{i}] ({:?}) must be strictly greater than descending()[{}] ({:?})",
            seq[i],
            i + 1,
            seq[i + 1]
        );
    }
}

// ── O3: Idempotent: two calls agree ──────────────────────────────────────────

#[test]
fn o3_descending_is_idempotent() {
    let a: Vec<Permission> = Permission::descending().collect();
    let b: Vec<Permission> = Permission::descending().collect();
    assert_eq!(
        a, b,
        "O3: two calls to descending() must return identical sequences"
    );
}

// ── O4: Compile visits AAA first and OOC last ────────────────────────────────

#[test]
fn o4_first_element_is_aaa() {
    assert_eq!(
        Permission::descending().next(),
        Some(Permission::AAA),
        "O4: descending() must begin with AAA (highest permission)"
    );
}

#[test]
fn o4_last_element_is_ooc() {
    assert_eq!(
        Permission::descending().last(),
        Some(Permission::OOC),
        "O4: descending() must end with OOC (lowest permission)"
    );
}

// ── O5: No duplicates in the iterator ────────────────────────────────────────

#[test]
fn o5_no_duplicate_elements() {
    let seq: Vec<Permission> = Permission::descending().collect();
    let mut seen = std::collections::HashSet::new();
    for p in &seq {
        assert!(
            seen.insert(*p),
            "O5: duplicate element {:?} found in descending()",
            p
        );
    }
}

// ── O6: ascending (reversed descending) agrees with Ord ──────────────────────

#[test]
fn o6_reversed_descending_is_ascending() {
    let desc: Vec<Permission> = Permission::descending().collect();
    let mut asc = desc.clone();
    asc.reverse();

    // Verify consecutive pairs in the reversed list are strictly ascending.
    for i in 0..asc.len() - 1 {
        assert!(
            asc[i] < asc[i + 1],
            "O6: reversed descending pair [{i}] must be strictly ascending: {:?} < {:?}",
            asc[i],
            asc[i + 1]
        );
    }
}

// ── O7: Ord is consistent with descending() ordering ─────────────────────────

#[test]
fn o7_ord_consistent_with_descending() {
    let seq: Vec<Permission> = Permission::descending().collect();
    for i in 0..seq.len() {
        for j in 0..seq.len() {
            if i < j {
                assert!(
                    seq[i] > seq[j],
                    "O7: seq[{i}] ({:?}) must be Ord-greater than seq[{j}] ({:?})",
                    seq[i],
                    seq[j]
                );
            } else if i == j {
                assert_eq!(seq[i], seq[j], "O7: same index must be Ord-equal");
            } else {
                assert!(
                    seq[i] < seq[j],
                    "O7: seq[{i}] ({:?}) must be Ord-less than seq[{j}] ({:?})",
                    seq[i],
                    seq[j]
                );
            }
        }
    }
}

// ── Additional: all 12 named permissions appear exactly once ──────────────────

#[test]
fn all_12_permissions_appear_exactly_once() {
    let expected = [
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
    let seq: Vec<Permission> = Permission::descending().collect();
    assert_eq!(seq.len(), 12, "must have exactly 12 permissions");
    for p in &expected {
        assert!(
            seq.contains(p),
            "permission {:?} is missing from descending()",
            p
        );
    }
}
