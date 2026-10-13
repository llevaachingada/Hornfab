# 02 TASK ENV

**Wave 0, step 1. Serial. Nothing else starts until CP-0 passes.**

Owner of: `TOOLCHAIN.md`. Writes no Python beyond throwaway probe scripts.
Reads: `01_CONTRACTS.md`

You install the stack, prove it works, and **measure the seven numbers every downstream decision depends on.** The previous version of this plan guessed at several of them and guessed wrong. Measure, do not assume, and record `UNRESOLVED` rather than inventing a value.

---

## Target machine

| | |
|---|---|
| GPU | NVIDIA RTX 4070 Laptop, **8 GB GDDR6**, 128-bit, 256 GB/s, Ada Lovelace |
| Driver | needs CUDA 12.x. Boundary Lab requires Maxwell or newer, so Ada is fine. |
| OS | record what it actually is |

**Do not install a CUDA Toolkit by hand.** Julia's `CUDA.jl` ships its own runtime via artifacts. You need a recent NVIDIA **driver** and nothing else from NVIDIA. A hand-installed toolkit is a common source of version conflicts that are hard to diagnose.

---

## Build

### Step 1: Starting state

```powershell
nvidia-smi
python --version
git --version
```

**Gate:** `nvidia-smi` lists an RTX 4070 and CUDA 12.0 or higher. If not, stop and report.

### Step 2: Python 3.11 or 3.12, and a venv

Contracts require `>=3.11,<3.14`.

```powershell
winget install Python.Python.3.12
mkdir C:\dev\hornlab-search
cd C:\dev\hornlab-search
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
```

Record the **absolute interpreter path**. Every later command uses it explicitly, never a bare `python`.

### Step 3: Julia

`hornlab-beat-bem` requires Julia 1.10 or later on `PATH`, settable via `HORNLAB_BEAT_JULIA`, or provisioned automatically. Its README names Julia 1.12.7 as the portable download.

```powershell
winget install Julia.Juliaup
juliaup add 1.12
juliaup default 1.12
julia --version
where julia
```

Record the version and absolute path.

### Step 4: Install the HornLab stack

**Read each repo's README before running anything.** They are authoritative and may have changed.

```powershell
$P = "C:\dev\hornlab-search\.venv\Scripts\python.exe"
& $P -m pip install "hornlab-waveguide-mesher @ git+https://github.com/m3gnus/hornlab-waveguide-mesher.git"
& $P -m pip install "hornlab-beat-bem @ git+https://github.com/m3gnus/hornlab-beat-bem.git"
& $P -m pip install "hornlab-plots @ git+https://github.com/m3gnus/hornlab-plots.git"
& $P -m pip install "hornlab-bempp-bem @ git+https://github.com/m3gnus/hornlab-bempp-bem.git"
```

`hornlab-bempp-bem` needs an OpenCL runtime or falls back to Numba. On Windows the Intel CPU OpenCL runtime works, including on AMD parts. If it will not install, that is acceptable: the cross-check becomes optional and you record it as unavailable. **Do not spend more than two attempts on it.**

**Now pin every one of them by commit SHA:**

```powershell
& $P -m pip freeze | Select-String hornlab
```

Record the full 40-character SHA for each. `01_CONTRACTS.md` requires `pyproject.toml` and every dataset record to carry these, because a dataset built across two solver commits has inconsistent labels.

### Step 5: Provision the GPU backend

```powershell
& $P -m hornlab_beat_bem.provision --if-nvidia-gpu
& $P -c "import hornlab_beat_bem as b; print(b.beat_engine_status()); print(b.beat_backend_statuses())"
& $P -c "import hornlab_beat_bem as b; print(b.capability_report())"
```

Provisioning downloads and precompiles the Julia environment. **It takes a long time and CUDA's first run pulls several GB.** Do not interrupt it, do not run it twice concurrently.

**Gate:** `beat_backend_statuses()` reports `cuda` as functional. If not, the whole plan still runs on `cpu`, just slower. Record which one works and why, and move on.

### Step 6: First mesh and first solve

Use a shipped example from the mesher.

```powershell
& $P -m pip show -f hornlab-waveguide-mesher          # find the examples directory
hornlab-waveguide <examples>\osse-freestanding.toml -o C:\dev\scratch\osse.msh
```

