# 01 CONTRACTS

**FROZEN.** Every agent reads this completely before writing code. If your code does not fit a contract here, your code is wrong. If something you need is missing, that is a contract gap: append it to `NOTES_FOR_SENIOR.md` and stop that line of work.

Items marked **[open]** cannot be known until the stack is installed. Task 02 resolves each one and records it in `TOOLCHAIN.md`. Nothing downstream may guess at them.

---

## 1. What we build and what we consume

We build a **search layer**. We consume Collin's HornLab packages and do not reimplement them.

| We consume | Import | Job |
|---|---|---|
| `hornlab-waveguide-mesher` | `hornlab_mesher` | Geometry and meshing. OSSE / R-OSSE / ICW / FREEFORM. Writes gmsh `.msh`. |
| `hornlab-beat-bem` | `hornlab_beat_bem` | GPU BEM. CUDA on the 4070. |
| `hornlab-bempp-bem` | `hornlab_bempp_bem` | CPU BEM. The independent cross-check. |
| `hornlab-plots` | `hornlab_plots` | Figures for the report. |

We write: the design space, the objective, the search, the dataset, the report, and the parts of the geometry the mesher refuses.

**We never write:** a BEM or FEM solver, a Green's function, a mesher, a gmsh writer, a plotting library. If you find yourself doing any of those, stop and report.

**We never modify** any installed HornLab, Boundary Lab, BEAT or Julia file. They are pinned read-only dependencies.

### Licensing, stated once

`hornlab-waveguide-mesher`, `hornlab-bempp-bem` and `hornlab-plots` are **AGPL-3.0**; `hornlab-beat-bem` is **GPL-3.0-or-later**. A program that imports them is a derivative work. Our package is therefore **AGPL-3.0-or-later**, and `pyproject.toml` says so. That is fine for personal use and for sharing with Collin. It matters only if this is ever offered as a hosted service, where AGPL's network clause requires offering source to users. Put the license in the file and move on.

---

## 2. Repository layout

```
hornlab-search/                      <- repo root, git init here
  pyproject.toml
  README.md
  TOOLCHAIN.md                       <- written by task 02, read by everyone
  NOTES_FOR_SENIOR.md                <- append only
  .gitignore
  hornlab_search/
    __init__.py
    types.py                         <- section 4, verbatim
    constants.py                     <- section 3, verbatim
    config.py                        <- YAML -> Config
    design/
      __init__.py
      space.py                       <- DesignSpace, normalize/denormalize
      families.py                    <- Design -> hornlab_mesher config dict
      custom.py                      <- geometry the mesher refuses (phase 2 seam)
    mesh/
      __init__.py
      sizing.py                      <- epw -> res_mm, dof budget, caps
      build.py                       <- drive hornlab_mesher, cache by hash
    solve/
      __init__.py
      base.py                        <- the Backend protocol
      beat.py                        <- hornlab_beat_bem adapter
      bempp.py                       <- hornlab_bempp_bem adapter
      worker.py                      <- warm-worker lifecycle
      cache.py
    metrics/
      __init__.py
      polar.py  di.py  smoothness.py  impedance.py  compute.py
    targets/
      __init__.py
      spec.py                        <- Target dataclass
      venue.py                       <- room geometry -> coverage target
    objective/
      __init__.py
      terms.py  scalar.py
    search/
      __init__.py
      evaluate.py                    <- one candidate, end to end, never raises
      cma.py
      nsga.py                        <- phase 2 stub
    dataset/
      __init__.py
      record.py                      <- frozen training-record schema
      store.py                       <- shard writer/reader
    report/
      __init__.py
      html.py
    cli.py
  examples/
    osse_baseline.yaml
    throat_adapter.yaml
    icw_termination.yaml
    freeform_hv.yaml
    search_smoke.yaml
  tests/
    conftest.py
    test_<module>_*.py
  runs/                              <- gitignored
  cache/                             <- gitignored
  dataset/                           <- gitignored, but PRECIOUS. Back it up.
```

Nine subpackages, each with one job, each independently testable. The expansion seams are `design/custom.py`, `solve/base.py` (a protocol with two implementations), `search/nsga.py`, and the `dataset/` directory, which is what phase 2 trains on.

---

## 3. `hornlab_search/constants.py` (verbatim)

