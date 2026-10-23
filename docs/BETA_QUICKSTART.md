# Beta quickstart: from a target to a printable horn

For beta testers on a Windows machine with an NVIDIA GPU (measured on an 8 GB RTX 4060). Every
command runs from the repository root with the project interpreter. Allow about one hour for
the first full loop.

## 0. Check the machine (1 minute, no GPU work)

```powershell
.\.venv\Scripts\hornlab-search.exe doctor
```

Expect `doctor OK: 11 checks, 0 failed` (the last one is free disk space). If `gpu-hygiene` reports BEAT hosts
alive, clear them with `.\.venv\Scripts\hornlab-search.exe gpu-clean` (it kills only this project's Julia / BEAT
worker hosts and refuses while another GPU job is running).

## 0a. Or use the browser GUI

```powershell
.\.venv\Scripts\hornlab-search.exe gui
```

Opens http://127.0.0.1:8765 (local only). Every view reads the same run folders as the CLI; Launch runs the same CLI
commands (shown before they start) and is refused with `GPU busy: ...` while another GPU job holds the lock. Ctrl-C in
the terminal stops the GUI, not running jobs. The 3D view loads three.js from a CDN (needs internet; otherwise it
falls back to the 2D wall profile). macOS: should work (stdlib + browser), untested.

## 0b. Compare typologies in one command (recommended start)

A **brief** (`examples/briefs/*.yaml`) fixes the driver exit, the size envelope, the target and the weights, so every
typology is scored on the same objective. Pick any combination of typologies by name or group:

```powershell
.\.venv\Scripts\hornlab-search.exe families --brief examples\briefs\hifi_90x60_1in.yaml
.\.venv\Scripts\hornlab-search.exe campaign --brief examples\briefs\axi_90x90_1in.yaml --families conical,exponential,tractrix --tier dry-run
.\.venv\Scripts\hornlab-search.exe campaign --brief examples\briefs\axi_90x90_1in.yaml --families classical --tier screen
.\.venv\Scripts\hornlab-search.exe campaign --brief examples\briefs\hifi_90x60_1in.yaml --families hybrid,rosse_baseline --tier compare
```

`--families` takes names (see `families`), groups (`classical`, `magnus`, `hybrid`, `legacy`) or `all`. Tiers:
`dry-run` meshes every seed and solves nothing; `screen` = one CMA-ES run per family, budget max(40, 10 × knobs);
`compare` = two CMA-ES seeds, budget max(150, 25 × knobs), median and spread reported (only `compare` supports
"family A beats family B"). Families that cannot meet the brief (an axisymmetric family on a 90×60 brief) are
skipped with the reason. Results: `runs\campaign_<time>\leaderboard.md`; each family's run has its own report.

Typologies available: conical, exponential, hyperbolic-exponential (hypex), tractrix, OSSE meridian (classical);
OSSE-H × hypex-V, OSSE-H × tractrix-V, convex blends, perturbed OSSE / tractrix (hybrids); OSSE, R-OSSE, ICW,
FREEFORM (Magnus's families). Le Cléac'h is disabled until a verifiable published construction is available.
Adding a typology run is a new YAML in `examples/typologies/` plus a catalog line.

## 1. Describe the horn you want

Copy an example and edit the `name:` line (run folders, reports and STEP files are named after it) and the
`target:` block (and `bounds:` if you know what you are doing):

```powershell
Copy-Item examples\freeform_sculpt.yaml examples\my_horn.yaml
```

| Field | Meaning | Example |
|---|---|---|
| `coverage_h_deg`, `coverage_v_deg` | Total included angle at −6 dB | 90, 90 |
| `band_lo_hz`, `band_hi_hz` | Band that is scored. On 8 GB keep `band_hi_hz` ≤ 5500 | 700, 5500 |
| `di_target_db` | Directivity index target; `null` derives it from the coverage | null |
| `di_slope_target` | DI slope in dB/decade; 0 = constant directivity | 0.0 |
| `weights` | Relative importance of coverage, ripple, DI, DI slope, flatness | see file |

Which example to start from:

| Example | Family | Use it for |
|---|---|---|
| `freeform_sculpt.yaml` | FREEFORM, 11 knobs | Freely shaped waveguide; best behaved search so far |
| `osse_baseline.yaml` | OSSE | Classic OS waveguide, rectangular coverage |
| `icw_termination.yaml` | ICW | Wide coverage with a rolled mouth |
| `throat_adapter.yaml` | OSSE | Small high-frequency adapter, 2–6.5 kHz |

## 2. Check it meshes (seconds, no GPU)

```powershell
.\.venv\Scripts\hornlab-search.exe run --config examples\my_horn.yaml --dry-run
```

Expect `dry-run OK` with the dof count under the cap. Its time estimate ("2 s per candidate") is a lower bound
from small meshes; a real search of `freeform_sculpt` measures about 6 s per candidate.

## 3. Search (GPU; about 4–7 s per candidate)

```powershell
.\.venv\Scripts\hornlab-search.exe search --config examples\my_horn.yaml --budget 60
```

60 candidates take about 7 minutes (measured 7.3 min on 2026-10-23); 400 about 30–45 minutes. The last line
names the run directory under `runs\`. Designs already solved by any earlier run (same shape, mesh and solve settings)
are reused for free, so the summary can say e.g. `777 evaluations (60 new, 717 cached)`: only the new ones cost GPU
time. An interrupted search (Ctrl-C) continues with `search --resume runs\<dir>`. A search leaves its Julia host warm
on purpose (the next run starts faster); when you are done, run `.\.venv\Scripts\hornlab-search.exe gpu-clean`.

## 4. Look at the result

```powershell
.\.venv\Scripts\hornlab-search.exe report runs\<dir>
```

Open `runs\<dir>\report.html` in a browser. Read in this order: convergence (did it keep
improving?), the bounds table (a parameter at a bound means the bound stopped the search, not
physics), beamwidth and DI against the targets, then the polar maps.

## 5. Get a solid for CAD or 3D printing

```powershell
.\.venv\Scripts\hornlab-search.exe export-step --run runs\<dir> --top 3
```

Writes closed STEP solids in millimetres (full horn, throat open) to `runs\<dir>\step\`. Add a
driver flange and mounting in CAD; the solver did not model them.

## What to send back

The run directory name, `report.html`, your config, and a note on anything that surprised you.
Known limits: no woofer entry ports, no room or baffle, searches stop at 5.5 kHz on 8 GB cards (finalists can be
re-solved to 12 kHz with `verify --run runs\<dir> --brief examples\briefs\<brief>_12k.yaml --top 3`; above
~7.9 kHz that compares geometries, not real drivers; the `_12k` briefs are refused by search/run/campaign), and the
surrogate (fast-prediction) model is not active yet.