Then solve it:

```python
import hornlab_beat_bem as beat, time
cfg = beat.SolveConfig(
    beat_backend="cuda",
    native_symmetry_plane=None,            # match the example's quadrants
    mesh_scale=1.0,                        # mesher writes METRES
    observation=beat.ObservationConfig(distance_m=2.0, angle_count=37),
)
t = time.time(); r = beat.solve_frequencies(r"C:\dev\scratch\osse.msh", [1000.0], cfg)
print("first solve", time.time() - t)
t = time.time(); r = beat.solve_frequencies(r"C:\dev\scratch\osse.msh", [1000.0], cfg)
print("second solve (warm worker)", time.time() - t)
print({k: getattr(r, k, None) for k in dir(r) if not k.startswith("_")})
beat.detach_workers()
```

**Gate:** a result object comes back, and the second solve is dramatically faster than the first.

**Report the full `dir(r)` listing and the type, dtype and shape of every array attribute.** This is the Response schema that task 05 adapts to. The README names `spl_db`, `directivity_db` (alias `spl_norm_db`), `directivity_reference_index`, `directivity_reference_deg`, `cancelled`, `requested_frequency_count`, `is_partial`, `native_diagnostics` (with `metal_pipeline` and `p1_dof_count`), and an impedance pair described as legacy-scaled `[Re(F)/2, -Im(F)/2]`. **Confirm each against the real object** and report anything extra, especially whether **complex pressure** is exposed.

While it runs, in a second terminal:

```powershell
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv -l 1
```

### Step 7: The seven measurements

These are the deliverable. Everything downstream is sized by them.

#### M1. The dof calibration table

Mesh the same design at several `mouth_res_mm` values and record what comes out.

| `mouth_res_mm` | `throat_res_mm` | triangles in the `.msh` | `p1_dof_count` from the solve | dof / triangle ratio |
|---|---|---|---|---|
| 12 | 6 | | | |
| 8 | 4 | | | |
| 6 | 3 | | | |
| 4 | 2 | | | |
| 3 | 1.5 | | | |

Do this for `quadrants = "1234"` and `quadrants = "1"`. `01_CONTRACTS.md` assumes `dof ~= tri/2` as an initial guess only; **this table replaces it** and `mesh/sizing.py` uses the measured ratio.

#### M2. VRAM versus dofs

Peak `nvidia-smi memory.used` during a single-frequency solve, at roughly 2,000, 6,000, 12,000 and 20,000 dofs.

| dofs | predicted `8N^2` (MB) | measured peak (MB) | ratio |
|---|---|---|---|
| | | | |

The prediction comes from the two datapoints in `hornlab-beat-bem`'s README (31 MB at 1,974 dofs, 3,337 MB at 20,422 dofs), both of which are exactly `8N^2` bytes. **If the measurements match, the dof caps in `01_CONTRACTS.md` stand. If they are much lower, the path is not dense and the caps can rise.** Say which.

#### M3. Throughput

| Case | dofs | frequencies | wall seconds |
|---|---|---|---|
| mesh only (no solve) | | | |
| screen-like | ~8,000 | 12 | |
| verify-like | ~16,000 | 25 | |

Report **seconds per candidate** and **candidates per hour** for the screen case, including meshing. `01_CONTRACTS.md` infers 4 to 8 s per screening candidate from a 256 GB/s bandwidth model; your measurement is the real number and it decides what kind of search is affordable.

Also report **what fraction of a screening candidate is meshing versus solving.** If meshing dominates at screening resolution, that changes where optimization effort goes.

#### M4. CUDA versus CPU

Same mesh, same frequencies, `beat_backend="cuda"` then `"cpu"`. Report both and the ratio. Then force CPU via `HORNLAB_BEAT_FORCE_CPU=1` and confirm it takes effect.

#### M5. Worker warmth

First solve, second solve, and a solve after `detach_workers()`. Three numbers. The README claims about 0.01 s for a warm start; confirm.

#### M6. Symmetry pairing

Solve the **same physical horn** two ways:

- full mesh (`quadrants="1234"`) with `native_symmetry_plane=None`
- quarter mesh (`quadrants="1"`) with `native_symmetry_plane="yz+xz"`

