# Admissibility Judgement for Approximate Consequential Systems

## Abstract

TBD

---
## 1. Introduction

There has been a seismic shift in software engineering. Someone describes a feature in natural language, then an agent writes the ticket, another agent writes the spec, another writes the code, writes tests, and the deployment manifest. A final agent reviews everything and ships it. 

There is no human in the loop. At no point did anyone check whether the evidence was sufficient for the actions being taken.

Once you notice this gap, you see it everywhere. A sepsis score adequate for flagging a patient gets used to trigger an automatic order set. A retrieval result adequate for surfacing a document gets used to ground a legal summary. In each case, evidence valid for one purpose is silently promoted into authorization for a stronger one. Call this **evidence overextension**.

Formal-methods and security systems solved an analogous problem decades ago by mechanically determining whether the action has the proof, authority, or capability the policy requires (Abadi et al., 1993; Necula, 1997; Appel and Felten, 1999; Myers, 1999; Schneider, 2000).

This paper builds on their work. Weak evidence should not be discarded, but it should receive only a weak license. Stronger actions should require stronger, scoped, live, provenance-bound evidence.

To that end, the paper introduces a permission-valued **admissibility judgment**, enforced operationally by an accompanying compiler, written

$$
\Gamma \vdash z : p \ \text{until}\ \varepsilon,
$$

which reads: under evidentiary context $\Gamma$, artifact or output $z$ supports permission $p$ until expiry condition $\varepsilon$.

The judgment asks what operational permission follows from the available evidence: diagnostic display, human review, experimentation, limited rollout, automatic action, or no action at all.

The compiler emits the strongest permission actually supported and prevents that permission from being silently upgraded as the artifact moves through a workflow.

---

## 2. The hard part is still hard

The compiler does not choose objectives, set thresholds, or invent evidence standards. A domain expert must still decide which metrics matter, which trade-offs are acceptable, and what evidence is sufficient for each permission level. That judgment is not automated away.

But the framework forces the policy to be written down in compiler-processable form, and in doing so, it reveals whether the policy actually exists.

Consider distribution shift in clinical AI. Before a judgment can be made, the compiler requires: institution identifier, cohort date range, cohort size, domain classifier AUC comparing training to deployment population, and per-feature drift statistics for the top predictive features.

Evidence without an institution identifier is structurally invalid. There is no way to audit whether the right population was tested. Most deployed clinical AI systems have never produced this evidence. Not because it is unavailable, but because nothing has ever demanded it in this form.

The framework does not make it easier to state a policy, but once stated, the compiler enforces it.

---

## 3. Approximate consequential systems and evidence overextension

A system is **approximate consequential** when four conditions hold.
1. The ideal output is unavailable at decision time.
2. The system acts on an approximation of that ideal output.
3. A downstream workflow treats the approximate output as permission, authority, or control-relevant evidence.
4. The validity of the output depends on context that can change.

All four conditions are necessary.

The first two conditions distinguish approximate systems from exact ones. Paxos is highly consequential, but its correctness condition is exact.

The third condition is what makes the system consequential. An output becomes dangerous when another system treats it as a license to act. The same evidence may be safe for display, useful for review, and insufficient for automatic action.

The fourth condition is what makes the framework useful for real-time systems. Populations drift, repositories update, policies expire. Admissibility must therefore come with an expiry: admissible until state no longer supports it.

---

## 4. The Framework, Defined Through Epic

### 4.1 The admissibility judgement

The central object of the framework is:

$$
\Gamma \vdash z : p \ \text{until}\ \varepsilon
$$

This reads: under evidentiary context $\Gamma$, candidate $z$ is admissible at permission $p$ until expiry condition $\varepsilon$.

Applied to the Epic deployment, $z$ is the sepsis alert system. The question the judgement answers is: what permission does Epic's evidence actually support?

The permission chain runs from most restrictive to least:

```
OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA < REV < AEX < ALR < AAA
```

| Symbol | Meaning |
|--------|---------|
| `OOC` | Out of class — the framework does not govern this input |
| `EXP` | Expired — a token or context TTL has elapsed |
| `REF` | Refused — a credential was actively rejected (wrong provenance, revoked, invalid) |
| `UNS` | Unsupported — profiles exist but no evidence satisfies any of them |
| `ETA` | Authority ceiling exceeded — evidence supports stronger permission than the actor holds |
| `ESC` | Escalation required — the decision is outside the actor's authorized scope |
| `ROL` | Rollback condition met — a live control obligation blocks positive permission |
| `DIA` | Diagnostic display only — the in-class floor; all gaps open, no positive evidence |
| `REV` | Human review recommended — evidence supports reversible action with oversight |
| `AEX` | Approve experiment — evidence supports controlled deployment study |
| `ALR` | Approve limited rollout — evidence supports operational use with logging |
| `AAA` | Approve automatic action — unrestricted |

The lower half of the chain — OOC through ROL — are not failure codes. They are live compiler outputs. REF fires when a token with the correct provenance location carries wrong provenance data: a deliberate credential substitution, not mere absence. UNS fires when profiles exist but no evidence satisfies any of them: the claim class is recognized but the evidence package is empty. ETA fires when the evidence supports a permission the actor is not authorized to hold: the ceiling is a structural delegation limit, independent of evidentiary strength.

Epic was deployed at ALR. The framework's question is whether ALR was supported by the evidence. It was not.

### 4.2 The proof context and what it demands

For the judgement to be meaningful, the compiler needs a proof context $\Gamma$ that captures everything relevant to the authorization question:

