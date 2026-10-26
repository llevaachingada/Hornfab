# SEARCH_LAYER_GAPS.md — Search-Layer Gap Analysis

**Date:** 2026-10-22  
**Source files examined:** `hornlab_search/design/families.py`, `design/space.py`, `design/custom.py`, `mesh/build.py`, `mesh/sizing.py`, `config.py`, `types.py`, `search/cma.py`, all `examples/*.yaml`, `docs/BOUNDARY_LAB_0.5_RESEARCH.md`, `docs/research/boundary_lab_0.5/`, `docs/plan/04_TASK_DESIGN_MESH.md`, `docs/plan/12_RESEARCH_BASIS.md`, `NOTES_FOR_SENIOR.md`, `docs/evidence/HANDOFF_6b.md`, `docs/evidence/CP-8c_data_summary.md`

---

## 1. Families: end-to-end support, searchable parameters, and gaps

### 1.1 OSSE (families.py:96-103)

**Status:** Fully supported (validate → to_mesher_config → build_mesh → solve). Two example configs: `osse_baseline.yaml` and `search_smoke.yaml` (both OSSE, screen mode). A third, `throat_adapter.yaml`, is also OSSE with throat-adapter knobs.

**Searchable parameters (KeySpec table `_OSSE`, families.py:96-103):**

| Key | Section | Note |
|-----|---------|------|
| `r0_mm` | profile | throat radius, mm |
| `a_deg` | profile | coverage half-angle, deg |
| `a0_deg` | profile | throat half-angle, deg |
| `k` | profile | OS/R-OSSE k |
| `q` | profile | termination q |
| `s1` | profile | throat stretch [0, 10] mm/deg |
| `s2` | profile | throat stretch [0, 10] 1/mm |
| `throat_ext_length_mm` | profile | extension length, mm |
| `throat_ext_angle_deg` | profile | extension angle, deg |
| `slot_length_mm` | profile | slot length, mm |
| `L_mm` | profile | axial length, mm |
| `n` | profile | termination n |
| `s` | profile | termination s |
| `rot_deg` | profile | rotation, deg |
| `h` | profile | half-sine bulge, mm |
| `exponent` | cross_section | superellipse exponent |
| `aspect_ratio` | cross_section | width-to-height scaling |
| `mode` | top | freestanding/bare/etc. |
| `wall_thickness_mm` | mesh | shell thickness |
| Plus full `_MORPH` set | morph | morph_target, morph_width/height/corner_mm, morph_rate, morph_fixed, morph_allow_shrinkage |
| Plus full `_GCURVE` set | gcurve | gcurve_type, gcurve_width_mm, gcurve_aspect_ratio, gcurve_dist, gcurve_rot_deg, gcurve_sf, gcurve_se_n, gcurve_sf_a/b/m1/m2/n1/n2/n3 |

**Mesher mapping:** All pass directly as the mesher's own keys; `to_mesher_config` routes by `KeySpec.section` into `profile`, `cross_section`, `mesh`, `morph`, `gcurve` sub-dicts. (families.py:432-466)

**Exposed in examples:** `osse_baseline.yaml` searches `a_deg, a0_deg, L_mm, n, s, q, k, exponent, aspect_ratio` (9 active dims). `throat_adapter.yaml` searches `throat_ext_length_mm, throat_ext_angle_deg, slot_length_mm, a0_deg, k` (5 dims). The GCURVE keys are in the table but **no example config exercises them**; the MORPH keys are now used by `ath_core` (native OSSE) and available to generated typologies (2026-10-25).

**Not exposed:** `rot_deg`, `h`, `s1`, `s2`, `slot_length_mm` (only `throat_adapter`), all 13 `_MORPH` and `_GCURVE` keys. `04_TASK_DESIGN_MESH.md` fork table (p.12) explicitly identifies MORPH and GCURVE (superformula) as "trivial, already there" table rows. Adding `gcurve_sf_a` etc. to a YAML config is the entire code change needed.

**2026-10-25 correction (later pass):** the morph half of this paragraph is superseded. `_MORPH` (including `morph_exponent`/target 3) is now legal on OSSE, R-OSSE, ICW and FREEFORM, and generated typologies can opt in through the generator's morph knobs. `ath_core` exercises native morph. `_GCURVE` remains exposed but unused; see `docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md`.

---

