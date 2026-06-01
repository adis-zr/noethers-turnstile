# MED-IND-001: Empty Taxonomy Experiment — Report

## What This Experiment Demonstrates

This is the autonomous gap discovery experiment for medical AI. It is the medical counterpart to LEG-001 (legal research admissibility), with one critical difference: the induction is fully automated. No human judgment is applied during the loop. The compiler is the only oracle.

The central claim: **starting from a two-gap structural skeleton and a corpus of documented deployment failures, a purely mechanical induction loop discovers a six-gap taxonomy that covers 100% of FDA, NHS, and EU AI Act requirements — without consulting those frameworks at any point during discovery.**

The regulatory comparison is performed last, as a post-hoc audit. It is never an input.

---

## The Design Principle

The induction loop operates as follows:

1. Start with a structural skeleton profile (`v0`): two gaps — `approximation_quality_gap` and `freshness_gap`. Any in-class system with basic validation (`AQ` bounded) and current inputs (`freshness` bounded) emits ALR. The profile has no domain knowledge.

2. Run each case from the failure corpus against the current profile.

3. If the compiler over-authorizes — emits ALR when the domain expert says < ALR — find the first OPEN gap in the case's `blocking_gaps` list that is not yet in the taxonomy. Add it to the ALR requirement table. Advance the profile version.

4. Move to the next case.

5. After all induction cases, re-run everything against the converged taxonomy. Verify no over-authorization remains.

The loop has no access to FDA guidance, NHS guidelines, or EU AI Act text. It has no LLM. It has no domain expert in the loop. The gap statuses on each case — reconstructed from public evidence — are the only domain knowledge that enters.

### Why no LLM

An LLM would introduce circularity: every major LLM has read FDA and NHS guidance. Asked to identify the gap in a clinical AI failure, it would name `clinical_utility_gap` because that is in its training data, not because the compiler forced the conclusion. The result would be indistinguishable from retrieval of pre-existing knowledge.

The experiment's claim requires that the taxonomy emerge from compiler feedback alone. The cases encode public evidence about what was OPEN at deployment. The compiler signals over-authorization. The gap name comes from the case record. No external oracle is consulted.

---

## File Structure

```
examples/medical/experiment/
  cases.py           6 induction cases + 5 held-out cases from CASE-LIB-001
  profile.py         InductionState, build_profiles() — grows with each induction step
  compiler.py        compile_case() — ProofContext builder + compiler bridge
  induction.py       run_induction(), run_convergence_check(), run_generalization_check()
  fda_nhs_audit.py   post-hoc regulatory audit — never consulted during induction
  REPORT.md          this file
examples/medical/
  run_induction.py   CLI entry point, formatted report
```

---

## The Permission Hierarchy

```
DIA  — model exists and produces output; nothing else known
REV  — approximation quality bounded; suitable for expert review
AEX  — structural skeleton satisfied; experiment-authorized
ALR  — all domain gaps bounded; authorized for limited rollout
AAA  — full authority (ceiling; not used in this experiment)
```

Over-authorization is defined as: compiler emits ALR when the domain expert says < ALR. The induction signal fires exactly when this condition holds.

---

## Profile Design

Domain gaps enter ALR only, never AEX. This is the same invariant as LEG-001.

AEX remains reachable with the structural skeleton alone throughout induction. The consequence: at every profile version, a system with structural evidence but open domain gaps yields AEX, not ALR. The over-authorization signal is always "compiler emits ALR, expert disagrees" — the undiscovered gap is visible at the ALR boundary and invisible below it.

| Profile | REV | AEX | ALR |
|---------|-----|-----|-----|
| v0 | AQ ≥ bounded | AQ + freshness ≥ bounded | ← same as AEX |
| v1 | same | same | + `clinical_utility_gap` ≥ bounded |
| v2 | same | same | + `model_specification_gap` ≥ bounded |
| v3 | same | same | + `distribution_shift_gap` ≥ bounded |
| v4 | same | same | + `individual_population_gap` ≥ bounded |
| v5 | same | same | + `blast_radius_gap` ≥ bounded |
| v6 | same | same | + `authority_gap` ≥ bounded |

---

## The Six Induced Gaps

### Step 1 — `clinical_utility_gap` (induced by M02: Epic Sepsis Model)

