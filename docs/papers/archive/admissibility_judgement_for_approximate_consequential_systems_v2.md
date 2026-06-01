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

The framework does not make this judgment easier. It makes the absence of judgment visible.

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

## 4. The admissibility judgment

The central object of the framework is the **admissibility judgement**: under proof context $\Gamma$, candidate $z$ is admissible at permission $p$ until expiry $\varepsilon$.
$$
\Gamma \vdash z : p \;\text{until}\; \varepsilon  
$$
where:
- $\Gamma$ is the proof context
- $z$ is the candidate claim, result, artifact, plan, or action being judged
- $p$ is the emitted permission or control outcome
- $\varepsilon$ is the expiry condition under which the judgment remains live

### 4.1. The proof context

For a candidate $z$, the proof context $\Gamma$ is the evidence package the compiler uses to answer:

> What permission is supported for this candidate, in this context, for this use, under this policy, using this evidence, at this time?

It contains the object being judged, the obligations induced for that object, the policy versions used to interpret those obligations, the proof tokens offered to discharge them, and the live runtime facts that determine whether the judgment still holds.

The proof context is not a universal ontology and it is not invented by the compiler. It is domain-specific machinery that says what kinds of claims exist, what can go wrong for each kind of claim, what evidence is required before each permission level, who is authorized to make which decision, and when evidence stops being live.

The compiler is domain-agnostic only after this bridge has done its work. A medical system, or multi-agent coding system may define different gaps, require different proof tokens, use different expiry rules, and impose different authority ceilings. Once those choices are written down, the compiler checks them mechanically.

For a candidate $z$, we write the proof context as:

$$
\begin{aligned}
\Gamma = &
\bigl(\mathsf{membership},\\
&\mathsf{claim},\\
&\mathsf{candidate},\\
&\mathsf{context},\\
&\mathsf{scope},\\
&\mathsf{claim\_gaps},\\
&\mathsf{gap\_taxonomy\_version},\\
&\mathsf{gap\_profile\_version},\\
&\mathsf{proof\_tokens},\\
&\mathsf{proof\_token\_provenance},\\
&\mathsf{detail\_contract\_registry\_version},\\
&\mathsf{expiry},\\
&\mathsf{allowed\_use},\\
&\mathsf{disallowed\_use},\\
&\mathsf{derivation},\\
&\mathsf{authority},\\
&\mathsf{runtime\_context},\\
&\mathsf{audit}
\bigr).
\end{aligned}
$$

The fields have five roles.

First, the proof context fixes the object of judgment. `membership` determines whether the candidate belongs to the class of systems or actions governed by the framework. `claim`, `candidate`, and `context` identify what is being asserted, what artifact or action is being considered, and the setting in which the assertion is meant to hold. `scope` limits where the resulting judgment may be used. These fields prevent the compiler from treating evidence for one claim, candidate, population, repository, model, or runtime setting as evidence for another.

Second, the proof context fixes the obligations. `claim_gaps` records the proof obligations induced for this claim. `gap_taxonomy_version` fixes the vocabulary of possible gaps. `gap_profile_version` fixes which gaps must be bounded or closed at each permission level. `detail_contract_registry_version` fixes the schemas and semantic checks that proof tokens must satisfy.

A **gap** is a proof obligation. It names a way in which the current evidence may be insufficient for the requested use. A gap is a question that must be answered before stronger permission can be granted.

Formally, a gap has the form
$$
g =
(\mathsf{gap\_id},
 \mathsf{gap\_type},
 \mathsf{status},
 \mathsf{metadata})
$$
where
$$
\mathsf{status}
\in
\{\mathsf{OPEN}, \mathsf{BOUNDED}, \mathsf{CLOSED}\}.
$$
The three statuses mean:
- `OPEN`: no admissible evidence has been supplied for this obligation.
- `BOUNDED`: admissible evidence limits the risk, but does not fully discharge the obligation.
- `CLOSED`: admissible evidence discharges the obligation for the relevant scope and use.

