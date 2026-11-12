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
import re
import sys
from pathlib import Path

# Runnable as a plain script (tools/data/<this file>): locate the repo root from the file
# location, not the current working directory, as the other tools do.
REPO_ROOT = Path(__file__).resolve().parents[2]

_SHARD_RE = re.compile(r"^shard-(\d+)\.jsonl$")

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
    parser.add_argument("--quiet", action="store_true",
                        help="do not print the human summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    doc = run(dataset=_resolve(args.dataset), out=_resolve(args.out))
    if args.json:
        _write_summary(_resolve(args.json), doc)
    if not args.quiet:
        for line in _summary_lines(doc):
            print(line)
    return 1 if doc["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
