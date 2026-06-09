//! Composition operator on ProofContext.
//!
//! `compose(Γ₁, Γ₂)` is the lax monoidal composition from spec §5:
//!   - permission_ceiling = meet of `compile(g1)` and `compile(g2)` (T9 non-promotion)
//!   - authority_ceiling = meet of both authority_ceilings
//!   - allowed_use must match
//!   - disallowed_uses: union
//!   - scope: intersection
//!   - expiry: minimum
//!   - gaps: union by gap_id, minimum status
//!   - tokens: union by token_id; fail on conflict
//!
//! Anti-laundering (T16 / T9): if either component compiles to Bottom (chain.role(Bottom)),
//! the composed context is forced to Bottom via the permission_ceiling meet.

use crate::compiler::{compile_with_chain, Judgment};
use crate::context::{Membership, ProofContext};
use crate::error::{CompositionError, TurnstileError};
use crate::gap::{GapRecord, Profile};
use crate::permission::{ChainRole, Permission, PermissionChain};
use crate::token::ProofToken;

/// Compose two proof contexts using the default chain.
pub fn compose(g1: ProofContext, g2: ProofContext) -> Result<ProofContext, TurnstileError> {
    compose_with_chain(g1, g2, PermissionChain::default_chain())
}

/// Compose two proof contexts under a specific chain.
///
/// Both contexts must be compatible with the chain (every Permission they
/// reference must be in the chain; any `expected_chain_hash` pin must match).
pub fn compose_with_chain(
    g1: ProofContext,
    g2: ProofContext,
    chain: &PermissionChain,
) -> Result<ProofContext, TurnstileError> {
    if g1.allowed_use != g2.allowed_use {
        return Err(CompositionError::UseConflict.into());
    }

    // Fail fast on chain-hash pin mismatch so composition never swallows the
    // signal under the `unwrap_or_else(bottom)` fallback below.
    for (label, ctx) in [("g1", &g1), ("g2", &g2)] {
        if let Some(pin) = &ctx.expected_chain_hash {
            if *pin != chain.chain_hash() {
                return Err(CompositionError::ChainMismatch.into());
            }
        }
        // Also check ceilings up front — if either ceiling names a level not
        // in this chain, fail cleanly. (Downstream meets would still catch it,
        // but the error type would be Chain(ForeignLevel) which is less
        // informative than ChainMismatch.)
        for p in [&ctx.authority_ceiling, &ctx.permission_ceiling]
            .into_iter()
            .flatten()
        {
            if !chain.contains(p) {
                let _ = label; // silence unused
                return Err(CompositionError::ChainMismatch.into());
            }
        }
    }

    let bottom = *chain.role(ChainRole::Bottom);
    let top = *chain.role(ChainRole::Top);

    // Non-promotion pre-check (T9 / T16). Compile each component under the
    // supplied chain to compute meet(p1, p2). That becomes the permission_ceiling.
    let p1: Permission = compile_with_chain(g1.clone(), chain)
        .map(|j| j.permission)
        .unwrap_or(bottom);
    let p2: Permission = compile_with_chain(g2.clone(), chain)
        .map(|j| j.permission)
        .unwrap_or(bottom);

    let g1_ceiling = g1.permission_ceiling.unwrap_or(top);
    let g2_ceiling = g2.permission_ceiling.unwrap_or(top);
    let non_promotion_ceiling = chain
        .meet(&p1, &p2)
        .and_then(|m| chain.meet(&m, &g1_ceiling))
        .and_then(|m| chain.meet(&m, &g2_ceiling))?;

    let membership = compose_membership(&g1.membership, &g2.membership);

    let mut disallowed_uses = g1.disallowed_uses.clone();
    for u in &g2.disallowed_uses {
        if !disallowed_uses.contains(u) {
            disallowed_uses.push(u.clone());
        }
    }

    let scope = g1.scope.intersect(g2.scope);
    let expiry = g1.expiry.min(g2.expiry);

    let g1_auth = g1.authority_ceiling.unwrap_or(top);
    let g2_auth = g2.authority_ceiling.unwrap_or(top);
    let authority_ceiling = chain.meet(&g1_auth, &g2_auth)?;

    let gaps = compose_gaps(g1.gaps, g2.gaps);
    let tokens = compose_tokens(g1.tokens, g2.tokens)?;
    let profiles = compose_profiles(g1.profiles, g2.profiles, chain);

    let context_fingerprint = format!("{}+{}", g1.context_fingerprint, g2.context_fingerprint);

    // Composed context retains expected_chain_hash if either input pinned it
    // (and they pinned the same chain).
    let expected_chain_hash = match (&g1.expected_chain_hash, &g2.expected_chain_hash) {
        (Some(a), Some(b)) => {
            if a == b {
                Some(*a)
            } else {
                return Err(CompositionError::ChainMismatch.into());
            }
        }
        (Some(a), None) | (None, Some(a)) => Some(*a),
        (None, None) => None,
    };

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
        authority_ceiling: Some(authority_ceiling),
        permission_ceiling: Some(non_promotion_ceiling),
        membership,
        expected_chain_hash,
    })
}

