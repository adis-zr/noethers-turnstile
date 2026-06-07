//! EC-055b — Chain identity tests (CH-01..06) from spec §7.4b.
//!
//! Verifies the "chain identity, not just name identity" mechanism (§3.3):
//! two chains with the same level name at different ranks have different
//! `chain_hash`es, and `expected_chain_hash` pinning rejects mismatches.

use std::collections::HashMap;

use noethers_turnstile_core::{
    compile_with_chain, compose_with_chain,
    context::{Membership, ProofContext, Scope},
    error::{CompositionError, TurnstileError},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::{ChainRole, Permission, PermissionChain},
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

/// Build chain X: ["FOO", "DIA", "BAR", "BAZ", "TOP"] — "DIA" at rank 1.
fn chain_x() -> PermissionChain {
    let levels: Vec<Permission> = ["FOO", "DIA", "BAR", "BAZ", "TOP"]
        .iter()
        .map(|n| Permission::new(*n))
        .collect();
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 0);
    roles.insert(ChainRole::Refused, 0);
    roles.insert(ChainRole::Unsatisfied, 0);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 2);
    roles.insert(ChainRole::Top, 4);
    PermissionChain::new(levels, roles).expect("chain_x must validate")
}

/// Build chain Y: ["BAR", "FOO", "DIA", "BAZ", "TOP"] — "DIA" at rank 2.
/// Same name set, different order.
fn chain_y() -> PermissionChain {
    let levels: Vec<Permission> = ["BAR", "FOO", "DIA", "BAZ", "TOP"]
        .iter()
        .map(|n| Permission::new(*n))
        .collect();
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 0);
    roles.insert(ChainRole::Refused, 0);
    roles.insert(ChainRole::Unsatisfied, 0);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 3);
    roles.insert(ChainRole::Top, 4);
    PermissionChain::new(levels, roles).expect("chain_y must validate")
}

fn ctx_pinned_to(
    chain: &PermissionChain,
    profile_level: &str,
    expected_hash: Option<noethers_turnstile_core::permission::ChainHash>,
    suffix: &str,
) -> ProofContext {
    let claim_id = format!("c-{suffix}");
    let candidate_id = format!("z-{suffix}");
    let context_id = format!("ctx-{suffix}");
    let allowed_use = "use".to_string();
    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, &allowed_use);
    ProofContext {
        claim_id,
        candidate_id,
        context_id,
        context_fingerprint: format!("fp-{suffix}"),
        allowed_use,
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "t")],
        profiles: vec![Profile {
            permission: chain.parse(profile_level).unwrap(),
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
                any_of: None,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: format!("tok-{suffix}"),
            token_type: "T".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: chrono::Utc::now(),
            expires_at: None,
            issuer: "t".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        }],
        expiry: Expiry::never(),
        authority_ceiling: Some(chain.role(ChainRole::Top).clone()),
        permission_ceiling: Some(chain.role(ChainRole::Top).clone()),
        membership: Membership::InClass,
        expected_chain_hash: expected_hash,
    }
}

#[test]
fn ch_01_pinned_context_rejects_foreign_chain_with_name_collision() {
    let x = chain_x();
    let y = chain_y();
    assert_ne!(
        x.chain_hash(),
        y.chain_hash(),
        "Setup: chains must have different hashes despite name collision"
    );

    // Context authored against chain X with hash pinned. Compile with Y.
    let ctx = ctx_pinned_to(&x, "DIA", Some(x.chain_hash()), "ch01");
    let result = compile_with_chain(ctx, &y);
    assert!(
        matches!(result, Err(TurnstileError::MalformedContext(_))),
        "CH-01: pinned context must reject foreign chain even if names match"
    );
}

#[test]
fn ch_02_unpinned_context_compiles_under_either_chain_but_hash_records_authorizer() {
    let x = chain_x();
    let y = chain_y();
    let ctx = ctx_pinned_to(&x, "DIA", None, "ch02");
    let j_y = compile_with_chain(ctx.clone(), &y).unwrap();
    // Y's hash is recorded — auditor can detect Y authorized, not X.
    assert_eq!(j_y.chain_hash, y.chain_hash());
    assert_ne!(j_y.chain_hash, x.chain_hash());
}

#[test]
fn ch_03_chain_hash_stable_across_clone_and_serde() {
    let x = chain_x();
    let h1 = x.chain_hash();
    let h2 = x.clone().chain_hash();
    assert_eq!(h1, h2);

    let json = serde_json::to_string(&x).unwrap();
    let parsed: PermissionChain = serde_json::from_str(&json).unwrap();
    assert_eq!(parsed.chain_hash(), h1);
}

#[test]
fn ch_04_chain_hash_deterministic_across_processes() {
    // Same content → same hash, regardless of construction path.
    let x1 = chain_x();
    let x2 = chain_x();
    assert_eq!(x1.chain_hash(), x2.chain_hash());

    // Reconstruct via serde round trip.
    let json = serde_json::to_string(&x1).unwrap();
    let x3: PermissionChain = serde_json::from_str(&json).unwrap();
    assert_eq!(x1.chain_hash(), x3.chain_hash());
}

#[test]
fn ch_05_role_binding_differences_yield_different_hash() {
    // Same ordered names, different role binding → different hash.
    let names = ["A", "B", "C", "D"];
    let levels_a: Vec<Permission> = names.iter().map(|n| Permission::new(*n)).collect();
    let levels_b = levels_a.clone();

    let mut r1 = HashMap::new();
    r1.insert(ChainRole::Bottom, 0);
    r1.insert(ChainRole::ExpiryFloor, 1);
    r1.insert(ChainRole::Refused, 1);
    r1.insert(ChainRole::Unsatisfied, 1);
    r1.insert(ChainRole::DisallowedUsesCeiling, 0);
    r1.insert(ChainRole::BlockerThreshold, 2);
    r1.insert(ChainRole::Top, 3);
    let c1 = PermissionChain::new(levels_a, r1).unwrap();

    let mut r2 = HashMap::new();
    r2.insert(ChainRole::Bottom, 0);
    r2.insert(ChainRole::ExpiryFloor, 0); // differs from r1
    r2.insert(ChainRole::Refused, 0);
    r2.insert(ChainRole::Unsatisfied, 0);
    r2.insert(ChainRole::DisallowedUsesCeiling, 0);
    r2.insert(ChainRole::BlockerThreshold, 2);
    r2.insert(ChainRole::Top, 3);
    let c2 = PermissionChain::new(levels_b, r2).unwrap();

    assert_ne!(c1.chain_hash(), c2.chain_hash());
}

#[test]
fn ch_06_compose_rejects_judgments_from_different_chains() {
    let x = chain_x();
    let y = chain_y();
    let ctx_x = ctx_pinned_to(&x, "DIA", Some(x.chain_hash()), "ch06x");
    let ctx_y = ctx_pinned_to(&y, "DIA", Some(y.chain_hash()), "ch06y");

    // Composing ctx_x with ctx_y under chain X must fail: ctx_y's pin doesn't match.
    let result = compose_with_chain(ctx_x.clone(), ctx_y.clone(), &x);
    assert!(matches!(
        result,
        Err(TurnstileError::Composition(CompositionError::ChainMismatch))
            | Err(TurnstileError::MalformedContext(_))
    ));
}
