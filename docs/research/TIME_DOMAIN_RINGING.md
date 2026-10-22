# Time-domain behaviour (ringing, internal reflections, waterfalls): findings and integration design

Date 2026-10-22. Status: **research note + proposed stage-2 design; not implemented.** Circle back after the
typology work (`docs/TYPOLOGY_PLAN.md`), or earlier if a finalist needs it.

## 1. The question

Good polar and directivity plots do not guarantee a good-sounding horn. Horns can ring: energy reflects at the
mouth and throat, higher-order modes (HOMs) bounce across the throat region, and diffraction from the mouth edge
arrives late. Can hornlab-search see this, and where should it sit: inside the search, or as a second stage on the
best designs?

## 2. What the current pipeline can and cannot see

| Phenomenon | Visible to our BEM? | Why |
|---|---|---|
| Mouth reflections (finite horn, standing waves throat <-> mouth) | **Yes** | linear 3-D frequency-domain BEM on the real geometry; the complex pressure contains them |
| Higher-order modes in the throat / body (cross modes, "sound bouncing inside") | **Yes** | full 3-D surface solve, not a 1-D Webster model; `f11` and multilobe counters already exist in `MetricSet.scalars` |
| Diffraction at the mouth edge and the outer shell | **Yes** | the mesh is a free-standing horn with its outer shell |
| Compression-chamber / phase-plug behaviour inside the driver | **No** | the source is a uniform-velocity spherical cap at the throat (`hornlab_mesher/builders/point_grid_sources.py`, `_source_cap_radius`); driver internals are not modelled. Phase plugs and throat "inner waveguides" are a driver-side problem we cannot score |
| Wall resonance, damping, air absorption | **No** | rigid, lossless walls; no viscothermal losses |
| Non-linearity | **No** | linear model |

**The data needed for a waterfall is complex pressure on a dense, uniform frequency grid.** We already store
complex `p_h`, `p_v`, `p_balloon` and complex `z_throat` per design (`designs/<hash>/response.npz`), but only at
12 log-spaced frequencies in screen mode (`config.py` `FREQ_GRIDS`: screen 12, verify 25, final 36). That grid is
far too sparse for time-domain analysis: an impulse response over a T-second window needs a frequency step
Δf ≈ 1/T, and the phase must change by much less than 2π between samples. A 0.2 m horn has a throat-mouth round
trip of about 1.2 ms, so its reflections need Δf well under 800 Hz just to avoid aliasing, and an 8 ms view needs
roughly 25–60 Hz steps.

## 3. Tools that already exist

| Tool | What it offers | Caveat |
|---|---|---|
| `hornlab_plots.complex_analysis.plot_impulse_response` (Magnus) | Hermitian extension + IFFT of H(f) at chosen angles, 8 ms window, "useful for spotting throat ringing and mouth reflections" (its docstring) | interpolates magnitude and phase from the solved grid onto a uniform one (`complex_analysis.py:363-409`); on our 12-point grid this smooths resonances away, so it is **only valid on a dense grid** |
| `hornlab_plots.complex_analysis.plot_group_delay`, `derived.save_group_delay_plot` | group delay in cycles, propagation delay re-added | same sampling requirement |
| `hornlab_plots.charts.save_impedance_plot` | throat impedance curves | dense grid needed to see the reflection ripple |
| `hornlab_search/solve/phasor.py` | time-convention conversion (ours exp(−iωt), Boundary Lab exp(+iωt)) | needed before comparing any phase with Boundary Lab |
| Boundary Lab 0.5.0 | no time-domain / waterfall feature found in our research notes (`docs/BOUNDARY_LAB_0.5_RESEARCH.md`) | unverified; re-check BL docs before relying on it |

## 4. Cheap proxies available now (no extra solves)

These go into the search loop or the report at zero GPU cost, and are already part of the typology plan (s6):

1. **Throat-impedance ripple** above the loading frequency (`z_throat`, complex). Mouth reflections show up as a
   periodic ripple in Re z and Im z with period ≈ c / (2·L_eff). On 12 log points this is coarse: it flags gross
   reflection problems, not fine ones.
2. **`f11`** (first cross-mode cut-on) and the **multilobe counters** (`n_multilobe_h/v`), already computed.
3. **Polar ripple** (already in J) catches lobing from HOMs.

None of these replace a real impulse response; they are screening signals.

## 5. Proposed stage 2: `hornlab-search transient` (second step on finalists)

Ringing analysis is about 20× the solve cost of a screen evaluation, so it belongs **after** the search, on the top
designs of a `compare`-tier campaign, and its metrics then re-rank the finalists.

- **Command**: `hornlab-search transient --run <dir> --top N [--df 25] [--fmin 200] [--fmax <dof-cap limit>]`.
- **Solve**: re-solve each finalist on a uniform grid (e.g. 200 Hz → 6 kHz at 25 Hz ≈ 230 frequencies) at the
  verify mesh. Measured screen cost today is about 0.32 s per frequency for a ~1,400-dof sculpt quarter mesh and about
  0.9 s for a ~3,000-dof OSSE, so roughly **1.5–4 minutes per design** on the RTX 4060. The upper frequency stays
  limited by the 8 GB dof cap (TOOLCHAIN M3).
- **Code needed**: an explicit frequency list for one evaluation (today `mode_freqs` only knows the three frozen
  grids), plus a pure-numpy analysis module; plotting via Magnus's `plot_impulse_response` / `plot_group_delay`
  (valid once the grid is dense).
- **Outputs per design** (on-axis, 30°, 60°, H and V): impulse response, step response, **cumulative spectral decay
  (waterfall)** from the windowed impulse response, group delay, dense throat impedance.
- **Metrics** (report-only first, then optionally a re-ranking key):
  - late-energy ratio: energy after the direct arrival + 1 ms, over total;
  - decay time to −30 dB per third-octave band (from the CSD ridges);
  - impedance ripple depth above the loading frequency (dense);
  - group-delay excess over the smooth trend.
- **Verification before trusting it**: (a) a closed-form check: an analytic delayed impulse (pure delay) must give a
  flat group delay and a clean impulse; (b) a pulsating sphere (already in `selftest --analytic`) must show no
  ringing; (c) refine Δf (25 → 12.5 Hz) on one design and confirm the metrics converge.

## 6. Recommendation

- **Now**: keep the cheap proxies (s4) in the typology plan; report them per design. No change to the plan's scope.
- **Next, after the typology campaign (V7)**: implement stage 2 as an optional lane D (about half a day of code plus
  ~10–30 GPU minutes for 5–10 finalists). Use it to choose between finalists whose directivity scores are close.
- **Not in the search loop**: 20× cost per evaluation, and a scalar "ringing" objective needs the verification in s5
  first.
- **Out of scope for this tool**: driver-internal phase-plug design. That needs a model of the compression chamber
  and is a separate problem (a different solver set-up, not a horn-geometry search).
