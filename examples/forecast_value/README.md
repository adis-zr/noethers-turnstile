# Meteorology — The Meet versus Forecast Value

Forecast-value confrontation between the latent authorization function `A(e)`
and the cost-loss decision rule, on a frost-protection domain. Spec is the
paper's `meteorology-v1` (`docs/...` — TBD when paper section lands).

## Layout

```
preregistration.md          §8 decision table, predictions frozen pre-run
worldgen.py                 §3 synthetic world DGP
domain.py                   §2 W, q, lattice, a(w), requirements
baselines.py                §4 cost-loss, DRO-over-fiber, naive-coarse
controls.py                 §7 calibration + null + equivalence + optimality
arm1_divergence.py          §5 expectation divergence sweep
arm2_conservation.py        §6 coarsening ladder + manufactured-permission witness
run_all.py                  driver: gate → controls → arm1 → arm2 → classify
figures/
results/                    CSV outputs and run metadata
```

## Reproducing

```
python3.10 examples/forecast_value/run_all.py
```

Outputs land in `results/` and the §8 classification is written to
`results/outcome.md` and echoed at the bottom of stdout.

## Outcome

The §8 verdict for this run is recorded in `results/outcome.md` once the
sweep completes. See that file (not this README) for the live result.

## Caveats

- All meteorological constants in this run are **placeholders**. Cite WSU /
  OSU cold-hardiness tables before using numerical values in any paper draft.
- The fiber heterogeneity is constructed. The claim defended is existence
  and structural characterization of divergence, not prevalence in operational
  forecasting.
- Cost-loss with its stated scalar `L_bar` is expected-cost-optimal by
  construction. The result is **divergence**, not "cost-loss errs". See
  `preregistration.md` §11 for the threats-to-validity framing.
