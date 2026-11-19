# Score-term audit of the shipped v10 home brief — why more solves have not produced better horns

> **CORRECTION 2026-11-19 (Gate A, `../xo_loading_gateA_2026-11-19/REPORT.md`): parts of this report are superseded.**
>
> - **F6's dB figures were referenced to the solver's unit-acceleration drive.**
>   - At unit velocity, fold_warm's 643–828 Hz on-axis level is −1.6/+1.5 dB relative to 2 kHz, and its power is +1.3/+2.8 dB. That power figure equals 10 log10 of its Re(z) ratio, and energy balance closes at 0.96–1.00.
>   - The "+8–9 / +10–11 dB bump" does not exist acoustically.
>   - The corridor-compliant horns (rosse, tritonia) are 5–8 dB under-loaded at 643–828 Hz, so `load` charges them for a real deficit.
>   - The bottom line's "rewards a crossover hump" reading, F6's inference, decisions 4–5 and the owner question are therefore **withdrawn**.
> - Decision 3 is lifted.
> - F1–F5, F7 and F8 stand. F8's census is refined in Gate A: 205 hashes, 9 of them on different meshes.

Fable senior lane, 2026-11-19. **CPU-only, read-only replay of stored responses.** No BEM solve, no
queue edit, no scoring default changed, nothing under `runs/` rewritten. Reproduce with
`score_term_audit.py` in this folder (output: `runs/analysis/score_term_audit_2026-11-19/`).

Labels: **VERIFIED** = replayed here through `hornlab_search.objective.replay` with exact parity to the
published fleet column (max |ΔJ| = 0.0 on all 271 replayed designs; 257 of 258 floor pairs replay and
reproduce the recorded screen/verify J exactly); **INFERENCE** = engineering reading; **PROPOSED** = next work.

Brief audited: `examples/briefs/home_landscape_2026-11-18_v10/room_landscape_80x50_700_hf1440_v10.yaml`
(corridor H 60–90° from 700 Hz, V 40–60° from 1 kHz, `ripple_region: preferred_edge`, loading on).

## Bottom line

The search is working; the scalar it optimises is not separating the horns the owner wants from the
horns it rewards. Among good designs the decisive term is **`load`**, and every top-ranked family under
v7 *and* v10 satisfies it through a **half-octave Re(Z) hump of ~1.8× at ~650–900 Hz** — directly on the
700 Hz crossover — with a matching **+8–9 dB on-axis / +10–11 dB power-response bump**. Horns with clean,
corridor-compliant directivity and a smooth power response lose 1.2–2.5 J on `load` alone (floor 0.47 J).
The same term is also most of the numerical floor: `load` is 56 % of the screen→verify variance. More
CMA evaluations of this objective produce better-tuned crossover-region humps, not better directivity.

## Findings

**F1 — The review's `dislope` hypothesis is rejected. VERIFIED.** `dislope` is 58 % of mean J over the
top-10-per-lane designs (n = 271; cov_profile 8 %, load 13 %, di_roughness 8 %). Setting its weight to 0
promotes classic beaming horns to the top: `es_style_rollback` (H 103° → 39°, V 119° → 37°, J 10.2 → 0.84),
`lecleach_iwata`, `section_axial` (V 136° → 33°). `dislope` is not punishing legitimate narrowing — among
the 153 designs inside the corridor at ≥ 90 % of frequencies the DI slope is a median 1.5 dB/decade
(≈ 0.26 J). It is the term that actually enforces the corridor. **Do not ship `dislope = 0`.**

**F2 — `cov_profile` is too weak to enforce the corridor it encodes. VERIFIED (code + replay).**
`scalar_v9._plane_cov_cost` averages a (deg/10)² cost over the whole 350–8000 Hz band; with
`cov_below_f0: one_sided` everything under 700 Hz is free but still in the mean, `freq_weights` doubles
2.5–5.5 kHz where ~every horn already complies, and the sum is divided by tolerance 3. Net: a horn 21°
under the H minimum at 8 kHz pays ~0.5 J. Corridor enforcement has migrated into a slope term that cannot
say *where* a horn fails.

**F3 — Side-lobe / outermost-crossing hypothesis rejected for this population. VERIFIED.** On the
top-300 v10 designs, outermost −6 dB and main-lobe (first-crossing, `acoustic_v2.main_lobe`) widths are
identical at every frequency on both cuts; no off-axis lobe exceeds −6 dB. No new lobe term is warranted.

**F4 — `preferred_edge` vs `max_edge` is policy-insensitive here. VERIFIED.** `max_edge` adds a near-uniform
0.06–0.12 J and leaves the lane-best order of the top 8 unchanged. No action.

**F5 — Where the corridor actually fails (top-300 v10). VERIFIED.** Misses concentrate at band edges:
V > 60° at 1.07 kHz in 99 % (median 63°) — consistent with the recorded K-law limit (480 mm of V height
holds 50° only to ~1.16 kHz; NOTES_FOR_SENIOR 2026-11-15), i.e. **the V corridor start is at the
envelope's physical limit**; H < 60° at 6.2 / 8 kHz in 53 % / 79 % (HF beaming); H < 60° at 828 Hz in 41 %;
a genuine main-lobe V widening at 3.76 kHz in 45 %. Strictly, 0 of 3,608 designs meet both corridors at
every frequency; a cluster (`rosse_rect_cd`, ATH `tritonia` v8/v9) is within ~1° (RMS miss 0.08–0.3°).

**F6 — The compliant horns lose on loading, and the winners "load" via a crossover-region hump. VERIFIED
(numbers) / INFERENCE (audibility).**

