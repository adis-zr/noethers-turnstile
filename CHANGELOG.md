# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Example `test_3_stress.py` — 9 stale assertions updated** (`examples/pgm/tests/test_3_stress.py`):
  - **A1–A5, D3** (6 tests): assertions updated from `OOC` → `REF`.  These tests present a
    valid-status token with wrong provenance.  Under current semantics the `PROVENANCE_MISMATCH`
    structural blocker fires at step 4 and applies a `meet(REF)` to the outcome.  `REF` (structural
    refusal — "credential seen and rejected") is the correct and more informative signal vs `OOC`
    ("not in class").  Docstrings updated accordingly.
  - **B1, B5** (2 tests): assertions updated from `OOC` → `EXP`.  These tests present a
    `Valid`-status token whose `expires_at` is in the past.  The expired token is silently skipped
    in `effective_gap_status` (gap stays OPEN), but step 6 independently fires the EXP floor because
    a valid-provenance valid-status time-expired token exists.  The EXP floor does not require a
    profile to be satisfied first.  The old docstring comment "EXP floor only applies when another
    valid token satisfies the profile first" was wrong and has been corrected.
  - **C3** (1 test, two assertions): `p_b` updated from `OOC` → `REF` (`tok_v2` has `Invalid`
    status with correct provenance → `DEAD_CREDENTIAL` blocker → REF); `p_composed` updated from
    `OOC` → `REF` (`permission_ceiling = meet(DIA, REF) = REF` caps the composed result).
    Anti-laundering invariant (T9) continues to hold — `p_composed ≤ meet(p_a, p_b)` is satisfied
    at REF.  Docstring rewritten to explain the full chain.

- **`examples/pgm/conftest.py` — new file** that prepends the workspace `python/` directory to
  `sys.path` at test collection time.  This ensures the example test suite always resolves to the
  locally-built `turnstile` rather than a potentially stale installed wheel, eliminating a class of
  silent version-skew failures.

- **Clippy: collapsible-if in `compiler.rs:411`** — collapsed nested `if` inside the
  `bounds_gaps` branch into a single `else if … && …` condition to satisfy
  `clippy::collapsible_if` under `-D warnings`.

- **Formatting: `assert_eq!` line-length violations in EC-003j and EC-049** — split two
  over-length `assert_eq!` calls into multi-line form so `cargo fmt --check` passes cleanly.

### Changed

- **Compiler: early context-expiry check (spec §14 step 4)** — `compile()` now checks
  `ctx.expiry.fired(now)` before evaluating any tokens or profiles.  If the context has already
  expired at compile time, a single `"context_expiry"` derivation step is emitted and the judgment
  short-circuits to `EXP`.  This prevents stale contexts from reaching the descending search.

- **Compiler: OOC → REF for in-class candidates with unmet profiles (spec §14 step 3)** — the
  descending search now initialises `outcome` to `REF` instead of `OOC`.  `OOC` is reserved for
  out-of-class membership (emitted by the membership check before the search begins) and for
  contexts that define no profiles at all.  An `InClass` candidate whose profiles are all defined
  but whose gap requirements are not met now emits `REF`, not `OOC`.

- **Compiler: `PROVENANCE_MISMATCH` structural blocker (spec §14 steps 6+9)** — tokens whose
  provenance hash does not match the context are now tracked via a `provenance_mismatch_seen` flag.
  When the flag is set *and* the descending search produced `REF` or lower (i.e. no profile was
  satisfied by a correct-provenance token), a `"structural_blockers"` derivation step applies a
  `meet(REF)` to the outcome.  If a correct-provenance token already satisfied a profile (outcome
  above `REF`), wrong-provenance tokens are silently rejected as before.

- **`gap::RequiredStatus::OpenAllowed` variant** — new variant that accepts any gap status
  (Open, Bounded, or Closed).  Satisfies the requirement whenever the gap is induced, regardless
  of closure level.  Python binding maps to the string `"open"`.

