# Item 3 — Claim-ledger audit

For each row of Table 1, I check whether the status verb matches what is
actually proven, and I add a traceability column mapping each claim to its
source (theorem, lemma, results file, or §).

The audit posture is conservative: any cell whose modal verb implies more
than is delivered is flagged. The ledger's rhetorical power depends on
every cell being exactly true.

## Row 1
**Claim**: A(e) is the strongest permission sound over all worlds compatible with evidence e
**v3 status**: Definition and theorem consequence
**Source**: §2.2 (Definition of A(e) as meet over fiber)
**Audit**:
- "Definition" is exact — A(e) is defined as the meet.
- "Theorem consequence" presumably refers to the soundness property
  `p ≼ A(e) → p is sound for every world in F(e)`, which is immediate
  from the definition of meet.
- Modal verb: "is" — claims an identity. Correct: A(e) is *defined* as
  this object.
- **Verdict**: pass.

## Row 2
**Claim**: Finite permission grids approximate A(e) from below
**v3 status**: Theorem
**Source**: §2.3 (or Theorem 1 in the appendix — "for every evidence state e, C_k(e) ≼ A(e)")
**Audit**:
- "Theorem" requires a formally stated and proven theorem. §2.3 states it
  informally and proves it as `floor of A(e) on P_k ≼ A(e)`, which is
  immediate. The proof is one line.
- **Verdict**: pass. Note that "Theorem" is a generous label for a one-line
  immediate consequence — a referee could ask whether this is a theorem
  or a definitional remark. Suggest "Lemma" or "Consequence" for
  precision, but "Theorem" is defensible.

## Row 3
**Claim**: Nested permission-grid refinement sharpens authorization monotonically
**v3 status**: Theorem
**Source**: §2.3 statement "If P_k ⊆ P_{k+1}, then C_k(e) ≼ C_{k+1}(e) ≼ A(e)"
**Audit**:
- Direct consequence of the floor map's monotonicity in the lattice.
- "Sharpens monotonically" matches the inequality.
- **Verdict**: pass.

## Row 4
**Claim**: Semantic evidence coarsening cannot create authorization
**v3 status**: Theorem
**Source**: §2.6 statement "A^π(π(e)) ≼ A(e)"
**Audit**:
- Direct consequence of the meet's monotonicity: a larger fiber gives a
  weaker or equal meet.
- "Cannot create" matches the inequality (the inequality is in the
  direction the claim asserts).
- **Verdict**: pass.

## Row 5 — FLAGGED IN USER'S NOTE
**Claim**: Implemented evidence projection is sound *only* when authorization-admissible
**v3 status**: Theorem and projection-fidelity test
**Source**: §2.6 admissibility condition + Level 5 demonstration
**Audit**:
- The word "only" claims a biconditional:
  - (⇒) authorization-admissible → sound. This is proven (admissibility
    is *defined* as `Â^π(π(e)) ≼ A(e)`, which is soundness).
  - (⇐) sound → authorization-admissible. This is the converse: any
    unsound projection is inadmissible. This is also immediate from the
    definitions (admissibility ≡ soundness for all e).
- So if "admissible" *means* "the projection satisfies the soundness
  inequality for every e", then the biconditional is trivially true by
  definition.
- The Level 5 demonstration witnesses one inadmissible projection that
  is also unsound; it does not establish the biconditional, but the
  biconditional is by-definition.
- **Verdict**: the claim is defensible *by definition*. But the user's
  concern is real: "only" is a strong word and a referee will check. The
  cleaner formulation is:

  > Authorization-admissibility is *equivalent to* per-state soundness of
  > the implemented projection. The projection-fidelity test witnesses
  > one inadmissible, unsound projection (Level 5) to demonstrate the
  > admissibility condition is non-vacuous.

  The current "only" claim is *technically* a tautology because of the
  definitions, but the phrasing makes it sound like a substantive claim.
  Either soften "only" or make clear that the equivalence is by definition.

- **Recommended action**: rewrite to either
  - "Implemented evidence projection is sound iff authorization-admissible,
    by definition. The non-vacuity of this equivalence is witnessed by
    Level 5 (an inadmissible projection that is unsound for at least one e)."
  - or just drop "only": "Implemented evidence projection is sound when
    authorization-admissible. Inadmissible projections may be unsound; the
    Level 5 projection-fidelity test witnesses this for at least one e."

