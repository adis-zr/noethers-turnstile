# Spec: _The Conservation of Incomplete Evidence_

## Kill-or-promote plan for moving from four-domain audit to conservation-law paper

**Target venue:** PNAS / Nature Computational Science  
**Current fallback:** the four-domain blind-audit paper remains viable.  
**Promoted version:** a conservation-law paper, only if the gates below pass.

## One-line thesis

Authorization is governed by a conserved relationship between evidence incompleteness and licensed action. As evidence is hidden, refined, or re-represented, the authorization boundary moves lawfully: monotonically, with controlled breakpoints, and invariantly across admissible representations of the same failure structure.

Regulation is one place this law surfaces. It is not where the law comes from.

## The fork

The current paper says:

> A compiler can partition regulatory structure into what evidence forces, what representation co-determines, what policy adds, and what the supplied evidence cannot reach.

The conservation paper says:

> There is a law governing how authorization changes as evidence-completeness changes. Regulatory boundaries are witnesses of that law, not the source of it.

The second paper is stronger. It is also riskier.

Do not promote unless the gates below pass.

---

# 0. Kill-or-promote gates

The conservation rewrite proceeds only if all four gates pass.

## Gate 1 — The conserved object can be named

The paper may use “conservation” only if it names the conserved object precisely.

The boundary is not conserved. It moves.

The permission level is not conserved. It changes.

The gap width is not necessarily conserved. It may shrink under refinement.

The likely conserved object is the **authorization-gap functional**: the relationship between evidence incompleteness and the interval of permissions still compatible with the evidence.

Required sentence:

> The conserved object is the authorization-gap functional: the map from an evidence fiber to the interval of permissions induced by the unresolved failure modes in that fiber.

If this cannot be stated cleanly, stop. Return to the audit paper.

## Gate 2 — The admissible transformation class can be fenced

The paper may not say “any metric” or “any representation.”

It may say:

> any admissible evidence transformation that preserves the failure preorder.

Or, if the proof supports it:

> any metric locally equivalent to the canonical product metric on failure-vector space and monotone with respect to failure refinement.

The exact condition matters. It is not fine print. It is the theorem.

Required output:

> A closed condition [P] on admissible metrics, divergences, or representations.

Adversarial test:

> Can a referee construct a pathological metric that looks admissible but breaks the bound?

If yes, [P] is too loose.

If [P] cannot be fenced, stop. Return to the audit paper.

## Gate 3 — The transformation sweeps show controlled boundary motion

The conservation paper needs experiments of transformation, not just point matches.

The curves must show:

- less evidence produces weaker authorization;
    
- more evidence produces stronger or equal authorization;
    
- boundary movement tracks the chosen divergence or incompleteness measure;
    
- breakpoints occur where the theory predicts;
    
- no unexplained jumps appear.
    

Do not claim literal smoothness unless the underlying authorization axis is continuous. A finite permission hierarchy naturally creates steps.

Preferred language:

> monotone boundary motion with predicted breakpoints.

Avoid:

> smooth with no cliffs.

If the sweeps do not show controlled monotone boundary motion, stop. Return to the audit paper.

## Gate 4 — Main-body legs are selected by law-quality, not story-quality

The body should include the experiments that best demonstrate the law.

Do not choose legs because they are famous.

Do not choose legs because they broaden the regulatory survey.

Do not choose legs because they make the table look complete.

Choose legs because they show controlled transformation of evidence into authorization.

If Epic is noisy, it goes to supplement.

If 3GPP and ECOA remain point audits, they go to supplement.

If only turbo and FAA cleanly show the law, the main body is a two-leg paper.

---

# 1. What is already viable

The current paper is viable as a four-domain blind-audit paper.

Its claim is:

> Given a fixed evidence package and permission hierarchy, the compiler returns the strongest sound permission and partitions external regulatory structure by what the evidence can force.

That paper already has a coherent architecture:

1. evidence gap;
    
2. compiler boundary;
    
3. blind audit;
    
4. correspondence partition;
    
5. representation theorem;
    
6. non-circularity protocol;
    
7. scope and limits.
    

Do not destroy this paper unless the conservation gates pass.

The fallback title is not _The Conservation of Incomplete Evidence_. It is something closer to:

> Evidence-forced authorization boundaries in consequential automated systems

or

> Blind recovery of evidence-grounded authorization boundaries

The conservation title is earned only if the invariant is named and the transformation sweeps carry the body.

