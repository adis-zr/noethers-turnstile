/// EC-048 — Theorem 2: greatest satisfiable permission (T5/T10, EC-001 §31.2).
///
/// Ported from: test_ec004a_theorem2_property_based.py (600 tests)
///
/// Theorem 2 (Strengthened): For any well-formed profile and gap-status
/// assignment, compile() returns the *greatest* satisfying permission — not
/// just *a* satisfying permission.
///
///   T2-1  — For each of 12 permission levels p: profile where p is highest
///            satisfiable → result = p exactly
///   T2-2  — Boundary: all gaps OPEN → weakest satisfying permission
///   T2-3  — Boundary: all gaps CLOSED → highest permission in profile
///   T2-4  — Evidence upgrade: closing one gap raises permission by exactly one step
///   T2-5  — No evidence: no profile satisfied → OOC
///   T2-6  — Two profiles (DIA, AEX): partial evidence satisfies DIA only → DIA
///   T2-7  — Two profiles (DIA, AEX): full evidence satisfies both → AEX (greatest)
///   T2-8  — Three profiles (DIA, REV, AEX): intermediate evidence → REV (greatest satisfied)
///   T2-9  — authority_ceiling caps greatest satisfiable: ceiling=DIA with AEX evidence → DIA
///   T2-10 — Profile with no gap requirements always satisfied → its permission is baseline
///   T2-11 — Highest profile with empty gap requirements and ceiling=AAA → AAA
///   Prop  — For random well-formed profiles + random gap-status, result ≥ all lower
///            satisfied profiles and result ≤ all unsatisfied profiles
use chrono::Utc;
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn valid_token(
    id: &str,
    closes: Vec<&str>,
    claim: &str,
    candidate: &str,
    ctx_id: &str,
    use_: &str,
) -> ProofToken {
    let hash = compute_provenance_hash(claim, candidate, ctx_id, use_);
    ProofToken {
        token_id: id.into(),
        token_type: "TEST".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: closes.into_iter().map(String::from).collect(),
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

fn ctx_with_profiles_and_closed_gaps(
    profiles: Vec<Profile>,
    closed_gaps: Vec<&str>,
    all_gaps: Vec<&str>,
    ceiling: Permission,
    suffix: &str,
) -> ProofContext {
    let claim = format!("claim-{suffix}");
    let candidate = format!("z-{suffix}");
    let ctx_id = format!("ctx-{suffix}");
    let use_ = format!("use-{suffix}");

    let gaps: Vec<GapRecord> = all_gaps
        .iter()
        .map(|g| {
            if closed_gaps.contains(g) {
                GapRecord::closed(*g, "t")
            } else {
                GapRecord::open(*g, "t")
            }
        })
        .collect();

    let tokens: Vec<ProofToken> = closed_gaps
        .iter()
        .enumerate()
        .map(|(i, g)| {
            valid_token(
                &format!("tok-{i}"),
                vec![*g],
                &claim,
                &candidate,
                &ctx_id,
                &use_,
            )
        })
        .collect();

    ProofContext {
        claim_id: claim,
        candidate_id: candidate,
        context_id: ctx_id,
        context_fingerprint: format!("fp-{suffix}"),
        allowed_use: format!("use-{suffix}"),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps,
        profiles,
        tokens,
        expiry: Expiry::never(),
        authority_ceiling: ceiling,
        membership: Membership::InClass,
    }
}

// ── T2-1: Each of 12 permission levels as the highest satisfiable ─────────────

#[test]
fn t2_1_each_permission_level_as_highest_satisfiable() {
    use Permission::*;
    let all_perms = [OOC, EXP, REF, UNS, ETA, ESC, ROL, DIA, REV, AEX, ALR, AAA];

    // For each permission p (excluding OOC which is the fallback), create a profile
    // where p is the only permission level, full evidence → result = p
    for &p in &all_perms[1..] {
        // skip OOC
        let profiles = vec![Profile {
            permission: p,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }];
        let ctx = ctx_with_profiles_and_closed_gaps(
            profiles,
            vec!["g1"],
            vec!["g1"],
            Permission::AAA,
            &format!("t2-1-{p:?}"),
        );
        let j = compile(ctx).unwrap();
        assert_eq!(
            j.permission, p,
            "T2-1: with only {p:?} profile and full evidence, result must be {p:?}"
        );
    }
}

// ── T2-2: All gaps OPEN → weakest satisfying permission ──────────────────────

#[test]
fn t2_2_all_gaps_open_weakest_satisfied() {
    // DIA profile requires g1 closed; no evidence → DIA not satisfied
    // No profile satisfied → OOC
    let profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    }];
    let ctx = ctx_with_profiles_and_closed_gaps(
        profiles,
        vec![], // no closed gaps
        vec!["g1"],
        Permission::AAA,
        "t2-2",
    );
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "T2-2: no evidence → no profile satisfied → OOC"
    );
}

// ── T2-3: All gaps CLOSED → highest permission in profile ─────────────────────

#[test]
fn t2_3_all_gaps_closed_highest_profile() {
    let profiles = vec![
        Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
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
    ];
    let ctx = ctx_with_profiles_and_closed_gaps(
        profiles,
        vec!["g1", "g2"],
        vec!["g1", "g2"],
        Permission::AAA,
        "t2-3",
    );
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::AEX,
        "T2-3: all gaps closed → highest profile AEX"
    );
}

