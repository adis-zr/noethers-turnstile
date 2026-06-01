# CASE-LIB-001: Multi-Domain Retrospective Case Library
## Admissibility Compiler Benchmark — Retrospective Audit Cases

**Document ID:** CASE-LIB-001  
**Status:** Draft v1  
**Relationship to MED-001:** Companion document. MED-001 is a prospective
benchmark (run models, verify compiler outputs). CASE-LIB-001 is a
retrospective audit: for real-world deployments with documented outcomes,
what would the compiler have emitted given the evidence available at
deployment time?

**Methodology:**
For each case:
1. Reconstruct gap statuses from public evidence at deployment time
2. Determine compiler output under a plausible profile for the claim class
3. Compare to the implicit permission actually granted
4. Identify which gap(s) were OPEN and should have been BOUNDED
5. Flag any gap types not in the current taxonomy

Gap status reconstruction is based on published papers, regulatory reports,
and public investigations. Where evidence is ambiguous, the reconstruction
is marked [INFERRED] and the basis stated. Cases are not included where
the public record is insufficient to pin gap statuses.

**New gap types induced by this library:**
  individual_population_gap    [NEW — §3.2]
  feedback_coupling_gap        [NEW — §3.3; distinct from existing coupling_gap]

All other gap types used here are from the existing taxonomy (ACS §8).

---

## 1. Gap Type Index

Gap types appearing in this library. Asterisk = new.

```
approximation_quality_gap   existing
model_specification_gap     existing (added PGM-001)
clinical_utility_gap        existing (added MED-001)
distribution_shift_gap      existing (added MED-001)
calibration_gap             existing
blast_radius_gap            existing
authority_gap               existing
freshness_gap               existing
proxy_gap                   existing
interference_gap            existing
coupling_gap                existing

individual_population_gap * NEW (§3.2)
  A model that accurately characterizes outcomes for a population provides
  no certifiable basis for predicting whether a specific individual will
  have that outcome. Population-level calibration is not individual-level
  predictive validity. This gap cannot be closed by improving approximation
  quality or model specification — it is a category difference in what a
  population score licenses for individual decisions.

feedback_coupling_gap *     NEW (§3.3)
  A model deployed in a decision-making system changes the distribution of
  future training data in a way that is not captured by existing
  interference_gap. Specifically: the model's outputs become inputs to
  future versions of itself, creating self-reinforcing error patterns that
  are invisible to standard distribution shift analysis. Distinct from
  interference_gap (which covers prediction-changes-the-thing-predicted)
  because here the feedback is through the model's own training data, not
  through the world state.
```

---

## 2. Case Format

Each case uses the following fields:

```
CASE-ID
Domain
System
Deployer
Year deployed
Action granted (implicit permission)
Reference (primary source)

Gap status at deployment (reconstructed):
  gap_type: status  [INFERRED if not directly evidenced]

Compiler output (retroactive):
  Under a reasonable profile for the claim class: [permission]
  Blocking gap(s): [list]

What was actually done:
  Implicit permission granted: [permission level]
  Scope: [description]

Outcome (hindsight):
  [what went wrong]

Primary missing obligation:
  [the specific evidence that, if required, would have blocked the deployment]

New gap types required:
  [NONE / list]
```

---

## 3. Cases — Medical Domain

### CASE-MED-001
**Epic Sepsis Model external validation failure**

```
Domain:     Medical
System:     Epic Sepsis Model (ESM), version unknown
Deployer:   Multiple health systems including UW Medicine
Year:       ~2017-2020 (deployment); 2021 (external validation published)
Reference:  Wong et al. (2021), JAMA Internal Medicine 181(8):1065-1070

Gap status at deployment:
  approximation_quality_gap:  BOUNDED  (AUC 0.76, reported by vendor)
  model_specification_gap:    BOUNDED  (predicts sepsis per Sepsis-3 criteria)
  clinical_utility_gap:       OPEN     [INFERRED: no external utility validation
                                        published at deployment; Wong et al.
                                        is the first external validation]
  distribution_shift_gap:     OPEN     [INFERRED: training population not
                                        publicly disclosed; no multi-site
                                        validation at deployment]
  calibration_gap:            UNKNOWN  (Epic did not publish calibration data)
  blast_radius_gap:           OPEN     (automated alert to nursing staff at
                                        scale; exact scope not publicly bounded)

Compiler output (retroactive):
  Permission: REV at most (approximation bounded; multiple required gaps OPEN)
  Blocking gaps: clinical_utility_gap, distribution_shift_gap, blast_radius_gap

What was actually done:
  Implicit permission: ALR to AAA
  Deployed to drive mandatory nursing alerts across multiple health systems
  with required response protocols

Outcome:
  External validation: sensitivity 33%, PPV 12% at deployed threshold
  67% of sepsis cases missed; 83% of alerts were false positives
  Significant alert fatigue; clinical workflow disruption

Primary missing obligation:
  clinical_utility_gap: no token bounding sensitivity/PPV at the operating
  threshold and blast radius was ever produced or required

New gap types required: NONE
```

---

### CASE-MED-002
**COVID-19 ML diagnostic models — systematic deployment failure**

