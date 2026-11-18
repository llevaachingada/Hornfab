# OWNER DECISIONS RESOLVED — 2026-11-18 (cloud senior research pass, under owner delegation)

> **Authority.** The owner asked the cloud senior (2026-11-18, chat) to research every open owner
> question, decide it, set the decisions in code and leave no open questions. Every decision below
> is therefore an **owner-delegated senior decision**. Each one says what would reverse it. Where a
> decision needs a machine the cloud lacks (`runs/`, GPU, the Windows box, a blocked web host), it is
> decided here and its *execution* is assigned to the local agent in `LOCAL_AGENT_PROMPT_2026-11-18.md`.
>
> Labels: [verified] re-run in the cloud · [code-verified] read in code · [primary] repo evidence doc ·
> [external] web source (listed at the end) · [inferred] reasoning.
> Plan anchors: `ARCHITECTURE_AND_STAGED_PLAN_2026-11-17.md` §4, §8.2, §10.1, §10.2.

---

## 0. What the research says about how to score these horns (the frame for R1-R3)

| Source | What it says | Consequence for us |
|---|---|---|
| CTA-2034-A as explained by measurement reviewers [external] | Listening window = average of 9 responses spanning **±30° H, ±10° V**; early reflections and sound power are separate averages; predicted in-room response ≈ 12 % LW + 44 % ER + 44 % SP | A home horn is judged over a window, not one axis; reflections and power matter as much as the window |
| Olive preference model (patent form) [external, cross-checked against `HORN_WHITEPAPERS_2026-11-15.md:74`] | `Pref = 12.69 − 2.49·NBD_ON − 2.99·NBD_PIR − 4.31·LFX + 2.32·SM_PIR`: half-octave **smoothness** of on-axis and in-room curves dominates; no term rewards a flat DI or a specific beamwidth | Smoothness terms (ripple, flat, DI roughness) carry the preference evidence; a beamwidth **corridor** (range, not a point) is the honest coverage term |
| Geddes, "Geddes on Waveguides" thread (author, forum) [external] | Rate the **smoothness of the DI** and the bandwidth over which it is nearly flat; off-axis (≈ 22.5°) smoothness matters more than the axis; "no waveguide is perfectly constant directivity" | Supports slope-limited (not strict) constancy and DI-roughness scoring |
| Sridhar, Tylka, Choueiri, JAES 2019 (via `SIM_VS_REAL_HORN_2026-10-27.md`) [primary] | Constant-directivity is best captured by **DI standard deviation** and polar cross-correlation, not one slope number | Constancy belongs as a declared, tolerance-normalised term, measured on a dense grid |
| `SIM_VS_REAL_HORN_2026-10-27.md` [primary] | Ideal-source BEM ranks **pattern above cutoff** well; it does not predict level, loading or sub-cutoff behaviour | Pattern terms are trustworthy; loading terms need the physical anchor before they decide anything |
| BEM-vs-measurement literature (BERIM horn study, audioXpress PAFEC/AKABAK study, Behler & Makarski 2004) [external] | Directivity agreement is reported as "good" qualitatively; error depends on the real throat velocity and baffle; no standard ±° figure exists | Our anchor pass rule (±5° / ±3° presence, DI ±1 dB) is a predeclared engineering tolerance, not a literature constant; it stays as written in the anchor dossier |
| `S1_RANGE_SCORING.md`, `N3_GRID_INDEPENDENCE_V9.md` [primary] | strict vs slope constancy share 18/20 of the top 20; constancy needs 116 dense points; the 18-vs-29 frequency residual is 0.113 J (v9) / 0.205 J (with constancy) | The constancy variant is its own identity on a 116-point grid and must publish its own floor before it ranks anything |

**Overall verdict on scoring (inferred from the table):** v10 (corridor coverage + ripple over the
`preferred_edge` window + DI slope + DI roughness + on-axis flatness + flat CV + loading) is consistent
with the preference evidence. No new objective version is created now: the next scoring change waits
for the physical anchor (D6), which is the only thing that can say which score predicts a real horn.

---

## 1. Decisions

### Scoring and briefs (WP 1.1-1.5)

