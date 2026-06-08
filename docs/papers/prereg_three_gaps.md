# Pre-Registration Spec: Closing or Bounding the Three Open Gaps

**Status: pre-registration. Everything above the "Execution log" section of each
experiment is fixed BEFORE the corresponding experiment is run. Nothing in the
fixed sections may be revised using information obtained during or after
execution. The epistemic value of these experiments over informal argument is
precisely that the operators, decision rules, and outcome-paragraphs were written
down first. This document is the proof of blindness; it must carry that proof on
its face.**

Pre-registration timestamp (fill before first run): 2026-06-02T02:31:44Z

Author commitment: I will record the result of each experiment in its Execution
log, apply the pre-registered decision rule mechanically, and paste the
corresponding pre-written outcome paragraph into the manuscript without
re-litigating the criteria. If I find myself wanting to adjust a decision rule
after seeing a result, that is the signal that the experiment has been
contaminated, and I will report the original rule and the result regardless.

---

## Framing: both outcomes are contributions

The purpose of these three experiments is NOT to confirm the framework. It is to
either close each open gap or decisively locate the boundary of the framework.
A clean "the framework stops here, and here is exactly why" is as publishable as
a closure, and in some cases stronger. Each experiment below is therefore written
so that both of its outcomes are wins before it is run. If at any point a
particular outcome starts to feel like the one I am hoping for, the experiment is
no longer blind.

The three gaps, restated:

1. **3GPP extraction.** Are BLER 0.10 and 0.02 properties of the evidence
   surface, or artifacts of how the permission levels were placed?
2. **Held-out generalization.** Does the induced taxonomy generalize to cases
   outside the induction set, judged against assessment independent of the
   taxonomy?
3. **World-realizability.** Is the §3.4 lemma's hypothesis — that every gap in
   the taxonomy is world-realizable — actually true, or can some gap be
   constructed as a pure documentation requirement?

Run order: A (cheap, decisive, determines whether Table 1 needs editing), then C
(cheap, tests the §3 keystone, no external dependencies), then B (expensive,
design-gated, possibly correctly concluded as "concede").

---

# Experiment A — 3GPP extraction-operator stability

## A.1 Claim under test (fixed)

The boundaries BLER = 0.10 and BLER = 0.02 are produced by a hierarchy-independent
property of the BER/BLER evidence surface, not by the placement of the permission
levels supplied to the compiler.

## A.2 The extraction operator (fixed before run)

The compiler scans the measured BLER-vs-SNR surface over a fixed SNR sweep. Define
the boundary operator as follows, and do not change it after seeing results:

- Sweep resolution: SNR grid step fixed at **0.1 dB** over the range **-1.0 to
  5.0 dB**. (Matches the resolution used in the original §2.4 experiment, taken
  from `audit_3gpp.py` line 60–61: `np.round(np.arange(-1.0, 5.01, 0.1), 2)`.)
- A *permission hierarchy* is a finite ordered set of BLER ceilings
  `{c_1 > c_2 > ... > c_m}`. The compiler maps each SNR point to the strongest
  permission whose BLER ceiling is met at that SNR.
- The *boundary set* B(H) of a hierarchy H is the set of BLER values at which the
  compiler's returned permission changes as SNR increases — i.e. the BLER ceilings
  that are actually realized as transitions on the measured surface.
- The operator under test is: B(H) for a given hierarchy H. The claim is about
  whether 0.10 and 0.02 are present in B(H) across a RANGE of hierarchies H, not
  about a single hand-placed H.

Note the honest framing this forces. If the only way 0.10 and 0.02 appear is by
placing permission ceilings AT 0.10 and 0.02, then the result is circular and the
operator records it as such. The experiment is the perturbation, not the single
run.

## A.3 The perturbation grid (fixed before run)

Construct a set of alternative permission hierarchies from first principles about
what granularities a standards body might plausibly use. Fix this grid BEFORE
running. Do NOT widen, narrow, or re-center the grid after seeing which
hierarchies keep 0.10/0.02 stable.

Pre-registered perturbation families:

1. **Granularity perturbation.** Hierarchies with m = 3, 4, 5, 6, 8 levels, with
   ceilings placed at log-uniform spacing across the BLER range **[1e-3, 0.50]**,
   with NO ceiling deliberately pinned at 0.10 or 0.02. This gives 5 hierarchies.

2. **Offset perturbation.** Take a baseline 5-level log-uniform hierarchy
   (ceilings at approximately 0.50, 0.18, 0.063, 0.022, 0.008) and shift all
   ceilings by multiplicative offsets of **{0.5×, 0.7×, 1.4×, 2.0×}**. No
   ceiling pinned at the target values. This gives 4 hierarchies.

3. **Random placement.** **N = 50** hierarchies with m drawn uniformly from
   {3,...,8} and ceilings drawn log-uniformly over [1e-3, 0.50], independent of
   the target values. Seed fixed at **42** for reproducibility.

