# Turnstile

[![CI](https://github.com/adisriram/turnstile/actions/workflows/ci.yml/badge.svg)](https://github.com/adisriram/turnstile/actions/workflows/ci.yml)
[![Crates.io](https://img.shields.io/crates/v/turnstile-core)](https://crates.io/crates/turnstile-core)
[![PyPI](https://img.shields.io/pypi/v/turnstile)](https://pypi.org/project/turnstile/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

Turnstile is an **admissibility compiler** for approximate consequential systems. Given a proof context Γ — a set of gap records, profiles, proof tokens, and authority constraints — it produces the strongest permission `p` the evidence supports and a binding expiry `ε`. The answer is a judgment in a typed form that the Rust borrow checker prevents from being read after it expires.

This library is for teams building systems where autonomous or consequential actions should be gated on structured evidence: calibration certificates, negative-control results, role assertions, scope restrictions. Turnstile handles the algebra; your domain supplies the certifiers.

**Judgment form:** `Γ ⊢ z : p until ε`

---

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/guide/introduction.md`](docs/guide/introduction.md) | Gentle introduction to admissibility compilers for approximate consequential systems — concepts, vocabulary, worked examples, and when this design does and doesn't fit |
| [`docs/papers/admissibility_compilers_for_approximate_consequential_systems.md`](docs/papers/admissibility_compilers_for_approximate_consequential_systems.md) | Core compiler paper: judgment form, permission algebra, gap/profile/token machinery, 19 structural theorems, PGM benchmark results |
| [`docs/papers/admissible_compilability_representation_theorem.md`](docs/papers/admissible_compilability_representation_theorem.md) | Representation theorem: characterizes exactly when a domain admits a bounded sharp monotone compiler; WQO and semialgebraic corollaries |

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
    permission_ceiling: Permission::AAA,
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

**1195 tests total — 998 Rust (85 files) + 100 Python (8 files) + 97 PGM example tests (6 files).** Every test passes on every commit (ubuntu + macos CI matrix).

The PGM example (`examples/pgm/bridge/certifier.py`) ships a reference certifier implementation: `PGMExactCertifier` self-computes all fingerprints from inputs and runs inference internally before issuing a token; `PGMModelSpecificationCertifier` is a documented stub that raises `NotImplementedError` with an explanation of why domain-expert attestation cannot be automated. See `examples/pgm/README.md` for the full certifier boundary discussion.

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

## Caller Responsibilities

Two checks that the compiler does **not** enforce internally — callers must invoke them:

### 1. Scope candidate admission

The compiler does not verify that `candidate_id ∈ scope.allowed_candidates`. After compiling, check before acting on the judgment:

```rust
// Returns true when allowed_candidates is empty (unconstrained) or contains candidate_id.
fn candidate_in_scope(scope: &Scope, candidate_id: &str) -> bool {
    scope.allowed_candidates.is_empty()
        || scope.allowed_candidates.iter().any(|c| c == candidate_id)
}

if !candidate_in_scope(&ctx.scope, &ctx.candidate_id) {
    // reject — candidate is outside declared scope
}
```

### 2. Profile monotonicity (Law G01)

The compiler does not validate that profiles are monotone (stronger permissions require at least as strong evidence as weaker ones). Validate on profile construction:

```rust
// Returns an error message if profiles[i].permission > profiles[j].permission but
// profiles[i] declares a weaker gap requirement than profiles[j] for the same gap_id.
fn check_profile_monotonicity(profiles: &[Profile]) -> Option<String> {
    for i in 0..profiles.len() {
        for j in 0..profiles.len() {
            if profiles[i].permission <= profiles[j].permission { continue; }
            for req_j in &profiles[j].required_gaps {
                if let Some(req_i) = profiles[i].required_gaps.iter()
                    .find(|r| r.gap_id == req_j.gap_id)
                {
                    let rank = |r: RequiredStatus| match r {
                        RequiredStatus::OpenAllowed     => 0u8,
                        RequiredStatus::BoundedRequired => 1u8,
                        RequiredStatus::ClosedRequired  => 2u8,
                    };
                    if rank(req_i.minimum_status) < rank(req_j.minimum_status) {
                        return Some(format!(
                            "gap '{}': {} requires {:?} but {} requires {:?}",
                            req_j.gap_id,
                            profiles[i].permission, req_i.minimum_status,
                            profiles[j].permission, req_j.minimum_status,
                        ));
                    }
                }
            }
        }
    }
    None
}
```

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
python3 -m venv .venv && .venv/bin/pip install maturin pytest
.venv/bin/maturin develop

# Run the Python integration test suite.
.venv/bin/pytest

# Build a release wheel.
.venv/bin/maturin build --release
```

After `maturin develop`, the `turnstile` package is importable in the active environment.

---

## Architecture

```
docs/guide/              Conceptual guides
  introduction.md        Admissibility compilers for approximate consequential systems — concepts and worked examples
docs/papers/             Research papers
  admissibility_compilers_for_approximate_consequential_systems.md
                         Compiler paper: judgment form, 19 theorems, PGM benchmark
  admissible_compilability_representation_theorem.md
                         Representation theorem: when a domain admits a sharp compiler

examples/pgm/            PGM inference integration example (97 Python tests)
  bridge/                domain adapter — token types, fingerprinting, gap profiles
    certifier.py         PGMExactCertifier + PGMModelSpecificationCertifier (stub)
  demo/                  self-contained diabetes BIF memory-budget sweep demo
    inference/           certified inference compiler (copied + stripped from hilbert-flow)
    bif_loader.py        BIF parser + ModelInstance factory
    tokens.py            InferenceResult → turnstile ProofToken translation layer
    run_demo.py          main script: 3-row OOC/DIA/AEX budget table
  tests/                 97 tests: bridge (10), demo (4), stress (32), BIF (32), gaps (20), tokens (9)
  results/               captured test and demo outputs (dated)
  conftest.py            auto-inserts workspace python/ ahead of any installed wheel

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

turnstile-tests/         Structural and property-based tests (998 Rust tests)
  ec003*/                EC-003 theorem suite (composition algebra,
                         provenance, expiry, token status, OOC variants, …)
  ec004_*/               EC-004 profile well-formedness
  ec005_*/               EC-005 domain admission
  ec006_*                Law G01 profile monotonicity validator
  ec007_*                Derivation chain soundness (non-increasing steps)
  ec008_*                Concurrent AuditStore integrity
  ec009_*                Permission::from_str exhaustive coverage
  ec010_*                Scope candidate admission (rule [ADMISSIBLE])
  ec011_*                GapStatus min_status algebra invariants
  ec012_*                Priority tier dominance (T8, T10)
  ec013_*                Composition fail-closed on all conflict types
  ec014_*                SchemaRegistry append-only invariants R1–R7
  ec015_*                Disallowed-use accumulation (T13)
  ec016_*                Compile determinism (sequential + concurrent)
  ec017_*                Error type coverage (all variants reachable)
  ec018_*                Large-context stress (100–500 gaps, 200 tokens)
  ec019_*                T11 diagnostic/action separation (exhaustive)
  ec020_*                Token and context expiry edge cases
  ec021_*                MalformedContext validation (all 4 conditions)
  ec022_*                LiveJudgment<'ctx> runtime T15 contract
  ec023_*                descending() order stability (pinned sequence)
  ec024_*                Token expiry masking in composition
  ec025_*                BoundKind variant coverage (Numeric/SetValued/Infinity)
  ec026_*                Dead-token expiry semantics (only Valid triggers EXP)
  ec027_*                Compose claim_id/candidate_id semantics
  ec028_*                Provenance hash unicode and large inputs
  ec029_*                Poisoned-mutex recovery (SchemaRegistry + AuditStore)
  ec030_*                compile()/compose() never panic (adversarial inputs)
  ec031_*                Adversarial families A1–A10 (EC-001 §34)
  ec032_*                Positive families P1–P10 (EC-001 §34, in-class domains)
  ec033_*                Negative families N1–N10 (EC-001 §34, OOC exact)
  ec034_*                Permission tier semantics (T8, exhaustive 144-pair meet)
  ec035_*                Multi-profile descending search (determinism, S7–S12)
  ec036_*                Token liveness and freshness (L1–L15, EXP floor)
  ec037_*                Serde round-trip and wire-format stability (W1–W12)
  ec038_*                Scope intersection semantics (SI1–SI10, T14)
  ec039_*                Derivation and audit trail integrity (D1–D12, T18)
  ec040_*                Composition identity laws (CI1–CI8, T6 end-to-end)
  ec041_*                Allowed-use soundness (AU1–AU14, T12, byte-exact binding)
  ec042_*                Heterogeneous anti-laundering (H1–H16, T16, OOC absorbing)
  ec043_*                Audit-not-authority exhaustive (A1–A9, T18, replay attacks)
  ec044_*                Authority ceiling exhaustive (C1–C14, T19, hard cap)
  ec045_*                Permission triples exhaustive (TR1–TR5, all 1728 triples)
  ec046_*                Meet GLB property exhaustive (GLB1–GLB5, T8, greatest lower bound)
  ec047_*                Step 11 assembler truth table (S1–S16, T8/T11, tier dominance)
  ec048_*                Theorem 2 greatest-satisfiable (T2-1–T2-11, T5/T10)
  ec049_*                Admission contract A1–A9 depth (T6/T19, bounded-time, adversarial)
  ec050_*                Schema version adversarial (SV1–SV12, T2, mismatch/concurrent)
  proptest_*/            Property-based tests for the 4 structural guarantees
  step11_assembler       Assembler integration tests

python/tests/            Python integration tests (100 tests, pytest)
  test_py001_permission  Permission ordering, meet, from_str, hash
  test_py002_compile_basic  compile() outcomes: OOC/DIA/EXP/MalformedContext
  test_py003_live_judgment  LiveJudgment expiry, fingerprint, idempotence
  test_py004_compose     compose() identity inheritance, g2 token rejection
  test_py005_timestamps  Timestamp precision and EXP floor boundary behavior
  test_py006_exceptions  Exception hierarchy and message quality
  test_py007_types       GapRecord/Membership/NegativeControlStatus/ProofToken
  test_py008_derivation  Derivation steps, compiled_at, permission match
```

---

## License

Apache 2.0. See [LICENSE](LICENSE).
