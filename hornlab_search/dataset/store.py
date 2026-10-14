"""Append-only dataset store: JSONL metadata + one ``.npz`` of arrays per record.

ARRAY-STORAGE LAYOUT (chosen once, do not change; the phase-2 loader reads exactly this):

    dataset/
      index.jsonl                one line per record: cheap to read, the only file stats() opens
      shard-0000.jsonl           one metadata object per line (the record, strict JSON)
      shard-0000/                arrays of shard 0: ONE uncompressed .npz PER RECORD
        rec-0000.npz               keys are the plain ARRAY_KEYS names ("spl_h_db", ...)
        rec-0001.npz
      shard-0001.jsonl  shard-0001/ ...
      traces/<design_hash>.npz   boundary traces, sampled, outside the shards

Rationale: ``np.savez`` cannot append to an archive, and rewriting a growing 200 MB archive on
every evaluation would make the dataset slower than the solve. One small ``.npz`` per record
needs a single fsync instead of one per array, has no zip step at shard close and nothing to
recover if the process dies mid-close, and reads back bit-identically (no compression, no dtype
changes). The cost is more inodes (one per record with arrays; failures write none), which is
irrelevant at the 10^4 records this project produces. A shard "rolls" simply by the next append
going to ``shard-(N+1)``; closed shards are never opened for writing again. This is the task's
accepted simpler alternative; 01_CONTRACTS.md section 13's "shard-0000.npz keyed <row>/<name>" is
not used. Compress at export time if a single archive is wanted (``export_training_npz``).

Durability: ``append`` writes the record ``.npz`` and fsyncs it; only then does it write the
record's line to the shard jsonl (the COMMIT POINT: a record exists iff its jsonl line is
complete) and its line to ``index.jsonl``, and those two files are fsynced concurrently (one
extra thread), because fsync latency is the whole cost of an append and the two are independent.
All three files are flushed and fsynced before ``append`` returns. A kill at any point leaves every
earlier record readable. On reopen the store truncates a torn final line in the index or the open
shard, deletes arrays of an uncommitted row, and re-derives any index line that is missing because
the process died between the jsonl and index writes. The repairs it made are reported in
``store.recovery``.

One writer at a time. The store holds a thread lock, not a process lock; two processes appending to
the same root would interleave rows. The pipeline runs one search at a time on one GPU.

This module imports only the stdlib, numpy and ``hornlab_search.types`` (through record.py).
"""
from __future__ import annotations

import json
import os
import re
import threading
from collections import Counter
from pathlib import Path

import numpy as np

from .record import (ARRAY_KEYS, FAMILIES, SCHEMA_VERSION, dumps_strict, lib_sha_key,
                     to_jsonable, validate_record)

#: stats() warns when one family exceeds this share of the store (once there are enough records
#: for the share to mean anything).
FAMILY_WARN_FRACTION = 0.8
FAMILY_WARN_MIN_RECORDS = 10

#: np.savez(file, *args, allow_pickle=True, **kwds): these names would collide with parameters.
_RESERVED_NPZ_KEYS = {"file", "allow_pickle"}
_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_HASH_RE = re.compile(r"^[A-Za-z0-9_-]+$")

#: Per-frequency metric arrays exported by to_training_arrays.
Y_METRIC_KEYS = ("bw_h_deg", "bw_v_deg", "di_db", "ripple_h_db", "ripple_v_db", "on_axis_db")


# ------------------------------------------------------------------ low-level io

def _fsync_file(f) -> None:
    f.flush()
    os.fsync(f.fileno())


def _scan_lines(data: bytes) -> tuple[list[tuple[int, int]], int]:
    """Offsets (start, length including the newline) of every newline-terminated line, and the
    byte length of the unterminated tail (0 if the data ends on a newline)."""
    offsets: list[tuple[int, int]] = []
    pos = 0
    while True:
        nl = data.find(b"\n", pos)
        if nl < 0:
            break
        offsets.append((pos, nl + 1 - pos))
        pos = nl + 1
    return offsets, len(data) - pos


