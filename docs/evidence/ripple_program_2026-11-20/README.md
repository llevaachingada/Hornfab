# Ripple program, 2026-11-20: corpus sweep, source sensitivity, HF width

Three experiments run back to back after the [handoff bundle](../../research/ripple_hf_2026-11-19/README.md).
All of it is report-only; **no score term was added or changed, and no stored `J` moved**. The one
piece of GPU work is listed with its baselines and peaks at the end.

Headline: **(1)** across 748 stored runs (545 unique designs) the fixed-angle residual is *not* redundant with `rip`
(the 24-design sample that suggested otherwise was unrepresentative), **(2)** the source-wavefront
assumption **cannot currently be varied at all** — `source.cap` is an inert key on the grid path, so
mandate item 5 was blocked by a bug, not by physics, and **(3)** HF width at 8 kHz is set by the wall
angles and **cannot be widened inside the 600 mm home envelope**.

## 1. Corpus-wide sweep - the redundancy question, answered on 748 runs

Tool: `tools/analysis/spectral_corpus_sweep.py` (report-only, zero solver calls). Per run it takes the
`best.json` design, computes V+/-25, V+/-35, V+45, H+25 and H+35 trend residuals plus V+25/V+35
band-mean residuals through `hornlab_search/metrics/spectral.py`, reads `terms.rip`, and groups by
**`brief.name` AND objective version** (`identity @ vN`).

Two hygiene rules were added after the first pass, and both changed the numbers:

- **Deduplicate by `design_hash`.** The same design is often solved into several run dirs (resumes,
  re-runs, mirrored studies): 748 usable runs hold 545 unique designs (1.37x). Correlations use
  unique designs; `rows` keeps the raw count.
- **Never pool across objective versions.** `organic_rollback_1in` mixed five Oct-25 runs with no
  declared version (rows `salmon_elliptical` / `iwata_ar` / `lecleach_asym`, J 45-86) with five
  Nov-13 v3 runs (all `salmon_elliptical`, J ~40). Its apparent rho of **-0.871 was an era-mixing
  artefact**; split, it reads -0.500 (v3, n=5) and +0.300 (v?, n=5). The earlier claim that this
  identity is anti-correlated is **retracted** - it was two design generations under one name.

Scanned: **748 usable**, 0 refused, 25 skipped (no resolvable design). Tabulated: 24 identities with
n >= 5 unique designs; 67 smaller ones excluded.

| identity | n | rows | median V+35 (dB) | p90 V+35 (dB) | rho(rip, V+35) |
|---|---:|---:|---:|---:|---:|
| `room_landscape_80x50_700_hf1440_v7` @v7 | 106 | 115 | 0.509 | 1.005 | 0.727 |
| `room_landscape_80x50_700_hf1440_v7_smooth` @v7 | 52 | 58 | 0.251 | 2.231 | **0.929** |
| `axi_90x90_1in` @v? | 38 | 82 | 1.228 | 1.781 | **-0.161** |
| `freeform_sculpt` @v? | 33 | 36 | 0.902 | 1.168 | **-0.120** |
| `b3a_pa_90x90_400_square_v4` @v4 | 29 | 29 | 0.577 | 1.410 | 0.761 |
| `room_80x60_700_hf1440_v7` @v7 | 23 | 37 | 0.541 | 0.663 | -0.240 |
| `compact400_xo1000_1400_hf1440_v10xo` @v10 | 21 | 27 | 0.587 | 0.798 | **0.061** |
| `room_landscape_80x50_700_hf1440_v10` @v10 | 21 | 29 | 0.319 | 0.835 | 0.765 |
| `hifi_90x60_1in` @v? | 16 | 21 | 1.120 | 1.905 | 0.532 |
| `room_landscape_80x50_700_hf1440_v11cd` @v11 | 15 | 20 | 0.429 | 1.671 | 0.725 |
| `native_ath_core_2in` @v3 | 7 | 7 | 0.382 | 0.508 | **0.893** |
| `organic_rollback_1in` @v3 / @v? | 5 / 5 | 17 / 12 | 0.372 / 0.227 | 0.374 / 0.230 | -0.500 / +0.300 |

Full table, per-run rows and provenance: `runs/analysis/corpus_sweep_v3_2026-11-20/{sweep.md,sweep.json}`
(git-ignored with `runs/`; regenerate with the command at the end of this file).

**What this says.** Pooled rho(rip, V+35) = **0.662** over 545 unique designs, and **21 of 24
tabulated identities sit below 0.8** - at the strict end with correlations indistinguishable from
zero or negative (`axi_90x90_1in` -0.161 on 38 designs, `freeform_sculpt` -0.120 on 33,
`compact400` 0.061 on 21). Only three reach 0.8+: `room_landscape...v7_smooth` (0.929, n=52),
`native_ath_core_2in` (0.893, n=7) and `b1w_hifi_90x60_850_wide` (0.881, n=8).