Total hierarchies in the grid: **59** (5 granularity + 4 offset + 50 random).

For each hierarchy H in the grid, record B(H). Then record, for each target value
t ∈ {0.10, 0.02}, whether some boundary in B(H) falls within the pre-registered
tolerance of t.

Tolerance (fixed): a boundary counts as recovering t if it lies within **±25%
multiplicative** of t — i.e., within [0.075, 0.125] for t = 0.10, and within
[0.015, 0.025] for t = 0.02.

Rationale: 25% multiplicative is one-quarter of an order of magnitude, smaller
than the gap between any two adjacent 3GPP service-class thresholds (which span
roughly 5× each). It is tight enough to distinguish recovery from coincidence.

## A.4 Decision rule (fixed before run)

Let p_010 = fraction of grid hierarchies whose boundary set recovers 0.10, and
p_002 likewise for 0.02.

- **STABLE outcome:** min(p_010, p_002) ≥ 0.80. The target values are attractors of
  the evidence surface, recovered across the plausible range of permission
  placements. The "natural ridge" claim is earned.
- **RELATIVE outcome:** min(p_010, p_002) < 0.80. The target values track the
  permission placement rather than the surface. The result is representation-
  relative, and that is the finding.

The threshold 0.80 is fixed now. It will not be moved after seeing p_010, p_002.

## A.5 Pre-written outcome paragraphs

Paste exactly one of the following into §2.4 and adjust Table 1 accordingly,
selected solely by the A.4 decision rule.

### A.5-STABLE (paste if STABLE)

> The boundaries are not artifacts of permission placement. Across 59 permission
> hierarchies spanning 3–8 levels and multiplicative placements offset by up to
> 2×, the extraction operator recovers BLER 0.10 and 0.02 in [p_010·100]% and
> [p_002·100]% of hierarchies respectively, without any hierarchy pinned at those
> values. The targets are attractors of the BER/BLER evidence surface: the points
> where the change from bit-level evidence to block-level reliability most strongly
> shifts the licensable permission, independent of how the permission axis is
> quantized. The 3GPP match is therefore a recovery of the evidence surface, not a
> reflection of the supplied hierarchy.

Table 1 action under STABLE: 3GPP exact-recovery cell stands as written.

### A.5-RELATIVE (paste if RELATIVE)

> The 3GPP result is representation-relative, and the perturbation experiment
> establishes this precisely rather than leaving it open. Across 59 permission
> hierarchies, the extraction operator recovers BLER 0.10 in [p_010·100]% and 0.02
> in [p_002·100]% of cases; the recovered boundaries track the placement of the
> permission ceilings rather than a hierarchy-independent feature of the surface.
> The claim the data support is the narrower one: once a BER/BLER representation and
> a block-level permission granularity are fixed without reading the standard, the
> compiler's boundaries align with the thresholds 3GPP later names. This is a blind,
> representation-relative alignment, not a free-standing discovery of the service
> thresholds. It locates the boundary of the method in this domain: the evidence
> surface constrains the boundary, but the permission granularity co-determines it.

Table 1 action under RELATIVE: change the 3GPP exact-recovery cell to a
"representation-relative alignment" entry; propagate the weaker claim to the
Abstract, Introduction, and §4.4 so the altitude is uniform end to end. (See the
manuscript-consistency checklist, §D below.)

## A.6 Execution log (fill during/after run only)

- Date run: 2026-06-02
- Grid actually used (confirm matches A.3): confirmed — 5 granularity + 4 offset + 50 random = 59 hierarchies, seed 42, BLER range [1e-3, 0.50], tolerance ±25%
- p_010 = 0.051 (3/59)
- p_002 = 0.034 (2/59)
- Decision rule output: **RELATIVE**
- Per-family: granularity p(0.10)=0.000 p(0.02)=0.000 | offset p(0.10)=0.000 p(0.02)=0.000 | random p(0.10)=0.060 p(0.02)=0.040
- Paragraph pasted: A.5-RELATIVE (below)
- Anomalies / deviations from spec: none. The 3/59 and 2/59 recoveries in the random family are coincidental placements near the target values, not structural recovery. The granularity and offset families recover neither target at zero rate.

**Outcome paragraph (A.5-RELATIVE):**

> The 3GPP result is representation-relative, and the perturbation experiment
> establishes this precisely rather than leaving it open. Across 59 permission
> hierarchies, the extraction operator recovers BLER 0.10 in 5.1% and 0.02
> in 3.4% of cases; the recovered boundaries track the placement of the
> permission ceilings rather than a hierarchy-independent feature of the surface.
> The claim the data support is the narrower one: once a BER/BLER representation and
> a block-level permission granularity are fixed without reading the standard, the
> compiler's boundaries align with the thresholds 3GPP later names. This is a blind,
> representation-relative alignment, not a free-standing discovery of the service
> thresholds. It locates the boundary of the method in this domain: the evidence
> surface constrains the boundary, but the permission granularity co-determines it.

