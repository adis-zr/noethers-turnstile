# The Conservation of Incomplete Evidence

## An authorization calculus for approximate and consequential systems

**Authors:** Aditya Sriram
**Affiliations:** Independent Researcher

---

## Abstract

Approximate systems increasingly authorize consequential action: clinical alerts, credit denials, automated holds, ranking decisions, routing policies and other interventions whose costs are borne outside the model. Yet the theory of approximate systems mostly asks how well a model predicts, not what its evidence is allowed to authorize. We introduce a latent authorization calculus for incomplete evidence. Given a space of possible worlds, an evidence map and an ordered permission scale, the strongest action supported by an evidence state is the meet of the world-level authorizations over all worlds still compatible with that evidence. This latent authorization function is not an average, threshold convention or regulatory label; it is the worst-case permission forced by the unresolved evidence fiber. We prove that finite permission hierarchies approximate this object from below, that admissible evidence coarsenings may weaken but not create authorization, and that resolving refinements across both evidence and permission axes converge to the same latent object. We implement the calculus as a deterministic compiler and test it across communication, probabilistic inference, aviation geometry and medical-AI authorization examples. Permission densification separates smooth quantization artifacts, genuine thresholds and evidence-axis transitions. Evidence hiding produces conservative permission descent. Projection experiments identify the admissibility boundary, including a compact representation that spuriously restores permission by erasing the permission skeleton. A two-axis refinement experiment closes the loop by showing joint convergence from below, while a non-resolving path loses monotonicity exactly where the theory predicts. External standards in aviation, communications, medicine and credit are then evaluated as correspondence audits, not as primary validation. The result is a computational separation between what evidence forces, what representation preserves, and what policy adds.

---

## 1. Introduction

Approximate systems increasingly gate consequential action. A sepsis model decides which patients trigger a clinical alert. A risk score informs pretrial detention. A care-management algorithm allocates services across a population. A predictive-policing system directs patrols. A resume screener forwards or discards a candidate. In each case, a system that is only approximately correct is granted authority to act, and the action carries costs that the model itself does not bear.

When these systems fail in ways that reach public record, the failure is often not a modeling error in the ordinary sense. The Optum population-health algorithm predicted health-care cost accurately; cost was the wrong proxy for need. The Amazon recruiting screener learned its training signal faithfully; the signal encoded historical hiring decisions rather than qualification. The Epic sepsis model carried real predictive signal; that signal did not establish benefit at the deployed intervention threshold. The recurring fault is not that the statistic was false. It is that a true statistic was allowed to authorize an action it did not support.

This is an authorization error. It is distinct from, and largely orthogonal to, predictive accuracy.

The asymmetry in the theory is striking. We have mature tools for asking how well a model predicts: calibration, generalization, error bounds, uncertainty quantification, robustness analysis and distribution-shift detection. We have much weaker tools for asking when a prediction licenses an action. In practice, the licensing step is often supplied by convention. A threshold is chosen, a population average is compared against a cutoff, a regulatory category is matched, or a review board signs off. These devices answer a question they rarely state:

> Given everything this evidence does and does not reveal, what is the strongest action it can soundly support?

This paper gives a formal answer to that question, conditional on the evidence representation, permission order and world-level soundness semantics supplied by the domain.

The answer is not an average. It is a meet.

Fix an evidence state. Many distinct worlds remain compatible with it. Some of those worlds may support strong action; others may not. The authorization forced by the evidence is the strongest permission sound in every compatible world. We call this object the latent authorization function, (A(e)). It is the meet of world-level authorizations over the evidence fiber. It exists whether or not any deployed system computes it.

This distinction matters. A population-average statistic may support an action for the average member of a group while failing for compatible individuals hidden inside the same evidence fiber. A block-level communication failure probability may be unacceptable even when a bit-level error statistic appears safe. A model may have sufficient retrospective discrimination but insufficient clinical-utility evidence at the deployed intervention threshold. In all of these cases, the evidence does not fail because it is empty. It fails because the action it was allowed to authorize is stronger than the weakest compatible world permits.

The contribution of this paper is an authorization calculus for this setting. We make four claims.

First, incomplete evidence induces a canonical lower endpoint once the evidence map, permission order and world-level soundness relation are supplied. This endpoint is (A(e)), the strongest permission sound for all worlds compatible with evidence (e).

Second, finite permission hierarchies can only approximate this endpoint from below. A finite compiler may be conservative, and it may sharpen as the permission scale is refined, but it cannot soundly exceed (A(e)).

Third, evidence representations can be changed only under an admissibility constraint. Coarsening may hide distinctions and weaken authorization. It may not manufacture permission unsupported by the finer evidence.

Fourth, resolving refinement of both axes — evidence representation and permission scale — converges to the same latent authorization object. This is the conservation law of the title. Authorization may be weakened, refined or relabelled under admissible transformations. It may not be created by representation.

We implement this calculus as a compiler. The compiler takes an evidence package, a finite permission hierarchy and a requirement map, then returns the strongest permission whose requirements are satisfied. It is a type checker for authorization rather than a predictive model.

We test the calculus in three ways.

First, we hold evidence fixed and refine permission scales. Across communication, inference and aviation-geometry examples, densification distinguishes three regularity classes: smooth quantization artifacts, genuine structural thresholds and evidence-axis transitions.

Second, we hold the permission scale fixed and alter evidence representation. Evidence hiding produces conservative permission descent. Projection fidelity exposes the admissibility boundary: a compact representation can look natural while erasing the permission skeleton and spuriously restoring authorization.

Third, we move both axes simultaneously. A two-axis refinement experiment on a medical-AI authorization hierarchy shows convergence from below along a resolving path. A path that passes through an inadmissible projection loses monotonicity exactly at the non-resolving step, then converges again once it enters a resolving tail.

Finally, we compare the same object against external standards in aviation, communications, medicine and credit. These comparisons are not treated as uniform validation. They are correspondence audits with different independence profiles: exact recovery in one supplied legal representation, independent-route same-axis convergence in one geometry case, representation-relative alignment in communications, shared-corpus correspondence in medical-AI guidance, and outside-package silence where the supplied evidence map cannot speak.

The result is a separation that the failure cases lacked: what evidence forces, what representation preserves, and what policy adds.

---

## 2. Results

### 2.1 Overview of the claim architecture

The paper has one conserved object and two finite approximation axes.

The conserved object is the latent authorization function (A(e)): the strongest permission sound in every world still compatible with evidence state (e). The first approximation axis is permission resolution. A finite permission hierarchy reads (A(e)) as a staircase approximation from below. The second approximation axis is evidence representation. A coarser evidence vocabulary enlarges evidence fibers and may weaken authorization, but an admissible coarsening cannot strengthen it.

The experiments are organized around this architecture rather than around domain frequency. The goal is not to estimate how often an authorization error occurs in a population of systems. The goal is to test whether the compiler behaves according to the predicted geometry under controlled transformations.

Table 1 records the status of the major claims.

|Claim|Status in this paper|
|---|---|
|(A(e)) is the strongest permission sound over all worlds compatible with evidence (e)|Definition and theorem consequence|
|Finite permission grids approximate (A(e)) from below|Theorem|
|Nested grid refinement sharpens authorization monotonically|Theorem|
|Admissible evidence coarsening cannot create permission|Theorem|
|Resolving evidence refinement recovers (A(e)) semantically|Theorem|
|Joint evidence and permission refinement converges to (A(e)) from below|Theorem and implemented demonstration|
|Densification separates smooth artifacts, structural steps and evidence-axis transitions|Controlled computational demonstration|
|Evidence hiding causes conservative permission descent|Implemented hierarchy demonstration|
|Projection collapse can spuriously restore authorization|Implemented non-vacuity witness|
|Regulatory thresholds instantiate the same latent structure|Correspondence audit, not primary theorem|
|The calculus chooses the correct evidence map or permission hierarchy|Not claimed|

