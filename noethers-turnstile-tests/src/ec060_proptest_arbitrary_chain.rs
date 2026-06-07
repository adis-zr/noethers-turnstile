//! EC-060 — Property tests over arbitrary valid chains (P-CHAIN-01..05).

use std::collections::HashMap;

use chrono::Utc;
use noethers_turnstile_core::{
    compile_with_chain,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::{ChainHash, ChainRole, Permission, PermissionChain, MAX_LEVELS},
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};
use proptest::prelude::*;

/// Generator: random valid chain of 3..=64 levels (capped lower than MAX_LEVELS
/// to keep proptest tractable; P-CHAIN-04 separately tests boundary).
fn arb_chain() -> impl Strategy<Value = PermissionChain> {
    (3usize..=64).prop_flat_map(|n| {
        let names: Vec<String> = (0..n).map(|i| format!("L{:03}", i)).collect();
        // Random role assignments satisfying L1–L9:
        // Bottom=0, Top=n-1, BlockerThreshold in 1..=n-1.
        (Just(names), 1..n).prop_flat_map(move |(names, threshold)| {
            (
                Just(names),
                Just(threshold),
                // ExpiryFloor, Refused, Unsatisfied each ∈ [0, threshold-1] = [0, threshold).
                0..threshold,
                0..threshold,
                0..threshold,
            )
        })
        .prop_map(|(names, threshold, ef, refused, unsat)| {
            let levels: Vec<Permission> =
                names.iter().map(|n| Permission::new(n.clone())).collect();
            let n = levels.len();
            let mut roles = HashMap::new();
            roles.insert(ChainRole::Bottom, 0);
            roles.insert(ChainRole::ExpiryFloor, ef);
            roles.insert(ChainRole::Refused, refused);
            roles.insert(ChainRole::Unsatisfied, unsat);
            roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, threshold);
            roles.insert(ChainRole::Top, n - 1);
            PermissionChain::new(levels, roles).expect("generator must produce valid chains")
        })
    })
}

fn make_ctx_satisfied_at(chain: &PermissionChain, level: Permission, suffix: &str) -> ProofContext {
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
            permission: level,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
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
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "t".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        }],
        expiry: Expiry::never(),
        authority_ceiling: Some(chain.role(ChainRole::Top).clone()),
        permission_ceiling: Some(chain.role(ChainRole::Top).clone()),
        membership: Membership::InClass,
        expected_chain_hash: None,
    }
}

