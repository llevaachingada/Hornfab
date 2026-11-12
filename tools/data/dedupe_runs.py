"""Replace byte-duplicate heavy run files with hardlinks to their cache entry.

Phase 1 of ``docs/DATA_CONSOLIDATION_PLAN_2026-10-29.md``. For every
``runs/<run>/designs/<hash>/{mesh.msh,response.npz}`` this tool finds the cache entry that
already holds the same bytes and, only when the sha256 digests are equal, replaces the run file
with a hardlink to that cache file. Nothing is ever written or deleted under ``cache/`` and no
run file is ever deleted.

The mapping is read from the files the pipeline already writes:

* mesh: the sibling ``mesh_meta.json`` field ``key`` -> ``<cache-mesh>/<key>/mesh.msh``;
* solve: the sibling ``status.json`` field ``key`` -> ``<cache-solve>/<key>/response.npz``.
  ``status.json`` stores the key WITHOUT the WP12 mounting suffix, while the cache entry may
  carry ``-mnt-<12hex>``; the tool therefore also tries every cache entry whose name starts with
  ``base + "-"``.

When the metadata is missing or unreadable the tool falls back to the cache entries named
``design_hash + "-..."`` (from the sibling ``design.json`` field ``design_hash``) and accepts a
candidate only if its sha256 equals the run file's. Size equality is never sufficient.

Cache directory names are indexed once per cache root (a sorted ``os.scandir`` list) and resolved
with ``bisect``; a per-run sha256 memo means a cache file shared by several run dirs is hashed
only once.

Hardlinks need no elevation on NTFS. ``os.link`` + ``os.replace`` is used so an existing link is
never written through; when linking fails (unsupported filesystem, cross-volume) the tool copies
to a temp name and replaces, recording ``copy-fallback``, or records the error and continues.
One failed file never aborts the run. ``--apply`` is therefore safely re-runnable.

Dry-run is the DEFAULT: nothing changes without ``--apply``. A manifest is written in both
modes, with ``"action": "would-link"`` in dry-run and ``"action": "linked"`` when applied.

Usage (from the repo root)::

    .venv\\Scripts\\python.exe tools/data/dedupe_runs.py
    .venv\\Scripts\\python.exe tools/data/dedupe_runs.py --apply
    .venv\\Scripts\\python.exe tools/data/dedupe_runs.py --limit 5 --apply
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import os
import shutil
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Runnable as a plain script (tools/data/<this file>): locate the repo root the same way the other
# tools do, from the file location rather than the current working directory.
REPO_ROOT = Path(__file__).resolve().parents[2]

MESH_FILE = "mesh.msh"
MESH_META = "mesh_meta.json"
RESPONSE_FILE = "response.npz"
STATUS_FILE = "status.json"
DESIGN_FILE = "design.json"

KIND_MESH = "mesh"
KIND_SOLVE = "solve"

_METADATA = {
    KIND_MESH: (MESH_META, "key", MESH_FILE),
    KIND_SOLVE: (STATUS_FILE, "key", RESPONSE_FILE),
}

_CHUNK = 1024 * 1024


def _resolve(path: str | os.PathLike[str]) -> Path:
    """A CLI path: absolute stays absolute, relative is resolved from the repo root."""
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def _read_json(path: Path) -> dict | None:
    """Parse a JSON object, or None when absent/unreadable/not an object."""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def _read_field(path: Path, field: str) -> str | None:
    doc = _read_json(path)
    if doc is None:
        return None
    value = doc.get(field)
    return value if isinstance(value, str) and value else None


def sha256_file(path: Path) -> str:
    """Streaming sha256 of one file (heavy meshes are hundreds of MB)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def _design_hash(design_dir: Path) -> str | None:
    return _read_field(design_dir / DESIGN_FILE, "design_hash")


