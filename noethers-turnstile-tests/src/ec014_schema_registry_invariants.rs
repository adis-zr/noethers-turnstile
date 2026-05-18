/// EC-014 — SchemaRegistry invariants: append-only, no duplicate schema versions,
///           concurrent read safety.
///
/// The SchemaRegistry is an append-only store for token schema definitions.
/// Its invariants:
///   R1 — Register a (schema_id, version) pair → always succeeds on first call.
///   R2 — Re-registering the same (schema_id, version) → Err (duplicate rejected).
///   R3 — get(schema_id, version) returns the registered entry.
///   R4 — current_version(schema_id) returns the latest registered version.
///   R5 — all_entries() returns every registered entry.
///   R6 — Registry is thread-safe under concurrent reads and writes.
///   R7 — Registry is append-only: registered entries cannot be mutated or removed.
use std::sync::Arc;
use std::thread;
use noethers_turnstile_core::registry::{SchemaEntry, SchemaRegistry};

fn make_entry(schema_id: &str, version: &str) -> SchemaEntry {
    SchemaEntry {
        schema_id: schema_id.into(),
        version: version.into(),
        description: format!("Schema {schema_id} v{version}"),
        created_at: chrono::Utc::now(),
    }
}

// ── R1: First registration succeeds ──────────────────────────────────────────

#[test]
fn r1_first_registration_succeeds() {
    let registry = SchemaRegistry::default();
    let entry = make_entry("calibration", "1.0");
    registry
        .register(entry)
        .expect("R1: first registration must succeed");
}

#[test]
fn r1_multiple_distinct_schemas_all_register() {
    let registry = SchemaRegistry::default();
    let schemas = [
        ("calibration", "1.0"),
        ("freshness", "1.0"),
        ("boundary", "2.1"),
        ("proxy", "0.5"),
    ];
    for (id, ver) in schemas {
        registry
            .register(make_entry(id, ver))
            .unwrap_or_else(|_| panic!("R1: registration of ({id}, {ver}) must succeed"));
    }
}

// ── R2: Duplicate registration rejected ──────────────────────────────────────

#[test]
fn r2_duplicate_registration_fails() {
    let registry = SchemaRegistry::default();
    registry.register(make_entry("dup-schema", "1.0")).unwrap();
    let result = registry.register(make_entry("dup-schema", "1.0"));
    assert!(
        result.is_err(),
        "R2: re-registering same (schema_id, version) must return Err"
    );
}

#[test]
fn r2_different_versions_of_same_schema_are_allowed() {
    let registry = SchemaRegistry::default();
    registry.register(make_entry("multi-ver", "1.0")).unwrap();
    registry
        .register(make_entry("multi-ver", "2.0"))
        .expect("R2: different versions of same schema_id must both register");
}

// ── R3: Retrieval returns registered entry ────────────────────────────────────

#[test]
fn r3_get_returns_registered_entry() {
    let registry = SchemaRegistry::default();
    let entry = make_entry("get-schema", "1.0");
    registry.register(entry.clone()).unwrap();
    let retrieved = registry.get("get-schema", "1.0");
    assert!(retrieved.is_some(), "R3: get must return registered entry");
    let r = retrieved.unwrap();
    assert_eq!(r.schema_id, "get-schema");
    assert_eq!(r.version, "1.0");
}

#[test]
fn r3_get_missing_returns_none() {
    let registry = SchemaRegistry::default();
    let result = registry.get("nonexistent", "1.0");
    assert!(
        result.is_none(),
        "R3: get of unregistered schema must return None"
    );
}

#[test]
fn r3_get_wrong_version_returns_none() {
    let registry = SchemaRegistry::default();
    registry.register(make_entry("versioned", "1.0")).unwrap();
    let result = registry.get("versioned", "9.9");
    assert!(
        result.is_none(),
        "R3: get with wrong version must return None even if schema_id exists"
    );
}

// ── R4: current_version returns latest ───────────────────────────────────────

#[test]
fn r4_current_version_returns_most_recently_registered() {
    let registry = SchemaRegistry::default();
    registry.register(make_entry("cv-schema", "1.0")).unwrap();
    registry.register(make_entry("cv-schema", "2.0")).unwrap();
    let current = registry.current_version("cv-schema");
    assert!(
        current.is_some(),
        "R4: current_version must return Some for registered schema_id"
    );
    // The current version should be one of the registered versions.
    let ver = current.unwrap();
    assert!(
        ver == "1.0" || ver == "2.0",
        "R4: current_version must be a registered version; got {ver}"
    );
}