/// Compose two judgments. Both must have been produced from the same chain;
/// returns `Err(CompositionError::ChainMismatch)` if chain_hashes differ.
pub fn compose_judgments(
    j1: &Judgment,
    j2: &Judgment,
    chain: &PermissionChain,
) -> Result<ProofContext, TurnstileError> {
    if j1.chain_hash != chain.chain_hash() || j2.chain_hash != chain.chain_hash() {
        return Err(CompositionError::ChainMismatch.into());
    }
    compose_with_chain(j1.context.clone(), j2.context.clone(), chain)
}

fn compose_membership(m1: &Membership, m2: &Membership) -> Membership {
    if m1.is_in_class() && m2.is_in_class() {
        Membership::InClass
    } else if m1.is_in_class() {
        m2.clone()
    } else {
        m1.clone()
    }
}

fn compose_gaps(gaps1: Vec<GapRecord>, gaps2: Vec<GapRecord>) -> Vec<GapRecord> {
    let mut map: std::collections::HashMap<String, GapRecord> = std::collections::HashMap::new();
    for g in gaps1.into_iter().chain(gaps2) {
        map.entry(g.gap_id.clone())
            .and_modify(|existing| {
                let new_status = existing.status.clone().min_status(g.status.clone());
                existing.status = new_status;
            })
            .or_insert(g);
    }
    let mut result: Vec<GapRecord> = map.into_values().collect();
    result.sort_by(|a, b| a.gap_id.cmp(&b.gap_id));
    result
}

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
                if !tokens_content_equal(existing, &t) {
                    return Err(CompositionError::TokenConflict {
                        token_id: t.token_id.clone(),
                    });
                }
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

fn tokens_content_equal(a: &ProofToken, b: &ProofToken) -> bool {
    a.token_type == b.token_type
        && a.schema_version == b.schema_version
        && a.closes_gaps == b.closes_gaps
        && a.bounds_gaps == b.bounds_gaps
        && a.provenance_hash == b.provenance_hash
        && a.issuer == b.issuer
        && a.details == b.details
}

fn compose_profiles(
    profiles1: Vec<Profile>,
    profiles2: Vec<Profile>,
    chain: &PermissionChain,
) -> Vec<Profile> {
    let mut map: std::collections::HashMap<String, Profile> = std::collections::HashMap::new();
    for p in profiles1.into_iter().chain(profiles2) {
        let key = p.permission.as_str().to_owned();
        map.entry(key)
            .and_modify(|existing| {
                merge_profile_requirements(existing, &p);
            })
            .or_insert(p);
    }
    let mut result: Vec<Profile> = map.into_values().collect();
    // Sort descending by chain rank. Profiles with foreign permission names
    // (shouldn't happen if validate_context fired) fall to the end.
    result.sort_by(|a, b| {
        let ra = chain.rank(&a.permission).unwrap_or(u8::MAX);
        let rb = chain.rank(&b.permission).unwrap_or(u8::MAX);
        rb.cmp(&ra)
    });
    result
}

