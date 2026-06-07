//! EC-060b — Publication smoke test (§3.3 mechanism 4).
//!
//! Acceptance criterion in §8: a smoke test that proves `verify_published`
//! fires correctly on an unpublished chain and passes on a published one.

use noethers_turnstile_core::{
    compile_with_chain, permission::AuditError, permission::InMemoryChainRegistry,
    permission::PermissionChain, verify_published,
};
use noethers_turnstile_tests::chain_helpers::{paper_5_level, simple_context_with_profile};

#[test]
fn unpublished_chain_fails_audit_then_publishes_and_passes() {
    let chain = paper_5_level();
    let ctx = simple_context_with_profile(&chain, chain.parse("DIA").unwrap(), "pub-smoke");
    let j = compile_with_chain(ctx, &chain).unwrap();

    // (a) Compile a judgment.
    assert_eq!(j.chain_hash, chain.chain_hash());

    // (b) Attempt verify_published against an empty registry — must fail.
    let mut reg = InMemoryChainRegistry::new();
    let err = verify_published(&j, &reg).expect_err("must be NotPublished");
    match err {
        AuditError::NotPublished { hash } => assert_eq!(hash, j.chain_hash),
        other => panic!("expected NotPublished, got {:?}", other),
    }

    // (c) Publish the chain.
    let published_hash = reg.publish(chain.clone());
    assert_eq!(published_hash, chain.chain_hash());

    // (d) Re-run — must pass.
    verify_published(&j, &reg).expect("must pass after publication");
}

#[test]
fn default_chain_judgment_can_be_verified_in_registry() {
    let chain = PermissionChain::default_chain().clone();
    let ctx = simple_context_with_profile(&chain, chain.parse("DIA").unwrap(), "pub-default");
    let j = compile_with_chain(ctx, &chain).unwrap();

    let mut reg = InMemoryChainRegistry::new();
    assert!(matches!(
        verify_published(&j, &reg),
        Err(AuditError::NotPublished { .. })
    ));
    reg.publish(chain);
    verify_published(&j, &reg).expect("default chain publication round-trip");
}

#[test]
fn chain_sidecar_carries_full_chain_for_self_contained_audit() {
    let chain = paper_5_level();
    let ctx = simple_context_with_profile(&chain, chain.parse("REV").unwrap(), "sidecar");
    let j = compile_with_chain(ctx, &chain)
        .unwrap()
        .with_chain_sidecar(&chain);
    assert!(j.chain.is_some());
    assert_eq!(j.chain.as_ref().unwrap().chain_hash(), j.chain_hash);
}
