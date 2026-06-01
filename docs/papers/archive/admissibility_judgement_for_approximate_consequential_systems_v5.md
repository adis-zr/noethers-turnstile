# Evidence Is Not Permission: Admissibility Judgments for Approximate Consequential Systems

## Abstract

Approximate consequential systems act on tractable approximations while downstream workflows treat their outputs as permission to act. A clinical score becomes support for operational rollout. A retrieval result becomes grounding for a legal summary. An agent-generated software artifact becomes a deployment candidate. In each case, evidence valid for one use is silently promoted into authorization for a stronger one. This paper calls that failure **evidence overextension**.

We introduce a permission-valued **admissibility judgment**:

```text
Γ ⊢ z : p until ε
```

which reads: under proof context `Γ`, candidate artifact or output `z` supports permission `p` until expiry condition `ε`. The judgment is enforced by an admissibility compiler. The compiler does not choose policy, certify scientific truth, or decide which trade-offs are acceptable. Instead, it enforces compiler-processable policy: given a taxonomy of proof obligations, a profile specifying which obligations are required at which permission levels, scoped proof tokens, provenance records, authority ceilings, and expiry conditions, it emits the strongest permission actually supported and no stronger.

The paper makes three claims. First, approximate outputs should not authorize action directly; they should authorize action only through admissibility judgments. Second, the relevant permission levels are domain-defined, but their finite monotone order is structural: it enables greatest-supported-permission search, meet-based composition, authority ceilings, expiry downgrade, and non-promotion. Third, the judgment form is not arbitrary. A companion representation theorem shows that domains admit sharp admissibility compilers exactly when their ideal licensing maps factor through finite monotone certifier-observable quotients; in tame settings, including Noetherian-style, well-quasi-ordered, and semialgebraic regimes, the required obstruction bases have finite forms.

We demonstrate the framework on the Epic sepsis model. Under a weak profile, Epic compiles to limited rollout because clinical utility and distribution shift are not required. Under a corrected profile, the same evidence compiles only to experiment because those obligations remain open. The difference is not a different model; it is an exposed policy boundary. The compiler does not make weak evidence strong. It gives weak evidence a weak license, strong evidence a stronger license, and unsupported escalation an auditable refusal.

---

# 1. Introduction: Evidence Is Being Used as Permission

There has been a seismic shift in software engineering and decision automation. Someone describes a feature in natural language. An agent writes the ticket. Another agent writes the specification. Another writes the code. Another writes tests. Another writes the deployment manifest. A final agent reviews everything and ships.

At no point did anyone necessarily ask whether the evidence available to the system was sufficient for the action being taken.

Once noticed, the same gap appears everywhere. A sepsis score adequate for flagging a patient gets used to support operational rollout. A retrieval result adequate for surfacing a document gets used to ground a legal summary. An experiment readout becomes rollout authority. A marketplace simulation becomes pricing authority. A fraud score becomes an account hold. A hiring score becomes a screening decision.

The recurring failure is not merely that approximate systems can be wrong. It is that approximate evidence is often used for a stronger purpose than it was certified to support.

Call this **evidence overextension**.

Evidence overextension occurs when evidence valid for one use is silently promoted into authorization for a stronger use. A metric that supports diagnostic display is treated as support for automatic action. A validation performed on one population is reused for another. A fresh top-level artifact hides a stale dependency. A token proving approximation quality is treated as evidence of model specification. A local experiment result becomes global rollout authority.

Formal-methods and security systems solved an analogous problem for exact systems. Access-control calculi, proof-carrying code, proof-carrying authorization, capability systems, information-flow control, and runtime monitors all ask whether an action has the proof, authority, capability, label, or invariant it requires.

Approximate consequential systems need the same discipline, but the object being controlled is different. The output is not a proof of correctness. It is an approximation whose authority depends on evidence, scope, context, provenance, and expiry.

This paper introduces a permission-valued **admissibility judgment**:

```text
Γ ⊢ z : p until ε
```

This reads: under proof context `Γ`, candidate artifact or output `z` supports permission `p` until expiry condition `ε`.

The central claim is:

> Approximate outputs do not authorize action directly. They authorize action only by compiling into admissibility judgments.

The compiler does not decide what an organization should value. It does not choose clinical thresholds, legal standards, fairness constraints, or risk tolerances. It does not certify that a domain expert used good science. Those judgments remain hard.

The compiler does something narrower: it prevents unsupported escalation once the policy has been written down. It asks what permission follows from the proof context actually supplied. It emits the strongest permission supported by the evidence, provenance, scope, authority, expiry, and profile — and no stronger.

That distinction is the paper.

---

# 2. Approximate Consequential Systems

A system is **approximate consequential** when four conditions hold:

1. The ideal output is unavailable at decision time.
    
2. The system acts on an approximation of that ideal output.
    
3. A downstream workflow treats the approximate output as permission, authority, or control-relevant evidence.
    
4. The validity of the output depends on context that can change.
    

All four conditions matter.

The first two distinguish approximate systems from exact systems. Paxos is highly consequential, but its correctness condition is exact. Sorting and arithmetic may be important, but they are not approximate in this sense.

The third condition is what makes the system consequential. A prediction, score, retrieval result, simulation, or agent plan becomes dangerous when another system treats it as a license to act.

The fourth condition is what makes the framework necessary for deployed systems. Populations drift. Repositories update. Policies expire. Model versions change. Evidence collected under one context may no longer support the same action under another.

Examples include:

- clinical alerts;
    
- legal retrieval and summarization;
    
- agentic software deployment;
    
- fraud holds;
    
- hiring or credit scores;
    
- experiment readouts;
    
- marketplace policy or pricing changes;
    
- probabilistic inference used for action;
    
- autonomous system interventions;
    
- cybersecurity responses.
    

The class is not “AI systems” in general. It is narrower:

```text
approximation + downstream authorization + changing context
```

A model used only for offline analysis may be approximate but not consequential. A deterministic write may be consequential but not approximate. A static report may be both approximate and consequential, but if no downstream workflow treats it as permission, the compiler may not be the right abstraction.

The framework applies when an approximate output enters an authorization path.

---

# 3. Permissions: Why the Levels Look the Way They Do

The judgment emits a permission. That raises an immediate question: who says these are the permission levels?

The answer is deliberately split.

The concrete levels are domain-defined. A hospital, legal platform, marketplace, software deployment system, or regulator may choose different operational categories. One domain may use “display,” “review,” “experiment,” “rollout,” and “automatic action.” Another may use “advisory,” “supervised,” “pilot,” “production,” and “autonomous.” A third may need more levels or fewer.

The labels are not laws of nature.

What matters structurally is that the permissions form a finite ordered set. Stronger permissions must require at least as much support as weaker permissions. The exact names can vary; the monotone order is what gives the compiler its properties.

At a high level, many domains have a positive permission chain like:

```text
diagnostic display
< human review
< controlled experiment
< limited rollout
< automatic action
```

The full system may also include restrictive or control outcomes such as:

```text
OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA < REV < AEX < ALR < AAA
```

where lower outcomes are more restrictive and higher outcomes are stronger permissions.

One concrete interpretation is:

|Symbol|Meaning|
|---|---|
|`OOC`|Out of class — the framework does not govern this input|
|`EXP`|Expired — a token or context TTL has elapsed|
|`REF`|Refused — a credential was rejected or structurally invalid|
|`UNS`|Unsupported — profiles exist but no evidence satisfies any of them|
|`ETA`|Authority ceiling exceeded|
|`ESC`|Escalation required|
|`ROL`|Rollback condition met|
|`DIA`|Diagnostic display only|
|`REV`|Human review recommended|
|`AEX`|Approve experiment|
|`ALR`|Approve limited rollout|
|`AAA`|Approve automatic action|

The particular symbols are implementation choices. The structure is not.

The order lets the compiler ask a well-defined question:

```text
What is the greatest permission supported by this proof context?
```

Without an order, “stronger than the evidence supports” has no general meaning. With an order, the compiler can search from strongest to weakest and return the first satisfiable permission.

The order also enables non-promotion. Authority ceilings, expiry, runtime checks, rollback obligations, composition, and structural failures all operate by meet. A meet can only preserve or lower the permission. A fresh component cannot pull a stale component upward. Strong evidence for one claim cannot upgrade weak evidence for another. A runtime check cannot make an issued judgment stronger than it was at compile time.

This is why the permission structure is central. The levels may be designed, but the monotone ordering is what makes the system enforceable.

The paper does not claim that every domain must use this exact chain. It claims that any domain using this compiler discipline must expose its action authorities as a finite monotone permission structure.

---

# 4. The Admissibility Judgment

The central object of the framework is:

```text
Γ ⊢ z : p until ε
```

This reads:

> Under evidentiary context `Γ`, candidate artifact or output `z` is admissible at permission `p` until expiry condition `ε`.

Each component is load-bearing.

`z` identifies the candidate artifact, output, claim, model, summary, deployment, action, or policy change being judged.

`Γ` is the proof context. It contains the evidence package: claim identity, candidate identity, context identity, induced gaps, profile version, proof tokens, provenance, authority, runtime facts, expiry rules, allowed use, disallowed use, and audit.

`p` is the emitted permission. It says what the artifact is allowed to support.

`ε` is the expiry condition. It states when the judgment ceases to be live.

The caller may request a permission. The compiler ignores that request as evidence. A request for rollout is not rollout evidence. A request for automatic action is not automatic-action evidence. The compiler emits the strongest permission supported by the proof context actually supplied.

This is the core anti-laundering discipline. The output of an approximate system is not authority. The output becomes authority only through the judgment.

A judgment is therefore not merely a decision. It is a decision plus the exact context in which that decision was valid. If a deployment is refused, the judgment records which stronger permissions were blocked and why. If a deployment is authorized, the judgment records which profile, taxonomy, detail contracts, tokens, provenance records, authority envelope, and expiry condition supported that authorization.

An informal deployment decision cannot be retrospectively interrogated in this way. A compiled judgment can.

---

# 5. What the Compiler Can and Cannot Guarantee

The compiler is powerful, but only inside a sharply defined boundary.

## 5.1 Two Classes of Approximate Consequential System

The framework's guarantee depends on which class of system it is applied to. The distinction is not a matter of degree. It is a structural difference in where the gap taxonomy comes from.

