# Ripple program, 2026-11-20: corpus sweep, source sensitivity, HF width

Three experiments run back to back after the [handoff bundle](../../research/ripple_hf_2026-11-19/README.md).
All of it is report-only; **no score term was added or changed, and no stored `J` moved**. The one
piece of GPU work is listed with its baselines and peaks at the end.

Headline: **(1)** across 730 stored designs the fixed-angle residual is *not* redundant with `rip`
(the 24-design sample that suggested otherwise was unrepresentative), **(2)** the source-wavefront
assumption **cannot currently be varied at all** — `source.cap` is an inert key on the grid path, so
mandate item 5 was blocked by a bug, not by physics, and **(3)** HF width at 8 kHz is set by the wall
angles and **cannot be widened inside the 600 mm home envelope**.

## 1. Corpus-wide sweep — the redundancy question, answered on 730 designs

Tool: `tools/analysis/spectral_corpus_sweep.py` (report-only, zero solver calls). Per run it takes the
`best.json` design, computes V±25/V±35/V+45/H+25/H+35 trend residuals and V+25/V+35 band-mean residuals
through `hornlab_search/metrics/spectral.py`, reads `terms.rip` from `best.json`, and groups by
`brief.name`. Identities with n ≥ 5 are reported; 61 smaller ones are listed as excluded.

Scanned: **730 usable** run dirs (25 more skipped: `best.json` did not resolve to a design response).
Refusals: 0.

| identity | n | median V+35 (dB) | p90 V+35 (dB) | ρ(rip, V+35) | ρ(J, V+35) |
|---|---:|---:|---:|---:|---:|
| `room_landscape_80x50_700_hf1440_v7` | 112 | 0.497 | 0.997 | **0.713** | −0.297 |
| `axi_90x90_1in` | 82 | 1.214 | 1.844 | **0.050** | −0.133 |
| `room_landscape_80x50_700_hf1440_v7_smooth` | 58 | 0.283 | 2.408 | **0.929** | −0.524 |
| `room_80x60_700_hf1440_v7` | 37 | 0.567 | 1.142 | 0.072 | 0.340 |
| `freeform_sculpt` | 36 | 0.930 | 1.221 | **0.014** | 0.011 |
| `b3a_pa_90x90_400_square_v4` | 29 | 0.577 | 1.410 | 0.761 | −0.108 |
| `organic_rollback_1in` | 29 | 0.372 | 0.403 | **−0.871** | −0.838 |
| `compact400_xo1000_1400_hf1440_v10xo` | 27 | 0.539 | 0.799 | **0.089** | 0.375 |
| `hifi_90x60_1in` | 22 | 1.120 | 2.201 | 0.363 | 0.583 |
| `room_landscape_80x50_700_hf1440_v10` | 19 | 0.491 | 0.838 | 0.717 | −0.251 |
| `room_landscape_80x50_700_hf1440_v11cd` | 15 | 0.429 | 1.671 | 0.725 | 0.493 |
| `b1w_hifi_90x60_850_wide_v4` | 14 | 0.774 | 1.609 | 0.560 | 0.698 |
| `native_ath_core_2in_v4` | 13 | 0.416 | 0.690 | 0.526 | −0.036 |
| `lecleach_rollback_1in_v6` | 12 | 0.454 | 0.478 | 0.469 | −0.783 |
| `native_ath_core_2in_v4_atlas2` | 11 | 0.408 | 0.547 | −0.555 | 0.745 |
| `b1w_hifi_90x60_850_wide` | 10 | 0.722 | 1.114 | 0.816 | 0.546 |
| *(11 more with n 5–7 in `sweep.md`)* | | | | | |

Full table, per-run rows and provenance: `runs/analysis/corpus_sweep_2026-11-20/{sweep.md,sweep.json}`
(git-ignored with `runs/`; regenerate with the command at the end of this file).

**What this overturns.** The 2026-11-19 audit measured ρ(`rip`, V+35) = 0.885 on 24 SCOUT40 bests and
concluded the fixed-angle residual was "largely redundant". On 730 designs the pooled ρ is **0.615**,
and **25 of 28 identities sit below 0.8** — seven of them near zero or negative:

