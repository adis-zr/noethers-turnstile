/// Property test: Non-promotion under composition.
///
/// For any Γ₁, Γ₂ with the same (claim_id, candidate_id, context_id, allowed_use):
///   compile(compose(Γ₁, Γ₂)).permission ≤ min(
///       compile(Γ₁).permission,
///       compile(Γ₂).permission,
///   )
use chrono::Utc;
use proptest::prelude::*;
use noethers_turnstile_core::{
    compile, compose,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{Bound, GapRecord, GapRequirement, Profile, RequiredStatus},
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

#[allow(clippy::too_many_arguments)]
fn build_ctx(
    ceiling: Permission,
    gap_statuses: &[u8],
    add_token: bool,
    disallowed_count: usize,
    claim_id: &str,
    candidate_id: &str,
    context_id: &str,
    allowed_use: &str,
) -> ProofContext {
    let mut gaps = vec![];
    let mut profiles = vec![];

    for (i, &sk) in gap_statuses.iter().enumerate() {
        let gap_id = format!("gap-{}", i);
        let gap = match sk {
            0 => GapRecord::open(gap_id.clone(), "t"),
            1 => GapRecord::bounded(gap_id.clone(), "t", Bound::numeric(0.5)),
            _ => GapRecord::closed(gap_id.clone(), "t"),
        };
        gaps.push(gap);
    }

    if !gap_statuses.is_empty() {
        profiles.push(Profile {
            permission: Permission::DIA,
            required_gaps: gap_statuses
                .iter()
                .enumerate()
                .map(|(i, _)| GapRequirement {
                    gap_id: format!("gap-{}", i),
                    minimum_status: RequiredStatus::ClosedRequired,
                })
                .collect(),
        });
    }

    let mut tokens = vec![];
    if add_token && !gap_statuses.is_empty() {
        let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);
        tokens.push(ProofToken {
            token_id: "tok-1".into(),
            token_type: "PROP_TEST_TOKEN".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: gap_statuses
                .iter()
                .enumerate()
                .map(|(i, _)| format!("gap-{}", i))
                .collect(),
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "prop-test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        });
    }

    let disallowed_uses: Vec<String> = (0..disallowed_count)
        .map(|i| format!("blocked-use-{}", i))
        .collect();

    ProofContext {
        claim_id: claim_id.to_owned(),
        candidate_id: candidate_id.to_owned(),
        context_id: context_id.to_owned(),
        context_fingerprint: "fp".into(),
        allowed_use: allowed_use.to_owned(),
        disallowed_uses,
        scope: Scope::default(),
        gaps,
        profiles,
        tokens,
        expiry: Expiry::never(),
        authority_ceiling: ceiling,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

proptest! {
    #[test]
    fn non_promotion_under_composition(
        ceiling1 in arb_permission(),
        ceiling2 in arb_permission(),
        gap_statuses in prop::collection::vec(0u8..3u8, 0..4usize),
        add_token in prop::bool::ANY,
        disallowed_count in 0usize..2usize,
    ) {
        let claim_id = "c1";
        let candidate_id = "z1";
        let context_id = "ctx1";
        let allowed_use = "use1";

        let g1 = build_ctx(
            ceiling1, &gap_statuses, add_token, disallowed_count,
            claim_id, candidate_id, context_id, allowed_use,
        );
        let g2 = build_ctx(
            ceiling2, &gap_statuses, add_token, disallowed_count,
            claim_id, candidate_id, context_id, allowed_use,
        );

        let p1 = compile(g1.clone()).unwrap().permission;
        let p2 = compile(g2.clone()).unwrap().permission;
        let min_individual = p1.meet(p2);

        if let Ok(composed) = compose(g1, g2) {
            let p_composed = compile(composed).unwrap().permission;
            prop_assert!(
                p_composed <= min_individual,
                "non-promotion violated: composed={} > min({},{})",
                p_composed, p1, p2
            );
        }
    }

    /// Varying gap configurations independently between the two contexts.
    #[test]
    fn non_promotion_asymmetric_gaps(
        ceiling1 in arb_permission(),
        ceiling2 in arb_permission(),
        gaps1 in prop::collection::vec(0u8..3u8, 0..4usize),
        gaps2 in prop::collection::vec(0u8..3u8, 0..4usize),
        add_token in prop::bool::ANY,
    ) {
        let claim_id = "c2";
        let candidate_id = "z2";
        let context_id = "ctx2";
        let allowed_use = "use2";

        let gap_count = gaps1.len().min(gaps2.len());
        let gs1 = &gaps1[..gap_count];
        let gs2 = &gaps2[..gap_count];

        let g1 = build_ctx(ceiling1, gs1, add_token, 0, claim_id, candidate_id, context_id, allowed_use);
        let g2 = build_ctx(ceiling2, gs2, add_token, 0, claim_id, candidate_id, context_id, allowed_use);

        let p1 = compile(g1.clone()).unwrap().permission;
        let p2 = compile(g2.clone()).unwrap().permission;
        let min_individual = p1.meet(p2);

        if let Ok(composed) = compose(g1, g2) {
            let p_composed = compile(composed).unwrap().permission;
            prop_assert!(
                p_composed <= min_individual,
                "non-promotion (asymmetric) violated: composed={} > min({},{})",
                p_composed, p1, p2
            );
        }
    }
}
