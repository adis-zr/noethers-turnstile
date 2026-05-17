/// EC-008 — Concurrent audit store integrity.
///
/// The `AuditStore` trait is `Send + Sync`, meaning multiple threads may record
/// judgments concurrently.  `InMemoryAuditStore` must:
///   - Accept concurrent `record()` calls without data loss or panic.
///   - Return all recorded entries from `entries()` with no duplicates or missing items.
///   - Maintain deterministic entry count under concurrent load.
///
/// This test suite verifies thread safety under concurrent write workloads.
///
/// Tests:
///   - Sequential record/retrieve baseline
///   - 8 threads × 100 records: all entries present (no data loss)
///   - 16 threads × 50 records: count is exactly 800 (no duplicates, no loss)
///   - entries() is consistent after concurrent writes (no partial state visible)
use std::sync::Arc;
use std::thread;

use chrono::Utc;
use turnstile_core::{
    audit::{AuditEntry, AuditStore, Derivation, InMemoryAuditStore},
    permission::Permission,
};

fn make_entry(id: usize) -> AuditEntry {
    AuditEntry {
        candidate_id: format!("z-{id}"),
        claim_id: format!("claim-{id}"),
        context_id: format!("ctx-{id}"),
        membership: "InClass".into(),
        permission: Permission::DIA,
        expiry_deadline: None,
        token_ids: vec![format!("tok-{id}")],
        provenance_hash: format!("hash-{id:064}"),
        derivation: Derivation::default(),
        emitted_at: Utc::now(),
    }
}

// ── Sequential baseline ──────────────────────────────────────────────────────

#[test]
fn sequential_record_and_retrieve() {
    let store = InMemoryAuditStore::default();
    for i in 0..10 {
        store.record(make_entry(i));
    }
    let entries = store.entries();
    assert_eq!(entries.len(), 10, "sequential: all 10 entries must be present");
}

// ── Concurrent writes: no data loss ─────────────────────────────────────────

#[test]
fn concurrent_writes_no_data_loss() {
    let store = Arc::new(InMemoryAuditStore::default());
    let num_threads = 8;
    let records_per_thread = 100;

    let handles: Vec<_> = (0..num_threads)
        .map(|t| {
            let store = Arc::clone(&store);
            thread::spawn(move || {
                for i in 0..records_per_thread {
                    store.record(make_entry(t * records_per_thread + i));
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
        num_threads * records_per_thread,
        "concurrent writes: all {} entries must be present (got {})",
        num_threads * records_per_thread,
        entries.len()
    );
}

// ── Concurrent writes: exact count, no duplicates or loss ────────────────────

#[test]
fn concurrent_writes_exact_count() {
    let store = Arc::new(InMemoryAuditStore::default());
    let num_threads = 16;
    let records_per_thread = 50;
    let expected = num_threads * records_per_thread;

    let handles: Vec<_> = (0..num_threads)
        .map(|t| {
            let store = Arc::clone(&store);
            thread::spawn(move || {
                for i in 0..records_per_thread {
                    store.record(make_entry(t * 1000 + i));
                }
            })
        })
        .collect();

    for h in handles {
        h.join().unwrap();
    }

    assert_eq!(
        store.entries().len(),
        expected,
        "exact count: expected {expected} entries"
    );
}

// ── Concurrent read/write: entries() always returns consistent state ──────────

#[test]
fn concurrent_read_write_entries_consistent() {
    let store = Arc::new(InMemoryAuditStore::default());
    let writer_threads = 4;
    let reader_threads = 4;
    let records_per_writer = 25;

    // Spawn readers that call entries() continuously while writers are active.
    let stop_flag = Arc::new(std::sync::atomic::AtomicBool::new(false));

    let reader_handles: Vec<_> = (0..reader_threads)
        .map(|_| {
            let store = Arc::clone(&store);
            let stop = Arc::clone(&stop_flag);
            thread::spawn(move || {
                while !stop.load(std::sync::atomic::Ordering::Relaxed) {
                    let _ = store.entries(); // must not panic
                }
            })
        })
        .collect();

    let writer_handles: Vec<_> = (0..writer_threads)
        .map(|t| {
            let store = Arc::clone(&store);
            thread::spawn(move || {
                for i in 0..records_per_writer {
                    store.record(make_entry(t * 1000 + i));
                }
            })
        })
        .collect();

    for h in writer_handles {
        h.join().unwrap();
    }
    stop_flag.store(true, std::sync::atomic::Ordering::Relaxed);
    for h in reader_handles {
        h.join().unwrap();
    }

    // After all writers done, count must be exact.
    assert_eq!(
        store.entries().len(),
        writer_threads * records_per_writer,
        "after concurrent read/write: entry count must be exact"
    );
}
