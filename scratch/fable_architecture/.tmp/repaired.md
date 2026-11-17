# Geometry and Parameter Map — hornlab-search

- **Repo:** `C:\Users\hunte\Hrns\hornlab-search` (canonical checkout; no worktree used)
- **Branch:** `main`
- **HEAD actually read (`git rev-parse HEAD`), re-checked by me:** `3efe9bef00d6889b4ae31120e9fcaba00b6a087e`
  (commit date `2026-11-16T19:20:54-05:00`; re-read `2026-11-16T19:38:59-05:00`)
- **`origin/main` actually read:** `2c0e2928e932a47975fc284401eafa74ebfc5002`
  - The dispatch brief said HEAD = `2c0e292`; the working tree is **3 commits ahead** of `origin/main`
    (`3efe9be`, `ded9e62`, `659da48`). Recorded, not changed.
  - Orchestrator's later provenance note (19:40) matches: HEAD advanced after dispatch. This header
    uses the re-read SHA, not the dispatch-time one.
- **Working tree at the time of writing (`git status --short`, 19:38:59):** dirty and not mine —
  `M hornlab_search/design/generated.py`, `M design/generators/grid.py`, `M mesh/build.py`,
  `M gui/data.py`, `M gui/server.py`, `M gui/static/app.js`, `M report/html.py`,
  `M targets/scoring_view.py`, `M tests/test_scoring_view.py`; untracked `klangfilm_lame_hv_family.py`,
  `_klangfilm_lame_hv_v1.py`, `examples/typologies/klangfilm_hv_2026-11-16/`, evidence docs and
  tests. Nothing in the tree was edited or staged by me.
- **Concurrent activity (observed read-only; untouched):** `git log` shows the 3 local commits at
  19:20; three cited files (`design/generated.py`, `design/generators/grid.py`, `mesh/build.py`)
  have mtime **19:26** and `design/generators/klangfilm_lame_hv_family.py` **19:32:57**. A `julia`
  process started **19:31:22** and python workers started 19:31/19:39 — consistent with the live
  solve the orchestrator warned about. I did not start, stop, signal or inspect-deeply any of them.
- **Citation basis:** every `path:line` below is a **working-tree** line observed between 19:26 and
  19:40 local, **not** a clean-commit line. The 19:26 edits to `generated.py`, `grid.py` and
  `build.py` are same-line substitutions (klangfilm dispatch-list entries), so their line numbers
  did not shift (verified by `git diff` and by re-reading the cited ranges). The 19:32 edit to
  `klangfilm_lame_hv_family.py` **did** change the file (7,707 → 9,650 bytes, new `size_policy`
  block); all citations to that file were re-read at 19:40 and updated.
- **Date:** 2026-11-16
- **Inspector:** Investigator A — shape languages, families, parameters. Read-only architecture pass:
  no pytest, no mesh/BEM/GPU, no search/job, no process control, no git mutation. The only write is
  this file plus `.tmp/` if used (not used).
- **Method:** source reading only. **No claim here was verified by executing code.** “directly
  verified” therefore means *the cited line says this*, not *a run produced this*.

### Status legend

| code | meaning |
|---|---|
| **DV** | directly verified in the cited source line (code/config/doc text read by me) |
| **DO** | documented only — a doc/test/build comment asserts it; I did not execute it |
| **PI** | plausible inference from the cited lines; not spelled out by any single line |
| **UN** | unverified — no source I read settles it |
| **CX** | contradicted — the cited code contradicts the cited claim |

---

## 1. Family / config inventory: construction vs preset vs search box

Verdict vocabulary: **CONSTRUCTION** = a distinct surface law or distinct body topology;
**PRESET** = the same construction with a discrete option or a fixed knob set;
**REPRESENTATION** = the same law carried through a different geometry container (anchors vs
rows vs formula); **DEFORMATION** = a map applied on top of another body; **BOX/BRIEF ONLY** = the
geometry is unchanged and only bounds/brief/objective differ; **BRIDGE-ONLY** = not loadable by the
stock `generator: {name: grid}` path without a process-local loader.