def _check_arrays(arrays: dict | None, allowed: tuple | None, where: str) -> dict:
    """Drop None values; reject unknown/odd keys and object arrays; return plain ndarrays."""
    out = {}
    for k, v in (arrays or {}).items():
        if v is None:
            continue
        if allowed is not None and k not in allowed:
            raise ValueError(f"{where}: unknown array key '{k}' (allowed: {allowed})")
        if not _KEY_RE.match(k) or k in _RESERVED_NPZ_KEYS:
            raise ValueError(f"{where}: illegal array key '{k}'")
        a = np.asarray(v)
        if a.dtype == object:
            raise ValueError(f"{where}: array '{k}' has dtype object (pickle is not allowed)")
        out[k] = a
    return out


def _write_npz_atomic(path: Path, arrays: dict) -> int:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f:
        np.savez(f, **arrays)
        _fsync_file(f)
    os.replace(tmp, path)
    return path.stat().st_size


def _write_npz_inplace(path: Path, arrays: dict) -> int:
    """Write and fsync. No temp file: the shard jsonl line is the commit point, so a torn file for
    a row whose line was never written is simply overwritten (or deleted on reopen)."""
    with open(path, "wb") as f:
        np.savez(f, **arrays)
        _fsync_file(f)
    return path.stat().st_size


def _load_npz(path: Path, keys=None) -> dict:
    with np.load(path, allow_pickle=False) as z:
        names = list(z.files) if keys is None else [k for k in keys if k in z.files]
        return {k: z[k] for k in names}


def _index_entry(meta: dict, shard: int, row: int) -> dict:
    """The index line for a record. Everything stats() and the exporter's filters need, so that
    neither has to open a shard."""
    return {
        "design_hash": meta["design_hash"], "shard": shard, "row": row,
        "objective": meta["objective"], "ok": meta["ok"],
        "family": meta["family"], "backend": meta["solve"]["backend"],
        "mode": meta["solve"]["mode"], "lib_sha": lib_sha_key(meta["lib_shas"]),
        "created_utc": meta["created_utc"], "solve_seconds": meta["solve"]["seconds"],
        "traces": bool(meta["traces"]["captured"]),
    }


# ------------------------------------------------------------------ the store

