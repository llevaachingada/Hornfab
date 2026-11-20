# Verified: the fixed-angle residual is stable under a frequency-grid change (2026-11-20)

Test of the [`spectral ripple audit`](README.md) itself, not of a horn. Night
`ripple_audit_2026-11-20` (11 jobs, launched 08:34 local, finished 08:48, **exit 0** after the
bridge-cell retry below); 10 verify-fidelity re-solves + 2 audit jobs; **no search, no new
geometry, no brief or config authored**.

**Question, predeclared before the run:** is the fixed-angle residual a property of the horn, or of
the 18-point screen grid? **Criterion:** Spearman(screen V+35, verify V+35) ≥ 0.8 over the ten
designs, no design moving more than 0.5 dB, and the B3 band still notched once verify frequencies
sample it.

**Answer: PASS on the ranking, and the dense grid then sharpened the verdict.**

## What was solved

Each design was re-solved at **verify fidelity** from its own archived run's `config.yaml` with
`hornlab-search verify --designs <hash> --verify-dir runs/ripple_audit/<id>`: 25 log frequencies +
balloon 1024 instead of 12+6 and 512; the mesh is the same (screen and verify share the band/caps,
stated by the CLI itself). Fidelity changes the frequency *positions*, so this is a **resampling**
test, not a dense-grid test — the dense 1.8–3.6 kHz runs remain mandate item 3
(`x_r3_b3_dense_epw6/epw9`).

Ten sources, chosen to span the measured range, both families, both SCOUT40 briefs:

| screen V+35 | design | run |
|---:|---|---|
| 2.247 | `14e53020adbe` Klangfilm C200 | `runs/20261119T051833Z-screen-64eea7` |
| 1.947 | `e4d38596e2a8` Klangfilm B3 previous | `runs/20261119T051630Z-screen-ce7a3f` |
| 1.441 | `ee85bcd2ad67` Klangfilm B3 current | `runs/20261119T073330Z-screen-723756` |
| 0.822 | `cf716e738ef8` OSSE morph | `runs/20261119T081214Z-screen-8470bd` |
| 0.774 | `c1d088b8b92f` extended throat | `runs/20261119T075629Z-screen-015bfc` |
| 0.596 | `efe4a8959d85` R-OSSE rectangular | `runs/20261119T085256Z-screen-c2203f` |
| 0.351 | `9b5428e6dec8` Crowe X OSSE | `runs/20261119T090559Z-screen-9b8767` |
| 0.342 | `2979e2d125ce` Tritonia v8 | `runs/20261119T083421Z-screen-ab2159` |
| 0.117 | `f2054faaa9d4` Klangfilm Lame | `runs/20261119T053037Z-screen-394fb1` |
| 0.058 | `5381c9cea1ec` Le Cléac'h smooth | `runs/20261119T050354Z-screen-7ebf9c` |

## Result — screen (10 band samples) vs verify (11 band samples)

| design | V+25 screen | V+25 verify | Δ | V+35 screen | V+35 verify | Δ |
|---|---:|---:|---:|---:|---:|---:|
| `14e53020adbe` | 1.090 | 0.606 | **−0.485** | 2.247 | 2.188 | −0.059 |
| `e4d38596e2a8` | 0.950 | 1.027 | +0.077 | 1.947 | 1.520 | −0.427 |
| `ee85bcd2ad67` | 1.151 | 1.173 | +0.022 | 1.441 | 1.908 | **+0.467** |
| `cf716e738ef8` | 0.497 | 0.396 | −0.101 | 0.822 | 0.638 | −0.184 |
| `c1d088b8b92f` | 0.601 | 0.573 | −0.028 | 0.774 | 0.691 | −0.083 |
| `efe4a8959d85` | 0.382 | 0.325 | −0.056 | 0.596 | 0.446 | −0.150 |
| `9b5428e6dec8` | 0.266 | 0.261 | −0.006 | 0.351 | 0.355 | +0.004 |
| `2979e2d125ce` | 0.302 | 0.401 | +0.099 | 0.342 | 0.386 | +0.044 |
| `f2054faaa9d4` | 0.038 | 0.044 | +0.006 | 0.117 | 0.122 | +0.005 |
| `5381c9cea1ec` | 0.053 | 0.065 | +0.012 | 0.058 | 0.056 | −0.002 |