A gap type names the class of obligation. For example, `calibration_gap`, `clinical_utility_gap`, `model_specification_gap`, or `freshness_gap`. A gap instance binds that obligation to a particular claim, candidate, context, and scope. This distinction matters because a token that bounds a gap for one population, or deployment setting, or runtime state does not automatically bound the same kind of gap for another.

The profile specifies what status is required for each permission level. For a claim class $\kappa$, gap type $h$, and permission $p$, the profile contains a requirement
$$
\mathsf{Req}_{\Phi_v}(\kappa,h,p)
  \in
  \{
    \mathsf{OPEN\_ALLOWED},
    \mathsf{BOUNDED\_REQUIRED},
    \mathsf{CLOSED\_REQUIRED}
  \}.
$$
A permission is satisfiable only when every induced gap reaches the status demanded by the versioned profile. The compiler therefore does not ask whether evidence is persuasive in ordinary language. It asks whether each obligation has been discharged to the level required by the relevant taxonomy, profile, and detail contract registry.

Third, the proof context records admissible evidence. `proof_tokens` are typed witnesses offered to bound or close gaps. `proof_token_provenance` binds each token to the exact tuple it is allowed to support: token, gap, claim, candidate, and context. A token does not count merely because it has the right name or reports a favorable result. It counts only if it is live, contract-conformant, scoped correctly, and provenanced to the specific obligation being discharged.

Fourth, the proof context records narrowing and runtime constraints. `expiry` states when the judgment ceases to be live. `allowed_use` and `disallowed_use` restrict the downstream uses for which the judgment may be relied on. `authority` imposes ceilings or escalation requirements that may be independent of evidentiary strength. `runtime_context` supplies the live facts needed to evaluate expiry, registry status, authority, rollback, revocation, and other runtime checks. `derivation` records how the claim and candidate were produced, so that invalid or untrusted transformations cannot silently create authority.

Finally, `audit` is different from the other fields. It explains the result. It records which permissions were denied, which gaps blocked them, which tokens were rejected, which runtime checks failed, which authority ceilings applied, and which expiry or scope rules narrowed the outcome.

The compiler’s soundness claims are therefore relative to $\Gamma$. If $\Gamma$ contains the required gaps, uses the intended profile, includes only valid tokens, binds those tokens by exact provenance, and supplies the required runtime facts, then the compiler emits the greatest permission supported by that context and no more. If a load-bearing obligation is missing from the taxonomy, omitted from the profile, or assigned an overly permissive detail contract, the compiler may authorize too much. But that failure is visible at the domain-bridge boundary rather than hidden inside an informal deployment decision.

## 4.2 Working example

Consider a multi-agent coding system. An agent proposes a patch $z$ and asks the compiler for permission to merge it into a production repository.

The induced claim is: This patch is safe to merge into service S for production deployment.

The candidate is not merely “the patch” in the abstract. It is the specific diff, at a specific commit, against a specific base, in a specific repository, under a specific deployment target.

For example:

```text
candidate:
  patch z = diff D at commit h_patch

claim:
  patch z is safe to merge into service S for production deployment

context:
  repository = service-S
  branch = main
  base_commit = h_base
  patch_commit = h_patch
  dependency_lockfile_hash = L1
  test_environment = ci-prod-like-v3
  deployment_target = production
  scanner_database_version = secdb_17
  production_config_version = config_42

scope:
  service = service-S
  environment = production
  commit = h_patch
  base = h_base
  lockfile = L1
  permission_family = merge/deploy
```

The requested permission is:
$$
p = \mathsf{APPROVE\_AUTOMATIC\_MERGE}.
$$

The domain bridge induces the following gaps:

```text
build_gap
unit_test_gap
integration_test_gap
security_scan_gap
dependency_gap
freshness_gap
blast_radius_gap
rollback_gap
authority_gap
```

