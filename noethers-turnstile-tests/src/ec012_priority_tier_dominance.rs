/// EC-012 — Priority tier dominance (T8, T10).
///
/// The compiler applies outcomes in priority tiers.  Higher-priority blockers
/// must always dominate lower-priority ones, regardless of token configuration.
///
/// Tier table (highest first):
///   Tier 5 — OOC  (out-of-class membership)
///   Tier 4 — EXP  (expired context/token)
///   Tier 3 — REF, UNS  (structural refusal / unsupported)
///   Tier 2 — ESC, ROL, ETA  (control outcomes)
///   Tier 1 — DIA, REV  (diagnostic / recommend review)
///   Tier 0 — AEX, ALR, AAA  (action permissions)
///
/// Tests:
///   - OOC always dominates any non-OOC profile outcome
///   - EXP always dominates positive action permissions
///   - Context expiry fires before any profile can emit a positive permission
///   - Authority ceiling of OOC emits OOC even if membership is InClass
///   - Authority ceiling lower than profile permission clips to ceiling
///   - Disallowed-uses ceiling (ROL) applied before authority ceiling
///   - Priority order: OOC > EXP > authority ceiling meet
///   - Membership check (OOC) fires before descending-search (profile check)
///   - Expired token floors outcome below any profile permission
///   - Context expiry fires even if all tokens are valid and not expired
use chrono::{Duration, Utc};
use noethers_turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

// ── Helpers ───────────────────────────────────────────────────────────────────

fn make_ctx_with_profile(membership: Membership, profile_perm: Permission) -> ProofContext {
    let claim_id = "claim-t12";
    let candidate_id = "z-t12";
    let context_id = "ctx-t12";
    let allowed_use = "t12-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-t12".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "calibration_gap")],
        profiles: vec![Profile {
            permission: profile_perm,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-t12".into(),
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
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership,
    }
}

// ── Tier 5: OOC dominates ─────────────────────────────────────────────────────

#[test]
fn ooc_dominates_all_profile_permissions_exhaustive() {
    // For every possible profile permission, OOC membership always yields OOC.
    for profile_perm in Permission::descending() {
        let ctx = make_ctx_with_profile(Membership::OutOfClassExact, profile_perm);
        let j = compile(ctx).unwrap();
        assert_eq!(
            j.permission,
            Permission::OOC,
            "Tier 5: OOC membership must yield OOC regardless of profile {profile_perm}"
        );
    }
}

#[test]
fn ooc_all_membership_variants_emit_ooc() {
    let variants = [
        Membership::OutOfClassExact,
        Membership::OutOfClassAuthorizedDeterministicWrite,
        Membership::OutOfClassNoConsequentialUse,
        Membership::OutOfClassOther("custom".into()),
    ];
    for m in variants {
        let ctx = make_ctx_with_profile(m.clone(), Permission::AAA);
        let j = compile(ctx).unwrap();
        assert_eq!(
            j.permission,
            Permission::OOC,
            "Tier 5: out-of-class variant {:?} must emit OOC",
            m
        );
    }
}

#[test]
fn membership_check_fires_before_descending_search() {
    // Even if the profile is perfectly satisfied (AAA), OOC membership takes priority.
    let ctx = make_ctx_with_profile(Membership::OutOfClassExact, Permission::AAA);
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::OOC);
    // The derivation must show the membership_check step, not a profile-satisfied step.
    let first_step = j
        .derivation
        .steps
        .first()
        .expect("derivation must have steps");
    assert_eq!(
        first_step.phase, "membership_check",
        "first derivation step must be membership_check when OOC"
    );
}

// ── Tier 4: EXP dominates positive permissions ───────────────────────────────

#[test]
fn expired_token_floors_outcome_when_profile_would_satisfy() {
    // The expiry blocker only fires when outcome > EXP (i.e., a profile was
    // satisfied but an expired token is in the context).
    // We need a context where:
    //   1. A valid non-expired token satisfies the profile (outcome > EXP).
    //   2. A separate expired token exists in the context.
    // The expiry blocker must then floor outcome to EXP.
    let claim_id = "claim-t12-exp";
    let candidate_id = "z-t12-exp";
    let context_id = "ctx-t12-exp";
    let allowed_use = "t12-exp-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    // Good token closes g1 (non-expired).
    let good_token = ProofToken {
        token_id: "tok-good".into(),
        token_type: "CLOSE".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash.clone(),
        issued_at: Utc::now() - Duration::hours(1),
        expires_at: None, // never expires
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };

    // Separate expired token (closes a different gap that isn't required).
    let expired_token = ProofToken {
        token_id: "tok-expired".into(),
        token_type: "OTHER".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g_other".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now() - Duration::hours(2),
        expires_at: Some(Utc::now() - Duration::hours(1)), // expired
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-t12-exp".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![
            GapRecord::open("g1", "calibration_gap"),
            GapRecord::open("g_other", "other_gap"),
        ],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![good_token, expired_token],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "Tier 4: expired token in context must floor outcome to EXP even when profile satisfied"
    );
    assert!(
        j.permission < Permission::AEX,
        "EXP must be below any action permission"
    );
}

