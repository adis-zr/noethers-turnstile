/// EC-003M — Evidence monotonicity: adding closed evidence never lowers permission;
///           adding blockers never raises it.
///
/// This is property #3 from turnstile_spec.md §8:
///   "Adding a closed proof token never lowers the emitted permission.
///    Adding a runtime blocker never raises it."
///
/// Covers theorems:
///   T10 — Composition monotonicity
///   Spec §8 property 3 — Monotonicity in evidence
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

fn base_ctx_with_gaps(gap_ids: &[&str], closed: &[bool]) -> ProofContext {
    let claim_id = "c-mono";
    let candidate_id = "z-mono";
    let context_id = "ctx-mono";
    let allowed_use = "mono-use";
    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-mono".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: gap_ids
            .iter()
            .zip(closed.iter())
            .map(|(&id, &cl)| {
                if cl {
                    GapRecord::closed(id, "t")
                } else {
                    GapRecord::open(id, "t")
                }
            })
            .collect(),
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

fn make_closing_token(gap_id: &str, ctx: &ProofContext) -> ProofToken {
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

// ── Adding a closing token to an empty context raises permission ──────────────

#[test]
fn adding_closed_token_raises_permission_from_ooc() {
    let mut ctx = base_ctx_with_gaps(&["g1"], &[false]);
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    }];
    let p_before = compile(ctx.clone()).unwrap().permission;
    // In-class candidate with a profile defined but gap unmet → REF (not OOC)
    assert_eq!(p_before, Permission::REF);

    // Now close the gap with a token
    let tok = make_closing_token("g1", &ctx);
    ctx.gaps[0] = GapRecord::closed("g1", "t");
    ctx.tokens.push(tok);

    let p_after = compile(ctx).unwrap().permission;
    assert!(
        p_after >= p_before,
        "adding evidence lowered permission: {p_before} → {p_after}"
    );
    assert_eq!(p_after, Permission::DIA);
}

// ── Adding a second closing token, enabling a higher profile ──────────────────

#[test]
fn adding_second_token_enables_higher_profile() {
    let mut ctx = base_ctx_with_gaps(&["g1", "g2"], &[false, false]);
    ctx.profiles = vec![
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
    ];

    // Close g1 only → DIA
    let t1 = make_closing_token("g1", &ctx);
    ctx.gaps[0] = GapRecord::closed("g1", "t");
    ctx.tokens.push(t1);
    let p_g1_only = compile(ctx.clone()).unwrap().permission;
    assert_eq!(p_g1_only, Permission::DIA);

    // Also close g2 → REV (higher)
    let t2 = make_closing_token("g2", &ctx);
    ctx.gaps[1] = GapRecord::closed("g2", "t");
    ctx.tokens.push(t2);
    let p_both = compile(ctx).unwrap().permission;
    assert!(p_both >= p_g1_only, "adding g2 token lowered permission");
    assert_eq!(p_both, Permission::REV);
}

// ── Adding a disallowed_use blocker lowers permission ─────────────────────────

#[test]
fn adding_disallowed_use_lowers_permission() {
    let mut ctx = base_ctx_with_gaps(&["g1"], &[true]);
    ctx.profiles = vec![Profile {
        permission: Permission::AAA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    }];
    let tok = make_closing_token("g1", &ctx);
    ctx.tokens.push(tok);

    let p_clean = compile(ctx.clone()).unwrap().permission;
    assert_eq!(p_clean, Permission::AAA);

    // Add a blocker
    ctx.disallowed_uses = vec!["write".into()];
    let p_blocked = compile(ctx).unwrap().permission;
    assert!(
        p_blocked <= p_clean,
        "adding blocker must not raise permission"
    );
    assert_eq!(p_blocked, Permission::ROL);
}

// ── Adding a lower authority ceiling lowers or preserves permission ───────────

#[test]
fn lowering_authority_ceiling_never_raises() {
    let mut ctx = base_ctx_with_gaps(&["g1"], &[true]);
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    }];
    let tok = make_closing_token("g1", &ctx);
    ctx.tokens.push(tok);

    let p_aaa = compile(ctx.clone()).unwrap().permission;
    assert_eq!(p_aaa, Permission::DIA);

    ctx.authority_ceiling = Permission::ROL;
    let p_capped = compile(ctx).unwrap().permission;
    assert!(p_capped <= p_aaa, "lowering ceiling raised permission");
    assert_eq!(p_capped, Permission::ROL);
}

