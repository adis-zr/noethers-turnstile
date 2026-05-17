# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
