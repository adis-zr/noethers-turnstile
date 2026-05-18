// PyO3 bindings for turnstile-core.
// Exposes all public types as Python classes with __repr__ and __eq__.
// All errors map to Python exceptions.
#![allow(non_snake_case)]
use pyo3::exceptions::{PyException, PyValueError};
use pyo3::prelude::*;

use noethers_turnstile_core::{
    audit::{Derivation as RustDerivation, DerivationStep as RustDerivationStep},
    compile as rust_compile,
    compiler::Judgment as RustJudgment,
    compose as rust_compose,
    context::{Membership as RustMembership, ProofContext as RustProofContext, Scope as RustScope},
    expiry::{
        Expiry as RustExpiry, LiveJudgment as RustLiveJudgment,
        RuntimeContext as RustRuntimeContext,
    },
    gap::{
        Bound as RustBound, GapRecord as RustGapRecord, GapRequirement as RustGapRequirement,
        GapStatus as RustGapStatus, Profile as RustProfile, RequiredStatus as RustRequiredStatus,
    },
    permission::Permission as RustPermission,
    token::{
        compute_provenance_hash as rust_compute_provenance_hash,
        NegativeControlStatus as RustNegativeControlStatus, ProofToken as RustProofToken,
        TokenStatus as RustTokenStatus,
    },
};

// ── Python exceptions ─────────────────────────────────────────────────────────

pyo3::create_exception!(
    _noethers_turnstile,
    TurnstileError,
    PyException,
    "Base Turnstile error."
);
pyo3::create_exception!(
    _noethers_turnstile,
    ExpiredError,
    TurnstileError,
    "Judgment has expired."
);
pyo3::create_exception!(
    _noethers_turnstile,
    CompositionError,
    TurnstileError,
    "Composition failed."
);
pyo3::create_exception!(
    _noethers_turnstile,
    ProvenanceError,
    TurnstileError,
    "Provenance mismatch."
);

// ── PyNegativeControlStatus ───────────────────────────────────────────────────

#[pyclass(name = "NegativeControlStatus")]
#[derive(Clone)]
pub struct PyNegativeControlStatus {
    inner: RustNegativeControlStatus,
}

#[pymethods]
impl PyNegativeControlStatus {
    #[classattr]
    fn Live() -> Self {
        Self {
            inner: RustNegativeControlStatus::Live,
        }
    }
    #[classattr]
    fn Stale() -> Self {
        Self {
            inner: RustNegativeControlStatus::Stale,
        }
    }
    #[classattr]
    fn Failed() -> Self {
        Self {
            inner: RustNegativeControlStatus::Failed,
        }
    }
    #[classattr]
    fn Missing() -> Self {
        Self {
            inner: RustNegativeControlStatus::Missing,
        }
    }

    fn __repr__(&self) -> &str {
        match self.inner {
            RustNegativeControlStatus::Live => "NegativeControlStatus.Live",
            RustNegativeControlStatus::Stale => "NegativeControlStatus.Stale",
            RustNegativeControlStatus::Failed => "NegativeControlStatus.Failed",
            RustNegativeControlStatus::Missing => "NegativeControlStatus.Missing",
        }
    }

    fn __str__(&self) -> &str {
        match self.inner {
            RustNegativeControlStatus::Live => "Live",
            RustNegativeControlStatus::Stale => "Stale",
            RustNegativeControlStatus::Failed => "Failed",
            RustNegativeControlStatus::Missing => "Missing",
        }
    }

    fn __eq__(&self, other: &PyNegativeControlStatus) -> bool {
        self.inner == other.inner
    }
}

// ── PyDerivationStep ──────────────────────────────────────────────────────────

#[pyclass(name = "DerivationStep")]
#[derive(Clone)]
pub struct PyDerivationStep {
    inner: RustDerivationStep,
}