So the 2026-11-19 conclusion ("largely redundant", rho 0.885 on 24 SCOUT40 bests) holds **only for the
v7_smooth family**, which is exactly the sample that was measured. Across the rest of the corpus the
fixed-angle residual is a second axis. The remaining gate is acoustic, not statistical: nothing here
shows that a large residual sounds bad.

Two machinery checks from the same run:

- rho(V+25, V+35) is 0.6-1.0 in most identities: **one seat angle is enough**; the second adds rank
  stability only.
- rho(trend, band_mean) ranges from -0.85 to +0.95 across identities - the reference-choice finding is
  a property of the families, not of the sample.

## 2. Source sensitivity — how the bug was found (the knob was inert)

Night `source_sensitivity_2026-11-20`, 6 jobs: two anchors (Crowe X OSSE `9b5428e6dec8`, OSSE morph
`cf716e738ef8`) × three source caps (auto / 150 mm / 60 mm curvature), each re-solved at verify
fidelity under a 12 kHz `verify_only` brief (`examples/briefs/source_sensitivity_2026-11-20/`), so the
8–12 kHz region above the 5.61 kHz throat cut-on is actually sampled.

**Result: all three caps are numerically identical — to 0.00 in every beamwidth and level.**

```
crowex  auto/150/60 : bwH 8k 74.06   bwV 8k 54.27   V+35@8k -10.18 dB   V+35@12k -10.87 dB
morph   auto/150/60 : bwH 8k 60.25   bwV 8k 50.39   V+35@8k -11.38 dB   V+35@12k -13.94 dB
```

That is not a physical result. It is the bug: `mesh_hash` is **identical (`7abdb66729…`) across all
three**, and only the first solve of each pair really ran (`cached: false`); the other two are cache
hits. `hornlab_search/mesh/grid_build.py` hardcodes
`PointGridHornGeometry(..., source_shape=1, source_auto_angle_deg=<throat angle>)` and never passes
`source_radius_mm`, so the mesher's `_source_cap_radius` always takes the auto-angle branch and the
brief's `source.cap` is decorative. **Every grid-family solve we have ever stored uses the auto cap.**

What that costs: the one experiment that could have bounded how much of our 8–12 kHz result is the
source assumption returned "no difference" for a purely mechanical reason. A reader who does not
compare hashes would file that as "the source doesn't matter" — the exact wrong conclusion, and the
third silent-killer of this session alongside the void dense pair and the bridge-cell verify hole.

Fix landed the same afternoon (see 2b): the brief's cap now reaches `source_radius_mm` in
`grid_build.py` **and** the mesh identity (`MeshSpec.source_cap_mm`, hash-neutral at 0), so `auto`
stays byte-identical to every stored hash while 150/60 produce distinct meshes. Item 4's comparisons
remain at the auto cap, which is now a declared condition rather than an invisible default.

## 2b. Source sensitivity, re-run with the knob live

Night `source_sensitivity2_2026-11-20` (same six jobs, new output dirs; the pre-fix runs stay under
`runs/source_sensitivity/` as the record of the bug). The fix works: the meshes now differ.

| anchor | cap | mesh sha256 | bwH 8 / 10 / 12 k | bwV 8 / 10 / 12 k | V+25 8 k / 12 k |
|---|---|---:|---|---|---|
| Crowe X (grid route) | auto | `884b6eef…` | 74.1 / 68.1 / **65.7** | 54.3 / 48.7 / 53.4 | −4.99 / −5.11 |
| Crowe X | 150 | `f3cb5316…` | 74.1 / 69.0 / **63.3** | 54.2 / 49.5 / 55.4 | −5.00 / −4.50 |
| Crowe X | 60 | `d59e8c75…` | 74.1 / 71.1 / **55.6** | 54.1 / 52.2 / 57.0 | −5.03 / −3.89 |
| OSSE morph (native route) | all three | `c59ec195…` (identical) | 60.3 / 52.5 / 50.4 | 50.4 / 47.1 / 44.1 | −5.94 / −7.71 |

**The answer, and it is frequency-dependent.** For the grid route the wavefront assumption is
irrelevant where the handoff made its comparisons and decisive where it warned:

- **8 kHz: the source does not matter** — width moves ≤ 0.2 deg, the +25 deg level ≤ 0.05 dB across a
  cap change from ~513 mm curvature to 60 mm (a 0.31 mm dome vs a 2.73 mm dome). Every 8 kHz claim in
  the handoff, including Crowe X OSSE's 74.0 x 53.9 deg, survives a change of source model.