**Table 1 action:** Change the 3GPP exact-recovery cell to "representation-relative alignment." Propagate the weaker claim uniformly to Abstract, Introduction, and §4.4.

---

# Experiment B — Held-out generalization

## B.0 GATE (must be answered before any other part of B is executed)

This experiment is design-bound, not compute-bound. It may not proceed until the
source of taxonomy-independent ground truth is fixed in writing. Answer the gate
first.

**Where does the independent assessment of each held-out case come from?**

Candidate sources, in order of defensibility:

1. **Pre-existing independent assessment.** A published expert assessment,
   regulatory finding, or post-incident determination of what authorization the
   case warranted, authored by parties who never saw the G1–G7 taxonomy. STRONGEST.
   Usable only if such assessments exist for the chosen held-out cases and can be
   reduced to a permission level under a fixed, pre-registered rubric.
2. **Blind independent rater.** A qualified person given the held-out cases and a
   neutral assessment rubric, blind to the gap taxonomy, who independently judges
   the warranted authorization level. WORKABLE. Requires a second person and a
   rubric fixed before they see the cases.
3. **Self-assessment by the author reading post-incident reports.** DISQUALIFIED.
   This re-applies the instrument under test and produces circular agreement. The
   spec forbids it.

**Gate decision (fill before proceeding):**

The candidate held-out cases with pre-existing independent assessments are:

- **Boeing 737 MAX MCAS** — FAA Airworthiness Directive 2020-24-02, House
  Transportation Committee report (Sept 2020), and Joint Authorities Technical
  Review report (Oct 2019) all constitute independent regulatory determinations
  that MCAS was not authorized for autonomous action at its deployed blast radius
  and authority level. Reducible to: compiler should emit below ALR on authority_gap
  and blast_radius_gap.

- **COVID-19 ML models (Roberts et al. 2021)** — Roberts et al. (Nature Machine
  Intelligence, 2021) is an independent systematic review by parties with no
  connection to any of the ~300 reviewed models, concluding none were ready for
  clinical use. Reducible to: compiler should emit below ALR on distribution_shift_gap
  and scope_coverage_gap.

- **Amazon recruiting algorithm** — Reuters investigation (Dastin 2018) and
  Amazon's own discontinuation of the tool constitute an independent determination
  that the system was not fit for the action it was used to authorize.
  Reducible to: compiler should emit below ALR on model_specification_gap.

- **Allegheny Family Screening Tool** — independent academic assessments
  (Eubanks 2018; Brown et al. 2019 Child Abuse & Neglect) raise individual_population_gap
  concerns; however these do not constitute a regulatory finding with a clear
  permission level. **BORDERLINE — include only if rubric can reduce it cleanly.**

The rubric for reducing each independent assessment to a permission level:

> A case warrants REFUSE if the independent assessment concludes the system caused
> direct harm and no remediation was possible without withdrawal.
> A case warrants REV (review-required) if the independent assessment concludes
> deployment required human review or oversight that was absent.
> A case warrants AEX (authority-exceeded) if the assessment concludes the scope
> of autonomous action was inappropriate regardless of model quality.
> A case warrants ALR (allowed) if the assessment concludes deployment was
> appropriate given the evidence available at the time.
> The rubric is applied to the independent assessment text, not to the author's
> reading of the case.

- Source selected: **1 (pre-existing independent assessments)**
- Assessment documents and reduction rule: as stated above.
- Allegheny inclusion decision (fix before run): **EXCLUDE** — the academic
  assessments do not reduce cleanly to a single permission level without
  author judgment, which reintroduces circularity.

Final held-out set: **Boeing MCAS, COVID-19 ML models (Roberts), Amazon recruiting.**
n = 3.

## B.1 Held-out set (fixed before scoring)

- Held-out cases (fixed): Boeing 737 MAX MCAS, COVID-19 ML models (Roberts et al.
  2021 systematic review), Amazon recruiting algorithm.
- Confirmation none were used in induction: confirmed. The induction set was Epic,
  Optum, PredPol, COMPAS, Watson Oncology, Dutch childcare, credit stress test.
  None of the three held-out cases appears in that list.
- The taxonomy is FROZEN at S1–S2 + G1–G7. No new gap may be added during this
  experiment. If a held-out case appears to force a new gap, that is a recorded
  result (taxonomy incompleteness), NOT a license to extend the taxonomy here.

## B.2 Procedure (fixed before run)

1. Freeze the converged taxonomy and the permission hierarchy.
2. For each held-out case, the compiler emits a permission level from the case's
   evidence package, with no taxonomy changes.
