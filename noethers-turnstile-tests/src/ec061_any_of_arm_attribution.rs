//! EC-061 — `GapRequirement::AnyOf` and derivation arm attribution.
//!
//! Phase 1b of the native-chains spec. Verifies:
//!   - A disjunctive requirement is satisfied iff at least one arm is satisfied.
//!   - The compiler records which arm fired in the `DerivationStep`.
//!   - An empty `any_of` arms list is rejected at validation time.
//!   - Nested `any_of` works and records a structured arm label.

use chrono::Utc;
use noethers_turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    error::TurnstileError,
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn ctx_with_two_gaps_and_any_of_profile(
    g1_closed: bool,
    g2_closed: bool,
    suffix: &str,
) -> ProofContext {
    let claim_id = format!("c-{suffix}");
    let candidate_id = format!("z-{suffix}");
    let context_id = format!("ctx-{suffix}");
    let allowed_use = "use".to_string();
    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, &allowed_use);
    let mut tokens = vec![];
    if g1_closed {
        tokens.push(ProofToken {
            token_id: "tok-g1".into(),
            token_type: "T".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec![],
            provenance_hash: hash.clone(),
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
            negative_control_id: None,
        });
    }
    if g2_closed {
        tokens.push(ProofToken {
            token_id: "tok-g2".into(),
            token_type: "T".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g2".into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
            negative_control_id: None,
        });
    }

    ProofContext {
        claim_id,
        candidate_id,
        context_id,
        context_fingerprint: "fp".into(),
        allowed_use,
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![
            if g1_closed {
                GapRecord::closed("g1", "t")
            } else {
                GapRecord::open("g1", "t")
            },
            if g2_closed {
                GapRecord::closed("g2", "t")
            } else {
                GapRecord::open("g2", "t")
            },
        ],
        profiles: vec![Profile {
            permission: Permission::AEX(),
            required_gaps: vec![GapRequirement::any_of(vec![
                GapRequirement::single("g1", RequiredStatus::ClosedRequired),
                GapRequirement::single("g2", RequiredStatus::ClosedRequired),
            ])],
        }],
        tokens,
        expiry: Expiry::never(),
        authority_ceiling: None,
        permission_ceiling: None,
        membership: Membership::InClass,
        expected_chain_hash: None,
    }
}

#[test]
fn any_of_neither_arm_satisfies_then_unsatisfied() {
    let ctx = ctx_with_two_gaps_and_any_of_profile(false, false, "neither");
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::UNS());
}

#[test]
fn any_of_first_arm_satisfies_records_g1_in_derivation() {
    let ctx = ctx_with_two_gaps_and_any_of_profile(true, false, "first");
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::AEX());
    let step = j
        .derivation
        .steps
        .iter()
        .find(|s| s.phase == "descending_search")
        .expect("descending_search step must exist");
    assert!(
        step.note.contains("any_of arm(s): g1"),
        "expected arm attribution to g1, got note: {:?}",
        step.note
    );
    assert!(
        step.token_ids.iter().any(|t| t == "any_of_arm:g1"),
        "token_ids must include any_of_arm:g1; got {:?}",
        step.token_ids
    );
}

#[test]
fn any_of_second_arm_satisfies_records_g2_in_derivation() {
    let ctx = ctx_with_two_gaps_and_any_of_profile(false, true, "second");
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::AEX());
    let step = j
        .derivation
        .steps
        .iter()
        .find(|s| s.phase == "descending_search")
        .expect("descending_search step must exist");
    assert!(
        step.note.contains("any_of arm(s): g2"),
        "expected arm attribution to g2, got note: {:?}",
        step.note
    );
    assert!(step.token_ids.iter().any(|t| t == "any_of_arm:g2"));
}

#[test]
fn any_of_both_arms_satisfy_records_first_one_only() {
    // Sharpness theorem: the first satisfied arm wins (descending-search
    // semantics extended to disjuncts).
    let ctx = ctx_with_two_gaps_and_any_of_profile(true, true, "both");
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::AEX());
    let step = j
        .derivation
        .steps
        .iter()
        .find(|s| s.phase == "descending_search")
        .unwrap();
    // First arm fires; the note must mention g1.
    assert!(step.note.contains("g1"));
}

#[test]
fn any_of_with_empty_arms_is_malformed() {
    let mut ctx = ctx_with_two_gaps_and_any_of_profile(true, true, "empty");
    ctx.profiles[0].required_gaps[0].any_of = Some(vec![]);
    let result = compile(ctx);
    assert!(
        matches!(result, Err(TurnstileError::MalformedContext(_))),
        "empty any_of must be rejected; got {:?}",
        result
    );
}

#[test]
fn any_of_validates_unknown_arm_gap_id() {
    let mut ctx = ctx_with_two_gaps_and_any_of_profile(true, true, "bad");
    // Arm references a gap that doesn't exist in ctx.gaps
    ctx.profiles[0].required_gaps[0]
        .any_of
        .as_mut()
        .unwrap()
        .push(GapRequirement::single(
            "nonexistent",
            RequiredStatus::ClosedRequired,
        ));
    let result = compile(ctx);
    assert!(
        matches!(result, Err(TurnstileError::MalformedContext(_))),
        "any_of arm with unknown gap_id must be rejected"
    );
}

#[test]
fn nested_any_of_records_structured_label() {
    // A profile requiring (g1 OR (g2 OR g3)). Only g3 is closed. The derivation
    // must record the nested arm fired.
    let claim_id = "c-nested".to_string();
    let candidate_id = "z-nested".to_string();
    let context_id = "ctx-nested".to_string();
    let allowed_use = "use".to_string();
    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, &allowed_use);
    let tok = ProofToken {
        token_id: "tok-g3".into(),
        token_type: "T".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g3".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
            negative_control_id: None,
    };
    let ctx = ProofContext {
        claim_id,
        candidate_id,
        context_id,
        context_fingerprint: "fp".into(),
        allowed_use,
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![
            GapRecord::open("g1", "t"),
            GapRecord::open("g2", "t"),
            GapRecord::closed("g3", "t"),
        ],
        profiles: vec![Profile {
            permission: Permission::AEX(),
            required_gaps: vec![GapRequirement::any_of(vec![
                GapRequirement::single("g1", RequiredStatus::ClosedRequired),
                GapRequirement::any_of(vec![
                    GapRequirement::single("g2", RequiredStatus::ClosedRequired),
                    GapRequirement::single("g3", RequiredStatus::ClosedRequired),
                ]),
            ])],
        }],
        tokens: vec![tok],
        expiry: Expiry::never(),
        authority_ceiling: None,
        permission_ceiling: None,
        membership: Membership::InClass,
        expected_chain_hash: None,
    };
    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::AEX());
    let step = j
        .derivation
        .steps
        .iter()
        .find(|s| s.phase == "descending_search")
        .unwrap();
    // The nested any_of fired via g3; expect a structured label like any_of[g3].
    assert!(
        step.note.contains("any_of[g3]"),
        "expected nested arm label any_of[g3], got: {:?}",
        step.note
    );
}
