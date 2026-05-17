# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
