/// EC-003O — T17: Negative-control liveness enforcement.
///
/// Covers theorem:
///   T17 — Negative-control liveness: in strict mode, any NC token whose
///          live state is not `Live` floors `LiveJudgment::permission()` to
///          `Permission::REF`.
///
/// Tests:
///   - NC token with `Live` state → permission unchanged
///   - NC token absent from map → `Missing` → `REF` (fail-closed)
///   - NC token with `Stale` state → `REF`
///   - NC token with `Failed` state → `REF`
///   - NC token with `Missing` state (explicit) → `REF`
///   - Non-strict mode → NC check skipped, permission unchanged
///   - No NC tokens in context → strict mode has no effect
///   - Multiple NC tokens: all Live → ok; one non-Live → `REF`
///   - NC check fires at runtime (`LiveJudgment`), not at compile time
///   - Floor is `REF`, not `OOC`, not `EXP`
///   - Derivation records NC token IDs in `negative_control_registration`
///   - Proptest: any non-Live state in strict mode always floors to `REF`
use std::collections::HashMap;

use chrono::Utc;
use proptest::prelude::*;
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::{Expiry, LiveJudgment, RuntimeContext},
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
    NegativeControlStatus,
};

// ── Helpers ──────────────────────────────────────────────────────────────────

fn base_ctx() -> ProofContext {
    ProofContext {
        claim_id: "claim-nc".into(),
        candidate_id: "z-nc".into(),
        context_id: "ctx-nc".into(),
        context_fingerprint: "fp-nc".into(),
        allowed_use: "nc-test".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "calibration")],
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
        membership: Membership::InClass,
    }
}

fn closing_token(ctx: &ProofContext, is_negative_control: bool) -> ProofToken {
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ProofToken {
        token_id: format!("tok-{}", if is_negative_control { "nc" } else { "plain" }),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control,
    }
}

fn runtime_with_nc_state(
    nc_id: &str,
    state: NegativeControlStatus,
    strict: bool,
) -> RuntimeContext {
    let mut map = HashMap::new();
    map.insert(nc_id.to_string(), state);
    RuntimeContext::with_nc_states(Utc::now(), "fp-nc", map, strict)
}

// ── Core NC liveness tests ────────────────────────────────────────────────────

#[test]
fn nc_token_live_state_passes_through() {
    let mut ctx = base_ctx();
    let tok = closing_token(&ctx, true);
    let tok_id = tok.token_id.clone();
    ctx.tokens = vec![tok];

    let judgment = compile(ctx).unwrap();
    assert_eq!(
        judgment.permission,
        Permission::DIA,
        "compile-time permission must be DIA before runtime check"
    );

    let rt = runtime_with_nc_state(&tok_id, NegativeControlStatus::Live, true);
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(
        live.permission(),
        Permission::DIA,
        "NC Live → permission unchanged"
    );
}

#[test]
fn nc_token_absent_from_map_floors_to_ref() {
    let mut ctx = base_ctx();
    ctx.tokens = vec![closing_token(&ctx, true)];

    let judgment = compile(ctx).unwrap();
    // No NC states in map → token_id is absent → Missing → REF
    let rt = RuntimeContext::new(Utc::now(), "fp-nc");
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(
        live.permission(),
        Permission::REF,
        "absent NC token defaults to Missing → must floor to REF"
    );
}

#[test]
fn nc_token_stale_state_floors_to_ref() {
    let mut ctx = base_ctx();
    let tok = closing_token(&ctx, true);
    let tok_id = tok.token_id.clone();
    ctx.tokens = vec![tok];

    let judgment = compile(ctx).unwrap();
    let rt = runtime_with_nc_state(&tok_id, NegativeControlStatus::Stale, true);
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(live.permission(), Permission::REF, "Stale NC → REF");
}

#[test]
fn nc_token_failed_state_floors_to_ref() {
    let mut ctx = base_ctx();
    let tok = closing_token(&ctx, true);
    let tok_id = tok.token_id.clone();
    ctx.tokens = vec![tok];

    let judgment = compile(ctx).unwrap();
    let rt = runtime_with_nc_state(&tok_id, NegativeControlStatus::Failed, true);
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(live.permission(), Permission::REF, "Failed NC → REF");
}

#[test]
fn nc_token_missing_state_explicit_floors_to_ref() {
    let mut ctx = base_ctx();
    let tok = closing_token(&ctx, true);
    let tok_id = tok.token_id.clone();
    ctx.tokens = vec![tok];

    let judgment = compile(ctx).unwrap();
    let rt = runtime_with_nc_state(&tok_id, NegativeControlStatus::Missing, true);
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(
        live.permission(),
        Permission::REF,
        "explicit Missing NC → REF"
    );
}

