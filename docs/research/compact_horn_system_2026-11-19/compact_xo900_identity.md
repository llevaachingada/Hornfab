# Compact crossover-aware identity — `compact_xo900_1250_hf1440_v10xo`

**Status (2026-11-19): authored and measured. CPU only. No GPU solve, no queue change, no git
mutation. No stored run, brief, objective, `runs/`, `docs/CODE_MAP.md` or `docs/INDEX.md` file was
edited.**

Brief: [`examples/briefs/compact_2026-11-19/compact_xo900_1250_hf1440_v10xo.yaml`](../../../examples/briefs/compact_2026-11-19/compact_xo900_1250_hf1440_v10xo.yaml)

This document publishes the identity's **floor** and a **CPU replay** of the six already-solved
compact designs. It is the deliverable promised by
[`solver_proposal.md`](solver_proposal.md) §4 step 3 and answers the gap named in
[`candidate_register.md`](candidate_register.md) §3 ("No 900-1100 Hz scoring exists").

---

## 1. What the identity encodes, and why

The owner decision (2026-11-19) was to open a **separate, crossover-aware compact identity** — not
to change v7 or v10 — and to encode the new priority **in the brief's targets**, reusing the
existing v10 objective scalar. No objective/scalar code is added.

The measured justification, quoted from the two dossiers this work must cite:

- `candidate_register.md` §3: *"No 900-1100 Hz scoring exists. Every lane was scored with the v7 or
  v10 target, whose V target starts at 1 kHz and whose F_X is 700 Hz. Crossover feasibility above is
  a screen of stored metrics, not a design objective."*
- `solver_proposal.md` §4: no non-reference compact row reaches the 40-60° V corridor below ~1.1 kHz
  (A1 88.8° @850 → 69.4° @1100; A2 69.0 → 56.3; K1 104.9 → 82.5; K2 163.9 → 123.9; R1b 128.4 →
  112.1), and A5 never does (134.2° @1100). *"The v10 corridor only starts its V target at 1 kHz
  (40-60°) and its F_X is 700 Hz, so a horn judged 'good' by v10 can still be unusable as the top of
  a 900-1100 Hz two-way."*

That is a **new acoustic priority** (a crossover-band requirement), so it is a new identity under
`hornlab-typology-research`. The construction, driver and envelope are unchanged; only the scored
target band changes. The corridors are **exploratory owner-requested priorities, not acoustic laws**
and not CD/Keele rules generalized across families.

### 1.1 Exact key mapping (where each priority lives)

Verified against the loader and the v10 scalar path:

| Priority | Key(s) | Consumed by |
|---|---|---|
| **F_X** (loading crossover corner) | `target.f0_hz` | `targets.spec.Target.f0_effective_hz()`; `objective/scalar_v7.py:342,366` (`fx = target.f0_effective_hz()`, `lfp_pen = max(0, log2(LFP20 * lfp_crossover_ratio / fx))`); score mask `objective/scalar_v9.py:638` (`score = band & (f >= target.f0_effective_hz())`) |
| **V-corridor start / band** | `target.f0_v_hz` + `target.coverage_profile.v[0].hz` | `targets/spec.py:19-26`; `targets/profile.py:profile_onset_hz` = `max(first_anchor_hz, plane_f0)`; `objective/scalar_v9.py:_plane_onset` |
| **Band edges** | `target.band_lo_hz`, `target.band_hi_hz` | carried in every target-aware term; `band = (f >= lo) & (f <= hi)` in `scalar_v9.py` / `scalar_v10.py` |
| **H / V target corridors** | `target.coverage_profile.{h,v}[].{hz,preferred_deg,min_deg,max_deg}` (+ `mode: corridor`, `interpolation: log_frequency`) | `targets/profile.py`; `objective/scalar_v9.py:_profile_at`, `_plane_cov_cost` |

