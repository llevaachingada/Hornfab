# 07 TASK DATASET

**Wave 1, parallel with 04, 05 and 06. No shared files.**

Owner of: `hornlab_search/dataset/record.py`, `store.py`, `tests/test_dataset_*.py`
Reads: `01_CONTRACTS.md` section 13
Imports: stdlib, `numpy`, `hornlab_search.types`

This is the smallest task in Wave 1 and the one with the longest shadow. You write the thing that records every evaluation the project ever performs.

**Why it is in Wave 1 and not a later fork.** Phase 2 is a neural surrogate that makes population-based search affordable, and the published method family it is modeled on needed **3,000 to 25,600 BEM solves** as training data. Routine search traffic produces exactly those solves. If we record them from the first run, the dataset accumulates for free. If we bolt this on in three months, every evaluation before that point is gone and has to be bought again with GPU-hours. Collin's proposal lives or dies on this file existing early.

You are writing a logging layer. It is not glamorous and it must not lose data.

---

## Build

### 1. `dataset/record.py`

```python
SCHEMA_VERSION = 1

ARRAY_KEYS = ("freqs_hz", "h_angles_deg", "v_angles_deg",
              "spl_h_db", "spl_v_db", "balloon_dirs", "spl_balloon_db",
              "z_throat", "bw_h_deg", "bw_v_deg", "di_db",
              "ripple_h_db", "ripple_v_db", "on_axis_db")


def build_record(ev: Evaluation, target: Target, lib_shas: dict) -> tuple[dict, dict]:
    """Returns (metadata_dict, arrays_dict).

    metadata is JSON-serializable with NO numpy types anywhere.
    arrays maps a key from ARRAY_KEYS to an ndarray, omitting absent ones.

    Records FAILURES too: ok=False, error set, arrays empty. A surrogate needs
    to learn where the invalid region is, and a search needs to know how much
    of its budget went to failures.
    """


def validate_record(meta: dict) -> None:
    """Raise ValueError naming the first problem. Checks every required key,
    that schema_version matches, that lib_shas has all four entries, that no
    value is a numpy type, and that the thing round-trips through json."""
```

The metadata schema is in `01_CONTRACTS.md` section 13, verbatim. Do not add fields; adding one later is a schema bump, which is cheap, but a field that appears in half the records and not the other half is a dataset nobody can load.

**The numpy-type check matters.** `json.dumps` raises on `np.float64`, and it will do so three hours into a search, on the one candidate that happened to produce one. Convert at the boundary with `float()`, `int()` and `.tolist()`, and assert in `validate_record`.

### 2. `dataset/store.py`

```python
class DatasetStore:
    def __init__(self, root: Path,
                 max_records_per_shard: int = 500,
                 max_shard_mb: int = 200): ...

    def append(self, meta: dict, arrays: dict) -> tuple[int, int]:
        """Returns (shard_index, row_index). Appends one line to
        shard-NNNN.jsonl, stores arrays into shard-NNNN.npz under keys
        '<row>/<name>', appends one line to index.jsonl, FLUSHES AND FSYNCS
        all three. Rolls to a new shard when either limit is hit."""

    def __len__(self) -> int: ...
    def read(self, shard: int, row: int) -> tuple[dict, dict]: ...
    def iter_records(self, with_arrays: bool = False): ...
    def stats(self) -> dict:
        """{'n', 'n_ok', 'n_failed', 'by_family', 'by_backend', 'by_lib_sha',
            'date_first', 'date_last', 'total_gpu_seconds', 'disk_mb'}"""
```

### The `.npz` append problem, and how to solve it

`np.savez` cannot append to an existing archive. Rewriting a 200 MB shard on every evaluation would make the dataset slower than the solve.

**Use one directory per shard of individually saved `.npy` files, zipped only when the shard closes:**

```
dataset/
  index.jsonl
  shard-0000.jsonl
  shard-0000/              <- open shard, one .npy per array
    0000_spl_h_db.npy
    0000_freqs_hz.npy
    ...
  shard-0000.npz           <- written once when the shard rolls; the dir is
                              then deleted
```

`read()` checks the `.npz` first, then the open directory. `np.save` of a single array is an atomic-enough single write, costs milliseconds, and appends naturally. Closing a shard is a one-time zip of 500 records.

If that feels fiddly, the acceptable simpler alternative is **one `.npz` per record** in `shard-NNNN/rec-NNNN.npz`. More inodes, no zip step, same guarantees. **Pick one, write it down in the module docstring, and do not change it later**: the loader in phase 2 reads whatever you choose.

### Rules, each of which is a test