class DatasetStore:
    def __init__(self, root: Path,
                 max_records_per_shard: int = 500,
                 max_shard_mb: int = 200):
        if max_records_per_shard < 1:
            raise ValueError("max_records_per_shard must be >= 1")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_records = int(max_records_per_shard)
        self.max_bytes = int(max_shard_mb * 1024 * 1024)
        self._lock = threading.RLock()
        self._executor = None
        self._index: list[dict] = []
        self._offsets: dict[int, list[tuple[int, int]]] = {}
        self._blob: tuple[int, int, bytes] | None = None     # (shard, size, bytes) read cache
        self._cur = 0
        self._cur_rows = 0
        self._cur_bytes = 0
        #: What opening the store had to repair. Empty when the store was clean.
        self.recovery: dict = {}
        self._open_existing()

    # -------------------------------------------------------------- paths

    @property
    def index_path(self) -> Path:
        return self.root / "index.jsonl"

    def shard_jsonl(self, shard: int) -> Path:
        return self.root / f"shard-{shard:04d}.jsonl"

    def shard_dir(self, shard: int) -> Path:
        return self.root / f"shard-{shard:04d}"

    def record_npz(self, shard: int, row: int) -> Path:
        return self.shard_dir(shard) / f"rec-{row:04d}.npz"

    @property
    def traces_dir(self) -> Path:
        return self.root / "traces"

    # -------------------------------------------------------------- open / recover

    def _note(self, key: str, value) -> None:
        self.recovery[key] = self.recovery.get(key, 0) + value if isinstance(value, int) \
            else value

    def _open_existing(self) -> None:
        # 1. index.jsonl: keep every complete, parseable line; drop a torn tail.
        ip = self.index_path
        if ip.exists():
            data = ip.read_bytes()
            offsets, tail = _scan_lines(data)
            for start, ln in offsets:
                try:
                    entry = json.loads(data[start:start + ln])
                    if not isinstance(entry, dict):
                        raise ValueError
                    self._index.append(entry)
                except ValueError:
                    self._note("bad_index_lines", 1)
            if tail:
                self._note("partial_index_line_bytes", tail)
                with open(ip, "r+b") as f:
                    f.truncate(len(data) - tail)
                    _fsync_file(f)

        # 2. the highest shard is the open one; a torn final line there is dropped.
        shards = sorted(int(m.group(1)) for p in self.root.glob("shard-*.jsonl")
                        if (m := re.fullmatch(r"shard-(\d+)\.jsonl", p.name)))
        if shards:
            self._cur = shards[-1]
            jp = self.shard_jsonl(self._cur)
            data = jp.read_bytes()
            offsets, tail = _scan_lines(data)
            if tail:
                self._note("partial_shard_line_bytes", tail)
                with open(jp, "r+b") as f:
                    f.truncate(len(data) - tail)
                    _fsync_file(f)
                data = data[:len(data) - tail]
            self._offsets[self._cur] = offsets
            self._cur_rows = len(offsets)
            self._cur_bytes = len(data)
            d = self.shard_dir(self._cur)
            if d.is_dir():
                for p in d.iterdir():
                    m = re.fullmatch(r"rec-(\d+)\.npz", p.name)
                    if p.name.endswith(".tmp") or (m and int(m.group(1)) >= self._cur_rows):
                        p.unlink()                      # arrays of a row that was never committed
                        self._note("orphan_array_files", 1)
                    else:
                        self._cur_bytes += p.stat().st_size

            # 3. a record in the shard but not in the index: the process died between the second
            #    and third write. Re-derive the index line from the record itself.
            have = {(e.get("shard"), e.get("row")) for e in self._index}
            for row in range(self._cur_rows):
                if (self._cur, row) in have:
                    continue
                meta = self._read_meta(self._cur, row)
                self._append_index(_index_entry(meta, self._cur, row))
                self._note("index_rebuilt_rows", 1)
            ahead = [e for e in self._index
                     if e.get("shard") == self._cur and e.get("row", -1) >= self._cur_rows]
            if ahead:
                self._note("index_entries_without_record", len(ahead))
        self._maybe_roll()

    def _maybe_roll(self) -> None:
        if self._cur_rows >= self.max_records or self._cur_bytes >= self.max_bytes:
            self._cur += 1
            self._cur_rows = 0
            self._cur_bytes = 0

    def _pool(self):
        if self._executor is None:
            from concurrent.futures import ThreadPoolExecutor
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="dataset-fsync")
        return self._executor

    def _append_index(self, entry: dict) -> None:
        line = (dumps_strict(entry) + "\n").encode("ascii")
        with open(self.index_path, "ab") as f:
            f.write(line)
            _fsync_file(f)
        self._index.append(entry)

    # -------------------------------------------------------------- write

    def append(self, meta: dict, arrays: dict | None = None) -> tuple[int, int]:
        """Returns (shard_index, row_index). Validates, writes the record's arrays, appends one
        line to shard-NNNN.jsonl, appends one line to index.jsonl; each write is flushed and
        fsynced. Rolls to a new shard when either limit is hit.

        Raises ValueError (before anything is written) if the record does not validate. The caller
        in the search loop should catch it, log it at ERROR, and continue.
        """
        validate_record(meta)
        arrs = _check_arrays(arrays, ARRAY_KEYS, "append")
        line = (dumps_strict(meta) + "\n").encode("ascii")
        with self._lock:
            s, r = self._cur, self._cur_rows
            nbytes = 0
            if arrs:
                self.shard_dir(s).mkdir(exist_ok=True)
                nbytes += _write_npz_inplace(self.record_npz(s, r), arrs)      # fsynced
            entry = _index_entry(meta, s, r)
            iline = (dumps_strict(entry) + "\n").encode("ascii")
            with open(self.shard_jsonl(s), "ab") as fj, open(self.index_path, "ab") as fi:
                fj.seek(0, os.SEEK_END)
                start = fj.tell()
                fj.write(line)
                fj.flush()
                fi.write(iline)
                fi.flush()
                pending = self._pool().submit(os.fsync, fi.fileno())
                os.fsync(fj.fileno())
                pending.result()
            self._offsets.setdefault(s, []).append((start, len(line)))
            self._index.append(entry)
            self._cur_rows += 1
            self._cur_bytes += nbytes + len(line)
            self._maybe_roll()
            return s, r

    def append_traces(self, design_hash: str, traces: dict) -> str:
        """Write traces/<design_hash>.npz and return the path relative to the store root, as the
        record's traces.path wants it. Called only when the pipeline sampled this design.

        Never overwrites: a second capture for the same design_hash (a different solver commit)
        goes to traces/<design_hash>-1.npz and so on, and the returned path says which.
        """
        if not _HASH_RE.match(str(design_hash)):
            raise ValueError(f"append_traces: illegal design_hash {design_hash!r}")
        arrs = _check_arrays(traces, None, "append_traces")
        if not arrs:
            raise ValueError("append_traces: no arrays to write")
        with self._lock:
            self.traces_dir.mkdir(exist_ok=True)
            name, i = f"{design_hash}.npz", 0
            while (self.traces_dir / name).exists():
                i += 1
                name = f"{design_hash}-{i}.npz"
            _write_npz_atomic(self.traces_dir / name, arrs)
            return f"traces/{name}"

    # -------------------------------------------------------------- read

    def __len__(self) -> int:
        return len(self._index)

    @property
    def index(self) -> list[dict]:
        """A copy of the in-memory index, in append order."""
        with self._lock:
            return [dict(e) for e in self._index]

    def _shard_offsets(self, shard: int) -> list[tuple[int, int]]:
        if shard not in self._offsets:
            p = self.shard_jsonl(shard)
            if not p.exists():
                raise KeyError(f"no shard {shard}")
            self._offsets[shard], _ = _scan_lines(p.read_bytes())
        return self._offsets[shard]

    def _read_meta(self, shard: int, row: int) -> dict:
        offsets = self._shard_offsets(shard)
        if not 0 <= row < len(offsets):
            raise KeyError(f"no record at shard {shard} row {row}")
        start, ln = offsets[row]
        size = offsets[-1][0] + offsets[-1][1]
        blob = self._blob
        if blob is None or blob[0] != shard or blob[1] != size:
            with open(self.shard_jsonl(shard), "rb") as f:
                data = f.read(size)
            blob = self._blob = (shard, size, data)
        return json.loads(blob[2][start:start + ln])

    def _read_arrays(self, shard: int, row: int, keys=None) -> dict:
        p = self.record_npz(shard, row)
        return _load_npz(p, keys) if p.exists() else {}

    def read_traces(self, meta: dict) -> dict:
        """The boundary traces a record points at, or {} if it has none."""
        tr = meta.get("traces") or {}
        if not tr.get("captured") or not tr.get("path"):
            return {}
        p = (self.root / tr["path"]).resolve()
        if self.root.resolve() not in p.parents:
            raise ValueError(f"traces.path escapes the store: {tr['path']!r}")
        return _load_npz(p)

    def read(self, shard: int, row: int, with_traces: bool = False) -> tuple[dict, dict]:
        """(metadata, arrays). Arrays are bit-identical to what was appended, dtypes included;
        a failed record has no arrays. With with_traces=True and a captured trace, the trace
        arrays are added under keys 'traces/<name>'."""
        with self._lock:
            meta = self._read_meta(shard, row)
        arrays = self._read_arrays(shard, row)
        if with_traces:
            for k, v in self.read_traces(meta).items():
                arrays[f"traces/{k}"] = v
        return meta, arrays

    def iter_records(self, with_arrays: bool = False, where=None, array_keys=None):
        """Yield (meta, arrays) in append order. ``arrays`` is None unless with_arrays=True.
        ``where`` is an optional predicate on the index entry, applied before any record is read.
        ``array_keys`` limits which arrays are loaded."""
        for e in self.index:
            if where is not None and not where(e):
                continue
            with self._lock:
                meta = self._read_meta(e["shard"], e["row"])
            arrays = self._read_arrays(e["shard"], e["row"], array_keys) if with_arrays else None
            yield meta, arrays

    # -------------------------------------------------------------- stats

    def trace_fraction(self) -> float:
        """Measured fraction of records with captured traces (0.0 for an empty store)."""
        n = len(self._index)
        return 0.0 if n == 0 else sum(1 for e in self._index if e.get("traces")) / n

    def family_balance(self) -> dict:
        """{'OSSE': n, 'R-OSSE': n, 'ICW': n, 'FREEFORM': n} from the index (other families, if
        any ever appear, are added)."""
        c = Counter(e.get("family") for e in self._index)
        out = {f: c.pop(f, 0) for f in FAMILIES}
        out.update(dict(c))
        return out

    def _disk_mb(self) -> float:
        total = 0
        stack = [self.root]
        while stack:
            with os.scandir(stack.pop()) as it:
                for de in it:
                    if de.is_dir(follow_symlinks=False):
                        stack.append(Path(de.path))
                    else:
                        total += de.stat(follow_symlinks=False).st_size
        return total / (1024 * 1024)

    def stats(self) -> dict:
        """Cheap: reads only the in-memory copy of index.jsonl (plus one directory walk for
        disk_mb). Keys: n, n_ok, n_failed, by_family, by_backend, by_lib_sha, date_first,
        date_last, total_gpu_seconds, disk_mb, plus trace_fraction, family_balance,
        family_warning (a message or None), n_shards, n_duplicate_designs and missing_families.

        ``n_duplicate_designs`` counts distinct ``design_hash`` values that appear MORE THAN ONCE
        in the index (a repeated design can straddle a cluster holdout split and inflate a gate).
        ``missing_families`` lists which of record.FAMILIES have zero records: the 80 % share
        warning below can never flag a MISSING family, so it is reported directly."""
        idx = self._index
        n = len(idx)
        n_ok = sum(1 for e in idx if e.get("ok"))
        dates = [e["created_utc"] for e in idx if e.get("created_utc")]
        gpu = sum(float(e.get("solve_seconds") or 0.0) for e in idx
                  if str(e.get("backend", "")).endswith("cuda"))
        bal = self.family_balance()
        dh_counts = Counter(e.get("design_hash") for e in idx)
        n_duplicate = sum(1 for c in dh_counts.values() if c > 1)
        missing_families = [f for f in FAMILIES if bal.get(f, 0) == 0]
        warning = None
        if n >= FAMILY_WARN_MIN_RECORDS:
            fam, cnt = max(bal.items(), key=lambda kv: kv[1])
            if cnt / n > FAMILY_WARN_FRACTION:
                warning = (f"dataset is {100.0 * cnt / n:.0f}% {fam} ({cnt}/{n}): a surrogate "
                           f"trained on it cannot be tested on other families; run the other "
                           f"example configs")
        return {
            "n": n, "n_ok": n_ok, "n_failed": n - n_ok,
            "by_family": dict(Counter(e.get("family") for e in idx)),
            "by_backend": dict(Counter(e.get("backend") for e in idx)),
            "by_lib_sha": dict(Counter(e.get("lib_sha") for e in idx)),
            "date_first": min(dates) if dates else None,
            "date_last": max(dates) if dates else None,
            "total_gpu_seconds": gpu,
            "disk_mb": self._disk_mb(),
            "trace_fraction": self.trace_fraction(),
            "family_balance": bal,
            "family_warning": warning,
            "n_shards": len({e.get("shard") for e in idx}),
            "n_duplicate_designs": n_duplicate,
            "missing_families": missing_families,
        }


