/// EC-003W — Meet non-promotion (T8) and Diagnostic/Action separation (T11).
///
/// T8: Permission meet non-promotion
///   For any p, q in the permission lattice:
///     meet(p, q) ≤ p  and  meet(p, q) ≤ q
///   The meet of two permissions cannot promote above either input.
///
/// T11: Diagnostic/action separation
///   A context whose profile only supports DIA-level evidence cannot
///   be composed into a higher action permission by any means.
///   Specifically: DIA evidence cannot unlock REV, AEX, ALR, or AAA.
///
/// This matters because: if a diagnostic-only assessment could compose
/// with a stale or minimal-evidence context to unlock automatic execution,
/// the permission algebra would be unsound.
use chrono::Utc;
use proptest::prelude::*;
use turnstile_core::{
    compile, compose,
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

// ── T8: Meet non-promotion ────────────────────────────────────────────────────

/// Full 144-pair exhaustive verification of the meet table.
#[test]
fn t8_meet_never_exceeds_either_operand_exhaustive() {
    let all: Vec<Permission> = Permission::descending().collect();
    for &p in &all {
        for &q in &all {
            let m = p.meet(q);
            assert!(
                m <= p,
                "T8 violated: meet({p}, {q}) = {m} > {p}"
            );
            assert!(
                m <= q,
                "T8 violated: meet({p}, {q}) = {m} > {q}"
            );
        }
    }
}

#[test]
fn t8_meet_is_commutative_exhaustive() {
    let all: Vec<Permission> = Permission::descending().collect();
    for &p in &all {
        for &q in &all {
            assert_eq!(
                p.meet(q),
                q.meet(p),
                "T8: meet({p}, {q}) ≠ meet({q}, {p})"
            );
        }
    }
}

#[test]
fn t8_meet_is_associative_exhaustive() {
    let all: Vec<Permission> = Permission::descending().collect();
    for &p in &all {
        for &q in &all {
            for &r in &all {
                assert_eq!(
                    p.meet(q).meet(r),
                    p.meet(q.meet(r)),
                    "T8: meet associativity failed for ({p}, {q}, {r})"
                );
            }
        }
    }
}

#[test]
fn t8_meet_idempotent_exhaustive() {
    for p in Permission::descending() {
        assert_eq!(p.meet(p), p, "T8: meet({p}, {p}) ≠ {p}");
    }
}

#[test]
fn t8_meet_aaa_is_identity() {
    for p in Permission::descending() {
        assert_eq!(p.meet(Permission::AAA), p, "T8: meet({p}, AAA) should be {p}");
        assert_eq!(Permission::AAA.meet(p), p, "T8: meet(AAA, {p}) should be {p}");
    }
}

#[test]
fn t8_meet_ooc_is_absorbing() {
    for p in Permission::descending() {
        assert_eq!(p.meet(Permission::OOC), Permission::OOC, "T8: meet({p}, OOC) should be OOC");
        assert_eq!(Permission::OOC.meet(p), Permission::OOC, "T8: meet(OOC, {p}) should be OOC");
    }
}

/// meet_n of all permissions = OOC (bottom absorbs).
#[test]
fn t8_meet_n_all_permissions_is_ooc() {
    let result = Permission::meet_n(Permission::descending());
    assert_eq!(result, Some(Permission::OOC));
}

/// meet_n of an empty iterator returns None.
#[test]
fn t8_meet_n_empty_is_none() {
    let result = Permission::meet_n(std::iter::empty());
    assert!(result.is_none());
}

// ── T11: Diagnostic/action separation ────────────────────────────────────────

/// A context whose highest profile is DIA cannot produce REV+ permissions.
#[test]
fn t11_dia_context_cannot_compose_into_action_permission() {
    let make_dia_ctx = |suffix: &str| {
        let claim_id = format!("claim-t11-{suffix}");
        let candidate_id = format!("z-t11-{suffix}");
        let context_id = format!("ctx-t11-{suffix}");
        let allowed_use = "t11-use";
        let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, allowed_use);

        ProofContext {
            claim_id,
            candidate_id,
            context_id,
            context_fingerprint: format!("fp-t11-{suffix}"),
            allowed_use: allowed_use.into(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps: vec![GapRecord::closed("g1", "diagnostic_gap")],
            profiles: vec![Profile {
                permission: Permission::DIA, // DIA is the top level in this adapter
                required_gaps: vec![GapRequirement {
                    gap_id: "g1".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                }],
            }],
            tokens: vec![ProofToken {
                token_id: format!("tok-t11-{suffix}"),
                token_type: "DIA_TOKEN".into(),
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
    };

    let dia_1 = make_dia_ctx("1");
    let dia_2 = make_dia_ctx("2");

    let p1 = compile(dia_1.clone()).unwrap().permission;
    let p2 = compile(dia_2.clone()).unwrap().permission;
    assert_eq!(p1, Permission::DIA, "setup: dia_1 should compile to DIA");
    assert_eq!(p2, Permission::DIA, "setup: dia_2 should compile to DIA");

    // Compose: result must not exceed DIA.
    let composed = compose(dia_1, dia_2).unwrap();
    let p_composed = compile(composed).unwrap().permission;
    assert!(
        p_composed <= Permission::DIA,
        "T11: DIA + DIA must not exceed DIA; got {p_composed}"
    );
}

/// Composing two DIA-only contexts via authority ceiling never produces above DIA.
///
/// T11 applies when the authority ceiling on a context is set to DIA:
/// no composition can elevate above the ceiling.
#[test]
fn t11_dia_ceiling_prevents_action_permission() {
    let claim_id = "claim-t11-ceil";
    let candidate_id = "z-t11-ceil";
    let context_id = "ctx-t11-ceil";
    let allowed_use = "t11-ceil-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    // Context with DIA authority ceiling: even if all gaps are closed,
    // the ceiling prevents any permission above DIA.
    let make_capped_ctx = |suffix: &str, ceiling: Permission| ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: format!("fp-t11-ceil-{suffix}"),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "t"), GapRecord::closed("g2", "t")],
        profiles: vec![
            Profile {
                permission: Permission::AAA,
                required_gaps: vec![
                    GapRequirement { gap_id: "g1".into(), minimum_status: RequiredStatus::ClosedRequired },
                    GapRequirement { gap_id: "g2".into(), minimum_status: RequiredStatus::ClosedRequired },
                ],
            },
            Profile {
                permission: Permission::DIA,
                required_gaps: vec![
                    GapRequirement { gap_id: "g1".into(), minimum_status: RequiredStatus::ClosedRequired },
                ],
            },
        ],
        tokens: vec![ProofToken {
            token_id: format!("tok-ceil-{suffix}"),
            token_type: "CLOSE".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into(), "g2".into()],
            bounds_gaps: vec![],
            provenance_hash: hash.clone(),
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        }],
        expiry: Expiry::never(),
        authority_ceiling: ceiling,
        membership: Membership::InClass,
    };

    // With DIA ceiling: result must be ≤ DIA even though evidence supports AAA.
    let capped = make_capped_ctx("dia", Permission::DIA);
    let p_capped = compile(capped).unwrap().permission;
    assert_eq!(
        p_capped,
        Permission::DIA,
        "T11: DIA authority ceiling must prevent AAA permission"
    );

    // With AAA ceiling (uncapped): result is AAA (both gaps closed).
    let uncapped = make_capped_ctx("aaa", Permission::AAA);
    let p_uncapped = compile(uncapped).unwrap().permission;
    assert_eq!(
        p_uncapped,
        Permission::AAA,
        "T11 setup: AAA ceiling allows AAA permission"
    );
}

