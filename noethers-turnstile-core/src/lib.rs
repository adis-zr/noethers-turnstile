//! # turnstile-core
//!
//! Pure Rust implementation of the admissibility compiler.
//!
//! The judgment form is:
//! ```text
//! Γ ⊢ z : p until ε
//! ```
//!
//! The compiler is parameterized over a [`PermissionChain`] — a validated
//! total order of named levels with role anchors (Bottom, ExpiryFloor, Refused,
//! Unsatisfied, BlockerThreshold, Top). The default chain (the historical
//! 12-level `OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA < REV < AEX < ALR < AAA`)
//! is available via [`PermissionChain::default_chain`].
//!
//! See `docs/specs/permission_chain_refactor_spec.md` for the full design.
//!
//! ## Quick start (default chain)
//!
//! ```rust
//! use noethers_turnstile_core::{
//!     context::{Membership, ProofContext, Scope},
//!     compiler::compile,
//!     expiry::Expiry,
//!     default_levels,
//! };
//!
//! let ctx = ProofContext {
//!     claim_id: "my-claim".into(),
//!     candidate_id: "z-001".into(),
//!     context_id: "ctx-001".into(),
//!     context_fingerprint: "fp-001".into(),
//!     allowed_use: "diagnostics".into(),
//!     disallowed_uses: vec![],
//!     scope: Scope::default(),
//!     gaps: vec![],
//!     profiles: vec![],
//!     tokens: vec![],
//!     expiry: Expiry::never(),
//!     authority_ceiling: None,
//!     permission_ceiling: None,
//!     expected_chain_hash: None,
//!     membership: Membership::InClass,
//! };
//!
//! let judgment = compile(ctx).unwrap();
//! // No profiles registered → OOC.
//! assert_eq!(judgment.permission, default_levels::OOC());
//! ```

pub mod audit;
pub mod certifier;
pub mod compiler;
pub mod composition;
pub mod context;
pub mod default_levels;
pub mod error;
pub mod expiry;
pub mod gap;
pub mod permission;
pub mod registry;
pub mod token;

// Re-export the most commonly used types at the crate root.
pub use compiler::{compile, compile_at, compile_at_with_chain, compile_with_chain, Judgment};
pub use composition::{
    compose, compose_judgments, compose_n, compose_n_with_chain, compose_with_chain,
};
pub use context::ProofContext;
pub use expiry::{Expiry, LiveJudgment, RuntimeContext};
pub use permission::{
    AuditError, ChainError, ChainHash, ChainRegistry, ChainRole, InMemoryChainRegistry,
    NameRejectionReason, Permission, PermissionChain, MAX_LEVELS, MAX_NAME_LEN,
};
pub use token::NegativeControlStatus;

/// Verify that a judgment's chain_hash resolves in the given registry, and
/// that the resolved chain re-hashes to the same value.
///
/// This is the audit-time check that converts publication from prose to API.
/// See §3.3 mechanism 4 of `docs/specs/permission_chain_refactor_spec.md`.
pub fn verify_published<R: ChainRegistry>(
    judgment: &Judgment,
    registry: &R,
) -> Result<(), AuditError> {
    match registry.lookup(&judgment.chain_hash) {
        None => Err(AuditError::NotPublished {
            hash: judgment.chain_hash,
        }),
        Some(chain) => {
            let actual = chain.chain_hash();
            if actual == judgment.chain_hash {
                Ok(())
            } else {
                Err(AuditError::HashMismatch {
                    expected: judgment.chain_hash,
                    actual,
                })
            }
        }
    }
}