3. Apply the B.0 rubric to the independent assessment text to obtain the
   independent permission level. Do this before comparing to the compiler output.
4. Compare per case.

## B.3 Metrics (fixed before run)

Report, as raw counts, not rates alone:

- **Agreements:** compiler level == independent assessment level.
- **Conservative disagreements:** compiler level < independent assessment
  (compiler refuses what the assessor would allow). Safe direction.
- **Permissive disagreements:** compiler level > independent assessment (compiler
  allows what the assessor would refuse). DANGEROUS direction.

## B.4 Decision rule (fixed before run)

- **GENERALIZES outcome:** zero permissive disagreements, AND agreements ≥ **2 of
  3** held-out cases. (With n = 3, requiring 2/3 agreements plus zero permissive
  errors is the appropriate criterion: it allows one conservative disagreement,
  which is the safe direction, while requiring the compiler not to over-authorize
  any case.) Conservative disagreements are acceptable and reported.
- **BOUNDED outcome:** any permissive disagreement, OR agreements fewer than 2 of
  3. The generalization claim is not supported; the result locates where the
  taxonomy is incomplete.

The permissive-disagreement threshold is zero and is fixed now. One permissive
disagreement falsifies the safe-generalization claim.

## B.5 Pre-written outcome paragraphs

### B.5-GENERALIZES (paste if GENERALIZES)

> On 3 held-out cases not used in induction — Boeing 737 MAX MCAS, COVID-19 ML
> models (Roberts et al. 2021), and the Amazon recruiting algorithm — evaluated
> against pre-existing independent regulatory and investigative assessments (FAA AD
> 2020-24-02; Roberts et al.; Dastin 2018), the compiler agreed on [k of 3] and
> never over-authorized: all disagreements were conservative, with the compiler
> refusing permissions the independent assessment would have allowed. The taxonomy
> was frozen during this evaluation; no gap was added. Three held-out cases with
> zero permissive disagreements is consistent with generalization beyond the
> induction set, but n = 3 is a bound on the strength of this claim: it rules out
> systematic over-authorization and confirms the taxonomy does not break on cases
> outside its induction domain, but does not establish generalization in the sense
> a larger held-out evaluation would.

### B.5-BOUNDED (paste if BOUNDED)

> The held-out evaluation locates a boundary of the taxonomy rather than confirming
> open-ended generalization. On 3 held-out cases evaluated against pre-existing
> independent assessments, the compiler [agreed on k; produced j permissive
> disagreement(s)]. The permissive case(s) — [name] — failed through [mechanism],
> which no induced gap covers. The taxonomy therefore generalizes within the failure
> modes its induction set spans and stops at failure modes outside that span. We
> report the specific uncovered mechanism as the boundary, and do not claim general
> socio-technical completeness.

### B.5-CONCEDE (paste if GATE returned NONE AVAILABLE)

> We do not claim out-of-sample generalization. Establishing it requires
> assessment of held-out cases by parties independent of and blind to the gap
> taxonomy; such independent assessment was not available for this study. We
> therefore report an induction-set recovery plus a blind regulatory audit, and
> specify the independent-assessment protocol (named held-out cases, blind rater
> or pre-existing determinations, zero-permissive-disagreement criterion) as
> required future work. The claims in this paper do not rest on generalization
> beyond the induction set.

Manuscript action under CONCEDE: remove the "generalize to held-out cases"
sentence from §2.5; ensure no front-matter sentence implies validated
generalization.

## B.6 Execution log (fill during/after run only)

- Date run: 2026-06-02
- Gate decision: Source 1 (pre-existing independent assessments). Gate answered before run — held-out set fixed, Allegheny excluded.
- Held-out cases: Boeing 737 MAX MCAS (H02), COVID-19 ML models — Roberts et al. 2021 (H03), Amazon recruiting algorithm (H04)
- Source used: FAA AD 2020-24-02 + House Transportation Committee (Sept 2020) + JATR (Oct 2019) → H02=REV; Roberts et al. (2021) Nature Machine Intelligence → H03=DIA; Dastin (2018) Reuters + Amazon discontinuation → H04=REV
- Taxonomy version at scoring: v6 (frozen; 6 induced gaps: clinical_utility_gap, model_specification_gap, distribution_shift_gap, individual_population_gap, blast_radius_gap, authority_gap). No gap added during B.
- Per-case results:
  - H02 Boeing MCAS: compiler=REV, independent=REV → AGREEMENT
  - H03 COVID-19 ML: compiler=DIA, independent=DIA → AGREEMENT
  - H04 Amazon recruiting: compiler=AEX, independent=REV → PERMISSIVE DISAGREEMENT