No new key was needed. **Contract gap: none.** `target.f0_hz`, `target.f0_v_hz`,
`target.coverage_profile.{h,v}[].{hz,preferred_deg,min_deg,max_deg}`, `target.band_lo_hz` and
`target.band_hi_hz` all exist in `Target.from_dict` (`hornlab_search/targets/spec.py`).

### 1.2 Values chosen (and why they are not invented laws)

| Field | v10 home | this identity | reason |
|---|---|---|---|
| `f0_hz` / `f0_v_hz` | 700 / 700 | **850 / 850** | F_X is a scalar; 850 Hz is exactly the lowest crossover the register screened and reproduces its loading rule `lfp20 <= XO/1.6` (`531.25 = 850/1.6`). It also permits a profile anchor at 850 (`parse_profile` refuses an anchor below the plane f0). Satisfying the loading rule at 850 automatically satisfies it at 900/950/1100/1250 (the threshold rises with XO), so 850 is the strict end that covers the whole screened window. |
| H corridor | 60-90 (pref 80) from 700 | **65-100 (pref 80) from 850, held to 1250+** | exploratory NEW priority |
| V corridor | 40-60 (pref 50) from 1000 | **40-75 (pref 50) from 850, held to 1250+** | exploratory NEW priority; the V knee is the measured v10 failure |
| band | 350-8000 | **350-8000 (unchanged)** | a crossover floor must not delete sub-crossover frequencies |
| weights / tolerances / `ripple_region` / `version` | v10 | **identical** | reuse the v10 scalar; only the target changes |

`cov_below_f0: one_sided` is kept, so 350-850 Hz remains scored (a wide pattern there is free
physics; only a too-narrow one is charged). `rip`, `flat`, `flat_cv` and `load` still run over the
whole declared band. The preferred angles (80/50) are unchanged so the v10 `ripple_region:
preferred_edge` window is not moved as a side effect.

Above 1250 Hz the last profile anchor is held (the parser does not extrapolate), so the corridor
continues to 8 kHz. That is the schema's documented behaviour, not an extra invented rule.

---

## 2. The identity floor (published)

**Floor = 0.2783 J** (combined), from the documented `b1_mesh` **top-28-pair protocol**: the
frequency part is the sd of `screen_j - verify_j` over the **top 28 designs by verify J**, and the
mesh part is the fixed B1 mesh sd. This is the same construction that produced v7 0.3105 and v10
0.4677 (`docs/evidence/b1_mesh_2026-11-18/README.md` §WP 2.3; `docs/CODE_MAP.md` L282).

| component | value (J) |
|---|---|
| frequency part (top-28 sd of screen − verify, **257 pairs**) | **0.27816444900371107** |
| mesh part (B1, fixed; `floor_record.json`) | 0.007676441842658574 |
| **combined floor** `sqrt(freq² + mesh²)` | **0.2782703514** |

Pair count: **257 finite pairs** (258 paired design directories; one verify row is unmeasurable and
is excluded, no errors). Top-N: **28**.

### 2.1 Exact command

```powershell
.\.venv\Scripts\python.exe tools/analysis/rescore_identity.py floor `
  --brief "examples/briefs/compact_2026-11-19/compact_xo900_1250_hf1440_v10xo.yaml" `
  --runs-root runs --top 28 `
  --out "$env:TEMP\opencode\floor_v10xo"
