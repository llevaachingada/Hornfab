# GUI integration plan — planning pass (proposed, 2026-10-25)

PLANNING pass written at M5 (`298b56f`, main == origin/main). Scope: the GUI surface needed by EVERY
capability the implementation plan adds by its end (WP1–WP17 + P6a/P6b). This doc does not commit to
building the owner-gated features — their GUI hooks are specified so landing them later is additive.
Origin: handoff `HORNLAB-SEARCH HANDOFF — GUI-INTEGRATION PLANNING PASS` (2026-10-25, after M5 WP11);
inventories file-verified against the tree on 2026-10-25 (in-flight WIP disclosed in §13). Oracle
review: pending → applied (see Status, §12). Commit discipline mirrors `docs/GUI_CONTRAST_PLAN.md`.

## Goal

Give every plan capability an honest, provenance-first GUI presence — routes, endpoints, views,
workflows — keyed to committed artifacts only, so that a run whose solve uses CUDA fused path, a
near-corrected solve, an enclosure mount, a multicell STEP body, a non-uniform source plug, or a
bake-off can never be *silently mixed* with a plain `beat_cuda` screen record in any comparison,
leaderboard, or dataset view.

## Constraints (binding) — inherited from GUI_CONTRAST_PLAN

- No build step, no npm, zero new runtime deps; Three.js stays r160 via the CDN import map with a
  functional 2D SVG fallback (`static/index.html:12-20`, `static/view3d.js:61+`).
- Both themes via `data-theme` + `localStorage "hl-theme"` + `prefers-color-scheme`; every new view
  inherits theme boot, `?theme=light|dark` capture override, tokens, and the semantic redundancy
  tests (GUI_CONTRAST_PLAN §Phase 2 / §Phase 6 / §Verification recipe).
- `pyproject.toml` ships static with the flat `static/*` glob — no new subdirectories; a new
  `static/bakeoff.js` is a file, allowed; a subdirectory would require flipping the glob in the same
  commit.
- Never touch: `server.py` security surface (Host check, 127.0.0.1 bind), frozen `docs/plan/**`,
  `types.py`/`record.py` literals, physics/mesher/solver code, and the 8 hard rules throughout.
  New GUI-visible provenance keys on solver/fork side are *specified* here but land via their own
  WP lanes, not this plan.
- Reader-first: every view derives from committed artifacts in the run dir (`run.json`,
  `search.ndjson`, `archive_heatmap.json`, `designs/<hash>/...`, `config.yaml`, `report.html`,
  `cma/restart_k/*`, `verify/`); no in-process solving; GPU work only via the `jobs.py` allow-list
  with the one-GPU lock.
- Interpreter always `.venv\Scripts\python.exe`; offline test selection `-m "not slow and not gpu
  and not crosscheck"`; junitxml is the authoritative counter.

## 1. GUI today (baseline, verified @ 298b56f)

`server.py` GET dispatch :36-84, POST :103-129. Existing routes: `/api/status` :39, `/api/runs` :41,
`/api/run/<id>` :43, `/api/campaign(s)` :45-48, `/api/mesh/<run>/<hash>` :49, `/api/briefs` :51,
`/api/evolution/<id>` :53, `/api/archive/<id>` :55 (QD atlas, `data.py::run_archive` :383 with the
`available:false` honesty pattern :396-399), `/api/typologies` :57, `/api/leaders` :59,
`/api/configs` :61, `/api/catalog` :63, `/api/families` :65, `/api/jobs` :75-81,
`/api/compare?a&b` :82-101, raw `/runs/<id>/report.html` :213 and `/runs/<id>/step/<name>.step` :217
(strict `D.STEP_NAME`); POST brief-save/preview/jobs/cancel/gpu-clean :107-124.

Views (`static/app.js`): ROUTES :49-64 — home, status, campaigns + detail, runs, run detail :991,
`#/run/<id>/3d` :55, `#/run/<id>/evolution` (evolution.js), `#/run/<id>/archive` :57
(viewRunArchive :879-989, canvas heatmap, hover readout, honest empty states), compare :1400,
briefs :1523, launch :1723, typologies :2201, glossary. Run-detail buttons :1024-1033 (Evolution /
QD atlas / 3D / Compare / report / Export STEP top-3). Job kinds (`jobs.py:113-141`): `dry-run`,
`run`, `search`, `campaign`, `export-step`, `report`; GPU kinds `run|search|campaign` :23;
**`verify` is NOT an allow-listed kind (gap G-1)**.

