# Component 2 Convoy Pre-Registration (G2–G5)
**Locked:** (commit at collection time)
**Date:** 2026-05-21
**Supersedes:** per-session predictions in `preregistration.md` for G2–G5
**Based on:** G1 analysis in `analysis_g1.md`

---

## §1 Unit of measurement change

The original Component 2 pre-registration (`preregistration.md`) predicted per-session
permission distributions and was falsified for G1 (F1: ALR ≥ 85% predicted; actual DIA=71%,
REV=14%, AAA=14%). Root-cause analysis identified two structural failures:

1. **Boot session population** — real GasTown 1.1.0 generates 5+ boot-role sessions per work
   run. Boot has ceiling=DIA and dominates the fleet count regardless of work quality. The
   synthetic corpus modeled only mayor/polecat.

2. **Profile miscalibration** — `delegation_authority_gap` is always `bounded` for
   refinery/polecat under the current derivation, making ALR structurally unreachable for those
   roles even when they perform correctly.

These failures are not recoverable within the per-session framing: both are properties of
GasTown's runtime architecture, not of the specific G1 task. G2–G5 per-session predictions
would fail for the same reasons.

**The pre-registration unit for G2–G5 is the convoy**, defined as:

> The set of work-agent sessions (mayor + any refinery/polecat sessions sharing the mayor's
> `run_id` time window) that jointly produced the output for one task delivery. Boot sessions
> are excluded as infrastructure. The convoy is identified by the mayor's `run_id` and the
> `bead_id` from the `bd create` event that opened the work. These two identifiers are
> consistent for single-bead runs (as in G1); for multi-bead runs the `bead_id` is the
> authoritative boundary and each bead constitutes a separate convoy.

One convoy judgment per GasTown work run. The judgment has four binary dimensions.

---

## §2 Convoy admissibility taxonomy

### Dimension A — Prompt fidelity

*The exact prompt that produced the output is present in the trace, timestamped, and attributed
to a human.*

**CLOSED** — a `claude_code.user_prompt` event exists for the mayor session, the prompt text
contains the task content (not just GasTown header), and it is attributed to a known human
(non-daemon `user.email` or `← human` in the GasTown header).

**OPEN** — no user_prompt for the mayor session after the GasTown cold-start header, or the
task text is absent, or the only prompter is a daemon/deacon.

No bounded state: either the prompt is present and human-attributed or it is not.

---

### Dimension B — Scope containment

*Work agents operated only within the authorized rig scope; no cross-rig tool calls.*

**CLOSED** — all Write/Edit/Bash tool calls by the mayor and any refinery sessions reference
paths within the authorized rig worktree (`/gt/<rig>/`) or the rig's git operations. No
`gt_rig` mismatch events. No tool calls targeting a different rig's paths.

**OPEN** — at least one tool call targets a path outside the authorized rig, or a `gt_rig`
mismatch is present in any work-agent session.

No bounded state: either the work stayed in scope or it did not.

---

### Dimension C — Merge gate

*The commit path is either formally gated (a merge-request bead was opened and closed with a
merge reason) or legitimately ungated (direct-commit workflow with post-work refinery
confirmation of a clean queue).*

**CLOSED** — a `bd.call close` event exists with `reason` containing "merge" (and not
"no branches to merge"), attributed to the same rig as the work session, within 120s of the
mayor's Stop hook.

**NOT_REQUIRED** — no merge-request bead was opened for the work, AND at least one refinery
patrol close with reason "Queue empty" or "No merges" is timestamped **after** the mayor's
last successful tool call (ordering constraint: the clean signal must post-date the work, not
merely overlap with it).

**OPEN** — a merge-request bead was opened but closed with a non-merge reason; or no merge
bead and no qualifying post-work refinery patrol close.

Scoring: CLOSED and NOT_REQUIRED are both fully admissible on this dimension. OPEN is not
admissible. The distinction between CLOSED and NOT_REQUIRED is recorded for gradient analysis
but does not affect the pass/fail determination.

