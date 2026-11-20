"""The owner's favorites registry (``docs/favorites/FAVORITES.yaml``) for the GUI star toggle.

Schema ``hornlab-favorites-v1``; rules in ``docs/favorites/README.md``: append-only, one entry per
design hash, never delete (retire with ``status: retired`` + ``retired_note``). The file is
hand-edited too, so it is never re-dumped: starring APPENDS a YAML block at the end of the
``favorites:`` list and retiring rewrites only the one ``status:`` line of one entry. Every write
re-parses the result and refuses (file untouched) unless exactly the intended change happened.

Starring builds the entry from the run's own files: ``best.json`` (hash, eval, J, family, knobs),
``run.json`` (config path, objective version, mode, verify parent) and the config's
``brief_file``. J is read from ``best.json``, never typed (README rule 1).
"""
from __future__ import annotations

import json
import os
import posixpath
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

SCHEMA = "hornlab-favorites-v1"
REL_PATH = Path("docs") / "favorites" / "FAVORITES.yaml"
_HEADER = (
    "# HornFab favorites registry: horns the OWNER has starred. Machine-readable; agents and the GUI"
    " read this file.\n"
    "# Rules: append-only (retire with status: retired, never delete); one entry per design hash; J"
    " is only\n# comparable within the same brief/objective identity, never across. How to add:"
    " docs/favorites/README.md.\n"
    f"schema: {SCHEMA}\nfavorites:\n")
_ID_RE = re.compile(r"^FAV-(\d+)$")
_LOCK = threading.Lock()
_MAX_NOTE = 4000


def favorites_path(root: Path) -> Path:
    return Path(root) / REL_PATH


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _read_json(p: Path) -> dict:
    try:
        v = json.loads(p.read_text(encoding="utf-8"))
        return v if isinstance(v, dict) else {}
    except (OSError, ValueError):
        return {}


def _parse(text: str) -> dict:
    try:
        doc = yaml.safe_load(text) if text.strip() else None
    except yaml.YAMLError as exc:
        raise ValueError(f"FAVORITES.yaml does not parse: {exc}") from exc
    if doc is None:
        return {"schema": SCHEMA, "favorites": []}
    if not isinstance(doc, dict):
        raise ValueError("FAVORITES.yaml is not a mapping")
    if doc.get("schema") != SCHEMA:
        raise ValueError(f"FAVORITES.yaml schema is {doc.get('schema')!r}, expected {SCHEMA!r}")
    favs = doc.get("favorites")
    if favs is None:
        doc["favorites"] = []
    elif not isinstance(favs, list):
        raise ValueError("FAVORITES.yaml 'favorites' is not a list")
    return doc


def _run_ids(entry: dict) -> list[str]:
    """Run ids an entry points at (``runs.<kind>.run_dir`` basenames, e.g. ``runs/<id>``)."""
    out = []
    runs = entry.get("runs") if isinstance(entry.get("runs"), dict) else {}
    for v in runs.values():
        rd = v.get("run_dir") if isinstance(v, dict) else None
        if isinstance(rd, str) and rd.strip():
            parts = [p for p in rd.replace("\\", "/").split("/") if p]
            # runs/<id>/verify -> <id>; runs/<id> -> <id>
            if parts and parts[-1] == "verify" and len(parts) >= 2:
                parts = parts[:-1]
            if parts:
                out.append(parts[-1])
    return out