```
Domain:     Medical
System:     Multiple (>300 COVID-19 ML models, systematic review)
Deployer:   Multiple hospitals globally
Year:       2020-2021
Reference:  Roberts et al. (2021), Nature Machine Intelligence 3:199-217
            (systematic review; found no model fit for clinical use)

Gap status at deployment:
  approximation_quality_gap:  OPEN     (most models not externally validated;
                                        many had methodological flaws including
                                        data leakage, wrong labels, inflated AUC)
  model_specification_gap:    OPEN     [INFERRED: most trained on early
                                        Wuhan/Italian cohorts; target variable
                                        definitions varied across studies]
  distribution_shift_gap:     OPEN     (near-universal; models not validated
                                        on populations outside training sites)
  calibration_gap:            OPEN     (almost universally unreported)
  clinical_utility_gap:       OPEN     (operating characteristics at clinical
                                        thresholds not reported for most)
  blast_radius_gap:           OPEN     (triage and treatment allocation; high
                                        stakes; scope not formally bounded)

Compiler output (retroactive):
  Permission: DIA at most (approximation quality not bounded for most models)
  Blocking gaps: all of the above

What was actually done:
  Multiple deployments at ALR to AAA authority
  Triage decisions, resource allocation, treatment prioritization

Outcome:
  Roberts et al.: "none of the identified studies are of sufficient quality
  to be used clinically"
  Multiple documented cases of biased performance (chest X-ray models
  detecting scanner type / hospital site rather than COVID pathology)

Primary missing obligation:
  approximation_quality_gap: external validation on a held-out population
  would have been the first gate; most models never cleared it

New gap types required: NONE
  (this case is notable for having ALL gaps OPEN simultaneously — a
  maximal-gap case useful for showing the compiler would have halted at DIA)
```

---

### CASE-MED-003
**Optum racial bias in health risk scoring**

```
Domain:     Medical
System:     Commercial health risk algorithm (Optum/UnitedHealth)
Deployer:   Hospitals, insurers — used for ~200M patients/year in US
Year:       ~2013-2019 (deployment); 2019 (bias study published)
Reference:  Obermeyer et al. (2019), Science 366(6464):447-453

Gap status at deployment:
  approximation_quality_gap:  BOUNDED  (model accurately predicted healthcare
                                        costs; that was the stated target)
  model_specification_gap:    OPEN     (training target = future healthcare
                                        COSTS; action target = identify patients
                                        who NEED more care. Cost is a proxy for
                                        need, but Black patients have lower costs
                                        than equally sick White patients due to
                                        access barriers. The proxy systematically
                                        diverges on the protected class.)
  proxy_gap:                  OPEN     (healthcare costs as proxy for healthcare
                                        needs; the proxy encodes access disparities)
  distribution_shift_gap:     BOUNDED  [INFERRED: performance on training
                                        distribution was validated]
  calibration_gap:            BOUNDED  (costs were well-calibrated)
  blast_radius_gap:           OPEN     (automated enrollment decisions affecting
                                        care management access; ~200M patients)

Compiler output (retroactive):
  Permission: REV at most
  Blocking gaps: model_specification_gap, proxy_gap, blast_radius_gap

What was actually done:
  Implicit permission: ALR to AAA
  Automated enrollment in high-risk care management programs
  Deployed at scale across US health system

Outcome:
  Obermeyer et al.: algorithm assigned same risk score to Black patients
  who were significantly sicker than White patients at that score level
  Racial bias in care management access; less care for equally sick
  Black patients

Primary missing obligation:
  proxy_gap: a token bounding the adequacy of cost as a proxy for need,
  with explicit analysis of proxy divergence on demographic subgroups,
  was never required. The model was certified on its stated target (cost
  prediction) without requiring certification that the target was adequate.

New gap types required: NONE
  (proxy_gap is existing; this case provides a canonical worked example)
```

---

### CASE-MED-004
**IBM Watson for Oncology — unsafe treatment recommendations**

```
Domain:     Medical
System:     IBM Watson for Oncology
Deployer:   Memorial Sloan Kettering (training); ~230 hospitals globally
Year:       2015-2019 (deployment); 2018 (STAT News investigation)
Reference:  Ross & Swetlitz (2018), STAT News (internal documents);
            Strickland (2019), IEEE Spectrum

Gap status at deployment:
  approximation_quality_gap:  OPEN     [INFERRED: system trained on synthetic
                                        cases constructed by MSK oncologists,
                                        not on real patient outcomes; no
                                        prospective validation published]
  model_specification_gap:    OPEN     (system generated treatment recommendations
                                        based on MSK's institutional practices;
                                        MSK's patient population differs
                                        significantly from global deployment
                                        populations)
  distribution_shift_gap:     OPEN     (trained on US academic cancer center
                                        cases; deployed in India, Southeast Asia,
                                        Europe with different cancer subtypes,
                                        treatment availability, guidelines)
  clinical_utility_gap:       OPEN     (no RCT or prospective validation of
                                        clinical outcomes)
  authority_gap:              OPEN     (recommendations presented as AI-generated
                                        expert guidance; clinicians reported
                                        difficulty overriding recommendations)

Compiler output (retroactive):
  Permission: DIA (approximation quality not bounded; no outcome validation)
  Blocking gaps: approximation_quality_gap, model_specification_gap,
                 distribution_shift_gap, clinical_utility_gap

What was actually done:
  Implicit permission: ALR at major cancer centers globally
  Treatment recommendations influencing chemotherapy decisions

Outcome:
  Internal IBM documents showed "unsafe and incorrect" recommendations
  in multiple cancer types (e.g., recommending treatments that conflicted
  with standard oncology guidelines for patients with severe bleeding)
  Program quietly scaled back; IBM sold Watson Health in 2022

Primary missing obligation:
  approximation_quality_gap: the system was never validated against real
  patient outcomes in a prospective study. The training data (synthetic
  cases from MSK oncologists) is not a valid basis for an approximation
  quality certificate.

New gap types required: NONE
```

---

### CASE-MED-005
**Deterioration models and ICU alarm fatigue**

