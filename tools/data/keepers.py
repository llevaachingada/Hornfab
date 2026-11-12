"""Derived, regenerable "keepers" index over the append-only dataset store.

Phase 4 of ``docs/DATA_CONSOLIDATION_PLAN_2026-10-29.md``: a curated good-horns view made
**without deleting the bad tail**. This tool never writes, moves or deletes anything under
``dataset/shard-*.jsonl``; it only reads the shards once and writes a CSV view (by default to
``dataset/views/keepers.csv``, which is gitignored through ``/dataset/``) plus an optional JSON
summary requested with ``--json PATH``.

Rows and keys
-------------
One row per ``(design_hash, solve_hash)`` pair. The store is append-only and re-evaluations can
append the same pair more than once; the **first occurrence wins** and the number of extra rows
collapsed is reported. Rows are emitted in dataset order (shards sorted by name, lines in file
order), so the output is deterministic for a given input.

``target_key`` is a stable 12-hex sha256 of the record's ``target`` block (JSON, sorted keys,
compact separators). Dataset records do **not** carry a brief hash (known gap R8), so this is the
closest thing to a brief identity that exists today; it is a derived value, not a new contract.
``brief_label`` is ``target.name`` when present, else ``""`` (the current store has no names, so
real rows carry ``""``).

``typology`` is the record's ``family`` plus ``+grid`` / ``+cad`` when ``params`` carries those
keys. It is a cheap discriminator, not a new taxonomy.

Best flags
----------
* ``is_best_in_target`` = 1 for the lowest ``objective`` among ``ok`` rows sharing
  ``(target_key, family)``.
* ``is_best_in_family`` = 1 for the lowest ``objective`` among ``ok`` rows sharing ``family``.

Ties: **every** tied row is flagged (objective equality on the stored float). Failed rows
(``ok: false``) and rows without a finite numeric objective can never win. ``1`` is a row that
wins its group; ``0`` is every other row.

``dof_class``
-------------
``n_dof`` is read from ``mesh.n_dof`` (falling back to ``solve.n_dof``) and bucketed as
``<=6k`` (n <= 6000), ``<=10k`` (n <= 10000), ``<=14k`` (n <= 14000) or ``>14k``; it is ``""``
when the record carries no ``n_dof`` (as failed records do).

``gates`` is ``unavailable`` on every row
-----------------------------------------
``tools/rescore/gate_audit.py`` holds the canonical gate logic, but every gate function
(``gate_h``, ``gate_v``, ``gate_di_rise``, ``gate_bw8k``, ``gate_loading``) needs the
per-frequency arrays stored in a run's ``metrics`` block (``freqs_hz``, ``bw_h_deg``,
``bw_v_deg``, ``di_db``, ``z_throat_real``); the throat gate additionally needs the solved mesh.
Dataset records keep only ``metrics_scalars`` (means/mins, no arrays) and there is no run
directory or ndjson row to read them from. ``gate_audit`` therefore exposes no function that can
compute a per-record verdict from ``metrics_scalars`` + ``target`` alone, and this tool does not
invent one: emitting derived booleans from scalar means would not be the canonical gates. The
honest value is the literal string ``unavailable``.

Usage (from the repo root)::

    .venv\\Scripts\\python.exe tools/data/keepers.py
    .venv\\Scripts\\python.exe tools/data/keepers.py --out dataset/views/keepers.csv
    .venv\\Scripts\\python.exe tools/data/keepers.py --json scratch/keepers.json --quiet
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import sys
from pathlib import Path

# Runnable as a plain script (tools/data/<this file>): locate the repo root from the file
# location, not the current working directory, as the other tools do.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_SHARD_RE = re.compile(r"^shard-(\d+)\.jsonl$")

#: Swarm lane H: optional record provenance fields. Backfilled only when absent; existing values
#: always win, and a missing join value never writes a null/empty string.
BACKFILL_FIELDS = ("run_id", "config_name", "typology")

FIELDS = (
    "design_hash",
    "solve_hash",
    "mesh_hash",
    "family",
    "objective",
    "ok",
    "created_utc",
    "n_dof",
    "dof_class",
    "target_key",
    "brief_label",
    "typology",
    "is_best_in_target",
    "is_best_in_family",
    "gates",
)

GATES_UNAVAILABLE = "unavailable"


def _resolve(path: str | Path) -> Path:
    """A CLI path: absolute stays absolute, relative is resolved from the repo root."""
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _objective(record: dict) -> float | None:
    return _finite_number(record.get("objective"))


def _n_dof(record: dict) -> int | None:
    for block_name in ("mesh", "solve"):
        block = record.get(block_name)
        if not isinstance(block, dict):
            continue
        value = _finite_number(block.get("n_dof"))
        if value is not None:
            return int(value)
    return None


def dof_class(n_dof: int | None) -> str:
    """Bucket a dof count; ``""`` when absent."""
    if n_dof is None:
        return ""
    if n_dof <= 6000:
        return "<=6k"
    if n_dof <= 10000:
        return "<=10k"
    if n_dof <= 14000:
        return "<=14k"
    return ">14k"


def target_key(target: object) -> str:
    """Stable 12-hex sha256 of a ``target`` block (JSON, sorted keys, compact)."""
    canonical = json.dumps(target, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def _brief_label(record: dict) -> str:
    target = record.get("target")
    if not isinstance(target, dict):
        return ""
    return _text(target.get("name"))


def _typology(record: dict) -> str:
    family = _text(record.get("family"))
    params = record.get("params")
    suffix = ""
    if isinstance(params, dict):
        if params.get("grid") is not None:
            suffix += "+grid"
        if params.get("cad") is not None:
            suffix += "+cad"
    return family + suffix


def read_records(dataset: Path) -> tuple[list[dict], list[str]]:
    """Parse every ``shard-*.jsonl`` under ``dataset`` exactly once. Never raises."""
    records: list[dict] = []
    errors: list[str] = []
    try:
        shard_files = sorted(
            p for p in dataset.glob("shard-*.jsonl")
            if p.is_file() and _SHARD_RE.match(p.name)
        )
    except OSError as exc:
        return records, [f"cannot list shards in {dataset}: {exc}"]

    for shard_path in shard_files:
        try:
            handle = open(shard_path, "r", encoding="utf-8")
        except OSError as exc:
            errors.append(f"cannot read {shard_path}: {exc}")
            continue
        with handle:
            line_no = 0
            try:
                for raw in handle:
                    if not raw.strip():
                        continue
                    line_no += 1
                    try:
                        record = json.loads(raw)
                    except ValueError as exc:
                        errors.append(f"malformed JSON in {shard_path} line {line_no}: {exc}")
                        continue
                    if not isinstance(record, dict):
                        errors.append(f"non-object JSON in {shard_path} line {line_no}")
                        continue
                    records.append(record)
            except OSError as exc:
                errors.append(f"error reading {shard_path}: {exc}")
    return records, errors


def build_rows(records: list[dict]) -> tuple[list[dict], int]:
    """Dedupe on ``(design_hash, solve_hash)`` (first wins) and build the CSV rows.

    Returns ``(rows, collapsed_extras)``. Best-in-target / best-in-family flags are set per
    the module docstring (ties all win; failed rows never win).
    """
    seen: set[tuple[object, object]] = set()
    unique: list[dict] = []
    collapsed = 0
    for record in records:
        pair = (record.get("design_hash"), record.get("solve_hash"))
        if pair in seen:
            collapsed += 1
            continue
        seen.add(pair)
        unique.append(record)

    rows: list[dict] = []
    target_groups: dict[tuple[str, str], list[tuple[float, dict]]] = {}
    family_groups: dict[str, list[tuple[float, dict]]] = {}

    for record in unique:
        n_dof = _n_dof(record)
        row = {
            "design_hash": _text(record.get("design_hash")),
            "solve_hash": _text(record.get("solve_hash")),
            "mesh_hash": _text(record.get("mesh_hash")),
            "family": _text(record.get("family")),
            "objective": record.get("objective"),
            "ok": 1 if record.get("ok") else 0,
            "created_utc": _text(record.get("created_utc")),
            "n_dof": "" if n_dof is None else n_dof,
            "dof_class": dof_class(n_dof),
            "target_key": target_key(record.get("target")),
            "brief_label": _brief_label(record),
            "typology": _typology(record),
            "is_best_in_target": 0,
            "is_best_in_family": 0,
            "gates": GATES_UNAVAILABLE,
        }
        rows.append(row)

        if not record.get("ok"):
            continue
        objective = _objective(record)
        if objective is None:
            continue
        target_groups.setdefault((row["target_key"], row["family"]), []).append(
            (objective, row)
        )
        family_groups.setdefault(row["family"], []).append((objective, row))

    target_best = {key: min(j for j, _row in group) for key, group in target_groups.items()}
    family_best = {key: min(j for j, _row in group) for key, group in family_groups.items()}

    for key, group in target_groups.items():
        best = target_best[key]
        for objective, row in group:
            if objective == best:
                row["is_best_in_target"] = 1

    for key, group in family_groups.items():
        best = family_best[key]
        for objective, row in group:
            if objective == best:
                row["is_best_in_family"] = 1

    return rows, collapsed


def _cell(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _cell(row.get(field)) for field in FIELDS})


def run(*, dataset: Path, out: Path) -> dict:
    """Read the shards once, write the CSV view and return the summary document."""
    records, errors = read_records(dataset)
    rows, collapsed = build_rows(records)
    write_csv(out, rows)

    ok_rows = sum(1 for row in rows if row["ok"])
    return {
        "dataset": str(dataset),
        "out": str(out),
        "records_read": len(records),
        "unique_rows": len(rows),
        "collapsed_extras": collapsed,
        "ok_records": sum(1 for record in records if record.get("ok")),
        "failed_records": sum(1 for record in records if not record.get("ok")),
        "ok_rows": ok_rows,
        "failed_rows": len(rows) - ok_rows,
        "distinct_families": len({row["family"] for row in rows}),
        "distinct_target_keys": len({row["target_key"] for row in rows}),
        "best_in_target_rows": sum(1 for row in rows if row["is_best_in_target"]),
        "best_in_family_rows": sum(1 for row in rows if row["is_best_in_family"]),
        "gate_mode": GATES_UNAVAILABLE,
        "errors": errors,
    }


# ------------------------------------------------------------------ lane H backfill
#
# Old records (schema v1, written before 2026-11-12) lack the optional top-level run_id /
# config_name / typology fields. Join them back from the run tree that produced them:
#
#   runs/<run_id>/search.ndjson   row (design_hash, solve_hash) -> generator block / family
#   runs/<run_id>/config.yaml     name: -> config_name
#
# Dry run by default. ``--apply`` copies every shard it will change into ``--backup`` before
# writing through a temp file + ``os.replace`` (hardlinked copies are never edited in place).
# Existing fields are never overwritten; a join miss leaves the record untouched.

def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _run_config_name(run_dir: Path) -> str | None:
    """``config.yaml`` ``name`` first (the contract the lane spec names), then run.json."""
    config_yaml = run_dir / "config.yaml"
    if config_yaml.is_file():
        try:
            import yaml
            data = yaml.safe_load(config_yaml.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001 - a bad run snapshot must not stop the backfill
            data = {}
        if isinstance(data, dict) and data.get("name"):
            return str(data["name"])
    run_json = _read_json(run_dir / "run.json")
    if run_json.get("config_name"):
        return str(run_json["config_name"])
    config = run_json.get("config")
    if isinstance(config, dict) and config.get("name"):
        return str(config["name"])
    return None


def _row_typology(row: dict) -> str:
    from hornlab_search.dataset.record import typology_name
    return typology_name(row.get("generator"), row.get("family"))


def run_index(runs_root: Path) -> tuple[dict[tuple[str, str], dict], int]:
    """Map ``(design_hash, solve_hash)`` to the provenance values of the first run that saw it.

    Returns ``(index, duplicate_hits)``. Runs are read in sorted directory order, so the result
    is deterministic; a later duplicate is counted, not allowed to overwrite the first.
    """
    index: dict[tuple[str, str], dict] = {}
    duplicates = 0
    try:
        run_dirs = sorted(p for p in runs_root.iterdir() if p.is_dir())
    except OSError:
        return index, duplicates
    for run_dir in run_dirs:
        ndjson = run_dir / "search.ndjson"
        if not ndjson.is_file():
            continue
        config_name = _run_config_name(run_dir)
        run_id = run_dir.name
        try:
            lines = ndjson.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if not isinstance(row, dict):
                continue
            design_hash, solve_hash = row.get("design_hash"), row.get("solve_hash")
            if not design_hash or not solve_hash:
                continue
            key = (str(design_hash), str(solve_hash))
            if key in index:
                duplicates += 1
                continue
            index[key] = {
                "run_id": run_id,
                "config_name": config_name,
                "typology": _row_typology(row),
            }
    return index, duplicates


def _backfill_record(record: dict, entry: dict) -> dict[str, str]:
    """Add only absent, non-empty fields. Returns the fields actually written."""
    added: dict[str, str] = {}
    for field in BACKFILL_FIELDS:
        if field in record:
            continue
        value = entry.get(field)
        if value:
            record[field] = str(value)
            added[field] = str(value)
    return added


def plan_backfill(dataset_root: Path, runs_root: Path) -> tuple[dict[Path, tuple[str, int, int]], dict]:
    """Build the rewrite plan without touching disk.

    Returns ``({shard: (new_text, changed_rows, added_fields)}, stats)``.
    """
    index, duplicates = run_index(runs_root)
    plan: dict[Path, tuple[str, int, int]] = {}
    shards = 0
    rows_seen = 0
    rows_changed = 0
    fields_added = 0
    rows_joined = 0
    try:
        shard_files = sorted(
            p for p in dataset_root.glob("shard-*.jsonl")
            if p.is_file() and _SHARD_RE.match(p.name)
        )
    except OSError:
        shard_files = []
    for shard in shard_files:
        shards += 1
        try:
            text = shard.read_text(encoding="utf-8")
        except OSError:
            continue
        lines = text.splitlines(keepends=True)
        out_lines: list[str] = []
        changed_rows = 0
        added_fields = 0
        for line in lines:
            raw = line.rstrip("\r\n")
            eol = line[len(raw):]
            if not raw.strip():
                out_lines.append(line)
                continue
            try:
                record = json.loads(raw)
            except ValueError:
                out_lines.append(line)
                continue
            rows_seen += 1
            if not isinstance(record, dict):
                out_lines.append(line)
                continue
            key = (str(record.get("design_hash") or ""), str(record.get("solve_hash") or ""))
            entry = index.get(key)
            if entry is None:
                out_lines.append(line)
                continue
            rows_joined += 1
            added = _backfill_record(record, entry)
            if not added:
                out_lines.append(line)
                continue
            out_lines.append(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + eol)
            changed_rows += 1
            added_fields += len(added)
        if changed_rows:
            plan[shard] = ("".join(out_lines), changed_rows, added_fields)
            rows_changed += changed_rows
            fields_added += added_fields
    stats = {
        "runs_indexed": len(index),
        "duplicate_run_hits": duplicates,
        "shards_read": shards,
        "rows_seen": rows_seen,
        "rows_joined": rows_joined,
        "rows_changed": rows_changed,
        "fields_added": fields_added,
    }
    return plan, stats


def _write_shard(path: Path, text: str, backup_root: Path, dataset_root: Path) -> None:
    try:
        rel = path.resolve().relative_to(dataset_root.resolve())
    except ValueError:
        rel = Path(path.name)
    dest = backup_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(path, dest)
    tmp = path.with_name(path.name + ".lane_h.tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    os.replace(tmp, path)


def _backfill_lines(stats: dict, plan: dict[Path, tuple[str, int, int]]) -> list[str]:
    return [
        "keepers backfill: optional run_id / config_name / typology (dry run by default)",
        f"  run rows indexed : {stats['runs_indexed']} "
        f"(duplicate (design, solve) hits skipped: {stats['duplicate_run_hits']})",
        f"  dataset rows     : {stats['rows_seen']} (joined {stats['rows_joined']})",
        f"  rows to change   : {stats['rows_changed']} in {len(plan)} shard(s)",
        f"  fields to add    : {stats['fields_added']}",
    ]


def _summary_lines(doc: dict) -> list[str]:
    return [
        "keepers: curated derived view of dataset records (dataset is read-only)",
        f"  records read     : {doc['records_read']}",
        f"  unique rows      : {doc['unique_rows']} "
        f"(collapsed {doc['collapsed_extras']} extra duplicate pair row(s))",
        f"  ok / failed      : {doc['ok_records']} / {doc['failed_records']}",
        f"  families         : {doc['distinct_families']}",
        f"  target keys      : {doc['distinct_target_keys']}",
        f"  best in target   : {doc['best_in_target_rows']} row(s)",
        f"  best in family   : {doc['best_in_family_rows']} row(s)",
        f"  gates            : {doc['gate_mode']} (see module docstring)",
        f"  output           : {doc['out']}",
    ]


def _write_summary(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="keepers.py",
        description="Write a derived one-row-per-(design, solve) view of the dataset "
                    "(read-only on the dataset; the CSV is regenerable).",
    )
    parser.add_argument("--dataset", default="dataset",
                        help="dataset root holding shard-*.jsonl (default: dataset)")
    parser.add_argument("--out", default="dataset/views/keepers.csv",
                        help="CSV output path (default: dataset/views/keepers.csv)")
    parser.add_argument("--json", default=None,
                        help="write the summary as JSON to this path (default: none)")
    parser.add_argument("--backfill", action="store_true",
                        help="lane H: backfill run_id/config_name/typology from runs/*/search.ndjson "
                             "+ config.yaml (dry run unless --apply)")
    parser.add_argument("--runs", default="runs",
                        help="run tree to join when --backfill (default: runs)")
    parser.add_argument("--apply", action="store_true",
                        help="with --backfill, write the changes (default: dry run)")
    parser.add_argument("--backup", default=None,
                        help="with --backfill --apply, backup root "
                             "(default: <dataset>/_backup_backfill_run_fields)")
    parser.add_argument("--quiet", action="store_true",
                        help="do not print the human summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.backfill:
        dataset = _resolve(args.dataset)
        runs = _resolve(args.runs)
        plan, stats = plan_backfill(dataset, runs)
        if not args.quiet:
            for line in _backfill_lines(stats, plan):
                print(line)
            for shard, (_text, rows, fields) in plan.items():
                print(f"  {shard}: {rows} row(s), {fields} field(s)")
        if not args.apply:
            print("dry run: nothing written (pass --apply)")
            return 0
        backup = _resolve(args.backup) if args.backup else dataset / "_backup_backfill_run_fields"
        for shard, (text, _rows, _fields) in plan.items():
            _write_shard(shard, text, backup, dataset)
        print(f"applied; originals in {backup}")
        return 0
    doc = run(dataset=_resolve(args.dataset), out=_resolve(args.out))
    if args.json:
        _write_summary(_resolve(args.json), doc)
    if not args.quiet:
        for line in _summary_lines(doc):
            print(line)
    return 1 if doc["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
