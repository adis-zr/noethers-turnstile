# Admissibility Compilers for Approximate Consequential Systems

## Abstract

TBD

---

## 0. What the Compiler Can and Cannot Guarantee

This section states the epistemological position of the paper before any formalism. A reader who disagrees with this position should stop here.

### 0.1 Two classes of approximate consequential system

The framework's guarantee depends on which class of system it is applied to. The distinction is not a matter of degree — it is a structural difference in where the gap taxonomy comes from.

**Mathematically grounded systems.** In probabilistic inference, formal verification, and cryptographic protocols, the gap taxonomy is canonical. `posterior_divergence_gap` is not a policy choice. The KL divergence between the approximate posterior and the true posterior either satisfies the certified bound or it does not. The certificate type is derived from the mathematics; the threshold is a theorem. There is no room for a hospital in Boston and a hospital in Seattle to disagree about what "close enough" means, because "close enough" is defined by the certificate, and the certificate is checked against a computable quantity grounded in probability theory.

For these systems, the compiler approaches a **completeness system**. Given the right gap taxonomy — which the mathematics largely determines — Theorem N (§8.4) becomes close to a correctness guarantee: if a required obligation is unmet, the compiler will refuse the permission. The domain expert's job is to identify the gaps; the mathematics defines what satisfies them.

**Policy-grounded systems.** In clinical deployment, hiring decisions, content moderation, fraud detection, and credit scoring, the gap taxonomy can be named and principled, but the satisfaction conditions are human choices. `clinical_utility_gap` exists and corresponds to a real failure mode. But PPV ≥ 0.20 before rollout is not a theorem — it is a judgment call that reasonable clinicians can disagree about. The blast radius categories, the freshness window, the population scope — all of these are engineering inputs, not derivations.

For these systems, the compiler does something different: it **separates policy from enforcement**, and it **forces policy to be compiler-processable**. These are two distinct contributions, both addressing failure modes that are common in practice.

### 0.2 The two failure modes the framework addresses

**Failure mode 1: missing policy.** The deployment proceeds on informal judgment. No one wrote down what evidence was required before rollout. Decisions are made case-by-case, by whoever is available, with no record of the reasoning. This is the most common failure mode. The compiler addresses it structurally: you cannot compile without a profile. The profile must exist before any deployment decision is made.

**Failure mode 2: underspecified policy.** A policy exists — "we require adequate clinical validation" — but it is too vague to enforce. No threshold, no scope, no expiry, no named obligation. The same policy can be interpreted to approve or to refuse any specific case, depending on who reads it and when. The compiler addresses this through the detail contract registry: tokens must satisfy registered schemas with concrete semantic checks. "Adequate" is not a valid semantic check. PPV ≥ 0.20 at blast_radius=notification with sample_size ≥ 1000 is. The framework specifies what a compiler-processable policy looks like, and rejects anything that does not meet that specification.

Both failure modes are present in the Epic Sepsis Model case. There was no explicit policy requiring operating-point utility validation before rollout. And had such a policy existed in prose, it would likely have been too vague to mechanically enforce. The model had a published AUC; clinical utility evidence was never required; deployment proceeded.

### 0.3 Separation of policy and enforcement

In most organizations, the team that decides what evidence is sufficient is the same team that decides whether a specific deployment has it. These are not separated structurally. A senior researcher who championed the model is unlikely to apply a strict utility standard at deployment time. A team under deadline pressure will satisfy the informal standard more loosely than the same team with no deadline. The standard drifts; the enforcement is inconsistent; the record is incomplete.

The compiler makes this separation structural. The profile is the policy — written down, versioned, reviewed by a separate governance process, immutable once issued. The compiler is the enforcer — it checks the profile against the presented evidence, and cannot be persuaded, fatigued, or deadline-pressured. The same profile, applied to the same evidence, produces the same output every time.

This is the same separation that TLA+ enforces for distributed systems. TLA+ does not tell AWS what invariants DynamoDB should maintain, and it does not tell your company what invariants your internal queue should maintain. These are different systems with different requirements and neither is canonically correct. What TLA+ provides is that once the invariants are written down, violations are caught mechanically, across all reachable states, without depending on the reviewer who happened to be on call. The discipline is in the writing-down and the mechanical enforcement — not in the derivation of the invariants.

This paper makes the same move for approximate consequential systems. The profile is the invariant. The compiler is the checker. The domain expert writes the profile; the compiler ensures it is not accidentally violated. The contribution is enforcement, not wisdom.

### 0.4 Compiler-processable policy as a specification language

There is a third contribution that follows from the second failure mode. By requiring that policy be compiler-processable, the framework also *specifies what a well-formed policy looks like*. This is not obvious in advance.

A compiler-processable policy for a clinical deployment must answer:
- Which gaps are required at which permission levels, for which action classes?
- What does a valid token for each gap look like — what fields, what semantic checks, what scope rules?
- What are the provenance requirements — which (claim, candidate, context) tuple does the token cover?
- What is the expiry — how long is the evidence live before a revalidation is required?
- What are the detail contracts — what is the PPV floor for auto_order vs. notification blast radius?

Most organizations have not answered these questions. The questions are not asked because there is no system that requires answers in this form. The compiler is that system. The profile and detail contract registries are the specification language. Writing a valid profile is an act of policy clarification that most governance processes do not currently perform.

The framework does not tell you the right answers. It tells you which questions must have answers before a deployment can be authorized.

### 0.5 The generalization claim

The empirical claim is not that any particular profile is correct. It is that profiles designed on a small set of motivating cases generalize to held-out cases without overfitting — and that this generalization has a formal basis.

For mathematically grounded systems, generalization is expected because the gap taxonomy is derived from the mathematics, not from the cases. The cases are witnesses to a structure that exists independently of them.

For policy-grounded systems, generalization is expected for a different reason: if the profile is *grounded* — every requirement maps to a named, domain-recognizable failure mode — then it will not block cases where that failure mode is genuinely mitigated, and it will block cases where it is genuinely present. A grounded profile does not overfit to its training cases because it is not fitted to them at all; it is fitted to the failure modes, which are properties of the domain, not of the specific cases that motivated the profile design.

The formal basis is Lemma M and Corollary M1 (§8.4): permission is Lipschitz in the profile with constant 1. A profile that differs from the intended profile by `k` entries cannot produce an output more than `k` permission steps wrong. The profile designer does not need to get the boundary exactly right — they need to get it approximately right. The stability of the output under small profile perturbations is the formal analog of the TLA+ observation that invariants do not need to anticipate every failure mode, only the known load-bearing ones.

Two benchmarks test this claim. MED-001 (prospective) tests within-domain generalization: Profile v2 was designed with one motivating failure (Epic/Wong et al. 2021) in mind and transfers without modification to 11 pre-registered oracle cases and 9 adversarial cases. CASE-LIB-001 (retrospective) tests cross-domain generalization: a four-gap Tier 1 profile — designed on the cross-domain intersection of known failure modes, not on any of the 16 cases — blocks all 16 documented harms across medical, criminal justice, employment, autonomous systems, and government benefits. Neither the within-domain cases (MED-001) nor the cross-domain cases (CASE-LIB-001) were used to design the profiles tested against them. The profiles are surgical: they block cases where the targeted failure modes are present and pass cases where they are genuinely mitigated.

### 0.6 The 4-cell picture

The medical benchmark populates a 2×2 grid: (compiler decision) × (hindsight outcome). Each cell is a triplet: (compiler outcome, deployment decision, actual outcome in hindsight).

```
                         Hindsight: harm        Hindsight: benefit
Compiler: ALR            (ALR, deployed, harm)  (ALR, deployed, benefit)
Compiler: < ALR          (<ALR, blocked, harm-  (<ALR, blocked, benefit-
                          prevented)             foregone)
```

The Epic case under Profile v1 gives **(ALR, deployed, harm)**: the compiler would have authorized rollout; the model was deployed; harm followed. This is the falsification of Profile v1.

Profile v2 on the same evidence gives **(<ALR, blocked, harm-prevented)**: the compiler refuses rollout authority; deployment is blocked; harm is averted. This is the correction.

The two remaining cells are not populated by this benchmark. **(ALR, deployed, benefit)** requires a prospectively validated clinical alert where deployment genuinely helped and the compiler would have authorized it — the true positive. **(<ALR, blocked, benefit-foregone)** is the over-refusal failure mode: a model that would have helped, blocked by a profile that was too conservative. This is the hardest cell to find honestly because it requires knowing, in hindsight, both that the deployment would have been beneficial and that the compiler's refusal was the reason it did not happen.

**The benefit-foregone cell as a named limitation.** The closest available candidate is CHARTwatch, a general internal medicine early warning system deployed prospectively at Toronto General Hospital (Tonekaboni et al. 2022, *Frontiers in Digital Health*). CHARTwatch was designed with an operating threshold explicitly chosen to achieve PPV = 0.40, sensitivity = 0.77. Under Profile v2, a model with PPV = 0.40 at the deployed threshold would produce a valid `clinical_utility_token` (PPV ≥ 0.15 floor), a bounded `distribution_shift_gap` from the local deployment cohort, and would compile to ALR. The compiler would have authorized it. CHARTwatch therefore occupies **(ALR, deployed, benefit)** under Profile v2, not the benefit-foregone cell.

