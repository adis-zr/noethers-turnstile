/// Audit store tests: T18 — Audit is not authority.
///
/// Ported from:
///   ecds-core/tests/test_core.py  TestInMemoryAuditStore
///
/// Properties proved:
///   T18 — Audit is not authority: recording a judgment in the audit store
///          does not change the permission that would be recompiled from the
///          same context; the audit trail is read-only evidence, not a grant.
use chrono::Utc;
use noethers_noethers_turnstile_core::{
    audit::{AuditEntry, AuditStore, Derivation, InMemoryAuditStore},
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    permission::Permission,
};

fn make_entry(candidate_id: &str, claim_id: &str, permission: Permission) -> AuditEntry {
    AuditEntry {
        candidate_id: candidate_id.into(),
        claim_id: claim_id.into(),
        context_id: "ctx".into(),
        membership: "InClass".into(),
        permission,
        expiry_deadline: None,
        token_ids: vec![],
        provenance_hash: "hash".into(),
        derivation: Derivation::default(),
        emitted_at: Utc::now(),
    }
}

// ── T18: Audit is not authority ───────────────────────────────────────────────

#[test]
fn recording_aaa_in_audit_does_not_grant_aaa() {
    let store = InMemoryAuditStore::default();

    // Record a fictitious AAA judgment
    store.record(make_entry("z-1", "claim-1", Permission::AAA));

    // Now compile a real context that has no evidence → must be OOC
    let ctx = ProofContext {
        claim_id: "claim-1".into(),
        candidate_id: "z-1".into(),
        context_id: "ctx".into(),
        context_fingerprint: "fp".into(),
        allowed_use: "use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "audit record must not grant permission"
    );
}

#[test]
fn audit_write_read_roundtrip() {
    let store = InMemoryAuditStore::default();
    let e1 = make_entry("z-1", "claim-1", Permission::DIA);
    let e2 = make_entry("z-2", "claim-1", Permission::REV);

    store.record(e1);
    store.record(e2);

    let entries = store.entries();
    assert_eq!(entries.len(), 2);
}

#[test]
fn audit_entries_do_not_affect_subsequent_compiles() {
    let store = InMemoryAuditStore::default();

    // Record many high-privilege judgments
    for _ in 0..100 {
        store.record(make_entry("z-1", "claim-1", Permission::AAA));
    }

    // Compile a no-evidence context → must still be OOC
    let ctx = ProofContext {
        claim_id: "claim-1".into(),
        candidate_id: "z-1".into(),
        context_id: "ctx".into(),
        context_fingerprint: "fp".into(),
        allowed_use: "use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![],
        profiles: vec![],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let j = compile(ctx).unwrap();
    assert_eq!(j.permission, Permission::OOC);

    // Store still has 100 entries (unchanged)
    assert_eq!(store.entries().len(), 100);
}

#[test]
fn audit_multiple_candidates_independent() {
    let store = InMemoryAuditStore::default();
    store.record(make_entry("z-1", "claim-1", Permission::DIA));
    store.record(make_entry("z-2", "claim-1", Permission::REV));
    store.record(make_entry("z-1", "claim-2", Permission::AAA));

    let all = store.entries();
    assert_eq!(all.len(), 3);

    // None of these should affect compilation of other candidates
    let z1_entries: Vec<_> = all.iter().filter(|e| e.candidate_id == "z-1").collect();
    assert_eq!(z1_entries.len(), 2);
}

#[test]
fn derivation_records_steps_in_order() {
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
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let j = compile(ctx).unwrap();
    // The derivation must have at least one step (membership_check or descending_search)
    assert!(!j.derivation.steps.is_empty(), "derivation must have steps");

    // Steps must be well-formed
    for step in &j.derivation.steps {
        assert!(!step.phase.is_empty(), "step phase must not be empty");
    }
}

#[test]
fn derivation_permission_after_is_non_increasing() {
    use noethers_noethers_turnstile_core::{
        gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
        token::{compute_provenance_hash, ProofToken, TokenStatus},
    };

    let claim_id = "c";
    let candidate_id = "z";
    let context_id = "ctx";
    let allowed_use = "use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec!["blocked-use".into()], // triggers structural blocker
        scope: Scope::default(),
        gaps: vec![GapRecord::closed("g1", "t")],
        profiles: vec![Profile {
            permission: Permission::AAA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok".into(),
            token_type: "TEST".into(),
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
        }],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    let j = compile(ctx).unwrap();
    // Each step can only lower (or maintain) the permission — non-increasing
    let mut prev = Permission::AAA;
    for step in &j.derivation.steps {
        assert!(
            step.permission_after <= prev,
            "derivation step raised permission: {} → {}",
            prev,
            step.permission_after
        );
        prev = step.permission_after;
    }
}