| # | name / entry point | module:line | physical construction | verdict | status / evidence |
|---|---|---|---|---|---|
| 1 | native **OSSE** (`examples/osse_baseline.yaml`) | `design/families.py:211-225`; `families.py:695` | OS/OSSE formula surface in the mesher (`formula: OSSE`), single formula body | CONSTRUCTION | DV. Family table and `cfg["formula"]=design.family`. |
| 2 | native **R-OSSE** (`examples/rosse_baseline.yaml`) | `families.py:227-234`; `families.py:276-291` | mesher R-OSSE formula body (`R_mm/tmax/m/r/b`); refuses `L_mm`, `n`, `s`, `rot_deg` | CONSTRUCTION | DV. Refusal hints are explicit; morph is present in `_ROSSE` (contradicts old `SEARCH_LAYER_GAPS.md`, see §6). |
| 3 | native **ICW** flat_baffle vs rollback (`icw_termination.yaml`, `icw_rollback.yaml`) | `families.py:236-257`; `families.py:244` | one ICW curve fitted to `icw_seed`; `termination` is a categorical that selects flat baffle vs rollback | CONSTRUCTION for the family; rollback/flat are **PRESET** branches | DV: `termination` choices are `("flat_baffle","rollback")` and are `str` (not searchable: no lo/hi). |
| 4 | native **FREEFORM** anchors (`freeform_hv.yaml`, `freeform_sculpt.yaml`) | `families.py:259-265`; `families.py:519-561` | two explicit meridians (`profileH/V.points`) + optional `crossSections` stations | CONSTRUCTION (free-form carrier for every generated typology) | DV. z strictly increasing, 2–64 rows, shared throat radius/z-span. |
| 5 | generator **conical** | `generators/registry.py:168-169`; `generators/profiles.py:76-92` | `r=r0+z tan α`, constant wall angle | CONSTRUCTION law → REPRESENTATION as FREEFORM anchors | DV. |
| 6 | generator **exponential** | `registry.py:170-171`; `profiles.py:95-116` | `r=r0 e^{mz}` | CONSTRUCTION | DV. |
| 7 | generator **hypex** (Salmon) | `registry.py:172-173`; `profiles.py:119-159` | `r=r0(cosh mz + T sinh mz)` plane-wave wall | CONSTRUCTION, different from §8 | DV. |
| 8 | generator **spherical_salmon** | `registry.py:198-206`; `profiles.py` | wavefront-area Salmon march (not a plane-wave radius law) | CONSTRUCTION | DV via `build_meridian` branch; name collision with hypex is real (“Salmon” does not imply one law). |
| 9 | generator **tractrix** | `registry.py:174-175` | Voigt tractrix cut at `max_wall_deg` | CONSTRUCTION | DV. |
| 10 | generator **lecleach** (FREEFORM, `stop≤88`) | `registry.py:176-181`; `profiles.lecleach` | Fourcade 2015 exact Le Cleac'h march, truncated into anchors | CONSTRUCTION, but REPRESENTATION cannot roll back | DV. Truncation branch returns `_truncate(m, L)`. |
| 11 | **spherical_wave** | `profiles.py:613-618` | literal alias `lecleach(..., T=1.0)` | **PRESET of §10** | DV: body is a one-line call. |
| 12 | **splice / blend / perturb** | `registry.py:186-197`, `257-263`, `281-302`; `profiles.py:637,793,1068,1170` | composition operators on meridians (C1 splice, convex blend, monotone increments) | **OPERATOR**, not a construction | DV. All still emit one FREEFORM body. |
| 13 | generator **osse** meridian (`osse_axi.yaml`) | `registry.py:127-139` | calls `hornlab_mesher.profile_formulas.profile_points(type="OSSE")`, then fits 16 anchors | **REPRESENTATION of §1** | DV. The ≤0.2 mm equality to the native formula is asserted by `tests/test_design_generated.py:148-161` (DO; not run). |
| 14 | generator **biradial** (`biradial_keele.yaml`) | `registry.py:207-218`; `profiles.py:257-330` | Keele/JBL `r=r0+tan(a)z+c z^n`, per plane; own `a_deg` default 25 | CONSTRUCTION | DV. Patent dossier cited at `registry.py:208-214`. |
| 15 | generator **qtw_waveguide** | `registry.py:219-228`; `profiles.py:331-411` | circular arc throat parallel to axis + straight bell; `rm` derived | CONSTRUCTION | DV. “per the published rule; not a claimed replica” at `registry.py:219-225`. |
| 16 | **GRID radius field** (`grid_ellipse.yaml`) | `generators/grid.py:1-48`; `grid.py:488-508`; `grid.py:561-642` | superellipse radius field between two sampled meridians + even Fourier mouth modulation + side rollback | CONSTRUCTION (distinct point-grid surface) | DV. `r(s,φ)=r_H r_V/((…) )^(1/p)·(1+Σ a_k(s)cos 2kφ)`, `z=sL+dz(φ)w(s)`. |
| 17 | **rows `lecleach`** (`lecleach_rollback.yaml`) | `grid.py:2176-2203`; `grid.py:2506-2545` | the same Fourcade march on every azimuth, stop 90–240° ⇒ real rollback; rows resampled on equal arc length | CONSTRUCTION/REPRESENTATION: same law as §10, carrier supports the rollback | DV. `stop` range `ROWS_LECLEACH_STOP_RANGE=(90,240)` at `grid.py:221`. |
| 18 | rows **`salmon_elliptical`** (`salmon_elliptical.yaml`) | `grid.py:2348-2416`; meta `grid.py:2784-2792` | one Salmon march per azimuth with `1/fc(φ)` law | LABELED HYPOTHESIS construction | DV: label `ROWS_HYPOTHESIS_LABEL` `grid.py:181-184`. |
| 19 | rows **`salmon_axisym`** | `grid.py:2380-2382` | identical march to §18 but `fc = fc_h` on every row | **PRESET of §18** | DV: one-line branch. |
| 20 | rows **`lecleach_mod`** | `grid.py:2235-2266`, `1160-1225` | Fourcade march + harmonic stop `a2/a4/b1/b3` + optional axial bend | LABELED RECONSTRUCTION; **PRESET of §17 when all harmonics = 0** | DV: `_rows_mod_half` states the quarter==half regression (`grid.py:1146-1154`). |
| 21 | rows **`lecleach_asym`** | `grid.py:2204-2234` | same march + odd-cosine radius asymmetry `cos φ`; forces full ring | CONSTRUCTION variant (asymmetric) | DV: label `ROWS_ASYM_LABEL` `grid.py:185-190`. |
| 22 | rows **`lecleach_ar`** vs **`iwata_ar`** | `grid.py:2325-2347` vs `2267-2298` | both area-preserving AR stretch `AR(l)`; different knob names (`AR_m/p` vs `ar_m/ar_p`), `T` default 0.8 vs 0.5 | **near-duplicate construction, two presets/APIs** | DV: same helper `lecleach_ar_profile` (`grid.py:1431`), both labels say “our reconstruction”. |
| 23 | rows **`toroidal_rollback`** | `grid.py:2299-2324` | Fourcade march + tangent-continuous circular lip, fixed 180° wrap | CONSTRUCTION (lip add-on) | DV: `TOROIDAL_WRAP_DEG` `grid.py:291`. |
| 24 | rows **`osse_rollback`** (`hl__crowe_x_osse_cd_v7.yaml`) | `grid.py:1908-1931`, `1939-2073`, `2171-2175` | OSSE/OS throat wall per azimuth, superformula mouth morph, flute ripple, curled lip | CONSTRUCTION (hybrid) | DV. |
| 25 | **rolled_family_rect_v1** (`rf__rect_*.yaml`) | `generators/rolled_family.py:17`, `141-205` | explicit rect body from `_rolled_rect_v1`, inner+outer surfaces, radial/axial relief with a window | CONSTRUCTION (versioned explicit body) | DV: digest binds adapter + kernel (`31-38`). |
| 26 | **rolled_family_section_v1** | `rolled_family.py:18`, `64-70` | a **different** parent kernel, `_crowe_section_v2` (digitized section reference) | CONSTRUCTION | DV: `_parent` dispatches on kind. |
| 27 | **klangfilm_lame_v1** | `generators/klangfilm_lame_family.py:26-29`, `resolve_grid` | frozen Klangfilm-Lame kernel + cap + sampled normal-offset shell | CONSTRUCTION (CPU geometry interface) | DV: “not an acoustic-readiness claim” `klangfilm_lame_family.py:4`. |
| 28 | **klangfilm_lame_hv_cd** (untracked new file at this pass) | `klangfilm_lame_hv_family.py:26-40`, `101-130`, `165-182`; dispatch `generated.py:137-141`, `grid.py:2806-2808` | HV core blend over the K body; five Phase-A knobs inert unless `cd_core_blend≠0`; new per-family `size_policy` (`enforce`/`report_only`) | CONSTRUCTION variant + explicit dormancy + envelope-policy variant | DV: dormancy refusal `165-176`; `report_only` keeps geometry and records violations `116-129`, `177-182`. File is `??` in git and was extended at 19:32 during this pass. |
| 29 | **lecleach_swept_hv** (`l01_geometry_only.yaml`) | `generators/lecleach_swept_hv.py:1-6`, `135-142`, `209-256` | flat-section-area Le Cleac'h parent, AR/Lame progression, rim sweep, lip, axial warp | EXPERIMENTAL CONSTRUCTION | DV: prototype docstring says not solver-ready (`1-6`); versioned adapter exists (`135-142`). |
| 30 | CAD **multicell** (`multicell_3x3.yaml`) | `mesh/step_build.py:87-140`; `families.py:597-609` | labelled STEP air volume from `tools/cad/multicell.py`; `{"cad": recipe}` only | CONSTRUCTION (topology, not formula) | DV. |
| 31 | CAD **plughorn** (`cone_plughorn__*`) | `design/generated.py:61-90`; `step_build.py:132-136` | vendor-model-derived axe-head body; 14 morph knobs; variants are presets | CONSTRUCTION + PRESET variants | DV: recipe = tool DEFAULTS overridden by fixed then knobs (`generated.py:74-83`). |
| 32 | CAD **meh** (`meh_t2a_search.yaml`) | `generated.py:93-127`; `step_build.py:137-139` | multi-entry horn STEP: driver + top/bottom entries; 6 C9 layout knobs | CONSTRUCTION (multi-entry topology) | DV: tags `10/11` entry exits (`step_build.py:110-117`). |
| 33 | native **morph** on OSSE (`ath_core.yaml`) | `families.py:72-81`; `families.py:701-713`; mesher `profile_morph.py:542-605` | target-shape map applied to the wall/mouth of another body | **DEFORMATION**, not a construction | DV. |
| 34 | **az-law OSSE** (`hl__ext_throat_hvlaw_v7.yaml`) | `families.py:99-136`, `150-184` | per-azimuth `a(φ)/n(φ)/s(φ)` expressions passed to the OSSE formula | LAW VARIANT of §1, not a new engine | DV: expressions become the `a_deg`/`n`/`s` values (`families.py:161-184`). |
| 35 | `native__ath_core_v4` vs `native__ath_core_2in_v5` | `examples/typologies/data_2026-10-29_v5/native__ath_core_2in_v5.yaml:1-3` | same seed/bounds/geometry; only brief (objective version) and name differ | **BOX/BRIEF ONLY** | DV: the file states it verbatim. |
| 36 | rows **`rolled_rect` / `rosse_rect` / `crowe_panel`** (`rr__reference_v7.yaml`) | `examples/catalog.gui.yaml:3-9`; `grid.py:139-141`, `903-916` | bridge-only rows types, installed by `tools/geometry/*_cli.py` | **BRIDGE-ONLY** | DV: not in `ROWS_TYPES`, so `_rows_check_spec` refuses; catalog.gui says “must use …_cli.py”. |

