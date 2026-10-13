# 05 TASK SOLVE

**Wave 1, parallel with 04, 06 and 07. No shared files.**

Owner of: `hornlab_search/solve/base.py`, `beat.py`, `bempp.py`, `worker.py`, `traces.py`, `cache.py`, `tests/test_solve_*.py`
Reads: `01_CONTRACTS.md`, `TOOLCHAIN.md` (especially the Response schema and C1 through C5)
Imports: stdlib, `numpy`, `hornlab_search.types`, `hornlab_beat_bem`, optionally `hornlab_bempp_bem`

You adapt two existing solvers to one `Backend` protocol and manage the warm worker. **You write no acoustics.** If you are writing a Green's function, a quadrature rule or a GMRES, stop.

The whole task is roughly 400 lines. The previous version of this plan had you authoring project files, launching subprocesses, parsing NDJSON event streams and reading run directories. None of that exists now: `hornlab_beat_bem.solve_frequencies()` is a Python function call.

---

## Step 0: Discovery

Read `TOOLCHAIN.md`'s Response schema section first. Then confirm it yourself:

```python
import hornlab_beat_bem as beat, inspect
print(inspect.signature(beat.solve_frequencies))
print(inspect.signature(beat.SolveConfig))
print(inspect.signature(beat.ObservationConfig))
print(inspect.getdoc(beat.SolveConfig))
r = beat.solve_frequencies(<a mesh from task 02>, [1000.0], cfg)
for n in dir(r):
    if not n.startswith("_"):
        v = getattr(r, n)
        print(f"{n:35s} {type(v).__name__:12s}",
              getattr(v, "shape", ""), getattr(v, "dtype", ""))
```

Answer and paste:

1. The complete `SolveConfig` and `ObservationConfig` field lists with defaults.
2. Every result attribute with type, shape and dtype.
3. **Which attribute holds the horizontal cut and which the vertical**, and whether the angle values come back as an array or must be reconstructed from `angle_count`.
4. **Is `spl_db` absolute dB SPL re 20 uPa, and is `directivity_db` the same data normalized so `directivity_reference_index` reads 0 dB?** Confirm by differencing them.
5. **The balloon.** Which field enables it, what shape comes back, and the direction convention: theta-major, theta and phi relative to +Z, full sphere or hemisphere. If you cannot enable it, say so plainly.
6. **Complex pressure:** exposed or not, and under what name.
7. The impedance pair. The README calls it legacy-scaled `[Re(F)/2, -Im(F)/2]`. Report what you actually get and what it would take to turn it into a normalized specific acoustic impedance.
8. What `is_partial`, `cancelled` and `requested_frequency_count` do on a successful run, and what exception type an incomplete sweep raises.

Then do the same for `hornlab_bempp_bem`, which exposes `solve`, `solve_frequencies`, `SolveConfig`, `ObservationConfig`, `load_mesh`, `Channel`, `Crossover`, `solve_channel_basis`, `check_opencl`, `require_opencl`, `evaluate_exterior_from_traces`, and returns a `SolveResult` with complex pressure, SPL, impedance and solver logs.

**Report every place the two interfaces differ.** That difference list is the reason `base.py` exists.

---

## Build

### 1. `solve/base.py`

```python
class Backend(Protocol):
    name: str
    def available(self) -> tuple[bool, str]: ...
    def warm(self) -> None: ...
    def solve(self, mesh: MeshResult, spec: SolveSpec) -> SolveOutcome: ...
    def release(self) -> None: ...


def get_backend(name: str) -> Backend:
    """'beat_cuda' | 'beat_cpu' | 'bempp_cpu'. Raises BackendUnavailableError
    with the reason from available() if the backend cannot run."""


def arc_angles_deg(angle_count: int) -> np.ndarray:
    """Ascending, -90 to +90 inclusive, with an EXACT 0. Raises if
    angle_count is even."""
```

The protocol is the expansion seam. A third backend later is a new file plus one line in `get_backend`.

### 2. `solve/beat.py`

```python
class BeatBackend:
    def __init__(self, device: str):     # "cuda" or "cpu"
        ...

    def solve(self, mesh: MeshResult, spec: SolveSpec) -> SolveOutcome:
        cfg = beat.SolveConfig(
            beat_backend=self.device,
            native_symmetry_plane=mesh.symmetry_plane,   # FROM THE MESH
            mesh_scale=1.0,                              # mesher writes METRES
            observation=beat.ObservationConfig(
                distance_m=spec.observation.distance_m,
                angle_count=spec.observation.angle_count,
            ),
            # plus whatever task 02's C1 found for the balloon
        )
        ...
```

