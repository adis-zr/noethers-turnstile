/// Property test: Evidence monotonicity.
///
/// Adding a Closed token to a context never lowers the emitted permission.
///
/// Formally: if Γ' = Γ ∪ {t} where t is a new valid Closed token with
/// correct provenance, then compile(Γ').permission ≥ compile(Γ).permission.
use chrono::Utc;
use proptest::prelude::*;
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn arb_permission() -> impl Strategy<Value = Permission> {
    prop_oneof![
        Just(Permission::OOC),
        Just(Permission::EXP),
        Just(Permission::REF),
        Just(Permission::UNS),
        Just(Permission::ETA),
        Just(Permission::ESC),
        Just(Permission::ROL),
        Just(Permission::DIA),
        Just(Permission::REV),
        Just(Permission::AEX),
        Just(Permission::ALR),
        Just(Permission::AAA),
    ]
}

proptest! {
    /// Adding a closed token never lowers the emitted permission.
    #[test]
    fn adding_closed_token_never_lowers_permission(
        ceiling in arb_permission(),
        gap_count in 1usize..4usize,
        // For each gap: 0 = open, 1 = bounded, 2 = closed
        gap_statuses in prop::collection::vec(0u8..3u8, 1..4usize),
        // Which single gap the new token will close.
        target_gap_idx in 0usize..4usize,
    ) {
        let claim_id = "claim-mono".to_string();
        let candidate_id = "z-mono".to_string();
        let context_id = "ctx-mono".to_string();
        let allowed_use = "mono-test".to_string();

        let actual_gap_count = gap_count.min(gap_statuses.len());
        prop_assume!(actual_gap_count > 0);

        let mut gaps = vec![];
        for i in 0..actual_gap_count {
            let gap_id = format!("gap-{}", i);
            let gap = match gap_statuses[i] {
                0 => GapRecord::open(gap_id.clone(), "t"),
                1 => GapRecord::bounded(gap_id.clone(), "t", turnstile_core::gap::Bound::numeric(1.0)),
                _ => GapRecord::closed(gap_id.clone(), "t"),
            };
            gaps.push(gap);
        }

        // Profile: DIA requires all gaps closed.
        let profiles = vec![Profile {
            permission: Permission::DIA,
            required_gaps: (0..actual_gap_count)
                .map(|i| GapRequirement {
                    gap_id: format!("gap-{}", i),
                    minimum_status: RequiredStatus::ClosedRequired,
                })
                .collect(),
        }];

        let base_ctx = ProofContext {
            claim_id: claim_id.clone(),
            candidate_id: candidate_id.clone(),
            context_id: context_id.clone(),
            context_fingerprint: "fp-mono".into(),
            allowed_use: allowed_use.clone(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps: gaps.clone(),
            profiles: profiles.clone(),
            tokens: vec![],
            expiry: Expiry::never(),
            authority_ceiling: ceiling,
            membership: Membership::InClass,
        };

        let p_before = compile(base_ctx.clone()).unwrap().permission;

        // Now add a closed token for one of the gaps.
        let target = target_gap_idx % actual_gap_count;
        let gap_id = format!("gap-{}", target);
        let hash = compute_provenance_hash(&claim_id, &candidate_id, &context_id, &allowed_use);

        let new_token = ProofToken {
            token_id: format!("tok-close-{}", target),
            token_type: "CLOSE_TOKEN".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![gap_id.clone()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
        };

        // Also update the gap record to Closed (the token attests to closure).
        let mut enhanced_gaps = gaps.clone();
        enhanced_gaps[target] = GapRecord::closed(gap_id, "t");

        let enhanced_ctx = ProofContext {
            gaps: enhanced_gaps,
            tokens: vec![new_token],
            ..base_ctx
        };

        let p_after = compile(enhanced_ctx).unwrap().permission;

        // Adding closed evidence must not lower the permission.
        prop_assert!(
            p_after >= p_before,
            "monotonicity violated: before={} after={} target_gap={}",
            p_before, p_after, target
        );
    }
}

/// Sanity: adding an irrelevant (wrong-provenance) token also must not lower permission.
#[test]
fn wrong_provenance_token_does_not_lower_permission() {
    let claim_id = "claim-1".to_string();
    let candidate_id = "z-1".to_string();
    let context_id = "ctx-1".to_string();
    let allowed_use = "use-1".to_string();

    let gap_id = "g1";

    let base_ctx = ProofContext {
        claim_id: claim_id.clone(),
        candidate_id: candidate_id.clone(),
        context_id: context_id.clone(),
        context_fingerprint: "fp".into(),
        allowed_use: allowed_use.clone(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open(gap_id, "t")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: gap_id.into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let p_before = compile(base_ctx.clone()).unwrap().permission;
    assert_eq!(p_before, Permission::OOC);

    // Add a wrong-provenance token.
    let bad_token = ProofToken {
        token_id: "bad".into(),
        token_type: "T".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec![gap_id.into()],
        bounds_gaps: vec![],
        provenance_hash: "0".repeat(64), // wrong
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "test".into(),
        details: serde_json::Value::Null,
    };

    let ctx_with_bad = ProofContext { tokens: vec![bad_token], ..base_ctx };
    let p_after = compile(ctx_with_bad).unwrap().permission;

    // Must not lower (already at OOC, must stay at OOC or above).
    assert!(p_after >= p_before);
    // And a wrong-provenance token must not raise it either.
    assert_eq!(p_after, Permission::OOC);
}
