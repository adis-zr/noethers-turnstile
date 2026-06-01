# EPIC: Blind Gap Induction from Medical AI Deployment Failures

**Experiment ID:** MED-IND-001

This example demonstrates the core claim of the noethers-turnstile paper: starting from a
two-gap structural skeleton and a corpus of documented deployment failures, a purely mechanical
induction loop discovers a six-gap taxonomy that covers 100% of FDA, NHS RCR, and EU AI Act
requirements — without consulting any of those frameworks during discovery.

## What it shows

The induction loop has no access to FDA guidance, NHS guidelines, or EU AI Act text.
It has no LLM. It has no domain expert in the loop. It receives only:

- A structural skeleton profile (v0): `approximation_quality_gap` + `freshness_gap`
- A corpus of deployment failures with gap statuses reconstructed from public evidence

Each time the compiler over-authorizes — emits ALR when the domain expert says < ALR —
the loop reads the case's blocking gaps and adds the first OPEN gap not yet in the taxonomy.
After 6 cases the taxonomy is complete. The FDA/NHS/EU AI Act comparison is opened only
after induction finishes.

## Results

| Phase | Result |
|---|---|
| Induction (6 steps) | 6 gaps discovered: `clinical_utility_gap`, `model_specification_gap`, `distribution_shift_gap`, `individual_population_gap`, `blast_radius_gap`, `authority_gap` |
| Convergence check | PASS — no over-authorization on any induction case |
| Generalization (5 held-out cases) | PASS — no over-authorization |
| FDA 2025 coverage | 4/4 requirements (100%) |
| NHS RCR 2024 coverage | 4/4 requirements (100%) |
| EU AI Act 2024 coverage | 4/4 requirements (100%) |

## Running

```bash
# From repo root:
python examples/epic/run_induction.py     # main induction + regulatory audit
python examples/epic/run_stress.py        # adversarial attacks + TCB boundary map
python examples/epic/run_synthetic.py     # synthetic probe (experiments A–F)
python examples/epic/run_demo.py          # short demo
```

## Structure

```
experiment/
  cases.py              Induction corpus (M01–M07) and held-out cases (H01–H05)
  compiler.py           ProofContext builder for each case
  profile.py            InductionState — version tracking, gap registry
  induction.py          run_induction(), run_convergence_check(), run_generalization_check()
  fda_nhs_audit.py      Post-hoc regulatory comparison (FDA/NHS/EU AI Act)
  stress/
    adversarial.py      10 attack vectors (A1–A10) against the converged v6 profile
    hidden_gaps.py      Falsified statuses (2a) and omitted gaps (2b)
    tcb_corruption.py   TCB surface map (T1–T6): what the compiler accepts on faith
    tamper_resistance.py Composition tamper tests (R1–R6)
  synthetic/
    world.py            Synthetic world generator W(k, p, n, seed)
    experiments.py      Experiments A–F: recovery, coverage, order independence, minimality
adapter/                Domain bridge to noethers-turnstile
acs/                    Admissibility compiler wrapper
```

## Failure corpus cases

| Case | System | Gap induced |
|---|---|---|
| M01 | Positive control — interpretable model, basic validation | — |
| M02 | Epic Sepsis Model — AUC validated, clinical utility never tested | `clinical_utility_gap` |
| M03 | Optum health risk scoring — cost proxy diverges from care-need target | `model_specification_gap` |
| M04 | PredPol predictive policing — self-reinforcing feedback loop | `distribution_shift_gap` |
| M05 | COMPAS recidivism — population statistics license individual detention | `individual_population_gap` |
| M06 | Watson Oncology — high-stakes recommendations without blast radius bound | `blast_radius_gap` |
| M07 | Dutch childcare benefit algorithm — automated AAA action without authority bound | `authority_gap` |

## Full report

`experiment/REPORT.md` — design rationale, induction trace, regulatory alignment analysis.
