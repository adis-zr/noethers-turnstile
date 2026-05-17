/// Property test: Provenance enforcement.
///
/// A token with a wrong provenance hash never closes or bounds a gap.
/// Equivalently: if the only token for a gap has the wrong provenance,
/// the gap remains Open and the profile for that gap is not satisfied.
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

proptest! {
    /// For any context, a token with wrong provenance hash never closes a gap.
    #[test]
    fn wrong_provenance_never_closes_gap(
        claim_id in "[a-z]{4,8}",
        candidate_id in "[a-z]{4,8}",
        context_id in "[a-z]{4,8}",
        allowed_use in "[a-z]{4,8}",
        // Wrong provenance: use a different candidate_id to produce a mismatched hash.
        wrong_candidate in "[A-Z]{4,8}",
    ) {
        prop_assume!(candidate_id != wrong_candidate);

        let gap_id = "g1";

        // Context with one required gap.
        let ctx = ProofContext {
            claim_id: claim_id.clone(),
            candidate_id: candidate_id.clone(),
            context_id: context_id.clone(),
            context_fingerprint: "fp".into(),
            allowed_use: allowed_use.clone(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps: vec![GapRecord::open(gap_id, "test_gap")],
            profiles: vec![Profile {
                permission: Permission::DIA,
                required_gaps: vec![GapRequirement {
                    gap_id: gap_id.into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                }],
            }],
            tokens: vec![ProofToken {
                token_id: "tok-bad-prov".into(),
                token_type: "TEST".into(),
                schema_version: "0.1".into(),
                status: TokenStatus::Valid,
                closes_gaps: vec![gap_id.into()],
                bounds_gaps: vec![],
                // Wrong provenance: computed against wrong_candidate, not candidate_id.
                provenance_hash: compute_provenance_hash(
                    &claim_id,
                    &wrong_candidate,  // deliberately wrong
                    &context_id,
                    &allowed_use,
                ),
                issued_at: Utc::now(),
                expires_at: None,
                issuer: "test".into(),
                details: serde_json::Value::Null,
            is_negative_control: false,
            }],
            expiry: Expiry::never(),
            authority_ceiling: Permission::AAA,
            membership: Membership::InClass,
        };

        let j = compile(ctx).unwrap();
        // Wrong provenance → PROVENANCE_MISMATCH structural failure → REF meet applied.
        // InClass candidate with profile defined but unmet → REF.
        prop_assert_eq!(
            j.permission,
            Permission::REF,
            "wrong provenance token should not close gap; got {:?}",
            j.permission,
        );
    }

    /// Correct provenance closes the gap and allows the profile.
    #[test]
    fn correct_provenance_closes_gap(
        claim_id in "[a-z]{4,8}",
        candidate_id in "[a-z]{4,8}",
        context_id in "[a-z]{4,8}",
        allowed_use in "[a-z]{4,8}",
    ) {
        let gap_id = "g1";

        let ctx = ProofContext {
            claim_id: claim_id.clone(),
            candidate_id: candidate_id.clone(),
            context_id: context_id.clone(),
            context_fingerprint: "fp".into(),
            allowed_use: allowed_use.clone(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps: vec![GapRecord::closed(gap_id, "test_gap")],
            profiles: vec![Profile {
                permission: Permission::DIA,
                required_gaps: vec![GapRequirement {
                    gap_id: gap_id.into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                }],
            }],
            tokens: vec![ProofToken {
                token_id: "tok-good".into(),
                token_type: "TEST".into(),
                schema_version: "0.1".into(),
                status: TokenStatus::Valid,
                closes_gaps: vec![gap_id.into()],
                bounds_gaps: vec![],
                provenance_hash: compute_provenance_hash(
                    &claim_id,
                    &candidate_id,
                    &context_id,
                    &allowed_use,
                ),
                issued_at: Utc::now(),
                expires_at: None,
                issuer: "test".into(),
                details: serde_json::Value::Null,
            is_negative_control: false,
            }],
            expiry: Expiry::never(),
            authority_ceiling: Permission::AAA,
            membership: Membership::InClass,
        };

        let j = compile(ctx).unwrap();
        prop_assert_eq!(
            j.permission,
            Permission::DIA,
            "correct provenance should close gap; got {:?}",
            j.permission,
        );
    }
}
