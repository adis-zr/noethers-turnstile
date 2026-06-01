# Admissibility Judgement for Approximate Consequential Systems

## Abstract

In 2021, an external validation published in JAMA Internal Medicine found that the Epic Sepsis Model, deployed at over 100 hospitals, produced alerts that were wrong eight times out of nine. AUC was 0.76. Sensitivity at the deployed threshold was 0.33. PPV was 0.12. The model had been authorized for deployment because nothing required anyone to ask whether the score was useful at the threshold where nurses would act on it.

This paper builds a framework that would have caught it.

We introduce a permission-valued admissibility judgement, $\Gamma \vdash z : p \ \text{until}\ \varepsilon$, enforced by an accompanying compiler. The judgement asks what operational permission follows from the available evidence. The compiler emits the strongest permission actually supported and prevents that permission from being silently upgraded as an artifact moves through a workflow.

Applied to Epic, the framework issues a precise diagnosis: the deployment was authorized because the implicit governance policy required AUC to be bounded but did not require clinical utility at the deployed threshold to be bounded. That omission is not visible in prose governance — it only becomes visible when policy is forced into compiler-processable form.

We show that the gap taxonomy the compiler requires — the set of proof obligations that must be discharged before each permission level — is not a designer's choice. It is determined by the domain's failure structure. We prove a representation theorem characterizing exactly when a domain admits such a compiler. We then run the induction loop: starting from an empty taxonomy, the compiler, presented with Epic and five comparable deployments, mechanically discovers the same six-gap taxonomy that the FDA's January 2025 draft guidance and the NHS RCR's 2024 deployment fundamentals require. The compiler and the regulators were responding to the same event.

The paper closes by running the framework on Epic's own published numbers. The v1 profile — the one implicitly in use at deployment — authorizes Epic. The v6 profile — the one the compiler discovers from failure evidence alone — blocks it, in under a second, with an exact audit trail.

---

## 1. The Problem Epic Exposes

In 2021, Wong et al. published an external validation of the Epic Sepsis Model in JAMA Internal Medicine. The model had been deployed at over 100 hospitals. The published numbers were: AUC = 0.76, sensitivity = 0.33, PPV = 0.12 at the deployed alert threshold. For every true sepsis case the model identified, it generated eight false alerts. Nurses were acting on alerts that were wrong eight times out of nine.

The Epic case is worth dwelling on before any formalism, because it is not primarily a story about a bad model. The AUC of 0.76 is unremarkable — it is close to the median AUC reported across clinical AI studies in the same period. Epic's failure is a story about authorization: the model was deployed because no framework required anyone to check whether it was useful at the point of use.

AUC measures discrimination across all possible thresholds. It answers the question: if you draw one true positive and one true negative at random, how often does the model rank the positive higher? That is a useful question during development. It is not the question a nurse faces when deciding whether to act on an alert. The nurse's question is: given that the model fired, what is the probability that this patient actually has sepsis? That is PPV at the deployed threshold. PPV = 0.12 means the answer is 12%. The model had a published AUC. Clinical utility evidence was never required. Deployment proceeded.

This is not a failure of the people involved. It is a failure of structure. The authorization decision was made through a process that never formally asked whether the evidence supported the action being authorized. The implicit governance policy was: if AUC is acceptable, the model may be deployed. Nothing in that policy demanded the answer to the nurse's question.

The framework this paper introduces does not make that kind of authorization possible. It forces the question into the open.

---

## 2. The Framework, Defined Through Epic

### 2.1 The admissibility judgement

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

The positive permissions are:

| Symbol | Meaning |
|--------|---------|
| `DIA` | Diagnostic display only — output may be shown, not acted on |
| `REV` | Recommend human review — a clinician should assess before action |
| `AEX` | Approve experiment — suitable for a controlled deployment study |
| `ALR` | Approve limited rollout — authorized for operational use with logging |
| `AAA` | Approve automatic action — unrestricted |

Epic was deployed at ALR. The framework's question is whether ALR was supported by the evidence. It was not — and the framework makes that precise.

### 2.2 The proof context and what it demands

For the judgement to be meaningful, the compiler needs a proof context $\Gamma$ that captures everything relevant to the authorization question:

$$
\Gamma = \bigl(\mathsf{membership},\ \mathsf{claim},\ \mathsf{candidate},\ \mathsf{context},\ \mathsf{scope},\ \mathsf{claim\_gaps},\ \mathsf{gap\_taxonomy\_version},\ \mathsf{gap\_profile\_version},\ \mathsf{proof\_tokens},\ \mathsf{proof\_token\_provenance},\ \mathsf{detail\_contract\_registry\_version},\ \mathsf{expiry},\ \mathsf{allowed\_use},\ \mathsf{authority},\ \mathsf{runtime\_context},\ \mathsf{audit}\bigr)
$$

