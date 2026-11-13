# Parent M0 contract and lane brief (bo-study-v1.1)

Status: **provisional freeze**, 2026-11-12. Parent orchestrator owns this file. Workers must not
edit it. After M0 evidence returns the parent issues `PARENT_M0_FREEZE.md` with the resolved
physical/scoring/encoding APIs; workers then align to the freeze.

## 1. Authoritative documents

Read, in this order:

1. `C:\Users\hunte\Hrns\oc-wt\DOCS\docs\research\HORN_OPTIMIZATION_HARDENING_2026-11-12.md`
2. `C:\Users\hunte\Hrns\oc-wt\DOCS\docs\research\BAYESIAN_STUDY_ORCHESTRATOR_SPEC_2026-11-12.md`
   (protocol **bo-study-v1.1**)
3. `C:\Users\hunte\Hrns\oc-wt\DOCS\docs\research\DATA_GA_IMPLEMENTATION_PROMPTS_2026-11-12.md`
   — your assigned slice block plus S0/R0/B2/S3 as applicable
4. `C:\Users\hunte\Hrns\oc-wt\DOCS\AGENTS.md`, `TOOLCHAIN.md`, `docs/plan/01_CONTRACTS.md`
5. Existing code in your worktree: `hornlab_search/**`, `tools/analysis/**`, `tests/**`

If any instruction conflicts, the hardening decision + bo-study-v1.1 win over the older council
plan; the parent resolves remaining conflicts.

## 2. Hard environment and safety rules

| Item | Value |
|---|---|
| Canonical source at dispatch | `origin/main` = `5f7c116` (all three lane worktrees created from it) |
| Live old queue checkout | `C:\Users\hunte\Hrns\hornlab-search` — **READ-ONLY**, never checkout/reset/commit there |
| Live data (read-only) | `hornlab-search\dataset`, `dataset_cpu`, `cache\solve`, `cache_cpu\solve`, `runs` |
| Python | `C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe` (3.12.10, torch 2.14.1+cpu; BoTorch/GPyTorch ABSENT) |
| Lane worktrees | data: `C:\Users\hunte\Hrns\oc-wt\BO-M0-DATA`; encoding: `...\BO-M0-B2`; cost: `...\BO-M0-S3` |
| Coordination dir | `C:\Users\hunte\Hrns\oc-wt\bo-study` (parent artifacts, shared freeze docs) |

Non-negotiable:

- **No BEM/GPU solve, no worker-host cleanup, no queue edit, no dataset/cache/runs mutation.**
  Analysis is read-only against immutable prefixes.
- **No production config/default/objective-registration change.** v8 stays unregistered. Never
  rank J across objective versions.
- **No new horn parameter/key/unit.** Reuse `design/params/`, `families.KeySpec`, generator
  registry, mesher schema, `config.py` brief resolution.
- **Do not weaken/skip tests** or widen assertions. A failing test is information.
- Only edit files in your owned paths. Everything else is read-only. Scratch outputs go under
  your worktree `scratch/bo_m0/<lane>/` (never inside live data).
- Do not install packages into the live venv. S3/data/encoding need stdlib+numpy+existing deps.
  BoTorch is M2 and gets a separate isolated environment.
- No commit/push/merge unless the parent explicitly asks. Return a diff + evidence.

## 3. Provisional frozen contracts (parent-owned)

### 3.1 Three identities — never collapse them

1. **Physical solve identity** (immutable): geometry hash + design params + family + mesh spec and
   mesh hash + source/excitation + boundary/mounting + frequency grid + observation grid +
   backend + solver/dependency pins + raw response/artifact hashes + producer. Preserve original
   uncertainty/completeness. Raw responses are immutable.
2. **Derived metric identity** (target-dependent): physical response identity + metric code
   version + coverage/band/frequency weights + normalization/detrending + required inputs
   (target, masks, angles, impedance where a metric requires it). Stored metric values are not
   universally scoring-independent.
3. **Score identity**: metric identity + exact objective version/weights/tolerances/gates/brief
   identity/code version. One physical solve can support several metric/score tables. A new score
   never overwrites an older one.

Every emitted analysis table must carry all three IDs and a completeness status:
`exact-complete | partial/unsupported | additional-data-or-solve-required`, with per-row reasons.
A missing gate/input is never a pass; incomplete scores never rank as equivalents beside complete
scores.

### 3.2 Candidate task (not yet eligibility-proven)

`examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml`, resolved through the normal
loader and `brief_file: examples/briefs/campaign_2026-10-26_v4/native_ath_core_2in_v4.yaml`.

Parent-observed resolved brief values (verify through the loader, do not trust the inline YAML):