#[pymethods]
impl PyDerivationStep {
    #[getter]
    fn phase(&self) -> &str {
        &self.inner.phase
    }
    #[getter]
    fn permission_after(&self) -> PyPermission {
        PyPermission {
            inner: self.inner.permission_after,
        }
    }
    #[getter]
    fn note(&self) -> &str {
        &self.inner.note
    }
    #[getter]
    fn token_ids(&self) -> Vec<String> {
        self.inner.token_ids.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "DerivationStep(phase={:?}, permission_after={}, note={:?})",
            self.inner.phase, self.inner.permission_after, self.inner.note,
        )
    }
}

// ── PyDerivation ──────────────────────────────────────────────────────────────

#[pyclass(name = "Derivation")]
#[derive(Clone)]
pub struct PyDerivation {
    inner: RustDerivation,
}

#[pymethods]
impl PyDerivation {
    #[getter]
    fn steps(&self) -> Vec<PyDerivationStep> {
        self.inner
            .steps
            .iter()
            .map(|s| PyDerivationStep { inner: s.clone() })
            .collect()
    }
    #[getter]
    fn provenance_hash(&self) -> &str {
        &self.inner.provenance_hash
    }
    #[getter]
    fn compiled_at(&self) -> Option<f64> {
        self.inner.compiled_at.map(|dt| dt.timestamp() as f64)
    }

    fn __repr__(&self) -> String {
        format!(
            "Derivation(steps={}, provenance_hash={:?})",
            self.inner.steps.len(),
            self.inner.provenance_hash
        )
    }
}

// ── PyPermission ──────────────────────────────────────────────────────────────

#[pyclass(name = "Permission")]
#[derive(Clone)]
pub struct PyPermission {
    inner: RustPermission,
}

#[pymethods]
impl PyPermission {
    #[classattr]
    fn OOC() -> Self {
        Self {
            inner: RustPermission::OOC,
        }
    }
    #[classattr]
    fn EXP() -> Self {
        Self {
            inner: RustPermission::EXP,
        }
    }
    #[classattr]
    fn REF() -> Self {
        Self {
            inner: RustPermission::REF,
        }
    }
    #[classattr]
    fn UNS() -> Self {
        Self {
            inner: RustPermission::UNS,
        }
    }
    #[classattr]
    fn ETA() -> Self {
        Self {
            inner: RustPermission::ETA,
        }
    }
    #[classattr]
    fn ESC() -> Self {
        Self {
            inner: RustPermission::ESC,
        }
    }
    #[classattr]
    fn ROL() -> Self {
        Self {
            inner: RustPermission::ROL,
        }
    }
    #[classattr]
    fn DIA() -> Self {
        Self {
            inner: RustPermission::DIA,
        }
    }
    #[classattr]
    fn REV() -> Self {
        Self {
            inner: RustPermission::REV,
        }
    }
    #[classattr]
    fn AEX() -> Self {
        Self {
            inner: RustPermission::AEX,
        }
    }
    #[classattr]
    fn ALR() -> Self {
        Self {
            inner: RustPermission::ALR,
        }
    }
    #[classattr]
    fn AAA() -> Self {
        Self {
            inner: RustPermission::AAA,
        }
    }

    fn meet(&self, other: &PyPermission) -> PyPermission {
        PyPermission {
            inner: self.inner.meet(other.inner),
        }
    }

    fn __repr__(&self) -> String {
        format!("Permission.{}", self.inner.as_str())
    }

    fn __str__(&self) -> String {
        self.inner.as_str().to_owned()
    }

    fn __eq__(&self, other: &PyPermission) -> bool {
        self.inner == other.inner
    }

    fn __lt__(&self, other: &PyPermission) -> bool {
        self.inner < other.inner
    }

    fn __le__(&self, other: &PyPermission) -> bool {
        self.inner <= other.inner
    }

    fn __gt__(&self, other: &PyPermission) -> bool {
        self.inner > other.inner
    }

    fn __ge__(&self, other: &PyPermission) -> bool {
        self.inner >= other.inner
    }

