//! Helper chain constructors shared across the chain-parameterization test suite
//! (ec051..ec060).
//!
//! Per spec §7.6: every test that exercises a non-default chain should be able
//! to grab one from this module with a one-line call. The chain definitions
//! here are stable — tests reference them by name, not by inline definition.

use std::collections::HashMap;

use noethers_turnstile_core::permission::{ChainRole, Permission, PermissionChain};

/// Paper-style 5-level chain: `REF < DIA < REV < AEX < ALR`.
///
/// Below-threshold roles all collapse to `REF` (the Q5 non-strict allowance).
/// `BlockerThreshold = DIA`, `Top = ALR`.
pub fn paper_5_level() -> PermissionChain {
    let levels = vec![
        Permission::new("REF"),
        Permission::new("DIA"),
        Permission::new("REV"),
        Permission::new("AEX"),
        Permission::new("ALR"),
    ];
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0); // REF
    roles.insert(ChainRole::ExpiryFloor, 0); // REF (collapsed)
    roles.insert(ChainRole::Refused, 0); // REF (collapsed)
    roles.insert(ChainRole::Unsatisfied, 0); // REF (collapsed)
    roles.insert(ChainRole::DisallowedUsesCeiling, 0); // REF (collapsed)
    roles.insert(ChainRole::BlockerThreshold, 1); // DIA
    roles.insert(ChainRole::Top, 4); // ALR
    PermissionChain::new(levels, roles).expect("paper_5_level must validate")
}

/// Minimal 3-level chain: `L0 < L1 < L2`. All four below-threshold roles
/// collapse to `L0`; threshold is `L1`, top is `L2`.
pub fn minimal_3_level() -> PermissionChain {
    let levels = vec![
        Permission::new("L0"),
        Permission::new("L1"),
        Permission::new("L2"),
    ];
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 0);
    roles.insert(ChainRole::Refused, 0);
    roles.insert(ChainRole::Unsatisfied, 0);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 1);
    roles.insert(ChainRole::Top, 2);
    PermissionChain::new(levels, roles).expect("minimal_3_level must validate")
}

/// 8-level chain with non-paper names `L00..L07`. Used to verify the compiler
/// is name-agnostic. `BlockerThreshold` at L04, all below-threshold roles
/// collapsed to L00.
pub fn anon_8_level() -> PermissionChain {
    let names = ["L00", "L01", "L02", "L03", "L04", "L05", "L06", "L07"];
    let levels: Vec<Permission> = names.iter().map(|n| Permission::new(*n)).collect();
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 0);
    roles.insert(ChainRole::Refused, 0);
    roles.insert(ChainRole::Unsatisfied, 0);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 4);
    roles.insert(ChainRole::Top, 7);
    PermissionChain::new(levels, roles).expect("anon_8_level must validate")
}

/// 16-level chain where role anchors are **distinct mid-chain**, NOT collapsed.
/// Used by AM-01..06 to verify the all-meets discipline survives non-trivial
/// role placements.
///
/// Levels `L00..L15`. Roles:
/// - Bottom = L00
/// - ExpiryFloor = L02
/// - Refused = L04
/// - Unsatisfied = L06
/// - BlockerThreshold = L08
/// - Top = L15
pub fn anon_16_level_distinct_anchors() -> PermissionChain {
    let names: Vec<String> = (0..16).map(|i| format!("L{:02}", i)).collect();
    let levels: Vec<Permission> = names.iter().map(|n| Permission::new(n.clone())).collect();
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 2);
    roles.insert(ChainRole::Refused, 4);
    roles.insert(ChainRole::Unsatisfied, 6);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 8);
    roles.insert(ChainRole::Top, 15);
    PermissionChain::new(levels, roles).expect("anon_16_level_distinct_anchors must validate")
}

/// 6-level chain where `ExpiryFloor` is mid-chain (rank 2 of 6). AM-01/02's
/// canonical chain. Roles:
/// - Bottom = L0, ExpiryFloor = L2_EF, Refused = L1, Unsatisfied = L1,
///   BlockerThreshold = L3_BT, Top = L5
pub fn am_expiry_mid_chain() -> PermissionChain {
    let levels = vec![
        Permission::new("L0"),
        Permission::new("L1"),
        Permission::new("L2_EF"),
        Permission::new("L3_BT"),
        Permission::new("L4"),
        Permission::new("L5"),
    ];
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::Refused, 1);
    roles.insert(ChainRole::Unsatisfied, 1);
    roles.insert(ChainRole::ExpiryFloor, 2);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 3);
    roles.insert(ChainRole::Top, 5);
    PermissionChain::new(levels, roles).expect("am_expiry_mid_chain must validate")
}

/// Same shape as `am_expiry_mid_chain` but with `Refused` mid-chain instead of
/// at the bottom. Used by AM-03/04.
pub fn am_refused_mid_chain() -> PermissionChain {
    let levels = vec![
        Permission::new("L0"),
        Permission::new("L1_EF"),
        Permission::new("L2_REF"),
        Permission::new("L3_BT"),
        Permission::new("L4"),
        Permission::new("L5"),
    ];
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 1);
    roles.insert(ChainRole::Unsatisfied, 1);
    roles.insert(ChainRole::Refused, 2);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 3);
    roles.insert(ChainRole::Top, 5);
    PermissionChain::new(levels, roles).expect("am_refused_mid_chain must validate")
}

/// 2-level minimal chain `L0 < L1`. Bottom = L0, Top = L1, BlockerThreshold = L1.
/// All four below-threshold roles collapse to L0. Tests the L1 lower bound.
pub fn minimal_2_level() -> PermissionChain {
    let levels = vec![Permission::new("L0"), Permission::new("L1")];
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 0);
    roles.insert(ChainRole::Refused, 0);
    roles.insert(ChainRole::Unsatisfied, 0);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 1);
    roles.insert(ChainRole::Top, 1);
    PermissionChain::new(levels, roles).expect("minimal_2_level must validate")
}

/// Build a fresh context with one closed gap and a single profile at the
/// supplied permission, configured against the supplied chain. Useful in
/// chain-parameterized tests.
pub fn simple_context_with_profile(
    chain: &PermissionChain,
    profile_perm: Permission,
    suffix: &str,
) -> noethers_turnstile_core::ProofContext {
    use noethers_turnstile_core::{
        context::{Membership, ProofContext, Scope},
        expiry::Expiry,
        gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
        token::{compute_provenance_hash, ProofToken, TokenStatus},
    };
    let claim_id = format!("claim-{}", suffix);
    let candidate_id = format!("z-{}", suffix);
    let context_id = format!("ctx-{}", suffix);
    let allowed_use = "test-use".to_string();
    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, &allowed_use);

    ProofContext {
        claim_id: claim_id.clone(),
        candidate_id: candidate_id.clone(),
        context_id: context_id.clone(),
        context_fingerprint: format!("fp-{}", suffix),
        allowed_use,
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "test-gap")],
        profiles: vec![Profile {
            permission: profile_perm,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
                any_of: None,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: format!("tok-{}", suffix),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: chrono::Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
            negative_control_id: None,
        }],
        expiry: Expiry::never(),
        authority_ceiling: Some(*chain.role(ChainRole::Top)),
        permission_ceiling: Some(*chain.role(ChainRole::Top)),
        membership: Membership::InClass,
        expected_chain_hash: None,
    }
}
