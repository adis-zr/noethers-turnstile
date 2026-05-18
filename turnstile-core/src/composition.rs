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
///
/// Anti-laundering (T16 / T9): if either component compiles to OOC, the
/// composed context is forced to OOC before token evaluation.  A disqualified
/// component cannot be laundered by a passing one — whatever structural check
/// disqualified the component (no profiles defined, membership check failed,
/// etc.) is not fixed by merging in another component's valid tokens.
///
/// # Architectural note
///
/// Two distinct ceilings exist on `ProofContext`:
///
/// - `authority_ceiling`: structural delegation authority — what the certifier chain
///   is permitted to grant.  Meets pairwise on composition.  Tests that verify
///   delegation semantics inspect this field.
///
/// - `permission_ceiling`: non-promotion ceiling (T9) — `meet(compile(g1), compile(g2))`.
///   Applied as a final hard meet in `compile()` after all other steps.  Prevents
///   a valid component from laundering a refused one.  This field is `AAA` on
///   contexts not produced by composition (defaults to unconstrained).
///
/// # Performance note
///
/// `compose()` calls `compile()` twice on the component contexts (to compute
/// the non-promotion ceiling).  For a chain of N contexts, `compose_n()` folds
/// left, calling `compile()` O(N) times.  Each call compiles a context of
/// growing size, so the total cost is O(N²) in the number of tokens/gaps.  This
/// is acceptable for small N but callers should be aware of the growth.
use crate::compiler::compile;
use crate::context::{Membership, ProofContext};
use crate::error::CompositionError;
use crate::gap::{GapRecord, Profile};
use crate::permission::Permission;
use crate::token::ProofToken;

/// Compose two proof contexts into one.
///
/// Fails closed on any conflict:
/// - `UseConflict` if `allowed_use` differs between contexts.
/// - `TokenConflict` if the same `token_id` appears in both contexts with
///   different content.
pub fn compose(g1: ProofContext, g2: ProofContext) -> Result<ProofContext, CompositionError> {
    // Allowed use must be identical (provenance hash would diverge otherwise).
    if g1.allowed_use != g2.allowed_use {
        return Err(CompositionError::UseConflict);
    }

    // Non-promotion pre-check (T9 / T16):
    // Compile each component in isolation to compute meet(p1, p2).  This becomes
    // the `permission_ceiling` on the composed context — a separate field from
    // `authority_ceiling` so structural delegation authority is not contaminated.
    //
    // Without this cap, a valid token from Γ₁ could launder a refused Γ₂: the
    // merged token pool sees Γ₁'s valid token, closes the gap, and the composed
    // outcome exceeds what Γ₂ allowed on its own — a direct T9 violation.
    let p1 = compile(g1.clone())
        .map(|j| j.permission)
        .unwrap_or(Permission::OOC);
    let p2 = compile(g2.clone())
        .map(|j| j.permission)
        .unwrap_or(Permission::OOC);
    // The non-promotion ceiling also incorporates any existing permission_ceiling
    // from each component (which may itself have been produced by a prior compose).
    let non_promotion_ceiling = p1.meet(p2).meet(g1.permission_ceiling).meet(g2.permission_ceiling);

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

    // Authority ceiling: purely structural delegation — meet of both components'
    // delegation ceilings.  The non-promotion ceiling is kept separate in
    // `permission_ceiling` so tests that inspect `authority_ceiling` see only
    // the delegation semantics (T9 non-promotion is enforced via `permission_ceiling`
    // in compile()).
    let authority_ceiling = g1.authority_ceiling.meet(g2.authority_ceiling);
    let permission_ceiling = non_promotion_ceiling;

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
        permission_ceiling,
        membership,
    })
}

/// Compose two Membership values conservatively: InClass only if both are InClass.
fn compose_membership(m1: &Membership, m2: &Membership) -> Membership {
    if m1.is_in_class() && m2.is_in_class() {
        Membership::InClass
    } else if m1.is_in_class() {
        // m2 is out-of-class; take the worse one.
        m2.clone()
    } else {
        m1.clone()
    }
}