Three things that must be right:

| | |
|---|---|
| **`native_symmetry_plane` comes from `mesh.symmetry_plane`**, which `mesh/sizing.py` derived from `quadrants`. Never from the config, never a literal. | A quarter mesh solved without the flag, or a full mesh solved with it, both give clean wrong polars. One of the three silent killers. |
| **`mesh_scale=1.0`**, with a comment saying the mesher writes metres and the beat README's `0.001` example does not apply to us. | A 1000x horn solves fine and looks smooth. |
| **`distance_m` and `angle_count` come from `spec.observation`.** | They are part of the solve hash, so the cache must see them. |

Wrap the call:

```python
t0 = time.perf_counter()
try:
    raw = beat.solve_frequencies(mesh.path, list(spec.freqs_hz), cfg)
except Exception as e:
    return SolveOutcome(False, None, time.perf_counter()-t0, vram, repr(e))
```

Then `_to_response(raw, spec, mesh)` builds our `Response`:

- `spl_h_db`, `spl_v_db` as `(nf, na)` float arrays, frequencies in the order of `spec.freqs_hz`.
- `h_angles_deg`, `v_angles_deg` from `arc_angles_deg(spec.observation.angle_count)`, **unless the result object supplies real angle arrays, in which case use those and assert they match.**
- `balloon_dirs` and `spl_balloon_db` if the balloon ran, else `None`.
- `n_dof` from `native_diagnostics["p1_dof_count"]`. **Always capture it:** it is what makes the dof calibration real instead of estimated, and it goes into every dataset record.
- `z_throat` from the impedance pair, if you worked out the conversion. `None` otherwise, which is fine: the default objective weight is 0.
- `meta` carries `is_partial`, `cancelled`, `requested_frequency_count`, and anything in `native_diagnostics`.

**Sanity assertions inside `_to_response`**, all raising rather than returning a bad `Response`:

- shapes are `(len(spec.freqs_hz), angle_count)`
- no `NaN` and no `inf`
- the on-axis sample of the horizontal and vertical cuts agree to 1e-6 dB, since they are the same physical point
- `spl_h_db` is finite and within a plausible range, say -200 to 200 dB

That third assertion is nearly free and catches a transposed or mis-sliced array immediately.

### 3. `solve/bempp.py`

Same shape, over `hornlab_bempp_bem`. It need not support everything: implement `solve` for the frequencies and the two cuts, and return `balloon_dirs=None` if a balloon is awkward. Its job is to be an **independent second opinion**, and for that we only need the cuts.

Set `p_h` and `p_v` from its complex pressure, which its README says it returns. That makes bempp the backend to use when phase 2 needs complex boundary data.

**Note from its README:** open-mesh results differ from the Metal backend because of the P1 space choice. Our meshes are closed (freestanding with wall thickness), so this should not bite, but record which mode you tested.

### 4. `solve/worker.py`

```python
_WARM: set[str] = set()

def warm(backend: Backend) -> None:
    """Idempotent. Calls backend.warm() once per process per backend."""

def detach() -> None:
    """hornlab_beat_bem.detach_workers(). Leaves the worker warm."""

def shutdown() -> None:
    """hornlab_beat_bem.shutdown_workers(). Only at process exit."""

def install_handlers() -> None:
    """atexit -> detach(). SIGINT -> detach() then re-raise.
    Called once from cli.py."""
```

This module is small and it is load-bearing. Measured cold start is 12 to 15 s; a warm worker starts in about 0.01 s. At roughly 4 s per screening candidate, paying a cold start per candidate would **quadruple the cost of every search in this project**.

Rules:

- Nothing outside this module calls `shutdown_workers()`.
- `install_handlers` must survive Ctrl-C without orphaning a Julia process holding VRAM. An orphan poisons every subsequent solve in the session with an out-of-memory that looks like a mesh problem.
- Log the first and second solve wall times at `INFO` on every run. **If the second is not dramatically faster, the worker is not being reused**, and that is a bug worth catching in the first minute rather than the third hour.

### 4b. `solve/traces.py` : boundary data capture and exact field recovery

Promoted from a fork to a build item after the neural-operator research pass. Every boundary-centric surrogate method in the literature trains on **boundary solutions**; far-field polars alone cannot train any of them, and traces cannot be recovered after a solve is thrown away. See `11_PHASE2_SURROGATE.md` sections 5 and 7.

