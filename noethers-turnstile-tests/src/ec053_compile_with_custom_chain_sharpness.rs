//! EC-053 — `compile_with_chain` sharpness on custom chains.
//!
//! Tests T-SHARP-01, T-SHARP-02 from spec §7.2. Sharpness: the compiler returns
//! the STRONGEST satisfied profile, not the weakest. Verified on multiple
//! chains to confirm name-agnosticism.

use chrono::Utc;
use noethers_turnstile_core::{
    compile_with_chain,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::{ChainRole, PermissionChain},
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};
use noethers_turnstile_tests::chain_helpers::{anon_16_level_distinct_anchors, paper_5_level};

fn closed_gap_ctx(chain: &PermissionChain, profile_perms: Vec<&str>, suffix: &str) -> ProofContext {
    let claim_id = format!("c-{suffix}");
    let candidate_id = format!("z-{suffix}");
    let context_id = format!("ctx-{suffix}");
    let allowed_use = format!("use-{suffix}");
    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, &allowed_use);
    let profiles = profile_perms
        .into_iter()
        .map(|name| Profile {
            permission: chain.parse(name).unwrap(),
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
                any_of: None,
            }],
        })
        .collect();
    ProofContext {
        claim_id,
        candidate_id,
        context_id,
        context_fingerprint: format!("fp-{suffix}"),
        allowed_use,
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "t")],
        profiles,
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
        authority_ceiling: Some(*chain.role(ChainRole::Top)),
        permission_ceiling: Some(*chain.role(ChainRole::Top)),
        membership: Membership::InClass,
        expected_chain_hash: None,
    }
}

#[test]
fn t_sharp_01_paper_chain_returns_strongest_satisfied() {
    // Paper chain: REF < DIA < REV < AEX < ALR.
    // Profiles at DIA, REV, AEX — all satisfied by closed g1. Result must be AEX.
    let chain = paper_5_level();
    let ctx = closed_gap_ctx(&chain, vec!["DIA", "REV", "AEX"], "sharp01");
    let j = compile_with_chain(ctx, &chain).unwrap();
    assert_eq!(j.permission.as_str(), "AEX");
}

#[test]
fn t_sharp_02_anon_16_chain_returns_strongest_satisfied() {
    // anon_16_level chain. Profiles at L05, L07, L12 all satisfied → L12 wins.
    let chain = anon_16_level_distinct_anchors();
    let ctx = closed_gap_ctx(&chain, vec!["L05", "L07", "L12"], "sharp02");
    let j = compile_with_chain(ctx, &chain).unwrap();
    assert_eq!(j.permission.as_str(), "L12");
}

#[test]
fn sharpness_with_single_profile_at_top() {
    let chain = paper_5_level();
    let ctx = closed_gap_ctx(&chain, vec!["ALR"], "sharp-top");
    let j = compile_with_chain(ctx, &chain).unwrap();
    assert_eq!(j.permission.as_str(), "ALR");
}