    fn __hash__(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut h = std::collections::hash_map::DefaultHasher::new();
        self.inner.hash(&mut h);
        h.finish()
    }

    #[staticmethod]
    fn from_str(s: &str) -> PyResult<PyPermission> {
        RustPermission::from_str(s)
            .map(|inner| PyPermission { inner })
            .ok_or_else(|| PyValueError::new_err(format!("Unknown permission: {:?}", s)))
    }

    fn as_str(&self) -> &str {
        self.inner.as_str()
    }
}

// ── PyScope ───────────────────────────────────────────────────────────────────

#[pyclass(name = "Scope")]
#[derive(Clone)]
pub struct PyScope {
    inner: RustScope,
}

#[pymethods]
impl PyScope {
    #[new]
    #[pyo3(signature = (allowed_candidates=None, allowed_paths=None, allowed_tools=None, allowed_resources=None))]
    fn new(
        allowed_candidates: Option<Vec<String>>,
        allowed_paths: Option<Vec<String>>,
        allowed_tools: Option<Vec<String>>,
        allowed_resources: Option<Vec<String>>,
    ) -> Self {
        Self {
            inner: RustScope {
                allowed_candidates: allowed_candidates.unwrap_or_default(),
                allowed_paths: allowed_paths.unwrap_or_default(),
                allowed_tools: allowed_tools.unwrap_or_default(),
                allowed_resources: allowed_resources.unwrap_or_default(),
            },
        }
    }

    #[getter]
    fn allowed_candidates(&self) -> Vec<String> {
        self.inner.allowed_candidates.clone()
    }
    #[getter]
    fn allowed_paths(&self) -> Vec<String> {
        self.inner.allowed_paths.clone()
    }
    #[getter]
    fn allowed_tools(&self) -> Vec<String> {
        self.inner.allowed_tools.clone()
    }
    #[getter]
    fn allowed_resources(&self) -> Vec<String> {
        self.inner.allowed_resources.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "Scope(candidates={:?}, paths={:?}, tools={:?}, resources={:?})",
            self.inner.allowed_candidates,
            self.inner.allowed_paths,
            self.inner.allowed_tools,
            self.inner.allowed_resources,
        )
    }

    fn __eq__(&self, other: &PyScope) -> bool {
        self.inner.allowed_candidates == other.inner.allowed_candidates
            && self.inner.allowed_paths == other.inner.allowed_paths
            && self.inner.allowed_tools == other.inner.allowed_tools
            && self.inner.allowed_resources == other.inner.allowed_resources
    }
}

// ── PyGapRecord ───────────────────────────────────────────────────────────────

#[pyclass(name = "GapRecord")]
#[derive(Clone)]
pub struct PyGapRecord {
    inner: RustGapRecord,
}

#[pymethods]
impl PyGapRecord {
    #[new]
    #[pyo3(signature = (gap_id, gap_type, status="open", bound_value=None))]
    fn new(
        gap_id: String,
        gap_type: String,
        status: &str,
        bound_value: Option<f64>,
    ) -> PyResult<Self> {
        let gap_status = match status {
            "open" => RustGapStatus::Open,
            "bounded" => {
                let v = bound_value.unwrap_or(0.0);
                RustGapStatus::Bounded(RustBound::numeric(v))
            }
            "closed" => RustGapStatus::Closed,
            other => {
                return Err(PyValueError::new_err(format!(
                    "Unknown gap status: {:?}",
                    other
                )))
            }
        };
        Ok(Self {
            inner: RustGapRecord {
                gap_id,
                gap_type,
                status: gap_status,
            },
        })
    }

    #[getter]
    fn gap_id(&self) -> &str {
        &self.inner.gap_id
    }
    #[getter]
    fn gap_type(&self) -> &str {
        &self.inner.gap_type
    }
    #[getter]
    fn status(&self) -> String {
        match &self.inner.status {
            RustGapStatus::Open => "open".into(),
            RustGapStatus::Bounded(_) => "bounded".into(),
            RustGapStatus::Closed => "closed".into(),
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "GapRecord(gap_id={:?}, gap_type={:?}, status={:?})",
            self.inner.gap_id,
            self.inner.gap_type,
            self.status()
        )
    }

