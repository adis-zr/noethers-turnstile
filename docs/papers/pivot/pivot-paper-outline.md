# New paper outline: _The Conservation of Incomplete Evidence_

## Working title

**The Conservation of Incomplete Evidence**

Possible subtitle, if needed:

**A latent authorization law for approximate and consequential systems**

## Central claim

A finite permission hierarchy does not define authorization. It samples a deeper object: the latent authorization function (A(e)), the strongest action sound for every world still compatible with incomplete evidence (e).

As evidence is hidden, refined, projected, or re-represented, finite compiler outputs move according to this latent function. Under admissible transformations, coarsening can only weaken authorization; resolving refinement converges from below to (A(e)). The limiting function may be smooth, stepped, or kinked depending on the underlying evidence geometry.

## One-sentence thesis

Incomplete evidence has a conserved authorization structure: finite permission systems observe it as staircases, but densification reveals the latent function those staircases approximate.

---

# 1. Introduction

## Job of the section

Move the reader from “authorization thresholds are chosen” to “authorization thresholds are samples of a latent evidence-governed function.”

## Opening move

Start with a concrete jolt, not the matrix.

Best candidate:

- FAA ILS: a regulatory threshold appears as a geometric boundary.
    
- The visual-acquisition curve recovers CAT I and then saturates at the CAT II transition.
    
- This gives the reader a real-world kink before they know the theorem.
    

Alternative opening:

- Turbo: BER looks safe while BLER still refuses action.
    
- Cleaner mathematically, less worldly.
    

Recommended: **open with FAA**, then use turbo as the naked mathematical version.

## Paragraph 1 — The phenomenon

- Consequential systems act under incomplete evidence.
    
- The question is not whether evidence is favorable.
    
- The question is what action remains sound for every world the evidence has not ruled out.
    
- Regulatory thresholds often appear as discrete categories, but the evidence underneath may vary continuously.
    

## Paragraph 2 — The old view is too coarse

- Existing authorization regimes use finite permission alphabets: display, review, experiment, limited rollout, autonomous action.
    
- Turnstile also begins with such a finite hierarchy.
    
- But these levels are not the ontology.
    
- They are a measurement grid over a deeper authorization object.
    

## Paragraph 3 — The latent object

- Introduce (A(e)) in prose.
    
- (A(e)) is the strongest action sound for all worlds compatible with evidence (e).
    
- A finite compiler returns a lower quantization of (A(e)), not (A(e)) itself.
    
- Refining the permission hierarchy should reveal the shape of (A(e)).
    

## Paragraph 4 — The conservation claim

- Coarsening evidence should not create stronger permission.
    
- Refining evidence should not weaken authorization unless the representation changed the problem.
    
- Under authorization-admissible transformations, the latent authorization structure is preserved.
    
- The one-line fence: admissible coarsening satisfies (A_{\pi}(\pi(e)) \le A(e)).
    

## Paragraph 5 — What the experiments show

Preview the three empirical regimes:

- Turbo: smooth monotone governing function; coarse staircases are quantization artifacts.
    
- Ising: genuine step; densification tracks a fixed threshold with error bounded by grid spacing.
    
- FAA: smooth geometry plus structural kink where the evidence axis saturates.
    
- Epic / socio-technical occlusion: permission descends at theory-predicted blockers.
    
- Projection collapse: a natural-looking coarsening violates admissibility and produces spurious authorization.
    

## Paragraph 6 — What this is not

- Not compliance review.
    
- Not a claim that all regulation is forced.
    
- Not a claim that the compiler chooses the right evidence map or permission hierarchy.
    
- The law is conditional: once evidence representation and permission hierarchy are supplied, the evidence-forced component is determined.
    

## Paragraph 7 — Contributions

Bullet these in prose:

- define the latent authorization function;
    
- prove conservative coarsening and resolving-refinement convergence;
    
- show finite permission hierarchies approximate (A(e));
    
- empirically distinguish quantization artifacts from genuine structural features;
    
- identify the admissibility boundary where projection destroys authorization structure;
    
- show regulatory thresholds as samples, margins, or failures of this structure.
    