| # | Question (source) | Decision | Evidence | Set in code / files | Reverses if |
|---|---|---|---|---|---|
| **R1** | C1 coverage target; which score do nights use | Nights keep **v7** (`room_landscape_80x50_700_hf1440_v7`). **v10** is the shipped second score: corridor H 60-90° (pref 80) from 700 Hz, V 40-60° (pref 50) from 1000 Hz, loading on. The H 60-80° range in S1 / SCORING_RANGE_PROPOSAL was a placeholder; the owner's 11-17 answer (60-90) wins | owner 11-17 C2 block [primary]; corridor = range not point (Olive/CTA, §0) | `examples/briefs/home_landscape_2026-11-18_v10/room_landscape_80x50_700_hf1440_v10.yaml` (loads; works as `--brief` override [verified]) | the D6 anchor shows v10 predicts the measured horn worse than v7 |
| **R2** | C2 constancy | **Slope-limited**, slope clip **5°/decade**, weight 1, tolerance 1 (S1's reproduction), on the **116-point** dense grid. Shipped as a separate identity `..._v10_slope5.yaml`. **Rule:** it ranks nothing until its own frequency floor is published (`rescore_identity.py floor` with that brief) | S1 18/20 overlap; N3 116 points; Geddes "no perfect CD"; owner 11-17 "slope-limited, floor first" | `examples/briefs/home_landscape_2026-11-18_v10/room_landscape_80x50_700_hf1440_v10_slope5.yaml` [verified loads] | its floor exceeds the gaps between finalists (then it stays diagnostic) |
| **R3** | C3 dead bands; v10 rip tolerance/weight | **No new dead bands.** Keep v9/S1 values: rip tolerance 1 dB, weight 1; ripple and constancy stay less-is-better terms. Ripple region `preferred_edge` (owner 11-18) | SCORING_RANGE_PROPOSAL L123-131 (dead-banding everything flattens the surface); E4 "rip barely moves ranks" | same two briefs | anchor data shows ripple beyond ±preferred/2 predicts preference |
| **R3b** | Frequency grid of the new brief (packet §6) | v10 briefs copy the v7 home grid: `screen_extra_hz [250,315,400,2573,3311,4260]`, `verify_points_per_octave 6` (18 screen / 29 verify) — the grid the N3 floor was measured on | packet §6; N3 | both v10 briefs [verified] | — |
| **R3c** | v9 corridor PROVISIONAL status | Closed by v10. v9 corridor numbers are never used for a decision; v9 J is never rewritten | §10.1 | none | — |

### Fidelity, GPU budget and order (WP 2.x, 4.x, D6, D7, C6)

| # | Question | Decision | Evidence | Set in | Reverses if |
|---|---|---|---|---|---|
| **R4** | D6 step 1 anchor | **Accept R-OSSE ST260** and its predeclared pass rule (beamwidth ±5° per 1/3 oct, ±3° in 2-5 kHz, DI ±1 dB, 1-8 kHz, same DI method both sides). **2 solves** approved, gated on the local source check | `ANCHOR_ST260_RESEARCH_2026-11-18.md` | `docs/evidence/gpu_queue_resolved_2026-11-18/anchor_st260.yaml` [dry-run verified] | no admissible measured build exists → fallback ATH CORE/Tritonia search |
| **R5** | C6 / D7 B1 | **Approve batch 1** (5 fold-warm x2 probes). **Approve batch 2** (3 ext_throat_v7 x2 probes) **only if** probe 1 shows Shared Usage ≈ 0. **Drop B1f**: the frequency floor was measured twice (N3 + WP3, D5 "cite, never re-measure") | b1 readiness packet; D5 | `scratch/fable_architecture/.b1/b1_mesh_night_insert.yaml`, `docs/evidence/b1_readiness_2026-11-18/b1_mesh_ext_throat_probes.yaml` | probe 1 spills → B1 = "not measurable on this card" |
| **R6** | GPU order | 1) B1 batch 1 → 2) ST260 anchor (after source check) → 3) B1 batch 2 (if R5 allows) → 4) WP 4.2 equivalence (2) → 5) WP 4.3 B2 (12-16, only if 4.2 passes) → 6) BO arms `_r2` → 7) B6 after the v10 rescore + floors | C6 order (senior review); critical path §10.2 | `LOCAL_AGENT_PROMPT_2026-11-18.md` | — |
| **R8** | U3 host (WP 4.1 → 4.2) | **`hl__biradial_es_style_v7`, best stored design.** Reasons: owner-requested and protected; the 4.1 CPU stage already ran on this family (8/8 meshed); record agreement p99 0.101 mm; `ext_throat_hvlaw` carries owner *drop* evidence and is the parent the throat block showed inert | `FABLE_SENIOR_REVIEW` SD-2; `U3_RECORD_EDITS_CPU`; A11 / C5 table | jobs from `tools/analysis/u3_jobs.py` (local; needs `runs/`) | 4.2 equivalence fails on biradial → stop B2, do not switch host silently |
| **R9** | Throat block (G5) | **Park on A** ("inert in this envelope"); B recorded "H authority, not competitive under v7". No further throat GPU | plan §10.2 table; G5 | none | v10 rescore shows B within the v10 floor of A |
| **R10** | D6 step 2 print-and-measure | After B1 + anchor pass: print **two** horns ≈ 0.5 J apart under v7 that are **different constructions**: the best v7 home design whose mesh floor B1 covers, plus the best v10 home design if it is a different construction, else the next construction in both top-5s. Both must fit the **build box** (R12). If the anchor fails, step 2 waits | §10.1 D6 | prompt | anchor fails |