**Mathematically grounded systems.** In probabilistic inference, formal verification, and cryptographic protocols, the gap taxonomy is closer to canonical. `posterior_divergence_gap` is not primarily a policy choice. The KL divergence between the approximate posterior and the true posterior either satisfies the certified bound or it does not. The certificate type is derived from the mathematics; the threshold may be fixed by theorem or by an explicit approximation contract.

For these systems, the compiler approaches a completeness system. Given the right gap taxonomy — which the mathematics largely determines — Theorem N becomes close to a correctness guarantee: if a required obligation is unmet, the compiler refuses the permission. The domain expert's job is to identify the relevant gaps; the mathematics defines much of what satisfies them.

**Policy-grounded systems.** In clinical deployment, hiring decisions, content moderation, fraud detection, legal research, marketplace policy, and credit scoring, the gap taxonomy can be named and principled, but the satisfaction conditions are human choices. `clinical_utility_gap` exists and corresponds to a real failure mode. But PPV ≥ 0.20 before rollout is not a theorem. It is a judgment call that reasonable clinicians can disagree about. The blast-radius categories, freshness windows, population scopes, and authority rules are engineering and governance inputs.

For these systems, the compiler does something different: it separates policy from enforcement and forces policy to be compiler-processable.

## 5.2 Missing Policy and Underspecified Policy

The framework addresses two recurring failure modes.

**Failure mode 1: missing policy.** The deployment proceeds on informal judgment. No one wrote down what evidence was required before rollout. Decisions are made case by case, by whoever is available, with no record of the reasoning. The compiler addresses this structurally: one cannot compile without a profile. The profile must exist before a deployment decision can be made.

**Failure mode 2: underspecified policy.** A policy exists — “we require adequate clinical validation” — but it is too vague to enforce. No threshold, no scope, no expiry, no named obligation. The same sentence can be interpreted to approve or refuse the same case depending on who reads it and when.

The compiler addresses this through profiles and detail contracts. Tokens must satisfy registered schemas with concrete semantic checks. “Adequate validation” is not a valid semantic check. “PPV ≥ 0.20 at `blast_radius=notification` with `sample_size ≥ 1000`” is.

Both failure modes appear in the Epic sepsis case. There was no explicit policy requiring operating-point utility validation before rollout. And had such a policy existed only in prose, it could still have been too vague to mechanically enforce.

## 5.3 Separation of Policy and Enforcement

In most organizations, the team that decides what evidence is sufficient is also the team that decides whether a specific deployment has it. These are not separated structurally. A senior researcher who championed a model is unlikely to apply a strict utility standard at deployment time. A team under deadline pressure may satisfy an informal standard more loosely than the same team with no deadline.

The compiler makes this separation structural. The profile is the policy: written down, versioned, reviewed, and immutable once issued. The compiler is the enforcer: it checks the profile against the presented evidence and cannot be persuaded, fatigued, or deadline-pressured. The same profile, applied to the same evidence, produces the same output every time.

This is analogous to the discipline of formal specification. A tool such as TLA+ does not tell an organization what invariant its system should maintain. The discipline is that once the invariant is written down, violations are checked mechanically rather than depending on the reviewer who happened to be on call.

This paper makes the same move for approximate consequential systems. The profile is the invariant. The compiler is the checker. The domain expert writes the profile; the compiler ensures it is not accidentally violated. The contribution is enforcement, not wisdom.

## 5.4 Compiler-Processable Policy as a Specification Language

By requiring policy to be compiler-processable, the framework also specifies what a well-formed policy must answer.

A compiler-processable policy must specify:

- which gaps are required at which permission levels, for which action classes;
    
- what a valid token for each gap looks like;
    
- what fields, semantic checks, and scope rules the token must satisfy;
    
- which claim, candidate, and context the token covers;
    
- how long the evidence remains live;
    
- which downstream uses are allowed or disallowed;
    
- which authority ceilings apply;
    
- which detail contracts distinguish different blast radii or action classes.
    

Most organizations have not answered these questions. They are not asked because no system requires answers in this form.

The compiler is that system. The profile and detail-contract registries are the specification language. Writing a valid profile is an act of policy clarification.

The framework does not tell the organization the right answers. It tells the organization which questions must have answers before a deployment can be authorized.

## 5.5 Structural Guarantees and Trusted Computing Base

The compiler does not choose:

- objectives;
    
- thresholds;
    
- acceptable trade-offs;
    
- evidence standards;
    
- moral judgments;
    
- regulatory requirements;
    
- scientific validity.
    

Domain experts still decide what evidence is sufficient for each permission level. The compiler does not know the correct PPV floor for a sepsis alert, the right blast-radius category for a legal summary, the acceptable fairness constraint for hiring, or the right threshold for marketplace rollout.

The compiler can structurally enforce:

- provenance binding;
    
- token status;
    
- expiry;
    
- authority ceilings;
    
- non-promotion under composition;
    
- empty-profile floor;
    
- absent-gap default;
    
- runtime downgrade;
    
- immutable profile, taxonomy, and contract versions for issued judgments.
    

But other properties remain inside the trusted computing base. The compiler accepts on faith:

- truthful gap statuses;
    
- honest certifiers;
    
- valid science;
    
- correct membership classification;
    
- correct profile selection;
    
- valid schema and profile versions;
    
- correct token/gap compatibility, unless encoded in the registry;
    
- correct context identity and context versioning;
    
- correct threshold choices.
    

Institutions must therefore ensure that certifiers, not submitters, produce proof tokens and gap statuses; that detail contracts define which token types can satisfy which gaps; that deprecated profiles are rejected at context construction; that context identifiers change when deployment-relevant conditions change; and that sample size, independence, pre-registration, and held-out validation are enforced by domain governance.

The compiler does not make governance unnecessary. It makes governance executable.

If governance supplies the wrong taxonomy, weak profile, bad certifiers, stale context identity, or inappropriate threshold, the compiler can still authorize too much. But the failure is now located at the boundary rather than hidden inside an informal deployment decision.

## 5.6 Trust Boundary

The soundness claim is not absolute. It is relative to a named trusted computing base.

|TCB component|Must guarantee|Attack excluded when correct|
|---|---|---|
|Compiler implementation|The order, meet, search, runtime, composition, decomposition, and normalization rules are implemented as specified.|A bug promotes permission.|
|Membership classifier|`IN_CLASS` and out-of-class reasons are correct for the candidate use.|An out-of-class system enters the compiler as in-class.|
|Adapter|Claim identity, context identity, candidate identity, and class assignment are deterministic and conservative.|Claim relabeling, context erasure, and class shopping.|
|Gap taxonomy|The taxonomy contains the obligation types needed for the class.|A required obligation is not expressible.|
|Gap induction|Every applicable obligation is induced or marked not applicable by a valid artifact.|A load-bearing gap is silently omitted.|
|Profile registry|Profiles are well formed, versioned, audited, and immutable for issued envelopes.|Strong permissions become easier without a visible profile change.|
|Artifact registry|Justification artifacts are live, typed, scoped, and unexpired.|Free text or stale artifacts discharge obligations.|
|Certifiers|Tokens report correct claim, scope, status, expiry, and contract data.|False domain evidence enters as valid evidence.|
|Detail-contract registry|Token schemas and semantic checks are versioned and immutable for issued envelopes.|Malformed payloads pass as evidence.|
|Token registry|Token liveness, revocation, and status are correct at runtime.|Revoked or stale tokens continue to close gaps.|
|Provenance writer|Provenance binds exactly `(τ,g,c,z,x)`.|Tokens are reused across gaps, claims, candidates, or contexts.|
|Authority source|Permission ceilings and rollback capabilities are live and complete.|The compiler authorizes action outside delegation.|
|Runtime context source|Values required by expiry, registries, and authority checks are current.|Missing runtime facts become permission.|

The compiler only names the trusted computing base. It does not remove it.

Request permissions, free text, token names, and the approximate output itself are outside the trust boundary. A benchmark can therefore produce two different kinds of result: it can falsify the compiler if an unsupported permission is emitted, or it can falsify the taxonomy/profile if a real obligation is not expressible or not required.

---

# 6. Running Example: Epic as Evidence Overextension

The Epic sepsis model is a useful running example because it was not a case of no evidence. It was a case of evidence being used for a stronger permission than it supported.

Epic had evidence relevant to:

- approximation quality;
    
- model specification;
    
- calibration;
    
- freshness;
    
- blast radius.
    

But Epic lacked evidence for two obligations that matter for operational rollout:

- clinical utility at the deployed threshold;
    
- distribution shift across deployment populations.
    

This distinction is central. A model can have a respectable AUC and still fail as an operational alert. AUC says something about ranking across thresholds. It does not by itself say that the deployed operating point has acceptable positive predictive value, sensitivity, or clinical utility.

Likewise, validation on one patient population does not automatically support deployment across many hospitals with different geographies, demographics, clinical practices, and baseline risks.

The question is not:

```text
Is Epic good or bad?
```

The question is:

```text
What permission did Epic's evidence actually support?
```

AUC evidence may support diagnostic display or controlled study. It does not by itself support limited rollout across deployment populations, and it certainly does not support automatic action.

The admissibility judgment makes this question explicit.

---

# 7. Gaps, Profiles, Tokens, and Proof Context

The proof context `Γ` contains everything relevant to the authorization question.

A representative proof context includes:

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

These fields play five roles.

First, they fix the object of judgment. `membership` determines whether the candidate belongs to the class governed by the framework. `claim`, `candidate`, and `context` identify what is being asserted, what artifact or action is under consideration, and the setting in which the assertion holds. `scope` limits where the resulting judgment may be used.

Second, they fix the proof obligations. `claim_gaps` records which obligations are induced. `gap_taxonomy_version` fixes the vocabulary of possible obligations. `gap_profile_version` fixes which obligations must be satisfied at each permission level. `detail_contract_registry_version` fixes the schemas and semantic checks that proof tokens must satisfy.

Third, they record the evidence. `proof_tokens` are typed witnesses offered to bound or close gaps. `proof_token_provenance` binds each token to the exact tuple it is allowed to support.

Fourth, they impose scope and temporal constraints. `expiry` states when the judgment ceases to be live. `allowed_use` and `disallowed_use` restrict downstream uses. `authority` imposes ceilings or escalation requirements. `runtime_context` supplies the live facts needed to evaluate expiry, registry status, revocation, and rollback conditions. `derivation` records how the candidate was produced.