```
Domain:     Medical
System:     Various ICU deterioration/early warning scores (EWS)
            including Epic EWS, Modified Early Warning Score (MEWS),
            and proprietary deterioration indexes
Deployer:   Multiple health systems
Year:       2010s-present
Reference:  Drew et al. (2014), Heart Rhythm 11(12):2108-2114 (alarm fatigue)
            Cvach (2012), AACN Advanced Critical Care 23(4):378-395

Gap status at deployment:
  approximation_quality_gap:  BOUNDED  (AUC typically 0.75-0.85 in training)
  model_specification_gap:    BOUNDED  (target: detect deterioration)
  clinical_utility_gap:       OPEN     [INFERRED: false positive rates
                                        extremely high; 80-99% of alarms
                                        clinically non-actionable in studies]
  blast_radius_gap:           OPEN     (each alert triggers mandatory response
                                        protocol; alert volume at scale creates
                                        alarm fatigue)
  calibration_gap:            OPEN     [INFERRED: threshold tuning for low
                                        false negative rate drives very low PPV]

Compiler output (retroactive):
  Permission: REV
  Blocking gaps: clinical_utility_gap, blast_radius_gap, calibration_gap

What was actually done:
  Implicit permission: ALR to AAA
  Mandatory alert protocols triggered by automated scores

Outcome:
  Desensitization to alarms; nurses acknowledge and silence without acting
  Studies document missed true deterioration events due to alarm fatigue
  Alarm fatigue is now a Joint Commission-recognized patient safety issue

Primary missing obligation:
  blast_radius_gap: the scope of action triggered per alert (mandatory
  response protocol) was never formally bounded against the expected
  false positive rate. A blast radius token for this action class would
  need to show that NNT for the mandatory response is acceptable given
  the protocol's resource cost and attention cost.

New gap types required: NONE
```

---

## 4. Cases — Criminal Justice Domain

### CASE-CJ-001
**COMPAS recidivism score and pretrial detention**

```
Domain:     Criminal Justice
System:     COMPAS (Correctional Offender Management Profiling for
            Alternative Sanctions), Equivant/Northpointe
Deployer:   ~100+ US jurisdictions including Broward County FL
Year:       1998-present (deployment); 2016 (ProPublica analysis)
Reference:  Angwin et al. (2016), ProPublica ("Machine Bias")
            Dressel & Farid (2018), Science Advances 4(1):eaao5580
            Larson et al. (2017), ProPublica (methodology)

Gap status at deployment:
  approximation_quality_gap:  BOUNDED  (model predicts recidivism at
                                        population level with reasonable AUC)
  model_specification_gap:    BOUNDED  [INFERRED: target = recidivism
                                        probability for population segment;
                                        model achieves this stated target]
  individual_population_gap:  OPEN     [NEW GAP TYPE]
                                        (a score calibrated to population
                                        recidivism rates does not certify
                                        whether THIS individual will reoffend;
                                        using population statistics to restrict
                                        an individual's liberty requires a
                                        different evidentiary standard that
                                        the score does not and cannot provide)
  calibration_gap:            BOUNDED  [INFERRED: score roughly calibrated
                                        across risk levels within racial groups]
  blast_radius_gap:           OPEN     (detention is among the highest-stakes
                                        actions in the system; blast radius
                                        token would need to bound the scope of
                                        liberty deprivation licensed by the score)
  authority_gap:              OPEN     [INFERRED: score structurally treated
                                        as a floor for detention decisions;
                                        judicial override carries burden of
                                        justification]

Compiler output (retroactive):
  Permission: DIA at most
  Blocking gaps: individual_population_gap, blast_radius_gap, authority_gap
  Note: even if these gaps were bounded, the individual_population_gap
  may be unboundable for this action class — population statistics cannot
  in principle certify individual predictions with sufficient precision
  for detention decisions.

What was actually done:
  Implicit permission: ALR to AAA
  COMPAS scores influenced bail, sentencing, and parole decisions
  at scale across the criminal justice system

Outcome:
  ProPublica analysis: Black defendants labeled high-risk at 2x the rate
  of White defendants when they did not reoffend
  Dressel & Farid: COMPAS no more accurate than untrained humans
  Fundamental structural critique: population recidivism rates were used
  to license individual detention decisions

Primary missing obligation:
  individual_population_gap: a token bounding the adequacy of
  population-level risk scores for individual liberty decisions.
  This token may be structurally unproducible for this action class
  (detention), which means the correct compiler output is DIA
  permanently — the evidence required to license the action class
  does not exist and cannot be constructed.

New gap types required:
  individual_population_gap [NEW]
  Definition: a statistical model may accurately characterize outcomes
  for a population without providing certifiable basis for predicting
  whether a specific individual will have that outcome. Population-level
  calibration is not individual-level predictive validity.
```

---

### CASE-CJ-002
**Arkansas Medicaid eligibility algorithm**

```
Domain:     Criminal Justice / Government Benefits
System:     InterRAI needs assessment algorithm (licensed by Optum)
            used to determine Medicaid personal care hours
Deployer:   State of Arkansas Department of Human Services
Year:       2016 (deployment); 2019 (federal court ruling)
Reference:  Ledgerwood v. Jegley, 8th Circuit (2019)
            Lecher (2018), The Verge (investigation)
            Eubanks (2018), "Automating Inequality" (context)

Gap status at deployment:
  approximation_quality_gap:  BOUNDED  [INFERRED: model predicts care hour
                                        needs per assessment protocol]
  model_specification_gap:    OPEN     (algorithm trained on population averages
                                        for conditions like cerebral palsy and
                                        diabetes; specific individuals with
                                        atypical presentations received sharply
                                        reduced hours that did not match their
                                        actual care needs)
  individual_population_gap:  OPEN     [NEW GAP TYPE]
                                        (population averages for care needs
                                        by condition cannot certify individual
                                        care requirements for people with
                                        complex, atypical presentations)
  authority_gap:              OPEN     (algorithm outputs not subject to
                                        meaningful human review; no explanation
                                        provided for benefit reductions;
                                        individuals could not challenge
                                        algorithmic decisions they couldn't see)
  blast_radius_gap:           OPEN     (benefit cuts affected ability to live
                                        independently; extremely high stakes)

Compiler output (retroactive):
  Permission: DIA at most
  Blocking gaps: model_specification_gap, individual_population_gap,
                 authority_gap, blast_radius_gap

What was actually done:
  Implicit permission: AAA
  Automatic benefit determination at scale; no human review for individual
  cases below a threshold; no explanation mechanism

Outcome:
  Multiple beneficiaries had care hours cut by 20-50% without explanation
  Donna Ray Ledgerwood (cerebral palsy) and others unable to function
  without restored hours; one plaintiff died during litigation
  Federal court found due process violations; algorithm use suspended

Primary missing obligation:
  authority_gap: no mechanism for human review or explanation of individual
  decisions. The authority token for automatic action at AAA level must
  bound the scope of decisions made without human oversight. An authority
  token that cannot be produced for this action class means the ceiling
  is REV at most.

New gap types required:
  individual_population_gap [NEW — same as CASE-CJ-001]
```