The domains are also assigned distinct evidentiary roles.

|Domain|Role in the paper|What it supports|
|---|---|---|
|Turbo-coded communication|Smooth negative control|Permission densification can subdivide a smooth monotone curve without revealing structural thresholds|
|Ising belief propagation|Structural-step example|A genuine authorization threshold remains pinned under densification|
|FAA CAT I geometry|Evidence-axis transition and independent-route correspondence|A supplied geometric evidence axis can saturate; a frozen geometric floor lands near an external standard|
|ILS occlusion|Physical hierarchy demonstration|Hiding required evidence weakens permission in the predicted order|
|Epic medical-AI hierarchy|Socio-technical hierarchy demonstration|Gap opening, projection fidelity and joint refinement can be compiled deterministically|
|3GPP BLER thresholds|Representation-relative correspondence|Alignment depends on the supplied hierarchy and does not persist under perturbation|
|ECOA reason traceability|Supplied-representation exact recovery|A legal reason-giving requirement matches a zero-gap authorization boundary|
|FDA AI/ML guidance|Shared-corpus correspondence|Regulatory categories align with gaps induced from documented deployment failures|
|Amazon recruiting|Held-out hierarchy-placement failure|A real gap can be present but placed at the wrong permission level|

This claim ledger is deliberately conservative. The paper’s central contribution is the calculus and its compiler behavior under representation and permission changes. The regulatory section is an external audit of correspondence, not the foundation of the theory.

---

### 2.2 The latent authorization function

Let (W) be the set of possible worlds. A world contains all facts relevant to authorization: the actual channel behavior, true approximation errors, deployment setting, oversight structure, reason trace, patient impact, available rollback mechanism or any other fact that could make an action sound or unsound.

Let (E) be a space of evidence states, and let

[  
q: W \to E  
]

be the evidence map. The evidence map records only what the evidence package can observe.

For an evidence state (e \in E), define the evidence fiber

[  
F(e)={w\in W:q(w)=e}.  
]

This is the set of worlds still compatible with the evidence.

Let (\mathcal A) be a permission lattice ordered from weaker to stronger permissions. We write

[  
p \preceq r  
]

to mean that permission (p) is no stronger than permission (r). In the implemented examples,

[  
\mathrm{REF} \preceq \mathrm{DIA} \preceq \mathrm{REV} \preceq \mathrm{AEX} \preceq \mathrm{ALR}.  
]

Here REF denotes refusal or no authorization; DIA denotes diagnostic display; REV denotes human review; AEX denotes bounded assisted execution; and ALR denotes autonomous or limited release under the strongest supplied requirements.

Let

[  
a:W\to \mathcal A  
]

be the world-level authorization function, where (a(w)) is the strongest action sound in world (w).

The latent authorization function induced by evidence map (q) is

[  
A(e)=\bigwedge_{w\in F(e)} a(w).  
]

Thus (A(e)) is the strongest permission sound for every world still compatible with (e). A permission (p) is sound given evidence (e) exactly when

[  
p\preceq A(e).  
]

The associated upper endpoint is

[  
B(e)=\bigvee_{w\in F(e)} a(w),  
]

the strongest permission consistent with at least one world compatible with (e). The interval

[  
[A(e),B(e)]  
]

is the authorization gap. The lower endpoint is what is sound for every compatible world. The upper endpoint is what remains possible in some compatible world. A sound compiler must return the lower endpoint or a lower approximation to it.

This definition is the central object of the paper. Authorization is not attached to an evidence state by averaging, voting or matching a regulatory label. It is the meet of the world-level authorizations over the worlds the evidence has not ruled out.

---

### 2.3 Finite permission levels sample the latent function from below

A finite compiler does not observe (A(e)) directly. It observes it through a finite permission grid.

Let

[  
P_k={p_1\prec p_2\prec \cdots \prec p_k}\subseteq \mathcal A  
]

be a finite permission grid. Define the floor of (x\in\mathcal A) with respect to (P_k) as

[  
\lfloor x \rfloor_{P_k}=  
\max{p\in P_k:p\preceq x},  
]

with the bottom permission returned if the set is empty. The compiler output under grid (P_k) is

[  
C_k(e)=\lfloor A(e)\rfloor_{P_k}.  
]

For every evidence state (e), (C_k(e)\preceq A(e)). If (P_k\subseteq P_{k+1}), then

[  
C_k(e)\preceq C_{k+1}(e)\preceq A(e).  
]

If the grid sequence resolves (\mathcal A) from below, then

[  
C_k(e)\nearrow A(e).  
]

This theorem is elementary, but its interpretation is important. A finite staircase is not the ontology. It is the finite-grid observation of the latent authorization value.

The densification experiments test what the staircase does as the permission grid is refined. Three signatures are predicted.

1. **Smooth artifact:** breakpoint count grows with grid granularity and path resolution. The staircase is subdividing a smooth curve.
    
2. **Genuine threshold:** breakpoint count is constant across grid refinements; location error is bounded by one grid spacing and converges to zero.
    
3. **Evidence-axis transition:** breakpoint count grows until a structural feature is resolved, then stabilizes or changes regime.
    

These signatures are evaluated in three domains.

---

### 2.4 Turbo-coded communication is a smooth negative control

Turbo codes transmit data over a noisy channel. Two error statistics are relevant: bit error rate (BER), which averages errors over bits, and block error rate (BLER), which flags a block as failed if any bit fails. BER and BLER can diverge sharply. A bit-level statistic can appear acceptable while the corresponding block-level failure probability remains too high.

We use a four-level hierarchy,

[  
\mathrm{REFUSE}/\mathrm{HOLD}/\mathrm{TRANSMIT_MONITORED}/\mathrm{TRANSMIT},  
]

with a monitored-transmission cutoff at

[  
\mathrm{BLER}\leq 0.02.  
]

If this cutoff is naively applied to a mean-like BER statistic, the link first appears to qualify for monitored transmission near (0.0) dB SNR. The derived block-level reference BLER does not reach the same cutoff until approximately (3.4) dB. The gap region is therefore

[  
\mathrm{SNR}\in[0.0,3.4],\mathrm{dB}.  
]

At the midpoint, SNR (=1.7) dB, BER is approximately (1.3\times 10^{-3}), while the independent-bit BLER reference is approximately (1.0). The authorization gap is large.

The BLER curve used here is the independent-bit reference curve derived from digitized BER,

[  
\mathrm{BLER}_{\mathrm{ref}} = 1-(1-\mathrm{BER})^L,  
]

with block length (L=65{,}536). It is not claimed to be the measured turbo-code channel law; turbo decoding creates correlated block failures. The role of the reference curve is to isolate mean-to-block amplification geometry.

Using log-uniform BLER thresholds over ([10^{-4},1.0]), breakpoints grow from 3 at (k=4) to 20 at (k=256) over 61 SNR points. Holding (k=256) fixed and increasing the SNR grid from 61 to 1,952 points, breakpoints grow from 20 to 205. The count scales with both permission-grid density and SNR resolution.

This is the signature of a smooth monotone function being subdivided. Turbo is therefore the smooth negative control: the authorization gap is real, but the densification staircase carries no structural signal beyond the monotone shape.

---

### 2.5 Ising belief propagation identifies a genuine structural step