```python
"""Physical constants and design-check relations. Nothing else hardcodes these."""

C_AIR = 343.0        # m/s, 20 C. Use this everywhere. Not 344.
RHO_AIR = 1.204      # kg/m^3
REF_P = 20e-6        # Pa

# Pattern-control break frequency (Hughes, Understanding Horn Directivity Control).
#   f0 = KEELE_K / (mouth_dimension_m * coverage_angle_deg)
# Verified against the source's worked examples: 12 in / 90 deg -> 926 Hz.
KEELE_K = 25400.0    # m * deg * Hz

# First non-axisymmetric duct mode in a circular throat of radius a:
#   f11 = BESSEL_J1P_11 * C_AIR / (2 * pi * a)
# 1.0 in -> 7914 Hz, 1.4 in -> 5653 Hz, 2.0 in -> 3957 Hz.
BESSEL_J1P_11 = 1.8412

# MEH quarter-wavelength entry rule: d <= C_AIR / (4 * f_crossover)
MEH_ENTRY_FRACTION = 0.25
```

These are **design checks and sanity bounds, never constraints on the search.** Nothing in the optimizer may refuse a design because it violates a rule of thumb.

### Coordinate frame

**Verified from `hornlab-beat-bem`: the horizontal cut is in x-z, the vertical cut is in y-z, +Z is forward, centred on the global mesh origin.**

| Axis | Meaning |
|---|---|
| `+Z` | on-axis, out of the mouth |
| `+X` | horizontal |
| `+Y` | vertical |

Horizontal plane is `y = 0`. Vertical plane is `x = 0`. We never rotate anything. The mesher emits this frame and the solver expects it.

### Units, and the one that will bite you

| Where | Unit |
|---|---|
| Our Python | **metres**, radians internally, degrees in YAML and reports |
| Mesher config keys ending `_mm` | **millimetres** |
| The `.msh` the mesher writes | **metres**, because `scale_to_metres` defaults to `true` |
| `SolveConfig(mesh_scale=...)` | **`1.0`** |

The `hornlab-beat-bem` README's example uses `mesh_scale=0.001` because its example mesh is in millimetres. **Ours is not.** A wrong `mesh_scale` produces a horn 1000x the intended size and a perfectly smooth, completely wrong result. `mesh/build.py` asserts the written mesh's bounding box is of order 0.1 to 1 m and raises if not. Test it.

---

## 4. `hornlab_search/types.py` (verbatim)

Task 03 creates this. Wave 1 imports from it and does not edit it.

