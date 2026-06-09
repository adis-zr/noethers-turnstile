//! The admissibility compiler: Γ ⊢ z : p until ε.
//!
//! Algorithm (spec §3, with all-meets discipline of §2.1):
//! 1. If membership ≠ InClass → role(Bottom)
//! 2. Early context expiry check → meet with role(ExpiryFloor)
//! 3. Descending search over chain → strongest p such that profile_satisfied(Γ, p)
//! 4. Structural blockers (PROVENANCE_MISMATCH / DEAD_CREDENTIAL) → meet with role(Refused)
//!    when outcome < role(BlockerThreshold); disallowed_uses → ROL-equivalent meet
//!    5a. Meet with authority_ceiling (structural delegation limit)
//!    5b. Meet with permission_ceiling (non-promotion ceiling T9, set by compose())
//! 6. Token-level expiry → meet with role(ExpiryFloor) when any usable correct-provenance
//!    token has expired
//! 7. Record negative-control token IDs in the derivation (liveness checked at runtime)
//!
//! Every step expressed as `outcome = chain.meet(outcome, ...)` so non-promotion
//! is a one-line theorem: meet is min, min never raises.
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use tracing::{debug, instrument, warn};

use crate::audit::{Derivation, DerivationStep};
use crate::context::ProofContext;
use crate::error::TurnstileError;
use crate::expiry::Expiry;
use crate::gap::GapStatus;
use crate::permission::{ChainHash, ChainRole, Permission, PermissionChain};
use crate::token::verify_provenance;

/// The result of compiling a proof context.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Judgment {
    /// The proof context that was compiled (snapshot).
    pub context: ProofContext,
    /// The emitted permission.
    ///
    /// WARNING: Do not read this field directly when evaluating live admissibility.
    /// Use `LiveJudgment::permission()` instead — it applies expiry, fingerprint
    /// verification, and negative-control liveness checks at read time.
    pub permission: Permission,
    /// The binding expiry (the `ε` in `Γ ⊢ z : p until ε`).
    pub expiry: Expiry,
    /// Full audit derivation.
    pub derivation: Derivation,
    /// Hash of the chain that authorized this judgment. Auditors resolve this
    /// against a `ChainRegistry` to recover the chain content.
    pub chain_hash: ChainHash,
    /// Optional chain sidecar for self-contained archival. `None` keeps the
    /// judgment small in normal operation; set via `with_chain_sidecar`.
    #[serde(default)]
    pub chain: Option<PermissionChain>,
}

impl Judgment {
    /// Inline the chain into the judgment for self-contained archival.
    pub fn with_chain_sidecar(mut self, chain: &PermissionChain) -> Self {
        self.chain = Some(chain.clone());
        self
    }
}

