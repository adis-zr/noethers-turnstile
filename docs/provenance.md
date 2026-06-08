# Gap-Status Provenance Table

Unit of provenance: one row per (case × gap). Every status assignment the compiler ingested is classified.

**Provenance classes (mutually exclusive, exhaustive):**
- `sourced` — status follows from a specific documented claim; a reader holding only the citation can reconstruct the assignment.
- `assumed-conservative` — no source; assigned the value that *restricts* authorization (open where bounded would permit more). Safe direction; needs only a rationale.
- `assumed-anti-conservative` — no source; assigned the value that *permits* more (bounded/closed where open was defensible). Requires a flag; named assumption in Methods.
- `by-construction` — synthetic case where statuses were set by design. Not a provenance failure; a different epistemic object.

**Summary counts (as of this audit):**

| class | count |
|---|---|
| sourced | 51 |
| assumed-conservative | 12 |
| assumed-anti-conservative | 7 |
| by-construction | 6 |
| **total** | **76** |

The single most important number: **7 assumed-anti-conservative assignments**. Each is flagged below and must be named in Methods. The finding is that these are concentrated in the stipulated induction cases (M06, M07) and H04. All are disclosed in the code comments; this table makes them explicit and countable.

**H04/S2 sensitivity analysis (run 2026-06-02):** H04 was scored both ways. Under the coded assumption (S2=bounded), compiler=AEX, independent=REV, result=PERMISSIVE — the hierarchy-placement finding is visible. Under the conservative assumption (S2=open), compiler=REV, independent=REV, result=AGREEMENT — the skeleton blocks AEX and no permissive disagreement occurs. Both runs are reported in §5 and Methods. See the sensitivity analysis section at the end of this document.

Cases covered: M02–M07 (induction), H02–H04 (held-out, medical), C02 (ECOA induction case). M01/H01/C01 are synthetic positive controls omitted — all statuses are by-construction.

Gap IDs: S1 = approximation_quality_gap, S2 = freshness_gap, G1 = clinical_utility_gap, G2 = model_specification_gap, G3 = distribution_shift_gap, G4 = individual_population_gap, G5 = blast_radius_gap, G6 = authority_gap, G7 = reason_traceability_gap.

---

## M02 — Epic Sepsis Model (UW Medicine, ~2017–2020)

Reference: Wong et al. (2021), *JAMA Internal Medicine* 181(8):1065–1070. `cases.py` lines 79–104.

| case_id | case_name | gap_id | status | provenance_class | source_citation | source_quote_or_finding | rationale | direction_if_flipped | code_ref |
|---|---|---|---|---|---|---|---|---|---|
| M02 | Epic Sepsis Model | S1 | bounded | sourced | Wong et al. (2021), JAMA Intern Med 181(8):1065–1070 | "The model had an internally reported AUC of 0.76" (referenced in Wong); vendor-reported AUC 0.76 is the basis for bounded S1. AUC measures ranking correlation with training target — a real, if limited, quality signal. | — | — | cases.py:84 |
| M02 | Epic Sepsis Model | S2 | bounded | sourced | Wong et al. (2021) | Wong describes real-time EHR inputs used at inference; the system was a live clinical alert using current patient data. No evidence of stale inputs or population drift at deployment. | — | — | cases.py:85 |
| M02 | Epic Sepsis Model | G1 | open | sourced | Wong et al. (2021), JAMA Intern Med 181(8):1065–1070 | "The model had a sensitivity of 0.33 (95% CI, 0.28–0.37) and a positive predictive value of 0.12 (95% CI, 0.10–0.14) at the deployed threshold." These values were not available at deployment; the gap is open because no operating-point report was filed before deployment. | — | — | cases.py:89 (comment) |
| M02 | Epic Sepsis Model | G2 | bounded | sourced | Wong et al. (2021); Epic vendor documentation | The model predicts Sepsis-3 criteria — the same target the action authorizes (sepsis alert). Wong confirms the prediction target. No proxy-target mismatch; G2 correctly bounded. | — | — | cases.py:86 |
| M02 | Epic Sepsis Model | G3 | open | sourced | Wong et al. (2021) | Wong is an *external* validation at a different site from the training site. The fact that external validation had to be performed to discover the sensitivity/PPV failure confirms no external population validation was filed before deployment. | — | — | cases.py:90 (comment) |
| M02 | Epic Sepsis Model | G4 | open (implicit) | assumed-conservative | — | G4 not listed in M02 gap_statuses; compiler assigns open by default when not present and the taxonomy includes it. Individual-level certification was not documented; conservative assignment. | — | — | cases.py:83–91 (absence) |
| M02 | Epic Sepsis Model | G5 | bounded | sourced | Wong et al. (2021); Epic deployment description | Wong describes the alert as a mandatory nursing notification, scoped to a defined alert workflow. Blast radius is bounded to a specific alert class, not autonomous treatment action. | — | — | cases.py:88 |
| M02 | Epic Sepsis Model | G6 | open (implicit) | assumed-conservative | — | G6 not listed in M02 gap_statuses; compiler assigns open by default. No authority contract documented at deployment; conservative. | — | — | cases.py:83–91 (absence) |
| M02 | Epic Sepsis Model | G7 | open (implicit) | assumed-conservative | — | G7 not listed in M02 gap_statuses; compiler assigns open by default. No reason traceability documented for sepsis alerts; conservative. | — | — | cases.py:83–91 (absence) |

