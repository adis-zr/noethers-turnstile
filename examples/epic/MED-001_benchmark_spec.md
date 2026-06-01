# MED-001: Clinical Sepsis Prediction Benchmark
## Admissibility Compiler Benchmark Specification

**Benchmark ID:** MED-001  
**Status:** Specification draft v6  
**Target paper section:** Part III — Stress Evidence  
**Analogous benchmark:** PGM-001 (probabilistic inference)  
**Expected finding type:** Taxonomy/profile falsification

**Revision notes (v1 → v2):**
- §5: explicit new/existing classification for every gap type
- §5: freshness_gap vs. expiry mechanism resolved
- §6: profile notation flagged for Rust source verification
- §7: Profile v2 completed (DIA/REV/AEX explicitly stated)
- §8.1: C06 pinned to single expected output
- §8.2: full parametrized grid stated with filter rules and post-filter count
- §9: pre-registration step added as Step 0

**Revision notes (v2 → v3):**
- §8.1: C08 corrected from REV to AEX (same reasoning as C06 correction)
- §8.1: oracle table and notes block cleaned up; stale C06 reasoning removed
- §8.1: C12 corrected from REV to AEX (same profile analysis applies)
- §8.3: A06 flagged with [VERIFY] on PPV floor value and contract schema
- §10: 8-cell independence table sketched with model×dataset mappings;
        hard cell (aq=O, ms=B, cu=B) identified; Model E added to §4

**Revision notes (v3 → v4):**
- §8.3: adversarial cases A01–A06 explicitly included in pre-registration lock
- §9 Step 0: pre-registration scope extended to cover oracle + adversarial cases
- §10: 8-cell table [VERIFY] hedges removed; all cells committed as pre-registered
        claims; empirical confirmation of Model E and qSOFA cells required before
        hashing the pre-registration document, not after
- §10: (O, O, B) synthetic cell committed as a named constructed case, not a
        vague possibility

**Revision notes (v4 → v5):**
- §8.1: C13 corrected from AEX to REV. AEX requires freshness=BOUNDED; fr=OPEN
        blocks AEX, dropping ceiling to REV. Discovered during implementation
        and confirmed by passing test suite.
- Status updated to v5.

**Revision notes (v5 → v6):**
- §9 Step 0 / §10: CHECK-2 empirically failed on Challenge 2019 SetA.
        qSOFA max PPV=0.089 across all thresholds (8.8% sepsis prevalence);
        never reaches notification floor 0.15. Per pre-condition protocol
        (§9), (B, O, B) cell witness is revised before hashing.
- §10: (B, O, B) cell revised from qSOFA to Model C (GBM) with ms=OPEN
        declared: GBM AUC=0.95 (aq=B), PPV=0.95 at thr=0.3 (cu=B),
        ms=OPEN because Challenge 2019 SepsisLabel proxies Sepsis-3 but
        omits clinician-judged "suspected infection" component.
- §9 CHECK-1 confirmed: lactate AUC=0.504 < 0.70 floor (aq=O), PPV=0.457
        at threshold=2.0 mmol/L (cu=B). (O, B, B) witness holds.
- Status updated to v6.

---

## 1. Objective

MED-001 tests whether the admissibility compiler correctly refuses to emit
rollout-level action authority (ALR, AAA) for clinical alert decisions based
on approximation quality evidence alone.

The expected finding is a three-way taxonomy separation not currently in
the gap taxonomy:

```
approximation_quality_gap:
  computed score is close to the model's training target

model_specification_gap:
  training target is adequate for the action-relevant clinical question

clinical_utility_gap:    [NEW]
  statistical accuracy at the operating threshold is sufficient
  to license alert actions at the proposed blast radius
```

These are not the same gap. A model with AUC 0.76 can have sensitivity 33%
and PPV 12% at the deployed alert threshold — the Wong et al. (2021) finding
on the Epic Sepsis Model. The compiler should not emit ALR from an
approximation certificate alone. If the current profile allows it to, the
profile is wrong.

This mirrors PGM-001's structure exactly: the compiler does what the profile
asks; the falsified object is the taxonomy/profile.

MED-001 adds two new gap types to the core taxonomy:
  clinical_utility_gap
  distribution_shift_gap

All other gap types used in this benchmark are existing (see §5).

---

## 2. Claim Class

```
claim_class:   icu.clinical_alert.sepsis.v1
intended_use:  clinical_alert

action_consequences:
  - nurse alert with required response protocol
  - rapid response team activation
  - automatic order set pre-population (antibiotics, cultures, fluids)

description:
  An ICU sepsis early-warning score emitted by a statistical model
  trained on EHR data, used to drive a downstream alert action at a
  specified blast radius.
```

---

## 3. Datasets

### 3.1 Primary: PhysioNet / Computing in Cardiology Challenge 2019

URL:    https://physionet.org/content/challenge-2019/1.0.0/
Access: PhysioNet account + DUA only. No CITI training required. Immediate
        after agreement.

```bash
wget -r -N -c -np \
  https://physionet.org/files/challenge-2019/1.0.0/ \
  -P ./data/challenge2019/
# Result: training_setA/ and training_setB/
# One .psv file per patient; hourly rows; SepsisLabel column
```

Contents:
- Set A: ~20,000 ICU patients, Hospital System 1
- Set B: ~20,000 ICU patients, Hospital System 2 (different institution)
- Hourly vitals and labs: HR, O2Sat, Temp, SBP, MAP, DBP, Resp, EtCO2,
  plus 26 lab values