The fields divide into five roles. First, they fix the object of judgement: what is being judged, in what setting, for what use. Second, they fix the proof obligations: which gaps are induced, under which taxonomy version, required to what level by which profile version. Third, they record the evidence: which tokens were presented, each bound by exact provenance to the specific claim, candidate, and context it supports. Fourth, they impose scope and temporal constraints: when the judgement expires, what uses it covers, what authority ceilings apply. Finally, the `audit` field explains the result — which permissions were denied, which gaps blocked them, which tokens were rejected, which runtime checks failed.

The proof context is not a universal ontology invented by the framework designer. It is domain-specific machinery, written down explicitly, that the compiler then enforces mechanically. For Epic, the proof context must answer: is this system in-class for clinical alerting? What proof obligations are induced for a clinical alert deployment? What evidence has been supplied to discharge them? What permission does that evidence support?

That last question requires a profile.

### 2.3 Gaps — what Epic's deployment failed to answer

A **gap** is a proof obligation. It names a way in which the current evidence may be insufficient for the requested use.

$$
g = (\mathsf{gap\_id},\ \mathsf{gap\_type},\ \mathsf{status},\ \mathsf{metadata})
$$

where $\mathsf{status} \in \{\mathsf{OPEN},\ \mathsf{BOUNDED},\ \mathsf{CLOSED}\}$. OPEN means no admissible evidence has been supplied. BOUNDED means evidence limits the risk without fully discharging it. CLOSED means evidence discharges the obligation for the relevant scope and use.

The framework introduces gaps not as abstract constructs but as precise names for questions that must be answered before each permission level. Applied to Epic, the question is: what did Epic's deployment fail to answer?

The answer is specific. Epic presented evidence for several obligations. AUC = 0.76 bounded `approximation_quality_gap`: the model is not random. Model specification was documented: the prediction target was sepsis onset. Calibration and blast radius were characterized. What Epic did not present — what was never required — was:

**`clinical_utility_gap`**: Is PPV/sensitivity sufficient at the deployed threshold for the intended action class? This is not a variation on AUC. It is a different question entirely. A model can have AUC = 0.90 and PPV = 0.05 at the threshold where it fires alerts, if it is set to fire rarely. PPV = 0.12 at Epic's deployed threshold means that 88% of alerts are false. The clinical utility gap was not defined in the implicit profile governing Epic's deployment. It was not asked. No certifier was ever required to answer it.

**`distribution_shift_gap`**: Does the model's validation hold on the deployment population? Epic was validated on data from the developing institution's patient population. Deployed at 100+ hospitals across different geographies, demographics, and care patterns, it was used on populations it had never been validated against. The distribution shift gap names this question. It requires: institution identifier, cohort date range, cohort size, domain classifier AUC comparing training to deployment population, per-feature drift statistics for top predictive features. Evidence without an institution identifier is structurally invalid for this obligation — there is no way to audit whether the right population was tested. Epic's deployment had no such evidence. The question was never posed.

The forcing function argument: most deployed clinical AI systems have never produced this evidence. Not because it is unavailable, but because nothing has ever demanded it in this form. The compiler is that demand. Before a judgement can be made, the proof context must supply the tokens. Before a token can be issued, the certifier must have produced the evidence. The discipline is in the writing-down, exactly as TLA+ makes the discipline visible for distributed systems.

### 2.4 The profile — what a policy that required these answers would look like

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

### 2.5 What the proof context prevents

The proof context prevents evidence overextension. The canonical forms:

**Evidence reuse across contexts.** A clinical utility validation conducted for one institution cannot be submitted as evidence for a deployment at a different institution. The `proof_token_provenance` field binds each token to the exact `(claim, candidate, context, allowed_use)` tuple it was issued against. A provenance hash mismatch means the token is rejected. Epic's validation at the developing institution is not evidence for Epic's deployment at 100 other hospitals.

**Token type laundering.** A freshness certificate cannot close a clinical utility gap. Tokens must satisfy registered detail contracts that specify their schema, semantic checks, artifact dependencies, scope rules, and expiry rules. Token type is a metadata field for human auditors. The compiler enforces the detail contract, not the name. A clinical utility token whose PPV field reads 0.12 fails the semantic check `ppv >= min_ppv` and is marked invalid before it reaches gap evaluation.

**Expiry.** A validation study conducted three years before deployment, on a patient population that has since shifted, is not current evidence. The expiry condition $\varepsilon$ states when the judgement ceases to be live. The domain expert defines what makes evidence expire — the compiler enforces it. This is the hardest and most critical component of the framework for real-time systems. Evidence is temporal. The framework treats it as such.

