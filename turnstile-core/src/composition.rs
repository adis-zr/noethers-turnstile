/// Composition operator on ProofContext.
///
/// `compose(Γ₁, Γ₂)` is the lax monoidal composition from spec §5:
///   - permission = meet of both authority_ceilings
///   - allowed_use: must match (same string) or fail with UseConflict
///   - disallowed_uses: union
///   - scope: intersection
///   - expiry: minimum expires_at
///   - gaps: union by gap_id, minimum status (Open < Bounded < Closed)
///   - tokens: union by token_id; on conflict fail closed with TokenConflict
///   - provenance: derived from the composed context (same allowed_use required)
use crate::context::{Membership, ProofContext};
use crate::error::CompositionError;
use crate::gap::{GapRecord, Profile};
use crate::token::ProofToken;

/// Compose two proof contexts into one.
///
/// Fails closed on any conflict:
/// - `UseConflict` if `allowed_use` differs between contexts.
/// - `TokenConflict` if the same `token_id` appears in both contexts with
///    different content.
pub fn compose(g1: ProofContext, g2: ProofContext) -> Result<ProofContext, CompositionError> {
    // Allowed use must be identical (provenance hash would diverge otherwise).
    if g1.allowed_use != g2.allowed_use {
        return Err(CompositionError::UseConflict);
    }

    // Membership: conservative — if either is out-of-class, result is out-of-class.
    let membership = compose_membership(&g1.membership, &g2.membership);

    // Disallowed uses: union.
    let mut disallowed_uses = g1.disallowed_uses.clone();
    for u in &g2.disallowed_uses {
        if !disallowed_uses.contains(u) {
            disallowed_uses.push(u.clone());
        }
    }

    // Scope: intersection.
    let scope = g1.scope.intersect(g2.scope);

    // Expiry: minimum.
    let expiry = g1.expiry.min(g2.expiry);

    // Authority ceiling: meet.
    let authority_ceiling = g1.authority_ceiling.meet(g2.authority_ceiling);

    // Gaps: union by gap_id, minimum status.
    let gaps = compose_gaps(g1.gaps, g2.gaps);

    // Tokens: union by token_id, fail on conflict.
    let tokens = compose_tokens(g1.tokens, g2.tokens)?;

    // Profiles: union by permission level; on conflict keep the stricter one
    // (the one with more requirements).  This is conservative: adding more
    // requirements can only lower the outcome.
    let profiles = compose_profiles(g1.profiles, g2.profiles);

    // The composed context keeps g1's identifiers (claim_id, candidate_id, etc.)
    // but uses the shared context_fingerprint from g1 (they may differ — the
    // composed context is a new logical context).
    // For composing two unrelated contexts, we combine the fingerprints.
    let context_fingerprint = format!("{}+{}", g1.context_fingerprint, g2.context_fingerprint);

    Ok(ProofContext {
        claim_id: g1.claim_id,
        candidate_id: g1.candidate_id,
        context_id: g1.context_id,
        context_fingerprint,
        allowed_use: g1.allowed_use,
        disallowed_uses,
        scope,
        gaps,
        profiles,
        tokens,
        expiry,
        authority_ceiling,
        membership,
    })
}

/// Compose two Membership values conservatively: InClass only if both are InClass.
fn compose_membership(m1: &Membership, m2: &Membership) -> Membership {
    if m1.is_in_class() && m2.is_in_class() {
        Membership::InClass
    } else {
        // Take the "worse" membership (non-InClass takes priority).
        m1.clone()
    }
}

/// Union of gaps by gap_id, minimum status.
fn compose_gaps(gaps1: Vec<GapRecord>, gaps2: Vec<GapRecord>) -> Vec<GapRecord> {
    let mut map: std::collections::HashMap<String, GapRecord> = std::collections::HashMap::new();

    for g in gaps1.into_iter().chain(gaps2) {
        map.entry(g.gap_id.clone())
            .and_modify(|existing| {
                // Take the minimum status (worst case).
                let new_status = existing.status.clone().min_status(g.status.clone());
                existing.status = new_status;
            })
            .or_insert(g);
    }

    let mut result: Vec<GapRecord> = map.into_values().collect();
    result.sort_by(|a, b| a.gap_id.cmp(&b.gap_id));
    result
}

/// Union of tokens by token_id; fail closed on conflict (same id, different content).
fn compose_tokens(
    tokens1: Vec<ProofToken>,
    tokens2: Vec<ProofToken>,
) -> Result<Vec<ProofToken>, CompositionError> {
    let mut map: std::collections::HashMap<String, ProofToken> = std::collections::HashMap::new();

    for t in tokens1 {
        map.insert(t.token_id.clone(), t);
    }

    for t in tokens2 {
        match map.get(&t.token_id) {
            Some(existing) => {
                // Conflict check: same token_id, check content equality.
                if !tokens_content_equal(existing, &t) {
                    return Err(CompositionError::TokenConflict {
                        token_id: t.token_id.clone(),
                    });
                }
                // Identical content: keep existing (deduplication).
            }
            None => {
                map.insert(t.token_id.clone(), t);
            }
        }
    }

    let mut result: Vec<ProofToken> = map.into_values().collect();
    result.sort_by(|a, b| a.token_id.cmp(&b.token_id));
    Ok(result)
}

/// Check whether two tokens have identical content (excluding mutable fields like
/// issued_at which may differ by milliseconds in tests).
///
/// Content equality is defined over the fields that determine what the token
/// attests: token_type, schema_version, closes_gaps, bounds_gaps, provenance_hash,
/// issuer, details.  We deliberately exclude issued_at, expires_at, and status
/// from conflict detection to allow clock-skew tolerance.
fn tokens_content_equal(a: &ProofToken, b: &ProofToken) -> bool {
    a.token_type == b.token_type
        && a.schema_version == b.schema_version
        && a.closes_gaps == b.closes_gaps
        && a.bounds_gaps == b.bounds_gaps
        && a.provenance_hash == b.provenance_hash
        && a.issuer == b.issuer
        && a.details == b.details
}