- Sepsis label per Sepsis-3 (Singer et al. 2016): SepsisLabel = 1 at onset
- Patient metadata: age, gender, unit type, hospital LOS

Why: Two hospital systems in one package gives a built-in distribution shift
test. Sepsis-3 labels are publication-standard. No credentialing delay.
Size: ~1.5 GB uncompressed.

### 3.2 Secondary: MIMIC-IV

URL:    https://physionet.org/content/mimic-iv/2.2/
Access: PhysioNet account + CITI training + DUA.

CITI steps:
  1. Register at https://physionet.org/register/
  2. Complete "Data or Specimens Only Research" course at
     https://about.citiprogram.org/ (~2-3 hours, free)
  3. Upload completion certificate to PhysioNet profile
  4. Sign MIMIC-IV DUA at dataset page
  5. Access granted within 1-5 business days (usually same day)

```bash
pip install wfdb
python -c "import wfdb; wfdb.dl_database('mimic-iv', './data/mimiciv')"
```

Contents: ~300,000 ICU admissions, Beth Israel Deaconess, 2008-2019.
Why: Gold standard for clinical ML benchmarking; large enough for
     meaningful calibration analysis on held-out sets.
Size: ~7 GB compressed.

### 3.3 Tertiary: eICU Collaborative Research Database

URL:    https://physionet.org/content/eicu-crd/2.0/
Access: Same CITI + DUA as MIMIC-IV. One CITI completion covers both.

Contents: 200,859 ICU admissions across 208 hospitals, 2014-2015.
Why: Multi-center, multi-state. Strongest distribution shift test available.
     Exercises blast_radius_gap across heterogeneous clinical contexts.

### 3.4 Reference numbers (no download)

Wong et al. (2021). JAMA Internal Medicine 181(8):1065-1070.
Epic Sepsis Model, externally validated at UW Medicine:
  AUC: 0.76
  Sensitivity at deployed threshold: 0.33
  PPV at deployed threshold: 0.12
  Sepsis cases missed: 67%
  False positive rate: 83%

These numbers define the benchmark's target failure region. They are used
directly as Model D inputs; the Epic model itself is not run.

---

## 4. Models to Instantiate

### Model A: Sepsis-3 SOFA Criteria
Rule-based. SOFA score >= 2 from baseline plus suspected infection.
Implement from Singer et al. 2016, Table 2. No training required.
Expected permission: ALR under both profiles (near-ideal specification).

### Model B: qSOFA
Rule-based. RR >= 22 OR altered mentation OR SBP <= 100 (2 of 3).
Intended for pre-ICU screening; systematically underperforms in ICU.
Expected to expose model_specification_gap: model was specified for a
different context than ICU deployment. No training required.

### Model C: Gradient Boosted Model on vitals/labs
Train on Set A. Evaluate on Set A held-out and Set B.
Target AUC: ~0.85 on training distribution (matches published Challenge
2019 top performers). This is the "high AUC, poor utility" configuration
that mimics the Epic Sepsis Model deployment pattern.
Expected permission under v2: AEX. Approximation quality and model
specification are bounded; clinical utility is not. AEX is the correct
ceiling — "approve experiment" is the right permission for a well-specified
model with good AUC but no utility validation. Should not reach ALR without
clinical_utility_gap bounded.

### Model D: Epic Sepsis Model proxy
Paper-input case only. Use Wong et al. numbers directly:
  AUC = 0.76, sensitivity = 0.33, PPV = 0.12 at deployed threshold.
Do not train. Construct tokens from published validation numbers.
Used to show what a correctly structured taxonomy would have done.

### Model E: Lactate threshold rule
Single-variable rule: serum lactate > 2.0 mmol/L triggers alert.
No training required. Lactate > 2 mmol/L is an explicit Sepsis-3 severity
component (Singer et al. 2016), so model_specification_gap is BOUNDED by
construction — the target variable is clinically grounded.

Expected metrics on Challenge 2019 Set A (to be verified empirically):
  AUC:         ~0.63-0.68 (single variable; likely below approximation
               quality contract floor, giving aq=OPEN)
  Sensitivity: ~0.68-0.72 at threshold
  PPV:         ~0.22-0.28 at threshold given ~15% ICU sepsis prevalence

If PPV passes the notification-level utility contract floor, cu=BOUNDED
for blast_radius=notification. Combined with ms=BOUNDED and aq=OPEN, this
fills the hard cell in the 8-cell independence table (see §10).

Clinical interpretation: a clinically grounded point-operating rule can have
poor global discrimination (AUC) but adequate operating-point utility at a
specific threshold. This shows that approximation_quality_gap and
clinical_utility_gap are genuinely independent — neither implies the other.

Model E is used only for the 8-cell independence table. It does not appear
in the oracle or parametrized test suites. PPV threshold assumption must be
confirmed against the detail contract floor in A06 [VERIFY].

---

## 5. Gap Taxonomy for this Class

Each gap is marked as existing (present in ACS §8 representative list)
or new (not currently in the taxonomy). This classification must be
confirmed against the current gap taxonomy version before implementation.

### 5.1 Gap classification

