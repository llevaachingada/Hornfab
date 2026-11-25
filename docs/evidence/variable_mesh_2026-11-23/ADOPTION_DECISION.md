# Adoption decision and integration contract

**Decision date:** 2026-11-24 (evidence executed 2026-11-23/24)
**Owner of the shared files:** the designated integrator; `hornlab_search/config.py` is owned by
the concurrent 12 kHz orchestrator and was **not edited** by this pass.

---

## 1. Decision

1. **Retain `mesh.rear_res_factor: 1.5` as the new-run policy for the validated formula classes**
   (smooth OSSE, folded R-OSSE, ATH/ridged/sculpted, large v11 leaders). It reduces unique-vertex
   DOF by **21.96–22.32%** on the four tested classes, with acoustic deviations far inside the
   pre-declared criteria at 8 kHz and on the tested 12 kHz leader. It is already explicit in 144
   shipped configs; this decision turns a mesh-only convention into an acoustically supported one.
2. **Do not promote factor 2.0 to a default.** It passes the acoustic criteria on the tested
   designs (including the 12 kHz leader), but it buys only ~8% more DOF than 1.5, is inert on the
   point-grid class, and its 12 kHz evidence is one design on a scratch brief. It stays an opt-in
   screening choice.
3. **Do not change `MeshSettings.rear_res_factor`'s 1.0 default in `config.py`.** An absent-key
   default change would alter meshes for resumed/historical configs that omit the key and would
   break the “preserve historical absent-key semantics” requirement. New-run configs/templates set
   `1.5` explicitly. If a future versioned default is wanted, it needs an explicit policy version,
   not a silent default flip.
4. **CAD/STEP/MEH:** keep the working policy; rear coarsening is inert and is now recorded as
   `rear_res_policy.applied_to_mesh = false`. Do not apply a universal rear factor to CAD.
5. **Point-grid/freeform:** keep 1.5 (safe, −7.4% DOF) but do not claim the 15% target; factor 2.0
   is blocked by the wall-clearance guard.

The acoustic criteria were frozen before the adoption comparison (README §2):
on-axis ≤0.20 dB, DI ≤0.15 dB, beamwidth ≤1.0°, normalised real throat impedance ≤0.03.

---

## 2. Evidence that supports the decision

| class | DOF 1.0 → 1.5 | Δ | 8 kHz acoustic max deviation | 12 kHz acoustic max deviation |
|---|---|---|---|---|
| 1 OSSE | 4474 → 3499 | −21.8% | 0.0186 dB on-axis, 0.0126 dB DI, 0.067° BW, 0.00222 z | not run |
| 2 fold | 4899 → 3836 | −21.7% | 0.0235 dB, 0.0118 dB DI, 0.071° BW, 0.00187 z | not run |
| 3 ATH | 4560 → 3556 | −22.0% | 0.0197 dB, 0.0157 dB DI, 0.155° BW, 0.00206 z | not run |
| 4 grid | 5187 → 4810 | −7.4% | not solved | not run |
| 5 CAD | 6135 → 6135 | 0.0% | not solved | not run |
| 6 leader | 8565 → 6702 | −21.7% | not run at 8k | 0.0230 dB, 0.0224 dB DI, 0.122° BW, 0.00169 z |

A 10 kHz class-1 case confirms the same direction: DOF 6862 → 5344 (−22.1%), worst on-axis
0.0126 dB, DI 0.0064 dB, beamwidth 0.054°, z_real 0.00132 (factor 1.5; all far inside the
criteria).

Complete rows, including factor 2.0 and the finer reference arms, are in
`ACOUSTIC_CONVERGENCE.csv`, `MESH_POLICY_AB.csv`, `PERFORMANCE.csv` and `MESH_REGIONS.csv`.
Performance target: the 15% median DOF target is met by the four formula classes; the 10% CPU
wall-time target is met at 31–43% (mesh + solve) on those classes. GPU wall time was not measured.

---

## 3. Integration contract (for the designated integrator)