```python
"""Frozen data contracts. No new fields without a contract change."""
from __future__ import annotations

import hashlib, json
from dataclasses import dataclass, field, asdict
from typing import Literal, Protocol

import numpy as np

Mode = Literal["screen", "verify", "final"]
Family = Literal["OSSE", "R-OSSE", "ICW", "FREEFORM"]


def _hash(obj) -> str:
    """12 hex chars, stable across processes. ALWAYS hashlib, never hash()."""
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=float)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def _canon(d: dict) -> dict:
    out = {}
    for k, v in sorted(d.items()):
        if isinstance(v, (int, float)):
            out[k] = round(float(v), 9)
        elif isinstance(v, dict):
            out[k] = _canon(v)
        elif isinstance(v, (list, tuple)):
            out[k] = [round(float(x), 9) if isinstance(x, (int, float)) else x for x in v]
        else:
            out[k] = v
    return out


# ------------------------------------------------------------------ design

@dataclass(frozen=True)
class Design:
    """One candidate, in the mesher's own parameter names and units.

    family picks which key set is legal. params holds ONLY that family's keys,
    in the mesher's units (mm and deg, per its _mm / _deg suffixes).
    Validation of key legality lives in design/families.py, not here.
    """
    family: Family
    params: dict

    def hash(self) -> str:
        return _hash({"family": self.family, "params": _canon(self.params)})


@dataclass(frozen=True)
class MeshSpec:
    """Everything that changes the mesh for a given Design."""
    epw: float                 # elements per wavelength
    f_max_hz: float            # the frequency the mesh must resolve
    quadrants: str             # "1234" | "12" | "14" | "1"
    max_triangles: int
    allow_large_mesh: bool = False

    def hash(self) -> str:
        return _hash(_canon(asdict(self)))


@dataclass
class MeshResult:
    path: str                  # the .msh on disk, in METRES
    n_triangles: int
    n_dof: int | None          # None until a solve reports p1_dof_count
    quadrants: str
    symmetry_plane: str | None # the matching solver flag
    res_mm: dict               # {throat, mouth, rear}
    bbox_m: tuple              # (xmin, ymin, zmin, xmax, ymax, zmax)
    seconds: float


# ------------------------------------------------------------------ solve

@dataclass(frozen=True)
class ObservationSpec:
    distance_m: float
    angle_count: int           # samples per cut, spanning -90..+90 inclusive
    balloon: bool
    balloon_points: int        # 0 when balloon is False

    def hash(self) -> str:
        return _hash(_canon(asdict(self)))


@dataclass(frozen=True)
class SolveSpec:
    mode: Mode
    freqs_hz: tuple[float, ...]
    backend: str               # "beat_cuda" | "beat_cpu" | "bempp_cpu"
    observation: ObservationSpec
    gmres_tol: float
    extra: dict = field(default_factory=dict)

    def hash(self) -> str:
        d = _canon(asdict(self))
        d["freqs_hz"] = [round(float(f), 4) for f in self.freqs_hz]
        return _hash(d)


@dataclass
class Response:
    """What every backend returns. dB arrays are the contract; complex
    pressure is a bonus some backends provide and metrics never require."""
    freqs_hz: np.ndarray                 # (nf,)
    h_angles_deg: np.ndarray             # (na,) ascending, -90..+90, 0 included
    v_angles_deg: np.ndarray             # (na,)
    spl_h_db: np.ndarray                 # (nf, na) absolute dB SPL
    spl_v_db: np.ndarray                 # (nf, na)
    balloon_dirs: np.ndarray | None      # (nb, 3) unit vectors
    spl_balloon_db: np.ndarray | None    # (nf, nb)
    z_throat: np.ndarray | None          # (nf,) complex, normalized by rho*c
    p_h: np.ndarray | None = None        # (nf, na) complex, if available
    p_v: np.ndarray | None = None
    p_balloon: np.ndarray | None = None
    backend: str = ""
    n_dof: int | None = None
    meta: dict = field(default_factory=dict)

    @property
    def axis_index(self) -> int:
        """Index of the 0-degree sample. Both cuts share it."""
        i = int(np.argmin(np.abs(self.h_angles_deg)))
        assert abs(self.h_angles_deg[i]) < 1e-9, "no exact on-axis sample"
        return i


@dataclass
class SolveOutcome:
    ok: bool
    response: Response | None
    seconds: float
    peak_vram_mb: float | None
    message: str = ""


class Backend(Protocol):
    """solve/base.py. Two implementations: beat.py and bempp.py."""
    name: str
    def available(self) -> tuple[bool, str]: ...
    def solve(self, mesh: MeshResult, spec: SolveSpec) -> SolveOutcome: ...
    def warm(self) -> None: ...
    def release(self) -> None: ...


# ------------------------------------------------------------------ metrics

@dataclass
class MetricSet:
    freqs_hz: np.ndarray
    bw_h_deg: np.ndarray
    bw_v_deg: np.ndarray
    di_db: np.ndarray
    di_source: str                 # "balloon" | "cuts_estimate"
    ripple_h_db: np.ndarray
    ripple_v_db: np.ndarray
    on_axis_db: np.ndarray         # normalized to its own band mean
    z_throat_real: np.ndarray | None
    scalars: dict = field(default_factory=dict)


# ------------------------------------------------------------------ search

@dataclass
class Evaluation:
    design_hash: str
    design: Design
    mesh_hash: str
    solve_hash: str
    objective: float
    terms: dict
    metrics: MetricSet | None
    mesh: MeshResult | None
    outcome: SolveOutcome | None
    cached: bool = False
    error: str = ""
```

Three exceptions, appended to the same file:

```python
class GeometryInvalidError(ValueError): ...
class MeshTooLargeError(ValueError): ...
class BackendUnavailableError(RuntimeError): ...
```

---

## 5. The design space

The mesher's parameter names are the contract. We do not rename them. A `Design` carries the family and a dict in the mesher's own keys and units.

### Legal keys per family, from the mesher's config schema

| Family | Searchable keys |
|---|---|
| **OSSE** | `r0_mm`, `a_deg`, `a0_deg`, `L_mm`, `n`, `s`, `q`, `k`, `h`, `s1`, `s2`, `rot_deg`, plus `throat_ext_length_mm`, `throat_ext_angle_deg`, `slot_length_mm`, plus `exponent`, `aspect_ratio`, plus `morph_*` and `gcurve_*` |
| **R-OSSE** | `R_mm`, `tmax`, `m`, `r`, `b`, `s1`, `s2`, `k`, `q`, plus the throat and cross-section keys. `rot_deg` and explicit `L_mm` are unsupported. |
| **ICW** | `termination`, `r0_mm`, `a0_deg`, `L_mm`, `R_mm`, `coverage_angle_deg`, `hold_start`, `hold_end`, `kappa0`, `theta1_deg`, `n_coeff`, `kappa_abs_max`, `dkappa_ds_abs_max`, `theta_max_deg`, `pin_mouth_radius`, `icw_seed`, `icw_coeffs`, `icw_S` |
| **FREEFORM** | `profileH` / `profileV` point lists, `throatAngleDeg`, `mouthAngleDeg`, `crossSections` with `circle` / `ellipse` / `superellipse` (exponent 2 to 16) / `rounded_rectangle`, `inflectionPolicy` |