### Added

- **EC-041** (`ec041_allowed_use_soundness`): Allowed-use soundness exhaustive coverage (T12,
  EC-001 §14) — AU1–AU14 plus a property-based test; verifies that `allowed_use` is bound
  byte-for-byte in the provenance hash (Unicode, whitespace, case, leading/trailing space, null
  bytes), that empty `allowed_use` is rejected by `compile()`, that `compose()` returns
  UseConflict on mismatch, that `compose_n` fails closed if any context differs, and that a token
  issued under one `allowed_use` cannot close a gap in a context with a different `allowed_use`.
  14 + 1 prop tests.

- **EC-042** (`ec042_heterogeneous_anti_laundering`): Heterogeneous anti-laundering exhaustive
  coverage (T16, EC-001 §38) — H1–H16 plus two property-based tests; confirms that OOC membership
  is absorbing under `compose_n` for all 16 pairwise Membership combinations, all N-ary sizes
  (N=3,5,10), every insertion position (first/middle/last), the adversarial majority attack (9
  InClass + 1 OOC → OOC), and all three non-InClass membership variants paired with InClass. 18 +
  2 prop tests.

- **EC-043** (`ec043_audit_not_authority`): Audit-not-authority exhaustive coverage (T18,
  EC-001 §31.18) — A1–A9 plus a property-based test; extends EC-003x with 10k fabricated-AAA
  entries, concurrent audit writes + compiles, future-timestamp entries, duplicate entries, replay
  attacks using AuditEntry data as a ProofToken, and confirms that compile() result is independent
  of the number of store observers. 10 + 1 prop tests.

- **EC-044** (`ec044_authority_ceiling_exhaustive`): Authority ceiling exhaustive coverage (T19,
  EC-001 §31.19) — C1–C14 plus a property-based test; confirms that all 12 ceiling values act as
  hard caps (full evidence → result = ceiling), that ceiling OOC/EXP/DIA/REF/ROL each cap
  correctly, that `compose_n` ceiling is the meet of all inputs, that adding evidence above the
  ceiling is inert, and that ceiling is consulted after gap resolution. 15 + 1 prop tests.

- **EC-045** (`ec045_permission_triples_exhaustive`): Permission triples exhaustive coverage
  (T8/T9/T10, EC-001 §16) — TR1–TR5; full 12³ = 1728-triple enumeration of `meet` associativity,
  `meet_n` order-independence, left-fold = right-fold = `meet_n` equivalence, `meet_n` idempotence
  on duplicates, and split-fold correctness. 5 tests (each iterates all 1728 triples).

- **EC-046** (`ec046_meet_glb_exhaustive`): Meet GLB property exhaustive (T8, EC-001 §16) —
  GLB1–GLB5 plus a property-based test; verifies that `meet(a,b)` is the *greatest* lower bound
  (not just a lower bound) for all 144 pairs: lower bound law, GLB law (all common lower bounds
  ≤ meet), uniqueness (no strictly higher lower bound exists), idempotence, and the degenerate
  single-element case. 6 + 1 prop tests.

- **EC-047** (`ec047_step11_truth_table`): Step 11 assembler truth table (T8/T11, EC-001 §30) —
  S1–S16; ported from the Python `test_ec003f_step11_assembler.py` 16-case critical-combination
  table; covers refusal-tier vs control-tier dominance, all OOC-absorbing cases, control-tier
  ordering, cross-tier conflict matrix for UNS, all 12 idempotence cases, and permutation
  invariance of [OOC, ESC, AAA]. 16 tests.

- **EC-048** (`ec048_theorem2_greatest_satisfiable`): Theorem 2 greatest-satisfiable permission
  (T5/T10, EC-001 §31.2) — T2-1–T2-11 plus a property-based test; ported from Python
  `test_ec004a_theorem2_property_based.py`; verifies that `compile()` returns the *greatest*
  satisfying permission (not just *a* satisfying permission): all 12 permission targets reachable,
  boundary conditions (all-open → weakest; all-closed → highest), evidence upgrade raises
  permission by exactly one step, partial evidence satisfies exactly the reachable profile, and
  authority ceiling caps the greatest satisfiable. 12 + 1 prop tests.

