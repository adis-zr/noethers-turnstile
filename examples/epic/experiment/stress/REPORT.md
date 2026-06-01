# MED-STR-001: Stress Tests — Full Report

## What This Experiment Tests

MED-IND-001 showed that the compiler discovers a correct gap taxonomy from failure evidence alone, and that the discovered taxonomy covers 100% of FDA/NHS/EU AI Act requirements. The natural follow-up question is: **is the compiler actually doing epistemic work, or is it just forwarding pre-labeled inputs?**

This report answers that question with two experiments:

**Experiment 1 — Adversarial attacks:** Ten distinct strategies for breaking or bypassing the converged v6 profile. Each targets a different structural property. Results classify which attacks the compiler blocks natively and which break it.

**Experiment 2 — Hidden gap experiments:**
- **2a**: Replace OPEN gaps with `bounded` on real induction cases (dishonest submitter). Does the compiler over-authorize?
- **2b**: Remove gap entries entirely from the case (omission). Does the compiler treat absent gaps as open? And does the same omission under v0 (before the gap was induced) correctly remain invisible?

---

## What the Compiler Is

Before reading the results, the correct frame: the compiler is a **structural enforcement layer**, not an evidence verifier.

It enforces that the right *shape* of evidence was presented — which gaps exist, what the profile requires, what tokens are present, whether provenance is valid. It does not verify that the evidence is *true*. It cannot. Verifying that `clinical_utility_gap` is genuinely bounded would require the compiler to re-run the clinical validation study. That is not in scope and cannot be in scope.

The trust boundary is therefore designed, not accidental. The compiler enforces what it can own cryptographically and structurally. Everything else is the responsibility of certifiers, audit trails, and institutional accountability for false attestations.

The stress tests are not an indictment. They are a map.

---

## Experiment 1: Adversarial Attacks

### Setup

All ten attacks are run against the converged v6 profile:

```
v6 ALR requires all 8 gaps bounded:
  approximation_quality_gap
  freshness_gap
  clinical_utility_gap
  model_specification_gap
  distribution_shift_gap
  individual_population_gap
  blast_radius_gap
  authority_gap
```

Each attack attempts to reach ALR (or above) through a different form of manipulation. Results are classified as **BREAKS** (attack succeeded; compiler over-authorized) or **BLOCKED** (compiler refused).

---

### A1 — Gap Laundering

**Strategy:** Mark all gaps `bounded` with no tokens and no supporting evidence. The profile requires all gaps bounded at ALR. If the compiler accepts status string assertions at face value, this reaches ALR.

**Result: BREAKS. Compiler emits ALR.**

The compiler reads `GapRecord.status` as a string. It checks whether the string satisfies the profile's `minimum_status` requirement. It does not check whether any token was issued to substantiate the claim. A submitter who asserts `"bounded"` for every gap, with no evidence whatsoever, reaches ALR.

**What this means:** The gap status system is an *attestation* layer, not a *verification* layer. Marking a gap `bounded` is a claim made by the bridge that constructs the `ProofContext` — not a fact the compiler verifies. The compiler enforces that a claim was made; it does not enforce that the claim is true.

**Defense:** External. Certifier discipline — only authorized certifiers may assert gap statuses, and their assertions are legally and institutionally accountable. The compiler's role is to enforce that the attestation chain is complete and internally consistent, not to audit the underlying evidence.

---

### A2 — Threshold Gaming

**Strategy:** Mark `approximation_quality_gap` as `bounded` with `bound_value=0.52` — AUC barely above chance. The profile requirement is `minimum_status="bounded"`. Does the compiler enforce a numerical floor on `bound_value`?

**Result: BREAKS. Compiler emits ALR.**

`GapRecord` has a `bound_value` field that is stored and returned but never compared against any numerical floor by the profile machinery. The profile requirement `minimum_status="bounded"` is a categorical gate: it checks the status string, not the numerical value. `bound_value=0.52` satisfies `minimum_status="bounded"` identically to `bound_value=0.95`.

**What this means:** The compiler's gap status system is categorical, not quantitative. It tracks whether evidence was presented and what level was claimed; it does not enforce that the claimed level meets a specific numerical standard. Quantitative floors — AUC ≥ 0.70, PPV ≥ 0.15, calibration ratio ≤ 1.3 — are enforced at the *token* level, inside the certifier that issues the token, before the token reaches the compiler.