`design/families.py` holds one table per family of legal keys and their types, validates a `Design` against it, and raises `GeometryInvalidError` with the offending key on a mismatch. **It does not guess.** If a key is not in the table, it is rejected, and adding a key is a one-line table edit.

### Known refusals, which are the geometry novelty opening

Per the mesher's schema, verbatim: **per-azimuth throat stretch is not supported yet.** Expressions and per-azimuth forms raise `ConfigError`; stretch must be a plain finite number. ICW rejects OSSE/R-OSSE shape keys at the top level, rejects `zmap`, and is TOML/JSON/dict only.

`design/custom.py` is the reserved module for geometry beyond this. **It is empty in phase 1** and exists so that adding a family later is a new file plus a table row, not a refactor.

### Bounds and the search vector

```python
@dataclass(frozen=True)
class Bound:
    lo: float
    hi: float
    search: bool = True
    log: bool = False          # search in log space, for scale-like params


@dataclass
class DesignSpace:
    family: Family
    seed: Design
    bounds: dict[str, Bound]

    def keys(self) -> list[str]:
        """Searchable keys, SORTED ALPHABETICALLY. This order IS the CMA-ES
        vector order and must never depend on YAML key order."""

    def normalize(self, d: Design) -> np.ndarray: ...   # -> [0,1]^k, clips
    def denormalize(self, x: np.ndarray) -> Design: ... # clips x first
```

Requirements, each a test:

1. `denormalize(normalize(d)) == d` to 1e-9 on every searchable key.
2. `keys()` is alphabetical and independent of YAML ordering.
3. `normalize` clips rather than raising on an out-of-bounds seed, and logs a warning.
4. `log=True` bounds require `lo > 0` and map through `log10`.

---

## 6. Mesh sizing, the dof budget, and VRAM

### The conversion the mesher does not do for us

The mesher **rejects frequency and EPW keys** (`ConfigError`). We convert:

```
res_mm       = 1000 * C_AIR / (epw * f_max_hz)
mouth_res_mm = res_mm
rear_res_mm  = res_mm
throat_res_mm = res_mm / 2        # finer where the field is strongest
```

`epw = 6.0` is the project default and the floor any checkpoint accepts.

### VRAM is exact and known

Confirmed to three significant figures from two published datapoints (31 MB at 1,974 dofs, 3,337 MB at 20,422 dofs): the fused Burton-Miller operator is a **dense `complex64` matrix**, so

```
VRAM_bytes = 8 * N_dof^2
```

**8 GB card, 6.5 GB usable, so the theoretical ceiling is 28,500 dofs.** Caps with headroom:

| Mode | dof cap | Operator | Purpose |
|---|---|---|---|
| `screen` | **8,000** | 0.51 GB | inside the search loop |
| `verify` | **16,000** | 2.05 GB | re-solve the top candidates |
| `final` | **24,000** | 4.61 GB | one design, for the report |

**dofs, not elements.** For a closed triangular surface `V = F/2 + 2`, so dofs are roughly half the triangle count, but **do not rely on that**: the solver reports the true `p1_dof_count` in `native_diagnostics`, and task 02 builds a calibration table of `res_mm -> n_triangles -> n_dof` for the real geometry. `mesh/sizing.py` uses the measured relation, with `n_dof ~= n_tri/2` only as the initial guess before calibration exists.

### Setting `max_triangles`

`max_triangles` is a **full-domain-equivalent** ceiling, and the solved mesh is reduced by the quadrant factor:

```
quadrant_factor = {"1234": 1, "12": 2, "14": 2, "1": 4}[quadrants]
max_triangles   = ceil(2 * dof_cap * quadrant_factor * 1.15)    # 15% slack
```

Keep `allow_large_mesh: False` so the mesher keeps guarding us. **[open]** Whether a `max_triangles` well above the 18,000 default is accepted, or whether a second hard check intervenes, is unknown; task 02 tests it by building a deliberately large mesh.

