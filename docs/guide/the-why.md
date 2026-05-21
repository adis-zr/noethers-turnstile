# The Intuition Behind Admissibility Compilers
## The core idea

The easiest way to intuit the underlying math is to start with what it prevents. 

Let's take a hypothetical scenario where:
```
1. A system makes a partial observation
2. Another systems confidently acts on that partial observation
```

That act is dangerous. That is what this library is built to gate.
* A metric becomes a policy change
* A diagnostic result becomes a real-world recommendation
* An agent plan becomes execution 

The fundamental problem is that approximations turn into permitted consequential action silently.

This is the entire raison d'etre of the admissibility compiler. To stop that silent escalation.

An admissibility compiler asks:

> Given what we actually know, what are we allowed to do?

Not what do we hope is true. Not what did the model output. Not what permission did the caller request. Given the evidence, what is the system allowed to do?

That is the whole idea.

---

## The missing step

Most systems have a result.

They may also have evidence somewhere nearby: logs, dashboards, notebooks, evaluations, test results, provenance, or human notes.

But the result and the permission are usually mixed together.

A dashboard says:

> Apply rate is down.

A team concludes:

> Job quality is worse.

A system acts as if it has learned:

> Reduce exposure for this class of jobs.

Those are three different claims.

The first may be visible. The second may be partly supported. The third may require much stronger evidence.

An admissibility compiler inserts a step between them.

It says:

> Before this result can become permission, we must check what gaps remain.

Maybe we know seeker response declined. Maybe we do not know whether hiring quality declined. Maybe the data is fresh. Maybe the model is stale. Maybe the computation is exact, but the model itself is not validated. Maybe the evidence applies only to one market, not the whole marketplace.

The compiler does not make the evidence stronger. It keeps the permission honest.

---
## Why the judgment has this shape

The central judgment is:

```text
Γ ⊢ z : p until ε
```

Read it as:

> Under proof context Γ, candidate output z is permitted at level p, until expiry ε.

But the judgment does not come from syntax alone.

It comes from an objective.

Before the system can judge anything, someone has to say what kind of action is being governed, what kind of error matters, what “safe enough” means, and what levels of reliance are allowed. A medical inference, a marketplace control change, an experiment result, an agent step, and a model recommendation do not share the same permission structure by default. Their structure comes from the objective we are trying to protect.

That is the honest semantic bottleneck.

The compiler can check evidence, apply rules, combine constraints, lower permission when gaps appear, and emit the strongest safe permission. But it cannot discover the objective from nowhere. It cannot decide, by pure mathematics alone, which human values, operational risks, legal constraints, business trade-offs, or domain meanings should matter.

So the judgment has two layers.

First, humans define the semantic frame:

```text
What are we trying to license?
What evidence matters?
What permissions exist?
What counts as stale, invalid, or out of scope?
```

Then the compiler operates inside that frame:

```text
Given this evidence, for this candidate, under this objective,
what is the strongest permission still justified, and until when?
```

That is what the judgment records.

Each part answers a different question.

`z` is the thing being judged.

It might be a model output, an experiment result, a proposed action, a rollout plan, an agent step, or an inference result. Permission is never free-floating. A certificate cannot just say “this is safe.” It has to bind safety to a particular candidate, claim, result, action, or use.

Without `z`, evidence can be laundered from one object to another.

A certificate for one model output could be reused for another. A token for one rollout could be applied to a different rollout. A result from one market could be promoted globally.

So the judgment must say what object the permission attaches to.

`Γ` is the evidence context.

It contains the tokens, gaps, profiles, provenance, scope, authority, runtime facts, registry versions, allowed use, and other checks that determine what is supportable.

The same `z` can deserve different permissions under different evidence. With weak evidence, it may only support diagnosis. With stronger evidence, it may support automation. With expired evidence, it may support nothing.

So permission is not a property of `z` alone. It is a property of `z` under a proof context.

`p` is the permission.

It says what the system is allowed to do with `z`.

The compiler is not merely answering:

> Is `z` true?

That question is usually too blunt.

The real question is:

> What may we do with `z`?

The same result may be acceptable for logging, acceptable for human review, acceptable for an experiment, but not acceptable for automatic execution. So the judgment needs an explicit permission level.

`ε` is the expiry.

It says how long the judgment remains valid, or under what conditions it stops being valid.

Evidence ages. Authority changes. Tokens expire. Registries revoke things. Context drifts. Model versions change. Markets move. A permission cannot be timeless unless the domain itself is timeless, and most consequential systems are not.

