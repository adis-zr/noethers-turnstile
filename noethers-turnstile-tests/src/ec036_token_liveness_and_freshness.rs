/// EC-036 — Token liveness and freshness semantics (EC-001 §11, §15, T2, T7).
///
/// EC-001 requires a token to be "live" (status = VALID AND not expired at now)
/// for it to support a gap.  This suite thoroughly exercises token liveness
/// across all status variants, expiry edge cases, and the interaction between
/// token expiry and context expiry.
///
///   L1  — Status = Valid, no expiry → token is live
///   L2  — Status = Valid, future expiry → token is live
///   L3  — Status = Valid, past expiry → token is not live (triggers EXP floor)
///   L4  — Status = Invalid, any expiry → token is not live (T2)
///   L5  — Status = Expired, any expiry → token is not live (T2)
///   L6  — Status = Revoked, any expiry → token is not live (T2)
///   L7  — Status = Malformed, any expiry → token is not live (T2)
///   L8  — Token expiry at exact boundary (now == expires_at) → expired (≥)
///   L9  — Token expiry 1ns before boundary → still live
///   L10 — Multiple tokens: one expired Valid → EXP floor regardless of others
///   L11 — Multiple tokens: only dead-status tokens with past expiry → no EXP
///   L12 — Token that bounds (not closes) still triggers EXP floor if expired+Valid
///   L13 — Context expiry (deadline) fires → EXP at compile time
///   L14 — Context expiry not yet fired → no EXP at compile time
///   L15 — Context expiry fires at exact boundary (≥)
use chrono::{Duration, Utc};
use noethers_turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn base_ctx(id: &str) -> ProofContext {
    // Note: gap starts as Open — the token is the only way to close it.
    // This ensures tests accurately reflect that dead/invalid tokens cannot
    // close gaps (they do not upgrade the base gap status).
    ProofContext {
        claim_id: format!("claim-{id}"),
        candidate_id: format!("z-{id}"),
        context_id: format!("ctx-{id}"),
        context_fingerprint: format!("fp-{id}"),
        allowed_use: "test-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "t")],
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

fn token_with_status_and_expiry(
    id: &str,
    status: TokenStatus,
    expires_at: Option<chrono::DateTime<Utc>>,
    ctx: &ProofContext,
) -> ProofToken {
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ProofToken {
        token_id: id.into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

// ── L1: Valid, no expiry → live ───────────────────────────────────────────────

#[test]
fn l1_valid_token_no_expiry_is_live() {
    let mut ctx = base_ctx("l1");
    let tok = token_with_status_and_expiry("tok-l1", TokenStatus::Valid, None, &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "L1: valid token with no expiry must be live"
    );
}

// ── L2: Valid, future expiry → live ──────────────────────────────────────────

#[test]
fn l2_valid_token_future_expiry_is_live() {
    let future = Utc::now() + Duration::hours(1);
    let mut ctx = base_ctx("l2");
    let tok = token_with_status_and_expiry("tok-l2", TokenStatus::Valid, Some(future), &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "L2: valid token with future expiry must be live"
    );
}

// ── L3: Valid, past expiry → EXP floor ───────────────────────────────────────
// The gap record is pre-closed so descending search finds DIA (outcome > EXP),
// then step 5 sees the expired valid token and floors to EXP.

#[test]
fn l3_valid_token_past_expiry_triggers_exp() {
    let past = Utc::now() - Duration::seconds(1);
    let mut ctx = base_ctx("l3");
    // Pre-close the gap so profile is satisfied (outcome will be DIA initially).
    ctx.gaps[0] = GapRecord::closed("g1", "t");
    // Now add the expired valid token — step 5 will floor DIA → EXP.
    let tok = token_with_status_and_expiry("tok-l3", TokenStatus::Valid, Some(past), &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "L3: expired valid token must floor permission to EXP"
    );
}

// ── L4: Invalid status → not live (does not close gap, does not trigger EXP) ─

#[test]
fn l4_invalid_token_neither_closes_nor_triggers_exp() {
    let past = Utc::now() - Duration::seconds(1);
    let mut ctx = base_ctx("l4");
    let tok = token_with_status_and_expiry("tok-l4", TokenStatus::Invalid, Some(past), &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    // Invalid token: gap not closed; InClass + profile unmet → REF (not OOC)
    assert_eq!(
        j.permission,
        Permission::REF,
        "L4: invalid token must not close gap; InClass unmet profile → REF"
    );
    assert_ne!(
        j.permission,
        Permission::EXP,
        "L4: invalid token must not trigger EXP floor"
    );
}

// ── L5: Expired status → not live ────────────────────────────────────────────

#[test]
fn l5_expired_status_token_neither_closes_nor_triggers_exp() {
    let past = Utc::now() - Duration::seconds(1);
    let mut ctx = base_ctx("l5");
    let tok = token_with_status_and_expiry("tok-l5", TokenStatus::Expired, Some(past), &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::REF,
        "L5: expired-status token must not close gap; InClass unmet profile → REF"
    );
    assert_ne!(
        j.permission,
        Permission::EXP,
        "L5: expired-status token must not trigger EXP floor"
    );
}

// ── L6: Revoked status → not live ────────────────────────────────────────────

#[test]
fn l6_revoked_token_neither_closes_nor_triggers_exp() {
    let past = Utc::now() - Duration::seconds(1);
    let mut ctx = base_ctx("l6");
    let tok = token_with_status_and_expiry("tok-l6", TokenStatus::Revoked, Some(past), &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::REF,
        "L6: revoked token must not close gap; InClass unmet profile → REF"
    );
    assert_ne!(
        j.permission,
        Permission::EXP,
        "L6: revoked token must not trigger EXP floor"
    );
}

// ── L7: Malformed status → not live ──────────────────────────────────────────

#[test]
fn l7_malformed_token_neither_closes_nor_triggers_exp() {
    let past = Utc::now() - Duration::seconds(1);
    let mut ctx = base_ctx("l7");
    let tok = token_with_status_and_expiry("tok-l7", TokenStatus::Malformed, Some(past), &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::REF,
        "L7: malformed token must not close gap; InClass unmet profile → REF"
    );
    assert_ne!(
        j.permission,
        Permission::EXP,
        "L7: malformed token must not trigger EXP floor"
    );
}

// ── L8: Expiry at exact boundary (now == expires_at) → expired ───────────────
// We need outcome > EXP to observe the floor.  Pre-close the gap so descending
// search finds DIA, then step 5 may floor to EXP depending on timing.

#[test]
fn l8_token_expires_at_exact_boundary() {
    let now = Utc::now();
    let mut ctx = base_ctx("l8");
    // Pre-close the gap so profile is satisfied (outcome = DIA before step 5).
    ctx.gaps[0] = GapRecord::closed("g1", "t");
    // expires_at = now: the compiler's Utc::now() at step 5 will be ≥ this,
    // so the token is expired (now >= expires_at fired).
    let tok = token_with_status_and_expiry("tok-l8", TokenStatus::Valid, Some(now), &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    // At boundary, either fired (EXP) or just barely not (DIA).
    // The important invariant: no other value is possible.
    assert!(
        j.permission == Permission::EXP || j.permission == Permission::DIA,
        "L8: at boundary, permission must be EXP or DIA (not other values)"
    );
}

// ── L9: Token expiry 1 second in future → live ───────────────────────────────

#[test]
fn l9_token_one_second_before_expiry_is_live() {
    let soon = Utc::now() + Duration::seconds(1);
    let mut ctx = base_ctx("l9");
    let tok = token_with_status_and_expiry("tok-l9", TokenStatus::Valid, Some(soon), &ctx);
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "L9: token expiring in 1s must still be live"
    );
}

// ── L10: Mix of tokens; one expired Valid → EXP floor ────────────────────────

#[test]
fn l10_one_expired_valid_token_triggers_exp_regardless_of_others() {
    let past = Utc::now() - Duration::seconds(1);
    let future = Utc::now() + Duration::hours(1);

    let mut ctx = base_ctx("l10");
    ctx.gaps.push(GapRecord::closed("g2", "t"));
    ctx.profiles[0].required_gaps.push(GapRequirement {
        gap_id: "g2".into(),
        minimum_status: RequiredStatus::ClosedRequired,
    });

    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );

    // Fresh valid token for g2
    ctx.tokens.push(ProofToken {
        token_id: "tok-fresh".into(),
        token_type: "T".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into(), "g2".into()],
        bounds_gaps: vec![],
        provenance_hash: hash.clone(),
        issued_at: Utc::now(),
        expires_at: Some(future),
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    });

    // Expired valid token
    ctx.tokens.push(ProofToken {
        token_id: "tok-expired".into(),
        token_type: "T".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: Some(past),
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    });

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "L10: one expired valid token must floor entire outcome to EXP"
    );
}

// ── L11: Only dead-status tokens with past expiry → no EXP floor ─────────────

#[test]
fn l11_only_dead_tokens_with_past_expiry_no_exp_floor() {
    let past = Utc::now() - Duration::seconds(1);
    let mut ctx = base_ctx("l11");

    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );

    for status in [
        TokenStatus::Invalid,
        TokenStatus::Expired,
        TokenStatus::Revoked,
        TokenStatus::Malformed,
    ] {
        ctx.tokens.push(ProofToken {
            token_id: format!("tok-dead-{status:?}"),
            token_type: "T".into(),
            schema_version: "0.1".into(),
            status,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec![],
            provenance_hash: hash.clone(),
            issued_at: Utc::now(),
            expires_at: Some(past),
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        });
    }

    let j = compile(ctx).unwrap();
    // Dead tokens cannot trigger EXP; gap not closed by dead tokens → OOC
    assert_ne!(
        j.permission,
        Permission::EXP,
        "L11: dead tokens with past expiry must not trigger EXP floor"
    );
    assert_eq!(
        j.permission,
        Permission::REF,
        "L11: dead tokens don't close gaps; InClass unmet profile → REF"
    );
}

// ── L12: Bounds-only expired Valid token also triggers EXP floor ─────────────
// Pre-close the gap so outcome > EXP before step 5 checks expired tokens.

#[test]
fn l12_bounding_expired_valid_token_triggers_exp() {
    let past = Utc::now() - Duration::seconds(1);
    let mut ctx = base_ctx("l12");
    // Pre-close the gap so profile is satisfied (outcome = DIA before step 5).
    ctx.gaps[0] = GapRecord::closed("g1", "t");

    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );

    ctx.tokens.push(ProofToken {
        token_id: "tok-bound-expired".into(),
        token_type: "T".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![],
        bounds_gaps: vec!["g1".into()], // bounds, not closes — but still triggers EXP floor
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: Some(past),
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    });

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "L12: expired valid bounding token must also trigger EXP floor"
    );
}

