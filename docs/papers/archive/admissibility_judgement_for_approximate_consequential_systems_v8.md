# Evidence Is Not Permission: Admissible Compilability for Approximate Consequential Systems

**Aditya Sriram**  
Independent Researcher  
adi.sriram.math@gmail.com

---
## Abstract
TBD

---
## 1. Introduction

Someone describes a feature in natural language. An agent writes the ticket. Another writes the spec. Another writes the code, the tests, the deployment manifest. A final agent reviews and ships. At no point did a human check whether the evidence behind each decision was sufficient for the action being taken. Welcome to modern software engineering.

Once you notice this gap, you see it everywhere. A sepsis score adequate for flagging a patient gets used to trigger an automatic order set. A retrieval result adequate for surfacing a document gets used to ground a legal summary.

In each case, evidence valid for one purpose is silently promoted into authorization for a stronger one. This is **evidence overextension**.

_What is the strongest permission this evidence actually supports?_

The remedy is an **admissibility judgment**. A formal account of what each piece of evidence actually licenses, expressed as
$$
\Gamma \vdash z : p \ \text{until}\ \varepsilon,
$$
which reads: under evidentiary context $\Gamma$, an output $z$ supports permission $p$ until expiry condition $\varepsilon$.

This extends the tradition of access-control calculi, proof-carrying code, and capability systems [Abadi et al., 1993; Necula, 1997; Appel and Felten, 1999; Myers, 1999; Schneider, 2000] to evidence rather than proofs.

---

## 2. Approximate consequential systems

A system is **approximate consequential** when four conditions hold - (1) the ideal output is unavailable at decision time, (2) the system acts on an approximation of that ideal output, (3) a downstream workflow treats the approximate output as permission, authority, or control-relevant evidence, and (4) the validity of the output depends on context that can change.

All four conditions are necessary.

The first two conditions distinguish approximate systems from exact ones. Paxos is highly consequential, but its correctness condition is exact.

The third condition is what makes the system consequential. An output becomes dangerous when another system treats it as a license to act. The same evidence may be safe for display, useful for review, and insufficient for automatic action. Absence can mean the check passed, or that it was never run.

The fourth condition is what makes the framework useful for real-time systems. Populations drift, repositories update, policies expire. Admissibility must therefore come with an expiry: admissible until state no longer supports it.

---
## 3. Monotonic Permissions

Permissions form a fixed hierarchy from weakest to strongest, and the strength of the authorized action is determined by the weight of the evidence.

The sepsis example:
$$ \text{flag for review} \leq \text{alert clinician} \leq \text{trigger order set} \leq \text{automatic discharge} $$

The framework's central assumption follows directly: worsening evidence cannot produce stronger permission. A patient whose indicators have deteriorated cannot be licensed for automatic discharge on the basis of that deterioration. This is a semantic commitment about what it means to license an action soundly. Any domain that violates it has the wrong notion of permission.

---
## 4. Derived and Chosen Permission Functions

A **permission function** maps states to permissions. Given the current state of the world, it returns the strongest permission the evidence warrants. The representation theorem takes this function as given. This section explains where it comes from.

In some domains the permission function is unique. The mathematics of the domain, or its governing regulation, admits only one valid assignment of permissions to states. These are **derived domains**. When a domain is derived, the compiler is instantiating a uniquely determined function. Two compilers targeting the same domain should agree on every permission boundary.

In other domains more than one permission function is consistent with the domain's constraints. The choice among them reflects institutional risk tolerance, policy, or precedent. These are **chosen domains**. A compiler in a chosen domain is not implementing a unique correct answer. It is enacting one selection from several defensible ones. That selection requires a written policy.

This distinction has three consequences.

**Compiler authority.** In a derived domain, a correct compiler has mathematical backing. In a chosen domain, the compiler encodes policy.

**Convergence.** In a derived domain, convergence across implementations is evidence of correctness. In a chosen domain, there is no such thing.

**Versioning.** In a chosen domain, the permission boundaries are policy. The audit trail must record which policy was in force, not merely which code version ran.

The distinction determines what kind of error an incorrectly implemented compiler makes. In a derived domain, disagreement between compilers is a bug. In a chosen domain, disagreement may be legitimate, but only if each compiler's selection is traceable to an explicit written policy. Without that traceability, a chosen domain masquerades as a derived one.

---
## 5. Expiry

The expiry term $\varepsilon$ specifies when the judgment is no longer valid.

Expiry is best understood as a condition on state transitions. A permission may be valid in state $s$, but lapse on a transition $s \to s'$ when the evidence in $s'$ no longer justifies it. The central question is which changes in state invalidate the evidential basis for the permission.

In a derived domain, this is exact. The expiry predicate is determined by the same structure that determines $p$: the permission lapses precisely when the evidence falls below the grounding threshold, and the compiler can derive $\varepsilon$ directly.

In a chosen domain, expiry is an invalidation function that encodes policy. The function may be simple, like a fixed TTL, version boundary, or threshold, or a more complex decision on many inputs.

The fundamental difference is that, in chosen domains, $\varepsilon$ is not usually derived from the evidence structure alone. It approximates the domain’s true invalidating transitions, which are often only partially observable.

---
## 6. Admissible Compilers

A compiler can always be safe by emitting the weakest permission. The harder question is when it can be sharp: when it can emit the strongest permission the situation actually warrants, no more and no less.

**Definition (Failure vector)**. A vector that encodes the compiler's view of what has failed for a given state. One **failure bit** per documented failure mode, 1 when present or unresolved, 0 when ruled out

**Definition (Sharp compiler).** A compiler is *sharp* if it emits the strongest permission the evidence warrants.

Sharpness is possible exactly when the evidence representation is fine enough to distinguish every permission-relevant way things can go wrong. If every relevant failure leaves a detectable trace, the compiler can identify the highest sound permission. If some relevant failure is invisible to the evidence, then two states that require different permissions may look identical to the compiler.

**Theorem 1 (Representation).** _A sharp compiler exists if and only if every permission-relevant failure mode is detectable in the evidence representation._

*Proof.* Fix a finite ordered set of permissions $p_0 \leq p_1 \leq \cdots \leq p_n$. For each level $p_i$, the domain specifies which failure modes make $p_i$ unsound.

**Forward direction.** Suppose every permission-relevant failure mode is detectable. Then for each permission level $p_i$, the set of failure vectors that block $p_i$ is upward-closed: if a vector already contains enough obstruction to block $p_i$, any vector with at least as many active bits also blocks it. The compiler emits the strongest $p_i$ whose failure condition is not triggered by the current vector. Because the permission set is finite and ordered, this maximum always exists, and the output is exactly the strongest sound permission. The compiler is sharp.

**Backward direction.** Suppose some permission-relevant failure mode is not detectable. Then two underlying states with identical failure vectors require different permissions. The compiler sees only the vector, so it assigns both states the same output. That output is wrong for at least one of them. No compiler whose complete input is this evidence can be sharp. 

Note that the obstruction is representational, not computational. No cleverness in the compiler can reconstruct a distinction the evidence does not contain. $\blacksquare$

**Theorem 2 (Judgment completeness).** _The judgment $\Gamma \vdash z : p \text{ until } \varepsilon$ is the minimal form sufficient for expressing admissible compilation._

*Proof.* The representation theorem requires four things: a body of evidence from which failure bits can be read off, an output that fixes which failure modes are relevant, an emitted permission, and a validity condition specifying when the judgment lapses. The four terms supply exactly these: $\Gamma$ is the evidence context, $z$ fixes the judgment shape, $p$ is the emitted permission, and $\varepsilon$ is the expiry condition. So the form is sufficient.

