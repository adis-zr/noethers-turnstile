/// Property test: Derivation audit trail invariants.
///
/// The derivation record must:
///   1. Have phases in non-increasing permission order (each step ≤ previous).
///   2. Always have at least one step (membership check).
///   3. The final step's permission_after must equal the judgment permission.
///   4. Provenance hash must be non-empty.
///   5. Derivation is deterministic: same context → same derivation steps.
use chrono::Utc;
use proptest::prelude::*;
use noethers_turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn arb_permission() -> impl Strategy<Value = Permission> {
    prop_oneof![
        Just(Permission::OOC),
        Just(Permission::EXP),
        Just(Permission::REF),
        Just(Permission::UNS),
        Just(Permission::ETA),
        Just(Permission::ESC),
        Just(Permission::ROL),
        Just(Permission::DIA),
        Just(Permission::REV),
        Just(Permission::AEX),
        Just(Permission::ALR),
        Just(Permission::AAA),
    ]
}

fn build_ctx(ceiling: Permission, membership: Membership, with_token: bool) -> ProofContext {
    let claim_id = "c-audit";
    let candidate_id = "z-audit";
    let context_id = "ctx-audit";
    let allowed_use = "audit-use";

    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let gaps = vec![GapRecord::closed("g1", "t")];
    let profiles = vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "g1".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    }];

    let tokens = if with_token {
        vec![ProofToken {
            token_id: "tok-audit".into(),
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
        }]
    } else {
        vec![]
    };

    ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-audit".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps,
        profiles,
        tokens,
        expiry: Expiry::never(),
        authority_ceiling: ceiling,
        permission_ceiling: Permission::AAA,
        membership,
    }
}

// ── Structural audit invariants ───────────────────────────────────────────────

#[test]
fn derivation_has_at_least_one_step() {
    let ctx = build_ctx(Permission::AAA, Membership::InClass, true);
    let j = compile(ctx).unwrap();
    assert!(
        !j.derivation.steps.is_empty(),
        "derivation must have at least one step"
    );
}

#[test]
fn ooc_derivation_has_membership_step() {
    let ctx = build_ctx(Permission::AAA, Membership::OutOfClassExact, false);
    let j = compile(ctx).unwrap();
    let has_membership = j
        .derivation
        .steps
        .iter()
        .any(|s| s.phase == "membership_check");
    assert!(has_membership, "OOC path must have membership_check step");
}

#[test]
fn final_step_permission_equals_judgment_permission_inclass() {
    let ctx = build_ctx(Permission::DIA, Membership::InClass, true);
    let j = compile(ctx).unwrap();
    let last = j.derivation.steps.last().expect("must have last step");
    assert_eq!(
        last.permission_after, j.permission,
        "last derivation step must equal judgment permission"
    );
}

#[test]
fn derivation_provenance_hash_is_nonempty() {
    let ctx = build_ctx(Permission::AAA, Membership::InClass, true);
    let j = compile(ctx).unwrap();
    assert!(
        !j.derivation.provenance_hash.is_empty(),
        "derivation must carry non-empty provenance hash"
    );
}

#[test]
fn derivation_provenance_hash_matches_context() {
    let ctx = build_ctx(Permission::AAA, Membership::InClass, true);
    let expected_hash = ctx.provenance_hash();
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.derivation.provenance_hash, expected_hash,
        "derivation provenance hash must match context's own hash"
    );
}

#[test]
fn derivation_steps_are_non_increasing() {
    let ctx = build_ctx(Permission::DIA, Membership::InClass, true);
    let j = compile(ctx).unwrap();
    let perms: Vec<Permission> = j
        .derivation
        .steps
        .iter()
        .map(|s| s.permission_after)
        .collect();
    for w in perms.windows(2) {
        assert!(
            w[1] <= w[0],
            "derivation steps must be non-increasing: {} > {}",
            w[1],
            w[0]
        );
    }
}

#[test]
fn authority_ceiling_step_recorded_when_it_fires() {
    // Ceiling DIA < AAA (what profile would produce): ceiling step must appear.
    let ctx = build_ctx(Permission::ETA, Membership::InClass, true);
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::ETA);
    let has_ceiling = j
        .derivation
        .steps
        .iter()
        .any(|s| s.phase == "authority_ceiling");
    assert!(
        has_ceiling,
        "authority_ceiling step must appear when ceiling fires"
    );
}

#[test]
fn descending_search_step_always_present_for_inclass() {
    let ctx = build_ctx(Permission::AAA, Membership::InClass, true);
    let j = compile(ctx).unwrap();
    let has_search = j
        .derivation
        .steps
        .iter()
        .any(|s| s.phase == "descending_search");
    assert!(has_search, "in-class path must have descending_search step");
}

// ── Proptest: derivation invariants hold for all permission values ────────────

proptest! {
    #[test]
    fn prop_derivation_steps_non_increasing(
        ceiling in arb_permission(),
        with_token in prop::bool::ANY,
    ) {
        let ctx = build_ctx(ceiling, Membership::InClass, with_token);
        let j = compile(ctx).unwrap();
        let perms: Vec<Permission> = j.derivation.steps.iter().map(|s| s.permission_after).collect();
        for w in perms.windows(2) {
            prop_assert!(
                w[1] <= w[0],
                "derivation step decreased unexpectedly: {} > {}", w[1], w[0]
            );
        }
    }

    #[test]
    fn prop_final_step_permission_matches_judgment(
        ceiling in arb_permission(),
        with_token in prop::bool::ANY,
    ) {
        let ctx = build_ctx(ceiling, Membership::InClass, with_token);
        let j = compile(ctx).unwrap();
        if let Some(last) = j.derivation.steps.last() {
            prop_assert_eq!(last.permission_after, j.permission);
        }
    }

    #[test]
    fn prop_derivation_has_at_least_one_step_always(
        ceiling in arb_permission(),
        is_inclass in prop::bool::ANY,
    ) {
        let membership = if is_inclass { Membership::InClass } else { Membership::OutOfClassExact };
        let ctx = build_ctx(ceiling, membership, false);
        let j = compile(ctx).unwrap();
        prop_assert!(!j.derivation.steps.is_empty(), "must have at least one derivation step");
    }
}
