# A Gentle Introduction to Admissibility Compilers for Approximate Consequential Systems

Most organizations are comfortable with data-driven decisions. We look at dashboards, compare metrics, run experiments, and make judgment calls. That is useful, but it is not enough for systems that will increasingly make or recommend decisions on their own.

As decision systems become more automated, the standard has to change. A system should not merely produce an answer. It should also explain what evidence supports the answer, what uncertainty remains, and whether the answer is *permitted* given that uncertainty.

That is the idea behind an admissibility compiler for approximate consequential systems. This document introduces the concept, the vocabulary, and the **noethers-turnstile** library that implements it.

---

## When is this needed?

A system is **approximate consequential** — and needs an admissibility compiler — when it turns approximate evidence into consequential action.

It is usually needed when a system decides, recommends, or constrains:

- who gets exposure, access, budget, priority, or eligibility
- whether a customer, user, job, campaign, model, or experiment is judged good or bad
- whether an automated action should be taken under uncertainty
- whether a policy, ranking, allocation, launch, rollback, or enforcement decision is justified
- whether a partial signal is strong enough to support a stronger business claim

It is usually not needed when a system simply computes, transforms, or moves information without making a consequential claim — a service that sorts numbers, a parser that validates input format, a job that copies records, a dashboard used only for exploration, or a deterministic rule whose boundary and action are already obvious.

The key distinction is not complexity. A technically complex system may not need this structure. A simple threshold rule may need it if crossing the threshold changes customer treatment.

**The framework belongs at the boundary where evidence becomes judgment, and judgment becomes action.**

---

## The basic idea

An ordinary decision system says:

> "This action is good."
> "This campaign is underperforming."
> "This intervention is safe."

An approximate consequential system, structured with an admissibility compiler, says:

> "Here is the claim. Here is the evidence behind it. Here is what we observed. Here is what we could not observe. Here are the limits of the claim. Here is why the system is permitted to make this claim."

The goal is not perfect certainty. The goal is bounded, checkable judgment.

A claim does not have to be perfectly true to be useful. It does need to be honest about what it knows, what it does not know, and how far the evidence can be trusted.

---

## Why ordinary analytics language is not enough

A phrase like "reasonable accuracy" sounds practical but hides too much.

Different people interpret it differently. A product manager may hear "good enough to make a decision." A data scientist may hear "within an acceptable statistical tolerance." An engineer may hear "the data pipeline is working." All three interpretations are reasonable. None of them are the same thing.

For automated or semi-automated decision systems, we need language that is less subjective. We need to know not only whether the data seems good enough, but what specific claims the data can and cannot support. That is where the vocabulary below becomes necessary.

---

## Core concepts

### Bounded evidence

Bounded evidence states its own limits.

It does not just say: "We have data."

It says: "We have this data. It covers these cases. It misses these cases. The missing part is this large. Therefore, this is the strongest claim we are permitted to make."

An unbounded claim: "Apply rate is down, so job quality is worse."

A bounded claim: "Apply rate is down 12% in these markets over the last 14 days. We observe impressions, clicks, applies, and rank position. We do not observe recruiter response for 40% of applies, so we can certify a decline in seeker response, but not yet a decline in hiring quality."

The second claim is more useful because it is honest. It answers four questions:

1. What can we see?
2. How clearly can we see it?
3. What can't we see?
4. How much does that blindness limit the claim?

### Certifiable claims

A claim is certifiable when it is supported by enough evidence that someone else can check whether it is valid.

Certifiable does not mean perfectly true. It means: the claim is supported, bounded, inspectable, and honest about its uncertainty.

A non-certifiable claim: "This campaign is underperforming."

A certifiable claim: "This campaign is underperforming relative to comparable campaigns in the same market over the last 14 days. We observe impressions, clicks, applies, budget pacing, and rank position. We do not observe downstream recruiter response for 38% of applies, so the claim is limited to marketplace delivery and seeker response, not final hiring quality."

