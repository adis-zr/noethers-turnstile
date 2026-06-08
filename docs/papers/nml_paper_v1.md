## 1. Introduction

The authorization boundaries that govern consequential automated decisions are not arbitrary. A hospital deploying a sepsis alert, an engineer certifying a transmission protocol, a pilot descending through instrument minima, and a lender issuing an adverse-action notice all operate at thresholds where available evidence licenses one action but not another. Those thresholds have been established independently — through decades of practice, committee deliberation, legal interpretation, and hard experience with what happens when they are wrong.

That convergence suggests a stronger possibility. When independent institutions reach similar thresholds by different routes, the common source may not be the institutions themselves. It may be the evidence boundary they are all trying to respect — the point where available evidence stops ruling out the failures that would make an action unsound. Some boundaries are therefore not merely chosen. They are forced.

This paper proves when that is true. When the failures that would make an action unsound are visible in the evidence, the authorization boundary is uniquely determined, and any correct compiler must find it. When the boundary depends on something the evidence cannot observe, when the permission hierarchy places a gap at a level the evidence does not force, or when the failure cases are not finitely distinguishable from the evidence, recovery is impossible in principle, not merely difficult in practice. The theorem identifies all three cases.

We implement the compiler and evaluate it blind against four independent regulatory traditions. The compiler is not given regulatory documents, threshold values, or target labels. It receives only an evidence package and a permission hierarchy, fixed before comparison, and the same recovery rule is used across domains. The results do not have one strength everywhere, and that is the point. In digital communications, the compiler aligns with the 3GPP BLER 0.10 and 0.02 thresholds under a fixed BER/BLER representation and permission hierarchy, but a preregistered perturbation shows that those values are not hierarchy-independent ridges of the evidence surface. In instrument approach operations, the compiler derives the FAA's Category I decision height and visibility minimum simultaneously from approach-lighting geometry, before consulting any FAA document. In medical AI, it induces from documented deployment failures the same evidence obligations the FDA's 2025 AI guidance encodes. In consumer credit, it recovers the adverse-action reason requirement that ECOA makes legally mandatory.

The failures are as informative as the matches. Where the compiler stops short of a regulatory boundary, the gap has structure: representation relative to a supplied hierarchy, policy added above the evidence, a requirement grounded on a different physical axis, or an obligation no evidence package of this type can speak to. The 3GPP case shows that permission granularity can determine a boundary even when the run is blind. The FAA case shows the opposite: visual-acquisition geometry genuinely forces the Category I boundary, then saturates before Category II. FDA and ECOA show a third pattern: harmful deployments induce evidence obligations that later match regulatory text, while other obligations remain outside the supplied package.

The mechanism is simple. Evidence summarizes a system. Authorization licenses an action. The two are not the same. Aggregate evidence can certify mean behavior while leaving local failures unresolved: the missed patient, the failed block, the applicant whose adverse-action reason cannot be reconstructed, the aircraft crossing a threshold on a single approach. The compiler reads the difference between what the evidence summarizes and what the action requires.

This is not a result about compliance. The compiler does not replace legal review, choose policy thresholds, or decide institutional risk tolerance. It asks a narrower question: before law, policy, or institutional authority adds anything else, what actions are already licensed by the evidence?

The result is therefore not that the compiler recovers all regulation. It recovers the part the evidence forces, measures the part policy adds, exposes the choices carried by the supplied representation and hierarchy, and stays silent where the supplied evidence cannot speak. The point is not a perfect match. The point is a partition.

## 2. Results

The compiler takes two inputs. The first is an evidence package: a finite list of named gaps, where each gap marks one way the proposed action could be unsound. Each gap has a status: open, bounded, or closed. The second is a permission hierarchy: a list of action levels, together with the gaps that must be bounded or closed before each level is allowed.

Given these inputs, the compiler returns the strongest action level whose gap requirements are met. It also returns a certificate naming the gaps it checked, their current status, and the first gap that prevents any stronger action level. That action level is the evidence-forced boundary. The certificate makes the boundary auditable: it shows not only where the evidence stops, but what would have to change for the boundary to move.
### 2.1 A compiler partitions regulatory structure by what evidence can force

We first report the main result: a unified correspondence matrix across four independent regulatory traditions. Each column is a regulatory tradition. Each row is a relationship between a compiler boundary and a regulatory threshold.

The compiler was not given regulatory thresholds, service-class labels, category names or target documents before boundary extraction. In each case, the evidence package and permission hierarchy were fixed before comparison. Regulatory documents were opened only after the compiler's boundaries or induced gaps were recorded.

The matrix partitions regulatory requirements into six reported relationships.

**Representation-relative alignment** means the compiler boundary aligns with the external threshold under the frozen evidence representation and permission hierarchy, but a preregistered perturbation shows that the alignment is not stable to plausible changes in the permission hierarchy.

**Exact recovery** means the compiler boundary matches the regulatory threshold or requirement and the match is not explained by later fitting to the external target.

**Same-axis policy margin** means the regulatory threshold sits above the compiler's evidence ceiling on the same evidence axis.

**Different evidence axis** means the boundary turns on another decision-relevant axis, rather than a stricter threshold on the original axis.

**Finer evidence resolution** means the compiler separates cases that the external regime collapses, or induces a more precise evidence relation than the external regime names explicitly, while staying on the same evidence axis.

**Outside the supplied evidence package** means the obligation is real, but the evidence package contains no gap through which the compiler could induce it.

### Table 1. Unified regulatory correspondence matrix

|Correspondence type|3GPP 5G New Radio|FAA ILS approach|FDA medical AI|ECOA / CFPB credit|
|---|---|---|---|---|
|**Representation-relative alignment**|Under the frozen BER/BLER representation and block-level permission hierarchy, the compiler aligns with the eMBB and radio-link monitoring thresholds at BLER 0.10 and 0.02. A preregistered perturbation across 59 alternative hierarchies recovered 0.10 in 5.1% and 0.02 in 3.4% of cases, with zero structured recovery in the granularity and offset families. The alignment is blind, but not hierarchy-independent recovery.|—|—|—|
|**Exact recovery**|—|The compiler recovers CAT I decision height and runway visual range from approach-lighting geometry: derived DH ≈ 197 ft and RVR ≈ 1,862 ft, matching FAA 200 ft and 1,800 ft within sweep resolution.|The compiler maps the locked taxonomy to FDA guidance elements: S2 evidence freshness, G1 operating-point utility, G3 deployment distribution, G4 scope coverage, and G6 authority and rollback.|The compiler induces G7 reason traceability from an adverse-action stress test, matching ECOA, Regulation B, and CFPB requirements for specific principal reasons.|
|**Same-axis policy margin**|Under the same frozen representation, URLLC and factory automation thresholds sit above the compiler's strongest boundary by approximately 0.51–1.36 dB on the SNR axis.|—|—|—|
|**Different evidence axis**|—|CAT II begins where roll-bar visibility geometry saturates. The FAA threshold is grounded in low-height human factors, not the visual evidence axis supplied to the compiler.|—|—|
|**Finer / compiler-strict resolution**|The compiler resolves sub-threshold BER/BLER divergence more finely than committee service classes, but the resulting boundary remains representation-relative.|—|G5 action blast radius calibrates clinical utility to deployment scale: the same PPV carries different authorization weight when applied to 20% of inpatients than when applied to 1% of ICU patients.|—|
|**Outside the supplied evidence package**|B5G ultra-reliability targets exceed the local channel-evidence resolution used here.|CAT III depends on autoland certification, fail-operational systems, and operator qualification, none of which live on the visual evidence axis.|Cybersecurity and user-interface/labeling adequacy are outside this package because no supplied induction case failed through cyber compromise, adversarial manipulation, or unsafe user communication.|Disparate impact and upstream data accuracy are not induced from an individual adverse-action evidence package.|

