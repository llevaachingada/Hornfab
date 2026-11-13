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

S3 cost/attempt terminology (never collapse these):

- **index rows** — JSONL lines in `search.ndjson` (one evaluation attempt/replay per line).
- **cache hit / replay** — `cached: true`; not a new attempt and not a new BEM call.
- **new attempt** — non-cached row. Includes valid, cheap refusal and failed attempts.
- **valid evaluation** — `ok: true`; reported separately for new and cached rows.
- **cheap pre-BEM refusal** — `invalid_geometry`, `invalid_envelope` or `mesh_too_large`;
  consumes an attempt, not a BEM call, and is not an acoustic observation.
- **solver/infrastructure failure** — `solve_failed` (real elapsed work retained).
- **pipeline/unknown failure** — `exception`/`metrics_failed` or an unclassified kind.
- **actual BEM call** — direct evidence is a positive `seconds.solve`; a recorded
  `solve_failed` with no positive time is counted as an *inferred* call. Never infer
  BEM calls from `ok` alone.
- **timing observation** — uncached BEM call with finite `seconds.solve`, the input to the
  bo-study-v1.1 cost extension `z = log(max(actual_BEM_seconds, 1e-3))`. The extension
  requires **>= 30** compatible observations; S3/M0 reports eligibility only and fits no
  cost model.
- **elapsed seconds** — `attempts_all_incl_failed_refused` always includes failed/refused
  work. When run `started_utc`/`finished_utc` parse, `wall_span` and
  `unaccounted_overhead` are reported (`cost_label: "wall_start_end"`); otherwise the
  label is `"accumulated_candidate_cost_no_wall_span"` and overhead is `null`.
- **compatibility** — task/objective/brief/family must match to rank J at all; grid,
  fidelity (`mode`), backend, target and software (`lib_shas`) must also match for pooled
  prospective inference. Differing search settings are an intentional treatment difference
  in `ab_compare`, not a compatibility failure.
- **replicate** — one run dir (resume segments/restarts inside it are one replicate).
  Two run dirs with the same CMA seed are duplicates, not independent evidence; a shared
  RNG seed is never proof of shared candidates.
- **descriptive historical** — observed-run summaries. Not an inference.
- **prospective paired** — only for a predeclared pairing. `d = A - B` (negative => A has
  lower J). Bootstrap CIs, sign counts and censoring are reported. Five pairs is a pilot,
  not a significance guarantee; power/sample-size planning uses the pilot paired SD and a
  declared practical target (not the historical max-minus-min range).

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

**Known limitation (outside the S3 files):** `convergence.py` still calls
`best_so_far_curve` with its default successful-eval-only cost basis, so its `wall_s`
excludes failed/refused work. S3's `seed_variance`/`ab_compare` use
`include_failed_seconds=True` and the `cost_ledger` reconciliation; `convergence.py` is not
an S3-owned file, so it is left unchanged rather than silently changing its historical axis.

## seed_variance.json (`tools/analysis/seed_variance.py`)