    fn __eq__(&self, other: &PyGapRecord) -> bool {
        self.inner.gap_id == other.inner.gap_id
            && self.inner.gap_type == other.inner.gap_type
            && self.inner.status == other.inner.status
    }
}

// ── PyGapRequirement ──────────────────────────────────────────────────────────

#[pyclass(name = "GapRequirement")]
#[derive(Clone)]
pub struct PyGapRequirement {
    inner: RustGapRequirement,
}

#[pymethods]
impl PyGapRequirement {
    #[new]
    #[pyo3(signature = (gap_id, minimum_status))]
    fn new(gap_id: String, minimum_status: &str) -> PyResult<Self> {
        let req = match minimum_status {
            "bounded" => RustRequiredStatus::BoundedRequired,
            "closed" => RustRequiredStatus::ClosedRequired,
            other => {
                return Err(PyValueError::new_err(format!(
                    "Unknown required_status: {:?}",
                    other
                )))
            }
        };
        Ok(Self {
            inner: RustGapRequirement {
                gap_id,
                minimum_status: req,
            },
        })
    }

    #[getter]
    fn gap_id(&self) -> &str {
        &self.inner.gap_id
    }
    #[getter]
    fn minimum_status(&self) -> &str {
        match self.inner.minimum_status {
            RustRequiredStatus::OpenAllowed => "open",
            RustRequiredStatus::BoundedRequired => "bounded",
            RustRequiredStatus::ClosedRequired => "closed",
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "GapRequirement(gap_id={:?}, minimum_status={:?})",
            self.inner.gap_id,
            self.minimum_status()
        )
    }
}

// ── PyProfile ─────────────────────────────────────────────────────────────────

#[pyclass(name = "Profile")]
#[derive(Clone)]
pub struct PyProfile {
    inner: RustProfile,
}

#[pymethods]
impl PyProfile {
    #[new]
    fn new(permission: &PyPermission, required_gaps: Vec<PyGapRequirement>) -> Self {
        Self {
            inner: RustProfile {
                permission: permission.inner,
                required_gaps: required_gaps.into_iter().map(|r| r.inner).collect(),
            },
        }
    }

    #[getter]
    fn permission(&self) -> PyPermission {
        PyPermission {
            inner: self.inner.permission,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "Profile(permission={}, gaps={})",
            self.inner.permission,
            self.inner.required_gaps.len()
        )
    }
}

// ── PyProofToken ──────────────────────────────────────────────────────────────

#[pyclass(name = "ProofToken")]
#[derive(Clone)]
pub struct PyProofToken {
    inner: RustProofToken,
}