1. **Append only.** Never rewrite a closed shard. Never renumber.
2. **`fsync` the index.** A kill mid-run must leave every prior record readable and `index.jsonl` parseable to its last complete line.
3. **`lib_shas` on every record**, all four packages plus `hornlab_search`'s own git SHA. A dataset mixing two solver commits has inconsistent labels, and without the SHA you cannot tell which half to discard.
4. **Record failures.** `ok: false`, the error string, empty arrays.
5. **Never deduplicate on write.** Two records with the same `design_hash` from different solver SHAs are both true and the difference is information.
6. **`stats()` must be cheap**, reading only `index.jsonl`. The CLI calls it on every run.

### 2b. Boundary traces and the structured grid

Promoted from a fork after the neural-operator research pass. `01_CONTRACTS.md` section 13 rules 5 through 7 are the contract; this is the implementation.

```python
class DatasetStore:
    def append_traces(self, design_hash: str, traces: dict) -> str:
        """Write dataset/traces/<design_hash>.npz and return the relative path.
        Called only when the pipeline sampled this design for trace capture."""

    def trace_fraction(self) -> float:
        """Measured fraction of records with captured traces. Reported by stats()."""
```

Three rules:

1. **Sampled, not universal.** Default 1 record in 20, set in the config, and the fraction **recorded in each record's metadata** so a later reader knows whether a gap means "not sampled" or "capture failed".
2. **Traces live outside the shard archives**, keyed by `design_hash`, because they are large and most records will not have them. The record carries `{"captured": true, "path": "traces/<hash>.npz", "kind": ...}`.
3. **`mesh.grid` is recorded on every row**, whether or not the grid itself was reachable. The segment counts are free; the `available` flag tells phase 2 whether the structured-grid input representation is on the table.

Why this is worth doing in Wave 1 rather than later: every boundary-centric surrogate method published trains on boundary solutions, far-field polars alone cannot train any of them, and a solve that has been thrown away cannot give up its traces afterwards. The same applies to the excitation block: B-FNO's verified finding is that frequency must be encoded through the source field on the boundary, so a dataset that recorded only a frequency list is the wrong shape for the method it was collected for.

### 2c. Multi-family sampling is a dataset design requirement

B-FNO varied geometry across its training samples and tested generalization. Ours must be able to as well, which means the dataset cannot be all one family.

```python
def family_balance(self) -> dict:
    """{'OSSE': n, 'R-OSSE': n, 'ICW': n, 'FREEFORM': n} from index.jsonl."""
```

`stats()` reports it, and the CLI prints a warning when one family exceeds 80% of the store. This costs one function and it is the difference between a dataset that can answer "does a surrogate trained on OSSE predict ICW?" and one that cannot. Running the four example configs rather than only the baseline is what actually produces the balance; the warning is there so nobody forgets.

### 3. The export phase 2 will use

```python
def to_training_arrays(store: DatasetStore,
                       family: str | None = None,
                       lib_sha: str | None = None,
                       ok_only: bool = True,
                       keys: list[str] | None = None) -> dict:
    """{'X': (n, k) float32 design matrix,
        'key_names': [...],
        'y_metrics': {name: (n, nf)},
        'y_scalars': {name: (n,)},
        'freqs_hz': (nf,),
        'design_hash': (n,) str,
        'meta': {...}}

    Only records sharing one frequency grid are returned; others are skipped
    and counted in meta['skipped_grid_mismatch'].
    Filtering by lib_sha is the default hygiene step before training.
    """
```

This function is the entire interface between phase 1 and phase 2. Getting it right now means phase 2 starts with `X, y = to_training_arrays(store)` instead of a week of data archaeology.

**The frequency-grid filter earns its line.** Records solved on a `screen` grid and a `verify` grid are not the same label space, and quietly concatenating them trains a model on a lie.

### 4. `hornlab-search dataset` CLI hooks

Task 08 owns `cli.py`, so provide the functions and say in your report which subcommands should call them:

```
hornlab-search dataset stats
hornlab-search dataset verify        # re-validate every record, report bad rows
hornlab-search dataset export --out train.npz [--family OSSE] [--lib-sha ...]
```

`verify` matters: a dataset you have never read back is a dataset you do not have.

---

## Tests

All offline, all fast. `tests/test_dataset_record.py`, `test_dataset_store.py`.

