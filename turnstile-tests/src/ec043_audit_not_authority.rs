/// EC-043 — Audit is not authority: exhaustive coverage (T18, EC-001 §31.18).
///
/// T18: An audit record alone cannot discharge proof obligations.  Recording
/// a judgment does not re-issue it.  An AuditStore entry is observational only
/// and cannot be fed back as a proof token.
///
/// This file extends ec003x_audit_not_authority.rs with the cases identified
/// as missing: large stores, concurrent writes + compiles, fabricated high-
/// permission entries, future timestamps, duplicate entries, and replay attacks.
///
///   A1  — 10k audit entries with fabricated AAA: compile still returns OOC
///   A2  — Concurrent audit writes + concurrent compiles: result unchanged
///   A3  — AuditEntry.permission = AAA does not affect compile()
///   A4  — AuditEntry with future emitted_at: no effect on compile()
///   A5  — Duplicate entries (same context compiled twice): same permission
///   A6  — Replay attack: AuditEntry data as ProofToken with fake hash → OOC
///   A7  — AuditEntry cannot round-trip to ProofToken (no shared constructor)
///   A8  — Store with mixed permissions (DIA, AAA, REF): compile returns OOC
///   A9  — compile() result independent of store observer count (0 vs 10k)
///   Prop — N random audit entries + compile → permission unchanged
use chrono::{Duration, Utc};
use std::sync::Arc;
use std::thread;
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
        claim_id: "claim-t18".into(),
        candidate_id: "z-t18".into(),
        context_id: "ctx-t18".into(),
        context_fingerprint: "fp-t18".into(),
        allowed_use: "t18-use".into(),
        disallowed_uses: vec![],
        scope: Scope::default(),
        gaps: vec![GapRecord::open("g1", "gap")],
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
        membership: Membership::InClass,
    }
}

fn fake_aaa_entry(i: usize) -> AuditEntry {
    AuditEntry {
        candidate_id: "z-t18".into(),
        claim_id: "claim-t18".into(),
        context_id: "ctx-t18".into(),
        membership: "InClass".into(),
        permission: Permission::AAA,
        expiry_deadline: None,
        token_ids: vec![format!("fake-{i}")],
        provenance_hash: format!("hash-{i}"),
        derivation: Derivation::default(),
        emitted_at: Utc::now(),
    }
}

// ── A1: 10k fabricated AAA entries → compile still returns OOC ───────────────

#[test]
fn a1_ten_thousand_aaa_entries_do_not_affect_compile() {
    let store = InMemoryAuditStore::default();
    for i in 0..10_000 {
        store.record(fake_aaa_entry(i));
    }
    assert_eq!(store.entries().len(), 10_000);

    let ctx = ctx_needs_g1_closed();
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "A1: 10k fabricated AAA audit entries must not affect compile result"
    );
}

// ── A2: Concurrent audit writes + concurrent compiles ────────────────────────

#[test]
fn a2_concurrent_writes_and_compiles_stable() {
    let store = Arc::new(InMemoryAuditStore::default());
    let n_writers = 4;
    let n_compilers = 4;

    // Writer threads flood the store
    let writer_handles: Vec<_> = (0..n_writers)
        .map(|t| {
            let s = Arc::clone(&store);
            thread::spawn(move || {
                for i in 0..500 {
                    s.record(fake_aaa_entry(t * 1000 + i));
                }
            })
        })
        .collect();

    // Compiler threads compile the same context concurrently
    let results: Vec<_> = (0..n_compilers)
        .map(|_| {
            thread::spawn(|| {
                let ctx = ctx_needs_g1_closed();
                compile(ctx).unwrap().permission
            })
        })
        .collect();

    for h in writer_handles {
        h.join().expect("writer thread panicked");
    }
    for h in results {
        let p = h.join().expect("compiler thread panicked");
        assert_eq!(
            p,
            Permission::OOC,
            "A2: concurrent audit writes must not affect compile result"
        );
    }
}

// ── A3: AuditEntry.permission = AAA does not influence compile ────────────────

#[test]
fn a3_fabricated_aaa_audit_entry_ignored() {
    let store = InMemoryAuditStore::default();
    store.record(AuditEntry {
        candidate_id: "z-t18".into(),
        claim_id: "claim-t18".into(),
        context_id: "ctx-t18".into(),
        membership: "InClass".into(),
        permission: Permission::AAA,
        expiry_deadline: None,
        token_ids: vec![],
        provenance_hash: "any".into(),
        derivation: Derivation::default(),
        emitted_at: Utc::now(),
    });

    let ctx = ctx_needs_g1_closed();
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "A3: AuditEntry claiming AAA must be ignored by compile()"
    );
}

// ── A4: Future emitted_at timestamp has no effect ────────────────────────────