**Defense:** Detail contracts in token constructors. The `clinical_utility_token` constructor (in `adapter/tokens.py`) marks the token `"invalid"` if PPV falls below the pre-registered floor, which prevents it from appearing in `bounds_gaps`. That invalid token (A7, below) is then rejected by the compiler. The quantitative floor enforcement is inside the TCB, one layer below the compiler.

**Implication for gap-status-only submissions (no tokens):** If the bridge sets `status="bounded"` directly in `GapRecord` without going through a token constructor, the detail contract is bypassed entirely. The defense requires the token pathway to be mandatory — which is an architectural enforcement question, not a compiler enforcement question.

---

### A3 — Wrong-Level Token

**Strategy:** Submit a `FRESHNESS` token (designed to close `freshness_gap`) that claims to close `clinical_utility_gap` instead. The `closes_gaps` field is `["clinical_utility_gap"]`. The `token_type` is `"FRESHNESS"`. Does the compiler validate that `token_type` matches the gap being closed?

**Result: BREAKS. Compiler emits ALR.**

The compiler validates `token.status` (must be `"valid"`) and `token.provenance_hash` (must match the current `(claim_id, candidate_id, context_id, allowed_use)` tuple). It does not validate `token_type` against the gap ID in `closes_gaps`. A token with the correct provenance hash and `status="valid"` can claim to close any gap regardless of its type.

**What this means:** `token_type` is a metadata field for human auditors and certifier systems, not a compiler-enforced constraint. The compiler's security model is: provenance binds the token to its deployment context; status reflects certifier judgment; the token's claim about which gaps it closes is accepted at face value from the certifier.

**Defense:** The certifier issuance system. A `LegalFreshnessCertifier` should only ever emit tokens with `closes_gaps=["freshness_gap"]`. If a certifier lies about what its token closes, that is a certifier failure — auditable and accountable — not a compiler failure. The compiler trusts certifiers. Certifier trustworthiness is enforced by institutional controls outside the TCB.

**Practical implication:** In a production deployment, certifiers are registered and permissioned entities. A certifier that issues a FRESHNESS token claiming to close `clinical_utility_gap` would be visibly lying in an auditable token record. The attack requires a compromised certifier, not just a clever submitter.

---

### A4 — Authority Ceiling Bypass

**Strategy:** Register an AAA-satisfying profile and satisfy all its requirements; set `authority_ceiling=ALR`. Does the ceiling hold?

**Result: BLOCKED. Compiler emits ALR.**

The compiler applies `meet(authority_ceiling, judgment)` as the final step. Even when the profile logic yields AAA, the ceiling caps the result. This is a natively enforced structural property — the ceiling is applied after all gap evaluation and cannot be bypassed by satisfying higher-level profiles.

**What this means:** The authority ceiling is the one constraint the compiler enforces unconditionally against the profile logic. It is the final operation, not an input to the profile evaluation. A submitter cannot reach above the ceiling regardless of what the profile says.

---

### A5 — Membership Spoof

**Strategy:** Submit `Membership.InClass` for a candidate that should be `OutOfClass`. Compare the result against correct `OutOfClass` submission.

**Result: BREAKS.**

- `OutOfClassExact` submitted correctly → `OOC` (correct)
- `InClass` submitted for the same candidate → `ALR` (spoofed)

`Membership` is caller-asserted. The compiler applies `OOC` immediately and unconditionally when `OutOfClass` is submitted — before any gap evaluation. But it has no way to verify whether `InClass` is accurate. A submitter who lies about class membership bypasses the OOC gate entirely.

**What this means:** Class membership assessment happens before the compiler runs. Whether a given candidate falls within the claim class — "is this an ICU patient?" "is this a legal research query?" — is a domain question that requires domain knowledge the compiler does not have. The compiler enforces the *consequence* of the membership determination; it does not make the determination itself.

**Defense:** Same structure as gap status assertions: institutional accountability for false membership claims. In a clinical deployment, the bridge that constructs the `ProofContext` is the entity attesting class membership. Systematic false assertions would be detectable in audit logs and constitute a compliance violation.

---

### A6 — Empty Profile Attack

**Strategy:** Register no profiles at all. Mark all gaps `bounded`. Can the compiler be forced above OOC?

**Result: BLOCKED. Compiler emits OOC.**

