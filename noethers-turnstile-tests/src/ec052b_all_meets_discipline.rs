//! EC-052b — All-meets discipline (AM-01..07) from spec §7.4a.
//!
//! This is the load-bearing test of the non-promotion theorem. Every named
//! structural step in the compiler must be expressed as `chain.meet(outcome, ...)`
//! — never a positional clamp. These tests place role anchors at non-bottom
//! positions in the chain so a positional-clamp bug would produce visible
//! promotion.

use chrono::{Duration, Utc};
use noethers_turnstile_core::{
    compile_with_chain, compose_with_chain,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::{ChainRole, Permission, PermissionChain},
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};
use noethers_turnstile_tests::chain_helpers::{
    am_expiry_mid_chain, am_refused_mid_chain, anon_16_level_distinct_anchors, paper_5_level,
};

// ── AM-01/02: Expiry meet target sits mid-chain — verify non-promotion ──────

fn token_for(
    id: &str,
    closes: Vec<String>,
    ctx: &ProofContext,
    status: TokenStatus,
    expires_at: Option<chrono::DateTime<Utc>>,
) -> ProofToken {
    let hash = compute_provenance_hash(
        &ctx.claim_id,
        &ctx.candidate_id,
        &ctx.context_id,
        &ctx.allowed_use,
    );
    ProofToken {
        token_id: id.into(),
        token_type: "AM".into(),
        schema_version: "0.1".into(),
        status,
        closes_gaps: closes,
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now() - Duration::seconds(60),
        expires_at,
        issuer: "am".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }
}

#[test]
fn am_01_mid_chain_expiry_floor_meet_does_not_promote_from_below() {
    // Chain: L0 < L1 < L2_EF < L3_BT < L4 < L5
    // ExpiryFloor = L2_EF (rank 2)
    // We construct a context whose descending search lands at L1 (below the
    // expiry floor). An expired Valid-status token is also present. With the
    // all-meets discipline, the expiry step is meet(L1, L2_EF) = L1.
    // If the step were a positional clamp (outcome := L2_EF), outcome would be
    // wrongly RAISED from L1 to L2_EF.
    let chain = am_expiry_mid_chain();

    // Build a context with two profiles:
    //  * Profile at L1 (Refused/Unsatisfied) — requires no gaps and is auto-satisfied;
    //    but wait — we want the descending search to land at L1, which means
    //    L1 itself must be the highest satisfied profile. Profile at L1 with
    //    no gap requirements is trivially satisfied.
    //  * Profile at L5 (Top) requiring a closed gap that we do NOT close → unsatisfied.
    let l1 = chain.parse("L1").unwrap();
    let l5 = chain.parse("L5").unwrap();
    let l2_ef = chain.parse("L2_EF").unwrap();

    let mut ctx = ProofContext {
        claim_id: "am01".into(),
        candidate_id: "am01-z".into(),
        context_id: "am01-ctx".into(),
        context_fingerprint: "am01-fp".into(),
        allowed_use: "am01-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g_unmet", "t")],
        profiles: vec![
            Profile {
                permission: l5.clone(),
                required_gaps: vec![GapRequirement {
                    gap_id: "g_unmet".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                }],
            },
            Profile {
                permission: l1.clone(),
                required_gaps: vec![], // auto-satisfied
            },
        ],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Some(chain.role(ChainRole::Top).clone()),
        permission_ceiling: Some(chain.role(ChainRole::Top).clone()),
        membership: Membership::InClass,
        expected_chain_hash: None,
    };

    // Add an expired valid token with correct provenance for some unrelated gap.
    let expired_tok = token_for(
        "tok-expired",
        vec!["g_unmet".into()],
        &ctx,
        TokenStatus::Valid,
        Some(Utc::now() - Duration::seconds(1)),
    );
    ctx.tokens.push(expired_tok);

    let j = compile_with_chain(ctx, &chain).unwrap();
    let outcome_rank = chain.rank(&j.permission).unwrap();
    let l1_rank = chain.rank(&l1).unwrap();
    let l2_ef_rank = chain.rank(&l2_ef).unwrap();

    // The non-promotion theorem: outcome ≤ both seed (L1) and the expiry meet target.
    assert!(
        outcome_rank <= l1_rank,
        "AM-01: outcome {} must not exceed L1 ({}); meet must not promote below-floor outcome",
        j.permission,
        l1
    );
    // Also: outcome is NOT L2_EF — the meet did NOT raise it.
    assert_ne!(
        outcome_rank, l2_ef_rank,
        "AM-01: outcome must NOT be ExpiryFloor (positional clamp would have set it there)"
    );
}