---

# 2. Results

## Section opening

Do not open with the old correspondence matrix.

Open with the main empirical discovery:

> Densifying permission levels reveals the latent authorization function.

The Results should be organized by what each experiment teaches about the governing function.

---

## 2.1 Finite permission levels sample a latent authorization function

## Purpose

Establish the central empirical frame before domain details.

## Include

- Define the densification experiment:
    
    - fixed evidence path;
        
    - permission grids (P_4, P_8, P_{16}, \ldots, P_{256});
        
    - compiler output (C_k(e) = \lfloor A(e) \rfloor_{P_k});
        
    - compare how staircases change as (k) increases.
        

## Claim

- If the staircase is a quantization artifact, breakpoints grow with grid resolution.
    
- If the staircase reflects a real structural threshold, breakpoint count stabilizes and location error shrinks with grid spacing.
    
- If the evidence axis changes, a kink persists under refinement.
    

## Figure

**Figure 1. Permission densification schematic.**

Panels:

- coarse staircase;
    
- refined staircase;
    
- latent smooth / step / kink function.
    

---

## 2.2 Turbo-coded communication: the smooth control

## Purpose

Show the cleanest continuous case and the authorization gap.

## Include

- BER is mean-like evidence.
    
- BLER is action-relevant worst-case/block failure evidence.
    
- BER can authorize before BLER does.
    
- The authorization gap spans the SNR interval where mean-like evidence over-authorizes.
    
- Permission densification does not reveal internal structure beyond the monotone BLER curve.
    
- Breakpoints scale with (k) and SNR resolution.
    
- Therefore, the staircase is entirely a measurement-grid artifact.
    

## What to emphasize

Turbo is not the best densification story anymore.

It is the best **negative control**:

- smooth function;
    
- no hidden kink;
    
- no false structural feature;
    
- breakpoints grow because thresholds cross a monotone curve.
    

## Figure

**Figure 2A. Turbo authorization gap and densification control.**

Panels:

- BER vs BLER over SNR;
    
- gap region where BER authorizes and BLER refuses;
    
- breakpoint count vs permission grid / SNR resolution.
    

## Main sentence

> Turbo shows the law without institutional structure: the compiler samples a smooth monotone failure function, and finite staircases disappear as artifacts of the measurement grid.

---

## 2.3 Ising inference: a genuine structural step

## Purpose

Show that not every staircase hides a smooth curve.

## Include

- Mean total variation error and max total variation error diverge.
    
- The authorization-relevant function is max TV.
    
- Densification produces exactly one breakpoint at every (k).
    
- The breakpoint tracks (TV_{\max} = 0.3338).
    
- Location error is always bounded by one grid spacing.
    
- Since spacing goes to zero, the breakpoint converges to the true threshold.
    
- Intermittent halving is expected behavior of a uniform grid approaching a fixed non-grid-aligned target.
    

## What to emphasize

This is the discriminator proving the method is not hallucinating smoothness.

Turbo says: staircase can be artifact.

Ising says: staircase can be real.

The method distinguishes them.

## Figure

**Figure 2B. Ising structural threshold.**

Panels:

- mean TV vs max TV;
    
- permission outputs under (P_4, P_8, \ldots, P_{256});
    
- location error vs grid spacing;
    
- breakpoint count constant at 1.
    

## Main sentence

> Ising shows the opposite of turbo: densification does not smooth the staircase away, because the staircase is the function.

---

## 2.4 FAA visual acquisition: a smooth function with a structural kink

## Purpose

Show the hybrid case in real-world geometry.

## Include

- The evidence axis is visual acquisition geometry.
    
- The compiler derives the CAT I decision-height / visual-range relation.
    
- The curve is smooth until the roll-bar visibility geometry saturates near 102 ft decision height.
    
- Below saturation, visual evidence no longer determines the authorization question.
    
- Densification stabilizes at the structural kink.
    
- Additional permission levels fall into the flat post-saturation region and add no information.
    

## What to emphasize

FAA is the real-world anchor.

It shows:

- smooth quantitative geometry;
    
- exact recovery of a real safety threshold;
    