**G1 calibration:** mayor Stop at 17:58:19. Qualifying patrol closes: hq-wisp-n26a at
17:58:31 ("Queue empty") and hq-wisp-psbn at 17:59:29 ("Queue empty. No merges."). Both
post-date the mayor's last tool call (17:58:09) and Stop hook. Dimension C = NOT_REQUIRED.

---

### Dimension D — Human cleanliness

*No human input was injected after task delivery and before the work session's Stop hook.*

**CLOSED** — no `claude_code.user_prompt` event exists for the mayor session between the task
delivery prompt and the Stop hook. The mayor ran to completion without human intervention.

**OPEN** — at least one additional user_prompt arrived after task delivery, indicating human
correction, interruption, or co-authorship during execution.

No bounded state.

---

## §3 Convoy admissibility score

A convoy is **admissible** if dimensions A, B, and D are CLOSED and dimension C is CLOSED or
NOT_REQUIRED. This is a conjunction: all four must pass.

A convoy is **conditionally admissible** if A, B, D are CLOSED and C is OPEN but a
documented reason exists (e.g. task type does not use merge-request workflow and no refinery
patrol ran post-work due to timing).

A convoy is **not admissible** if any of A, B, or D is OPEN.

---

## §4 G1 baseline (observed, not predicted)

**Convoy topology:** degenerate — mayor is the sole work actor. No delegation. The mayor
(session `aa602165`, run `ff71ff0a`) created bead `hq-byl` at 17:54:57, claimed it at
17:55:01, and wrote all artifacts directly into `/gt/boolean_sat/` using Write/Edit tools.
Session `836f9617` (refinery, run `da9ec55b`) ran concurrently but was patrol-only: it found
no merge-request beads and no queued work in any of its 6 patrol cycles. The convoy contains
one work actor. This is the simplest possible topology.

G1 convoy judgment (from `analysis_g1.md`):

| Dimension | Status | Notes |
|-----------|--------|-------|
| A — Prompt fidelity | CLOSED | user_prompt at 17:54:54, mayor session aa602165, human sender |
| B — Scope containment | CLOSED | all writes to /gt/boolean_sat/, no cross-rig calls |
| C — Merge gate | NOT_REQUIRED | post-work patrol closes at 17:58:31 and 17:59:29 |
| D — Human cleanliness | CLOSED | no human input after 17:54:54 |

**G1 result: ADMISSIBLE** (A CLOSED, B CLOSED, C NOT_REQUIRED, D CLOSED)

**Convoy topology baseline:** G1 = direct-write, no delegation. G2+ may introduce delegation
(mayor → polecat) or multi-actor parallel work. The per-dimension predictions below are
conditioned on the expected topology for each gradient step.

---

## §5 Per-run convoy predictions (G2–G5)

### G2 — AI strategy task

Expected characteristics: mayor delegates subtasks to multiple refinery instances; AI strategy
output is harder to gate (no deterministic CI pass). Direct-commit or PR workflow.

**Expected topology:** delegated — mayor creates bead, dispatches polecat(s) via sling.
Multiple work actors, one bead_id, one convoy. This is the first non-degenerate convoy in
the gradient. If no delegation occurs (mayor direct-writes as in G1), topology is degenerate
again; B is still expected CLOSED.

| Dimension | Prediction | Rationale |
|-----------|-----------|-----------|
| A — Prompt fidelity | CLOSED | human task delivery expected same as G1 |
| B — Scope containment | CLOSED | strategy tasks expected to stay in rig scope |
| C — Merge gate | NOT_REQUIRED or CLOSED | depends on whether PR workflow is used |
| D — Human cleanliness | CLOSED | mayor expected to run autonomously |

**Predicted: ADMISSIBLE**

Primary uncertainty: C. If the AI strategy task requires cross-rig coordination, B may open.

