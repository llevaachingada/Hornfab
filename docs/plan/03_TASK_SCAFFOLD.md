# 03 TASK SCAFFOLD

**Wave 0, step 2. Same agent as task 02, immediately after CP-0 passes.**

Owner of: `pyproject.toml`, `.gitignore`, `README.md`, `hornlab_search/__init__.py`, `constants.py`, `types.py`, `config.py`, `cli.py` (until Wave 2), `tests/conftest.py`, `tests/test_config.py`, `examples/*.yaml`, and the empty `__init__.py` of every subpackage.

Reads: `01_CONTRACTS.md`, `TOOLCHAIN.md`

Four agents are about to build inside this skeleton simultaneously. Get the layout and `types.py` exactly right; a rename afterwards costs four merge conflicts.

---

## Build

### Step 1: Directories

Create every directory from `01_CONTRACTS.md` section 2, and **create an empty `__init__.py` in every subpackage now** (`design`, `mesh`, `solve`, `metrics`, `targets`, `objective`, `search`, `dataset`, `report`), even though you do not own what goes inside them. That way no Wave 1 agent ever has to touch a shared file.

```powershell
cd C:\dev\hornlab-search
git init
```

### Step 2: `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "hornlab-search"
version = "0.1.0"
description = "Objective-driven horn geometry search over the HornLab BEM stack"
requires-python = ">=3.11,<3.14"
license = {text = "AGPL-3.0-or-later"}
dependencies = [
  "numpy>=1.26,<3",
  "scipy>=1.11",
  "cma>=3.3",
  "pyyaml>=6",
  "jinja2>=3.1",
  "hornlab-waveguide-mesher @ git+https://github.com/m3gnus/hornlab-waveguide-mesher.git@<SHA FROM TOOLCHAIN>",
  "hornlab-beat-bem @ git+https://github.com/m3gnus/hornlab-beat-bem.git@<SHA FROM TOOLCHAIN>",
  "hornlab-plots @ git+https://github.com/m3gnus/hornlab-plots.git@<SHA FROM TOOLCHAIN>",
]

[project.optional-dependencies]
crosscheck = ["hornlab-bempp-bem @ git+https://github.com/m3gnus/hornlab-bempp-bem.git@<SHA>"]
dev = ["pytest>=8", "pytest-timeout"]
surrogate = ["torch>=2.2"]

[project.scripts]
hornlab-search = "hornlab_search.cli:main"