### 1.2 R-OSSE (families.py:105-112)

**Status:** Defined in `FAMILY_KEYS` table and in `_validate_osse_like`. **No example config exists.** CP-8c data summary (line 213): `families {'OSSE': 2034, 'R-OSSE': 0, 'ICW': 800, 'FREEFORM': 722}` — zero R-OSSE records in the entire dataset.

**Searchable parameters (`_ROSSE`, families.py:105-112):**

| Key | Note |
|-----|------|
| `r0_mm` | throat radius |
| `a_deg` | coverage half-angle |
| `a0_deg` | throat half-angle |
| `k` | R-OSSE k |
| `q` | termination q |
| `s1`, `s2` | throat stretch |
| `throat_ext_length_mm`, `throat_ext_angle_deg`, `slot_length_mm` | adapter knobs |
| `R_mm` | mouth radius (**R-OSSE specific**) |
| `tmax` | truncation parameter (> 0) |
| `m`, `r`, `b` | R-OSSE shape params |
| `exponent`, `aspect_ratio` | cross-section |
| `mode`, `wall_thickness_mm` | shared |

**NOT in R-OSSE:** `rot_deg`, `L_mm`, `n`, `s`, `h` — explicitly in `_REFUSED_HINTS` (families.py:155-168). Morph and gcurve keys are also absent from `_ROSSE`.

**What a config needs:** A `family: R-OSSE` YAML with `seed_params` containing at least `r0_mm`, `R_mm`, `tmax`, plus the standard throat knobs. `bounds` would search `R_mm`, `tmax`, `m`, `r`, `b`, `k`, `q`, `a_deg` etc. Validation is already implemented; the mesher would receive `formula: R-OSSE`. No code change required — only a YAML example file is missing.

**Risk:** Unclear without a test run whether the mesher's R-OSSE path is stable. Families.py has no morph/gcurve for R-OSSE (the task-04 `_ROSSE` dict omits them), but `12_RESEARCH_BASIS.md` section 4 lists R-OSSE parameters including `s1, s2, k, q` but no morph keys. Unclear whether the mesher supports morph for R-OSSE.

---

### 1.3 ICW (families.py:113-135)

**Status:** Fully supported. Example: `icw_termination.yaml`. CP-8c ran 800 evaluations, 787 ok.

**Searchable parameters (`_ICW`, families.py:113-135):**

| Key | Note |
|-----|------|
| `termination` | categorical: `flat_baffle` or `rollback` — **cannot be searched** (no lo/hi bound possible for str) |
| `r0_mm`, `a0_deg`, `L_mm`, `R_mm` | geometry scalars |
| `coverage_angle_deg` | ICW wall half-angle |
| `hold_start`, `hold_end` | [0,1] each; hold_start < hold_end enforced (families.py:321-324) |
| `kappa0` | initial curvature, 1/mm |
| `theta1_deg` | theta1, deg |
| `n_coeff` | ICW basis size (int) |
| `kappa_abs_max`, `dkappa_ds_abs_max`, `theta_max_deg` | ICW solver caps |
| `pin_mouth_radius` | bool |
| `icw_seed` | seed formula dict (passes entire OSSE/R-OSSE block) |
| `icw_coeffs` | list |
| `icw_S` | float |
| `mode`, `wall_thickness_mm` | shared |

**Mesher mapping:** ICW refuses OSSE shape keys at the top level; OSSE/R-OSSE geometry can be fed via `icw_seed` dict. The layer does not expose `icw_seed` as searchable (it is a dict, not directly plottable in a 1-D bound). `n_coeff` is searchable as an int but not searched in any example.

**Termination categorical gap:** `termination: rollback` is in the schema and the mesher supports it, but it is pinned to `flat_baffle` in the only example. The layer has no mechanism to search categorically (space.py only handles numeric bounds). To compare both terminations, two separate configs must be run.

**CP-8c icw_termination run:** `hold_end` pinned at lower bound (6/6 of top designs at `hold_end ≈ 0.55`). `kappa0` also pinned at lower bound (4/6). This means the search is trying to push the curvature hold as early/narrow as possible — a plausible physics signal (tightest transition). The `n_coeff` parameter is pinned at its seed value (not in bounds).

---

### 1.4 FREEFORM (families.py:137-143)

