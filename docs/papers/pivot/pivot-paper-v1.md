# The Conservation of Incomplete Evidence

**A latent authorization law for approximate and consequential systems**

## Abstract

TBD

---

## 1. Introduction

Approximate systems increasingly gate consequential action. A sepsis model decides which patients trigger a clinical alert [7]. A risk score informs pretrial detention [10]. A care-management algorithm allocates services across a population [8]. A predictive-policing system directs patrols [9]. A resume screener forwards or discards a candidate [11]. In each case a system that is only approximately correct is granted authority to act, and the action carries cost that the model itself does not bear. When these systems fail in the ways that reach public record, the failure is frequently not a modeling error in the ordinary sense. The Optum algorithm predicted health-care cost accurately; cost was the wrong proxy for need [8]. The Amazon screener learned its training signal faithfully; the signal encoded historical hiring rather than qualification [11]. The Epic sepsis model carried real predictive signal; that signal did not establish benefit at the deployed intervention threshold [7]. The recurring fault is not that the statistic was false. It is that a true statistic was allowed to authorize an action it did not support. This is an authorization error, and it is distinct from, and largely orthogonal to, predictive accuracy.

The asymmetry in our theory is striking. We have a mature account of how well a model predicts — calibration, generalization, error bounds, uncertainty quantification. We have almost no principled account of when a prediction licenses an action. In practice the licensing step is supplied by convention. A threshold is chosen, a population average is compared against a cutoff, a regulatory label is matched, votes are aggregated. These devices answer a question they never state: given everything the evidence does and does not reveal, what is the strongest action this evidence can soundly support? Treated as conventions, such thresholds are defensible operational choices. Treated as facts about the evidence, they are unjustified, and the gap between the two is exactly where authorization errors live.

Here we show that this question has a canonical answer, and that the answer is conserved. Fix what a system's evidence package can observe. Many distinct states of the world remain compatible with any given observation; the evidence cannot separate them. The authorization the evidence forces is the strongest action that is sound in _every_ compatible world — the worst case over what the evidence has failed to rule out, not the average over it. We call this the latent authorization function $A(e)$, and it is a meet, a greatest lower bound, rather than a mean. The distinction is not technical. Optum's failure is precisely the substitution of a population average for a meet: the cost prediction was true on average and unsound for the compatible individuals hidden inside that average. $A(e)$ is the object that those individuals would have forced had the evidence been able to see them, and it exists whether or not any deployed system computes it.

A finite system does not create $A(e)$. It reads it, through two finite instruments, and it can lose it in only one way. The first instrument is a permission scale: a finite hierarchy of action levels through which the continuous authorization value is observed as a staircase. The second is an evidence vocabulary: a finite, possibly coarse representation of what the system records. We prove that a finite permission scale can only approximate $A(e)$ from below — it is always sound, never spuriously permissive, and it sharpens monotonically as the scale is refined. We prove that coarsening the evidence vocabulary may hide distinctions and weaken authorization, but, when the coarsening is _admissible_, can never manufacture permission the compatible worlds do not support. And we prove that these two refinements, of the permission scale and of the evidence vocabulary, are refinements of the same object: along any jointly resolving sequence they converge to $A(e)$. This is the conservation law of the title. Admissible transformations may weaken, refine, or relabel authorization. They may not create it. Authorization is conserved across change of representation in the same sense that a physical invariant is conserved across change of coordinates: the ruler may change, the boundary does not.

We make the law operational with a compiler that takes an evidence package, a permission hierarchy, and a per-level requirement map, and returns the strongest sound action level — a type checker for authorization rather than a model. We then test it along both axes across four domains chosen to span the regularity classes the theory predicts and to range from a physics-grade system to socio-technical ones: turbo-coded communication [1], loopy belief propagation on an Ising lattice, instrument-landing approach geometry [5,6], and medical and credit AI [7,8]. Refining the permission scale discriminates a genuine decision threshold from a quantization artifact and from an evidence-axis transition: the breakpoint signature differs by class, and the diagnostic fires correctly on all three, including the smooth negative control where it must report nothing. Hiding evidence one gap at a time drives authorization downward in exactly the order the hierarchy predicts, with no reversals. And an aggressive but natural-looking simplification of the evidence vocabulary returns a stronger permission than the unchanged evidence warrants — a concrete witness that the admissibility condition is non-vacuous, and that representational compactness bought at the cost of the permission skeleton is not free.

The strongest test removes the system's knowledge of the answer. Under a blind protocol, we freeze each evidence package from public sources and run the compiler before consulting any regulatory standard, then classify how the evidence-derived boundary relates to the published one. The correspondences are graded, and we report them as such: from instrument-landing geometry, frozen in advance, the compiler derives a required visual range of approximately 1,862 ft at the standard decision height, against a regulatory minimum of 1,800 ft — an independent, same-axis prediction landing within 3.4% of a number it never saw, with the residual identifying the policy margin rather than the evidence-forced floor. The Equal Credit Opportunity Act's reason-traceability requirement [4] is recovered exactly, as the zero-gap boundary case of the theory. Communications [2] and medical-device [3] thresholds align as representation-relative and shared-corpus correspondences, weaker in independence but consistent in structure. Read together, regulatory thresholds spanning aviation, telecommunications, medicine, and credit behave as samples of a single latent authorization structure — independently legislated in four domains, and recovered from evidence geometry alone.

The contribution is a calculus, not a verdict. The law does not choose the evidence map or the permission hierarchy; those remain matters of domain knowledge and institutional judgment, and the paper is explicit about where it is silent. What the law provides is the separation that the failure cases lacked: a principled boundary between the authorization that evidence forces and the permission that policy and representation add. Approximate systems will continue to act under incomplete evidence. The question this paper answers is what that incomplete evidence can, and cannot, be made to authorize.

---

## 2. Results

Authorization structure is a conserved quantity of incomplete evidence. The conserved object is $A(e)$: the strongest permission sound in every world still compatible with the evidence state $e$, equivalently the meet of world-level authorizations over the evidence fiber. The finite compiler does not create this quantity. It reads it, approximates it, and loses it only when the representation ceases to be admissible.

The results are organized by the two axes along which a finite system can fail to see the same object. The first axis is permission resolution: the evidence representation is fixed, while the permission hierarchy is densified so that the finite instrument gives a sharper reading of (A(e)). The second axis is evidence representation: evidence is hidden, projected, or compared against external standards, and the admissibility symmetry is tested. Along this second axis, authorization may weaken, but it may not strengthen without new evidence. The results therefore do not present densification and conservation as separate findings. They present one object, the finite measurement of that object, and the transformations under which it is conserved.

The case count follows from this architecture. The densification experiments are coverage tests for the three regularity classes demonstrated here — smooth artifact, structural step, and evidence-axis kink — rather than frequency estimates over application domains. The conservation experiments test the admissibility symmetry in two independently documented hierarchies, one physical and one socio-technical, and then compare the same object against external regulatory standards. The claim is not that these examples exhaust consequential authorization, but that they instantiate the two axes by which finite systems observe the same latent authorization function.

### 2.1 Finite permission levels sample a latent authorization function

**Setup.** Fix an evidence path: a sequence of evidence states parameterized by a single variable. Define a family of permission grids (P_k) for

[
k \in {4, 8, 16, 32, 64, 128, 256}.
]

At each (k), run the compiler on every evidence point and record

[
C_k(e) = \lfloor A(e) \rfloor_{P_k}.
]

Count the breakpoints: evidence values where (C_k) changes. For domains with a known structural threshold, also measure the location error.

**The diagnostic.** Three signatures appear in the experiments:

* **Artifact:** breakpoint count grows with (k) and with evidence-path resolution. The staircase has no fixed target; it is subdividing a smooth curve.
* **Genuine threshold:** breakpoint count is constant across all (k); location error is bounded by one grid spacing at every (k); spacing (\to 0) implies error (\to 0).
* **Kink:** breakpoint count grows until a structural feature is resolved, then stabilizes; additional resolution fills smooth regions without creating new features.

For monotone, piecewise-smooth governing functions with finitely many structural features, these signatures separate quantization artifacts from genuine thresholds and evidence-axis transitions. The experiment tests which signature applies in each domain.

![Figure 1. Permission densification schematic — coarse staircase, refined staircase, latent function.](figures/fig1_latent_function.png)

### 2.2 Turbo-coded communication: the smooth negative control

**Domain.** Turbo codes transmit data over a noisy channel. Two error statistics are available: bit error rate (BER), which averages errors over bits, and block error rate (BLER), which flags a block as failed if any bit fails. BER and BLER diverge: a bit-level statistic can look acceptable while the corresponding block-level failure probability remains too high. The evidence package available to a scheduler or admission controller typically aggregates to something closer to BER than to BLER.

**Authorization gap.** Under a four-level hierarchy

[
\mathrm{REFUSE} / \mathrm{HOLD} / \mathrm{TRANSMIT\_MONITORED} / \mathrm{TRANSMIT},
]

the block-level monitored-transmission cutoff is (\mathrm{BLER}\leq 0.02). If that numerical cutoff is naively applied to the mean-like BER statistic, the link first appears to qualify for monitored transmission at approximately (0.0) dB SNR. The derived block-level BLER does not reach the same cutoff until approximately (3.4) dB. The gap region,

[
\mathrm{SNR} \in [0.0, 3.4]\ \mathrm{dB},
]

is the interval where a mean-like evidence summary authorizes a level the block-level evidence cannot support. At the midpoint, SNR (=1.7) dB, BER is (1.3\times 10^{-3}), while the derived BLER is approximately (1.0). The authorization gap is not small.

The BLER curve used here is the independent-bit reference curve derived from digitized BER,

[
\mathrm{BLER}_{\mathrm{ref}} = 1 - (1-\mathrm{BER})^L,
]

with block length (L=65{,}536). It is not claimed to be the measured turbo-code channel law; turbo decoding creates correlated block failures. The role of this reference curve is to isolate the mean-to-block amplification geometry.

**Densification.** We use log-uniform BLER thresholds over

[
[10^{-4}, 1.0].
]

At 61 SNR points, breakpoints grow from 3 at (k=4) to 20 at (k=256). Holding (k=256) fixed and increasing the SNR grid from 61 to 1,952 points, breakpoints grow from 20 to 205. The count scales with grid density and SNR resolution: the characteristic signature of a monotone curve being subdivided.

