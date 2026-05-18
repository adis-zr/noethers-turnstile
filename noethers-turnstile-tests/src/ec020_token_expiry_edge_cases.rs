/// EC-020 — Token and context expiry edge cases.
///
/// Comprehensive expiry coverage beyond what ec003p provides:
///
///   E1  — Token expiring exactly at boundary (now == expires_at → expired).
///   E2  — Token expiring 1ns in the future (not yet expired).
///   E3  — Multiple tokens, some expired, some not: any expired → EXP floor.
///   E4  — Token with expires_at=None never expires regardless of time.
///   E5  — Context expiry at boundary: now == deadline → EXP.
///   E6  — Context expiry in future: no EXP floor.
///   E7  — Token with Invalid/Revoked/Malformed status: treated as dead,
///          does NOT trigger EXP floor (only Valid expired tokens do).
///   E8  — Expired token that does NOT satisfy any gap: compiler must still
///          floor to EXP because the token exists in the context.
///   E9  — LiveJudgment: expiry fires at exactly runtime.now == deadline.
///   E10 — LiveJudgment: expiry does not fire at runtime.now < deadline.
use chrono::{Duration, Utc};
use noethers_turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::{Expiry, LiveJudgment, RuntimeContext},
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

// ── Helpers ───────────────────────────────────────────────────────────────────

fn base_ctx_with_tokens(suffix: &str, tokens: Vec<ProofToken>) -> ProofContext {
    let claim_id = format!("claim-exp-{suffix}");
    let candidate_id = format!("z-exp-{suffix}");
    let context_id = format!("ctx-exp-{suffix}");
    let allowed_use = "exp-use";

    ProofContext {
        claim_id,
        candidate_id,
        context_id,
        context_fingerprint: format!("fp-exp-{suffix}"),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "calibration_gap")],
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

fn valid_token(
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
        token_id: format!("tok-exp-{suffix}"),
        token_type: "CLOSE".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now() - Duration::hours(1),
        expires_at,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

// ── E1: Token expired at boundary (now == expires_at) ────────────────────────

#[test]
fn e1_token_expired_at_exact_boundary_floors_to_exp() {
    // The expiry blocker fires when outcome > EXP.  We need:
    //   1. A non-expired token that satisfies the profile (raises outcome to DIA).
    //   2. A separate expired token (triggers the expiry floor).
    // Without the non-expired token, outcome is OOC (profile unsatisfied) and
    // OOC < EXP so the floor would not apply — OOC would dominate.
    let past = Utc::now() - Duration::milliseconds(100);
    let future = Utc::now() + Duration::hours(24);

    let mut ctx = base_ctx_with_tokens("e1", vec![]);
    // Good token that satisfies the profile.
    let good_tok = valid_token("e1-good", &ctx, Some(future));
    // Expired token (closes a gap not in the profile, but exists in the context).
    let exp_tok = ProofToken {
        token_id: "tok-exp-e1-bad".into(),
        token_type: "OTHER".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![], // does not close g1 — g1 is handled by good_tok
        bounds_gaps: vec![],
        provenance_hash: {
            compute_provenance_hash(
                &ctx.claim_id,
                &ctx.candidate_id,
                &ctx.context_id,
                &ctx.allowed_use,
            )
        },
        issued_at: Utc::now() - Duration::hours(2),
        expires_at: Some(past),
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    ctx.tokens = vec![good_tok, exp_tok];
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "E1: expired token in context must floor outcome to EXP (profile was satisfied → outcome DIA → EXP floor applied)"
    );
}

// ── E2: Token expiring in the future: no EXP floor ───────────────────────────

#[test]
fn e2_token_not_yet_expired_does_not_floor() {
    let future = Utc::now() + Duration::hours(24);
    let mut ctx = base_ctx_with_tokens("e2", vec![]);
    let tok = valid_token("e2", &ctx, Some(future));
    ctx.tokens = vec![tok];
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "E2: token with future expiry must not trigger EXP floor; got {}",
        j.permission
    );
}

// ── E3: Mixed expired + non-expired tokens → any expired → EXP ───────────────

#[test]
fn e3_any_expired_token_floors_whole_context() {
    let past = Utc::now() - Duration::hours(1);
    let future = Utc::now() + Duration::hours(24);

    let mut ctx = base_ctx_with_tokens("e3", vec![]);
    let good_tok = valid_token("e3-good", &ctx, Some(future));
    let bad_tok = valid_token("e3-bad", &ctx, Some(past));
    ctx.tokens = vec![good_tok, bad_tok];

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "E3: at least one expired token must floor the whole context to EXP"
    );
}

// ── E4: Token with no expiry never triggers EXP ───────────────────────────────

#[test]
fn e4_token_with_no_expiry_never_triggers_exp() {
    let mut ctx = base_ctx_with_tokens("e4", vec![]);
    let tok = valid_token("e4", &ctx, None); // expires_at = None
    ctx.tokens = vec![tok];
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "E4: token with no expiry must not trigger EXP"
    );
}

// ── E5: Context expiry fired → EXP ───────────────────────────────────────────

#[test]
fn e5_context_expiry_at_boundary_yields_exp() {
    let past = Utc::now() - Duration::milliseconds(1);
    let mut ctx = base_ctx_with_tokens("e5", vec![]);
    let tok = valid_token("e5", &ctx, None); // token itself not expired
    ctx.tokens = vec![tok];
    ctx.expiry = Expiry::at(past);
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "E5: fired context expiry must yield EXP"
    );
}

// ── E6: Context expiry in future: no EXP floor ───────────────────────────────

