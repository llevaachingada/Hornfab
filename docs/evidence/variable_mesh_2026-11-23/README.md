# Variable mesh audit, regional grading and acoustic convergence

**Date of execution:** 2026-11-23 evening – 2026-11-24 early morning (local, EST)
**Canonical checkout:** `C:/Users/hunte/Hrns/hornlab-search`
**HEAD at start:** `626a7c65` (docs/renders); other lanes' uncommitted files were present and
left untouched. `hornlab_search/config.py`, `search/evaluate.py`, `objective/**` and
`metrics/**` were **not** edited by this pass.
**Mesher pin:** `jamescollinharky/hornlab-waveguide-mesher` @ `55da4f46d662d8dcd7a9f94a609eeea4009fcd62`
— installed `direct_url.json` matches; `hornlab_mesher 0.2.4`.
**GPU:** owned throughout by the live `v11_bo_day_core_2026-11-23` queue (the separate 12 kHz
screen orchestrator). No CUDA solve was launched by this pass. The acoustic A/B ran in the free
**CPU lane** with `beat_cpu`; no GPU lock was taken and no GPU numbers are claimed.

**Status:** PASS for the intended spatial grading on the formula families at factor 1.5, with
large margin inside the pre-declared acoustic criteria at 8, 10 and 12 kHz (the 12 kHz case is one leader).
Factor 2.0 also passes the acoustic criteria on the tested designs but is **not** adopted here
(see §10). The CAD/STEP route does not implement rear coarsening at all, and the point-grid route
saturates at factor 1.5 under its wall-clearance guard; both are documented, not hidden.

---

## 0. Scope, and what this pass does not do

In scope: the **spatial mesh-resolution system** — whether produced BEM meshes have the intended
regional triangle distribution, whether `mesh.rear_res_factor` changes the exterior as intended,
acoustic convergence of the tested designs, and conditional production defaults.

Out of scope (owner split): the separate **12 kHz SCREEN frequency-grid** and optimization-scoring
project. This pass used frozen explicit frequency lists only for mesh A/B; it changed no SCREEN
default, no objective, no score identity and no queue file.

---

## 1. Baseline checked against the code

| Item | Audit baseline | Found in the tree |
|---|---|---|
| `mesh/sizing.py` | `h_mouth = 1000 c/(epw f_max)`, `h_throat = h_mouth/2`, `h_rear = h_mouth` | confirmed (`sizing.py:40-46`) |
| `mesh/build.py::res_mm_for_spec` | `res["rear"] *= rear_res_factor` | confirmed (`build.py:311-317`) |
| `config.py` default | `rear_res_factor = 1.0` | confirmed, **not changed** (§10) |
| shipped modern configs | — | 144 configs already set `rear_res_factor: 1.5`; 8 study configs set 2.0/2.5 |
| mesher spatial fields | `configure_density()` inner/mouth/outer/rear | confirmed; `outer` in freestanding mode is a **constant** `rear_res_mm`, inner/mouth interpolate throat→mouth |
| installed mesher pin | `55da4f46…` | matches `direct_url.json` exactly |

The existence of the field is not evidence that the produced mesh has the gradient; §4 measures
the realised edges.

---

## 2. Method and labels

* **`MESH_REGIONS.csv`** — per-arm, per-region triangle count, unique vertices, area, edge-length
  p05/p25/p50/p75/p95/p99/max, area-weighted mean, aspect ratio, minimum angle, within-region
  dihedral p95, requested size, realised/requested, mapping residual.
* Regions on the formula/point-grid routes are assigned from the **producer's own point grid**
  (`mesh_meta.json.mesher_config` → `resolve_geometry`), not from tag guessing: nearest
  `inner_points` → `throat_transition` / `inner_bore` / `mouth_lip` by the producer grid's axial
  station; nearest `outer_points` → `outer_shell`; the flat face behind the throat plane →
  `rear_cap`; the ambiguous mouth-plane fill → `mouth_aperture`. Rows report the distance to the
  assigned surface; `unknown` is used rather than inventing a region.
* **`MESH_POLICY_AB.csv`** — the M0/M1/M2/M3/M4 mesh arms for one saved design per geometry class:
  triangle count, unique vertices, contract DOF estimate (`ceil(triangles × 0.51)`), build time,
  requested resolutions, region p50s.
* **`ACOUSTIC_CONVERGENCE.csv`** — same design, same frozen frequency list, same backend and
  observation spec, one mesh policy per arm. Raw complex pressures, on-axis SPL, H/V polar cuts,
  full-balloon DI, H/V beamwidth, complex throat impedance and bounded complex-pressure error.
* Labels: **[measured]** from a file/log produced by this run; **[inferred]** a conclusion from
  measured numbers; **PROVISIONAL** observed once, not a clean-state repeat.

