/// EC-003H — Compiler idempotence: compiling the same context twice produces
///           the same permission. This is property #2 from turnstile_spec.md §8.
///
/// Covers:
///   Spec §8 property 2 — Idempotence
///   Determinism invariant: same ProofContext + same registry + same runtime → identical output
///
/// Idempotence here means:
///   compile(Γ) and compile(Γ) where Γ has fresh `now` — the permission must be equal.
///   (Timestamps advance, but since tokens are not yet expired, results are equal.)
///
/// We also test that the Judgment's context snapshot does not affect a fresh compilation.
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

fn make_ctx(target: Permission) -> ProofContext {
    let claim_id = "claim-idem";
    let candidate_id = "z-idem";
    let context_id = "ctx-idem";
    let allowed_use = "idem-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);
    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-idem".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "t")],
        profiles: vec![Profile {
            permission: target,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-idem".into(),
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
        authority_ceiling: target,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

const ALL: [Permission; 12] = [
    Permission::OOC,
    Permission::EXP,
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

// ── Idempotence: compile(Γ) = compile(Γ) for all permission levels ─────────

#[test]
fn compile_idempotent_all_permissions() {
    for p in ALL {
        if p == Permission::OOC {
            continue;
        }
        let ctx = make_ctx(p);
        let j1 = compile(ctx.clone()).unwrap();
        let j2 = compile(ctx).unwrap();
        assert_eq!(
            j1.permission, j2.permission,
            "idempotence failed at {p}: {}/{}",
            j1.permission, j2.permission
        );
    }
}

// ── Idempotence with disallowed_uses ─────────────────────────────────────────

#[test]
fn compile_idempotent_with_structural_blockers() {
    let mut ctx = make_ctx(Permission::AAA);
    ctx.disallowed_uses = vec!["write".into()];
    let j1 = compile(ctx.clone()).unwrap();
    let j2 = compile(ctx).unwrap();
    assert_eq!(
        j1.permission, j2.permission,
        "idempotence broken by structural blockers"
    );
}

// ── Idempotence: OOC membership ──────────────────────────────────────────────

#[test]
fn compile_idempotent_ooc_membership() {
    let mut ctx = make_ctx(Permission::AAA);
    ctx.membership = Membership::OutOfClassExact;
    let j1 = compile(ctx.clone()).unwrap();
    let j2 = compile(ctx).unwrap();
    assert_eq!(j1.permission, j2.permission);
    assert_eq!(j1.permission, Permission::OOC);
}

// ── Idempotence: expired context at compile time ──────────────────────────────

#[test]
fn compile_idempotent_expired_context() {
    let mut ctx = make_ctx(Permission::DIA);
    ctx.expiry = Expiry::at(Utc::now() - Duration::seconds(1));
    let j1 = compile(ctx.clone()).unwrap();
    let j2 = compile(ctx).unwrap();
    assert_eq!(
        j1.permission, j2.permission,
        "idempotence broken by expired context"
    );
    assert_eq!(j1.permission, Permission::EXP);
}

// ── Determinism: 100 recompilations ─────────────────────────────────────────

#[test]
fn compile_deterministic_100_iterations() {
    let ctx = make_ctx(Permission::DIA);
    let baseline = compile(ctx.clone()).unwrap().permission;
    for _ in 0..99 {
        let p = compile(ctx.clone()).unwrap().permission;
        assert_eq!(
            p, baseline,
            "compile produced different result on repeated call"
        );
    }
}

// ── Idempotence: no side effects from prior compilations ─────────────────────

#[test]
fn compile_result_unaffected_by_other_compilations() {
    let ctx_a = make_ctx(Permission::DIA);
    let ctx_b = make_ctx(Permission::REV);

    let p_a1 = compile(ctx_a.clone()).unwrap().permission;
    let _p_b = compile(ctx_b).unwrap().permission;
    let p_a2 = compile(ctx_a).unwrap().permission;

    assert_eq!(
        p_a1, p_a2,
        "compilation of another context affected this one"
    );
}

// ── Proptest: idempotence ────────────────────────────────────────────────────

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

proptest! {
    #[test]
    fn prop_compile_idempotent(target in arb_permission()) {
        if target == Permission::OOC { return Ok(()); }
        let ctx = make_ctx(target);
        let p1 = compile(ctx.clone()).unwrap().permission;
        let p2 = compile(ctx).unwrap().permission;
        prop_assert_eq!(p1, p2, "compile not idempotent at {:?}", target);
    }

    #[test]
    fn prop_compile_deterministic_ceiling(
        target in arb_permission(),
        ceiling in arb_permission(),
    ) {
        if target == Permission::OOC { return Ok(()); }
        let mut ctx = make_ctx(target);
        ctx.authority_ceiling = ceiling;
        let p1 = compile(ctx.clone()).unwrap().permission;
        let p2 = compile(ctx).unwrap().permission;
        prop_assert_eq!(p1, p2, "compile not deterministic with ceiling");
    }
}
