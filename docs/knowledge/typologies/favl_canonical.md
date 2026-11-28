# favL / `osse_rollback` (FAV-001 canonical)

- Status: navigation summary. **LABELED HYPOTHESIS-SHAPE EXPERIMENT** (owner-directed hybrid
  2026-10-28), no published name (`grid.py:2051-2055`). `favL` is the canonical "favourite
  landscape" lineage: FAV-001 `4140768780f0` is a Crowe-X mouth on the OS/OSSE CD wall; `favL` is
  the 2-inch compact500 continuation of that family. It is implemented as the `osse_rollback`
  rows kind inside the shared `grid.py`, not as a separate family module.
- Design principles: a constant-directivity OS/OSSE throat wall per azimuth
  (`a(phi) = a_h cos²phi + a_v sin²phi`), an even-lobe flute ripple, and a tangent-continuous
  curled lip. The optional split-plane and ridge/beak knobs extend the same law.
- Appropriate objectives: CD corridor H/V width, DI slope/std, off-axis smoothness, loading at the
  crossover, and the physical envelope. This is the protected CD benchmark for the home-900 brief;
  score it on a CD brief and against its own control.
- Limitations: the v9–v11 corridor charges zero inside `[min, max]` and never uses `preferred_deg`;
  the flatness the owner meant is the opt-in `objective.constancy` term
  (`docs/evidence/coverage_pull_2026-11-25/`). FAV-001 is flat at the *wrong* angles in the
  +−5° brief. V is mouth-limited; `k` trades loading for CD terms.
- Common incorrect assumptions: a corridor pass is not a constant beamwidth; a lower J is not a
  better design across k/dose; `throat_hv_ratio` couples k_H and k_V (see FAMILY_LAWS); split-plane
  `k_v`/`s_v` is a separate law and cannot be combined with `throat_hv_ratio` ≠ 1.
- Key sources and detailed research: [FAV-001 research](../../research/favorites_2026-11-20/CROWE_X_FAVORITE_RESEARCH.md),
  [throat-loading levers](../../research/favorites_2026-11-20/THROAT_LOADING_LEVERS.md),
  [split-plane proposals](../../research/typologies/FAV_SPLIT_PLANE_PROPOSALS_2026-11-20.md),
  [home-900 decision](../../evidence/home_xo900_2026-11-20/README.md). Joint laws:
  [FAMILY_LAWS.md](../FAMILY_LAWS.md).

## Kinds / generators

- Generator: `name: grid`, `rows: {type: osse_rollback}` (`grid.py:2008-2176`). FREEFORM family.
- Models: `FREEFORM` via `grid.rows_grid_points` / `grid.design_params` / `grid.validate_*`
  (`grid.py:3033`, `:3113`, `:3168`).
- Parent examples: `hl__crowe_x_osse_cd_v7.yaml` (FAV-001 lineage), `favL__2in_c500_pm5`
  (`examples/typologies/cd_pm5const_2026-11-25/favl_pm5.yaml`).

## Knobs with legal ranges

| Knob | Range / rule | Where |
|---|---|---|
| `a_h_deg`, `a_v_deg` | [5, 85] | `grid.py:2028`, `:2075-2079` |
| `k` | > 0 | `:2080-2083` |
| `n` | > 0 | `:2080-2083` |
| `s` | ≥ 0 | `:2080-2083` |
| `q` | `0 < q <= 1` | `:2080-2083` |
| `L_mm` | [10, 1000] | `:2084-2086` |
| `r_lip_mm` | [0, 100] (0 = row untouched) | `:172`, `:1085-1093` |
| `wrap_deg` | [0, 200] | `:2029`, `:2088-2091` |
| `wrap_cos_amp` | [0, 0.9] | `:2030`, `:2092-2095` |
| `sf_m` | even int [2, 16], or 0 = off | `:2026`, `:2096-2102` |
| `sf_n1`, `sf_n2`, `sf_ab` | > 0; `sf_ab != 1` needs `sf_m % 4 == 0` | `:2103-2109` |
| `sf_amt` / `sf_start` | [0, 1.5] / [0, 1) | `:2027`, `:2110-2113` |
| `a_fold` / `a_union` | {2, 4} / {0, 1}; alternatives | `:2116-2120` |
| `union_blend_deg` | [0, 30] | `:2022`, `:2121-2124` |
| `ripple_lobes` | even int [6, 24] (0 = off) | `:178`, `:1046-1062` |
| `ripple_amp_mm` | [0, 50] | `:179`, `:1042-1045` |
| `ripple_start` | [0, 1) | `:1043`, `:1063-1066` |
| `k_v` / `s_v` | > 0 / ≥ 0 | `:2129-2136` |
| `k_v_log` | 0 or 1 (needs `k_v`) | `:2137-2144` |
| `v_exp_mm` | [0, 120] | `:2042`, `:2139-2141` |
| `throat_hv_ratio` | [0.25, 4.0] | `design/throat_hv.py:30` |
| `hv_onset_frac` | [0, 0.9] | `throat_hv.py:31` |
| `section_exp_ramp` | [0.5, 8] | `throat_hv.py:32` |
| `a_d_deg` | [-15, 20] | `:2049` |
| `beak_h_mm`, `beak_v_mm` | [-60, 60] | `:2049` |
| `beak_d_mm` | [-40, 40] | `:2050` |
| `beak_start` | [0.3, 0.95] | `:2050` |