**SNR-resolution check.** As a negative control, this test asks whether the turbo reference curve contains internal structure that densification should recover. If breakpoints had stabilized, turbo would no longer be a smooth-control case; it would have exposed a fixed threshold or kink worth reporting. They did not. The correct conclusion is that the independent-bit BLER reference curve has no internal kinks between (-1) and (5) dB SNR. The governing function is smooth and monotone throughout the tested range, and the finite-permission staircase is a measurement artifact. This makes turbo the right negative control: a domain where the authorization gap is real, but the densification staircase carries no signal beyond the monotone shape.

> *Turbo shows the law without institutional structure: the compiler samples a smooth monotone failure function, and finite staircases disappear as artifacts of the measurement grid.*

### 2.3 Ising belief propagation: a genuine structural step

**Domain.** Loopy belief propagation (BP) on a (6\times 6) Ising grid at coupling strength (\beta = 0.44), near critical coupling. Exact marginals are computed by full enumeration; BP marginals are computed by loopy BP. The per-variable total variation (TV) between BP and exact marginals measures approximation error. Two summary functionals are compared:

[
TV_{\mathrm{mean}} = 0.2231,
\qquad
TV_{\max} = 0.3338.
]

The compiler authorizes ACT only if TV (\leq \tau) for the chosen functional. Mean TV and max TV cross the authorization threshold at different (\tau), producing a gap region

[
\tau \in [0.2231,0.3338]
]

of width (0.1108).

**Densification.** Use a uniform (\tau)-grid over ([0,0.50]). At every

[
k \in {4,8,\ldots,256},
]

the compiler produces exactly one breakpoint: the smallest grid point at or above

[
TV_{\max}=0.3338.
]

Breakpoint count is constant at 1 across all seven granularity levels.

**Location-error tracking.** The location error, the distance from the grid-estimated threshold to the true (TV_{\max}), is bounded by one grid spacing at every (k).

| (k) | Grid spacing | Location error | Error (\leq) spacing? |
| --: | -----------: | -------------: | :-------------------: |
|   4 |      0.12500 |        0.04116 |          yes          |
|   8 |      0.06250 |        0.04116 |          yes          |
|  16 |      0.03125 |        0.00991 |          yes          |
|  32 |      0.01563 |        0.00991 |          yes          |
|  64 |      0.00781 |        0.00209 |          yes          |
| 128 |      0.00391 |        0.00209 |          yes          |
| 256 |      0.00195 |        0.00014 |          yes          |

The error does not decrease at every doubling. At (k=4\to 8), the nearest grid point above (TV_{\max}) remains (0.375), so no improvement occurs. At (k=8\to 16), a new grid point lands at (0.344), and the error drops. This intermittent improvement is the expected behavior of a uniform rational grid converging to a fixed non-grid-aligned target. It is not noise; it is the signature that the breakpoint is tracking a fixed point. An artifact has no fixed target, so its error has no reason to remain inside one spacing as spacing shrinks.

The claim, stated precisely: the single breakpoint is pinned to (TV_{\max}) up to the resolution currently available. As spacing (=0.50/k\to 0), the error (\to 0).

> *Ising shows the opposite of turbo: densification does not smooth the staircase away, because the staircase is the function.*

### 2.4 FAA instrument landing: a smooth function with a structural kink

**Domain.** Category I instrument landing system (ILS) approach geometry. At decision height (DH) above the runway, the pilot must acquire visual reference to continue the approach. The required runway visual range (RVR) is determined by glide-slope geometry: the pilot must see the runway threshold or approach lighting system before descending below DH. The geometric constraint is

[
\mathrm{RVR}_{\mathrm{floor}}(H)=
\max\left(0,\frac{H-50}{\tan(3^\circ)}-1000\right).
]

This curve is smooth and strictly decreasing in DH until it saturates at zero near DH (\approx 102.4) ft. Below that point, glide-slope geometry no longer constrains RVR: visual acquisition at ground level is determined by a different evidence axis that the CAT I package does not contain.

**The kink.** RVR floor falls from 3,770 ft at DH (=300) ft to 336 ft at DH (=120) ft, then reaches zero at DH (\approx 102) ft and remains there. The saturation is not a regulatory choice; it is the geometric point where the active evidence axis changes. Above 102 ft, CAT I visual acquisition is the binding evidence. Below 102 ft, it is not, and the compiler has nothing to say about what is, because the supplied evidence package does not contain it.

**Densification.** Use uniform RVR thresholds over ([0,2400]) ft. Breakpoints grow from 4 at (k=4) to 64 at (k=64), then stabilize: at (k=128) and (k=256), the count remains 64. The 64 breakpoints above saturation correspond to the smooth geometric curve being subdivided by the uniform grid. No additional breakpoints appear below saturation because RVR is identically zero; the flat region absorbs all new grid points without producing new transitions.

The kink at 102.4 ft persists at every (k). It is not a quantization artifact. It is the boundary where the evidence stops speaking.

> *FAA shows that the latent authorization function can be smooth until the evidence itself stops speaking.*

### 2.5 Densification classifies authorization geometry

The three domains together establish the diagnostic as a discriminator, not just a description.

| Domain | Densification signature                                               | Latent regularity                              |
| ------ | --------------------------------------------------------------------- | ---------------------------------------------- |
| Turbo  | Breakpoints grow with (k) and SNR resolution                          | Smooth monotone function                       |
| Ising  | One breakpoint at all (k); spacing-bounded location error             | Genuine structural step                        |
| FAA    | Breakpoints stabilize at kink; flat region absorbs further resolution | Piecewise smooth with evidence-axis transition |

![Figure 2. Three regularity classes — Turbo (smooth control), Ising (genuine step), FAA (kink). Top row: governing curves. Bottom row: densification diagnostics.](figures/fig2_three_classes.png)

The diagnostic fires correctly on all three cases, including the null case, turbo. A method that reported growth for Ising or stability for turbo would not be a discriminator. This one does neither.

**Why this matters.** A coarse permission hierarchy cannot tell whether a threshold is real or merely where the compiler's grid happens to land. The densification experiment answers this empirically. Count stability with spacing-bounded tracking error is a certificate of structural reality. Growing count with resolution is a certificate of artifact. Kink persistence is a certificate of evidence-axis transition.

These first experiments establish the measurement axis of the conservation law. Holding evidence fixed, permission densification shows how a finite hierarchy reads the latent authorization value (A(e)). We now turn to the second axis: what happens when the evidence available to the compiler is hidden, coarsened, or compared with an external regulatory representation. The question is no longer whether the instrument resolves (A(e)), but whether the same object is preserved conservatively under representation change.

### 2.6 Evidence hiding produces conservative permission descent

**Setup.** Two domains with known permission hierarchies. In each, evidence is hidden one gap at a time and the compiler is rerun. The expected result is that permission weakens or holds at each step, with the active blocker identifying the gap that caused the drop.

**ILS occlusion.** Three gaps are used: `ils_signal_integrity` (S), `visual_reference` (V), and `sub_cat1_authorization` (A). Starting from all gaps at the status required for ALR, opening authorization drops permission to REV; opening visual drops to DIA; opening signal drops to REF. Four levels are traversed in theory-predicted order. No reversals occur. *(Figure 3A.)*

**Epic medical-AI occlusion.** Nine gaps are used across the socio-technical taxonomy: (G1) clinical utility, (G2) model specification, (G3) distribution shift, (G4) individual-population scope, (G5) blast radius, (G6) authority/rollback, (G7) reason traceability, (S2) freshness, and (S1) approximation quality. Starting from all gaps at the status required for ALR, opening (G1) drops permission to AEX. The (G)-gaps gate ALR, not AEX, so opening (G2)–(G7) individually does not lower permission further once AEX is already the binding level. Opening (S2) drops AEX to REV. Opening (S1) drops REV to DIA. *(Figure 3B.)*

Bounded and closed remain distinct gap statuses. The occlusion runs start from the status that satisfies the relevant permission requirement in the implemented hierarchy; they do not identify bounded and closed globally.

The occlusion staircase is not a smooth function. It is a piecewise-constant descent governed by the permission hierarchy. The active blocker at each step is the gap specified in the hierarchy definition. The compiler is not making a judgment call; it is reading the requirements. This is the conservation law under evidence hiding: the authorization structure is preserved, while the accessible part of it changes.

![Figure 3. Evidence hiding produces theory-predicted permission descent. (A) ILS: ALR → REV → DIA → REF. (B) Epic: ALR → AEX → REV → DIA, with active blockers annotated.](figures/fig3_occlusion.png)

> *Evidence hiding moves authorization downward exactly at the gaps required by each permission level.*

### 2.7 Projection fidelity exposes the admissibility boundary

**Setup.** Six projection levels are applied to the Epic evidence package, from finest, the full 9-gap taxonomy, to coarsest, a 2-gap representation: evidence quality and evidence scope. Each level merges structurally related gaps into a composite gap. The compiler is run on both the fine and projected evidence packages for all seven induction cases M01–M07. Gap width is

[
|C_{\mathrm{fine}} - C_{\mathrm{projected}}|
]

in permission rank.

**Levels 0–3.** Merging (G1+G2), then (G3+G4), then (G5+G6), produces no change in projected permission. The merges are within the same functional category, and conservative composite-gap semantics preserve the authorization structure. Gap width is 0 at all cases.

**Level 4.** Merging (G7) reason traceability with (S2) freshness into a single `evidence_currency_gap` crosses a structural boundary: (G7) and (S2) are in different parts of the requirement hierarchy. The projected compiler loses the ability to satisfy the AEX requirement independently through each gap. The merged gap now blocks both (G7)'s and (S2)'s contributions. Result: projected permission drops from AEX to REV at all cases. Gap width is 1 at all cases. This is the admissible boundary: the authorization gap has opened, but authorization has weakened, not strengthened. The condition

[
\widehat A^\pi(\pi(e)) \preceq A(e)
]

holds.

**Level 5.** Merging all evidence into two generic gaps, `evidence_quality` and `evidence_scope`, erases the AEX structural requirements from the projected vocabulary. The profile builder can only check whether the merged gaps are open or satisfied. With the merged gaps satisfied in the projection, the compiler returns AEX. Gap width bounces from 1 back to 0.

This is the violation. Not because gap width fell — that would be valid if caused by genuine evidence improvement — but because no genuine evidence improvement occurred. The evidence package is unchanged; only the representation changed. The projection returns a stronger permission than the evidence warrants:

[
\widehat A^\pi(\pi(e)) \npreceq A(e).
]

![Figure 4. Admissible coarsening and structural collapse. (A) Projected permission per case across levels 0–5. (B) Gap width per level — opens at L4 (admissible), collapses at L5 (violation).](figures/fig4_projection.png)

The Level 5 result is not a bad data point. It is the witness that the admissibility condition ([P]) is non-vacuous: a natural-looking, compactness-motivated simplification falls outside the admissible class because it erases the permission skeleton.

> *Coarsening is admissible only while it remains conservative; once projection erases the permission skeleton, the compiler authorizes by representation rather than evidence.*

### 2.8 Regulatory thresholds as samples of the latent authorization structure

Occlusion and projection tested admissibility under representation changes authored inside the compiler. Regulatory correspondence tests the same symmetry against representations the compiler did not author: external standards, guidance, and legal thresholds. We now ask how those external regulatory thresholds relate to the latent authorization function. For each case, we run the compiler on a frozen evidence package constructed from public sources before examining the regulatory standard, then classify the relationship between the compiler output and the regulatory threshold.

**Correspondence classes.** Six relationships are possible:

1. **Exact recovery:** compiler threshold and regulatory threshold identify the same fixed point.
2. **Representation-relative alignment:** compiler and regulator agree under the supplied representation but diverge under hierarchy perturbation.
3. **Same-axis policy margin:** compiler and regulator use the same evidence axis, but regulation introduces a safety margin, tolerance, rounding convention, lighting/equipment condition, or other policy choice on that same axis.
4. **Different evidence axis:** regulation covers a dimension the supplied evidence package does not.
5. **Hierarchy-placement failure:** a real gap exists but is placed at the wrong level in the permission hierarchy.
6. **Outside supplied package:** the compiler is silent because the relevant gap is not in the supplied evidence package.

**Results.** *(Figure 5.)*

**FAA CAT I.** The compiler derives the RVR-floor-vs-DH curve from glide-slope geometry without using the FAA CAT I threshold. At the standard CAT I decision height DH (=200) ft, the frozen geometric model gives

$$
\mathrm{RVR}_{\mathrm{floor}}(200) = \frac{200-50}{\tan(3^\circ)}-1000 \approx 1862\ \mathrm{ft}.
$$

The corresponding FAA CAT I minimum for suitably equipped runways is RVR 1,800 ft. The difference is 62 ft, or approximately 3.4% of the regulatory value. The curve crosses 1,800 ft at DH (\approx 196.7) ft. This is therefore not exact recovery. It is independent-route, same-axis policy-margin convergence: the evidence-derived geometry lands on the same visual-range axis and within the regulatory bin, but the published threshold contains a policy/rounding/equipment convention not present in the supplied geometric package.

This residual is useful rather than embarrassing. Had the constants been tuned after seeing the regulation, the roll-bar offset would have been chosen near 1,062 ft rather than the frozen 1,000 ft. The 1,862 ft prediction is evidence that the geometric model was fixed before regulatory comparison, while the 62 ft discrepancy marks the non-forced component of the boundary.

**3GPP 0.10/0.02.** Under the frozen hierarchy, the compiler aligns with the 10% and 2% BLER thresholds. Under 59 hierarchy perturbations, recovery of 0.10 falls to 5.1% and recovery of 0.02 falls to 3.4%, with zero recovery in the structured perturbation families. The alignment is representation-relative: the thresholds are not hierarchy-independent ridges of the latent function.

**FDA deployment gaps.** The gap list induced from documented AI deployment failures, including Epic, Optum, PredPol, COMPAS, and Watson, recovers FDA AI/ML action-plan categories as same-axis policy obligations. The FDA guidance specifies evidence failures that the compiler induces from incident records. This is a same-axis policy-margin correspondence from overlapping evidence, not independent derivation.

**ECOA reason traceability.** The compiler induces (G7), reason traceability, from credit and adverse-action failures. ECOA Regulation B requires adverse-action notices with specific reasons. The legal requirement and the induced gap are structurally identical. Exact recovery.

**FAA CAT II/III.** CAT II requires a different evidence axis not present in the CAT I package. CAT III depends on autoland, fail-operational systems, aircraft equipment, and operator qualification. The compiler is silent on these axes because the supplied package has nothing to say about them. Different evidence axis / outside supplied package.

**Amazon recruiting, held out.** Gap (G2), model specification, is real and present in the induced package. The disagreement is a hierarchy-placement failure, not a missing gap: the gap was identified, but the hierarchy placed it below AEX, allowing AEX to proceed without closing it.

![Figure 5. Regulatory thresholds as samples of the latent authorization structure — seven cases classified by correspondence type.](figures/fig5_regulatory.png)

---

## 3. The Conservation Law

The results above are finite observations of one order-theoretic object, (A(e)). This section states that object as the conserved quantity of incomplete evidence. The paper has two experimental halves because a finite authorization system can fail to see that object along two independent axes: the permission grid can be too coarse, or the evidence representation can be too coarse. Permission densification refines the first axis. Occlusion, projection, and regulatory comparison probe the second. The conservation law is that admissible transformations along either axis may weaken, refine, or relabel authorization, but they may not create permission unsupported by the compatible worlds.

The proof spine follows that architecture. The lower-approximation theorem says how finite permission grids measure (A(e)). The coarsening, refinement, and invariance theorems say which evidence-side transformations preserve it. The two-axis convergence theorem states the bridge: when permission refinement and evidence refinement are both resolving, finite implemented compilers converge to the same conserved object. The proofs are deferred to Appendix A; the body states each claim with its hypotheses, failure mode, and experimental witness.

We use one order convention throughout. Let (\mathcal A) be a permission lattice, ordered from weaker to stronger permissions. We write

[
p \preceq r
]

to mean that permission (p) is no stronger than permission (r). Thus, in the examples,

[
\mathrm{REF} \preceq \mathrm{DIA} \preceq \mathrm{REV} \preceq \mathrm{AEX} \preceq \mathrm{ALR}.
]

Meets (\bigwedge) are greatest lower bounds in this order: the strongest permission no stronger than every element in a set. Joins (\bigvee) are least upper bounds. We assume the meets and joins used below exist.

### 3.1 The latent authorization function

Let (W) be the set of possible worlds. A world contains the full state relevant to authorization: the actual channel behavior, the true approximation errors, the deployment setting, the oversight structure, the available reason trace, or any other fact that could make an action sound or unsound.

Let (E) be a space of evidence states, and let

[
q:W\to E
]

be the evidence map. The evidence map records only what the evidence package can observe. For (e\in E), define the evidence fiber

[
F(e)=\{w\in W:q(w)=e\}.
]

This is the set of worlds still compatible with evidence (e).

Let

[
a:W\to\mathcal A
]

be the world-level authorization function, where (a(w)) is the strongest action sound in world (w).

**Definition 1. Latent authorization function.** The latent authorization function induced by evidence map (q) is

[
A(e)=\bigwedge_{w\in F(e)}a(w).
]

Thus (A(e)) is the strongest permission sound for every world still compatible with evidence (e). A permission (p) is sound given evidence (e) exactly when

[
p\preceq A(e).
]

The associated upper endpoint is

[
B(e)=\bigvee_{w\in F(e)}a(w),
]

the strongest permission consistent with at least one world compatible with (e). The interval

[
[A(e),B(e)]
]

is the authorization gap. The lower endpoint is what is sound for every compatible world. The upper endpoint is what remains possible in some compatible world. A sound compiler must return the lower endpoint or a lower approximation to it.

This definition is the point of the paper. Authorization is not attached to an evidence state by averaging, voting, or matching a regulatory label. It is the meet of the world-level authorizations over the worlds the evidence has not ruled out.

### 3.2 Finite permission hierarchies are lower approximations

A finite compiler does not observe (A(e)) directly. It observes (A(e)) through a finite permission grid.

Let

[
P_k=\{p_1\prec p_2\prec \cdots \prec p_k\}\subseteq\mathcal A
]

be a finite permission grid. Define the floor of (x\in\mathcal A) with respect to (P_k) as

[
\lfloor x\rfloor_{P_k}=
\max\{p\in P_k:p\preceq x\},
]

with the bottom permission returned if the set is empty. The compiler output under grid (P_k) is

[
C_k(e)=\lfloor A(e)\rfloor_{P_k}.
]

A grid sequence ((P_k)) **resolves (\mathcal A) from below** if, for every (x\in\mathcal A),

[
\bigvee_k \lfloor x\rfloor_{P_k}=x.
]

**Theorem 1. Finite lower-approximation law.** For every evidence state (e):

1. **Soundness.** For every finite grid (P_k),

   [
   C_k(e)\preceq A(e).
   ]

2. **Monotone grid refinement.** If (P_k\subseteq P_{k+1}), then

   [
   C_k(e)\preceq C_{k+1}(e)\preceq A(e).
   ]

3. **Dense-grid convergence.** If ((P_k)) resolves (\mathcal A) from below, then

   [
   C_k(e)\nearrow A(e).
   ]

For non-nested grids, pointwise monotonicity need not hold, but convergence still follows whenever the floor error tends to zero. Proof: Appendix A.1.

This theorem is the formal object measured in the densification experiments. Turbo shows the smooth-control case: breakpoints grow because the finite grid is subdividing a monotone curve. Ising shows the fixed-threshold case: the breakpoint count stays one and the location error is bounded by grid spacing. FAA shows the evidence-axis transition: densification tracks the smooth part until the supplied evidence axis saturates.

The finite staircase is therefore not the ontology. It is the finite-grid observation of (A(e)).

### 3.3 Coarsening may weaken authorization but may not strengthen it

Evidence representations can be coarsened. Let

[
\pi:E\to\bar E
]

be a projection from fine evidence states to coarser evidence states. The projected evidence fiber is

[
F_\pi(\bar e)=\{w\in W:\pi(q(w))=\bar e\}.
]

The semantic authorization function induced by the projected evidence is

$$
 A^\pi(\bar e)=\bigwedge_{w\in F_\pi(\bar e)}a(w) = \bigwedge_{e'\in \pi^{-1}(\bar e)}A(e').
$$

Semantic coarsening is always conservative:

[
A^\pi(\pi(e))\preceq A(e).
]

Real implementations, however, need not compute the semantic meet over the projected fiber. A projected profile may use a new gap vocabulary, a new requirement map, or a simplified rule for composite gaps. Let