```python
def capture_traces(mesh: MeshResult, spec: SolveSpec, backend_cfg) -> dict | None:
    """Enable the backend's surface_traces option and return
    {'points': (n,3), 'normals': (n,3), 'pressure': (nf,n) complex,
     'neumann': (nf,n) complex, 'ordering': 'node'|'element'}
    or None if the backend cannot produce them.

    Shape and semantics come from task 02's C2b answer. Do not guess."""


def field_from_traces(traces: dict, points_m: np.ndarray,
                      freqs_hz: np.ndarray) -> np.ndarray:
    """Exact exterior boundary-integral evaluation. Wraps
    hornlab_bempp_bem.evaluate_exterior_from_traces.

    THIS STEP IS EXACT AND IS NEVER LEARNED. It is how a learned
    Dirichlet-to-Neumann map becomes a polar in phase 2, and it is how we
    will check that such a map is producing physically valid boundary data.
    """
```

Two requirements:

1. **Trace capture is off by default and sampled.** The pipeline enables it for 1 design in 20, configurable. Traces are large; task 02's C2b measured how large. Never capture for every candidate in a search.
2. **`field_from_traces` must reproduce the solver's own far field.** Solve one design normally, capture its traces, recover the field at the same observation points, and compare. Agreement to a small fraction of a dB proves the recovery path is correct, and it is the only thing that makes a learned-backend integration testable later. Add it as test 19.

If task 02 reports C2b as unavailable, write both functions as stubs that raise a clear `NotImplementedError` naming `TOOLCHAIN.md`, and say so in your report. Do not fake traces.

### 5. `solve/cache.py`

```python
def key(design_hash: str, mesh_hash: str, solve_hash: str) -> str:
    return f"{design_hash}-{mesh_hash}-{solve_hash}"

def lookup(k: str, root: Path) -> Response | None:
    """Hit requires status.json with ok: true. Loads response.npz."""

def store(k: str, root: Path, resp: Response, status: dict) -> None: ...
```

Copy, never symlink: symlinks on Windows need elevation and fail in confusing ways. Store `response.npz` with keys exactly matching `Response` field names, so `save`/`load` is mechanical and testable.

---

## Tests

**Offline, no solver needed** (`tests/test_solve_base.py`, `test_solve_cache.py`):

1. `arc_angles_deg(73)` is ascending, spans exactly -90 to +90, has 73 entries, and `angles[36] == 0.0` exactly.
2. `arc_angles_deg(72)` raises.
3. `get_backend("nonsense")` raises `BackendUnavailableError`.
4. `cache.key` is stable across processes (subprocess comparison).
5. A stored `ok: true` response is a hit; `ok: false` is a miss.
6. Changing one frequency by 0.01 Hz changes `SolveSpec.hash()` and causes a miss.
7. Changing `distance_m` or `angle_count` causes a miss.
8. `store` then `lookup` round-trips every array bit-identically, including complex dtypes and `None` fields.

**With a fake backend** (`tests/test_solve_fake.py`): write a `FakeBackend` implementing the protocol and returning the `fake_response` fixture. This proves the protocol is actually usable before a real solve exists.

9. `FakeBackend` satisfies `isinstance(fb, Backend)` under `runtime_checkable`, or passes an explicit attribute check.
10. `_to_response`'s sanity assertions fire: feed deliberately broken arrays (wrong shape, a NaN, mismatched on-axis values) and assert each raises with a readable message.

**Solver-gated** (`@requires_beat @pytest.mark.slow`, `tests/test_solve_beat.py`):

11. Solve the seed mesh at 3 frequencies and assert a `Response` with the right shapes, no NaN, and `n_dof` populated.
12. **Symmetry sanity, free and strong:** the seed design is mirror-symmetric, so `|spl_h_db(+theta) - spl_h_db(-theta)| < 0.05 dB` at every angle and frequency. Report the measured maximum. **This number is the project's noise floor** and `09_CHECKPOINTS.md` uses it.
13. **Idempotence:** solve twice, assert agreement, and **report the measured disagreement as a number.** GPU reductions are not associative, so bit-identical is not expected. At 1e-6 dB, ignore it. At 1e-2 dB, CMA-ES cannot distinguish a real improvement from noise and the senior agent must know.
14. Warm worker: first solve, second solve, assert the second is at least 3x faster. Paste both times.
15. Symmetry flag mismatch: solve a quarter mesh with `native_symmetry_plane=None` and assert the result differs substantially from the correct pairing. **Report how wrong it looks**, so everyone can recognize the failure mode.
16. `n_dof` from the solver is within 15% of `mesh/sizing.estimate_dofs`. If not, the `dof_per_triangle` calibration in the config is stale: report it rather than adjusting the test.

**Cross-check** (`@requires_bempp @pytest.mark.crosscheck`, `tests/test_solve_crosscheck.py`):

