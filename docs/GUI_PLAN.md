# Local web GUI for hornlab-search (plan, 2026-10-23)

## Goal

One command, `hornlab-search gui`, opens a browser page at `http://127.0.0.1:8765` that lets the owner and the
collaborator see the GPU state, browse every run and campaign, edit briefs, launch the same searches the CLI runs,
and export STEP, on Windows and macOS, without learning the CLI. The GUI adds **no physics**: every number it shows
is read from run folders the CLI wrote, and every job it starts is the ordinary CLI command, shown verbatim before it
runs.

## Constraints (binding)

- **Never solves in-process.** Launches go through `hornlab-search <cmd>` as a subprocess, so the GPU lock,
  hygiene, failure cache, dataset records and run folders are exactly those of the CLI. A busy lock is shown, not
  bypassed.
- **Read-only on data.** Reads `runs/`, `docs/evidence/`, `examples/`. Writes only: new brief files under
  `examples/briefs/user/`, GUI job logs under `runs/gui_jobs/`, STEP files via `export-step`. Never edits shipped
  YAML, `dataset/`, `docs/plan/**`, gate thresholds or the `Family` contract.
- **Local only.** Binds 127.0.0.1. Launch requests are an allow-list of CLI subcommands with validated arguments
  (paths must resolve inside the repo); no free-form shell.
- **Easy to edit.** No JS build step, no npm. Python stdlib server (`http.server.ThreadingHTTPServer`) + JSON API +
  static vanilla HTML/CSS/JS. Charts are hand-drawn SVG/canvas reusing the review page's `chart()`/`heat()` code.
  three.js (pinned version from a CDN) only for the optional 3D view, with a 2D fallback when offline.
- **Cross-platform.** Pure Python + browser. On a Mac without CUDA everything except GPU launches works; the launch
  panel shows `doctor`'s backend state and offers `--backend beat_cpu` / `bempp_cpu` where the CLI supports it.
- Zero new runtime dependencies.

## Views

1. **Status**: `doctor` summary (cached, re-run on demand), GPU lock holder (user, command, since), VRAM, disk,
   project julia / worker-host count, overnight queue log tail and watchdog log tail, `gpu-clean` button (refused
   while a live job holds the lock, as in the CLI).
2. **Campaigns**: list `runs/campaign_*` newest first; leaderboard table (best/median J, spread, failures, pinned
   bounds, note); per-family best-design wall profiles; beamwidth overlays.
3. **Run explorer**: every `runs/<id>`: convergence (each eval + running best), objective terms seed vs best,
   beamwidth H/V vs target, DI vs DI*, on-axis, polar maps (H/V), wall profile, parameter sensitivity and pinned
   bounds, failure breakdown, generator knobs and provenance; buttons: open `report.html` (generate if missing),
   `export-step --top N`.
4. **Compare**: pick two runs; `compare_metrics` table plus overlaid curves (refuses different grids, as the CLI).
5. **Briefs and families**: brief viewer and form editor (target, weights, envelope, band; band_hi capped at 5500
   with the reason shown); "Save as" to `examples/briefs/user/<name>.yaml`, validated with `config.load_brief`;
   families table with compatibility per brief (`families --brief`).
6. **Launch**: campaign / search / run form -> exact CLI command shown -> Start. Live log tail, elapsed time, Cancel
   (terminates the process tree, then `gpu-clean`). A dry-run button for every config.
7. **3D view** (phase 2): the best design's mesh (`designs/<hash>/mesh.msh`, already written by the search) as a
   triangle surface in three.js, mirrored from the quarter model.

## Architecture

```
hornlab_search/gui/
  server.py   ThreadingHTTPServer, routing, static files, 127.0.0.1 only, `hornlab-search gui [--port] [--no-browser]`
  data.py     pure readers: runs, campaigns, run detail (curves, polars from response.npz), briefs, families, logs
  jobs.py     allow-listed CLI launcher, job registry, log files, cancel (process tree), lock-state passthrough
  static/     index.html, app.css, app.js (views), charts.js (from the review page), view3d.js (phase 2)
tests/test_gui_data.py, test_gui_jobs.py, test_gui_server.py   offline, fixture run folders, no GPU
```

API (JSON): `GET /api/status`, `/api/campaigns`, `/api/campaign/<id>`, `/api/runs`, `/api/run/<id>`,
`/api/compare?a=&b=`, `/api/briefs`, `/api/brief/<name>`, `/api/families?brief=`, `/api/jobs`, `/api/job/<id>`;
`POST /api/brief` (save as user brief), `/api/jobs` (launch), `/api/job/<id>/cancel`, `/api/gpu-clean`.

## Lanes (built while the GPU queue runs; nothing here touches the search path)

- **A, orchestrator:** `server.py`, `data.py`, `jobs.py`, CLI `gui` subcommand, tests.
- **B, one Sonnet subagent:** `static/**` against a frozen JSON fixture of the API, reusing the review page's chart
  code; no Python edits.
- Integration and a browser check (desktop and 400 px), then commit. Package data for `static/` in `pyproject.toml`.

## Acceptance

- `hornlab-search gui` starts on Windows; every view renders real runs from `runs/`; the full offline suite is green.
- A launch while the GPU lock is held shows `GPU busy: ...` and starts nothing.
- A launched `campaign --tier dry-run` runs, streams its log and finishes; Cancel kills the tree and runs gpu-clean.
- No file outside the write list changes (checked by a test with a temp repo root).
- macOS: not testable on this machine; the server is pure stdlib and paths use `pathlib`. Mark it "should work,
  untested" until the collaborator tries it.

## Prior art (survey 2026-10-23, read-only)

- Magnus's `m3gnus/waveguide-generator` (AGPL-3.0-or-later): FastAPI server + React/TypeScript/Vite frontend,
  three.js (react-three-fiber) live 3D horn, ECharts for on-axis / polar map / DI / impedance / power, durable job
  store streamed over WebSocket, ATH `.cfg` import, Fusion 360 link. Ideas taken: single-origin local server,
  job store with live log, polar map + DI + impedance panels, 3D view. Not taken: the Vite/TS build step.
- `JWSound/boundary-lab` (GPL-3.0): PySide6 + pyvistaqt desktop, matplotlib panels (isobars, spinorama, impedance),
  3D balloon. Ideas only (Qt desktop, no browser sharing).
- ATH (closed source): `.cfg` conventions only.

## Not in scope

Running solves in the server process; editing shipped configs or bounds; any physics; authentication or remote
access; Boundary Lab plugin (its geometry providers are PySide6 / GUI-thread bound; see
`docs/research/boundary_lab_0.5/bl_inventory.md`).
