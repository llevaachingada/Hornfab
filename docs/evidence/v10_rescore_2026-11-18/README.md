# v10 rescore: one local command (Fable WP 1.4 / 1.5, cloud senior 2026-11-18)

**Status: tool ready, NOT RUN.** `runs/` exists only on the owner's Windows machine. Nothing here
is a result. CPU only, no GPU, no queue.

## What was wrong, what changed

| Item | Before | After | Label |
|---|---|---|---|
| `objective/replay.py` version gate | `if version not in (1, 2, 3, 4, 7, 9)` refused v10 with `objective_version_not_supported_by_replay`, although `_dispatch` already had a v10 branch. A v10 rescore scored **zero rows**. | `(1, 2, 3, 4, 7, 9, 10)`; reason text updated | code-verified + tested |
| `tools/analysis/rescore_identity.py` | one brief, a list of run dirs on the command line | adds `--run-brief <stem>` (keep only runs whose own `config.yaml` names that brief), `--runs-root <dir>` (find run dirs, depth 3, avoids the Windows 32 767-char command-line limit), and a `compare` subcommand that puts per-lane bests side by side, one column per identity, ranked only within its column | tested |
| Briefs | no v10 brief existed | two **offline rescore-only** briefs in this folder, identical except `version` and `ripple_region` | loader-verified |

Tests: `tests/test_rescore_identity_v10.py` (8), `tests/test_obj_replay_v9_parity.py` (gate
string updated), existing `tests/test_tools_analysis_rescore_identity.py` unchanged and passing.

## The briefs (both `[proposed]`, offline, never queued)

- `home_v9_corridor_rescore.yaml`: the owner's 2026-11-17 evening second-score decision. H corridor
  60-90° (preferred 80) from 700 Hz, V corridor 40-60° (preferred 50) from 1000 Hz, loading on.
  **Constancy NOT declared** (owner: measure its noise floor first). Copied from
  `scratch/fable_architecture/.tmp/v9_candidates/candidate_v_onset_1000.yaml`.
  v9 corridor numbers stay **PROVISIONAL** (ripple mask bug, `scalar_v9.py:493`).
- `home_v10_corridor_preferred_edge_rescore.yaml`: the same file with `version: 10` and
  `ripple_region: preferred_edge` (owner answer 2026-11-18). The rip tolerance and weight are the
  v9 values; the owner may still change them, which would be a new identity.

## Exact local commands (PowerShell, repo root, nothing else running on the CPU lane)

```powershell
$PY   = ".venv\Scripts\python.exe"
$T    = "tools\analysis\rescore_identity.py"
$B7   = "examples\briefs\home_landscape_2026-11-15\room_landscape_80x50_700_hf1440_v7.yaml"
$B9   = "docs\evidence\v10_rescore_2026-11-18\home_v9_corridor_rescore.yaml"
$B10  = "docs\evidence\v10_rescore_2026-11-18\home_v10_corridor_preferred_edge_rescore.yaml"
$STEM = "room_landscape_80x50_700_hf1440_v7"           # the home brief's runs only
$OUT  = "runs\analysis\v10_rescore_2026-11-18"

# 1. WP 1.4: the same stored responses under three identities (never pooled)
& $PY $T rescore --brief $B7  --run-brief $STEM --runs-root runs --out "$OUT\v7"
& $PY $T rescore --brief $B9  --run-brief $STEM --runs-root runs --out "$OUT\v9"
& $PY $T rescore --brief $B10 --run-brief $STEM --runs-root runs --out "$OUT\v10"

# 2. side by side: one column per identity, ranked only within its own column
& $PY $T compare --out "$OUT\compare" v7="$OUT\v7" v9="$OUT\v9" v10="$OUT\v10"

# 3. WP 1.5: frequency part of the v10 noise floor (screen vs verify, same mesh)
& $PY $T floor --brief $B10 --runs-root runs --top 28 --out "$OUT\floor_v10"
& $PY $T floor --brief $B7  --runs-root runs --top 28 --out "$OUT\floor_v7"
```

Outputs (all under `runs\analysis\v10_rescore_2026-11-18\`): `v7|v9|v10\rescore.jsonl` (one row
per design, with status and reasons), `rescore_summary.json` (score ids, status counts,
`lane_best`), `compare\lane_bests_side_by_side.csv` + `compare_summary.json`,
`floor_*\floor_summary.json` + `floor_pairs.jsonl`.

## Acceptance checks for the local agent (do these before anyone reads a ranking)

1. **v7 parity:** every row of `v7\rescore.jsonl` whose run used the v7 home brief should carry
   `parity_delta` ≈ 0 when replayed by `replay_run_dir` (the v7 column is the self-check). If
   `status_counts` shows many non-`exact_complete` rows, report the top `reasons`, do not rank.
2. **One identity per column:** `compare_summary.json` → `columns.<label>.mixed_identity` must be
   `false` for all three. If true, stop: two score identities ended up in one column.
3. **Floor before ranks:** a v10 lane gap below `floor_v10\floor_summary.json` `sd_diff_top` is a
   TIE (plan §7 invariant 7). Until the v10 floor exists, use nothing from the v10 column for a
   decision. v7 uses ≈ 0.13 J (D8) until B1 lands.
4. Commit the three `rescore_summary.json`, `compare\*` and `floor_*\floor_summary.json` into a new
   `docs/evidence/v10_rescore_<date>/results/` folder with CONTINUITY / ISSUES / INDEX lines. Do
   not commit `rescore.jsonl` if it is over ~5 MB; quote its row count instead.

## What this does not do

- It does not change any default, brief in `examples/`, queue or stored row.
- It does not make v10 the nights' score. Owner decision (2026-11-17): nights stay v7 until a
  physical measurement (D6 stage 2b) shows which score predicts a real horn better.