### Frozen acoustic criteria (declared before the adoption comparison)

| metric | criterion |
|---|---|
| on-axis SPL, max |Δ| over the frozen band | **≤ 0.20 dB** |
| full-balloon DI, max |Δ| | **≤ 0.15 dB** |
| H or V beamwidth, max |Δ| | **≤ 1.0°** |
| normalised throat impedance, real part, max |Δ| | **≤ 0.03** |

These are engineering criteria for this pass, not universal standards. Deep nulls are judged on
complex pressure and bounded relative error, not unbounded dB differences.

---

## 3. Geometry coverage (six actual saved designs)

All are **quarter-domain** meshes (`quadrants: '1'`, symmetry planes yz+xz). No full-domain horn
is used to claim a quarter result; the symmetry is part of each identity.

A mounted/enclosure probe is included in the failures file (B5): the only WP12 enclosure brief
(`enclosure_1in`) produces 4726 triangles at factor 1.0, 1.5 and 2.0, so the rear factor is inert
on that topology and is recorded as not applied.

| class | design | family / generator | config / brief | source / mounting / symmetry | run dir | mesh (tris) |
|---|---|---|---|---|---|---|
| 1 smooth parametric OSSE | `09752eb2cd0a` | OSSE + rounded-rect morph | `cd_v11_2026-11-20/cd11__osse_morph.yaml` / v11 CD landscape 80x50 700 HF1440 | HF1440, 18 mm exit, 2°; free-standing; quarter `1` (yz+xz) | `runs/20261120T055336Z-screen-e23136` | 6721 |
| 2 rolled / fold R-OSSE | `68001408e339` | OSSE meridian fold | `cd11__osse_fold_warm.yaml` / same brief | HF1440, 18 mm exit, 2°; free-standing; quarter `1` | `runs/20261120T185520Z-verify-fec2a6` | 7387 |
| 3 ATH / ridged petal | `0dd357ce7e22` | OSSE + ATH H/V superformula | `cd11__ath_core_petal.yaml` / same brief | HF1440, 18 mm exit, 2°; free-standing; quarter `1` | `runs/20261120T063822Z-screen-a5a822` | 6828 |
| 4 point-grid FREEFORM | `94b93dc23478` | FREEFORM `rows` grid, rolled rectangle | `rolled_cd_2026-11-20/candidate.yaml` / room landscape v10 | HF1440, 18 mm exit, 2°; free-standing; quarter `1` | `runs/20261120T162620Z-screen-5a23c5` | 9323 |
| 5 CAD / STEP MEH | `03143899575f` | CAD `meh` T2 large multicell | `meh_2026-10-30/meh_t1.yaml` / MEH T1 | 1 in (12.7 mm), 0°; MEH 4-source quarter open shell; free-standing; quarter `1` | `runs/20261101T015657Z-screen-fc1d24` | 11979 |
| 6 large current leader | `01fa4b5c4806` | v11 home morph port (1.4 in) | `v11_bo_day_2026-11-23/home_morph_v11_port.yaml` / v11 CD open | HF1440, 18 mm exit, 2°; free-standing; quarter `1` | `runs/20261123T204048Z-screen-9d3630` | 8318 |

