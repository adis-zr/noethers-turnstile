# Preregistration — The Meet versus Forecast Value

**Domain:** Frost protection for a perennial crop. Synthetic worlds drawn from
a climatology + dwell-time + phenology model. Calibrated probabilistic forecast
of `Pr(T_min < tau)`.

**Frozen before run.** This document fixes the decision rule, the controls,
the preregistered predictions, and the outcome classification *before* any
sweep is executed. The classification table in §8 of the spec is the only
mapping from observed results to verdicts; no post-hoc category may be added.

**Status of meteorological constants.** All `tau`, damage-curve parameters,
`C`, and `L_bar` values in this run are PLACEHOLDERS pending citation against
published cold-hardiness tables (WSU/OSU grapevine/stone-fruit critical
temperature charts). Numeric values reported here are not publishable until
constants are sourced and verified.

---

## Decision rule (§8 of spec, verbatim)

| Outcome | Arm 1 | Arm 2 | Verdict |
|---|---|---|---|
| Strong  | divergence tracks heterogeneity | manufactured permission, A(e) conserved | flagship |
| Partial | divergence exists               | no manufactured-permission witness      | supporting |
| Scope   | no divergence                    | A(e) conserved trivially                | stated limit |
| Null    | no divergence                    | no asymmetry                            | repo example only |
| Bug     | null control fails OR A(e) non-monotone under admissible coarsening | — | halt, fix before any paper mention |

## Preregistered predictions

### Calibration gate (§7.1)
The reliability diagram of `p_hat` against realized `1[T_min < tau]` lies on the
diagonal within mean-absolute-deviation `<= 0.05` across non-empty bins.
**Fail → experiment void.**

### Homogeneous-loss null (§7.2)
With `L_real` collapsed to a single scalar (degenerate `D`, `V`), `A(e)` and
cost-loss must coincide at every swept `(p_hat, C/L_bar)`. **Disagreement at
any cell → framework bug.** This is the existence-of-bug check, not a
performance metric.

### DRO-equivalence check (§7.3)
At L0, `A(e)` should coincide with DRO whose ambiguity set is exactly `F(e)`.
**Disagreement at any cell → framework bug or definitional drift.**

### Arm 1 — Expectation divergence (§5)
At fixed `p_hat = p*` chosen to sit just above the cost-loss threshold for
the nominal `C/L_bar`, increasing fiber loss-heterogeneity (widening the
`(D, V)` distribution within `F(e)`) drives `A(e)` strictly below cost-loss
on the permission lattice. The divergence region in `(C/L_bar, heterogeneity)`
space is **non-empty** and its boundary is governed by **heterogeneity**,
not by `p_hat`. Held-fixed `p_hat` with rising heterogeneity must move
`A(e)` down while leaving cost-loss unchanged.

### Arm 2 — Conservation under coarsening (§6.3)
Along the ladder `L0 → L1 → L2 → L3`:

1. `A(e)` is **monotonically non-increasing** in permission rank.
2. At the inadmissible step `L2 → L3` (drop duration + vulnerability handles),
   the **naive-coarse compiler** emits a permission strictly stronger than
   the honest `A(e)` for at least one swept evidence state — the
   manufactured-permission witness.
3. **Cost-loss strengthens or holds** at L3 with no admissibility flag.
4. **DRO** matches `A(e)` at L0 (worst-case over the forced fiber) but
   provides no conservation guarantee across `L0 → L3`.

## Classification rule

After the run, compute:

- `arm1_divergence_exists` ← any cell with `cost_loss_perm > A_perm` in the
  Arm 1 sweep (with calibration gate passed and homogeneous-null passed).
- `arm1_tracks_heterogeneity` ← the per-`p_hat` divergence boundary monotone
  in heterogeneity at fixed `p_hat`.
- `arm2_A_conserved` ← `A(e)` non-increasing along `L0 → L3` at every swept
  evidence state.
- `arm2_witness_fires` ← at the L3 step, the naive-coarse compiler emits
  a permission strictly greater than honest `A(e)` for some swept state.
- `controls_passed` ← calibration + homogeneous null + DRO-equivalence all
  green.

Outcome:

| `controls_passed` | `arm1_div` | `arm1_het` | `arm2_cons` | `arm2_witness` | verdict |
|---|---|---|---|---|---|
| F | * | * | * | * | **bug** |
| T | * | * | F | * | **bug** |
| T | T | T | T | T | **strong** |
| T | T | T | T | F | **partial** |
| T | T | F | T | T | **partial** |
| T | F | * | T | T | **scope** |
| T | F | * | T | F | **null** |

No other categorization permitted.

## Frozen prior to run

- spec version: `meteorology-v1` (paper-spec text, §0–§11)
- code revision: see `git rev-parse HEAD` recorded in `results/run_metadata.json`
- run timestamp: see `results/run_metadata.json`