Not read by the GUI today (verified): `best.json`, `cma/restart_k/*`, raw `archive.json`,
`run.json.restarts`, `run.json.qd`, the `run.json.config` dict, dataset provenance beyond summary
keys. The QD atlas is the ONLY post-M5 new-capability view so far.

## 2. Capability inventory at plan end (verified per-work-package)

| WP | Capability (plain terms) | Status | Keys it adds | Run-dir artifacts for the GUI |
|---|---|---|---|---|
| 1 | Objective v2 opt-in (detrended ripple/flatness, Gaussian-beam DI target) + offline re-score | DONE (M1 `28b05ff`) | `objective.version` | `run.json.objective_version`; `objective_version` in every ndjson row + dataset record |
| 2 | Brief pins the driver (`r0_mm` fairness, throat-angle policy) | DONE (M1) | `driver.throat_angle_policy: pin\|free` | report scalar `throat_angle_mismatch_deg` in ndjson scalars |
| 3 | Shape-only perturb + graded infeasibility | DONE (M1) | `generator.perturb.mode: shape\|legacy`, `search.infeasible_penalty: graded\|flat` | failure marker kind `invalid_envelope` (+ `brief_hash`, `lib_shas`) |
| 4 | Per-frequency weights + HF verify grid | DONE (M1) | `target.freq_weights`, `grid.verify_points_per_octave` | solve grid group `solve.freqs_hz` (hash-distinct); weights echoed in `config.yaml` |
| 5 | Measurement pack (2/10/50 m, balloon scaling, source motion) | DONE as measurement (M3 `38b0847`) | `solve.source_motion: normal\|axial` | `Response.meta["source_motion"]`; distance/balloon already in ` ObservationSpec` |
| 6 | 12 kHz demo-sheet searches | **ABANDONED** (owner: capability banked via WP15) | none | none |
| 7 | Coarser rear/shell mesh | DONE measured (M3); proposal only | `mesh.rear_res_factor` | `-rearN` cache suffix + `extra.rear_res_factor` in solve hash; resolution map in `mesh_meta.json` |
| 8 | Band-split meshing | Machinery landed; gate FAILED → opt-in (M3) | `mesh.band_split {edges_hz}` | provenance `mesh_policy: band_split_v1` + `extra.band_edges_hz`; `Response.meta["seam_check"]` |
| 9/9b | New freeform generators + lecleach/organic/X rows | DONE (M4 `0ee5a28`) | profile types `splice`, `spherical_salmon`, `lecleach`, …; rows kinds | `design.json.generator {name,spec,knobs,…}`; `design.params["grid"]` |
| 10 | GRID family via point-grid builder | DONE (M4) | `generator.name: grid` + `GRID_SPEC_KEYS`, `span: quarter\|half` | `design.params["grid"]`, `mesh_meta.json` (sign conventions); **no mesh cache** (sketch at `mesh/grid_build.py` EOF) |
| 11 | IPOP/BIPOP restarts + CMA-ME QD atlas | DONE (M5 `298b56f`) | `search.restarts {mode,max}`, `search.algorithm: cma_me`, `search.qd {…}` | `run.json.restarts[]`, `run.json.qd`, `cma/restart_k/*`, `archive.json`, `archive_heatmap.json` (pinned contract) |
| 14 | Multicell prototype via CAD→STEP (3×3 build123d exporter, presentation-style face labels `driver`/`wall` named in the STEP text — physical tag assignment is the adapter lane's, TBD; closed-solid guard) + CPU double/near-correction validation arm | **LANDING** (uncommitted: `tools/cad/multicell.py`, `tests/test_cad_multicell.py`; mesh adapter + validation runs pending) | `solve.near_correction(_cutoff/_order)`, `solve.solve_precision` (WIP; ride `SolveSpec.extra` only when set) | STEP files (existing `/runs/<id>/step/` route); planned face-label inventory sidecar (§5) |
| 15 | Fused CUDA Burton-Miller | DONE (M1/M2) | `solve.cuda_fused`, env `HORNLAB_BEAT_FUSED_BM_CUDA=1` | `Response.meta["cuda_fused"]`; per-freq `native_diagnostics.assembly_path = "fused_cuda"` |
| 16 | Non-uniform source velocity `v(r)=1+α·J0(j01·r/r0)` on the fused path (fork) | **LANDED-fork / LANDING-repo** — WP16 committed `f4ef05c` on `hornlab-search/wp16-source-profile` and **pushed to `ourfork` = github.com/llevaachingada/hornlab-beat-bem** (verified: branch contains it); repo-side ride key does NOT exist yet (rg = 0 hits — "TBD" is verified, so repo integration pending; gate B = fork hosting: a hosted branch now exists, whether the owner's gate B is thereby met is an owner call) | `SolveConfig.source_profile_alpha` (repo-side ride key TBD by that lane) | per-freq diagnostics when α≠0: `source_profile="j0_radial"`, `source_profile_alpha`, `source_profile_path="fused_cuda"`, `source_profile_face_count`, `assembly_path` |
| 17 | Near-singular correction on fused CUDA (no-symmetry first, then symmetry) | PLANNED (fork; staged) | consumes the same `solve.near_correction*` keys | must add its own CUDA near-correction diagnostic next to `assembly_path="fused_cuda"` (spec, §3.10) |
| 12 | Enclosure mounting via brief block → mesher's OWN HornEnclosure keys | PLANNED (owner gate) | `brief.mounting {type: enclosure, depth_mm, margins, edge_mm, plan}` | planned `provenance.mounting` in records; mesher keys real names: `depth_mm`, `space_l/t/r/b_mm`, `edge_mm`, `edge_type`, `plan_type`, `plan_n`, `enc_front/enc_back resolution` (`geometry.py:130-152`, `config_builder.py:608-664`, `config_parser.py:862-883`) |
| 13 | Axisymmetric BEM backend | PLANNED (owner gate + GPL-3.0 decision) | `backend: axibem` | its own dataset group; H=V cuts; θ-only DI must stay `di_source`-honest |
| P6a | Superformula mouth campaigns (m=4/8/12, 9 configs) | PLANNED (gates: WP1–17 + owner GO) | `gcurve_type: 2`, `gcurve_sf_*` knobs | D19 GUI: `guiding_curve {phi[], r[], m, dist}` on `/api/run/<id>` |
| P6b | GSA vs CMA-ES bake-off | PLANNED (same; CMA stays default) | `search.algorithm: gsa` + `search.gsa`, `compare --bar` judge (W4, MISSING) | `runs/bakeoff_<id>/bakeoff.jsonl` + `bakeoff_summary.json` (pre-registered row contract) |
| P5 W4 | `compare --bar` judge mode | PLANNED | CLI flag | nonzero exit at CP-7f bars (0.039 dB / 1°) |

## 3. Feature-by-feature GUI hooks

### 3.1 Already-visible, keep: QD atlas (WP11) + evolution (WP11)
`viewRunArchive` :879-989 covers the pinned `archive_heatmap.json` contract. Enhancement E-3.1:
the atlas header should surface the `run.json.qd` provenance (algorithm, descriptor meanings,
coverage N/M, total non-cached evals) instead of only axes labels — data already committed; once
C-1 puts `qd` in `run_detail`, that is the single source of truth (no `run_archive` mirror).

### 3.2 Restarts diagnostics (WP11 — data committed, GUI MISSING today)
`run.json.restarts[]` ({index, popsize, sigma0, n_new_in_restart, evals_in_restart, stop}) and
`run.json.qd` are written for every restart run but no view reads them. Hook:
- `data.py::run_detail` :358 gains additive keys `restarts`, `qd` (read from run.json; absent when
  absent — no shape invention, list the array as-is), plus a `restart_dirs` listing of
  `cma/restart_*` directory names (names only; pycma logs stay file-downloadable via a new static
  route mirroring `/run/<id>/step/` — §5).
- `viewRunDetail` :991 gains a **restart strip**: mode/max header, one row per restart (k, popsize,
  σ₀, evals, stop reason), and the schedule is visible next to the search settings. Honest empty
  state when `search.restarts` is unset (single-ES run): row reads "single ES".
- Per-restart pycma logs (`cma/restart_k/*`) exposed download-only, never parsed — same contract as
  `report.html` raw serving.

### 3.3 Objective version, weights, solved grid (WP1/WP4)
`viewRunDetail` KPI strip gains a compact provenance row: `objective_version` badge (v1 default
unlabelled, v2 explicit "J v2"), the effective `freq_weights` bands only when non-default (else
"uniform"), and the solved frequency grid identity (`solve.freqs_hz` from config.yaml) + screen vs
verify grid group label. Comparing runs of different `objective_version` in the compare view must
render a warn banner (never a silent mix) — compare view hook in §3.9's group logic.

### 3.4 Driver pin + measurement provenance (WP2/WP5)
Run detail shows `throat_angle_mismatch_deg` next to f11 (`scalars` already carries it) and badges
for `solve.distance_m`, balloon points, `source_motion=axial` when non-default. f11 caveat rule:
any panel whose band_hi exceeds `scalars.f11_hz` must print the caveat sentence — "8–12 kHz compare
GEOMETRIES, not drivers (above f11 = 7,914 Hz for 1″ the source is an idealized rigid cap)". This
sentence is an established repo rule carried in the brief headers (`examples/briefs/*_12k.yaml:3`)
and CONTINUITY's caveat mandate — `report/html.py:272-275,401` draws only the f11 marker/value, so
the web views ADD the sentence here (that is the work: bringing an existing verbal rule into the
web surface, `constants.py:12-16` is the f11 formula).

### 3.5 Generator / GRID recipe display (WP9/9b/10)
`viewRunDetail` knob table already reads `design.json` knobs via `run_detail.params`; additions:
`design.params["grid"]` recipe (n_phi/n_s/span, wall_thickness) rendered as a "GRID recipe" chip
row, and rows-kind provenance ("labeled hypothesis-shape experiment" wording kept verbatim from
`grid.py:112-114`). 3D view unchanged (mesh.msh is span-aware; `mirrorMesh` already passes full
meshes through).

### 3.6 Failure-kind semantics (WP3)
`failurePills` :161 already words failures; ensure `invalid_envelope` (graded-penalty rows) is
distinct from `invalid_geometry` / `mesh_too_large`, and run detail's sensitivity panel shows the
graded penalty term (it already reads `terms`; label the penalty component). No new endpoint.

### 3.7 Multicell STEP provenance (WP14 — LANDING)
Today `/runs/<id>/step/<name>.step` :217 serves raw STEP by strict name, and run detail lists
`step_files` :1032. WP14 adds: face labels exactly `driver` / `wall` — but as **presentation-style
labels only** (`STYLED_ITEM('driver', …)` per `multicell.py:42-64,93-95,421-474`); NO tag numbers
appear in the STEP text — mapping faces to source tag 2 (`PRIMARY_SOURCE`)/wall tag 1
(`RIGID_WALL`) is the mesher-adapter lane's job (plan 04 step 3: read `step_import.py` /
`step_mapping.py` first). The exporter refuses missing/ambiguous driver and non-closed solids
(`check_solid`). GUI hooks:
- **Provenance sidecar (to create, repo-side, with the WP14 landing lane)**: exporter/adapter writes
  `step/<name>.inventory.json`: `{tool: "tools/cad/multicell.py", tool_sha, faces: [{"label",
  "count"}], solids: n, closed: true, grid: ["3x3", …]}` (label+count only; a `"tag"` field may be
  added by the adapter lane once real tag assignment exists — the current artifact provides none).
  GUI: run-detail STEP chips render the inventory inline (driver/wall counts + tool SHA) when the
  sidecar exists; without it the chip says "inventory MISSING" — never fabricated.
- **Solve-provenance markers for the mandated validation arm**: `solve_precision="double"` +
  `near_correction=true` must be VISIBLY DISTINCT. Today they ride `SolveSpec.extra` (solve-hash
  distinct) but are NOT echoed into `Response.meta` (verified; gap G-3). GUI displays them from
  `run.json.config` / `config.yaml` immediately (no solver change needed), and the plan
  registers a small WP14-lane ask to echo them into `Response.meta` for per-row provenance parity
  with `cuda_fused`/`mesh_policy`.
- **CUDA-screen gate badge** for multicell runs ("CUDA screens only if CPU-vs-CUDA < 0.2 dB",
  plan `04:480`): a static text rule on the multicell provenance section — the gate itself is
  enforced in the lane, the badge discloses it.

### 3.8 Source plug provenance (WP16 — LANDING; fork keys verified)
The fork emits per-frequency diagnostics ONLY when α≠0: `source_profile="j0_radial"`,
`source_profile_alpha`, `source_profile_path="fused_cuda"`, `source_profile_face_count`,
`assembly_path`. GUI hooks:
- Run detail + compare + leaders: α≠0 records get the badge "source plug α = … (j0_radial, fused
  CUDA)" — click-through shows face count + path. α=0/no-diagnostics records show nothing (absent
  = default, honest).
