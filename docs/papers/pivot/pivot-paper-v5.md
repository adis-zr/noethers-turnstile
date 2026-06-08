# The Conservation of Incomplete Evidence

**An authorization calculus for approximate and consequential systems**

**Author:** Aditya Sriram  
**Affiliation:** Independent Researcher

---

## Abstract

Approximate systems increasingly authorize consequential action: clinical alerts, credit denials, automated holds, ranking decisions, routing policies and other interventions whose costs are borne outside the model. Yet the theory of approximate systems mostly asks how well a model predicts, not what its evidence is allowed to authorize. We introduce a latent authorization calculus for incomplete evidence. Given a space of possible worlds, an evidence map and an ordered permission scale, the strongest action supported by an evidence state is the meet of the world-level authorizations over all worlds still compatible with that evidence. This latent authorization function is not an average, threshold convention or regulatory label; it is the worst-case permission forced by the unresolved evidence fiber. We prove that finite permission hierarchies approximate this object from below, that admissible evidence coarsenings may weaken but not create authorization, and that resolving refinements across both evidence and permission axes converge to the same latent object. We implement the calculus as a deterministic compiler and test it across communication, probabilistic inference, aviation geometry and medical-AI authorization examples. Permission densification separates smooth quantization artifacts, genuine thresholds and evidence-axis transitions. Evidence hiding produces conservative permission descent. Projection experiments identify the admissibility boundary, including a compact skeleton-truncating representation that spuriously restores permission by erasing the requirements that made stronger action unsound. The central two-axis experiment is separated into a canonical-map matrix and targeted controls. Under the canonical requirement map, 16 cases exercise DIA through ALR; the resolving path is sound and monotone in all 400 tested cells and converges in every case. Targeted controls supply the missing synthetic floor and active-refinement witnesses, bringing the combined stress test to 21 cases over the full REF-to-ALR chain without conflating distinct requirement maps. A non-resolving path through a skeleton-truncating projection loses soundness and evidence-axis monotonicity at the inadmissible boundary, then reconverges after entering the resolving tail. A four-shape stress test localizes the failures: each inadmissible truncation contributes exactly the structurally eligible unsound cells, and each restoration transition contributes exactly the structurally eligible monotonicity violations. External standards in aviation, communications, medicine and credit are evaluated as correspondence audits, not as primary validation. The result is a computational separation between what evidence forces, what admissible representation preserves and what policy adds.

---

## 1. Introduction

Approximate systems increasingly gate consequential action. A sepsis model decides which patients trigger a clinical alert. A risk score informs pretrial detention. A care-management algorithm allocates services across a population. A predictive-policing system directs patrols. A resume screener forwards or discards a candidate. Ranking systems, routing policies and automated holds decide which opportunities are surfaced, delayed, denied or escalated. In each case, a system that is only approximately correct is granted authority to act, and the action carries costs that the model itself does not bear.

When these systems fail in ways that reach public record, the failure is often not a modeling error in the ordinary sense. The Optum population-health algorithm predicted health-care cost accurately; cost was the wrong proxy for need [8]. The Amazon recruiting screener learned its training signal faithfully; the signal encoded historical hiring decisions rather than qualification [11]. The Epic sepsis model carried real predictive signal; that signal did not establish benefit at the deployed intervention threshold [7]. The recurring fault is not that the statistic was false. It is that a true statistic was allowed to authorize an action it did not support.

This is an authorization error. It is distinct from, and largely orthogonal to, predictive accuracy.

The asymmetry in the theory is striking. We have mature tools for asking how well a model predicts: calibration, generalization, error bounds, uncertainty quantification, robustness analysis and distribution-shift detection. We have much weaker tools for asking when a prediction licenses an action. In practice, the licensing step is often supplied by convention. A threshold is chosen, a population average is compared against a cutoff, a regulatory category is matched, or a review board signs off. These devices answer a question they rarely state:

> Given everything this evidence does and does not reveal, what is the strongest action it can soundly support?

This paper gives a formal answer to that question, conditional on the evidence representation, permission order and world-level soundness semantics supplied by the domain.

The answer is not an average. It is a meet.

This puts the paper near, but not inside, several older traditions. Maximin decision theory and distributionally robust optimization also reason against adverse states or distributions [13,14]. The difference is structural. In those frameworks, the uncertainty or ambiguity set is part of the decision model, often chosen to express a risk attitude, robustness radius, distributional neighborhood or loss class. Here the compatible set is not chosen as a robustness device. It is the evidence fiber forced by the representation: the set of worlds the supplied evidence has failed to distinguish. The output is also different. The calculus does not select the utility-optimal act. It returns an authorization ceiling: the strongest permission that no compatible world refutes.

A second neighboring tradition studies forecast value and expected utility, including cost-loss decision rules for acting on probabilistic information [15]. That tradition asks whether a forecast improves a decision maker's expected utility. The present calculus asks a prior question: which action classes the evidence is allowed to license at all. Policy can still optimize below that ceiling, or choose to act more conservatively. What it cannot soundly do is exceed the ceiling without adding evidence, changing the permission semantics, or acknowledging a policy override.

Fix an evidence state. Many distinct worlds remain compatible with it. Some of those worlds may support strong action; others may not. The authorization forced by the evidence is the strongest permission sound in every compatible world. We call this object the latent authorization function, denoted \(A(e)\). It is the meet of world-level authorizations over the evidence fiber. It exists whether or not any deployed system computes it.

This distinction matters. A population-average statistic may support an action for the average member of a group while failing for compatible individuals hidden inside the same evidence fiber. A bit-level communication statistic may appear safe while the corresponding block-level failure probability remains unacceptable. A model may have sufficient retrospective discrimination but insufficient clinical-utility evidence at the deployed intervention threshold. In all of these cases, the evidence does not fail because it is empty. It fails because the action it was allowed to authorize is stronger than the weakest compatible world permits.

The contribution of this paper is an authorization calculus for this setting. We make five claims.

First, incomplete evidence induces a canonical lower endpoint once the evidence map, permission order and world-level soundness relation are supplied. This endpoint is \(A(e)\), the strongest permission sound for all worlds compatible with evidence \(e\).

Second, finite permission hierarchies can only approximate this endpoint from below. A finite compiler may be conservative, and it may sharpen as the permission scale is refined, but it cannot soundly exceed \(A(e)\).

Third, evidence representations can be changed only under an admissibility constraint. Coarsening may hide distinctions and weaken authorization. It may not manufacture permission unsupported by the finer evidence.

Fourth, resolving refinement of both axes -- evidence representation and permission scale -- converges to the same latent authorization object. This is the conservation law of the title. Authorization may be weakened, refined or relabelled under admissible transformations. It may not be created by representation.

Fifth, this law is computationally testable. We implement the calculus as a compiler. The compiler takes an evidence package, a finite permission hierarchy and a requirement map, then returns the strongest permission whose requirements are satisfied. It is a type checker for authorization rather than a predictive model.

The experiments follow the theorem architecture. We first hold evidence fixed and refine permission scales. Across communication, inference and aviation-geometry examples, densification distinguishes three regularity classes: smooth quantization artifacts, genuine structural thresholds and evidence-axis transitions. We then hold the permission scale fixed and alter evidence representation. Evidence hiding produces conservative permission descent. Projection fidelity exposes the admissibility boundary: a compact representation can look natural while erasing the permission skeleton and spuriously restoring authorization. Finally, we move both axes simultaneously. The central experiment is deliberately split into two parts. Under a single canonical requirement map, 16 cases exercise the DIA-through-ALR portion of the implemented chain; the resolving path is sound and monotone in every tested cell and converges for every case. Five targeted controls use explicitly declared non-canonical maps: one synthetic floor case that realizes REF, and four active-refinement witnesses that test whether later evidence splits can carry signal. The combined stress test spans the full REF-to-ALR chain, but the manuscript keeps the canonical result and the targeted controls separate rather than treating them as one uniform requirement-map experiment. Non-resolving paths lose soundness and evidence-axis monotonicity exactly where they pass through skeleton-truncating projections, and reconverge precisely when a resolving tail is restored.

We also compare the same object against external standards in aviation, communications, medicine and credit. These comparisons are not treated as uniform validation. They are correspondence audits with different independence profiles: exact recovery in one supplied legal representation, independent-route same-axis convergence in one geometry case, representation-relative alignment in communications, shared-corpus correspondence in medical-AI guidance, and outside-package silence where the supplied evidence map cannot speak.

The result is a separation that the failure cases lacked: what evidence forces, what representation preserves, and what policy adds.

---

## 2. Results

### 2.1 Overview of the claim architecture

The paper has one conserved object and two finite approximation axes.

The conserved object is the latent authorization function \(A(e)\): the strongest permission sound in every world still compatible with evidence state \(e\). The first approximation axis is permission resolution. A finite permission hierarchy reads \(A(e)\) as a lower approximation. The second approximation axis is evidence representation. A coarser evidence vocabulary enlarges evidence fibers and may weaken authorization, but an admissible coarsening cannot strengthen it.

The experiments are organized around this architecture rather than around domain frequency. The goal is not to estimate how often an authorization error occurs in a population of systems. The goal is to test whether the compiler behaves according to the predicted geometry under controlled transformations.

**Table 1. Claim ledger.**

| Claim | Status in this paper |
|---|---|
| \(A(e)\) is the strongest permission sound over all worlds compatible with evidence \(e\) | Definition and theorem consequence |
| Finite permission grids approximate \(A(e)\) from below | Theorem |
| Nested permission-grid refinement sharpens authorization monotonically | Theorem |
| Semantic evidence coarsening cannot create authorization | Theorem |
| Authorization-admissibility is a non-vacuous, checkable condition on implemented projections | Definition, theorem consequence and projection-fidelity witness |
| Resolving evidence refinement recovers \(A(e)\) semantically | Theorem |
| Joint evidence and permission refinement converges to \(A(e)\) from below under a fixed requirement map | Theorem and canonical-map implementation |
| Full REF-to-ALR stress coverage requires targeted controls with declared non-canonical maps | Explicit scope statement and control experiment |
| Active evidence refinements can shift permission when they resolve single-poison active blockers | Synthetic control demonstration and witness lemma |
| Later refinements can be inert after the active blocker has been resolved | Observed behavior; certified only for absence of the tested single-poison mechanism |
| Skeleton-truncating projection can spuriously restore authorization | Implemented non-vacuity witness |
| Non-resolving prefixes produce localized transient violations; reconvergence is determined by the resolving tail | Localization theorem, resolving-tail corollary and four-shape stress test |
| External standards instantiate or approximate the same structure | Correspondence audit, not primary validation |
| The calculus chooses the correct evidence map or permission hierarchy | Not claimed |

The domains are assigned distinct evidentiary roles.

**Table 2. Domain and experiment roles.**