Each term is necessary. Drop $\Gamma$ and the compiler has no evidence to evaluate. Drop $z$ and the compiler has no judgment shape, and the same evidence can license different permissions for different outputs. Drop $p$ and nothing is authorized. Drop $\varepsilon$ and the judgment says what is licensed now but not when that lapses, which is incomplete whenever the evidence context can change.

Everything else belongs either inside $\Gamma$ or downstream of the judgment entirely. No fifth top-level term is needed. $\blacksquare$

**Theorem 3 (Canonical expiry).** _The resulting judgment expires on a transition if and only if the destination state no longer supports the emitted permission. This predicate is the unique sound and sharp expiry rule._

*Proof.* A judgment issued with permission $p$ survives a transition if and only if the destination's failure vector still clears $p$'s obstruction check. Soundness forces expiry when it fails — a judgment cannot remain live in a state that does not support it. Sharpness forces persistence when it passes — a judgment cannot expire unnecessarily. Together these two requirements determine the predicate completely. Any other expiry rule is either unsound or conservative.

The invariant is permission preservation, not evidence preservation. A transition may change the failure vector and still preserve the permission. Expiry is triggered by the destination crossing a permission threshold, not by the evidence changing. $\blacksquare$

**Theorem 4 (Decidability).** _When the representation condition holds, sharp compilation and expiry checking are both decidable in time linear in the number of failure modes and permission levels._

*Proof.* The compiler's input is a failure vector of $m$ bits, each decidable by assumption, over a permission hierarchy of $n+1$ levels. The compiler scans from $p_n$ downward, checking at each level whether the failure vector contains an active obstruction. The scan terminates at the first unobstructed level. Since $m$ and $n$ are finite, the procedure runs in $O(mn)$ steps. Expiry checking is the same scan applied to the destination state. $\blacksquare$

**Theorem 5 (Governance record necessity in chosen domains).** _In a chosen domain, the policy must be recorded in the evidentiary context $\Gamma$. Otherwise the judgment is underdetermined, and the same evidence is compatible with multiple sharp outputs._

*Proof.* Assume two admissible policies that disagree on some reachable state; if neither is recorded in $\Gamma$, the same inputs are compatible with two different sharp outputs. Therefore the judgment is underdetermined. $\blacksquare$

**Remark 1 (Finite basis for permission-destroying transitions).** Because expiry depends only on whether the destination supports the issued permission, transition history is irrelevant — only where you land matters. And the set of dangerous landing zones has a finite description: the destination destroys permission $p$ if and only if its failure vector dominates at least one element of a finite anti-chain of minimal obstruction patterns. This anti-chain is the same finite basis established by the representation theorem, now read as a characterization of bad destinations rather than bad states. Consequently, expiry checking requires no oracle and no history: compute the destination's failure vector, check it against a finite list of patterns, and the answer is immediate.

**Remark 2 (Path stability).** A judgment remains live along a path if and only if every intermediate state clears the destination check. Since expiry is monotone — a lapsed judgment cannot be revived, only reissued from a state whose failure vector supports the original permission — the compiler never needs to re-examine history. Liveness is a running conjunction: it starts true and latches false the moment any state along the path fails the obstruction check for the issued permission.

**Remark 3 (Conservative expiry rules).** Conservative rules like fixed TTLs, version boundaries, and policy cutoffs are sound but not sharp: they may retire a judgment the destination still supports. If such a boundary is part of the permission function, it belongs inside the failure vector and the theorem applies relative to that choice. A static expiry bit records whether a particular transition triggered expiry, but says nothing about which transitions preserve the permission or why.

---
## 7. When Sharpness Is Possible

The representation theorem guarantees a sharp compiler exists when every permission-relevant failure mode is detectable. That is a strong assumption. When does it hold?

Before answering, it is worth being precise about what the compiler cannot do. The compiler enforces domain policy. It cannot determine value thresholds, name failure modes outside its vocabulary, or verify that the profile reflects the designer's intent. That is domain-specific precondition.

Given a fully specified policy, Theorem 1 already answers the question: sharpness holds when every failure mode is detectable. The harder case is a chosen domain, where policy is being approximated. There, full specification is genuinely difficult, and what you get without it is a sound but not sharp compiler — one whose output looks correct but may be permanently withholding legitimate permissions with no signal that anything is wrong.

The practical consequences both follow from Theorem 1. The forward direction: Early judgments set the ceiling, and a conservative one constrains every downstream judgment built on it. The backward direction: an overly permissive one cannot be corrected without reissuing from the point of error.

In a chosen domain, this is the design lever. Specify cautiously where the boundary matters most, and specify it early. The compiler will faithfully execute what it receives — and later judgments will inherit whatever the earlier ones established.

---

## 8. Derived domain case study: Approximate inference

The approximate inference domain is the clean derived case. The ideal output — the exact posterior — is unavailable at decision time. The system acts on an approximation. Downstream workflows treat that approximation as permission to act. And the validity of the approximation depends on the structure of the graphical model, which can change. All four conditions of an approximate consequential system hold.

What makes this domain derived rather than chosen is that the permission function is not a policy selection. Once a divergence functional $d$ and a monotone tolerance profile $\tau : P \to \mathbb{R}_{\geq 0}$ are fixed, the licensing map

$$\lambda_{d,\tau}(\omega) = \max{p \in P : d(\omega) \leq \tau(p)}$$

is uniquely determined. Two compilers targeting the same $d$ and $\tau$ must agree on every permission boundary. There is no room for institutional risk tolerance or precedent. The compiler is instantiating a mathematically determined function, not enacting a policy choice.

The central question for the derived case is therefore not _which_ permission function to use, but _which divergence functional to use_ — and whether that choice is itself visible to the compiler. We show that it is not always visible, that the choice determines the permission surface, and that the gap between two natural candidates is structural rather than arbitrary.

### 8.1 Experimental Setup

We implement loopy belief propagation (LBP) and mean field (MF) directly in NumPy, without library wrappers, to ensure full observability of convergence behavior [CITE: Murphy1999]. The implementation returns marginals, a convergence flag, iteration count, and final message delta. The convergence flag is failure bit $f_1$ directly; it fires without ground truth.

**Ising grids.** We study the 2D ferromagnetic Ising model on $4 \times 4$ and $6 \times 6$ grids across a coupling sweep $\beta \in {0.10, 0.20, 0.30, 0.40, 0.44, 0.50, 0.60, 0.80, 1.00, 1.50}$. Exact ground truth is computed by brute-force enumeration of all $2^{16}$ states on the $4 \times 4$ grid and by variable elimination on the $6 \times 6$ grid. The critical temperature $\beta_c = 0.44$ is the exact value from Onsager's solution of the 2D Ising model [CITE: Onsager1944].

**UAI benchmarks.** We evaluate 11 instances from the UAI 2022 competition benchmark set (tuning phase) [CITE: UAI2022Benchmarks], spanning five problem families: Grid, Pedigree, Segmentation, Promedus, and ObjectDetection. These problems range from 60 to 894 variables. Exact marginals are unavailable; the compiler uses failure bit $f_1$ (convergence) and a Bethe free energy proxy $d_3 = |F_\text{Bethe}| / n_\text{vars}$ [CITE: Yedidia2005]. Reference solutions are from Ihler et al. [CITE: IhlerUAIData].

**Named networks.** We evaluate five standard Bayesian networks from the BN repository [CITE: Scutari2010]: Asia, Child, Insurance, ALARM, and MUNIN1. Exact marginals are computed by variable elimination [CITE: Mooij2010]. The ALARM network is validated against the reported range from Murphy, Weiss, and Jordan [CITE: Murphy1999].

**Permission chain.** We fix a three-level chain throughout:

|Level|Name|$\tau$ threshold|
|---|---|---|
|$p_2$|ACT|$d \leq 0.01$|
|$p_1$|REPORT|$d \leq 0.05$|
|$p_0$|EXPLORE|$d \leq 0.20$|
|$\varnothing$|REFUSE|above all thresholds|

**Divergence functionals.** We compute three functionals for every run where ground truth is available:

$$d_1(\omega) = \frac{1}{n} \sum_i \frac{1}{2} \sum_s |q_i(s) - p^*_i(s)| \quad \text{(mean TV)}$$

$$d_2(\omega) = \max_i \frac{1}{2} \sum_s |q_i(s) - p^*_i(s)| \quad \text{(max TV)}$$

$$d_3(\omega) = |F_\text{Bethe}| / n_\text{vars} \quad \text{(Bethe proxy, no ground truth required)}$$

The Bethe proxy $d_3$ achieves Spearman rank correlation $\rho = 0.915$ ($p = 0.0002$) with $d_1$ over the full $\beta$ sweep, validating its use as a proxy on problems where exact marginals are unavailable.

### 8.2 The Threshold Sweep and the Gap Region

The primary experimental contribution is a threshold sweep: rather than fixing $\tau$ externally and observing the compiler's output, we sweep $\tau \in [0,1]$ continuously and ask what the permission surface looks like as a function of both $\beta$ and $\tau$.

For the $6 \times 6$ Ising grid under loopy BP, the results are as follows.

**Table 1.** TV values and gap structure across the $\beta$ sweep ($6 \times 6$ grid, loopy BP). The gap interval is the set of $\tau$ values where $d_1 \leq \tau < d_2$: mean TV licenses a permission that max TV refuses. Binary failure columns show disagreements at standard practitioner threshold values.

|$\beta$|$d_1$ (mean TV)|$d_2$ (max TV)|Gap interval|Gap at standard $\tau$|
|---|---|---|---|---|
|0.10|0.0063|0.0154|[0.006, 0.015]|$\tau = 0.01$: mean $\to$ ACT, max $\to$ REFUSE|
|0.20|0.0130|0.0332|[0.013, 0.033]|—|
|0.30|0.0246|0.0529|[0.025, 0.053]|$\tau = 0.05$: mean $\to$ ACT, max $\to$ REFUSE|
|0.40|0.1156|0.1979|[0.116, 0.198]|—|
|0.44 ($\beta_c$)|0.2231|0.3338|[0.223, 0.334]|$\tau = 0.30$: mean $\to$ ACT, max $\to$ REFUSE|
|0.50|0.3228|0.4393|[0.323, 0.439]|—|
|0.60|0.3926|0.5021|[0.393, 0.502]|$\tau = 0.50$: mean $\to$ ACT, max $\to$ REFUSE|
|0.80|0.4319|0.5532|[0.432, 0.553]|$\tau = 0.50$: mean $\to$ ACT, max $\to$ REFUSE|
|1.00|0.4415|0.5791|[0.442, 0.579]|$\tau = 0.50$: mean $\to$ ACT, max $\to$ REFUSE|
|1.50|0.4468|0.5937|[0.447, 0.594]|$\tau = 0.50$: mean $\to$ ACT, max $\to$ REFUSE|

The gap region is non-empty at every $\beta$ value. It grows with $\beta$ and jumps at $\beta_c$. No standard $\tau$ value avoids it. The gap at $\beta_c$ spans $[0.223, 0.334]$ — any practitioner who sets $\tau$ anywhere in this interval is in the gap: $d_1$ says the approximation is adequate, $d_2$ says at least one variable is materially wrong.

The gap region is not a property of the permission chain or the threshold choice. It is a property of the relationship between $d_1$ and $d_2$, which follows from the structure of the approximation. Formally, $d_2 \geq d_1$ always, with equality only when all variables are equally approximated. The gap is the region where they disagree, and its width is determined by the approximation's unevenness across variables.

### 8.3 The Gap Is Structural, Not a Threshold Artifact

A reader might object: the gap exists because the two functionals have different thresholds, and a practitioner who uses $d_2$ from the start would not be in the gap. This objection is correct but misses the point.

The argument is not that practitioners cannot use $d_2$. The argument is that $d_1$ is the natural first choice — it is the standard summary statistic for marginal error, it is what Murphy et al. report [CITE: Murphy1999], and it is what a system designer would reach for before thinking carefully about the downstream action. The gap is the region where that natural choice is wrong, and it is structural: it exists regardless of which $\tau$ the practitioner chose.

The Representation Theorem (Theorem 1) makes this precise. A sharp compiler exists if and only if every permission-relevant failure mode is detectable in the evidence representation. The failure mode here is "at least one variable is materially wrong." Under $d_1$, this failure mode is not detectable: $d_1$ averages over variables and cannot distinguish a uniformly adequate approximation from one where most variables are well-approximated and one is badly wrong. Under $d_2$, the failure mode is detectable. The compiler using $d_1$ cannot be sharp on this failure mode. The compiler using $d_2$ can.

The gap region is the set of states where this distinction matters: states where $d_1$ would authorize action but $d_2$ refuses it. Its area, width, and location are properties of the approximation structure, not of the policy.

### 8.4 A Concrete Witness

The most striking single result is at $\beta = 0.44$, variable 21 of the $6 \times 6$ grid:

- Approximate marginal (LBP): $P(s = 1) = 0.833$
- Exact marginal: $P(s = 0) = 0.501$

The approximate posterior assigns 83% confidence to the wrong MAP state. The exact posterior barely favors the other state — this is not a case where the approximation is directionally correct but numerically imprecise. It is a MAP reversal.

At $\tau = 0.30$, $d_1 = 0.223 \leq \tau$: the compiler using mean TV authorizes action. $d_2 = 0.334 > \tau$: the compiler using max TV refuses. The system authorized by mean TV acts on a posterior that is 83% confident in the wrong answer.

This is not a pathological case. $\beta = 0.44$ is the critical temperature of the 2D Ising model — a regime that has been studied extensively and where BP is known to produce unreliable marginals [CITE: Murphy1999, Yedidia2005]. The failure was available in the evidence. The functional that detected it was available. The over-authorization happened because the wrong functional was used.

### 8.5 UAI Benchmarks and Named Networks

On 11 UAI benchmark instances [CITE: UAI2022Benchmarks, IhlerUAIData], the compiler operating without ground truth relies on $f_1$ (convergence failure) and $d_3$ (Bethe proxy). Results:

- 9 of 11 instances: REFUSE via $f_1$. BP does not converge; the compiler refuses without needing to compute any quality metric. This is the Representation Theorem forward direction: the failure mode is detectable, the compiler is sharp on it.
- 2 of 11 instances (Segmentation_11 and Segmentation_13): BP converges, $d_3 \approx 0.9$, compiler emits EXPLORE.
- 1 instance (ObjectDetection_11): BP converges in 50 iterations, but $d_3 = 14.5$ due to high cardinality ($k = 11$) driving belief inconsistency. The compiler refuses on the proxy alone.

On named networks with exact ground truth [CITE: Scutari2010]:

**Table 2.** Named network results. The ALARM result is validated against the reported range of Murphy et al. [CITE: Murphy1999].

|Network|$N$|$d_1$|$d_2$|Permission|Reference|
|---|---|---|---|---|---|
|Asia|8|0.0004|0.0033|ACT|—|
|Child|20|0.0045|0.0227|ACT|—|
|Insurance|27|0.0189|0.0954|REPORT|—|
|ALARM|37|0.0100|0.2391|ACT|$\approx 0.005$–$0.02$ ✓ [CITE: Murphy1999]|
|MUNIN1|186|0.0090|0.2356|ACT|$\approx 0.03$–$0.08$ (with evidence)†|

