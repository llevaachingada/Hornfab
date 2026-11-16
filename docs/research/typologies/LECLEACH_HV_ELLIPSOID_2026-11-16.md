# Le Cléac'h H/V pair — ellipsoidal-wavefront construction (dossier, 2026-11-16)

Deliverable for item 13 of `docs/queue/HOME_18H_PLAN_2026-11-16.md` (owner: the per-plane
`lecleach` rows produced lobed, bulbous bodies; fix from the published construction). This
file extends, and where stated CORRECTS, the landed dossiers
`JMLC_LECLEACH_RESEARCH_2026-10-25.md` (verified T1 march, R9-J) and
`JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md` (T3 `fc(φ)` law flagged un-attributed).

## 1. Source table

| Source | What it gives us | Status |
|---|---|---|
| sphericalhorns.net, 2020-12-21, "JMLC inspired horn calculator" (fetched 2026-11-16) | The construction: expansion law `S(z) = S0 (cosh(mz/2) + T sinh(mz/2))^2`, `m = 4π fc / cs`; "The base for any later modifications ... is always the round horn to determine the construction wave front surface areas and the resulting horn profile"; H/V difference via per-plane PETF/hvdiff ("If horizontal and vertical expansion PETF parameters are set to the same values a round horn will result"; the hvdiff images); rollback terminated at 180° | **primary (author)** |
| sphericalhorns.net, 2019-08-05, "Ellipsoidal wave fronts in horns" (fetched 2026-11-16) | The section transformation: keep the flat section area equal (`π a b = π r_m²`), `b = r_m / f_s`, `a = r_m² / b`, a smooth stretch `f_s(z)` (1 at throat, max at mouth/rollback), Lamé exponent n for round→rectangular (n = 2 = ellipse) | **primary (author)** |
| Auto-Tech 920×330 asymmetric-JMLC-300 datasheet (in the T3 dossier) | The only dimensioned published H/V numbers; ratio fc_v/fc_h = 2.8 | **primary (manufacturer, datasheet)** (already fetched 2026-10-25) |
| Owner references `docs/queue/lecleach_refs_2026-11-16/` (4.png; jmlc_300_rnd_1; jmlc_HVDiff_2/3, archived from the 2020 article) | The target look: long slim round throat, large rollback lip curling past 180°, horizontal flare much larger than the vertical, lip continuous all the way round | **owner-provided** |
| Fourcade 2015 (in the T1 dossier) | The verified per-plane meridian (`lecleach_exact`, R9-J passed) | **primary (author)** |

The owner's second saddle reference (different rollback depth per plane) was provided in chat
2026-11-16; the article's `jmlc_HVDiff_2/3` images carry the same property and are archived
next to it.

## 2. Corrections (dated, per skill §4 — nothing settled edited)

**C1 (2026-11-16): the per-azimuth INDEPENDENT-march reading of the `1/fc(φ)` law is invalid.**
The landed `lecleach` fc-pair path (grid.py `kind == "lecleach"`, pre-2026-11-16) built one
COMPLETE Fourcade march per azimuth at `fc(φ)`/`stop(φ)` and lofted the rows point by point.
Measured consequences (probe + run `20261116T040651Z-screen-e53ae9`): at the rejected run's own
seed the rim is up to **+16.8 mm (11.1% of r_V) off the ellipse** through the H/V endpoints and
the rim is axially non-planar by **155.6 mm**; at a box corner (fc 300/1400) the bulge reaches
**+118.5 mm (183% of r_V)** with a **319 mm** rim spread; row lengths span **2.3×** (fc 450 →
389 mm vs fc 800 → 169 mm) — differently-sized horns lofted point by point never form one horn.
This is the "lobed, bulbous body" the owner rejected. The `1/fc(φ)` law itself is smooth and
monotone (verified) — the invalid part was its realization as independent per-azimuth marches.

**C2 (2026-11-16): a naive area-correcting factor `λ = r_m/sqrt(r_h r_v)` is REJECTED.**
Closed-form `λ` (to enforce `π a b = π r_m²` exactly at every station) was implemented and
removed the same evening on measured evidence: across marches of different arc length the
arc-fraction misalignment makes λ recede near the lip and re-introduces a wall bulge (unit tests
`test_hv_rows_*` caught rows receding up to 6.3 mm before the rim). The shipped construction
uses the plane-march radii as axes verbatim and reports the section-area deviation instead
(grid.py `area_note`); the exact-area Newton step of the 2019 article remains a future option.

## 3. The shipped construction (grid.py `_rows_lecleach_hv_marches`)

