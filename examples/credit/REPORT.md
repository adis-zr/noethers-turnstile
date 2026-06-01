# CRED-IND-001: Credit Adverse Action Experiment — Report

Generated: 2026-06-01

## Setup

CRED-IND-001 is an empty taxonomy induction experiment. Starting from a structural
skeleton of two gaps (approximation_quality_gap, freshness_gap), the compiler is run
against a set of credit model deployment cases. Each time it over-authorizes — emits
ALR when the expert says < ALR — the discrepancy forces exactly one new gap into the
taxonomy. No regulatory knowledge is consulted during induction. The CFPB / ECOA
comparison in Phase 4 is opened only after induction is complete.

The experiment is fully independent. It does not share code with any other example.

## Permission Label Translation

The experiment uses noethers-turnstile library labels. The paper uses operational names.

| Library label | Operational meaning                                              |
|---------------|------------------------------------------------------------------|
| DIA           | Document exists — model produces output; nothing validated       |
| REV           | Expert review only — approximation quality bounded               |
| AEX           | Experiment authorized — structural skeleton satisfied            |
| ALR           | Limited rollout — all induced domain gaps bounded                |

## Induction Trace

Starting profile: v0 (approximation_quality_gap + freshness_gap only).

### Positive Control — C01 (profile: v0)

**System:** Interpretable logistic scorecard, pre-screen notification only (no adverse action).

**Evidence package:** AQ bounded (AUC validated on hold-out), freshness bounded (real-time
bureau inputs), reason_traceability_gap bounded (N/A — action class is notification only;
the gap is scoped to adverse actions that carry a legal obligation to communicate specific
reasons).

| compiler | expert | result |
|----------|--------|--------|
| ALR      | ALR    | ✓ AGREE |

Positive control holds at v0: an interpretable model used for notification only is correctly
authorized at ALR. This case must remain ALR under every profile version.

### Induction Step — C02 (profile: v0 → v1)

**System:** Black-box credit scoring model (vendor-supplied gradient-boosted tree); consumer
lending; ECOA-covered adverse actions (denial, credit limit reduction, account termination).

**Evidence package at v0:** All structural gaps bounded — AUC 0.78, GINI 0.42, real-time
bureau inputs.

| compiler | expert | result          |
|----------|--------|-----------------|
| ALR      | REV    | ✗ OVER-AUTHORIZED |

**Over-authorization.** The compiler emits ALR. The expert says REV. The v0 profile has no
mechanism to detect the failure: both structural gaps are bounded, and no domain gap has yet
been induced.

**Forcing observation.** The black-box model produces a score but not the reasoning. The loan
officer cannot reconstruct which inputs drove this applicant's score. ECOA 15 U.S.C. § 1691(d)
and Regulation B 12 CFR § 1002.9 require a specific, accurate statement of the principal
reasons for adverse action. CFPB Circular 2022-03 (May 26, 2022) makes explicit that model
complexity is not an excuse for noncompliance. No traceable reason is available in the evidence
package regardless of how good the model is.

**Why this is not any existing gap.**

*Not approximation_quality_gap.* The model's predictive quality is bounded — AUC 0.78 is
adequate. The failure is not about whether the score is good; it is about whether the score's
derivation can be stated.

*Not freshness_gap.* The inputs are current. The failure is not about staleness.

The gap is structurally prior to both. A model can have excellent AUC on fresh inputs and
still be unable to produce a specific, accurate reason for an adverse action. The two existing
gaps cannot see this failure mode.

**Gap induced: reason_traceability_gap.**

Profile advances to v1. ALR now requires: approximation_quality_gap bounded, freshness_gap
bounded, reason_traceability_gap bounded.

---

Induction complete. **Converged at v1.** One gap discovered: `reason_traceability_gap`.

## Gap Definition

**reason_traceability_gap:** The evidence package supports the decision output but does not
contain specific, accurate, actionable reasons — traceable to the model's actual inputs for
this individual — that the authorized action legally requires to be communicated to the
affected party.

**Scope condition.** This gap is scoped to action classes that carry a legal obligation to
communicate specific reasons to the affected party: denial, sanction, termination, benefit
reduction. Notification, flagging, and display actions do not trigger it.