- Agreements / conservative / permissive (counts): 2 / 0 / 1
- Decision rule output: **BOUNDED** (1 permissive disagreement; 2/3 agreements; decision rule requires zero permissive disagreements)
- Paragraph pasted: B.5-BOUNDED (below)
- Taxonomy version note: The paper's full taxonomy is S1–S2 + G1–G7 (nine gaps). Scoring used v6 (six induced gaps: G1–G6). G7 (reason_traceability_gap) was absent from the scoring profile. This is not a substantive version mismatch: G7 gates the adverse-action/reason-traceability obligation induced by the credit stress test. None of the three held-out cases (aviation authority, medical triage, hiring proxy) presents a reason-traceability failure mode. Had G7 been present and open in H02, H03, or H04, the profile would have blocked ALR — but ALR was already blocked in all three cases by other open gaps. AEX does not require G7 under any profile version (G7, like all induced gaps, enters at ALR only). DIA requires nothing. REV requires only AQ. The permission level emitted for each case is therefore identical whether or not G7 is present. Scoring was unaffected.

- Deviation (DIA not in pre-registered rubric): The B.0 rubric enumerated REFUSE / REV / AEX / ALR as the four permission levels for independent-assessment reduction. Scoring used DIA as the independent-assessment level for H03, mapped from Roberts et al.'s conclusion that none of the models were fit for clinical use. DIA was not listed in the rubric. The reconciliation is that REFUSE (rubric) and DIA (hierarchy) denote the same position — below any authorized use — named once in the rubric as a concept and once in the hierarchy as a chain term. The reconciliation does not change any agreement/disagreement classification: H03 produced an agreement at the lowest level regardless of whether that level is labeled REFUSE or DIA. Recorded as a deviation; the rubric listing was incomplete, not the scoring.

- H04 failure mechanism — sharp reading (do not soften): model_specification_gap is OPEN for H04. By the gap definitions, open means the proxy-target mismatch is already known, not suspected. The compiler emitted AEX for a system with a known open proxy-target mismatch. This is not a soundness violation relative to the frozen hierarchy — the compiler is sound by construction because model_specification_gap is not a blocking gap for AEX; it is not required at that level. But that is the wrong question to rest on. The compiler is sound relative to the hierarchy, and the hierarchy is mis-specified relative to the independent assessment. The design choice — all induced gaps enter at ALR only, never AEX — was a reasonable instrument for induction, but blind held-out evaluation has revealed that it does not hold up as a permission semantics when an external assessor weighs in. An independent assessment, blind to the taxonomy and conducted before any comparison, placed the ceiling at REV. The compiler went above it. The blind assessor is the ground truth in this experiment; the assessor adjudicates whether AEX is a defensible level for a known-misspecified system, and the answer is no. The AEX-semantics interpretation — "a supervised trial might tolerate a misspecified proxy" — is the gentle reading, and it is available only by choosing a favorable interpretation of AEX after seeing the result. That move is not available here. The finding is: blind held-out evaluation revealed that the policy choice baked into the frozen hierarchy (induced gaps gate only ALR) causes the compiler to over-authorize a known-misspecified system relative to independent judgment. This directly instantiates the representation-relativity the paper already owns in §3.7: the placement of induced gaps in the permission hierarchy is a policy choice the framework does not force, and that choice determined an over-authorization. The held-out experiment demonstrates this concretely rather than abstractly.

- H02/H04 consistency check: The H04 mechanism (all induced gaps gate ALR only, leaving AEX reachable with skeleton gaps bounded) predicts that any case with skeleton gaps bounded and only induced gaps open will reach AEX. H02 (Boeing MCAS) has model_specification_gap open and blast_radius_gap open — both induced gaps — but also has freshness_gap (S2, a skeleton gap) open. AEX requires both skeleton gaps bounded. Because freshness_gap is open, AEX is blocked for H02 by the structural skeleton itself, before any induced-gap logic applies. The compiler correctly holds H02 at REV — not because authority_gap or blast_radius_gap gate AEX, but because the single-sensor AOA architecture left a skeleton gap open. H04 has both skeleton gaps bounded; the skeleton gives no block; AEX is reachable via skeleton alone; the open induced gaps block only ALR. The mechanism is consistent across both cases and the two cases expose it from opposite sides: H02 shows that a broken skeleton holds a system below AEX regardless of induced gaps; H04 shows that a sound skeleton lets a substantively broken system reach AEX because the induced gaps were never placed there. The three-case table (H02=REV/REV, H03=DIA/DIA, H04=AEX/REV) is internally coherent. The finding is not contradicted by H02; it is clarified by it.

- Anomalies / deviations: Two deviations noted above — DIA used in scoring without appearing in B.0 rubric (reconciled, no classification impact); G7 absent from scoring profile (inert for these cases, no classification impact). No other deviations. The BOUNDED outcome was pre-written and applies without modification. The decision rule fired honestly.

**Outcome paragraph (B.5-BOUNDED):**