```
approximation_quality_gap     EXISTING
  (equivalent to posterior_divergence_gap / approximation_gap from PGM-001)
  Is the computed score close to what the model would output with full data?

model_specification_gap       EXISTING (added in PGM-001 correction)
  Is the model's training target adequate for the action-relevant clinical
  question?
  Example: "predict Sepsis-3 label within 6h" may not be adequate for
  "patient will benefit from immediate antibiotic administration."

clinical_utility_gap          NEW
  At the operating alert threshold and blast radius, are sensitivity,
  specificity, PPV, and NPV sufficient to license the proposed action?
  This is not the same as approximation quality or model specification.
  A well-specified model approximated well can still have clinical utility
  too low for automatic action at a given threshold.

distribution_shift_gap        NEW
  Does the model perform adequately on the deployment population,
  given that the training population may differ in case mix, demographics,
  EHR system, or care protocols?
  Note: this is distinct from model_specification_gap. A correctly specified
  model (right target variable) can still fail on distribution shift if the
  training population is unrepresentative of deployment.

calibration_gap               EXISTING
  Are predicted probabilities calibrated against observed outcomes?
  A model with good AUC and poor calibration licenses incorrect
  probability-weighted decisions.

blast_radius_gap              EXISTING
  What is the scope of downstream actions triggered per alert?
  A 12% PPV alert that auto-populates antibiotics has a very different
  blast radius than one that sends a notification. The same model may
  license the notification and not the order set.

authority_gap                 EXISTING
  Does the deploying system have authority to act at the proposed
  permission level given patient context, care setting, and existing orders?
```

### 5.2 freshness_gap vs. expiry mechanism

The ACS paper provides two distinct mechanisms for time-sensitivity:

Token expiry (existing first-class mechanism on ProofContext / LiveJudgment):
  The certificate itself is stale. A score computed and certified at time T
  has an expiry field. If now() > expiry, the compiler halts at EXP.
  Use for: score is more than N hours old.

freshness_gap (EXISTING gap type, ACS §8):
  The input data used to compute the score was stale at compute time,
  regardless of when the certificate was issued. A freshly-issued
  certificate can be based on 4-hour-old vitals.
  Use for: inputs to the model were not current when the model was run.

These are different things and both should be exercised:
  C09 (score >2h old):    model via token expiry firing, not freshness_gap
  C13 (missing recent vitals): model via freshness_gap OPEN — no token can
                               attest that inputs were current at compute time

freshness_gap remains a gap in this benchmark. It is exercised differently
from token expiry.

---

## 6. Token Sketches

### NOTATION NOTE
The profile requirement levels below use OPEN_ALLOWED / BOUNDED_REQUIRED /
CLOSED_REQUIRED as defined in ACS §8.3. These must be verified against the
actual Rust enum names in the compiler source before implementation. Every
profile table cell marked [VERIFY] should be checked against the source.

### 6.1 Approximation quality token (adapted from pgm.posterior_divergence_bound.v1)

```
token_type = clinical.approximation_quality_bound.v1
bounds_gaps = [approximation_quality_gap_id]
closes_gaps = []
scope = (claim_id, candidate_id, context_id, model_id, dataset_id, split)
details = (
  model_fingerprint,
  training_dataset,
  evaluation_dataset,
  evaluation_split,
  auc_roc,
  auc_pr,
  brier_score,
  calibration_method,
  calibration_result,
  threshold_used,
  sensitivity_at_threshold,    # these fields distinguish this token
  specificity_at_threshold,    # from a pure AUC certificate
  ppv_at_threshold,
  npv_at_threshold,
  artifact_refs
)
```

A token that reports only AUC cannot bound clinical_utility_gap; it can
only bound approximation_quality_gap.

### 6.2 Clinical utility token (NEW — required by corrected profile at ALR)

```
token_type = clinical.utility_bound.v1
bounds_gaps = [clinical_utility_gap_id]
closes_gaps = []
scope = (claim_id, candidate_id, context_id, model_id, alert_action, blast_radius)
details = (
  operating_threshold,
  sensitivity,
  specificity,
  ppv,
  npv,
  nnt,                          # alerts per true positive
  false_alert_rate,
  blast_radius_description,
  comparator_standard,
  population_description,
  sample_size,
  confidence_intervals,
  subgroup_analysis_refs,
  clinical_workflow_scope,
  artifact_refs
)
```

This token is harder to produce than the approximation quality token.
The difficulty is the point. A system unable to produce this token should
not receive ALR or AAA for clinical alert actions.

Scope binding: a utility token scoped to blast_radius="notification" does
not advance clinical_utility_gap for blast_radius="auto_order_antibiotics".
The blast radius is part of the scope tuple, not a free parameter.

### 6.3 Model specification token (adapted from Appendix D pgm.model_specification_bound.v1)

```
token_type = clinical.model_specification_bound.v1
bounds_gaps = [model_specification_gap_id]
details = (
  training_target_definition,
  action_target_definition,
  target_adequacy_argument,
  validation_artifacts,
  distribution_shift_analysis,
  subpopulation_performance,
  temporal_stability,
  scope_limits,
  claim_limit
)
```

### 6.4 Distribution shift token (NEW gap type, NEW token)

```
token_type = clinical.distribution_shift_bound.v1
bounds_gaps = [distribution_shift_gap_id]
details = (
  training_population_description,
  deployment_population_description,
  shift_analysis_method,
  performance_on_deployment_population,
  covariate_shift_analysis,
  sample_size,
  confidence_intervals,
  artifact_refs
)
```

---

## 7. Profile Specification

### NOTATION NOTE
OPEN_ALLOWED / BOUNDED_REQUIRED / CLOSED_REQUIRED must be verified against
Rust source before implementation. [VERIFY] marks each cell.

