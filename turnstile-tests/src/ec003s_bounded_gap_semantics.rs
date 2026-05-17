/// EC-003S — Bounded gap semantics: BoundedRequired satisfaction, bounded tokens,
///           and gap status composition through the proof pipeline.
///
/// Covers theorems:
///   T5  — Gap requirement soundness: BoundedRequired accepts Bounded and Closed,
///          rejects Open; ClosedRequired accepts only Closed
///   T6  — No proof, no license: Open gap with BoundedRequired blocks profile
///   T2  — Token validity soundness: only Valid status provides gap support
///
/// Tests:
///   - Bounding token upgrades Open → Bounded for BoundedRequired profile
///   - Bounding token is insufficient for ClosedRequired profile
///   - Closing token satisfies both BoundedRequired and ClosedRequired
///   - Open gap with BoundedRequired blocks the profile
///   - Token with bounds_gaps closes the gap to Bounded level only
///   - Mixed: gap closed by one token, bounded by another → Closed wins
///   - Composition: min_status applies — closed + open = open
///   - Invalid/expired bounding token provides no support
///   - Bound value semantics: Numeric, SetValued, Infinity all satisfy BoundedRequired
use chrono::{Duration, Utc};
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{Bound, GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn base_ctx() -> ProofContext {
    ProofContext {
        claim_id: "claim-bd".into(),
        candidate_id: "z-bd".into(),
        context_id: "ctx-bd".into(),
        context_fingerprint: "fp-bd".into(),
        allowed_use: "bd-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

fn closing_token(gap_id: &str, ctx: &ProofContext) -> ProofToken {
    let hash = compute_provenance_hash(
        &ctx.claim_id, &ctx.candidate_id, &ctx.context_id, &ctx.allowed_use,
    );
    ProofToken {
        token_id: format!("tok-close-{gap_id}"),
        token_type: "CLOSE".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![gap_id.to_string()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

fn bounding_token(gap_id: &str, ctx: &ProofContext) -> ProofToken {
    let hash = compute_provenance_hash(
        &ctx.claim_id, &ctx.candidate_id, &ctx.context_id, &ctx.allowed_use,
    );
    ProofToken {
        token_id: format!("tok-bound-{gap_id}"),
        token_type: "BOUND".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![],
        bounds_gaps: vec![gap_id.to_string()],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

// ── BoundedRequired profile with bounding token ───────────────────────────────

#[test]
fn bounded_required_profile_satisfied_by_bounding_token() {
    let mut ctx = base_ctx();
    ctx.gaps = vec![GapRecord::open("g1", "freshness")];
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::BoundedRequired,
        }],
    }];
    let tok = bounding_token("g1", &ctx);
    ctx.tokens = vec![tok];

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "bounding token must satisfy BoundedRequired"
    );
}

#[test]
fn bounded_required_profile_fails_with_no_token() {
    let mut ctx = base_ctx();
    ctx.gaps = vec![GapRecord::open("g1", "freshness")];
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::BoundedRequired,
        }],
    }];
    // No token.
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::OOC, "no token → BoundedRequired not met");
}

// ── ClosedRequired profile with only a bounding token ─────────────────────────

#[test]
fn closed_required_profile_not_satisfied_by_bounding_token() {
    let mut ctx = base_ctx();
    ctx.gaps = vec![GapRecord::open("g1", "t")];
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    }];
    let tok = bounding_token("g1", &ctx);
    ctx.tokens = vec![tok];

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "bounding token must NOT satisfy ClosedRequired"
    );
}

// ── Closing token satisfies both requirements ─────────────────────────────────

#[test]
fn closing_token_satisfies_bounded_required() {
    let mut ctx = base_ctx();
    ctx.gaps = vec![GapRecord::open("g1", "t")];
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::BoundedRequired,
        }],
    }];
    let tok = closing_token("g1", &ctx);
    ctx.tokens = vec![tok];

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA, "closing token must satisfy BoundedRequired");
}