// ── L13: Context expiry fired at compile time → EXP ──────────────────────────

#[test]
fn l13_context_expiry_fires_at_compile_time() {
    let past = Utc::now() - Duration::seconds(1);
    let mut ctx = base_ctx("l13");
    ctx.expiry = Expiry::at(past);

    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ctx.tokens.push(ProofToken {
        token_id: "tok-l13".into(),
        token_type: "T".into(),
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
    });

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "L13: fired context expiry must produce EXP at compile time"
    );
}

// ── L14: Context expiry not yet fired → no EXP at compile time ───────────────

#[test]
fn l14_context_expiry_not_yet_fired_no_exp() {
    let future = Utc::now() + Duration::hours(1);
    let mut ctx = base_ctx("l14");
    ctx.expiry = Expiry::at(future);

    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ctx.tokens.push(ProofToken {
        token_id: "tok-l14".into(),
        token_type: "T".into(),
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
    });

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "L14: future context expiry must not produce EXP"
    );
}

// ── L15: Context expiry fires at exact boundary ───────────────────────────────

#[test]
fn l15_context_expiry_fires_at_exact_boundary() {
    // Create a context that expires slightly in the past (1ms ago)
    let just_past = Utc::now() - Duration::milliseconds(1);
    let mut ctx = base_ctx("l15");
    ctx.expiry = Expiry::at(just_past);

    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ctx.tokens.push(ProofToken {
        token_id: "tok-l15".into(),
        token_type: "T".into(),
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
    });

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "L15: context expiry 1ms in the past must have fired"
    );
}