- **EC-049** (`ec049_admission_contract_a1_a9`): Admission contract A1–A9 depth (T6/T19,
  EC-001 §35) — 14 tests; ported from Python `test_ec005a_admission_contract_predicates.py`
  (~311-test suite); deepens coverage of the nine finite admission conditions enforced by
  `compile()`: duplicate gap_id rejection, aliased-but-distinct gap_ids accepted, 10k-gap context
  terminates in bounded time, ceiling-capped result for all 12 levels, fingerprint mismatch in
  RuntimeContext, and adversarial large inputs (1M-char `allowed_use`, 1k gaps × 1k-char IDs,
  1k all-open profiles). 14 tests.

- **EC-050** (`ec050_schema_version_adversarial`): Schema version mismatch adversarial (T2,
  EC-001 §13) — SV1–SV12; extends EC-003k and EC-014 with adversarial schema/version mismatch
  scenarios: unregistered version rejection, empty schema_version rejected as MalformedContext,
  concurrent same-version registration (exactly one wins), 100-entry registry correctness,
  older-version token acceptance, two tokens with different versions of the same schema, whitespace
  and Unicode in schema_version treated as distinct identifiers, very long schema_version, and
  `get()` with wrong version returns None. 12 tests.

- **EC-031** (`ec031_adversarial_families`): Adversarial families A1–A10 from EC-001 §34 —
  systematically tests all ten named laundering paths: fake-token promotion (A1), diagnostic
  promoted into action (A2), stale context laundering (A3), provenance mismatch (A4), parent-scope
  laundering (A5), proxy-to-objective laundering (A6), coupling omission (A7), negative-control
  ritualization (A8), authority-gap laundering (A9), domain-certifier overreach (A10). Uses
  call-the-shots pre-registration discipline. 18 tests.

- **EC-032** (`ec032_positive_families`): Positive families P1–P10 from EC-001 §34 — end-to-end
  scenarios for all ten named in-class domains: approximate probabilistic inference (P1), OPE/causal
  inference (P2), marketplace allocation (P3), medical triage (P4), fraud and trust (P5),
  cybersecurity response (P6), trading risk (P7), LLM agent deployment (P8), scientific surrogate
  modeling (P9), resource-constrained planning (P10). Each family calls its expected outcome before
  constructing the scenario. 12 tests.

- **EC-033** (`ec033_negative_families`): Negative families N1–N10 from EC-001 §34 — confirms that
  all ten out-of-class exact-deterministic computations produce OOC even when fake proof tokens are
  attached: sorting (N1), exact SQL (N2), file hash verification (N3), unit conversion (N4),
  field validation (N5), static rendering (N6), CRUD updates (N7), regex matching (N8), feature
  flags (N9), cache lookups (N10). Also verifies OOC early exit produces exactly one derivation
  step. 14 tests.

- **EC-034** (`ec034_permission_tier_semantics`): Permission tier semantics and action-set
  interpretation from EC-001 §16–20 — verifies the five-tier priority table, OOC absorption,
  EXP domination, approval chain meet semantics, DIA as the action/non-action boundary, all
  144 pairwise meet non-promotion cases, commutativity, associativity, and idempotence. 16 tests.

- **EC-035** (`ec035_multi_profile_descending_search`): Multi-profile descending search and
  strongest-admissible selection from EC-001 §30 — verifies that the compiler selects the
  strongest satisfied profile (S1), skips unsatisfied profiles (S2), falls through to OOC (S3),
  is unaffected by profile ordering (S7), handles empty required_gaps (S10), rejects duplicate
  permission levels (S11), and can target all 12 permission levels via profiles (S12). 14 tests.

