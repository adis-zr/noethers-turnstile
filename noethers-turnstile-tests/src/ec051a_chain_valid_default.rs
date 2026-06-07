//! EC-051a — Chain construction: VALID chains (C-VALID-01 .. C-VALID-05).
//!
//! Each test instantiates a `PermissionChain` that should pass validation
//! (L1–L9 per spec §3.2) and asserts the constructor returns `Ok`. These tests
//! verify property (2) of the permission-chain refactor: validation accepts
//! chains that satisfy the structural rules.

use std::collections::HashMap;

use noethers_turnstile_core::permission::{ChainRole, Permission, PermissionChain, MAX_LEVELS};

#[test]
fn c_valid_01_default_chain_constructs() {
    let chain = PermissionChain::default_chain();
    assert_eq!(chain.len(), 12);
    // All six roles mapped.
    for role in ChainRole::ALL {
        let _ = chain.role(role);
    }
}

#[test]
fn c_valid_02_minimal_2_level_chain_with_collapsed_below_threshold_roles() {
    // 2 levels; Bottom=0, Top=1, BlockerThreshold=1, all four below-threshold
    // roles collapse to Bottom. Permitted under non-strict L7–L9 (Q5).
    let levels = vec![Permission::new("L0"), Permission::new("L1")];
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 0);
    roles.insert(ChainRole::Refused, 0);
    roles.insert(ChainRole::Unsatisfied, 0);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 1);
    roles.insert(ChainRole::Top, 1);
    let chain = PermissionChain::new(levels, roles).expect("minimal 2-level must validate");
    assert_eq!(chain.len(), 2);
    assert_eq!(chain.role(ChainRole::Bottom).as_str(), "L0");
    assert_eq!(chain.role(ChainRole::Top).as_str(), "L1");
    assert_eq!(chain.role(ChainRole::ExpiryFloor).as_str(), "L0");
    assert_eq!(chain.role(ChainRole::Refused).as_str(), "L0");
    assert_eq!(chain.role(ChainRole::Unsatisfied).as_str(), "L0");
}

#[test]
fn c_valid_03_paper_5_level_chain() {
    // REF < DIA < REV < AEX < ALR. Paper-style abbreviated chain.
    // All four below-threshold roles collapse to REF.
    let chain = noethers_turnstile_tests::chain_helpers::paper_5_level();
    assert_eq!(chain.len(), 5);
    assert_eq!(chain.role(ChainRole::Bottom).as_str(), "REF");
    assert_eq!(chain.role(ChainRole::ExpiryFloor).as_str(), "REF");
    assert_eq!(chain.role(ChainRole::Refused).as_str(), "REF");
    assert_eq!(chain.role(ChainRole::Unsatisfied).as_str(), "REF");
    assert_eq!(chain.role(ChainRole::BlockerThreshold).as_str(), "DIA");
    assert_eq!(chain.role(ChainRole::Top).as_str(), "ALR");
}

#[test]
fn c_valid_04_max_levels_boundary_256() {
    // L1: levels.len() ≤ MAX_LEVELS = 256.
    let levels: Vec<Permission> = (0..MAX_LEVELS)
        .map(|i| Permission::new(format!("L{:04}", i)))
        .collect();
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 1);
    roles.insert(ChainRole::Refused, 2);
    roles.insert(ChainRole::Unsatisfied, 3);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 100);
    roles.insert(ChainRole::Top, MAX_LEVELS - 1);
    let chain = PermissionChain::new(levels, roles).expect("256-level chain must validate");
    assert_eq!(chain.len(), MAX_LEVELS);
}

#[test]
fn c_valid_05_max_levels_minus_one() {
    let levels: Vec<Permission> = (0..MAX_LEVELS - 1)
        .map(|i| Permission::new(format!("L{:04}", i)))
        .collect();
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 1);
    roles.insert(ChainRole::Refused, 2);
    roles.insert(ChainRole::Unsatisfied, 3);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 100);
    roles.insert(ChainRole::Top, MAX_LEVELS - 2);
    let chain = PermissionChain::new(levels, roles).expect("255-level chain must validate");
    assert_eq!(chain.len(), MAX_LEVELS - 1);
}
