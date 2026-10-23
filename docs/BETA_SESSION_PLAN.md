# Beta session plan (2026-10-23, refreshed for the GUI)

Two people, one 8 GB GPU: the owner (drives the GPU) and an applied-mathematician collaborator (reviews the
objective and the evidence). **The GUI is the main path** (`hornlab-search gui`, http://127.0.0.1:8765, Home has a
four-step "How to use this" guide); the CLI commands in `docs/BETA_QUICKSTART.md` are the fallback and give the same
results. Measured timings are in `docs/evidence/BETA_READINESS.md` (F).

## Agenda (about 2 h 30)

| Time | Step | Who | GPU |
|---|---|---|---|
| 0:00-0:10 | `hornlab-search doctor` (expect 11 checks incl. disk space, 0 failed); `gpu-clean` if a host is listed; start `hornlab-search gui` | owner | no |
| 0:10-0:30 | What the tool claims and where each claim comes from (below); Known limits; GUI **Glossary** for every term | both | no |
| 0:30-0:50 | GUI **Typologies** (every family, brief compatibility, best result per brief) and **Campaigns** (compare-tier leaderboards from the night) | both | no |
| 0:50-1:00 | GUI **Launch**: campaign, tier `screen`, families `conical,exponential`, axi brief (~6 min). Dry-run first if unsure | owner | **yes** |
| 1:00-1:30 | While it runs: Home shows live progress; review the objective (below) and the compare evidence | mathematician | (running) |
| 1:30-1:45 | Open the finished run: beamwidth vs target, DI, isobars, **Evolution** time-lapse; **Export STEP**; **Compare** two runs | owner | no |
| 1:45-2:00 | The 12 kHz finalist verify (P2) runs: what 8-12 kHz shows and what it cannot (caveat below) | both | no |
| 2:00-2:15 | Open questions (s9 of `docs/TYPOLOGY_PLAN.md`; bound proposals in `docs/evidence/TYPOLOGY_COMPARE_2026-10-23.md`) | both | no |
| 2:15-2:30 | Write down decisions and problems (format below); `gpu-clean` | owner | no |

## Who drives the GPU

Only one GPU job at a time. `search`, `run` (not `--dry-run`), `verify`, `selftest`, `campaign` (not
`dry-run`) and `surrogate round` take a lock (`runs\.gpu.lock`). A second GPU command fails at once with
`GPU busy: <user> running "<command>" (pid ...) since <time>` (exit 3). A lock left by a dead process is taken
over automatically. After an interrupted job, or before handing over, run `hornlab-search gpu-clean`. It
refuses while another live job holds the lock; `--force` overrides that and kills a running solve.

**Run live:** `dry-run` tiers, and `screen` on two or three cheap families (5-15 min). The GUI disables GPU
actions while the lock is held and re-enables them when it is released (the server re-checks on every launch).
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
- 12 log-spaced frequencies (500-5500 Hz) cannot see narrow resonances; the isobar plots interpolate between them.
- The open questions are on the review page and in `docs/TYPOLOGY_PLAN.md` s9.

## Known limits (say these out loud)

- Free-standing horn with a shell: no baffle, room or enclosure; rigid lossless walls; no air absorption.
- Source: rigid uniform-velocity spherical cap. No phase plug, no compression chamber. The brief's
  `source.cap: auto` is not applied: every design uses the mesher default cap.
- Search, screen and compare stop at **5.5 kHz** on the 8 GB GPU. Above that there is only a **12 kHz verify pass**
  for the small typology finalists (NEXT_DEV_PRIORITIES P2, `docs/evidence/HF12K_VERIFY_2026-10-23.md`; GUI runs
  named `...-verify-...`). Above ~7.9 kHz (first cross mode of a 1-inch exit) a real compression driver is not a
  uniform cap, so **8-12 kHz results compare geometries, not drivers**. 12 kHz SEARCH and big horns at 12 kHz need
  P1 (a solver change, post-beta).
- Shell: generated horns 3 mm, native configs 6 mm (mesher default).
- The surrogate model is inactive (its gates failed for lack of data).

## Do not try (and why)

- **Le Cléac'h**: disabled until a verifiable published construction is supplied; approximating it would be
  invented physics.
- **Widening bounds** on existing configs (`perturbed_osse_hv` `L_mm` is pinned): needs the owner's decision,
  and invalidates comparisons with earlier runs.
- **`band_hi_hz` above 5500 for a search**: exceeds the 8 GB dof cap; solves are refused or OOM. The `*_12k.yaml`
  briefs are for `verify --brief` only.
- **Native configs under a smaller brief** (e.g. `osse_baseline`, `freeform_sculpt` under the 400 x 300 mm hifi
  brief): their seeds lie outside the envelope, so the leaderboard says "NO VALID DESIGN". That is expected, not
  a bug.
- `compare` tier live; two GPU jobs at once (the lock refuses); killing julia while a job runs (use `gpu-clean`).

## Reporting a problem

Paste: the exact command; the run directory (`runs\<dir>`) or `runs\campaign_<time>\campaign.json`; the last 30
lines of output; `doctor` output. OCCT "Statistics on Transfer" lines during `export-step` are normal and cannot
be suppressed.
