# GPU run summary layer — committed 2026-10-22

Purpose: durable copies in git of the **abbreviated/summary layer** of every local CUDA GPU
run (`backend: beat_cuda`), per explicit user request 2026-10-22. The heavy per-design raw
blobs (`runs/<run_id>/designs/**` .npz/.msh payloads) remain gitignored **by design** and are
NOT in this folder — they stay covered by `dataset verify` / `manifest.sha256` at the parent
evidence level.

Each `<run_id>/` here contains only what the run wrote outside `designs/`:
`run.json`, `config.yaml`, `best.json`, `search.ndjson` (and `cma/*.dat`, optional
`verify/search.ndjson`, one `report_cp8b.html`).

Bit-level coverage: `runs/manifest.sha256` (SHA-256 + bytes for every file in this folder,
including these meta copies).

| Run ID | Command | Budget | Best J | Checkpoint |
|---|---|---|---|---|
| `20261013T053716Z-screen-d627d9` | `run --config examples/osse_baseline.yaml --mode screen` | — | 22.592 | CP-8a seed (1 eval) |
| `20261013T053757Z-screen-7e6e5b` | `search --config examples/search_smoke.yaml --resume` | resume 0 | 7.363 | smoke / resume check |
| `20261013T121958Z-screen-9e5a5c` | `search --config examples/search_smoke.yaml` | 60 | 10.778 | CP-8b smoke (report_html included) |
| `20261013T123136Z-screen-ca15be` | `search --config examples/osse_baseline.yaml` | 1500 | 6.106 | CP-8c run 1/4 (osse_baseline) |
| `20261013T204408Z-screen-6bdcbd` | `search --config examples/icw_termination.yaml` | 800 | 12.201 | CP-8c run 2/4 (icw_termination) |
| `20261013T234724Z-screen-ff569c` | `search --config examples/freeform_hv.yaml` | 800 | 30.543 | CP-8c run 3/4 (freeform_hv) |
| `20261014T025335Z-screen-852be3` | `search --config examples/throat_adapter.yaml` | 400 | 5.983 | CP-8c run 4/4 (throat_adapter) |
| `20261022T141552Z-screen-616fcb` | `run --config examples/freeform_sculpt_symcheck_quarter.yaml` | — | 41.781 | HANDOFF 6b step 4 (quarter, 451 dofs) |
| `20261022T141639Z-screen-8cc55e` | `run --config examples/freeform_sculpt_symcheck_full.yaml` | — | 41.754 | HANDOFF 6b step 4 (full, 1636 dofs) |
| `20261022T141729Z-screen-babb6b` | `search --config examples/freeform_sculpt.yaml` | 60 | 24.213 | HANDOFF 6b step 5 (sculpt, seed 30.945) |

Note: this commits the summary/log layer of the runs to the code branch as an admitted,
user-approved exception to the "evidence about the data, never the data itself" rule in
`docs/evidence/README.md` — the `search.ndjson` files are logs, and the per-design raw
payloads stay excluded. If future runs produce much larger summary layers, move them to a
data branch / release assets instead (per the parent README escape hatch).