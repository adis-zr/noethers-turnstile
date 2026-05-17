# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