#[test]
fn context_expiry_fired_yields_exp() {
    let claim_id = "claim-t12-ctx-exp";
    let candidate_id = "z-t12-ctx-exp";
    let context_id = "ctx-t12-ctx-exp";
    let allowed_use = "t12-ctx-exp-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    // Context expiry already fired.
    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-t12-ctx-exp".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "calibration_gap")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-t12-ctx-exp".into(),
            token_type: "CLOSE".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now() - Duration::hours(2),
            expires_at: None, // token itself not expired
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        }],
        expiry: Expiry::at(Utc::now() - Duration::hours(1)), // context expired
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::EXP,
        "Tier 4: fired context expiry must yield EXP"
    );
}

#[test]
fn exp_is_above_ooc_in_lattice_order() {
    // Sanity check: EXP > OOC in the total order.
    assert!(
        Permission::EXP > Permission::OOC,
        "EXP must be strictly above OOC — OOC is the absolute bottom"
    );
}

// ── Authority ceiling clips profile permission ───────────────────────────────

#[test]
fn authority_ceiling_clips_profile_permission_all_pairs() {
    // For every (profile_perm, ceiling) pair where ceiling < profile_perm,
    // compile() must emit ceiling.
    let all: Vec<Permission> = Permission::descending().collect();
    for &profile_perm in &all {
        for &ceiling in &all {
            if ceiling >= profile_perm {
                continue; // ceiling above or equal to profile — no clipping
            }
            let claim_id = "claim-ceil";
            let candidate_id = "z-ceil";
            let context_id = "ctx-ceil";
            let allowed_use = "ceil-use";
            let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

            let ctx = ProofContext {
                claim_id: claim_id.into(),
                candidate_id: candidate_id.into(),
                context_id: context_id.into(),
                context_fingerprint: "fp-ceil".into(),
                allowed_use: allowed_use.into(),
                disallowed_uses: vec![],
                scope: Scope::default(),
                gaps: vec![GapRecord::open("g1", "gap")],
                profiles: vec![Profile {
                    permission: profile_perm,
                    required_gaps: vec![GapRequirement {
                        gap_id: "g1".into(),
                        minimum_status: RequiredStatus::ClosedRequired,
                    }],
                }],
                tokens: vec![ProofToken {
                    token_id: "tok-ceil".into(),
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
                authority_ceiling: ceiling,
                permission_ceiling: Permission::AAA,
                membership: Membership::InClass,
            };

            let j = compile(ctx).unwrap();
            assert!(
                j.permission <= ceiling,
                "authority ceiling {ceiling} must clip profile {profile_perm}; got {}",
                j.permission
            );
        }
    }
}

// ── Disallowed-uses ceiling applied before authority ceiling ──────────────────

#[test]
fn disallowed_uses_ceiling_rol_applied_correctly() {
    // A context with AAA profile permission and a non-empty disallowed_uses list
    // must be clipped to at most ROL.
    let claim_id = "claim-t12-dis";
    let candidate_id = "z-t12-dis";
    let context_id = "ctx-t12-dis";
    let allowed_use = "t12-dis-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-t12-dis".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec!["production-write".into()],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "gap")],
        profiles: vec![Profile {
            permission: Permission::AAA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-t12-dis".into(),
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
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let j = compile(ctx).unwrap();
    assert!(
        j.permission <= Permission::ROL,
        "disallowed_uses must cap outcome at ROL; got {}",
        j.permission
    );
}

// ── No positive action when no profiles matched ───────────────────────────────

#[test]
fn no_matched_profile_emits_ooc_not_unsupported() {
    // The compiler emits OOC when no profile is satisfied (including no profiles
    // at all).  UNS is a caller-assigned outcome for "no profile exists for
    // this candidate class"; the core compiler does not distinguish them.
    let ctx = ProofContext {
        claim_id: "claim-no-profile".into(),
        candidate_id: "z-no-profile".into(),
        context_id: "ctx-no-profile".into(),
        context_fingerprint: "fp-no-profile".into(),
        allowed_use: "no-profile-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "no profiles → OOC (bottom of lattice)"
    );
}

// ── Priority ordering assertion for all tier pairs ────────────────────────────

#[test]
fn tier_5_above_all_others_in_lattice() {
    // OOC (tier 5) must be the strict minimum of the whole lattice.
    for p in Permission::descending() {
        if p != Permission::OOC {
            assert!(
                Permission::OOC < p,
                "OOC must be strictly less than {p} in the total order"
            );
        }
    }
}

#[test]
fn tier_4_exp_is_above_ooc_below_ref() {
    assert!(Permission::EXP > Permission::OOC);
    assert!(Permission::EXP < Permission::REF);
}

#[test]
fn action_permissions_are_above_control_permissions() {
    // AEX, ALR, AAA are action permissions.
    // DIA, REV are above control (ESC, ROL, ETA) in total order.
    // Control outcomes sit between diagnostic and unsupported.
    let controls = [Permission::ESC, Permission::ROL, Permission::ETA];
    let actions = [Permission::AEX, Permission::ALR, Permission::AAA];
    for ctrl in controls {
        for act in actions {
            assert!(
                ctrl < act,
                "control permission {ctrl} must be below action permission {act}"
            );
        }
    }
}