1. **One horn.** A round CORE march at `fc_core = √(fc_h·fc_v)` (the choice that tracks
   `r_h·r_v = r_m²` to first order under the published `W·fc` invariant) and at the
   **deepest per-plane stop** (the wavefront chain must reach every plane's expansion)
   provides the shared arc-fraction stations `x(s)` — the axial curl, so the lip is the
   same smooth continuous rollback on every azimuth. [grounding: 2020 article, "round
   horn is always the base"; realization [inferred]]
2. **Per-plane expansions.** The plane marches — the verified march at `fc_h`/`stop(0)`
   and `fc_v`/`stop(90)` — provide the section semi-axes verbatim. The H and V plane
   meridians ARE their own verified Fourcade marches; the H/V difference comes from the
   expansions themselves, never from a mouth stretch. [grounding: 2020 PETF/hvdiff
   principle; per-plane realization with the verified march [inferred]]
3. **Elliptical sections.** Every intermediate section is the ellipse through the axes
   `(r_h(s), r_v(s))` at the shared station — the 2019 article's transformation with the
   Lamé exponent at n = 2 (ellipse, convex). All marches share the throat `(r0, θ0)`, so
   station 0 is a circle of radius `r0` on every azimuth (round exact throat, slim from
   the march itself). [grounding: 2019 eqs 10-12; closed form without the Newton step [inferred]]
4. **Per-plane rollback difference.** The `stop` knob + the `cos(2kφ)` stop harmonic
   (`g_stop_cos2k`, searchable scalar alias `g_stop_a2`) set per-plane roll depth,
   gated per plane by `ROWS_LECLEACH_STOP_RANGE` `[90, 240]`. [grounding: none
   published for asymmetric stops (T3 dossier); labeled reconstruction as before]

Rationale for `fc_core = √(fc_h·fc_v)`: mouth radius ∝ 1/fc, so `r_h·r_v ∝ 1/(fc_h·fc_v)`
and the core at the geometric mean carries the neutral area scale — the published
`W·fc_h ≈ H·fc_v` product then holds by construction (validated below).

## 4. Validation properties (tests `tests/test_design_generators_lecleach_hv.py`, all pass)

| # | Property | Test |
|---|---|---|
| V1 | rows share the core's stations exactly; rim axial spread ≤ 1e-6 mm (was 155-319 mm) | `share_one_station_chain_and_are_planar` |
| V2 | mouth edge IS the ellipse through the H/V endpoints (≤ 1e-6 max, was +11%/+183%) and the closed rim has no concave vertex (no peanut) | `mouth_outline_is_an_ellipse_and_convex` |
| V3 | the body silhouette in the mouth plane has no concave vertex (no lobes) | `silhouette_stays_convex` |
| V4 | every row is a simple curve (no self-intersection); the deep-roll lip tuck-in ≤ 8% of r_max; throat exactly round on every φ | `never_self_intersect_and_keep_a_round_throat` |
| V5 | `W·fc_h ≈ H·fc_v` within 2% with equal per-plane stops | `match_the_fc_product_invariant` |
| V6 | `fc_h = fc_v`, no harmonic ⇒ byte-identical to the plain axisymmetric lecleach rows (≤ 1e-9 mm) — backward compatibility | `degenerate_to_the_axisymmetric_march` |
| V7 | per-plane stops follow the stop harmonic (230°/170° at seed `a2 = 0.15`), plane meridians keep their own march endpoints | `per_plane_rollback_follows_the_stop_harmonic` |
| V8 | construction labels + `fc_core_hz` recorded in meta | `meta_carries_the_published_construction_labels` |
| V9 | fc-pair ratio capped at 4.0 (published territory 1.5-3.0 + margin; the old 300/1400 = 4.67 corner refused) | `fc_pair_ratio_is_capped` |
| V10 | every admissible box-corner combination builds, self-consistent and rim-elliptical | `build_validly_across_the_config_box_corners` |
| V11 | `g_stop_a2` scalar alias still maps to `g_stop_cos2k[0]` | `g_stop_a2_alias_feeds_the_stop_harmonic` |

## 5. Knobs and ranges (config `hl__lecleach_hv_landscape_smooth_v7.yaml`)

| Knob | Seed | Box | Basis |
|---|---|---|---|
| `g_fc_h_hz` | 450 | 300-800 | reference look (H flare ≫ V); fits the 600×480×480 envelope (W·fc ≈ 1.87e5 mm·Hz at this throat) |
| `g_fc_v_hz` | 800 | 450-1150 | ratio ≤ 2.56 in-box, cap 4.0 in code (published asymmetric territory 1.5-3.0); old 1400 corner (4.67) removed |
| `g_T` | 0.6 | 0.4-0.9 | T1 dossier (0.5 quasi-Iwata analogue, 0.707 hypex, ~1 the calculator's JMLC look) |
| `g_stop_deg` | 200 | 150-240 | deep rollback past 180° per the references; hard range 90-240 unchanged |
| `g_stop_a2` | 0.15 | -0.3..0.35 | different rollback depth per plane (owner's 2nd ref); per-plane stop gate raises beyond 240°/below 90° |
| `g_r_lip_mm` | 0 | fixed 0 | the natural continuous rollback IS the lip; torus lip stays default-off |

Throat check: with `fc ≈ 450-800` at a 700 Hz crossover the visible duct is shorter than the
jmlc-300 reference (fc/f0 = 0.64 vs 0.43) — physical, not a defect; `T` and `stop` remain the
slimness/depth levers.

## 6. Open items

- The 2019 article's exact ellipsoidal-cap Newton correction (vs our few-% closed-form
  deviation, reported in meta) — only worth revisiting if a datasheet-quality reference
  surface becomes available.
- The 2020 article's calculators were revoked by the author (site-wide notice); the
  construction text remains public and is the used grounding — recorded here per the R9
  "source unreachable" pattern (the source is reachable, the tool is not).