**Status:** Fully supported. Two example configs: `freeform_hv.yaml` (3 knobs) and `freeform_sculpt.yaml` (11 knobs). CP-8c ran 722 evaluations (freeform_hv); HANDOFF_6b ran 60 + 400 evaluations (freeform_sculpt).

**Searchable parameters (`_FREEFORM`, families.py:137-143):**

| Key | Kind | Note |
|-----|------|------|
| `profileH` | dict | `{points, throatAngleDeg, mouthAngleDeg}`; accessed via dotted paths |
| `profileV` | dict | same |
| `crossSections` | list | 2..32 stations `{t, shape, exponent/cornerRadiusMm}` |
| `inflectionPolicy` | str | `warn` or `reject` |
| `mode`, `wall_thickness_mm` | shared | |

**Path-based search:** `profileH.mouthAngleDeg`, `profileH.points.2.1` (z=1 is the radius of anchor index 2) are valid search keys. The `exponent` bare alias resolves to the first `superellipse` station's exponent. (`families.py:211-244`, `space.py:87-88`)

**Current freeform_sculpt.yaml searches:** 8 anchor radii (4 H + 4 V), 2 mouth angles, 1 exponent = 11 dims.

**Unsearchable but present:**
- `throatAngleDeg` in both meridians (pinned due to mesher warning about inconsistent H/V throat angles; NOTES_FOR_SENIOR 2026-10-14)
- z-coordinates of all anchors (pinned; required strictly increasing, cannot be searched independently without monotone constraint)
- `t` values in `crossSections` (pinned at 0.0 and 1.0; only 2 stations exist in the seed)
- Additional cross-section shape stations (no example has more than 2)
- `inflectionPolicy` (categorical)

---

### 1.5 Summary: mesher supports vs. layer exposes

| Family | Mesher supports | Layer implements | Example config | Dataset records |
|--------|----------------|-----------------|----------------|-----------------|
| OSSE | YES | YES, fully | `osse_baseline.yaml`, `search_smoke.yaml`, `throat_adapter.yaml` | 2034 |
| R-OSSE | YES | YES (table + validator), no YAML | MISSING | 0 |
| ICW | YES | YES, fully | `icw_termination.yaml` | 800 |
| FREEFORM | YES | YES, fully | `freeform_hv.yaml`, `freeform_sculpt.yaml` | 1906 |
| MORPH (OSSE sub-feature) | YES | Table exists, no example | MISSING | 0 |
| GCURVE/superformula (OSSE sub-feature) | YES | Table exists, no example | MISSING | 0 |
| Per-azimuth throat stretch | REFUSED ("not supported yet") | Reserved in `custom.py` | — | — |
| Wall ports / MEH entries | REFUSED (feature request NOTES_FOR_SENIOR 2026-10-14) | Not designed | — | — |

---

## 2. Hybrid capability assessment

### 2.1 Can the layer express per-axis different families?

**No.** Each `Config` and `DesignSpace` is single-family (`config.py:83-84`, `space.py:75-78`). The search runs one family per config. A FREEFORM config that has H≠V profiles is the closest available approximation, but both profiles use the same formula. A true "OSSE H-axis + ICW V-axis" hybrid would require a new mesher feature and a new family entry in `FAMILY_KEYS`.

### 2.2 Cross-section morphing (circle→superellipse with t, multiple stations)

**Partially.** FREEFORM `crossSections` supports 2–32 stations, each with `{t, shape, exponent/cornerRadiusMm}`. The seed in `freeform_sculpt.yaml` has exactly 2 stations: `{t:0.0, circle}` and `{t:1.0, superellipse, exponent:4.0}`. Additional intermediate stations (e.g., circle at t=0, ellipse at t=0.3, superellipse at t=0.7, rounded_rectangle at t=1.0) are supported by the mesher and validator (families.py:373-400) but not exposed in any example config. The bare `exponent` alias only resolves the **first** superellipse station — a second superellipse station at t=0.5 would need the path `crossSections.1.exponent` in bounds (if the station is at index 1). This path-based indexing works (NOTES_FOR_SENIOR 2026-10-13 task-04) but is fragile if station ordering shifts.

**Gap:** No example seeds multiple cross-section stations. No mechanism to search t-values (their boxes would need to maintain strict monotone ordering, which disjoint-range bounds enforce only if the user manually separates them — the same problem as FREEFORM anchor radii).

### 2.3 OSSE termination knobs