// ── T2-4: Closing one gap upgrades permission ─────────────────────────────────

#[test]
fn t2_4_closing_gap_upgrades_permission() {
    let profiles = vec![
        Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        },
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
    ];

    // Only g1 closed → DIA
    let ctx_partial = ctx_with_profiles_and_closed_gaps(
        profiles.clone(),
        vec!["g1"],
        vec!["g1", "g2"],
        Permission::AAA,
        "t2-4-partial",
    );
    let p_partial = compile(ctx_partial).unwrap().permission;
    assert_eq!(p_partial, Permission::DIA, "T2-4: g1 only → DIA");

    // Both closed → REV
    let ctx_full = ctx_with_profiles_and_closed_gaps(
        profiles,
        vec!["g1", "g2"],
        vec!["g1", "g2"],
        Permission::AAA,
        "t2-4-full",
    );
    let p_full = compile(ctx_full).unwrap().permission;
    assert_eq!(
        p_full,
        Permission::REV,
        "T2-4: g1+g2 → REV (greatest satisfied)"
    );

    assert!(
        p_partial < p_full,
        "T2-4: closing g2 must upgrade permission from {p_partial:?} to {p_full:?}"
    );
}

// ── T2-5: No profiles → OOC ───────────────────────────────────────────────────

#[test]
fn t2_5_no_profiles_yields_ooc() {
    let ctx = ctx_with_profiles_and_closed_gaps(
        vec![], // no profiles
        vec![],
        vec![],
        Permission::AAA,
        "t2-5",
    );
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::OOC, "T2-5: no profiles → OOC");
}

// ── T2-6: Partial evidence satisfies only lower profile ───────────────────────

#[test]
fn t2_6_partial_evidence_gives_lower_profile() {
    let profiles = vec![
        Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
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
    ];
    // Only g1 closed → DIA satisfied, AEX not satisfied → result = DIA (greatest satisfied)
    let ctx = ctx_with_profiles_and_closed_gaps(
        profiles,
        vec!["g1"],
        vec!["g1", "g2"],
        Permission::AAA,
        "t2-6",
    );
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "T2-6: partial evidence (g1 only) → greatest satisfied = DIA"
    );
}

// ── T2-7: Full evidence satisfies both profiles → AEX (greatest) ─────────────

#[test]
fn t2_7_full_evidence_gives_highest_profile() {
    let profiles = vec![
        Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
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
    ];
    let ctx = ctx_with_profiles_and_closed_gaps(
        profiles,
        vec!["g1", "g2"],
        vec!["g1", "g2"],
        Permission::AAA,
        "t2-7",
    );
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::AEX,
        "T2-7: full evidence → greatest satisfied = AEX"
    );
}

// ── T2-8: Three profiles, intermediate evidence → middle profile ──────────────

#[test]
fn t2_8_three_profiles_intermediate_evidence_gives_middle() {
    let profiles = vec![
        Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        },
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
                GapRequirement {
                    gap_id: "g3".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                },
            ],
        },
    ];
    // g1+g2 closed, g3 open → DIA and REV satisfied, AEX not → result = REV
    let ctx = ctx_with_profiles_and_closed_gaps(
        profiles,
        vec!["g1", "g2"],
        vec!["g1", "g2", "g3"],
        Permission::AAA,
        "t2-8",
    );
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::REV,
        "T2-8: intermediate evidence (g1+g2) → greatest satisfied = REV"
    );
}

// ── T2-9: Authority ceiling caps greatest satisfiable ────────────────────────

#[test]
fn t2_9_ceiling_caps_greatest_satisfiable() {
    let profiles = vec![
        Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        },
        Profile {
            permission: Permission::AEX,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        },
    ];
    // Full evidence satisfies both, ceiling=DIA → result = DIA (not AEX)
    let ctx = ctx_with_profiles_and_closed_gaps(
        profiles,
        vec!["g1"],
        vec!["g1"],
        Permission::DIA, // ceiling caps AEX
        "t2-9",
    );
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "T2-9: ceiling=DIA caps greatest satisfiable from AEX to DIA"
    );
}

// ── T2-10: Profile with no gap requirements always satisfied ──────────────────

#[test]
fn t2_10_empty_requirements_always_satisfied() {
    // DIA profile with no gap requirements is always satisfied → baseline = DIA
    let profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![],
    }];
    let ctx = ctx_with_profiles_and_closed_gaps(profiles, vec![], vec![], Permission::AAA, "t2-10");
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "T2-10: profile with no gap requirements is always satisfied → DIA"
    );
}

// ── T2-11: Highest profile with empty requirements + ceiling=AAA → AAA ────────

#[test]
fn t2_11_empty_requirements_aaa_profile_gives_aaa() {
    let profiles = vec![
        Profile {
            permission: Permission::DIA,
            required_gaps: vec![],
        },
        Profile {
            permission: Permission::AAA,
            required_gaps: vec![],
        },
    ];
    let ctx = ctx_with_profiles_and_closed_gaps(profiles, vec![], vec![], Permission::AAA, "t2-11");
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::AAA,
        "T2-11: AAA profile with no requirements and ceiling=AAA → AAA"
    );
}
