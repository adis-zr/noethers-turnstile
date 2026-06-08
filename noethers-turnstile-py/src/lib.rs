// PyO3 bindings for turnstile-core.
// Exposes all public types as Python classes with __repr__ and __eq__.
// All errors map to Python exceptions.
#![allow(non_snake_case)]
use pyo3::exceptions::{PyException, PyValueError};
use pyo3::prelude::*;

use noethers_turnstile_core::{
    audit::{Derivation as RustDerivation, DerivationStep as RustDerivationStep},
    compile as rust_compile, compile_with_chain as rust_compile_with_chain,
    compiler::Judgment as RustJudgment,
    compose as rust_compose, compose_with_chain as rust_compose_with_chain,
    context::{Membership as RustMembership, ProofContext as RustProofContext, Scope as RustScope},
    expiry::{
        Expiry as RustExpiry, LiveJudgment as RustLiveJudgment,
        RuntimeContext as RustRuntimeContext,
    },
    gap::{
        Bound as RustBound, GapRecord as RustGapRecord, GapRequirement as RustGapRequirement,
        GapStatus as RustGapStatus, Profile as RustProfile, RequiredStatus as RustRequiredStatus,
    },
    permission::{
        ChainHash as RustChainHash, ChainRole as RustChainRole,
        InMemoryChainRegistry as RustInMemoryChainRegistry, Permission as RustPermission,
        PermissionChain as RustPermissionChain,
    },
    token::{
        compute_provenance_hash as rust_compute_provenance_hash,
        NegativeControlStatus as RustNegativeControlStatus, ProofToken as RustProofToken,
        TokenStatus as RustTokenStatus,
    },
    verify_published as rust_verify_published, ChainRegistry,
};
use std::collections::HashMap;

// ── Timestamp helpers ─────────────────────────────────────────────────────────

/// Convert a Python-supplied Unix timestamp (seconds, float) to a
/// `chrono::DateTime<Utc>`.
///
/// Rejects NaN, non-finite, and values that overflow chrono's representation.
/// This replaces the previous silent fallback to `Utc::now()`, which could
/// convert "expires at NaN" into "expires now" — the opposite of safe.
fn unix_to_datetime(unix_seconds: f64, field: &str) -> PyResult<chrono::DateTime<chrono::Utc>> {
    if !unix_seconds.is_finite() {
        return Err(PyValueError::new_err(format!(
            "{}: timestamp must be finite, got {}",
            field, unix_seconds
        )));
    }
    // Round-half-to-even style cast guards against silent saturation: an
    // out-of-i64-range float casts to i64::MAX/MIN, which chrono then accepts.
    // Bound-check explicitly.
    if unix_seconds < (i64::MIN as f64) || unix_seconds > (i64::MAX as f64) {
        return Err(PyValueError::new_err(format!(
            "{}: timestamp {} is out of i64 range",
            field, unix_seconds
        )));
    }
    chrono::DateTime::from_timestamp(unix_seconds as i64, 0).ok_or_else(|| {
        PyValueError::new_err(format!(
            "{}: timestamp {} is out of chrono's representable range",
            field, unix_seconds
        ))
    })
}