To populate **(< ALR, blocked, benefit-foregone)** honestly requires a model with: (a) PPV between 0.12 and 0.15 at the deployed threshold, (b) genuine prospective evidence of clinical benefit, and (c) a counterfactual in which Profile v2's `clinical_utility_gap` requirement was the specific barrier to deployment. No published case in the literature meets all three conditions. The Epic model has PPV = 0.12 and documented harm, not benefit. Models with PPV slightly above the floor — in the 0.15–0.20 range — exist in the breast cancer screening literature (Lunit INSIGHT MMG: PPV = 0.221 at deployed operating point; Mia/Kheiron: PPV = 0.20) but these are radiology screening systems with a different blast radius profile than ICU alerting, and no prospective harm-benefit data is available for the counterfactual deployment scenario.

This is a genuine limitation. Profile v2's PPV floor of 0.15 for `blast_radius=notification` is a design parameter, not a theorem. A model with PPV = 0.14 and strong sensitivity might, in a specific care context, produce net clinical benefit despite failing the floor. The framework's response to this objection is structural rather than empirical: the floor is explicit and auditable, so an institution that disagrees can change it. An informal governance process that applies no floor at all cannot be audited, overridden, or held accountable. The framework does not claim the floor is correct. It claims that having a named, enforceable floor is better than having no floor — and that the correct floor is a question that belongs in the profile governance process, not in the model evaluation process.

**Both cells matter.** The paper does not claim to fill the benefit-foregone cell here. It claims that the framework makes filling it possible: the profile is explicit, so the question of whether a refusal was justified is answerable in principle. An informal governance decision cannot be retrospectively audited, because the standard it applied was never written down.

### 0.7 Empirical calibration of Profile V1 against published standards

Profile V1 was submitted to two independent checks: a web search against publicly available hospital and regulatory guidelines, and an LLM query asking whether V1 represents a reasonable clinical AI deployment policy. The LLM is not the authority. The FDA and NHS are. The LLM is the retrieval mechanism that surfaces authoritative sources. This operationalizes the "ask an LLM" calibration device described in §0.3.

**What V1 requires and does not require.** V1 requires AUC bounded, model specification bounded, calibration bounded, blast radius bounded, and freshness bounded. V1 does not require operating-point clinical utility evidence — PPV and sensitivity at the deployment threshold — nor local population validation. These are not edge cases. They are the two gaps V2 adds.

**The LLM verdict.** V1 is defensible as a baseline — it would pass a cursory IRB review — but it would not satisfy a rigorous clinical AI governance committee. The two omissions are precisely the two gaps V2 adds. The LLM independently named the Epic Sepsis Model as the canonical failure case without being prompted.

**Regulatory sources.** Two authoritative sources were found.

*FDA Draft Guidance, January 2025 (AI-Enabled Device Software Functions, docket FDA-2024-D-4488).* For binary diagnostic outputs, the FDA requires sensitivity, specificity, PPV, and NPV with pre-specified acceptance criteria and 95% confidence intervals. AUC and ROC are supporting context for continuous-score outputs; they are not the primary authorization basis for binary decision devices. Multi-site validation at three or more geographically diverse US sites is recommended.

*NHS RCR "AI Deployment Fundamentals for Medical Imaging" (November 2024).* Shadow-mode testing on the local population is mandatory before go-live (§4.21–4.22). Pre-defined acceptance criteria including sensitivity and specificity are required before procurement (§2.10). An ongoing post-implementation evaluation plan is required before deployment (§2.13).

**V1 against those standards.** V1 satisfies the AMA/AMIA vague "clinical validation" standard. V1 fails the FDA standard: no operating-point PPV requirement, no multi-site validation. V1 fails the NHS standard: no shadow mode, no local population acceptance criteria, no monitoring plan.

**Whether V2 faithfully encodes FDA and NHS.** V2 adds `clinical_utility_gap` and `distribution_shift_gap`. This covers the FDA pre-clearance evidence standard and the population-specific validation obligation. But V2 is still missing two deployment-phase obligations that NHS RCR treats as minimum standards: `shadow_mode_validation_gap` (local population shadow-mode test before go-live, NHS §4.21–4.22) and `post_market_monitoring_gap` (ongoing evaluation plan required before deployment, NHS §2.13; FDA §XI for PMA devices). These are not V1's omissions — they are V2's.

**Profile V3.** Profile V3 adds these two gaps. It is not invented — it is derived directly from the regulatory text.

**Compiler results across V1, V2, and V3.**

| Case | Evidence | V1 | V2 | V3 |
|------|----------|----|----|-----|
| P1 | Core only — Epic pattern | ALR | AEX | AEX |
| P2 | V2-complete (adds utility + shift) | ALR | ALR | AEX |
| P3 | V3-complete (all gaps bounded) | ALR | ALR | ALR |
| P6 | Missing shadow mode only | ALR | ALR | AEX |
| P7 | Missing monitoring plan only | ALR | ALR | AEX |

Three things this shows. First, V1→V2 catches the Epic failure: any case missing clinical utility or distribution shift evidence drops from ALR to AEX. Second, V2→V3 catches the deployment-phase gap: a model with full pre-clearance evidence but no shadow mode or monitoring plan drops from ALR to AEX under V3. Third, V3 is not over-refusal: fully evidenced cases (P3) still reach ALR under all three profiles.

**Counterfactual cost of V2: would it block everything?** A skeptical reviewer can ask whether Profile v2 is so restrictive that it would block most real deployments, leaving the framework with no practical authorization pathway. The available evidence suggests it would not. The literature on deployed clinical AI systems with reported operating-point metrics is sparse — only a handful of prospective deployments publish PPV at the deployed threshold rather than AUC — but the cases that do exist distribute across a wide range. CHARTwatch (Toronto General, GIM ward deterioration) was designed to PPV = 0.40. Google's diabetic retinopathy screening system deployed prospectively in Thailand achieved PPV = 0.79 at its operating point. The Lunit INSIGHT MMG breast cancer screening system achieved PPV = 0.221 in real-world deployment. All three would pass the v2 `clinical_utility_gap` floor of PPV ≥ 0.15 for `blast_radius=notification`. The Epic Sepsis Model at PPV = 0.12 is the failure case, not the median case.

The harder empirical question is what fraction of *candidate* deployments — models under evaluation that have not yet been deployed — would pass the v2 floor. The literature does not answer this directly: systematic reviews report AUC distributions (Nagendran et al. 2020 *BMJ*: median AUC 0.77 across 82 clinical AI studies) but rarely report PPV at a specified operating threshold. The PLOS Digital Health 2024 meta-analysis of 50 AI-CDSS studies found only 24% involved prospective deployment; operating-point PPV was not consistently reported in the remainder. This absence is itself evidence for the framework's central claim: the clinical AI literature systematically under-reports the metrics that matter for deployment authorization.

The calibration conclusion is therefore: Profile v2 would not block well-evidenced, utility-aware deployments. It would block deployments — like Epic's — that were approved without ever requiring operating-point utility evidence. The fraction of the latter in the current deployment landscape is unknown precisely because no framework required that evidence to be recorded.

**What this validates.** The calibration exercise validates two claims from the abstract. It validates the generalization claim: V2 was designed on the Epic failure, and the V1→V2 transition correctly handles all held-out cases without overfitting. It also validates the compiler-processable policy claim: the exercise of writing V2 in compiler-processable form forced the question of what FDA and NHS actually require, which revealed that V2 was incomplete, producing V3. The incompleteness of V2 was not visible from the cases that motivated it. It was visible only when the profile was matched against regulatory text — which the framework made tractable by demanding that policy be explicit and machine-checkable.

---

## 1. Approximate Consequential Systems

A system is **approximate consequential** when four conditions hold.

1. The ideal output is unavailable at decision time.
2. The system acts on an approximation.
3. A downstream system treats the output as permission.
4. Validity depends on context that can change.

Examples include fraud holds, marketplace policy changes, agent plans, medical triage signals, security responses, and experiment readouts.

Sorting, exact arithmetic, and authorized deterministic writes are outside the class. They may be important. They do not need this compiler.

The recurring failure is **evidence laundering**.

- A score becomes an action certificate.
- A token for one candidate is reused for another.
- A fresh primary artifact hides a stale dependency.
- A local metric win becomes rollout authority.

The compiler prevents these promotions. It does not make weak evidence strong. It gives weak evidence a weak license.

---

## 2. Judgment and Compiler

The compiler emits judgments of the form:

```text
Γ ⊢ z : p until ε
```

where:

- `Γ` is the proof context;
- `z` is the candidate claim, result, or action;
- `p` is the emitted permission or control outcome;
- `ε` is the expiry condition.

The caller may request a permission. The compiler ignores that request as evidence. It emits the greatest permission supported by the context.

The compiler checks structural admissibility. It checks membership, gaps, profiles, proof tokens, provenance, scope, allowed use, authority, expiry, runtime context, negative controls, and composition.

It does not check whether a domain certifier is scientifically correct. A valid token can still be wrong if the certifier lied, used bad science, or certified the wrong ideal object. That is outside the theorem. It is inside the trusted computing base.

This matters for inference. A certificate can prove that an approximation is close to the posterior of the supplied model. That does not prove that the supplied model is the right model for the world. The compiler needs separate obligations for approximation error and model-specification error.

---

## 3. Proof Context

```text
Γ = (
  membership,
  claim,
  candidate,
  context,
  scope,
  claim_gaps,
  gap_taxonomy_version,
  gap_profile_version,
  proof_tokens,
  proof_token_provenance,
  detail_contract_registry_version,
  expiry,
  allowed_use,
  disallowed_use,
  derivation,
  authority,
  runtime_context,
  audit
)
```