/// Validate structural preconditions on a context before compilation, against
/// the supplied chain.
///
/// Returns `Err(MalformedContext)` for any of:
///   - A profile references a `gap_id` not present in `ctx.gaps`.
///   - `ctx.gaps` contains duplicate `gap_id` values.
///   - `ctx.profiles` contains two entries with the same `permission` level.
///   - `ctx.allowed_use` is empty.
///   - Any `Permission` field references a name not in the chain.
///   - `ctx.expected_chain_hash` is `Some` and differs from `chain.chain_hash()`.
fn validate_context(ctx: &ProofContext, chain: &PermissionChain) -> Result<(), TurnstileError> {
    if ctx.allowed_use.is_empty() {
        return Err(TurnstileError::MalformedContext(
            "allowed_use must not be empty".into(),
        ));
    }

    // expected_chain_hash pin (§3.3 mechanism 2).
    if let Some(expected) = &ctx.expected_chain_hash {
        if *expected != chain.chain_hash() {
            return Err(TurnstileError::MalformedContext(format!(
                "expected_chain_hash {} does not match supplied chain {}",
                expected,
                chain.chain_hash()
            )));
        }
    }

    // Duplicate gap_ids.
    let mut seen_gap_ids = std::collections::HashSet::new();
    for g in &ctx.gaps {
        if !seen_gap_ids.insert(g.gap_id.as_str()) {
            return Err(TurnstileError::MalformedContext(format!(
                "duplicate gap_id '{}'",
                g.gap_id
            )));
        }
    }

    // All gap_ids referenced by profiles exist; all profile permissions are in chain.
    for profile in &ctx.profiles {
        if !chain.contains(&profile.permission) {
            return Err(TurnstileError::MalformedContext(format!(
                "profile permission '{}' not in supplied chain",
                profile.permission
            )));
        }
        for req in &profile.required_gaps {
            validate_requirement(ctx, req, &profile.permission)?;
        }
    }

    // Duplicate permission levels in profiles.
    let mut seen_perms: std::collections::HashSet<&str> = std::collections::HashSet::new();
    for profile in &ctx.profiles {
        if !seen_perms.insert(profile.permission.as_str()) {
            return Err(TurnstileError::MalformedContext(format!(
                "duplicate profile for permission level {}",
                profile.permission
            )));
        }
    }

    // Ceilings, if Some, must be in chain.
    if let Some(p) = &ctx.authority_ceiling {
        if !chain.contains(p) {
            return Err(TurnstileError::MalformedContext(format!(
                "authority_ceiling '{}' not in supplied chain",
                p
            )));
        }
    }
    if let Some(p) = &ctx.permission_ceiling {
        if !chain.contains(p) {
            return Err(TurnstileError::MalformedContext(format!(
                "permission_ceiling '{}' not in supplied chain",
                p
            )));
        }
    }

    Ok(())
}

/// Validate a single `GapRequirement` (conjunctive or disjunctive) against ctx.
/// Conjunctive: gap_id must exist in ctx.gaps.
/// Disjunctive: every arm validates recursively; an empty arm list is rejected.
fn validate_requirement(
    ctx: &ProofContext,
    req: &crate::gap::GapRequirement,
    profile_perm: &Permission,
) -> Result<(), TurnstileError> {
    if let Some(arms) = &req.any_of {
        if arms.is_empty() {
            return Err(TurnstileError::MalformedContext(format!(
                "profile for {}: any_of requirement has zero arms",
                profile_perm
            )));
        }
        for arm in arms {
            validate_requirement(ctx, arm, profile_perm)?;
        }
        Ok(())
    } else if ctx.find_gap(&req.gap_id).is_none() {
        Err(TurnstileError::MalformedContext(format!(
            "profile for {} references unknown gap_id '{}'",
            profile_perm, req.gap_id
        )))
    } else {
        Ok(())
    }
}

/// Compile a proof context using the default chain. Equivalent to
/// `compile_with_chain(ctx, PermissionChain::default_chain())`. The returned
/// `Judgment` carries the default chain's hash — the decision to use the
/// default is *recorded*, not implicit.
///
/// Production callers should prefer `compile_with_chain` so the chain selection
/// appears at the call site.
pub fn compile(ctx: ProofContext) -> Result<Judgment, TurnstileError> {
    compile_with_chain(ctx, PermissionChain::default_chain())
}

/// Compile against the default chain at a pinned clock. Useful for tests and
/// any caller that wants deterministic re-runs across wall-clock drift.
pub fn compile_at(ctx: ProofContext, now: DateTime<Utc>) -> Result<Judgment, TurnstileError> {
    compile_at_with_chain(ctx, PermissionChain::default_chain(), now)
}

/// Compile a proof context against a specific permission chain.
///
/// Returns `Err(TurnstileError::MalformedContext)` if the context is structurally
/// invalid (see `validate_context`).
pub fn compile_with_chain(
    ctx: ProofContext,
    chain: &PermissionChain,
) -> Result<Judgment, TurnstileError> {
    compile_at_with_chain(ctx, chain, Utc::now())
}

