# +-5 deg constant-directivity briefs and jobs (2026-11-25)

**Owner intent (17:35 / 17:43):** a corridor should let a horn hold *any constant* beamwidth near the target, not
accept anything in the range. "Perfectly constant ... at 78 degrees [H] ... 48 degrees vertically ... would be fine";
window +-5 deg.

**Finding** (`../coverage_pull_2026-11-25/replay_constancy.py`, `replay_constancy_*.json`): v9/v10/v11 corridor mode
charges zero anywhere inside [min, max] and never uses `preferred_deg`; the flatness the owner meant exists as the opt-in
`objective.constancy` term (`hornlab_search/objective/scalar_v9.py::_plane_constancy_cost`), which no v11 brief
declared. favL's best (`6552f5c8c536`) is already flat (H 66.6 +-3.2, V 62.4 +-2.0 deg, 0.9-8 kHz) but at the wrong
angles; corridor cost 0.01 of J 1.39.

**Briefs** (new J/BO identities; builder `build_pm5.py`): corridor H 75-85, V 45-55 + `constancy {strict, weight 1.0,
tolerance 0.25}` (level clamped into the window; 5 deg rms off a flat in-window line = 1.0):
- `examples/briefs/home_xo900_2026-11-20/room_landscape_80x50_900_hf1440_v11cd_open115_pm5const_2026-11-25.yaml`
- `examples/briefs/hf2in_2026-11-20/compact500_xo900_80x50_hf2in_v11cd_open115_pm5const_2026-11-25.yaml`

Replay of the 150 favL designs under the compact500 pm5 brief (`replay_favl_pm5.json`): the old best goes J 1.388 ->
6.363 (cov 0.59 + constancy 4.39), i.e. the window now dominates J until the pattern moves to ~80 x 50.

**Jobs** (`examples/typologies/cd_pm5const_2026-11-25/`, inserted into `runs/nights/cd_bo_cohort_2026-11-25.yaml`
after the running job by `queue_pm5.py`; nothing removed; dry-run OK): favl, rolled, lcl_beak, iwar_beak,
sculpted_beak, sculpted_sweep, klangfilm; 100 valid screen solves each; box + seed = each family's exploration run 1
(favL: its 150-valid run's best, sigma0 0.2, no warm start). `check_pm5.py`: loads, BO round trip, box == source, no
problems. `shape_check.txt`: all mesh, 2.1k-6.1k DOF, inside the open envelope. Judged on verify by the six CD rules.
