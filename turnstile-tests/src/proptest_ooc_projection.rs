/// Property test: Out-of-class projection (Spec §8 property 6).
///
/// Every OutOfClass* membership variant must project to OOC regardless
/// of token contents, gap statuses, profiles, or authority ceiling.
///
/// This is the structural anti-laundering invariant from Theorem T1:
///   "Out-of-class systems cannot become in-class via proof tokens."
///
/// Formally: ∀ Γ. Γ.membership ≠ InClass → compile(Γ).permission = OOC
///
/// Falsification: if any out-of-class context with any token configuration
/// ever produces a permission other than OOC, the property fails.
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

fn arb_ooc_membership() -> impl Strategy<Value = Membership> {
    prop_oneof![
        Just(Membership::OutOfClassExact),
        Just(Membership::OutOfClassAuthorizedDeterministicWrite),
        Just(Membership::OutOfClassNoConsequentialUse),
        "[a-z]{3,8}".prop_map(Membership::OutOfClassOther),
    ]
}

/// Build a maximally permissive context with the given membership.
/// All gaps closed, all profiles satisfied, valid tokens — the compiler
/// has no reason to refuse other than the membership classification.
fn maximally_permissive_ctx(membership: Membership, ceiling: Permission) -> ProofContext {
    let claim_id = "claim-ooc";
    let candidate_id = "z-ooc";
    let context_id = "ctx-ooc";
    let allowed_use = "ooc-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-ooc".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![
            GapRecord::closed("g1", "calibration_gap"),
            GapRecord::closed("g2", "freshness_gap"),
            GapRecord::closed("g3", "authority_gap"),
        ],
        profiles: vec![
            Profile {
                permission: Permission::AAA,
                required_gaps: vec![
                    GapRequirement { gap_id: "g1".into(), minimum_status: RequiredStatus::ClosedRequired },
                    GapRequirement { gap_id: "g2".into(), minimum_status: RequiredStatus::ClosedRequired },
                    GapRequirement { gap_id: "g3".into(), minimum_status: RequiredStatus::ClosedRequired },
                ],
            },
        ],
        tokens: vec![
            ProofToken {
                token_id: "tok-ooc-1".into(),
                token_type: "CLOSE".into(),
                schema_version: "0.1".into(),
                status: TokenStatus::Valid,
                closes_gaps: vec!["g1".into(), "g2".into(), "g3".into()],
                bounds_gaps: vec![],
                provenance_hash: hash.clone(),
                issued_at: Utc::now(),
                expires_at: None,
                issuer: "ooc-test".into(),
                details: serde_json::Value::Null,
                is_negative_control: false,
            },
        ],
        expiry: Expiry::never(),
        authority_ceiling: ceiling,
        membership,
    }
}

// ── Deterministic per-variant tests ──────────────────────────────────────────

#[test]
fn out_of_class_exact_always_ooc() {
    let ctx = maximally_permissive_ctx(Membership::OutOfClassExact, Permission::AAA);
    assert_eq!(compile(ctx).unwrap().permission, Permission::OOC);
}

#[test]
fn out_of_class_deterministic_write_always_ooc() {
    let ctx = maximally_permissive_ctx(
        Membership::OutOfClassAuthorizedDeterministicWrite,
        Permission::AAA,
    );
    assert_eq!(compile(ctx).unwrap().permission, Permission::OOC);
}

#[test]
fn out_of_class_no_consequential_use_always_ooc() {
    let ctx = maximally_permissive_ctx(
        Membership::OutOfClassNoConsequentialUse,
        Permission::AAA,
    );
    assert_eq!(compile(ctx).unwrap().permission, Permission::OOC);
}

#[test]
fn out_of_class_other_always_ooc() {
    let ctx = maximally_permissive_ctx(
        Membership::OutOfClassOther("custom-domain".into()),
        Permission::AAA,
    );
    assert_eq!(compile(ctx).unwrap().permission, Permission::OOC);
}

