/// EC-006 — Profile monotonicity (Law G01).
///
/// Law G01 (EC-001 §10): A profile set is monotone iff for any two permissions
/// p1 < p2, every gap requirement for p2 is at least as strict as the
/// corresponding requirement for p1.  In other words, stronger permissions
/// require at least as much (or more) evidence than weaker ones.
///
/// Violation example:
///   Profile AAA requires g1 BoundedRequired
///   Profile DIA requires g1 ClosedRequired    ← DIA requires MORE than AAA → violation
///
/// This is a misconfiguration risk: a non-monotone profile set can cause the
/// descending search to emit a *weaker* permission (DIA) even when the evidence
/// is insufficient for the stronger one (AAA), which is correct — but it may
/// also allow unexpected behaviours where adding evidence *lowers* the result
/// if the compiler is not careful.
///
/// Currently the compiler does NOT validate Law G01 on load; this test suite
/// documents the behaviour and provides a validator function for callers.
///
/// Tests:
///   - Monotone profile set: adding evidence at each level raises or maintains permission
///   - Non-monotone detection: validate_profile_monotonicity() catches violations
///   - Compiler descending search with non-monotone profiles: documents behaviour
///   - Proptest: for any monotone profile pair, adding evidence never lowers permission
use chrono::Utc;
use noethers_turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};
use proptest::prelude::*;

// ── Profile monotonicity validator ───────────────────────────────────────────

/// Law G01: returns the first violation found, if any.
///
/// A violation is: profile p_high has a gap requirement that is *weaker* than
/// the same gap's requirement in profile p_low, where p_high > p_low.
#[derive(Debug, PartialEq)]
pub struct MonotonicityViolation {
    pub gap_id: String,
    pub high_permission: Permission,
    pub low_permission: Permission,
    pub high_required: RequiredStatus,
    pub low_required: RequiredStatus,
}

pub fn validate_profile_monotonicity(profiles: &[Profile]) -> Option<MonotonicityViolation> {
    for i in 0..profiles.len() {
        for j in 0..profiles.len() {
            if profiles[i].permission <= profiles[j].permission {
                continue;
            }
            // profiles[i] is strictly stronger than profiles[j].
            // Check: for each gap required by profiles[j], the requirement in
            // profiles[i] must be at least as strict.
            for req_j in &profiles[j].required_gaps {
                if let Some(req_i) = profiles[i]
                    .required_gaps
                    .iter()
                    .find(|r| r.gap_id == req_j.gap_id)
                {
                    // ClosedRequired(2) > BoundedRequired(1) > OpenAllowed(0).
                    let rank = |r: RequiredStatus| match r {
                        RequiredStatus::OpenAllowed => 0u8,
                        RequiredStatus::BoundedRequired => 1u8,
                        RequiredStatus::ClosedRequired => 2u8,
                    };
                    if rank(req_i.minimum_status) < rank(req_j.minimum_status) {
                        return Some(MonotonicityViolation {
                            gap_id: req_j.gap_id.clone(),
                            high_permission: profiles[i].permission,
                            low_permission: profiles[j].permission,
                            high_required: req_i.minimum_status,
                            low_required: req_j.minimum_status,
                        });
                    }
                }
            }
        }
    }
    None
}

// ── Monotone profile set: correct structure ───────────────────────────────────

#[test]
fn monotone_profiles_pass_validation() {
    let profiles = vec![
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
                minimum_status: RequiredStatus::BoundedRequired,
            }],
        },
    ];
    // AAA requires g1 ClosedRequired; DIA requires g1 BoundedRequired.
    // AAA (stronger) >= DIA (weaker) requirement for g1: Closed >= Bounded → monotone.
    assert!(validate_profile_monotonicity(&profiles).is_none());
}

#[test]
fn monotone_equal_requirements_pass_validation() {
    let profiles = vec![
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
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        },
    ];
    // Equal requirements at different permission levels → monotone.
    assert!(validate_profile_monotonicity(&profiles).is_none());
}

// ── Non-monotone profile set: violation detected ──────────────────────────────

#[test]
fn non_monotone_profile_violation_detected() {
    let profiles = vec![
        Profile {
            permission: Permission::AAA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::BoundedRequired, // weaker than DIA!
            }],
        },
        Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired, // stricter at lower permission
            }],
        },
    ];
    let violation = validate_profile_monotonicity(&profiles);
    assert!(violation.is_some(), "non-monotone profile must be detected");
    let v = violation.unwrap();
    assert_eq!(v.gap_id, "g1");
    assert_eq!(v.high_permission, Permission::AAA);
    assert_eq!(v.low_permission, Permission::DIA);
}