- **Naming gap (G-4)**: the handoff's `source_plug` provenance field does NOT exist anywhere
  (verified). The WP16 landing lane must either (a) add `source_plug` to dataset record
  `provenance` (additive key, mirrors `mesh_policy` precedent), or (b) the GUI keys on
  `source_profile`/`source_profile_alpha` diagnostics. **Plan adopts (b) as the GUI contract** and
  logs the naming decision as an ISSUES item for the WP16 lane — no invented keys.
- Refusals are user-visible by design (fused-path-only + strict gates): the launch view's preview
  already surfaces CLI errors; nothing extra needed.

### 3.9 Backend/solve-group distinction (WP13 + all of the above)
`/api/compare` :86-101 and `leaders` / campaign leaderboards must never silently mix records with
different solve groups. Hook:
- Define **solve-group fingerprint** computed GUI-side from already-committed data: `(backend,
  mesh_policy, rear_res_factor, band_split edges, cuda_fused, near_correction set, solve_precision,
  source_profile α≠0, mounting, objective_version, freqs_hz grid identity)`.
- `/api/compare` response gains additive `group_a`, `group_b` objects (each key only when
  non-default) + `mixed_keys` (list of keys where the two differ). `viewCompare` :1400 renders a
  warn list "these runs differ in: …" and refuses J-ranking language; the existing DI guard
  (`di_source == "balloon"`, cli.py:1065-1068) stays as-is, its GUI twin prints "DI: cuts estimate —
  not comparable" when false.
