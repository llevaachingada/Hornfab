# Beta readiness pass, 2026-10-22/23 (`docs/HANDOFF_BETA.md` items A-G)

Machine: RTX 4060 Laptop 8 GB, Windows 11. Every GPU step ran alone, with this project's julia and BEAT
`worker_host` processes cleared before and after (`search/hygiene.py`); VRAM recorded.

## A. Dependencies and upstream

`doctor`: 10/10 PASS before this pass (incl. `pinned-shas`).

| Package (dist) | Version | Pin (pyproject / TOOLCHAIN) | Installed (`direct_url.json`) | Upstream HEAD (m3gnus) |
|---|---|---|---|---|
| hornlab-waveguide-mesher | 0.2.4 | b922e807 | b922e807a5cf10cf732c4557ec0b9b495762afd7 | 4573bc90 (**57 newer commits**) |
| hornlab-beat-bem | 0.2.0 | 38544d21 | 38544d214ba2e8a4977bb82170d2fb4a3f9fa8b0 | = pin |
| hornlab-bempp-bem | 0.2.0 | 8e691060 | 8e6910602ece9abb2e9ce0db7a637f4bedf17f53 | = pin |
| hornlab-plots | 0.1.3 | 9e4a6d0d | 9e4a6d0dd2ccb6e735dd00233dccccb50d12ed44 | = pin |

Mesher upstream since the pin (not bumped; owner decision 2026-10-22: **keep the pin for the beta**):
ATH .cfg import compatibility; new native geometry options (source bodies, roundovers, cubic throat adapters,
terminating arcs, phase-plug passages; new config keys we never set); test-fixture encoding fixes; and
**FREEFORM corner work** (`967db56` joins / Bezier handles, `d740c28` corner topology / density / build cost,
`68ed646` shared crease edges). Signatures we use are unchanged at HEAD: `profile_formulas.profile_points(params,
n_axial, phi=0.0)`, `freeform.build_freeform_geometry(params)`, `profile_sampling.build_point_grid(params, *,
defer_osse_offset_repair=False)`; the FREEFORM outer-shell guard (`freeform._validate_freeform_config` ->
`surface_curvature_report(wall_thickness_mm, margin=0.4)`) is unchanged. Our generated H/V horns use FREEFORM
rounded-rectangle corners, so the corner commits are a post-beta bump candidate with its own verification ladder.
Our own topology check (`mesh/topology.py`: no open / non-manifold edges off the symmetry planes) passes on today's
meshes. Guard test: `tests/test_mesh_semipublic_api.py`.

## B. Data integrity

- Backup: `dataset_backup_20261022\` (834.4 MB, git-excluded).
- `dataset verify`: OK, 6055 records re-read, 0 bad, 0 bad arrays.
- `dataset stats`: 6055 records (5458 ok, 597 failed), 13 shards, 834.4 MB; OSSE 2274, R-OSSE 217, ICW 1024,
  FREEFORM 2540; duplicate designs 226; backend beat_cuda only; lib_sha b922e807a5+38544d214b on all records.
- R8 (brief provenance): records now carry an optional, additive `provenance` block {config, brief, brief_hash,
  generator {name, spec, knobs, brief, brief_hash}} (`dataset/record.py::build_record`,
  `search/evaluate.py::_record_provenance`); older records lack it. The surrogate recomputes every objective
  from the target-free metric curves with the CURRENT target (`surrogate/train.py:55-71`), so mixed-brief data
  does not corrupt training. Tests: `tests/test_dataset_provenance.py`.
- `surrogate train/propose/round` on a typology (`generator:`) config is refused up front with a clear message
  (knobs are not stored as record params): `surrogate/features.py::require_surrogate_config`,
  `tests/test_surrogate_generator_refusal.py`. Before: a late `searchable key 'L_mm' is missing` error.

## C. Physics audit

1. **Throat impedance.** `z_throat = impedance * (-i omega) / (rho c)` (`solve/beat.py:222-232`), where beat's
   `impedance` is the area-weighted mean pressure over the source-tagged cap per unit normal acceleration
   (`hornlab_beat_bem/sweep.py:420`). With uniform normal velocity u on the cap, z = p_mean / (rho c u): a
   specific impedance, no extra area factor. Consistent with V5 (conical matched (kx0)^2 / (1 + (kx0)^2)).
   Convention exp(-i omega t): mass loading has NEGATIVE imaginary part; only Re z enters J.
2. **Mesh resolution above 2.5 kHz (GPU, measured).** Same design, epw 6 vs epw 8, screen mode, 12 frequencies
   500-5500 Hz, dof cap raised to 8900 for the measurement only, separate scratch dataset/cache:

   | Design | dofs epw6 / epw8 | max dB diff (DI / on-axis / ripple H,V) | max beamwidth diff H / V | J epw6 / epw8 |
   |---|---|---|---|---|
   | `osse_axi` seed | 588 / 1013 | **0.124** / **0.107** / 0.020, 0.023 | 0.80 / 0.90 deg | 19.990 / 19.807 (dislope 1.667 / 1.335) |
   | `perturbed_osse_hv` screen best (dbb2cf700679) | 997 / 1722 | 0.022 / 0.050 / 0.010, 0.012 | 0.31 / 0.38 deg | 11.221 / 11.243 |

   The H/V design passes (<= 0.1 dB, <= 1 deg). The axi seed misses on DI and on-axis by ~0.02 dB, and its DI-slope
   term moves 0.33, comparable to the gaps between the axi screen leaders. Owner decision (2026-10-22): **axi
   typology configs raised to epw 8** (same cost there: 5.3 vs 5.5 s per candidate); H/V configs stay at epw 6
   (epw 8 would be ~4x solve time: 5.2 -> 20.3 s). The axi screen campaign is re-run at epw 8 (below).
   Reproducibility: the epw-6 re-solve of the H/V best gave J 11.221, identical to the screen run.
   One `ConnectionResetError` from the worker host on the first H/V epw-6 attempt did not reproduce from a clean
   state (CLAUDE.md GPU rule 7): not a finding.
3. **Band limit.** Every brief sets `band_hi_hz: 5500` (8 GB dof cap, `TOOLCHAIN.md`). Nothing above 5.5 kHz is
   solved or scored in screen mode. HF horns cannot be judged above that.
4. **Boundary conditions.** Free-standing horn with an outer shell; no baffle, no enclosure; rigid lossless walls;
   no air absorption. The mesher's `infinite-baffle` mode (`families.MODES`) exists but is not enabled: a future
   brief option.
5. **Source model.** Rigid, uniform-velocity spherical cap at the throat (mesher default cap). Phase plugs and
   compression chambers are out of scope. Brief `source.cap: auto` is NOT applied (FREEFORM keys do not expose the
   cap); the cap is identical for every design in a campaign.
6. **Objective caveats.** J is a hand-weighted sum of terms with different units; beamwidth is a -6.02 dB
   threshold crossing (kinks, not smooth); `load` uses an arbitrary z_min = 0.7; 12 log-spaced frequencies cannot
   see narrow resonances (see `docs/research/TIME_DOMAIN_RINGING.md`).
7. **Shell.** Generated (typology) horns: 3 mm shell (`design/generators/registry.py:199`; the FREEFORM curvature
   guard requires thickness x concave curvature < 0.4). Native configs: mesher default 6 mm for free-standing
   horns (`hornlab_mesher/config_builder.py:837`). The brief envelope check uses the outer mesh bbox, shell included.
   The doctor's "outer wall clearance ... holding at 19.056 mm" warning concerns the outer shell only; the mesher
   states the acoustic (inner) surface is unaffected.