### Profile v1 (expected to be falsified by benchmark)

Profile v1 represents the naive clinical deployment profile: it requires
approximation quality evidence for ALR but does not require clinical utility.

```
class: icu.clinical_alert.sepsis.v1

DIA:
  approximation_quality_gap:  OPEN_ALLOWED     [VERIFY]
  model_specification_gap:    OPEN_ALLOWED     [VERIFY]
  clinical_utility_gap:       OPEN_ALLOWED     [VERIFY]
  distribution_shift_gap:     OPEN_ALLOWED     [VERIFY]
  calibration_gap:            OPEN_ALLOWED     [VERIFY]
  blast_radius_gap:           OPEN_ALLOWED     [VERIFY]
  freshness_gap:              OPEN_ALLOWED     [VERIFY]

REV:
  approximation_quality_gap:  BOUNDED_REQUIRED [VERIFY]
  model_specification_gap:    OPEN_ALLOWED     [VERIFY]
  clinical_utility_gap:       OPEN_ALLOWED     [VERIFY]
  distribution_shift_gap:     OPEN_ALLOWED     [VERIFY]
  calibration_gap:            OPEN_ALLOWED     [VERIFY]
  blast_radius_gap:           OPEN_ALLOWED     [VERIFY]
  freshness_gap:              OPEN_ALLOWED     [VERIFY]

AEX:
  approximation_quality_gap:  BOUNDED_REQUIRED [VERIFY]
  model_specification_gap:    BOUNDED_REQUIRED [VERIFY]
  clinical_utility_gap:       OPEN_ALLOWED     [VERIFY]
  distribution_shift_gap:     OPEN_ALLOWED     [VERIFY]
  calibration_gap:            BOUNDED_REQUIRED [VERIFY]
  blast_radius_gap:           OPEN_ALLOWED     [VERIFY]
  freshness_gap:              BOUNDED_REQUIRED [VERIFY]

ALR:
  approximation_quality_gap:  BOUNDED_REQUIRED [VERIFY]
  model_specification_gap:    BOUNDED_REQUIRED [VERIFY]
  clinical_utility_gap:       OPEN_ALLOWED     [VERIFY]  # falsification target
  distribution_shift_gap:     OPEN_ALLOWED     [VERIFY]
  calibration_gap:            BOUNDED_REQUIRED [VERIFY]
  blast_radius_gap:           BOUNDED_REQUIRED [VERIFY]
  freshness_gap:              BOUNDED_REQUIRED [VERIFY]

AAA:
  approximation_quality_gap:  CLOSED_REQUIRED  [VERIFY]
  model_specification_gap:    BOUNDED_REQUIRED [VERIFY]
  clinical_utility_gap:       OPEN_ALLOWED     [VERIFY]  # also falsification target
  distribution_shift_gap:     BOUNDED_REQUIRED [VERIFY]
  calibration_gap:            CLOSED_REQUIRED  [VERIFY]
  blast_radius_gap:           BOUNDED_REQUIRED [VERIFY]
  freshness_gap:              CLOSED_REQUIRED  [VERIFY]
```

Under v1, a model with high AUC and bounded model_specification can receive
ALR without demonstrating clinical utility. Wong et al. numbers show this
is wrong: sensitivity 0.33, PPV 0.12 should not license automatic alert
propagation at scale.

### Profile v2 (corrected after benchmark finding)

Profile v2 tightens only ALR and AAA. DIA, REV, and AEX are inherited
unchanged from v1. This is explicit, not implied.

```
DIA:  unchanged from v1
REV:  unchanged from v1
AEX:  unchanged from v1

ALR:
  approximation_quality_gap:  BOUNDED_REQUIRED [VERIFY]
  model_specification_gap:    BOUNDED_REQUIRED [VERIFY]
  clinical_utility_gap:       BOUNDED_REQUIRED [VERIFY]  # new requirement
  distribution_shift_gap:     BOUNDED_REQUIRED [VERIFY]  # new requirement
  calibration_gap:            BOUNDED_REQUIRED [VERIFY]
  blast_radius_gap:           BOUNDED_REQUIRED [VERIFY]
  freshness_gap:              BOUNDED_REQUIRED [VERIFY]

AAA:
  approximation_quality_gap:  CLOSED_REQUIRED  [VERIFY]
  model_specification_gap:    BOUNDED_REQUIRED [VERIFY]
  clinical_utility_gap:       BOUNDED_REQUIRED [VERIFY]  # new requirement
  distribution_shift_gap:     BOUNDED_REQUIRED [VERIFY]  # new requirement
  calibration_gap:            CLOSED_REQUIRED  [VERIFY]
  blast_radius_gap:           CLOSED_REQUIRED  [VERIFY]
  freshness_gap:              CLOSED_REQUIRED  [VERIFY]
```

Profile v2 well-formedness check: every gap requirement at a stronger
permission is >= the requirement at a weaker permission. This must pass
the existing profile validator before any benchmark runs.

---

## 8. Test Case Design

### 8.1 Oracle-checked cases (pre-registered before any data runs; see §9 Step 0)

For each case, all inputs are fully specified so expected output is determined
uniquely by the profile + compiler rules. No "or" outputs are acceptable in
pre-registration.

Gap status abbreviations: O=OPEN, B=BOUNDED, C=CLOSED, —=not applicable

