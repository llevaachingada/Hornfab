# S5 seed packs — status and root cause (2026-11-13, offline)

**Status: BLOCKED (upstream parser bug); packs contain zero selections. No GPU/solve work.**

Two seed packs were built from the fresh M2-gate catalog:

| Pack | Task | Objective | k | Result |
|---|---|---|---:|---|
| `s5/native__ath_core_v4/seed_pack.json` | `native__ath_core_v4` | v4 | 8 | `eligible.total=0`, `selections=[]`, `malformed_records=30,723` |
| `s5/p80x60__osse_ext_throat_home700_v7/seed_pack.json` | `p80x60__osse_ext_throat_home700_v7` | v7 | 8 | `eligible.total=0`, `selections=[]`, `malformed_records=30,723` |

Inputs: `scratch/bo_m0/m2_gate/catalog_20261113/catalog.csv`
(SHA-256 `5e1eb62dca302b7437a86fd2f78a9ca3f3051c949d6f1e9df0b7d1151aa61e10`, 30,723 rows).
The native pack also reads `scratch/bo_m0/r0/offline_scores_native_full/offline_scores.json`
(`2e5f2470…`); the home pack has `scores: null` because there is no replayable home score file
(`docs/evidence/bo_study_2026-11-12/home/READINESS.md`).

## Root cause: `_hex40` rejects the real 12-hex design hash

`tools/analysis/seed_pack.py::_hex40` (current lines 111–115) accepts only strings of length
`>= 16` (its docstring says 40). Every `design_hash` in the catalog is **12 lowercase hex
characters** — the actual format produced by `hornlab_search/design/generated.py:42`
(`sha256(...).hexdigest()[:12]`) — for **30,723 / 30,723** rows.

Consequently `_normalise_record` returns `None` at `seed_pack.py:214–216` for every row. The
builder then reports `malformed_records = total_raw_records - len(records) = 30,723` and has no
eligible rows to deduplicate, score-floor or select. This is a parser-format mismatch, **not**
missing data:

- the same catalog has 217 `ok` rows for the home task (250 rows total; 33 failed);
- it has native rows and one recorded experiment id per run; the M2 gate joins 197 native rows
  through this catalog successfully.

`_hex40` is also used by `_score_map`/`_round_trip_check`, so a partial fix limited to
`_normalise_record` would still drop the score join and the round-trip label.

## Ownership and next action

`tools/analysis/seed_pack.py` is owned by the separate cloud session that will land it as a PR.
This session did **not** edit it. After that PR merges:

1. Accept the real 12-hex (or any non-empty lowercase-hex) design hash while still rejecting
   non-hex/empty values; add a regression test with a 12-hex catalog row.
2. Re-run both pack builds and overwrite
   `docs/evidence/bo_study_2026-11-12/s5/*/seed_pack.json`.
3. Verify `eligible.total > 0`, non-empty selections, and `malformed_records == 0` for a
   well-formed catalog.

## Impact

- S5 seed cards are absent until the fix lands; no S5 selection was fabricated.
- S11 warm starts reference existing run directories (`runs/…`), not seed-pack output, so the
  S11 pilot manifests are unaffected.
- Home readiness uses the catalog directly and is unaffected by this parser; its blockers are the
  ATH-only candidate scan, replay v1–v4, missing `impedance_matrix` and one experiment group
  (`home/READINESS.md`).

## Evidence / verification

- Read-only: catalog CSV read, `seed_pack.build_seed_pack` invoked through its CLI; no solve,
  mesh, GPU, queue, cache or live dataset write.
- The two committed `seed_pack.json` files are the real outputs of those builds; their
  `input.malformed_records=30,723` and empty selections are the evidence of this bug, not a
  placeholder.