| Domain or experiment | Role in the paper | What it supports |
|---|---|---|
| Turbo-coded communication | Smooth negative control | Permission densification can subdivide a smooth monotone curve without revealing structural thresholds |
| Ising belief propagation | Structural-step example | A genuine authorization threshold remains pinned under densification |
| FAA CAT I geometry | Evidence-axis transition and independent-route correspondence | A supplied geometric evidence axis can saturate; a frozen geometric floor lands near an external standard |
| ILS occlusion | Physical hierarchy demonstration | Hiding required evidence weakens permission in the predicted order |
| Epic medical-AI hierarchy | Socio-technical hierarchy demonstration | Gap opening, projection fidelity and joint refinement can be compiled deterministically |
| Projection fidelity | Admissibility boundary | Coarsening remains safe only while it preserves the permission skeleton conservatively |
| Canonical two-axis matrix | Central implemented conservation result | A single canonical requirement map exercises DIA through ALR and recovers \(A(e)\) from below |
| Synthetic floor control | Declared non-canonical boundary control | REF can be realized by a strict floor map, but is not part of the canonical-map coverage claim |
| Active-refinement witnesses | Declared non-canonical signal controls | Later evidence splits can carry signal when they resolve single-poison active blockers |
| Path-shape stress test | Boundary test for theorem hypotheses | Failure localization follows inadmissible truncation and restoration sites; reconvergence follows the resolving tail |
| 3GPP, FDA, ECOA, Amazon and FAA CAT II/III | External correspondence audits | External standards can be classified by relation to the latent authorization structure |

This claim ledger is deliberately conservative. The paper's central contribution is the calculus and its compiler behavior under representation and permission changes. The regulatory section is an external audit of correspondence, not the foundation of the theory. The two-axis section separates a fixed-map conservation result from targeted controls; this prevents a full-chain stress test from being misread as one uniform requirement-map experiment.

---

### 2.2 The latent authorization function

Let \(W\) be the set of possible worlds. A world contains all facts relevant to authorization: actual channel behavior, true approximation errors, deployment setting, oversight structure, reason trace, patient impact, available rollback mechanism or any other fact that could make an action sound or unsound.

Let \(E\) be a space of evidence states, and let

$$
q: W \to E
$$

be the evidence map. The evidence map records only what the evidence package can observe.

For an evidence state \(e\in E\), define the evidence fiber

$$
F(e)=\{w\in W:q(w)=e\}.
$$

This is the set of worlds still compatible with the evidence.

Let \(\mathcal A\) be a permission lattice ordered from weaker to stronger permissions. We write

$$
p\preceq r
$$

to mean that permission \(p\) is no stronger than permission \(r\). In the implemented examples,

$$
\mathrm{REF}\preceq \mathrm{DIA}\preceq \mathrm{REV}\preceq \mathrm{AEX}\preceq \mathrm{ALR}.
$$

Here REF denotes refusal or no authorization; DIA denotes diagnostic display; REV denotes human review; AEX denotes bounded assisted execution; and ALR denotes autonomous or limited release under the strongest supplied requirements.

Let

$$
a:W\to\mathcal A
$$

be the world-level authorization function, where \(a(w)\) is the strongest action sound in world \(w\).

The latent authorization function induced by evidence map \(q\) is

$$
A(e)=\bigwedge_{w\in F(e)} a(w).
$$

Thus \(A(e)\) is the strongest permission sound for every world still compatible with \(e\). A permission \(p\) is sound given evidence \(e\) exactly when

$$
p\preceq A(e).
$$

The associated upper endpoint is

$$
B(e)=\bigvee_{w\in F(e)} a(w),
$$

the strongest permission consistent with at least one world compatible with \(e\). The interval

$$
[A(e),B(e)]
$$

is the authorization gap. The lower endpoint is what is sound for every compatible world. The upper endpoint is what remains possible in some compatible world. A sound compiler must return the lower endpoint or a lower approximation to it.

This definition is the central object of the paper. Authorization is not attached to an evidence state by averaging, voting or matching a regulatory label. It is the meet of the world-level authorizations over the worlds the evidence has not ruled out.

---

### 2.3 Finite permission levels sample the latent function from below

A finite compiler does not observe \(A(e)\) directly. It observes it through a finite permission grid.

Let

$$
P_k=\{p_1\prec p_2\prec \cdots \prec p_k\}\subseteq \mathcal A
$$

be a finite permission grid. Define the floor of \(x\in\mathcal A\) with respect to \(P_k\) as

$$
\lfloor x\rfloor_{P_k}=\max\{p\in P_k:p\preceq x\},
$$

with the bottom permission returned if the set is empty. The compiler output under grid \(P_k\) is

$$
C_k(e)=\lfloor A(e)\rfloor_{P_k}.
$$

For every evidence state \(e\), \(C_k(e)\preceq A(e)\). If \(P_k\subseteq P_{k+1}\), then

$$
C_k(e)\preceq C_{k+1}(e)\preceq A(e).
$$

If the grid sequence resolves \(\mathcal A\) from below, then

$$
C_k(e)\nearrow A(e).
$$

This theorem is elementary, but its interpretation is important. A finite staircase is not the ontology. It is the finite-grid observation of the latent authorization value.

The densification experiments test what the staircase does as the permission grid is refined. Three signatures are predicted:

1. **Smooth artifact.** Breakpoint count grows with grid granularity and path resolution. The staircase is subdividing a smooth curve.
2. **Genuine threshold.** Breakpoint count is constant across grid refinements; location error is bounded by one grid spacing and converges to zero.
3. **Evidence-axis transition.** Breakpoint count grows until a structural feature is resolved, then stabilizes or changes regime.

These signatures are evaluated in three domains.

![Figure 1. The latent authorization function. A finite permission grid reads \(A(e)\) as a staircase approximation from below.](figures/fig1_latent_function.png)

---

### 2.4 Permission densification separates three regularity classes

#### 2.4.1 Turbo-coded communication is a smooth negative control

Turbo codes transmit data over a noisy channel. Two error statistics are relevant: bit error rate (BER), which averages errors over bits, and block error rate (BLER), which flags a block as failed if any bit fails. BER and BLER can diverge sharply. A bit-level statistic can appear acceptable while the corresponding block-level failure probability remains too high.

We use a four-level hierarchy,

$$
\mathrm{REFUSE}/\mathrm{HOLD}/\mathrm{TRANSMIT\_MONITORED}/\mathrm{TRANSMIT},
$$

with a monitored-transmission cutoff at

$$
\mathrm{BLER}\leq 0.02.
$$

If this cutoff is naively applied to a mean-like BER statistic, the link first appears to qualify for monitored transmission near \(0.0\) dB SNR. The derived block-level reference BLER does not reach the same cutoff until approximately \(3.4\) dB. The gap region is therefore

$$
\mathrm{SNR}\in[0.0,3.4]\ \mathrm{dB}.
$$

At the midpoint, SNR \(=1.7\) dB, BER is approximately \(1.3\times 10^{-3}\), while the independent-bit BLER reference is approximately \(1.0\). The authorization gap is large.

The BLER curve used here is the independent-bit reference curve derived from digitized BER,

$$
\mathrm{BLER}_{\mathrm{ref}}=1-(1-\mathrm{BER})^L,
$$

with block length \(L=65{,}536\). It is not claimed to be the measured turbo-code channel law; turbo decoding creates correlated block failures. The role of the reference curve is to isolate mean-to-block amplification geometry.

Using log-uniform BLER thresholds over \([10^{-4},1.0]\), breakpoints grow from 3 at \(k=4\) to 20 at \(k=256\) over 61 SNR points. Holding \(k=256\) fixed and increasing the SNR grid from 61 to 1,952 points, breakpoints grow from 20 to 205. The count scales with both permission-grid density and SNR resolution.

This is the signature of a smooth monotone function being subdivided. Turbo is therefore the smooth negative control: the authorization gap is real, but the densification staircase carries no structural signal beyond the monotone shape.

#### 2.4.2 Ising belief propagation identifies a genuine structural step

We next evaluate loopy belief propagation on a \(6\times 6\) Ising grid at coupling strength \(\beta=0.44\), near critical coupling. Exact marginals are computed by full enumeration; BP marginals are computed by loopy belief propagation. The per-variable total variation distance between BP and exact marginals measures approximation error.

Two summary functionals are compared:

$$
TV_{\mathrm{mean}}=0.2231,
\qquad
TV_{\max}=0.3338.
$$

The compiler authorizes ACT only if TV \(\leq \tau\) for the chosen functional. Mean TV and max TV cross the authorization threshold at different \(\tau\), producing a gap region

$$
\tau\in[0.2231,0.3338]
$$

of width \(0.1108\).

We use a uniform \(\tau\)-grid over \([0,0.50]\). At every

$$
k\in\{4,8,16,32,64,128,256\},
$$

the compiler produces exactly one breakpoint: the smallest grid point at or above

$$
TV_{\max}=0.3338.
$$

Breakpoint count is constant at 1 across all seven granularity levels. Location error is bounded by one grid spacing at every \(k\).

| \(k\) | Grid spacing | Location error | Error \(\leq\) spacing |
|---:|---:|---:|:---:|
| 4 | 0.12500 | 0.04116 | yes |
| 8 | 0.06250 | 0.04116 | yes |
| 16 | 0.03125 | 0.00991 | yes |
| 32 | 0.01563 | 0.00991 | yes |
| 64 | 0.00781 | 0.00209 | yes |
| 128 | 0.00391 | 0.00209 | yes |
| 256 | 0.00195 | 0.00014 | yes |

The error does not decrease at every doubling because the nearest grid point above \(TV_{\max}\) sometimes remains unchanged. This intermittent improvement is expected for a uniform rational grid converging to a non-grid-aligned target. The important fact is that the breakpoint remains pinned to a fixed structural threshold and the error stays within one grid spacing.

Ising therefore shows the opposite of turbo. Densification does not smooth the staircase away because the staircase is tracking a genuine step.

#### 2.4.3 FAA instrument landing shows an evidence-axis transition

The third densification example is Category I instrument landing system geometry. At decision height \(H\) above the runway, the pilot must acquire visual reference to continue the approach. The geometric constraint used here is

$$
\mathrm{RVR}_{\mathrm{floor}}(H)=\max\left(0,\frac{H-50}{\tan(3^\circ)}-1000\right).
$$

The curve is smooth and decreasing in decision height until it saturates at zero near \(H\approx102.4\) ft. Above that point, the supplied visual-acquisition geometry is the binding evidence axis. Below that point, the supplied CAT I evidence package no longer constrains RVR; a different evidence axis would be needed.

The RVR floor falls from 3,770 ft at \(H=300\) ft to 336 ft at \(H=120\) ft, then reaches zero at approximately 102 ft and remains there. The saturation is not a regulatory choice. It is the geometric point where the supplied evidence axis stops speaking.

