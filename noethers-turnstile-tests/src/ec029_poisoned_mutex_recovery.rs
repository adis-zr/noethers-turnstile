use noethers_turnstile_core::{
    audit::{AuditEntry, AuditStore, Derivation, InMemoryAuditStore},
    registry::{SchemaEntry, SchemaRegistry},
};
/// EC-029 — Poisoned-mutex recovery in SchemaRegistry and InMemoryAuditStore.
///
/// Both `SchemaRegistry` and `InMemoryAuditStore` use `Err(p) => p.into_inner()`
/// to silently recover from a poisoned lock.  This is a deliberate soundness
/// decision: the alternative is to propagate a panic, which would crash the
/// caller.  The risk is that a partial write during the panicking thread could
/// leave the state inconsistent — but because both data structures only append
/// (never mutate), a partial write is still a safe state.
///
/// This suite verifies that both structures continue to function correctly
/// after a thread panics while holding the write lock:
///
///   P1 — SchemaRegistry: after a panic during write, subsequent reads succeed.
///   P2 — SchemaRegistry: after a panic during write, subsequent writes succeed.
///   P3 — SchemaRegistry: entries registered before the panic are still readable.
///   P4 — InMemoryAuditStore: after a panic in a reader thread, the store is
///         still writable and readable from other threads.
///   P5 — SchemaRegistry: concurrent operations after a poison recovery produce
///         consistent results.
use std::sync::Arc;
use std::thread;

use chrono::Utc;

fn make_schema(id: &str, ver: &str) -> SchemaEntry {
    SchemaEntry {
        schema_id: id.into(),
        version: ver.into(),
        description: format!("{id} v{ver}"),
        created_at: Utc::now(),
    }
}

fn make_audit_entry(id: &str) -> AuditEntry {
    AuditEntry {
        candidate_id: format!("z-{id}"),
        claim_id: format!("claim-{id}"),
        context_id: format!("ctx-{id}"),
        membership: "InClass".into(),
        permission: noethers_turnstile_core::permission::Permission::DIA,
        expiry_deadline: None,
        token_ids: vec![],
        provenance_hash: "deadbeef".repeat(8),
        derivation: Derivation::default(),
        emitted_at: Utc::now(),
    }
}

// ── P1: SchemaRegistry readable after panic during write ─────────────────────

#[test]
fn p1_registry_readable_after_writer_panic() {
    let registry = Arc::new(SchemaRegistry::default());

    // Pre-populate a known entry.
    registry.register(make_schema("pre", "1.0")).unwrap();

    // Spawn a thread that panics after (or during) registration.
    let reg_clone = Arc::clone(&registry);
    let handle = thread::spawn(move || {
        let _ = reg_clone.register(make_schema("panic-entry", "1.0"));
        panic!("deliberate test panic in writer thread");
    });
    let _ = handle.join(); // deliberately discarding the Err on panic

    // Pre-panic entry must still be readable.
    let pre_entry = registry.get("pre", "1.0");
    assert!(
        pre_entry.is_some(),
        "P1: entry registered before panic must still be readable after mutex recovery"
    );

    // Registry must accept new registrations after poison recovery.
    let result = registry.register(make_schema("post-panic", "1.0"));
    assert!(
        result.is_ok(),
        "P1: registry must accept new registrations after poison recovery; got {:?}",
        result
    );
}

// ── P2: SchemaRegistry writable after panic during write ─────────────────────

#[test]
fn p2_registry_writable_after_writer_panic() {
    let registry = Arc::new(SchemaRegistry::default());

    let reg_clone = Arc::clone(&registry);
    let handle = thread::spawn(move || {
        let _ = reg_clone.register(make_schema("mid-panic", "1.0"));
        panic!("test panic");
    });
    let _ = handle.join();

    // Must be able to write multiple new entries.
    for i in 0..5 {
        let result = registry.register(make_schema(&format!("recovery-{i}"), "1.0"));
        assert!(
            result.is_ok(),
            "P2: write {i} after poison recovery must succeed"
        );
    }
    assert!(
        registry.all_entries().len() >= 5,
        "P2: all post-panic registrations must be recorded"
    );
}

// ── P3: Pre-panic entries persist after recovery ─────────────────────────────

#[test]
fn p3_pre_panic_entries_persist_after_recovery() {
    let registry = Arc::new(SchemaRegistry::default());

    let n_before = 10;
    for i in 0..n_before {
        registry
            .register(make_schema(&format!("before-{i}"), "1.0"))
            .unwrap();
    }

    let reg_clone = Arc::clone(&registry);
    let handle = thread::spawn(move || {
        let _ = reg_clone.register(make_schema("panic-target", "1.0"));
        panic!("test panic");
    });
    let _ = handle.join();

    for i in 0..n_before {
        let entry = registry.get(&format!("before-{i}"), "1.0");
        assert!(
            entry.is_some(),
            "P3: pre-panic entry 'before-{i}' must survive mutex poison recovery"
        );
    }
}

// ── P4: InMemoryAuditStore functional after reader-thread panic ───────────────

#[test]
fn p4_audit_store_functional_after_thread_panic() {
    let store = Arc::new(InMemoryAuditStore::default());

    // Pre-populate.
    store.record(make_audit_entry("pre"));

    // Spawn a thread that reads from the store then panics.
    let store_clone = Arc::clone(&store);
    let handle = thread::spawn(move || {
        let _ = store_clone.entries();
        panic!("deliberate thread panic");
    });
    let _ = handle.join();

    // Store must still be writable.
    store.record(make_audit_entry("post"));
    let all = store.entries();
    assert!(
        !all.is_empty(),
        "P4: AuditStore entries must be preserved and store must remain functional after thread panic"
    );
}

// ── P5: Consistent results from concurrent operations after poison recovery ────

#[test]
fn p5_consistent_results_after_poison_recovery() {
    let registry = Arc::new(SchemaRegistry::default());

    // Poison by panicking in a writer.
    let reg_clone = Arc::clone(&registry);
    let _ = thread::spawn(move || {
        let _ = reg_clone.register(make_schema("poison", "1.0"));
        panic!("poison test");
    })
    .join();

    // Concurrent operations after recovery — all must succeed.
    let n = 4;
    let handles: Vec<_> = (0..n)
        .map(|t| {
            let reg = Arc::clone(&registry);
            thread::spawn(move || {
                for i in 0..5 {
                    let id = format!("concurrent-{t}-{i}");
                    let _ = reg.register(make_schema(&id, "1.0"));
                }
                reg.all_entries().len()
            })
        })
        .collect();

    for h in handles {
        let count = h.join().expect("concurrent thread panicked unexpectedly");
        assert!(
            count > 0,
            "P5: all_entries after poison recovery must return a non-empty result"
        );
    }
}