All baseline meshes are the **already-solved** meshes from those runs (response.npz present) except
class 3, whose stored design has no response (the run's later designs do); its mesh is identical in
policy and geometry to the class-1/6 formula route.

Selection: class 6 is a 2026-11-23 BO-day leader; classes 1-4 are the v11 fleet designs the
2026-11-22/23 rounds resume (the saved mesh is the production mesh for that exact design). Class 5
is the only CAD/MEH design in the tree with a solved 12 kHz response; no 2026-11-22/23 CAD design
exists. The mounted probe in FAILURES B5 uses the only WP12 enclosure brief. The acoustic A/B re-meshed and re-solved all
arms itself, so no stored row is compared across different grids.

---

## 4. Phase A — the produced mesh really is graded (formula routes)

Tool: `tools/analysis/mesh_region_audit.py` (new, read-only). Command:

```text
.venv\Scripts\python.exe tools\analysis\mesh_region_audit.py runs/20261120T055336Z-screen-e23136/designs/09752eb2cd0a --out text
```

Class 1, factor 1.5 **[measured]**, verbatim from `logs/class1_audit.txt` (UTF-16 decoded, LF):

```text
mesh: runs\20261120T055336Z-screen-e23136\designs\09752eb2cd0a\mesh.msh
triangles: 6721  vertices: 3499  dof_estimate: 3428  area: 0.15410 m2
policy: res_mm {"mouth": 7.145833333333333, "rear": 10.71875, "throat": 3.5729166666666665}  rear_res_factor: 1.50  epw: 6  fmax: 8000 Hz
region source: producer_geometry  (ok); unknown 0.00%
region               tris  verts   p50mm   p95mm   maxmm   hreq  r/req  asp95  dih95  res95
source                 58     40   3.053   4.254   4.426    3.6   0.84   2.38    0.3      -
throat_transition     140     87   3.553   3.961   4.696    3.7   0.88   2.25   10.3   0.49
inner_bore           4324   2282   6.118   7.056   9.343    6.2   0.99   2.08    8.3   2.92
mouth_lip             456    336   7.006   7.804   9.570    7.1   0.92   2.85   94.9   4.39
mouth_aperture          9     17   4.792   6.017   6.017    7.1   0.64   2.21    0.0      -
outer_shell          1713    964  10.709  11.953  15.131   10.7   0.98   2.36   84.5   3.48
rear_cap               21     18   8.106  11.066  11.205   10.7   0.74   2.21   87.4  20.07
```

Answers to the Phase A questions **[measured]**:

* **Is the throat actually finer?** Yes. Throat-transition p50 3.55 mm vs inner-bore p50 6.12 mm
  and mouth-lip 7.01 mm; the requested axial interpolation at the throat is 3.57 mm.
* **Does resolution vary along the horn?** Yes. Inner-bore p50 6.12 mm is the axial interpolation
  between throat (3.57) and mouth (7.15); the realised/requested p50 is 0.99.
* **Does exterior coarsening happen?** Yes, exactly as requested: outer-shell p50 7.15 → 10.71 →
  14.05 mm for factor 1.0 → 1.5 → 2.0, against requested rear 7.15 / 10.72 / 14.29 mm. Inner,
  throat and mouth p50s are unchanged to 0.01 mm across the factor arms.
* **Is the rear factor effective?** On the formula routes, yes; on CAD, no (§6/§11); on the
  point-grid route it saturates at 1.5 (§6/§11).
* **What happens at mouth rollbacks?** The mouth-lip region keeps the mouth resolution (p50 7.0 mm
  at factor 1.5) and shows a high within-region dihedral p95 (95°) on this sharp OSSE termination;
  the mesher's mouth-rim clearance cap is the relevant guard (metadata now recorded, §6). It does
  not collapse the lip; realised/requested is 0.92.
* **What happens at ridges/sharp curvature?** The ATH-petal class 3 (CSV) has inner-bore p50
  6.00 mm and throat 3.66 mm; the classification reports **0% unknown** after the producer-grid
  assignment. Its dihedral distribution is in `MESH_REGIONS.csv`; no ridge region is invented.
* **Are Gmsh boundary sizes overriding the field?** On the formula routes, no global override was
  observed: realised/requested p50 is 0.93–0.99 on the three inner regions. The throat-transition
  p95 is 3.96 mm (not 7+ mm) after the classifier stopped folding rear-cap triangles into it.
* **Are clearance guards preventing coarsening?** On the formula routes, not at these designs
  (outer p50 tracks the factor). On the thin-wall point-grid class, yes: the outer shell stops at
  ~8.05 mm even when factor 2.0 asks 14.3 mm (§6).
* **Does the CAD route implement this policy at all?** No. Factor 1.0/1.5/2.0 produce byte-identical
  triangle counts 11979/11979/11979 and the same unique-vertex count 6135; §6 records the proof and
  the honest record flag.

All six classes and all arms: `MESH_REGIONS.csv` (147 rows). Unknown fraction is 0.00% on the
formula classes after the classifier fix; the grid/CAD rows are tag-level because those routes do
not preserve per-triangle producer geometry (`region = tag_1_wall`), and say so.

Topology on the six audited baseline meshes: `mesh.topology.check_surface` reports **0 bad open
edges, 0 non-manifold edges and 0 near-coincident vertices** for every class (class 4 infers its
quarter flag from the run config because the grid route wrote no sidecar at capture time). The
same check now runs inside the audit tool and is reported in its JSON output.

---

## 5. Phase B — GUI mesh-density view

`GET /api/mesh/<run>/<hash>?density=1&f=<hz>` now returns, additively:

```text
density = {
  edge_mm: [max edge length per displayed triangle, mm],
  edge_basis: "solver_mesh" | "display_decimated",
  decimated: bool,
  stats: {n_tris_full, n_tris_shown, edge_mm_p05..max, dof_estimate, freq_hz, lambda_mm,
          h_over_lambda_p50/p95/max},
  policy: {res_mm, mesher_mesh, rear_res_factor, epw, curvature_npts, band_split},
  tags: {tag: count}, mesh_kind: "solved_mesh" | "stored_mesh", solved: bool
}
```

The dedicated 3D page now has a compact **Mesh density** group: a heatmap toggle, a frequency
input, a legend with exact min→max mm and h/λ, the policy line (res throat/mouth/rear, rear factor,
epw), full-vs-shown triangle counts and DOFs, and an explicit warning when the display is
decimated. It is lazy: the density payload is not requested until the user enables it; no GET
solves or re-meshes. The inline run-page viewer only adds a solved/stored-mesh label next to the
triangle count. Files: `gui/data.py` (payload), `gui/server.py` (query), `gui/static/app.js`,
`view3d.js`, `app.css` (UI).

Screenshots (`renders/`, produced by Playwright against the live local GUI):

* `mesh_density_smooth.png` — class 1 run, heatmap on (light theme). The dedicated route always
  renders the run's current best (`737be630b12e`, 6822 triangles), not the audited hash
  `09752eb2cd0a` (6721 triangles); same family/run, and the density path is hash-agnostic.
* `mesh_density_ridged.png` — class 3 (ATH petal) run, heatmap on (dark theme; current best
  `928733968160`, 6144 triangles).
* `mesh_density_smooth__375.png`, `mesh_density_ridged__375.png` — fresh 375 px viewport; the
  camera refits on narrow aspect ratios (distance +7.1% / +5.3% at 375 px; 1280 px framing is
  pixel-identical), so the whole horn is inside the canvas with margin. A first 375 shot was
  cropped at the left/bottom; that defect was fixed and the evidence regenerated.
* `mesh_density_decimation_warning_synthetic.png` — the required warning path with a synthetic
  >60k payload (no real solved design >60k tris was available); labelled `_synthetic`
* `browser_report.json` — 16 route/width/theme combinations; console errors 0, horizontal
  overflow 0. One `networkidle` post-screenshot reload timed out at 30 s and passed in an isolated
  rerun; it is a harness timing flake, not a page error.

`node --check` passed on both JS files; the GUI test files that cover `view3d`/`mesh_surface`/
`mirrorMesh` pass (re-run after the final UI edit). A focused rerun of the audit/policy/
provenance/grid/CAD/GUI tests after the last code edit reports **107 passed in 58.75 s**; the exact
output is `logs/tests.txt`.

---

## 6. Phase C — proven defects and the fixes landed in this pass

1. **Region classification folded the rear cap into `throat_transition`.** The rear disc at
   z = -6 mm is closer to the inner throat ring than to the outer shell, so a nearest-surface rule
   alone put 7 coarse cap triangles into the throat band and inflated its p95 to 7.9 mm. Fixed by
   deciding the rear plane before the inner/outer comparison; throat p95 is now 3.96 mm and the
   cap is its own row. This was a **diagnostic** defect, not a mesher defect.
2. **The mouth-plane fill was reported `unknown`.** On meshes without a tag-12 aperture, the
   ambiguous (inner≈outer) flat fill at the last producer station is the mouth aperture. Fixed by
   assigning that case to `mouth_aperture`; unknown is 0.00% on the formula classes.
3. **`mesh_meta.json` lost the mesher's own provenance.** `mesh/build.py` now writes an additive
   `mesher` block with `mouthRimClearance`, `outerWallClearance`, `quality`, facet/triangle
   counts, etc. Old files simply lack the key; mesh hashes and cache entries are unchanged.
4. **The GRID route wrote no `mesh_meta.json` at all.** `mesh/grid_build.py` now writes the same
   additive sidecar (`mesh_route: "grid"`, `grid.n_phi/n_s/wall_thickness/row_span`, `result`,
   `summary`, `rear_res_factor`, `mesher`). No cache key or mesh hash depends on the sidecar. The
   existing test that asserted "no meta" was updated to assert the new contract; `_grid_info` now
   finds the real area instead of `None` (new rows only).
5. **CAD ignored the rear factor but the record implied otherwise.** `mesh/step_build.py` now
   records `mesh_route: "cad"`, `rear_res_factor`, and `rear_res_policy {requested_rear_mm,
   applied_to_mesh: false, reason: "CAD route uses one global wall size; no outer/rear surface
   label"}`. This is the explicit "CAD/MEH remains unsupported" documentation the mandate asks for.
6. **GUI honesty.** `mesh_kind`/`solved` are now always present on the base mesh payload; the
   density payload distinguishes the solver mesh from a decimated display and carries the policy
   actually stored on disk.

Not fixed (deliberately): the CAD rear coarsening itself, and the point-grid clearance guard that
caps outer coarsening. A rear field on CAD would have to coarsen the acoustic bore with the same
single wall label, which would violate the "do not disable topology/clearance protections" rule;
the point-grid cap is the wall-self-intersection guard, not a bug.

---

## 7. Phase D — mesh arms (identical design, source, grid, solver per row)

Command pattern (one saved design per class):

```text
.venv\Scripts\python.exe tools\analysis\mesh_policy_ab.py --run <run> --design <hash> \
  --out <scratch>/<class> --arms 1.0:1,1.5:1,2.0:1,1.5:1.5,1.5:2
```

`FACTOR:EPW_MULTIPLIER`; the screen grid/f_max is the run's own. **[measured]**

| class | policy | tris | unique verts | DOF est. | ΔDOF vs 1.0 | inner p50 | throat p50 | mouth p50 | outer p50 |
|---|---|---|---|---|---|---|---|---|---|
| 1 OSSE | factor 1.0 | 8627 | 4474 | 4400 | — | 6.12 | 3.55 | 7.01 | 7.15 |
| | factor 1.5 | 6721 | 3499 | 3428 | **−22.09%** | 6.12 | 3.55 | 7.01 | 10.71 |
| | factor 2.0 | 6066 | 3161 | 3094 | **−29.68%** | 6.12 | 3.55 | 7.01 | 14.05 |
| 2 fold | factor 1.0 | 9469 | 4899 | 4830 | — | 6.12 | 3.66 | 6.93 | 7.15 |
| | factor 1.5 | 7387 | 3836 | 3768 | **−21.99%** | 6.12 | 3.66 | 6.93 | 10.70 |
| | factor 2.0 | 6634 | 3448 | 3384 | **−29.94%** | 6.12 | 3.66 | 6.93 | 14.05 |
| 3 ATH petal | factor 1.0 | 8792 | 4560 | 4484 | — | 6.00 | 3.66 | 7.00 | 7.15 |
| | factor 1.5 | 6828 | 3556 | 3483 | **−22.32%** | 6.00 | 3.66 | 7.00 | 10.72 |
| | factor 2.0 | 6175 | 3219 | 3150 | **−29.75%** | 6.00 | 3.66 | 7.00 | 14.14 |
| 4 grid | factor 1.0 | 10069 | 5187 | 5136 | — | tag-level | tag-level | tag-level | tag-level |
| | factor 1.5 | 9323 | 4810 | 4755 | **−7.42%** | — | — | — | ~8.05* |
| | factor 2.0 | 9321 | 4809 | 4754 | −7.44% | — | — | — | ~8.05* |
| 5 CAD MEH | factor 1.0 | 11979 | 6135 | 6110 | — | tag-level | tag-level | tag-level | tag-level |
| | factor 1.5 | 11979 | 6135 | 6110 | **0.00%** | — | — | — | — |
| | factor 2.0 | 11979 | 6135 | 6110 | 0.00% | — | — | — | — |
| 6 leader | factor 1.0 | 10660 | 5514 | 5437 | — | 5.94 | 3.64 | 7.10 | 7.15 |
| | factor 1.5 | 8318 | 4318 | 4243 | **−21.96%** | 5.94 | 3.64 | 7.10 | 10.69 |
| | factor 2.0 | 7477 | 3885 | 3814 | **−29.85%** | 5.94 | 3.64 | 7.10 | 14.05 |

\* Point-grid outer p50 was measured by the auxiliary producer-grid reconstruction (§6/§11), not by
the tag-only CSV row; the CSV records only `tag_1_wall` for that route. The 1.5 and 2.0 arms are
9323/9321 triangles: the clearance guard binds at ~1.5 and factor 2.0 buys nothing.

Finer reference arms (same policy, `epw` ×1.5 and ×2) are in `MESH_POLICY_AB.csv`; they fit the
formula classes' 24k DOF screen cap (7.6–16.7k contract DOF) and are used as the numerical
references below.

---

## 8. Phase E — acoustic convergence on a frozen grid

Commands (CPU lane; no GPU lock; one backend per run):

```text
.venv\Scripts\python.exe tools\analysis\mesh_acoustic_ab.py --run <run> --design <hash> \
  --out <scratch>/<case> --arms 1.0:1,1.5:1,2.0:1,1.5:1.5 --freqs "500,750,1125,1700,2550,3800,5700,6800,8000" \
  --reference-arm rear1.5_epw1.5
```

The 12 kHz case used `brief_v11cd_verify12k_meshpass.yaml` (this directory): a copy of the class-6
brief with `target.band_hi_hz: 12000` and `grid.screen_extra_hz` removed, plus

```text
--freqs "800,1200,1800,2700,4000,5600,7600,9800,12000"
```

All arms in a case share the exact solved frequencies, backend (`beat_cpu`), distance (10 m),
73 angles, 512-point balloon and the same design. The reference is the fine arm
`rear1.5_epw1.5` (epq 9), not a stored production row. `beat_cpu` is the same BEAT formulation on a
different device; it is a valid *relative* mesh comparison, not a production GPU timing.

### 8 kHz (three formula classes) — max |difference| vs the fine reference **[measured]**

| case | arm | DOF | on-axis dB | DI dB | BW H / V deg | z_real | p_h rel. |
|---|---|---|---|---|---|---|---|
| class 1 | 1.0 | 4474 | 0.0181 | 0.0121 | 0.065 / 0.077 | 0.00218 | 0.00426 |
| | 1.5 | 3499 | 0.0186 | 0.0126 | 0.067 / 0.075 | 0.00222 | 0.00427 |
| | 2.0 | 3161 | 0.0199 | 0.0141 | 0.075 / 0.079 | 0.00227 | 0.00420 |
| class 2 | 1.0 | 4899 | 0.0231 | 0.0101 | 0.070 / 0.097 | 0.00191 | 0.00455 |
| | 1.5 | 3836 | 0.0235 | 0.0118 | 0.071 / 0.101 | 0.00187 | 0.00454 |
| | 2.0 | 3448 | 0.0241 | 0.0164 | 0.073 / 0.105 | 0.00171 | 0.00449 |
| class 3 | 1.0 | 4560 | 0.0187 | 0.0146 | 0.153 / 0.063 | 0.00206 | 0.00435 |
| | 1.5 | 3556 | 0.0197 | 0.0157 | 0.155 / 0.068 | 0.00206 | 0.00434 |
| | 2.0 | 3219 | 0.0228 | 0.0183 | 0.162 / 0.082 | 0.00199 | 0.00424 |

All 27 comparisons are **far inside** the criteria: worst on-axis 0.0241 dB (limit 0.20), worst DI
0.0183 dB (0.15), worst beamwidth 0.162° (1.0), worst z_real 0.00227 (0.03). Complex on-axis
pressure p95 relative error ≤0.0046; balloon phase at low-amplitude directions is the only large
number (up to 44° on a near-null), while the bounded balloon complex error stays ≤0.0048. [measured]

### 10 kHz (class 1, scratch 10 kHz brief) — same metrics **[measured]**

| arm | DOF | on-axis dB | DI dB | BW H / V deg | z_real | p_h rel. |
|---|---|---|---|---|---|---|
| 1.0 | 6862 | 0.0125 | 0.0046 | 0.044 / 0.040 | 0.00132 | 0.00290 |
| 1.5 | 5344 | 0.0123 | 0.0053 | 0.050 / 0.038 | 0.00129 | 0.00288 |
| 2.0 | 4791 | 0.0126 | 0.0064 | 0.054 / 0.037 | 0.00122 | 0.00287 |

The 10 kHz arms are even closer to the reference than 8 kHz: all criteria are met by more than
15-fold (worst on-axis 0.0126 dB, DI 0.0064 dB, beamwidth 0.054°). The scratch brief is
`brief_v11cd_verify10k_meshpass.yaml`; the grid is 500−10000 Hz in nine points and the mesh
f_max is 10000 Hz. [measured]

### 12 kHz (class 6 leader, scratch 12 kHz brief) — same metrics **[measured]**

| arm | DOF | on-axis dB | DI dB | BW H / V deg | z_real | p_h rel. | polar H / V max dB |
|---|---|---|---|---|---|---|---|
| 1.0 | 8565 | 0.0222 | 0.0217 | 0.120 / 0.106 | 0.00167 | 0.00424 | 0.469 / 0.369 |
| 1.5 | 6702 | 0.0230 | 0.0224 | 0.122 / 0.106 | 0.00169 | 0.00428 | 0.478 / 0.357 |
| 2.0 | 6034 | 0.0256 | 0.0254 | 0.132 / 0.109 | 0.00171 | 0.00474 | 0.562 / 0.426 |

At 12 kHz the same arms remain inside every criterion by roughly six- to nine-fold. The
polar max difference is 0.36–0.56 dB at low-SPL off-axis angles; the on-axis and DI criteria are
the physically meaningful ones and are 0.02–0.03 dB.
 The reference is epq 9, not ground truth: a still-finer arm (epq 12) was not run because it
exceeds the CPU lane budget and the production cap; the claim is "no measurable change down to the
finest feasible reference", not "converged against an exact solution". [measured, with that caveat]

**Diagonal cuts (45°/225°) were extracted from the stored balloons** (`ACOUSTIC_CONVERGENCE.csv`
columns `diag_spl_*`, `diag_complex_rel_p95`). The diagonal SPL maximum is 0.2–4.0 dB, but every
maximum sits at a rear null (polar 156–180°, reference −42 to −59 dB), where the bounded complex
amplitude error is only 0.0043–0.0107; the diagonal SPL p95 is 0.10–0.53 dB. This is report-only,
not a pass/fail criterion: a dB difference at a deep null is not a meaningful accuracy claim
without the complex amplitude, which is why the bounded complex error is quoted alongside it.

**Reading.** The exterior coarsening changes the exterior mesh (outer p50 7.15→10.7→14.0 mm) but
not the acoustic field above the stated thresholds on these designs. The fine-reference arm itself
changes far more (it refines the inner bore too) and still moves on-axis by <0.03 dB, which means
the tested 8–12 kHz band is not mesh-limited at epq 6 for these smooth-to-ridged formula horns.
This is consistent with the earlier B1 result (mesh term ~0.008 J sd, ≤0.025 J per design): the
mesh sensitivity is small, and the rear factor is smaller than the uniform epq refinement.

---

## 9. Performance **[measured on the CPU lane]**

DOF reduction is the contract estimate; the solved `n_dof` equals unique vertices on every arm.

| class | DOF 1.0 → 1.5 | Δ | DOF 1.0 → 2.0 | Δ | CPU solve 1.0 → 1.5 (s) | Δ wall (mesh+solve) |
|---|---|---|---|---|---|---|
| 1 OSSE | 4474 → 3499 | −21.8% | 3161 | −29.3% | 129.4 → 81.0 | 31.0% |
| 2 fold | 4899 → 3836 | −21.7% | 3448 | −29.6% | 145.3 → 90.4 | 33.8% |
| 3 ATH | 4560 → 3556 | −22.0% | 3219 | −29.4% | 147.4 → 92.0 | 36.7% |
| 1 OSSE @10k | 6862 → 5344 | −22.1% | 4791 | −30.2% | 270.4 → 164.3 | 37.6% |
| 4 grid | 5187 → 4810 | −7.4% | 4809 | −7.4% | not solved | — |
| 5 CAD | 6135 → 6135 | 0.0% | 6135 | 0.0% | not solved | — |
| 6 leader @12k | 8565 → 6702 | −21.7% | 6034 | −29.5% | 453.5 → 270.0 | 43.1% |

* The **15% median DOF target** is met by the four formula classes at factor 1.5 (median −22.04%, range −21.96 to −22.32%)
  and exceeded at 2.0 (median −29.80%, range −29.68 to −29.94%). The point-grid class is at −7.4% and CAD at 0%; neither
  meets the target, and both are documented rather than averaged in.
* The **10% complete-candidate wall-time target** is met on the CPU lane for every solved formula
  class (31–43% including mesh build; solve-only 37–40%). GPU wall time was **not** measured: the
  12 kHz queue held the GPU for the whole pass. Because GPU solve time scales with DOF, a similar
  or larger reduction is [inferred], but it is not claimed as measured.
* Mesh-build seconds in `MESH_POLICY_AB.csv` are single observations with OS/gmsh warm-up noise
  (0.03–0.14 s here); do not read a policy slowdown from them. The solve is the dominant cost.
* One CPU worker host died mid-reference (`ConnectionResetError 10054`) and the harness re-warmed
  once and completed the arm; the retry is visible in the class-1 log and is not counted as a
  solver failure. No solve result was lost.

---

## 10. Adoption decision (see `ADOPTION_DECISION.md` for the contract)

* **Adopt factor 1.5 for new runs of the validated formula classes** (smooth OSSE, folded R-OSSE,
  ATH/ridged, large v11 leaders). It is already explicit in 144 shipped configs; the evidence now
  supports retaining it, not just the mesh-only DOF audit.
* **Do not adopt factor 2.0 as a default.** It passes the acoustic criteria on the tested designs
  (8k, 10k and the 12k leader), but it adds only ~8% DOF over 1.5, does nothing on the point-grid class,
  and the 10k/12k evidence is one design each on scratch briefs. It remains an opt-in screening choice.
* **Do not change `config.py`'s `rear_res_factor = 1.0` default.** Changing an absent-key default
  would change meshes for resumed/historical configs that omit the key and would break the
  "preserve historical absent-key semantics" rule. New-run templates/configs set 1.5 explicitly;
  old runs keep 1.0 and their hashes.
* **CAD/STEP:** retain the working policy; the rear factor is inert and now explicitly recorded as
  not applied. No universal rear factor is justified for CAD.
* **Point-grid:** keep 1.5 (safe, saturates); do not promise the 15% target there.

Rollback: set `mesh.rear_res_factor: 1.0` in the run config; the mesh cache key already carries a
`-rear<factor>` suffix for non-default factors, so 1.0 and 1.5 entries cannot collide. Historical
configs without the key are unchanged.

---

## 11. Failures, limitations, remaining risks

1. **Mounted/enclosure rear coarsening is unsupported** too: the enclosure walls use
   `enc_front_res_mm`/`enc_back_res_mm`, and the measured probe is 4726 triangles at 1.0/1.5/2.0.
   The record carries `mounting.rear_res_policy.applied_to_mesh = false`.
2. **CAD rear coarsening is unsupported** (byte-identical meshes at 1.0/1.5/2.0; the T2 MEH mesh
   is only valid to 5023 Hz at the requested 10 kHz per the mesher's own validation). This is a
   route limitation, not a regression. A future fix needs labelled outer/rear surfaces in the STEP
   contract; do not coarsen the single wall tag blindly.
3. **Point-grid factor 2.0 is inert** (9323→9321 triangles). The wall-clearance/self-intersection
   guard caps the shell at ~8.05 mm; disabling it is out of bounds. This is a *guard working*, not a
   bug, but it means the 15% target is not available on this class.
4. **The point-grid production screen cap (6000 DOF) refuses a 1.5× finer reference** (6647 DOF in
   an early attempt). The reference ladder for that class is therefore limited; the class was not
   used for the adoption decision.
5. **Acoustic reference is the finest feasible arm, not ground truth.** epq 9 at 12 kHz; epq 12
   was not run (CPU budget/cap). The convergence claim is relative to that reference.
6. **CPU backend, not GPU.** `beat_cpu` is the same BEAT formulation but a different device; the
   relative acoustic comparison is valid, GPU wall times are not measured.
7. **Balloon phase at near-nulls is misleading** (up to 60° for factor 2.0); the bounded complex
   amplitude error is ~1%. Deep-null topology was not used as a pass/fail criterion by itself.
8. **No real >60k-triangle design was available** for a decimation screenshot; the warning was
   verified with a synthetic payload and is clearly named `_synthetic`.
9. **Other lanes' uncommitted work was preserved.** No git mutation was performed; the designated
   integrator still owns the commit and the `config.py` decision.

---

## 12. Reproduction

```text
# 1. inspect one saved mesh, all regions
.venv\Scripts\python.exe tools\analysis\mesh_region_audit.py runs/20261120T055336Z-screen-e23136/designs/09752eb2cd0a --out text

# 2. rebuild the policy arms for one saved design (CPU, no solve)
.venv\Scripts\python.exe tools\analysis\mesh_policy_ab.py --run runs/20261120T055336Z-screen-e23136 \
  --design 09752eb2cd0a --out <scratch>/class1 --arms 1.0:1,1.5:1,2.0:1,1.5:1.5,1.5:2

# 3. frozen-grid acoustic A/B (CPU lane; do not run while a CUDA solve is live)
.venv\Scripts\python.exe tools\analysis\mesh_acoustic_ab.py --run runs/20261120T055336Z-screen-e23136 \
  --design 09752eb2cd0a --out <scratch>/class1_ac --backend beat_cpu \
  --arms 1.0:1,1.5:1,2.0:1,1.5:1.5 --freqs "500,750,1125,1700,2550,3800,5700,6800,8000" \
  --reference-arm rear1.5_epw1.5

# 4. GUI density payload (read-only)
.venv\Scripts\python.exe -c "from pathlib import Path; from hornlab_search.gui.data import mesh_surface_at; d=Path('runs/20261120T055336Z-screen-e23136'); print(mesh_surface_at(d/'designs/09752eb2cd0a', d, '09752eb2cd0a', density=True, freq_hz=12000)['density']['stats'])"

# 5. tests
.venv\Scripts\python.exe -m pytest tests\test_mesh_region_audit.py tests\test_mesh_policy_ab.py \
  tests\test_mesh_meta_provenance.py tests\test_mesh_build_grid.py tests\test_mesh_step_build.py \
  tests\test_gui.py -q -p no:cacheprovider
```

---

## 13. Files in this directory

| file | contents |
|---|---|
| `MESH_REGIONS.csv` | 147 region rows: 6 classes × arms, edge percentiles, requested/realised, quality, dihedral |
| `MESH_POLICY_AB.csv` | 26 arm rows: triangles, vertices, DOF estimate, build time, policy, region p50s |
| `ACOUSTIC_CONVERGENCE.csv` | 20 arm rows: frozen-grid on-axis, polars, DI, beamwidth, impedance, complex error |
| `PERFORMANCE.csv` | 34 rows: 26 mesh-policy arms plus the four 12 kHz and four 10 kHz acoustic arms (own mesh counts/times), DOF, CPU solve time, deltas |
| `FAILURES.md` | the proven defects, the unfixed route limits, and the evidence that each is what it is |
| `ADOPTION_DECISION.md` | the conditional decision, the integration contract, rollback |
| `brief_v11cd_verify12k_meshpass.yaml` | the frozen 12 kHz brief copy used by the class-6 acoustic arms |
| `brief_v11cd_verify10k_meshpass.yaml` | the frozen 10 kHz brief copy used by the class-1 acoustic arms |
| `logs/` | verbatim terminal output for the quoted audit block, the five acoustic runs (UTF-16 PowerShell redirects decoded for quote checks) and `tests.txt` (107 passed) |
| `renders/` | GUI density screenshots and the browser report |