Using uniform RVR thresholds over \([0,2400]\) ft, breakpoints grow from 4 at \(k=4\) to 64 at \(k=64\), then stabilize: at \(k=128\) and \(k=256\), the count remains 64. The 64 breakpoints above saturation correspond to the smooth geometric curve being subdivided by the finite grid. No additional breakpoints appear below saturation because RVR is identically zero; the flat region absorbs new grid points without producing new transitions.

The kink at 102.4 ft persists at every \(k\). It is not a quantization artifact. It is the boundary where the supplied evidence stops speaking.

Together, turbo, Ising and FAA geometry establish the densification diagnostic as a discriminator.

| Domain | Densification signature | Latent regularity |
|---|---|---|
| Turbo | Breakpoints grow with \(k\) and SNR resolution | Smooth monotone function |
| Ising | One breakpoint at all \(k\); spacing-bounded location error | Genuine structural step |
| FAA | Breakpoints stabilize at the evidence-axis saturation | Piecewise smooth with evidence-axis transition |

![Figure 2. Densification signatures. Turbo is the smooth control, Ising is the structural step, and FAA geometry is the evidence-axis transition.](figures/fig2_densification_signatures.png)

---

### 2.5 Evidence hiding produces conservative permission descent

The first evidence-side experiment hides evidence one gap at a time and reruns the compiler. The prediction is monotone descent: removing evidence may weaken or preserve authorization, but it cannot strengthen it.

#### 2.5.1 ILS occlusion

The ILS hierarchy uses three gaps:

- `ils_signal_integrity` (S),
- `visual_reference` (V),
- `sub_cat1_authorization` (A).

Starting from all gaps at the status required for ALR, opening authorization drops permission to REV; opening visual reference drops permission to DIA; opening signal integrity drops permission to REF. The compiler traverses four levels in the theory-predicted order:

$$
\mathrm{ALR}\to\mathrm{REV}\to\mathrm{DIA}\to\mathrm{REF}.
$$

No reversals occur.

#### 2.5.2 Epic medical-AI occlusion

The Epic hierarchy uses nine gaps: approximation quality (S1), freshness (S2), clinical utility (G1), model specification (G2), distribution shift (G3), individual-population scope (G4), blast radius (G5), authority/rollback (G6) and reason traceability (G7).

Starting from all gaps at the status required for ALR, opening G1 drops permission to AEX. The G-gaps gate ALR, not AEX, so opening G2--G7 individually does not lower permission further once AEX is already binding. Opening S2 drops AEX to REV. Opening S1 drops REV to DIA.

The occlusion staircase is not a smooth function. It is a piecewise-constant descent governed by the requirement map. The compiler is not making a judgment call. It is reading the hierarchy. This is the conservation law under evidence hiding: the accessible authorization may weaken, but it does not strengthen without new evidence.

![Figure 3. Evidence hiding produces conservative permission descent.](figures/fig3_occlusion.png)

---

### 2.6 Projection fidelity exposes the admissibility boundary

Evidence representations can be coarsened. Let

$$
\pi:E\to\bar E
$$

be a projection from fine evidence states to coarser evidence states. The semantic projected authorization is

$$
A^\pi(\bar e)=\bigwedge_{w:\pi(q(w))=\bar e}a(w).
$$

For every fine evidence state \(e\),

$$
A^\pi(\pi(e))\preceq A(e).
$$

Semantic coarsening is always conservative because it takes the meet over a larger compatible set.

Real implementations, however, need not compute the semantic meet. A projected compiler may use a simplified vocabulary, a new profile builder or a new requirement map. Let

$$
\widehat A^\pi:\bar E\to\mathcal A
$$

be the implemented authorization function under the projected representation. We call the projection authorization-admissible if

$$
\widehat A^\pi(\pi(e))\preceq A(e)
\quad\text{for all }e\in E.
$$

This is the admissibility fence. Coarsening may hide evidence and weaken authorization. It may not create stronger permission.

We test this condition on the Epic evidence package using six projection levels. The finest representation has all nine gaps. Intermediate projections merge structurally related gaps. The coarsest representation collapses all evidence into two generic gaps: evidence quality and evidence scope.

Levels 0--3 merge gaps within the same functional category and produce no change in projected permission. Gap width is zero.

Level 4 merges reason traceability (G7) with freshness (S2) into a single `evidence_currency_gap`. This crosses a structural boundary in the requirement hierarchy. Under conservative composite semantics, the projected compiler loses the ability to satisfy AEX through the two obligations independently. Projected permission drops from AEX to REV. Gap width becomes one permission rank. This is admissible: authorization weakens, but does not strengthen.

Level 5 intentionally uses a skeleton-truncating two-gap profile rather than the inherited conservative map. This profile erases the AEX permission skeleton from the projected vocabulary. The profile builder can only check whether the generic gaps are open or satisfied. With the merged gaps satisfied, the compiler returns AEX.

This is the violation. No evidence has improved; only the implemented representation changed. The projected compiler returns a stronger permission than the fine evidence warrants for the affected cases:

$$
\widehat A^\pi(\pi(e))\npreceq A(e).
$$

The Level 5 result is not a bad data point. It is the witness that admissibility is non-vacuous. A natural-looking simplification can fall outside the admissible class because it erases the permission skeleton.

![Figure 4. Projection fidelity and admissibility.](figures/fig4_projection_fidelity.png)

---

### 2.7 Two-axis convergence is the central conservation experiment

The previous experiments test the two approximation axes separately. Permission densification fixes the evidence representation and refines the grid. Occlusion and projection fidelity fix the permission scale and alter the evidence representation. The central experiment moves both axes at once.

This section makes one structural distinction explicit. The canonical-map matrix and the targeted controls answer different questions. The canonical matrix asks whether a fixed admissible requirement map converges under resolving evidence refinement and permission densification. The controls ask whether the same machinery can realize the missing floor level and whether later splits can carry signal when a targeted active blocker is present. The combined stress test spans the full implemented permission chain, but it is not described as one experiment under one requirement map.

#### 2.7.1 Canonical-map coverage and targeted controls

The v3 run contains 21 cases: seven induction cases M01--M07, five held-out cases H01--H05, five synthetic level-ladder cases S-REF, S-DIA, S-REV, S-AEX and S-ALR, and four active-refinement witnesses W-currency, W-deployment, W-population and W-clinical.

A requirement-map audit separates these cases into two classes. Sixteen cases use the canonical admissible requirement map: the seven induction cases, the five held-out cases and the synthetic ladder cases S-DIA, S-REV, S-AEX and S-ALR. These canonical cases exercise four permission levels,

$$
\mathrm{DIA}\prec\mathrm{REV}\prec\mathrm{AEX}\prec\mathrm{ALR}.
$$

The canonical map does not produce a REF endpoint in the tested case family. Full-chain REF-to-ALR coverage therefore requires targeted controls. S-REF uses a declared strict-floor map to realize REF. The four active-refinement witnesses each modify one ALR requirement from canonical bounded to strict closed in order to test a single target split. These five cases are not evidence for a single-map full-chain theorem; they are controls with declared non-canonical maps.

The paper reports both facts because each is useful. The fixed-map result is the clean conservation experiment. The targeted controls show that the compiler can realize the floor and that later refinements can carry signal when a blocker is constructed to be active.

#### 2.7.2 Resolving path under the canonical map

The resolving path is

$$
L4\to L3\to L2\to L1\to L0.
$$

At every level it uses the admissible join projection: composite statuses are meets of component statuses, and composite requirements are joins of inherited fine requirements. The permission-grid settings are

$$
k\in\{4,8,16,32,64\}.
$$

On the 16 canonical-map cases, the resolving path contains 400 tested cells. Every cell is sound, every evidence-refinement check is monotone, every permission-refinement check is monotone, and every case converges at the final representation:

| Matrix | Cells | Sound | Monotone in evidence refinement | Monotone in permission refinement | Jointly converged |
|---|---:|---:|---:|---:|---:|
| Canonical resolving path | 400 | 400 | 400 | 400 | 16/16 |

Including the five declared controls gives the larger stress-test matrix:

| Matrix | Cells | Sound | Monotone in evidence refinement | Monotone in permission refinement | Jointly converged |
|---|---:|---:|---:|---:|---:|
| Resolving path, canonical plus controls | 525 | 525 | 525 | 525 | 21/21 |

The second line is not used to claim that a single requirement map spans REF through ALR. It shows that, once each case's declared map is fixed, the resolving path behaves exactly as the conservation law predicts in every tested cell.

#### 2.7.3 Active-refinement witnesses show that later splits can carry signal

In the original Epic cases, later refinements after the evidence-currency split are inert because the active blocker has already been resolved and no later split crosses a permission boundary. To test whether this inertness is an artifact of the refinement machinery, we add four active-refinement witnesses.

Each witness uses conservative composite semantics plus join-of-fine-requirements. One component of a composite has a closed ALR requirement and closed status. Its sibling has bounded status and a weaker requirement. Before the split, the composite status is bounded by the meet, while the composite ALR requirement is closed by the join. ALR is blocked at the merged level. After the split, the strict component satisfies its closed requirement and the sibling no longer poisons it.

The witnesses fire exactly at their target splits and are inert elsewhere:

| Witness | Target split | L4 | L3 | L2 | L1 | L0 |
|---|---|---|---|---|---|---|
| W-currency | L4→L3 | AEX | ALR | ALR | ALR | ALR |
| W-deployment | L3→L2 | AEX | AEX | ALR | ALR | ALR |
| W-population | L2→L1 | AEX | AEX | AEX | ALR | ALR |
| W-clinical | L1→L0 | AEX | AEX | AEX | AEX | ALR |

The conclusion is deliberately scoped. The witnesses establish that inertness is not a property of the refinement machinery itself: when a single-poison active blocker is present in a coarsened composite, splitting resolves the block and raises the emit. An inert split therefore certifies that no single-poison active blocker of this tested form is present in the split composite. We do not prove that single-poison is the only mechanism by which a split could carry signal.

#### 2.7.4 Non-resolving paths localize transient violations

The non-resolving path used in the main matrix is

$$
L5\to L4\to L3\to L2\to L1\to L0.
$$

At L5 only, the path uses a skeleton-truncating projection profile. From L4 onward, it returns to the admissible join projection. This makes the inadmissibility a property of the projection rule, not of any individual case.

On the 16 canonical-map cases, the non-resolving path contains 480 tested cells. It remains monotone in permission refinement in all cells and converges at the final resolving endpoint for every case, but it loses the guarantees that require admissibility and resolving refinement:

| Matrix | Cells | Sound | Monotone in evidence refinement | Monotone in permission refinement | Jointly converged |
|---|---:|---:|---:|---:|---:|
| Canonical non-resolving path | 480 | 470 | 420 | 480 | 16/16 |

Including the five controls gives the larger stress-test matrix:

| Matrix | Cells | Sound | Monotone in evidence refinement | Monotone in permission refinement | Jointly converged |
|---|---:|---:|---:|---:|---:|
| Non-resolving path, canonical plus controls | 630 | 620 | 550 | 630 | 21/21 |

