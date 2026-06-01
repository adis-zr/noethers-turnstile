# Blind recovery of regulatory boundaries in approximate systems

**Aditya Sriram** Independent Researcher adi.sriram.math@gmail.com

---

## Abstract

Every consequential system that acts on incomplete information faces the same unresolved question: what does the available evidence actually license? Not what it suggests or what a reasonable person might infer, but what action it can soundly authorize — the strongest permission the evidence warrants and no more. Despite the centrality of this question to medicine, engineering, law, and algorithmic governance, no formal account of it has existed. Evidence has been translated into authorization by convention, intuition, and institutional practice, without a mathematical account of where that translation is sound and where it fails.

We show that the boundary between sound and unsound authorization is not arbitrary. It is geometric: determined by the relationship between how evidence is summarized and what the downstream action requires, and domain-invariant across systems with no shared subject matter. We introduce a formal calculus that reads this geometry directly from the evidence and returns the strongest permission it supports. Running this calculus blind — without consulting any standard or regulation — against four regulatory traditions spanning telecommunications, aviation, medical AI, and consumer credit, we recover the evidence-grounded subset of regulatory boundaries and distinguish them from policy margins, different-axis requirements, and obligations the available evidence cannot reach. In telecommunications, three of five 3GPP 5G Radio Link Monitoring thresholds correspond exactly to the compiler's natural boundaries. In aviation, the FAA's CAT I instrument landing minimum is derived from approach lighting geometry alone, exact on both decision height and runway visual range simultaneously. In medical AI, five of six FDA 2025 AI guidance requirements are recovered from deployment failure evidence without reading the guidance; the compiler's natural tolerance interval, fixed before any external validation existed, brackets a performance degradation observed by an independent research team four years after deployment. In consumer credit, the ECOA adverse action reason requirement — as clarified by CFPB Circular 2022-03 — is recovered from a single adverse-action evidence package without consulting the statute, revealing a seventh gap type structurally distinct from all six preceding ones: evidence sufficient to decide is not always evidence sufficient to justify the decision.

These results suggest that the evidence-grounded component of regulatory requirements — the part that physics and failure patterns force, independent of institutional choice — has a domain-invariant geometric character that has been encoded in regulatory practice for decades without being formally identified. The calculus makes it visible, measurable, and separable from the policy judgments that operate above it.

---

## 1. The Phenomenon

Every consequential decision is made on incomplete information. The physician does not know with certainty what the patient has. The engineer does not know with certainty whether the channel is clear. The algorithm does not know with certainty what will happen if it acts. This is not a failure of effort or technology. It is the permanent condition of decision-making in the real world. The ideal output — the exact diagnosis, the perfect posterior, the complete picture — is unavailable at the moment the decision must be made.

What takes its place is an approximation. A test result, a model score, a decoded signal, a retrieved document. The approximation is used not just to inform the decision but to authorize it: to license an action that would not otherwise be taken. This translation — from approximation to authorization — is so routine that it has become invisible. We do not notice it happening because it happens everywhere, in every consequential system, every time a decision is made.

The question that has not been formally answered is: what does an approximation actually license?

Not what it suggests, not what it is correlated with, not what a reasonable person might infer from it. What it licenses — the strongest action it can soundly authorize, given what it contains and what it cannot contain.

This paper shows that the answer is not arbitrary. It is geometric. The boundary between what an approximation licenses and what it does not has a mathematical structure that is determined by the relationship between the evidence representation and the downstream action. That structure is domain-invariant: the same geometric object appears in the physics of digital communications, in the statistics of probabilistic inference, and in the societal consequences of algorithmic decision-making. It is recoverable by a formal calculus that reads the evidence directly — without consulting the standards, regulations, or guidelines that govern each domain.

And when that calculus is run blind against existing regulatory frameworks in four independent traditions, it finds the same boundaries the frameworks were built around.

### 1.1 The problem is not new. The formal account is.

Incomplete information is not a modern phenomenon. Physicians have always diagnosed without certainty. Engineers have always built systems that must operate in noisy environments. Judges have always decided cases on the balance of probabilities, not proof beyond all doubt. The institutions that govern these activities — medicine, engineering, law — have developed, over centuries, practical frameworks for translating incomplete information into authorized action.

What is new is scale and automation. A sepsis prediction model deployed across a hospital network translates an approximation into an authorization decision for hundreds of patients simultaneously, invisibly, faster than any human reviewer can track. A turbo decoder in a 5G base station translates an approximation into a transmission decision millions of times per second. An agentic software pipeline translates a retrieved document into an authorized action — writing code, submitting a pull request, sending an email — without any human check on whether the evidence behind the action was adequate for the action it licensed.

The volume and speed of these translations have outpaced the informal frameworks that governed them when they were slow and human. When a physician decides to order a test based on incomplete evidence, the reasoning is visible, the scope is limited, and the physician bears professional accountability for the translation. When an algorithm makes the same translation at scale, the reasoning is opaque, the scope is unbounded, and no formal account exists of what the evidence actually licensed.

This is the gap the paper addresses. Not the existence of approximation — that is permanent and irreducible — but the absence of a formal account of what approximation licenses. We have built a world of approximate consequential systems without ever asking, in precise terms, what each approximation is authorized to do.

### 1.2 The core observation

The translation from evidence to authorization fails in a characteristic way. A summary statistic that accurately describes what the evidence contains is used as if it certifies what the evidence does not contain.

A model's AUC of 0.76 accurately describes its ranking performance across all possible thresholds. It says nothing about whether the specific alert threshold that was deployed produces clinically acceptable sensitivity and positive predictive value. A mean bit error rate of $3 \times 10^{-4}$ accurately describes the average decoding quality across bits. It says nothing about whether any specific block was correctly decoded. A recidivism score calibrated to population statistics accurately describes the statistical behavior of a group. It says nothing about whether a specific individual will reoffend. A black-box credit model with validated individual-level predictive performance accurately ranks applicants by default risk. It says nothing about whether the scoring process can produce the specific, accurate, traceable reason that adverse action legally requires.

In each case, the summary statistic answers one question. The authorization requires an answer to a different question. And the last case introduces a further dimension: the evidence may license the decision while being structurally incapable of supporting the reason the decision requires. Evidence sufficient to decide is not always evidence sufficient to justify the decision. And because the two questions share a surface — they are both about the quality of the approximation — the surface similarity obscures the structural gap.

The gap is not a matter of choosing better summary statistics. It is a matter of choosing summary statistics adequate to the action being authorized. The evidence that is sufficient for displaying a result to a clinician may not be sufficient for triggering an automatic order set. The evidence that is sufficient for flagging a document for review may not be sufficient for grounding a legal summary. The evidence that is sufficient for monitoring a sensor may not be sufficient for issuing an automated sanction.

What distinguishes these cases is not the quality of the approximation in the abstract. It is the relationship between the approximation and the specific action it is being asked to authorize. That relationship has a formal character — a geometry — that determines where the boundary of sound authorization lies.

### 1.3 The compiler

We formalize this geometry through a calculus that takes an evidence package and a permission hierarchy as inputs and returns the strongest action the evidence soundly licenses. We call the mechanism that performs this translation a compiler, because it compiles evidence into authorization — and like a compiler, it is sound when it never licenses more than the evidence warrants, and sharp when it licenses exactly what the evidence warrants and no less.

The permission hierarchy is a total ordering of possible actions from weakest to strongest: display a result, flag for review, alert a clinician, trigger an order set, issue an automated sanction. The compiler scans from strongest to weakest, checking at each level whether the evidence is adequate for that action. It stops at the first level the evidence supports and returns that permission.

The compiler's key property follows from a representational fact: it can find the correct boundary if and only if every relevant failure mode is detectable in the evidence representation. If a failure mode is invisible to the evidence — if the evidence cannot distinguish states where the failure has occurred from states where it has not — the compiler cannot find the boundary for that failure mode. No amount of computational sophistication changes this. The boundary is determined by what the evidence contains, not by how cleverly the evidence is processed.

This property has a corollary that drives the main results. The natural, standard summary statistics for approximation quality — mean error, AUC, aggregate accuracy — are mean-like functionals. They average over components. The failure modes that matter for authorization — any variable materially wrong, any bit incorrectly decoded, any individual incorrectly scored — are worst-case properties. They ask about individual components. These two questions have structurally different answers whenever the approximation is uneven across components, which is the generic case.

The gap between them — the region where the mean-like functional authorizes and the worst-case functional refuses — is the mathematical object at the center of this paper.

### 1.4 What the paper shows

We run the compiler in two registers.

In the first register, the evidence is mathematical and the ground truth is available. We study three physically unrelated derived systems — approximate inference in graphical models, turbo-coded digital communications, and ILS instrument approach operations — where exact ground truth can be computed or measured. We show that the authorization gap is non-empty at every operating point tested in the first two systems, and produces concrete failures: a variable whose approximate posterior assigns 83% confidence to the wrong state, a decoded block where every bit fails as the mean bit error rate clears the voice communication standard. We derive the FAA's CAT I decision height and runway visual range minimum from approach lighting geometry alone, recovering both on both dimensions simultaneously before opening any FAA document. We then run the compiler blind against two engineering regulatory frameworks — 3GPP and FAA — and find exact correspondence at the thresholds where the evidence geometry forces boundaries, measurable policy offsets where application-layer demands add margin on the same axis, and a new finding at CAT II where the evidence axis changes character entirely.

In the second register, the evidence is socio-technical and the ground truth is contested. We study seven documented deployments — sepsis prediction, health risk scoring, predictive policing, recidivism scoring, oncology recommendations, automated welfare administration, and credit adverse action — where the authorization failure produced documented harm or legal violation. Starting from a minimal evidence taxonomy, we induce the full gap structure from the failures alone, without consulting any regulatory document. We then run the compiler blind against the 2025 FDA AI guidance and the ECOA/CFPB regulatory framework and find the same structure: exact correspondence at the boundaries the evidence forces, policy offsets at the boundaries institutional judgment must supply, and one finding where the compiler recovers a requirement more precise than the current regulation articulates.

The unified result, displayed in a single matrix in Section 4, shows that these four sets of boundaries — from telecommunications engineering, aviation certification, medical AI regulation, and consumer credit law — partition into thresholds the evidence forces, thresholds that policy adds on the same axis, thresholds grounded in different physical constraints on different axes, and thresholds that arise from outside the evidence entirely. The compiler finds the first set in all four traditions without reading the second, third, or fourth.

This is not a result about compliance or enforcement. It is a result about the structure of sound authorization under incomplete information. The boundaries that regulatory bodies have been building toward, in different fields and different centuries, are not arbitrary. They are tracking a geometry that was always present in the evidence. The compiler makes that geometry visible.

### 1.5 Structure of this paper

Section 2 establishes the physical layer: the authorization gap in approximate inference and digital communications, the FAA ILS geometric derivation and blind audit, the 3GPP blind audit, and what the three registers together establish. Section 3 establishes the socio-technical layer: the induction of the seven-gap taxonomy from documented harmful deployments across healthcare, criminal justice, hiring, public administration, and consumer finance; the depth analysis of the Epic sepsis model with a predictive numerical finding; and the FDA and ECOA/CFPB blind audits. Section 4 presents the unified regulatory correspondence matrix across four regulatory traditions and states the structural symmetry as a general proposition. Section 5 gives the precise scope and limits of the results.

The formal machinery — the compiler specification, the proofs of soundness and sharpness, the implementation and benchmark suite — is in the Methods and Supplementary Material. The main text assumes no prior knowledge of formal methods or programming language theory. The results stand on the experiments.

---

## 2. The Physical Layer: Evidence Geometry in Derived Systems

A system's authorization boundaries are derived when the evidence alone determines them — when there is no room for institutional preference, risk tolerance, or policy selection. Two compilers given the same evidence and the same permission hierarchy must agree on every boundary. The derived case is where we can establish the geometry most cleanly, because the ground truth is available and the mathematics is exact.

We study three physically unrelated derived systems: approximate probabilistic inference, turbo-coded digital communications, and ILS instrument approach operations. They share no subject matter, no application domain, no historical connection, and no shared physics. What they share is the structure of the compiler's relationship to their evidence: in each case, the compiler reads what the evidence contains, finds the boundaries the evidence forces, and stops where the evidence runs out.

### 2.1 The gap between what evidence reports and what it licenses

Every approximate system faces a fundamental asymmetry. When a system approximates an ideal output — an exact posterior, a perfectly decoded bitstream — it must summarize that approximation in some way before using it to authorize action. The summary that feels natural is usually an average: mean error across variables, mean error rate across bits. But the action being authorized often depends on a worst-case property: whether any variable is materially wrong, whether any bit in the block is incorrect.

These two questions have different answers whenever the approximation is uneven. And unevenness is not a pathological condition — it is the generic case. A uniform approximation, where every component is equally well-estimated, is the exception that holds only in highly symmetric systems far from critical regimes. In realistic operating conditions, some components are well-approximated and others are not. The mean says the approximation is good. The worst case says one component is badly wrong.

This gap is not a matter of choosing the right threshold. It is a geometric feature of the evidence space: the set of states where the mean functional authorizes action but the worst-case functional refuses. Its width and location are determined by the structure of the approximation, not by any policy choice.

**Proposition 1 (Gap non-emptiness).** For any approximation with unequal component errors, there exists a non-empty interval of tolerance values $\tau$ for which the mean functional licenses a stronger permission than the worst-case functional. The width of this interval grows with the unevenness of the approximation across components.

This follows directly from $d_\text{worst} \geq d_\text{mean}$ with equality only when all components are equally approximated. The gap is the region $[d_\text{mean}, d_\text{worst})$: any tolerance set within this interval authorizes action under the mean functional while the worst-case functional refuses. It is non-empty whenever the inequality is strict — which is to say, almost always.

The practical consequence is severe. A system designer who uses the mean functional as their quality measure — the natural, standard choice — will authorize action across the entire gap region. At the worst-case end of that region, the approximation contains a component that is materially wrong. The authorization was not earned.

### 2.2 Register 1: Approximate inference in graphical models

We instantiate this geometry in loopy belief propagation (LBP), the standard algorithm for approximate inference in graphical models. LBP computes marginal probability distributions over variables by passing messages along a graph. For loopy graphs — graphs with cycles — these marginals are approximate. The downstream action depends on their quality.

We study the 2D ferromagnetic Ising model, the canonical benchmark for approximate inference, on a $6 \times 6$ grid of binary variables with nearest-neighbor couplings. The coupling strength $\beta$ controls the difficulty of the inference problem: at low $\beta$, variables are nearly independent and LBP is accurate; as $\beta$ increases, long-range correlations develop and LBP degrades. At $\beta_c = 0.44$ — the exact critical temperature from Onsager's 1944 solution [CITE: Onsager1944] — the system undergoes a phase transition and LBP is known to produce its least reliable output [CITE: Murphy1999, Yedidia2005].

We compute exact ground truth by variable elimination and measure two divergence functionals against it:

$$d_\text{mean}(\omega) = \frac{1}{n} \sum_i \frac{1}{2} \sum_s |q_i(s) - p^*_i(s)|$$