```json
{
  "tool": "seed_variance",
  "generated_utc": "...",
  "seed_rule": "legacy descriptive label only; not the decision",
  "inference_policy": {
    "descriptive_historical": "observed runs; no causal/prospective claim",
    "prospective": "requires --pair; d = A - B; bootstrap CI; censoring reported",
    "pairing": "predeclared only; matching RNG seeds is not proof",
    "pilot_warning": "five pairs is a pilot, not a significance guarantee"
  },
  "descriptive_historical": {"groups": {"<name>": {
    "runs": ["<path>"], "n_seeds": 3, "n_independent_replicates": 3,
    "seeds": [{"run_dir": "<path>", "cma_seed": 1030, "best_j": 12.3, "n_new_valid": 110,
               "evals_to_1pct": 55, "evals_to_5pct": null,
               "cost": {"index_rows": 151, "cache_hits": 1, "attempts_new": 150,
                        "valid_evaluations_new": 150, "cheap_refusals": 0,
                        "solver_failures": 0, "pipeline_failures": 0,
                        "unknown_failures": 0, "actual_bem_calls_observed": 150,
                        "actual_bem_calls_inferred": 150,
                        "actual_bem_seconds": 659.7, "timing_observations": 150,
                        "elapsed_seconds": {"attempts_all_incl_failed_refused": 959.1,
                                            "wall_span": 961.0,
                                            "unaccounted_overhead": 1.9},
                        "cost_label": "wall_start_end",
                        "cost_model_gate": {"min_timing_observations": 30,
                                            "n_timing_observations": 150,
                                            "eligible": true,
                                            "status": "eligible_not_fitted_in_m0"}},
               "replicate": {"n_resume_segments": 1, "n_restarts": 0}}],
    "median_best": 12.4, "spread_best": 2.0,             // descriptive max-min (unit J)
    "ci95_median_best": [11.8, 13.1],                    // bootstrap 95% CI, fixed seed 0
    "seed_distances_norm": {"<dirA>|<dirB>": 0.31},      // normalised best-design distance
    "ecdf_basis": "relative_to_group_best_descriptive",
    "ecdf_1pct": [[0, 0.0], [10, 0.33]],                 // legacy relative ECDF (descriptive)
    "ecdf_5pct": [[0, 0.0], [10, 0.67]],
    "compatibility": {"blocking": ["software_drift"], "compatible_for_inference": false},
    "replicates": {"n_independent_replicates": 3, "duplicate_seed_run_dirs": {}},
    "cost_totals": {"index_rows": 453, "attempts_new": 450, "actual_bem_calls_observed": 450},
    "cost_model": {"target": "z=log(max(actual_uncached_BEM_seconds,1e-3))",
                   "n_timing_observations": 450, "min_observations": 30,
                   "count_gate_passed": true, "compatibility_gate_passed": true,
                   "compatibility_blocking": [], "eligible": true,
                   "status": "eligible_not_fitted_in_m0"},
    "fixed_target": {                                    // only with --target-j
      "target_j": 20.0,
      "ecdf_evals": {"n_reached": 20, "n_censored": 5, "points": [[110, 0.04]]},
      "ert_evals": {"ert": 128.4, "n_success": 20, "n_censored": 5,
                    "ert_is_lower_bound": true},
      "ecdf_cost_s": {}, "ert_cost_s": {}
    }
  }}},
  "prospective": {
    "pairing_declared": true,
    "pairs": [{"pair": "p0", "a": "<dirA>", "b": "<dirB>", "shared_cma_seed": false,
               "final": {"difference": -2.0},
               "fixed_eval_budget": {"budget": 150, "difference": -2.0,
                                     "complete_pair": true},
               "fixed_cost_budget": {"budget_s": 900.0, "difference": -1.5,
                                     "complete_pair": true},
               "time_to_target": {"target_j": 20.0, "difference_evals": -12,
                                  "difference_cost_s": -40.0}}],
    "summaries": {
      "final_best": {"n_pairs": 5, "mean": -2.0, "median": -2.0,
                     "ci95_bootstrap_mean": [-2.6, -1.4],
                     "signs": {"a_better": 5, "b_better": 0, "ties": 0},
                     "decision": "a_better", "pilot": true},
      "fixed_eval_budget": {}, "fixed_cost_budget": {}, "preferred_basis": "fixed_eval_budget",
      "summary": {}                                      // preferred summary, repeated
    },
    "power": {"status": "ok", "pilot_sd": 0.38, "practical_delta": 0.5,
              "n_pairs_required": 5,
              "method": "normal approximation to a paired one-sample test"}
  },
  // compatibility aliases for the GUI/report_day (prospective only, [] without --pair):
  "groups": {},
  "verdicts": [{"a": "paired_runs", "b": "declared_pairs", "n_seeds": 5,
                "verdict": "a-beats-b", "decision": "a_better",
                "ci95_bootstrap_mean": [-2.6, -1.4], "pilot": true}]
}
```

