# Construction contracts: Crowe V2A area/aspect law and Crowe-X on OS-SE CD

Drafted 2026-11-18 against HornFab main @1d6ebc8. Read-only review; no solves, meshes, BEM or tests run (`scipy` and `hornlab_mesher` are not importable here). Labels: [published] [derived] [reconstruction] [original-hypothesis] [code-verified] [unverified]. Paths relative to repo root. Two independent contracts; claims do not transfer between them.

---

## CONTRACT A: `crowe_hv_area_aspect_v1` (V2A forward area/aspect law)

### A1. Identity

| Item | Value |
|---|---|
| construction_id | `crowe_hv_area_aspect_v1`, schema `crowe-hv-area-aspect-v1` (`crowe_hv_area_aspect_v1.py:59-60`) |
| Route | `generator.name` on `family: FREEFORM`; `materialize()` (`:313`) emits profileH/profileV plus `crossSections` |
| Status | Crowe-inspired, our construction, not Crowe CAD (`info()` `construction_label`). Law: [original-hypothesis]. `C(p)`: [derived] (Lamé). |
| Code / tests | `hornlab_search/design/generators/crowe_hv_area_aspect_v1.py` (618 lines); `_lame_cap_v1.py:38-41`; tools `tools/geometry/crowe_hv_area_aspect_{sections,jacobian}.py`; tests `tests/test_design_generators_crowe_hv_area_aspect.py` (not run) |
| Configs / dossier | `examples/typologies/crowe_hv_area_aspect_2026-11-16/` (c0-c3); addendum `docs/research/typologies/CROWE_V2A_THROAT_TRANSITION_ADDENDUM_2026-11-16.md`; `docs/evidence/CROWE_HV_AREA_ASPECT_V2A_2026-11-16.md`. Introduced 2026-11-16. |

### A2. Lineage

| Ancestor (as cited in the addendum; papers not re-checked) | Supports | Does not support |
|---|---|---|
| Superellipse section area `C(p)=4Γ(1+1/p)²/Γ(1+2/p)` [published math] | Section area and `p=2` circle identity | Any acoustic claim |
| Batík OS-SE section 5, power onset / no slope break [published] (addendum S1) | Motivation for C2 onset of the aspect law | That V2A is OS-SE |
| Batík ATH CORE, fixed part 0, morph rate 3 [published] (S2) | Justifies the default hold 0 (smooth start at the throat) | Transfer to HF1440 or Crowe geometry |
| Cinanni hybrid CD horn: separate area and aspect controls [published] (S3) | Keeping `A(u)` and `R(u)` as separate controls | That equal area means equal acoustics |
| Keele Bi-Radial / Manta-Ray: H/V progression matters at LF [published] (S12-13) | Aspect development as a design variable | That this shell holds 50 V at 700 Hz |
| Crowe ES-600/450 H/V area progression [reconstruction] | Name and inspiration only | Any dimension or equation |

### A3. Operator order

Coordinates: `z` (mm), `u = z/L_forward` in [0,1]. No azimuth: each station is a planar superellipse, semi-axes `a` (H), `b` (V). No rollback (Phase 2).

1. `_validate_shape` (`:148`): exactly four knobs (`PARAM_KEYS`, `:63`), fixed generator-block keys, `_BOUNDS` (`:83`), hold < L/2.
2. `evaluate` (`:224`): area law, aspect gate, exponent and radii on a 2049-point `u` grid. Refuses `m0` outside [0,2] (`:245`) and non-monotone forward radii (`_check_forward`, `:287`).
3. `materialize` (`:313`): envelope check against the brief (max W/H/depth). Anchors `u_i = ½(1−cos πs_i)`, n=29 (`_anchor_u`). Wall angles `atan(dr/dz)` by `np.gradient` on the dense grid, interpolated to anchors.
4. Stations: `t=0` circle; mid-anchor superellipses with `p(u_mid)`; `t=1` with `p_mouth`; a positive hold adds a `p=2` station.
5. Output is FREEFORM params. The mesher's `crossSections` interpretation is external; the addendum warns it may not keep the C2 law (§C).

### A4. Mathematics (as implemented)

Symbols: `A0=πr0²`, `A1=C(p_m)(W/2)(H/2)`, `Δ=ln(A1/A0)`, `L=L_forward`; `r0`=18 mm, `a0`=2° from brief (assumed). Units: mm, mm², dimensionless `p`, `u`, `S`; angles in degrees.

