/// EC-003J — Multi-gap, multi-token: realistic profile structures.
///
/// Covers theorems:
///   T5  — Gap requirement soundness: all required gaps must be satisfied
///   T6  — No proof, no license: missing any gap → blocked
///   T9  — Descending search finds greatest satisfying permission
///
/// Tests scenarios with:
/// - Multiple gaps required by a single profile
/// - Multiple tokens closing different gaps
/// - Partial satisfaction falls to a lower permission
/// - Adding one more token promotes to the next permission
/// - Tokens with bounds_gaps (BoundedRequired)
use chrono::Utc;
use proptest::prelude::*;
use noethers_turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{Bound, GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn make_token(gap_ids: &[&str], bounds_gap_ids: &[&str], ctx: &ProofContext) -> ProofToken {
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ProofToken {
        token_id: format!("tok-{}", gap_ids.join("+")),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: gap_ids.iter().map(|s| s.to_string()).collect(),
        bounds_gaps: bounds_gap_ids.iter().map(|s| s.to_string()).collect(),
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

fn base_ctx() -> ProofContext {
    ProofContext {
        claim_id: "claim-mg".into(),
        candidate_id: "z-mg".into(),
        context_id: "ctx-mg".into(),
        context_fingerprint: "fp-mg".into(),
        allowed_use: "mg-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── 3-gap profile: all required, partial satisfaction ────────────────────────

#[test]
fn three_gap_profile_requires_all_closed() {
    let mut ctx = base_ctx();
    ctx.gaps = vec![
        GapRecord::closed("g1", "t"),
        GapRecord::closed("g2", "t"),
        GapRecord::open("g3", "t"),
    ];
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g2".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g3".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    }];

    let t1 = make_token(&["g1"], &[], &ctx);
    let t2 = make_token(&["g2"], &[], &ctx);
    ctx.tokens = vec![t1, t2]; // g3 not closed

    let j = compile(ctx).unwrap();
    // Missing g3 → profile not satisfied → UNS (in-class, profile defined)
    assert_eq!(
        j.permission,
        Permission::UNS,
        "missing g3 must block DIA; in-class → UNS not OOC"
    );
}

#[test]
fn three_gap_profile_all_closed_satisfies() {
    let mut ctx = base_ctx();
    ctx.gaps = vec![
        GapRecord::closed("g1", "t"),
        GapRecord::closed("g2", "t"),
        GapRecord::closed("g3", "t"),
    ];
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![
            GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g2".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
            GapRequirement {
                gap_id: "g3".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            },
        ],
    }];

    let t1 = make_token(&["g1"], &[], &ctx);
    let t2 = make_token(&["g2"], &[], &ctx);
    let t3 = make_token(&["g3"], &[], &ctx);
    ctx.tokens = vec![t1, t2, t3];

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA);
}

// ── Two-tier profile: low profile with 1 gap, high profile with 3 gaps ───────

#[test]
fn two_tier_profile_partial_evidence_lands_on_lower() {
    let mut ctx = base_ctx();
    ctx.gaps = vec![
        GapRecord::closed("g1", "t"),
        GapRecord::open("g2", "t"),
        GapRecord::open("g3", "t"),
    ];
    ctx.profiles = vec![
        Profile {
            permission: Permission::REV, // requires all 3
            required_gaps: vec![
                GapRequirement {
                    gap_id: "g1".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                },
                GapRequirement {
                    gap_id: "g2".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                },
                GapRequirement {
                    gap_id: "g3".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                },
            ],
        },
        Profile {
            permission: Permission::DIA, // requires only g1
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        },
    ];

    let t1 = make_token(&["g1"], &[], &ctx);
    ctx.tokens = vec![t1]; // only g1 closed

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "partial evidence → descending search lands on DIA"
    );
}

#[test]
fn two_tier_profile_full_evidence_lands_on_higher() {
    let mut ctx = base_ctx();
    ctx.gaps = vec![
        GapRecord::closed("g1", "t"),
        GapRecord::closed("g2", "t"),
        GapRecord::closed("g3", "t"),
    ];
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
                GapRequirement {
                    gap_id: "g3".into(),
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

    let t1 = make_token(&["g1"], &[], &ctx);
    let t2 = make_token(&["g2"], &[], &ctx);
    let t3 = make_token(&["g3"], &[], &ctx);
    ctx.tokens = vec![t1, t2, t3];

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::REV,
        "full evidence → highest satisfied profile"
    );
}

