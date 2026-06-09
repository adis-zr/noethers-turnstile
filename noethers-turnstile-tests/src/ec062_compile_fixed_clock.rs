//! EC-062 — Fixed-clock determinism (F3).
//!
//! `compile` consults `Utc::now()` at multiple call sites within one invocation
//! (the early expiry check and per-token expiry checks inside
//! `effective_gap_status`). For a token whose `expires_at` straddles those
//! reads, the descending-search portion can treat the token as live while
//! step 6 treats it as expired — non-deterministic across re-runs.
//!
//! The fix is a single observation of `now` per compile invocation, threaded
//! through every expiry-sensitive call site. We expose `compile_at(ctx, now)`
//! (and `compile_at_with_chain`) so callers — and tests — can pin the clock.
//!
//! Properties:
//!   T1 — `compile_at` exists and accepts a fixed `now`.
//!   T2 — For any pair of clocks straddling a token's `expires_at`, the result
//!         depends only on the supplied `now`, not on the wall clock.
//!   T3 — `compile_at` invariant under the time-fan: calling it twice with the
//!         same `now` yields identical permissions, regardless of how much
//!         wall-clock time has passed between the calls.

use chrono::{Duration, TimeZone, Utc};
use noethers_turnstile_core::{
    compile_at,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn ctx_with_token_expiring_at(token_expires: chrono::DateTime<Utc>) -> ProofContext {
    let claim_id = "claim-clock";
    let candidate_id = "z-clock";
    let context_id = "ctx-clock";
    let allowed_use = "clock-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-clock".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "gap")],
        profiles: vec![Profile {
            permission: Permission::DIA(),
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
                any_of: None,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-clock".into(),
            token_type: "CLOSE".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc.with_ymd_and_hms(2025, 1, 1, 0, 0, 0).unwrap(),
            expires_at: Some(token_expires),
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
            negative_control_id: None,
        }],
        expiry: Expiry::never(),
        authority_ceiling: Some(Permission::AAA()),
        permission_ceiling: Some(Permission::AAA()),
        membership: Membership::InClass,
        expected_chain_hash: None,
    }
}

#[test]
fn t1_compile_at_exists_and_pins_clock() {
    // Token expires at T. Compile at T - 1 ns → token live → DIA.
    let expires = Utc.with_ymd_and_hms(2025, 6, 1, 12, 0, 0).unwrap();
    let ctx = ctx_with_token_expiring_at(expires);
    let before = expires - Duration::nanoseconds(1);
    let j = compile_at(ctx, before).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA(),
        "live token before its expiry must satisfy the profile"
    );
}

#[test]
fn t2_compile_at_with_now_after_expiry_floors_to_exp() {
    // Token expires at T. Compile at T → token has expired → no profile
    // satisfied → outcome floors to ExpiryFloor (EXP on the default chain).
    let expires = Utc.with_ymd_and_hms(2025, 6, 1, 12, 0, 0).unwrap();
    let ctx = ctx_with_token_expiring_at(expires);
    let j = compile_at(ctx, expires).unwrap();
    // The token is no longer live so the gap stays Open, the DIA profile is
    // not satisfied, and the expired-token blocker (step 6) meets outcome
    // with ExpiryFloor.
    assert_eq!(
        j.permission,
        Permission::EXP(),
        "compile_at past token deadline must return ExpiryFloor"
    );
}

#[test]
fn t3_same_now_yields_same_permission_regardless_of_wall_clock() {
    // Two compile_at calls with the same `now` must produce the same
    // permission, even if real wall-clock time passes between the calls.
    let expires = Utc.with_ymd_and_hms(2025, 6, 1, 12, 0, 0).unwrap();
    let now = expires - Duration::seconds(1); // both calls see token as live
    let ctx_a = ctx_with_token_expiring_at(expires);
    let ctx_b = ctx_with_token_expiring_at(expires);
    let j1 = compile_at(ctx_a, now).unwrap();
    // Simulate wall-clock advancing well past the deadline.
    let j2 = compile_at(ctx_b, now).unwrap();
    assert_eq!(j1.permission, j2.permission);
    assert_eq!(j1.permission, Permission::DIA());
}