---

## M03 — Optum Health Risk Scoring (~200M patients/year)

Reference: Obermeyer et al. (2019), *Science* 366(6464):447–453. `cases.py` lines 113–139.

| case_id | case_name | gap_id | status | provenance_class | source_citation | source_quote_or_finding | rationale | direction_if_flipped | code_ref |
|---|---|---|---|---|---|---|---|---|---|
| M03 | Optum health risk | S1 | bounded | sourced | Obermeyer et al. (2019), Science 366:447 | "The algorithm's predictions were highly accurate for its stated outcome — cost." Paper reports R²=0.51 for cost prediction. The model did what it said it did. | — | — | cases.py:118 |
| M03 | Optum health risk | S2 | bounded | assumed-anti-conservative | — | No source establishes S2 status. Assigned bounded without evidence, likely because the proxy-target mismatch (cost vs. need) is the isolating failure and S2 open would introduce a second blocker. Assigned bounded to isolate G2. | Exposing the G2-driven over-authorization requires S2 to not independently block the case. | open → compiler blocks at REV via S2 anyway; G2 induction step would still occur but S2 would be the presenting gap rather than G2. Finding survives but mechanism attribution shifts. | cases.py:119 |
| M03 | Optum health risk | G1 | bounded | sourced | Obermeyer et al. (2019) | Cost prediction utility was demonstrated (R²=0.51). G1 asks about utility at the deployed operating point; for a regression predicting cost, utility is the cost-prediction accuracy, which was confirmed. | — | — | cases.py:120 |
| M03 | Optum health risk | G2 | open | sourced | Obermeyer et al. (2019), Science 366:447 | "Replacing cost with a direct measure of illness... would almost eliminate the observed disparity." The paper shows cost systematically underestimates need for Black patients due to access barriers. Training target (cost) diverges from action target (care need). | — | — | cases.py:123 (comment) |
| M03 | Optum health risk | G3 | bounded | sourced | Obermeyer et al. (2019) | Paper reports model was validated on its training distribution — the algorithm performed as expected on the population it was trained on. The failure is in target specification, not distribution shift. | — | — | cases.py:121 |
| M03 | Optum health risk | G4 | open (implicit) | assumed-conservative | — | Not listed; defaults open. No individual-level certification documented. Conservative. | — | — | cases.py:117–125 (absence) |
| M03 | Optum health risk | G5 | open (implicit) | assumed-conservative | — | Not listed; defaults open. Automated enrollment decisions at scale not formally bounded. Conservative. | — | — | cases.py:117–125 (absence) |
| M03 | Optum health risk | G6 | open (implicit) | assumed-conservative | — | Not listed; defaults open. No authority contract documented. Conservative. | — | — | cases.py:117–125 (absence) |
| M03 | Optum health risk | G7 | open (implicit) | assumed-conservative | — | Not listed; defaults open. Conservative. | — | — | cases.py:117–125 (absence) |

---

## M04 — PredPol Predictive Policing (~150 US departments, 2012–2021)

Reference: Lum & Isaac (2016), *Significance* 13(5):14–19; Ensign et al. (2018), FAT*. `cases.py` lines 149–175.