*Reference: Wong et al. (2021), JAMA Internal Medicine 181(8):1065–1070*

The Epic Sepsis Model was deployed with AUC = 0.76 — a reasonable approximation quality result. Under v0, the compiler emits ALR: `AQ` bounded, `freshness` bounded, nothing else tracked. Expert judgment: REV at most.

The failure: at the deployed alert threshold, sensitivity = 0.33 and PPV = 0.12. The model missed two of every three sepsis cases and generated eight false alerts per true positive. This information was not disclosed at deployment and was discovered only by external validation three years later.

AUC is an aggregate measure across all thresholds. It says nothing about sensitivity or PPV at the specific threshold where nurses will act. A model can have AUC = 0.95 and PPV = 0.05 at its deployed threshold. The v0 profile had no representation of this distinction — it could not see it.

**Gap induced:** `clinical_utility_gap` — the model's operating-point metrics (sensitivity, PPV, NPV, specificity) at the intended clinical threshold and blast radius must be bounded before ALR is reachable.

---

### Step 2 — `model_specification_gap` (induced by M03: Optum racial bias)

*Reference: Obermeyer et al. (2019), Science 366(6464):447–453*

The Optum health risk algorithm accurately predicted healthcare costs — its stated training target. Under v1, the compiler emits ALR: `AQ` bounded, `freshness` bounded, `clinical_utility` bounded (cost prediction utility was demonstrated). Expert judgment: REV.

The failure: the action target was not cost prediction. The algorithm was used to identify patients who *need* more care, and it enrolled them in high-risk care management programs. Cost is a proxy for need — but Black patients have lower healthcare costs than equally sick White patients due to access barriers. The proxy diverges systematically on the protected class. Obermeyer et al. found the algorithm assigned the same risk score to Black patients who were significantly sicker than White patients at that score level.

The v1 profile had no representation of the training-target / action-target distinction. A model can be certified excellent at predicting its stated training target while being entirely unfit for the clinical or operational action it is used to drive.

**Gap induced:** `model_specification_gap` — the training target must be adequate for the action target. Certification that the model predicts X well does not certify that X is the right thing to predict for action Y.

---

### Step 3 — `distribution_shift_gap` (induced by M04: PredPol predictive policing)

*Reference: Lum & Isaac (2016), Significance 13(5):14–19; Ensign et al. (2018), FAT\**

