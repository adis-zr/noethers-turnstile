# Turnstile

Turnstile is an admissibility compiler. It takes a proof context Γ and a candidate z, evaluates the gap profile against proof tokens, and emits the strongest permission the evidence supports. It enforces conservation, idempotence, provenance, scope, expiry, authority, and runtime non-upgrade.

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

## Building

### Rust

```bash
# Build everything.
cargo build

# Run all tests (unit + property).
cargo test

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
  audit.rs               AuditTrail, Derivation
  certifier.rs           Certifier trait

turnstile-py/            PyO3 bindings (thin wrapper over turnstile-core)
  src/lib.rs             #[pymodule] + all #[pyclass] wrappers

turnstile-tests/         Property-based tests (proptest)
  proptest_composition   Non-promotion under composition
  proptest_provenance    Provenance hash enforcement
  proptest_expiry        Expiry fires at boundary
  proptest_monotonicity  Adding closed token never lowers permission
```

---

## License

Apache 2.0. See [LICENSE](LICENSE).
