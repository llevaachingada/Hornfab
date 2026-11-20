"""Project readiness registry (WP3.1) — the merged view behind ``GET /api/overview/registry``.

Two hand-maintained files, one merged read:

* ``docs/registry/project_readiness.yaml`` (schema ``project_readiness_v1``) carries only the
  project-side rows (areas ``search`` / ``software`` / ``gui`` / ``data``).
* ``docs/research/system_woofer_2026-11-18/readiness.yaml`` (schema ``hw_readiness_v1``,
  or ``hw_readiness_v2`` since 2026-11-20, whose case declarations live in ``cases.d/``) keeps the
  hardware rows where they already live; this loader merges them at read time with ``area: hw``.
  Nothing is duplicated into the project file.

Read-only, stdlib + ``yaml`` only. A missing or malformed file is reported in ``errors`` and the
other file's rows are still returned — a registry that silently drops a file is worse than one
that admits it. Duplicate ids across the two files are an error: the later row (the project one,
because the HW file is loaded first) is dropped and the drop is named in ``errors``.

Every returned row has the same shape the Readiness page already uses, plus ``area``:

* risk     ``{id, area, level, title, status, wp, blocked_by, evidence, source}``
* decision ``{id, area, question, recommendation, status, decided, source}``
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import data as D

SCHEMA = "project_readiness_v1"
HW_SCHEMA = "hw_readiness_v1"
HW_SCHEMA_V2 = "hw_readiness_v2"
PROJECT_REL = Path("docs/registry/project_readiness.yaml")
HW_REL = Path("docs/research/system_woofer_2026-11-18/readiness.yaml")
AREAS = ("search", "hw", "software", "gui", "data")

_RISK_KEYS = ("id", "area", "level", "title", "status", "wp", "blocked_by", "evidence", "source")
_DECISION_KEYS = ("id", "area", "question", "recommendation", "status", "decided", "source")

_CACHE: dict[tuple, Any] = {}
_CACHE_MAX = 16


# --------------------------------------------------------------------------- cache

def _stamp(p: Path) -> tuple:
    """A cache key component; missing files are keyed too, so creating one invalidates the entry."""
    if not p.is_file():
        return ("missing", str(p))
    st = p.stat()
    return (str(p), st.st_mtime_ns, st.st_size)


def _cached(key: tuple, fn):
    if key in _CACHE:
        return _CACHE[key]
    value = fn()
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = value
    return value


# --------------------------------------------------------------------------- parsing

def _read_yaml(path: Path, expected_schema: str, label: str, errors: list[str],
               *, also: tuple[str, ...] = ()) -> dict | None:
    if not path.is_file():
        errors.append(f"{label} not found: {path.as_posix()}")
        return None
    try:
        import yaml
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - reported, never raised out of the loader
        errors.append(f"{label} unreadable: {type(exc).__name__}: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{label} is not a mapping")
        return None
    schema = data.get("schema")
    allowed = (expected_schema, *also)
    if schema not in allowed:
        wanted = " or ".join(repr(s) for s in allowed)
        errors.append(f"{label}: schema must be {wanted}, got {schema!r}")
    return data


def _rows(records: Any, kind: str, default_area: str, source_default: str,
          label: str, errors: list[str], *, report_missing_area: bool) -> list[dict]:
    """Normalise records to their documented shape; never silently drop a valid row."""
    keys = _RISK_KEYS if kind == "risk" else _DECISION_KEYS
    out: list[dict] = []
    if records is None:
        return out
    if not isinstance(records, list):
        errors.append(f"{label}: {kind}s must be a list, got {type(records).__name__}")
        return out
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            errors.append(f"{label} {kind}[{i}] is not a mapping")
            continue
        row = {k: rec.get(k) for k in keys}
        if row.get("id") in (None, ""):
            errors.append(f"{label} {kind}[{i}] is missing an id")
            continue
        if not row.get("area"):
            row["area"] = default_area
            if report_missing_area:
                errors.append(f"{label} {kind} {row['id']}: missing area, defaulted to "
                              f"{default_area!r}")
        elif row["area"] not in AREAS:
            errors.append(f"{label} {kind} {row['id']}: unknown area {row['area']!r}")
        if not row.get("source"):
            row["source"] = source_default
        out.append(row)
    return out


def _merge_by_id(hw_rows: list[dict], project_rows: list[dict], kind: str,
                 errors: list[str]) -> tuple[list[dict], int, int]:
    """HW rows first, then project rows; a duplicate id drops the later (project) row."""
    merged: list[dict] = []
    seen: dict[str, str] = {}
    kept_hw = kept_project = 0
    for origin, rows in (("hw", hw_rows), ("project", project_rows)):
        for row in rows:
            rid = str(row["id"])
            if rid in seen:
                errors.append(f"duplicate {kind} id {rid!r} in {origin} file "
                              f"(already from {seen[rid]}); dropped the {origin} row")
                continue
            seen[rid] = origin
            merged.append(row)
            if origin == "hw":
                kept_hw += 1
            else:
                kept_project += 1
    return merged, kept_hw, kept_project


def _declared_sources(project: dict | None) -> list[str]:
    declared = (project or {}).get("sources")
    out: list[str] = []
    if isinstance(declared, list):
        for item in declared:
            if isinstance(item, str) and item and item not in out:
                out.append(item)
    return out


# --------------------------------------------------------------------------- public API

def load_project_registry(root: Path) -> dict[str, Any]:
    """The merged HW + project readiness registry, with errors reported rather than swallowed."""
    root = Path(root)
    project_path = root / PROJECT_REL
    hw_path = root / HW_REL
    key = ("project_registry", _stamp(project_path), _stamp(hw_path))
    return _cached(key, lambda: _load(root))


def _load(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    project_path = root / PROJECT_REL
    hw_path = root / HW_REL
    project = _read_yaml(project_path, SCHEMA, PROJECT_REL.as_posix(), errors)
    hw = _read_yaml(hw_path, HW_SCHEMA, HW_REL.as_posix(), errors, also=(HW_SCHEMA_V2,))

    project_risks = _rows((project or {}).get("risks"), "risk", "search",
                          PROJECT_REL.as_posix(), "project", errors, report_missing_area=True)
    project_decisions = _rows((project or {}).get("decisions"), "decision", "search",
                              PROJECT_REL.as_posix(), "project", errors, report_missing_area=True)
    hw_risks = _rows((hw or {}).get("risks"), "risk", "hw",
                     HW_REL.as_posix(), "hw", errors, report_missing_area=False)
    hw_decisions = _rows((hw or {}).get("decisions"), "decision", "hw",
                         HW_REL.as_posix(), "hw", errors, report_missing_area=False)

    risks, hw_risk_n, project_risk_n = _merge_by_id(hw_risks, project_risks, "risk", errors)
    decisions, hw_decision_n, project_decision_n = _merge_by_id(
        hw_decisions, project_decisions, "decision", errors)

    rows = risks + decisions
    open_count = sum(1 for r in rows if str(r.get("status") or "").lower() == "open")
    by_level: dict[str, int] = {}
    for r in risks:
        level = str(r.get("level") or "UNKNOWN")
        by_level[level] = by_level.get(level, 0) + 1

    sources = _declared_sources(project)
    for rel in (PROJECT_REL.as_posix(), HW_REL.as_posix()):
        if rel not in sources:
            sources.append(rel)

    payload = {
        "schema": SCHEMA,
        "risks": risks,
        "decisions": decisions,
        "counts": {
            "hw": hw_risk_n + hw_decision_n,
            "project": project_risk_n + project_decision_n,
            "total": len(rows),
            "open": open_count,
            "by_level": by_level,
        },
        "sources": sources,
        "errors": errors,
    }
    return D.clean(payload)