- `m0 = (2L·tan a0 / r0) / Δ`, required in [0,2] (`:244-250`).
- `ln A(u) = ln A0 + Δ·[m0·u + (1−m0)·u²] + β·(4u(1−u))⁴` (`:252`, basis `:218`).
- Timing: `q = u50/(1−u50)`, `w = u/(u + q(1−u))`, `S_R = smootherstep(w) = 10w³−15w⁴+6w⁵` (`_timing`, `:181`).
  - `S_R(0)=0`, `S_R(1)=1`, `S_R(u50)=½`.
  - `S_R' = S_R'' = 0` at `u=0` and `u=1` [derived]: `dS/dw ∝ w²(1−w)²` and `w'(0)=1/q` is finite, so the chain rule gives zero at both ends. Test: `:105` (not run here).
- `ln R = ln(W/H)·S_R`; `p = 2 + (p_m−2)·S_R` (`:257-258`).
- `C(p) = flat_lame_area(1,1,p)`; `a = √(A·R/C(p))`, `b = √(A/(R·C(p)))` (`:262-263`).
- Section: `|x/a|^p + |y/b|^p = 1`, planar area `C(p)·a·b = A` exactly [derived]. Mouth: `a=W/2`, `b=H/2`, `p=p_m` (test `:54`).
- Source tangent: `a'(0)=b'(0)=tan a0` because `R'(0)=p'(0)=0` and the linear `m0` term sets `d ln A/dz|0 = 2 tan a0 / r0` [derived; test `:79`].
- Hold `h = throat_round_hold_mm/L`: gate `= S_R((u−h)/(1−h))` with `u50' = (u50−h)/(1−h)`. Circular for `u ≤ h`, C2 at `h` (`_aspect_gate`, `:208`; test `:152`).
- Area meaning: **planar superellipse section area** `A(z)=C(p)ab`. Not a curved-cap area (the cap math in `_lame_cap_v1` is not used by V2A) and not a wavefront area.

### A5. Parameter ownership

| YAML key | Operator | Effect | Status | Bounds and source |
|---|---|---|---|---|
| `height_v_active_mm` | `evaluate` | Mouth H, `A1`, aspect | searched (c1) | c1 [300,474]. Module: >0 only. Envelope 480 from brief. [proposed] |
| `L_forward_mm` | `evaluate` | Depth, `m0` | searched (c1) | c1 [220,340]. Module: >0. Envelope 480 from brief. [proposed] |
| `area_mid_bias` | `_area_mid_window` | Local mid-area bulge | searched (c1) | c1 ±0.15 = module `_BOUNDS` `:83`. [proposed] |
| `aspect_timing_u50` | `S_R` | When H/V aspect develops | searched (c1) | c1 [0.35,0.65]. Module [0.15,0.75]. [proposed] |
| `width_h_active_mm` | `A1`, `R` | Mouth W | fixed 580 (c0-c3) | Brief envelope 600 |
| `p_mouth` | `A1`, `p(u)` | Mouth exponent | fixed 3.25; A/B 2.2 (c3) | Module [2,5]; `p≥2` needed by `flat_lame_area` |
| `throat_round_hold_mm` | gate | Circular hold | fixed 0; A/B 20 (c2) | Module [0,200), `<L/2`; never a search knob |
| `n_anchors` / `wall_thickness_mm` | `materialize` | Anchors / wall | fixed 29 / 3.0 | Module [9,32] / [0.5,12] |
| `driver` r0 / exit angle | `m0`, `a` | Source | brief: 18 / 2 | 2° assumed, not measured |

### A6. Zero-control identities

| Setting | Recovers | Exact? | Test |
|---|---|---|---|
| `throat_round_hold_mm=0` (default) | No circular hold; smooth start at throat | Exact by construction [code-verified] | `:152` covers hold 20 only |
| `area_mid_bias=0` | Pure quadratic log-area law (set by `m0`) | Exact [derived] | `:140` covers 0.15 only |
| `W=H` and `p_mouth=2` | All stations circular (`R≡1`, `p≡2`) | Exact [derived] | No test located |
| `m0` at 0 or 2 | Edge of monotone domain | Refused outside [0,2] | `:203` |


### A7. Seeds and provenance

- **c0**: 580×474×300, hold 0, p 3.25, `u50` 0.5, bias 0; all bounds fixed. Authors' geometry diagnostic, no solve. **c1**: owner-gated box, budget 200. **c2** (hold 20) and **c3** (p 2.2): A/B of c0. None queued or referenced by `docs/queue/` or catalogs [code-verified, grep].

### A8. Objective fit