// ── Single profile is trivially monotone ────────────────────────────────────

#[test]
fn single_profile_is_trivially_monotone() {
    let profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    }];
    assert!(validate_profile_monotonicity(&profiles).is_none());
}

// ── Empty profiles is trivially monotone ────────────────────────────────────

#[test]
fn empty_profiles_trivially_monotone() {
    assert!(validate_profile_monotonicity(&[]).is_none());
}

// ── Compiler behaviour with non-monotone profiles ────────────────────────────

#[test]
fn compiler_with_non_monotone_profiles_emits_lower_if_higher_fails() {
    // AAA requires g1 Bounded (weaker), DIA requires g1 Closed (stricter).
    // With g1 closed by token: descending search tries AAA first.
    // AAA requires BoundedRequired for g1; Closed satisfies Bounded → AAA satisfied.
    // So the compiler correctly emits AAA (the evidence satisfies even the looser
    // high-level requirement), even though the profile set is non-monotone.
    // This documents that a non-monotone profile can lead to unexpected results:
    // providing LESS evidence might sometimes give MORE permission if the
    // higher profile has weaker requirements.
    let claim_id = "nm-claim";
    let candidate_id = "nm-z";
    let context_id = "nm-ctx";
    let allowed_use = "nm-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "nm-fp".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "t")],
        profiles: vec![
            Profile {
                permission: Permission::AAA,
                required_gaps: vec![GapRequirement {
                    gap_id: "g1".into(),
                    minimum_status: RequiredStatus::BoundedRequired,
                }],
            },
            Profile {
                permission: Permission::DIA,
                required_gaps: vec![GapRequirement {
                    gap_id: "g1".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                }],
            },
        ],
        tokens: vec![ProofToken {
            token_id: "tok-nm".into(),
            token_type: "BOUND".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![],
            bounds_gaps: vec!["g1".into()], // only bounds, doesn't close
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

    let profiles_to_check = ctx.profiles.clone();
    let violation = validate_profile_monotonicity(&profiles_to_check);
    assert!(
        violation.is_some(),
        "this profile set is non-monotone and must be detected"
    );

    // The compiler emits AAA because AAA's BoundedRequired is satisfied by the
    // bounding token — demonstrating the risk of non-monotone profiles.
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::AAA,
        "non-monotone profile: AAA (BoundedRequired) is satisfied by bounding token \
         even though DIA (ClosedRequired) would NOT be — callers must validate G01"
    );
}

// ── Proptest: monotone profile set, adding evidence never lowers permission ───

fn make_ctx(gap_closed: bool, permission: Permission) -> ProofContext {
    let claim_id = "prop-mono-claim";
    let candidate_id = "prop-mono-z";
    let context_id = "prop-mono-ctx";
    let allowed_use = "prop-mono-use";

    let gap = if gap_closed {
        GapRecord::closed("g1", "t")
    } else {
        GapRecord::open("g1", "t")
    };

    let mut tokens = vec![];
    if gap_closed {
        let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);
        tokens.push(ProofToken {
            token_id: "tok-prop-mono".into(),
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
        });
    }

    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "prop-mono-fp".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![gap],
        profiles: vec![Profile {
            permission,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens,
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

proptest! {
    #[test]
    fn prop_monotone_adding_evidence_never_lowers(
        permission in prop_oneof![
            Just(Permission::DIA),
            Just(Permission::REV),
            Just(Permission::AEX),
            Just(Permission::ALR),
            Just(Permission::AAA),
        ],
    ) {
        let p_without = compile(make_ctx(false, permission)).unwrap().permission;
        let p_with = compile(make_ctx(true, permission)).unwrap().permission;
        prop_assert!(
            p_with >= p_without,
            "adding closed-gap evidence lowered permission: {} → {}",
            p_without, p_with
        );
    }

    #[test]
    fn prop_validate_monotonicity_on_all_single_profiles(
        p in prop_oneof![
            Just(Permission::DIA),
            Just(Permission::REV),
            Just(Permission::AEX),
            Just(Permission::ALR),
            Just(Permission::AAA),
        ],
    ) {
        let profiles = vec![Profile {
            permission: p,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }];
        prop_assert!(validate_profile_monotonicity(&profiles).is_none());
    }
}