[
\widehat A^\pi:\bar E\to\mathcal A
]

denote the implemented authorization function under the projected representation.

**Definition 2. Authorization-admissible implemented projection.** An implemented projection ((\pi,\widehat A^\pi)) is authorization-admissible if

[
\tag{P}
\widehat A^\pi(\pi(e))\preceq A(e)
\quad
\text{for all }e\in E.
]

Equivalently,

[
\widehat A^\pi(\bar e)\preceq A^\pi(\bar e)
\quad
\text{for all }\bar e\in\bar E.
]

This is the admissibility fence. Coarsening may hide evidence and weaken authorization, but it may not create stronger permission.

**Definition 3. Meet-exact implemented projection.** An implemented projection is meet-exact if

[
\widehat A^\pi(\bar e)=A^\pi(\bar e)
\quad
\text{for every }\bar e\in\bar E.
]

Meet-exactness is stronger than authorization-admissibility. Authorization-admissibility guarantees soundness. Meet-exactness guarantees that the implementation computes the strongest sound permission available in the projected representation.

**Theorem 2. Conservative coarsening law.** If ((\pi,\widehat A^\pi)) is authorization-admissible, then for every finite permission grid (P_k),

[
C_k^\pi(\pi(e))\preceq C_k(e)
]

for all (e\in E), where

[
C_k^\pi(\pi(e))=\lfloor \widehat A^\pi(\pi(e))\rfloor_{P_k}.
]

Proof: Appendix A.2.

The Level 5 projection in §2.7 is the non-vacuity witness for (P). The evidence package has not improved; only the representation has changed. Yet the projected compiler returns AEX where the fine representation exposes that AEX is not genuinely supported:

[
\widehat A^\pi(\pi(e))\npreceq A(e).
]

The violation is not that the gap widens. Widening is allowed. The violation is that authorization comes back through representation collapse.

### 3.4 Resolving refinement recovers the latent authorization function

Conservatism prevents spurious authorization. It does not by itself recover the latent authorization function. Recovery requires refinement.

Let

[
\pi_m:E\to E_m
]

be a sequence of evidence projections.

**Definition 4. Refining sequence.** The sequence ((\pi_m)) is refining if each later projection separates at least as much evidence as the previous one. Equivalently, for each (m) there exists a map

[
\rho_m:E_{m+1}\to E_m
]

such that

[
\pi_m=\rho_m\circ \pi_{m+1}.
]

For a fixed (e), define its projected equivalence class at level (m) as

[
[e]_m=\{e'\in E:\pi_m(e')=\pi_m(e)\}.
]

Refinement is exactly the condition

[
[e]_{m+1}\subseteq [e]_m.
]