### The guard

`mesh/build.py` raises `MeshTooLargeError` **before** handing anything to the solver if the estimated or reported dof count exceeds the mode cap. A CUDA out-of-memory mid-solve is far more expensive than a rejected candidate.

### What frequency this actually buys

For a quarter-domain surface of roughly 0.125 m^2 at `epw = 6`:

| dof cap | triangles solved | f_max |
|---|---|---|
| 8,000 | ~16,000 | ~13 kHz |
| 16,000 | ~32,000 | ~19 kHz |
| 24,000 | ~48,000 | ~23 kHz |

**[open]** These are arithmetic, not measurement. The calibration table in task 02 replaces them.

---

## 7. Observation and the probe geometry

```python
ObservationSpec(distance_m=2.0, angle_count=73, balloon=..., balloon_points=...)
```

- **`distance_m` default 2.0.** This matches `hornlab-beat-bem`'s own example and is the standard measurement distance. All our metrics are normalized, so the absolute level does not matter; what matters is being consistent and being outside the near field. **[open]** confirm the backend does not require a minimum.
- **`angle_count` default 73**, giving 2.5-degree steps from -90 to +90 inclusive. **It must be odd**, so there is an exact on-axis sample. `Response.axis_index` asserts this.
- **Balloon.** `hornlab-beat-bem` supports "spherical balloon/DI grids (theta-major)". Use it when available: `balloon=True`, `balloon_points` 512 for `screen` and 1024 for `verify` and `final`.

### The DI fallback, labeled honestly

**[open]** The exact balloon grid convention. If a backend cannot produce a balloon, DI is estimated from the two cuts via the solid-angle relation:

```
Omega = 4 * arcsin( sin(bw_h/2) * sin(bw_v/2) )
DI    = 10 * log10( 4*pi / Omega )
```

That is an **estimate assuming a separable rectangular pattern**, and it will be wrong for a lobed or diagonal-misbehaving horn. `MetricSet.di_source` records `"balloon"` or `"cuts_estimate"` on every single evaluation, the report prints it, and **no checkpoint may be passed on `cuts_estimate` DI.** A number whose provenance is not carried alongside it is how a project ends up with two incompatible DI conventions in one plot.

---

## 8. Frequency grids

Log-spaced, inclusive endpoints, rounded to 2 decimals. Band edges are YAML defaults; the grid shape is frozen.

| Mode | f_low | f_high | Points |
|---|---|---|---|
| `screen` | 500 | 10,000 | 12 |
| `verify` | 300 | 16,000 | 25 |
| `final` | 250 | 20,000 | 36 |

```python
def freq_grid(lo: float, hi: float, n: int) -> tuple[float, ...]:
    return tuple(round(float(f), 2) for f in np.geomspace(lo, hi, n))
```

**[verified]** B-FNO found that non-uniform frequency sampling materially improved accuracy near resonances. Log spacing is already non-uniform in linear frequency, which is the right default for both the physics and any later surrogate.

---

## 9. The worker lifecycle, which is not optional

**[verified]** Cold start is 12 to 15 s on CPU and about 41 s on Metal; a persistent worker reduces subsequent starts to about **0.01 s**. CUDA's first run pulls several GB.

At an expected 4 s per screening candidate, paying a 12 s cold start per candidate would **quadruple the cost of every search in this project.**

```
search startup:   backend.warm()          once
every candidate:  backend.solve(...)      reuses the warm worker
search teardown:  detach_workers()        leaves it warm for the next run
process exit:     shutdown_workers()      only here
```

- `solve/worker.py` owns this. Nothing else calls `shutdown_workers()`.
- `warm()` is idempotent and is called once at the top of `hornlab-search search` and `run`.
- Register an `atexit` handler that calls `detach_workers()`, and a `SIGINT` handler that does the same before exiting, so Ctrl-C does not orphan a Julia process holding VRAM.
- Log the measured first-solve and second-solve times at `INFO` on every run. If the second solve is not dramatically faster, the worker is not being reused and that is a bug worth catching immediately.

---

## 10. Metric definitions (frozen)

All on dB, normalized to the **on-axis sample** at each frequency unless stated.