**All OSSE termination knobs are searchable:** `n`, `s`, `q`, `k` are in the `_OSSE` table and searched in `osse_baseline.yaml`. The `rot_deg` (rotation) and `h` (half-sine bulge) are in the table but not in any example bound.

### 2.4 FREEFORM seeded from OSSE/R-OSSE profile

**Not implemented.** `custom.py` is a stub (line 18). The mesher's `icw_seed` mechanism allows an OSSE/R-OSSE formula dict inside an ICW config (families.py:132), but FREEFORM has no analogous seeding mechanism. To seed a FREEFORM search from an OSSE result, the user would manually compute the OSSE profile's `[z, r]` points at a chosen number of stations and write them as the `profileH/profileV.points` seed. No helper exists for this conversion.

### 2.5 Mesher knobs not exposed by the layer

| Mesher knob | Family | Layer status |
|-------------|--------|-------------|
| `morph_target`, `morph_width_mm`, `morph_height_mm`, `morph_corner_mm`, `morph_rate`, `morph_fixed`, `morph_allow_shrinkage` | OSSE only | In `_MORPH` table (families.py:71-78), no example |
| `gcurve_type`, `gcurve_sf_a/b/m1/m2/n1/n2/n3`, `gcurve_se_n`, etc. | OSSE only | In `_GCURVE` table (families.py:79-94), no example |
| `rot_deg` | OSSE only | In table, no example; explicitly refused for R-OSSE |
| `h` | OSSE only | In table, no example |
| `s1`, `s2` | OSSE + R-OSSE | In table; range validated [0,10]; no example except implicitly via throat_adapter which pins them (not in bounds) |
| `n_coeff` | ICW only | In table; no example searches it |
| `icw_seed` | ICW | In table as dict; not path-searchable (dict bound semantics undefined) |
| `icw_coeffs` | ICW | In table as list; not path-searchable |
| `pin_mouth_radius` | ICW | Bool; not searchable (no lo/hi for bool) |
| `inflectionPolicy` | FREEFORM | Str; not searchable |
| Additional crossSection stations | FREEFORM | Supported by mesher and validator; no example |
| `slot_length_mm` | OSSE + R-OSSE | Only in `throat_adapter.yaml` |
| Enclosure keys (`depth_mm`, etc.) | OSSE | Not in `_OSSE` table at all |

---

## 3. FREEFORM search parametrization problems and proposed fixes

### 3.1 The current disjoint-radius-box problem

`freeform_sculpt.yaml` (lines 40-49) bounds anchor radii in non-overlapping intervals:

```
profileH.points.1.1: {lo: 22.0,  hi: 55.0}
profileH.points.2.1: {lo: 58.0,  hi: 105.0}
profileH.points.3.1: {lo: 108.0, hi: 160.0}
profileH.points.4.1: {lo: 163.0, hi: 200.0}
```

Gaps of 3 mm between adjacent hi and lo guarantee strictly-increasing radii for any independent draw. However this is achieved at the cost of:
1. **Dead zones in the box:** the real feasible region is a simplex (r1 < r2 < r3 < r4) but the box is rectangularized with artificial gaps. CMA-ES does not know about the structure; candidates that violate the mesher's actual ordering requirement (r > 0, but the mesher enforces monotone only via the spline-overshoot guard) are not pre-rejected.
2. **Pinning:** HANDOFF_6b (lines 104-105) reports that after 400 evals `profileH.points.3.1` was pinned at its **lower bound** in 28/46 top designs and `profileV.points.3.1` at its lower bound in 39/46 top designs. The optimiser wants smaller intermediate radii than the disjoint boxes allow — the gap of 3 mm at `r2.hi → r3.lo` (105 → 108) is a structural artefact, not a physical constraint.

### 3.2 Monotone-increment parametrization (r_{i+1} = r_i + Δ_i, Δ_i ≥ ε)