**Definition 5. Resolving sequence.** A refining sequence ((\pi_m)) is resolving at (e) if, for every permission (p\prec A(e)), there exists (m_0) such that for all (m\geq m_0) and all (e'\in [e]_m),

[
p\preceq A(e').
]

Equivalently, beyond some resolution, the projected fiber around (e) contains no evidence state whose latent authorization falls below any chosen permission strictly weaker than (A(e)). The sequence is resolving if it is resolving at every (e\in E).

For finite permission lattices, this condition has a simpler form. If (A(e)) has an immediate predecessor (p^-), resolving at (e) means that eventually every (e'\in [e]_m) satisfies

[
p^-\preceq A(e').
]

The threshold formulation is needed for dense or continuous permission lattices; the finite experiments instantiate its finite-lattice version.

Define the semantic projected authorization at level (m) by

$$
 A^{\pi_m}(\pi_m(e)) = \bigwedge_{e'\in [e]_m}A(e').
$$

This theorem concerns the semantic meet over projected evidence fibers, not the output of an implemented compiler. Implemented convergence requires the additional bridge condition in §3.5.

**Theorem 3. Semantic convergence under resolving refinement.** If ((\pi_m)) is refining and resolving at (e), then

[
A^{\pi_m}(\pi_m(e))\nearrow A(e).
]

Proof: Appendix A.3.

The resolving hypothesis is not decorative. If a projection sequence is non-resolving, the semantic projected meet can plateau strictly below (A(e)). In that case a conservative implementation cannot in general become tight to (A(e)); admissibility is the right property, not convergence.

### 3.5 Two-axis convergence requires an explicit bridge condition

This section is the formal reason the paper is one result rather than two coupled results. There are two independent approximation axes, but both are approximations to the same latent authorization value (A(e)).

1. **Permission-grid refinement:** the evidence representation is fixed, but the finite permission grid (P_n) becomes denser. This is the axis exercised by the turbo, Ising, and FAA densification experiments.
2. **Evidence-projection refinement:** the permission scale is fixed or separately controlled, but the evidence representation (\pi_m:E\to E_m) becomes more informative. This is the axis governed by Theorem 3 and exercised empirically by occlusion and projection fidelity.

The two axes can be composed, but they are not interchangeable. Permission densification cannot recover evidence distinctions erased by a non-admissible projection. Evidence refinement cannot compensate for a permission grid that has no resolving lower approximation. The bridge condition below states when an implementation is tight enough on the evidence side for the two finite readings to converge to the same conserved object.

**Definition 6. Asymptotically meet-exact implementation along a resolving refinement.** Let ((\pi_m)) be a refining evidence-projection sequence that is resolving at (e), and let

[
\widehat A_m:E_m\to\mathcal A
]

be the implemented authorization function at resolution (m). The implemented sequence ((\pi_m,\widehat A_m)) is asymptotically meet-exact at (e) if it satisfies both conditions below.

First, it is conservative relative to the semantic projected meet at every resolution:

[
\widehat A_m(\pi_m(e))
\preceq
A^{\pi_m}(\pi_m(e))
\quad \text{for all }m.
]

Second, it becomes tight to the latent authorization value in the limit:

[
\bigvee_{M\geq 1}
\bigwedge_{m\geq M}
\widehat A_m(\pi_m(e))=
A(e).
]

Equivalently, the eventual lower envelope of the implemented outputs converges to (A(e)) from below. In an order-dense lattice this is equivalent to the threshold form: for every (p\prec A(e)), eventually

[
p\preceq \widehat A_m(\pi_m(e)).
]

In a finite chain with (A(e)\in\mathcal A), it collapses to eventual exactness:

[
\widehat A_m(\pi_m(e))=A(e)
]

for all sufficiently large (m). This definition is intended only along resolving refinements. For a non-resolving sequence, the semantic projected meet may remain strictly below (A(e)), so the two conditions above may be unsatisfiable. Proof of the equivalences: Appendix A.4.

**Theorem 4. Analytical joint implemented convergence under resolving, asymptotically meet-exact refinement.** This theorem is an analytical bridge for two-axis refinement. It is not directly exercised by the experiments in §2. Let ((\pi_m)) be refining and resolving at (e). Let ((\pi_m,\widehat A_m)) be asymptotically meet-exact at (e). Then the implemented projected authorizations converge to (A(e)) from below in the order-envelope sense:

$$
\bigvee_{M\geq 1} \bigwedge_{m\geq M} \widehat A_m(\pi_m(e)) = A(e).
$$

Now let (P_n) be a permission-grid sequence resolving (\mathcal A) from below, and define the two-axis compiler output

$$
 C_{m,n}(e) = \left\lfloor \widehat A_m(\pi_m(e))\right\rfloor_{P_n}.
$$

Then

[
C_{m,n}(e)\to A(e)
]

from below along any cofinal refinement of both axes: for every permission (p\prec A(e)), there exist (m_0,n_0) such that for all (m\geq m_0) and (n\geq n_0),

[
p\preceq C_{m,n}(e)\preceq A(e).
]

If the implemented evidence projections and permission grids are nested, this convergence is monotone. Otherwise, it is joint convergence from below without pointwise monotonicity. Proof: Appendix A.4.

The current experiments validate the two axes of Theorem 4 separately rather than the full joint limit. Permission densification validates finite-grid convergence to a fixed authorization value (§§2.2–2.5). Occlusion and projection fidelity validate the admissibility fence and expose its failure (§§2.6–2.7). Regulatory correspondence then asks how external standards sample the same object (§2.8). This separation is deliberate: the first block calibrates the finite instrument for reading (A(e)); the second block tests the admissible transformations under which that same (A(e)) is conserved. A future experiment that coarsens an evidence vocabulary and then refines it back toward the full representation would exercise Theorem 4 directly.

### 3.6 Evidence-side representation invariance

The preceding laws are order-theoretic. They use fibers, meets, floors, refinement, and conservatism. They do not depend on a particular numerical metric on evidence space.

A metric can change the scale on which evidence distance is plotted. It can change whether a curve looks steep or flat. It cannot change authorization unless it changes the evidence fibers, the refinement preorder, or the permission order.

**Definition 7. Authorization-equivalent evidence representations.** Two evidence representations

[
q_1:W\to E_1
\quad\text{and}\quad
q_2:W\to E_2
]

are authorization-equivalent if they induce the same evidence fibers up to relabeling. That is, there exists a bijection

[
\psi:q_1(W)\to q_2(W)
]

such that

[
q_2=\psi\circ q_1.
]

Equivalently,

[
q_1(w)=q_1(w')
\quad\text{if and only if}\quad
q_2(w)=q_2(w')
]

for all worlds (w,w').

**Theorem 5. Evidence-representation invariance.** If (q_1) and (q_2) are authorization-equivalent, then their latent authorization functions agree up to relabeling:

[
A_2(\psi(e))=A_1(e).
]

Proof: Appendix A.5.

This is the precise metric-invariance claim. If two metrics or divergences induce the same evidence states, the same fibers, and the same refinement preorder, then they induce the same latent authorization function. They may rescale distances along a path, but they do not alter the authorization boundary. Supplementary §S3 gives the empirical witness used here: alternate Ising and turbo functionals change the ruler but preserve the authorization ordering.

Metrics that merge permission-relevant distinctions, reverse refinement order, or create spurious reachability are not equivalent representations. They are different evidence maps, and they must satisfy authorization-admissibility if they are to be used as coarsenings.

A separate, weaker invariance holds for relabeling permissions. If (\phi:\mathcal A\to\mathcal A') is an order isomorphism and (a'(w)=\phi(a(w))), then

[
A'(e)=\phi(A(e)).
]

Proof: Appendix A.6. Permission relabeling is not the main metric claim. It says only that changing the names or scale of permission values preserves the structure when the order is unchanged.

### 3.7 Regularity classes of (A(e))

The latent authorization function need not be globally smooth. The conservation law does not say that every staircase hides a smooth curve. It says that finite permission outputs approximate the same latent object under admissible transformations.

The regularity of (A(e)) depends on the evidence geometry.

**Smooth regions.** When the action-relevant failure functional varies continuously along a quantitative evidence path, (A(e)) is smooth or piecewise smooth. Turbo-coded communication is this case over the tested SNR range: the independent-bit BLER reference curve is monotone in SNR, and finite breakpoints are threshold crossings of a smooth curve.

**Structural steps.** When authorization turns on a fixed threshold, densification does not smooth the staircase away. It localizes the step. Ising belief propagation is this case: the authorization boundary is the maximum per-variable total variation error, and the breakpoint tracks (TV_{\max}) within one grid spacing.

**Kinks and evidence-axis transitions.** When the active evidence axis changes, (A(e)) may be continuous but non-smooth. FAA visual acquisition is this case: the visual RVR constraint varies smoothly until it saturates near 102 ft decision height. Below that point, the supplied visual evidence axis no longer governs the authorization question.

A fourth class is predicted by the framework but not demonstrated here.

**Structural gates.** Some obligations are categorical rather than quantitative. Reason traceability is the canonical candidate. The question is not how much explanatory evidence exists in the abstract, but whether the decision pipeline contains an auditable path from inputs and model output to the required reasons. Such gates may appear as discontinuities in (A(e)), not as artifacts of a coarse permission grid.

ECOA demonstrates that the G7 reason-traceability gate recovers the legal requirement at the supplied adverse-action state, a Theorem-6 exact-recovery statement. It does not demonstrate the structural-gate regularity class, which concerns the behavior of (A(e)) as a discontinuous function along a varying evidence axis and remains a predicted class.

Smoothness is not the law. The law is that admissible transformations preserve the authorization structure: smooth regions remain smooth, steps track fixed thresholds, kinks persist at evidence-axis transitions, and inadmissible projections are exposed by spurious authorization.

### 3.8 Exact recovery is the zero-gap boundary case

The representation theorem is the zero-gap case of the latent-function framework.

**Theorem 6. Exact recovery iff the fiber is authorization-constant.** For an evidence state (e), the following are equivalent:

1. (a(w)) is constant over (F(e));
2. (A(e)=B(e));
3. the evidence (e) determines a unique authorization value.

Proof: Appendix A.7.

When the gap collapses, the semantic compiler recovers the unique correct authorization:

[
A(e)=B(e).
]

A finite compiler recovers it exactly if (A(e)\in P_k). Otherwise it returns the lower grid approximation

[
\lfloor A(e)\rfloor_{P_k},
]

which converges to (A(e)) under permission densification.

When (a) is non-constant on the fiber, no compiler reading only (e) can recover the world-specific distinction. Any algorithm receiving only (e) must return one value for every world in (F(e)). If it returns a permission above (A(e)), it is unsound for at least one compatible world. If it returns (A(e)), it is sound but conservative for worlds whose true authorization is stronger. The limitation is representational, not computational.

ECOA reason traceability is exact recovery in this sense: within the supplied adverse-action representation, the reason-traceability gate and the legal reason requirement identify the same authorization-constant boundary. FAA CAT I is deliberately not classified as exact recovery after the arithmetic check in §2.8: the supplied geometry determines a same-axis floor of approximately 1,862 ft at DH (=200) ft, while the published CAT I threshold is 1,800 ft under the relevant lighting/equipment convention. That residual is the policy/rounding margin, not a collapsed fiber. 3GPP is not exact recovery under perturbation: the frozen BER/BLER hierarchy aligns with 0.10 and 0.02, but those values are not invariant under admissible hierarchy changes. CAT II is different again: the supplied visual axis saturates, so the relevant fiber cannot collapse without a different evidence map.

### 3.9 Order- and source-invariance

The remaining invariances are consequences of the same structure.

**Corollary 1. Order-invariance of gap induction.** Suppose a fixed corpus determines a finite set (G^\star) of visible, policy-relevant failure modes. Suppose the induction procedure adds a gap whenever a processed case exposes a permissive disagreement that is blocked by that gap, never removes gaps, and eventually processes every case. Then the final induced gap set is (G^\star), independent of the order in which cases are processed. Proof: Appendix A.8.

The preconditions matter. If the corpus does not expose a failure, induction cannot recover it. If policy does not care about a visible failure, it is not a permission-relevant gap. These are not weaknesses of the theorem; they define its domain.

**Corollary 2. Source-invariance of compiler soundness.** For fixed evidence state (e), permission hierarchy (P), and gap-requirement map (R), the compiler output is independent of the source that proposed the gaps. Proof: Appendix A.8.

The LLM, expert, regulator, or incident report is a proposal mechanism. The compiler is the type checker. Soundness is conditional on the written evidence contract; it is not inherited from the authority of the source.

## 4. Scope and Limits

### 4.1 The law does not choose the evidence map

(A(e)) is defined after an evidence representation is supplied. If the supplied representation erases evidence relevant to the authorization question, the compiler operates on incomplete information — not incomplete in the authorization-gap sense, but incomplete in the sense that the fiber (F(e)) is larger than it needs to be. Level 5 shows this directly: a representation that conflates structurally distinct gaps can make the projected evidence language unable to express the blocker that made a stronger permission unsound.

Choosing the right evidence map is not a task the compiler can perform. It requires domain knowledge about which failures are distinguishable from the evidence and which are not.

### 4.2 The law does not choose the permission hierarchy

A real gap can be placed at the wrong level. The Amazon recruiting case is the example: (G2), model specification, was present in the evidence package and the compiler induced it from the deployment record. But the hierarchy placed AEX below the (G2) requirement threshold: (G2) open did not block AEX. The compiler would have returned AEX given the same evidence and hierarchy.

This is a hierarchy-placement failure, not a missing gap. The evidence-forced component of authorization was identified correctly. The policy-supplied permission hierarchy placed a permission level too high relative to the evidence it should require. The law distinguishes these; a compliance audit cannot make the distinction without running the compiler on the actual evidence package.

### 4.3 Not all regulatory matches have equal independence

FAA CAT I is an independent-route, same-axis convergence: the compiler derives an RVR value from glide-slope geometry without using FAA category thresholds. The frozen geometric value at DH (=200) ft is approximately 1,862 ft, while the regulatory minimum is 1,800 ft for suitably equipped runways. That is not exact recovery. It is a same-axis policy/rounding margin whose independence is stronger than the shared-corpus cases but whose equality claim is weaker than the zero-gap case.

FDA and ECOA correspondences have different independence profiles. FDA is partially shared-corpus: the compiler's gap list is induced from deployment failures, and regulatory guidance was written partly in response to documented AI failures. The correspondence is real but not fully independent; the regulator and the compiler drew from overlapping incident histories. ECOA reason traceability is exact recovery on the supplied adverse-action representation: the induced G7 gate and the legal reason requirement identify the same boundary. Its independence claim is weaker than FAA CAT I, however, because the compiler could induce G7 only after the corpus exposed reason traceability as a failure mode.

3GPP is representation-relative. The compiler aligns under the frozen hierarchy but diverges under perturbation. The alignment is real within the supplied representation; it is not a hierarchy-independent structural feature of the latent function.

### 4.4 Outside-package obligations remain real

Cybersecurity vulnerabilities, UI labeling requirements, disparate impact at the community level, and upstream data accuracy are real failure modes for deployed AI systems. The compiler is silent on these axes when the supplied evidence package contains no gap that speaks to them.

Silence is a result, not permission. The compiler's silence means: "I cannot authorize or refuse on this dimension with the evidence you have given me." It does not mean the dimension is irrelevant. An outside-package obligation is a real obligation; the compiler's inability to speak to it is a property of the evidence package, not of the world.

### 4.5 The compiler does not replace judgment

The compiler separates what evidence forces from what policy adds. Evidence forces the authorization ceiling: the strongest level sound for all compatible worlds. Policy may set the actual permission level below this ceiling, as conservatism, or incorrectly above it, as spurious authorization. The compiler identifies the evidence-forced ceiling. The decision about whether to act at or below that ceiling is an institutional judgment.

> Incomplete evidence conserves authorization structure only inside admissible representations. The contribution is not that all boundaries are forced, but that the evidence-forced component can be identified, approximated, refined, and separated from policy and representation choice.

---

## Methods

### M1 Compiler implementation

The authorization compiler is implemented in Rust with Python bindings (`noethers_turnstile`). Inputs are an evidence package, with named gaps and statuses; a permission hierarchy; and a gap-requirement map per permission level.

Gap statuses are ordered

[
\mathrm{open}\prec\mathrm{bounded}\prec\mathrm{closed}.
]

A requirement cell specifies the minimum status sufficient for that gap at that permission level. Thus a gap with observed status (s) satisfies a requirement (r) exactly when (r\preceq s). A requirement of `open` is therefore vacuous: every status satisfies it. A requirement of `bounded` is satisfied by `bounded` or `closed`; a requirement of `closed` is satisfied only by `closed`.

The compiler traverses the permission hierarchy from strongest to weakest and returns the first level whose gap requirements are all satisfied. If no non-bottom level's requirements are satisfied, it returns the bottom permission, REF. All computation is deterministic given the evidence state, permission hierarchy, and requirement map. The source that proposed a gap is not an input to the compiler.

Source: `python/noethers_turnstile/__init__.py`, `python/noethers_turnstile/_turnstile.so` (Rust extension, Python 3.10).

### M2 Permission densification

(P_k) is constructed as either uniform or log-uniform thresholds over the relevant evidence axis:

* Uniform: (k) evenly spaced thresholds from (t_{\min}) to (t_{\max}).
* Log-uniform: (k) thresholds spaced evenly on log scale, used for error rates spanning decades.

The mathematical compiler output is the lattice element

[
C_k(e)=\lfloor A(e)\rfloor_{P_k}.
]

For plotting and breakpoint counting, this lattice element is represented by the normalized rank score

[
s_k(e)=\frac{\#\{p\in P_k:p\preceq A(e)\}}{|P_k|}.
]

The score (s_k) is an order-preserving relabeling of (C_k) under the threshold-count representation of the finite chain (§3.6). No authorization claim depends on the normalization.

Breakpoints are counted as values of the swept axis where (s_k) changes. The swept axes are: SNR for turbo, decision height (DH) for FAA, and the authorization threshold (\tau) for Ising. Ising is therefore a threshold sweep against a fixed computed pair ((TV_{\mathrm{mean}},TV_{\max})), not a sweep over multiple Ising worlds. Location error is the absolute distance from the first grid threshold at or above the true structural threshold.

Source: `examples/conservation/run_densification.py`.

### M3 Turbo experiment

BER data are digitized from Berrou (1993), using a 12-point grid from (-1.0) to (5.0) dB SNR. To evaluate denser SNR grids, the digitized BER curve is interpolated piecewise linearly on the (\log_{10}\mathrm{BER}) scale as a function of SNR; the interpolated BER is then transformed to the independent-bit BLER reference curve

[
\mathrm{BLER}_{\mathrm{ref}} = 1-(1-\mathrm{BER})^L,
]

with block length

[
L=65{,}536\ \text{bits}.
]

The same interpolation rule is used for the 61-point and 1,952-point SNR sweeps. This is not asserted to be the measured turbo-code BLER law; turbo decoding creates correlated block failures. The curve is used as a reference model for mean-to-block amplification.

Permission hierarchy: REFUSE when (\mathrm{BLER}>0.10); HOLD when (\mathrm{BLER}\leq 0.10); TRANSMIT_MONITORED when (\mathrm{BLER}\leq 0.02); TRANSMIT when (\mathrm{BLER}\leq 0.001). Log-uniform BLER thresholds are drawn over ([10^{-4},1.0]). SNR-resolution check: fix (k=256) permission thresholds and vary the SNR grid from 61 to 1,952 points.

Source: `examples/conservation/run_permissivity_path.py`, `examples/conservation/run_densification.py`.

### M4 Ising experiment

A (6\times 6) Ising grid is evaluated at coupling (\beta=0.44). The graph is the open-boundary square lattice with uniform ferromagnetic nearest-neighbor coupling and zero external field. No random couplings are drawn, so no seed is required.

Exact marginals are computed by full enumeration over (2^{36}) states via exact inference. BP marginals are computed by synchronous loopy BP with 100 iterations and convergence threshold (10^{-6}). Per-variable TV is

[
\frac{1}{2}\sum_x |p_{\mathrm{BP}}(x)-p_{\mathrm{exact}}(x)|.
]

Mean TV is (0.2231); max TV is (0.3338). Uniform (\tau)-grids are drawn over ([0,0.50]). The densification axis is (\tau), the authorization tolerance; the Ising model itself is fixed for the reported run.

Source: `examples/inference/ising/`, `examples/conservation/run_densification.py`.

### M5 FAA experiment

Glide slope is 3° to runway threshold. Decision height is altitude above touchdown zone. RVR floor is

[
\max\left(0,\frac{H-50}{\tan(3^\circ)}-1000\right),
]

where (H) is decision height in feet. Saturation occurs at

[
H_{\mathrm{sat}}
=
\mathrm{TCH}+d_{\mathrm{rollbar}}\tan(3^\circ)
\approx 102.4\ \mathrm{ft},
]

where TCH is 50 ft and (d_{\mathrm{rollbar}}=1000) ft. At DH (=200) ft the frozen geometry gives

[
\mathrm{RVR}_{\mathrm{floor}}(200)\approx 1862\ \mathrm{ft}.
]

The curve crosses RVR (=1800) ft at DH (\approx 196.7) ft. Uniform RVR thresholds are drawn over ([0,2400]) ft.

Source: `examples/ils/geometry.py`, `examples/conservation/run_densification.py`.

### M6 Occlusion sweeps

ILS uses three gaps: `ils_signal_integrity` (S), `visual_reference` (V), and `sub_cat1_authorization` (A). The requirement matrix below gives the minimum status required at each permission level.

| Permission | S: `ils_signal_integrity` | V: `visual_reference` | A: `sub_cat1_authorization` |
| ---------- | ------------------------- | --------------------- | ---------------------------- |
| ALR        | closed                    | closed                | closed                       |
| REV        | closed                    | closed                | open                         |
| DIA        | closed                    | open                  | open                         |
| REF        | open                      | open                  | open                         |

Opening authorization therefore drops ALR to REV; opening visual reference drops REV to DIA; opening signal integrity drops DIA to REF.

Epic uses nine gaps: S1, S2, and G1–G7. The table records the minimum status required for each permission level in the implemented hierarchy used for §2.6 and §2.7.

| Permission | S1 approximation quality | S2 freshness | G1 clinical utility | G2 model specification | G3 distribution shift | G4 individual-population scope | G5 blast radius | G6 authority/rollback | G7 reason traceability |
| ---------- | ------------------------ | ------------ | ------------------- | ---------------------- | --------------------- | ------------------------------ | --------------- | --------------------- | ---------------------- |
| ALR        | closed                   | closed       | closed              | closed                 | closed                | closed                         | closed          | closed                | closed                 |
| AEX        | closed                   | bounded      | open                | open                   | open                  | open                           | open            | open                  | open                   |
| REV        | bounded                  | open         | open                | open                   | open                  | open                           | open            | open                  | open                   |
| DIA        | open                     | open         | open                | open                   | open                  | open                           | open            | open                  | open                   |
| REF        | open                     | open         | open                | open                   | open                  | open                           | open            | open                  | open                   |

The starting state sets all gaps to the status required for ALR. Gaps are opened in sequence: G1, G2, G3, G4, G5, G6, G7, S2, S1. Bounded and closed remain distinct statuses; the experiment uses the status required by the hierarchy rather than identifying the two globally.

In the Epic hierarchy, REF is the structural bottom and fallback level. The reported Epic requirements do not force REF under this occlusion sequence because DIA is already satisfied when all gaps are open; this differs from ILS, where signal-integrity failure forces descent below DIA to REF.

Source: `examples/conservation/run_occlusion_sweep.py`.

### M7 Projection fidelity

Six projection levels are used:

* L0: all 9 gaps, full taxonomy.
* L1: merge G1+G2, clinical efficacy.
* L2: merge G3+G4, population generalization.
* L3: merge G5+G6, deployment safety.
* L4: merge G7+S2, evidence currency.
* L5: merge S1+S2 into evidence quality; merge G1–G7 into evidence scope.

Levels L0–L5 are distinct coarsenings for the projection-fidelity experiment; they are not asserted to form a nested refining sequence in the sense of Definition 4. In particular, S2 is merged with G7 at L4 and with S1 at L5.

For L0–L4, composite-gap semantics are conservative. The observed status of a composite gap is the meet, i.e. the weakest status, of its component statuses under

[
\mathrm{open}\prec\mathrm{bounded}\prec\mathrm{closed}.
]

At each permission level, the composite requirement is the join, i.e. the strongest minimum requirement, among the component requirements inherited from the fine hierarchy. Thus a merged gap is satisfied only when every component gap would have satisfied its own fine-level requirement. This is the rule that makes L4 admissible: merging G7 with S2 can only make the projected compiler more conservative, because the merged evidence-currency gap must satisfy the stricter inherited requirement.

L5 intentionally uses the collapsed two-gap profile builder rather than the inherited conservative map. Its generic `evidence_quality` and `evidence_scope` requirements erase the AEX skeleton present in the fine hierarchy. This is why L5 is the non-vacuity witness for admissibility: the projected vocabulary is compact, but the implemented authorization function is no longer guaranteed to satisfy

[
\widehat A^\pi(\pi(e))\preceq A(e).
]

The admissibility check is applied for each case at each level.

Source: `examples/conservation/run_projection_fidelity.py`.

### M8 Blind audit protocol

For each regulatory case: first freeze evidence inputs from public sources without examining the target standard; then run the compiler; then record output; then open the regulatory document; then classify correspondence. No target leakage: compiler output is recorded before regulatory comparison in all cases.

The ILS geometry derivation, Epic/FDA gap induction, 3GPP hierarchy construction, ECOA reason-traceability induction, and Amazon held-out classification were all completed before the corresponding regulatory or incident comparison was used for scoring. Amazon was not used to induce the taxonomy; it was held out to test hierarchy placement after the G2 gap already existed.

---
## Supplementary Material

### S1 Full regulatory correspondence matrix

Presented in compressed form in §2.8; full audit table in `docs/provenance.md`.

There are 76 gap-status assignments across induction cases M01–M07 and audit/held-out cases H02–H04: 51 sourced to public documents, 12 assumed-conservative, 7 assumed-anti-conservative, and 6 by construction. The non-consecutive held-out labels are historical audit-trail labels rather than an implied missing result: H01 was an internal pilot and is excluded from the reported matrix; H02 is the FDA deployment-gap audit; H03 is the ECOA adverse-action/reason-traceability audit; H04 is Amazon recruiting. Sensitivity analysis: H04 S2 status is reported with two runs, S2=bounded (\to) AEX and S2=open (\to) REV. Full audit trail appears in `docs/provenance.md`.

### S2 3GPP perturbation experiment

59 hierarchies are tested: 5 granularity levels, 4 offsets, and 50 random perturbations. Each hierarchy assigns different numerical values to the BLER thresholds while preserving ordering structure. Recovery of 0.10: 3/59, or 5.1%. Recovery of 0.02: 2/59, or 3.4%. Structured families show zero recovery. Under the frozen hierarchy, both thresholds align; under perturbation, they do not. Conclusion: representation-relative alignment, not hierarchy-independent recovery.

Source: `examples/inference/register2/turbo/experiment_a_stability.py`.

### S3 Metric invariance

Four functionals on the same Ising TV distribution are tested: F1, mean TV; F2, median TV; F3, p75 TV; and F4, max TV. Tested at

[
\beta\in{0.20,0.30,0.40,0.44}.
]

Result: F4 is largest at all (\beta); all functionals are bounded below F4; ordering holds at all (\beta). The ruler changes across functionals; the authorization ordering does not. This is the operational empirical witness for §3.6. It is weaker than literal fiber identity, and the paper uses it only in that weaker operational sense.

Turbo equivalent: T1, BER; T2, BER+(1\sigma); T3, derived BLER reference curve. Ordering holds at 61/61 SNR points.

Source: `examples/conservation/run_metric_invariance.py`.

### S4 World-realizability witnesses

For each induced gap G1–G7, a world-realizability witness is a concrete deployment scenario where the gap is open, the system takes the over-authorized action, and a real failure occurs that is not merely a documentation or process failure. The table below gives the compressed witness set used to support the claim that the gaps correspond to facts about the world, not merely tokens about the world.

| Gap | Witness scenario | Why the failure is world-realizable |
| --- | ---------------- | ----------------------------------- |
| G1 clinical utility | A sepsis alert has acceptable retrospective discrimination but no demonstrated clinical benefit at the deployed intervention threshold. | Clinicians receive actionable alerts, but patient outcomes or workflow burden make the intervention unsound despite predictive signal. |
| G2 model specification | A recruiting model is trained to predict historical resume-screening success and then used as if it measured job qualification. | The target variable is a proxy for prior institutional behavior, so the deployed action optimizes the wrong world-level property. |
| G3 distribution shift | A model trained and calibrated at one hospital, region, or population is deployed in a different site with different base rates and measurement practices. | The same score no longer denotes the same risk; authorization based on the source distribution overstates what the target evidence supports. |
| G4 individual-population scope | Population-average performance is used to justify action on a subgroup or individual whose error profile is materially worse. | The mean statistic is true, but the action fails for compatible individuals hidden inside the evidence fiber. |
| G5 blast radius | An automated hold, denial, or alert is allowed to trigger many downstream actions without bounding the number of affected people or the severity of consequences. | The local model error becomes a system-level harm because propagation was not bounded. |
| G6 authority/rollback | An automated system continues consequential action after conditions change, without a clear authority boundary or rollback protocol. | The failure is not that documentation is missing; the world contains no operative mechanism for stopping or reversing the action. |
| G7 reason traceability | A credit or adverse-action model cannot produce principal reasons that connect the applicant's inputs to the decision. | The denial occurs, but the system cannot generate the reasons needed for review, contestation, or legal notice. |

### S5 Requirement matrices

The ILS and Epic gap-requirement matrices used for the occlusion and projection experiments are included directly in Methods M6. This supplementary pointer is retained only to make the reproducibility dependency explicit: the results in §§2.6–2.7 are determined by those matrices plus the evidence states.

---
## Appendix A. Proofs for Section 3

### Appendix A.1. Proof of Theorem 1: finite lower-approximation law

Recall that

[
C_k(e)=\lfloor A(e)\rfloor_{P_k}
]

and

[
\lfloor x\rfloor_{P_k}=\max\{p\in P_k:p\preceq x\}.
]

**Soundness.** By definition, (C_k(e)) is chosen from permissions (p\in P_k) satisfying (p\preceq A(e)). Therefore

[
C_k(e)\preceq A(e).
]

Since (A(e)) is sound for every world in (F(e)), every weaker permission is also sound.

**Monotone grid refinement.** Suppose (P_k\subseteq P_{k+1}). The feasible set defining (C_k(e)),

[
\{p\in P_k:p\preceq A(e)\},
]

is contained in the feasible set defining (C_{k+1}(e)),

[
\{p\in P_{k+1}:p\preceq A(e)\}.
]

Taking the maximum over a larger feasible set can only increase or preserve the result. Thus

[
C_k(e)\preceq C_{k+1}(e).
]

Soundness gives

[
C_{k+1}(e)\preceq A(e).
]

**Dense-grid convergence.** Suppose ((P_k)) resolves (\mathcal A) from below, so that for every (x\in\mathcal A),

[
\bigvee_k \lfloor x\rfloor_{P_k}=x.
]

By monotone grid refinement, (C_k(e)) is monotone nondecreasing and bounded above by (A(e)). Its supremum is

[
\bigvee_k C_k(e) =
\bigvee_k \lfloor A(e)\rfloor_{P_k} =
A(e),
]

by the density assumption. Therefore (C_k(e)) converges to (A(e)) from below.

When grids are not nested but their mesh size tends to zero, the monotone conclusion need not hold at every (k). Convergence still follows whenever the floor error tends to zero. This is the situation in the Ising experiment: the nearest grid point above (TV_{\max}) improves intermittently rather than at every doubling, but the error is always bounded by one grid spacing and the spacing tends to zero.

### Appendix A.2. Proof of Theorem 2: conservative coarsening law

For a projection (\pi:E\to\bar E), the projected fiber is

[
F_\pi(\bar e)=\{w\in W:\pi(q(w))=\bar e\}.
]

For every fine evidence state (e), the fine fiber (F(e)) is contained in the projected fiber (F_\pi(\pi(e))). Indeed, if (q(w)=e), then (\pi(q(w))=\pi(e)). Thus

[
F(e)\subseteq F_\pi(\pi(e)).
]

Taking the meet over a larger set can only weaken or preserve the result. Hence

[
A^\pi(\pi(e)) =
\bigwedge_{w\in F_\pi(\pi(e))}a(w)
\preceq
\bigwedge_{w\in F(e)}a(w) =
A(e).
]

The alternative expression

[
A^\pi(\bar e)=\bigwedge_{e'\in\pi^{-1}(\bar e)}A(e')
]

follows because the projected fiber is the union of the fine fibers over all evidence states mapping to (\bar e).

Now let (\widehat A^\pi) be an implemented projected authorization function. The condition

[
\widehat A^\pi(\pi(e))\preceq A(e)
\quad\text{for all }e\in E
]

is equivalent to

[
\widehat A^\pi(\bar e)\preceq A^\pi(\bar e)
\quad\text{for all }\bar e\in\bar E.
]

To see this, fix (\bar e). The first inequality must hold for every fine state (e'\in\pi^{-1}(\bar e)). Therefore (\widehat A^\pi(\bar e)) is a lower bound of the set

[
\{A(e'):e'\in\pi^{-1}(\bar e)\}.
]

It is therefore no stronger than their meet (A^\pi(\bar e)). Conversely, if (\widehat A^\pi(\bar e)\preceq A^\pi(\bar e)), then for every (e\in\pi^{-1}(\bar e)),

[
\widehat A^\pi(\pi(e))=\widehat A^\pi(\bar e)\preceq A^\pi(\bar e)\preceq A(e).
]

Finally, suppose ((\pi,\widehat A^\pi)) is authorization-admissible. Then

[
\widehat A^\pi(\pi(e))\preceq A(e).
]

The floor operator is monotone: if (x\preceq y), then

[
\lfloor x\rfloor_{P_k}\preceq \lfloor y\rfloor_{P_k}.
]

Therefore

[
 C_k^\pi(\pi(e)) = \lfloor \widehat A^\pi(\pi(e))\rfloor_{P_k} \preceq \lfloor A(e)\rfloor_{P_k} = C_k(e).
]

This proves the conservative coarsening law.

### Appendix A.3. Proof of Theorem 3: semantic convergence under resolving refinement

Let ((\pi_m)) be refining and resolving at (e). Recall that

[
A^{\pi_m}(\pi_m(e)) = \bigwedge_{e'\in [e]_m}A(e').
]

First, conservatism gives the upper bound. Since (e\in[e]_m),

[
A^{\pi_m}(\pi_m(e)) = \bigwedge_{e'\in [e]_m}A(e') \preceq A(e).
]

Thus every projected authorization is no stronger than the fine latent authorization.

Second, refinement gives monotonicity. Because

[
[e]_{m+1}\subseteq [e]_m,
]

the meet at level (m+1) is taken over a subset of the states used at level (m). Taking a meet over a smaller set can only strengthen or preserve the result. Hence

[
A^{\pi_m}(\pi_m(e))
\preceq
A^{\pi_{m+1}}(\pi_{m+1}(e)).
]

So the sequence is monotone nondecreasing and bounded above by (A(e)).

Third, resolving identifies the limit. Let (p\prec A(e)). Since the sequence is resolving at (e), there exists (m_0) such that for all (m\geq m_0) and all (e'\in[e]_m),

[
p\preceq A(e').
]

Therefore (p) is a lower bound for the set (\{A(e'):e'\in[e]_m\}), so

$$
p \preceq \bigwedge_{e'\in[e]_m}A(e') = A^{\pi_m}(\pi_m(e)).
$$

Thus every permission (p\prec A(e)) is eventually below the projected authorization. Since the projected authorization is always no stronger than (A(e)), its supremum is exactly (A(e)). Hence

[
A^{\pi_m}(\pi_m(e))\nearrow A(e).
]

### Appendix A.4. Proof of Definition 6 equivalences and Theorem 4: analytical joint implemented convergence

Let ((\pi_m)) be refining and resolving at (e), and let (\widehat A_m:E_m\to\mathcal A) be the implemented authorization function at resolution (m). Definition 6 requires

[
\widehat A_m(\pi_m(e))
\preceq
A^{\pi_m}(\pi_m(e))
\quad\text{for all }m,
]

and

[
\bigvee_{M\geq 1}
\bigwedge_{m\geq M}
\widehat A_m(\pi_m(e))=A(e).
]

The first condition gives pointwise soundness relative to the semantic projected meet. Since Theorem 3 gives

[
A^{\pi_m}(\pi_m(e))\preceq A(e),
]

each implemented output is a sound lower bound:

[
\widehat A_m(\pi_m(e))\preceq A(e).
]

In an order-dense lattice, the lower-envelope condition is equivalent to the threshold form: for every (p\prec A(e)), there exists (m_0) such that for all (m\geq m_0),

[
p\preceq \widehat A_m(\pi_m(e)).
]

Indeed, if the threshold form holds for every (p\prec A(e)), then every strict lower permission eventually lies below the tail meet, so the supremum of tail meets is (A(e)). Conversely, if the supremum of the tail meets is (A(e)) and some (p\prec A(e)) failed to be eventually below the implemented outputs, then every tail would contain an output below (p), forcing the eventual lower envelope below (p) and contradicting equality with (A(e)).

In a finite chain with (A(e)\in\mathcal A), the same condition collapses to eventual exactness. Let (p^-) be the immediate predecessor of (A(e)), if one exists. If infinitely many implemented outputs were no stronger than (p^-), then every tail meet would be no stronger than (p^-), and the lower envelope could not equal (A(e)). Therefore all sufficiently late implemented outputs equal (A(e)). If (A(e)) is the bottom element, the claim is immediate because every output is already no stronger than (A(e)).

Now define the two-axis compiler output

[
 C_{m,n}(e) = \left\lfloor \widehat A_m(\pi_m(e))\right\rfloor_{P_n}.
]

The first claim of Theorem 4 is exactly the lower-envelope clause of Definition 6. We prove the finite-grid joint convergence claim.

Let (p\prec A(e)).

**Finite permission lattice.** By the finite-collapse clause above, there exists (m_0) such that, for all (m\geq m_0),

[
\widehat A_m(\pi_m(e))=A(e).
]

Thus

[
C_{m,n}(e)=\lfloor A(e)\rfloor_{P_n}
]

for all sufficiently large (m). Since (P_n) resolves (\mathcal A) from below, Theorem 1 gives

[
\lfloor A(e)\rfloor_{P_n}\to A(e)
]

from below. Hence there is an (n_0) such that, for all (n\geq n_0),

[
p\preceq C_{m,n}(e)\preceq A(e).
]

**Order-dense permission lattice.** Choose (s) such that

[
p\prec s\prec A(e).
]

By the threshold form of asymptotic meet-exactness, there exists (m_0) such that for all (m\geq m_0),

[
s\preceq \widehat A_m(\pi_m(e)).
]

Because (P_n) resolves (\mathcal A) from below, there exists (n_0) such that for all (n\geq n_0), the grid contains some (r_n\in P_n) satisfying

[
p\preceq r_n\preceq s.
]

For all (m\geq m_0) and (n\geq n_0), we therefore have

[
p\preceq r_n\preceq s\preceq \widehat A_m(\pi_m(e)).
]

Since (r_n) is a grid point no stronger than (\widehat A_m(\pi_m(e))), the floor must be at least (r_n):

[
 r_n \preceq \left\lfloor \widehat A_m(\pi_m(e))\right\rfloor_{P_n} = C_{m,n}(e).
]

Therefore

[
p\preceq C_{m,n}(e)
]

eventually. Since

[
C_{m,n}(e)\preceq \widehat A_m(\pi_m(e))\preceq A(e),
]

the two-axis compiler output converges jointly to (A(e)) from below. If the implemented evidence projections and permission grids are nested, the convergence is monotone. Otherwise, it is joint convergence from below without pointwise monotonicity.

### Appendix A.5. Proof of Theorem 5: evidence-representation invariance

Let (q_1:W\to E_1) and (q_2:W\to E_2) be authorization-equivalent evidence representations. Thus there exists a bijection

[
\psi:q_1(W)\to q_2(W)
]

such that

[
q_2=\psi\circ q_1.
]

For any world (w\in W),

[
w\in F_2(\psi(e))
\quad\Longleftrightarrow\quad
q_2(w)=\psi(e)
\quad\Longleftrightarrow\quad
\psi(q_1(w))=\psi(e)
\quad\Longleftrightarrow\quad
q_1(w)=e
\quad\Longleftrightarrow\quad
w\in F_1(e),
]

where the third equivalence uses injectivity of (\psi). Therefore

[
F_2(\psi(e))=F_1(e).
]

It follows that

$$
 A_2(\psi(e)) = \bigwedge_{w\in F_2(\psi(e))}a(w) = \bigwedge_{w\in F_1(e)}a(w) = A_1(e).
$$

### Appendix A.6. Proof of permission-relabeling invariance

Let (\phi:\mathcal A\to\mathcal A') be an order isomorphism of permission lattices. Define

[
a'(w)=\phi(a(w)).
]

Since (\phi) is an order isomorphism, it preserves meets. Therefore

$$
 A'(e) = \bigwedge_{w\in F(e)}a'(w) = \bigwedge_{w\in F(e)}\phi(a(w)) = \phi\left(\bigwedge_{w\in F(e)}a(w)\right) = \phi(A(e)).
$$

### Appendix A.7. Proof of Theorem 6: exact recovery iff the fiber is authorization-constant

For an evidence state (e), recall that

[
A(e)=\bigwedge_{w\in F(e)}a(w),
]

and

[
B(e)=\bigvee_{w\in F(e)}a(w).
]

If (a(w)) is constant on (F(e)), say (a(w)=p) for every (w\in F(e)), then both the meet and the join over the fiber are (p). Thus

[
A(e)=B(e)=p.
]

Conversely, suppose

[
A(e)=B(e)=p.
]

For any (w\in F(e)), the meet is no stronger than (a(w)), and (a(w)) is no stronger than the join:

[
A(e)\preceq a(w)\preceq B(e).
]

Since (A(e)=B(e)=p), it follows that (a(w)=p). Thus (a) is constant over the fiber.

Finally, evidence (e) determines a unique authorization value exactly when all worlds compatible with (e) have the same world-level authorization. This is the same condition as authorization-constancy of the fiber.

### Appendix A.8. Proofs of order- and source-invariance

**Order-invariance of gap induction.** Suppose a fixed corpus determines a finite set (G^\star) of visible, policy-relevant failure modes. Suppose the induction procedure adds a gap whenever a processed case exposes a permissive disagreement that is blocked by that gap, never removes gaps, and eventually processes every case.

Each induction step adds an element of (G^\star). No step removes elements. Because every case is eventually processed, every gap in (G^\star) is eventually exposed and added. Therefore the terminal set is exactly the union of the gaps exposed by the corpus:

[
\bigcup_{\text{cases }c}g(c)=G^\star.
]

Set union is commutative and associative, so the result does not depend on the order of cases.

**Source-invariance of compiler soundness.** For fixed evidence state (e), permission hierarchy (P), and gap-requirement map (R), the compiler is a deterministic function

[
C(e;P,R).
]

No argument to this function records whether a gap was proposed by an expert, induced from a deployment failure, suggested by an LLM, copied from a regulation, or written by a developer. Therefore two evidence packages with identical gaps, statuses, permission hierarchy, and requirement map produce identical compiler outputs. The source may affect epistemic trust in the evidence contract, but it does not affect the soundness of the compiler relative to that contract.


## References

1. Berrou, C., Glavieux, A., & Thitimajshima, P. (1993). Near Shannon limit error-correcting coding and decoding: Turbo-codes. *Proceedings of IEEE International Conference on Communications*.
2. 3GPP. TS 38.214. *NR; Physical layer procedures for data*.
3. U.S. Food and Drug Administration. (2021). *Artificial Intelligence/Machine Learning (AI/ML)-Based Software as a Medical Device (SaMD) Action Plan*.
4. Consumer Financial Protection Bureau. *Equal Credit Opportunity Act (Regulation B), 12 CFR Part 1002*, including §1002.9, Notifications.
5. Federal Aviation Administration. *Aeronautical Information Manual*, Chapter 5, Section 4, Arrival Procedures.
6. Federal Aviation Administration. *Runway Visual Range (RVR)*, navigation services description of CAT I/II/III minima.
7. Wong, A., Otles, E., Donnelly, J. P., et al. (2021). External validation of a widely implemented proprietary sepsis prediction model in hospitalized patients. *JAMA Internal Medicine*.
8. Obermeyer, Z., Powers, B., Vogeli, C., & Mullainathan, S. (2019). Dissecting racial bias in an algorithm used to manage the health of populations. *Science*.
9. Lum, K., & Isaac, W. (2016). To predict and serve? *Significance*.
10. Angwin, J., Larson, J., Mattu, S., & Kirchner, L. (2016). Machine bias. *ProPublica*.
11. Dastin, J. (2018). Amazon scraps secret AI recruiting tool that showed bias against women. *Reuters*.
12. IBM Watson oncology, PredPol, COMPAS, Epic, Optum, and Amazon source documents are listed in the full audit trail at `docs/provenance.md`.

---

## Figure Captions

**Figure 1.** *The latent authorization function.* Left: (P_4), a 4-level permission grid, produces a blocky staircase approximation to (A(e)). Center: (P_{16}) resolves the staircase further. Right: the latent function (A(e)) is the limit of these lower approximations. Finite compilers observe the staircase; densification reveals the function.

**Figure 2.** *Three regularity classes of the latent authorization function.* (A) Turbo: a BER-based surrogate reaches the monitored-transmission cutoff near (0.0) dB SNR, while the derived BLER reference curve requires approximately (3.4) dB; the orange region is the authorization gap. Breakpoints grow with both (k) and SNR resolution: artifact signature. (B) Ising: the binary ACT/REFUSE step at (\tau=TV_{\max}=0.3338). Breakpoint count is exactly 1 at all (k). Location error is bounded by one grid spacing at every resolution and converges to zero as spacing (=0.50/k\to 0): genuine-threshold signature. Intermittent improvement is the expected behavior of a uniform rational grid approaching a fixed non-grid-aligned target. (C) FAA: RVR floor falls smoothly from 3,770 ft at DH (=300) ft to zero at the saturation point DH (\approx 102.4) ft. Below saturation, visual-acquisition geometry no longer constrains the approach. Breakpoints stabilize at 64 after (k=64); additional resolution fills the flat post-saturation region without producing new features.

**Figure 3.** *Evidence hiding produces theory-predicted permission descent.* (A) ILS: opening authorization, visual, and signal gaps in sequence drops permission ALR → REV → DIA → REF. Each drop occurs exactly at the gap required by the departing permission level. (B) Epic: opening G1–G7 drops ALR → AEX at G1; G2–G7 do not further lower permission because they gate ALR, which has already been departed. Opening S2 drops AEX → REV; opening S1 drops REV → DIA.

**Figure 4.** *Admissible coarsening and structural collapse.* (A) Projected permission per case M01–M07 across six projection levels. Levels 0–3 produce no change. Level 4 drops all cases from AEX to REV: the gap has opened, authorization has weakened, and the admissibility condition holds. Level 5 returns all cases to AEX: spurious authorization by structural collapse. (B) Total gap width across levels. Level 4: gap opens, admissibly. Level 5: gap collapses back to zero, violating (\widehat A^\pi(\pi(e))\preceq A(e)).

**Figure 5.** *Regulatory thresholds as samples of the latent authorization structure.* Seven cases classified by correspondence type. ECOA G7: exact recovery. FAA CAT I: independent-route same-axis policy/rounding margin, with frozen geometry giving 1,862 ft at DH (=200) ft versus the 1,800 ft regulatory minimum. 3GPP: representation-relative alignment. FDA gaps: same-axis policy margin (shared-corpus; see §4.3). FAA CAT II/III: different evidence axis or outside supplied package. Amazon recruiting: hierarchy-placement failure. Cybersecurity: outside supplied package.

---

*Figures generated by `docs/pivot/figures/generate_figures.py`. All numerical values from `examples/conservation/results/`. Implementation: `python/noethers_turnstile/`, `examples/`.*
