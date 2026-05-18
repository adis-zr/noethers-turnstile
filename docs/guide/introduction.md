# A Gentle Introduction to Admissibility Compilers for Approximate Consequential Systems

Most organizations are comfortable with data-driven decisions. We look at dashboards, compare metrics, run experiments, and make judgment calls. That is useful, but it is not enough for systems that will increasingly make or recommend decisions on their own.

As decision systems become more automated, the standard has to change. A system should not merely produce an answer. It should also explain what evidence supports the answer, what uncertainty remains, and whether the answer is *permitted* given that uncertainty.

That is the idea behind an admissibility compiler for approximate consequential systems. This document introduces the concept, the vocabulary, and the **noethers-turnstile** library that implements it.

---

## When is this needed?

A system is **approximate consequential** when it turns approximate evidence into consequential action.

It is usually needed when a system decides, recommends, or constrains:

- who gets exposure, access, budget, priority, or eligibility
- whether a customer, user, model, or experiment is judged good or bad
- whether an automated action should be taken under uncertainty
- whether a policy, ranking, allocation, launch, rollback, or enforcement decision is justified
- whether a partial signal is strong enough to support a stronger business claim

It is usually not needed when a system simply computes, transforms, or moves information without making a consequential claim — a service that sorts numbers, a parser that validates input format, a job that copies records, a dashboard used only for exploration, or a deterministic rule whose boundary and action are already obvious.

The key distinction is not complexity. A technically complex system may not need this structure. A simple threshold rule may need it if crossing the threshold changes customer treatment.

**The framework is valuable when evidence turns into judgment, and judgment turns into action.**

---

## The basic idea

An ordinary decision system says:

> "This action is good."
> "This model is underperforming."
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

## Where this design does not fit

Not every system needs this level of structure. An admissibility compiler is probably unnecessary when the work is purely descriptive, low-stakes, easily reversible, or not tied to automated action.

The design is most valuable when a system might otherwise confuse a partial signal for a complete truth — and then act on it.

The standard should not be: every metric needs a certificate. The standard should be: any approximate consequential system should carry the claim, the limits, and the permission with it.

---

## Summary

An approximate consequential system, structured with an admissibility compiler, makes claims with evidence, boundaries, and permissions attached. It does not just return an answer. It returns the answer together with the evidence contract that makes the answer valid.

noethers-turnstile implements this as a structural compiler. The compiler checks evidence but does not produce it. Certifiers produce tokens. Tokens close gaps. Profiles map gap coverage to permissions. The compiler emits the greatest permission the evidence can support and cannot be induced to emit more.

The goal is not systems that are always right. The goal is systems that are honest about what they know, what they do not know, and what they are permitted to do anyway.