We next evaluate loopy belief propagation on a (6\times 6) Ising grid at coupling strength (\beta=0.44), near critical coupling. Exact marginals are computed by full enumeration; BP marginals are computed by loopy belief propagation. The per-variable total variation distance between BP and exact marginals measures approximation error.

Two summary functionals are compared:

[  
TV_{\mathrm{mean}}=0.2231,  
\qquad  
TV_{\max}=0.3338.  
]

The compiler authorizes ACT only if TV (\leq \tau) for the chosen functional. Mean TV and max TV cross the authorization threshold at different (\tau), producing a gap region

[  
\tau\in[0.2231,0.3338]  
]

of width (0.1108).

We use a uniform (\tau)-grid over ([0,0.50]). At every

[  
k\in{4,8,16,32,64,128,256},  
]

the compiler produces exactly one breakpoint: the smallest grid point at or above

[  
TV_{\max}=0.3338.  
]

Breakpoint count is constant at 1 across all seven granularity levels. Location error is bounded by one grid spacing at every (k).

|(k)|Grid spacing|Location error|Error (\leq) spacing|
|--:|--:|--:|:-:|
|4|0.12500|0.04116|yes|
|8|0.06250|0.04116|yes|
|16|0.03125|0.00991|yes|
|32|0.01563|0.00991|yes|
|64|0.00781|0.00209|yes|
|128|0.00391|0.00209|yes|
|256|0.00195|0.00014|yes|

The error does not decrease at every doubling because the nearest grid point above (TV_{\max}) sometimes remains unchanged. This intermittent improvement is expected for a uniform rational grid converging to a non-grid-aligned target. The important fact is that the breakpoint remains pinned to a fixed structural threshold and the error stays within one grid spacing.

Ising therefore shows the opposite of turbo. Densification does not smooth the staircase away because the staircase is tracking a genuine step.

---

### 2.6 FAA instrument landing shows an evidence-axis transition

The third densification example is Category I instrument landing system geometry. At decision height (H) above the runway, the pilot must acquire visual reference to continue the approach. The geometric constraint used here is

[  
\mathrm{RVR}_{\mathrm{floor}}(H)=  
\max\left(0,\frac{H-50}{\tan(3^\circ)}-1000\right).  
]

The curve is smooth and decreasing in decision height until it saturates at zero near (H\approx102.4) ft. Above that point, the supplied visual-acquisition geometry is the binding evidence axis. Below that point, the supplied CAT I evidence package no longer constrains RVR; a different evidence axis would be needed.

The RVR floor falls from 3,770 ft at (H=300) ft to 336 ft at (H=120) ft, then reaches zero at approximately 102 ft and remains there. The saturation is not a regulatory choice. It is the geometric point where the supplied evidence axis stops speaking.

Using uniform RVR thresholds over ([0,2400]) ft, breakpoints grow from 4 at (k=4) to 64 at (k=64), then stabilize: at (k=128) and (k=256), the count remains 64. The 64 breakpoints above saturation correspond to the smooth geometric curve being subdivided by the finite grid. No additional breakpoints appear below saturation because RVR is identically zero; the flat region absorbs new grid points without producing new transitions.

The kink at 102.4 ft persists at every (k). It is not a quantization artifact. It is the boundary where the supplied evidence stops speaking.

Together, turbo, Ising and FAA geometry establish the densification diagnostic as a discriminator.

|Domain|Densification signature|Latent regularity|
|---|---|---|
|Turbo|Breakpoints grow with (k) and SNR resolution|Smooth monotone function|
|Ising|One breakpoint at all (k); spacing-bounded location error|Genuine structural step|
|FAA|Breakpoints stabilize at the evidence-axis saturation|Piecewise smooth with evidence-axis transition|

---

### 2.7 Evidence hiding produces conservative permission descent

The first evidence-side experiment hides evidence one gap at a time and reruns the compiler. The prediction is monotone descent: removing evidence may weaken or preserve authorization, but it cannot strengthen it.

#### ILS occlusion

The ILS hierarchy uses three gaps:

- `ils_signal_integrity` (S),
    
- `visual_reference` (V),
    
- `sub_cat1_authorization` (A).
    

Starting from all gaps at the status required for ALR, opening authorization drops permission to REV; opening visual reference drops permission to DIA; opening signal integrity drops permission to REF. The compiler traverses four levels in the theory-predicted order:

[  
\mathrm{ALR}\to\mathrm{REV}\to\mathrm{DIA}\to\mathrm{REF}.  
]

No reversals occur.

#### Epic medical-AI occlusion

The Epic hierarchy uses nine gaps: approximation quality (S1), freshness (S2), clinical utility (G1), model specification (G2), distribution shift (G3), individual-population scope (G4), blast radius (G5), authority/rollback (G6) and reason traceability (G7).

Starting from all gaps at the status required for ALR, opening G1 drops permission to AEX. The G-gaps gate ALR, not AEX, so opening G2–G7 individually does not lower permission further once AEX is already binding. Opening S2 drops AEX to REV. Opening S1 drops REV to DIA.

The occlusion staircase is not a smooth function. It is a piecewise-constant descent governed by the requirement map. The compiler is not making a judgment call. It is reading the hierarchy. This is the conservation law under evidence hiding: the accessible authorization may weaken, but it does not strengthen without new evidence.

---

### 2.8 Projection fidelity exposes the admissibility boundary

Evidence representations can be coarsened. Let

[  
\pi:E\to\bar E  
]

be a projection from fine evidence states to coarser evidence states. The semantic projected authorization is

[  
A^\pi(\bar e)=  
\bigwedge_{w:\pi(q(w))=\bar e} a(w).  
]

For every fine evidence state (e),

[  
A^\pi(\pi(e))\preceq A(e).  
]

Semantic coarsening is always conservative because it takes the meet over a larger compatible set.

Real implementations, however, need not compute the semantic meet. A projected compiler may use a simplified vocabulary, a new profile builder or a new requirement map. Let

[  
\widehat A^\pi:\bar E\to\mathcal A  
]

be the implemented authorization function under the projected representation. We call the projection authorization-admissible if

[  
\widehat A^\pi(\pi(e))\preceq A(e)  
\quad\text{for all }e\in E.  
]

This is the admissibility fence. Coarsening may hide evidence and weaken authorization. It may not create stronger permission.

We test this condition on the Epic evidence package using six projection levels. The finest representation has all nine gaps. Intermediate projections merge structurally related gaps. The coarsest representation collapses all evidence into two generic gaps: evidence quality and evidence scope.

Levels 0–3 merge gaps within the same functional category and produce no change in projected permission. Gap width is zero.

Level 4 merges reason traceability (G7) with freshness (S2) into a single `evidence_currency_gap`. This crosses a structural boundary in the requirement hierarchy. The projected compiler loses the ability to satisfy AEX through the two obligations independently. Projected permission drops from AEX to REV. Gap width becomes one permission rank. This is admissible: authorization weakens, but does not strengthen.

Level 5 merges all evidence into two generic gaps. This erases the AEX permission skeleton from the projected vocabulary. The profile builder can only check whether the generic gaps are open or satisfied. With the merged gaps satisfied, the compiler returns AEX. Gap width collapses back to zero.

This is the violation. No evidence has improved; only the representation changed. The projected compiler returns a stronger permission than the fine evidence warrants for the affected induction cases:

[  
\widehat A^\pi(\pi(e))\npreceq A(e).  
]

The Level 5 result is not a bad data point. It is the witness that admissibility is non-vacuous. A natural-looking simplification can fall outside the admissible class because it erases the permission skeleton.

