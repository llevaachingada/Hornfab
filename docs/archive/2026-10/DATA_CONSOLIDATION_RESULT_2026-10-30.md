# Data consolidation — result, 2026-10-30

Executed `docs/DATA_CONSOLIDATION_PLAN_2026-10-29.md` (plan) with two owner decisions taken on
2026-10-30: **hardlinks are allowed** in the run/cache copy path (amends `docs/plan/01_CONTRACTS.md`
section 14 to "copy or hardlink, never symlink"), and the **off-machine backup gate is waived**.
Nothing in `docs/plan/**` was edited; the amendment is recorded in CONTINUITY/ISSUES only.

## Result

| Store | Before (logical) | After | How |
|---|---:|---:|---|
| `runs/` | 15.56 GB | ~1.8 GB unique on disk | 49,968 heavy files hardlinked to `cache/` (13.30 GiB) + NTFS compression |
| `cache/` | 10.81 GB | 7.88 GB | NTFS compression (1.5x) |
| `dataset/` | 3.49 GB | 2.46 GB | traces 1.9x, records 1.2x compressed |
| backups | 0.84 GB | 0 | both re-verified strict subsets, then deleted |
| `scratch/` | 0.82 GB | 0.35 GB | `vizenv` moved out of the repo, uncited dirs removed |
| **Total** | **~32.6 GB** | **~12.5 GB** | drive free space +17.26 GB |

The plan's ~11 GB estimate assumed `scratch/` would go to ~0.1 GB and did not count
`%LOCALAPPDATA%/hornlab/vizenv` (460 MB) as still occupying the disk. The 0.4 GB delta is
deliberate: scratch entries whose *family* is cited by an evidence doc were kept.

## What ran, in order

1. **Phase 0** — committed the 51 pending files (`9a59210`); pushed `beta-fixes` (`24dd073..279c5a2`)
   after recording the Solana section as an owner amendment. Backup gate waived by the owner.
2. **Phase 1 code** (`10cf008`) — `solve/cache.py` + `mesh/build.py` install cache files with
   `os.link` (copy fallback) through a temp name + `os.replace`; `response.npz`/`mesh.msh` are
   linked, `status.json`/`mesh_meta.json` stay copies; `save_response` and `evaluate._write_json`
   are atomic; all three mesh routes unlink `out_path` before the mesher writes.
3. **Phase 1 applied** (`d8cc1ba`) — `tools/data/dedupe_runs.py --apply`: **49,968 files,
   13.30 GiB freed, 0 errors**. Dry-run predicted 13.30 GiB exactly. Unmatched 3,954:
   3,806 `no candidate` (GRID/STEP designs have no mesh cache by design), 143 `sha mismatch`,
   5 `no metadata`.
4. **Phase 2** — `compact /c /s:<dir>` on `cache/`, `runs/`, `dataset/`: 3.12 + 0.47 + 0.91 +
   0.32 GB freed, all transparent and reversible with `compact /u`.
5. **Phase 3** — deleted the two backups, the root `report.html`, uncited scratch dirs, 24 orphan
   traces, and the outside-repo strays; removed the `hornlab-beta-wt` worktree; updated
   `HANDOFF_BETA` step B1 to say `dataset/` is the only copy.
6. **Phase 4** — `tools/data/doctor.py` (read-only integrity report, exit 1 on ERROR) and
   `tools/data/keepers.py` (derived CSV at `dataset/views/keepers.csv`, one row per
   `(design, solve)`, best-per-target and best-per-family flags). `gates` is `unavailable` by
   design: the canonical gate functions need per-frequency arrays from a run's `metrics` block,
   which dataset records do not carry — no verdict was invented.
7. **Phase 5** — CONTINUITY/ISSUES/NOTES_FOR_SENIOR rotated older entries into `docs/history/`,
   the three superseded HANDOFF files archived with a "superseded by" line, and INDEX updated.

## Gate evidence (Phase 1)

- GUI data layer on the Oct 13 `ca15be` and Oct 29 `9766f0` runs: `run_detail`, `design_curves`,
  `mesh_surface` (24,480 / 35,376 tris), `balloon_designs` (6/6 with stored balloons), `balloon`,
  `evolution_frames3d` (38 / 12 frames) — all return data.
- `cli report` → 2.7 MB per run; `tools/loudness_report.py` → rows per run.
- 30 random links are `samefile` with their cache file, `st_nlink` 2–6 (a cache entry shared by
  several runs raises the count).
- `dataset verify OK: 23884 records re-read, 0 bad, 0 bad arrays` before and after compression.
- Doctor after the apply: mesh 23,839 linked / 3,702 not (1.6 GB), response 26,129 / 252 not
  (49 MB).

## Findings worth keeping

1. **The 143 `sha mismatch` files are not corruption.** In a sample, complex pressures agree with
   the cache entry to 1.2e-4 while `spl_h_db` differs by up to 4.7 dB and `spl_balloon_db` by up to
   19 dB: the same solve, re-saved with a different SPL convention by an older/re-scoring path.
   The tool refuses to link anything whose sha256 differs, so both representations survive.
2. **The cache is not garbage.** 18,106 of 18,109 mesh entries and 20,659 of 20,660 solve entries
   are referenced; a cache GC would free ~1.6 MB. Do not build one.
3. **GRID/STEP designs have no mesh cache** (`grid_build.py` documents why), which is the whole
   `no candidate` population. That is a design choice, not a leak.
4. **768 duplicate `(design, solve)` groups add 1,022 rows (4%)** — dedupe in the reader
   (`keepers.py` collapses them), not in the append-only files.
5. **`dataset/` records still carry no brief hash** (known gap R8), so `keepers.py` derives its
   brief identity from a hash of the `target` block. Adding `brief_hash` + `generator` metadata
   stays on the HANDOFF_BETA list.

## Manifests and evidence

`scratch/2026-10-30_consolidation/` (gitignored):

| File | What |
|---|---|
| `dedupe_dryrun_full.json` | full pre-apply scan: 49,968 would-link, 13.30 GiB |
| `dedupe_apply_full.json` | per-file record of every link made |
| `doctor_post_dedupe.json` | link/record/trace/cache state after the apply |
| `pytest_phase0.log` | focused suite before the Phase 0 commit |
| `gate_phase1.py`, `orphan_traces.py`, `sha_mismatch_probe.py` | the checks above, re-runnable |

## Not done, deliberately

- **`Hrns/.git`** (an empty repo with no commits) was not deleted: 30 KB, and it defines the
  workspace root. Remove it only if the workspace should stop being a repo.
- **`examples/` generation archive**: no generation is archivable today without editing tests —
  `typologies/campaign_2026-10-26` is pinned by `tests/test_tools_night_runner.py` and the other
  `_v4` dirs have no `_vN` successor in-tree. The policy is in CONTRIBUTING: new configs get one
  generation dir, and a superseded one moves to `examples/_archive/` once tests stop referencing it.
- **`keepers.py` gate verdicts** (see above) and the `aborted/no-result` runs (≈0 bytes, and the
  heuristic that finds them also matches cited campaign manifests).