/// Composing a DIA-ceiling context with an AAA context produces at most DIA.
#[test]
fn t11_compose_dia_ceiling_with_aaa_stays_at_dia() {
    let claim_id = "claim-t11-comp";
    let candidate_id = "z-t11-comp";
    let context_id = "ctx-t11-comp";
    let allowed_use = "t11-comp-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let base = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-t11-comp-base".into(),
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
            token_id: "tok-t11-comp".into(),
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
        authority_ceiling: Permission::DIA, // diagnostic ceiling
        membership: Membership::InClass,
    };

    let mut uncapped = base.clone();
    uncapped.authority_ceiling = Permission::AAA;
    uncapped.context_fingerprint = "fp-t11-comp-uncapped".into();

    let p_base = compile(base.clone()).unwrap().permission;
    let p_uncapped = compile(uncapped.clone()).unwrap().permission;
    assert_eq!(p_base, Permission::DIA, "setup: capped context compiles to DIA");
    assert_eq!(p_uncapped, Permission::AAA, "setup: uncapped context compiles to AAA");

    // Composition: meet of ceilings = meet(DIA, AAA) = DIA.
    let composed = compose(base, uncapped).unwrap();
    let p_composed = compile(composed).unwrap().permission;
    assert!(
        p_composed <= Permission::DIA,
        "T11: composition of DIA-capped + AAA context must not exceed DIA; got {p_composed}"
    );
}

// ── Proptest: meet never promotes ────────────────────────────────────────────

proptest! {
    #[test]
    fn prop_t8_meet_never_promotes(p in arb_permission(), q in arb_permission()) {
        let m = p.meet(q);
        prop_assert!(m <= p, "T8: meet never promotes above left operand");
        prop_assert!(m <= q, "T8: meet never promotes above right operand");
    }

    #[test]
    fn prop_t8_meet_commutative(p in arb_permission(), q in arb_permission()) {
        prop_assert_eq!(p.meet(q), q.meet(p));
    }

    #[test]
    fn prop_t8_meet_n_never_exceeds_any_input(
        perms in prop::collection::vec(arb_permission(), 1..8),
    ) {
        let result = Permission::meet_n(perms.iter().copied()).unwrap();
        for &p in &perms {
            prop_assert!(result <= p, "T8: meet_n result must not exceed any input");
        }
    }
}