- `organic_rollback_1in` (n=29): **ρ = −0.871**. Strongly *anti*-correlated: the designs that ripple
  most in angle are the smoothest along a fixed angle, or the metric is picking up a trade-off the
  angular term cannot see. Worth a look before anything is built on this number.
- `axi_90x90_1in` (n=82): 0.050, `freeform_sculpt` (n=36): 0.014, `compact400` (n=27): 0.089,
  `room_80x60_v7` (n=37): 0.072 — effectively independent axes.
- Only `room_landscape_80x50_700_hf1440_v7_smooth` (0.929, n=58) and two small identities reach ≥ 0.8.

The 0.885 sample was the *v7_smooth* family, which is exactly the identity where the two agree. So:
**the fixed-angle residual is a real second axis for most of our lines of work**, and the earlier
"no promotion" conclusion is revised — not to "promote it", but to "it is no longer dismissed on
redundancy grounds". The remaining gate is acoustic, not statistical (see §4).

Two machinery checks from the same run:

- ρ(V+25, V+35) is 0.6–1.0 in most identities: **one seat angle is enough**, the second adds rank
  stability only.
- ρ(trend, band_mean) varies from −0.85 to +0.95 across identities — the reference-choice finding
  from the 24-design audit is a property of the families, not of the sample.

## 2. Source sensitivity — the knob is inert, so item 5 is blocked by a bug

Night `source_sensitivity_2026-11-20`, 6 jobs: two anchors (Crowe X OSSE `9b5428e6dec8`, OSSE morph
`cf716e738ef8`) × three source caps (auto / 150 mm / 60 mm curvature), each re-solved at verify
fidelity under a 12 kHz `verify_only` brief (`examples/briefs/source_sensitivity_2026-11-20/`), so the
8–12 kHz region above the 5.61 kHz throat cut-on is actually sampled.

**Result: all three caps are numerically identical — to 0.00 in every beamwidth and level.**

```
crowex  auto/150/60 : bwH 8k 74.06   bwV 8k 54.27   V+35@8k -10.18 dB   V+35@12k -10.87 dB
morph   auto/150/60 : bwH 8k 60.25   bwV 8k 50.39   V+35@8k -11.38 dB   V+35@12k -13.94 dB
```

That is not a physical result. It is the bug: `mesh_hash` is **identical (`7abdb66729…`) across all
three**, and only the first solve of each pair really ran (`cached: false`); the other two are cache
hits. `hornlab_search/mesh/grid_build.py` hardcodes
`PointGridHornGeometry(..., source_shape=1, source_auto_angle_deg=<throat angle>)` and never passes
`source_radius_mm`, so the mesher's `_source_cap_radius` always takes the auto-angle branch and the
brief's `source.cap` is decorative. **Every grid-family solve we have ever stored uses the auto cap.**

What that costs: the one experiment that could have bounded how much of our 8–12 kHz result is the
source assumption returned "no difference" for a purely mechanical reason. A reader who does not
compare hashes would file that as "the source doesn't matter" — the exact wrong conclusion, and the
third silent-killer of this session alongside the void dense pair and the bridge-cell verify hole.

Fix in flight: thread the brief's cap into `source_radius_mm` in `grid_build.py`, with a test that the
`auto` path is byte-identical to today's hashes and that `cap: 60` changes the mesh hash. Until that
lands, **mandate item 5 has no lever and must not be attempted** — and item 4's comparisons are
implicitly "at the auto cap", which is at least consistent across designs.

## 3. HF width — one knob at a time, and an envelope that binds

Night `hf_width_2026-11-20`, base = Crowe X OSSE best `9b5428e6dec8` (wall H 36.39° / V 22.71°, lip
18.28 mm, L 259.60 mm), all knobs pinned, one factor per config, screen fidelity.

`tools/shape_check.py` first: the base seed is **envelope-saturated** — mouth 593 × 412 mm inside the
600 × 480 mm HOME brief. Wall ×1.15 → 672 mm mouth (OVER), lip ×1.5 → 614 mm (OVER). Both were deleted
rather than queued; the legal space is one-sided (shrink only).