Finally, `audit` explains the result. It records which permissions were denied, which gaps blocked them, which tokens were rejected, which runtime checks failed, which authority ceilings applied, and which expiry or scope rules narrowed the outcome.

## 7.0 Membership and Adapters

Membership values are:

```text
IN_CLASS
OUT_OF_CLASS_EXACT
OUT_OF_CLASS_AUTHORIZED_DETERMINISTIC_WRITE
OUT_OF_CLASS_NO_CONSEQUENTIAL_USE
OUT_OF_CLASS_OTHER
```

Every out-of-class reason projects to `OOC`. The reason is kept for audit. Fake proof tokens cannot promote an out-of-class system: membership is checked before token evaluation.

An **adapter** maps an approximate output into a claim class and identities:

```text
c ← induce_claim(A, κ, z, x)
```

It must satisfy five conditions:

1. **Determinism.** Equal inputs produce equal outputs.
    
2. **Identity binding.** Claim identity binds output, class, candidate, and context.
    
3. **Profile coverage.** Each mandatory gap type is induced or validly marked not applicable.
    
4. **Context sensitivity.** Load-bearing context changes affect claim identity, gap identity, or expiry.
    
5. **Profile-conservative class assignment.** The adapter cannot choose a looser compatible class.
    

For the fifth condition, define a preorder on classes:

```text
κ₁ ≼Φ κ₂    iff    ∀h,p. ReqΦ(κ₁,h,p) ≥ ReqΦ(κ₂,h,p)
```

Read `κ₁ ≼Φ κ₂` as: `κ₁` is no looser than `κ₂`. Let `K(A,z,x,u)` be the set of classes compatible with approximate output `A`, candidate `z`, context `x`, and intended use `u`. The assigned class `κ` must satisfy:

```text
∀κ' ∈ K(A,z,x,u).  κ ≼Φ κ'
```

unless excluding `κ'` is justified by a valid `CheckableJustification`. If no conservative class exists, the adapter fails closed and records `CLASS_AMBIGUITY`. This prevents class-shopping: a compatible looser class cannot be selected to obtain a stronger permission.

## 7.1 Gaps

A **gap** is a proof obligation. It names a way the evidence may be insufficient for the requested permission.

A gap has status:

```text
OPEN < BOUNDED < CLOSED
```

`OPEN` means no admissible evidence has been supplied. `BOUNDED` means evidence limits the risk without fully discharging it. `CLOSED` means evidence discharges the obligation for the relevant scope and use.

Examples include:

- `approximation_quality_gap`;
    
- `clinical_utility_gap`;
    
- `distribution_shift_gap`;
    
- `model_specification_gap`;
    
- `calibration_gap`;
    
- `blast_radius_gap`;
    
- `freshness_gap`;
    
- `authority_gap`;
    
- `shadow_mode_validation_gap`;
    
- `post_market_monitoring_gap`.
    

Applied to Epic, `clinical_utility_gap` asks whether PPV and sensitivity are sufficient at the deployed threshold for the intended action class. This is not a variation on AUC. It is a different question.

`distribution_shift_gap` asks whether validation evidence holds on the deployment population. Evidence from one institution is not automatically evidence for another institution.

**Gap induction completeness.** Let `Θ_v` be a versioned gap taxonomy. `induce_gaps(κ,z,x,u,Θ_v)` is complete for profile version `Φ_v` when every applicable required obligation is induced or validly discharged:

```text
Applicable(Θ_v,κ,z,x,u,h) ∧ RequiredBy(Φ_v,κ,h,p)
  ⇒  h ∈ types(G) ∨ ValidNA(h,c,z,x,ArtifactRegistry)
```

This is a trusted-computing-base condition. The compiler cannot require evidence for a gap type the taxonomy does not contain. Failure is closed: if `Φ_v` requires `h`, and `G` contains no gap of type `h`, and there is no valid not-applicable artifact, then every permission requiring `h` is unsatisfied.

**Approximation gap versus model-specification gap.** A critical distinction that the taxonomy must represent explicitly:

`posterior_divergence_gap` or `approximation_gap` asks whether the computed object is close to the ideal object under the supplied model.

`model_specification_gap` asks whether the supplied model is adequate for the real target of action.

These are not the same gap:

```text
approximation certificate:
  approximate posterior is close to assumed posterior

model-specification certificate:
  assumed posterior is close enough to the data-generating or action-relevant target
```

A compiler may license diagnostic use from an approximation certificate alone. It should not license rollout authority against the world from that certificate alone unless the profile also requires `model_specification_gap` to be at least `BOUNDED`. For world-facing inference claims, `ALR` and `AAA` require `model_specification_gap` to be at least `BOUNDED_REQUIRED` unless the claim is explicitly scoped to the supplied model rather than to the external world.

## 7.2 Profiles

A **profile** specifies which gaps are required at which permission levels for a given claim class.

It answers:

```text
For this claim class, what evidence is required before this permission may be granted?
```

Formally:

```text
Φ_v : (κ,p) ↦ PermissionRequirementProfile
```

|Requirement level|Satisfied by|
|---|---|
|`OPEN_ALLOWED`|`OPEN`, `BOUNDED`, or `CLOSED`|
|`BOUNDED_REQUIRED`|`BOUNDED` or `CLOSED`|
|`CLOSED_REQUIRED`|`CLOSED`|

A profile is **well formed** when stronger permissions never require weaker evidence. For `p_strong > p_weak`:

```text
required_status(κ,h,p_strong,Φ_v) ≥ required_status(κ,h,p_weak,Φ_v)
```

or `p_strong` marks `h` not applicable by a valid `CheckableJustification`.

A `CheckableJustification` is valid only if the artifact registry confirms that the artifact exists, has the correct type, covers the gap type, is unexpired, and is scoped to the claim and candidate. Free text is not a valid justification.

A weak clinical AI profile might allow limited rollout when the following gaps are bounded:

```text
approximation_quality_gap
model_specification_gap
calibration_gap
blast_radius_gap
freshness_gap
```

A stronger profile may also require:

```text
clinical_utility_gap
distribution_shift_gap
shadow_mode_validation_gap
post_market_monitoring_gap
```

The compiler does not ask whether evidence is persuasive in ordinary language. It asks whether each obligation has been discharged to the level required by the relevant profile.

A profile is therefore policy in compiler-processable form.

For world-facing inference claims, the profile must distinguish at least `posterior_divergence_gap` and `model_specification_gap`. A token that bounds the first does not bound the second by implication. A profile that allows `ALR` with open model specification is too weak for action authority unless the intended use is explicitly diagnostic or model-internal.

## 7.3 Proof Tokens

A **proof token** is a typed witness offered to bound or close a gap.

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

A token only counts if it is live, valid, scoped correctly, contract-conformant, and provenanced to the exact claim/candidate/context/gap tuple.

A token is not evidence because it has a reassuring name. A freshness token cannot close a clinical utility gap merely because it is called a token. A validation token for one institution cannot support deployment at another merely because both involve the same model.

**Detail contracts.** A token type is not evidence by name. Its payload must satisfy a registered detail contract. Let `Σ_v` be the versioned detail-contract registry.

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

`detail_contract_ok(τ,ρ,Σ_v)` holds only if all seven checks pass:

1. `Σ_v` contains `τ.detail_contract_id`.
    
2. The registry fingerprint equals `τ.detail_contract_hash`.
    
3. The contract token type equals `τ.token_type`.
    
4. `τ.details` satisfies the registered schema.
    
5. Every semantic check passes under `ρ`.
    
6. Every artifact dependency is live, typed, scoped to `(c,z,x)`, and unexpired.
    
7. Token scope and expiry are no wider than the contract permits.
    

Unknown contracts fail closed. Schema mismatch fails closed. Failed semantic checks fail closed. Stale dependencies fail closed. Free text inside `details` has no force unless the contract assigns it force.

## 7.4 Provenance

The provenance relation binds a token to the exact judgment components it supports:

```text
(token, gap, claim, candidate, context)
```

No provenance, no proof.

This prevents evidence reuse across contexts. A clinical utility validation conducted at one institution cannot be submitted as evidence for deployment at another unless the token was issued for that deployment context.

It also prevents token type laundering when the detail-contract registry encodes token/gap compatibility. A token supporting one kind of obligation does not automatically support another.

## 7.5 Audit

The audit field is what makes later accountability possible. It records the profile used, the taxonomy version, the tokens accepted and rejected, the open gaps, the denied stronger permissions, and the reasons for denial.

An informal deployment decision says, “Approved.” A compiled judgment says, “Approved at this permission level, under this profile, with these gaps bounded, these tokens accepted, these tokens rejected, this expiry condition, this authority ceiling, and these stronger permissions denied for these reasons.”

That is the difference between a decision and an admissibility judgment.

## 7.6 Versioning and Immutability

A compile fixes three registry versions:

```text
Θ_v = gap taxonomy version
Φ_v = gap profile version
Σ_v = detail-contract registry version
```

The emitted judgment records version ids and hashes. Runtime revalidation uses the recorded versions. It does not substitute newer versions.

**Taxonomy versioning.** Any taxonomy change creates a new `Θ_v`. This includes adding or removing a gap type, changing applicability predicates, or changing gap metadata semantics. Gap identity includes the taxonomy version:

```text
gap_id = H(Θ_v, claim_id, candidate_id, context_id, gap_type, gap_parameters)
```

A taxonomy shift changes gap identity. Tokens minted under the old taxonomy do not close gaps induced under the new taxonomy unless a new compile creates new provenance.

**Profile versioning.** Any profile change creates a new `Φ_v`. There are no in-place edits after a profile version has issued an envelope. Profile changes are ordered pointwise:

```text
Tightens(Φ₂,Φ₁)
  iff ∀κ,h,p. ReqΦ₂(κ,h,p) ≥ ReqΦ₁(κ,h,p)
```

Tightening may reduce permission. A tightening cannot replace a required status with `NotApplicable`. Relaxation can make a fresh compile stronger, so it is a governance event: every relaxation records a new version, author, reason, diff, effective time, and audit record. Existing envelopes are not upgraded by relaxation.