| Metric | Definition |
|---|---|
| `bw_h_deg` | **Total included angle** between the two -6 dB crossings of the horizontal cut, referenced to the on-axis level at that frequency, not the maximum. Linear interpolation in dB versus angle between bracketing samples. No crossing in range gives `180.0`. More than two crossings: take the **outermost** pair and record the count in `scalars`. |
| `bw_v_deg` | Same, vertical cut. |
| `di_db` | `10*log10( p_axis^2 / mean(p_balloon^2) )` in linear power, from the balloon. Equal weights, which is correct for an equal-area grid. Otherwise the cuts estimate, with `di_source` saying so. |
| `ripple_h_db` | Standard deviation of normalized dB over cut samples **inside the target coverage angle**, excluding samples more than 40 dB down. Fewer than 5 surviving samples returns `nan`. |
| `ripple_v_db` | Same, vertical. |
| `on_axis_db` | `spl` on axis minus its own mean over the band. A flatness measure, not a level. |
| `di_slope_db_per_dec` | `polyfit(log10 f, di_db, 1)[0]`. **A constant-directivity horn is one whose DI is flat with frequency**, so this single number captures "does the pattern hold together" better than per-frequency beamwidth error does. |
| `z_throat_real` | Real part of throat impedance normalized by `rho*c`. `None` if the backend does not report it. |

**Beamwidth is -6 dB total included angle.** Half the horn specs in the world use the other convention; ours is fixed here so no two of our numbers are ever on different ones. The cardioid reads 180.0, not 90.0, and that is the test.

Standard deviation rather than peak-to-peak for ripple: peak-to-peak is set by one sample, which makes the objective landscape spiky, which is poison for CMA-ES. It also matches the definition the earlier tiling study used, so the numbers stay comparable.

---

## 11. Targets and the objective

### `targets/spec.py`

```python
@dataclass(frozen=True)
class Target:
    coverage_h_deg: float        # TOTAL included angle
    coverage_v_deg: float
    band_lo_hz: float
    band_hi_hz: float
    di_target_db: float | None   # None -> derive from coverage
    di_slope_target: float = 0.0 # flat DI
    z_min: float = 0.0
    freq_weights: dict | None = None
```

### `targets/venue.py`, the cheap generative piece

Turns a described space into a coverage target instead of typing 75 x 45:

```python
def coverage_from_room(listener_width_m, listener_depth_near_m,
                       listener_depth_far_m, height_m, splay_deg=0.0) -> Target
```

Pure trigonometry, no solver. Also reports, from `KEELE_K`, the **mouth dimension each axis would need** to hold that coverage down to `band_lo_hz`, which immediately tells the user whether their target is physically possible at the size they have in mind. That check costs nothing and prevents a search from grinding for hours against geometry that cannot exist.

### The objective

```
cov    = mean_f( (bw_h - target_h)^2 + (bw_v - target_v)^2 ) / 100
rip    = mean_f( ripple_h + ripple_v )
di     = mean_f( (di - di_target)^2 ) / 10
dislope= (di_slope - di_slope_target)^2
flat   = std_f( on_axis_db )
load   = mean_f( max(0, z_min - z_throat_real) )       skipped if None

J = w_cov*cov + w_rip*rip + w_di*di + w_dislope*dislope
    + w_flat*flat + w_load*load + penalty
```

- Every mean is `np.nanmean` over frequencies inside `[band_lo, band_hi]`, and the nan count goes in `terms`.
- `di_target` from `Target.di_target_db`, else `10*log10(4*pi/Omega)` from the coverage angles.
- Penalties, all **large and finite**: invalid geometry `1e3`, mesh too large `1e3`, solve failed `1e3`. **Never `inf`**: `inf` permanently poisons the CMA-ES covariance update.
- **Lower is better.** Every agent assumes minimization.
- Every term is logged separately in `Evaluation.terms`, always with the same key set, zeros for skipped terms, plus `penalty` and `total`.

Defaults: `w_cov=1.0, w_rip=1.0, w_di=0.3, w_dislope=0.5, w_flat=0.5, w_load=0.0`.

Task 08 prints all terms for the seed design and confirms none dominates by two orders of magnitude. If one does, the divisors are wrong and the YAML weights are lying.

---

## 12. Search

**CMA-ES** via `cma` for phase 1. Not NSGA-II yet, and the reason is now quantified rather than asserted: at an expected 4 to 8 s per screening solve we get **hundreds to a couple of thousand** evaluations in a sitting, not the 10,000 a population method wants. CMA-ES is the most sample-efficient general black-box optimizer at that budget for a 6 to 15 dimensional continuous problem, needs no gradient, and tolerates occasional failure penalties.