The exact-recovery row is now deliberately narrower than the first draft. It contains the FAA, FDA, and ECOA matches, not 3GPP. The 3GPP result remains blind, but the preregistered stability experiment shows that it is representation-relative: the fixed BER/BLER representation and permission granularity align with the standard, while plausible changes to the hierarchy do not recover the 0.10 and 0.02 values as stable attractors.

That demotion strengthens the matrix. The table is not a list of successes. It is a partition. It shows what the evidence forces, what the supplied representation and hierarchy co-determine, what policy adds, what requires another evidence axis, what the compiler resolves more finely, and what the evidence cannot reach.

This stopping behavior is essential. A useful compiler must not invent a boundary when the evidence is silent. In the matrix, silence has structure. It can mean policy above evidence, a different evidence axis, a representation-relative alignment, or a requirement outside the evidence package entirely.

### 2.2 Evidence summaries and authorization requirements define different boundaries

The matrix has one common structure. In each tradition, the evidence package reports one object while the action requires another. The compiler is not checking whether the evidence is good in general. It checks whether the evidence rules out the failures that would make a specific permission unsound.

This distinction matters because consequential evidence is usually compressed. It arrives as an average, a rank statistic, a validation score, a channel metric, a visibility value, or a documented review token. Such summaries can be accurate and still fail to answer the authorization question. Mean bit error can be low while the transmitted block still contains an error. AUC can be acceptable while the deployed operating point misses patients. A visual-acquisition model can determine a manual-landing boundary while saying nothing about autoland certification. The evidence is not false. It is incomplete for the permission being requested.

We call this incompleteness the authorization gap. The gap is the set of states where the available evidence supports a weaker summary claim but does not support the stronger action claim.

In physical systems, the gap can be measured directly. A mean-like functional asks about average behavior. A worst-case functional asks whether any component remains unresolved. Since the worst case is at least the mean, the interval between them is exactly the region where a mean-based rule authorizes and a worst-case rule refuses. That interval is non-empty whenever approximation error is uneven across components.

In chosen systems, the same structure is usually not numeric. It appears as a missing evidence token. A model score may support a decision but not the reason legally required for that decision. A single-site validation may support local display but not broad clinical rollout. A human review chain may support recommendation but not autonomous sanction. The compiler reads these as gap statuses: open, bounded, or closed.

This explains the rows of Table 1. Representation-relative alignment occurs when a fixed evidence representation and permission hierarchy align with an external threshold, but the alignment disappears under preregistered hierarchy perturbation. Exact recovery occurs when the evidence contains the relevant gap and closes it at the same boundary the external regime later names. Same-axis policy margin occurs when the evidence boundary is visible, but the external regime adds a buffer above it on the same axis. Different evidence axis occurs when the first evidence representation runs out and a different kind of evidence is needed. Finer / compiler-strict resolution occurs when the compiler distinguishes an evidence relation that the external regime names only coarsely. Outside the supplied evidence package occurs when no available gap can speak to the obligation at all.

![Figure 1. Authorization gap schematic. A mean-like functional crosses the acceptability threshold before the worst-case functional does. The shaded interval between the two crossings is the authorization gap.](figures/fig1_auth_gap_schematic.png)

**Figure 1. Authorization gap schematic.** A mean-like evidence summary can cross an acceptability threshold before the action-relevant failure has been ruled out. The interval between those crossings is the authorization gap. In derived systems, this gap is measured as a distance between functionals. In chosen systems, it appears as an open gap in the evidence package. The compiler returns the strongest permission below the first open gap and reports the gap that blocks stronger action.

The rest of the Results section tests this same object in two settings. First, in physical systems where ground truth exists, the gap can be measured directly. Second, in socio-technical systems, the gap can be induced from over-authorization failures and then audited against regulation.

### 2.3 The physical layer: the gap is measurable in systems with ground truth

The authorization gap is directly measurable in systems where ground truth is available. We first test it in two derived systems: approximate inference in graphical models and turbo-coded digital communication. These systems are physically different in use, but mathematically close. Both produce approximate beliefs over many components. Both are commonly summarized by an average error. Both can fail through a single unresolved component.

The first test uses loopy belief propagation on a two-dimensional Ising model. The ideal object is the exact marginal distribution at each variable. The approximation is the marginal produced by belief propagation. We compare two summaries of the same approximation: mean total variation distance across all variables, and worst-case total variation distance over the single worst variable.

The mean functional answers a summary question: how accurate is the approximation on average? The worst-case functional answers an authorization question: is any variable badly wrong? These are not equivalent. The worst-case error is always at least the mean error, and the difference between them is the authorization gap.

On a $6 \times 6$ Ising grid, the gap is non-empty at every coupling strength tested. It widens as the system approaches the critical regime. At $\beta = 0.44$, the mean error is 0.223 and the worst-case error is 0.334. Thus any tolerance between 0.223 and 0.334 produces a disagreement: the mean functional authorizes, while the worst-case functional refuses.

The disagreement is not cosmetic. At the same operating point, one variable has an approximate marginal assigning probability 0.833 to one state, while the exact marginal assigns probability 0.501 to the other. The approximation is not merely noisy. It reverses the most likely state. A mean-based rule can therefore authorize action even when one component is confidently wrong.

The second test uses turbo-coded communication. The ideal object is the transmitted bitstream. The approximation is the decoded block. Here the same gap appears as the difference between bit error rate and block error rate. Bit error rate is mean-like: it averages over bits. Block error rate is worst-case: it fires if any bit in the block is wrong.

For independent bit errors, a useful illustrative conversion is
$$
\mathrm{BLER} = 1 - (1 - \mathrm{BER})^k.  
$$

This is not assumed as the turbo-code channel law. Coding and decoding create correlated block failures, so the experiment uses measured BLER; the formula is only an independent-error reference curve for mean-to-block amplification.

On that reference curve, a 65,536-bit block with bit error rate $3 \times 10^{-4}$ has block error rate approximately 1.0. The average bit looks good enough for monitored transmission. The block can still fail almost every time.

The measured authorization gap spans roughly 1 dB of SNR. At 2.0 dB, BER authorizes monitored transmission while BLER refuses. At 2.5 dB, BER still authorizes while BLER remains too high for transmission. Only near 3.0 dB does the block-level failure rate fall enough for the stronger permission to become available.

These two experiments show the same object in two registers. In the Ising model, the gap is between average marginal accuracy and the worst variable. In turbo decoding, it is between average bit accuracy and any failed bit in the block. In both cases, the evidence summary can improve while the action-relevant failure remains unresolved.

![Figure 2. Physical authorization gaps in inference and communication. Left: Ising 6×6 loopy BP — mean TV and worst-case TV diverge across coupling strengths, gap widest near critical regime. Right: turbo-coded communication — BER crosses the monitored-transmission threshold ~1 dB before BLER does.](figures/fig2_physical_gaps.png)

**Figure 2. Physical authorization gaps in inference and communication.**  
Left: loopy belief propagation on the (6 \times 6) Ising grid. Mean error and worst-case error diverge across coupling strengths, with the widest authorization gap near the critical regime. The shaded region marks tolerances where mean error authorizes and worst-case error refuses. Right: turbo-coded communication. BER falls below the monitored-transmission threshold before BLER does; the shaded SNR interval marks the region where bit-level evidence authorizes while block-level evidence refuses.

