# BoTorch on the four best-populated typologies — 25 screens each (STAGED, NOT LAUNCHED)

Prepared 2026-11-15. Night file `docs/queue/bo_multityp_2026-11-16.yaml`;
admission packet `docs/queue/bo_multityp_2026-11-16.admission.json`.
Code prerequisites in this same change set: `comparison-25`/`comparison-30` budget profiles,
`prepare_study.py --config/--brief/--budget-profile`, four new registered study tasks,
`tools/bo_compare/preflight_arms.py`, and an optional `--admission` gate on the night runner.

**Status: staged and held.** Nothing here authorises a solve. The owner's 2026-11-15 17:15 pause
(brief / DI-slope scoring, lip-and-waist law) still binds, and objective v7 itself is the thing under
review — see §7 before releasing.

---

## 1. The rule this campaign obeys

Owner rule (2026-11-15, `CONTINUITY.md`): **BoTorch only on a typology that already has enough solved
designs.** Enforced in code as `prepare_study.py --min-rows 100` against
`build_native_training_set(..., require_single_fidelity=True)` — not against raw record counts, which
are an upper bound (records do not carry weights/tolerances/metric_source).

A `scalar_pool_v1` GP over `d` knobs needs `2(d+1)` points to fit at all; 100 is the *spend* floor,
not the mathematical one. Below 100 the campaign is refused before a study exists.

## 2. Selection evidence (measured 2026-11-15, read-only)

Each row: a cohort built with `tools/analysis/study_cohort.py --limit 256`, then the strict builder.
`n` = accepted usable rows after every gate (config identity, objective version, brief/metric policy,
fidelity, design-hash round-trip).

| candidate config | family / idea | objective | n | d | verdict |
|---|---|---|---:|---:|---|
| `atlas_2026-10-30/atlas__osse_ext_throat` | OSSE extended throat | v7 | 256 | 6 | **excluded at execution** — biggest cohort, but its rows were solved with `hornlab_beat_bem 0850ef39…` and the worker runs `38e5b1f8…`; production refuses a pin mismatch (§2b) |
| `bo_vs_cma_2026-11-15/p80x60__ext_throat_hvlaw_cov_v7` | strict 80x60, ext throat + H/V cosine law | v7 | **231** | 9 | **arm 1** |
| `print_80x60_2026-11-13/p80x60__ath_core_14in_700_v7` | ATH-core 14 in | v7 | **219** | 14 | **arm 2** |
| `suggest_ab_2026-11-14/p80x60__ext_throat_corelaw_v7` | ext throat + ATH core-law wall angle | v7 | **206** | 9 | **arm 3** |
| `print_80x60_2026-11-13/p80x60__osse_ext_throat_700_v7_seed5678` | OSSE ext throat (home task) | v7 | 185 | 6 | excluded — **already has a 66-call BoTorch comparison** (night B/D); 25 more screens there add nothing new |
| `home_landscape_2026-11-15/hl__ext_throat_hvlaw_v7` | landscape 80x50 ext throat | v7 | **136** | 8 | **arm 4** (best remaining executable cohort; different brief, landscape target) |
| `home_landscape_2026-11-15/hl__osse_rrect_morph_v7` | OSSE rounded-rect | v7 | 75 | 14 | **below the 100 floor** |
| `home_landscape_2026-11-15/hl__ath_core_petal_hvlaw_v7` | ATH petals | v7 | 46 | 11 | below the floor |
| `home_landscape_2026-11-15/hl__lecleach_iwata_ar_landscape_v7` | Le Cléac'h Iwata AR | v7 | 1 | 4 | below the floor (one usable row; needs a CMA cohort) |
| `home_landscape_2026-11-15/hl__es_style_rollback_v7` | ES-style rollback | v7 | 1 | 5 | below the floor |
| `home_landscape_2026-11-15/hl__crowe_panel_home_v7` | Crowe panel (bridge) | v7 | — | — | **not trainable by the strict builder**: `unknown rows type 'crowe_panel'` — the bridge is not installed in the study worker |
| `rolled_rect_2026-11-15/rr__crowe_panel_es600_v7` | Crowe ES-600 (bridge) | v7 | — | — | same bridge refusal |