$$d_\text{worst}(\omega) = \max_i \frac{1}{2} \sum_s |q_i(s) - p^*_i(s)|$$

where $q_i$ is the LBP marginal and $p^*_i$ is the exact marginal for variable $i$. The mean functional $d_\text{mean}$ reports the average total variation distance across all variables. The worst-case functional $d_\text{worst}$ reports the largest total variation distance for any single variable. Both are natural measures of approximation quality. They answer different questions.

**Table 1.** Authorization gap across coupling strengths ($6 \times 6$ Ising grid, loopy BP). The gap interval is the set of tolerance values where $d_\text{mean}$ licenses action but $d_\text{worst}$ refuses. The gap is non-empty at every coupling strength tested and jumps discontinuously at the critical temperature.

|$\beta$|$d_\text{mean}$|$d_\text{worst}$|Gap interval|Gap width|
|---|---|---|---|---|
|0.10|0.0063|0.0154|[0.006, 0.015]|0.009|
|0.20|0.0130|0.0332|[0.013, 0.033]|0.020|
|0.30|0.0246|0.0529|[0.025, 0.053]|0.028|
|0.40|0.1156|0.1979|[0.116, 0.198]|0.082|
|**0.44** ($\beta_c$)|**0.2231**|**0.3338**|**[0.223, 0.334]**|**0.111**|
|0.50|0.3228|0.4393|[0.323, 0.439]|0.117|
|0.60|0.3926|0.5021|[0.393, 0.502]|0.110|
|1.00|0.4415|0.5791|[0.442, 0.579]|0.137|
|1.50|0.4468|0.5937|[0.447, 0.594]|0.147|

The gap is non-empty at every coupling strength. It grows monotonically and jumps at $\beta_c$. No choice of tolerance value avoids it: any practitioner who sets a threshold anywhere in the gap region is authorizing action on the basis of the mean functional while the worst-case functional refuses — and there is no threshold setting that eliminates this region, only ones that sit outside it.

The worst-case single-variable result at $\beta_c$ makes the stakes concrete. Variable 21 of the $6 \times 6$ grid:

- LBP marginal: $P(s = 1) = 0.833$
- Exact marginal: $P(s = 0) = 0.501$

LBP assigns 83% confidence to the wrong state. The exact posterior barely favors the opposite. This is not numerical imprecision — it is a MAP reversal, a complete inversion of the most probable outcome. At tolerance $\tau = 0.30$, $d_\text{mean} = 0.223 \leq \tau$: a system using the mean functional authorizes action. $d_\text{worst} = 0.334 > \tau$: the worst-case functional refuses. A decision taken on LBP's output acts on a probability 83% confident in the wrong answer.

This is not a constructed pathology. $\beta_c = 0.44$ is the textbook operating point where LBP is least reliable. The failure was visible in the evidence. The functional that would have detected it was available. The authorization was issued because the wrong summary statistic was used.

The gap is the geometric object that separates correct authorization from this failure. It exists in the structure of the approximation before any policy is written.

### 2.3 Register 2: Turbo codes and the identical structure

Turbo codes, introduced by Berrou, Glavieux, and Thitimajshima in 1993 [CITE: Berrou1993], achieve near-Shannon-limit performance in digital communications by running an iterative decoding algorithm that McEliece, MacKay, and Cheng later showed is mathematically equivalent to loopy belief propagation on a chain-structured graphical model [CITE: McEliece1998]. The connection is not approximate or analogical — it is exact. Turbo decoding is belief propagation. The decoder produces an approximate posterior over transmitted bits, and the downstream action — transmitting the block or requesting retransmission — depends on the quality of that approximation.

Two divergence functionals arise naturally from the communications setting:

$$d_\text{BER} = \frac{\text{incorrectly decoded bits}}{\text{total bits}} \qquad d_\text{BLER} = \mathbf{1}[\text{any bit in block incorrect}]$$

The bit error rate $d_\text{BER}$ averages over bits. The block error rate $d_\text{BLER}$ fires if any single bit is wrong. The structural relationship between them is given exactly by:

$$d_\text{BLER} = 1 - (1 - d_\text{BER})^k$$

where $k$ is the block size. For $k = 65{,}536$ bits (the Berrou et al. experimental setup), this amplification is extreme: at SNR $= 2$ dB, $d_\text{BER} = 3 \times 10^{-4}$ while $d_\text{BLER} = 1.0$. Every block fails even as the average bit error rate has cleared the voice communication standard of $10^{-3}$.

The structural correspondence with Register 1 is exact:

||Register 1: Inference|Register 2: Communications|
|---|---|---|
|Mean-like functional|$d_\text{mean}$: average over variables|$d_\text{BER}$: average over bits|
|Worst-case functional|$d_\text{worst}$: single worst variable|$d_\text{BLER}$: any bit fails = block fails|
|Gap law|$d_\text{worst} \geq d_\text{mean}$ by construction|$d_\text{BLER} = 1-(1-d_\text{BER})^k$|
|Peak amplification|$d_\text{worst}/d_\text{mean} \gg 1$ near $\beta_c$|$d_\text{BLER}/d_\text{BER} > 3{,}000$ at SNR $= 2$ dB|

The compiler does not know which domain it is operating in. It receives a divergence functional and emits an authorization judgment. The gap structure it finds — the region where the mean-like functional authorizes and the worst-case functional refuses — is the same mathematical object in both registers. Its existence is not a property of inference or communications. It is a property of the relationship between averaging over components and requiring correctness of each component.

**Table 2.** Authorization gap across SNR values (turbo codes, rate-1/2, block size $k = 65{,}536$). BER values from Berrou et al. [CITE: Berrou1993]; BLER estimated via the independence bound.

|SNR (dB)|$d_\text{BER}$|$d_\text{BLER}$|Auth. ($d_\text{BER}$)|Auth. ($d_\text{BLER}$)|Gap?|
|---|---|---|---|---|---|
|$-1.0$ to $1.5$|$\geq 2 \times 10^{-3}$|$1.0000$|REFUSE|REFUSE|—|
|**2.0**|$3 \times 10^{-4}$|$1.0000$|TRANSMIT_MONITORED|REFUSE|←|
|**2.5**|$2 \times 10^{-5}$|$0.7304$|TRANSMIT_MONITORED|REFUSE|←|
|3.0|$5 \times 10^{-7}$|$0.0322$|TRANSMIT|TRANSMIT_MONITORED|—|
|$3.5+$|$\leq 10^{-8}$|$\leq 7 \times 10^{-4}$|TRANSMIT|TRANSMIT|closed|

The gap spans 1 dB of SNR. In this interval, $d_\text{BER}$ has cleared the voice communication standard while $d_\text{BLER} = 1.0$ — every block fails. A system authorizing transmission on $d_\text{BER}$ alone transmits; a system using $d_\text{BLER}$ refuses. The same geometric object that produces MAP reversals in Ising grids produces complete block failures in digital communications.

### 2.4 The 3GPP blind audit

The 3GPP standards body has specified, over three decades of engineering work, a permission hierarchy for 5G New Radio transmissions. The hierarchy assigns exact block error rate thresholds to service classes: enhanced mobile broadband, ultra-reliable low-latency communications for industrial control, factory automation, and grid fault switching [CITE: 3GPP_TS38133, 3GPP_TR38913, 3GPP_Rel16_URLLC]. These thresholds were determined by committees of engineers working from system requirements, field measurements, and application-layer specifications.

We ask what the compiler finds when it does not know this standard exists.

**Protocol.** Before consulting any 3GPP document, we run the compiler over both $d_\text{BER}$ and $d_\text{BLER}$ across the full SNR range from $-1$ to $5$ dB at 0.1 dB resolution, using BER values digitized from the original Berrou et al. curves and BLER estimated via the independence bound. We specify a five-level permission chain defined by operational meaning only — no threshold values, no service class names, no BLER targets. We extract the compiler's natural permission boundaries from the ridge structure of the permission surface: the SNR values at which a small change in channel quality produces the largest change in what can be authorized. We record these boundaries. Then we open the 3GPP specifications and compare.

**Natural boundaries extracted blind** (from $d_\text{BLER}$ crossings, before any 3GPP document consulted):

|Permission boundary|$\tau$ (BLER)|SNR crossing|
|---|---|---|
|TRANSMIT_CRITICAL|$10^{-3}$|3.49 dB|
|TRANSMIT_DATA|$0.02$|3.19 dB|
|TRANSMIT_MONITORED|$0.10$|2.95 dB|
|HOLD|$0.50$|2.66 dB|

**Table 3.** 3GPP blind audit result. Compiler boundaries versus 3GPP thresholds. EXACT: compiler boundary matches standard threshold exactly. OFFSET: standard threshold sits above compiler boundary by a measurable margin; the margin is the policy distance.

|3GPP threshold|Standard|Ref. BLER|Ref. SNR|Compiler BLER|Compiler SNR|Classification|
|---|---|---|---|---|---|---|
|eMBB CSI target|3GPP Rel. 15|$10^{-1}$|2.95 dB|$0.10$|2.95 dB|**EXACT**|
|RLM $Q_\text{out}$|3GPP TS 38.133|$10^{-1}$|2.95 dB|$0.10$|2.95 dB|**EXACT**|
|RLM $Q_\text{in}$|3GPP TS 38.133|$2 \times 10^{-2}$|3.19 dB|$0.02$|3.19 dB|**EXACT**|
|URLLC Rel. 15|3GPP TR 38.913|$10^{-5}$|4.00 dB|$10^{-3}$|3.49 dB|**OFFSET** (+0.51 dB)|
|Factory Rel. 16|3GPP Rel. 16|$10^{-6}$|4.85 dB|$10^{-3}$|3.49 dB|**OFFSET** (+1.36 dB)|
|B5G evolution|Post-Rel. 17|$10^{-9}$|—|—|—|**COMPILER_PERMISSIVE**|

Three of five observable thresholds correspond exactly to the compiler's natural boundaries — to the SNR values where the gap geometry is widest and the functional choice matters most. The compiler found BLER $= 0.10$ and BLER $= 0.02$ as natural permission boundaries without knowing those values appear in 3GPP TS 38.133. They are not arbitrary choices. They are the points where the authorization surface has the sharpest geometry.

The two URLLC thresholds tell a different story. They sit 0.51 and 1.36 dB above the compiler's highest natural boundary. The compiler is more permissive than the standard in this regime. This is the expected result once the source of each type of threshold is understood: the EXACT thresholds are forced by the physics of the channel — by the geometry of the BER/BLER relationship — and the compiler finds them because it reads that geometry directly. The OFFSET thresholds encode application-layer demands: remote process control and factory motion control require $10^{-5}$ and $10^{-6}$ reliability because the consequences of block failure in those applications exceed what the channel model can express. The compiler has no vocabulary for "a failed block here costs a robot arm."

The 0.51 to 1.36 dB interval is not an error in the standard or a limitation of the compiler. It is the measurable distance between what the physics determines and what deliberate policy adds. It is the formal signature of human judgment operating above the evidence — and the compiler identifies it precisely because it reaches its ceiling at the evidence boundary and stops there.

_Sensitivity analysis._ The independence bound is known to overstate BLER due to burst error correlations in turbo-decoded blocks [CITE: Benedetto1996]. We assess robustness by applying a uniform downward correction $\delta$ to all BLER values and re-extracting the compiler's natural boundaries. At $\delta = 0.30$ — twice the conservative estimate — the $Q_\text{out}$ crossing shifts by 0.03 dB and the $Q_\text{in}$ crossing by 0.14 dB. Both remain well within the 0.5 dB correspondence band. At $\delta = 0.50$, a physically implausible 50% overstatement, the shifts are 0.07 dB and 0.20 dB. The EXACT findings are robust. The OFFSET findings are robust by construction: if actual BLER is lower than the bound, the compiler is even more permissive than reported, widening the policy margin rather than closing it.

### 2.5 Register 3: ILS approach authorization and the FAA category system

The third physical register has no connection to the first two. Loopy belief propagation and turbo decoding share deep mathematical structure — turbo decoding is literally belief propagation on a chain-structured graphical model. A skeptical reader could object that the gap structure found in both is the same algorithm recognized twice. The ILS approach system resolves that objection. Its evidence space is optical and radio-geometric: runway visual range, glide slope signal integrity, approach lighting geometry. It has no relationship to message passing, graphical models, or error-correcting codes. The compiler receives a different kind of evidence and runs a different kind of scan.

The FAA has specified, over seven decades of aviation practice, a category system for instrument approach and landing operations: CAT I, CAT II, CAT IIIa, CAT IIIb, and CAT IIIc. Each category specifies a decision height and a runway visual range minimum. These thresholds were established through a combination of human factors research, equipment certification programs, and operational experience spanning the 1940s through the present. We ask what the compiler finds when it does not know this system exists.

**Physical floor derivation.** Before consulting any FAA document, we derive the minimum RVR required for unaided manual landing from approach lighting geometry alone. On a standard 3° ILS glideslope with threshold crossing height 50 ft AGL, an aircraft at decision height $H$ is at horizontal distance $(H - 50)/\tan(3°)$ before the threshold. The ALSF-2 approach lighting system places its roll bar — the minimum adequate visual reference for runway environment acquisition — 1,000 ft before the threshold. The horizontal distance from the aircraft to the roll bar at decision height $H$ is:

$$\text{RVR}_\text{floor}(H) = \frac{H - 50}{\tan(3°)} - 1{,}000 \text{ ft}$$

This constraint saturates at $H_\text{sat} = 50 + 1{,}000 \times \tan(3°) = 102.4$ ft: below this decision height, the aircraft has already passed the roll bar before reaching decision height. The roll bar visibility constraint no longer applies.

We record all derived values before opening any FAA document:

|Quantity|Derived value|
|---|---|
|RVR floor at DH = 200 ft|1,862 ft|
|DH at which RVR floor = 1,800 ft|196.7 ft|
|Saturation DH|102.4 ft|
|RVR floor at DH = 100 ft|−46 ft (saturated)|
|Time to touchdown from DH = 200 ft|13.0 sec|
|Time to touchdown from DH = 100 ft|4.3 sec|

**Protocol.** We specify a five-level permission chain by operational meaning only — CONTINUE_APPROACH, DESCEND_TO_DH, LAND_MANUAL, LAND_ASSISTED, LAND_ZERO_ZERO — with no FAA category names and no threshold values. Three failure bits are defined from the aircraft-side evidence: $f_1$ (ILS signal integrity failure), $f_2$ (RVR below the geometric floor derived above), and $f_3$ (sub-CAT-I authorization absent). We run two sweeps across the full RVR range from 2,400 ft to 0 ft at 100-ft resolution before opening any FAA document.

**Sweep A** ($f_3$ absent, $f_1$ clear): the compiler transitions from LAND_MANUAL to DESCEND_TO_DH at RVR = 1,800 ft — exactly the geometric derivation rounded to sweep resolution. LAND_ASSISTED and LAND_ZERO_ZERO are unreachable throughout: $f_3$ is absent.

