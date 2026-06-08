//! EC-052 — `compile_with_chain` soundness on custom chains.
//!
//! Tests T-SOUND-01, T-SOUND-02 from spec §7.2. Soundness (§3.1, §3.3 of the
//! paper): the compiler must never authorize a permission whose blocking gap
//! is still open.

use noethers_turnstile_core::{
    compile_with_chain,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::ChainRole,
};
use noethers_turnstile_tests::chain_helpers::{minimal_3_level, paper_5_level};

/// T-SOUND-01: on a paper-style 5-level chain, an unsatisfied profile emits
/// `Unsatisfied`, not the profile's permission.
#[test]
fn t_sound_01_paper_chain_unsatisfied_profile_emits_unsatisfied() {
    let chain = paper_5_level();

    // For each level above the threshold, build a context whose ONLY profile
    // requires an open gap. The descending search must fail and outcome must
    // not exceed `Unsatisfied`.
    let above_threshold = ["DIA", "REV", "AEX", "ALR"];
    for level_name in above_threshold {
        let level = chain.parse(level_name).unwrap();
        let ctx = ProofContext {
            claim_id: format!("claim-{level_name}"),
            candidate_id: format!("z-{level_name}"),
            context_id: format!("ctx-{level_name}"),
            context_fingerprint: format!("fp-{level_name}"),
            allowed_use: "test-use".into(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps: vec![GapRecord::open("g1", "test-gap")],
            profiles: vec![Profile {
                permission: level,
                required_gaps: vec![GapRequirement {
                    gap_id: "g1".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                    any_of: None,
                }],
            }],
            tokens: vec![],
            expiry: Expiry::never(),
            authority_ceiling: Some(*chain.role(ChainRole::Top)),
            permission_ceiling: Some(*chain.role(ChainRole::Top)),
            membership: Membership::InClass,
            expected_chain_hash: None,
        };
        let j = compile_with_chain(ctx, &chain).unwrap();
        let outcome_rank = chain.rank(&j.permission).unwrap();
        let threshold_rank = chain.rank(chain.role(ChainRole::BlockerThreshold)).unwrap();
        assert!(
            outcome_rank < threshold_rank,
            "T-SOUND-01: outcome {} must be below BlockerThreshold for unsatisfied profile at {level_name}",
            j.permission,
        );
    }
}

/// T-SOUND-02: on a 3-level minimal chain (threshold = top), unsatisfied
/// profile at top emits the Unsatisfied role.
#[test]
fn t_sound_02_minimal_chain_unsatisfied_emits_role() {
    let chain = minimal_3_level();
    let top = *chain.role(ChainRole::Top);

    let ctx = ProofContext {
        claim_id: "c".into(),
        candidate_id: "z".into(),
        context_id: "ctx".into(),
        context_fingerprint: "fp".into(),
        allowed_use: "use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "t")],
        profiles: vec![Profile {
            permission: top,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
                any_of: None,
            }],
        }],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Some(*chain.role(ChainRole::Top)),
        permission_ceiling: Some(*chain.role(ChainRole::Top)),
        membership: Membership::InClass,
        expected_chain_hash: None,
    };
    let j = compile_with_chain(ctx, &chain).unwrap();
    assert_eq!(j.permission, *chain.role(ChainRole::Unsatisfied));
}

/// Membership out-of-class yields chain.role(Bottom) — not a hardcoded "OOC".
#[test]
fn membership_out_of_class_emits_chain_bottom() {
    let chain = paper_5_level();
    let ctx = ProofContext {
        claim_id: "c".into(),
        candidate_id: "z".into(),
        context_id: "ctx".into(),
        context_fingerprint: "fp".into(),
        allowed_use: "use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Some(*chain.role(ChainRole::Top)),
        permission_ceiling: Some(*chain.role(ChainRole::Top)),
        membership: Membership::OutOfClassExact,
        expected_chain_hash: None,
    };
    let j = compile_with_chain(ctx, &chain).unwrap();
    // Paper chain's bottom is REF.
    assert_eq!(j.permission.as_str(), "REF");
    assert_eq!(j.permission, *chain.role(ChainRole::Bottom));
}

/// compile_with_chain rejects contexts that reference foreign permission names.
#[test]
fn foreign_permission_rejected() {
    let chain = paper_5_level();
    // A profile at "DIA" is fine for paper chain. Use "OOC" (default-chain
    // bottom) which is NOT in the paper chain.
    let mut ctx = noethers_turnstile_tests::chain_helpers::simple_context_with_profile(
        &chain,
        chain.parse("DIA").unwrap(),
        "foreign",
    );
    ctx.profiles[0].permission = noethers_turnstile_core::permission::Permission::new("OOC");
    let result = compile_with_chain(ctx, &chain);
    assert!(matches!(
        result,
        Err(noethers_turnstile_core::error::TurnstileError::MalformedContext(_))
    ));
}