**Section 1 conclusions (evidence, not recommendation).**
- The number of *distinct physics engines* is small: OSSE, R-OSSE, ICW, FREEFORM, point-grid, CAD
  STEP. Everything classical/hybrid is a meridian law or a composition that lands in one FREEFORM
  body (`registry.materialize` returns `profileH/profileV/crossSections`, `registry.py:344-345`).
- Several catalogue “families” are the same construction under a different carrier or option:
  spherical_wave = lecleach T=1 (`profiles.py:613-618`); salmon_axisym = salmon_elliptical with
  `fc=fc_h` (`grid.py:2380-2382`); lecleach_mod with zero harmonics = lecleach; generator `osse`
  = native OSSE resampled.
- Many catalogue entries differ only by brief/objective/bounds (§35). The catalogue is therefore
  not a taxonomy of constructions; it is a mix of constructions, carriers, deformation layers,
  presets and campaign cells (group vocabulary itself mixes `magnus/classical/hybrid/organic/cone/
  meh/home` at `examples/catalog.yaml:4-14`).

---

## 2. Parameter semantics and units

Class abbreviations: **F** fixed/pinned in the config, **S** searched (a CMA dimension), **D**
derived inside the build, **C** conditional (only read when a predicate holds), **I** inactive for
the resolved config, **X** clipped, **K** coupled to another knob (not independent).

### 2.1 Search-space mechanics (true for every family)

| name | module:line | unit | class | predicate / trigger | status |
|---|---|---|---|---|---|
| search vector order | `design/space.py:1-4`, `119-122` | — | **K** | alphabetical order of searched keys; never YAML order | DV |
| `search: false` bound | `space.py:26-43`, `164-168` | native unit | **F** | a non-searched bound keeps the seed value and is absent from the vector (`denormalize` copies seed, `space.py:144`) | DV |
| bound `log` | `space.py:46-64` | — | — | log10 map for scale-like knobs; requires `lo>0` | DV |
| out-of-bound candidate | `space.py:124-135`, `143` | native unit | **X** | normalise warns+clips; denormalise clips `x` into [0,1] | DV |
| int knob | `space.py:148-152` | — | **K/D** | `KeySpec.kind is int` is rounded at denormalise; continuous box, discrete value | DV |
| knob not in seed | `space.py:91-116` | native unit | **D** | filled with bound midpoint, warning, seed geometry changes | DV |
| generator list knob | `design/generated.py:142-155`, `generated.py:172-180`; `grid.py:368-388` | varies | **F** (not searchable) | JSON list knobs (stop harmonics) are kept as lists; only scalar bounds become CMA dimensions | DV |
| generator vector↔knobs | `generated.py:172-222` | — | — | `normalize` requires provenance (`_knobs_by_hash`) or a versioned recipe; geometry cannot be inverted | DV |
| `search.links` parent/child | `search/links.py:1-12`, `28-55`, `70-87` | parent's unit | **K/X** | child removed from vector, computed `scale*parent+offset`, clipped to [min,max]; **refused with a generator block** | DV |
| seed policy | `registry.py:244-245` (`seed_policy` stripped before materialising) | — | **F** | config-load directive, never geometry | DV |

### 2.2 Native OSSE (also the meaning inside the OSSE meridian generator)

| name | module:line | unit | class | predicate / trigger | status |
|---|---|---|---|---|---|
| `r0_mm` | `families.py:53` | mm | **F** brief-pinned or **S** | native: pinned to `driver.exit_radius_mm` unless an extended throat is declared (`config.py:1219-1224`); generator: always the brief radius (`registry.py:246`) | DV |
| `a0_deg` | `families.py:54` | deg (half-angle) | **F/S** | pinned only when brief says `throat_angle_policy: pin` (`config.py:1223-1224`); generator: always brief exit angle (`registry.py:247`); extension disables the native pin | DV |
| `a_deg` | `families.py:53`; mesher `profile_formulas.py:379-393` | deg, **half**-angle | **S/K** | far-field wall half-angle; replaced by the gcurve-solved angle whenever a guiding curve is active (`profile_formulas.py:389-393`) | DV |
| `L_mm` | `families.py:213`; mesher `profile_formulas.py:156-172, 367` | mm | **S/K** | main-horn length; total length = `ext_len + slot_len + L`; envelope checked on `L` (`families.py:435-445`) | DV |
| `n`, `s`, `q` | `families.py:56-57,214-215`; mesher `profile_formulas.py:264-280` | dimensionless | **C/K** | `n`,`q` are skipped when `s==0`; while `s≠0`, `n>0` and `q>0` are enforced `families.py:435-443` | DV |
| `k` | `families.py:55`; `registry.py:131-133` | dimensionless | **S** | OSSE shape factor passed into the mesher formula | DV |
| `s1`, `s2` | `families.py:58-59`; mesher `profile_formulas.py:283-300, 426-427` | s1 mm/deg, s2 1/mm (families notes) | **C/K** | axial stretch is a no-op when **either** is 0, and only applies beyond `ext+slot`; rotating + prefix is refused (`profile_formulas.py:424`) | DV |
| `throat_ext_length_mm`, `throat_ext_angle_deg`, `slot_length_mm` | `families.py:60-62`; `profile_formulas.py:382-386` | mm, deg | **S/K** | extension tapers back from `r0`; a searched extension changes which plane is “driven” and disables r0/a0 pinning (`config.py:1202-1206`) | DV |
| `rot_deg` | `families.py:216`; `profile_formulas.py:417-423` | deg | **S/K** | rotates the whole meridian in the (x,y) plane, so it moves mouth z and radius together | DV |
| `h` | `families.py:217`; `profile_formulas.py:157-164` | mm | **S/K** | half-sine radial bulge over the composite length; also offsets the coverage inversion target | DV |
| `exponent`, `aspect_ratio` | `families.py:64-67` | dimensionless | **S** (OSSE) | cross-section superellipse and H/V scale; no hard schema range in the table (only notes) | DV |
| `mode` | `families.py:69`, `48-49` | token | **F** | top-level mesher build mode; overridden to `enclosure` when a mounting block exists (`families.py:696-698`) — see §3 break B4 | DV |
| `wall_thickness_mm` | `families.py:70` | mm | **S/F** | `mesh` section; freestanding shell thickness | DV |
| `mid_ports` | `families.py:218-224`, `457-479` | mm / fractions | **C** | OSSE only; dict `walls∈{tb,lr,tblr}`, `0<z_frac<1`, `0<across_frac≤1`, `port_along_mm>0`; emitted top-level | DV |
| `az_*` (18 keys) | `families.py:109-136`; `families.py:150-184` | deg / dimensionless | **C/K** | OSSE only; no expression is emitted unless some `az_a_*`/fold/`az_n_cos2_amp`/`az_s_cos2_amp` is non-zero; `az_sf_m` must be a multiple of 4; the whole law is sampled every 3° and must stay in `(0.5, 89.5)°` (`families.py:423-434`) | DV |
| `gcurve_type`, `gcurve_width_mm`, `gcurve_dist`, `gcurve_rot_deg`, `gcurve_sf*`, `gcurve_se_n` | `families.py:82-97`; mesher `profile_morph.py:10-38`, `229-274` | int/mm/deg | **C/K** | active iff `type∈{1,2}` and `width>0`; then it **solves/replaces** `a_deg`; `gcurve_dist` picks the z target | DV |

