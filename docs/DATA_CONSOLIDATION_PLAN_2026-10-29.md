# Data consolidation plan — 2026-10-29

Senior analysis of everything hornlab-search stores locally, and a phased plan to cut it from
**~32 GB to ~11 GB** without losing a single solve. Plan only: nothing has been deleted, moved,
linked or compressed. Every number below was measured on this machine on 2026-10-29.

## 1. What is stored

| Store | Size | Files / entries | Role | Verdict |
|---|---|---|---|---|
| `runs/` | 16.0 GB on disk (msh 8.2 GB, npz 6.8 GB, json 0.23 GB, other text ~0.3 GB) | 477 dirs, ~170k files, 30,182 `designs/<hash>/` dirs | Per-search history; GUI, report and loudness tools read `designs/<hash>/{mesh.msh,response.npz}` | **~90% duplicate bytes** |
| `cache/mesh/` | 5.7 GB | 18,109 entries | Canonical mesh store (key `design-mesh[-mounting]`) | Canonical; 1 unreferenced entry |
| `cache/solve/` | 5.6 GB | 20,660 entries | Canonical solve store (key `design-mesh-solve`); re-scoring reads this | Canonical; 1 unreferenced entry |
| `dataset/` | 3.6 GB | 23,884 records, 48 shards | Surrogate-training view (frozen schema v1): traces 1.9 GB, per-record npz 1.6 GB, JSONL 86 MB | Keep; small fixes |
| `dataset_backup_20261022/` | 834 MB | 6,055 records | Pre-beta snapshot | Strict subset of `dataset/` |
| `dataset_backup_20261013/` | 8 MB | 74 records | First-search snapshot | Strict subset of the 10-22 backup |
| `scratch/` | 839 MB | 226 entries | Mixed: `vizenv/` Python env 478 MB, `polluted/` 55 MB, A/B caches, galleries, audits, one-off scripts | ~300 MB junk + misplaced env |
| `docs/` | ~35 MB | 135 md + data/renders | `CONTINUITY.md` 410 KB / 149 entries, `ISSUES.md` 133 KB, `NOTES_FOR_SENIOR.md` 84 KB | Versioning sprawl |
| `report.html` (root) | 5 MB | 1 | Oct 13 report, superseded | Delete |
| Outside the repo (`C:\Users\hunte\Hrns`) | ~62 MB | | `.opencode/` 61 MB, `AppData/` 264 KB (misplaced opencode temp), `gui_fixture/` 232 KB, `beta_suite.txt` and `gui_suite.txt` (two pytest logs), empty `Hrns/.git` with no commits, `hornlab-beta-wt/` worktree | Strays |

**There is no off-machine copy.** `runs/`, `cache/` and `dataset/` are gitignored, and the HF
account `chingadalleva` has no datasets: `tools/hf_sync.py` has never been run. Today the two local
backups are the only safety net, and they sit on the same disk.

## 2. Findings

1. **`runs/` is mostly a third copy of the cache.** `solve/cache.py:copy_entry` and
   `mesh/build.py:_copy_entry` copy, never link: section 14 of the contracts rules out symlinks
   because Windows needs elevation for them. Measured: **6.62 GB of run `mesh.msh` and 6.65 GB of
   run `response.npz` are the same size as their cache entry**, and md5 spot checks are
   byte-identical. Another 1.49 GB of meshes didn't match only because the measurement ignored
   the `-mounting` key suffix, so they are almost certainly duplicates too. A design that appears
   in several runs is stored once per run.
2. **The cache is clean and fully used.** 18,105 of 18,109 meshes and 20,556 of 20,660 solves are
   referenced by a run; 1 of each is referenced by neither a run nor the dataset. A cache GC would
   free nothing, so don't build one now.
3. **`dataset/` arrays are derived from the solve cache.** `rec-NNNN.npz` holds SPL in dB, DI,
   bandwidths and impedance; `cache/solve` holds complex pressures. This is a different
   representation, not a copy, and the schema is frozen, so leave it alone.
4. **Old solver SHAs are not bad data.** Records span beat `38544d2` (14.2k), `760a1ec` (9.1k,
   the current pin) and `fa99ee5` (564). The CONTINUITY rule-7 evidence shows them physics-equal
   to within about 1e-4 dB (Float32 reduction order). Don't cull by SHA.
5. **Failed records cost nothing.** There are 3,467 of them; 3,438 never reached the solver
   (no arrays, roughly 1 KB each). They are useful negatives for an invalid-geometry classifier.
   Keep them.
6. **"Bad" horns are not useless.** The stored `objective` is per-brief: 40 distinct targets, and
   v2/v4/v5 re-scoring is done offline from the cache. A poor design under one brief is a cache
   hit and a training sample under another, and the surrogate needs the bad tail. Deleting by
   score saves little and damages both. Build a curated view instead (Phase 4).