---

### CASE-CJ-003
**Predictive policing — PredPol/Geolitica**

```
Domain:     Criminal Justice
System:     PredPol (now Geolitica) predictive policing algorithm
Deployer:   ~150 US police departments
Year:       2012-2021 (PredPol eventually shut down 2021)
Reference:  Lum & Isaac (2016), Significance 13(5):14-19
            Ensign et al. (2018), FAT* proceedings
            Stop LAPD Spying Coalition investigations

Gap status at deployment:
  approximation_quality_gap:  BOUNDED  [INFERRED: model accurately predicts
                                        where reported crimes occurred in
                                        training data]
  model_specification_gap:    OPEN     (training target = reported crime
                                        location; action target = predict
                                        where crime WILL occur. Reported
                                        crime is a function of policing
                                        patterns, not just actual crime.)
  feedback_coupling_gap:      OPEN     [NEW GAP TYPE]
                                        (increased policing in predicted areas
                                        generates more reported crime in those
                                        areas, which updates the model to
                                        predict more crime there — a
                                        self-reinforcing loop invisible to
                                        distribution shift analysis because
                                        the model is "accurate" on its
                                        training distribution at every step)
  interference_gap:           OPEN     (prediction changes deployment of
                                        police, which changes crime patterns)
  distribution_shift_gap:     OPEN     [INFERRED: model trained on historical
                                        reported crime; not validated on
                                        actual crime rates independent of
                                        policing patterns]
  blast_radius_gap:           OPEN     (patrol allocation, stop-and-frisk
                                        authorization, public safety resource
                                        distribution; high-stakes actions at
                                        neighborhood scale)

Compiler output (retroactive):
  Permission: DIA at most
  Blocking gaps: model_specification_gap, feedback_coupling_gap,
                 interference_gap, distribution_shift_gap

What was actually done:
  Implicit permission: ALR to AAA
  Automated patrol deployment and stop authorization recommendations

Outcome:
  Lum & Isaac: model reliably sends police to over-policed areas,
  generating more arrests there, generating more training data there,
  creating a self-reinforcing loop
  Disproportionate surveillance of communities of color
  PredPol discontinued 2021 after mounting evidence of bias and
  effectiveness questions

Primary missing obligation:
  feedback_coupling_gap: no token bounding the effect of deployment
  on future training data was ever required. Standard distribution
  shift analysis cannot detect this failure mode because the model
  remains accurate on its (self-generated) training distribution.

New gap types required:
  feedback_coupling_gap [NEW]
  Definition: a model deployed in a decision-making system that changes
  the distribution of future training data through its own outputs,
  creating self-reinforcing error patterns invisible to standard
  distribution shift analysis. Distinct from interference_gap (which
  covers prediction-changes-the-thing-predicted) because here the
  feedback loop runs through the training data pipeline.
```

---

### CASE-CJ-004
**Chicago Police Strategic Subject List (heat list)**

```
Domain:     Criminal Justice
System:     Strategic Subject List (SSL) / "heat list"
            Chicago Police Department / Illinois Institute of Technology
Deployer:   Chicago Police Department
Year:       2013-2019
Reference:  Saunders et al. (2016), RAND Corporation evaluation
            Chicago Inspector General (2020), evaluation report

Gap status at deployment:
  approximation_quality_gap:  BOUNDED  [INFERRED: SSL score predicted
                                        prior arrest patterns]
  model_specification_gap:    OPEN     (training target = prior criminal
                                        justice involvement; action target =
                                        predict future violence. Prior arrest
                                        is heavily correlated with policing
                                        intensity, not just behavior.)
  individual_population_gap:  OPEN     (SSL score characterizes population-level
                                        co-occurrence patterns; does not certify
                                        individual future behavior)
  proxy_gap:                  OPEN     (prior arrests as proxy for violence
                                        risk; proxy encodes disparate policing)
  blast_radius_gap:           OPEN     (preemptive police contact with listed
                                        individuals; "custom notifications"
                                        at homes; extremely high stakes)
  authority_gap:              OPEN     (listed individuals not informed of
                                        their score or the basis for it)

Compiler output (retroactive):
  Permission: DIA
  Blocking gaps: model_specification_gap, individual_population_gap,
                 proxy_gap, blast_radius_gap, authority_gap

What was actually done:
  Implicit permission: AAA (preemptive police action)
  Police visited individuals at home to "notify" them of their score
  Score used in parole and probation decisions

Outcome:
  RAND evaluation: no evidence of reduction in gun violence
  Inspector General: "CPD cannot demonstrate that SSL is effective"
  Civil liberties concerns; individuals listed had no recourse
  Program discontinued 2019

Primary missing obligation:
  model_specification_gap: prior arrest as a proxy for future violence
  risk requires a proxy_gap token showing the proxy is adequate; that
  token requires showing the proxy doesn't systematically diverge from
  the true target in ways that encode existing biases. That token
  was never constructed or required.

New gap types required: NONE (individual_population_gap already identified)
```