// ── Monotonicity: each additional gap closed ≥ previous ─────────────────────

#[test]
fn closing_gaps_incrementally_never_lowers() {
    let gap_ids = ["g1", "g2", "g3", "g4"];
    let mut ctx = base_ctx_with_gaps(&gap_ids, &[false; 4]);

    // Build profiles: each adds one more gap requirement
    ctx.profiles = vec![
        Profile {
            permission: Permission::REV,
            required_gaps: gap_ids
                .iter()
                .map(|id| GapRequirement {
                    gap_id: id.to_string(),
                    minimum_status: RequiredStatus::ClosedRequired,
                })
                .collect(),
        },
        Profile {
            permission: Permission::DIA,
            required_gaps: gap_ids[..2]
                .iter()
                .map(|id| GapRequirement {
                    gap_id: id.to_string(),
                    minimum_status: RequiredStatus::ClosedRequired,
                })
                .collect(),
        },
        Profile {
            permission: Permission::ROL,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        },
    ];

    let mut prev_p = Permission::OOC;
    for (i, gap_id) in gap_ids.iter().enumerate() {
        ctx.gaps[i] = GapRecord::closed(*gap_id, "t");
        let tok = make_closing_token(gap_id, &ctx);
        ctx.tokens.push(tok);

        let p = compile(ctx.clone()).unwrap().permission;
        assert!(
            p >= prev_p,
            "closing gap {gap_id} lowered permission: {prev_p} → {p}"
        );
        prev_p = p;
    }
}

// ── Proptest: adding a closed gap token never lowers permission ───────────────

fn arb_permission() -> impl Strategy<Value = Permission> {
    prop_oneof![
        Just(Permission::DIA),
        Just(Permission::REV),
        Just(Permission::AEX),
        Just(Permission::ALR),
        Just(Permission::AAA),
    ]
}

proptest! {
    #[test]
    fn prop_adding_closed_token_never_lowers_monotonicity(
        target in arb_permission(),
        ceiling in arb_permission(),
    ) {
        let claim_id = "c-mprop";
        let candidate_id = "z-mprop";
        let context_id = "ctx-mprop";
        let allowed_use = "mprop-use";
        let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

        let base_ctx = ProofContext {
            claim_id: claim_id.into(),
            candidate_id: candidate_id.into(),
            context_id: context_id.into(),
            context_fingerprint: "fp-mprop".into(),
            allowed_use: allowed_use.into(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps: vec![GapRecord::open("g1", "t")],
            profiles: vec![Profile {
                permission: target,
                required_gaps: vec![GapRequirement {
                    gap_id: "g1".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                }],
            }],
            tokens: vec![],
            expiry: Expiry::never(),
            authority_ceiling: ceiling,
            membership: Membership::InClass,
        };

        let p_before = compile(base_ctx.clone()).unwrap().permission;

        let tok = ProofToken {
            token_id: "tok-mprop".into(),
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
        };

        let enhanced = ProofContext {
            gaps: vec![GapRecord::closed("g1", "t")],
            tokens: vec![tok],
            ..base_ctx
        };

        let p_after = compile(enhanced).unwrap().permission;
        prop_assert!(
            p_after >= p_before,
            "adding closed token lowered: {p_before} → {p_after}"
        );
    }

    #[test]
    fn prop_adding_blocker_never_raises(
        target in arb_permission(),
        n_blockers in 1usize..=4usize,
    ) {
        let claim_id = "c-blocker";
        let candidate_id = "z-blocker";
        let context_id = "ctx-blocker";
        let allowed_use = "blocker-use";
        let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

        let tok = ProofToken {
            token_id: "tok-blocker".into(),
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
        };

        let clean_ctx = ProofContext {
            claim_id: claim_id.into(),
            candidate_id: candidate_id.into(),
            context_id: context_id.into(),
            context_fingerprint: "fp-blocker".into(),
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
            tokens: vec![tok.clone()],
            expiry: Expiry::never(),
            authority_ceiling: Permission::AAA,
            membership: Membership::InClass,
        };

        let p_clean = compile(clean_ctx.clone()).unwrap().permission;

        let blocked_ctx = ProofContext {
            disallowed_uses: (0..n_blockers).map(|i| format!("use-{i}")).collect(),
            ..clean_ctx
        };
        let p_blocked = compile(blocked_ctx).unwrap().permission;

        prop_assert!(
            p_blocked <= p_clean,
            "adding blocker raised permission: {p_clean} → {p_blocked}"
        );
    }
}