You could hide expiry inside `Γ`, but the concept still has to exist. Writing `until ε` makes the validity boundary visible.

So the real question is not:

> Is `z` true?

The real question is:

> Given this objective, this evidence, this context, this candidate, and this intended use, how strongly may we rely on `z`, and for how long?

That is exactly what the judgment records.

The judgment is therefore necessary as a normal form, not because this exact notation is sacred, but because any useful action license under approximation needs the same ingredients somewhere:

```text
evidence/context  ⊢  object/action  :  permission  until validity boundary
```

Other encodings are possible:

```text
license(Γ, z, ε) = p
```

or:

```text
(Γ, z, ε) ↦ p
```

or:

```text
Γ ⊢ (claim, candidate, use) : permission until expiry
```

These are not different ideas. They are notational variants.

The sequent form is useful because it makes the dependency visible: the permission is not inside the object, and it is not inside the evidence alone. It is the result of judging the object under the evidence, relative to the objective.

This also explains the role of human judgment.

The permission chain itself is semantic. Someone has to decide what the levels mean. Someone has to decide whether a new evidence set should exist. Someone has to define what a token certifies, what gap it closes, what scope it applies to, and where it sits in the permission order.

The mathematics does not remove that responsibility.

What it does is make the responsibility explicit.

Once the objective, evidence vocabulary, and permission order are defined, the compiler can enforce them monotonically. Missing evidence cannot increase permission. Expired evidence cannot increase permission. Broader scope cannot increase permission. Weaker provenance cannot increase permission. Reduced authority cannot increase permission. Runtime failure cannot increase permission.

That monotonicity is what makes the judgment stable.

It lets the system combine many local checks into one global permission by taking the strongest permission that survives all constraints. Without monotonicity, the judgment would not be safe: a worse context might somehow justify stronger action, and the whole “gaps obstruct permission” structure would break.

So the punchline is:

```text
Γ ⊢ z : p until ε
```

is the minimal action-license shape.

It is necessary, up to equivalent encoding, because removing any part creates a laundering path:

```text
no z      → evidence can attach to the wrong object
no Γ      → permission ignores its supporting evidence
no p      → the system cannot say what action is allowed
no ε      → stale permission can persist forever
```

It is sufficient when `Γ` contains the whole permission-relevant observable state for the objective at hand.

That last phrase matters: **for the objective at hand**.

There is no objective-free, semantics-free permission judgment. The compiler can be formal, but the thing it formalizes is a human-defined action boundary. Once that boundary is defined, the judgment is the right shape because it captures exactly what safe action under approximation requires:

```text
Given what we are trying to protect,
given what we know,
given what is being proposed,
what may we do,
and until when?
```

---

## Why not just say yes or no?

A yes/no system is too crude.

Many approximate systems are not simply safe or unsafe. They are safe for some uses and not for others.

A result might be good enough for diagnostics but not for automatic action.

A computation might be exact given a model, but the model might not be validated against the real world.

An experiment might support a limited rollout but not a global launch.

A policy change might be safe if reversible but not safe if irreversible.

So the compiler does not emit only `ALLOW` or `DENY`.

It emits the strongest permission the evidence supports.

That gives the system room to be useful without pretending to know more than it does.

---

## The permission chain

Permissions form a chain from most restrictive to least restrictive:

```text
OOC < EXP < REF < UNS < ETA < ESC < ROL < DIA < REV < AEX < ALR < AAA
```

You can think of this as a staircase.

At the bottom, the system cannot use the result at all.

Higher up, the system can do more.

The compiler tries to climb as high as the evidence allows. But every missing requirement, failed check, expired token, scope mismatch, or authority limit can pull it back down.

This is useful because actions are not all the same.

Diagnostic use is weaker than review. Review is weaker than automatic execution. Automatic execution given a model is weaker than rollout authority against the real world.

The chain gives these distinctions a single shared language.

It lets the system say:

> This evidence is enough for `DIA`, but not for `AEX`.

or:

> This evidence is enough for `AEX`, but not for `ALR`.

or:

> This evidence would support `AAA`, but authority only permits `AEX`.

The compiler is not deciding what the organization values. The profile and authority rules do that. The compiler enforces the resulting structure.

---

## Why monotonicity matters

Monotonicity means:

> If the situation gets worse, the permission cannot get stronger.

That sounds obvious. It is also the main safety idea.

If evidence becomes stale, permission should not increase.

If provenance is missing, permission should not increase.

If scope becomes broader, permission should not increase.

If uncertainty grows, permission should not increase.

If authority is reduced, permission should not increase.

If a required dependency disappears, permission should not increase.

