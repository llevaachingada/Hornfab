"""Read-only integrity report for hornlab-search's local data stores.

One command that answers the Phase 3 deletion questions and doubles as an ongoing health
check. It never writes, moves, links or deletes anything under ``runs/``, ``cache/``,
``dataset/`` or the ``dataset_backup_*/`` directories; the only optional write is the report
requested with ``--json PATH``.

Sections
--------
1. **Records** - per-shard JSONL line counts, total records, ``ok`` true/false, distinct
   ``(design_hash, solve_hash)`` pairs, and failed records that have no arrays ``.npz``.
2. **Duplicate rows** - groups of ``(design_hash, solve_hash)`` appearing more than once, the
   extra-row count, and a bounded sample.
3. **Traces** - files in ``dataset/traces/`` compared (by basename) with the ``traces`` paths
   referenced by records (a dict with ``path`` or a plain string). Orphans are on disk but
   unreferenced; missing references are referenced but absent.
4. **Unreferenced cache entries** - directory names in ``cache/mesh/`` and ``cache/solve/``
   that no run or dataset record refers to.
5. **Run heavy files not hardlinked** - ``mesh.msh`` and ``response.npz`` whose
   ``st_nlink < 2`` (Phase 1 proves dedupe by making these links).
6. **Backup dirs** - record counts for ``dataset_backup_*/`` and whether each backup's
   ``(design_hash, solve_hash)`` set is a subset of the main dataset.

Cache reference model
---------------------
A cache entry is **referenced** when its directory name equals any of:

* a ``key`` field in ``runs/*/designs/*/mesh_meta.json``;
* a ``key`` field in ``runs/*/designs/*/status.json``;
* a ``key`` field in any row of ``runs/*/search.ndjson``;
* ``f"{design_hash}-{mesh_hash}-{solve_hash}"`` built from a dataset record.

An entry whose name starts with a referenced key followed by ``-`` also counts as referenced;
that is the WP12 mounting suffix (``...-mnt-<12hex>``) and the rear factor
(``...-rear<factor>``). A run design directory is scanned (and so its metadata keys are
collected) subject to ``--limit``; the JSONL searches and the dataset are always read in full.

Findings carry a severity. Missing traces and unreadable inputs are ``ERROR`` (exit code 1);
orphan traces, duplicate rows, unreferenced cache entries, unlinked heavy files and backups
that are not subsets are ``WARN`` (do not affect the exit code).

Usage (from the repo root)::

    .venv\\Scripts\\python.exe tools/data/doctor.py
    .venv\\Scripts\\python.exe tools/data/doctor.py --limit 5
    .venv\\Scripts\\python.exe tools/data/doctor.py --json scratch/doctor.json --quiet
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Runnable as a plain script (tools/data/<this file>): locate the repo root from the file
# location, not the current working directory, as the other tools do.
REPO_ROOT = Path(__file__).resolve().parents[2]

SAMPLE_LIMIT = 20

_SHARD_RE = re.compile(r"^shard-(\d+)\.jsonl$")
_KEY_RE = re.compile(r'"key"\s*:\s*"([^"]*)"')

KIND_MESH = "mesh"
KIND_RESPONSE = "response"

_HEAVY = (
    (KIND_MESH, "mesh.msh"),
    (KIND_RESPONSE, "response.npz"),
)


def _resolve(path: str | os.PathLike[str]) -> Path:
    """A CLI path: absolute stays absolute, relative is resolved from the repo root."""
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def _human_bytes(n: int) -> str:
    value = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024.0 or unit == "TiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024.0
    return f"{n} B"


def _read_json(path: Path) -> dict | None:
    """Parse a JSON object, or None when absent/unreadable/not an object. Never raises."""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def _dir_size(path: Path) -> int:
    """Total size of the files below one directory; unreadable files count as zero."""
    total = 0
    try:
        for root, _dirs, files in os.walk(path):
            for name in files:
                try:
                    total += os.stat(os.path.join(root, name)).st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _trace_name(value: object) -> str | None:
    """The trace basename from a record's ``traces`` field (dict with path, or a string)."""
    if isinstance(value, dict):
        value = value.get("path")
    if not isinstance(value, str) or not value:
        return None
    name = value.replace("\\", "/").rsplit("/", 1)[-1]
    return name or None