The important point is not that these two systems share an algorithmic history. It is that the same authorization geometry appears whenever an average over components is used to license an action that can fail through one component. The mean summary may be accurate. It may be useful. It may even be the standard engineering measure. But it does not answer the stronger authorization question.

The compiler reads that difference. It does not ask whether the evidence is favorable in general. It asks whether the evidence rules out the failure that would make the permission unsound. In these physical systems, the answer is measurable against ground truth: the authorization boundary is the point where the worst-case failure, not the mean summary, is finally ruled out.

### 2.4 Blind recovery in 3GPP and FAA standards

The physical gap experiments show that the authorization boundary can be measured when ground truth is available. We next ask whether existing regulatory and standards bodies have placed their thresholds at the same boundaries.

We test this in two physical regulatory traditions: 5G New Radio and instrument landing operations. In both cases, the compiler is run before consulting the relevant standard. It receives an evidence representation and a permission hierarchy. It is not given regulatory documents, threshold values, service-class names, approach categories, or target labels. The extracted boundaries are recorded first. The standards are opened afterward.

#### 3GPP New Radio

In the 5G experiment, the evidence representation is the BER/BLER authorization surface over signal-to-noise ratio. The original compiler run used a fixed block-level permission hierarchy and recorded four BLER transitions before any 3GPP document was consulted: 0.50, 0.10, 0.02, and 0.001. Under that frozen representation, two transitions align with 3GPP thresholds: eMBB at BLER 0.10 and radio-link monitoring at BLER 0.02.

The stability question is whether those values are properties of the evidence surface or artifacts of the permission levels supplied to the compiler. We therefore preregistered a perturbation experiment before treating the match as evidence-forced recovery. The boundary operator, sweep range, tolerance, perturbation families, random seed, and decision rule were fixed before the run. The test evaluated 59 alternative permission hierarchies: five log-uniform granularity perturbations, four multiplicative offset perturbations, and fifty random hierarchies over the BLER range [0.001, 0.50]. None was pinned at 0.10 or 0.02.

The result is representation-relative. Across the 59 hierarchies, the extraction operator recovered BLER 0.10 in 5.1% of cases and BLER 0.02 in 3.4% of cases. The structured perturbation families recovered neither value: the granularity and offset families both had zero recovery for both targets. The few random recoveries were coincidental placements near the targets, not stable surface features.

The claim the data support is therefore narrower than exact recovery. Once a BER/BLER representation and a block-level permission granularity are fixed without reading the standard, the compiler's boundaries align with the thresholds 3GPP later names. But the evidence surface does not by itself force 0.10 and 0.02. The surface provides at most a weak prior; the permission granularity determines the boundary. This is a blind, representation-relative alignment, not a free-standing discovery of the service thresholds.

The stricter ultra-reliable and factory-automation thresholds are read under the same limitation. Relative to the frozen hierarchy used in the original audit, they sit above the compiler's strongest boundary on the same SNR axis. The URLLC threshold sits about 0.51 dB above it. The factory-automation threshold sits about 1.36 dB above it. This is a same-axis margin within the fixed representation, not a hierarchy-independent evidence ceiling.

#### FAA instrument approach operations

The aviation experiment has a different structure. The evidence axis is not channel reliability but visual acquisition geometry: decision height, runway visual range, glide slope, threshold crossing height, and approach lighting geometry.

Before consulting FAA documents, the compiler derives the minimum visual range required for manual landing from the geometry of a standard three-degree glide slope and the ALSF-2 approach lighting system. At a 200 ft decision height, the derived visual range floor is approximately 1,862 ft. Solving the same geometry in reverse gives a decision height of approximately 197 ft when the visual range is 1,800 ft.

The FAA Category I threshold is 200 ft decision height and 1,800 ft runway visual range. The compiler therefore recovers both dimensions at once, within sweep resolution, from geometry alone.

The lower approach categories do not behave like the 3GPP ultra-reliable thresholds. Category II is not simply a stricter visual threshold on the same axis. The visual-acquisition constraint saturates at approximately 102 ft decision height: below that point, the aircraft has already passed the roll bar before reaching decision height. The visual geometry has no further boundary to give.

FAA Category II begins at 100 ft decision height. That is just below the saturation point. The corresponding 1,200 ft runway visual range requirement is therefore not a same-axis margin above the Category I geometry. It is grounded in a different evidence axis: low-height human factors, flare completion, and the reduced time available before touchdown.

This is a different evidence axis. The compiler finds the visual boundary, reaches the point where the visual evidence stops determining the decision, and then stops. The FAA threshold beyond that point is real, but it depends on evidence the supplied visual package does not contain.

Category III is different again. Its requirements depend on autoland certification, fail-operational systems, operator qualification, and aircraft equipment. None of those live on the visual-acquisition axis. The compiler is therefore permissive relative to the FAA category table, but for a structurally correct reason: it has been given the wrong evidence package for zero-visibility authorization.

![Figure 3. Blind recovery and representation-relative alignment in 3GPP and FAA standards. Left: 3GPP BLER boundaries under the frozen BER/BLER representation — eMBB/RLM align at 0.10 and 0.02, but hierarchy perturbation shows the alignment is not stable. Right: FAA ILS geometric curve — CAT I exact recovery marked, saturation at ~102 ft DH, CAT II annotated as different evidence axis, CAT III as outside the evidence package.](figures/fig3_blind_recovery.png)

**Figure 3. Blind recovery and representation-relative alignment in 3GPP and FAA standards.**  
Left: 3GPP New Radio. Under the frozen BER/BLER representation and permission hierarchy, the compiler aligns with BLER 0.10 and 0.02 before consulting the standard; a preregistered perturbation across 59 alternative hierarchies shows that those values are not hierarchy-independent ridges. Right: FAA ILS. The compiler derives the Category I decision-height and runway-visual-range pair from approach-lighting geometry. The visual constraint saturates just above Category II, showing why lower categories require a different evidence axis rather than a stricter visual threshold.

Together, the two blind audits show that existing standards do not have a single architecture. In 3GPP, the fixed representation aligns with standard thresholds but the permission hierarchy co-determines the result. In FAA approach operations, visual geometry determines Category I, saturates at the Category II transition, and gives way to human-factors and equipment-certification evidence below that point.

The compiler identifies both structures without reading either standard. Its matches are informative, but so are its stops and demotions. Exact recovery marks the boundary the evidence forces. Representation-relative alignment marks a boundary that appears only after the representation and permission granularity are fixed. Same-axis margin marks policy added above a boundary within that representation. Different-axis silence marks the point where the supplied evidence no longer contains the relevant question.

### 2.5 The socio-technical layer: inducing gaps from harmful deployments

The physical layer shows the authorization gap in systems where ground truth is available. Socio-technical systems are harder. The ideal output is often contested, the relevant harm may be institutional rather than physical, and the permission boundary is not determined by mathematics alone.

The compiler does not remove that indeterminacy. It does something narrower. It asks whether the evidence package rules out the world states that would make the requested action unsound. A closing token is evidence of that fact; it does not constitute the fact. When the compiler over-authorizes a harmful deployment, the failure identifies a missing gap: a real deployment condition the evidence package should have checked before the stronger permission was allowed.

We use this to induce a gap taxonomy from harmful deployments.