Each gap corresponds to a real failure mode. The patch may not build. The relevant tests may not have run. The security scanner may not have checked the final diff. The dependency lockfile may have changed after testing. The patch may be safe for review but not safe for automatic merge. The deployment may require a canary, feature flag, or rollback plan. The agent may be authorized to open a pull request but not authorized to merge or deploy.

For this claim class and permission level, the profile might require:

| Gap type | Requirement for `APPROVE_AUTOMATIC_MERGE` |
|---|---|
| `build_gap` | `CLOSED_REQUIRED` |
| `unit_test_gap` | `CLOSED_REQUIRED` |
| `integration_test_gap` | `BOUNDED_REQUIRED` |
| `security_scan_gap` | `CLOSED_REQUIRED` |
| `dependency_gap` | `CLOSED_REQUIRED` |
| `freshness_gap` | `CLOSED_REQUIRED` |
| `blast_radius_gap` | `BOUNDED_REQUIRED` |
| `rollback_gap` | `BOUNDED_REQUIRED` |
| `authority_gap` | `CLOSED_REQUIRED` |

The system then attaches proof tokens:

| Proof token | Intended gap | Provenance | Result |
|---|---|---|---|
| `ci_build_token` | `build_gap` | build for `h_patch` on `h_base` | closes `build_gap` |
| `unit_test_report` | `unit_test_gap` | tests for `h_patch` on `h_base` | closes `unit_test_gap` |
| `integration_test_report` | `integration_test_gap` | partial integration suite for service `S` | bounds `integration_test_gap` |
| `security_scan_report` | `security_scan_gap` | scan of final diff at `h_patch` using `secdb_17` | closes `security_scan_gap` |
| `dependency_audit` | `dependency_gap` | audit of lockfile hash `L1` | closes `dependency_gap` |
| `blast_radius_report` | `blast_radius_gap` | affected-service analysis for service `S` | bounds `blast_radius_gap` |
| `rollback_plan` | `rollback_gap` | rollback plan for deployment target `production` | bounds `rollback_gap` |
| `agent_role_token` | `authority_gap` | agent may open PRs but may not merge | does not close `authority_gap` for automatic merge |

At first glance, the evidence looks strong. The patch builds, tests pass, the scanner is clean, dependencies were audited, and a rollback plan exists. But the compiler does not evaluate the evidence by impression. It checks the exact obligations required for the requested permission.

Two things block automatic merge.

First, the actor does not have authority to perform the requested action. The `agent_role_token` may authorize the agent to propose a patch or open a pull request, but it does not authorize automatic merge to production. Therefore `authority_gap` remains open for `APPROVE_AUTOMATIC_MERGE`.

Second, the judgment may expire before use. Suppose the runtime context now says:

```text
current_time = t1
current_base_commit = h_base_prime
current_lockfile_hash = L1
current_scanner_database_version = secdb_17
patch_commit = h_patch
```

The base branch has moved from `h_base` to `h_base_prime`. The build, test, and scan tokens were provenanced to `h_patch` on `h_base`, not to `h_patch` on the new base. Even if the patch itself did not change, the merge target did. The relevant freshness condition is no longer satisfied.

The expiry rule for this permission might be:

$$
\varepsilon_{\mathsf{merge}}
=
\operatorname{first}
\{
\text{base branch changes},
\text{patch changes},
\text{lockfile changes},
\text{scanner database changes},
\text{production config changes},
t + 24\text{h}
\}.
$$

Because the base branch changed, the previous judgment is no longer live. Evidence that was admissible for the old context is not silently carried into the new one.

The compiler therefore denies the requested permission:

$$
\Gamma \nvdash z : \mathsf{APPROVE\_AUTOMATIC\_MERGE}.
$$

But it may still emit a weaker supported permission:

$$
\Gamma \vdash z : \mathsf{OPEN\_PULL\_REQUEST\_FOR\_REVIEW}
\ \text{until}\ 
\varepsilon_{\mathsf{review}}.
$$

