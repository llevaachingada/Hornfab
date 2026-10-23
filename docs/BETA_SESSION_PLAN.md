# Beta session plan (2026-10-23)

Two people, one 8 GB GPU: the owner (drives the GPU) and an applied-mathematician collaborator (reviews the
objective and the evidence). Commands come from `docs/BETA_QUICKSTART.md`; measured timings are in
`docs/evidence/BETA_READINESS.md` (F).

## Agenda (about 2 h 30)

| Time | Step | Who | GPU |
|---|---|---|---|
| 0:00-0:10 | `doctor` (expect 11 checks, 0 failed); `gpu-clean` if a host is listed | owner | no |
| 0:10-0:30 | What the tool claims and where each claim comes from (below); Known limits | both | no |
| 0:30-0:50 | `families --brief` on each brief; `campaign --tier dry-run --families all` | owner | no (meshing only) |
| 0:50-1:00 | Screen campaign `--families conical,exponential` on the axi brief (~6 min) | owner | **yes** |
| 1:00-1:30 | Review page: objective definition, compare-tier leaderboards, open questions | mathematician | no |
| 1:30-1:45 | `report` and `export-step --top 1` on the live run; `compare` two runs | owner | no |
| 1:45-2:15 | Open questions (s9 of `docs/TYPOLOGY_PLAN.md`; review page questions) | both | no |
| 2:15-2:30 | Write down decisions and problems (format below); `gpu-clean` | owner | no |

## Who drives the GPU

Only one GPU job at a time. `search`, `run` (not `--dry-run`), `verify`, `selftest`, `campaign` (not
`dry-run`) and `surrogate round` take a lock (`runs\.gpu.lock`). A second GPU command fails at once with
`GPU busy: <user> running "<command>" (pid ...) since <time>` (exit 3). A lock left by a dead process is taken
over automatically. After an interrupted job, or before handing over, run `hornlab-search gpu-clean`. It
refuses while another live job holds the lock; `--force` overrides that and kills a running solve.

**Run live:** `dry-run` tiers, and `screen` on two or three cheap families (5-15 min).
**Never run live:** the `compare` tier (1.5-2 h). Its results from the night before are on the review page.

## Where each claim comes from

- Geometry: Magnus's `hornlab_mesher` (pinned b922e807). Classical profiles come from textbook formulas, and
  Magnus's own FREEFORM evaluator reproduces them within 0.2 mm (V2, `docs/evidence/TYPOLOGY_VERIFY.md`).
- Acoustics: `hornlab_beat_bem` on the GPU, verified against the exact pulsating sphere (0.020 dB) and the CPU
  solver `hornlab_bempp_bem` (0.039 dB) (`docs/evidence/SOLVER_VERIFY_2026-10-22.md`).
- Textbook behaviour: conical loading (kx0)^2 / (1 + (kx0)^2), exponential cut-off, tractrix beaming (V5).
- Mesh convergence: epw 6 vs 8 measured (C2 in `BETA_READINESS.md`); axi typologies run at epw 8.
- Rankings: `screen` = one CMA-ES seed, a coarse ordering only. `compare` = two seeds; a ranking is claimed only
  where the medians separate by more than both spreads.

## For the mathematician

- J is a hand-weighted sum of terms in different units (coverage deg, ripple dB, DI dB, DI slope dB/decade,
  flatness, loading). The weights live in the brief YAML.
- Beamwidth is a -6.02 dB threshold crossing, so J has kinks. CMA-ES does not need gradients.
- `load` penalises Re z_throat below an arbitrary z_min = 0.7.
- 12 log-spaced frequencies (500-5500 Hz) cannot see narrow resonances.
- The open questions are on the review page and in `docs/TYPOLOGY_PLAN.md` s9.

## Known limits (say these out loud)

- Free-standing horn with a shell: no baffle, room or enclosure; rigid lossless walls; no air absorption.
- Source: rigid uniform-velocity spherical cap. No phase plug, no compression chamber. The brief's
  `source.cap: auto` is not applied: every design uses the mesher default cap.
- Nothing above **5.5 kHz** is solved or scored on an 8 GB GPU, so high-frequency horns cannot be judged.
- Shell: generated horns 3 mm, native configs 6 mm (mesher default).
- The surrogate model is inactive (its gates failed for lack of data).

## Do not try (and why)

- **Le Cléac'h**: disabled until a verifiable published construction is supplied; approximating it would be
  invented physics.
- **Widening bounds** on existing configs (`perturbed_osse_hv` `L_mm` is pinned): needs the owner's decision,
  and invalidates comparisons with earlier runs.
- **`band_hi_hz` above 5500**: exceeds the 8 GB dof cap; solves are refused or OOM.
- **Native configs under a smaller brief** (e.g. `osse_baseline`, `freeform_sculpt` under the 400 x 300 mm hifi
  brief): their seeds lie outside the envelope, so the leaderboard says "NO VALID DESIGN". That is expected, not
  a bug.
- `compare` tier live; two GPU jobs at once (the lock refuses); killing julia while a job runs (use `gpu-clean`).

## Reporting a problem

Paste: the exact command; the run directory (`runs\<dir>`) or `runs\campaign_<time>\campaign.json`; the last 30
lines of output; `doctor` output. OCCT "Statistics on Transfer" lines during `export-step` are normal and cannot
be suppressed.
