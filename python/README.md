# noethers-turnstile — Python bindings

PyO3 bindings for the [noethers-turnstile-core](../noethers-turnstile-core/src/lib.rs) Rust library.
The Python package exposes the full compiler surface: `compile()`, `compose()`, all context and
token types, the permission lattice, expiry, and the `Certifier` pattern.

## Installation

```bash
# Development (build from source with maturin)
pip install maturin
python3 -m venv .venv && source .venv/bin/activate
pip install maturin pytest
maturin develop

# Or install the published wheel
pip install noethers-turnstile
```

After `maturin develop` the `noethers_turnstile` package is importable in the active environment.

## Quick start

```python
import time
import noethers_turnstile as ts

# 1. Compute provenance hash — binds the token to exactly this deployment slot.
h = ts.compute_provenance_hash("my-claim", "z-001", "ctx-001", "diagnostics")

# 2. Build a token issued by your certifier.
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

# 3. Build the proof context.
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

# 4. Compile and read through a RuntimeContext (expiry enforced here).
live = ts.compile(ctx)
rt = ts.RuntimeContext(now_unix=time.time(), context_fingerprint="ctx-001")
print(live.permission_str(rt))  # "DIA"
```

## Composition

```python
composed = ts.compose(ctx1, ctx2)
live = ts.compile(composed)
# Non-promotion holds automatically:
# compile(composed).permission <= min(compile(ctx1), compile(ctx2))
```

## Permission chain

```
OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA < REV < AEX < ALR < AAA
```

`OOC` is the bottom (weakest). `AAA` is the top (strongest). `meet(a, b) = min(a, b)`.

## API surface

| Symbol | Description |
|---|---|
| `Permission` | Enum of the 12 permission levels. Supports `<`, `<=`, `meet()`, `from_str()` |
| `GapRecord(gap_id, gap_type, status=...)` | One gap entry in a context |
| `GapRequirement(gap_id, minimum_status)` | Requirement within a profile |
| `Profile(permission, requirements)` | One row in the evidence ladder |
| `ProofToken(...)` | Evidence token issued by a domain certifier |
| `Expiry.never()` / `Expiry.at(unix)` | Context expiry deadline |
| `Scope(allowed_candidates, ...)` | Optional scope constraint |
| `Membership.InClass` / `OutOfClassExact` / ... | Candidate membership classification |
| `ProofContext(...)` | The full proof context Γ passed to `compile()` |
| `RuntimeContext(now_unix, context_fingerprint)` | Runtime snapshot for expiry evaluation |
| `LiveJudgment` | Returned by `compile()`. Call `.permission(rt)` or `.permission_str(rt)` |
| `Judgment` | Static snapshot returned by `compile_static()` |
| `compile(ctx)` | Main entry point — returns `LiveJudgment` |
| `compile_static(ctx)` | Returns a `Judgment` without a runtime handle |
| `compose(g1, g2)` | Lax monoidal composition of two contexts |
| `compute_provenance_hash(claim, candidate, context, use)` | SHA-256 binding hash |

Full type stubs: [`noethers_turnstile/__init__.pyi`](noethers_turnstile/__init__.pyi).

## Tests

100 pytest tests covering the full Python API surface:

```bash
# From the repo root (after maturin develop):
.venv/bin/pytest python/tests/ -v
```

| File | Coverage |
|---|---|
| `test_py001_permission.py` | Permission ordering, meet, `from_str`, hash |
| `test_py002_compile_basic.py` | `compile()` outcomes: OOC/DIA/EXP/MalformedContext |
| `test_py003_live_judgment.py` | `LiveJudgment` expiry, fingerprint, idempotence |
| `test_py004_compose.py` | `compose()` identity inheritance, token rejection |
| `test_py005_timestamps.py` | Timestamp precision and EXP floor boundary behavior |
| `test_py006_exceptions.py` | Exception hierarchy and message quality |
| `test_py007_types.py` | `GapRecord`, `Membership`, `NegativeControlStatus`, `ProofToken` |
| `test_py008_derivation.py` | Derivation steps, `compiled_at`, permission match |

## Building a release wheel

```bash
.venv/bin/maturin build --release
# Wheel lands in target/wheels/
```