# ------------------------------------------------------------------ phase-2 interface

def _is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, str)


def _grid_of(meta: dict) -> tuple:
    return tuple(round(float(f), 4) for f in (meta["solve"].get("freqs_hz") or []))


def to_training_arrays(store: DatasetStore,
                       family: str | None = None,
                       lib_sha: str | None = None,
                       ok_only: bool = True,
                       keys: list[str] | None = None) -> dict:
    """The entire interface between phase 1 and phase 2.

    {'X': (n, k) float32 design matrix, 'key_names': [...],
     'y_metrics': {name: (n, nf) float64}, 'y_scalars': {name: (n,) float64},
     'freqs_hz': (nf,), 'design_hash': (n,) str, 'family': (n,) str, 'ok': (n,) bool,
     'di_source': (n,) str,
     'excitation': {port_tag, port_name, kind, amplitude, units, frequency_dependent: (n,)},
     'meta': {...}}

    Only records sharing one frequency grid (the grid of the majority of the selected successful
    records) are returned; the rest are skipped and counted in meta['skipped_grid_mismatch'].
    Records on a screen grid and a verify grid are not the same label space, and concatenating them
    quietly trains a model on a lie.

    family       keep only this family.
    lib_sha      keep only records whose label provenance matches: the index key
                 ("<mesher10>+<beat10>"), or a prefix (>= 7 chars) of any SHA in the record's
                 lib_shas. Filtering by lib_sha is the default hygiene step before training.
    ok_only      False also returns failures, with NaN labels (X is still filled: where the
                 invalid region lies is the information).
    keys         design-parameter columns of X, in the order given (pass DesignSpace.keys()).
                 Default: every parameter that is numeric in every record that has it, sorted
                 alphabetically. Missing values are NaN. Non-numeric default columns (ICW
                 'termination', FREEFORM point lists) are listed in meta['skipped_keys'].
    """
    def want(e: dict) -> bool:
        if family is not None and e.get("family") != family:
            return False
        if ok_only and not e.get("ok"):
            return False
        return True

    pairs = [(m, a) for m, a in store.iter_records(
        with_arrays=True, where=want,
        array_keys=Y_METRIC_KEYS + ("z_throat",))]
    if lib_sha is not None:
        def lib_match(m: dict) -> bool:
            if lib_sha_key(m["lib_shas"]) == lib_sha:
                return True
            return len(lib_sha) >= 7 and any(str(v).startswith(lib_sha) for v in m["lib_shas"].values())
        pairs = [(m, a) for m, a in pairs if lib_match(m)]
    n_considered = len(pairs)

    # The frequency grid: majority among successful records, first seen wins a tie.
    ok_grids = [_grid_of(m) for m, _ in pairs if m["ok"]]
    all_grids = ok_grids or [_grid_of(m) for m, _ in pairs if _grid_of(m)]
    counts: dict[tuple, int] = {}
    for g in all_grids:
        counts[g] = counts.get(g, 0) + 1
    grid = max(counts, key=lambda g: counts[g]) if counts else ()
    nf = len(grid)

    kept, skipped_grid, skipped_bad = [], 0, 0
    for m, a in pairs:
        g = _grid_of(m)
        if g and g != grid:
            skipped_grid += 1
            continue
        if m["ok"]:
            bad = any(k in a and (a[k].ndim != 1 or a[k].shape[0] != nf) for k in Y_METRIC_KEYS)
            if not g or bad:
                skipped_bad += 1
                continue
        kept.append((m, a))
    n = len(kept)

    # X
    skipped_keys: list[str] = []
    if keys is None:
        seen: dict[str, bool] = {}
        for m, _ in kept:
            for k, v in m["params"].items():
                seen[k] = seen.get(k, True) and _is_number(v)
        key_names = sorted(k for k, numeric in seen.items() if numeric)
        skipped_keys = sorted(k for k, numeric in seen.items() if not numeric)
    else:
        key_names = list(keys)
    X = np.full((n, len(key_names)), np.nan, dtype=np.float32)
    for i, (m, _) in enumerate(kept):
        for j, k in enumerate(key_names):
            v = m["params"].get(k)
            if v is None:
                continue
            if not _is_number(v):
                raise ValueError(f"to_training_arrays: parameter '{k}' is not numeric "
                                 f"(design {m['design_hash']}: {v!r})")
            X[i, j] = float(v)

    # y
    y_metrics = {k: np.full((n, nf), np.nan) for k in Y_METRIC_KEYS}
    z_real = np.full((n, nf), np.nan)
    scalar_names: dict[str, None] = {"objective": None}
    for m, _ in kept:
        for k, v in m["metrics_scalars"].items():
            if _is_number(v) or v is None:
                scalar_names[k] = None
    scalar_names.pop("di_source", None)
    y_scalars = {k: np.full(n, np.nan) for k in scalar_names}
    for i, (m, a) in enumerate(kept):
        if m["ok"]:
            for k in Y_METRIC_KEYS:
                if k in a:
                    y_metrics[k][i] = a[k]
            if "z_throat" in a and a["z_throat"].shape == (nf,):
                z_real[i] = np.real(a["z_throat"])
        if m["objective"] is not None:
            y_scalars["objective"][i] = float(m["objective"])
        for k, v in m["metrics_scalars"].items():
            if k in y_scalars and v is not None and _is_number(v):
                y_scalars[k][i] = float(v)
    y_metrics["z_throat_real"] = z_real

    exc_keys = ("port_tag", "port_name", "kind", "amplitude", "units", "frequency_dependent")
    excitation = {
        "port_tag": np.array([m["excitation"]["port_tag"] for m, _ in kept], dtype=np.int64),
        "port_name": np.array([m["excitation"]["port_name"] for m, _ in kept], dtype=str),
        "kind": np.array([m["excitation"]["kind"] for m, _ in kept], dtype=str),
        "amplitude": np.array([m["excitation"]["amplitude"] for m, _ in kept], dtype=np.float64),
        "units": np.array([m["excitation"]["units"] for m, _ in kept], dtype=str),
        "frequency_dependent": np.array([m["excitation"]["frequency_dependent"] for m, _ in kept],
                                        dtype=bool),
    }
    assert set(excitation) == set(exc_keys)
    di_source = np.array([str(m["metrics_scalars"].get("di_source", "")) for m, _ in kept],
                         dtype=str)
    return {
        "X": X,
        "key_names": key_names,
        "y_metrics": y_metrics,
        "y_scalars": y_scalars,
        "freqs_hz": np.array(grid, dtype=np.float64),
        "design_hash": np.array([m["design_hash"] for m, _ in kept], dtype=str),
        "family": np.array([m["family"] for m, _ in kept], dtype=str),
        "ok": np.array([m["ok"] for m, _ in kept], dtype=bool),
        "di_source": di_source,
        "excitation": excitation,
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "n_considered": n_considered,
            "n_selected": n,
            "skipped_grid_mismatch": skipped_grid,
            "skipped_bad_arrays": skipped_bad,
            "skipped_keys": skipped_keys,
            "family": family,
            "lib_sha": lib_sha,
            "ok_only": ok_only,
        },
    }