## Row 6
**Claim**: Resolving evidence refinement recovers A(e) semantically
**v3 status**: Theorem
**Source**: Lemma A.3 or §2.6 ("if π_m is resolving and admissible, A^{π_m}(π_m(e)) → A(e) along m")
**Audit**:
- Standard convergence-of-meets result given resolving refinement.
- "Semantically" qualifies the claim correctly (semantic projected
  authorization, not implemented).
- **Verdict**: pass.

## Row 7
**Claim**: Joint evidence and permission refinement converges to A(e) from below
**v3 status**: Theorem and full-chain implemented demonstration
**Source**: Lemma A.10 + §2.7.2 (525/525 monotone, 21/21 jointly converged)
**Audit**:
- Theorem side: A.10 establishes the conditions.
- Implementation side: §2.7.2 demonstrates 21 cases. **HOWEVER**, per the
  Item 0 audit, the 21 cases include 5 (S-REF + 4 witnesses) that run
  under non-canonical maps. The aggregate "21/21 jointly converged" is
  honest only if reframed as "21 cases each under its own map".
- The claim "converges to A(e)" remains true per-case. The cross-case
  uniformity in the v3 text is what needs softening.
- **Verdict**: pass-with-caveat. Needs the Item 0 reframing in the §2.7.2
  text. The ledger row itself can stand if the §2.7.2 text is revised.

## Row 8
**Claim**: Active evidence refinements can shift permission when they resolve active blockers
**v3 status**: Synthetic control demonstration
**Source**: §2.7.3 active-refinement witnesses + Lemma A.9
**Audit**:
- A.9 proves the existence direction: there exist witnesses that fire on
  the single-poison mechanism.
- "Can shift" is the existence direction. Correct as stated.
- **Verdict**: pass.

## Row 9 — FLAGGED IN USER'S NOTE
**Claim**: Later refinements can be inert when no remaining split crosses a permission boundary
**v3 status**: Analytic consequence and observed behavior
**Source**: §2.7.3 inertness observation + Lemma A.9
**Audit**:
- "Analytic consequence" is the strongest status verb in the table after
  "Theorem". It claims a deductive entailment.
- The Item 2 audit established: A.9 proves single-poison witnesses fire
  on the single-poison mechanism. It does NOT prove that inertness
  certifies absence of every active blocker — only absence of single-poison
  blockers.
- The §2.7.3 conclusion that "Epic tail inertness means no remaining
  active blocker is present" overclaims, and "Analytic consequence" in
  this row inherits the overclaim.
- The Provisional Lemma A.9.1 (Item 2) gives a coverage argument that
  under conservative-meet/join semantics, single-poison is the only
  mechanism. If A.9.1 is accepted as a lemma, "Analytic consequence" is
  correct. If A.9.1 is left provisional, "Analytic consequence" is
  overclaiming.
- **Verdict**: needs change. Two options:
  - **Conservative**: change to "Observed behavior in induction tail; the
    coverage statement (inert split certifies absence of single-poison
    blocker) is a Provisional Lemma A.9.1 with full coverage scope open."
  - **Aggressive**: keep "Analytic consequence" but cite A.9.1, and
    accept that A.9.1's coverage of `n`-component merges needs to be
    formal-proof-checked.
- **Recommended action**: conservative formulation. Cheap, honest, and
  doesn't depend on A.9.1's formalization holding up.

## Row 10
**Claim**: Skeleton-truncating projection can spuriously restore authorization
**v3 status**: Implemented non-vacuity witness
**Source**: §2.6 Level 5 + §2.7.4 L5 on non-resolving path
**Audit**:
- "Can spuriously restore" is the existence direction; the witnesses
  demonstrate it.
- "Non-vacuity witness" matches the role: shows the admissibility
  condition has empirical content.
- **Verdict**: pass.