The audit field explains the result. The other fields constrain it.

---

## 4. Trust Boundary

The soundness claim is not absolute. It is relative to a named trusted computing base.

| TCB component | Must guarantee | Attack excluded when correct |
|---|---|---|
| Compiler implementation | The order, meet, search, runtime, composition, decomposition, and normalization rules are implemented as specified. | A bug promotes permission. |
| Membership classifier | `IN_CLASS` and out-of-class reasons are correct for the candidate use. | An out-of-class system enters the compiler as in-class. |
| Adapter | Claim identity, context identity, candidate identity, and class assignment are deterministic and conservative. | Claim relabeling, context erasure, and class shopping. |
| Gap taxonomy | The taxonomy contains the obligation types needed for the class. | A required obligation is not expressible. |
| Gap induction | Every applicable obligation is induced or marked not applicable by a valid artifact. | A load-bearing gap is silently omitted. |
| Profile registry | Profiles are well formed, versioned, audited, and immutable for issued envelopes. | Strong permissions become easier without a visible profile change. |
| Artifact registry | Justification artifacts are live, typed, scoped, and unexpired. | Free text or stale artifacts discharge obligations. |
| Certifiers | Tokens report correct claim, scope, status, expiry, and contract data. | False domain evidence enters as valid evidence. |
| Detail-contract registry | Token schemas and semantic checks are versioned and immutable for issued envelopes. | Malformed payloads pass as evidence. |
| Token registry | Token liveness, revocation, and status are correct at runtime. | Revoked or stale tokens continue to close gaps. |
| Provenance writer | Provenance binds exactly `(τ,g,c,z,x)`. | Tokens are reused across gaps, claims, candidates, or contexts. |
| Authority source | Permission ceilings and rollback capabilities are live and complete. | The compiler authorizes action outside delegation. |
| Runtime context source | Values required by expiry, registries, and authority checks are current. | Missing runtime facts become permission. |

The compiler only names the TCB. It does not remove it. 

Things outside the trust boundary including request permissions, free text, token types, and the approximate output are not trusted.

A benchmark can therefore produce two different kinds of result. It can falsify the compiler if an unsupported permission is emitted. Or it can falsify the taxonomy/profile if a real obligation is not expressible or not required. The first probabilistic-inference benchmark produced the second kind of result.

---

## 5. Permission Algebra

The compiler emits one continuation outcome.

| Symbol | Outcome                              |
| ------ | ------------------------------------ |
| `OOC`  | `OUT_OF_CLASS`                       |
| `EXP`  | `EXPIRED`                            |
| `REF`  | `REFUSED`                            |
| `UNS`  | `UNSUPPORTED`                        |
| `ETA`  | `ESCALATE_TRADEOFF_OUT_OF_AUTHORITY` |
| `ESC`  | `ESCALATE`                           |
| `ROL`  | `ROLLBACK`                           |
| `DIA`  | `DIAGNOSTIC_ONLY`                    |
| `REV`  | `RECOMMEND_HUMAN_REVIEW`             |
| `AEX`  | `APPROVE_EXPERIMENT`                 |
| `ALR`  | `APPROVE_LIMITED_ROLLOUT`            |
| `AAA`  | `APPROVE_AUTOMATIC_ACTION`           |

The total order is:

```text
OOC ≤ EXP ≤ REF ≤ UNS ≤ ETA ≤ ESC ≤ ROL ≤ DIA ≤ REV ≤ AEX ≤ ALR ≤ AAA
```

Lower means more restrictive.

`ETA`, `ESC`, and `ROL` are control outcomes. They live in the same order because the compiler emits one continuation. A positive permission cannot dominate a live control obligation.

The meet is minimum in this order.

```text
meet(p,q) = min(p,q)
meet_n(L) = min(L), 
    for finite nonempty list L
    meet_n is undefined on the empty list
```

---

## 6. Membership

```text
PermissionOutcome = Classified(reason) | Operational(outcome: Permission)
```

Membership values are:

```text
IN_CLASS
OUT_OF_CLASS_EXACT
OUT_OF_CLASS_AUTHORIZED_DETERMINISTIC_WRITE
OUT_OF_CLASS_NO_CONSEQUENTIAL_USE
OUT_OF_CLASS_OTHER
```

Every out-of-class reason projects to `OOC`. The reason is kept for audit. It does not affect the order.

Fake proof tokens cannot promote an out-of-class system. Membership is checked before token evaluation.

---

## 7. Claims, Candidates, Contexts, and Adapters

```text
c = (claim_id, claim_class, statement, intended_use)
z = (candidate_id, payload, candidate_type)
x = (context_id, context_fingerprint, metadata)
c ← induce_claim(A,κ,z,x)
```

An adapter maps an approximate output into a claim class and identities. It must satisfy five conditions.

1. **Determinism.** Equal inputs produce equal outputs.
2. **Identity binding.** Claim identity binds output, class, candidate, and context.
3. **Profile coverage.** Each mandatory gap type is induced or validly marked not applicable.
4. **Context sensitivity.** Load-bearing context changes affect claim identity, gap identity, or expiry.
5. **Profile-conservative class assignment.** The adapter cannot choose a looser compatible class.

### 7.1 Class assignment

Let `ReqΦ(κ,h,p)` be the requirement imposed by profile `Φ` for class `κ`, gap type `h`, and permission `p`.

```text
OPEN_ALLOWED < BOUNDED_REQUIRED < CLOSED_REQUIRED
```

Define a preorder on classes:

```text
κ₁ ≼Φ κ₂    iff    ∀h,p. ReqΦ(κ₁,h,p) ≥ ReqΦ(κ₂,h,p)
```

Read `κ₁ ≼Φ κ₂` as: `κ₁` is no looser than `κ₂`.

Let `K(A,z,x,u)` be the set of classes compatible with approximate output `A`, candidate `z`, context `x`, and intended use `u`.

The assigned class `κ` must satisfy:

```text
∀κ' ∈ K(A,z,x,u).  κ ≼Φ κ'
```

unless excluding `κ'` is justified by a valid `CheckableJustification`.

If no conservative class exists, the adapter fails closed and records `CLASS_AMBIGUITY`.

---

## 8. Gaps and Profiles

A gap is a proof obligation.

```text
g = (gap_id, gap_type, status, metadata)
status ∈ {OPEN, BOUNDED, CLOSED}
```

Every induced gap starts `OPEN`.

Representative gap types include:

```text
approximation_gap
posterior_divergence_gap
model_specification_gap
calibration_gap
proxy_gap
interference_gap
authority_gap
freshness_gap
blast_radius_gap
coupling_gap
```

### 8.1 Approximation gap versus model-specification gap

The inference benchmark exposed a distinction that the taxonomy must represent explicitly.

`posterior_divergence_gap` or `approximation_gap` asks whether the computed object is close to the ideal object under the supplied model.

`model_specification_gap` asks whether the supplied model is adequate for the real target of action.

These are not the same gap.

```text
approximation certificate:
  approximate posterior is close to assumed posterior

model-specification certificate:
  assumed posterior is close enough to the data-generating or action-relevant target
```

A compiler may license diagnostic use from an approximation certificate alone. It should not license rollout authority against the world from that certificate alone unless the profile also requires `model_specification_gap` to be at least `BOUNDED`, or explicitly routes the decision to review/escalation.

For inference profiles, `ALR` and `AAA` require `model_specification_gap` to be at least `BOUNDED_REQUIRED` unless the claim is explicitly scoped to the supplied model rather than to the external world.

### 8.2 Gap induction completeness

Let `Θ_v` be a versioned gap taxonomy.

`induce_gaps(κ,z,x,u,Θ_v)` is complete for profile version `Φ_v` when every applicable required obligation is induced or validly discharged:

```text
Applicable(Θ_v,κ,z,x,u,h) ∧ RequiredBy(Φ_v,κ,h,p)
  ⇒  h ∈ types(G) ∨ ValidNA(h,c,z,x,ArtifactRegistry)
```

This is a TCB condition. The compiler cannot require evidence for a gap type the taxonomy does not contain. It also cannot close a gap that was not induced.

Failure is closed. If `Φ_v` requires `h`, and `G` contains no gap of type `h`, and there is no valid not-applicable artifact, then every permission requiring `h` is unsatisfied.

### 8.3 Profiles

A profile maps classes and permissions to gap requirements.

```text
Φ_v : (κ,p) ↦ PermissionRequirementProfile
```

| Requirement level | Satisfied by |
|---|---|
| `OPEN_ALLOWED` | `OPEN`, `BOUNDED`, or `CLOSED` |
| `BOUNDED_REQUIRED` | `BOUNDED` or `CLOSED` |
| `CLOSED_REQUIRED` | `CLOSED` |

A profile is well formed when stronger permissions never require weaker evidence.

For `p_strong > p_weak`:

```text
required_status(κ,h,p_strong,Φ_v)
  ≥ required_status(κ,h,p_weak,Φ_v)
```

or `p_strong` marks `h` not applicable by a valid `CheckableJustification`.

A `CheckableJustification` is valid only if the artifact registry confirms that the artifact exists, has the correct type, covers the gap type, is unexpired, and is scoped to the claim and candidate.

Free text is not a valid justification.

For world-facing inference claims, the profile must distinguish at least:

```text
posterior_divergence_gap
model_specification_gap
```

A token that bounds the first does not bound the second by implication. A profile that allows `ALR` with open model specification is too weak for action authority unless the intended use is explicitly diagnostic or model-internal.

---