The failure decomposition is more informative than the aggregate counts. There are 10 unsound cells. All occur at L5. They are H02 and S-REV across all five reported \(k\)-settings. In both cases the reference authorization is REV, while the skeleton-truncating L5 projection emits AEX. The `sound` flag in this matrix is categorical: it compares the emitted permission with the reference permission before any score-flooring diagnostic. A separate score-floored statistic would require its own grid-resolution condition and could hide adjacent-category over-authorization on an under-resolved grid. That is not the statistic counted here.

There are 80 evidence-axis monotonicity failures in the full stress test, all at the transition L5→L4. These failures occur when the admissible skeleton is restored and inflated permissions drop. In the canonical submatrix, 60 such failures occur: 12 canonical cases across five reported \(k\)-settings. The remaining 20 occur in the four active-refinement controls. The five cases with no L5→L4 monotonicity failure are H03, S-REF, S-DIA, S-AEX and S-ALR; in those cases the truncating projection cannot produce a higher emit than the restored admissible projection at that transition.

This pattern is structural. Let \(K\) be the set of permission-grid settings, with \(|K|=5\). Let

$$
U=\{e:\widehat A_{\mathrm{trunc}}(e)\succ A(e)\}
$$

be the cases over-authorized by the skeleton-truncating projection. In this experiment, \(U=\{\mathrm{H02},\mathrm{S\text{-}REV}\}\), so each truncating step contributes

$$
|U|\,|K|=2\cdot5=10
$$

unsound cells. Let

$$
R=\{e:\widehat A_{\mathrm{trunc}}(e)\succ \widehat A_{\mathrm{restored}}(e)\}
$$

be the cases whose emitted permission drops when the admissible skeleton is restored. In the full stress test, \(|R|=16\), so each restoration transition contributes

$$
|R|\,|K|=16\cdot5=80
$$

monotonicity failures. Unsoundness and monotonicity failure are therefore different phenomena: unsoundness is over-authorization relative to \(A(e)\); monotonicity failure is a drop relative to the immediately preceding inadmissible representation.

A four-path-shape stress test confirms that these failures localize to the inadmissible and restoration sites rather than diffusing through the path. A path with a truncating projection at the start, a path with truncation in the middle and a path with two truncating projections all reconverge once they enter a resolving tail. Each truncating step contributes the same 10 structurally eligible unsound cells. Each restoration transition contributes the same 80 structurally eligible monotonicity failures. A terminal-truncation path with no resolving tail does not recover the two over-authorized REV cases, and therefore converges in 19 of 21 cases rather than 21 of 21.

| Path shape | Inadmissible location | Resolving tail? | Final convergence | Localized violations |
|---|---|---|---|---|
| Start truncation | step 0 | yes | 21/21 | 10 unsound cells; 80 restoration monotonicity failures |
| Middle truncation | step 1 | yes | 21/21 | 10 unsound cells; 80 restoration monotonicity failures |
| Double truncation | steps 0 and 2 | yes | 21/21 | two copies of the same localized pattern |
| Terminal truncation | final step | no | 19/21 | 10 terminal unsound cells; no restoration transition |

The theorem boundary is therefore precise. Prefix admissibility is not required for eventual recovery if the path later enters a resolving, asymptotically meet-exact tail. Prefix inadmissibility determines the location and size of transient violations. If the path ends in a non-admissible truncation and has no resolving tail, the over-authorized cases need not reconverge.

#### 2.7.5 Central result

Under a fixed canonical map, resolving refinement recovers the latent authorization value from below across 16 DIA-through-ALR cases with no soundness or monotonicity violations. Targeted controls extend the stress test to REF and verify that later refinements can carry signal when single-poison active blockers are present. Non-resolving path shapes show that skeleton-truncating projections produce localized, structurally predictable transient violations, and that reconvergence is governed by the resolving tail.

This is the implemented conservation law.

![Figure 5. Two-axis convergence and path-shape boundary.](figures/fig5_two_axis_convergence.png)

---

### 2.8 External standards as correspondence audits

The previous results validate the compiler and conservation law under controlled transformations. We now ask a different question: how do external regulatory standards relate to the latent authorization structure induced by supplied evidence packages?

These tests are correspondence audits. They do not have equal independence, and they are not treated as the primary validation of the theory.

We classify six relationships:

1. **Exact recovery:** compiler threshold and external threshold identify the same fixed point.
2. **Representation-relative alignment:** compiler and external standard agree under the supplied representation but diverge under hierarchy perturbation.
3. **Same-axis policy margin:** compiler and external standard use the same evidence axis, but the external standard includes a safety margin, tolerance, rounding convention, equipment condition or policy choice not forced by the evidence package.
4. **Different evidence axis:** the standard covers a dimension not contained in the supplied evidence map.
5. **Hierarchy-placement failure:** a real gap exists but is placed at the wrong permission level.
6. **Outside supplied package:** the compiler is silent because the relevant gap is not represented.

#### FAA CAT I

The compiler derives the RVR-floor-vs-decision-height curve from glide-slope geometry without using the FAA CAT I threshold. At the standard CAT I decision height \(H=200\) ft, the frozen geometric model gives

$$
\mathrm{RVR}_{\mathrm{floor}}(200)=\frac{200-50}{\tan(3^\circ)}-1000\approx 1862\ \mathrm{ft}.
$$

The corresponding FAA CAT I minimum for suitably equipped runways is RVR 1,800 ft. The difference is 62 ft, or approximately 3.4% of the regulatory value. The curve crosses 1,800 ft at \(H\approx196.7\) ft.

This is not exact recovery. It is independent-route, same-axis policy-margin convergence. The evidence-derived geometry lands on the same visual-range axis and within the regulatory bin, while the residual identifies policy, rounding or equipment conventions not present in the supplied geometric package.

#### 3GPP BLER thresholds

Under the frozen hierarchy, the compiler aligns with 10% and 2% BLER thresholds. Under 59 hierarchy perturbations, recovery of 0.10 falls to 5.1%, and recovery of 0.02 falls to 3.4%, with zero recovery in structured perturbation families.

The alignment is representation-relative. The thresholds are not hierarchy-independent ridges of the latent function.

#### FDA AI/ML deployment gaps

The gap list induced from documented AI deployment failures -- including Epic, Optum, PredPol, COMPAS and Watson -- recovers categories that align with FDA AI/ML action-plan obligations. This is a same-axis policy correspondence from overlapping evidence, not an independent derivation. The regulator and compiler draw partly from the same public failure record.

#### ECOA reason traceability

The compiler induces G7, reason traceability, from credit and adverse-action failures. ECOA Regulation B requires adverse-action notices with specific reasons. Within the supplied adverse-action representation, the legal requirement and the induced gap identify the same authorization boundary.

This is exact recovery in the zero-gap sense: the supplied evidence representation determines a unique authorization value at the reason-traceability boundary.

#### FAA CAT II/III

CAT II and CAT III minima depend on evidence axes not present in the CAT I visual-geometry package: autoland, fail-operational systems, aircraft equipment, operator qualification and additional procedural controls. The compiler is silent on these axes because the supplied package does not represent them.

Silence is not permission. It means the supplied evidence map cannot authorize or refuse on that dimension.

#### Amazon recruiting

Amazon recruiting is held out from the taxonomy induction. The model-specification gap G2 is real and present in the induced package. The disagreement is a hierarchy-placement failure: the gap was identified, but the hierarchy placed it below the AEX requirement threshold, allowing AEX to proceed without closing it.

This distinction matters. A missing-gap failure and a hierarchy-placement failure require different repairs.

![Figure 7. External standards as correspondence audits.](figures/fig7_external_correspondence.png)

---

## 3. Discussion

This paper introduces a computational object for a problem that is usually handled by convention. Approximate systems do not merely predict. They authorize action. The central question is therefore not only whether a statistic is accurate, calibrated or robust. It is what action the statistic can soundly license under incomplete evidence.

The latent authorization function answers this question conditionally: given an evidence map, a permission order and world-level soundness semantics, the strongest evidence-supported action is the meet over compatible worlds. The answer is canonical only after those ingredients are supplied. The calculus does not choose the evidence map. It does not choose the permission hierarchy. It does not decide institutional risk tolerance. It separates the authorization forced by evidence from the permission added by policy and representation.

The separation from decision theory is intentional. A maximin or distributionally robust decision rule chooses an action by optimizing a loss or payoff against an uncertainty set. A forecast-value calculation asks whether information improves expected utility for a decision maker. The latent authorization function is neither an ambiguity-set optimizer nor an expected-utility value. It is an order-theoretic ceiling induced by the evidence fiber. Its distinctive invariance claim is not that worst-case reasoning is new, but that admissible changes of evidence representation may weaken, refine or relabel this ceiling without creating permission unsupported by the compatible worlds.

This separation gives three practical tools.

First, a finite permission hierarchy can be audited as an instrument. Densification reveals whether observed thresholds are smooth grid artifacts, genuine structural steps or evidence-axis transitions.

Second, evidence representations can be audited for admissibility. A coarser vocabulary may be useful, but it is safe only if it cannot return stronger permission than the finer evidence supports. The Epic projection experiment shows why this condition is non-vacuous: compactness can erase the permission skeleton.

Third, joint refinement can be tested. Under the canonical requirement map, the resolving path recovers the latent authorization value from below across the DIA-through-ALR portion of the implemented chain. Declared targeted controls add the synthetic REF floor and active-refinement witnesses without pretending that all 21 cases share one requirement map. The non-resolving path shows that a skeleton-truncating projection can lose soundness and evidence-axis monotonicity exactly where the theorem's hypotheses fail, while still reconverging after entering a resolving tail.

This is why the result is a conservation law. Conservation does not mean authorization never changes. It means that admissible representation change cannot create unsupported permission. Authorization may weaken when evidence is hidden. It may sharpen when evidence or permission resolution improves. It may be relabelled under order-preserving transformations. But it cannot be manufactured by changing the representation while leaving the evidence unchanged.

The regulatory correspondences should be read cautiously. They are not evidence that all regulation secretly computes the same law. They show that several external standards can be classified in the language of the calculus: exact recovery, same-axis margin, representation-relative alignment, different evidence axis, hierarchy-placement failure or outside-package silence. This classification is itself useful because it prevents false equivalence. FAA CAT I geometry is not the same kind of evidence as FDA deployment guidance. ECOA reason traceability is not the same kind of evidence as 3GPP threshold alignment. A single framework can compare them without pretending they have equal independence.

The main limitation is that the calculus is conditional. If the supplied evidence map erases a relevant distinction, \(A(e)\) will be conservative relative to the enlarged fiber. If the supplied permission hierarchy places a real gap at the wrong level, the compiler will faithfully implement that mistake. If the world-level authorization function is misspecified, the meet will preserve the wrong semantics. These are not implementation bugs. They are the boundary between authorization checking and domain judgment.