The difference is that the certifiable version carries its evidence with it. It can be inspected, challenged, limited, and trusted in a specific way.

### The gap between what you can certify and what you want to claim

This is the most important concept to internalize before the rest of the vocabulary makes sense.

Evidence has two distinct limitations. The first is approximation error: the system computed something, but the computation is an approximation, and we need to know how close it is to the exact answer. The second is model specification error: even if the computation is exact, the model being computed over may not be adequate for the real-world target.

These are different problems. Closing the first does not close the second.

An inference system that produces a certified exact posterior — KL divergence from the true posterior is zero — has established that its computation was correct *given the model*. It has not established that the model faithfully represents the real system. A fraud detection model that produces a perfectly calibrated score has established its calibration properties. It has not established that the features it was trained on are the right features for the population it will be deployed on.

This distinction — computation quality versus model adequacy — runs through all the machinery below. It is why **AEX** (computation certified) and **ALR** (computation certified *and* model adequate) are different permissions in the noethers-turnstile system.

### Certificates

A certificate is the evidence packet attached to a claim. It says: "This is why the system is permitted to make this claim."

In ordinary analytics, the result and the reasoning are usually separate — the result is in a dashboard, the reasoning is in a notebook or a meeting. In an approximate consequential system, they travel together.

A certificate for a marketplace decision might include: the data used, the time window, the comparison group, the observed outcome, the missing data, the uncertainty bound, the assumptions, the claim type, and the reason the claim is permitted.

The certificate is not decoration. It is part of the output.

### Envelopes

An envelope is the boundary around what can safely be claimed.

Data is missing. Proxies are imperfect. Markets drift. Logging policies change. Customer behavior shifts. The system's own actions affect what happens next. So we need a way to say: "Inside this boundary, the claim is supported. Outside this boundary, the system should not pretend to know."

An example: "We can certify marketplace delivery quality for this segment because impressions, clicks, applies, rank position, and budget state are observed. We cannot certify hiring quality because downstream employer response is missing for too large a share of the segment."

The envelope prevents overclaiming. It tells the system: you may say this much, but no more.

### Compilers

A compiler translates a high-level statement into something more precise and executable.

Someone might ask: "Are subscription customers being treated fairly?" That is a real question, but it is too vague for a system to answer directly. A claim compiler translates it into more precise questions: What does "fairly" mean here? Relative to what promise? Over what time window? Compared to which customers? With what observed data? With what missing data? Which claims are supportable? Which are not yet supportable?

The compiler's job is not to answer the original question. Its job is to turn the question into a structured set of claims, evidence requirements, and limits.

### Algebra

Algebra means rules for how claims combine.

In a marketplace, many local signals combine into larger judgments: apply rate, click-through rate, budget pacing, rank position, employer response, seeker mix, market density. Without rules, these signals are combined informally, which leads to overclaiming.

An algebra of claims asks: "If we know these smaller things, what larger thing are we permitted to conclude?" A decline in apply rate may support a claim about seeker response. It does not support a claim about job quality. A marketplace-level health claim may require both seeker-side and employer-side evidence. The algebra defines how claims compose without becoming nonsense. It prevents the system from turning weak local signals into strong global claims.

### Tokens

A token is a named, verifiable artifact that certifies a specific gap in the evidence is closed or bounded.

The system may be permitted to issue a `SEEKER_RESPONSE_DECLINE` token, but not a `HIRING_QUALITY_DECLINE` token — because it has enough evidence to show that seekers are responding less, but not enough evidence to prove that hiring outcomes are worse.

Tokens force precision. They prevent the system from using one observed fact to imply a stronger unobserved conclusion. They also carry provenance: a token is bound to the specific claim, candidate, context, and intended use it was issued for. A token issued for one context cannot be reused in another.

---

## How noethers-turnstile implements this

**noethers-turnstile** is a Rust library (with Python bindings) that implements the admissibility compiler. It takes a proof context — a bundle of evidence tokens, gap records, permission profiles, and runtime constraints — and emits the strongest permission the evidence can support.