All four configs point `brief_file` at `examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7_smooth.yaml`: `di_slope_target 5`, `cov` tolerance 8, `cov_narrow_ratio 1`, `di` weight 0 [code-verified]. This is the non-CD variant, chosen because a smoothly narrowing horn should not be scored as CD. Its J values are not comparable with the base brief (brief header). V2A has no objective score, no BEM and no acoustic result.

### A9. Verification status

- **Analytic:** A4 by hand [derived]; hand check `m0(c0) ≈ 0.21`, inside [0,2].
- **Tests:** present (`:54`, `:79`, `:105`, `:236`, `:272`); not run.
- **Author-reported, not re-run (README):** c0 at 20 mm area 1.102× throat, `|aspect−1| = 5.4e-4`; T2 practical rank 4; quarter mesh 8,318 triangles, closed.
- **Not verified:** BEM, measured response, mesher C2 realisation. **Gaps:** no X crease, lip or rim setback (Phase 2). The docstring understates `(4u(1−u))⁴` (vanishes to third order; harmless).

### A10. CPU-first checks and open questions

1. Install `scipy`, run the V2A tests (CPU). Add a `W=H, p_mouth=2` circularity test. Finite-difference the realised `crossSections` (export only) against `S_R'`, `S_R''`. Sweep c1 corners for `m0 ∈ [0,2]`.
- **Q1.** Is a 2° source angle acceptable for an unmeasured HF1440 interface? **Q2.** Should `p_mouth` stay fixed? **Q3.** Should V2A keep the non-CD brief or get its own objective?

---

## CONTRACT B: `hl__crowe_x_osse_cd_v7` (Crowe-X on OS-SE CD throat)

### B1. Identity

| Item | Value |
|---|---|
| construction_id | `hl__crowe_x_osse_cd_v7` (`examples/typologies/home_landscape_2026-11-15/hl__crowe_x_osse_cd_v7.yaml`) |
| Generator | `generator.name: grid`, `rows.type: osse_rollback`, `span: quarter`, `n_phi 25`, `n_s 40`, `wall_thickness_mm 3.0`, `seed_policy: explicit` (YAML `:18-26`) |
| Code | `hornlab_search/design/generators/grid.py`: knobs `:1912-1931`, `:1939`; marches `:2010-2072`; lip `:2108`; dispatch `:2171`, `:2663`, `:2970` |
| Status | [original-hypothesis]. Code label `OSSE_ROLL_LABEL` (`:1932`): "labeled hypothesis-shape experiment ... no published name is used". Not Crowe geometry, not a published construction. |
| Tests / study | `tests/test_design_generators_grid_osse_rollback.py` (skips here: `importorskip("hornlab_mesher")`); `docs/research/typologies/BIRADIAL_CROWE_STUDY_2026-11-15.md`; `docs/research/CROWE_X_HORN_HANDOFF_2026-11-15.md`; catalog `examples/catalog.yaml:411`. Rows type 2026-10-28; YAML 2026-11-15; seed 2026-11-16. |

### B2. Lineage

| Ancestor | Supports | Does not support |
|---|---|---|
| OS-SE / OSSE per-azimuth wall `profile_points` [published, external formula]. Attributed "Magnus's" in code (`grid.py:1908`, YAML header) but to Batík OS-SE in the V2A addendum | Per-row meridian shape; CD intent for the axisymmetric case | Non-axisymmetric CD; attribution is unresolved in the repo |
| Crowe ES-600/450: exponential flare, X creases, bow-tie, ~270° roll [published, secondhand as cited in the handoff; not re-checked] | Target look only | Any dimension. The YAML says the ES flare is not reproduced, and HF beaming differs |
| Gielis superformula [published math] | The X morph form `sf(φ)` | That it models Crowe |
| Tangent-continuous curled lip (`grid.py:2108`) [original-hypothesis], self-labelled "[inferred]" | C1 continuity of the roll | That it matches Crowe's rolled lip (max wrap 200°, searched ≤160°) |

### B3. Operator order

Coordinates: `x` (axial, mm, from coupling plane), `y` (radius, mm), `φ` (azimuth, rad; origin on +x, `grid.py:814`), `σ` (normalized arc length of the OSSE wall), `wrap` (deg). Rollback = 2D circular arc in the meridian plane (not a torus; `_append_lip_torus` is not used here).

