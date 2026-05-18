/// EC-003C — Runtime never upgrades permission (PC-12, EC-003 §29–30).
///
/// Ported from:
///   test_ec003c_runtime_nonupgrade.py
///   test_ec003c_decomposition_nonupgrade.py
///   test_ec003c_runtime_idempotence.py
///
/// Properties proved:
///   T15 — Runtime non-upgrade: live permission ≤ compiled permission
///   T7  — Expiry soundness: expired token/context → EXP, not upgradeable
use chrono::{Duration, Utc};
use proptest::prelude::*;
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::{Expiry, LiveJudgment, RuntimeContext},
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn arb_permission() -> impl Strategy<Value = Permission> {
    prop_oneof![
        Just(Permission::OOC),
        Just(Permission::EXP),
        Just(Permission::REF),
        Just(Permission::UNS),
        Just(Permission::ETA),
        Just(Permission::ESC),
        Just(Permission::ROL),
        Just(Permission::DIA),
        Just(Permission::REV),
        Just(Permission::AEX),
        Just(Permission::ALR),
        Just(Permission::AAA),
    ]
}

fn build_dia_ctx(expiry: Expiry) -> ProofContext {
    let claim_id = "claim-rt";
    let candidate_id = "z-rt";
    let context_id = "ctx-rt";
    let allowed_use = "rt-test";
    let gap_id = "g1";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-rt".into(),
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
            token_id: "tok-rt".into(),
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
        expiry,
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── Runtime non-upgrade: live.permission() ≤ compiled.permission ─────────────

const OPERATIONAL: [Permission; 10] = [
    Permission::REF,
    Permission::UNS,
    Permission::ETA,
    Permission::ESC,
    Permission::ROL,
    Permission::DIA,
    Permission::REV,
    Permission::AEX,
    Permission::ALR,
    Permission::AAA,
];

#[test]
fn runtime_matching_fp_never_upgrades_all_operational() {
    for p in OPERATIONAL {
        let mut ctx = build_dia_ctx(Expiry::never());
        ctx.authority_ceiling = p; // cap at p
        let judgment = compile(ctx).unwrap();
        let compiled_p = judgment.permission;

        let rt = RuntimeContext::new(Utc::now(), "fp-rt");
        let live = LiveJudgment::new(judgment, &rt);
        assert!(
            live.permission() <= compiled_p,
            "runtime upgraded: live={} > compiled={compiled_p}",
            live.permission()
        );
    }
}

#[test]
fn runtime_mismatched_fp_returns_ooc() {
    let ctx = build_dia_ctx(Expiry::never());
    let judgment = compile(ctx).unwrap();

    let rt = RuntimeContext::new(Utc::now(), "fp-wrong"); // mismatched
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(live.permission(), Permission::OOC);
}

#[test]
fn runtime_expired_context_returns_exp() {
    let past = Utc::now() - Duration::seconds(1);
    let ctx = build_dia_ctx(Expiry::at(past));
    let judgment = compile(ctx).unwrap();
    // Even though compile succeeded, expiry is already in the past
    let rt = RuntimeContext::new(Utc::now(), "fp-rt");
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(live.permission(), Permission::EXP);
}

#[test]
fn runtime_dia_cannot_become_rev() {
    let ctx = build_dia_ctx(Expiry::never());
    let judgment = compile(ctx).unwrap();
    assert_eq!(judgment.permission, Permission::DIA);

    let rt = RuntimeContext::new(Utc::now(), "fp-rt");
    let live = LiveJudgment::new(judgment, &rt);
    assert!(live.permission() <= Permission::DIA);
    assert_ne!(live.permission(), Permission::REV);
}

// ── Expiry fires at the boundary (T7) ────────────────────────────────────────

#[test]
fn expiry_fires_exactly_at_boundary() {
    let now = Utc::now();
    let deadline = now + Duration::seconds(60);
    let ctx = build_dia_ctx(Expiry::at(deadline));
    let judgment = compile(ctx).unwrap();

    // Before: not expired
    let rt_before = RuntimeContext::new(deadline - Duration::nanoseconds(1), "fp-rt");
    let live_before = LiveJudgment::new(judgment.clone(), &rt_before);
    assert_ne!(live_before.permission(), Permission::EXP);

    // At boundary: expired
    let rt_at = RuntimeContext::new(deadline, "fp-rt");
    let live_at = LiveJudgment::new(judgment.clone(), &rt_at);
    assert_eq!(live_at.permission(), Permission::EXP);

    // After: expired
    let rt_after = RuntimeContext::new(deadline + Duration::seconds(1), "fp-rt");
    let live_after = LiveJudgment::new(judgment, &rt_after);
    assert_eq!(live_after.permission(), Permission::EXP);
}

#[test]
fn expired_token_floors_to_exp_during_compile() {
    let claim_id = "c-tok-exp";
    let candidate_id = "z-tok-exp";
    let context_id = "ctx-tok-exp";
    let allowed_use = "use-tok-exp";
    let gap_id = "g1";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let past = Utc::now() - Duration::seconds(1);
    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp".into(),
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
            token_id: "tok-exp".into(),
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
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let judgment = compile(ctx).unwrap();
    assert_eq!(
        judgment.permission,
        Permission::EXP,
        "expired token should floor to EXP at compile time"
    );
}

// ── Idempotence: compiling twice gives same result ────────────────────────────

#[test]
fn compile_idempotent() {
    let ctx = build_dia_ctx(Expiry::never());
    let j1 = compile(ctx.clone()).unwrap();
    let j2 = compile(ctx).unwrap();
    assert_eq!(j1.permission, j2.permission);
}

// ── Proptest: runtime non-upgrade ────────────────────────────────────────────

proptest! {
    #[test]
    fn prop_runtime_never_upgrades_matching_fp(
        ceiling in arb_permission(),
        offset_secs in 1i64..=86400i64,
    ) {
        let now = Utc::now();
        let deadline = now + Duration::seconds(offset_secs);
        let ctx = {
            let mut c = build_dia_ctx(Expiry::at(deadline));
            c.authority_ceiling = ceiling;
            c
        };
        let judgment = compile(ctx).unwrap();
        let compiled_p = judgment.permission;

        // Check well before deadline
        let rt = RuntimeContext::new(now, "fp-rt");
        let live = LiveJudgment::new(judgment, &rt);
        prop_assert!(
            live.permission() <= compiled_p,
            "runtime upgraded: live={} > compiled={compiled_p}", live.permission()
        );
    }

    #[test]
    fn prop_expiry_fires_at_or_after_deadline(
        offset_secs in 1i64..=86400i64,
        past_secs in 0i64..=3600i64,
    ) {
        let now = Utc::now();
        let deadline = now + Duration::seconds(offset_secs);
        let ctx = build_dia_ctx(Expiry::at(deadline));
        let judgment = compile(ctx).unwrap();

        let check_time = deadline + Duration::seconds(past_secs);
        let rt = RuntimeContext::new(check_time, "fp-rt");
        let live = LiveJudgment::new(judgment, &rt);
        prop_assert_eq!(live.permission(), Permission::EXP);
    }

    #[test]
    fn prop_expiry_does_not_fire_before_deadline(
        offset_secs in 2i64..=86400i64,
    ) {
        let now = Utc::now();
        let deadline = now + Duration::seconds(offset_secs);
        let ctx = build_dia_ctx(Expiry::at(deadline));
        let judgment = compile(ctx).unwrap();

        let before = deadline - Duration::nanoseconds(1);
        let rt = RuntimeContext::new(before, "fp-rt");
        let live = LiveJudgment::new(judgment, &rt);
        prop_assert_ne!(live.permission(), Permission::EXP);
    }
}
