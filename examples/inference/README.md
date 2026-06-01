# Inference: Probabilistic Inference Compiler Benchmarks

This example validates the noethers-turnstile compiler against a range of probabilistic
inference problems. It tests that the compiler's permission outputs are physically grounded —
transitions occur at the right evidence thresholds, not at arbitrary values.

150 pytest tests across six test files. All pass with no data downloads required for the
core test suite (Ising, 3GPP turbo, and UAI tests are self-contained; named Bayesian
network tests skip gracefully if BIF files are absent).

## Running

```bash
# From repo root:
.venv/bin/python -m pytest examples/inference/tests/ -v

# Or from within the example directory:
cd examples/inference
../../.venv/bin/python -m pytest tests/ -v
```

## Domains

### Ising model (`ising/`)

Random Ising grids on a 2D lattice. Belief propagation degrades above the critical
coupling β_c; mean field degrades earlier. Tests verify:

- BP error degrades at β_c (reproducible known result)
- Mean field degrades at a lower threshold than BP
- Compiler permission transitions match the physical degradation boundary
- Full pipeline: generate grid → run BP/exact → compute TV → compile()

### UAI benchmark networks (`uai/`)

UAI format factor graph files. Tests verify:

- Parser correctness on real UAI files
- BP runs without error on benchmark instances
- Compiler failure vectors map to correct permissions
- Bethe free energy is finite and physically meaningful
- Permission outputs are internally consistent

### Named Bayesian networks (`named/`)

Classic networks (ALARM, MUNIN1). Tests verify:

- ALARM TV falls in Murphy (1999) reported range
- MUNIN1 TV shows expected non-trivial error
- Full pipeline: BIF → factor graph → BP → exact → TV → compile()
- Compiler threshold scan on real networks matches Tier 1 structure

Tests skip gracefully if BIF files are not present locally.

### 3GPP turbo codes (`register2/turbo/`)

Blind audit of 3GPP TS 36.212 turbo code BLER curves across SNR. Tests verify:

- Layer 1: Blind chain correctness — 5-level compiler structure
- Layer 2: Natural boundary extraction — transitions are physically grounded
- Layer 3: Phase A / Phase B consistency — gap persists across chain choice
- Layer 4: Audit table structure — 6-column spec, correct classification logic

### Benchmarks (`benchmarks/`)

Scaling and density sweeps. Run with:

```bash
cd examples/inference && bash benchmarks/run_all.sh
```

Generates scaling figures and CSV results in `benchmarks/results/` and `figures/`.

## Structure

```
ising/
  run_bp.py / run_exact.py / run_mf.py    Inference kernels
  run_ising.py                            Full sweep entry point
  run_threshold_sweep.py                  Compiler threshold scan
  generate_ising.py                       Grid generator
uai/
  compiler_uai.py                         UAI → compile() adapter
  parse_uai.py                            UAI file parser
  run_bp_uai.py                           BP on UAI instances
named/
  run_named.py                            Named network sweep
  bif_to_factor_graph.py                  BIF → factor graph converter
register2/turbo/
  ber_bler_curves.py                      3GPP published BER/BLER data
benchmarks/
  scaling/                                mn surface + problem size sweeps
  compiler.py                             Compiler kernel for benchmarks
  run_all.sh                              Single entry point for all benchmarks
tests/
  test_ising.py            38 tests — Ising model (3 layers)
  test_uai.py              26 tests — UAI benchmark networks (3 layers)
  test_named.py            16 tests — Named Bayesian networks (3 layers)
  test_audit_3gpp.py       23 tests — 3GPP turbo blind audit (4 layers)
  test_turbo.py            26 tests — Turbo code BER/BLER curves
  test_sensitivity_bler.py 21 tests — BLER sensitivity and bias model behavior
conftest.py              Inserts workspace python/ on sys.path
```