1. Coupling plane: `r0 = 18` mm at `x=0`, round (test `:32`).
2. Azimuth law, per row: `a(φ) = a_h·cos²φ + a_v·sin²φ` in degrees (`a_fold=2`, `a_union=0` by default; `:2026`, `:2037`).
3. OSSE wall: `profile_points({type OSSE, r0, a0, L, a(φ), k, s, n, q}, 400, φ)` (`:2038-2045`). Validity: `x` strictly increasing, `y > 0`.
4. Superformula morph of radius (`:2052-2056`): `y ← y·[1 + sf_amt·w(σ)·(sf(φ)/mean_sf − 1)]`, with `w = smoothstep((σ − sf_start)/(1 − sf_start))` (`_rows_eps_window`, `:807`). `σ` is arc length of the OSSE wall, **not** `z/L`.
5. Ripple (flutes): off unless `ripple_lobes > 0`. Absent from the YAML.
6. End tangent `end_deg = atan2` of the last segment of the **morphed** wall (`:2062`).
7. Lip: arc of radius `r_lip` tangent to the wall at the end, sweeping `wrap` (× `(1 + wrap_cos_amp·cos Nφ)` only with ripple). Stop angle `= end + wrap` (`:2065`, `:2108-2137`).
8. Assembly: quarter-span rows mirrored to a full circle (`_full_circle`, `:645`). Wall offset by 3 mm (`grid_outer_points`, `:679`). Self-approach (`:661`) and envelope (`_rows_envelope_extents`, `:2817`) checks. Not traced line by line.

### B4. Mathematics (as implemented)

- Wall angle: `a(φ) = a_h cos²φ + a_v sin²φ` (deg). `a_h` is the nominal horizontal half-angle at `φ=0`.
- Superformula: `sf(φ) = (|cos(mφ/4)|^n2 + |sin(mφ/4)/ab|^n2)^(−1/n1)`, with `n3 = n2` and `a = 1` (`:2017-2021`). `m` even, `sf_ab ≠ 1` needs `m ≡ 0 mod 4` (`:1986`).
- `mean_sf` is the mean over the full circle, 4096 samples, global and not per row (`:2023`).
- Morph sign: diagonal bulge is confirmed by test `:88` for an extreme box (`y(45°) > 1.5 · y(0)`). Seed values were not run.
- Morph is multiplicative on radius and not area-normalized. Mouth size changes with `sf_amt` [derived].
- Lip: centre `(x_end − r sinψ0, y_end + r cosψ0)` with `ψ0 = end − 90°`. Arc of radius `r` over `wrap`, C1 at the joint (`:2108-2137`).
- Units: mm, deg, dimensionless `σ`, `φ`. No area law and no area parameter. **Section area is undefined by the generator**: it is an emergent result of wall, morph and lip. Not planar, not cap, not wavefront.
- Coverage: `a_h`, `a_v` are nominal OSSE half-angles. Morph and lip change the mouth radius, so effective coverage differs from nominal [derived].
- CD: constant directivity holds only per row for the axisymmetric OSSE. No test or analysis in the clone shows CD preserved after morph and lip.

### B5. Parameter ownership (YAML)

| YAML key | Operator | Effect | Status | Bounds and source |
|---|---|---|---|---|
| `g_a_h_deg` | OSSE, φ=0 | H coverage and width | searched | YAML [33,40] (study box). Module [5,85] (`:1939-1957`). Seed 36.39 from screen run `620f81` (external, `runs/` absent) |
| `g_a_v_deg` | OSSE, φ=90 | V coverage | searched | [20,28]; module as above |
| `g_L_mm` | OSSE depth | Envelope W, H, depth | searched | YAML `hi: 285` (`:56`). Header `:14` says widened to 320 on 2026-11-16, **not reflected in the file**. Module [10,1000]. Unresolved. |
| `g_s` | OSSE termination | Mouth flare | searched | [0.2,0.45] (study box, `s=0` is a flat cone) |
| `g_n` | OSSE termination | Bowl vs plate | searched | [1.8,3.2] (study box) |
| `g_r_lip_mm` | Lip | Roll radius | searched | [8,30]. Module cap `ROWS_MAX_R_LIP_MM=100` (`:170`) |
| `g_wrap_deg` | Lip | Roll angle | searched | [80,160]. Module cap 200 (`ROWS_OSSE_ROLL_MAX_WRAP_DEG`) |
| `g_sf_m` | Superformula | Symmetry (4 corners) | fixed 4 | Module even in [2,16] |
| `g_sf_n1` / `g_sf_n2` | Superformula | Corner sharpness / edge straightness | fixed 1.8 / 7.0 | Module >0 |
| `g_sf_ab` | Superformula | Stretch (<1 wider) | searched | [0.7,0.9] (study box). Module >0 |
| `g_sf_amt` | Superformula | X strength | searched | [0.15,0.38] (study box). Module ≤1.5. Zero turns the morph off. |
| `g_sf_start` | Superformula | Onset (arc fraction) | fixed 0.25 | Module [0,1) |
| not in YAML | `ripple_*`, `wrap_cos_amp`, `a_fold`, `a_union`, `union_blend_deg` | Off by default | — | Module defaults `:1912` |

