//! EC-055 — Provenance enforcement under custom chains. T-PROV-01, T-PROV-02.

use chrono::Utc;
use noethers_turnstile_core::{
    compile_with_chain,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::ChainRole,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};
use noethers_turnstile_tests::chain_helpers::{
    anon_16_level_distinct_anchors, anon_8_level, paper_5_level,
};

fn ctx_with_open_gap_and_profile_at(
    chain: &noethers_turnstile_core::permission::PermissionChain,
    profile_level: &str,
    suffix: &str,
) -> ProofContext {
    ProofContext {
        claim_id: format!("c-{suffix}"),
        candidate_id: format!("z-{suffix}"),
        context_id: format!("ctx-{suffix}"),
        context_fingerprint: format!("fp-{suffix}"),
        allowed_use: format!("use-{suffix}"),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "t")],
        profiles: vec![Profile {
            permission: chain.parse(profile_level).unwrap(),
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
    }
}

#[test]
fn t_prov_01_provenance_mismatch_meets_to_refused_on_three_chains() {
    for (name, chain, profile_level) in [
        ("paper_5_level", paper_5_level(), "DIA"),
        ("anon_8_level", anon_8_level(), "L04"),
        ("anon_16_level", anon_16_level_distinct_anchors(), "L08"),
    ] {
        let mut ctx = ctx_with_open_gap_and_profile_at(&chain, profile_level, "prov01");
        // Wrong-provenance token.
        let bad = ProofToken {
            token_id: "bad".into(),
            token_type: "T".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec![],
            provenance_hash: "deadbeef".repeat(8),
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "t".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
            negative_control_id: None,
        };
        ctx.tokens.push(bad);
        let j = compile_with_chain(ctx, &chain).unwrap();
        let refused = chain.role(ChainRole::Refused);
        let outcome_rank = chain.rank(&j.permission).unwrap();
        let refused_rank = chain.rank(refused).unwrap();
        assert!(
            outcome_rank <= refused_rank,
            "T-PROV-01 ({name}): outcome {} must be ≤ Refused {refused}",
            j.permission
        );
    }
}

#[test]
fn t_prov_02_correct_provenance_above_threshold_suppresses_blocker() {
    // If a correct-provenance token satisfies a profile at or above the
    // BlockerThreshold, the structural blocker meet is suppressed even when a
    // wrong-provenance token is also present.
    let chain = paper_5_level();
    let allowed_use = "use".to_string();
    let claim_id = "c".to_string();
    let candidate_id = "z".to_string();
    let context_id = "ctx".to_string();
    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, &allowed_use);
    let good_tok = ProofToken {
        token_id: "good".into(),
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
            negative_control_id: None,
    };
    let bad_tok = ProofToken {
        token_id: "bad".into(),
        token_type: "T".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: "deadbeef".repeat(8),
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "t".into(),
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
        gaps: vec![GapRecord::open("g1", "t")],
        profiles: vec![Profile {
            permission: chain.parse("AEX").unwrap(),
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
                any_of: None,
            }],
        }],
        tokens: vec![good_tok, bad_tok],
        expiry: Expiry::never(),
        authority_ceiling: Some(*chain.role(ChainRole::Top)),
        permission_ceiling: Some(*chain.role(ChainRole::Top)),
        membership: Membership::InClass,
        expected_chain_hash: None,
    };
    let j = compile_with_chain(ctx, &chain).unwrap();
    // Profile at AEX satisfied → outcome = AEX, blocker suppressed.
    assert_eq!(j.permission.as_str(), "AEX");
}