- persistent kink where the active evidence axis changes;
    
- why CAT II is not merely a stricter version of CAT I.
    

## Figure

**Figure 2C. FAA kink and evidence-axis transition.**

Panels:

- visual acquisition curve;
    
- CAT I recovery;
    
- kink/saturation at ~102 ft;
    
- densification breakpoint stabilization.
    

## Main sentence

> FAA shows that the latent authorization function can be smooth until the evidence itself stops speaking.

---

## 2.5 Densification classifies authorization geometry

## Purpose

Synthesize turbo, Ising, and FAA.

## Include table

|Domain|Densification signature|Latent regularity|
|---|---|---|
|Turbo|Breakpoints grow with grid and SNR resolution|Smooth monotone function|
|Ising|One breakpoint at all (k), spacing-bounded location error|Genuine step|
|FAA|Breakpoints stabilize at kink|Piecewise smooth with evidence-axis transition|

## Claim

- The experiment is not just producing prettier curves.
    
- It is a diagnostic:
    
    - growing breakpoints = quantization artifact;
        
    - stable count + spacing-bounded tracking = real threshold;
        
    - stabilized kink = structural evidence-axis transition.
        

## Main sentence

> Permission densification reveals whether a finite authorization staircase is an artifact, a true threshold, or a kink in the evidence geometry.

---

## 2.6 Occlusion sweeps show conservative boundary motion

## Purpose

Show the law under evidence hiding.

## Include

### ILS occlusion

- Staircase: ALR → REV → DIA → REF.
    
- Each drop occurs exactly when evidence required for that permission is hidden.
    
- No reversals.
    

### Epic occlusion

- Staircase: ALR → AEX → REV → DIA.
    
- Opening G1 drops ALR → AEX.
    
- G2–G7 do not drop further because they gate ALR while AEX is already reached.
    
- Opening S2 drops AEX → REV.
    
- Opening S1 drops REV → DIA.
    
- Breakpoints match the hierarchy.
    

## What to emphasize

This is not smoothness.

This is conservative motion under evidence hiding:

- hide evidence;
    
- authorization weakens or stays fixed;
    
- active blocker explains each transition.
    

## Figure

**Figure 3. Evidence hiding produces theory-predicted permission descent.**

Panels:

- ILS occlusion staircase;
    
- Epic occlusion staircase;
    
- active blocker annotations.
    

## Main sentence

> Evidence hiding moves authorization downward exactly at the gaps required by each permission level.

---

## 2.7 Projection fidelity exposes the admissibility boundary

## Purpose

Introduce [P] empirically before proving it.

## Include

- Projection levels 0–4:
    
    - coarsening widens the gap;
        
    - authorization weakens or stays fixed;
        
    - no spurious strengthening.
        
- Level 5:
    
    - merging S1 and S2 into a two-gap representation collapses the skeleton;
        
    - AEX becomes reachable by accident;
        
    - gap width bounces from 1 back to 0;
        
    - this is not genuine evidence closure.
        
- The failure is structural collapse.
    

## Core interpretation

Level 5 is not a bad data point.

It is the witness that [P] is non-vacuous.

A natural-looking simplification falls outside the admissible class because it creates spurious authorization.

## Figure

**Figure 4. Admissible coarsening and structural collapse.**

Panels:

- permission vs projection level;
    
- gap width vs projection level;
    
- Level 5 highlighted as violation;
    
- schematic showing skeleton gap merged away.
    

## Main sentence

> Coarsening is admissible only while it remains conservative; once projection erases the permission skeleton, the compiler can authorize by representation rather than evidence.

---

## 2.8 Regulatory thresholds are samples, margins, or silences of the same structure

## Purpose

Bring back the old audit results in compressed form.

## Include

- The old correspondence matrix, but smaller.
    
- Use it after the reader already understands (A(e)).
    
- Regulatory thresholds are no longer the main event.
    
- They are external samples of the authorization structure.
    

## Correspondence classes

Define once:

- exact recovery;
    
- representation-relative alignment;
    
- same-axis policy margin;
    
- different evidence axis;
    
- finer evidence resolution;
    