`g_k` 1.0 and `g_q` 0.996 are fixed. `sf_n1`, `sf_n2`, `sf_ab`, `sf_start` are inactive when `sf_amt = 0` (`domains_extract.py:105`). No box is historically tested in this clone.

### B6. Zero-control identities

| Setting | Recovers | Exact? | Test |
|---|---|---|---|
| `g_sf_amt = 0` | No superformula (morph off) | Exact by code (`:2052` condition) [code-verified] | No test for `amt=0`; `:88` covers `amt>0` only |
| `g_r_lip_mm = 0` | No lip; row ends at the OSSE wall | Exact, early return (`:2108` branch) | `:42` (row 0 only, ripple off) |
| `g_a_h_deg = g_a_v_deg` | Axisymmetric OSSE; all rows identical | Exact by formula [derived] | `:42` uses 45/45, row 0 only |
| Ripple off (default), `amt=0`, `r_lip=0`, `a_h=a_v` together | Parent: axisymmetric OS-SE throat (external formula) | Exact modulo the external formula | `:42`, row 0 |

### B7. Seeds and provenance

- **Main YAML seed:** `a_h 36.389`, `a_v 22.708`, `L 259.60`, `s 0.390`, `n 2.144`, `q 0.996`, `r_lip 18.28`, `wrap 86.09`, `sf_ab 0.848`, `sf_amt 0.239`; fixed `sf_m 4`, `sf_n1 1.8`, `sf_n2 7`, `sf_start 0.25`, `k 1`. Header provenance: "best of `runs/20261116T074832Z-screen-620f81` (J 5.344)". `runs/` is absent from the clone, so **unverified**.
- **Diverged duplicate:** `docs/queue/rolled_readiness_2026-11-15/configs/hl__crowe_x_osse_cd_v7.yaml` (`a_h 38`, `a_v 24`, `L 240`, `wrap 130`, `sf_amt 0.3`, `g_L_mm hi 260`, Windows brief path). Not the same seed or box.

### B8. Objective fit

- `brief_file` = `examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml`: strict CD scoring (`di_slope_target 0`, `cov_narrow_ratio 2`, `di` weight 0.3, cov tolerance 3, `cov_v_weight 0.5`) [code-verified]. This is consistent with the CD claim.
- Queued in `docs/queue/home18_a_2026-11-16.yaml:39,48`, `home18_b_2026-11-16.yaml:87`, `home_day_2026-11-16.yaml:143`. Queue presence is not run results.
- Envelope refusals: 21/24 reported (`docs/queue/HOME_18H_PLAN_2026-11-16.md:30,172`). BoTorch cannot encode `osse_rollback` rows (`:158,174`), so CMA only.
- J is not reproduced here. `HOME_SCORE_AUDIT_2026-11-16.md` records ranking sensitivity in a single run, not a validated metric.

### B9. Verification status

- **Analytic / tests:** from code reading [code-verified, not executed]. Tests skip without `hornlab_mesher`.
- **Sampled / meshed / BEM / measured:** cited in queue and HOME docs; no run artifacts in the clone. Seed J 5.344 **unverified**.
- **Gaps:** OSSE formula external (`hornlab_mesher.profile_formulas`), attribution inconsistent (Magnus vs Batík); morph mean is global, so mouth size shifts with `sf_amt`; no check that CD survives morph and lip; wrap capped at 200° and searched ≤160°, so no ~270° Crowe roll (not claimed); BIRADIAL study §5b ranges are stale against the YAML box; `g_L_mm` mismatch (B5).

### B10. CPU-first checks and open questions

1. Install `hornlab_mesher`, run the OSSE tests (CPU). Add `sf_amt=0` and all-rows `a_h=a_v` identity tests.
2. Pre-check envelope at seed and bound corners with `rows_grid_points`; locate the 21/24 refusals.
3. Compare per-row effective exit angles (`marches`) with nominal `a(φ)`. Reconcile `g_L_mm` (285 vs 320) and the two YAML copies.
- **Q1.** Is a CD brief valid for a morph-plus-lip design? **Q2.** OS-SE attribution: Magnus or Batík? **Q3.** Should the superformula mean be per row?
