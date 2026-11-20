"""Overview phase 4 (WP4.3): the search box behind every line, and whether it is pinned to a wall.

For each ranked line of work the Overview shows the best run's declared bounds and the winning
parameters, so "the search still improves" can be read next to "the knob sits on its bound". This
is the read-only view of ``config.yaml`` (``bounds``: ``lo``/``hi``/``search: false``) plus the
best valid row of the run's ``search.ndjson``. Nothing here solves, and nothing is written.

A knob is **box-limited** when its best value is within 2 % of either end of its own range
(``(hi - lo) * 0.02``); a knob with ``search: false`` is **fixed** and listed separately. Values are
never compared across score identities.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from . import data as D
from . import data_overview as OV

BOUND_TOL = 0.02                    # "within 2 % of a bound" (plan WP4.3)


def _config(run_dir: Path) -> dict:
    try:
        raw = yaml.safe_load((run_dir / "config.yaml").read_text(encoding="utf-8-sig"))
    except (OSError, yaml.YAMLError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _best_row(run_dir: Path) -> dict | None:
    rows = [r for r in D.read_ndjson(run_dir / "search.ndjson")
            if r.get("ok") and isinstance(r.get("objective"), (int, float))]
    if not rows:
        return None
    return min(rows, key=lambda r: float(r["objective"]))


def _knobs(bounds: dict, values: dict) -> tuple[list[dict], list[dict], list[str]]:
    """(fixed, free, at_bound_keys) from one run's bounds and best params."""
    fixed: list[dict] = []
    free: list[dict] = []
    at_bound: list[str] = []
    for key, spec in (bounds or {}).items():
        if not isinstance(spec, dict):
            continue
        val = values.get(key)
        if spec.get("search") is False:
            fixed.append({"key": str(key), "value": val,
                          "lo": spec.get("lo"), "hi": spec.get("hi")})
            continue
        lo, hi = spec.get("lo"), spec.get("hi")
        row = {"key": str(key), "value": val, "lo": lo, "hi": hi, "at_bound": None}
        if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and isinstance(val, (int, float)):
            span = float(hi) - float(lo)
            tol = abs(span) * BOUND_TOL
            if span and abs(float(val) - float(lo)) <= tol:
                row["at_bound"] = "lo"
            elif span and abs(float(val) - float(hi)) <= tol:
                row["at_bound"] = "hi"
            if row["at_bound"]:
                at_bound.append(str(key))
        free.append(row)
    return fixed, free, at_bound


def line_params(runs: Path, line: dict) -> dict:
    """Bounds + best parameters for one line's best run (absent run/config -> a note, never a raise)."""
    run_id = line.get("best_run_id")
    out = {"construction": line.get("construction"), "card": line.get("card"),
           "best_run_id": run_id, "best_j": line.get("best_j"),
           "fixed": [], "free": [], "at_bound": [], "error": None}
    if not run_id:
        out["error"] = "no ranked run"
        return out
    run_dir = Path(runs) / str(run_id)
    cfg = _config(run_dir)
    if not cfg:
        out["error"] = "config.yaml missing or unreadable"
        return out
    best = _best_row(run_dir)
    values = dict((best or {}).get("params") or {})
    fixed, free, at_bound = _knobs(cfg.get("bounds") or {}, values)
    out.update(fixed=fixed, free=free, at_bound=at_bound)
    if best is None:
        out["error"] = "no valid evaluated row"
    return out


def params(root: Path, runs: Path, days: float = 14.0, show_legacy: bool = False) -> dict:
    """Per ranked line of every visible identity: fixed knobs, free knobs, bound hits."""
    ov = OV.overview(root, runs, days=float(days), show_legacy=bool(show_legacy))
    identities = []
    for ident in ov.get("identities") or []:
        lines = [line_params(runs, ln) for ln in ident.get("lines") or [] if ln.get("rank")]
        if not lines:
            continue
        identity = {"id": ident["id"], "label": ident.get("label"), "status": ident.get("status"),
                    "objective_version": ident.get("objective_version"), "lines": lines}
        identity["n_bound_lines"] = sum(1 for ln in lines if ln.get("at_bound"))
        identities.append(identity)
    return D.clean({"generated_utc": ov.get("generated_utc"), "days": float(days),
                    "since_utc": ov.get("since_utc"), "show_legacy": bool(show_legacy),
                    "identities": identities})