---

## 5. Cases — Employment Domain

### CASE-EMP-001
**Amazon internal recruiting tool**

```
Domain:     Employment
System:     Amazon's ML-based resume screening tool
Deployer:   Amazon (internal)
Year:       2014-2017 (development/use); 2018 (Reuters investigation)
Reference:  Dastin (2018), Reuters ("Amazon scraps secret AI recruiting tool")

Gap status at deployment:
  approximation_quality_gap:  BOUNDED  [INFERRED: model predicted which
                                        resumes resembled those of previously
                                        hired candidates]
  model_specification_gap:    OPEN     (training target = resemblance to
                                        historical hires; action target =
                                        identify best future candidates.
                                        Historical hires encode historical
                                        gender bias in tech hiring.)
  proxy_gap:                  OPEN     (historical hiring decisions as proxy
                                        for candidate quality; proxy encodes
                                        gender disparities in tech)
  distribution_shift_gap:     OPEN     [INFERRED: candidate pool and job
                                        market changed; historical hires
                                        are not representative of current
                                        best candidates]
  blast_radius_gap:           OPEN     (resume screening at scale; systematic
                                        exclusion of qualified candidates)

Compiler output (retroactive):
  Permission: REV at most
  Blocking gaps: model_specification_gap, proxy_gap

What was actually done:
  Implicit permission: ALR
  Automated ranking of resumes with systematic downgrading of
  candidates who attended all-women's colleges or whose resumes
  contained the word "women's"

Outcome:
  Amazon discovered the gender bias; tool scrapped 2017
  All-women's colleges downgraded; gender-specific terms penalized

Primary missing obligation:
  proxy_gap: a token bounding the adequacy of historical hiring
  decisions as a proxy for candidate quality, with explicit analysis
  of proxy divergence on demographic subgroups

New gap types required: NONE
```

---

### CASE-EMP-002
**HireVue facial expression and speech analysis**

```
Domain:     Employment
System:     HireVue video interview AI (facial/speech feature analysis)
Deployer:   ~700 companies including Unilever, Goldman Sachs
Year:       2014-2021 (facial analysis feature)
Reference:  Harwell (2019), Washington Post
            Drew (2021), The Guardian (EEOC filing)
            HireVue suspended facial analysis 2021

Gap status at deployment:
  approximation_quality_gap:  OPEN     [INFERRED: model analyzed facial
                                        expressions and voice patterns;
                                        no published validation of whether
                                        these features predict job performance
                                        at all]
  model_specification_gap:    OPEN     (target = undefined "employability"
                                        or "competency" construct from facial
                                        features; no evidence this construct
                                        is validly measured by facial analysis)
  clinical_utility_gap:       OPEN     (no predictive validity study linking
                                        scores to actual job performance)
  distribution_shift_gap:     OPEN     [INFERRED: facial analysis has known
                                        accuracy disparities across skin tones
                                        and facial structures]
  blast_radius_gap:           OPEN     (automated pre-screening; candidates
                                        rejected without human review)

Compiler output (retroactive):
  Permission: DIA (approximation quality not bounded)
  Blocking gaps: all gaps OPEN

What was actually done:
  Implicit permission: AAA (automated rejection at pre-screen stage)
  No human review for rejected candidates
  Candidates not informed of the basis for rejection

Outcome:
  HireVue suspended facial analysis in 2021 following EEOC scrutiny
  and mounting evidence of no predictive validity for facial features
  Illinois AI Video Interview Act (2019) required disclosure to candidates

Primary missing obligation:
  approximation_quality_gap: no evidence was ever produced that
  facial expression features predict job performance. This is a
  DIA-level gap — the entire basis of the token is missing.

New gap types required: NONE
```

---

### CASE-EMP-003
**Apple Card gender credit discrimination**

```
Domain:     Finance / Employment (credit access)
System:     Apple Card credit limit algorithm (Goldman Sachs)
Deployer:   Goldman Sachs / Apple
Year:       2019
Reference:  Telford (2019), Washington Post
            New York State DFS investigation (2019, settled)
            Pärna (2020), fintech regulatory analysis

Gap status at deployment:
  approximation_quality_gap:  BOUNDED  [INFERRED: model predicted credit
                                        risk by Goldman's internal standards]
  model_specification_gap:    OPEN     [INFERRED: model used features
                                        correlated with gender despite gender
                                        not being an explicit input; training
                                        data encoded historical credit
                                        disparities]
  proxy_gap:                  OPEN     (features used as credit proxies
                                        correlated with gender; proxy gap
                                        not audited for demographic divergence)
  distribution_shift_gap:     OPEN     [INFERRED: credit history features
                                        encode historical discrimination;
                                        not validated for demographic parity]
  authority_gap:              OPEN     (no explanation mechanism for credit
                                        decisions; applicants could not
                                        identify or challenge algorithmic
                                        basis)

Compiler output (retroactive):
  Permission: REV at most
  Blocking gaps: proxy_gap, model_specification_gap, authority_gap

What was actually done:
  Implicit permission: AAA
  Automated credit limit assignment at scale with no demographic audit

Outcome:
  Twitter complaints including tech VC David Heinemeier Hansson
  reporting wife received 20x lower limit than him despite better
  credit score; Steve Wozniak reported similar
  NYDFS investigation found Goldman violated fair lending law
  Goldman settled; algorithm revised

Primary missing obligation:
  proxy_gap: a token bounding the adequacy of the credit features
  as proxies for creditworthiness, with explicit demographic parity
  analysis, was never required before deployment at scale.

New gap types required: NONE
```

---

