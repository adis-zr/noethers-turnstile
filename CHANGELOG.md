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

Total test count: **562 tests across 46 files** (up from 504 / 40).

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
