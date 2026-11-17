# N1 — finish X1: the five contract tests on the six lanes

Run: 2026-11-17, HEAD `01560e5` (working tree has other lanes' uncommitted scratch edits). Read-only,
CPU only; no mesh build, no solve, no pytest. Scripts: `scratch/fable_architecture/.n1/`
(`build.py`, `analyze.py`, `component_check.py`, `inner_wall2.py`, `separate.py`,
`resolution_test.py`, `rolled_native.py`, `volume_check.py`). Inputs: `.fable/rows.pkl`; the ten
`.x1/<hash>.npz` samplers for five lanes; `.x1/legacy_k_results.txt` for Klangfilm; the stored
`runs/<run>/designs/<hash>/{design.json,mesh.msh}`; `.tmp/fable_replay_harness.py` for the §0 check.
Records: `.n1/build1/`, `.n1/build2/`, `.n1/build_ref/`, `.n1/*.json`, `.n1/*.log`.

§0 gate: HEAD `01560e5`; parity harness printed
`parity smoke: worst regenerated-vs-stored DI across study screen designs: 0.0 n 17`. Zero, so the
task proceeded.

## Headline

1. **The contract-minimum record (65 stations × 31 azimuths = 3° step) fails inner-wall mesh
   agreement on three lanes, so the X1 failure condition is met.** Rolled 0/10 (p99 1.70 mm),
   Crowe 0/10 (p99 1.87 mm), Klangfilm 9/10 (one design p99 1.46 mm). Ext-throat, ATH morph and
   biradial pass 10/10 with p99 ≤ 0.85 mm. The causes are known and differ: the rolled relief is
   under-resolved by 31 azimuths (49 azimuths passes 10/10, p99 0.36–0.59), the Crowe rectangular
   corner sits at the mesher's own surface-fit floor (~1.1 mm) plus 31-azimuth chords, and one
   Klangfilm design does not match its stored mesh even at native resolution.
2. **The other three tests are mostly sound.** Determinism 60/60 across six lanes in separate
   processes. Refinement passes 30/30 on the three testable lanes (worst 0.198 mm; largest
   descriptor change 0.15 %). Envelope width/height fails on biradial (+1.9 to +3.5 mm) and
   partly on ext-throat (H up to +1.41 mm) and Crowe (H down to −1.64 mm); the depth deficit in
   every lane is the rear closure at `z = −t` (tag-1 z minimum), and after that correction is
   within 1 mm everywhere except one ATH design (+1.04 mm).
3. **Metadata is mostly recoverable, but not complete.** Throat radius (18.00 mm at s=0),
   exit angle (2.0°), symmetry (`hv`), quadrants (`1`), mounting (none), source-cap setting
   (`cap: auto`) are recovered from recipe/config for all lanes. Wall thickness is not found for
   ATH (mesher default, absent from recipe/config). Termination kind is not found for ext-throat,
   ATH morph and biradial (the measured surfaces are forward-only in z, so not rollback). The ten
   Klangfilm designs' saved implementation digest is `e3a1f4a3…`, not the current legacy-bridge
   digest `ea5026…`; the addendum's verified digest belongs to a different run.

**STOP.** Two or more lanes fail Test 2 on the inner wall. Per the runbook, N2–N5 were not run and
this is handed back.

## Result table

Each T2 cell uses the topology-based inner-sheet isolation (see below): the solid mesh is cut at
sharp creases and the sheet component closest to the sampled inner surface is measured. The literal
step-4b nearest-surface rule is reported separately; it fails more lanes only because it scores
mouth-rim nodes.

| Lane | T1 refinement | T2 mesh agreement (inner) | T3 envelope | T4 metadata | T5 determinism |
|---|---|---|---|---|---|
| `hl__ext_throat_hvlaw_v7` | **pass** 10/10, worst 0.112 mm, descriptor 0.10 % | **pass** 10/10, median-of-medians 0.019 mm, worst p99 0.158 mm | **fail** W 9/10 (+0.65…+1.05), H 6/10 (+0.68…+1.41); depth pass after closure (+0.25…+0.51) | **partial** termination not found | **pass** 10/10 |
| `hl__ath_tritonia_landscape_v9` | **pass** 10/10, worst 0.198 mm, descriptor 0.05 % | **pass** 10/10, 0.013 mm, worst p99 0.850 mm | **pass** W/H (≤0.83); depth 9/10 after closure (+0.55…+1.04) | **partial** wall thickness and termination not found | **pass** 10/10 |
| `hl__crowe_x_osse_cd_v7` | not testable (fixed 25×41 recipe) | **fail** 0/10, 0.057 mm, worst p99 1.870 mm | **partial** W 9/10 (−1.01…−0.35), H 5/10 (−1.64…−0.26); depth pass after closure (+0.23…+0.52) | **pass** all fields | **pass** 10/10 |
| `rf__section_axial_home_v7` | not testable (fixed 49×97 recipe) | **fail** 0/10, 0.053 mm, worst p99 1.696 mm; **49 azimuths pass 10/10 (p99 0.36–0.59)** | **pass** W/H (≤0.68); depth pass after closure (−0.05…+0.07) | **pass** all fields | **pass** 10/10 |
| `hl__klangfilm_lame_curved_v1` | not testable (fixed 19×65 recipe) | **fail** 1/10 (9/10 pass), worst p99 1.457 mm (`b9ea3ad77e3f`) | **pass** W/H (≤0.22); depth raw within 0.18 (rollback already in the sample) | **partial** fields complete but provenance digest does not match | **pass** 10/10 |
| `hl__biradial_es_style_v7` | **pass** 10/10, worst 0.110 mm, descriptor 0.15 % | **pass** 10/10, 0.011 mm, worst p99 0.142 mm | **fail** W/H (+1.94…+3.45); depth pass after closure (+0.08…+0.09) | **partial** termination not found | **pass** 10/10 |

Denominators: 10 stored designs per lane, 60 total; 10/10 materialized for every lane. T5 used two
separate Python processes building all 60 surfaces.

## Selection and provenance

Ten distinct valid stored designs per lane; the five non-Klangfilm lanes reuse the exact hashes in
`.x1/*.npz`, and Klangfilm uses the ten hashes in `.x1/legacy_k_results.txt`. Each design was
resolved by its own build route:

| Lane | Route used here | Native shape |
|---|---|---|
| ext-throat | `hornlab_mesher.config_builder.resolve_geometry` (freestanding) | 33–43 × 169–186 |
| ATH morph | same | 48–55 × 151–192 |
| Crowe | `grid.grid_points` + `grid.grid_outer_points` | 25 × 41 |
| Rolled | `rolled_family.resolve_grid` | 49 × 97 |
| Klangfilm | `tools.geometry.klangfilm_lame.make_grid` + `grid.grid_outer_points` | 19 × 65 |
| Biradial | `resolve_geometry` (freestanding) | 39–51 × 140–187 |

Klangfilm provenance: the ten selected recipes (run `20261116T205942Z-screen-8b22b5`) carry
`rows.schema: klangfilm-lame-v1` and `rows.implementation_sha256: e3a1f4a3…`, while
`tools.geometry.klangfilm_lame_cli.implementation_digest()` at this HEAD returns `ea5026…`.
The addendum's verified value `ea5026…` belongs to the later example run
`20261116T224336Z-screen-55f39d`. The two kernels (`tools.geometry.klangfilm_lame` and
`_klangfilm_lame_v1`) produce byte-identical arrays for the failing design (checked, max difference
0.0), so the geometry code is the same; the digest-covered companion files changed. **These ten
designs' provenance is therefore unverified by digest**, and the surface is accepted provisionally
for the mesh test.

## Test 5 — determinism

Two independent processes built each design and resampled it to 65 × 31. `numpy.array_equal` on the
inner and outer arrays:

| Lane | identical |
|---|---:|
| ext-throat | 10/10 |
| ATH morph | 10/10 |
| Crowe | 10/10 |
| Rolled | 10/10 |
| Klangfilm | 10/10 |
| Biradial | 10/10 |

**Verdict: pass, 60/60.** Both Klangfilm builds used the same `tools/geometry/klangfilm_lame.py`.

## Test 1 — refinement

For the three native/freeform lanes the recipe can be resolved at 10 mm and 5 mm; the 5 mm resolve
double the native station count and roughly doubles the azimuth count (e.g. biradial 46 × 155 →
65 × 283). Both are resampled to the same 65 × 31 normalized-arc record and compared directly; the
record-level 65→129 / 31→61 resampling is zero by construction and is not used as evidence.

| Lane | n pass | worst point movement | largest descriptor change |
|---|---:|---:|---:|
| ext-throat | 10/10 | 0.1115 mm | 0.10 % |
| ATH morph | 10/10 | 0.1978 mm | 0.05 % |
| Biradial | 10/10 | 0.1103 mm | 0.15 % |
| Crowe, Rolled, Klangfilm | — | fixed-resolution recipe: not testable by refinement | — |

The ATH worst value (0.198 mm) is just inside 0.2 mm; two of its ten designs are 0.195–0.198 mm.
**Verdict: pass on all three testable lanes; not testable on the three fixed-recipe lanes.**

## Test 2 — agreement with the stored mesh

### Separation (runbook 4b and its repair)

The literal rule (nearest of the sampled inner and outer surfaces; >3 mm from both = unassigned)
misclassifies mouth-rim nodes: at the mouth the generator's normal-offset outer sheet ends 3–5 mm
behind the lip, so rim nodes are ~t/2 from both sheets and are scored as inner. Literal-rule results:

| Lane | literal pass | med-of-med | worst p99 |
|---|---:|---:|---:|
| ext-throat | 3/10 | 0.019 | 2.440 |
| ATH morph | 3/10 | 0.013 | 2.298 |
| Crowe | 0/10 | 0.058 | 1.868 |
| Rolled | 0/10 | 0.053 | 1.693 |
| Klangfilm | 4/10 | 0.130 | 1.464 |
| Biradial | 9/10 | 0.011 | 1.442 |

The rim tail is the same for every route: e.g. ext-throat's 24 nodes >1 mm are all at
z ≈ 379.6–380.6 mm (the mouth end face). A closed point-grid solid is one surface whose inner
sheet, outer shell and closure faces meet at sharp creases; cutting edges whose adjacent triangle
normals differ by >50° yields 3–4 components. The measured component is the inner sheet (largest
component within 0.5 mm of the sampled inner surface; 956 cm² for ATH, 793 cm² for rolled). This is
the separation the brief asks for; it is independent of the outer sampling.

### Result (topology-separated inner sheet, 65 × 31 record)

| Lane | pass | median-of-medians | worst p99 | worst max |
|---|---:|---:|---:|---:|
| ext-throat | **10/10** | 0.0185 | 0.158 | 0.333 |
| ATH morph | **10/10** | 0.0125 | 0.850 | 2.747 |
| Crowe | **0/10** | 0.0570 | 1.870 | 2.672 |
| Rolled | **0/10** | 0.0526 | 1.696 | 2.910 |
| Klangfilm | **9/10** | 0.1272 | 1.457 | 1.784 |
| Biradial | **10/10** | 0.0107 | 0.142 | 0.329 |

Pass line: median ≤ 0.3 mm and p99 ≤ 1.0 mm.

### Why the three failures

**Rolled — record azimuth resolution.** The azimuth step is the cause, not the station count:

| Sampling | p99 (mm) | nodes > 1 mm | pass |
|---|---:|---:|---|
| native 49 × 97 | 0.487 | 0 | yes |
| 49 azimuth × 65 stations | 0.549 | 0 | yes |
| 61 azimuth × 97 stations | 0.806 | 12 | yes (p99) |
| 31 azimuth × 97 stations | 1.695 | 62 | no |
| record 31 × 65 | 1.696 | 66 | no |

All ten rolled designs: native 49 × 97 p99 0.359–0.589 (10/10 pass); the 31 × 65 record p99
1.213–1.694 (0/10 pass). The 3° azimuth step aliases the rolled relief; **49 azimuths (1.875°)
fixes it and 65 stations are sufficient.**

**Crowe — mesher surface fit plus azimuth chords.** The same design (`9f7b158c831d`):

| Sampling of the same 25 × 41 point grid | p99 (mm) | nodes > 1 mm |
|---|---:|---:|
| native points 25 × 41 | 1.066 | 30 |
| 25 azimuth × 65 stations | 1.184 | 39 |
| dense linear 61 × 129 | 1.152 | 43 |
| 31 azimuth × 41 stations | 1.817 | 64 |
| record 31 × 65 | 1.870 | 66 |

The mesher's smooth fit through the point grid already sits ~1.07 mm from the native points at the
rectangular corner; the 31-azimuth record's linear chords add another ~0.7 mm. No record sampling
tested reaches the 1.0 mm line; the route's measured mesher fit error is ~1.1 mm at p99.

**Klangfilm — one design does not match its stored mesh.** For `b9ea3ad77e3f` the inner p99 is
1.27 mm at native 19 × 65, 1.46 mm at the record, and 1.28 mm at dense 61 × 129 — so it is not a
sampling artefact. The kernel arrays agree byte-for-byte; the saved digest differs from the current
one. The other nine designs pass (worst p99 among them 0.59 mm). This is either a historical
geometry difference for that one design or a mesh/recipe mismatch; it is not established which.

## Test 3 — envelope

Sampled extents are taken over the union of the sampled inner and outer surfaces (a solid's
bounding box), quarter model doubled in W and H. Stored `bbox_m` comes from the mesh's used nodes.

| Lane | W delta (mm) | H delta (mm) | D delta, raw | D delta after rear closure | closure tag-1 z min |
|---|---|---|---:|---:|---:|
| ext-throat | +0.65…+1.05 | +0.68…+1.41 | −4.75…−4.49 | +0.25…+0.51 | −5.0 |
| ATH morph | +0.48…+0.83 | +0.20…+0.58 | −5.45…−4.96 | +0.55…+1.04 | −6.0 |
| Crowe | −1.01…−0.35 | −1.64…−0.26 | −2.77…−2.48 | +0.23…+0.52 | −3.0 |
| Rolled | −0.68…−0.41 | −0.38…0.00 | −3.05…−2.93 | −0.05…+0.07 | −3.0 |
| Klangfilm | −0.22…−0.03 | −0.09…+0.02 | −0.18…+0.07 | (rollback already sampled) | −3.0…−72.4 |
| Biradial | +1.94…+3.06 | +2.68…+3.45 | −2.92…−2.91 | +0.08…+0.09 | −3.0 |

The depth deficit in every full-ring lane is exactly the rear closure behind the throat plane: the
lowest-z tag-1 nodes sit at `z = −t`, while the sampled surfaces start at `z = 0` (or at the
Klangfilm rollback). That is the cause the runbook asked for, and it is not a sampler failure.

Width/height failures: **biradial** is systematic (+1.9 to +3.5 mm). The stored bbox equals the
*inner* mouth width/height exactly (e.g. 560.0 × 350.0 mm); the generator's normal-offset outer
surface adds 1.2–1.7 mm per side beyond the mesh's sharp mouth rim. **Crowe** sampled smaller than
stored (H −1.64 mm on the worst design), consistent with the mesher's smoother/decimated outer
body; not fully established. **ext-throat** is +0.65…+1.41 mm on H, the same rim-offset order.
ATH, rolled and Klangfilm are within 1 mm on W and H.

**Verdict: fail on biradial; partial (near the 1 mm line, cause at the mesher outer/rim) on Crowe
and ext-throat; pass on ATH and rolled; Klangfilm pass.**

## Test 4 — exact metadata

| Field | Value | Source | Recovered |
|---|---|---|---|
| throat radius | 18.00 mm (measured s=0 ring 17.98–18.00) | config `brief.driver.exit_radius_mm`; rolled/Klangfilm also recipe `rows.driver` | 60/60 (config/recipe) |
| exit angle | 2.0° | config `brief.driver.exit_angle_deg`; rolled/Klangfilm recipe `rows.driver` | 60/60 |
| symmetry / quadrants | `hv` / `1` | config `brief.symmetry`, `mesh.quadrants` | 60/60 |
| wall thickness | 3.0 mm (biradial, Crowe, rolled, Klangfilm), 5.0 mm (ext-throat) | recipe `params.wall_thickness_mm` or `params.grid.wall_thickness_mm` | 50/60; **ATH 0/10 not found** |
| source cap settings | `{"cap": "auto"}` | config `brief.source` | 60/60 for the setting; resolved radius/curvature/auto angle **not stored** |
| termination kind | rollback | recipe `params.grid.rows.type` (Crowe, rolled, Klangfilm) | 30/60; **ext-throat, ATH, biradial not found** (recipe/config silent; measured 0/31 non-monotone-z azimuths, so forward-only, but the exact kind is not recorded) |
| mounting | none (freestanding) | config `brief.mounting` absent | 60/60 |

Not found anywhere: ATH wall thickness (a mesher default, not in recipe or config); termination kind
for the three native/freeform lanes; the resolved source-cap radius, curvature and auto angle; and
Klangfilm's digest-verified provenance for this run.

## Verdict against the brief's lines

- **T1:** pass on the three testable lanes (10/10 each); the three fixed-recipe lanes are "not
  testable by refinement", as the runbook instructs.
- **T2:** **the X1 failure condition is met.** Two or more lanes fail the inner-wall test at the
  contract-minimum record: rolled 0/10 and Crowe 0/10, plus one Klangfilm design (9/10). This is the
  brief's stop/plan-change condition, not a threshold that can be relaxed after seeing the result.
- **T3:** fail on biradial; partial on Crowe and ext-throat; pass on ATH (width/height, depth 9/10 at
  +1.04 mm), rolled (after the closure cause) and Klangfilm.
- **T4:** partial; the missing fields and the Klangfilm digest gap are listed above.
- **T5:** pass 60/60.

## What failed / what is unknown

- Rolled fails at 31 azimuths (3° step); 49 azimuths passes 10/10. Unknown: the minimum azimuth
  count that passes all ten at every station (49 works; 61 tested on one design also works).
- Crowe fails at 31 × 65 (p99 1.87) and even at its native 25 × 41 (1.07). The mesher's smooth fit
  through the point grid is the floor. Unknown: whether the mesh's surface fit or the record's
  linear azimuth chords dominates at each corner; a route tolerance is required.
- Klangfilm `b9ea3ad77e3f` fails at native, record and dense sampling. The saved digest for the ten
  is `e3a1f4a3…`, the current digest is `ea5026…`; the addendum's verified digest belongs to a
  different run. Unknown: which historical geometry produced the stored mesh for this design.
- Envelope: biradial's +2–3.5 mm is the generator outer surface versus the mesh's sharp mouth rim;
  Crowe's negative H is unexplained at the millimetre level. A route-specific envelope method is
  needed before T3 can be called.
- The literal step-4b rule is not sufficient to isolate the inner wall; a topology (sharp-crease)
  or signed-position separation is needed. This is a method finding for the contract itself.

## What this does not prove

- Nothing about acoustic equality: no response, solve or score was compared.
- That the surfaces cannot be represented; the failures are at the record's sampling and at the
  mesher's fit, with known remedies.
- That U1–U3 can or cannot proceed: U1 was not run because N1 triggered the stop condition.
- That the ten Klangfilm designs are unrecoverable: nine pass the mesh test; the tenth and the
  digest gap are unresolved.

## Next action enabled

The common shape description is reliable for ATH morph, ext-throat and biradial at the tested
record, and not yet reliable for rolled, Crowe or Klangfilm. Before N4/U1:

1. Raise the record's azimuth sampling for the rolled relief family to at least 49 (1.875°);
   re-run Test 2 (should be 10/10) and record whether any station count above 65 is needed.
2. Decide a Crowe tolerance from the measured mesher fit (~1.1 mm p99 at the rectangular corner),
   or compare against the mesher's own surface rather than the point grid. Do not silently keep
   1.0 mm.
3. Resolve the Klangfilm run/version for the ten selected designs (the digest gap) and the one
   failing design before admitting them to the acceptance table.
4. Revisit the envelope method at the mouth rim (outer offset versus meshed sharp rim) before
   using T3 to reject a route.
5. Then N2/N3 (independent) and N4/U1 may be run. They were **not run here** because the stop
   condition was met.

## Reproduce

```powershell
# from C:\Users\hunte\Hrns\hornlab-search
git rev-parse --short HEAD
git status --short | Select-Object -First 20
.venv/Scripts/python.exe scratch/fable_architecture/.tmp/fable_replay_harness.py
.venv/Scripts/python.exe scratch/fable_architecture/.n1/build.py scratch/fable_architecture/.n1/build1
.venv/Scripts/python.exe scratch/fable_architecture/.n1/build.py scratch/fable_architecture/.n1/build2
.venv/Scripts/python.exe scratch/fable_architecture/.n1/build.py scratch/fable_architecture/.n1/build_ref --res 5
.venv/Scripts/python.exe scratch/fable_architecture/.n1/analyze.py
.venv/Scripts/python.exe scratch/fable_architecture/.n1/component_check.py
.venv/Scripts/python.exe scratch/fable_architecture/.n1/inner_wall2.py
.venv/Scripts/python.exe scratch/fable_architecture/.n1/resolution_test.py
.venv/Scripts/python.exe scratch/fable_architecture/.n1/rolled_native.py
```

`analyze.py` writes `.n1/results_partial.json`; `component_check.py` writes
`.n1/components.json`; `inner_wall2.py` rewrites `.n1/inner_wall_final.json` and appends the rolled
native comparison. No file outside `scratch/fable_architecture/` was written; `runs/`, `examples/`,
`hornlab_search/` and `tools/` were read only.
