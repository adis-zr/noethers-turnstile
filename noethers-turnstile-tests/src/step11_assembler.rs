/// Step 11 assembler tests: meet of multiple compiler stages.
///
/// Ported from:
///   ecds-core/tests/test_core.py  TestStep11
///   test_ec003f_step11_assembler.py
///
/// Properties proved:
///   T8  — Permission meet non-promotion: meet of all inputs ≤ each input
///   T9  — N-ary composition non-promotion
///   T11 — Diagnostic/action separation
///
/// The "Step 11" pattern tests that the final permission is the meet of
/// best_positive, authority_ceiling, structural_blockers, and expiry_blocker —
/// all four of which are conservative (can only lower, never raise).
use chrono::Utc;
use noethers_noethers_turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

const ALL: [Permission; 12] = [
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

fn ctx_for_permission(target_permission: Permission) -> ProofContext {
    let claim_id = "c";
    let candidate_id = "z";
    let context_id = "ctx";
    let allowed_use = "use";
    let gap_id = "g1";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed(gap_id, "t")],
        profiles: vec![Profile {
            permission: target_permission,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok".into(),
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
        }],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── T8/T9: Final permission is meet of all contributing inputs ────────────────

#[test]
fn final_permission_equals_profile_when_no_blockers() {
    for p in ALL {
        if p == Permission::OOC {
            continue;
        } // OOC = no profile
        let ctx = ctx_for_permission(p);
        let j = compile(ctx).unwrap();
        assert_eq!(j.permission, p, "expected {p}, got {}", j.permission);
    }
}

#[test]
fn authority_ceiling_meet_all_pairs() {
    // For each (profile_p, ceiling_p): result = meet(profile_p, ceiling_p)
    for profile_p in ALL {
        if profile_p == Permission::OOC {
            continue;
        }
        for ceiling_p in ALL {
            let mut ctx = ctx_for_permission(profile_p);
            ctx.authority_ceiling = ceiling_p;
            let j = compile(ctx).unwrap();
            let expected = profile_p.meet(ceiling_p);
            assert_eq!(
                j.permission, expected,
                "profile={profile_p} ceiling={ceiling_p}: expected meet={expected}, got {}",
                j.permission
            );
        }
    }
}

#[test]
fn disallowed_uses_ceiling_dangerous_combinations() {
    // From EC-003F: "dangerous combinations" — high evidence + disallowed use
    let dangerous_pairs = [
        (Permission::AAA, Permission::AAA), // AAA profile + disallowed → ROL
        (Permission::ALR, Permission::AAA),
        (Permission::AEX, Permission::AAA),
        (Permission::REV, Permission::AAA),
    ];

    for (profile_p, ceiling_p) in dangerous_pairs {
        let mut ctx = ctx_for_permission(profile_p);
        ctx.authority_ceiling = ceiling_p;
        ctx.disallowed_uses = vec!["production-write".into()];

        let j = compile(ctx).unwrap();
        // disallowed_uses cap at ROL; then meet with ceiling
        let expected = profile_p.meet(ceiling_p).meet(Permission::ROL);
        assert_eq!(
            j.permission, expected,
            "dangerous: profile={profile_p} ceiling={ceiling_p}: expected {expected}, got {}",
            j.permission
        );
    }
}

#[test]
fn safe_combinations_no_disallowed_use_effect() {
    // Permissions at or below ROL are not affected by disallowed_uses cap
    let safe_perms = [
        Permission::OOC,
        Permission::EXP,
        Permission::REF,
        Permission::UNS,
        Permission::ETA,
        Permission::ESC,
        Permission::ROL,
    ];

    for p in safe_perms {
        if p == Permission::OOC {
            continue;
        }
        let mut ctx = ctx_for_permission(p);
        ctx.disallowed_uses = vec!["something".into()];

        let j = compile(ctx).unwrap();
        // p ≤ ROL, so disallowed_uses cap at ROL doesn't lower it further
        assert_eq!(
            j.permission, p,
            "safe permission {p} should not be affected by disallowed_uses"
        );
    }
}

// ── T11: Membership is always the first gate ──────────────────────────────────

#[test]
fn membership_gate_runs_before_evidence() {
    // Even with a fully satisfied profile, OOC membership → OOC result
    for p in ALL {
        if p == Permission::OOC {
            continue;
        }
        let mut ctx = ctx_for_permission(p);
        ctx.membership = Membership::OutOfClassExact;

        let j = compile(ctx).unwrap();
        assert_eq!(
            j.permission,
            Permission::OOC,
            "OOC membership must produce OOC regardless of profile {p}"
        );
    }
}

// ── Derivation structure: phases are non-increasing ───────────────────────────

#[test]
fn derivation_phases_are_non_increasing_all_permissions() {
    for p in ALL {
        if p == Permission::OOC {
            continue;
        }
        let ctx = ctx_for_permission(p);
        let j = compile(ctx).unwrap();

        let mut prev = Permission::AAA;
        for step in &j.derivation.steps {
            assert!(
                step.permission_after <= prev,
                "permission raised in step '{}': {prev} → {}",
                step.phase,
                step.permission_after
            );
            prev = step.permission_after;
        }
        // Final step matches emitted permission
        if let Some(last) = j.derivation.steps.last() {
            assert_eq!(last.permission_after, j.permission);
        }
    }
}

// ── Meet is the only combiner — no alternative outcomes ──────────────────────

#[test]
fn compile_result_is_always_meet_of_all_constraints() {
    // Construct contexts with all possible combinations of ceiling + disallowed_uses
    // and verify: result = meet(profile, ceiling, disallowed_cap)
    let profile_perms = [Permission::AAA, Permission::DIA, Permission::REV];
    let ceiling_perms = [Permission::AAA, Permission::DIA, Permission::ETA];

    for &profile_p in &profile_perms {
        for &ceiling_p in &ceiling_perms {
            for &has_disallowed in &[false, true] {
                let mut ctx = ctx_for_permission(profile_p);
                ctx.authority_ceiling = ceiling_p;
                if has_disallowed {
                    ctx.disallowed_uses = vec!["x".into()];
                }

                let j = compile(ctx).unwrap();

                let mut expected = profile_p.meet(ceiling_p);
                if has_disallowed {
                    expected = expected.meet(Permission::ROL);
                }

                assert_eq!(
                    j.permission, expected,
                    "profile={profile_p} ceiling={ceiling_p} disallowed={has_disallowed}: expected {expected}, got {}",
                    j.permission
                );
            }
        }
    }
}