To implement this, the minimal change is:
- **`families.py`**: Add a new set of FREEFORM bound-key aliases, e.g. `profileH.delta.1`, `profileH.delta.2`, etc. These would not correspond to any mesher field. Instead, `resolve_path` for FREEFORM needs a new branch: if the key starts with `profileH.delta.<i>`, it resolves to the radius of anchor i **after computing** r_i = r_0 + sum(Δ_0..Δ_{i-1}). But this requires the path resolver to carry an accumulation state over the whole `params` dict, which is more than `resolve_path` (families.py:210-244) currently does — it is a pure dict walk. The function would need a semantic hook for "delta" keys that interprets them as increments rather than direct values. `param_get` (families.py:247-251) and `param_set` (families.py:254-261) would both need analogous hooks — `param_get` would sum increments, `param_set` would back-compute the increment given a target radius.
- **`space.py`**: `denormalize` (space.py:137-154) calls `param_set`, which would naturally call the new delta-aware setter. No other change needed in `space.py` if `param_set` correctly handles the accumulation.
- The mesher config is built from the seed's `profileH.points` list, which must hold computed absolute radii, not deltas. `to_mesher_config` (families.py:432-466) reads from `design.params` using the `profile` section. The delta parametrization must materialize the absolute radii into `params["profileH"]["points"]` before `to_mesher_config` is called — either in `param_set` itself or in a FREEFORM-specific pre-processing step inside `validate`/`to_mesher_config`.

Concretely: the functions that would change are `resolve_path`, `param_get`, `param_set` (all in `families.py`), and the `denormalize` path in `space.py` would work without modification if `param_set` is correctly extended. A new helper `_accumulate_deltas(family, params)` called from `to_mesher_config` before construction is the cleanest boundary.

### 3.3 "Profile seeded from OSSE formula + bounded perturbation"

To implement a perturbation parametrization:
- A new FREEFORM seed helper (a function, not a class) that evaluates the OSSE or R-OSSE profile at N stations and populates `profileH.points` / `profileV.points`. This helper would live in a new module (e.g., `design/seed_helpers.py`) and be called by the user when constructing the seed YAML, or it could be invoked at config-load time if a special seed key like `seed_from: {family: OSSE, params: {...}}` were recognized.
- **`config.py`**: The only change needed is to recognize an optional `seed_from` block and call the helper before constructing `Config.seed_params`. This is a one-function addition to `config.py` or a pre-processing step in `load_config`.
- **`families.py` / `space.py`**: No change needed for the perturbation bounds themselves — the existing dotted-path mechanism already handles `profileH.points.i.1 ± δ` bounds. The perturbation semantics are just narrow bounds centred on the OSSE-derived radius.
- **Gap:** The "bounded perturbation" framing shares the disjoint-box ordering problem. If the OSSE profile's radii at adjacent stations are close, the perturbation boxes will overlap and the monotone guarantee breaks. A perturbation approach therefore still needs either the delta parametrization above or tightly-sized non-overlapping perturbation boxes (the current approach, with the known pinning risk).

---

## 4. Physically implausible designs wasting budget

### 4.1 OSSE: mesh_too_large dominates

**CP-8c osse_baseline** (1500 evaluations): 93/95 failures were `mesh_too_large`, only 2 were `invalid_geometry`.

**Root cause parameters** (CP-8c_data_summary.md lines 118-121, median params of mesh_too_large failures):
```
a_deg: 18.2, exponent: 3.46, L_mm: 392.1, a0_deg: 25.9, k: 1.98, aspect_ratio: 1.84
```
The pattern is: **large L_mm (near 420 mm hi) + large a_deg = large mouth area**. A horn with L=420 mm and a_deg=18° has a mouth width of approximately 2 × 420 × tan(18°) ≈ 273 mm per side. At epw=6, f_max=5500 Hz (res_mm ≈ 10.4 mm mouth), the number of elements scales as mouth_area / h² ≈ (0.273)² / (0.0104)² ≈ 690 elements per quarter, times area-factor ≈ scales to well above the 5000-dof cap. The pre-mesh guard fires at 1.5× cap before even calling the mesher (build.py:282-288).

**Additional OSSE causes:**
- Large `aspect_ratio` (1.84) multiplies the mouth width × height product.
- `a0_deg` large (26°) contributes to larger effective coverage at the throat.
- The `invalid_geometry` failures (2 rows) share parameters `a_deg≈34°, L_mm≈284, a0_deg≈26, k≈1.37` — the "chord too long" mesher error, meaning the profile curve cannot be discretized at the requested resolution.

**Guards that could reject earlier (before meshing):**

1. **Pre-mesh triangle estimate already exists** (`build.py:279-288`) and fires at 1.5× cap. It correctly blocked most bad OSSE candidates (the 93 `mesh_too_large` pre-mesh examples all say "no mesh was generated"). This guard is **working and effective** for OSSE.

