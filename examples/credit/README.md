# Credit: Blind Recovery of ECOA Adverse-Action Requirement

**Experiment ID:** CRED-IND-001

This example applies the noethers-turnstile induction loop to credit adverse-action decisions.
Starting from a two-gap structural skeleton, one induction step recovers the ECOA
reason-traceability requirement without consulting CFPB, ECOA, or Regulation B during induction.

## What it shows

A black-box credit scoring model that cannot supply a specific, accurate, individual-level
reason traceable to the applicant's actual inputs fails at case C02. The compiler
over-authorizes (emits ALR; the expert says REV). The induction loop reads the blocking
gap — `reason_traceability_gap` — and adds it to the profile. The CFPB/ECOA comparison
is opened only after the taxonomy is complete.

## Results

| Phase | Result |
|---|---|
| Induction (1 step) | `reason_traceability_gap` discovered |
| Convergence check | PASS |
| Generalization (4 held-out cases) | PASS — no over-authorization |
| ECOA § 1691(d) / Regulation B § 1002.9 | EXACT match |
| CFPB Circular 2022-03 | EXACT match (accuracy + traceability) |
| COMPILER_PERMISSIVE items | 2 (disparate impact, FCRA accuracy — outside evidence induction can reach) |

## Running

```bash
# From repo root:
python examples/credit/run_credit_audit.py
```

## Structure

```
experiment/
  cases.py              Induction corpus (C01–C02) and held-out cases (H01–H04)
  compiler.py           ProofContext builder for each case
  profile.py            InductionState — version tracking, gap registry
  induction.py          run_induction(), run_convergence_check(), run_generalization_check()
  cfpb_audit.py         Post-hoc CFPB/ECOA/Regulation B comparison
```

## Induction cases

| Case | System | Gap induced |
|---|---|---|
| C01 | Positive control — interpretable scorecard with traceable reasons | — |
| C02 | Black-box credit scoring — adverse action requires specific, traceable reason; model cannot supply it | `reason_traceability_gap` |

## Full report

`REPORT.md` — induction trace, CFPB/ECOA alignment analysis, permission label translation.