## Row 11
**Claim**: Non-resolving paths may reconverge but lose monotone guarantees
**v3 status**: Implemented boundary test
**Source**: §2.7.4 + Lemma A.10
**Audit**:
- Per the Item 1b experiment, this is now established across **four**
  path shapes (A, B, C, D), not just one. The reconvergence depends
  exclusively on whether the path has a resolving tail (Paths A/B/C
  reconverge; Path D does not). This is much stronger than v3 currently
  claims.
- "May reconverge but lose monotone guarantees" matches Paths A/B/C.
- The new finding is that **non-resolving paths without a resolving tail
  may fail to reconverge entirely** (Path D, H02 and S-REV diverge to
  final emit AEX while A(e) = REV).
- **Verdict**: pass-but-strengthen. The current row understates what the
  experiment now shows. Recommend updating to:
  - "Non-resolving paths reconverge iff the path has a resolving meet-exact
    tail; the prefix sets the location and size of transient violations
    but not whether reconvergence occurs."
  - Status: "Theorem (tail-subsumes-prefix) and four-path-shape experiment".

## Row 12
**Claim**: External standards instantiate or approximate the same structure
**v3 status**: Correspondence audit, not primary validation
**Source**: §2.8 + classification table
**Audit**:
- "Instantiate or approximate" is appropriately weak.
- "Correspondence audit, not primary validation" explicitly downgrades
  this from a proof-of-concept to an external audit.
- **Verdict**: pass. This is one of the best rows in the ledger because
  it correctly downgrades a claim that would otherwise be load-bearing
  in a way the paper cannot support.

## Row 13
**Claim**: The calculus chooses the correct evidence map or permission hierarchy
**v3 status**: Not claimed
**Audit**:
- Explicit non-claim. Smart inclusion.
- **Verdict**: pass.

---

## Summary of changes recommended

| Row | Recommended action |
|---|---|
| 1 | Pass |
| 2 | Pass (consider "Lemma" instead of "Theorem" for precision) |
| 3 | Pass |
| 4 | Pass |
| 5 | **Soften "only" to "iff by definition" or drop "only"** |
| 6 | Pass |
| 7 | **Reframe §2.7.2 per Item 0 audit (per-case-under-own-map)** |
| 8 | Pass |
| 9 | **Soften "Analytic consequence" per Item 2 scope** |
| 10 | Pass |
| 11 | **Strengthen with four-path-shape Item 1 result + tail theorem** |
| 12 | Pass |
| 13 | Pass |

Of 13 rows, 4 need text changes:
- 2 softenings (Rows 5 and 9).
- 1 reframing (Row 7, depending on §2.7.2 main text).
- 1 strengthening (Row 11, which currently understates the result).

The audit reveals the ledger is mostly accurate but has two specific
overclaims (Rows 5 and 9) that a careful referee would catch. The
recommended changes harden the ledger to the form where every cell is
exactly true.

---

## Traceability column (recommended addition)

| Claim | Source |
|---|---|
| A(e) is the strongest sound permission... | §2.2 def; Lemma A.1 (soundness) |
| Finite permission grids approximate A(e) from below | §2.3; Theorem A.2 (floor monotonicity) |
| Nested grid refinement sharpens... | §2.3; Theorem A.2 (corollary) |
| Semantic coarsening cannot create authorization | §2.6; Theorem A.4 (meet over larger fiber) |
| Projection sound iff admissible (by definition) | §2.6 def; Level 5 §2.6/§2.7.4 |
| Resolving refinement recovers A(e) semantically | §2.6; Lemma A.3 |
| Joint refinement converges to A(e) | §2.7.2 + Lemma A.10; results/two_axis_convergence_v2_*.csv |
| Active refinements can shift permission | §2.7.3 + Lemma A.9; results/two_axis_convergence_v2_*.csv (witness rows) |
| Inert splits certify absence of single-poison blocker | §2.7.3 + Lemma A.9; Provisional Lemma A.9.1 |
| Skeleton-truncating projection can restore authorization | §2.7.4; Level 5; results/path_shapes_matrix.csv |
| Reconvergence requires resolving tail (new) | Item 1a theorem; results/path_shapes_matrix.csv (Paths A/B/C/D) |
| External standards correspondence | §2.8; per-standard classification |
| Calculus does not choose maps | §3 (explicit non-claim) |