**Sweep B** ($f_3$ present, $f_1$ clear): the compiler emits LAND_ASSISTED at every RVR value from 2,400 ft down to zero. No transitions appear. The RVR axis is completely flat in the sub-CAT-I regime. The compiler finds no natural sub-boundaries in the authorization space that $f_3$ unlocks — because that space does not live on the RVR evidence axis.

**Table 4.** FAA ILS blind audit result. Classification introduced here: OFFSET_DIFFERENT_AXIS — a regulatory boundary that exists and is physically grounded, but on an evidence axis the compiler's package does not contain.

|FAA category|FAA RVR|FAA DH|Compiler RVR|Compiler DH|Classification|
|---|---|---|---|---|---|
|CAT I|1,800 ft|200 ft|1,800 ft|196.7 ft|**EXACT**|
|CAT II|1,200 ft|100 ft|—|—|**OFFSET_DIFFERENT_AXIS**|
|CAT IIIa|700 ft|≤ 100 ft|—|—|**COMPILER_PERMISSIVE**|
|CAT IIIb|150–700 ft|< 50 ft|—|—|**COMPILER_PERMISSIVE**|
|CAT IIIc|no limit|no DH|—|—|**COMPILER_PERMISSIVE**|

The CAT I result is EXACT on both dimensions simultaneously. The geometric derivation gives DH = 196.7 ft and RVR = 1,862 ft — 3.3 ft and 62 ft from the FAA's values respectively, both within the 100-ft sweep resolution. Neither number was taken from a FAA document; both came from the same geometric curve, independently.

The CAT II result requires a new classification. The roll bar visibility constraint saturates at DH = 102.4 ft. The FAA's CAT II decision height is 100 ft — just below the saturation point. The compiler has no RVR floor to enforce at CAT II DH: the aircraft has already passed the roll bar. Yet the FAA requires 1,200 ft of RVR. That requirement is grounded in a real physical constraint — the 8.7-second reduction in time available between CAT I and CAT II decision heights, and the corresponding human factors demands for flare completion at 100 ft AGL — but that constraint lives on an evidence axis the aircraft-side visual package does not contain. This is not a policy margin above the physics on the same axis. The physics on the RVR axis has run out entirely. The FAA's threshold is on a different axis: human factors, not optics.

The roll bar visibility constraint saturates at DH = 102.4 ft. The CAT II decision height of 100 ft sits just below this saturation point. The compiler finds the physical floor, reaches the saturation point, and stops — and the FAA's threshold begins exactly where the physics of the visual evidence runs out.

The CAT IIIa through IIIc results are COMPILER_PERMISSIVE for a structurally different reason than the FDA cybersecurity and labeling results in Section 3. The FDA's COMPILER_PERMISSIVE items were unreachable because no available deployment failure was caused by inadequate labeling. The FAA's CAT III items are unreachable because the authorization space for zero-visibility operations is entirely grounded in autoland certification, fail-operational system requirements, and operator qualification evidence — none of which exists on the RVR evidence axis. This is a structural absence, not a vocabulary gap.

### 2.6 What the physical layer establishes

Four results follow from the three registers together.

**The gap is real and measurable.** In a system with known ground truth, the region where the mean functional authorizes and the worst-case functional refuses is non-empty at every operating point tested, grows with approximation difficulty, and contains states where the approximation is deeply wrong — including complete MAP reversals in inference and complete block failure in communications.

**The gap is domain-invariant across registers with no shared physics.** The same mathematical relationship — $d_\text{worst} \geq d_\text{mean}$, with the gap driven by component-level unevenness — appears in approximate inference and digital communications. The ILS case shows that the same compiler framework applies in a physically unrelated domain with different evidence geometry and different failure modes.

**The geometry was already encoded in existing standards, across two independent regulatory traditions.** Three of five observable 3GPP thresholds correspond exactly to the compiler's natural boundaries. The CAT I ILS threshold corresponds exactly to the compiler's geometric derivation on both dimensions simultaneously. These correspondences come from different physics, different engineering communities, different regulatory bodies, and different decades of development.

**Regulatory frameworks have distinct internal architectures, and the compiler identifies them.** The 3GPP framework is single-axis: EXACT thresholds where the physics forces boundaries, OFFSET thresholds where application-layer policy adds margin on the same axis. The FAA ILS framework is multi-layered: EXACT at CAT I where visual geometry is determinative, OFFSET_DIFFERENT_AXIS at CAT II where a different physical constraint governs, COMPILER_PERMISSIVE at CAT III where the authorization space is entirely orthogonal to visual evidence. The compiler finds these structural differences because it reads what the evidence contains — and its stopping points are as informative as its findings.

These four results establish the physical layer case. The question is whether this geometry appears in systems where the approximation is not over bits, variables, or runway visibility, but over human lives.

---

## 3. The Socio-Technical Layer: Evidence Geometry in Chosen Systems

The physical layer establishes that authorization boundaries have geometric character in systems where the ground truth is mathematically defined. The harder question is whether this geometry survives the translation to human systems — systems where the ideal output is a clinical judgment, a legal determination, or a societal outcome; where ground truth is contested or unavailable; and where the authorization hierarchy is not fixed by physics but chosen by institutions.

These are chosen systems. The permission function is not uniquely determined by the evidence. Institutional risk tolerance, policy, and precedent all shape where the boundaries sit. Two compilers given the same evidence can produce different authorization levels, and both can be defensible. The compiler does not resolve this indeterminacy. What it does is make the structure of the choice visible — and reveal, through the over-authorization loop, which gaps in the evidence the choice is hiding.

We run three experiments. The first is a breadth experiment: seven documented harmful deployments across criminal justice, healthcare, hiring, public administration, and consumer finance, starting from a minimal evidence taxonomy and inducing the full gap structure from the failures alone. The second is a depth experiment: a single deployment, Epic's sepsis prediction model, run with actual numbers against a single empirical witness — and then compared, blind, against FDA regulatory guidance. The third is a regulatory stress test in a new domain: a consumer credit adverse action case, constructed to satisfy all six preceding gaps, which forces a seventh gap from the legal architecture of ECOA.

### 3.1 The over-authorization loop

In a derived system, the gap between mean-like and worst-case functionals is a mathematical object with known geometry. In a chosen system, the analog is the gap between what the evidence package contains and what sound authorization requires. This gap is not defined by a divergence functional — it is induced by cases where the compiler's authorization exceeds what a domain expert would sanction.

The induction procedure is as follows. Begin with a minimal evidence taxonomy: only approximation quality and evidence freshness are tracked. Run the compiler against a set of real deployments with known outcomes. For each case where the compiler over-authorizes — where it emits a stronger permission than a domain expert would grant — ask what positive evidence would have blocked the over-authorization while permitting future legitimate deployments. The answer to that question is a new gap type. Add it to the taxonomy. Repeat until the taxonomy is stable: no available case forces a further gap.

This loop does not consult regulatory documents, domain guidelines, or prior literature. It induces the gap structure from the failure pattern of real systems alone.

### 3.2 MED-IND-001 and CRED-IND-001: Breadth across sectors

We run the induction loop starting from a two-gap taxonomy (approximation quality, freshness) against six documented harmful deployments, deliberately chosen to span different failure modes, sectors, and institutional contexts, followed by a single credit adverse action stress test constructed to probe a structurally distinct failure mode. The positive control — a well-validated clinical decision support tool with low blast radius — emits the correct authorization at every profile version and serves as a stability anchor.

**Table 4.** Induction trace across seven harmful deployments. Each step: compiler over-authorizes, expert disagrees, discrepancy forces exactly one new gap type. Profile version increments at each step.

|Step|System|Compiler|Expert|Gap induced|
|---|---|---|---|---|
|—|Positive control (validated CDS, low blast radius)|ALR|ALR|—|
|1|Epic Sepsis Model — AUC 0.76, operating-point utility never validated|ALR|REV|clinical_utility_gap|
|2|Optum health risk scoring — training target (cost) diverges from action target (care need)|ALR|REV|model_specification_gap|
|3|PredPol predictive policing — self-reinforcing feedback loop between predictions and arrests|ALR|REV|distribution_shift_gap|
|4|COMPAS recidivism — population statistics used to license individual detention decisions|ALR|REV|individual_population_gap|
|5|IBM Watson Oncology — high-stakes treatment recommendations at global scale, no blast radius bound|ALR|AEX|blast_radius_gap|
|6|Dutch childcare algorithm — automated repayment demands of tens of thousands of euros, no human review|ALR|AEX|authority_gap|
|7|Credit adverse action — evidence package contains no validated reason token; adverse action legally requires one|ALR|REV|reason_traceability_gap|

The induction converges in exactly seven steps. Each step forces exactly one gap. The taxonomy is stable at seven gaps: clinical_utility_gap, model_specification_gap, distribution_shift_gap, individual_population_gap, blast_radius_gap, authority_gap, reason_traceability_gap.

Each gap corresponds to a distinct structural failure mode that the pre-induction taxonomy was blind to.

**clinical_utility_gap** is induced by the Epic case. AUC 0.76 is not contested — it survives the induction intact because it accurately describes the model's ranking performance. What AUC cannot detect is that a model with excellent ranking performance can still be a bad alerting system at a specific deployed threshold. AUC integrates over all possible thresholds; it has no opinion about the one that was actually chosen. Sensitivity 0.33 and PPV 0.12 at threshold ≥ 6 are not recoverable from AUC. They require a different question.

**model_specification_gap** is induced by the Optum case. The Obermeyer et al. investigation found that the algorithm used healthcare cost as a proxy for healthcare need, and that Black patients with equal medical need incurred systematically lower costs due to structural barriers to care [CITE: Obermeyer2019]. A model can be well-specified for its stated prediction task — predicting cost — and badly specified for the action it was used to authorize. The gap is between training target adequacy and action target adequacy. No amount of AUC improvement on cost prediction closes it.

**distribution_shift_gap** is induced by PredPol. Standard distribution shift analysis asks whether the deployment population matches the training population. PredPol's failure is different in kind: the model's predictions become part of the training distribution, because increased policing in predicted areas generates more reported crime there. The model is accurate on its self-generated distribution. External validation against an independent distribution — one not produced by the model's own output history — is the only evidence that closes this gap. No internal validation can.

**individual_population_gap** is induced by COMPAS. A recidivism score calibrated to population base rates describes the statistical behavior of groups. It does not certify whether this specific individual will reoffend. The distinction is not a statistical quibble — it is a category error with legal consequence. Using population-level probabilities to restrict an individual's liberty treats group membership as predictive of individual behavior. Improving the model's population-level calibration does not close this gap; it requires a separate certifier for individual-level predictive validity.

**blast_radius_gap** is induced by Watson Oncology. Even with all preceding gaps closed, the scope of downstream harm per recommendation matters. A model authorizing individual clinical suggestions in a supervised setting and the same model authorizing treatment recommendations delivered to clinicians worldwide through a system that made override difficult are not the same action even if the underlying evidence package is identical. The gap requires an explicit bound on the scope of actions the system can trigger per output.

**authority_gap** is induced by the Dutch childcare algorithm, which issued automated debt repayment demands averaging €30,000 against 26,000 families — the largest government scandal in Dutch postwar history — with no meaningful human review, no explanation of the algorithmic basis, and no accessible appeals process [CITE: Dutch2020]. The authority gap requires that the boundary between what a system can do autonomously and what requires human confirmation be explicitly contracted. It is not satisfied by the presence of a human somewhere in the chain; it requires a formal specification of where autonomous action ends.

**reason_traceability_gap** is induced by a credit adverse action case — a constructed regulatory stress test, not a named real-world incident, deliberately designed to satisfy all six preceding gaps. The model is well-specified, approximation quality is bounded, distribution coverage is documented, individual-level predictive validity is certified, blast radius is bounded to individual decisions, and authority is properly contracted with human loan officer review. The compiler emits ALR. The expert says REV.

The forcing observation is structural: a human loan officer cannot issue an adverse action notice that complies with ECOA without a specific, accurate statement of the principal reasons. The evidence package under review contains a risk score but no validated reason token — no auditable mapping from the score to the specific input features that drove this applicant's outcome. The loan officer cannot reconstruct which factors were actually considered, and a score alone does not supply that reconstruction. The evidence supports the decision. It does not support the reason the decision legally requires.

The first six gaps ask whether the evidence supports the action — whether the model is good, the target is right, the population is covered, the individual validity is certified, the scope is bounded, the authority is contracted. Step 7 asks something structurally prior: does the evidence support the reason the action legally requires to be communicated? Evidence sufficient to decide is not always evidence sufficient to justify the decision.

The gap is scoped to action classes that carry a legal obligation to communicate specific reasons to the affected party: denial, sanction, termination, benefit reduction. Notification, flagging, and display actions do not trigger it.

Non-reducibility to individual_population_gap: certifying that a score is accurate for this individual is not the same as certifying that the path from inputs to score can be audited. These are separable properties requiring different tokens.

Non-reducibility to authority_gap: a fully authorized human reviewer cannot comply with ECOA if the evidence package they receive does not contain the required reason token. Authority governs who acts. reason_traceability_gap governs what the evidence must supply before that act is legally permissible.

**Convergence check.** All eight cases (including the positive control) are re-run against the converged seven-gap taxonomy. The compiler emits a permission below ALR on every induction case — all seven gaps remain open in the respective evidence packages. No over-authorization occurs. The positive control continues to emit ALR correctly.

**Generalization.** Five held-out cases not used in the induction — including the Boeing 737 MAX MCAS failures, COVID-19 ML models (Roberts et al.), and the Amazon recruiting algorithm — are evaluated against the converged taxonomy. The compiler agrees with expert assessment on all five, with two results where the compiler is marginally more permissive than the expert (Amazon and Allegheny Family Screening, where the compiler emits AEX(9) against expert REV(8) — both below ALR(10), no over-authorization). Permissive errors above ALR do not occur.

### 3.3 The chosen domain is not arbitrary

Before turning to the depth experiment, one structural observation is necessary.

In a derived system, the permission function has a unique correct form: the mathematics of the domain determines the boundary. In a chosen system, multiple permission functions are consistent with the evidence constraints. The institution must choose among them, and the choice encodes risk tolerance that the evidence cannot determine.

This is not a weakness of the framework. It is an honest description of how chosen systems work. The compiler's contribution in a chosen domain is not to resolve the choice — it cannot — but to make the choice explicit, mechanical, and auditable. A profile that says "adequate validation required" is a policy aspiration. A profile that names clinical_utility_gap, distribution_shift_gap, scope_coverage_gap, and their field contracts is a policy implementation. The difference is the difference between a sentence in a regulation and a certifiable requirement.

What the induction loop establishes is that the gap structure forced by the evidence of real failures is not arbitrary. It corresponds to a taxonomy of structurally distinct failure modes. Each gap type answers a question the preceding taxonomy could not ask. The taxonomy converges — no available failure adds a gap type the existing taxonomy already handles — and the converged taxonomy has a clean partition structure with no redundant entries.

reason_traceability_gap is structurally distinct from all six preceding gaps: it is not about model quality, target alignment, distribution coverage, population-individual transfer, scope of harm, or oversight chain. It fires when the permission hierarchy includes actions that require not only a sound decision but a communicable, legally adequate justification — and the evidence package does not contain the materials for one. The six preceding gaps ask whether the evidence supports the action. This gap asks whether the evidence supports the reason the action legally requires.

