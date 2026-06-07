//! EC-051b — Chain construction: INVALID chains (C-INVALID-01 .. C-INVALID-11).
//!
//! Each test constructs a chain that should fail validation. Asserts the
//! correct `ChainError` variant fires. Verifies property (2) of the
//! permission-chain refactor: validation REJECTS chains that violate L1–L9.

use std::collections::HashMap;

use noethers_turnstile_core::permission::{
    ChainError, ChainRole, NameRejectionReason, Permission, PermissionChain, MAX_LEVELS,
    MAX_NAME_LEN,
};

fn all_six_roles_at(idx: usize) -> HashMap<ChainRole, usize> {
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 0);
    roles.insert(ChainRole::Refused, 0);
    roles.insert(ChainRole::Unsatisfied, 0);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, idx);
    roles.insert(ChainRole::Top, idx);
    roles
}

#[test]
fn c_invalid_01_too_few_levels() {
    // L1: levels.len() ≥ 2.
    let result = PermissionChain::new(vec![Permission::new("ONLY")], all_six_roles_at(0));
    match result {
        Err(ChainError::TooFewLevels { count: 1 }) => {}
        other => panic!("expected TooFewLevels {{ count: 1 }}, got {:?}", other),
    }
}

#[test]
fn c_invalid_02_too_many_levels() {
    // L1: levels.len() ≤ MAX_LEVELS. (MAX_LEVELS + 1) levels must fail.
    let levels: Vec<Permission> = (0..MAX_LEVELS + 1)
        .map(|i| Permission::new(format!("L{:04}", i)))
        .collect();
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 1);
    roles.insert(ChainRole::Refused, 2);
    roles.insert(ChainRole::Unsatisfied, 3);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 100);
    roles.insert(ChainRole::Top, MAX_LEVELS);
    let result = PermissionChain::new(levels, roles);
    match result {
        Err(ChainError::TooManyLevels { count, max }) => {
            assert_eq!(count, MAX_LEVELS + 1);
            assert_eq!(max, MAX_LEVELS);
        }
        other => panic!("expected TooManyLevels, got {:?}", other),
    }
}

#[test]
fn c_invalid_03_empty_name() {
    // L2: empty name rejected.
    let levels = vec![Permission::new(""), Permission::new("TOP")];
    let result = PermissionChain::new(levels, all_six_roles_at(1));
    match result {
        Err(ChainError::InvalidName {
            reason: NameRejectionReason::Empty,
            ..
        }) => {}
        other => panic!("expected InvalidName(Empty), got {:?}", other),
    }
}

#[test]
fn c_invalid_04_duplicate_name() {
    // L3: duplicate names rejected.
    let levels = vec![
        Permission::new("DUP"),
        Permission::new("DUP"),
        Permission::new("TOP"),
    ];
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 0);
    roles.insert(ChainRole::Refused, 0);
    roles.insert(ChainRole::Unsatisfied, 0);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 1);
    roles.insert(ChainRole::Top, 2);
    let result = PermissionChain::new(levels, roles);
    match result {
        Err(ChainError::DuplicateName(name)) => assert_eq!(name, "DUP"),
        other => panic!("expected DuplicateName, got {:?}", other),
    }
}

#[test]
fn c_invalid_05_missing_top_role() {
    // L4: every role must be mapped. Omit Top.
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 0);
    roles.insert(ChainRole::Refused, 0);
    roles.insert(ChainRole::Unsatisfied, 0);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 1);
    let result = PermissionChain::new(vec![Permission::new("A"), Permission::new("B")], roles);
    match result {
        Err(ChainError::MissingRole(ChainRole::Top)) => {}
        other => panic!("expected MissingRole(Top), got {:?}", other),
    }
}

#[test]
fn c_invalid_06_bottom_not_index_zero() {
    // L5: Bottom must be index 0. Put Bottom at index 1.
    let levels = vec![
        Permission::new("A"),
        Permission::new("B"),
        Permission::new("C"),
    ];
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 1);
    roles.insert(ChainRole::ExpiryFloor, 1);
    roles.insert(ChainRole::Refused, 1);
    roles.insert(ChainRole::Unsatisfied, 1);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 2);
    roles.insert(ChainRole::Top, 2);
    let result = PermissionChain::new(levels, roles);
    match result {
        Err(ChainError::RoleOrderViolation {
            role: ChainRole::Bottom,
            ..
        }) => {}
        other => panic!("expected RoleOrderViolation(Bottom), got {:?}", other),
    }
}

