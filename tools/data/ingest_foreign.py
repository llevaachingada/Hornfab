"""Ingest foreign rows from another lab: validate, tag, and write a CP-7b parity report.

A lab's pull lands in ``dataset_ext/<lab>/`` (``tools/hf_sync.py pull --lab <name>``). This tool is
the gate those rows must pass before anyone compares or trains on them:

1. Validate every pulled row with ``hornlab_search.dataset.record.validate_record`` (the same
   gatekeeper the local store uses). Malformed lines and rows failing validation are counted and
   reported (first errors each); they are never tagged and never rewritten.
2. Tag every validated row with ``"lab": "<name>"`` (additive field; dry run by default, ``--apply``
   writes through a temp file after backing up each touched shard). The tool REFUSES to operate on
   any path outside ``dataset_ext/`` — and the local ``dataset/`` is read-only on every code path.
3. Parity report: shared designs are rows on both sides with the same ``design_hash`` +
   ``mesh_hash`` + solve spec (backend, mode, frequency grid, GMRES tolerance, observation). For each
   shared pair the stored on-axis responses (``shard-XXXX/rec-NNNN.npz`` → ``on_axis_db``) are
   compared: mean and max absolute SPL difference. Per the CP-7b rule, the labs are comparable ONLY
   after at least 3 shared designs agree within 0.2 dB (max abs over the shared grid); until then
   the report labels the foreign rows a separate group.

Usage (from the repo root)::

    .venv\\Scripts\\python.exe tools\\data\\ingest_foreign.py --lab collin               # dry run
    .venv\\Scripts\\python.exe tools\\data\\ingest_foreign.py --lab collin --apply
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hornlab_search.dataset.record import validate_record  # noqa: E402

#: CP-7b: two labs may be compared only when >= 3 shared designs agree within this SPL distance.
MAX_SPL_DELTA_DB = 0.2
MIN_SHARED_DESIGNS = 3


# ------------------------------------------------------------------ shard scanning

def _shard_files(dataset_root: Path) -> list[Path]:
    try:
        return sorted(dataset_root.glob("shard-*.jsonl"))
    except OSError:
        return []


def _solve_spec_key(record: dict[str, Any]) -> tuple:
    """The solve spec a row was produced under: backend, mode, frequencies, tolerance, observation."""
    solve = record.get("solve")
    solve = solve if isinstance(solve, dict) else {}
    observation = json.dumps(solve.get("observation"), sort_keys=True, default=str)
    freqs = tuple(float(f) for f in (solve.get("freqs_hz") or []))
    gmres_tol = solve.get("gmres_tol")
    return (str(solve.get("backend") or ""), str(solve.get("mode") or ""),
            freqs, gmres_tol, observation)


def _scan_shard(path: Path) -> tuple[list[tuple[int, dict]], list[tuple[int, str]], list[str]]:
    """Parse one shard. Returns (valid, invalid, malformed); line numbers are 1-BASED everywhere:

    ``valid``   (line number, record) pairs for rows that pass validate_record, in line order.
    ``invalid`` (line number, first validation error) for rows validate_record refuses.
    ``malformed`` human-readable notes for torn / non-JSON lines.
    The npz of the ``n``-th valid row of shard ``s`` is ``shard-{s:04d}/rec-{n:04d}.npz``.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [], [], [f"unreadable: {exc}"]
    valid: list[tuple[int, dict]] = []
    invalid: list[tuple[int, str]] = []
    malformed: list[str] = []
    for lineno, line in enumerate(text.splitlines()):
        raw = line.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except ValueError:
            malformed.append(f"line {lineno + 1}: not JSON")
            continue
        if not isinstance(row, dict):
            malformed.append(f"line {lineno + 1}: not an object")
            continue
        try:
            validate_record(row)
        except ValueError as exc:
            invalid.append((lineno + 1, str(exc)))
            continue
        valid.append((lineno + 1, row))
    return valid, invalid, malformed


def _read_rows(path: Path) -> list[dict]:
    return [row for _lineno, row in _scan_shard(path)[0]]


# ------------------------------------------------------------------ read-only local index

def _local_index(dataset_root: Path) -> dict[tuple, list[tuple[str, int]]]:
    """(design_hash, mesh_hash, solve spec) -> [(shard name, npz row no), ...] over the local
    dataset. Read-only."""
    where: dict[tuple, list[tuple[str, int]]] = {}
    for shard in _shard_files(dataset_root):
        for row_no, (_line_no, record) in enumerate(_scan_shard(shard)[0]):
            key = (str(record.get("design_hash")), str(record.get("mesh_hash")),
                   _solve_spec_key(record))
            where.setdefault(key, []).append((shard.name, row_no))
    return where