The judgment form is:

```
Γ ⊢ z : p until ε
```

Read as: "Under proof context Γ, candidate output z is permitted at level p, valid until expiry ε."

### The permission chain

Permissions form a total order from most restrictive to least:

```
OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA < REV < AEX < ALR < AAA
```

| Permission | Meaning |
|---|---|
| `OOC` | Out of class — the system does not apply to this input |
| `EXP` | Expired — a token or context TTL has elapsed |
| `REF` | Refused — a credential was actively rejected (wrong provenance, revoked, invalid) |
| `UNS` | Unsupported — profiles exist but no evidence satisfies them |
| `DIA` | Diagnostic — the in-class floor; all gaps open, no positive evidence |
| `REV` | Reversible action permitted |
| `AEX` | Automatic execution permitted — computation certified |
| `ALR` | Automated and logged rollout — computation certified *and* model adequate |
| `AAA` | Unrestricted |

The compiler emits the **greatest** permission supported by the evidence. Every intermediate step can only lower the result — the compiler cannot promote beyond what the evidence supports.

### Gaps and profiles

A **gap** is a proof obligation — something the evidence must address before a higher permission can be granted. Gaps start open and are closed or bounded by tokens.

A **profile** specifies what gap coverage is required to unlock a given permission level. For example, a profile for `ALR` in the PGM inference domain might require:

- `approximation_gap` — CLOSED (computation is exact, or a certified bound exists)
- `freshness_gap` — CLOSED (the computation is current)
- `model_specification_gap` — BOUNDED (a domain expert has validated the model)

If any required gap is not satisfied, the profile is not met and `ALR` is not emitted.

### Tokens and provenance

A **proof token** is a typed, scoped artifact that closes or bounds one or more gaps. Every token is bound by a SHA-256 provenance hash over `(claim_id, candidate_id, context_id, allowed_use)`. A token issued for one context cannot be replayed in another — the provenance check is exact and bitwise.

The compiler does not trust token names. It verifies: is the token live? Does it match the detail contract? Is the provenance hash correct? Are the gaps it claims to close actually induced in this context?

### Structural non-promotion

The compiler's central guarantee is non-promotion: the emitted permission is no stronger than what the evidence jointly supports. This is enforced algebraically using a meet (minimum) operation over a finite permission chain. Composition of judgments takes the meet of components — a valid component cannot launder a refused one.

---

## A concrete example: PGM inference

The `examples/pgm` directory shows a complete domain adapter for Bayesian network inference.

The domain defines 11 gaps including `approximation_gap`, `model_specification_gap`, `freshness_gap`, and `evidence_identity_gap`. It defines profiles for four claim classes: exact inference result, certified approximate inference, uncertified approximate inference, and inference comparison.

Running the memory-budget demo against the diabetes BIF network (`python demo/run_demo.py`) produces:

```
Budget    Budget     Geometry    KL bound    Mem         Permission
tight      9 MB       —           —           —           OOC
medium    20 MB       infinite    ∞           20.0 MB     DIA
loose    120 MB       exact       0.0000     115.1 MB     AEX
```

Three rows, three meaningfully different outcomes:

- **OOC** — no certified plan fits within 9 MB. The inference problem is out of class for this memory tier. The minimum feasible plan requires ~11.2 MB.
- **DIA** — a plan fits in 20 MB using the Hilbert kernel, but the composition soundness check fails (4307 overlapping scope pairs across 161 sites). A finite KL bound requires a residual certificate that is not available here. Result: infinite certificate, no useful bound, permission stays at the in-class floor.
- **AEX** — exact inference everywhere at 120 MB. KL = 0. The computation is provably correct given the model. Permission is AEX, not ALR.

The last point is the key lesson. AEX proves the computation was correct given the model. ALR requires a separate `ModelSpecificationToken` issued by a domain expert attesting that the model is adequate for the real-world target. No inference kernel can self-issue that token. The system will not grant ALR without it.