def _scan_records(dataset: Path) -> tuple[dict, Counter, set[str], set[str]]:
    """Parse every shard once. Returns (section, pair_counts, dataset_keys, trace_refs)."""
    section: dict = {
        "shards": [],
        "total_records": 0,
        "ok_true": 0,
        "ok_false": 0,
        "failed_without_arrays": 0,
        "distinct_pairs": 0,
        "errors": [],
    }
    pair_counts: Counter = Counter()
    dataset_keys: set[str] = set()
    trace_refs: set[str] = set()

    try:
        shard_files = sorted(p for p in dataset.glob("shard-*.jsonl")
                             if p.is_file() and _SHARD_RE.match(p.name))
    except OSError as exc:
        section["errors"].append(f"cannot list shards in {dataset}: {exc}")
        return section, pair_counts, dataset_keys, trace_refs

    for shard_path in shard_files:
        match = _SHARD_RE.match(shard_path.name)
        shard_index = int(match.group(1)) if match else None
        shard_dir = dataset / f"shard-{shard_index:04d}" if shard_index is not None else None
        lines = 0
        try:
            handle = open(shard_path, "r", encoding="utf-8")
        except OSError as exc:
            section["errors"].append(f"cannot read {shard_path}: {exc}")
            section["shards"].append({"path": str(shard_path), "line_count": 0,
                                      "error": f"{type(exc).__name__}: {exc}"})
            continue
        with handle:
            try:
                for raw in handle:
                    if not raw.strip():
                        continue
                    row_index = lines
                    lines += 1
                    try:
                        record = json.loads(raw)
                    except ValueError as exc:
                        section["errors"].append(
                            f"malformed JSON in {shard_path} line {lines}: {exc}")
                        continue
                    if not isinstance(record, dict):
                        section["errors"].append(
                            f"non-object JSON in {shard_path} line {lines}")
                        continue
                    section["total_records"] += 1
                    if bool(record.get("ok")):
                        section["ok_true"] += 1
                    else:
                        section["ok_false"] += 1
                        if shard_dir is not None:
                            arrays = shard_dir / f"rec-{row_index:04d}.npz"
                            try:
                                present = arrays.is_file()
                            except OSError:
                                present = False
                            if not present:
                                section["failed_without_arrays"] += 1
                        else:
                            section["failed_without_arrays"] += 1

                    design = record.get("design_hash")
                    mesh = record.get("mesh_hash")
                    solve = record.get("solve_hash")
                    if all(isinstance(v, str) and v for v in (design, mesh, solve)):
                        pair_counts[(design, solve)] += 1
                        dataset_keys.add(f"{design}-{mesh}-{solve}")

                    name = _trace_name(record.get("traces"))
                    if name is not None:
                        trace_refs.add(name)
            except OSError as exc:
                section["errors"].append(f"error reading {shard_path}: {exc}")
        section["shards"].append({"path": str(shard_path), "line_count": lines})

    section["distinct_pairs"] = len(pair_counts)
    return section, pair_counts, dataset_keys, trace_refs


def _duplicate_section(pair_counts: Counter) -> dict:
    groups = [(pair, count) for pair, count in pair_counts.items() if count > 1]
    groups.sort(key=lambda item: (-item[1], item[0]))
    extra_rows = sum(count - 1 for _pair, count in groups)
    return {
        "group_count": len(groups),
        "extra_rows": extra_rows,
        "sample": [
            {"pair": "-".join(pair), "count": count}
            for pair, count in groups[:SAMPLE_LIMIT]
        ],
    }