- Leaders/typologies view: entries group badges for any non-default group key; `backend: axibem`
  records (when WP13 lands) stay in their own dataset/filter group — a backend filter on
  `/api/leaders` (additive `?backend=`) is the planning hook requested for WP13.

### 3.10 WP17 hook (PLANNED — specify only)
When CUDA near-correction lands (fork staged), the diagnostics must distinguish fused-CUDA
near-corrected from CPU near-corrected records `never mixed silently` (plan 04:21-22). GUI rule
(§3.9 fingerprint already covers it via `near_correction` + `backend`): plus a require-from-lane
note — the WP17 landing must add a discriminative diagnostic (e.g. near-correction path
`cpu|fused_cuda`) since `assembly_path="fused_cuda"` alone is ambiguous with WP15. GUI change:
none beyond the fingerprint; documented as a lane condition.

### 3.11 Mounting badge + enclosure preview (WP12 — PLANNED, owner-gated)
Specified against the mesher's OWN keys (verified names in §2 row 12; never invent keys):
- Brief editor (viewBriefs :1523) gains a `mounting:` block scaffolding (type enclosure,
  depth_mm, margins, edge_mm, plan) — written to the user brief YAML, validated via `load_brief`
  by `gui/data.py::save_user_brief` (:526-548). LANE CONDITION (WP12, mirrors G-4/G-5): this only
  works if the brief schema tolerates the `mounting` block by then — the WP12 lane must extend
  `brief.*` allowed keys first; the GUI scaffolding gates on that.