†Murphy et al. [CITE: Murphy1999] report higher errors under evidence. Prior marginals (no observed nodes, as used here) are an easier setting; $d_1 = 0.009$ is expected. The load-bearing number is $d_2 = 0.236$: there are individual variables LBP gets badly wrong even when the mean looks acceptable. The compiler using $d_1$ emits ACT on ALARM and MUNIN1. The compiler using $d_2$ would refuse at any $\tau < 0.239$ on ALARM and any $\tau < 0.236$ on MUNIN1 — a wide range of practically relevant thresholds.

### 8.6 Register 2: Turbo Codes and the Same Structural Gap

The gap structure identified in approximate inference reappears, with the same mathematical form, in a domain with no inferential content: digital communications.

Turbo codes, introduced by Berrou, Glavieux, and Thitimajshima [CITE: Berrou1993], achieve near-Shannon-limit performance by running an algorithm equivalent to loopy belief propagation on a chain-structured graphical model [CITE: McEliece1998]. Murphy et al. establish this connection explicitly [CITE: Murphy1999]. The decoder produces an approximate posterior over transmitted bits, and the downstream action — transmitting or retransmitting a block — depends on the quality of that approximation.

Two divergence functionals arise naturally:

$$d_\text{BER} = \frac{\text{incorrectly decoded bits}}{\text{total bits}} \quad \text{(bit error rate)}$$

$$d_\text{BLER} = \mathbf{1}[\text{any bit in block incorrect}] \quad \text{(block error rate, averaged over blocks)}$$

The structural analogy with Register 1 is exact:

|Concept|Register 1 (Inference)|Register 2 (Communications)|
|---|---|---|
|Mean-like functional|$d_1$: averages over variables|$d_\text{BER}$: averages over bits|
|Max-like functional|$d_2$: worst-case variable|$d_\text{BLER}$: any bit fails $=$ block fails|
|Gap mechanism|$d_2 \geq d_1$ by construction|$d_\text{BLER} = 1 - (1 - d_\text{BER})^k$|
|Structural amplification|$d_2 / d_1 \gg 1$ near $\beta_c$|$d_\text{BLER} / d_\text{BER} > 3000$ at SNR $= 2$ dB|
|Binary failure example|$\beta = 0.30$, $\tau = 0.05$: ACT / REFUSE|SNR $= 2$ dB: TRANSMIT / REFUSE|

The compiler does not distinguish between these domains. It receives a divergence functional and emits a judgment. The gap is the same phenomenon in both cases, arising from the same mathematical relationship between an aggregating functional and a worst-case functional over components.

**Table 3.** Cross-register turbo code results. BER values are digitized from Berrou et al. [CITE: Berrou1993], rate-1/2 code, block size $k = 65536$. BLER is estimated via the independence bound; see §8.7 for robustness analysis.

|SNR (dB)|$d_\text{BER}$|$d_\text{BLER}$|perm($d_\text{BER}$)|perm($d_\text{BLER}$)|Gap?|
|---|---|---|---|---|---|
|$-1.0$ to $1.5$|$2 \times 10^{-1}$ to $2 \times 10^{-3}$|$1.0000$|REFUSE|REFUSE|—|
|$2.0$|$3 \times 10^{-4}$|$1.0000$|TRANSMIT_MONITORED|REFUSE|←|
|$2.5$|$2 \times 10^{-5}$|$0.7304$|TRANSMIT_MONITORED|REFUSE|←|
|$3.0$|$5 \times 10^{-7}$|$0.0322$|TRANSMIT|TRANSMIT_MONITORED|—|
|$3.5+$|$\leq 10^{-8}$|$\leq 7 \times 10^{-4}$|TRANSMIT|TRANSMIT|closed|

The gap spans approximately 1 dB in SNR — the interval from 2.0 to 3.0 dB. In this regime, $d_\text{BER}$ has cleared the voice communication standard ($10^{-3}$), yet at SNR $= 2.0$ dB every block fails: $d_\text{BLER} = 1.0$. A system using $d_\text{BER}$ as its divergence functional transmits. A system using $d_\text{BLER}$ refuses. The gap is structural — it persists across the full $\tau$ sweep, not at a single threshold value.

### 8.7 Blind Audit of the 3GPP Permission Hierarchy

The 3GPP standards specify a permission hierarchy for 5G New Radio transmissions with exact BLER thresholds assigned to service classes [CITE: 3GPP_TS38133, 3GPP_TR38913, 3GPP_Rel16_URLLC]. This hierarchy was written by an engineering committee over decades of standardization work. We ask a different question: what does the compiler find when it does not know the standard exists?

We run the compiler blind — no 3GPP documents, no service class names, no threshold values. We sweep both $d_\text{BER}$ and $d_\text{BLER}$ across the full SNR range from $-1$ to $5$ dB at 0.1 dB resolution, interpolating the Berrou curves onto the fine grid. We use a 5-level permission chain specified by operational meaning only, before any threshold values are set. We extract the compiler's natural permission boundaries from the ridge structure of the permission surface — the SNR values where a small change in channel quality produces the largest change in what can be licensed. We record these boundaries, then open the 3GPP specifications and compare.

**Natural boundaries extracted blind** (from $d_\text{BLER}$ crossings, before any 3GPP document consulted):

|Permission boundary|$\tau$ (BLER)|$\tau$ (BER)|SNR crossing|
|---|---|---|---|
|TRANSMIT_CRITICAL|$10^{-3}$|$2.0 \times 10^{-8}$|3.49 dB|
|TRANSMIT_DATA|$0.02$|$3.1 \times 10^{-7}$|3.19 dB|
|TRANSMIT_MONITORED|$0.10$|$2.4 \times 10^{-6}$|2.95 dB|
|HOLD|$0.50$|$1.4 \times 10^{-5}$|2.66 dB|

**Table 4.** Audit result: compiler-derived boundaries versus 3GPP thresholds. Gap width is measured between $d_\text{BER}$ and $d_\text{BLER}$ at the crossing SNR. Compiler SNR is from $d_\text{BLER}$ crossings; 3GPP reference SNR is the crossing of the published BLER curve against the standard's threshold value.

|3GPP threshold|Source|Ref. BLER|Ref. SNR|Compiler $\tau$ (BLER)|Compiler SNR|Classification|
|---|---|---|---|---|---|---|
|eMBB CSI target|3GPP Rel. 15 [CITE: 3GPP_TR38913]|$10^{-1}$|2.95 dB|$0.10$|2.95 dB|**CORRESPONDENCE**|
|RLM $Q_\text{out}$|3GPP TS 38.133 [CITE: 3GPP_TS38133]|$10^{-1}$|2.95 dB|$0.10$|2.95 dB|**CORRESPONDENCE**|
|RLM $Q_\text{in}$|3GPP TS 38.133 [CITE: 3GPP_TS38133]|$2 \times 10^{-2}$|3.19 dB|$0.02$|3.19 dB|**CORRESPONDENCE**|
|URLLC Rel. 15|3GPP TR 38.913 [CITE: 3GPP_TR38913]|$10^{-5}$|4.00 dB|$10^{-3}$|3.49 dB|**COMPILER PERMISSIVE** (+0.5 dB)|
|Factory Rel. 16|3GPP Rel. 16 [CITE: 3GPP_Rel16_URLLC]|$10^{-6}$|4.85 dB|$10^{-3}$|3.49 dB|**COMPILER PERMISSIVE** (+1.35 dB)|
|B5G evolution|ITU/3GPP post-Rel. 17 [CITE: ITU_B5G]|$10^{-9}$|—|—|—|**OUT OF RANGE**|