$$
\Gamma = \bigl(\mathsf{membership},\ \mathsf{claim},\ \mathsf{candidate},\ \mathsf{context},\ \mathsf{scope},\ \mathsf{claim\_gaps},\ \mathsf{gap\_taxonomy\_version},\ \mathsf{gap\_profile\_version},\ \mathsf{proof\_tokens},\ \mathsf{proof\_token\_provenance},\ \mathsf{detail\_contract\_registry\_version},\ \mathsf{expiry},\ \mathsf{allowed\_use},\ \mathsf{disallowed\_use},\ \mathsf{derivation},\ \mathsf{authority},\ \mathsf{runtime\_context},\ \mathsf{audit}\bigr)
$$

The fields divide into five roles.

First, they fix the object of judgement. `membership` determines whether the candidate belongs to the class governed by the framework. `claim`, `candidate`, and `context` identify what is being asserted, what artifact or action is under consideration, and the setting in which the assertion holds. `scope` limits where the resulting judgement may be used. Applied to Epic: membership is in-class for clinical alerting systems; the candidate is the sepsis alert system as deployed; the context is the specific institution, patient population, and deployment configuration.

Second, they fix the proof obligations. `claim_gaps` records which proof obligations are induced for this claim. `gap_taxonomy_version` fixes the vocabulary of possible obligations. `gap_profile_version` fixes which obligations must be satisfied at each permission level. `detail_contract_registry_version` fixes the schemas and semantic checks that proof tokens must satisfy. These three version fields together mean the meaning of a judgement is immutable: later revisions to the taxonomy or profile cannot retroactively change what the evidence supported at the time of issue.

Third, they record the evidence. `proof_tokens` are typed witnesses offered to bound or close gaps. `proof_token_provenance` binds each token to the exact tuple it is allowed to support: token, gap, claim, candidate, and context. A token does not count merely because it has a reassuring name or reports a favorable result. It counts only if it is live, contract-conformant, scoped correctly, and provenanced to the specific obligation being discharged.

Fourth, they impose scope and temporal constraints. `expiry` states when the judgement ceases to be live. `allowed_use` and `disallowed_use` restrict the downstream uses the judgement covers. `authority` imposes ceilings or escalation requirements that are independent of evidentiary strength. `runtime_context` supplies the live facts needed to evaluate expiry, registry status, revocation, and rollback conditions. `derivation` records how the claim and candidate were produced, so that invalid or untrusted transformations cannot silently create authority: a derived output carries at most the weakest permission of its inputs.

Finally, `audit` explains the result. It records which permissions were denied, which gaps blocked them, which tokens were rejected, which runtime checks failed, which authority ceilings applied, and which expiry or scope rules narrowed the outcome. The audit field is what makes later accountability possible. An informal deployment decision cannot be retrospectively interrogated; a compiled judgement always can.

The compiler's soundness claims are relative to $\Gamma$. If $\Gamma$ contains the required gaps, uses the intended profile, includes only valid tokens, binds those tokens by exact provenance, and supplies the required runtime facts, then the compiler emits the greatest permission supported by that context and no more. If a load-bearing obligation is missing from the taxonomy, omitted from the profile, or assigned an overly permissive detail contract, the compiler may authorize too much. But that failure is visible at the domain-bridge boundary rather than hidden inside an informal deployment decision.

### 4.3 Gaps — what Epic's deployment failed to answer

A **gap** is a proof obligation. It names a way in which the current evidence may be insufficient for the requested use.

$$
g = (\mathsf{gap\_id},\ \mathsf{gap\_type},\ \mathsf{status},\ \mathsf{metadata})
$$

where $\mathsf{status} \in \{\mathsf{OPEN},\ \mathsf{BOUNDED},\ \mathsf{CLOSED}\}$. OPEN means no admissible evidence has been supplied. BOUNDED means evidence limits the risk without fully discharging it. CLOSED means evidence discharges the obligation for the relevant scope and use.

The framework introduces gaps not as abstract constructs but as precise names for questions that must be answered before each permission level. Applied to Epic, the question is: what did Epic's deployment fail to answer?

The answer is specific. Epic presented evidence for several obligations. AUC = 0.76 bounded `approximation_quality_gap`: the model is not random. Model specification was documented: the prediction target was sepsis onset. Calibration and blast radius were characterized. What Epic did not present — what was never required — was:

**`clinical_utility_gap`**: Is PPV/sensitivity sufficient at the deployed threshold for the intended action class? This is not a variation on AUC. It is a different question entirely. A model can have AUC = 0.90 and PPV = 0.05 at the threshold where it fires alerts, if it is set to fire rarely. PPV = 0.12 at Epic's deployed threshold means that 88% of alerts are false. The clinical utility gap was not defined in the implicit profile governing Epic's deployment. It was not asked. No certifier was ever required to answer it.

**`distribution_shift_gap`**: Does the model's validation hold on the deployment population? Epic was validated on data from the developing institution's patient population. Deployed at 100+ hospitals across different geographies, demographics, and care patterns, it was used on populations it had never been validated against. The distribution shift gap names this question. It requires: institution identifier, cohort date range, cohort size, domain classifier AUC comparing training to deployment population, per-feature drift statistics for top predictive features. Evidence without an institution identifier is structurally invalid for this obligation — there is no way to audit whether the right population was tested. Epic's deployment had no such evidence. The question was never posed.