---

### 2.9 Two-axis joint convergence recovers authorization from below

The previous experiments exercise the two approximation axes separately. Permission densification fixes evidence and refines the grid. Occlusion and projection fidelity fix the grid and alter evidence representation.

The joint-convergence theorem concerns both axes at once. It states that along a resolving evidence refinement and a permission grid resolving from below, implemented compiler outputs converge to (A(e)) from below, provided the implementation becomes meet-exact along the refinement.

We test this directly on the Epic hierarchy.

The experiment uses two cases:

- M01, a positive-control sound deployment;
    
- M02, the Epic Sepsis Model failure case.
    

Both have fine-resolution authorization

[  
A(e)=\mathrm{AEX}.  
]

Under the (k=64) normalized rank score used for plotting, this corresponds to 0.6562.

#### Resolving path

We define a nested resolving path

[  
R_4\to R_3\to R_2\to R_1\to R_0,  
]

where (R_4) is a coarse but admissible five-gap projection and (R_0) is the full nine-gap taxonomy. The path progressively splits composite gaps back into their fine obligations. The first split separates the structurally distinct reason-traceability and freshness obligations that were merged into an evidence-currency gap. Later splits refine deployment-control, population-generalization and clinical-efficacy composites.

At the coarsest point, (R_4) with (k=4), the merged evidence-currency gap blocks AEX. The compiler emits REV:

[  
C_{4,4}(e)=0.25.  
]

The gap to the fine authorization score is 0.4062.

At the first evidence refinement, (R_4\to R_3), the active structural merge is resolved and the AEX skeleton becomes expressible again. With (k) fixed at 4, the compiler recovers AEX at the coarse permission resolution:

[  
C_{3,4}(e)=0.50.  
]

The remaining gap is 0.1562.

Holding (R_3) fixed and densifying the permission grid from (k=4) to (k=32) closes the within-level grid gap:

[  
C_{3,32}(e)=0.6562=A(e).  
]

Further evidence refinements (R_2\to R_1\to R_0) leave the output unchanged because the compiler has already recovered AEX, and the fine taxonomy does not reveal a stronger permission. This is correct behavior. Once the projection is fine enough to resolve the blocking gap, further evidence refinement is inert unless it crosses a new permission boundary.

The resolving path satisfies all implemented checks:

|Check|Result|
|---|--:|
|Pointwise soundness over compiler cells|50/50|
|Evidence-axis monotonicity over transitions|40/40|
|Permission-axis monotonicity over transitions|40/40|
|Joint convergence at (R_0,k=64)|gap (=0.0000)|

This is an empirical instance of the joint theorem: along a resolving, asymptotically meet-exact refinement of both axes, (C_{m,n}(e)) approaches (A(e)) from below.

#### Non-resolving path

We also run a path that first passes through the inadmissible two-gap collapse (N_5):

[  
N_5\to R_4\to R_3\to R_2\to R_1\to R_0.  
]

At (N_5), the projection erases the AEX skeleton. For M01 and M02, this happens to emit AEX, the same value as the fine authorization. This is accidental pointwise agreement, not global admissibility. Section 2.8 shows that the same collapsed representation over-authorizes other induction cases.

At the next step, (N_5\to R_4), the admissible projected skeleton is restored. The compiler drops from AEX back to REV. This creates monotonicity failures at exactly this transition:

|Check|Result|
|---|--:|
|Pointwise no-overauthorization on selected cells|60/60|
|Global admissibility of (N_5)|failed in Section 2.8|
|Evidence-axis monotonicity over transitions|40/50|
|Permission-axis monotonicity over transitions|48/48|
|Joint convergence at (R_0,k=64)|gap (=0.0000)|

The 10 evidence-axis monotonicity failures are not noise. They are the predicted consequence of passing through a non-resolving, inadmissible representation. Theorem 4 gives sufficient conditions for monotone convergence; it does not claim that every eventually resolving path must be monotone. Once the non-resolving path enters the resolving tail (R_4\to R_0), it converges again.

This experiment closes the architecture loop. Permission densification shows how finite grids read (A(e)). Projection fidelity shows how representation can preserve or destroy the permission skeleton. Two-axis refinement shows both effects in one implemented surface.

---

### 2.10 External standards as correspondence audits

The previous results validate the compiler and conservation law under controlled transformations. We now ask a different question: how do external regulatory standards relate to the latent authorization structure induced by supplied evidence packages?

These tests are correspondence audits. They do not have equal independence, and they are not treated as the primary validation of the theory.

We classify six relationships.

1. **Exact recovery:** compiler threshold and external threshold identify the same fixed point.
    
2. **Representation-relative alignment:** compiler and external standard agree under the supplied representation but diverge under hierarchy perturbation.
    
3. **Same-axis policy margin:** compiler and external standard use the same evidence axis, but the external standard includes a safety margin, tolerance, rounding convention, equipment condition or policy choice not forced by the evidence package.
    
4. **Different evidence axis:** the standard covers a dimension not contained in the supplied evidence map.
    
5. **Hierarchy-placement failure:** a real gap exists but is placed at the wrong permission level.
    
6. **Outside supplied package:** the compiler is silent because the relevant gap is not represented.
    

#### FAA CAT I

The compiler derives the RVR-floor-vs-decision-height curve from glide-slope geometry without using the FAA CAT I threshold. At the standard CAT I decision height (H=200) ft, the frozen geometric model gives

# [  
\mathrm{RVR}_{\mathrm{floor}}(200)

\frac{200-50}{\tan(3^\circ)}-1000  
\approx 1862,\mathrm{ft}.  
]

The corresponding FAA CAT I minimum for suitably equipped runways is RVR 1,800 ft. The difference is 62 ft, or approximately 3.4% of the regulatory value. The curve crosses 1,800 ft at (H\approx196.7) ft.

This is not exact recovery. It is independent-route, same-axis policy-margin convergence. The evidence-derived geometry lands on the same visual-range axis and within the regulatory bin, while the residual identifies policy, rounding or equipment conventions not present in the supplied geometric package.

#### 3GPP BLER thresholds

Under the frozen hierarchy, the compiler aligns with 10% and 2% BLER thresholds. Under 59 hierarchy perturbations, recovery of 0.10 falls to 5.1%, and recovery of 0.02 falls to 3.4%, with zero recovery in structured perturbation families.

The alignment is representation-relative. The thresholds are not hierarchy-independent ridges of the latent function.

#### FDA AI/ML deployment gaps

The gap list induced from documented AI deployment failures — including Epic, Optum, PredPol, COMPAS and Watson — recovers categories that align with FDA AI/ML action-plan obligations. This is a same-axis policy correspondence from overlapping evidence, not an independent derivation. The regulator and compiler draw partly from the same public failure record.

#### ECOA reason traceability

The compiler induces G7, reason traceability, from credit and adverse-action failures. ECOA Regulation B requires adverse-action notices with specific reasons. Within the supplied adverse-action representation, the legal requirement and the induced gap identify the same authorization boundary.

This is exact recovery in the zero-gap sense: the supplied evidence representation determines a unique authorization value at the reason-traceability boundary.

#### FAA CAT II/III

CAT II and CAT III minima depend on evidence axes not present in the CAT I visual-geometry package: autoland, fail-operational systems, aircraft equipment, operator qualification and additional procedural controls. The compiler is silent on these axes because the supplied package does not represent them.

Silence is not permission. It means the supplied evidence map cannot authorize or refuse on that dimension.

#### Amazon recruiting