- Run detail: `mounting: enclosure` badge with depth/edge/plan values (from `config.yaml` or
  planned `provenance.mounting`).
- Mesh preview: `/api/mesh/<run>/<hash>` already serves the mesh; enclosure context comes from
  `mesh_meta.json` (additive reader field when the mesher starts writing it). Rendering an
  enclosure box outline in `view3d.js` is a PLANNED polish item, owner-gated with WP12 itself.

### 3.12 Bake-off view (P6b — PLANNED; hooks now, build on gate)
Exactly per ATH spec (verified, `ATH_SUPERFORMULA_AND_GSA_2026-10-25.md:320,418-426`): route
`#/bakeoff/<id>`; `GET /api/bakeoff/<id>` (§5); new `static/bakeoff.js` (flat file, glob-safe);
race chart bold median + IQR ribbon + faint per-seed lines (log-x evals), final-best ECDF, box
plots per budget slice, budget-normalized table; **statistics in a footnote/table — never a
dashboard headline, no winner implied** (ATH-mandated); **no wall-clock time on any bake-off
x-axis** (this plan's own display rule — ATH's D18 rows carry `wall_s`, the GUI must not chart it).
Both themes. Reader: `runs/bakeoff_<id>/bakeoff.jsonl` + `bakeoff_summary.json`, read-only.

### 3.13 Superformula mouth preview (P6a — PLANNED)
D19 spec: `/api/run/<id>` gains additive `guiding_curve: {phi[], r[], m, dist}` computed pure-math
from the design's `gcurve_*` params (absent for non-gcurve runs — `available:false`-style
omission); run detail renders the mouth outline polar trace labelled "mouth outline m = …" with
the brief envelope as second trace (`ATH…:406-416`). Owner-gated with P6a.