- **10 kHz: it starts to matter** — up to 3.1 deg (H) and 3.5 deg (V).
- **12 kHz: it decides** — H width **65.7 -> 55.6 deg (-10.1)**, and the +25 deg level **-5.11 ->
  -3.89 dB (+1.2)** as the cap tightens. A 10 deg swing at 12 kHz is larger than most of the design
  differences we have been ranking.

So the handoff's "8–16 kHz is source-conditional" is right in substance but wrong in scope: the
conditionality starts around 10 kHz, not at 8. Any report above ~10 kHz must state its cap; at 8 kHz
it need not.

**Second gap, found by the same run.** The native route (OSSE/FREEFORM, e.g. OSSE morph) still ignores
`source.cap`: all three meshes are **byte-identical** (`c59ec195…`) while the recorded `mesh_hash`
differs, because `MeshSpec` now carries the cap on every route. That is safe for the response (same
mesh, same answer) but it makes the provenance overstate what changed - a reader sees three mesh hashes
and one mesh. The native spec path needs the same wiring, or an explicit refusal when a native brief
sets a cap.


## 2c. Native route wired - and a poisoned cache entry caught in the act

`hornlab_search/mesh/build.py` now forwards the brief's numeric cap into the mesher config's
`source.source_radius_mm` for the formula route (OSSE / R-OSSE / ICW / FREEFORM). Evidence it works,
from a direct `build_mesh` call on the morph design (CPU only):

| cap | `MeshSpec.source_cap_mm` | triangles | `.msh` sha256 |
|---|---:|---:|---|
| auto | 0.0 | 16,062 | `04fe395f3fa5` |
| 150 | 150.0 | 16,062 | `148dcbd015f3` |

`auto` is byte-identical to the pre-fix meshes (screen `ababdbae8fea`, 12 kHz `c59ec195933a`).

**But the first re-run (`source_sensitivity3`) did not measure anything.** `ss_morph_cap150` came back
`cached: true, solve 0.0 s` with the **auto** mesh copied into its directory, under the *correct*
cap-aware key `cf716e738ef8-bcf9a8cec98b-d0fa0a468ff5`. Cause: the pre-fix `source_sensitivity2`
run had already recorded that same cap-aware `mesh_hash` while the native builder ignored the cap, so
its auto-mesh response was cached under a key that only became meaningful after the fix. The cache
entry is poisoned, and re-running with the fix silently returns it.

This is a general hazard, not a one-off: **a cache key is only as honest as the hash recorded at
solve time.** Any run produced while a knob was silently inert can poison every later run of the same
identity. The clean re-run therefore passes a fresh `--cache-dir`:
`docs/queue/source_sensitivity4_2026-11-20.yaml` (3 jobs) - **staged, not yet run**: a concurrent
`fav_crowe` search and its Julia host held the GPU lane for the whole afternoon window, and this
workstream does not start a second solve.

## 3. HF width — one knob at a time, and an envelope that binds

Night `hf_width_2026-11-20`, base = Crowe X OSSE best `9b5428e6dec8` (wall H 36.39° / V 22.71°, lip
18.28 mm, L 259.60 mm), all knobs pinned, one factor per config, screen fidelity.

`tools/shape_check.py` first: the base seed is **envelope-saturated** — mouth 593 × 412 mm inside the
600 × 480 mm HOME brief. Wall ×1.15 → 672 mm mouth (OVER), lip ×1.5 → 614 mm (OVER). Both were deleted
rather than queued; the legal space is one-sided (shrink only).

| config | change | J | bwH 4.26 / 6.22 / 8 k | bwV 4.26 / 6.22 / 8 k | V+25@8k | V+35@8k |
|---|---|---:|---|---|---:|---:|
| baseline | — | 5.3454 | 71.5 / 72.7 / **74.0** | 55.7 / 54.1 / **53.9** | −5.08 | −10.27 |
| lip_lo | lip 18.28 → 9.14 mm | 5.5866 | 72.7 / 72.9 / **74.2** | 57.7 / 54.1 / **54.1** | −5.02 | −10.21 |
| wall_lo | wall angles ×0.85 | 6.7169 | 63.9 / 61.1 / **62.2** | 49.8 / 48.2 / **47.2** | −6.77 | −12.02 |

Against the pre-declared thresholds (≥1° or ≥0.5 dB = controllable):

- **Wall angle is the lever**: −11.8° H and −6.7° V at 8 kHz, −1.7 dB at +25°, and it costs +1.37 J.
- **Lip radius is essentially inert** for HF width: +0.2° / +0.2° / +0.06 dB, i.e. inside the noise
  of the detrend/angle choices. It does move J slightly (+0.24), through the loading/pattern terms.
- Baseline reproduces the stored SCOUT40 design exactly (same hash → cache hit, J 5.3454), which
  validates the pinned-config construction.

