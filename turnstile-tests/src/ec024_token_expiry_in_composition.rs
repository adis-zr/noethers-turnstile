/// EC-024 — Token expiry masking in composition.
///
/// `tokens_content_equal` deliberately excludes `issued_at`, `expires_at`, and
/// `status` from conflict detection to allow clock-skew tolerance.  This means
/// that when two contexts carry the "same" token (same token_id, same content)
/// but with different `expires_at` values, composition silently keeps the token
/// from `g1`, discarding the possibly-earlier expiry from `g2`.
///
/// This suite documents and tests that behaviour so callers are not surprised:
///
///   X1 — Compose(g1 has expires_at=T1, g2 has same token with expires_at=T2
///         where T2 < T1): composed token keeps T1 (g1's expiry).
///   X2 — Compose(g1 has no expiry on token, g2 same token has expiry=T):
///         composed token has no expiry (g1 wins).
///   X3 — Compose(g1 token has status=Revoked, g2 same token has Valid):
///         composed token keeps g1's Revoked status.
///   X4 — Token conflict fires when token_id matches but token_type differs
///         (content equality covers token_type).
///   X5 — Identical tokens (same content including expires_at) deduplicate
///         without conflict.
///   X6 — Context expiry (not token expiry) is always the minimum of both
///         contexts and is independent of token expiry masking.
///
/// NOTE: X1 and X2 document known behaviour, not bugs.  Callers who care about
/// early token expiry should use the minimum expires_at of the two when building
/// their contexts before composing, or rely on context-level expiry.
use chrono::{Duration, Utc};
use turnstile_core::{
    compose,
    context::{Membership, ProofContext, Scope},
    error::CompositionError,
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn base_ctx(suffix: &str) -> ProofContext {
    ProofContext {
        claim_id: "claim-x".into(),
        candidate_id: "z-x".into(),
        context_id: "ctx-x".into(),
        context_fingerprint: format!("fp-x-{suffix}"),
        allowed_use: "x-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "gap")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

fn same_token(
    _suffix: &str,
    expires_at: Option<chrono::DateTime<Utc>>,
    status: TokenStatus,
) -> ProofToken {
    let hash = compute_provenance_hash("claim-x", "z-x", "ctx-x", "x-use");
    ProofToken {
        token_id: "shared-tok".into(),
        token_type: "CLOSE".into(),
        schema_version: "0.1".into(),
        status,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now() - Duration::hours(1),
        expires_at,
        // Use a fixed issuer so tokens_content_equal considers these "the same token".
        // The dedup logic checks issuer as part of content equality.
        issuer: "shared-issuer".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

// ── X1: Earlier expiry in g2 is silently dropped ─────────────────────────────

#[test]
fn x1_g1_expiry_wins_when_g2_has_earlier_expiry() {
    let later = Utc::now() + Duration::hours(10);
    let earlier = Utc::now() + Duration::hours(2);

    let mut g1 = base_ctx("x1");
    let mut g2 = base_ctx("x1");
    g1.context_fingerprint = "fp-x1-a".into();
    g2.context_fingerprint = "fp-x1-b".into();

    g1.tokens
        .push(same_token("x1-g1", Some(later), TokenStatus::Valid));
    g2.tokens
        .push(same_token("x1-g2", Some(earlier), TokenStatus::Valid));

    let composed = compose(g1, g2).unwrap();
    let tok = composed
        .tokens
        .iter()
        .find(|t| t.token_id == "shared-tok")
        .unwrap();

    // The token was deduplicated (same content-equal key), keeping g1's version.
    // g1's expires_at is `later`; g2's earlier expiry was discarded.
    assert_eq!(
        tok.expires_at,
        Some(later),
        "X1: composition keeps g1's token (including its later expiry), silently dropping g2's earlier expiry. \
         Callers must pre-minimise expiry before composing if this matters."
    );
}

// ── X2: g2 token with expiry — no-expiry g1 token wins ───────────────────────

#[test]
fn x2_g1_no_expiry_token_masks_g2_expiry() {
    let future = Utc::now() + Duration::hours(5);

    let mut g1 = base_ctx("x2");
    let mut g2 = base_ctx("x2");
    g1.context_fingerprint = "fp-x2-a".into();
    g2.context_fingerprint = "fp-x2-b".into();

    g1.tokens
        .push(same_token("x2-g1", None, TokenStatus::Valid)); // no expiry
    g2.tokens
        .push(same_token("x2-g2", Some(future), TokenStatus::Valid)); // has expiry

    let composed = compose(g1, g2).unwrap();
    let tok = composed
        .tokens
        .iter()
        .find(|t| t.token_id == "shared-tok")
        .unwrap();

    // g1's token has no expiry; g2's expiry is discarded.
    assert_eq!(
        tok.expires_at, None,
        "X2: g1's no-expiry token wins and discards g2's expiry. \
         Callers should pre-apply context-level expiry to guard this."
    );
}

// ── X3: g1's Revoked status masks g2's Valid status ──────────────────────────

#[test]
fn x3_g1_revoked_status_masks_g2_valid_status() {
    let mut g1 = base_ctx("x3");
    let mut g2 = base_ctx("x3");
    g1.context_fingerprint = "fp-x3-a".into();
    g2.context_fingerprint = "fp-x3-b".into();

    g1.tokens
        .push(same_token("x3-g1", None, TokenStatus::Revoked));
    g2.tokens
        .push(same_token("x3-g2", None, TokenStatus::Valid));

    let composed = compose(g1, g2).unwrap();
    let tok = composed
        .tokens
        .iter()
        .find(|t| t.token_id == "shared-tok")
        .unwrap();

    // g1's Revoked status is kept (g2's Valid is ignored after dedup).
    assert_eq!(
        tok.status,
        TokenStatus::Revoked,
        "X3: g1's Revoked token status masks g2's Valid status after dedup"
    );
}

// ── X4: Token conflict fires on different token_type ─────────────────────────

#[test]
fn x4_different_token_type_triggers_conflict() {
    let hash = compute_provenance_hash("claim-x", "z-x", "ctx-x", "x-use");
    let tok_a = ProofToken {
        token_id: "conflict-tok".into(),
        token_type: "CLOSE".into(), // different type
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash.clone(),
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "issuer".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    let tok_b = ProofToken {
        token_id: "conflict-tok".into(),
        token_type: "BOUND".into(), // different type → content conflict
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "issuer".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };

    let mut g1 = base_ctx("x4a");
    let mut g2 = base_ctx("x4b");
    g1.context_fingerprint = "fp-x4-a".into();
    g2.context_fingerprint = "fp-x4-b".into();
    g1.tokens.push(tok_a);
    g2.tokens.push(tok_b);

    let result = compose(g1, g2);
    assert!(
        matches!(result, Err(CompositionError::TokenConflict { .. })),
        "X4: different token_type for same token_id must produce TokenConflict"
    );
}

// ── X5: Identical tokens deduplicate silently ────────────────────────────────

#[test]
fn x5_identical_tokens_deduplicate_without_conflict() {
    let hash = compute_provenance_hash("claim-x", "z-x", "ctx-x", "x-use");
    let tok = ProofToken {
        token_id: "dedup-tok".into(),
        token_type: "CLOSE".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "issuer".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };

    let mut g1 = base_ctx("x5a");
    let mut g2 = base_ctx("x5b");
    g1.context_fingerprint = "fp-x5-a".into();
    g2.context_fingerprint = "fp-x5-b".into();
    g1.tokens.push(tok.clone());
    g2.tokens.push(tok);

    let composed = compose(g1, g2).unwrap();
    let tok_count = composed
        .tokens
        .iter()
        .filter(|t| t.token_id == "dedup-tok")
        .count();
    assert_eq!(
        tok_count, 1,
        "X5: identical tokens must deduplicate to a single token in the composed context"
    );
}

// ── X6: Context expiry is always minimum, independent of token expiry ─────────

#[test]
fn x6_context_expiry_is_minimum_of_both() {
    let soon = Utc::now() + Duration::hours(1);
    let later = Utc::now() + Duration::hours(10);

    let mut g1 = base_ctx("x6a");
    let mut g2 = base_ctx("x6b");
    g1.context_fingerprint = "fp-x6-a".into();
    g2.context_fingerprint = "fp-x6-b".into();
    g1.expiry = Expiry::at(later);
    g2.expiry = Expiry::at(soon);

    let composed = compose(g1, g2).unwrap();
    assert_eq!(
        composed.expiry.deadline,
        Some(soon),
        "X6: context expiry must be the minimum of both contexts' expiry deadlines"
    );
}
