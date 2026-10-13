# 04 TASK DESIGN AND MESH

**Wave 1, parallel with 05, 06 and 07. No shared files.**

Owner of: `hornlab_search/design/space.py`, `families.py`, `custom.py`, `mesh/sizing.py`, `mesh/build.py`, `tests/test_design_*.py`, `tests/test_mesh_*.py`
Reads: `01_CONTRACTS.md`, `TOOLCHAIN.md`
Imports: `numpy`, `hornlab_search.types`, `hornlab_search.constants`, and `hornlab_mesher`

You turn a `Design` into a `.msh` on disk. **You do not write a mesher.** `hornlab_mesher` does the geometry and the meshing; you build its config dict, convert our frequency-based sizing into its millimetre resolution keys, enforce the dof budget, and validate what comes back.

If you find yourself writing a profile curve, a superellipse, a loft, a triangulation or a gmsh writer, stop: all five exist in `hornlab_mesher` and your job is to call it correctly.

---

## Step 0: Discovery, before any code

Twenty minutes that saves a day. Paste the results.

```powershell
$P = ".\.venv\Scripts\python.exe"
& $P -m pip show -f hornlab-waveguide-mesher
& $P -c "import hornlab_mesher as m; print([n for n in dir(m) if not n.startswith('_')])"
& $P -c "from hornlab_mesher import tags; print({k: v for k, v in vars(tags).items() if not k.startswith('_')})"
```

Then read, on disk in the installed package:

- `docs/config-schema.md` — the authoritative key list. `01_CONTRACTS.md` section 5 summarizes it; **the file on disk wins.**
- `docs/public-api.md` — which names are stable API.
- `hornlab_mesher/tags.py` — confirm the nine tags.
- the `examples/` directory — at least one working TOML per family.

Report:

1. The exact signature of `build_from_config` and `write_step_from_config`.
2. The nine tag numbers and names, confirming `01_CONTRACTS.md`.
3. Which exception type a bad config raises, and what its message looks like. You will be catching it.
4. For a shipped OSSE example: does the written `.msh` contain coordinates of order **metres** or **millimetres**? Print the bounding box. This confirms `scale_to_metres: true` and therefore `mesh_scale=1.0`.
5. Any config key in `docs/config-schema.md` that `01_CONTRACTS.md` section 5 does not list.
6. Whether a `Design` can legally carry `quadrants` as a param, or whether it belongs only to `MeshSpec`. (Per contracts it belongs to `MeshSpec`.)

---

## Build

### 1. `design/families.py`

One table per family of legal keys, their type, and a plausibility range. Nothing more clever than that.

```python
FAMILY_KEYS: dict[str, dict[str, KeySpec]] = {
    "OSSE":     {...},
    "R-OSSE":   {...},
    "ICW":      {...},
    "FREEFORM": {...},
}

@dataclass(frozen=True)
class KeySpec:
    kind: type            # float | int | str | list
    lo: float | None
    hi: float | None
    note: str = ""


def validate(design: Design) -> None:
    """Raise GeometryInvalidError naming the offending key. No guessing:
    a key not in the family's table is rejected, not passed through."""


def to_mesher_config(design: Design, mesh: MeshSpec,
                     res_mm: dict, out_path: Path) -> dict:
    """Build the dict hornlab_mesher.build_from_config consumes."""
```

Populate the tables from `01_CONTRACTS.md` section 5 and the on-disk schema. Known constraints to encode, from the schema:

- R-OSSE does **not** accept `rot_deg` or an explicit `L_mm`.
- ICW rejects OSSE/R-OSSE shape keys at top level, rejects `zmap` and `z_map_points`, and is TOML/JSON/dict only.
- `n` must be `> 0` while `s != 0`; `q` must be `> 0` while `s != 0`.
- `s1` is finite in 0 to 10 with units mm/degree; `s2` is finite in 0 to 10 with units 1/mm.
- FREEFORM needs `profileH` and `profileV`, each 2 to 64 `[z, r]` or `[z, r, angleDeg]` rows with **z strictly increasing**, mm; `crossSections` has 2 to 32 stations with `t` in `[0, 1]`; `superellipse` exponent is in `[2, 16]`.
- Per-azimuth throat stretch raises `ConfigError`. Catch it and re-raise as `GeometryInvalidError` with a message pointing at `design/custom.py`.