This is why the permission chain matters. Once permissions are ordered, the compiler can enforce a simple rule:

> Every check may keep the permission the same or lower it. No check may raise it unless new evidence is compiled into a new judgment.

That rule is what prevents evidence laundering.

A fresh piece of evidence cannot hide a stale one. A valid token cannot erase a refused token. A broad claim cannot inherit a narrow certificate. A model-quality certificate cannot pretend to be a real-world adequacy certificate.

Everything moves in the safe direction.

---

## The meet intuition

The compiler combines constraints using a simple rule:

> The final permission is no stronger than the weakest live constraint.

This is called a meet. In this setting, it is just the minimum in the permission chain.

Suppose one part of the evidence supports `ALR`, but another required part only supports `DIA`.

The final result is not halfway between them.

It is `DIA`.

Suppose an action has enough evidence for automatic execution, but the authority ceiling is only experiment approval.

The final result cannot exceed the authority ceiling.

Suppose two envelopes are composed, and one is fresh but the other is expired.

The composed result is expired.

This is the discipline:

> Combining evidence cannot make the weakest part disappear.

That is why composition is safe.

Without this rule, systems can accidentally launder evidence. They can combine a narrow, stale, or weak component with a strong-looking component and produce a conclusion that looks stronger than either component really supports.

The meet prevents that.

---

## Gaps are unanswered questions

A gap is a proof obligation.

It is a question the system must answer before it can claim a stronger permission.

Examples:

```text
Is the computation accurate enough?
Is the data fresh enough?
Does the token apply to this candidate?
Is the model adequate for the real-world target?
Is the scope narrow enough?
Is the action within authority?
Could this policy interfere with another part of the system?
```

Every important uncertainty becomes a named gap.

That does not mean every gap must be closed before anything can happen. Different permissions require different levels of evidence.

A diagnostic permission may allow many gaps to remain open.

A limited experiment may require some gaps to be bounded.

An automatic rollout may require the load-bearing gaps to be closed or bounded by stronger evidence.

The point is not to demand perfect knowledge.

The point is to make the missing knowledge explicit.

---

## Profiles say how much evidence is enough

A profile maps gaps to permissions.

It says:

> To emit this permission, these gaps must be at these levels.

For example:

```text
DIA may require very little.
AEX may require the computation gap to be closed.
ALR may require computation to be closed and model adequacy to be bounded.
AAA may require even stronger authority, scope, and safety evidence.
```

This is where organizational judgment enters.

The compiler does not know, by itself, whether a particular business should require model adequacy for a rollout. The profile says that.

Once the profile is written, the compiler enforces it mechanically.

That separation is important.

Humans decide what evidence should be required.

Certifiers produce evidence.

The compiler checks whether the evidence satisfies the profile.

---

## Tokens are specific answers to specific gaps

A token is a verifiable evidence artifact.

It says:

> This specific gap is closed or bounded for this specific claim, candidate, context, and use.

The specificity matters.

A token is not a general badge of goodness.

A calibration token for one model version does not certify a different model version.

A freshness token for yesterday does not certify next week.

A proof token for one candidate does not certify another candidate.

A token that bounds approximation error does not bound model-specification error.

That last distinction is one of the most important examples.

A system may prove:

> This computation is correct given the model.

That does not prove:

> The model is adequate for the real world.

Those require different tokens because they answer different questions.

The compiler enforces that distinction.

---

## Why provenance is strict

Evidence must be bound to what it proves.

Otherwise, it can be replayed in the wrong place.

A token must match the claim, candidate, context, gap, and intended use. If any of those change, the token no longer proves the same thing.

This may feel strict, but it is necessary.

Most evidence laundering happens through quiet substitution.

A result from one market is used for another market.

A test from one model version is used for another model version.

A diagnostic certificate is used as rollout authority.

A token for one gap is treated as if it closed a different gap.

Strict provenance blocks that move.

No match, no proof.

---

## Why expiry is part of the judgment

Evidence ages.

Markets drift. Models change. Logs arrive late. Customers behave differently. Policies interact. Dependencies are revoked. Authority changes.

A judgment that was valid yesterday may not be valid today.

That is why the judgment says:

```text
until ε
```

The expiry is not decoration. It is part of the permission.

The compiler is saying:

> This permission is valid only while these conditions remain true.

Runtime checks can only lower the permission. They cannot upgrade it.

If a token expires, the permission drops.

If a registry is unavailable, the permission drops.

If a required runtime fact is missing, the permission drops.

If new evidence appears, the system must compile a new judgment.