## 4. Workflow maps (user-facing flows, current + planned)

1. **brief → campaign → leaderboard → verify/screen → report → compare → STEP** — all exists
   today (briefs :1523 → launch :1723 → campaigns :507/:554 → run detail :991 → report link :1029 →
   compare :1400 → export-step :1032). Planned additions inside this flow: verify as a GUI job kind
   (G-1), `--bar` judge verdict surfacing in the campaign leaderboard when W4 lands.
2. **QD atlas reading** — exists (WP11). Add qd-block provenance strip (§3.1) + restart strip (§3.2).
3. **restart/QD diagnostics** — per-restart stops + schedule from `run.json.restarts`; pycma log dir
   download links (§3.2).
4. **bake-off** — `#/bakeoff/<id>` from the campaigns/runs surfaces (§3.12); discoverable via a
   "bake-off" list section on the campaigns page listing `runs/bakeoff_*` dirs.
5. **enclosure/mounting previews** — brief scaffolding (§3.11) + badges on results; preview views
   gated with WP12.
6. **multicell STEP** — brief/config carries the multicell source; STEP export chips show named-face
   inventory + tool SHA; the mandated `beat_cpu` double/near-correction validation arm is displayed
   as provenance before any CUDA screen is even possible (§3.7).

## 5. New/extended API contracts

All read-only, all tolerant of missing files, all following the `run_archive` honesty pattern
(`data.py:396-399`: `{"run_id", "available": false, …}` — trigger on absent file / wrong types /
empty cells; route still 200). NaN/Inf → null via `D.clean` :31.

