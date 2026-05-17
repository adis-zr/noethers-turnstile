# Turnstile

[![CI](https://github.com/adisriram/turnstile/actions/workflows/ci.yml/badge.svg)](https://github.com/adisriram/turnstile/actions/workflows/ci.yml)
[![Crates.io](https://img.shields.io/crates/v/turnstile-core)](https://crates.io/crates/turnstile-core)
[![PyPI](https://img.shields.io/pypi/v/turnstile)](https://pypi.org/project/turnstile/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

Turnstile is an **admissibility compiler** for approximate consequential systems. Given a proof context Γ — a set of gap records, profiles, proof tokens, and authority constraints — it produces the strongest permission `p` the evidence supports and a binding expiry `ε`. The answer is a judgment in a typed form that the Rust borrow checker prevents from being read after it expires.

This library is for teams building systems where autonomous or consequential actions should be gated on structured evidence: calibration certificates, negative-control results, role assertions, scope restrictions. Turnstile handles the algebra; your domain supplies the certifiers.

**Judgment form:** `Γ ⊢ z : p until ε`

---

## Permission Chain

Total order. `OOC` is the bottom (weakest). `AAA` is the top (strongest). Meet = min.

```
OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA < REV < AEX < ALR < AAA
```

---

## Quick Start — Rust

```rust
use turnstile_core::{
    compile,
    context::{Membership, ProofContext, Scope},
    expiry::{Expiry, LiveJudgment, RuntimeContext},
    gap::{GapRecord, GapRequirement, Profile, RequiredStatus},
    permission::Permission,
    token::{compute_provenance_hash, ProofToken, TokenStatus},
};
use chrono::Utc;

// 1. Build a context with one gap that needs closing.
let claim_id = "my-claim";
let candidate_id = "z-001";
let context_id = "ctx-001";
let allowed_use = "diagnostics";

let hash = compute_provenance_hash(claim_id, candidate_id, context_id, allowed_use);

let ctx = ProofContext {
    claim_id: claim_id.into(),
    candidate_id: candidate_id.into(),
    context_id: context_id.into(),
    context_fingerprint: "fp-001".into(),
    allowed_use: allowed_use.into(),
    disallowed_uses: vec![],
    scope: Scope::default(),
    gaps: vec![GapRecord::closed("calibration-gap", "calibration_gap")],
    profiles: vec![Profile {
        permission: Permission::DIA,
        required_gaps: vec![GapRequirement {
            gap_id: "calibration-gap".into(),
            minimum_status: RequiredStatus::ClosedRequired,
        }],
    }],
    tokens: vec![ProofToken {
        token_id: "tok-1".into(),
        token_type: "CALIBRATION_CERT".into(),
        schema_version: "0.1".into(),
        status: TokenStatus::Valid,
        closes_gaps: vec!["calibration-gap".into()],
        bounds_gaps: vec![],
        provenance_hash: hash,
        issued_at: Utc::now(),
        expires_at: None,
        issuer: "domain-certifier".into(),
        details: serde_json::Value::Null,
        is_negative_control: false,
    }],
    expiry: Expiry::never(),
    authority_ceiling: Permission::AAA,
    membership: Membership::InClass,
};

// 2. Compile.
let judgment = compile(ctx).unwrap();
assert_eq!(judgment.permission, Permission::DIA);

// 3. Read through LiveJudgment (expiry check enforced by Rust borrow checker).
let rt = RuntimeContext::new(Utc::now(), "fp-001");
let live = turnstile_core::expiry::LiveJudgment::new(judgment, &rt);
assert_eq!(live.permission(), Permission::DIA);
```

### Composition

```rust
use turnstile_core::compose;

let composed = compose(ctx1, ctx2)?;
// Composition is non-promoting:
// compile(composed).permission <= min(compile(ctx1).permission, compile(ctx2).permission)
```

---

## Quick Start — Python

```python
import time
import turnstile as ts

# Compute provenance hash.
h = ts.compute_provenance_hash("my-claim", "z-001", "ctx-001", "diagnostics")

# Build a ProofToken.
token = ts.ProofToken(
    token_id="tok-1",
    token_type="CALIBRATION_CERT",
    schema_version="0.1",
    status="valid",
    closes_gaps=["calibration-gap"],
    bounds_gaps=[],
    provenance_hash=h,
    issued_at=time.time(),
    issuer="domain-certifier",
)

# Build the context.
ctx = ts.ProofContext(
    claim_id="my-claim",
    candidate_id="z-001",
    context_id="ctx-001",
    allowed_use="diagnostics",
    membership=ts.Membership.InClass,
    authority_ceiling=ts.Permission.AAA,
    expiry=ts.Expiry.never(),
    gaps=[ts.GapRecord("calibration-gap", "calibration_gap", status="closed")],
    profiles=[ts.Profile(
        ts.Permission.DIA,
        [ts.GapRequirement("calibration-gap", "closed")],
    )],
    tokens=[token],
)

# Compile.
live = ts.compile(ctx)
rt = ts.RuntimeContext(now_unix=time.time(), context_fingerprint="ctx-001")
print(live.permission_str(rt))  # "DIA"
```

### Composition in Python

```python
composed = ts.compose(ctx1, ctx2)
live = ts.compile(composed)
# Non-promotion guarantee holds automatically.
```

---

## The 4 Structural Guarantees

| Property | Description |
|----------|-------------|
| **Non-promotion under composition** | `compile(Γ₁ ⊗ Γ₂).permission ≤ min(compile(Γ₁), compile(Γ₂))` — composition cannot launder permission |
| **Provenance enforcement** | Tokens are accepted only when their SHA-256 provenance hash exactly matches `(claim_id, candidate_id, context_id, allowed_use)`; no fuzzy matching |
| **Expiry fires at boundary** | `LiveJudgment::permission()` returns `EXP` for all `now ≥ deadline`; Rust borrow checker prevents stale reads |
| **Evidence monotonicity** | Adding a closed proof token to a context never lowers the emitted permission |

All four properties are checked by `proptest` property-based tests on every run:

```bash
cargo test -p turnstile-tests
```

---

## Implementing a Certifier

The `Certifier` trait is the primary extension point. A certifier is the domain component that issues and validates proof tokens. Turnstile calls `validate()` at compile time; your domain layer calls `issue()`.

```rust
use turnstile_core::certifier::{Certifier, Evidence, IssueError, ValidationResult};
use turnstile_core::context::ProofContext;
use turnstile_core::token::{compute_provenance_hash, ProofToken, TokenStatus};
use chrono::Utc;

struct CalibrationCertifier;

impl Certifier for CalibrationCertifier {
    fn name(&self) -> &str { "calibration" }

    fn issue(&self, evidence: Evidence) -> Result<ProofToken, IssueError> {
        // Inspect evidence.payload, run domain checks, then emit a token.
        let ctx_tuple = serde_json::from_value::<(String,String,String,String)>(
            evidence.payload.clone()
        ).map_err(|e| IssueError::Internal(e.to_string()))?;

        Ok(ProofToken {
            token_id: uuid::Uuid::new_v4().to_string(),
            token_type: "CALIBRATION_CERT".into(),
            schema_version: "0.1".into(),
            status: TokenStatus::Valid,
            closes_gaps: vec!["calibration-gap".into()],
            bounds_gaps: vec![],
            provenance_hash: compute_provenance_hash(
                &ctx_tuple.0, &ctx_tuple.1, &ctx_tuple.2, &ctx_tuple.3,
            ),
            issued_at: Utc::now(),
            expires_at: None,
            issuer: "calibration-certifier".into(),
            details: evidence.payload,
            is_negative_control: false,
        })
    }

    fn validate(&self, token: &ProofToken, _ctx: &ProofContext) -> ValidationResult {
        if token.token_type == "CALIBRATION_CERT" {
            ValidationResult::ok()
        } else {
            ValidationResult::fail("wrong token type")
        }
    }
}
```

Turnstile's compiler does not call certifiers directly — it only inspects token provenance hashes and gap membership. Certifiers are called by your domain layer before tokens are placed in a `ProofContext`.

---

## Building

### Rust

```bash
# Build everything.
cargo build

# Run all tests (unit + structural + property).
cargo test
cargo test -p turnstile-tests

# Run benchmarks.
cargo bench -p turnstile-core
```

### Python (via maturin)

```bash
# Install maturin if needed.
pip install maturin

# Build and install in development mode.
python3 -m maturin develop

# Build a release wheel.
python3 -m maturin build --release
```

After `maturin develop`, the `turnstile` package is importable in the current Python environment.

---

## Architecture

```
turnstile-core/          Pure Rust library (no PyO3 dependency)
  permission.rs          Permission enum + total order + algebra
  gap.rs                 GapStatus, GapRecord, Profile, GapRequirement
  token.rs               ProofToken, provenance hashing
  context.rs             ProofContext (Γ), Scope, Membership
  compiler.rs            compile() — descending search + structural meets
  composition.rs         compose() — lax monoidal composition
  expiry.rs              Expiry, RuntimeContext, LiveJudgment<'ctx>
  error.rs               TurnstileError hierarchy
  registry.rs            Append-only schema registry
  audit.rs               AuditEntry, Derivation, AuditStore trait
  certifier.rs           Certifier trait (main extension point)

turnstile-py/            PyO3 bindings (thin wrapper over turnstile-core)
  src/lib.rs             #[pymodule] + all #[pyclass] wrappers

turnstile-tests/         Structural and property-based tests
  ec003*/                EC-003 theorem suite (composition algebra,
                         provenance, expiry, token status, OOC variants, …)
  ec004_*/               EC-004 profile well-formedness
  ec005_*/               EC-005 domain admission
  proptest_*/            Property-based tests for the 4 structural guarantees
  step11_assembler       Assembler integration tests
```

---

## License

Apache 2.0. See [LICENSE](LICENSE).