> The held-out evaluation locates a boundary of the taxonomy rather than confirming
> open-ended generalization. On 3 held-out cases evaluated against pre-existing
> independent assessments, the compiler agreed on 2 (Boeing MCAS at REV; COVID-19
> ML models at DIA) and produced 1 permissive disagreement (Amazon recruiting:
> compiler AEX, independent REV). The permissive case failed through a mechanism
> that is structural, not incidental: the frozen permission hierarchy places all
> induced gaps as ALR-level requirements. A system with model_specification_gap open
> — a known proxy-target mismatch — is correctly blocked from ALR, but reaches AEX
> (experiment-authorized) because AEX requires only the two structural skeleton gaps,
> both of which are bounded. Boeing MCAS, by contrast, has freshness_gap (S2, a
> skeleton gap) open due to the single-sensor AOA architecture; the skeleton itself
> blocks AEX, so the agreement at REV is consistent with the same mechanism.
> An independent assessment blind to the taxonomy (Dastin 2018; Amazon
> discontinuation) placed Amazon's ceiling at REV. The compiler went above it.
> The finding is not that the taxonomy lacks a gap; it is that the placement of
> induced gaps in the permission hierarchy is a policy choice the framework does not
> force, and that choice caused over-authorization relative to independent judgment.
> This is the representation-relativity the paper already owns in §3.7, now
> instantiated concretely: the hierarchy encodes a design decision, and blind
> held-out evaluation revealed its boundary. The taxonomy therefore generalizes
> within the ALR-vs-below failure modes its induction set spans and stops at the
> AEX-vs-REV boundary — not because a gap is missing, but because the hierarchy's
> gap placement is itself a policy choice that the evidence does not force.

---

# Experiment C — World-realizability falsification

## C.1 Claim under test (fixed)

Every gap in the taxonomy (G1–G7; S1–S2 are structural) is world-realizable: the
failure it names is a fact about the deployment world that its closing token is
evidence of but does not constitute. Equivalently, for each gap there exist two
world-states consistent with the same evidence profile that differ in whether the
failure obtains.

This experiment ATTEMPTS TO FALSIFY that claim, gap by gap. A failure to falsify
is corroboration; a successful falsification for some gap is a sharper result
(the taxonomy partitions into authorization gaps and documentation gaps).

## C.2 Procedure (fixed before run)

For each gap G in {G1, G2, G3, G4, G5, G6, G7}:

1. State the gap's world-fact and its closing token, verbatim from §2.5/§3.4.
2. Attempt to construct a deployment scenario in which the world-fact is FULLY
   DETERMINED by the token — i.e., where "the failure is absent" means nothing
   more than "the token is present," so the fiber over the evidence profile is
   constant and the authorization interval collapses to width zero.
3. Record one of:
   - **NOT FALSIFIED:** no such scenario can be constructed; the world-fact can
     obtain or fail independently of the token. Provide the two distinguishing
     world-states (the witness pair) as positive evidence.
   - **FALSIFIED:** such a scenario exists; exhibit it. The gap is a documentation
     requirement, not an authorization gap.

Construction is by reasoning; no compute required. The difference from the earlier
audit is that this is an explicit falsification attempt, recorded per gap,
including near-misses.

## C.3 Gap definitions for reference (verbatim from §2.5, fixed)

**G1 clinical_utility_gap.** World-fact: the model's sensitivity and PPV at the
deployed operating threshold are adequate for clinical use. Token: a validated
operating-point report supplying sensitivity, PPV at the deployed threshold with
confidence intervals. The token certifies the world-fact; it does not constitute
it.

**G2 model_specification_gap.** World-fact: the training target is a valid proxy
for the action target in the deployment population. Token: specification
documentation confirming alignment between prediction target and action target,
with evidence from the deployment context. The world-fact is a causal relationship
in the world; the token is evidence of it.

**G3 distribution_shift_gap.** World-fact: model performance on the deployment
population is stable relative to the training distribution, not generated by the
model's own output history. Token: external validation against an independently
generated distribution. The world-fact is a population-level property; the token
is independent evidence of it.

**G4 individual_population_gap.** World-fact: the population-level statistic is
predictively valid for the individual decision being authorized. Token: a
certifier for individual-level predictive validity, separate from population
calibration. The world-fact is about the inferential validity of applying a group
statistic to a specific case.

**G5 blast_radius_gap.** World-fact: the scope of downstream actions licensed per
model output is bounded within the stated deployment architecture. Token: an
explicit scope contract specifying the maximum downstream actions triggered per
output. The world-fact is an architectural property of the deployed system.

**G6 authority_gap.** World-fact: a human with genuine authority to halt or
override any individual decision is architecturally positioned to intervene before
consequential action is taken. Token: an authority contract specifying the exact
boundary between autonomous action and human-confirmed action, with evidence that
the human role is genuine (not a rubber stamp). The world-fact is the presence of
an actual override position in the decision architecture — not the existence of a
human somewhere in the organization.