## 6. Cases — Autonomous Systems Domain

### CASE-AUT-001
**Uber Advanced Technologies Group — Elaine Herzberg fatality**

```
Domain:     Autonomous Systems
System:     Uber ATG self-driving vehicle (Volvo XC90)
            Object classification and path prediction system
Deployer:   Uber ATG
Year:       2018 (incident); NTSB report 2019
Reference:  NTSB (2019), Highway Accident Report HWY18MH010
            Wakabayashi (2018), New York Times

Gap status at deployment:
  approximation_quality_gap:  OPEN     [INFERRED: NTSB found system correctly
                                        detected object 6 seconds before impact
                                        but misclassified it 3 times (vehicle,
                                        then bicycle, then other) before
                                        correct classification too late to
                                        brake. Classification instability
                                        not bounded.]
  model_specification_gap:    OPEN     (system designed to classify objects
                                        into discrete categories; pedestrian
                                        with bicycle outside crosswalk was
                                        an edge case not in training distribution)
  distribution_shift_gap:     OPEN     (training on standard scenarios;
                                        edge cases including jaywalking
                                        pedestrians with bicycles not
                                        adequately covered)
  freshness_gap:              OPEN     (1-second latency in classification
                                        pipeline; at vehicle speed, 1 second
                                        = ~15 meters traveled; freshness
                                        requirement not formally bounded
                                        against braking distance)
  blast_radius_gap:           OPEN     (autonomous operation at speed on
                                        public road; action = no brake applied;
                                        blast radius = pedestrian death)
  authority_gap:              OPEN     (safety operator not monitoring
                                        system; phone distraction noted
                                        by NTSB; no fallback mechanism
                                        when operator inattentive)

Compiler output (retroactive):
  Permission: DIA (approximation quality not bounded for edge cases;
              classification instability not addressed)
  Blocking gaps: all gaps OPEN or UNKNOWN

What was actually done:
  Implicit permission: AAA (autonomous operation on public road)

Outcome:
  Elaine Herzberg killed; first pedestrian fatality caused by
  autonomous vehicle
  NTSB found: object classification system inadequate; safety
  operator inattentive; Uber had disabled Volvo's automatic
  emergency braking
  Uber ATG eventually sold to Aurora

Primary missing obligation:
  freshness_gap: formal bounding of the classification latency
  against worst-case braking distance requirements at operational
  speed was never produced. The system had 1-second classification
  update latency; at 45 mph this is ~20 meters. The blast radius
  token for autonomous pedestrian operation must bound latency
  requirements; no such token existed.

New gap types required: NONE
```

---

### CASE-AUT-002
**Boeing 737 MAX MCAS**

```
Domain:     Autonomous Systems (automated flight control)
System:     Maneuvering Characteristics Augmentation System (MCAS)
Deployer:   Boeing; certified by FAA
Year:       2017-2019 (deployment); 2018-2019 (two crashes)
Reference:  Joint Authorities Technical Review (2019)
            US House Committee on Transportation report (2020)
            FAA (2020), AD 2020-24-02

Note: MCAS is not an ML system in the conventional sense. It is
included because it is a canonical case of automated consequential
action with authority_gap and blast_radius_gap as primary failure modes.
The compiler framework applies directly.

Gap status at deployment:
  model_specification_gap:    OPEN     (MCAS designed to activate on one
                                        AOA sensor input; specification did
                                        not require sensor disagreement
                                        check or sensor failure mode analysis)
  approximation_quality_gap:  BOUNDED  [INFERRED: within its specified
                                        operating range, MCAS performed
                                        as designed]
  authority_gap:              OPEN     (system could override pilot inputs
                                        repeatedly without pilot knowledge
                                        that MCAS was active; no authority
                                        bound on number of override cycles)
  blast_radius_gap:           OPEN     (override applied nose-down trim
                                        repeatedly; at low altitude, blast
                                        radius = catastrophic; no formal
                                        bounding of worst-case action scope)
  freshness_gap:              OPEN     (single AOA sensor; no redundancy
                                        check; faulty sensor reading treated
                                        as current fresh data)

Compiler output (retroactive):
  Permission: DIA to REV (specification adequate within range; authority
              and blast radius not bounded for worst-case sensor failure)
  Blocking gaps: authority_gap, blast_radius_gap, model_specification_gap
                 (for sensor failure modes)

What was actually done:
  Implicit permission: AAA (full override authority, repeating, without
  pilot awareness or consent)

Outcome:
  Lion Air 610: 189 deaths (October 2018)
  Ethiopian Airlines 302: 157 deaths (March 2019)
  737 MAX grounded globally for 20 months
  Boeing fined $2.5B; multiple FAA certification failures identified

Primary missing obligation:
  authority_gap: a token bounding the scope of override authority —
  specifically, limiting the number of repeat activations and requiring
  pilot-visible annunciation of MCAS activation — was never required.
  The authority contract for automated flight control override must bound
  the maximum authority the system can exercise before requiring pilot
  confirmation.

New gap types required: NONE
```

---

## 7. Cases — Government Benefits Domain

### CASE-GOV-001
**Dutch childcare benefit fraud algorithm (Toeslagenaffaire)**