The procedure starts with a deliberately weak evidence profile. It tracks only approximation quality and evidence freshness. The compiler is then run against documented deployments where the outcome is known. Expert assessments are fixed from published post-incident analyses before each induction step. When the compiler emits a permission stronger than the locked assessment, we ask what positive evidence would have blocked that over-authorization while still permitting a legitimate deployment. That missing evidence becomes a new gap type. The case is rerun with the expanded taxonomy. The loop continues until no available case forces a new gap.

This is the socio-technical analogue of the physical gap. In the physical layer, the gap is a measurable interval between two functionals. In the socio-technical layer, the gap is a missing evidence obligation exposed by over-authorization.

The induction locks the canonical taxonomy used in the rest of the paper. The two structural gaps present in the weak starting profile keep their IDs throughout:

**S1 approximation quality** asks whether the summary evidence is strong enough for the requested permission.

**S2 evidence freshness** asks whether the evidence remains valid after deployment, drift, version changes, and population change.

The induction then produces seven new gap types.

The first is **G1 operating-point utility**. The Epic Sepsis Model had acceptable ranking performance, but its deployed operating point had low sensitivity and low positive predictive value. AUC did not answer the clinical authorization question. The missing evidence was utility at the deployed threshold.

The second is **G2 target-action specification**. The Optum health risk algorithm predicted healthcare cost, but the action required care need. The prediction target and the action target diverged. The missing evidence was that the model was specified for the action it was used to authorize.

The third is **G3 deployment distribution**. Predictive policing systems can alter the distribution they later train on. Increased policing produces more recorded crime in the same areas, which reinforces future predictions. The missing evidence was validation against a distribution not generated by the model's own deployment.

The fourth is **G4 scope coverage**. A population-level recidivism score can describe group risk while failing to certify an individual detention decision. The missing evidence was that the validation scope covered the population, site, subgroup, and individual action being authorized.

The fifth is **G5 action blast radius**. IBM Watson Oncology showed that the same model output can have different authorization weight depending on the scope of downstream harm. A supervised suggestion in one clinic is not the same action as a treatment recommendation distributed globally. The gap is the deployment scale itself: how far one output can propagate, how many people or sites it can affect, and how much downstream action it can trigger before containment. The evidence that closes G5 is a blast-radius bound, but the gap is the architecture that gives the output that radius.

The sixth is **G6 authority and rollback**. The Dutch childcare benefits algorithm converted automated risk assessments into repayment demands with severe consequences and inadequate review. The missing fact was not another accuracy metric. It was whether the decision architecture placed genuine authority outside the model, and whether a live mechanism could halt or roll back the system when the evidential basis changed. These are one gap, not two: both ask when the system must stop acting on its own. A contract, change protocol, or response plan can be evidence that closes the gap, but the gap itself is structural authority and operational rollback in the deployed system.

The seventh is **G7 reason traceability**. In a credit adverse-action stress test, the evidence package was constructed to satisfy the preceding six induced gaps. The compiler still over-authorized. The missing fact was that the model and decision pipeline contained an auditable computational path from the inputs and model output to the specific principal reasons required for the adverse action. A validated reason token can close the gap, but the gap itself is reason traceability in the computation. Evidence sufficient to support a decision was not sufficient to support the reason the decision required.

These names and IDs are canonical below. Regulatory phrases such as post-market monitoring, validation dataset diversity, and algorithm change protocol are external matches to these gaps, not additional gap names.

These gaps are not interchangeable. Each one blocks an over-authorization that the previous taxonomy could not block. Operating-point utility is not deployment distribution. Deployment distribution is not scope coverage. Authority and rollback is not reason traceability. Each gap names a distinct way evidence can support a weaker claim while failing to license the stronger action.

![Figure 4. Induction trace and gap taxonomy. Left: compiler starts at v0 with S1 approximation quality and S2 evidence freshness; each harmful deployment forces one new evidence obligation. Right: converged 9-gap taxonomy matrix — S1–S2 plus G1–G7 — showing each induced gap blocks exactly the cases where it is open.](figures/fig4_induction_trace.png)

**Figure 4. Induction trace and gap taxonomy.**  
Left: the compiler begins at v0 with S1 approximation quality and S2 evidence freshness. Each harmful deployment exposes one missing evidence obligation; the profile advances one version per induction step. Right: the converged 9-gap taxonomy (S1–S2 plus G1–G7) shown as a case × gap matrix. Each induced gap is structurally independent: it blocks exactly the cases where it is open, and no others.

After convergence, all induction cases are rerun against the converged profile: two structural gaps plus seven induced gaps. The over-authorizations disappear. The positive control remains authorized.

We then ran a preregistered held-out evaluation to test how far this claim should go. The held-out set was fixed before scoring: Boeing 737 MAX MCAS, COVID-19 ML models evaluated in the Roberts et al. systematic review, and the Amazon recruiting algorithm. The taxonomy was frozen. No gap could be added. Independent assessments were reduced to permission levels before comparison. The decision rule required zero permissive disagreements and at least two agreements out of three.

The held-out result is bounded. The compiler agreed on two cases: Boeing MCAS at review-required, and COVID-19 ML models at the lowest clinical-use level. It produced one permissive disagreement: Amazon recruiting, where the compiler emitted experiment-authorized while the independent assessment placed the ceiling at review-required. The permissive case failed through a structural mechanism. The frozen permission hierarchy placed all induced gaps as ALR-level requirements. A system with **G2 target-action specification** open — a known proxy-target mismatch — is blocked from ALR, but can still reach AEX if the two structural skeleton gaps are bounded.

The Boeing case exposes the same mechanism from the other side. In the raw H02 evidence package, MCAS had **S2 evidence freshness** scored open; this was a first-class package entry, not an inference added after comparison. The single-sensor angle-of-attack architecture left the evidential basis unmonitored against a live validity failure. AEX requires both structural skeleton gaps to be bounded. The skeleton therefore blocked AEX before the induced-gap placement could matter. Amazon had the skeleton bounded, so the induced-gap placement mattered.

The finding is not that the taxonomy lacks a gap. It is that the placement of induced gaps in the permission hierarchy is a policy choice the framework does not force. The compiler is sound relative to the frozen hierarchy, but the hierarchy was too permissive relative to blind independent judgment. This is representation-relativity in the permission hierarchy, not missing evidence in the taxonomy.

Held-out scoring used the six induced gaps exercised by the three held-out cases. **G7 reason traceability** was inert for all three. It gates the adverse-action reason-traceability obligation induced by the credit stress test, and none of the held-out cases presented that failure mode. The emitted permission level was identical with or without G7 present in the profile.

This result does not show that the taxonomy is complete for all future socio-technical failures. It shows something more precise. Given this induction set, the harmful deployments force a stable set of evidence obligations. Those obligations are structurally distinct. They recover the induction cases, align with independent regulatory obligations in FDA and ECOA, and generalize only up to a revealed boundary: ALR-vs-below failures are covered by the induced gaps, while the AEX-vs-REV placement of those gaps remains a policy choice. That boundary is itself a result.

### 2.6 Blind recovery in FDA and ECOA

The socio-technical induction produces a gap taxonomy without reading regulatory text. We next ask whether the induced gaps correspond to obligations that regulators later named independently.

The audit is blind in the same sense as the physical standards audits. The gap definitions are fixed before the regulatory documents are opened. No FDA, ECOA, Regulation B, or CFPB text is used to define the gaps. The regulatory documents are consulted only after the induction trace is complete, and the locked gap definitions are then compared against the external requirements.

The FDA audit uses the locked taxonomy from Section 2.5. The names below are canonical gap IDs, not a second FDA-specific taxonomy. Five entries from that taxonomy correspond exactly to named elements in the FDA's 2025 AI guidance.