- outside supplied package.
    

## Include core examples

- FAA CAT I: exact recovery.
    
- 3GPP 0.10 / 0.02: representation-relative alignment.
    
- FDA gaps: evidence obligations recovered from deployment failures.
    
- ECOA G7: exact reason-traceability recovery.
    
- CAT II / CAT III: different axis / outside package.
    
- Amazon held-out: hierarchy-placement failure.
    

## Figure

**Figure 5. Regulatory correspondence as partition of the latent authorization structure.**

Keep this figure compact. Do not make it the lead figure.

## Main sentence

> Regulation does not define the law; it samples, margins, coarsens, or exceeds the evidence-grounded authorization structure.

---

# 3. The Conservation Law

## Job of the section

Discharge the theory after the reader has already seen the phenomenon.

No heavy machinery in the first page.

State the theorem clearly in words, then formalize.

---

## 3.1 The latent authorization function

## Define

- (W): possible worlds / system states.
    
- (E): evidence states.
    
- (q: W \to E): evidence map.
    
- (F(e)): fiber of worlds compatible with evidence (e).
    
- (A^*(w)): true strongest sound action in world (w).
    
- (A(e)): strongest action sound for every world in (F(e)).
    

## Main equation

[  
A(e) = \inf_{w \in F(e)} A^*(w)  
]

or meet over compatible worlds.

## Prose

- The function is conservative by construction.
    
- It returns what is sound for all worlds not ruled out by evidence.
    
- It is the object finite permission compilers approximate.
    

---

## 3.2 Finite permission hierarchies are lower approximations

## Define

- (P_k): finite permission grid.
    
- (C_k(e)): compiler output under (P_k).
    

## Claim

[  
C_k(e) = \lfloor A(e) \rfloor_{P_k}  
]

## Include

- This explains staircases.
    
- Coarse permissions produce coarse staircases.
    
- Densification refines the approximation.
    
- The staircase is the instrument, not necessarily the object.
    

---

## 3.3 Authorization-admissible coarsening

## State [P]

A projection (\pi) is authorization-admissible iff:

[  
A_{\pi}(\pi(e)) \leq A(e)  
]

for all evidence states (e).

## Explain

- Coarsening may hide evidence.
    
- Hiding evidence may weaken authorization.
    
- It may not create stronger authorization.
    
- This is conservatism under coarsening.
    

## Include Level 5 as witness

- The Level 5 projection violates this.
    
- It is natural-looking, not pathological.
    
- It merges the structural skeleton and creates spurious AEX.
    
- Therefore [P] is non-vacuous.
    

## Important distinction

Conservatism is not enough for convergence.

A projection that maps everything to REFUSE is conservative but useless.

Therefore the next theorem needs resolving refinement.

---

## 3.4 Resolving refinement and convergence

## Define

A sequence (\pi_k) is resolving if, for every permission-relevant distinction active at (e), there exists (k_0) such that all (k \geq k_0) preserve that distinction.

## Theorem

If (\pi_k) is authorization-admissible and resolving, then:

[  
A_{\pi_k}(\pi_k(e)) \uparrow A(e)  
]

from below.

With finite permission grids:

[  
C_k(e) = \lfloor A_{\pi_k}(\pi_k(e)) \rfloor_{P_k}  
]

## Explain

- Conservative coarsening gives safety.
    
- Resolving refinement gives convergence.
    
- Together they define admissible representation change.
    

---

## 3.5 Regularity classes of (A(e))

## State

The latent authorization function need not be globally smooth.

It may be:

- smooth on quantitative evidence regions;
    
- stepped at genuine structural thresholds;
    
- kinked when the active evidence axis changes;
    
- discontinuous where a categorical obligation is absent.
    

## Tie to data

- Turbo: smooth.
    
- Ising: step.
    
- FAA: kink.
    
- Socio-technical reason traceability: likely structural gate.
    

## Main sentence

> Smoothness is not the law. Conservation is the preservation of the authorization structure under admissible transformations.

---

## 3.6 Exact recovery as the zero-gap boundary case

## Collapse old representation theorem here

## State