2. **Analytic mouth-area bound** (not implemented): before calling `estimate_triangles_premesh` (which costs 25-60 ms and calls the mesher internally), a purely analytic estimate `mouth_r ≈ r0 + L * tan(a_deg)` → `area ≈ π * mouth_r²` → `N_tri ≈ 2.3 * area / h²` could reject in microseconds with no mesher import. This would save the 25-60 ms coarse-geometry resolve on hopeless candidates. The function `estimate_triangles_premesh` in `build.py:147-170` uses `resolve_geometry`, which is a private mesher API. A pure-Python analytic guard would be more robust to mesher API changes.

3. **Bound tightening** (not a guard, but changes which designs CMA proposes): the CP-8c data shows `L_mm` median at 396 mm (near upper bound 420) and `a_deg` range 5–51°. The product `L_mm × tan(a_deg)` predicts mouth radius. A derived bound `L_mm × tan(a_deg) ≤ max_mouth_r` could be enforced in `validate`, but the contracts forbid "rule-of-thumb plausibility limits" (families.py:13). The correct approach is a pre-evaluation analytic estimate in `build_mesh`, not a validation change.

### 4.2 ICW: `mesh_too_large` (8 rows) and `invalid_geometry` (5 rows)

ICW `mesh_too_large` failures (8 rows) have **no distinctive parameter pattern** beyond large `R_mm` (near 220 mm). `R_mm` directly controls mouth size; the dof budget is hit when R_mm is large at the search's band_hi (7000 Hz for ICW, giving smaller res_mm than OSSE at 5500 Hz).

ICW `invalid_geometry` (5 rows): "ICW target set is infeasible: max|dkappa/dsigma| 32.8701 exceeds cap 10.0" — the curvature derivative cap `dkappa_ds_abs_max` (pinned at 10.0 in the seed, not searched) is exceeded internally. The ICW solver needs a higher cap or a tighter `kappa0`/`theta1_deg` to stay feasible. These failures have no distinctive params at the median; they arise at rare CMA proposals near an invalid region.

**Guard:** The ICW mesher's own infeasibility message is returned as `GeometryInvalidError`, which is correctly classified as `invalid_geometry` and treated as a penalty. No additional pre-meshing guard is feasible here — the ICW feasibility depends on the ODE solver's convergence, not on a geometric dimension.

### 4.3 FREEFORM: 1 failure in 722 (freeform_hv), 1 in 460 (freeform_sculpt 400)

Both failures are `invalid_geometry: FREEFORM outward wall offset fails the surface-curvature guard near t=0.9998` — the mouth outer shell curvature guard fires when the mouth angle is steep and the anchor radius is large. The NOTES_FOR_SENIOR 2026-10-14 (cloud reviewer) confirms this was reduced from 14/41 to 1/41 by narrowing mouth angles from [40,90] to [35,70]. The current bounds in `freeform_sculpt.yaml` produce essentially zero failures.

### 4.4 Budget waste summary

| Family | Config | Failure rate | Dominant kind | Root parameters |
|--------|--------|-------------|---------------|-----------------|
| OSSE | `osse_baseline` | 95/1500 = 6.3% | `mesh_too_large` 93/95 | large L_mm (near 420) + large a_deg or aspect_ratio |
| OSSE | `search_smoke` | 7/60 = 11.7% | `mesh_too_large` | same; tighter dof cap 3000 |
| ICW | `icw_termination` | 13/800 = 1.6% | `mesh_too_large` 8, `invalid_geometry` 5 | large R_mm; ICW infeasibility |
| FREEFORM | `freeform_hv` | 1/722 = 0.14% | `invalid_geometry` | steep mouth angle (now bounded at 70°) |
| FREEFORM | `freeform_sculpt` (400) | 1/460 = 0.22% | `invalid_geometry` | same |

**The only material waste is OSSE's `mesh_too_large` at ~6–12%**. The pre-mesh guard is already catching them (no mesh file is written). The real cost is the 25-60 ms coarse-geometry resolve inside `estimate_triangles_premesh`. A direct analytic `L_mm * tan(a_deg) * aspect_ratio` pre-screen in `build_mesh`, before calling `estimate_triangles_premesh`, would cut that overhead with no API dependency.

---

## 5. Target–typology consistency