| design | v10 J | `load` | RMS corridor miss | Re(Z) 643/828/1065 Hz | on-axis 643–828 rel. 2 kHz | power 643–828 |
|---|---|---|---|---|---|---|
| fold_warm (v10 #1) | 1.42 | 0.09 | 1.38° | 1.39 / 1.93 / 1.29 | +8 / +9 dB | +11 / +10 dB |
| morph_v7 | 1.43 | 0.01 | 2.06° | 1.43 / 1.80 / 1.30 | +7 / +8 | +11 / +10 |
| ext_throat_v7 (v7 #1) | 1.57 | 0.00 | 1.75° | 1.99 / 1.46 / 0.66 | +9 / +8 | +13 / +9 |
| tritonia_v9 | 3.26 | 1.25 | 0.29° | 0.29 / 0.50 / 0.88 | +2 / +3 | +4 / +4 |
| rosse_rect_cd | 4.58 | 2.47 | 0.08° | 0.19 / 0.34 / 0.57 | −1 / +1 | +2 / +3 |

On the 29-point verify grid the fold_warm feature is a ~half-octave plateau (Re z 1.54–1.80 from 682 to
896 Hz) with a very steep low edge (0.27 → 1.54 over 519 → 682 Hz). It is a mouth/cutoff hump, not a
needle. `load` = log2(lfp20·1.6/700) + max(0, 0.5 − min Re z ≥ 700 Hz) cannot tell such a hump from
broadband loading, and the linear detrend in `flat`/`flat_cv` absorbs the bump as tilt. The prior research
criterion (NOTES 2026-11-15: a DI rise is acceptable only if monotonic, continuous at the XO, **with no
in-band resonance**) is therefore not enforced by any term. Whether this hump is audibly worse after a
real 700 Hz crossover and driver is **not established** (ideal-source model; D6 measurement still blocked).

**F7 — The 0.47 J floor is mostly the loading edge, not directivity. VERIFIED.** Attribution of
screen→verify ΔJ over the published floor pairs: `load` 56 % of variance (all 256 and top-28 alike),
`flat_cv` 16–31 %; `cov_profile`, `rip`, `di_roughness` ≤ 5 %. Directivity sub-J (cov + rip + dislope +
di_roughness) has screen→verify SD **0.055 J on the top-28 cohort**, ~8× tighter than the published floor.
The families v10 calls "tied" are tied on an undersampled 500–650 Hz loading edge, not on directivity.

**F8 — Provenance defect. VERIFIED.** `runs/analysis/v10_rescore_2026-11-18/*/rescore.jsonl` stores the leaf
run name (`"screen"`) for runs nested under `study-*/`; 35 of the 271 audited rows (incl. the published
v10 leader fold_warm 1.4214 and ext_throat_v7 1.5710) cannot be located from the row. Across the fleet,
204 design hashes exist in >1 run dir with slightly different stored solves (picking the wrong one moved J
by up to 0.011); the audit script resolves each row to its own run (`run_dir_for`). Fix belongs in `tools/analysis/rescore_identity.py` (store the run path relative to `runs/`).

## Decisions (Fable senior, within delegation; no default changed)

1. **No `dislope` patch, no lobe term, no ripple-region change.** F1, F3, F4.
2. **Do not spend GPU on B6 matched reruns of fold_warm / morph / ext_throat on the current grid.** Their tie
   is the F7 loading-edge sampling; equal-budget reruns on the same grid cannot resolve it.
3. **Do not add new v7/v10 CMA continuations whose only aim is lower J** until item 4 reports; existing
   owner-requested jobs are left alone (owner rule: don't cut owner-requested jobs).
4. **PROPOSED, one small GPU job for the integrator's queue (not launched here; GPU lane is live):** dense
   low-frequency re-solve, 400–1400 Hz at 1/12 octave (~22 frequencies, the cheapest BEM band), of six
   stored geometries: fold_warm 688ffe811b6a and the fleet best, morph 436a4d221328, ext_throat_v7 best,
   tritonia_v9 3050a4666f51, rosse fd45d3b5e62f. Output: true Re(Z) and power-response shape through the
   crossover region; settles hump width/Q and the `load` sampling floor. `HORNLAB_GPU_LOCK=refuse`.
5. **PROPOSED owner question (decides the next score identity, if any):** "Loading to a 700 Hz crossover"
   — should a design meet it with a resonant Re(Z) hump of ~1.8× and a +10 dB power bump at 650–900 Hz,
   or should loading be judged on smooth/broadband Re(Z) with a penalty for in-band humps (the 11-15
   research criterion)? Only after item 4 and this answer would a new identity be justified; candidate
   terms: `load` on a smoothed/upper-capped Re z, and a power-response hump term relative to a smooth fit.
   Corridor enforcement (F2) should move back into `cov_profile` (score only the corridor-active
   frequencies, drop the 2.5–5.5 kHz up-weight for coverage) in the same identity, with `dislope` reduced
   accordingly; preserve all historical identities.
6. **PROPOSED for the brief owner:** the V corridor start (40–60° at 1 kHz) sits at the 480 mm envelope
   limit (F5). Either accept ~63° V at ~1 kHz or move the V onset to ~1.2 kHz; scoring a physically
   unreachable target only adds a constant and noise.
7. **PROPOSED, CPU:** a corridor-compliance + smooth-loading shortlist (directivity sub-J ranked with the
   0.055 J floor) as the finalist menu, instead of a single scalar winner. `rosse_rect_cd` / `tritonia`
   are the best-directivity families the current J buries.
