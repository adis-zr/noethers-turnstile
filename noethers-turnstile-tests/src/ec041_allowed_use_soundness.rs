/// EC-041 — Allowed-use soundness (T12, EC-001 §14).
///
/// `allowed_use` is the sole caller-supplied binding between a token and its
/// purpose.  It enters the provenance hash; any mutation causes a hash mismatch
/// and prevents the token from closing a gap.  Two contexts with different
/// `allowed_use` values must not compose (UseConflict).
///
/// T12 — Allowed-use soundness: `allowed_use` is bound in the provenance hash;
///        UseConflict on mismatch; compiler rejects empty string.
///
///   AU1  — Unicode / multi-byte `allowed_use` changes provenance hash
///   AU2  — Internal whitespace is exact: "foo bar" ≠ "foo  bar"
///   AU3  — Case-sensitive: "Exact" ≠ "exact"
///   AU4  — Leading/trailing whitespace is exact: " use" ≠ "use"
///   AU5  — Empty allowed_use rejected by compile()
///   AU6  — compose() with mismatched allowed_use → UseConflict
///   AU7  — compose() with matching allowed_use succeeds
///   AU8  — compose_n fails closed if any context has different allowed_use
///   AU9  — Very long string (>10k chars): hash stable and distinct per value
///   AU10 — Token provenance hash computed from exact allowed_use byte string
///   AU11 — Token bound to "use-A" cannot close gap in context with "use-B"
///   AU12 — Two tokens, same gap, different allowed_use: neither closes the gap
///   AU13 — allowed_use mutation in one field only (not candidate/claim/context)
///   AU14 — Null bytes in allowed_use: treated as distinct values
///   Prop — Single-character mutation to allowed_use changes provenance hash
use chrono::Utc;
use proptest::prelude::*;
use noethers_turnstile_core::{
    compile, compose, compose_n,
    context::{Membership, ProofContext, Scope},
    error::CompositionError,
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn ctx_with_use(allowed_use: &str) -> ProofContext {
    ProofContext {
        claim_id: "claim-au".into(),
        candidate_id: "z-au".into(),
        context_id: "ctx-au".into(),
        context_fingerprint: "fp-au".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

fn ctx_with_token_use(ctx_use: &str, tok_use: &str) -> ProofContext {
    let hash = compute_provenance_hash("claim-au", "z-au", "ctx-au", tok_use);
    let gap_id = "g1";
    ProofContext {
        claim_id: "claim-au".into(),
        candidate_id: "z-au".into(),
        context_id: "ctx-au".into(),
        context_fingerprint: "fp-au".into(),
        allowed_use: ctx_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open(gap_id, "t")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-au".into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![gap_id.into()],
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
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── AU1: Unicode changes provenance hash ──────────────────────────────────────

#[test]
fn au1_unicode_allowed_use_produces_distinct_hash() {
    let h_ascii = compute_provenance_hash("c", "z", "ctx", "use");
    let h_unicode = compute_provenance_hash("c", "z", "ctx", "üse");
    let h_emoji = compute_provenance_hash("c", "z", "ctx", "use🔑");
    let h_cjk = compute_provenance_hash("c", "z", "ctx", "用途");

    assert_ne!(h_ascii, h_unicode, "AU1: unicode vs ascii must differ");
    assert_ne!(h_ascii, h_emoji, "AU1: emoji suffix must differ");
    assert_ne!(h_ascii, h_cjk, "AU1: CJK must differ");
    assert_ne!(h_unicode, h_cjk, "AU1: distinct unicode must differ");
}

// ── AU2: Internal whitespace is exact ────────────────────────────────────────

#[test]
fn au2_internal_whitespace_exact_match() {
    let h1 = compute_provenance_hash("c", "z", "ctx", "foo bar");
    let h2 = compute_provenance_hash("c", "z", "ctx", "foo  bar");
    assert_ne!(h1, h2, "AU2: single vs double space must differ");

    let h3 = compute_provenance_hash("c", "z", "ctx", "foo\tbar");
    assert_ne!(h1, h3, "AU2: space vs tab must differ");
}

// ── AU3: Case sensitivity ─────────────────────────────────────────────────────

#[test]
fn au3_case_sensitive() {
    let h_lower = compute_provenance_hash("c", "z", "ctx", "exact");
    let h_upper = compute_provenance_hash("c", "z", "ctx", "Exact");
    let h_all_upper = compute_provenance_hash("c", "z", "ctx", "EXACT");
    assert_ne!(h_lower, h_upper, "AU3: 'exact' vs 'Exact' must differ");
    assert_ne!(h_lower, h_all_upper, "AU3: 'exact' vs 'EXACT' must differ");
    assert_ne!(h_upper, h_all_upper, "AU3: 'Exact' vs 'EXACT' must differ");
}

// ── AU4: Leading/trailing whitespace is exact ─────────────────────────────────

#[test]
fn au4_leading_trailing_whitespace_exact() {
    let h_bare = compute_provenance_hash("c", "z", "ctx", "use");
    let h_lead = compute_provenance_hash("c", "z", "ctx", " use");
    let h_trail = compute_provenance_hash("c", "z", "ctx", "use ");
    assert_ne!(h_bare, h_lead, "AU4: leading space must differ");
    assert_ne!(h_bare, h_trail, "AU4: trailing space must differ");
    assert_ne!(h_lead, h_trail, "AU4: leading vs trailing must differ");
}

// ── AU5: Empty allowed_use rejected ──────────────────────────────────────────

#[test]
fn au5_empty_allowed_use_rejected_by_compile() {
    let mut ctx = ctx_with_use("");
    ctx.gaps.push(GapRecord::open("g1", "t"));
    let result = compile(ctx);
    assert!(
        result.is_err(),
        "AU5: empty allowed_use must be rejected by compile()"
    );
}

// ── AU6: Mismatched allowed_use → UseConflict ─────────────────────────────────

#[test]
fn au6_compose_mismatched_allowed_use_is_use_conflict() {
    let ctx_a = ctx_with_use("purpose-alpha");
    let ctx_b = ctx_with_use("purpose-beta");
    let result = compose(ctx_a, ctx_b);
    assert!(
        matches!(result, Err(CompositionError::UseConflict)),
        "AU6: different allowed_use must yield UseConflict"
    );
}

#[test]
fn au6_use_conflict_is_symmetric() {
    let ctx_a = ctx_with_use("use-x");
    let ctx_b = ctx_with_use("use-y");
    let fwd = compose(ctx_a.clone(), ctx_b.clone());
    let rev = compose(ctx_b, ctx_a);
    assert!(matches!(fwd, Err(CompositionError::UseConflict)));
    assert!(matches!(rev, Err(CompositionError::UseConflict)));
}

// ── AU7: Matching allowed_use succeeds ───────────────────────────────────────

#[test]
fn au7_compose_matching_allowed_use_succeeds() {
    let ctx_a = ctx_with_use("shared-purpose");
    let ctx_b = ctx_with_use("shared-purpose");
    let result = compose(ctx_a, ctx_b);
    assert!(
        result.is_ok(),
        "AU7: identical allowed_use must compose successfully"
    );
}

// ── AU8: compose_n fails closed on any mismatch ──────────────────────────────

#[test]
fn au8_compose_n_fails_on_any_mismatch() {
    let ctxs = vec![
        ctx_with_use("use-a"),
        ctx_with_use("use-a"),
        ctx_with_use("use-b"), // mismatch
        ctx_with_use("use-a"),
    ];
    let result = compose_n(ctxs);
    assert!(
        matches!(result, Err(CompositionError::UseConflict)),
        "AU8: compose_n must fail closed when any context has different allowed_use"
    );
}

// ── AU9: Very long allowed_use: hash is stable and distinct ──────────────────

#[test]
fn au9_long_allowed_use_hash_stable() {
    let long_use: String = "x".repeat(10_001);
    let h1 = compute_provenance_hash("c", "z", "ctx", &long_use);
    let h2 = compute_provenance_hash("c", "z", "ctx", &long_use);
    assert_eq!(h1, h2, "AU9: same long string must produce same hash");

    let long_use_2: String = "x".repeat(10_000) + "y";
    let h3 = compute_provenance_hash("c", "z", "ctx", &long_use_2);
    assert_ne!(
        h1, h3,
        "AU9: long strings differing by one char must differ"
    );
}

// ── AU10: Token uses exact allowed_use bytes in hash ─────────────────────────

#[test]
fn au10_token_hash_bound_to_exact_allowed_use() {
    // Token computed with "use-correct" must not match context with "use-wrong"
    let j = compile(ctx_with_token_use("use-wrong", "use-correct")).unwrap();
    assert_eq!(
        j.permission,
        Permission::REF,
        "AU10: token bound to 'use-correct' cannot close gap in 'use-wrong' context; PROVENANCE_MISMATCH → REF"
    );
}

#[test]
fn au10_token_matches_context_allowed_use() {
    let mut ctx = ctx_with_token_use("use-match", "use-match");
    // close the gap manually so the profile is satisfied
    ctx.gaps[0] = GapRecord::closed("g1", "t");
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "AU10: token with matching allowed_use closes gap → DIA"
    );
}

// ── AU11: Token for use-A cannot close gap in use-B context ──────────────────

#[test]
fn au11_token_bound_to_other_use_cannot_close_gap() {
    let j = compile(ctx_with_token_use("use-B", "use-A")).unwrap();
    assert_eq!(
        j.permission,
        Permission::REF,
        "AU11: token for use-A must not close gap in use-B context; PROVENANCE_MISMATCH → REF"
    );
}

// ── AU12: Two tokens with different allowed_use: neither closes the gap ───────

#[test]
fn au12_two_tokens_wrong_use_neither_closes() {
    let gap_id = "g1";
    let hash_wrong_1 = compute_provenance_hash("claim-au", "z-au", "ctx-au", "use-wrong-1");
    let hash_wrong_2 = compute_provenance_hash("claim-au", "z-au", "ctx-au", "use-wrong-2");

    let ctx = ProofContext {
        claim_id: "claim-au".into(),
        candidate_id: "z-au".into(),
        context_id: "ctx-au".into(),
        context_fingerprint: "fp-au".into(),
        allowed_use: "use-correct".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open(gap_id, "t")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![
            ProofToken {
                token_id: "tok-1".into(),
                token_type: "TEST".into(),
                schema_version: "0.1".into(),
                status: TokenStatus::Valid,
                closes_gaps: vec![gap_id.into()],
                bounds_gaps: vec![],
                provenance_hash: hash_wrong_1,
                issued_at: Utc::now(),
                expires_at: None,
                issuer: "test".into(),
                details: serde_json::Value::Null,
                is_negative_control: false,
            },
            ProofToken {
                token_id: "tok-2".into(),
                token_type: "TEST".into(),
                schema_version: "0.1".into(),
                status: TokenStatus::Valid,
                closes_gaps: vec![gap_id.into()],
                bounds_gaps: vec![],
                provenance_hash: hash_wrong_2,
                issued_at: Utc::now(),
                expires_at: None,
                issuer: "test".into(),
                details: serde_json::Value::Null,
                is_negative_control: false,
            },
        ],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::REF,
        "AU12: two tokens with wrong allowed_use: PROVENANCE_MISMATCH → REF"
    );
}

// ── AU13: Mutation of allowed_use only (not other provenance fields) ──────────

#[test]
fn au13_only_allowed_use_differs_changes_hash() {
    let base = compute_provenance_hash("claim", "z", "ctx", "use-base");
    let mutated = compute_provenance_hash("claim", "z", "ctx", "use-mutated");
    assert_ne!(
        base, mutated,
        "AU13: changing only allowed_use must change provenance hash"
    );
    // Other fields unchanged should still match
    let same = compute_provenance_hash("claim", "z", "ctx", "use-base");
    assert_eq!(base, same, "AU13: identical inputs must produce same hash");
}

// ── AU14: Null bytes in allowed_use: treated as distinct ──────────────────────

#[test]
fn au14_null_bytes_are_distinct() {
    let h_plain = compute_provenance_hash("c", "z", "ctx", "use");
    let h_null = compute_provenance_hash("c", "z", "ctx", "use\0");
    let h_null_mid = compute_provenance_hash("c", "z", "ctx", "u\0se");
    assert_ne!(h_plain, h_null, "AU14: null suffix must differ");
    assert_ne!(h_plain, h_null_mid, "AU14: embedded null must differ");
    assert_ne!(
        h_null, h_null_mid,
        "AU14: different null positions must differ"
    );
}

// ── Proptest: single-character mutation changes provenance hash ───────────────

proptest! {
    #[test]
    fn prop_single_char_mutation_changes_hash(
        base_use in "[a-z]{4,16}",
        pos in 0usize..16,
        replacement in "[A-Z0-9]",
    ) {
        prop_assume!(!base_use.is_empty());
        let idx = pos % base_use.len();
        let mutated: String = base_use
            .char_indices()
            .map(|(i, c)| {
                if i == idx {
                    replacement.chars().next().unwrap_or('X')
                } else {
                    c
                }
            })
            .collect();
        prop_assume!(mutated != base_use);

        let h_base = compute_provenance_hash("c", "z", "ctx", &base_use);
        let h_mut = compute_provenance_hash("c", "z", "ctx", &mutated);
        prop_assert_ne!(
            h_base, h_mut,
            "single-char mutation to allowed_use must change provenance hash"
        );
    }
}
