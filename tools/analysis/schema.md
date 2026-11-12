# Analysis-report JSON schemas (Group A, 2026-11-12)

Every tool in `tools/analysis/` writes `<name>.json` (machine-readable, shape below),
`<name>.md` (tables) and PNG charts into the `--out` folder. Never writes into `runs/`.
`null` marks "not computable from this data" (missing timestamps, no sklearn, <3 rows, ...).
All JSON is produced by `json.dump(..., allow_nan=False)` with non-finite floats mapped to
`null`. Every report carries a top-level `{"tool", "generated_utc", ...}` header.

Terminology (same as `search.ndjson` rows):

- **valid row** — `ok == true`.
- **new eval** — a non-`cached` row (cached rows are replays of prior solves, not new
  evaluations; they never advance the eval axis, they only extend the best-so-far curve
  if the replay is a valid better design — impossible by construction, so effectively ignored).
- **new valid eval** — `ok == true` and `cached == false`. This index is the X axis of every
  convergence-style plot.
- **normalised knob space** — per knob in the run's `bounds`, `(v - lo) / (hi - lo)`
  (`search: false` knobs have `lo == hi` and are excluded).
- **top decile** — the 10% of valid rows with the lowest J (per run), at least 3 rows
  (`max(3, ceil(n_valid / 10))`); `< 10` valid rows -> `top_decile: null`, tools degrade.

---

## convergence.json (`tools/analysis/convergence.py`)

```json
{
  "tool": "convergence",
  "generated_utc": "2026-11-12T18:00:00Z",
  "runs": [
    {
      "run_dir": "<path>", "brief": "<config name>", "family": "OSSE",
      "objective_version": 4, "mode": "screen",
      "n_rows": 150, "n_valid": 120, "n_cached": 10, "n_new_valid": 110,
      "refusals": {"invalid_geometry": 18, "mesh_too_large": 2},
      "final_best": 12.34,                      // min objective over valid rows (unit: J, dimensionless score)
      "curve": [                                // one point per new valid eval, in row order
        {"n": 1, "best": 22.59, "wall_s": 19.31}
      ],
      "evals_to_1pct": 55,                      // new valid evals until best-so-far <= 1.01 * final_best; null if never
      "evals_to_5pct": 21,
      "last20_improvement": true,               // best improved > 1% of final_best inside the last 20% of new valid evals
      "last20_improvement_pct": 6.2,
      "refusal_rate_by_kind":
        [{"w": [1, 50], "rate": 0.30, "kinds": {"invalid_geometry": 14, "mesh_too_large": 1}}]
                                                // windows of 50 NON-CACHED rows (last window may be shorter);
                                                // rate = refusals / window size (dimensionless fraction)
    }
  ]
}
```

Charts: `convergence_<id>.png` — best-so-far J vs new-valid-eval index (and vs cumulative
wall seconds on a second panel when `created_utc` exists).

## seed_variance.json (`tools/analysis/seed_variance.py`)

```json
{
  "tool": "seed_variance",
  "generated_utc": "...",
  "seed_rule": "A beats B only when medians differ by more than both spreads",
  "groups": {
    "<name>": {
      "runs": ["<path>"],
      "n_seeds": 3,
      "seeds": [{"run_dir": "<path>", "cma_seed": 1030, "best_j": 12.3, "n_new_valid": 110,
                 "evals_to_1pct": 55, "evals_to_5pct": null}],
      "median_best": 12.4, "spread_best": 2.0,           // max-min over seeds (unit J)
      "ci95_median_best": [11.8, 13.1],                  // bootstrap 95% CI, 2000 resamples, fixed seed 0
      "seed_distances_norm": {"<dirA>|<dirB>": 0.31},    // L2 distance of best designs in normalised knob space
      "ecdf_1pct": [[0, 0.0], [10, 0.33]],               // COCO-style ECDF of evals-to-target (fraction of seeds)
      "ecdf_5pct": [[0, 0.0], [10, 0.67]]
    }
  },
  "verdicts": [
    {"a": "g1", "b": "g2", "median_a": 12.4, "median_b": 13.9,
     "spread_a": 2.0, "spread_b": 1.1,
     "n_seeds": 2, "verdict": "indicative",              // "a-beats-b" | "b-beats-a" | "indicative" (rule holds, <5 seeds) | "no-verdict"
     "rule_holds": true}
  ]
}
```