Amazon recruiting is held out from the taxonomy induction. The model-specification gap G2 is real and present in the induced package. The disagreement is a hierarchy-placement failure: the gap was identified, but the hierarchy placed it below the AEX requirement threshold, allowing AEX to proceed without closing it.

This distinction matters. A missing-gap failure and a hierarchy-placement failure require different repairs.

---

## 3. Discussion

The paper introduces a computational object for a problem that is usually handled by convention. Approximate systems do not merely predict. They authorize action. The central question is therefore not only whether a statistic is accurate, calibrated or robust. It is what action the statistic can soundly license under incomplete evidence.

The latent authorization function answers this question conditionally: given an evidence map, a permission order and world-level soundness semantics, the strongest evidence-supported action is the meet over compatible worlds. The answer is canonical only after those ingredients are supplied. The calculus does not choose the evidence map. It does not choose the permission hierarchy. It does not decide institutional risk tolerance. It separates the authorization forced by evidence from the permission added by policy and representation.

This separation gives three practical tools.

First, a finite permission hierarchy can be audited as an instrument. Densification reveals whether observed thresholds are smooth grid artifacts, genuine structural steps or evidence-axis transitions.

Second, evidence representations can be audited for admissibility. A coarser vocabulary may be useful, but it is safe only if it cannot return stronger permission than the finer evidence supports. The Epic projection experiment shows why this condition is non-vacuous: compactness can erase the permission skeleton.

Third, joint refinement can be tested. Experiment 6 demonstrates that a resolving evidence path and densifying permission grid recover the latent authorization value from below, while a path that passes through an inadmissible collapse loses monotonicity exactly where the theory predicts.

The regulatory correspondences should be read cautiously. They are not evidence that all regulation secretly computes the same law. They show that several external standards can be classified in the language of the calculus: exact recovery, same-axis margin, representation-relative alignment, different evidence axis, hierarchy-placement failure or outside-package silence. This classification is itself useful because it prevents false equivalence. FAA CAT I geometry is not the same kind of evidence as FDA deployment guidance. ECOA reason traceability is not the same kind of evidence as 3GPP threshold alignment. A single framework can compare them without pretending they have equal independence.

The main limitation is that the calculus is conditional. If the supplied evidence map erases a relevant distinction, (A(e)) will be conservative relative to the enlarged fiber. If the supplied permission hierarchy places a real gap at the wrong level, the compiler will faithfully implement that mistake. If the world-level authorization function is misspecified, the meet will preserve the wrong semantics. These are not implementation bugs. They are the boundary between authorization checking and domain judgment.

A second limitation is that the empirical domains are role-based demonstrations, not a representative sample. Turbo, Ising and FAA geometry are chosen to span regularity classes. Epic and ILS are chosen to test gap hierarchies. Regulatory standards are used as correspondence audits. The paper does not claim prevalence estimates across deployed AI systems.

A third limitation is that structural-gate behavior is predicted more broadly than it is demonstrated. Reason traceability supplies a zero-gap legal boundary in the ECOA representation, but a full dynamic experiment varying reason-trace evidence across a discontinuous gate remains future work.

Despite these limits, the conservation law gives a usable standard:

> Evidence may weaken, refine or relabel authorization under admissible transformations. It may not create permission.

That is the missing type rule for approximate systems acting under incomplete evidence.

---

## 4. Methods

### 4.1 Compiler implementation

The authorization compiler is implemented in Rust with Python bindings. Inputs are:

1. an evidence package with named gaps and statuses;
    
2. a permission hierarchy;
    
3. a per-permission requirement map.
    

Gap statuses are ordered

[  
\mathrm{open}\prec\mathrm{bounded}\prec\mathrm{closed}.  
]

A requirement cell specifies the minimum status sufficient for that gap at that permission level. A gap with observed status (s) satisfies requirement (r) exactly when

[  
r\preceq s.  
]

A requirement of `open` is vacuous. A requirement of `bounded` is satisfied by `bounded` or `closed`. A requirement of `closed` is satisfied only by `closed`.

The compiler traverses the permission hierarchy from strongest to weakest and returns the first level whose gap requirements are all satisfied. If no non-bottom level is satisfied, it returns REF. Computation is deterministic given the evidence state, permission hierarchy and requirement map. The source that proposed a gap is not an input to the compiler.

Implementation paths:

- `python/noethers_turnstile/__init__.py`
    
- `python/noethers_turnstile/_turnstile.so`
    
- `examples/conservation/`
    

---

### 4.2 Permission densification

For a finite grid (P_k), the mathematical compiler output is

[  
C_k(e)=\lfloor A(e)\rfloor_{P_k}.  
]

For plotting and breakpoint counting, this lattice element is represented by the normalized rank score

[  
s_k(e)=\frac{#{p\in P_k:p\preceq A(e)}}{|P_k|}.  
]

The score is an order-preserving relabelling under the threshold-count representation. No authorization claim depends on the normalization.

Uniform or log-uniform threshold grids are used depending on the evidence axis.

- Uniform grids are used for bounded linear quantities such as TV distance or RVR.
    
- Log-uniform grids are used for error rates spanning orders of magnitude.
    

Breakpoints are counted as swept-axis values where (s_k) changes. The swept axes are SNR for turbo, authorization tolerance (\tau) for Ising, and decision height (H) for FAA geometry.

Implementation path:

- `examples/conservation/run_densification.py`
    

---

### 4.3 Turbo experiment

BER data are digitized from Berrou et al. over a 12-point grid from (-1.0) to (5.0) dB SNR. For denser SNR grids, the digitized BER curve is interpolated piecewise linearly on the (\log_{10}\mathrm{BER}) scale as a function of SNR. The interpolated BER is transformed to the independent-bit BLER reference curve

[  
\mathrm{BLER}_{\mathrm{ref}}=1-(1-\mathrm{BER})^L,  
]

with block length

[  
L=65{,}536.  
]

This is not asserted to be the measured turbo-code BLER law. It is a reference curve for mean-to-block amplification.

Permission hierarchy:

- REFUSE when (\mathrm{BLER}>0.10);
    
- HOLD when (\mathrm{BLER}\leq0.10);
    
- TRANSMIT_MONITORED when (\mathrm{BLER}\leq0.02);
    
- TRANSMIT when (\mathrm{BLER}\leq0.001).
    

Log-uniform BLER thresholds are drawn over ([10^{-4},1.0]). The SNR-resolution check fixes (k=256) and varies the SNR grid from 61 to 1,952 points.

Implementation paths:

- `examples/conservation/run_permissivity_path.py`
    
- `examples/conservation/run_densification.py`
    

---

### 4.4 Ising experiment

A (6\times6) Ising grid is evaluated at coupling (\beta=0.44). The graph is the open-boundary square lattice with uniform ferromagnetic nearest-neighbor coupling and zero external field. No random couplings are drawn.

Exact marginals are computed by full enumeration over (2^{36}) states. BP marginals are computed by synchronous loopy belief propagation with 100 iterations and convergence threshold (10^{-6}). Per-variable TV is

[  
\frac{1}{2}\sum_x |p_{\mathrm{BP}}(x)-p_{\mathrm{exact}}(x)|.  
]

Mean TV is 0.2231. Max TV is 0.3338. Uniform (\tau)-grids are drawn over ([0,0.50]). The densification axis is the authorization tolerance (\tau), not a sweep over multiple Ising worlds.

Implementation paths:

- `examples/inference/ising/`
    
- `examples/conservation/run_densification.py`
    

---

### 4.5 FAA geometry experiment

Glide slope is (3^\circ) to runway threshold. Decision height is altitude above touchdown zone. The RVR floor is

[  
\max\left(0,\frac{H-50}{\tan(3^\circ)}-1000\right),  
]

where (H) is decision height in feet. Saturation occurs at

# [  
H_{\mathrm{sat}}

50+1000\tan(3^\circ)  
\approx102.4,\mathrm{ft}.  
]