The audit explains the downgrade:

```text
requested_permission:
  APPROVE_AUTOMATIC_MERGE

granted_permission:
  OPEN_PULL_REQUEST_FOR_REVIEW

blocking_reasons:
  - authority_gap remains OPEN for automatic merge
  - freshness_gap reopened because base branch moved from h_base to h_base_prime

accepted_tokens:
  - ci_build_token
  - unit_test_report
  - integration_test_report
  - security_scan_report
  - dependency_audit
  - blast_radius_report
  - rollback_plan

rejected_or_limited_tokens:
  - agent_role_token does not authorize automatic merge
  - build/test/scan tokens are limited to h_patch on h_base

required_continuations:
  - rerun build and tests against h_base_prime
  - rerun or validate security scan against the new merge target
  - obtain approval from an actor with merge authority
```

This example shows why the proof context is not just metadata. It is the structure that prevents evidence from being overextended. A CI run for one commit does not prove safety for another. A security scan over one diff does not cover a moved branch head. A reviewer approval for human review does not authorize automatic deployment. A technically strong evidence package does not override an authority ceiling. And a judgment that was valid before a runtime change may no longer be valid after it.

---
### 4.2. Candidate claim
The claim $z$ is a concrete statement that can be certified by $\Gamma$.

A non-certifiable claim: "This refactor is safe to merge."

A certifiable claim: "This refactor is safe to merge with respect to the 47 test cases in `tests/unit/` and the three integration scenarios in `tests/integration/payment_flow/`. We observe: test pass/fail, static type coverage over modified call sites, and absence of modified public API signatures. We do not observe: runtime behavior under concurrent load, downstream service contracts not covered by the integration suite, or any behavior conditional on environment variables not set in CI. The claim is scoped to the observable test surface; production safety beyond that surface is not certified."

### 4.3. Permission

Permissions can be thought of as an enumeration, documented below.

| Permission | Meaning                                                                           |
| ---------- | --------------------------------------------------------------------------------- |
| `OOC`      | Out of class — the system does not apply to this input                            |
| `EXP`      | Expired — a token or context TTL has elapsed                                      |
| `REF`      | Refused — a credential was actively rejected (wrong provenance, revoked, invalid) |
| `UNS`      | Unsupported — profiles exist but no evidence satisfies them                       |
| `DIA`      | Diagnostic — the in-class floor; all gaps open, no positive evidence              |
| `REV`      | Reversible action permitted                                                       |
| `AEX`      | Automatic execution permitted — computation certified                             |
| `ALR`      | Automated and logged rollout — computation certified *and* model adequate         |
| `AAA`      | Unrestricted                                                                      |

Permissions form a total order from most restrictive to least:

```
OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA < REV < AEX < ALR < AAA
```

### 4.4. Expiry

Expiry is the hardest and arguably the most critical component for making  the framework useful. It is domain dependent and must be set by humans.  The domain defines what makes evidence expire; the framework enforces expiration.

For example, in an agentic coding system, humans or teams might decide that a CI result expires after the source branch diverges from main, after a dependency lockfile changes, or when a security-scan artifact becomes stale. These are engineering judgments. Once written into the profile or detail contract, the compiler treats them as hard constraints.

There can be several sources of expiry, including
1. **Artifact expiry** — the validation report, dataset, audit, or monitoring artifact may become stale.
2. **Detail-contract expiry rules** — the contract may say evidence cannot be older than 30 days, cannot survive a model version change, cannot survive context drift, etc
3. **Authority expiry** — the person/system granting permission may only have delegated authority for a time, scope, or rollback condition

---

## 5. The compiler

The admissibility compiler prevents these promotions by requiring every consequential use to pass through a profile.

A profile specifies which gaps matter for a given claim and permission level. A proof token can bound or close a gap only if it has the right type, satisfies the required detail contract, is live, is scoped correctly, and has exact provenance to the claim, candidate, context, and gap it purports to support.

