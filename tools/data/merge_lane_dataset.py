"""Merge the CPU lane's dataset into the main dataset, gated on the lane-parity report (D.3).

Why: the two-lane night writes its CPU-backend records to ``dataset_cpu`` so the two backends
never mix silently; once the A.7 parity check (``tools/analysis/lane_parity.py``, CP-7b:
>= 3 shared designs agree within 0.2 dB) says PASS, those rows belong in ``dataset/``.

What this tool does:

  .venv\\Scripts\\python.exe tools\\data\\merge_lane_dataset.py --src dataset_cpu --dst dataset \\
      --parity runs\\analysis\\lane_parity_2026-11-12.json            # dry run (default)
  ... --apply

* DRY RUN BY DEFAULT: prints what would merge, writes nothing.
* GATE: rows merge ONLY when the parity report says PASS (A.7's ``"pass": true``; a
  ``verdict``/``status``/``result`` field holding "pass"/"passed" is accepted so the gate
  survives minor schema drift). A FAIL/unrecognised report refuses the merge loudly.
* SELECTION: only CPU-lane records (``solve.backend == "beat_cpu"``) from the source's
  ``shard-*.jsonl``, tag each merged row ``provenance.lane = "cpu"`` (existing ``provenance``
  keys are preserved). Rows already present in the destination (same
  ``design_hash``/``mesh_hash``/``solve_hash``/``objective_version``/``solve.mode``) are skipped.
* SAFETY: destination rows land in ``<dst>\\shard-lane-cpu.jsonl`` (existing shards are never
  touched). Before a rewrite, the previous target file is copied to ``--backup`` first and the
  new file is written via a temp file + ``os.replace`` (model:
  ``tools/data/renumber_objective_v5_to_v7.py``). A ``lane-merge-manifest.json`` sidecar records
  which parity report authorised the merge.
* IDEMPOTENT: re-running with the same parity after an applied merge writes nothing (all rows
  already present, manifest unchanged).

Exit codes: 0 ok (including a clean no-op), 1 nothing merged (gate refuses), 2 bad input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

LANE_TAG = "cpu"
SOURCE_BACKEND = "beat_cpu"
LANE_SHARD_NAME = "shard-lane-cpu.jsonl"
MANIFEST_NAME = "lane-merge-manifest.json"

_PASS_WORDS = {"pass", "passed"}


# ------------------------------------------------------------------ parity gate


def parity_verdict(report: dict) -> tuple[bool, str]:
    """``(passed, reason)`` from an A.7 lane_parity report.

    The A.7 schema's gate field is the top-level boolean ``pass``; report variants carrying an
    equivalent ``verdict``/``status``/``result`` string are accepted case-insensitively. Anything
    else is "unrecognised" -> the merge must refuse (fail closed).
    """
    value = report.get("pass")
    if isinstance(value, bool):
        return value, "pass field is true" if value else "pass field is false"
    for key in ("verdict", "status", "result"):
        text = str(report.get(key, "")).strip().lower()
        if text in _PASS_WORDS:
            return True, f"{key} says pass"
        if text in {"fail", "failed"}:
            return False, f"{key} says fail"
    return False, "report has no recognisable pass/verdict field"


def load_parity(path: Path) -> tuple[dict, bool, str]:
    """Read a parity report; refuse loudly on unreadable/unrecognised input."""
    try:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"cannot read parity report {path}: {exc}")
    except ValueError as exc:
        raise SystemExit(f"parity report {path} is not valid JSON: {exc}")
    if not isinstance(report, dict):
        raise SystemExit(f"parity report {path} must be a JSON object")
    passed, reason = parity_verdict(report)
    return report, passed, reason


# ------------------------------------------------------------------ row selection


def row_key(rec: dict) -> tuple:
    """The identity of one dataset record for merge dedupe."""
    solve = rec.get("solve") or {}
    return (str(rec.get("design_hash") or ""),
            str(rec.get("mesh_hash") or ""),
            str(rec.get("solve_hash") or ""),
            str(rec.get("objective_version") or ""),
            str(solve.get("mode") or str(rec.get("mode") or "")))


def row_backend(rec: dict) -> str | None:
    solve = rec.get("solve")
    backend = solve.get("backend") if isinstance(solve, dict) else None
    return backend or (rec.get("backend") if isinstance(rec.get("backend"), str) else None)


def tag_row(rec: dict) -> dict:
    """A copy of ``rec`` tagged ``provenance.lane = "cpu"`` (existing provenance keys kept)."""
    out = dict(rec)
    provenance = dict(out.get("provenance") or {})
    provenance["lane"] = LANE_TAG
    out["provenance"] = provenance
    return out


def read_rows(path: Path) -> list[tuple[str, dict]]:
    """``[(origin, row)]`` for every readable JSON line; unreadable lines are skipped with a note."""
    rows: list[tuple[str, dict]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            rows.append((path.name, rec))
    return rows


def shards(root: Path) -> list[Path]:
    return sorted(root.glob("shard-*.jsonl"))


def plan_merge(src: Path, dst: Path) -> dict:
    """Compute the merge: rows to tag, rows already present, rows not eligible.  No writes."""
    existing_keys: set[tuple] = set()
    for shard in shards(dst):
        for _, rec in read_rows(shard):
            existing_keys.add(row_key(rec))
    selected: list[tuple[str, dict]] = []
    skipped_not_cpu = 0
    skipped_duplicate = 0
    for shard in shards(src):
        for _, rec in read_rows(shard):
            if row_backend(rec) != SOURCE_BACKEND:
                skipped_not_cpu += 1
                continue
            key = row_key(rec)
            if key in existing_keys:
                skipped_duplicate += 1
                continue
            existing_keys.add(key)
            selected.append((shard.name, tag_row(rec)))
    selected.sort(key=lambda item: (str(item[1].get("created_utc") or ""),
                                    str(item[1].get("design_hash") or ""),
                                    str(item[1].get("solve_hash") or "")))
    return {
        "selected": selected,
        "skipped_not_cpu": skipped_not_cpu,
        "skipped_duplicate": skipped_duplicate,
    }


# ------------------------------------------------------------------ safe writes (renumber model)


def _backup_and_replace(path: Path, text: str, backup_root: Path, repo: Path) -> None:
    """Copy ``path`` to ``backup_root`` first, then write ``text`` via temp file + ``os.replace``."""
    if path.exists():
        dest = backup_root / path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(path, dest)
    tmp = path.with_name(path.name + ".mergelane.tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    os.replace(tmp, path)  # new inode: never modifies an existing file in place


def _manifest(parity_path: Path, passed: bool, reason: str, n_rows_total: int) -> dict:
    """The merge manifest. Deliberately deterministic (no timestamps, no per-run counts): it
    describes the end state of the merge (which parity authorised it, how many rows the lane
    shard holds), so re-running with the same parity + same shard writes nothing."""
    return {
        "schema_version": 1,
        "lane": LANE_TAG,
        "parity_file": str(parity_path),
        "parity_sha256": hashlib.sha256(parity_path.read_bytes()).hexdigest(),
        "parity_pass": passed,
        "parity_reason": reason,
        "n_rows_total": n_rows_total,
    }


def _count_rows(path: Path) -> int:
    """Non-empty lines in ``path`` (0 when the file does not exist)."""
    try:
        return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
                   if line.strip())
    except OSError:
        return 0


def _sync_manifest(dst: Path, manifest: dict) -> bool:
    """Write the manifest when its content changed; True when written."""
    path = dst / MANIFEST_NAME
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        current = None
    if current == manifest:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    _backup_and_replace(path, json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                        dst.parent / f"_backup_merge_lane", dst.parent)
    return True


# ------------------------------------------------------------------ CLI


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--src", type=Path, required=True, help="CPU-lane dataset root (e.g. dataset_cpu)")
    ap.add_argument("--dst", type=Path, required=True, help="main dataset root (e.g. dataset)")
    ap.add_argument("--parity", type=Path, required=True, help="A.7 lane_parity.json report")
    ap.add_argument("--apply", action="store_true", help="write the merge (default: dry run)")
    a = ap.parse_args(argv)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    src, dst = a.src, a.dst
    for label, root in (("src", src), ("dst", dst)):
        if not root.is_dir():
            print(f"error: {label} dataset root {root} does not exist", file=sys.stderr)
            return 2
    if not a.parity.is_file():
        print(f"error: parity report {a.parity} does not exist", file=sys.stderr)
        return 2

    src_shards = shards(src)
    if not src_shards:
        print(f"error: no shard-*.jsonl under {src}", file=sys.stderr)
        return 2

    _, passed, reason = load_parity(a.parity)
    plan_data = plan_merge(src, dst)
    n_src = sum(len(read_rows(s)) for s in src_shards)
    print(f"parity {a.parity}: verdict {'PASS' if passed else 'NOT PASS'} ({reason})")
    print(f"source {src}: {n_src} rows in {len(src_shards)} shard(s)")
    print(f"eligible ({SOURCE_BACKEND}): {len(plan_data['selected'])} new, "
          f"{plan_data['skipped_duplicate']} already present, "
          f"{plan_data['skipped_not_cpu']} not {SOURCE_BACKEND}")
    target = dst / LANE_SHARD_NAME
    print(f"target {target}")

    if not passed:
        if a.apply:
            print("refusing to merge: the parity report does not say PASS", file=sys.stderr)
            return 1
        print("dry run: nothing would merge (gate refuses); nothing written")
        return 0
    if not plan_data["selected"]:
        print("nothing to merge: every eligible row is already present (idempotent no-op)")
        if a.apply:
            _sync_manifest(dst, _manifest(a.parity, passed, reason, _count_rows(target)))
        return 0

    for shard_name, rec in plan_data["selected"][:8]:
        print(f"  would merge row {rec.get('design_hash')} ({rec.get('objective_version')}) "
              f"from {shard_name}")
    if len(plan_data["selected"]) > 8:
        print(f"  ... and {len(plan_data['selected']) - 8} more")
    if not a.apply:
        print("dry run: nothing written (pass --apply)")
        return 0

    existing_text = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
    merged = plan_data["selected"]
    lines = []
    if existing_text.strip():
        # Keep the previously merged rows in order, then append the new ones.
        lines = existing_text.rstrip("\n").split("\n")
    new_lines = [json.dumps(rec, ensure_ascii=False, sort_keys=False)
                 for _, rec in merged]
    text = "\n".join(lines + new_lines) + "\n"
    backup_root = dst.parent / "_backup_merge_lane"
    _backup_and_replace(target, text, backup_root, dst.parent)
    if _sync_manifest(dst, _manifest(a.parity, passed, reason,
                                     len(lines) + len(merged))):
        print(f"manifest {dst / MANIFEST_NAME} updated")
    if lines:
        print(f"applied: {len(merged)} row(s) merged with provenance.lane={LANE_TAG!r}; "
              f"previous shard backed up to {backup_root}")
    else:
        print(f"applied: {len(merged)} row(s) written with provenance.lane={LANE_TAG!r}")
    print(f"applied at {now}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
