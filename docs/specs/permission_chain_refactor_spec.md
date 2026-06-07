# Spec: Parameterizing the Permission Chain

**Status:** Proposed
**Scope:** `noethers-turnstile-core`, `noethers-turnstile-py`. Tests are NOT refactored — they continue using the default chain.

## 1. Problem

`Permission` is currently a Rust `enum` with twelve hardcoded variants. The compiler's structural rules name specific levels by variant: `OOC` for out-of-class, `EXP` for the expiry floor, `REF` for the structural-blocker meet, `UNS` for "profile defined but unsatisfied", `DIA` as the threshold below which provenance/dead-credential blockers fire, `AAA` as the top of the lattice. The descending search iterates `Permission::descending()` which yields a fixed 12-element sequence.

We want the caller to be able to supply a different chain. The existing 12-level chain becomes the **default**; supplied chains must be **validated** to satisfy the lattice and monotonicity properties the paper relies on.

The hard constraint the user named: **tests** may reference levels by name (`Permission::DIA`, `Permission::EXP`) because tests run against the default. **Library code in `compile`/`compose` must not** — those functions receive their semantic anchors via the chain parameter, not by naming a variant.

## 2. What "permission chain" means in this codebase

The compiler doesn't just need a total order over named levels. It needs **role anchors** — specific levels with specific structural meaning baked into the algorithm:

| Anchor | Variant in default chain | Used where | What breaks without it |
|---|---|---|---|
| `bottom`             | `OOC` | membership ≠ InClass; no profiles defined; compose meet seed | No floor for non-promotion |
| `expiry_floor`       | `EXP` | context expiry already fired; expired-token meet (always as `chain.meet(outcome, expiry_floor)` — see §2.1) | Expiry has no place to land |
| `refused`            | `REF` | provenance-mismatch / dead-credential meet | Structural blockers have no target |
| `unsatisfied`        | `UNS` | descending-search initial value when profiles exist but none satisfied | Loop has no "not-yet-found" sentinel |
| `blocker_threshold`  | `DIA` | guard for the structural-blocker meet (`outcome < threshold`) | Provenance blockers can't decide when to suppress |
| `top`                | `AAA` | `Permission::top()` serde default for unconstrained ceilings | No way to express "no ceiling" |

The chain also supplies the **total order** (descending search iterator, meet=min, GLB) and the **string codec** (`from_str`/`as_str` for serde and Python).

A correct parameterization gives the compiler all of this — order **and** anchors — and validates the supplied bundle.

### 2.1 The all-meets discipline (load-bearing)

**Every named structural operation in `compile` and `compose` is a `chain.meet`, never a positional clamp.** This is the single rule that makes non-promotion a theorem over the compiler rather than a side-effect of placement.

In the original enum-based implementation, EXP being near the bottom of the chain made "expired-token outcome floors to EXP" trivially non-promoting: even if the outcome had somehow already landed below EXP, replacing it with EXP would have promoted. The default chain hid this by placing EXP at rank 1.

Under parameterization, that hiding is gone. A chain author may legally place `ExpiryFloor` mid-chain (L7 only requires it sits strictly between `Bottom` and `BlockerThreshold`). If the expiry step were implemented as a positional clamp — "outcome := role(ExpiryFloor)" — then an outcome that had already been floored below the expiry floor by some earlier meet would be **raised** by the expiry step. That is exactly the "authorization created by representation" failure the paper exists to prevent, reproduced at the compiler step boundary.

The fix is structural, not numerical: every step that lowers the outcome must be expressed as

```rust
outcome = chain.meet(outcome, chain.role(SomeRole));
```

`meet` is `min` over the chain's order. `min` cannot promote, by construction. This is the whole point of computing floors as meets rather than assignments.

The non-promotion theorem then has a one-line proof: the outcome variable is initialized once and only ever assigned the result of `chain.meet(outcome, ...)`. Composition over `chain.meet` is monotone non-increasing. QED.

L7/L8/L9 (§3.2) do **not** carry the non-promotion guarantee. They guarantee something weaker and complementary: **reachability**. The meet target sits below the blocker threshold so that the meet, when triggered, lands the outcome in a region where downstream steps still apply — i.e. the structural blockers don't become unreachable depending on what the previous step produced. Without L7–L9 the compiler would still be sound; it would just be unable to reach `REF` / `EXP` / `UNS` outcomes from above-threshold starting points without going through them.

Concretely:
- L7 says `ExpiryFloor < BlockerThreshold` so that when expiry fires from an above-threshold outcome, the meet lands below the threshold and structural blockers can subsequently fire if applicable.
- L8 says `Refused < BlockerThreshold` so that the structural-blocker meet from an at-threshold outcome lands strictly below it (otherwise the meet is a no-op and the blocker is silently dropped).
- L9 says `Unsatisfied < BlockerThreshold` so that the descending-search initial outcome triggers structural blockers when they apply.

In each case, the L-rule guarantees **reachability**, not **safety**. Safety comes from the all-meets discipline. The L7 *Why* column in §3.2 is rewritten in those terms below.

## 3. Design

### 3.1 New type: `PermissionChain`

A `PermissionChain` is a validated, ordered list of named levels plus a mapping from role → level. It is constructed by a constructor that validates the lattice properties; raw construction is not exposed.

```rust
// noethers-turnstile-core/src/permission.rs

/// A named permission level. Identity is the (case-sensitive) name string.
///
/// Display, serde, comparison-for-equality all key off `name`. Order in the
/// chain is NOT carried by the level itself — it's carried by the chain that
/// contains it. A level is only meaningfully comparable through its chain.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Permission {
    name: String,
}

impl Permission {
    pub fn new<S: Into<String>>(name: S) -> Self { ... }
    pub fn as_str(&self) -> &str { &self.name }
}

/// Roles the compiler must be able to address by name.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ChainRole {
    Bottom,
    ExpiryFloor,
    Refused,
    Unsatisfied,
    BlockerThreshold,
    Top,
}

/// A validated permission chain.
///
/// Construction goes through [`PermissionChain::new`] which enforces the
/// lattice and monotonicity properties (§3.2). Once constructed, the chain
/// is immutable. The compiler reads the total order and the role anchors
/// from it; it never names a level literally.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PermissionChain {
    /// Levels in ascending order: levels[0] is bottom, levels.last() is top.
    levels: Vec<Permission>,
    /// Role → index in `levels`.
    roles: HashMap<ChainRole, usize>,
    /// name → index in `levels`. Built once at construction for O(1) lookups.
    name_index: HashMap<String, usize>,
}
```

### 3.2 Validation (`PermissionChain::new`)

This is property (2) the user requested. The constructor returns `Err(ChainError)` if any rule fails.