def _on_axis_npz(dataset_root: Path, shard_name: str, row: int) -> Path:
    return dataset_root / Path(shard_name).stem / f"rec-{row:04d}.npz"


def _load_on_axis(path: Path) -> list[float] | None:
    try:
        import numpy as np
        with np.load(path) as data:
            if "on_axis_db" not in data:
                return None
            return [float(x) for x in data["on_axis_db"].tolist()]
    except (OSError, ValueError, KeyError):
        return None


# ------------------------------------------------------------------ tagging

def _tag_shards(foreign_root: Path, backup_root: Path, lab: str,
                shard_valid: dict[Path, list[int]]) -> None:
    """Rewrite the validated shard lines, adding ``"lab": <lab>`` (never overwriting an existing
    value). Backs up every touched shard once, then writes through a temp file + os.replace."""
    for shard, valid_lines in sorted(shard_valid.items()):
        wanted = set(valid_lines)
        rel = shard.resolve().relative_to(foreign_root.resolve())
        backup = backup_root / rel
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(shard, backup)
        lines = shard.read_text(encoding="utf-8", errors="surrogateescape").splitlines(keepends=True)
        out: list[str] = []
        changed = 0
        for lineno0, line in enumerate(lines):
            raw = line.rstrip("\r\n")
            eol = line[len(raw):]
            if not raw.strip():
                out.append(line)
                continue
            try:
                row = json.loads(raw)
            except ValueError:
                out.append(line)
                continue
            if isinstance(row, dict) and (lineno0 + 1) in wanted:
                row.setdefault("lab", lab)
                out.append(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + eol)
                changed += 1
            else:
                out.append(line)
        if changed:
            tmp = shard.with_name(shard.name + ".ingest_tmp")
            tmp.write_text("".join(out), encoding="utf-8", newline="")
            os.replace(tmp, shard)
            print(f"  tagged {changed} row(s) in {rel}")


# ------------------------------------------------------------------ the report

def report(foreign_root: Path, local_dataset: Path, *, apply: bool, backup_root: Path,
           lab: str) -> dict:
    """Validate + tag the foreign rows and build the parity report.

    The only writes are: row tags (``--apply``, inside ``foreign_root``), one backup per touched
    shard, and ``parity_report.json``. The local dataset is read-only on every path.
    """
    foreign_root = foreign_root.resolve()
    local_dataset = local_dataset.resolve()
    _guard(foreign_root)
    if local_dataset == foreign_root or local_dataset in foreign_root.parents \
            or foreign_root in local_dataset.parents:
        raise SystemExit("local dataset and foreign root must be separate trees")

    local_where = _local_index(local_dataset)
    shards: list[dict] = []
    shard_valid: dict[Path, list[int]] = {}
    valid_rows = 0
    malformed_total = 0
    invalid_total = 0
    invalid_examples: list[str] = []
    shared: list[dict[str, Any]] = []
    common_without_arrays = 0
    foreign_dataset = foreign_root / "dataset" if (foreign_root / "dataset").is_dir() \
        else foreign_root
    for shard in _shard_files(foreign_dataset):
        valid, invalid, malformed = _scan_shard(shard)
        rel = shard.resolve().relative_to(foreign_root.resolve()).as_posix()
        malformed_total += len(malformed)
        invalid_total += len(invalid)
        for lineno, err in invalid[:3]:
            invalid_examples.append(f"{rel} line {lineno}: {err}")
        shards.append({"name": shard.name, "rows_valid": len(valid), "rows_invalid": len(invalid),
                       "malformed_lines": len(malformed)})
        if valid:
            shard_valid[shard] = [lineno for lineno, _row in valid]
        valid_rows += len(valid)
        for row_no, (_lineno, record) in enumerate(valid):
            key = (str(record.get("design_hash")), str(record.get("mesh_hash")),
                   _solve_spec_key(record))
            if key not in local_where:
                continue
            local_shard, local_row = local_where[key][0]
            foreign_cur = _load_on_axis(_on_axis_npz(shard.parent, shard.name, row_no))
            local_cur = _load_on_axis(_on_axis_npz(local_dataset, local_shard, local_row))
            entry: dict[str, Any] = {
                "design_hash": str(record.get("design_hash")),
                "foreign_row": f"{rel}#{row_no}",
                "local_row": f"{local_shard}#{local_row}",
                "spl": None,
            }
            if foreign_cur is None or local_cur is None:
                common_without_arrays += 1
            elif len(foreign_cur) != len(local_cur):
                entry["spl"] = {"error": "on-axis arrays differ in length"}
            else:
                deltas = [abs(f - l) for f, l in zip(foreign_cur, local_cur)]
                entry["spl"] = {"mean_abs_db": round(sum(deltas) / len(deltas), 6),
                                "max_abs_db": round(max(deltas), 6)}
            shared.append(entry)

    to_tag = sum(len(v) for v in shard_valid.values())
    if apply and to_tag:
        _tag_shards(foreign_root, backup_root, lab, shard_valid)

    with_spl = [s for s in shared
                if isinstance(s.get("spl"), dict) and "mean_abs_db" in s["spl"]]  # type: ignore[union-attr]
    agreeing = [s for s in with_spl if s["spl"]["max_abs_db"] <= MAX_SPL_DELTA_DB]  # type: ignore[index]
    comparable = len(agreeing) >= MIN_SHARED_DESIGNS
    return {
        "lab": lab,
        "foreign_root": str(foreign_root),
        "local_dataset": str(local_dataset),
        "applied_tagging": bool(apply),
        "rows_validated": valid_rows,
        "rows_to_tag": to_tag,
        "malformed_lines": malformed_total,
        "invalid_rows": invalid_total,
        "invalid_examples": sorted(invalid_examples),
        "shards": shards,
        "parity": {
            "rule": (f"comparable only after >= {MIN_SHARED_DESIGNS} shared designs agree within "
                     f"{MAX_SPL_DELTA_DB} dB max abs SPL (CP-7b)"),
            "shared_designs": shared,
            "shared_with_spl": len(with_spl),
            "shared_within_threshold_db": len(agreeing),
            "shared_without_spl_arrays": common_without_arrays,
            "comparable": comparable,
            "group": "comparable-with-local" if comparable else "separate-group",
            "threshold_db": MAX_SPL_DELTA_DB,
            "min_shared_designs": MIN_SHARED_DESIGNS,
        },
    }