The forcing function argument: most deployed clinical AI systems have never produced this evidence. Not because it is unavailable, but because nothing has ever demanded it in this form. The compiler is that demand. Before a judgement can be made, the proof context must supply the tokens. Before a token can be issued, the certifier must have produced the evidence.

### 4.4 The profile — what a policy that required these answers would look like

A **profile** specifies which gaps are required at which permission levels for a given claim class.

$$
\mathsf{Req}_{\Phi_v}(\kappa, h, p) \in \{\mathsf{OPEN\_ALLOWED},\ \mathsf{BOUNDED\_REQUIRED},\ \mathsf{CLOSED\_REQUIRED}\}
$$

A permission is satisfiable only when every induced gap reaches the status demanded by the versioned profile. The compiler does not ask whether evidence is persuasive in ordinary language. It asks whether each obligation has been discharged to the level required by the relevant taxonomy, profile, and detail contract registry.

The v1 profile — the one implicitly in use at Epic's deployment — required at ALR:

```
approximation_quality_gap:   BOUNDED_REQUIRED
model_specification_gap:     BOUNDED_REQUIRED
calibration_gap:             BOUNDED_REQUIRED
blast_radius_gap:            BOUNDED_REQUIRED
freshness_gap:               BOUNDED_REQUIRED
```

Under this profile, Epic compiles to ALR. All required gaps are bounded. The profile never asks about clinical utility or distribution shift. It cannot block what it does not require.

The v2 profile adds two requirements:

```
clinical_utility_gap:        BOUNDED_REQUIRED
distribution_shift_gap:      BOUNDED_REQUIRED
```

Under v2, Epic compiles to AEX. PPV = 0.12 fails the `clinical_utility_token` detail contract's floor of 0.15. The token is marked invalid. The gap stays open. The descending permission search reaches ALR, finds `clinical_utility_gap` OPEN with BOUNDED_REQUIRED, and fails. It continues down to AEX. Epic may be studied in a controlled deployment; it may not be operationally rolled out.

This is the correction. Not a different model — the same evidence. A different profile.

### 4.5 What the proof context prevents

The proof context prevents evidence overextension. The canonical forms:

**Evidence reuse across contexts.** A clinical utility validation conducted for one institution cannot be submitted as evidence for a deployment at a different institution. The `proof_token_provenance` field binds each token to the exact `(claim, candidate, context, allowed_use)` tuple it was issued against. A provenance hash mismatch means the token is rejected. Epic's validation at the developing institution is not evidence for Epic's deployment at 100 other hospitals.

**Token type laundering.** A freshness certificate cannot close a clinical utility gap. Tokens must satisfy registered detail contracts that specify their schema, semantic checks, artifact dependencies, scope rules, and expiry rules. Token type is a metadata field for human auditors. The compiler enforces the detail contract, not the name. A clinical utility token whose PPV field reads 0.12 fails the semantic check `ppv >= min_ppv` and is marked invalid before it reaches gap evaluation.

**Expiry.** A validation study conducted three years before deployment, on a patient population that has since shifted, is not current evidence. The expiry condition $\varepsilon$ states when the judgement ceases to be live. The domain expert defines what makes evidence expire; the compiler enforces it. This is the hardest and most critical component of the framework for real-time systems. Evidence is temporal. The framework treats it as such.

In the reference implementation, the expiry is not advisory. The `LiveJudgment` type is parameterized by the context lifetime. Reading the permission through `LiveJudgment::permission()` re-evaluates the expiry condition at read time. The type system prevents reading a stale judgement: it is not possible to hold a reference to the permission value past the expiry boundary without invoking the live check. The $\varepsilon$ in $\Gamma \vdash z : p \ \text{until}\ \varepsilon$ is enforced structurally, not contractually.

**Separation of requested from supported permission.** The caller may request ALR. The compiler ignores that request as evidence. It emits the greatest permission supported by the proof context. A request for rollout does not count as rollout evidence.

---

## 5. The Gap Taxonomy Is Not Arbitrary

The Epic case raises an immediate question: is `clinical_utility_gap` a principled construct, or is it a name the framework designer chose? Could a different designer, looking at the same failure, have arrived at different gaps and reached different conclusions?

The answer to this question matters because the framework's authority depends on it. If the taxonomy is arbitrary, then the framework is a sophisticated way of encoding the designer's prior opinions. If the taxonomy is determined by the domain's failure structure, then the framework discovers something real.

This section answers the question in three steps.

### 5.1 The representation theorem

For a claim class $\kappa$, the **ideal licensing map** is:

$$
\lambda_\kappa : \Omega_\kappa \to P
$$

where $\Omega_\kappa$ is the action-state space — every fact relevant to the soundness of action under class $\kappa$ — and $P$ is the permission chain. $\lambda_\kappa(\omega)$ is the strongest permission that would be sound at state $\omega$ if all ideal facts were known.

For each permission threshold $p$, the failure set is:

$$
F_p = \{\omega \in \Omega_\kappa : \lambda_\kappa(\omega) < p\}
$$

This is the set of states where permission $p$ is unsound. The family $\{F_p\}$ is the mathematical object behind the word "taxonomy." It names exactly where each permission becomes unsound.

The representation theorem (proved in the companion paper) establishes the equivalence of three conditions:

1. The threshold failure sets $F_p$ are finitely generated by certifier-observable obstruction predicates.
2. The ideal licensing map $\lambda_\kappa$ factors through a finite monotone certifier-observable quotient.
3. There exists a bounded, monotone, threshold-complete compiler for $\kappa$.