**Detail-contract versioning.** Detail contracts are immutable per content. Any schema change, semantic-check change, artifact-dependency change, scope-rule change, or expiry-rule change creates a new contract id. `Σ_v` is determined by the set of `(detail_contract_id, detail_contract_hash)` pairs in the registry. Runtime does not reinterpret an old token under a new contract.

**Envelope immutability.** An emitted envelope is immutable. Runtime can only continue it at the same or lower permission. New evidence, a refreshed context, a changed authority envelope, or a different `Θ_v`, `Φ_v`, or `Σ_v` requires a new compile. A new compile may emit a stronger judgment; runtime may not.

---

# 8. The Epic Compile

Under a weak profile, Epic satisfies the required gaps. The profile requires approximation quality, model specification, calibration, blast radius, and freshness. It does not require clinical utility or distribution shift.

The compiler emits:

```text
Γ ⊢ epic_sepsis_model : ALR until ε₁
```

This is not a compiler failure. It is a profile failure. The profile did not ask the questions that mattered, so the compiler could not block the deployment on those grounds.

Under a corrected profile, limited rollout requires clinical utility and distribution shift evidence. Epic has two open gaps:

```text
clinical_utility_gap: OPEN
distribution_shift_gap: OPEN
```

The compiler refuses limited rollout and emits:

```text
Γ ⊬ epic_sepsis_model : ALR
Γ ⊢ epic_sepsis_model : AEX until ε₂
```

Epic may be studied experimentally. It may not be operationally rolled out.

The correction is not a different model. It is the same evidence under a different profile. The framework exposes that the old policy did not require the obligations that would have blocked the unsafe permission.

## 8.1 The Four-Cell Picture

The medical benchmark populates a 2×2 grid: compiler decision by hindsight outcome.

```text
                         Hindsight: harm        Hindsight: benefit
Compiler: ALR            (ALR, deployed, harm)  (ALR, deployed, benefit)
Compiler: < ALR          (<ALR, blocked,        (<ALR, blocked,
                          harm-prevented)        benefit-foregone)
```

The Epic case under the weak profile gives **(ALR, deployed, harm)**: the compiler would have authorized rollout; the model was deployed; harm followed. This falsifies the weak profile.

The corrected profile on the same evidence gives **(<ALR, blocked, harm-prevented)**: the compiler refuses rollout authority and allows only experiment.

A well-evidenced deployment, such as CHARTwatch, occupies the true-positive cell: clinical utility evidence exists, deployment population evidence exists, and the compiler permits operational use.

The benefit-foregone cell is a genuine limitation. A threshold can be too conservative. A model just below a PPV floor might still produce net clinical benefit in a specific care context.

The framework does not prove the threshold is correct. It makes the threshold explicit, auditable, and changeable through profile governance.

This is the point. The same evidence can support different permissions under different profiles. That is not a weakness. It is how the compiler exposes policy instead of hiding it.

---

# 9. The Compiler Discipline

The compiler constructs the judgment. It receives the proof context and emits the greatest permission the context supports.

A representative algorithm is:

1. If membership is not in class, emit `OOC`.
    
2. Induce the claim.
    
3. Induce gaps under a fixed taxonomy.
    
4. If expired, emit `EXP`.
    
5. For each token, check registry status, detail contract, expiry, scope, and provenance.
    
6. Advance gap statuses only through valid witnesses.
    
7. Record structural failures such as provenance mismatch, allowed-use conflict, empty scope, invalid derivation, failed negative controls, and runtime context failure.
    
8. Apply authority ceilings, escalation requirements, and rollback controls.
    
9. Search positive permissions from strongest to weakest.
    
10. Return the first permission whose profile requirements are satisfied.
    
11. Meet the positive result with structural failures and control outcomes.
    
12. Emit the judgment and record blocking reasons for every stronger denied permission.
    

The core discipline is:

```text
No approximation may be used as stronger permission than its evidence,
scope, provenance, expiry, authority, and policy profile jointly support.
```

The compiler enforces five separations.

## 9.1 Requested Permission from Supported Permission

The caller's desired outcome is not evidence. A request for limited rollout does not count as rollout evidence.

## 9.2 Policy from Enforcement

The profile states which gaps are required for which permissions. The compiler enforces the profile mechanically. The same profile, applied to the same evidence, produces the same result.

## 9.3 Token Name from Token Validity

A token does not count because it has a reassuring name. It must satisfy a registered detail contract, including schema checks, semantic checks, artifact dependencies, scope rules, and expiry rules.

## 9.4 Evidence Existence from Evidence Provenance

Evidence exists for the compiler only when it is provenanced to the exact judgment tuple. A token for a different gap, claim, candidate, or context does not support the current judgment.

## 9.5 Structural Admissibility from Domain Truth

The compiler checks that the right kind of evidence was presented in the right form with valid provenance. It does not guarantee that the certifier used good science or that the threshold was morally correct. Those are governance obligations.

The compiler is not a wisdom machine. It is a non-promotion machine.

## 9.6 Expiry, Scope, Use, and Negative Controls

Expiry is evaluated against runtime context `ρ`:

```text
Expired(ε,ρ)
  iff ε.expired=true
   or now(ρ) > ε.expires_at
   or ∃r ∈ ε.expiry_rules. Fires(r,ρ)
```

The runtime context must contain every value required by expiry rules, token registries, detail contracts, and authority checks. Missing dependencies fail closed.

Allowed use narrows permission:

```text
UseOK(u) iff (allowed_use=[] or u ∈ allowed_use) and u ∉ disallowed_use
```

Authority sets a ceiling. If evidence supports `AAA` but authority permits at most `AEX`, the compiler records `ETA`. If authority is absent or a human tradeoff is required, it records `ESC`. If a rollback condition fires and rollback capability exists, it records `ROL`. If rollback capability is missing, it records `ESC` and `ROLLBACK_CAPABILITY_MISSING`.

**Negative controls.** Negative controls are registered pass/fail token types. Examples include placebo slices, pre-period effect checks, shadow outcomes, and known-null detectors. Under `strict_mode`, a missing, invalid, expired, unprovenanced, or failed required negative control records `NEGCTRL_FAILED`, which forces `REF` into the final meet.

## 9.7 Composition and Decomposition

For `n ≥ 1` envelopes:

```text
permission     = meet_n([Ei.permission])
allowed_use    = ∩(Ei.allowed_use)
disallowed_use = ∪(Ei.disallowed_use)
scope          = ∩(Ei.scope)
expiry         = min_expiry(Ei.expiry)
proof_tokens   = ∪(Ei.proof_tokens)
provenance     = ∪(Ei.provenance)
```

Composition cannot widen permission, scope, allowed use, or expiry. A stale or downgraded component cannot be hidden by composition with a fresh component: the meet of its lower permission with any stronger permission remains at most the stale component's value.

Decomposition cannot upgrade a child:

```text
E_child.permission = meet(E_parent.permission, child_permission_floor)
E_child.scope      ⊆ scope_mapping(E_parent.scope)
E_child.expiry     ≤ E_parent.expiry
```

New evidence may strengthen a child only through a separate compile.

---

# 10. Structural Guarantees

The compiler's structural guarantees are intentionally small.

It relies on:

```text
finite permission order
+ meet
+ monotone profiles
+ exact provenance
+ immutable versions
+ runtime downgrade
```

From these ingredients it gets the main non-promotion properties.

The compiler guarantees that:

- invalid tokens do not close gaps;
    
- no provenance means no proof;
    
- expired evidence cannot remain live;
    
- runtime can only downgrade;
    
- composition cannot upgrade weak evidence;
    
- authority ceilings cannot be exceeded;
    
- profile, taxonomy, and contract version changes require a new compile;
    
- absent required gaps fail closed;
    
- the emitted permission is no stronger than the profile, evidence, provenance, authority, scope, and expiry jointly support.
    

The structural soundness claim is relative to the proof context and trusted computing base.

Informally:

> Given correct in-class membership, complete gap induction, fixed taxonomy, fixed profile, valid detail contracts, exact provenance, live runtime context, and honest certifiers, the compiler emits no stronger permission than those constraints jointly support.

This is not a claim of scientific correctness. A valid token can still be scientifically bad if the certifier lied or used poor methodology. A profile can be too weak. A taxonomy can omit a failure mode. A threshold can be wrong.

The compiler's claim is narrower: if the obligation is present, required by the profile, and not discharged by valid evidence, the compiler will not silently grant a permission that depends on it.

---

# 11. Why This Judgment Has This Form

At this point a natural objection arises. Are these objects made up? Who says these are the permission levels? Who says these are the relevant gaps? Who says a judgment should have this shape at all?

The answer has two parts.

First, the concrete policy choices are domain-defined. A hospital, court system, marketplace, or software platform must decide which actions it recognizes, what evidence it requires, what thresholds it accepts, and which actors have authority. The compiler does not derive those choices from first principles.

Second, not every such decision structure is arbitrary. The companion paper shows that admissibility judgments have mathematical forms.

For a claim class `κ`, suppose there is an ideal licensing map:

```text
λκ : Ωκ → P
```

where `Ωκ` is the action-state space and `P` is a finite ordered set of permissions. The map sends each ideal state to the strongest permission that would be sound if all relevant facts were known.

For each permission threshold `p`, define the failure set:

```text
F_p = {ω ∈ Ωκ : λκ(ω) < p}
```

This is the set of states where permission `p` is unsound.

These failure sets are the semantic object behind permissions, gaps, and profiles. They identify where a permission becomes unsound.

The concrete permission labels can be made up. A domain may call them diagnostic display, review, experiment, rollout, automatic action, or something else entirely. But the monotone ordering is not decorative. It is the structure that gives the system its properties.

The total order over permissions lets the compiler ask:

```text
What is the greatest permission supported by this proof context?
```

It also makes non-promotion enforceable. Runtime checks, authority ceilings, expiry, composition, and structural failures operate by meet. They can only preserve or lower the emitted permission. Without an ordered permission set, there is no general notion of “stronger than the evidence supports,” no greatest supported permission, and no algebraic guarantee that composition or runtime revalidation cannot upgrade.

Thus the permission levels are policy interfaces, but the monotone order is structural.

The same is true of gaps. A gap is legitimate when leaving it open corresponds to a domain-recognizable way that a permission can become unsound. `clinical_utility_gap` is not important because of its name. It is important because a model can have adequate AUC while failing at the deployed operating threshold. `distribution_shift_gap` is not important because the framework designer likes the phrase. It is important because evidence from one population may not support deployment on another.