7. **Exact duplicate rows are real but minor.** 768 `(design_hash, solve_hash)` groups add 1,022
   extra rows, about 4%, from CMA restarts and re-evaluations. The schema is append-only, so
   dedupe in the reader, not in the files.
8. **Compression is available for free.** Samples compressed with NTFS (transparent, no code
   change) came out at mesh 1.5x, solve npz 1.4x and traces 1.9x. gzip gives mesh 2.6x, npz 1.9x
   and traces 2.4x. The cache writes uncompressed `np.savez` with float64 arrays.
9. **`runs/` holds 81 non-run entries:** `campaign_*`, `step*`, `m5_*`, pytest `*.xml`, `nights/`,
   `gui_*`. They are cited by path all over CONTINUITY and evidence. Moving them is cosmetic and
   breaks those citations, so leave existing paths alone and stop adding new ones (Phase 4).
10. **Docs version sprawl:** 6 `HANDOFF*.md`, about 10 `*_PLAN*.md`,
    `SOLVE_CAMPAIGN_PLAN_2026-10-26.orig.md`, CONTINUITY at 149 entries growing about 25 KB a
    day, and generation-suffixed config directories (`campaign_2026-10-26` and `..._v4`,
    `*_2026-10-28_v4`, `*_2026-10-29_v5`) mirrored between `examples/briefs` and
    `examples/typologies`.
11. **The `hornlab-beta-wt` worktree** is on `beta-fixes`, **2 commits ahead of origin**
    (unpushed). It also has uncommitted edits to `docs/NEXT_DEV_PRIORITIES.md` and to
    `docs/plan/12_RESEARCH_BASIS.md`, which is a frozen file.

## 3. Phased plan

Each phase has a gate. Run phases one at a time, with no GPU night writing to `runs/` or `cache/`.

### Phase 0: Safety (prerequisite for anything irreversible)

- Commit the 51 uncommitted files on `feat/hardened-plan-2026-10-29`, with the CONTINUITY and
  ISSUES update the push rule requires.
- In `hornlab-beta-wt`: push `beta-fixes` (2 ahead). Decide on the `12_RESEARCH_BASIS.md` edit:
  revert it, or record it as an owner amendment.
- **Make one off-machine backup** of `dataset/` and `cache/solve/` (about 9 GB, the irreplaceable
  GPU work). Meshes and run text can be regenerated or are small. Options:
  `tools/hf_sync.py pack/upload` to a private HF dataset (the owner enters the write token
  themselves), or an external drive.
- **Gate:** the backup is restored to a temp dir and its record count and sha256 manifest match.

### Phase 1: Zero-loss dedupe of `runs/` (saves ~13–15 GB, the main win)

1. **Code first.** The mesher writes `mesh.msh` straight into the run's `designs/<hash>/` and
   then copies it into the cache. If that file were a hardlink, a rebuild into an existing design
   dir would overwrite the cache entry in place. So:
   - make the mesher write to a temp name and `os.replace` it into place, which breaks any link
     safely;
   - change both `copy_entry` and `_copy_entry` to `os.link`, falling back to copy on error.
     Hardlinks need no elevation on NTFS, and a copied run dir is still self-contained.
   - add tests: linked files share an inode, and a rebuild doesn't change the cache bytes.
   - This amends contract §14's "copy, never symlink" to "copy or hardlink, never symlink".
     **That's an owner decision.**
2. **New tool `tools/data/dedupe_runs.py`**, with `--dry-run` as the default. For each run
   `mesh.msh` and `response.npz`: find the cache entry from `status.json.key`, compare sha256
   (not size), and only then replace the run file with a hardlink to the cache file. Write a
   manifest of every link made.
3. **Check `tools/hf_sync.py`.** Python `tarfile` stores repeat inodes as links only within one
   archive, so make sure shards don't silently re-inflate or drop linked files.
4. **Gate:** GUI run-detail, balloon and 3D views, `report`, and `loudness_report` work on an old
   run (Oct 13 `ca15be`) and a new one (Oct 29 `9766f0`). Free space rose by the dry-run's
   estimate.

### Phase 2: Transparent compression (saves ~5–6 GB)