def _guard(foreign_root: Path) -> None:
    """Foreign data lives only in dataset_ext/<lab>/ — never in dataset/ or elsewhere."""
    parts = {p.lower() for p in foreign_root.parts}
    if "dataset_ext" not in parts:
        raise SystemExit(f"{foreign_root} is not a dataset_ext/<lab>/ directory: foreign rows live "
                         "in dataset_ext/, never in dataset/")


# ------------------------------------------------------------------ CLI

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ingest_foreign.py",
        description="Validate + tag rows pulled from another lab and write a CP-7b parity report "
                    "(foreign data lives in dataset_ext/<lab>/, never in dataset/).")
    parser.add_argument("--lab", required=True, help="lab label written as the rows' 'lab' field")
    parser.add_argument("--from-root", type=Path, default=None,
                        help="pulled tree (default dataset_ext/<lab>/ at the repo root; may point "
                             "at either the <lab>/ dir or its dataset/ dir)")
    parser.add_argument("--dataset", type=Path, default=None,
                        help="local comparator dataset (default <repo>/dataset; read-only)")
    parser.add_argument("--apply", action="store_true", help="tag rows in place (default dry run)")
    parser.add_argument("--backup", type=Path, default=None,
                        help="backup root (default <from-root>/_backup_ingest_lab)")
    parser.add_argument("--report", type=Path, default=None,
                        help="parity report path (default <from-root>/parity_report.json)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    foreign_root = args.from_root or REPO_ROOT / "dataset_ext" / args.lab
    foreign_root = foreign_root / "dataset" if (foreign_root / "dataset").is_dir() else foreign_root
    local_dataset = args.dataset or REPO_ROOT / "dataset"
    backup_root = args.backup or foreign_root / "_backup_ingest_lab"
    doc = report(foreign_root, local_dataset, apply=args.apply, backup_root=backup_root,
                 lab=args.lab)
    report_path = args.report or (foreign_root / "parity_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(doc, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    parity = doc["parity"]
    print(f"ingest_foreign lab={args.lab}: {doc['rows_validated']} valid, {doc['invalid_rows']} "
          f"invalid, {doc['malformed_lines']} malformed "
          f"({'tagged' if args.apply else 'dry run'})")
    print(f"  shared designs: {len(parity['shared_designs'])} "
          f"(with SPL: {parity['shared_with_spl']}, within {parity['threshold_db']} dB: "
          f"{parity['shared_within_threshold_db']})")
    print(f"  group: {parity['group']} ({parity['rule']})")
    print(f"  report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
