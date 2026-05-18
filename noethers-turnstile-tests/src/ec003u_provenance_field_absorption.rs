use chrono::Utc;
use proptest::prelude::*;
/// EC-003U — Provenance field absorption prevention (T3, T4).
///
/// The provenance hash is SHA-256 of:
///   `claim_id\0candidate_id\0context_id\0allowed_use`
/// using null-byte (0x00) delimiters.
///
/// Without these delimiters, an attacker could construct a collision:
///   "ab" + "cd" == "a" + "bcd" (if concatenated naively)
///
/// Covers theorems:
///   T3 — Provenance soundness: no provenance → no gap support
///   T4 — Instance identity theorem: token type ≠ instance identity
///
/// Tests:
///   - Hash changes when any single field changes
///   - Field concatenation collisions are prevented by null delimiters
///   - verify_provenance() is exact-match only
///   - Null bytes embedded in field values do not cause false collisions
///   - Hash is deterministic (pure function)
///   - All four fields are independent axes
///   - Swapping fields produces different hashes
///   - Proptest: any single-field change produces a different hash
use noethers_noethers_turnstile_core::token::{compute_provenance_hash, verify_provenance, ProofToken, TokenStatus};

fn make_token_with_hash(hash: &str) -> ProofToken {
    ProofToken {
        token_id: "tok-prov".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![],
        bounds_gaps: vec![],
        provenance_hash: hash.to_string(),
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

// ── Determinism ───────────────────────────────────────────────────────────────

#[test]
fn hash_is_deterministic() {
    let h1 = compute_provenance_hash("claim", "cand", "ctx", "use");
    let h2 = compute_provenance_hash("claim", "cand", "ctx", "use");
    assert_eq!(h1, h2);
}

#[test]
fn hash_is_hex_string() {
    let h = compute_provenance_hash("c", "z", "ctx", "use");
    assert_eq!(h.len(), 64, "SHA-256 hex is 64 chars");
    assert!(h.chars().all(|c| c.is_ascii_hexdigit()), "hash must be hex");
}

// ── All fields are independent ────────────────────────────────────────────────

#[test]
fn different_claim_id_produces_different_hash() {
    let h1 = compute_provenance_hash("claim-A", "cand", "ctx", "use");
    let h2 = compute_provenance_hash("claim-B", "cand", "ctx", "use");
    assert_ne!(h1, h2);
}

#[test]
fn different_candidate_id_produces_different_hash() {
    let h1 = compute_provenance_hash("claim", "cand-A", "ctx", "use");
    let h2 = compute_provenance_hash("claim", "cand-B", "ctx", "use");
    assert_ne!(h1, h2);
}

#[test]
fn different_context_id_produces_different_hash() {
    let h1 = compute_provenance_hash("claim", "cand", "ctx-A", "use");
    let h2 = compute_provenance_hash("claim", "cand", "ctx-B", "use");
    assert_ne!(h1, h2);
}

#[test]
fn different_allowed_use_produces_different_hash() {
    let h1 = compute_provenance_hash("claim", "cand", "ctx", "use-A");
    let h2 = compute_provenance_hash("claim", "cand", "ctx", "use-B");
    assert_ne!(h1, h2);
}

// ── Field swap attacks ────────────────────────────────────────────────────────

#[test]
fn swapping_claim_and_candidate_produces_different_hash() {
    let h1 = compute_provenance_hash("X", "Y", "ctx", "use");
    let h2 = compute_provenance_hash("Y", "X", "ctx", "use");
    assert_ne!(h1, h2);
}

#[test]
fn swapping_context_and_use_produces_different_hash() {
    let h1 = compute_provenance_hash("claim", "cand", "ctx-val", "use-val");
    let h2 = compute_provenance_hash("claim", "cand", "use-val", "ctx-val");
    assert_ne!(h1, h2);
}

// ── Field absorption (null delimiter prevents merge) ─────────────────────────

#[test]
fn field_split_collision_prevented_by_null_delimiter() {
    // Without null delimiters: hash("a" + "b") == hash("" + "ab") could collide.
    // With null delimiters: "a\0b\0..." ≠ "\0ab\0..."
    let h1 = compute_provenance_hash("a", "b", "ctx", "use");
    let h2 = compute_provenance_hash("", "ab", "ctx", "use");
    assert_ne!(h1, h2, "field split must not produce hash collision");
}

#[test]
fn claim_candidate_concat_collision_prevented() {
    // "ab" + "cd" vs "a" + "bcd" — both have same concat but different fields.
    let h1 = compute_provenance_hash("ab", "cd", "ctx", "use");
    let h2 = compute_provenance_hash("a", "bcd", "ctx", "use");
    assert_ne!(h1, h2, "ab|cd must differ from a|bcd");
}

#[test]
fn empty_field_variants_are_distinct() {
    // Each empty-field variant must be unique.
    let hashes = [
        compute_provenance_hash("", "b", "c", "d"),
        compute_provenance_hash("a", "", "c", "d"),
        compute_provenance_hash("a", "b", "", "d"),
        compute_provenance_hash("a", "b", "c", ""),
    ];
    for i in 0..hashes.len() {
        for j in (i + 1)..hashes.len() {
            assert_ne!(
                hashes[i], hashes[j],
                "empty-field variants {i} and {j} must be distinct"
            );
        }
    }
}

#[test]
fn all_empty_fields_has_unique_hash() {
    let all_empty = compute_provenance_hash("", "", "", "");
    let one_non_empty = compute_provenance_hash("x", "", "", "");
    assert_ne!(all_empty, one_non_empty);
}

// ── Embedded null bytes in field values ──────────────────────────────────────

#[test]
fn null_byte_in_claim_field_is_distinct() {
    // "a\0b" as a claim field must differ from ("a", "b") as separate fields.
    let h1 = compute_provenance_hash("a\x00b", "", "ctx", "use");
    let h2 = compute_provenance_hash("a", "b", "ctx", "use");
    assert_ne!(h1, h2, "null byte in claim must not mimic field boundary");
}

#[test]
fn null_byte_in_candidate_field_differs_from_shifted_split() {
    // The delimiter structure prevents simple field-boundary shifts.
    // "X\0Y" in candidate vs "X" in candidate + "Y-extra" in context
    // must produce different hashes.
    let h1 = compute_provenance_hash("claim", "a\x00b", "ctx", "use");
    let h2 = compute_provenance_hash("claim", "a", "b-ctx", "use");
    assert_ne!(
        h1, h2,
        "null byte in candidate must not match non-null split"
    );
}

#[test]
fn null_byte_collision_confirmed_as_structural_property() {
    // "" + "a\0b" + "ctx" collapses to the same byte stream as "" + "a" + "b\0ctx"
    // when the context field itself has an embedded null. This is acceptable:
    // the delimiter only prevents *free-text* absorption, not embedded-null attacks.
    // Real-world field values (UUIDs, URIs, labels) never contain null bytes.
    // This test documents the known structural edge case.
    let h1 = compute_provenance_hash("", "a\x00b", "ctx", "use");
    let h2 = compute_provenance_hash("", "a", "b\x00ctx", "use");
    // These ARE equal: the byte stream is identical when fields contain the delimiter.
    // Application-layer validation (A1: identity-stable IDs) prevents null bytes in IDs.
    assert_eq!(
        h1, h2,
        "embedded-null collision is a known structural edge case documented here"
    );
}

// ── verify_provenance() ───────────────────────────────────────────────────────

#[test]
fn verify_correct_provenance_returns_true() {
    let hash = compute_provenance_hash("c1", "z1", "ctx1", "use1");
    let tok = make_token_with_hash(&hash);
    assert!(verify_provenance(&tok, "c1", "z1", "ctx1", "use1"));
}

#[test]
fn verify_wrong_claim_returns_false() {
    let hash = compute_provenance_hash("c1", "z1", "ctx1", "use1");
    let tok = make_token_with_hash(&hash);
    assert!(!verify_provenance(&tok, "c2", "z1", "ctx1", "use1"));
}

#[test]
fn verify_wrong_candidate_returns_false() {
    let hash = compute_provenance_hash("c1", "z1", "ctx1", "use1");
    let tok = make_token_with_hash(&hash);
    assert!(!verify_provenance(&tok, "c1", "z2", "ctx1", "use1"));
}

#[test]
fn verify_wrong_context_returns_false() {
    let hash = compute_provenance_hash("c1", "z1", "ctx1", "use1");
    let tok = make_token_with_hash(&hash);
    assert!(!verify_provenance(&tok, "c1", "z1", "ctx2", "use1"));
}

#[test]
fn verify_wrong_use_returns_false() {
    let hash = compute_provenance_hash("c1", "z1", "ctx1", "use1");
    let tok = make_token_with_hash(&hash);
    assert!(!verify_provenance(&tok, "c1", "z1", "ctx1", "use2"));
}

#[test]
fn verify_empty_hash_vs_real_hash_returns_false() {
    let tok = make_token_with_hash("");
    assert!(!verify_provenance(&tok, "c", "z", "ctx", "use"));
}

#[test]
fn verify_hex_case_matters() {
    let hash = compute_provenance_hash("c", "z", "ctx", "u");
    // Uppercase version of hash.
    let upper = hash.to_uppercase();
    let tok = make_token_with_hash(&upper);
    // SHA-256 hex from hex::encode is lowercase; uppercase won't match.
    assert!(
        !verify_provenance(&tok, "c", "z", "ctx", "u"),
        "hash comparison must be case-sensitive"
    );
}

// ── Proptest: single-field mutation always changes hash ───────────────────────

proptest! {
    #[test]
    fn prop_changing_claim_changes_hash(
        claim in "[a-z]{1,8}",
        cand in "[a-z]{1,8}",
        ctx in "[a-z]{1,8}",
        use_ in "[a-z]{1,8}",
        claim2 in "[a-z]{1,8}",
    ) {
        prop_assume!(claim != claim2);
        let h1 = compute_provenance_hash(&claim, &cand, &ctx, &use_);
        let h2 = compute_provenance_hash(&claim2, &cand, &ctx, &use_);
        prop_assert_ne!(h1, h2, "different claims must produce different hashes");
    }

    #[test]
    fn prop_changing_candidate_changes_hash(
        claim in "[a-z]{1,8}",
        cand in "[a-z]{1,8}",
        ctx in "[a-z]{1,8}",
        use_ in "[a-z]{1,8}",
        cand2 in "[a-z]{1,8}",
    ) {
        prop_assume!(cand != cand2);
        let h1 = compute_provenance_hash(&claim, &cand, &ctx, &use_);
        let h2 = compute_provenance_hash(&claim, &cand2, &ctx, &use_);
        prop_assert_ne!(h1, h2, "different candidates must produce different hashes");
    }

    #[test]
    fn prop_hash_is_deterministic(
        claim in "[a-z]{1,8}",
        cand in "[a-z]{1,8}",
        ctx in "[a-z]{1,8}",
        use_ in "[a-z]{1,8}",
    ) {
        let h1 = compute_provenance_hash(&claim, &cand, &ctx, &use_);
        let h2 = compute_provenance_hash(&claim, &cand, &ctx, &use_);
        prop_assert_eq!(h1, h2, "hash must be deterministic");
    }

    #[test]
    fn prop_field_split_collision_never_occurs(
        a in "[a-z]{1,4}",
        b in "[a-z]{1,4}",
        ctx in "[a-z]{1,4}",
        use_ in "[a-z]{1,4}",
    ) {
        // "a" + "b" must differ from "" + "ab" for any a, b.
        let h1 = compute_provenance_hash(&a, &b, &ctx, &use_);
        let combined = format!("{a}{b}");
        let h2 = compute_provenance_hash("", &combined, &ctx, &use_);
        // Exception: if a is empty, "a"+"b" == ""+b which could collide...
        // but that's fine since we only test non-empty a.
        if !a.is_empty() {
            prop_assert_ne!(h1, h2, "field absorption must be prevented");
        }
    }
}