The companion representation theorem says that an approximate consequential system is admissibly compilable exactly when these failure sets admit a finite monotone certifier-observable presentation. Equivalently, the ideal licensing map must factor through a finite obstruction quotient:

```text
Ωκ → finite obstruction quotient → P
```

This is the formal reason the judgment has the shape it does. The compiler is not inventing domain truth. It is evaluating a finite observable shadow of the domain's licensing structure.

This also explains why the framework is not merely a list of hand-picked factors:

- permission levels are domain-defined action interfaces;
    
- the order over permissions is the algebraic structure that enables non-promotion;
    
- gaps are observable generators of permission failure;
    
- profiles specify which generators must be bounded or closed before each permission is allowed;
    
- tokens are certifier-produced witnesses that move a gap from open to bounded or closed;
    
- expiry records when the judgment ceases to be live;
    
- provenance binds evidence to the specific claim, candidate, context, and use.
    

In tame domains, those generators have recognizable mathematical forms. In discrete settings, they may be finite minimal bad patterns. In Noetherian settings, they may correspond to finitely generated ideals, components, or strata of a failure locus. In semialgebraic settings, they may be finite systems of inequalities stable under projection. In o-minimal or tropical settings, they may arise from finite cell decompositions or finite polyhedral shadows.

The details differ by domain, but the structural pattern is the same:

```text
monotone threshold failure
+ finite or tame observable presentation
⇒ finite obstruction basis
⇒ admissibility compiler
```

The main paper therefore makes an operational claim, while the companion paper supplies the representation claim.

The operational claim is that, given a proof context, profile, tokens, provenance, authority, and expiry, the compiler prevents unsupported promotion.

The representation claim is that this is the right kind of object when the domain's action-unsoundness has a finite or tame observable form.

So the framework does not say: these are the one true permissions, these are the one true gaps, or this is the one true policy.

It says something narrower and stronger:

> If a domain has an ordered action structure whose failure regions admit a finite monotone observable presentation, then its approximations can be compiled into admissibility judgments.

The domain supplies the policy. The companion theorem explains when that policy has a form the compiler can enforce.

## 11.1 Grounded Profiles and Generalization

The empirical claim is not that any particular profile is correct. It is that profiles designed on a small set of motivating cases can generalize to held-out cases when they are grounded in domain failure modes rather than fitted to cases.

For mathematically grounded systems, generalization is expected because the gap taxonomy is derived from the mathematics, not from the cases. The cases are witnesses to a structure that exists independently of them.

For policy-grounded systems, generalization is expected for a different reason: if the profile is **grounded** — every requirement maps to a named, domain-recognizable failure mode — then it should not block cases where that failure mode is genuinely mitigated, and it should block cases where it is genuinely present.

A gap type `h` is **domain-grounded** for class `κ` under profile `Φ` when there exists a named, domain-recognizable failure mode `F(h,κ)` such that:

```text
EffΓ(h) = OPEN  ⇒  F(h,κ) is an unmitigated risk for action authority p
```

Every gap requirement at every permission level corresponds to a real thing that can go wrong if the gap is left open. A profile `Φ` is **grounded** for class `κ` when every `BOUNDED_REQUIRED` or `CLOSED_REQUIRED` entry in `Φ(κ,·)` is domain-grounded.

Groundedness is a trusted-computing-base condition, not a compiler check. The profile designer asserts it; domain review confirms it; the compiler enforces it. The medical profile v2 is grounded: `clinical_utility_gap` maps to the failure mode model deployed without operating-point validation; `distribution_shift_gap` maps to evidence collected on a different population than the deployment population.

## 11.2 Profile Sensitivity and the Surgical Property

Lemma M and Corollary M1 establish that permission is Lipschitz in the profile:

```text
|Compile(Γ,Φ') - Compile(Γ,Φ)| ≤ d(Φ,Φ')
```

where `d(Φ,Φ')` is the number of differing profile entries. A profile that differs from the intended profile by `k` entries cannot produce an output more than `k` permission steps wrong. The profile designer does not need to get the boundary exactly right; they need to get it approximately right.

A profile is **overfit** to a training case set if it contains requirements that are not domain-grounded — requirements added to make specific training cases pass or fail rather than to represent real failure modes. An overfit profile will generalize poorly: it will block well-evidenced held-out cases that happen to pattern-match the training refusals.

Groundedness is the guard against overfitting.

The **surgical property** of a profile upgrade is:

```text
Tightens(Φ₂,Φ₁)  ∧  ∀h ∈ new_requirements(Φ₂). domain-grounded(h,κ)
  ⇒  Φ₂ blocks exactly the cases where the new failure mode is unmitigated
     and does not additionally block cases where it is mitigated
```

Profile v1 → v2 in the medical benchmark satisfies this: adding `clinical_utility_gap` as `BOUNDED_REQUIRED` at ALR blocks deployments with no utility evidence and does not block deployments that have a valid clinical utility token.

---

# 12. Evidence: Does This Actually Work?

The evidence section asks whether the framework behaves as claimed.

The tests are not the proof. They are executable attempts to falsify the proof obligations, the implementation, and the profile/taxonomy boundary.

## 12.1 Profile Calibration Against Published Standards

Profile V1 requires AUC bounded, model specification bounded, calibration bounded, blast radius bounded, and freshness bounded. It does not require operating-point clinical utility evidence or local population validation.

FDA Draft Guidance for AI-enabled device software functions requires sensitivity, specificity, PPV, and NPV with pre-specified acceptance criteria and confidence intervals. Multi-site validation is recommended. V1 fails this standard.

NHS RCR guidance for AI deployment in medical imaging requires shadow-mode testing on the local population before go-live, pre-defined acceptance criteria before procurement, and an ongoing post-implementation evaluation plan before deployment. V1 fails this standard.

Profile V2 adds `clinical_utility_gap` and `distribution_shift_gap`, covering the operating-point utility and population-specific validation obligations. But V2 is still missing two deployment-phase obligations: `shadow_mode_validation_gap` and `post_market_monitoring_gap`.

Profile V3 adds these two gaps. It is not invented from the Epic case. It is derived from regulatory text.

Compiler results across V1, V2, and V3:

|Case|Evidence|V1|V2|V3|
|---|---|---|---|---|
|P1|Core only — Epic pattern|ALR|AEX|AEX|
|P2|V2-complete: utility + shift|ALR|ALR|AEX|
|P3|V3-complete: all gaps bounded|ALR|ALR|ALR|
|P6|Missing shadow mode only|ALR|ALR|AEX|
|P7|Missing monitoring plan only|ALR|ALR|AEX|

The exercise of writing V2 in compiler-processable form forced the question of what the regulatory standards actually require, which revealed that V2 was incomplete, producing V3. The incompleteness of V2 was not visible from the Epic case alone. It became visible when the profile was matched against external standards.

## 12.2 Algebraic and Structural Tests

`EC-003` tests the algebra, composition, decomposition, runtime, anti-laundering, token reuse, provenance identity, rollback, and final-meet truth table. Result: 11,178 tests, 0 falsifications.

`EC-004` tests profile well-formedness, artifact validation, free-text rejection, greatest-permission search, adapter determinism, context sensitivity, and adversarial domain suites. Result: 11,245 cumulative tests, 0 falsifications.

|Evidence class|Target|Locus|
|---|---|---|
|Algebraic checks|Order, meet, associativity, idempotence, normalization|EC-003|
|Runtime checks|Expiry, replay, skew, missing dependencies, registry failure|EC-003|
|Composition checks|Stale or narrow components hidden by fresh ones|EC-003|
|Provenance adversaries|Token reuse across ids|EC-003, EC-004|
|Profile checks|Stronger permissions easier than weaker ones|EC-004|
|Property checks|Descending search not returning greatest satisfiable permission|EC-004|
|Registry checks|Free text, wrong type, wrong scope, expired artifacts|EC-004|
|Adapter adversaries|Hidden context changes and class ambiguity|EC-004|

No structural conjectures remain open in the current structural test battery. Domain-scientific adequacy belongs to domain certifiers.

## 12.3 Medical Benchmark: MED-001

MED-001 is a prospective benchmark: real models run against real PhysioNet Challenge 2019 data; compiler output verified against oracle expectations.

```text
11/11 oracle cases: 0 violations
9/9 adversarial cases: 0 violations
```

The benchmark produced the V1→V2→V3 profile progression. V1 authorizes the Epic failure pattern. V2 adds `clinical_utility_gap` and `distribution_shift_gap`, blocking it. V3 adds `shadow_mode_validation_gap` and `post_market_monitoring_gap`, encoding deployment-phase obligations that V2 missed.

Each profile transition was forced by matching the profile against either a failure case or external standard — a task the framework made tractable by requiring policy to be explicit and machine-checkable.

One taxonomy correction: `clinical_utility_gap` and `distribution_shift_gap` were not in the initial taxonomy. They were induced by the benchmark's falsification of V1.

## 12.4 Multi-Domain Retrospective Audit: CASE-LIB-001

CASE-LIB-001 is a retrospective benchmark: for 16 real-world AI deployments with documented harmful outcomes, what would the compiler have emitted given the evidence available at deployment time?

The 16 cases span five domains: medical, criminal justice, employment, autonomous systems, and government benefits. All cases have public source records sufficient to reconstruct gap statuses.

Three profile tiers were pre-registered before running:

- **Tier 0 — min_viable:** requires only `approximation_quality_gap` bounded. Represents the implicit deployment standard: “does the model work at all?”
    
- **Tier 1 — reasonable_deployment:** requires `approximation_quality + model_specification + blast_radius + authority` bounded. A single cross-domain profile. No domain-specific gaps.
    
- **Tier 2 — per-domain:** Tier 1 plus one to two domain-specific gaps.
    

All 48 pre-registered predictions matched compiler output.

```text
Tier 0 (AUC only):              5/16 cases blocked
Tier 1 (reasonable deployment): 16/16 cases blocked
Tier 2 (per-domain):            16/16 cases blocked
```

The Tier 1 result is the load-bearing claim. A single four-gap cross-domain profile would have blocked all 16 documented harms. The profile was not fitted to these cases. It was derived independently from the observation that model specification, blast radius, and authority gaps appear across all five domains.