- **EC-036** (`ec036_token_liveness_and_freshness`): Token liveness and freshness semantics from
  EC-001 §11, §15, T2, T7 — exhaustively tests all five token status variants (Valid, Invalid,
  Expired, Revoked, Malformed) for gap contribution and EXP floor triggering, expiry boundary
  conditions, mixed token sets, context expiry vs token expiry interaction. 15 tests.

- **EC-037** (`ec037_serde_and_wire_format`): Serde round-trip and wire-format stability — verifies
  that Judgment, ProofContext, ProofToken, GapRecord, Expiry, RuntimeContext, and Derivation all
  round-trip through `serde_json` correctly; Permission serializes as UPPERCASE tags; TokenStatus
  and NegativeControlStatus serialize as SCREAMING_SNAKE_CASE; all 12 permission values survice
  JSON round-trip. 15 tests.

- **EC-038** (`ec038_scope_intersection_semantics`): Scope intersection semantics from EC-001 §22,
  T14 — verifies all four scope fields (candidates, paths, tools, resources), top semantics (empty
  list = unconstrained), commutativity, associativity, N-ary intersection equivalence, T14
  containment guarantee, and the monotone-narrowing invariant. 12 tests.

- **EC-039** (`ec039_derivation_and_audit_trail`): Derivation trail integrity and audit correctness
  from EC-001 §23, T18 — verifies that each compiler phase records the correct derivation step
  (D1–D6), steps are non-increasing in permission_after (D7), the final step matches the emitted
  permission (D8), `compiled_at` is set (D9), provenance hash matches context (D10), T18 holds
  (audit writes do not alter permission, D11), and derivation token_ids are accurate (D12). 12 tests.

- **EC-040** (`ec040_composition_identity_laws`): Composition identity laws and lax monoidal
  structure from EC-001 §24 — verifies compose-with-self idempotence (CI1–CI4), associativity of
  authority_ceiling, expiry, and disallowed_uses (CI5–CI7), left-fold equivalence with compose_n
  (CI8), right-associative equivalence (CI9), fail-closed behavior on UseConflict and TokenConflict
  (CI10–CI11), single-element compose_n identity (CI12), and end-to-end non-promotion. 14 tests.

- **EC-021** (`ec021_malformed_context_validation`): `MalformedContext` validation — V1–V8
  covering all four pre-flight rejection conditions: empty `allowed_use`, duplicate `gap_id`s,
  profile referencing an unknown `gap_id`, and duplicate permission levels in profiles.
  Proptest confirms `allowed_use` is always required. 16 tests.

- **EC-022** (`ec022_livejudgment_lifetime_guard`): `LiveJudgment<'ctx>` lifetime guard —
  L1–L8 covering the runtime T15 contract: `permission()` returns EXP on fingerprint
  mismatch, non-expired context returns stored permission, idempotent reads, strict-mode
  NC liveness. 11 tests.

- **EC-023** (`ec023_descending_order_stability`): `Permission::descending()` order stability
  — O1–O7 pinning the exact 12-element descending sequence
  `[AAA, ALR, AEX, REV, DIA, ROL, ESC, ETA, UNS, REF, EXP, OOC]`.
  Verifies `descending()[0] > descending()[1]`, round-trip through `as_str()`, and
  stability across 100 repeated calls. 9 tests.

- **EC-024** (`ec024_token_expiry_in_composition`): Token expiry masking in composition —
  X1–X6 documenting the dedup contract: when g1 and g2 carry the same `token_id` with
  identical content, the composed context keeps one copy; the earlier expiry is not masked
  by a later one; Revoked status is not upgraded to Valid. 6 tests.

- **EC-025** (`ec025_bound_variant_coverage`): `BoundKind` variant coverage — B1–B15
  exercising `Numeric`, `SetValued`, and `Infinity` across `PartialEq`, serde round-trip,
  `GapStatus` rank ordering, and bounding-token behavior in `compile()`. 19 tests.

