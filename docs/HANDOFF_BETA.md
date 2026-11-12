# HANDOFF: hornlab-search beta-readiness pass

Written 2026-10-22 21:30 EDT by the previous local orchestrator. Continue from `main` (see `git log -1`) of
`llevaachingada/Hornfab`, local clone `C:\Users\hunte\Hrns\hornlab-search`. The outer folder `C:\Users\hunte\Hrns`
is a different, empty repo: ignore it.

> **After the beta, the next development round starts with `docs/NEXT_DEV_PRIORITIES.md`** (P1: fused/direct CUDA
> Burton-Miller assembly to lift the 8 GB memory ceiling; P2: 12 kHz finalist pass; P3: Metal backend for the Mac).
> Do NOT enable P1 during the overnight queue or the beta: one solver for all comparison and surrogate data.

## 0. Who you are, how you work, and what "done" means

- **Model and effort: run as Claude Opus at medium effort.** You are the orchestrator and decision maker.
- **Subagents: at most 2 at a time, Haiku or Sonnet**, for menial or well-scoped work: repo ingest and
  summarising, reading upstream repos, writing tests, small coding tasks, doc updates, read-only reviews. Give every
  subagent an exact file-ownership list, tell it not to commit, and keep it OFF the GPU unless you explicitly hand it
  a GPU slot. You review and integrate everything they produce; you make every decision, run every GPU job yourself,
  and own every commit.
- Machine: Windows, RTX 4060 Laptop 8 GB. Interpreter `.venv\Scripts\python.exe`, CLI `.venv\Scripts\hornlab-search.exe`.
- **Done means:** the user and an applied-mathematician collaborator can run a beta session from
  `docs/BETA_QUICKSTART.md` without a crash, a misleading number, or a GPU pile-up; every claim the tool makes is
  traceable to Magnus's mesher, the verified BEM solver, or published horn theory. Nothing invented.

## 1. Read first, in this order (~20 min)

1. `CLAUDE.md` (rules, file ownership, GPU/Julia hygiene: binding).
2. `docs/CONTINUITY.md`, the 2026-10-22 entries from ~17:35 onwards.
3. `docs/TYPOLOGY_PLAN.md` (v2: s2 adversarial table, s3 briefs, s4 generators, s9 verification ladder).
4. `docs/evidence/SOLVER_VERIFY_2026-10-22.md`, `TYPOLOGY_VERIFY.md`, `TYPOLOGY_SCREEN_2026-10-22.md`.
5. `docs/ISSUES.md` (TO-DO list at the bottom).
6. `docs/BETA_QUICKSTART.md`, `docs/research/TIME_DOMAIN_RINGING.md`.

## 2. Non-negotiable rules

- Every push updates `docs/CONTINUITY.md` (new dated entry at the top) and `docs/ISSUES.md` in the same commit. Check
  the real pytest exit code before committing. Push to `main` (the established local lane).
- One GPU job at a time. Before and after every GPU step clear this project's julia AND BEAT `worker_host` processes
  (`hornlab_search/search/hygiene.py` does both) and record `nvidia-smi` memory.used. Never leave a host warm at the end.
- Never edit `docs/plan/**`, the frozen `Family` contract (`OSSE`, `R-OSSE`, `ICW`, `FREEFORM`), gate thresholds or
  tolerances. Never loosen a test.
- No bound widening on existing configs without the user's OK (open item: `perturbed_osse_hv` `L_mm` pinned). No OSSE
  data top-up, no Boundary Lab work without the user's OK.
- Le Cléac'h stays DISABLED until the user supplies a verifiable published construction. Do not approximate it.
- Horn numbers live in YAML, never in code.

## 3. Current state (short)

- Solver verified 2026-10-22: GPU tests 18/18; analytic pulsating sphere 0.020 dB; beat_cuda vs bempp_cpu 0.039 dB.
- Typologies: classical generators (conical, exponential, hypex, tractrix, OSSE meridian sampled from Magnus's
  `profile_points`) and hybrids (H/V, convex blend, monotone perturbation) materialise as ordinary FREEFORM designs;
  briefs fix driver, envelope, target, weights; `families` / `campaign` CLI (tiers dry-run/screen/compare,
  `--max-evals` for equal search); failure cache keyed by design+mesh+solve+library SHAs; brief size envelope
  enforced for every family; report-only loading scalars `f_load_hz`, `z_ripple`, `z_mean_band`.
- Verification V1–V5 PASS (Magnus's FREEFORM evaluator within 0.2 mm of each analytic curve; 16 vs 48 anchors
  within 0.1 dB; textbook loading/beamwidth behaviour). V7: one fair screen campaign per brief, leaders in
  `TYPOLOGY_SCREEN_2026-10-22.md`.
