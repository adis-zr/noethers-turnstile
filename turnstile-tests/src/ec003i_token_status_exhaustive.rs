/// EC-003I — Token status exhaustive: all TokenStatus variants are fail-closed.
///
/// Covers theorems:
///   T2  — Token validity soundness: only Valid tokens contribute
///   T7  — Expiry soundness: expired token → gap stays Open
///
/// TokenStatus variants: Valid | Invalid | Expired | Revoked | Malformed
///
/// All non-Valid statuses must cause the token to be rejected, leaving any
/// associated gap at its existing status (Open if it was Open).
///
/// Also tests: token-level expiry via expires_at vs. context-level expiry.
use chrono::{Duration, Utc};
use proptest::prelude::*;
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn ctx_with_status(status: TokenStatus) -> ProofContext {
    let claim_id = "c-ts";
    let candidate_id = "z-ts";
    let context_id = "ctx-ts";
    let allowed_use = "ts-use";
    let gap_id = "g1";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);
    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-ts".into(),
        allowed_use: allowed_use.into(),
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
            token_id: "tok-ts".into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status,
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
        membership: Membership::InClass,
    }
}

// ── Only Valid token closes the gap ─────────────────────────────────────────

#[test]
fn valid_token_closes_gap() {
    let mut ctx = ctx_with_status(TokenStatus::Valid);
    // Update gap to Closed (the token attests it)
    ctx.gaps[0] = GapRecord::closed("g1", "t");
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA);
}

#[test]
fn invalid_token_does_not_close_gap() {
    let j = compile(ctx_with_status(TokenStatus::Invalid)).unwrap();
    assert_eq!(
        j.permission,
        Permission::REF,
        "Invalid token must not close gap; in-class with unmet profile → REF"
    );
}

#[test]
fn expired_status_token_does_not_close_gap() {
    let j = compile(ctx_with_status(TokenStatus::Expired)).unwrap();
    assert_eq!(
        j.permission,
        Permission::REF,
        "Expired status token must not close gap; in-class with unmet profile → REF"
    );
}

#[test]
fn revoked_token_does_not_close_gap() {
    let j = compile(ctx_with_status(TokenStatus::Revoked)).unwrap();
    assert_eq!(
        j.permission,
        Permission::REF,
        "Revoked token must not close gap; in-class with unmet profile → REF"
    );
}

#[test]
fn malformed_token_does_not_close_gap() {
    let j = compile(ctx_with_status(TokenStatus::Malformed)).unwrap();
    assert_eq!(
        j.permission,
        Permission::REF,
        "Malformed token must not close gap; in-class with unmet profile → REF"
    );
}

// ── Token-level expiry (expires_at): expired by timestamp → not live ─────────

#[test]
fn token_expired_by_timestamp_gives_exp_at_compile() {
    let past = Utc::now() - Duration::seconds(1);
    let claim_id = "c-texp";
    let candidate_id = "z-texp";
    let context_id = "ctx-texp";
    let allowed_use = "texp-use";
    let gap_id = "g1";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);
    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-texp".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed(gap_id, "t")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-expired".into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![gap_id.into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now() - Duration::seconds(10),
            expires_at: Some(past), // already expired
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        }],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "token expired by timestamp must floor to EXP"
    );
}

#[test]
fn token_not_yet_expired_contributes_normally() {
    let future = Utc::now() + Duration::seconds(3600);
    let claim_id = "c-tfut";
    let candidate_id = "z-tfut";
    let context_id = "ctx-tfut";
    let allowed_use = "tfut-use";
    let gap_id = "g1";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);
    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-tfut".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed(gap_id, "t")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-future".into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![gap_id.into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: Some(future), // not expired yet
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        }],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "non-expired token must contribute"
    );
}

// ── Context-level expiry vs token-level expiry: both independently floor to EXP ─

#[test]
fn context_expiry_independent_of_token_expiry() {
    // Context already expired, token valid → EXP from context-level expiry
    let claim_id = "c-ctx-exp";
    let candidate_id = "z-ctx-exp";
    let context_id = "ctx-ctx-exp";
    let allowed_use = "ctx-exp-use";
    let gap_id = "g1";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);
    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-ctx-exp".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed(gap_id, "t")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-ctx-exp".into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![gap_id.into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: Some(Utc::now() + Duration::seconds(3600)), // token not expired
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        }],
        expiry: Expiry::at(Utc::now() - Duration::seconds(1)), // context expired
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "context-level expiry must floor to EXP"
    );
}

// ── Both token and context expired: still EXP (not double-counted) ────────────

#[test]
fn both_token_and_context_expired_gives_exp() {
    let past = Utc::now() - Duration::seconds(1);
    let claim_id = "c-both-exp";
    let candidate_id = "z-both-exp";
    let context_id = "ctx-both-exp";
    let allowed_use = "both-exp-use";
    let gap_id = "g1";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);
    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-both-exp".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed(gap_id, "t")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-both-exp".into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![gap_id.into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now() - Duration::seconds(10),
            expires_at: Some(past),
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        }],
        expiry: Expiry::at(past),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::EXP);
}

// ── Multiple gaps, one expired token: only the expired gap is downgraded ──────

#[test]
fn one_expired_token_among_many_floors_to_exp() {
    let claim_id = "c-multi-exp";
    let candidate_id = "z-multi-exp";
    let context_id = "ctx-multi-exp";
    let allowed_use = "multi-exp-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);
    let past = Utc::now() - Duration::seconds(1);

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-multi-exp".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "t"), GapRecord::closed("g2", "t")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![
                GapRequirement {
                    gap_id: "g1".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                },
                GapRequirement {
                    gap_id: "g2".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                },
            ],
        }],
        tokens: vec![
            ProofToken {
                token_id: "tok-live".into(),
                token_type: "TEST".into(),
                schema_version: "0.1".into(),
                status: TokenStatus::Valid,
                closes_gaps: vec!["g1".into()],
                bounds_gaps: vec![],
                provenance_hash: hash.clone(),
                issued_at: Utc::now(),
                expires_at: None, // live
                issuer: "test".into(),
                details: serde_json::Value::Null,
                is_negative_control: false,
            },
            ProofToken {
                token_id: "tok-expired".into(),
                token_type: "TEST".into(),
                schema_version: "0.1".into(),
                status: TokenStatus::Valid,
                closes_gaps: vec!["g2".into()],
                bounds_gaps: vec![],
                provenance_hash: hash,
                issued_at: Utc::now() - Duration::seconds(10),
                expires_at: Some(past), // expired
                issuer: "test".into(),
                details: serde_json::Value::Null,
                is_negative_control: false,
            },
        ],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "any expired token must floor to EXP"
    );
}

// ── Proptest: any non-Valid status → gap stays Open, no promotion ─────────────

fn arb_non_valid_status() -> impl Strategy<Value = TokenStatus> {
    prop_oneof![
        Just(TokenStatus::Invalid),
        Just(TokenStatus::Expired),
        Just(TokenStatus::Revoked),
        Just(TokenStatus::Malformed),
    ]
}

proptest! {
    #[test]
    fn prop_non_valid_token_never_closes_gap(status in arb_non_valid_status()) {
        let j = compile(ctx_with_status(status)).unwrap();
        // Non-valid token → gap stays Open → profile not satisfied → REF (in-class, profile defined)
        prop_assert!(j.permission <= Permission::REF,
            "non-Valid token {:?} must not emit above REF; got {:?}", status, j.permission);
    }
}
