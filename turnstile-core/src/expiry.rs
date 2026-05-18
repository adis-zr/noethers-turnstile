/// Expiry types and the LiveJudgment wrapper.
use std::collections::HashMap;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use tracing::{debug, warn};

use crate::compiler::Judgment;
use crate::context::ProofContext;
use crate::permission::Permission;
use crate::token::NegativeControlStatus;

/// The expiry constraint on a judgment (`ε` in `Γ ⊢ z : p until ε`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Expiry {
    /// Hard deadline.  A `None` deadline never expires.
    pub deadline: Option<DateTime<Utc>>,
    /// Human-readable reason for the expiry (for audit).
    pub reason: Option<String>,
}

impl Expiry {
    /// An expiry that never fires.
    pub fn never() -> Self {
        Self {
            deadline: None,
            reason: None,
        }
    }

    /// An expiry that fires at `deadline`.
    pub fn at(deadline: DateTime<Utc>) -> Self {
        Self {
            deadline: Some(deadline),
            reason: None,
        }
    }

    /// An expiry that fires at `deadline` with an audit reason.
    pub fn at_with_reason(deadline: DateTime<Utc>, reason: impl Into<String>) -> Self {
        Self {
            deadline: Some(deadline),
            reason: Some(reason.into()),
        }
    }

    /// Returns `true` iff the expiry deadline has been reached or passed at `now`.
    pub fn fired(&self, now: DateTime<Utc>) -> bool {
        match self.deadline {
            Some(deadline) => now >= deadline,
            None => false,
        }
    }

    /// Minimum expiry: the one that fires earliest.
    pub fn min(self, other: Self) -> Self {
        match (self.deadline, other.deadline) {
            (Some(a), Some(b)) => {
                if a <= b {
                    Self {
                        deadline: Some(a),
                        reason: self.reason,
                    }
                } else {
                    Self {
                        deadline: Some(b),
                        reason: other.reason,
                    }
                }
            }
            (Some(a), None) => Self {
                deadline: Some(a),
                reason: self.reason,
            },
            (None, Some(b)) => Self {
                deadline: Some(b),
                reason: other.reason,
            },
            (None, None) => Self::never(),
        }
    }
}

/// Runtime context for evaluating whether a judgment is still live.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuntimeContext {
    /// Current wall-clock time for expiry evaluation.
    pub now: DateTime<Utc>,
    /// Runtime fingerprint for revalidation (must match the context fingerprint
    /// the judgment was compiled against).
    pub context_fingerprint: String,
    /// Live negative-control state map, keyed by token_id (T17).
    ///
    /// Only consulted when `strict_mode` is `true`.  Tokens absent from this
    /// map are treated as `Missing` in strict mode.
    #[serde(default)]
    pub negative_control_states: HashMap<String, NegativeControlStatus>,
    /// When `true`, every negative-control token in the compiled judgment must
    /// appear as `Live` in `negative_control_states`.  Any other state (or
    /// absence) floors the live permission to `REF` (T17).
    ///
    /// Defaults to `true`: strict mode is the safe default.
    #[serde(default = "default_strict_mode")]
    pub strict_mode: bool,
}

fn default_strict_mode() -> bool {
    true
}

impl RuntimeContext {
    /// Construct a runtime context with strict mode enabled and no NC state.
    pub fn new(now: DateTime<Utc>, context_fingerprint: impl Into<String>) -> Self {
        Self {
            now,
            context_fingerprint: context_fingerprint.into(),
            negative_control_states: HashMap::new(),
            strict_mode: true,
        }
    }

    /// Construct a runtime context with an explicit strict-mode flag and NC state map.
    pub fn with_nc_states(
        now: DateTime<Utc>,
        context_fingerprint: impl Into<String>,
        negative_control_states: HashMap<String, NegativeControlStatus>,
        strict_mode: bool,
    ) -> Self {
        Self {
            now,
            context_fingerprint: context_fingerprint.into(),
            negative_control_states,
            strict_mode,
        }
    }

    /// Check that this runtime context matches the context the judgment was
    /// compiled against (fingerprint equality).
    pub fn satisfies(&self, ctx: &ProofContext) -> bool {
        self.context_fingerprint == ctx.context_fingerprint
    }

    /// Check negative-control liveness for a set of token IDs (T17).
    ///
    /// Returns `Ok(())` if all NC tokens are live, or `Err(token_id)` for the
    /// first token that fails the liveness check.  In non-strict mode always
    /// returns `Ok(())`.
    pub fn check_negative_controls<'a>(
        &self,
        nc_token_ids: impl Iterator<Item = &'a str>,
    ) -> Result<(), String> {
        if !self.strict_mode {
            return Ok(());
        }
        for token_id in nc_token_ids {
            let state = self
                .negative_control_states
                .get(token_id)
                .copied()
                .unwrap_or(NegativeControlStatus::Missing);
            if state != NegativeControlStatus::Live {
                return Err(token_id.to_owned());
            }
        }
        Ok(())
    }
}

/// A live judgment: a compiled judgment bound to a runtime context.
///
/// The lifetime `'ctx` ties the `LiveJudgment` to the `RuntimeContext` it was
/// created from, preventing stale-read attacks at the type-system level.
///
/// The only way to read `permission()` is to hold a live reference to the
/// `RuntimeContext`; if that context is dropped or mutated, the borrow checker
/// prevents the read.
pub struct LiveJudgment<'ctx> {
    inner: Judgment,
    runtime: &'ctx RuntimeContext,
}

impl<'ctx> LiveJudgment<'ctx> {
    pub fn new(inner: Judgment, runtime: &'ctx RuntimeContext) -> Self {
        Self { inner, runtime }
    }

