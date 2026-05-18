/// The admissibility compiler: Γ ⊢ z : p until ε.
///
/// Algorithm (spec §3):
/// 1. If membership ≠ InClass → OOC
/// 2. Early context expiry check — halt before evaluating tokens (spec §14 step 4)
/// 3. Descending search: find the strongest p such that profile_satisfied(Γ, p)
/// 4. meet with structural_blockers (PROVENANCE_MISMATCH → REF; disallowed_uses → ROL ceiling)
///    5a. meet with authority_ceiling (structural delegation limit)
///    5b. meet with permission_ceiling (non-promotion ceiling T9, set by compose())
/// 6. meet with expiry_blocker (any expired token with valid provenance → EXP floor)
/// 7. record negative-control token IDs in the derivation (liveness checked at runtime)
///
/// Every meet can only lower the outcome.
use chrono::Utc;
use serde::{Deserialize, Serialize};
use tracing::{debug, instrument, warn};

use crate::audit::{Derivation, DerivationStep};
use crate::context::ProofContext;
use crate::expiry::Expiry;
use crate::gap::GapStatus;
use crate::permission::Permission;
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
    /// verification, and negative-control liveness checks at read time.  Reading
    /// `permission` directly bypasses all of those runtime guards.
    pub permission: Permission,
    /// The binding expiry (the `ε` in `Γ ⊢ z : p until ε`).
    pub expiry: Expiry,
    /// Full audit derivation.
    pub derivation: Derivation,
}

/// Validate structural preconditions on a context before compilation.
///
/// Returns `Err(MalformedContext)` for any of:
///   - A profile references a `gap_id` not present in `ctx.gaps`.
///   - `ctx.gaps` contains duplicate `gap_id` values.
///   - `ctx.profiles` contains two entries with the same `permission` level.
///   - `ctx.allowed_use` is empty.
fn validate_context(ctx: &ProofContext) -> Result<(), crate::error::TurnstileError> {
    if ctx.allowed_use.is_empty() {
        return Err(crate::error::TurnstileError::MalformedContext(
            "allowed_use must not be empty".into(),
        ));
    }

    // Check for duplicate gap_ids.
    let mut seen_gap_ids = std::collections::HashSet::new();
    for g in &ctx.gaps {
        if !seen_gap_ids.insert(g.gap_id.as_str()) {
            return Err(crate::error::TurnstileError::MalformedContext(format!(
                "duplicate gap_id '{}'",
                g.gap_id
            )));
        }
    }

    // Check that all gap_ids referenced by profiles exist.
    for profile in &ctx.profiles {
        for req in &profile.required_gaps {
            if ctx.find_gap(&req.gap_id).is_none() {
                return Err(crate::error::TurnstileError::MalformedContext(format!(
                    "profile for {:?} references unknown gap_id '{}'",
                    profile.permission, req.gap_id
                )));
            }
        }
    }

    // Check for duplicate permission levels in profiles.
    let mut seen_perms = std::collections::HashSet::new();
    for profile in &ctx.profiles {
        let key = profile.permission as u8;
        if !seen_perms.insert(key) {
            return Err(crate::error::TurnstileError::MalformedContext(format!(
                "duplicate profile for permission level {:?}",
                profile.permission
            )));
        }
    }

    Ok(())
}