A second limitation is that the empirical domains are role-based demonstrations, not a representative sample. Turbo, Ising and FAA geometry are chosen to span regularity classes. Epic and ILS are chosen to test gap hierarchies. The two-axis matrix is chosen to stress the theorem boundary across the implemented permission chain. Regulatory standards are used as correspondence audits. The paper does not claim prevalence estimates across deployed AI systems.

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

$$
\mathrm{open}\prec\mathrm{bounded}\prec\mathrm{closed}.
$$

A requirement cell specifies the minimum status sufficient for that gap at that permission level. A gap with observed status \(s\) satisfies requirement \(r\) exactly when

$$
r\preceq s.
$$

A requirement of `open` is vacuous. A requirement of `bounded` is satisfied by `bounded` or `closed`. A requirement of `closed` is satisfied only by `closed`.

The compiler traverses the permission hierarchy from strongest to weakest and returns the first level whose gap requirements are all satisfied. If no non-bottom level is satisfied, it returns REF. Computation is deterministic given the evidence state, permission hierarchy and requirement map. The source that proposed a gap is not an input to the compiler.

Implementation paths:

- `python/noethers_turnstile/__init__.py`
- `python/noethers_turnstile/_turnstile.so`
- `examples/conservation/`

### 4.2 Permission densification

For a finite grid \(P_k\), the mathematical compiler output is

$$
C_k(e)=\lfloor A(e)\rfloor_{P_k}.
$$

For plotting and breakpoint counting, this lattice element is represented by the normalized rank score

$$
s_k(e)=\frac{\#\{p\in P_k:p\preceq A(e)\}}{|P_k|}.
$$

The score is an order-preserving relabelling under the threshold-count representation. No authorization claim depends on the normalization.

Uniform or log-uniform threshold grids are used depending on the evidence axis.

- Uniform grids are used for bounded linear quantities such as TV distance or RVR.
- Log-uniform grids are used for error rates spanning orders of magnitude.

Breakpoints are counted as swept-axis values where \(s_k\) changes. The swept axes are SNR for turbo, authorization tolerance \(\tau\) for Ising, and decision height \(H\) for FAA geometry.

Implementation path:

- `examples/conservation/run_densification.py`

### 4.3 Turbo experiment

BER data are digitized from Berrou et al. [1] over a 12-point grid from \(-1.0\) to \(5.0\) dB SNR. For denser SNR grids, the digitized BER curve is interpolated piecewise linearly on the \(\log_{10}\mathrm{BER}\) scale as a function of SNR. The interpolated BER is transformed to the independent-bit BLER reference curve

$$
\mathrm{BLER}_{\mathrm{ref}}=1-(1-\mathrm{BER})^L,
$$

with block length

$$
L=65{,}536.
$$

This is not asserted to be the measured turbo-code BLER law. It is a reference curve for mean-to-block amplification.

Permission hierarchy:

- REFUSE when \(\mathrm{BLER}>0.10\);
- HOLD when \(\mathrm{BLER}\leq0.10\);
- TRANSMIT_MONITORED when \(\mathrm{BLER}\leq0.02\);
- TRANSMIT when \(\mathrm{BLER}\leq0.001\).

Log-uniform BLER thresholds are drawn over \([10^{-4},1.0]\). The SNR-resolution check fixes \(k=256\) and varies the SNR grid from 61 to 1,952 points.

Implementation paths:

- `examples/conservation/run_permissivity_path.py`
- `examples/conservation/run_densification.py`

### 4.4 Ising experiment

A \(6\times6\) Ising grid is evaluated at coupling \(\beta=0.44\). The graph is the open-boundary square lattice with uniform ferromagnetic nearest-neighbor coupling and zero external field. No random couplings are drawn.

Exact marginals are computed by full enumeration over \(2^{36}\) states. BP marginals are computed by synchronous loopy belief propagation with 100 iterations and convergence threshold \(10^{-6}\). Per-variable TV is

$$
\frac{1}{2}\sum_x |p_{\mathrm{BP}}(x)-p_{\mathrm{exact}}(x)|.
$$

Mean TV is 0.2231. Max TV is 0.3338. Uniform \(\tau\)-grids are drawn over \([0,0.50]\). The densification axis is the authorization tolerance \(\tau\), not a sweep over multiple Ising worlds.

Implementation paths:

- `examples/inference/ising/`
- `examples/conservation/run_densification.py`

### 4.5 FAA geometry experiment

Glide slope is \(3^\circ\) to runway threshold. Decision height is altitude above touchdown zone. The RVR floor is

$$
\mathrm{RVR}_{\mathrm{floor}}(H)=\max\left(0,\frac{H-50}{\tan(3^\circ)}-1000\right),
$$

where \(H\) is decision height in feet. Saturation occurs at

$$
H_{\mathrm{sat}}=50+1000\tan(3^\circ)\approx102.4\ \mathrm{ft}.
$$

At \(H=200\) ft, the frozen geometry gives

$$
\mathrm{RVR}_{\mathrm{floor}}(200)\approx1862\ \mathrm{ft}.
$$

The curve crosses RVR \(=1800\) ft at \(H\approx196.7\) ft. Uniform RVR thresholds are drawn over \([0,2400]\) ft.

Implementation path:

- `examples/ils/geometry.py`

### 4.6 Occlusion sweeps

The ILS hierarchy uses three gaps: signal integrity, visual reference and sub-CAT-I authorization. The minimum requirements are:

| Permission | Signal integrity | Visual reference | Sub-CAT-I authorization |
|---|---|---|---|
| ALR | closed | closed | closed |
| REV | closed | closed | open |
| DIA | closed | open | open |
| REF | open | open | open |

Opening authorization drops ALR to REV. Opening visual reference drops REV to DIA. Opening signal integrity drops DIA to REF.

The Epic hierarchy uses nine gaps: S1, S2 and G1--G7. The requirement matrix is:

| Permission | S1 approximation quality | S2 freshness | G1 clinical utility | G2 model specification | G3 distribution shift | G4 individual-population scope | G5 blast radius | G6 authority/rollback | G7 reason traceability |
|---|---|---|---|---|---|---|---|---|---|
| ALR | closed | closed | closed | closed | closed | closed | closed | closed | closed |
| AEX | closed | bounded | open | open | open | open | open | open | open |
| REV | bounded | open | open | open | open | open | open | open | open |
| DIA | open | open | open | open | open | open | open | open | open |
| REF | open | open | open | open | open | open | open | open | open |

The starting state sets all gaps to the status required for ALR. Gaps are opened in sequence: G1, G2, G3, G4, G5, G6, G7, S2, S1.

Implementation path:

- `examples/conservation/run_occlusion_sweep.py`

### 4.7 Projection fidelity

The projection-fidelity experiment applies six projected representations to the Epic evidence package.

- L0: all 9 gaps.
- L1: merge G1+G2 into model adequacy or clinical efficacy.
- L2: merge G3+G4 into population scope.
- L3: merge G5+G6 into deployment control.
- L4: merge G7+S2 into evidence currency.
- L5: collapse S1+S2 into evidence quality and G1--G7 into evidence scope.

For admissible projections, composite-gap semantics are conservative. The observed status of a composite gap is the meet of component statuses under

$$
\mathrm{open}\prec\mathrm{bounded}\prec\mathrm{closed}.
$$

At each permission level, the composite requirement is the join, i.e. the strongest minimum requirement, among the component requirements inherited from the fine hierarchy. A composite gap is satisfied only when its components would have satisfied their inherited fine-level obligations.

L5 intentionally uses a collapsed skeleton-truncating profile builder rather than the inherited conservative map. Its generic requirements erase the AEX skeleton. This makes L5 the non-vacuity witness for inadmissibility.

Implementation path:

- `examples/conservation/run_projection_fidelity.py`

### 4.8 Two-axis convergence matrices

The two-axis experiment is implemented in:

- `examples/conservation/run_two_axis_convergence_v2.py`

The output files are:

- `examples/conservation/results/two_axis_convergence_v2_matrix.csv`
- `examples/conservation/results/two_axis_convergence_v2_summary.csv`
- `examples/conservation/results/two_axis_convergence_v2_admissibility.csv`

The matrix has 1,155 rows. Each row corresponds to one tuple

$$
(\mathrm{path},\mathrm{case},m,k),
$$

where `path` is resolving or non-resolving, `case` is one of the 21 cases, \(m\) is the evidence representation level, and \(k\) is the reported permission-grid setting. This matrix is a finite-chain implementation audit, not the breakpoint-densification diagnostic of §2.4. The row records the categorical permission emitted by the compiler, an order-preserving normalized rank code \(C_{m,k}\), the reference authorization score \(A(e)\), the gap, soundness, evidence-axis monotonicity and permission-axis monotonicity. The `sound`, `monotone_m` and `monotone_n` flags are computed from categorical permissions. They are therefore replicated across the reported \(k\)-settings when the categorical emit is unchanged. A score-flooring analysis would be a different diagnostic and would require explicit grid-resolution hypotheses.

A requirement-map audit partitions the 21 cases into 16 canonical-map cases and five targeted controls. The canonical cases are M01--M07, H01--H05, S-DIA, S-REV, S-AEX and S-ALR. The targeted controls are S-REF and the four active-refinement witnesses. Aggregate 21-case summaries are reported only as stress-test summaries; fixed-map conservation claims are reported on the 16-case canonical submatrix.

The resolving path is

$$
L4\to L3\to L2\to L1\to L0.
$$

The non-resolving path is

$$
L5\to L4\to L3\to L2\to L1\to L0.
$$

Only L5 is inadmissible in the non-resolving path. From L4 onward, the path uses the same admissible join projection as the resolving path.

The summary file has 42 rows, one for each path-case pair. It aggregates cell count, soundness count, evidence-axis monotonicity count, permission-axis monotonicity count and final convergence. The admissibility file records the 10 unsound L5 cells.

### 4.9 Active-refinement witnesses

The active-refinement witnesses are targeted synthetic controls under conservative composite semantics. They are not part of the canonical-map coverage claim.

For a target composite \(X=(x_s,x_p)\), let \(x_s\) be the strict component and \(x_p\) the poisoning sibling. The construction sets

$$
s(x_s)=\mathrm{closed},
\qquad
r(x_s)=\mathrm{closed},
$$

and

$$
s(x_p)=\mathrm{bounded},
\qquad
r(x_p)\preceq \mathrm{bounded}.
$$

The projected composite status is the meet:

$$
s(X)=s(x_s)\wedge s(x_p)=\mathrm{bounded}.
$$

The projected composite requirement is the join:

$$
r(X)=r(x_s)\vee r(x_p)=\mathrm{closed}.
$$

Thus the composite fails before the split. After the split, \(x_s\) satisfies the strict requirement and \(x_p\) no longer poisons it. If all other requirements are satisfied, permission rises exactly at the target split.

The four witnesses target the four refinements:

- W-currency: L4→L3;
- W-deployment: L3→L2;
- W-population: L2→L1;
- W-clinical: L1→L0.

The inference drawn from these witnesses is intentionally limited: they certify that the refinement machinery can carry signal when a single-poison active blocker is present. They do not prove that every possible signal-carrying split must have this form.

### 4.10 Path-shape stress test

The non-resolving boundary is tested with four path shapes generated by:

- `examples/conservation/run_path_shapes.py`

The output file is:

- `examples/conservation/results/path_shapes_matrix.csv`

The path shapes place the skeleton-truncating projection at the start, in the middle, at two positions, or at the terminal step. For each shape, the same cases and permission grids are evaluated. The stress test records whether unsound cells localize to truncating steps, whether monotonicity failures localize to restoration transitions, and whether final convergence is recovered once a resolving tail is present.

For the reported run, the unsound-eligible set is

$$
U=\{\mathrm{H02},\mathrm{S\text{-}REV}\},
$$

and the restoration-drop set has size \(|R|=16\). With five reported \(k\)-settings, each truncating step contributes \(2\cdot5=10\) unsound cells and each restoration transition contributes \(16\cdot5=80\) evidence-axis monotonicity failures. A terminal truncation has no restoration transition and lacks a resolving tail; it converges in 19 of 21 cases.

### 4.11 Blind regulatory audit protocol
### 4.10 Blind regulatory audit protocol

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

All numerical values reported in the paper are generated from deterministic scripts under `examples/conservation/results/` and the domain-specific example folders listed in Methods. The v3 two-axis experiment writes the full matrix, summary and admissibility files as `two_axis_convergence_v2_matrix.csv`, `two_axis_convergence_v2_summary.csv` and `two_axis_convergence_v2_admissibility.csv`. The regulatory correspondence audit is represented as a provenance table in `docs/provenance.md`. No private patient-level, applicant-level or individual-level data are used.

---

## 6. Code availability

The compiler is implemented in Rust with Python bindings under `python/noethers_turnstile/`. Experiment scripts are listed in Methods. The two-axis v3 result is generated by `examples/conservation/run_two_axis_convergence_v2.py`. Figure generation is under `docs/pivot/figures/generate_figures.py`. A public release archive, commit hash and persistent identifier should be supplied with the submission package.

---

## 7. Ethics and human subjects

This work uses public incident reports, public regulatory standards, synthetic or deterministic computational examples and hand-constructed evidence packages. It does not use human-subject records, patient-level data, applicant-level data or private institutional data.

---

## 8. Competing interests

The author declares no competing interests.

---

## 9. Author contributions

A.S. conceived the study, developed the latent authorization calculus, implemented the compiler and experiments, analyzed the results and wrote the manuscript.

---

## 10. Acknowledgements

The author thanks the reviewers and colleagues whose comments sharpened the distinction between theoremic convergence, implemented conservation and regulatory correspondence. Any remaining errors are the author's own.

---

# Appendix A. Proofs

## A.1 Finite lower-approximation law

Recall

$$
C_k(e)=\lfloor A(e)\rfloor_{P_k}
$$

and

$$
\lfloor x\rfloor_{P_k}=\max\{p\in P_k:p\preceq x\}.
$$

**Theorem A.1.** For every evidence state \(e\):

1. **Soundness.** For every finite grid \(P_k\),

   $$
   C_k(e)\preceq A(e).
   $$

2. **Monotone grid refinement.** If \(P_k\subseteq P_{k+1}\), then

   $$
   C_k(e)\preceq C_{k+1}(e)\preceq A(e).
   $$

3. **Dense-grid convergence.** If \((P_k)\) resolves \(\mathcal A\) from below, then

   $$
   C_k(e)\nearrow A(e).
   $$

**Proof.** By definition, \(C_k(e)\) is chosen from permissions \(p\in P_k\) satisfying \(p\preceq A(e)\). Therefore \(C_k(e)\preceq A(e)\). Since \(A(e)\) is sound for every world in \(F(e)\), every weaker permission is also sound.

If \(P_k\subseteq P_{k+1}\), the feasible set defining \(C_k(e)\) is contained in the feasible set defining \(C_{k+1}(e)\). Taking the maximum over a larger feasible set can only increase or preserve the result, so \(C_k(e)\preceq C_{k+1}(e)\). Soundness gives \(C_{k+1}(e)\preceq A(e)\).

If \((P_k)\) resolves \(\mathcal A\) from below, then for every \(x\in\mathcal A\),

$$
\bigvee_k \lfloor x\rfloor_{P_k}=x.
$$

Applying this to \(x=A(e)\),

$$
\bigvee_k C_k(e)=\bigvee_k\lfloor A(e)\rfloor_{P_k}=A(e).
$$

Thus \(C_k(e)\) converges to \(A(e)\) from below. When grids are not nested but their mesh size tends to zero, pointwise monotonicity need not hold at every \(k\), but convergence still follows whenever the floor error tends to zero. \(\square\)

---

## A.2 Conservative coarsening law

For a projection \(\pi:E\to\bar E\), define

$$
F_\pi(\bar e)=\{w\in W:\pi(q(w))=\bar e\}.
$$

For every fine evidence state \(e\),

$$
F(e)\subseteq F_\pi(\pi(e)).
$$

The projected fiber is larger. Taking the meet over a larger set can only weaken or preserve the result:

$$
A^\pi(\pi(e))=
\bigwedge_{w\in F_\pi(\pi(e))}a(w)
\preceq
\bigwedge_{w\in F(e)}a(w)=A(e).
$$

Equivalently,

$$
A^\pi(\bar e)=\bigwedge_{e'\in\pi^{-1}(\bar e)}A(e').
$$

Let \(\widehat A^\pi\) be an implemented projected authorization function. The implementation is authorization-admissible if

$$
\widehat A^\pi(\pi(e))\preceq A(e)
\quad\text{for all }e\in E.
$$

This condition is equivalent to

$$
\widehat A^\pi(\bar e)\preceq A^\pi(\bar e)
\quad\text{for all }\bar e\in\bar E.
$$

To see this, fix \(\bar e\). The first inequality must hold for every fine state \(e'\in\pi^{-1}(\bar e)\). Therefore \(\widehat A^\pi(\bar e)\) is a lower bound of the set \(\{A(e'):e'\in\pi^{-1}(\bar e)\}\). It is therefore no stronger than their meet \(A^\pi(\bar e)\). Conversely, if \(\widehat A^\pi(\bar e)\preceq A^\pi(\bar e)\), then for every \(e\in\pi^{-1}(\bar e)\),

$$
\widehat A^\pi(\pi(e))=\widehat A^\pi(\bar e)\preceq A^\pi(\bar e)\preceq A(e).
$$

Because the floor operator is monotone, an authorization-admissible implementation satisfies

$$
\lfloor\widehat A^\pi(\pi(e))\rfloor_{P_k}
\preceq
\lfloor A(e)\rfloor_{P_k}.
$$

Therefore

$$
C_k^\pi(\pi(e))\preceq C_k(e).
$$

This proves the conservative coarsening law. \(\square\)

---

## A.3 Semantic convergence under resolving refinement

Let \((\pi_m)\) be a refining evidence-projection sequence. For a fixed \(e\), define

$$
[e]_m=\{e'\in E:\pi_m(e')=\pi_m(e)\}.
$$