## 8.4 Profile Generalization

The compiler enforces whatever profile it receives. This section characterizes when a profile is *well-grounded* — a property that supports the claim that profiles designed on a small set of motivating cases transfer to held-out cases without overfitting.

### 8.4.1 Grounded profiles

A gap type `h` is **domain-grounded** for class `κ` under profile `Φ` when there exists a named, domain-recognizable failure mode `F(h,κ)` such that:

```text
EffΓ(h) = OPEN  ⇒  F(h,κ) is an unmitigated risk for action authority p
```

That is: every gap requirement at every permission level corresponds to a real thing that can go wrong if the gap is left open. The requirement is not defensive padding; it is a traceable obligation.

A profile `Φ` is **grounded** for class `κ` when every `BOUNDED_REQUIRED` or `CLOSED_REQUIRED` entry in `Φ(κ,·)` is domain-grounded.

Groundedness is a TCB condition, not a compiler check. The profile designer asserts it; domain review confirms it; the compiler enforces it. The medical profile v2 is grounded: `clinical_utility_gap` maps to the failure mode *model deployed without operating-point validation* (Epic/Wong et al. 2021); `distribution_shift_gap` maps to *evidence collected on a different population than the deployment population*.

### 8.4.2 Sensitivity of permission to profile perturbation

Let `Φ` and `Φ'` be two profiles that differ on a single gap requirement: for some `(κ,h,p)`,

```text
ReqΦ'(κ,h,p) = ReqΦ(κ,h,p) + 1
```

where the ordering is `OPEN_ALLOWED=0 < BOUNDED_REQUIRED=1 < CLOSED_REQUIRED=2`, and all other entries are equal.

Let `Compile(Γ,Φ)` denote the emitted permission under profile `Φ` for proof context `Γ`.

**Lemma M. Unit profile tightening bounds permission change.**

```text
Compile(Γ,Φ') ≤ Compile(Γ,Φ)
Compile(Γ,Φ') ≥ Compile(Γ,Φ) - 1
```

where the difference is measured in steps of the permission order.

*Proof sketch.* The upper bound follows from Lemma 4 (profile tightening cannot promote). For the lower bound: the single changed requirement can only block one additional permission level `p`. All permission levels below `p` are unaffected by the change, because the well-formedness condition on profiles ensures that `p' < p` requires evidence no stronger than `p` requires, so the changed entry does not constrain `p'`. The greatest satisfiable permission therefore drops by at most one step. ∎

**Corollary M1. Permission is Lipschitz in the profile under the pointwise distance.**

Let `d(Φ,Φ') = |{(κ,h,p) : ReqΦ(κ,h,p) ≠ ReqΦ'(κ,h,p)}|`.

Then for any proof context `Γ`:

```text
|Compile(Γ,Φ') - Compile(Γ,Φ)| ≤ d(Φ,Φ')
```

A profile that differs from a correct profile by `k` entries cannot produce an output more than `k` steps wrong. Small profile errors produce small permission errors.

### 8.4.3 The generalization theorem

**Theorem N. Grounded profiles generalize across held-out cases.**

Let `Φ` be a grounded profile for class `κ`. Let `C_train` be the set of cases used to design `Φ`, and let `C_test` be any held-out set of cases in the same class.

Then for any `Γ` induced from a case in `C_test`:

```text
Compile(Γ,Φ) = OOC                    if Γ is out of class
Compile(Γ,Φ) ≤ p                      for every p such that F(h,κ) is an
                                        unmitigated risk and EffΓ(h) = OPEN
Compile(Γ,Φ) = AAA                    only if all closed-required gaps are
                                        closed and all bounded-required gaps
                                        are at least bounded
```

*Proof sketch.* The first and third conditions follow directly from the compiler algorithm (Steps 1 and 8) and the definition of profile satisfiability. The second condition follows from groundedness: if gap `h` is domain-grounded and `EffΓ(h) = OPEN`, then the profile requires `h` to be at least `BOUNDED_REQUIRED` before any permission `p` that names `F(h,κ)` as a load-bearing obligation. The descending search in Step 8 will not reach `p` with an open required gap. ∎

The theorem says that a grounded profile cannot silently authorize an action when a known failure mode is unmitigated. It can only fail in one direction: if the profile is *missing* a gap type that corresponds to a real failure mode, the compiler will emit too strong a permission. This is the taxonomy completeness failure mode, already encountered in PGM-001 and MED-001. It is caught at the profile/taxonomy boundary, not inside the compiler — which is the intended failure mode of the framework.

### 8.4.4 Overfitting and the surgical property

A profile is **overfit** to `C_train` if it contains requirements that are not domain-grounded — requirements added to make specific training cases pass or fail rather than to represent real failure modes. An overfit profile will generalize poorly: it will block well-evidenced held-out cases that happen to pattern-match the training refusals.

Groundedness is the guard against overfitting. A requirement that cannot be pointed at a named failure mode is not a grounded requirement; it should be removed or replaced with one that is.

The **surgical property** of a profile upgrade is:

```text
Tightens(Φ₂,Φ₁)  ∧  ∀h ∈ new_requirements(Φ₂). domain-grounded(h,κ)
  ⇒  Φ₂ blocks exactly the cases where the new failure mode is unmitigated
     and does not additionally block cases where it is mitigated
```

Profile v1 → v2 in the medical benchmark satisfies this: adding `clinical_utility_gap` as `BOUNDED_REQUIRED` at ALR blocks deployments with no utility evidence (the Epic failure mode) and does not block deployments that have a valid clinical utility token. The oracle suite confirms the surgical property empirically: fully-evidenced cases still reach ALR; evidence-partial cases drop to AEX; misspecified models stay at REV.

---

## 9. Proof Tokens and Provenance

A proof token is a typed witness.

```text
τ = (
  proof_token_id,
  token_type,
  token_fingerprint,
  detail_contract_id,
  detail_contract_hash,
  status,
  closes_gaps,
  bounds_gaps,
  scope,
  expiry,
  details
)
```

Token evaluation uses live-registry semantics. Registry unavailability fails closed.

```text
TokenSupports(τ,g,CLOSED)
  iff τ.status=VALID ∧ Live(τ.expiry,ρ) ∧ g.gap_id ∈ τ.closes_gaps

TokenSupports(τ,g,BOUNDED)
  iff τ.status=VALID ∧ Live(τ.expiry,ρ) ∧ g.gap_id ∈ τ.bounds_gaps
```

A token supports a gap only with exact provenance.

```text
Prov(τ,g,c,z,x)
  iff ∃r ∈ Π such that r matches (τ,g,c,z,x) on all five ids
```

No provenance, no proof.

```text
EffΓ(g) = CLOSED
  if ∃τ. TokenSupports(τ,g,CLOSED) ∧ Prov(τ,g,c,z,x)

EffΓ(g) = BOUNDED
  if ∃τ. TokenSupports(τ,g,BOUNDED) ∧ Prov(τ,g,c,z,x)
     and no CLOSED witness exists

EffΓ(g) = OPEN
  otherwise
```

### 9.1 Detail contracts

A token type is not evidence by name. Its payload must satisfy a registered detail contract.

Let `Σ_v` be the versioned detail-contract registry.

```text
σ = (
  detail_contract_id,
  token_type,
  schema_fingerprint,
  required_fields,
  semantic_checks,
  artifact_dependencies,
  scope_rules,
  expiry_rules
)
```

`detail_contract_ok(τ,ρ,Σ_v)` holds only if all seven checks pass.

1. `Σ_v` contains `τ.detail_contract_id`.
2. The registry fingerprint equals `τ.detail_contract_hash`.
3. The contract token type equals `τ.token_type`.
4. `τ.details` satisfies the registered schema.
5. Every semantic check passes under `ρ`.
6. Every artifact dependency is live, typed, scoped to `(c,z,x)`, and unexpired.
7. Token scope and expiry are no wider than the contract permits.

Unknown contracts fail closed. Schema mismatch fails closed. Failed semantic checks fail closed. Stale dependencies fail closed. Free text inside `details` has no force unless the contract assigns it force.

The semantic checks are the active adversarial surface. They must live in the registered contract and follow the registry versioning discipline in §10.

---

## 10. Versioning and Immutability

A compile fixes three registry versions.

```text
Θ_v = gap taxonomy version
Φ_v = gap profile version
Σ_v = detail-contract registry version
```

The emitted judgment records version ids and hashes. Runtime revalidation uses the recorded versions. It does not substitute newer versions.

### 10.1 Taxonomy versioning

Any taxonomy change creates a new `Θ_v`. This includes adding a gap type, removing a gap type, changing applicability predicates, changing not-applicable rules, or changing gap metadata semantics.

Gap identity includes the taxonomy version.

```text
gap_id = H(Θ_v, claim_id, candidate_id, context_id, gap_type, gap_parameters)
```

A taxonomy shift changes gap identity. Tokens minted under the old taxonomy do not close gaps induced under the new taxonomy unless a new compile creates new provenance.

### 10.2 Profile versioning

Any profile change creates a new `Φ_v`. There are no in-place edits after a profile version has issued an envelope.

Profile changes are ordered pointwise.

```text
Tightens(Φ₂,Φ₁)
  iff ∀κ,h,p. ReqΦ₂(κ,h,p) ≥ ReqΦ₁(κ,h,p)
```

Tightening may reduce permission. It may not raise it.

A tightening cannot replace a required status with `NotApplicable`. A `NotApplicable` entry may only be preserved or narrowed by a valid `CheckableJustification`.

