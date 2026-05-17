/// Certifier trait: whatever produces a proof token.
///
/// Turnstile does not run certifiers; it consumes their output.
/// The interface is minimal.
use crate::context::ProofContext;
use crate::token::ProofToken;

/// Error from attempting to issue a proof token.
#[derive(Debug, thiserror::Error)]
pub enum IssueError {
    #[error("evidence insufficient: {0}")]
    InsufficientEvidence(String),

    #[error("schema not registered: {schema_id}")]
    UnregisteredSchema { schema_id: String },

    #[error("internal error: {0}")]
    Internal(String),
}

/// Validation result from a certifier.
#[derive(Debug, Clone)]
pub struct ValidationResult {
    pub valid: bool,
    pub reason: Option<String>,
}

impl ValidationResult {
    pub fn ok() -> Self {
        Self { valid: true, reason: None }
    }

    pub fn fail(reason: impl Into<String>) -> Self {
        Self { valid: false, reason: Some(reason.into()) }
    }
}

/// Evidence bundle supplied to a certifier.
#[derive(Debug, Clone)]
pub struct Evidence {
    pub payload: serde_json::Value,
    pub source: String,
}

/// The certifier trait.  A certifier issues proof tokens and validates them
/// against a proof context.
///
/// Implementations are domain-specific.  Turnstile itself only calls
/// `validate()` at compile time; `issue()` is called by the domain layer.
pub trait Certifier: Send + Sync {
    /// Human-readable name of this certifier.
    fn name(&self) -> &str;

    /// Issue a new proof token from the supplied evidence.
    fn issue(&self, evidence: Evidence) -> Result<ProofToken, IssueError>;

    /// Validate an existing proof token against a proof context.
    fn validate(&self, token: &ProofToken, ctx: &ProofContext) -> ValidationResult;
}
