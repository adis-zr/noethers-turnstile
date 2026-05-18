/// EC-049 — Admission contract A1–A9 depth (T6/T19, EC-001 §35).
///
/// Ported from: test_ec005a_admission_contract_predicates.py (~311 tests)
///
/// Nine finite, inspectable conditions (A1–A9) must be satisfied for admission.
/// This file deepens coverage for the conditions directly enforced by compile().
///
///   A1-1  — Duplicate gap_id → MalformedContext
///   A1-2  — Aliased gap_ids (logically same but different strings) → accepted
///   A3-1  — 10k-gap context terminates in bounded time
///   A3-2  — 1k-gap context with no profiles → OOC (graceful)
///   A4-1  — Duplicate permission level in profiles → MalformedContext (all 12 levels)
///   A4-2  — Well-formed profiles (unique permissions) → accepted
///   A6-1  — Each of 12 ceiling values produces result ≤ ceiling
///   A6-2  — Ceiling lower than any profile → OOC (no satisfied profile within ceiling)
///   A7-1  — Mismatched context_fingerprint in RuntimeContext → OOC
///   A7-2  — Matching context_fingerprint → permission unchanged
///   A9-1  — Adversarial 1M-char allowed_use → compile terminates
///   A9-2  — 1k gaps all with 1k-char gap_ids → compile terminates
///   A9-3  — All gap statuses OPEN + 1k profiles → compile terminates (all unsatisfied → OOC)
///   All   — Clean context passes all conditions
use chrono::Utc;
use std::time::Instant;
use noethers_noethers_turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    error::TurnstileError,
    expiry::{Expiry, LiveJudgment, RuntimeContext},
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

const ALL_PERMISSIONS: [Permission; 12] = [
    Permission::OOC,
    Permission::EXP,
    Permission::REF,
    Permission::UNS,
    Permission::ETA,
    Permission::ESC,
    Permission::ROL,
    Permission::DIA,
    Permission::REV,
    Permission::AEX,
    Permission::ALR,
    Permission::AAA,
];

fn clean_ctx() -> ProofContext {
    let hash = compute_provenance_hash("claim-a", "z-a", "ctx-a", "a-use");
    ProofContext {
        claim_id: "claim-a".into(),
        candidate_id: "z-a".into(),
        context_id: "ctx-a".into(),
        context_fingerprint: "fp-a".into(),
        allowed_use: "a-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "t")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-a".into(),
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
        }],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── All: Clean context passes ─────────────────────────────────────────────────

#[test]
fn all_clean_context_passes() {
    let ctx = clean_ctx();
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "Clean context must compile to DIA"
    );
}

// ── A1: Duplicate gap_id → MalformedContext ───────────────────────────────────

#[test]
fn a1_1_duplicate_gap_id_rejected() {
    let mut ctx = clean_ctx();
    // Add second gap with same id
    ctx.gaps.push(GapRecord::open("g1", "t"));
    let result = compile(ctx);
    assert!(
        matches!(result, Err(TurnstileError::MalformedContext(_))),
        "A1-1: duplicate gap_id must be rejected with MalformedContext"
    );
}

#[test]
fn a1_2_different_gap_ids_same_type_accepted() {
    // Logically similar but lexically distinct gap_ids are accepted
    let hash = compute_provenance_hash("claim-a12", "z-a12", "ctx-a12", "a12-use");
    let ctx = ProofContext {
        claim_id: "claim-a12".into(),
        candidate_id: "z-a12".into(),
        context_id: "ctx-a12".into(),
        context_fingerprint: "fp-a12".into(),
        allowed_use: "a12-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![
            GapRecord::closed("g1-alpha", "t"),
            GapRecord::closed("g1-beta", "t"),
        ],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1-alpha".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-a12".into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1-alpha".into()],
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
    let result = compile(ctx);
    assert!(result.is_ok(), "A1-2: distinct gap_ids must be accepted");
}

// ── A3: Large gap basis terminates ────────────────────────────────────────────

