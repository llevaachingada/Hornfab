# Search-config keys (day 2026-11-12, group B)

> **Hand-maintained — deliberately NOT generated.** `docs/reference/PARAMETERS.md` is produced by
> `tools/gen_param_catalog.py` and covers design knobs only; these are the search/solve config keys
> written by hand. Fold this file into the generator when it learns to document search/brief keys,
> then delete this file and its `SEARCH_CONFIG_KEYS.md` pointer.

All keys are OPT-IN: absent key = the pre-day-B behaviour byte for byte (pinned by
`tests/test_search_invariance_defaults.py` at 78ed1f4). Every refusals message comes from
`hornlab_search/config.py`, so a YAML typo is never silent.

## `search.budget_counts` (B.4) and `search.max_attempts` (B.4)

- **Summary:** `budget_counts` selects what consumes the evaluation budget: `new` (default, today's
  semantics: every non-cached evaluation counts, refusals included) or `valid` (only VALID
  evaluations consume budget; the deterministic refusals - invalid_geometry / invalid_envelope /
  mesh_too_large - are free).
- **Detail:** With `budget_counts: valid`, `search.max_attempts` (a positive integer, default
  `4 x budget`) is the hard ceiling on new attempts so a box that refuses everything still stops.
  pycma's fitness-range stops (tolfun / tolfunhist / tolflatfitness) are suppressed in `valid`
  mode because a refusal is told as the flat penalty. Both counts land in `run.json`
  (`budget_counts`) and in the final summary line.
- **Validation:** `in ('new', 'valid')` / `max_attempts >= 1` (int, no bool, no float).
- **Example:**

```yaml
search:
  budget_counts: valid      # refusals do not consume budget
  max_attempts: 200         # optional; default = 4 x budget
```

## `brief gates.round_throat` (B.5)

- **Summary:** A brief `gates: {round_throat: true}` opts ANY single-entry objective version into
  the C4 round-throat refusal (the driven surface must round-match `2 x driver.exit_radius_mm`,
  refused before any solver call).
- **Detail:** v7 always applies the gate and needs no key. Absent key = today's behaviour for
  every existing brief. Other gate names are refused (`GATE_KEYS` in `hornlab_search/config.py`).
- **Example (brief YAML):**

```yaml
gates:
  round_throat: true
```

## `search.links` (B.2)

- **Summary:** Linked knobs: `{<knob>: {from, scale, offset, min, max}}` removes the linked knob
  from the CMA (or CMA-ME) dimension and computes it from its parent before meshing
  (`v = scale * parent + offset`, clipped to `[min, max]`; missing min/max default to the knob's
  own bound lo/hi).
- **Detail:** One level only (a parent that is itself linked - chains, and with them cycles - is
  a ConfigError); unknown knobs/parents are a ConfigError; the seed's own value for a linked knob
  is ignored with a warning; `search.ndjson` `params` carry the computed value; `run.json`
  records the resolved links. Not supported with a `generator:` block.
- **Example:**

```yaml
search:
  links:
    exponent: {from: s, scale: 6.0, offset: 1.0}    # exponent = 6 s + 1, clipped to its bounds
```

## `search.warm_start` (B.1)

- **Summary:** Data warm start: the CMA (or CMA-ME) mean starts at the best valid design among
  `from_runs` (same family, the same searched knob names, normalised into this config's box;
  out-of-box designs are clipped and counted), and `sigma0` becomes the median per-knob spread of
  the top-`k` best valid rows, clamped to `[0.05, sigma0]`.
- **Detail:** A source run of another objective version or brief is a ConfigError unless
  `allow_cross_brief: true`. `run.json` records a `warm_start` block (sources + `config_sha`,
  mean design hash/objective, sigma record, rows/clip counts). The solve hash formula is
  untouched. Paths resolve against the config's directory (then the repo root); the directory
  must exist at load.
- **Example:**

```yaml
search:
  warm_start:
    from_runs: [runs/osse_screen_2026-11-12]   # absolute or config-relative run dir(s)
    top_k: 10                   # rows feeding the sigma spread (default 10)
    sigma_from_spread: true     # default; sigma0 = clamp(median spread, 0.05, sigma0)
    allow_cross_brief: false    # default; true accepts other briefs/versions
```

## `hornlab-search narrow` (B.3)

- **Summary:** Writes a config copied from a finished run's `config.yaml` where ONLY the bound
  changes from the run's own wall analysis (top-decile fraction within `--wall-frac` of each
  bound, implemented in `search/pin_from_cma.py`), `search.seed` (+1) and `name` change, plus a
  header comment listing exactly what changed and why (reference format:
  `examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4_narrow.yaml`).
- **Detail:** Walled sides are never narrowed; `--widen` (owner opt-in) extends a walled side by
  10% of the span; knobs walled in >50% of all valid rows are printed as `PIN CANDIDATE` (consider
  `search: false` instead). The run dir is never modified.
- **Example:**

```
hornlab-search narrow --run runs/<run_id> --wall-frac 0.03 --out <name>_narrow.yaml
hornlab-search narrow --run runs/<run_id> --widen        # also extend the walled sides
```

## `search.infeasible_penalty: resample` (B.6)

- **Summary:** Third mode (besides `flat`/`graded`): a deterministic refusal is REPLACED by a
  fresh sample from the same CMA distribution (up to 10 tries per candidate) and never told to
  the ES; the refusal is still evaluated and logged, and with `budget_counts: valid` it is free.
- **Detail:** After the cap the last refusal is told with the usual penalty so a fully-refusing
  box terminates. Not supported with `search.algorithm: cma_me` (ribs 0.12 `scheduler.tell`
  needs one result per asked solution; ribS path cited in the PR).
- **Example:**

```yaml
search:
  infeasible_penalty: resample   # default 'flat' unchanged
```

## `search.surrogate` (B.7)

- **Summary:** `search.surrogate: lq` runs the plain-CMA search through pycma 4.5.0's
  `SurrogatePopulation` (fmin_lq_surr2-style lq-CMA-ES): a linear/quadratic regression over the
  true evaluations predicts most of a population's fitness, so a budget buys many more
  generations.
- **Detail:** The model is seeded from the run's own prior rows on a resume; `run.json` gains a
  `surrogate` block (mode, model_seeded, model_size, true_evaluations). Refused together with
  `search.restarts`, `search.pipeline_prefetch` and `search.algorithm: cma_me`.
- **Example:**

```yaml
search:
  surrogate: lq    # default: omitted = plain CMA
```

## `search.qd.maes` (B.8)

- **Summary:** Inside an existing `search.qd` block, `maes: {learning_rate, j_threshold}` turns
  the CMA-ME archive into a CMA-MAE soft archive: `GridArchive(learning_rate in [0.01, 0.1],
  threshold_min = -j_threshold)` (the archive maximises -J), emitter ranker `imp` and NO emitter
  bounds (candidates are clipped in `DesignSpace.denormalize`, like plain CMA).
- **Detail:** Absent `maes` = today's CMA-ME (learning_rate 1.0, threshold_min -inf, ranker
  `2imp`, emitter `bounds=` resampling). `run.json`'s `qd` block records `maes` when set.
- **Example:**

```yaml
search:
  algorithm: cma_me
  qd:
    descriptor_h: mean_bw_h_deg
    descriptor_v: mean_bw_v_deg
    bins_h: 8
    bins_v: 8
    maes:
      learning_rate: 0.05    # [0.01, 0.1]
      j_threshold: 1000.0    # the refusal-penalty J cap; archive threshold_min = -1000
```