That keeps old envelopes from silently becoming stronger than they were.

---

## The certifier boundary

The compiler checks evidence. It does not create evidence.

This separation is load-bearing.

A certifier is the domain-specific authority that decides whether a token should be issued.

For example, an inference certifier may check whether a computation is exact. A model-specification certifier may check whether a model is adequate for a real-world target. A marketplace certifier may check whether an experiment result supports a particular claim.

The compiler consumes those tokens and applies the rules.

If the compiler also issued the tokens, the system would be trusting itself.

That would collapse the boundary.

The compiler should be boring. It should ask:

```text
Is the token valid?
Is it live?
Does it match this claim?
Does it match this context?
Does it close the right gap?
Does the profile accept it?
Does the permission stay within authority?
```

It should not invent domain truth.

---

## Why this works structurally

The structural reason is simple:

> Every route to stronger permission must pass through an explicit requirement.

A stronger permission requires a stronger profile.

A stronger profile requires more gaps to be bounded or closed.

A gap can be bounded or closed only by a valid token.

A valid token must satisfy its contract.

A token must match the exact claim, candidate, context, gap, and use.

The final permission is then met with expiry, authority, scope, runtime checks, structural failures, and control obligations.

At no point is there a path that says:

> The output looks good, so grant the action.

That path is deliberately removed.

The output is not permission.

The evidence context determines permission.

---

## The deeper intuition: finite visible obstructions

The representation theorem says something deeper.

It asks:

> When can a domain be compiled this way at all?

The answer is:

> When the reasons a permission can fail are visible through a finite set of checkable obstruction questions for each judgment.

That sounds abstract, but the intuition is practical.

For any proposed action, imagine there is an ideal answer:

> If we knew everything, what is the strongest permission this action deserves?

Call that the ideal permission.

In real systems, we do not know everything. So we need a smaller set of observable questions that tell us enough.

Questions like:

```text
Is the computation certified?
Is the model adequate?
Is the evidence fresh?
Is the scope narrow enough?
Is provenance exact?
Is authority present?
Is interference bounded?
Is the claim only diagnostic?
```

If those questions are enough to determine the right permission, then the domain is compilable.

The compiler does not need to see the whole ideal world. It needs to see the finite shadow of the world that matters for permission.

That finite shadow is the quotient.

---

## A simpler way to say quotient

A quotient is what you get when many detailed situations are treated the same because they have the same permission-relevant shape.

For example, two marketplace situations may differ in thousands of raw details. But for a particular rollout decision, they may have the same answers to the relevant questions:

```text
freshness: ok
proxy evidence: bounded
interference: open
authority: present
scope: limited
```

If those answers are the same, the compiler may treat the two situations the same for this permission decision.

The quotient is the compressed view.

It throws away details that do not affect the permission and keeps the details that do.

The representation theorem says:

> A sharp compiler exists when this compressed view is finite, monotone, observable, and rich enough to recover the ideal permission.

That is the mathematical reason the compiler can work.

---

## Why finite matters

A production compiler must finish.

It cannot ask infinitely many questions.

It cannot inspect every possible hidden fact about the world.

It needs a finite checklist for each judgment.

Finite does not mean the whole system has only finitely many possible claims, tokens, models, users, markets, or contexts.

New instances can appear forever.

Finite means:

> For this specific judgment, the compiler induces a finite set of relevant checks.

A system may have infinitely many possible provenance atoms over its lifetime because new tokens and claims keep appearing. But any one judgment uses only the tokens and gaps relevant to that judgment.

That is enough.

The compiler is not one giant global checklist. It is a uniform way to build a finite checklist for each case.

---

## Why monotone obstructions matter

An obstruction is a reason a permission should fail.

Examples:

```text
missing provenance
expired token
open model-specification gap
scope too broad
authority absent
freshness failed
rollback unavailable
```

These are monotone in the safety sense:

> Adding an obstruction cannot make the action more permitted.

That is why obstruction language fits the permission chain.

The compiler can ask which obstructions are present, then map that obstruction pattern to the strongest still-allowed permission.

If more obstructions appear, the result can only stay the same or go down.

This is the core geometry of the system:

```text
more obstruction  →  no stronger permission
less evidence     →  no stronger permission
wider claim       →  no stronger permission
staler context    →  no stronger permission
```

That is the reason the algebra is so small.

Once everything is expressed as monotone obstruction, the safe operation is just: take the most restrictive live constraint.

---

## Sharpness versus mere safety

There is a trivial safe compiler:

> Always deny everything.

That compiler never over-promotes. It is also useless.

So safety alone is not the goal.