- Offline suite: 736 passed. Review page for the collaborator:
  `https://claude.ai/artifact/E9YwQVZHnTgya8R7ovwjua` (built by `tools/review/`).

## 4. Work items, in order, each with acceptance

### A. Grounding audit: dependencies and upstream (no GPU; good subagent task: repo ingest)
1. `hornlab-search doctor` → 10/10 incl. `pinned-shas`. Record installed SHAs of `hornlab_mesher` (dist
   `hornlab-waveguide-mesher` 0.2.4), `hornlab_beat_bem` 0.2.0, `hornlab_bempp_bem` 0.2.0, `hornlab_plots` 0.1.3 vs
   `pyproject.toml` / `TOOLCHAIN.md`.
2. Check Magnus's upstream repos (GitHub `m3gnus`: mesher, beat-bem, plots, waveguide-generator) for commits newer
   than our pins. **Do not bump.** List what changed, especially FREEFORM, `profile_points`, the outer-shell curvature
   guard, the source cap, symmetry; write findings to ISSUES. A bump needs its own verification ladder and the user's OK.
3. We call semi-public mesher APIs (`profile_formulas.profile_points`, `build_freeform_geometry`, the FREEFORM curvature
   guard): add a guard test pinning their signatures (pattern of the existing `build_point_grid` guard).
Accept: SHA table in a new `docs/evidence/BETA_READINESS.md`; upstream diff summary in ISSUES; guard test green.