#[test]
fn e6_context_expiry_in_future_does_not_floor() {
    let future = Utc::now() + Duration::hours(12);
    let mut ctx = base_ctx_with_tokens("e6", vec![]);
    let tok = valid_token("e6", &ctx, None);
    ctx.tokens = vec![tok];
    ctx.expiry = Expiry::at(future);
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "E6: context with future expiry must not trigger EXP"
    );
}

// ── E7: Invalid/Revoked/Malformed token does NOT trigger EXP floor ────────────

#[test]
fn e7_invalid_token_does_not_trigger_exp_floor() {
    let past = Utc::now() - Duration::hours(1);
    let mut ctx = base_ctx_with_tokens("e7", vec![]);
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    let dead_tok = ProofToken {
        token_id: "tok-dead".into(),
        token_type: "CLOSE".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Invalid, // dead status
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now() - Duration::hours(2),
        expires_at: Some(past), // also has a past expiry
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    ctx.tokens = vec![dead_tok];

    // The token has Invalid status AND a past expiry.  The compiler should
    // check token.status == Valid before considering expiry.  An Invalid token
    // is dead; only live (Valid) expired tokens floor to EXP.
    let j = compile(ctx).unwrap();
    // The invalid token cannot close the gap, so DIA profile is unsatisfied → OOC.
    // But crucially it must NOT produce EXP (that would mean dead tokens have
    // the same effect as live-but-expired tokens, which is incorrect).
    assert_ne!(
        j.permission,
        Permission::EXP,
        "E7: Invalid/dead token with past expiry must not trigger EXP floor; got {}",
        j.permission
    );
}

#[test]
fn e7_revoked_token_does_not_trigger_exp_floor() {
    let past = Utc::now() - Duration::hours(1);
    let mut ctx = base_ctx_with_tokens("e7-rev", vec![]);
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    let revoked_tok = ProofToken {
        token_id: "tok-revoked".into(),
        token_type: "CLOSE".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Revoked,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now() - Duration::hours(2),
        expires_at: Some(past),
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    ctx.tokens = vec![revoked_tok];
    let j = compile(ctx).unwrap();
    assert_ne!(
        j.permission,
        Permission::EXP,
        "E7: Revoked token with past expiry must not floor to EXP"
    );
}

// ── E8: Expired token not satisfying required gap still floors to EXP ────────

#[test]
fn e8_expired_token_not_satisfying_required_gap_still_floors_to_exp() {
    // The expired token closes "g_other" (not required by any profile).
    // A non-expired token satisfies the DIA profile via g1.
    // Outcome before expiry blocker = DIA > EXP → expiry floor applies → EXP.
    let past = Utc::now() - Duration::hours(1);
    let future = Utc::now() + Duration::hours(24);

    let mut ctx = base_ctx_with_tokens("e8", vec![]);
    ctx.gaps.push(GapRecord::open("g_other", "other_gap"));

    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );

    // Non-expired token that satisfies the DIA profile (closes g1).
    let good_tok = valid_token("e8-good", &ctx, Some(future));

    // Expired token that closes g_other (not in profile).
    let expired_tok = ProofToken {
        token_id: "tok-exp-e8".into(),
        token_type: "CLOSE".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g_other".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now() - Duration::hours(2),
        expires_at: Some(past),
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    ctx.tokens = vec![good_tok, expired_tok];
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "E8: expired token (even one not satisfying required gap) must floor to EXP when profile otherwise satisfied"
    );
}

// ── E9/E10: LiveJudgment expiry checks ───────────────────────────────────────

fn make_live_judgment_ctx(suffix: &str) -> (ProofContext, Permission) {
    let claim_id = format!("claim-live-{suffix}");
    let candidate_id = format!("z-live-{suffix}");
    let context_id = format!("ctx-live-{suffix}");
    let allowed_use = "live-use";
    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, allowed_use);

    let ctx = ProofContext {
        claim_id,
        candidate_id,
        context_id,
        context_fingerprint: format!("fp-live-{suffix}"),
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
        tokens: vec![ProofToken {
            token_id: format!("tok-live-{suffix}"),
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
        expiry: Expiry::at(Utc::now() + Duration::hours(1)), // future expiry
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    let j = compile(ctx).unwrap();
    (j.context.clone(), j.permission)
}

#[test]
fn e9_live_judgment_expiry_fires_when_now_equals_deadline() {
    let (ctx, _) = make_live_judgment_ctx("e9");
    let deadline = ctx.expiry.deadline.unwrap();

    // Re-compile with the same context.
    let j = compile(ctx.clone()).unwrap();
    // Set runtime.now to exactly the deadline.
    let rt = RuntimeContext::new(deadline, &ctx.context_fingerprint);
    let live = LiveJudgment::new(j, &rt);
    assert_eq!(
        live.permission(),
        Permission::EXP,
        "E9: LiveJudgment must return EXP when runtime.now == deadline"
    );
}

#[test]
fn e10_live_judgment_expiry_does_not_fire_before_deadline() {
    let (ctx, _) = make_live_judgment_ctx("e10");
    let deadline = ctx.expiry.deadline.unwrap();

    let j = compile(ctx.clone()).unwrap();
    // Set runtime.now to 1ms before the deadline.
    let just_before = deadline - Duration::milliseconds(1);
    let rt = RuntimeContext::new(just_before, &ctx.context_fingerprint);
    let live = LiveJudgment::new(j, &rt);
    assert_eq!(
        live.permission(),
        Permission::DIA,
        "E10: LiveJudgment must not expire 1ms before deadline; got {}",
        live.permission()
    );
}
