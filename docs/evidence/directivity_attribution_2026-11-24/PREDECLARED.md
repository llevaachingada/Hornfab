# Predeclared bins, predictions and pass rules

Written 2026-11-24T23:48Z, **before** any solve in this folder. Not edited after results; outcomes go in
[README.md](README.md).

## Fixed comparison

Every candidate is its neutral anchor with only the knobs named below changed (checked: the YAMLs differ from
`docs/evidence/size_aware_2026-11-24/anchor_*_neutral.yaml` only in `name`, `description`, `seed_params`,
`bounds`). Same brief `room_landscape_80x50_900_hf1440_v11cd`, v11 objective, 36 mm / 2° assumed source,
freestanding quarter model, BEAT CUDA, 29-frequency verify grid, 1024-point balloon DI, epw 6. Controls are
the existing anchor verifies (`runs/rolled_lame_anchor_verify_2026-11-24/{rolled,lame}`), whose meshes are
byte-identical to the neutral adapters (`anchor_verify_parity.json`).

Widths are full −6 dB widths at the saved verify frequencies (no interpolation).

| Bin set | Saved frequencies (Hz) |
|---|---|
| HF (6–8 kHz) | 6085, 6325, 6977, 7113, 8000 |
| 4–8 kHz | 4037, 4628, 5000, 5307, 5623, 6085, 6325, 6977, 7113, 8000 |
| Mid (1–4 kHz) | 1028 … 3520 (9 bins) |

Anchor corridor misses (H 60–90° from 900 Hz, V 40–60° from 1 kHz):

- **Rolled** `fa5b207bca6d`: H below 60° at 6977, 7113, 8000 (59.0, 58.4, 54.8); H at the 90° edge at 2037
  (90.15); V above 60° at and below 4037 Hz.
- **Lamé** `0782945027ae`: H below 60° from 4628 to 8000 (59.8 → 46.0, 10 bins); V below 40° at 6325–8000
  (39.1 → 34.1, 4 bins); V above 60° at and below 3070 Hz.

## Predictor used for the numbers below (heuristic)

`station_map.py`: width(f) ≈ 2 × wall angle at a fixed meridian station, the station for f taken half an
octave toward the throat for H, with a fitted gain. Fitted on the two solved variants: rolled H gain 0.61
(rms 1.0°), rolled V 0.62 (rms 2.0°), Lamé H 0.72 (rms 0.4°); **Lamé V is uncalibrated** (borrows rolled V).
It ignores the mouth, return, lobing and loading. It is a predeclaration device, not evidence.

## Rolled hybrid

| Job | Change | Prediction | Pass rule |
|---|---|---|---|
| `rolled_h10_v0` | H +10°, V 0°, window .30/.60/.88 | ΔH(2037) ≈ +9.5; ΔH HF −0.2…+2.0; ΔV ≈ 0 | **H causes the 2 kHz overshoot** if ΔH(2037) ≥ +8 (≥ ⅔ of the combined +12.05) and \|ΔV\| ≤ 2 at 2–8 kHz |
| `rolled_h0_v6` | H 0°, V +6°, same window | ΔV(2037) −3.1, ΔV(8000) +6.2; ΔH ≈ 0 | **V gain separable** if ΔV(2037) ≤ −3.6 and ΔV(8000) ≥ +2.9 (≥ 75 % of combined −4.81/+3.90) and \|ΔH\| ≤ 2 at 1–8 kHz |
| `rolled_h10_early` | H +10°, window .12/.40/.65 | ΔH HF +5.0…+9.4; ΔH(2037) −10.7 (→ ≈ 79°); ΔH 3–5 kHz ≈ 0…+3 | **Earlier development has HF H authority** if ΔH ≥ +3 at ≥ 4 of 5 HF bins and H(2037) ≤ 90 |
| `rolled_h20_early` | H +20°, same early window | about twice `h10_early` (ΔH(8000) +19, ΔH(2037) −22) | dose response: HF gain larger than `h10_early`; flag lobing (wall angle is non-monotone: 38.9° at u .30 → 27.3° at .45) |
| `rolled_h10_late` | H +10°, window .55/.75/.94 | \|ΔH\| ≤ 0.3 at 2–8 kHz; effect, if any, below 2 kHz | **Later development lacks HF authority** if \|ΔH\| < 1.5 at all HF bins |