The Tier 0 result quantifies what the industry's implicit deployment standard missed. AUC-only blocked 5 cases where basic technical validity was never established. It passed 11 cases where the model performed on its stated target but was deployed at the wrong action class, without blast-radius controls, without authority checks, or using a proxy that diverged from the relevant target.

Two new gap types were induced.

**`individual_population_gap`.** A statistical model that accurately characterizes outcomes for a population provides no certifiable basis for predicting whether a specific individual will have that outcome. Population-level calibration is not individual-level predictive validity.

**`feedback_coupling_gap`.** A model deployed in a decision-making system changes the distribution of future training data through its own outputs, creating self-reinforcing error patterns invisible to standard distribution-shift analysis.

Both gap types follow the same induction pattern as earlier benchmarks: a case exposes over-authorization, the taxonomy lacks a gap, and adding the gap produces the correct output.

## 12.5 Probabilistic Inference Benchmark: PGM-001

PGM-001 tested inference certificates over Bayesian-network workloads.

```text
0 violations across 12 oracle-checked cases
0 violations across 316 parametrized tests
```

The benchmark also found that the workload design did not stress the approximate regime enough: many networks fit exact variable elimination inside fixed memory tiers, so tightness remains undermeasured.

The benchmark produced one taxonomy/profile correction. `posterior_divergence_gap` was not enough. On deliberately misspecified models, the framework correctly certified approximation error against the supplied model, but action authority was too strong relative to the external world.

Adding `model_specification_gap` corrected this. The compiler did what the then-current profile asked; the falsified component was the taxonomy/profile.

## 12.6 Adversarial Attacks

The adversarial experiments split into two categories.

The compiler structurally blocks:

- authority ceiling spoofing;
    
- empty profile;
    
- invalid token status;
    
- expired token;
    
- provenance mismatch;
    
- composition upgrade.
    

The compiler can be broken by trusted-computing-base violations:

- falsified gap statuses;
    
- fabricated bound values;
    
- token type laundering if the registry does not prevent it;
    
- membership spoofing;
    
- manually closing gaps without tokens;
    
- profile rollback if deprecated profiles are not rejected.
    

This is the intended boundary. The compiler fails where it said it would fail: at the trusted computing base.

## 12.7 Current Evidence Status

|Claim|Status|
|---|---|
|Algebraic non-promotion|Supported by proof and EC-003|
|Profile/search non-promotion|Supported by proof and EC-004|
|Token/provenance anti-laundering|Supported by proof, EC-003, and EC-004|
|Runtime non-upgrade|Supported by proof and EC-003|
|Profile Lipschitz sensitivity|Supported by proof|
|Grounded profile non-authorization|Supported by proof|
|Profile surgical property|Supported by MED-001 and CASE-LIB-001|
|Inference structural soundness|Supported by PGM-001 on checked cases|
|Inference tightness|Not yet measured in the interesting regime|
|Inference taxonomy completeness|Falsified once; patched with `model_specification_gap`|
|Clinical taxonomy completeness|Falsified once; patched with `clinical_utility_gap`, `distribution_shift_gap`|
|Cross-domain profile generalization|Supported by CASE-LIB-001 Tier 1|
|Retrospective taxonomy completeness|Two new gap types induced: `individual_population_gap`, `feedback_coupling_gap`|
|Kernel-family coverage|Open instrumentation task|
|GasTown multi-agent class benchmark|Pending|

The important result is not that every benchmark passed. The important result is that the framework failed in the right place in three separate domains, through the same mechanism each time: a case where the emitted permission was too strong relative to what a domain expert would accept. In every instance the correction was a profile or taxonomy change, not a compiler change.

## 12.8 What the Evidence Supports

The evidence supports:

- structural non-promotion;
    
- provenance anti-laundering;
    
- runtime downgrade;
    
- profile sensitivity;
    
- taxonomy/profile correction as the right failure mode;
    
- cross-domain recurrence of some gap types.
    

The evidence does not prove:

- all relevant gaps are known;
    
- thresholds are correct;
    
- certifiers are honest;
    
- all domains are admissibly compilable;
    
- retrospective success guarantees prospective safety.
    

---

# 13. Related Work

This paper builds on several traditions.

Access-control systems define when an actor has authority to perform an action. Capability systems make authority explicit and transferable only through controlled mechanisms. Information-flow systems use labels and lattices to prevent data from flowing into unauthorized contexts. Trust-management systems bind authorization to credentials. Runtime monitors enforce safety properties during execution. Proof-carrying code and proof-carrying authorization require evidence before execution or access.

These systems provide the closest ancestors of the admissibility compiler.

The difference is that approximate consequential systems require a judgment about what an approximation may authorize. A metric, score, posterior, retrieval result, or agent plan is not itself authority. It must be compiled into authority through scoped, live, provenanced evidence.

Model cards, datasheets, AI governance frameworks, clinical validation standards, and legal AI audits address adjacent problems. They specify or document evidence. But documentation alone does not prevent downstream promotion. A model card can say a model was validated in one population; it does not mechanically prevent reuse in another. A governance checklist can ask whether evidence exists; it does not necessarily bind that evidence to permission levels, expiry, provenance, and authority ceilings.

The novelty here is not the use of orders, meets, credentials, or provenance individually. Those are well understood.

The contribution is the compiled object and admissibility discipline for approximate consequential systems:

- permission-valued judgments;
    
- explicit proof contexts;
    
- ordered permission levels;
    
- gap profiles;
    
- exact evidence provenance;
    
- live scoped evidence;
    
- expiry;
    
- immutable envelopes;
    
- runtime non-upgrade;
    
- compiler-processable policy;
    
- separation of evidence from permission.
    

This is not “formal methods for AI” generally. It is an authorization discipline for approximate evidence.

---

# 14. Limitations

The compiler does not choose the right policy.

It does not choose the right threshold.

It does not verify scientific truth.

It does not guarantee certifier honesty.

It does not prevent all profile mistakes.

It does not discover missing gaps automatically in every domain.

It does not guarantee that a conservative refusal is socially optimal.

It does not prove all domains admit finite monotone observable failure structure.

It does not make retrospective audits equivalent to prospective validation.

A benefit-foregone case is possible. A profile may block a deployment that would have helped. The framework's response is not that this cannot happen. The response is that the refusal is auditable because the profile is explicit.

A false-permissive case is also possible. If the taxonomy omits a failure mode, if the profile does not require it, if certifiers lie, if gap statuses are hand-written, or if deprecated profiles remain available, the compiler can authorize too much.

The framework's value is that these failures become locatable. They are no longer hidden inside informal judgment. They occur at named boundaries: taxonomy, profile, certifier, registry, context construction, authority source, or runtime context.

The framework is powerful but not magical. Its value is that it makes over-authorization, under-authorization, and governance failures explicit.

---

# 15. Conclusion

Approximate outputs should not authorize action directly.

They should authorize action only through admissibility judgments.

The compiler does not make weak evidence strong. It gives weak evidence a weak license, strong evidence a stronger license, and unsupported escalation an auditable refusal.

The concrete permission labels are domain-defined. The monotone order is structural. The concrete gaps are domain-grounded. The compiler enforces the profile that ties them together. The companion theorem explains when this whole object has a finite or tame observable form.

The central contribution is a mechanical boundary between evidence and permission.

---

# Appendix A. Notation

|Symbol|Meaning|
|---|---|
|`Γ`|Proof context|
|`z`|Candidate artifact, output, claim, result, or action|
|`p`|Permission or control outcome|
|`ε`|Expiry condition|
|`κ`|Claim class|
|`c`|Claim|
|`x`|Context|
|`u`|Intended use|
|`P`|Finite permission chain|
|`Θ_v`|Gap taxonomy version|
|`Φ_v`|Gap profile version|
|`Σ_v`|Detail-contract registry version|
|`T`|Proof tokens|
|`Π`|Provenance records|
|`ρ`|Runtime context|
|`g`|Gap|
|`EffΓ(g)`|Effective gap status under proof context `Γ`|
|`Prov(τ,g,c,z,x)`|Exact provenance relation|
|`λκ`|Ideal licensing map for class `κ`|
|`Ωκ`|Action-state space for class `κ`|
|`F_p`|Failure set for permission threshold `p`|

---

# Appendix B. Permission Algebra

Let `P` be a finite total order of permission outcomes, where lower elements are more restrictive and higher elements are stronger permissions.

A representative order is:

```text
OOC ≤ EXP ≤ REF ≤ UNS ≤ ETA ≤ ESC ≤ ROL ≤ DIA ≤ REV ≤ AEX ≤ ALR ≤ AAA
```

Define meet as minimum in this order:

```text
meet(p,q) = min(p,q)
```

For a finite nonempty list `L`:

```text
meet_n(L) = min(L)
```

The compiler emits one final outcome. Positive permissions and restrictive control outcomes live in the same order because the compiler must return a single continuation. A live rollback condition, expiry, refusal, or authority ceiling must be able to dominate positive evidence.

---

# Appendix C. Core Definitions

## Definition C.1: Gap

A gap is a proof obligation:

```text
g = (gap_id, gap_type, status, metadata)
```

where:

```text
status ∈ {OPEN, BOUNDED, CLOSED}
```

with:

```text
OPEN < BOUNDED < CLOSED
```

## Definition C.2: Profile

A profile maps claim classes, gaps, and permissions to requirement levels:

```text
ReqΦ(κ,h,p) ∈ {OPEN_ALLOWED, BOUNDED_REQUIRED, CLOSED_REQUIRED}
```

A profile is well formed when stronger permissions never require weaker evidence than weaker permissions.

For `p_strong > p_weak`:

```text
ReqΦ(κ,h,p_strong) ≥ ReqΦ(κ,h,p_weak)
```

unless the gap is validly marked not applicable.

## Definition C.3: Token Support

A proof token `τ` supports a gap `g` at level `CLOSED` only if:

```text
τ.status = VALID
∧ Live(τ.expiry,ρ)
∧ detail_contract_ok(τ,ρ,Σ_v)
∧ scope_ok(τ,c,z,x)
∧ g.gap_id ∈ τ.closes_gaps
```

It supports `BOUNDED` analogously when `g.gap_id ∈ τ.bounds_gaps`.

## Definition C.4: Provenance

A token supports a gap only with exact provenance:

```text
Prov(τ,g,c,z,x)
```