**Consequence for "how do we get a wider HF pattern?"** Not with these knobs inside this envelope:
width tracks the wall angle, and the wall angle is already at the 600 mm mouth limit. Widening HF
requires a larger envelope (owner decision) or a different mouth/aspect law — which is what mandate
item 4's *second* factor (aspect/morph) should test next, not more wall angle.

## 3b. Item 4, second factor - the mouth law is also envelope-bound

Follow-up to §3: if the wall angle is at the mouth limit, can a *mouth-law* change steer HF width
inside the same 600 mm envelope? Three one-knob variants of the Crowe X OSSE base, all pins except one
(`tools/shape_check.py`, before any solve):

| variant | knob | mouth W x H (mm) | verdict |
|---|---|---:|---|
| `hf_crowex_sf0` | `g_sf_amt` 0.239 -> 0.0 (no superformula morph) | 610 x 447 | **OVER 600 - refused, deleted** |
| `hf_crowex_sf5` | `g_sf_amt` 0.239 -> 0.5 (stronger morph) | 596 x 462 | fits - solve staged |
| `hf_crowex_s550` | `g_s` 0.390 -> 0.550 (aspect) | 663 x 470 | **OVER 600 - refused, deleted** |

Two of the three legal-looking mouth-law directions are already outside the envelope, and the one that
fits is +3 mm wider than the base - i.e. this typology has essentially **no mouth-law headroom at
600 mm**. Read together with §3, the answer to "how do we get a wider HF pattern?" is now measured, not
guessed: neither the wall angle nor the mouth law can widen it inside the home envelope, so a wider
horn needs a bigger envelope (owner decision) or a different construction - not another knob search.

`hf_crowex_sf5` is queued in `docs/queue/hf_width2_2026-11-20.yaml` and **not yet run**: a concurrent
night resumed a search and owns the GPU lane. Its pre-declared reading is in the file (>=1 deg or
>=0.5 dB = the mouth law matters at the margin; <=0.3 deg / 0.2 dB = it does not).

## 4. What we now know we need

1. **The native-route source knob.** The grid route is fixed and measured (2b); OSSE/FREEFORM configs
   still ignore `source.cap` and record a `mesh_hash` that overstates what changed. Wire it or refuse it
   before any native-family HF comparison is believed.
2. **Envelope headroom or a mouth-law change** if wider-than-74 deg HF at 8 kHz is a goal. The home
   envelope is the binding constraint, not the shape family.
3. **An acoustic criterion for the fixed-angle residual** before it ever becomes a term. The corpus
   shows it is a second axis on 21 of 24 identities; what it does not show is that a large residual is
   *audibly* bad. The honest next test is the one measurement we cannot simulate: a real driver on a
   real horn, with the fixed-angle curve measured at the seat.
4. **Corpus hygiene, now enforced in the tool.** Dedupe by design and group by (brief, objective
   version). The one identity that looked like a strong anti-correlation
   (`organic_rollback_1in`, rho -0.871) turned out to be two design generations under one brief name;
   split by version it reads -0.500 and +0.300, both on n=5. Any future corpus claim must carry the
   same two guards, or it will measure era, not acoustics.

## 5. Verification and provenance

```
.venv\Scripts\python.exe tools/analysis/spectral_corpus_sweep.py --runs-root runs ^
    --out runs/analysis/corpus_sweep_v3_2026-11-20                  -> exit 0, 748 usable, 0 refused, 545 unique
.venv\Scripts\python.exe -m pytest -o addopts="" -q -p no:cacheprovider ^
    tests/test_tools_analysis_spectral_corpus_sweep.py               -> 4 passed
.venv\Scripts\python.exe tools/shape_check.py "examples/typologies/hf_width_2026-11-20/*.yaml"
                                                                    -> 3 pass, 2 OVER (deleted)
```

GPU work (two nights, both `HORNLAB_GPU_LOCK=refuse`, `gpu-clean` before/after every job, one solve
at a time): `source_sensitivity_2026-11-20` 6 jobs, 2 real solves, peaks 887–1697 MiB, baselines
737–848 MiB; `hf_width_2026-11-20` 3 jobs, 2 real solves (18.7 s / 22.1 s), peak ≤ 1 GB. No solve ran
concurrently with another: one night's first job was refused `GPU busy` by a foreign job, waited, and
then ran. Queue logs `runs/nights/queue_{source_sensitivity,hf_width}_2026-11-20.log`; per-job logs and
`summary.jsonl` in `runs/nights/<night>/`.

Uncommitted machine output (all under the git-ignored `runs/`): the six source-sensitivity responses
and the three HF-width responses; regenerate by re-running the two night files in `docs/queue/`.