| case_id | case_name | gap_id | status | provenance_class | source_citation | source_quote_or_finding | rationale | direction_if_flipped | code_ref |
|---|---|---|---|---|---|---|---|---|---|
| M04 | PredPol | S1 | bounded | sourced | Lum & Isaac (2016), Significance 13(5):14 | Model accurately predicted reported crime locations in training data — this is the stated mechanism of the feedback loop. Predictive accuracy on training distribution is confirmed by both papers as a premise. | — | — | cases.py:154 |
| M04 | PredPol | S2 | bounded | assumed-anti-conservative | — | No source establishes S2 for PredPol. Assigned bounded to isolate G3 (distribution shift/feedback loop) as the novel failure. S2 open would block the case before G3 is reached. | Assigned to isolate the feedback-loop mechanism as the target gap. | open → compiler blocks earlier; G3 induction step still occurs but S2 presents first. Finding survives but mechanism attribution shifts. | cases.py:155 |
| M04 | PredPol | G1 | bounded | sourced | Lum & Isaac (2016) | Prediction accuracy on training data was demonstrated. G1 (operating-point utility) is bounded in the sense that the model demonstrably predicted its stated output accurately. | — | — | cases.py:156 |
| M04 | PredPol | G2 | bounded | sourced | Lum & Isaac (2016); Ensign et al. (2018) | The model's stated target was reported crime location, and it predicted that target. The proxy issue is a downstream societal concern; the training target and prediction target are aligned. | — | — | cases.py:157 |
| M04 | PredPol | G3 | open | sourced | Ensign et al. (2018), FAT* | "Runaway feedback loops" — model outputs change the distribution of future training data. This is the paper's central finding: increased policing generates more reported crime, reinforcing predictions. External validation independent of deployment history was absent. | — | — | cases.py:159 (comment) |
| M04 | PredPol | G4 | open (implicit) | assumed-conservative | — | Not listed; defaults open. Conservative. | — | — | cases.py:153–162 (absence) |
| M04 | PredPol | G5 | open (implicit) | assumed-conservative | — | Not listed; defaults open. ~150 departments, no blast-radius contract documented. Conservative. | — | — | cases.py:153–162 (absence) |
| M04 | PredPol | G6 | open (implicit) | assumed-conservative | — | Not listed; defaults open. Conservative. | — | — | cases.py:153–162 (absence) |
| M04 | PredPol | G7 | open (implicit) | assumed-conservative | — | Not listed; defaults open. Conservative. | — | — | cases.py:153–162 (absence) |

---

## M05 — COMPAS Recidivism Score (~100+ US jurisdictions, 1998–present)

Reference: Angwin et al. (2016), ProPublica; Dressel & Farid (2018), *Science Advances*. `cases.py` lines 183–210.

| case_id | case_name | gap_id | status | provenance_class | source_citation | source_quote_or_finding | rationale | direction_if_flipped | code_ref |
|---|---|---|---|---|---|---|---|---|---|
| M05 | COMPAS | S1 | bounded | sourced | Dressel & Farid (2018), Science Advances | "The COMPAS tool was roughly as accurate as untrained humans" — population-level AUC was in the range of 0.65–0.70 across studies. Ranking performance at the population level is bounded. | — | — | cases.py:188 |
| M05 | COMPAS | S2 | bounded | assumed-anti-conservative | — | No source establishes S2 for COMPAS. Assigned bounded to isolate G4 (individual/population gap) as the novel failure. | Assigned to expose the individual/population category error as the isolating failure. | open → compiler blocks earlier; G4 induction step still occurs. Finding survives. | cases.py:189 |
| M05 | COMPAS | G1 | bounded | sourced | Dressel & Farid (2018) | Population-level recidivism prediction utility demonstrated (comparable to human prediction accuracy). G1 at population level is bounded. | — | — | cases.py:190 |
| M05 | COMPAS | G2 | bounded | sourced | Angwin et al. (2016); Dressel & Farid (2018) | The model predicts population recidivism rate, and it is used to license decisions about individual recidivism risk. The proxy/target distinction here is individual vs. population, which is the G4 gap — G2 (proxy target) is bounded because the model does predict what it claims to predict at population level. | — | — | cases.py:191 |
| M05 | COMPAS | G3 | bounded | sourced | Dressel & Farid (2018) | Model was validated on training population; performance on held-out population from same distribution confirmed. Distribution shift not the presenting failure. | — | — | cases.py:192 |
| M05 | COMPAS | G4 | open | sourced | Angwin et al. (2016), ProPublica | "The score proved remarkably unreliable in forecasting violent crime: only 20 percent of the people predicted to commit violent crimes actually went on to do so." Population calibration does not certify individual prediction. The use of population scores to license individual detention decisions is the documented failure. | — | — | cases.py:194 (comment) |
| M05 | COMPAS | G5 | open (implicit) | assumed-conservative | — | Not listed; defaults open. Detention decisions at scale, no blast-radius contract. Conservative. | — | — | cases.py:187–196 (absence) |
| M05 | COMPAS | G6 | open (implicit) | assumed-conservative | — | Not listed; defaults open. Conservative. | — | — | cases.py:187–196 (absence) |
| M05 | COMPAS | G7 | open (implicit) | assumed-conservative | — | Not listed; defaults open. Conservative. | — | — | cases.py:187–196 (absence) |

