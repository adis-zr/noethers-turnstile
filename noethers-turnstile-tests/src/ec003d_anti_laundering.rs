/// EC-003D — Anti-laundering: provenance identity, token reuse prevention,
///           heterogeneous laundering (PC-20, EC-003 §38).
///
/// Ported from:
///   test_ec003d_provenance_identity.py
///   test_ec003d_token_reuse.py
///   test_ec003d_heterogeneous_property.py
///   test_ec003d_heterogeneous_anti_laundering.py
///
/// Properties proved:
///   T1  — Fake-token non-promotion: wrong provenance → PROVENANCE_MISMATCH → REF
///   T3  — Provenance soundness: token bound to (claim, candidate, ctx, use)
///   T4  — Instance identity: token for z₁ never licenses z₂ (emits REF via prov mismatch)
///   T16 — Heterogeneous anti-laundering: stale never upgrades; group-fold independent
use chrono::Utc;
use proptest::prelude::*;
use noethers_noethers_turnstile_core::{
    compile, compose,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn arb_id() -> impl Strategy<Value = String> {
    "[a-z]{4,8}"
}

fn ctx_with_token(
    claim_id: &str,
    candidate_id: &str,
    context_id: &str,
    allowed_use: &str,
    token_provenance_hash: &str,
) -> ProofContext {
    let gap_id = "g1";
    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp".into(),
        allowed_use: allowed_use.into(),
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
        tokens: vec![ProofToken {
            token_id: "tok".into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![gap_id.into()],
            bounds_gaps: vec![],
            provenance_hash: token_provenance_hash.into(),
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

// ── T1/T3: Wrong provenance never closes a gap ────────────────────────────────

#[test]
fn wrong_candidate_token_rejected() {
    let wrong_hash = compute_provenance_hash("claim", "z-WRONG", "ctx", "use");

    let ctx = ctx_with_token("claim", "z-correct", "ctx", "use", &wrong_hash);
    let j = compile(ctx).unwrap();
    // Wrong provenance → PROVENANCE_MISMATCH structural failure → REF meet applied.
    assert_eq!(
        j.permission,
        Permission::REF,
        "wrong provenance token must not close gap; PROVENANCE_MISMATCH floors to REF"
    );
}

#[test]
fn correct_provenance_closes_gap() {
    let hash = compute_provenance_hash("claim", "z-1", "ctx", "use");
    let mut ctx = ctx_with_token("claim", "z-1", "ctx", "use", &hash);
    ctx.gaps[0] = GapRecord::closed("g1", "t"); // gap is attested closed
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA);
}

#[test]
fn wrong_claim_token_rejected() {
    let wrong_hash = compute_provenance_hash("claim-WRONG", "z-1", "ctx", "use");
    let ctx = ctx_with_token("claim-RIGHT", "z-1", "ctx", "use", &wrong_hash);
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::REF);
}

#[test]
fn wrong_context_id_token_rejected() {
    let wrong_hash = compute_provenance_hash("claim", "z-1", "ctx-WRONG", "use");
    let ctx = ctx_with_token("claim", "z-1", "ctx-RIGHT", "use", &wrong_hash);
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::REF);
}

#[test]
fn wrong_allowed_use_token_rejected() {
    let wrong_hash = compute_provenance_hash("claim", "z-1", "ctx", "use-WRONG");
    let ctx = ctx_with_token("claim", "z-1", "ctx", "use-RIGHT", &wrong_hash);
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::REF);
}

// ── T4: Token for z₁ cannot license z₂ ──────────────────────────────────────

#[test]
fn token_for_z1_does_not_license_z2() {
    let hash_z1 = compute_provenance_hash("claim", "z-1", "ctx", "use");
    // Present the z1 token against a z2 context
    let ctx = ctx_with_token("claim", "z-2", "ctx", "use", &hash_z1);
    let j = compile(ctx).unwrap();
    // Wrong provenance → PROVENANCE_MISMATCH → REF (not OOC; candidate is in-class).
    assert_eq!(
        j.permission,
        Permission::REF,
        "token for z-1 must not license z-2; PROVENANCE_MISMATCH floors to REF"
    );
}

// ── T1: Invalid token status never promotes ───────────────────────────────────