If (A^*(w)) is constant over the evidence fiber (F(e)), then the gap collapses:

[  
\inf_{w \in F(e)} A^_(w) = \sup_{w \in F(e)} A^_(w)  
]

The compiler recovers the unique correct boundary.

If (A^*) is non-constant on the fiber, no compiler reading only (e) can recover the distinction.

## Use

- FAA CAT I: zero-gap / exact recovery on supplied axis.
    
- 3GPP: not zero-gap under hierarchy perturbation.
    
- CAT II: different axis.
    
- Amazon: hierarchy placement, not missing gap.
    

---

## 3.7 Order- and source-invariance

## Order-invariance

- If failures are visible and policy cares about them, induction order does not change the final gap set.
    
- The loop is a discovery procedure over a fixed closure.
    

## Source-invariance

- The source of a candidate gap does not determine authorization soundness.
    
- Expert, LLM, regulator, incident report: all are proposal mechanisms.
    
- The compiler is the type checker.
    
- Soundness comes from the evidence contract and gap checks, not from trusting the source.
    

## Keep concise

These are corollaries, not the center of the paper.

---

# 4. Scope and limits

## Job of the section

Protect the claim by stating exactly where it stops.

## 4.1 The law does not choose the evidence map

- (A(e)) is defined after an evidence representation is supplied.
    
- Bad representations can erase relevant failures.
    
- Level 5 shows this directly.
    

## 4.2 The law does not choose the permission hierarchy

- A real gap can be placed too high or too low.
    
- Amazon recruiting is the example.
    
- G2 was real, but the hierarchy allowed AEX despite G2 being open.
    
- This is hierarchy-placement failure, not missing evidence.
    

## 4.3 Not all regulatory matches have equal independence

- FAA is an independent-route convergence.
    
- FDA / ECOA are partially shared-corpus convergence.
    
- This does not invalidate them.
    
- It bounds the epistemic claim.
    

## 4.4 3GPP remains representation-relative

- The 0.10 and 0.02 alignments are blind under frozen hierarchy.
    
- Perturbation shows they are not hierarchy-independent ridges.
    
- This is not a failure.
    
- It is an example of representation-relative alignment.
    

## 4.5 Outside-package obligations remain real

- Cybersecurity, UI/labeling, disparate impact, upstream data accuracy may be real.
    
- The compiler is silent when the supplied package has no gap that can speak to them.
    
- Silence is a result, not permission.
    

## 4.6 The compiler does not replace judgment

- It does not choose institutional risk tolerance.
    
- It does not decide law.
    
- It separates what evidence forces from what policy adds.
    

## Final paragraph

Return to the main claim:

> Incomplete evidence conserves authorization structure only inside admissible representations. The contribution is not that all boundaries are forced, but that the evidence-forced component can be identified, approximated, refined, and separated from policy and representation choice.

---

# Methods

## M1 Compiler

- Inputs:
    
    - evidence package;
        
    - gap statuses;
        
    - permission hierarchy;
        
    - gap requirements per permission.
        
- Output:
    
    - strongest sound permission;
        
    - certificate;
        
    - active blocker.
        

## M2 Permission densification

- Define (P_k).
    
- Explain how permission thresholds are generated.
    
- Explain how (C_k(e)) is computed.
    
- Explain breakpoint count, location error, and grid spacing.
    

## M3 Turbo experiment

- BER / BLER data.
    
- SNR path.
    
- Permission thresholds.
    
- SNR-resolution check.
    
- Why turbo is a smooth control.
    

## M4 Ising experiment

- Grid, coupling, loopy BP, exact marginals.
    
- Mean TV and max TV.
    
- Threshold tracking.
    
- Location error ≤ grid spacing.
    

## M5 FAA experiment

- Glide slope.
    
- Decision height.
    
- RVR.
    
- Approach lighting geometry.
    
- Saturation at ~102 ft.
    
- Densification breakpoint stabilization.
    

## M6 Occlusion sweeps

- ILS gap hiding.
    
- Epic gap hiding.
    
- Permission requirements.
    
- Active blocker logging.
    

## M7 Projection fidelity