- `compact /c /s /i` on `cache\`, `runs\` and `dataset\traces\`. This is per-file, transparent,
  reversible with `compact /u`, and needs no code change. Measured 1.4–1.9x.
- Optional follow-up as code: `np.savez_compressed` for new solve-cache entries. Loading stays
  backward compatible. Don't rewrite existing entries.
- **Gate:** time one cache-hit eval and one GUI run load before and after. Expect a few percent
  slower at most.

### Phase 3: Real deletions (after Phase 0's backup gate; saves ~1.8 GB)

| Delete | Size | Check first |
|---|---|---|
| `dataset_backup_20261013/` | 8 MB | Subset of the 10-22 backup (verified) |
| `dataset_backup_20261022/` | 834 MB | Subset of `dataset/` (verified). Replaced by the off-machine backup. Update the HANDOFF_BETA "backup" step to point at it |
| Orphan traces in `dataset/traces/` | ~100 MB (55 files) | Re-verify with the Phase 4 doctor tool. The inventory report contradicted itself on whether these are unreferenced files or missing references |
| `scratch/` junk: `polluted/`, `ab_*`, `m3_*_cache*`, `m6_wp12_*`, `ceiling_cache`, `m5wp11_*` trial dirs, old logs | ~300 MB | grep `docs/` for each name; cited ones stay |
| `scratch/vizenv/` | 478 MB | Rebuild it in `%LOCALAPPDATA%\hornlab\vizenv` and update CODE_MAP.md:89 and `tools/render` |
| `report.html` (root) | 5 MB | Regenerable with `cli report` |
| 4 aborted and 4 no-result runs | ~0 | Not cited |
| Outside the repo: `AppData/`, `beta_suite.txt`, `gui_suite.txt`, `.opencode/*.bak-*`, empty `Hrns/.git` | <1 MB | `gui_fixture/` only after grepping the beta worktree's GUI tests (no references found so far) |
| `hornlab-beta-wt/` | | `git worktree remove` after Phase 0's push |

**Don't delete:** failed records, low-score designs, old-SHA records, cited runs (roughly 300;
the inventory's grep is approximate), `docs/plan/**` (frozen), galleries, or gate audits.

### Phase 4: Make it cohesive going forward

- **`tools/data/doctor.py`:** a one-command integrity report covering record counts, orphan and
  missing traces, cache entries referenced by neither runs nor dataset, duplicate
  `(design, solve)` rows, and run dirs with heavy files that aren't hardlinked.
- **`tools/data/keepers.py`:** a derived, regenerable index (CSV or parquet under the gitignored
  `dataset/views/`). It holds the best-per-brief and best-per-typology rows, gate pass status,
  and one row per `(design, solve)`. This is the curated "good horns" list, made without
  deleting the bad tail.
- **New loose artifacts go to `scratch/<date>_<topic>/`**, never to `runs/` (pytest XML, probes,
  campaign manifests). Add that to CONTRIBUTING.md.
- **Config generations:** when a `_vN` generation supersedes another, move the old
  `examples/{briefs,typologies}/<gen>/` dirs to `examples/_archive/` once tests no longer
  reference them. Runs keep their own `config.yaml` snapshot, so reproducibility survives.

### Phase 5: Docs versioning (no data risk)

- **CONTINUITY.md:** keep the status block and the last 7 days. Rotate older entries into
  `docs/history/CONTINUITY_<from>_<to>.md`, verbatim. The per-push rule still holds.
- **ISSUES.md:** move closed issues to `docs/history/ISSUES_closed.md`.
- **NOTES_FOR_SENIOR.md:** move the 15 resolved entries to history. This needs an owner amendment
  because the file is append-only.
- **HANDOFF\*.md:** keep `HANDOFF_COLLABORATOR_2026-10-27.md` and `HANDOFF_BETA.md` current. Move
  `HANDOFF.md`, `HANDOFF_LOCAL.md` and `HANDOFF_COLLABORATOR_2026-10-23.md` to `docs/archive/`
  with a "superseded by" line. Delete `SOLVE_CAMPAIGN_PLAN_2026-10-26.orig.md` (git keeps it).
  Update INDEX.md in the same commit.
- `docs/plan/**` is untouched.

## 4. Expected result

| | Now | After |
|---|---|---|
| `runs/` | 15.4 GB | ~1–2 GB unique (text plus unlinked meshes), then compressed |
| `cache/` | 11.3 GB | ~7.5 GB compressed |
| `dataset/` + backups | 4.4 GB | ~2.7 GB (backups off-machine, traces compressed) |
| `scratch/` | 0.84 GB | ~0.1 GB |
| **Total** | **~32 GB** | **~11 GB**, plus one off-machine backup that doesn't exist today |

## 5. Owner decisions needed

1. Allow hardlinks in the run/cache copy path (amends contract §14)?
2. Off-machine backup target: a private HF dataset (`tools/hf_sync.py`) or an external drive?
3. Rotate CONTINUITY, ISSUES and NOTES_FOR_SENIOR into `docs/history/`, which amends the
   append-only and per-push rules?
4. Confirm the "no quality culling" position: keep low-score and failed designs, and get the
   curated list from `keepers.py`.
