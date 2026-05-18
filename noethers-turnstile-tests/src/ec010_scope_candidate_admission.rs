use chrono::Utc;
/// EC-010 — Scope candidate admission (rule [ADMISSIBLE]).
///
/// EC-001 §24 rule [ADMISSIBLE]:
///   A judgment is admissible only if the candidate z is within the declared scope.
///   Formally: z ∈ Γ.scope.allowed_candidates (when scope is constrained).
///
/// The compiler currently does NOT enforce this rule — it compiles regardless of
/// whether candidate_id is in scope.allowed_candidates.  This test suite:
///
///   1. Documents the current behaviour (compiles even when out of scope).
///   2. Provides a `validate_candidate_in_scope` function callers MUST invoke.
///   3. Tests that function exhaustively.
///
/// This is an explicit compliance gap that downstream users must close by calling
/// the validator before acting on the judgment permission.
///
/// Tests:
///   - Empty scope → unconstrained → any candidate admitted
///   - Scope with candidate_id present → admitted
///   - Scope with candidate_id absent → rejected by validator
///   - Scope with single entry matching exactly → admitted
///   - Scope with multiple entries, candidate not in list → rejected
///   - candidate_id case-sensitive check
///   - Proptest: candidate always admitted when scope is empty
///   - Proptest: candidate in list is always admitted
use proptest::prelude::*;
use noethers_noethers_turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

// ── Scope candidate validator ────────────────────────────────────────────────

/// Returns true if `candidate_id` is admitted by `scope`.
///
/// An empty `allowed_candidates` list means unconstrained (all candidates pass).
/// A non-empty list requires exact membership.
pub fn validate_candidate_in_scope(scope: &Scope, candidate_id: &str) -> bool {
    if scope.allowed_candidates.is_empty() {
        return true;
    }
    scope.allowed_candidates.iter().any(|c| c == candidate_id)
}

// ── Helpers ──────────────────────────────────────────────────────────────────

fn base_ctx(candidate_id: &str, scope: Scope) -> ProofContext {
    let claim_id = "scope-claim";
    let context_id = "scope-ctx";
    let allowed_use = "scope-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "scope-fp".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope,
        gaps: vec![GapRecord::closed("g1", "t")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "scope-tok".into(),
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

// ── validate_candidate_in_scope ───────────────────────────────────────────────

#[test]
fn empty_scope_admits_any_candidate() {
    let scope = Scope::default();
    assert!(validate_candidate_in_scope(&scope, "any-candidate"));
    assert!(validate_candidate_in_scope(&scope, "z-99"));
    assert!(validate_candidate_in_scope(&scope, ""));
}

#[test]
fn scope_with_candidate_admits_exact_match() {
    let scope = Scope {
        allowed_candidates: vec!["z-1".into(), "z-2".into()],
        ..Default::default()
    };
    assert!(validate_candidate_in_scope(&scope, "z-1"));
    assert!(validate_candidate_in_scope(&scope, "z-2"));
}

#[test]
fn scope_with_candidate_rejects_non_member() {
    let scope = Scope {
        allowed_candidates: vec!["z-1".into(), "z-2".into()],
        ..Default::default()
    };
    assert!(!validate_candidate_in_scope(&scope, "z-3"));
    assert!(!validate_candidate_in_scope(&scope, "z-0"));
    assert!(!validate_candidate_in_scope(&scope, ""));
}

#[test]
fn scope_candidate_check_is_case_sensitive() {
    let scope = Scope {
        allowed_candidates: vec!["Z-1".into()],
        ..Default::default()
    };
    assert!(validate_candidate_in_scope(&scope, "Z-1"));
    assert!(
        !validate_candidate_in_scope(&scope, "z-1"),
        "must be case-sensitive"
    );
    assert!(
        !validate_candidate_in_scope(&scope, "Z-1 "),
        "trailing space must not match"
    );
}

#[test]
fn scope_single_entry_exact_match() {
    let scope = Scope {
        allowed_candidates: vec!["only-z".into()],
        ..Default::default()
    };
    assert!(validate_candidate_in_scope(&scope, "only-z"));
    assert!(!validate_candidate_in_scope(&scope, "only-z-extra"));
    assert!(!validate_candidate_in_scope(&scope, "only-"));
}

// ── Compiler behaviour: does NOT enforce scope candidate admission ────────────

#[test]
fn compiler_does_not_enforce_scope_candidate_admission() {
    // This test DOCUMENTS that the compiler compiles even when candidate is
    // outside scope.allowed_candidates.  Callers MUST check via
    // validate_candidate_in_scope() before acting on the permission.
    let constrained_scope = Scope {
        allowed_candidates: vec!["z-allowed".into()],
        ..Default::default()
    };
    let ctx = base_ctx("z-NOT-in-scope", constrained_scope.clone());

    // Validator correctly rejects this.
    assert!(
        !validate_candidate_in_scope(&ctx.scope, &ctx.candidate_id),
        "validate_candidate_in_scope must reject out-of-scope candidate"
    );

    // But the compiler does not check this — it still compiles.
    let j = compile(ctx).unwrap();
    // The token provenance was computed for "z-NOT-in-scope" so it still matches.
    // This means the compiler returns a non-OOC permission for an out-of-scope
    // candidate — which is why callers MUST validate before acting.
    //
    // We assert the compiler's current behaviour explicitly, so any future change
    // that adds enforcement will be caught here and the test can be updated.
    assert_eq!(
        j.permission,
        Permission::DIA,
        "DOCUMENTED BEHAVIOUR: compiler emits DIA for out-of-scope candidate; \
         callers must call validate_candidate_in_scope() before acting on judgment"
    );
}

#[test]
fn compiler_in_scope_candidate_compiles_normally() {
    let constrained_scope = Scope {
        allowed_candidates: vec!["z-allowed".into()],
        ..Default::default()
    };
    let ctx = base_ctx("z-allowed", constrained_scope.clone());

    assert!(validate_candidate_in_scope(&ctx.scope, &ctx.candidate_id));
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::DIA);
}

// ── Proptest ─────────────────────────────────────────────────────────────────

proptest! {
    #[test]
    fn prop_empty_scope_always_admits(candidate in "[a-z0-9]{1,20}") {
        let scope = Scope::default();
        prop_assert!(validate_candidate_in_scope(&scope, &candidate));
    }

    #[test]
    fn prop_candidate_in_list_always_admitted(
        prefix in "[a-z]{1,5}",
        n in 1usize..=5usize,
    ) {
        let candidates: Vec<String> = (0..n).map(|i| format!("{prefix}-{i}")).collect();
        let scope = Scope {
            allowed_candidates: candidates.clone(),
            ..Default::default()
        };
        for c in &candidates {
            prop_assert!(
                validate_candidate_in_scope(&scope, c),
                "candidate {c:?} must be admitted when it is in the list"
            );
        }
    }

    #[test]
    fn prop_candidate_not_in_list_always_rejected(
        listed in "[a-z]{3}",
        unlisted in "[A-Z]{3}",
    ) {
        // Use uppercase for unlisted so it's always different from lowercase listed.
        let scope = Scope {
            allowed_candidates: vec![listed.clone()],
            ..Default::default()
        };
        // Only reject if they are actually different (guard against proptest edge cases).
        if listed != unlisted {
            prop_assert!(
                !validate_candidate_in_scope(&scope, &unlisted),
                "unlisted candidate {unlisted:?} must be rejected"
            );
        }
    }
}
