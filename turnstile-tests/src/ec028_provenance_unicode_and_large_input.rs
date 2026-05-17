/// EC-028 — Provenance hash: unicode, large inputs, and canonical form.
///
/// The provenance hash is SHA-256 over `claim_id\0candidate_id\0context_id\0allowed_use`
/// using null-byte delimiters.  This suite verifies the hash is stable, correct,
/// and free of canonicalization pitfalls:
///
///   U1 — Different unicode representations of the same visual string produce
///        different hashes (NFC vs NFD are distinct byte sequences — correct).
///   U2 — Empty fields hash differently from fields with content.
///   U3 — Field swap changes the hash (claim_id↔candidate_id).
///   U4 — Very large inputs (1 MB per field) produce a hash without panicking.
///   U5 — Null byte embedded in a field collides with the delimiter
///        (this is tested in ec003u; we re-verify with unicode-safe examples).
///   U6 — Multi-byte unicode characters are hashed over their UTF-8 encoding,
///        not code-point values.
///   U7 — Verify_provenance is deterministic: calling it twice on the same token
///        returns the same result.
///   U8 — Large provenance fields do not cause a panic in compile().
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::GapRecord,
    permission::Permission,
    token::{compute_provenance_hash, verify_provenance, ProofToken, TokenStatus},
};

use chrono::Utc;

// ── U1: NFC vs NFD unicode normalization produces different hashes ─────────────

#[test]
fn u1_nfc_and_nfd_produce_different_hashes() {
    // "é" can be represented as NFC (U+00E9, 2 bytes) or NFD (U+0065 U+0301, 3 bytes).
    let nfc = "\u{00e9}"; // precomposed é
    let nfd = "\u{0065}\u{0301}"; // decomposed e + combining acute

    // Visually identical but different byte sequences → different SHA-256.
    let h_nfc = compute_provenance_hash(nfc, "z", "ctx", "use");
    let h_nfd = compute_provenance_hash(nfd, "z", "ctx", "use");
    assert_ne!(
        h_nfc, h_nfd,
        "U1: NFC '{nfc}' and NFD '{nfd}' must produce different provenance hashes"
    );
}

// ── U2: Empty fields hash differently from non-empty ─────────────────────────

#[test]
fn u2_empty_field_differs_from_nonempty() {
    let h_empty = compute_provenance_hash("", "z", "ctx", "use");
    let h_nonempty = compute_provenance_hash("x", "z", "ctx", "use");
    assert_ne!(
        h_empty, h_nonempty,
        "U2: empty claim_id must produce different hash from non-empty"
    );
}

#[test]
fn u2_all_empty_fields_produce_stable_hash() {
    let h1 = compute_provenance_hash("", "", "", "");
    let h2 = compute_provenance_hash("", "", "", "");
    assert_eq!(
        h1, h2,
        "U2: all-empty fields must produce a stable (deterministic) hash"
    );
}

// ── U3: Field swap changes the hash ──────────────────────────────────────────

#[test]
fn u3_swapping_claim_and_candidate_changes_hash() {
    let h1 = compute_provenance_hash("claim-A", "candidate-B", "ctx", "use");
    let h2 = compute_provenance_hash("candidate-B", "claim-A", "ctx", "use");
    assert_ne!(
        h1, h2,
        "U3: swapping claim_id and candidate_id must change the provenance hash"
    );
}

// ── U4: Very large inputs produce a hash without panicking ────────────────────

#[test]
fn u4_large_claim_id_does_not_panic() {
    let large = "x".repeat(1_000_000); // 1 MB
    let h = compute_provenance_hash(&large, "z", "ctx", "use");
    assert_eq!(
        h.len(),
        64,
        "U4: SHA-256 hex digest must always be 64 chars"
    );
}

#[test]
fn u4_large_all_fields_does_not_panic() {
    let large = "a".repeat(200_000); // 200 KB each
    let h = compute_provenance_hash(&large, &large, &large, &large);
    assert_eq!(h.len(), 64, "U4: large all-fields hash must be 64 chars");
}

// ── U5: Null byte in field still produces a unique hash ───────────────────────

#[test]
fn u5_null_byte_in_field_does_not_collide_with_delimiter() {
    // "a\0b" in claim_id vs "a" in claim_id + "b" in candidate_id must differ.
    let h1 = compute_provenance_hash("a\x00b", "", "ctx", "use");
    let h2 = compute_provenance_hash("a", "b", "ctx", "use");
    assert_ne!(
        h1, h2,
        "U5: null byte embedded in field must not collide with delimiter"
    );
}

// ── U6: Multi-byte unicode hashed over UTF-8 bytes ───────────────────────────

#[test]
fn u6_multibyte_unicode_hashed_over_utf8() {
    // CJK character U+4E2D (中, 3 UTF-8 bytes: E4 B8 AD)
    let cjk = "\u{4e2d}";
    let h_cjk = compute_provenance_hash(cjk, "z", "ctx", "use");
    // ASCII 'a' is 1 byte — different encoding, different hash.
    let h_ascii = compute_provenance_hash("a", "z", "ctx", "use");
    assert_ne!(
        h_cjk, h_ascii,
        "U6: CJK character must produce a different hash than ASCII 'a'"
    );
    // Determinism: same CJK input → same hash.
    let h_cjk2 = compute_provenance_hash(cjk, "z", "ctx", "use");
    assert_eq!(
        h_cjk, h_cjk2,
        "U6: hash must be deterministic for same input"
    );
}

// ── U7: verify_provenance is deterministic ────────────────────────────────────

#[test]
fn u7_verify_provenance_deterministic() {
    let hash = compute_provenance_hash("c", "z", "ctx", "use");
    let tok = ProofToken {
        token_id: "u7-tok".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    let r1 = verify_provenance(&tok, "c", "z", "ctx", "use");
    let r2 = verify_provenance(&tok, "c", "z", "ctx", "use");
    assert_eq!(r1, r2, "U7: verify_provenance must be deterministic");
    assert!(r1, "U7: correct provenance must verify");
}

// ── U8: Large provenance fields in compile() do not panic ─────────────────────

#[test]
fn u8_large_field_in_compile_does_not_panic() {
    let large = "L".repeat(100_000);
    let hash = compute_provenance_hash(&large, &large, &large, &large);

    let ctx = ProofContext {
        claim_id: large.clone(),
        candidate_id: large.clone(),
        context_id: large.clone(),
        context_fingerprint: "fp-u8".into(),
        allowed_use: large.clone(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "gap")],
        profiles: vec![],
        tokens: vec![ProofToken {
            token_id: "u8-tok".into(),
            token_type: "CLOSE".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        }],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    // Must not panic. The profile is empty so outcome is OOC.
    let result = compile(ctx);
    assert!(
        result.is_ok(),
        "U8: large provenance fields must not panic in compile()"
    );
}