Return onset is **not** solved here: it is a separate variable (`rolled_terminal_family`), whose only solve
(2026-11-20, a different parent) moved 8 kHz H by 0.4° and raised ripple 0.029 → 0.159.

## Klangfilm–Lamé

| Job | Change | Prediction | Pass rule |
|---|---|---|---|
| `lame_morph_040` | `morph_frac` 0.60 → 0.40 (earlier round→Lamé) | ΔH HF +5.3…+5.5; ΔV HF +2.7…+5.8 (uncalibrated); ΔH(2037) −2.2; ΔV(2037) +3.7 | **Transition timing widens HF** if ΔH ≥ +2 at ≥ 4 of 5 HF bins and V(8000) not narrower |
| `lame_morph_085` | `morph_frac` 0.60 → 0.85 (later) | ΔH −2…−4 at 2–8 kHz; ΔV HF +4 | expected **fail** on H; tests the predictor in the opposite direction. Return curve sampled ≤ 0.72 mm off neutral (resampling), rim unchanged |
| `lame_hmid_m2` | Phase A blend 1, H mid gain −2 mm (mirror of solved +2) | ΔH HF +2.8…+3.7; ΔV ≈ −0.7…−1.0 (mirror of measured +2 arm) | **H/V schedule widens HF** if ΔH ≥ +2 at ≥ 4 of 5 HF bins |

Throat radius, roundness and entrance tangent are unchanged for all Lamé jobs (throat-station delta 0); the
Phase A entrance angle (`theta_h0/v0`) is not changed because it alters the throat slope.

## Guardrails for every candidate

- No new H/V multilobe bins (`n_multilobe_h/v`); report the diagonal (45°) balloon cut and isobars.
- Loading: min Re(z_throat) from 900 Hz up stays ≥ 0.5 and falls by no more than 0.1 versus the anchor.
- Report 1–4 kHz trade-offs bin by bin; DI and on-axis response smoothness in the 1–8 kHz band.
- J (v11, frozen) and its raw terms are reported beside the widths; J alone does not promote.

## Promotion to the next construction

A candidate is promoted only if it passes its HF rule, does not worsen J, raises no guardrail, **and** its
predeclared-bin deltas keep their sign and at least half their size on a refined spatial mesh (epw 9, the
anchor re-solved at epw 9 as its control). The refined pair is run for each family's best passing candidate
only; if none passes, the anchors alone are re-solved at epw 9 to bound mesh noise on the reported deltas.

## Addendum, written 2026-11-24T23:57Z after batch 1 and before batch 2

Batch 1 passing candidates: `rolled_h10_early`, `rolled_h20_early`, `lame_morph_040`, `lame_hmid_m2`. Batch 2 runs
the predeclared refined-mesh gate for all of them except `lame_hmid_m2` (its +2 mm mirror already bounds the
same mechanism; it is re-solved at epw 9 only if budget allows), plus both anchors at epw 9 as controls. Same
configs with `mesh.epw` 6 → 9 only (verify DOF 6.6–7.8k, cap 24k).

Pass rule (unchanged): each predeclared HF-bin delta keeps its sign and at least half its epw-6 size, and the
2 kHz H change keeps its sign.

Source-angle sensitivity, `lame_src10`: the exact Lamé anchor with brief driver `exit_angle_deg` 2 → 10 (36 mm
unchanged). Wall arrays are bit-identical; only the assumed source cap changes (radius 18/sin θ: 516 → 104 mm,
sag 0.31 → 1.58 mm). New source identity; compared only as a sensitivity pair. Prediction: |ΔH|, |ΔV| ≤ 1.5° at
all HF bins. If larger, the assumed 2° exit is a material modelling choice for every HF claim here and any
wider-exit driver study must be solved, not inferred.