The theorem says: the taxonomy is not chosen. It is the finite monotone observable shadow of the domain's ideal licensing structure. The compiler works sharply for a domain exactly when the domain's failure sets admit this kind of finite presentation. A taxonomy entry that does not correspond to a real failure mode is not a ground requirement — it is padding, and a grounded profile will not contain it.

Applied to Epic: `clinical_utility_gap` is not a naming choice. It names the upward-closed failure set in the clinical alert action-state space consisting of all states where PPV at the deployed threshold is below the level required for the action class. That set exists whether or not anyone names it. The compiler's job is to observe it.

### 5.2 Grounded profiles do not silently authorize unmitigated failure modes

A gap type $h$ is **domain-grounded** for class $\kappa$ when there exists a named, domain-recognizable failure mode $F(h, \kappa)$ such that:

$$
\mathsf{Eff}_\Gamma(h) = \mathsf{OPEN} \implies F(h, \kappa) \text{ is an unmitigated risk for action authority } p
$$

**Theorem N.** Let $\Phi$ be a grounded profile for class $\kappa$. Let $\Gamma$ be any in-class proof context. Let $h$ be any gap type such that $F(h, \kappa)$ is a named failure mode and $\mathsf{Eff}_\Gamma(h) = \mathsf{OPEN}$. Then:

$$
\mathsf{Compile}(\Gamma, \Phi) < p
$$

for every permission level $p$ at which $\Phi(\kappa, h, p) \geq \mathsf{BOUNDED\_REQUIRED}$.

A grounded profile cannot silently grant action authority when a known failure mode is unmitigated. The only path to strong permission with an open required gap is a gap-closing token — a domain claim, auditable, versioned, subject to its own certifier obligations.

The profile v1 → v2 transition for Epic satisfies the surgical property. Adding `clinical_utility_gap` as BOUNDED_REQUIRED at ALR blocks exactly the deployments where clinical utility evidence is absent. It does not block deployments that have a valid clinical utility token. CHARTwatch (Tonekaboni et al. 2022, Toronto General Hospital), deployed prospectively with PPV = 0.40, sensitivity = 0.77, passes v2 at ALR. The profile does not block well-evidenced systems; it blocks the failure mode it was designed to catch.

### 5.3 The induction loop and regulatory convergence

The third step removes the last ambiguity: are the gaps that a designer names looking at Epic the same gaps an independent observer would arrive at?

The **clean witness theorem** establishes that the induction loop — starting from an empty taxonomy, presented only with failure cases and an over-authorization signal — converges on the unique minimal sufficient taxonomy. The loop induces a gap when the compiler over-authorizes on a case where that gap is the last remaining unresolved proof obligation. Because the signal is over-authorization rather than correlation, the loop cannot induce spurious gaps: once the profile is complete, the signal stops firing, regardless of what other correlates are present in the cases.

The induction is run on Epic and five comparable AI deployment failures. Starting from v0 — a skeleton profile requiring only approximation quality and freshness — the loop induces, in order:

1. `clinical_utility_gap` — from the Epic sepsis model (Wong et al. 2021)
2. `model_specification_gap` — from the Optum racial bias study (Obermeyer et al. 2019)
3. `distribution_shift_gap` — from PredPol predictive policing feedback effects
4. `individual_population_gap` — from COMPAS recidivism scoring
5. `blast_radius_gap` — from IBM Watson Oncology
6. `authority_gap` — from the Dutch childcare benefit algorithm

This converged profile is then audited against FDA Draft Guidance (January 2025, docket FDA-2024-D-4488) and NHS RCR "AI Deployment Fundamentals for Medical Imaging" (November 2024) — two regulatory frameworks developed independently, by different institutions, on different continents, over several years. The audit finds 12/12 FDA and NHS requirements covered by the six induced gaps.

There is a further check. After the induction converges, writing the profile in compiler-processable form — specifying concrete thresholds, scope rules, and expiry conditions for each gap — forces questions that the prose version of the six gaps does not answer. Two obligations that the NHS treats as minimum standards emerge only at this stage: shadow-mode testing on the local population before go-live (NHS §4.21–4.22), and an ongoing post-market monitoring plan required before deployment (NHS §2.13, FDA §XI for PMA devices). These are not gaps visible in the failure cases that drove induction. They are visible only when the profile is matched against regulatory text.

The v3 profile adds them:

```
shadow_mode_validation_gap:  BOUNDED_REQUIRED at ALR
post_market_monitoring_gap:  BOUNDED_REQUIRED at ALR
```

The V1→V2→V3 progression illustrates a compound claim. First, the induction result: the compiler and the regulators converge on the same taxonomy because they are responding to the same failure structure. Second, the compiler-processable policy claim: writing a profile in compiler-processable form reveals incompleteness that prose governance cannot detect, because the compiler demands answers in a form that prose does not require.

---

## 6. The Framework Running on Epic

This section closes the loop. The paper opened by asking what a framework that prevented Epic would look like. This section shows that framework running, on Epic's own published numbers.

### 6.1 Evidence available at deployment time

The evidence Epic presented, reconstructed from public sources:

| Gap | Status at deployment | Evidence |
|-----|---------------------|----------|
| `approximation_quality_gap` | BOUNDED | AUC = 0.76, internal validation |
| `model_specification_gap` | BOUNDED | Sepsis onset documented as prediction target |
| `calibration_gap` | BOUNDED | Calibration reported in internal validation |
| `blast_radius_gap` | BOUNDED | Alert-only; no automatic order entry at deployment |
| `freshness_gap` | BOUNDED | Computed from near-real-time EHR data |
| `clinical_utility_gap` | OPEN | PPV = 0.12, sensitivity = 0.33 at deployed threshold — no utility evidence required |
| `distribution_shift_gap` | OPEN | No multi-site validation; deployed on populations not in training data |