holds iff there exists a provenance record matching the token, gap, claim, candidate, and context.

## Definition C.5: Effective Gap Status

For a gap `g`:

```text
EffΓ(g) = CLOSED
```

if there exists a valid, live, contract-conformant, scoped, provenanced token closing `g`.

```text
EffΓ(g) = BOUNDED
```

if there exists a valid, live, contract-conformant, scoped, provenanced token bounding `g`, and no closing token.

```text
EffΓ(g) = OPEN
```

otherwise.

---

# Appendix D. Compiler Algorithm

A reference compiler is:

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
        if (
            profile_exists(kappa, p, Phi_v)
            and gaps_ok(G, eff, kappa, p, Phi_v)
            and use_ok(c)
            and in_scope(z)
        ):
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

# Appendix E. Proofs

## Lemma 1. Meet Laws

**Statement.** `meet = min` over a finite total order. Therefore meet is commutative, associative, idempotent, and order independent. `meet_n(L)` is the greatest lower bound of finite nonempty `L`.

**Proof.** Since `P` is a total order, every pair has a minimum. For any `p,q ∈ P`, `min(p,q) = min(q,p)`, so meet is commutative. For any `p,q,r ∈ P`, `min(min(p,q),r) = min(p,min(q,r)) = min(p,q,r)`, so meet is associative. For any `p`, `min(p,p)=p`, so meet is idempotent. For a finite nonempty list, the iterated minimum is independent of evaluation order and equals the greatest element that is less than or equal to every member of the list. ∎

## Lemma 2. Profile Satisfiability Is Downward Closed

**Statement.** Under a well-formed profile, if a stronger permission `p_strong` is satisfiable by effective gap statuses `Eff`, then any profiled weaker permission `p_weak < p_strong` is also satisfiable by `Eff`.

**Proof.** A well-formed profile requires that stronger permissions demand evidence at least as strong as weaker permissions. Thus for every gap `h`:

```text
ReqΦ(κ,h,p_strong) ≥ ReqΦ(κ,h,p_weak)
```

If `Eff` satisfies the stronger requirement, then it satisfies the weaker requirement. Since this holds for every required gap, `p_weak` is satisfiable whenever `p_strong` is satisfiable. ∎

## Lemma 3. Descending Search Returns the Greatest Satisfiable Positive Permission

**Statement.** If the compiler searches positive permissions from strongest to weakest and returns the first satisfiable permission, it returns the greatest satisfiable positive permission.

**Proof.** The positive permission list is ordered from strongest to weakest. When the search reaches the first satisfiable permission `p`, every stronger permission has already been tested and found unsatisfiable. Therefore no satisfiable permission stronger than `p` exists. Since `p` is satisfiable, it is the greatest satisfiable positive permission. ∎

## Lemma 4. Profile Tightening Cannot Promote

**Statement.** If profile `Φ₂` tightens profile `Φ₁`, then for any proof context `Γ`:

```text
Compile(Γ,Φ₂) ≤ Compile(Γ,Φ₁)
```

ignoring independent structural or control meets that are identical across both compiles.

**Proof.** Tightening means every requirement under `Φ₂` is at least as strong as the corresponding requirement under `Φ₁`. Therefore any permission satisfiable under `Φ₂` is also satisfiable under `Φ₁`. The set of satisfiable permissions under `Φ₂` is a subset of the satisfiable permissions under `Φ₁`. The greatest satisfiable permission under `Φ₂` cannot exceed the greatest satisfiable permission under `Φ₁`. Final structural meets can only lower both outputs. ∎

## Lemma 5. Class Shopping Fails Closed

**Statement.** If the adapter must choose a class no looser than every compatible class, or fail with class ambiguity, then a compatible looser class cannot be selected to obtain stronger permission.

**Proof.** Let `K(A,z,x,u)` be the set of compatible classes. The adapter must assign a class `κ` such that for every compatible `κ'`, `κ` is no looser than `κ'` under the profile preorder. Therefore the assigned class has requirements at least as strong as any looser compatible class. If no such conservative class exists, the adapter fails closed. Thus class assignment cannot be used to select a weaker profile and obtain a stronger permission. ∎

## Lemma 6. Absent Required Gaps Fail Closed

**Statement.** If a profile requires gap type `h`, and the induced gap set contains no gap of type `h`, and no valid not-applicable artifact exists, then any permission requiring `h` is unsatisfied.

**Proof.** A permission is satisfiable only if every required gap reaches the required status. If a required gap is absent and not validly marked not applicable, it cannot have a bounded or closed effective status. It is therefore treated as open or unsatisfied. Any permission requiring it is unsatisfiable. The descending search must return a lower permission or `UNS`. ∎

## Lemma 7. No Provenance, No Proof

**Statement.** Any non-open effective gap status has an explicit provenanced witness.

**Proof.** Every gap begins with status `OPEN`. The only rules that advance a gap to `BOUNDED` or `CLOSED` require a token that supports the gap and exact provenance matching token, gap, claim, candidate, and context. Therefore if `EffΓ(g)` is not `OPEN`, at least one valid provenanced token exists as a witness. ∎

## Lemma 8. Invalid Token Details Do Not Close Gaps

**Statement.** Unknown contracts, schema mismatch, failed semantic checks, stale dependencies, invalid status, expired tokens, and scope violations cannot advance a gap status.

**Proof.** Token support is considered only after registry validity, detail-contract conformance, liveness, and scope checks pass. If any such check fails, the token is ignored. Since ignored tokens are not considered in the rules advancing `EffΓ(g)`, they cannot move a gap from `OPEN` to `BOUNDED` or `CLOSED`. ∎

## Lemma 9. Token Reuse Cannot Launder Proof

**Statement.** A token for a different gap, claim, candidate, or context cannot support the current gap.

**Proof.** The provenance relation requires equality on token, gap, claim, candidate, and context. If any component differs, `Prov(τ,g,c,z,x)` fails. Since token support requires provenance, the token cannot advance the current gap. ∎

## Lemma 10. Composition Cannot Widen

**Statement.** A composed envelope cannot exceed any component in permission, scope, allowed use, or expiry.

**Proof.** Composition defines permission as the meet of component permissions, which is less than or equal to each component. Scope and allowed use are intersections, so they cannot be wider than any component. Disallowed use is a union, so restrictions can only accumulate. Expiry is the minimum expiry, so the composed envelope expires no later than any component. ∎

## Lemma 11. Decomposition Cannot Upgrade

**Statement.** A child envelope derived from a parent cannot exceed the parent in permission, scope, or expiry.

**Proof.** The child permission is the meet of the parent permission and any child permission floor. A meet cannot exceed either operand. The child scope is constrained to be a subset of the mapped parent scope. The child expiry is no later than the parent expiry. Therefore decomposition cannot upgrade. ∎

## Lemma 12. Runtime Cannot Upgrade

**Statement.** Runtime revalidation cannot increase the permission of an issued envelope.

**Proof.** Runtime revalidation computes a meet containing the issued permission and any downgrading outcomes from live checks. A meet cannot exceed any element it contains. Therefore runtime permission is less than or equal to issued permission. ∎

## Lemma 13. Runtime Is Idempotent Under Fixed Context

**Statement.** Revalidating the same envelope twice under the same runtime context produces the same result as revalidating once.

**Proof.** Under fixed runtime context, the same live checks produce the same downgrading outcomes. Meeting the same finite set of outcomes twice is idempotent by Lemma 1. Therefore `Runtime(Runtime(E,ρ),ρ) = Runtime(E,ρ)`. ∎

## Lemma 14. Runtime Is Monotone Under Worse Context

**Statement.** If runtime context `ρ'` contains all downgrades of `ρ` and possibly more, then:

```text
Runtime(E,ρ') ≤ Runtime(E,ρ)
```

**Proof.** Runtime computes a meet of the issued permission and the downgrading outcomes produced by context. If `ρ'` has all downgrades of `ρ` plus possibly more, then the meet under `ρ'` contains every element in the meet under `ρ` and possibly additional lower elements. Adding elements to a meet can only preserve or lower the result. ∎

## Lemma 15. Version Changes Do Not Upgrade Runtime

**Statement.** Runtime cannot upgrade an issued envelope by applying a different taxonomy, profile, or detail-contract version.

**Proof.** An issued envelope records the taxonomy version, profile version, and detail-contract registry version used at compile time. Runtime revalidation uses those recorded versions. It does not reinduce gaps, substitute profiles, or reinterpret token details under newer versions. A different version requires a new compile. Therefore runtime cannot upgrade by version substitution. ∎

## Theorem A. Positive Soundness

**Statement.** Assume in-class membership, live expiry, conforming adapter, profile-conservative class assignment, complete gap induction under fixed taxonomy, fixed well-formed profile, registered detail-contract conformance, complete runtime context, and live-registry semantics. Then the compiler's positive-permission search returns the greatest satisfiable positive permission.

**Proof.** By Lemma 6, absent required gaps fail closed. By Lemma 7, non-open gaps have provenanced witnesses. By Lemma 8, invalid token details do not advance gaps. By Lemma 2, profile satisfiability is downward closed. By Lemma 3, descending search returns the greatest satisfiable positive permission. Therefore the positive search result is the greatest positive permission supported by the effective gap statuses under the profile. ∎

## Theorem B. Non-Promotion

**Statement.** The final emitted permission is no greater than the best positive permission.

```text
p_final ≤ best_positive
```

**Proof.** The final permission is computed as a meet containing `best_positive` and any structural or control outcomes. A meet cannot exceed any of its operands. Therefore `p_final ≤ best_positive`. ∎

## Theorem C. Structural Soundness

**Statement.** Under the assumptions of Theorem A, the emitted permission is no stronger than membership, expiry, gap evidence, provenance, scope, allowed use, authority, derivation, runtime context, negative controls, and control obligations jointly support.

**Proof.** Out-of-class membership halts at `OOC`. Expiry halts or downgrades to `EXP`. Valid tokens advance gaps only with detail-contract conformance and exact provenance. The positive search returns the greatest satisfiable positive permission. Structural failures add restrictive outcomes such as `REF`. Authority, escalation, and rollback add control outcomes. The final result is a meet of the positive result and all applicable structural/control outcomes. By Lemma 1, the meet cannot exceed any constraint. ∎

## Theorem D. Composition Soundness

**Statement.** A composed envelope cannot exceed any component in permission, scope, allowed use, or expiry.