| # | Contract | Shape | Source artifacts |
|---|---|---|---|
| C-1 | **Extend** `GET /api/run/<id>` (additive keys) | `restarts: [ … as-is from run.json ]` (absent when unset), `qd: {…}` (absent when unset), `restart_dirs: ["cma/restart_0", …]`, `step_files` entries gain `inventory` (parsed `<name>.inventory.json` or null) | `run.json`, dir listing, sidecar |
| C-2 | **Extend** `GET /api/compare` (additive) | `group_a`, `group_b` (only non-default keys), `mixed_keys: [key,…]` — computed from the two runs' `config.yaml` + run.json; empty objects when identical | `config.yaml`, `run.json` |
| C-3 | **NEW** `GET /api/bakeoff/<id>` | `available:false` empty pattern; else `{id, algos, budgets, families, summary: bakeoff_summary.json as-is, curves: [{algo, seed, points: [{eval_idx, objective}]}] (decimated to ≤800 pts/series), ecdf: [{algo, values}], boxes}` | `runs/bakeoff_<id>/bakeoff.jsonl` + `bakeoff_summary.json` |
| C-4 | **Extend** `GET /api/run/<id>` (P6a, owner-gated) | `guiding_curve: {phi[], r[], m, dist}` or absent | design params (pure math, no solve) |
| C-5 | **NEW** `GET /runs/<id>/cma/<name>` | raw pycma log file serving by strict allow-list (dir `cma/restart_k/`, extension whitelist — e.g. pycma's `.txt`/`.dat`/`.json2` — never executables, no traversal, same guards as `_report`/`_report_step` :213-227) | `cma/restart_k/*` (download-only, never parsed) |
| C-6 | **Filter** `GET /api/leaders` (P6a/P6b era) | additive `?backend=` — requires a WP13-era `data.py::leaders` reader extension (today it has no such plumbing; NOT pure GUI) | dataset/campaign readers |

jobs.py allow-list change required for C-flow 1 (G-1): add `verify` kind (GPU) mapping to
`verify --run <id> --top N [--brief]` — allow-list edit is contained (`jobs.py:113-141`) and
mirrors existing kinds (`TIERS`/`GPU_KINDS` gain nothing; verify is its own kind). Test note:
also cover the `verify_only`-brief refusal path (`cli.py:523-533`) to complete the pattern.

## 6. Honesty rules (binding, carried over)

- Empty states everywhere: every new view/section has an explicit empty/missing branch (pattern:
  archive :885-905).
- `available:false` (200) for absent artifacts, never fabricated shells; MISSING disclosed as the
  literal word, null-rendered as "–" (`fmt*` helpers).
- No in-process solving; GPU work via the one-GPU job system only (`jobs.py` lock + gpu-clean).
- Every number traceable: displayed J/terms/coverage/provenance read from committed artifacts only.
- Never imply verdicts: compare shows differences; bake-off shows distributions + stats footnote;
  leaders keep the existing ranking rule unchanged.
- Grid-group honesty: solved freq set + weights visible (§3.3); mixed-grid comparisons are
  already refused (`config.py:619-639` is the grid-group *definition*; the enforcement is the
  solve-spec hash + `cli.py:1037-1041` `compare_metrics` raising on differing frequency grids) —
  GUI mirrors with C-2 banners.

## 7. Provenance display contract (the badge matrix)

Every run-detail/leaders/compare view renders a provenance strip; badges appear ONLY when
non-default, else nothing:

| Key (source) | Badge text | Distinct group |
|---|---|---|
| `solve.backend` (run.json/config) | `beat_cuda` / `beat_cpu` / `bempp_cpu` / `axibem` (P6b/WP13-era) | backend |
| `Response.meta.cuda_fused` / diagnostics `assembly_path` | "fused CUDA" | backend refinement |
| `solve.near_correction*`, `solve_precision` (config.yaml until G-3 lands) | "near-corrected · double" | solve fidelity |
| diagnostics `source_profile_alpha` (WP16) | "source plug α=… (j0_radial)" | excitation |
| `mesh_policy: band_split_v1` + `band_edges_hz` | "band-split 3/6 k" | meshing |
| `rear_res_factor` ≠ 1 | "rear ×2" | meshing |
| `mounting: enclosure` (WP12) | "enclosure d=… mm" | mounting |
| `objective_version: 2` | "J v2" | objective |
| `search.restarts.mode` / `search.algorithm: cma_me` | "IPOP ×N" / "CMA-ME" | search |
| STEP inventory sidecar (WP14) | "3×3 STEP · driver=1 wall=N · tool SHA" | geometry source |

Rule (from the plan's dataset rule 04:21-22): records differing in any non-default group key are
NEVER pooled into one comparison verdict; GUI groups reflect this (C-2, §3.9).

## 8. Phased build order (when implementation resumes) + verification

Order chosen so data-committed-but-unviewed capabilities surface first (zero new solver deps);
owner-gated phases are last and gated again at build time.

| Phase | Content | Effort | Risk |
|---|---|---|---|
| G1 | Provenance strip + badge matrix (§3.3, §3.4, §7) — run-detail reader already has everything | ~0.5d | very low |
| G2 | Restarts + qd surfaces: `run_detail` additive keys, restart strip, pycma log raw route (C-1, C-5; §3.1, §3.2) | ~0.75d | low |
| G3 | Compare solve-group fingerprint + mixed warns (C-2); `invalid_envelope` semantics (§3.6) | ~0.5d | low |
| G4 | `verify` job kind (G-1) + STEP inventory chips (C-1 sidecar; §3.7) | ~0.5d | low (verify kind touches jobs.py allow-list — contained, tested) |
| G5 | Bake-off view (C-3, `bakeoff.js`, §3.12) — build on P6b landing | ~1d | medium (gated: P6) |
| G6 | Mounting scaffolding + enclosure badges (§3.11, C-4-adjacent) — build on WP12 owner gate | ~0.75d | medium (gated: WP12) |

Per-phase verification recipe (conventions from `tests/test_gui.py`): fixture `repo` :54-79 builds
tmp run dirs (synthetic `designs/<hash>/`, `search.ndjson` rows via `_row` :47, campaign.json),
`server` fixture :191-202 binds a real thread server, `_req` :205-215 exercises routes offline;
JS gates via the node `--check` parametrize (:342; add `bakeoff.js` to the list when G5 lands);
NO browser automation. New tests per phase:
- G1: provenance keys appear/absent honestly (absent-field ⇒ no badge) — reader + route.
- G2: restarts array passthrough shape, `restart_dirs` listing, raw log route name-guard, 404 on
  path traversal.
- G3: `mixed_keys` computed on two configs differing in one/many keys; DI-guard twin.
- G4: verify-kind argv allow-list + GPU-busy refusal (pattern :159); inventory sidecar parse +
  MISSING chip.
- G5: bakeoff reader on synthetic `bakeoff.jsonl`/`bakeoff_summary.json`; `available:false` pattern;
  decimation bounds.
- G6: brief-mounting scaffolding survives `save_user_brief` CLI validation; badges absent default.
Plus `compileall` + the offline suite each phase; pixel/theme checks inherit GUI_CONTRAST_PLAN
§Verification recipe (both themes, `?theme=` capture).

## 9. Small repo-side gaps this plan depends on (logged in ISSUES, owned by their lanes)

- **G-1**: `verify` missing from the GUI job allow-list (`jobs.py:113-141`) — closed by G4.
- **G-2**: `run.json.restarts`/`qd` never read by any view — closed by G2.
- **G-3**: `near_correction*`/`solve_precision` not echoed into `Response.meta`
  (`solve/beat.py` WIP emits only cuda_fused/mesh_policy/source_motion) — GUI works from
  `config.yaml` meanwhile; per-row echo is a WP14-lane ask, not GUI work.
- **G-4**: `source_plug` provenance field does not exist; WP16 lane decides (a) add it (b) rely on
  `source_profile*` diagnostics. GUI contract = the diagnostics (§3.8); naming decision logged.
- **G-5**: WP17 must emit a near-correction-path diagnostic to keep fused-CUDA near-corrected
  records distinguishable (§3.10) — lane condition, not GUI work.

## 10. GUI_CONTRAST_PLAN compliance

New views/elements inherit: theme boot + `?theme=` capture (§Phase 2), tokens + annotation type
tiers + WCAG table (§Phase 1, §WCAG), semantic/state redundancy (§Phase 6 — every new badge carries
text, never color-only), capture recipe and offline gates (§Verification recipe). No layout/IA
change beyond the additive sections specified here; the nav gains no new top-level entries in
G1-G4 (badges/sections live in existing views); G5's bake-off is reachable from campaigns/runs
plus a glossary-linked hash route — nav-only addition if the owner wants a permanent item.

## 11. Out of scope

Physics/mesher/solver changes (WP14/16/17/12/13 land via their own lanes + gates); surrogate
training/dataset APIs beyond display-side filters; auth/build steps/npm; any change to frozen
contracts, `server.py` security surface, or `jobs.py` beyond the single contained verify-kind
addition (G-1; owner gate = this plan's approval itself — G4 builds only after it); dashboard-style
aggregated health scores (honesty rule).

## 12. Status

Proposed 2026-10-25 (planning pass; inventories verified against tree at 298b56f + disclosed WIP).
Oracle pre-commit review 2026-10-25: **GO-with-fixes** (6 MUSTs — fork-state correction, f11
sentence attribution, STEP label/tag contract, mixed-grid refusal anchor, disclosure completeness,
INDEX phrasing — plus 7 SHOULDs, all applied to this revision; §13 chronology). Owner gates
respected: no WP12/13/P6 code is started by this plan; their hooks are specified only.

## 13. In-flight disclosed (inventory at planning time, 2026-10-25)

- Uncommitted on main (WP14 + M4 debts pattern, disjoint files): `hornlab_search/config.py`,
  `solve/beat.py`, `gui/data.py` (seed-gate memoize `_SEED_GATE_CACHE` :623-645), `mesh/grid_build.py`
  (EOF mesh-cache sketch), `tests/test_config.py`, `tests/test_gui.py`,
  `tests/test_design_generators_grid_half.py`, new `tests/test_solve_near_correction.py`,
  `examples/typologies/salmon_saddle.yaml` (warning note), `pyproject.toml`, `tests/conftest.py`
  (build123d marker), untracked `tools/cad/` + `tests/test_cad_multicell.py`, and untracked
  `examples/briefs/user/7040.yaml` (a GUI-created runtime user brief — disclosed, left alone).
  Owned by the WP14/debts lane — this plan only reads.
- Fork clone `C:\Users\hunte\Hrns\forks\hornlab-beat-bem`: WP16 is **committed** (`f4ef05c`,
  verified in the branch log with its 7-file stat) and **pushed** to
  `ourfork/hornlab-search/wp16-source-profile` (= github.com/llevaachingada/hornlab-beat-bem).
  The checkout currently sits on branch `hornlab-search/wp17-cuda-near` (at `f4ef05c`, zero WP17
  commits) carrying fresh uncommitted WIP in 3 files (`hornlab_beat_bem/config.py`,
  `julia/BeatEngineDriver.jl`, `sweep.py`) — the WP17 lane's scope; verified WP16 key names in this
  doc come from the committed f4ef05c diff. Whether owner gate B ("fork hosting") is met by the
  hosted branch is an owner call, not asserted here.
- The four docs files (`CONTINUITY.md`, `ISSUES.md`, `INDEX.md`, `CODE_MAP.md`) are modified by
  this pass itself and land in its commit set (companion updates, same-commit discipline).