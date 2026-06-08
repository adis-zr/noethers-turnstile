//! Expiry types and the LiveJudgment wrapper.
use std::collections::HashMap;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use tracing::{debug, warn};

use crate::compiler::Judgment;
use crate::context::ProofContext;
use crate::permission::{ChainRole, Permission, PermissionChain};
use crate::token::NegativeControlStatus;

/// The expiry constraint on a judgment (`ε` in `Γ ⊢ z : p until ε`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Expiry {
    pub deadline: Option<DateTime<Utc>>,
    pub reason: Option<String>,
}

impl Expiry {
    pub fn never() -> Self {
        Self {
            deadline: None,
            reason: None,
        }
    }

    pub fn at(deadline: DateTime<Utc>) -> Self {
        Self {
            deadline: Some(deadline),
            reason: None,
        }
    }

    pub fn at_with_reason(deadline: DateTime<Utc>, reason: impl Into<String>) -> Self {
        Self {
            deadline: Some(deadline),
            reason: Some(reason.into()),
        }
    }

    pub fn fired(&self, now: DateTime<Utc>) -> bool {
        match self.deadline {
            Some(deadline) => now >= deadline,
            None => false,
        }
    }

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
    pub now: DateTime<Utc>,
    pub context_fingerprint: String,
    #[serde(default)]
    pub negative_control_states: HashMap<String, NegativeControlStatus>,
    #[serde(default = "default_strict_mode")]
    pub strict_mode: bool,
}

fn default_strict_mode() -> bool {
    true
}

impl RuntimeContext {
    pub fn new(now: DateTime<Utc>, context_fingerprint: impl Into<String>) -> Self {
        Self {
            now,
            context_fingerprint: context_fingerprint.into(),
            negative_control_states: HashMap::new(),
            strict_mode: true,
        }
    }

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

    pub fn satisfies(&self, ctx: &ProofContext) -> bool {
        self.context_fingerprint == ctx.context_fingerprint
    }

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
pub struct LiveJudgment<'ctx> {
    inner: Judgment,
    runtime: &'ctx RuntimeContext,
    chain: &'ctx PermissionChain,
}

impl<'ctx> LiveJudgment<'ctx> {
    /// Construct a live judgment bound to the default chain.
    pub fn new(inner: Judgment, runtime: &'ctx RuntimeContext) -> Self {
        Self {
            inner,
            runtime,
            chain: PermissionChain::default_chain(),
        }
    }

    /// Construct a live judgment bound to a specific chain.
    pub fn with_chain(
        inner: Judgment,
        runtime: &'ctx RuntimeContext,
        chain: &'ctx PermissionChain,
    ) -> Self {
        Self {
            inner,
            runtime,
            chain,
        }
    }

    pub fn runtime(&self) -> &RuntimeContext {
        self.runtime
    }

    pub fn chain(&self) -> &PermissionChain {
        self.chain
    }

    /// Read the effective permission at this instant.
    ///
    /// Returns `chain.role(ExpiryFloor)` if the judgment has expired.
    /// Returns `chain.role(Bottom)` if the runtime fingerprint does not match.
    /// Returns `chain.role(Refused)` if strict mode is enabled and any NC token
    /// is not Live.
    pub fn permission(&self) -> Permission {
        if self.inner.expiry.fired(self.runtime.now) {
            warn!(
                candidate_id = %self.inner.context.candidate_id,
                claim_id = %self.inner.context.claim_id,
                "judgment expired; returning ExpiryFloor"
            );
            return *self.chain.role(ChainRole::ExpiryFloor);
        }
        if !self.runtime.satisfies(&self.inner.context) {
            warn!(
                candidate_id = %self.inner.context.candidate_id,
                claim_id = %self.inner.context.claim_id,
                runtime_fingerprint = %self.runtime.context_fingerprint,
                compile_fingerprint = %self.inner.context.context_fingerprint,
                "fingerprint mismatch; returning Bottom"
            );
            return *self.chain.role(ChainRole::Bottom);
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
                "T17: negative-control not live; flooring to Refused"
            );
            return *self.chain.role(ChainRole::Refused);
        }
        debug!(
            candidate_id = %self.inner.context.candidate_id,
            claim_id = %self.inner.context.claim_id,
            permission = %self.inner.permission,
            "live permission read"
        );
        self.inner.permission
    }

    pub fn deadline(&self) -> Option<DateTime<Utc>> {
        self.inner.expiry.deadline
    }

    pub fn judgment(&self) -> &Judgment {
        &self.inner
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::audit::Derivation;
    use crate::context::{Membership, Scope};
    use crate::default_levels;
    use chrono::Duration;

    fn dummy_ctx() -> ProofContext {
        ProofContext {
            claim_id: "c".into(),
            candidate_id: "z".into(),
            context_id: "ctx".into(),
            context_fingerprint: "fp".into(),
            allowed_use: "use".into(),
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

    fn make_judgment(perm: Permission, expiry: Expiry) -> Judgment {
        Judgment {
            context: dummy_ctx(),
            permission: perm,
            expiry,
            derivation: Derivation::default(),
            chain_hash: PermissionChain::default_chain().chain_hash(),
            chain: None,
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
        let judgment = make_judgment(
            default_levels::DIA(),
            Expiry::at(now + Duration::seconds(5)),
        );
        let live = LiveJudgment::new(judgment, &rt);
        assert_eq!(live.permission(), default_levels::EXP());
    }

    #[test]
    fn live_judgment_returns_ooc_on_fingerprint_mismatch() {
        let now = Utc::now();
        let rt = RuntimeContext::new(now, "wrong-fp");
        let judgment = make_judgment(default_levels::DIA(), Expiry::never());
        let live = LiveJudgment::new(judgment, &rt);
        assert_eq!(live.permission(), default_levels::OOC());
    }

    #[test]
    fn live_judgment_returns_permission_when_valid() {
        let now = Utc::now();
        let rt = RuntimeContext::new(now, "fp");
        let judgment = make_judgment(default_levels::DIA(), Expiry::never());
        let live = LiveJudgment::new(judgment, &rt);
        assert_eq!(live.permission(), default_levels::DIA());
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