| config | change | J | bwH 4.26 / 6.22 / 8 k | bwV 4.26 / 6.22 / 8 k | V+25@8k | V+35@8k |
|---|---|---:|---|---|---:|---:|
| baseline | — | 5.3454 | 71.5 / 72.7 / **74.0** | 55.7 / 54.1 / **53.9** | −5.08 | −10.27 |
| lip_lo | lip 18.28 → 9.14 mm | 5.5866 | 72.7 / 72.9 / **74.2** | 57.7 / 54.1 / **54.1** | −5.02 | −10.21 |
| wall_lo | wall angles ×0.85 | 6.7169 | 63.9 / 61.1 / **62.2** | 49.8 / 48.2 / **47.2** | −6.77 | −12.02 |

Against the pre-declared thresholds (≥1° or ≥0.5 dB = controllable):

- **Wall angle is the lever**: −11.8° H and −6.7° V at 8 kHz, −1.7 dB at +25°, and it costs +1.37 J.
- **Lip radius is essentially inert** for HF width: +0.2° / +0.2° / +0.06 dB, i.e. inside the noise
  of the detrend/angle choices. It does move J slightly (+0.24), through the loading/pattern terms.
- Baseline reproduces the stored SCOUT40 design exactly (same hash → cache hit, J 5.3454), which
  validates the pinned-config construction.

**Consequence for "how do we get a wider HF pattern?"** Not with these knobs inside this envelope:
width tracks the wall angle, and the wall angle is already at the 600 mm mouth limit. Widening HF
requires a larger envelope (owner decision) or a different mouth/aspect law — which is what mandate
item 4's *second* factor (aspect/morph) should test next, not more wall angle.

## 4. What we now know we need

1. **A live source knob.** Without it, item 5 cannot be attempted and every 8–16 kHz result carries an
   unknown, unmeasured source condition. (Fix in flight; then re-run this section's night unchanged.)
2. **Envelope headroom or a mouth-law change** if wider-than-74° HF at 8 kHz is a goal. The current
   home envelope is the binding constraint, not the shape family.
3. **An acoustic criterion for the fixed-angle residual** before it ever becomes a term. The corpus
   shows it is a second axis (25/28 identities < 0.8); what it does not show is that a large residual
   is *audibly* bad. The honest next test is the one measurement we cannot simulate: a real driver on
   a real horn, with the fixed-angle curve measured at the seat.
4. **A tie-breaker for the anti-correlated identity.** `organic_rollback_1in` (ρ = −0.871, n=29) is
   either a real design trade-off or a metric pathology. One afternoon of stored-data work settles it.

## 5. Verification and provenance

```
.venv\Scripts\python.exe tools/analysis/spectral_corpus_sweep.py --runs-root runs ^
    --out runs/analysis/corpus_sweep_2026-11-20                     -> exit 0, 730 usable, 0 refused
.venv\Scripts\python.exe -m pytest -o addopts="" -q -p no:cacheprovider ^
    tests/test_tools_analysis_spectral_corpus_sweep.py               -> 4 passed
.venv\Scripts\python.exe tools/shape_check.py "examples/typologies/hf_width_2026-11-20/*.yaml"
                                                                    -> 3 pass, 2 OVER (deleted)
```

GPU work (two nights, both `HORNLAB_GPU_LOCK=refuse`, `gpu-clean` before/after every job, one solve
at a time): `source_sensitivity_2026-11-20` 6 jobs, 2 real solves, peaks 887–1697 MiB, baselines
737–848 MiB; `hf_width_2026-11-20` 3 jobs, 2 real solves (18.7 s / 22.1 s), peak ≤ 1 GB. No solve ran
concurrently with another: one night's first job was refused `GPU busy` by a foreign job, waited, and
then ran. Queue logs `runs/nights/queue_{source_sensitivity,hf_width}_2026-11-20.log`; per-job logs and
`summary.jsonl` in `runs/nights/<night>/`.

Uncommitted machine output (all under the git-ignored `runs/`): the six source-sensitivity responses
and the three HF-width responses; regenerate by re-running the two night files in `docs/queue/`.