### 6.2 The v1 profile authorizes Epic

Under the v1 profile — the one implicitly governing clinical AI deployment at most institutions before 2022 — only the first five gaps are required at ALR. Epic satisfies all five. The compiler emits ALR.

```
Γ ⊢ epic_sepsis_model : ALR  until ε₁
```

The audit field records: all required gaps bounded; `clinical_utility_gap` and `distribution_shift_gap` not required by profile; permission search reaches ALR; judgement issued.

This is the falsification of v1. Profile v1 would have authorized Epic's deployment. Epic was deployed. Wong et al. (2021) documented the harm.

### 6.3 The v6 profile blocks Epic

The converged v6 profile requires all six induced domain gaps at ALR, in addition to the structural skeleton. Epic has two open: `clinical_utility_gap` and `distribution_shift_gap`.

```
Γ ⊬ epic_sepsis_model : ALR

Γ ⊢ epic_sepsis_model : AEX  until ε₂
```

The audit field records exactly why:

```
requested:    ALR
granted:      AEX

blocking_reasons:
  - clinical_utility_gap OPEN (required BOUNDED at ALR)
    PPV = 0.12 < floor 0.15 in clinical_utility_token detail contract
    token marked invalid by certifier; gap not advanced from OPEN
  - distribution_shift_gap OPEN (required BOUNDED at ALR)
    no multi-site validation token presented
    no institution-specific cohort evidence

accepted_tokens:
  - approximation_quality_token (AUC = 0.76, internal validation)
  - model_specification_token (sepsis onset as target)
  - calibration_token
  - blast_radius_token (alert-only action class)
  - freshness_token

required_continuations:
  - present clinical_utility_token with PPV >= 0.15 at deployed threshold
  - present distribution_shift_token with institution identifier,
    cohort date range, cohort size, and drift statistics for
    deployment population
```

Epic may be studied experimentally. It may not be rolled out.

### 6.4 The four-cell table

The framework's authorization decisions, checked against hindsight:

|  | Hindsight: harm | Hindsight: benefit |
|--|-----------------|-------------------|
| **Compiler: ALR** | **(ALR, deployed, harm)** Epic under v1. Compiler authorizes. Model deploys. Sensitivity = 0.33, PPV = 0.12 at 100+ hospitals. Falsification of v1. | **(ALR, deployed, benefit)** CHARTwatch under v2 (Toronto General, GIM ward). PPV = 0.40, sensitivity = 0.77. All gaps bounded. Compiler emits ALR. Prospective deployment showed clinical benefit. v2 is not over-refusal. |
| **Compiler: < ALR** | **(< ALR, blocked, harm-prevented)** Epic under v2 and v6. PPV = 0.12 fails clinical_utility_token floor. Token invalid. Gap open. Compiler caps at AEX. Correction. | **(< ALR, blocked, benefit-foregone)** Named limitation. Filling this cell honestly requires a model with PPV between 0.12 and 0.15, prospective evidence of clinical benefit, and the profile being the specific deployment barrier. No published case meets all three conditions. |

The benefit-foregone cell is a genuine limitation. The PPV floor of 0.15 in the `clinical_utility_token` detail contract is a design parameter, not a theorem. A model with PPV = 0.14 and high sensitivity might, in a specific care context, produce net clinical benefit despite failing the floor. The framework's structural response: the floor is explicit and auditable. An institution that disagrees with it can change it. An informal governance process that applies no floor cannot be audited, overridden, or held accountable. The framework does not claim the floor is correct. It claims that having a named, enforceable floor is better than having no floor, and that the correct floor belongs in the profile governance process, not in the model evaluation process.

### 6.5 Profile stability

The v1 → v2 transition is bounded. Lemma M (proved in the companion structural paper) establishes that a single-entry profile tightening can change emitted permission by at most one step. Corollary M1 extends this: permission is Lipschitz in the profile, with constant 1 in the profile entry metric.

For Epic, the v1 → v2 transition adds two requirements. Epic drops two steps — from ALR to AEX. CHARTwatch satisfies both new requirements: it drops zero steps, remaining at ALR. A profile that differs from the correct profile by $k$ entries cannot produce an output more than $k$ steps wrong. The transition is surgical.

---

## 7. The Compiler

The compiler is the mechanism that constructs the judgement. It receives the proof context and emits the greatest permission the context supports.

The compiler algorithm:

1. If membership is not IN_CLASS, emit OOC. Halt.
2. Induce claim $c$.
3. Induce gaps $G$ under fixed $\Theta_v$.
4. If expired, emit EXP. Halt.
5. For each token $\tau$: check registry status, detail contract, expiry, scope, and provenance. Advance $\mathsf{Eff}_\Gamma(g)$ only through valid witnesses.
6. Record structural failures: provenance mismatch fires REF; revoked or malformed credentials fire REF; disallowed uses impose a ROL ceiling.
7. Record authority ceiling: meet the positive outcome with the actor's delegation limit.
8. Record non-promotion ceiling: in composed contexts, meet with the minimum of the component judgements.
9. Search positive permissions in descending order — AAA, ALR, AEX, REV, DIA — returning the first whose profile requirements are satisfied. If no profile is satisfied, emit UNS.
10. Apply structural failures and ceilings as meets. Every meet can only preserve or lower the outcome.
11. Apply token-level expiry: if any live token with correct provenance has expired, floor to EXP.
12. Register negative-control tokens for runtime liveness check.
13. Emit $\Gamma \vdash z : p_{\text{final}} \ \text{until} \ \varepsilon$.
14. Record blocking reasons for every denied stronger permission.