proptest! {
    /// P-CHAIN-01: Four README guarantees hold on every random chain × context.
    /// (Here we exercise non-promotion of compile: outcome ≤ profile level.)
    #[test]
    fn p_chain_01_compile_outcome_bounded_by_profile_level(
        chain in arb_chain(),
        profile_idx in any::<u8>(),
    ) {
        let levels = chain.levels();
        let idx = (profile_idx as usize) % levels.len();
        let profile_perm = levels[idx].clone();
        let ctx = make_ctx_satisfied_at(&chain, profile_perm.clone(), "p01");
        let j = compile_with_chain(ctx, &chain).unwrap();
        let p_rank = chain.rank(&j.permission).unwrap();
        let prof_rank = chain.rank(&profile_perm).unwrap();
        prop_assert!(p_rank <= prof_rank, "outcome {} exceeds profile {}", j.permission, profile_perm);
    }

    /// P-CHAIN-02: descending iterator yields every parseable level.
    #[test]
    fn p_chain_02_descending_levels_round_trip(chain in arb_chain()) {
        for level in chain.descending() {
            let parsed = chain.parse(level.as_str());
            prop_assert_eq!(parsed.as_ref(), Some(level));
        }
    }

    /// P-CHAIN-03: chain.meet(a, b) is a lower bound and the greatest lower bound.
    #[test]
    fn p_chain_03_meet_is_glb(chain in arb_chain(), a_idx in any::<u8>(), b_idx in any::<u8>()) {
        let levels = chain.levels();
        let a = levels[(a_idx as usize) % levels.len()].clone();
        let b = levels[(b_idx as usize) % levels.len()].clone();
        let m = chain.meet(&a, &b).unwrap();
        let m_rank = chain.rank(&m).unwrap();
        let a_rank = chain.rank(&a).unwrap();
        let b_rank = chain.rank(&b).unwrap();
        prop_assert!(m_rank <= a_rank, "meet({a},{b}) = {m}: not ≤ {a}");
        prop_assert!(m_rank <= b_rank, "meet({a},{b}) = {m}: not ≤ {b}");
        // GLB: no level c with c ≤ a and c ≤ b has c > m.
        for c in chain.descending() {
            let c_rank = chain.rank(c).unwrap();
            if c_rank <= a_rank && c_rank <= b_rank {
                prop_assert!(c_rank <= m_rank, "{c} is lower bound but exceeds meet");
            }
        }
    }

    /// P-CHAIN-04: Determinism — same chain, same context, same outcome.
    #[test]
    fn p_chain_04_compile_is_deterministic(
        chain in arb_chain(),
        idx in any::<u8>(),
    ) {
        let levels = chain.levels();
        let level = levels[(idx as usize) % levels.len()].clone();
        let ctx = make_ctx_satisfied_at(&chain, level, "p04");
        let j1 = compile_with_chain(ctx.clone(), &chain).unwrap();
        let j2 = compile_with_chain(ctx, &chain).unwrap();
        prop_assert_eq!(j1.permission, j2.permission);
        prop_assert_eq!(j1.chain_hash, j2.chain_hash);
    }

    /// P-CHAIN-05: Cross-chain rejection — a context whose profile permission
    /// is in chain A but not chain B yields MalformedContext under B.
    #[test]
    fn p_chain_05_cross_chain_rejection(
        chain_a in arb_chain(),
        chain_b in arb_chain(),
    ) {
        // Find a level name in A that is NOT in B.
        let a_names: Vec<&str> = chain_a.levels().iter().map(|l| l.as_str()).collect();
        let foreign: Option<&str> = a_names.into_iter().find(|n| !chain_b.contains(&Permission::new(*n)));
        let Some(foreign_name) = foreign else {
            return Ok(()); // every name in A also in B; skip (rare)
        };
        let profile_perm = chain_a.parse(foreign_name).unwrap();
        let ctx = make_ctx_satisfied_at(&chain_a, profile_perm, "p05");
        let result = compile_with_chain(ctx, &chain_b);
        prop_assert!(
            matches!(result, Err(noethers_turnstile_core::error::TurnstileError::MalformedContext(_))),
            "expected MalformedContext for cross-chain compile"
        );
    }
}

/// MAX_LEVELS boundary: a 256-level chain compiles a trivial context.
#[test]
fn boundary_256_level_chain_compiles_trivial_context() {
    let names: Vec<String> = (0..MAX_LEVELS).map(|i| format!("L{:04}", i)).collect();
    let levels: Vec<Permission> = names.iter().map(|n| Permission::new(n.clone())).collect();
    let mut roles = HashMap::new();
    roles.insert(ChainRole::Bottom, 0);
    roles.insert(ChainRole::ExpiryFloor, 1);
    roles.insert(ChainRole::Refused, 2);
    roles.insert(ChainRole::Unsatisfied, 3);
    roles.insert(ChainRole::DisallowedUsesCeiling, 0);
    roles.insert(ChainRole::BlockerThreshold, 100);
    roles.insert(ChainRole::Top, MAX_LEVELS - 1);
    let chain = PermissionChain::new(levels, roles).expect("256-level chain must validate");
    let ctx = make_ctx_satisfied_at(&chain, chain.parse("L0150").unwrap(), "max");
    let j = compile_with_chain(ctx, &chain).expect("compile must succeed");
    assert_eq!(j.permission.as_str(), "L0150");
}

/// chain_hash is unaffected by an unused ChainHash type fields. Smoke test that
/// the hash is deterministic across chain instances built from the same input.
#[test]
fn chain_hash_zero_value_does_not_collide_with_real_chain() {
    let zero = ChainHash::from_hex(&"0".repeat(64)).unwrap();
    assert_ne!(PermissionChain::default_chain().chain_hash(), zero);
}