---

# 2. Workstream 1 — State the law

## 2.1 Name the conserved object

This gates the whole rewrite.

The title spends its precision budget on force. The abstract must pay that rigor back.

Required abstract opening:

> The conserved object is the authorization-gap functional: the map from incomplete evidence to the interval of permissions left unresolved by that evidence.

Then define it in body language:

> An evidence package does not license a single action merely by being favorable. It defines a set of worlds still compatible with the evidence. Across that set, some stronger permissions may be possible in some worlds but unsound in others. The authorization gap is the interval between the permission safe for every compatible world and the permission possible in at least one compatible world.

Then state the law:

> Admissible transformations of evidence may change the representation, metric, or order in which gaps are discovered. They do not change the authorization-gap functional when they preserve the underlying failure preorder. Refining evidence can only shrink the gap. Hiding evidence can only widen it. The compiler returns the lower endpoint: the strongest permission sound for every world the evidence has not ruled out.

This is the clean version.

Only introduce formal notation after the claim is clear.

## 2.2 Decide whether “conservation” is literal or metaphorical

There are two possible outcomes.

### Outcome A — Literal conservation

Use the title _The Conservation of Incomplete Evidence_.

Requirements:

- name the conserved functional;
    
- define admissible transformations;
    
- show invariance under those transformations;
    
- prove monotone refinement/hiding;
    
- demonstrate boundary motion empirically.
    

Then the conservation claim is real.

### Outcome B — Continuity / invariance, not conservation

If the proof only gives Lipschitz continuity, monotonicity, or bounded sensitivity, do not force the word conservation.

Possible title:

> The Continuity of Authorization under Incomplete Evidence

or

> Invariant authorization boundaries under evidence refinement

This is still a strong paper. It is just not a conservation paper.

## 2.3 Fence the admissible class [P]

This is the most attackable theorem surface.

The paper must not say:

> any metric

or

> any representation

or

> any divergence.

The theorem must say something like:

> For any admissible evidence representation satisfying [P], the authorization-gap functional is invariant up to order-preserving equivalence.

The condition [P] is the law’s domain of definition.

Candidate forms of [P]:

1. **Failure-order preservation**  
    The transformation preserves which failure modes are open, bounded, or closed, and preserves the partial order of evidence refinement.
    
2. **Local metric equivalence**  
    The divergence is locally bi-Lipschitz equivalent to the canonical product metric on failure-vector space.
    
3. **Monotone product structure**  
    The representation decomposes over failure coordinates and respects coordinate-wise refinement.
    
4. **Admissible projection / refinement**  
    Evidence hiding is a projection. Evidence refinement is a lift. Both preserve the underlying failure preorder.
    

The proof decides which one is right.

The body must state the condition. The appendix can carry the machinery.

## 2.4 Metric-invariance theorem

Main-body statement:

> Metric-invariance. Within the admissible class [P], changing the metric used to measure evidence incompleteness changes the numerical scale of distance but not the induced authorization ordering. The compiler returns the same permission boundary, and the displacement of that boundary remains bounded by the same authorization-gap functional.

Appendix proof:

- define admissible metric class;
    
- show order preservation;
    
- show same lower endpoint of authorization interval;
    
- show divergence rescaling does not change boundary ordering;
    
- show any violation requires leaving [P].
    

Do not overclaim. The theorem is only as strong as [P].

## 2.5 Order-invariance theorem

The induction loop looks sequential. The object is not.

Main-body statement:

> Order-invariance. When a fixed corpus contains visible permission-relevant failures, the final gap set does not depend on the order in which cases are processed. Different orders change the route by which the compiler discovers the gaps, not the destination.

Required precondition:

> the gap must be visible, and the policy must care about it.

Say this with pride. It is not a weakness. It is the domain of definition.

This theorem explains why socio-technical induction is not merely a story about the order of famous cases. The loop is a discovery procedure over a fixed object.

## 2.6 Source-invariance theorem

This is important, but it is not the conserved quantity.

It answers the LLM objection.

Main-body statement:

> Source-invariance. The soundness of authorization does not depend on the trustworthiness of the source that proposed a candidate gap. Once a gap is written into the evidence contract, the compiler checks it mechanically. The source may be an expert, a regulator, an LLM, a failure report, or a hand-written policy. Discovery credit changes. Authorization soundness does not.

Framing:

> The LLM is the programmer. The compiler is the type checker.

