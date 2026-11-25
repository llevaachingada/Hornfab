# Rolled and Lamé exact-anchor body checks

2026-11-24. **The rolled body change lowers J but does not fix horizontal high-frequency narrowing. The tested Lamé change worsens J and horizontal 8 kHz coverage.** These are simulated, matched verify-tier comparisons, not physical-driver measurements or a spatial mesh-convergence study.

## Identity and controls

Both pairs use the same effective brief `room_landscape_80x50_900_hf1440_v11cd`, recorded brief hash `205eb1c8efbb`, v11 objective, 36 mm assumed exit, 2° assumed exit angle, freestanding quarter model, BEAT CUDA, 29 verify frequencies and balloon DI. The horizontal corridor is 60–90° from 900 Hz, the vertical corridor 40–60° from 1 kHz; preferences are 80° and 50°, respectively. The source cap is a numerical assumption; the 2° is not a measured HF1440 exit wavefront.

The anchors are `fa5b207bca6d` in `runs/rolled_lame_anchor_verify_2026-11-24/rolled` and `0782945027ae` in `runs/rolled_lame_anchor_verify_2026-11-24/lame`. Rolled variant is `runs/20261124T222433Z-verify-4617d0`, using the existing front-load law H +10° / V +6°; Lamé variant is `runs/20261124T222525Z-verify-b5497c`, using the existing Phase A H mid-gain +2 mm. Anchor exact-parent versus neutral-adapter verify meshes were byte-identical and matched the saved verify mesh; mesh and solve specs, mesh config, target, weights, objective parameters and brief matched among anchor, neutral and variant. Reproduce and inspect hashes with `anchor_verify_parity.py` and `anchor_verify_parity.json` in this folder. The non-neutral variant meshes are necessarily different shapes, and this is not a same-mesh numerical error estimate.

Geometry checks and fixed configurations are in [ANCHOR_GEOMETRY.md](ANCHOR_GEOMETRY.md). Rolled return and last 10% of sampled inner stations are unchanged by the law. The Lamé original return law is retained; arc-length resampling creates a maximum 0.0102 mm difference in the final 10% of sampled points. These geometry checks do not demonstrate preserved acoustic character.

## Measured verify results

Widths below are full −6 dB H/V degrees at the nearest saved points, with no interpolation to the requested round frequencies. They are not nominal wall angles.

| Design | J | 1,027.68 Hz | 2,036.74 Hz | 4,036.58 Hz | 8,000 Hz |
|---|---:|---:|---:|---:|---:|
| Rolled anchor | 8.1209 | 114.23 / 114.23 | 90.15 / 74.02 | 70.38 / 61.54 | 54.84 / 47.67 |
| Rolled front-load | 7.7094 | 107.18 / 112.70 | 102.20 / 69.21 | 76.68 / 60.64 | 53.89 / 51.57 |
| Lamé anchor | 11.2206 | 90.98 / 127.46 | 75.45 / 80.99 | 62.62 / 51.27 | 45.98 / 34.05 |
| Lamé H mid-gain | 12.0276 | 90.97 / 127.48 | 75.61 / 80.97 | 61.49 / 51.30 | 43.06 / 34.72 |

Rolled J falls by 0.4115 (5.1%). At the listed 2 kHz point the V excess improves by 4.81°, while H moves 12.05° farther outside the corridor; H at 8 kHz narrows a further 0.95°. V at 8 kHz remains in corridor and moves closer to preferred 50°. At 1.03 kHz both planes remain too wide. Thus the combined body deformation has measurable authority but does not satisfy the primary H objective. The raw `dislope` term improves 5.839→4.635 and `diag` 6.754→5.016, while `offaxis_smooth` worsens 1.427→1.836 and `flat` 0.187→0.356; raw terms are not weighted contributions and should not be summed directly.

Lamé J rises by 0.8070 (7.2%); H narrows by 2.92° at 8 kHz where it already misses the lower limit, and V remains below the lower limit. The 1.03 kHz V response remains far too wide. Raw `dislope` rises 9.508→10.198 and `offaxis_smooth` 2.041→2.170. This rejects **this** +2 mm H-gain trial, not every Phase A setting or every retained-return Lamé construction.

Balloon DI at 1.03/8 kHz is rolled 7.69/14.54 dB anchor and 7.99/14.18 dB variant; Lamé 7.90/16.39 dB anchor and 7.90/16.59 dB variant. All four report zero detected H/V multilobe bins on this sampled grid; that is not proof of no lobes between samples or in other planes. Loading penalty is zero for all four. Minimum normalized real throat impedance from crossover is rolled 0.991→1.002 and Lamé 0.782→0.712; compare the actual impedance and response before treating the zero penalty as a complete loading assessment.

## Decision and cost

Retain the rolled result as a partial candidate, not an accepted CD solution. If the next question is attribution, run **two** matched fixed controls on this exact anchor: H-only +10°/V 0° and H 0°/V-only +6°, with the same fixed window, brief, source, grid and verify fidelity. Use the neutral geometry and config in this folder as the base; hold every other knob. Compare both H and V cuts, diagonal response, J components, loading and the returned geometry. These controls separate the two amplitudes' effects, although nonlinearity means their sum need not equal the combined change. Stop pursuing this body shear alone if H 8 kHz remains outside the corridor or diagonal/off-axis behavior worsens materially; a termination or body alternative then needs its own neutral-controlled, return-preserving construction and CPU geometry validation.

Hold the tested Lamé +2 mm H mid-gain and avoid a broad Phase A search based on it. Preserve the exact anchor, its rounded-square section and rollback while researching a separately controlled intermediate/terminal wall-law change; the existing Phase B core removes the return and is not a drop-in visually equivalent solution. The earlier Phase A experiment was on another seed and does not prove that every Phase A modification lacks authority.

Each of the four jobs completed successfully. Anchor wall times in `runs/nights/rolled_lame_anchor_verify_2026-11-24/summary.jsonl` were 50.45 and 50.80 s; body variants in `runs/nights/rolled_lame_body_verify_2026-11-24/summary.jsonl` were 51.50 and 49.83 s, with reported solve times 26.35 and 25.97 s. These are observed single-job costs on this machine, not guarantees; the two proposed attribution solves might cost roughly another 100 s wall plus setup, if comparable. The four jobs bought a concrete rejection and a bounded partial improvement, not a validated production design. Screen and verify use the same mesh under the current policy; a refined spatial mesh and, where appropriate, an independent backend are separate gates.

## Two-inch interface is a separate study

Beyma specifies a 50.8 mm throat, 7° exit angle, 500 Hz–20 kHz frequency range, crossover at or above 500 Hz with at least 12 dB/octave slope, 100 mm voice coil, and four M6 holes on a 101.6 mm circle. The datasheet includes mounting dimensions and measures its on-axis response with a TD-460/N horn. Confirm whether the 7° is included or half-angle and obtain the outlet section before mapping it to the model. Use separate source/interface provenance for the 50.8 mm geometry, cap assumption and any adapter. The wavefront and high-frequency effect remain open. [Beyma product specification](https://www.beyma.com/en/products/c/compression-driver/1CP85ND8/motor-cp-850nd-8-oh/) · [Datasheet and mounting drawing](https://www.beyma.com/speakers/Fichas_Tecnicas/beyma-speakers-data-sheet-compression-driver-CP850Nd.pdf)
