/// Audit trail and derivation record.
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::permission::Permission;

/// A single step in the derivation of a judgment.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DerivationStep {
    /// Which phase this step belongs to (e.g. "descending_search", "authority_meet").
    pub phase: String,
    /// The permission value after this step.
    pub permission_after: Permission,
    /// Human-readable explanation for audit.
    pub note: String,
    /// IDs of tokens consulted in this step.
    pub token_ids: Vec<String>,
}

/// The derivation record for a judgment: the full audit trail from context
/// to emitted permission.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Derivation {
    pub steps: Vec<DerivationStep>,
    pub provenance_hash: String,
    pub compiled_at: Option<DateTime<Utc>>,
}

impl Derivation {
    pub fn new() -> Self {
        Self {
            steps: vec![],
            provenance_hash: String::new(),
            compiled_at: Some(Utc::now()),
        }
    }

    pub fn with_provenance(mut self, hash: impl Into<String>) -> Self {
        self.provenance_hash = hash.into();
        self
    }

    pub fn push(&mut self, step: DerivationStep) {
        self.steps.push(step);
    }
}

/// Append-only audit store.  All compiled judgments are recorded here for
/// offline replay and proof-of-compliance review.
pub trait AuditStore: Send + Sync {
    fn record(&self, entry: AuditEntry);
    fn entries(&self) -> Vec<AuditEntry>;
}

/// A single audit entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEntry {
    pub candidate_id: String,
    pub claim_id: String,
    pub context_id: String,
    pub membership: String,
    pub permission: Permission,
    pub expiry_deadline: Option<DateTime<Utc>>,
    pub token_ids: Vec<String>,
    pub provenance_hash: String,
    pub derivation: Derivation,
    pub emitted_at: DateTime<Utc>,
}

/// In-memory audit store (for testing and single-process deployments).
#[derive(Debug, Default)]
pub struct InMemoryAuditStore {
    entries: std::sync::Mutex<Vec<AuditEntry>>,
}

impl AuditStore for InMemoryAuditStore {
    fn record(&self, entry: AuditEntry) {
        self.entries.lock().unwrap().push(entry);
    }

    fn entries(&self) -> Vec<AuditEntry> {
        self.entries.lock().unwrap().clone()
    }
}