```

Exit status `0`. The summary written to `floor_summary.json` (score-id list elided):

```
{
 "brief": "examples/briefs/compact_2026-11-19/compact_xo900_1250_hf1440_v10xo.yaml",
 "n_pairs": 257,
 "mean_diff_all": -0.3170635577774744,
 "sd_diff_all": 0.4454134902777868,
 "spearman_all": 0.9547241199891411,
 "top": 28,
 "sd_diff_top": 0.27816444900371107,
 "spearman_top": 0.4504652435686919
}
```

Protocol check (same command and run set, v10 brief) reproduced the v10 frequency floor
**exactly**: `n_pairs 257`, `sd_diff_top 0.46767581844496897`, which is the value in the existing
`runs/analysis/v10_rescore_2026-11-18/floor_v10/floor_summary.json`. (`floor_record.json` publishes
`0.46767600053596237`; the two v10 records differ in the 7th decimal, and this replay matches the
`floor_summary` value exactly.) That is the evidence that the run set and pairing are the
documented protocol, not a new one.

### 2.2 Which stored runs were used

Rule: every run directory under `runs/` that has **both** `designs/` and `verify/designs/` — i.e.
the paired screen/verify runs. `--runs-root runs` discovers them; nested `study-*/screen` dirs are
visited but skipped by the floor pairing because a study screen has no sibling `screen/verify/`.
The result is **71 paired run dirs**, 258 paired design dirs, 257 finite pairs.

Full set (71):

```
20261013T053757Z-screen-7e6e5b  20261027T051600Z-screen-ed1da9  20261027T052720Z-screen-e7f4f8
20261027T070736Z-screen-d37d64  20261027T073751Z-screen-c7a1db  20261027T075151Z-screen-4b0492
20261027T083216Z-screen-23544f  20261027T085242Z-screen-c7d820  20261027T090600Z-screen-3c966e
20261027T095824Z-screen-48956a  20261027T104422Z-screen-a060fb  20261027T110844Z-screen-41dc97
20261027T223824Z-screen-2978fc  20261029T030445Z-screen-7a1e70  20261029T041046Z-screen-54280b
20261029T054210Z-screen-219b47  20261029T055455Z-screen-0b7917  20261030T111108Z-screen-377bbe
20261030T170642Z-screen-fbab4f  20261101T004552Z-screen-427d57  20261101T015657Z-screen-fc1d24
20261115T052416Z-screen-cdbc27  20261115T060011Z-screen-9e3528  20261115T085601Z-screen-0c9c90
20261115T105220Z-screen-e0be04  20261115T115015Z-screen-f1258b  20261115T152510Z-screen-a504f6
20261115T154322Z-screen-07bea2  20261115T161238Z-screen-1b1b6e  20261115T162516Z-screen-e31b23
20261115T163824Z-screen-d4a7c4  20261115T164910Z-screen-f94955  20261115T165937Z-screen-4d8a33
20261115T171150Z-screen-d66ffb  20261115T180109Z-screen-0f2ab5  20261115T181250Z-screen-1e22a5
20261115T182340Z-screen-35c541  20261115T194455Z-screen-bf9fc8  20261116T001222Z-screen-b25d61
20261116T003142Z-screen-981f59  20261116T030920Z-screen-5d1082  20261116T043544Z-screen-dd15d8
20261116T044917Z-screen-12eb61  20261116T052759Z-screen-44001e  20261116T054705Z-screen-570bc6
20261116T060140Z-screen-679c6f  20261116T061215Z-screen-058f0d  20261116T064438Z-screen-8defc1
20261116T065413Z-screen-a70423  20261116T071520Z-screen-1c8608  20261116T073857Z-screen-7b9313
20261116T074832Z-screen-620f81  20261116T081139Z-screen-63158a  20261116T085415Z-screen-0a228d
20261116T090751Z-screen-37b115  20261116T093400Z-screen-56681d  20261116T095336Z-screen-7fc9b7
20261116T130335Z-screen-ab4fb9  20261116T131710Z-screen-f1a263  20261116T145634Z-screen-e4c778
20261116T150941Z-screen-0e777a  20261116T152544Z-screen-5f7d93  20261116T153619Z-screen-c221aa
20261116T173311Z-screen-96f899  20261116T193501Z-screen-f008ad  20261117T003115Z-screen-4f7cd5
20261117T053153Z-screen-15f0e4  20261117T071329Z-screen-e4f90d
elites_20261030_ath_core  elites_20261030_core_law  elites_20261030_hypex
```

**Read:** a J gap below **0.2783 J** inside this identity is a TIE. Do not reuse the v10 0.4677 or
v7 0.3105 floors here.

---

## 3. CPU replay of the six solved compact designs

CPU replay only: stored `response.npz` + `metrics.json` are re-scored under the new brief. **No
solver ran.** Fidelity label for every row: **CPU replay / SCREEN_MAGNITUDE** (single-mesh stored
screen response, balloon DI). **No installed/exterior BEM exists** for any row (no BL case id;
`candidate_register.md` §3, `SENIOR_REVIEW_HANDOFF_2026-11-19` §4 risk R1). `stored_j_own_identity`
is the run's own stored J under its original identity (v7/v10) and is **never** comparable to
`j_v10xo`.

### 3.1 Exact commands

Per run (all exit `0`):

```powershell
.\.venv\Scripts\python.exe tools/analysis/rescore_identity.py rescore `
  --brief "examples/briefs/compact_2026-11-19/compact_xo900_1250_hf1440_v10xo.yaml" `
  --out "$env:TEMP\opencode\rescore_v10xo\A1" "runs/20261119T155454Z-screen-d1a61d"
