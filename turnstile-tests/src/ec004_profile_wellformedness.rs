use chrono::Utc;
/// EC-004 — Profile wellformedness: monotonicity, greatest-satisfiable-permission.
///
/// Ported from:
///   test_ec004a_profile_monotonicity.py
///   admissibility-atlas EC-004 §4 monotonicity
///
/// Properties proved:
///   T5  — Gap requirement soundness: profile must be monotone in evidence requirement
///          (stronger permission requires at least as strong gap requirements)
///
/// Key invariant: if a profile P maps permission p₁ ≤ p₂ to gap-requirement sets
/// G₁ and G₂, then every gap requirement in G₁ must be satisfiable with whatever
/// satisfies G₂ (i.e., the descending search returns the *greatest* satisfying p).
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

fn make_token(gap_id: &str, ctx: &ProofContext) -> ProofToken {
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ProofToken {
        token_id: format!("tok-{gap_id}"),
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
    }
}

// ── Descending search returns greatest satisfying permission ─────────────────

#[test]
fn descending_search_returns_highest_satisfied_profile() {
    // Two profiles: AAA requires g1+g2 closed; DIA requires only g1 closed.
    // With g1 closed and g2 open → DIA is the greatest satisfied profile.
    let claim_id = "c";
    let candidate_id = "z";
    let context_id = "ctx";
    let allowed_use = "use";

    let base_ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "t"), GapRecord::open("g2", "t")],
        profiles: vec![
            Profile {
                permission: Permission::AAA,
                required_gaps: vec![
                    GapRequirement {
                        gap_id: "g1".into(),
                        minimum_status: RequiredStatus::ClosedRequired,
                    },
                    GapRequirement {
                        gap_id: "g2".into(),
                        minimum_status: RequiredStatus::ClosedRequired,
                    },
                ],
            },
            Profile {
                permission: Permission::DIA,
                required_gaps: vec![GapRequirement {
                    gap_id: "g1".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                }],
            },
        ],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let tok = make_token("g1", &base_ctx);
    let mut ctx = base_ctx;
    ctx.tokens.push(tok);

    let j = compile(ctx).unwrap();
    // g1 closed (by token), g2 open → AAA not satisfied, DIA is satisfied → DIA
    assert_eq!(j.permission, Permission::DIA);
}

#[test]
fn both_gaps_closed_satisfies_highest_profile() {
    let claim_id = "c";
    let candidate_id = "z";
    let context_id = "ctx";
    let allowed_use = "use";

    let mut ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "t"), GapRecord::closed("g2", "t")],
        profiles: vec![
            Profile {
                permission: Permission::REV,
                required_gaps: vec![
                    GapRequirement {
                        gap_id: "g1".into(),
                        minimum_status: RequiredStatus::ClosedRequired,
                    },
                    GapRequirement {
                        gap_id: "g2".into(),
                        minimum_status: RequiredStatus::ClosedRequired,
                    },
                ],
            },
            Profile {
                permission: Permission::DIA,
                required_gaps: vec![GapRequirement {
                    gap_id: "g1".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                }],
            },
        ],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let t1 = make_token("g1", &ctx);
    let t2 = make_token("g2", &ctx);
    ctx.tokens.push(t1);
    ctx.tokens.push(t2);

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::REV);
}

// ── Monotonicity: adding evidence never lowers permission (T5) ───────────────

#[test]
fn adding_evidence_never_lowers_permission_ordered_profiles() {
    // With a monotone profile structure, adding a token can only raise or maintain permission.
    let claim_id = "c";
    let candidate_id = "z";
    let context_id = "ctx";
    let allowed_use = "use";

    let base_ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "t")],
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
    };

    let p_before = compile(base_ctx.clone()).unwrap().permission;
    assert_eq!(p_before, Permission::OOC);

    // Add a closing token + update gap to Closed
    let tok = make_token("g1", &base_ctx);
    let mut ctx = base_ctx;
    ctx.gaps[0] = GapRecord::closed("g1", "t");
    ctx.tokens.push(tok);

    let p_after = compile(ctx).unwrap().permission;
    assert!(
        p_after >= p_before,
        "adding evidence lowered permission: {p_before} → {p_after}"
    );
    assert_eq!(p_after, Permission::DIA);
}

// ── Profile with multiple levels: descending search (monotone structure) ──────

