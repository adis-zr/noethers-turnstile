/// EC-003X — Audit is not authority (T18).
///
/// T18: Audit is not authority
///   An audit record alone cannot discharge proof obligations.
///   Recording a judgment does not re-issue it. An audit store entry
///   is observational only; it cannot be fed back as a proof token.
///
/// T19: Scientific boundary theorem (structural only)
///   Turnstile proves structural soundness. Domain-scientific correctness
///   (calibration truth, causal validity, optimality) belongs to certifiers.
///   The compiler does not validate certifier outputs.
///
/// Falsification conditions:
///   - An AuditEntry could be deserialized back into a ProofToken and
///     used to close a gap (audit laundering).
///   - AuditStore.entries() count affects compile() outcome.
///   - Compiling the same context multiple times inflates audit entries
///     in a way that upgrades subsequent compilations.
use chrono::Utc;
use std::sync::Arc;
use turnstile_core::{
    audit::{AuditEntry, AuditStore, Derivation, InMemoryAuditStore},
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::Expiry,
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};

fn ctx_needs_g1_closed() -> ProofContext {
    ProofContext {
        claim_id: "claim-t18-auth".into(),
        candidate_id: "z-t18-auth".into(),
        context_id: "ctx-t18-auth".into(),
        context_fingerprint: "fp-t18-auth".into(),
        allowed_use: "t18-auth-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "calibration_gap")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    }
}

// ── T18: Audit record does not grant permission ───────────────────────────────

#[test]
fn t18_audit_store_not_consulted_by_compiler() {
    // Pre-populate an audit store with a prior judgment of DIA.
    // The compiler must not look at the store or be affected by it.
    let store = Arc::new(InMemoryAuditStore::default());

    let prior_judgment_context = ctx_needs_g1_closed();
    // Manually create an audit entry claiming DIA (as if it had been granted before).
    let fake_entry = AuditEntry {
        candidate_id: prior_judgment_context.candidate_id.clone(),
        claim_id: prior_judgment_context.claim_id.clone(),
        context_id: prior_judgment_context.context_id.clone(),
        membership: "InClass".into(),
        permission: Permission::DIA,
        expiry_deadline: None,
        token_ids: vec!["fake-tok".into()],
        provenance_hash: prior_judgment_context.provenance_hash(),
        derivation: Derivation::new().with_provenance(prior_judgment_context.provenance_hash()),
        emitted_at: Utc::now(),
    };
    store.record(fake_entry);
    assert_eq!(
        store.entries().len(),
        1,
        "setup: one audit entry pre-recorded"
    );

    // Now compile the same context WITHOUT any actual proof tokens.
    // The store has a DIA record but the compiler must not use it.
    let ctx = ctx_needs_g1_closed();
    let j = compile(ctx).unwrap();

    // In-class, profile defined, no proof token → UNS
    assert_eq!(
        j.permission,
        Permission::UNS,
        "T18: audit record must not grant permission; gap still open → UNS (in-class)"
    );
}

#[test]
fn t18_repeated_compilations_do_not_escalate() {
    // Compiling the same context 100 times must not produce different results.
    let ctx = ctx_needs_g1_closed();
    let baseline = compile(ctx.clone()).unwrap().permission;
    // In-class, profile defined, no token → UNS
    assert_eq!(baseline, Permission::UNS);

    for i in 0..100 {
        let p = compile(ctx.clone()).unwrap().permission;
        assert_eq!(
            p,
            Permission::UNS,
            "T18: repeated compilation {i} changed permission from UNS to {p}"
        );
    }
}

#[test]
fn t18_audit_store_append_only() {
    let store = InMemoryAuditStore::default();
    let e1 = AuditEntry {
        candidate_id: "z-1".into(),
        claim_id: "c-1".into(),
        context_id: "ctx-1".into(),
        membership: "InClass".into(),
        permission: Permission::DIA,
        expiry_deadline: None,
        token_ids: vec![],
        provenance_hash: "hash-1".into(),
        derivation: Derivation::default(),
        emitted_at: Utc::now(),
    };
    let e2 = AuditEntry {
        candidate_id: "z-2".into(),
        claim_id: "c-2".into(),
        context_id: "ctx-2".into(),
        membership: "InClass".into(),
        permission: Permission::REF,
        expiry_deadline: None,
        token_ids: vec![],
        provenance_hash: "hash-2".into(),
        derivation: Derivation::default(),
        emitted_at: Utc::now(),
    };
    store.record(e1);
    store.record(e2);

    let entries = store.entries();
    assert_eq!(entries.len(), 2, "audit store must hold both records");
    // Verify both are present (order may vary).
    let ids: Vec<&str> = entries.iter().map(|e| e.candidate_id.as_str()).collect();
    assert!(ids.contains(&"z-1"), "audit store missing z-1");
    assert!(ids.contains(&"z-2"), "audit store missing z-2");
}

#[test]
fn t18_compile_result_unaffected_by_audit_store_size() {
    // An audit store with many entries must not affect compile() results.
    let store = InMemoryAuditStore::default();

    // Flood the store with 1000 fake DIA entries for the same candidate.
    for i in 0..1000 {
        store.record(AuditEntry {
            candidate_id: "z-t18-flood".into(),
            claim_id: "c-t18-flood".into(),
            context_id: "ctx-t18-flood".into(),
            membership: "InClass".into(),
            permission: Permission::AAA,
            expiry_deadline: None,
            token_ids: vec![format!("tok-{i}")],
            provenance_hash: format!("hash-{i}"),
            derivation: Derivation::default(),
            emitted_at: Utc::now(),
        });
    }
    assert_eq!(store.entries().len(), 1000, "setup: 1000 audit entries");

    // Compile a context that cannot produce AAA (no valid tokens).
    let ctx = ctx_needs_g1_closed();
    let j = compile(ctx).unwrap();
    // In-class, profile defined, no valid tokens → UNS
    assert_eq!(
        j.permission,
        Permission::UNS,
        "T18: 1000 audit entries must not affect compile result; still UNS (in-class)"
    );
}

// ── T18: Audit record fields do not influence compiler ────────────────────────

#[test]
fn t18_audit_entry_cannot_be_used_as_proof_token() {
    // Simulate an attacker who serializes an AuditEntry and tries to
    // use its data as a ProofToken. The token must be rejected because
    // the audit entry does not carry a valid provenance hash or gap claims.
    let ctx_ref = ctx_needs_g1_closed();

    // Craft a ProofToken whose fields mirror the audit entry format
    // but with fabricated provenance.
    let fake_tok = ProofToken {
        token_id: "audit-laundering-attempt".into(),
        token_type: "AUDIT_ENTRY".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: "0".repeat(64), // fabricated hash — wrong
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "audit-store".into(),
        details: serde_json::json!({"source": "audit_record", "prior_permission": "DIA"}),
        is_negative_control: false,
    };

    let mut ctx = ctx_ref;
    ctx.tokens.push(fake_tok);
    let j = compile(ctx).unwrap();
    // Fake token with wrong provenance → PROVENANCE_MISMATCH → REF
    assert_eq!(
        j.permission,
        Permission::REF,
        "T18: audit-laundering via fake token must be rejected (wrong provenance → REF)"
    );
}

// ── T18: Concurrent audit store writes remain safe ───────────────────────────

#[test]
fn t18_concurrent_audit_writes_are_safe() {
    use std::thread;
    let store = Arc::new(InMemoryAuditStore::default());

    let n_threads = 8;
    let n_entries_per_thread = 100;

    let handles: Vec<_> = (0..n_threads)
        .map(|t| {
            let store_clone = Arc::clone(&store);
            thread::spawn(move || {
                for i in 0..n_entries_per_thread {
                    store_clone.record(AuditEntry {
                        candidate_id: format!("z-{t}-{i}"),
                        claim_id: format!("c-{t}-{i}"),
                        context_id: format!("ctx-{t}-{i}"),
                        membership: "InClass".into(),
                        permission: Permission::DIA,
                        expiry_deadline: None,
                        token_ids: vec![],
                        provenance_hash: format!("hash-{t}-{i}"),
                        derivation: Derivation::default(),
                        emitted_at: Utc::now(),
                    });
                }
            })
        })
        .collect();

    for h in handles {
        h.join().expect("thread panicked");
    }

    let entries = store.entries();
    assert_eq!(
        entries.len(),
        n_threads * n_entries_per_thread,
        "all concurrent writes must be recorded without loss"
    );
}

// ── T19: Scientific boundary — structural soundness ≠ domain correctness ──────

#[test]
fn t19_compiler_accepts_any_valid_token_regardless_of_domain_science() {
    // A token with a "wrong" KL bound (scientifically dubious) but valid structure
    // is accepted by the compiler. The compiler does not validate domain science.
    // Domain correctness is the certifier's responsibility.
    let claim_id = "claim-t19";
    let candidate_id = "z-t19";
    let context_id = "ctx-t19";
    let allowed_use = "t19-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let ctx = ProofContext {
        claim_id: claim_id.into(),
        candidate_id: candidate_id.into(),
        context_id: context_id.into(),
        context_fingerprint: "fp-t19".into(),
        allowed_use: allowed_use.into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "calibration_gap")],
        profiles: vec![Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        }],
        tokens: vec![ProofToken {
            token_id: "tok-t19-dubious".into(),
            token_type: "CALIBRATION_TOKEN".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "dubious-certifier".into(),
            // "details" contains scientifically questionable values.
            // The compiler does not validate these — that is the certifier's job.
            details: serde_json::json!({
                "kl_bound": 9999.0,
                "comment": "This bound is nonsensical but structurally valid"
            }),
            is_negative_control: false,
        }],
        expiry: Expiry::never(),
        authority_ceiling: Permission::AAA,
        permission_ceiling: Permission::AAA,
        membership: Membership::InClass,
    };

    // The compiler accepts this token because it has correct structure and provenance.
    // T19: structural soundness is proven; domain soundness is outside scope.
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::DIA,
        "T19: structurally valid token accepted regardless of details content"
    );
}

