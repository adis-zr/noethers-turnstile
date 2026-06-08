# Item 2 — Inertness coverage: scope + provisional coverage theorem

## Background

§2.7.3 of v3 concludes:

> Epic tail inertness means no remaining active blocker is present, not
> that the refinement machinery has run out of signal.

Lemma A.9 establishes the *existence* direction: a constructed witness
with a strict-closed component paired with a bounded-poisoning sibling,
merged into a composite under conservative-meet status and
join-of-requirements semantics, blocks the target level at the merged
representation and resolves the block at the split. This rebuts "the
machinery ran out of signal."

The §2.7.3 conclusion claims the *converse*: an inert split certifies
structural absence of active blockers. Lemma A.9 does not prove this. It
shows witnesses fire on the single-poison mechanism only.

## Two paths forward

### Path 1 — Honest scope (cheap, ships now)

Replace the §2.7.3 conclusion with:

> The witnesses establish that inertness is not a property of the
> refinement machinery itself: when a single-poison active blocker is
> present in a coarsened composite (strict-closed component masked by a
> bounded sibling under conservative meet of status and join of
> requirements), splitting resolves the block and raises the emit.
>
> An inert split therefore certifies that no single-poison active blocker
> is present in the split composite. We do not prove that single-poison
> is the only mechanism by which a split could carry signal. Co-poisoning
> across three or more components, or alternative mechanisms involving
> requirement-join inflation without status-meet poisoning, are uncovered
> by these witnesses and remain open.

This is the minimum revision. It accurately scopes the §2.7.3 claim to
what A.9 actually proves.

### Path 2 — Coverage theorem (the real version)

If we can prove that single-poison is the *only* mechanism by which an
admissible split can change the emitted permission, then an inert split
certifies structural absence of any active blocker, not just single-poison
ones. The §2.7.3 conclusion as written becomes a theorem consequence
rather than an extrapolation.

**Provisional Lemma A.9.1 (Coverage of single-poison).**
*Let `C` be a composite gap merging components `g_1, ..., g_n` under the
projection semantics:*

  *status_C = ⋀ status_{g_i}     (conservative meet)*

  *requirement_C(p) = ⋁ requirement_{g_i}(p)     (join of component requirements at level p)*

*Suppose the unsplit composite `C` blocks emission at level `p`, while the
split components individually satisfy their own requirements at `p` (i.e.,
`status_{g_i} ≥ requirement_{g_i}(p)` for every `i`).*

*Then there exists at least one `g_i` such that:*

  *(a) `requirement_{g_i}(p) ≻ requirement_C(p)`'s lower bound on the other components, AND*

  *(b) the status of `g_i` is at or above its own requirement, while at
   least one other component's status falls below `requirement_C(p)`.*

*Equivalently: the configuration is a single-poison configuration —
the composite is blocked because the meet of statuses is dragged below
the join of requirements by at least one bounded-or-open sibling, while
the strict component's own status is satisfied individually.*

**Proof sketch.** Suppose the composite `C` blocks at level `p` after
projection but split components individually satisfy their requirements.
Then `status_C = ⋀ status_{g_i}` and `requirement_C(p) = ⋁ requirement_{g_i}(p)`.
By assumption `status_C < requirement_C(p)`. The status meet is
strictly less than the requirement join. Either (i) some `g_i` has
`status_{g_i} < requirement_C(p) = ⋁_j requirement_{g_j}(p)`, in which
case `g_i` is the strict component whose requirement *would have* been
satisfied individually but whose status is poisoned in the meet — no,
wait, the assumption is that each component individually satisfies its
*own* requirement. So for every `g_i`, `status_{g_i} ≥ requirement_{g_i}(p)`.

The composite blocks because `⋀ status_{g_i} < ⋁ requirement_{g_i}(p)`.
This is possible only if the components do not all share the strictest
requirement. Let `g*` be the component with the strictest requirement:
`requirement_{g*}(p) = ⋁_j requirement_{g_j}(p)`. Then by individual
satisfaction, `status_{g*} ≥ requirement_{g*}(p)`. For the meet
`⋀ status_{g_i}` to fall below `requirement_{g*}(p)`, some other
component `g_k` must have `status_{g_k} < requirement_{g*}(p)`. Since
that `g_k` individually satisfies its own requirement
`requirement_{g_k}(p)`, we have `status_{g_k} ≥ requirement_{g_k}(p)`,
and `requirement_{g_k}(p) < requirement_{g*}(p)` (since `g_k` is the
poisoner, not the strict component).

This is the single-poison configuration: a strict component `g*` with
its requirement satisfied, masked by a less-strict component `g_k` with
its requirement also satisfied but at a lower status. The poisoning
component `g_k` has `status_{g_k}` between `requirement_{g_k}(p)` and
`requirement_{g*}(p)` — i.e., it is "bounded by its own standard but
below the strict standard". □

**Discussion.** The lemma generalizes to `n` components. Multiple poisoners
are possible but the *mechanism* is the same: at least one strict component
whose individual requirement is the binding join, and at least one less-
strict component whose status falls below the binding join. Three-way
merges and higher fall under this case structurally — the binding
requirement is set by the strictest component; the poisoning comes from
any less-strict sibling.

**Caveat.** The proof assumes:
1. The composite semantics are exactly conservative-meet on status and
   join on requirements. Other projection semantics would not fall under
   this theorem.
2. Each component individually satisfies its own requirement (the case
   considered for "inert split certifies absence of single-poison blocker").
   The non-vacuous case where a component *also* fails its own requirement
   is a different mechanism — the composite blocks for a reason a split
   does not resolve, which the §2.7.3 result already handles correctly.
3. Requirements are point values in the status lattice (open, bounded,
   closed). Lattice extensions (intervals, fractional statuses) require
   re-examination.

## Recommendation

Adopt **Path 1 (honest scope)** in v3 main text. Add the **Provisional
Lemma A.9.1** as an appendix item, marked provisional, with the caveats.
This gives the cheap correct outcome (no overclaim) plus a forward-leaning
result that can be hardened in a follow-up paper.

If the lemma's proof survives a careful sanity check (covers all `n`-component
configurations under exactly the assumed semantics), the §2.7.3 conclusion
can be upgraded from "absence of single-poison blocker" to "absence of any
active blocker under conservative-meet/join semantics".

I'd suggest leaving §2.7.3 with the scoped conclusion for this paper and
flagging the coverage theorem as a footnote: "Provisional Lemma A.9.1
suggests this scope is the entire coverage; we leave the formal proof for
follow-up work."