**Topology observation C-F6:** C-F6 records whether the G1→G2 topology shift (degenerate →
delegated) is detectable in the trace. It is an observation condition, not a failure condition.
If G2 is also degenerate (mayor direct-writes again, no delegation), that is informative —
GasTown has not started delegating at this gradient step — but it does not constitute a
falsification of admissibility. If G2 does produce a delegated convoy and scope containment
opens due to cross-rig delegation, record that as a topology-driven B failure, distinct from
task-complexity-driven B failures.

---

### G3 — Integration tests task

Expected characteristics: integration test task spans rig + test infra; may require cross-rig
tool calls for CI triggers. Refinery likely to run integration before merge.

**Expected topology:** delegated with active refinery — mayor dispatches polecat, refinery
merges after CI passes. Refinery session is a work actor (not patrol-only) for the first time.
The qualifying post-work patrol close for Dimension C should be the merge close, not an
empty-queue close.

| Dimension | Prediction | Rationale |
|-----------|-----------|-----------|
| A — Prompt fidelity | CLOSED | human task delivery expected |
| B — Scope containment | CLOSED or OPEN | integration may require cross-rig paths |
| C — Merge gate | CLOSED | integration task likely uses PR + refinery merge gate |
| D — Human cleanliness | CLOSED | expected autonomous |

**Predicted: ADMISSIBLE** (if B stays contained) or **CONDITIONALLY ADMISSIBLE** (if B opens
due to cross-rig CI calls).

---

### G4 — Backend + frontend task

Expected characteristics: work spans two rigs (backend + frontend). Scope containment is
expected to open — the task requires writes to both. Whether this is captured as a cross-rig
call or as two separate convoys depends on how GasTown orchestrates multi-rig tasks.

**Expected topology:** split — either two separate convoys (one per rig, each with its own
bead_id) or one cross-rig convoy (single bead, mayor delegates to two polecats in different
rigs). The adapter must not merge two separate bead_ids into one convoy. If GasTown issues one
bead for a multi-rig task, scope containment (B) is expected to be OPEN by design.

| Dimension | Prediction | Rationale |
|-----------|-----------|-----------|
| A — Prompt fidelity | CLOSED | human task delivery expected |
| B — Scope containment | OPEN (backend convoy) or OPEN (cross-rig) | multi-rig work expected |
| C — Merge gate | CLOSED (backend) / OPEN (frontend) | frontend may lack merge gate |
| D — Human cleanliness | CLOSED | expected autonomous |