Refinement means

$$
[e]_{m+1}\subseteq[e]_m.
$$

The semantic projected authorization is

$$
A^{\pi_m}(\pi_m(e))=\bigwedge_{e'\in[e]_m}A(e').
$$

A refining sequence is resolving at \(e\) if, for every permission \(p\prec A(e)\), there exists \(m_0\) such that for all \(m\geq m_0\) and all \(e'\in[e]_m\),

$$
p\preceq A(e').
$$

**Theorem A.2.** If \((\pi_m)\) is refining and resolving at \(e\), then

$$
A^{\pi_m}(\pi_m(e))\nearrow A(e).
$$

**Proof.** Since \(e\in[e]_m\),

$$
A^{\pi_m}(\pi_m(e))\preceq A(e).
$$

Because \([e]_{m+1}\subseteq[e]_m\), the meet at level \(m+1\) is taken over a subset of the states used at level \(m\). Taking a meet over a smaller set can only strengthen or preserve the result:

$$
A^{\pi_m}(\pi_m(e))\preceq A^{\pi_{m+1}}(\pi_{m+1}(e)).
$$

Thus the sequence is monotone nondecreasing and bounded above by \(A(e)\).

Let \(p\prec A(e)\). By resolving, eventually every \(e'\in[e]_m\) satisfies \(p\preceq A(e')\). Therefore \(p\) is a lower bound for \(\{A(e'):e'\in[e]_m\}\), so

$$
p\preceq A^{\pi_m}(\pi_m(e))
$$

eventually. Every permission strictly below \(A(e)\) is eventually below the projected authorization, and the projected authorization is always no stronger than \(A(e)\). Hence the supremum is exactly \(A(e)\). \(\square\)

---

## A.4 Joint implemented convergence

Let \((\pi_m)\) be refining and resolving at \(e\), and let

$$
\widehat A_m:E_m\to\mathcal A
$$

be the implemented authorization function at resolution \(m\).

The implementation is asymptotically meet-exact at \(e\) if it is conservative relative to the semantic projected meet,

$$
\widehat A_m(\pi_m(e))\preceq A^{\pi_m}(\pi_m(e)),
$$

and its eventual lower envelope converges to \(A(e)\):

$$
\bigvee_{M\geq1}\bigwedge_{m\geq M}\widehat A_m(\pi_m(e))=A(e).
$$

Define the two-axis compiler output

$$
C_{m,n}(e)=\left\lfloor\widehat A_m(\pi_m(e))\right\rfloor_{P_n}.
$$

**Theorem A.3.** Let \((\pi_m)\) be refining and resolving at \(e\). Let \((\pi_m,\widehat A_m)\) be asymptotically meet-exact at \(e\). Let \((P_n)\) resolve \(\mathcal A\) from below. Then \(C_{m,n}(e)\to A(e)\) from below along any cofinal refinement of both axes. That is, for every \(p\prec A(e)\), there exist \(m_0,n_0\) such that for all \(m\geq m_0\) and \(n\geq n_0\),

$$
p\preceq C_{m,n}(e)\preceq A(e).
$$

**Proof.** Conservatism gives

$$
C_{m,n}(e)\preceq\widehat A_m(\pi_m(e))\preceq A(e),
$$

so every output is a lower bound on \(A(e)\).

Let \(p\prec A(e)\). In a finite permission chain, asymptotic meet-exactness implies eventual exactness: for sufficiently large \(m\), \(\widehat A_m(\pi_m(e))=A(e)\). Then

$$
C_{m,n}(e)=\lfloor A(e)\rfloor_{P_n}
$$

for sufficiently large \(m\), and Theorem A.1 gives convergence to \(A(e)\) from below as \(n\) increases.

In an order-dense lattice, choose \(s\) such that \(p\prec s\prec A(e)\). By asymptotic meet-exactness, eventually

$$
s\preceq\widehat A_m(\pi_m(e)).
$$

Because \((P_n)\) resolves \(\mathcal A\) from below, eventually the grid contains a point \(r_n\) satisfying

$$
p\preceq r_n\preceq s.
$$

For sufficiently large \(m,n\),

$$
p\preceq r_n\preceq s\preceq\widehat A_m(\pi_m(e)).
$$

Since \(r_n\) is a grid point no stronger than the implemented authorization, the floor must be at least \(r_n\). Thus

$$
p\preceq C_{m,n}(e)\preceq A(e)
$$

eventually. If the evidence projections and permission grids are nested, convergence is monotone. Otherwise, convergence from below does not imply pointwise monotonicity. \(\square\)

---

## A.5 Evidence-representation invariance

Two evidence representations

$$
q_1:W\to E_1,
\qquad
q_2:W\to E_2
$$

are authorization-equivalent if they induce the same evidence fibers up to relabelling. That is, there exists a bijection

$$
\psi:q_1(W)\to q_2(W)
$$

such that

$$
q_2=\psi\circ q_1.
$$

Then for any evidence state \(e\),

$$
F_2(\psi(e))=F_1(e).
$$

Therefore

$$
A_2(\psi(e))=
\bigwedge_{w\in F_2(\psi(e))}a(w)=
\bigwedge_{w\in F_1(e)}a(w)=A_1(e).
$$

Evidence representations with the same fibers induce the same latent authorization function up to relabelling. \(\square\)

---

## A.6 Permission relabelling invariance

Let \(\phi:\mathcal A\to\mathcal A'\) be an order isomorphism of permission lattices. Define

$$
a'(w)=\phi(a(w)).
$$

Since \(\phi\) is an order isomorphism, it preserves meets. Therefore

$$
A'(e)=\bigwedge_{w\in F(e)}a'(w)
=\bigwedge_{w\in F(e)}\phi(a(w))
=\phi\left(\bigwedge_{w\in F(e)}a(w)\right)
=\phi(A(e)).
$$

Changing the names or scale of permission values preserves the authorization structure when the order is unchanged. \(\square\)

---

## A.7 Exact recovery iff the fiber is authorization-constant

For an evidence state \(e\), define

$$
A(e)=\bigwedge_{w\in F(e)}a(w)
$$

and

$$
B(e)=\bigvee_{w\in F(e)}a(w).
$$

**Theorem A.4.** For an evidence state \(e\), the following are equivalent:

1. \(a(w)\) is constant over \(F(e)\);
2. \(A(e)=B(e)\);
3. the evidence \(e\) determines a unique authorization value.

**Proof.** If \(a(w)\) is constant over \(F(e)\), say \(a(w)=p\) for every \(w\in F(e)\), then both the meet and the join over the fiber are \(p\). Thus \(A(e)=B(e)=p\).

Conversely, suppose \(A(e)=B(e)=p\). For any \(w\in F(e)\),

$$
A(e)\preceq a(w)\preceq B(e).
$$

Since \(A(e)=B(e)=p\), it follows that \(a(w)=p\). Thus \(a\) is constant over the fiber. Evidence determines a unique authorization value exactly when all compatible worlds have the same world-level authorization. \(\square\)

---

## A.8 Order- and source-invariance

Suppose a fixed corpus determines a finite set \(G^\star\) of visible, policy-relevant failure modes. Suppose the induction procedure adds a gap whenever a processed case exposes a permissive disagreement blocked by that gap, never removes gaps, and eventually processes every case.

Each induction step adds an element of \(G^\star\). No step removes elements. Because every case is eventually processed, every gap in \(G^\star\) is eventually exposed and added. The terminal set is

$$
\bigcup_{\text{cases }c}g(c)=G^\star.
$$

Set union is commutative and associative, so the result does not depend on case order.

For source-invariance, fix evidence state \(e\), permission hierarchy \(P\) and requirement map \(R\). The compiler is a deterministic function

$$
C(e;P,R).
$$

No argument to this function records whether a gap was proposed by an expert, induced from a deployment failure, suggested by an LLM, copied from regulation or written by a developer. Therefore two evidence packages with identical gaps, statuses, permission hierarchy and requirement map produce identical compiler outputs. The source may affect epistemic trust in the evidence contract, but it does not affect compiler soundness relative to that contract. \(\square\)

---

## A.9 Active-refinement witness lemma

Let a projected composite gap \(X\) merge two fine gaps, \(x_s\) and \(x_p\). The projected status is the meet of fine statuses,

$$
s(X)=s(x_s)\wedge s(x_p),
$$

and the projected requirement at permission \(p\) is the join of fine requirements,

$$
r_p(X)=r_p(x_s)\vee r_p(x_p).
$$

Assume

$$
s(x_s)=\mathrm{closed},\qquad r_p(x_s)=\mathrm{closed},
$$

and

$$
s(x_p)=\mathrm{bounded},\qquad r_p(x_p)\preceq\mathrm{bounded}.
$$

Then at the projected level,

$$
s(X)=\mathrm{bounded},\qquad r_p(X)=\mathrm{closed},
$$

so the composite fails requirement \(p\). After refinement splits \(X\) into \(x_s,x_p\), the strict component satisfies its closed requirement and the poisoning sibling satisfies its weaker requirement. Therefore the obstruction caused by \(X\) is removed. If all other requirements for permission \(p\) are satisfied and all stronger permissions remain blocked, the compiler output strictly rises to \(p\) at that refinement step.

This lemma proves the positive witness direction only. It does not prove that every possible signal-carrying split must arise from a single-poison composite of this form. Accordingly, the paper uses the active-refinement witnesses as controls: they show that later refinements can carry signal when such a blocker exists, and they justify the narrower statement that inertness rules out this tested single-poison mechanism in the observed split. \(\square\)

---

## A.10 Localization of non-admissible transient violations

This proposition concerns the categorical localization counts reported in §2.7.4 and Supplementary Note 7. It does not assert a score-flooring invariant for under-resolved permission grids.

Let \\((\pi_m,\widehat A_m)\\) be an implemented evidence-projection path. Suppose one step \\(j\\) uses a skeleton-truncating projection \\(T\\), and suppose step \\(j+1\\), when present, restores an admissible projection \\(R\\). Let \\(K\\) be the set of reported \\(k\\)-settings. In the finite-chain matrix, each cell records a categorical emitted permission \\(p_m(e)\\). The normalized value \\(C_{m,k}\\) is an order-preserving rank code for that categorical emit in this localization audit; the `sound` flag is computed categorically:

$$
\mathrm{sound}(e,m,k)=1
\quad\Longleftrightarrow\quad
p_m(e)\preceq A(e).
$$

Define the unsound-eligible set for the truncating projection by

$$
U_T=\{e:p_T(e)\succ A(e)\}.
$$

Then the number of unsound cells contributed by the truncating step is

$$
|U_T|\,|K|.
$$

If a restored projection \\(R\\) follows \\(T\\), define the restoration-drop set by

$$
D_{T,R}=\{e:p_T(e)\succ p_R(e)\}.
$$

Then the number of evidence-axis monotonicity failures contributed by the restoration transition \\(T\to R\\) is

$$
|D_{T,R}|\,|K|.
$$

**Proof.** A cell at the truncating step is unsound exactly when its categorical emitted permission exceeds the reference authorization. This condition depends on \\(e\\) and \\(T\\), not on the reported \\(k\\)-setting, because the counted Boolean is categorical. Therefore every evidence state in \\(U_T\\) contributes one unsound row for each \\(k\in K\\), and no evidence state outside \\(U_T\\) contributes one.

Similarly, a restoration transition violates evidence-axis monotonicity exactly when the categorical emit drops from the truncating representation to the restored representation. Every evidence state in \\(D_{T,R}\\) contributes one such violation for each \\(k\in K\\), and no evidence state outside \\(D_{T,R}\\) contributes one. \\(\square\\)

The \\(k\\)-independence in this proposition is not because every reported \\(k\\)-grid resolves the full five-level permission chain. It is because the localization statistic is categorical. A separate score-floored comparison would require a grid-resolution condition; on an under-resolved grid, adjacent categorical permissions could collapse to the same score and hide over-authorization.

In the path-shape experiment, \\(|K|=5\\),

$$
U_T=\{\mathrm{H02},\mathrm{S\text{-}REV}\},
$$

and \\(|D_{T,R}|=16\\). Therefore each truncating step contributes \\(2\cdot5=10\\) categorical unsound cells, and each restoration transition contributes \\(16\cdot5=80\\) categorical evidence-axis monotonicity failures.

---

## A.11 Resolving-tail corollary

Theorem A.4 gives sufficient conditions for convergence from below along a resolving, asymptotically meet-exact refinement. The consequence used in §2.7.4 is a tail property.

Suppose an implemented path has a finite prefix, possibly containing non-admissible projections, followed from some index \(t\) onward by a resolving asymptotically meet-exact tail. Then the eventual lower envelope

$$
\bigvee_{M\geq t}\ \bigwedge_{m\geq M}\widehat A_m(\pi_m(e))
$$

is determined entirely by the tail. If the tail satisfies the hypotheses of Theorem A.4 at \(e\), this envelope is \(A(e)\). Finite prefixes can create transient unsoundness or monotonicity failures, but they do not change the eventual envelope after the prefix has been excluded from the tail meet.

This corollary is the formal reason that start, middle and double-truncation paths reconverge once they enter a resolving tail. It is also the reason a terminal-truncation path need not reconverge: when the path ends in a non-admissible projection, there is no later resolving tail whose lower envelope can recover \(A(e)\). \(\square\)

---

# Supplementary Notes

## Supplementary Note 1. Regulatory correspondence matrix

The full audit table is maintained in `docs/provenance.md`.

The held-out labels H01--H05 are audit-trail identifiers for held-out case templates. Only the subset relevant to external standards is discussed in Section 2.8. The two-axis convergence experiment uses all held-out templates to test compiler behavior, not to claim uniform regulatory recovery.

## Supplementary Note 2. 3GPP perturbation experiment

Fifty-nine hierarchies are tested: five granularity levels, four offsets and 50 random perturbations. Each hierarchy assigns different numerical values to BLER thresholds while preserving ordering structure.

Recovery of 0.10 occurs in 3/59 runs, or 5.1%. Recovery of 0.02 occurs in 2/59 runs, or 3.4%. Structured perturbation families show zero recovery.

Under the frozen hierarchy, both thresholds align. Under perturbation, they do not. The conclusion is representation-relative alignment, not hierarchy-independent recovery.

Implementation path:

- `examples/inference/register2/turbo/experiment_a_stability.py`

## Supplementary Note 3. Metric and representation invariance witnesses

Four functionals on the same Ising TV distribution are tested:

- F1: mean TV;
- F2: median TV;
- F3: 75th-percentile TV;
- F4: max TV.

They are tested at

$$
\beta\in\{0.20,0.30,0.40,0.44\}.
$$

F4 is largest at all \(\beta\), and all other functionals remain bounded below it. The ruler changes across functionals; the authorization ordering does not. This is an operational witness for representation invariance weaker than literal fiber identity.

The turbo analogue tests:

- T1: BER;
- T2: BER plus one standard deviation;
- T3: derived BLER reference curve.

Ordering holds at 61/61 SNR points.

Implementation path:

- `examples/conservation/run_metric_invariance.py`

## Supplementary Note 4. World-realizability witnesses

For each induced gap G1--G7, a world-realizability witness is a concrete deployment scenario where the gap is open, the system takes an over-authorized action, and a real failure occurs that is not merely a documentation failure.

| Gap | Witness scenario | Why the failure is world-realizable |
|---|---|---|
| G1 clinical utility | A sepsis alert has acceptable retrospective discrimination but no demonstrated clinical benefit at the deployed intervention threshold. | Clinicians receive actionable alerts, but patient outcomes or workflow burden make the intervention unsound despite predictive signal. |
| G2 model specification | A recruiting model is trained to predict historical resume-screening success and then used as if it measured job qualification. | The target variable is a proxy for prior institutional behavior, so the deployed action optimizes the wrong world-level property. |
| G3 distribution shift | A model trained and calibrated at one hospital, region or population is deployed in a different site with different base rates or measurement practices. | The same score no longer denotes the same risk; authorization based on the source distribution overstates what the target evidence supports. |
| G4 individual-population scope | Population-average performance is used to justify action on a subgroup or individual whose error profile is materially worse. | The mean statistic is true, but the action fails for compatible individuals hidden inside the evidence fiber. |
| G5 blast radius | An automated hold, denial or alert triggers many downstream actions without bounding the number of affected people or severity of consequences. | Local model error becomes system-level harm because propagation was not bounded. |
| G6 authority/rollback | An automated system continues consequential action after conditions change, without a clear authority boundary or rollback protocol. | The world contains no operative mechanism for stopping or reversing the action. |
| G7 reason traceability | A credit or adverse-action model cannot produce principal reasons connecting applicant inputs to the decision. | The denial occurs, but the system cannot generate reasons needed for review, contestation or legal notice. |

## Supplementary Note 5. Two-axis convergence matrix schema

The full two-axis matrix contains one row per path, case, evidence level and permission-grid setting. Fields are:

- `path`: resolving or nonresolving;
- `case_id`: case label;
- `family`: induction, held_out, synthetic_ladder or active_witness;
- `expert_judgment`: short case descriptor;
- `level`: evidence representation level;
- `level_name`: projected representation name;
- `n_gaps`: number of gaps visible at that level;
- `admissible`: whether the projection rule is admissible;
- `k`: permission-grid setting;
- `perm_m`: categorical compiler output;
- `C_mn`: normalized compiler score;
- `A_e`: reference authorization score;
- `gap`: \(A(e)-C_{m,n}(e)\);
- `sound`: whether \(C_{m,n}(e)\preceq A(e)\);
- `monotone_m`: evidence-axis monotonicity check;
- `monotone_n`: permission-axis monotonicity check.

The 16 canonical-map cases are M01--M07, H01--H05, S-DIA, S-REV, S-AEX and S-ALR. The five declared targeted controls are S-REF and W-currency, W-deployment, W-population and W-clinical.

Canonical-map summary:

| Path | Cells | Sound | Monotone in evidence refinement | Monotone in permission refinement | Jointly converged |
|---|---:|---:|---:|---:|---:|
| Resolving | 400 | 400 | 400 | 400 | 16/16 |
| Non-resolving | 480 | 470 | 420 | 480 | 16/16 |

Full stress-test summary, including targeted controls:

| Path | Cells | Sound | Monotone in evidence refinement | Monotone in permission refinement | Jointly converged |
|---|---:|---:|---:|---:|---:|
| Resolving | 525 | 525 | 525 | 525 | 21/21 |
| Non-resolving | 630 | 620 | 550 | 630 | 21/21 |

The non-resolving full stress test has 10 unsound cells and 80 evidence-axis monotonicity failures. All unsound cells occur at L5. All evidence-axis monotonicity failures occur at L5→L4. The canonical-map submatrix accounts for all 10 unsound cells and 60 of the 80 monotonicity failures; the active-refinement controls account for the remaining 20 monotonicity failures.

## Supplementary Note 6. Active-refinement controls

The active-refinement controls instantiate Appendix A.9. Each witness targets one split and uses a declared targeted map with one strict closed ALR requirement.

| Witness | Target split | L4 | L3 | L2 | L1 | L0 |
|---|---|---|---|---|---|---|
| W-currency | L4→L3 | AEX | ALR | ALR | ALR | ALR |
| W-deployment | L3→L2 | AEX | AEX | ALR | ALR | ALR |
| W-population | L2→L1 | AEX | AEX | AEX | ALR | ALR |
| W-clinical | L1→L0 | AEX | AEX | AEX | AEX | ALR |

Each transition is strict at the target split and inert elsewhere. This confirms that the resolving path can carry signal at every refinement level when the tested single-poison active blocker is present.

## Supplementary Note 7. Path-shape stress test

The path-shape experiment evaluates four placements of the skeleton-truncating projection.

| Path shape | Inadmissible location | Resolving tail? | Final convergence | Violation pattern |
|---|---|---|---|---|
| Start truncation | step 0 | yes | 21/21 | 10 unsound cells; 80 restoration monotonicity failures |
| Middle truncation | step 1 | yes | 21/21 | 10 unsound cells; 80 restoration monotonicity failures |
| Double truncation | steps 0 and 2 | yes | 21/21 | two localized copies of the same pattern |
| Terminal truncation | final step | no | 19/21 | 10 terminal unsound cells; no restoration transition |

The invariant is structural. In the reported case set, the truncating projection over-authorizes exactly H02 and S-REV, so each truncating step contributes \(2\times5=10\) unsound cells. The restored admissible projection lowers the inflated emit for 16 cases, so each restoration transition contributes \(16\times5=80\) evidence-axis monotonicity failures. The terminal path does not have a restoration transition and does not enter a resolving tail; the two over-authorized REV cases therefore remain divergent at the endpoint.

---

# Figure Captions

**Figure 1. The latent authorization function.** A finite permission grid reads \(A(e)\) as a staircase approximation from below. A coarse grid produces blocky authorization. A refined grid samples the same latent function more sharply. The latent function itself is the meet of world-level authorizations over the evidence fiber.

**Figure 2. Densification signatures.** Turbo-coded communication is the smooth negative control: breakpoints grow with permission-grid and SNR resolution. Ising belief propagation shows a genuine structural step: one breakpoint remains pinned to \(TV_{\max}=0.3338\). FAA CAT I geometry shows an evidence-axis transition: the smooth RVR floor saturates near 102.4 ft, after which the supplied visual evidence axis no longer constrains authorization.

**Figure 3. Evidence hiding produces conservative permission descent.** ILS occlusion descends ALR → REV → DIA → REF as authorization, visual-reference and signal-integrity gaps are opened. Epic occlusion descends ALR → AEX when G1 opens, then AEX → REV when S2 opens, then REV → DIA when S1 opens.

**Figure 4. Projection fidelity and admissibility.** Epic projection levels L0--L3 preserve permission. L4 merges reason traceability with freshness and weakens authorization from AEX to REV, satisfying admissibility. L5 uses a skeleton-truncating two-gap profile and spuriously restores AEX, violating the admissibility condition.

**Figure 5. Two-axis convergence under fixed and declared maps.** The canonical resolving path covers 16 cases under one requirement map, exercises DIA through ALR, and recovers \(A(e)\) with 400/400 sound cells, 400/400 evidence-axis monotonicity checks, 400/400 permission-axis monotonicity checks and 16/16 final convergence. Declared targeted controls add a synthetic REF floor and four active-refinement witnesses; the combined resolving stress test has 525/525 sound cells and 21/21 final convergence.

**Figure 6. Non-resolving localization and active-refinement controls.** Active-refinement witnesses shift permission exactly at their target splits and remain inert elsewhere. Skeleton-truncating projections produce unsoundness only in the structurally eligible over-authorized cases and monotonicity failures only at restoration transitions. Path-shape stress tests show that start, middle and double truncations reconverge once they enter a resolving tail, while terminal truncation without a resolving tail leaves H02 and S-REV divergent.

**Figure 7. External standards as correspondence audits.** FAA CAT I is an independent-route same-axis policy-margin correspondence: frozen geometry gives 1,862 ft at DH = 200 ft versus the 1,800 ft standard. ECOA reason traceability is exact recovery in the supplied adverse-action representation. 3GPP is representation-relative. FDA AI/ML gaps are shared-corpus same-axis correspondence. FAA CAT II/III are different-axis or outside-package cases. Amazon recruiting is a hierarchy-placement failure.

---

# References

1. Berrou, C., Glavieux, A. & Thitimajshima, P. Near Shannon limit error-correcting coding and decoding: Turbo-codes. *Proceedings of IEEE International Conference on Communications* (1993).
2. 3GPP. TS 38.214. *NR; Physical layer procedures for data*.
3. U.S. Food and Drug Administration. *Artificial Intelligence/Machine Learning (AI/ML)-Based Software as a Medical Device (SaMD) Action Plan* (2021).
4. Consumer Financial Protection Bureau. *Equal Credit Opportunity Act (Regulation B), 12 CFR Part 1002*, including §1002.9, Notifications.
5. Federal Aviation Administration. *Aeronautical Information Manual*, Chapter 5, Section 4, Arrival Procedures.
6. Federal Aviation Administration. *Runway Visual Range (RVR)*, navigation services description of CAT I/II/III minima.
7. Wong, A., Otles, E., Donnelly, J. P. et al. External validation of a widely implemented proprietary sepsis prediction model in hospitalized patients. *JAMA Internal Medicine* (2021).
8. Obermeyer, Z., Powers, B., Vogeli, C. & Mullainathan, S. Dissecting racial bias in an algorithm used to manage the health of populations. *Science* (2019).
9. Lum, K. & Isaac, W. To predict and serve? *Significance* (2016).
10. Angwin, J., Larson, J., Mattu, S. & Kirchner, L. Machine bias. *ProPublica* (2016).
11. Dastin, J. Amazon scraps secret AI recruiting tool that showed bias against women. *Reuters* (2018).
12. Additional IBM Watson oncology, PredPol, COMPAS, Epic, Optum and Amazon source documents are listed in the full audit trail at `docs/provenance.md`.
13. Wald, A. *Statistical Decision Functions*. Wiley (1950).
14. Rahimian, H. & Mehrotra, S. Distributionally robust optimization: a review. *arXiv:1908.05659* (2019).
15. Murphy, A. H. On expected-utility measures in cost-loss ratio decision situations. *Journal of Applied Meteorology* (1969).