#[test]
fn c_invalid_07_top_not_last() {
    // L6: Top must be index len-1.
    let levels = vec![
        Permission::new("A"),
        Permission::new("B"),
        Permission::new("C"),
    ];
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 0);
    roles.insert(ChainRole::Refused, 0);
    roles.insert(ChainRole::Unsatisfied, 0);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 1);
    roles.insert(ChainRole::Top, 1); // should be 2
    let result = PermissionChain::new(levels, roles);
    match result {
        Err(ChainError::RoleOrderViolation {
            role: ChainRole::Top,
            ..
        }) => {}
        other => panic!("expected RoleOrderViolation(Top), got {:?}", other),
    }
}

#[test]
fn c_invalid_08_expiry_floor_above_or_equal_threshold() {
    // L7: ExpiryFloor < BlockerThreshold strict.
    let levels = vec![
        Permission::new("A"),
        Permission::new("B"),
        Permission::new("C"),
    ];
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 2); // bad: ≥ threshold (1)
    roles.insert(ChainRole::Refused, 0);
    roles.insert(ChainRole::Unsatisfied, 0);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 1);
    roles.insert(ChainRole::Top, 2);
    let result = PermissionChain::new(levels, roles);
    match result {
        Err(ChainError::RoleOrderViolation {
            role: ChainRole::ExpiryFloor,
            ..
        }) => {}
        other => panic!("expected RoleOrderViolation(ExpiryFloor), got {:?}", other),
    }
}

#[test]
fn c_invalid_09_refused_above_or_equal_threshold() {
    // L8: Refused < BlockerThreshold strict.
    let levels = vec![
        Permission::new("A"),
        Permission::new("B"),
        Permission::new("C"),
    ];
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 0);
    roles.insert(ChainRole::Refused, 1); // bad: == threshold
    roles.insert(ChainRole::Unsatisfied, 0);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 1);
    roles.insert(ChainRole::Top, 2);
    let result = PermissionChain::new(levels, roles);
    match result {
        Err(ChainError::RoleOrderViolation {
            role: ChainRole::Refused,
            ..
        }) => {}
        other => panic!("expected RoleOrderViolation(Refused), got {:?}", other),
    }
}

#[test]
fn c_invalid_10_unsatisfied_above_or_equal_threshold() {
    // L9: Unsatisfied < BlockerThreshold strict.
    let levels = vec![
        Permission::new("A"),
        Permission::new("B"),
        Permission::new("C"),
    ];
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 0);
    roles.insert(ChainRole::Refused, 0);
    roles.insert(ChainRole::Unsatisfied, 2); // bad: > threshold
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 1);
    roles.insert(ChainRole::Top, 2);
    let result = PermissionChain::new(levels, roles);
    match result {
        Err(ChainError::RoleOrderViolation {
            role: ChainRole::Unsatisfied,
            ..
        }) => {}
        other => panic!("expected RoleOrderViolation(Unsatisfied), got {:?}", other),
    }
}

#[test]
fn c_invalid_11_charset_violations() {
    // L2 charset: [A-Za-z0-9_][A-Za-z0-9_-]*, length 1–MAX_NAME_LEN.

    // (a) Space.
    let res = PermissionChain::new(
        vec![Permission::new("A B"), Permission::new("TOP")],
        all_six_roles_at(1),
    );
    assert!(matches!(
        res,
        Err(ChainError::InvalidName {
            reason: NameRejectionReason::CharsetViolation {
                offending_char: ' ',
                ..
            },
            ..
        })
    ));

    // (b) Non-ASCII (Unicode combining char).
    let res = PermissionChain::new(
        vec![Permission::new("DI\u{0301}A"), Permission::new("TOP")],
        all_six_roles_at(1),
    );
    assert!(matches!(
        res,
        Err(ChainError::InvalidName {
            reason: NameRejectionReason::CharsetViolation { .. },
            ..
        })
    ));

    // (c) Leading dash.
    let res = PermissionChain::new(
        vec![Permission::new("-LEAD"), Permission::new("TOP")],
        all_six_roles_at(1),
    );
    assert!(matches!(
        res,
        Err(ChainError::InvalidName {
            reason: NameRejectionReason::CharsetViolation { .. },
            ..
        })
    ));

    // (d) Too long.
    let long = "A".repeat(MAX_NAME_LEN + 1);
    let res = PermissionChain::new(
        vec![Permission::new(long), Permission::new("TOP")],
        all_six_roles_at(1),
    );
    assert!(matches!(
        res,
        Err(ChainError::InvalidName {
            reason: NameRejectionReason::TooLong { .. },
            ..
        })
    ));
}