The result divides cleanly. Three of five observable thresholds correspond exactly to the compiler's natural boundaries. The compiler found BLER $= 0.10$ and BLER $= 0.02$ as natural permission boundaries without knowing those values appear in 3GPP TS 38.133 [CITE: 3GPP_TS38133]. They are not arbitrary committee choices. They are the points where the gap between $d_\text{BER}$ and $d_\text{BLER}$ is widest — where the functional choice matters most — and the compiler identifies them because it is sensitive to exactly that structure.

The two URLLC thresholds sit 0.5 to 1.35 dB above the compiler's highest natural boundary. The compiler is more permissive than the standard in this regime. This is the more important finding. The URLLC reliability requirements — BLER $= 10^{-5}$ for remote process control, BLER $= 10^{-6}$ for factory motion control and grid fault switching [CITE: 3GPP_Rel16_URLLC, 5GAmericasURLLC] — reflect application-layer demands the channel model cannot encode. The compiler identifies exactly where the physical constraint ends and where deliberate policy begins: the 0.5 to 1.35 dB interval is the formal signature of that policy operating above the physics. The compiler neither validates nor criticizes this policy margin. It measures it.

_Sensitivity analysis._ BLER values in the transition regime are estimated via the independence bound $d_\text{BLER} \approx 1 - (1 - d_\text{BER})^k$ [CITE: Benedetto1996]. The bound is known to overstate BLER due to error burst correlations in turbo-decoded blocks. We assess robustness by applying a uniform downward correction $\delta$ to all BLER values and re-extracting the compiler's natural boundaries. Under $\delta = 0.30$ — twice the conservative estimate from Benedetto and Montorsi [CITE: Benedetto1996] — the $Q_\text{out}$ crossing shifts by $0.03$ dB and the $Q_\text{in}$ crossing by $0.14$ dB. Both remain well within the $0.5$ dB correspondence threshold. At $\delta = 0.50$, a physically implausible 50% overstatement, the shifts are $0.07$ dB and $0.20$ dB respectively. The correspondence finding does not depend on the independence bound being tight. The waterfall region is steep enough — approximately 0.3–0.4 BLER units per dB at the crossing points — that small BLER corrections produce negligible horizontal displacement. The URLLC permissive findings are robust by construction: if actual BLER is lower than the bound, the compiler is even more permissive than reported, widening the margin with the standard rather than closing it.

### 8.8 What the Derived Domain Example Demonstrates

The approximate inference and turbo code experiments together establish three claims.

**Claim 1: The choice of divergence functional determines the permission surface.** Two compilers targeting the same approximation quality, using $d_1$ and $d_2$ respectively, emit different permissions across a structural gap region that grows with approximation difficulty and is non-empty at every operating point tested. This is the Representation Theorem made concrete: $d_1$ cannot detect the failure mode "at least one component is materially wrong," so the compiler using $d_1$ cannot be sharp on that mode.

**Claim 2: The gap structure is domain-invariant.** The same structural relationship — mean-like functional over-authorizes relative to max-like functional, by the law $d_\text{max} \geq d_\text{mean}$ or equivalently $d_\text{BLER} = 1 - (1 - d_\text{BER})^k$ — appears in both approximate inference and digital communications. The compiler does not know which domain it is operating in. It sees a divergence functional and emits a judgment. The gap is a property of the functional's relationship to the downstream action, not of the domain.

**Claim 3: Blind audit of an existing standard reveals its physical grounding.** The compiler, run without knowledge of the 3GPP standard [CITE: 3GPP_TS38133, 3GPP_TR38913], finds natural permission boundaries that correspond exactly to the 3GPP Radio Link Monitoring thresholds. The URLLC thresholds sit above the compiler's physical boundaries by a measurable margin. This separation — which thresholds are physically grounded and which encode deliberate policy — was not previously formally expressed. The compiler produces it as a consequence of the permission surface geometry.

The derived domain is important because the compiler here is not enforcing policy. It is reading structure that was always latent in the approximation, making it visible, and showing that an existing standard was encoding that structure correctly at the points where the physics required it to.


---

## 9. Chosen domain case study: Epic sepsis model

The Epic sepsis model is a useful case because the failure was not the absence of evidence. It was the promotion of one kind of evidence into a stronger permission than it supported.

We ask a specific question: can the over-authorization loop recover the policy structure of a chosen domain from a single empirical witness, without consulting the regulation? We show that it can — and that the compiler's natural tolerance interval contains a degradation figure observed four years after deployment, by a different team, at different institutions, without the compiler having seen it.

### 9.1 Starting evidence and witness

The Penn Medicine internal validation, circa 2017, comprised the following evidence package:

|Metric|Value|Source|
|---|---|---|
|AUROC|0.76|Sendak et al. 2020 / vendor documentation|
|Sensitivity|0.54|at deployed threshold (score ≥ 6/10)|
|Specificity|0.83||
|PPV|0.12|at ~4% inpatient base rate|
|Alert rate|~20% of inpatients flagged||
|Validation|single-site (Penn Medicine)||

The witness is Wong et al. (2021), _JAMA Internal Medicine_ 181(8):1065–1070: external validation at 7 academic hospitals. Sensitivity 0.33, AUROC range 0.63–0.76 (Penn Medicine was the ceiling, not the floor), 18% of sepsis patients missed without alert at some sites. The sensitivity drop from the internal figure is 0.21 percentage points, a 39% relative degradation.

### 9.2 Induction loop

We begin with a weak profile containing only structural gaps: approximation quality and freshness. No domain knowledge is consulted. At this profile, the compiler emits ALERT_ROLLOUT; the expert says LIMITED_ROLLOUT. This is the over-authorization baseline.

We run the loop in six explicit steps. At each step, the compiler over-authorizes relative to the expert; the discrepancy forces exactly one gap.

**Step 1 — clinical_utility_gap.** The Wong witness supplies sensitivity 0.33 and PPV 0.12 at the deployed threshold. AUC 0.76 survives: Wong does not contest the ranking measure, and the compiler correctly leaves it intact. AUC is immune to operating-point failures because it integrates over all thresholds. It cannot detect that 88% of alerts are false positives or that two-thirds of sepsis cases are missed, because those are properties of a specific threshold, not of the ranking. This is the Representation Theorem made concrete: AUC cannot detect the failure mode "alert rate is clinically unsustainable," so a compiler using AUC as its only functional cannot be sharp on that mode. The gap induced is clinical_utility_gap — sensitivity and PPV at the specific operating threshold must be bounded before ALERT_ROLLOUT is reachable.

**Step 2 — distribution_shift_gap.** Stipulate clinical_utility_gap closed. The distribution shift failure bit fires vacuously: no token in the evidence package bounds performance outside Penn Medicine. The profile requires positive evidence of stability; absence of a token is the failure, not a weak signal. This inverts the standard statistical framing. In most contexts, absence of evidence is not evidence of absence. Here it is: the failure bit is set until cleared by a positive token, and no positive token exists. The compiler refuses without needing to observe degradation. Wong confirms post-hoc: AUROC 0.63–0.76 across 7 sites, with Penn Medicine as the ceiling.

**Step 3 — scope_coverage_gap.** Closing distribution_shift requires a multi-site validation token whose field contract specifies representativeness: site count, population description, temporal coverage, similarity criterion to the deployment context. Without this contract, any multi-site data satisfies the gap — including data from sites identical to the training site, which bounds nothing. The Penn Medicine study cannot satisfy this contract by definition. The origin site cannot serve as independent validation of its own distribution. This is a logical impossibility, not an empirical gap that more data could close.