fn merge_profile_requirements(target: &mut Profile, source: &Profile) {
    use crate::gap::RequiredStatus;
    for src_req in &source.required_gaps {
        // Disjunctive (`any_of`) requirements are independent clauses — each
        // must be satisfied by the composed context. Never merge them; push
        // each one as its own clause. This keeps composition conservative:
        // the composed profile demands every any_of choice from every source.
        if src_req.is_any_of() {
            target.required_gaps.push(src_req.clone());
            continue;
        }
        // For conjunctive single-gap requirements, merge by gap_id and pick
        // the stricter minimum_status. Only collapse against other
        // single-gap requirements; never into an any_of clause.
        match target
            .required_gaps
            .iter_mut()
            .find(|r| !r.is_any_of() && r.gap_id == src_req.gap_id)
        {
            Some(tgt_req) => {
                tgt_req.minimum_status =
                    match (tgt_req.minimum_status, src_req.minimum_status) {
                        (RequiredStatus::ClosedRequired, _)
                        | (_, RequiredStatus::ClosedRequired) => RequiredStatus::ClosedRequired,
                        (RequiredStatus::BoundedRequired, _)
                        | (_, RequiredStatus::BoundedRequired) => RequiredStatus::BoundedRequired,
                        _ => RequiredStatus::OpenAllowed,
                    };
            }
            None => {
                target.required_gaps.push(src_req.clone());
            }
        }
    }
}

/// Compose an iterator of proof contexts into one (N-ary composition) under the
/// default chain.
pub fn compose_n(
    contexts: impl IntoIterator<Item = ProofContext>,
) -> Result<ProofContext, TurnstileError> {
    compose_n_with_chain(contexts, PermissionChain::default_chain())
}

/// Compose an iterator of proof contexts into one under a specific chain.
pub fn compose_n_with_chain(
    contexts: impl IntoIterator<Item = ProofContext>,
    chain: &PermissionChain,
) -> Result<ProofContext, TurnstileError> {
    let mut iter = contexts.into_iter();
    let first = iter
        .next()
        .ok_or::<TurnstileError>(CompositionError::EmptyComposition.into())?;
    iter.try_fold(first, |acc, g| compose_with_chain(acc, g, chain))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::context::Scope;
    use crate::default_levels;
    use crate::expiry::Expiry;
    use crate::gap::{GapRecord, GapStatus};
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
            authority_ceiling: None,
            permission_ceiling: None,
            membership: Membership::InClass,
            expected_chain_hash: None,
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
            is_negative_control: false,
            negative_control_id: None,
        }
    }

    #[test]
    fn use_conflict_fails() {
        let g1 = base_ctx("1");
        let mut g2 = base_ctx("2");
        g2.allowed_use = "other-use".into();
        let err = compose(g1, g2).unwrap_err();
        assert!(matches!(
            err,
            TurnstileError::Composition(CompositionError::UseConflict)
        ));
    }

    #[test]
    fn token_conflict_fails() {
        let g1 = base_ctx("1");
        let g2 = base_ctx("2");
        let t1 = make_token("tok-1", vec!["g1".into()], &g1);
        let t2 = make_token("tok-1", vec!["g2".into()], &g2);
        let mut g1 = g1;
        let mut g2 = g2;
        g1.tokens.push(t1);
        g2.tokens.push(t2);
        let err = compose(g1, g2).unwrap_err();
        assert!(matches!(
            err,
            TurnstileError::Composition(CompositionError::TokenConflict { .. })
        ));
    }

    #[test]
    fn gap_composition_takes_minimum_status() {
        let mut g1 = base_ctx("1");
        let mut g2 = base_ctx("2");
        g1.gaps.push(GapRecord::closed("g1", "calibration_gap"));
        g2.gaps.push(GapRecord::open("g1", "calibration_gap"));
        let composed = compose(g1, g2).unwrap();
        assert!(matches!(
            composed.find_gap("g1").unwrap().status,
            GapStatus::Open
        ));
    }

    #[test]
    fn authority_ceiling_is_meet() {
        let mut g1 = base_ctx("1");
        let mut g2 = base_ctx("2");
        g1.authority_ceiling = Some(default_levels::DIA());
        g2.authority_ceiling = Some(default_levels::REV());
        let composed = compose(g1, g2).unwrap();
        assert_eq!(composed.authority_ceiling.unwrap(), default_levels::DIA());
    }
}