**What these rules are and are not.** L1–L9 are **chain-local well-formedness predicates**: each one is checkable on a single chain in isolation. They are **structural preconditions** for the compiler. They are NOT the four paper guarantees themselves. The paper guarantees — non-promotion, provenance, expiry-at-boundary, evidence monotonicity — are **compiler invariants** that follow from L1–L9 *together with* the all-meets discipline of §2.1. The validator does not (and cannot) check the guarantees directly; it checks that the chain is shaped so that the compiler, written under the all-meets discipline, satisfies them. The guarantees are verified by proptest (§3.8, §7.3) over the cross-product of valid chains and contexts.

This split is why there is no "monotonicity rule" or "non-promotion rule" in the table below: those are not chain-local. The closest thing is the all-meets discipline of §2.1, which is a discipline on `compile` source code, not on chain values.

| # | Rule | Why (what this rule *actually* guarantees) |
|---|---|---|
| L1 | `levels.len() ≥ 2` and `≤ MAX_LEVELS` | Need at least bottom + top. `MAX_LEVELS` is set to 256 (`u8::MAX` — see Q8 in §6). Not load-bearing for any algorithm; exists to prevent pathological chains from blowing up `HashMap`/`Vec` allocations and to keep proptest spaces tractable. |
| L2 | All names match the conservative charset `[A-Za-z0-9_][A-Za-z0-9_-]*`, length 1–64 bytes | Names are used as map keys, serde output, and Python `str`; downstream codecs key off byte-exact equality. Allowing arbitrary Unicode (combining characters, non-NFC forms, RTL marks) creates a footgun where two visually identical names compare unequal — and a different footgun where two visually distinct names compare equal under some normalization. The conservative charset eliminates both. Authors who need richer names can encode them externally and use the chain as an indirection layer. |
| L3 | Names are unique (case-sensitive) | Total order over a set requires distinct elements. |
| L4 | All six `ChainRole`s are mapped to some index in `levels` | Compiler cannot run without all role anchors. |
| L5 | `roles[Bottom] == 0` | Bottom must be the bottom. |
| L6 | `roles[Top] == levels.len() - 1` | Top must be the top. |
| L7 | `roles[ExpiryFloor] < roles[BlockerThreshold]` (non-strict allowed at `Bottom`: see Q5) | **Reachability** of the expiry floor: when the expiry meet fires from any outcome at or above `BlockerThreshold`, the resulting outcome lands strictly below `BlockerThreshold`. Without L7 the expiry meet could be a no-op from above-threshold outcomes and the EXP floor would be silently dropped. L7 does NOT guarantee non-promotion of the expiry step — that comes from §2.1. |
| L8 | `roles[Refused] < roles[BlockerThreshold]` | **Reachability** of the structural-blocker meet: when the blocker fires from an outcome at the threshold, the meet target sits strictly below it so the meet is not a no-op. Non-promotion is guaranteed by §2.1, not by this rule. |
| L9 | `roles[Unsatisfied] < roles[BlockerThreshold]` | **Reachability**: the descending-search initial outcome sits in a region where structural blockers can fire if applicable. Without L9 the search could initialize at-or-above the threshold and the "no profile satisfied + blocker present" branch would silently skip the blocker. |

Notes:
- L7–L9 are **reachability** rules, not safety rules. Non-promotion of every compiler step is delivered by §2.1's all-meets discipline; L7–L9 ensure the meets land in regions where downstream steps remain applicable.
- We deliberately **do not** require that `Refused` sit above `ExpiryFloor` — a chain author may choose either ordering. The compiler does not depend on REF vs EXP order.
- We deliberately **do not** require fixed names for non-default chains — only that roles are assigned and inequalities hold.
- **Note on L10:** an earlier draft of this spec listed an "L10: the default chain has the historical names and roles" rule. That rule has been removed from the validator. A constructor running on a single chain in isolation cannot check that *it* is *the* unique default; that's not a chain-local predicate. The intended back-compat assertion lives in §3.8 instead, as a single equality test against a frozen reference: `assert!(default_chain() == frozen_default_v1())`.

`ChainError` is a new variant of `TurnstileError` with concrete subcases: `TooFewLevels`, `TooManyLevels`, `DuplicateName(String)`, `MissingRole(ChainRole)`, `RoleOrderViolation { role: ChainRole, index: usize, threshold_index: usize }`, `InvalidName { name: String, reason: NameRejectionReason }` (with `reason` distinguishing empty / charset-violation / length-exceeded), and `ForeignLevel { name: String }`.

### 3.3 Comparison and meet are chain-relative; chains have a content hash

```rust
impl PermissionChain {
    pub fn default_chain() -> &'static PermissionChain { ... } // OOC..AAA, lazy_static

    pub fn role(&self, role: ChainRole) -> &Permission { ... }
    pub fn rank(&self, p: &Permission) -> Option<u8> { ... }     // None if foreign
    pub fn cmp(&self, a: &Permission, b: &Permission) -> Option<Ordering> { ... }
    pub fn meet(&self, a: &Permission, b: &Permission) -> Result<Permission, ChainError> { ... }
    pub fn descending(&self) -> impl Iterator<Item = &Permission> { ... }
    pub fn contains(&self, p: &Permission) -> bool { ... }

    /// SHA-256 over a canonical encoding of `(ordered names, role bindings)`.
    /// Two chains have the same hash iff they have the same ordered list of
    /// level names AND the same role→index mapping. Name-equality is not
    /// enough; order and roles also have to match.
    pub fn chain_hash(&self) -> ChainHash { ... }
}

/// 32-byte SHA-256 digest. `Display` emits hex, `Serialize` emits hex.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct ChainHash([u8; 32]);
```

**Chain identity, not just name identity.** A `Permission` value compared through chain X has no meaning under chain Y *even if Y contains a level with the same name*. Consider: a context authored against chain X (where `"DIA"` is rank 7 of 12) compiled against chain Y (where someone names an unrelated level `"DIA"` at rank 2 of 5). Every name matches; a naive membership check passes; the compiler silently reinterprets the context under Y's order. This is the "authorization created by representation" failure the paper exists to prevent, reproduced at the API boundary by name-collision.

Two mechanisms together close this hole:

1. **Membership check (name-level).** The compiler validates that every Permission referenced in the context — profile permission levels, `authority_ceiling`, `permission_ceiling`, and any other field typed as `Permission` — is contained in the chain by name. Fails as `MalformedContext`.

2. **Chain hash (chain-level).** Every emitted `Judgment` carries the `chain_hash` of the chain that authorized it. Composition of two `Judgment`s with different `chain_hash`es is rejected as `MalformedContext`. A `ProofContext` may optionally declare an `expected_chain_hash: Option<ChainHash>` field; if present, the compiler rejects with `MalformedContext` unless `chain.chain_hash() == expected_chain_hash`. Contexts authored against chain X are then unable to be silently reinterpreted under Y — even if Y has a name-collision.