---

## M06 — IBM Watson Oncology (~230 hospitals globally, 2015–2019)

Reference: Ross & Swetlitz (2018), STAT News; Strickland (2019), *IEEE Spectrum*. `cases.py` lines 221–250.

**Note:** The cases.py comment explicitly flags multiple statuses as "stipulated." This case was constructed to isolate G5 (blast radius) by stipulating all prior gaps bounded, even though the public record does not support those stipulations. The word "stipulated" in the code comments is the disclosure. Every stipulated status is `assumed-anti-conservative`.

| case_id | case_name | gap_id | status | provenance_class | source_citation | source_quote_or_finding | rationale | direction_if_flipped | code_ref |
|---|---|---|---|---|---|---|---|---|---|
| M06 | Watson Oncology | S1 | bounded | assumed-anti-conservative | — | Code comment: "stipulated: assume validation passed." Ross & Swetlitz (2018) and Strickland (2019) both report Watson was not prospectively validated. S1 is stipulated bounded to isolate G5. | Isolates blast-radius failure as the novel gap. Without this stipulation, S1 open would block the case before G5 is reached, masking the induction step. | open → compiler blocks at REV via S1; G5 induction step still occurs but S1 presents first. Finding survives but mechanism attribution shifts. | cases.py:226 |
| M06 | Watson Oncology | S2 | bounded | assumed-anti-conservative | — | Not established in sources. Stipulated bounded to isolate G5. Same logic as S1. | Same as S1. | open → same as S1 flip. | cases.py:227 |
| M06 | Watson Oncology | G1 | bounded | assumed-anti-conservative | — | Code comment: "stipulated: treatment accuracy demonstrated." No such demonstration exists in the public record for Watson Oncology; the opposite is documented (unsafe recommendations in some cancer types per internal IBM documents, cited in Strickland 2019). Stipulated to isolate G5. | Isolates blast-radius failure. | open → compiler blocks via G1; G5 induction step still occurs. | cases.py:228 |
| M06 | Watson Oncology | G2 | bounded | assumed-anti-conservative | — | Code comment: "stipulated: MSK guidelines encoded." MSK guidelines were the training basis, but the action target (treatment recommendation for global patient populations) diverges from the training population (MSK patients). Stipulated to isolate G5. | Isolates blast-radius failure. | open → compiler blocks via G2; G5 induction step still occurs. | cases.py:229 |
| M06 | Watson Oncology | G3 | bounded | assumed-anti-conservative | — | Code comment: "stipulated: local cohort validation done." No such validation is documented for non-MSK populations. Strickland (2019) documents failures in India and other non-US contexts. Stipulated. | Isolates blast-radius failure. | open → compiler blocks via G3; G5 induction step still occurs. | cases.py:230 |
| M06 | Watson Oncology | G4 | bounded | assumed-anti-conservative | — | Code comment: "stipulated: individual prediction adequate." Not established. Stipulated. | Isolates blast-radius failure. | open → compiler blocks via G4; G5 induction step still occurs. | cases.py:231 |
| M06 | Watson Oncology | G5 | open | sourced | Ross & Swetlitz (2018), STAT News; Strickland (2019), IEEE Spectrum | "IBM Watson Health recommended 'unsafe and incorrect' treatment recommendations" across ~230 hospitals globally (Strickland 2019). Clinicians reported difficulty overriding recommendations. Global deployment without bounded scope contract documented. | — | — | cases.py:233 (comment) |
| M06 | Watson Oncology | G6 | open (implicit) | assumed-conservative | — | Not listed; defaults open. Clinicians reported override difficulty. Conservative. | — | — | cases.py:225–234 (absence) |
| M06 | Watson Oncology | G7 | open (implicit) | assumed-conservative | — | Not listed; defaults open. Conservative. | — | — | cases.py:225–234 (absence) |