### 2.3 Native morph (a deformation surface shared by OSSE/R-OSSE/ICW/FREEFORM)

| name | module:line | unit | class | predicate / trigger | status |
|---|---|---|---|---|---|
| `morph_target` | `families.py:73`; mesher `profile_morph.py:358-381` | int 0–3 | **S/F, K** | `0` none, `1` rectangle, `2` circle, `3` superellipse; searched as a continuous int box (rounded, `space.py:148-152`) | DV |
| `morph_width_mm`, `morph_height_mm` | `families.py:74-75`; `profile_morph.py:563-574` | mm | **C** | target != 0; `0` falls back to the drawn mouth extent | DV |
| `morph_corner_mm` | `families.py:76`; `profile_morph.py:604-605` | mm | **C** | target == 1 only | DV |
| `morph_exponent` | `families.py:77`; `profile_morph.py:575-603` | dimensionless | **C/I** | target == 3 only; proven no-op at target 1 by `tools/analysis/parameter_activity.py:586-606` | DV |
| `morph_rate` | `families.py:78`; `profile_morph.py:639-653` | dimensionless | **C** | target != 0 and `t>morph_fixed`; must be ≥0 | DV |
| `morph_fixed` | `families.py:79`; `profile_morph.py:656-682` | fraction [0,1) | **C** | start station of the blend | DV |
| `morph_allow_shrinkage` | `families.py:80`; `profile_morph.py:481-498` | 0/1 | **C** | when false, target half-dimensions are floored at the drawn extents | DV |

### 2.4 R-OSSE and ICW

| name | module:line | unit | class | predicate / trigger | status |
|---|---|---|---|---|---|
| `R_mm` (R-OSSE) | `families.py:229`; `knobs_native.py:977-998` | mm | **S/K** | sets the mouth **and** the derived length; no separate `L_mm` | DV (doc/code note) |
| `tmax` (R-OSSE) | `families.py:230`; `families.py:446-448` | dimensionless | **S** | truncation; must be >0 | DV |
| `m`,`r`,`b` (R-OSSE) | `families.py:231-233` | dimensionless | **S** | R-OSSE formula coefficients | DV |
| `n`,`s` on R-OSSE | `families.py:280-282` | — | **I** | explicitly refused (“OSSE-only key”) | DV |
| `termination` (ICW) | `families.py:238-239` | categorical | **F** | `flat_baffle` or `rollback`; cannot carry a bound, so cannot be searched | DV |
| `coverage_angle_deg` (ICW) | `families.py:244` | deg, half-angle | **S** | `0 < value < 90`; brief target `coverage_*_deg` is the **total included** angle | DV |
| `hold_start`,`hold_end` (ICW) | `families.py:245-246`, `482-486` | fraction [0,1] | **S/C** | requires `hold_start < hold_end` | DV |
| `kappa0`,`theta1_deg`,`n_coeff`,`kappa_abs_max`,`dkappa_ds_abs_max`,`theta_max_deg`,`pin_mouth_radius`,`icw_seed`,`icw_coeffs`,`icw_S` | `families.py:247-256` | 1/mm, deg, count, bool, dict, list | **S/F/C** | `icw_seed` holds a nested formula spec; `pin_mouth_radius` bool | DV (table); individual mesher use UN here |
| OSSE shape keys on ICW | `families.py:292-300` | — | **I** | every OSSE/R-OSSE shape key is refused at the top level; must be nested in `icw_seed` | DV |
| `sampling_mode`/`z_map_points`/`zmap` on ICW | `families.py:299-300` | — | **I** | ICW samples uniformly in arc length | DV |

### 2.5 FREEFORM (native anchors)

| name | module:line | unit | class | predicate / trigger | status |
|---|---|---|---|---|---|
| `profileH.points`, `profileV.points` | `families.py:261-262`, `489-516` | mm rows `[z,r(,angleDeg)]` | **S/K** | 2–64 rows, z strictly increasing, r>0; first/last z and first r must match across H/V | DV |
| `*.throatAngleDeg`,`*.mouthAngleDeg` | `families.py:512-515` | deg | **S/C** | [-90,90]; pinned to the brief when `policy: pin` (`config.py:1232-1237`) | DV |
| `crossSections` | `families.py:263`, `531-561` | list of stations | **S/C/K** | 2–32 stations, `t` increasing in [0,1], first t=0 and last t=1, first shape circle/ellipse; `exponent` only on superellipse (2–16), `cornerRadiusMm` required for rounded_rectangle | DV |
| `inflectionPolicy` | `families.py:264` | token | **F** | `warn` or `reject` | DV |
| `exponent` (bare alias) | `families.py:309`, `342-346` | dimensionless | **K** | resolves to the **first superellipse station** of `crossSections` | DV |
| OSSE shape keys on FREEFORM | `families.py:301-305` | — | **I** | `exponent/aspect_ratio/rot_deg/h/s1/s2/throat_ext_*/slot_length/gcurve_type` refused; “crossSections / the two meridians own the outline” | DV |
| active guiding curve on FREEFORM | mesher `freeform.py:1965-1975` | — | **I** | refused by the mesher (“use crossSections stations instead”) | DV |

### 2.6 GRID and rows