### 3.1 Code already landed in this pass (mesh-owned files)

| file | change | hash impact |
|---|---|---|
| `tools/analysis/mesh_region_audit.py` | new read-only region audit | none |
| `tools/analysis/mesh_policy_ab.py` | new mesh-arm builder/auditor | none |
| `tools/analysis/mesh_acoustic_ab.py` | new frozen-grid acoustic A/B (CPU by default) | none |
| `hornlab_search/mesh/build.py` | additive `mesh_meta["mesher"]` provenance; `_mesher_provenance` helper | none (sidecar only) |
| `hornlab_search/mesh/grid_build.py` | additive `mesh_meta.json` for the GRID route | none (sidecar only) |
| `hornlab_search/mesh/step_build.py` | additive `mesh_route: "cad"` + `rear_res_policy` | none (sidecar only) |
| `hornlab_search/gui/data.py`, `gui/server.py` | density payload + always-on `mesh_kind`/`solved` | none |
| `hornlab_search/gui/static/{app.js,view3d.js,app.css}` | mesh-density UI | none |
| tests | `test_mesh_region_audit.py`, `test_mesh_policy_ab.py`, `test_mesh_meta_provenance.py`; updated `test_mesh_build_grid.py`, `test_mesh_step_build.py` | none |

### 3.2 The only configuration request (no `config.py` edit)

For a **new run** of a validated formula class, set this explicitly in the run config (or its
template/brief):

```yaml
mesh:
  rear_res_factor: 1.5
```

Do **not** change the dataclass default. Existing runs without the key keep loading as 1.0 and
keep their mesh hashes. The mesh cache key already appends `-rear<factor>` when the factor is not
1.0 (`mesh/build.py::mesh_cache_key`), so 1.0 and 1.5 cache entries cannot collide.

Identity note: `MeshSpec.hash()` deliberately does **not** include `rear_res_factor` (that would
rewrite every historical mesh hash). Distinctness is carried by the mesh **cache key** suffix
`-rear<factor>` and by `SolveSpec.extra["rear_res_factor"]` when the factor is not 1.0, so the
solve cache, failure markers and resume memo are distinct while absent/1.0 keeps every old hash
byte-identical. A bare `mesh_hash` is not the full mesh identity; pair it with
`mesh_meta.key`/`config_sha`.

If the owner later wants a global default, the safe form is an explicit versioned policy, e.g. a
new `mesh.policy_version: 2` that maps absent `rear_res_factor` to 1.5 for configs declaring that
version; this pass did **not** implement it, and it would need a resume/hash review.

### 3.3 CAD/MEH

No code change is requested beyond the recorded `rear_res_policy`. If a future STEP contract adds
separate `outer/rear` wall labels, the CAD route can apply a rear size field then; until that
exists, `rear_res_factor` is inert on this route and must not be used to claim CAD DOF savings.

### 3.4 Rollback

Set `mesh.rear_res_factor: 1.0` in the affected config. No code rollback is needed: the factor is a
config value; the sidecar additions are additive and ignored by old readers. For a code rollback,
revert the six files listed in §3.1; no installed package or `.venv` file was touched.

---

## 4. Files modified (this pass)

* `tools/analysis/mesh_region_audit.py` (new)
* `tools/analysis/mesh_policy_ab.py` (new)
* `tools/analysis/mesh_acoustic_ab.py` (new)
* `hornlab_search/mesh/build.py`
* `hornlab_search/mesh/grid_build.py`
* `hornlab_search/mesh/step_build.py`
* `hornlab_search/gui/data.py`
* `hornlab_search/gui/server.py`
* `hornlab_search/gui/static/app.js`
* `hornlab_search/gui/static/view3d.js`
* `hornlab_search/gui/static/app.css`
* `tests/test_mesh_region_audit.py` (new)
* `tests/test_mesh_policy_ab.py` (new)
* `tests/test_mesh_meta_provenance.py` (new)
* `tests/test_mesh_build_grid.py` (assertion updated for the new sidecar)
* `tests/test_mesh_build_grid_halfmodel.py`, `test_mesh_build_grid_rows.py`,
  `test_mesh_build_lecleach_rows.py` (same no-meta assertion updated)