def _scan_traces(dataset: Path, referenced: set[str]) -> dict:
    trace_dir = dataset / "traces"
    on_disk: dict[str, int] = {}
    errors: list[str] = []
    try:
        if trace_dir.is_dir():
            with os.scandir(trace_dir) as iterator:
                for entry in iterator:
                    try:
                        if not entry.is_file(follow_symlinks=True):
                            continue
                        try:
                            size = entry.stat().st_size
                        except OSError:
                            size = 0
                        on_disk[entry.name] = size
                    except OSError as exc:
                        errors.append(f"cannot stat {entry.path}: {exc}")
    except OSError as exc:
        errors.append(f"cannot list {trace_dir}: {exc}")

    orphan_names = sorted(set(on_disk) - referenced)
    missing_names = sorted(referenced - set(on_disk))
    orphan_bytes = sum(on_disk[name] for name in orphan_names)
    return {
        "trace_dir": str(trace_dir),
        "files_on_disk": len(on_disk),
        "referenced_names": len(referenced),
        "orphans": {
            "count": len(orphan_names),
            "bytes": orphan_bytes,
            "sample": [
                {"path": str(trace_dir / name), "bytes": on_disk[name]}
                for name in orphan_names[:SAMPLE_LIMIT]
            ],
        },
        "missing": {
            "count": len(missing_names),
            "sample": missing_names[:SAMPLE_LIMIT],
        },
        "errors": errors,
    }


def _scan_search_keys(runs: Path) -> tuple[set[str], list[str]]:
    """Collect every ``key`` field from ``runs/*/search.ndjson`` (never limited)."""
    keys: set[str] = set()
    errors: list[str] = []
    try:
        run_dirs = sorted(p for p in runs.iterdir() if p.is_dir())
    except OSError as exc:
        if runs.exists():
            errors.append(f"cannot list runs in {runs}: {exc}")
        return keys, errors

    for run_dir in run_dirs:
        search = run_dir / "search.ndjson"
        try:
            if not search.is_file():
                continue
        except OSError as exc:
            errors.append(f"cannot stat {search}: {exc}")
            continue
        try:
            with open(search, "r", encoding="utf-8") as handle:
                for raw in handle:
                    # The key is the first quoted "key" field in the row; extracting it with
                    # a regex avoids decoding the (large) metrics arrays in every line.
                    match = _KEY_RE.search(raw)
                    if match is not None and match.group(1):
                        keys.add(match.group(1))
        except OSError as exc:
            errors.append(f"cannot read {search}: {exc}")
    return keys, errors


def _scan_runs(runs: Path, limit: int | None) -> tuple[set[str], dict, int, list[str]]:
    """Scan run design dirs (metadata keys + heavy-file link state)."""
    keys: set[str] = set()
    heavy = {
        kind: {
            "scanned": 0,
            "linked": 0,
            "not_linked": 0,
            "not_linked_bytes": 0,
            "sample": [],
        }
        for kind, _filename in _HEAVY
    }
    errors: list[str] = []

    design_dirs: list[Path] = []
    try:
        run_dirs = sorted(p for p in runs.iterdir() if p.is_dir())
    except OSError as exc:
        if runs.exists():
            errors.append(f"cannot list runs in {runs}: {exc}")
        run_dirs = []

    for run_dir in run_dirs:
        designs = run_dir / "designs"
        try:
            if not designs.is_dir():
                continue
            design_dirs.extend(sorted(p for p in designs.iterdir() if p.is_dir()))
        except OSError as exc:
            errors.append(f"cannot list {designs}: {exc}")

    if limit is not None:
        design_dirs = design_dirs[:limit]

    for design_dir in design_dirs:
        for meta_name in ("mesh_meta.json", "status.json"):
            doc = _read_json(design_dir / meta_name)
            if doc is not None:
                key = doc.get("key")
                if isinstance(key, str) and key:
                    keys.add(key)

        for kind, filename in _HEAVY:
            path = design_dir / filename
            try:
                stat = os.stat(path)
            except FileNotFoundError:
                continue
            except OSError as exc:
                errors.append(f"cannot stat {path}: {exc}")
                continue
            bucket = heavy[kind]
            bucket["scanned"] += 1
            if stat.st_nlink >= 2:
                bucket["linked"] += 1
            else:
                bucket["not_linked"] += 1
                bucket["not_linked_bytes"] += stat.st_size
                if len(bucket["sample"]) < SAMPLE_LIMIT:
                    bucket["sample"].append(
                        {"path": str(path), "bytes": stat.st_size}
                    )
    return keys, heavy, len(design_dirs), errors


