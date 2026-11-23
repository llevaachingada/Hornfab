# Best horns solved 2026-11-22

The best screen design of each horn family solved on 2026-11-22, re-rendered on 2026-11-23 after the
overnight data top-up, at 200 dpi (6000 px wide) on three contact sheets. Each row: isometric, top-skew, V cut (x=0), H cut (y=0), V dispersion,
H dispersion and the score ledger.

Open `index.html` for the gallery (served by GitHub Pages).

**J is the screen objective of each brief — never compare it across briefs.** Sizes are the outer
shell in mm (quarter-mesh bounding box doubled in width/height). None of these designs is
verify-grid confirmed.

## Sheets

### `best22_01.png` — home v10
| design | run | hash | J | outer W×H×D mm |
|---|---|---|---|---|
| home Fold | `20261122T205923Z-screen-391141` | `6d9e8c874827` | 1.19315 | 512×426×362 |
| home Morph | `20261119T181029Z-screen-c3b6c6` | `adf7e74388f0` | 1.39730 | 549×413×406 |
| home TwinRay | `20261119T175926Z-screen-8454e6` | `026edbad538c` | 1.73558 | 589×430×449 |

### `best22_02.png` — compact400 / compact500
| design | run | hash | J | outer W×H×D mm |
|---|---|---|---|---|
| compact400 Fold | `20261122T221847Z-screen-5857d8` | `f4774d562aae` | 0.96787 | 474×350×303 |
| compact500 Crowe | `20261122T223153Z-screen-98b41d` | `138f09ce5472` | 1.70512 | 770×548×393 |
| compact500 2-inch | `20261122T092931Z-screen-6edb3a` | `b7ae23ef8caa` | 1.93303 | 484×447×257 |

### `best22_03.png` — v11 home
| design | run | hash | J | outer W×H×D mm |
|---|---|---|---|---|
| FAV v11 | `20261122T232104Z-screen-2cc59b` | `5987a94e99c0` | 3.30792 | 720×608×418 |
| v11 Fold | `20261123T001107Z-screen-c88c3d` | `606abb301970` | 3.42866 | 522×445×423 |

## Overnight update (2026-11-23)

The `bo_data_topup_2026-11-22` night resumed these run dirs in place to grow each cohort to BO
training size. Three bests improved and are the designs on the sheets now: compact500 Crowe
1.815 -> **1.705**, FAV 3.385 -> **3.308**, v11 Fold 3.617 -> **3.429**. The other five are unchanged.
All J remain screen-grid.

## Read this correctly

- The compact400 (474 mm), compact500 Crowe (719 mm) and FAV (730 mm) winners exceed their old build
  envelopes because the brief envelope was deliberately switched off on 2026-11-22
  (`envelope.enforce: false`, 1200 mm per-dimension sanity ceiling). Filter by size separately if a
  build constraint returns.
- The open-envelope briefs are new score identities; their J is not comparable to closed-envelope
  runs or the published floors.
- The home Fold gain came through `k` = 3.36, past the old 2.81 cap, while staying inside the old
  600×480 envelope. The compact500 Crowe's loading term collapsed 0.46 → 0.03; diagonal/off-axis
  response is now its limiting term.

## Regenerate

```powershell
# views + sections (viz env; pyvista is not in the project venv)
scratch\vizenv\Scripts\python.exe docs\renders\2026-11-22-best-horns\render_best.py docs\renders\2026-11-22-best-horns\targets.txt
# sheets (project venv)
.venv\Scripts\python.exe docs\renders\2026-11-22-best-horns\compose_best.py docs\renders\2026-11-22-best-horns\targets.txt best22 1 "best screen design of each family, solved 2026-11-22"
```

`targets.txt` holds one `run_dir hash` line per design. The run directories are local (gitignored);
the scripts and target list sit beside this page.