The core discipline:

```
No approximation may be used as stronger permission than its evidence,
scope, provenance, expiry, authority, and policy profile jointly support.
```

The compiler enforces five separations.

**Requested from supported.** The caller's desired outcome is not evidence.

**Policy from enforcement.** The profile states which gaps are required for which permissions. The compiler enforces the profile mechanically. The same profile, applied to the same evidence, produces the same output every time. It cannot be persuaded, fatigued, or deadline-pressured.

**Token type from token validity.** A token is not evidence because it has a reassuring name. It must satisfy a registered detail contract, including schema checks, semantic checks, artifact dependencies, scope rules, and expiry rules.

**Evidence existence from evidence provenance.** A token supports a gap only when provenanced to the exact tuple it claims to support:

$$
(\tau, g, c, z, x)
$$

Token, gap, claim, candidate, and context. No provenance, no proof. This is the anti-laundering property. Epic's validation at the developing institution cannot be submitted as evidence for a deployment at a hospital that was not part of the validation. The provenance hash cryptographically binds the token to exactly one deployment context.

**Structural admissibility from domain truth.** The compiler checks that the right kind of evidence was presented, scoped correctly, live, satisfying its registered contract, attached to the right candidate and context. It cannot guarantee that the certifier used good science or that the domain's threshold was morally correct. Those are trusted-computing-base assumptions and governance obligations. This limitation is the framework's epistemological boundary — not a defect.

A judgment is therefore not merely a decision. It is a decision plus the exact context in which that decision was valid. If a deployment was refused, the judgement records which stronger permissions were blocked and why. If a deployment was authorized, the judgement records which profile, taxonomy, detail contracts, tokens, provenance records, authority envelope, and expiry condition supported that authorization. The compiler is that discipline:

```
Approximate outputs do not authorize action directly.
They authorize action only by compiling into an admissibility judgement.
```

---

## 8. What the Framework Can and Cannot Guarantee

The preceding sections establish the formal structure of the framework and demonstrate it running on a single domain. This section reports what we actually know from running it: what the compiler enforces unconditionally, what it accepts on faith, where the governance obligation falls, and how the taxonomy transfer argument holds up when run against independent ground truth.

### 8.1 The compiler boundary

The admissibility compiler enforces seven properties by construction — properties that hold regardless of what the caller supplies:

**Provenance hash.** A token is valid only for the exact `(claim, candidate, context, allowed_use)` tuple it was issued against. The hash is SHA-256 over that tuple. Epic's validation at the developing institution cannot be submitted as evidence for a deployment at a different institution. The compiler does not inspect the token's provenance claim. It recomputes the hash from the current context and rejects tokens that do not match.

**Token status.** Invalid tokens are ignored regardless of claims. A `clinical_utility_token` whose PPV field is below the detail contract floor has its `status` field set to `"invalid"` by the certifier, and `bounds_gaps` cleared, before it reaches gap evaluation. The compiler never sees the PPV value. It sees an invalid token and a gap that has not advanced.

**Expiry.** An expired token floors the judgment to EXP. The `LiveJudgment` type enforces this at the type level: reading a permission value through `LiveJudgment::permission()` re-evaluates the expiry condition at read time. It is not possible to hold a reference to a valid permission past the expiry boundary without invoking the live check.

**Authority ceiling.** The compiler meets the positive outcome with the actor's delegation limit. This meet can only preserve or lower the outcome. A submitter cannot claim more authority than the ceiling assigns.

**Non-promotion under composition.** A composed context inherits `min(component permissions)`. The stronger component cannot pull the weaker one up. A claim supported only by weak evidence does not become stronger by being composed with a well-evidenced claim.

**Empty profile floor.** A proof context with no profiles compiles to OOC. No profiles means the framework has no opinion on this claim class — the in-class floor is not reachable without a profile.

**Absent gap default.** A gap absent from the context's `gap_statuses` is treated as OPEN. The compiler does not silently default absent proof obligations to closed.

These seven properties are enforced structurally. They cannot be bypassed by constructing a proof context that omits or misrepresents any field. The adversarial attack experiments confirm this: A4 (authority ceiling spoofing), A6 (empty profile → OOC), A7 (invalid token status), A8 (expired token → EXP floor), and A9 (provenance hash mismatch → AEX) are all blocked regardless of what the attacker supplies in the remaining fields.

### 8.2 The trusted computing base

Eight properties are accepted on faith. They constitute the compiler's trusted computing base (TCB) — the boundary beyond which the compiler's guarantees do not extend.

**Gap status truthfulness.** The compiler accepts the `status` field of each `GapRecord` as presented. A dishonest submitter who replaces every OPEN gap with `"bounded"` causes the compiler to emit ALR. Experiment 2a confirms this: all six induction cases over-authorize when blocking gaps are falsified. The compiler cannot verify that the submitted status reflects the actual state of the world; it can only verify that the submitted status satisfies the profile's minimum. The certifier discipline — requiring that gap statuses be produced by certifiers who sign tokens, not written by hand in the proof context — is a governance obligation that sits outside the compiler.