`to_mesher_config` always sets, regardless of family:

```python
cfg = {
    "formula": design.family,
    "mode": "freestanding",              # or from design.params if present
    **design.params,
    "quadrants": mesh.quadrants,
    "throat_res_mm": res_mm["throat"],
    "mouth_res_mm":  res_mm["mouth"],
    "rear_res_mm":   res_mm["rear"],
    "max_triangles": mesh.max_triangles,
    "allow_large_mesh": mesh.allow_large_mesh,   # False
    "scale_to_metres": True,                     # EXPLICIT, never implicit
    "output": {"path": str(out_path)},
}
```

**`scale_to_metres` is written explicitly even though it is the default.** It is the single value that, if it ever changes upstream, silently produces a 1000x horn.

### 2. `design/space.py`

`DesignSpace` per `01_CONTRACTS.md` section 5, with:

```python
def keys(self) -> list[str]:      # searchable, SORTED ALPHABETICALLY
def normalize(self, d: Design) -> np.ndarray      # -> [0,1]^k, clips, warns
def denormalize(self, x: np.ndarray) -> Design    # clips x first
def from_config(cfg) -> DesignSpace               # builds from Config.bounds_raw
```

Alphabetical, not YAML order, so that reordering the YAML cannot silently permute the CMA-ES vector and invalidate a resumed run. `log=True` bounds require `lo > 0` and map through `log10`.

### 3. `design/custom.py`

**Empty in phase 1.** Create the file with a module docstring that says what it is for, and one `NotImplementedError` stub:

```python
"""Geometry beyond what hornlab_mesher supports.

The mesher refuses per-azimuth throat stretch ("not supported yet") and has no
low-order azimuthal series over the flare parameters. That gap is the geometry
novelty opening for this project; see 12_RESEARCH_BASIS.md section 8.

A future family implemented here must produce a gmsh .msh in METRES with the
physical tags from hornlab_mesher.tags, so that solve/ needs no changes.
"""

def build_custom(design: Design, mesh: MeshSpec, res_mm: dict, out: Path):
    raise NotImplementedError("phase 2: see 11_PHASE2_SURROGATE.md forks")
```

That stub is the whole point: adding a family later is a new file and a table row, not a refactor.

### 4. `mesh/sizing.py`

```python
QUADRANT_FACTOR = {"1234": 1, "12": 2, "14": 2, "1": 4}
SYMMETRY_PLANE  = {"1234": None, "12": "xz", "14": "yz", "1": "yz+xz"}


def res_mm_for(epw: float, f_max_hz: float) -> dict:
    """res = 1000 * C_AIR / (epw * f_max). Returns
    {'throat': res/2, 'mouth': res, 'rear': res}."""


def max_triangles_for(dof_cap: int, quadrants: str,
                      dof_per_triangle: float, slack: float = 1.15) -> int:
    """FULL-DOMAIN-EQUIVALENT ceiling:
       tri_solved = dof_cap / dof_per_triangle
       tri_full   = tri_solved * QUADRANT_FACTOR[quadrants]
       return ceil(tri_full * slack)"""


def estimate_dofs(n_triangles: int, quadrants: str,
                  dof_per_triangle: float) -> int:
    """n_triangles is what the .msh contains (already reduced).
    Returns the estimated solver dof count."""


def f_max_for_dofs(dof_cap, area_m2, epw, quadrants, dof_per_triangle) -> float:
    """Inverse of the sizing chain. Used by --dry-run and by the report to
    say what frequency a budget actually buys."""
```

`dof_per_triangle` comes from `TOOLCHAIN.md`'s M1 calibration, through the config. **Do not hardcode 0.5.** It is the initial guess only, and the config carries the measured value.

`SYMMETRY_PLANE` is the only place the quadrants-to-flag mapping exists. `solve/` imports it from here. One source, so the two can never drift apart. This is one of the three silent killers named in `00_ORCHESTRATOR.md`.

### 5. `mesh/build.py`