[tool.setuptools.packages.find]
include = ["hornlab_search*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
timeout = 900
markers = [
  "slow: needs a real BEM solve",
  "gpu: needs a working CUDA backend",
  "crosscheck: needs hornlab-bempp-bem",
]
addopts = "-ra -q"
```

**Paste the real 40-character SHAs from `TOOLCHAIN.md`.** A floating git dependency means the dataset labels drift under you.

The AGPL license line is not optional: three of the four dependencies are AGPL-3.0 and a program importing them is a derivative work.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

`.gitignore`:

```
.venv/
__pycache__/
*.pyc
runs/
cache/
dataset/
scratch/
*.msh
report.html
.pytest_cache/
```

**`dataset/` is gitignored but precious.** Say so in `README.md`: it is the only artifact here that costs GPU-hours to regenerate, and it is the entire prerequisite for phase 2.

### Step 3: `constants.py` and `types.py`

Copy **sections 3 and 4 of `01_CONTRACTS.md` verbatim**. Do not improve them, add fields, or reorder dataclasses. Four agents are about to depend on the exact names. Append the three exceptions from section 4.

**Gate:**

```powershell
.\.venv\Scripts\python.exe -c "from hornlab_search.types import Design, MeshSpec, MeshResult, ObservationSpec, SolveSpec, Response, SolveOutcome, Backend, MetricSet, Evaluation, GeometryInvalidError, MeshTooLargeError, BackendUnavailableError; from hornlab_search.constants import C_AIR, KEELE_K, BESSEL_J1P_11; print(C_AIR, KEELE_K, BESSEL_J1P_11)"
```

prints `343.0 25400.0 1.8412`.

### Step 4: `config.py`

```python
@dataclass
class Config:
    name: str
    space: DesignSpace          # from design/space.py (task 04); import lazily
    target: Target              # from targets/spec.py (task 06); import lazily
    weights: dict               # term name -> float
    mesh: MeshSettings
    solve: SolveSettings
    search: SearchSettings
    raw: dict


def load_config(path) -> Config: ...
def freq_grid(lo: float, hi: float, n: int) -> tuple[float, ...]: ...
def mesh_spec(mode: str, cfg: Config) -> MeshSpec: ...
def solve_spec(mode: str, cfg: Config) -> SolveSpec: ...
```

**Circular-import note.** `config.py` needs `DesignSpace` and `Target`, which Wave 1 agents own. Define both as **lightweight local dataclasses in their own modules and import them inside the function body**, or keep `Config.space` and `Config.target` as plain dicts in Wave 0 and have Wave 2 build the typed objects. **Pick the dict approach**: `config.py` returns `raw` sections and the pipeline constructs typed objects. It keeps Wave 0 free of any dependency on Wave 1 and it is one fewer thing to break.

So concretely:

```python
@dataclass
class Config:
    name: str
    family: str
    seed_params: dict
    bounds_raw: dict            # key -> {lo, hi, search, log}
    target_raw: dict
    weights: dict
    mesh: MeshSettings
    solve: SolveSettings
    search: SearchSettings
    raw: dict
```

`MeshSettings`: `epw`, `quadrants`, `dof_cap_screen/verify/final`, `dof_per_triangle` (from the M1 calibration), `max_triangle_slack`.

`SolveSettings`: `backend`, `distance_m`, `angle_count`, `balloon`, `balloon_points_screen/verify`, `gmres_tol`, `timeout_s`.

`SearchSettings`: `algorithm`, `sigma0`, `seed`, `budget`, `popsize`, `tolfun`.

### Step 5: Example configs

Four seeds, one per idea worth running. Every number is a starting point.

**`examples/osse_baseline.yaml`** — the general-purpose waveguide.

```yaml
name: osse_baseline
family: OSSE

seed_params:
  r0_mm:   17.78        # 1.4 in exit radius
  a_deg:   37.5         # coverage HALF-angle in the mesher's convention
  a0_deg:  15.5
  L_mm:    260.0
  n:       4.0
  s:       0.7
  q:       0.995
  k:       1.0
  exponent: 4.0         # superellipse cross-section
  aspect_ratio: 1.25

bounds:
  r0_mm:        {lo: 17.78, hi: 17.78, search: false}
  a_deg:        {lo: 25.0,  hi: 55.0}
  a0_deg:       {lo: 2.0,   hi: 30.0}
  L_mm:         {lo: 140.0, hi: 420.0}
  n:            {lo: 2.0,   hi: 8.0}
  s:            {lo: 0.0,   hi: 1.0}
  q:            {lo: 0.90,  hi: 1.00}
  k:            {lo: 0.3,   hi: 2.5}
  exponent:     {lo: 2.0,   hi: 8.0}
  aspect_ratio: {lo: 1.0,   hi: 2.0}

target:
  coverage_h_deg: 75.0        # TOTAL included angle, -6 dB
  coverage_v_deg: 45.0
  band_lo_hz: 700.0
  band_hi_hz: 13000.0
  di_target_db: null          # derive from coverage
  di_slope_target: 0.0        # flat DI with frequency

weights: {cov: 1.0, rip: 1.0, di: 0.3, dislope: 0.5, flat: 0.5, load: 0.0}

mesh:
  epw: 6.0
  quadrants: "1"              # quarter; requires a symmetric design
  dof_cap_screen: 8000
  dof_cap_verify: 16000
  dof_cap_final:  24000
  dof_per_triangle: 0.5       # REPLACE with the M1 measurement

solve:
  backend: beat_cuda
  distance_m: 2.0
  angle_count: 73             # must be ODD
  balloon: true
  balloon_points_screen: 512
  balloon_points_verify: 1024
  gmres_tol: 1.0e-5
  timeout_s: 900

search: {algorithm: cma, sigma0: 0.25, seed: 1234, budget: 200,
         popsize: null, tolfun: 1.0e-3}
```

**`examples/throat_adapter.yaml`** — the project docs call this the best effort-to-payoff bet. Small, axisymmetric, fast, and it produces a printable part for hardware already owned.

Family `OSSE`, searching only `throat_ext_length_mm`, `throat_ext_angle_deg`, `slot_length_mm`, `a0_deg`, `k` with everything else pinned. Band 2 kHz to 16 kHz, weights `{rip: 1.0, flat: 1.0, load: 0.5, cov: 0.2}`. `quadrants: "1"`. This one runs in minutes per candidate and is the right first real experiment.

**`examples/icw_termination.yaml`** — mouth termination is the top of the project's own sensitivity ranking, with roughly 2.6 dB available. Family `ICW`, searching `termination`, `kappa0`, `theta1_deg`, `hold_start`, `hold_end`, `R_mm`, `coverage_angle_deg`. Nobody has optimized these.

**`examples/freeform_hv.yaml`** — family `FREEFORM`, with `profileH` and `profileV` control points and a `crossSections` list using `superellipse`. The widest geometry freedom the mesher offers today.

**`examples/search_smoke.yaml`** — a copy of `osse_baseline` with `dof_cap_screen: 3000`, `band_hi_hz: 6000`, `budget: 60`, `balloon_points_screen: 256`. **Size it from the M3 measurement so it finishes in under an hour on the real machine**, and record what you chose.

### Step 6: `tests/conftest.py`

Wave 1 agents must not edit this, so put everything they might need in it now.

```python
REPO = Path(__file__).resolve().parents[1]

@pytest.fixture(scope="session")
def toolchain() -> dict:
    """Parsed key/value lines from TOOLCHAIN.md. Returns {} if absent,
    never raises, so unit tests run on a machine with no solver."""

@pytest.fixture(scope="session")
def cfg(): return load_config(REPO / "examples" / "osse_baseline.yaml")

@pytest.fixture(scope="session")
def smoke_cfg(): return load_config(REPO / "examples" / "search_smoke.yaml")

@pytest.fixture
def rng(): return np.random.default_rng(20261013)

@pytest.fixture(scope="session")
def mesher_available() -> bool: ...     # importlib.util.find_spec
@pytest.fixture(scope="session")
def beat_available() -> bool: ...
@pytest.fixture(scope="session")
def bempp_available() -> bool: ...

@pytest.fixture
def fake_response():
    """A synthetic Response with a cardioid pattern at 12 frequencies,
    73 angles per cut, a 512-point balloon, and no NaN. Metrics and dataset
    tests build on this instead of running a solver."""

@pytest.fixture
def fibonacci_512() -> np.ndarray: ...
```

Plus skip markers:

```python
requires_mesher   = pytest.mark.skipif(not _have("hornlab_mesher"), reason="...")
requires_beat     = pytest.mark.skipif(not _have("hornlab_beat_bem"), reason="...")
requires_bempp    = pytest.mark.skipif(not _have("hornlab_bempp_bem"), reason="...")
```

**Every test that does not carry one of these markers must pass with nothing installed but numpy and scipy.** That is what makes the four Wave 1 tasks independently verifiable.

The `fake_response` fixture is the most important thing in this file. Tasks 06, 07 and 08 all build on it, and if it is wrong they all inherit the error, so write it carefully and assert its own properties in `test_config.py`.

### Step 7: `cli.py` with `doctor` and `version`

You own this until Wave 2.

| `doctor` check | Pass |
|---|---|
| Python version | in `[3.11, 3.14)` |
| core imports | numpy, scipy, cma, yaml, jinja2 |
| HornLab imports | `hornlab_mesher`, `hornlab_beat_bem`, `hornlab_plots`; bempp reported but optional |
| pinned SHAs | installed SHAs match `pyproject.toml`; **mismatch is a WARNING with both values printed** |
| `TOOLCHAIN.md` | present, and its `dof_per_triangle` is not the placeholder `0.5` |
| GPU | `nvidia-smi` exits 0 |
| backend | `beat_backend_statuses()` reports the configured backend functional |
| configs | all five example YAMLs load |
| round trip | reserved, filled by task 04 |

Exit 0 if all pass, 1 otherwise, one `PASS`/`FAIL` line each with a reason. Leave:

```python
# --- Wave 2 adds run / search / verify / report / selftest below (task 08) ---
```

The SHA-mismatch check earns its place: it is how someone discovers in five seconds, rather than after a confusing afternoon, that their dataset was built against a different solver than their code expects.

### Step 8: `README.md`

Short. What it does, that it is a search layer over Collin's HornLab packages, install, the six commands, the AGPL note, **and a line telling the reader to back up `dataset/`**. Link the two project docs. Do not restate the contracts.

---

## Checkpoint CP-1

```powershell
.\.venv\Scripts\python.exe -m pip list
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\hornlab-search.exe doctor
.\.venv\Scripts\hornlab-search.exe version
```

Plus a full recursive directory listing excluding `.venv`.

Write `tests/test_config.py` yourself:

1. All five example YAMLs load with no `None` in a required field.
2. `freq_grid(500, 10000, 12)` returns 12 ascending values, endpoints exact.
3. `angle_count` is odd in every example config, and `(angle_count - 1)` divides 180 evenly.
4. `Design.hash()` is **stable across processes**: compute it in a subprocess and compare. Confirm the implementation uses `hashlib`, not Python's salted `hash()`.
5. `SolveSpec.hash()` changes when any single field changes, including one frequency moving by 0.01 Hz.
6. `MeshSpec.hash()` changes when `quadrants` changes.
7. `fake_response` has: no NaN anywhere, an exact 0-degree sample, `axis_index` working, balloon directions of unit norm, and shapes consistent with its own frequency and angle arrays.
8. `constants.KEELE_K / (0.3048 * 90) == 926` to 1 Hz, which reproduces the worked example from the source the constant came from.

Test 4 matters more than it looks: an unstable hash means the cache misses forever, every resumed search re-solves everything, and the dataset gets duplicate rows under different keys.

Test 8 is a one-line guard against someone "tidying" the constant later.

**CP-1 passes when:** `pytest -q` is all green with no skips other than dependency-gated ones, `doctor` exits 0, and the layout matches `01_CONTRACTS.md` section 2 exactly.

---

## Handoff block

End your report with this, filled in. It is what the orchestrator pastes to the four Wave 1 agents.

```
WAVE 1 IS CLEAR TO START.

Repo root:              <abs path>
Python interpreter:     <abs path>
pytest command:         <exact command>
Working backend:        <beat_cuda | beat_cpu>
bempp available:        <yes | no>
dof caps:               screen <N>  verify <N>  final <N>
Measured dof/triangle:  <value from M1>
Measured s/candidate:   <value from M3>
Balloon available:      <yes, field <name> | no, metrics use cuts_estimate>
Complex pressure:       <yes, attr <name> | no>
Impedance BCs:          <yes | no | UNRESOLVED>
Response attributes:    <paste the list>
```
