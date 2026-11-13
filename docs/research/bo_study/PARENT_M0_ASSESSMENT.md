# Parent M0 critical assessment (external reviews, resolved brief, legacy surrogate)

Date: 2026-11-12. Parent orchestrator. Read-only; no solve, no data mutation. This file records the
parent's own verification, not worker evidence. Worker claims are reconciled separately.

## 1. Source and state verified locally

| Item | Verified value |
|---|---|
| Lane worktrees created from | `origin/main` = `5f7c116` (merge PR #48, day/AN-analysis) |
| Docs baseline | DOCS worktree HEAD `4910c64` (docs branch, plan docs uncommitted) |
| Code delta HEAD..origin/main | only `tools/analysis/specs/day_2026-11-12.yaml` (+38/−50); inspected design/objective/search/surrogate/GUI paths unchanged |
| Live old queue | `C:\Users\hunte\Hrns\hornlab-search` at `79edc8d` branch `day/2026-11-12-queue`; untracked `cache_cpu/`, `dataset_cpu/` |
| Data present (read-only) | dataset 25,212 files / 4,277 MB; dataset_cpu 244 / 49 MB; cache/solve 51,214 / 6,456 MB; cache_cpu/solve 456 / 82 MB; runs 196,871 / 19,213 MB |
| Interpreter | `.venv` Python 3.12.10, torch 2.14.1+cpu; **botorch and gpytorch absent** |
| `git worktree list` | 24 pre-existing worktrees; `gui-int` dirty 13, `T` dirty 2, `L1` dirty 1, DOCS dirty 8 — preserved, untouched |

The hardening doc's line 22 says local `origin/main` was `091c6ed`; that is stale. `origin/main` is
now `5f7c116`. The doc's substantive claim (no code differences over the inspected paths) still
holds against `4910c64`, but the SHA must not be quoted as current.

## 2. Resolved candidate task — parent-observed freeze evidence

Command (pinned interpreter, `sys.path` forced to the DOCS checkout, no mesh/solve):

```
load_config(examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml)
DesignSpace.from_config(cfg)
```

Resolved values (not inline YAML):

- objective **v4**; tolerances `cov 2.0, rip 1.0, di 0.4, dislope 9.0, flat 1.5, load 0.3, distd 2.0, diag 2.0`
- `cov_narrow_ratio: 2.0`; `cov_below_f0: mask` (absent → default); `diag_reference: round`
- target: 50°/50°, band **300–8000 Hz**, `f0_hz 1280.0`, `di_slope_target 0.0`, `z_min 0.0`,
  frequency weights `[2500, 5500, ×2]`
- weights: `cov 1.0, rip 1.0, di 0.3, dislope 0.5, flat 0.5, load 0.0, distd 0.5, diag 0.5`
- feasibility record: K-law required mouth 396.875 mm, held coverage 30.53° at 650 mm envelope,
  `screen_freqs_below_f0 4/12`, `verify_freqs_below_f0 11/25`
- search keys (alphabetical, `d=14`): `L_mm, a_deg, k, morph_corner_mm, morph_exponent,
  morph_fixed, morph_height_mm, morph_rate, morph_width_mm, n, q, s, s1, s2`
- fixed/non-searched: `r0_mm 25.4, a0_deg 1.2, exponent 2.0, aspect_ratio 1.0,
  morph_target 1, morph_allow_shrinkage 1`
- seed design hash: `b930c6c35b14`
- resolved bounds: `L_mm 104–520`, `a_deg 10–80`, `n 1–10`, `s 0–1.5`, `q 0.9–1.0`, `k 0.3–5.0`,
  `s1 1–1.3`, `s2 0.015–0.035`, `morph_width/height 238.2–456.55`, `morph_corner 0–80`,
  `morph_exponent 2–10`, `morph_rate 0.5–8.0`, `morph_fixed 0–0.6`

Findings to carry into the freeze:

1. The inline YAML target block (`500–5500 Hz`, `coverage 50`) is **overridden** by the brief. Any
   analysis that reads the YAML target directly is wrong. Confirmed by the loader.
2. The YAML comment says campaign `morph_fixed 0–0.1`, but the resolved search bound is **0–0.6**.
   The brief does not override bounds. This is a provenance/comment mismatch in the live config,
   not a parent-authorized change. Record it; do not silently tighten.
3. `morph_exponent` is searched (2–10) but inactive for `morph_target=1`. The no-op claim still
   requires the static source branch test plus sampled final-geometry invariance (target 3 active).
4. `d=14` includes one statically inactive knob. After the audited `active-projection-v1`, `d=13`.
   Do not remove any other knob; `s1/s2` are conditionally inactive only when either is zero.

## 3. Critical assessment of the two external reviews (as synthesized in the hardening decision)

The two Terra reviews are not stored as separate files; their accepted findings are the table in
`HORN_OPTIMIZATION_HARDENING_2026-11-12.md` §1. The parent re-checked each locally:

| Review claim | Parent verdict | Evidence / caveat |
|---|---|---|
| Searched knob inactive (`morph_exponent` at target 1) | **Accept, conditional** | Config pins `morph_target=1`, searches `morph_exponent`; mesher reads exponent only for target 3. No-op needs the static branch test + geometry sampling; a flat local response is not global proof. |
| Parameter hashes ≠ physical uniqueness | **Accept** | `Design.hash` hashes family + canonical params; ignored/construction-equivalent fields can move the hash without moving the surface. Final-surface equivalence must be separate, and cache keys must not change. |
| Resolved brief matters more than inline YAML | **Accept, verified** | Loader produced 300–8000/f0 1280/narrow 2; inline 500–5500 is stale. |
| Pareto helper lost the narrow-side preference | **Accept, verified in source** | `V8Params.for_class("A")` calls `from_block` without `cov_narrow_ratio` → default 1.0, while the brief requires 2.0. Forbidden shortcut for v4 raw terms; v8 remains unregistered. |
| First task is directivity, not loading/efficiency | **Accept** | Brief weight `load 0.0`; f11 disclosure 3,957 Hz; 2-inch uniform piston. No efficiency/max-SPL/distortion claims. |
| Beamwidth alone hides lobes/saturation | **Accept** | Outermost-crossing + 180° no-crossing conventions; multilobe counts exist in `metrics/compute.py`. Report crossings, DI source/variation, polars, missingness. |
| Tree finite differences are not physical derivatives | **Accept** | ExtraTrees is discontinuous; treat 0.025/0.05/0.10 normalized steps as finite model changes with support/group stability, not derivatives. |
| 14-D Sobol pool is not proven useful | **Accept** | 4096 pool is an engineering choice; diagnostics vs space-filling/CMA required. Proposals are cheap-check-passed, mesh/acoustic eligibility unknown. |
| New orchestration was too early | **Accept** | M1 uses existing analysis/report/run/verify; no DB/job framework prerequisite. |
| Default cache enforcement is disruptive | **Accept** | S2 audit-only; no producer enforcement in M0–M2; legacy reuse stays unknown, not blanket-missed. |

Parent disagreements/risks added:

- **Review synthesis is not a council vote.** The hardening doc says this explicitly; treat the
  two reviews as leads plus parent/source verification, not as independently reproduced evidence.
- **"No code differences" must be re-established per phase.** Main advanced to `5f7c116`; only one
  spec file differs today, but that can change. Freeze against the actual lane worktree, not a
  quoted SHA from the doc.
- **Bound/comment drift (`morph_fixed 0–0.6`)** is an unlisted finding. It does not invalidate the
  review but must appear in the control ledger and cohort comparability rules.
- **Cohort eligibility is still unproven.** 23,941 ok records overall does not mean an ATH-v4
  compatible cohort exists. The DATA lane must return per-identity counts or
  `insufficient_evidence`; the parent will not assume ATH eligibility.

## 4. Legacy surrogate capability audit (parent, source-level)

Source inspected read-only on `origin/main` code:

- `hornlab_search/surrogate/predict.py`: `metric_set` constructs `MetricSet(..., z_throat_real=None)`;
  `objective` calls `hornlab_search.objective.scalar.objective` (v1 semantics) on predicted curves;
  `evaluator` marks surrogate mesh/solve hashes and warns to re-solve.
- `hornlab_search/surrogate/train.py`: `_targets` recomputes held-out true J with the same
  `objective` (v1) from exported metric arrays.
- No v4 tolerance normalization, no `distd`/`diag` terms, no v4 asymmetric coverage, no gates, no
  throat impedance. `config_mismatch` checks family/keys/bounds/frequency grid, not objective
  version/input completeness.

Verdict: the legacy surrogate is **v1-scoring only** and must not be compared with a v4 BoTorch
model or used to rank v4 J. M0 requires an explicit supported-version/input capability declaration
and either (a) a version-aware pure scorer adapter shared with R0, or (b) refusal for v4+. No
predicted impedance, no fabricated metrics. This is a source-level scoring-compatibility gap, not
measured acoustic loss.

## 5. Refusal-handoff claim check (critical)

The reviewed plan's §6.10 integrates the owner refusal handoff. Parent findings:

- It reports 17 existing resample/budget tests passed and a spy observation on an all-refusing
  test; that is a **local reproduction claim**, not proof of general refusal correctness.
- The census figures (28,575 records: 23,941 ok / 4,634 failed; CPU 237: 221 ok / 16 failed) are a
  prior snapshot and not an atomic writer snapshot. They must not be quoted as current without a
  fresh coherent read. The v8 re-score's 23,833 scored rows is a different scope; not a
  contradiction, but never mix the two denominators.
- Failure categories must stay separate (invalid geometry, envelope, mesh budget, solve failure,
  generic exception, infrastructure). None become `J=1000` acoustic observations.
- "Zero recorded J≥1000 cells" was observed for one archived run (`fbab4f`) only; it does not
  generalize.
- F0 (all-refusing sampler handling) is a separate additive correctness option with its own
  ownership; it is not part of B3 and must not flip defaults.

## 6. Parent decisions before worker reconciliation

1. Use `5f7c116`-based lane worktrees; re-verify HEADs at freeze.
2. Do not authorize any real solve, dataset merge/apply, cache behavior change, v8 registration, or
   default change.
3. M1 report must state the resolved brief (300–8000/f0 1280/ratio 2) and must not use the inline
   500–5500 target.
4. ATH eligibility is open until the DATA lane returns counts. `insufficient_evidence` is a valid
   M0 outcome; it does not authorize weak pooling or a different task without parent review.
5. No M1/M2/M3 dispatch until the user resumes: the owner requested a pause after the three M0
   workers stop.
