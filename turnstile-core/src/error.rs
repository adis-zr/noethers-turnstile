/// TurnstileError hierarchy.
use thiserror::Error;

/// Error returned by the composition operator.
#[derive(Debug, Error)]
pub enum CompositionError {
    #[error("use conflict: contexts have incompatible allowed_use sets")]
    UseConflict,

    #[error("token conflict: token '{token_id}' exists in both contexts with different content")]
    TokenConflict { token_id: String },

    #[error("provenance conflict: hash collision with different content for token '{token_id}'")]
    ProvenanceConflict { token_id: String },

    #[error("empty composition: at least one context is required")]
    EmptyComposition,
}

/// The top-level error type for all Turnstile operations.
#[derive(Debug, Error)]
pub enum TurnstileError {
    #[error("composition failed: {0}")]
    Composition(#[from] CompositionError),

    #[error(
        "provenance mismatch: token '{token_id}' expected '{expected}' got '{actual}'"
    )]
    ProvenanceMismatch {
        token_id: String,
        expected: String,
        actual: String,
    },

    #[error(
        "schema version mismatch: token issued under '{token_version}', registry at '{registry_version}'"
    )]
    SchemaVersionMismatch {
        token_version: String,
        registry_version: String,
    },

    #[error("malformed context: {0}")]
    MalformedContext(String),

    #[error("expired: judgment expired at {deadline}")]
    Expired { deadline: String },
}