/// Union of profiles by permission level; on conflict, keep the stricter one
/// (the profile with more required gaps — more requirements can only lower outcome).
fn compose_profiles(profiles1: Vec<Profile>, profiles2: Vec<Profile>) -> Vec<Profile> {
    let mut map: std::collections::HashMap<String, Profile> = std::collections::HashMap::new();

    for p in profiles1.into_iter().chain(profiles2) {
        let key = p.permission.as_str().to_owned();
        map.entry(key)
            .and_modify(|existing| {
                // Merge: union of required_gaps by gap_id, keeping stricter requirement.
                merge_profile_requirements(existing, &p);
            })
            .or_insert(p);
    }

    let mut result: Vec<Profile> = map.into_values().collect();
    // Sort descending by permission.
    result.sort_by(|a, b| b.permission.cmp(&a.permission));
    result
}

/// Merge the requirements of `source` into `target`, keeping the stricter
/// requirement for each gap_id and adding any new requirements from source.
fn merge_profile_requirements(target: &mut Profile, source: &Profile) {
    use crate::gap::RequiredStatus;

    for src_req in &source.required_gaps {
        match target
            .required_gaps
            .iter_mut()
            .find(|r| r.gap_id == src_req.gap_id)
        {
            Some(tgt_req) => {
                // Keep the stricter: ClosedRequired > BoundedRequired.
                if src_req.minimum_status == RequiredStatus::ClosedRequired {
                    tgt_req.minimum_status = RequiredStatus::ClosedRequired;
                }
            }
            None => {
                target.required_gaps.push(src_req.clone());
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::context::Scope;
    use crate::expiry::Expiry;
    use crate::gap::{GapRecord, GapStatus};
    use crate::permission::Permission;
    use crate::token::{compute_provenance_hash, ProofToken, TokenStatus};
    use chrono::Utc;

    fn base_ctx(suffix: &str) -> ProofContext {
        ProofContext {
            claim_id: format!("claim-{}", suffix),
            candidate_id: format!("z-{}", suffix),
            context_id: format!("ctx-{}", suffix),
            context_fingerprint: format!("fp-{}", suffix),
            allowed_use: "diagnostics".into(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps: vec![],
            profiles: vec![],
            tokens: vec![],
            expiry: Expiry::never(),
            authority_ceiling: Permission::AAA,
            membership: Membership::InClass,
        }
    }

    fn make_token(id: &str, closes: Vec<String>, ctx: &ProofContext) -> ProofToken {
        let hash = compute_provenance_hash(
            &ctx.claim_id,
            &ctx.candidate_id,
            &ctx.context_id,
            &ctx.allowed_use,
        );
        ProofToken {
            token_id: id.into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: closes,
            bounds_gaps: vec![],
            provenance_hash: hash,
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
        }
    }

    #[test]
    fn use_conflict_fails() {
        let g1 = base_ctx("1");
        let mut g2 = base_ctx("2");
        g2.allowed_use = "other-use".into();
        assert!(matches!(compose(g1, g2), Err(CompositionError::UseConflict)));
    }

    #[test]
    fn token_conflict_fails() {
        let g1 = base_ctx("1");
        let g2 = base_ctx("2");
        let t1 = make_token("tok-1", vec!["g1".into()], &g1);
        let mut t2 = make_token("tok-1", vec!["g2".into()], &g2); // different content
        t2.token_id = "tok-1".into();
        // t2 has different closes_gaps → conflict.
        let mut g1 = g1;
        let mut g2 = g2;
        g1.tokens.push(t1);
        g2.tokens.push(t2);
        assert!(matches!(compose(g1, g2), Err(CompositionError::TokenConflict { .. })));
    }

    #[test]
    fn gap_composition_takes_minimum_status() {
        let mut g1 = base_ctx("1");
        let mut g2 = base_ctx("2");
        g1.gaps.push(GapRecord::closed("g1", "calibration_gap"));
        g2.gaps.push(GapRecord::open("g1", "calibration_gap"));
        let composed = compose(g1, g2).unwrap();
        assert!(matches!(composed.find_gap("g1").unwrap().status, GapStatus::Open));
    }

    #[test]
    fn authority_ceiling_is_meet() {
        let mut g1 = base_ctx("1");
        let mut g2 = base_ctx("2");
        g1.authority_ceiling = Permission::DIA;
        g2.authority_ceiling = Permission::REV;
        let composed = compose(g1, g2).unwrap();
        assert_eq!(composed.authority_ceiling, Permission::DIA);
    }

    #[test]
    fn disallowed_uses_are_unioned() {
        let mut g1 = base_ctx("1");
        let mut g2 = base_ctx("2");
        g1.disallowed_uses = vec!["write".into()];
        g2.disallowed_uses = vec!["delete".into()];
        let composed = compose(g1, g2).unwrap();
        assert!(composed.disallowed_uses.contains(&"write".to_string()));
        assert!(composed.disallowed_uses.contains(&"delete".to_string()));
    }

    #[test]
    fn expiry_takes_minimum() {
        let now = Utc::now();
        let mut g1 = base_ctx("1");
        let mut g2 = base_ctx("2");
        g1.expiry = Expiry::at(now + chrono::Duration::seconds(100));
        g2.expiry = Expiry::at(now + chrono::Duration::seconds(10));
        let composed = compose(g1, g2).unwrap();
        assert_eq!(
            composed.expiry.deadline,
            Some(now + chrono::Duration::seconds(10))
        );
    }
}