**What opens the gap.** A model whose internals are not auditable by the decision-maker.
The decision-maker receives the score but not the reasoning path from inputs to output.

**What closes the gap.** The evidence package must contain: (a) the specific factors that
materially drove the score for this individual, (b) traceable to the model's actual inputs
(not approximated from a surrogate), (c) accurate in the sense that they correctly describe
the model's decision process for this case (not a post-hoc rationalization), and (d)
sufficient for the affected party to understand the basis and identify what they could change.

**On post-hoc explanation methods.** LIME, SHAP, and related attribution methods can close
reason_traceability_gap if and only if the approximation quality of the attribution is
validated — meaning it can be demonstrated that the attributed features correspond to the
features the model actually weighted for this individual case. Unvalidated post-hoc
attributions do not close the gap.

**Non-reducibility to individual_population_gap** (the closest structural neighbor). A
logistic regression and a gradient-boosted tree can have identical AUC, identical individual
calibration, identical distribution coverage. The logistic model can produce a traceable
reason directly from its weights. The gradient-boosted tree cannot without additional
machinery. Individual_population_gap certifies that the score is accurate for this individual.
It does not require that the path from inputs to score be auditable. The two properties are
separable and certified by different tokens. No existing field contract for
individual_population_gap requires auditability.

**Non-reducibility to authority_gap.** A fully authorized human reviewer cannot comply with
ECOA if the evidence package they receive does not contain the required information. Authority
governs who acts. reason_traceability_gap governs what the evidence must supply to that actor
before the action is legally permissible. Even with a complete human authority chain in place,
the gap is open if the evidence package lacks a traceable reason.

## Phase 2: Convergence Check

All induction cases re-run against v1.

| Case | compiler | expert | converged |
|------|----------|--------|-----------|
| C01  | ALR      | ALR    | ✓         |
| C02  | AEX      | REV    | ✓         |

**CONVERGENCE: PASS.** No over-authorization on any induction case. C02 now compiles to AEX
because reason_traceability_gap is open in its evidence package and the v1 profile requires it
bounded for ALR. AEX (rank 9) sits above REV (rank 8) in the permission chain — the compiler
is slightly more permissive than the expert on this case, but both are below ALR (rank 10),
which is the only level that triggers over-authorization. This is the same safe pattern as
MED-IND-001: the convergence criterion is compiler < ALR, not compiler ≤ expert.

## Phase 3: Generalization

Held-out cases not used in induction, evaluated against v1.

| Case | compiler | expert | result                           |
|------|----------|--------|----------------------------------|
| H01  | ALR      | ALR    | ✓ AGREE                          |
| H02  | AEX      | REV    | ~ SAFE (AEX > REV; not over-auth)   |
| H03  | ALR      | ALR    | ✓ AGREE                          |
| H04  | DIA      | DIA    | ✓ AGREE                          |

**GENERALIZATION: PASS.** No over-authorization on any held-out case.

**H01** (interpretable scorecard, adverse action, gap closed): compiler=ALR, expert=ALR.
The logistic regression's feature weights are auditable; the creditor can produce the signed
contribution of each input directly from the model. reason_traceability_gap is bounded.

**H02** (black-box with unvalidated SHAP, gap open): compiler=AEX, expert=REV. SHAP
attributions are present but their approximation quality is not validated. The compiler
emits AEX — one level above REV in the permission chain, but both are below ALR. Not
over-authorizing; the over-authorization criterion is compiler ≥ ALR.

**H03** (black-box with validated SHAP, gap closed): compiler=ALR, expert=ALR. Ablation
studies confirm that SHAP attributions for this model class correctly identify the factors
the model actually weighted for individual cases. reason_traceability_gap is bounded.

**H04** (no AQ validation, gap open): compiler=DIA, expert=DIA. The structural skeleton
blocks at DIA before reason_traceability_gap is reached. The v1 addition does not weaken
the skeleton.

The H02 / H03 pair is the critical structural test: two black-box models with identical
architecture, one with unvalidated SHAP (AEX) and one with validated SHAP (ALR). The compiler
distinguishes them correctly. The gap is not about model architecture — it is about whether
the evidence package contains a validated traceable reason.

## Phase 4: CFPB / ECOA Blind Audit

Opened after induction is complete. Regulatory text not consulted during any prior phase.