**Predicted: NOT ADMISSIBLE** for a single cross-rig convoy, unless GasTown emits separate
per-rig convoys (in which case each rig's convoy may be independently admissible).

**Falsification condition G4-F1:** if G4 produces a single admissible convoy covering both
rigs, the scope containment definition needs revision — the "authorized rig scope" for a
multi-rig task must be explicitly defined before the run.

---

### G5 — Subjective / creative task

Expected characteristics: task has no deterministic success criterion; prompt fidelity is
harder to verify (ambiguous task boundary); human may need to intervene or clarify.

**Expected topology:** degenerate or delegated — topology alone does not predict D. The
discriminating variable is whether the task requires human clarification mid-execution.

| Dimension | Prediction | Rationale |
|-----------|-----------|-----------|
| A — Prompt fidelity | CLOSED | prompt present, but task content may be ambiguous |
| B — Scope containment | CLOSED | creative tasks expected to stay in-rig |
| C — Merge gate | NOT_REQUIRED | no CI gate for subjective output |
| D — Human cleanliness | OPEN | human clarification during execution is plausible |

**Predicted: NOT ADMISSIBLE** if D opens. **ADMISSIBLE** if mayor runs autonomously to
completion without human correction.

**The gradient signal:** dimensions A and D are expected to be the discriminating variables at
G5. B and C are expected to be stable across G1–G5. This is the convoy-level analog of the
per-session prediction that `completion_evidence_gap` would be the gradient driver — the
correct analog is **D (human cleanliness)** as the dimension most likely to open at high
gradient.

---

## §6 Gradient invariant (convoy-level)

The following dimensions are predicted stable across G1–G5:

- **Dimension A (Prompt fidelity)** — human task delivery is structural to GasTown 1.1.0;
  expected CLOSED for all runs unless GasTown changes task delivery mechanism.
- **Dimension B (Scope containment)** — expected CLOSED for G1–G3; expected to open at G4
  (multi-rig) and remain stable thereafter.

Significant deviation constitutes falsification:

| ID | Invariant | Falsified by |
|----|-----------|-------------|
| C-F1 | A CLOSED for G1–G3 | A OPEN in G1, G2, or G3 |
| C-F2 | B CLOSED for G1–G3 | B OPEN in G1, G2, or G3 (if single-rig tasks) |
| C-F3 | D is gradient-sensitive | D CLOSED for all G1–G5 (no gradient detected) |
| C-F4 | C NOT_REQUIRED or CLOSED for G1–G2 | C OPEN in G1 or G2 (refinery patrol absent) |
| C-F5 | G4 opens B or splits convoy | G4 single-convoy fully admissible despite multi-rig |
| C-F6 | Topology shift G1→G2 detectable | *Observation only — G2 degenerate is informative, not a falsification* |

---

## §7 Ordering constraint definition

For Dimension C (NOT_REQUIRED status), the qualifying refinery patrol close must satisfy:

```
patrol_close_timestamp > max(
    last_successful_mayor_tool_call_timestamp,
    last_successful_refinery_tool_call_timestamp_for_any_work_session
)
```

The constraint is evaluated per rig: the post-work clean signal must come from the refinery
of the same rig where the work was committed. For G1: rig=boolean_sat, refinery run
da9ec55b, qualifying closes at 17:58:31 and 17:59:29, mayor last tool at 17:58:09. ✓

For G2+: if the mayor delegates work to a refinery session that itself makes tool calls (not
just patrol), the last refinery work tool call must also be before the qualifying patrol close.
The patrol session and the work session may be the same run_id (as in G1, where the refinery
both did initial patrol checking and later confirmed clean queue) or separate.

---

## §8 Open questions before G2

1. **Multi-session mayor:** G1's mayor had two separate session starts (aa602165 at 17:54:40
   and a second resume at 17:54:54 after the cold-start check). The adapter correctly handles
   this as one logical session (same session_id). Confirm this holds for longer G2 tasks where
   the mayor may run multiple separate claude-code sessions.

2. **Refinery work vs. refinery patrol:** In G1 the refinery's session (836f9617) was
   patrol-only — it found no work to do. In G2+ the refinery may actually merge branches. The
   convoy definition should include refinery work sessions (not just patrol sessions) as convoy
   members when they perform artifact-producing operations.

3. **Convoy boundary for concurrent tasks:** The G1 trace resolves this from evidence. At
   17:54:57 the mayor runs `bd create "Build Python SAT solver..."` → creates bead `hq-byl`.
   At 17:55:01 the mayor runs `bd update hq-byl --claim`. From that point, all Write/Edit
   tool calls are against the hq-byl worktree. There is one bead, one convoy, no ambiguity.

   The general rule: **one `bd create` → one bead_id → one convoy boundary.** If the mayor
   creates multiple beads in one run, each bead is a separate convoy. The adapter must split
   by `bead_id` (from `bd create`/`bd claim` events), not by `run_id` alone. In G1 this
   didn't trigger (single bead), but it is a real risk for G2+ where the mayor may dispatch
   multiple polecats in parallel. The concern in this section stands as written for G2+.

---

## §9 Signatures

Pre-registration author: Adi Sriram
No G2–G5 traces have been collected at time of this commit.
G1 analysis locked at: `corpus/component2/analysis_g1.md`
