# Report 4. Implementation plan (for an implementing agent)

Senior pass, 2026-10-24. Turns the highest-value findings of Reports 1–3 into work packages (WPs) that a careful
but less senior agent can execute one at a time. **Read this whole file before starting any WP.**

## 0. Ground rules (non-negotiable; from CLAUDE.md / AGENTS.md)

1. Interpreter: `.venv\Scripts\python.exe`. Never bare `python`.
2. **Never hand-edit the installed copies in `.venv`.** Changes to Magnus's packages (Python or Julia) ARE allowed
   (owner decision 2026-10-24), but only in our pinned forks under `C:\Users\hunte\Hrns\forks\` and only by the
   workflow in `docs/FORKS.md`: topic branch, opt-in flag defaulting to today's behaviour, commit, install by SHA,
   pin, validate. WP15–WP17 are fork work packages.
3. **`docs/plan/**` is frozen**, including `01_CONTRACTS.md` (objective, metrics). Do not change the meaning of any
   existing term, metric or default. New behaviour is **opt-in and versioned** (see WP1): with no new keys in a
   YAML, every existing run must reproduce bit-for-bit. The test suite proves it.
4. Every horn number is a YAML default in `examples/`, never hard-coded in Python.
5. Every pushed commit updates `docs/CONTINUITY.md` (new dated entry on top plus the status block) and
   `docs/ISSUES.md`. A new module gets a line in `docs/CODE_MAP.md`; a new doc gets one in `docs/INDEX.md`.
6. GPU work: follow "GPU / Julia hygiene" in CLAUDE.md exactly (clear hosts, record the VRAM baseline, one GPU job at
   a time, `gpu-clean` after). Offline WPs need no GPU. Do them first.
7. Records produced under any new physics, mesh policy, grid or objective version must be distinguishable in the
   dataset (provenance field), and must never be mixed silently into the existing surrogate training group.
8. Each WP ends with: offline `pytest` green (paste the summary), the WP's acceptance checks, and a short evidence
   note in `docs/evidence/` when a GPU number was produced.

Ownership: the wave-era owner table in CLAUDE.md predates this work. Treat these WPs as orchestrator-assigned. If a
WP touches a frozen-contract file (`objective/terms.py`, `metrics/*.py`), **add** new functions and dispatch on the
version; do not edit the existing functions' behaviour.

## 1. Order and dependencies

```
OFFLINE (no GPU, do first)            GPU (after offline)                 FORK (our copy of Magnus's code)
WP1 objective v2 + offline re-score   WP5 far-field / balloon / source    WP15 fused CUDA Burton-Miller (P1)
WP2 brief pins driver (fairness)      WP6 12 kHz screen briefs            WP16 non-uniform source velocity
WP3 shape-only perturb + graded pen.  WP7 rear-shell coarsening           WP17 near-correction on CUDA
WP4 freq_weights + HF grid density    WP8 band-split meshing              (long term: matrix-free GMRES)
WP9 new FREEFORM generators           WP10 GRID family (point grid)
WP9b Le Cléac'h/Kugelwellen (T1,T2)   WP9b organic/elliptical/X (T3-T7, needs WP10)
WP11 BIPOP restarts + QD archive      WP12 enclosure mounting
                                      WP13 axisymmetric BEM backend (owner OK first)
                                      WP14 multicell prototype (CAD → STEP)
```
Highest value per hour: **WP1 → WP15 → WP2 → WP3 → WP6 → WP10 → WP9 → WP8 → WP13**. WP15 is the owner's top
interest (higher-frequency solves on the 4060) and can run in parallel with the offline WPs: it touches only the
fork plus a small solver flag here.

---

## WP1. Objective v2 (detrended ripple, detrended flatness, beam-model DI target) and offline re-score

**Why.** Report 1 F1, F2, F5: about 60–70 % of today's J measures beam taper, source tilt and a DI-formula offset.

**Design.**
- New brief/config key `objective: {version: 2}`; default `1`. Add `"objective"` to the allowed keys in
  `config.load_brief` (`config.py:121`) and carry it into `Config` (e.g. `Config.objective_version: int = 1`).
  `Target.from_dict` stays untouched (it rejects unknown keys by design).
- New metric functions (new names, in new modules or appended, never altering existing ones):
  - `metrics/smoothness.py::ripple_detrended_db(angles_deg, spl_db, target_total_deg, floor_db=-40.0)`:
    ```python
    n = normalized_db(s, s[i0]); keep = coverage_mask(a, cov) & (n >= floor_db)
    if keep.sum() < 7: return nan
    t = np.radians(a[keep]); A = np.column_stack([np.ones_like(t), t**2, t**4])
    coef, *_ = np.linalg.lstsq(A, n[keep], rcond=None)
    return float(np.std(n[keep] - A @ coef, ddof=3))
    ```
  - `metrics/smoothness.py::band_flatness_detrended_db(freqs_hz, on_axis_db)`: residual std (ddof=2) after
    `np.polyfit(np.log2(f), x, 1)` on finite points; NaN if fewer than 4 points.
  - `metrics/di.py::target_di_gaussian_db(cov_h_deg, cov_v_deg)`: numerical DI of the separable Gaussian beam
    `dB = -6.0206·((θ_h/(h/2))² + (θ_v/(v/2))²)` on a sin θ-weighted full-sphere grid, with θ_h = atan2(x, z) and
    θ_v = atan2(y, z). The reference implementation is `di_gauss` in
    `docs/research/senior_pass_2026-10-24/evidence/objective_assumption_checks.py`. Cache with `functools.lru_cache`.
- `MetricSet` is frozen: put the new per-frequency arrays in `scalars` as report keys and in a new
  `metrics_v2` dict on the Evaluation/ndjson row, **or** compute them inside the v2 objective from the `Response`.
  Prefer the latter: `objective_v2(metrics, resp, ok, target, weights)` in a new `objective/scalar_v2.py`.
- `objective_v2` terms: `cov` (unchanged), `rip` = mean_f(ripple_detrended_h + ripple_detrended_v),
  `di` against `target_di_gaussian_db` (or skipped if weight 0), `dislope` (unchanged), `flat` =
  `band_flatness_detrended_db`, `load` (unchanged). Same key set, `PENALTY_*` and never-raise contract as v1.
- Dispatch at the single call site `search/evaluate.py:617`: version 1 calls `objective(...)`; version 2 calls
  `objective_v2(...)`. Record `objective_version` in every ndjson row and in `run.json`.

**Offline re-score tool** `tools/rescore/rescore_v2.py` (new): walk `runs/*/designs/*/response.npz` and the dataset
store, rebuild the `Response`, compute v1 and v2 J for each record, and write a CSV plus a markdown summary: per
campaign family, the v1 and v2 medians, Spearman ρ(v1, v2) over all designs, and whether each "Claimed" line in
`docs/evidence/TYPOLOGY_COMPARE_2026-10-23.md` survives. **This needs no GPU and decides whether old conclusions
stand.** Full polars and balloons are stored per design [verified: `response.npz` keys spl_h_db, spl_v_db,
spl_balloon_db, p_h, p_v, z_throat].

**Tests** (`tests/test_metrics_smoothness_v2.py`, `tests/test_objective_v2.py`):
- an ideal Gaussian and a cosⁿ taper → `ripple_detrended_db` < 0.05 dB; the same plus a ±1 dB alternating ripple → ≈ 1 dB.
- a pure −3 dB/oct tilt → `band_flatness_detrended_db` < 1e-9; tilt plus ±0.5 dB → ≈ 0.5.
- `target_di_gaussian_db(90, 90)` ≈ 10.33 ± 0.05; (90, 60) ≈ 11.91; (75, 45) ≈ 13.76.
- **v1 reproduction:** with no `objective` key, `objective()` output is identical to before (golden values from
  `tests/test_objective_scalar.py` still pass unchanged).
- v2 never raises and never returns NaN or inf (fuzz with NaN-laden inputs, like the v1 tests).

**Acceptance.** Offline suite green; re-score report written to `docs/evidence/OBJECTIVE_V2_RESCORE.md`, with rank
changes shown for the top 20 designs of each family; owner decides whether v2 becomes the brief default.

## WP2. Briefs pin the driver for native families (fairness)

**Why.** Report 1 F3, B2, B5, B7.

**Steps.**
1. In `config.load_config`, after a brief is merged and `generator` is None, if the family is OSSE or R-OSSE (or ICW
   with `r0_mm`/`a0_deg` keys): force `seed_params.r0_mm = driver.exit_radius_mm` and `bounds.r0_mm =
   {lo=hi=value, search: false}`. If the config's own pinned `r0_mm` differs by more than 0.01 mm, **raise
   ConfigError** with a clear message: silently rescaling a horn is worse.
2. New brief key `driver.throat_angle_policy: pin | free` (default `pin` for new briefs; **absent means the old
   behaviour** so old runs reproduce). `pin` fixes `a0_deg` to `exit_angle_deg`.
3. FREEFORM native configs: pin `profileH/V.throatAngleDeg` to the exit angle under `pin`.
4. New report scalar `throat_angle_mismatch_deg` (|a0 − exit angle|) in `search/evaluate.py` for every family. It is
   report-only.
5. `examples/catalog.yaml`: mark `osse_baseline` as tied to `osse_75x45.yaml` (1.4"); the campaign should SKIP it
   under 1" briefs with the reason printed.

**Tests.** A brief with a 12.7 mm exit applied to `osse_baseline.yaml` raises; applied to `rosse_baseline.yaml` with
`pin` gives `a0_deg` pinned at 5.0; without the new key, the loaded Config equals today's (snapshot compare).

## WP3. Shape-only perturbations and graded infeasibility

**Why.** Report 1 F11 (30–40 % invalid-geometry rates, flat 1e3 plateau).

**Steps.**
1. `profiles.py`: add `perturb_increments_shape(anchors, u, u_max)`, the same as `perturb_increments` but rescale
   `new_d *= d.sum() / new_d.sum()` so the mouth radius is unchanged. Registry: generator block `perturb: {mode: shape}`
   (default `mode: legacy` reproduces today). Mouth size then comes from the parent's own knobs.
2. Pre-mesh envelope check for generators: after `materialize`, compute mouth W/H and depth from the anchors plus
   `wall_thickness_mm` (the 15 mm depth allowance stays). On violation return a **graded** penalty
   `PENALTY_INVALID + 100·max_relative_overshoot` (capped at `2·PENALTY_INVALID`) with kind `invalid_envelope`.
   Keep `PENALTY_INVALID` as is for other invalid kinds. This needs a new constant and a version switch:
   `search: {infeasible_penalty: graded}` (default `flat`).

**Tests.** The shape perturbation keeps the mouth radius within 1e-9; the graded penalty is monotone in overshoot,
finite, and > any valid J; with defaults, old behaviour holds.

## WP4. Per-frequency weights and HF frequency density

**Why.** Report 1 F6, F7, F10.

**Steps.**
1. Implement `Target.freq_weights` under objective v2 only (v1 keeps ignoring it, but **log a WARNING once** if it is
   set under v1, so it is no longer silent). Schema: `{band_hz: [[lo, hi, w], ...]}`; a frequency gets the product of
   the matching weights, default 1. Apply in every `_mean` of v2 as a weighted mean.
2. Add a `verify_hf` grid option: briefs may set `grid: {verify_points_per_octave: 8}` to build a verify grid that is
   the frozen verify grid **plus** extra log points in [5 kHz, band_hi] at that density. It is a new grid group
   (the grid check already separates it).
3. Document in `docs/TYPOLOGY_PLAN.md` (append a dated note): screens rank coarsely; finalists are re-ranked on the
   denser verify grid.

## WP5. Measurement pack: far field, balloon resolution, source sensitivity (GPU, about 1 h)

**Why.** Report 1 F8, F9; Report 3 section 7. All three are measurements before any change.

**Steps** (3 finalists: osse_axi best, perturbed_osse_hv best, rosse best; a clean GPU state per job):
1. Solve once with `surface_traces=True` (`BeatBackend.solve_traced`). Using `solve/traces.py`, evaluate the field at
   2 m, 10 m and 50 m; report Δbeamwidth (H/V) and ΔDI per frequency. Normalise level by r. If the existing traces
   module cannot evaluate arbitrary points, re-solve with `distance_m` 10 and 50 instead (3 solves per design).
2. Balloon 512 vs 1,024 vs 2,592 (36×72): ΔDI per frequency.
3. `source_motion: "axial"` vs `"normal"`: Δbeamwidth above 5 kHz. (Expose it as an optional `solve.source_motion`
   key; default `normal` = today.)

**Acceptance.** `docs/evidence/MEASUREMENT_PACK_<date>.md` with tables. Decision rules: if |Δbw| > 1° between 2 m and
50 m, propose `distance_m: 10` for v2 briefs; if |ΔDI| > 0.1 dB from 512 → 1,024, raise the screen balloon.

## WP6. 12 kHz screening briefs for 1" horns (GPU)

**Why.** Report 3 H1: it fits today.

**Steps.** Copy `examples/briefs/axi_90x90_1in.yaml` and `hifi_90x60_1in.yaml` to `*_12k_search.yaml` with
`band_hi_hz: 12000` and no `verify_only`. Fix the misleading comment in the existing `_12k.yaml` files. Run one
`search` with budget 20 on `osse_axi` and `perturbed_osse_hv`, record seconds/candidate, peak VRAM and dofs, and
confirm no `mesh_too_large`. Then a screen campaign if under 45 s/candidate. Print the f11 caveat in the report header.

## WP7. Coarser rear/outer shell (GPU check)

**Why.** Report 3 H3. **Steps.** Add `mesh.rear_res_factor` (default 1.0 = today) used by `res_mm_for` callers to scale
the `rear` resolution only. Measure 1.0 vs 1.5 vs 2.0 on the WP5 finalists: dofs, J, Δon-axis, Δbeamwidth, ΔDI at the
top frequency. Adopt the largest factor within the CP-7f bar (0.039 dB on-axis; 1° beamwidth; 0.1 dB DI) as a v2
default. **First** check which surfaces the mesher's `rear` size actually applies to: read `MeshDensity` in
`hornlab_mesher/geometry.py` (it has `rear`/`back` sizes [verify]).

## WP8. Band-split meshing (GPU check)

**Why.** Report 3 H2 (25–40 % of solve time). **Steps.**
1. `mesh.band_split: {edges_hz: [3000, 6000]}` (absent = today).
2. In `search/evaluate.py`, mesh once per band (`mesh_spec` with `f_max_hz` = band top; cache key includes the band),
   solve each band's frequencies on its mesh, and stack Responses in frequency order (reuse `solve/beat.py::_stack`
   ideas; write a small `stack_responses` in `solve/base.py`).
3. Seam check: the first frequency above each edge is also solved on the lower band's mesh, in verify mode only, and
   the difference is stored in `meta`.
4. Provenance: `mesh_policy: band_split_v1` in each record.

**Acceptance.** On two designs, J and per-frequency metrics within the CP-7f bar of the single-mesh solve; wall time
reported.

## WP9. New FREEFORM generators (offline, then a GPU smoke)

**Why.** Report 2 G1–G6. All live in `design/generators/profiles.py` + `registry.py` (new `TYPES`), each with a config
under `examples/typologies/` and a catalog entry.

1. **`splice`** (G2): `profile_h: {type: splice, first: {type: osse}, second: {type: tractrix}}` plus knob
   `{p}_zs_frac` ∈ [0.2, 0.8]. Build both parents from r0. Second parent: translate it in z so its radius equals the
   first's at z_s, and find its point with the same wall angle (search θ along the second meridian; if no match within
   2°, use a C¹ Hermite bridge over 10 % of L). Output one meridian; test C¹ continuity (Δθ < 0.5° at the joint).
2. **`throat_blend_mm`** (G3) for conical, exponential, hypex, tractrix: over [0, L_b] blend
   `r = (1−w)·r_OS(z) + w·r_cls(z)` with `w = smoothstep(z/L_b)`, where `r_OS` is the OS meridian with a0 = driver exit
   and the same far-field angle as the classical profile at L_b. Default 0 reproduces today exactly (test that).
3. **`spherical_salmon`** (G4): implement the march in Report 2 section 3 (`profiles.spherical_salmon(r0_mm, fc_hz,
   T, theta0_deg, max_wall_deg, dx_mm=0.25)`). Tests: area law satisfied at every step (rel. error < 1e-6); z strictly
   increasing; θ monotone; a plane-wave limit check. Keep `lecleach()` disabled. The rename gate (match a published JMLC
   table within 0.5 mm) is an owner task.
4. **`angle_space`** (G6): θ(s) = θ_OS(s) + Σ_{k=1..K} c_k·cos(kπ s/L) with s = z/L; integrate r(z) = r0 + ∫tan θ dz
   (trapezoid, 2,000 steps); clip θ to [−max_wall, max_wall]; then optional scaling to a mouth-radius knob by
   adjusting L with brentq. Knobs `{p}_c1..{p}_cK` ∈ [−10°, 10°], K = 4 default.
5. **Presets** (G1): `os_conical.yaml` (OSSE meridian with `s: 0`), `qt_rect.yaml` (OS meridians in H and V, rounded
   rectangle mouth), `catenoidal.yaml` (hypex T = 0 pinned).

Tests: the existing generator test style (`tests/test_design_generators_profiles.py`): Hermite fidelity within
0.2 mm, envelope refusal, knob → params determinism. GPU smoke: one `run` per new typology at screen.

## WP9b. Le Cléac'h family, organic/elliptical horns and X-shapes (owner request 2026-10-24)

Goal: the curled-lip Le Cléac'h horns (axisymmetric JMLC, elliptical JMLC, Iwata/FH-N2, Ferguson/toroidal), the
Kugelwellen, Gerstgrasser's "Min-Phase" (Le Cléac'h × OS), and audiohorn.net-style X-shapes, as searchable typologies.
Depends on WP10 (GRID adapter); T1 and T2 can be built and unit-tested before WP10 exists.

### 9b.0 Sources actually read, and what each gives (all checked 2026-10-24)

| Source | What it gives us | Status |
|---|---|---|
| **J. Fourcade, "Calcul du Pavillon Le Cléac'h", 14 Apr 2015** (16 pp., French; `unepassionaudiophile.fr/wp-content/uploads/2018/01/Pavillon-JMLC.pdf`) | **The exact Le Cléac'h construction (eqs 10–27)**, the JMLC 2007 spreadsheet recurrence (eqs 1–8) and its derivation, the offset-profile formula for wall thickness (28–29), and **a numerical reference case** (fig. 7 + table p.13). | primary/secondary, verifiable; **this satisfies the R9 gate** |
| J.-M. Le Cléac'h, "Acoustical horns and waveguides", ETF 2010 lecture (128 slides, rintelen.ch) | Tractrix as a spherical-cap law A = 2πR²(1−cos α) (p.77); Kugelwellen = same idea with **twice** the tractrix radius (p.78, Rösch/Klangfilm; H. Schmidt, *Funk und Ton* 5, 1950); the JMLC method slide (p.82, figure only); Le Cléac'h vs OS isobars (pp.97–99, 122); multicell and sectoral horns (pp.111–118); **Gerstgrasser Min-Phase horn = Le Cléac'h/OS compromise** (pp.125–127). | primary (author) |
| B. Kolbrek, "Horn Theory: An Introduction, Part 2", audioXpress 2008 | **Kugelwellen equations 18–22** (below); its wavefronts are *not* normal to the wall; it folds back; JMLC's principle described (equidistant wavefronts normal to wall + Salmon law); OS r = √(r_t² + tan²θ0·x²). | secondary, peer-reviewed magazine |
| J.-M. Le Cléac'h, diyAudio thread 140190 p.40 (posts by "Jmmlc", 2010) | The two JMLC rules in his words (wavefront i parallel/equidistant to wavefront i−1; wavefronts orthogonal to walls); **"quasi Iwata": keeps the original Iwata's width/height-ratio evolution throat→mouth and T = 0.5**; non-axisymmetric versions were made as 3-D point clouds (spreadsheets > 100 MB); hypex T = 0.707 gives the most resistive throat impedance; **driver exit angles are quoted as DOUBLE (included) angles**; a mismatch between driver exit and horn throat angle causes ripples near the throat. | primary (author, forum) |
| sphericalhorns.net (2019, 2020) | Kugelwellen formulas (agree with Kolbrek); a JMLC-inspired calculator (self-declared not identical to JMLC) | secondary; used only as a cross-check |
| audiohorn.net (X-Shape pages) | The X-Shape is designed by in-house FEA for constant directivity on both axes and "true loading" (lower crossover than OS). **No geometry is published.** | marketing; geometry below is OUR hypothesis |

### 9b.1 Why these horns look the way they do (physics, short)

1. **Curled lips (rollback past 90°).** A JMLC/Kugelwellen wall keeps turning so it stays normal to the growing
   wavefront. Past 90° it curls back toward the driver. The mouth is then not an edge but a smooth surface wrapping
   around the wavefront, so the impedance step to free air is gradual. That means low mouth reflection (smooth
   response, little "horn sound") and weak edge diffraction. Fourcade's table shows the gain: the same horn stopped at
   90° has a 0.13 m² mouth wavefront; stopped at 360° it has 0.72 m², with the overall length unchanged.
2. **Organic/saddle mouths (elliptical JMLC, Iwata, FH-N2).** With different coverage horizontally and vertically, the
   wavefront grows faster sideways. Each azimuth's wall reaches 90° (and starts curling) at a different distance
   from the throat, so the lip curls at different depths around the mouth: the mouth edge becomes a 3-D saddle.
   Iwata additionally changes the width/height ratio along the horn, hence the twisted, flowing look.
3. **X-shapes (audiohorn.net).** No published geometry. Our physical reading [inferred]: a near-rectangular coverage
   pattern needs the diagonal directions to keep up with the sides. Extending the diagonals ("arms") gives the corner
   wavefront the same rollback room as the sides and spreads the mouth diffraction over many depths instead of one
   ring. That is a hypothesis to test with the BEM, not a known result.
4. **Min-Phase (Gerstgrasser).** An OS waveguide (good directivity control) whose mouth begins curling much earlier
   (ETF slide p.126). That keeps OS directivity while borrowing JMLC's low-reflection mouth.

### 9b.2 New typologies (generator names, knobs, construction)

All lengths in mm, angles in degrees. Every typology takes its throat from the brief: `r0 = driver.exit_radius_mm`,
`phi0 = driver.exit_angle_deg` (a **half**-angle; JMLC's driver tables give the included angle, so divide by 2).

**T1 `lecleach` (axisymmetric JMLC, exact formulation).** Port of `docs/research/senior_pass_2026-10-24/evidence/jmlc_reference.py`
into `design/generators/profiles.py` as `lecleach_exact(r0_mm, fc_hz, T, phi0_deg, stop_deg, dl_mm=1.0, c=C_AIR)`:
```
R0 = r0 / sin(phi0);  S0 = 2π R0² (1 − cos phi0);  m = 4π fc / c                     (Fourcade 11, 13, 43)
S(l) = S0 [cosh(m l/2) + T sinh(m l/2)]²                                            (42)
start: x0 = 0, y0 = r0, φ0 = phi0; l_i = i·dl
for i = 1, 2, ...:
    acc  = 2π (R0 + l_i)² (1 − cos phi0)                                            (15) spherical core
    acc += Σ_{k=1}^{i−1} 2π h_k (h_k sin φ_{k−1} + y_{k−1}) dα_{k−1},  h_k = l_i − l_{k−1}   (20) earlier rings
    S_ii = S(l_i) − acc                                                             (22) new compensating ring
    r_i  = dl sin φ_{i−1} + y_{i−1}                                                 (23)
    dα_{i−1} = S_ii / (2π r_i dl)                                                   (24)
    φ_i = φ_{i−1} + dα_{i−1};  x_i = x_{i−1} + dl cos φ_i;  y_i = y_{i−1} + dl sin φ_i   (25–27)
stop when φ_i ≥ stop_deg
```
The ring sum is O(i), so the whole march is O(n²): 500 steps take milliseconds; vectorize the sum with numpy (see
the reference file). Output: the meridian as arc-length samples (x, y, φ), which is **not** a function y(x) past 90°.
Knobs: `fc_hz` (300–1,200 for a 1" driver), `T` (0–1; 0.5 Iwata, 0.707 hypex, 0.8 JMLC default), `stop_deg`
(90–270; above ~270° the curl nearly closes on itself, see 9b.4). Re-enable the `lecleach` name only when the
validation test below passes (R9 gate satisfied by Fourcade's published table).

**Validation (unit test, offline).** Fourcade fig. 7: fc 400 Hz, T 0.8, throat Ø25.4 mm, exit half-angle 8°,
dl 1 mm, c 344 m/s, stop 360°.

| quantity | published | our reference implementation (2026-10-24) | test tolerance |
|---|---|---|---|
| L0 (arc length at stop) for stop 90/180/270/360° | 394 / 467 / 496 / 511 mm | 394 / 467 / 496 / 512 mm | ±2 mm |
| mouth wavefront area S(L0), stop 90/180/270/360° | 0.13 / 0.38 / 0.57 / 0.72 m² | 0.131 / 0.379 / 0.579 / 0.732 m² | ±2 % |
| overall length (max x) | 321.35 mm | 321.41 mm (dl 0.5: 321.46) | ±1 mm |
| overall width (2·max y) | 467.30 mm | 471.31 mm | ±1 % (**open item**: 0.9 % gap, see below) |
| "throat cone angle" | 8.55° | (definition differs; our φ dips to 4.3° in the first mm) | report only |

Open item: our width is 0.9 % larger, and the program's "throat angle" definition is unknown (its source is in
`AxialHorn.zip`, which we do not have). Likely a different first-step convention (sphericalhorns notes adding
the first outer element one step later). Try that variant; if it closes the gap, adopt it. Otherwise ship with ±1 %.

**T2 `kugelwellen` (Klangfilm spherical-wave horn; Kolbrek eqs 18–22).**
```
r_k = c / (π fc)                 # constant wavefront sphere radius (= 2 × tractrix radius c/(2π fc))
h0  = r_k − √(r_k² − r0²)        # throat cap height
m   = 4π fc / c
for x from 0 upward (x = axial distance of the wavefront apex from the throat apex):
    h  = h0·e^(m x)              # area 2π r_k h grows exponentially
    y  = √(2 r_k h − h²)         # rim radius (wall)
    xw = x − h + h0              # rim axial position (wall)
stop at h = 2 r_k (closed sphere) or at a chosen fold-back angle
```
The wall reaches 90° at h = 1/m = r_k/4 (y = (√7/4)·r_k ≈ 0.661 r_k, the axial maximum of x_w). It then folds
back, reaches 180° at h = r_k (y = r_k, the maximum radius) and closes at h = 2 r_k [verified numerically
2026-10-24, fc 800 Hz, r0 12.7 mm]. The wavefronts are not normal to the wall (Kolbrek), so expect slightly more
mouth reflection than JMLC; that is a reason to include it as a comparison. Requires r0 < r_k. Knobs: `fc_hz`,
`fold_deg` (stop angle, 90–240). Tests: those three landmarks within 0.5°/0.1 mm; x_end = ln(2 r_k/h0)/m.

**T3 `jmlc_elliptical` (Level-1 elliptical JMLC, per-azimuth meridians).** Build one T1 meridian per azimuth φ with
its own cutoff:
```
1/fc(φ) = cos²φ / fc_h + sin²φ / fc_v      # larger fc → narrower; fc_h < fc_v for a wide-horizontal horn
```
(same T, same throat). Rows are equal-**l** (same wavefront index), so row j of every φ belongs to the same
wavefront index; the mouth edge is the set of each row's last point, which sits at different (x, y) per φ: the
saddle. Stop rule per φ: `stop_deg` (same angle all around, the natural choice), or `L0` common. Knobs: `fc_h_hz`,
`fc_v_hz`, `T`, `stop_deg`. Level 1 is an approximation: true 3-D JMLC also keeps wavefronts parallel *across*
azimuths, which per-azimuth 2-D marches do not enforce. Report it as "JMLC-type elliptical", not as JMLC's own.

**T4 `jmlc_iwata` (quasi-Iwata / FH-N2: width/height ratio law + T = 0.5).** Area-preserving elliptical stretch of
an axisymmetric T1 meridian, which keeps JMLC's wavefront-area law exactly in the cross-section-area sense:
```
AR(l) = AR_t + (AR_m − AR_t)·(l/L0)^p            # width/height ratio, throat → mouth (Iwata: AR_t ≈ 1)
y_h(l) = y(l)·√AR(l),  y_v(l) = y(l)/√AR(l)      # π·y_h·y_v = π·y² (area preserved)
x is shared: x_h(l) = x_v(l) = x(l)
intermediate φ: superellipse of exponent n(l) = 2 + (n_m − 2)·(l/L0)^q   (quasi-rectangular mouth)
```
Knobs: `fc_hz`, `T` (default 0.5 per JMLC), `AR_m` (1.2–2.5), `p` (0.5–3), `n_m` (2–6), `stop_deg`. This is our
reconstruction of the published *principle* (ratio evolution + T = 0.5). JMLC's own Iwata point clouds are not
public; say so in the catalog description.

**T5 `x_shape` (hypothesis, audiohorn-inspired).** T3 or T4 plus a diagonal term on each azimuth's construction
length and stop angle:
```
stop(φ) = stop_deg·(1 + x_amp·cos 4φ')      with φ' = φ − 45° so the maxima sit on the diagonals
fc(φ)  from T3, optionally × (1 − x_fc·cos 4φ')  (diagonals flare slightly faster)
```
`x_amp` ∈ [0, 0.4], `x_fc` ∈ [0, 0.3]. x_amp = 0 must reproduce T3/T4 exactly (test). cos 4φ is even about both
mirror planes, so the quarter model stays valid.

**T6 `min_phase` (Gerstgrasser-style OS + early curl) [inferred from ETF slides 125–127; no formula published].**
OS meridian `r(x) = √(r0² + tan²θ·x²)` (Kolbrek eq 23; OSSE with s = 0) from the throat to a switch point `x_s`, then
continue with a JMLC-type curl. Implementation: from x_s, run the T1 march initialized with the OS point and
angle (y = r(x_s), φ = atan(dr/dx)) and an S0 equal to the spherical-cap area through that point (R = y/sin φ). This
is the WP9 `splice` idea applied to a curl. Knobs: `cov_half_deg` (θ), `xs_frac`, `fc_hz`, `T`, `stop_deg`.

**T7 `toroidal_rollback` ("Ferguson"-like ring mouth).** T1 with stop 180–240° plus a large wall radius at the lip
(`wall_thickness_mm` 6–12, rounded by the shell offset). Mainly a geometry preset of T1 for the catalog; list it so
users can find the look.

**T8 (research, optional) `jmlc_3d`: true 3-D parallel-wavefront construction.** Wavefront surface W_i (triangulated)
→ offset by dl along its normals → add a rim strip whose angular growth dα(φ) is split around the rim to keep the
total area on S(l) and steer the rim aspect toward AR(l). Eikonal/level-set flavoured. Do it only if T3/T4 results
justify it.

### 9b.3 Geometry pipeline (GRID route)

1. **Rows.** For quarter models, φ_j = 0…90° with n_phi ≥ 13 (≥ 25 when x_amp > 0). For each φ_j the generator returns
   (x, y, φ) samples on the arc-length grid. Resample every row to the **same n_s** by normalized arc length (use
   l/L0(φ), so row k is "the same fraction of the horn" for every φ). The point grid needs a rectangular (n_phi × n_s)
   array.
2. **3-D points.** For T3/T5 each row's radius is used directly at its azimuth: `P = (y·cos φ, y·sin φ, x)`. For T4:
   `P = (y_h(l)·cos θ_s, y_v(l)·sin θ_s, x(l))`, where θ_s traces the superellipse of exponent n(l). Units: mm (the GRID
   adapter converts as WP10 specifies).
3. **Non-monotone x.** Past 90° x decreases along a row. The point grid stores 3-D points per row, so this is
   representable (Magnus's R-OSSE rollback already produces such grids). **Verify** with one T1 horn at stop 200°
   before anything else; if the builder assumes monotone z, that is a fork change (FORKS.md) in the mesher, not a
   reason to drop rollback.
4. **Wall thickness / outer shell.** Offset the profile along the in-plane normal by t (Fourcade eq 28–29:
   `x_d = x + t·cos(φ + π/2)`, `y_d = y + t·sin(φ + π/2)`) and pass it as `outer_points`, or let the mesher offset.
   Check the curl's inner gap: the minimum distance between any two non-adjacent points of a row (and its offset)
   must be ≥ 2t + 2 mm, otherwise refuse (`GeneratorError`, a graded infeasible penalty per WP3).
5. **Source.** JMLC's throat wavefront is a spherical cap of radius R0 = r0/sin φ0, which is exactly our
   `source.cap: auto` (r0/sin θ_throat). Keep `auto`.
6. **Envelope.** Use the meshed bbox as now; rollback adds width, not depth, so curled horns need wide, shallow
   envelopes.

### 9b.4 Limits and failure modes to test for

- **Stop angle.** At 360° Fourcade's horn has a nearly closed spiral: thin air pockets and self-approach. Default
  `stop_deg` ≤ 240; bounds [90, 270].
- **Size versus cutoff.** fc 400 Hz on 1" gives ≈ 470 mm wide and 320 mm long. For the 1" briefs use fc 600–1,200 Hz
  (smaller, and the band starts at 700 Hz anyway).
- **dofs.** The curled lip roughly doubles the radiating surface over a 90°-stopped horn of the same width. Screen at
  f_max 4–5.5 kHz on the current CUDA path; 8–12 kHz only after WP15 (fused CUDA) or on `beat_cpu`.
- **Thin gaps** between the curl and the outer shell behave like thin septa (near-singular quadrature): validate one
  design on `beat_cpu` with `near_correction=True` before trusting CUDA screens (as WP14).
- **Throat mismatch.** If `phi0` (driver) differs from where the law wants to start, the profile ripples in the first
  millimetres (JMLC's own remark; our reference dips from 8° to 4.3°). Report `throat_angle_mismatch_deg` (WP2).

### 9b.5 Files, tests, catalog

- `design/generators/profiles.py`: `lecleach_exact`, `kugelwellen`, helper `resample_by_arclength`; keep the old
  `lecleach()` raising until T1's validation test passes, then route `lecleach` to `lecleach_exact`.
- `design/generators/grid.py` (WP10) gains row builders `rows_axisym(meridian)`, `rows_per_azimuth(fc_of_phi, …)`,
  `rows_ar_stretch(meridian, AR, n_exp)`, `x_shape_modulation(...)`.
- Tests (`tests/test_design_generators_lecleach.py`, `..._kugelwellen.py`, `..._grid_organic.py`):
  Fourcade table (above); Kugelwellen closed-form checks; T3 with fc_h = fc_v equals T1 at every φ (≤ 1e-9 mm);
  T4 with AR_m = 1 and n_m = 2 equals T1; T5 with x_amp = 0 equals T3/T4; quarter-symmetry of every grid
  (mirror rows match within 1e-9); the self-approach refusal; arc-length resampling keeps endpoints exactly.
- `examples/typologies/`: `lecleach.yaml` (replace the gated stub), `kugelwellen.yaml`, `jmlc_elliptical.yaml`,
  `jmlc_iwata.yaml`, `x_shape.yaml`, `min_phase.yaml`, `toroidal_rollback.yaml`; catalog group `organic`
  (axisymmetric ones also usable under axi briefs). Starting bounds for 1": fc 600–1,200 Hz; T 0.3–1.0;
  stop 120–240°; fc_v/fc_h 1.0–2.0; AR_m 1.2–2.2; x_amp 0–0.35.
- Brief `examples/briefs/organic_rollback_1in.yaml`: 90×60, band 700–5,500 Hz, envelope about 520×420×260 mm
  (wide and shallow), `source.cap: auto`, objective v2 once WP1 lands.
- Evidence `docs/evidence/ORGANIC_SMOKE_<date>.md`: one screen run per typology, with screenshots from the GUI 3-D
  view and the CPU near-correction check of one curled design.

### 9b.6 How the owner runs them (after WP9b + WP10 land)

```
hornlab-search families --brief examples\briefs\organic_rollback_1in.yaml
hornlab-search campaign --brief examples\briefs\organic_rollback_1in.yaml --families organic --tier screen
hornlab-search gui            # Typologies page / 3-D view to see the shapes; Export STEP for renders
```

## WP10. GRID family via the mesher's point-grid builder

**Why.** Report 2 section 4: the single biggest shape-space expansion.

**Steps.**
1. **Read first:** `hornlab_mesher/geometry.py:214-333` (`PointGridHornGeometry`), `mesher.py:207`
   (`build_mesh_with_info`), `builders/point_grid_dispatch.py:285`, `MeshDensity`, and how `mesh/build.py` builds
   FREEFORM today. Write down in `NOTES_FOR_SENIOR.md` (append-only) which fields you set and why.
2. `design/generators/grid.py` (new): `grid_points(spec, knobs, brief) -> (inner_points (nφ, ns, 3) mm, meta)` using
   the radius field in Report 2 section 4. Meridians come from existing generators (`build_meridian`). Start with
   **G8 (even Fourier cross-section)** and **G9 (φ-varying termination)**, both quarter-symmetric. Leave twist (G12)
   and up/down asymmetry (G11) for later, since they need other quadrants.
3. `mesh/grid_build.py` (new): call `build_mesh_with_info(PointGridHornGeometry(inner_points=..., closed=False,
   symmetry_planes=("x","y"), wall_thickness_mm=..., source_shape=..., ...), density)` and return the same
   `MeshResult` as `mesh/build.py`. **Reuse** the existing post-mesh checks (metre scale bbox 0.1–1 m, symmetry plane
   from `SYMMETRY_PLANE`, topology). Pin guard test like `tests/test_mesh_pin.py`.
4. A new pseudo-family `GRID` in `design/families.py`, or route through the generator path with
   `generator: {name: grid}`; prefer the generator path (it already carries provenance and the brief).
5. Validation: a GRID horn with zero modulation must reproduce the equivalent FREEFORM horn's J within the CP-7f bar
   (same meridians, ellipse section). **Do not skip this:** it is what proves the adapter is not silently wrong.

## WP11. Search upgrades: restarts and a quality-diversity atlas (offline + GPU)

1. `search.restarts: {mode: bipop, max: 4}` (absent = today). Implement with pycma's `cma.fmin2` or a manual IPOP loop
   around `CMAEvolutionStrategy`. Each restart records its own generation log, and budget accounting stays as now.
2. `search.algorithm: cma_me` using `pyribs` (MIT; add it to an optional extra in `pyproject.toml`). Archive
   descriptors from the Evaluation's metrics: (mean bw_h, mean bw_v) over the band, or a brief-chosen pair. Write
   `archive.json` and a GUI-ready heatmap. Budget semantics as in `search/cma.py`. Acceptance: on a cheap family
   (exponential, 2 knobs) the archive covers more than 50 % of cells reachable by a grid scan.

## WP12. Enclosure mounting (GPU)

`brief.mounting: {type: enclosure, depth_mm, margins_mm, edge_mm, plan: rounded_rectangle}` (absent = freestanding =
today). In `design/families.py:443` pass mode `enclosure` and the enclosure block, using the mesher's own config keys
(read `config_parser.py:860-960` and `geometry.HornEnclosure`). First test that the quarter model meshes. Measure the
dof increase and compare J freestanding vs enclosure on two finalists. Records carry `mounting` in provenance.

## WP13. Axisymmetric BEM backend (owner approval required first)

Report 3 section 5. **Ask the owner**: is a third-party GPL-3.0 solver acceptable as a backend? (bempp is the
precedent.) If yes:
1. Vendor nothing. Add AcousticBEM as an optional dependency (`pip install` from its repo at a pinned SHA, recorded
   in `TOOLCHAIN.md`).
2. Confirm in its source which axisymmetric exterior formulation exists (Burton-Miller or CHIEF) before writing the
   adapter.
3. `solve/axibem.py`: input is the meridian polyline (inner wall → lip → outer shell → rear) from the generator, plus
   the source segment; output a `Response` with H = V cuts and a θ-only DI (a balloon is optional).
4. Gates: analytic sphere; vs `beat_cuda` on 3 axi designs, 0.5–5.5 kHz, < 0.2 dB on-axis and < 1° beamwidth;
   own dataset group (`backend: axibem`).

## WP14. Multicell prototype (after WP10; CPU validation mandatory)

Report 2 section 5. Optional dependency `build123d` or `cadquery`. Script `tools/cad/multicell.py` builds the solid
(N_h×N_v, septum thickness ≥ 1.5 mm, septum start z_s) and exports STEP with named faces. Read `hornlab_mesher/step_import.py`
and `step_mapping.py` to learn how a face becomes the source tag **before** writing the exporter. Mesh, then solve a
3×3 at f_max 4 kHz on `beat_cpu` with `near_correction=True, solve_precision="double"` and on `beat_cuda`; report the
CUDA vs CPU difference. CUDA screens of multicells are allowed only if that difference is < 0.2 dB.

---

## WP15. Fused CUDA Burton-Miller in our fork (the GPU-ceiling fix; NEXT_DEV_PRIORITIES P1)

**Why.** Report 3 section 1: the non-fused CUDA path lives at about 80·N² bytes, so it tops out at ~9k quarter dofs.
The direct assembler stores one `2×N×N` Float32 matrix and factors it in place, which means ~20k dofs and 12 kHz
for the large OSSE seed, plus no memory-pressure slowdown at 7–9k (today 45 s per frequency at 8.9k).

**What already exists [verified 2026-10-24 in the pinned source].**
- `assemble_burton_miller_neumann_system_cuda` (`julia/src/BeatEngineCudaBurtonMiller.jl:350`) handles symmetry images
  (`symmetry_image_transforms`, `device_image_singular_cache`, `p1_symmetry_orbit_weights` row scaling), singular
  corrections and optional near caches. `solve_burton_miller_system_cuda!` (line 642) does `lu!` in place and frees.
- It is tested against the 4-operator path in `julia/tests/runtests.jl` (~1214, ~1300, quarter mesh
  `test_meshes/sample_quarter.msh` from ~1353): matrix rtol 2e-5, pressure rtol 2e-4.
- The driver already builds every cache it needs on CUDA (`BeatEngineDriver.jl:1264-1290`: `device_cache`,
  `device_singular_cache`, `device_image_singular_cache`), and the CPU/Metal fused branch (≈1466) shows the payload
  shape the channel loop expects (`kind=:fused`, `fused_pressure[:, channel]`, `q_columns[:, channel]`).
- CUDA module handle in the driver: `BeatEngineCore.CUDA_MODULE` (see line 1067).

**Patch (fork `C:\Users\hunte\Hrns\forks\hornlab-beat-bem`, branch `hornlab-search/fused-cuda` from `hornlab-search/base`).**
All in `hornlab_beat_bem/julia/BeatEngineDriver.jl`, opt-in, default off:
1. Next to `fused_burton_miller = …` (≈1215):
   ```julia
   fused_burton_miller_cuda = beat_backend == :cuda &&
       near_selection === nothing &&
       get(ENV, "HORNLAB_BEAT_FUSED_BM_CUDA", "0") == "1" &&
       Symbol(symmetry_mode) != :ground          # ground-plane images untested on this path here
   ```
2. In the per-frequency assembly `if/elseif` chain, before `elseif fused_burton_miller`:
   ```julia
   elseif fused_burton_miller_cuda
       fused_q_columns = channel_neumann_columns(
           mesh, element_mesh_ids, radiators, channel_names, rho, omega, FloatType;
           source_motion=source_motion)
       size(fused_q_columns, 2) == 1 || error("HORNLAB_BEAT_FUSED_BM_CUDA supports exactly one channel")
       d_q = BeatEngineCore.CUDA_MODULE.CuArray(fused_q_columns[:, 1])
       cuda_system = assemble_burton_miller_neumann_system_cuda(      # qualify with BeatEngineCore. if not in scope
           mesh, p1_space, dp0_space, d_q, k, selected_rule;
           device_cache=device_cache,
           singular_cache=singular_cache,
           device_singular_cache=device_singular_cache,
           device_image_singular_cache=device_image_singular_cache,
           symmetry_mode=Symbol(symmetry_mode))
       assembly_payload = (kind=:fused_cuda, system=cuda_system, q_columns=fused_q_columns, d_q=d_q)
   ```
3. In the solve block, a branch for `:fused_cuda`:
   ```julia
   if assembly_payload.kind === :fused_cuda
       t_solve += @elapsed begin
           fused_pressure = reshape(solve_burton_miller_system_cuda!(assembly_payload.system), :, 1)
       end
       BeatEngineCore.CUDA_MODULE.unsafe_free!(assembly_payload.d_q)
   elseif assembly_payload.kind === :fused
   ```
4. In the channel loop, `if assembly_payload.kind === :fused` becomes `if assembly_payload.kind in (:fused, :fused_cuda)`.
5. Add `"assembly_path" => "fused_cuda"` (or the existing diagnostics key style) to the per-frequency
   `native_diagnostics`, so our layer can prove which path ran. Grep how `dense_solve_report` and the diagnostics dict
   are built, and follow that pattern.
6. Watch the dtype: `q_neumann` must be `Complex{FloatType}` on the device, matching what the tests pass (`d_q_neumann`).
   Check the `device_cache` rule matches `selected_rule` (on CUDA `selected_rule = rule`).
7. **Julia test** (add to `julia/tests/runtests.jl` CUDA section): run the driver's single-frequency path on
   `sample_quarter.msh` twice (env off/on) and require pressure rtol 2e-4 and polar SPL within 0.01 dB. If running the
   whole driver from the tests is awkward, test through Python instead (step 9).

**Our side (this repo, small).**
8. `SolveSettings` gets optional `cuda_fused: bool = False` (YAML `solve.cuda_fused`). `BeatBackend` with
   `cuda_fused=True` sets `os.environ["HORNLAB_BEAT_FUSED_BM_CUDA"] = "1"` **before** the worker host starts. A warm
   host started without it must not be reused: make the flag part of the worker identity, or run `gpu-clean` before
   switching. Verify the persistent host inherits the variable: read `hornlab_beat_bem/worker_host.py` and
   `worker_client.py`; if it does not, pass it through whatever env the client sets. Record `meta["cuda_fused"]` and
   the diagnostics' `assembly_path` in every Response. Refuse (raise) if `cuda_fused=True` but diagnostics show the
   old path.
9. GPU test `tests/test_solve_beat_fused_cuda.py` (marked `gpu`): small quarter mesh (the CP-7 seed at 2 kHz), fused vs
   non-fused, on-axis within 0.01 dB, beamwidth within 0.1°, z_throat rtol 1e-3.
10. Install the fork commit by SHA (FORKS.md step 4), re-provision if asked, and run the FORKS.md validation ladder:
    analytic selftest, crosscheck vs bempp, A/B on the three reference meshes (`compare` within 0.039 dB and 1°).
11. **Re-measure the ceiling** (TOOLCHAIN M2 protocol: fresh process, VRAM baseline, one solve) at quarter dofs 8.9k,
    12k, 15.7k, 20k, 24k. Record seconds per frequency and peak VRAM. Expect ~20k to fit [inferred].
12. Then new configs/briefs (not edits of the old caps): `dof_cap_verify`/`final` raised to the measured safe value,
    with a `*_fusedcuda` suffix; the 12 kHz verify of the large OSSE seed; `docs/evidence/FUSED_CUDA_<date>.md`.

**Acceptance.** Ladder green; the ceiling measured; one 12 kHz verify of the large seed done on the GPU; old-path
results reproduce bit-for-bit with the flag off (pin the base SHA in a test run to prove it).

**Risks.** The CUDA path was never run by its authors except through these tests; LU in Float32 on a larger,
worse-conditioned matrix at high kR. Watch the crosscheck error versus frequency, and if it grows above 5 kHz, try
the double-precision CPU reference for the same mesh before blaming geometry.

## WP16. Non-uniform source velocity (fork, after WP15)

Extend `velocity_sources` handling so the source tag can carry per-face amplitudes (radial profile:
`v(r) = 1 + α·J0(j01·r/r0)`, normalised to the same volume velocity), at least on the fused paths. It is opt-in.
Purpose: a phase-plug-like exit above f11 (Report 3 section 7). Validate: α = 0 must equal today bit-for-bit.

## WP17. Near-singular correction on CUDA (fork; needed only for multicell/vanes on the GPU)

The CUDA direct assembler already accepts `near_correction_cache` / `device_near_correction_cache`
(`BeatEngineCudaBurtonMiller.jl:361-366`), while `hornlab_beat_bem/config.py` refuses `near_correction` on
accelerators (`NEAR_CORRECTION_REFUSALS`). Read why it is refused before touching it: the config docstring warns
about a CUDA-specific silent-error hazard with a single image-near cache under multi-image symmetry. The approach:
enable it only on the fused CUDA path, without symmetry first, validated against `beat_cpu` with near-correction
on a thin-septum test body. Only then add symmetry.

## Long term (fork, research-scale): matrix-free GPU Burton-Miller + GMRES

O(N) memory and 50k+ dofs (Report 3 section 6). Treat it as a project of its own after WP15 is in production.

## Optional: offer changes upstream

Once WP15–WP17 are validated, offer the branches to Magnus (m3gnus) with our 4060 numbers. Not a dependency.

## Definition of done for the whole programme

- v2 objective live as an opt-in brief key, the offline re-score report written, and the owner's decision recorded.
- Native families compete on the brief's driver; typology leaderboards regenerated under v2 with two seeds.
- 12 kHz screens available for 1" briefs; finalists verified at ≥ 8 points/octave to 12 kHz with the far-field and
  balloon checks done.
- At least two new shape families (GRID Fourier sections, splice or angle-space) in the catalog with smoke runs.
- WP15 validated: fused CUDA in production, new ceiling measured, 12 kHz verify of the large seed on the GPU.

Out of scope by owner decision (2026-10-24): Synergy / multi-entry (MEH) horns and the multi-source-tag solver
ask that they would need.
