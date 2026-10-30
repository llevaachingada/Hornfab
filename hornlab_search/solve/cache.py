"""Solve cache: ``<root>/<key>/{response.npz, status.json}``.

Key is ``f"{design_hash}-{mesh_hash}-{solve_hash}"`` (01_CONTRACTS section 14). A hit
requires ``status.json`` with ``"ok": true`` AND a loadable ``response.npz``; anything else
(missing, corrupt, ``ok: false``) is a miss, never an error. Files are copied or hardlinked,
never symlinked (symlinks on Windows need elevation and fail in confusing ways).

``response.npz`` keys are exactly the ``Response`` field names. A ``None`` array field is an
ABSENT key. ``backend`` is a 0-d string array, ``n_dof`` a 0-d int array (absent when None) and
``meta`` a 0-d string array holding its JSON, so ``load(save(r))`` is bit-identical for every
array including complex dtypes. ``meta`` must be JSON-native (``base.jsonable`` guarantees it).
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import uuid
from dataclasses import fields
from pathlib import Path

import numpy as np

from ..types import Response
from .base import jsonable

log = logging.getLogger("hornlab_search.solve.cache")

RESPONSE_FILE = "response.npz"
STATUS_FILE = "status.json"

_ARRAY_FIELDS = ("freqs_hz", "h_angles_deg", "v_angles_deg", "spl_h_db", "spl_v_db",
                 "balloon_dirs", "spl_balloon_db", "z_throat", "p_h", "p_v", "p_balloon")
_SCALAR_FIELDS = ("backend", "n_dof", "meta")


def _field_names() -> set[str]:
    return {f.name for f in fields(Response)}


assert set(_ARRAY_FIELDS) | set(_SCALAR_FIELDS) == _field_names(), (
    "solve/cache.py is out of date with types.Response: " f"{sorted(_field_names())}")


def key(design_hash: str, mesh_hash: str, solve_hash: str) -> str:
    return f"{design_hash}-{mesh_hash}-{solve_hash}"


def entry_dir(k: str, root: Path) -> Path:
    return Path(root) / k


# ------------------------------------------------------------------ save / load


def save_response(path: Path, resp: Response) -> None:
    """Write ``resp`` to ``path`` (a .npz). Mechanical: field name == npz key."""
    arrays: dict[str, np.ndarray] = {}
    for name in _ARRAY_FIELDS:
        v = getattr(resp, name)
        if v is not None:
            arrays[name] = np.asarray(v)
    arrays["backend"] = np.array(str(resp.backend))
    if resp.n_dof is not None:
        arrays["n_dof"] = np.array(int(resp.n_dof), dtype=np.int64)
    arrays["meta"] = np.array(json.dumps(jsonable(resp.meta), sort_keys=True))
    path = Path(path)
    # Atomic: ``path`` may be a hardlink to a cache entry, so never write through it. Write a
    # temp file in the same directory, then replace the directory entry.
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        with open(tmp, "wb") as fh:      # a file object: np.savez must not append ".npz"
            np.savez(fh, **arrays)
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def load_response(path: Path) -> Response:
    with np.load(path, allow_pickle=False) as z:
        kw: dict = {}
        for name in _ARRAY_FIELDS:
            kw[name] = np.array(z[name]) if name in z.files else None
        kw["backend"] = str(z["backend"]) if "backend" in z.files else ""
        kw["n_dof"] = int(z["n_dof"]) if "n_dof" in z.files else None
        kw["meta"] = json.loads(str(z["meta"])) if "meta" in z.files else {}
    return Response(**kw)


# ------------------------------------------------------------------ lookup / store


def lookup(k: str, root: Path) -> Response | None:
    """Hit requires ``status.json`` with ``ok: true``. Loads ``response.npz``. Else None."""
    d = entry_dir(k, root)
    try:
        status = json.loads((d / STATUS_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(status, dict) or status.get("ok") is not True:
        return None
    try:
        return load_response(d / RESPONSE_FILE)
    except Exception as exc:       # corrupt or truncated entry is a miss, never a crash
        log.warning("cache entry %s is unreadable (%s); treating as a miss", k, exc)
        return None


def lookup_status(k: str, root: Path) -> dict | None:
    """The stored status dict (including ``ok: false`` ones), or None if absent/corrupt."""
    try:
        s = json.loads((entry_dir(k, root) / STATUS_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return s if isinstance(s, dict) else None


def store(k: str, root: Path, resp: Response | None, status: dict) -> None:
    """Write the entry. ``response.npz`` first, ``status.json`` last (atomically), so a reader
    never sees ``ok: true`` without its arrays. ``resp=None`` stores a status only (a failure
    record); ``status['ok']`` defaults to True when a response is given, False otherwise."""
    d = entry_dir(k, root)
    d.mkdir(parents=True, exist_ok=True)
    st = dict(status)
    st.setdefault("ok", resp is not None)
    if st["ok"] is True and resp is None:
        raise ValueError("store(): status ok=True requires a Response")
    # invalidate any previous good entry before rewriting its parts
    try:
        (d / STATUS_FILE).unlink()
    except OSError:
        pass
    if resp is not None:
        tmp = d / f".{RESPONSE_FILE}.{uuid.uuid4().hex[:8]}.tmp"
        save_response(tmp, resp)
        os.replace(tmp, d / RESPONSE_FILE)
    tmp = d / f".{STATUS_FILE}.{uuid.uuid4().hex[:8]}.tmp"
    tmp.write_text(json.dumps(jsonable(st), sort_keys=True, indent=2), encoding="utf-8")
    os.replace(tmp, d / STATUS_FILE)


def _install(src: Path, dst: Path, *, link: bool) -> None:
    """Install ``src`` at ``dst`` through a temp name in ``dst``'s directory + ``os.replace``.

    A pre-existing ``dst`` (possibly itself a hardlink to the shared cache) is replaced
    atomically and never written through. ``link=True`` hardlinks when the filesystem allows
    it and falls back to a plain copy (different volume, no hardlink support, permissions).
    """
    tmp = dst.with_name(f".{dst.name}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        if link:
            try:
                os.link(src, tmp)
            except OSError:
                shutil.copy2(src, tmp)
        else:
            shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def copy_entry(k: str, src_root: Path, dst_dir: Path) -> Path:
    """Copy or hardlink a cache entry's files into ``dst_dir`` (a run's designs/<hash>/).

    ``response.npz`` is hardlinked (copy fallback), so a run's file shares the cache inode;
    every writer into the run dir must therefore be atomic. ``status.json`` is always a plain
    copy: ``search/evaluate.py`` rewrites the run's own status and a shared inode would corrupt
    the cache entry. Never symlink (01_CONTRACTS section 14).
    """
    src = entry_dir(k, src_root)
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    if (src / RESPONSE_FILE).exists():
        _install(src / RESPONSE_FILE, dst_dir / RESPONSE_FILE, link=True)
    if (src / STATUS_FILE).exists():
        _install(src / STATUS_FILE, dst_dir / STATUS_FILE, link=False)
    return dst_dir