// ── Non-strict mode skips NC check ───────────────────────────────────────────

#[test]
fn non_strict_mode_skips_nc_check() {
    let mut ctx = base_ctx();
    let tok = closing_token(&ctx, true);
    let tok_id = tok.token_id.clone();
    ctx.tokens = vec![tok];

    let judgment = compile(ctx).unwrap();

    // Stale in non-strict mode → check skipped → permission passes through.
    let rt = runtime_with_nc_state(&tok_id, NegativeControlStatus::Stale, false);
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(
        live.permission(),
        Permission::DIA,
        "non-strict mode: NC check skipped, permission must be DIA"
    );
}

#[test]
fn non_strict_absent_nc_does_not_floor() {
    let mut ctx = base_ctx();
    ctx.tokens = vec![closing_token(&ctx, true)];

    let judgment = compile(ctx).unwrap();

    // No NC states at all, but strict_mode = false.
    let rt = RuntimeContext::with_nc_states(Utc::now(), "fp-nc", HashMap::new(), false);
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(
        live.permission(),
        Permission::DIA,
        "non-strict absent NC → no floor"
    );
}

// ── No NC tokens in context ───────────────────────────────────────────────────

#[test]
fn no_nc_tokens_strict_mode_has_no_effect() {
    let mut ctx = base_ctx();
    // Non-NC closing token.
    ctx.tokens = vec![closing_token(&ctx, false)];

    let judgment = compile(ctx).unwrap();

    // Strict mode but no NC tokens → check trivially passes.
    let rt = RuntimeContext::new(Utc::now(), "fp-nc");
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(
        live.permission(),
        Permission::DIA,
        "no NC tokens: strict mode must not alter permission"
    );
}

// ── Multiple NC tokens ────────────────────────────────────────────────────────

#[test]
fn multiple_nc_tokens_all_live_passes() {
    let mut ctx = base_ctx();
    // Need a second gap to have two distinct NC tokens close two gaps.
    ctx.gaps.push(GapRecord::closed("g2", "second"));
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
    let tok1 = ProofToken {
        token_id: "nc-1".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash.clone(),
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: true,
    };
    let tok2 = ProofToken {
        token_id: "nc-2".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g2".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: true,
    };
    ctx.tokens = vec![tok1, tok2];

    let judgment = compile(ctx).unwrap();

    let mut nc_map = HashMap::new();
    nc_map.insert("nc-1".to_string(), NegativeControlStatus::Live);
    nc_map.insert("nc-2".to_string(), NegativeControlStatus::Live);
    let rt = RuntimeContext::with_nc_states(Utc::now(), "fp-nc", nc_map, true);
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(live.permission(), Permission::DIA, "all NC Live → DIA");
}

#[test]
fn multiple_nc_tokens_one_non_live_floors_to_ref() {
    let mut ctx = base_ctx();
    ctx.gaps.push(GapRecord::closed("g2", "second"));
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
    let tok1 = ProofToken {
        token_id: "nc-a".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash.clone(),
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: true,
    };
    let tok2 = ProofToken {
        token_id: "nc-b".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g2".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: true,
    };
    ctx.tokens = vec![tok1, tok2];

    let judgment = compile(ctx).unwrap();

    let mut nc_map = HashMap::new();
    nc_map.insert("nc-a".to_string(), NegativeControlStatus::Live);
    nc_map.insert("nc-b".to_string(), NegativeControlStatus::Stale); // one fails
    let rt = RuntimeContext::with_nc_states(Utc::now(), "fp-nc", nc_map, true);
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(
        live.permission(),
        Permission::REF,
        "one non-Live NC among many must floor to REF"
    );
}

// ── NC check at runtime, not compile time ─────────────────────────────────────

#[test]
fn compile_time_permission_unaffected_by_nc_state() {
    // compile() must return the full profile permission regardless of NC state.
    // NC liveness is only enforced by LiveJudgment::permission().
    let mut ctx = base_ctx();
    ctx.tokens = vec![closing_token(&ctx, true)];

    let judgment = compile(ctx).unwrap();
    // Compile-time result must be DIA even though no RuntimeContext exists yet.
    assert_eq!(
        judgment.permission,
        Permission::DIA,
        "compile() must not consult NC liveness — that is a runtime concern"
    );
}

// ── REF floor, not OOC or EXP ────────────────────────────────────────────────

#[test]
fn nc_floor_is_ref_not_ooc_not_exp() {
    let mut ctx = base_ctx();
    ctx.tokens = vec![closing_token(&ctx, true)];

    let judgment = compile(ctx).unwrap();
    // Absent NC → floor to REF.
    let rt = RuntimeContext::new(Utc::now(), "fp-nc");
    let live = LiveJudgment::new(judgment, &rt);
    let p = live.permission();
    assert_eq!(p, Permission::REF, "NC floor must be REF");
    assert_ne!(p, Permission::OOC, "NC floor must not be OOC");
    assert_ne!(p, Permission::EXP, "NC floor must not be EXP");
}