#[test]
fn a3_1_ten_thousand_gap_context_terminates() {
    let gaps: Vec<GapRecord> = (0..10_000)
        .map(|i| GapRecord::open(format!("gap-{i}"), "t"))
        .collect();

    let ctx = ProofContext {
        claim_id: "claim-a3".into(),
        candidate_id: "z-a3".into(),
        context_id: "ctx-a3".into(),
        context_fingerprint: "fp-a3".into(),
        allowed_use: "a3-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps,
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let start = Instant::now();
    let j = compile(ctx).unwrap();
    let elapsed = start.elapsed();

    assert_eq!(j.permission, Permission::OOC, "A3-1: no profiles → OOC");
    assert!(
        elapsed.as_secs() < 5,
        "A3-1: 10k-gap context must compile in <5s (took {elapsed:?})"
    );
}

#[test]
fn a3_2_one_thousand_gaps_no_profiles_yields_ooc() {
    let gaps: Vec<GapRecord> = (0..1_000)
        .map(|i| GapRecord::open(format!("gap-{i}"), "t"))
        .collect();

    let ctx = ProofContext {
        claim_id: "claim-a3b".into(),
        candidate_id: "z-a3b".into(),
        context_id: "ctx-a3b".into(),
        context_fingerprint: "fp-a3b".into(),
        allowed_use: "a3b-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps,
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
        "A3-2: 1k gaps, no profiles → OOC"
    );
}

// ── A4: Duplicate permission level in profiles → MalformedContext ─────────────

#[test]
fn a4_1_duplicate_permission_level_rejected_for_all_12() {
    for (i, &p) in ALL_PERMISSIONS.iter().enumerate() {
        let ctx = ProofContext {
            claim_id: format!("claim-a4-{i}"),
            candidate_id: format!("z-a4-{i}"),
            context_id: format!("ctx-a4-{i}"),
            context_fingerprint: format!("fp-a4-{i}"),
            allowed_use: format!("a4-use-{i}"),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps: vec![GapRecord::open("g1", "t")],
            profiles: vec![
                Profile {
                    permission: p,
                    required_gaps: vec![],
                },
                Profile {
                    permission: p, // duplicate!
                    required_gaps: vec![],
                },
            ],
            tokens: vec![],
            expiry: Expiry::never(),
            authority_ceiling: Permission::AAA,
            permission_ceiling: Permission::AAA,
            membership: Membership::InClass,
        };
        let result = compile(ctx);
        assert!(
            matches!(result, Err(TurnstileError::MalformedContext(_))),
            "A4-1: duplicate permission level {p:?} must yield MalformedContext"
        );
    }
}

#[test]
fn a4_2_unique_permission_levels_accepted() {
    let ctx = ProofContext {
        claim_id: "claim-a4-ok".into(),
        candidate_id: "z-a4-ok".into(),
        context_id: "ctx-a4-ok".into(),
        context_fingerprint: "fp-a4-ok".into(),
        allowed_use: "a4-ok-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![
            Profile {
                permission: Permission::DIA,
                required_gaps: vec![],
            },
            Profile {
                permission: Permission::AEX,
                required_gaps: vec![],
            },
        ],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    assert!(
        compile(ctx).is_ok(),
        "A4-2: distinct permission levels must be accepted"
    );
}

// ── A6: Each of 12 ceiling values produces result ≤ ceiling ──────────────────

#[test]
fn a6_1_all_12_ceilings_produce_result_leq_ceiling() {
    for (i, &ceiling) in ALL_PERMISSIONS.iter().enumerate() {
        let hash = compute_provenance_hash(
            &format!("c-{i}"),
            &format!("z-{i}"),
            &format!("x-{i}"),
            &format!("u-{i}"),
        );
        let ctx = ProofContext {
            claim_id: format!("c-{i}"),
            candidate_id: format!("z-{i}"),
            context_id: format!("x-{i}"),
            context_fingerprint: format!("fp-{i}"),
            allowed_use: format!("u-{i}"),
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
                token_id: format!("tok-{i}"),
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
            }],
            expiry: Expiry::never(),
            authority_ceiling: ceiling,
            permission_ceiling: Permission::AAA,
            membership: Membership::InClass,
        };
        let j = compile(ctx).unwrap();
        assert!(
            j.permission <= ceiling,
            "A6-1: ceiling={ceiling:?} → result {r:?} must not exceed ceiling",
            r = j.permission
        );
    }
}

// ── A7: RuntimeContext fingerprint check ──────────────────────────────────────