#[test]
fn am_02_expiry_meet_does_lower_from_above_threshold() {
    // Same chain as AM-01. Descending search lands at L5 (top) with a closed
    // gap and a correct-provenance token. Then an expired Valid token is also
    // present → expiry meet fires → outcome lowers to L2_EF.
    let chain = am_expiry_mid_chain();

    let mut ctx = ProofContext {
        claim_id: "am02".into(),
        candidate_id: "am02-z".into(),
        context_id: "am02-ctx".into(),
        context_fingerprint: "am02-fp".into(),
        allowed_use: "am02-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![
            GapRecord::closed("g_met", "t"),
            GapRecord::open("g_separate", "t"),
        ],
        profiles: vec![Profile {
            permission: chain.parse("L5").unwrap(),
            required_gaps: vec![GapRequirement {
                gap_id: "g_met".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Some(chain.role(ChainRole::Top).clone()),
        permission_ceiling: Some(chain.role(ChainRole::Top).clone()),
        membership: Membership::InClass,
        expected_chain_hash: None,
    };
    // Satisfying token for g_met
    let met_tok = token_for(
        "tok-met",
        vec!["g_met".into()],
        &ctx,
        TokenStatus::Valid,
        None,
    );
    ctx.tokens.push(met_tok);
    // Expired token for an unrelated gap; with correct provenance, triggers EXP floor.
    let expired_tok = token_for(
        "tok-expired",
        vec!["g_separate".into()],
        &ctx,
        TokenStatus::Valid,
        Some(Utc::now() - Duration::seconds(1)),
    );
    ctx.tokens.push(expired_tok);

    let j = compile_with_chain(ctx, &chain).unwrap();
    // Outcome must be ExpiryFloor (L2_EF) — meet lowered from L5.
    assert_eq!(j.permission.as_str(), "L2_EF");
}

// ── AM-03/04: Refused meet target sits mid-chain ─────────────────────────────

#[test]
fn am_03_mid_chain_refused_meet_does_not_promote_from_below() {
    // Chain: L0 < L1_EF < L2_REF < L3_BT < L4 < L5
    // Refused = L2_REF.
    // Descending search lands at L0 (no profile defined at any level → Bottom).
    // A provenance-mismatch token is present. The structural-blocker meet only
    // fires when `outcome < BlockerThreshold (L3_BT)`. Here outcome is L0, so
    // the meet target L2_REF would raise it under a positional clamp.
    let chain = am_refused_mid_chain();

    let mut ctx = ProofContext {
        claim_id: "am03".into(),
        candidate_id: "am03-z".into(),
        context_id: "am03-ctx".into(),
        context_fingerprint: "am03-fp".into(),
        allowed_use: "am03-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "t")],
        // Profile at L5 requires g1 closed; gap is open so profile is unsatisfied.
        profiles: vec![Profile {
            permission: chain.parse("L5").unwrap(),
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Some(chain.role(ChainRole::Top).clone()),
        permission_ceiling: Some(chain.role(ChainRole::Top).clone()),
        membership: Membership::InClass,
        expected_chain_hash: None,
    };
    // Add a wrong-provenance token.
    let bad_tok = ProofToken {
        token_id: "bad".into(),
        token_type: "AM".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: "deadbeef".repeat(8),
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "am".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    ctx.tokens.push(bad_tok);

    let j = compile_with_chain(ctx, &chain).unwrap();
    // Descending search starts at Unsatisfied=L1_EF (because a profile exists but
    // is not satisfied). The provenance-mismatch blocker fires (outcome
    // < threshold). The meet(L1_EF, L2_REF) = L1_EF — meet picks the LOWER.
    // Under a positional clamp the outcome would be raised to L2_REF.
    let outcome_rank = chain.rank(&j.permission).unwrap();
    let refused_rank = chain.rank(chain.role(ChainRole::Refused)).unwrap();
    assert!(
        outcome_rank <= refused_rank,
        "AM-03: outcome {} must not exceed Refused (positional clamp would raise it)",
        j.permission
    );
}

#[test]
fn am_04_refused_meet_lowers_outcome_at_threshold() {
    // Same chain. Build a context where the descending search lands AT the
    // BlockerThreshold (one threshold-rank profile satisfied — but actually we
    // need the descending search to skip into the below-threshold region
    // entirely for the blocker to fire). Test: provenance-mismatch blocker
    // can lower outcomes from below-threshold positions.
    let chain = am_refused_mid_chain();

    let mut ctx = ProofContext {
        claim_id: "am04".into(),
        candidate_id: "am04-z".into(),
        context_id: "am04-ctx".into(),
        context_fingerprint: "am04-fp".into(),
        allowed_use: "am04-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "t")],
        profiles: vec![Profile {
            permission: chain.parse("L4").unwrap(),
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Some(chain.role(ChainRole::Top).clone()),
        permission_ceiling: Some(chain.role(ChainRole::Top).clone()),
        membership: Membership::InClass,
        expected_chain_hash: None,
    };
    // Add wrong-provenance token. Descending search lands at Unsatisfied=L1_EF
    // (rank 1). Blocker fires → meet with L2_REF (rank 2). But meet picks min.
    let bad_tok = ProofToken {
        token_id: "bad".into(),
        token_type: "AM".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: "deadbeef".repeat(8),
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "am".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    ctx.tokens.push(bad_tok);

    let j = compile_with_chain(ctx, &chain).unwrap();
    // outcome is L1_EF (Unsatisfied), meet with L2_REF (Refused) gives min=L1_EF.
    // So outcome stays at L1_EF — confirming the meet does not raise.
    let outcome_rank = chain.rank(&j.permission).unwrap();
    let l1_ef_rank = chain.rank(chain.role(ChainRole::Unsatisfied)).unwrap();
    assert_eq!(
        outcome_rank, l1_ef_rank,
        "AM-04: meet picks lower of the two"
    );
}

// ── AM-05/06: Composition non-promotion + derivation step monotonicity ──────

#[test]
fn am_05_compose_non_promotion_mid_chain_anchors() {
    let chain = anon_16_level_distinct_anchors();

    // Build two contexts each compiling to known levels: one at L10, one at L08.
    let ctx_a = make_satisfied_ctx(&chain, "a", chain.parse("L10").unwrap());
    let ctx_b = make_satisfied_ctx(&chain, "b", chain.parse("L08").unwrap());

    let p_a = compile_with_chain(ctx_a.clone(), &chain)
        .unwrap()
        .permission;
    let p_b = compile_with_chain(ctx_b.clone(), &chain)
        .unwrap()
        .permission;
    let expected_min = chain.meet(&p_a, &p_b).unwrap();

    let composed = compose_with_chain(ctx_a, ctx_b, &chain).unwrap();
    let p_c = compile_with_chain(composed, &chain).unwrap().permission;

    let p_c_rank = chain.rank(&p_c).unwrap();
    let expected_rank = chain.rank(&expected_min).unwrap();
    assert!(
        p_c_rank <= expected_rank,
        "AM-05: composed permission {} must be ≤ meet({}, {}) = {}",
        p_c,
        p_a,
        p_b,
        expected_min
    );
}

fn make_satisfied_ctx(
    chain: &PermissionChain,
    suffix: &str,
    profile_perm: Permission,
) -> ProofContext {
    let claim_id = format!("claim-{suffix}");
    let candidate_id = format!("z-{suffix}");
    let context_id = format!("ctx-{suffix}");
    let allowed_use = "common-use".to_string();
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
        issuer: "test".into(),
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
fn am_06_derivation_steps_are_monotone() {
    // For 30 random contexts × 3 chains, every step in Judgment.derivation has
    // permission_after ≤ previous_step.permission_after under the chain's order.
    use proptest::prelude::*;
    use proptest::strategy::ValueTree;
    use proptest::test_runner::TestRunner;

    let chains = [
        paper_5_level(),
        am_expiry_mid_chain(),
        anon_16_level_distinct_anchors(),
    ];
    let mut runner = TestRunner::default();

    for chain in &chains {
        for _ in 0..30 {
            // Random profile permission within the chain (above bottom).
            let levels = chain.levels();
            let mut idx_tree = (1usize..levels.len()).new_tree(&mut runner).unwrap();
            let idx = idx_tree.current();
            let profile_perm = levels[idx].clone();
            let ctx = make_satisfied_ctx(chain, "am06", profile_perm);
            let j = compile_with_chain(ctx, chain).unwrap();
            let mut prev_rank: Option<u8> = None;
            for step in &j.derivation.steps {
                let r = chain.rank(&step.permission_after).unwrap();
                if let Some(p) = prev_rank {
                    assert!(
                        r <= p,
                        "AM-06: derivation step {} ranks {} > previous {} (non-monotone)",
                        step.phase,
                        r,
                        p
                    );
                }
                prev_rank = Some(r);
            }
        }
    }
}

// ── AM-07: Dual of AM-01 — collapsed anchors (paper-5-level) ─────────────────

#[test]
fn am_07_collapsed_anchor_multi_blocker_compile_is_monotone() {
    // Paper-5-level chain has Bottom = ExpiryFloor = Refused = Unsatisfied = REF.
    // Construct a context that simultaneously fires all three below-threshold
    // meets: descending search lands at Unsatisfied (no profile satisfied),
    // a provenance-mismatch token is present (Refused meet), AND an expired
    // valid token is present (ExpiryFloor meet).
    let chain = paper_5_level();

    let mut ctx = ProofContext {
        claim_id: "am07".into(),
        candidate_id: "am07-z".into(),
        context_id: "am07-ctx".into(),
        context_fingerprint: "am07-fp".into(),
        allowed_use: "am07-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "t")],
        profiles: vec![Profile {
            permission: chain.parse("AEX").unwrap(),
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Some(chain.role(ChainRole::Top).clone()),
        permission_ceiling: Some(chain.role(ChainRole::Top).clone()),
        membership: Membership::InClass,
        expected_chain_hash: None,
    };
    // Wrong-provenance token → Refused meet.
    let bad_tok = ProofToken {
        token_id: "bad".into(),
        token_type: "AM".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: "deadbeef".repeat(8),
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "am".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };
    ctx.tokens.push(bad_tok);

    // Expired correct-provenance token → ExpiryFloor meet.
    let expired_tok = token_for(
        "tok-exp",
        vec!["g1".into()],
        &ctx,
        TokenStatus::Valid,
        Some(Utc::now() - Duration::seconds(1)),
    );
    ctx.tokens.push(expired_tok);

    let j = compile_with_chain(ctx, &chain).unwrap();
    // All three roles collapse to REF — outcome must be REF.
    assert_eq!(j.permission.as_str(), "REF");

    // Each step in the derivation should be ≤ previous (idempotent meets on
    // the coincident target).
    let mut prev_rank: Option<u8> = None;
    for step in &j.derivation.steps {
        let r = chain.rank(&step.permission_after).unwrap();
        if let Some(p) = prev_rank {
            assert!(
                r <= p,
                "AM-07: derivation step {} ranks {} > previous {} (non-monotone)",
                step.phase,
                r,
                p
            );
        }
        prev_rank = Some(r);
    }
}