/// Compare two permissions under the default chain. Returns a Python
/// ValueError if either is foreign — never panics.
fn default_chain_cmp(a: &RustPermission, b: &RustPermission) -> PyResult<std::cmp::Ordering> {
    RustPermissionChain::default_chain()
        .cmp(a, b)
        .ok_or_else(|| {
            PyValueError::new_err(format!(
                "Permission ordering requires both operands to be in the default chain; \
                 got {:?} and {:?}",
                a.as_str(),
                b.as_str()
            ))
        })
}

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
pyo3::create_exception!(
    _noethers_turnstile,
    ChainError,
    TurnstileError,
    "Permission chain construction or use failed."
);
pyo3::create_exception!(
    _noethers_turnstile,
    AuditError,
    TurnstileError,
    "Chain audit verification failed (chain not published or hash mismatch)."
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
            inner: RustPermission::OOC(),
        }
    }
    #[classattr]
    fn EXP() -> Self {
        Self {
            inner: RustPermission::EXP(),
        }
    }
    #[classattr]
    fn REF() -> Self {
        Self {
            inner: RustPermission::REF(),
        }
    }
    #[classattr]
    fn UNS() -> Self {
        Self {
            inner: RustPermission::UNS(),
        }
    }
    #[classattr]
    fn ETA() -> Self {
        Self {
            inner: RustPermission::ETA(),
        }
    }
    #[classattr]
    fn ESC() -> Self {
        Self {
            inner: RustPermission::ESC(),
        }
    }
    #[classattr]
    fn ROL() -> Self {
        Self {
            inner: RustPermission::ROL(),
        }
    }
    #[classattr]
    fn DIA() -> Self {
        Self {
            inner: RustPermission::DIA(),
        }
    }
    #[classattr]
    fn REV() -> Self {
        Self {
            inner: RustPermission::REV(),
        }
    }
    #[classattr]
    fn AEX() -> Self {
        Self {
            inner: RustPermission::AEX(),
        }
    }
    #[classattr]
    fn ALR() -> Self {
        Self {
            inner: RustPermission::ALR(),
        }
    }
    #[classattr]
    fn AAA() -> Self {
        Self {
            inner: RustPermission::AAA(),
        }
    }

    /// Meet under the default chain. Returns a Python ValueError if either
    /// operand is not in the default chain (no panic crosses the FFI).
    fn meet(&self, other: &PyPermission) -> PyResult<PyPermission> {
        RustPermissionChain::default_chain()
            .meet(&self.inner, &other.inner)
            .map(|inner| PyPermission { inner })
            .map_err(|e| {
                PyValueError::new_err(format!(
                    "Permission.meet requires both operands to be in the default chain: {}",
                    e
                ))
            })
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

    /// Default-chain ordering. Returns a Python ValueError if either operand
    /// is not in the default chain. Use `PermissionChain.cmp(a, b)` (via the
    /// underlying Rust API) for custom chains.
    fn __lt__(&self, other: &PyPermission) -> PyResult<bool> {
        default_chain_cmp(&self.inner, &other.inner)
            .map(|o| o == std::cmp::Ordering::Less)
    }

    fn __le__(&self, other: &PyPermission) -> PyResult<bool> {
        default_chain_cmp(&self.inner, &other.inner)
            .map(|o| o != std::cmp::Ordering::Greater)
    }

    fn __gt__(&self, other: &PyPermission) -> PyResult<bool> {
        default_chain_cmp(&self.inner, &other.inner)
            .map(|o| o == std::cmp::Ordering::Greater)
    }

    fn __ge__(&self, other: &PyPermission) -> PyResult<bool> {
        default_chain_cmp(&self.inner, &other.inner)
            .map(|o| o != std::cmp::Ordering::Less)
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
                any_of: None,
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

    /// Construct a disjunctive requirement satisfied by any of the supplied arms.
    /// Each arm is itself a GapRequirement (which may itself be `any_of`).
    /// The derivation step records which arm fired by gap_id.
    #[staticmethod]
    fn any_of(arms: Vec<PyGapRequirement>) -> Self {
        let inner_arms: Vec<RustGapRequirement> = arms.into_iter().map(|a| a.inner).collect();
        Self {
            inner: RustGapRequirement::any_of(inner_arms),
        }
    }

    #[getter]
    fn is_any_of(&self) -> bool {
        self.inner.is_any_of()
    }

    fn __repr__(&self) -> String {
        if self.inner.is_any_of() {
            let n = self.inner.any_of.as_ref().map(|a| a.len()).unwrap_or(0);
            format!("GapRequirement(any_of=[{} arms])", n)
        } else {
            format!(
                "GapRequirement(gap_id={:?}, minimum_status={:?})",
                self.inner.gap_id,
                self.minimum_status()
            )
        }
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

        let issued_at_dt = unix_to_datetime(issued_at, "ProofToken issued_at")?;
        let expires_at_dt = match expires_at {
            Some(ts) => Some(unix_to_datetime(ts, "ProofToken expires_at")?),
            None => None,
        };

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

    /// Structural equality. Matches the predicate Rust composition uses to
    /// decide whether two tokens with the same token_id can coexist
    /// (`tokens_content_equal`): all substantive fields must agree.
    fn __eq__(&self, other: &PyProofToken) -> bool {
        self.inner.token_id == other.inner.token_id
            && self.inner.token_type == other.inner.token_type
            && self.inner.schema_version == other.inner.schema_version
            && self.inner.status == other.inner.status
            && self.inner.closes_gaps == other.inner.closes_gaps
            && self.inner.bounds_gaps == other.inner.bounds_gaps
            && self.inner.provenance_hash == other.inner.provenance_hash
            && self.inner.issuer == other.inner.issuer
            && self.inner.details == other.inner.details
            && self.inner.is_negative_control == other.inner.is_negative_control
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
    fn at(deadline_unix: f64) -> PyResult<Self> {
        let dt = unix_to_datetime(deadline_unix, "Expiry.at deadline")?;
        Ok(Self {
            inner: RustExpiry::at(dt),
        })
    }

    fn fired(&self, now_unix: f64) -> PyResult<bool> {
        let now = unix_to_datetime(now_unix, "Expiry.fired now")?;
        Ok(self.inner.fired(now))
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
        // F13: if no context_fingerprint is supplied, derive one from the
        // context payload. A literal copy of context_id is the wrong default
        // because it makes runtime fingerprint revalidation trivially
        // satisfiable: two contexts with the same id but different payloads
        // would pass the same check. The canonical provenance hash binds the
        // fingerprint to the (claim, candidate, context, allowed_use) tuple
        // so payload tampering is detectable at the runtime boundary.
        let fingerprint = context_fingerprint.unwrap_or_else(|| {
            rust_compute_provenance_hash(&claim_id, &candidate_id, &context_id, &allowed_use)
        });
        Self {
            inner: RustProofContext {
                claim_id,
                candidate_id,
                context_id,
                context_fingerprint: fingerprint,
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
                authority_ceiling: Some(authority_ceiling.inner),
                permission_ceiling: None,
                membership: membership.inner.clone(),
                expected_chain_hash: None,
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
            inner: self
                .inner
                .authority_ceiling
                .unwrap_or_else(RustPermission::AAA),
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

    /// Hash of the chain that authorized this judgment. Auditors resolve this
    /// against a `ChainRegistry` to recover the chain content.
    #[getter]
    fn chain_hash(&self) -> PyChainHash {
        PyChainHash {
            inner: self.inner.chain_hash,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "Judgment(permission={}, expiry={:?}, chain_hash={})",
            self.inner.permission, self.inner.expiry.deadline, self.inner.chain_hash
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
    ) -> PyResult<Self> {
        let now = unix_to_datetime(now_unix, "RuntimeContext now_unix")?;
        let nc_states = negative_control_states
            .unwrap_or_default()
            .into_iter()
            .map(|(k, v)| (k, v.inner))
            .collect();
        Ok(Self {
            inner: RustRuntimeContext::with_nc_states(
                now,
                context_fingerprint,
                nc_states,
                strict_mode,
            ),
        })
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
/// the chain it was compiled against, and evaluates expiry / fingerprint /
/// negative-control checks when `.permission(runtime_context)` is called.
///
/// The chain is required so that role lookups (ExpiryFloor / Bottom / Refused)
/// resolve in the same chain that authorized the judgment, not the default
/// chain. See LiveJudgment::with_chain in turnstile-core.
#[pyclass(name = "LiveJudgment")]
pub struct PyLiveJudgment {
    judgment: RustJudgment,
    chain: RustPermissionChain,
}

#[pymethods]
impl PyLiveJudgment {
    /// Evaluate the effective permission at the given runtime context.
    ///
    /// Raises `ExpiredError` if the judgment has expired (the live read returned
    /// this chain's `ExpiryFloor` level).
    fn permission(&self, runtime: &PyRuntimeContext) -> PyResult<PyPermission> {
        let live =
            RustLiveJudgment::with_chain(self.judgment.clone(), &runtime.inner, &self.chain);
        let p = live.permission();
        if p == *self.chain.role(RustChainRole::ExpiryFloor) {
            return Err(ExpiredError::new_err(format!(
                "judgment expired at {:?}",
                self.judgment.expiry.deadline
            )));
        }
        Ok(PyPermission { inner: p })
    }

    /// Get the permission without raising on expiry — returns the
    /// chain-specific ExpiryFloor name when expired.
    fn permission_str(&self, runtime: &PyRuntimeContext) -> String {
        let live =
            RustLiveJudgment::with_chain(self.judgment.clone(), &runtime.inner, &self.chain);
        live.permission().as_str().to_owned()
    }

    /// Hash of the chain that authorized this judgment.
    #[getter]
    fn chain_hash(&self) -> PyChainHash {
        PyChainHash {
            inner: self.judgment.chain_hash,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "LiveJudgment(permission={}, expiry={:?}, chain_hash={})",
            self.judgment.permission, self.judgment.expiry.deadline, self.judgment.chain_hash
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
///
/// If `chain` is None, uses the default chain (and the resulting judgment's
/// chain_hash is the default chain's hash — the decision is recorded even when
/// implicit). If `chain` is supplied, the compiler uses that chain explicitly.
///
/// The returned LiveJudgment carries the chain by value, so subsequent live
/// reads (expiry, fingerprint, NC-liveness) resolve role anchors against the
/// authorizing chain rather than the default chain.
#[pyfunction]
#[pyo3(signature = (ctx, chain=None))]
fn compile(
    ctx: &PyProofContext,
    chain: Option<&PyPermissionChain>,
) -> PyResult<PyLiveJudgment> {
    let chain_for_live = match chain {
        Some(c) => c.inner.clone(),
        None => RustPermissionChain::default_chain().clone(),
    };
    let result = match chain {
        Some(c) => rust_compile_with_chain(ctx.inner.clone(), &c.inner),
        None => rust_compile(ctx.inner.clone()),
    };
    result
        .map(|j| PyLiveJudgment {
            judgment: j,
            chain: chain_for_live,
        })
        .map_err(|e| TurnstileError::new_err(format!("{}", e)))
}

/// Compile a ProofContext into a Judgment (static snapshot, no live-check).
#[pyfunction]
#[pyo3(signature = (ctx, chain=None))]
fn compile_static(
    ctx: &PyProofContext,
    chain: Option<&PyPermissionChain>,
) -> PyResult<PyJudgment> {
    let result = match chain {
        Some(c) => rust_compile_with_chain(ctx.inner.clone(), &c.inner),
        None => rust_compile(ctx.inner.clone()),
    };
    result
        .map(|j| PyJudgment { inner: j })
        .map_err(|e| TurnstileError::new_err(format!("{}", e)))
}

/// Compose two ProofContexts into one.
#[pyfunction]
#[pyo3(signature = (g1, g2, chain=None))]
fn compose(
    g1: &PyProofContext,
    g2: &PyProofContext,
    chain: Option<&PyPermissionChain>,
) -> PyResult<PyProofContext> {
    let result = match chain {
        Some(c) => rust_compose_with_chain(g1.inner.clone(), g2.inner.clone(), &c.inner),
        None => rust_compose(g1.inner.clone(), g2.inner.clone()),
    };
    result
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

// ── PyChainRole ───────────────────────────────────────────────────────────────
//
// Python-side enum-like class with class attributes for each role.

#[pyclass(name = "ChainRole")]
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct PyChainRole {
    inner: RustChainRole,
}

#[pymethods]
impl PyChainRole {
    fn __eq__(&self, other: &PyChainRole) -> bool {
        self.inner == other.inner
    }

    #[classattr]
    fn Bottom() -> Self {
        Self { inner: RustChainRole::Bottom }
    }
    #[classattr]
    fn ExpiryFloor() -> Self {
        Self { inner: RustChainRole::ExpiryFloor }
    }
    #[classattr]
    fn Refused() -> Self {
        Self { inner: RustChainRole::Refused }
    }
    #[classattr]
    fn Unsatisfied() -> Self {
        Self { inner: RustChainRole::Unsatisfied }
    }
    #[classattr]
    fn DisallowedUsesCeiling() -> Self {
        Self { inner: RustChainRole::DisallowedUsesCeiling }
    }
    #[classattr]
    fn BlockerThreshold() -> Self {
        Self { inner: RustChainRole::BlockerThreshold }
    }
    #[classattr]
    fn Top() -> Self {
        Self { inner: RustChainRole::Top }
    }

    fn __repr__(&self) -> String {
        format!("ChainRole.{:?}", self.inner)
    }

    fn __hash__(&self) -> u64 {
        // ChainRole has 7 variants; the discriminant is a stable per-variant
        // integer that's cheaper and less fragile than hashing the Debug
        // format. Cast through u8 first so the hash is independent of
        // platform pointer size.
        match self.inner {
            RustChainRole::Bottom => 0u64,
            RustChainRole::ExpiryFloor => 1,
            RustChainRole::Refused => 2,
            RustChainRole::Unsatisfied => 3,
            RustChainRole::DisallowedUsesCeiling => 4,
            RustChainRole::BlockerThreshold => 5,
            RustChainRole::Top => 6,
        }
    }
}

// ── PyChainHash ───────────────────────────────────────────────────────────────

#[pyclass(name = "ChainHash")]
#[derive(Clone, PartialEq, Eq)]
pub struct PyChainHash {
    inner: RustChainHash,
}

#[pymethods]
impl PyChainHash {
    #[staticmethod]
    fn from_hex(s: &str) -> PyResult<Self> {
        RustChainHash::from_hex(s)
            .map(|inner| Self { inner })
            .ok_or_else(|| PyValueError::new_err(format!("invalid ChainHash hex: {:?}", s)))
    }

    fn to_hex(&self) -> String {
        self.inner.to_hex()
    }

    fn __str__(&self) -> String {
        self.inner.to_hex()
    }

    fn __repr__(&self) -> String {
        format!("ChainHash({})", self.inner.to_hex())
    }

    fn __eq__(&self, other: &PyChainHash) -> bool {
        self.inner == other.inner
    }

    fn __ne__(&self, other: &PyChainHash) -> bool {
        self.inner != other.inner
    }

    fn __hash__(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut h = std::collections::hash_map::DefaultHasher::new();
        self.inner.as_bytes().hash(&mut h);
        h.finish()
    }
}

// ── PyPermissionChain ─────────────────────────────────────────────────────────

#[pyclass(name = "PermissionChain")]
#[derive(Clone)]
pub struct PyPermissionChain {
    inner: RustPermissionChain,
}

#[pymethods]
impl PyPermissionChain {
    /// Construct a validated permission chain.
    ///
    /// `levels` is a list of distinct level names, ordered from Bottom to Top.
    /// `roles` is a dict mapping `ChainRole` objects to indices in `levels`.
    ///
    /// Raises ChainError if the chain fails validation (rules L1-L9 of the
    /// chain spec).
    #[staticmethod]
    fn new(levels: Vec<String>, roles: &Bound<'_, pyo3::types::PyDict>) -> PyResult<Self> {
        let rust_levels: Vec<RustPermission> =
            levels.iter().map(|s| RustPermission::new(s.as_str())).collect();
        let mut rust_roles: HashMap<RustChainRole, usize> = HashMap::new();
        for (k, v) in roles.iter() {
            let py_role: PyChainRole = k.extract()?;
            let idx: usize = v.extract()?;
            rust_roles.insert(py_role.inner, idx);
        }
        RustPermissionChain::new(rust_levels, rust_roles)
            .map(|inner| Self { inner })
            .map_err(|e| ChainError::new_err(format!("{}", e)))
    }

    /// Return the default 12-level chain (OOC..AAA).
    #[staticmethod]
    fn default_chain() -> Self {
        Self {
            inner: RustPermissionChain::default_chain().clone(),
        }
    }

    /// Look up the permission level bound to a given role.
    fn role(&self, role: &PyChainRole) -> PyPermission {
        PyPermission {
            inner: *self.inner.role(role.inner),
        }
    }

    /// Parse a level name. Returns None if the name is not in this chain.
    fn parse(&self, name: &str) -> Option<PyPermission> {
        self.inner.parse(name).map(|inner| PyPermission { inner })
    }

    /// Rank of a level within this chain. Returns None for foreign levels.
    fn rank(&self, p: &PyPermission) -> Option<u8> {
        self.inner.rank(&p.inner)
    }

    /// Meet (min under the chain's order) of two levels.
    fn meet(&self, a: &PyPermission, b: &PyPermission) -> PyResult<PyPermission> {
        self.inner
            .meet(&a.inner, &b.inner)
            .map(|inner| PyPermission { inner })
            .map_err(|e| ChainError::new_err(format!("{}", e)))
    }

    /// All levels from top to bottom.
    fn descending(&self) -> Vec<PyPermission> {
        self.inner
            .descending()
            .copied()
            .map(|inner| PyPermission { inner })
            .collect()
    }

    /// All levels from bottom to top.
    fn ascending(&self) -> Vec<PyPermission> {
        self.inner
            .ascending()
            .copied()
            .map(|inner| PyPermission { inner })
            .collect()
    }

    /// Whether this chain contains a level with the given name.
    fn contains(&self, p: &PyPermission) -> bool {
        self.inner.contains(&p.inner)
    }

    fn __len__(&self) -> usize {
        self.inner.len()
    }

    fn __eq__(&self, other: &PyPermissionChain) -> bool {
        self.inner == other.inner
    }

    /// Content hash over (ordered names, role bindings).
    fn chain_hash(&self) -> PyChainHash {
        PyChainHash {
            inner: self.inner.chain_hash(),
        }
    }

    fn __repr__(&self) -> String {
        let names: Vec<&str> = self.inner.levels().iter().map(|l| l.as_str()).collect();
        format!("PermissionChain({:?}, hash={})", names, self.inner.chain_hash())
    }
}

// ── PyInMemoryChainRegistry ───────────────────────────────────────────────────

#[pyclass(name = "InMemoryChainRegistry")]
pub struct PyInMemoryChainRegistry {
    inner: RustInMemoryChainRegistry,
}

#[pymethods]
impl PyInMemoryChainRegistry {
    #[new]
    fn new() -> Self {
        Self {
            inner: RustInMemoryChainRegistry::new(),
        }
    }

    fn publish(&mut self, chain: &PyPermissionChain) -> PyChainHash {
        PyChainHash {
            inner: self.inner.publish(chain.inner.clone()),
        }
    }

    fn lookup(&self, hash: &PyChainHash) -> Option<PyPermissionChain> {
        self.inner
            .lookup(&hash.inner)
            .cloned()
            .map(|inner| PyPermissionChain { inner })
    }

    fn __len__(&self) -> usize {
        self.inner.len()
    }
}

// ── verify_published ──────────────────────────────────────────────────────────

#[pyfunction]
fn verify_published(
    judgment: &PyJudgment,
    registry: &PyInMemoryChainRegistry,
) -> PyResult<()> {
    rust_verify_published(&judgment.inner, &registry.inner)
        .map_err(|e| AuditError::new_err(format!("{}", e)))
}

// ── Module definition ─────────────────────────────────────────────────────────

#[pymodule]
fn _noethers_turnstile(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Exceptions.
    m.add("TurnstileError", py.get_type_bound::<TurnstileError>())?;
    m.add("ExpiredError", py.get_type_bound::<ExpiredError>())?;
    m.add("CompositionError", py.get_type_bound::<CompositionError>())?;
    m.add("ProvenanceError", py.get_type_bound::<ProvenanceError>())?;
    m.add("ChainError", py.get_type_bound::<ChainError>())?;
    m.add("AuditError", py.get_type_bound::<AuditError>())?;

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
    m.add_class::<PyChainRole>()?;
    m.add_class::<PyChainHash>()?;
    m.add_class::<PyPermissionChain>()?;
    m.add_class::<PyInMemoryChainRegistry>()?;

    // Functions.
    m.add_function(wrap_pyfunction!(compile, m)?)?;
    m.add_function(wrap_pyfunction!(compile_static, m)?)?;
    m.add_function(wrap_pyfunction!(compose, m)?)?;
    m.add_function(wrap_pyfunction!(compute_provenance_hash, m)?)?;
    m.add_function(wrap_pyfunction!(init_tracing, m)?)?;
    m.add_function(wrap_pyfunction!(verify_published, m)?)?;

    Ok(())
}