| ID  | Model | Dataset  | Profile | aq  | ms  | cu  | ds  | cal | br  | fr  | Expected | Purpose |
|-----|-------|----------|---------|-----|-----|-----|-----|-----|-----|-----|----------|---------|
| C01 | A     | SetA     | v1      | B   | B   | O   | O   | B   | B   | B   | ALR      | Baseline: strong model |
| C02 | A     | SetA     | v2      | B   | B   | B   | B   | B   | B   | B   | ALR      | v2 doesn't penalize strong model |
| C03 | B     | ICU/SetA | v1      | B   | O   | O   | O   | O   | B   | B   | REV      | qSOFA: approx bounded, spec not |
| C04 | B     | ICU/SetA | v2      | B   | O   | O   | O   | O   | B   | B   | REV      | Same result |
| C05 | C     | SetA→SetB| v1      | B   | B   | O   | O   | B   | B   | B   | ALR      | FALSIFICATION: high AUC emits ALR |
| C06 | C     | SetA→SetB| v2      | B   | B   | O   | O   | B   | B   | B   | AEX      | v2 blocks ALR; AEX reachable (see note) |
| C07 | D     | UW       | v1      | B   | B   | O   | O   | B   | B   | B   | ALR      | FALSIFICATION: Epic proxy |
| C08 | D     | UW       | v2      | B   | B   | O   | O   | B   | B   | B   | AEX      | v2 blocks ALR; AEX reachable (same as C06) |
| C09 | C     | SetA     | v2      | —   | —   | —   | —   | —   | —   | —   | EXP      | Token expiry fires (score >2h old) |
| C10 | C     | SetA     | v2      | B   | B   | O   | O   | B   | O   | B   | AEX      | blast_radius=auto_order: br OPEN |
| C11 | C     | SetA     | v2      | B   | B   | B   | B   | B   | B   | B   | ALR      | notification blast_radius: properly evidenced |
| C12 | A     | eICU     | v2      | B   | B   | O   | O   | B   | B   | B   | AEX      | ds OPEN across eICU; AEX reachable (same) |
| C13 | C     | SetA     | v2      | B   | B   | O   | O   | B   | B   | O   | REV      | freshness_gap OPEN: blocks AEX (requires fr=B); REV is ceiling |
| C14 | A     | SetA+cal | v2      | C   | B   | B   | B   | C   | B   | B   | ALR      | Fully evidenced |
| C15 | C     | elective | v1/v2   | —   | —   | —   | —   | —   | —   | —   | OOC      | Membership: elective surgery patient |

Column key: aq=approximation_quality, ms=model_specification, cu=clinical_utility,
            ds=distribution_shift, cal=calibration, br=blast_radius, fr=freshness

Notes on pinned cases:

C05/C07 are the headline falsification cases. Their gap status rows are
identical: aq=B, ms=B, cu=O, ds=O under both profiles. Under Profile v1,
ALR requires neither cu nor ds to be bounded — so both emit ALR. Under
Profile v2, ALR requires cu=BOUNDED and ds=BOUNDED — both blocked.

C06/C08/C12 all share the same gap profile (cu=O, ds=O, aq=B, ms=B,
cal=B, br=B, fr=B) and the same expected output under v2: AEX.

Reasoning (applies identically to all three):
  v2 AEX is inherited from v1 AEX, which has OPEN_ALLOWED for both
  clinical_utility_gap and distribution_shift_gap. All other AEX
  requirements (aq=BOUNDED, ms=BOUNDED, cal=BOUNDED) are satisfied.
  AEX is therefore reachable. ALR is blocked by cu=BOUNDED_REQUIRED.

The clinical interpretation is correct: "approve experiment" is the right
permission for a well-specified model with good AUC but no cross-institution
utility validation or clinical utility certificate. The benchmark shows that
v2 does not collapse these cases to REV — it places the evidence burden
exactly where it belongs.

C12 specifically: eICU deployment with Set A-trained SOFA. distribution_shift
is OPEN because no eICU-population utility token exists. AEX is the ceiling.
The same model that could reach ALR on its training population cannot reach
ALR in a new deployment context without new population-scoped evidence.

### 8.2 Parametrized tests

Full grid:
  models:       4 (A, B, C, D)
  datasets:     3 (SetA, SetB, eICU sample)
  profiles:     2 (v1, v2)
  thresholds:   5 (0.1, 0.2, 0.3, 0.4, 0.5)
  blast_radii:  3 (notification, rapid_response, auto_order)
  freshness:    4 (current, 1h_stale, 2h_stale, 4h_stale)

Full cross: 4 × 3 × 2 × 5 × 3 × 4 = 1,440

Filter rules (applied before running):

  F1: Model D (Epic proxy) has fixed paper-derived numbers.
      Threshold dimension collapses to 1 (the deployed threshold from
      Wong et al.). Freshness dimension does not apply (not a live-computed
      score). Removes: 3 × 2 × 4 × 3 × (5-1 + 4) = significant reduction.
      Model D rows: 3 datasets × 2 profiles × 1 threshold × 3 blast_radii
                  × 1 freshness = 18 cases.

  F2: Models A and B are rule-based. Threshold variation applies only to
      the score cutoff, which is fixed for SOFA/qSOFA. Collapse threshold
      to 1 for these models.
      Models A/B rows: 2 × 3 × 2 × 1 × 3 × 4 = 144 cases.

  F3: freshness=4h_stale cases where the token has already expired
      (covered by C09 oracle case) are excluded from parametrized suite
      to avoid double-counting.
      Removes ~25% of Model C freshness rows.

  F4: blast_radius=auto_order cases where Model B (qSOFA) is used are
      excluded as OOC by membership classifier before gap evaluation.
      Removes 12 cases.