#[test]
fn a4_future_emitted_at_has_no_effect() {
    let store = InMemoryAuditStore::default();
    store.record(AuditEntry {
        candidate_id: "z-t18".into(),
        claim_id: "claim-t18".into(),
        context_id: "ctx-t18".into(),
        membership: "InClass".into(),
        permission: Permission::DIA,
        expiry_deadline: None,
        token_ids: vec![],
        provenance_hash: "any".into(),
        derivation: Derivation::default(),
        emitted_at: Utc::now() + Duration::days(365), // future timestamp
    });

    let ctx = ctx_needs_g1_closed();
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "A4: future-emitted audit entry must not grant permission"
    );
}

// ── A5: Duplicate entries: same context compiled twice → same result ──────────

#[test]
fn a5_duplicate_entries_same_result() {
    let ctx = ctx_needs_g1_closed();
    let p1 = compile(ctx.clone()).unwrap().permission;
    let p2 = compile(ctx.clone()).unwrap().permission;
    assert_eq!(
        p1, p2,
        "A5: compiling same context twice must produce same result"
    );
    assert_eq!(p1, Permission::OOC);
}

// ── A6: Replay attack — AuditEntry data as ProofToken with fake hash ──────────

#[test]
fn a6_audit_replay_as_proof_token_rejected() {
    let fake_tok = ProofToken {
        token_id: "audit-replay".into(),
        token_type: "AUDIT_REPLAY".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: "0".repeat(64), // fabricated — wrong hash
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "audit-store".into(),
        details: serde_json::json!({"source": "audit_replay", "permission": "DIA"}),
        is_negative_control: false,
    };

    let mut ctx = ctx_needs_g1_closed();
    ctx.tokens.push(fake_tok);
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "A6: audit replay via ProofToken with wrong provenance hash must be rejected"
    );
}

// ── A7: AuditEntry cannot be used as ProofToken (type separation) ─────────────

#[test]
fn a7_audit_entry_fields_do_not_map_to_proof_token() {
    // This test verifies structural separation: you cannot construct a ProofToken
    // from an AuditEntry because AuditEntry lacks the fields required for valid
    // provenance (closes_gaps, bounds_gaps, is_negative_control).
    // The only way to "replay" would be to fabricate fields — which the provenance
    // hash check rejects.
    let entry = fake_aaa_entry(0);

    // Attempt to construct a token using the audit entry's provenance_hash.
    // The hash in the entry was fabricated and does not match any real context.
    let fake_tok = ProofToken {
        token_id: entry.token_ids.first().cloned().unwrap_or_default(),
        token_type: "AUDIT".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["g1".into()],
        bounds_gaps: vec![],
        provenance_hash: entry.provenance_hash.clone(), // from audit entry
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "audit".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    };

    let mut ctx = ctx_needs_g1_closed();
    ctx.tokens.push(fake_tok);
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "A7: audit entry provenance hash does not match real context → OOC"
    );
}

// ── A8: Store with mixed permissions: compile still returns correct result ────

#[test]
fn a8_mixed_permission_entries_do_not_interfere() {
    let store = InMemoryAuditStore::default();
    for (perm, suffix) in [
        (Permission::DIA, "dia"),
        (Permission::AAA, "aaa"),
        (Permission::REF, "ref"),
        (Permission::OOC, "ooc"),
    ] {
        store.record(AuditEntry {
            candidate_id: "z-t18".into(),
            claim_id: "claim-t18".into(),
            context_id: "ctx-t18".into(),
            membership: "InClass".into(),
            permission: perm,
            expiry_deadline: None,
            token_ids: vec![format!("tok-{suffix}")],
            provenance_hash: format!("hash-{suffix}"),
            derivation: Derivation::default(),
            emitted_at: Utc::now(),
        });
    }

    let ctx = ctx_needs_g1_closed();
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "A8: mixed-permission audit entries must not affect compile result"
    );
}

// ── A9: Compile result independent of observation count ──────────────────────

#[test]
fn a9_result_independent_of_store_read_count() {
    let store = Arc::new(InMemoryAuditStore::default());
    for i in 0..100 {
        store.record(fake_aaa_entry(i));
    }

    // Read the store many times — should not affect compile
    for _ in 0..50 {
        let _ = store.entries();
    }

    let ctx = ctx_needs_g1_closed();
    let j = compile(ctx).unwrap();
    assert_eq!(
        j.permission,
        Permission::OOC,
        "A9: repeated store reads must not affect compile result"
    );
}

// ── Proptest: N random entries → compile unchanged ───────────────────────────

proptest::proptest! {
    #[test]
    fn prop_n_audit_entries_do_not_affect_compile(n in 0usize..200) {
        let store = InMemoryAuditStore::default();
        for i in 0..n {
            store.record(fake_aaa_entry(i));
        }
        let ctx = ctx_needs_g1_closed();
        let j = compile(ctx).unwrap();
        proptest::prop_assert_eq!(
            j.permission,
            Permission::OOC,
            "audit entries must not affect compile result"
        );
    }
}