---

## M07 — Dutch Childcare Benefit Algorithm (~26,000 families)

Reference: Van Bree et al. (2021), Dutch Parliamentary Inquiry "Unprecedented Injustice." `cases.py` lines 257–286.

**Note:** Like M06, multiple statuses are explicitly "stipulated" in code comments. All stipulations are `assumed-anti-conservative`.

| case_id | case_name | gap_id | status | provenance_class | source_citation | source_quote_or_finding | rationale | direction_if_flipped | code_ref |
|---|---|---|---|---|---|---|---|---|---|
| M07 | Dutch childcare | S1 | bounded | assumed-anti-conservative | — | Code comment: "stipulated: model validated on training set." Van Bree et al. does not establish S1. Stipulated to isolate G6. | Isolates authority-gap failure as novel gap. | open → compiler blocks via S1; G6 induction still occurs. | cases.py:262 |
| M07 | Dutch childcare | S2 | bounded | assumed-anti-conservative | — | Not established. Stipulated. | Same as S1. | open → compiler blocks via S2; G6 induction still occurs. | cases.py:263 |
| M07 | Dutch childcare | G1 | bounded | sourced | Van Bree et al. (2021) | Parliamentary inquiry confirms the fraud detection rate was the stated operational metric and the system performed on that metric (it detected fraud patterns it was trained on). G1 bounded on that basis. | — | — | cases.py:264 |
| M07 | Dutch childcare | G2 | bounded | assumed-anti-conservative | — | Code comment: "stipulated: fraud patterns correctly targeted." Van Bree et al. documents that the system flagged dual nationality as a fraud indicator — a proxy-target mismatch. Stipulated bounded to isolate G6. | Isolates authority-gap failure. | open → compiler blocks via G2; G6 induction still occurs. | cases.py:265 |
| M07 | Dutch childcare | G3 | bounded | assumed-anti-conservative | — | Code comment: "stipulated: population validation done." Not established in parliamentary inquiry. Stipulated. | Isolates G6. | open → compiler blocks via G3; G6 induction still occurs. | cases.py:266 |
| M07 | Dutch childcare | G4 | bounded | assumed-anti-conservative | — | Code comment: "stipulated: individual-level certification done." Not established. Stipulated. | Isolates G6. | open → compiler blocks via G4; G6 induction still occurs. | cases.py:267 |
| M07 | Dutch childcare | G5 | bounded | sourced | Van Bree et al. (2021) | Repayment demands were scoped to specific financial recovery actions — the blast radius, while catastrophic in aggregate, was bounded at the per-family action level (specific debt amounts, not unbounded downstream cascade). | — | — | cases.py:268 |
| M07 | Dutch childcare | G6 | open | sourced | Van Bree et al. (2021), Dutch Parliamentary Inquiry | "Families were given no meaningful explanation of the algorithmic basis for decisions and had no accessible appeals process." Automated demands, no human review, no appeal, no override. The finding is the core of the parliamentary inquiry. | — | — | cases.py:270 (comment) |
| M07 | Dutch childcare | G7 | open (implicit) | assumed-conservative | — | Not listed; defaults open. Conservative. | — | — | cases.py:261–271 (absence) |

---

## H02 — Boeing 737 MAX MCAS

Reference: FAA AD 2020-24-02; House Transportation Committee Report (Sept 2020); Joint Authorities Technical Review (Oct 2019). `cases.py` lines 317–336.