This is the right analogy.

Nobody calls a type checker circular because the programmer knew the intended type. The checker is not there to have ideas. It is there to prevent written claims from lying about what they guarantee.

Keep source-invariance near the theorem family, but do not make it the center of conservation. It is a soundness result.

## 2.7 Demote the representation theorem

The current representation theorem should no longer be the main theorem if the conservation law works.

It becomes the zero-gap boundary case.

Body sentence:

> Exact recovery is the boundary case of the conservation law. When every permission-relevant failure is detectable in the evidence representation, the authorization gap collapses to a point; the lower and upper endpoints coincide; and every sound, sharp compiler must return the same boundary.

This absorbs:

- constant on fibers;
    
- meet equals join;
    
- exact recovery;
    
- impossibility when failure is invisible.
    

The appendix can preserve the full formal statement.

---

# 3. Workstream 2 — Promote transformation experiments

The current Results section is built for the audit paper.

It reports point correspondences:

- match;
    
- margin;
    
- different axis;
    
- finer resolution;
    
- outside package;
    
- representation-relative alignment.
    

A conservation paper needs transformation evidence.

The key empirical question is:

> When evidence is varied, does authorization move according to the law?

## 3.1 Blindness / occlusion sweep

Main-body figure.

Design:

- start with a complete evidence package;
    
- progressively hide outcome-relevant evidence;
    
- run the compiler at each occlusion level;
    
- record emitted permission;
    
- record active gap;
    
- record distance from the complete package.
    

Expected result:

> As evidence is hidden, the boundary weakens monotonically. Breakpoints occur when the hidden evidence crosses the requirements for a stronger permission.

This is the clearest empirical signature of the law.

It also kills the weak recognizability confound.

A recognizer can say “this is Epic.” A recognizer cannot produce a lawful monotone boundary slide under controlled occlusion unless it is actually using the evidence.

## 3.2 Permissivity-vs-divergence curve

Main-body figure.

Design:

- fix one evidence package;
    
- vary another along a controlled path;
    
- compute divergence or incompleteness distance under an admissible metric;
    
- run the compiler;
    
- plot permission level or authorization endpoint against distance.
    

Expected result:

> Difference in permissivity tracks distance in evidence-completeness.

Directional monotonicity is not enough. The strong result is quantitative:

> the landing points and breakpoints occur where the theory predicts.

This is where conserved-quantity language belongs.

## 3.3 Metric-invariance demonstration

Main-body or supplement depending on cleanliness.

Design:

- repeat the divergence curve under several admissible metrics;
    
- show that the numerical x-axis changes;
    
- show that the induced authorization ordering and boundary breakpoints remain stable.
    

Expected result:

> The metric changes the ruler, not the authorization structure.

This is the empirical counterpart of [P].

## 3.4 Projection fidelity sweep

Optional but strong.

Design:

- begin from a high-resolution failure vector;
    
- project it to coarser evidence summaries;
    
- vary projection fidelity;
    
- record the authorization gap.
    

Expected result:

> Coarser projections widen the gap. Finer projections shrink it. Exact recovery occurs when the projection preserves all permission-relevant failures.

This directly connects the conservation law to the old representation theorem.

## 3.5 No unexplained cliffs

Do not require literal smoothness.

A finite hierarchy should produce steps.

What must not appear are unexplained jumps.

Acceptable:

- monotone steps;
    
- predicted breakpoints;
    
- stable ordering across metrics;
    
- boundary movement matching gap closure.
    

Concerning:

- non-monotone permission jumps;
    
- permission strengthening when evidence is hidden;
    
- metric-dependent reversal;
    
- breakpoints that do not correspond to any gap requirement.
    

If those appear, either the law is wrong, the metric class is wrong, or the experiment is outside the domain of definition.

Do not paper over this.

## 3.6 Run all candidate domains before cutting

Do not decide inclusion before seeing the curves.

Run the conservation-strength experiments for:

1. turbo-coded communication;
    
2. FAA visual acquisition;
    
3. Epic sepsis;
    
4. 3GPP / ECOA if controllable transformations exist.
    

Then cut.

Selection criterion:

> main-body legs must demonstrate the law, not merely match a regulator.

---

# 4. Workstream 3 — Choose the empirical spine

## 4.1 Candidate legs