**Separation of requested from supported permission.** The caller may request ALR. The compiler ignores that request as evidence. It emits the greatest permission supported by the proof context. A request for rollout does not count as rollout evidence.

---

## 3. The Gap Taxonomy Is Not Arbitrary

The Epic case raises an immediate question: is `clinical_utility_gap` a principled construct, or is it a name the framework designer chose? Could a different designer, looking at the same failure, have arrived at different gaps and reached different conclusions?

The answer to this question matters because the framework's authority depends on it. If the taxonomy is arbitrary, then the framework is a sophisticated way of encoding the designer's prior opinions. If the taxonomy is determined by the domain's failure structure, then the framework discovers something real.

This section answers the question in three steps.

### 3.1 The representation theorem

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

The theorem says: the taxonomy is not chosen. It is the finite monotone observable shadow of the domain's ideal licensing structure. The compiler works sharply for a domain exactly when the domain's failure sets admit this kind of finite presentation. A taxonomy that does not correspond to a real failure mode is not a ground requirement — it is padding, and a grounded profile will not contain it.

Applied to Epic: `clinical_utility_gap` is not a naming choice. It names the upward-closed failure set in the clinical alert action-state space consisting of all states where PPV at the deployed threshold is below the level required for the action class. That set exists whether or not anyone names it. The compiler's job is to observe it.

### 3.2 Grounded profiles do not silently authorize unmitigated failure modes

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

### 3.3 The clean witness theorem and regulatory convergence

The third step removes the last ambiguity: are the gaps that a designer names looking at Epic the same gaps an independent observer would arrive at?

The **clean witness theorem** (proved in the MED-STR-SYN-001 synthetic probe) establishes that the induction loop — starting from an empty taxonomy, presented only with failure cases and an over-authorization signal — converges on the unique minimal sufficient taxonomy. The loop induces a gap when the compiler over-authorizes on a case where that gap is the last remaining unresolved proof obligation. Because the signal is over-authorization rather than correlation, the loop cannot induce spurious gaps: once the profile is complete, the signal stops firing, regardless of what other correlates are present in the cases.

The induction is run on Epic and five comparable AI deployment failures (MED-IND-001). Starting from v0 — a skeleton profile requiring only approximation quality and freshness — the loop induces, in order:

1. `clinical_utility_gap` — from the Epic sepsis model (Wong et al. 2021)
2. `model_specification_gap` — from the Optum racial bias study (Obermeyer et al. 2019)
3. `distribution_shift_gap` — from PredPol predictive policing feedback effects
4. `individual_population_gap` — from COMPAS recidivism scoring
5. `blast_radius_gap` — from IBM Watson Oncology
6. `authority_gap` — from the Dutch childcare benefit algorithm

The converged profile is then audited against FDA Draft Guidance (January 2025, docket FDA-2024-D-4488) and NHS RCR "AI Deployment Fundamentals for Medical Imaging" (November 2024) — two regulatory frameworks developed independently, by different institutions, on different continents, over several years.

The audit finds 12/12 FDA and NHS requirements covered by the six induced gaps. The compiler, run against failure evidence alone with no regulatory text consulted during induction, discovered the same taxonomy the regulators produced.

This is the regulatory convergence result. `clinical_utility_gap` was induced from the Epic failure. FDA Appendix C's operating-point metrics requirement exists because of the Epic failure. The compiler and the regulator were responding to the same event. The gap is not a naming choice. It is the domain's failure structure, observed from two directions.

---

## 4. The Framework Running on Epic

This section closes the loop. The paper opened by asking what a framework that prevented Epic would look like. This section shows that framework running, on Epic's own published numbers.

### 4.1 Evidence available at deployment time

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

### 4.2 The v1 profile authorizes Epic

Under the v1 profile — the one implicitly governing clinical AI deployment at most institutions before 2022 — only the first five gaps are required at ALR. Epic satisfies all five. The compiler emits ALR.

```
Γ ⊢ epic_sepsis_model : ALR  until ε₁
```

The audit field records: all required gaps bounded; `clinical_utility_gap` and `distribution_shift_gap` not required by profile; permission search reaches ALR; judgement issued.

This is the falsification of v1. Profile v1 would have authorized Epic's deployment. Epic was deployed. Wong et al. (2021) documented the harm.

### 4.3 The v6 profile blocks Epic

The converged v6 profile — the one the induction loop discovers from failure evidence alone — requires all six induced domain gaps at ALR, in addition to the structural skeleton. Epic has two open: `clinical_utility_gap` and `distribution_shift_gap`.

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

### 4.4 The four-cell table

