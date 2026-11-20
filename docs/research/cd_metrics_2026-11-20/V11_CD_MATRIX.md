# V11 CD matrix — design and grounding (2026-11-20)

Status: **owner-directed implementation** (owner answer 2026-11-20: new objective v11 + report,
loud-home 110 dB max, not a pro high-SPL tuning; 8-family shortlist). This file is the
`hornlab-typology-research` dossier for the new objective/directivity terms and the build spec for
the implementation. It does **not** rescore any stored run and does not change any historical J.

## 0. Source table

| Source | What it gives us | Status |
|---|---|---|
| Sridhar, Tylka & Choueiri, *Generalized Metrics for Constant Directivity*, JAES **67**(9):666–678, 2019, DOI `10.17743/jaes.2019.0022` (local PDF `Sridhar_JAES_CDMetrics.pdf`) | Five metrics, exact formulas (Eqs. 2–13, A.14–A.15, B.17), measurement conditions, per-metric failure modes, application guidance | primary, peer-reviewed |
| IEC 60268-5 §20.6; Klippel Application Note 40 | Band-mean-referenced frequency-response smoothness (the defensible fixed-angle reference) | standard / secondary |
| CTA-2034-B | Listening-window definition (±30° H, ±10° V) | standard |
| `docs/research/V4_SCORING_REVIEW_2026-10-27.md` (this repo) | DI std and polar correlation were already identified as the Princeton constancy pair; `distd` exists but is weight 0; tolerance-normalisation and worst-valid ordering lessons | in-repo evidence |
| `docs/research/ripple_hf_2026-11-19/{HANDOFF,MEASUREMENT_TAXONOMY,MANDATE_STATUS}.md` + `docs/evidence/spectral_ripple_audit_2026-11-19/` | Fixed-angle spectral residual is a real gap; band-mean reference is IEC/Klippel; trend reference is exploratory; residual is ρ=0.885 redundant with `rip`; do not promote without owner; M1/M4/M5 penalize legitimate narrowing | in-repo research |
| `docs/knowledge/imported/HornFab_Research_Knowledge_Base_2026-11-16.md` HT-15/HT-16 | Citation record and intended use | in-repo |
| `docs/research/typologies/NON_CD_OBJECTIVE_PROFILE_RFC_2026-11-16.md`; AGENTS.md | CD is a brief-declared goal, never a family default; never impose CD on non-CD horns | in-repo rule |

Corrections / limits carried into the design:
- The paper's M1, M4 and M5 **penalize a legitimately narrowing horn by construction** (M4:
  "penalizes broadband spectral trends in directivity more severely than narrowband deviations";
  M1 is biased toward wide contour sections). V11 is therefore **CD-brief-only** and its 8-family
  shortlist excludes Le Cléac'h/Iwata/rolled-B3 progressive-narrowing families.
- The paper explicitly **declines to normalize Ω_CD by coverage** (it would mix CD and directivity).
  M3 is therefore **report-only** in v11; the brief's coverage corridor already fixes the intended
  directivity.
- The ripple audit measured that the trend-reference fixed-angle residual is largely redundant
  with `rip` (ρ=0.885) and that the band-mean reference reverses the ranking. V11 uses the
  **band-mean** reference in a declared HF band and keeps `rip` at reduced weight; it does not call
  the new term "ripple".
- The BEM source is a uniform-velocity cap; above f11 (~5.6 kHz at 18 mm) the absolute HF is a
  model claim. V11 reports it; it does not create a real-driver claim.

## 1. What v11 scores

V11 = v10 (v9 corridor + preferred-edge ripple) **plus** a CD block, as a new identity. It never
edits v9/v10 and never ranks against them.