|Leg|Provides|Immune to|Exposed to|Epistemic mode|
|---|---|---|---|---|
|Turbo-coded communication|Law in pure arithmetic; no institution|Recognizability, regulatory circularity, famous-case laundering|Artificiality|Gap measured directly|
|FAA ILS|Real-world safety boundary from geometry|Artificiality|Mild recognizability|Boundary recovered against external truth|
|Epic sepsis|Socio-technical register|Pure synthetic objection|High recognizability|Law witnessed under occlusion|
|3GPP|Standards breadth|Some regulatory breadth|Representation-relative hierarchy dependence|Audit confirmation|
|ECOA|Legal reason-traceability match|Shows chosen-system gap|Point comparison; hard to sweep|Audit confirmation|

## 4.2 Recommended main body

### Main spine: turbo + FAA

This is the strongest pair.

Turbo gives the law with nothing institutional draped over it.

FAA gives worldly force: a safety threshold recovered from geometry and ratified by real operations.

Together they close the major confound space.

A skeptic cannot say:

> It only works because the cases are famous.

Turbo refutes that.

A skeptic cannot say:

> It only works because the setting is synthetic.

FAA refutes that.

## 4.3 Epic as conditional third leg

Epic enters the main body only if its occlusion curve is clean.

It must show:

- monotone weakening under evidence hiding;
    
- predicted breakpoints;
    
- no recognizer-like flatline;
    
- no unexplained jumps;
    
- a clear socio-technical analogue of the physical conservation curve.
    

If Epic is clean, it gives the paper a third mode:

1. measured-in-vacuum;
    
2. recovered-against-world;
    
3. witnessed-under-occlusion in a social deployment.
    

If Epic is noisy, it goes to supplement.

A noisy third leg subtracts more than it adds.

## 4.4 3GPP and ECOA as supplement unless upgraded

3GPP is excellent for the audit paper. It is weaker for the conservation paper because the perturbation already shows representation-relative alignment.

Keep it as:

> supplementary confirmation that the same partition appears in communication standards, but that permission granularity co-determines the named threshold.

ECOA is excellent for reason traceability. But unless there is a meaningful occlusion or transformation sweep, it remains a point audit.

Keep it as:

> supplementary confirmation that the induced gap taxonomy recovers a legally mandatory evidence obligation.

Do not let breadth replace depth.

## 4.5 Depth-over-breadth rule

Four domains support “broadly applicable.”

One or two domains pushed to conservation strength support “fundamental.”

A law earns universality through the proof’s quantifiers, not by adding more anecdotes.

The main body should show the law where it is cleanest.

The supplement can show breadth.

---

# 5. Workstream 4 — New narrative spine

## 5.1 Paper architecture

Recommended structure if the conservation gates pass:

```text
1. Introduction
2. Results
3. The Conservation Law
4. Scope and Limits
Methods
Supplementary blind-audit protocol
Supplementary regulatory mappings
Appendices
```

Old Section 4, “Correctness of the blind-audit protocol,” moves to appendix or supplement.

But its core claim stays in the body:

> outputs were frozen before standards were opened, and every non-match was reported.

Do not bury non-circularity.

## 5.2 Introduction

The introduction should promise the law without discharging it.

Opening job:

- make the reader feel the phenomenon;
    
- show that evidence and authorization are different;
    
- suggest that the boundary moves lawfully;
    
- avoid front-loading machinery.
    

The intro should not open with a matrix. It should open with a jolt.

Candidate jolt:

> A 200 ft decision height is not only a regulatory threshold. In a standard instrument approach, it is the point where visual-acquisition geometry stops ruling out an unsafe manual landing.

Or:

> A bit error rate can look acceptable while the probability of a block error remains nearly one.

FAA is more legible. Turbo is cleaner. Choose after seeing the figures.

## 5.3 Results

Results must open on the jolt.

Not the matrix.

Not the theorem.

Not the compiler.

A possible order:

1. FAA or turbo jolt.
    
2. Boundary motion under evidence transformation.
    
3. Conservation curve.
    
4. Metric-invariance / admissible metrics.
    
5. Secondary real-world audit.
    
6. Partition matrix, compressed.
    
7. Socio-technical confirmation, if clean.
    

The matrix becomes comprehension, not astonishment.

## 5.4 The Conservation Law

This section is the payoff.

It should state the theorem in main-body language:

> Evidence does not license action by producing a favorable score. It licenses action by ruling out the failures that would make the action unsound. All states still compatible with the evidence form an evidence fiber. The authorization gap is the interval between the strongest permission safe for every state in that fiber and the strongest permission possible in some state in that fiber. Admissible transformations preserve this interval when they preserve the failure preorder. Evidence refinement shrinks it. Evidence hiding widens it. Exact recovery occurs when the interval collapses to a point.

Then give the theorem statements:

1. conservation / invariance theorem;
    
2. monotone refinement theorem;
    
3. metric-invariance theorem;
    
4. order-invariance theorem;
    
5. source-invariance theorem;
    
6. exact recovery as boundary case.
    

Machinery goes to appendix.

## 5.5 Scope and Limits

This section must be blunt.

State:

- the law is conditional on a supplied evidence representation;
    
- the law does not choose the permission hierarchy;
    
- real gaps can be placed at the wrong level;
    
- 3GPP shows representation-relative alignment;
    
- Amazon shows hierarchy-placement failure;
    
- outside-package obligations remain real;
    
- the selected domains are convergence evidence, not a sampling theorem.
    

This is not a caveat. It is the point.

The paper’s strongest claim is not:

> all regulation is forced.

It is:

> the evidence-forced component of authorization can be separated from representation choice, policy margin, and outside-package obligation.

That is the durable headline.

---

# 6. Confounds to name directly

## 6.1 Independent route vs shared corpus

Not all convergence has the same strength.

FAA is an independent route.

The compiler derives the boundary from optics. FAA arrives there through aviation safety practice.

FDA and ECOA are weaker as independence evidence because they likely respond to the same public failure corpus that helped induce the gaps.

Say this.

It does not sink the result. It bounds interpretation.

## 6.2 Recognizability

Famous cases can be recognized.

The old blind audit kills critique laundering:

> the compiler did not receive the paper’s critiques or verdicts.

It does not fully kill weak recognizability:

> the case itself may be recognizable from public discourse.

The occlusion sweep kills that weaker confound.

A recognizer would remain stable under evidence hiding. A compiler using evidence should move lawfully.

## 6.3 Representation choice

The theorem does not choose the evidence map.

It says what follows once the map is supplied.

3GPP is the exhibit. Under one frozen BER/BLER representation and hierarchy, the compiler aligns with 0.10 and 0.02. Under perturbation, those thresholds do not remain stable.

That is not failure.

It is the partition working.

## 6.4 Hierarchy placement

The theorem does not choose the permission hierarchy.

Amazon is the exhibit.

The taxonomy had the real gap: target-action specification. But the hierarchy placed induced gaps too high, so AEX remained reachable.

That is not missing evidence.

It is policy placement.

Say:

> A gap can be genuine and still be misplaced.

## 6.5 Source of gaps

The LLM or expert source can suggest gaps.

That source is not trusted for authorization.

The compiler trusts only the written evidence contract.

This is source-invariance.

---

# 7. The partition, stated once

The six correspondence classes should be defined once, sharply, then used.

## Representation-relative alignment

The compiler aligns with an external threshold under a frozen representation and hierarchy, but the alignment is not stable under admissible perturbation.

## Exact recovery

The evidence contains the relevant failure mode, and the external threshold names the same boundary the evidence forces.

## Same-axis policy margin

The compiler reaches an evidence boundary, and the external standard adds a stricter buffer on the same axis.

## Different evidence axis

The supplied evidence representation stops being the relevant representation. The external threshold depends on another kind of evidence.

## Finer evidence resolution

The compiler distinguishes a relation the external regime names more coarsely.

## Outside the supplied evidence package

The obligation is real, but the supplied package contains no gap that can speak to it.

Use these categories. Do not redefine them four times.

---

# 8. Figure plan

## Main-body figures if conservation paper passes

### Figure 1 — The jolt

Either:

- FAA geometric recovery of CAT I; or
    
- turbo BER/BLER gap.
    

Purpose:

> show the reader the phenomenon before naming the law.

### Figure 2 — Boundary motion under evidence hiding

Occlusion sweep.

Purpose:

> show that authorization weakens lawfully as evidence is hidden.

### Figure 3 — Permissivity vs divergence

Divergence curve across admissible metric or evidence-distance.

Purpose:

> show the quantitative relationship.

### Figure 4 — Metric / representation invariance

Same ordering and breakpoints under admissible metrics.

Purpose:

> show the ruler changes, not the authorization structure.

### Figure 5 — Real-world confirmation

FAA if not already Figure 1, or Epic if clean.

Purpose:

> show the law outside the synthetic setting.

### Figure 6 — Partition matrix

Compressed.

Purpose:

> show what the law explains across regulatory systems.

## Supplementary figures

- 3GPP perturbation audit.
    
- ECOA G7 reason traceability.
    
- FDA gap mapping.
    
- Full blind-audit protocol.
    
- Held-out Amazon / MCAS / COVID evaluation.
    
- Full world-realizability witnesses.
    
- Additional metrics.
    
- Alternative induction orders.
    

---

# 9. Abstract handshake

The title can be bold.

The first sentence must be exact.

Title:

> The Conservation of Incomplete Evidence

Opening sentence:

> The conserved object is the authorization-gap functional: the map from incomplete evidence to the interval of actions that remain unresolved by that evidence.

Then:

> We show that this functional is invariant under admissible evidence representations, monotone under evidence refinement and hiding, and independent of the order or source by which visible gaps are discovered. A compiler that reads only an evidence package and a permission hierarchy returns the lower endpoint of this interval: the strongest action sound for every world the evidence has not ruled out.

Then the empirical hook:

> In communication, aviation, medical AI, and consumer credit, the same law separates evidence-forced boundaries from policy margins, representation-relative alignments, different evidence axes, and obligations outside the supplied package.

Do not overstate:

Avoid:

> regulation is conserved.

Say:

> the evidence-grounded component of authorization is conserved across admissible representations.

---

# 10. Dependency order

## Step 1 — Name the invariant

Write the conserved-object sentence.

If it fails, stop.

## Step 2 — Fence [P]

State the admissible metric / representation class.

If it fails, stop.

## Step 3 — Run transformation sweeps

Run:

- occlusion;
    
- permissivity vs divergence;
    
- metric-invariance;
    
- projection fidelity if available.
    

If curves fail, stop.

## Step 4 — Choose body legs

Decide:

- turbo + FAA only;
    
- turbo + FAA + Epic;
    
- whether any audit leg has upgraded enough to remain in body.
    

## Step 5 — Rewrite narrative

Only after Steps 1–4.

Do not rewrite the whole paper before the law earns itself.

---

# 11. Explicit stop conditions

Stop the conservation rewrite and return to the audit paper if any of the following happen:

1. the conserved object cannot be named without metaphor;
    
2. the admissible metric class cannot be fenced;
    
3. “conservation” reduces only to vague continuity;
    
4. evidence hiding strengthens permission;
    
5. refinement weakens permission without explanation;
    
6. metric choice reverses authorization ordering inside the claimed admissible class;
    
7. breakpoints do not correspond to gap requirements;
    
8. Epic is noisy and the paper depends on Epic;
    
9. the body still needs all four domains to feel convincing;
    
10. the title says more than the theorem proves.
    

These are not failures of the project.

They mean the correct paper is the blind-audit paper.

---

# 12. Promote conditions

Promote to the conservation paper if all of the following hold:

1. the authorization-gap functional is named cleanly;
    
2. admissible transformations are fenced by [P];
    
3. hiding and refinement produce monotone controlled boundary motion;
    
4. divergence predicts the boundary breakpoints or landing regions;
    
5. metric changes preserve authorization ordering inside [P];
    
6. at least one physical leg demonstrates the law nakedly;
    
7. at least one real-world leg demonstrates the law independently;
    
8. socio-technical evidence either passes cleanly or is honestly supplementary;
    
9. the theorem states the claim in the body;
    
10. the appendix carries machinery, not meaning.
    

If those pass, the conservation version is the stronger paper.

---

# 13. Final positioning

The conservation paper should not say:

> We rediscovered regulation.

It should say:

> We identify the conserved authorization structure that regulation sometimes tracks.

It should not say:

> Every boundary is forced.

It should say:

> Once an evidence representation and permission hierarchy are supplied, the evidence-forced component of authorization is determined.

It should not say:

> The compiler replaces law or policy.

It should say:

> The compiler separates evidence from policy, representation, and silence.

The strongest final claim:

> Incomplete evidence has a conserved authorization structure. Refining the evidence shrinks the set of actions still unresolved; hiding evidence expands it; and admissible re-representations preserve the same underlying authorization gap. Regulatory thresholds are therefore neither arbitrary nor universally forced. They are partitions of this structure: some are evidence-forced, some representation-relative, some policy margins, some different-axis requirements, and some outside the supplied evidence entirely.

That is the paper.