#[test]
fn ooc_is_independent_of_token_count() {
    // Adding more tokens to an OOC context must not change the OOC result.
    let claim_id = "claim-ooc-tok";
    let candidate_id = "z-ooc-tok";
    let context_id = "ctx-ooc-tok";
    let allowed_use = "use-tok";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let make_token = |id: &str, gap: &str| ProofToken {
        token_id: id.into(),
        token_type: "CLOSE".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![gap.into()],
        bounds_gaps: vec![],
        provenance_hash: hash.clone(),
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };

    for n_tokens in 0..=5 {
        let tokens: Vec<ProofToken> = (0..n_tokens)
            .map(|i| make_token(&format!("tok-{i}"), &format!("g{i}")))
            .collect();
        let gaps: Vec<GapRecord> = (0..n_tokens)
            .map(|i| GapRecord::closed(format!("g{i}"), "t"))
            .collect();
        let profiles = if n_tokens > 0 {
            vec![Profile {
                permission: Permission::AAA,
                required_gaps: (0..n_tokens)
                    .map(|i| GapRequirement {
                        gap_id: format!("g{i}"),
                        minimum_status: RequiredStatus::ClosedRequired,
                    })
                    .collect(),
            }]
        } else {
            vec![]
        };

        let ctx = ProofContext {
            claim_id: claim_id.into(),
            candidate_id: candidate_id.into(),
            context_id: context_id.into(),
            context_fingerprint: "fp".into(),
            allowed_use: allowed_use.into(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps,
            profiles,
            tokens,
            expiry: Expiry::never(),
            authority_ceiling: Permission::AAA,
            membership: Membership::OutOfClassExact,
        };
        let j = compile(ctx).unwrap();
        assert_eq!(
            j.permission,
            Permission::OOC,
            "OOC violated at n_tokens={n_tokens}"
        );
    }
}

#[test]
fn ooc_membership_gates_before_gap_evidence() {
    // Membership check runs first (Step 1). Even if all gaps are Closed
    // and profiles are satisfied, OOC membership wins.
    let ctx = maximally_permissive_ctx(Membership::OutOfClassExact, Permission::AAA);
    let j = compile(ctx).unwrap();
    // The derivation must show membership_check as the first step.
    let first_step = j.derivation.steps.first().expect("must have at least one step");
    assert_eq!(first_step.phase, "membership_check");
    assert_eq!(j.permission, Permission::OOC);
}

// ── Proptest: all OOC variants project to OOC under any configuration ─────

proptest! {
    #[test]
    fn prop_all_ooc_variants_emit_ooc(
        membership in arb_ooc_membership(),
        ceiling in arb_permission(),
        n_gaps in 0usize..4usize,
    ) {
        let claim_id = "c-prop-ooc";
        let candidate_id = "z-prop-ooc";
        let context_id = "ctx-prop-ooc";
        let allowed_use = "prop-ooc";
        let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

        let gaps: Vec<GapRecord> = (0..n_gaps)
            .map(|i| GapRecord::closed(format!("g{i}"), "t"))
            .collect();
        let profiles = if n_gaps > 0 {
            vec![Profile {
                permission: Permission::AAA,
                required_gaps: (0..n_gaps).map(|i| GapRequirement {
                    gap_id: format!("g{i}"),
                    minimum_status: RequiredStatus::ClosedRequired,
                }).collect(),
            }]
        } else {
            vec![]
        };
        let tokens: Vec<ProofToken> = if n_gaps > 0 {
            vec![ProofToken {
                token_id: "tok-prop".into(),
                token_type: "CLOSE".into(),
                schema_version: "0.1".into(),
                status: TokenStatus::Valid,
                closes_gaps: (0..n_gaps).map(|i| format!("g{i}")).collect(),
                bounds_gaps: vec![],
                provenance_hash: hash,
                issued_at: Utc::now(),
                expires_at: None,
                issuer: "test".into(),
                details: serde_json::Value::Null,
                is_negative_control: false,
            }]
        } else {
            vec![]
        };

        let ctx = ProofContext {
            claim_id: claim_id.into(),
            candidate_id: candidate_id.into(),
            context_id: context_id.into(),
            context_fingerprint: "fp-prop-ooc".into(),
            allowed_use: allowed_use.into(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps,
            profiles,
            tokens,
            expiry: Expiry::never(),
            authority_ceiling: ceiling,
            membership,
        };

        let j = compile(ctx).unwrap();
        prop_assert_eq!(
            j.permission,
            Permission::OOC,
            "OOC variant must emit OOC; got {}", j.permission
        );
    }

    /// Composition of any OOC context with any context must produce OOC.
    #[test]
    fn prop_compose_with_ooc_always_ooc(
        ooc_membership in arb_ooc_membership(),
        ceiling in arb_permission(),
    ) {
        let ooc_ctx = maximally_permissive_ctx(ooc_membership, ceiling);
        // Build an InClass context with same allowed_use.
        let inclass_ctx = ProofContext {
            claim_id: "claim-ooc".into(),
            candidate_id: "z-ooc".into(),
            context_id: "ctx-ooc".into(),
            context_fingerprint: "fp-ooc2".into(),
            allowed_use: "ooc-use".into(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps: vec![],
            profiles: vec![],
            tokens: vec![],
            expiry: Expiry::never(),
            authority_ceiling: Permission::AAA,
            membership: Membership::InClass,
        };

        if let Ok(composed) = turnstile_core::compose(ooc_ctx, inclass_ctx) {
            let j = compile(composed).unwrap();
            prop_assert_eq!(
                j.permission,
                Permission::OOC,
                "composed context containing OOC must emit OOC"
            );
        }
    }
}