**Steps 4–6.** Closing distribution_shift and scope_coverage does not certify that the operating threshold is clinically appropriate. This forces operating_point_utility_gap: PPV, sensitivity, specificity, and NPV at the deployed threshold with confidence intervals, evaluated against pre-specified acceptance criteria — a separate requirement from aggregate AUC. Broad rollout then requires a monitoring plan before deployment, not after, forcing post_market_monitoring_gap. Monitoring without a response plan is incomplete, forcing rollback_criteria_gap.

Stability check: all six gaps remain open in the Penn Medicine evidence package. No available witness forces a further gap. The taxonomy is stable.

### 9.3 PPV threshold sweep

We fix the permission hierarchy at four levels and sweep the PPV floor $\tau_L \in [0.05, 0.30]$, recording the utility-derived permission, distribution shift status, and compound permission at each threshold. The compound permission is the meet of the two independent axes.

|$\tau_L$|Penn PPV|Utility permission|Dist. shift|Compound|Over-auth?|
|---|---|---|---|---|---|
|0.05|0.12|ALERT_ROLLOUT|OPEN|LIMITED_ROLLOUT|yes|
|0.10|0.12|ALERT_ROLLOUT|OPEN|LIMITED_ROLLOUT|yes|
|0.12|0.12|ALERT_ROLLOUT|OPEN|LIMITED_ROLLOUT|yes|
|0.15–0.30|0.12|LIMITED_ROLLOUT|OPEN|LIMITED_ROLLOUT|yes|

ALERT_ROLLOUT is unreachable at any clinically defensible $\tau_L$. Distribution shift is unresolved regardless of where the utility floor is set — the two gap types are independent axes, and the compound permission is always their meet. Penn Medicine's own PPV (0.12) fails any floor above 0.12, and even below 0.12 the distribution shift bit blocks independently.

### 9.4 Transfer degradation tolerance analysis

The permission hierarchy implies natural sensitivity floors for each level: a permission that licenses broad rollout requires a tighter degradation tolerance than one that licenses controlled single-site deployment. We derive the compiler's natural tolerance intervals from the permission hierarchy alone — not from Wong.

|Level|Sensitivity floor|Max tolerable drop from Penn baseline (0.54)|
|---|---|---|
|ALERT_ROLLOUT|0.50|0.04 pp|
|LIMITED_ROLLOUT|0.30|0.24 pp|

Wong observed a 0.21 pp drop (sensitivity 0.54 → 0.33, 39% relative degradation).

- 0.21 pp exceeds ALERT_ROLLOUT tolerance (0.04 pp). $\times$
- 0.21 pp falls within LIMITED_ROLLOUT tolerance (0.24 pp). $\checkmark$

The compiler's natural tolerance interval, derived from the permission hierarchy without reading Wong, brackets the observed degradation at exactly the right level: too large for broad rollout, consistent with controlled single-site deployment. The implied AUROC range from the sensitivity drop (0.741–0.760) falls within the Wong observed range (0.63–0.76). $\checkmark$

This is the central numerical result of the chosen domain case study, and it is stronger than correspondence alone. The 3GPP audit (§8.7) found that the compiler's natural boundaries matched the thresholds in the standard — a retrospective correspondence. This result is predictive: the compiler's tolerance interval was determined by the permission hierarchy, not by the Wong data, and the Wong data landed inside it four years later.

### 9.5 Formal structure

Clinical rollout is a chosen domain. The permission function is not uniquely determined by the mathematics of the evidence — it reflects institutional risk tolerance operating above what the evidence can derive. The induction loop makes the structure of that choice explicit.

Let $p = \mathrm{ALR}$. Let $F_p^0$ be the base rollout failure set induced by model specification, approximation quality, calibration, provenance, blast radius, authority, and freshness. Let $U$ be the upward-closed set of states where deployed-threshold clinical utility evidence is absent or inadequate. One profile sets $F_p^{\mathrm{without}} = F_p^0$. Another sets $F_p^{\mathrm{with}} = F_p^0 \cup U$. If $U \setminus F_p^0 \neq \varnothing$, there are states that satisfy every base rollout requirement but lack deployed-threshold utility evidence. The first profile permits $\mathrm{ALR}$ there. The second refuses it. Both maps are monotone. They are different licensing maps, and the difference is a semantic policy act.

The same pattern applies to each induced gap: distribution shift, scope coverage, operating-point utility, monitoring, and rollback. Each added gap expands the rollout failure set. The compiler's contribution is that each expansion becomes explicit, mechanical, and auditable. A profile is not a paragraph saying "adequate validation required." It is a structured object with required tokens, field-level contracts, scope rules, and expiry conditions. A token asserting AUC cannot close a gap requiring deployed-threshold PPV. A single-site validation token cannot close a distribution shift gap unless its scope contract permits that use.

### 9.6 FDA 2025 blind audit

We open the FDA 2025 AI Draft Guidance (Docket FDA-2024-D-4488) after completing the induction. We record, for each induced gap, the corresponding FDA requirement and its classification.

|Induced gap|FDA element|Section|Classification|
|---|---|---|---|
|distribution_shift_gap|Real-World Performance Monitoring; intended use population spec|§6/§4|✓ CORRESPONDENCE|
|scope_coverage_gap|Validation dataset diversity; PCCP site representation|§5/Appendix C|✓ CORRESPONDENCE|
|operating_point_utility_gap|Clinical performance metrics at intended operating point|Appendix C|✓ CORRESPONDENCE|
|post_market_monitoring_gap|Post-market surveillance plan|§6/PMA|✓ CORRESPONDENCE|
|rollback_criteria_gap|Algorithm change protocol; performance degradation response|§7/PCCP|✓ CORRESPONDENCE|
|clinical_utility_gap|Clinical utility (Appendix C — partial)|Appendix C|↑ COMPILER_STRICT|
|—|Software cybersecurity requirements|§8|↓ COMPILER_PERMISSIVE|
|—|Labeling / Instructions for Use|§9|↓ COMPILER_PERMISSIVE|

5 CORRESPONDENCE · 1 COMPILER_STRICT · 2 COMPILER_PERMISSIVE.

The five correspondences establish that the gaps induced from a single over-authorization witness correspond exactly to the core deployment requirements of the current FDA AI guidance, without consulting it. The two COMPILER_PERMISSIVE items — cybersecurity and labeling — were not reachable from deployment failure evidence. No available witness forced them. The compiler does not discover what the evidence does not reveal.

The COMPILER_STRICT finding on clinical_utility_gap is the more interesting result. FDA's Appendix C names operating-point metrics and confidence intervals, but does not separately articulate the concept of a PPV floor calibrated to the blast radius of the clinical action: the requirement that PPV must meet a pre-specified acceptance criterion relative to the scope of downstream harm the alert can trigger. An alert system flagging 20% of inpatients with PPV 0.12 and one flagging 1% of ICU patients with the same PPV have identical metrics but radically different clinical profiles. The compiler's gap concept encodes this distinction; the current regulation does not fully articulate it. The compiler recovered a policy structure more precise than the existing regulatory text.

### 9.7 Structural symmetry

The derived domain result (§8) and the chosen domain result are structurally symmetric.

In both cases, the compiler's input is the evidence structure. The boundary is wherever the evidence runs out. In a derived domain, the physics _is_ the evidence structure: the BER/BLER relationship is a mathematical object, and the compiler finds the thresholds where the physics forces natural gaps. In a chosen domain, the evidence structure determines what the data can certify, and policy fills in above where the evidence runs out. The compiler finds the boundary between what the evidence determines and what institutional choice must supply.

The 3GPP audit found that the compiler's natural boundaries, derived without reading the standard, correspond to the thresholds that three decades of standardization work arrived at for the same physical quantities. The Epic audit found that the compiler's natural tolerance interval, derived without reading the regulation, brackets the degradation figure an independent research team observed four years later. In both cases, the boundary existed in the structure of the evidence before anyone wrote it down.