**G3 deployment distribution** corresponds to distribution-shift controls and specification of the intended-use population. **G4 scope coverage** corresponds to validation dataset diversity and site representation requirements. **G1 operating-point utility** corresponds to clinical performance metrics at the intended operating point. **S2 evidence freshness** corresponds to post-market monitoring and real-world performance surveillance. **G6 authority and rollback** corresponds to the requirement for an algorithm change protocol and a response plan when performance degrades.

**G2 target-action specification** is handled separately. It corresponds to intended-use and indications-for-use language, but it is treated here as part of the input contract: the action target must be specified before the compiler can assess any downstream evidence gap. For that reason, it is not counted as one of the five deployment-evidence matches in Table 1.

These matches are exact in the relevant sense. The compiler induced or carried forward the evidence obligation before the FDA text was opened. The FDA guidance names the same obligation in regulatory language.

The Epic tolerance result is treated as a medical-depth result rather than as a same-axis entry in Table 1. In the Epic case, broad medical rollout is blocked by compound evidence gaps, and the compiler's tolerance interval brackets the externally observed sepsis-model degradation. That finding concerns the interaction of G1 operating-point utility, G3 deployment distribution, and G5 action blast radius; it is not a single-axis policy margin analogous to the 3GPP reliability margin.

One canonical gap is stricter than the current regulatory text. The FDA guidance requires operating-point metrics such as sensitivity, specificity, positive predictive value, and negative predictive value. G5 action blast radius adds a more precise relationship: those metrics must be interpreted against the scope of the clinical action. A model with positive predictive value 0.12 does not authorize the same action when it flags 20% of all inpatients as when it flags 1% of ICU patients. The metric is the same. The licensed action is not.

Two FDA requirements are outside the induced evidence package: cybersecurity and user-interface/labeling adequacy. These are real obligations, not mere paperwork. Cybersecurity is a software-and-threat axis: a device can be robust or vulnerable independent of whether a cybersecurity report was filed. User-interface and labeling adequacy can also be a human-factors axis: users may or may not understand the device, its limits, and how to use its output safely. They are outside this package only because no deployment failure in the induction set failed through cyber compromise, adversarial manipulation, or unsafe user communication. The compiler therefore has no supplied gap through which to induce them. Its silence is correct. It shows that this deployment-failure corpus does not recover the whole regulatory framework.

The ECOA audit tests **G7 reason traceability**. This gap was forced by a credit adverse-action stress test designed to satisfy the six preceding gaps. The model was specified for the action target, validated across the deployment population, bounded at the individual level, constrained in blast radius, and placed under human authority. The compiler still over-authorized because the decision pipeline contained no auditable computational path from the model output to the specific principal reasons required for adverse action.

After that gap was locked, ECOA, Regulation B, and CFPB guidance were opened. The correspondence is exact. Consumer credit law requires a specific and accurate statement of the principal reasons for adverse action. Model complexity is not an excuse. A risk score alone is not enough. The evidence must support not only the decision, but the reason the decision legally requires.

The audit also identifies two credit obligations outside the supplied evidence package: disparate impact and upstream data accuracy. These are real regulatory concerns. But an individual adverse-action package cannot certify population-level discrimination, and a reason token cannot certify the provenance and accuracy of upstream credit data. Those questions live on different evidence axes.

![Figure 5. FDA and ECOA blind audit. Left: locked taxonomy vs. FDA 2025 AI guidance requirements — exact matches for G3 deployment distribution, G4 scope coverage, G1 operating-point utility, S2 evidence freshness, and G6 authority and rollback; one compiler-strict relation for G5 action blast radius; and two outside-package axes, cybersecurity and user-interface/labeling adequacy. Right: G7 reason traceability vs. ECOA adverse-action requirement — exact match; disparate impact and upstream data accuracy outside individual evidence package.](figures/fig5_fda_ecoa_audit.png)

**Figure 5. FDA and ECOA blind audit.**  
Left: the locked taxonomy mapped against FDA 2025 AI guidance. Five requirements recover exactly through canonical taxonomy entries: G3 deployment distribution, G4 scope coverage, G1 operating-point utility, S2 evidence freshness, and G6 authority and rollback. One relation is compiler-strict: G5 action blast radius requires clinical utility to be calibrated to deployment scale, so the same PPV does not license the same action at different blast radii. Two axes, cybersecurity and user-interface/labeling adequacy, are outside the induced evidence package. Right: G7 reason traceability mapped against ECOA, Regulation B, and CFPB Circular 2022-03. The match is exact. Disparate impact and upstream data accuracy are outside the individual adverse-action evidence package.

The point is not that the compiler performs compliance review. It does not. The point is that evidence-induced gaps recover the evidence-grounded subset of regulatory structure. Where regulation names an obligation that real deployment failures force, the compiler finds it. Where regulation names an obligation outside the supplied evidence, the compiler is silent.

This is the same pattern as in the physical layer. Exact recovery marks the boundary the evidence forces. Compiler-strict results mark places where the evidence structure is more precise than the regulatory prose. Compiler-permissive results mark real obligations that this evidence package cannot reach. Together, the FDA and ECOA audits show that the socio-technical gap taxonomy is not merely an internal artifact of the induction loop. It converges with independent regulatory structures built for medical AI and consumer credit.

## 3. Why the boundary is forced

The results above show that the compiler recovers some regulatory boundaries
exactly, stops short of others, and is silent where the supplied evidence cannot
speak. This section states why those outcomes are forced by the evidence rather
than chosen by the compiler. The same statement covers the physical and the
socio-technical layers, because both are instances of one object.

The compiler has only two inputs. The first is an evidence package. The second is
a permission hierarchy.

The evidence package names the ways a requested action could be unsound. Each
named gap has a status: open, bounded, or closed. An open gap means the evidence
has not ruled out the corresponding failure. A bounded gap means the failure is
constrained but not eliminated. A closed gap means the evidence has ruled it out
at the level required for the requested permission.

The permission hierarchy orders possible actions from weaker to stronger. A weaker
permission may require only that some gaps be bounded. A stronger permission may
require those same gaps to be closed, and may require additional gaps as well. A
permission is blocked when at least one gap required for that permission remains
open.

The compiler applies one rule. It scans the hierarchy from strongest permission to
weakest and returns the first permission whose required gaps are bounded or closed.
It also returns a certificate naming the gaps checked and the first gap that blocks
any stronger permission. That returned permission is the evidence-forced boundary.

### 3.1 One authorization map

Behind the two inputs there is a single object. Let `X` be the space of underlying
states the action operates on: in a physical system, a configuration of
approximation errors across components; in a socio-technical system, a concrete
deployment of a model into a population, an oversight structure, and an action
pipeline. Let `P` be the permission hierarchy, ordered from weaker to stronger,
with meets and joins (the strongest permission below a set, the weakest permission
above it).

Define the true authorization `A*: X -> P` by a single rule:

> `A*(x)` is the strongest permission `p` such that no failure mode required for `p`
> is unresolved in state `x`.

This is the same function in both layers. In a physical system, "no failure mode
unresolved" means the worst-case functional over the configuration is below the
acceptability threshold. In a socio-technical system, it means each failure the
permission depends on does not obtain in the deployment. The difference between the
layers is not in `A*`. It is in how the state `x` is represented and in what
"unresolved" measures. The function is one.

The compiler does not see `x`. It sees a summary. Let `q: X -> E` be the evidence
map: the mean functional in the physical case, the evidence profile in the
socio-technical case. The compiler must return one permission for every state that
produces the same summary, because it cannot distinguish them. Those states are the
*fiber* over `e`. Because evidence improves monotonically and we ask what a given
quality of evidence licenses, the relevant object is the level set

    F(e) = { x in X : q(x) <= e },