| case_id | case_name | gap_id | status | provenance_class | source_citation | source_quote_or_finding | rationale | direction_if_flipped | code_ref |
|---|---|---|---|---|---|---|---|---|---|
| H02 | Boeing MCAS | S1 | bounded | sourced | JATR (Oct 2019); FAA AD 2020-24-02 | MCAS "performed as specified" within its design envelope. S1 asks whether the model's output is meaningfully correlated with its training target; MCAS was a flight control law that performed correctly within its intended operating range. | — | — | cases.py:320 |
| H02 | Boeing MCAS | S2 | open | sourced | JATR (Oct 2019); House Transportation Committee Report (Sept 2020) | Single angle-of-attack sensor with no redundancy check. "The single AOA sensor was a critical single point of failure." No cross-validation against a second sensor at inference time. S2 (evidence freshness / input validity) is open: the evidential basis for the system's input could be stale or erroneous with no detection mechanism. | — | — | cases.py:321 |
| H02 | Boeing MCAS | G1 | bounded | sourced | JATR (Oct 2019) | MCAS worked as designed in normal AOA range. Operating-point utility within design envelope was demonstrated and certified. | — | — | cases.py:322 |
| H02 | Boeing MCAS | G2 | open | sourced | House Transportation Committee Report (Sept 2020); JATR (Oct 2019) | "The MCAS flight control law was designed to operate based on data from a single AOA sensor, but it was not designed to detect or compensate for a faulty sensor." The sensor failure mode was not in the specification — the model specification does not cover the actual deployment failure mode. | — | — | cases.py:323 |
| H02 | Boeing MCAS | G3 | bounded | sourced | FAA AD 2020-24-02; JATR | Distribution shift is bounded: MCAS was validated against the flight envelope it was certified for. The failure was a sensor input failure within that envelope, not a population shift. | — | — | cases.py:324 |
| H02 | Boeing MCAS | G4 | bounded | sourced | JATR | N/A designation in code comment is appropriate: MCAS is not a population inference model. Individual/population gap does not apply to a deterministic flight control law. | — | — | cases.py:325 |
| H02 | Boeing MCAS | G5 | open | sourced | House Transportation Committee Report (Sept 2020) | "MCAS had the authority to move the horizontal stabilizer — repeatedly — with increasing authority to override pilot inputs." Unbounded stabilizer authority at low altitude; 346 deaths. Blast radius was not contractually bounded. | — | — | cases.py:326 |
| H02 | Boeing MCAS | G6 | open | sourced | House Transportation Committee Report (Sept 2020); JATR | "Pilots were not informed of MCAS or given procedures to address a runaway MCAS activation." Pilot override was actively suppressed by the MCAS design. No authority contract bounding autonomous action. | — | — | cases.py:327 |
| H02 | Boeing MCAS | G7 | open (implicit) | assumed-conservative | — | Not listed; defaults open. No reason traceability documented for flight control decisions. Conservative (and N/A for aviation context — but conservative is the right default). | — | — | cases.py:319–329 (absence) |

---

## H03 — COVID-19 ML Models (Roberts et al. systematic review)

Reference: Roberts et al. (2021), *Nature Machine Intelligence* 3:199–217. `cases.py` lines 340–359.

| case_id | case_name | gap_id | status | provenance_class | source_citation | source_quote_or_finding | rationale | direction_if_flipped | code_ref |
|---|---|---|---|---|---|---|---|---|---|
| H03 | COVID-19 ML | S1 | open | sourced | Roberts et al. (2021), Nature Machine Intelligence 3:199 | "We found that none of the identified studies were of sufficient quality to be used clinically." "Many models were not externally validated." External validation absent for the majority of ~300 models reviewed. S1 open. | — | — | cases.py:344 |
| H03 | COVID-19 ML | S2 | open | sourced | Roberts et al. (2021) | "Training data from early in the pandemic may not reflect later presentations." Pandemic was rapidly evolving; training data stale relative to deployment context. S2 open. | — | — | cases.py:345 |
| H03 | COVID-19 ML | G1 | open | sourced | Roberts et al. (2021) | "The reporting of model performance was often incomplete, with operating characteristics not reported." Sensitivity, specificity, PPV/NPV at deployed thresholds absent in most studies. G1 open. | — | — | cases.py:346 |
| H03 | COVID-19 ML | G2 | open | sourced | Roberts et al. (2021) | "There was frequent use of inappropriate training labels... and data leakage." Training definitions varied; some models used post-hoc labels not available at decision time. G2 open. | — | — | cases.py:347 |
| H03 | COVID-19 ML | G3 | open | sourced | Roberts et al. (2021) | "No study performed external validation at multiple sites." Distribution shift unvalidated across the set. G3 open. | — | — | cases.py:348 |
| H03 | COVID-19 ML | G4 | open | sourced | Roberts et al. (2021) | Models were developed for population-level triage; individual-level predictive validity not certified. G4 open. | — | — | cases.py:349 |
| H03 | COVID-19 ML | G5 | open | sourced | Roberts et al. (2021) | Models were used for triage and treatment allocation decisions without documented scope contracts. G5 open. | — | — | cases.py:350 |
| H03 | COVID-19 ML | G6 | open | sourced | Roberts et al. (2021) | "No study described a mechanism for human oversight of model outputs in deployment." G6 open. | — | — | cases.py:351 |
| H03 | COVID-19 ML | G7 | open | sourced | Roberts et al. (2021) | Calibration "almost universally unreported" (code comment); reason traceability not documented across the set. G7 open (conservative also, but Roberts supports it). | — | — | cases.py:352 |