# ... repeated for A3, A2, K1, C2 and fold_warm with the run dirs in the table below
```

The target design is read from each output `rescore.jsonl` by `design_hash`; `mixed_identity` is
read from the same run's `rescore_summary.json`.

### 3.2 Results (ordered by `j_v10xo`)

| # | ID | design | run | `j_v10xo` | status | `stored_j` (own identity) | `mixed_identity` | fidelity |
|---|---|---|---|---|---|---|---|---|
| 1 | **fold_warm** | `00826f071b24` | `study-0c9805ad97208a2e/screen` | **1.062399** | exact_complete | 3.590065 | false (1 identity) | CPU replay / SCREEN_MAGNITUDE |
| 2 | **A3** | `b295be5854c2` | `20261119T152446Z-screen-d98c8d` | **1.602795** | exact_complete | 8.741988 | false (1 identity) | CPU replay / SCREEN_MAGNITUDE |
| 3 | **A1** | `74d8eed97268` | `20261119T155454Z-screen-d1a61d` | **1.657784** | exact_complete | 4.161633 | false (1 identity) | CPU replay / SCREEN_MAGNITUDE |
| 4 | **A2** | `5487ba86a54b` | `20261119T153950Z-screen-5d766f` | **1.707416** | exact_complete | 5.872227 | false (1 identity) | CPU replay / SCREEN_MAGNITUDE |
| 5 | **C2** | `be9ab290d3cf` | `20261119T161820Z-screen-9fda2a` | **2.468036** | exact_complete | 7.598246 | false (1 identity) | CPU replay / SCREEN_MAGNITUDE |
| 6 | **K1** | `3545b3e078ac` | `20261119T073330Z-screen-723756` | **3.444470** | exact_complete | 2.969981 | false (1 identity) | CPU replay / SCREEN_MAGNITUDE |

All six rows are `exact_complete`, no refusals, `target_changed: true`, `parity_delta: null`
(expected: a target change is not a parity replay). The shared score-identity count across the six
is **1** (`mixed_identity: false`). Per-run summary rows: A1 41/55, A3 30/31, A2 30/37, K1 41/41,
C2 10/27, fold_warm 80/80 scored.

**Ordering: fold_warm < A3 < A1 < A2 < C2 < K1.**

Gaps against the floor (0.2783 J):

- fold_warm leads A3 by 0.5404 J → **real** (> floor).
- A3 → A1 = 0.0550 J and A1 → A2 = 0.0496 J → **ties** (both < floor). The honest statement is that
  A3/A1/A2 are statistically indistinguishable on this identity.
- A2 → C2 = 0.7606 J and C2 → K1 = 0.9764 J → **real** separations.

---

## 4. Historical 80×50 home corridor — separate readout (v10, NOT overwritten)

The v10 home identity is not restated in the new brief's target and the v10 brief file was not
edited. It is kept as a separately identified readout: the same six design hashes, CPU-replayed from
the same stored responses under the unchanged
[`room_landscape_80x50_700_hf1440_v10.yaml`](../../../examples/briefs/home_landscape_2026-11-18_v10/room_landscape_80x50_700_hf1440_v10.yaml)
(H 60-90 pref 80 from 700 Hz, V 40-60 pref 50 from 1000 Hz, F_X 700).

| # | ID | design | `j_v10` (home 80×50) |
|---|---|---|---|
| 1 | fold_warm | `00826f071b24` | 1.421403 |
| 2 | A1 | `74d8eed97268` | 1.985767 |
| 3 | A3 | `b295be5854c2` | 2.773388 |
| 4 | A2 | `5487ba86a54b` | 2.881348 |
| 5 | K1 | `3545b3e078ac` | 3.742832 |
| 6 | C2 | `be9ab290d3cf` | 4.819274 |

These reproduce the v10 numbers already in `candidate_register.md` §4 (A1 1.9858, A3 2.7734,
A2 2.8813, K1 3.7428, C2 4.8193) and the fold-warm 1.4214 v10 leader. **The two columns are never
pooled:** they are different target sets, so their J are different identities. (The ordering itself
differs — the new identity reverses A1/A3 and places C2 ahead of K1 — which is the point: the
crossover priority is not a monotone relabelling of v10.)

---

## 5. What this identity still cannot say

- **No installed/exterior BEM for any row.** No Boundary Lab case id exists for any compact
  candidate; the horn channel in the available system cases is an ideal normal-velocity source, not
  a compression driver (`candidate_register.md` §3; `SENIOR_REVIEW_HANDOFF_2026-11-19` §4 risk R1).
  A good `j_v10xo` is an isolated-horn screen magnitude, not a built-horn result.
- **No woofer, cabinet, baffle or real centre spacing.** Panel fit and real spacing need a maker
  drawing; the register's spacing numbers are moving-diameter lower bounds. This identity scores
  the horn's *crossover-band behaviour*, not the assembled two-way.
- **The floor is a score-consistency floor, not a physical repeatability floor.** It is the
  documented screen/verify frequency part over older runs whose grids differ; it does not measure
  build-to-build or driver-to-driver variation. Per-design `dJ < 0.025 J` still needs the B1
  mesh-sensitive flag.
- **The corridors are exploratory scoring priorities, not acoustic laws.** They are not CD targets,
  not Keele mouth rules, and not transferred from another family. A later physical anchor could
  contradict them.
- **Identity matching needs the brief, not just the objective block.** The objective block is v10's
  (same `v10_score_identity` sha); the row identity from `_row_score_identity` additionally carries
  `brief_hash`/`brief_name`. Never filter this column by the v10 objective sha alone.
- **No search is authorised by this document.** Any CMA/BO on this identity must first pass
  `tools/search_preflight.py` (sigma0 rule) and is an owner/orchestrator decision.
- **A4 (published TwinRay reconstruction) is not in this replay** — it has no v7/v10/v10xo J of its
  own (`candidate_register.md` §2 A4) and remains reference-only.

---

## 6. Registration lines (proposed — NOT applied)

`docs/CODE_MAP.md`, insert after the v7 hifi brief row in **Configs and tools**:

```diff
--- a/docs/CODE_MAP.md
+++ b/docs/CODE_MAP.md
@@ -192,1 +192,2 @@
 | `examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7_hifi.yaml` | H12 hifi brief (2026-11-16): the room-landscape 80x50 v7 brief with `flat_band: scored`, `cov_v_weight: 0.5` and `oa_excess_tol: 0.5`; same target/driver/envelope as the base brief. |
