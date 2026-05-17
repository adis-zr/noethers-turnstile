/// EC-003Q — Context fingerprint sensitivity (T-fingerprint / AC-002 T1-6).
///
/// The `context_fingerprint` field in `ProofContext` is the runtime identity
/// of the live execution environment.  `LiveJudgment::permission()` requires
/// that the runtime context's fingerprint matches the fingerprint the judgment
/// was compiled against.  Any mismatch returns EXP (fail-closed).
///
/// Covers theorems:
///   T15 — Runtime non-upgrade: fingerprint mismatch cannot upgrade
///   T7  — Expiry soundness: fingerprint mismatch treated as expiry
///
/// Tests:
///   - Matching fingerprint → compiled permission
///   - Any mutation of fingerprint → EXP
///   - Case sensitivity: "FP" ≠ "fp"
///   - Whitespace: " fp" ≠ "fp"
///   - Empty string fingerprint: mismatch unless compiled with ""
///   - Proptest: any string change → EXP
use chrono::Utc;
use proptest::prelude::*;
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::{Expiry, LiveJudgment, RuntimeContext},
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn ctx_with_fingerprint(fp: &str) -> ProofContext {
    let claim_id = "claim-fp";
    let candidate_id = "z-fp";
    let context_id = "ctx-fp";
    let allowed_use = "fp-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: fp.into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "t")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-fp".into(),
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
            is_negative_control: false,
        }],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── Matching fingerprint passes through ──────────────────────────────────────

#[test]
fn matching_fingerprint_returns_compiled_permission() {
    let fp = "sha256-abc123def456";
    let ctx = ctx_with_fingerprint(fp);
    let judgment = compile(ctx).unwrap();
    assert_eq!(judgment.permission, Permission::DIA);

    let rt = RuntimeContext::new(Utc::now(), fp);
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(live.permission(), Permission::DIA);
}

// ── Any mismatch → EXP ────────────────────────────────────────────────────────

#[test]
fn single_char_change_returns_exp() {
    let fp = "sha256-abc123";
    let ctx = ctx_with_fingerprint(fp);
    let judgment = compile(ctx).unwrap();

    // One character changed.
    let rt = RuntimeContext::new(Utc::now(), "sha256-abc124");
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(live.permission(), Permission::EXP);
}

#[test]
fn truncated_fingerprint_returns_exp() {
    let fp = "sha256-abc123def456";
    let ctx = ctx_with_fingerprint(fp);
    let judgment = compile(ctx).unwrap();

    let rt = RuntimeContext::new(Utc::now(), "sha256-abc123def45"); // truncated
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(live.permission(), Permission::EXP);
}

#[test]
fn extra_char_fingerprint_returns_exp() {
    let fp = "sha256-abc123";
    let ctx = ctx_with_fingerprint(fp);
    let judgment = compile(ctx).unwrap();

    let rt = RuntimeContext::new(Utc::now(), "sha256-abc123X"); // extra char
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(live.permission(), Permission::EXP);
}

#[test]
fn case_sensitive_fingerprint_mismatch_returns_exp() {
    let fp = "ABC-fingerprint";
    let ctx = ctx_with_fingerprint(fp);
    let judgment = compile(ctx).unwrap();

    let rt = RuntimeContext::new(Utc::now(), "abc-fingerprint"); // different case
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(live.permission(), Permission::EXP);
}

#[test]
fn leading_whitespace_fingerprint_mismatch_returns_exp() {
    let fp = "fp-abc";
    let ctx = ctx_with_fingerprint(fp);
    let judgment = compile(ctx).unwrap();

    let rt = RuntimeContext::new(Utc::now(), " fp-abc"); // leading space
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(live.permission(), Permission::EXP);
}

#[test]
fn empty_runtime_fingerprint_when_compiled_nonempty_returns_exp() {
    let fp = "real-fingerprint";
    let ctx = ctx_with_fingerprint(fp);
    let judgment = compile(ctx).unwrap();

    let rt = RuntimeContext::new(Utc::now(), ""); // empty
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(live.permission(), Permission::EXP);
}