/// Compile a proof context into a judgment.
///
/// This function is `O(|P| · max_p |gaps_required_at_p|)` in the number of
/// permission levels and the maximum required-gap count per profile.
///
/// Returns `Err(TurnstileError::MalformedContext)` if the context is structurally
/// invalid (e.g. a profile references a gap_id that does not exist in `ctx.gaps`,
/// duplicate gap_ids, duplicate permission levels in profiles, or empty
/// `allowed_use`).
#[instrument(
    name = "turnstile.compile",
    skip(ctx),
    fields(
        claim_id = %ctx.claim_id,
        candidate_id = %ctx.candidate_id,
        context_id = %ctx.context_id,
        allowed_use = %ctx.allowed_use,
    )
)]
pub fn compile(ctx: ProofContext) -> Result<Judgment, crate::error::TurnstileError> {
    validate_context(&ctx)?;

    let mut derivation = Derivation::new().with_provenance(ctx.provenance_hash());

    // Step 1: membership check.
    if !ctx.membership.is_in_class() {
        debug!(
            phase = "membership_check",
            membership = ?ctx.membership,
            permission = "OOC",
            "out-of-class membership: emitting OOC"
        );
        let step = DerivationStep {
            phase: "membership_check".into(),
            permission_after: Permission::OOC,
            note: format!("out-of-class membership: {:?}", ctx.membership),
            token_ids: vec![],
        };
        derivation.push(step);
        return Ok(Judgment {
            permission: Permission::OOC,
            expiry: ctx.expiry.clone(),
            derivation,
            context: ctx,
        });
    }

    // Step 2: early expiry check — halt before touching any tokens (spec §14 step 4).
    let now = Utc::now();
    if ctx.expiry.fired(now) {
        warn!(
            phase = "context_expiry",
            "context expiry has already fired; emitting EXP"
        );
        derivation.push(DerivationStep {
            phase: "context_expiry".into(),
            permission_after: Permission::EXP,
            note: "context expiry fired before token evaluation".into(),
            token_ids: vec![],
        });
        return Ok(Judgment {
            permission: Permission::EXP,
            expiry: ctx.expiry.clone(),
            derivation,
            context: ctx,
        });
    }

    // Step 3: descending search.
    // outcome starts at UNS: "profile exists but no positive permission satisfiable
    // given the current evidence."  REF is reserved for explicit structural refusals
    // (wrong-provenance token, step 4 blocker).  OOC is reserved for out-of-class
    // membership (step 1, already handled above).
    let mut outcome = Permission::UNS;
    let mut search_note = "no profile satisfied".to_string();
    let mut consulted_tokens: Vec<String> = vec![];
    let mut had_any_profile = false;
    let mut provenance_mismatch_seen = false;
    let mut dead_credential_seen = false;

    'outer: for p in Permission::descending() {
        match profile_satisfied(
            &ctx,
            p,
            &mut consulted_tokens,
            &mut provenance_mismatch_seen,
            &mut dead_credential_seen,
        ) {
            ProfileCheckResult::Satisfied => {
                outcome = p;
                search_note = format!("profile satisfied at {}", p);
                had_any_profile = true;
                break 'outer;
            }
            ProfileCheckResult::NoProfile => {
                continue;
            }
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

    // If no profiles were defined at all, emit OOC (undefined class behavior).
    if !had_any_profile {
        outcome = Permission::OOC;
        search_note = "no profiles defined".to_string();
    }

    debug!(
        phase = "descending_search",
        permission = %outcome,
        note = %search_note,
        "descending search complete"
    );
    derivation.push(DerivationStep {
        phase: "descending_search".into(),
        permission_after: outcome,
        note: search_note,
        token_ids: consulted_tokens.clone(),
    });

    // Step 4: structural blockers — both PROVENANCE_MISMATCH and DEAD_CREDENTIAL force a
    // REF meet when no profile was satisfied (outcome < DIA).
    //
    // Guard is `outcome < DIA` (not `outcome <= REF`) because outcome now initializes to UNS
    // when profiles exist but none are satisfied.  "No satisfied profile" covers UNS, REF,
    // EXP, OOC — all are below DIA.  If a correct-provenance token did satisfy a profile
    // (outcome ≥ DIA), these blockers are suppressed: the profile was met legitimately.
    //
    // PROVENANCE_MISMATCH: a token whose provenance hash doesn't match this context was
    // presented — active credential forgery/misdirection, not mere absence.
    //
    // DEAD_CREDENTIAL: a token with correct provenance but non-usable status (Invalid,
    // Revoked, Malformed, or the Expired variant) was presented — the credential was
    // explicitly revoked/rejected, not merely absent.  Time-expired tokens (Valid status +
    // expires_at < now) are handled separately by the step 6 EXP floor; they don't trigger
    // this blocker.
    let apply_ref_blocker =
        (provenance_mismatch_seen || dead_credential_seen) && outcome < Permission::DIA;
    if apply_ref_blocker {
        let note = match (provenance_mismatch_seen, dead_credential_seen) {
            (true, true) => {
                "PROVENANCE_MISMATCH + DEAD_CREDENTIAL: rejected token(s) seen; REF meet applied"
                    .to_string()
            }
            (true, false) => {
                "PROVENANCE_MISMATCH: token(s) with wrong provenance seen; REF meet applied"
                    .to_string()
            }
            (false, true) => {
                "DEAD_CREDENTIAL: token(s) with non-usable status seen; REF meet applied"
                    .to_string()
            }
            (false, false) => unreachable!(),
        };
        warn!(
            phase = "structural_blockers",
            provenance_mismatch = provenance_mismatch_seen,
            dead_credential = dead_credential_seen,
            "structural blocker(s) detected; meeting outcome with REF"
        );
        derivation.push(DerivationStep {
            phase: "structural_blockers".into(),
            permission_after: outcome.meet(Permission::REF),
            note,
            token_ids: vec![],
        });
        outcome = outcome.meet(Permission::REF);
    }

    let (blocker_outcome, blocker_note) = structural_blockers(&ctx, outcome);
    if blocker_outcome < outcome {
        warn!(
            phase = "structural_blockers",
            before = %outcome,
            after = %blocker_outcome,
            note = %blocker_note,
            "structural blocker lowered permission"
        );
        derivation.push(DerivationStep {
            phase: "structural_blockers".into(),
            permission_after: blocker_outcome,
            note: blocker_note,
            token_ids: vec![],
        });
    }
    outcome = blocker_outcome;

    // Step 5a: authority ceiling (structural delegation limit).
    let ceiling = ctx.authority_ceiling;
    if ceiling < outcome {
        warn!(
            phase = "authority_ceiling",
            ceiling = %ceiling,
            before = %outcome,
            "authority ceiling lowered permission"
        );
        derivation.push(DerivationStep {
            phase: "authority_ceiling".into(),
            permission_after: ceiling,
            note: format!("authority ceiling is {}", ceiling),
            token_ids: vec![],
        });
    }
    outcome = outcome.meet(ceiling);

    // Step 5b: permission ceiling (non-promotion ceiling, T9).
    // Set by compose() to meet(compile(g1), compile(g2)).  AAA on contexts not
    // produced by composition (defaults to unconstrained).
    let perm_ceiling = ctx.permission_ceiling;
    if perm_ceiling < outcome {
        warn!(
            phase = "permission_ceiling",
            ceiling = %perm_ceiling,
            before = %outcome,
            "non-promotion ceiling (T9) lowered permission"
        );
        derivation.push(DerivationStep {
            phase: "permission_ceiling".into(),
            permission_after: perm_ceiling,
            note: format!("non-promotion ceiling (T9) is {}", perm_ceiling),
            token_ids: vec![],
        });
    }
    outcome = outcome.meet(perm_ceiling);

    // Step 6: token-level expiry blocker — if any Valid-status token with correct
    // provenance has expired, floor to EXP.  Tokens with wrong provenance are
    // invisible to the compiler and must not trigger this blocker (a token with
    // bad provenance was already rejected in effective_gap_status; letting it also
    // trigger EXP would be a correctness violation).
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
    if !expired_ids.is_empty() && outcome > Permission::EXP {
        warn!(
            phase = "expiry_blocker",
            expired_token_ids = ?expired_ids,
            "expired proof token(s) flooring permission to EXP"
        );
        derivation.push(DerivationStep {
            phase: "expiry_blocker".into(),
            permission_after: Permission::EXP,
            note: "at least one proof token has expired".into(),
            token_ids: expired_ids,
        });
        outcome = outcome.meet(Permission::EXP);
    }

    // Step 7: record negative-control token IDs in the derivation.
    // Liveness is checked at runtime in LiveJudgment::permission() (T17).
    // We record them here so the derivation is self-contained for audit.
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
            nc_token_ids = ?nc_token_ids,
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
/// Token provenance is checked bitwise: any token with wrong provenance is
/// treated as if the gap is still Open and `provenance_mismatch` is set so the
/// caller can apply a REF-meet.  Any token with correct provenance but non-usable
/// status sets `dead_credential` so the same REF-meet applies.
fn profile_satisfied(
    ctx: &ProofContext,
    p: Permission,
    consulted: &mut Vec<String>,
    provenance_mismatch: &mut bool,
    dead_credential: &mut bool,
) -> ProfileCheckResult {
    let profile = match ctx.profiles.iter().find(|pr| pr.permission == p) {
        Some(pr) => pr,
        None => return ProfileCheckResult::NoProfile,
    };

    for req in &profile.required_gaps {
        let gap = match ctx.find_gap(&req.gap_id) {
            Some(g) => g,
            None => {
                return ProfileCheckResult::GapNotMet;
            }
        };

        let effective_status =
            effective_gap_status(ctx, gap, consulted, provenance_mismatch, dead_credential);

        if !req.minimum_status.satisfied_by(&effective_status) {
            return ProfileCheckResult::GapNotMet;
        }
    }

    ProfileCheckResult::Satisfied
}

/// Compute the effective gap status for a gap, considering only tokens whose
/// provenance hash matches the context exactly and whose status is usable.
///
/// Tokens with wrong provenance set `provenance_mismatch`; tokens with correct
/// provenance but non-usable status (Invalid, Revoked, Malformed, Expired variant)
/// set `dead_credential`.  Both flags cause a REF-meet in step 4.
///
/// Time-expired tokens (Valid status + `expires_at` < now) are silently skipped
/// here; they are handled by the step 6 EXP floor.
fn effective_gap_status(
    ctx: &ProofContext,
    gap: &crate::gap::GapRecord,
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
            // Wrong provenance: token is rejected. Record the structural failure.
            *provenance_mismatch = true;
            continue;
        }

        // Correct provenance but non-usable status = explicitly rejected credential.
        if !token.status.is_usable() {
            *dead_credential = true;
            continue;
        }

        if !token.is_live(Utc::now()) {
            // Time-expired (Valid + past expires_at): silently skip — step 6 handles EXP.
            continue;
        }

        consulted.push(token.token_id.clone());

        if token.closes_gaps.iter().any(|g| g == &gap.gap_id) {
            best_status = GapStatus::Closed;
            break;
        } else if token.bounds_gaps.iter().any(|g| g == &gap.gap_id)
            && best_status < GapStatus::Bounded(crate::gap::Bound::infinity())
        {
            // Any Bounded(_) value has rank 1; this condition is false when best_status is
            // already Bounded.  The branch exists to prevent overwriting a Closed status
            // downward — once Closed, the break above fires first.
            best_status = GapStatus::Bounded(crate::gap::Bound::infinity());
        }
    }

    best_status
}

