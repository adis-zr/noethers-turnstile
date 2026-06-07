# Spec: Native Permission Chains in Examples and Benchmarks

**Status:** Proposed
**Scope:** `examples/`, `noethers-turnstile-core/benches/`, the Python binding's `PermissionChain` surface.
**Depends on:** `docs/specs/permission_chain_refactor_spec.md` (already shipped).

## 0. What the refactor actually shipped (read this first)

This spec was originally drafted against the v2 refactor spec; the shipped code (commit `9a85737`) diverged from that draft in two places that matter for this work. Both deltas are in the shipped library, not new asks of this spec.

**0.1 — `ChainRole` has SEVEN variants, not six.** The shipped `noethers-turnstile-core/src/permission.rs:191-211` declares:

```rust
pub enum ChainRole {
    Bottom,
    ExpiryFloor,
    Refused,
    Unsatisfied,
    DisallowedUsesCeiling,    // <-- added during the refactor
    BlockerThreshold,
    Top,
}
impl ChainRole {
    pub const ALL: [ChainRole; 7] = [ ... ];
}
```

The seventh role, `DisallowedUsesCeiling`, was added late in the refactor to fix a CI-grep Gate 2 violation: the compiler's `disallowed_uses` ceiling step had been written as `chain.parse("ROL")` — a quoted string literal that Gate 2 catches. The fix was to give that ceiling a chain role. The default chain maps it to `ROL` (rank 6); paper-style chains collapse it to `Bottom`. The validator's L9b (in `permission.rs:497-521`) requires `DisallowedUsesCeiling < Top` strictly; no other constraint.

So critique #1 in the most recent review ("the role enum has seven roles here and six in the shipped refactor") points at a real ambiguity but the wrong direction: this spec was right, the reviewer's reading of the refactor was from the v2 draft, not the shipped code. The refactor spec at `docs/specs/permission_chain_refactor_spec.md` §2 still lists six roles and is now stale; that's a documentation cleanup, not a redesign.

**0.2 — `InMemoryChainRegistry` + `verify_published` already exist.** `noethers-turnstile-core/src/permission.rs:734-789` ships the `ChainRegistry` trait, `InMemoryChainRegistry` struct, and `lib.rs:80` exposes `verify_published`. These were added as the §3.3 mechanism 4 of the refactor spec. Phase 1 of this spec only adds the **Python binding** for them, not the Rust types themselves. Critique #5 ("new core+binding API masquerading as binding-only") is half-right: the *core* surface already exists; the *binding* surface does not. The spec should say "expose existing core API through PyO3" — that's what §3.1 was trying to do, but the language was sloppy. Fixed in §3 below.

**0.3 — Default-chain accessors are `pub fn`, not `static`.** Verified against shipped code (`noethers-turnstile-core/src/default_levels.rs:24-34`). The `level_fn!` macro emits:

```rust
pub fn $name() -> Permission {
    static CACHE: OnceLock<Permission> = OnceLock::new();
    *CACHE.get_or_init(|| level($literal))
}
```

So `default_levels::DIA()` (with parens, call syntax) is the correct accessor; same shape for `Permission::DIA()` via the `impl Permission` block at line 53. There are no `pub static`s; v2-era specs that wrote `default_levels::DIA.clone()` are stale.

**0.4 — The `disallowed_uses` ceiling step is guarded.** Verified against shipped code (`noethers-turnstile-core/src/compiler.rs:340`):

```rust
if !ctx.disallowed_uses.is_empty() {
    let disallowed_ceiling = chain.role(ChainRole::DisallowedUsesCeiling).clone();
    let after = chain.meet(&outcome, &disallowed_ceiling)?;
    // ... step records and outcome update ...
}
```

The meet only fires when the context's `disallowed_uses` list is non-empty. This is load-bearing for any chain that collapses `DisallowedUsesCeiling` to `Bottom`: the role value would otherwise floor every outcome to Bottom on every compile. The guard is what makes the collapse safe.

**Net effect on this spec:** all role dicts already use the seven-role form. `DisallowedUsesCeiling` is correct, not an error. The Python binding adds existing Rust types, not new ones. References to "six roles" or `default_levels::DIA` (no parens) in the v2-era refactor spec are out of date. Examples that collapse `DisallowedUsesCeiling` to `Bottom` rely on the §0.4 guard — see §2.0 for the explicit invariant each example must satisfy, and §7.4 #6 for the dual-of-AM-01 test that verifies the collapse is sound.

---

## 1. Problem

The permission-chain refactor (commit `9a85737`) made the compiler chain-parameterized at the library boundary. The Python bindings still expose only the default 12-level chain. As a result, every example written in Python that wants its own domain vocabulary today does one of two things:

**(a) Translate domain semantics onto the default chain.** ILS is the cleanest case. `examples/ils/profiles.py` declares:

```python
PERM_DESCEND  = t.Permission.DIA   # DESCEND_TO_DH
PERM_MANUAL   = t.Permission.REV   # LAND_MANUAL
PERM_ASSISTED = t.Permission.AEX   # LAND_ASSISTED
PERM_ZERO     = t.Permission.ALR   # LAND_ZERO_ZERO
```

with the explicit docstring "Permission chain (operational meaning only, no FAA category names)". The compiler emits `t.Permission.DIA` but the *real* answer is `DESCEND_TO_DH`. The translation is a comment that the system cannot read.

**(b) Reimplement the compiler.** `examples/inference/register2/turbo/compiler_turbo.py` and `compiler_blind.py` do this. They define an integer chain (`TRANSMIT=3, HOLD=1, REFUSE=0`) and run their own threshold-scan logic. They do not call `noethers_turnstile.compile` at all — they are *the same algorithm, reimplemented*, because the chain wasn't parameterizable when they were written.

This spec proposes:

1. **A Python binding for `PermissionChain`** so domain examples can construct their own chain (Phase 1).
2. **A rewrite of every example currently doing (a) or (b)** to call the library compiler with a domain-native chain (Phase 2).
3. **Update the Rust benchmark** (`bench_compile.rs`) similarly (Phase 3).
4. **Verification protocol** — every rewritten example must reproduce the same `paper-relevant outputs` as before (Phase 4).

The user's framing: "you should be able to reproduce the same results by actually now passing in the permission chain and gaps directly to the compiler library without having to do a translation."

That is the success criterion. No translation comment, no integer-coded chains, no reimplemented compilers.

---

## 2. Inventory: every Python file that touches `Permission`

I read every file in the `examples/` tree to classify how it uses the chain. The classification is in §2.1.

### 2.0 Invariant: `DisallowedUsesCeiling = Bottom` requires zero declared disallowed uses

Multiple chains in this spec collapse `DisallowedUsesCeiling` to `Bottom`. This is safe **iff** the contexts compiled against the chain never declare a non-empty `disallowed_uses` list. Restated:

> **Collapse invariant.** A chain that maps `ChainRole::DisallowedUsesCeiling` to its `Bottom` level is sound only for contexts where `ctx.disallowed_uses` is empty. Compiling a context with a non-empty `disallowed_uses` against such a chain floors every outcome to `Bottom` (because the §0.4 guarded meet fires `outcome = chain.meet(outcome, Bottom)`, and `meet(x, Bottom) = Bottom` for any `x`).