#[pymethods]
impl PyProofToken {
    #[new]
    #[pyo3(signature = (
        token_id, token_type, schema_version, status,
        closes_gaps, bounds_gaps, provenance_hash,
        issued_at, issuer,
        expires_at=None,
        details=None,
        is_negative_control=false,
    ))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        token_id: String,
        token_type: String,
        schema_version: String,
        status: &str,
        closes_gaps: Vec<String>,
        bounds_gaps: Vec<String>,
        provenance_hash: String,
        issued_at: f64, // Unix timestamp (seconds)
        issuer: String,
        expires_at: Option<f64>,
        details: Option<&str>,
        is_negative_control: bool,
    ) -> PyResult<Self> {
        let token_status = match status {
            "valid" => RustTokenStatus::Valid,
            "invalid" => RustTokenStatus::Invalid,
            "expired" => RustTokenStatus::Expired,
            "revoked" => RustTokenStatus::Revoked,
            "malformed" => RustTokenStatus::Malformed,
            other => {
                return Err(PyValueError::new_err(format!(
                    "Unknown token status: {:?}",
                    other
                )))
            }
        };

        let issued_at_dt =
            chrono::DateTime::from_timestamp(issued_at as i64, 0).unwrap_or_else(chrono::Utc::now);
        let expires_at_dt =
            expires_at.and_then(|ts| chrono::DateTime::from_timestamp(ts as i64, 0));

        let details_value = match details {
            Some(s) => serde_json::from_str(s)
                .map_err(|e| PyValueError::new_err(format!("Invalid JSON for details: {}", e)))?,
            None => serde_json::Value::Null,
        };

        Ok(Self {
            inner: RustProofToken {
                token_id,
                token_type,
                schema_version,
                status: token_status,
                closes_gaps,
                bounds_gaps,
                provenance_hash,
                issued_at: issued_at_dt,
                expires_at: expires_at_dt,
                issuer,
                details: details_value,
                is_negative_control,
            },
        })
    }

    #[getter]
    fn token_id(&self) -> &str {
        &self.inner.token_id
    }
    #[getter]
    fn token_type(&self) -> &str {
        &self.inner.token_type
    }
    #[getter]
    fn schema_version(&self) -> &str {
        &self.inner.schema_version
    }
    #[getter]
    fn status(&self) -> String {
        format!("{:?}", self.inner.status).to_lowercase()
    }
    #[getter]
    fn closes_gaps(&self) -> Vec<String> {
        self.inner.closes_gaps.clone()
    }
    #[getter]
    fn bounds_gaps(&self) -> Vec<String> {
        self.inner.bounds_gaps.clone()
    }
    #[getter]
    fn provenance_hash(&self) -> &str {
        &self.inner.provenance_hash
    }
    #[getter]
    fn issuer(&self) -> &str {
        &self.inner.issuer
    }

    /// The details payload as a JSON string, or None if not set.
    #[getter]
    fn details(&self) -> Option<String> {
        if self.inner.details.is_null() {
            None
        } else {
            Some(self.inner.details.to_string())
        }
    }

    #[getter]
    fn is_negative_control(&self) -> bool {
        self.inner.is_negative_control
    }

    fn __repr__(&self) -> String {
        format!(
            "ProofToken(id={:?}, type={:?}, status={:?}, nc={})",
            self.inner.token_id,
            self.inner.token_type,
            self.status(),
            self.inner.is_negative_control,
        )
    }

    fn __eq__(&self, other: &PyProofToken) -> bool {
        self.inner.token_id == other.inner.token_id
            && self.inner.provenance_hash == other.inner.provenance_hash
    }
}

// ── PyExpiry ──────────────────────────────────────────────────────────────────

#[pyclass(name = "Expiry")]
#[derive(Clone)]
pub struct PyExpiry {
    inner: RustExpiry,
}

#[pymethods]
impl PyExpiry {
    #[staticmethod]
    fn never() -> Self {
        Self {
            inner: RustExpiry::never(),
        }
    }

    #[staticmethod]
    fn at(deadline_unix: f64) -> Self {
        let dt = chrono::DateTime::from_timestamp(deadline_unix as i64, 0)
            .unwrap_or_else(chrono::Utc::now);
        Self {
            inner: RustExpiry::at(dt),
        }
    }

    fn fired(&self, now_unix: f64) -> bool {
        let now =
            chrono::DateTime::from_timestamp(now_unix as i64, 0).unwrap_or_else(chrono::Utc::now);
        self.inner.fired(now)
    }

    fn __repr__(&self) -> String {
        match self.inner.deadline {
            Some(d) => format!("Expiry(deadline={})", d.to_rfc3339()),
            None => "Expiry(never)".into(),
        }
    }
}

// ── PyMembership ──────────────────────────────────────────────────────────────

#[pyclass(name = "Membership")]
#[derive(Clone)]
pub struct PyMembership {
    inner: RustMembership,
}