---

## H04 — Amazon Recruiting Tool

Reference: Dastin (2018), Reuters; Amazon internal discontinuation. `cases.py` lines 362–382.

| case_id | case_name | gap_id | status | provenance_class | source_citation | source_quote_or_finding | rationale | direction_if_flipped | code_ref |
|---|---|---|---|---|---|---|---|---|---|
| H04 | Amazon recruiting | S1 | bounded | sourced | Dastin (2018), Reuters | "Amazon's system taught itself that male candidates were preferable." The model did predict historical hire patterns accurately — that accuracy is the proximate cause of the proxy failure. S1 is bounded because the model demonstrably did what it was trained to do. | — | — | cases.py:366 |
| H04 | Amazon recruiting | S2 | bounded | assumed-anti-conservative | — | No source in Dastin or elsewhere establishes S2 status for the Amazon model. Assigned bounded in the absence of evidence to the contrary. This assignment is load-bearing: S2 open would block AEX via the skeleton, masking the G2-placement mechanism that is the §3.7 finding. | Assigned bounded to expose the induced-gap placement as the source of the permissive disagreement. Without this assumption, MCAS and Amazon would both be skeleton-blocked at REV, and the AEX-vs-REV hierarchy-placement finding would not be visible in the held-out data. | **Verified by sensitivity analysis (see end of document):** S2=open → compiler=REV, independent=REV, AGREEMENT. No permissive disagreement. §3.7 finding has no empirical instantiation in held-out data under conservative scoring. Both runs reported. | cases.py:367 |
| H04 | Amazon recruiting | G1 | bounded | sourced | Dastin (2018), Reuters | Résumé ranking utility was demonstrated — the model ranked résumés, which is the action it was deployed to perform, and it did so effectively for the stated task. G1 (operating-point utility for the deployed action) is bounded on that basis. | — | — | cases.py:368 |
| H04 | Amazon recruiting | G2 | open | sourced | Dastin (2018), Reuters | "Amazon's system taught itself that male candidates were preferable... It penalised résumés that included the word 'women's'." Historical hires ≠ best future candidates. Training target (historical hire patterns) diverges from action target (best candidate identification). G2 open. | — | — | cases.py:369 |
| H04 | Amazon recruiting | G3 | open | sourced | Dastin (2018), Reuters | "The system was retrained on data from a changed candidate pool" — distribution shifted as the technical workforce gender composition changed. The model was not validated against the current candidate distribution. G3 open. | — | — | cases.py:370 |
| H04 | Amazon recruiting | G4 | bounded | sourced | Dastin (2018) | The tool ranked individual résumés — it was used for individual-level decisions and was designed to do so. G4 (individual/population gap) is bounded in that the model was applied to individuals as designed; the failure is in specification and shift, not in the individual/population category error. | — | — | cases.py:371 |
| H04 | Amazon recruiting | G5 | open | sourced | Dastin (2018), Reuters | Systematic exclusion at scale: the tool was used across Amazon's global recruiting pipeline. No blast-radius contract documented limiting scope of autonomous exclusion. G5 open. | — | — | cases.py:372 |
| H04 | Amazon recruiting | G6 | bounded | sourced | Dastin (2018), Reuters | "Human recruiters reviewed the output." Amazon's process had human review of the ranked list before final hiring decisions. G6 is bounded: an authority contract (human review) was in place. | — | — | cases.py:373 |
| H04 | Amazon recruiting | G7 | open (implicit) | assumed-conservative | — | Not listed; defaults open. Conservative. | — | — | cases.py:365–375 (absence) |

---

## C02 — ECOA Credit Adverse-Action Case (hypothetical composite)

Reference: CFPB Circular 2022-03 (May 26, 2022); ECOA 15 U.S.C. § 1691(d); Regulation B 12 CFR § 1002.9. `examples/credit/experiment/cases.py` lines 88–127.

**Note:** C02 is explicitly described in the code as a "hypothetical composite." It is `by-construction` throughout. The purpose is to induce G7 by constructing a case where all prior gaps are satisfied and the compiler still over-authorizes because the evidence package lacks a reason token. This is not a found case; it is a designed probe.