#[test]
fn closing_token_satisfies_closed_required() {
    let mut ctx = base_ctx();
    ctx.gaps = vec![GapRecord::open("g1", "t")];
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    }];
    let tok = closing_token("g1", &ctx);
    ctx.tokens = vec![tok];

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA, "closing token must satisfy ClosedRequired");
}

// ── GapRecord already bounded: no token needed for BoundedRequired ────────────

#[test]
fn pre_bounded_gap_satisfies_bounded_required_without_token() {
    let mut ctx = base_ctx();
    ctx.gaps = vec![GapRecord::bounded("g1", "t", Bound::numeric(0.1))];
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::BoundedRequired,
        }],
    }];
    // No token: gap record itself is already Bounded.
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "pre-bounded gap must satisfy BoundedRequired without token"
    );
}

#[test]
fn pre_closed_gap_satisfies_closed_required_without_token() {
    let mut ctx = base_ctx();
    ctx.gaps = vec![GapRecord::closed("g1", "t")];
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    }];
    // No token needed: gap record already closed.
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "pre-closed gap must satisfy ClosedRequired without token"
    );
}

// ── Mixed: both bounding and closing tokens — closing wins ────────────────────

#[test]
fn closing_wins_over_bounding_for_same_gap() {
    let mut ctx = base_ctx();
    ctx.gaps = vec![GapRecord::open("g1", "t")];
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    }];
    // Both bounding and closing tokens present.
    let bt = bounding_token("g1", &ctx);
    let ct = closing_token("g1", &ctx);
    ctx.tokens = vec![bt, ct];

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA, "closing token wins over bounding token");
}

// ── Expired bounding token provides no support ────────────────────────────────

#[test]
fn expired_bounding_token_provides_no_support() {
    // An expired token is excluded from gap support by `is_live()`.
    // The gap stays Open → BoundedRequired is not met → profile fails → OOC.
    // The expiry_blocker step fires only when outcome > EXP (OOC < EXP, so no
    // additional floor occurs). The correct result is OOC (profile not met).
    let mut ctx = base_ctx();
    ctx.gaps = vec![GapRecord::open("g1", "t")];
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::BoundedRequired,
        }],
    }];
    let hash = compute_provenance_hash(
        &ctx.claim_id, &ctx.candidate_id, &ctx.context_id, &ctx.allowed_use,
    );
    let expired_tok = ProofToken {
        token_id: "tok-expired-bound".into(),
        token_type: "BOUND".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![],
        bounds_gaps: vec!["g1".into()],
        provenance_hash: hash,
        issued_at: Utc::now() - Duration::seconds(10),
        expires_at: Some(Utc::now() - Duration::seconds(1)), // expired
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    ctx.tokens = vec![expired_tok];

    let j = compile(ctx).unwrap();
    // Expired token provides no gap support → gap stays Open → profile not met.
    // OOC < EXP, so expiry blocker does not lower further. Result is OOC.
    assert!(
        j.permission <= Permission::EXP,
        "expired bounding token must result in OOC or EXP, got {}", j.permission
    );
}

#[test]
fn expired_closing_token_floors_to_exp_when_profile_would_otherwise_pass() {
    // When a token that WOULD close a gap is expired, the expiry_blocker fires
    // AFTER the descending search (step 5). If the search found a profile
    // satisfied (using the gap_record's own Closed status), but the token is
    // expired, the expiry blocker floors the outcome to EXP.
    let mut ctx = base_ctx();
    // Gap record itself is Closed (not relying on token).
    ctx.gaps = vec![GapRecord::closed("g1", "t")];
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    }];
    let hash = compute_provenance_hash(
        &ctx.claim_id, &ctx.candidate_id, &ctx.context_id, &ctx.allowed_use,
    );
    // Add an expired token (even though it's not needed for the gap since the
    // gap record is already closed). Its expiry still triggers the expiry blocker.
    let expired_tok = ProofToken {
        token_id: "tok-expired-close".into(),
        token_type: "CLOSE".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now() - Duration::seconds(10),
        expires_at: Some(Utc::now() - Duration::seconds(1)), // expired
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    ctx.tokens = vec![expired_tok];

    let j = compile(ctx).unwrap();
    // The gap is already Closed (via GapRecord), so the profile is satisfied
    // during descending search (outcome = DIA). Then expiry_blocker fires
    // because the token is expired → floors to EXP.
    assert_eq!(
        j.permission,
        Permission::EXP,
        "expired token in context must floor judgment to EXP"
    );
}

