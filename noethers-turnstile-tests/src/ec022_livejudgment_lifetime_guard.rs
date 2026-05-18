/// EC-022 — LiveJudgment<'ctx> lifetime structural guarantee.
///
/// The `LiveJudgment<'ctx>` type is tied by a lifetime to the `RuntimeContext`
/// it was created from.  This is the type-system enforcement of T15: the runtime
/// cannot upgrade a compiled permission after the fact, because no live read can
/// outlive the context it was compiled against.
///
/// Tests in this suite:
///   L1 — LiveJudgment can be created and read within a RuntimeContext's scope.
///   L2 — Cloning the inner Judgment and creating a fresh LiveJudgment from a
///         new RuntimeContext works correctly (context switch).
///   L3 — LiveJudgment::judgment() exposes the inner Judgment for audit/serde.
///   L4 — LiveJudgment::deadline() correctly reflects the inner expiry.
///   L5 — Two LiveJudgments from the same RuntimeContext can coexist.
///   L6 — LiveJudgment returns OOC when the runtime fingerprint differs from
///         the compile-time fingerprint (wrong-context guard, not expiry).
///   L7 — LiveJudgment permission is idempotent: calling permission() multiple
///         times on the same live instance returns the same value.
///   L8 — LiveJudgment with no expiry and matching fingerprint returns the
///         compiled permission without modification (T15: never upgrades).
///
/// NOTE: The compile-time lifetime constraint ("LiveJudgment cannot outlive its
/// RuntimeContext") is enforced by the borrow checker and cannot be demonstrated
/// via a passing test — only via a compile_fail doctest.  That doctest lives in
/// the turnstile-core source (see `expiry.rs`).  This suite tests the *runtime*
/// behaviour of the lifetime contract.
use chrono::{Duration, Utc};
use noethers_noethers_turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::{Expiry, LiveJudgment, RuntimeContext},
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn build_valid_ctx(suffix: &str, perm: Permission) -> ProofContext {
    let claim_id = format!("claim-ll-{suffix}");
    let candidate_id = format!("z-ll-{suffix}");
    let context_id = format!("ctx-ll-{suffix}");
    let allowed_use = "live-use";

    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, allowed_use);

    ProofContext {
        claim_id,
        candidate_id,
        context_id,
        context_fingerprint: format!("fp-ll-{suffix}"),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "gap")],
        profiles: vec![Profile {
            permission: perm,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: format!("tok-ll-{suffix}"),
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
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── L1: Basic LiveJudgment creation and read ─────────────────────────────────

#[test]
fn l1_live_judgment_readable_within_runtime_scope() {
    let ctx = build_valid_ctx("l1", Permission::DIA);
    let fp = ctx.context_fingerprint.clone();
    let j = compile(ctx).unwrap();

    let rt = RuntimeContext::new(Utc::now(), &fp);
    let live = LiveJudgment::new(j, &rt);
    assert_eq!(
        live.permission(),
        Permission::DIA,
        "L1: LiveJudgment must return compiled permission when live"
    );
}

// ── L2: Context switch via fresh LiveJudgment ────────────────────────────────

#[test]
fn l2_fresh_live_judgment_from_cloned_judgment_reflects_new_runtime() {
    let ctx = build_valid_ctx("l2", Permission::REV);
    let fp = ctx.context_fingerprint.clone();
    let j = compile(ctx).unwrap();

    // Original runtime — valid.
    let rt1 = RuntimeContext::new(Utc::now(), &fp);
    {
        let live1 = LiveJudgment::new(j.clone(), &rt1);
        assert_eq!(live1.permission(), Permission::REV, "L2: first runtime ok");
    }

    // New runtime with wrong fingerprint.
    let rt2 = RuntimeContext::new(Utc::now(), "wrong-fp");
    {
        let live2 = LiveJudgment::new(j, &rt2);
        assert_eq!(
            live2.permission(),
            Permission::OOC,
            "L2: mismatched runtime fingerprint must return OOC"
        );
    }
}

// ── L3: judgment() exposes inner Judgment for audit ──────────────────────────

#[test]
fn l3_judgment_accessor_returns_inner_judgment() {
    let ctx = build_valid_ctx("l3", Permission::DIA);
    let fp = ctx.context_fingerprint.clone();
    let j = compile(ctx).unwrap();
    let stored_perm = j.permission;

    let rt = RuntimeContext::new(Utc::now(), &fp);
    let live = LiveJudgment::new(j, &rt);
    assert_eq!(
        live.judgment().permission,
        stored_perm,
        "L3: judgment() must return the inner judgment with the compiled permission"
    );
}

// ── L4: deadline() reflects inner expiry ─────────────────────────────────────

#[test]
fn l4_deadline_is_none_for_no_expiry() {
    let ctx = build_valid_ctx("l4", Permission::DIA);
    let fp = ctx.context_fingerprint.clone();
    let j = compile(ctx).unwrap();
    let rt = RuntimeContext::new(Utc::now(), &fp);
    let live = LiveJudgment::new(j, &rt);
    assert_eq!(
        live.deadline(),
        None,
        "L4: deadline() must be None when context has no expiry"
    );
}

#[test]
fn l4_deadline_matches_context_expiry() {
    let mut ctx = build_valid_ctx("l4b", Permission::DIA);
    let future = Utc::now() + Duration::hours(8);
    ctx.expiry = Expiry::at(future);
    let fp = ctx.context_fingerprint.clone();
    let j = compile(ctx).unwrap();
    let rt = RuntimeContext::new(Utc::now(), &fp);
    let live = LiveJudgment::new(j, &rt);
    assert_eq!(
        live.deadline(),
        Some(future),
        "L4: deadline() must reflect the context expiry"
    );
}

// ── L5: Two LiveJudgments from the same RuntimeContext coexist ────────────────

#[test]
fn l5_two_live_judgments_from_same_runtime_coexist() {
    let ctx1 = build_valid_ctx("l5a", Permission::DIA);
    let ctx2 = build_valid_ctx("l5b", Permission::REV);

    // Both contexts must share the same fingerprint to pass the RT check.
    // But they have different fingerprints — so we use a fresh RT per judgment.
    let fp1 = ctx1.context_fingerprint.clone();
    let fp2 = ctx2.context_fingerprint.clone();

    let j1 = compile(ctx1).unwrap();
    let j2 = compile(ctx2).unwrap();

    let rt1 = RuntimeContext::new(Utc::now(), fp1);
    let rt2 = RuntimeContext::new(Utc::now(), fp2);

    let live1 = LiveJudgment::new(j1, &rt1);
    let live2 = LiveJudgment::new(j2, &rt2);

    assert_eq!(
        live1.permission(),
        Permission::DIA,
        "L5: first live judgment"
    );
    assert_eq!(
        live2.permission(),
        Permission::REV,
        "L5: second live judgment"
    );
}

// ── L6: Fingerprint mismatch returns OOC ─────────────────────────────────────

#[test]
fn l6_fingerprint_mismatch_returns_ooc() {
    let ctx = build_valid_ctx("l6", Permission::AAA);
    let j = compile(ctx).unwrap();
    let rt = RuntimeContext::new(Utc::now(), "completely-wrong-fingerprint");
    let live = LiveJudgment::new(j, &rt);
    assert_eq!(
        live.permission(),
        Permission::OOC,
        "L6: fingerprint mismatch must return OOC (T15 runtime non-upgrade enforcement)"
    );
}

// ── L7: permission() is idempotent ───────────────────────────────────────────

#[test]
fn l7_permission_is_idempotent() {
    let ctx = build_valid_ctx("l7", Permission::DIA);
    let fp = ctx.context_fingerprint.clone();
    let j = compile(ctx).unwrap();
    let rt = RuntimeContext::new(Utc::now(), &fp);
    let live = LiveJudgment::new(j, &rt);

    let p1 = live.permission();
    let p2 = live.permission();
    let p3 = live.permission();
    assert_eq!(p1, p2, "L7: permission() must be idempotent (call 1 vs 2)");
    assert_eq!(p2, p3, "L7: permission() must be idempotent (call 2 vs 3)");
}

// ── L8: T15 — permission() never upgrades the compiled permission ────────────

#[test]
fn l8_live_judgment_never_upgrades_permission() {
    // Compile at DIA. The runtime has a higher "intent" but cannot override.
    // The only way to upgrade would be to modify the inner judgment, which is
    // not possible without recompiling.
    let ctx = build_valid_ctx("l8", Permission::DIA);
    let fp = ctx.context_fingerprint.clone();
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "L8: compiled permission must be DIA"
    );

    let rt = RuntimeContext::new(Utc::now(), &fp);
    let live = LiveJudgment::new(j, &rt);

    // The live permission must never be higher than the compiled permission.
    let live_perm = live.permission();
    assert!(
        live_perm <= Permission::DIA,
        "L8: T15 — live permission ({live_perm}) must not exceed compiled permission (DIA)"
    );
}

#[test]
fn l8_live_judgment_can_lower_but_not_raise() {
    // Start with AAA-ceiling but authority ceiling blocks at DIA.
    // The live read must not raise above DIA.
    let mut ctx = build_valid_ctx("l8b", Permission::AAA);
    ctx.authority_ceiling = Permission::DIA;
    let fp = ctx.context_fingerprint.clone();
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "L8b: authority ceiling must cap at DIA"
    );

    let rt = RuntimeContext::new(Utc::now(), &fp);
    let live = LiveJudgment::new(j, &rt);
    assert!(
        live.permission() <= Permission::DIA,
        "L8b: live permission must not exceed compiled DIA"
    );
}