No profiles → no permission level is reachable → OOC is the structural floor. This is unconditional: there is no combination of gap statuses or tokens that produces a non-OOC result when the profile list is empty. The floor is enforced before any gap or token evaluation.

**What this means:** The compiler's permission system is opt-in at the profile level. Without a profile registering a permission level as achievable, that level cannot be reached. A deployment that omits the ALR profile cannot accidentally reach ALR. This is the correct fail-safe default.

---

### A7 — Invalid Token Submission

**Strategy:** Submit a token with `status="invalid"` that claims to bound `clinical_utility_gap`. With all other gaps bounded, does the compiler accept the invalid token and reach ALR?

**Result: BLOCKED. Compiler emits AEX.**

Tokens with `status="invalid"` are ignored by the compiler. The `clinical_utility_gap` stays open. With that gap open, ALR is blocked and AEX is the ceiling.

**What this means:** The `status` field on tokens is a vetted field — it reflects whether the certifier's own validation passed. The compiler respects the certifier's self-assessment. A token that the certifier marked `"invalid"` (e.g., because PPV fell below the floor) cannot close a gap even if it is submitted. This is the mechanism that makes detail contracts work: the certifier marks the token invalid; the compiler refuses to use it.

**Note:** This is how the MED-001 A06 oracle test works. `clinical_utility_token()` with PPV=0.12 sets `status="invalid"`. The token then cannot bound `clinical_utility_gap`. The compiler's rejection of invalid tokens is what makes the PPV floor enforceable through the token pathway — even if the caller also marks the `GapRecord.status` as open (which they should, if the token is invalid).

---

### A8 — Expired Token Floor

**Strategy:** Submit one expired token alongside valid gap statuses. Does the compiler floor the judgment to EXP?

**Result: BLOCKED. Compiler emits EXP.**

Any expired token in the `ProofContext` floors the `LiveJudgment` to `EXP` at runtime evaluation — before any gap or profile logic runs. This is a hard structural property: stale evidence contaminates the entire context. The correct response to stale evidence is not to ignore the expired token and proceed with the remaining evidence; it is to reject the entire judgment and require re-evaluation.

**What this means:** Evidence has temporal scope. A clinical utility validation that expires does not become irrelevant — it becomes *unknowable*. The model may have drifted, the population may have shifted, the operating context may have changed. The compiler's response is correct: expire the entire judgment and require re-issuance with fresh evidence.

**Implication for the induction experiment:** The original bug where all cases returned `EXP` was caused by fingerprint mismatch between `ProofContext.context_fingerprint` and `RuntimeContext.context_fingerprint` — the runtime was passing `ctx.context_id` instead of the fingerprint string. The fix was to pass the fingerprint directly. This test (A8) confirms that the EXP floor mechanism works correctly when *intentionally* triggered.

---

### A9 — Provenance Laundering

**Strategy:** Submit a token whose `provenance_hash` was computed for a different `(claim_id, candidate_id, context_id, allowed_use)` tuple. Can evidence from one deployment context be recycled into another?

**Result: BLOCKED. Compiler emits AEX (token rejected; gap stays open).**

The compiler verifies the `provenance_hash` of every token against the current deployment context. A hash computed for `(claim-DIFFERENT, candidate-DIFFERENT, context-DIFFERENT, use-DIFFERENT)` does not match the hash for the current context. The token is rejected and contributes nothing to gap status.

**What this means:** This is the anti-laundering property. A clinical utility validation conducted for a specific model, in a specific context, for a specific use cannot be submitted as evidence for a different deployment. The provenance hash cryptographically binds the token to exactly one `(claim, candidate, context, use)` tuple. Cross-context token reuse is structurally impossible.

**This is the compiler's strongest structural guarantee.** It is the property that prevents an operator from building a library of valid tokens and applying them across deployments without re-evaluation. Every deployment requires fresh evidence, or the provenance check fails.

---

### A10 — Maximum Status Assertion

**Strategy:** Mark all gaps `closed` (stronger than `bounded`) with no tokens. Test at both ALR and AAA ceilings.

**Result: BREAKS. ALR at ALR ceiling; AAA at AAA ceiling.**