| Config | family | coverage_h_deg | coverage_v_deg | band_lo/hi Hz | Known strengths of typology | Assessment |
|--------|--------|---------------|---------------|---------------|------------------------------|------------|
| `osse_baseline.yaml` | OSSE | 75° total | 45° total | 700–5500 | OSSE: pattern control via flare, flexible coverage ratio | Consistent. 75×45 is the canonical "wide-H narrow-V" pro-audio pattern. `a_deg` (half-angle ≤55°) allows up to ~110° total, so the 37.5° seed (75° total) sits mid-range. Band hi 5500 Hz is limited by the 8 GB dof cap — physically correct for the mouth size. |
| `search_smoke.yaml` | OSSE | 75° total | 45° total | 700–4500 | same | Consistent. Band clipped to 4500 Hz for speed (comment). |
| `throat_adapter.yaml` | OSSE | 75° total | 45° total | 2000–6500 | OSSE with throat extensions: high-frequency adapter | **Partially consistent.** Target 75×45 is pinned (the outer horn coverage is fixed); `throat_adapter` searches the throat geometry to improve `flat` (on-axis flatness) and `rip` (ripple) above 2 kHz. The `cov` weight is 0.2 (vs 1.0 in baseline) — correctly downweighted since coverage is essentially fixed. |
| `icw_termination.yaml` | ICW | 100° total | 100° total | 700–7000 | ICW: constant curvature, smooth rollback, wide even coverage | Consistent. ICW is known for wider, more symmetric coverage at lower DI. 100×100 matches its physics: ICW's curvature constraints naturally produce a wide, even pattern. Band hi 7000 Hz is higher than OSSE due to smaller mouth (R_mm ≤220 mm vs OSSE L≤420 mm). |
| `freeform_hv.yaml` | FREEFORM | 75° total | 45° total | 700–5500 | FREEFORM: per-axis independent shaping | **Somewhat inconsistent.** The 3-knob version (only mouth angles + exponent) is too coarse to meaningfully differentiate H vs V coverage. The freeform_hv CP-8c run showed very poor coverage terms (cov median 26.5 vs OSSE's 0.85), suggesting the 3-knob parametrization is insufficient to hit 75×45. Using a full-domain mesh (quadrants "1234") also wastes 4× the dof budget vs. quarter-domain. HANDOFF_6b confirmed the full-domain was a misreading and the quarter domain is safe (< 0.05° beamwidth diff). |
| `freeform_sculpt.yaml` | FREEFORM | 90° total | 90° total | 700–5500 | FREEFORM: independent H/V wall shaping | Consistent. 90×90 is a natural target for a multi-knob FREEFORM search, matching the JW Sound Solana archetype cited in the config (lines 6–9). The search achieved J=16.79 after 400 evals (−46% from seed), with `cov=5.79` — better than freeform_hv but still high, suggesting the 90×90 target at 700 Hz requires a large mouth that strains the dof budget. |

---

## Appendix: CMA-ES parameter mapping

`search/cma.py:141-145`: CMA is called with `x0 = space.normalize(space.seed)` (the seed, normalized to [0,1]^k), `sigma0` from `cfg.search.sigma0` (default 0.25 in all configs), bounds `[0, 1]` (hard clip in `denormalize`). Popsize: default CMA formula (4 + floor(3 * ln(k))). Alphabetical key order in `space.keys()` is the CMA vector order and is FROZEN to key name, not YAML order (`space.py:121-122`).

The alias `exponent` in FREEFORM resolves via `FREEFORM_ALIASES` (families.py:187-188, 221-224) at `param_get`/`param_set` time to the first superellipse station of `crossSections`. The alias appears as the alphabetically-sorted key `exponent` in the CMA vector. A path key like `profileH.points.3.1` also sorts by its full dotted string. Both are stable across YAML reorderings.

Sigma0=0.25 means CMA starts at ±25% of the [0,1] box. For a 400-mm L_mm bound (lo=140, hi=420), one sigma = 70 mm initial step. Given the 93/1500 mesh_too_large failures at median L_mm=392 (near the hi), CMA has drifted toward large L_mm as that reduces cov terms (longer horn → more directional at lower frequencies). The pinning of `n` at lo=2.0 in 6/6 top designs (CP-8c summary line 112) suggests CMA has learned `n=2` (near-OS profile, minimal termination ripple) as optimal.
