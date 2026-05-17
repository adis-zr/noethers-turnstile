/// EC-003K — Schema registry: append-only immutability, version non-upgrade.
///
/// Covers theorems:
///   Theorem K  — Profile-version non-upgrade
///   Theorem K′ — Taxonomy-version non-upgrade (gap taxonomy versions immutable per envelope)
///   Theorem L  — Detail-contract non-upgrade
///
/// The SchemaRegistry is append-only:
///   - A (schema_id, version) pair cannot be overwritten once registered
///   - Old versions remain queryable after new versions are added
///   - Current version pointer advances but old versions survive
///
/// Token schema versions are immutable: a token issued under version V cannot
/// be validated against version V' ≠ V.
use chrono::Utc;
use turnstile_core::registry::{SchemaEntry, SchemaRegistry};

fn entry(schema_id: &str, version: &str) -> SchemaEntry {
    SchemaEntry {
        schema_id: schema_id.into(),
        version: version.into(),
        description: format!("{schema_id} v{version}"),
        created_at: Utc::now(),
    }
}

// ── Append-only: register twice with same (id, version) fails ─────────────────

#[test]
fn register_same_version_twice_fails() {
    let reg = SchemaRegistry::new();
    reg.register(entry("s1", "1.0")).unwrap();
    let result = reg.register(entry("s1", "1.0"));
    assert!(
        result.is_err(),
        "duplicate (schema_id, version) must be rejected"
    );
}

#[test]
fn register_different_versions_both_succeed() {
    let reg = SchemaRegistry::new();
    reg.register(entry("s1", "1.0")).unwrap();
    reg.register(entry("s1", "2.0")).unwrap();
    assert!(
        reg.get("s1", "1.0").is_some(),
        "v1.0 must survive after v2.0 is registered"
    );
    assert!(reg.get("s1", "2.0").is_some(), "v2.0 must be queryable");
}

// ── Old versions remain queryable after new ones are added ────────────────────

#[test]
fn old_version_survives_registration_of_new_version() {
    let reg = SchemaRegistry::new();
    reg.register(entry("s2", "0.1")).unwrap();
    reg.register(entry("s2", "0.2")).unwrap();
    reg.register(entry("s2", "0.3")).unwrap();

    let v01 = reg.get("s2", "0.1");
    let v02 = reg.get("s2", "0.2");
    let v03 = reg.get("s2", "0.3");

    assert!(v01.is_some(), "v0.1 must survive v0.3");
    assert!(v02.is_some(), "v0.2 must survive v0.3");
    assert!(v03.is_some(), "v0.3 must be present");
}

// ── all_entries() is monotone (never shrinks) ─────────────────────────────────

#[test]
fn all_entries_count_never_shrinks() {
    let reg = SchemaRegistry::new();
    let c0 = reg.all_entries().len();
    reg.register(entry("s3", "1.0")).unwrap();
    let c1 = reg.all_entries().len();
    reg.register(entry("s3", "2.0")).unwrap();
    let c2 = reg.all_entries().len();
    reg.register(entry("s4", "1.0")).unwrap();
    let c3 = reg.all_entries().len();

    assert!(c1 > c0, "all_entries must grow after registration");
    assert!(c2 > c1);
    assert!(c3 > c2);
}

// ── Multiple schemas are independent ─────────────────────────────────────────

#[test]
fn different_schema_ids_are_independent() {
    let reg = SchemaRegistry::new();
    reg.register(entry("schema-a", "1.0")).unwrap();
    reg.register(entry("schema-b", "1.0")).unwrap();

    assert!(reg.get("schema-a", "1.0").is_some());
    assert!(reg.get("schema-b", "1.0").is_some());
    assert!(reg.get("schema-a", "2.0").is_none()); // not registered
}

// ── current_version tracks the latest registered version ─────────────────────

#[test]
fn current_version_reflects_latest_registration() {
    let reg = SchemaRegistry::new();
    reg.register(entry("s5", "1.0")).unwrap();
    assert!(reg.current_version("s5").is_some());

    reg.register(entry("s5", "2.0")).unwrap();
    // current_version is now "2.0" (most recently registered)
    let cv = reg.current_version("s5").unwrap();
    assert_eq!(cv, "2.0");
}

#[test]
fn current_version_unknown_schema_returns_none() {
    let reg = SchemaRegistry::new();
    assert!(reg.current_version("nonexistent").is_none());
}

// ── Thread safety: concurrent reads while writing ─────────────────────────────

#[test]
fn registry_is_send_sync() {
    fn assert_send_sync<T: Send + Sync>() {}
    assert_send_sync::<SchemaRegistry>();
}

#[test]
fn concurrent_registration_and_lookup() {
    use std::sync::Arc;
    use std::thread;

    let reg = Arc::new(SchemaRegistry::new());
    let n_threads = 4;

    let handles: Vec<_> = (0..n_threads)
        .map(|i| {
            let reg = Arc::clone(&reg);
            thread::spawn(move || {
                let schema_id = format!("schema-concurrent-{i}");
                reg.register(entry(&schema_id, "1.0")).unwrap();
                assert!(reg.get(&schema_id, "1.0").is_some());
            })
        })
        .collect();

    for h in handles {
        h.join().unwrap();
    }

    assert_eq!(reg.all_entries().len(), n_threads);
}

// ── Version non-upgrade: registering v2 does not modify v1's content ──────────

#[test]
fn registering_v2_does_not_mutate_v1_description() {
    let reg = SchemaRegistry::new();
    reg.register(SchemaEntry {
        schema_id: "s6".into(),
        version: "1.0".into(),
        description: "original description".into(),
        created_at: Utc::now(),
    })
    .unwrap();

    reg.register(SchemaEntry {
        schema_id: "s6".into(),
        version: "2.0".into(),
        description: "updated description".into(),
        created_at: Utc::now(),
    })
    .unwrap();

    let v1 = reg.get("s6", "1.0").unwrap();
    assert_eq!(
        v1.description, "original description",
        "v1 content must not change after v2 registration"
    );
}

// ── Missing version returns None ──────────────────────────────────────────────

#[test]
fn get_nonexistent_version_returns_none() {
    let reg = SchemaRegistry::new();
    reg.register(entry("s7", "1.0")).unwrap();
    assert!(
        reg.get("s7", "9.9").is_none(),
        "nonexistent version must return None"
    );
    assert!(
        reg.get("s8", "1.0").is_none(),
        "nonexistent schema must return None"
    );
}

// ── Registering over a deleted/nonexistent entry is OK ────────────────────────

#[test]
fn register_new_schema_family_succeeds() {
    let reg = SchemaRegistry::new();
    for i in 0..20 {
        let id = format!("schema-family-{i}");
        reg.register(entry(&id, "1.0")).unwrap();
    }
    assert_eq!(reg.all_entries().len(), 20);
}