Relaxation can make a fresh compile stronger. It is therefore a governance event. Every relaxation records a new version, author, reason, diff, effective time, and audit record.

Existing envelopes are not upgraded by relaxation. A decision under relaxed `Φ_{v+1}` is a new judgment.

### 10.3 Detail-contract versioning

Detail contracts are immutable per content. Any schema change, semantic-check change, artifact-dependency change, scope-rule change, or expiry-rule change creates a new contract id.

`Σ_v` is determined by the set of `(detail_contract_id, detail_contract_hash)` pairs in the registry. Any add, remove, or replacement creates a new `Σ_v`. A content change therefore creates both a new contract id and a new registry version.

Issued envelopes record the contract id and hash through the token. Runtime does not reinterpret an old token under a new contract.

### 10.4 Envelope immutability

An emitted envelope is immutable.

Runtime can only continue it at the same or lower permission. New evidence requires a new compile. A refreshed context requires a new compile. A changed authority envelope requires a new compile. A different `Θ_v`, `Φ_v`, or `Σ_v` requires a new compile.

A new compile may emit a stronger judgment. Runtime may not.

---

## 11. Expiry, Scope, Use, Authority, and Negative Controls

Expiry is evaluated against runtime context `ρ`.

```text
Expired(ε,ρ)
  iff ε.expired=true
   or now(ρ) > ε.expires_at
   or ∃r ∈ ε.expiry_rules. Fires(r,ρ)
```

The runtime context must contain every value required by expiry rules, token registries, detail contracts, and authority checks. Missing dependencies fail closed.

Allowed use narrows permission.

```text
UseOK(u) iff (allowed_use=[] or u ∈ allowed_use) and u ∉ disallowed_use
```

Scope narrows permission.

```text
z ∈ scope
```

Composition intersects allowed use and scope. It unions disallowed use.

Authority sets a ceiling. If evidence supports `AAA` but authority permits at most `AEX`, the compiler records `ETA`. If authority is absent or a human tradeoff is required, it records `ESC`. If a rollback condition fires and rollback capability exists, it records `ROL`. If rollback capability is missing, it records `ESC` and `ROLLBACK_CAPABILITY_MISSING`.

Negative controls are registered pass/fail token types. Examples include placebo slices, pre-period effect checks, shadow outcomes, and known-null detectors.

The class contract names which controls are required. `strict_mode` may be set by the class contract, by an operator flag, or by both when policy requires gated activation.

Under `strict_mode`, a missing, invalid, expired, unprovenanced, or failed required negative control records `NEGCTRL_FAILED`. That forces `REF` into the final meet.

---

## 12. Composition and Decomposition

For `n ≥ 1` envelopes:

```text
permission     = meet_n([Ei.permission])
allowed_use    = ∩_top(Ei.allowed_use)
disallowed_use = ∪(Ei.disallowed_use)
scope          = ∩(Ei.scope)
expiry         = min_expiry(Ei.expiry)
proof_tokens   = ∪(Ei.proof_tokens)
provenance     = ∪(Ei.provenance)
```

Composition cannot widen permission, scope, allowed use, or expiry.

Decomposition cannot upgrade a child.

```text
E_child.permission = meet(E_parent.permission, child_permission_floor)
E_child.scope      ⊆ scope_mapping(E_parent.scope)
E_child.expiry     ≤ E_parent.expiry
```

New evidence may strengthen a child only through a separate compile.

---

## 13. Runtime Revalidation

Runtime revalidation only downgrades.

```text
Runtime(E,ρ).permission = meet_n([E.permission] ∪ D(E,ρ))
```

`D(E,ρ)` is the multiset of downgrading outcomes from live checks. Runtime reruns expiry, token registry, structural, control, authority, and dependency checks.

Runtime does not reinduce membership, claims, gaps, class assignment, profiles, or taxonomy versions.

Two invariants follow.

```text
Runtime(E,ρ).permission ≤ E.permission
Runtime(Runtime(E,ρ),ρ) = Runtime(E,ρ)
```

---

## 14. Compiler Algorithm

**Step 1.** If membership is not `IN_CLASS`, emit `Classified(reason)` and `OOC`. Halt.

**Step 2.** Induce claim `c`.

**Step 3.** Induce gaps `G` under fixed `Θ_v`. Record `Θ_v`, `Φ_v`, and `Σ_v`.

**Step 4.** If `Expired(ε,ρ)`, emit `EXP`. Halt.

**Step 5.** For each token `τ`, check registry status, detail contract, expiry, scope, and provenance. Advance `EffΓ(g)` only through valid witnesses.

**Step 6.** Record structural failures:

```text
PROVENANCE_MISMATCH
ALLOWED_USE_CONFLICT
SCOPE_EMPTY
DERIVATION_INVALID
NEGCTRL_FAILED
RUNTIME_CONTEXT_FAILURE
```

**Step 7.** Record control outcomes from authority, tradeoff, and rollback checks.

**Step 8.** Search positive permissions in descending order.

```text
AAA, ALR, AEX, REV, DIA
```

Return the first permission whose profile exists and whose gap, use, and scope requirements hold.

If none is satisfiable, set `best_positive = UNS`.

**Step 9.** Meet `best_positive` with `REF` if any structural failure exists.

**Step 10.** Meet the result with the meet of control outcomes, if any.

**Step 11.** Emit `Γ ⊢ z : p_final until ε`.

**Step 12.** Record blocking reasons for every stronger denied permission.

---

# Part I — Proofs

## Lemma 1. Meet laws

`meet = min` over a finite total order. Therefore meet is commutative, associative, idempotent, and order independent. `meet_n(L)` is the greatest lower bound of finite nonempty `L`. ∎

## Lemma 2. Profile satisfiability is downward closed

Under a well-formed profile, if `p_strong` is satisfiable by `Eff`, then any profiled `p_weak < p_strong` is satisfiable by `Eff`. Stronger permissions require evidence at least as strong as weaker permissions. ∎

## Lemma 3. Descending search returns the greatest satisfiable positive permission

Step 8 visits positive permissions from strongest to weakest. The first satisfiable permission has no stronger satisfiable predecessor. ∎

## Lemma 4. Profile tightening cannot promote

If `Tightens(Φ₂,Φ₁)`, every requirement under `Φ₂` is at least as strong as the corresponding requirement under `Φ₁`. The greatest satisfiable permission under `Φ₂` is therefore no greater than under `Φ₁`. ∎

## Lemma 5. Class shopping fails closed

The adapter must choose a class no looser than every compatible class, or fail with `CLASS_AMBIGUITY`. Compiling under the assigned class cannot yield a stronger permission by choosing a looser compatible class. ∎

## Lemma 6. Absent required gaps fail closed

If a profile requires gap type `h`, and `G` contains no gap of type `h`, and no valid not-applicable artifact exists, then any permission requiring `h` is unsatisfied. Step 8 returns a lower satisfiable permission or `UNS`. ∎

## Lemma 7. No provenance, no proof

`EffΓ(g)` starts `OPEN`. It advances only through rules that require token support and exact five-id provenance. Therefore any non-open effective status has an explicit witness. ∎

## Lemma 8. Invalid token details do not close gaps

Token support is considered only after registry status, expiry, scope, and `detail_contract_ok` pass. Unknown contracts, schema mismatch, failed semantic checks, stale dependencies, and scope violations cannot advance `EffΓ(g)`. ∎

## Lemma 9. Token reuse cannot launder proof

`Prov(τ,g,c,z,x)` requires equality on token, gap, claim, candidate, and context. A token for a different gap, claim, candidate, or context fails provenance. ∎

## Lemma 10. Composition cannot widen

Permission is a meet. Scope and allowed use are intersections. Disallowed use is a union. Expiry is a minimum. Each output is no wider than its inputs. ∎

## Lemma 11. Decomposition cannot upgrade

`meet(E_parent.permission, child_permission_floor) ≤ E_parent.permission`. Child scope is a subset. Child expiry is no later than parent expiry. ∎

## Lemma 12. Runtime cannot upgrade

`Runtime(E,ρ).permission` is a meet containing `E.permission`. Therefore it is no greater than `E.permission`. ∎

## Lemma 13. Runtime is idempotent under fixed context

Under fixed `ρ`, rerunning the same live checks adds no new downgrading outcomes. Meeting the same finite set again changes nothing. ∎

## Lemma 14. Runtime is monotone under worse context

If `ρ'` has all downgrades of `ρ` and possibly more, then `D(E,ρ) ⊆ D(E,ρ')`. Adding elements to a finite meet preserves or lowers the result. ∎

## Lemma 15. Version changes do not upgrade runtime

Runtime uses recorded `Θ_v`, `Φ_v`, and `Σ_v`. It does not reinduce gaps, substitute profiles, or reinterpret token details. A different version requires a new compile. ∎

---

# Part II — Structural Theorems

## Theorem A. Positive Soundness

Assume in-class membership, live expiry, conforming adapter, profile-conservative class assignment, complete gap induction under fixed `Θ_v`, fixed well-formed `Φ_v`, registered detail-contract conformance under fixed `Σ_v`, complete runtime context, and live-registry semantics.

Then Step 8 returns the greatest satisfiable positive permission.

**Proof.** By Lemmas 2, 3, 6, 7, and 8. ∎

## Theorem B. Non-Promotion

`p_final ≤ best_positive`.

**Proof.** `p_final` is a meet containing `best_positive`. ∎

## Theorem C. Structural Soundness

