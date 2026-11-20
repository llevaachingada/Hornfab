"""Capture a small, portable fixture pack from the system case store.

Read-only over ``--store`` (the ``system_runs`` directory).  For every manifest payload ``kind``
and for ``invalid`` case directories, copy up to ``--per-kind N`` case directories into ``--out``,
preserving their store-relative layout (``system/<experiment>/<case>/...``).

Copy rules:

* only ``*.json`` files are copied by default, and nothing larger than 256 KiB;
* ``.npz`` / ``.msh`` / ``.vtk`` files are never copied unless ``--include-arrays`` is given
  (the size cap still applies);
* bytes are copied verbatim, so the manifests' recorded sha256 values stay valid;
* an existing case is never modified and ``--out`` may not be inside ``--store``.

Selection is deterministic: cases are ordered by ``(experiment, case)`` and the first ``N`` of each
kind are taken.  ``FIXTURE_PROVENANCE.json`` records the source store-relative path and the sha256
of every copied file, the kinds covered and the tool version.  It contains no timestamps, so an
unchanged store produces byte-identical output.

Odd store contents never raise: they are recorded in ``diagnostics`` and skipped.

Usage::

    python tools/system/capture_fixture_cases.py --store system_runs \
        --out tests/system/fixtures/case_store --per-kind 2
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

TOOL = "capture_fixture_cases"
TOOL_VERSION = "1"
SCHEMA_VERSION = 1
PROVENANCE_NAME = "FIXTURE_PROVENANCE.json"

#: Mirrors ``tools/data/system_cases.py``: a case dir starts with a UTC timestamp.
CASE_DIR_RE = re.compile(r"^\d{8}T\d{6}Z")

#: Mirrors ``tools/data/system_cases.py``: path parts that are not study records.
SKIP_PARTS = frozenset({"_fixtures", "__pycache__", ".git"})

#: Never copied unless ``--include-arrays``; still subject to the size cap.
ARRAY_SUFFIXES = frozenset({".npz", ".msh", ".vtk"})

MAX_FILE_BYTES = 256 * 1024


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> tuple[Any, str | None]:
    """``(data, error)``; never raises."""
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}"
    except ValueError as exc:
        return None, f"JSONDecodeError: {exc}"


def _store_rel(path: Path, store: Path) -> str:
    """POSIX-style path relative to the store (never absolute)."""
    return path.relative_to(store).as_posix()


def _inspect_case(case_dir: Path) -> tuple[str | None, str | None]:
    """``(kind, invalid_reason)`` for one case directory; never raises.

    ``invalid_reason`` is set for a missing/unreadable/malformed manifest (the export's
    ``invalid`` status).  A readable manifest without a string ``payload.kind`` is odd but not
    ``invalid``: it yields ``(None, None)`` and the caller records a diagnostic and skips it.
    """
    manifest_path = case_dir / "manifest.json"
    if not manifest_path.is_file():
        return None, "missing manifest.json"
    manifest, error = _read_json(manifest_path)
    if error is not None:
        return None, error
    if not isinstance(manifest, dict):
        return None, "manifest.json is not an object"
    payload = manifest.get("payload")
    if not isinstance(payload, dict):
        return None, "manifest payload missing"
    kind = payload.get("kind")
    if isinstance(kind, str) and kind.strip():
        return kind.strip(), None
    return None, None


def _discover(store: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Ordered case records ``{experiment, case, kind, bucket}`` plus diagnostics."""
    base = store / "system"
    cases: list[dict[str, str]] = []
    diagnostics: list[dict[str, str]] = []
    if not base.is_dir():
        diagnostics.append({"case_key": "", "reason": "store has no system/ directory"})
        return cases, diagnostics

    try:
        experiments = sorted(
            (item for item in base.iterdir() if item.is_dir()), key=lambda item: item.name
        )
    except OSError as exc:
        diagnostics.append({"case_key": "", "reason": f"unreadable system/ directory: {exc}"})
        return cases, diagnostics

    for experiment_dir in experiments:
        if experiment_dir.name in SKIP_PARTS or experiment_dir.name.startswith("_"):
            continue
        try:
            entries = sorted(
                (item for item in experiment_dir.iterdir() if item.is_dir()),
                key=lambda item: item.name,
            )
        except OSError as exc:
            diagnostics.append(
                {"case_key": experiment_dir.name, "reason": f"unreadable experiment dir: {exc}"}
            )
            continue
        for case_dir in entries:
            if not CASE_DIR_RE.match(case_dir.name):
                continue
            case_key = f"{experiment_dir.name}/{case_dir.name}"
            try:
                kind, invalid_reason = _inspect_case(case_dir)
            except Exception as exc:  # noqa: BLE001 - odd store contents must never stop the tool
                diagnostics.append(
                    {"case_key": case_key, "reason": f"unexpected {type(exc).__name__}: {exc}"}
                )
                continue
            if invalid_reason is not None:
                bucket = "invalid"
            elif kind is None:
                diagnostics.append({"case_key": case_key, "reason": "payload kind missing"})
                continue
            else:
                bucket = kind
            cases.append(
                {
                    "experiment": experiment_dir.name,
                    "case": case_dir.name,
                    "case_key": case_key,
                    "kind": kind or "",
                    "bucket": bucket,
                }
            )

    cases.sort(key=lambda item: (item["experiment"], item["case"]))
    return cases, diagnostics