| term | paper metric | raw definition | units | weight | tolerance | why |
|---|---|---|---:|---:|---:|---|
| `cov_profile` | — | existing v10 corridor cost | — | 1.0 | 3.0° | keep the intended 80×50 coverage; a perfectly CD 20° beam must not win |
| `cd_lw` | **M2** `⟨C_LW⟩` | directional average of level-normalised spectral distortions in the ±30°H/±10°V window | dB | 1.5 | 1.5 dB | primary for loud-home critical listening (paper: M2/M3 best in quiet/treated/static) |
| `cd_di_std` | **M4** `σ_DI` | log-frequency-weighted std of full-sphere DI over the score band | dB | 0.75 | 1.0 dB | secondary (paper: best for high SPL; 110 dB max is the owner's ceiling, not a PA target) |
| `cd_nacc` | **M5** `Φ̄` | mean normalised aligned cross-correlation of H/V polar power responses over all frequency pairs; cost = `1 − Φ̄` | — | 0.75 | 0.02 | secondary; catches pattern-shape change at constant DI |
| `offaxis_smooth` | — (ripple work) | worst band-mean fixed-angle residual at the listening-window and preferred-edge angles, 2.5–8 kHz | dB | 1.0 | 1.0 dB | integrates the 2026-11-19 off-axis work at the HF band where `rip` is weakest; band-mean reference (IEC/Klippel) |
| `rip` | (M1 proxy) | existing v10 detrended angular ripple | dB | 0.5 | 1.0 dB | keep angular lobing guard; reduced weight because `cd_lw`/`offaxis_smooth` now charge the frequency axis |
| `flat` | — | existing on-axis detrended flatness | dB | 0.5 | 1.5 dB | on-axis tonal balance |
| `flat_cv` | — | existing constant-velocity LF flatness | — | 0.5 | 1.5 | keep LF behaviour |
| `load` | — | existing Re(z) loading | — | 1.0 | 0.3 | 700 Hz home horn must load; Crowe-X's load deficit must still count |
| `dislope` | (M4 trend) | existing DI slope error against 0 dB/dec | dB/dec | 0.5 | 9.0 | keep a coarse trend guard; M4 owns the constancy |
| `di_roughness` | (M4 residual) | existing detrended DI roughness | dB | 0.5 | 1.0 | keep bumpiness separate from broadband trend |
| `cd_omega_2pi` | **M3** `Ω_CD/(2π)` | forward clean-region solid angle at 3 dB spectral distortion | 2π sr | **report only** | — | paper declines normalization; brief coverage already fixes the target |
| `cd_contour_pct` | **M1** `ε` | contour-line Fourier metric | % | **report only, deferred** | — | requires the paper's contour raster; not implemented in v11.0 (documented gap) |

Active scored set = the ten weighted rows above (all finite). Report keys are always emitted.
`cd_status` records `balloon` / `cuts_fallback` / `unmeasurable`.

### 1.1 Exact metric definitions used (paper equations)

- **M2** (`scalar`): `P = 10^(SPL/10)`; `P̄_d = Σ_k w_k P[k,d] / Σ_k w_k` (log-frequency weights);
  `D[k,d] = sqrt(P[k,d]/P̄_d) / sqrt(P[k,0]/P̄_0)`; `E = 10^|log10 D|`;
  `C[k] = sqrt(Σ_window w_d E² / Σ_window w_d)`; `⟨C_LW⟩ = 10 log10(Σ_k w_k C[k]² / Σ_k w_k)`.
- **M3**: `Ω_CD[k] = 4π Σ_{d in connected forward region} w_d`, where the region is the
  axis-connected set with `E[k,d] ≤ 10^(3/20)`; report `Ω_CD/(2π)` averaged over the band.
- **M4**: `σ_DI = sqrt(Σ_k w_k (DI[k] − mean_w)² / Σ_k w_k)`, `w_k` = trapezoid weights in
  `log10 f`, over the score band (f0 → band_hi).
- **M5**: `Φ_m[k,k'] = Σ_n P_mn[k]P_mn[k'] / sqrt(Σ_n P_mn[k]² Σ_n P_mn[k']²)`; `Φ = mean_m Φ_m`
  over the H and V half-planes; `Φ̄ = Σ_{k,k'} w_k w_k' Φ[k,k'] / (Σ w)²`.
- **Off-axis**: `offaxis_smooth = max_a fixed_angle_residual_db(f, spl_plane, angles, a,
  reference="band_mean", band_hz=(2500,8000))` over `a ∈ {±30°, ±40°}` (H) and
  `{±10°, ±25°}` (V). The function is `metrics/spectral.py:194`.

### 1.2 Why these weights

The owner's use is a **loud home system, 110 dB max** — not a live-sound PA. The paper's
application table: M1 best for reflective/dynamic critical listening; M2/M3 best for quiet/treated/
static critical listening; M4/M5 best for high-amplitude. At 110 dB the system is still a home
system, so M2 is primary, M4/M5 are secondary, and M1 is report-only. `cov_profile`/`load` are
kept as physical guards so the winner is a usable 80×50/700 Hz horn, not a CD curiosity.

**Seed calibration (CPU, archived SCOUT40 responses, band 700–8000 Hz, window 30/10).** Measured
before any GPU time, to check the tolerances are in a sensible range (not to rank the families):

| seed family | M2 LW dB | M3 Ω/2π | M4 σ_DI dB | M5 NACC | offaxis dB |
|---|---:|---:|---:|---:|---:|
| OSSE morph | 0.881 | 0.500 | 0.723 | 0.9890 | 1.658 |
| Crowe X OSSE | 0.516 | 0.708 | 0.485 | 0.9931 | 0.614 |
| R-OSSE rect (bridge; replaced) | 0.453 | 0.662 | 0.717 | 0.9936 | 1.146 |
| ext throat | 1.128 | 0.723 | 0.637 | 0.9850 | 1.701 |
| Klangfilm Lame (legacy; replaced) | 0.516 | 0.496 | 2.254 | 0.9704 | 1.372 |
| ATH petal | 0.862 | 0.712 | 0.932 | 0.9887 | 2.078 |
| biradial ES | 0.668 | 0.671 | 0.623 | 0.9857 | 1.143 |
| OSSE fold | 0.560 | 0.586 | 0.665 | 0.9897 | 1.656 |

The tolerances (1.5 dB LW, 0.02 NACC, 1.0 dB σ_DI, 1.0 dB offaxis) put these CD seeds in the
0.3–2.3 J range per term before weights; none is trivially zero or saturated. The two runnable
substitutes (ATH Tritonia v9, Klangfilm B3 soft) are measured from their own first 50-eval runs,
not assumed from these rows.

## 2. V11 parameter block

All CD parameters live in a new `objective.cd` mapping; v9/v10 keys and their validation are
untouched (v11 strips `cd` before building `V10Params`).

```yaml
objective:
  version: 11
  # ... every v10 key unchanged (ripple_region: preferred_edge, tolerances, ...)
  cd:
    band_hz: [700.0, 8000.0]          # M2–M4 score band (default f0..band_hi)
    window_h_deg: 30.0                # CTA-2034 / paper listening window
    window_v_deg: 10.0
    lw:      {weight: 1.5, tolerance_db: 1.5}
    di_std:  {weight: 0.75, tolerance_db: 1.0}
    nacc:    {weight: 0.75, tolerance: 0.02}
    offaxis: {weight: 1.0, tolerance_db: 1.0, reference: band_mean,
              band_hz: [2500.0, 8000.0],
              angles_h_deg: [-40, -30, 30, 40], angles_v_deg: [-25, -10, 10, 25]}
    report:  {omega: true, contour: false}
```

Weights are validated finite ≥ 0; tolerances finite > 0; angles within ±90; `band_hz` lo<hi and
inside the target band; `reference ∈ {band_mean, trend}`. `objective.cd` is required for v11
(no silent default; a v11 brief without it is a config error).

## 3. Files and registration (implementation contract)

- `hornlab_search/metrics/cd.py` — pure numpy: `power_from_spl_db`, `log_frequency_weights`,
  `di_std_log_db`, `nacc_matrix`, `nacc_mean`, `listening_window_metrics`, `cd_metrics`.
  `cd_metrics(metrics_or_arrays, resp, band_hz, window_h_deg, window_v_deg, offaxis...)` returns
  `{"cd_lw_db", "cd_di_std_db", "cd_nacc", "cd_omega_2pi", "offaxis_smooth_db", "cd_status"}`.
  Missing balloon → `cd_lw_db` cuts fallback, `cd_omega_2pi = nan`, `cd_status="cuts_fallback"`.
- `hornlab_search/objective/scalar_v11.py` — `V11Params`, `CDParams`, `objective_v11`,
  `resolve_v11_weights`, `worst_valid_v11_j`, `v11_score_identity`, `V11_ALL_KEYS`.
  `_objective_v11` calls `_objective_v10` for the base terms, reconstructs raw values from the
  normalized v10 terms, then overrides `total` with the v11 weighted sum. It never raises.
- `objective/versions.py` — add 11 (docstring).
- `search/evaluate.py` — import + `_OBJECTIVE_SCORERS[11]`, `make_context` branch.
- `config.py` — version allow-list, `objective.cd` validation, worst-valid gate.
- `objective/replay.py` — `REPLAY_VERSIONS`, `_dispatch`, `_params_from_block`, `_weight_for`,
  and the balloon arrays if the replay path needs them.
- `dataset/record.py` — version tuple is imported; no edit expected.
- Tests: `tests/test_metrics_cd.py`, `tests/test_objective_v11.py`.
  Required fixtures: omni pattern → `σ_DI=0`, `NACC=1`, `C_LW=0 dB`, `Ω_CD=2π`; frequency-narrowing
  Gaussian → `NACC<1`, `σ_DI>0`, `C_LW>0`; constant pattern in the window → fallback equals balloon;
  `reference="band_mean"` residual zero for a flat normalized cut; `worst_valid_v11_j <
  PENALTY_INVALID`; identity changes with any CD tolerance/weight; v11 replay of a stored response
  equals the in-process score.

## 4. Brief and lanes

- Brief: `examples/briefs/cd_v11_2026-11-20/room_landscape_80x50_700_hf1440_v11cd.yaml`,
  copied from `home_landscape_2026-11-18_v10/room_landscape_80x50_700_hf1440_v10.yaml` (same
  envelope 600×480×480, HF1440, F_X 700 Hz, corridor H 60–90 / V 40–60), with `version: 11` and
  the `cd` block above. New identity; never ranked against v7/v10.
- Configs: `examples/typologies/cd_v11_2026-11-20/` — eight copies of the home_landscape seeds,
  brief_file switched to the v11 brief, `search.budget: 50`, every other knob/bound unchanged:
  1. `cd11__osse_fold_warm` ← `hl__osse_rrect_fold_warm_v7.yaml`
  2. `cd11__osse_morph` ← `hl__osse_rrect_morph_v7.yaml`
  3. `cd11__ext_throat_hvlaw` ← `hl__ext_throat_hvlaw_v7.yaml`
  4. `cd11__ath_tritonia_v9` ← `hl__ath_tritonia_landscape_v9.yaml` (substitute: the R-OSSE-rect
     source is a GUI-preview bridge with a bridge-only rows type, not runnable in the stock search;
     see §4.1)
  5. `cd11__crowe_x_osse_cd` ← `hl__crowe_x_osse_cd_v7.yaml`
  6. `cd11__klangfilm_b3_soft` ← `hl__klangfilm_b3_soft_v10__p10_s1.yaml` (substitute: the legacy
     `klangfilm_lame` rows type is not in the stock `ROWS_TYPES`; this is the runnable current
     Klangfilm LAME **HV core** construction)
  7. `cd11__ath_core_petal` ← `hl__ath_core_petal_hvlaw_v7.yaml`
  8. `cd11__biradial_es` ← `hl__biradial_es_style_v7.yaml`

### 4.1 Runtime substitutions (2026-11-20)

The first dry-run of the queue reported `free-dimension check skipped (GeometryInvalidError: ...
unknown rows type 'rosse_rect' / 'klangfilm_lame')`. `design/generators/grid.py::ROWS_TYPES`
(line 140) contains only the stock rows types; `rosse_rect` is a GUI-preview bridge
(`tools/geometry/gui_preview.py`), and the legacy `klangfilm_lame` rows type is superseded by
`klangfilm_lame_hv_core` in the package generator. Running either as a stock search would refuse
the seed. The two lanes were replaced with stock-runnable CD constructions (`hl__ath_tritonia_landscape_v9`
and the package `klangfilm_lame_hv_core` B3 soft). This is a runnability substitution, not a
result: the paper's CD matrix is unchanged.
- Queue: `docs/queue/cd_v11_2026-11-20.yaml`, 8 jobs, `budget: 50`, `mode: screen`,
  `timeout_s: 3600`, `env: {HORNLAB_GPU_LOCK: refuse}`; `gpu-clean` before the first job; one GPU
  solve at a time. The GPU lock is stale-held by a dead pid at design time — the queue pre-hygiene
  must clear it (the `hornlab-night-queue`/`hornlab-gpu-job` rules).
- Report: `docs/evidence/cd_v11_2026-11-20/README.md` with the per-family CD matrix
  (best/median of the 50 evals for `cd_lw`, `cd_omega_2pi`, `cd_di_std`, `cd_nacc`,
  `offaxis_smooth`, plus coverage/load), run dirs, exit codes and decoded logs. No pooled J rank
  across versions; the matrix is the comparison.

## 5. Acceptance

1. `pytest tests/test_metrics_cd.py tests/test_objective_v11.py -q` passes.
2. `python -c "from hornlab_search.objective.versions import SUPPORTED_OBJECTIVE_VERSIONS as V; assert 11 in V"`.
3. One stored-response replay through v11 gives a finite J and the expected report keys; the
   analytic fixtures above hold.
4. All eight seeds pass `hornlab-shape-check` (mesh, dof cap, envelope, round throat) before the
   GPU queue.
5. The queue runs 8 × 50 valid evals with `HORNLAB_GPU_LOCK=refuse`, one solve at a time, and the
   evidence doc quotes the terminal bytes.