### Governance, provenance, envelope, queue (WP 0.9, 5.x, 7.1, D9, D10)

| # | Question | Decision | Evidence | Set in | Reverses if |
|---|---|---|---|---|---|
| **R7** | b06a938 (comments that moved the Klangfilm H/V digests) | **Revert the code part; keep the facts in the contract errata.** Digests restored (hv_core `ee160698…`, hv `c65beb16…`) and **pinned by a test**, so no stored recipe is locked out | b06a938 is comments only [code-verified]; no committed recipe or queued job names the new digests [verified] | kernel files restored; `tests/test_klangfilm_hv_digest_pin.py`; `docs/knowledge/contracts/klangfilm_lame_hv.md` Errata | WP 0.9 record digest lands (then the kernel digest becomes informational, R12b) |
| **R11** | C5 protected list; refusal storms | **List confirmed as shipped** (29 entries). ext_throat_hvlaw v7/v8 and osse_rrect_morph v7/v8 stay unprotected (owner drop evidence); sp__* and rf__rect_radial_wide_v7 stay unprotected (no evidence). **Refusal storms stop protected lanes**; J-based stops (no gain / bound-pinned / stalled) only advise | A11 / OWNER_DECISIONS C5 [primary]; a refusal storm means a broken config, not a slow one [inferred] | `examples/protected_lanes.yaml` `status: confirmed`; `run_campaign_night.PROTECTED_STOP_PREFIXES`; test | owner names a lane to add/remove |
| **R12** | Envelope convention | The brief's 600×480×480 gate applies to the **acoustic box** (mesh-built inner sheet = stored `bbox_m`, 70/70 records). The **build box** (acoustic + declared wall/shell) is recorded beside it (D9) and is the box a printed horn (R10) must fit | OWNER_DECISIONS no-solve proposal 2; senior review envelope row; 0/309 biradial designs within 3.5 mm of the limit [primary] | no gate change (today's behaviour) [inferred: gate reads mesh bbox]; build-box recording = local WP 0.9/D9 task | — |
| **R12b** | WP 0.9 provenance digest rule | **Geometry gates, code informs.** New recipes carry `implementation_sha256` (kernel, informational) **and** `record_digest` (65×61 record, float64, fixed byte order) which gates rebuilds; legacy recipes are classified rebuildable / bridge / unverified, never rewritten | packet: Klangfilm `e3a1f4a3…` 72 designs unrebuildable, ROSSE validator-only lockout [primary] | spec here; implementation = local task (D9 one work item) | — |
| **R13** | Crowe-X `g_L_mm` 285 vs 320 | **285 stays** for this lane (identity and BO cohort intact). Longer L only as a new `_v8` config with hi 320, after shape_check against the 480 mm depth box, with `search.warm_start` + reason (D4) | D4 no_headroom marking; contract | YAML comment (config_sha unchanged [verified]) | — |
| **R14** | Le Cléac'h "published" wording | Read as "built on the published JMLC march"; the H/V pairing is a LABELED HYBRID. Description text left as is so the lane's config_sha stays one identity; new versions use the corrected wording | contract `lecleach_iwata_hv.md` | YAML comment (config_sha unchanged [verified]) | — |
| **R15** | BO arms | Re-run `t_ath14_scalar100` and `t_corelaw_turbo100` with fresh `_r2` roots after B1 + anchor. **Not** re-queued: `t_hvlaw_*` (too few rows; needs a CMA cohort first, owner rule 2026-11-15), `t_klame_*` and `t_ath14_turbo100` until their log causes are read | night review [verified + code-verified] | `docs/evidence/gpu_queue_resolved_2026-11-18/bo_arms_r2.yaml` [dry-run verified] | logs show a code fault (fix first) |
| **R16** | Night truth: "ok" with nothing recorded | New status **`ok_no_result`** for search/BO jobs that exit 0 with no rows, no J, no run dir, no BO progress (new rows only) | t_trit80_rc2 (2 h, 0 evals) [verified] | `tools/run_campaign_night.py` `STATUS_OK_NO_RESULT`; test | — |
| **R17** | Replay version gate (off-plan item, folded into WP 0.4) | One list `replay.REPLAY_VERSIONS` drives the gate; a test pins one dispatch branch per entry and names v5/v6 as the only non-replayable versions | the v10 gate bug [verified] | `objective/replay.py`; `tests/test_replay_versions_single_source.py` | — |
| **R18** | Authority tables depend on hand-made CSVs | `u3_authority.py --csv-dir` writes `hv_beamwidth_<arm>.csv` from stored responses | part3 CSVs were hand-made | `tools/analysis/u3_authority.py`; test | — |
| **R19** | §2 space-card proposals (14) | **Approve** the zero-seed-shift fixes and sigma0 reductions for: atlas__ath_core, atlas__core_law, petal_hvlaw, tritonia_v7, ext_throat_hvlaw (sigma0 0.10), iwata_ar_smooth, osse_rrect_fold_warm (fix a0_deg), rf__section_axial_home, sab__lecleach_ctrl/fc540, p80x60 ath_core_14in/corelaw. Where no tested sigma0 is ≤ 15 % bad, use **0.05**. **Reject:** Crowe-X (no_headroom; needs warm_start), fold_warm_w1 links (data unknown, links withdrawn elsewhere), b3_soft trim (n-sensitive). Apply each as a new `__space_v1` config **only when that lane is next queued** (B6) | packet §1-§2, §8.6 | proposals stay in `space_cards/proposals/` until then | — |
| **R20** | WP 5.2 categorical split | **Approved in principle, executed at re-queue time.** None of the 5 flagged configs is in a queue, so no files now; any re-queue of them must first split `morph_target` into one config per category | packet §3 | warning already in `config.py` | — |
| **R20b** | `search.record_gate` | `shadow` on lanes whose route builds records (ext_throat first); `resample` only after a lane's shadow report shows 0 `record_inside_but_refused` | packet §4 | none now | — |
| **R21** | D10 integration and ownership | The **local orchestrator is the single integrator** of `hornfab-all-*` and `main`; cloud work arrives only as PRs into `hornfab-all-*`. Merge order: PR #69 → `hornfab-all`; PR #67 → `main`; one PR `hornfab-all` → `main`; close PR #68 (superseded, byte-identical code [verified]). Nights move to `main` at the next night boundary. Ownership: `hornlab_search/geometry/**`, `tools/analysis/**`, `tools/night_queue/fidelity_pairs.py`, `examples/protected_lanes.yaml` and `scratch/fable_architecture/**` = Fable senior lane. **The CLAUDE.md ownership row could not be written from the cloud (blocked by the session's permission guard); the local agent adds it** | D10; CLAUDE.md ownership table | prompt | — |
| **R22** | Uncommitted `scalar_v9.py` / `AGENTS.md` / `.opencode` edits on the owner box | `scalar_v9.py` is frozen: any edit that changes v9 math is discarded (the ripple fix lives in v10). Doc-only edits to AGENTS.md / .opencode may be committed after review | invariant 1; §10.1 | prompt | — |
| **R23** | Agent benchmark A/B (off-plan) | Deferred until after D6 step 1; not on the critical path | ISSUES 11-18 | none | — |
| **R24** | Klangfilm b3_soft `g_theta_h1_deg` trim | Rejected (n-sensitive, 47 % vs > 50 %) | packet §1, §8.6 | none | a 128-point box shows > 50 % |
| **R25** | Throat-block landing target | Lands with `hornfab-all` → main (it is already on the branch; opt-in keys, neutral when absent [code-verified contract invariants]) | contract `throat_hv_block.md` §3 | none | — |