#[test]
fn multi_level_profile_descending_search_exhaustive() {
    // For all permission pairs (p_high, p_low) where p_high > p_low,
    // a context that only satisfies p_low must not emit p_high.
    const HIGH_LOW_PAIRS: [(Permission, Permission); 6] = [
        (Permission::REV, Permission::DIA),
        (Permission::AEX, Permission::REV),
        (Permission::ALR, Permission::AEX),
        (Permission::AAA, Permission::DIA),
        (Permission::DIA, Permission::ROL),
        (Permission::ROL, Permission::ETA),
    ];

    for (p_high, p_low) in HIGH_LOW_PAIRS {
        let claim_id = "c";
        let candidate_id = "z";
        let context_id = "ctx";
        let allowed_use = "use";

        // Two gaps: g_low (for p_low profile), g_high (for p_high profile)
        let mut ctx = ProofContext {
            claim_id: claim_id.into(),
            candidate_id: candidate_id.into(),
            context_id: context_id.into(),
            context_fingerprint: "fp".into(),
            allowed_use: allowed_use.into(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps: vec![
                GapRecord::closed("g_low", "t"),
                GapRecord::open("g_high", "t"), // not satisfied
            ],
            profiles: vec![
                Profile {
                    permission: p_high,
                    required_gaps: vec![
                        GapRequirement {
                            gap_id: "g_low".into(),
                            minimum_status: RequiredStatus::ClosedRequired,
                        },
                        GapRequirement {
                            gap_id: "g_high".into(),
                            minimum_status: RequiredStatus::ClosedRequired,
                        },
                    ],
                },
                Profile {
                    permission: p_low,
                    required_gaps: vec![GapRequirement {
                        gap_id: "g_low".into(),
                        minimum_status: RequiredStatus::ClosedRequired,
                    }],
                },
            ],
            tokens: vec![],
            expiry: Expiry::never(),
            authority_ceiling: Permission::AAA,
            membership: Membership::InClass,
        };

        let tok_low = make_token("g_low", &ctx);
        ctx.tokens.push(tok_low);

        let j = compile(ctx).unwrap();
        assert_eq!(
            j.permission, p_low,
            "with g_low closed and g_high open, expected {p_low} not {p_high}"
        );
    }
}

// ── Proptest: adding a closed token never lowers permission ──────────────────

proptest! {
    #[test]
    fn prop_adding_closed_token_never_lowers(
        ceiling in arb_permission(),
        gap_count in 1usize..=4usize,
        close_idx in 0usize..4usize,
    ) {
        let claim_id = "c";
        let candidate_id = "z";
        let context_id = "ctx";
        let allowed_use = "use";

        let gap_ids: Vec<String> = (0..gap_count).map(|i| format!("g{i}")).collect();

        // All gaps open initially
        let base_gaps: Vec<GapRecord> = gap_ids.iter().map(|id| GapRecord::open(id, "t")).collect();

        let profile = Profile {
            permission: Permission::DIA,
            required_gaps: gap_ids.iter().map(|id| GapRequirement {
                gap_id: id.clone(),
                minimum_status: RequiredStatus::ClosedRequired,
            }).collect(),
        };

        let base_ctx = ProofContext {
            claim_id: claim_id.into(),
            candidate_id: candidate_id.into(),
            context_id: context_id.into(),
            context_fingerprint: "fp".into(),
            allowed_use: allowed_use.into(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps: base_gaps.clone(),
            profiles: vec![profile.clone()],
            tokens: vec![],
            expiry: Expiry::never(),
            authority_ceiling: ceiling,
            membership: Membership::InClass,
        };

        let p_before = compile(base_ctx.clone()).unwrap().permission;

        let target = close_idx % gap_count;
        let target_id = &gap_ids[target];

        let tok = make_token(target_id, &base_ctx);
        let mut enhanced_gaps = base_gaps;
        enhanced_gaps[target] = GapRecord::closed(target_id, "t");

        let enhanced_ctx = ProofContext {
            gaps: enhanced_gaps,
            tokens: vec![tok],
            ..base_ctx
        };

        let p_after = compile(enhanced_ctx).unwrap().permission;
        prop_assert!(
            p_after >= p_before,
            "adding closed token lowered permission: {p_before} → {p_after}"
        );
    }
}
