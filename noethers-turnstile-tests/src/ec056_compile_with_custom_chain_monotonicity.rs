//! EC-056 — Evidence monotonicity (T-MONO-01) across multiple chains.
//!
//! Adding a closed token to a context never lowers the emitted permission.

use chrono::Utc;
use noethers_turnstile_core::{
    compile_with_chain,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::{ChainRole, PermissionChain},
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};
use noethers_turnstile_tests::chain_helpers::{
    am_expiry_mid_chain, am_refused_mid_chain, anon_16_level_distinct_anchors, anon_8_level,
    minimal_3_level, paper_5_level,
};

fn ctx_with_two_gaps(
    chain: &PermissionChain,
    profile_level: &str,
    g1_closed: bool,
    g2_closed: bool,
    suffix: &str,
) -> ProofContext {
    let claim_id = format!("c-{suffix}");
    let candidate_id = format!("z-{suffix}");
    let context_id = format!("ctx-{suffix}");
    let allowed_use = format!("use-{suffix}");
    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, &allowed_use);
    let mut gaps = vec![];
    let mut tokens = vec![];
    let mut required = vec![];

    let g1 = if g1_closed {
        GapRecord::closed("g1", "t")
    } else {
        GapRecord::open("g1", "t")
    };
    gaps.push(g1);
    required.push(GapRequirement {
        gap_id: "g1".into(),
        minimum_status: RequiredStatus::ClosedRequired,
        any_of: None,
    });
    if g1_closed {
        tokens.push(make_tok("tok-g1", "g1", &hash));
    }

    let g2 = if g2_closed {
        GapRecord::closed("g2", "t")
    } else {
        GapRecord::open("g2", "t")
    };
    gaps.push(g2);
    required.push(GapRequirement {
        gap_id: "g2".into(),
        minimum_status: RequiredStatus::ClosedRequired,
        any_of: None,
    });
    if g2_closed {
        tokens.push(make_tok("tok-g2", "g2", &hash));
    }

    ProofContext {
        claim_id,
        candidate_id,
        context_id,
        context_fingerprint: format!("fp-{suffix}"),
        allowed_use,
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps,
        profiles: vec![Profile {
            permission: chain.parse(profile_level).unwrap(),
            required_gaps: required,
        }],
        tokens,
        expiry: Expiry::never(),
        authority_ceiling: Some(chain.role(ChainRole::Top).clone()),
        permission_ceiling: Some(chain.role(ChainRole::Top).clone()),
        membership: Membership::InClass,
        expected_chain_hash: None,
    }
}

fn make_tok(id: &str, gap: &str, hash: &str) -> ProofToken {
    ProofToken {
        token_id: id.into(),
        token_type: "T".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![gap.into()],
        bounds_gaps: vec![],
        provenance_hash: hash.to_string(),
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "t".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

#[test]
fn t_mono_01_adding_evidence_never_lowers_permission_on_eight_chains() {
    // For each chain in a hand-crafted test set, verify monotonicity:
    // closing more gaps never lowers outcome.
    let pairs: Vec<(&str, PermissionChain, &str)> = vec![
        ("paper_5_level", paper_5_level(), "AEX"),
        ("minimal_3_level", minimal_3_level(), "L2"),
        ("anon_8_level", anon_8_level(), "L05"),
        ("anon_16_level", anon_16_level_distinct_anchors(), "L10"),
        ("am_expiry_mid_chain", am_expiry_mid_chain(), "L4"),
        ("am_refused_mid_chain", am_refused_mid_chain(), "L4"),
    ];
    for (name, chain, profile_level) in pairs {
        // ctx_before: g1 closed, g2 OPEN → profile unsatisfied (UNS).
        let ctx_before = ctx_with_two_gaps(&chain, profile_level, true, false, "before");
        // ctx_after: both closed → profile satisfied.
        let ctx_after = ctx_with_two_gaps(&chain, profile_level, true, true, "after");
        let p_before = compile_with_chain(ctx_before, &chain).unwrap().permission;
        let p_after = compile_with_chain(ctx_after, &chain).unwrap().permission;
        let r_before = chain.rank(&p_before).unwrap();
        let r_after = chain.rank(&p_after).unwrap();
        assert!(
            r_after >= r_before,
            "T-MONO-01 ({name}): adding closing token lowered permission ({} -> {})",
            p_before,
            p_after
        );
    }
}