The result is not that weak evidence becomes strong. The result is that weak evidence receives only a weak license.

A diagnostic certificate may justify diagnostic display. A local test result may justify human review. A bounded experiment may justify limited rollout. A fully scoped, live, provenanced, authority-compatible evidence package may justify automatic action. But no evidence item is allowed to promote itself by implication, analogy, institutional confidence, or prose.

The core discipline is simple:

```text
No approximation may be used as stronger permission than its evidence, scope,
provenance, expiry, authority, and policy profile jointly support.
```


The compiler is the mechanism that constructs this judgment. It receives evidence, profiles, registries, tokens, provenance records, authority constraints, and runtime context. It then emits the greatest permission supported by those inputs. The caller may request a permission, but the request has no evidentiary force. A request for rollout does not count as rollout evidence. A request for automatic action does not count as automatic-action authority.

The judgment is intentionally permission-valued rather than Boolean-valued. Approximate consequential systems rarely divide cleanly into “allowed” and “not allowed.” The same candidate may be inadmissible for automatic action, admissible for limited rollout, admissible for experiment, admissible only for diagnostic display, or admissible only after human review. The compiler therefore emits a permission level, not a yes/no answer.

The permission order is restrictive-to-permissive:

```text
OOC ≤ EXP ≤ REF ≤ UNS ≤ ETA ≤ ESC ≤ ROL ≤ DIA ≤ REV ≤ AEX ≤ ALR ≤ AAA
```

The positive permissions are:

```text
DIA  = DIAGNOSTIC_ONLY
REV  = RECOMMEND_HUMAN_REVIEW
AEX  = APPROVE_EXPERIMENT
ALR  = APPROVE_LIMITED_ROLLOUT
AAA  = APPROVE_AUTOMATIC_ACTION
```

The lower outcomes represent out-of-class, expired, refused, unsupported, escalation, rollback, or other control states. They live in the same order because the compiler emits one continuation. A positive permission cannot dominate a live control obligation.

The compiler searches positive permissions from strongest to weakest:

```text
AAA, ALR, AEX, REV, DIA
```

It returns the first permission whose requirements are satisfied. If no positive permission is satisfiable, the result is `UNS`. The final emitted permission is then met with any structural failures or control obligations. Since meet is minimum in the permission order, every additional constraint can only preserve or lower the emitted permission. Nothing after the positive search can promote the result.

A judgment is therefore not merely a decision. It is a decision plus the exact context in which that decision was valid. This is what makes later audit possible. If a deployment was refused, the judgment records which stronger permissions were blocked and why. If a deployment was authorized, the judgment records which profile, taxonomy, detail contracts, tokens, provenance records, authority envelope, and expiry condition supported that authorization.

The admissibility judgment enforces five separations.

First, it separates **requested permission** from **supported permission**. The caller’s desired outcome is not evidence.

Second, it separates **policy** from **enforcement**. The profile states which gaps are required for which permissions. The compiler enforces that profile mechanically.

Third, it separates **token type** from **token validity**. A token is not evidence merely because it has a reassuring name. It must satisfy a registered detail contract, including schema checks, semantic checks, artifact dependencies, scope rules, expiry rules, and registry liveness.

Fourth, it separates **evidence existence** from **evidence provenance**. A token can support a gap only when it is provenanced to the exact tuple it claims to support:

```text
(τ, g, c, z, x)
```

That is: token, gap, claim, candidate, and context. No provenance, no proof.

Fifth, it separates **structural admissibility** from **domain truth**. The compiler can check that the right kind of evidence was presented, that it was scoped correctly, that it was live, that it satisfied its registered contract, and that it was attached to the right candidate and context. It cannot guarantee that the certifier used good science, that the measurement was not fraudulent, or that the domain’s chosen threshold was morally or scientifically correct. Those are trusted-computing-base assumptions and governance obligations.

This limitation is not a defect in the framework. It is the framework’s epistemological boundary.