At (H=200) ft, the frozen geometry gives

[  
\mathrm{RVR}_{\mathrm{floor}}(200)\approx1862,\mathrm{ft}.  
]

The curve crosses RVR (=1800) ft at (H\approx196.7) ft. Uniform RVR thresholds are drawn over ([0,2400]) ft.

Implementation path:

- `examples/ils/geometry.py`
    

---

### 4.6 Occlusion sweeps

The ILS hierarchy uses three gaps: signal integrity, visual reference and sub-CAT-I authorization. The minimum requirements are:

|Permission|Signal integrity|Visual reference|Sub-CAT-I authorization|
|---|---|---|---|
|ALR|closed|closed|closed|
|REV|closed|closed|open|
|DIA|closed|open|open|
|REF|open|open|open|

Opening authorization drops ALR to REV. Opening visual reference drops REV to DIA. Opening signal integrity drops DIA to REF.

The Epic hierarchy uses nine gaps: S1, S2 and G1–G7. The requirement matrix is:

|Permission|S1 approximation quality|S2 freshness|G1 clinical utility|G2 model specification|G3 distribution shift|G4 individual-population scope|G5 blast radius|G6 authority/rollback|G7 reason traceability|
|---|---|---|---|---|---|---|---|---|---|
|ALR|closed|closed|closed|closed|closed|closed|closed|closed|closed|
|AEX|closed|bounded|open|open|open|open|open|open|open|
|REV|bounded|open|open|open|open|open|open|open|open|
|DIA|open|open|open|open|open|open|open|open|open|
|REF|open|open|open|open|open|open|open|open|open|

The starting state sets all gaps to the status required for ALR. Gaps are opened in sequence: G1, G2, G3, G4, G5, G6, G7, S2, S1.

Implementation path:

- `examples/conservation/run_occlusion_sweep.py`
    

---

### 4.7 Projection fidelity

The projection-fidelity experiment applies six projected representations to the Epic evidence package.

- L0: all 9 gaps.
    
- L1: merge G1+G2 into clinical efficacy.
    
- L2: merge G3+G4 into population generalization.
    
- L3: merge G5+G6 into deployment safety.
    
- L4: merge G7+S2 into evidence currency.
    
- L5: collapse S1+S2 into evidence quality and G1–G7 into evidence scope.
    

For admissible projections, composite-gap semantics are conservative. The observed status of a composite gap is the meet of component statuses under

[  
\mathrm{open}\prec\mathrm{bounded}\prec\mathrm{closed}.  
]

At each permission level, the composite requirement is chosen to preserve the permission skeleton conservatively. A composite gap is satisfied only when its components would have satisfied their inherited fine-level obligations.

L5 intentionally uses the collapsed two-gap profile builder rather than the inherited conservative map. Its generic requirements erase the AEX skeleton. This makes L5 the non-vacuity witness for inadmissibility.

Implementation path:

- `examples/conservation/run_projection_fidelity.py`
    

---

### 4.8 Two-axis joint convergence

Experiment 6 defines a nested resolving path derived from the projection levels, but not identical to the non-nested projection-fidelity sequence.

The resolving path is

[  
R_4\to R_3\to R_2\to R_1\to R_0.  
]

- (R_4): five-gap admissible projection.
    
- (R_3): splits evidence currency into reason traceability and freshness.
    
- (R_2): splits deployment control into blast radius and authority/rollback.
    
- (R_1): splits population generalization into distribution shift and individual-population scope.
    
- (R_0): full nine-gap taxonomy.
    

The non-resolving path prepends the inadmissible L5-style collapse:

[  
N_5\to R_4\to R_3\to R_2\to R_1\to R_0.  
]

The permission grid is swept over

[  
k\in{4,8,16,32,64}.  
]

The reported cases are M01 and M02. Both have fine authorization (A(e)=\mathrm{AEX}), normalized to 0.6562 at (k=64).

For the resolving path:

- pointwise soundness is evaluated over (2\times5\times5=50) compiler cells;
    
- evidence-axis monotonicity is evaluated over (2\times4\times5=40) transitions;
    
- permission-axis monotonicity is evaluated over (2\times5\times4=40) transitions.
    

For the non-resolving path:

- selected-cell no-overauthorization is evaluated over (2\times6\times5=60) cells;
    
- evidence-axis monotonicity is evaluated over (2\times5\times5=50) transitions;
    
- permission-axis monotonicity is evaluated over (2\times6\times4=48) transitions.
    

The non-resolving path is not globally admissible because (N_5) over-authorizes other induction cases, as shown in the projection-fidelity experiment.

Implementation path:

- `examples/conservation/run_joint_convergence.py`
    

---

### 4.9 Blind regulatory audit protocol

For each regulatory case, the protocol is:

1. freeze evidence inputs from public sources without using the target standard;
    
2. run the compiler;
    
3. record output;
    
4. compare with the regulatory or legal standard;
    
5. classify the correspondence.
    

The ILS geometry derivation, Epic/FDA gap induction, 3GPP hierarchy construction, ECOA reason-traceability induction and Amazon held-out classification were completed before their corresponding comparisons were used for scoring. Amazon was not used to induce the taxonomy; it was held out to test hierarchy placement after G2 already existed.

The resulting classes are exact recovery, representation-relative alignment, same-axis policy margin, different evidence axis, hierarchy-placement failure and outside supplied package.

---

## 5. Data availability

All numerical values reported in the paper are generated from deterministic scripts under `examples/conservation/results/` and the domain-specific example folders listed in Methods. The regulatory correspondence audit is represented as a provenance table in `docs/provenance.md`. No private patient-level, applicant-level or individual-level data are used.

---

## 6. Code availability

The compiler is implemented in Rust with Python bindings under `python/noethers_turnstile/`. Experiment scripts are listed in Methods. Public release details, commit hash and archival DOI are TBD.

---

## 7. Ethics and human subjects

This work uses public incident reports, public regulatory standards, synthetic or deterministic computational examples and hand-constructed evidence packages. It does not use human-subject records, patient-level data, applicant-level data or private institutional data.

---

## 8. Competing interests

The authors declare no competing interests. TBD before submission.

---

## 9. Author contributions

TBD.

---

## 10. Acknowledgements

TBD.

---

## Appendix A. Proofs

### A.1 Finite lower-approximation law

Recall

[  
C_k(e)=\lfloor A(e)\rfloor_{P_k}  
]

and

[  
\lfloor x\rfloor_{P_k}=\max{p\in P_k:p\preceq x}.  
]

By definition, (C_k(e)) is chosen from permissions satisfying (p\preceq A(e)). Therefore

[  
C_k(e)\preceq A(e).  
]

If (P_k\subseteq P_{k+1}), the feasible set defining (C_k(e)) is contained in the feasible set defining (C_{k+1}(e)). Taking the maximum over a larger feasible set can only increase or preserve the result:

[  
C_k(e)\preceq C_{k+1}(e).  
]

Soundness gives

[  
C_{k+1}(e)\preceq A(e).  
]

If (P_k) resolves (\mathcal A) from below, then for every (x\in\mathcal A),

[  
\bigvee_k \lfloor x\rfloor_{P_k}=x.  
]

Applying this to (x=A(e)),

# [  
\bigvee_k C_k(e)