#[test]
fn t19_compiler_does_not_validate_details_json_schema() {
    // The `details` field is an opaque JSON blob; the compiler ignores its content.
    let claim_id = "claim-t19-detail";
    let candidate_id = "z-t19-detail";
    let context_id = "ctx-t19-detail";
    let allowed_use = "t19-detail-use";
    let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

    let variants = vec![
        serde_json::Value::Null,
        serde_json::json!({}),
        serde_json::json!({"key": "value"}),
        serde_json::json!([1, 2, 3]),
        serde_json::json!({"deeply": {"nested": {"arbitrary": true}}}),
    ];

    for details in variants {
        let ctx = ProofContext {
            claim_id: claim_id.into(),
            candidate_id: candidate_id.into(),
            context_id: context_id.into(),
            context_fingerprint: "fp-t19-detail".into(),
            allowed_use: allowed_use.into(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps: vec![GapRecord::open("g1", "calibration_gap")],
            profiles: vec![Profile {
                permission: Permission::DIA,
                required_gaps: vec![GapRequirement {
                    gap_id: "g1".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                }],
            }],
            tokens: vec![ProofToken {
                token_id: "tok-detail".into(),
                token_type: "CLOSE".into(),
                schema_version: "0.1".into(),
                status: TokenStatus::Valid,
                closes_gaps: vec!["g1".into()],
                bounds_gaps: vec![],
                provenance_hash: hash.clone(),
                issued_at: Utc::now(),
                expires_at: None,
                issuer: "test".into(),
                details,
                is_negative_control: false,
            }],
            expiry: Expiry::never(),
            authority_ceiling: Permission::AAA,
            permission_ceiling: Permission::AAA,
            membership: Membership::InClass,
        };
        let j = compile(ctx).unwrap();
        assert_eq!(
            j.permission,
            Permission::DIA,
            "T19: details content must not affect compile result"
        );
    }
}
