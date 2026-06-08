//! EC-054 — Expiry behavior under custom chains. T-EXPIRY-01, T-EXPIRY-02.
//!
//! Expiry floors to `chain.role(ExpiryFloor)`, not a hardcoded "EXP". The
//! expiry meet only lowers — never raises.

use chrono::{Duration, Utc};
use noethers_turnstile_core::{
    compile_with_chain,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::ChainRole,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};
use noethers_turnstile_tests::chain_helpers::anon_16_level_distinct_anchors;

#[test]
fn t_expiry_01_floors_to_chain_role_not_hardcoded_exp() {
    // anon_16_level chain has ExpiryFloor = L02 (NOT a level named "EXP").
    let chain = anon_16_level_distinct_anchors();
    let now = Utc::now();
    let allowed_use = "exp-use".to_string();
    let hash = compute_provenance_hash("c", "z", "ctx", &allowed_use);
    let tok = ProofToken {
        token_id: "expired".into(),
        token_type: "T".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: now - Duration::seconds(10),
        expires_at: Some(now - Duration::seconds(1)),
        issuer: "t".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    let ctx = ProofContext {
        claim_id: "c".into(),
        candidate_id: "z".into(),
        context_id: "ctx".into(),
        context_fingerprint: "fp".into(),
        allowed_use,
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "t")],
        profiles: vec![Profile {
            permission: chain.parse("L10").unwrap(),
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
                any_of: None,
            }],
        }],
        tokens: vec![tok],
        expiry: Expiry::never(),
        authority_ceiling: Some(*chain.role(ChainRole::Top)),
        permission_ceiling: Some(*chain.role(ChainRole::Top)),
        membership: Membership::InClass,
        expected_chain_hash: None,
    };
    let j = compile_with_chain(ctx, &chain).unwrap();
    // ExpiryFloor for this chain is L02. Result must equal L02.
    assert_eq!(j.permission, *chain.role(ChainRole::ExpiryFloor));
    assert_eq!(j.permission.as_str(), "L02");
}

#[test]
fn t_expiry_02_expiry_meet_only_lowers_never_raises() {
    // Chain has ExpiryFloor at rank 2. Construct a context whose descending
    // search would have landed at L05 (rank 5) without expiry. Add an expired
    // token. Outcome must be L02 (rank 2) — the meet lowered.
    let chain = anon_16_level_distinct_anchors();
    let now = Utc::now();
    let allowed_use = "exp-use".to_string();
    let hash = compute_provenance_hash("c", "z", "ctx", &allowed_use);

    let met_tok = ProofToken {
        token_id: "met".into(),
        token_type: "T".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g_met".into()],
        bounds_gaps: vec![],
        provenance_hash: hash.clone(),
        issued_at: now,
        expires_at: None,
        issuer: "t".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    let expired_tok = ProofToken {
        token_id: "exp".into(),
        token_type: "T".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g_other".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: now - Duration::seconds(10),
        expires_at: Some(now - Duration::seconds(1)),
        issuer: "t".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    let ctx = ProofContext {
        claim_id: "c".into(),
        candidate_id: "z".into(),
        context_id: "ctx".into(),
        context_fingerprint: "fp".into(),
        allowed_use,
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![
            GapRecord::closed("g_met", "t"),
            GapRecord::open("g_other", "t"),
        ],
        profiles: vec![Profile {
            permission: chain.parse("L05").unwrap(),
            required_gaps: vec![GapRequirement {
                gap_id: "g_met".into(),
                minimum_status: RequiredStatus::ClosedRequired,
                any_of: None,
            }],
        }],
        tokens: vec![met_tok, expired_tok],
        expiry: Expiry::never(),
        authority_ceiling: Some(*chain.role(ChainRole::Top)),
        permission_ceiling: Some(*chain.role(ChainRole::Top)),
        membership: Membership::InClass,
        expected_chain_hash: None,
    };
    let j = compile_with_chain(ctx, &chain).unwrap();
    // Search lands at L05, expiry meet → L02.
    assert_eq!(j.permission.as_str(), "L02");
}