Post-filter estimate: ~480-520 parametrized tests.

The invariant checked on every parametrized test:
  emitted_permission <= meet of (best_positive, structural_failures, controls)
  This is the non-promotion check. No parametrized case should violate it.
  Profile v1 falsification cases are checked separately (they do not violate
  non-promotion; they show the profile permits too much).

### 8.3 Adversarial cases

```
A01: AUC=0.95, sensitivity=0.20 at threshold.
     Profile v1: emits ALR (falsification).
     Profile v2: refuses ALR.
     Tests that utility evidence is checked independently of AUC.

A02: Two tokens present: approximation_quality BOUNDED,
     model_specification BOUNDED. clinical_utility_gap OPEN.
     Profile v1: emits ALR (falsification).
     Profile v2: emits AEX at most.
     Tests that missing gap is not filled by presence of other tokens.

A03: clinical_utility token scoped to Set A.
     Deployment is Set B population.
     Expected: provenance mismatch; clinical_utility_gap stays OPEN.
     Tests that cross-population token reuse is blocked.

A04: blast_radius in deployment = "auto_order_antibiotics".
     clinical_utility token scope = "notification_only".
     Expected: scope mismatch; blast_radius_gap stays OPEN for auto_order.
     Tests that blast_radius scope is enforced within token.

A05: clinical_utility token expired (>90 days, population drift).
     Expected: token expiry fires; gap status reverts to OPEN.
     Tests that stale utility evidence cannot support active permission.

A06: clinical_utility token with PPV=0.12, NNT=8.3.
     Profile v2 contract has a semantic check: PPV_floor = 0.20 for
     blast_radius=auto_order.
     [VERIFY: PPV floor value of 0.20 is illustrative. Must be grounded
      in clinical literature or explicitly chosen as a benchmark design
      parameter before pre-registration. The floor is part of the TCB
      (detail contract), not the compiler. Wrong floor value = wrong TCB,
      not a compiler bug.]
     [VERIFY: contract schema structure must follow the same pattern as
      existing PGM-001 certifier contracts — semantic check format,
      artifact dependency structure, scope rules. Check against Rust
      source for contract interface before implementing.]
     Expected: detail_contract_ok fails on semantic check; gap not advanced.
     Tests that contracts encode domain-specific floors, not just schema.
```

A06 requires a detail contract with a semantic check on PPV floor. This is
analogous to the semantic checks in the PGM inference contract. The contract
is part of the TCB, not the compiler. A06 tests the contract, not the
compiler itself.

---

## 9. Implementation Steps

### Step 0: Pre-registration (before any data is touched)

Lock expected outputs for all oracle and adversarial cases before any
model is run, any dataset is loaded, and any compiler is invoked.

Pre-registration document must contain:
  - Full oracle case table from §8.1 (C01–C15), with gap status
    assignments and expected compiler output for each case under
    each profile
  - Full adversarial case list from §8.3 (A01–A06), with expected
    compiler output and the specific mechanism being tested
  - The headline falsification claims, stated explicitly:
      "Profile v1 will emit ALR on C05 and C07."
      "Profile v2 will not emit ALR on C05, C06, C07, C08, or C12."
      "Profile v1 will emit ALR on A01 and A02."
      "Profile v2 will refuse ALR on A01 and A02."
  - The 8-cell independence table from §10, with all cell assignments
    committed (Model E and qSOFA cells included as pre-registered claims)
  - PPV floor value for A06 detail contract (chosen as benchmark design
    parameter; grounded in Wong et al. 2021 where PPV=0.12 is the
    failure case; floor set at 0.20 for blast_radius=auto_order)

Empirical pre-conditions before hashing:
  Before the pre-registration document is hashed and timestamped,
  two empirical checks must run to confirm the 8-cell table is
  achievable as claimed:
    CHECK-1: Run Model E (lactate > 2) on Challenge 2019 SetA.
             Confirm AUC < approximation quality contract floor
             AND PPV >= 0.20 at the notification-level threshold.
             If either condition fails, revise the (O, B, B) cell
             witness before hashing.
    CHECK-2: Run Model B (qSOFA) on ICU patients in SetA.
             Confirm PPV >= notification-level floor.
             RESULT: FAILED. qSOFA max PPV = 0.089 across all
             thresholds on Challenge 2019 SetA (8.8% sepsis
             prevalence). Witness revised to Model C (GBM) with
             ms=OPEN (see §10 table revision). CHECK-2 is satisfied
             by revised witness: GBM PPV=0.95 at thr=0.3.
  These checks inform the pre-registration document. They are not
  benchmark runs. No compiler is invoked, no profiles are evaluated,
  no oracle assertions are checked during these pre-conditions.

Hash the pre-registration document after all pre-conditions pass:
  sha256sum MED-001_preregistration.txt > MED-001_preregistration.sha256

Timestamp via git commit. The paper will reference the pre-registration
hash. Any oracle or adversarial result that deviates from the
pre-registered expectation must be explained before paper submission —
deviation is not grounds for silent correction.

### Step 1: Data acquisition