# \bigvee_k \lfloor A(e)\rfloor_{P_k}

A(e).  
]

Thus (C_k(e)) converges to (A(e)) from below.

---

### A.2 Conservative coarsening law

For a projection (\pi:E\to\bar E), define

[  
F_\pi(\bar e)={w\in W:\pi(q(w))=\bar e}.  
]

For every fine evidence state (e),

[  
F(e)\subseteq F_\pi(\pi(e)).  
]

The projected fiber is larger. Taking the meet over a larger set can only weaken or preserve the result:

# [  
A^\pi(\pi(e))

# \bigwedge_{w\in F_\pi(\pi(e))}a(w)  
\preceq  
\bigwedge_{w\in F(e)}a(w)

A(e).  
]

Equivalently,

[  
A^\pi(\bar e)=  
\bigwedge_{e'\in\pi^{-1}(\bar e)}A(e').  
]

Let (\widehat A^\pi) be an implemented projected authorization function. The implementation is authorization-admissible if

[  
\widehat A^\pi(\pi(e))\preceq A(e)  
\quad  
\text{for all }e\in E.  
]

Because the floor operator is monotone,

[  
\lfloor \widehat A^\pi(\pi(e))\rfloor_{P_k}  
\preceq  
\lfloor A(e)\rfloor_{P_k}.  
]

Therefore

[  
C_k^\pi(\pi(e))\preceq C_k(e).  
]

---

### A.3 Semantic convergence under resolving refinement

Let ((\pi_m)) be a refining evidence-projection sequence. For a fixed (e), define

[  
[e]_m={e'\in E:\pi_m(e')=\pi_m(e)}.  
]

Refinement means

[  
[e]_{m+1}\subseteq [e]_m.  
]

The semantic projected authorization is

[  
A^{\pi_m}(\pi_m(e))=  
\bigwedge_{e'\in[e]_m} A(e').  
]

Since (e\in[e]_m),

[  
A^{\pi_m}(\pi_m(e))\preceq A(e).  
]

Because ([e]_{m+1}\subseteq[e]_m), the meet at level (m+1) is taken over a subset of the states used at level (m). Taking a meet over a smaller set can only strengthen or preserve the result:

[  
A^{\pi_m}(\pi_m(e))  
\preceq  
A^{\pi_{m+1}}(\pi_{m+1}(e)).  
]

Thus the sequence is monotone nondecreasing and bounded above by (A(e)).

