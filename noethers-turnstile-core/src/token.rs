/// ProofToken types and provenance hashing.
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// Status of a proof token.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum TokenStatus {
    Valid,
    Invalid,
    Expired,
    Revoked,
    Malformed,
}

/// Live state of a negative-control token in the runtime context (T17).
///
/// In strict mode the compiler checks every NC token against this map.
/// Any state other than `Live` causes the outcome to be floored to `REF`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum NegativeControlStatus {
    /// NC passed and is currently live.
    Live,
    /// NC was live but has become stale (e.g. context changed since issue).
    Stale,
    /// NC was explicitly checked and failed.
    Failed,
    /// NC token is expected but absent from the live-state map.
    Missing,
}

impl TokenStatus {
    pub fn is_usable(self) -> bool {
        matches!(self, TokenStatus::Valid)
    }
}

/// A proof token that closes or bounds one or more gaps in a proof context.
///
/// The `provenance_hash` is a SHA-256 hex digest of
/// `(claim_id, candidate_id, context_id, allowed_use)`.
/// Equality is bitwise — no fuzzy matching.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProofToken {
    pub token_id: String,
    pub token_type: String,
    pub schema_version: String,
    pub status: TokenStatus,
    /// Gap IDs this token fully closes.
    pub closes_gaps: Vec<String>,
    /// Gap IDs this token bounds (but does not close).
    pub bounds_gaps: Vec<String>,
    /// SHA-256 hex hash of (claim_id, candidate_id, context_id, allowed_use).
    pub provenance_hash: String,
    pub issued_at: DateTime<Utc>,
    pub expires_at: Option<DateTime<Utc>>,
    pub issuer: String,
    pub details: serde_json::Value,
    /// Whether this token is a negative control.
    ///
    /// A negative control token attests that a control experiment ran and
    /// passed.  In strict mode, the compiler checks that every negative-control
    /// token present in the context is live in the runtime's
    /// `negative_control_states` map.  A missing, stale, or failed NC token
    /// causes the compiler to floor the outcome to `REF` (T17).
    ///
    /// `false` (the default) means "not a negative control" and the token is
    /// treated identically to the existing gap-closing / gap-bounding logic.
    #[serde(default)]
    pub is_negative_control: bool,
    /// Optional stable identifier for this negative-control token.
    ///
    /// Only meaningful when `is_negative_control` is `true`. Allows callers to
    /// reference a specific NC token by id rather than embedding the id in
    /// `token_id`. Deserialized as `null`/absent on older payloads.
    #[serde(default)]
    pub negative_control_id: Option<String>,
}

impl ProofToken {
    /// True if the token is currently valid and not expired at `now`.
    pub fn is_live(&self, now: DateTime<Utc>) -> bool {
        if !self.status.is_usable() {
            return false;
        }
        if let Some(exp) = self.expires_at {
            if now >= exp {
                return false;
            }
        }
        true
    }
}

/// Compute the canonical provenance hash for a context tuple.
///
/// The hash is SHA-256 over the canonical form:
/// `claim_id\0candidate_id\0context_id\0allowed_use`
/// using null bytes as delimiters so no field can absorb another's content.
pub fn compute_provenance_hash(
    claim_id: &str,
    candidate_id: &str,
    context_id: &str,
    allowed_use: &str,
) -> String {
    let mut hasher = Sha256::new();
    hasher.update(claim_id.as_bytes());
    hasher.update(b"\x00");
    hasher.update(candidate_id.as_bytes());
    hasher.update(b"\x00");
    hasher.update(context_id.as_bytes());
    hasher.update(b"\x00");
    hasher.update(allowed_use.as_bytes());
    hex::encode(hasher.finalize())
}

/// Verify that a token's provenance hash matches the expected context tuple.
pub fn verify_provenance(
    token: &ProofToken,
    claim_id: &str,
    candidate_id: &str,
    context_id: &str,
    allowed_use: &str,
) -> bool {
    let expected = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);
    // Constant-time comparison to prevent timing attacks.
    constant_time_eq(&token.provenance_hash, &expected)
}

/// Constant-time string comparison.
///
/// Provenance hashes are always 64-char SHA-256 hex, so the length-equal case
/// is the common path. The length-differ case folds into the same XOR loop
/// (the shorter side's missing bytes contribute a non-zero diff) so the
/// running time does not branch on the length-equal / length-differ predicate.
fn constant_time_eq(a: &str, b: &str) -> bool {
    let a_bytes = a.as_bytes();
    let b_bytes = b.as_bytes();
    let n = a_bytes.len().max(b_bytes.len());
    let mut diff: u8 = 0;
    // OR in a "length differs" sentinel as a single byte so the loop body
    // is independent of which side is longer.
    diff |= if a_bytes.len() == b_bytes.len() { 0 } else { 1 };
    for i in 0..n {
        let x = a_bytes.get(i).copied().unwrap_or(0);
        let y = b_bytes.get(i).copied().unwrap_or(0);
        diff |= x ^ y;
    }
    diff == 0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn provenance_hash_is_deterministic() {
        let h1 = compute_provenance_hash("c1", "z1", "ctx1", "diagnostics");
        let h2 = compute_provenance_hash("c1", "z1", "ctx1", "diagnostics");
        assert_eq!(h1, h2);
    }

    #[test]
    fn provenance_hash_changes_with_candidate() {
        let h1 = compute_provenance_hash("c1", "z1", "ctx1", "diagnostics");
        let h2 = compute_provenance_hash("c1", "z2", "ctx1", "diagnostics");
        assert_ne!(h1, h2);
    }

    #[test]
    fn provenance_hash_not_prefix_injectable() {
        // "a\0b" and "a" + "b" must produce different hashes for different splits.
        let h1 = compute_provenance_hash("a\x00b", "", "ctx", "use");
        let h2 = compute_provenance_hash("a", "b", "ctx", "use");
        assert_ne!(h1, h2);
    }

    #[test]
    fn verify_correct_provenance() {
        let hash = compute_provenance_hash("claim", "cand", "ctx", "allowed");
        let token = ProofToken {
            token_id: "t1".into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec![],
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test-issuer".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        };
        assert!(verify_provenance(&token, "claim", "cand", "ctx", "allowed"));
        assert!(!verify_provenance(
            &token, "claim", "OTHER", "ctx", "allowed"
        ));
    }
}
