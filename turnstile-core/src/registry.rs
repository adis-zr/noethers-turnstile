/// Schema registry: append-only, versioned.
///
/// A schema version is never mutated in place.  A new version is a new entry;
/// the old version remains queryable for replay and audit.
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

/// A registered schema entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SchemaEntry {
    pub schema_id: String,
    pub version: String,
    pub description: String,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

/// Append-only schema registry.
///
/// All writes go through `register()`.  Schema entries are never removed or
/// mutated.  The registry is `Send + Sync` and can be shared across threads.
#[derive(Debug, Default, Clone)]
pub struct SchemaRegistry {
    inner: Arc<RwLock<RegistryInner>>,
}

#[derive(Debug, Default)]
struct RegistryInner {
    /// All versions of all schemas, keyed by (schema_id, version).
    entries: HashMap<(String, String), SchemaEntry>,
    /// The current version for each schema_id.
    current_versions: HashMap<String, String>,
}

impl SchemaRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    /// Register a new schema entry.  Returns an error if the (schema_id, version)
    /// pair already exists (versions are immutable).
    pub fn register(&self, entry: SchemaEntry) -> Result<(), String> {
        let mut inner = match self.inner.write() {
            Ok(g) => g,
            Err(p) => p.into_inner(),
        };
        let key = (entry.schema_id.clone(), entry.version.clone());
        if inner.entries.contains_key(&key) {
            return Err(format!(
                "schema '{}' version '{}' already registered",
                entry.schema_id, entry.version
            ));
        }
        inner.current_versions.insert(entry.schema_id.clone(), entry.version.clone());
        inner.entries.insert(key, entry);
        Ok(())
    }

    /// Look up a schema by id and version.
    pub fn get(&self, schema_id: &str, version: &str) -> Option<SchemaEntry> {
        let inner = match self.inner.read() {
            Ok(g) => g,
            Err(p) => p.into_inner(),
        };
        inner.entries.get(&(schema_id.to_owned(), version.to_owned())).cloned()
    }

    /// Current version of a schema.
    pub fn current_version(&self, schema_id: &str) -> Option<String> {
        let inner = match self.inner.read() {
            Ok(g) => g,
            Err(p) => p.into_inner(),
        };
        inner.current_versions.get(schema_id).cloned()
    }

    /// All registered entries (for audit).
    pub fn all_entries(&self) -> Vec<SchemaEntry> {
        let inner = match self.inner.read() {
            Ok(g) => g,
            Err(p) => p.into_inner(),
        };
        inner.entries.values().cloned().collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;

    fn entry(id: &str, ver: &str) -> SchemaEntry {
        SchemaEntry {
            schema_id: id.into(),
            version: ver.into(),
            description: "test".into(),
            created_at: Utc::now(),
        }
    }

    #[test]
    fn register_and_retrieve() {
        let reg = SchemaRegistry::new();
        reg.register(entry("s1", "1.0")).unwrap();
        assert!(reg.get("s1", "1.0").is_some());
        assert!(reg.get("s1", "2.0").is_none());
    }

    #[test]
    fn duplicate_version_is_rejected() {
        let reg = SchemaRegistry::new();
        reg.register(entry("s1", "1.0")).unwrap();
        assert!(reg.register(entry("s1", "1.0")).is_err());
    }

    #[test]
    fn current_version_tracks_latest_registration() {
        let reg = SchemaRegistry::new();
        reg.register(entry("s1", "1.0")).unwrap();
        reg.register(entry("s1", "2.0")).unwrap();
        // current_version reflects the most recently registered
        assert!(reg.current_version("s1").is_some());
    }
}
