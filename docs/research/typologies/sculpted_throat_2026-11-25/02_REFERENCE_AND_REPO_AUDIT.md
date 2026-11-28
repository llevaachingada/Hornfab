# Sculpted throat — reference CAD and repository audit (2026-11-25)

Handoff: [`00_HANDOFF_2026-11-25.md`](00_HANDOFF_2026-11-25.md) (moved here from the owner's Downloads).
Web source pass: [`01_SOURCE_VERIFICATION.md`](01_SOURCE_VERIFICATION.md). Evidence packet:
[`docs/evidence/throat_sculpting_2026-11-25/`](../../../evidence/throat_sculpting_2026-11-25/README.md).
Labels: [measured] (computed here from files on disk), [published], [reported], [inferred], [unverified].

## 1. Local state at start (protects concurrent work)

- Checkout `C:/Users/hunte/Hrns/hornlab-search`, branch `hornfab-all-2026-11-18`, HEAD `9ce1550e` (the handoff
  indexed `626a7c65`; three commits landed since). Pre-existing uncommitted files (skills, knowledge cards,
  `docs/handoffs/repo_findability_2026-11-25/`, a screen_12k experiment dir) were left untouched.
- GPU: the `cd_bo_cohort_2026-11-25` night was paused at 19:16 and **resumed by its owner at 19:48**
  (`favl_pm5_size`, ~60 jobs queued). The GPU lane was therefore never used by this pass; the acoustic pilot runs
  on the CPU lane (`beat_cpu`, own worker registry, `runs/.cpu.lane.lock`), which the two-lane rule allows.
- **Digest hazard found and avoided.** `rows_bb_v1`'s implementation digest hashes `grid.py`; its current value
  `3ce85c42…` matches ~300 designs saved today by that night (e.g. `dataset/shard-0099.jsonl`, `-0100.jsonl`),
  and the queued `explore_verify_tops` job re-verifies tops from it. Registering a new kind in `grid.py`'s
  dispatch tuples would orphan all of them. The new family is therefore **not** registered in `grid.py` /
  `mesh/build.py` / `generated.py` in this pass; the 14-line byte-wise patch is staged in
  [`dispatch_registration.patch`](dispatch_registration.patch) for the owner to apply when no saved `rows_bb_v1`
  recipe still needs replay (it is the only step between this lane and CLI `search`/`verify`).

## 2. ST260-BLD reference CAD [measured]

### 2.1 Manifest

| file | URL | bytes | sha256 | archive member (date) |
|---|---|---:|---|---|
| `ST260-BLD-v1-STEP.zip` | https://at-horns.eu/ext/ST260-BLD-v1-STEP.zip | 1,366,409 | `d8e0f8f1…89665f90` | `ST260-BLD-v1.step` 5,004,565 B (2022-11-19; header name "ST260-BLD v5 v1.step", Autodesk translator) |
| `ST260-BLD-mres.zip` | https://at-horns.eu/ext/ST260-BLD-mres.zip | 1,460,056 | `7f39635d…b10a037d5`¹ | `ST260-BLD-mres.stl` 3,178,184 B (2022-08-03), 63,562 binary triangles |

¹ full archive and member hashes: evidence `reference_manifest.json`. Downloaded 2026-11-25 19:31 EST, both
HTTP 200. Kept local-only in the git-ignored `/reference/ath_st260_bld/` (license: the author states free for
non-commercial use [published]; CC BY-NC-SA wording was not found — `01_SOURCE_VERIFICATION.md` s1). No
script from the archives was run; STL parsed as bytes with numpy, STEP tessellated with OCP. Only derived
section measurements are committed.

Frame: the files are already in mm with the flange bore at z = 0 (circle r = 12.70 mm, all azimuths) and z
increasing into the horn; bbox x,y ±130, z 0…108.3 mm. No re-alignment was needed.

### 2.2 Sections (STL, first wall hit from the axis, `tools/geometry/throat_sections.py`)

| z mm | r(0°) | r(45°) | r(90°) | area / source | A / A_hull |
|---:|---:|---:|---:|---:|---:|
| 0 | 12.70 | 12.70 | 12.70 | 0.994 | 1.000 |
| 1 | 12.88 | 12.73 | 12.16 | 0.987 | 0.998 |
| 3 | 13.24 | 12.79 | 11.11 | 0.972 | 1.000 |
| 5 | 13.69 | 12.93 | 10.13 | 0.972 | 0.994 |
| 7.5 | 14.35 | 13.18 | 9.02 | 0.986 | 0.978 |
| 10 | 15.13 | 13.54 | 8.02 | 1.024 | 0.956 |
| 15 | 17.02 | 14.70 | 6.36 | 1.179 | 0.917 |
| 20 | 19.29 | 16.36 | 5.24 | 1.439 | 0.892 |
| **25.5** | 22.25 | 18.70 | **4.80** | 1.868 | 0.878 |
| 30 | 25.01 | 21.00 | 5.10 | 2.352 | 0.876 |
| 40 | 31.90 | 26.99 | 7.31 | 3.888 | 0.883 |
| 50 | 40.23 | 34.59 | 11.98 | 6.420 | 0.899 |
| 60 | 49.92 | 43.68 | 19.29 | 10.34 | 0.921 |

Findings:

1. **A genuine below-source-radius pinch in the real wall**: r(90°) falls from 12.70 to **4.80 mm at z = 25.5 mm
   (0.378 r0, 7.9 mm intrusion per side)** and re-crosses r0 only at z ≈ 52 mm. The orthogonal plane opens
   from the first millimetre. This is not a cap artefact (the cap is not in the file; the flange ring is exact).
2. **Directional constriction at constant area**: section area stays 0.97-0.99 of the source disk through
   z ≈ 7 mm while one pair of walls goes in and the other goes out; total area only grows after z ≈ 9 mm.
3. **Nonconvex** sections (A/A_hull down to 0.876; negative signed curvature on the pinched flanks).
4. **21.0 %** of the source disk (area-weighted) is axially occluded by the wall.
5. Shape content: Fourier fits of r(φ) at every z are almost entirely **c2 and c4** (c2/c0 ≈ +0.51, c4/c0 ≈
   −0.16 at 25 mm, c6/c0 ≈ +0.025, orders ≥ 8 < 1 %; `fourier.csv`). A low-order even-cosine basis therefore
   expresses the reference section; the reference differs from a compact "ridge" by its long axial extent.

### 2.3 Recipe check (`tools/geometry/rosse_reference_fit.py`)

The handoff's transcription `R-OSSE {R 130, r0 12.7, a0 = 8 − 35 sin⁴p, a 39.5, k 3, r 0.25, b 0.29, m 0.82,
q 4.5}` evaluated with the **pinned mesher's own** `profile_points` (no rotation needed: p = 0 is +x and the pinch
is at p = 90°) reproduces the STL wall to **0.082 mm RMS, 0.39 mm max** over z 0-50 mm (per-meridian RMS 0.03 mm
on H rising to 0.20 mm at 90°). Analytic waist 4.56 mm at z 26.5 vs CAD 4.80 at 25.5. Initial wall angles
(first 0.5 mm): CAD 10.0° / 1.7° / −28.5° at 0/45/90°, analytic 8.6° / −0.5° / −27.9° (the STL "mres"
tessellation chords the first half-millimetre). So the forum recipe **is** the CAD [measured], and its mechanism
is exactly the handoff's Operator B: a **signed angular throat angle**, negative over ±40° of the pinch axis.
STEP parity: see the evidence README (OCP tessellation at 0.02 mm).

Physical caveat [inferred]: BLD's source tangent is −27.9° on one axis and +8.6° on the other. That cannot be
matched to a real compression-driver exit, which is why HornFab's driver-matched lane (below) keeps the source
tangent and turns inward only after the source plane.

## 3. Seeds (subagent audit, re-checked by replay)

| seed | config | brief / identity | J | status |
|---|---|---|---:|---|
| **FAV-001** `4140768780f0` | `examples/typologies/fav8_2026-11-20/fav8__k1_cd_polish.yaml` seed (= cd11c best) | `room_landscape_80x50_700_hf1440_v11cd`, v11, r0 18.0 mm, a0 2° | **4.9939 verify** (GPU, 4487 DOF) | chosen parent; replayed here: same hash, CPU verify J 4.993855 |
| P1 split-plane `favP1s__fav_kv3_sv` | `examples/typologies/favP1_2026-11-20/` | same | 4.657 (CPU screen proxy) | no filed verify; second parent for phase 2 |
| mouth polish `392276e62470` | `fav8__k1_cd_polish.yaml` run | same | screen only | phase 2 |
| k-home `cd7e60025f70` | home-900 brief | different identity (2.604) | — | not pooled |

FAV-001 was chosen because it is the only verified incumbent on one identity and it **replays exactly** (design
hash and J to 2.6e-5), so every pilot delta is attributable. Its H beamwidth sits below the 80° target at HF
(the motivation for a horizontal pinch in the handoff). The brief's r0 is **18.0 mm**, not the 17.78 mm the
handoff assumed.

## 4. Code trace and guards

- Rows route: `grid._rows_osse_rollback_marches` (OSSE wall per azimuth from `profile_points`, 400 samples, then
  superformula morph, beak, flutes, tangent lip) → `rows_per_azimuth` → `_build_rows_grid` (uniform-arc
  resample to `n_s`) → `mesh/grid_build.build_grid_mesh` → `PointGridHornGeometry` (axial edges between grid
  stations are straight; FAV's 40 stations are ~8 mm apart, too coarse for a 10-40 mm throat feature).
- Guards that matter here: per-row `x` strictly increasing and `y > 0` — **a negative dr/dz is legal** (no
  monotone-radius guard on this route); `_sheet_min_nonadjacent_gap` / `check_self_approach` (topology);
  mesher symmetry-plane topology guard (refused `S_v20`, see atlas); source tag 2 non-empty; dof cap 24000.
  The Klangfilm no-constriction guards live in that family only and were not touched.
- `throat_hv_ratio` (shared block) rescales OSSE `k` per azimuth; with the source slope fixed it cannot enter
  the source disk, so it is not a pinch mechanism. `g_a_d_deg` / `g_beak_*` act on the far wall / lip.
- Existing native `slotLength` in the mesher is a straight r0 tube **prepended** (ATH semantics [published]); it
  lengthens the horn. The new slot operator is a different, mouth-preserving construction (labelled).

## 5. What was built (see `hornlab_search/design/generators/_throat_sculpt_v1.py`)

New kind `throat_sculpt_v1` (`throat_sculpt_family.py` + `_throat_sculpt_v1.py`, own digest; parent recipe carried
under `rows.parent_rows`; neutral = parent bit-for-bit). Operators on the parent's forward core only:

- **(A) slot**: `D(ψ) = Dh|cos|^{2p} + Dv|sin|^{2p} + Dd|sin2ψ|^{2p}`; wall = source cone up to D, then the
  parent's excess flare through a C2 monotone quintic delayed coordinate that rejoins the parent exactly at
  `z_rec = max D + span` (mouth, depth and lip unchanged).
- **(C) radial sculpt**: `r += r0·w(z)·(c2 cos2ψ + c4 cos4ψ + c6 cos6ψ)`, w a C2 compact bump (onset/rise/fall
  spans, so the order is always valid); `ts_area = 1` rescales each section to the pre-sculpt area.
- Re-stationing: shared core/body station split, `core_step_mm` (default 3 mm) through the core.
- Achieved descriptors (waist, z/ψ of the minimum, true-pinch flag, area monotonicity, H/V ratio) are recorded
  in the meta from the emitted rows; a pinch target is root-found on `ts_c2` by the pilot tool.
- Operator B (signed angular a0) is reproduced natively for the reference (R-OSSE + a0 expression, §2.3) but
  is not offered as a driver-matched production knob: C with c2 < 0 is the driver-matched equivalent.
- Operator D (free loft) was not needed: c2/c4/c6 fits the reference sections.

## 6. Discrepancies with the handoff

| handoff | found |
|---|---|
| HEAD 626a7c65 | 9ce1550e (+ local changes) |
| HF1440 r0 ≈ 17.78 mm | brief pins 18.0 mm, a0 2° |
| BLD recipe needs CAD verification | verified to 0.08 mm RMS |
| `favRBs__ridge8` = candidate control | it changes depth (244.9 mm); not a clean control — the pilot uses FAV-001 itself |
| GPU pilot | GPU lane held by the owner's night; CPU lane used (backend parity 2.6e-5 in J) |
| Tritonia-X a published ATH design | not an official at-horns.eu product; forum-only, unverified |
| ATH Slot.Length | prepended straight tube (User Guide [published]) — not the mouth-preserving slot built here |