```python
def build_mesh(design: Design, mesh: MeshSpec, cfg, out_dir: Path) -> MeshResult:
    """
    1. families.validate(design)
    2. res = sizing.res_mm_for(mesh.epw, mesh.f_max_hz)
    3. mcfg = families.to_mesher_config(design, mesh, res, out_dir/"mesh.msh")
    4. log mcfg at DEBUG, as a copy-pasteable repr
    5. check the cache by (design.hash(), mesh.hash()); return on hit
    6. hornlab_mesher.build_from_config(mcfg, path)
         - its ConfigError -> GeometryInvalidError, message preserved verbatim
    7. read back: triangle count, bounding box, surface area, tags present
    8. GUARD: bbox extent must be in [0.02, 5.0] m. Otherwise raise a hard
       error naming mesh_scale. This is a units bug, not a bad candidate.
    9. estimate dofs; raise MeshTooLargeError if over the cap
   10. return MeshResult, with symmetry_plane from sizing.SYMMETRY_PLANE
    """
```

Step 8 deserves its own emphasis. The mesher writes metres and the solver's README example uses millimetres. A wrong `mesh_scale` gives a 1000x horn that solves cleanly and produces a smooth, confident, completely wrong polar. There is no other check in the system that catches it.

Also write a small reader so you are not depending on a mesh library:

```python
def read_msh_summary(path: Path) -> dict:
    """{'n_triangles', 'n_nodes', 'bbox_m', 'area_m2', 'tags': {id: count}}
    Parses the gmsh ASCII $Nodes and $Elements blocks. Read only. We never
    write a .msh."""
```

Surface area from the triangles via the cross-product formula; it is four lines and the report wants it.

### 6. STEP export, free and worth having

`hornlab_mesher.write_step_from_config` writes a **closed B-rep solid in millimetres**, with the driver membrane removed and symmetry-reduced designs expanded to all four quadrants. Expose it:

```python
def export_step(design: Design, mesh: MeshSpec, cfg, out: Path) -> tuple[Path, dict]:
    """Returns (path, info) where info has .body and .volume_mm3."""
```

This is the Rhino and Fusion path, answered better than the previous plan's: a STEP solid imports directly, and `volume_mm3` times the filament density gives a print-cost estimate the report can print. One function, large practical payoff.

---

## Tests

**Offline, must pass with nothing installed** (`tests/test_design_space.py`, `test_design_families.py`, `test_mesh_sizing.py`):

1. `keys()` is alphabetical and unchanged when the YAML bounds dict is reordered.
2. `denormalize(normalize(d)) == d` to 1e-9 for the seed and 200 random in-bounds designs, for all four families' example configs.
3. `normalize` clips an out-of-bounds seed, warns, does not raise.
4. `log=True` with `lo <= 0` raises at construction, not at first use.
5. `validate` rejects an unknown key, naming it in the message.
6. `validate` rejects R-OSSE with `rot_deg`, and ICW with an OSSE shape key.
7. `validate` rejects FREEFORM with non-increasing `z` in `profileH`, and with a superellipse exponent of 1.5 or 20.
8. `to_mesher_config` always emits `scale_to_metres: True`, `allow_large_mesh: False`, and the three `*_res_mm` keys.
9. `res_mm_for(6.0, 10000)` equals `1000*343/(6*10000) = 5.7167` mm for mouth, half that for throat. Assert to 1e-9.
10. `SYMMETRY_PLANE` and `QUADRANT_FACTOR` have identical key sets, and `"1" -> ("yz+xz", 4)`.
11. `max_triangles_for(8000, "1", 0.5, 1.15)` equals `ceil(8000/0.5*4*1.15) = 73600`.
12. `f_max_for_dofs` is the numeric inverse of the sizing chain to 0.5%.
13. `Design.hash()` is unchanged by reordering `params`, and changes when any value changes in the ninth decimal place.

**Mesher-gated** (`@requires_mesher`, `tests/test_mesh_build.py`):

14. `build_mesh` on each of the four example seeds succeeds and returns a `MeshResult`.
15. The written `.msh` bounding box is in `[0.02, 5.0]` m. **Then deliberately pass `scale_to_metres: False` and assert the guard raises.** A guard never shown to fire is not a guard.
16. All expected physical tags are present, with `SD1D1001` (the source) non-empty.
17. Triangle count scales roughly as `f_max^2`: build at 3, 6 and 12 kHz and assert the ratios are within 25% of 1 : 4 : 16.
18. `MeshTooLargeError` is raised, and **no mesh is written**, when `f_max` is set high enough to exceed the cap. Assert the file does not exist and the call returns in under 100 ms.
19. `quadrants="1"` produces roughly a quarter of the triangles of `quadrants="1234"` for the same design and resolution, within 20%.
20. **Determinism:** `build_mesh` twice on the same design and spec gives identical triangle counts and identical bounding boxes. If gmsh is not deterministic here, that is a finding for `NOTES_FOR_SENIOR.md` and it breaks the cache, so report the magnitude.
21. `export_step` produces a file and an `info.volume_mm3` greater than zero.
22. Cache hit: a second `build_mesh` call with the same hashes does not invoke the mesher. Assert by monkeypatching `build_from_config` to raise.