+| `examples/briefs/compact_2026-11-19/compact_xo900_1250_hf1440_v10xo.yaml` | **Compact crossover-aware brief identity (2026-11-19, owner-approved, CPU-authoring only):** objective **v10 scalar reused unchanged** (`version: 10`, `ripple_region: preferred_edge`); only the target differs - F_X `f0_hz`/`f0_v_hz` 850 Hz, corridor H 65-100 (pref 80) / V 40-75 (pref 50) from 850 Hz, band 350-8000 Hz retained, same HF1440 / 600x480x480. A NEW identity, **never rankable against v7/v10**; published floor **0.2783 J** (b1_mesh top-28-pair protocol, 257 pairs). Readout: `docs/research/compact_horn_system_2026-11-19/compact_xo900_identity.md`. |
```

`docs/INDEX.md`, insert after the `research/system_woofer_2026-11-18/readiness.yaml` row in
**Research**:

```diff
--- a/docs/INDEX.md
+++ b/docs/INDEX.md
@@ -337,1 +337,2 @@
 | [research/system_woofer_2026-11-18/readiness.yaml](research/system_woofer_2026-11-18/readiness.yaml) | Machine-read registry behind `#/hw/readiness`: R1-R17 status/evidence/WP, owner decisions, case fidelity declarations (the ONLY source of fidelity labels). |
