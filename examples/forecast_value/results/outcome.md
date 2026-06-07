# Outcome — §8 verdict

**Verdict:** `strong`

**Reason:** all gates and controls passed

## Details

```json
{
  "calibration_mad": 0.019312384805212014,
  "null_failures": 0,
  "dro_failures": 0,
  "arm1_summary": {
    "n_rows": 224,
    "n_divergences": 100,
    "divergence_rate": 0.44642857142857145,
    "n_bins_with_Ae_variation_at_fixed_p_hat": 4,
    "n_bins_with_cl_variation_at_fixed_p_hat": 0,
    "n_bins_total": 56,
    "preregistered_check_arm1_div_exists": true,
    "preregistered_check_boundary_tracks_heterogeneity": true,
    "csv_path": "/Users/adis/Workspace/noethers-turnstile/examples/forecast_value/results/arm1_divergence.csv"
  },
  "arm2_summary": {
    "n_evidence_states": 56,
    "Ae_monotone_along_L0_to_L3": "56/56",
    "manufactured_permission_witness_fires_at_L3": "56/56",
    "cost_loss_strengthens_or_holds_L0_to_L3": "56/56",
    "DRO_matches_Ae_at_L0": "56/56",
    "honest_compiler_equals_naive_at_L3": "0/56",
    "preregistered_check_1_Ae_conserved": true,
    "preregistered_check_2_manufactured_witness_fires": true,
    "preregistered_check_3_cost_loss_no_flag": true,
    "preregistered_check_4_DRO_matches_Ae_at_L0": true,
    "csv_path": "/Users/adis/Workspace/noethers-turnstile/examples/forecast_value/results/arm2_conservation.csv"
  }
}
```

## §8 mapping

| Outcome | Arm 1 | Arm 2 | Verdict |
|---|---|---|---|
| Strong  | divergence tracks heterogeneity | manufactured permission, A(e) conserved | flagship |
| Partial | divergence exists               | no manufactured-permission witness      | supporting |
| Scope   | no divergence                    | A(e) conserved trivially                | stated limit |
| Null    | no divergence                    | no asymmetry                            | repo example only |
| Bug     | null control fails OR A(e) non-monotone under admissible coarsening | — | halt, fix before any paper mention |