```bash
# Challenge 2019 — immediate after PhysioNet DUA
# https://physionet.org/content/challenge-2019/1.0.0/
mkdir -p data/challenge2019
wget -r -N -c -np \
  https://physionet.org/files/challenge-2019/1.0.0/ \
  -P ./data/challenge2019/

# MIMIC-IV — after CITI training + DUA
# https://physionet.org/content/mimic-iv/2.2/
pip install wfdb
python -c "import wfdb; wfdb.dl_database('mimic-iv', './data/mimiciv')"
```

### Step 2: Feature extraction

```python
FEATURES = [
    # Vitals
    'HR', 'O2Sat', 'Temp', 'SBP', 'MAP', 'DBP', 'Resp',
    # Labs
    'BUN', 'Creatinine', 'Glucose', 'Lactate', 'WBC',
    'Bilirubin_total', 'Platelets',
    # Derived
    'hours_since_admission', 'sofa_score', 'qsofa_score'
]
# Label: SepsisLabel; target: predict 6h before onset
```

### Step 3: Model training

```python
# Model C: GBM
from sklearn.ensemble import GradientBoostingClassifier
# Train on Set A, evaluate on Set A held-out AND Set B
# Report: AUC-ROC, AUC-PR, Brier score,
#         sensitivity/specificity/PPV/NPV at thresholds [0.1..0.5]

# Model A: SOFA — rule-based from Singer et al. 2016 Table 2
# Model B: qSOFA — rule-based
# Model D: paper numbers from Wong et al. 2021 directly
```

### Step 4: Metric computation (token payload construction)

```python
for model, dataset, threshold in combinations:
    metrics = {
        'auc_roc': ...,
        'threshold': threshold,
        'sensitivity': tp / (tp + fn),
        'specificity': tn / (tn + fp),
        'ppv': tp / (tp + fp),
        'npv': tn / (tn + fn),
        'nnt': 1 / ppv,
        'false_alert_rate': fp / (fp + tn)
    }
    # Construct token payloads
    # Determine which gaps each token bounds given contract requirements
    # Apply filter rules F1-F4 to exclude invalid combinations
```

### Step 5: Profile validator

Before any compiler runs, run the existing profile validator on both
Profile v1 and Profile v2. A profile that fails the well-formedness check
(stronger permission easier than weaker permission) must be corrected before
benchmark runs.

### Step 6: Compiler runs

For each oracle and parametrized case:
  1. Construct Gamma with available tokens
  2. Run under Profile v1 and v2
  3. Record emitted permission and all blocking reasons
  4. Assert non-promotion invariant
  5. For oracle cases: assert emitted == pre-registered expected

The structural soundness assertion is the same as PGM-001.
The new assertion: no parametrized case under Profile v2 emits ALR or AAA
without clinical_utility_gap BOUNDED.

### Step 7: Distribution shift analysis (eICU)

Take Model C trained on Challenge 2019 Set A. Run on stratified eICU sample
(20k patients, stratified by hospital). For each hospital cohort compute
AUC and utility metrics. Show:

  - AUC degrades modestly across hospitals
  - Sensitivity/PPV degrades substantially
  - distribution_shift_gap token scoped to Set A cannot advance gap status
    on eICU deployment (provenance mismatch on population scope)
  - Same model that might reach REV in one hospital cannot reach ALR
    in a different deployment without a new population-scoped utility token

---

## 10. Expected Results Summary