| name | module:line | unit | class | predicate / trigger | status |
|---|---|---|---|---|---|
| `profile_h`, `profile_v` | `grid.py:442-485` | typology spec | **F** | `same` mirrors H; `blend_v` requires an explicit V | DV |
| `n_phi` | `grid.py:321`, `69`, `923` | count | **F/D** | ≥13 quarter, ≥25 half/full, odd for half/half_xz (`grid.py:1652-1668`) | DV |
| `n_s` | `grid.py:322`, `924` | count | **F** | ≥8 axial intervals (33 stations typical) | DV |
| `max_wall_deg` | `grid.py:323-325`, `451-453` | deg | **F** | [10,90) | DV |
| `wall_thickness_mm` | `grid.py:326-328` | mm | **F** | [0.5,12]; also sets the self-approach limit `2t+2` | DV |
| `pnorm` | `grid.py:61-66`, `399-403`, `618` | dimensionless | **S**, constant | ≥1; **constant in s** in this pass (“plan names a function”) | DV |
| `a{k}_throat`, `a{k}_mouth` | `grid.py:404-419`, `488-508` | dimensionless | **S/K** | G8 Fourier amplitude linear in s; highest k present raises K, default 2, max 16; modulation must stay positive | DV |
| `term_side_mm` | `grid.py:404-407`, `596-599` | mm | **S** | absolute value; `dz=-abs(t)*cos²φ`, so positive knob = side rollback | DV |
| `rows.type` | `grid.py:139-141` | token | **F** | one of 9 kinds; selects the whole march table and legal knob set | DV |
| `span` | `grid.py:149-150`, `854-897` | token | **F/K** | `quarter`/`half`/`half_xz`/`full`; **must match `mesh.quadrants`** (`grid_build.py:157-166`) | DV |
| `g_fc_h_hz`,`g_fc_v_hz`,`g_T`,`g_stop_deg` (salmon) | `grid.py:947-1001` | Hz, dimensionless, deg | **S/K** | `stop∈(0,360)`, `stop=180` refused; T≥0; fc>0 | DV |
| `g_x_amp`,`g_x_fc` (T5) | `grid.py:983-988` | dimensionless | **S/K** | `x_amp∈[-0.4,0.4]` (signed), `x_fc∈[0,0.3]`; scaled by the Salmon stop | DV |
| `g_fc_fold`,`g_fc_union` | `grid.py:989-998`, `2383-2389` | 2 or 4; 0 or 1 | **F** | mutually exclusive (`union` requires fold 2) | DV |
| `g_stop_cos2k`,`g_stop_sin2k1` | `grid.py:276-277`, `368-388`, `1851-1872` | list of fractions | **F** (not searchable) | ≤2 terms; `g_stop_a2` is the scalar alias for the first term (`grid.py:357-367`); odd-cosine/even-sine keys are refused (`grid.py:1141-1143`) | DV |
| `g_bend_sin1_mm` | `grid.py:1686-1690` | mm | **C/K** | axial fan bend; forces the half model | DV |
| `g_r_lip_mm` | `grid.py:1066-1075` | mm | **C** | 0 = byte-identical; [0,100] | DV |
| `g_ripple_lobes`,`g_ripple_amp_mm`,`g_ripple_start` | `grid.py:1004-1048` | count, mm, fraction | **C/K** | even lobes 6–24, amp 0–50, start [0,1); amp>0 requires lobes; ≥4 phi samples per lobe (`grid.py:1051-1063`) | DV |
| `g_AR_m`,`g_p` / `g_ar_m`,`g_ar_p` | `grid.py:267-270`, `1897-1900` | dimensionless | **S/K** | AR stretch; throat ratio pinned at 1.0; `ar_p≤8` (iwata) | DV |
| `g_cd_core_blend` + Phase-A keys | `klangfilm_lame_hv_family.py:38-40`, `165-176` | dimensionless/mm/deg | **C/I** | phase-A keys inert when blend is fixed 0; config load refuses searching them | DV |
| `size_policy` (K family only) | `klangfilm_lame_hv_family.py:32-36`, `116-129`, `177-182` | token | **F** | `enforce` (legacy) vs `report_only`; `report_only` cannot be combined with any searched bound | DV |
| `rows.mode` + relief keys | `rolled_family.py:17-23`, `102-113`, `240-252` | token/mm/fractions | **C/F** | radial keys active only in radial/hybrid; axial only in axial/hybrid; dormant dimensions refused at search-config validation | DV |

### 2.7 Brief / config-side knobs that move geometry without appearing in `bounds`

| name | module:line | unit | class | predicate / trigger | status |
|---|---|---|---|---|---|
| `driver.exit_radius_mm`, `driver.exit_angle_deg` | `config.py:248-256`; `registry.py:246-247`; native pin `config.py:1219-1224` | mm, deg | **F/K** | generator r0/a0 always; native r0 always (extension excepted), a0 only under `pin` | DV |
| `envelope.max_mouth_w_mm/max_mouth_h_mm/max_depth_mm` | `config.py:248-292`; `registry.py:304-307`, `431-484`; `grid.py:2989-3020` | mm | **D/constraint** | invalid design if exceeded; pre-mesh estimate adds wall thickness | DV |
| `symmetry` | `config.py:271-282` | token | **F** | axisymmetric brief requires `coverage_h==coverage_v` | DV |
| `mounting` | `config.py:497-503`; `families.py:635-673` | mm | **C** | only `plan: rounded_rectangle`; flips mode to enclosure; no shipped example config references `enclosure_1in.yaml` | DV |
| `source.cap` | `config.py:239`; `families.py:695` | auto/mm | **F** | source cap construction at mesh time | DO |

---

## 3. Composition reality check: YAML feature → generator → mesher → meshed surface

The two meshing routes are explicit in `mesh/build.py:351-357`: `grid` params → `_build_grid_mesh`
→ `grid_build.build_grid_mesh`; `cad` params → `step_build.build_mesh_from_cad`; everything else →
`families.to_mesher_config` → `hornlab_mesher.build_from_config`.

| YAML feature | generator / materializer | mesher consumer | reaches the meshed surface? | status |
|---|---|---|---|---|
| OSSE `profile` keys | `families.to_mesher_config` routes by `KeySpec.section` (`families.py:699-727`) | `hornlab_mesher` OSSE formula (`profile_formulas.py:359-428`) | **Yes**, one-to-one | DV |
| OSSE `az_*` | `families.azlaw_expressions` builds Python expressions (`families.py:150-184`) | replaces `a_deg`/`n`/`s` in the profile section (`families.py:701-713`); mesher evaluates per φ | **Yes**, but only for OSSE; R-OSSE/ICW/FREEFORM have no such keys | DV |
| `gcurve_*` | `families.py:82-97` | coverage inversion; `a_deg` is **ignored** while a curve is active (`profile_formulas.py:389-393`) | **Yes, non-orthogonally**: searching `a_deg` and `gcurve_width_mm` together does not mean two independent levers | DV |
| `morph_*` | `families.py:701-713` | morph target branch (`profile_morph.py:542-605`; FREEFORM `freeform.py:194-281`) | **Yes**; which keys matter depends on the target (corner only t1, exponent only t3) | DV |
| `mid_ports` (OSSE) | `families.py:218-224` | top-level dict, mesher fork mid-port patch, tags 10 | **Yes on OSSE only**; not a legal key on R-OSSE/ICW/FREEFORM/grid | DV |
| `FREEFORM profileH/V + crossSections` | `families.py:519-561` | spline + station blend (`freeform.py:194-210`, 1846-1916) | **Yes**; morph blends stations, and a morph-induced non-convex outline is refused (`freeform.py:1874-1903`) | DV |
| generator `crossSections` | `registry.materialize` emits exactly **two** stations: `t=0 circle`, `t=1 ellipse/superellipse/rounded_rectangle` (`registry.py:323-332`) | station blend | **Only a mouth shape**, not an arbitrary station stack; the plan’s “station t and exponent searched” is not implemented in the generator path | DV |
| native `morph` + non-elliptical cross-section | `registry.py:315-322` refuses to build it | mesher itself does **not** refuse; only convexity checks | **The stated “FREEFORM refuses a morphed non-elliptical cross-section” is a search-layer policy, not a mesher limitation** | CX (see §6) |
| grid radius field | `grid.design_params` persists `{"grid": {spec, knobs}}` (`grid.py:2881-2927`) | re-derived at mesh time in `mesh/build.py:485-500` → `grid_build.py:185-194` (`PointGridHornGeometry`) | **Yes**; geometry needs `cfg.brief` at mesh time (`mesh/build.py:486-490`) | DV |
| grid `rows` | `grid.rows_per_azimuth` (`grid.py:2444-2800`) | same point-grid path; span → `quadrants` must match | **Yes**, but a mismatch is a hard error (`grid_build.py:157-166`) | DV |
| `rows` b-terms / bend | `_rows_mod_half` presence rule (`grid.py:1146-1157`) | half model, quadrants “14” | **Yes**; the same config with all b-terms zero is quarter geometry | DV |
| mouth ripple | `_rows_ripple_resolution_guard` (`grid.py:1051-1063`) | per-azimuth radius multiplier (`grid.py:2396-2404`) | **Yes**, or refused if `n_phi` cannot resolve the lobes | DV |
| rolled-family relief | `_shape` validates mode-vs-relief (`rolled_family.py:102-113`) | `resolve_grid` applies inward/axial relief (`rolled_family.py:160-183`) | **Yes**; dormant relief keys are refused at config load (`221-252`) | DV |
| klangfilm Phase-A keys | `_DORMANT_KEYS` (`klangfilm_lame_hv_family.py:38-40`, `165-176`) | kernel HV blend | **Conditionally**; inert unless `cd_core_blend≠0` | DV |
| klangfilm `size_policy: report_only` | `klangfilm_lame_hv_family.py:116-129`, `177-182` | family's own envelope check is relaxed; `search/evaluate.envelope_violation` still runs after the mesh (`evaluate.py:1216`, `1438`) | **Geometry builds, but the search-layer envelope gate still applies**; the flag cannot be combined with any searched bound | DV (code) / PI (that no other gate re-admits it) |
| CAD recipe | `generated.py:61-127` builds a tool recipe | `step_build.build_cad_step` → gmsh → labelled STEP (`step_build.py:295-336`) | **Yes**, but via a completely different builder; STEP export through the formula path is refused (`mesh/build.py:540-551`) | DV |
| `montage.mounting` enclosure | `families.enclosure_section` (`families.py:635-653`) | mesher `enclosure` sibling section | **Yes on the formula route**; refused for rolled family (`rolled_family.py:146-147`) and for a full-ring grid (`grid_build.py:153-156`) | DV |
| `search.links` | `search/links.py:28-55` | pre-mesh value substitution | **Yes for native families only**; generator block raises (`search/links.py:36-37`) | DV |
| bridge rows types | `catalog.gui.yaml:3-9` | `grid._rows_check_spec` refuses unknown types | **No on the stock path**; process-local CLI required | DV |