### 3.4 MED-002: Depth in a single case

The Epic Sepsis Model is the first induction case — the one that forced clinical_utility_gap. We return to it for a depth experiment. Where MED-IND-001 names the gap and moves on, MED-002 asks: how wide is the over-authorization, and does the compiler's natural tolerance interval — derived from the permission hierarchy alone, before any external validation exists — contain the degradation that external validation later observed?

**Starting evidence.** Penn Medicine internal validation, circa 2017.

|Metric|Value|
|---|---|
|AUROC|0.76|
|Sensitivity at deployed threshold (score ≥ 6/10)|0.54|
|Specificity|0.83|
|PPV at ~4% inpatient base rate|0.12|
|Alert rate|~20% of inpatients flagged|
|Validation sites|Single site (Penn Medicine)|

**The witness.** Wong et al. (2021), external validation at 7 academic hospitals [CITE: Wong2021]. Sensitivity 0.33. AUROC range 0.63–0.76, with Penn Medicine as the ceiling rather than the midpoint. 18% of sepsis patients missed without alert at some sites. The sensitivity drop from the internal figure: 0.21 percentage points, a 39% relative degradation.

The Wong study was published four years after deployment. It was conducted by an independent team at institutions with no connection to the original development. It is not a reanalysis of Penn Medicine data — it is a genuinely external measurement of what the model does when it encounters populations it was not trained on.

**The induction loop on Epic alone.** Starting from the weak two-gap profile, we run the induction in six explicit steps. At each step the compiler over-authorizes relative to the expert; each discrepancy forces one gap.

_Step 1._ The Wong witness supplies sensitivity 0.33 and PPV 0.12 at the deployed threshold. AUC 0.76 survives — Wong does not contest the ranking measure, and the compiler correctly leaves it intact. AUC integrates over all thresholds. It cannot detect that 88% of alerts are false positives or that two-thirds of sepsis cases are missed, because those properties belong to a specific threshold, not to the ranking. A compiler using only AUC cannot detect the failure mode "alert rate is clinically unsustainable." Gap induced: **clinical_utility_gap**.

_Step 2._ Stipulate clinical_utility_gap closed. The distribution shift failure bit fires vacuously: no token in the evidence package bounds performance outside Penn Medicine. The profile requires positive evidence of performance stability across deployment populations; absence of such a token is itself the failure, not a signal of low confidence. This inverts the standard statistical framing. In most reasoning, absence of evidence is not evidence of absence. Here it is: the bit is set until a positive token clears it, and no positive token exists. The compiler refuses without needing to observe degradation. Wong later confirms: AUROC 0.63–0.76 across 7 sites, with Penn Medicine as the ceiling. Gap induced: **distribution_shift_gap**.

_Step 3._ Closing distribution_shift requires a multi-site validation token whose field contract specifies representativeness — site count, population description, temporal coverage, similarity criterion to the deployment context. Without this contract, any multi-site data technically satisfies the gap, including data from sites identical to the training site, which certifies nothing. The Penn Medicine study cannot satisfy this contract by definition: the origin site cannot serve as independent validation of its own distribution. This is a logical impossibility, not an empirical gap that more data could close. Gap induced: **scope_coverage_gap**.

_Steps 4–6._ Closing the preceding gaps does not certify that the operating threshold is clinically appropriate. Gap induced: **operating_point_utility_gap** — sensitivity, specificity, PPV, and NPV at the deployed threshold with confidence intervals, against pre-specified acceptance criteria. Broad rollout requires a monitoring plan before deployment, not after. Gap induced: **post_market_monitoring_gap**. Monitoring without a defined response is incomplete. Gap induced: **rollback_criteria_gap**.

The taxonomy is stable at six gaps. All six remain open in the Penn Medicine evidence package. No available witness forces a further gap.

**The compound authorization surface.** We sweep the PPV floor $\tau_L$ across the full range of clinically defensible values, recording the utility-derived permission, the distribution shift status, and their compound. The compound permission is the meet — the minimum — of the two independent axes.

|PPV floor $\tau_L$|Penn PPV|Utility permission|Dist. shift|Compound|
|---|---|---|---|---|
|0.05|0.12|ALERT_ROLLOUT|OPEN|LIMITED_ROLLOUT|
|0.10|0.12|ALERT_ROLLOUT|OPEN|LIMITED_ROLLOUT|
|0.12|0.12|ALERT_ROLLOUT|OPEN|LIMITED_ROLLOUT|
|0.15–0.30|0.12|LIMITED_ROLLOUT|OPEN|LIMITED_ROLLOUT|

ALERT_ROLLOUT is unreachable at any clinically defensible threshold. The distribution shift gap blocks it independently of where the utility floor is set. The two gap types are orthogonal axes — closing one does not affect the other — and the compound permission is always their meet.

**The predictive finding.** The permission hierarchy implies natural sensitivity floors for each authorization level. A permission that licenses broad rollout across hospitals requires tighter degradation tolerance than one that licenses controlled single-site deployment. We derive the compiler's natural tolerance intervals from the permission hierarchy alone — before opening the Wong paper.

|Authorization level|Sensitivity floor|Max tolerable drop from Penn baseline (0.54)|
|---|---|---|
|ALERT_ROLLOUT|0.50|0.04 pp|
|LIMITED_ROLLOUT|0.30|0.24 pp|

Wong observed: 0.21 pp drop.

- 0.21 pp exceeds ALERT_ROLLOUT tolerance (0.04 pp). The degradation is larger than broad rollout can sustain.
- 0.21 pp falls within LIMITED_ROLLOUT tolerance (0.24 pp). The degradation is consistent with controlled single-site deployment.

The compiler's natural tolerance interval, derived from the permission hierarchy without reading Wong, brackets the observed degradation at exactly the right level. The implied AUROC range from the sensitivity drop (0.741–0.760) falls within the Wong observed range (0.63–0.76).

This is the depth experiment's central result, and it is stronger than the 3GPP correspondence finding in one specific sense. The 3GPP result is retrospective: the compiler's natural boundaries match thresholds that already existed in an established standard. The Epic result is predictive: the compiler's tolerance interval was fixed by the permission hierarchy before external validation existed, and the external validation, conducted four years later by an independent team, produced a degradation figure that landed inside it. The compiler did not fit to Wong. Wong confirmed the compiler.

### 3.5 The FDA blind audit

Having completed the medical induction without consulting any regulatory document, we open the FDA 2025 AI Draft Guidance (Docket FDA-2024-D-4488) and record, for each of the six medically-induced gaps, the corresponding regulatory requirement and its classification. The seventh gap, reason_traceability_gap, was induced from the credit case and is audited separately against ECOA/CFPB below.

**Protocol.** The induction in §3.4 was completed before any FDA document was consulted. The classification below was assigned after the induction, by matching induced gap descriptions to regulatory text, with no retroactive adjustment to gap definitions.

**Table 5.** FDA blind audit result. EXACT: induced gap corresponds to a named FDA requirement. COMPILER_STRICT: compiler induces a requirement more precise than the current regulatory text. COMPILER_PERMISSIVE: FDA requires something the compiler's evidence induction cannot reach.

|Induced gap|FDA element|Section|Classification|
|---|---|---|---|
|distribution_shift_gap|Real-World Performance Monitoring; intended use population specification|§6/§4|**EXACT**|
|scope_coverage_gap|Validation dataset diversity; PCCP site representation requirements|§5/Appendix C|**EXACT**|
|operating_point_utility_gap|Clinical performance metrics at intended operating point|Appendix C|**EXACT**|
|post_market_monitoring_gap|Post-market surveillance plan|§6/PMA|**EXACT**|
|rollback_criteria_gap|Algorithm change protocol; performance degradation response|§7/PCCP|**EXACT**|
|clinical_utility_gap|Clinical utility — partial|Appendix C|**COMPILER_STRICT**|
|—|Software cybersecurity requirements|§8|**COMPILER_PERMISSIVE**|
|—|Labeling / Instructions for Use|§9|**COMPILER_PERMISSIVE**|

5 EXACT · 1 COMPILER_STRICT · 2 COMPILER_PERMISSIVE.

Five of the six medically-induced gaps correspond exactly to named requirements in the current FDA guidance. The two COMPILER_PERMISSIVE items — cybersecurity and labeling — were not reachable from deployment failure evidence. No case in the medical induction set involved a failure attributable to software security vulnerabilities or inadequate labeling. The compiler does not discover what the evidence does not reveal; its silence on these requirements is not a flaw, it is accurate.

The COMPILER_STRICT finding is the most consequential. FDA Appendix C requires operating-point metrics and confidence intervals — sensitivity, specificity, PPV, NPV. The compiler induces something more precise: a PPV floor calibrated to the blast radius of the downstream clinical action. A system flagging 20% of all inpatients with PPV 0.12 and a system flagging 1% of ICU patients with PPV 0.12 report the same metric. They authorize radically different actions. The compiler encodes the relationship between the metric and the scope of harm it licenses; the current regulatory text does not. The compiler recovered a policy structure that is more precise than the regulation it was compared against — without having read it.

### 3.6 The ECOA/CFPB blind audit

The credit adverse action case that forced reason_traceability_gap was constructed as a regulatory stress test: an evidence package satisfying all six preceding gaps, against which the compiler still over-authorizes. Having recorded that result, we open ECOA (15 U.S.C. §1691), Regulation B (12 CFR §1002), and CFPB Circular 2022-03, and classify the induced gap against the regulatory text.

**Protocol.** The credit induction (CRED-IND-001) was completed before any ECOA document was consulted. The classification was assigned after, by matching the gap description to the statutory and regulatory text, with no retroactive adjustment.

**Table 5a.** ECOA/CFPB blind audit result.

|Induced gap|Regulatory element|Citation|Classification|
|---|---|---|---|
|reason_traceability_gap|Specific, accurate statement of principal reasons for adverse action; must accurately describe factors actually considered; model complexity not an excuse|ECOA §1691(d); Reg B §1002.9; CFPB 2022-03|**EXACT**|
|—|Prohibition on disparate impact|12 CFR §1002.6(a)|**COMPILER_PERMISSIVE**|
|—|Data accuracy procedures|15 U.S.C. §1681e(b)|**COMPILER_PERMISSIVE**|

1 EXACT · 2 COMPILER_PERMISSIVE.

The two COMPILER_PERMISSIVE entries are real regulatory obligations not forced by the evidence structure of the credit stress test. A model can produce a bounded, traceable reason for every individual adverse action and still generate systemically discriminatory population-level outcomes. These are orthogonal failure modes on orthogonal evidence axes. The compiler's silence on disparate impact and data accuracy is not a vocabulary gap. It is an accurate reading of what individual-case evidence cannot certify about population-level behavior.

### 3.7 What the socio-technical layer establishes

Four results follow from MED-IND-001, MED-002, CRED-IND-001, and the two blind audits together.

**The gap structure generalizes across sectors.** Starting from a taxonomy containing only approximation quality and freshness, the over-authorization loop induces seven structurally distinct gap types from seven cases spanning criminal justice, healthcare, hiring, public administration, and consumer finance. Each gap type corresponds to a distinct failure mode that the preceding taxonomy was blind to. The taxonomy converges — no available case forces an eighth gap — and generalizes correctly to five held-out cases.

**The geometry is predictive, not just descriptive.** The compiler's natural tolerance intervals for the Epic deployment, derived from the permission hierarchy before external validation existed, bracket the degradation figure observed by an independent research team four years later. The correspondence is not a fit to known data. It is a prediction confirmed.

**The induction recovers regulatory structure without reading the regulation.** Five of six medically-induced gaps correspond exactly to named requirements in the 2025 FDA AI guidance. The reason_traceability_gap, induced from a credit adverse-action stress test, corresponds exactly to ECOA and Regulation B as clarified by CFPB Circular 2022-03 — a second independent regulatory tradition, confirming the same correspondence structure in a wholly separate legal domain. The one COMPILER_STRICT finding identifies a distinction the regulation names only partially. The COMPILER_PERMISSIVE findings identify requirements that deployment failure evidence cannot reach — correctly, because no available failure was attributable to those causes.

**The compiler's coverage is honest about its limits.** It covers exactly what the evidence of harm can force, and is silent where that evidence runs out. In the medical domain this means two FDA requirements are missed. In the credit domain it means disparate impact and data accuracy are missed. These silences are not errors. They are accurate readings of what individual-case evidence cannot certify about population-level behavior or upstream data provenance.

The physical layer showed that authorization boundaries have geometric character in systems governed by physics. The socio-technical layer shows the same geometry operating in systems governed by human institutions — forced by the structure of evidence, recoverable from failure cases alone, and independently convergent with the boundaries that regulators have been trying to articulate in prose for decades.

---

## 4. The Unified Regulatory Correspondence Matrix

Sections 2 and 3 established the same phenomenon in two different registers. In the physical layer: a compiler reading evidence geometry without knowledge of any standard independently recovers the permission boundaries that three decades of 5G standardization work produced — and identifies, by measurement, where those boundaries are forced by physics and where they are forced by policy. In the socio-technical layer: a compiler reading the failure pattern of real harmful deployments without consulting any regulation independently recovers the gap structure that the FDA's 2025 AI guidance and the ECOA/CFPB credit framework try to articulate in prose — and identifies, by a predictive numerical finding, where evidence determines the boundary and where institutional judgment must supply what evidence cannot.

These results span four independent regulatory traditions — telecommunications, aviation, medical AI, and consumer credit — with no shared subject matter, no shared regulatory history, and no shared scientific methodology. The question this section answers is whether that similarity is structural — whether all four results arise from the same underlying geometry — or whether it is coincidental.

The answer is structural. The geometry is the same object in both cases. This section makes that claim explicit, shows it in a unified matrix, and states the consequences.

### 4.1 The three types of boundary

The experiments in Sections 2 and 3 consistently produce three distinct types of regulatory threshold. Two of these appeared in the first two physical registers; the FAA ILS experiment revealed a third.

**Boundaries forced by evidence geometry** are the thresholds where the structure of the approximation itself determines what can be soundly authorized. In the physical layer, these are the SNR values where the gap between $d_\text{BER}$ and $d_\text{BLER}$ is widest, and the ILS decision height and RVR pair where the ALSF-2 roll bar visibility geometry produces its natural floor. The compiler finds these boundaries because it reads the geometry directly. In the socio-technical layer, these are the evidentiary gaps where no amount of existing evidence closes the authorization question — where AUC cannot answer the question about operating-point utility, where single-site validation cannot answer the question about distribution stability across populations.

In all cases the boundary is not chosen. It is discovered. The compiler reaches it from below, finds that the evidence runs out, and stops there.

**Boundaries forced by policy above evidence on the same axis** are the thresholds where institutional judgment adds requirements beyond what the evidence geometry determines, expressed as an additional margin along the same evidence dimension. In the physical layer, these are the URLLC thresholds: the BER/BLER physics establishes a ceiling at 3.49 dB, and the 3GPP standards add 0.51–1.36 dB of reliability margin because application-layer demands for factory automation and remote process control exceed what the channel model can derive. The additional margin is measurable in dB — on the same SNR axis as the EXACT boundaries.