For mathematically grounded systems, the boundary may be narrow. If the relevant gap is posterior divergence, and the certificate computes a valid bound against the correct ideal object, the compiler can enforce a theorem-like obligation.

For policy-grounded systems, the boundary is wider. If a clinical profile says that limited rollout requires PPV above a given threshold, the compiler can enforce that threshold. It cannot prove that the threshold was the right threshold. The judgment is therefore a guarantee of admissibility relative to an explicit profile, not a guarantee of universal correctness.

This is why the emitted object should be called a judgment. A compiler suggests an implementation. A judgment names the thing the implementation produces: a scoped, expiring, auditable statement that a candidate is admissible at a particular permission level under a particular proof context.

The rest of the formalism exists to make this judgment non-launderable. Membership prevents out-of-class systems from entering the permission ladder. Gap profiles prevent vague policy from becoming enforcement. Proof tokens and detail contracts prevent token names from substituting for evidence. Provenance prevents evidence reuse across claims, candidates, contexts, and gaps. Expiry and runtime revalidation prevent stale judgments from silently remaining live. Composition and decomposition prevent larger systems from hiding weaker components. Versioning prevents later registry changes from rewriting the meaning of an issued envelope.

The admissibility judgment is therefore the paper’s load-bearing abstraction:

```text
Approximate outputs do not authorize action directly.
They authorize action only by compiling into an admissibility judgment.
```

---
## References

Abadi, Martín, Michael Burrows, Butler Lampson, and Gordon Plotkin. 1993. "A Calculus for Access Control in Distributed Systems." _ACM Transactions on Programming Languages and Systems._

Gebru, Timnit, Jamie Morgenstern, Briana Vecchione, Jennifer Wortman Vaughan, Hanna Wallach, Hal Daumé III, and Kate Crawford. 2021. "Datasheets for Datasets." _Communications of the ACM._

Guo, Chuan, Geoff Pleiss, Yu Sun, and Kilian Q. Weinberger. 2017. "On Calibration of Modern Neural Networks." _ICML / PMLR._

Mitchell, Margaret, Simone Wu, Andrew Zaldivar, Parker Barnes, Lucy Vasserman, Ben Hutchinson, Elena Spitzer, Inioluwa Deborah Raji, and Timnit Gebru. 2019. "Model Cards for Model Reporting." _FAccT._

Moreau, Luc, Paolo Missier, Khalid Belhajjame, Reza B'Far, et al. 2013. "PROV-DM: The PROV Data Model." _W3C Recommendation._

Necula, George C. 1997. "Proof-Carrying Code." _POPL._

NIST. 2023. _Artificial Intelligence Risk Management Framework 1.0._ National Institute of Standards and Technology.

Ovadia, Yaniv, Emily Fertig, Jie Ren, Zachary Nado, D. Sculley, Sebastian Nowozin, Joshua Dillon, Balaji Lakshminarayanan, and Jasper Snoek. 2019. "Can You Trust Your Model's Uncertainty? Evaluating Predictive Uncertainty Under Dataset Shift." _NeurIPS._

Quiñonero-Candela, Joaquin, Masashi Sugiyama, Anton Schwaighofer, and Neil D. Lawrence, eds. 2008. _Dataset Shift in Machine Learning._ MIT Press.

Raji, Inioluwa Deborah, Andrew Smart, Rebecca N. White, Margaret Mitchell, Timnit Gebru, Ben Hutchinson, Jamila Smith-Loud, Daniel Theron, and Parker Barnes. 2020. "Closing the AI Accountability Gap: Defining an End-to-End Framework for Internal Algorithmic Auditing." _FAT / FAccT*._

Schneider, Fred B. 2000. "Enforceable Security Policies." _ACM Transactions on Information and System Security._

Shafer, Glenn, and Vladimir Vovk. 2008. "A Tutorial on Conformal Prediction." _Journal of Machine Learning Research._