Under the assumptions of Theorem A, the emitted permission is no stronger than membership, expiry, gap evidence, provenance, scope, allowed use, authority, derivation, runtime context, negative controls, and control obligations jointly support.

**Proof.** Out-of-class membership halts at `OOC`. Expiry halts at `EXP`. Valid tokens advance gaps only with detail-contract conformance and exact provenance. Step 8 gives the greatest positive permission. Structural failures add `REF`. Control obligations add their outcomes. The final meet cannot exceed any constraint. ∎

## Theorem D. Composition Soundness

A composed envelope cannot exceed any component in permission, scope, allowed use, or expiry.

**Proof.** Lemma 10. ∎

## Theorem E. Decomposition Soundness

A child envelope cannot exceed its parent in permission, scope, or expiry. Recomposing children cannot exceed the parent.

**Proof.** Lemmas 10 and 11. ∎

## Theorem F. Runtime Soundness

Runtime revalidation cannot upgrade an issued envelope. It is idempotent under fixed context and monotone under worse context.

**Proof.** Lemmas 12, 13, and 14. ∎

## Theorem G. Anti-Laundering

No stale or downgraded component can be hidden by composition with a fresh component.

**Proof.** Composition takes the meet of component permissions. A fresh component cannot raise a stale component. ∎

## Theorem H. Fake-Token Non-Promotion

Out-of-class membership blocks all token evidence.

**Proof.** Step 1 halts before token evaluation. ∎

## Theorem I. Domain Non-Theorem

Structural soundness does not imply scientific correctness of domain evidence.

**Proof.** The compiler checks token validity, liveness, provenance, scope, expiry, and contract conformance. It does not verify the certifier's science. It also does not turn a certificate about one ideal object into a certificate about another. If a token bounds divergence from an assumed posterior, that does not by itself bound divergence from the true data-generating or action-relevant target. The missing obligation must be represented as a separate gap, such as `model_specification_gap`, and required by the profile before action authority is emitted. ∎

## Theorem J. Class-Shopping Non-Promotion

Under profile-conservative class assignment, a compatible looser class cannot be used to obtain stronger permission.

**Proof.** Lemma 5 gives the assigned class no looser than every compatible class. Theorem A then applies under the assigned class. Meets can only lower the result. ∎

## Theorem K. Profile-Version Non-Upgrade

Runtime cannot upgrade an issued envelope by applying a relaxed profile version.

**Proof.** Runtime uses the recorded `Φ_v`. It does not substitute a later profile. A compile under a relaxed profile is a new judgment. ∎

## Theorem K′. Taxonomy-Version Non-Upgrade

Runtime cannot upgrade an issued envelope by applying a different gap taxonomy version.

**Proof.** Runtime uses the recorded `Θ_v`. It does not reinduce gaps. Gap identity embeds `Θ_v`, so old provenance cannot close newly induced gaps by name alone. ∎

## Theorem L. Detail-Contract Non-Upgrade

Runtime cannot upgrade an issued envelope by interpreting an old token under a newer detail contract.

**Proof.** Runtime uses the recorded contract id and hash. Contract content changes create a new contract id and a new registry version. Reinterpretation requires a new compile. ∎

## Lemma M. Unit profile tightening bounds permission change by one step

Let `Φ` and `Φ'` differ on exactly one entry: for some `(κ,h,p₀)`, `ReqΦ'(κ,h,p₀) = ReqΦ(κ,h,p₀) + 1` (one step tighter in the `OPEN_ALLOWED < BOUNDED_REQUIRED < CLOSED_REQUIRED` order), and all other entries are equal. Then for any proof context `Γ`:

```text
Compile(Γ,Φ') ≤ Compile(Γ,Φ)                  [non-promotion, from Lemma 4]
Compile(Γ,Φ') ≥ Compile(Γ,Φ) - 1              [bounded drop]
```

**Proof of the bounded drop.** Let `p* = Compile(Γ,Φ)`. Suppose `p* < p₀`. Then the changed requirement at `p₀` does not affect any permission `p ≤ p*`, because the well-formedness condition ensures requirements only increase with permission level — the changed entry at `p₀` cannot impose a stricter requirement at any `p < p₀`. The descending search in Step 8 still satisfies `p*` under `Φ'`. So `Compile(Γ,Φ') = p*`.

Suppose `p* ≥ p₀`. The changed entry now makes `p₀` strictly harder to satisfy. The descending search may fail to satisfy `p*` under `Φ'`. The next candidate is `p* - 1`. Since the single changed requirement only constrains permissions `≥ p₀`, and `p* - 1 < p*` means one step down, the search finds `p* - 1` satisfiable unless there is an independent reason it was not satisfiable under `Φ` — but that would contradict downward closure (Lemma 2), which guarantees that if `p*` is satisfiable, all weaker permissions are too, and the single changed entry affects at most one level. Therefore `Compile(Γ,Φ') ≥ p* - 1`. ∎

## Corollary M1. Permission is Lipschitz in the profile

Let `d(Φ,Φ') = |{(κ,h,p) : ReqΦ(κ,h,p) ≠ ReqΦ'(κ,h,p)}|` be the number of differing entries. Then for any `Γ`:

```text
|Compile(Γ,Φ') - Compile(Γ,Φ)| ≤ d(Φ,Φ')
```

A profile that differs from the intended profile by `k` entries produces an output no more than `k` permission steps wrong.

**Proof.** Apply Lemma M inductively, one entry at a time. ∎

## Theorem N. Grounded profiles do not silently authorize unmitigated failure modes

Let `Φ` be a grounded profile for class `κ` (§8.4.1). Let `Γ` be any in-class proof context. Let `h` be any gap type such that `F(h,κ)` is a named failure mode and `EffΓ(h) = OPEN`. Then:

```text
Compile(Γ,Φ) < p
```

for every permission level `p` at which `Φ(κ,h,p) ≥ BOUNDED_REQUIRED`.

**Proof.** By groundedness, `ReqΦ(κ,h,p) ≥ BOUNDED_REQUIRED`. By the profile satisfiability check in Step 8, `p` requires `EffΓ(h) ≥ BOUNDED`. Since `EffΓ(h) = OPEN`, `p` is not satisfiable. By Lemma 3, the descending search returns the greatest satisfiable permission, which is strictly below `p`. ∎

The theorem says a grounded profile cannot silently grant action authority when a named, domain-recognizable failure mode is unmitigated. The only way to obtain a strong permission with an open required gap is to present a gap-closing token — which is a domain claim, auditable, versioned, and subject to its own certifier obligations.

**Theorem N is not a guarantee of correctness. Its strength depends on the domain class.**

In mathematically grounded domains, the gap taxonomy is derivable from the mathematics, not from case selection. The failure modes are theorems: `posterior_divergence_gap` is open iff the approximate posterior exceeds the certified bound. There is no policy choice in this. Given a complete taxonomy — one where every relevant failure mode has a corresponding gap type — Theorem N approaches a correctness guarantee: a well-evidenced system will be authorized; an insufficiently evidenced system will not. The benchmark finding that `model_specification_gap` was missing is a claim that the taxonomy was incomplete, not that the profile was miscalibrated. Once added, its satisfaction condition is again mathematical.

In policy-grounded domains, the gap types can be named but their satisfaction conditions are human choices. `clinical_utility_gap` is bounded by a token that asserts PPV ≥ 0.20 at a given threshold. Whether 0.20 is the right floor is not a theorem — it is a judgment that different institutions will make differently. Theorem N here is a guarantee of *enforcement*, not *correctness*: if the profile requires clinical utility to be bounded and the evidence does not meet the detail contract's threshold, the permission is refused. Whether the threshold was set correctly is outside the theorem. It is inside the profile governance process.

The framework can only fail by omission — a failure mode not in the taxonomy, or in the taxonomy but not required by the profile at the right permission level. Both failures are visible: the taxonomy and profile are explicit, versioned, and auditable. Both benchmarks demonstrate this: PGM-001 found a missing gap type; MED-001 found a missing profile requirement. Both were caught at the boundary, not inside the compiler. The common failure mode in practice — missing policy, underspecified policy — produces exactly this kind of omission. Making the policy compiler-processable makes the omission visible.

---

# Part III — Stress Evidence

The tests are not the proof. They are executable attempts to falsify the proof obligations, the implementation, and the profile/taxonomy boundary.

`EC-003` tests the algebra, composition, decomposition, runtime, anti-laundering, token reuse, provenance identity, rollback, and final-meet truth table. Result: 11,178 tests, 0 falsifications.

`EC-004` tests profile well-formedness, artifact validation, free-text rejection, greatest-permission search, adapter determinism, context sensitivity, and adversarial domain suites. Result: 11,245 cumulative tests, 0 falsifications.

| Evidence class | Target | Current locus |
|---|---|---|
| Algebraic checks | Order, meet, associativity, idempotence, normalization | `EC-003` |
| Runtime checks | Expiry, replay, skew, missing dependencies, registry failure | `EC-003` |
| Composition checks | Stale or narrow components hidden by fresh ones | `EC-003` |
| Provenance adversaries | Token reuse across ids | `EC-003`, `EC-004` |
| Profile checks | Stronger permissions easier than weaker ones | `EC-004` |
| Property checks | Descending search not returning greatest satisfiable permission | `EC-004` |
| Registry checks | Free text, wrong type, wrong scope, expired artifacts | `EC-004` |
| Adapter adversaries | Hidden context changes and class ambiguity | `EC-004` |
| Domain benchmark | Inference certificates over PGM workloads | `PGM-001` |

