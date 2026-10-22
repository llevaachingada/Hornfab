# Senior architecture report, 2026-10-22: where hornlab-search sits, and what to do next

Author: senior reviewer (cloud, Claude). Audience: the user and the local GPU agent. Read this first; details live in
`docs/BOUNDARY_LAB_0.5_RESEARCH.md` (findings), `docs/BOUNDARY_LAB_INTEGRATION_PLAN.md` (plan) and
`docs/research/boundary_lab_0.5/` (cited inventories). No code changed by this report.

## 1. Where hornlab-search sits

| Layer | Owner | Job | Optimizes? |
|---|---|---|---|
| BEAT Engine (solver maths) | JW Sound | Computes the sound field (BEM/FEM) | No |
| Boundary Lab (desktop app) | JW Sound | Designs a whole speaker by hand: box, drivers, ports, crossover | No (0.5.0 plugin hooks could host one, GUI only) |
| HornLab libraries + waveguide-generator | Magnus (m3gnus) | Horn geometry (mesher), a wrapped copy of the BEAT solver, plots; a horn GUI | No |
| **hornlab-search (this repo)** | us | Finds horn geometry **by objective**, keeps every result, learns a surrogate | **Yes, that is its job** |

Neither app does what this repo does. Our value sits above both; we should not move inside either.

## 2. Decision on Boundary Lab 0.5.0: sidechain, do not become a plugin

- We do **not** need to conform to Boundary Lab's plugin API. Boundary Lab is used **as is**, in its own
  environment, by passing files: we export a solve-ready project; optionally we call its command-line solver
  (`blab project solve`) for a second opinion. Zero changes on either side.
- **Magnus's libraries stay our engine.** They live in our `.venv`; Boundary Lab and its BEAT 0.6.0 live in a separate
  install. They never share packages (Boundary Lab refuses any BEAT other than 0.6.0, so it must not be installed in
  our venv).
- The two use different versions of the solver maths (our vendored copy, about 2026-10-07, vs BEAT 0.6.0). The
  cross-check measures the difference against the frozen CP-7b rule (< 0.2 dB). The long-term clean fix is Magnus
  updating `hornlab-beat-bem` to BEAT 0.6.0; that is his call, not a blocker.
- The plugin (plan phase BL-3) is **parked**: it mainly helps other Boundary Lab users, its API is 5 weeks old, and it
  carries the most upkeep. Build it only on request.

**Revised priority (supersedes the phase order in the integration plan):**
1. Core first (section 3 items 1-5).
2. BL-1 project export (small, no risk; lets the user finish box/crossover in Boundary Lab).
3. BL-2 headless cross-check (one evening once export works).
4. Engine question (move to BEAT 0.6.0 upstream, more dofs on 8 GB): conversation with Magnus.
5. BL-3 plugin: parked.

## 3. Project status and what is left to see results

State on `main` (`2311f92`, 2026-10-22): the local merge lane fast-forwarded `main` to `6d1d5c7` (all CP-8 work, issue-#13
fixes, cloud FREEFORM work, Boundary Lab docs; offline suite 533 passed), committed the 7 GPU runs' summaries to
`docs/evidence/runs/`, and closed PRs #12/#14 as superseded. Results:

| Run | Family | Best J vs seed |
|---|---|---|
| osse_baseline 1500 | OSSE | 22.59 -> 6.11 (-73 %) |
| icw_termination 800 | ICW | 55.74 -> 12.20 (-78 %) |
| throat_adapter 400 | OSSE | 9.16 -> 5.98 (-35 %) |
| freeform_hv 722 | FREEFORM | 33.31 -> 30.54 (-8 %, only 3 knobs; fixed by `freeform_sculpt.yaml`) |

Dataset 3556 records (verify OK). CP-8d: Stage A surrogate FAILED its gates (held-out 285 < 500; top-20 overlap and
beamwidth MAE short); model not used.

To do, in order:

| # | Task | Where | Effort |
|---|---|---|---|
| 1 | Look at existing results: `hornlab-search report runs\<dir>` for each CP-8c run | local, no GPU | 10 min |
| 2 | ~~Merge PR #14~~ DONE 2026-10-22 (main = `2311f92`). Note: the CONTINUITY "Next action" still lists CP-8d train/propose/round; CP-8d already ran and FAILED its gates (2026-10-14), so do not re-run it before the data top-up (item 5) | local | done |
| 3 | `docs/HANDOFF_LOCAL.md` section 6b: FREEFORM symmetry check, then a 60-candidate sculpt search | local GPU | about 1 h |
| 4 | Add a CLI for STEP export (`mesh/build.py::export_step` exists, nothing calls it) so a winner can be 3D printed / opened in CAD | cloud | small |
| 5 | OSSE data top-up to reach 500 held-out for the surrogate gates (about 3,400 records on the osse_baseline grid) | local GPU, overnight | 1-2 nights |
| 6 | BL-1 export to Boundary Lab | cloud | about 1 day |

## 4. Open decisions for the user

1. Approve the revised priority in section 2.
2. Who is who: the HornLab author (docs say "Collin", account `m3gnus`, user says Magnus) and who proposed the NN
   surrogate (user: Colin). Plan files are frozen; a correction goes in a non-plan doc once confirmed.
3. FREEFORM full-vs-quarter pass bar (proposal in `NOTES_FOR_SENIOR.md`, 2026-10-14).
4. CP-8d data top-up (GPU nights) and widening `n` / `hold_end` bounds (probe first).
5. Contact JW Sound (headless result reader, worker shutdown) and Magnus (engine drift, mesher wall ports).

## 5. Branch map

| Branch | State |
|---|---|
| `main` | **Everything** (Waves 0-3, CP-8, issue-#13 fixes, FREEFORM sculpt, Boundary Lab docs, GPU-run summaries) + this report |
| `claude/wave-3-implementation-review-2dk4qe`, `ccr-455d2184-yj5zk4` | Ancestors of `main`; PRs #12/#14 closed as superseded. Work from `main` from now on |

Oracle follow-ups recorded by the local merge lane (non-blocking, see `docs/ISSUES.md`): `compare` with an empty
frequency list raises IndexError; the `exponent` alias resolves to the first superellipse station only.