def _cache_prefixes(name: str) -> set[str]:
    """Every ``-``-delimited prefix of a cache entry name, including the full name."""
    parts = name.split("-")
    return {"-".join(parts[:index]) for index in range(1, len(parts) + 1)}


def _scan_cache(store_root: Path, referenced_keys: set[str], label: str) -> dict:
    entries: list[Path] = []
    errors: list[str] = []
    try:
        if store_root.is_dir():
            entries = sorted(p for p in store_root.iterdir() if p.is_dir())
    except OSError as exc:
        errors.append(f"cannot list {store_root}: {exc}")

    referenced = 0
    unreferenced: list[Path] = []
    for entry in entries:
        if _cache_prefixes(entry.name) & referenced_keys:
            referenced += 1
        else:
            unreferenced.append(entry)

    unreferenced_bytes = 0
    sample = []
    for entry in unreferenced:
        size = _dir_size(entry)
        unreferenced_bytes += size
        if len(sample) < SAMPLE_LIMIT:
            sample.append({"path": str(entry), "bytes": size})

    return {
        "store": label,
        "root": str(store_root),
        "entries": len(entries),
        "referenced": referenced,
        "unreferenced": {
            "count": len(unreferenced),
            "bytes": unreferenced_bytes,
            "sample": sample,
        },
        "errors": errors,
    }


def _backup_pairs(backup: Path) -> tuple[int, set[tuple[str, str]], list[str]]:
    records = 0
    pairs: set[tuple[str, str]] = set()
    errors: list[str] = []
    try:
        shard_files = sorted(p for p in backup.glob("shard-*.jsonl")
                             if p.is_file() and _SHARD_RE.match(p.name))
    except OSError as exc:
        return 0, pairs, [f"cannot list {backup}: {exc}"]

    for shard_path in shard_files:
        try:
            with open(shard_path, "r", encoding="utf-8") as handle:
                for raw in handle:
                    if not raw.strip():
                        continue
                    try:
                        record = json.loads(raw)
                    except ValueError:
                        continue
                    if not isinstance(record, dict):
                        continue
                    records += 1
                    design = record.get("design_hash")
                    mesh = record.get("mesh_hash")
                    solve = record.get("solve_hash")
                    if (isinstance(design, str) and design
                            and isinstance(mesh, str) and mesh
                            and isinstance(solve, str) and solve):
                        pairs.add((design, solve))
        except OSError as exc:
            errors.append(f"cannot read {shard_path}: {exc}")
    return records, pairs, errors


def _scan_backups(dataset: Path, main_pairs: set[tuple[str, str]]
                  ) -> tuple[list[dict], list[str]]:
    backups: list[dict] = []
    errors: list[str] = []
    parent = dataset.parent
    try:
        candidates = sorted(p for p in parent.glob("dataset_backup_*") if p.is_dir())
    except OSError as exc:
        errors.append(f"cannot list backups in {parent}: {exc}")
        return backups, errors

    for backup in candidates:
        records, pairs, backup_errors = _backup_pairs(backup)
        errors.extend(backup_errors)
        missing = pairs - main_pairs
        backups.append({
            "path": str(backup),
            "record_count": records,
            "subset": not missing,
            "missing_count": len(missing),
            "missing_sample": ["-".join(pair) for pair in sorted(missing)[:SAMPLE_LIMIT]],
        })
    return backups, errors