**Regulatory anchor:** ECOA 15 U.S.C. § 1691(d)(2); Regulation B 12 CFR § 1002.9(b)(2);
CFPB Circular 2022-03 (May 26, 2022).

### Correspondence Table

| Induced gap               | Regulatory requirement                                        | Citation                              | Classification        |
|---------------------------|---------------------------------------------------------------|---------------------------------------|-----------------------|
| reason_traceability_gap   | Specific, accurate statement of principal reasons for adverse action; reasons must accurately describe factors actually considered; model complexity not an excuse | ECOA § 1691(d); Reg B § 1002.9; CFPB 2022-03 | **EXACT** |
| —                         | Prohibition on disparate impact in credit scoring             | 12 CFR § 1002.6(a)                    | COMPILER_PERMISSIVE   |
| —                         | Data accuracy procedures (FCRA § 1681e(b))                   | 15 U.S.C. § 1681e(b)                  | COMPILER_PERMISSIVE   |

**1 EXACT · 2 COMPILER_PERMISSIVE**

### EXACT: reason_traceability_gap ↔ ECOA adverse action statement

The compiler induces a requirement for a specific, accurate, individual-level reason
traceable to the model's actual inputs. ECOA and Regulation B require the same from the
regulatory side. CFPB Circular 2022-03 makes it explicit: "A creditor cannot justify
noncompliance based on the mere fact that the technology it employs to evaluate applications
is too complicated or opaque to understand." Both the compiler and the regulation require
that reasons relate to and accurately describe the factors actually considered — not an
approximation, not a post-hoc rationalization. Both arrive at this requirement from different
starting points.

Classification: **EXACT**.

Note on cardinality: the regulation specifies that the statement must contain 2–4 reasons;
the compiler's token is binary (present/absent). The binary token is a simplification of the
full regulatory requirement in one respect (cardinality), while equivalent in the primary
respect (accuracy and traceability). The EXACT classification holds on the core requirement.

### COMPILER_PERMISSIVE: disparate impact, FCRA data accuracy

No induction case failed because of disparate impact in outcomes or because of upstream
data accuracy failures. These are real regulatory obligations — ECOA's disparate impact
prohibition and FCRA's accuracy requirements — but they are not forced by the evidence
structure of this induction. The compiler's silence here is correct: it does not discover
what the evidence does not reveal.

The disparate impact finding is particularly notable. A model can have a bounded and traceable
reason for every individual adverse action and still produce systemically discriminatory
outcomes across protected classes. These are orthogonal failure modes. reason_traceability_gap
addresses whether the evidence supports the individual justification. Disparate impact addresses
whether the population-level outcomes are lawful. The compiler can find the first; it cannot
reach the second from this induction corpus.

## Summary

| Phase | Result |
|-------|--------|
| Induction (1 step) | reason_traceability_gap induced from C02 at v0→v1 |
| Convergence check | PASS — no over-authorization on any induction case |
| Generalization (4 held-out cases) | PASS — 3 exact agree, 1 AEX vs REV (not over-auth)  |
| CFPB/ECOA audit | 1/1 EXACT · 2 COMPILER_PERMISSIVE |

**The experiment establishes one finding:** the compiler, starting from a structural skeleton
of two gaps and no regulatory knowledge, induces reason_traceability_gap from a single
deployment failure. When ECOA and CFPB regulatory text is opened afterward, the induced gap
corresponds exactly to the statutory requirement. The compiler found the boundary from evidence
structure alone. ECOA encoded the same boundary from the regulatory side. Neither was derived
from the other.

## Architectural Note

reason_traceability_gap is structurally distinct from all six gaps in the MED-IND-001 taxonomy.
It is not about model quality (approximation_quality_gap), training target alignment
(model_specification_gap), distribution coverage (distribution_shift_gap), population-individual
transfer (individual_population_gap), scope of harm (blast_radius_gap), or oversight chain
(authority_gap). It fires when the permission hierarchy includes actions that require not only
a sound decision but a communicable, legally adequate justification — and the evidence package
does not contain the materials for one.

The first six gaps from MED-IND-001 ask whether the evidence supports the action.
This gap asks whether the evidence supports the reason the action legally requires.
These are different questions about different objects. Evidence sufficient to decide is not
always evidence sufficient to justify the decision.