#[test]
fn invalid_token_does_not_close_gap() {
    let hash = compute_provenance_hash("claim", "z-1", "ctx", "use");
    let gap_id = "g1";
    let ctx = ProofContext {
        claim_id: "claim".into(),
        candidate_id: "z-1".into(),
        context_id: "ctx".into(),
        context_fingerprint: "fp".into(),
        allowed_use: "use".into(),
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
        tokens: vec![ProofToken {
            token_id: "tok-invalid".into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Invalid, // invalid status
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
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    let j = compile(ctx).unwrap();
    // Correct provenance but Invalid status → token skipped, gap stays Open,
    // profile not satisfied → REF (in-class candidate with profile defined).
    assert_eq!(
        j.permission,
        Permission::REF,
        "invalid token must not close gap; in-class with unmet profile → REF"
    );
}

#[test]
fn revoked_token_does_not_close_gap() {
    let hash = compute_provenance_hash("claim", "z-1", "ctx", "use");
    let gap_id = "g1";
    let ctx = ProofContext {
        claim_id: "claim".into(),
        candidate_id: "z-1".into(),
        context_id: "ctx".into(),
        context_fingerprint: "fp".into(),
        allowed_use: "use".into(),
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
        tokens: vec![ProofToken {
            token_id: "tok-rev".into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Revoked,
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
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    let j = compile(ctx).unwrap();
    // Correct provenance but Revoked status → token skipped, gap stays Open,
    // profile not satisfied → REF (in-class candidate with profile defined).
    assert_eq!(
        j.permission,
        Permission::REF,
        "revoked token must not close gap; in-class with unmet profile → REF"
    );
}

// ── T16: Heterogeneous anti-laundering — stale never upgrades, group-fold OK ──

fn dia_ctx_with_fp(fp_fingerprint: &str) -> ProofContext {
    let gap_id = "g1";
    let hash = compute_provenance_hash("claim-h", "z-h", "ctx-h", "use-h");
    ProofContext {
        claim_id: "claim-h".into(),
        candidate_id: "z-h".into(),
        context_id: "ctx-h".into(),
        context_fingerprint: fp_fingerprint.into(),
        allowed_use: "use-h".into(),
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
            token_id: "tok-h".into(),
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
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

#[test]
fn stale_context_fingerprint_downgrades_via_live_judgment() {
    let ctx = dia_ctx_with_fp("fp-old");
    let judgment = compile(ctx).unwrap();
    // Live context has a different fingerprint
    let rt = noethers_turnstile_core::expiry::RuntimeContext::new(Utc::now(), "fp-new");
    let live = noethers_turnstile_core::expiry::LiveJudgment::new(judgment, &rt);
    assert_eq!(
        live.permission(),
        Permission::OOC,
        "stale fp should downgrade to OOC (wrong context entirely, not expiry)"
    );
}

#[test]
fn two_contexts_order_independent_same_fp() {
    let ctx1 = dia_ctx_with_fp("fp-live");
    let ctx2 = {
        let mut c = dia_ctx_with_fp("fp-live");
        c.authority_ceiling = Permission::DIA;
        c
    };
    // Compose forward and backward — authority ceiling is meet → commutative
    let fwd = compose(ctx1.clone(), ctx2.clone()).unwrap();
    let rev = compose(ctx2, ctx1).unwrap();
    assert_eq!(fwd.authority_ceiling, rev.authority_ceiling);
}

#[test]
fn adding_stale_context_cannot_upgrade() {
    // fresh context compiles to DIA
    let fresh = dia_ctx_with_fp("fp-live");
    let p_fresh = compile(fresh.clone()).unwrap().permission;

    // add a stale context via composition
    let stale = {
        let mut c = dia_ctx_with_fp("fp-old");
        c.authority_ceiling = Permission::AAA;
        c
    };

    // After composition the ceiling is still the meet
    if let Ok(composed) = compose(fresh, stale) {
        let p_composed = compile(composed).unwrap().permission;
        assert!(
            p_composed <= p_fresh,
            "adding stale context must not upgrade permission"
        );
    }
}

// ── Proptest ──────────────────────────────────────────────────────────────────

proptest! {
    #[test]
    fn prop_wrong_provenance_always_ref(
        claim_id in arb_id(),
        candidate_id in arb_id(),
        context_id in arb_id(),
        allowed_use in arb_id(),
        wrong_candidate in "[A-Z]{4,8}",
    ) {
        prop_assume!(candidate_id != wrong_candidate.to_lowercase());
        let wrong_hash = compute_provenance_hash(
            &claim_id,
            &wrong_candidate, // wrong candidate
            &context_id,
            &allowed_use,
        );
        let ctx = ctx_with_token(&claim_id, &candidate_id, &context_id, &allowed_use, &wrong_hash);
        let j = compile(ctx).unwrap();
        // Wrong provenance → PROVENANCE_MISMATCH structural failure → REF meet applied.
        // Permission must be ≤ REF (cannot be higher than REF when a provenance mismatch exists).
        prop_assert!(j.permission <= Permission::REF,
            "wrong provenance must not emit above REF; got {:?}", j.permission);
    }

    #[test]
    fn prop_correct_provenance_with_closed_gap_satisfies_profile(
        claim_id in arb_id(),
        candidate_id in arb_id(),
        context_id in arb_id(),
        allowed_use in arb_id(),
    ) {
        let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, &allowed_use);
        let gap_id = "g1";
        let ctx = ProofContext {
            claim_id: claim_id.clone(),
            candidate_id: candidate_id.clone(),
            context_id: context_id.clone(),
            context_fingerprint: "fp".into(),
            allowed_use: allowed_use.clone(),
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
                token_id: "tok".into(),
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
            permission_ceiling: Permission::AAA,
            membership: Membership::InClass,
        };
        let j = compile(ctx).unwrap();
        prop_assert_eq!(j.permission, Permission::DIA);
    }
}