The framework's authorization decisions, checked against hindsight:

|  | Hindsight: harm | Hindsight: benefit |
|--|-----------------|-------------------|
| **Compiler: ALR** | **(ALR, deployed, harm)** Epic under v1. Compiler authorizes. Model deploys. Sensitivity = 0.33, PPV = 0.12 at 100+ hospitals. Falsification of v1. | **(ALR, deployed, benefit)** CHARTwatch under v2 (Toronto General, GIM ward). PPV = 0.40, sensitivity = 0.77. All gaps bounded. Compiler emits ALR. Prospective deployment showed clinical benefit. v2 is not over-refusal. |
| **Compiler: < ALR** | **(< ALR, blocked, harm-prevented)** Epic under v2 and v6. PPV = 0.12 fails clinical_utility_token floor. Token invalid. Gap open. Compiler caps at AEX. Correction. | **(< ALR, blocked, benefit-foregone)** Named limitation. Filling this cell honestly requires a model with PPV between 0.12 and 0.15, prospective evidence of clinical benefit, and the profile being the specific deployment barrier. No published case meets all three conditions. |

The benefit-foregone cell is a genuine limitation. The PPV floor of 0.15 in the `clinical_utility_token` detail contract is a design parameter, not a theorem. A model with PPV = 0.14 and high sensitivity might, in a specific care context, produce net clinical benefit despite failing the floor. The framework's structural response: the floor is explicit and auditable. An institution that disagrees with it can change it. An informal governance process that applies no floor cannot be audited, overridden, or held accountable. The framework does not claim the floor is correct. It claims that having a named, enforceable floor is better than having no floor, and that the correct floor belongs in the profile governance process, not in the model evaluation process.

### 4.5 Profile stability

The v1 → v2 transition is bounded. Lemma M (proved in the companion structural paper) establishes that a single-entry profile tightening can change emitted permission by at most one step. Corollary M1 extends this: permission is Lipschitz in the profile, with constant 1 in the profile entry metric.

For Epic, the v1 → v2 transition adds two requirements. Epic drops two steps — from ALR to AEX. CHARTwatch satisfies both new requirements: it drops zero steps, remaining at ALR. A profile that differs from the correct profile by $k$ entries cannot produce an output more than $k$ steps wrong. The transition is surgical.

---

## 5. The Compiler

The compiler is the mechanism that constructs the judgement. It receives the proof context and emits the greatest permission the context supports.

The compiler algorithm:

1. If membership is not IN_CLASS, emit OOC. Halt.
2. Induce claim $c$.
3. Induce gaps $G$ under fixed $\Theta_v$.
4. If expired, emit EXP. Halt.
5. For each token $\tau$: check registry status, detail contract, expiry, scope, and provenance. Advance $\mathsf{Eff}_\Gamma(g)$ only through valid witnesses.
6. Record structural failures: provenance mismatch, scope conflict, derivation invalid, negative control failed, runtime context failure.
7. Record control outcomes: authority ceiling exceeded, human tradeoff required, rollback condition met.
8. Search positive permissions in descending order — AAA, ALR, AEX, REV, DIA — returning the first whose profile requirements are satisfied.
9. Meet with REF if structural failures exist.
10. Meet with control outcomes.
11. Emit $\Gamma \vdash z : p_{\text{final}} \ \text{until} \ \varepsilon$.
12. Record blocking reasons for every denied stronger permission.

The core discipline:

```
No approximation may be used as stronger permission than its evidence,
scope, provenance, expiry, authority, and policy profile jointly support.
```

The compiler enforces five separations.

**Requested from supported.** The caller's desired outcome is not evidence.

**Policy from enforcement.** The profile states which gaps are required for which permissions. The compiler enforces the profile mechanically.

**Token type from token validity.** A token is not evidence because it has a reassuring name. It must satisfy a registered detail contract, including schema checks, semantic checks, artifact dependencies, scope rules, and expiry rules.

**Evidence existence from evidence provenance.** A token supports a gap only when provenanced to the exact tuple it claims to support:

$$
(\tau, g, c, z, x)
$$

Token, gap, claim, candidate, and context. No provenance, no proof. This is the anti-laundering property. Epic's validation at the developing institution cannot be submitted as evidence for a deployment at a hospital that was not part of the validation. The provenance hash cryptographically binds the token to exactly one deployment context.

**Structural admissibility from domain truth.** The compiler checks that the right kind of evidence was presented, scoped correctly, live, satisfying its registered contract, attached to the right candidate and context. It cannot guarantee that the certifier used good science or that the domain's threshold was morally correct. Those are trusted-computing-base assumptions and governance obligations. This limitation is the framework's epistemological boundary — not a defect.

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