    /// The runtime context this judgment is bound to.
    pub fn runtime(&self) -> &RuntimeContext {
        self.runtime
    }

    /// Read the effective permission at this instant.
    ///
    /// Returns `Permission::EXP` if the judgment has expired or if the runtime
    /// context fingerprint does not match the compile-time context.
    ///
    /// Returns `Permission::REF` if strict mode is enabled and any
    /// negative-control token in the judgment is not `Live` in the runtime
    /// context's NC state map (T17).
    pub fn permission(&self) -> Permission {
        if self.inner.expiry.fired(self.runtime.now) {
            warn!(
                candidate_id = %self.inner.context.candidate_id,
                claim_id = %self.inner.context.claim_id,
                "judgment expired; returning EXP"
            );
            return Permission::EXP;
        }
        if !self.runtime.satisfies(&self.inner.context) {
            warn!(
                candidate_id = %self.inner.context.candidate_id,
                claim_id = %self.inner.context.claim_id,
                runtime_fingerprint = %self.runtime.context_fingerprint,
                compile_fingerprint = %self.inner.context.context_fingerprint,
                "fingerprint mismatch; returning OOC (judgment applied in wrong context)"
            );
            // A fingerprint mismatch means this judgment is being evaluated in a
            // different context than it was compiled against — the judgment should
            // not be applied at all.  OOC (not EXP) is the correct outcome: the
            // candidate is out-of-class with respect to *this* runtime context.
            // EXP is reserved for "was valid, now expired"; it must not be confused
            // with "wrong context entirely".
            return Permission::OOC;
        }
        // T17: negative-control liveness check.
        let nc_ids = self
            .inner
            .context
            .tokens
            .iter()
            .filter(|t| t.is_negative_control)
            .map(|t| t.token_id.as_str());
        if let Err(failed_id) = self.runtime.check_negative_controls(nc_ids) {
            warn!(
                candidate_id = %self.inner.context.candidate_id,
                claim_id = %self.inner.context.claim_id,
                failed_nc_token_id = %failed_id,
                "T17: negative-control not live; flooring to REF"
            );
            return Permission::REF;
        }
        debug!(
            candidate_id = %self.inner.context.candidate_id,
            claim_id = %self.inner.context.claim_id,
            permission = %self.inner.permission,
            "live permission read"
        );
        self.inner.permission
    }

    /// Expiry deadline, if any.
    pub fn deadline(&self) -> Option<DateTime<Utc>> {
        self.inner.expiry.deadline
    }

    /// Underlying judgment (for audit / serialization only).
    ///
    /// WARNING: Do not read `judgment().permission` for admissibility decisions.
    /// That field bypasses expiry, fingerprint verification, and negative-control
    /// liveness checks. `LiveJudgment::permission()` is the only correct read path.
    pub fn judgment(&self) -> &Judgment {
        &self.inner
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Duration;

    fn dummy_ctx() -> ProofContext {
        crate::context::ProofContext {
            claim_id: "c".into(),
            candidate_id: "z".into(),
            context_id: "ctx".into(),
            context_fingerprint: "fp".into(),
            allowed_use: "use".into(),
            disallowed_uses: vec![],
            scope: crate::context::Scope::default(),
            gaps: vec![],
            profiles: vec![],
            tokens: vec![],
            expiry: Expiry::never(),
            authority_ceiling: Permission::AAA,
            permission_ceiling: Permission::AAA,
            membership: crate::context::Membership::InClass,
        }
    }

    #[test]
    fn expiry_fires_at_deadline() {
        let t = Utc::now();
        let exp = Expiry::at(t);
        assert!(exp.fired(t));
        assert!(exp.fired(t + Duration::nanoseconds(1)));
        assert!(!exp.fired(t - Duration::nanoseconds(1)));
    }

    #[test]
    fn live_judgment_returns_exp_when_expired() {
        let now = Utc::now();
        let rt = RuntimeContext::new(now + Duration::seconds(10), "fp");
        let judgment = Judgment {
            context: dummy_ctx(),
            permission: Permission::DIA,
            expiry: Expiry::at(now + Duration::seconds(5)),
            derivation: crate::audit::Derivation::default(),
        };
        let live = LiveJudgment::new(judgment, &rt);
        assert_eq!(live.permission(), Permission::EXP);
    }

    #[test]
    fn live_judgment_returns_ooc_on_fingerprint_mismatch() {
        let now = Utc::now();
        let rt = RuntimeContext::new(now, "wrong-fp");
        let judgment = Judgment {
            context: dummy_ctx(),
            permission: Permission::DIA,
            expiry: Expiry::never(),
            derivation: crate::audit::Derivation::default(),
        };
        let live = LiveJudgment::new(judgment, &rt);
        // Fingerprint mismatch = wrong context entirely, not expiry. OOC, not EXP.
        assert_eq!(live.permission(), Permission::OOC);
    }

    #[test]
    fn live_judgment_returns_permission_when_valid() {
        let now = Utc::now();
        let rt = RuntimeContext::new(now, "fp");
        let judgment = Judgment {
            context: dummy_ctx(),
            permission: Permission::DIA,
            expiry: Expiry::never(),
            derivation: crate::audit::Derivation::default(),
        };
        let live = LiveJudgment::new(judgment, &rt);
        assert_eq!(live.permission(), Permission::DIA);
    }

    #[test]
    fn expiry_min_picks_earliest() {
        let t1 = Utc::now();
        let t2 = t1 + Duration::seconds(100);
        let e1 = Expiry::at(t1);
        let e2 = Expiry::at(t2);
        assert_eq!(e1.clone().min(e2.clone()).deadline, Some(t1));
        assert_eq!(e2.min(e1).deadline, Some(t1));
    }
}