the set of states at least as good as the summary `e` reports.

### 3.2 The authorization gap is an interval

On the fiber `F(e)`, the true authorization `A*` is generally not constant. Two
states can produce the same summary and still warrant different permissions. This
defines the **authorization gap** as an interval in `P`:

    gap(e) = [  meet over F(e) of A*  ,  join over F(e) of A*  ].

The lower endpoint is the strongest permission that is sound for *every* state the
evidence cannot rule out. The upper endpoint is the strongest permission the
evidence *supports* for *some* state in the fiber. The gap is the distance between
what is safe and what is merely consistent with the summary.

This is the object measured in Section 2.3 and induced in Section 2.5. In the Ising
and turbo experiments, `q` is the mean and the join over the fiber is the
worst-case functional; the interval is the measured `[mean, worst-case]` band. In
the deployment cases, `q` is the evidence profile and the interval is the spread of
sound permissions across deployments that submit the same evidence. One interval,
two instantiations.

### 3.3 Soundness, sharpness, and the representation theorem

A compiler is *sound* if it never returns a permission that is unsound for some
state in the fiber. The sound compiler returns the lower endpoint, the meet. The
compiler used here is sound by construction: it cannot authorize a permission until
the gaps that permission requires are no longer open, and an open gap is exactly a
fiber on which the meet sits below that permission.

A compiler is *sharp* if it returns the strongest permission the evidence supports
without unnecessary conservatism. The question is when sound and sharp coincide.

> **Representation theorem.** The sound compiler recovers the true authorization
> on every fiber if and only if `A*` is constant on each fiber of `q` — equivalently,
> if and only if every permission-relevant failure mode is detectable in the evidence
> representation. When `A*` is constant on the fiber, meet equals join and the
> compiler returns the unique correct permission; any sound and sharp compiler must
> return the same one. When `A*` is non-constant on the fiber, the gap has positive
> width, and no compiler reading only `q` can recover the boundary, because two
> states with different correct permissions present the same evidence.

The proof is the indistinguishability argument, now made precise. If `A*` is
constant on `F(e)`, the evidence determines the correct permission and the meet,
join, and true value coincide. If `A*` is non-constant on `F(e)`, two states in the
fiber have different correct permissions; the compiler returns one output for both;
that output is wrong for at least one of them. The failure is representational, not
computational. No algorithm recovers a distinction the evidence does not contain.

The distinction soundness/sharpness is exactly the distinction meet/join. A failure
mode invisible to the evidence does not make the stronger permission unsupported —
the evidence supports it (the join reaches it). It makes the stronger permission
*unsound* (the meet does not). Conflating the two is the same error as conflating
the endpoints of the gap.

### 3.4 When the gap is real: world-realizability

The representation theorem says the gap is non-empty exactly when `A*` is non-constant on the fiber. The remaining question is whether that condition is met in practice, or whether it is an artifact of how the gaps were named.

> **Non-constancy lemma.** Let `G` be a permission-relevant failure mode, and let `e` be an evidence profile that does not close `G`. If `G` is *world-realizable at `e`* — meaning the states consistent with `e` are not contained entirely within "`G` obtains" nor entirely within "`G` does not obtain" — then `A*` is non-constant on `F(e)`, and the authorization gap is non-empty.

World-realizability is the domain assumption, and it is substantive. It holds for a gap precisely when the failure the gap names is a fact about the deployment world that its closing token is evidence of but does not constitute. A gap fails the assumption only when the world-fact and the token-fact are identical — when "the failure is absent" means nothing more than "a document was filed." Such a requirement is a real obligation, but it is a documentation requirement, not an authorization gap: its fiber is constant, its interval is empty, and the theorem correctly excludes it.

We did not leave this as an assertion. We preregistered an adversarial falsification attempt for every induced gap. For each gap, the attempt asked whether a deployment could be constructed in which the world-fact was fully determined by the closing token. If such a construction existed, the gap would be reclassified as a documentation requirement. If no such construction existed, the gap would survive as world-realizable.

All seven induced gaps survived. For each one, we found two deployment states consistent with the same evidence profile that differ in whether the failure obtains. The two highest-risk gaps, **G6 authority and rollback** and **G7 reason traceability**, were tested in both directions. For G6, a written authority contract can exist without actual architectural override capacity, and genuine physician review can exist without a filed contract. For G7, a post-hoc LIME-style reason token can exist without an auditable causal path in the model's forward pass, and an interpretable model can contain the causal path before any reason token is filed.

The witness pairs are given in Appendix C. The result is not proof that every future obligation is world-realizable. It is narrower and stronger: the particular induced taxonomy used here was subjected to an explicit falsification attempt, and no induced gap collapsed into a pure documentation requirement. The Section 3.4 hypothesis is therefore not a naming artifact. It is corroborated across the taxonomy by witness construction.

### 3.5 Two kinds of access to one object

The physical and socio-technical layers are the same object under the same theorem,
but the evidence available about the object differs, and the paper states this
plainly.

In the physical layer, ground truth exists. Both endpoints of `gap(e)` are
computable: the mean is measured directly, the worst-case is found by scanning
components. The interval is *measured* — its width and location are reported (the
roughly 1 dB SNR band, the `[0.223, 0.334]` total-variation interval). The physical
layer is where the abstract interval acquires concrete geometry.

In the socio-technical layer, ground truth is unavailable and the fiber is not
enumerable. The interval cannot be measured. But the non-constancy lemma applies
once world-realizability is witnessed, and the falsification attempt in Section
3.4 supplies those witnesses for the induced taxonomy. The induction loop of
Section 2.5 recovers which gaps make the interval non-empty. The socio-technical
layer is where the interval is proved conditionally, stress-tested by witness
construction, and induced from failure.

These are different epistemic acts on one structure: the physical layer measures
the gap; the socio-technical layer proves it. The theorem unifies them at the level
of the lemma. Neither layer is the analogy of the other; both are instances.

### 3.6 Why silence is also a result

The theorem also explains the compiler's non-matches. A stop is not necessarily a miss. Once `q` and `P` are fixed, each external requirement stands in a determinate relation to the gap structure. After the preregistered stability and held-out tests, the paper reports six such relations.

- **Representation-relative alignment** occurs when a frozen evidence map and permission hierarchy align with an external threshold, but perturbing the hierarchy destroys the apparent recovery. The run is blind, but the boundary is not forced by the evidence representation alone.
- **Exact recovery** occurs when the evidence contains the relevant failure mode and the external threshold names the meet — the boundary the evidence forces.
- **Same-axis policy margin** occurs when the meet is visible and the external standard sits above it on the same evidence axis. The compiler reaches the evidence ceiling and stops; the remaining distance is policy above evidence.
- **Different evidence axis** occurs when `q` ceases to be the relevant representation and the next threshold depends on a different evidence map entirely. The compiler cannot recover it from `q`, and should not try.
- **Finer evidence resolution** occurs when `q` separates states the external regime collapses — the fiber is finer than the regime's classes.
- **Outside the supplied evidence package** occurs when the obligation is real but no supplied gap can speak to it. The compiler is silent because the evidence is.

These relations are not excuses. They are the output space. The correspondence matrix is therefore not a list of successes with exceptions. It is a partition of what the evidence forces, what the supplied representation and hierarchy determine, what policy adds, what requires another axis, what the evidence resolves more finely, and what the evidence cannot reach.