Assume the sequence is resolving at (e). For every (p\prec A(e)), there exists (m_0) such that for all (m\geq m_0) and all (e'\in[e]_m),

[  
p\preceq A(e').  
]

Therefore (p) is a lower bound for ({A(e'):e'\in[e]_m}), so

[  
p\preceq A^{\pi_m}(\pi_m(e)).  
]

Every permission strictly below (A(e)) is eventually below the projected authorization. Since projected authorization is always no stronger than (A(e)), its supremum is (A(e)). Hence

[  
A^{\pi_m}(\pi_m(e))\nearrow A(e).  
]

---

### A.4 Joint implemented convergence

Let ((\pi_m)) be refining and resolving at (e), and let

[  
\widehat A_m:E_m\to\mathcal A  
]

be the implemented authorization function at resolution (m).

The implementation is asymptotically meet-exact at (e) if it is conservative relative to the semantic projected meet,

[  
\widehat A_m(\pi_m(e))  
\preceq  
A^{\pi_m}(\pi_m(e)),  
]

and its eventual lower envelope converges to (A(e)):

# [  
\bigvee_{M\geq1}  
\bigwedge_{m\geq M}  
\widehat A_m(\pi_m(e))

A(e).  
]

Define the two-axis compiler output

[  
C_{m,n}(e)=  
\left\lfloor \widehat A_m(\pi_m(e)) \right\rfloor_{P_n}.  
]

Because

[  
C_{m,n}(e)  
\preceq  
\widehat A_m(\pi_m(e))  
\preceq  
A(e),  
]

every output is a lower bound on (A(e)).

Let (p\prec A(e)). By asymptotic meet-exactness, eventually

[  
p\preceq \widehat A_m(\pi_m(e))  
]

up to the relevant order-dense or finite-chain formulation. Since (P_n) resolves (\mathcal A) from below, there exists (n_0) such that for all sufficiently large (n), the grid contains a point no weaker than (p) and no stronger than the implemented authorization. Therefore

[  
p\preceq C_{m,n}(e)\preceq A(e)  
]

for sufficiently large (m,n). Hence (C_{m,n}(e)\to A(e)) from below along cofinal refinements of both axes.

If the evidence projections and permission grids are nested, convergence is monotone. Otherwise, convergence from below does not imply pointwise monotonicity.

---

### A.5 Evidence-representation invariance

Two evidence representations

[  
q_1:W\to E_1,  
\qquad  
q_2:W\to E_2  
]

are authorization-equivalent if they induce the same evidence fibers up to relabelling. That is, there exists a bijection

[  
\psi:q_1(W)\to q_2(W)  
]

such that

[  
q_2=\psi\circ q_1.  
]

Then for any evidence state (e),

[  
F_2(\psi(e))=F_1(e).  
]

Therefore

# [  
A_2(\psi(e))

# \bigwedge_{w\in F_2(\psi(e))}a(w)

# \bigwedge_{w\in F_1(e)}a(w)

A_1(e).  
]

Thus evidence representations with the same fibers induce the same latent authorization function up to relabelling.

---

### A.6 Exact recovery iff the fiber is authorization-constant

For an evidence state (e), define

[  
A(e)=\bigwedge_{w\in F(e)}a(w)  
]

and

[  
B(e)=\bigvee_{w\in F(e)}a(w).  
]

If (a(w)) is constant over (F(e)), say (a(w)=p) for every (w\in F(e)), then

[  
A(e)=B(e)=p.  
]

Conversely, suppose

[  
A(e)=B(e)=p.  
]

For any (w\in F(e)),

[  
A(e)\preceq a(w)\preceq B(e).  
]

Since (A(e)=B(e)=p), it follows that (a(w)=p). Thus (a) is constant over the fiber.

The evidence determines a unique authorization value exactly when all compatible worlds have the same world-level authorization.

---

### A.7 Order- and source-invariance

Suppose a fixed corpus determines a finite set (G^\star) of visible, policy-relevant failure modes. Suppose the induction procedure adds a gap whenever a processed case exposes a permissive disagreement blocked by that gap, never removes gaps, and eventually processes every case.

Each induction step adds an element of (G^\star). No step removes elements. Because every case is eventually processed, every gap in (G^\star) is eventually exposed and added. The terminal set is

[  
\bigcup_{\text{cases }c}g(c)=G^\star.  
]

Set union is commutative and associative, so the result does not depend on case order.

For source-invariance, fix evidence state (e), permission hierarchy (P) and requirement map (R). The compiler is a deterministic function

[  
C(e;P,R).  
]

No argument to this function records whether a gap was proposed by an expert, induced from a deployment failure, suggested by an LLM, copied from regulation or written by a developer. Therefore two evidence packages with identical gaps, statuses, permission hierarchy and requirement map produce identical compiler outputs. The source may affect epistemic trust in the evidence contract, but it does not affect compiler soundness relative to that contract.

---

## Supplementary Note 1. Regulatory correspondence matrix

The full audit table is maintained in `docs/provenance.md`.

There are 76 gap-status assignments across induction cases M01–M07 and audit or held-out cases H02–H04. Of these, 51 are sourced to public documents, 12 are assumed-conservative, 7 are assumed-anti-conservative and 6 are by construction.

The non-consecutive held-out labels are historical audit-trail labels. H01 was an internal pilot and is excluded from the reported matrix. H02 is the FDA deployment-gap audit. H03 is the ECOA adverse-action/reason-traceability audit. H04 is Amazon recruiting.

H04 S2 status is reported with two runs: S2=bounded, yielding AEX, and S2=open, yielding REV.

---

## Supplementary Note 2. 3GPP perturbation experiment

Fifty-nine hierarchies are tested: five granularity levels, four offsets and 50 random perturbations. Each hierarchy assigns different numerical values to BLER thresholds while preserving ordering structure.

Recovery of 0.10 occurs in 3/59 runs, or 5.1%. Recovery of 0.02 occurs in 2/59 runs, or 3.4%. Structured perturbation families show zero recovery.

Under the frozen hierarchy, both thresholds align. Under perturbation, they do not. The conclusion is representation-relative alignment, not hierarchy-independent recovery.

Implementation path:

- `examples/inference/register2/turbo/experiment_a_stability.py`
    

---

## Supplementary Note 3. Metric invariance

Four functionals on the same Ising TV distribution are tested:

- F1: mean TV;
    
- F2: median TV;
    
- F3: 75th-percentile TV;
    
- F4: max TV.
    

They are tested at

[  
\beta\in{0.20,0.30,0.40,0.44}.  
]

F4 is largest at all (\beta), and all other functionals remain bounded below it. The ruler changes across functionals; the authorization ordering does not. This is an operational witness for representation invariance weaker than literal fiber identity.

The turbo analogue tests:

- T1: BER;
    
- T2: BER plus one standard deviation;
    
- T3: derived BLER reference curve.
    

Ordering holds at 61/61 SNR points.

Implementation path:

- `examples/conservation/run_metric_invariance.py`
    

---

## Supplementary Note 4. World-realizability witnesses

For each induced gap G1–G7, a world-realizability witness is a concrete deployment scenario where the gap is open, the system takes an over-authorized action, and a real failure occurs that is not merely a documentation failure.

|Gap|Witness scenario|Why the failure is world-realizable|
|---|---|---|
|G1 clinical utility|A sepsis alert has acceptable retrospective discrimination but no demonstrated clinical benefit at the deployed intervention threshold.|Clinicians receive actionable alerts, but patient outcomes or workflow burden make the intervention unsound despite predictive signal.|
|G2 model specification|A recruiting model is trained to predict historical resume-screening success and then used as if it measured job qualification.|The target variable is a proxy for prior institutional behavior, so the deployed action optimizes the wrong world-level property.|
|G3 distribution shift|A model trained and calibrated at one hospital, region or population is deployed in a different site with different base rates or measurement practices.|The same score no longer denotes the same risk; authorization based on the source distribution overstates what the target evidence supports.|
|G4 individual-population scope|Population-average performance is used to justify action on a subgroup or individual whose error profile is materially worse.|The mean statistic is true, but the action fails for compatible individuals hidden inside the evidence fiber.|
|G5 blast radius|An automated hold, denial or alert triggers many downstream actions without bounding the number of affected people or severity of consequences.|Local model error becomes system-level harm because propagation was not bounded.|
|G6 authority/rollback|An automated system continues consequential action after conditions change, without a clear authority boundary or rollback protocol.|The world contains no operative mechanism for stopping or reversing the action.|
|G7 reason traceability|A credit or adverse-action model cannot produce principal reasons connecting applicant inputs to the decision.|The denial occurs, but the system cannot generate reasons needed for review, contestation or legal notice.|

---

## Figure captions

**Figure 1. The latent authorization function.**  
A finite permission grid reads (A(e)) as a staircase approximation from below. A coarse grid produces blocky authorization. A refined grid samples the same latent function more sharply. The latent function itself is the meet of world-level authorizations over the evidence fiber.

**Figure 2. Densification signatures.**  
Turbo-coded communication is the smooth negative control: breakpoints grow with permission-grid and SNR resolution. Ising belief propagation shows a genuine structural step: one breakpoint remains pinned to (TV_{\max}=0.3338). FAA CAT I geometry shows an evidence-axis transition: the smooth RVR floor saturates near 102.4 ft, after which the supplied visual evidence axis no longer constrains authorization.

**Figure 3. Evidence hiding produces conservative permission descent.**  
ILS occlusion descends ALR → REV → DIA → REF as authorization, visual-reference and signal-integrity gaps are opened. Epic occlusion descends ALR → AEX when G1 opens, then AEX → REV when S2 opens, then REV → DIA when S1 opens.

**Figure 4. Projection fidelity and admissibility.**  
Epic projection levels 0–3 preserve permission. Level 4 merges reason traceability with freshness and weakens authorization from AEX to REV, satisfying admissibility. Level 5 collapses the evidence vocabulary and spuriously restores AEX, violating the admissibility condition.

**Figure 5. Two-axis joint convergence.**  
Resolving path: a coarse admissible evidence projection and coarse permission grid start below (A(e)). Evidence refinement resolves the active structural merge and permission densification closes the remaining grid gap, converging to (A(e)=\mathrm{AEX}). Non-resolving path: the inadmissible two-gap collapse emits AEX by skeleton erasure, then drops to REV when the admissible skeleton is restored, producing monotonicity failures exactly at the non-resolving step.

**Figure 6. External standards as correspondence audits.**  
FAA CAT I is an independent-route same-axis policy-margin correspondence: frozen geometry gives 1,862 ft at DH=200 ft versus the 1,800 ft standard. ECOA reason traceability is exact recovery in the supplied adverse-action representation. 3GPP is representation-relative. FDA AI/ML gaps are shared-corpus same-axis correspondence. FAA CAT II/III are different-axis or outside-package cases. Amazon recruiting is a hierarchy-placement failure.

---

## References

1. Berrou, C., Glavieux, A. & Thitimajshima, P. Near Shannon limit error-correcting coding and decoding: Turbo-codes. _Proceedings of IEEE International Conference on Communications_ (1993).
    
2. 3GPP. TS 38.214. _NR; Physical layer procedures for data_.
    
3. U.S. Food and Drug Administration. _Artificial Intelligence/Machine Learning (AI/ML)-Based Software as a Medical Device (SaMD) Action Plan_ (2021).
    
4. Consumer Financial Protection Bureau. _Equal Credit Opportunity Act (Regulation B), 12 CFR Part 1002_, including §1002.9, Notifications.
    
5. Federal Aviation Administration. _Aeronautical Information Manual_, Chapter 5, Section 4, Arrival Procedures.
    
6. Federal Aviation Administration. _Runway Visual Range (RVR)_, navigation services description of CAT I/II/III minima.
    
7. Wong, A., Otles, E., Donnelly, J. P. et al. External validation of a widely implemented proprietary sepsis prediction model in hospitalized patients. _JAMA Internal Medicine_ (2021).
    
8. Obermeyer, Z., Powers, B., Vogeli, C. & Mullainathan, S. Dissecting racial bias in an algorithm used to manage the health of populations. _Science_ (2019).
    
9. Lum, K. & Isaac, W. To predict and serve? _Significance_ (2016).
    
10. Angwin, J., Larson, J., Mattu, S. & Kirchner, L. Machine bias. _ProPublica_ (2016).
    
11. Dastin, J. Amazon scraps secret AI recruiting tool that showed bias against women. _Reuters_ (2018).
    
12. Additional IBM Watson oncology, PredPol, COMPAS, Epic, Optum and Amazon source documents are listed in the full audit trail at `docs/provenance.md`.
    

---