- **EC-026** (`ec026_dead_token_expiry_semantics`): Dead-token expiry semantics — D1–D10
  verifying that only `status = Valid` tokens trigger the EXP floor in compiler step 5.
  `Invalid`, `Expired`, `Revoked`, and `Malformed` tokens with past `expires_at` do not
  cause EXP. Fixes a pre-existing bug where dead-token expiry silently downgraded outcomes.
  10 tests.

- **EC-027** (`ec027_compose_claim_id_semantics`): Compose `claim_id` / `candidate_id`
  semantics — C1–C8 documenting that `compose(g1, g2)` inherits g1's identity tuple; tokens
  issued for g2's tuple have wrong provenance in the composed context and are silently
  rejected. Fingerprint concatenation (`"fp-a+fp-b"`) also pinned. 8 tests.

- **EC-028** (`ec028_provenance_unicode_and_large_input`): Provenance hash unicode and large
  inputs — U1–U8 confirming NFC vs NFD produce distinct hashes, CJK characters are hashed
  over UTF-8 bytes, null bytes embedded in fields do not collide with the `\0` delimiter,
  1 MB inputs complete without panic, and `verify_provenance` is deterministic. 10 tests.

- **EC-029** (`ec029_poisoned_mutex_recovery`): Poisoned-mutex recovery — P1–P5 confirming
  `SchemaRegistry` and `InMemoryAuditStore` remain fully functional after a thread panic
  mid-write. New entries can be registered, `get_schema` returns existing entries, and
  `append` continues to accumulate audit records. 5 tests.

- **EC-030** (`ec030_compile_never_panics`): `compile()` and `compose()` never panic —
  N1–N13 exercising every identified panic surface: `NaN`/`+∞`/`-∞` in `Bound::Numeric`,
  1000-gap contexts, 1000-token contexts with one correct provenance, `compose_n` over
  200 contexts, profiles with 100 required gaps, and 10k-character field strings. 13 tests.

- **Python integration test suite** (`python/tests/`, 100 tests across 8 files):
  - `PY-001` — `Permission` ordering, meet commutativity/idempotence, `from_str`
    (case-insensitive), `hash`, `__eq__`. 17 tests.
  - `PY-002` — `compile()` basic outcomes: OOC, DIA, authority-ceiling truncation, all
    four `MalformedContext` conditions surfaced as `TurnstileError`. 13 tests.
  - `PY-003` — `LiveJudgment` runtime evaluation: `ExpiredError` raised on expired context
    and on fingerprint mismatch; `permission_str()` never raises; idempotence. 10 tests.
  - `PY-004` — `compose()` semantics: identity-field inheritance, g2-token rejection
    (provenance mismatch), `CompositionError` on use-mismatch, token deduplication. 10 tests.
  - `PY-005` — Timestamp precision: `as i64` truncation behavior documented; valid
    expired token triggers EXP floor; dead token does not; far-future and near-epoch
    timestamps handled without error. 11 tests.
  - `PY-006` — Exception hierarchy: all four exception types (`TurnstileError`,
    `ExpiredError`, `CompositionError`, `ProvenanceError`) reachable; message quality
    spot-checks. 11 tests.
  - `PY-007` — Data types: all `GapRecord`/`Membership`/`NegativeControlStatus` variants,
    `ProofToken` details and `is_negative_control`, `Scope` defaults,
    `compute_provenance_hash` determinism and field-order sensitivity. 18 tests.
  - `PY-008` — Derivation inspection: step types, `compiled_at` float, final step matches
    `Judgment.permission`. 10 tests.

### Fixed

- **`compiler.rs` — `validate_context()` pre-flight** (previously missing): `compile()`
  now returns `Err(TurnstileError::MalformedContext)` for four conditions that were
  previously silently degraded: empty `allowed_use`, duplicate `gap_id`s, a profile
  referencing an unknown `gap_id`, and duplicate permission levels across profiles.