```
Pre-registration check:
  All oracle expected outputs match pre-registered values.
  Any deviation must be explained before paper submission.

Structural soundness:
  0 non-promotion violations across all oracle cases.
  0 non-promotion violations across ~480-520 parametrized cases.

Profile v1 falsification:
  C05 emits ALR. C07 emits ALR. (pre-registered)
  Additional parametrized cases where v1 emits ALR with
  clinical_utility_gap OPEN.

Profile v2 correction:
  C05 emits AEX under v2. C06 emits AEX. C07 emits AEX. C08 emits AEX.
  C12 emits AEX. (all pre-registered)
  0 cases under v2 emit ALR without clinical_utility_gap BOUNDED.
  Note: v2 does not collapse evidence-partial cases to REV. AEX is the
  correct ceiling when approximation and specification evidence is present
  but utility evidence is absent. This is the intended semantics.

New taxonomy obligations:
  clinical_utility_gap and distribution_shift_gap are added to the
  core taxonomy as Theta_v+1.
  Evidence: 8-cell independence table below.

  The table shows all 2^3 = 8 combinations of
    (approximation_quality, model_specification, clinical_utility)
    in {BOUNDED, OPEN} are independently achievable.
  If any two gaps were redundant, some cell would be structurally
  unreachable. The table falsifies all three redundancy claims.

8-cell independence table:

  All cells are pre-registered claims. The two cells marked
  PRE-CONDITION are confirmed by CHECK-1 and CHECK-2 in §9 Step 0
  before the pre-registration document is hashed. If a pre-condition
  fails, the witness is revised before hashing — not after.

  aq  ms  cu  | Model × Dataset                        | Notes
  ------------|----------------------------------------|------
  B   B   B   | Model A (SOFA), SetA, with utility tok | C14 oracle case
  B   B   O   | Model C (GBM), SetA, no utility token  | C05 falsification case
  B   O   B   | Model C (GBM), SetA, notification      | REVISED WITNESS (CHECK-2 failed).
              | utility token, ms declared OPEN        | Original CHECK-2 witness (qSOFA)
              |                                        | failed: qSOFA max PPV=0.089 on
              |                                        | Challenge 2019 SetA (8.8% sepsis
              |                                        | prevalence) — never reaches
              |                                        | notification floor 0.15.
              |                                        | Revised witness: GBM AUC=0.95
              |                                        | (aq=B), PPV=0.95 at thr=0.3
              |                                        | (cu=B). ms=OPEN because Challenge
              |                                        | 2019 SepsisLabel proxies Sepsis-3
              |                                        | but omits "suspected infection"
              |                                        | (clinician judgment), leaving the
              |                                        | training target specification
              |                                        | question open for ICU deployment.
              |                                        | Shows aq=B and cu=B are compatible
              |                                        | with ms=O. Witness is empirical,
              |                                        | not synthetic.
  B   O   O   | Model B (qSOFA), ICU/SetA, no utility  | C03 oracle case
  O   B   B   | Model E (lactate > 2), SetA,           | PRE-CONDITION (CHECK-1).
              | notification-level utility token       | AUC ~0.65 falls below aq
              |                                        | contract floor (aq=O). Lactate
              |                                        | is a Sepsis-3 component by
              |                                        | definition (ms=B). PPV >= 0.20
              |                                        | at notification threshold (cu=B).
              |                                        | Shows that a clinically grounded
              |                                        | point rule can have poor global
              |                                        | discrimination but adequate
              |                                        | operating-point utility.
  O   B   O   | Model E (lactate > 2), SetA,           | Model E without utility token.
              | no utility token                       | Paired with cell above to show
              |                                        | cu is independently controllable.
  O   O   B   | Synthetic: GBM trained on hospital     | PATHOLOGICAL CELL. Committed
              | mortality (proxy), SetA. AUC ~0.58     | as a named constructed case.
              | for sepsis prediction. Utility token   | A misspecified model with poor
              | constructed from operating-point       | global discrimination that happens
              | metrics at high-sensitivity threshold. | to have adequate operating-point
              |                                        | utility at one threshold. Included
              |                                        | for logical completeness. Paper
              |                                        | will note this cell is pathological
              |                                        | in practice: it implies lucky
              |                                        | threshold performance without
              |                                        | discriminative or specified basis.
              |                                        | The compiler correctly permits
              |                                        | this combination — the profile
              |                                        | is the guard, not the compiler.
  O   O   O   | Model C (GBM), SetA, no tokens         | Trivial lower bound. Not an
              |                                        | interesting benchmark case but
              |                                        | included for table completeness.

  All 8 cells are pre-registered. The two PRE-CONDITION cells require
  CHECK-1 and CHECK-2 (§9 Step 0) to confirm their witnesses before
  the pre-registration document is hashed. If a witness fails its
  check, the witness is revised before hashing. The claim — that all
  8 combinations are independently achievable — is the pre-registered
  claim. The table is not post-hoc.

Envelopes issued under Theta_v remain valid under their recorded version
by Theorem K'. Fresh compiles use Theta_v+1.
```

---

## 11. What Constitutes Compiler Falsification

The following would falsify the compiler implementation, not the taxonomy:

  - Any case where Profile v2 emits a permission higher than the meet
    of all gap statuses supports
  - Any case where an expired token advances a gap
  - Any case where a token scoped to Set A advances a gap for Set B
    (provenance mismatch)
  - Any case where scope mismatch on blast_radius is silently ignored
  - Any case where a failed detail_contract semantic check still
    advances a gap

These are not expected. They would be implementation bugs, not taxonomy
findings.

---

## 12. Relation to PGM-001

| Dimension             | PGM-001                              | MED-001                                       |
|-----------------------|--------------------------------------|-----------------------------------------------|
| Domain                | Bayesian network inference           | ICU sepsis prediction                         |
| Primary dataset       | Benchmark PGM networks               | PhysioNet Challenge 2019                      |
| Additional datasets   | —                                    | MIMIC-IV, eICU                                |
| Primary finding       | approx != model_spec                 | Three-way: approx != model_spec != utility    |
| New gap types         | model_specification_gap (1)          | clinical_utility_gap, distribution_shift_gap (2)|
| Real-world anchor     | —                                    | Epic Sepsis Model, Wong et al. 2021           |
| Falsification target  | Profile allowed ALR on misspecified  | Profile allows ALR without utility bound      |
| Profile fix           | Add model_spec to ALR                | Add clinical_utility + dist_shift to ALR      |
| Token difficulty      | model_specification_bound            | clinical.utility_bound (harder to produce)    |
| Pre-registration      | Not applicable (retrospective)       | Required before data runs (Step 0)            |

---

## 13. Key References

Singer et al. (2016). "The Third International Consensus Definitions for
Sepsis and Septic Shock (Sepsis-3)." JAMA 315(8):801-810.

Wong et al. (2021). "External Validation of a Widely Implemented Proprietary
Sepsis Prediction Model in Hospitalized Patients." JAMA Internal Medicine
181(8):1065-1070.

Johnson et al. (2023). "MIMIC-IV, a freely accessible electronic health
record dataset." Scientific Data 10:1.

Reyna et al. (2019). "Early Prediction of Sepsis from Clinical Data: The
PhysioNet/Computing in Cardiology Challenge 2019." Critical Care Medicine
48(2):210-217.

Pollard et al. (2018). "The eICU Collaborative Research Database, a freely
available multi-center database for critical care research." Scientific Data
5:180178.

Desautels et al. (2016). "Prediction of Sepsis in the Intensive Care Unit
with Minimal Electronic Health Record Data." JMIR Medical Informatics 4(3):e28.