def _finding(severity: str, section: str, message: str, sample: list | None = None) -> dict:
    finding: dict = {"severity": severity, "section": section, "message": message}
    if sample:
        finding["sample"] = sample
    return finding


def run(*, runs: Path, cache_mesh: Path, cache_solve: Path, dataset: Path,
        limit: int | None = None) -> dict:
    """Scan every store read-only and return the report document."""
    findings: list[dict] = []

    records, pair_counts, dataset_keys, trace_refs = _scan_records(dataset)
    for message in records["errors"]:
        findings.append(_finding("ERROR", "records", message))
    duplicates = _duplicate_section(pair_counts)
    if duplicates["group_count"]:
        findings.append(_finding(
            "WARN", "duplicates",
            f"{duplicates['group_count']} duplicate (design, solve) groups, "
            f"+{duplicates['extra_rows']} extra rows",
            [f"{item['pair']} x{item['count']}" for item in duplicates["sample"]],
        ))

    traces = _scan_traces(dataset, trace_refs)
    for message in traces["errors"]:
        findings.append(_finding("ERROR", "traces", message))
    if traces["missing"]["count"]:
        findings.append(_finding(
            "ERROR", "traces",
            f"{traces['missing']['count']} referenced trace file(s) missing",
            traces["missing"]["sample"],
        ))
    if traces["orphans"]["count"]:
        findings.append(_finding(
            "WARN", "traces",
            f"{traces['orphans']['count']} orphan trace file(s), "
            f"{_human_bytes(traces['orphans']['bytes'])}",
            [f"{item['path']} ({_human_bytes(item['bytes'])})"
             for item in traces["orphans"]["sample"]],
        ))

    search_keys, search_errors = _scan_search_keys(runs)
    for message in search_errors:
        findings.append(_finding("ERROR", "runs", message))

    run_keys, heavy, design_dirs_scanned, run_errors = _scan_runs(runs, limit)
    for message in run_errors:
        findings.append(_finding("ERROR", "runs", message))

    referenced_keys = dataset_keys | search_keys | run_keys
    cache = {
        "mesh": _scan_cache(cache_mesh, referenced_keys, "mesh"),
        "solve": _scan_cache(cache_solve, referenced_keys, "solve"),
    }
    for label, section in cache.items():
        for message in section["errors"]:
            findings.append(_finding("ERROR", f"cache/{label}", message))
        missed = section["unreferenced"]
        if missed["count"]:
            findings.append(_finding(
                "WARN", f"cache/{label}",
                f"{missed['count']} unreferenced entry(s), "
                f"{_human_bytes(missed['bytes'])}",
                [f"{item['path']} ({_human_bytes(item['bytes'])})"
                 for item in missed["sample"]],
            ))

    for kind, section in heavy.items():
        if section["not_linked"]:
            findings.append(_finding(
                "WARN", f"runs/{kind}",
                f"{section['not_linked']} of {section['scanned']} {kind} file(s) not "
                f"hardlinked, {_human_bytes(section['not_linked_bytes'])}",
                [f"{item['path']} ({_human_bytes(item['bytes'])})"
                 for item in section["sample"]],
            ))

    backups, backup_errors = _scan_backups(dataset, set(pair_counts))
    for message in backup_errors:
        findings.append(_finding("ERROR", "backups", message))
    for backup in backups:
        if backup["missing_count"]:
            findings.append(_finding(
                "WARN", "backups",
                f"{backup['path']} has {backup['missing_count']} pair(s) absent from "
                "the main dataset",
                backup["missing_sample"],
            ))

    now = datetime.now(timezone.utc)
    return {
        "generated_utc": now.isoformat(timespec="seconds"),
        "paths": {
            "runs": str(runs),
            "cache_mesh": str(cache_mesh),
            "cache_solve": str(cache_solve),
            "dataset": str(dataset),
        },
        "limit": limit,
        "records": records,
        "duplicates": duplicates,
        "traces": traces,
        "cache": cache,
        "run_heavy": {
            "design_dirs_scanned": design_dirs_scanned,
            "mesh": heavy[KIND_MESH],
            "response": heavy[KIND_RESPONSE],
        },
        "backups": backups,
        "findings": findings,
    }