**Report the maximum difference in dB across all angles and frequencies.** This is the single most valuable number in this task: it simultaneously validates the quadrant-to-flag mapping, the mesher, the solver's symmetry handling, and our understanding of the frame. Then deliberately **mismatch** them (quarter mesh, no flag) and report how wrong it gets, so everyone can see what the failure looks like.

#### M7. `max_triangles`

Build a mesh with `max_triangles` set well above the 18,000 default, aiming for roughly 70,000 full-domain-equivalent triangles, with `allow_large_mesh: False`. **Does it succeed, or is there a second hard check?** Report the exact error if it refuses.

### Step 8: Three capability checks

Answer each with evidence, or `UNRESOLVED`.

**C1. Balloon / DI grid.** The beat-bem README says "spherical balloon/DI grids (theta-major) are also supported". Find the `ObservationConfig` or `SolveConfig` field that enables it. Report the field name, its values, the shape of the returned array, and the direction convention: is the grid theta-major, what are theta and phi relative to +Z, and is it a full sphere or a hemisphere? **If you cannot enable a balloon, say so**: metrics fall back to a labeled cuts estimate and no checkpoint may pass on it.

**C2. Complex pressure.** Does either backend expose complex pressure at the observation points, not just SPL in dB? `hornlab-bempp-bem`'s README says its `SolveResult` carries complex pressure. Check beat-bem too. Metrics do not need it; the phase-2 surrogate and interference work do.

**C2b. Boundary surface traces.** `hornlab-beat-bem`'s `SolveConfig` lists a `surface_traces` option. Enable it on a small mesh and report: what comes back (pressure, normal derivative, both?), its shape and dtype, whether it is ordered by node or by element, and **the file size for one design at screening resolution**. Also check `hornlab_bempp_bem.evaluate_exterior_from_traces`: what does it take and what does it return?

This gates the entire phase-2 surrogate direction. Every boundary-centric neural operator method in the literature trains on boundary solutions; far-field polars alone cannot train any of them, and traces cannot be recovered after the fact. A clear "no" is important to know now.

**C3. Non-rigid boundary conditions.** Does either solver accept an **impedance or admittance boundary condition** on a tagged region, rather than only rigid walls and velocity sources? Search both packages for `impedance`, `admittance`, `Robin`, `absorb`, `Y`, `beta`. This is the capability gate on the metamaterial-termination and graded-wall-admittance ideas, which are among the highest-payoff bets in the project docs. A clear "no" is a valuable answer: it tells us those ideas need a different tool.

**C4. The mesher's structured surface grid.** `hornlab_mesher`'s config exposes `angular_segments` (default 64) and `length_segments` (default 32) as the sampling of the fitted surface, plus `preserve_grid`, and its internal modules are named `profiles.build_point_grid` and `geometry.PointGridHornGeometry`.

Report whether that `angular x length` point grid is **reachable through the public API**, or only through internals that `docs/public-api.md` does not cover. Give the array shape and the ordering, and say whether the azimuthal axis wraps.

Why it matters enough to check on day one: a Fourier neural operator needs a structured grid with meaningful periodicity, and an unstructured triangle soup does not have one. B-FNO's 3D cases had to reshape boundary data into 2D arrays by hand. If this grid is accessible, phase 2's input representation is settled for free by the geometry layer we were already using. If it is not, it is a one-line feature request to Collin rather than a research problem.

**C5. The driver excitation.** How is the source on tag 2 (`SD1D1001`) actually defined? Uniform normal velocity, uniform pressure, a piston, something else? Is it frequency-dependent? Can the distribution be prescribed rather than taken as a default?

This is the frequency-encoding channel for any phase-2 surrogate, per B-FNO's finding that frequency must enter through the boundary source field rather than as a scalar. Record the answer; `01_CONTRACTS.md` section 13 puts it on every dataset row.

### Step 9: Write `TOOLCHAIN.md`

Every line filled. `UNRESOLVED` is acceptable; blank or invented is not.

