# Learning from Boundary Lab 0.5.0: implemented items and plan for the rest

Date 2026-10-22. Senior reviewer (cloud). Source study: Boundary Lab `v0.5.0` (`6c9185b`), see
`docs/BOUNDARY_LAB_0.5_RESEARCH.md`. **Ideas and maths only; no Boundary Lab code was copied** (BL is GPL-3.0-only,
this repo AGPL-3.0-or-later). The user authorized edits outside the reviewer's own paths for this work (chat,
2026-10-22); each is listed in `NOTES_FOR_SENIOR.md` with its test.

## 1. Implemented (on this PR), each tested

| # | Item | Files | What it does | Verification |
|---|---|---|---|---|
| 1 | **Pre-solve surface checks** | `hornlab_search/mesh/topology.py` (new), `mesh/build.py` (wired after read-back and on cache hits; `read_msh_summary(..., return_arrays=True)`) | Rejects meshes with open edges off the symmetry planes, non-manifold edges, or near-coincident vertices (`GeometryInvalidError` -> `invalid_geometry`), before any GPU time | `tests/test_mesh_topology.py` (synthetic case per failure class + real mesher, 5 families). Measured on real meshes (seed + random samples, 6 configs): 0 off-plane open edges, 0 non-manifold, 0 near-coincident (closest pair ~1.5 mm vs ~0.3 um tolerance) |
| 7 | **Symmetry fundamental-domain check** (silent killer 2, geometry side) | same module | A reduced mesh must lie in x >= 0 (`yz`) / y >= 0 (`xz`) within max(1e-9 m, 1e-6 x extent); violation raises `SymmetryMismatchError` (stops the run; a convention bug, not a bad candidate) | same tests; all real quarter meshes have min x = min y = 0.0 |
| 6 | **Phasor conventions in one place** | `hornlab_search/solve/phasor.py` (new) | Ours `exp(-i w t)` + unit acceleration; Boundary Lab `exp(+i w t)` + 1 m/s velocity; `convert_time_convention`, `velocity_to_acceleration_drive`, `boundary_lab_to_ours` | `tests/test_solve_phasor.py` checks against time-domain signals (numerical derivative), not against its own algebra |
| 5 | **Live runtime provenance** in `run.json` | `search/rundir.py` (`runtime_provenance`, `package_source_fingerprint`), `search/cma.py` (`"runtime"` key) | Records what the run actually ran on: Python, platform, `nvidia-smi` GPU name/driver/memory, `julia --version`, and source-content fingerprints of hornlab_beat_bem / hornlab_mesher / hornlab_bempp_bem (distinguishes modified trees sharing a commit). Best effort, never raises | `tests/test_search_provenance.py` (stable hash, edit detection, missing package) |
| 3 | **CEA-2034 subset** (report-only) | `hornlab_search/metrics/spinorama.py` (new) | Listening window (9-curve energy average) and sound-power DI via SPDI = DI - (OnAxis - LW). Early Reflections / full Sound Power from cuts are NOT computed (our cuts stop at +-90 deg) | `tests/test_metrics_spinorama.py`; cardioid check: SPDI 4.554 dB = 4.77 - 0.217 |
| 2 | **Forward beam shape** (report-only) | `hornlab_search/metrics/beam_shape.py` (new) | Fits the forward -6 dB balloon contour with a superellipse on the tangent plane: exponent `p` (2 round, ~4 rounded square) + residual | `tests/test_metrics_beam_shape.py`. Accuracy (subagent-measured): exact on a 91x72 theta-phi grid; at screen resolution (16x32 grid) p reads low by up to ~0.3 (p=4) and ~1.1 (p=8); NaN when the beam is wider than +-89 deg |
| 2+3 | Wiring | `search/evaluate.py` (`directivity_extras`, `EXTRA_SCALAR_KEYS`), `report/html.py` (one line per design) | Six scalars added to `MetricSet.scalars` (open dict; no contract change): `spdi_mean_db`, `spdi_range_db`, `lw_minus_on_axis_mean_db`, `beam_p_mean`, `beam_p_residual_pct_mean`, `beam_p_n_valid`. **Never weighted into J**; failures inside become NaN, never a failed solve | `tests/test_search_directivity_extras.py` (J unchanged with/without extras; broken input does not raise). Cost ~0.07 s per candidate (~0.6 % of a 13 s solve) |

Offline suite after these changes (cloud, mesher installed, CPU torch): **553 passed, 1 skipped, 18 deselected, exit 0**.