In these cases the boundary is set above the physics. The compiler reaches its evidence ceiling, stops, and the policy requirement sits above it at a measurable distance on the same axis.

**Boundaries forced by policy on a different axis** are the thresholds where the physics of the evidence changes character rather than simply running out. This third type was revealed by the FAA ILS experiment. The roll bar visibility constraint saturates at DH = 102.4 ft: below this decision height, the aircraft has already passed the roll bar, and the visual geometry constraint no longer exists. The FAA's CAT II threshold sits just below this saturation point at DH = 100 ft, with an RVR requirement of 1,200 ft. That requirement is not a policy margin above the visual geometry physics — the visual geometry physics has ended. The 1,200 ft requirement is grounded in a different physical constraint: the human factors demands of completing a manual landing with only 4.3 seconds to touchdown. That constraint lives on a human factors evidence axis the visual package does not contain.

The distinction from the second type is precise. In 3GPP OFFSET, the policy margin is on the same SNR axis as the EXACT boundaries — the physical evidence continues and policy adds margin on top. In FAA OFFSET_DIFFERENT_AXIS, the physical evidence of the first type runs out entirely, and a different physical constraint governs — one the compiler cannot see because it is not in the evidence package.

This three-way taxonomy — EXACT, OFFSET (same axis), OFFSET (different axis) — is itself a finding about regulatory architecture. Different regulatory frameworks encode their authorization requirements along different evidence geometries, and the compiler's stopping behavior identifies which type is operating at each threshold.

### 4.2 The unified matrix

The matrix below places all four regulatory traditions side by side under a shared classification taxonomy. Every entry is derived from the experiments in Sections 2 and 3 with no post-hoc adjustment.

The rows are correspondence types. The columns are regulatory traditions. Within each cell, the specific thresholds and measurements from the experiments are listed. The classification of each entry was determined before opening any standard or regulatory document; the correspondence was observed afterward.

---

**Table 6. Unified Regulatory Correspondence Matrix.** Classification definitions: **EXACT** — compiler boundary matches regulatory threshold, derived without knowledge of that threshold. **OFFSET** — regulatory threshold sits above compiler's evidence ceiling by a measurable margin on the same evidence axis; the margin is policy operating above physics. **OFFSET_DIFFERENT_AXIS** — regulatory threshold exists and is physically grounded, but the physical constraint governing it is on an evidence axis the compiler's package does not contain. **COMPILER_STRICT** — compiler induces a requirement more precise than what the current regulatory text articulates. **COMPILER_PERMISSIVE** — regulatory requirement exists but no available evidence forces it; the compiler correctly reaches no boundary there.

||**Physical / Derived**|**Physical / Derived**|**Socio-Technical / Chosen**|**Socio-Technical / Chosen**|
|---|---|---|---|---|
||_3GPP 5G New Radio (telecommunications)_|_FAA ILS approach (aviation)_|_FDA 2025 AI Guidance (medical AI)_|_ECOA / CFPB (consumer credit)_|
|**EXACT**|eMBB CSI target: BLER $= 0.10$ at 2.95 dB — compiler finds without reading standard.|CAT I: DH = 200 ft, RVR = 1,800 ft — compiler derives DH = 196.7 ft, RVR = 1,862 ft from roll bar geometry. Exact on both dimensions.|distribution_shift_gap → Real-World Performance Monitoring; scope_coverage_gap → validation diversity; operating_point_utility_gap → clinical metrics at operating point; post_market_monitoring_gap → surveillance plan; rollback_criteria_gap → algorithm change protocol. All five induced without reading FDA guidance.|reason_traceability_gap → adverse action statement of specific reasons; model complexity not an excuse (ECOA §1691(d); Reg B §1002.9; CFPB Circular 2022-03). Induced from credit stress test without consulting ECOA.|
||RLM $Q_\text{out}$: BLER $= 0.10$ at 2.95 dB — exact correspondence.||||
||RLM $Q_\text{in}$: BLER $= 0.02$ at 3.19 dB — exact correspondence.||||
|**OFFSET**|URLLC Rel. 15: 3GPP requires BLER $= 10^{-5}$ at 4.00 dB; compiler ceiling at 3.49 dB. **Policy margin: +0.51 dB on same SNR axis.** Application-layer demand for remote process control reliability.|—|ALERT_ROLLOUT blocked by orthogonal constraints: PPV $= 0.12$ fails any defensible utility floor; distribution_shift_gap blocks independently. **Compound: LIMITED_ROLLOUT at best.** _Predictive finding:_ compiler tolerance [0, 0.24 pp]; Wong observed 0.21 pp drop. $0.21 \in [0, 0.24]$.|—|
||Factory Rel. 16: 3GPP requires BLER $= 10^{-6}$ at 4.85 dB; compiler ceiling at 3.49 dB. **Policy margin: +1.36 dB on same SNR axis.** Factory automation and grid fault switching.||||
|**OFFSET_DIFFERENT_AXIS**|—|CAT II: DH = 100 ft, RVR = 1,200 ft. Roll bar constraint **saturated** at DH = 102.4 ft — aircraft passes roll bar before reaching CAT II DH. Visual geometry constraint gone. FAA's 1,200 ft grounded in human factors: 4.3 sec to touchdown vs 13.0 sec at CAT I. **Different physical constraint, orthogonal evidence axis.**|—|—|
|**COMPILER_STRICT**|Sub-threshold gap resolution: compiler identifies full BER/BLER divergence geometry at finer granularity than the committee lines capture.|—|clinical_utility_gap: FDA requires operating-point metrics; compiler induces PPV floor calibrated to blast radius of clinical action. PPV = 12% flagging 20% of inpatients ≠ PPV = 12% flagging 1% of ICU patients. Regulation names the metric; compiler names the relationship between metric and harm scope.|—|
|**COMPILER_PERMISSIVE**|B5G evolution: Post-Rel. 17 BLER $= 10^{-9}$ beyond evidence resolution of local channel state.|CAT IIIa/b/c: RVR 700 ft / 150 ft / no limit. Roll bar constraint saturated; authorization space entirely grounded in autoland certification, fail-operational systems, operator qualification. **Structural absence** — wrong evidence type, not missing threshold.|Software cybersecurity (§8); Labeling / Instructions for Use (§9). No induction case failed from these causes. Compiler does not discover what the evidence does not reveal.|Disparate impact (12 CFR §1002.6(a)); data accuracy (15 U.S.C. §1681e(b)). Individual-case evidence cannot certify population-level discrimination or upstream data provenance. **Orthogonal failure axes** — correct silence.|

---

### 4.3 Reading the matrix

The matrix has a clean partition structure that is worth stating explicitly.

**The EXACT row** is the primary result. Twelve thresholds across four independent regulatory traditions — telecommunications, aviation, medical AI, and consumer credit — correspond exactly to boundaries the compiler found without knowledge of any standard. These thresholds span different countries, different scientific communities, different legal systems, and different centuries of institutional development. Their correspondence with the compiler's natural boundaries is consistent across every measurable threshold in all four traditions where the evidence geometry has sufficient resolution.

The mechanism is the same in all cases. The compiler finds boundaries at the points where the evidence geometry has the sharpest structure — where the gap between the evidence representation and the downstream action is widest. The regulatory bodies, working from empirical measurements and operational requirements, placed their thresholds at the same points. They were tracking the same geometry, in different vocabularies, in different fields, without knowing it.

**The OFFSET row** is the secondary result. The EXACT boundaries are where physics and policy agree. The OFFSET boundaries are where they diverge on the same evidence axis — and the divergence is measurable, interpretable, and consistent. In 3GPP, the policy margin (0.51 to 1.36 dB) encodes application-layer safety demands that exceed what channel physics can certify, expressed as additional SNR margin on the same BER/BLER axis. In the medical domain, the offset takes a compound form: two orthogonal gap types block ALERT_ROLLOUT simultaneously, and the compiler's predictive tolerance interval brackets the external finding without having seen it.

**The OFFSET_DIFFERENT_AXIS row** is the new finding from the FAA experiment. At CAT II, the evidence physics does not merely fall short — it changes character. The roll bar visibility constraint saturates at DH = 102.4 ft, and the CAT II decision height sits just below that point. The compiler correctly finds no boundary there: it has reached the end of the evidence axis it was reading. The FAA's 1,200 ft RVR requirement is grounded in a real physical constraint — human factors at low decision height — but that constraint is on a different axis. This distinguishes CAT II from the 3GPP OFFSET entries: those are policy margin on the same SNR axis; this is a different physical constraint on a different axis entirely. The compiler's silence here is not a gap in its vocabulary. It is an accurate reading of what its evidence contains.

**The COMPILER_STRICT row** is the third finding. In the physical domains, the compiler resolves gap geometry at finer granularity than the committee lines capture. In the medical domain, the compiler induces a requirement — PPV calibrated to blast radius — that is more precise than what the current regulation articulates. In all cases the compiler is not missing something; it is finding something the regulation hasn't fully named yet.

**The COMPILER_PERMISSIVE row** is the honest limit. The B5G thresholds, FAA CAT III requirements, cybersecurity requirements, and labeling requirements are real regulatory obligations the compiler cannot reach. Notably, the FAA CAT III and the FDA cybersecurity entries are COMPILER_PERMISSIVE for different reasons: CAT III is structurally absent (autoland certification and operator qualification are not on any visual evidence axis), while FDA cybersecurity is inductively absent (no available deployment failure was caused by a security vulnerability). Both are correct silences. They mean different things about the regulatory frameworks they come from.

### 4.4 The structural symmetry

The unified matrix establishes a claim that no single domain could support: the geometry of sound authorization boundaries is a domain-invariant property of the relationship between evidence representations and downstream actions, and it is recoverable by a compiler that reads evidence structure directly.

The symmetry has a precise form that admits three cases.

In derived systems with a single dominant evidence axis — the 3GPP case — the compiler finds the thresholds where the evidence geometry forces permission boundaries, and the policy margin above the physical ceiling is measurable on the same axis. The agreement is exact where the physics is determinative and offset where application-layer demands exceed the physics.

In derived systems with layered evidence axes — the FAA case — the compiler finds the threshold of the first layer exactly, identifies where that layer's physics saturates, and stops. The policy requirements above the saturation point are on different physical axes that the compiler cannot reach from the first layer's evidence. The compiler's stopping behavior is itself the finding: it identifies exactly which layer it is reading and where that layer ends.

In chosen systems — the medical AI and consumer credit cases — the compiler finds the evidentiary gaps that any defensible permission function must close. These gaps are the same ones a regulatory body names when it tries to articulate adequate requirements in prose. The agreement is exact where the evidence is determinative and absent where non-evidentiary concerns operate outside the evidence space entirely.

The parallel is not metaphorical. The EXACT entries across all four columns are the same type of object: thresholds where the evidence structure is sharp enough to force a unique boundary, and where independent processes working from different starting points converge to the same answer. The OFFSET entries are the measurable distance between the evidence ceiling and the policy floor on the same axis. The OFFSET_DIFFERENT_AXIS entry is where the evidence axis itself changes character. The COMPILER_PERMISSIVE entries are requirements that arise from outside the evidence, correctly unreachable.

**Proposition 2 (Regulatory correspondence).** In any approximate consequential system — derived or chosen — the compiler's natural authorization boundaries correspond to the evidence-grounded subset of the regulatory thresholds governing that system. Where a regulatory threshold exceeds the compiler's boundary on the same evidence axis, the distance is measurable and equals the policy margin above the evidence. Where a regulatory threshold is grounded in a different evidence axis, the compiler correctly finds no boundary and stops. Where a regulatory threshold arises from outside the evidence entirely, the compiler is silent.

This is a strong claim. It says that regulatory thresholds, whatever their institutional origin, partition into those the evidence forces, those that policy adds on the same axis, those that arise from different physical constraints on different axes, and those that arise from outside the evidence entirely — and that a compiler reading the evidence directly can find this partition without consulting the regulation. The experiments in Sections 2 and 3 provide evidence for it across three independent physical domains, four regulatory traditions (3GPP, FAA, FDA, ECOA/CFPB), and centuries of institutional development.

### 4.5 What this means

The standard account of regulation is that standards bodies and regulatory agencies determine requirements through a combination of technical expertise, stakeholder input, empirical measurement, and policy deliberation. The result is a set of thresholds that reflect all of these inputs simultaneously, in proportions that are not separately visible in the final document.

What the matrix shows is that this composite can be decomposed. The evidence-forced component — the thresholds that the physics or the failure pattern of real deployments requires — is recoverable by a compiler that reads the evidence directly. The policy-added component on the same axis — the thresholds that application-layer demands require above the evidence ceiling — is the measurable residual. And the thresholds that are grounded in different physical constraints entirely — like CAT II's human factors demands — are identifiable as structurally distinct from both: the compiler finds where one physical constraint ends, and its silence on the next constraint is itself informative.

This decomposition has practical consequences. A regulatory threshold that sits exactly on the compiler's natural boundary can be validated: the evidence determines it. A regulatory threshold that sits above the compiler's ceiling on the same axis requires explicit justification for the margin — how much safety buffer, why, and what evidence would reduce it. A regulatory threshold that the compiler cannot reach at all, because it is on a different physical axis, requires a different kind of evidence package entirely — one that the current deployment evidence cannot supply regardless of its quality.

The compiler neither validates nor criticizes any of these. It measures what it can reach, stops where the evidence ends, and is silent where the evidence axis is wrong. All three are information about regulatory design — and all three were available in the evidence all along.

---

## 5. Scope and Limits

The results in Sections 2–4 establish that authorization boundaries in approximate consequential systems have geometric character, that this character is domain-invariant, and that a compiler reading evidence structure directly recovers the evidence-grounded subset of regulatory thresholds across four independent regulatory traditions. These are strong claims, and they have precise limits. This section names those limits exactly.

The limits are not apologies. Each one is a consequence of the framework's core commitment: the compiler reads evidence structure and nothing else. Where the evidence runs out, so does the compiler. That boundary — between what the evidence determines and what it cannot — is itself part of the result.

### 5.1 The compiler cannot name what the evidence does not contain

The most fundamental limit follows directly from Proposition 1. A compiler can find an authorization boundary only if the failure mode that defines it is detectable in the evidence representation. If a failure mode leaves no trace in the evidence — if the evidence is simply silent on whether the failure has occurred — the compiler cannot find the boundary.

This is not a computational limitation. It is a representational one. No amount of sophistication in the compiler can recover a distinction the evidence does not contain. The COMPILER_PERMISSIVE entries in the matrix are not blind spots that a better compiler would fix. They are accurate readings of what the evidence of deployment failure can and cannot certify.

First, the gap taxonomy induced by the over-authorization loop is bounded by the failures available to it. The seven gap types in MED-IND-001 and CRED-IND-001 are the types forced by those specific cases. A different induction set — one that included a deployment that failed because of inadequate labeling, or one that included a security breach attributable to a software vulnerability — would force additional gap types. The taxonomy is not complete with respect to all possible failure modes. It is complete with respect to the failure modes that the available evidence can force. Claiming more would require either a larger induction set or an external vocabulary for failure modes not yet observed.