# ------------------------------------------------------------------ CLI hooks (task 08 wires them)

def verify_store(store: DatasetStore, check_arrays: bool = True) -> dict:
    """Re-read and re-validate every record. A dataset you have never read back is a dataset you
    do not have. Returns {'n', 'n_bad', 'bad', 'n_bad_arrays', 'bad_arrays',
    'recovery': store.recovery}. Called by `hornlab-search dataset verify`.

    ``bad`` lists records that fail validation or existence checks. ``bad_arrays`` lists OK records
    whose present per-frequency metric arrays are not 1-D with ``len == len(solve.freqs_hz)`` —
    reported separately because they would otherwise pass here and then silently vanish from the
    training pool via ``to_training_arrays``' ``skipped_bad_arrays``. Each entry has the same
    {'shard','row','design_hash','problem'} shape as ``bad``."""
    bad, bad_arrays = [], []
    for e in store.index:
        s, r, h = e.get("shard"), e.get("row"), e.get("design_hash")
        try:
            meta, arrays = store.read(s, r)
            validate_record(meta)
            if meta["design_hash"] != h:
                raise ValueError("index design_hash disagrees with the record")
            if meta["ok"] != bool(e.get("ok")):
                raise ValueError("index ok flag disagrees with the record")
            if check_arrays:
                if meta["ok"] and not arrays:
                    raise ValueError("successful record has no arrays")
                if not meta["ok"] and arrays:
                    raise ValueError("failed record has arrays")
                if meta["traces"]["captured"]:
                    if not store.read_traces(meta):
                        raise ValueError("trace file is missing or empty")
                if meta["ok"]:                  # shape problems: separate list, never a silent drop
                    nf = len(meta["solve"].get("freqs_hz") or [])
                    for k in Y_METRIC_KEYS:
                        if k not in arrays:
                            continue
                        a = np.asarray(arrays[k])
                        if a.ndim != 1 or a.shape[0] != nf:
                            bad_arrays.append({"shard": s, "row": r, "design_hash": h,
                                               "problem": f"array '{k}' has shape {a.shape}; "
                                                          f"expected 1-D length {nf} "
                                                          f"(len(solve.freqs_hz))"})
        except Exception as ex:                      # noqa: BLE001 - report every bad row
            bad.append({"shard": s, "row": r, "design_hash": h,
                        "problem": f"{type(ex).__name__}: {ex}"})
    return {"n": len(store), "n_bad": len(bad), "bad": bad,
            "n_bad_arrays": len(bad_arrays), "bad_arrays": bad_arrays,
            "recovery": dict(store.recovery)}