### 3.7 What the theorem proves

The theorem proves a conditional claim, and it is worth stating what it does not prove. It does not prove that every regulatory requirement is evidence-grounded. It does not prove that any policy margin is correct. It does not prove that the selected domains exhaust the space of authorization systems. It does not choose the evidence map `q` or the permission hierarchy `P`.

That last limitation is central. The theorem says what follows once `q` and `P` are fixed. It does not say that the chosen representation and hierarchy are themselves forced. A permission hierarchy can place a real gap too high or too low. When it does, the compiler can remain sound relative to that hierarchy while the hierarchy is too permissive relative to an independent assessment.

The held-out Amazon recruiting result is the concrete example. The taxonomy contained the relevant gap: **G2 target-action specification**. The known proxy-target mismatch blocked ALR. But the frozen hierarchy placed induced gaps only at ALR, so AEX remained reachable once the two structural skeleton gaps were bounded. The independent assessment placed the ceiling at REV. The compiler went above it. That disagreement does not refute the representation theorem. It shows exactly where the theorem stops: evidence can force a boundary only after the evidence map and permission hierarchy have been supplied.

There is no contradiction between **G2** being world-realizable and **G2** being placed at the wrong level in the hierarchy. The first fact says the gap is real: proxy validity is a world-fact, not a document. The second says the supplied hierarchy put that real gap too high. A gap can be genuine and still be mis-placed.

It proves something narrower and exact. Given a fixed evidence map `q` and a fixed permission hierarchy `P`, the strongest sound permission is the meet of `A*` over the fiber, and the sound compiler returns it. If the permission-relevant failures are detectable — if `A*` is constant on the fiber — that meet is the unique correct boundary, and any correct compiler must return it. If a relevant failure is world-realizable but undetectable, the gap has positive width and recovery from `q` is impossible.

This is enough for the empirical results. The exact matches are meaningful because the compiler was given no regulatory targets and still returned the meet at the boundary the external framework later names. The 3GPP demotion is meaningful because the perturbation showed that a blind match was not hierarchy-independent recovery. The held-out Amazon disagreement is meaningful because it exposed a policy choice in the permission hierarchy rather than a missing gap. The forced object is not the whole regulation. It is the evidence-grounded component of authorization — the part a fixed evidence package and permission hierarchy can force.

## 4. Correctness of the blind-audit protocol

Section 3 explains why an evidence boundary can be forced. This section explains why the reported correspondences were not introduced by fitting the compiler to the standards after the fact.

A blind audit is correct if every reported correspondence is determined by artifacts fixed before the target document is opened: the evidence package, permission hierarchy, extraction rule, compiler output, comparison corpus, and classification rule.

Correctness here does not mean that the external regulation is correct. It does not mean that every regulatory requirement is evidence-grounded. It means that the audit is non-circular. The compiler output must be fixed before comparison, and the rules for classifying comparison outcomes must not change after the target document is read.

The protocol has four stages.

First, freeze the inputs. The evidence package, permission hierarchy, gap definitions, and extraction rule are fixed before the target standard or regulation is consulted.

Second, run the compiler. The compiler emits boundaries, certificates, stopping points, or induced gaps using only the frozen inputs.

Third, open the external document. The relevant standard, guidance, statute, or regulatory interpretation is consulted only after the compiler output has been recorded.

Fourth, classify the relationship. Each comparison is assigned to a pre-defined correspondence class: exact recovery, same-axis policy margin, different evidence axis, finer evidence resolution, or outside the supplied evidence package. Where a preregistered perturbation tests stability of the extraction operator, the result may also be reported as representation-relative alignment.

No stage may be revised using information from a later stage.

### 4.1 What is frozen before comparison

The frozen object depends on the audit type.

In the physical audits, the frozen object is an evidence geometry and a boundary-extraction rule. For 3GPP, the compiler scans the BER/BLER authorization surface over signal-to-noise ratio under a frozen permission hierarchy before any 3GPP document is opened. The extracted BLER boundaries are recorded first. A preregistered perturbation then tests whether the apparent match is stable to plausible hierarchy changes. The standard thresholds are read afterward.

For FAA instrument approach operations, the frozen object is the visual-acquisition geometry. The decision-height and runway-visual-range relation is derived from glide slope, threshold crossing height, and approach-lighting geometry before FAA category thresholds are consulted. The saturation point of the visual evidence axis is also recorded before comparison.

In the socio-technical audits, the frozen object is a gap taxonomy. The compiler begins with a weak profile, over-authorizes documented harmful deployments, and induces the missing evidence obligations needed to block those over-authorizations. The induced gaps are locked before the FDA, ECOA, Regulation B, or CFPB materials are opened. Regulatory language is then compared to the locked gap definitions.

In all cases, the audit forbids target leakage. The compiler is not given threshold values, category names, service-class labels, regulatory text, or target requirements before it emits its boundary or gap.

### 4.2 What counts as a match

A match is not a verbal resemblance. It is a relationship between a compiler output and an external requirement.

An exact recovery is recorded only when the compiler boundary and the external threshold identify the same obstruction at the same level of resolution tested by the audit. In FAA, this means the geometry-derived decision-height and runway-visual-range pair matches the Category I threshold within the pre-specified sweep resolution. In FDA and ECOA, it means a locked gap asks for the same missing evidence obligation that the external document later names. In 3GPP, the preregistered perturbation ruled out exact recovery in this sense: the initial BLER match did not survive hierarchy perturbation.

A representation-relative alignment is recorded when the compiler aligns with an external threshold under the frozen representation and hierarchy, but a preregistered perturbation shows that the boundary tracks the hierarchy rather than a hierarchy-independent feature of the evidence surface.

A same-axis policy margin is recorded when the external threshold is stricter than the compiler boundary on the same evidence axis. The compiler must have reached a boundary within the frozen representation, and the regulation must sit above it on that same axis. The margin is measured in the units of that axis.

A different evidence axis is recorded when the compiler's evidence representation stops being the relevant representation. The external threshold may be real and physically grounded, but it depends on evidence the supplied package does not contain.

A finer evidence resolution is recorded when the compiler distinguishes an evidence relation more precisely than the external regime names it.

An outside-package result is recorded when the external obligation is real but no supplied gap can induce or certify it. This is not a failed match. It is a correct silence.

These categories are fixed before comparison. They are not created to rescue individual cases.

### 4.3 Non-circularity lemma

The blind-audit protocol is non-circular if three conditions hold.

First, the compiler output is fixed before the target document is opened.

Second, the comparison classes are fixed before the target document is opened.

Third, the evidence package and permission hierarchy are not revised after the target document is opened.

Under these conditions, an exact correspondence cannot be introduced by post-hoc editing without violating the protocol.

The reason is direct. The compiler output is a function of the frozen evidence package, permission hierarchy, and extraction rule. The external requirement is read only after that output is fixed. If the output matches the external requirement, the match is an observed correspondence between two independently fixed objects. If it does not match, the protocol can classify the non-match, but it cannot alter the compiler output to make it match.

This is why the non-match categories matter. A protocol that reports only exact matches is vulnerable to cherry-picking. A protocol that also reports representation-relative alignment, margins, different-axis stops, finer-resolution results, and outside-package silence has falsifiable outcomes. The compiler can succeed, align only under a fixed representation, stop short, be stricter, be more permissive, or be silent. All outcomes are reportable.

The audit is therefore not a search for confirmations. It is a partition of the external framework by what the frozen evidence package can and cannot force.

### 4.4 Application to the four audits