+| [research/compact_horn_system_2026-11-19/compact_xo900_identity.md](research/compact_horn_system_2026-11-19/compact_xo900_identity.md) | **Compact crossover-aware brief identity (2026-11-19, CPU-only):** reuses objective v10 unchanged and moves the priority into the brief target (F_X 850 Hz; H 65-100 / V 40-75 from 850 Hz; band 350-8000 retained). NEW identity, never ranked against v7/v10; floor **0.2783 J** (b1_mesh top-28-pair protocol, 257 pairs); six-design CPU replay fold_warm < A3 < A1 < A2 < C2 < K1; historical 80x50 v10 readout kept separate. Brief: `examples/briefs/compact_2026-11-19/`. |
```

Do not apply these from this task; the parent integrator owns the shared docs.

---

## 7. Reproducibility ledger

| check | command (from `C:/Users/hunte/Hrns/hornlab-search`) | exit |
|---|---|---|
| brief loads through the real loader | `python -c "from hornlab_search.config import load_brief, load_config; ..."` (see §2/§7.1) | 0 |
| identity floor | `python tools/analysis/rescore_identity.py floor --brief examples/briefs/compact_2026-11-19/compact_xo900_1250_hf1440_v10xo.yaml --runs-root runs --top 28 --out <dir>` | 0 |
| v10 floor protocol check | same command with the v10 brief | 0 |
| six rescoring columns | `python tools/analysis/rescore_identity.py rescore --brief <new brief> --out <dir> <run>` ×6 | 0 each |

Output directories for this pass were written outside the repo
(`%TEMP%\opencode\...`) so that `runs/` stayed untouched. A committed reproduction should use
`runs/analysis/compact_xo900_floor_2026-11-19/` and `runs/analysis/compact_xo900_rescore_2026-11-19/`
by the integrator; `--out` does not affect any number.

### 7.1 Brief-load output (pasted)

```
load_brief ok: compact_xo900_1250_hf1440_v10xo
objective.version: 10 ripple_region: preferred_edge
band: 350.0 8000.0
f0_hz: 850.0 f0_v_hz: 850.0
h: [{'hz': 850, 'max_deg': 100, 'min_deg': 65, 'preferred_deg': 80}, {'hz': 1250, 'max_deg': 100, 'min_deg': 65, 'preferred_deg': 80}]
v: [{'hz': 850, 'max_deg': 75, 'min_deg': 40, 'preferred_deg': 50}, {'hz': 1250, 'max_deg': 75, 'min_deg': 40, 'preferred_deg': 50}]
load_config(brief=) ok: 850.0 10 preferred_edge
resolved grid: {'verify_points_per_octave': 6, 'screen_extra_hz': [250, 315, 400, 2573, 3311, 4260]}
```

(The `load_config(brief=...)` call loads an existing typology config with the new brief injected as
the `brief=` override, so the brief passes through `_validate_objective_block`,
`_require_v9_coverage_profile`, `Target.from_dict` and `_brief_preflight_and_derive` exactly as a
real run would. `load_brief` alone is not the full loader.)