This confirms and extends A1. `status="closed"` is treated identically to `status="bounded"` by the profile machinery — both satisfy `minimum_status="bounded"`, and both satisfy `minimum_status="closed"`. The compiler does not require tokens to substantiate `"closed"` any more than it requires them for `"bounded"`. At the AAA ceiling, claiming `"closed"` for all gaps with no tokens yields AAA.

**What this means:** The `open` / `bounded` / `closed` status hierarchy is an attestation hierarchy, not an evidence-quality hierarchy enforced by the compiler. `"closed"` means the submitter claims the gap is fully resolved. The compiler enforces that the profile's minimum status is met. It does not verify the claim.

**Practical implication:** A submitter who controls the `ProofContext` construction can reach any permission level up to the authority ceiling by asserting the right gap statuses — with or without tokens, with or without supporting evidence. The break surface for A1, A2, A3, A5, and A10 all reduce to this root: **the compiler trusts its inputs**.

---

### Experiment 1 Summary

**5 of 10 attacks break the compiler. 5 of 10 are blocked.**

The break surface and defended surface are not random — they fall along a single structural line.

**Breaks — the compiler trusts:**

| Attack | What is trusted | Root mechanism |
|--------|----------------|----------------|
| A1 | Gap status string `"bounded"` | `GapRecord.status` is caller-asserted |
| A2 | Numerical value in `bound_value` | No quantitative floor at profile level |
| A3 | Token's `closes_gaps` claim | `token_type` not validated against gap |
| A5 | `Membership.InClass` assertion | Membership is caller-assessed |
| A10 | Gap status string `"closed"` | Same root as A1 |

**Blocked — the compiler owns:**

| Attack | What is enforced | Mechanism |
|--------|-----------------|-----------|
| A4 | Authority ceiling | `meet(ceiling, judgment)` always applied last |
| A6 | Empty profile floor | No profiles → OOC unconditionally |
| A7 | Invalid token status | `status="invalid"` tokens ignored |
| A8 | Token expiry | Expired token → EXP floor at runtime |
| A9 | Provenance binding | Hash mismatch → token rejected |

**The trust boundary is a straight line:** everything the compiler *computes itself* (hashes, expiry evaluation, ceiling application, floor enforcement) cannot be faked. Everything the compiler *receives as input* (gap statuses, membership, token type claims) is trusted from the caller.

This is not a weakness in the compiler design. It is the correct separation of concerns for a structural enforcement layer. A compiler that tried to verify its inputs would need to become a domain oracle — which would make it both impossible to build and incorrectly scoped. The architecture's correct response to the break surface is external trust infrastructure: certifier registration, audit logs, legal accountability for false attestations.

---

## Experiment 2a: Falsely Optimistic Statuses

### Setup

Take each of the six induction cases (M02–M07). Each has at least one OPEN `blocking_gap`. Under the converged v6 profile, the compiler correctly emits AEX (all domain gaps AEX-reachable, but ALR requires the blocking gap bounded).

Replace the blocking gap status with `"bounded"`. Fill in any other taxonomy gaps not present in the case with `"bounded"` as well (a thorough dishonest submitter would do this). Re-compile.

### Results: 6/6 Break

Every case over-authorizes when blocking gap statuses are falsified.

| Case | System | Normal output | After falsification | Expert judgment |
|------|--------|--------------|---------------------|-----------------|
| M02 | Epic Sepsis Model | AEX | ALR | REV |
| M03 | Optum racial bias | AEX | ALR | REV |
| M04 | PredPol feedback loop | AEX | ALR | REV |
| M05 | COMPAS recidivism | AEX | ALR | REV |
| M06 | Watson Oncology | AEX | ALR | AEX |
| M07 | Dutch childcare | AEX | ALR | AEX |

In every case, a single false status assertion on one gap is sufficient to reach ALR. The converged v6 profile correctly holds the compiler at AEX when statuses are honest. It cannot hold it at AEX when the submitter lies.

### What this means

This result answers the original question directly: **yes, the compiler is doing real epistemic work — but only on honest inputs**.

With honest inputs, the profile enforces a meaningful boundary. Epic's `clinical_utility_gap` being OPEN correctly prevents ALR. COMPAS's `individual_population_gap` being OPEN correctly prevents ALR. The gap structure matters. The profile requirements are not vacuous.

With dishonest inputs, the boundary fails. A single false `"bounded"` assertion is sufficient to bypass any individual gap requirement. This is the correct characterization of the compiler's actual guarantee: **it enforces attestation completeness, not attestation truth**.