**Derived domains:** the compiler finds where physics forces the boundary.

**Chosen domains:** the compiler finds where policy operates above physics — and where, under the best available evidence, the policy was operating above what the physics could yet certify.

## 10. Implementation and Library

The implemented judgment form is

\[
\Gamma \vdash z : p \text{ until } \varepsilon.
\]

The proof context \(\Gamma\) contains membership, claim, candidate, context, scope, induced gaps, taxonomy version, profile version, proof tokens, token provenance, detail-contract registry version, expiry, allowed uses, disallowed uses, derivation, authority, runtime context, and audit metadata.

The compiler evaluates a judgment in the following order.

1. Check membership in the claim class; otherwise emit out-of-class.
2. Induce the claim and gap set under a fixed taxonomy version.
3. Check expiry.
4. Validate each proof token against the registry, detail contract, liveness rule, provenance rule, and scope rule.
5. Close only those gaps supported by valid live scoped witnesses.
6. Apply structural downgrades: provenance mismatch, allowed-use conflict, empty scope, failed negative controls, invalid derivation, runtime failure.
7. Apply authority ceilings, escalation requirements, rollback controls, and runtime constraints.
8. Search permissions strongest-to-weakest and return the first satisfiable level.
9. Emit the judgment with blocking reasons for every denied stronger permission.

The core invariant is simple: no approximation may be used as stronger permission than its evidence, scope, provenance, expiry, authority, runtime context, and policy profile jointly support.

The repository is:

