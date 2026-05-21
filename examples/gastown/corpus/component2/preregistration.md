# Component 2 Pre-Registration
**Locked:** de45ec1
**Date:** 2026-05-21
**Based on Component 1 results:** de45ec1 (`corpus/component1/results.json`)

## Basis

Component 1 CLEAN trace ALR rate:            80.0%
Component 1 CLEAN trace REV rate:             0.0%
Component 1 CLEAN trace DIA rate:             0.0%
context_integrity_gap CLOSED rate (CLEAN):  100.0%
context_integrity_gap BOUNDED rate (CLEAN):   0.0%
completion_evidence_gap CLOSED rate (CLEAN): 100.0%

CLEAN traces (n=50) represent fully-closed gap profiles — mayor or polecat role, CI gate
present, provenance clean, no failed resolution. 80% emit ALR (polecat role); 20% emit AAA
(mayor role). No CLEAN trace emits below ALR. This is the upper bound: any real G1–G5 run
that introduces approximation pressure should produce fewer ALR judgments and more REV/DIA.

## Per-Run Permission Predictions

Thresholds derived from Component 1 CLEAN base rate (ALR=80%) adjusted downward for expected
approximation pressure at each gradient position. The CLEAN base rate is the ceiling; each
gradient step opens the completion_evidence_gap further, reducing ALR reachability.

| Run | Predicted dominant permission | Threshold   | Primary gap driver if restricted         |
|-----|-------------------------------|-------------|------------------------------------------|
| G1  | ALR                           | ≥ 85%       | context_integrity_gap (seance staleness) |
| G2  | ALR                           | ≥ 75%       | completion_evidence_gap (AI strategy)    |
| G3  | ALR                           | ≥ 70%       | completion_evidence_gap (integration tests) |
| G4  | ALR (backend) / REV (frontend)| ALR ≥ 65%   | completion_evidence_gap (no frontend CI) |
| G5  | REV or DIA                    | ≥ 60% below ALR | completion_evidence_gap OPEN (subjective) |

**Note on G1 threshold exceeding CLEAN base rate:** G1 is a pure library task where the CI
gate reliably closes the completion_evidence_gap. The threshold (85%) is higher than the raw
CLEAN polecat rate (80%) because G1 traces are expected to be structurally cleaner than the
average CLEAN synthetic — no mixed mayor/polecat population, and context_integrity is expected
to close via a tighter seance window.

## Gradient Invariant

The following gap status distributions are predicted to be stable across G1–G5. Significant
variation (> 20% deviation from G1 baseline) constitutes falsification of the invariant.

- `context_integrity_gap` — depends on GasTown session structure, not task type. Expected:
  rate tracks CLEAN baseline (closed ≈ 100% where seance staleness is within bounds).
- `delegation_authority_gap` — depends on Mayor convoy assignment, not artifact complexity.
  Expected: closed or bounded depending on whether sling is mayor-authorized.
- `authority_chain_gap` — depends on sling provenance chain, not task type. Expected: closed
  when authority chain is complete; insensitive to G1→G5.

Component 1 CLEAN gap rates (reference baseline):
  context_integrity_gap:   closed=100%
  delegation_authority_gap: closed=100%
  authority_chain_gap:      closed=100%

## Falsification Conditions

| ID  | Prediction                                   | Falsified by                              |
|-----|----------------------------------------------|-------------------------------------------|
| F1  | G1 dominant permission: ALR ≥ 85%            | G1 majority REV or lower                 |
| F2  | G5 dominant permission: REV or DIA ≥ 60%     | G5 majority ALR                           |
| F3  | completion_evidence_gap is gradient driver   | Uniform CEG distribution across G1–G5    |
| F4  | context_integrity_gap gradient-stable        | CIG varies > 20% from G1 baseline        |
| F5  | delegation_authority_gap gradient-stable     | DAG varies > 20% from G1 baseline        |
| F6  | Profile detects gradient                     | Uniform permission distribution G1–G5    |

A falsified prediction is reported in §6.10 with root-cause classification:
- **Profile miscalibration** — gap profile requirements do not reflect GasTown's real behavior
- **Taxonomy gap** — real-world trace pattern has no corresponding gap type in Θ_GT_v1
- **GasTown behavioral finding** — GasTown's process structure differs from the synthetic model

## Signatures

Pre-registration author: Adi Sriram
No Component 2 trace has been collected at time of this commit.