Audit-log carriage: `Judgment.chain_hash` is the canonical location. Individual `DerivationStep`s do NOT each carry the hash (would balloon the log), but the `Judgment` envelope does.

**Hash alone is necessary but not sufficient.** A `ChainHash` is an opaque 32-byte fingerprint; an auditor holding a judgment with a hash but no corresponding chain has detection without inspection — they can tell that *some* chain authorized the decision and that two judgments share or differ, but they cannot read what that chain *says*. For a project whose thesis is that authorization-by-unexamined-convention is the failure mode, a hash pointing at a chain nobody archived is a convention you can detect but not inspect. This is not adequate.

Two mechanisms close the publication gap. Implementations MUST do both:

3. **Optional chain sidecar on the judgment.** `Judgment` carries an optional `chain: Option<PermissionChain>` field that, when `Some`, holds the full chain inline. This is a serializable sidecar — auditors who serialize a judgment for archival can opt in to inlining the chain so the artifact is self-contained. Default is `None` (chain referenced by hash only) to keep judgments small in normal operation. Setting it is one call: `judgment.with_chain_sidecar(&chain)`.

4. **Mechanically verified publication.** A `ChainRegistry` trait + a `verify_published(judgment, &registry)` function. A registry maps `ChainHash → PermissionChain`. The verification function returns `Ok(())` if the judgment's `chain_hash` resolves in the registry to a chain that hashes back to the same value, and `Err(NotPublished)` otherwise. The intended deploy pattern: every authority publishing decisions also publishes a chain registry; downstream auditors run `verify_published` over the corpus. **An acceptance criterion (§8) requires that a smoke test exists which: (a) compiles a judgment, (b) attempts `verify_published` against an empty registry and asserts it fails, (c) publishes the chain to the registry, (d) re-runs and asserts it passes.**

The trait + smoke test convert "publication" from prose obligation to compile-time API. Authorities are still free to publish or not, but a downstream auditor can mechanically determine which. `provenance.md` is amended to require, for any judgment archived for audit, EITHER a chain sidecar OR a published registry entry for that judgment's `chain_hash`.

```rust
pub trait ChainRegistry {
    fn lookup(&self, hash: &ChainHash) -> Option<&PermissionChain>;
}

/// Returns Ok(()) iff judgment.chain_hash resolves in the registry AND the
/// resolved chain re-hashes to the same value. Catches both unpublished hashes
/// and registries that have been tampered with post-publication.
pub fn verify_published<R: ChainRegistry>(
    judgment: &Judgment,
    registry: &R,
) -> Result<(), AuditError>;
```

### 3.4 Compiler signature

The primary entry point requires an explicit chain. The bare `compile` is preserved as a convenience for tests and examples, but it **stamps the judgment** with the default-chain hash so the choice is recorded even when implicit. There is no silent default at any level of the API.

```rust
// noethers-turnstile-core/src/compiler.rs

/// Primary entry point. Caller supplies the chain explicitly.
/// Resulting Judgment carries chain.chain_hash().
pub fn compile_with_chain(
    ctx: ProofContext,
    chain: &PermissionChain,
) -> Result<Judgment, TurnstileError> {
    // ... uses chain.role(ChainRole::Bottom), chain.descending(), chain.meet(...) ...
}

/// Convenience wrapper for tests, examples, and migration. Equivalent to
/// `compile_with_chain(ctx, PermissionChain::default_chain())`. The returned
/// Judgment's `chain_hash` field IS set to the default chain's hash — the
/// decision to use the default chain is *recorded*, not implicit.
///
/// Production callers should prefer `compile_with_chain` so the chain
/// selection appears at the call site.
pub fn compile(ctx: ProofContext) -> Result<Judgment, TurnstileError> {
    compile_with_chain(ctx, PermissionChain::default_chain())
}
```

Inside `compile_with_chain`, every literal `Permission::OOC` etc. is replaced by `chain.role(...)`. The compiler **never** names a level by string literal — see §7.8 for the CI guard.

`compose` / `compose_n` get the same treatment:

```rust
pub fn compose_with_chain(
    g1: ProofContext,
    g2: ProofContext,
    chain: &PermissionChain,
) -> Result<ProofContext, TurnstileError> { ... }

pub fn compose(g1: ProofContext, g2: ProofContext) -> Result<ProofContext, TurnstileError> {
    compose_with_chain(g1, g2, PermissionChain::default_chain())
}
```

**Considered and rejected:** gating bare `compile` behind a `#[cfg(test)]` or feature flag so library *consumers* must pass a chain explicitly. The hash-stamping approach (above) achieves the same audit property — "no decision is unrecorded" — without forcing every existing example, doc test, and downstream consumer to break on import. The hash on the judgment is what auditors care about; the call-site shape is ergonomic surface.

### 3.5 What changes in `ProofContext`

The chain is **not** stored in `ProofContext`. The chain is an argument to `compile`/`compose`. Rationale:

- Avoid serializing a chain into every context (would explode wire format).
- Composition of two contexts compiled against different chains is undefined; making the chain a compile-time argument forces the caller to pick one.
- The compiler's first validation step (new) confirms every Permission in the context is in the chain.

`Permission::top()` is removed. The serde default for `permission_ceiling` becomes the chain's top — but since the chain isn't available at deserialization time, we change the field type:

```rust
#[serde(default)]
pub permission_ceiling: Option<Permission>,
```

`None` means "no ceiling" (= chain top). Same treatment for `authority_ceiling`. The compiler resolves `None → chain.role(ChainRole::Top)` at compile time. This is the **only** behavioral change visible at the wire boundary; old contexts with explicit `"AAA"` still deserialize correctly.

### 3.6 String codec

`Permission::from_str` no longer makes sense as a free function (it would need a chain). It becomes:

```rust
impl PermissionChain {
    pub fn parse(&self, s: &str) -> Option<Permission> { ... } // case-sensitive
}
```

The 12 named constructors (`Permission::OOC`, ...) are removed from the public API of the core crate. Tests and Python bindings get a compatibility shim (§3.7).

### 3.7 Tests + Python: compatibility shim

The user's constraint: tests can still write `Permission::DIA`. This is satisfied by a module that re-exports the default chain's levels as named constants:

```rust
// noethers-turnstile-core/src/permission/default_levels.rs
// Re-exported as `noethers_turnstile_core::default_levels::*` for tests.
//
// LIBRARY CODE MUST NOT USE THIS MODULE. Only tests, examples, and the
// Python binding's compatibility layer may import these constants.

use crate::permission::Permission;
use once_cell::sync::Lazy;

pub static OOC: Lazy<Permission> = Lazy::new(|| Permission::new("OOC"));
pub static EXP: Lazy<Permission> = Lazy::new(|| Permission::new("EXP"));
// ... etc for all 12
```

A lint / CI check (cheap: `grep -r 'default_levels::' noethers-turnstile-core/src/`) enforces that core library code does not import this module. The check is documented in `CONTRIBUTING.md`-equivalent location (or as a comment at the top of the module).