// ── BoundedRequired is satisfied by a bounding token ─────────────────────────

#[test]
fn bounding_token_satisfies_bounded_required() {
    let mut ctx = base_ctx();
    let gap_id = "g1";
    ctx.gaps = vec![GapRecord::bounded(gap_id, "t", Bound::numeric(0.05))];
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: gap_id.into(),
            minimum_status: RequiredStatus::BoundedRequired,
        }],
    }];

    let t = ProofToken {
        token_id: "tok-bounds".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![],
        bounds_gaps: vec![gap_id.into()], // bounds, not closes
        provenance_hash: compute_provenance_hash(
            &ctx.claim_id,
            &ctx.candidate_id,
            &ctx.context_id,
            &ctx.allowed_use,
        ),
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    ctx.tokens = vec![t];

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "bounding token must satisfy BoundedRequired"
    );
}

#[test]
fn bounding_token_does_not_satisfy_closed_required() {
    let mut ctx = base_ctx();
    let gap_id = "g1";
    ctx.gaps = vec![GapRecord::bounded(gap_id, "t", Bound::numeric(0.05))];
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: gap_id.into(),
            minimum_status: RequiredStatus::ClosedRequired, // stricter requirement
        }],
    }];

    let t = ProofToken {
        token_id: "tok-bounds-only".into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![],
        bounds_gaps: vec![gap_id.into()], // only bounds, does not close
        provenance_hash: compute_provenance_hash(
            &ctx.claim_id,
            &ctx.candidate_id,
            &ctx.context_id,
            &ctx.allowed_use,
        ),
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    ctx.tokens = vec![t];

    let j = compile(ctx).unwrap();
    // Bounding token doesn't satisfy ClosedRequired → UNS (in-class, profile defined)
    assert_eq!(
        j.permission,
        Permission::UNS,
        "bounding token must not satisfy ClosedRequired; in-class → UNS not OOC"
    );
}

// ── Single token closing multiple gaps ───────────────────────────────────────

#[test]
fn single_token_closing_multiple_gaps() {
    let mut ctx = base_ctx();
    ctx.gaps = vec![GapRecord::closed("g1", "t"), GapRecord::closed("g2", "t")];
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
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
    }];

    let t = make_token(&["g1", "g2"], &[], &ctx); // single token closes both
    ctx.tokens = vec![t];

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "single token closing multiple gaps must work"
    );
}

// ── Proptest: descending search returns the greatest satisfied permission ─────

fn arb_permission_operational() -> impl Strategy<Value = Permission> {
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
    fn prop_two_tier_descending_returns_max_satisfied(
        p_low in arb_permission_operational(),
        p_high_offset in 1usize..=5usize,
    ) {
        // p_high is higher than p_low by offset steps in the chain
        let all: Vec<Permission> = Permission::descending().collect::<Vec<_>>()
            .into_iter().rev().collect();
        let idx_low = all.iter().position(|&p| p == p_low).unwrap_or(7);
        let idx_high = (idx_low + p_high_offset).min(11);
        let p_high = all[idx_high];

        prop_assume!(p_high > p_low);

        let mut ctx = base_ctx();
        ctx.gaps = vec![
            GapRecord::closed("g_low", "t"),
            GapRecord::open("g_high", "t"),
        ];
        ctx.profiles = vec![
            Profile {
                permission: p_high,
                required_gaps: vec![
                    GapRequirement { gap_id: "g_low".into(), minimum_status: RequiredStatus::ClosedRequired },
                    GapRequirement { gap_id: "g_high".into(), minimum_status: RequiredStatus::ClosedRequired },
                ],
            },
            Profile {
                permission: p_low,
                required_gaps: vec![
                    GapRequirement { gap_id: "g_low".into(), minimum_status: RequiredStatus::ClosedRequired },
                ],
            },
        ];

        let tok = make_token(&["g_low"], &[], &ctx);
        ctx.tokens = vec![tok];

        let j = compile(ctx).unwrap();
        prop_assert_eq!(j.permission, p_low,
            "with g_high open, expected {:?} not {:?}", p_low, p_high);
    }
}
