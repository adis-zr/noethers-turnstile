//! ProofContext (Γ): the full proof context for a compilation.
use serde::{Deserialize, Serialize};

use crate::expiry::Expiry;
use crate::gap::{GapRecord, Profile};
use crate::permission::{ChainHash, Permission};
use crate::token::ProofToken;

/// Scope constraints on what the judgment applies to.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Scope {
    /// Candidate IDs this judgment is valid for.  Empty = unconstrained.
    pub allowed_candidates: Vec<String>,
    /// Path prefixes this judgment is valid for.  Empty = unconstrained.
    pub allowed_paths: Vec<String>,
    /// Tool names this judgment is valid for.  Empty = unconstrained.
    pub allowed_tools: Vec<String>,
    /// Resource identifiers this judgment is valid for.  Empty = unconstrained.
    pub allowed_resources: Vec<String>,
}

impl Scope {
    /// Intersection of two scopes.  Empty = unconstrained;
    /// non-empty lists are intersected element-wise.
    pub fn intersect(self, other: Self) -> Self {
        Self {
            allowed_candidates: intersect_list(self.allowed_candidates, other.allowed_candidates),
            allowed_paths: intersect_list(self.allowed_paths, other.allowed_paths),
            allowed_tools: intersect_list(self.allowed_tools, other.allowed_tools),
            allowed_resources: intersect_list(self.allowed_resources, other.allowed_resources),
        }
    }
}

fn intersect_list(a: Vec<String>, b: Vec<String>) -> Vec<String> {
    if a.is_empty() {
        return b;
    }
    if b.is_empty() {
        return a;
    }
    let b_set: std::collections::HashSet<&str> = b.iter().map(|s| s.as_str()).collect();
    a.into_iter()
        .filter(|s| b_set.contains(s.as_str()))
        .collect()
}

/// Whether the candidate is a member of the class this compiler handles.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", content = "reason")]
pub enum Membership {
    InClass,
    OutOfClassExact,
    OutOfClassAuthorizedDeterministicWrite,
    OutOfClassNoConsequentialUse,
    OutOfClassOther(String),
}

impl Membership {
    pub fn is_in_class(&self) -> bool {
        matches!(self, Membership::InClass)
    }
}

/// Deserializer shim for ceilings: accepts both the new `Option<Permission>`
/// form and the legacy bare-string form (e.g. `"AAA"`) for wire compat.
mod ceiling_serde {
    use super::*;
    use serde::Deserializer;

    pub fn deserialize<'de, D: Deserializer<'de>>(d: D) -> Result<Option<Permission>, D::Error> {
        // Try Option<Permission> first; falls back to bare string via Permission's
        // transparent serde impl. Both shapes resolve here.
        Option::<Permission>::deserialize(d)
    }
}

/// The full proof context `Γ` that the compiler operates on.
///
/// All fields are owned — no borrowed references cross the FFI boundary.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProofContext {
    /// Identifier of the claim being evaluated.
    pub claim_id: String,
    /// Identifier of the candidate output `z`.
    pub candidate_id: String,
    /// Runtime context identifier.
    pub context_id: String,
    /// Fingerprint of the runtime context (for LiveJudgment revalidation).
    pub context_fingerprint: String,
    /// The primary allowed use (enters the provenance hash).
    pub allowed_use: String,
    /// Uses that are explicitly disallowed (union on composition).
    pub disallowed_uses: Vec<String>,
    /// Scope constraints.
    pub scope: Scope,
    /// All gaps in this context, keyed by gap_id.
    pub gaps: Vec<GapRecord>,
    /// Permission profiles.
    pub profiles: Vec<Profile>,
    /// Proof tokens supplied for this context.
    pub tokens: Vec<ProofToken>,
    /// Expiry constraint on any judgment compiled from this context.
    pub expiry: Expiry,
    /// Structural delegation ceiling — the maximum permission any certifier in
    /// the delegation chain is authorized to grant. `None` means no ceiling
    /// (resolves to the chain's top at compile time).
    #[serde(default, deserialize_with = "ceiling_serde::deserialize")]
    pub authority_ceiling: Option<Permission>,
    /// Non-promotion ceiling — set by `compose()` to `meet(compile(g1), compile(g2))`
    /// (T9). `None` means no ceiling.
    #[serde(default, deserialize_with = "ceiling_serde::deserialize")]
    pub permission_ceiling: Option<Permission>,
    /// Class membership of the candidate.
    pub membership: Membership,
    /// If `Some`, the compiler must be supplied a chain whose `chain_hash`
    /// matches; otherwise compile fails with `MalformedContext`. This pins a
    /// context to a specific chain at authoring time so name-collisions on a
    /// foreign chain cannot silently reinterpret it.
    #[serde(default)]
    pub expected_chain_hash: Option<ChainHash>,
}

