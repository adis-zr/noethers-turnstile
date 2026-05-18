/// Certifier trait: whatever produces a proof token.
///
/// Turnstile does not run certifiers; it consumes their output (tokens already
/// present in the [`crate::context::ProofContext`] at compile time).
/// The interface is minimal; see [`Certifier`] for the failure-mode contract.
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
        Self {
            valid: true,
            reason: None,
        }
    }

    pub fn fail(reason: impl Into<String>) -> Self {
        Self {
            valid: false,
            reason: Some(reason.into()),
        }
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
/// Implementations are domain-specific.  **Turnstile never calls either method
/// on this trait.**  `compile()` operates on a snapshot of tokens already
/// present in the [`ProofContext`]; it does not invoke certifiers.
///
/// # Failure mode contract
///
/// Because certifier calls happen entirely outside `compile()`, the integration
/// layer owns the failure policy:
///
/// - **Fail hard**: if `issue()` errors or times out, do not call `compile()`
///   (or surface the error to the caller).
/// - **Graceful degradation**: call `compile()` anyway, without the token.
///   The gap stays open and `compile()` returns the strongest permission the
///   remaining evidence supports — an honest, lower signal rather than a silent
///   failure.
///
/// Neither policy is enforced here; choose the one appropriate for your
/// system's risk tolerance.
pub trait Certifier: Send + Sync {
    /// Human-readable name of this certifier.
    fn name(&self) -> &str;

    /// Issue a new proof token from the supplied evidence.
    ///
    /// Called by the domain layer before constructing a [`ProofContext`].
    /// Not called by `compile()`.
    fn issue(&self, evidence: Evidence) -> Result<ProofToken, IssueError>;

    /// Validate an existing proof token against a proof context.
    ///
    /// Available for domain-layer use (e.g. pre-flight checks before calling
    /// `compile()`).  Not called by `compile()`.
    fn validate(&self, token: &ProofToken, ctx: &ProofContext) -> ValidationResult;
}