### B. Data integrity (no GPU)
1. `dataset\` is the **only** copy. The `dataset_backup_20261013\` and `dataset_backup_20261022\`
   snapshots were deleted on 2026-10-30 after both were re-verified as strict subsets (0 missing
   `(design_hash, solve_hash)` ids), and the owner waived an off-machine backup. Treat data loss as
   final; run `hornlab-search dataset verify` before any migration.
2. `hornlab-search dataset verify` → OK; `dataset stats` pasted.
3. Known gap: plan R8 says records carry the brief hash; today generator/brief provenance is only in `search.ndjson`
   rows and `design.json`, not in dataset records, and the store now mixes objectives scored under different briefs.
   Preferred fix: add optional, additive `generator` + `brief_hash` record metadata (`dataset/record.py`,
   `search/evaluate.py::_persist`) with a test; or make `surrogate train` refuse mixed-brief data. Metric curves are
   target-free and remain valid.
4. `surrogate train/propose/round` on a generator config must fail with a clear message, not a traceback.
Accept: verify OK, R8 closed or fenced with a test, surrogate refusal tested.

### C. Physics audit: no fallacies (one GPU check)
Record each conclusion in `BETA_READINESS.md` with file:line or a measured number; limitations go to the quickstart's
"Known limits".
1. Throat impedance normalisation with the spherical source cap (rigid, uniform velocity, default radius 3.75·r₀):
   confirm area/velocity used for `z_throat_real` (`metrics/impedance.py`, beat solver path). V5 conical matched
   (kx₀)²/(1+(kx₀)²); this is a confirmation.
2. **Mesh resolution above 2.5 kHz is unmeasured since CP-7.** On the GPU, solve the `osse_axi` seed and the
   `perturbed_osse_hv` best design at epw 6 and epw 8 (within the dof cap) and `hornlab-search compare`. Accept:
   dB metrics ≤ 0.1 dB, beamwidth ≤ 1°. If not: raise screen epw in the typology configs, say so, re-run the screens.
3. Band limit: 8 GB caps scoring at 5.5 kHz. State plainly in the quickstart and on the review page that nothing above
   5.5 kHz is scored or solved in screen mode (matters for HF horns).
4. Boundary conditions: free-standing horn with shell; no baffle/enclosure; rigid lossless walls; no air absorption.
   The mesher has an `infinite-baffle` mode (`families.MODES`); do not enable tonight; list as a future brief option.
5. Source model: rigid uniform-velocity spherical cap; phase plugs and compression chambers out of scope. Brief
   `source.cap: auto` not applied (FREEFORM keys do not expose the cap); identical for every design in a campaign.
6. Objective caveats for the mathematician (review page questions already cover most): hand-weighted sum of terms
   with different units; beamwidth is a −6.02 dB threshold crossing (kinks); `load` uses an arbitrary z_min = 0.7;
   12 log-spaced frequencies cannot see narrow resonances.
7. Shell: generated horns use a 3 mm outer shell (mesher curvature guard: thickness × curvature < 0.4); native configs
   use the mesher default; the envelope check includes the shell. Record both numbers.
Accept: every item has a recorded conclusion; C2 measured; quickstart "Known limits" updated.

### D. Bulletproofing for two people on one GPU (code; subagent can write it, you review)
1. **GPU lock**: process-wide lock file (e.g. `runs/.gpu.lock` with PID, user, command, start time) acquired by
   `search`, `run` (non-dry), `verify`, `selftest`, `campaign` (non-dry), `surrogate round`. A second caller fails fast
   with "GPU busy: <who/what> since <time>"; stale locks (PID gone) are taken over. Offline test with a fake PID.
2. `hornlab-search gpu-clean`: calls `hygiene.clear_julia()` and prints VRAM; documented in the quickstart.
3. Ctrl-C a screen campaign mid-run: hygiene still runs, the lock is released, `leaderboard.md` written with partial
   results (short GPU test, ~2 min).
4. Disk: record free space for `runs/`, `cache/`, `dataset/`; doctor warns below 10 GB free.
5. Paths: every quickstart command from a different working directory with absolute paths (`campaign`, `report`,
   `export-step`).
Accept: lock and `gpu-clean` tested; Ctrl-C leaves a clean state; doctor disk check; full offline suite green.

### E. Compare tier on the leaders (GPU ~1.5–2 h; overnight or first thing; tell the user the estimate first)
```
hornlab-search campaign --brief examples\briefs\axi_90x90_1in.yaml  --families osse_axi,blend_osse_tractrix,hypex --tier compare
hornlab-search campaign --brief examples\briefs\hifi_90x60_1in.yaml --families perturbed_osse_hv,hyb_osse_h_hypex_v,rosse_baseline --tier compare
```
2 CMA seeds per family, budget max(150, 25·knobs) (`perturbed_osse_hv`: 18 knobs → 450 per seed, ~40 min for that
family alone). Report median and spread; claim a ranking only where medians separate by more than both spreads.
Copy each `leaderboard.md` and `campaign.json` to `docs/evidence/campaigns/`, write
`docs/evidence/TYPOLOGY_COMPARE_<date>.md`, rebuild the review page:
`.venv\Scripts\python.exe tools\review\build_review_data.py tools\review\review_data.json "20261022T142919Z-screen-1db72d|freeform_sculpt 400|budget 400" --campaign <compare campaign.json> ...`
then `tools\review\assemble.py tools\review`, then `node --check` the inline script; republish to the existing URL
(read it with the Artifact tool first) or ask the user to.
Accept: both campaigns finished, no julia / worker host left, evidence written, page rebuilt with no horizontal
overflow at desktop and 400 px.

### F. Beta rehearsal (timed; must pass before you declare done)
Fresh PowerShell, follow `docs/BETA_QUICKSTART.md` verbatim: `doctor` → `families --brief` (each brief) →
`campaign --tier dry-run --families all` (each brief) → screen campaign on `conical,exponential` (~6 min) → `report`
→ `export-step --run <dir> --top 1` → `compare` → review page build. Time each step; fix every friction point (paths,
unclear output, stale doc lines, unexplained warnings; OCCT "Statistics on Transfer" spam cannot be suppressed: add a
one-line note).
Accept: runs without hand-holding; timings in `BETA_READINESS.md`; quickstart matches reality line for line.

### G. Beta session pack (docs)
`docs/BETA_SESSION_PLAN.md`: agenda with times; who drives the GPU (one job at a time, enforced by the lock); what the
mathematician reviews (review page, objective definition, s9 open questions); which campaigns to run live (cheap,
never `compare` live); how to report a problem (run dir, `campaign.json`, exact command, last 30 lines of output);
the known-limits list from C; what NOT to try and why (Le Cléac'h, bound widening, HF band above 5.5 kHz, native
configs under a smaller brief → "NO VALID DESIGN"). Update README's command list.

## 5. Known issues you inherit (ISSUES)
- `perturbed_osse_hv`: 36 % invalid in screen, `L_mm` pinned. Widening needs the user's OK; you may propose numbers
  grounded in the envelope.
- Native configs sized for other targets show "NO VALID DESIGN" under the 400×300 brief: labelled, expected.
- `search_smoke` (legacy) cannot dry-run under a 5.5 kHz brief: harmless.
- `compare` IndexError on an empty frequency list (oracle follow-up): fix if trivial.
- NOT for the beta: stage-2 transient/waterfall analysis, BL-1 Boundary Lab export, surrogate top-up.

## 6. Stop and ask the user if
- any verification (C2, compare medians, a re-run of V4/V5) contradicts an earlier result;
- an upstream change in Magnus's repos would require a bump to stay correct;
- a fix would touch `docs/plan/**`, the `Family` contract, or a gate threshold;
- the GPU OOMs or hangs from a clean state (CLAUDE.md GPU rule 7).

## 7. Final report to the user
Tables: what was run, PASS/FAIL, key numbers; open decisions; julia / worker host still running (must be none);
beta-day checklist. Never write "tests pass" without the pasted exit code.
