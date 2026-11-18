"""Provenance and immutable case directories for ``hornlab_search.system``.

Design rules (parent brief, feat/woofer-system-v0):

* The system layer NEVER writes into the historical ``runs/`` tree. Historical responses,
  caches and night records are read-only inputs. Everything new goes into an isolated store:
  ``<HORNLAB_SYSTEM_STORE>`` (default ``<repo>/system_runs``).
* One case directory per evaluated assembly/optimisation case, created fresh and never
  rewritten: a rerun creates a new directory stamped with the study/analysis ids.
* Every manifest is written atomically (temp file + ``os.replace``) and carries the
  canonical-JSON SHA-256 of its own payload so later corruption is detectable.
* Identity functions come from :mod:`hornlab_search.system.contracts` (domain-separated
  sha16; horn identities are never reused as system identities).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import platform
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Mapping

from hornlab_search.system.contracts import SchemaError, canonical_json

__all__ = [
    "HISTORICAL_RUNS_MARKER",
    "case_paths",
    "new_case_dir",
    "write_manifest",
    "load_manifest",
    "file_sha256",
    "default_store_root",
    "assert_not_in_historical_runs",
]


#: Any directory whose ancestors include a path containing this marker is protected.
HISTORICAL_RUNS_MARKER = "runs"


def default_store_root() -> Path:
    """Isolated system store: ``$HORNLAB_SYSTEM_STORE`` or ``<cwd>/system_runs``."""
    env = os.environ.get("HORNLAB_SYSTEM_STORE", "").strip()
    return Path(env).resolve() if env else (Path.cwd() / "system_runs").resolve()


def case_paths(case_dir: Path) -> tuple[Path, Path]:
    """Standard layout of a case directory: manifest + artifacts live flat inside it."""
    case_dir = Path(case_dir)
    return case_dir, case_dir / "manifest.json"


def _utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def new_case_dir(experiment_id: str, store_root: str | os.PathLike[str] | None = None,
                 tag: str = "case") -> Path:
    """Create and return a fresh, empty, immutable-by-convention case directory.

    Layout: ``<store>/system/<experiment_id>/<UTC-timestamp>-<tag>-<pidsuffix>``. Two calls in
    the same second still differ by the pid suffix, so artifacts from different reruns never
    overwrite each other. Callers must not delete or rewrite prior directories.
    """
    if not experiment_id or any(c in experiment_id for c in "/\\:*?\"<>|"):
        raise SchemaError(f"experiment_id must be a safe non-empty label, got {experiment_id!r}")
    root = Path(store_root) if store_root else default_store_root()
    suffix = f"{os.getpid() % 100000:05d}-{uuid.uuid4().hex[:8]}"
    case_dir = root / "system" / experiment_id / f"{_utc_stamp()}-{tag}-{suffix}"
    case_dir.mkdir(parents=True, exist_ok=False)
    return case_dir


def write_manifest(case_dir: str | os.PathLike[str], payload: Mapping[str, Any]) -> Path:
    """Atomically write ``manifest.json`` with a self-describing integrity block.

    The manifest includes the canonical-JSON sha256 of ``payload`` (``manifest_payload_sha256``)
    plus host provenance (python version, platform, cwd). Existing manifests are never mutated:
    writing into a case dir that already has one must create a new case dir instead.
    """
    case_dir = Path(case_dir)
    manifest_path = case_dir / "manifest.json"
    if manifest_path.exists():
        raise SystemExit(
            f"manifest already present at {manifest_path}; immutability violation — "
            "create a new case directory for a rerun instead")
    body = {
        "created_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "host": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "cwd": str(Path.cwd()),
        },
        "manifest_payload_sha256": hashlib.sha256(canonical_json(payload).encode()).hexdigest(),
        "payload": {k: canonical_json(v) if isinstance(v, (dict, list, tuple)) else v
                    for k, v in payload.items()},
    }
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(case_dir), delete=False,
                                     suffix=".tmp") as fh:
        json.dump(body, fh, indent=2, sort_keys=True)
        fh.write("\n")
        tmp = Path(fh.name)
    os.replace(tmp, manifest_path)
    return manifest_path


def load_manifest(manifest_path: str | os.PathLike[str]) -> dict:
    """Read a manifest and verify its recorded payload checksum.

    ``payload`` entries that were canonicalised on write (dicts/lists) are reparsed to objects,
    and their re-canonicalised sha256 must match ``manifest_payload_sha256`` byte-exactly
    (round-trip integrity), else :class:`SchemaError`.
    """
    path = Path(manifest_path)
    with path.open("r", encoding="utf-8") as fh:
        body = json.load(fh)
    payload = {}
    for k, v in body.get("payload", {}).items():
        if isinstance(v, str) and v[:1] in ("{", "["):
            try:
                payload[k] = json.loads(v)
                continue
            except json.JSONDecodeError:
                pass
        payload[k] = v
    digest = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
    if digest != body.get("manifest_payload_sha256"):
        raise SchemaError(
            f"manifest integrity check failed for {path} "
            f"(recorded {body.get('manifest_payload_sha256')!r}, computed {digest!r})")
    return {"body": body, "payload": payload}


def file_sha256(path: str | os.PathLike[str]) -> str:
    """Streaming sha256 of a file (mesh/binaries/NPZ manifests use this, not the JSON canon)."""
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def assert_not_in_historical_runs(path: str | os.PathLike[str], store_root: Path) -> None:
    """Refuse a write target inside any historical ``runs`` tree (except the isolated store).

    The system layer has no sanctioned write path into ``runs/*``; the isolated store lives
    elsewhere (default ``<cwd>/system_runs``). This is a guard, not a policy substitute.
    """
    target = Path(path).resolve()
    store = Path(store_root).resolve()
    if store == target or store in target.parents:
        return
    for parent in target.parents:
        if parent.name == HISTORICAL_RUNS_MARKER:
            raise SchemaError(
                f"write target {target} is inside a historical runs tree; the system layer "
                "must write only in its isolated store (set HORNLAB_SYSTEM_STORE)")