### Where modularity breaks

1. **Top-level `mode` can undo the mounting flip.** `to_mesher_config` sets `cfg["mode"]="enclosure"`
   at `families.py:696-698`, then copies every `section=="top"` key from `design.params` at
   `families.py:702-710`; a design carrying `mode` would overwrite it while the `enclosure`
   section stays. No shipped native config sets `mode` (checked under `examples/`), so this is a
   latent ordering hazard, not a current failure. *(PI)*
2. **“Independent” knobs are not independent.** `gcurve_*` overrides `a_deg`; extension + `s1/s2`
   changes the meaning of `r0/a0` and disables the brief pin; `rot_deg` rotates radius and depth;
   `h` offsets the coverage inversion target; `n/q` vanish at `s=0`.
3. **A categorical cannot be searched honestly.** `morph_target` is an `int` `KeySpec`, so CMA gets
   a continuous [1,3] box rounded at denormalise (`space.py:148-152`); ICW `termination` is a
   string and cannot be a bound at all (`families.py:238-239`).
4. **Some YAML is inert for the resolved config.** `morph_*` keys are routinely present with
   `morph_target: 0` and are then inactive
   (`examples/typologies/home_landscape_2026-11-15/hl__ext_throat_hvlaw_v7.yaml:13-31`); the `az_*`
   block is often present with every amplitude pinned at 0 (same file, line 16); and `mode` lives in
   the native schema (`families.py:69`) but no shipped config in `examples/` sets it (rg over
   `examples/`). By contrast `gcurve_*` is exercised (16 files under `examples/`, e.g.
   `examples/typologies/shape_variants/osse_baseline__gcurve.yaml`).
5. **Rows span is not a free knob.** It is coupled to `mesh.quadrants`; every half/full kind that
   emits a b-term or bend forces the half model.
6. **The generator cannot express what the native FREEFORM can.** Only two cross-section stations;
   no intermediate t; no arbitrary 32-station stack; a non-elliptical generator mouth blocks native
   morph by policy (`registry.py:318-322`).

---

## 4. Existing analyzer tools and their documented limits

| tool | what it does | documented / code limits | status |
|---|---|---|---|
| `tools/analysis/parameter_activity.py` | Resolves one native config, records every control as `searched/fixed/derived/conditional/inactive/unresolved`, with unit, `[0,1]`/log transform, application predicate, affected geometry features, `file:line` refs, static-source evidence, and an optional canonical-surface perturbation (`1-22`, `560-606`). Emits `active_projection` for a **proven** no-op (currently only `morph_exponent` at target 1) and refuses the projection otherwise (`586-606`). | Native-oriented: builds a `DesignSpace` (`512-519`) and labels the payload `kind: "native"`, `generator: None` (`615-625`). It does **not** prove generator/rows activity. Geometry sampling may be refused and is reported rather than hidden (`286-320`). Task eligibility is explicitly `insufficient_evidence` (`636-641`). | DV (limits drawn from the file) |
| `tools/analysis/geometry_effects.py` | Canonical final-surface sampler: `bo.data.materialize_geometry` → `hornlab_mesher.config_builder.resolve_geometry`; preserves meridian/azimuth/t stations, H/V/diagonal meridians, cross-sections, area/aspect, convergence check (`1-16`, `48-82`). | **Refuses CAD and point-grid recipes** (`14-15`; `bo/data.py:908-910`), then refuses any sampled surface whose axial stations are not monotone at some azimuth — folded/rollback walls are “non-star-shaped”, not flattened (`104-124`, `174`, `182`, `387-393`). Convergence is sampling convergence, explicitly not mesh/acoustic convergence (`11-12`). `bo.data` does admit the versioned rolled-family recipe (`bo/data.py:871-905`), but a rolled/backward body then hits the star-shape refusal. | DV |
| `tools/analysis/geometry_descriptors.py` | Deterministic, score-free descriptors: 9 numeric geometry keys + H/V/diagonal ratios (`39-54`), plus PCA+k-means navigation that never ranks (`172-177`, `274-301`). | Supports only OSSE/R-OSSE/ICW/FREEFORM (`112`); **refuses MEH** (`118-119`), **mid_ports** (`120-121`), **CAD** (`122-123`), **point-grid** (`124-127`). Uses `mode: bare` so shells/mounting do not affect descriptors (`141-145`). Default resolution 8 mm (`28`). | DV |
| `tools/analysis/links.py` | Proposes `links:` entries from run data: top-decile Spearman `|ρ|≥0.6` + least-squares `knob_b=scale*knob_a+offset` with R², plus CMA covariance eigen-directions whose top 2–3 loadings carry ≥0.85 (`1-11`, `26-28`, `60-74`, `78-118`). | Statistical co-movement only; it proposes a link, it does not prove a physical dependency or test the linked model. Needs ≥5 top-decile rows (`52-53`). Reads run artifacts, not geometry. | DV |
| `hornlab_search/search/links.py` | Applies a `links:` map: removes the child from the CMA dimension, computes it from the parent before meshing, clips to `[min,max]`; one level only, cycles excluded, unknown knobs a config error (`1-12`, `28-55`, `70-87`). | **`search.links is not supported with a generator block`** — explicit `ValueError` (`36-37`). It implements a linear link, not a conditional/dormancy model: it cannot express “inactive unless `morph_target==3`”. | DV |
| `tools/analysis/parameter_study.py` | Downstream report: reads the B2 activity ledger (never re-derives it), selects 3–5 designs, adds geometry descriptors and ExtraTrees diagnostics. | Native-only cohort; descriptive only below 100 unique observations / experiment groups; “no recommendation” when held-out validation does not beat the training mean (`1-22`). | DV |
| `hornlab_search/design/params/*` (adjacent prior art, not an analyzer) | Frozen parameter-catalog layer with flags `overloaded`, `derived`, `not_a_knob`, `doc_mismatch`, `pinned_by_brief`, `deferred` (`schema.py:17-25`); documents name/unit/context/formula/`code_ref`. | It documents; it does not prove activity or geometry. Numbers are read from `registry.DEFAULT_KNOBS` / `families.FAMILY_KEYS`, never typed (`schema.py:7-10`). | DV |