impl ProofContext {
    /// Look up a gap record by gap_id.
    pub fn find_gap(&self, gap_id: &str) -> Option<&GapRecord> {
        self.gaps.iter().find(|g| g.gap_id == gap_id)
    }

    /// Look up all tokens that close or bound a given gap_id.
    pub fn tokens_for_gap<'a>(&'a self, gap_id: &'a str) -> impl Iterator<Item = &'a ProofToken> {
        self.tokens.iter().filter(move |t| {
            t.closes_gaps.iter().any(|g| g == gap_id) || t.bounds_gaps.iter().any(|g| g == gap_id)
        })
    }

    /// Compute the canonical provenance hash for this context.
    pub fn provenance_hash(&self) -> String {
        crate::token::compute_provenance_hash(
            &self.claim_id,
            &self.candidate_id,
            &self.context_id,
            &self.allowed_use,
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn scope_intersect_empty_means_unconstrained() {
        let a = Scope {
            allowed_tools: vec![],
            ..Default::default()
        };
        let b = Scope {
            allowed_tools: vec!["hammer".into()],
            ..Default::default()
        };
        let result = a.intersect(b);
        assert_eq!(result.allowed_tools, vec!["hammer"]);
    }

    #[test]
    fn scope_intersect_non_empty() {
        let a = Scope {
            allowed_tools: vec!["a".into(), "b".into()],
            ..Default::default()
        };
        let b = Scope {
            allowed_tools: vec!["b".into(), "c".into()],
            ..Default::default()
        };
        let result = a.intersect(b);
        assert_eq!(result.allowed_tools, vec!["b"]);
    }

    #[test]
    fn membership_in_class() {
        assert!(Membership::InClass.is_in_class());
        assert!(!Membership::OutOfClassExact.is_in_class());
    }

    #[test]
    fn legacy_string_ceiling_deserializes() {
        // Pre-refactor wire format used bare "AAA" string. Confirm it still
        // deserializes correctly.
        let raw = r#"{
            "claim_id": "c",
            "candidate_id": "z",
            "context_id": "ctx",
            "context_fingerprint": "fp",
            "allowed_use": "use",
            "disallowed_uses": [],
            "scope": {"allowed_candidates":[],"allowed_paths":[],"allowed_tools":[],"allowed_resources":[]},
            "gaps": [],
            "profiles": [],
            "tokens": [],
            "expiry": {"deadline":null,"reason":null},
            "authority_ceiling": "AAA",
            "permission_ceiling": "AAA",
            "membership": {"kind":"InClass"}
        }"#;
        let ctx: ProofContext = serde_json::from_str(raw).expect("legacy wire format");
        assert_eq!(ctx.authority_ceiling.unwrap().as_str(), "AAA");
        assert_eq!(ctx.permission_ceiling.unwrap().as_str(), "AAA");
    }

    #[test]
    fn missing_ceiling_deserializes_as_none() {
        let raw = r#"{
            "claim_id": "c",
            "candidate_id": "z",
            "context_id": "ctx",
            "context_fingerprint": "fp",
            "allowed_use": "use",
            "disallowed_uses": [],
            "scope": {"allowed_candidates":[],"allowed_paths":[],"allowed_tools":[],"allowed_resources":[]},
            "gaps": [],
            "profiles": [],
            "tokens": [],
            "expiry": {"deadline":null,"reason":null},
            "membership": {"kind":"InClass"}
        }"#;
        let ctx: ProofContext = serde_json::from_str(raw).expect("missing ceilings");
        assert!(ctx.authority_ceiling.is_none());
        assert!(ctx.permission_ceiling.is_none());
    }
}