```
Domain:     Government Benefits
System:     Automated fraud detection classifier (internal Dutch Tax Authority)
Deployer:   Dutch Tax Authority (Belastingdienst)
Year:       ~2012-2019 (deployment); 2020 (parliamentary inquiry)
Reference:  Van Bree et al. (2021), Dutch Parliamentary Inquiry Committee
            report "Unprecedented Injustice"
            Aanhangsel Handelingen II 2020/21 (parliamentary record)

Gap status at deployment:
  approximation_quality_gap:  UNKNOWN  (algorithm details not publicly
                                        released; accuracy on training
                                        distribution unknown)
  model_specification_gap:    OPEN     (training target = patterns associated
                                        with historical fraud cases; action
                                        target = identify actual fraud.
                                        Childcare assistance applications from
                                        dual-nationality families flagged at
                                        higher rates regardless of actual
                                        fraud probability.)
  proxy_gap:                  OPEN     (features correlated with dual
                                        nationality used as fraud proxies;
                                        proxy encodes ethnic profiling)
  individual_population_gap:  OPEN     (population-level flag rates for
                                        demographic groups used to license
                                        individual repayment demands)
  authority_gap:              OPEN     (automated demands for full repayment
                                        over multiple years; no meaningful
                                        human review; no explanation of
                                        algorithmic basis; appeals process
                                        effectively inaccessible)
  blast_radius_gap:           OPEN     (full repayment demands ranging to
                                        tens of thousands of euros;
                                        families bankrupted; extremely
                                        high-stakes financial action)

Compiler output (retroactive):
  Permission: DIA (approximation quality unknown; authority and blast
              radius clearly unbounded)
  Blocking gaps: all major gaps OPEN or UNKNOWN

What was actually done:
  Implicit permission: AAA
  Automatic repayment demands; aggressive collection; families destroyed

Outcome:
  ~26,000 families wrongly accused of fraud
  Families bankrupted, children placed in foster care in some cases
  Dutch government resigned January 2021
  Compensation program established; billions in repayments reversed
  European Parliament cited as trigger for EU AI Act development

Primary missing obligation:
  authority_gap: no token was ever required bounding the scope of
  automated repayment demands — specifically, the requirement for
  human review before demands above a threshold, and the requirement
  for explanation accessible to the recipient. The authority contract
  for automatic financial action at this blast radius must require
  human-in-the-loop review; no such contract existed.

New gap types required: NONE
```

---

### CASE-GOV-002
**Allegheny Family Screening Tool (child welfare)**

```
Domain:     Government Benefits / Child Welfare
System:     Allegheny Family Screening Tool (AFST)
Deployer:   Allegheny County Department of Human Services, Pennsylvania
Year:       2016-present
Reference:  Eubanks (2018), "Automating Inequality," Chapter 4
            Chouldechova et al. (2018), FAT* proceedings
            Keddell (2019), Aotearoa New Zealand Social Work

Gap status at deployment:
  approximation_quality_gap:  BOUNDED  [INFERRED: model trained on
                                        administrative data; AUC reported
                                        in published validation]
  model_specification_gap:    OPEN     (training target = future administrative
                                        contact with child welfare system;
                                        action target = identify children at
                                        risk of harm. Prior system contact
                                        encodes surveillance intensity, not
                                        just risk.)
  proxy_gap:                  OPEN     (administrative contact rates as
                                        proxy for maltreatment risk; proxy
                                        encodes disparate surveillance of
                                        low-income families and families
                                        of color who use public services)
  individual_population_gap:  OPEN     (population contact rates do not
                                        certify individual child risk)
  distribution_shift_gap:     OPEN     [INFERRED: model trained on
                                        families already in contact with
                                        system; not validated on broader
                                        population including families who
                                        have not had system contact]
  authority_gap:              OPEN     [INFERRED: score presented to
                                        call screeners; degree to which
                                        screeners can override high-risk
                                        scores is unclear; structural
                                        authority ambiguity]

Compiler output (retroactive):
  Permission: REV
  Blocking gaps: model_specification_gap, proxy_gap, individual_population_gap

What was actually done:
  Implicit permission: ALR
  Score used in call-screening decisions at Allegheny County child
  welfare hotline

Outcome:
  Chouldechova et al.: score exhibits racial disparities in false
  positive rates consistent with training data disparities
  Black families flagged at higher rates; low-income families
  using public services disproportionately represented
  Program continues with ongoing academic scrutiny

Primary missing obligation:
  proxy_gap: a token bounding the adequacy of administrative contact
  rates as a proxy for child maltreatment risk, with explicit analysis
  of proxy divergence by race and income, was never required before
  deployment. The AFST uses "number of prior hotline calls" as a
  feature — but calls are a function of surveillance intensity, not
  just risk.

New gap types required: NONE (individual_population_gap already identified)
```

---

## 8. Gap Coverage Matrix

This matrix shows which gap types are exercised (O=OPEN at deployment,
causing compiler to halt below actual deployed permission) across cases.

```
                          aq   ms   cu   ds   cal  br   au   fr   prx  int  cpl  i/p  fbc
CASE-MED-001 (Epic)        .    .    O    O    ?    O    .    .    .    .    .    .    .
CASE-MED-002 (COVID)       O    O    O    O    O    O    .    .    .    .    .    .    .
CASE-MED-003 (Optum)       .    O    .    .    .    O    .    .    O    .    .    .    .
CASE-MED-004 (Watson)      O    O    O    O    .    .    O    .    .    .    .    .    .
CASE-MED-005 (alarms)      .    .    O    .    O    O    .    .    .    .    .    .    .
CASE-CJ-001  (COMPAS)      .    .    .    .    .    O    O    .    .    .    O    O    .
CASE-CJ-002  (Arkansas)    .    O    .    .    .    O    O    .    .    .    .    O    .
CASE-CJ-003  (PredPol)     .    O    .    O    .    O    .    .    .    O    .    .    O
CASE-CJ-004  (Chicago)     .    O    .    .    .    O    O    .    O    .    .    O    .
CASE-EMP-001 (Amazon)      .    O    .    O    .    O    .    .    O    .    .    .    .
CASE-EMP-002 (HireVue)     O    O    O    .    .    O    .    .    .    .    .    .    .
CASE-EMP-003 (Apple Card)  .    O    .    O    .    .    O    .    O    .    .    .    .
CASE-AUT-001 (Uber)        O    O    .    O    .    O    O    O    .    .    .    .    .
CASE-AUT-002 (Boeing)      .    O    .    .    .    O    O    O    .    .    .    .    .
CASE-GOV-001 (Dutch)       ?    O    .    .    .    O    O    .    O    .    .    O    .
CASE-GOV-002 (AFST)        .    O    .    O    .    .    O    .    O    .    .    O    .

Key: O = OPEN at deployment (gap was unbounded when action was taken)
     . = BOUNDED or not applicable
     ? = UNKNOWN (insufficient public information)

Column key:
  aq=approximation_quality  ms=model_specification  cu=clinical_utility
  ds=distribution_shift     cal=calibration         br=blast_radius
  au=authority              fr=freshness            prx=proxy
  int=interference          cpl=coupling            i/p=individual_population*
  fbc=feedback_coupling*    (* = new gap types)
```