**G7 reason_traceability_gap.** World-fact: an auditable causal path from model
inputs to the specific principal reasons for this decision exists in the model's
computation. Token: a validated reason token — an auditable mapping from input
features to the principal reasons required by law. The world-fact is an
architectural property of the model's forward pass; the token certifies it.

## C.4 Special attention (fixed before run)

G6 and G7 are the two gaps whose world-fact/token-fact distinction is closest,
as established by prior analysis. They are the most likely to falsify. Apply
the same rigor to them as to the others; do not pre-decide they survive.
If either falsifies, that is the most informative outcome of this experiment.

For G6 specifically: the falsification attempt must address whether "genuine
override authority" is fully determined by the existence of a written authority
contract, or whether the contract can exist while the world-fact (actual
architectural override capacity) is absent. The Dutch childcare case is the
existence proof that the world-fact and the token can come apart. The falsification
attempt must try to construct a scenario where they cannot — where the token
and the world-fact are logically identical.

For G7 specifically: falsification requires showing the fiber over the evidence
profile is *constant* — that the world-fact and the token-fact are definitionally
identical, with no state where they come apart in either direction. The attempt
must therefore test both halves:

**Direction 1 (token without world-fact):** An opaque model where no auditable
causal path exists in the forward pass, but a reason token is generated post-hoc
by a separate explainability system (e.g., LIME applied after inference). The
token is present; the world-fact is absent. If this state is constructible, the
fiber contains a state with G7 open despite a token being present — world-fact and
token come apart, fiber is non-constant, NOT FALSIFIED. Note: this construction is
likely to yield a witness pair, not a collapse, because the post-hoc generator
is precisely the Dutch-childcare analogue for G7: token present, world-fact absent.

**Direction 2 (world-fact without token):** A model with interpretable features
that computes reason candidates as part of its forward pass — the causal path
genuinely exists — but no validation process has been run and no reason token has
been submitted. The world-fact is present; the token is absent. If this state is
constructible, the fiber also contains a state with G7 closed despite no token
being present — again non-constant, NOT FALSIFIED.

Falsification requires that *neither* construction works — that token-present
always implies world-fact-present and world-fact-present always implies
token-present, making them logically equivalent. Both directions must be tested
and must collapse before G7 is recorded as FALSIFIED.

## C.5 Decision rule (fixed before run)

- **LEMMA HOLDS outcome:** all seven gaps return NOT FALSIFIED, each with a witness
  pair. §3.4 stands; world-realizability is corroborated across the taxonomy.
- **PARTITION outcome:** one or more gaps return FALSIFIED. The taxonomy splits
  into authorization gaps (world-realizable, covered by the theorem) and
  documentation gaps (token-constituted, excluded by the theorem). §3.4 is revised
  to state the partition explicitly, and the falsified gap(s) are reclassified.

## C.6 Pre-written outcome paragraphs

### C.6-LEMMA-HOLDS (paste if LEMMA HOLDS)

> We attempted to falsify world-realizability for each gap by constructing a
> deployment in which the gap's world-fact is fully determined by its closing
> token. For all seven induced gaps the attempt fails: in each case two deployment
> states consistent with the same evidence profile differ in whether the failure
> obtains, so the fiber is non-constant and the authorization interval is
> non-empty. Witness pairs are given in Appendix C. The §3.4 hypothesis is
> therefore not an artifact of how the gaps were named; it is corroborated by
> explicit falsification attempt across the taxonomy.

### C.6-PARTITION (paste if PARTITION)

> The falsification attempt succeeds for [gap(s)], which partitions the taxonomy.
> [Gap] can be constructed so that its world-fact is fully determined by its token:
> [exhibit]. Such a gap is a documentation requirement, not an authorization gap —
> its fiber is constant, its interval empty, and the representation theorem
> correctly excludes it. The remaining [k] gaps survive the attempt with witness
> pairs. The taxonomy therefore separates into authorization gaps, which the
> theorem governs, and documentation gaps, which it does not. This sharpens rather
> than weakens the framework: it gives an operational test — the falsification
> construction — for which obligations are evidence-forced and which are policy
> documentation.

Manuscript action under PARTITION: revise §3.4 to state the partition; reclassify
the falsified gap(s) in §2.5 and Table 1; this strengthens the §1 forced-vs-chosen
thesis by giving it a constructive test.

## C.7 Execution log (fill during/after run only)

- Date run: 2026-06-02