## Joint validity laws (file:line)

- **`k_v` and `throat_hv_ratio` ≠ 1 are two per-azimuth k laws; use one** — `grid.py:2145-2148`.
- **`k_v_log` needs `k_v`** — `grid.py:2143-2144`.
- **`beak_start` needs a beak amount** — `grid.py:2157-2158`.
- **`wrap_cos_amp` follows the flute count; needs `ripple_lobes`** — `:2126-2128`.
- **`a_union` and `a_fold == 4` are alternatives** — `:2119-2120`.
- **`sf_amt > 0` needs `sf_m`; `sf_m` must be an even integer; `sf_ab != 1` needs `sf_m % 4 == 0`** —
  `:2096-2115`.
- **Ripple resolution**: the row grid must give `>= 4` phi samples per lobe period —
  `grid.py:1070-1082`.
- **`hv_onset_frac` / `section_exp_ramp` drive the superformula window**: they need `sf_m` and
  `sf_amt > 0`; `hv_onset_frac` replaces `sf_start`, so `sf_start` must stay 0 when it is set —
  `grid.py:2163-2175`.
- **FREEFORM `rows` contract**: rows kind checked and the seed/bounds are validated by the
  grid-family dispatch (`grid.py:3033-3261`). `span` and `mesh.quadrants` must agree (quarter ⇔
  `'1'`).

## Inert knobs per mode

- `sf_*` knobs inert at `sf_m == 0`; `sf_amt > 0` without `sf_m` is refused (`grid.py:2096-2115`).
- Ripple knobs inert at `ripple_lobes == 0` (`:1047-1056`); `wrap_cos_amp > 0` needs lobes (`:2126`).
- Beak knobs inert at zero amplitude; `beak_start` alone is refused (`:2157-2158`).
- `k_v`/`s_v`/`k_v_log`/`v_exp_mm` inert when absent; `k_v_log` needs `k_v` (`:2129-2144`).
- `throat_hv_ratio` is neutral at 1.0; absent keys keep the parent law byte-for-byte
  (`throat_hv.py:20`, `:73-77`).
- `r_lip_mm == 0` returns the row untouched (`grid.py:1410`, `:1562`).
- `a_fold`/`a_union` are categorical, not continuous search dimensions.

## Implementation-digest files

Unlike the newer family modules, `osse_rollback` has **no separate `implementation_digest()`
function**: it lives inside the shared `hornlab_search/design/generators/grid.py` (and draws on
`profiles.py` / the installed mesher's `profile_points` and `eval_param`). The saved recipe is the
FREEFORM rows config. Treat `grid.py` as the implementation source and cite it in any
generator-family digest skill; editing it changes every `osse_rollback` recipe's geometry (the
2026-11-25 handoff calls this out as a digest hazard for all family modules).

## Best-known designs (from I3 evidence)

- `docs/evidence/home_xo900_2026-11-20/` [current] — FAV-001 `4140768780f0` home-900 J **2.607618**
  (RMS H/V error 9.35/9.99°); extended-throat OSSE `e85cdd7c61f6` J 2.774; OSSE morph
  `0636d3f22d5c` 2.997; fold-warm `68001408e339` 3.216; ATH CORE petal `2683984c802c` 3.327.
- `docs/evidence/cd_pm5const_2026-11-25/` [current] — favL best `6552f5c8c536` J **1.388**,
  H 66.6 ± 3.2°, V 62.4 ± 2.0° (0.9–8 kHz); replay under the +−5° constancy brief moves it to
  J 6.363 (window dominates until the pattern moves to ~80 × 50).
- `docs/evidence/favL_2in_c500_continue_2026-11-25/` [current; no results yet] — predeclared
  continuation of parent best J **1.870458** under the open box (1.15) and a new identity.
- `docs/evidence/cd_v11_2026-11-20/` and `cd_v11_completion_2026-11-20/` [current] — eight
  objective-v11 CD lanes; 8/8 reached 50 valid evals.
- `docs/evidence/cd_backbone_2026-11-25/` survey: `osse_rollback` best saved J 1.113 (b3a PA
  90×90); the CD body angle is already a native knob (`g_a_h_deg`, `g_a_v_deg`).

## Open questions

- Corridor mode does not encode the owner's constant-beamwidth intent; the `+−5°` constancy briefs
  are new identities and their jobs/verify are pending (`docs/evidence/cd_pm5const_2026-11-25/`).
- `k` trades loading against the CD terms; the split-plane `k_v`/`s_v` and `v_exp_mm` levers are
  new and not yet verified.
- Low-band V is mouth-limited; a bigger exit is the cleanest loading lever but overshoots V when
  stacked with k_V.
- `osse_rollback` has no own digest function; if provenance must bind the generator, a versioned
  module (not an edit to `grid.py`) is the safe route.