### 2b. The dependency-pin gate (why the biggest cohort is not the best arm)

Row count alone is not enough. `studies/production.py:170-181` refuses to execute a study whose
training cohort was measured with a different `hornlab_mesher` / `hornlab_beat_bem` /
`hornlab_plots` build than the executing interpreter — the GP would be learning scores produced by a
different solver. Verified per cohort on 2026-11-15:

| cohort | rows | `hornlab_beat_bem` (cohort) | execution | executable |
|---|---:|---|---|---|
| atlas `atlas__osse_ext_throat` | 256 | `0850ef39…` | `38e5b1f8…` | **no** |
| hvlaw_cov | 231 | `38e5b1f8…` | `38e5b1f8…` | yes |
| ath_core_14in | 219 | `38e5b1f8…` | `38e5b1f8…` | yes |
| corelaw | 206 | `38e5b1f8…` | `38e5b1f8…` | yes |
| seed5678 | 185 | `38e5b1f8…` | `38e5b1f8…` | yes (already studied) |
| hvlaw (landscape) | 136 | `38e5b1f8…` | `38e5b1f8…` | yes |

This is also why `tools/bo_compare/preflight_arms.py` checks pins and not just row counts. The atlas
arm can be made eligible later only by re-solving a cohort under the current BEM (or by moving the
execution interpreter back to that pin, which would invalidate every other arm).