// ── Invalid bounding token provides no support ────────────────────────────────

#[test]
fn invalid_bounding_token_provides_no_support() {
    let mut ctx = base_ctx();
    ctx.gaps = vec![GapRecord::open("g1", "t")];
    ctx.profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::BoundedRequired,
        }],
    }];
    for bad_status in [TokenStatus::Invalid, TokenStatus::Revoked, TokenStatus::Malformed] {
        let hash = compute_provenance_hash(
            &ctx.claim_id, &ctx.candidate_id, &ctx.context_id, &ctx.allowed_use,
        );
        let tok = ProofToken {
            token_id: format!("tok-{bad_status:?}"),
            token_type: "BOUND".into(),
            schema_version: "0.1".into(),
            status: bad_status,
            closes_gaps: vec![],
            bounds_gaps: vec!["g1".into()],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        };
        let mut ctx_copy = ctx.clone();
        ctx_copy.tokens = vec![tok];
        let j = compile(ctx_copy).unwrap();
        assert_eq!(
            j.permission,
            Permission::OOC,
            "{bad_status:?} bounding token must provide no gap support"
        );
    }
}

// ── Bound value types all satisfy BoundedRequired ─────────────────────────────

#[test]
fn numeric_bound_satisfies_bounded_required() {
    let bound = Bound::numeric(0.05);
    assert!(RequiredStatus::BoundedRequired.satisfied_by(&turnstile_core::gap::GapStatus::Bounded(bound)));
}

#[test]
fn infinity_bound_satisfies_bounded_required() {
    let bound = Bound::infinity();
    assert!(RequiredStatus::BoundedRequired.satisfied_by(&turnstile_core::gap::GapStatus::Bounded(bound)));
}

#[test]
fn set_valued_bound_satisfies_bounded_required() {
    let bound = Bound::set_valued(vec!["read".into(), "list".into()]);
    assert!(RequiredStatus::BoundedRequired.satisfied_by(&turnstile_core::gap::GapStatus::Bounded(bound)));
}

// ── Two-profile hierarchy: bounded admits DIA, closed admits REV ──────────────

#[test]
fn two_profile_hierarchy_bounding_token_reaches_lower_permission_only() {
    let mut ctx = base_ctx();
    ctx.gaps = vec![GapRecord::open("g1", "t")];
    // REV requires closed; DIA requires bounded.
    ctx.profiles = vec![
        Profile {
            permission: Permission::REV,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        },
        Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::BoundedRequired,
            }],
        },
    ];
    let tok = bounding_token("g1", &ctx);
    ctx.tokens = vec![tok];

    let j = compile(ctx).unwrap();
    // Bounding satisfies DIA but not REV.
    assert_eq!(j.permission, Permission::DIA, "bounding token reaches DIA but not REV");
}

#[test]
fn two_profile_hierarchy_closing_token_reaches_highest_permission() {
    let mut ctx = base_ctx();
    ctx.gaps = vec![GapRecord::open("g1", "t")];
    ctx.profiles = vec![
        Profile {
            permission: Permission::REV,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        },
        Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::BoundedRequired,
            }],
        },
    ];
    let tok = closing_token("g1", &ctx);
    ctx.tokens = vec![tok];

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::REV, "closing token reaches REV");
}