The goal is to emit the strongest permission the evidence really supports.

That is sharpness.

A sharp compiler does not merely avoid bad actions. It also avoids unnecessary refusal.

It says:

> We should deny what is unsupported, but we should not deny what is actually supported.

This matters because the purpose of the system is not paralysis. The purpose is bounded action.

A good admissibility compiler lets the system act when the evidence is strong enough, and only then.

---

## Why the chain is semantic, but the enforcement is mathematical

The permission chain is not discovered from pure math alone.

Someone has to decide what the permissions mean.

Diagnostic use, human review, experiment approval, limited rollout, and automatic action are semantic distinctions. They come from the domain and from governance.

But once those meanings are fixed, the compiler can enforce them mathematically.

The semantic work is deciding:

```text
What permissions exist?
What does each permission allow?
What gaps matter?
What evidence is required for each permission?
What counts as authority?
What expires?
```

The mathematical work is ensuring:

```text
stronger permissions require no weaker evidence;
missing evidence cannot promote;
tokens cannot be replayed;
composition cannot hide weak components;
runtime cannot upgrade;
profile changes do not rewrite old envelopes.
```

So the answer is not that the chain is magically forced by set theory.

The chain is a governance object.

The monotone structure is the mathematical discipline that makes it safe.

---

## Why this is not just naming evidence

A common worry is:

> Aren't we just giving evidence sets names?

If all we did was name evidence, yes, that would not solve the problem.

The important move is not naming.

The important move is binding each name to:

```text
a gap;
a claim;
a candidate;
a context;
a use;
a contract;
a scope;
an expiry;
a permission profile.
```

A token is not powerful because it has a name.

It is powerful only if it passes the contract and matches the judgment.

A profile is not powerful because it lists requirements.

It is powerful because stronger permissions cannot require weaker evidence.

A compiler is not powerful because it emits labels.

It is powerful because every label is produced by a non-promotion rule.

The discipline is what matters.

---

## Why model adequacy is separate from computation quality

This is the simplest example of why the framework is necessary.

Suppose an inference system computes an exact posterior under a model.

That is strong evidence about the computation.

It says:

> Given this model, the computation is correct.

But it does not say:

> This model is the right model for the real world.

Those are different claims.

The first can be certified by an inference certifier.

The second requires model validation, external evidence, domain judgment, and scope limits.

If the system treats the first as if it proved the second, it has laundered evidence.

The compiler prevents this by making them separate gaps.

Closing the computation gap does not close the model-specification gap.

That is why a result may earn `AEX` but not `ALR`.

The computation may be safe to execute as a computation. The result may not yet be safe to roll out as a real-world action.

---

## Why old judgments are immutable

Once a judgment is emitted, it should not be silently reinterpreted.

If the taxonomy changes, that is a new version.

If the profile changes, that is a new version.

If the token contract changes, that is a new version.

If new evidence arrives, that is a new compile.

Old envelopes do not become stronger because the rules changed later.

This matters because otherwise a relaxation could upgrade old decisions without anyone noticing.

The system would be able to say:

> This old evidence now means something stronger.

That is dangerous.

A new permission requires a new judgment.

---

## How the two papers fit together

There are two questions.

The first question is:

> If we build the compiler this way, why can't it promote beyond the evidence?

That is the structural soundness question.

The answer is the permission chain, meet, profiles, exact provenance, valid tokens, immutable versions, and runtime downgrade.

The second question is:

> When does a domain admit this kind of compiler in the first place?

That is the representation question.

The answer is finite monotone observability: the domain must have a finite, checkable obstruction view that determines the right permission for each judgment.

Put plainly:

```text
The structural paper says why the machine is safe.
The representation paper says when the world can be fed into that machine without losing the permission-relevant truth.
```

Both are needed.

A safe machine with the wrong domain interface can still be useless or too conservative.

A domain with a clean permission structure still needs an implementation that cannot launder evidence.

---

## The core intuition in one sentence

An admissibility compiler works because it turns action under uncertainty into a finite, monotone permission problem:

> identify the relevant gaps, accept only scoped evidence for those gaps, map the remaining obstruction pattern to the strongest supported permission, and let every later check only lower that permission.

That is why the judgment has the shape it has.

That is why the permission chain matters.

That is why monotonicity matters.

That is why provenance matters.

That is why expiry matters.

That is why the compiler can be small even when the domain is complicated.

The compiler is not trying to understand the whole world.

It is enforcing a disciplined boundary between:

```text
what the system computed,
what the evidence supports,
and what action is permitted.
```

That boundary is the whole point.