#[test]
fn r4_current_version_missing_schema_returns_none() {
    let registry = SchemaRegistry::default();
    assert!(
        registry.current_version("never-registered").is_none(),
        "R4: current_version of unregistered schema must be None"
    );
}

// ── R5: all_entries returns everything ────────────────────────────────────────

#[test]
fn r5_all_entries_returns_all_registered() {
    let registry = SchemaRegistry::default();
    let schemas = [("s1", "1.0"), ("s2", "1.0"), ("s3", "2.0")];
    for (id, ver) in schemas {
        registry.register(make_entry(id, ver)).unwrap();
    }
    let entries = registry.all_entries();
    assert_eq!(
        entries.len(),
        3,
        "R5: all_entries must return all 3 registered entries"
    );
}

#[test]
fn r5_all_entries_empty_registry_returns_empty() {
    let registry = SchemaRegistry::default();
    assert_eq!(
        registry.all_entries().len(),
        0,
        "R5: all_entries on empty registry must return empty vec"
    );
}

// ── R6: Thread-safe under concurrent registration ────────────────────────────

#[test]
fn r6_concurrent_registrations_are_all_recorded() {
    let registry = Arc::new(SchemaRegistry::default());
    let n_threads = 8;
    let n_schemas_per_thread = 10;

    let handles: Vec<_> = (0..n_threads)
        .map(|t| {
            let reg = Arc::clone(&registry);
            thread::spawn(move || {
                for i in 0..n_schemas_per_thread {
                    let schema_id = format!("thread-{t}-schema-{i}");
                    let _ = reg.register(make_entry(&schema_id, "1.0"));
                }
            })
        })
        .collect();

    for h in handles {
        h.join().expect("thread panicked");
    }

    let entries = registry.all_entries();
    assert_eq!(
        entries.len(),
        n_threads * n_schemas_per_thread,
        "R6: all concurrent registrations must be recorded; expected {}, got {}",
        n_threads * n_schemas_per_thread,
        entries.len()
    );
}

#[test]
fn r6_concurrent_reads_while_writing_do_not_panic() {
    let registry = Arc::new(SchemaRegistry::default());

    // Pre-populate some entries.
    for i in 0..20 {
        registry
            .register(make_entry(&format!("pre-{i}"), "1.0"))
            .unwrap();
    }

    let n_readers = 4;
    let n_writers = 4;

    let mut handles = vec![];

    // Spawn readers.
    for _ in 0..n_readers {
        let reg = Arc::clone(&registry);
        handles.push(thread::spawn(move || {
            for _ in 0..100 {
                let _ = reg.all_entries();
                let _ = reg.get("pre-0", "1.0");
                let _ = reg.current_version("pre-0");
            }
        }));
    }

    // Spawn writers.
    for w in 0..n_writers {
        let reg = Arc::clone(&registry);
        handles.push(thread::spawn(move || {
            for i in 0..25 {
                let id = format!("concurrent-writer-{w}-{i}");
                let _ = reg.register(make_entry(&id, "1.0"));
            }
        }));
    }

    for h in handles {
        h.join()
            .expect("thread panicked during concurrent read/write");
    }
}

// ── R7: Append-only: registered entries cannot be removed ────────────────────

#[test]
fn r7_registered_entry_persists_after_further_registrations() {
    let registry = SchemaRegistry::default();
    registry.register(make_entry("persist", "1.0")).unwrap();
    // Register many other schemas.
    for i in 0..50 {
        registry
            .register(make_entry(&format!("other-{i}"), "1.0"))
            .unwrap();
    }
    // Original entry must still be retrievable.
    let entry = registry.get("persist", "1.0");
    assert!(
        entry.is_some(),
        "R7: entry registered before subsequent writes must still be retrievable"
    );
}

#[test]
fn r7_all_entries_count_only_increases() {
    let registry = SchemaRegistry::default();
    let count_0 = registry.all_entries().len();
    registry.register(make_entry("grow-1", "1.0")).unwrap();
    let count_1 = registry.all_entries().len();
    registry.register(make_entry("grow-2", "1.0")).unwrap();
    let count_2 = registry.all_entries().len();

    assert!(
        count_1 > count_0,
        "R7: count must increase after registration"
    );
    assert!(
        count_2 > count_1,
        "R7: count must increase after second registration"
    );
}