**Numerical bound values.** The compiler does not compare bound values against domain floors at the profile level. A `distribution_shift_token` with `domain_classifier_auc = 0.001` reaches gap evaluation. Whether that value is scientifically meaningful is a question for the certifier, not the compiler. (The token-level detail contract can impose a floor if the domain bridge encodes one — and the medical bridge does for clinical utility — but this is a per-domain design choice, not a compiler guarantee.)

**Token type / gap compatibility.** Any structurally valid, provenanced token can be submitted as evidence for any gap. A freshness certificate whose provenance matches the current context can be offered as evidence for `clinical_utility_gap`. The compiler checks provenance and schema validity; it does not check whether the token type is semantically appropriate for the gap it claims to close. A1 (status assertion path) and A3 (token type laundering) confirm this: the compiler is broken by supplying a correctly provenanced token of the wrong type for a gap. The detail contract registry — specifying which token types are admissible for which gaps — is the defense. It is a governance artifact, not a compiler invariant.

**Scientific validity.** The compiler checks that the right kind of evidence was presented in the right form with valid provenance. It does not check that the certifier used valid science. A token attesting `n=47` in a single-center observational study with the training population, with PPV = 0.16 (just above the floor of 0.15), with no held-out test set, compiles to ALR on the clinical utility gap. The science is bad. The token is structurally valid. This is T4 in the TCB experiments.

**Membership classification.** The membership field is caller-asserted. A submitter who misclassifies an out-of-class candidate as InClass gets an in-class judgment. T5 confirms this.

**Schema version binding.** The compiler accepts deprecated schema versions. A proof context presenting a `clinical_utility_token` under schema version `"med001/0.0"` — a version that predates the PPV floor — still reaches gap evaluation. The profile version registry, which should reject deprecated contracts at context construction, is a governance artifact.

**Profile version.** The caller chooses which profile to apply. There is no version registry in the compiler that rejects deprecated profiles. A submitter who explicitly selects profile v1 — which does not require clinical utility or distribution shift evidence — gets an ALR judgment on Epic. This is not a theorem violation. It is a governance gap: the context construction step should reject deprecated profiles, but the compiler itself has no opinion about which profiles are current. R3 in the tamper resistance experiments confirms that profile rollback succeeds at the compiler level.

**Context identity versioning.** A context_id change alone does not invalidate previously issued tokens. Tokens carry their provenance hash; if a new context_id is chosen but the hash is recomputed from the old context_id, old tokens are still rejected. But if the context_id changes and tokens are reissued under the new context_id, the compiler has no memory of the previous context. Evidence-invalidating deployment changes — population shift, model update, threshold change — must be reflected in a new context_id with new tokens, and the governance process must enforce this. R4 confirms the structural property: same context_id → token carries; different context_id → token rejected. The governance obligation is to change the context_id when it should change.

### 8.3 Governance obligations

The TCB analysis implies five governance obligations that fall outside the compiler and must be satisfied by the institutional deployment process:

Certifiers must produce tokens and sign gap statuses. Bridge authors must not write gap statuses by hand. The certifier discipline is what prevents Experiment 2a's attack (falsified statuses) in practice.

The detail contract registry must enforce token type / gap compatibility. Without this registry, any provenanced token can close any gap.

The profile version registry must reject deprecated profiles at context construction. Without this, a submitter can always roll back to the weakest profile in the history.

The context_id must change when evidence-invalidating deployment changes occur. Population shift, model update, threshold change, and site expansion all represent changes for which existing tokens are no longer valid evidence.

Sample size, population independence, pre-registration, and held-out test sets are certifier obligations. The compiler cannot see them. The certifier governance process must enforce them.

### 8.4 Empirical results: adversarial and composition attacks

The adversarial experiment (A1–A10) tests ten attack vectors against the converged v6 medical profile. Five attacks break the compiler:

- **A1** (gap status assertion): marks all blocking gaps as `"bounded"` without tokens → ALR. TCB violation.
- **A2** (bound value fabrication): supplies a token with `domain_classifier_auc = 0.001` → ALR. TCB violation.
- **A3** (token type laundering): correct provenance, wrong token type for the gap → ALR. TCB violation.
- **A5** (membership spoof): InClass assertion on an out-of-class candidate → in-class judgment. TCB violation.
- **A10** (all gaps closed, no tokens): gap statuses set to `"closed"` by hand, no supporting tokens → ALR. TCB violation.

Five attacks are blocked by the compiler's structural properties:

- **A4** (authority ceiling): `authority_ceiling = ETA` → AEX; positive evidence cannot exceed the ceiling.
- **A6** (empty profile): no profiles → OOC regardless of gap statuses.
- **A7** (invalid token status): token with `status="invalid"` → gap stays open; compiler emits AEX.
- **A8** (expired token): expired token → EXP floor applied.
- **A9** (provenance mismatch): token issued for a different context → rejected; gap stays open; AEX.

All five breaks are TCB violations — they exploit gaps the compiler accepts on faith. All five blocks are structural — they exploit properties the compiler enforces unconditionally. The break/block boundary maps exactly onto the TCB boundary.

The tamper resistance experiment (R1–R6) tests four structural composition properties and finds two governance gaps:

- **R1**: `compose(AEX, AEX)` = AEX. Non-promotion holds.
- **R2**: `compose(ALR, AEX)` = AEX. The stronger component cannot pull the weaker up.
- **R3**: Profile rollback from v6 to v1 yields ALR on Epic. This is a governance gap, not a theorem violation: the compiler enforces the profile it is given.
- **R4**: Token issued for context A is rejected in context B. Same context_id → token carries. Different context_id → rejected. Cross-context replay is blocked.
- **R5**: All gaps asserted `"bounded"` by status (no tokens) + blast radius scope mismatch → ALR on the status path. This is a governance gap: the blast radius scope check requires a token; the status path bypasses it.
- **R6**: `compose(ctx_A, ctx_B)` where a token was issued for ctx_A. The composed context inherits ctx_A's identity, but the token's provenance hash was computed against the original allowed_use tuple; the composition changes the effective context. Token rejected. Composed result: AEX.

### 8.5 Empirical results: cross-domain taxonomy transfer

The medical induction result establishes a six-gap taxonomy from six failure cases. The legal induction result establishes a four-gap taxonomy from four failure cases, starting from zero domain knowledge. Both are tested against independent ground truth.

**Medical domain.** The six induced gaps are audited post-hoc against FDA Draft Guidance (FDA-2024-D-4488, January 2025), NHS RCR "AI Deployment Fundamentals for Medical Imaging" (November 2024), and the EU AI Act (2024). The audit finds 12/12 requirements covered, with zero novel gaps in the compiler taxonomy and zero uncovered regulatory requirements. The two gaps that emerge only when writing compiler-processable policy — `shadow_mode_validation_gap` and `post_market_monitoring_gap` — are present in the NHS text but not visible in the six failure cases that drove induction. They become visible when the profile must supply concrete thresholds, scope rules, and certifier obligations in a form the compiler can process.

**Legal domain.** The four induced gaps are compared against Magesh et al. (JELS 2025), an empirical audit of Lexis+ AI and Westlaw AI-Assisted Research. Magesh et al. documented four failure categories in production systems: jurisdictional inapplicability, superseded authority, incorrect binding force, and question mismatch. The compiler independently induced: `jurisdictional_scope_gap`, `precedential_currency_gap`, `precedential_weight_gap`, and `question_specificity_gap`. The mapping is 1-to-1, with zero novel gaps and zero uncovered failure modes.

The legal comparison is structurally distinct from the medical comparison. The FDA/NHS/EU AI Act are advance specifications — humans writing down what should matter before deployment. Magesh et al. is a post-deployment empirical finding — auditors observing what actually went wrong in production systems that neither had access to this framework nor were designed to satisfy its requirements. The compiler derived the same taxonomy from different cases on a different continent without knowledge of the audit. Neither side could have reverse-engineered the other's result.

The freshness/currency distinction in the legal domain illustrates the depth of the convergence. Both the compiler (forced by L03, where Lochner — overruled in 1937 — appeared in a fresh corpus) and Magesh et al. (empirically observing that overruled cases appear in AI-generated legal citations despite being in current corpora) had to discover that corpus currency and precedential currency are categorically different failure modes. That this non-obvious conceptual split appears in both derivations for the same structural reason is the convergence result.

**Cross-domain result.** The CASE-LIB-001 retrospective applies a four-gap Tier 1 profile — the intersection of the medical and legal gap taxonomies — to sixteen documented AI deployment harms across medical, criminal justice, employment, autonomous systems, and government benefits. The profile was not designed for these cases. Applied retrospectively, it covers all sixteen without modification. The cross-domain transfer result does not claim the Tier 1 profile is sufficient for any individual domain. It claims that the four gaps at the intersection of multiple independently derived domain taxonomies are not domain-specific artifacts — they reflect a failure structure present across consequential approximate systems generally.

---

## References

Abadi, Martín, Michael Burrows, Butler Lampson, and Gordon Plotkin. 1993. "A Calculus for Access Control in Distributed Systems." *ACM Transactions on Programming Languages and Systems.*

Necula, George C. 1997. "Proof-Carrying Code." *POPL.*

Appel, Andrew W., and Edward W. Felten. 1999. "Proof-Carrying Authentication." *CCS.*

Myers, Andrew C. 1999. "JFlow: Practical Mostly-Static Information Flow Control." *POPL.*

Schneider, Fred B. 2000. "Enforceable Security Policies." *ACM Transactions on Information and System Security.*

Wong, Andrew, et al. 2021. "External Validation of a Widely Implemented Proprietary Sepsis Prediction Model in Hospitalized Patients." *JAMA Internal Medicine.*

Obermeyer, Ziad, et al. 2019. "Dissecting Racial Bias in an Algorithm Used to Manage the Health of Populations." *Science.*

Tonekaboni, Sana, et al. 2022. "Predicting Clinical Deterioration in Hospitalized Patients: A Prospective Study." *Frontiers in Digital Health.*

Nagendran, Myura, et al. 2020. "Artificial Intelligence versus Clinicians: Systematic Review of Design, Reporting Standards, and Claims of Deep Learning Studies in Medical Imaging." *BMJ.*

FDA. 2025. *Artificial Intelligence-Enabled Device Software Functions — Draft Guidance.* Docket FDA-2024-D-4488. January.

NHS Royal College of Radiologists. 2024. *AI Deployment Fundamentals for Medical Imaging.* November.

Gebru, Timnit, et al. 2021. "Datasheets for Datasets." *Communications of the ACM.*

Mitchell, Margaret, et al. 2019. "Model Cards for Model Reporting." *FAccT.*

Moreau, Luc, et al. 2013. "PROV-DM: The PROV Data Model." *W3C Recommendation.*