- Projection levels 0–5.
    
- Conservative composite gap semantics.
    
- Level 5 skeleton collapse.
    
- Test of (A_{\pi}(\pi(e)) \leq A(e)).
    

## M8 Blind audit protocol

- Freeze inputs.
    
- Run compiler.
    
- Open documents.
    
- Classify correspondence.
    
- No target leakage.
    

---

# Supplementary material

## S1 Full regulatory correspondence matrix

- 3GPP.
    
- FAA.
    
- FDA.
    
- ECOA.
    
- Held-out cases.
    

## S2 3GPP perturbation

- 59 hierarchies.
    
- 0.10 and 0.02 recovery rates.
    
- Representation-relative demotion.
    

## S3 FDA and ECOA mappings

- Locked gaps.
    
- FDA guidance elements.
    
- ECOA / Regulation B / CFPB reason traceability.
    
- Outside-package axes.
    

## S4 World-realizability witnesses

- G1–G7.
    
- Token vs world-fact separation.
    
- Documentation requirement exclusion.
    

## S5 Proofs

- Latent authorization function.
    
- Conservative coarsening.
    
- Resolving refinement convergence.
    
- Exact recovery boundary case.
    
- Order-invariance.
    
- Source-invariance.
    

## S6 Additional figures

- Full occlusion traces.
    
- All (k)-level densification outputs.
    
- Alternative metric checks.
    
- Projection-fidelity matrix.
    
- Negative controls.
    

---

# Recommended figure order

## Figure 1 — The latent authorization function

A conceptual figure showing:

- evidence path;
    
- finite permission staircase;
    
- densified approximation;
    
- latent function.
    

Purpose: introduce the object.

## Figure 2 — Three regularity classes under densification

Three panels:

- Turbo: smooth monotone control.
    
- Ising: genuine step.
    
- FAA: kink / evidence-axis transition.
    

Purpose: main empirical result.

## Figure 3 — Evidence hiding produces conservative descent

ILS and Epic occlusion staircases.

Purpose: show boundary motion under missing evidence.

## Figure 4 — Projection admissibility and Level 5 failure

Levels 0–5, with Level 5 highlighted.

Purpose: show [P] is non-vacuous.

## Figure 5 — Regulatory partition

Compressed matrix.

Purpose: connect law to regulation after the law is established.

## Figure 6 — The conservation law

Optional if needed:

- evidence fibers;
    
- meet/lower endpoint;
    
- coarsening;
    
- resolving refinement.
    

Purpose: make theorem visually legible.

---

# What moves out of the old draft

## Move to supplement

- Full blind-audit protocol.
    
- Full 3GPP discussion.
    
- Full FDA/ECOA mapping.
    
- Full held-out socio-technical evaluation.
    
- Full proof machinery.
    

## Keep in body, compressed

- Non-circularity claim.
    
- Regulatory partition classes.
    
- FAA CAT I recovery.
    
- 3GPP representation-relative demotion.
    
- FDA/ECOA as corroborating audit.
    
- Amazon as hierarchy-placement limit.
    

## Remove or rewrite

- Repeated definitions of the six correspondence types.
    
- Repeated “one object” explanations.
    
- Any claim that sounds like all regulation is forced.
    
- Any claim that the compiler chooses the right evidence map.
    
- Any claim that “smoothness” is universal.
    

---

# Best one-paragraph paper shape

This paper identifies a latent authorization function (A(e)): the strongest action sound for every world compatible with incomplete evidence. Finite permission hierarchies do not define this function; they sample it. Across communication, inference, aviation, and medical deployment, permission densification reveals three regularity classes of the same object: smooth monotone functions, genuine structural steps, and kinks where the active evidence axis changes. Evidence hiding moves authorization downward at theory-predicted blockers, while admissible coarsening is exactly conservative coarsening: (A_{\pi}(\pi(e)) \leq A(e)). A natural-looking projection that violates this condition produces spurious authorization, showing that the admissibility fence is non-vacuous. Regulatory thresholds then appear not as the source of the law but as samples, margins, coarsenings, or silences of the evidence-grounded authorization structure.