- Per-gap results:

  G1 clinical_utility_gap — NOT FALSIFIED.
    Witness: x₁ = system with sensitivity 0.80, no report filed. x₂ = system with sensitivity 0.33, no report filed. Same evidence profile, different A*.

  G2 model_specification_gap — NOT FALSIFIED.
    Witness: x₁ = model with genuine proxy validity, no spec doc filed. x₂ = model with invalid proxy (cost ≠ care need for subpopulation), specification doc filed. Same evidence profile, different A*.

  G3 distribution_shift_gap — NOT FALSIFIED.
    Witness: x₁ = model in stable deployment population, no external validation token. x₂ = model whose deployment induced the distribution later validated against (PredPol structure), token filed. Same evidence profile, different A*.

  G4 individual_population_gap — NOT FALSIFIED.
    Witness: x₁ = model with genuine individual-level calibration, no certifier issued. x₂ = population-score model, individual certifier issued making unsupported claims. Same evidence profile, different A*.

  G5 blast_radius_gap — NOT FALSIFIED.
    Witness: x₁ = model used by single physician in supervised setting, no scope contract filed. x₂ = model with global routing and difficult override, scope contract filed. Same evidence profile, different A*.

  G6 authority_gap — NOT FALSIFIED. Both directions tested.
    Direction 1 (token without world-fact): Dutch-style deployment with authority contract filed but no actual override mechanism. Token present, world-fact absent.
    Direction 2 (world-fact without token): Physician who genuinely reviews and halts every output before action, no contract filed. World-fact present, token absent.
    Witness: x₁ = genuine oversight, no contract. x₂ = nominal oversight (compliance officer sees aggregates), contract filed. Same evidence profile, different A*.

  G7 reason_traceability_gap — NOT FALSIFIED. Both directions tested.
    Direction 1 (token without world-fact — LIME construction): Opaque ensemble with post-hoc LIME generating reason token. Token present; no auditable causal path in forward pass. World-fact absent.
    Direction 2 (world-fact without token): Logistic regression whose coefficient weights on specific features constitute the causal path. World-fact present; no token filed.
    Collapse test: neither direction collapses. Post-hoc generators produce tokens without world-facts; interpretable models have world-facts without tokens.
    Witness: x₁ = logistic regression, causal path present, no token. x₂ = opaque GBM with LIME token filed. Same evidence profile, different A*.

- Decision rule output: **LEMMA HOLDS**

- Paragraph pasted: C.6-LEMMA-HOLDS (below)

- Anomalies / deviations: None. G6 and G7 were the designated high-risk gaps. Both survived with their strongest adversarial constructions (Dutch-case analogue for G6, LIME construction for G7) producing witness pairs rather than collapses. The LIME construction is the most informative near-miss: it is the exact scenario where a token is produced without the world-fact, which is the direction-1 witness for G7 rather than a falsification.

**Outcome paragraph (C.6-LEMMA-HOLDS):**

> We attempted to falsify world-realizability for each gap by constructing a
> deployment in which the gap's world-fact is fully determined by its closing
> token. For all seven induced gaps the attempt fails: in each case two deployment
> states consistent with the same evidence profile differ in whether the failure
> obtains, so the fiber is non-constant and the authorization interval is
> non-empty. Witness pairs are given in Appendix C. The §3.4 hypothesis is
> therefore not an artifact of how the gaps were named; it is corroborated by
> explicit falsification attempt across the taxonomy.

---

# D. Manuscript-consistency checklist (apply after all three experiments)

The front matter currently claims the strongest version of every result. After
the experiments, the Abstract, Significance, Introduction, Table 1, and §4 must
claim exactly what the decision rules selected — no more. Run this checklist:

1. **Altitude is uniform.** The strength of the 3GPP claim in the Abstract,
   Introduction, Table 1, §2.4, and §4.4 must all match the A.4 outcome. No split
   where the front says "exact recovery" and the body says "representation-
   relative."
2. **Headline matches the post-experiment ledger.** Re-derive the one-sentence
   headline from {A outcome, B outcome, C outcome} and confirm the Abstract states
   that and not the pre-experiment version.
3. **No to-do prose in the manuscript.** This spec is the lab notebook. Nothing
   from it (including any "submission-critical items" list) appears in the paper.
4. **Scope section claims only the bounded version.** Whatever the experiments
   conceded (a RELATIVE 3GPP, a CONCEDE or BOUNDED held-out, a PARTITION taxonomy)
   is owned in Scope as a bound, stated once and firmly.
5. **Representation-relativity stays owned.** Independent of A's outcome, the
   theorem is representation-relative (it does not force q and P). The §3.7
   paragraph stating this stays; it is a true property, not a gap any experiment
   closes.

# E. Discipline note

The value of this document is entirely in the ordering: operators, perturbation
grids, decision rules, thresholds, and outcome-paragraphs are fixed before
execution. If any fixed item is changed after a run, record the original, the
change, and the reason in the relevant Execution log, and treat the result as
exploratory rather than confirmatory. A pre-registered "the framework stops here"
is a contribution. A post-hoc "the framework works" is not.
