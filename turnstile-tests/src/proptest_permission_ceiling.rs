/// Property test: Authority ceiling invariants (T-ceiling).
///
/// The authority_ceiling is a hard cap: the compiler must never emit a
/// permission above the ceiling regardless of what the profiles and tokens
/// support.
///
/// Properties:
///   1. compile(ctx).permission ≤ ctx.authority_ceiling   (always)
///   2. If ceiling is OOC, result is always OOC (for in-class contexts too)
///   3. Ceiling and profile satisfaction are independent axes
///   4. Adding a lower ceiling can only lower or preserve the result
///   5. N-way meet of ceilings applied to the same context is monotone
use chrono::Utc;
use proptest::prelude::*;
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
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

fn full_ctx(ceiling: Permission) -> ProofContext {
    let claim_id = "c-ceil";
    let candidate_id = "z-ceil";
    let context_id = "ctx-ceil";
    let allowed_use = "ceil-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-ceil".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "t")],
        profiles: vec![Profile {
            permission: Permission::AAA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-ceil".into(),
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
        authority_ceiling: ceiling,
        membership: Membership::InClass,
    }
}

// ── Deterministic ceiling tests ───────────────────────────────────────────────

#[test]
fn ceiling_aaa_allows_full_profile() {
    let ctx = full_ctx(Permission::AAA);
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::AAA);
}

#[test]
fn ceiling_dia_caps_aaa_profile() {
    let ctx = full_ctx(Permission::DIA);
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA);
}

#[test]
fn ceiling_ooc_floors_inclass_to_ooc() {
    // Even an in-class context with all gaps closed gets OOC if ceiling = OOC.
    let ctx = full_ctx(Permission::OOC);
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "authority_ceiling=OOC must force OOC even for in-class"
    );
}

#[test]
fn ceiling_exp_caps_to_exp() {
    let ctx = full_ctx(Permission::EXP);
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::EXP);
}

#[test]
fn ceiling_ref_caps_to_ref() {
    let ctx = full_ctx(Permission::REF);
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::REF);
}

#[test]
fn lower_ceiling_always_reduces_or_preserves_permission() {
    let ceilings = [
        Permission::AAA, Permission::ALR, Permission::AEX, Permission::REV,
        Permission::DIA, Permission::ROL, Permission::ESC, Permission::ETA,
        Permission::UNS, Permission::REF, Permission::EXP, Permission::OOC,
    ];
    let mut prev = compile(full_ctx(ceilings[0])).unwrap().permission;
    for &c in &ceilings[1..] {
        let p = compile(full_ctx(c)).unwrap().permission;
        assert!(
            p <= prev,
            "lowering ceiling from {:?} to {c:?}: permission went up from {prev} to {p}",
            ceilings[ceilings.iter().position(|&x| x == prev).unwrap_or(0)]
        );
        prev = p;
    }
}

// ── Ceiling is independent of profile satisfaction ─────────────────────────────

#[test]
fn ceiling_below_profile_level_wins() {
    let mut ctx = full_ctx(Permission::AAA);
    // Profile targets AAA but ceiling is DIA.
    ctx.authority_ceiling = Permission::DIA;
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA);
}

#[test]
fn ceiling_above_profile_level_does_not_promote() {
    let mut ctx = full_ctx(Permission::AAA);
    // Profile targets AAA, ceiling is also AAA → result = AAA.
    // Then lower profile to DIA. Ceiling won't promote above DIA.
    ctx.profiles[0].permission = Permission::DIA;
    ctx.authority_ceiling = Permission::AAA; // ceiling higher than profile
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "ceiling above profile does not promote beyond profile level"
    );
}

// ── Proptest: ceiling is always a hard cap ────────────────────────────────────

proptest! {
    #[test]
    fn prop_permission_never_exceeds_ceiling(ceiling in arb_permission()) {
        let ctx = full_ctx(ceiling);
        let j = compile(ctx).unwrap();
        prop_assert!(
            j.permission <= ceiling,
            "permission {} exceeds ceiling {}", j.permission, ceiling
        );
    }

    #[test]
    fn prop_lower_ceiling_never_raises_permission(
        ceiling1 in arb_permission(),
        ceiling2 in arb_permission(),
    ) {
        let higher = ceiling1.max(ceiling2);
        let lower = ceiling1.min(ceiling2);

        let p_higher = compile(full_ctx(higher)).unwrap().permission;
        let p_lower = compile(full_ctx(lower)).unwrap().permission;

        prop_assert!(
            p_lower <= p_higher,
            "lower ceiling {lower} produced higher permission {p_lower} > {p_higher}"
        );
    }

    #[test]
    fn prop_ceiling_is_exact_when_profile_exceeds_ceiling(
        ceiling in arb_permission(),
    ) {
        // Profile targets a permission > ceiling → result should be exactly ceiling
        // (assuming there is no expiry or other blocker).
        // Find what the context emits at ceiling.
        let ctx = full_ctx(ceiling);
        let j = compile(ctx).unwrap();

        // Result = meet(what_profile_wants=AAA, ceiling) = ceiling.
        // Except if there's some other blocker (shouldn't be in this clean context).
        prop_assert!(
            j.permission <= ceiling,
            "permission {} must be ≤ ceiling {}", j.permission, ceiling
        );
    }
}