* `tests/test_mesh_step_build.py` (new CAD policy test)
* `docs/evidence/variable_mesh_2026-11-23/*` (this evidence packet)

No git mutation was performed. The integrator stages only these hunks; other lanes' uncommitted
work was left untouched. `config.py`, `search/evaluate.py`, `objective/**`, `metrics/**` were not
edited.

Focused validation after the last code edit: **107 passed in 58.75 s** (`logs/tests.txt`);
`compileall` and `node --check` pass.

---

## 5. Remaining risks and open gates

* **GPU wall time is inferred, not measured.** A CUDA A/B on the same designs should be run when
  the 12 kHz queue releases the GPU, to confirm the CPU-lane time reduction and peak VRAM. The DOF
  reduction is measured and is the controlling quantity.
* **One 12 kHz design.** Broader 12 kHz coverage (the large leaders, the ridged class) is needed
  before factor 2.0 could ever be considered; factor 1.5 already has a large margin.
* **CAD frequency validity.** The T2 MEH is only valid to 5023 Hz by the mesher's own report at a
  10 kHz request; this is a separate CAD/MEH fidelity gate.
* **Point-grid reference ladder.** Raising the point-grid screen cap in a scratch config could
  give a fine reference, but it is not a production-valid arm; the class was excluded from
  adoption. If the owner wants a point-grid convergence claim, fund a CPU reference with a raised
  cap and label it as such.
* **B1 leaders.** The two B1 leaders that refuse epq 12 were not reopened; their mesh-floor claim
  remains outside this pass.

---

## 6. Senior handback (short form)

**What was implemented:** a read-only region audit from the producer grid; a mesh-policy A/B
builder; a frozen-grid acoustic A/B runner; additive mesher/grid/CAD provenance; an honest GUI
mesh-density view with decimation disclosure; focused tests.

**Did the variable mesh already work?** On the formula routes, yes: throat p50 3.55 mm vs bore 6.12
mm vs mouth 7.0 mm, outer shell exactly at the requested rear size. On CAD it is inert; on the
point-grid route it works at 1.5 and saturates at the wall-clearance guard.

**Failures corrected:** rear-cap misclassification, mouth-aperture misclassification, lost mesher
metadata, missing grid sidecar, and the CAD record implying a rear size was applied.

**Actual savings:** factor 1.5 −21.96…−22.32% DOF on the four formula classes; factor 2.0
−29.68…−29.94%; point-grid −7.42%; CAD 0%.

**Acoustic convergence:** 8 kHz worst deviations 0.0241 dB on-axis, 0.0183 dB DI, 0.162°
beamwidth, 0.00227 z (all ≪ criteria); 12 kHz leader 0.0230 dB, 0.0224 dB, 0.122°/0.106° BW,
0.00169 z, with 0.36–0.56 dB worst off-axis polar at low SPL.

**Runtime:** CPU-lane solve 37–40% faster at 1.5; complete candidate (mesh + solve) 31–43% faster.
GPU timing not measured because the 12 kHz queue held the GPU.

**Geometry classes that passed/failed:** passed: smooth OSSE, folded R-OSSE, ATH/ridged, large v11
leader (8 kHz; leader also 12 kHz). Passed-with-small-savings: point-grid (7.4%, 1.5 only).
Not applicable: CAD/MEH (rear factor inert; mesh validity 5023 Hz at a 10 kHz request).

**Defaults now appropriate:** 1.5 explicit for new formula-class runs (already the fleet
convention); 2.0 opt-in only; CAD unchanged; point-grid 1.5. No `config.py` default change.

**Integration needs:** the integrator should land the six mesh/GUI code hunks and the evidence
packet; no config edit is required. If a global default is desired, implement a versioned policy
rather than flipping the absent-key default.
