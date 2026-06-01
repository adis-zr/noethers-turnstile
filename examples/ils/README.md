# ILS: Blind Recovery of FAA CAT I Approach Boundary

**Experiment ID:** ILS-AUD-001

This example runs a blind audit of Instrument Landing System (ILS) approach minima.
Pre-registration is sealed before any FAA document is opened. The compiler is run
on geometric sweeps derived purely from ILS physics. FAA thresholds are compared
only after the sweeps complete.

## What it shows

The RVR threshold where visual reference (f2) is achievable at Decision Height 200 ft
is determined entirely by ILS geometry: glideslope angle, TCH, roll-bar distance,
approach speed. The compiler transition at 1800 ft matches the FAA CAT I minimum
exactly. Higher CAT boundaries (CAT II–IIIc) require evidence types the geometry
alone cannot supply (human-factors reaction time, autoland certification, operator
qualification) — the compiler correctly identifies these as absent from its evidence
space rather than emitting wrong thresholds.

## Results

| FAA category | FAA RVR (ft) | Compiler (ft) | Classification |
|---|---|---|---|
| CAT I | 1800 | 1800 | EXACT |
| CAT II | 1200 | — | OFFSET_DIFFERENT_AXIS |
| CAT IIIa | 700 | — | COMPILER_PERMISSIVE |
| CAT IIIb | 150 | — | COMPILER_PERMISSIVE |
| CAT IIIc | none | — | COMPILER_PERMISSIVE |

## Running

```bash
# From repo root:
python examples/ils/run_ils_audit.py

# Re-run from scratch (deletes and re-seals pre-registration):
python examples/ils/run_ils_audit.py --force
```

## Structure

```
geometry.py           ILS physical constants and derived geometric quantities
profiles.py           ACS gap profiles: f1 (signal integrity), f2 (visual ref), f3 (sub-CAT-I auth)
ils_compiler.py       ProofContext builder from approach state → compile()
sweeps.py             Sweep A (f3 absent) and Sweep B (f3 present) over RVR range
preregistration.py    Sealed pre-registration writer and verifier
faa_comparison.py     Post-hoc FAA threshold comparison and classification
run_ils_audit.py      Orchestrator: seal → sweeps → compare → REPORT.md
```

## Pre-registration

The pre-registration file (`preregistration.json`) and seal (`preregistration.seal`)
are committed. They record all geometric predictions before any FAA source is
consulted. The seal is a SHA-256 hash of the JSON. `run_ils_audit.py` verifies
the seal before running sweeps; use `--force` only if intentionally re-running
from scratch.

## Full report

`REPORT.md` — geometric constants, sweep tables, FAA correspondence, explanations
for each classification.