[https://github.com/adis-zr/noethers-turnstile](https://github.com/adis-zr/noethers-turnstile)

The library contains the compiler, profile registry, gap taxonomy, detail-contract registry, examples, and benchmark machinery. A domain adopter supplies a claim class, a profile, and certifiers for the relevant gap types. The compiler handles the permission search, monotone downgrades, envelope emission, runtime revalidation, and audit trail.

The implementation matters because the paper's claim is not merely philosophical. The framework is meant to be used. A profile is not a paragraph saying “adequate validation required.” It is a structured object with required tokens, field-level contracts, scope rules, expiry rules, and authority ceilings. A token asserting AUC cannot close a gap requiring deployed-threshold PPV. A single-site validation token cannot close a multi-site distribution-shift gap unless its scope permits that use. Expired evidence cannot remain live. Composition cannot upgrade weak evidence, because composed permission is the meet of component permissions.

The benchmark suites exercise three classes of behavior: structural algebra and adversarial domain tests; medical prospective cases over real clinical data; and retrospective case-library audits of documented harmful deployments. Their purpose is not to prove that every domain profile is correct. It is to test the compiler discipline: invalid tokens do not close gaps, provenance cannot be laundered, profile changes require recompilation, runtime downgrades cannot be hidden, and unsupported escalation is refused.

### 10.1 Runtime Performance

#### Theoretical bound

Theorem 4 establishes that sharp compilation and expiry checking are both decidable in time linear in the number of failure modes and permission levels. Concretely: the compiler receives a failure vector of $m$ bits and scans from the strongest permission $p_n$ downward, checking at each level whether the failure vector contains an active obstruction. The scan terminates at the first unobstructed level. The procedure runs in $O(mn)$ steps, where $m$ is the number of failure bits and $n$ is the number of permission levels.

Expiry checking is the same scan applied to the destination state. By the latch-false property (Remark 2), a judgment that expires does not require re-evaluation — liveness is a running conjunction that latches false on the first expired state and is not recomputed thereafter.

Both bounds are over the profile complexity $(m, n)$, not over the size of the underlying problem. The compiler is deliberately local: it evaluates one judgment at a time against one evidence context. Its cost is decoupled from whatever produced $\Gamma$.

#### Empirical validation

We validate the theoretical bounds through a dedicated benchmark suite committed to the repository, independent of the case study problems. The suite measures four scaling claims using synthetic constructions, plus four degenerate cases that test boundary conditions the case studies do not reach. All benchmarks are reproducible via a single entry point (`benchmarks/run_all.sh`).

**Claim 1 — Compiler cost is $O(mn)$ in profile complexity.**

We fix the underlying problem and vary $m \in [1, 1000]$ failure bits and $n \in [2, 20]$ permission levels independently, measuring compiler time only. The measured slope is $0.49$ ns per $(m \times n)$ unit. The relationship is clearly linear at large $m$; Python dispatch overhead dominates at small $m$, producing a Pearson $r = 0.55$ on the raw data that increases to $r > 0.99$ when the constant overhead term is subtracted. The constant factor is small: at $m = 100$, $n = 10$ (a generous real-world profile), the compiler runs in under $1\ \mu$s.

**Claim 2 — Compiler cost is independent of problem size.**

We fix $m = 10$ failure bits and $n = 4$ permission levels (the profile used in the case studies) and vary problem size from $n_\text{vars} = 9$ to $n_\text{vars} = 10{,}000$ using randomly generated factor graphs. We instrument three timing boundaries separately: inference, $\Gamma$ assembly (computing TV, Bethe energy, convergence flag from inference output), and compiler (reading the failure vector, emitting a permission).

**Table 5.** Absolute runtimes and compiler overhead fraction across problem sizes. Inference time grows by five orders of magnitude; compiler time stays flat.

| $n_\text{vars}$ | Inference time | $\Gamma$ assembly | Compiler time | Overhead fraction |
|----------------|---------------|-------------------|---------------|-------------------|
| 9 | 748 µs | 12 µs | 3.7 µs | $4.9 \times 10^{-3}$ |
| 100 | 84 ms | 31 µs | 5.2 µs | $6.2 \times 10^{-5}$ |
| 1,000 | 8.4 s | 89 µs | 9.1 µs | $1.1 \times 10^{-6}$ |
| 10,000 | 92.6 s | 210 µs | 13.6 µs | $1.5 \times 10^{-7}$ |

Inference scales by a factor of $124{,}000\times$ across this range. Compiler time grows from $3.7$ to $13.6\ \mu$s — a factor of $3.7\times$, attributable to the larger failure vectors produced by larger graphs, and well within the $O(mn)$ prediction with $m$ fixed. The overhead fraction drops five orders of magnitude: at $n_\text{vars} = 10{,}000$, the compiler consumes $1.5 \times 10^{-7}$ of total runtime. The compiler becomes proportionally cheaper as the underlying problem becomes harder.

**Claim 3 — Average scan depth is well below worst case.**

We fix $m = 10$, $n = 4$ and vary failure vector density $d \in [0, 1]$, where density is the fraction of failure bits set to 1. At $d = 0$ (all bits clear) the compiler terminates at the first level — scan depth 1. At $d = 1$ (all bits failed) it scans all levels — scan depth $n$. At $d = 0.30$, the mean scan depth is $3.6$ out of a maximum of $4$, with the REFUSE rate growing steeply above $d = 0.7$. Average-case scan depth is substantially below worst case across the full density range. For typical real-world profiles where most failure modes are resolved, the expected scan terminates early.

**Claim 4 — Expiry checking adds no asymptotic cost.**

We generate state transition sequences of varying length and measure bits evaluated per step for both forward compilation and expiry checking. Forward compilation evaluates $36.1$ bits per step (flat across all sequence lengths). Expiry checking evaluates $3.1$ bits per step (flat), reflecting that only the bits relevant to the issued permission are re-evaluated at each transition. The latch-false property reduces cumulative expiry cost below the worst case for sequences containing early expired judgments: once a judgment lapses, no further evaluation occurs for that judgment on that path.

#### Degenerate cases

Four boundary constructions verify soundness and performance at the extremes of the parameter space.

**Degenerate A ($m = 1$, $n$ varied).** With a single failure bit, the compiler reduces to a threshold scan over $n$ permission levels. Measured time is $290n + 927$ ns, confirming $O(n)$ with Pearson $r = 1.0000$. The constant term is Python dispatch overhead.

**Degenerate B ($m$ varied, $n = 2$).** With two permission levels (PERMIT / REFUSE), the compiler evaluates all $m$ bits against a single threshold. Measured time is flat at approximately $1{,}700$ ns for $m \in [1, 1000]$ — the constant overhead of the dispatch dominates and the linear term in $m$ is below the noise floor at $n = 2$. REFUSE rate approaches 1 as $m$ grows, as expected.

**Degenerate C (contradictory failure vectors).** Failure vectors with conflicting signals — some bits indicating adequate quality, others indicating inadequate quality for the same permission level — are handled correctly. The compiler emits the highest permission whose full obstruction condition is not triggered. Soundness verified across all generated contradictory configurations.

**Degenerate D (empty evidence context, $\Gamma = \varnothing$).** With no evidence, the failure vector is vacuously clear. The compiler emits the weakest non-trivially licensed permission (EXPLORE in the four-level chain). Scan depth is 1 for all $(m, n)$ combinations. Soundness verified.

#### What the benchmark establishes

The benchmark suite establishes three things that the case studies alone could not.

First, the $O(mn)$ bound is not a theoretical abstraction — it is measured at $0.49$ ns per unit, with a concrete constant that practitioners can use to estimate compiler cost for any profile.

Second, the decoupling of compiler cost from problem size is not a property of the specific problems chosen for the case studies. It holds across randomly generated graphs spanning five orders of magnitude in inference runtime. A practitioner deploying the compiler on a problem ten times larger than any tested here can extrapolate the overhead fraction with confidence.

Third, the degenerate cases confirm that no pathological input structure defeats the compiler's soundness or produces unexpected runtime behavior. Contradictory failure vectors, empty contexts, and extreme $(m, n)$ configurations all produce correct, fast outputs. The compiler has no special cases.

**[BenchmarkSuite]** Benchmark suite, synthetic constructions, and figure generation scripts. `benchmarks/` directory of the accompanying repository.

---

## References

Abadi, M., Burrows, M., Lampson, B., and Plotkin, G. 1993. A Calculus for Access Control in Distributed Systems. *ACM Transactions on Programming Languages and Systems.*

Abdulla, P., Čerāns, K., Jonsson, B., and Tsay, Y.-K. 1996. General Decidability Theorems for Infinite-State Systems. *LICS.*

Appel, A. W. and Felten, E. W. 1999. Proof-Carrying Authentication. *CCS.*

Basu, S., Pollack, R., and Roy, M.-F. 2006. *Algorithms in Real Algebraic Geometry.* Springer.

Bochnak, J., Coste, M., and Roy, M.-F. 1998. *Real Algebraic Geometry.* Springer.

Dickson, L. E. 1913. Finiteness of the Odd Perfect and Primitive Abundant Numbers with n Distinct Prime Factors. *American Journal of Mathematics.*

FDA. 2025. Artificial Intelligence-Enabled Device Software Functions — Draft Guidance. Docket FDA-2024-D-4488.

Finkel, A. and Schnoebelen, P. 2001. Well-Structured Transition Systems Everywhere! *Theoretical Computer Science.*

Gebru, T. et al. 2021. Datasheets for Datasets. *Communications of the ACM.*

Higman, G. 1952. Ordering by Divisibility in Abstract Algebras. *Proceedings of the London Mathematical Society.*

Kruskal, J. B. 1960. Well-Quasi-Ordering, the Tree Theorem, and Vazsonyi's Conjecture. *Transactions of the American Mathematical Society.*

Mitchell, M. et al. 2019. Model Cards for Model Reporting. *FAccT.*

Myers, A. C. 1999. JFlow: Practical Mostly-Static Information Flow Control. *POPL.*

Necula, G. C. 1997. Proof-Carrying Code. *POPL.*

NHS Royal College of Radiologists. 2024. *AI Deployment Fundamentals for Medical Imaging.*

Obermeyer, Z. et al. 2019. Dissecting Racial Bias in an Algorithm Used to Manage the Health of Populations. *Science.*

Schneider, F. B. 2000. Enforceable Security Policies. *ACM Transactions on Information and System Security.*

Tarski, A. 1951. *A Decision Method for Elementary Algebra and Geometry.* University of California Press.

van den Dries, L. 1998. *Tame Topology and O-minimal Structures.* Cambridge University Press.

Wong, A. et al. 2021. External Validation of a Widely Implemented Proprietary Sepsis Prediction Model in Hospitalized Patients. *JAMA Internal Medicine.*

**[Benedetto1996]** Benedetto, S. and Montorsi, G. (1996). Unveiling turbo codes: Some results on parallel concatenated coding schemes. _IEEE Transactions on Information Theory_, 42(2):409–428.

**[Berrou1993]** Berrou, C., Glavieux, A., and Thitimajshima, P. (1993). Near Shannon limit error-correcting coding and decoding: Turbo codes. In _Proceedings of ICC 1993_, pages 1064–1070.

**[IhlerUAIData]** Ihler, A. UAI model files and solutions. `http://sli.ics.uci.edu/~ihler/uai-data/`. Accessed 2025.

**[ITU_B5G]** ITU-T/3GPP (2022). Beyond 5G URLLC evolution: New service modes and practical considerations. _ITU Journal on Future and Evolving Technologies_, 3(3).

**[McEliece1998]** McEliece, R. J., MacKay, D. J. C., and Cheng, J.-F. (1998). Turbo decoding as an instance of Pearl's belief propagation algorithm. _IEEE Journal on Selected Areas in Communications_, 16(2):140–152.

**[Mooij2010]** Mooij, J. M. (2010). libDAI: A free and open source C++ library for discrete approximate inference in graphical models. _Journal of Machine Learning Research_, 11:2169–2173.

**[Murphy1999]** Murphy, K. P., Weiss, Y., and Jordan, M. I. (1999). Loopy belief propagation for approximate inference: An empirical study. In _Proceedings of the Fifteenth Conference on Uncertainty in Artificial Intelligence (UAI 1999)_, pages 467–475.

**[Onsager1944]** Onsager, L. (1944). Crystal statistics I: A two-dimensional model with an order-disorder transition. _Physical Review_, 65(3–4):117–149.

**[Scutari2010]** Scutari, M., Denis, J.-B., and Proissl, M. (2021). Bayesian network repository. `https://www.bnlearn.com/bnrepository/`.

**[UAI2022Benchmarks]** UAI 2022 Inference Competition. Benchmark instances. `https://uaicompetition.github.io/uci-2022/results/benchmarks/`. Accessed 2025.

**[Yedidia2005]** Yedidia, J. S., Freeman, W. T., and Weiss, Y. (2005). Constructing free-energy approximations and generalized belief propagation algorithms. _IEEE Transactions on Information Theory_, 51(7):2282–2312.

**[3GPP_Rel16_URLLC]** 3GPP (2020). Release 16: Support of ultra-reliable and low latency communication. Technical report, 3rd Generation Partnership Project.

**[3GPP_TR38913]** 3GPP (2018). TR 38.913: Study on scenarios and requirements for next generation access technologies. Technical report, 3rd Generation Partnership Project.

**[3GPP_TS38133]** 3GPP (2018). TS 38.133: NR; Requirements for support of radio resource management. Technical specification, 3rd Generation Partnership Project.

**[5GAmericasURLLC]** 5G Americas (2019). Wireless technology evolution towards 5G: 3GPP release 13 to release 15 and beyond. White paper.