For Python: the existing `ts.Permission.DIA` style API is preserved. `noethers-turnstile-py` exposes `Permission` as an opaque type whose attribute access (`Permission.DIA`) returns the default-chain level. A new `PermissionChain` class is exposed; `compile` accepts an optional `chain=` kwarg.

### 3.8 Default-chain compatibility

Behavioral contract: **for the default chain, every public function returns bit-identical results to the pre-refactor code, except where §3.5 changes the wire format (None-as-top in ceilings).** This is testable:

- All 998 existing Rust tests pass unchanged.
- All 100 existing Python tests pass unchanged.
- The proptest invariants (non-promotion, provenance, expiry, monotonicity) pass on the default chain.
- `PermissionChain::default_chain() == frozen_default_v1()` where `frozen_default_v1()` is a const-constructible chain with the historical 12 names in their historical order and the historical role bindings. This is the former L10, demoted from a validator rule to a single equality assertion.
- `PermissionChain::default_chain().chain_hash()` matches a frozen 32-byte hex string committed to the test fixtures. If the default chain ever changes (intentional or accidental), this assertion is the canary.

The proptest harness gains a **new** suite (`proptest_arbitrary_chain.rs`) that generates random valid chains and asserts the four invariants still hold. This is the property (1)+(2)+(3) acceptance test for the refactor.

### 3.9 Error handling at the boundary

If `compile_with_chain(ctx, chain)` is called with a context that references a permission name not in `chain`:

```
TurnstileError::MalformedContext("profile permission 'DIA' not in supplied chain")
```