**Proof.** This follows directly from Lemma 10. ∎

## Theorem E. Decomposition Soundness

**Statement.** A child envelope cannot exceed its parent in permission, scope, or expiry. Recomposing children cannot exceed the parent.

**Proof.** The first claim follows from Lemma 11. Recomposing children takes meets and intersections by Lemma 10. Since no child exceeds the parent, their composition cannot exceed the parent. ∎

## Theorem F. Runtime Soundness

**Statement.** Runtime revalidation cannot upgrade an issued envelope. It is idempotent under fixed context and monotone under worse context.

**Proof.** Runtime non-upgrade follows from Lemma 12. Idempotence follows from Lemma 13. Monotonicity under worse context follows from Lemma 14. ∎

## Theorem G. Anti-Laundering

**Statement.** No stale or downgraded component can be hidden by composition with a fresh or stronger component.

**Proof.** Composition computes permission by meet. If one component is stale or downgraded, its permission is lower. The meet of that lower permission with any stronger permission remains no greater than the stale or downgraded component. Thus a fresh component cannot hide or upgrade the stale one. ∎

## Theorem H. Fake-Token Non-Promotion

**Statement.** Out-of-class membership blocks token evidence.

**Proof.** The compiler checks membership before token evaluation. If membership is out of class, it emits `OOC` and halts. Since tokens are never evaluated, fake tokens cannot promote an out-of-class input. ∎

## Theorem I. Domain Non-Theorem

**Statement.** Structural soundness does not imply scientific correctness of domain evidence.

**Proof.** The compiler checks token validity, liveness, provenance, scope, expiry, and contract conformance. It does not verify that the certifier used valid science or that the certified ideal object is the right one for the domain. For example, a certificate may bound approximation error relative to an assumed posterior without proving that the assumed posterior is an adequate model of the world. That requires a separate model-specification obligation. Therefore structural soundness does not imply scientific correctness. ∎

## Theorem J. Class-Shopping Non-Promotion

**Statement.** Under profile-conservative class assignment, a compatible looser class cannot be used to obtain stronger permission.

**Proof.** This follows from Lemma 5 and Theorem A. The adapter either assigns a class no looser than all compatible classes or fails closed. Under that assigned class, the positive search returns the greatest satisfiable permission. Since no looser compatible class can be selected, class shopping cannot promote. ∎

## Theorem K. Profile-Version Non-Upgrade

**Statement.** Runtime cannot upgrade an issued envelope by applying a relaxed profile version.

**Proof.** Runtime uses the profile version recorded in the issued envelope. It does not substitute a later relaxed profile. A compile under a relaxed profile is a new judgment, not a runtime continuation of the old one. Therefore runtime cannot upgrade through profile relaxation. ∎

## Theorem K′. Taxonomy-Version Non-Upgrade

**Statement.** Runtime cannot upgrade an issued envelope by applying a different gap taxonomy version.

**Proof.** Runtime uses the taxonomy version recorded in the issued envelope. It does not reinduce gaps. Gap identity embeds the taxonomy version, so old provenance cannot close newly induced gaps by name alone. A different taxonomy requires a new compile. ∎

## Theorem L. Detail-Contract Non-Upgrade

**Statement.** Runtime cannot upgrade an issued envelope by interpreting an old token under a newer detail contract.

**Proof.** Runtime uses the contract id and hash recorded through the token and registry version. Contract content changes create a new contract id and registry version. Reinterpretation under the newer contract requires a new compile. Therefore runtime cannot upgrade an issued envelope by contract substitution. ∎

## Lemma M. Unit Profile Tightening Bounds Permission Change by One Step

**Statement.** Let profiles `Φ` and `Φ'` differ on exactly one entry, where `Φ'` tightens that entry by one requirement level and all other entries are equal. Then for any proof context `Γ`:

```text
Compile(Γ,Φ') ≤ Compile(Γ,Φ)
Compile(Γ,Φ') ≥ Compile(Γ,Φ) - 1
```

where permission difference is measured in steps of the positive permission order.

**Proof.** The upper bound follows from Lemma 4: tightening cannot promote.

For the lower bound, let `p* = Compile(Γ,Φ)`. If the changed requirement is above `p*`, then it does not affect the satisfiability of `p*`, so the output remains `p*`.

If the changed requirement applies at `p*`, it can make `p*` unsatisfiable. But because the profile differs at only one permission entry and well-formed profiles require weaker permissions to demand no stronger evidence than stronger permissions, the next weaker permission remains satisfiable unless independently blocked. Such independent blockage would already have contradicted downward closure under `Φ`. Therefore the output drops by at most one permission step. ∎

## Corollary M1. Permission Is Lipschitz in the Profile

**Statement.** Let `d(Φ,Φ')` be the number of differing profile entries. Then for any proof context `Γ`:

```text
|Compile(Γ,Φ') - Compile(Γ,Φ)| ≤ d(Φ,Φ')
```

**Proof.** Transform `Φ` into `Φ'` one differing entry at a time. By Lemma M, each unit entry change changes permission by at most one step. Applying this inductively over all differing entries gives the bound. ∎

## Theorem N. Grounded Profiles Do Not Silently Authorize Unmitigated Failure Modes

**Statement.** Let `Φ` be a grounded profile for class `κ`. Let `Γ` be any in-class proof context. Let `h` be any gap type such that `F(h,κ)` is a named failure mode and `EffΓ(h)=OPEN`. Then:

```text
Compile(Γ,Φ) < p
```

for every permission level `p` at which:

```text
Φ(κ,h,p) ≥ BOUNDED_REQUIRED
```

**Proof.** Since `Φ` requires `h` to be at least bounded for permission `p`, profile satisfiability at `p` requires `EffΓ(h) ≥ BOUNDED`. But `EffΓ(h)=OPEN`. Therefore permission `p` is not satisfiable. By Lemma 3, descending search returns the greatest satisfiable permission, which must be strictly below `p`. ∎

---

# Appendix F. Representation Theorem Summary

The companion paper proves the representation result that explains when the judgment form is available.

For a claim class `κ`, let:

```text
λκ : Ωκ → P
```

be the ideal licensing map, where `Ωκ` is the action-state space and `P` is a finite permission chain.

For each permission threshold `p`, define:

```text
F_p = {ω ∈ Ωκ : λκ(ω) < p}
```

The main theorem states that the following are equivalent, relative to a monotone certifier language:

1. The threshold failure sets `F_p` are finitely generated by certifier-observable obstruction predicates.
    
2. The ideal licensing map factors through a finite monotone certifier-observable quotient.
    
3. There exists a bounded, monotone, threshold-complete compiler for the class.
    

In diagram form:

```text
Ωκ → finite obstruction quotient → P
```

This theorem separates soundness from sharpness. A constant-bottom compiler is sound for every domain, because it never authorizes anything strong. But it is sharp for almost none. Sharpness requires the compiler's denial regions to match the ideal failure sets.

The theorem also explains why admissibility judgments have finite/tame forms in many domains. In well-quasi-ordered discrete domains, upward failure sets have finite minimal bad bases. In Noetherian regimes, failure loci may have finite generators, components, or strata. In semialgebraic regimes, projection preserves finite definability. These are different mathematical routes to the same operational object:

```text
finite obstruction basis
⇒ finite permission-valued compiler
```

The main paper uses this theorem as a grounding result, not as the operational mechanism. The operational mechanism is the admissibility compiler. The representation theorem explains when such a compiler is a sharp finite observable presentation of the domain's licensing structure.

---

# Appendix G. Marketplace Token Sketch

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

The contract checks schema, artifacts, scope, coverage floor, overlap floor, expiry, and bias checks. Passing this contract bounds `proxy_gap`. It does not close `proxy_gap`. It says nothing about `interference_gap` or `coupling_gap`.

---

# Appendix H. PGM Inference Token Sketch

A PGM inference token must state which object it certifies.

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

Passing this contract bounds `posterior_divergence_gap`. It does not bound `model_specification_gap`. A separate model-specification token requires a different contract:

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

---

# References

Abadi, Martín, Michael Burrows, Butler Lampson, and Gordon Plotkin. 1993. “A Calculus for Access Control in Distributed Systems.” _ACM Transactions on Programming Languages and Systems._

Appel, Andrew W., and Edward W. Felten. 1999. “Proof-Carrying Authentication.” _CCS._

FDA. 2025. _Artificial Intelligence-Enabled Device Software Functions — Draft Guidance._ Docket FDA-2024-D-4488.

Gebru, Timnit, et al. 2021. “Datasheets for Datasets.” _Communications of the ACM._

Magesh, Varun, Faiz Surani, Daniel E. Ho, and Peter Henderson. 2025. “Hallucination-Free? Assessing the Reliability of Leading AI Legal Research Tools.” _Journal of Empirical Legal Studies._

Mitchell, Margaret, et al. 2019. “Model Cards for Model Reporting.” _FAccT._

Moreau, Luc, et al. 2013. “PROV-DM: The PROV Data Model.” _W3C Recommendation._

Myers, Andrew C. 1999. “JFlow: Practical Mostly-Static Information Flow Control.” _POPL._

Nagendran, Myura, et al. 2020. “Artificial Intelligence versus Clinicians: Systematic Review of Design, Reporting Standards, and Claims of Deep Learning Studies in Medical Imaging.” _BMJ._

Necula, George C. 1997. “Proof-Carrying Code.” _POPL._

Obermeyer, Ziad, et al. 2019. “Dissecting Racial Bias in an Algorithm Used to Manage the Health of Populations.” _Science._

NHS Royal College of Radiologists. 2024. _AI Deployment Fundamentals for Medical Imaging._

Roberts, Michael, et al. 2021. “Common Pitfalls and Recommendations for Using Machine Learning to Detect and Prognosticate for COVID-19 Using Chest Radiographs and CT Scans.” _Nature Machine Intelligence._

Schneider, Fred B. 2000. “Enforceable Security Policies.” _ACM Transactions on Information and System Security._

Tonekaboni, Sana, et al. 2022. “Predicting Clinical Deterioration in Hospitalized Patients: A Prospective Study.” _Frontiers in Digital Health._

Wong, Andrew, et al. 2021. “External Validation of a Widely Implemented Proprietary Sepsis Prediction Model in Hospitalized Patients.” _JAMA Internal Medicine._