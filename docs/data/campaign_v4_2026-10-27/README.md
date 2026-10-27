# Campaign tables (objective v4)

Exported by `tools/export_campaign_tables.py` from the screen-tier runs. No meshes, no raw responses.

* `cells_summary.csv` - one row per typology cell. `refused` = candidates the search refused (invalid geometry/envelope);
  `best_eval_no` is the 1-based row in `evals.csv` for that cell.
* `evals.csv` - one row per evaluation. `J` is the v4 objective; `term_*` are the **tolerance-normalised** terms
  (raw = term x tolerance, tolerances in `docs/evidence/OBJECTIVE_V4_TOLERANCES.md`; `J = sum(weight x term) + penalty`,
  weights in each cell's brief under `examples/briefs/campaign_2026-10-26_v4/`). `p_*` are the design parameters
  (blank when not used by that family). `freqs_hz`, `bw_h_deg`, `bw_v_deg`, `di_db`, `ripple_*`, `on_axis_db` are JSON
  arrays on the 12-point screen grid (500-10k Hz). Refused rows have blank J/terms.
* `best_designs.json` - best parameters and terms per cell.

Caveats: J is comparable only WITHIN a cell (each brief weights the terms differently). The screen grid has 12 frequency
points, so dispersion between them is interpolated. Cached rows (`cached=True`) re-use an earlier solve of the same geometry.
Each cell's search is CMA-ES with one fixed seed; a "resume" extends the same run, so later rows are later CMA generations.
The solve cache itself (needed to re-score under a different objective without CUDA) is NOT included here.