- **`compiler.rs` — dead-token EXP floor** (step 5): The expiry blocker previously
  checked all tokens regardless of status. Dead tokens (`Invalid`, `Expired`, `Revoked`,
  `Malformed`) with a past `expires_at` incorrectly floored outcomes to EXP. The check
  now guards with `t.status.is_usable()` so only live (`Valid`) tokens with a past
  deadline can trigger the EXP floor.

- **`ec005_domain_admission.rs`** — tests A3 and A4 updated to reflect corrected
  `MalformedContext` semantics (previously documented silent-degradation behavior that is
  no longer correct).

- **`pyproject.toml`** — `classifiers` was incorrectly nested under `[project.urls]`
  (TOML parse error in maturin ≥ 1.4); moved to `[project]`. Adds
  `[tool.pytest.ini_options]` with `testpaths = ["python/tests"]` so `pytest` resolves
  tests without path arguments.

Total test count: **865 tests** — 765 Rust (65 files) + 100 Python (8 files).

## [0.1.1] - 2026-05-17

### Added

- **EC-006** (`ec006_profile_monotonicity_law`): Law G01 profile-monotonicity validator.
  `validate_profile_monotonicity()` detects configurations where a stronger permission
  declares weaker evidence requirements than a lower permission — a misconfiguration that
  can cause unexpected permission grants. 8 tests + proptest suite.

- **EC-007** (`ec007_derivation_chain_soundness`): Derivation chain soundness invariants.
  Every step in a compiled `Derivation` must be non-increasing in `permission_after`;
  the final step must equal `judgment.permission`; `compiled_at` is always `Some`;
  `provenance_hash` in the derivation always matches the compiled context. 9 tests + proptest.

- **EC-008** (`ec008_concurrent_audit_store`): Concurrent `InMemoryAuditStore` integrity.
  Verifies `Send + Sync` under 8–16 concurrent writer threads; no data loss, exact entry
  counts, and no panics under simultaneous read/write workloads. 4 tests.

- **EC-009** (`ec009_permission_from_str`): Exhaustive `Permission::from_str` coverage.
  All 12 codes in uppercase, lowercase, and mixed case; near-miss strings (`"DI"`, `"DIAA"`,
  `"D I A"`), empty string, whitespace, and numerics all return `None`. 11 tests.

- **EC-010** (`ec010_scope_candidate_admission`): Scope candidate admission (EC-001 rule
  [ADMISSIBLE]). Documents that the compiler does not enforce `z ∈ scope.allowed_candidates`
  and provides `validate_candidate_in_scope()` that callers must invoke before acting on a
  judgment. 10 tests + proptest.

- **EC-011** (`ec011_gap_composition_invariants`): `GapStatus::min_status` algebra.
  Rank commutativity (9 exhaustive pairs), associativity (27 exhaustive triples),
  `Open` absorbs all inputs, `Closed.min_status(Bounded) = Bounded`. Proptest confirms
  `rank(min(a, b)) == min(rank(a), rank(b))` universally. 16 tests.

- **EC-012** (`ec012_priority_tier_dominance`): Priority tier dominance (T8, T10).
  Exhaustive verification that higher-priority outcomes dominate lower tiers: OOC
  dominates all profiles, EXP dominates positive permissions, authority ceiling clips
  exhaustively for all 144 (profile, ceiling) pairs, disallowed-uses ROL ceiling applied
  correctly, tier ordering asserted for action vs control permissions. 12 tests.

- **EC-013** (`ec013_composition_fail_closed`): Composition fail-closed on all conflict types.
  UseConflict (differing allowed_use, symmetry), TokenConflict (same token_id with
  different type or issuer), identical token deduplication, EmptyComposition, compose_n
  identity, non-promotion guarantee over all (ceiling1, ceiling2) pairs. 10 tests.