Second, the correspondence results in Section 3 cannot be reversed. The compiler finds five of six FDA requirements from medical deployment failure evidence and one of three ECOA/CFPB requirements from the credit stress test. The requirements it misses — cybersecurity, labeling, disparate impact, data accuracy — arise from legal frameworks and threat models outside the evidence of individual decision failures. A practitioner who uses the compiler as a compliance checklist will have a sound but incomplete compliance picture: sound on everything the evidence can force, silent on everything it cannot. The compiler should not be used as a substitute for regulatory compliance review. It is a tool for reading what the evidence requires.

### 5.2 The compiler cannot choose policy thresholds

Proposition 2 establishes that the compiler can measure the distance between its evidence ceiling and a regulatory threshold. It does not establish that the compiler can determine whether that distance is correct.

In the physical layer: the compiler finds the natural BLER boundary at 3.49 dB SNR and measures the URLLC policy margin at 0.51 to 1.36 dB. Whether those margins are appropriate for remote process control and factory automation — whether 0.51 dB is enough or too much — depends on the consequences of block failure in those applications, the cost of retransmission, the tolerance of the downstream control system, and the acceptable rate of automation failure. These are engineering and policy questions. The channel physics that the compiler reads cannot answer them. The compiler measures the margin; it cannot evaluate it.

In the socio-technical layer: the compiler determines that ALERT_ROLLOUT requires a PPV floor above Penn Medicine's 0.12 and multi-site validation that Penn Medicine cannot supply. It does not determine whether the PPV floor should be 0.15 or 0.20, how many sites constitute adequate coverage, or what population similarity criterion makes a validation site representative. These are clinical and institutional questions. The over-authorization loop reveals that some threshold must be set; it cannot set the threshold.

This limit is sometimes framed as a weakness. It is not. A tool that correctly identifies where policy judgment is required — and refuses to substitute its own judgment — is more useful than one that silently supplies a number. The compiler's silence on policy thresholds is information: it is telling the user that this decision requires human judgment and specifying precisely which decision that is.

### 5.3 The compiler cannot evaluate the wisdom of institutional choices

In chosen systems, multiple permission functions are consistent with the evidence constraints. The compiler can induce the minimum set of evidence gaps that any defensible permission function must close. It cannot rank the defensible options against each other or determine which institutional choice is better.

The Dutch childcare algorithm's authority_gap and COMPAS's individual_population_gap are both in the induced taxonomy. The compiler can determine that any system that issues automated debt demands of €30,000 without human review, or that uses population recidivism statistics to justify individual detention, fails to close the relevant gap. It cannot determine whether the Dutch government's subsequent prohibition of fully automated administrative sanctions was the right policy response, or whether the Brennan Center's criticism of COMPAS was the right normative stance. These are political and ethical judgments. The compiler is not a substitute for them and does not try to be.

This limit matters especially for chosen domains, where the question "what permission function should we use?" is a genuine open question with multiple defensible answers. The compiler can enforce whatever permission function a profile specifies, and it can reveal through the over-authorization loop which gaps the evidence requires any profile to address. It cannot determine which of the remaining policy choices — the ones above the evidence floor — is correct. Any claim to the contrary would be a misuse of the framework.

### 5.4 The derived/chosen distinction is itself a judgment

The partition between derived and chosen systems is not always crisp. The physical layer cases in Section 2 are unambiguously derived: ground truth exists, the permission function is mathematically determined, two correct compilers must agree. The socio-technical cases in Section 3 are unambiguously chosen: ground truth is contested, multiple permission functions are defensible, institutional risk tolerance shapes the boundary.

But many real systems sit between these poles. A credit scoring system has some mathematically determinable components (default rates over a historical population) and some institutionally chosen ones (what default rate is acceptable for what credit product). A content moderation system has a measurable component (prevalence of a category of content) and a chosen component (what prevalence requires removal). For these hybrid systems, the derived/chosen distinction must be applied at the level of individual gap types, not of the system as a whole. Some gaps in a hybrid system will have unique correct closures; others will require institutional choice. The compiler handles each gap independently, but the practitioner must determine, for each gap, whether its closure is derived or chosen — and that determination is itself a judgment.

The framework does not automate this judgment. It provides the vocabulary and the machinery for making it explicit.

### 5.5 Four regulatory traditions are not a proof of universality

The regulatory correspondence result holds across four independent regulatory traditions: telecommunications, aviation, medical AI, and consumer credit. This is stronger evidence than three traditions — the four share no subject matter, no regulatory body, no scientific community, and no historical connection — but it is not a proof that the result holds universally.

A skeptic could propose that the four traditions were selected because they exhibit the correspondence, and that other domains might not. This is a legitimate concern, and the honest response is that we do not have results across more domains. The theoretical grounding in Propositions 1 and 2 provides a structural argument for why the correspondence should generalize — the mechanism is the geometry of evidence structure, which is domain-agnostic — but structural arguments are not empirical demonstrations.

The FAA result adds a further dimension to the generalization claim: the compiler does not always find the same pattern, and when the pattern changes, the change is itself informative. The FAA's OFFSET_DIFFERENT_AXIS finding at CAT II is a structurally different result from the 3GPP OFFSET finding — and the compiler correctly identifies the difference because it reads the evidence to where it ends. That the compiler produces structurally distinct results in structurally distinct domains is itself evidence that it is reading something real, not fitting a template.

The claim this paper makes is precisely scoped: in these four regulatory traditions, in these specific experiments, with these specific compilers, the correspondence holds and the structural differences are interpretable. The generality claim is that the mechanism is not domain-specific, and that the correspondence is therefore expected wherever the mechanism operates. Testing that expectation in additional domains — legal risk assessment, agentic software pipelines, insurance underwriting — is the natural next step, and is work we have not done.

### 5.6 The policy margin is measurable but its components are not always separable

The OFFSET entries in the unified matrix report the distance between the compiler's evidence ceiling and the regulatory threshold. In the physical layer, this distance is a single number: 0.51 dB for URLLC Rel. 15, 1.36 dB for Factory Rel. 16. In the socio-technical layer, the offset takes a compound form: ALERT_ROLLOUT is blocked by two orthogonal constraints, and the predictive tolerance interval brackets the external finding.

In both cases, the reported distance is the total margin — the aggregate of all policy-layer contributions above the evidence. The framework does not decompose this margin into its components. For URLLC, the 0.51 dB margin reflects some combination of safety factor, measurement uncertainty, future-proofing, and application-specific reliability demand. The compiler cannot determine the relative contribution of each. For the medical AI case, the compound offset reflects the interaction of the utility floor and the distribution shift constraint; the compiler reports the compound but not the marginal contribution of each axis.

This is a limit of the measurement, not a limit of the underlying claim. The claim is that the margin exists, is measurable in aggregate, and is interpretable as policy operating above evidence. The decomposition of that margin into its constituent policy rationales requires domain knowledge the compiler does not have.

### 5.7 Summary

The framework's scope is precisely the space between "the evidence determines everything" and "policy determines everything." In that space — which is where most real consequential systems operate — the compiler can do three things: find the boundaries the evidence forces, measure the distance to boundaries that policy sets above the evidence, and identify the requirements that no available evidence can reach.

It cannot name failure modes outside its vocabulary, set policy thresholds, evaluate institutional choices, determine whether a system is derived or chosen without human judgment, prove universality from four regulatory traditions, or decompose the policy margin into its components. Each of these limits is an honest boundary of a specific capability, not an apology for the work.

The compiler reads what the evidence contains. Where the evidence runs out is, itself, information.

---

## 6. A unification conjecture

The experiments in Sections 2–4 establish the correspondence result empirically across four regulatory traditions. Each case has the same structure: the compiler reads the evidence, finds the boundaries the evidence forces, and stops. The boundaries it finds match those that independent regulatory processes — working from different physics, different failure histories, different institutional mandates, over different timescales — converged to independently.

The empirical pattern raises a mathematical question the experiments do not answer: is this domain-invariance a theorem, or a coincidence observed four times?

We conjecture it is a theorem, and that the four traditions are instances of a single algebraic structure.

**The structural observation.** In every domain studied, the compiler's obstruction sets are monotone in the evidence order: if an evidence state fails to support a permission, any strictly weaker evidence state also fails. This is not an assumption imposed on the domains — it follows from the operational meaning of authorization. Stronger evidence cannot make a previously unsound action unsound. The failure regions point downward; the admissible regions point upward.

Monotonicity alone does not guarantee finiteness. What the experiments suggest is that in all four domains, each monotone failure region has a finite set of minimal bad patterns — a finite obstruction basis — and the compiler's boundaries are exactly those minimal elements. The correspondence result then says something precise: the evidence-forced regulatory thresholds are the minimal elements of the failure regions, and independent regulatory processes converge to the same points because those points are determined by the structure of the evidence space, not by the process that found them.

**Conjecture (Unification).** Let $(\mathcal{E}, \leq)$ be a partially ordered evidence space and let $\{O_i\}$ be a family of upward-closed failure regions, one per permission level, each defined by the evidence constraints of the domain. If $(\mathcal{E}, \leq)$ is Noetherian — every ascending chain of admissible regions stabilizes — then each $O_i$ has a finite antichain of minimal elements, the compiler's obstruction basis is exactly that antichain, and the compiler recovers the evidence-forced authorization boundaries in finite time regardless of how the domain is presented.

Under this condition, the domain-invariance of the correspondence result is not an empirical surprise. It is the expected consequence of the evidence space being Noetherian and the failure regions being upward-closed. Any two processes that correctly identify the minimal elements of the same failure regions must agree — whether those processes are a formal compiler, a standards committee, a regulatory agency, or a body of case law.

**What is open.** Whether the four domains in this paper are Noetherian in the relevant sense, or merely behave as if they are at the resolution the experiments probe, has not been established. For discrete evidence spaces the Noetherian condition has a direct combinatorial interpretation and is verifiable in principle. For continuous evidence spaces — where the evidence geometry is semialgebraic or definable in an o-minimal structure — the appropriate tameness condition may differ, and the connection between o-minimal finiteness theorems and the compiler's obstruction basis has not been formalized. Whether Noetherian is necessary as well as sufficient, and whether a weaker condition captures the same class of domains, is also open.

The conjecture, if true, would explain why the same compiler works in telecommunications, aviation, medical AI, and consumer credit without modification. It would also identify the class of domains where the correspondence result is guaranteed in advance — and by exclusion, the domains where it is not, and why.

---
## Methods

### The compiler

The compiler takes as input an evidence package $\Gamma$ and a permission hierarchy $p_0 < p_1 < \cdots < p_n$, and returns the strongest permission the evidence soundly licenses.

The evidence package is represented as a failure vector: one binary bit per documented failure mode, set to 1 when the failure mode is present or unresolved and 0 when it is ruled out by the evidence. For each permission level $p_i$, the domain specifies which failure modes make $p_i$ unsound — its obstruction set. The compiler scans from $p_n$ downward, checking at each level whether any obstruction bit is active. It returns the first unobstructed level. If all levels are obstructed, it returns REFUSE.

The compiler is sound by construction: it never returns a permission whose obstruction condition is triggered. It is sharp — returning the strongest sound permission — if and only if every relevant failure mode is detectable in the evidence representation. This condition is the central formal result (Appendix A, Theorem 1). The compiler runs in $O(mn)$ time where $m$ is the number of failure bits and $n$ is the number of permission levels; at $m = 100$, $n = 10$, runtime is under 1 µs.