/// Structural blockers that can lower the outcome.
///
/// Current blockers:
/// - Any disallowed_use that fires a hard ceiling.
fn structural_blockers(ctx: &ProofContext, current: Permission) -> (Permission, String) {
    // For now, any non-empty disallowed_uses list imposes a ceiling of ROL.
    // This is conservative: if the context lists explicit disallowed uses,
    // automatic/unlimited actions are blocked.
    if !ctx.disallowed_uses.is_empty() {
        let ceiling = Permission::ROL;
        if ceiling < current {
            return (
                current.meet(ceiling),
                format!(
                    "disallowed_uses present ({}), ceiling at ROL",
                    ctx.disallowed_uses.join(", ")
                ),
            );
        }
    }
    (current, String::new())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::context::{Membership, Scope};
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
            authority_ceiling: Permission::AAA,
            permission_ceiling: Permission::AAA,
            membership,
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
        }
    }

    #[test]
    fn out_of_class_returns_ooc() {
        let ctx = minimal_ctx(Membership::OutOfClassExact);
        let j = compile(ctx).unwrap();
        assert_eq!(j.permission, Permission::OOC);
    }

    #[test]
    fn no_profiles_returns_ooc() {
        let ctx = minimal_ctx(Membership::InClass);
        let j = compile(ctx).unwrap();
        assert_eq!(j.permission, Permission::OOC);
    }

    #[test]
    fn satisfied_profile_emits_correct_permission() {
        let mut ctx = minimal_ctx(Membership::InClass);
        ctx.gaps.push(GapRecord::closed("g1", "calibration_gap"));
        ctx.profiles.push(Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        });
        let tok = make_token(vec!["g1".into()], &ctx);
        ctx.tokens.push(tok);
        let j = compile(ctx).unwrap();
        assert_eq!(j.permission, Permission::DIA);
    }

    #[test]
    fn authority_ceiling_limits_outcome() {
        let mut ctx = minimal_ctx(Membership::InClass);
        ctx.gaps.push(GapRecord::closed("g1", "gap"));
        ctx.profiles.push(Profile {
            permission: Permission::AAA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        });
        let tok = make_token(vec!["g1".into()], &ctx);
        ctx.tokens.push(tok);
        ctx.authority_ceiling = Permission::DIA;
        let j = compile(ctx).unwrap();
        assert_eq!(j.permission, Permission::DIA);
    }

    #[test]
    fn wrong_provenance_token_leaves_gap_open() {
        let mut ctx = minimal_ctx(Membership::InClass);
        ctx.gaps.push(GapRecord::open("g1", "calibration_gap"));
        ctx.profiles.push(Profile {
            permission: Permission::DIA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        });
        // Token with wrong provenance.
        let bad_token = ProofToken {
            token_id: "bad-tok".into(),
            token_type: "TEST".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["g1".into()],
            bounds_gaps: vec![],
            provenance_hash: "deadbeef".repeat(8), // wrong
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "test".into(),
            details: serde_json::Value::Null,
            is_negative_control: false,
        };
        ctx.tokens.push(bad_token);
        let j = compile(ctx).unwrap();
        // Wrong provenance → PROVENANCE_MISMATCH structural failure → REF meet applied.
        // Candidate is in-class, profile exists but gap unmet → REF (not OOC).
        assert_eq!(j.permission, Permission::REF);
    }

    #[test]
    fn disallowed_uses_cap_at_rol() {
        let mut ctx = minimal_ctx(Membership::InClass);
        ctx.gaps.push(GapRecord::closed("g1", "gap"));
        ctx.profiles.push(Profile {
            permission: Permission::AAA,
            required_gaps: vec![GapRequirement {
                gap_id: "g1".into(),
                minimum_status: RequiredStatus::ClosedRequired,
            }],
        });
        let tok = make_token(vec!["g1".into()], &ctx);
        ctx.tokens.push(tok);
        ctx.disallowed_uses = vec!["production-write".into()];
        let j = compile(ctx).unwrap();
        assert!(j.permission <= Permission::ROL);
    }
}

// uuid is used in tests; add it as a dev dependency via the workspace
// (added to turnstile-core/Cargo.toml below)