// ── REF > EXP — NC block is recoverable in liveness hierarchy ────────────────

#[test]
fn ref_is_above_exp_in_permission_order() {
    // REF sits above EXP in the lattice (T-floor from NC is more recoverable
    // than expired evidence).
    assert!(
        Permission::REF > Permission::EXP,
        "REF must be strictly above EXP in the permission order"
    );
}

// ── Derivation records NC token IDs ──────────────────────────────────────────

#[test]
fn derivation_records_nc_token_ids() {
    let mut ctx = base_ctx();
    let tok = closing_token(&ctx, true);
    let tok_id = tok.token_id.clone();
    ctx.tokens = vec![tok];

    let judgment = compile(ctx).unwrap();

    let nc_step = judgment
        .derivation
        .steps
        .iter()
        .find(|s| s.phase == "negative_control_registration");

    assert!(
        nc_step.is_some(),
        "derivation must contain a negative_control_registration step"
    );
    let step = nc_step.unwrap();
    assert!(
        step.token_ids.contains(&tok_id),
        "derivation step must list NC token ID"
    );
    // Phase must not change the permission.
    assert_eq!(
        step.permission_after,
        Permission::DIA,
        "NC registration step must not alter permission in derivation"
    );
}

#[test]
fn derivation_omits_nc_step_when_no_nc_tokens() {
    let mut ctx = base_ctx();
    ctx.tokens = vec![closing_token(&ctx, false)]; // non-NC
    let judgment = compile(ctx).unwrap();

    let nc_step = judgment
        .derivation
        .steps
        .iter()
        .find(|s| s.phase == "negative_control_registration");

    assert!(
        nc_step.is_none(),
        "no NC tokens → derivation must not contain negative_control_registration step"
    );
}

// ── Proptest: any non-Live state in strict mode always floors to REF ──────────

fn arb_non_live_status() -> impl Strategy<Value = NegativeControlStatus> {
    prop_oneof![
        Just(NegativeControlStatus::Stale),
        Just(NegativeControlStatus::Failed),
        Just(NegativeControlStatus::Missing),
    ]
}

proptest! {
    #[test]
    fn prop_any_non_live_state_strict_mode_floors_to_ref(
        state in arb_non_live_status(),
    ) {
        let mut ctx = base_ctx();
        let tok = closing_token(&ctx, true);
        let tok_id = tok.token_id.clone();
        ctx.tokens = vec![tok];

        let judgment = compile(ctx).unwrap();
        let rt = runtime_with_nc_state(&tok_id, state, true);
        let live = LiveJudgment::new(judgment, &rt);
        prop_assert_eq!(
            live.permission(),
            Permission::REF,
            "non-Live state {:?} in strict mode must floor to REF",
            state
        );
    }

    #[test]
    fn prop_live_state_strict_mode_passes_through(
        // Use a permission high enough to be above REF so we can distinguish.
        perm in prop_oneof![
            Just(Permission::DIA),
            Just(Permission::REV),
            Just(Permission::AEX),
            Just(Permission::ALR),
            Just(Permission::AAA),
        ],
    ) {
        let mut ctx = base_ctx();
        ctx.authority_ceiling = perm;
        // Set a profile that matches perm.
        ctx.profiles[0].permission = perm;

        let tok = closing_token(&ctx, true);
        let tok_id = tok.token_id.clone();
        ctx.tokens = vec![tok];

        let judgment = compile(ctx).unwrap();
        let rt = runtime_with_nc_state(&tok_id, NegativeControlStatus::Live, true);
        let live = LiveJudgment::new(judgment, &rt);
        prop_assert_eq!(
            live.permission(),
            perm,
            "Live NC in strict mode must pass permission {:?} through",
            perm
        );
    }

    #[test]
    fn prop_non_strict_mode_never_floors_on_nc(
        state in prop_oneof![
            Just(NegativeControlStatus::Live),
            Just(NegativeControlStatus::Stale),
            Just(NegativeControlStatus::Failed),
            Just(NegativeControlStatus::Missing),
        ],
    ) {
        let mut ctx = base_ctx();
        let tok = closing_token(&ctx, true);
        let tok_id = tok.token_id.clone();
        ctx.tokens = vec![tok];

        let judgment = compile(ctx).unwrap();
        let rt = runtime_with_nc_state(&tok_id, state, false);
        let live = LiveJudgment::new(judgment, &rt);
        prop_assert_eq!(
            live.permission(),
            Permission::DIA,
            "non-strict mode: any NC state {:?} must not floor permission",
            state
        );
    }
}