**Do not invent a parallel tool.** The activity vocabulary, predicate column and `active_projection`
already exist in `parameter_activity.py`; the geometry sampler already exists in
`geometry_effects.py`; the cross-run co-movement proposer already exists in
`tools/analysis/links.py`. Any new evidence pass should extend these, or state exactly which of
their documented refusals it is bypassing.

---

## 5. Alternative representations (unranked, no recommendation)

Listed only where the evidence above supports them. Tradeoffs and incompatibilities are stated
against the *current* code paths.

### (a) Keep specialized physics families; unify data/search/provenance only
- **What it is:** keep OSSE/R-OSSE/ICW/FREEFORM/grid/rows/CAD as today; one typed recipe record
  (`family`, `kind`, `brief_hash`, knobs, bounds) and one activity/descriptor contract across them.
- **Existing hooks:** `DesignSpace`/`GeneratedSpace` already share the vector interface
  (`generated.py:1-12`, `space.py:119-154`); `provenance()` already emits `{name, spec, knobs,
  brief_hash, derived}` (`generated.py:243-249`); the params catalog already carries the flag
  vocabulary (`schema.py:17-25`).
- **Tradeoffs:** lowest physics risk and preserves published labels (R9 gates are per-typology).
  But it preserves every per-family conditional table (`families.py:52-305`, `grid.py:139-270`
  ), so activity/dormancy must be solved per family; `search.links` stays unavailable to generators
  (`search/links.py:36-37`); categorical knobs still need a non-CMA mechanism.
- **Incompatible with:** a single canonical sampler/descriptor over all bodies — CAD, point-grid and
  folded surfaces are refused by `geometry_effects.py:14-15,104-124` and
  `geometry_descriptors.py:112-127`. One geometry hash is also not shareable: a grid design hashes
  its recipe, not its surface (`grid.py:75-78`, `2881-2891`).

### (b) Composable profile grammar with explicit conditional parameters
- **What it is:** a meridian/azimuth expression grammar with typed units, named sub-expressions,
  and declared `active_when` predicates (parameter, operator, span), so a splice/blend/lip/fold is
  data rather than a new kind.
- **Existing hooks:** `azlaw_expressions` is already a small expression generator
  (`families.py:150-184`); the mesher already evaluates parameter expressions per azimuth
  (`eval_param` use in `profile_formulas.py:155-172`, `profile_morph.py:10-38`); dormancy guards
  already exist in `rolled_family.validate_search_config` (`221-252`) and
  `klangfilm_lame_hv_family.validate_search_config` (`165-176`); `parameter_activity.py` already has
  the predicate/projection vocabulary.
- **Tradeoffs:** expresses H/V asymmetry, blends, splices, lips, folds and per-azimuth laws without
  new engines; makes dormancy declarable and checkable. But it risks a DSL with silent no-ops,
  per-azimuth evaluation cost, and operator/units ambiguity (the mesher already has `a_deg` as a
  half-angle while briefs speak total included angle, `families.py:244`). It still cannot express a
  multi-entry body or a boolean CAD topology.
- **Incompatible with:** the current `KeySpec` whitelist model — a grammar key not in the family
  table is rejected (`families.py:610-616`), and the mesher silently ignores unknown profile keys
  (`families.py:7-9`), so the grammar must be validated before the mesher, not by it.

### (c) Shared physically-constrained freeform surface (one body representation)
- **What it is:** one spline/subdivision/level-set body with declared constraints (throat circle +
  tangent, envelope, self-intersection, convexity, smoothness), decoded to the mesher. Every
  family becomes an initializer + constraint set.
- **Existing hooks:** the rolling/rows machinery already builds explicit inner+outer point grids and
  checks `2t+2` self-approach (`grid.py:661-732`, `1629-1746`); rolled family already builds
  inner+outer and refuses relief-induced constriction (`rolled_family.py:160-192`); the mesher's
  `PointGridHornGeometry` accepts arbitrary point grids (`grid_build.py:185-194`).
- **Tradeoffs:** the only route that naturally covers rollback/asymmetric/swept surfaces and CAD
  bodies; removes the star-shaped assumption. But it loses the published-family parameterization
  and its R9 provenance; search becomes constrained optimisation (envelope, convexity,
  self-approach) rather than a box; and BEM source closure/tagging must be re-proved. It also
  requires new mesher/fork capability, which is outside a focused search-layer slice.
- **Incompatible with:** `geometry_effects.assert_star_shaped` (`104-124`) and the 9-key descriptor
  contract (`geometry_descriptors.py:39-54`), which assume a single-valued radius field about the
  axis; the descriptor contract also refuses grid/CAD today.

### (d) Latent / descriptor shape search
- **What it is:** search in a low-dimensional geometry descriptor or learned latent space, decode to
  a surface, evaluate acoustics as today.
- **Existing hooks:** `geometry_descriptors.py` already produces deterministic score-free vectors and
  PCA/k-means navigation (`172-177`, `274-301`); `geometry_effects.py` already samples canonical
  surfaces without meshing; `bo` already has a native design/vector projection layer
  (`hornlab_search/bo/data.py:871-910`).
- **Tradeoffs:** small search dimension, reuses existing descriptors, and can cover families whose
  knob spaces are incomparable. But the descriptor contract is not invertible (no decoder exists);
  the current sampler refuses the folded/CAD/grid surfaces where the interesting shapes live; a
  latent space is not physically constrained; and published typology labels/provenance would be
  carried as metadata only. Objective correctness still depends on the same BEM path.
- **Incompatible with:** `search.links`, which assumes named parent/child knobs (`search/links.py:70-87`),
  and with the current `Design` hash/recipe provenance for generators (`generated.py:224-241`).

### (e) Topology-first body graph for multi-entry / source-mounted horns
- **What it is:** model the horn as a body graph (throat/coupling plane, wall patches, ports/entries,
  mouth termination, mounting), with profile law attached per patch. Multi-entry and CAD bodies are
  first-class instead of a `mid_ports` dict or a whole STEP tool.
- **Existing hooks:** MEH already implements the topology in CAD with labelled entries/tags
  (`step_build.py:100-140`); native OSSE has `mid_ports` as an opt-in patch with `walls/z_frac/
  across_frac/port_along_mm/slide_mm` (`families.py:218-224`, `457-479`); the enclosure route is
  already a separate topology (`families.py:629-673`, `grid_build.py:150-156`).
- **Tradeoffs:** the only candidate that addresses multi-entry, source mounting and asymmetric
  entry layouts without pretending they are a meridian. But it needs boolean/STEP-quality authoring,
  tags and source closure per entry, and a mesh-quality story the formula path does not have. It
  also multiplies the parameter surface (layout knobs are not shape knobs).
- **Incompatible with:** the FREEFORM/OSSE formula route (which cannot represent a second entry) and
  with the point-grid outer-shell convention (a single swept sheet). `geometry_descriptors.py`
  explicitly refuses MEH/mid_ports (`118-121`).

---