## 2. Not implemented: direction for the next agent (each needs a ruling first)

### Item 4. Coarse-to-fine frequency order with early rejection (largest GPU saver)
- Idea (BL `live.py::order_frequencies_for_live_plotting`): solve the band ends first, then fill the middle in
  van-der-Corput order.
- Direction: in `solve/beat.py` the CUDA path already makes one call per frequency (`per_frequency_calls`). Add an
  optional `frequency_order="coarse_first"` and a `stop_after(partial_metrics) -> bool` hook in `search/evaluate.py`:
  after K = 4 frequencies, compute a LOWER BOUND on J from the solved subset (coverage and ripple terms can only add
  over the remaining frequencies); if the bound already exceeds the current CMA generation's worst kept J by a
  margin, stop and record the candidate as **`early_rejected`** with its partial bound.
- Rulings needed (do not implement before): (a) is a partial-bound J an acceptable CMA-ES fitness (it is an
  inequality, not a value); (b) dataset policy: early-rejected rows must NOT enter `to_training_arrays` as ok
  records (new `ok=False` failure kind, or excluded). (c) Measure first: replay CP-8c ndjson offline to count how
  many candidates such a rule would have stopped and whether any eventual top-20 design would have been lost.
- Risk if done carelessly: biased search and a polluted surrogate dataset. Offline replay is mandatory.

### Item 8. Release-qualification habit
- Idea (BL release notes): a standing CPU vs CUDA agreement screen, with failed comparisons kept in the record.
- Direction: a `selftest --agreement` (or a slow/GPU-marked test) solving 2 fixed seeds (OSSE quarter, FREEFORM
  quarter) on `beat_cpu` and `beat_cuda`, reported with `hornlab-search compare`, appended to
  `docs/evidence/qualification/` per pinned-library change. Threshold: the frozen CP-7b rule (< 0.2 dB). Needs the
  GPU box; no new threshold.

## 3. Future-risk review (aggressive)

| Change | Could it bite later? | Mitigation in place |
|---|---|---|
| Topology check rejects a mesh that used to be accepted | Only genuinely broken surfaces; none in any measured family. A future mesher pin or new family (e.g. wall ports) could legitimately produce extra open edges or interfaces | Clear `GeometryInvalidError` message naming counts; real-mesher test per family fails loudly on a pin bump (`tests/test_mesh_topology.py`) |
| Check also runs on mesh-cache hits | Old cached meshes are re-read (~tens of ms) | Intended: cached entries predate the checks; no cache-key change, so solve-cache hits stay valid |
| Symmetry-domain violation stops the run | A new mesher that mirrors into -x/-y would stop searches immediately | Correct behaviour (silent killer 2); message says which plane and how far |
| New scalars in records | `to_training_arrays` `y_scalars` gains columns (NaN for older records) | Surrogate uses metric curves and `objective` only; scalars are not training targets |
| Beam-shape `p` misread as accurate | Screen balloon (512 pts) under-reads square beams | Labelled qualitative in code, report line and here; never in J |
| `run.json` gains `runtime` | Larger file; `nvidia-smi`/`julia --version` add ~1 s at run start | Read-only query at start only; never during a measurement window; best effort |
| `phasor.py` unused by solvers today | Someone "fixes" the solver sign | Module is documentation + conversion only; solvers untouched |
| Frozen plan | No plan file, contract field, gate threshold or tolerance changed | `MetricSet.scalars` is an open dict in `01_CONTRACTS.md` |

## 4. Tonight's local test plan (GPU box)
1. `git pull --ff-only origin main` after this PR merges; offline suite -> expect ~553 passed (more with beat
   installed), exit 0.
2. `hornlab-search doctor` -> 10/10.
3. GPU hygiene (CLAUDE.md), then `hornlab-search search --config examples\freeform_sculpt.yaml --budget 40`;
   `hornlab-search report runs\<dir>`. Check: (a) `run.json` has a `runtime` block with the RTX 4060, driver and
   Julia version; (b) the report shows the report-only line (SPDI, listening window, beam p) per design; (c) failure
   kinds unchanged in character (no new `invalid_geometry` flood); (d) s/candidate within ~1 % of HANDOFF 6b's run.
4. Same for `examples\osse_baseline.yaml --budget 40` (quarter OSSE, compare beam p of best vs seed).
5. Clear Julia, confirm VRAM idle, report with the numbers above.