```
AEX: "the computation was correct given the model."
ALR: "the model is adequate AND the computation was correct."
```

These are different questions. The compiler enforces the distinction.

---

## The certifier boundary

Every token in the system is issued by a **certifier** — a domain-specific authority that runs its own checks before signing a token. The compiler consumes tokens; it does not produce them. This separation is load-bearing.

If the compiler also issued tokens, the trust chain would collapse to the process trusting itself.

The PGM example ships a `PGMExactCertifier` in `bridge/certifier.py`. It accepts a graph, query, evidence, and algorithm; runs inference internally; verifies the certificate geometry is `"exact"`; and computes all fingerprints itself from the inputs. The caller cannot supply pre-computed hashes. If inference fails or returns an approximate certificate, the certifier refuses to issue.

The `PGMModelSpecificationCertifier` is a stub that raises `NotImplementedError` with an explanation. This is intentional. The inference system computes P(query | evidence, model). It has no access to the real-world system the model is supposed to represent. Issuing a `ModelSpecificationToken` would be the system attesting to its own adequacy — the exact circularity the certifier boundary is designed to prevent. Any production deployment that wants ALR must implement this certifier externally, with validation artifacts, scope limits, and an expiry policy.

---

## Getting started

Install the library:

```bash
pip install noethers-turnstile
```

Or build from source with maturin:

```bash
maturin develop
```

A minimal compilation:

```python
import noethers_turnstile as t

ctx = t.ProofContext(
    claim_id="my-claim",
    candidate_id="z-001",
    context_id="ctx-001",
    context_fingerprint="fp-001",
    allowed_use="diagnostics",
    membership=t.Membership.InClass,
    authority_ceiling=t.Permission.AAA,
    expiry=t.Expiry.never(),
    gaps=[t.GapRecord("g1", "calibration_gap")],
    profiles=[t.Profile(
        t.Permission.DIA,
        [t.GapRequirement("g1", "closed")],
    )],
    tokens=[],  # no evidence yet
)

live = t.compile(ctx)
rt = t.RuntimeContext(now_unix=..., context_fingerprint="fp-001")
print(live.permission_str(rt))  # → "UNS" (profile exists, gap unsatisfied)
```

Add a token with correct provenance and the gap closes:

```python
prov = t.compute_provenance_hash("my-claim", "z-001", "ctx-001", "diagnostics")

token = t.ProofToken(
    token_id="tok-001",
    token_type="CALIBRATION",
    schema_version="0.1",
    status="valid",
    closes_gaps=["g1"],
    bounds_gaps=[],
    provenance_hash=prov,
    issued_at=...,
    issuer="my-certifier",
)

ctx.tokens = [token]
live = t.compile(ctx)
print(live.permission_str(rt))  # → "DIA"
```

For a complete domain adapter, see `examples/pgm/bridge/`. For the full memory-budget demo, see `examples/pgm/demo/run_demo.py`.

---

## Where this design does not fit

Not every system needs this level of structure. An admissibility compiler is probably unnecessary when the work is purely descriptive, low-stakes, easily reversible, or not tied to automated action.

The design is most valuable when a system might otherwise confuse a partial signal for a complete truth — and then act on it.

The standard should not be: every metric needs a certificate. The standard should be: any approximate consequential system should carry the claim, the limits, and the permission with it.

---

## Summary

An approximate consequential system, structured with an admissibility compiler, makes claims with evidence, boundaries, and permissions attached. It does not just return an answer. It returns the answer together with the evidence contract that makes the answer valid.

noethers-turnstile implements this as a structural compiler. The compiler checks evidence but does not produce it. Certifiers produce tokens. Tokens close gaps. Profiles map gap coverage to permissions. The compiler emits the greatest permission the evidence can support and cannot be induced to emit more.

The goal is not systems that are always right. The goal is systems that are honest about what they know, what they do not know, and what they are permitted to do anyway.