- **EC-014** (`ec014_schema_registry_invariants`): `SchemaRegistry` append-only invariants R1–R7.
  First registration success, duplicate rejection, version isolation, retrieval
  correctness, current_version accuracy, all_entries completeness, concurrent
  registration safety (8 threads × 10 schemas), concurrent read/write non-panic,
  append-only persistence. 15 tests.

- **EC-015** (`ec015_disallowed_use_accumulation`): Disallowed-use accumulation (T13).
  Disjoint union, overlap deduplication, empty+non-empty identity, compose_n
  accumulation, ROL ceiling applied to non-empty lists, proptest: composed
  disallowed_uses ⊇ both inputs; non-empty always caps at ROL. 10 tests.

- **EC-016** (`ec016_compile_determinism`): Compiler determinism (Spec §8).
  Same context twice → identical permission and derivation; 1000 sequential calls;
  16-thread concurrent compilation under barrier; no wall-clock drift without expiry;
  serde round-trip preserves permission; structurally identical objects agree. 9 tests.

- **EC-017** (`ec017_error_coverage`): Error type coverage.
  Every `CompositionError` and `TurnstileError` variant is reachable; every variant
  carries correct data; Display/Debug output is non-empty; errors propagate through
  compose_n; `std::error::Error` is implemented. 12 tests.

- **EC-018** (`ec018_large_context_stress`): Large-context stress correctness.
  100 gaps all closed → DIA; 49/50 closed → OOC; compose_n of 20 contexts with
  non-promotion guarantee; 200 tokens with only 1 correct provenance → DIA; 500 open
  gaps → OOC; compose_n of 50 contexts verifies ceiling is meet of all inputs. 6 tests.

- **EC-019** (`ec019_t11_diagnostic_action_separation`): T11 diagnostic/action separation.
  DIA authority ceiling blocks all action permissions (AEX/ALR/AAA); symmetry of
  ceiling meet; all sub-DIA ceilings (ESC, ROL, ETA, REF, UNS) block action; OOC
  membership in compose input yields OOC; REV ceiling blocks action; meet lattice
  basis (144 pairs); composed authority ceiling equals meet of inputs. 9 tests.

- **EC-020** (`ec020_token_expiry_edge_cases`): Token and context expiry edge cases.
  Expired token floors when profile satisfied; future expiry does not floor; mixed
  expired+non-expired → any expired → EXP; no-expiry token never triggers EXP;
  context expiry boundary; future context expiry OK; Invalid/Revoked tokens do not
  trigger EXP floor; expired token for non-required gap still floors; LiveJudgment
  fires at exact boundary; LiveJudgment does not fire 1ms before deadline. 11 tests.

Total test count: **656 tests across 55 files** (up from 562 / 46).

## [0.1.0] - 2026-05-17

### Added

- `turnstile-core`: pure Rust admissibility compiler (`compile`, `compose`, `LiveJudgment<'ctx>`)
- Permission total order: `OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA < REV < AEX < ALR < AAA`
- `ProofContext` / `ProofToken` / `GapRecord` / `Profile` types
- SHA-256 provenance hashing with constant-time comparison
- `RuntimeContext` + `LiveJudgment<'ctx>`: borrow-checker-enforced expiry reads
- Negative-control token support (`is_negative_control`, T17 liveness check in strict mode)
- `AuditStore` trait + `InMemoryAuditStore` with full `Derivation` trail
- `Certifier` trait for domain token issuance and validation
- `turnstile-py`: PyO3 bindings exposing all core types to Python ≥ 3.10
- `turnstile-tests`: 417-test suite covering EC-003 (composition algebra, provenance,
  expiry, token status, OOC variants, evidence monotonicity, certifier interface),
  EC-004 (profile well-formedness), EC-005 (domain admission), and proptest
  property suites for the 4 structural guarantees
- Criterion benchmark harness: `out_of_class`, `single_gap_closed`, `six_gaps_closed`,
  `six_gaps_bad_provenance`
- CI: GitHub Actions matrix (ubuntu, macos), clippy `-D warnings`, rustfmt check,
  bench compile verification
