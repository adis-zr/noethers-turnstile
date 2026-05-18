//! # turnstile-core
//!
//! Pure Rust implementation of the admissibility compiler.
//!
//! The judgment form is:
//! ```text
//! Γ ⊢ z : p until ε
//! ```
//!
//! The permission chain (total order, OOC=bottom, AAA=top):
//! `OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA < REV < AEX < ALR < AAA`
//!
//! ## Quick start
//!
//! ```rust
//! use turnstile_core::{
//!     context::{Membership, ProofContext, Scope},
//!     compiler::compile,
//!     expiry::Expiry,
//!     permission::Permission,
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
//!     authority_ceiling: Permission::AAA,
//!     permission_ceiling: Permission::AAA,
//!     membership: Membership::InClass,
//! };
//!
//! let judgment = compile(ctx).unwrap();
//! // No profiles registered → OOC.
//! assert_eq!(judgment.permission, Permission::OOC);
//! ```

pub mod audit;
pub mod certifier;
pub mod compiler;
pub mod composition;
pub mod context;
pub mod error;
pub mod expiry;
pub mod gap;
pub mod permission;
pub mod registry;
pub mod token;

// Re-export the most commonly used types at the crate root.
pub use compiler::{compile, Judgment};
pub use composition::{compose, compose_n};
pub use context::ProofContext;
pub use expiry::{Expiry, LiveJudgment, RuntimeContext};
pub use permission::Permission;
pub use token::NegativeControlStatus;
