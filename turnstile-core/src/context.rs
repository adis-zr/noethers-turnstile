/// ProofContext (Γ): the full proof context for a compilation.
use serde::{Deserialize, Serialize};

use crate::expiry::Expiry;
use crate::gap::{GapRecord, Profile};
use crate::permission::Permission;
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
    a.into_iter().filter(|s| b_set.contains(s.as_str())).collect()
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
    /// Permission profiles sorted AAA → OOC (descending).
    pub profiles: Vec<Profile>,
    /// Proof tokens supplied for this context.
    pub tokens: Vec<ProofToken>,
    /// Expiry constraint on any judgment compiled from this context.
    pub expiry: Expiry,
    /// Hard authority ceiling — the compiler will never emit above this.
    pub authority_ceiling: Permission,
    /// Class membership of the candidate.
    pub membership: Membership,
}

impl ProofContext {
    /// Look up a gap record by gap_id.
    pub fn find_gap(&self, gap_id: &str) -> Option<&GapRecord> {
        self.gaps.iter().find(|g| g.gap_id == gap_id)
    }

    /// Look up all tokens that close or bound a given gap_id.
    pub fn tokens_for_gap<'a>(&'a self, gap_id: &'a str) -> impl Iterator<Item = &'a ProofToken> {
        self.tokens.iter().filter(move |t| {
            t.closes_gaps.iter().any(|g| g == gap_id)
                || t.bounds_gaps.iter().any(|g| g == gap_id)
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
        let a = Scope { allowed_tools: vec![], ..Default::default() };
        let b = Scope { allowed_tools: vec!["hammer".into()], ..Default::default() };
        let result = a.intersect(b);
        assert_eq!(result.allowed_tools, vec!["hammer"]);
    }

    #[test]
    fn scope_intersect_non_empty() {
        let a = Scope { allowed_tools: vec!["a".into(), "b".into()], ..Default::default() };
        let b = Scope { allowed_tools: vec!["b".into(), "c".into()], ..Default::default() };
        let result = a.intersect(b);
        assert_eq!(result.allowed_tools, vec!["b"]);
    }

    #[test]
    fn membership_in_class() {
        assert!(Membership::InClass.is_in_class());
        assert!(!Membership::OutOfClassExact.is_in_class());
    }
}