1. `build_record` on a complete `Evaluation` produces metadata that survives `json.dumps` with no default handler.
2. **No numpy types anywhere** in the metadata: walk it recursively and assert every leaf is `str`, `int`, `float`, `bool` or `None`.
3. `build_record` on a failed `Evaluation` sets `ok: false`, keeps the error, and emits empty arrays without raising.
4. `validate_record` rejects a missing required key, naming it.
5. `validate_record` rejects a `lib_shas` missing one package.
6. `validate_record` rejects `np.float64(1.0)` smuggled into a value.
7. `append` then `read` round-trips metadata exactly and every array bit-identically, including dtypes and `None` fields.
8. 1,200 appends with `max_records_per_shard=500` produce shards 0, 1, 2 with 500, 500, 200 records, and `len(store) == 1200`.
9. `index.jsonl` has exactly one line per record, in append order, each parseable.
10. **Crash simulation:** truncate `index.jsonl` mid-line, reopen the store, and assert it reads every complete line, reports the partial one, and appends correctly afterward.
11. **Shard rollover integrity:** after a roll, `read()` still returns records from the closed shard.
12. `stats()` returns the right counts for a store with a known mix of ok and failed records, across two families and two lib SHAs.
13. `to_training_arrays` on 50 synthetic records returns `X` of shape `(50, k)` with `key_names` matching `DesignSpace.keys()` order **alphabetically**, and `y_metrics['bw_h_deg']` of shape `(50, nf)`.
14. `to_training_arrays` with records on two different frequency grids returns only the majority grid and counts the rest in `meta['skipped_grid_mismatch']`.
15. `to_training_arrays(ok_only=True)` excludes failures; `ok_only=False` includes them with NaN labels.
16. `to_training_arrays(lib_sha=...)` filters correctly.
17. Appending 500 records takes under 5 seconds on a normal disk. **Paste the measured time.** If the dataset layer is slow it will be the first thing someone disables, and then phase 2 is dead.
18. Disk usage for 500 typical records is reported as a number, so a projection to 10,000 records is possible. **Paste it.**
19. `validate_record` rejects a record missing the `excitation` block, and one missing `mesh.grid`.
20. `append_traces` writes a readable `.npz` keyed by `design_hash`, the record points at it, and `read()` returns both together.
21. `trace_fraction()` on a store with 100 records and 5 trace captures returns `0.05`.
22. `family_balance()` is correct on a mixed store, and `stats()` flags a store that is 90% one family.
23. `to_training_arrays` returns the `excitation` fields alongside `X`, since they are the frequency-encoding channel for phase 2 and are useless if the exporter drops them.

Tests 10, 17 and 18 are the ones that decide whether this layer survives contact with a real four-hour search.

---

## Checkpoint CP-5

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_dataset_record.py tests/test_dataset_store.py -v
```

Paste it in full, plus:

1. The chosen array-storage layout, with one paragraph of rationale, exactly as it appears in the module docstring.
2. A sample record's metadata, pretty-printed, from a synthetic `Evaluation`.
3. `stats()` output for a 1,200-record synthetic store.
4. Append time for 500 records (test 17).
5. Disk per 500 records, and the projection to 10,000 (test 18), **both with and without trace capture at the default 1-in-20 fraction.**
6. The `to_training_arrays` output shapes and `key_names` for a 50-record store, including the exported `excitation` fields.
7. `family_balance()` and `trace_fraction()` output for a mixed synthetic store.

**CP-5 passes when:** all 23 tests pass, the crash-simulation test actually recovers, and the projected disk for 10,000 records is a number someone can plan around, **with and without traces.**

### CP-5a: what the senior agent checks

**That a record is sufficient to retrain without the original run.** Take one record from the pasted sample and confirm it carries: the full design params, the family, the target, the mesh resolution and dof count, the solve backend and frequency grid, the observation spec, all four library SHAs, and the metric arrays. If anything needed to reproduce or interpret that row lives only in a run directory, the dataset is incomplete and will be worthless the first time a run directory is deleted.

---

## Forks

| Fork | Difficulty | Value | Notes |
|---|---|---|---|
| ~~Capture boundary surface traces~~ | | | **Promoted to build item 2b.** |
| Parquet instead of JSONL plus npz | low | low now | Nicer for analysis, adds `pyarrow`. The JSONL plus npy layout is dependency-free and append-safe, which matters more during a long run. Convert at export time if someone wants a dataframe. |
| Content-addressed mesh storage | low | medium | Keep the `.msh` for a sampled subset keyed by `mesh_hash`. A geometry-encoding surrogate (SDF or point cloud input) needs the actual boundary, not just the parameters, and regenerating meshes later is cheap but not free. |
| Dataset versioning and a manifest | low | medium | A `MANIFEST.json` recording schema version, record count, SHAs present, and date range. Makes the dataset shareable with Collin as a single artifact. |
| Deduplicate at export | trivial | medium | Same `design_hash` and same `lib_sha` means a true duplicate; keep the first. Do it at export, never at write. |
| Publish the dataset | low | **high, strategically** | A public corpus of (waveguide geometry, full balloon) pairs does not exist. It is a byproduct of work already being done, it is the most citable thing this project is likely to produce, and it is what would let anyone else attempt the operator surrogate. Decide the license deliberately, since the solvers are AGPL and GPL. |