`verdict` labels remain `a-beats-b | b-beats-a | indicative | no-verdict` for existing
GUI/report consumers, but are derived from the paired decision (`pilot_only` -> indicative,
CI spanning the practical threshold -> no-verdict). The historical median-vs-spread rule is
retained only as descriptive `seed_rule`/`legacy` context. Censored runs contribute at
least their last observed budget to ERT, so `ert_is_lower_bound` is true; the target ECDF
keeps censored runs in the denominator but never counts them as reached
(`ecdf_is_lower_bound: true`).

Hard refusal (exit code 2, not a warning): a group mixing **objective versions, briefs,
families or task config**, or a pair whose sides differ in those identities.

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
    "a": {"runs": ["<path>"], "n_runs": 1, "n_new_valid_max": 110,
          "cost": {"index_rows": 151, "cache_hits": 1, "attempts_new": 150,
                   "valid_evaluations_new": 150, "actual_bem_calls_observed": 150,
                   "cheap_refusals": 0, "solver_failures": 0,
                   "pipeline_failures": 0, "unknown_failures": 0},
          "replicates": {"n_independent_replicates": 1}},
    "b": {"runs": ["<path>"], "n_runs": 1, "n_new_valid_max": 108, "cost": {}, "replicates": {}}
  },
  "compatibility": {"blocking": [], "compatible_for_inference": true},
  "cost_totals": {"index_rows": 300, "attempts_new": 300, "timing_observations": 300},
  "cost_model": {"n_timing_observations": 300, "count_gate_passed": true,
                 "compatibility_gate_passed": true, "eligible": true,
                 "status": "eligible_not_fitted_in_m0"},
  "equal_budget": [{"n": 10, "best_a": 15.2, "best_b": 16.9,
                    "n_observed_a": 1, "n_observed_b": 1,
                    "n_censored_a": 0, "n_censored_b": 0}],
                   // median over runs at each matched new-valid-eval count; censoring shown
  "fixed_cost": {"budget_s": 900.0, "budget_basis": "declared",
                 "median_a": 12.4, "median_b": 13.1,
                 "n_observed_a": 1, "n_observed_b": 1,
                 "n_censored_a": 0, "n_censored_b": 0},
  "fixed_target": {"target_j": 20.0,
                   "a": {"ecdf_evals": {"n_reached": 4, "n_censored": 1,
                                        "ecdf_is_lower_bound": true},
                         "ecdf_cost_s": {}, "ert_evals": {"ert": 128.4},
                         "ert_cost_s": {}},
                   "b": {}},
  "final": {"median_a": 12.4, "median_b": 12.0, "spread_a": 0.7, "spread_b": 2.1},
  "verdict": {"verdict": "a-beats-b", "decision": "a_better",
              "rule_holds": true, "n_runs_per_side": 5,
              "ci95_bootstrap_mean": [-2.6, -1.4],
              "practical_delta": 1.0, "pilot": true,
              "note": "pilot-scale paired evidence"},
  "legacy_median_rule": {"rule_holds": true, "n_runs_per_side": 5,
                         "verdict": "a-beats-b",
                         "note": "historical descriptive label; not the decision"},
  "paired": {
    "pairing_declared": true,
    "pairs": [{"pair": "p0", "a": "<dirA>", "b": "<dirB>",
               "shared_cma_seed": false,
               "final": {"difference": -2.0},
               "fixed_eval_budget": {"budget": 150, "difference": -2.0,
                                     "complete_pair": true},
               "fixed_cost_budget": {"budget_s": 900.0, "difference": -1.5,
                                     "complete_pair": true}}],
    "summaries": {"final_best": {}, "fixed_eval_budget": {},
                  "fixed_cost_budget": {}, "preferred_basis": "fixed_eval_budget",
                  "summary": {}},
    "power": {"status": "ok", "n_pairs_required": 5}
  }
}
```

`verdict.decision` is `a_better | b_better | pilot_only | inconclusive |
insufficient_pairs | descriptive_only`; `verdict.verdict` keeps the legacy labels. Without
a predeclared `--pair`, `decision` is `descriptive_only` and no win is declared. Matching
CMA seeds alone never pairs runs. Fixed-cost and fixed-budget views report censored runs
separately. J is only comparable when both sides share objective version, brief and family
(hard error, exit 2).

## lane_parity.json (`tools/analysis/lane_parity.py`)

Pooled mode (`--pair GPU,CPU` repeated): `{mode: "pooled", pairs: [<single-pair payload>...], n_pairs, n_distinct_compared, n_within_0p2, within_hashes, threshold_db, min_designs, pass, gate, dedupe}`; a design_hash counts once across pairs (its best compared pair).


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

## surrogate_validation.json (`tools/analysis/surrogate_validation.py`)

S7 advisory surrogate check. Read-only over a rows JSONL (`row_id, design_hash, t, objective_version, x,
ok, j, metrics`); never solves, never changes a default. A refusal is a result: `status: "refused"` with
`reason` one of `insufficient_rows` (< 8 rows), `mixed_objective_versions`, `unsupported_objective_version`,
`missing_inputs`, plus `detail`. Only objective versions the legacy metric surrogate can actually score pass
(`surrogate/capability.py`, currently v1): v4+ is refused by design because a v4 J also needs tolerances,
target terms and measured throat impedance the surrogate cannot supply, and J is only comparable within one
objective version **and** brief/weights/tolerances — the row contract carries no such identity. Rows are
split chronologically into the latest `test_frac`; same-`design_hash` test rows seen in train are dropped and
the check is reported. Predictions are hypotheses, `measured: false`.

```json
{
  "tool": "surrogate_validation", "schema_version": 1, "input_key": "<sha256 of rows+pool+params>",
  "params": {"test_frac": 0.25, "k": 5, "topk": 5, "n_propose": 6},
  "advisory_only": true, "changes_defaults": false, "resumed": false, "stale_partial_replaced": false,
  "input": {"rows": "<path>", "pool": "<path|null>"},
  "status": "ok",                                        // or "refused" + reason/detail
  "objective_version": 1, "metric_names": ["bw_h_deg", "..."],
  "split": {"kind": "chronological",
            "checks": {"max_train_t": 29, "min_test_t": 30,
                       "no_future_rows_in_train": true, "same_geometry_removed_from_test": 1,
                       "duplicate_test_rows_removed": 0, "tie_rows_moved_to_train": 0,
                       "shared_design_hashes": 0},
            "train_ids": ["r0"], "test_ids": ["r39"]},
  "evaluation": {"n_train": 30, "n_test": 10, "n_ood_fallback": 0, "support_radius": 1.42,
                 "feasibility": {"brier": 0.09, "brier_baseline": 0.14,
                                 "reliability_bins": [{"bin": [0.0, 0.2], "n": 4,
                                                       "mean_pred": 0.1, "observed": 0.0}]},
                 "regression": {"status": "ok", "n_eval": 6,
                                "targets": {"j": {"mae": 0.31, "mae_baseline": 0.55,
                                                  "spearman": 0.82, "interval_95_coverage": 1.0,
                                                  "topk": 5, "topk_recall": 0.8, "regret": 0.04,
                                                  "direction": "minimize"}}}},
  "proposals": {"status": "ok",
                "proposals": [{"candidate_id": "c3", "role": "exploit", "predicted_j": 1.02,
                               "uncertainty": 0.11, "in_support": true,
                               "measured": false, "status": "hypothesis"}],
                "note": "predictions are hypotheses; validate with the normal evaluator (BEM) later"},
  "complete": true, "path": "<out>/surrogate_validation-<key16>.json"
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

## bo-study-v1.1 analysis artifacts

`parameter_study.json` is a descriptive, versioned report with `task_identity`,
`cohort`, `controls`, selected measured `designs`, `evidence`, and `limitations`.
Row-level held-out fits are diagnostics; recommendations and interaction rankings
remain suppressed when independent-group support or stability is unavailable.
`source_fidelity.json` carries per-design source and fidelity context, including
pairing and DI provenance; missing or unpaired evidence is explicit. Both are
read-only reports: the Analysis renderer does not initiate a solve.

`bo_sensitivity` is an offline diagnostic harness, not a validated optimization
result. It requires explicitly validated cohort and group inputs and independent
fit/proposal adapters; missing evidence returns unavailable and synthetic fixtures
do not establish a performance claim or pass the M2 gate.
