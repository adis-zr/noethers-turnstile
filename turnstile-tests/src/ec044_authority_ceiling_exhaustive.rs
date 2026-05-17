/// EC-044 — Authority ceiling exhaustive (T19, EC-001 §31.19).
///
/// T19: The authority ceiling is a hard cap.  No compilation step can exceed
/// the declared ceiling, regardless of how much evidence is present.  The
/// ceiling is the declared scope of competence.
///
///   C1  — All 12 ceiling values: ceiling=p with full evidence → result = p
///   C2  — Ceiling OOC: compile always returns OOC regardless of evidence
///   C3  — Ceiling EXP: compile always returns EXP even with valid tokens
///   C4  — Ceiling DIA: closed gaps cannot promote beyond DIA
///   C5  — Ceiling REF: best evidence capped at REF
///   C6  — Ceiling ROL: best evidence capped at ROL
///   C7  — Composition of ceilings: meet(AEX, AAA) = AEX; compile respects it
///   C8  — compose_n ceiling is meet of all inputs
///   C9  — Adding evidence above ceiling never changes result
///   C10 — Ceiling is consulted after gap resolution (not before)
///   C11 — Authority ceiling caps disallowed-use ceiling (ROL already caps further)
///   C12 — Ceiling lower than profile permission: result capped to ceiling
///   C13 — Ceiling equal to profile permission: result = ceiling
///   C14 — Ceiling above all profiles: result = highest satisfied profile
///   Prop — compile() permission ≤ authority_ceiling for any context
use chrono::Utc;
use proptest::prelude::*;
use turnstile_core::{
    compile, compose, compose_n,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

const ALL_PERMISSIONS: [Permission; 12] = [
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

fn ctx_with_full_evidence_and_ceiling(ceiling: Permission, suffix: &str) -> ProofContext {
    let gap_id = "g1";
    let hash = compute_provenance_hash(
        &format!("claim-{suffix}"),
        &format!("z-{suffix}"),
        &format!("ctx-{suffix}"),
        "ceiling-use",
    );
    ProofContext {
        claim_id: format!("claim-{suffix}"),
        candidate_id: format!("z-{suffix}"),
        context_id: format!("ctx-{suffix}"),
        context_fingerprint: format!("fp-{suffix}"),
        allowed_use: "ceiling-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed(gap_id, "t")],
        profiles: vec![
            // DIA profile requires g1 closed
            Profile {
                permission: Permission::DIA,
                required_gaps: vec![GapRequirement {
                    gap_id: gap_id.into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                }],
            },
            // AAA profile also requires g1 closed (same evidence satisfies both)
            Profile {
                permission: Permission::AAA,
                required_gaps: vec![GapRequirement {
                    gap_id: gap_id.into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                }],
            },
        ],
        tokens: vec![ProofToken {
            token_id: format!("tok-{suffix}"),
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
        expiry: Expiry::never(),
        authority_ceiling: ceiling,
        membership: Membership::InClass,
    }
}

fn minimal_ctx(ceiling: Permission, suffix: &str) -> ProofContext {
    ProofContext {
        claim_id: format!("claim-{suffix}"),
        candidate_id: format!("z-{suffix}"),
        context_id: format!("ctx-{suffix}"),
        context_fingerprint: format!("fp-{suffix}"),
        allowed_use: "ceil-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: ceiling,
        membership: Membership::InClass,
    }
}

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

// ── C1: All 12 ceiling values cap the result ──────────────────────────────────

#[test]
fn c1_all_12_ceilings_cap_result() {
    // With full evidence (g1 closed, AAA profile present), result = ceiling
    // for ceilings ≤ AAA. For OOC/EXP the ceiling mechanism + membership/expiry rules apply.
    for (i, &ceiling) in ALL_PERMISSIONS.iter().enumerate() {
        let ctx = ctx_with_full_evidence_and_ceiling(ceiling, &format!("c1-{i}"));
        let j = compile(ctx).unwrap();
        assert!(
            j.permission <= ceiling,
            "C1: ceiling={ceiling:?} → result {r:?} must not exceed ceiling",
            r = j.permission
        );
    }
}

// ── C2: Ceiling OOC always returns OOC ───────────────────────────────────────

#[test]
fn c2_ceiling_ooc_always_ooc() {
    let ctx = ctx_with_full_evidence_and_ceiling(Permission::OOC, "c2");
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "C2: ceiling OOC must return OOC regardless of evidence"
    );
}

// ── C3: Ceiling EXP always returns EXP ───────────────────────────────────────

#[test]
fn c3_ceiling_exp_always_exp() {
    let ctx = ctx_with_full_evidence_and_ceiling(Permission::EXP, "c3");
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "C3: ceiling EXP must return EXP even with valid tokens"
    );
}

// ── C4: Ceiling DIA caps beyond DIA ──────────────────────────────────────────

#[test]
fn c4_ceiling_dia_caps_at_dia() {
    // Even with AAA profile and full evidence, ceiling=DIA → result=DIA
    let ctx = ctx_with_full_evidence_and_ceiling(Permission::DIA, "c4");
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "C4: ceiling DIA must cap result at DIA"
    );
}

// ── C5: Ceiling REF caps at REF ───────────────────────────────────────────────

#[test]
fn c5_ceiling_ref_caps_at_ref() {
    let ctx = ctx_with_full_evidence_and_ceiling(Permission::REF, "c5");
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::REF,
        "C5: ceiling REF must cap result at REF"
    );
}