Consequence worth stating up front: **three of the four arms are OSSE-extended-throat variants with
different wall-angle laws, and one is ATH-core.** That is where the data actually is. The genuinely
different shapes (Le Cléac'h, Crowe, rounded-rect) are one cohort away from eligibility, not one
policy away.

## 3. Budget

**Owner decision 2026-11-15 (evening, final for now): skip verification entirely.** The three
staged arms use `comparison-25x0`: **25 screens + 0 verify = 25 calls, 150 attempts.**

What that buys and costs:
- ~10-13 minutes saved per arm (six verify calls) and 6 fewer GPU solves per arm;
- the frozen rule still *selects* up to 4 finalists + 2 audits, but with zero verify capacity the
  evaluator reports `shortfall: 4` / `audit_shortfall: 2` and proposes no verification candidate
  (it never emits a candidate the journal would refuse); the arm ends `pool_exhausted` after the
  screens, which is the normal completion status;
- consequence, stated plainly: **a screen-only arm has no verified finalist**, so its result is a
  screen J and the rule "the improvement survives the audit pair" cannot be evaluated. Screen vs
  verify gaps of ~1-2 J have been measured on other designs; treat these arms as directional.
  Use `comparison-25` (25 + 6 = 31) or `comparison-25x2` (25 + 2 = 27) when the decision depends
  on a verified number.

The running `cov` pilot was prepared *before* this decision, so it finishes on its original
`comparison-25` package (6 verify). Re-preparing it would start a new package with zero observations
(observations are keyed by `package_id`), i.e. throw away ~12 solved designs to save ~10 minutes.

Other profiles: `baseline` 18+6 (frozen default), `comparison-30` 30+6, `comparison-60` 60+6.

## 4. Arms

One arm per typology, scalar policy (the default; `--policy turbo` / `pareto` are a flag swap on the
same job once the scalar round is read):

| arm | task | seed | study root |
|---|---|---:|---|
| cov | `p80x60__ext_throat_hvlaw_cov_v7` | 71001 | `runs/bo_multityp_2026-11-16/bo_cov_s71001` |
| ath14 | `p80x60__ath_core_14in_home700_v7` | 71002 | `runs/bo_multityp_2026-11-16/bo_ath14_s71002` |
| corelaw | `p80x60__ext_throat_corelaw_v7` | 71003 | `runs/bo_multityp_2026-11-16/bo_corelaw_s71003` |
| hvlaw | `hl__ext_throat_hvlaw_v7` | 71004 | `runs/bo_multityp_2026-11-16/bo_hvlaw_s71004` |

Cohorts (prebuilt, verified, **not rebuilt by the night**):

```
runs/bo_multityp_2026-11-16/ext_throat_hvlaw_cov/cohort      231 rows   pins ok
runs/bo_multityp_2026-11-16/ath_core_14in/cohort             219 rows   pins ok
runs/bo_multityp_2026-11-16/ext_throat_corelaw/cohort        206 rows   pins ok
runs/home_landscape_b_2026-11-15/cohort                      136 rows   pins ok  (hl__ext_throat_hvlaw_v7)
```

The atlas cohort (`runs/bo_multityp_2026-11-16/atlas_osse_ext_throat/cohort`, 256 rows) stays on disk
as evidence and is deliberately **not** in the night: its BEM pin does not match the worker (§2b).

Each arm is two jobs: `prep_*` (create study → snapshot → training → analysis → proposal → package;
CPU only, no solves) then `bo_*` (`studies.cli run --execute`, adaptive serial solves on the GPU lane).
A failed prep leaves no `package.json`, so its run job fails fast and the next arm is unaffected.

## 5. Readout (fixed before the run)

Because there is no matched CMA control in this campaign, the question is *"does BoTorch find a
distinct, better design than the CMA data it trained on?"*, not *"is BO better than CMA?"*:

1. **Baseline** per arm: the best **screen** J in that arm's cohort (the data the GP saw) and the
   best cohort design's distance to the bound box.
2. **Arm result**: best **verify** J of the 4 finalists, plus the 2 audits.
3. **Win condition**: best verify J < cohort best screen J, and the improvement survives the audit
   pair (no audit design scoring worse than the cohort's 90th percentile).
4. **Same basin or new**: normalised distance of the arm's best design from the cohort's best.
5. **Efficiency**: screens needed to first reach the cohort best (a never-reaching arm counts >25).
6. `tools/analysis/hifi_rescore.py --verify` on every winner, and the beamwidth pair actually measured
   — J is not comparable across briefs, so report the physical numbers next to it.

Report per arm; do not pool across arms (different briefs and different objective targets).

## 6. Preflight and release

```powershell
# 1. read-only proof: registry + cohort files + strict row counts + dependency pins + budget profile
.venv\Scripts\python.exe tools\bo_compare\preflight_arms.py --budget-profile comparison-25 --min-rows 100 `
  --arm ext_throat_hvlaw_cov=p80x60__ext_throat_hvlaw_cov_v7:runs/bo_multityp_2026-11-16/ext_throat_hvlaw_cov/cohort `
  --arm ath_core_14in=p80x60__ath_core_14in_home700_v7:runs/bo_multityp_2026-11-16/ath_core_14in/cohort `
  --arm ext_throat_corelaw=p80x60__ext_throat_corelaw_v7:runs/bo_multityp_2026-11-16/ext_throat_corelaw/cohort `
  --arm ext_throat_hvlaw=hl__ext_throat_hvlaw_v7:runs/home_landscape_b_2026-11-15/cohort

# 2. plan + admission validation (no processes, no solves)
.venv\Scripts\python.exe tools\run_campaign_night.py --night docs\queue\bo_multityp_2026-11-16.yaml `
  --admission docs\queue\bo_multityp_2026-11-16.admission.json --dry-run
```

Launch (only after §7 is settled and the GPU lane is free):

```powershell
# copy the night file into runs\nights\ and launch detached, exactly as for the 14/15 Nov nights
.venv\Scripts\python.exe tools\run_campaign_night.py --night docs\queue\bo_multityp_2026-11-16.yaml `
  --admission docs\queue\bo_multityp_2026-11-16.admission.json
```

The `--admission` packet is the release record for this exact job set. It lists every job id; a night
file edited afterwards (extra job, renamed id) is refused as a whole. Omitting `--admission` is
allowed by the runner for historical nights but must not be used for this one.

### 6b. Verified 2026-11-15 (no solves were run)

- `preflight_arms.py` for the four staged arms → `"ready": true` on all four (rows 231/219/206/136,
  pins matched, `comparison-25` known), exit 0.
- The same tool refuses the atlas arm with
  `dependency_pin_mismatch: hornlab_beat_bem: cohort='0850ef39…' execution='38e5b1f8…'`, exit 1 —
  the gate works, and that is why atlas is not in the night.
- A full **prep-only** run of every arm into throwaway roots
  `runs/bo_multityp_2026-11-16/_smoke_bo_{cov,ath14,corelaw,hvlaw}` produced
  `{"status": "ok"}` from `execution_capability` for all four (snapshot, training, analysis and
  proposal all `ok`; package budget `{25, 6, 31, 150}`). These roots are evidence only — the staged
  roots `bo_{cov,ath14,corelaw,hvlaw}_s7100X` are still empty, so the night's prep jobs will run
  normally.
- `run_campaign_night.py --admission … --dry-run` → `admission accepted … 9 job(s) allowed`, 9 jobs
  printed, exit 0. A packet with a wrong `night` is refused with exit 2.
- The smoke prep runs above used `comparison-25` (25+6). The staged night itself now uses
  `comparison-25x0` (25+0) per the owner decision in §3; dry-run and preflight were re-verified
  with that profile (`ready: true`, budget `{25, 0, 25, 150}`), and the evaluator emits no
  verification candidate when the profile budgets none
  (`tests/test_study_evaluator.py::test_zero_verify_budget_skips_verification_entirely`).

### 6c. Launch log

- **2026-11-15 20:08 — owner authorised one arm.** Launched detached (controller pid 26816, parent
  WmiPrvSE) via `launch_detached.ps1` → `queue.ps1` → runner: night `bo_cov_pilot_2026-11-16`,
  admission `docs/queue/bo_cov_pilot_2026-11-16.admission.json` (3 job ids), arm `cov`
  (`p80x60__ext_throat_hvlaw_cov_v7`, 231 rows, d=9, seed 71001, `comparison-25`).
  Preflight passed; prep reported `training rows: 231 (min 100)`.
  Logs: `runs/nights/queue_bo_cov_pilot_2026-11-16.log` and
  `runs/nights/bo_cov_pilot_2026-11-16_runner_{stdout,stderr}.log`.
- `queue.ps1` now takes `-Admission` and `-DryRun`; before that change a queue-launched night would
  have bypassed the gate (it forwarded only `--night`).
- The remaining three arms (`ath14`, `corelaw`, `hvlaw`) are still staged and unadmitted.

## 7. Open blockers that belong to the owner, not the queue

- **Objective v7 is under review** (17:15 pause). These arms optimise v7 J. If the brief or the
  DI-slope/diag convention changes, the cohorts keep their historical identity but their J values are
  not comparable with the new objective — the arms must be re-staged against the new brief, not reused.
- **Crowe / rolled-family arms are blocked by the bridge**, not by data: the study worker does not
  install `crowe_panel_cli` / `section_pucker_cli` / `rolled_rect_cli`, and rolled-family proposals
  additionally require verified surface identities. Fixing that is separate work.
- **Cost, not data, is now the constraint** for Le Cléac'h / rounded-rect: each is ~25 CMA screens
  away from the 100-row floor. That is a cheap way to unlock two genuinely different typologies.

## 8. What this campaign does *not* claim

No acoustic quality claim, no claim that BO beats CMA (no matched control here), and no ranking of J
across arms. Screen J is a screen; verify J on four finalists plus two audits is the reported number,
and the physical terms (`hifi_rescore.py`) are what the listening decision uses.
