# Multicell horn research — compilation dossier (started 2026-10-25)

**Status: COMPILATION ONLY — deliberately NOT an implementation plan.** Owner request 2026-10-25
("start building a document for researching… adding info from the repo… planning the implementation
in terms of how to actually make this work"); owner ruling the same day: the multicell CATEGORY is
landed in the repo, the multicell PHYSICS troubleshooting is deferred, WP13 was deferred with
"don't know how necessary that is". This doc compiles what the repo has, what was planned before,
exactly how/why the first attempt failed, and the open questions the eventual plan must answer —
with every claim anchored. Append dated blocks; never rewrite history here.

---

## 1. What the repo already has (banked 2026-10-25; all committed on main)

| Piece | Path | State |
|---|---|---|
| CAD authoring tool | `tools/cad/multicell.py` (build123d 0.13.0, optional `cad` extra) | LANDED. Classic WE/Altec frusta-of-pyramids cells on `x = z·tan α_i` / `y = z·tan β_j` planes; thickened septa (≥ 1.5 mm, enforced) from `z_s`; exponential throat manifold; CLI + importable API; exports the labelled STEP via OCC `STYLED_ITEM` styles (build123d's own writer measurably CANNOT carry face labels — `SHELL_BASED_SURFACE_MODEL` is always `''`); round-trip proven 54/54 through the mesher's own parsers + a real gmsh import. |
| CAD→STEP→mesh route | `hornlab_search/mesh/step_build.py` | LANDED. recipe → STEP → gmsh OCC import → `driver`→tag 2 / `wall`→tag 1 via exact labels + `advanced_face_order_for_surfaces` → 2D mesh → the mesher's own `postprocess_mesh` + `mesh_frequency_validation` → metres `.msh` + our topology/bbox/tag/dof guards → `mesh_meta.json["cad"]` probe block (tool sha / recipe / step sha / face inventory / frequency/repair/topology reports). |
| Design-space ride | `design/families.py` — `FREEFORM.cad` 11-key recipe branch | LANDED. Strict validation (`CadParamsError`, prefix `FREEFORM.cad:`); odd `n_h`/`n_v` place a cell centred on axis (asserted by test). |
| CPU-arm solver knobs | `solve.{near_correction, near_correction_cutoff, near_correction_order, solve_precision}` | LANDED (M5B). Ride solve-spec `extra` when set; beat-only; accelerator refusals surfaced pre-import; absent = bit-for-bit. |
| Thin-wall GPU correction | hornlab-beat-bem fork branch `hornlab-search/wp17-cuda-near` @ `760a1ec` (THE PIN) | LANDED + GPU-VALIDATED (stage 1): near-singular correction allowed on the FUSED CUDA path with NO symmetry/ground; gated in Python config + Julia driver + sweep re-check; diagnostics prove the path (`near_correction_applied`, `near_correction_pair_count`, `assembly_path="fused_cuda"`); CPU thin-septum parity testset green; stage 2 (fused + per-image symmetry caches) designed-out until needed. |
| Mounting (for later enclosure-style work) | `brief.mounting` → the mesher's own keys (M6/WP12) | LANDED + measured (dofs +199 %/+107 % on two finalists, under the unchanged caps; enclosure = a different objective landscape). |
| Record honesty | `grid.available=false` + additive `cad` echo on cad rows (evaluate/ndjson/dataset) | LANDED. GUI cad chips + badges live (the GUI sessions' deferred-provenance/3D commits read the cad echo + cma logs). |
| Example + evidence | `examples/typologies/multicell_3x3.yaml`; `docs/evidence/M5B_WP14_WP16_WP17_2026-10-25.md` (byte-check `tools/evidence_bytecheck_m5b.py` 33/33); `runs/m5_wp14*/` artifacts (gitignored) | LANDED. The 3×3 builds deterministically (STEP byte-identical modulo the OCC `FILE_NAME` timestamp). |

## 2. What was planned previously (verbatim anchors)

- **WP14** (`docs/research/senior_pass_2026-10-24/04_IMPLEMENTATION_PLAN.md:474-480`):
  > Optional dependency `build123d` or `cadquery`. Script `tools/cad/multicell.py` builds the solid (N_h×N_v, septum
  > thickness ≥ 1.5 mm, septum start z_s) and exports STEP with named faces. … Mesh, then solve a 3×3 at f_max 4 kHz
  > on `beat_cpu` with `near_correction=True, solve_precision="double"` and on `beat_cuda`; report the CUDA vs CPU
  > difference. CUDA screens of multicells are allowed only if that difference is < 0.2 dB.
- **Report 2 §4/§5** (`docs/research/senior_pass_2026-10-24/02_TYPOLOGIES_AND_MULTICELL.md:119-152`):
  classic WE/Altec cells are frusta of pyramids sharing a virtual apex at the throat, mouths tiling a spherical cap;
  every septum lies on a plane through the apex; parameterization `N_h, N_v`, total cap angles, cell flare
  (exponential from a manifold throat), septum thickness `t`, septum start `z_s`; **septa on symmetry planes are
  acoustically free for symmetric drive** (a 4×4 quarter needs only one off-axis septum per direction per quadrant;
  an ODD cell count centres a cell on axis — the classic designs did this); the three solver traps: closed surfaces
  only (zero-thickness septa are NOT allowed for this solver), thin-gap quadrature (a septum's two faces sit ~1.5–3 mm
  apart, far below the element size — validate on `beat_cpu` with near correction before trusting CUDA), and the
  symmetry gift. Septa add `(N_h−1)+(N_v−1)` plates ×2 faces; 4×4 quarter ≈ +30–60 % dofs [inferred].
- **Multicell route ruling** (same doc :21-27): multicells are NOT expressible through FREEFORM formulas or the point
  grid ("the ducts are multiply connected"); the route is CAD → STEP → `hornlab_mesher.step_import`.
- **Typology grounding**: Le Cléac'h ETF 2010 covers multicell + sectoral horns (pp. 111–118) in the M4/M5 typology
  dossier chain (`research/typographies/WP9_WP9B_GROUNDING_2026-10-25.md` research basis).

## 3. How the first attempt failed — the full honest record (2026-10-25)

**What ran** (evidence `docs/evidence/M5B…§6` + the focal run dirs): the mandated comparison — the 3×3
multicell solved at 4 kHz BOTH ways on the same byte-identical mesh (4501 dofs, 12 freqs, 73-pt balloon):
CUDA arm J=172.566 (17.3 s) vs CPU near+double arm J=471.984 (314.1 s).
**The gate verdict: NOT ALLOWED** (bar 0.2 dB): on-axis max **11.28 dB**, DI max **14.59 dB**,
bw_v max **159.1°** (re-captured: `runs/m6_wp12/compare_focal.log`; sources `runs/20261025T112316Z-screen-b22f31`
vs `runs/20261025T112519Z-screen-c6b2d8`).

**Owner deferred the troubleshooting; the senior physics review (preserved) found two layered problems:**

1. **F1 — THE FIXTURE SOLVED THE WRONG OBJECT (dominant).** The CAD solid capped the mouth with a rigid
   `wall` face and mounted the driver as a flat disk on the REAR face (normal −z). The solver measures
   the field OUTSIDE the solid — so both arms computed *sound from a rear driver diffracting around a
   closed 346×218×300 mm multicell-shaped body*, never horn-mouth radiation. Independent proof:
   - throat impedance = a FREE UNBAFFLED DISK in both arms (the analytic (ka)²/4 curve matched within
     2–8 % from 500 Hz to 4 kHz — NO waveguide loading; the OSSE pipeline's own reference load is 1.02 ρc);
   - DI is NEGATIVE in both arms (0.42 → −7.5 vs 0.36 → −22.1) — a 4λ radiating aperture cannot have
     DI < 0; a rear source shadowed by its own body can;
   - the +z-side "directivity" that looked horn-like (CUDA: bw_v 73.6→20.9°, on-axis roll-off) is
     rim-diffraction fringe structure of the closed body, not mouth radiation.
   **Consequence: NO far-field metric of this fixture (in either arm, at any frequency) is evidence
   about the multicell AS A HORN — fix the mouth topology first.**
2. **The 4 kHz gate was unanswerable anyway.** The mesh's own validator sets the conservative global
   ceiling at **2891.68 Hz** (requested 4000); above that the two arms track interference fringes on
   10 %-class diverging discretizations. Per-severity: the driver patch alone resolves 6615 Hz; the
   walls within 200 mm of the driver only 3085 Hz. The bandwidth-restricted honest re-gate (≤2.9 kHz)
   on NON-threshold metrics (bw_v's 180° readings are −6.0206 dB threshold flips of valley depth, not
   physics — the 1287 Hz valley sits 1.05 dB from the rule's crossing) is the only gate this mesh can
   support — AFTER F1 is fixed.
3. **Attribution between the arms (ranked, from the review; UNRESOLVED — deferred):** #1 arm-A (CUDA)
   ran WITHOUT near-correction over the ~O(10⁵) near-coincident septum/second-ring pairs — the
   library's own refusal text warns this returns "a plausible wrong number rather than a crash" for
   exactly this geometry (the thin-gap trap from Report 2 §5 — WP17 stage 1, now landed and
   GPU-validated, exists precisely to fix this); #2 mesh under-resolution near the driver amplifying
   (a); #3 metric amplification (bw_v flips + dislope 597 vs 98); #4 FP32-vs-FP64 unlikely primary;
   #5 per-frequency-vs-single-call granularity unresolved on CPU (the isolation arm-D never ran; arm
   C (CPU plain) ran — its log exists under `runs/m5_wp14_focal/` — but conclusions were NOT drawn:
   the owner deferred at that point).

**What this means for the next attempt:** the trust gate (CUDA-vs-CPU < 0.2 dB) is only meaningful
AFTER (a) the geometry radiates from the mouth, and (b) the comparison runs in the mesh-valid band on
threshold-immune metrics. The thin-wall GPU correction (WP17) is ready for step (b)'s GPU arm.

## 4. The acoustic picture (compiled from the typology research; context for the eventual plan)

- **What classic multicells did:** WE/Altec/JBL multicellular horns split one throat into N_h×N_v
  rectangular cells whose mouths tile a curved cap; the cells' combined mouth behaves like a wider
  continuous aperture at low-mid frequencies, and the cells' separate mouths cause pattern narrowing +
  split-lobe behavior as each cell becomes directional on its own — the classic "beamy in-band, then
  lobing" trade. Odd cell counts centre a cell on the axis (classic practice; keeps the pattern
  symmetric). Sectoral (radial) horns are the 1-D ancestor.
- **The simulator-relevant physics:** septa walls are rigid; a septum ON a symmetry plane is
  free for symmetric drive (the model can use HALF/QUARTER domains — this is the dofs-gift;
  the M4 GRID work already proves the mesher's quadrant machinery); septa must have THICKNESS
  (this solver models only closed solids: rigid walls are meshed surfaces, zero-thickness internal
  walls can't exist), which creates thin air gaps between a septum's two faces — the source of the
  near-singular quadrature problem (corrected on CPU; fused-CUDA stage-1 correction now landed).
- **The mouth problem (the central open question — see §6):** for the solver, "the horn radiates"
  means the solution domain's boundary carries the OPEN aperture — this is exactly how the formula
  route models freestanding horns (wall-thickness shell with an open mouth), and how the enclosure
  route models a baffle + box (WP12 machinery). The CAD/STEP route's first pass instead exported a
  FULLY CLOSED solid — the fix space is in making the exported solid match one of the solver's open
  boundary semantics (or adding a mouth-boundary concept to the CAD route), while KEEPING the
  solver's closed-surface requirements satisfied wherever it needs closed surfaces.

## 5. Constraints ledger (everything the eventual plan must respect)

- Solver: exterior problem, closed input solids wherever required by the mesh writer's contract;
  thin 2 mm-class gaps need near-correction (CPU: landed; fused-CUDA stage 1: landed/validated);
  symmetry planes for free septa (stage-2 near caches NOT built — fused+symmetry+near is refused today);
  per-frequency CUDA calls; caps 5,000/7,000/8,900 (quarter) and 5,000/12,000/12,000 (fused) NEVER
  raised offline; enclosure machinery (WP12) is available if a mounted multicell is ever wanted.
- Costs measured so far: freestanding→enclosure doubled–tripled dofs on the tested finalists; septa
  add double-sided area (~58 % of the 3×3's mesh area is septum surfaces) → the near-pair count
  dominates CPU near-correction cost (the B arm: 257 s assembly at order 8; ~O(10⁵) pairs).
- Tooling: the label contract (`driver`/`wall`, exact strings, STYLED_ITEM carrier) is pinned and
  round-trip-proven; the STEP sha256 + CAD tool sha bind provenance end-to-end; the GUI surfaces the
  cad echo (chips/badges) already.
- Honest-metric discipline: bw_v/dislope flip near the −6.02 dB rule — report valley depths instead
  near thresholds; f11 = 7,914 Hz caveat on any 12 kHz claim; DI source=balloon only.

## 6. Open questions (for the eventual implementation plan — NOT decided here)

1. **Mouth treatment** (the F1 fix): which open-aperture semantics does the CAD route adopt —
   (a) export the air volume with the mouth faces ABSENT (open boundary like the freestanding
   wall-shell route), (b) an explicit mouth-boundary concept for the STEP route, or (c) route
   multicells through an enclosure/baffle-style topology (WP12 machinery exists)? What does each cost
   in solver-contract terms (closed vs open surfaces per stage)?
2. **Mesh sizing near septa**: how much local refinement do thin gaps need (Report-2's "expect local
   refinement near septum edges"), and can the near-pair count stay tractable on the GPU arm (order-8
   cost is measured ~80× a plain entry)?
3. **Symmetry exploitation**: 4×4 via quarter (free septa on mirrors) is the dofs gift — when does the
   stage-2 near-cache fork work become worth it (only for symmetric-drive with thin septa)?
4. **Which metrics gate the eventual trust claim** (valid-band on-axis/DI; valley depths instead of
   bw_v near thresholds), and at which f_max stages (2.9 kHz mesh-valid first; beyond needs the
   mesh rebuild + possibly the W7 density ladder)?
5. **Cell-shape parameterization for SEARCH** (if a multicell ever enters a campaign): which of
   Report-2 §5's knobs become search keys, with which bounds — and the brief that would drive it.
6. **Driver/exit reality**: real multicell drivers have per-exit phase plugs — WP16's J0 plug
   (landed, fused-path, per-face normal velocity) is the in-stack approximation; what its α range
   means physically for per-cell excitation is an open modeling question.

## 7. Deferred-evidence registry (all preserved, all gitignored-local)

| Item | Path |
|---|---|
| CUDA arm (closed-solid fixture) | `runs/20261025T112316Z-screen-b22f31` |
| CPU near+double arm | `runs/20261025T112519Z-screen-c6b2d8` |
| The compare tables (focal + M5B re-captures) | `runs/m6_fork/compare_focal.log`; `runs/m5_wp14_focal/` |
| The 3×3 STEP + mesh + cad probe | `runs/m5_wp14/`, `runs/m6_fork/cad_3x3_probe.txt` |
| Partial isolation arms (C ran, D config-only) | `runs/m5_wp14_focal/cfg_cpu_plain.yaml`, `cpu_plain.log`, `cfg_cpu_near_single.yaml` |
| The measurement-lane reports | this doc §3 + `docs/evidence/M5B_WP14_WP16_WP17_2026-10-25.md` §5-§6 |
| The senior physics review | `docs/ISSUES.md` deferred-WP14 block (full resume recipe) |

*Next owner decision recorded for WP12/WP13/multicell: WP12 DONE; WP13 OWNER-DEFERRED ("don't know
how necessary that is", 2026-10-25); multicell physics deferred (this doc = the compile-before-plan).*