- band **300–8000 Hz**, target coverage 50° H/V, f0 **1280 Hz**
- `cov_narrow_ratio: 2.0`, `cov_below_f0` per brief/objective resolution, `diag_reference` per
  `objective/scalar_v4.py`; brief weights `cov 1.0, rip 1.0, di 0.3, dislope 0.5, flat 0.5,
  load 0.0, distd 0.5, diag 0.5`; tolerances as in the brief; objective version **4**
- inline config target `500–5500 Hz` and `morph_fixed` bounds are **stale**, overridden by the
  brief. Never model against inline YAML values.
- source/model caveat: 2-inch uniform piston, f11 ≈ 3957 Hz; results above it are geometry
  comparisons under that excitation. Loading weight is 0: this task does not optimize loading,
  efficiency, distortion or max SPL.

ATH is a **candidate only**. M0 must demonstrate compatible cohort completeness or return
`insufficient_evidence`; the parent then selects an evidenced task without weakening compatibility.

### 3.3 Advisory active projection

- Version: `active-projection-v1` (advisory, reversible, never a production config change).
- May remove only statically proven **and geometry-tested no-op** controls, reconstructing them at
  their recorded reference value when decoding. `morph_exponent` is inactive for this task because
  `morph_target` is pinned to 1 (static source + geometry test required; a flat local response is
  not proof). Never remove a merely quiet or conditionally active knob.
- Encoding order is the existing **alphabetical** `space.keys()`; `d` = retained length after the
  audited projection. Preserve bound/log transforms and reconstruct the **full** alphabetical
  vector before `space.denormalize`. Fixed/no-op reference keys stay fixed. Reject missing keys,
  clipping of historical out-of-domain observations, unsupported discrete spaces, and
  hash-mismatched round-trips.
- Generated-space support only when full knob provenance + hash round-trip are proven.

### 3.4 Raw acoustic metric policy (B2/S4/B7 consume; R0 owns the canonical adapter)

- Use the canonical v4 raw helpers; `V8Params.for_class("A")` is **forbidden** as a shortcut
  because it silently loses the resolved brief's narrow ratio 2.
- Build raw params from the resolved brief: `cov_narrow_ratio`, `cov_below_f0`,
  `diag_reference`; use declared helper tolerances only to satisfy the raw API. Freeze band and
  frequency weights, detrended ripple branch, and metric hash.
- Ripple must use the **response-based detrended branch** (`_used_resp` true, finite nonempty
  scored support). If absent, exclude or return a distinctly named legacy metric spec; never pool
  both under one ripple label.
- Freeze complete intended per-plane/ripple frequency masks and valid weight vectors. Every
  compared design must supply the same declared bins, or an identical predeclared restricted mask
  with distinct identity + partial status. No silent per-design finite filtering, invalid-weight
  fallback, or mixed ripple-definition fallback. Missing impedance/throat/balloon/MEH inputs are
  unavailable, never fabricated.
- No v8 registration.

### 3.5 Legacy surrogate capability

The existing neural surrogate uses `objective.scalar` and predicts a `MetricSet` without throat
impedance (`surrogate/predict.py`, `train.py`). Before it can be compared with BoTorch it must
declare supported objective versions/inputs and either share a version-aware pure scorer adapter
or refuse unsupported newer objectives. No fabricated impedance/metrics. Audit only in M0.

## 4. Lane ownership

| Lane | Worktree | Owns | Must not edit |
|---|---|---|---|
| DATA (S0+R0) | `BO-M0-DATA` | `tools/analysis/catalog.py`, `cohorts.py`, `offline_scores.py`; `hornlab_search/objective/replay.py`; focused tests; preservation/surrogate audit reports | `_common.py`, dataset writer, `config.py`, solver, GUI, frozen contracts |
| ENCODING (B2) | `BO-M0-B2` | `tools/analysis/parameter_activity.py`, `geometry_effects.py`; `hornlab_search/bo/{data,encoding,metrics}.py` (pure adapters); focused tests/fixtures | `_common.py`, scorer math (consume R0), production configs/cache/search/writer/GUI |
| COST (S3) | `BO-M0-S3` | `tools/analysis/_common.py`, `seed_variance.py`, `ab_compare.py`, focused tests | search algorithms, GUI, dataset writer, S0/R0/B2 modules |

Shared helper `tools/analysis/_common.py` has exactly one owner: **S3**. DATA/B2 read it or
coordinate; they do not edit it.

## 5. Handoff format (all lanes)

Return one message containing:

1. changed-file list and `git -C <worktree> status --short`;
2. exact commands run (absolute Python path, cwd) + actual pass/fail counts and failure excerpts;
3. the frozen/proposed API surface: function signatures, artifact field lists, reason codes;
4. actual evidence counts (records, unique solves, cohorts, exclusions) with source paths;
5. explicit untested limits and unresolved contract gaps for the parent;
6. no commits/pushes, no live-data writes.

The parent will not accept "tests pass" without the exact output, and will reconcile every
file change against the ownership table.