## 6. Contradicted / uncertain claims and what would settle them

| claim (source) | status | evidence | what would settle it |
|---|---|---|---|
| Brief: HEAD = `2c0e292` = `origin/main`; a given dirty set | **CX** | re-read 19:38:59: HEAD = `3efe9be`; origin/main = `2c0e292`; tree dirty in different files and more of them (header) | re-read the tree at the intended SHA, or confirm the 3 local commits are in scope |
| Brief: `design/generators/grid.py` is 2813 lines | **CX** | file is 3020 lines (read toolline count; mtime 19:26) | none needed; line numbers here are from the current working tree |
| Citations are anchored to a stable commit | **CX** | HEAD unchanged, but working-tree files changed mid-pass: `klangfilm_lame_hv_family.py` 7,707→9,650 bytes at 19:32:57; `generated.py`/`grid.py`/`build.py` mtime 19:26 (same-line klangfilm dispatch edits) | freeze a SHA/worktree snapshot and re-derive line numbers; treat this doc as timestamped evidence, not a commit-stable map |
| `size_policy: report_only` is safe because the search layer still enforces the envelope | **PI** | family's own check is relaxed (`klangfilm_lame_hv_family.py:116-129`), and the comment says so (`32-35`, `177-182`); `evaluate.py:1216` and `1438` call `envelope_violation` after meshing | build an over-envelope `report_only` design and confirm the rejection comes from `search/evaluate.py`, not the family |
| “FREEFORM refuses a morphed non-elliptical cross-section” (`registry.py:47-50`) | **CX (as a mesher statement)** | the generator refuses to construct it (`registry.py:315-322`); the mesher only refuses a **morph-induced non-convex outline** (`freeform.py:1874-1903`, validated at `1955-1963`) | mesh a FREEFORM design with `crossSections` superellipse + `morph_target` 1/3 through `build_mesh`; if it builds and is convex, the mesher does compose it |
| R-OSSE has no morph keys and no example config (`docs/research/typologies/SEARCH_LAYER_GAPS.md:52,71,75`, dated 2026-10-22) | **CX** | `_ROSSE` includes `_MORPH` (`families.py:227-234`); `examples/rosse_baseline.yaml` exists | doc is stale; re-run the gap pass at current HEAD |
| OSSE lacks morph/gcurve exposure (`SEARCH_LAYER_GAPS.md:44`) | **CX** | `_OSSE` includes `_MORPH` and `_GCURVE` (`families.py:211-225`); `ath_core.yaml` searches morph | same |
| `_GCURVE` keys are “exposed but unused” (`SEARCH_LAYER_GAPS.md:42,46`) | **CX** | 16 files under `examples/` set `gcurve_*` (e.g. `examples/typologies/shape_variants/osse_baseline__gcurve.yaml`); `gcurve` is legal on OSSE only (`families.py:211-234`) | count configs at HEAD; the doc predates the gcurve campaign cells |
| “Real rollback stays with R-OSSE and ICW-rollback” (`docs/TYPOLOGY_PLAN.md:83-84`) | **CX** | rows/rolled point grids represent non-monotone axial stations explicitly (`grid.py:2503`, `examples/typologies/salmon_elliptical.yaml:12-13`); mesher builds them (`grid_build.py:185-194`) | the plan predates WP9b; mark it superseded |
| `search.links` cannot be used with generator blocks | **DV** | `search/links.py:36-37` raises | none |
| `geometry_effects` rejects non-star-shaped surfaces | **DV** | `geometry_effects.py:104-124`, `174`, `182` | none |
| `geometry_effects` rejects CAD and point-grid | **DV with a nuance** | it refuses via `bo.data.materialize_geometry` (`bo/data.py:908-910`), **but** that function admits the versioned rolled-family recipe (`871-905`); a rolled body then normally fails `assert_star_shaped` | run `geometry_effects` on an `rf__rect_radial_v7` design and record where it stops |
| `morph_target` is “searched” (`registry.py:347-350`) | **DV but discrete** | it is an `int` KeySpec (`families.py:73`) over a continuous bound (`examples/typologies/ath_core.yaml:64`), rounded at denormalise (`space.py:148-152`) | decide whether a categorical is acceptable as a continuous coordinate (policy, not code) |
| `a_deg` and `coverage_h_deg` mean the same angle | **CX** | `a_deg` is a **half**-angle (`families.py:53`, `families.py:244`); brief coverage is the **total included** angle (`enclosure_1in.yaml:30`) | an objective-level unit test comparing achieved −6 dB angle to the target |
| A native OSSE `a0_deg` is pinned by the brief | **conditional** | only under `throat_angle_policy: pin` and only without an extended throat (`config.py:1219-1224`); generator typologies always take the brief angle (`registry.py:246-247`); `osse_baseline.yaml` searches `a0_deg` 2–30° with no brief | compare two configs (native OSSE vs generator) on the same brief and log the actual throat angle |
| A design carrying `mode` plus a mounting brief still meshes as an enclosure | **PI (latent hazard)** | `families.py:696-698` sets `enclosure`, then `families.py:702-710` copies top-level params including `mode` | build such a config and inspect the mesher config / mesh mode |
| Ripple/harmonic/bend knobs are ordinary search knobs | **CX** | list knobs are recipe-only (`grid.py:368-388`, `generated.py:142-155`); only the scalar `g_stop_a2` alias is searchable (`grid.py:357-367`) | check the run's search keys for `g_stop_cos2k`; expect absence |
| `lecleach_ar` and `iwata_ar` are distinct constructions | **PI** | both call `lecleach_ar_profile`; only defaults/knob names differ (`grid.py:2267-2298`, `2325-2347`, `267-270`) | diff the emitted grids for equal parameters |
| Bridge configs (`rolled_rect`, `rosse_rect`, `crowe_panel`) run through the stock search | **CX** | not in `ROWS_TYPES` (`grid.py:139-141`); `_rows_check_spec` refuses (`903-916`); `examples/catalog.gui.yaml:3-9` says a CLI is required | `load_config` + `DesignSpace` on `rr__reference_v7.yaml` without the CLI |
| The enclosure mounting model is exercised by a catalogued config | **UN / likely no** | `rg -l enclosure_1in examples` returned only the brief itself; no example config references the mounting block | check `runs/` configs for `mounting:`; otherwise this is dormant surface |
| An R-OSSE `R_mm` independently sets mouth size and length | **DV** | `knobs_native.py:977-998` states it changes both; there is no `L_mm` for R-OSSE (`families.py:276-282`) | a geometry perturbation of `R_mm` at fixed other knobs |
| Grid/rows designs are cache-keyed like native designs | **CX** | `mesh/build.py:328-331` says the grid route has no mesh cache and writes no `mesh_meta.json`; the grid docstring explains the recipe hash reason (`grid.py:75-78`) | inspect a grid run directory for `mesh_meta.json` / cache entry |

---

### Residual unknowns (explicit)

- No run was made, so every “reaches the meshed surface” statement is a **source-path** statement.
  Whether a specific YAML/knob vector builds is unverified here.
- `icw_seed`/`icw_coeffs`/`icw_S` semantics beyond the family table were not traced into the mesher;
  they are listed as documented keys only.
- The exact mesher version was not recorded (the pin lives in `pyproject.toml`/`TOOLCHAIN.md`); line
  numbers cited from `.venv/Lib/site-packages/hornlab_mesher` are for the installed copy at the time
  of this pass.
- `docs/research/typologies/**` was sampled, not exhaustively read; the only doc claims contradicted
  above are the ones with concrete code lines against them.