#[pymethods]
impl PyMembership {
    #[classattr]
    fn InClass() -> Self {
        Self {
            inner: RustMembership::InClass,
        }
    }
    #[classattr]
    fn OutOfClassExact() -> Self {
        Self {
            inner: RustMembership::OutOfClassExact,
        }
    }
    #[classattr]
    fn OutOfClassAuthorizedDeterministicWrite() -> Self {
        Self {
            inner: RustMembership::OutOfClassAuthorizedDeterministicWrite,
        }
    }
    #[classattr]
    fn OutOfClassNoConsequentialUse() -> Self {
        Self {
            inner: RustMembership::OutOfClassNoConsequentialUse,
        }
    }

    #[staticmethod]
    fn other(reason: String) -> Self {
        Self {
            inner: RustMembership::OutOfClassOther(reason),
        }
    }

    fn is_in_class(&self) -> bool {
        self.inner.is_in_class()
    }

    fn __repr__(&self) -> String {
        format!("Membership({:?})", self.inner)
    }

    fn __eq__(&self, other: &PyMembership) -> bool {
        self.inner == other.inner
    }
}

// ── PyProofContext ────────────────────────────────────────────────────────────

#[pyclass(name = "ProofContext")]
#[derive(Clone)]
pub struct PyProofContext {
    inner: RustProofContext,
}

#[pymethods]
impl PyProofContext {
    #[new]
    #[pyo3(signature = (
        claim_id, candidate_id, context_id, allowed_use,
        membership,
        authority_ceiling,
        expiry,
        gaps=None,
        profiles=None,
        tokens=None,
        disallowed_uses=None,
        scope=None,
        context_fingerprint=None,
    ))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        claim_id: String,
        candidate_id: String,
        context_id: String,
        allowed_use: String,
        membership: &PyMembership,
        authority_ceiling: &PyPermission,
        expiry: &PyExpiry,
        gaps: Option<Vec<PyGapRecord>>,
        profiles: Option<Vec<PyProfile>>,
        tokens: Option<Vec<PyProofToken>>,
        disallowed_uses: Option<Vec<String>>,
        scope: Option<&PyScope>,
        context_fingerprint: Option<String>,
    ) -> Self {
        Self {
            inner: RustProofContext {
                claim_id,
                candidate_id,
                context_id: context_id.clone(),
                context_fingerprint: context_fingerprint.unwrap_or(context_id),
                allowed_use,
                disallowed_uses: disallowed_uses.unwrap_or_default(),
                scope: scope.map(|s| s.inner.clone()).unwrap_or_default(),
                gaps: gaps
                    .unwrap_or_default()
                    .into_iter()
                    .map(|g| g.inner)
                    .collect(),
                profiles: profiles
                    .unwrap_or_default()
                    .into_iter()
                    .map(|p| p.inner)
                    .collect(),
                tokens: tokens
                    .unwrap_or_default()
                    .into_iter()
                    .map(|t| t.inner)
                    .collect(),
                expiry: expiry.inner.clone(),
                authority_ceiling: authority_ceiling.inner,
                permission_ceiling: noethers_turnstile_core::permission::Permission::AAA,
                membership: membership.inner.clone(),
            },
        }
    }

    #[getter]
    fn claim_id(&self) -> &str {
        &self.inner.claim_id
    }
    #[getter]
    fn candidate_id(&self) -> &str {
        &self.inner.candidate_id
    }
    #[getter]
    fn context_id(&self) -> &str {
        &self.inner.context_id
    }
    #[getter]
    fn allowed_use(&self) -> &str {
        &self.inner.allowed_use
    }
    #[getter]
    fn authority_ceiling(&self) -> PyPermission {
        PyPermission {
            inner: self.inner.authority_ceiling,
        }
    }

    fn provenance_hash(&self) -> String {
        self.inner.provenance_hash()
    }

    fn __repr__(&self) -> String {
        format!(
            "ProofContext(claim_id={:?}, candidate_id={:?}, allowed_use={:?})",
            self.inner.claim_id, self.inner.candidate_id, self.inner.allowed_use
        )
    }
}