Hard refusal (exit code 2, not a warning): a group mixing **objective versions, briefs or
families**, or a verdict over groups that differ in any of the three.

## sensitivity.json (`tools/analysis/sensitivity.py`)

```json
{
  "tool": "sensitivity", "generated_utc": "...",
  "run_dir": "<path>", "family": "OSSE", "objective_version": 4,
  "n_valid": 110, "top_decile_n": 11,
  "spearman": [{"key": "a_deg", "rho": -0.41, "rho_abs": 0.41, "n": 110}],
  "top_decile_shift": [{"key": "a_deg", "mean_all": 41.2, "mean_top": 38.7,
                        "shift_norm": -0.03}],           // shift_norm = (mean_top - mean_all) / (hi - lo), null without bounds
  "surrogate": {                                          // only with sklearn; null when unavailable/too few rows
    "available": true, "model": "RandomForestRegressor", "n_train": 88, "n_test": 22,
    "r2": 0.61,
    "importance": [{"key": "a_deg", "permutation_importance": 0.21, "std": 0.02}]
  }
}
```

Units: `rho` in [-1, 1]; `permutation_importance` is the mean J increase (unit J) when the
knob is permuted. Spearman runs on valid rows (optimizer samples - known to be biased;
that is why the surrogate importance is separate). No Sobol (SALib not installed).

## links.json (`tools/analysis/links.py`)

```json
{
  "tool": "links", "generated_utc": "...",
  "run_dir": "<path>",
  "top_decile_n": 11,
  "pairs": [{"a": "a_deg", "b": "n", "rho": -0.72,
             "fit": {"scale": 0.104, "offset": 1.88, "r2": 0.55}}],
             // fit: least squares "b_knob = scale * a_knob + offset" on TOP-DECILE rows (raw knob units)
  "cma_directions": [{"rank": 1, "eigenvalue": 0.42, "fraction": 0.61,
                      "keys": ["a_deg", "a0_deg", "n"],
                      "loadings": {"a_deg": 0.57, "a0_deg": -0.55, "n": -0.43}}],
                      // eigenpairs where 2-3 knobs carry >= 0.85 of the abs-loadings norm
                      // (one dominant direction; from run.json cma_covariance / cma/covariance.json)
  "proposed_links": [{"knob_b": "n", "knob_a": "a_deg", "scale": 0.104, "offset": 1.88,
                      "r2": 0.55, "source": "rho_top_decile"}]
                      // feeds Group B's `links:` config (only |rho| >= 0.6 pairs get fits)
}
```

## walls.json (`tools/analysis/walls.py`)

```json
{
  "tool": "walls", "generated_utc": "...",
  "run_dir": "<path>", "top_decile_n": 11,
  "walls": [{"key": "L_mm", "lo": 140.0, "hi": 420.0, "frac_lo": 0.18, "frac_hi": 0.55,
             "wall_hi": true, "wall_lo": false}],
             // fraction of TOP-DECILE rows within 3% of the bound width of lo / hi
  "proposal": [{"key": "L_mm", "action": "widen_hi", "new_lo": 156.0, "new_hi": 462.0,
                "reason": "55% of top-decile within 3% of hi; top-decile range padded 5%"}],
                // action: narrow_<lo|hi> (clamp to top-decile span padded 5%) or
                // widen_hi / widen_lo (bound +10%, candidate only; physical safety is the caller's gate)
  "note": "proposals are inputs for Group B 'narrow', not automatic config changes"
}
```

## ab_compare.json (`tools/analysis/ab_compare.py`)

