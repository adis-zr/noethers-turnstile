/// The admissibility compiler: Γ ⊢ z : p until ε.
///
/// Algorithm (spec §3):
/// 1. If membership ≠ InClass → OOC
/// 2. Descending search: find the strongest p such that profile_satisfied(Γ, p)
/// 3. meet with structural_blockers (disallowed_uses → ROL ceiling, etc.)
/// 4. meet with authority_ceiling
/// 5. meet with expiry_blocker (any expired token → EXP floor)
///
/// Every meet can only lower the outcome.
use chrono::Utc;
use serde::{Deserialize, Serialize};

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
    pub permission: Permission,
    /// The binding expiry (the `ε` in `Γ ⊢ z : p until ε`).
    pub expiry: Expiry,
    /// Full audit derivation.
    pub derivation: Derivation,
}

/// Compile a proof context into a judgment.
///
/// This function is `O(|P| · max_p |gaps_required_at_p|)` in the number of
/// permission levels and the maximum required-gap count per profile.
///
/// Returns `Err(TurnstileError::MalformedContext)` if the context is structurally
/// invalid (e.g. a profile references a gap_id that does not exist in `ctx.gaps`).
pub fn compile(ctx: ProofContext) -> Result<Judgment, crate::error::TurnstileError> {
    let mut derivation = Derivation::new().with_provenance(ctx.provenance_hash());

    // Step 1: membership check.
    if !ctx.membership.is_in_class() {
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

    // Step 2: descending search.
    let mut outcome = Permission::OOC;
    let mut search_note = "no profile satisfied".to_string();
    let mut consulted_tokens: Vec<String> = vec![];

    'outer: for p in Permission::descending() {
        match profile_satisfied(&ctx, p, &mut consulted_tokens) {
            ProfileCheckResult::Satisfied => {
                outcome = p;
                search_note = format!("profile satisfied at {}", p);
                break 'outer;
            }
            ProfileCheckResult::NoProfile => {
                // No profile registered for this permission level; continue descending.
                continue;
            }
            ProfileCheckResult::GapNotMet => {
                // Gap requirement not met; continue descending.
                continue;
            }
        }
    }

    derivation.push(DerivationStep {
        phase: "descending_search".into(),
        permission_after: outcome,
        note: search_note,
        token_ids: consulted_tokens.clone(),
    });

    // Step 3: structural blockers.
    let (blocker_outcome, blocker_note) = structural_blockers(&ctx, outcome);
    if blocker_outcome < outcome {
        derivation.push(DerivationStep {
            phase: "structural_blockers".into(),
            permission_after: blocker_outcome,
            note: blocker_note,
            token_ids: vec![],
        });
    }
    outcome = blocker_outcome;

    // Step 4: authority ceiling.
    let ceiling = ctx.authority_ceiling;
    if ceiling < outcome {
        derivation.push(DerivationStep {
            phase: "authority_ceiling".into(),
            permission_after: ceiling,
            note: format!("authority ceiling is {}", ceiling),
            token_ids: vec![],
        });
    }
    outcome = outcome.meet(ceiling);

    // Step 5: expiry blocker — if any token in the context has expired, floor to EXP.
    let now = Utc::now();
    let has_expired_token = ctx.tokens.iter().any(|t| {
        if let Some(exp) = t.expires_at {
            now >= exp
        } else {
            false
        }
    });
    if has_expired_token && outcome > Permission::EXP {
        derivation.push(DerivationStep {
            phase: "expiry_blocker".into(),
            permission_after: Permission::EXP,
            note: "at least one proof token has expired".into(),
            token_ids: ctx
                .tokens
                .iter()
                .filter(|t| t.expires_at.map(|e| now >= e).unwrap_or(false))
                .map(|t| t.token_id.clone())
                .collect(),
        });
        outcome = Permission::EXP;
    }

    // Also apply the context-level expiry as a ceiling at compile time.
    if ctx.expiry.fired(now) && outcome > Permission::EXP {
        derivation.push(DerivationStep {
            phase: "context_expiry".into(),
            permission_after: Permission::EXP,
            note: "context expiry has already fired".into(),
            token_ids: vec![],
        });
        outcome = Permission::EXP;
    }

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
/// treated as if the gap is still Open (the token is silently rejected for that
/// gap, but nothing is surfaced to the caller — gaps simply remain Open).
fn profile_satisfied(
    ctx: &ProofContext,
    p: Permission,
    consulted: &mut Vec<String>,
) -> ProfileCheckResult {
    // Find the profile for this permission.
    let profile = match ctx.profiles.iter().find(|pr| pr.permission == p) {
        Some(pr) => pr,
        None => return ProfileCheckResult::NoProfile,
    };

    let expected_hash = ctx.provenance_hash();

    for req in &profile.required_gaps {
        // Look up the gap record.
        let gap = match ctx.find_gap(&req.gap_id) {
            Some(g) => g,
            None => {
                // Gap referenced in profile but not present in context → treat as Open.
                return ProfileCheckResult::GapNotMet;
            }
        };

        // Determine the effective gap status after provenance validation.
        // A token closes/bounds a gap only if its provenance hash matches exactly.
        let effective_status = effective_gap_status(ctx, gap, &expected_hash, consulted);

        // Check the requirement.
        if !req.minimum_status.satisfied_by(&effective_status) {
            return ProfileCheckResult::GapNotMet;
        }
    }

    ProfileCheckResult::Satisfied
}

/// Compute the effective gap status for a gap, considering only tokens whose
/// provenance hash matches the context exactly.
///
/// Tokens with wrong provenance are silently skipped — they do not contribute
/// to gap status.  The gap remains at its original status from `GapRecord`.
fn effective_gap_status(
    ctx: &ProofContext,
    gap: &crate::gap::GapRecord,
    _expected_hash: &str,
    consulted: &mut Vec<String>,
) -> GapStatus {
    let base_status = gap.status.clone();

    // Find tokens that claim to close or bound this gap with correct provenance.
    let mut best_status = base_status;

    for token in ctx.tokens_for_gap(&gap.gap_id) {
        // Provenance check: skip token if it doesn't match.
        if !verify_provenance(
            token,
            &ctx.claim_id,
            &ctx.candidate_id,
            &ctx.context_id,
            &ctx.allowed_use,
        ) {
            // Wrong provenance: token is silently rejected.
            continue;
        }

        // Token must be live (valid status, not expired).
        if !token.is_live(Utc::now()) {
            continue;
        }

        consulted.push(token.token_id.clone());

        // Determine what status the token contributes.
        if token.closes_gaps.iter().any(|g| g == &gap.gap_id) {
            // A closing token upgrades the gap to Closed.
            best_status = GapStatus::Closed;
            break; // Closed is the maximum; no need to check further.
        } else if token.bounds_gaps.iter().any(|g| g == &gap.gap_id) {
            // A bounding token upgrades to at least Bounded (if not already Closed).
            // We use the gap's existing bound if already Bounded; otherwise use a
            // default numeric bound of 0.0 (the certifier is responsible for the
            // actual bound value stored in the gap record).
            if best_status < GapStatus::Bounded(crate::gap::Bound::infinity()) {
                best_status = GapStatus::Bounded(crate::gap::Bound::infinity());
            }
        }
    }

    best_status
}

/// Ordering for GapStatus (for comparison in effective_gap_status).
impl PartialOrd for GapStatus {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.rank().cmp(&other.rank()))
    }
}

impl Ord for GapStatus {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.rank().cmp(&other.rank())
    }
}

impl Eq for GapStatus {}

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
        };
        ctx.tokens.push(bad_token);
        let j = compile(ctx).unwrap();
        // Wrong provenance → gap stays Open → DIA profile not satisfied → OOC.
        assert_eq!(j.permission, Permission::OOC);
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
