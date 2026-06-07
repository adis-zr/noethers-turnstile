//! EC-057 — Non-promotion under composition (T-NONPROMO-01, T-NONPROMO-02).

use chrono::Utc;
use noethers_turnstile_core::{
    compile_with_chain, compose_with_chain,
    context::{Membership, ProofContext, Scope},
    error::TurnstileError,
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::{ChainRole, Permission, PermissionChain},
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};
use noethers_turnstile_tests::chain_helpers::{
    am_expiry_mid_chain, anon_16_level_distinct_anchors, paper_5_level,
};

fn satisfied_ctx(chain: &PermissionChain, profile_perm: Permission, suffix: &str) -> ProofContext {
    let claim_id = format!("c-{suffix}");
    let candidate_id = format!("z-{suffix}");
    let context_id = format!("ctx-{suffix}");
    let allowed_use = "use".to_string();
    let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, &allowed_use);
    let tok = ProofToken {
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
    };
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
            permission: profile_perm,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
                any_of: None,
            }],
        }],
        tokens: vec![tok],
        expiry: Expiry::never(),
        authority_ceiling: Some(chain.role(ChainRole::Top).clone()),
        permission_ceiling: Some(chain.role(ChainRole::Top).clone()),
        membership: Membership::InClass,
        expected_chain_hash: None,
    }
}

#[test]
fn t_nonpromo_01_compose_under_three_chains() {
    let chains_and_perms: Vec<(&str, PermissionChain, &str, &str)> = vec![
        ("paper", paper_5_level(), "REV", "AEX"),
        ("expiry_mid", am_expiry_mid_chain(), "L4", "L5"),
        ("anon_16", anon_16_level_distinct_anchors(), "L09", "L12"),
    ];
    for (name, chain, a_level, b_level) in chains_and_perms {
        let ctx_a = satisfied_ctx(&chain, chain.parse(a_level).unwrap(), "a");
        let ctx_b = satisfied_ctx(&chain, chain.parse(b_level).unwrap(), "b");
        let p_a = compile_with_chain(ctx_a.clone(), &chain)
            .unwrap()
            .permission;
        let p_b = compile_with_chain(ctx_b.clone(), &chain)
            .unwrap()
            .permission;
        let meet = chain.meet(&p_a, &p_b).unwrap();
        let composed = compose_with_chain(ctx_a, ctx_b, &chain).unwrap();
        let p_c = compile_with_chain(composed, &chain).unwrap().permission;
        let r_c = chain.rank(&p_c).unwrap();
        let r_meet = chain.rank(&meet).unwrap();
        assert!(
            r_c <= r_meet,
            "T-NONPROMO-01 ({name}): composed {} > meet({}, {}) = {}",
            p_c,
            p_a,
            p_b,
            meet
        );
    }
}

#[test]
fn t_nonpromo_02_chain_mismatch_rejected() {
    // Two contexts pinned to different chains. compose_with_chain under either
    // one must reject the other.
    let x = paper_5_level();
    let y = anon_16_level_distinct_anchors();
    let mut ctx_x = satisfied_ctx(&x, x.parse("DIA").unwrap(), "x");
    ctx_x.expected_chain_hash = Some(x.chain_hash());
    let mut ctx_y = satisfied_ctx(&y, y.parse("L08").unwrap(), "y");
    ctx_y.expected_chain_hash = Some(y.chain_hash());

    let result = compose_with_chain(ctx_x, ctx_y, &x);
    // Either: a MalformedContext from foreign permission name detection, a
    // Composition(ChainMismatch) from chain-hash pin check, or Chain(ForeignLevel)
    // from a downstream meet on a foreign level — all are acceptable rejection
    // paths for N-04.
    assert!(
        matches!(
            result,
            Err(TurnstileError::MalformedContext(_))
                | Err(TurnstileError::Composition(
                    noethers_turnstile_core::error::CompositionError::ChainMismatch
                ))
                | Err(TurnstileError::Chain(_))
        ),
        "expected rejection, got {:?}",
        result
    );
}
