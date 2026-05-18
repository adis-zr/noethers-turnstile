# How noethers-turnstile implements this

**noethers-turnstile** is a Rust library (with Python bindings) that implements the admissibility compiler. It takes a proof context — a bundle of evidence tokens, gap records, permission profiles, and runtime constraints — and emits the strongest permission the evidence can support.

The judgment form is:

```
Γ ⊢ z : p until ε
```

Read as: "Under proof context Γ, candidate output z is permitted at level p, valid until expiry ε."

## The permission chain

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

## Gaps and profiles

A **gap** is a proof obligation — something the evidence must address before a higher permission can be granted. Gaps start open and are closed or bounded by tokens.

A **profile** specifies what gap coverage is required to unlock a given permission level. For example, a profile for `ALR` in the PGM inference domain might require:

- `approximation_gap` — CLOSED (computation is exact, or a certified bound exists)
- `freshness_gap` — CLOSED (the computation is current)
- `model_specification_gap` — BOUNDED (a domain expert has validated the model)

If any required gap is not satisfied, the profile is not met and `ALR` is not emitted.

## Tokens and provenance

A **proof token** is a typed, scoped artifact that closes or bounds one or more gaps. Every token is bound by a SHA-256 provenance hash over `(claim_id, candidate_id, context_id, allowed_use)`. A token issued for one context cannot be replayed in another — the provenance check is exact and bitwise.

The compiler does not trust token names. It verifies: is the token live? Does it match the detail contract? Is the provenance hash correct? Are the gaps it claims to close actually induced in this context?

## Structural non-promotion

The compiler's central guarantee is non-promotion: the emitted permission is no stronger than what the evidence jointly supports. This is enforced algebraically using a meet (minimum) operation over a finite permission chain. Composition of judgments takes the meet of components — a valid component cannot launder a refused one.