`search/nsga.py` exists as a stub with the interface defined, because NSGA-II becomes the right answer the moment the surrogate lands. That is the whole point of phase 2.

| Setting | Value |
|---|---|
| Space | unit box `[0,1]^k` |
| `x0` | normalized seed |
| `sigma0` | `0.25` |
| Seed | YAML, default `1234`. Reproducibility is required. |
| Stop | evaluation budget, or `tolfun` **set above the measured noise floor** |
| Bounds | clip inside `denormalize`, not with CMA penalties |

**`tolfun` must sit above the noise floor measured in CP-7f.** A search converging below its own noise floor spends hours refining an artifact.

---

## 13. The dataset record (frozen, written from day one)

This is the prerequisite for everything in `11_PHASE2_SURROGATE.md`. It costs almost nothing now and cannot be reconstructed later.

**Every evaluation writes a record, including failures.** Failures teach a surrogate where the invalid region is, which is information a search needs.

```
dataset/
  shard-0000.jsonl     one JSON object per line, metadata
  shard-0000.npz       arrays, keys "<row_index>/<array_name>"
  index.jsonl          one line per record: {design_hash, shard, row, objective, ok}
```

Metadata schema, `schema_version: 1`:

```json
{
  "schema_version": 1,
  "design_hash": "...", "mesh_hash": "...", "solve_hash": "...",
  "family": "OSSE",
  "params": { },
  "target": { },
  "mesh": {"n_triangles": 0, "n_dof": 0, "quadrants": "1",
           "res_mm": {"throat": 0, "mouth": 0, "rear": 0},
           "bbox_m": [0,0,0,0,0,0], "area_m2": 0.0, "seconds": 0.0,
           "grid": {"angular_segments": 64, "length_segments": 32,
                    "available": false}},
  "solve": {"backend": "beat_cuda", "mode": "screen",
            "freqs_hz": [], "observation": { }, "gmres_tol": 1e-5,
            "seconds": 0.0, "peak_vram_mb": 0.0, "n_dof": 0},
  "excitation": {"port_tag": 2, "port_name": "SD1D1001",
                 "kind": "uniform_normal_velocity",
                 "amplitude": 1.0, "units": "m/s",
                 "frequency_dependent": false, "notes": ""},
  "traces": {"captured": false, "path": null, "kind": null},
  "metrics_scalars": { },
  "objective": 0.0, "terms": { },
  "ok": true, "error": "",
  "created_utc": "2026-10-13T00:00:00Z",
  "lib_shas": {"hornlab_mesher": "...", "hornlab_beat_bem": "...",
               "hornlab_search": "..."}
}
```

Arrays in the `.npz`: `freqs_hz`, `h_angles_deg`, `v_angles_deg`, `spl_h_db`, `spl_v_db`, `balloon_dirs`, `spl_balloon_db`, `z_throat`, and the per-frequency metric arrays.

Rules:

1. **Append only.** Never rewrite a shard. Roll to a new shard at 500 records or 200 MB.
2. **`lib_shas` on every record.** A dataset mixing two solver versions is a dataset whose labels disagree, and without the SHA you cannot tell which half to throw away.
3. **Record failures.** `ok: false` with the error string, and null arrays.
4. **`dataset/` is gitignored and precious.** The README says to back it up. It is the only artifact here that takes GPU-hours to regenerate.
5. **The `excitation` block is mandatory on every row.** B-FNO's verified finding is that frequency must be encoded through the **source field on the boundary**, not as a scalar channel, and that the scalar version performed worse. A dataset recording only a frequency list cannot train a model with that encoding, and the rows cannot be repaired afterwards. In phase 1 the excitation is a constant uniform normal velocity on tag 2, so this block is three lines of boilerplate. It costs nothing now and is unrecoverable later.
6. **Boundary traces, on a sampled fraction.** Every boundary-centric surrogate in the literature trains on boundary solutions; far-field alone cannot train any of them. Capture `surface_traces` for **1 record in 20** by default, configurable, with the fraction recorded in the metadata. Store under `dataset/traces/<design_hash>.npz`. If task 02's capability check says traces are unavailable, set `"captured": false` everywhere and note it in `TOOLCHAIN.md`.
7. **`mesh.grid` records the mesher's structured surface sampling.** An `angular x length` tensor with a periodic azimuthal axis is exactly the layout a Fourier neural operator assumes, and the usual hardest part of building one. Record the segment counts always, and whether the grid itself was reachable through the mesher's API.