def _summary_lines(doc: dict) -> list[str]:
    records = doc["records"]
    duplicates = doc["duplicates"]
    traces = doc["traces"]
    lines = [
        "doctor: hornlab-search local data integrity (read-only)",
        f"  records      : {records['total_records']} records in "
        f"{len(records['shards'])} shards | ok {records['ok_true']} / failed "
        f"{records['ok_false']} | distinct pairs {records['distinct_pairs']} | "
        f"failed w/o arrays {records['failed_without_arrays']}",
        f"  duplicates   : {duplicates['group_count']} groups, "
        f"+{duplicates['extra_rows']} extra rows",
        f"  traces       : {traces['files_on_disk']} on disk, "
        f"{traces['referenced_names']} referenced | orphans "
        f"{traces['orphans']['count']} ({_human_bytes(traces['orphans']['bytes'])}) | "
        f"missing {traces['missing']['count']}",
    ]
    for label in ("mesh", "solve"):
        section = doc["cache"][label]
        missed = section["unreferenced"]
        lines.append(
            f"  cache {label:<6}: {missed['count']} unreferenced of "
            f"{section['entries']} ({_human_bytes(missed['bytes'])})"
        )
    heavy = doc["run_heavy"]
    for kind in ("mesh", "response"):
        section = heavy[kind]
        lines.append(
            f"  run {kind:<8}: {section['not_linked']} not linked of "
            f"{section['scanned']} ({_human_bytes(section['not_linked_bytes'])}), "
            f"{section['linked']} linked"
        )
    for backup in doc["backups"]:
        verdict = "subset" if backup["subset"] else f"MISSING {backup['missing_count']}"
        lines.append(
            f"  backup       : {Path(backup['path']).name} "
            f"{backup['record_count']} records, {verdict}"
        )

    if doc["findings"]:
        lines.append("  findings:")
        for item in doc["findings"]:
            lines.append(f"    [{item['severity']}] {item['section']}: {item['message']}")
            for entry in item.get("sample", []):
                lines.append(f"        {entry}")
    else:
        lines.append("  findings     : none (OK)")

    errors = sum(1 for item in doc["findings"] if item["severity"] == "ERROR")
    warns = sum(1 for item in doc["findings"] if item["severity"] == "WARN")
    verdict = "FAIL" if errors else "OK"
    lines.append(f"  result       : {verdict} ({errors} ERROR, {warns} WARN)")
    return lines


def _write_report(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=False), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doctor.py",
        description="Read-only integrity report for runs/, cache/ and dataset/ "
                    "(exit 1 when an ERROR-severity finding is present).",
    )
    parser.add_argument("--runs", default="runs", help="run store (default: runs)")
    parser.add_argument("--cache-mesh", default="cache/mesh",
                        help="mesh cache root (default: cache/mesh)")
    parser.add_argument("--cache-solve", default="cache/solve",
                        help="solve cache root (default: cache/solve)")
    parser.add_argument("--dataset", default="dataset",
                        help="dataset root (default: dataset)")
    parser.add_argument("--json", default=None,
                        help="write the full report as JSON to this path (default: none)")
    parser.add_argument("--quiet", action="store_true",
                        help="do not print the human summary")
    parser.add_argument("--limit", type=int, default=None,
                        help="cap the number of run design dirs scanned")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit is not None and args.limit < 0:
        raise SystemExit("--limit must be >= 0")

    doc = run(
        runs=_resolve(args.runs),
        cache_mesh=_resolve(args.cache_mesh),
        cache_solve=_resolve(args.cache_solve),
        dataset=_resolve(args.dataset),
        limit=args.limit,
    )
    if args.json:
        _write_report(_resolve(args.json), doc)
    if not args.quiet:
        for line in _summary_lines(doc):
            print(line)
    return 1 if any(item["severity"] == "ERROR" for item in doc["findings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