No structural conjectures remain open in the current structural test battery. Domain-scientific adequacy belongs to domain certifiers.

## MED-001. Clinical sepsis benchmark

MED-001 is a prospective benchmark: real models run against real PhysioNet Challenge 2019 data; compiler output verified against oracle expectations. Two prospective axes: oracle cases (pre-registered expected outputs) and adversarial cases (boundary perturbations not used in profile design).

```text
11/11 oracle cases: 0 violations
9/9 adversarial cases: 0 violations
```

The benchmark also produced the V1→V2→V3 profile progression documented in §0.7. V1 (AUC only) authorized the Epic failure pattern. V2 (adds `clinical_utility_gap`, `distribution_shift_gap`) blocked it. V3 (adds `shadow_mode_validation_gap`, `post_market_monitoring_gap`) encoded the NHS/FDA deployment-phase obligations V2 missed. Each profile transition was forced by matching the profile against regulatory text — a task the framework made tractable by requiring that policy be explicit and machine-checkable.

One taxonomy correction: `clinical_utility_gap` and `distribution_shift_gap` were not in the initial taxonomy. They were induced by the benchmark's falsification of V1. This follows the same pattern as PGM-001's induction of `model_specification_gap`.

---

## CASE-LIB-001. Multi-domain retrospective audit

CASE-LIB-001 is a retrospective benchmark: for 16 real-world AI deployments with documented harmful outcomes, what would the compiler have emitted given the evidence available at deployment time?

The 16 cases span five domains: medical (5), criminal justice (4), employment (3), autonomous systems (2), government benefits (2). All cases have primary sources in published peer-reviewed papers, federal court records, regulatory reports, or investigative journalism. Gap statuses are reconstructed from public evidence; cases where public evidence was insufficient to pin gap statuses were excluded.

Three profile tiers were pre-registered before running:

- **Tier 0 — min_viable:** requires only `approximation_quality_gap` bounded. Represents the implicit deployment standard at most organizations pre-2020: "does the model work at all?"
- **Tier 1 — reasonable_deployment:** requires `approximation_quality + model_specification + blast_radius + authority` bounded. A single cross-domain profile. No domain-specific gaps.
- **Tier 2 — per-domain:** Tier 1 plus one to two domain-specific gaps (medical: `clinical_utility + distribution_shift`; criminal justice and government: `individual_population`; employment: `proxy`; autonomous: `freshness`).

All 48 pre-registered predictions matched compiler output. Results:

```text
Tier 0 (AUC only):              5/16 cases blocked
Tier 1 (reasonable deployment): 16/16 cases blocked
Tier 2 (per-domain):            16/16 cases blocked
```

**The Tier 1 result is the load-bearing claim.** A single four-gap cross-domain profile would have blocked all 16 documented harms. The profile was not fitted to these cases. It was derived independently from the Tier 2 observation that model_specification, blast_radius, and authority gaps appear across all five domains. Tier 1 is the cross-domain intersection.

**The Tier 0 result is a quantified account of what the industry's implicit pre-2020 deployment standard missed.** AUC-only blocked the 5 cases where basic technical validity was never established (COVID models via Roberts et al. 2021; IBM Watson; HireVue; Uber ATG; Dutch Toeslagenaffaire — approximation quality unknown). It passed the 11 cases where the model performed accurately on its stated target but was deployed at the wrong action class, without blast radius controls, without authority checks, or using a proxy that diverged on the protected class. These are the harms an AUC certificate cannot see.

**The §10.2 invariant holds for all 16 cases under Tier 1 and Tier 2:** compiler output was strictly below the implicit permission actually granted at deployment, with the gap between them explained by exactly the OPEN gaps identified.

**Two new gap types were induced.** The retrospective found two gap types not in the current taxonomy:

*`individual_population_gap`.* A statistical model that accurately characterizes outcomes for a population provides no certifiable basis for predicting whether a specific individual will have that outcome. Population-level calibration is not individual-level predictive validity. This gap appears in 5 cases: COMPAS (pretrial detention), Arkansas Medicaid (benefit cuts), Chicago SSL (preemptive policing), Dutch Toeslagenaffaire (fraud repayment demands), and Allegheny AFST (child welfare screening). It is structurally distinct from `distribution_shift_gap` and `model_specification_gap` — a model may generalize perfectly to the deployment population and have this gap permanently open for the specific action class. For detention-class actions, this gap may be unboundable in principle: the evidence required to license individual liberty deprivation from population recidivism rates does not exist and cannot be constructed.

*`feedback_coupling_gap`.* A model deployed in a decision-making system changes the distribution of future training data through its own outputs, creating self-reinforcing error patterns invisible to standard distribution shift analysis. The model may remain accurate on its own self-generated training distribution at every time step while drifting arbitrarily from the true target. This appears in CASE-CJ-003 (PredPol): increased policing in predicted areas generated more reported crime there, which updated the model to predict more crime there. Standard `distribution_shift_gap` analysis cannot detect this failure because the model's training distribution is endogenous to the model's past outputs. Distinct from `interference_gap` (which covers prediction-changes-the-thing-predicted): here the feedback runs through the model's own evidence base, not through the world state.

Both new gap types follow the same induction pattern as PGM-001's induction of `model_specification_gap` and MED-001's induction of `clinical_utility_gap`: the benchmark identified a case where the compiler emitted too-strong permission, the gap was absent from the taxonomy, and adding the gap produced the correct output. In all three cases, the compiler did what the current profile asked; the falsified component was the taxonomy.

**The Tier 2 domain gaps are analytically informative but not necessary for the headline.** Every domain's cases were already blocked by Tier 1. Tier 2 additions identify which specific gap is the *primary obligation* per domain — the one that, if required, would have been the first gate. This matters for taxonomy design: if domain gaps are load-bearing for some cases that Tier 1 passes, the profile is too weak. The result here — Tier 2 adds no new blocks — means Tier 1's four-gap intersection is sufficient, and domain gaps add precision, not coverage.

---

## PGM-001. Probabilistic inference benchmark

The first domain benchmark tested inference certificates over Bayesian-network workloads. Its main result is mixed in the useful way.

Structural soundness was clean.

```text
0 violations across 12 oracle-checked cases
0 violations across 316 parametrized tests
```

The oracle-checked cases were mostly exact-certificate cases. Of the 316 parametrized tests, 200 were random-seed Hilbert-family soundness tests in which the compiler's certified bound was checked against numerical ground truth on the approximate path. These are the load-bearing soundness evidence.

The benchmark also found that the current workload design does not stress the approximate regime enough.

```text
37/60 AAA exact cases
3/60 ALR approximate cases
20/60 OOC cases
```

Many networks fit exact variable elimination inside the fixed memory tiers. The tightness result is therefore not yet meaningful: the oracle cases with exact certificates have certified KL equal to actual KL, and the non-exact certificates are too large for the oracle. The next inference run should use per-network budget calibration rather than fixed 1/4/16MB tiers.

The benchmark produced one taxonomy/profile correction.

`posterior_divergence_gap` was not enough. On deliberately misspecified models, the framework correctly certified approximation error against the supplied model, but the action authority was too strong relative to the external world.

```text
39 rows identified by benchmark perturbation tooling
3 ALR cases occurred on misspecified posteriors
```

The compiler did not emit this diagnostic under the old taxonomy. The benchmark's perturbation tooling identified rows where the compiler emitted permission against an intentionally misspecified posterior. The compiler did what the then-current profile asked. The falsified component was the taxonomy/profile: world-facing rollout authority requires a `model_specification_gap`.

Adding `model_specification_gap` produced a new `Θ_v`. Envelopes issued under the prior taxonomy remain valid under their recorded version by Theorem K′. Fresh compiles use the updated taxonomy and strengthened profile.

The benchmark also separated two OOC causes.

```text
memory ceiling:
  no candidate fits the budget

kernel coverage:
  no registered kernel family produced a candidate
```

Memory OOC is clean refusal. Kernel coverage OOC is a registry/instrumentation problem, not a gap. It is recorded as an audit reason on the failed compile, because no certifier can discharge it as evidence about the posterior or the world. The next run should log, per failed elimination site, which kernel families declined, why they declined, what the local scope looked like, and whether the failure reflects missing family coverage or bad applicability declarations.

## Current evidence status

| Claim                                      | Status                                                              |
| ------------------------------------------ | ------------------------------------------------------------------- |
| Algebraic non-promotion                    | Supported by proof and EC-003                                       |
| Profile/search non-promotion               | Supported by proof and EC-004                                       |
| Token/provenance anti-laundering           | Supported by proof, EC-003, and EC-004                              |
| Runtime non-upgrade                        | Supported by proof and EC-003                                       |
| Profile Lipschitz sensitivity (Corollary M1) | Supported by proof                                                |
| Grounded profile non-authorization (Theorem N) | Supported by proof                                              |
| Profile surgical property                  | Supported by MED-001 oracle suite (11/11 cases) and CASE-LIB-001 Tier 1 (16/16 cases) |
| Inference structural soundness             | Supported by PGM-001 on checked cases                               |
| Inference tightness                        | Not yet measured in the interesting regime                          |
| Inference taxonomy completeness            | Falsified once; patched with `model_specification_gap`              |
| Clinical taxonomy completeness             | Falsified once; patched with `clinical_utility_gap`, `distribution_shift_gap` |
| Clinical profile generalization            | Supported by MED-001 (11 oracle + 9 adversarial cases); supported by CASE-LIB-001 Tier 1 (16/16 cases, 5 domains, profile not designed on these cases) |
| Cross-domain profile generalization        | Supported by CASE-LIB-001: four-gap Tier 1 profile blocks all 16 retrospective harms across medical, criminal justice, employment, autonomous, government |
| §10.2 retrospective invariant              | Verified: compiler output < implicit permission for all 16 CASE-LIB-001 cases under Tier 1 and Tier 2 |
| Retrospective taxonomy completeness       | Two new gap types induced: `individual_population_gap` (5 cases), `feedback_coupling_gap` (1 case); same induction pattern as prior benchmarks |
| Kernel-family coverage                     | Open instrumentation task                                           |
| GasTown multi-agent class benchmark        | Pending                                                             |