/// Compile a proof context against a specific permission chain at a pinned
/// clock. Every expiry-sensitive check observes `now` — never `Utc::now()`.
/// This is the single observation-point guarantee from EC-062.
#[instrument(
    name = "turnstile.compile",
    skip(ctx, chain, now),
    fields(
        claim_id = %ctx.claim_id,
        candidate_id = %ctx.candidate_id,
        context_id = %ctx.context_id,
        allowed_use = %ctx.allowed_use,
        chain_hash = %chain.chain_hash(),
    )
)]
pub fn compile_at_with_chain(
    ctx: ProofContext,
    chain: &PermissionChain,
    now: DateTime<Utc>,
) -> Result<Judgment, TurnstileError> {
    validate_context(&ctx, chain)?;

    let mut derivation = Derivation::new().with_provenance(ctx.provenance_hash());

    let bottom = *chain.role(ChainRole::Bottom);
    let expiry_floor = *chain.role(ChainRole::ExpiryFloor);
    let refused = *chain.role(ChainRole::Refused);
    let unsatisfied = *chain.role(ChainRole::Unsatisfied);
    let threshold = *chain.role(ChainRole::BlockerThreshold);
    let top = *chain.role(ChainRole::Top);

    // Step 1: membership check.
    if !ctx.membership.is_in_class() {
        debug!(
            phase = "membership_check",
            membership = ?ctx.membership,
            permission = %bottom,
            "out-of-class membership: emitting Bottom"
        );
        derivation.push(DerivationStep {
            phase: "membership_check".into(),
            permission_after: bottom,
            note: format!("out-of-class membership: {:?}", ctx.membership),
            token_ids: vec![],
        });
        return Ok(Judgment {
            permission: bottom,
            expiry: ctx.expiry.clone(),
            derivation,
            chain_hash: chain.chain_hash(),
            chain: None,
            context: ctx,
        });
    }

    // Step 2: early expiry check — halt before touching any tokens (spec §14 step 4).
    if ctx.expiry.fired(now) {
        warn!(
            phase = "context_expiry",
            "context expiry has already fired; emitting ExpiryFloor"
        );
        derivation.push(DerivationStep {
            phase: "context_expiry".into(),
            permission_after: expiry_floor,
            note: "context expiry fired before token evaluation".into(),
            token_ids: vec![],
        });
        return Ok(Judgment {
            permission: expiry_floor,
            expiry: ctx.expiry.clone(),
            derivation,
            chain_hash: chain.chain_hash(),
            chain: None,
            context: ctx,
        });
    }

    // Step 3: descending search.
    // outcome starts at Unsatisfied: "profile exists but no positive permission
    // satisfiable given the current evidence." Refused is reserved for explicit
    // structural refusals (wrong-provenance, step 4 blocker). Bottom is reserved
    // for out-of-class membership (step 1, already handled above).
    let mut outcome = unsatisfied;
    let mut search_note = "no profile satisfied".to_string();
    let mut consulted_tokens: Vec<String> = vec![];
    let mut had_any_profile = false;
    let mut provenance_mismatch_seen = false;
    let mut dead_credential_seen = false;
    let mut satisfied_arms: Vec<String> = vec![];

    'outer: for p in chain.descending() {
        let mut arms_for_this_profile: Vec<String> = vec![];
        match profile_satisfied(
            &ctx,
            p,
            now,
            &mut consulted_tokens,
            &mut provenance_mismatch_seen,
            &mut dead_credential_seen,
            &mut arms_for_this_profile,
        ) {
            ProfileCheckResult::Satisfied => {
                outcome = *p;
                if arms_for_this_profile.is_empty() {
                    search_note = format!("profile satisfied at {}", p);
                } else {
                    // Arm attribution: record which disjunct fired for each
                    // any_of requirement. This is the audit-granularity
                    // contract from spec §2.2.5 / Phase 1b.
                    search_note = format!(
                        "profile satisfied at {} via any_of arm(s): {}",
                        p,
                        arms_for_this_profile.join(", ")
                    );
                }
                satisfied_arms = arms_for_this_profile;
                had_any_profile = true;
                break 'outer;
            }
            ProfileCheckResult::NoProfile => continue,
            ProfileCheckResult::GapNotMet => {
                had_any_profile = true;
                debug!(
                    phase = "descending_search",
                    permission = %p,
                    "gap requirement not met; descending"
                );
                continue;
            }
        }
    }

    // If no profiles were defined at all, emit Bottom (undefined class behavior).
    if !had_any_profile {
        outcome = bottom;
        search_note = "no profiles defined".to_string();
    }

    debug!(
        phase = "descending_search",
        permission = %outcome,
        note = %search_note,
        "descending search complete"
    );
    // Token-IDs include both consulted tokens and any_of arm attributions
    // (prefixed `any_of_arm:`). Auditors distinguish them by the prefix and
    // can also read the satisfied-arm gap_ids from `note`.
    let mut all_attribution = consulted_tokens.clone();
    for arm in &satisfied_arms {
        all_attribution.push(format!("any_of_arm:{}", arm));
    }
    derivation.push(DerivationStep {
        phase: "descending_search".into(),
        permission_after: outcome,
        note: search_note,
        token_ids: all_attribution,
    });

    // Step 4: structural blockers. Both PROVENANCE_MISMATCH and DEAD_CREDENTIAL
    // meet outcome with Refused when outcome < BlockerThreshold.
    //
    // "outcome < BlockerThreshold" covers the "no profile satisfied" cases
    // (Unsatisfied, and various below-threshold roles). If a correct-provenance
    // token satisfied a profile above the threshold, these blockers are
    // suppressed: the profile was met legitimately.
    let outcome_rank = chain.rank(&outcome).expect("outcome must be in chain");
    let threshold_rank = chain.rank(&threshold).expect("threshold must be in chain");
    let apply_ref_blocker =
        (provenance_mismatch_seen || dead_credential_seen) && outcome_rank < threshold_rank;
    if apply_ref_blocker {
        let note = match (provenance_mismatch_seen, dead_credential_seen) {
            (true, true) => {
                "PROVENANCE_MISMATCH + DEAD_CREDENTIAL: rejected token(s) seen; Refused meet applied"
                    .to_string()
            }
            (true, false) => {
                "PROVENANCE_MISMATCH: token(s) with wrong provenance seen; Refused meet applied"
                    .to_string()
            }
            (false, true) => {
                "DEAD_CREDENTIAL: token(s) with non-usable status seen; Refused meet applied"
                    .to_string()
            }
            (false, false) => unreachable!(),
        };
        warn!(
            phase = "structural_blockers",
            provenance_mismatch = provenance_mismatch_seen,
            dead_credential = dead_credential_seen,
            "structural blocker(s) detected; meeting outcome with Refused"
        );
        let after = chain.meet(&outcome, &refused)?;
        derivation.push(DerivationStep {
            phase: "structural_blockers".into(),
            permission_after: after,
            note,
            token_ids: vec![],
        });
        outcome = after;
    }

    // disallowed_uses blocker: meet with the chain's DisallowedUsesCeiling role.
    // No level naming — the role is the structural anchor.
    if !ctx.disallowed_uses.is_empty() {
        let disallowed_ceiling = *chain.role(ChainRole::DisallowedUsesCeiling);
        let after = chain.meet(&outcome, &disallowed_ceiling)?;
        if chain.rank(&after) < chain.rank(&outcome) {
            warn!(
                phase = "structural_blockers",
                before = %outcome,
                after = %after,
                "disallowed_uses present; meeting with ceiling"
            );
            derivation.push(DerivationStep {
                phase: "structural_blockers".into(),
                permission_after: after,
                note: format!(
                    "disallowed_uses present ({}), ceiling at {}",
                    ctx.disallowed_uses.join(", "),
                    disallowed_ceiling
                ),
                token_ids: vec![],
            });
            outcome = after;
        }
    }

    // Step 5a: authority ceiling (structural delegation limit).
    let authority_ceiling = ctx.authority_ceiling.unwrap_or(top);
    let after_auth = chain.meet(&outcome, &authority_ceiling)?;
    if chain.rank(&after_auth) < chain.rank(&outcome) {
        warn!(
            phase = "authority_ceiling",
            ceiling = %authority_ceiling,
            before = %outcome,
            "authority ceiling lowered permission"
        );
        derivation.push(DerivationStep {
            phase: "authority_ceiling".into(),
            permission_after: after_auth,
            note: format!("authority ceiling is {}", authority_ceiling),
            token_ids: vec![],
        });
    }
    outcome = after_auth;

    // Step 5b: permission ceiling (non-promotion ceiling, T9).
    let permission_ceiling = ctx.permission_ceiling.unwrap_or(top);
    let after_perm = chain.meet(&outcome, &permission_ceiling)?;
    if chain.rank(&after_perm) < chain.rank(&outcome) {
        warn!(
            phase = "permission_ceiling",
            ceiling = %permission_ceiling,
            before = %outcome,
            "non-promotion ceiling (T9) lowered permission"
        );
        derivation.push(DerivationStep {
            phase: "permission_ceiling".into(),
            permission_after: after_perm,
            note: format!("non-promotion ceiling (T9) is {}", permission_ceiling),
            token_ids: vec![],
        });
    }
    outcome = after_perm;

    // Step 6: token-level expiry blocker — if any Valid-status token with
    // correct provenance has expired, meet outcome with ExpiryFloor.
    let expired_ids: Vec<String> = ctx
        .tokens
        .iter()
        .filter(|t| {
            t.status.is_usable()
                && t.expires_at.map(|e| now >= e).unwrap_or(false)
                && verify_provenance(
                    t,
                    &ctx.claim_id,
                    &ctx.candidate_id,
                    &ctx.context_id,
                    &ctx.allowed_use,
                )
        })
        .map(|t| t.token_id.clone())
        .collect();
    if !expired_ids.is_empty() {
        let after_exp = chain.meet(&outcome, &expiry_floor)?;
        if chain.rank(&after_exp) < chain.rank(&outcome) {
            warn!(
                phase = "expiry_blocker",
                expired_token_ids = ?expired_ids,
                "expired proof token(s); meeting outcome with ExpiryFloor"
            );
            derivation.push(DerivationStep {
                phase: "expiry_blocker".into(),
                permission_after: after_exp,
                note: "at least one proof token has expired".into(),
                token_ids: expired_ids,
            });
            outcome = after_exp;
        }
    }

    // Step 7: record negative-control token IDs in the derivation.
    let nc_token_ids: Vec<String> = ctx
        .tokens
        .iter()
        .filter(|t| t.is_negative_control)
        .map(|t| t.token_id.clone())
        .collect();
    if !nc_token_ids.is_empty() {
        debug!(
            phase = "negative_control_registration",
            nc_token_count = nc_token_ids.len(),
            "negative-control tokens registered for runtime liveness check (T17)"
        );
        derivation.push(DerivationStep {
            phase: "negative_control_registration".into(),
            permission_after: outcome,
            note: format!(
                "{} negative-control token(s) registered; liveness checked at runtime",
                nc_token_ids.len()
            ),
            token_ids: nc_token_ids,
        });
    }

    debug!(permission = %outcome, "compilation complete");
    Ok(Judgment {
        permission: outcome,
        expiry: ctx.expiry.clone(),
        derivation,
        chain_hash: chain.chain_hash(),
        chain: None,
        context: ctx,
    })
}