def stats_report(store: DatasetStore) -> str:
    """Human-readable stats() with the family-balance warning. For `dataset stats` and for the
    one-line summary the CLI prints on every run."""
    s = store.stats()
    lines = [f"records {s['n']} (ok {s['n_ok']}, failed {s['n_failed']}), shards {s['n_shards']}, "
             f"{s['disk_mb']:.1f} MB",
             f"families {s['family_balance']}",
             f"missing families {s['missing_families'] or 'none'}, "
             f"duplicate designs {s['n_duplicate_designs']}",
             f"backends {s['by_backend']}  lib_sha {s['by_lib_sha']}",
             f"traces {100.0 * s['trace_fraction']:.1f}% of records, "
             f"gpu solve seconds {s['total_gpu_seconds']:.1f}",
             f"dates {s['date_first']} .. {s['date_last']}"]
    if s["family_warning"]:
        lines.append("WARNING: " + s["family_warning"])
    if store.recovery:
        lines.append(f"recovered on open: {store.recovery}")
    return "\n".join(lines)


def export_training_npz(store: DatasetStore, out: Path, **kwargs) -> dict:
    """Write to_training_arrays(store, **kwargs) as a compressed .npz and return the dict.
    Flat keys: X, key_names, freqs_hz, design_hash, family, ok, di_source, y_metrics/<name>,
    y_scalars/<name>, excitation/<name>, and meta_json. For `dataset export --out train.npz
    [--family F] [--lib-sha S]`."""
    d = to_training_arrays(store, **kwargs)
    flat = {"X": d["X"], "key_names": np.array(d["key_names"], dtype=str),
            "freqs_hz": d["freqs_hz"], "design_hash": d["design_hash"], "family": d["family"],
            "ok": d["ok"], "di_source": d["di_source"],
            "meta_json": np.array(dumps_strict(to_jsonable(d["meta"])))}
    for grp in ("y_metrics", "y_scalars", "excitation"):
        for k, v in d[grp].items():
            flat[f"{grp}/{k}"] = v
    out = Path(out)
    tmp = out.with_name(out.name + ".tmp")
    with open(tmp, "wb") as f:
        np.savez_compressed(f, **flat)
    os.replace(tmp, out)
    return d