This is the dual of the AM-01 expiry-floor landmine from the refactor: a role collapsed to a value that's catastrophic if its step ever fires. Per-example responsibilities:

| Example | DisallowedUsesCeiling target | Declares `disallowed_uses`? | Invariant satisfied? |
|---|---|---|---|
| ILS | `REFUSE_APPROACH` (Bottom) | No (verified: §2.2.1 confirms) | Yes |
| Credit | `REFUSE` (Bottom) | No (verified: §2.2.2 confirms) | Yes |
| EPIC | (deferred) | (deferred) | (deferred) |
| Conservation | depends on §11 Q3 resolution | No (no run script uses `disallowed_uses`) | Yes either way |
| Forecast value | `NO_ACTION` (Bottom) | No (verified: `domain.py` does not set disallowed_uses) | Yes |
| Turbo (A) | `REFUSE` (Bottom) | No (turbo contexts are pure (SNR, ber, bler) cells with no use restrictions) | Yes |
| Turbo (B) | `REFUSE` (Bottom) | No (same as A) | Yes |

**If any example ever needs `disallowed_uses`**, its chain must bind `DisallowedUsesCeiling` to a non-Bottom level (e.g., a `RESTRICTED` level just below the operational profiles). Adding a disallowed-use to an example that currently has none is a chain-level change, not just a context-level change. The rewrites in Phase 2 do NOT introduce disallowed_uses to any example that lacks them; that's an out-of-scope future change.