The compiler is implemented in Rust and Python in the noethers-turnstile library (https://github.com/adis-zr/noethers-turnstile). All experiments in this paper are reproducible from the repository.

### Physical layer experiments

**Approximate inference.** Loopy belief propagation (LBP) was implemented directly in NumPy without library wrappers to ensure full observability of convergence behavior. The implementation returns marginals, a convergence flag, iteration count, and final message delta. The convergence flag serves as failure bit $f_1$ directly; it fires without ground truth.

The 2D ferromagnetic Ising model was studied on $4 \times 4$ and $6 \times 6$ grids across coupling strengths $\beta \in {0.10, 0.20, 0.30, 0.40, 0.44, 0.50, 0.60, 0.80, 1.00, 1.50}$. Exact ground truth was computed by brute-force enumeration of all $2^{16}$ states on the $4 \times 4$ grid and by variable elimination on the $6 \times 6$ grid. The critical temperature $\beta_c = 0.44$ is the exact value from Onsager's analytic solution [CITE: Onsager1944].

Two divergence functionals were computed for every run where ground truth was available: mean total variation distance across variables ($d_\text{mean}$) and maximum total variation distance across variables ($d_\text{worst}$). A Bethe free energy proxy ($d_\text{proxy} = |F_\text{Bethe}| / n_\text{vars}$) was computed for runs without ground truth. The proxy achieves Spearman rank correlation $\rho = 0.915$ ($p = 0.0002$) with $d_\text{mean}$ over the full $\beta$ sweep.

Eleven UAI 2022 competition benchmark instances were evaluated spanning five problem families (Grid, Pedigree, Segmentation, Promedus, ObjectDetection; 60–894 variables) [CITE: UAI2022Benchmarks, IhlerUAIData]. Five standard Bayesian networks from the BN repository were evaluated with exact marginals computed by variable elimination [CITE: Scutari2010, Mooij2010]: Asia (8 variables), Child (20), Insurance (27), ALARM (37), MUNIN1 (186). The ALARM result was validated against the reported range from Murphy et al. [CITE: Murphy1999].

**Turbo codes.** BER values were digitized from the original Berrou, Glavieux, and Thitimajshima curves [CITE: Berrou1993], rate-1/2 code, block size $k = 65{,}536$. BLER was estimated via the independence bound $d_\text{BLER} \approx 1 - (1 - d_\text{BER})^k$. The bound is known to overstate BLER due to burst error correlations in turbo-decoded blocks [CITE: Benedetto1996]. Robustness was assessed by applying uniform downward corrections $\delta \in {0.30, 0.50}$ to all BLER values and re-extracting compiler boundaries; results reported in Appendix B.

**ILS approach experiment.** Three failure bits were defined from aircraft-side evidence without consulting any FAA document: $f_1$ (ILS signal integrity failure, self-reported by ground equipment), $f_2$ (RVR below the geometric floor derived from ALSF-2 approach lighting geometry), and $f_3$ (sub-CAT-I authorization absent, fires vacuously when no token exists). The $f_2$ floor was derived geometrically before any FAA document was consulted: on a 3° glideslope with TCH = 50 ft and roll bar at 1,000 ft before threshold, $\text{RVR}_\text{floor}(H) = (H-50)/\tan(3°) - 1{,}000$ ft, giving 1,862 ft at $H = 200$ ft and saturating at $H_\text{sat} = 102.4$ ft. Two sweeps were run across the RVR range 2,400 ft to 0 ft at 100-ft resolution before any FAA document was opened: Sweep A with $f_3$ absent and Sweep B with $f_3$ present. All geometric constants and predicted transition values were written to a pre-registration file before the FAA documents (AC 120-29A, AC 120-28D, FAA Order 8400.13F) were opened.

**3GPP blind audit protocol.** Before consulting any 3GPP document, the compiler was run over both $d_\text{BER}$ and $d_\text{BLER}$ across the SNR range $-1$ to $5$ dB at 0.1 dB resolution, interpolating the Berrou curves onto the fine grid. A five-level permission chain was specified by operational meaning only, with no threshold values, no service class names, and no BLER targets. Natural permission boundaries were extracted from the ridge structure of the permission surface — the SNR values where a unit change in channel quality produces the largest change in licensed permission. These boundaries were recorded before opening any 3GPP specification. The 3GPP documents consulted were: 3GPP TS 38.133 [CITE: 3GPP_TS38133], 3GPP TR 38.913 [CITE: 3GPP_TR38913], 3GPP Release 16 URLLC specification [CITE: 3GPP_Rel16_URLLC], and ITU-T/3GPP B5G evolution document [CITE: ITU_B5G].

### Socio-technical layer experiments

**MED-IND-001 induction procedure.** The induction began from a two-gap taxonomy (approximation quality, evidence freshness) with no domain knowledge consulted. Six harmful deployments were selected to span distinct failure modes and institutional contexts: Epic Sepsis Model [CITE: Wong2021], Optum health risk scoring [CITE: Obermeyer2019], PredPol predictive policing, COMPAS recidivism scoring, IBM Watson Oncology, and the Dutch childcare benefits algorithm. A positive control — a well-validated clinical decision support tool with documented multi-site validation, bounded blast radius, and human-in-the-loop authority — was included to verify that the converged taxonomy does not block sound deployments.

At each induction step, the compiler was run against the current taxonomy. Where the compiler over-authorized relative to expert assessment, the discrepancy was used to identify the minimal positive evidence that would block the over-authorization while permitting the positive control. That evidence requirement was formalized as a new gap type and added to the taxonomy. The loop terminated when no available medical case forced a further gap. Convergence was verified by re-running all six medical cases plus the positive control against the converged six-gap medical taxonomy and confirming no over-authorization.

Generalization was tested on five held-out cases not used in the induction: Boeing 737 MAX MCAS failures, COVID-19 ML models (Roberts et al.), Amazon recruiting algorithm, Allegheny Family Screening Tool, and a hypothetical well-validated full-authority clinical decision support system. Expert assessments for all cases were drawn from published post-incident analyses, regulatory findings, and peer-reviewed literature.

**CRED-IND-001 adverse-action stress test.** A single evidence package was constructed to satisfy all six medically-induced gaps: model specification confirmed for the adverse action target (default risk prediction), approximation quality bounded with individual-level calibration certificates, distribution coverage documented across the deployment population, individual-level predictive validity certified, blast radius bounded to individual lending decisions, and authority contracted with human loan officer review at the final decision step. The package was designed to represent the strongest plausible evidence package for a credit scoring system operating within current practice.

The package was submitted to the compiler against the seven-type profile. The compiler emitted ALR. Expert assessment was REV. The gap was identified by comparing the legal requirements of ECOA §1691(d) and Regulation B §1002.9 against the package contents: the package contained a risk score and supporting validation documentation but no validated reason token — no auditable mapping from model inputs to the specific principal reasons the adverse action legally requires. This token type was formalized as reason_traceability_gap. The converged taxonomy was re-verified: all seven cases now show at least one open gap, and the positive control (notification-only action) correctly emits ALR because reason_traceability_gap does not fire for non-adverse-action permission levels.

**MED-002 Epic Sepsis audit.** The starting evidence package was drawn from Sendak et al. 2020 and vendor documentation: AUROC 0.76, sensitivity 0.54, specificity 0.83, PPV 0.12 at the deployed threshold (score ≥ 6/10), alert rate approximately 20% of inpatients, single-site validation at Penn Medicine. The witness was Wong et al. (2021), JAMA Internal Medicine 181(8):1065–1070 [CITE: Wong2021]: external validation at 7 academic hospitals reporting sensitivity 0.33 and AUROC range 0.63–0.76.

The induction loop was run on the Epic case alone in six explicit steps, with each step documented before proceeding to the next. The PPV threshold sweep covered $\tau_L \in {0.05, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30}$, recording utility-derived permission, distribution shift status, and compound permission at each value.

The tolerance interval analysis derived sensitivity floors for each permission level from the permission hierarchy definition alone, before computing the observed Wong degradation. The ALERT_ROLLOUT floor (0.50) and LIMITED_ROLLOUT floor (0.30) are the minimum sensitivity values at which each level's field contract is satisfiable given the evidence constraints; they are not fitted to the Wong data. The observed drop (0.54 − 0.33 = 0.21 pp) was compared to the compiler's intervals after they were fixed.

**FDA blind audit protocol.** The MED-002 induction was completed in full before the FDA 2025 AI Draft Guidance (Docket FDA-2024-D-4488) was opened. Gap definitions were recorded and locked. The FDA document was then read and each section was matched to the locked gap definitions. No gap definition was modified after the FDA document was consulted. The COMPILER_STRICT and COMPILER_PERMISSIVE classifications were assigned based on the locked definitions against the regulatory text, with no retroactive adjustment.

**ECOA/CFPB blind audit protocol.** The CRED-IND-001 stress test was completed before any ECOA, Regulation B, or CFPB document was consulted. The reason_traceability_gap definition was recorded and locked. The regulatory documents were then read and matched to the locked definition. The same lock-before-open discipline applied as in the FDA audit. Classification was assigned without retroactive adjustment to the gap definition.

### Unified matrix construction

The classification taxonomy — EXACT, OFFSET, COMPILER_STRICT, COMPILER_PERMISSIVE — was defined before any blind audit was conducted, based on the four possible relationships between a compiler boundary and a regulatory threshold: exact match, regulatory threshold above compiler ceiling, compiler boundary more precise than regulatory text, regulatory requirement outside compiler evidence reach. Classifications were assigned independently for each regulatory tradition and combined into the unified matrix after all audits were complete. The OFFSET_DIFFERENT_AXIS classification was added after the FAA experiment revealed a structurally distinct case not covered by the original four categories.

### Computational environment

All inference experiments were run in Python 3.11 with NumPy 1.26. The compiler was run from the noethers-turnstile library (Rust 1.78 core, Python bindings). Benchmark timing was measured on a single core with process isolation; reported values are medians over 100 runs. All code, data, and figure generation scripts are available at https://github.com/adis-zr/noethers-turnstile under the MIT license.

---

## Appendix A: Formal Foundations

This appendix provides the formal basis for the compiler described in the main text and Methods. The main text requires no prior knowledge of these results; they are supplied here for readers who want to verify soundness and sharpness from first principles.

### A.1 The judgment form

An admissibility judgment has the form

$$\Gamma \vdash z : p \ \text{until} \ \varepsilon$$

which reads: under evidentiary context $\Gamma$, output $z$ supports permission $p$ until expiry condition $\varepsilon$.

$\Gamma$ is the evidence package — the complete set of tokens, provenance records, scope contracts, and policy version identifiers available to the compiler at judgment time. $z$ is the system output being evaluated; it fixes which failure modes are relevant. $p$ is the emitted permission — the strongest action the evidence soundly licenses. $\varepsilon$ is the expiry condition — the predicate on state transitions that determines when the judgment lapses.

**Definition (Failure vector).** A vector $\mathbf{f} \in {0,1}^m$ encoding the compiler's view of what has failed for a given state. Each coordinate corresponds to one documented failure mode: bit $i$ is 1 when failure mode $i$ is present or unresolved, 0 when it is ruled out by the evidence.

**Definition (Obstruction set).** For each permission level $p_i$, the obstruction set $O_i \subseteq {0,1}^m$ is the set of failure vectors that make $p_i$ unsound. A permission $p_i$ is blocked when the current failure vector $\mathbf{f} \in O_i$.

**Definition (Sharp compiler).** A compiler is _sound_ if it never emits a permission whose obstruction condition is triggered. It is _sharp_ if it emits the strongest sound permission — if it neither over-authorizes nor under-authorizes.

### A.2 Theorems

**Theorem 1 (Representation).** _A sharp compiler exists if and only if every permission-relevant failure mode is detectable in the evidence representation._

_Proof._ Fix a finite ordered permission set $p_0 \leq p_1 \leq \cdots \leq p_n$.

_Forward direction._ Suppose every permission-relevant failure mode is detectable. For each level $p_i$, the obstruction set $O_i$ is upward-closed in the bit-ordering: if $\mathbf{f} \in O_i$ and $\mathbf{f}' \geq \mathbf{f}$ componentwise, then $\mathbf{f}' \in O_i$. The compiler emits the strongest $p_i$ whose obstruction condition is not triggered. Because the permission set is finite and ordered, this maximum always exists. The output is the strongest sound permission. The compiler is sharp.

_Backward direction._ Suppose some permission-relevant failure mode $k$ is not detectable. Then there exist two underlying states $s, s'$ such that state $s$ has failure mode $k$ active, state $s'$ does not, but both produce the same failure vector $\mathbf{f}$. These states require different permissions. The compiler sees only $\mathbf{f}$ and must assign them the same output. That output is wrong for at least one. No compiler whose complete input is this evidence representation can be sharp.

The obstruction is representational, not computational. No algorithmic sophistication recovers a distinction the evidence does not contain. $\blacksquare$

**Theorem 2 (Judgment completeness).** _The judgment $\Gamma \vdash z : p \ \text{until} \ \varepsilon$ is the minimal form sufficient for expressing admissible compilation._

_Proof._ Sufficiency: the form provides exactly what the representation theorem requires — a body of evidence ($\Gamma$), an output fixing which failure modes are relevant ($z$), an emitted permission ($p$), and a validity condition ($\varepsilon$). Necessity: each term is required. Drop $\Gamma$: no evidence to evaluate. Drop $z$: no judgment shape, and the same evidence licenses different permissions for different outputs. Drop $p$: nothing is authorized. Drop $\varepsilon$: the judgment is incomplete whenever the evidence context can change, which it always can. No fifth top-level term is needed. $\blacksquare$

**Theorem 3 (Canonical expiry).** _A judgment expires on a state transition if and only if the destination state no longer supports the emitted permission. This predicate is the unique sound and sharp expiry rule._

_Proof._ A judgment with permission $p$ survives a transition $s \to s'$ if and only if $\mathbf{f}(s') \notin O_p$. Soundness requires expiry when $\mathbf{f}(s') \in O_p$ — the judgment cannot remain live in a state that does not support it. Sharpness requires persistence when $\mathbf{f}(s') \notin O_p$ — the judgment cannot expire unnecessarily. Together these two requirements pin the predicate uniquely. Any other expiry rule is either unsound or conservative. The invariant is permission preservation, not evidence preservation: expiry is triggered by the destination crossing a permission threshold, not by any change in the evidence. $\blacksquare$

**Theorem 4 (Decidability).** _When the representation condition holds, sharp compilation and expiry checking are both decidable in time $O(mn)$ where $m$ is the number of failure modes and $n$ is the number of permission levels._

_Proof._ The compiler receives a failure vector of $m$ bits and scans from $p_n$ downward over $n+1$ levels, checking at each level whether the obstruction condition is triggered. The scan terminates at the first unobstructed level. $m$ and $n$ are both finite. Total operations: $O(mn)$. Expiry checking is the same scan applied to the destination state's failure vector. $\blacksquare$

**Theorem 5 (Governance record necessity in chosen domains).** _In a chosen domain, the policy selection must be recorded in $\Gamma$. Otherwise the judgment is underdetermined._

_Proof._ In a chosen domain, at least two admissible policies disagree on some reachable state $s$. If neither policy is recorded in $\Gamma$, the compiler receives the same $\Gamma$ under both policies and must assign the same permission to $s$. But the two policies require different permissions at $s$. The judgment is underdetermined. Therefore the policy must be in $\Gamma$. $\blacksquare$

### A.3 Remarks on expiry

**Remark 1 (Finite basis).** The set of failure vectors that destroy permission $p$ has a finite description: a failure vector destroys $p$ if and only if it dominates at least one element of a finite antichain of minimal obstruction patterns. Expiry checking requires no oracle and no history: compute the destination's failure vector, check it against this finite list. The answer is immediate.

**Remark 2 (Path stability).** A judgment remains live along a path if and only if every intermediate state clears the obstruction check. Expiry is monotone: a lapsed judgment cannot be revived, only reissued from a state whose failure vector clears the obstruction. Liveness is a running conjunction that latches false on the first failed state.

**Remark 3 (Conservative rules).** Fixed TTLs, version boundaries, and policy cutoffs are sound but not sharp: they may retire a judgment in a state that still supports it. If such a boundary is part of the domain's permission function, it belongs inside the failure vector and the theorems apply relative to that choice.

---

## Appendix B: Physical Layer Detail

### B.1 Full Ising grid results

The $4 \times 4$ grid results (exact ground truth by brute-force enumeration of $2^{16}$ states) confirm the gap structure seen in the $6 \times 6$ grid at all tested coupling strengths. The $6 \times 6$ grid uses variable elimination for exact ground truth. Results for all ten coupling strengths are given in Table 1 of the main text; the table below gives the complete per-variable breakdown at $\beta_c = 0.44$ for the five variables with the largest individual total variation distances.

|Variable|$d_\text{mean}$ contribution|TV distance|LBP marginal $P(s=1)$|Exact marginal $P(s=1)$|
|---|---|---|---|---|
|21|highest|0.334|0.833|0.499|
|14|second|0.287|0.791|0.512|
|7|third|0.251|0.762|0.511|
|28|fourth|0.198|0.698|0.500|
|35|fifth|0.171|0.671|0.500|

Variable 21's MAP reversal (LBP: $s=1$ with probability 0.833; exact: $s=0$ with probability 0.501) is the most extreme case. Variables 14 and 7 also show directional errors, though less severe. All five variables lie near $P^* = 0.5$ for the exact posterior — a signature of the critical regime where LBP produces the least reliable output.

### B.2 UAI benchmark and named network results

**UAI 2022 benchmarks** (11 instances, no exact ground truth available):

- 9 of 11 instances: compiler emits REFUSE via convergence failure bit $f_1$. BP does not converge; the compiler refuses without computing any quality metric.
- Segmentation_11, Segmentation_13: BP converges, Bethe proxy $d_\text{proxy} \approx 0.9$, compiler emits EXPLORE.
- ObjectDetection_11: BP converges in 50 iterations but Bethe proxy $d_\text{proxy} = 14.5$ due to high variable cardinality ($k = 11$) driving belief inconsistency. Compiler refuses on the proxy alone.

**Named networks** (exact ground truth by variable elimination):

|Network|$N$|$d_\text{mean}$|$d_\text{worst}$|Permission|Reference|
|---|---|---|---|---|---|
|Asia|8|0.0004|0.0033|ACT|—|
|Child|20|0.0045|0.0227|ACT|—|
|Insurance|27|0.0189|0.0954|REPORT|—|
|ALARM|37|0.0100|0.2391|ACT|$\approx 0.005$–$0.02$ ✓ [CITE: Murphy1999]|
|MUNIN1|186|0.0090|0.2356|ACT|$\approx 0.03$–$0.08$ (with evidence)†|

