# docs/evidence — committed evidence for the CP-8 checkpoints

Purpose: make the CP-8 checkpoint evidence **durable in git** without committing the raw
datasets/runs. The raw artifacts are large and are gitignored **by design** (see
`AGENTS.md` hard rules and CP-5's measured projection: 10,000 records ≈ 0.78–1.4 GB):

| Local (gitignored) path | What it holds | Size at 2026-10-13 13:1x |
|---|---|---|
| `dataset/` | the real training/validation store (shards, traces) — **precious** | 1069 files, 180.6 MB, 1128 records |
| `runs/<run_id>/` | per-run `search.ndjson`, `designs/`, `cma/`, `best.json`, `run.json`, `config.yaml` | ~3.1 MB ndjson per 1k evals |
| `cache/` | cross-run solve cache | — |

`.gitignore` lines 4–6 anchor exactly these three paths.

What IS committed here:
- `CP-8a.md`, `CP-8b.md`, `CP-8c_*.md` — the checkpoint terminal output, verbatim.
- `logs/` — copies of the live monitor logs used during the long CP-8c runs.
- `manifest.sha256` — SHA-256 + size of the **metadata layer** of the raw artifacts (run books
  `run.json`/`config.yaml`/`best.json`, the per-run `search.ndjson`, the store `index.jsonl` +
  shard JSONLs, committed log copies). It does **NOT** hash the per-record `.npz` label arrays or
  `traces/` (the bulk of the GBs): those are covered by **`dataset verify`** for existence and
  validity, not bit-identity. So the manifest detects tampering/renaming of run books and store
  structure, not silent float corruption inside a label array — worded honestly after review.

- Added 2026-10-22 (user-approved exception): `runs/` — the summarized metadata+log layer
  (run.json/config.yaml/best.json/search.ndjson/cma/*) of all 7 local GPU run dirs, with its own
  index README + `runs/manifest.sha256`. Raw `designs/` blobs are still NOT committed.

Rule: this folder holds **evidence about** the data, never the data itself. If a raw blob must
travel, push it to a data branch / release asset / external store, not to the code branch.