The important result is not that every benchmark passed. The important result is that the framework failed in the right place in three separate domains, through the same mechanism each time: a case where the emitted permission was too strong relative to what a domain expert would accept. In every instance the correction was a profile or taxonomy change, not a compiler change. The compiler continued to enforce the updated specification correctly on held-out cases.

Three taxonomy falsifications across three domains:
1. PGM-001: `model_specification_gap` induced by misspecified-posterior cases in Bayesian inference
2. MED-001: `clinical_utility_gap` and `distribution_shift_gap` induced by the Epic sepsis deployment failure
3. CASE-LIB-001: `individual_population_gap` and `feedback_coupling_gap` induced by the retrospective audit

The pattern is consistent: the compiler enforces what the profile asks; the profile enforces what the taxonomy defines; the taxonomy is incomplete until the benchmark falsifies it. Each falsification event adds one or two gap types, corrects the profile, and the updated pair (taxonomy, profile) produces correct outputs on the cases that motivated the correction without breaking the cases that were already handled. This is the empirical analog of Theorem N: grounded profiles, once corrected, do not silently authorize the failure modes they are designed to catch.

---

# Part IV — Related Work and Novelty

Orders, meets, monotone composition, and credentials are not new.

Capability systems narrow authority. Information-flow control uses labels and lattices. Differential privacy composes privacy loss. Trust-management systems bind authorization to credentials. Remote attestation binds claims to measured artifacts. Proof-carrying authorization requires evidence before action.

The contribution here is the compiled object and the admissibility discipline.

Approximate consequential outputs become judgments only through:

- gap profiles;
- exact five-id provenance;
- live evidence;
- checkable not-applicable artifacts;
- profile-conservative class assignment;
- immutable envelopes;
- fixed registry versions;
- runtime non-upgrade.

The meet is the carrier. The discipline is the contribution.

---

# Part VI — Artifact Status and Remaining Work

The reference implementation contains the algebra, compiler protocol, profile discipline, adapter checks, registry checks, and adversarial suites. `EC-003` and `EC-004` run against it.

The proof surface is small:

- finite ordered outcomes;
- finite nonempty meets;
- monotone profile requirements;
- exact provenance equality;
- immutable registry versions;
- runtime meets.

The current proof is textual. The submission artifact target is concrete: first mechanize Lemmas 1–3, then extend the same finite-order development to composition, decomposition, runtime non-upgrade, malformed-detail non-promotion, class-shopping non-promotion, profile-version non-upgrade, taxonomy-version non-upgrade, and detail-contract non-upgrade.

Remaining implementation work:

1. run the GasTown class benchmark over constructable multi-agent workflows;
2. rerun the PGM benchmark with calibrated per-network memory budgets;
3. instrument kernel-family coverage failures for `link` and `munin1`;
4. replace the illustrative marketplace token with emitted certifier output;
5. formalize predicate scopes beyond finite sets;
6. extend adversarial suites for adapters, taxonomies, profiles, contracts, registries, and authority envelopes.

---

# Appendix A — Notation

| Symbol | Meaning |
|---|---|
| `Γ` | Proof context |
| `A` | Approximate output |
| `z` | Candidate claim, result, or action |
| `p` | Permission or control outcome |
| `ε` | Expiry condition |
| `κ` | Claim class |
| `c` | Claim |
| `x` | Context |
| `u` | Intended use |
| `Θ_v` | Gap taxonomy version |
| `Φ_v` | Gap profile version |
| `Σ_v` | Detail-contract registry version |
| `T` | Proof tokens |
| `Π` | Provenance records |
| `ρ` | Runtime context |
| `EffΓ(g)` | Effective gap status under `Γ` |
| `Prov(τ,g,c,z,x)` | Exact provenance relation |
| `posterior_divergence_gap` | Obligation bounding approximation error relative to the supplied posterior/model |
| `model_specification_gap` | Obligation bounding whether the supplied model is adequate for the action-relevant target |

---

# Appendix B — Reference Pseudocode

```python
def compile(A, kappa, z, x, Phi_v, Theta_v, Sigma_v, T, Pi, epsilon, rho):
    m = membership(A, kappa, z, x)
    if m != "IN_CLASS":
        return judgment(None, z, "OOC", epsilon, reason=m.reason)

    c = induce_claim(A, kappa, z, x)
    G = induce_gaps(kappa, z, x, intended_use(A), Theta_v)

    if expired(epsilon, rho):
        Gamma = build_context(c, z, x, G, Theta_v, Phi_v, Sigma_v, T, Pi, epsilon, rho)
        return judgment(Gamma, z, "EXP", epsilon)

    eff = {g.id: "OPEN" for g in G}

    for tau in T:
        if not registry_valid(tau, rho):
            continue
        if not detail_contract_ok(tau, rho, Sigma_v):
            continue
        if not live(tau.expiry, rho):
            continue

        for g in G:
            if g.id in tau.closes_gaps and prov(tau, g, c, z, x, Pi):
                eff[g.id] = "CLOSED"
            elif g.id in tau.bounds_gaps and prov(tau, g, c, z, x, Pi):
                if eff[g.id] != "CLOSED":
                    eff[g.id] = "BOUNDED"

    failures = []
    if provenance_mismatch(T, Pi):
        failures.append("PROVENANCE_MISMATCH")
    if allowed_use_conflict(c):
        failures.append("ALLOWED_USE_CONFLICT")
    if scope_empty(z):
        failures.append("SCOPE_EMPTY")
    if not derivation_ok(c, z, x):
        failures.append("DERIVATION_INVALID")
    if rho.strict_mode and negative_control_failed(T, Pi, rho):
        failures.append("NEGCTRL_FAILED")
    if runtime_context_failure(rho):
        failures.append("RUNTIME_CONTEXT_FAILURE")

    controls = []
    if authority_ceiling_exceeded(c, z, rho):
        controls.append("ETA")
    if human_tradeoff_required(c, z, rho) or authority_absent(rho):
        controls.append("ESC")
    if rollback_condition_met(c, z, rho):
        if rollback_capability_present(T, rho):
            controls.append("ROL")
        else:
            controls.append("ESC")
            record_blocking_reason("ROLLBACK_CAPABILITY_MISSING")

    best = "UNS"
    for p in ["AAA", "ALR", "AEX", "REV", "DIA"]:
        if (profile_exists(kappa, p, Phi_v)
            and gaps_ok(G, eff, kappa, p, Phi_v)
            and use_ok(c)
            and in_scope(z)):
            best = p
            break

    candidates = [best]
    if failures:
        candidates.append("REF")
    if controls:
        candidates.append(permission_meet_n(controls))

    Gamma = build_context(
        c, z, x, G, Theta_v, Phi_v, Sigma_v, T, Pi,
        epsilon, rho, failures, controls, blocking_reasons()
    )

    return judgment(Gamma, z, permission_meet_n(candidates), epsilon)
```

---

# Appendix C — Marketplace Token Sketch

A marketplace proxy-bound token must carry enough structure for a contract to check it.

```text
proof_token_id
 token_type = marketplace.proxy_bound.v1
 detail_contract_id
 detail_contract_hash
 status = VALID
 bounds_gaps = [proxy_gap_id]
 closes_gaps = []
 scope = (candidate_id, context_id, placements, market)
 expiry
 details = (
   estimand,
   method,
   artifact_refs,
   coverage,
   overlap,
   estimate,
   bias_checks,
   claim_limit
 )
```

The contract checks schema, artifacts, scope, coverage floor, overlap floor, expiry, and bias checks.

Passing this contract bounds `proxy_gap`. It does not close `proxy_gap`. It says nothing about `interference_gap` or `coupling_gap`.
---

# Appendix D — PGM Inference Token Sketch

A PGM inference token must say which object it certifies.

```text
proof_token_id
token_type = pgm.posterior_divergence_bound.v1
detail_contract_id
detail_contract_hash
status = VALID
bounds_gaps = [posterior_divergence_gap_id]
closes_gaps = []
scope = (claim_id, candidate_id, context_id, network_id, query, evidence)
expiry
details = (
  model_fingerprint,
  query_variables,
  evidence_fingerprint,
  inference_family,
  memory_budget,
  certificate_type,
  certified_divergence_bound,
  oracle_check_status,
  kernel_family,
  approximation_parameters,
  artifact_refs
)
```

Passing this contract bounds `posterior_divergence_gap`. It does not bound `model_specification_gap`.

A separate model-specification token would need a different contract.

```text
token_type = pgm.model_specification_bound.v1
bounds_gaps = [model_specification_gap_id]
details = (
  data_generating_assumptions,
  validation_artifacts,
  perturbation_sensitivity,
  calibration_or_fit_checks,
  scope_limits,
  claim_limit
)
```

That token is harder to produce. The difficulty is the point. The compiler should not treat approximation evidence as model adequacy evidence.