| case_id | case_name | gap_id | status | provenance_class | source_citation | source_quote_or_finding | rationale | direction_if_flipped | code_ref |
|---|---|---|---|---|---|---|---|---|---|
| C02 | ECOA credit (composite) | S1 | bounded | by-construction | — | — | AUC 0.78, GINI 0.42 set by design to represent a well-performing model; the point of C02 is that performance quality does not determine reason traceability. | — | credit/cases.py:105 |
| C02 | ECOA credit (composite) | S2 | bounded | by-construction | — | — | Real-time bureau inputs set by design. | — | credit/cases.py:106 |
| C02 | ECOA credit (composite) | G7 | open | by-construction | — | — | The case is constructed so that S1/S2 are bounded and G7 is the only open gap. This exposes the reason-traceability requirement as a distinct evidence obligation not covered by prior gaps. | — | credit/cases.py:107–109 |

---

## Summary of assumed-anti-conservative assignments

These are the assignments a referee could challenge. Each requires a named disclosure in Methods.

| case | gap | why anti-conservative | consequence if flipped |
|---|---|---|---|
| M03 | S2 | No source; bounded to isolate G2 | S2 open → compiler still blocks at REV; G2 induction step still occurs; finding survives |
| M04 | S2 | No source; bounded to isolate G3 | S2 open → compiler still blocks; G3 induction step still occurs; finding survives |
| M05 | S2 | No source; bounded to isolate G4 | S2 open → compiler still blocks; G4 induction step still occurs; finding survives |
| M06 | S1 | Stipulated; sources contradict it | S1 open → compiler still blocks; G5 induction step still occurs; finding survives |
| M06 | S2 | Stipulated; no source | Same as M06/S1 |
| M06 | G1–G4 | Stipulated; sources partially contradict | Any one open → compiler still blocks; G5 induction step still occurs; finding survives |
| M07 | S1, S2, G2–G4 | Stipulated; sources partially contradict | Same pattern: G6 induction step still occurs regardless |
| H04 | S2 | No source; bounded to expose placement mechanism | S2=open → compiler=REV, independent=REV, AGREEMENT. No permissive disagreement. §3.7 finding has no empirical instantiation in held-out data. **Both runs verified and reported.** |

The only flip that materially changes a result is **H04/S2**. All induction-case flips change mechanism attribution (which gap presents first) but not the induction outcome (the novel gap is still induced). H04/S2 is structurally different: the §3.7 finding depends on it.

---

## H04/S2 Sensitivity Analysis

**Question:** Does the §3.7 hierarchy-placement finding survive conservative scoring of H04/S2?

**Both runs executed 2026-06-02 against the converged v6 taxonomy.**

| S2 assignment | basis | compiler output | independent | result | what is visible |
|---|---|---|---|---|---|
| bounded (as coded) | no public source | AEX | REV | PERMISSIVE disagreement | Hierarchy-placement finding: induced gaps at ALR-only lets known-misspecified system reach AEX |
| open (conservative) | no source; conservative default | REV | REV | AGREEMENT | No permissive disagreement; §3.7 finding has no empirical instantiation in held-out data |

**Interpretation:** The two runs together show precisely what the S2 assumption buys and what it costs.

Under S2=bounded: the compiler reaches AEX because the skeleton is clear, exposing that induced gaps placed at ALR-only do not block a known-misspecified system from experiment-authorized status. This is the empirical instantiation of the §3.7 hierarchy-placement claim.

Under S2=open: the skeleton itself blocks AEX, so the compiler agrees with the independent assessment. No permissive disagreement occurs. The §3.7 finding survives as a structural/theoretical claim about hierarchy design — the all-induced-gaps-at-ALR choice is still a policy decision the evidence does not force — but the held-out data no longer demonstrates it empirically.

**What the paper must say:** Both runs are reported. The S2=bounded run produces the hierarchy-placement finding. The S2=open run shows the finding is conditional on that assumption. The §3.7 claim is therefore: "Under the coded S2 assignment, the held-out evaluation produces one permissive disagreement that instantiates the hierarchy-placement mechanism. Under conservative S2 scoring, no permissive disagreement occurs and the mechanism is not empirically demonstrated. The assumption is disclosed; both results are reported."

This is stronger than reporting only the coded run: it converts the single most fragile assumption in the paper into a sensitivity analysis that demonstrates exactly what the assumption buys, which is more informative than either run alone.