---

## 9. Summary of New Gap Types Induced

**individual_population_gap**
Induced by: CASE-CJ-001, CASE-CJ-002, CASE-CJ-004, CASE-GOV-001,
            CASE-GOV-002

Definition: A statistical model may accurately characterize outcomes
for a population without providing certifiable basis for predicting
whether a specific individual will have that outcome. Population-level
calibration is not individual-level predictive validity.

Cannot be closed by: improving AUC, better model specification, larger
training data. The gap is structural to the use case: using population
statistics to license individual high-stakes decisions.

May be permanently unboundable for certain action classes (e.g.,
pretrial detention based on population recidivism rates). If so,
the correct compiler output for those action classes is DIA permanently.

Relationship to existing gaps:
  Not model_specification_gap: the model may be correctly specified
  for its population-level target and still have this gap OPEN for
  individual decisions.
  Not distribution_shift_gap: the model may generalize perfectly to
  the deployment population and still have this gap OPEN.

**feedback_coupling_gap**
Induced by: CASE-CJ-003 (PredPol)

Definition: A model deployed in a decision-making system that changes
the distribution of future training data through its own outputs,
creating self-reinforcing error patterns invisible to standard
distribution shift analysis. The model may remain accurate on its
own (self-generated) training distribution at every time step while
drifting arbitrarily from the true target.

Cannot be detected by: standard distribution shift analysis, because
the model's training distribution is itself a function of the model's
past outputs. A distribution shift token scoped to the training
population is not informative when the training population is
endogenous to the model.

Relationship to existing gaps:
  Distinct from interference_gap: interference_gap covers
  prediction-changes-the-thing-being-predicted (the world state).
  feedback_coupling_gap covers prediction-changes-the-training-data
  (the evidence base for future certificates). The feedback runs
  through the model's own epistemics, not through the world.

---

## 10. Proposed Additions to Core Benchmark Suite

Beyond the 16 retrospective cases, the following extensions are recommended:

### 10.1 Additional domains to add in future revisions

Criminal justice — bail algorithm outcomes (Laura and John Arnold
  Foundation PSA validation data, public)
Medical — mammography AI false negative rates (FDA postmarket surveillance)
Finance — mortgage denial algorithms (HMDA data, public)
Social media — content recommendation and mental health (Facebook
  internal research, 2021 leak)

### 10.2 Cross-case invariants to check

For all 16 cases, the compiler output should be strictly below the
implicit permission actually granted. If any case has compiler output
>= actual deployed permission, that is a potential failure of the
framework: either the profile is too weak or the gap analysis is wrong.

Expected result: compiler output < actual permission for all 16 cases,
with the gap between them explained by exactly the OPEN gaps identified.

### 10.3 Relationship to prospective benchmarks

CASE-LIB-001 is a retrospective audit. MED-001 is prospective. The
two serve different functions:

  MED-001: Can the compiler be falsified by running real models?
  CASE-LIB-001: Would the compiler have prevented real harms?

The combination is the paper's empirical contribution. MED-001 shows
the compiler is structurally sound (non-promotion, anti-laundering).
CASE-LIB-001 shows it would have been practically useful.

---

## 11. References

Angwin et al. (2016). "Machine Bias." ProPublica.
Chouldechova et al. (2018). "A case study of algorithm-assisted decision
  making in child maltreatment hotline screening." FAT* proceedings.
Dastin (2018). "Amazon scraps secret AI recruiting tool." Reuters.
Dressel & Farid (2018). "The accuracy, fairness, and limits of predicting
  recidivism." Science Advances 4(1):eaao5580.
Ensign et al. (2018). "Runaway feedback loops in predictive policing."
  FAT* proceedings.
Eubanks (2018). "Automating Inequality." St. Martin's Press.
Harwell (2019). "A face-scanning algorithm increasingly decides whether
  you deserve the job." Washington Post.
Joint Authorities Technical Review (2019). "MCAS Design, Development,
  Test and Evaluation." Boeing 737 MAX.
Lum & Isaac (2016). "To predict and serve?" Significance 13(5):14-19.
NTSB (2019). Highway Accident Report HWY18MH010.
Obermeyer et al. (2019). "Dissecting racial bias in an algorithm used
  to manage the health of populations." Science 366(6464):447-453.
Roberts et al. (2021). "Common pitfalls and recommendations for using
  machine learning to detect and prognosticate for COVID-19 using chest
  radiographs and CT scans." Nature Machine Intelligence 3:199-217.
Ross & Swetlitz (2018). "IBM's Watson supercomputer recommended 'unsafe
  and incorrect' cancer treatments." STAT News.
Saunders et al. (2016). "Predictions put into practice." RAND Corporation.
Van Bree et al. (2021). "Unprecedented Injustice." Dutch Parliamentary
  Inquiry Committee report.
Wong et al. (2021). "External Validation of a Widely Implemented
  Proprietary Sepsis Prediction Model." JAMA Internal Medicine 181(8).
