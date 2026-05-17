/// Property test: Expiry fires at boundary.
///
/// For any judgment with `expires_at = T`,
/// `LiveJudgment::permission()` at `now >= T` returns `EXP`.
use chrono::{DateTime, Duration, Utc};
use proptest::prelude::*;
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::{Expiry, LiveJudgment, RuntimeContext},
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn build_dia_ctx_with_expiry(expiry: Expiry) -> ProofContext {
    let claim_id = "claim-exp".to_string();
    let candidate_id = "z-exp".to_string();
    let context_id = "ctx-exp".to_string();
    let allowed_use = "exp-test".to_string();

    let gap_id = "g1";
    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, &allowed_use);

    ProofContext {
        claim_id: claim_id.clone(),
        candidate_id,
        context_id,
        context_fingerprint: "fp-exp".into(),
        allowed_use,
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed(gap_id, "test_gap")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-exp".into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![gap_id.into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: None, // token itself does not expire
            issuer: "test".into(),
            details: serde_json::Value::Null,
        }],
        expiry,
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

proptest! {
    /// LiveJudgment returns EXP at or after the deadline.
    #[test]
    fn expiry_fires_at_or_after_deadline(
        // Offset in seconds from "now" for the deadline: 1..=86400
        offset_secs in 1i64..=86400i64,
        // How far past the deadline we check: 0..=3600
        past_secs in 0i64..=3600i64,
    ) {
        let now = Utc::now();
        let deadline = now + Duration::seconds(offset_secs);
        let expiry = Expiry::at(deadline);

        // Compile at "now" (before deadline) → should succeed with DIA.
        let ctx = build_dia_ctx_with_expiry(expiry);
        let judgment = compile(ctx).unwrap();

        // Check at exactly deadline + past_secs.
        let check_time = deadline + Duration::seconds(past_secs);
        let rt = RuntimeContext::new(check_time, "fp-exp");
        let live = LiveJudgment::new(judgment, &rt);

        prop_assert_eq!(
            live.permission(),
            Permission::EXP,
            "expiry should fire at deadline+{}s: deadline={:?}, check_time={:?}",
            past_secs, deadline, check_time
        );
    }

    /// LiveJudgment returns the compiled permission strictly before the deadline.
    #[test]
    fn expiry_does_not_fire_before_deadline(
        // Deadline is at least 2 seconds in the future.
        offset_secs in 2i64..=86400i64,
    ) {
        let now = Utc::now();
        let deadline = now + Duration::seconds(offset_secs);
        let expiry = Expiry::at(deadline);

        let ctx = build_dia_ctx_with_expiry(expiry);
        let judgment = compile(ctx).unwrap();

        // Check one nanosecond before the deadline.
        let before = deadline - Duration::nanoseconds(1);
        let rt = RuntimeContext::new(before, "fp-exp");
        let live = LiveJudgment::new(judgment, &rt);

        // Permission should be DIA (not EXP), since we're before the deadline.
        prop_assert_ne!(
            live.permission(),
            Permission::EXP,
            "expiry should not have fired before deadline: deadline={:?}, check_time={:?}",
            deadline, before
        );
    }
}

/// Direct non-proptest check: expiry fires exactly at the boundary.
#[test]
fn expiry_fires_exactly_at_boundary() {
    let now = Utc::now();
    let deadline = now + Duration::seconds(60);
    let expiry = Expiry::at(deadline);

    let ctx = build_dia_ctx_with_expiry(expiry);
    let judgment = compile(ctx).unwrap();

    // Before deadline: not expired.
    let rt_before = RuntimeContext::new(deadline - Duration::nanoseconds(1), "fp-exp");
    let live_before = LiveJudgment::new(judgment.clone(), &rt_before);
    assert_ne!(live_before.permission(), Permission::EXP);

    // Exactly at deadline: expired.
    let rt_at = RuntimeContext::new(deadline, "fp-exp");
    let live_at = LiveJudgment::new(judgment.clone(), &rt_at);
    assert_eq!(live_at.permission(), Permission::EXP);

    // After deadline: expired.
    let rt_after = RuntimeContext::new(deadline + Duration::seconds(1), "fp-exp");
    let live_after = LiveJudgment::new(judgment, &rt_after);
    assert_eq!(live_after.permission(), Permission::EXP);
}
