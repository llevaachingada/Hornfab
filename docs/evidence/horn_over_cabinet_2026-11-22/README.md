# Horn-over-cabinet assembly: local run record, 2026-11-22

**Status:** working evidence. One three-dimensional assembly pose is resolved from real
geometry, reproduced by Boundary Lab staging, proven mechanically legal, rendered from the
compiled meshes, and solved on CPU at three legal placements. One further pose is refused
for a real penetration. Nothing here is a calibrated two-way system result.

Working tree: `C:/Users/hunte/Hrns/hornlab-search`, branch `hornfab-all-2026-11-18`, HEAD
`a30f2de9` **plus uncommitted changes** (see §1.3). Other agents' uncommitted
optimizer/sculpted/GUI work was left untouched.

---

## 1. Installed versions and what changed

### 1.1 Environment (verified this session)

| Component | Version | Path / identity |
|---|---|---|
| Boundary Lab | **0.5.0**, `v0.5.0-10-g15f9a89`, clean tree | `C:\Users\hunte\Github\boundary-lab` |
| Boundary Lab HEAD | `15f9a89245a9adfec8c2f0006c164953ce381e58` | **the baseline HornFab documents** |
| BEAT engine (in BL's venv) | `beat-engine 0.7.0` | — |
| HornLab venv | `hornlab-beat-bem 0.2.0`, numpy 2.5.4, scipy 1.18.1, meshio 5.3.5, gmsh 4.15.2 | `.venv` |
| HornFab | HEAD `a30f2de9`, branch `hornfab-all-2026-11-18` | — |

**Version decision:** the installed Boundary Lab is the pinned baseline, **not** the
68-commits-ahead public `main` the handoff cites. No upgrade was attempted: nothing in
this pass needed a newer feature, and the GPU lane was in use by another agent. This
removes one of the handoff's open questions.

### 1.2 Reuse matrix — what Boundary Lab already does

| Capability | Where | Decision |
|---|---|---|
| Parametric rectangular vented enclosure, front woofer, flared port, 3 mm fit rules | BL `geometry_providers/vented_enclosure` | **reuse as-is** (no port) |
| Coupled FEM interior + BEM exterior + LEM transducer + port interface | BL physical compiler / `system_solve` | **reuse as-is** |
| Full 3-D mesh translation in metres (`points*scale_to_m + translation_m`, scale first) | BL `physical_compiler._transformed_mesh` | **reuse**; HornFab needed no change here |
| Imported horn as `bem_surface`, `normal_velocity` excitation, rigid other groups | HornFab `runner_stage.py::_stage_horn` | **already correct**; kept |
| `blab project validate` (graph/ports/regions) | BL `project_cli` | **reuse** |
| Per-excitation complex results, H/V polars, sphere, probes | BL headless results | **reuse**; HornFab reader unchanged |
| Channel synthesis (gain/polarity/delay/ideal filters) | BL `channel_synthesis.py` | **reuse, not used in this pass** |
| Inter-body collision / clearance | **nobody** — BL has none, `project validate` accepts intersecting bodies | **new, minimal** (`boundarylab/collision.py`) |
| One authoritative 3-D pose | **nobody** — screen wrote Y-only, `plan_assembly` wrote Z-only | **new, minimal** (`system/assembly_pose.py`) |
| AABB + vertex clearance guard | HornFab `boundarylab/clearance.py` | **kept as a coarse cross-check**, no longer the verdict |

**Implementation work explicitly avoided:** no second woofer generator, no coupled solver,
no crossover engine, no DSP block, no mesh renderer inside the solver path, no BL upgrade,
no vendor copy of BL, no new binary collision dependency (no trimesh/FCL/VTK install).
The renderer is a 90-line matplotlib evidence tool, not a product component.

### 1.3 Changes made (uncommitted, preserved for review)

| File | Change |
|---|---|
| `hornlab_search/system/boundarylab/collision.py` | **new.** Exact triangle-surface-vs-solid-box clearance: vertex/edge/box-edge decomposition, slab-clip penetration detection, containment, box-vs-compiled-mesh verification. No new dependency. |
| `hornlab_search/system/assembly_pose.py` | **new.** `AssemblyPose` (one resolved 3-D pose, hashed, serialisable), overhang placement policy with the closed-form minimum `dy` from the real mesh, silhouette-vs-collision separation, optional driver-frame solid. |
| `hornlab_search/system/boundarylab/stage.py` | stage gate now uses the exact horn-vs-cabinet (and optional driver-frame) check; the legacy AABB/vertex report is retained in the manifest as `clearance.aabb_vertex_guard`; the spec may carry a full `pose` block. |
| `hornlab_search/system/woofer_seed.py` | `HornEnvelope.mesh_path`; `placement_legality(..., horn_points_mm, placement_policy, woofer_frame_center_y_mm)`; `PlacementCheck.notes`/`aabb_overlaps`/`woofer_frame_center_y_mm`; `run_seed_screen(..., placement_policy)`; CLI `--placement-policy`. Default behaviour is unchanged (`envelope_above`); the frame centre is now the resolved mount height in **millimetres** (§6.1). |
| `hornlab_search/system/contracts.py` | `AssemblyPoint` now carries `horn_mount_offset_xyz_mm` with `z`/`y`/`x` read-only views (was Z-only). |
| `hornlab_search/system/boundarylab/assemble.py` | `plan_assembly` accepts `dx_mm`/`dy_mm`; the draft transform is now a full 3-D translation. |
| `hornlab_search/system/reference.py` | `prepare(..., assembly_pose=...)`: the pose's `translation_mm` overrides a stray translation, the pose is recorded in the prepare record, and `min_clearance_m` comes from the pose. `solve` writes one record per run (§6.2). |
| `hornlab_search/system/cli.py` | `reference prepare --pose <json>`. |
| `tools/system/pose.py` | **new.** Resolve + validate a pose, write its JSON. |
| `tools/system/assembly_render.py` | **new.** Front/side/plan/perspective render of the compiled meshes. |
| `tools/system/placement_compare.py` | **new.** Per-excitation comparison of solved placements. |
| `tools/system/mesh_sensitivity.py` | **new.** Level-to-level complex-pressure comparison with amplitude gating, circular phase statistics and null reporting (§5.6). |
| `tests/system/test_assembly_pose.py` | **new.** 14 tests. |
| `tests/system/test_woofer_seed.py` | **+8 tests.** Frame-centre offsets, a true collision, the PASS→FAIL flip, the mm seam, the dz = 0 refusal and the screen replay. |
| `tests/system/test_reference_cli.py` | **+2 tests.** Separate per-run records; completed records never overwritten (§6.2). |
| `tests/system/test_clearance.py` | stage-gate expectation for a synthetic 3 mm overlap tightened from `UNPROVEN` to `VIOLATION` (the exact check proves the crossing); added a real-case exact replay. |

---

## 2. What the owner's photo means in world coordinates

Shared frame (unchanged from `contracts.AssemblyRanges`): **X** right, **Y** up, **Z**
toward the listener; the cabinet baffle is `z = 0`, the body occupies `z < 0`; the horn
mesh keeps its own origin (throat near `z = 0`, mouth at `+z`).

The photo is not a "flush baffle" and not a "whole horn above the box". It is:

> the horn is **seated on the cabinet top** with its mouth **overhanging the front face**,
> so the mouth circle overlaps the cabinet's front-view outline. The solids do not touch.

For the horn and cabinet actually in the store (`lecleach_rollback_1in_v6`, W×H×D =
233.3 × 233.3 × 142.9 mm; cabinet 320 × 500 × 360 mm):

| Quantity | Value |
|---|---|
| horn envelope (source frame) | x ±116.673, y ±116.673, z −3.000 … 139.874 mm |
| throat half-height at the rear plane | 15.67 mm (**this is what governs, not the mouth radius**) |
| derived pose | `translation_mm = (0, 268.674, 13.000)` |
| closest legal height without the frame constraint | `dy = 268.674` at `dz = 0` → seat clearance 3.000 mm |
| front-view overlap | 233.3 mm wide × **98.0 mm** tall, mouth lower lip 98 mm below the cabinet top line |
| solid clearance | **10.000 mm** exact, 1130 candidate triangles, box-vs-compiled-mesh verified |
| support | `unmodeled_cantilever` (see §5.3 — the real woofer frame forces the mouth forward) |

Renders (actual compiled BL geometry, not a schematic):
`p1_above_dz000.png`, `p2b_overhang_dz013_regenerated.png`, `p3_overhang_dz040.png`.
`p2_overhang_dz000.png` shows the pose that was later refused.

---

## 3. Corrected data flow

```
tools/system/pose.py  (horn mesh + cabinet + frame)
        │  resolve_pose(): policy dy, exact clearance, silhouette, hashes
        ▼
system_runs/poses_2026-11-22/<pose>.json           AssemblyPose (geometry_id)
        │  --pose
        ▼
hornlab-search system reference prepare --pose …
        │  reference.prepare(assembly_pose=…)
        ▼
stage_horn_project(translation_mm=[x,y,z], pose=…)
        │  BL runner (BL's own interpreter): MeshResource(translation_m=mm/1000)
        ▼
BL physical compiler → case.blab.json
        │
        ├── blab project validate           (graph/ports/regions)
        ├── exact horn-vs-cabinet + frame clearance gate → manifest.clearance
        ▼
reference solve (beat_cpu) → run/manifest.json + frequencies/*.npz
        ▼
bl_results.read_bl_headless_result → tools/system/placement_compare.py
        ▼
GUI /api/hw/mesh applies the same `points*scale + translation_mm/1000` (unchanged)
```

Before this pass the first arrow did not exist (`dy` was a screen column nobody staged,
`plan_assembly` only moved Z), and the last arrow's clearance gate refused the legal
arrangement.

---

## 4. Collision method, limits, proof

**Method.** BL's vented provider generates a rectangular enclosure whose manifold
`exterior.msh` is exactly the parameter box (verified at run time: bbox agreement ≤ 1e-6 m,
recorded as `compiled_exterior_matches_box: true`). So the mechanically meaningful test is
exact and closed-form per triangle:

* triangle ↔ box minimum distance = min over the triangle's 3 edges of
  `segment ↔ box` = min(2 endpoint→box, 12 segment→box-edge);
* any triangle edge that slab-clips the box ⇒ penetration ⇒ distance 0 (this is the case a
  naive vertex-face/edge-edge decomposition misses);
* containment: any horn vertex inside the solid ⇒ VIOLATION;
* optional extra solids (real woofer frame) are tested identically; the worst verdict wins;
* distance at or above the search cutoff is reported as a **lower bound** (`distance_exact:
  false`), which still proves any required gap ≤ cutoff.

**Limits.** Box solids only (exact for this provider; the stage refuses `UNPROVEN` if the
compiled exterior does not match the box). Horn must be closed (already enforced before
staging). Support brackets are not solids. Contact/gasket fits are not modelled.

**Proof (see `tests/system/test_assembly_pose.py`, `tests/system/test_clearance.py`):**

| Case | Verdict |
|---|---|
| real horn, `dy=268.674`, `dz=13` | **PASS**, 10.000 mm exact |
| real horn, `dy=268.674`, `dz=40` | **PASS**, 37.121 mm exact |
| real horn, `dy=369.673` (above) | **PASS**, ≥ 50 mm lower bound |
| real horn, `dz=0`, `dy=0` (old seam) | **VIOLATION**, 27 horn vertices inside the cabinet |
| real horn, `dz=0`, `dy=268.674` + real 315.2 mm frame | **VIOLATION**, 5 vertices inside the frame solid |
| triangle cutting the top face | intersecting, distance 0 |
| edge-to-edge 20 mm above the top | 20.000 mm exact |
| nesting (small solid in large) | VIOLATION |

Note: case `…8f425b7b` (P2b) and case `…4bbd22ee` (P2) were staged *before* the driver-frame
solid was added to the stage gate, so their manifests show the cabinet-only verdict. The
re-stage of P2 with the frame is the refusal below; P2b was re-checked with
`driver_frame` supplied and stays PASS at 10.000 mm.

The staged end-to-end refusal is on disk:
`system_runs/system/hf_overhang_refusal_2026-11-22/20261122T222833Z-assembly-51740-ccd102bf`
(`clearance.status = VIOLATION`, `nested = 5_horn_vertices_inside_extra_solid_0`,
`ok = false`).

**Decision (documented deviation).** The handoff suggested VTK/PyVista/trimesh. PyVista/VTK
exist only in **Boundary Lab's** venv; importing them into HornLab would couple two
environments. Because BL's enclosure is an exact box, the analytic method is both stronger
(no tolerance guessing) and dependency-free. The general mesh-mesh kernel was prototyped
and **discarded** after it failed a random-triangle exactness check — the discarded version
would have *understated* penetration.

---

## 5. Solves

### 5.1 Authorization
`SOLVE_AUTHORIZATION.md` — scoped to `beat_cpu`, these cases, 3/21 frequencies, no ranking.
The GPU lane was held by another agent's live search night throughout; **no GPU solve was
attempted** and the night's jobs were unaffected (queue advanced normally).

### 5.2 C1 smoke — PASS

Case `20261122T212619Z-assembly-32880-4bbd22ee` (the later-refused `dz=0` pose),
`request_smoke.json` (700/1000/1400 Hz), `beat_cpu`:
`status=complete`, 3/3 frequencies, ports `["vented/voltage","excitation:horn"]`, all
complex arrays finite, H/V polars 37 points, 5 probes. **87.6 s** wall.
No combined SPL was computed.

### 5.3 C2 placement control — three legal poses, 21 frequencies each

| label | case id | translation (mm) | support | exact clearance | state |
|---|---|---|---|---|---|
| **P1** above | `20261122T212531Z-assembly-21700-98b4310e` | (0, 369.673, 0) | seated | ≥ 50 mm (AABB-separated) | solved 21/21, 464 s |
| **P2b** overhang minimal | `20261122T221414Z-assembly-24200-0f425b7b` | (0, 268.674, 13) | cantilever | 10.000 mm | solved 21/21, 460 s |
| **P3** overhang forward | `20261122T212630Z-assembly-36576-7dee2536` | (0, 268.674, 40) | cantilever | 37.121 mm | solved 21/21, 458 s |
| (refused) P2 | `20261122T212619Z-assembly-32880-4bbd22ee` | (0, 268.674, 0) | — | cabinet-only PASS (staged before the frame solid existed); **VIOLATION** on re-stage with the real frame | smoke only, not a legal placement |

Common inputs: cabinet 320×500×360, wall 18 mm, BL demo moving diameter 200 mm, cone 40 mm,
surround 12 mm, port area 28.274 cm², port length 220 mm, NFR 0.12, driver y 100 mm, port y
−130 mm, horn `lecleach_rollback_1in_v6`, group `SD1D1001`, scale 1.0, `beat_cpu`, same 21
log-spaced frequencies 400–2500 Hz, same 2 m probes and project polars.

**Results** (`placement_compare.png`, `placement_compare.csv`, `placement_compare.json`).
Levels are per-excitation and **not** a calibrated SPL: horn is dB re 20 µPa per 1 m/s
prescribed normal velocity; woofer is dB re 20 µPa per 2.83 V.

| comparison | horn on-axis (700–1600 Hz RMS) | woofer on-axis (700–1600 Hz RMS) | horn/woofer relative phase, median |
|---|---|---|---|
| P2b − P1 (horn 101 mm down, 13 mm forward) | **0.59 dB** | **2.40 dB** | +33.4° |
| P3 − P2b (pure +27 mm forward) | **0.77 dB** | **1.30 dB** | +23.8° |

* The horn's own on-axis response is **essentially unchanged** by the overhang: the three
  curves lie on top of each other above 800 Hz (max |Δ| 1.54 dB for P2b−P1 over all 21
  frequencies).
* The woofer channel changes by 1.3–2.4 dB RMS. Part of that is real (the horn body is a
  scatterer whose position moved), but the largest single-frequency deltas (+5.9 dB at
  632 Hz, −8.2 dB at 2081 Hz) sit in **deep nulls** (60–68 dB vs 85 dB neighbours) and must
  not be read as robust. This is the known null-shift sensitivity, not a placement ranking.
* The horn-channel phase change grows smoothly with frequency (+10° at 400 Hz to +50° at
  2 kHz for P2b vs P1), i.e. a real propagation-path change of the assembled geometry.
* Vertical polar at 1 kHz over ±60°: horn spread 10.54 → 11.75 → 10.65 dB
  (P1 → P2b → P3); woofer spread 5.70 → 8.49 → 7.99 dB. The overhang slightly narrows the
  horn and visibly changes the woofer's vertical pattern.

**Not claimed:** combined SPL, sensitivity, crossover ranking, "time alignment", or any
statement that one placement is acoustically better. The two channels still have different,
uncalibrated drive references.

**Caveat added after C4 (§5.6, 2026-11-22):** these numbers were produced on one mesh
(30 mm / 9 mm). C4 shows the **horn-channel** differences are 10× above the mesh floor and
stand, but the C2 **woofer-channel** RMS differences (2.40 and 1.30 dB) are smaller than the
mesh-induced spread at the same pose (4.34 dB L0→L1, 2.72 dB L1→L2). Those woofer RMS values
are therefore an upper bound on any placement effect, not a measurement of it. The broadband
(median) level is mesh-stable, so a level comparison remains valid; the RMS comparison does not.

---

### 5.4 C3 source-shape control — same pose, same box, area-equivalent diaphragm

Case `20261122T230403Z-assembly-57912-77467bec`, 21 frequencies, `beat_cpu`, 462 s, 21/21.
Only `driver_diameter_m` changes (0.200 → **0.2605 m**, the area-equivalent round piston for
Sd = 533 cm², still a proxy) and, forced by BL's panel rule
(`|driver_y| + r + 3 ≤ H/2 − t`), `driver_y_m` 0.100 → 0.098. Cabinet, port, horn, pose
(`dz = 13`, `dy = 268.674`) and request are identical to P2b. Labelled
`APPROX_SOURCED / DEMO_PORT / DEMO_CONE`; the real 315.2 mm frame is **not** represented in
this case (see §5.5 and §6 item 6).

| comparison | horn on-axis 700–1600 Hz | woofer on-axis 700–1600 Hz | phase |
|---|---|---|---|
| C3 − P2b | **0.10 dB RMS** (max 0.28 dB) | **3.22 dB RMS**, +3.6 dB median | −1.7° median |

* The horn channel is effectively **independent of the woofer's moving surface** (0.1 dB),
  which is the expected decoupling and a useful sanity check on the two-excitation set-up.
* C3 is a **controlled source-geometry comparison with one forced mounting adjustment**
  (`driver_y` 100 → 98 mm), not a perfectly single-variable experiment. No result is
  attributed to area alone below the amplifier/port level.
* Area scaling, corrected (2026-11-22 directive). An ideal rigid circular piston on an
  infinite baffle has far-field on-axis pressure ∝ piston area `A = πd²/4`. Against
  Sd = 533 cm² the BL demo 200 mm piston is `A₀ = 0.031416 m²`, ratio **1.69659 → +4.59 dB**.
  At one frequency the volume velocity is `Sd·u` (velocity) or `Sd·x` (displacement), so
  **equal-velocity and equal-displacement limits coincide at +4.59 dB**. The earlier
  "+2.3 dB fixed-displacement limit" was the *diameter* ratio `20log₁₀(1.3025) = +2.30 dB`,
  which is not a pressure-scaling limit and is withdrawn. Analytic fixture:
  `c3_area_scaling_fixture.json` (`ANALYTIC_FIXTURE`, no BEM, no calibration).
* The simulated +3.6 dB median rise is **below** the ideal-piston area limit (+4.59 dB). The
  1.0 dB difference is the real box's loading/diffraction/port response and the non-piston
  diaphragm, **not** an efficiency or sensitivity measurement. The level therefore remains
  uncalibrated; nothing here ranks the two sources.
* Nulls at 527 / 632 / 1581 / 2081 Hz swing the point values (−3.0 to +20.3 dB) and are not
  a shape effect.
* Cross-over-region vertical spread grows from 8.49 to 10.31 dB for the larger diaphragm —
  a real directivity consequence of the source size.

`c3/placement_compare.{png,csv,json}`.

### 5.5 D2 cabinet reconciliation and selection

First pass (`cabinet_fit.json`, analytic): the smallest front that mounts the real 315.2 mm
frame with 3 mm clearance and 18 mm walls, driver on the baffle centre-line, port separated by
BL's own rule (`|driver_y − port_y| > r_move + r_port + 3`):

| Vb | smallest front | external depth then | smallest front with depth ≤ 380 mm |
|---|---|---|---|
| 42 L | 360 × 400 mm | 392 mm | 360 × 420 × 374 mm |
| 115 L | 360 × 400 mm | **1011 mm** | 540 × 700 × 380 mm |

The 320 × 500 × 360 research cabinet (42 L) is **14 mm too narrow** for the real frame, and a
115 L alignment in a 360 mm-wide tower becomes a metre-deep box.

Second pass (`d2_cabinet_reconciliation.json`, four BL generations + analytic rules). Three
volumes are reconciled per candidate — requested nominal Vb, empty internal rectangle, and the
OCC B-rep air volume BL actually generates (a CAD mass property, not a mesh integral, so it is
independent of mesh resolution):

| cand | external mm | internal rect L [computed] | BL air L [measured] | delta | f3 Hz | port ratio @40/63 | frame @ y=98 | min dy at dz=0 (→ spacing) | baffle step |
|---|---|---|---|---|---|---|---|---|---|
| A | 320 × 500 × 360 | 42.695 | **42.270** | −0.425 | 64.3 | **1.536 FLAG** | **FAIL** (−26.6 h, −18.6 w) | 268.674 → 170.674 | 341 Hz |
| B | 360 × 420 × 374 | 42.053 | **refused by BL** | — | — | — | **FAIL** (−66.6 h) | 228.674 → 130.674 | 303 Hz |
| C | 540 × 700 × 380 | 115.122 | **114.697** | −0.425 | 58.7 | 0.741 | PASS (+73.4 h, +91.4 w) | 368.674 → 270.674 | 202 Hz |
| D | 420 × 620 × 420 | 86.114 | **85.689** | −0.425 | 59.7 | 0.957 (marginal) | PASS (+33.4 h, +31.4 w) | 328.674 → 230.674 | 260 Hz |

* The 0.425 L delta is identical for every candidate: it is the driver cone + port solid
  displacement, so **BL's net volume is the empty rectangle minus the hardware**, exactly as
  intended. The nominal volumes in the grid are therefore close to, but not identical with, the
  delivered net volume.
* **B is refused by BL itself** (`Driver must fit inside the enclosure walls with 3 mm
  clearance` at the 260.5 mm moving diameter, `driver_y = 98 mm`) — that is the compact 42 L
  option gone before the real frame is even considered. **A fails the real frame** on both
  height (−26.6 mm) and width (−18.6 mm). Neither can host the 12PR300 as drawn.
* At the study's fixed port (220 mm, 28.27 cm²) the port tunes to ≈ 17–20 Hz, far below the
  box's natural rolloff, so f3 is set by the driver: C and D differ by **1.0 Hz** despite
  29 L. The large box buys port headroom and nothing else in extension.
* `rules.py`'s port-fit rule binds nowhere (237 mm required vs ≥ 324 mm internal depth).

**Selected baseline: D, 420 × 620 × 420 mm, ≈ 85.7 L net.** Why it serves the objective: it is
the smallest candidate that accepts the real frame with margin (36.4 mm height, 31.4 mm width at
`driver_y = 98`), keeps the horn/woofer centre spacing 40 mm smaller than C, shifts the baffle
step only 100 mm from the research cabinet (260 Hz vs 341 Hz, both well below the 700–1600 Hz
band under study), and costs 30 % less enclosure volume. Its LF extension is statistically
identical to C at the fixed port.

**Retained alternative: C, 540 × 700 × 380 mm (115 L).** It is the fallback if the port is
re-tuned upward for real LF extension: D's 0.957 velocity ratio leaves 4 % headroom, and any
higher tuning pushes it over. C's 0.741 ratio absorbs that. Choosing C now would trade 29 L,
120 mm of width and 40 mm of centre spacing for headroom the current experiment does not use.

**Port and tuning are explicitly not settled.** The 220 mm port is inherited from the research
config; a 35–45 Hz tuning study for D is a design task that belongs with the driver model, not
with this per-excitation comparison. It is listed as a non-blocking improvement.

### 5.6 C4 mesh sensitivity — what is safe to compare

Three mesh levels on the fixed P2b pose, 10 frequencies (700–1600 Hz, 1050/1100 bracketing the
1077 Hz null), `beat_cpu`, both excitation ports, 5 probes + H/V polars. Only BL's vented
generator `mesh_size_m` / `detail_size_m` vary: **the horn mesh is imported unchanged**
(sha256 `9b4057c2…9815d` and design hash `f04827bc5973` identical at all levels, geometry id
`ecfae5f89ebee429` identical). Cases and costs (`c4/levels.json`):

| level | mesh / detail mm | interior tets | exterior tris | air L | elapsed (10 freq) | case |
|---|---|---|---|---|---|---|
| L0 | 30 / 9.0 | 23,150 | 3,248 | 42.169 | 184 s | `20261123T011651Z-assembly-45740-4b3fbc6a` |
| L1 | 21 / 6.3 | 51,397 | 6,440 | 42.169 | 331 s | `20261123T012027Z-assembly-60396-c33304e6` |
| L2 | 15 / 4.5 | 110,106 | 11,962 | 42.169 | 750 s | `20261123T012101Z-assembly-49572-fbe5af54` |

`c4/mesh_sensitivity.{json,csv,png}`; amplitude gates: a sample must be within 20 dB of its own
frequency's peak and its frequency within 40 dB of the band peak, so deep nulls never enter the
ordinary RMS or phase statistics. Phase uses circular statistics.

| pair | channel | on-axis RMS | median | p90 | max | phase RMS |
|---|---|---|---|---|---|---|
| L0→L1 | horn | 0.059 dB | −0.002 | 0.108 | 0.108 | 0.33° |
| L1→L2 | horn | 0.058 dB | −0.004 | 0.112 | 0.140 | 0.27° |
| L0→L2 | horn | 0.110 dB | −0.009 | 0.213 | 0.248 | 0.33° |
| L0→L1 | woofer | **4.34 dB** | +0.038 | 6.95 | 10.16 | 59° |
| L1→L2 | woofer | **2.72 dB** | −0.012 | 3.23 | 8.09 | 46° |
| L0→L2 | woofer | **6.24 dB** | +0.054 | 9.90 | 14.69 | 51° |

Per-frequency on-axis woofer delta (dB): 700 −0.06, 800 +0.03, 900 +0.14, 1000 −0.06,
1050 −1.77, 1150 +0.08, 1250 +0.85, **1100 +9.37, 1400 −9.04, 1600 +14.69** (L0→L2). The horn's
worst on-axis delta over the band is 0.25 dB.

Both excitations are compared as **absolute complex pressure** (dB re 20 µPa per that
excitation's own reference, with its full phase), never normalised against each other.
Listening-window RMS over ±60° H / V: L0→L1 horn 0.082 / 0.083 dB, woofer 4.71 / 3.97 dB;
L1→L2 horn 0.067 / 0.088 dB, woofer 4.54 / 2.07 dB; L0→L2 horn 0.113 / 0.153 dB,
woofer 7.84 / 5.11 dB.

**Findings.**

1. **The horn channel is mesh-stable.** 0.06–0.11 dB RMS over a 2× refinement, ≤0.75 dB at the
   worst polar sample, <1° phase. Placement effects of the size seen in C2 (0.59–0.77 dB RMS on
   the horn channel) are therefore resolved above the numerical floor by roughly an order of
   magnitude.
2. **The woofer channel is broadband-stable but fine-structure-unstable.** The median level
   moves by ≤0.06 dB at every level pair, so a band level or a level *difference* is
   trustworthy. The RMS is dominated by three bins (1100, 1400, 1600 Hz) where the response has
   a null or peak whose depth depends on the mesh: nulls deepen from 5.8/6.4/10.0 dB at L0 to
   10.0/11.4/16.8 dB at L2. The C2 woofer differences (2.40 and 1.30 dB RMS) sit **inside** this
   mesh-induced spread and must not be read as placement effects.
3. **Label: `MESH_SENSITIVITY_CHECK`, not `CONVERGED`.** Three levels are present, but the
   level-to-level change does not fall with refinement in a way that supports an extrapolation
   (horn: flat at 0.06 dB; woofer: 4.34 → 2.72 dB, with the 1600 Hz bin getting worse, +6.60 →
   +8.09 dB). The 1077 Hz region is bracketed by 1050/1100 Hz samples; the null depth there
   moves by 1.8 dB between L0 and L2 while its location stays inside that bracket.
4. **Same-parameters reproducibility control.** The L0 case is an independent re-run of the
   earlier 21-frequency P2b case at 1000 Hz (identical parameters, 3,248 vs 3,256 exterior
   triangles because gmsh is not bit-reproducible). Agreement: **0.00026 dB and 0.00021°** on
   the woofer, 0.00004 dB on the horn. That is the floor for comparing two *runs at the same
   settings*; the larger numbers above are discretisation *bias*, which is common-mode for
   placements on the same cabinet.

### 5.6.1 L3 targeted probe — the woofer null depths do **not** converge

A fourth level (`mesh 10 mm / detail 3 mm`, 327,766 interior tets, 25,598 exterior triangles)
was run at 1000/1100/1400/1600 Hz only (`c4/levels_L3.json`, `c4/subset4/`). It is legal,
complete (4/4, both ports, finite) and the horn sha is again identical — but it **breaches the
480 s/frequency budget** at 3 of 4 frequencies (520.7 / 378.2 / 633.3 / 603.5 s). BL's own
`solve_s` is only 5–8 s; the wall time is **assembly**, and it grows faster than the element
count (23k→110k tets cost 184→750 s, 110k→328k tets cost 750→2137 s). So L3 is a one-off probe,
not a producible campaign level.

| on-axis woofer delta (dB) | 1000 | 1100 | 1400 | 1600 |
|---|---|---|---|---|
| L0→L1 | −0.04 | +10.16 | −6.34 | +6.60 |
| L1→L2 | −0.03 | −0.79 | −2.69 | +8.09 |
| L2→L3 | −0.02 | −0.38 | **+6.06** | **−7.63** |
| L0→L3 | −0.09 | +8.99 | −2.98 | +7.06 |

* 1000 Hz is converged to 0.09 dB over a 2.4× refinement. 1100 Hz is stable once the mesh is
  ≥21 mm (L1/L2/L3 agree within 0.8 dB; L0 is the outlier).
* **1400 and 1600 Hz oscillate**: the sign of the L2→L3 change is opposite to L1→L2, and the
  1400 Hz null depth runs 10.0 dB (L0) → 16.8 dB (L2) → **5.4 dB (L3)**. These are sharp
  null/peak bins: a small shift in the null frequency moves the fixed-frequency probe by
  several dB in either direction. No tested level resolves them, and refining further is not a
  remedy at this cost.
* The horn channel at the same four bins is again flat: L0→L3 deltas +0.01, +0.11, −0.12,
  +0.00 dB.

**Operational rule adopted:** placement comparisons report band medians/levels and the
amplitude-gated RMS; bins whose level is >20 dB below the local peak are reported only as null
locations/depths with their level-to-level spread, never as placement deltas. Production
placement runs use **L1 (21 mm / 6.3 mm)**, which is mesh-stable at 1100 Hz and costs 331 s per
10 frequencies.
5. **What the next placement campaign may use.** Horn channel: L1 is sufficient (L0 also fine
   for the horn alone). Woofer broadband level: L1 is sufficient. Woofer fine structure and
   null depth: **no tested level converges** (§5.6.1) — report them as null locations/depths
   with the L0–L3 spread, never as placement deltas. `MESH_SENSITIVITY_CHECK` stands.

## 6. Physics left open (unchanged priorities)

1. **Real driver frame vs the research cabinet** (numbers in §5.5). The 320×500×360 cabinet
   cannot host the real 12PR300, and the compact 360×420×374 candidate is refused by BL at the
   moving diameter. **Resolved by selecting D (420×620×420)**; the next campaign must not reuse
   the research cabinet.
2. **The seated pose needs a forward offset** because the horn throat protrudes 3 mm behind its
   own origin, i.e. into the woofer frame's swept plane. With `min_legal_dy_mm` the horn only
   overlaps the cabinet top for `dz < 3`; at `dz = 13` (10 mm gap) or `dz = 40` (37 mm gap) the
   pose is a **labelled cantilever** and the bracket/spacer is unmodelled.
3. ~~Woofer frame check in the seed screen is centred at y = 0~~ — **fixed** (§6.1 below).
4. **Source calibration** (D3/R1/R13): the horn channel is a 1 m/s surface velocity and the
   woofer 2.83 V. No physical combined SPL, no ranking. Unchanged.
5. **Observation standard** (D5/R5b): 2 m probes are diagnostic; no far-field convergence or
   CTA-2034 claim was made.
6. **Driver moving surface** (D1/R2): C3 covered the area-equivalent 260.5 mm proxy on the demo
   cabinet; the real 315.2 mm frame has **not** been in any solve — the pose geometry carries it
   as a solid, the acoustic source does not.
7. **Mesh/null convergence**: now measured (§5.6). Broadband stable, null depth not.
8. ~~`reference.solve` allows one record per case~~ — **fixed and tested** (§6.2 below).

### 6.1 Screen frame-centre fix (2026-11-22)

`placement_legality` now centres the woofer frame solid on the resolved mount height
(`woofer_frame_center_y_mm`, mm) instead of y = 0; `derive_min_center_spacing_mm` does the same
for `flush_baffle`; the screen passes BL's resolved `driver_y` after converting metres to
millimetres. Six unit tests cover positive/negative offsets, a legal arrangement, a true
horn/frame collision, and a PASS→FAIL flip under the old model; two screen-level tests pin the
mm seam and the resulting dz = 0 refusal.

**Consequence, stated plainly:** BL's panel validator uses the *moving* radius, so at its
maximum legal `driver_y` the real frame overhangs the cabinet top by
`r_frame − r_move ≈ 30.5 mm`. A horn seated on that top therefore collides at `dz = 0` and needs
`dz ≥ 13 mm` to clear. Replaying the six recorded screens against the fixed source flips
9/27, 42/126, 9/27, 9/27, 42/126, 42/126 kept rows to FAIL
(`stale_screens_after_frame_fix.json`); those screens are **superseded** and must not be reused
for a shortlist. No historical file was rewritten — the replay is a new record.

**Underlying defect left open:** the panel-fit gate itself still checks the moving diameter, not
the frame, so it accepts panels on which the real frame overhangs the baffle edge. Fixing that
changes a frozen boolean's behaviour and belongs to a separate pass.

### 6.2 Multi-run solve provenance

`reference.solve` writes `reference_solve_<run-dir>.json` for any run other than the default
`run/`, never overwrites an existing record, and pins request/project digests so a run is
replayable. Two new tests: two requests in one case produce two distinct, complete records;
a completed record is never overwritten. P2's 21-frequency record remains explicitly
`backfilled: true`.

---

## 7. Next bounded experiment

1. **N-series placement control on the selected D cabinet** (authorized under the same
   directive, CPU only, 10 frequencies from `request_c4_mesh_10f.json`, mesh L1 = 21/6.3 mm).
   All three poses were pre-resolved against the real horn mesh **and** the 315.2 mm frame
   (`resolve_pose(..., driver_frame={frame_od 315.2, depth 140.6, center_y 98})`), so no
   staging surprise:
   * **N1** — D, `(0, 328.674, 13)` → 10.440 mm exact clearance, `unmodeled_cantilever`;
   * **N2** — D, `(0, 328.674, 40)` → 37.121 mm exact clearance, `unmodeled_cantilever`;
   * **N3** — D, `(0, 334.674, 0)` → 8.963 mm exact clearance, `seated_on_cabinet_top`,
     92.0 mm front-view overhang.
   Note for N3: the closed-form minimum `dy = 328.674157` clears the cabinet by exactly
   3.0000 mm, and writing it rounded (`328.674`) is refused at 2.99984 mm; `334.674` is the
   robust value.
   Expected cost ≈ 3 × 330 s (L1 was 331 s for 10 frequencies) plus staging; abort on any
   frequency > 480 s. The woofer fine structure may be reported as null locations only.
2. **Woofer fine structure** stays out of any placement claim until a mesh level is found that
   stabilises the null depths (§5.6); the L3 probe is the first step.
3. **Crossover study, still per-excitation:** only after N-series; the assembled solve already
   carries the propagation phase, so a delay sweep must **not** add a second free-space
   `exp(±jkΔz)` correction.
4. **Not before calibration:** physical combined SPL, sensitivity, constrained system ranking.
5. **Can wait:** port re-tuning for D (35–45 Hz), cone depth/surround CAD, a frame-aware panel
   gate, regeneration of the superseded screens.

---

## 8. Files in this packet

| File | Content |
|---|---|
| `vented_overrides.json` | the exact BL vented-source overrides used by all cases |
| `vented_overrides_c3_area_equiv.json` | C3 overrides (0.2605 m moving diameter, driver_y 98 mm) |
| `request_smoke.json`, `request_placement.json` | solve request overlays |
| `cabinet_fit.json` | the 304 feasible real-frame fronts behind §5.5 |
| `SOLVE_AUTHORIZATION.md` | scoped authorization record |
| `staged_cases.json` | staged-case clearance summary |
| `p1_above_dz000.png`, `p2b_overhang_dz013_regenerated.png`, `p3_overhang_dz040.png` | compiled-geometry renders |
| `p2_overhang_dz000.png` | the refused pose (for comparison) |
| `placement_compare.{png,csv,json}` | P1 / P2b / P3 per-excitation comparison |
| `c3/placement_compare.{png,csv,json}` | P2b vs C3 source-shape comparison |
| `c3_area_scaling_fixture.json` | analytic piston area-scaling fixture behind §5.4 |
| `d2_cabinet_reconciliation.json`, `d2_numbers.md` | four-candidate volume/port/frame/LF numbers behind §5.5 |
| `request_c4_mesh_10f.json`, `request_c4_subset4.json` | C4 solve request overlays |
| `c4/overrides_L0.json` … `c4/overrides_L3.json` | one override file per mesh level |
| `c4/levels.json`, `c4/levels_L3.json` | per-level case ids, mesh stats, checks, elapsed |
| `c4/mesh_sensitivity.{json,csv,png}` | C4 mesh-sensitivity analysis (§5.6) |
| `c4/subset4/mesh_sensitivity.{json,csv,png}` | L3 targeted 4-frequency probe analysis (§5.6.1) |
| `stale_screens_after_frame_fix.json` | row-level replay of the six superseded screens (§6.1) |

---

## 9. Test and verification status (2026-11-22, end of pass)

**Scoped system tests.** `tests/system/test_woofer_seed.py` 26 passed;
`test_assembly_pose.py` 14 passed; `test_reference_cli.py` (offline) passed including the two new
provenance tests; lifecycle/data-export neighbours (`test_provenance`, `test_evidence_case`,
`test_import_results_hook`) 47 passed with 2 real-BL tests skipped by their gate.

**Full non-GPU suite.** `pytest -m "not slow and not gpu and not crosscheck" -n 6` →
**8 failed, 5,824 passed, 29 skipped in 24:06** (solo box, no solve running). None of the eight
touches this pass's files:

| failing test | status |
|---|---|
| `test_targets.py::test_from_dict_round_trips_example_targets[score_identities.yaml]` | known, other lane |
| `test_objective_v8.py::test_v8_is_registered_nowhere_and_never_changes_a_default` | known, other lane |
| `test_objective_v8.py::test_v8_key_set_is_v4_minus_load_plus_the_extras` | known, other lane |
| `test_queue_fable_scout40.py::test_scout40_jobs_are_budgeted_and_grouped` | known, other lane |
| `test_dataset_manifest.py::test_manifest_census_groups_and_provenance` | known, other lane |
| `test_b8_lanes_bounded_gui.py::test_study_modules_have_no_host_cleanup_or_process_kill_paths` | known, other lane |
| `test_tools_search_preflight.py::test_generated_history_fallback_reads_grid_knobs` | known, other lane |
| `test_dataset_store.py::test_append_500_typical_records_is_fast` (5.28 s vs a 5.0 s bound, **alone**) | new to the list, machine-speed assertion, file unmodified |

**Gated real-BL tests** (`HORNLAB_BL_REAL_TESTS=1`, 4 files): all passed except
`test_boundarylab_geometry.py::test_real_bl_generate_smoke`, which passes BL a 300×440×320 box
and BL's own default `driver_y = 100 mm`; BL 0.5.0 requires
`|y| + r + 3 < H/2 − t` → `100 + 100 + 3 = 203 ≥ 220 − 18 = 202`. One millimetre. The test
predates this pass and touches no file changed here; the same rule is what refused D2 candidate
B (with a 66.6 mm margin, not 1 mm). `test_real_bl_reference_report_on_recorded_smoke` skipped:
its recorded smoke path is not in this worktree.

**No commit was made.** The tree carries this pass's changes plus other lanes' uncommitted work,
as instructed.