/// Union of gaps by gap_id, minimum status.
///
/// When the same gap_id appears in both contexts with different gap_type values,
/// the gap_type from the first context (g1) wins.  This is a known limitation:
/// same-id gaps with different types represent a data integrity issue that is
/// currently not surfaced as an error.
fn compose_gaps(gaps1: Vec<GapRecord>, gaps2: Vec<GapRecord>) -> Vec<GapRecord> {
    let mut map: std::collections::HashMap<String, GapRecord> = std::collections::HashMap::new();

    for g in gaps1.into_iter().chain(gaps2) {
        map.entry(g.gap_id.clone())
            .and_modify(|existing| {
                // Take the minimum status (worst case).  gap_type from g1 wins when
                // types differ — a same-id conflict is not currently an error.
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
///
/// # Security note
///
/// `status` is excluded from content equality to allow clock-skew tolerance
/// between two contexts that carry the same token at different points in time.
/// The first context's token wins on deduplication.  This is fail-closed when
/// g1 is the trusted source.  If g1 carries an Invalid token and g2 carries a
/// Valid token with the same id, the Invalid token silently wins — the more
/// restrictive outcome.  Callers that need different semantics should not compose
/// contexts where token status may legitimately diverge.
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
/// `status` is intentionally excluded — see security note on `compose_tokens`.
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
    result.sort_by_key(|p| std::cmp::Reverse(p.permission));
    result
}

/// Merge the requirements of `source` into `target`, keeping the stricter
/// requirement for each gap_id and adding any new requirements from source.
///
/// The ordering is `OpenAllowed < BoundedRequired < ClosedRequired`; the merge
/// always keeps the maximum (strictest) of the two requirements.
fn merge_profile_requirements(target: &mut Profile, source: &Profile) {
    use crate::gap::RequiredStatus;

    for src_req in &source.required_gaps {
        match target
            .required_gaps
            .iter_mut()
            .find(|r| r.gap_id == src_req.gap_id)
        {
            Some(tgt_req) => {
                // Keep the strictest: ClosedRequired > BoundedRequired > OpenAllowed.
                tgt_req.minimum_status = match (tgt_req.minimum_status, src_req.minimum_status) {
                    (RequiredStatus::ClosedRequired, _) | (_, RequiredStatus::ClosedRequired) => {
                        RequiredStatus::ClosedRequired
                    }
                    (RequiredStatus::BoundedRequired, _) | (_, RequiredStatus::BoundedRequired) => {
                        RequiredStatus::BoundedRequired
                    }
                    _ => RequiredStatus::OpenAllowed,
                };
            }
            None => {
                target.required_gaps.push(src_req.clone());
            }
        }
    }
}

/// Compose an iterator of proof contexts into one (N-ary composition).
///
/// Returns `Err(CompositionError::EmptyComposition)` if the iterator is empty.
/// Otherwise folds left using `compose()`, failing closed on any conflict.
///
/// Theorem T9: N-ary composition is non-promoting.
///   compile(compose_n([Γ₁, …, Γₙ])).permission ≤ compile(Γᵢ).permission for all i.
pub fn compose_n(
    contexts: impl IntoIterator<Item = ProofContext>,
) -> Result<ProofContext, CompositionError> {
    let mut iter = contexts.into_iter();
    let first = iter.next().ok_or(CompositionError::EmptyComposition)?;
    iter.try_fold(first, compose)
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
            permission_ceiling: Permission::AAA,
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
            is_negative_control: false,
        }
    }

    #[test]
    fn use_conflict_fails() {
        let g1 = base_ctx("1");
        let mut g2 = base_ctx("2");
        g2.allowed_use = "other-use".into();
        assert!(matches!(
            compose(g1, g2),
            Err(CompositionError::UseConflict)
        ));
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
        assert!(matches!(
            compose(g1, g2),
            Err(CompositionError::TokenConflict { .. })
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
        // authority_ceiling is purely the structural delegation meet.
        // The non-promotion ceiling is separate (permission_ceiling).
        let mut g1 = base_ctx("1");
        let mut g2 = base_ctx("2");
        g1.authority_ceiling = Permission::DIA;
        g2.authority_ceiling = Permission::REV;
        let composed = compose(g1, g2).unwrap();
        // DIA.meet(REV) = DIA (DIA < REV in the total order).
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

#[cfg(test)]
mod anti_launder_tests {
    use super::*;
    use crate::compiler::compile;
    use crate::context::Scope;
    use crate::expiry::Expiry;
    use crate::gap::{GapRecord, GapRequirement, Profile, RequiredStatus};
    use crate::permission::Permission;
    use crate::token::{compute_provenance_hash, ProofToken, TokenStatus};
    use chrono::Utc;

    fn make_token(id: &str, status: TokenStatus, closes: Vec<String>, h: String) -> ProofToken {
        ProofToken {
            token_id: id.into(), token_type: "T".into(), schema_version: "0.1".into(),
            status, closes_gaps: closes, bounds_gaps: vec![],
            provenance_hash: h, issued_at: Utc::now(), expires_at: None,
            issuer: "test".into(), details: serde_json::Value::Null, is_negative_control: false,
        }
    }

    fn make_ctx(token: ProofToken, fp: &str) -> ProofContext {
        let h = compute_provenance_hash("claim", "cand", fp, "use");
        let profile = Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement { gap_id: "g1".into(), minimum_status: RequiredStatus::ClosedRequired }],
        };
        ProofContext {
            claim_id: "claim".into(), candidate_id: "cand".into(),
            context_id: fp.into(), context_fingerprint: fp.into(),
            allowed_use: "use".into(), disallowed_uses: vec![],
            scope: Scope::default(), membership: Membership::InClass,
            authority_ceiling: Permission::AAA,
            permission_ceiling: Permission::AAA,
            expiry: Expiry::never(),
            gaps: vec![GapRecord::open("g1", "gap")],
            profiles: vec![profile],
            tokens: vec![ProofToken { provenance_hash: h, ..token }],
        }
    }

    #[test]
    fn anti_laundering_refused_component_caps_composed() {
        // ctx_a: valid token closes g1 → DIA.
        // ctx_b: invalid token can't close g1 → REF (profile defined but unsatisfied).
        // compose(a, b) must be ≤ meet(DIA, REF) = REF.
        // Without the non-promotion ceiling, ctx_a's valid token would launder ctx_b
        // by closing g1 in the merged pool → DIA, violating T9.
        let h = compute_provenance_hash("claim", "cand", "fp", "use");
        let tok_v = make_token("tok", TokenStatus::Valid, vec!["g1".into()], h.clone());
        let tok_i = make_token("tok", TokenStatus::Invalid, vec!["g1".into()], h);
        let ctx_a = make_ctx(tok_v, "fp");
        let ctx_b = make_ctx(tok_i, "fp");

        let p_a = compile(ctx_a.clone()).unwrap().permission;
        let p_b = compile(ctx_b.clone()).unwrap().permission;
        assert_eq!(p_a, Permission::DIA, "ctx_a should be DIA");
        assert_eq!(p_b, Permission::REF, "ctx_b should be REF (profile present, gap unmet)");

        let composed = compose(ctx_a, ctx_b).unwrap();
        let p_c = compile(composed).unwrap().permission;
        // Non-promotion: p_c ≤ meet(DIA, REF) = REF
        assert!(p_c <= p_a.meet(p_b), "T9 violated: composed={:?} > meet({:?},{:?})", p_c, p_a, p_b);
        // More specifically: should be exactly REF (the ceiling set by the weaker component)
        assert_eq!(p_c, Permission::REF, "composed should be REF (non-promotion ceiling), got {:?}", p_c);
    }
}

#[cfg(test)]
mod b1_trace_tests {
    use super::*;
    use crate::compiler::compile;
    use crate::context::Scope;
    use crate::expiry::Expiry;
    use crate::gap::{GapRecord, GapRequirement, Profile, RequiredStatus};
    use crate::permission::Permission;
    use crate::token::{compute_provenance_hash, ProofToken, TokenStatus};
    use chrono::{Duration, Utc};

    #[test]
    fn b1_expired_token_only_gives_exp_not_ooc() {
        let claim_id = "claim-b1";
        let candidate_id = "cand-b1";
        let context_id = "ctx-b1";
        let allowed_use = "stress-test";
        let h = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

        let now = Utc::now();
        let expired_tok = ProofToken {
            token_id: "tok-b1".into(), token_type: "CLOSE".into(),
            schema_version: "0.1".into(), status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()], bounds_gaps: vec![],
            provenance_hash: h, issued_at: now - Duration::hours(1),
            expires_at: Some(now - Duration::seconds(1)),
            issuer: "stress-test".into(), details: serde_json::Value::Null,
            is_negative_control: false,
        };
        let ctx = ProofContext {
            claim_id: claim_id.into(), candidate_id: candidate_id.into(),
            context_id: context_id.into(), context_fingerprint: context_id.into(),
            allowed_use: allowed_use.into(), disallowed_uses: vec![],
            scope: Scope::default(), membership: Membership::InClass,
            authority_ceiling: Permission::AAA,
            permission_ceiling: Permission::AAA,
            expiry: Expiry::never(),
            gaps: vec![GapRecord::open("g1", "gap")],
            profiles: vec![Profile {
                permission: Permission::DIA,
                required_gaps: vec![GapRequirement {
                    gap_id: "g1".into(),
                    minimum_status: RequiredStatus::ClosedRequired,
                }],
            }],
            tokens: vec![expired_tok],
        };

        let j = compile(ctx).unwrap();
        println!("B1 result: {}", j.permission);
        // Trace: expired token skipped → g1 OPEN → profile GapNotMet → had_any_profile=true
        // outcome stays UNS → step6: has_expired_token=true, UNS > EXP → floor to EXP
        assert_eq!(j.permission, Permission::EXP, "Expected EXP for expired-only token, got {:?}", j.permission);
    }
}
