/// EC-026 — Dead-token expiry semantics.
///
/// Only a token that is *live* (status = Valid) and whose `expires_at` deadline
/// has passed triggers the EXP floor in step 5 of the compiler.  Dead tokens
/// (Invalid, Expired, Revoked, Malformed) already carry no evidentiary weight
/// and must not cause an EXP floor — doing so would mean dead evidence has the
/// same effect as recently-expired live evidence, which violates sound semantics.
///
/// After the fix in compiler.rs step 5, this suite verifies:
///
///   D1 — Valid token with past expires_at → EXP floor (baseline, still works).
///   D2 — Invalid token with past expires_at → no EXP floor.
///   D3 — TokenStatus::Expired token with past expires_at → no EXP floor.
///   D4 — Revoked token with past expires_at → no EXP floor.
///   D5 — Malformed token with past expires_at → no EXP floor.
///   D6 — Mixed: Valid expired + Invalid expired → EXP (Valid wins).
///   D7 — All dead with past expiry, Valid satisfies profile → outcome is DIA
///         (no EXP floor from dead tokens, profile satisfied).
///   D8 — No tokens at all → no EXP floor.
///   D9 — Token with status=Valid but no expires_at → no EXP floor ever.
///   D10 — TokenStatus::Expired with future expires_at → no EXP floor
///          (status semantics dominate, not the deadline).
use chrono::{Duration, Utc};
use noethers_noethers_turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn ctx_with_tokens(suffix: &str, tokens: Vec<ProofToken>) -> ProofContext {
    let claim_id = format!("claim-d-{suffix}");
    let candidate_id = format!("z-d-{suffix}");
    let context_id = format!("ctx-d-{suffix}");
    let allowed_use = "d-use";

    // Note: valid closing token must be pre-computed with these fields.
    ProofContext {
        claim_id,
        candidate_id,
        context_id,
        context_fingerprint: format!("fp-d-{suffix}"),
        allowed_use: allowed_use.into(),
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
        tokens,
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

fn valid_closing_token(
    suffix: &str,
    ctx: &ProofContext,
    expires_at: Option<chrono::DateTime<Utc>>,
) -> ProofToken {
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ProofToken {
        token_id: format!("valid-{suffix}"),
        token_type: "CLOSE".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now() - Duration::hours(2),
        expires_at,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

fn dead_token(
    suffix: &str,
    ctx: &ProofContext,
    status: TokenStatus,
    expires_at: Option<chrono::DateTime<Utc>>,
) -> ProofToken {
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ProofToken {
        token_id: format!("dead-{suffix}"),
        token_type: "CLOSE".into(),
        schema_version: "0.1".into(),
        status,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now() - Duration::hours(3),
        expires_at,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

// ── D1: Valid expired token still triggers EXP (baseline) ────────────────────

#[test]
fn d1_valid_expired_token_triggers_exp() {
    let past = Utc::now() - Duration::hours(1);
    let future = Utc::now() + Duration::hours(24);

    // We need a non-expired valid token to satisfy the profile (otherwise outcome
    // stays OOC and OOC < EXP so the floor wouldn't apply).
    let placeholder = ctx_with_tokens("d1", vec![]);
    let good_tok = valid_closing_token("d1-good", &placeholder, Some(future));
    let exp_tok = ProofToken {
        token_id: "d1-expired".into(),
        token_type: "OTHER".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![],
        bounds_gaps: vec![],
        provenance_hash: {
            compute_provenance_hash(
                &placeholder.claim_id,
                &placeholder.candidate_id,
                &placeholder.context_id,
                &placeholder.allowed_use,
            )
        },
        issued_at: Utc::now() - Duration::hours(5),
        expires_at: Some(past),
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    let mut ctx = placeholder;
    ctx.tokens = vec![good_tok, exp_tok];
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "D1: Valid token with past expires_at must trigger EXP floor"
    );
}

// ── D2: Invalid token with past expires_at → no EXP ──────────────────────────

#[test]
fn d2_invalid_token_with_past_expiry_does_not_trigger_exp() {
    let past = Utc::now() - Duration::hours(1);
    let future = Utc::now() + Duration::hours(24);

    let placeholder = ctx_with_tokens("d2", vec![]);
    let good_tok = valid_closing_token("d2-good", &placeholder, Some(future));
    let dead = dead_token("d2", &placeholder, TokenStatus::Invalid, Some(past));
    let mut ctx = placeholder;
    ctx.tokens = vec![good_tok, dead];
    let j = compile(ctx).unwrap();
    assert_ne!(
        j.permission,
        Permission::EXP,
        "D2: Invalid token with past expiry must NOT trigger EXP floor"
    );
    assert_eq!(
        j.permission,
        Permission::DIA,
        "D2: outcome must be DIA (profile satisfied by valid token)"
    );
}

// ── D3: TokenStatus::Expired with past expires_at → no EXP ───────────────────

#[test]
fn d3_token_status_expired_with_past_expiry_does_not_trigger_exp() {
    let past = Utc::now() - Duration::hours(1);
    let future = Utc::now() + Duration::hours(24);

    let placeholder = ctx_with_tokens("d3", vec![]);
    let good_tok = valid_closing_token("d3-good", &placeholder, Some(future));
    let dead = dead_token("d3", &placeholder, TokenStatus::Expired, Some(past));
    let mut ctx = placeholder;
    ctx.tokens = vec![good_tok, dead];
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "D3: token with status=Expired and past expires_at must not trigger EXP floor"
    );
}

// ── D4: Revoked token with past expires_at → no EXP ──────────────────────────

#[test]
fn d4_revoked_token_with_past_expiry_does_not_trigger_exp() {
    let past = Utc::now() - Duration::hours(1);
    let future = Utc::now() + Duration::hours(24);

    let placeholder = ctx_with_tokens("d4", vec![]);
    let good_tok = valid_closing_token("d4-good", &placeholder, Some(future));
    let dead = dead_token("d4", &placeholder, TokenStatus::Revoked, Some(past));
    let mut ctx = placeholder;
    ctx.tokens = vec![good_tok, dead];
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "D4: Revoked token with past expiry must not trigger EXP floor"
    );
}

// ── D5: Malformed token with past expires_at → no EXP ────────────────────────

#[test]
fn d5_malformed_token_with_past_expiry_does_not_trigger_exp() {
    let past = Utc::now() - Duration::hours(1);
    let future = Utc::now() + Duration::hours(24);

    let placeholder = ctx_with_tokens("d5", vec![]);
    let good_tok = valid_closing_token("d5-good", &placeholder, Some(future));
    let dead = dead_token("d5", &placeholder, TokenStatus::Malformed, Some(past));
    let mut ctx = placeholder;
    ctx.tokens = vec![good_tok, dead];
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "D5: Malformed token with past expiry must not trigger EXP floor"
    );
}

// ── D6: Mixed Valid-expired + Invalid-expired → EXP ──────────────────────────

#[test]
fn d6_valid_expired_dominates_dead_expired() {
    let past = Utc::now() - Duration::hours(1);
    let future = Utc::now() + Duration::hours(24);

    let placeholder = ctx_with_tokens("d6", vec![]);
    let good_tok = valid_closing_token("d6-good", &placeholder, Some(future));
    let valid_expired = ProofToken {
        token_id: "d6-valid-exp".into(),
        token_type: "OTHER".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![],
        bounds_gaps: vec![],
        provenance_hash: {
            compute_provenance_hash(
                &placeholder.claim_id,
                &placeholder.candidate_id,
                &placeholder.context_id,
                &placeholder.allowed_use,
            )
        },
        issued_at: Utc::now() - Duration::hours(5),
        expires_at: Some(past),
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    let dead_expired = dead_token("d6-dead", &placeholder, TokenStatus::Invalid, Some(past));
    let mut ctx = placeholder;
    ctx.tokens = vec![good_tok, valid_expired, dead_expired];
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "D6: valid expired token must cause EXP even when a dead expired token is also present"
    );
}

// ── D7: All dead with past expiry, Valid satisfies profile → DIA ──────────────

#[test]
fn d7_only_dead_expired_tokens_and_valid_profile_token_gives_dia() {
    let past = Utc::now() - Duration::hours(1);
    let future = Utc::now() + Duration::hours(24);

    let placeholder = ctx_with_tokens("d7", vec![]);
    let good_tok = valid_closing_token("d7-good", &placeholder, Some(future));
    let dead1 = dead_token("d7a", &placeholder, TokenStatus::Invalid, Some(past));
    let dead2 = dead_token("d7b", &placeholder, TokenStatus::Revoked, Some(past));
    let dead3 = dead_token("d7c", &placeholder, TokenStatus::Malformed, Some(past));
    let mut ctx = placeholder;
    ctx.tokens = vec![good_tok, dead1, dead2, dead3];
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "D7: valid non-expired token must yield DIA even with many dead expired tokens present"
    );
}

// ── D8: No tokens → no EXP floor ─────────────────────────────────────────────

#[test]
fn d8_no_tokens_no_exp_floor() {
    let ctx = ctx_with_tokens("d8", vec![]);
    let j = compile(ctx).unwrap();
    // No profile satisfied (no closing token) → OOC, not EXP.
    assert_ne!(
        j.permission,
        Permission::EXP,
        "D8: context with no tokens must not produce EXP floor"
    );
}

// ── D9: Valid token, no expires_at → no EXP floor ────────────────────────────

#[test]
fn d9_valid_token_without_expiry_no_exp_floor() {
    let placeholder = ctx_with_tokens("d9", vec![]);
    let tok = valid_closing_token("d9", &placeholder, None);
    let mut ctx = placeholder;
    ctx.tokens = vec![tok];
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "D9: valid token with no expiry must not trigger EXP floor"
    );
}

// ── D10: TokenStatus::Expired with future expires_at → no EXP floor ──────────

#[test]
fn d10_token_status_expired_with_future_deadline_no_exp_floor() {
    let future = Utc::now() + Duration::hours(24);
    let also_future = Utc::now() + Duration::hours(1);

    let placeholder = ctx_with_tokens("d10", vec![]);
    // A dead-status token (Expired) with a *future* expires_at.
    let dead_future = dead_token("d10-dead", &placeholder, TokenStatus::Expired, Some(future));
    let good_tok = valid_closing_token("d10-good", &placeholder, Some(also_future));
    let mut ctx = placeholder;
    ctx.tokens = vec![good_tok, dead_future];
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "D10: token with status=Expired but future deadline must not trigger EXP floor"
    );
}