---

## 2. What is still not decidable by anyone without new data (not open questions; scheduled measurements)

| Item | Why it waits | Scheduled by |
|---|---|---|
| Which score (v7 vs v10) the nights use | Only the physical anchor (D6) can tell which predicts a real horn | R4 → R10 |
| Mesh part of the floor | B1 has not run | R5 |
| v10 and v10_slope5 frequency floors | need `runs/` | prompt step "rescore" |
| Whether a U3 freedom has authority | 4.2 then 4.3 must run | R6, R8 |

## Sources (web, this pass)

- CTA-2034 explanation (listening window ±30° H / ±10° V, PIR weights): https://www.erinsaudiocorner.com/loudspeakers/wharfedale_heritage_center/ ; https://www.erinsaudiocorner.com/loudspeakers/audio_craftsmen_victoria/ ; https://github.com/Arnwald/cta2034-room-study
- Olive preference model (patent): https://patents.google.com/patent/US20050195982A1/en
- Geddes on waveguides (author, forum): https://www.diyaudio.com/community/threads/geddes-on-waveguides.103872/
- BEM vs measured horn directivity: https://www.researchgate.net/publication/235788684 ; https://audioxpress.com/article/development-design-experimental-and-theoretical-investigation-of-an-unusually-shaped-horn ; https://aes.org/e-lib/browse.cfm?elib=12743