The 3GPP audit tests same-axis physical alignment under a fixed representation. The evidence axis is channel reliability. The compiler extracts BLER transitions under the frozen BER/BLER representation and permission hierarchy before reading the standard. The later comparison finds alignment at BLER 0.10 and 0.02. The preregistered perturbation then demotes that alignment: across 59 alternative hierarchies, the operator recovered 0.10 in 5.1% and 0.02 in 3.4% of cases, with zero structured recovery in the granularity and offset families. The audit therefore reports representation-relative alignment, not exact recovery.

The FAA audit tests layered physical recovery. The evidence axis is visual acquisition. The compiler derives the Category I boundary from geometry and records the saturation point at which that geometry stops determining the decision. The later comparison finds exact recovery at Category I, a different evidence axis at Category II, and outside-package silence for Category III autoland and fail-operational requirements.

The FDA audit tests socio-technical gap induction. The evidence axis is the set of deployment failures used to induce missing evidence obligations. The locked taxonomy is compared against the FDA's AI-enabled device software guidance only after induction. The later comparison finds exact matches for the deployment-evidence obligations the harmful cases forced, a compiler-strict relation where blast radius refines operating-point utility, and outside-package silence for obligations not present in the induction failures.

The ECOA audit tests reason traceability. The credit stress test is constructed so that the preceding gaps are satisfied. The compiler still over-authorizes because the evidence package lacks a validated reason token. That gap is locked before ECOA, Regulation B, and CFPB materials are opened. The later comparison finds exact recovery of the adverse-action reason requirement and outside-package silence for population-level disparate impact and upstream data accuracy.

The held-out socio-technical evaluation tests whether the induced taxonomy can be used without adding gaps. It agrees on two of three cases and produces one permissive disagreement. The MCAS agreement is explained by the raw H02 package itself: **S2 evidence freshness** was scored open, so the structural skeleton blocked AEX before induced-gap placement mattered. The Amazon disagreement reveals a boundary of the permission hierarchy, not a missing gap: induced gaps were placed at ALR, so AEX remained available for Amazon recruiting despite an open target-action specification gap.

The same protocol is used in all four audits. The evidence differs. The documents differ. The comparison classes do not.

### 4.5 What the protocol proves

The protocol proves non-circularity.

It shows that the reported correspondences are between frozen compiler outputs and external requirements consulted afterward. It rules out the strongest post-hoc objection: that the compiler saw the target and was adjusted to recover it.

It also proves that the non-matches were not hidden. Every external requirement compared in the audit must be assigned to one of the correspondence classes. Exact recovery is only one possible outcome.

The protocol does not prove that the selected domains were the only possible domains. It does not prove that all regulatory requirements are evidence-grounded. It does not prove that a same-axis policy margin is normatively correct. It does not prove that an outside-package obligation is unimportant.

Those are different claims.

The blind audit establishes that, in these domains, the evidence-grounded subset of the external framework was recoverable or alignable without reading the framework, and that the unrecovered or demoted subset had structured reasons for being unrecovered or demoted.

That is the empirical claim the matrix reports.

### 4.6 Why this matters

The theorem in Section 3 and the protocol in this section do different work.

The theorem says that, once the evidence package and permission hierarchy are fixed, the strongest sound permission is determined when the relevant failures are visible.

The protocol says that the evidence package, hierarchy, extraction rule, and comparison rule were fixed before the external standards were opened.

Together they answer the central objection.

The boundaries are not arbitrary because the theorem forces them from the evidence. The correspondences are not cherry-picked because the blind protocol fixes the compiler output before comparison and requires every non-match to be reported.

The result is therefore not that the compiler rediscovered regulation. It is more precise than that.

The compiler recovered the part of regulation that the evidence forced, identified the part that was only representation-relative, measured the part that policy added, identified the points where another evidence axis was required, and stayed silent where the supplied evidence could not speak.

## 5. Scope and limits

The claims in this paper are conditional. That is a strength, not a caveat to hide.

First, the 3GPP result is representation-relative. The original audit was blind: the BER/BLER representation and permission hierarchy were fixed before the standard was opened. But the perturbation experiment shows that BLER 0.10 and 0.02 are not hierarchy-independent ridges of the evidence surface. The standard alignment is therefore a result about a fixed representation and permission granularity, not a free-standing recovery of 3GPP service thresholds.

Second, held-out generalization is bounded. The induced taxonomy recovered the induction cases and aligned with FDA and ECOA obligations, but the held-out evaluation produced one permissive disagreement. That disagreement was not a missing-gap failure. It was a hierarchy-placement failure: induced gaps were placed at ALR, so AEX remained reachable for a known proxy-target mismatch. This does not make **G2 target-action specification** less real; Appendix C shows that G2 is world-realizable. It shows that a real gap can be placed at the wrong level in the supplied hierarchy. The framework therefore does not force the placement of gaps inside the permission hierarchy.

Third, the theorem is representation-relative throughout. It proves what follows from a fixed evidence map `q` and a fixed permission hierarchy `P`. It does not choose `q`. It does not choose `P`. It does not prove that a supplied hierarchy is normatively right.

Fourth, the cross-domain evidence is a convergence result, not a sampling theorem. The four traditions were selected because they expose different kinds of authorization structure: communication reliability, visual acquisition, medical AI deployment, and credit adverse action. The paper does not claim that these four exhaust the space of consequential automated systems.

These limits define the contribution. The framework separates evidence-forced boundaries from representation-relative alignments, policy margins, different evidence axes, finer compiler resolution, and outside-package obligations. It does not make every boundary forced. It makes the difference auditable.

## Appendix C. World-realizability falsification witnesses

We attempted to falsify world-realizability for each induced gap by constructing a deployment in which the gap's world-fact was fully determined by its closing token. A gap would fail if the world-fact and token-fact were logically identical. All seven induced gaps returned **not falsified**.

**G1 operating-point utility.** Witness pair: one system has sensitivity 0.80 at the deployed threshold with no operating-point report filed; another has sensitivity 0.33 at the deployed threshold with no operating-point report filed. The evidence profile is the same. The world-fact differs.

**G2 target-action specification.** Witness pair: one model has genuine proxy validity in the deployment population with no specification document filed; another predicts an invalid proxy, such as cost rather than care need for a subpopulation, while a specification document is filed. The token and the world-fact come apart.

**G3 deployment distribution.** Witness pair: one model is deployed into a stable population with no external validation token; another is validated against a distribution generated by its own output history, as in predictive-policing feedback. The evidence token does not constitute independent distributional stability.

**G4 scope coverage.** Witness pair: one model has genuine individual-level calibration with no individual certifier issued; another population-score model receives an individual certifier making unsupported claims. Population validity and individual validity are different world-facts.

**G5 action blast radius.** Witness pair: one model is used by a single physician in a supervised setting with no scope contract filed; another has global routing and difficult override while a scope contract is filed. The deployment architecture determines the blast radius, not the document alone.

**G6 authority and rollback.** Both directions survive. A Dutch-style deployment can file an authority contract while lacking actual override capacity. A physician can genuinely review and halt every output before action with no contract filed. The witness pair is genuine oversight without a contract versus nominal oversight with a contract. The world-fact is actual architectural authority.

**G7 reason traceability.** Both directions survive. An opaque ensemble can generate a post-hoc LIME-style reason token without an auditable causal path in the forward pass. A logistic regression can contain a genuine causal path from features to reason candidates before any reason token is filed. The witness pair is an interpretable model with no token versus an opaque model with a post-hoc token. The world-fact is computational traceability, not the emitted explanation alone.