/// Result of checking whether a profile is satisfied.
enum ProfileCheckResult {
    Satisfied,
    NoProfile,
    GapNotMet,
}

/// Check whether all gap requirements in the profile for permission `p` are met
/// in context `ctx`.
///
/// `satisfied_arms` collects the gap_id of the satisfied arm for each
/// disjunctive (`any_of`) requirement. Used by the caller to record arm
/// attribution in the derivation step.
fn profile_satisfied(
    ctx: &ProofContext,
    p: &Permission,
    now: DateTime<Utc>,
    consulted: &mut Vec<String>,
    provenance_mismatch: &mut bool,
    dead_credential: &mut bool,
    satisfied_arms: &mut Vec<String>,
) -> ProfileCheckResult {
    let profile = match ctx.profiles.iter().find(|pr| &pr.permission == p) {
        Some(pr) => pr,
        None => return ProfileCheckResult::NoProfile,
    };

    for req in &profile.required_gaps {
        if !check_requirement(
            ctx,
            req,
            now,
            consulted,
            provenance_mismatch,
            dead_credential,
            satisfied_arms,
        ) {
            return ProfileCheckResult::GapNotMet;
        }
    }

    ProfileCheckResult::Satisfied
}

/// Check a single `GapRequirement` (conjunctive or disjunctive). Returns true
/// iff satisfied. For disjunctive (`any_of`) requirements, the satisfied arm's
/// gap_id (or a nested-disjunction label) is appended to `satisfied_arms`.
fn check_requirement(
    ctx: &ProofContext,
    req: &crate::gap::GapRequirement,
    now: DateTime<Utc>,
    consulted: &mut Vec<String>,
    provenance_mismatch: &mut bool,
    dead_credential: &mut bool,
    satisfied_arms: &mut Vec<String>,
) -> bool {
    if let Some(arms) = &req.any_of {
        for arm in arms {
            let mut nested: Vec<String> = vec![];
            if check_requirement(
                ctx,
                arm,
                now,
                consulted,
                provenance_mismatch,
                dead_credential,
                &mut nested,
            ) {
                let label = if arm.any_of.is_some() {
                    format!("any_of[{}]", nested.join(","))
                } else {
                    arm.gap_id.clone()
                };
                satisfied_arms.push(label);
                return true;
            }
        }
        return false;
    }

    let gap = match ctx.find_gap(&req.gap_id) {
        Some(g) => g,
        None => return false,
    };
    let effective_status = effective_gap_status(
        ctx,
        gap,
        now,
        consulted,
        provenance_mismatch,
        dead_credential,
    );
    req.minimum_status.satisfied_by(&effective_status)
}