### The correct interpretation

The break in 2a is not a flaw — it is the explicit architectural choice that makes the system deployable. An admissibility compiler that required verification of all evidence claims would need to:

- Re-run every clinical study to verify `clinical_utility_gap` is genuinely bounded
- Re-train and evaluate every model to verify `approximation_quality_gap`
- Re-analyze every deployment population to verify `distribution_shift_gap`

This is not a compiler. This is a regulatory agency. The compiler's job is to enforce *that* the attestation was made, *which* gaps were attested, *by whom*, and *for which deployment context*. Whether the attestation is truthful is the responsibility of the certifier, auditable in the token record, and legally accountable.

The 6/6 result in 2a does not mean the compiler is useless — it means the compiler's guarantee is precisely scoped. The complement of 2a is 2b.

---

## Experiment 2b: Omitted Gap Entries

### Setup

Take the same six induction cases. Instead of falsifying the blocking gap status, **remove the gap entry entirely** from `gap_statuses`. The gap simply is not mentioned.

Test two scenarios for each case:

- **Under converged v6**: the gap is in the taxonomy. Absent → defaults to `"open"` in `compile_case()` → should block ALR.
- **Under v0**: the gap is not yet in the taxonomy. Absent and not required → should be invisible → ALR correctly emitted.

### Results: 6/6 Correct in Both Directions

| Case | v6 omitted | v0 omitted | Interpretation |
|------|-----------|-----------|----------------|
| M02 | AEX | ALR | CORRECT: absent CU gap → open (v6 blocks), invisible (v0 passes) |
| M03 | AEX | ALR | CORRECT: absent MS gap → open (v6 blocks), invisible (v0 passes) |
| M04 | AEX | ALR | CORRECT: absent DS gap → open (v6 blocks), invisible (v0 passes) |
| M05 | AEX | ALR | CORRECT: absent IP gap → open (v6 blocks), invisible (v0 passes) |
| M06 | AEX | ALR | CORRECT: absent BR gap → open (v6 blocks), invisible (v0 passes) |
| M07 | AEX | ALR | CORRECT: absent AU gap → open (v6 blocks), invisible (v0 passes) |

### What this means

**Under v6:** When a gap is in the taxonomy and simply not mentioned in the `gap_statuses` dict, `compile_case()` defaults it to `"open"`. The profile requires it `"bounded"` for ALR. The compiler correctly emits AEX. Omission is not a loophole — an unmentioned gap is treated as unresolved.

**Under v0:** The same gap is not in the taxonomy. The profile has no requirement for it. The compiler cannot see what it has not been told to track. ALR is correctly emitted. The induction loop's pre-discovery blindness is genuine, not simulated.

This is the key result of 2b: **the blindness is symmetric and intentional**. Before a gap is induced, its OPEN status is invisible to the compiler — correctly, because the profile has not yet been taught to ask for it. After induction, that same gap being absent is treated as open — correctly, because the profile now requires evidence for it. The transition from invisible to required is exactly what each induction step accomplishes.

### The contrast with 2a

2a and 2b test fundamentally different things:

- **2a (falsified):** Submitter actively lies. Asserts `"bounded"` for a gap that is genuinely OPEN. The compiler is told a falsehood and accepts it.
- **2b (omitted):** Submitter passively omits. Does not mention a gap. The compiler defaults it to OPEN and blocks correctly.

The asymmetry is stark: **omission is safe; falsification is not**. A bridge that simply fails to fill in a gap leaves the compiler in the correct conservative state. A bridge that fills in a false status breaks the compiler. This maps directly onto the real-world trust model: the dangerous actor is not the one who doesn't know about a gap (they will just fail to submit evidence and be held at AEX), but the one who fabricates evidence (they will bypass the profile entirely).

---

## Full Trust Boundary Map

Combining both experiments:

### What the compiler enforces unconditionally

These properties hold regardless of what inputs are submitted. They cannot be bypassed by any input construction.

| Property | Mechanism | Relevant test |
|----------|-----------|---------------|
| Provenance binding | `provenance_hash` verified against `(claim, candidate, context, use)` | A9 |
| Token expiry floor | Expired token → EXP before any gap evaluation | A8 |
| Invalid token rejection | `status="invalid"` tokens contribute nothing | A7 |
| Authority ceiling | `meet(ceiling, judgment)` always applied last | A4 |
| Empty profile floor | No profiles → OOC, no exceptions | A6 |
| Absent gap default | Gap absent from `gap_statuses` → treated as `"open"` | 2b |