**Test (§7.4 #6, new).** For each rewritten example, a smoke test compiles a representative context against the example's chain and asserts the emit is NOT `chain.role(Bottom)` for at least one input that *should* emit higher. This catches the case where the collapse invariant is silently violated by a future test fixture adding `disallowed_uses=["something"]`.

### 2.1 Classification

| Class | Description | Files |
|---|---|---|
| **T (translation)** | Imports `noethers_turnstile`, calls `t.compile()`, but maps domain levels onto default-chain names via a comment block | ILS (`profiles.py`, `ils_compiler.py`, `sweeps.py`, `run_ils_audit.py`), Credit (`experiment/profile.py`, `experiment/compiler.py`, `run_credit_audit.py`), EPIC (`acs/compiler.py`, `experiment/compiler.py`, `experiment/profile.py`, `run_*.py`, `tests/test_*.py`), forecast_value (`domain.py`, `baselines.py`) |
| **R (reimplemented)** | Does NOT import the library; defines its own integer permission chain + threshold-scan logic | `inference/register2/turbo/compiler_turbo.py`, `compiler_blind.py`, `sweep_turbo.py`, `audit_3gpp.py`, `experiment_a_stability.py`, `sensitivity_bler.py`, `ber_bler_curves.py` |
| **N (native default)** | Uses the default chain because the default chain *is* the natural vocabulary (no translation, no domain-specific names) | conservation (most run scripts use the default chain's REF/DIA/REV/AEX/ALR as the operational chain per the paper §2.2) |
| **U (utility)** | Imports the library but does not construct profiles/permission references — only types like `ProofContext`, `Expiry`, etc. | `examples/epic/conftest.py`, helpers in `examples/epic/adapter/` |

### 2.2 Per-example summary

Each subsection lists: (a) what the example does, (b) its current chain shape (T/R/N), (c) the proposed domain-native chain, (d) the planned rewrite scope.

#### 2.2.1 ILS (`examples/ils/`) — Class T

- **What it does:** Compiles instrument-landing-system approach authorization. Three gaps (`ils_signal_integrity`, `visual_reference`, `sub_cat1_authorization`). Sweeps RVR and DH to find the boundary where outcome transitions between approach permissions. Paper Track A §2.4 (FAA recovery).
- **Current chain:** 5 levels via translation onto default chain levels. The translation is documented in `profiles.py`.
- **Proposed native chain:** `REFUSE_APPROACH < CONTINUE_APPROACH < DESCEND_TO_DH < LAND_MANUAL < LAND_ASSISTED < LAND_ZERO_ZERO`. Six levels. Bottom = `REFUSE_APPROACH`. Top = `LAND_ZERO_ZERO`. Roles: `Bottom=REFUSE_APPROACH`, `ExpiryFloor=REFUSE_APPROACH`, `Refused=REFUSE_APPROACH`, `Unsatisfied=CONTINUE_APPROACH`, `DisallowedUsesCeiling=CONTINUE_APPROACH`, `BlockerThreshold=DESCEND_TO_DH`, `Top=LAND_ZERO_ZERO`.
- **Files to rewrite:** `profiles.py`, `ils_compiler.py`, `sweeps.py`, `run_ils_audit.py`, `faa_comparison.py` (the comparison to FAA categories — now reads `LAND_MANUAL` as `CAT_I`, etc., explicitly). Tests under `examples/ils/` if any.

#### 2.2.2 Credit (`examples/credit/`) — Class T

- **What it does:** ECOA adverse-action induction. Starts from a structural skeleton (approximation_quality + freshness) and grows the gap taxonomy case-by-case until reason-traceability is induced. Paper Track A §2.6 (ECOA recovery).
- **Current chain:** Maps DIA/REV/AEX/ALR/AAA onto domain semantics in `experiment/profile.py`:
    ```python
    DIA  — model exists and produces an output; nothing else known
    REV  — approximation quality bounded; suitable for expert review only
    AEX  — structural skeleton satisfied; experiment-authorized
    ALR  — all induced domain gaps bounded; authorized for limited rollout
    ```
- **Proposed native chain:** `REFUSE < MODEL_EXISTS < EXPERT_REVIEW < EXPERIMENT_AUTHORIZED < LIMITED_ROLLOUT < FULL_AUTHORITY`. Six levels.
- **Files to rewrite:** `experiment/profile.py`, `experiment/compiler.py`, `experiment/induction.py`, `experiment/cases.py`, `experiment/cfpb_audit.py`, `run_credit_audit.py`, and any oracle/report builders.

#### 2.2.3 EPIC (`examples/epic/`) — Class T

- **What it does:** Sepsis-model deployment audit. Same skeleton as credit (approximation_quality + freshness) extended with the seven socio-technical gaps (operating-point utility, model specification, distribution shift, individual-population, blast radius, authority, reason traceability). Paper Track A §2.5.
- **Current chain:** Same DIA/REV/AEX/ALR/AAA pattern as credit, mapped onto deployment semantics.
- **Proposed native chain:** `REFUSE < OUTPUT_ONLY < EXPERT_REVIEW < EXPERIMENT_AUTHORIZED < LIMITED_ROLLOUT < FULL_AUTHORITY`. Same five-plus-refuse shape as credit; the level NAMES differ slightly (`OUTPUT_ONLY` vs. `MODEL_EXISTS`) to match Epic's docstring narration.
- **Files to rewrite:** ~30 files under `examples/epic/`, including run scripts, the `experiment/` and `acs/` subdirectories, and tests under `examples/epic/tests/`.
- **Notable:** EPIC is by far the heaviest. About 60% of all the example-rewrite work lives here. Per §6 (scoping), it is **optional / deferred to a follow-up commit**.

#### 2.2.4 Conservation (`examples/conservation/`) — Class N (mostly)

- **What it does:** Runs §6 of the pivot paper — the central two-axis convergence experiment. Permission densification, evidence hiding, projection fidelity. Paper Track B §2 (pivot).
- **Current chain:** Uses default chain by NAME (`REF`, `DIA`, `REV`, `AEX`, `ALR`) as the actual operational vocabulary. The pivot paper §2.2 lists these as the abbreviated 5-level chain — these ARE the domain levels for the conservation experiments.
- **Proposed:** **No rewrite required for the levels themselves.** However, the conservation scripts should switch from `t.Permission.DIA` (default chain accessor) to a **paper-5-level chain** constructed explicitly, so they (i) exercise the new API, (ii) demonstrate that the same `REF/DIA/REV/AEX/ALR` names work under an *author-declared* chain rather than borrowed from the default, and (iii) document the chain object in the paper appendix. This is a small ergonomic rewrite (each run script imports the chain from a shared `chain.py` helper).
- **Files to rewrite:** ~11 run scripts under `examples/conservation/`. Each gets a 5-line `chain = PermissionChain.paper_5_level()` and `compile(ctx, chain=chain)` swap.

#### 2.2.5 Forecast value (`examples/forecast_value/`) — Class T

- **What it does:** Frost-protection domain for the meet-vs-cost-loss confrontation. Paper Track B §6 (forecast value).
- **Current chain:** Maps frost-protection semantics onto default chain:
    ```
    REF : base
    DIA : exceedance reported
    REV : exceedance bounded
    AEX : exceedance bounded + (duration OR vulnerability bounded)
    ALR : exceedance bounded + duration + vulnerability bounded
    ```
- **Proposed native chain:** `NO_ACTION < REPORT_EXCEEDANCE < BOUND_EXCEEDANCE < ACT_ON_PARTIAL_EVIDENCE < ACT_ON_FULL_EVIDENCE`. Five levels.
- **Files to rewrite:** `domain.py`, `baselines.py`, `controls.py`, `arm1_divergence.py`, `arm2_conservation.py`, `worldgen.py` (only if it imports the chain), `run_all.py`.

#### 2.2.6 Inference register-2 turbo (`examples/inference/register2/turbo/`) — Class R

- **What it does:** 3GPP 5G NR audit. Sweeps SNR, decodes turbo-coded blocks, classifies each (BER, BLER) pair into a permission level, recovers 3GPP thresholds blind. Paper Track A §2.4.
- **Current chain:** **Reimplements the compiler** with integer constants and threshold-scan logic. Two separate chains: `compiler_turbo.py` (4 levels for the Phase-A cross-register comparison) and `compiler_blind.py` (5 levels for the Phase-B blind audit). `audit_3gpp.py` calls these reimplemented compilers, not `noethers_turnstile.compile`.

- **Original `emit()` has a catastrophic fork that the encoding must preserve.** `compiler_turbo.py` lines 282–288:
    ```python
    if ber > τ_BER[MONITORED] or bler > τ_BLER[MONITORED]:
        return REFUSE if (ber > 1.0 or bler > 1.0) else HOLD
    if ber > τ_BER[TRANSMIT] or bler > τ_BLER[TRANSMIT]:
        return TRANSMIT_MONITORED
    return TRANSMIT
    ```
    The MONITORED-failure branch splits on a SECOND threshold (`ber > 1.0` is catastrophic — channel is unusable; `≤ 1.0` is sub-threshold — channel exists but is below monitored). This split is independent of the τ levels and must survive the rewrite, or the densification headline ("breakpoints grow with k") corrupts: every cell that fails MONITORED collapses to a single below-threshold value instead of forking REFUSE / HOLD.

- **Proposed Phase A native chain:** `REFUSE < HOLD < TRANSMIT_MONITORED < TRANSMIT`. Four levels.

- **Proposed Phase A gaps (with the catastrophic gap):**
    - `ber_below_tau_transmit` — closed iff `ber ≤ τ_BER[TRANSMIT]`
    - `bler_below_tau_transmit` — closed iff `bler ≤ τ_BLER[TRANSMIT]`
    - `ber_below_tau_monitored` — closed iff `ber ≤ τ_BER[MONITORED]`
    - `bler_below_tau_monitored` — closed iff `bler ≤ τ_BLER[MONITORED]`
    - `channel_not_catastrophic` — closed iff `ber ≤ 1.0 AND bler ≤ 1.0` (the missing degree of freedom)

- **Proposed Phase A profiles:**
    ```
    TRANSMIT:           ber_below_tau_transmit closed, bler_below_tau_transmit closed
    TRANSMIT_MONITORED: ber_below_tau_monitored closed, bler_below_tau_monitored closed
    HOLD:               channel_not_catastrophic closed
    ```
    REFUSE is the chain's `Bottom`; it is emitted when no profile is satisfied AND the catastrophic gap is open. The descending search lands at `Unsatisfied` for sub-threshold-but-not-catastrophic cells; HOLD's profile is then the only satisfied one and outcome = HOLD. For catastrophic cells the HOLD profile is also unsatisfied → outcome = `Unsatisfied`. **Role assignment must put `Unsatisfied = Bottom = REFUSE`** so the catastrophic case falls through to REFUSE cleanly.

- **Phase A role table:**
    ```
    Bottom                = REFUSE   (rank 0)
    ExpiryFloor           = REFUSE   (rank 0, collapsed)
    Refused               = REFUSE   (rank 0, collapsed)
    Unsatisfied           = REFUSE   (rank 0, collapsed) ← catastrophic falls through here
    DisallowedUsesCeiling = REFUSE   (rank 0, collapsed)
    BlockerThreshold      = HOLD     (rank 1)
    Top                   = TRANSMIT (rank 3)
    ```

- **Proposed Phase B native chain:** `REFUSE < HOLD < TRANSMIT_MONITORED < TRANSMIT_DATA < TRANSMIT_CRITICAL`. Five levels. Same shape — TRANSMIT splits into DATA / CRITICAL with their own τ pairs (per `compiler_blind.py`'s docstring). The catastrophic gap and role table carry over unchanged; only the higher-τ profiles differ.

- **Files to rewrite:** `compiler_turbo.py`, `compiler_blind.py`, `sweep_turbo.py`, `audit_3gpp.py`, `sensitivity_bler.py`, `ber_bler_curves.py`, `experiment_a_stability.py`. This is the **highest-value rewrite** because it eliminates the reimplemented compiler entirely.

- **Caveat:** Threshold-scan logic in the original is computed per (SNR, level) cell. Translating to gap-statuses-per-cell requires constructing a fresh `ProofContext` per cell. The original is a tight numerical loop; the rewrite uses the compiler at each cell. This is a **performance regression** of unknown magnitude. Acceptance test must include "sweep completes in <5× original time" or we accept a slowdown as the cost of using the real library.

- **Verification must check catastrophic-cell classification, not just τ recovery.** The recovered τ thresholds (the ±0.05 dB check in §10) can be right while the failure-side classification is wrong — an emit matrix that collapsed REFUSE and HOLD into one bucket would still recover τ correctly. The acceptance test in §10 below extends to: for every (SNR, ber, bler) cell where the original `emit()` returned REFUSE, the rewritten emit must also return REFUSE; same for HOLD. The cell-by-cell golden is the authoritative check.

---

## 3. Phase 1: Python binding for `PermissionChain` (binding-only)

The Rust core already exposes `PermissionChain`, `ChainRole` (seven variants — see §0.1), `ChainHash`, `ChainRegistry` trait, `InMemoryChainRegistry`, `verify_published`, and `compile_with_chain`. **Phase 1 adds the PyO3 surface for the existing core types. It does not add any new core API.** See §0.2 for why this is binding-only.

If anything in §3.1 below looks like a new type, it isn't — it's a PyO3 `#[pyclass]` wrapping the existing Rust struct/trait of the same name.

### 3.1 New Python types

```python
# After this phase, in noethers_turnstile:

class ChainRole:
    """Structural anchors a chain must declare. Class attributes."""
    Bottom: ChainRole
    ExpiryFloor: ChainRole
    Refused: ChainRole
    Unsatisfied: ChainRole
    DisallowedUsesCeiling: ChainRole
    BlockerThreshold: ChainRole
    Top: ChainRole

class PermissionChain:
    """Validated permission chain. Construct via `PermissionChain.new(...)`."""

    @staticmethod
    def new(levels: list[str], roles: dict[ChainRole, int]) -> PermissionChain: ...

    @staticmethod
    def default_chain() -> PermissionChain: ...

    def role(self, role: ChainRole) -> Permission: ...
    def parse(self, name: str) -> Permission | None: ...
    def rank(self, p: Permission) -> int | None: ...
    def meet(self, a: Permission, b: Permission) -> Permission: ...
    def descending(self) -> list[Permission]: ...
    def ascending(self) -> list[Permission]: ...
    def contains(self, p: Permission) -> bool: ...
    def __len__(self) -> int: ...
    def __eq__(self, other) -> bool: ...
    def chain_hash(self) -> str: ...  # hex string

class ChainHash:
    """32-byte SHA-256 of a chain. Wraps as hex string."""
    @staticmethod
    def from_hex(s: str) -> ChainHash: ...
    def __str__(self) -> str: ...
    def __eq__(self, other) -> bool: ...

class InMemoryChainRegistry:
    def __init__(self) -> None: ...
    def publish(self, chain: PermissionChain) -> ChainHash: ...
    def lookup(self, hash: ChainHash) -> PermissionChain | None: ...

def verify_published(judgment: Judgment, registry: InMemoryChainRegistry) -> None:
    """Raises AuditError if the judgment's chain is not published."""

# Compile API:
def compile(ctx: ProofContext, chain: PermissionChain | None = None) -> Judgment: ...
def compose(g1: ProofContext, g2: ProofContext, chain: PermissionChain | None = None) -> ProofContext: ...
```

### 3.2 Backwards compatibility

- `t.compile(ctx)` (no `chain=` kwarg) is unchanged: uses the default chain, stamps `chain_hash` to the default's hash.
- `t.Permission.DIA` etc. still work (default chain accessors).
- `t.Permission.ALR` etc. still produce the same `Permission` object as before.
- The wire format for `ProofContext` is unchanged.

### 3.3 Implementation notes

- The PyO3 binding goes in `noethers-turnstile-py/src/lib.rs`. About 200 lines of additions.
- `ChainRole` is exposed as a `#[pyclass]` with `#[classattr]` for each variant (mirrors the existing `NegativeControlStatus` pattern).
- `PermissionChain::new` from Python takes `list[str]` and `dict[ChainRole, int]`. Dict keys are `ChainRole` class-attribute objects (e.g. `ChainRole.Bottom`), not strings. The PyO3 binding accepts the `PyChainRole` wrapper and maps to the Rust enum internally. **Reason:** matches the §3.1 type annotation, lets static type-checkers verify role names at authoring time (a typo'd `ChainRole.Bttom` is a `NameError` at lint, while a typo'd `"Bttom"` would be a runtime `MissingRole`), and is consistent with how `ChainRole.Top` is used as a Python value in §3.4 tests and §4.1's rewrite template. Earlier drafts considered a `dict[str, int]` form but it loses authoring-time validation; rejected.
- `ChainHash` is exposed as an opaque wrapper around the 64-char hex string. Equality and hex round-trip work as expected.
- `compile_with_chain` becomes the implementation of the new `compile` when `chain=` is supplied; the existing `compile_static` from the binding becomes a thin wrapper.

### 3.4 Tests

A new pytest file `python/tests/test_py009_chain_parameterization.py` covers:
- Constructing a 5-level chain from Python; verifying `chain.role(ChainRole.Top)` returns the expected name.
- Constructing an invalid chain (too few levels, bad role binding) → raises a Python exception.
- `compile(ctx, chain=custom)` returns a judgment whose `chain_hash` matches `custom.chain_hash()`.
- `expected_chain_hash` pinning: a context pinned to chain X compiled with chain Y → `MalformedContext`.
- `compose(g1, g2, chain=custom)` is non-promoting.
- `InMemoryChainRegistry` smoke test: empty registry rejects, populated accepts.

---

## 4. Phase 2: Rewrite domain examples to use native chains

For each example in §2.2, the rewrite has the same shape. I document it generically here and call out per-example specifics in §4.3.

### 4.1 Rewrite pattern

**Before:**
```python
import noethers_turnstile as t

PERM_LOW    = t.Permission.DIA   # OPERATIONAL_NAME_LOW
PERM_HIGH   = t.Permission.ALR   # OPERATIONAL_NAME_HIGH

profiles = [t.Profile(PERM_LOW, [...]), t.Profile(PERM_HIGH, [...])]
ctx = t.ProofContext(..., profiles=profiles)
judgment = t.compile(ctx)
print(judgment.permission_str(rt))  # prints "DIA" or "ALR"
```

**After:**
```python
import noethers_turnstile as t
from noethers_turnstile import PermissionChain, ChainRole

# Domain chain — declared once at module top.
_CHAIN = PermissionChain.new(
    levels=["REFUSE", "OPERATIONAL_NAME_LOW", "OPERATIONAL_NAME_HIGH"],
    roles={
        ChainRole.Bottom: 0,
        ChainRole.ExpiryFloor: 0,
        ChainRole.Refused: 0,
        ChainRole.Unsatisfied: 0,
        ChainRole.DisallowedUsesCeiling: 0,
        ChainRole.BlockerThreshold: 1,
        ChainRole.Top: 2,
    },
)

PERM_LOW    = _CHAIN.parse("OPERATIONAL_NAME_LOW")
PERM_HIGH   = _CHAIN.parse("OPERATIONAL_NAME_HIGH")

profiles = [t.Profile(PERM_LOW, [...]), t.Profile(PERM_HIGH, [...])]
ctx = t.ProofContext(..., profiles=profiles)
judgment = t.compile(ctx, chain=_CHAIN)
print(judgment.permission_str(rt))  # prints "OPERATIONAL_NAME_LOW" or "OPERATIONAL_NAME_HIGH"
```

The key shifts:
1. The chain is a first-class object, constructed once and shared.
2. `Permission` objects are obtained via `_CHAIN.parse("NAME")`, not `t.Permission.DIA`.
3. `compile(ctx, chain=_CHAIN)` is the actual call.
4. The string output is now the domain name — no translation comment.

### 4.2 Test/oracle migration

Every example's tests/oracles include assertions like `assert permission == t.Permission.REV`. Those need to become `assert permission.as_str() == "LAND_MANUAL"` (or whatever the new name is). Same goes for the case-library files (`cases.py` in credit/EPIC) that hold `(case_id, expected_permission)` rows.

### 4.3 Per-example specifics

**ILS** — The 5-level chain is already documented in `profiles.py`'s docstring; the rewrite just turns the docstring into code. `faa_comparison.py` needs updating to read the new names; an explicit mapping table from native level → FAA category is added to `faa_comparison.py` (this is *legitimate* translation, not a workaround — the FAA comparison is a deliberate cross-reference, not an internal substitution).

**Credit** — Profile builder in `experiment/profile.py` becomes parametric on the chain. The case library in `experiment/cases.py` continues to use the old strings; the case-runner translates one final time when comparing emit to expected (until the case library is rewritten too, which is mechanical).

**EPIC** — Same shape as credit but ~30 files. The compiler bridge in `experiment/compiler.py` and `acs/compiler.py` are the load-bearing spots; everything else propagates from there. **§6 marks EPIC as optional / deferred.** I propose ILS + credit + forecast_value + inference/turbo in this commit, EPIC + conservation in a follow-up.

**Conservation** — All 11 run scripts share the paper-5-level chain. Factor it to a single `examples/conservation/chain.py` that exports `paper_5_level()`. Each run script imports and uses it. The level names are `REF/DIA/REV/AEX/ALR` — same as default chain — but the chain object is now author-declared, not borrowed from the library default. **This is a deliberate semantic shift:** the paper's conservation experiments don't operate on the default 12-level chain; they operate on the paper's abbreviated chain.

**Forecast value** — `domain.py` is the load-bearing file. Five new level names, one chain constructor, and the AEX-disjunction encoding. The disjunction is implemented by **two profiles binding the same level** (`ACT_ON_PARTIAL_EVIDENCE`) with disjoint gap requirements — `AEX_dur` requires duration bounded; `AEX_vul` requires vulnerability bounded.

**Library change blocker.** The current `validate_context` rejects duplicate-permission profiles (`noethers-turnstile-core/src/compiler.rs:118-127`: "Duplicate permission levels in profiles"). Three options to resolve:

(a) **Relax `validate_context` to permit multiple profiles at the same level**, with `Any(profile_1, profile_2)` disjunction semantics (the descending search returns the strongest *satisfied* profile, so ties on satisfaction emit the shared level — well-defined). Small library change.

(b) **Extend `GapRequirement` with a disjunctive variant** (e.g. `AnyOf(Vec<GapRequirement>)`). Larger library change but more expressive than (a); the disjunction lives in the requirement itself rather than across profiles, and `validate_context`'s duplicate check is preserved as-is.

(b) is a core library change, not an example detail. It goes through the same representation-vs-enforcement discipline as the chain refactor: its own PR, its own validator rule (every requirement inside `AnyOf` must reference an existing gap; `AnyOf` is satisfied iff at least one arm is satisfied), its own proptest (descending search emits the strongest *p* whose profile is satisfied, which now extends to "some `AnyOf` arm satisfied"), and **an explicit `DerivationStep` contract**:

> When a profile is satisfied via an `AnyOf` requirement, the `DerivationStep` for that profile records which specific arm fired. The audit trail thus contains, for `ACT_ON_PARTIAL_EVIDENCE` in forecast_value, "satisfied by `duration_bounded`" or "satisfied by `vulnerability_bounded`" — never the bare profile name with no disjunct attribution. This is the whole point of choosing (b) over (c); if the implementation does not record the arm, the spec has paid for granularity it didn't bank.

The Phase 1b PR's acceptance test is a unit test that constructs an `AnyOf` with two arms, satisfies only one, compiles, and asserts the derivation contains the satisfied-arm's gap_id by name. Without that test passing, Phase 2C must fall back to (c).

(c) **Synthesize the disjunction in domain code** before constructing the context: a single fused gap `duration_or_vulnerability_bounded` whose status is the max of duration and vulnerability statuses, computed by `domain.py` and stamped into the context. No library change.

**Recommendation: (b), on engineering grounds.** Under (c), the disjunction is computed *upstream* of the compiler — domain code fuses the two gap statuses before constructing the context — so the `DerivationStep` records only the fused gap. An auditor reading the derivation cannot tell whether `ACT_ON_PARTIAL_EVIDENCE` was licensed by duration evidence or by vulnerability evidence; that information was erased before the compiler saw it.

The library's whole point is that the derivation is the auditable artifact. A representation that cannot distinguish which of two distinct evidence axes licensed an action contradicts that purpose, regardless of whether any specific paper asks for the distinction. (b) preserves the separation: the satisfied `GapRequirement::AnyOf(...)` disjunct is identifiable from the audit trail, and the derivation records which one fired. (b) also generalizes — every future example that wants disjunctive evidence requirements (e.g., "either FAA Part 91 or Part 121 authorization") inherits the feature without further library work.

**Honest scope note.** An earlier draft of this paragraph argued (b) over (c) by citing "the paper's frost-protection taxonomy lists duration and vulnerability as separate gaps." That claim was unsupported — the pivot paper (v5) contains no frost-protection experiment, no duration_gap or vulnerability_gap, only a related-work mention of cost-loss decision theory (v5 lines 34, 637). The forecast_value example was constructed to dramatize the cost-loss separation that v5 argues *abstractly*, not to instantiate a taxonomy v5 describes. The (b)-over-(c) call therefore stands on engineering grounds alone — auditability of disjunctive evidence requirements — not on paper fidelity. The forecast_value example itself, in `examples/forecast_value/domain.py`, is the source of the duration/vulnerability gap structure.

**Status:** (b) is a justified library proposal on auditability grounds. Phase 2C depends on it. Until (b) lands, the forecast_value rewrite is blocked. (c) remains the documented fallback if (b) doesn't ship; under (c), the rewrite docstring records that the derivation cannot recover the licensing disjunct.

(a) is rejected: collapsing duplicate-profile detection makes it harder to catch real authoring errors (a user typoing a profile level and getting it silently merged with another).

**Inference register-2 turbo** — This is the biggest content shift, even though the file count is small. The existing `compiler_turbo.py` and `compiler_blind.py` are *replaced wholesale* with thin shims that build profiles + call `compile_with_chain`. The threshold tables (`TAU_BER`, `TAU_BLER`) move into the profile construction — each level requires `ber_exceeds_threshold_τ` and `bler_exceeds_threshold_τ` gaps for its specific τ. **§5 documents the threshold-encoding choice in detail because there are two valid encodings.**

---

## 5. Detail: encoding numerical thresholds as gap statuses

This affects turbo and forecast_value primarily. The original code uses:

```python
def emit(snr_db, ber, bler):
    if ber > TAU_BER[TRANSMIT_MONITORED] or bler > TAU_BLER[TRANSMIT_MONITORED]:
        return REFUSE if (ber > 1.0 or bler > 1.0) else HOLD
    if ber > TAU_BER[TRANSMIT] or bler > TAU_BLER[TRANSMIT]:
        return TRANSMIT_MONITORED
    return TRANSMIT
```

This is exactly the kind of in-code threshold logic the library was designed to replace. Two encodings to choose from:

### Encoding A — one gap per threshold (plus catastrophic gap)

A gap `ber_below_τ_TRANSMIT` is `closed` when `ber ≤ τ_BER[TRANSMIT]`, `open` otherwise. Similarly for `bler_below_τ_TRANSMIT`, `ber_below_τ_TRANSMIT_MONITORED`, etc. **Plus a catastrophic gap** `channel_not_catastrophic` closed iff `ber ≤ 1.0 AND bler ≤ 1.0`, used to separate REFUSE (channel unusable) from HOLD (channel exists but below monitored threshold). See §2.2.6 for why this gap is required.

Profiles for Phase A (4-level):

```python
Profile(TRANSMIT, [
    GapRequirement("ber_below_tau_transmit", "closed"),
    GapRequirement("bler_below_tau_transmit", "closed"),
])
Profile(TRANSMIT_MONITORED, [
    GapRequirement("ber_below_tau_monitored", "closed"),
    GapRequirement("bler_below_tau_monitored", "closed"),
])
Profile(HOLD, [
    GapRequirement("channel_not_catastrophic", "closed"),
])
# REFUSE = chain.role(Bottom). Emitted when no profile is satisfied (i.e.
# channel_not_catastrophic is open) AND structural fallthrough lands at
# Unsatisfied (which is mapped to Bottom for this chain).
```

5 gap types total for the 4-level Phase A chain (4 τ-pair gaps + 1 catastrophic gap). Each ProofContext at one (SNR, ber, bler) point sets the right gaps to closed/open. **Maps cleanly to the compiler's structural semantics.** Recommended.

### Encoding B — one gap per metric, status encodes bound

A gap `ber` is `bounded` (with `Bound::numeric(τ_BER[level])`) for each level that the BER passes, `open` otherwise. The compiler's `BoundedRequired` requirement gates each profile. Requires the compiler to understand numeric bound comparisons.

**The compiler does not currently compare bound values; `BoundedRequired` is satisfied by any `Bounded` status regardless of the numeric value.** Encoding B would require extending the compiler. Out of scope. Pick A.

---

## 6. Phase 3: Rust benchmark

`noethers-turnstile-core/benches/bench_compile.rs` currently uses `Permission::DIA` (which no longer compiles after the refactor). Two changes:

1. Update to use `default_levels::DIA()` (the canonical accessor — `Permission::DIA()` also exists as an associated fn defined in `default_levels.rs`, but library-internal code should prefer the direct module path so the dependency on `default_levels` is explicit). Both return the same `Permission` value; benches live outside `src/` so the CI Gate 1 grep does not apply.
2. Add a new benchmark variant `bench_compile_with_custom_chain` that constructs a 5-level domain chain and measures compile time against it. **Acceptance:** custom chain compile must be within 1.5× of default-chain compile time. If slower, it's a perf bug in the refactor (probably in `chain.meet()` going through HashMap lookups instead of direct enum compare).

---

## 7. Phase 4: Verification protocol

For each rewritten example, we run the example and compare outputs against a pre-rewrite golden through an **explicit declared bijection**, not through rank ordering.

### 7.1 Why rank ordering is insufficient

An earlier draft of this spec proposed verifying that "the rewrite emits the level at the same rank-from-top as the old emit." That fails the moment the new chain has a different cardinality from the old one — which is the case for every example that adds a level. Concrete failure:

- Old ILS chain (default-chain translation): four operational levels DIA<REV<AEX<ALR plus default-chain bottom OOC.
- New ILS chain (this spec, §2.2.1): six levels REFUSE_APPROACH<CONTINUE_APPROACH<DESCEND_TO_DH<LAND_MANUAL<LAND_ASSISTED<LAND_ZERO_ZERO.

`LAND_MANUAL` is the new chain's rank-3-from-top. The old emit equivalent (`REV`) was rank-1-from-top among the operational levels. Rank-from-top does not preserve. The earlier draft's claim that "LAND_MANUAL is the second-highest level in the new chain" was wrong on its face — LAND_MANUAL is third from the top.

The verification has to use **the declared old→new bijection**, exactly the translation table that already lives in each example's profiles.py docstring.

### 7.2 Declared bijection per example

For each Class T example, the rewrite includes a translation table that records what each old default-chain level maps to in the new domain chain. The table is the source of truth for the verification; if a row is missing, the verification can't run on that row.

- **ILS** (`examples/ils/profiles.py`):
    ```
    DIA  ↔ DESCEND_TO_DH
    REV  ↔ LAND_MANUAL
    AEX  ↔ LAND_ASSISTED
    ALR  ↔ LAND_ZERO_ZERO
    ```
    plus refusal levels — see "Refusal-side rows below" — and the §2.2.1 role table line `Unsatisfied = CONTINUE_APPROACH`. Both are pinned by what the golden capture in §7.3 actually contains, not asserted in advance.

    **Refusal-side rows in tension with the role table — must be pinned by the golden, not asserted.** §2.2.1's proposed role table for ILS sets `Unsatisfied = CONTINUE_APPROACH` (rank 1, not Bottom). If the pre-rewrite ILS code ever lands at the default-chain `UNS` outcome — which it does whenever a profile is declared but no profile's gaps are satisfied — that `UNS` emit appears in the golden, and the bijection needs a `UNS ↔ CONTINUE_APPROACH` row. The reviewer's note is exactly right: an asserted "no equivalent" claim is unverified.

    Likewise the pre-rewrite ILS code may emit `REF` (the structural-blocker target — fires on PROVENANCE_MISMATCH or DEAD_CREDENTIAL tokens when outcome is below the default chain's DIA threshold). If any test fixture in ILS exercises that branch, the golden contains a `REF` row. The new chain collapses ExpiryFloor / Refused / DisallowedUsesCeiling to `REFUSE_APPROACH` and keeps `Unsatisfied = CONTINUE_APPROACH`; under that mapping `REF ↔ REFUSE_APPROACH` (the refusal-target collapse) is the right bijection row.

    **Step 0 (golden capture) is the authority.** Before writing any bijection row, the implementer grep'd the captured `examples/ils/...` golden JSON for the set of distinct old-chain emit values that actually appear. The bijection then contains exactly one row per distinct value, none more, none fewer. Candidate rows the implementer should expect to see in the golden — based on reading the ILS code — are:
    ```
    OOC  ↔ REFUSE_APPROACH    (Membership::OutOfClassExact → chain.role(Bottom))
    REF  ↔ REFUSE_APPROACH    (structural blocker → role(Refused), collapsed to Bottom)
    UNS  ↔ CONTINUE_APPROACH  (profile defined, no gap satisfied → role(Unsatisfied))
    DIA  ↔ DESCEND_TO_DH
    REV  ↔ LAND_MANUAL
    AEX  ↔ LAND_ASSISTED
    ALR  ↔ LAND_ZERO_ZERO
    ```
    If any of OOC/REF/UNS does NOT appear in the golden, that row is omitted. If a level the implementer didn't predict DOES appear (e.g. `EXP` from an expiry test), the bijection must add a row for it; document the call in the rewrite commit message. The "no old equivalent for CONTINUE_APPROACH" line in an earlier draft was wrong: if the old code ever emitted `UNS`, that's the equivalent. The bijection is potentially a folding (multiple old values → one new value); folding is fine, the lookup just must be total over the golden's actual distinct values.

- **Credit** (`examples/credit/experiment/profile.py`):
    ```
    OOC  ↔ REFUSE
    DIA  ↔ MODEL_EXISTS
    REV  ↔ EXPERT_REVIEW
    AEX  ↔ EXPERIMENT_AUTHORIZED
    ALR  ↔ LIMITED_ROLLOUT
    AAA  ↔ FULL_AUTHORITY
    ```

- **Forecast value** (`examples/forecast_value/domain.py`):
    ```
    REF  ↔ NO_ACTION
    DIA  ↔ REPORT_EXCEEDANCE
    REV  ↔ BOUND_EXCEEDANCE
    AEX  ↔ ACT_ON_PARTIAL_EVIDENCE
    ALR  ↔ ACT_ON_FULL_EVIDENCE
    ```

- **Conservation** (closed per §11 Q3 Option A):
    ```
    OOC ↔ REF   (membership-failure folding — old default-chain emit collapsed to the paper-5 chain's bottom)
    REF ↔ REF
    DIA ↔ DIA
    REV ↔ REV
    AEX ↔ AEX
    ALR ↔ ALR
    ```
    Two deltas, not one: (i) the chain object is author-declared (the paper-5-level chain from `examples/conservation/chain.py`) rather than borrowed from the default 12, and (ii) any conservation cell that previously emitted `OOC` under the default chain now emits `REF` under the paper-5-level chain — a real behavioral fold for membership-failure cells, even though it's results-neutral for the canonical 16-case matrix (which the paper itself reports as not reaching the floor anyway; v5 lines 445–452). Verification is bijection-mapped per §7.4 #2, not byte-for-byte: any golden row with old-emit `OOC` is asserted equal to new-emit `REF` under the bijection. **Byte-for-byte equality is the correct test only as a degenerate case when the golden empirically contains no `OOC` row** (Phase 0 capture will confirm whether that holds); the bijection-mapped test is correct either way and is what §10's acceptance criterion already says.

- **Turbo Phase A** (`examples/inference/register2/turbo/compiler_turbo.py`):
    ```
    Integer-coded REFUSE              ↔ chain.parse("REFUSE")
    Integer-coded HOLD                ↔ chain.parse("HOLD")
    Integer-coded TRANSMIT_MONITORED  ↔ chain.parse("TRANSMIT_MONITORED")
    Integer-coded TRANSMIT            ↔ chain.parse("TRANSMIT")
    ```
    (Levels unchanged in name; only the implementation changes from integer-coded to library-compiled. The cell-by-cell golden in §2.2.6 still applies.)

- **Turbo Phase B** (`examples/inference/register2/turbo/compiler_blind.py`): same identity bijection; five levels REFUSE..TRANSMIT_CRITICAL preserved.

### 7.3 Golden output capture (Step 0)

Before touching any example file, run each example on the current code and capture its emit table to `docs/specs/native_chains_golden/<example_name>.json`. For Class T examples the JSON records old-chain emit per case/cell; for Class R examples it records the integer-coded emit per (SNR, ber, bler) cell.

The schema for each row:
```json
{
  "case_or_cell_id": "...",
  "old_chain_emit": "REV",
  "key_inputs": { ... }
}
```

### 7.4 Post-rewrite assertion

For each example, after the rewrite a new test (or extended existing test) loads the golden, loads the declared bijection from the example's profiles.py docstring (or a `BIJECTION` dict in the rewrite), and asserts:

1. The example runs without error.
2. For every row in the golden, `bijection[old_chain_emit] == new_chain_emit(same_inputs)`. **Cell-by-cell, not rank-by-rank.**
3. The judgment's `chain_hash` matches `chain.chain_hash()` for the new chain.
4. For turbo: §2.2.6's REFUSE/HOLD-by-cell assertion is satisfied (the catastrophic fork is preserved).
5. For turbo audit: the recovered 3GPP τ thresholds are within ±0.1 dB of pre-rewrite recovery. This is a sanity check on top of the cell-by-cell, not a substitute — see §2.2.6 "Verification must check catastrophic-cell classification, not just τ recovery."
6. **Collapse invariant test (dual of AM-01, per §2.0).** For each chain that maps `DisallowedUsesCeiling` to `Bottom`, the test crate constructs a representative context whose canonical run emits a non-Bottom level (e.g., ILS at DH=200ft/RVR=2000ft emits `LAND_MANUAL`). The test asserts the emit is NOT `chain.role(Bottom)`. This proves the §0.4 guard fired correctly (i.e., `disallowed_uses` was empty, so the ceiling step was skipped). If a future fixture silently adds `disallowed_uses=["something"]`, this test fails immediately rather than silently flooring every cell to REFUSE/REF/NO_ACTION.

### 7.5 What NOT to verify

- **Rank-order equivalence.** Forbidden (see §7.1). Only the declared bijection is authoritative.
- Bit-for-bit string equality of output JSON. The level names change deliberately — that's the point. Only the bijection-mapped emit must match.
- Performance regressions below 5× of original (turbo) or 2× (others). Above-threshold slowdowns are flagged but non-blocking.

---

## 8. What is NOT in scope

- **EPIC rewrite.** Deferred to a follow-up commit. EPIC is ~30 files; doing it in the same commit as ILS + credit + forecast + turbo + conservation makes the diff unreviewable. EPIC continues using its current default-chain translation; the docstring `t.Permission.ALR — full authority (ceiling not used)` stays, and tests continue asserting `t.Permission.REV` etc.
- **Renaming `t.Permission.DIA` etc.** They keep working as default-chain accessors. The CI Gate doesn't apply to example code.
- **Removing the `python/noethers_turnstile/__init__.py` re-exports.** Backwards-compatible.
- **Removing the integer-coded chains in `compiler_turbo.py` etc.** Those files get REPLACED (the integer constants disappear), not deprecated.
- **Cross-paper revisions.** The papers reference `DIA/REV/AEX` etc. as if they were operational names. The paper drafts (`docs/papers/*.md`, `docs/pivot/*.md`) need their own pass to refer to native chain names. **Out of scope for this commit;** flag for a follow-up.

---

## 9. Implementation order

The phases run in this order. Each phase ends with a working `cargo test && pytest && cargo bench --no-run` and a meaningful intermediate state.

| # | Phase | Approx LOC | Tests added | Blocked on | Failure mode if skipped |
|---|---|---|---|---|---|
| 0 | Capture golden outputs for ILS, credit, forecast, conservation, turbo | n/a | n/a | — | Can't verify rewrites preserve semantics |
| 1 | Python binding: `PermissionChain`, `ChainRole`, `ChainHash`, `InMemoryChainRegistry`, `verify_published`, `compile(chain=)` | ~250 in PyO3 + ~100 in __init__.py + ~80 new pytest | 8 new pytest | — | Examples can't supply custom chain |
| 1b | **Library proposal: disjunctive `GapRequirement::AnyOf` variant** (forecast_value blocker — Option (b) in §2.2.5) | ~80 in compiler + ~40 new test | 4 new Rust unit tests + 1 new pytest | — | Phase 2C cannot use option (b); falls back to (c) with audit-trail loss |
| 2A | Rewrite ILS to native chain + tests + report | ~100 net | 3 new pytest | §0 golden | n/a |
| 2B | Rewrite credit to native chain + tests + report | ~150 net | 4 new pytest | §0 golden | n/a |
| 2C | Rewrite forecast_value to native chain + tests | ~80 net | 2 new pytest | Phase 1b (or §11 Q5 fallback to (c)) | If skipped, AEX disjunction can't be encoded |
| 2D | Rewrite inference register-2 turbo: replace `compiler_*.py` integer chains with `compile_with_chain` calls; rewrite `audit_3gpp.py` to consume library judgments | ~300 net (largest) | 3 new pytest + cell-by-cell REFUSE/HOLD test (§2.2.6) | §0 golden | n/a |
| 2E | Rewrite conservation to use an explicit paper-N-level chain (factored into `chain.py`) | ~50 net | 1 new pytest | §11 Q3 manuscript decision | Conservation rewrite can't pick chain cardinality |
| 3 | Update Rust benchmark | ~50 net | n/a | — | Benchmarks won't compile |
| 4 | Verification: run each example, compare to golden | n/a | per-example pytest + collapse-invariant test §7.4 #6 | All Phase 2 | n/a |

**Total estimated diff:** ~1100 lines net additions across ~50 files. Comparable to the chain refactor itself in scope; smaller in design complexity (no library API redesign).

**EPIC and the paper drafts are deferred.** Spec §8 documents the cutoff.

---

## 10. Acceptance criteria

- [ ] `pytest python/tests/test_py009_chain_parameterization.py` — 8 new tests pass.
- [ ] `pytest examples/ils/` — ILS runs against the native chain; emits domain-level names; FAA comparison still produces the same threshold table (DH≈197ft, RVR≈1862ft).
- [ ] `pytest examples/credit/` — Credit induction completes; final taxonomy matches the golden; CFPB audit produces the same correspondence partition.
- [ ] `pytest examples/forecast_value/` — `run_all.py` outcome.md text matches the pre-rewrite outcome under the declared bijection (§7.2 forecast_value table).
- [ ] `pytest examples/inference/register2/turbo/` (or equivalent runner) — `audit_3gpp.py` recovers BLER 0.10 and 0.02 thresholds within ±0.05 of the pre-rewrite recovery.
- [ ] `pytest examples/conservation/` — at least the central `run_two_axis_convergence_v2.py` produces a bijection-equivalent matrix to the pre-rewrite output under the declared conservation bijection (§7.2; identity over `REF/DIA/REV/AEX/ALR` plus `OOC ↔ REF` per Q3 Option A).
- [ ] `cargo bench -p noethers-turnstile-core --no-run` — benchmarks compile.
- [ ] No file under `examples/` has the comment `# operational meaning, no [domain] names` or equivalent translation phrase. Replaced by actual domain names.
- [ ] `grep -rE 't\.Permission\.(DIA|REV|AEX|ALR|AAA)' examples/` returns zero hits outside `examples/epic/` (which is deferred) and `examples/conservation/` (which intentionally uses the same names — but now via a chain.parse() call, not the default-chain accessor).
- [ ] No file under `examples/inference/register2/turbo/` defines its own integer permission constants for transmission classes.

---

## 11. Open questions before coding

1. **Are paper-Phase B turbo levels (TRANSMIT_CRITICAL / TRANSMIT_DATA) actually the right native names?** They come from `compiler_blind.py`'s docstring. They're plausible but I'm reading them off the file, not from a 3GPP spec. → **Action: keep as proposed; the paper text uses these names.**

2. **What about `examples/inference/` files OUTSIDE `register2/turbo/`?** There are conftest + named-network tests under `examples/inference/named/`, `examples/inference/ising/`, `examples/inference/uai/`. **None of them import `noethers_turnstile`** (verified by grep). They are pure-pytest unit tests for the inference benchmarks themselves and don't touch the permission chain. → **Out of scope. Confirmed.**

3. **(closed — Option A; the paper had already decided)** **Conservation chain cardinality: five levels, `OOC ↔ REF` in the bijection.** Verified against `docs/pivot/pivot-paper-v5.md`:
    - Line 140 declares the conservation chain as exactly `REF ⪯ DIA ⪯ REV ⪯ AEX ⪯ ALR` (five levels).
    - Line 143 defines REF as "refusal or no authorization" — a definition that already folds membership failure into the bottom level.
    - The string `OOC` appears **zero times** in the paper. The phrase "out of class" appears zero times.
    - The canonical 16-case conservation matrix (lines 445–452) exercises only `DIA ≺ REV ≺ AEX ≺ ALR`. REF appears only in S-REF, a declared targeted control, and in the ILS occlusion figure as the floor.

    Implication: the OOC level appears in the conservation scripts only because they borrowed the **default 12-level** chain (which has OOC as its bottom). On the paper's own 5-level chain, `Membership::OutOfClassExact` emits `chain.role(Bottom) = REF`. The script is what's out of step, not the paper.

    **Decision: Option A.** Conservation chain is five levels, `REF<DIA<REV<AEX<ALR`. The §7.2 bijection becomes `OOC ↔ REF` (the membership-failure folding), identity on the rest. No paper number moves under this choice because nothing in the canonical results emits an OOC-distinct-from-REF cell in the first place. Option B would have *introduced* a membership-vs-refusal distinction the paper deliberately doesn't make and would owe the paper an unjustified extra sentence; rejected.

    **Phase 2E unblocked.** The chain factor module is `examples/conservation/chain.py`, returning the paper-5-level chain.

4. **EPIC is deferred. Does that block any paper deadline?** Worth flagging — the Track A paper (`docs/papers/admissibility_judgement_for_approximate_consequential_systems_v10.md`) cites EPIC as a primary blind-recovery case. If the paper draft refers to `t.Permission.ALR` in figures or appendices, those persist with the OLD level name until the EPIC rewrite ships. → **Action: flag in §8; user decides whether to gate Phase 2 on EPIC inclusion.**

5. **(closed — ≤5× turbo perf regression acceptable.)** Phase 2D replaces a tight per-cell numerical loop with a per-cell `compile_with_chain` call. The slowdown buys real structural validation; turbo is not latency-critical. Acceptance test threshold per §7.5: sweep completes in ≤5× original time; above 5× is flagged but non-blocking.

6. **(closed — ship (b) as Phase 1b, on engineering grounds.)** Forecast value's `ACT_ON_PARTIAL_EVIDENCE` profile is satisfied by "duration bounded OR vulnerability bounded." Option (b) — a new `GapRequirement::AnyOf` variant — ships as Phase 1b. Justification is auditability of disjunctive evidence requirements, not paper fidelity (v5 contains no forecast taxonomy that would have demanded it). **Phase 1b's PR must include the `DerivationStep` arm-attribution unit test described in §2.2.5 (b)**: an `AnyOf` requirement satisfied by exactly one arm must produce a derivation step whose record names the satisfied arm by gap_id. If that test does not pass, Phase 2C must fall back to (c) with the audit-trail loss documented in the rewrite. (a) remains rejected (collapsing duplicate-profile detection hides authoring errors).
