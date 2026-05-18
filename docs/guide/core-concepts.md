# Core concepts

## Bounded evidence

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

## Certifiable claims

A claim is certifiable when it is supported by enough evidence that someone else can check whether it is valid.

Certifiable does not mean perfectly true. It means: the claim is supported, bounded, inspectable, and honest about its uncertainty.

A non-certifiable claim: "This campaign is underperforming."

A certifiable claim: "This campaign is underperforming relative to comparable campaigns in the same market over the last 14 days. We observe impressions, clicks, applies, budget pacing, and rank position. We do not observe downstream recruiter response for 38% of applies, so the claim is limited to marketplace delivery and seeker response, not final hiring quality."

The difference is that the certifiable version carries its evidence with it. It can be inspected, challenged, limited, and trusted in a specific way.

## The gap between what you can certify and what you want to claim

This is the most important concept to internalize before the rest of the vocabulary makes sense.

Evidence has two distinct limitations. The first is approximation error: the system computed something, but the computation is an approximation, and we need to know how close it is to the exact answer. The second is model specification error: even if the computation is exact, the model being computed over may not be adequate for the real-world target.

These are different problems. Closing the first does not close the second.

An inference system that produces a certified exact posterior — KL divergence from the true posterior is zero — has established that its computation was correct *given the model*. It has not established that the model faithfully represents the real system. A fraud detection model that produces a perfectly calibrated score has established its calibration properties. It has not established that the features it was trained on are the right features for the population it will be deployed on.

This distinction — computation quality versus model adequacy — runs through all the machinery below. It is why **AEX** (computation certified) and **ALR** (computation certified *and* model adequate) are different permissions in the noethers-turnstile system.

## Certificates

A certificate is the evidence packet attached to a claim. It says: "This is why the system is permitted to make this claim."

In ordinary analytics, the result and the reasoning are usually separate — the result is in a dashboard, the reasoning is in a notebook or a meeting. In an approximate consequential system, they travel together.

A certificate for a marketplace decision might include: the data used, the time window, the comparison group, the observed outcome, the missing data, the uncertainty bound, the assumptions, the claim type, and the reason the claim is permitted.

The certificate is not decoration. It is part of the output.

## Envelopes

An envelope is the boundary around what can safely be claimed.

Data is missing. Proxies are imperfect. Markets drift. Logging policies change. Customer behavior shifts. The system's own actions affect what happens next. So we need a way to say: "Inside this boundary, the claim is supported. Outside this boundary, the system should not pretend to know."

An example: "We can certify marketplace delivery quality for this segment because impressions, clicks, applies, rank position, and budget state are observed. We cannot certify hiring quality because downstream employer response is missing for too large a share of the segment."

The envelope prevents overclaiming. It tells the system: you may say this much, but no more.

## Compilers

A compiler translates a high-level statement into something more precise and executable.

Someone might ask: "Are subscription customers being treated fairly?" That is a real question, but it is too vague for a system to answer directly. A claim compiler translates it into more precise questions: What does "fairly" mean here? Relative to what promise? Over what time window? Compared to which customers? With what observed data? With what missing data? Which claims are supportable? Which are not yet supportable?

The compiler's job is not to answer the original question. Its job is to turn the question into a structured set of claims, evidence requirements, and limits.

## Algebra

Algebra means rules for how claims combine.

In a marketplace, many local signals combine into larger judgments: apply rate, click-through rate, budget pacing, rank position, employer response, seeker mix, market density. Without rules, these signals are combined informally, which leads to overclaiming.

An algebra of claims asks: "If we know these smaller things, what larger thing are we permitted to conclude?" A decline in apply rate may support a claim about seeker response. It does not support a claim about job quality. A marketplace-level health claim may require both seeker-side and employer-side evidence. The algebra defines how claims compose without becoming nonsense. It prevents the system from turning weak local signals into strong global claims.

## Tokens

A token is a named, verifiable artifact that certifies a specific gap in the evidence is closed or bounded.

The system may be permitted to issue a `SEEKER_RESPONSE_DECLINE` token, but not a `HIRING_QUALITY_DECLINE` token — because it has enough evidence to show that seekers are responding less, but not enough evidence to prove that hiring outcomes are worse.

Tokens force precision. They prevent the system from using one observed fact to imply a stronger unobserved conclusion. They also carry provenance: a token is bound to the specific claim, candidate, context, and intended use it was issued for. A token issued for one context cannot be reused in another.