### What the compiler trusts from the caller

These properties depend on caller honesty. They can be broken by dishonest input.

| Property | Trusted claim | Attack that breaks it |
|----------|--------------|----------------------|
| Gap status | `GapRecord.status` string | A1, A10, 2a |
| Numerical floors | `GapRecord.bound_value` | A2 |
| Token scope | `ProofToken.closes_gaps` / `bounds_gaps` lists | A3 |
| Token type validity | `ProofToken.token_type` | A3 |
| Class membership | `Membership.InClass` assertion | A5 |

### Architectural consequence

The break surface (5 attacks) and the falsification result (2a: 6/6) share one root cause: the compiler trusts its inputs. This is not a design flaw — it is the separation of concerns that makes the compiler possible.

The compiler's job is to enforce structural completeness: was an attestation presented for each required gap, is the evidence bound to this deployment context, is it current? The certifier's job is to ensure the attestation is truthful. The institution's job is to ensure the certifier is accountable.

A compiler that tried to verify gap status claims would need to re-run every study, re-evaluate every model, and re-analyze every population for every compilation. That is not a compiler — that is the entire regulatory process. The architecture distributes the work correctly:

```
Institution → accountable certifiers
Certifier   → truthful attestations with valid provenance
Compiler    → structural completeness of the attestation chain
Profile     → which attestations are required for which permission level
```

The stress tests reveal exactly where each layer's responsibility begins and ends. The compiler holds its layer. What breaks it is a certifier failure — and certifier failures are auditable, traceable to a specific token, and attributable to a specific issuer.

---

## Comparison to LEG-001

The legal example did not have an explicit stress test, but the same trust model applies. A legal research bridge that marks `jurisdictional_scope_gap: bounded` without issuing a `JurisdictionToken` would produce the same A1 break. The profile would not catch it. The certifier discipline prevents it.

The medical stress tests are more severe because the medical domain has quantitative thresholds (PPV floors, AUC values) that the legal domain does not. A2 (threshold gaming) has no direct legal analog. This means the medical domain has a deeper reliance on detail contracts inside token constructors to enforce the quantitative layer — a layer that the compiler cannot reach.

---

## What Would a Stronger Compiler Require?

For completeness, here is what would be needed to close each break vector at the compiler level — and why each is architecturally inadvisable.

**To close A1/A10 (gap status trust):** Require that every `bounded` or `closed` gap status be backed by at least one valid token with matching `bounds_gaps` or `closes_gaps`. This would make direct `GapRecord.status` assertions insufficient — all status claims would need to come through tokens. This is achievable and would significantly harden the compiler. The cost: it removes the bridge-level shorthand used throughout the medical and legal examples and requires every test to construct full tokens.

**To close A2 (threshold gaming):** Add a numerical floor registry to the profile — `minimum_bound_value` per gap per permission level. When `minimum_bound_value` is set, the compiler compares `GapRecord.bound_value` against it. This is architecturally clean but requires the profile designer to pre-specify numerical floors for every gap, which is domain-specific knowledge the compiler currently leaves to token constructors.

**To close A3 (token type/gap mismatch):** Add a gap-type registry to the profile that maps `gap_id` → allowed `token_type` values. Tokens claiming to close a gap whose `token_type` is not in the allowed list would be rejected. This is feasible. The cost: it makes the profile more complex and couples the compiler to domain-specific type taxonomies.

**To close A5 (membership spoof):** Not closeable at the compiler level. Membership determination requires domain knowledge. The compiler can only enforce the consequence of the membership assessment.

**To close A3/A1 together via mandatory tokens:** The strongest hardening is to require that `ALR` (or above) is only reachable via token-backed gap status updates — direct `GapRecord.status="bounded"` assertions are allowed only up to AEX. This would mean: to reach ALR, every required gap must have a corresponding valid token in the context. The compiler already has the machinery (token provenance checking, invalid token rejection) to enforce this. The missing piece is a profile-level flag: `require_tokens_for_alr=True`.

None of these changes were made in this codebase. They are documented here as the natural extensions that a production hardening effort would consider, given the precise knowledge of the break surface this experiment produced.