†Murphy et al. report higher errors under evidence. Prior marginals (no observed nodes, as used here) represent an easier setting; $d_\text{mean} = 0.009$ is expected. The load-bearing number is $d_\text{worst} = 0.236$: individual variables that LBP gets badly wrong even when the mean looks acceptable. A compiler using $d_\text{mean}$ alone emits ACT on both ALARM and MUNIN1; a compiler using $d_\text{worst}$ would refuse at any tolerance below 0.239 on ALARM and 0.236 on MUNIN1.

### B.3 Full turbo code BER/BLER table

BER values digitized from Berrou et al. [CITE: Berrou1993], rate-1/2 code, $k = 65{,}536$. BLER via independence bound.

|SNR (dB)|$d_\text{BER}$|$d_\text{BLER}$|Auth. ($d_\text{BER}$)|Auth. ($d_\text{BLER}$)|Gap|
|---|---|---|---|---|---|
|$-1.0$|$2.0 \times 10^{-1}$|1.0000|REFUSE|REFUSE|—|
|0.0|$7.0 \times 10^{-2}$|1.0000|REFUSE|REFUSE|—|
|0.5|$2.0 \times 10^{-2}$|1.0000|REFUSE|REFUSE|—|
|1.0|$5.0 \times 10^{-3}$|1.0000|REFUSE|REFUSE|—|
|1.5|$2.0 \times 10^{-3}$|1.0000|REFUSE|REFUSE|—|
|**2.0**|$3.0 \times 10^{-4}$|1.0000|TRANSMIT_MONITORED|REFUSE|←|
|**2.5**|$2.0 \times 10^{-5}$|0.7304|TRANSMIT_MONITORED|REFUSE|←|
|3.0|$5.0 \times 10^{-7}$|0.0322|TRANSMIT|TRANSMIT_MONITORED|—|
|3.5|$1.0 \times 10^{-8}$|$6.5 \times 10^{-4}$|TRANSMIT|TRANSMIT|closed|
|4.0|$\leq 10^{-9}$|$\leq 6.5 \times 10^{-5}$|TRANSMIT|TRANSMIT|closed|

### B.4 BLER sensitivity analysis

The independence bound $d_\text{BLER} \approx 1 - (1 - d_\text{BER})^k$ overstates BLER due to burst error correlations. Robustness was assessed by applying uniform downward corrections $\delta$ to all BLER values and re-extracting the compiler's natural boundaries.

|Correction $\delta$|$Q_\text{out}$ shift|$Q_\text{in}$ shift|EXACT findings|
|---|---|---|---|
|0 (baseline)|—|—|hold|
|0.30 (2× conservative estimate [CITE: Benedetto1996])|0.03 dB|0.14 dB|hold|
|0.50 (physically implausible)|0.07 dB|0.20 dB|hold|

Both EXACT crossings remain within the 0.5 dB correspondence band at all tested correction levels. The OFFSET findings are robust by construction: lower actual BLER widens the compiler's policy margin rather than closing it.

### B.5 3GPP boundary extraction procedure

The permission surface was computed as a function of both SNR and tolerance $\tau$ at 0.1 dB SNR resolution and 0.001 BLER resolution. Natural boundaries were identified as the ridges of the surface: points where $\partial(\text{permission level}) / \partial(\text{SNR})$ is maximized, corresponding to SNR values where a unit change in channel quality produces the largest change in what can be licensed. Four ridges were identified at SNR crossings 2.66, 2.95, 3.19, and 3.49 dB before any 3GPP document was consulted. These correspond to BLER values 0.50, 0.10, 0.02, and $10^{-3}$ respectively.

---

## Appendix C: Socio-Technical Layer Detail

### C.1 Full MED-IND-001 induction trace

Each induction step is documented in full. For each step: the current profile version, the case triggering the gap, the over-authorization, the forcing observation, and the gap induced.

**Step 1 — clinical_utility_gap** (Epic Sepsis Model). Profile v0 requires only approximation quality and freshness. Compiler emits ALR; expert says REV. Forcing observation: AUC 0.76 is a ranking measure that integrates over all thresholds. It cannot detect that sensitivity 0.33 and PPV 0.12 at the deployed threshold (score ≥ 6) are inadequate for clinical alerting. AUC cannot distinguish a model that ranks well and alerts well from one that ranks well and alerts badly. Gap: clinical_utility_gap — sensitivity and PPV at the deployed operating threshold must be bounded before ALR is reachable.

**Step 2 — model_specification_gap** (Optum health risk scoring). Profile v1 adds clinical_utility_gap. Compiler emits ALR; expert says REV. Forcing observation: the model predicts healthcare cost with high utility, but cost is a proxy for care need. Black patients with equal medical need incur lower costs due to structural access barriers, causing the model to systematically underestimate their care need [CITE: Obermeyer2019]. A model can be well-specified for its stated prediction task and badly specified for the action it authorizes. Gap: model_specification_gap — training target must be adequate for the action target, not merely for the stated prediction task.

**Step 3 — distribution_shift_gap** (PredPol predictive policing). Profile v2. Compiler emits ALR; expert says REV. Forcing observation: increased policing in predicted areas generates more reported crime, which updates the training distribution. The model is accurate on its self-generated distribution. Standard distribution shift analysis cannot detect feedback-coupled distributions. External validation against an independently generated distribution is the only adequate evidence. Gap: distribution_shift_gap — performance on the deployment population must be validated independently of the model's own output history.

**Step 4 — individual_population_gap** (COMPAS recidivism). Profile v3. Compiler emits ALR; expert says REV. Forcing observation: a recidivism score calibrated to population base rates describes statistical group behavior. It does not certify individual predictive validity. Using population-level probabilities to restrict an individual's liberty is a category error that population-level calibration cannot resolve. Gap: individual_population_gap — a population-level score must separately certify its adequacy for individual high-stakes decisions.

**Step 5 — blast_radius_gap** (IBM Watson Oncology). Profile v4. Compiler emits ALR; expert says AEX. Forcing observation: even with all preceding gaps closed, the scope of downstream harm per recommendation must be bounded. Treatment recommendations delivered globally through a system that made clinical override difficult are a different action from the same recommendations in a supervised setting. Gap: blast_radius_gap — the scope of actions licensed per output must be bounded before ALR is reachable.

**Step 6 — authority_gap** (Dutch childcare algorithm). Profile v5. Compiler emits ALR; expert says AEX. Forcing observation: automated debt repayment demands of €30,000 against 26,000 families, with no human review, no explanation of the algorithmic basis, and no accessible appeals process, constitute fully autonomous action at AAA authority level. The scope of autonomous action must be explicitly contracted before ALR. Gap: authority_gap — the boundary between autonomous action and human-confirmed action must be specified before ALR is reachable.

### C.2 CRED-IND-001 induction trace (Step 7)

**Step 7 — reason_traceability_gap** (credit adverse action stress test). Profile v6. The evidence package was constructed to satisfy all six preceding gaps — model specification confirmed, approximation quality bounded, distribution coverage documented, individual predictive validity certified, blast radius bounded, authority contracted with human review. Compiler emits ALR; expert says REV.

Forcing observation: ECOA §1691(d) and Regulation B §1002.9 require that the adverse action notice contain a specific, accurate statement of the principal reasons the creditor relied upon. The evidence package contains a risk score and validation documentation. It does not contain a reason token: an auditable mapping from the model's input features to the specific principal reasons for this applicant's adverse outcome. The loan officer cannot reconstruct which factors were actually considered from the score alone. The evidence supports the decision. It does not supply the reason the decision legally requires.

Gap: reason_traceability_gap — adverse action evidence packages must contain a validated reason token before ALR is reachable for adverse-action permission levels. The gap fires only on actions that carry a legal obligation to communicate specific reasons; it is inactive on notification, flagging, and display actions.

CFPB Circular 2022-03 is the operative clarification: model complexity, including the use of machine learning models, does not exempt a creditor from the reason-statement requirement. A score without a reason token is not a compliant adverse action package regardless of how accurate the score is.

### C.3 Held-out generalization cases

|Case|Compiler|Expert|Result|Notes|
|---|---|---|---|---|
|Well-validated CDS (all gaps bounded, authority contracted)|ALR|ALR|✓ AGREE|Positive control confirms no false blocks|
|Boeing 737 MAX MCAS|REV|REV|✓ AGREE|blast_radius_gap and authority_gap both open|
|COVID-19 ML models (Roberts et al.)|DIA|DIA|✓ AGREE|All gaps open; compiler correctly emits diagnostic only|
|Amazon recruiting algorithm|AEX|REV|~ SAFE|model_specification_gap and distribution_shift_gap open; compiler conservative|
|Allegheny Family Screening Tool|AEX|REV|~ SAFE|individual_population_gap open; compiler conservative|

Conservative results (AEX vs REV) are sound: both are below ALR. No over-authorization occurs in any held-out case.

### C.4 Full regulatory audit tables

The main text reports the FDA 2025 audit (Table 5) and ECOA/CFPB audit (Table 5a). The full audit covers four regulatory frameworks.

**FDA 2025 AI Draft Guidance** (Docket FDA-2024-D-4488):

|Induced gap|FDA element|Section|Classification|
|---|---|---|---|
|distribution_shift_gap|Real-World Performance Monitoring; intended use population spec|§6/§4|EXACT|
|scope_coverage_gap|Validation dataset diversity; PCCP site representation|§5/Appendix C|EXACT|
|operating_point_utility_gap|Clinical performance metrics at intended operating point|Appendix C|EXACT|
|post_market_monitoring_gap|Post-market surveillance plan|§6/PMA|EXACT|
|rollback_criteria_gap|Algorithm change protocol; performance degradation response|§7/PCCP|EXACT|
|clinical_utility_gap|Clinical utility (partial)|Appendix C|COMPILER_STRICT|
|—|Software cybersecurity requirements|§8|COMPILER_PERMISSIVE|
|—|Labeling / Instructions for Use|§9|COMPILER_PERMISSIVE|

**NHS Royal College of Radiologists 2024** [CITE: NHS2024]:

|Induced gap|NHS element|Section|Classification|
|---|---|---|---|
|distribution_shift_gap|Local validation requirements|§4.21|EXACT|
|distribution_shift_gap + individual_population_gap|Population representativeness|§4.22|EXACT|
|authority_gap|Human oversight and governance|§2.13|EXACT|
|clinical_utility_gap|Clinical benefit demonstration|§3.1|EXACT|

**EU AI Act 2024**:

|Induced gap|EU AI Act element|Article|Classification|
|---|---|---|---|
|blast_radius_gap + authority_gap|Risk management system|Article 9|EXACT|
|model_specification_gap + distribution_shift_gap|Data and data governance|Article 10|EXACT|
|individual_population_gap + distribution_shift_gap|Transparency and information|Article 13|EXACT|
|authority_gap|Human oversight|Article 14|EXACT|

**CFPB / ECOA (consumer credit)** — from CRED-IND-001 (see Table 5a in main text):

|Induced gap|Regulatory element|Citation|Classification|
|---|---|---|---|
|reason_traceability_gap|Specific, accurate statement of principal reasons for adverse action; must accurately describe factors actually considered; model complexity not an excuse|ECOA §1691(d); Reg B §1002.9; CFPB 2022-03|EXACT|
|—|Prohibition on disparate impact|12 CFR §1002.6(a)|COMPILER_PERMISSIVE|
|—|Data accuracy procedures|15 U.S.C. §1681e(b)|COMPILER_PERMISSIVE|

1 EXACT · 2 COMPILER_PERMISSIVE.

The two COMPILER_PERMISSIVE entries — disparate impact and FCRA data accuracy — are real regulatory obligations not forced by the evidence structure of the credit adverse action induction. A model can produce a traceable, reason-complete adverse action for every individual decision and still generate systemically discriminatory population-level outcomes. These are orthogonal failure modes on orthogonal evidence axes. The compiler's silence is an accurate reading of what individual-case evidence cannot certify about population-level behavior.

### C.5 Tolerance interval derivation

The sensitivity floors for each permission level are derived from the permission hierarchy's field contracts, not from the Wong data.

ALERT_ROLLOUT requires broad operational rollout across heterogeneous hospital populations. Its field contract specifies that sensitivity must be sufficient to detect the majority of cases across the deployment population — a floor of 0.50 is the minimum at which the clinical purpose of the alert (early sepsis detection) is served at all. At sensitivity below 0.50, the alert system misses more cases than it detects, which is worse than no alert at all given the false positive burden (alert rate ~20% of inpatients, PPV 0.12).

LIMITED_ROLLOUT requires controlled single-site deployment with monitoring. Its field contract requires sensitivity sufficient to detect a meaningful fraction of cases at the training site — a floor of 0.30 is the minimum at which the system provides net clinical value over existing standard-of-care detection at a familiar site with known operating characteristics.

These floors are derived from the clinical purpose of the permission level, not from any external measurement. Penn Medicine baseline: sensitivity 0.54. Max tolerable drop to ALERT_ROLLOUT floor: 0.54 − 0.50 = 0.04 pp. Max tolerable drop to LIMITED_ROLLOUT floor: 0.54 − 0.30 = 0.24 pp. Wong observed drop: 0.54 − 0.33 = 0.21 pp. The observed drop exceeds the ALERT_ROLLOUT tolerance and falls within the LIMITED_ROLLOUT tolerance.

---

## Appendix D: Implementation

The noethers-turnstile library is available at https://github.com/adis-zr/noethers-turnstile under the MIT license.

**Repository structure.**

```
noethers-turnstile/
├── src/                   # Rust compiler core
├── python/                # Python bindings and domain examples  
├── benchmarks/            # Benchmark suite
│   └── run_all.sh         # Single entry point for all benchmarks
├── experiments/
│   ├── ising/             # Ising grid LBP experiments
│   ├── turbo/             # Turbo code BER/BLER experiments  
│   ├── med_ind_001/       # MED-IND-001 induction experiments
│   └── med_002/           # MED-002 Epic depth experiments
└── figures/               # Figure generation scripts
```

**Reproducing results.** All figures and tables in the main text and appendices are reproducible from the repository. The inference experiments require NumPy 1.26 and Python 3.11. The compiler benchmarks require Rust 1.78. A single `make reproduce` command runs all experiments and generates all figures.

**Compiler performance.** The compiler scans $O(mn)$ where $m$ is failure bits and $n$ is permission levels. Measured at 0.49 ns per $(m \times n)$ unit. At $m = 100$, $n = 10$: under 1 µs. Compiler overhead as a fraction of inference runtime drops from $4.9 \times 10^{-3}$ at $n_\text{vars} = 9$ to $1.5 \times 10^{-7}$ at $n_\text{vars} = 10{,}000$: the compiler becomes proportionally cheaper as the underlying problem becomes harder.

**Extending to new domains.** A domain adopter supplies three objects: a claim class defining what kind of output is being evaluated, a profile specifying which gap types must be closed and at what field-contract level, and certifiers for each gap type that evaluate whether the available evidence closes the gap. The compiler handles the permission scan, soundness enforcement, expiry checking, and audit trail. It does not supply gap types, thresholds, or policy choices — those are the domain adopter's responsibility.

---