```markdown
# TOOLCHAIN
Recorded by task 02 on <date>.

## Machine
OS / CPU / RAM / GPU / NVIDIA driver / CUDA version:

## Interpreters
Python:  <abs path>  <version>
Julia:   <abs path>  <version>
venv:    <abs path>

## Pinned dependencies (40-char SHAs)
hornlab-waveguide-mesher:
hornlab-beat-bem:
hornlab-plots:
hornlab-bempp-bem:            <or NOT INSTALLED, with the reason>

## Backends
beat_engine_status():
beat_backend_statuses():
Working default:              <cuda | cpu>   because:
bempp available:              <yes | no>

## Response object schema
<full dir(r) listing, with dtype and shape of every array attribute>
Complex pressure exposed:     <yes, as <attr> | no>

## M1 dof calibration
<the table, for quadrants 1234 and 1>
Measured dof/triangle ratio:

## M2 VRAM
<the table>
Verdict: <8N^2 dense confirmed | lower, path is not dense>
dof caps in force:  screen <N>  verify <N>  final <N>

## M3 throughput
seconds per screening candidate:
candidates per hour:
mesh fraction of that:

## M4 cuda vs cpu
cuda:  <s>   cpu:  <s>   ratio:

## M5 worker warmth
first / second / after detach:

## M6 symmetry pairing
full vs quarter max difference:            <dB>
deliberately mismatched max difference:    <dB>

## M7 max_triangles
Largest mesh built with allow_large_mesh=False:   <triangles>
Error if refused:

## C1 balloon grid
Field name and values:
Returned shape and convention:
Status: <AVAILABLE | UNRESOLVED>

## C2 complex pressure
beat:   <yes/no, attr>
bempp:  <yes/no, attr>

## C2b boundary surface traces
beat surface_traces:      <available? field name, what it returns, shape, dtype>
Ordering:                 <by node | by element>
Size per design at screen resolution:   <MB>
bempp evaluate_exterior_from_traces:    <signature, inputs, outputs>
Status: <AVAILABLE | UNRESOLVED>

## C3 impedance boundary conditions
beat:   <yes, how | no>
bempp:  <yes, how | no>
Evidence:

## C4 structured surface grid
Reachable through public API:   <yes, how | internals only | no>
Array shape and ordering:
Azimuthal axis wraps:           <yes | no>

## C5 driver excitation
Definition on tag SD1D1001:     <uniform normal velocity | pressure | other>
Frequency-dependent:            <yes | no>
Can the distribution be prescribed:  <yes, how | no>

## Mesher examples directory
<abs path>

## Anything surprising
```

---

## Checkpoint CP-0

Paste, unedited:

1. `nvidia-smi`, `julia --version`, `python --version`.
2. `pip freeze | grep hornlab` with full SHAs.
3. `beat_engine_status()`, `beat_backend_statuses()`, `capability_report()`.
4. The full `dir(r)` response schema with dtypes and shapes.
5. All seven measurement tables, M1 to M7.
6. The capability answers C1, C2, **C2b**, C3, **C4** and **C5**, with evidence.
7. The complete `TOOLCHAIN.md`.

**CP-0 passes when:** a mesh was built and solved on the working backend, M1 through M6 have real numbers, C1 through C5 have an answer or an explicit `UNRESOLVED`, and `TOOLCHAIN.md` has no blank fields.

**CP-0 does not require CUDA**, only a working backend and an honest record of which.

### What the senior agent checks first

**M6, the symmetry pairing.** If the full and quarter solves of the same horn do not agree to a fraction of a dB, nothing downstream is trustworthy and the cause must be found before Wave 1 starts. It is also the cheapest possible test of the mesher, the solver, the symmetry mapping and the frame convention, all at once.

---

## Forks

| Fork | Difficulty | Value | When |
|---|---|---|---|
| CPU only, skip CUDA | trivial | medium | If CUDA fights back. Everything works, screening is slower. Not a blocker. |
| Skip `hornlab-bempp-bem` | trivial | **costly** | You lose the independent cross-check, which is the strongest verification available. Try reasonably hard before giving up. |
| WSL2 instead of native Windows | medium | low to medium | Julia, CUDA and bempp are all better tested on Linux. Costs a day. Only if native Windows is genuinely broken. |
| A cloud GPU with real fp64 and 40+ GB | low | high later | Raises the dof ceiling by roughly 2.5x in each dimension. Not now; after the loop is proven and the cost per candidate is known. |
| Ask Collin about impedance BCs (C3) | trivial | **high** | He wrote these packages. One message saves a day of grepping, and if the answer is no, it tells you immediately that a whole branch of the project needs a different tool. |