def load_favorites(root: Path) -> dict:
    """The registry plus lookups the views need. Never raises: a broken file reports ``error``.

    ``{available, path, schema, favorites, by_run: {run_id: [fav_id]}, by_hash: {hash: fav_id},
    error?}``; ``by_run``/``by_hash`` index ACTIVE entries only (a retired star is not shown).
    """
    p = favorites_path(root)
    out: dict[str, Any] = {"available": p.is_file(), "path": REL_PATH.as_posix(), "schema": SCHEMA,
                           "favorites": [], "by_run": {}, "by_hash": {}}
    if not p.is_file():
        return out
    try:
        doc = _parse(p.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out
    favs = [f for f in doc["favorites"] if isinstance(f, dict)]
    out["favorites"] = favs
    for f in favs:
        if f.get("status", "active") != "active":
            continue
        if f.get("design_hash"):
            out["by_hash"][str(f["design_hash"])] = f.get("id")
        for rid in _run_ids(f):
            out["by_run"].setdefault(rid, []).append(f.get("id"))
    return out


def _next_id(favs: list[dict]) -> str:
    n = 0
    for f in favs:
        m = _ID_RE.match(str(f.get("id", "")))
        if m:
            n = max(n, int(m.group(1)))
    return f"FAV-{n + 1:03d}"


def _brief_path(config_path: str | None, brief_file: str | None) -> str | None:
    if not brief_file:
        return None
    b = str(brief_file).replace("\\", "/")
    if config_path and not posixpath.isabs(b):
        return posixpath.normpath(posixpath.join(posixpath.dirname(config_path.replace("\\", "/")), b))
    return b


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def build_entry(root: Path, runs: Path, run_id: str, *, owner_note: str, fav_id: str,
                title: str | None = None) -> dict:
    """A new registry entry from the run's ``best.json``/``run.json``/``config.yaml``."""
    from .data import _config, _resolve_run, run_objective_version
    d = _resolve_run(Path(runs), run_id)
    best = _read_json(d / "best.json")
    if not best.get("design_hash"):
        raise ValueError(f"run {run_id} has no best.json design_hash to star")
    rj = _read_json(d / "run.json")
    cfg = _config(d)
    version = run_objective_version(d)
    config_path = rj.get("config_path") or None
    brief = _brief_path(config_path, cfg.get("brief_file"))
    gen = cfg.get("generator")
    gen_s = None
    if isinstance(gen, dict):
        gen_s = str(gen.get("name") or "")
        rows = gen.get("rows")
        if isinstance(rows, dict) and rows.get("type"):
            gen_s += f" / rows.type {rows['type']}"
    elif gen:
        gen_s = str(gen)
    try:
        rel_run = d.resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        rel_run = f"runs/{d.name}"
    mode = str(best.get("mode") or rj.get("mode") or "screen")
    rec = {"run_dir": rel_run, "eval_no": best.get("eval_no"), "J": _num(best.get("objective"))}
    run_refs: dict[str, Any] = {}
    if mode == "verify":
        parent = rj.get("verify_of") if isinstance(rj.get("verify_of"), dict) else {}
        if parent.get("run_id"):
            run_refs["screen"] = {"run_dir": f"runs/{parent['run_id']}"}
        run_refs["verify"] = rec
    else:
        run_refs["screen"] = rec
    params = best.get("params") if isinstance(best.get("params"), dict) else {}
    grid = params.get("grid") if isinstance(params.get("grid"), dict) else {}
    knobs = grid.get("knobs") if isinstance(grid.get("knobs"), dict) else {
        k: v for k, v in params.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    entry: dict[str, Any] = {
        "id": fav_id,
        "added": _today(),
        "added_by": "owner (GUI star)",
        "title": (title or "").strip() or f"{cfg.get('name') or rj.get('config_name') or d.name} "
                                          f"({best['design_hash']})",
        "owner_note": owner_note,
        "design_hash": str(best["design_hash"]),
        "family": best.get("family") or cfg.get("family"),
        "generator": gen_s,
        "config": config_path,
        "brief": brief,
        "objective": f"v{version}",
        "runs": run_refs,
        "gui": f"http://127.0.0.1:8765/#/run/{d.name}",
        "knobs": {k: (round(float(v), 6) if isinstance(v, float) else v) for k, v in knobs.items()},
        "status": "active",
    }
    return {k: v for k, v in entry.items() if v is not None}


def _entry_yaml(entry: dict) -> str:
    """One list item, indented like the hand-written entries (``- id: ...`` / two-space body)."""
    body = yaml.safe_dump([entry], sort_keys=False, allow_unicode=True, width=110,
                          default_flow_style=False)
    return body if body.endswith("\n") else body + "\n"


def _write_checked(p: Path, new_text: str, check, what: str) -> None:
    """Parse + ``check`` the new text, then replace the file atomically; any failure leaves it."""
    try:
        check(_parse(new_text))
    except ValueError as exc:
        raise ValueError(f"FAVORITES.yaml {what} check failed (file left unchanged): {exc}") from exc
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(new_text, encoding="utf-8", newline="\n")
    os.replace(tmp, p)


def star_run(root: Path, runs: Path, run_id: str, owner_note: str, title: str | None = None) -> dict:
    """Star a run's best design: append a new entry, or re-activate a retired one for that hash.

    Raises ``ValueError`` when the hash already has an ACTIVE entry or the note is empty.
    """
    note = str(owner_note or "").strip()
    if not note:
        raise ValueError("owner_note is required (the owner's words about why this horn is a favorite)")
    if len(note) > _MAX_NOTE:
        raise ValueError(f"owner_note longer than {_MAX_NOTE} characters")
    p = favorites_path(root)
    with _LOCK:
        text = p.read_text(encoding="utf-8") if p.is_file() else _HEADER
        doc = _parse(text)
        favs = [f for f in doc["favorites"] if isinstance(f, dict)]
        probe = build_entry(root, runs, run_id, owner_note=note, fav_id=_next_id(favs), title=title)
        same = [f for f in favs if str(f.get("design_hash")) == probe["design_hash"]]
        if same:
            f = same[0]
            if f.get("status", "active") == "active":
                raise ValueError(f"{probe['design_hash']} is already favorite {f.get('id')}")
            return _set_status(p, text, str(f.get("id")), "active", note)
        if not text.endswith("\n"):
            text += "\n"
        if text.rstrip().endswith("favorites: []"):
            text = text.rstrip()[: -len(" []")] + "\n"
        old = [dict(f) for f in favs]

        def check(new_doc):
            got = new_doc["favorites"]
            if not got or got[:-1] != old or got[-1] != probe:
                raise ValueError("the 'favorites:' list must be the last top-level key")
        _write_checked(p, text + _entry_yaml(probe), check, "append")
    return {"ok": True, "action": "starred", "id": probe["id"], "entry": probe}


def _set_status(p: Path, text: str, fav_id: str, status: str, note: str) -> dict:
    """Rewrite one entry's ``status:`` line (plus dated note lines); everything else byte-equal."""
    lines = text.splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines)
                  if re.match(rf"^- id:\s*['\"]?{re.escape(fav_id)}['\"]?\s*$", ln)), None)
    if start is None:
        raise ValueError(f"{fav_id} not found in FAVORITES.yaml")
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].startswith("- ") or re.match(r"^[A-Za-z_]", lines[i])), len(lines))
    idx = next((i for i in range(start + 1, end) if re.match(r"^  status:\s*\S", lines[i])), None)
    if idx is None:
        raise ValueError(f"{fav_id} has no top-level 'status:' line to change")
    doc = _parse(text)
    before = [dict(f) for f in doc["favorites"] if isinstance(f, dict)]
    extra = ({"retired": _today(), "retired_note": note} if status == "retired"
             else {"reactivated": _today(), "reactivated_note": note})
    block = yaml.safe_dump({"status": status, **extra}, sort_keys=False, allow_unicode=True,
                           width=110, default_flow_style=False)
    block = "".join("  " + ln + "\n" for ln in block.splitlines())
    new_text = "".join(lines[:idx]) + block + "".join(lines[idx + 1:])

    def check(new_doc):
        after = [f for f in new_doc["favorites"] if isinstance(f, dict)]
        if len(after) != len(before):
            raise ValueError("the entry count changed")
        for a, b in zip(after, before):
            if b.get("id") != fav_id:
                if a != b:
                    raise ValueError("another entry changed")
                continue
            expect = {**b, "status": status, **extra}
            if a != expect:
                raise ValueError(f"{fav_id} is not exactly the expected entry")
    _write_checked(p, new_text, check, "status change")
    return {"ok": True, "action": "retired" if status == "retired" else "reactivated", "id": fav_id}


def retire_favorite(root: Path, fav_id: str, note: str) -> dict:
    """Un-star: ``status: retired`` with ``retired``/``retired_note`` (README rule 4: never delete)."""
    note = str(note or "").strip()
    if not note:
        raise ValueError("retired_note is required (why the star is removed)")
    p = favorites_path(root)
    with _LOCK:
        if not p.is_file():
            raise FileNotFoundError(REL_PATH.as_posix())
        text = p.read_text(encoding="utf-8")
        doc = _parse(text)
        match = [f for f in doc["favorites"] if isinstance(f, dict) and f.get("id") == fav_id]
        if not match:
            raise ValueError(f"{fav_id} not found in FAVORITES.yaml")
        if match[0].get("status", "active") != "active":
            raise ValueError(f"{fav_id} is already {match[0].get('status')}")
        return _set_status(p, text, fav_id, "retired", note)