/// Compute the effective gap status for a gap, considering only tokens whose
/// provenance hash matches the context exactly and whose status is usable.
fn effective_gap_status(
    ctx: &ProofContext,
    gap: &crate::gap::GapRecord,
    now: DateTime<Utc>,
    consulted: &mut Vec<String>,
    provenance_mismatch: &mut bool,
    dead_credential: &mut bool,
) -> GapStatus {
    let base_status = gap.status.clone();
    let mut best_status = base_status;

    for token in ctx.tokens_for_gap(&gap.gap_id) {
        if !verify_provenance(
            token,
            &ctx.claim_id,
            &ctx.candidate_id,
            &ctx.context_id,
            &ctx.allowed_use,
        ) {
            *provenance_mismatch = true;
            continue;
        }

        if !token.status.is_usable() {
            *dead_credential = true;
            continue;
        }

        if !token.is_live(now) {
            continue;
        }

        consulted.push(token.token_id.clone());

        if token.closes_gaps.iter().any(|g| g == &gap.gap_id) {
            best_status = GapStatus::Closed;
            break;
        } else if token.bounds_gaps.iter().any(|g| g == &gap.gap_id)
            && best_status < GapStatus::Bounded(crate::gap::Bound::infinity())
        {
            best_status = GapStatus::Bounded(crate::gap::Bound::infinity());
        }
    }

    best_status
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::context::{Membership, Scope};
    use crate::default_levels;
    use crate::gap::{GapRecord, GapRequirement, Profile, RequiredStatus};
    use crate::token::{compute_provenance_hash, ProofToken, TokenStatus};
    use chrono::Utc;

    fn minimal_ctx(membership: Membership) -> ProofContext {
        ProofContext {
            claim_id: "claim-1".into(),
            candidate_id: "z-1".into(),
            context_id: "ctx-1".into(),
            context_fingerprint: "fp-1".into(),
            allowed_use: "diagnostics".into(),
            disallowed_uses: vec![],
            scope: Scope::default(),
            gaps: vec![],
            profiles: vec![],
            tokens: vec![],
            expiry: Expiry::never(),
            authority_ceiling: None,
            permission_ceiling: None,
            membership,
            expected_chain_hash: None,
        }
    }

    fn make_token(closes: Vec<String>, ctx: &ProofContext) -> ProofToken {
        let hash = compute_provenance_hash(
            &ctx.claim_id,
            &ctx.candidate_id,
            &ctx.context_id,
            &ctx.allowed_use,
        );
        ProofToken {
            token_id: format!("tok-{}", uuid::Uuid::new_v4()),
            token_type: "TEST_TOKEN".into(),
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
    fn out_of_class_returns_bottom() {
        let ctx = minimal_ctx(Membership::OutOfClassExact);
        let j = compile(ctx).unwrap();
        assert_eq!(j.permission, default_levels::OOC());
    }

    #[test]
    fn no_profiles_returns_bottom() {
        let ctx = minimal_ctx(Membership::InClass);
        let j = compile(ctx).unwrap();
        assert_eq!(j.permission, default_levels::OOC());
    }

    #[test]
    fn satisfied_profile_emits_correct_permission() {
        let mut ctx = minimal_ctx(Membership::InClass);
        ctx.gaps.push(GapRecord::closed("g1", "calibration_gap"));
        ctx.profiles.push(Profile {
            permission: default_levels::DIA(),
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
                any_of: None,
            }],
        });
        let tok = make_token(vec!["g1".into()], &ctx);
        ctx.tokens.push(tok);
        let j = compile(ctx).unwrap();
        assert_eq!(j.permission, default_levels::DIA());
    }

    #[test]
    fn authority_ceiling_limits_outcome() {
        let mut ctx = minimal_ctx(Membership::InClass);
        ctx.gaps.push(GapRecord::closed("g1", "gap"));
        ctx.profiles.push(Profile {
            permission: default_levels::AAA(),
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
                any_of: None,
            }],
        });
        let tok = make_token(vec!["g1".into()], &ctx);
        ctx.tokens.push(tok);
        ctx.authority_ceiling = Some(default_levels::DIA());
        let j = compile(ctx).unwrap();
        assert_eq!(j.permission, default_levels::DIA());
    }

    #[test]
    fn wrong_provenance_token_yields_ref() {
        let mut ctx = minimal_ctx(Membership::InClass);
        ctx.gaps.push(GapRecord::open("g1", "calibration_gap"));
        ctx.profiles.push(Profile {
            permission: default_levels::DIA(),
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
                any_of: None,
            }],
        });
        let bad_token = ProofToken {
            token_id: "bad-tok".into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec![],
            provenance_hash: "deadbeef".repeat(8),
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
            negative_control_id: None,
        };
        ctx.tokens.push(bad_token);
        let j = compile(ctx).unwrap();
        assert_eq!(j.permission, default_levels::REF());
    }

    #[test]
    fn disallowed_uses_cap_at_rol() {
        let mut ctx = minimal_ctx(Membership::InClass);
        ctx.gaps.push(GapRecord::closed("g1", "gap"));
        ctx.profiles.push(Profile {
            permission: default_levels::AAA(),
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
                any_of: None,
            }],
        });
        let tok = make_token(vec!["g1".into()], &ctx);
        ctx.tokens.push(tok);
        ctx.disallowed_uses = vec!["production-write".into()];
        let j = compile(ctx).unwrap();
        let chain = PermissionChain::default_chain();
        assert!(chain.rank(&j.permission).unwrap() <= chain.rank(&default_levels::ROL()).unwrap());
    }

    #[test]
    fn judgment_carries_chain_hash() {
        let ctx = minimal_ctx(Membership::InClass);
        let j = compile(ctx).unwrap();
        assert_eq!(j.chain_hash, PermissionChain::default_chain().chain_hash());
    }
}