**[verified]** B-FNO needed 3,000 to 25,600 BEM solves depending on the case, with geometry varying across training samples. At an inferred 4 s per screening solve, 10,000 records is about 11 hours. Routine search traffic produces them for free, **provided the rows carry enough to train on.** Rules 5 through 7 are what make that true, and each is cheap now and impossible to backfill.

---

## 14. Run directory

```
runs/<UTC timestamp>-<mode>-<short id>/
  run.json              config snapshot, TOOLCHAIN snapshot, lib SHAs, timings
  search.ndjson         one Evaluation per line, appended, FLUSHED AND FSYNCED
  best.json             rewritten on every improvement
  designs/<design_hash>/
    design.json  mesh.msh  response.npz  metrics.json  status.json
  cma/                  cma logger output
  report.html
```

Cache key: `f"{design.hash()}-{mesh.hash()}-{solve.hash()}"`. A hit requires `ok: true`. Copy, never symlink: symlinks on Windows need elevation and fail in confusing ways.

Resume must be free: re-running the same config performs zero solves for evaluations already in `search.ndjson`. Test it.

---

## 15. Error handling

| Situation | Result |
|---|---|
| Illegal param key for the family | `GeometryInvalidError`, invalid, search continues |
| Mesher raises `ConfigError` | invalid, the mesher's message saved verbatim |
| Estimated or reported dofs over cap | `MeshTooLargeError`, invalid, **no solve attempted** |
| Mesh bbox not of order 0.1 to 1 m | hard failure, this is a units bug, stop the run |
| Backend unavailable | `BackendUnavailableError` at startup, not per candidate |
| Solve raises | `SolveOutcome(ok=False)`, penalty, full traceback saved, search continues |
| Solve times out | kill the process **group**, not the child; Julia spawns workers that will otherwise hold VRAM |
| CUDA OOM | solve failure **and** the dof cap in `TOOLCHAIN.md` is wrong; append to `NOTES_FOR_SENIOR.md` |
| Any unexpected exception in an evaluation | caught at `search/evaluate.py`, logged into the row with traceback, search continues |

**The search loop is never killed by one bad candidate.** That is the difference between a tool and a demo.

**[verified]** beat-bem raises on incomplete sweeps rather than returning partial data, so there is no partial-result path to handle. If that changes, a partial result is usable in `screen` and never in `verify`, `final` or any checkpoint.

---

## 16. Logging

`stdlib logging`, one logger per module, named `hornlab_search.<module>`.

| Level | Content |
|---|---|
| `INFO` | one line per evaluation: hash, J, mesh s, solve s, dofs, cached |
| `DEBUG` | every mesher config dict and every `SolveConfig`, as a copy-pasteable repr |
| `WARNING` | clipped bounds, `cuts_estimate` DI, fallback backend, cold worker |
| `ERROR` | solve failures with the first 2000 characters of the traceback |

The `DEBUG` repr requirement matters: when something is wrong at 2 a.m., being able to paste one dict into a REPL and call `build_from_config` by hand is worth more than any amount of structured error handling.

---

## 17. Dependencies

```toml
requires-python = ">=3.11,<3.14"

dependencies = [
  "numpy>=1.26,<3",
  "scipy>=1.11",
  "cma>=3.3",
  "pyyaml>=6",
  "jinja2>=3.1",
  "hornlab-waveguide-mesher @ git+https://github.com/m3gnus/hornlab-waveguide-mesher.git@<SHA>",
  "hornlab-beat-bem @ git+https://github.com/m3gnus/hornlab-beat-bem.git@<SHA>",
  "hornlab-plots @ git+https://github.com/m3gnus/hornlab-plots.git@<SHA>",
]

[project.optional-dependencies]
crosscheck = ["hornlab-bempp-bem @ git+https://github.com/m3gnus/hornlab-bempp-bem.git@<SHA>"]
dev = ["pytest>=8", "pytest-timeout"]
surrogate = ["torch>=2.2"]          # phase 2 only, not installed in phase 1
```

**Pin every HornLab dependency by 40-character commit SHA.** Their own README instructs this, none are on PyPI, and a dataset built against two different solver commits is a dataset with inconsistent labels. Task 02 records the SHAs; `pyproject.toml` carries them; every dataset record repeats them.

**Not** torch in phase 1. **Not** pymoo until NSGA-II. **Not** gmsh directly, the mesher owns it. **Not** matplotlib directly, `hornlab_plots` owns it.

`hornlab-search` lives in **its own virtualenv** with the HornLab packages installed into it. We import them as libraries; we do not live inside Boundary Lab's environment.
