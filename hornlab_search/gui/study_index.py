"""Bounded discovery and routing for local study registries.

A night can create one study registry per arm (``runs/<night>/<arm>/studies.sqlite3``)
while the GUI's own drafts live in ``runs/studies``.  The GUI must read both without
turning a client string into a filesystem path, so this module keeps an explicit,
read-only root index:

* the primary root (``runs/studies`` by default),
* extra roots passed on the command line / environment,
* study registries discovered under ``runs`` (depth-limited, cached).

Every route resolves a study id to exactly one registered root.  The returned root id
is a short hash of the repository-relative path, so it is safe to put in a URL.
"""
from __future__ import annotations

import hashlib
import os
import threading
import time
from pathlib import Path

from hornlab_search.studies.schema import Conflict, NotFound, StudyError
from hornlab_search.studies.service import StudyService

#: How long a discovery result may be reused.  The study page polls every few seconds;
#: re-walking ``runs/`` on every poll would be wasteful and can race a night writing files.
DISCOVERY_TTL_S = 10.0
#: Depth below ``runs/`` to look for ``studies.sqlite3``.  Real arms are at depth 2
#: (``runs/<night>/<arm>``); 4 leaves room for a nested campaign without turning into a
#: whole-tree search.
MAX_DEPTH = 4
_SKIP_DIRS = frozenset({
    ".git", ".venv", "__pycache__", "artifacts", "workers", "designs", "step",
    "cache", "cache_cpu", "dataset", "dataset_cpu", "node_modules",
})


class StudyIndex:
    """Resolve study ids to services without accepting a path from the client."""

    def __init__(self, root, *, primary_root=None, extra_roots=()):
        self.root = Path(root).resolve()
        self.primary_root = (Path(primary_root) if primary_root is not None
                             else self.root / "runs" / "studies").resolve()
        self.extra_roots = tuple(Path(p).resolve() for p in extra_roots)
        self._services: dict[Path, StudyService] = {}
        self._roots: list[dict] = []
        self._stamp = 0.0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ roots

    def _rel(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return path.resolve().as_posix()

    def _root_id(self, path: Path) -> str:
        return hashlib.sha256(self._rel(path).encode("utf-8")).hexdigest()[:8]

    def _valid(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
        except OSError:
            return False
        if not resolved.is_dir() or not (resolved / "studies.sqlite3").is_file():
            return False
        try:
            resolved.relative_to(self.root)
        except ValueError:
            return False
        return True

    def _discover(self) -> list[Path]:
        found: list[Path] = []
        seen: set[Path] = set()

        def add(path: Path) -> None:
            try:
                resolved = path.resolve()
            except OSError:
                return
            if resolved not in seen and self._valid(resolved):
                seen.add(resolved)
                found.append(resolved)

        add(self.primary_root)
        for path in self.extra_roots:
            add(path)
        runs = (self.root / "runs").resolve()
        if runs.is_dir():
            for dirpath, dirnames, filenames in os.walk(runs):
                current = Path(dirpath)
                try:
                    depth = len(current.relative_to(runs).parts)
                except ValueError:
                    continue
                if "studies.sqlite3" in filenames:
                    add(current)
                    dirnames[:] = []          # a study root: do not walk its artifacts
                    continue
                if depth >= MAX_DEPTH:
                    dirnames[:] = []
                    continue
                dirnames[:] = sorted(
                    d for d in dirnames
                    if d not in _SKIP_DIRS and not d.startswith(".")
                )
        return found

    def roots(self, *, force: bool = False) -> list[dict]:
        with self._lock:
            now = time.monotonic()
            if force or not self._roots or now - self._stamp > DISCOVERY_TTL_S:
                paths = self._discover()
                self._roots = [
                    {"id": self._root_id(path), "label": self._rel(path), "path": path}
                    for path in paths
                ]
                self._stamp = now
            return [dict(item, path=str(item["path"])) for item in self._roots]

    def _service(self, path: Path) -> StudyService:
        resolved = path.resolve()
        with self._lock:
            service = self._services.get(resolved)
            if service is None:
                service = StudyService(resolved)
                self._services[resolved] = service
            return service

    def _root_by_id(self, root_id: str) -> dict:
        if not isinstance(root_id, str) or not root_id:
            raise StudyError("root id is required")
        for item in self.roots():
            if item["id"] == root_id:
                return item
        raise NotFound(f"unknown study root {root_id!r}")

    # ------------------------------------------------------------------ resolution

    def service_for_path(self, path) -> tuple[str, StudyService]:
        """Return ``(root_id, service)`` for a repository-contained study root."""
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.root / candidate
        if not self._valid(candidate):
            raise NotFound("study root is not a registered studies.sqlite3 folder")
        resolved = candidate.resolve()
        return self._root_id(resolved), self._service(resolved)

    def resolve(self, study_id: str, root_id: str | None = None) -> tuple[dict, StudyService, dict]:
        """Resolve ``(study_id, optional root_id)`` to ``(root, service, study)``."""
        if root_id:
            item = self._root_by_id(root_id)
            service = self._service(Path(item["path"]))
            return item, service, service.get_study(study_id)
        matches = []
        for item in self.roots():
            service = self._service(Path(item["path"]))
            try:
                matches.append((item, service, service.get_study(study_id)))
            except NotFound:
                continue
            except Exception:  # noqa: BLE001 - a broken/corrupt root must not hide a good one
                continue
        if not matches:
            raise NotFound(f"study {study_id!r} was not found in any registered root")
        if len(matches) > 1:
            raise Conflict("ambiguous study id; pass root")
        return matches[0]

    def list_studies(self, limit: int = 50) -> list[dict]:
        """Bounded summaries from every registered root, newest registry first."""
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
            raise StudyError("study list limit must be in 1..50")
        out: list[dict] = []
        for item in self.roots():
            service = self._service(Path(item["path"]))
            try:
                rows = service.list_studies(limit=limit)
            except Exception:  # noqa: BLE001 - one broken/corrupt root must not hide the rest
                continue
            for row in rows:
                out.append({
                    **row,
                    "root": item["id"],
                    "root_label": item["label"],
                })
        return out[:limit]