- **Spearman(V+35 screen, V+35 verify) = 0.964** (p = 7.3 × 10⁻⁶); Kendall ordering holds at the
  top (C200 worst) and the bottom (Le Cléac'h / Lame smoothest).
- **max |Δ| = 0.467 dB** (B3 current at +35°), **mean |Δ| = 0.143 dB**. Every move is inside the
  detrend-order spread already reported for these designs (up to 0.957 dB on C200).
- Reading: the *ranking* is robust to where the samples land; an *absolute* threshold is not, which
  is what the audit already says for the detrend order. No design changed verdict.

## The B3 notch survives the resampling

`spl_v(+25°) − spl_v(0°)` on the 25-frequency grid: **−6.77 dB at 1,776 Hz, −5.80 at 2,037,
−6.47 at 2,335, −2.90 at 2,678, −4.61 at 3,070**. The screen grid read −6.88 at 1,763, −6.74 at
2,269, −3.61 at 2,573, −3.64 at 2,919, −4.88 at 3,311. The 1.8–2.3 kHz dip is reproduced at new
sample positions and the mid-band values move by ~1 dB — a broad, stable feature, not a
knife-edge notch that one unlucky sample invented.

## Addendum — the dense grid, and what it does to the verdict (2026-11-20, same morning)

The corrected item-3 solves were already on disk when this test ran
(`runs/20261120T065945Z-screen-c0ef06` epw 6.0, 69.8 s real solve; `runs/20261120T070119Z-screen-83e864`
epw 9.0, 251.9 s), **91 frequencies**, 25 Hz steps through 1.8–3.6 kHz, `cached=False` both. (The
*earlier* pair, `20261120T053929Z`/`T053950Z`, is void: those jobs ran 00:39 with the old brief — 18
frequencies, `cached: true` — and their configs were corrected at 00:46, seven minutes too late. A
re-run of the corrected configs later the same morning hit the cache at 0.0 s, which is how the two
pairs were told apart.)

**The feature is not a resonance.** At 25 Hz resolution, +25° relative to on-axis, vertical, both
meshes agree to ≤ 0.1 dB:

```
1.80 kHz -6.6 → 2.00 kHz -5.7 → 2.30 kHz -6.7 → 2.50 kHz -4.5
2.75 kHz -2.8 (local maximum) → 3.00 kHz -4.2 → 3.20 kHz -4.9 (flat to 3.34 kHz)
```

That is a **broad, smooth double-dip spanning ~600 Hz** (a −6.7 dB shelf to 2.3 kHz, a −2.8 dB bump
around 2.75 kHz, then −4.9 dB). No high-Q structure, nothing narrower than 1/9 octave, and no
difference between the two mesh densities (3,375 vs 7,326 dof) — so it is mesh-converged and is a
property of the geometry, not of the sampling. Whatever produces it (spatial redistribution,
diffraction, broad modal interference), **it is not a mouth or throat resonance**, which is the
reading the handoff explicitly left open.

The separate readout in
[`../runs/expand_2026-11-19/README.md`](../runs/expand_2026-11-19/README.md) measures the **on-axis**
response (1 kHz-referenced) on the same two solves: a ~2.1 dB dip whose minimum is at 2.8 kHz, epw6
vs epw9 max |Δ| 0.01 dB. The two are the same feature seen from two axes, and consistent: on-axis
falls by ~2 dB at 2.8 kHz while the +25° cut does not, which is precisely why the *ratio* used here
humps up at 2.8 kHz. Read the two together, never interchangeably.

**Consequence for the metric — the honest revision.** The dense grid gives
`V+25 = 1.104`, `V+35 = 1.313` for B3 current. The three grids therefore read:

| grid | samples in band | V+25 | V+35 |
|---|---:|---:|---:|
| screen (18 freqs) | 10 | 1.151 | 1.441 |
| verify (25 freqs) | 11 | 1.173 | 1.908 |
| dense (91 freqs) | 80 | 1.104 | 1.313 |

The **ranking** result stands (ρ = 0.964 across ten designs), but the **absolute** value is
grid-dependent at the 0.1–0.6 dB level even at 25 points — verify's +35° value is 0.60 dB above the
dense truth while screen's is only 0.13 dB above it. So: quote this metric comparatively, never as an
absolute threshold, and prefer the screen grid (the one the evidence base uses) over verify for it.
The predeclared "no design moving more than 0.5 dB" criterion held for screen↔verify; the dense data
shows that agreement is not accuracy.

## Two things this run found that are not about the metric

1. **`runs/20261119T085256Z-screen-c2203f` cannot be verified or resumed from the plain CLI.**
   Its `config.yaml` stores `generator.rows.type: rosse_rect`, one of the opt-in **bridge cells**
   (`examples/catalog.yaml`: "REQUIRE their own process-local entry point"). `hornlab-search verify`
   refuses with `GeometryInvalidError: generator seed is not a legal horn: unknown rows type
   'rosse_rect'`. The job succeeded only after re-running through
   `tools/geometry/rosse_rect_cli.py verify ...` (same subcommand, process-local catalog rebind).
   **Any run whose rows type is a bridge cell needs its own entry point for verify/resume** — worth
   knowing before a lane queues a verify night on bridge-cell bests (`n`, `rolled_rect`,
   `crowe_panel`, `rosse_rect`, …).
2. **Verify J is not screen J.** B3 current: screen J 2.80022 → verify J 3.49921; R-OSSE rect 4.55960
   → 5.08620. The frequency grid enters J, so the two tiers are different score identities — never
   pool them or call the delta an improvement.

## Provenance

- Night file: `docs/queue/ripple_audit_2026-11-20.yaml` (13 jobs: 10 solves, 1 failed plain-CLI
  attempt, 1 bridge retry, 2 audit attempts). Queue logs:
  `runs/nights/queue_ripple_audit_2026-11-20{,b}.log`; per-job logs and `summary.jsonl` in
  `runs/nights/ripple_audit_2026-11-20/`.
- Audit output committed here: `verify_v2/{audit.json,disagreement.md}` (the ten verify rows; the
  per-design JSONs the tool also writes are regenerable duplicates and are not committed).
- VRAM: per-job peaks 473–1,118 MiB against a recorded 474–491 MiB baseline (RTX 4060, 8 GB);
  `gpu-clean` ran before and after every job; no solve ran concurrently with anything else.
- The verify responses themselves live under `runs/ripple_audit/` (git-ignored with `runs/`).