If `compose_with_chain(g1, g2, chain)` is called with mismatched chains (i.e. either context's ceilings reference a level not in `chain`): same error.

Constructing a `PermissionChain` that violates L1–L9 returns `TurnstileError::ChainError(...)` — not panic.

## 4. What is NOT in scope

- Renaming `Permission` to something else. The type keeps its name; only its representation changes.
- Adding new compiler steps or changing the algorithm. The refactor is purely structural — every step's semantics is preserved under the default chain.
- Reworking `Profile` / `GapRequirement` / `Token`. Their `permission` fields stay typed as `Permission`; they're validated against the chain at compile time.
- Refactoring the 50+ ec00*-ec0050 test files. They continue to use `default_levels::DIA` etc. (re-export shim).
- Changing the audit log format. `DerivationStep::permission_after` is still a `Permission`; readers consult the chain to interpret its rank.
- A Python API for constructing custom chains in this pass. Python keeps the default chain for now; a follow-up exposes `PermissionChain` construction with role kwargs.

## 5. Implementation order

1. **Add `PermissionChain` + `ChainRole` + validation** (`permission.rs`). New code, no callers yet. Unit tests cover L1–L9.
2. **Add `default_levels` module** with the twelve `Lazy<Permission>` constants. Verify it round-trips through `PermissionChain::default_chain().parse(...)`.
3. **Add `compile_with_chain` alongside `compile`.** Existing `compile` delegates. Migrate the body of `compile` line-by-line to use `chain.role(...)` instead of `Permission::OOC` etc. Existing tests must still pass.
4. **Same migration for `compose` → `compose_with_chain`.**
5. **Migrate `ProofContext` ceilings to `Option<Permission>`** with serde default `None`. Update default-construction sites. Verify wire-format back-compat with a serde round-trip test for the historical `"AAA"` string.
6. **Migrate test files** to use `default_levels::DIA` instead of `Permission::DIA`. Mechanical replace; one commit per ec00* file is fine but a single sweep is cleaner.
7. **Add `proptest_arbitrary_chain.rs`** generating random valid chains (3–256 levels, random role assignments satisfying L1–L9) and asserting the four guarantees. Stratify the level-count distribution so small (3–8), medium (9–32), and boundary (240–256) chains are all sampled.
8. **Add the static lint** (CI check that core src/ does not import `default_levels::`).
9. **Update Python bindings** to expose `PermissionChain` as an opaque type and accept `chain=` on `compile`. Default behavior unchanged.
10. **Update README + guide docs** with the new API.

Steps 1–4 are the load-bearing migration. Steps 5–10 are mechanical.

## 6. Open questions to resolve before coding

1. **Permission rank stability.** Currently `profile.permission as u8` is used in `validate_context` to detect duplicate profiles. With `Permission` as a struct, this becomes `chain.rank(p)`. Confirms: validation needs the chain. → Means `validate_context` must be folded into `compile_with_chain` (it already lives there; signature changes).

2. **`Permission` equality across chains.** Two `Permission { name: "DIA" }` values are `Eq`. Is that desirable? **Yes**, because contexts deserialize names from strings and we need to match them against chain levels by name. The chain provides the order; the name provides the identity.

3. **Should `Permission::Display` show the name only, or `name@rank`?** Just the name. Rank is chain-relative and meaningless outside it.

4. **Audit-log readability when a non-default chain is used.** `DerivationStep` records names. A reader who knows the chain can resolve order. This is sufficient; we don't bake the chain into the audit log.

5. **L7/L8/L9 strict or non-strict?** Defaults to **non-strict** (see Q5 in §7.7). The default 12-level chain satisfies strict; a paper-style 5-level chain collapses three below-threshold roles to `REF`.

6. **Non-constancy lemma test feasibility.** See Q6 in §7.7. Recommendation: include as a unit test that asserts the compiler returns the same output on two contexts with identical evidence but different unobservable world facts.

7. **Golden-value corpus for default-chain wire compat.** See Q7 in §7.7. Capture pre-refactor compile outputs **before** step 1 of §5; commit them to `noethers-turnstile-tests/fixtures/pre_refactor_contexts/`.

8. **What is `MAX_LEVELS` and is it load-bearing?** The earlier draft said "64 fits in a u8 cheaply" — but a u8 holds 256, so 64 was an arbitrary sub-cap. Decision: `MAX_LEVELS = 256` (`u8::MAX + 1`). The rank type is `u8`; that's the only hard limit. Anything below 256 is a soft limit at most. The proptest generator (P-CHAIN-01) is widened to 3–256 levels with random sampling so the boundary is fuzzed. If a downstream component later needs a tighter cap (e.g. a bitset over levels), it raises its own error; the chain validator does not.

9. **String-literal level names in compiler/composition source.** The all-meets discipline of §2.1 says the compiler never names a level. The CI grep gate in §7.8 currently catches `Permission::DIA`-style variant references but not bare string literals like `chain.parse("DIA")` in `compiler.rs` / `composition.rs`. Decision: add a second grep that fails CI if any of the historical 12 names (`OOC|EXP|REF|UNS|ETA|ESC|ROL|DIA|REV|AEX|ALR|AAA`) appear as quoted string literals in `noethers-turnstile-core/src/compiler.rs` or `noethers-turnstile-core/src/composition.rs`. (Doc comments are excluded by matching only on `"` quotes inside non-comment lines, or — simpler — by running the grep against `cargo rustc --emit=mir` output if doc-comment exclusion is fiddly.)

10. **Chain hash carriage in `DerivationStep`.** §3.3 puts the hash on the `Judgment` envelope. Should each `DerivationStep` also carry it? Decision: **no**, for the reasons in §3.3 (log size). The `Judgment.chain_hash` is the canonical anchor; an auditor reading a derivation always reads it inside a `Judgment` envelope and can resolve the chain from there.

## 7. Test matrix

This is the load-bearing section. The spec has to demonstrate that the parameterization preserves every property the paper proves, on **every** valid chain — not just the default. Conversely, invalid chains must be rejected at construction, not at compile time.

The matrix is organized by paper property → required test → location. Each row is a separate file in `noethers-turnstile-tests/src/` following the existing `ec0XX_*` convention. A new prefix `ec051`–`ec060` is allocated for chain-parameterization tests so existing tests are not renumbered; sub-suffixes (`ec052b`, `ec055b`, etc.) are used where one numeric prefix covers multiple closely-related test files.

### 7.1 Chain construction validation (property 2 in the user's request)

Tests for `PermissionChain::new` itself. These do not touch the compiler.

| ID | File | What it tests | Expected outcome |
|---|---|---|---|
| C-VALID-01 | `ec051a_chain_valid_default.rs` | `PermissionChain::default_chain()` constructs without error, has exactly 12 levels, all six roles mapped | `Ok` |
| C-VALID-02 | `ec051a_chain_valid_default.rs` | A minimal 2-level chain `[bottom, top]` with `Bottom→0`, `Top→1`, `ExpiryFloor→0`, `Refused→0`, `Unsatisfied→0`, `BlockerThreshold→1` | `Ok` — degenerate but valid under non-strict L7–L9 (per Q5 resolution); all four below-threshold roles collapse to `Bottom` |
| C-VALID-03 | `ec051a_chain_valid_default.rs` | A 5-level paper-style chain `[REF, DIA, REV, AEX, ALR]` with roles assigned per §3.2 | `Ok` — matches the abbreviated chain used in `docs/pivot/pivot-paper-v5.md` §2.2 |
| C-VALID-04 | `ec051a_chain_valid_default.rs` | A 256-level chain (`MAX_LEVELS` boundary of L1 — see Q8) | `Ok` |
| C-VALID-05 | `ec051a_chain_valid_default.rs` | A 255-level chain (`MAX_LEVELS - 1`) | `Ok` |
| C-INVALID-01 | `ec051b_chain_invalid_rejected.rs` | 1-level chain | `Err(ChainError::TooFewLevels)` |
| C-INVALID-02 | `ec051b_chain_invalid_rejected.rs` | 257-level chain (`MAX_LEVELS + 1`) | `Err(ChainError::TooManyLevels)` |
| C-INVALID-03 | `ec051b_chain_invalid_rejected.rs` | Chain with empty-string level name | `Err(ChainError::InvalidName { reason: NameRejectionReason::Empty, .. })` |
| C-INVALID-04 | `ec051b_chain_invalid_rejected.rs` | Chain with duplicate level names | `Err(ChainError::DuplicateName(_))` |
| C-INVALID-05 | `ec051b_chain_invalid_rejected.rs` | Chain missing the `Top` role mapping | `Err(ChainError::MissingRole(ChainRole::Top))` |
| C-INVALID-06 | `ec051b_chain_invalid_rejected.rs` | Chain with `Bottom` not at index 0 | `Err(ChainError::RoleOrderViolation { role: Bottom, .. })` |
| C-INVALID-07 | `ec051b_chain_invalid_rejected.rs` | Chain with `Top` not at last index | `Err(ChainError::RoleOrderViolation { role: Top, .. })` |
| C-INVALID-08 | `ec051b_chain_invalid_rejected.rs` | Chain with `ExpiryFloor` ≥ `BlockerThreshold` (violates L7) | `Err(ChainError::RoleOrderViolation { role: ExpiryFloor, .. })` |
| C-INVALID-09 | `ec051b_chain_invalid_rejected.rs` | Chain with `Refused` ≥ `BlockerThreshold` (violates L8) | `Err(ChainError::RoleOrderViolation { role: Refused, .. })` |
| C-INVALID-10 | `ec051b_chain_invalid_rejected.rs` | Chain with `Unsatisfied` ≥ `BlockerThreshold` (violates L9) | `Err(ChainError::RoleOrderViolation { role: Unsatisfied, .. })` |
| C-INVALID-11 | `ec051b_chain_invalid_rejected.rs` | Chain with a name violating the L2 charset (covers: null byte, space, non-ASCII char, NFC-vs-NFD ambiguity case like `"DIÁ"` vs `"DIA\u{0301}"`, name starting with `-`, name longer than 64 bytes) — one assertion per failure shape | `Err(ChainError::InvalidName { name, reason })` with `reason` distinguishing the failure shape |

### 7.2 Compiler behavior under custom chains (property 3 in the user's request)

Each of these tests instantiates a non-default chain and asserts that the compiler's behavior on that chain matches what the paper's theorems predict.

| ID | File | Paper property | What it tests |
|---|---|---|---|
| T-SOUND-01 | `ec052_compile_with_custom_chain_soundness.rs` | Soundness (§3.1, §3.3) | On a paper-style 5-level chain `[REF, DIA, REV, AEX, ALR]`, a context whose only profile requires a closed gap that is open emits `chain.role(Unsatisfied)`, not the profile's permission. Verified for every level in the chain. |
| T-SOUND-02 | `ec052_compile_with_custom_chain_soundness.rs` | Soundness | On a 3-level minimal chain `[Bottom, Mid, Top]` (with `BlockerThreshold = Top`), an unsatisfied profile at `Top` emits `Unsatisfied`. |
| T-SHARP-01 | `ec053_compile_with_custom_chain_sharpness.rs` | Sharpness (§3.1, §3.3) | On a paper-style chain, the compiler returns the **strongest** satisfied profile, not the weakest. Construct a context with closed gaps satisfying profiles at `DIA`, `REV`, and `AEX` — assert outcome is `AEX`. |
| T-SHARP-02 | `ec053_compile_with_custom_chain_sharpness.rs` | Sharpness | Same as T-SHARP-01 but on a 16-level chain with arbitrary names (`L00`..`L15`). Verifies sharpness is name-agnostic. |
| T-EXPIRY-01 | `ec054_compile_with_custom_chain_expiry.rs` | Expiry fires at boundary (README guarantee 3) | On a non-default chain, an expired Valid-status token floors outcome to `chain.role(ExpiryFloor)`, not a hardcoded `EXP`. Verified by passing a chain whose `ExpiryFloor` role points to a level named `"FROZEN"` and asserting outcome name == `"FROZEN"`. |
| T-EXPIRY-02 | `ec054_compile_with_custom_chain_expiry.rs` | Expiry monotonicity | If `ExpiryFloor` is at rank 2 in a 10-level chain, and the descending search would have landed at rank 5, the expiry meet lowers to rank 2 — never raises. |
| T-PROV-01 | `ec055_compile_with_custom_chain_provenance.rs` | Provenance enforcement (README guarantee 2) | A token with a wrong provenance hash forces a meet with `chain.role(Refused)` when `outcome < chain.role(BlockerThreshold)`. Verified across three chains: default, paper-5-level, and an 8-level chain with custom role assignments. |
| T-PROV-02 | `ec055_compile_with_custom_chain_provenance.rs` | Provenance + blocker threshold suppression | A correct-provenance token that **satisfies** a profile above the chain's `BlockerThreshold` suppresses the structural blocker even if a wrong-provenance token is also present. Verifies the `outcome < BlockerThreshold` guard transfers to non-default chains. |
| T-MONO-01 | `ec056_compile_with_custom_chain_monotonicity.rs` | Evidence monotonicity (README guarantee 4) | On every chain in a test set of 8 hand-crafted chains, adding a closed token to a context never lowers the emitted permission. Implemented as a property: `compile(ctx).permission ≤ compile(ctx_with_extra_closed_token).permission` under the chain's order. |
| T-NONPROMO-01 | `ec057_compose_with_custom_chain_nonpromotion.rs` | Non-promotion under composition (README guarantee 1) | `compose_with_chain(g1, g2, chain).then_compile() ≤ chain.meet(compile(g1), compile(g2))` for every chain in the test set. |
| T-NONPROMO-02 | `ec057_compose_with_custom_chain_nonpromotion.rs` | Non-promotion + chain mismatch | `compose_with_chain(g1, g2, chain)` where `g1.permission_ceiling` references a name not in `chain` returns `MalformedContext`. |
| T-REPR-01 | `ec058_representation_theorem_under_chains.rs` | Representation theorem (§3.3) | On a paper-5-level chain, construct two contexts that have identical evidence representations but differ in a hidden world fact — the compiler must return the same permission for both, demonstrating sharpness depends on the representation, not the chain. Asserts the theorem's conditional: "sharp iff representation reveals the failure" is invariant to chain choice. |
| T-NONCONST-01 | `ec058_representation_theorem_under_chains.rs` | Non-constancy lemma (§3.4) | Construct a permission-relevant failure mode `G` that is invisible to the evidence map under chain X. Verify that two contexts mapping to the same evidence yield the same compiler output but at least one is unsound — i.e. the gap is non-empty. (This is a "negative" test: it asserts the compiler correctly fails to be sharp when the representation hides a relevant failure, on a non-default chain.) |
| T-DEFAULT-01 | `ec059_default_chain_behavioral_equivalence.rs` | Default-chain compatibility (§3.8) | For a corpus of 50 hand-rolled contexts (cherry-picked from existing ec00* tests covering provenance mismatch, expiry, multi-profile, composition, ceilings, OOC membership), `compile(ctx) == compile_with_chain(ctx, default_chain())` bit-for-bit on `permission`, `expiry`, and `derivation`. |
| T-DEFAULT-02 | `ec059_default_chain_behavioral_equivalence.rs` | Default-chain wire compat | A frozen JSON corpus (committed to `noethers-turnstile-tests/fixtures/pre_refactor_contexts/*.json`) of pre-refactor contexts deserializes and compiles under the default chain to outcomes matching pre-refactor golden values (also frozen). |

### 7.3 Property-based tests over the space of valid chains

| ID | File | What it tests |
|---|---|---|
| P-CHAIN-01 | `ec060_proptest_arbitrary_chain.rs` | Generator: random valid chains of 3–256 levels (stratified: small 3–8, medium 9–32, boundary 240–256), random role assignments satisfying L1–L9. The four README guarantees hold on every generated chain × context pair. |
| P-CHAIN-02 | `ec060_proptest_arbitrary_chain.rs` | Round-trip: every level produced by `chain.descending()` is parseable by `chain.parse(level.as_str())`. |
| P-CHAIN-03 | `ec060_proptest_arbitrary_chain.rs` | `chain.meet(a, b)` is the greatest lower bound: `chain.meet(a,b) ≤ a`, `≤ b`, and no element `c ≤ a, c ≤ b` has `c > chain.meet(a,b)`. |
| P-CHAIN-04 | `ec060_proptest_arbitrary_chain.rs` | Determinism: compiling the same context with the same chain twice yields identical judgments (extends ec016 to non-default chains). |
| P-CHAIN-05 | `ec060_proptest_arbitrary_chain.rs` | Cross-chain rejection: a context's permission names from chain A used with chain B (where B lacks at least one of those names) always yields `MalformedContext`. |

### 7.4 Negative tests: things that should fail

These exist to prove the system rejects bad inputs at the right boundary, not at runtime via a panic.

| ID | What it tests | Expected error |
|---|---|---|
| N-01 | `compile_with_chain(ctx, chain)` where ctx has a profile permission name not in chain | `MalformedContext` |
| N-02 | `compile_with_chain(ctx, chain)` where ctx has `authority_ceiling = Some(level)` with `level.name` not in chain | `MalformedContext` |
| N-03 | Constructing a chain where `Bottom == Top` (excluded transitively by L1 ≥ 2 levels + L5 `Bottom==0` + L6 `Top==len-1`; this row tests that the transitive exclusion actually fires) | `ChainError` (specifically: L1 fires for `len==1`, or the chain has `len≥2` and `Bottom`/`Top` cannot map to the same index without violating L5 or L6) |
| N-04 | `compose_with_chain(g1, g2, chain)` where `g1.chain_hash != chain.chain_hash()` or `g2.chain_hash != chain.chain_hash()` | `MalformedContext::ChainMismatch` |
| N-05 | Round-trip a chain through serde and verify the round-tripped chain validates and produces identical compile outputs **and identical `chain_hash`** | `Ok` + bit-equal — guards against serde-introduced reordering |
| N-06 | `chain.meet(level_in_chain, level_not_in_chain)` | `ChainError::ForeignLevel` — never silently returns `Bottom` |
| N-07 | Context authored against chain X compiled with chain Y where Y has a name-collision (e.g. a level named `"DIA"` at a different rank) and ctx has `expected_chain_hash: Some(X.chain_hash())` | `MalformedContext::ChainMismatch` — proves name-equality alone does not authorize reinterpretation |

### 7.4a All-meets discipline tests (load-bearing — covers critique #1)

This subsection exists specifically because the all-meets discipline of §2.1 is the source of the non-promotion theorem; if it's not directly tested, the spec's safety claim is unverified.

| ID | File | What it tests |
|---|---|---|
| AM-01 | `ec052b_all_meets_discipline_expiry.rs` | Construct a 6-level chain `[L0, L1, L2_ExpiryFloor, L3_BlockerThreshold, L4, L5]` — `ExpiryFloor` is **mid-chain**, not near the bottom. Construct a context where the descending search lands at L1 (below the expiry floor) and an expired Valid-status token is also present. Assert: outcome is L1, not L2. Proves that the expiry step is implemented as `chain.meet(outcome, expiry_floor)` — never `outcome := expiry_floor`. If the step were a positional clamp, outcome would be wrongly *raised* to L2. |
| AM-02 | `ec052b_all_meets_discipline_expiry.rs` | Same chain as AM-01, descending search lands at L5. Expired token present. Assert: outcome is L2 (the expiry floor — the meet lowered from L5 to L2). |
| AM-03 | `ec052b_all_meets_discipline_blockers.rs` | Construct a chain where `Refused` is mid-chain (not at the bottom). Construct a context that lands the descending search below `Refused` and has a provenance-mismatch token present. Assert: outcome is unchanged (the structural-blocker meet from below-`Refused` does not promote to `Refused`). |
| AM-04 | `ec052b_all_meets_discipline_blockers.rs` | Same chain as AM-03. Descending search lands at the `BlockerThreshold`. Provenance-mismatch token present. Assert: outcome is below `Refused`-or-at-`Refused` (the meet lowers). Together AM-03 + AM-04 prove the blocker step lowers from above, never promotes from below. |
| AM-05 | `ec052b_all_meets_discipline_compose.rs` | `compose_with_chain(g1, g2, chain)` where the composition's permission-ceiling meet has the meet target placed mid-chain. Assert: composition outcome is `chain.meet(compile(g1), compile(g2))` and is never above either component, on chains where the role anchors are deliberately not at the bottom. |
| AM-06 | `ec052b_all_meets_discipline_compose.rs` | The non-promotion theorem holds element-wise: for every step recorded in `Judgment.derivation`, `step.permission_after ≤ previous_step.permission_after` under the chain's order. Verified for 100 randomly generated contexts × 10 randomly generated chains. |
| AM-07 | `ec052b_all_meets_discipline_collapsed.rs` | **Dual of AM-01: collapsed-anchor safety.** Construct a paper-style 5-level chain `[REF, DIA, REV, AEX, ALR]` where `Bottom=ExpiryFloor=Refused=Unsatisfied=REF` (all four below-threshold roles collapsed onto the same level, valid under non-strict L7–L9). Construct a context that simultaneously fires all three below-threshold meets: descending-search lands at `Unsatisfied` (no profile satisfied), a provenance-mismatch token is present (Refused meet), and an expired Valid-status token is present (ExpiryFloor meet). Assert: (a) final outcome is `REF`, (b) the recorded derivation is monotone step-by-step through all three meets, (c) each meet's `permission_after` equals `REF` (idempotent meets on the coincident target). Proves that the all-meets discipline survives anchor collapse — coincident targets are safe because `meet` is idempotent. Without this test, Q5's non-strict resolution is asserted by construction (C-VALID-02/03) but never exercised through a multi-blocker compile. |

### 7.4b Chain identity tests (covers critique #5)

| ID | File | What it tests |
|---|---|---|
| CH-01 | `ec055b_chain_identity.rs` | Construct two chains X and Y where both contain a level named `"DIA"` at different ranks. Build a context authored against X with `expected_chain_hash: Some(X.chain_hash())`. Compile with Y. Assert: `MalformedContext::ChainMismatch`. |
| CH-02 | `ec055b_chain_identity.rs` | Same as CH-01 but with `expected_chain_hash: None`. Compile with Y. Assert: compile **succeeds** but the resulting `Judgment.chain_hash == Y.chain_hash()`. An auditor reading the judgment can detect that Y, not X, authorized the decision. |
| CH-03 | `ec055b_chain_identity.rs` | `Judgment.chain_hash` is stable across `clone()` and serde round-trip. |
| CH-04 | `ec055b_chain_identity.rs` | `chain_hash` is deterministic across processes (same chain content → same hash). Verified by serializing a chain, re-parsing, computing the hash, and asserting equality. |
| CH-05 | `ec055b_chain_identity.rs` | Two chains differing only in role binding (same ordered names, different role→index map) have **different** hashes. |
| CH-06 | `ec055b_chain_identity.rs` | `compose_with_chain(g1, g2, chain)` rejects when `g1.chain_hash != chain.chain_hash()`. Verified for both g1 and g2 mismatches independently. |

### 7.5 Test coverage check: theorem-by-theorem

| Paper property | Default-chain test (existing) | Custom-chain test (new) |
|---|---|---|
| Soundness | `ec048_theorem2_greatest_satisfiable.rs` | T-SOUND-01, T-SOUND-02, P-CHAIN-01 |
| Sharpness | `ec048_theorem2_greatest_satisfiable.rs`, `ec035_multi_profile_descending_search.rs` | T-SHARP-01, T-SHARP-02 |
| Non-promotion (T9) — via all-meets discipline | `ec003b_composition_algebra.rs`, `proptest_composition.rs` | T-NONPROMO-01, T-NONPROMO-02, AM-01..06, P-CHAIN-01 |
| Provenance enforcement | `ec028_provenance_unicode_and_large_input.rs`, `proptest_*` | T-PROV-01, T-PROV-02, AM-03, AM-04 |
| Expiry-at-boundary | `ec020_token_expiry_edge_cases.rs`, `ec022_livejudgment_lifetime_guard.rs` | T-EXPIRY-01, T-EXPIRY-02, **AM-01, AM-02** (mid-chain expiry floor) |
| Evidence monotonicity | `proptest_monotonicity.rs`, `ec003m_evidence_monotonicity.rs` | T-MONO-01, P-CHAIN-01 |
| Representation theorem | (implicit in ec048 + ec032/033) | T-REPR-01 |
| Non-constancy lemma | (not previously tested explicitly — see open question Q6) | T-NONCONST-01 |
| Meet is GLB (T8) | `ec046_meet_glb_exhaustive.rs` | P-CHAIN-03 |
| Default-chain compatibility | n/a (this *is* the default) | T-DEFAULT-01, T-DEFAULT-02 |
| Chain construction | n/a | C-VALID-01..04, C-INVALID-01..11 |
| **All-meets discipline (§2.1)** | n/a (default chain hides this) | **AM-01..06** |
| **Chain identity (§3.3)** | n/a (no notion of chain in pre-refactor) | **CH-01..06, N-07** |

**Coverage rule:** every README guarantee and every named theorem/lemma in the paper appears in **at least one** custom-chain row of this table. Anything that does not is either (a) not affected by chain parameterization and the existing default-chain test suffices, or (b) needs an additional test added before merging — to be flagged at PR review.

Additionally, the all-meets discipline and chain identity rows are tested only by custom-chain tests **by necessity** — the default chain's role placements hide both failure modes. AM-01 in particular is the test that, if absent, the spec's response to critique #1 is unverified.

### 7.6 Test ergonomics

To keep the new tests readable, the test crate gets a small helper module:

```rust
// noethers-turnstile-tests/src/test_helpers/chains.rs

/// A paper-style 5-level chain: REF < DIA < REV < AEX < ALR.
/// Roles: Bottom=REF, ExpiryFloor=REF, Refused=REF, Unsatisfied=REF,
///        BlockerThreshold=DIA, Top=ALR.
pub fn paper_5_level() -> PermissionChain { ... }

/// A minimal 3-level chain for boundary testing.
pub fn minimal_3_level() -> PermissionChain { ... }

/// An 8-level chain with non-paper names ("L00".."L07") to verify
/// name-agnosticism.
pub fn anon_8_level() -> PermissionChain { ... }

/// A 16-level chain with `BlockerThreshold` in the middle, for testing
/// suppression of structural blockers above the threshold.
pub fn anon_16_level_mid_threshold() -> PermissionChain { ... }
```

The proptest generator (P-CHAIN-*) shares this module.

### 7.7 CI guards (the "compiler names no level" discipline)

Two grep gates run in CI. If either fails, the build fails.

**Gate 1 — no variant references.** No file under `noethers-turnstile-core/src/` outside `permission/default_levels.rs` may reference the historical variants as identifiers:

```bash
# Fails the build if any hit.
! grep -rE 'Permission::(OOC|EXP|REF|UNS|ETA|ESC|ROL|DIA|REV|AEX|ALR|AAA)\b' \
    noethers-turnstile-core/src/ \
    --exclude='default_levels.rs'
```

**Gate 2 — no string-literal level names.** No `.rs` file under `noethers-turnstile-core/src/compiler.rs` or `composition.rs` may contain the historical names as quoted string literals (catches `chain.parse("DIA")` and similar leaks):

```bash
# Fails the build if any hit. Excludes doc comments (lines starting with `///` or `//!`).
! grep -nE '"(OOC|EXP|REF|UNS|ETA|ESC|ROL|DIA|REV|AEX|ALR|AAA)"' \
    noethers-turnstile-core/src/compiler.rs \
    noethers-turnstile-core/src/composition.rs \
    | grep -vE '^[^:]+:[0-9]+:\s*(///|//!)'
```

Gate 2 enforces the spirit of §2.1: the compiler never names a level. Identifier-form references (Gate 1) and string-form references (Gate 2) together cover the surface.

**On a third gate (dropped).** An earlier draft proposed a Gate 3 that read `compiler.rs` source via `include_str!` at test time and asserted the only `chain.` method calls in `compile_with_chain`'s body came from an allowlist. Dropped. The check is brittle (breaks on rustfmt drift, on helpers the body delegates to, on method chains across lines) and tests a syntactic proxy for the real invariant. The real invariant — "every step lowers the outcome" — is checked semantically by **AM-06** (§7.4a), which asserts element-wise `permission_after ≤ previous_step.permission_after` across 100 randomly generated contexts × 10 randomly generated chains. AM-06 is the authoritative test; Gates 1 and 2 are cheap syntactic backstops.

### 7.8 New open questions raised by the test matrix

These are added to §6:

- **Q5.** Are L7, L8, L9 strict (`<`) or non-strict (`≤`)? A degenerate chain where `ExpiryFloor == Bottom == Refused == Unsatisfied` is **valid** under non-strict; under strict it requires three distinct levels below `BlockerThreshold`. The default chain satisfies strict. The minimal-3-level paper chain `[REF, DIA, REV, AEX, ALR]` collapses all four below-threshold roles to `REF`. → **Recommendation: non-strict.** Tests C-VALID-02 and C-VALID-03 verify this works.
- **Q6.** Should the `T-NONCONST-01` test be a unit test or a documentation example? The non-constancy lemma is a meta-property (about what the compiler *cannot* recover), not a property of any single compile call. The test asserts the compiler's silence-shape, not its output. Implementing it requires constructing two contexts with the same evidence but different world facts — feasible but laborious. → **Recommendation: include as a unit test; the test asserts the compiler returns the same output on both contexts and labels one as unsound externally.**
- **Q7.** Does `T-DEFAULT-02` require a golden-value corpus we don't currently have? Yes — pre-refactor compile outputs need to be captured before the refactor lands. → **Action: capture golden outputs in step 0 of the implementation plan (before step 1 of §5).**

## 8. Acceptance criteria

- [ ] `cargo test` — all 998 Rust tests pass without changes to their assertions about the default chain.
- [ ] `pytest` — all 100 Python tests pass.
- [ ] `cargo test -p noethers-turnstile-tests ec051` — chain validation tests (C-VALID-01..05, C-INVALID-01..11) pass.
- [ ] `cargo test -p noethers-turnstile-tests ec052` through `ec058` — all custom-chain behavior tests (T-*, AM-01..07, CH-01..06) pass.
- [ ] `cargo test -p noethers-turnstile-tests ec059` — default-chain behavioral equivalence (T-DEFAULT-01, T-DEFAULT-02) passes against the frozen golden corpus.
- [ ] `cargo test -p noethers-turnstile-tests ec060` — proptest over arbitrary chains (P-CHAIN-01..05) passes.
- [ ] §7.5 coverage table: every row has at least one passing custom-chain test.
- [ ] **Publication smoke test (§3.3 mechanism 4):** a test compiles a judgment, calls `verify_published` against an empty `ChainRegistry` and asserts `Err(NotPublished)`, publishes the chain to the registry, re-runs and asserts `Ok(())`. Without this passing, "publication" is not mechanically enforceable.
- [ ] `grep -r 'default_levels::' noethers-turnstile-core/src/` returns **zero hits** outside `permission/default_levels.rs` itself.
- [ ] `grep -rE 'Permission::(OOC|EXP|REF|UNS|ETA|ESC|ROL|DIA|REV|AEX|ALR|AAA)' noethers-turnstile-core/src/compiler.rs noethers-turnstile-core/src/composition.rs` returns **zero hits** (Gate 1).
- [ ] `grep -nE '"(OOC|EXP|REF|UNS|ETA|ESC|ROL|DIA|REV|AEX|ALR|AAA)"' noethers-turnstile-core/src/compiler.rs noethers-turnstile-core/src/composition.rs | grep -vE '(///|//!)'` returns **zero hits** (Gate 2).
- [ ] Wire-format compatibility: a JSON-serialized `ProofContext` from before the refactor (with `"authority_ceiling":"AAA"`) deserializes correctly after.
- [ ] README + Quick Start examples updated; `cargo test --doc` passes.