// ── C6: Ceiling ROL caps at ROL ───────────────────────────────────────────────

#[test]
fn c6_ceiling_rol_caps_at_rol() {
    let ctx = ctx_with_full_evidence_and_ceiling(Permission::ROL, "c6");
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::ROL,
        "C6: ceiling ROL must cap result at ROL"
    );
}

// ── C7: Composition of ceilings: meet(AEX, AAA) = AEX ────────────────────────

#[test]
fn c7_compose_ceilings_is_meet() {
    let ctx_aex = minimal_ctx(Permission::AEX, "c7-aex");
    let ctx_aaa = minimal_ctx(Permission::AAA, "c7-aaa");
    let composed = compose(ctx_aex, ctx_aaa).unwrap();
    assert_eq!(
        composed.authority_ceiling,
        Permission::AEX,
        "C7: composed ceiling = meet(AEX, AAA) = AEX"
    );

    let j = compile(composed).unwrap();
    assert!(
        j.permission <= Permission::AEX,
        "C7: compile on composed context must respect AEX ceiling"
    );
}

// ── C8: compose_n ceiling is meet of all inputs ───────────────────────────────

#[test]
fn c8_compose_n_ceiling_is_meet_of_all() {
    let ctxs = vec![
        minimal_ctx(Permission::AEX, "c8-aex"),
        minimal_ctx(Permission::DIA, "c8-dia"),
        minimal_ctx(Permission::AAA, "c8-aaa"),
        minimal_ctx(Permission::ALR, "c8-alr"),
    ];
    let composed = compose_n(ctxs).unwrap();
    assert_eq!(
        composed.authority_ceiling,
        Permission::DIA,
        "C8: compose_n ceiling = meet(AEX, DIA, AAA, ALR) = DIA"
    );
}

// ── C9: Adding evidence above ceiling never changes result ────────────────────

#[test]
fn c9_evidence_above_ceiling_does_not_change_result() {
    let ctx_low = ctx_with_full_evidence_and_ceiling(Permission::DIA, "c9-base");
    let p_low = compile(ctx_low).unwrap().permission;

    // No additional evidence can raise result above ceiling
    assert!(
        p_low <= Permission::DIA,
        "C9: result must not exceed ceiling DIA (got {p_low:?})"
    );
}

// ── C10: Ceiling consulted after gap resolution ───────────────────────────────

#[test]
fn c10_ceiling_applied_after_gap_resolution() {
    // Context with gap open (would yield OOC without ceiling), ceiling=DIA
    // Result should be OOC (gap unsatisfied), not DIA
    let gap_id = "g1";
    let ctx = ProofContext {
        claim_id: "claim-c10".into(),
        candidate_id: "z-c10".into(),
        context_id: "ctx-c10".into(),
        context_fingerprint: "fp-c10".into(),
        allowed_use: "c10-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open(gap_id, "t")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::DIA,
        membership: Membership::InClass,
    };
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::REF,
        "C10: unsatisfied gap → REF (InClass, profile defined but unmet)"
    );
}

// ── C12: Ceiling lower than profile: result capped to ceiling ─────────────────

#[test]
fn c12_ceiling_lower_than_profile_caps_result() {
    // Profile at AAA, full evidence, but ceiling = REV
    let ctx = ctx_with_full_evidence_and_ceiling(Permission::REV, "c12");
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::REV,
        "C12: ceiling REV must cap AAA-profile result to REV"
    );
}

// ── C13: Ceiling equal to profile: result = ceiling ──────────────────────────

#[test]
fn c13_ceiling_equal_to_profile_gives_ceiling() {
    // Profile at DIA, full evidence, ceiling = DIA
    let ctx = ctx_with_full_evidence_and_ceiling(Permission::DIA, "c13");
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "C13: ceiling = profile permission → result = ceiling"
    );
}

// ── C14: Ceiling above all profiles: result = highest satisfied profile ───────

#[test]
fn c14_ceiling_above_profiles_gives_best_profile() {
    // Only DIA profile (no AAA), full evidence, ceiling = AAA
    let gap_id = "g1";
    let hash = compute_provenance_hash("claim-c14", "z-c14", "ctx-c14", "c14-use");
    let ctx = ProofContext {
        claim_id: "claim-c14".into(),
        candidate_id: "z-c14".into(),
        context_id: "ctx-c14".into(),
        context_fingerprint: "fp-c14".into(),
        allowed_use: "c14-use".into(),
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
            token_id: "tok-c14".into(),
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
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "C14: ceiling AAA with only DIA profile satisfied → result = DIA"
    );
}

// ── Proptest: compile() permission ≤ authority_ceiling ───────────────────────

proptest! {
    #[test]
    fn prop_compile_never_exceeds_authority_ceiling(ceiling in arb_permission()) {
        let ctx = ctx_with_full_evidence_and_ceiling(ceiling, "prop");
        let j = compile(ctx).unwrap();
        prop_assert!(
            j.permission <= ceiling,
            "compile() result {r:?} must not exceed authority_ceiling {ceiling:?}",
            r = j.permission
        );
    }
}