def _select(cases: list[dict[str, str]], per_kind: int) -> list[dict[str, str]]:
    """First ``per_kind`` cases per bucket, in deterministic ``(experiment, case)`` order."""
    selected: list[dict[str, str]] = []
    counts: dict[str, int] = {}
    for case in cases:
        bucket = case["bucket"]
        taken = counts.get(bucket, 0)
        if taken >= per_kind:
            continue
        counts[bucket] = taken + 1
        selected.append(case)
    return selected


def _copy_case(
    case: dict[str, str], store: Path, out: Path, *, include_arrays: bool
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]]]:
    """Copy one case dir; return ``(copied_files, omitted_files, diagnostics)``."""
    source_dir = store / "system" / case["experiment"] / case["case"]
    copied: list[dict[str, Any]] = []
    omitted: list[dict[str, str]] = []
    diagnostics: list[dict[str, str]] = []

    for root, dirs, files in os.walk(source_dir):
        dirs.sort()
        for name in sorted(files):
            source = Path(root) / name
            source_rel = _store_rel(source, store)
            suffix = source.suffix.lower()
            try:
                size = source.stat().st_size
            except OSError as exc:
                diagnostics.append(
                    {"case_key": case["case_key"], "reason": f"cannot stat {source_rel}: {exc}"}
                )
                continue
            if suffix in ARRAY_SUFFIXES and not include_arrays:
                omitted.append({"path": source_rel, "reason": "array_extension"})
                continue
            if suffix != ".json" and not include_arrays:
                omitted.append({"path": source_rel, "reason": "not_json"})
                continue
            if size > MAX_FILE_BYTES:
                omitted.append({"path": source_rel, "reason": "too_large"})
                continue
            try:
                data = source.read_bytes()
            except OSError as exc:
                diagnostics.append(
                    {"case_key": case["case_key"], "reason": f"cannot read {source_rel}: {exc}"}
                )
                continue
            target = out / source.relative_to(store)
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            except OSError as exc:
                diagnostics.append(
                    {"case_key": case["case_key"], "reason": f"cannot write {source_rel}: {exc}"}
                )
                continue
            copied.append(
                {"path": source_rel, "sha256": _sha256_bytes(data), "size_bytes": len(data)}
            )

    return copied, omitted, diagnostics


def _provenance(
    selected: list[dict[str, str]],
    entries: list[dict[str, Any]],
    *,
    per_kind: int,
    include_arrays: bool,
    diagnostics: list[dict[str, str]],
) -> dict[str, Any]:
    kinds = sorted({case["bucket"] for case in selected})
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "tool_version": TOOL_VERSION,
        "per_kind": per_kind,
        "include_arrays": include_arrays,
        "max_file_bytes": MAX_FILE_BYTES,
        "kinds_covered": kinds,
        "cases": entries,
        "diagnostics": sorted(
            diagnostics, key=lambda item: (item.get("case_key") or "", item.get("reason") or "")
        ),
    }


def _is_inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def run(store: Path, out: Path, *, per_kind: int = 2, include_arrays: bool = False) -> int:
    """Capture the fixture pack; return a process exit code."""
    if per_kind < 0:
        print("capture_fixture_cases: --per-kind must be >= 0", file=sys.stderr)
        return 2

    store_path = store.expanduser().resolve()
    out_path = out.expanduser().resolve()
    if _is_inside(out_path, store_path):
        print(
            f"capture_fixture_cases: refusing to write inside --store ({out_path} is under {store_path})",
            file=sys.stderr,
        )
        return 2
    if not store_path.is_dir():
        print(f"capture_fixture_cases: --store is not a directory: {store_path}", file=sys.stderr)
        return 2

    cases, diagnostics = _discover(store_path)
    selected = _select(cases, per_kind)

    entries: list[dict[str, Any]] = []
    for case in selected:
        copied, omitted, case_diagnostics = _copy_case(
            case, store_path, out_path, include_arrays=include_arrays
        )
        diagnostics.extend(case_diagnostics)
        entries.append(
            {
                "case_key": case["case_key"],
                "kind": case["bucket"],
                "source": _store_rel(
                    store_path / "system" / case["experiment"] / case["case"], store_path
                ),
                "files": copied,
                "omitted": omitted,
            }
        )

    provenance = _provenance(
        selected,
        entries,
        per_kind=per_kind,
        include_arrays=include_arrays,
        diagnostics=diagnostics,
    )
    out_path.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(provenance, indent=2, sort_keys=True) + "\n"
    (out_path / PROVENANCE_NAME).write_bytes(payload.encode("utf-8"))

    n_files = sum(len(entry["files"]) for entry in entries)
    print(
        f"capture_fixture_cases: {len(entries)} case dirs, {n_files} files, "
        f"{len(diagnostics)} diagnostics -> {out_path}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="capture_fixture_cases",
        description="Copy a deterministic, small fixture pack out of a read-only system store.",
    )
    parser.add_argument("--store", required=True, type=Path, help="system store (e.g. system_runs)")
    parser.add_argument("--out", required=True, type=Path, help="fixture output directory")
    parser.add_argument(
        "--per-kind",
        type=int,
        default=2,
        metavar="N",
        help="copy the first N case dirs for each payload kind (default: 2)",
    )
    parser.add_argument(
        "--include-arrays",
        action="store_true",
        help="also copy .npz/.msh/.vtk files (still capped at 256 KiB)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args.store, args.out, per_kind=args.per_kind, include_arrays=args.include_arrays)


if __name__ == "__main__":
    raise SystemExit(main())
