# Admissibility Compilers for Approximate Consequential Systems

**Core judgment:** `Γ ⊢ z : p until ε`

## Abstract

Approximate systems often emit outputs that downstream systems treat as permission to act. This is evidence laundering. An admissibility compiler blocks that move. It takes an approximate output and emits the strongest admissible judgment supported by live evidence, provenance, scope, authority, expiry, and runtime context. The result is structural soundness relative to an explicit trusted computing base.

The proof is small. The discipline is not optional. The first probabilistic-inference benchmark gives the right kind of evidence: no structural soundness violations on the checked cases, and one concrete taxonomy failure. Approximation-to-model error was bounded, but model-specification error was not. That distinction becomes a first-class gap in this draft.

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

| Symbol | Outcome |
|---|---|
| `OOC` | `OUT_OF_CLASS` |
| `EXP` | `EXPIRED` |
| `REF` | `REFUSED` |
| `UNS` | `UNSUPPORTED` |
| `ETA` | `ESCALATE_TRADEOFF_OUT_OF_AUTHORITY` |
| `ESC` | `ESCALATE` |
| `ROL` | `ROLLBACK` |
| `DIA` | `DIAGNOSTIC_ONLY` |
| `REV` | `RECOMMEND_HUMAN_REVIEW` |
| `AEX` | `APPROVE_EXPERIMENT` |
| `ALR` | `APPROVE_LIMITED_ROLLOUT` |
| `AAA` | `APPROVE_AUTOMATIC_ACTION` |

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

| Claim | Status |
|---|---|
| Algebraic non-promotion | Supported by proof and EC-003 |
| Profile/search non-promotion | Supported by proof and EC-004 |
| Token/provenance anti-laundering | Supported by proof, EC-003, and EC-004 |
| Runtime non-upgrade | Supported by proof and EC-003 |
| Inference structural soundness | Supported by PGM-001 on checked cases |
| Inference tightness | Not yet measured in the interesting regime |
| Inference taxonomy completeness | Falsified once; patched with `model_specification_gap` |
| Kernel-family coverage | Open instrumentation task |
| GasTown multi-agent class benchmark | Pending |
| Sift/product-decision benchmark | Pending |

The important result is not that every benchmark passed. The important result is that the framework failed in the right place. It did not silently promote invalid evidence inside the compiler. It exposed a missing obligation in the taxonomy.

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
2. run the Sift/product-decision benchmark over proposal and experiment-readout cases;
3. rerun the PGM benchmark with calibrated per-network memory budgets;
4. instrument kernel-family coverage failures for `link` and `munin1`;
5. replace the illustrative marketplace token with emitted certifier output;
6. formalize predicate scopes beyond finite sets;
7. extend adversarial suites for adapters, taxonomies, profiles, contracts, registries, and authority envelopes.

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