class _CacheIndex:
    """Sorted directory-name index for one cache root, scanned at most once per run.

    ``glob`` re-reads the whole cache directory on every call, which is quadratic when one
    index serves tens of thousands of run files. Names are scanned once and matched by
    ``bisect`` instead.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self._names: list[str] | None = None

    def names(self) -> list[str]:
        if self._names is None:
            try:
                found = [entry.name for entry in os.scandir(self.root) if entry.is_dir()]
            except OSError:
                found = []
            found.sort()
            self._names = found
        return self._names

    def contains(self, name: str) -> bool:
        names = self.names()
        pos = bisect.bisect_left(names, name)
        return pos < len(names) and names[pos] == name

    def with_prefix(self, prefix: str) -> list[str]:
        """Names in the contiguous range ``prefix`` .. ``prefix[:-1] + ";"``.

        For ``prefix == key + "-"`` this is exactly the ``key + "-*"`` prefix match, without the
        ``abcd``-for-``abc`` near-miss a naive range would include.
        """
        names = self.names()
        upper = prefix[:-1] + ";"
        lo = bisect.bisect_left(names, prefix)
        hi = bisect.bisect_right(names, upper)
        return [name for name in names[lo:hi] if name.startswith(prefix)]


def _sha_key(path: Path) -> str:
    try:
        return os.path.normcase(str(path.resolve()))
    except OSError:
        return os.path.normcase(str(path))


def _sha256_cached(path: Path, memo: dict[str, str] | None) -> str:
    """sha256 of a cache file, memoised by resolved path for the whole run."""
    if memo is None:
        return sha256_file(path)
    key = _sha_key(path)
    try:
        return memo[key]
    except KeyError:
        digest = sha256_file(path)
        memo[key] = digest
        return digest


def _candidates(design_dir: Path, kind: str, cache_root: Path,
                design_hash: str | None, *, index: _CacheIndex | None = None
                ) -> tuple[list[Path], bool]:
    """Existing candidate cache files for one run file, metadata route first.

    Returns ``(candidates, have_metadata)``. ``have_metadata`` is False only when neither the
    pipeline metadata key nor the design hash is available, which is the ``no metadata`` case.
    """
    meta_name, meta_field, filename = _METADATA[kind]
    key = _read_field(design_dir / meta_name, meta_field)
    if design_hash is None:
        design_hash = _design_hash(design_dir)
    if index is None:
        index = _CacheIndex(cache_root)

    raw: list[Path] = []
    if key:
        if index.contains(key):
            raw.append(cache_root / key / filename)
        if kind == KIND_SOLVE:
            # status.json omits the WP12 mounting suffix; the cache entry may carry it.
            for name in index.with_prefix(key + "-"):
                raw.append(cache_root / name / filename)
    if design_hash:
        for name in index.with_prefix(design_hash + "-"):
            raw.append(cache_root / name / filename)

    seen: set[str] = set()
    existing: list[Path] = []
    for candidate in raw:
        try:
            marker = os.path.normcase(str(candidate.resolve()))
        except OSError:
            marker = os.path.normcase(str(candidate))
        if marker in seen:
            continue
        seen.add(marker)
        if candidate.is_file():
            existing.append(candidate)
    return existing, bool(key or design_hash)


def find_candidate(design_dir: Path, run_file: Path, kind: str, cache_root: Path, *,
                   index: _CacheIndex | None = None,
                   sha_memo: dict[str, str] | None = None
                   ) -> tuple[Path | None, str]:
    """The cache file whose sha256 equals ``run_file``'s, or ``(None, reason)``.

    ``reason`` is one of ``"no metadata"``, ``"no candidate"``, ``"sha mismatch"``.
    """
    candidates, have_metadata = _candidates(design_dir, kind, cache_root, None, index=index)
    if not have_metadata:
        return None, "no metadata"
    if not candidates:
        return None, "no candidate"
    try:
        digest = sha256_file(run_file)
    except OSError:
        raise
    for candidate in candidates:
        try:
            if _sha256_cached(candidate, sha_memo) == digest:
                return candidate, ""
        except OSError:
            continue
    return None, "sha mismatch"


def _link_or_copy(run_file: Path, cache_file: Path) -> str:
    """Replace ``run_file`` with a hardlink to ``cache_file``; never write through a link.

    ``os.link`` into a fresh temp name, then ``os.replace`` over the run file. On OSError the
    temp is removed, a byte copy is attempted instead (``copy-fallback``); an OSError on the
    fallback propagates to the caller, which records the error and continues.
    """
    tmp = run_file.with_name(f".{run_file.name}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        os.link(cache_file, tmp)
    except OSError:
        try:
            shutil.copyfile(cache_file, tmp)
            os.replace(tmp, run_file)
        except OSError:
            _unlink_quietly(tmp)
            raise
        return "copy-fallback"
    try:
        os.replace(tmp, run_file)
    except OSError:
        _unlink_quietly(tmp)
        raise
    return "linked"


def _unlink_quietly(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def _process(run_file: Path, design_dir: Path, kind: str, cache_root: Path, apply: bool,
             *, index: _CacheIndex | None = None,
             sha_memo: dict[str, str] | None = None) -> dict:
    """Work one run file. Never raises for an expected failure; returns the manifest entry."""
    entry: dict = {
        "run_file": str(run_file),
        "cache_file": None,
        "design_dir": str(design_dir),
        "kind": kind,
        "size_bytes": 0,
        "action": "",
        "reason": "",
    }
    try:
        entry["size_bytes"] = run_file.stat().st_size
        candidate, reason = find_candidate(
            design_dir, run_file, kind, cache_root, index=index, sha_memo=sha_memo
        )
        if candidate is None:
            entry["action"] = "unmatched"
            entry["reason"] = reason
            return entry
        entry["cache_file"] = str(candidate)
        try:
            same = os.path.samefile(run_file, candidate)
        except OSError:
            same = False
        if same:
            entry["action"] = "already"
        elif not apply:
            entry["action"] = "would-link"
        else:
            entry["action"] = _link_or_copy(run_file, candidate)
        return entry
    except Exception as exc:      # noqa: BLE001 - one bad file must not abort the run
        entry["action"] = "error"
        entry["error"] = f"{type(exc).__name__}: {exc}"
        return entry


def _iter_design_dirs(runs: Path, limit: int | None) -> list[Path]:
    try:
        dirs = sorted(p for p in runs.glob("*/designs/*") if p.is_dir())
    except OSError:
        return []
    return dirs[:limit] if limit is not None else dirs


def _human_bytes(n: int) -> str:
    value = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024.0 or unit == "TiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024.0
    return f"{n} B"


def run(*, runs: Path, cache_mesh: Path, cache_solve: Path, apply: bool = False,
        limit: int | None = None, manifest: Path | None = None) -> dict:
    """Scan (and with ``apply`` link) the heavy run files. Returns the manifest document."""
    counts: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    entries: list[dict] = []
    indexes: dict[Path, _CacheIndex] = {}
    sha_memo: dict[str, str] = {}

    for design_dir in _iter_design_dirs(runs, limit):
        counts["design_dirs"] += 1
        for kind, (_, _, filename) in _METADATA.items():
            run_file = design_dir / filename
            if not run_file.is_file():
                continue
            counts[f"{kind}_examined"] += 1
            cache_root = cache_mesh if kind == KIND_MESH else cache_solve
            index = indexes.get(cache_root)
            if index is None:
                index = _CacheIndex(cache_root)
                indexes[cache_root] = index
            entry = _process(run_file, design_dir, kind, cache_root, apply,
                             index=index, sha_memo=sha_memo)
            entries.append(entry)
            action = entry["action"]
            counts[action] += 1
            if action == "unmatched":
                reasons[entry["reason"] or "unknown"] += 1

    saved_actions = {"linked", "would-link", "already"}
    bytes_saved = sum(e["size_bytes"] for e in entries if e["action"] in saved_actions)
    bytes_by_action: Counter[str] = Counter()
    for e in entries:
        if e["action"] in saved_actions:
            bytes_by_action[e["action"]] += e["size_bytes"]

    now = datetime.now(timezone.utc)
    doc = {
        "generated_utc": now.isoformat(timespec="seconds"),
        "mode": "apply" if apply else "dry-run",
        "runs": str(runs),
        "cache_mesh": str(cache_mesh),
        "cache_solve": str(cache_solve),
        "limit": limit,
        "counts": {
            "design_dirs_scanned": counts["design_dirs"],
            "mesh_files_examined": counts["mesh_examined"],
            "response_files_examined": counts[f"{KIND_SOLVE}_examined"],
            "linked": counts["linked"],
            "would_link": counts["would-link"],
            "already": counts["already"],
            "copy_fallback": counts["copy-fallback"],
            "unmatched": counts["unmatched"],
            "errors": counts["error"],
        },
        "unmatched_reasons": dict(sorted(reasons.items())),
        "bytes_saved": bytes_saved,
        "bytes_by_action": dict(sorted(bytes_by_action.items())),
        "entries": entries,
    }
    doc["_manifest_path"] = str(manifest) if manifest is not None else ""
    return doc


def _write_manifest(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    tmp.write_text(json.dumps(doc, indent=2, sort_keys=False), encoding="utf-8")
    os.replace(tmp, path)


def _summary_lines(doc: dict) -> list[str]:
    c = doc["counts"]
    mode = "dry-run (nothing changed)" if doc["mode"] == "dry-run" else "apply"
    lines = [
        f"dedupe_runs [{mode}]",
        f"  design dirs scanned    : {c['design_dirs_scanned']}",
        f"  mesh files examined    : {c['mesh_files_examined']}",
        f"  response files examined: {c['response_files_examined']}",
        f"  linked (this run)      : {c['linked']}",
        f"  would-link             : {c['would_link']}",
        f"  already linked         : {c['already']}",
        f"  copy-fallback          : {c['copy_fallback']}",
        f"  unmatched              : {c['unmatched']}"
        f" {doc['unmatched_reasons'] or ''}".rstrip(),
        f"  errors                 : {c['errors']}",
        f"  bytes saved            : {_human_bytes(doc['bytes_saved'])}"
        f" ({doc['bytes_saved']} bytes)",
        f"  manifest               : {doc['_manifest_path'] or '(not written)'}",
    ]
    return lines


def _default_manifest() -> Path:
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    return _resolve(f"scratch/{now.strftime('%Y-%m-%d')}_consolidation/"
                    f"dedupe_manifest_{stamp}.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dedupe_runs.py",
        description="Replace byte-duplicate heavy run files with hardlinks to their cache entry "
                    "(dry-run by default; --apply to link).",
    )
    parser.add_argument("--runs", default="runs", help="run store (default: runs)")
    parser.add_argument("--cache-mesh", default="cache/mesh",
                        help="mesh cache root (default: cache/mesh)")
    parser.add_argument("--cache-solve", default="cache/solve",
                        help="solve cache root (default: cache/solve)")
    parser.add_argument("--apply", action="store_true",
                        help="perform the links (default: report only)")
    parser.add_argument("--manifest", default=None,
                        help="manifest path (default: "
                             "scratch/<YYYY-MM-DD>_consolidation/dedupe_manifest_<UTC>.json)")
    parser.add_argument("--limit", type=int, default=None,
                        help="cap the number of design dirs processed")
    parser.add_argument("--quiet", action="store_true", help="only write the manifest")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit is not None and args.limit < 0:
        raise SystemExit("--limit must be >= 0")
    manifest = _resolve(args.manifest) if args.manifest else _default_manifest()
    doc = run(
        runs=_resolve(args.runs),
        cache_mesh=_resolve(args.cache_mesh),
        cache_solve=_resolve(args.cache_solve),
        apply=bool(args.apply),
        limit=args.limit,
        manifest=manifest,
    )
    _write_manifest(manifest, doc)
    if not args.quiet:
        for line in _summary_lines(doc):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
