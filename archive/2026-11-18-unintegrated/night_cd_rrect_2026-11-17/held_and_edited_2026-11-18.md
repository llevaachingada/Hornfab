# Held / queue edits — cd_rrect_2026-11-17 (2026-11-18, orchestrator, owner-approved)

1. **`w_osse_rrect_fold_warm_v7_200w1` HELD (removed from queue, not dead).** Reason (senior
   direction D4 2026-11-17 evening, owner-informed): its warm-start identity is broken pending
   C5 (digest-based brief identity, owner-gated) and its data links were withdrawn
   (data_agrees false). Its `_w1` config stays committed in `examples/`. To re-queue it later,
   restore its entry with `--cma-seed 41359 --budget 200` as before the hold.
2. **`t_rrect_turbo300` REPLACED by `c_rrect_100w_rc3`** (in the same queue position, index 39):
   `tools/geometry/rosse_rect_cli.py search --config
   examples/typologies/home_landscape_2026-11-15/hl__rosse_rect_cd_v7_r100w.yaml --mode screen
   --budget 110 --cma-seed 5679 --resume C:\Users\hunte\Hrns\hornlab-search\runs\20261117T070118Z-screen-8627f8`
   Owner decision 2026-11-17 (§4 answer 1): the BO sampler rejects this grid-route config
   (`t_rrect80` failed twice: "no successful screen records"); the CMA resume gives the
   R-OSSE rect exploration through a route that works. `--budget 110` preserves the run's
   cumulative cap (rc2's `--budget 109` was refused: "cumulative budget cap would shrink 110 → 109").
3. **`t_atlas_corelaw_turbo300` + `t_atlas_athcore_turbo300` moved to the END of the queue**
   (behind the walls-relieved home jobs) — owner's optional item, answer 1. Entries unchanged.

Validation: full YAML parse OK, 54 unique job ids, no BOM, header intact
(`night: cd_rrect_2026-11-17`, `lane: gpu`). The file is the source of truth; done jobs are
skipped by the runner via queue_state.json.

4. **`w_*_200w1` argv[0] FIX (2026-11-18, orchestrator; D4 lane finding).** All 12 queued
   walls-relieved jobs had a bare `search` token as argv[0]; `kind: command` argv runs verbatim
   (`run_campaign_night.py` Popen), so every one would have died at LAUNCH (FileNotFoundError,
   0 evals). Fixed: the 8 stock-compatible lanes now prepend
   `.venv/Scripts/hornlab-search.exe`; the 5 bridge-type lanes (control →
   `section_pucker_cli.py`, crowe_panel → `crowe_panel_cli.py`, klangfilm_lame v1 →
   `klangfilm_lame_cli.py`, rosse r120 + r50_refine → `rosse_rect_cli.py`) now run
   `.venv/Scripts/python.exe tools/geometry/<bridge>_cli.py search ...` — the same adapter
   pattern the file's existing bridge jobs (`klangfilm_ellipse_cli.py`) and tonight's running
   rrect jobs already use; the bridge CLIs delegate to the stock CLI surface after installing
   their geometry (`rolled_rect_cli.main` → `hornlab_search.cli.main`). Post-fix audit: 54 jobs,
   no bare tokens, all tool paths exist; runner `--dry-run` clean. Evidence of the 5 bridge
   lanes' config-load failure on the stock path:
   `scratch/fable_architecture/.evidence/search_preflight_20261118/` (space_build_failed,
   `unknown rows type`).