PredPol accurately predicted reported crime locations in its training data. Under v2, the compiler emits ALR: all currently tracked gaps are bounded (model's stated target was accurately achieved). Expert judgment: REV.

The failure has two layers. The surface layer: the model was trained on reported crime — which is a function of policing patterns, not actual crime — and deployed to predict where crime will occur. The deeper layer: increased policing in predicted areas generates more reported crime there, which updates the model to predict more crime there, which sends more police. This is a self-reinforcing loop. Standard distribution shift analysis cannot detect it because the model remains accurate on its own (self-generated) training distribution at every time step. The evidence base for future certificates is endogenous to the model's outputs.

The v2 profile had no requirement that the model's performance be validated on a population whose composition is independent of the model's own past outputs.

**Gap induced:** `distribution_shift_gap` — the model's performance must be validated on the deployment population, not just the training population, and the validation population must not be endogenous to the model's own deployment history.

---

### Step 4 — `individual_population_gap` (induced by M05: COMPAS recidivism)

*Reference: Angwin et al. (2016), ProPublica; Dressel & Farid (2018), Science Advances 4(1):eaao5580*

The COMPAS recidivism score had reasonable population-level AUC and was roughly calibrated across risk levels within racial groups. Under v3, the compiler emits ALR. Expert judgment: REV.

The failure is structural, not empirical. COMPAS scores were used to influence bail, sentencing, and parole decisions for individual defendants. A score calibrated to population recidivism rates — even a perfectly calibrated one — does not certify whether *this individual* will reoffend. Population-level calibration is not individual-level predictive validity. This gap cannot be closed by improving AUC, enlarging the training set, or improving distribution shift validation. It is a category difference in what a population score licenses.

Dressel and Farid (2018) found COMPAS was no more accurate than untrained humans given the same information. ProPublica found Black defendants were labeled high risk at twice the rate of White defendants when they did not reoffend. Both findings are downstream of the same root: a population score was treated as individual certification.

The v3 profile had no representation of this category distinction.

**Gap induced:** `individual_population_gap` — a model that accurately characterizes population-level outcomes must separately certify its adequacy for individual high-stakes decisions. Population-level validation is a necessary but not sufficient condition for individual-level authorization.

---

### Step 5 — `blast_radius_gap` (induced by M06: IBM Watson for Oncology)

*Reference: Ross & Swetlitz (2018), STAT News; Strickland (2019), IEEE Spectrum*

Watson for Oncology was stipulated (for this induction step) to have passed all previously induced gaps — validation was complete, target was appropriate, deployment population was covered, individual-level certification was in place. Under v4, the compiler emits ALR. Expert judgment: AEX.

The failure: even with all validation complete, treatment recommendations at global scale — deployed to 230 hospitals in countries with different cancer subtypes, treatment availability, and clinical guidelines — require formal bounding of the downstream action scope. Internal IBM documents showed "unsafe and incorrect" treatment recommendations in multiple cancer types. Clinicians at several sites reported difficulty overriding the system's recommendations; the authority structure created pressure to follow outputs regardless of their adequacy.

The scope of consequential action that a model output licenses — what actions will be taken, at what scale, with what override mechanisms — must be bounded as a condition of ALR, not assumed from validation results alone.

**Gap induced:** `blast_radius_gap` — the scope of downstream actions licensed by each model output must be formally bounded. A high-stakes action at global scale with unclear override mechanisms requires an explicit blast-radius contract before ALR is reachable.

---

### Step 6 — `authority_gap` (induced by M07: Dutch childcare fraud algorithm)

*Reference: Van Bree et al. (2021), Dutch Parliamentary Inquiry "Unprecedented Injustice"*

All five previously induced gaps were stipulated bounded. Under v5, the compiler emits ALR. Expert judgment: AEX.

The failure: the Dutch Tax Authority's fraud detection algorithm generated automatic repayment demands for childcare benefits — ranging to tens of thousands of euros — with no meaningful human review, no explanation of the algorithmic basis, and no accessible appeals process. Approximately 26,000 families were wrongly accused of fraud; families were bankrupted; children were placed in foster care in some cases. The Dutch government resigned in January 2021. The European Parliament subsequently cited this case as a trigger for the EU AI Act.

The system exercised AAA-level authority — irreversible, high-stakes, mass-scale financial action — with zero oversight contract. No mechanism existed to bound what decisions the system could make autonomously versus what required human confirmation.

**Gap induced:** `authority_gap` — the scope of autonomous decision-making must be explicitly bounded. A system must not exercise authority beyond what is bounded by an oversight contract specifying: which decisions require human confirmation, what explanation is owed to affected parties, and what recourse is available.

---

## Phase 1: Induction Trace

```
[POSITIVE CONTROL]  M01  (v0)
  ✓  compiler=ALR   expert=ALR
     Structural skeleton sufficient for a well-validated, low-blast-radius notification tool.

[INDUCTION STEP]  M02  (v0 → v1)
  ✗  OVER-AUTHORIZED: compiler=ALR   expert=REV
     GAP INDUCED: clinical_utility_gap
     Epic Sepsis Model: AUC=0.76, PPV=0.12 at deployed threshold — invisible to v0.

[INDUCTION STEP]  M03  (v1 → v2)
  ✗  OVER-AUTHORIZED: compiler=ALR   expert=REV
     GAP INDUCED: model_specification_gap
     Optum: cost prediction certified; care-need action target not certified.

[INDUCTION STEP]  M04  (v2 → v3)
  ✗  OVER-AUTHORIZED: compiler=ALR   expert=REV
     GAP INDUCED: distribution_shift_gap
     PredPol: self-reinforcing feedback loop invisible to training-population validation.

[INDUCTION STEP]  M05  (v3 → v4)
  ✗  OVER-AUTHORIZED: compiler=ALR   expert=REV
     GAP INDUCED: individual_population_gap
     COMPAS: population recidivism rates used to license individual liberty decisions.

[INDUCTION STEP]  M06  (v4 → v5)
  ✗  OVER-AUTHORIZED: compiler=ALR   expert=AEX
     GAP INDUCED: blast_radius_gap
     Watson Oncology: global deployment at treatment-decision scale without action scope contract.

[INDUCTION STEP]  M07  (v5 → v6)
  ✗  OVER-AUTHORIZED: compiler=ALR   expert=AEX
     GAP INDUCED: authority_gap
     Dutch childcare: AAA-level financial action with zero oversight contract.
```

Six cases. Six over-authorizations. Six gaps induced. Profile advances from v0 to v6.

---

## Phase 2: Convergence

After v6, no induction case over-authorizes.

```
  M01  compiler=AEX   expert=ALR    converged ✓
  M02  compiler=AEX   expert=REV    converged ✓
  M03  compiler=AEX   expert=REV    converged ✓
  M04  compiler=AEX   expert=REV    converged ✓
  M05  compiler=AEX   expert=REV    converged ✓
  M06  compiler=AEX   expert=AEX    converged ✓
  M07  compiler=AEX   expert=AEX    converged ✓
```

Note: M01 (positive control) now emits AEX rather than ALR. At v6, ALR requires all six domain gaps bounded. M01 supplies only the structural skeleton. This is correct: the converged profile requires domain evidence; a case that does not present it cannot reach ALR. With full domain-gap evidence supplied, M01 would emit ALR. The positive control's role was to verify the v0 floor — it did.

The residual gap between compiler (AEX) and expert (REV) on M02–M05 mirrors the residual in LEG-001. The compiler signals "unverified on domain gaps"; a domain expert signals "this is known-inadequate." The compiler cannot say a deployment is *wrong*, only *unverified*. That distinction requires a domain judgment the compiler does not and should not make. The certifier boundary sits exactly there.

---

## Phase 3: Generalization

Five held-out cases not used in induction, tested against v6.

```
  H01  All gaps bounded — positive control           ALR   ✓  (exact agreement)
  H02  Boeing 737 MAX MCAS                           REV   ✓  (exact agreement)
  H03  COVID-19 ML models — all gaps open            DIA   ✓  (exact agreement)
  H04  Amazon recruiting tool                        AEX   ~  (expert: REV; no over-authorization)
  H05  Allegheny Family Screening Tool               AEX   ~  (expert: REV; no over-authorization)
```

**3 of 5 exact agreement. 5 of 5 no over-authorization.**

H01 (all gaps bounded) correctly reaches ALR under v6 — confirming the converged profile does not over-refuse well-evidenced deployments.

H02 (Boeing 737 MAX MCAS) reaches REV: `model_specification_gap` and `authority_gap` and `blast_radius_gap` are open. The compiler correctly recognizes an automated control system that overrode pilot inputs without annunciation or authority limit as REV-level at best.

H03 (COVID-19 models, Roberts et al. systematic review) reaches DIA: `approximation_quality_gap` is open, blocking everything above DIA. Roberts et al. found none of the 300+ models fit for clinical use; the compiler halts at the first gate.

H04 (Amazon recruiting) and H05 (AFST) land at AEX where experts say REV. This is the same residual as LEG-001 and M02–M05 at convergence: multiple domain gaps are open, the compiler correctly refuses ALR, but it signals "unverified" rather than "known-wrong." An expert who knows the specific failure mode says REV. A compiler that only sees which gaps are open says AEX. This is correct behavior and a structural property of the framework, not a failure.

---

## Phase 4: Post-Hoc Regulatory Audit

The discovered taxonomy was compared against three independent regulatory frameworks after induction completed. These frameworks were never consulted during the experiment.

**Result: 12/12 requirements covered. 0 uncovered. 0 novel gaps.**

### FDA Draft Guidance (January 2025)

| Requirement | Section | Covered by |
|---|---|---|
| Operating-point metrics (sensitivity, PPV with 95% CIs at clinical threshold) | Appendix C | `clinical_utility_gap` |
| Training/validation population disclosure; subpopulation performance | §5 / Appendix C | `distribution_shift_gap`, `model_specification_gap` |
| Real-world performance monitoring plan before deployment | §6 / PMA conditions | `authority_gap` |
| Intended use must specify clinical action, not just prediction task | §4 | `model_specification_gap` |

FDA Appendix C's core requirement — operating-point metrics at the clinically intended threshold, not just summary AUC — maps directly to `clinical_utility_gap`, which was discovered from the Epic Sepsis Model failure. FDA wrote their guidance partly in response to exactly that failure mode.

### NHS Royal College of Radiologists (November 2024)

| Requirement | Section | Covered by |
|---|---|---|
| Shadow mode before go-live; local performance data collected | §4.21 | `distribution_shift_gap` |
| Enriched local population test set required | §4.22 | `distribution_shift_gap`, `individual_population_gap` |
| Post-implementation evaluation plan before deployment | §2.13 | `authority_gap` |
| Clinical utility must be demonstrated; not just test-set performance | §3.1 | `clinical_utility_gap` |

NHS §4.21 (shadow mode) is precisely the mechanism for closing `distribution_shift_gap`: run the model on the local deployment population before it has any authority over clinical decisions. The compiler discovered the gap that shadow mode addresses before encountering the NHS guidance that mandates shadow mode.

### EU AI Act (2024)

| Requirement | Article | Covered by |
|---|---|---|
| Risk management system; identify and control known risks lifecycle-wide | Article 9 | `blast_radius_gap`, `authority_gap` |
| Data governance; training/validation data representative and bias-free | Article 10 | `model_specification_gap`, `distribution_shift_gap` |
| Transparency; deployers informed of subpopulation limits and conditions of use | Article 13 | `individual_population_gap`, `distribution_shift_gap` |
| Human oversight; ability to override, stop, or disregard outputs | Article 14 | `authority_gap` |

Article 14's human oversight requirement maps directly to `authority_gap`, which was discovered from the Dutch childcare case — a case that the European Parliament explicitly cited as a trigger for the EU AI Act itself. The compiler discovered the gap from the failure that motivated the regulation.

---

## What the Regulatory Alignment Means

The 100% coverage result is not trivial, but it requires careful interpretation.

**What it shows:** Six gaps discovered from deployment failure evidence, with no consultation of regulatory text, are sufficient to cover every material requirement across three independent regulatory frameworks. The compiler-guided discovery process and the regulatory drafting process arrived at structurally identical conclusions from different starting points.

**What it does not show:** It does not show that the six discovered gaps are *complete* — there may be failure modes not represented in the CASE-LIB-001 corpus that would force additional gaps. The regulatory frameworks themselves acknowledge this: FDA, NHS, and the EU AI Act are all described as living documents subject to revision as new failure modes emerge.

**What is structurally notable:** The compiler discovered `authority_gap` from the Dutch childcare case (2019–2020). The EU AI Act was drafted partly in response to the Dutch childcare case. The compiler's inductive path and the legislature's motivating evidence were the same event. The taxonomy and the regulation converge because they are both downstream of the same failure.

Similarly, the compiler discovered `clinical_utility_gap` from the Epic Sepsis Model pattern. FDA's Appendix C operating-point metrics requirement exists because of that failure pattern. The regulatory requirement and the compiler-induced gap are responses to the same empirical problem.

This is the experiment's central claim: **regulatory requirements are not arbitrary design choices. They are responses to observed failure modes. A compiler guided by failure modes will converge on the same taxonomy that regulators converge on, because both processes are grounded in the same underlying evidence.**

---

## The Individual/Population Gap

`individual_population_gap` is the most structurally novel finding. It has no exact counterpart in the medical AI literature before CASE-LIB-001 named it, and it does not reduce to any existing gap.

It is not `approximation_quality_gap`: a model can have high AUC at population level and still have this gap fully open for individual decisions.

It is not `distribution_shift_gap`: a model can generalize perfectly to the deployment population and still have this gap open.

It is not `model_specification_gap`: the model may be correctly specified for its population-level target and still have this gap open for individual decisions.

The gap is structural to the use case: population statistics and individual certification are different epistemic categories. A recidivism score that is perfectly calibrated across 100,000 defendants cannot certify that defendant 100,001 will reoffend. No improvement to the model can close this gap for individual liberty decisions — the evidence required to close it (individual-level prediction with sufficient precision for detention) does not exist and may be structurally unproducible for some action classes.

The EU AI Act's Article 13 transparency requirement — deployers must be told the conditions under which the system should *not* be used — maps to this gap. FDA's subpopulation performance disclosure maps to it. NHS §4.22's enriched local test set maps to it. Three independent regulatory frameworks each found it necessary to address this category distinction, using different mechanisms. The compiler discovered the same distinction from the COMPAS and Arkansas Medicaid cases without consulting any of them.

---

## Comparison to LEG-001

| Dimension | LEG-001 (legal) | MED-IND-001 (medical) |
|---|---|---|
| Starting profile | v0: retrieval provenance + freshness | v0: approximation quality + freshness |
| Induction cases | 7 (6 induction + 1 positive control) | 7 (6 induction + 1 positive control) |
| Gaps discovered | 4 | 6 |
| Induction mode | Human-in-the-loop | Fully automated |
| External oracle | Human legal expert at each step | None — case gap_statuses only |
| Convergence | v4, no over-authorization | v6, no over-authorization |
| Generalization (held-out) | 5/5 exact agreement | 3/5 exact, 5/5 no over-authorization |
| Post-hoc validation | Magesh et al. (JELS 2025) audit | FDA/NHS/EU AI Act (100% coverage) |
| Residual gap | AEX vs REF/REV | AEX vs REV |

The residual gap is identical in structure across both experiments. In both cases, the compiler signals "unverified" where an expert signals "wrong." This is not a failure of either taxonomy — it is the correct behavior of a compiler that does not have access to ground truth. The certifier boundary is exactly there: "this gap is open" is a compiler judgment; "this deployment was harmful" is a domain judgment.

The medical experiment is stronger on automation — no human judgment enters the induction loop. The legal experiment is stronger on external validation — Magesh et al. is a fully independent audit published in a peer-reviewed journal, not a comparison to regulatory text that may itself have been written in response to the same cases the induction corpus uses.

---

## Connection to Theorem N

Theorem N: a correctly grounded profile prevents silent authorization of unmitigated failure modes.

The induction experiment is a constructive proof of the theorem's converse. Start with an ungrounded profile (v0: no domain knowledge). The compiler silently authorizes six categories of known failure. Ground each gap one at a time. The silent authorizations stop, one per grounding step, in the order grounded.

The experiment also makes the cost of under-grounding legible. At each profile version, you can read directly which failure modes the profile cannot see. v0 cannot see operating-point utility, target mismatch, distribution shift, individual/population distinction, blast radius, or authority scope. v1 adds utility; v2 adds target specification; and so on. The progression from v0 to v6 is a map of exactly what a regulatory framework must require to avoid the failures in the corpus.

The 100% regulatory coverage in Phase 4 is evidence that FDA, NHS, and the EU AI Act have converged on a correct grounding of the profile for their domains. They required exactly the gaps the compiler forced. Neither the compiler nor the regulators had access to the other's reasoning during their respective processes. They arrived at the same answer.

---

## Limitations

**The corpus is not exhaustive.** CASE-LIB-001 covers 16 cases across five domains. Additional failure modes exist that are not represented. The gaps `calibration_gap`, `proxy_gap`, `interference_gap`, `coupling_gap`, and `feedback_coupling_gap` are all in the existing taxonomy but were not induced in this run — either because the cases that would induce them were held out, or because the induction corpus was not long enough to reach them. A longer induction corpus would force additional gaps.

**The positive control breaks at convergence.** M01 drops from ALR (at v0) to AEX (at v6) because the converged profile requires six domain gaps bounded and M01 does not supply them. This is structurally correct but means the positive control must be re-read as: "with structural evidence only, v0 correctly emits ALR; with domain gaps added, the same case would still reach ALR if it supplied domain-gap evidence." The positive control demonstrates the v0 floor, not the v6 floor.

**The regulatory audit gap names are pre-mapped.** The `fda_nhs_audit.py` module contains explicit mappings from each regulatory requirement to specific gap IDs. These mappings were written after induction, but they were written by the experiment designers, not derived automatically. A fully automated audit would require regulatory text parsing — which is beyond the scope of this experiment.

**The residual AEX vs REV gap is permanent.** Cases H04, H05, and the induction cases at convergence all show the compiler at AEX where experts say REV. This gap cannot be closed by improving the taxonomy. It is structural: the compiler can require evidence; it cannot evaluate whether deployed evidence was adequate in practice. Closing it would require the compiler to have access to hindsight outcome data, which arrives after deployment and is not available at authorization time.