17. Solve the **same mesh** at 5 frequencies with `beat_cuda` and `bempp_cpu`. Report the per-frequency maximum difference in normalized dB across the horizontal cut, as a table.

**Trace round trip** (`tests/test_solve_traces.py`, `@requires_beat @pytest.mark.slow`):

19. Solve one design normally. Capture its traces. Recover the field at the **same** observation points with `field_from_traces`. Assert agreement to under 0.1 dB and **paste the measured maximum difference.**

Test 19 is the gate on the whole phase-2 learned-backend direction. If the exact boundary integral cannot reproduce the solver's own far field from its own traces, then no learned boundary map can be turned into a polar, and `11_PHASE2_SURROGATE.md` section 5 is unreachable. It costs one extra solve to find out.

Test 17 is the strongest verification available anywhere in this project: two independently implemented solvers, in different languages, on the same mesh. Agreement within a few tenths of a dB means both are very likely right. Disagreement is a finding, not a test failure, and it goes to the senior agent with the numbers. **Do not tune anything to make it agree.**

---

## Checkpoint CP-3

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_solve_base.py tests/test_solve_cache.py tests/test_solve_fake.py -v
.\.venv\Scripts\python.exe -m pytest tests/test_solve_beat.py -v -m slow
.\.venv\Scripts\python.exe -m pytest tests/test_solve_crosscheck.py -v -m crosscheck
```

Paste all three, plus:

1. **The step-0 discovery report**, both backends, all eight numbered answers, and the interface difference list.
2. The exact `SolveConfig` repr from a successful solve, copy-pasteable.
3. The measured symmetry asymmetry (test 12), as one number in dB.
4. The measured idempotence disagreement (test 13), as one number in dB.
5. Cold, warm and post-detach solve times (test 14).
6. The cross-check table (test 17), or an explicit note that bempp is unavailable and why.
7. `n_dof` reported by the solver next to the estimate (test 16).
8. The trace round-trip difference (test 19), as one number in dB, plus the trace array shapes, dtypes and the disk size for one design.

**CP-3 passes when:** the offline tests pass with nothing installed, a real solve returns a valid `Response`, the symmetry asymmetry is under 0.1 dB, and the warm worker demonstrably works.

### CP-3a: what the senior agent checks

**That the pressure we extract is at the angles we asked for, in the order we asked for.** Nothing downstream can detect a reversed arc: a mirrored polar looks completely plausible. Two checks, from the pasted numbers:

- the on-axis sample of the H cut and the V cut are the same physical point and must agree to 1e-6 dB
- a deliberately asymmetric design (set `rot_deg` non-zero, or use different H and V coverage) must produce an H cut whose asymmetry has the **sign** you would predict by hand

Add that second one as test 18 and paste the result.

---

## Forks

| Fork | Difficulty | Value | Notes |
|---|---|---|---|
| **Rayleigh-integral pre-screen** | medium | **highest throughput win** | An FFT of the mouth aperture is roughly 100x cheaper than BEM and correlates well above the mouth cutoff. Reject obviously bad candidates for free, BEM only the survivors. The code exists in spirit as the `far_field` function from the earlier tiling study. Implement as a third `Backend` named `rayleigh`, so it drops into the same protocol and the same cache. |
| `solve_channel_basis` for multi-driver | medium | high later | bempp exposes `Channel`, `Crossover`, `solve_channel_basis`, and WG has a `multi_channel` result kind. This is the path to per-cell FIR steering and to the shared-aperture steerable source from the project docs. |
| ~~`surface_traces` capture~~ | | | **Promoted to build item 4b.** |
| ~~`evaluate_exterior_from_traces`~~ | | | **Promoted to build item 4b.** |
| **A learned Dirichlet-to-Neumann `Backend`** | high | **high later** | The `Backend` protocol exists so a trained operator network can be a fourth implementation: same mesh, same exact boundary integral downstream, only the matrix solve learned. This is the closest thing in the plan to Collin's literal proposal, and it is the phase-2 integration that fails loudly rather than quietly. `11_PHASE2_SURROGATE.md` section 5. |
| Reduced-order model across frequency | high | high later | Every frequency is a fresh matrix. A frequency-sweep ROM could turn a 25-point verify sweep into 5 solves plus interpolation. Real research, not a weekend. |
| Warm-start GMRES from the previous candidate | medium | medium | The backend is iterative (GMRES at `1e-5`, 51 to 119 iterations measured), so a good initial guess from a nearby design could cut iterations materially. CMA-ES generates nearby designs by construction. Worth a measurement. |