#[test]
fn empty_compiled_fingerprint_matches_empty_runtime() {
    let fp = "";
    let ctx = ctx_with_fingerprint(fp);
    let judgment = compile(ctx).unwrap();

    let rt = RuntimeContext::new(Utc::now(), "");
    let live = LiveJudgment::new(judgment, &rt);
    // Empty matches empty → permission passes through.
    assert_eq!(live.permission(), Permission::DIA);
}

#[test]
fn totally_different_fingerprint_returns_exp() {
    let fp = "env-sha256-production-context";
    let ctx = ctx_with_fingerprint(fp);
    let judgment = compile(ctx).unwrap();

    let rt = RuntimeContext::new(Utc::now(), "env-sha256-staging-context");
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(live.permission(), Permission::EXP);
}

// ── Fingerprint mismatch is independent of expiry ────────────────────────────

#[test]
fn fingerprint_mismatch_with_future_expiry_still_returns_exp() {
    let fp = "fp-real";
    let mut ctx = ctx_with_fingerprint(fp);
    ctx.expiry = Expiry::at(Utc::now() + chrono::Duration::seconds(3600)); // future
    let judgment = compile(ctx).unwrap();

    let rt = RuntimeContext::new(Utc::now(), "fp-wrong");
    let live = LiveJudgment::new(judgment, &rt);
    assert_eq!(live.permission(), Permission::EXP);
}

// ── Composed context: fingerprint is concatenation ────────────────────────────

#[test]
fn composed_context_fingerprint_must_match_combined() {
    use turnstile_core::compose;
    use turnstile_core::context::ProofContext;

    let fp1 = "fp-A";
    let fp2 = "fp-B";
    let ctx1 = ctx_with_fingerprint(fp1);
    let ctx2 = ctx_with_fingerprint(fp2);

    // compose() combines fingerprints as "{fp1}+{fp2}"
    let composed = compose(ctx1, ctx2).unwrap();
    let expected_fp = format!("{fp1}+{fp2}");
    assert_eq!(composed.context_fingerprint, expected_fp);

    let judgment = compile(composed).unwrap();

    // Matching the combined fingerprint passes.
    let rt_ok = RuntimeContext::new(Utc::now(), &expected_fp);
    let live_ok = LiveJudgment::new(judgment.clone(), &rt_ok);
    assert_ne!(
        live_ok.permission(),
        Permission::EXP,
        "matching combined fingerprint must not return EXP"
    );

    // Original single fingerprint fails.
    let rt_wrong = RuntimeContext::new(Utc::now(), fp1);
    let live_wrong = LiveJudgment::new(judgment, &rt_wrong);
    assert_eq!(
        live_wrong.permission(),
        Permission::EXP,
        "single sub-fingerprint for composed context must return EXP"
    );
}

// ── Proptest: any fingerprint change → EXP ────────────────────────────────────

proptest! {
    #[test]
    fn prop_changed_fingerprint_returns_exp(
        base_fp in "[a-z0-9]{4,32}",
        changed_fp in "[a-z0-9]{4,32}",
    ) {
        // Only test when fingerprints actually differ.
        prop_assume!(base_fp != changed_fp);

        let ctx = ctx_with_fingerprint(&base_fp);
        let judgment = compile(ctx).unwrap();

        let rt = RuntimeContext::new(Utc::now(), changed_fp.as_str());
        let live = LiveJudgment::new(judgment, &rt);
        prop_assert_eq!(
            live.permission(),
            Permission::EXP,
            "fingerprint change must return EXP"
        );
    }

    #[test]
    fn prop_matching_fingerprint_preserves_permission(
        fp in "[a-z0-9]{4,32}",
    ) {
        let ctx = ctx_with_fingerprint(&fp);
        let judgment = compile(ctx).unwrap();
        let compiled_p = judgment.permission;

        let rt = RuntimeContext::new(Utc::now(), fp.as_str());
        let live = LiveJudgment::new(judgment, &rt);
        prop_assert_eq!(
            live.permission(),
            compiled_p,
            "matching fingerprint must preserve compiled permission"
        );
    }
}