---

## Checkpoint CP-2

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_design_space.py tests/test_design_families.py tests/test_mesh_sizing.py -v
.\.venv\Scripts\python.exe -m pytest tests/test_mesh_build.py -v
```

Paste both in full, plus:

1. **The step-0 discovery report**, all six numbered answers.
2. A table, for `examples/osse_baseline.yaml` at `f_max` of 3, 6, 9 and 12 kHz: `res_mm`, triangles, estimated dofs, bbox, surface area, mesh seconds.
3. The same table for `quadrants` `"1234"` and `"1"` side by side.
4. The first 30 lines of one written `.msh`, so the format and the units are visible.
5. The `read_msh_summary` output for the seed, showing the tag histogram.

**CP-2 passes when:** all 22 tests pass, tests 15 and 18 actually raise, and the bounding box in the pasted `.msh` header is unmistakably in metres.

### CP-2a: what the senior agent checks

From the pasted tables, not from the code:

- **The bounding box is metres.** A seed horn 260 mm long must show a z extent near 0.26, not 260.
- **`quadrants="1"` really is a quarter.** If the quarter mesh is not roughly a quarter of the triangles, the quadrant key is not doing what we think, and task 02's M6 symmetry test should be re-read.
- **Triangle count scales as `f_max^2`.** If it scales linearly, the resolution keys are not controlling element size the way we assume, and every dof budget in the project is wrong.

---

## Forks

| Fork | Difficulty | Value | Notes |
|---|---|---|---|
| **Per-azimuth flare control** | medium | **highest geometry value** | A low-order Fourier series in azimuth over the flare parameters, meshed ourselves into `design/custom.py`. The mesher refuses this today ("not supported yet"), which is exactly why it is unclaimed ground. The output must be a `.msh` in metres with `hornlab_mesher.tags` numbering, so nothing downstream changes. |
| **Guiding-curve superformula** | **trivial, already there** | medium | OSSE exposes `gcurve_sf_a`, `gcurve_sf_b`, `gcurve_sf_m1`, `gcurve_sf_m2`, `gcurve_sf_n1..n3`, `gcurve_se_n`. Add them to the OSSE key table and they become searchable. This is the Gielis superformula the project docs wanted, for the cost of a table row. **Do this one first.** |
| **ICW curvature controls as the search space** | **trivial, already there** | **high** | `kappa0`, `theta1_deg`, `hold_start`, `hold_end`, `kappa_abs_max`, `dkappa_ds_abs_max`, `n_coeff`. Mouth termination is the top of the project's own sensitivity ranking with ~2.6 dB available, and these parameters control exactly that. `examples/icw_termination.yaml` exists for this. |
| Morph parameters | trivial | medium | `morph_target`, `morph_width_mm`, `morph_height_mm`, `morph_corner_mm`, `morph_rate`. Rounded-rectangle mouth shaping. |
| ATH text import as a seed source | low | medium | The mesher imports ATH `.cfg`/`.txt` with global `Scale` and `VerticalOffset`. Lets a known-good published design become a search seed, which makes "did we beat the state of the art" a direct comparison instead of an argument. |
| Enclosure parameters | low | medium | `depth_mm`, `space_*_mm`, `edge_mm`, `edge_type`, `plan_type`, `plan_n`. The cabinet affects diffraction and therefore the polar. Searchable once the waveguide itself is settled. |
| MEH chamber and ports | high | high later | Tags 8 to 11 (`mid_chamber`, `mid_port_interior`, `mid_port_exit_left/right`) exist in the mesher. The geometry path is there; the blocker is coupled interior modeling, not geometry. |

The first three forks are table rows, not code, and two of them point straight at the highest-value physics in the project. Do them as soon as CP-2 passes.