// ── PyJudgment ────────────────────────────────────────────────────────────────

#[pyclass(name = "Judgment")]
#[derive(Clone)]
pub struct PyJudgment {
    inner: RustJudgment,
}

#[pymethods]
impl PyJudgment {
    #[getter]
    fn permission(&self) -> PyPermission {
        PyPermission {
            inner: self.inner.permission,
        }
    }
    #[getter]
    fn permission_str(&self) -> String {
        self.inner.permission.as_str().to_owned()
    }
    #[getter]
    fn expiry(&self) -> PyExpiry {
        PyExpiry {
            inner: self.inner.expiry.clone(),
        }
    }

    #[getter]
    fn derivation(&self) -> PyDerivation {
        PyDerivation {
            inner: self.inner.derivation.clone(),
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "Judgment(permission={}, expiry={:?})",
            self.inner.permission, self.inner.expiry.deadline
        )
    }

    fn __eq__(&self, other: &PyJudgment) -> bool {
        self.inner.permission == other.inner.permission
    }
}

// ── PyRuntimeContext ──────────────────────────────────────────────────────────

#[pyclass(name = "RuntimeContext")]
#[derive(Clone)]
pub struct PyRuntimeContext {
    inner: RustRuntimeContext,
}

#[pymethods]
impl PyRuntimeContext {
    /// Create a RuntimeContext.
    ///
    /// `negative_control_states` is an optional dict mapping token_id (str) to a
    /// `NegativeControlStatus` value.  `strict_mode` defaults to `True`.
    #[new]
    #[pyo3(signature = (now_unix, context_fingerprint, negative_control_states=None, strict_mode=true))]
    fn new(
        now_unix: f64,
        context_fingerprint: String,
        negative_control_states: Option<std::collections::HashMap<String, PyNegativeControlStatus>>,
        strict_mode: bool,
    ) -> Self {
        let now =
            chrono::DateTime::from_timestamp(now_unix as i64, 0).unwrap_or_else(chrono::Utc::now);
        let nc_states = negative_control_states
            .unwrap_or_default()
            .into_iter()
            .map(|(k, v)| (k, v.inner))
            .collect();
        Self {
            inner: RustRuntimeContext::with_nc_states(
                now,
                context_fingerprint,
                nc_states,
                strict_mode,
            ),
        }
    }

    #[getter]
    fn strict_mode(&self) -> bool {
        self.inner.strict_mode
    }

    fn __repr__(&self) -> String {
        format!(
            "RuntimeContext(now={}, fp={:?}, strict_mode={})",
            self.inner.now.to_rfc3339(),
            self.inner.context_fingerprint,
            self.inner.strict_mode,
        )
    }
}

// ── PyLiveJudgment ────────────────────────────────────────────────────────────

/// A live judgment handle.  The Python binding holds the judgment by value and
/// evaluates expiry when `.permission(runtime_context)` is called.
#[pyclass(name = "LiveJudgment")]
pub struct PyLiveJudgment {
    judgment: RustJudgment,
}

#[pymethods]
impl PyLiveJudgment {
    /// Evaluate the effective permission at the given runtime context.
    ///
    /// Raises `ExpiredError` if the judgment has expired.
    fn permission(&self, runtime: &PyRuntimeContext) -> PyResult<PyPermission> {
        let live = RustLiveJudgment::new(self.judgment.clone(), &runtime.inner);
        let p = live.permission();
        if p == RustPermission::EXP {
            return Err(ExpiredError::new_err(format!(
                "judgment expired at {:?}",
                self.judgment.expiry.deadline
            )));
        }
        Ok(PyPermission { inner: p })
    }

    /// Get the permission without raising on EXP — returns the string "EXP" if expired.
    fn permission_str(&self, runtime: &PyRuntimeContext) -> String {
        let live = RustLiveJudgment::new(self.judgment.clone(), &runtime.inner);
        live.permission().as_str().to_owned()
    }