```json
{
  "tool": "ab_compare", "generated_utc": "...",
  "label_a": "narrow", "label_b": "control",
  "sides": {
    "a": {"runs": ["<path>"], "n_runs": 1, "n_new_valid_max": 110},
    "b": {"runs": ["<path>"], "n_runs": 1, "n_new_valid_max": 108}
  },
  "equal_budget": [{"n": 10, "best_a": 15.2, "best_b": 16.9},
                   {"n": 20, "best_a": 12.9, "best_b": 12.4}]
                   // per group MEDIAN over runs of best-so-far J at each matched new-valid-eval count
  "final": {"median_a": 12.4, "median_b": 12.0, "spread_a": 0.7, "spread_b": 2.1},
  "verdict": {"rule_holds": true, "n_runs_per_side": 1, "verdict": "indicative"}
}
```

Same verdict rule and >=5-seeds requirement as `seed_variance` (fewer runs ->
`"indicative"`, <3 -> `"no-verdict"`).

## lane_parity.json (`tools/analysis/lane_parity.py`)

```json
{
  "tool": "lane_parity", "generated_utc": "...",
  "gpu_dir": "<path>", "cpu_dir": "<path>",
  "designs": [{"design_hash": "8443a576",
               "compared": true, "max_abs_dspl_db": 0.03,   // max |dSPL| over freqs&angles, unit dB
               "d_j": 0.5,                                   // |J_gpu - J_cpu| from the runs' rows (null if no J)
               "source": "designs/<hash>/response.npz",
               "note": ""} | {"compared": false, "note": "response.npz missing / shape mismatch"}],
  "n_compared": 3, "n_within_0p2": 3,
  "threshold_db": 0.2, "min_designs": 3,
  "pass": true,                                            // CP-7b: >= 3 designs within 0.2 dB
  "gate": "CP-7b"
}
```

## term_balance.json (`tools/analysis/term_balance.py`)

```json
{
  "tool": "term_balance", "generated_utc": "...",
  "brief": "native__ath_core_v4", "objective_version": 4, "family": "OSSE", "n_valid": 110,
  "shares": {"cov": {"median": 0.42, "mean": 0.46}, "rip": {"median": 0.01, "mean": 0.02}},
            // share of J = weight * term / total per valid row, median/mean across rows, unit fraction
  "top_decile_raw": {"cov": {"median": 9.1, "p10": 4.0, "p90": 19.2}},
            // raw-unit term value of top-decile designs (term * tolerance for v4+; term / weight
            // for v1-v3 where the stored term is already weighted); no unit names are invented
  "weights": {"cov": 1.0, "rip": 1.0},                     // config weights actually used
  "tolerances": {"cov": 100.0, "rip": 3.0}                 // from the run's objective block (v4+); null for v1-v3
}
```

## fidelity.json (`tools/analysis/fidelity.py`)

```json
{
  "tool": "fidelity", "generated_utc": "...",
  "run_dir": "<path>", "brief": "native__ath_core_v4", "objective_version": 4,
  "n_pairs": 12,
  "pairs": [{"design_hash": "8443a576", "j_screen": 12.3, "j_verify": 15.0,
             "bias_pct": 21.9}],                           // (J_verify - J_screen) / J_screen * 100
  "bias_median_pct": 25.0,
  "spearman_all": 0.55,                                    // J_screen vs J_verify over all paired designs
  "spearman_top5": 0.30                                    // within-run rank agreement restricted to the screen top 5
}
```

## report_day.json / REPORT.md (`tools/analysis/report_day.py`)

```json
{
  "tool": "report_day", "generated_utc": "...", "spec": "<path to yaml>",
  "sections": [{"id": "g1", "tool": "seed_variance", "status": "ok|skipped|error",
                "detail": "written to <sub-out dir>", "error": null}]
                // one section per spec entry; every tool above runs from the spec,
                // REPORT.md links each section's JSON/MD/PNGs
}
```

Spec YAML (keys, not values):

```yaml
convergence:   [{id, run}]
seed_groups:   [{id, seeds: [run, ...]}]        # >= 5 seeds for a verdict
sensitivity:   [{id, run}]
links:         [{id, run}]
walls:         [{id, run}]
ab_compare:    [{id, a: [run, ...], b: [run, ...], label_a, label_b}]
lane_parity:   [{id, gpu, cpu}]
term_balance:  [{id, run}]
fidelity:      [{id, run}]
runs_root:     optional base directory prepended to relative run paths
```
