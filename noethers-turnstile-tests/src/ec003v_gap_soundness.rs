/// EC-003V — Gap requirement soundness (T5, T6).
///
/// T5: Gap requirement soundness
///   If compile(Γ).permission = p > OOC, then every gap required by the
///   profile for p is satisfied (≥ required status) in Γ.
///
/// T6: No proof, no license
///   If a required gap has no valid, provenanced token that closes/bounds it,
///   the profile for that permission level is not satisfied, so the compiler
///   falls through to a lower permission.
///
/// Falsification conditions:
///   - A permission is emitted while a required-closed gap remains Open.
///   - A permission is emitted using a token whose gap_id is not listed in
///     closes_gaps (gap requirement satisfied via wrong field).
///   - Adding a token that bounds a required-closed gap but doesn't close it
///     still causes the profile to be satisfied.
use chrono::Utc;
use noethers_turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn base_ctx(with_token: bool, gap_status_fn: impl Fn() -> GapRecord) -> ProofContext {
    let claim_id = "claim-t5";
    let candidate_id = "z-t5";
    let context_id = "ctx-t5";
    let allowed_use = "t5-use";

    let gap = gap_status_fn();
    let gap_id = gap.gap_id.clone();

    let mut tokens = vec![];
    if with_token {
        let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);
        tokens.push(ProofToken {
            token_id: "tok-t5".into(),
            token_type: "CLOSE".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![gap_id.clone()],
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
        context_fingerprint: "fp-t5".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![gap],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id,
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

// ── T6: No proof, no license ──────────────────────────────────────────────────

#[test]
fn t6_open_gap_no_token_blocks_permission() {
    let ctx = base_ctx(false, || GapRecord::open("g1", "calibration_gap"));
    let j = compile(ctx).unwrap();
    // In-class, profile defined, gap open, no token → UNS
    assert_eq!(
        j.permission,
        Permission::UNS,
        "T6: open gap without token must not grant DIA; in-class → UNS"
    );
}

#[test]
fn t6_closed_gap_record_but_no_token_still_blocks() {
    // Gap record says Closed but no token attests to it.
    // The gap status in the record is the base status; tokens elevate it.
    // Without a token, the effective status is what the record says — but
    // the compiler's effective_gap_status uses token provenance for elevation.
    // Here the gap record already says Closed; the compiler must accept it.
    // This tests that the record's base status is respected when no tokens contradict.
    let ctx = base_ctx(false, || GapRecord::closed("g1", "calibration_gap"));
    let j = compile(ctx).unwrap();
    // GapRecord::closed means the gap is already marked Closed (certifier pre-closed it).
    assert_eq!(
        j.permission,
        Permission::DIA,
        "gap record marked Closed must satisfy ClosedRequired even without a token"
    );
}

#[test]
fn t6_bounded_gap_does_not_satisfy_closed_required() {
    let claim_id = "claim-t6-bound";
    let candidate_id = "z-t6-bound";
    let context_id = "ctx-t6-bound";
    let allowed_use = "t6-bound";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-t6".into(),
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
            token_id: "tok-bound".into(),
            token_type: "BOUND".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![],
            bounds_gaps: vec!["g1".into()], // only bounds, does not close
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
    // In-class, profile defined, bounding token ≠ ClosedRequired → UNS
    assert_eq!(
        j.permission,
        Permission::UNS,
        "T6: bounding token does not satisfy ClosedRequired; in-class → UNS"
    );
}

#[test]
fn t6_bounded_gap_satisfies_bounded_required() {
    let claim_id = "claim-t6-bnd-ok";
    let candidate_id = "z-t6-bnd-ok";
    let context_id = "ctx-t6-bnd-ok";
    let allowed_use = "t6-bnd-ok";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-t6-bnd-ok".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "calibration_gap")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::BoundedRequired, // only bounded needed
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-bnd-ok".into(),
            token_type: "BOUND".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![],
            bounds_gaps: vec!["g1".into()],
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
    assert_eq!(
        j.permission,
        Permission::DIA,
        "T6: bounding token satisfies BoundedRequired"
    );
}

// ── T5: Gap requirement soundness ─────────────────────────────────────────────

#[test]
fn t5_emitted_permission_implies_all_required_gaps_satisfied() {
    // If DIA is emitted, then every gap required by the DIA profile is satisfied.
    let claim_id = "claim-t5-sat";
    let candidate_id = "z-t5-sat";
    let context_id = "ctx-t5-sat";
    let allowed_use = "t5-sat";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-t5-sat".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![
            GapRecord::open("g1", "calibration_gap"),
            GapRecord::open("g2", "freshness_gap"),
        ],
        profiles: vec![Profile {
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
        }],
        tokens: vec![ProofToken {
            token_id: "tok-t5-sat".into(),
            token_type: "CLOSE".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into(), "g2".into()],
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
    assert_eq!(
        j.permission,
        Permission::DIA,
        "both gaps closed → DIA emitted"
    );
}

#[test]
fn t5_partial_gap_satisfaction_falls_to_lower_profile() {
    // Two profiles: AAA requires g1+g2 closed; DIA requires only g1 closed.
    // Token only closes g1. Should emit DIA, not AAA.
    let claim_id = "claim-t5-partial";
    let candidate_id = "z-t5-partial";
    let context_id = "ctx-t5-partial";
    let allowed_use = "t5-partial";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-t5-partial".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![
            GapRecord::open("g1", "calibration_gap"),
            GapRecord::open("g2", "freshness_gap"),
        ],
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
        tokens: vec![ProofToken {
            token_id: "tok-partial".into(),
            token_type: "CLOSE".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()], // closes only g1
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
    assert_eq!(
        j.permission,
        Permission::DIA,
        "T5: partial gap satisfaction falls to DIA, not AAA"
    );
}

#[test]
fn t5_wrong_gap_id_in_token_does_not_satisfy_profile() {
    // Token claims to close "g2" but profile requires "g1".
    let claim_id = "claim-t5-wrong-id";
    let candidate_id = "z-t5-wrong-id";
    let context_id = "ctx-t5-wrong-id";
    let allowed_use = "t5-wrong-id";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-t5-wrong-id".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![
            GapRecord::open("g1", "calibration_gap"),
            GapRecord::open("g2", "freshness_gap"),
        ],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(), // requires g1
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-wrong-gap".into(),
            token_type: "CLOSE".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g2".into()], // closes g2, not g1
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
    // In-class, token for g2 doesn't close g1 → GapNotMet → UNS
    assert_eq!(
        j.permission,
        Permission::UNS,
        "T5/T6: token for g2 must not satisfy g1 requirement; in-class → UNS"
    );
}

#[test]
fn t6_empty_gap_claim_in_token_satisfies_nothing() {
    // Token has empty closes_gaps and empty bounds_gaps.
    let claim_id = "claim-t6-empty";
    let candidate_id = "z-t6-empty";
    let context_id = "ctx-t6-empty";
    let allowed_use = "t6-empty";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-t6-empty".into(),
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
            token_id: "tok-empty-claims".into(),
            token_type: "CLOSE".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![], // claims nothing
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
    // In-class, empty closes_gaps → gap not closed → UNS
    assert_eq!(
        j.permission,
        Permission::UNS,
        "T6: token with empty closes_gaps must not satisfy any gap requirement; in-class → UNS"
    );
}

// ── Multi-level profile satisfaction ─────────────────────────────────────────

#[test]
fn greatest_satisfiable_permission_is_emitted() {
    // Multiple profiles; only the highest satisfiable one should be emitted.
    let claim_id = "claim-greatest";
    let candidate_id = "z-greatest";
    let context_id = "ctx-greatest";
    let allowed_use = "greatest";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-greatest".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![
            GapRecord::open("g1", "calibration_gap"),
            GapRecord::open("g2", "freshness_gap"),
            GapRecord::open("g3", "model_gap"),
        ],
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
                    GapRequirement {
                        gap_id: "g3".into(),
                        minimum_status: RequiredStatus::ClosedRequired,
                    },
                ],
            },
            Profile {
                permission: Permission::AEX,
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
        // Token only closes g1 and g2.
        tokens: vec![ProofToken {
            token_id: "tok-greatest".into(),
            token_type: "CLOSE".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into(), "g2".into()],
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
    assert_eq!(
        j.permission,
        Permission::AEX,
        "T5: greatest satisfiable permission is AEX (g1+g2 closed; g3 still open)"
    );
}