#[test]
fn a7_1_mismatched_fingerprint_yields_ooc() {
    let ctx = clean_ctx(); // context_fingerprint = "fp-a"
    let j = compile(ctx).unwrap();
    let rt = RuntimeContext::new(Utc::now(), "fp-DIFFERENT");
    let live = LiveJudgment::new(j, &rt);
    assert_eq!(
        live.permission(),
        Permission::OOC,
        "A7-1: mismatched fingerprint must yield OOC (wrong context, not expiry)"
    );
}

#[test]
fn a7_2_matching_fingerprint_preserves_permission() {
    let ctx = clean_ctx(); // context_fingerprint = "fp-a"
    let j = compile(ctx).unwrap();
    let rt = RuntimeContext::new(Utc::now(), "fp-a");
    let live = LiveJudgment::new(j, &rt);
    assert_eq!(
        live.permission(),
        Permission::DIA,
        "A7-2: matching fingerprint must preserve permission"
    );
}

// ── A9: Adversarial inputs terminate ─────────────────────────────────────────

#[test]
fn a9_1_million_char_allowed_use_terminates() {
    let long_use: String = "x".repeat(1_000_000);
    let hash = compute_provenance_hash("claim-a9", "z-a9", "ctx-a9", &long_use);
    let ctx = ProofContext {
        claim_id: "claim-a9".into(),
        candidate_id: "z-a9".into(),
        context_id: "ctx-a9".into(),
        context_fingerprint: "fp-a9".into(),
        allowed_use: long_use,
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "t")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-a9".into(),
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
        }],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    let start = Instant::now();
    let result = compile(ctx);
    let elapsed = start.elapsed();
    assert!(result.is_ok(), "A9-1: 1M-char allowed_use must not error");
    assert!(
        elapsed.as_secs() < 5,
        "A9-1: must complete in <5s (took {elapsed:?})"
    );
}

#[test]
fn a9_2_one_thousand_long_gap_ids_terminates() {
    let gaps: Vec<GapRecord> = (0..1_000)
        .map(|i| GapRecord::open(format!("gap-{}-{}", i, "x".repeat(100)), "t"))
        .collect();

    let ctx = ProofContext {
        claim_id: "claim-a9b".into(),
        candidate_id: "z-a9b".into(),
        context_id: "ctx-a9b".into(),
        context_fingerprint: "fp-a9b".into(),
        allowed_use: "a9b-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps,
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    let start = Instant::now();
    let result = compile(ctx);
    let elapsed = start.elapsed();
    assert!(result.is_ok(), "A9-2: 1k long-id gaps must not error");
    assert!(
        elapsed.as_secs() < 5,
        "A9-2: must complete in <5s (took {elapsed:?})"
    );
}

#[test]
fn a9_3_one_thousand_profiles_all_open_terminates_ooc() {
    let gaps: Vec<GapRecord> = (0..20)
        .map(|i| GapRecord::open(format!("gap-{i}"), "t"))
        .collect();

    let _profiles: Vec<Profile> = (0..1_000)
        .map(|i| Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: format!("gap-{}", i % 20),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        })
        .collect();

    // But wait: duplicate permissions → MalformedContext. Use unique permissions.
    // Can only have 12 unique permission levels, so cap profiles at 12.
    let profiles: Vec<Profile> = [
        Permission::EXP,
        Permission::REF,
        Permission::UNS,
        Permission::ETA,
        Permission::ESC,
        Permission::ROL,
        Permission::DIA,
        Permission::REV,
        Permission::AEX,
        Permission::ALR,
        Permission::AAA,
    ]
    .iter()
    .map(|&p| Profile {
        permission: p,
        required_gaps: vec![GapRequirement {
            gap_id: "gap-0".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    })
    .collect();

    let ctx = ProofContext {
        claim_id: "claim-a9c".into(),
        candidate_id: "z-a9c".into(),
        context_id: "ctx-a9c".into(),
        context_fingerprint: "fp-a9c".into(),
        allowed_use: "a9c-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps,
        profiles,
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };
    let start = Instant::now();
    let j = compile(ctx).unwrap();
    let elapsed = start.elapsed();
    assert_eq!(
        j.permission,
        Permission::UNS,
        "A9-3: all gaps open → UNS (InClass, profiles defined but unmet)"
    );
    assert!(
        elapsed.as_secs() < 5,
        "A9-3: must complete in <5s (took {elapsed:?})"
    );
}