    fn __repr__(&self) -> String {
        format!(
            "LiveJudgment(permission={}, expiry={:?})",
            self.judgment.permission, self.judgment.expiry.deadline
        )
    }
}

// ── Tracing ───────────────────────────────────────────────────────────────────

/// Route Rust tracing events into Python's `logging` hierarchy.
///
/// After calling this, `debug!` / `info!` / `warn!` / `error!` events emitted
/// by turnstile-core appear as records on the `turnstile` Python logger at the
/// corresponding level.  Safe to call multiple times; subsequent calls are
/// no-ops.
#[pyfunction]
fn init_tracing() -> PyResult<()> {
    // ResetHandle::reset() is a no-op if the subscriber is already set.
    let _ = pyo3_log::try_init();
    Ok(())
}

// ── Module-level functions ────────────────────────────────────────────────────

/// Compile a ProofContext into a LiveJudgment.
#[pyfunction]
fn compile(ctx: &PyProofContext) -> PyResult<PyLiveJudgment> {
    rust_compile(ctx.inner.clone())
        .map(|j| PyLiveJudgment { judgment: j })
        .map_err(|e| TurnstileError::new_err(format!("{}", e)))
}

/// Compile a ProofContext into a Judgment (static snapshot, no live-check).
#[pyfunction]
fn compile_static(ctx: &PyProofContext) -> PyResult<PyJudgment> {
    rust_compile(ctx.inner.clone())
        .map(|j| PyJudgment { inner: j })
        .map_err(|e| TurnstileError::new_err(format!("{}", e)))
}

/// Compose two ProofContexts into one.
#[pyfunction]
fn compose(g1: &PyProofContext, g2: &PyProofContext) -> PyResult<PyProofContext> {
    rust_compose(g1.inner.clone(), g2.inner.clone())
        .map(|ctx| PyProofContext { inner: ctx })
        .map_err(|e| CompositionError::new_err(format!("{}", e)))
}

/// Compute the provenance hash for a context tuple.
#[pyfunction]
fn compute_provenance_hash(
    claim_id: &str,
    candidate_id: &str,
    context_id: &str,
    allowed_use: &str,
) -> String {
    rust_compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use)
}

// ── Module definition ─────────────────────────────────────────────────────────

#[pymodule]
fn _noethers_turnstile(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Exceptions.
    m.add("TurnstileError", py.get_type_bound::<TurnstileError>())?;
    m.add("ExpiredError", py.get_type_bound::<ExpiredError>())?;
    m.add("CompositionError", py.get_type_bound::<CompositionError>())?;
    m.add("ProvenanceError", py.get_type_bound::<ProvenanceError>())?;

    // Types.
    m.add_class::<PyNegativeControlStatus>()?;
    m.add_class::<PyDerivationStep>()?;
    m.add_class::<PyDerivation>()?;
    m.add_class::<PyPermission>()?;
    m.add_class::<PyScope>()?;
    m.add_class::<PyGapRecord>()?;
    m.add_class::<PyGapRequirement>()?;
    m.add_class::<PyProfile>()?;
    m.add_class::<PyProofToken>()?;
    m.add_class::<PyExpiry>()?;
    m.add_class::<PyMembership>()?;
    m.add_class::<PyProofContext>()?;
    m.add_class::<PyJudgment>()?;
    m.add_class::<PyRuntimeContext>()?;
    m.add_class::<PyLiveJudgment>()?;

    // Functions.
    m.add_function(wrap_pyfunction!(compile, m)?)?;
    m.add_function(wrap_pyfunction!(compile_static, m)?)?;
    m.add_function(wrap_pyfunction!(compose, m)?)?;
    m.add_function(wrap_pyfunction!(compute_provenance_hash, m)?)?;
    m.add_function(wrap_pyfunction!(init_tracing, m)?)?;

    Ok(())
}
