"""Overview phase 2 (WP2.4): a per-line-of-work state for the typology matrix.

Adds one short ``state`` to every line of the phase-1 Overview payload and copies the **best**
line's state into each typology cell, so a cell can show why a line is where it is:

``converged | improving | box_limited | refusal_storm | probe | stale``

Precedence (documented here because it is the contract; first match wins):

    probe > refusal_storm > box_limited > improving > stale > converged

* **probe** - the line never reached the leaderboard minimum (``probe_only``).
* **refusal_storm** - ``refused_pct >= 40``: too many solves are being refused to read progress.
* **box_limited** - a ``walls`` analysis under ``runs/analysis/**/walls_*/walls.json`` proposes
  widening a bound for the line's best run (read-only check; no walls are computed here).
* **improving** - the budget rule is still open: the best run's valid rows gained at least 1 % in
  the tail (the last 20 % of valid rows improved the best-so-far value). This mirrors WP2.1's
  budget rule locally; the findings module is not imported.
* **stale** - the line's newest row is more than 7 days old.
* **converged** - none of the above.

Read-only over ``runs/``. :func:`annotate_states` mutates and returns the payload, is idempotent,
and never raises on a missing or partial payload (it returns it unchanged).
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from . import data as D

#: Canonical display order and the closed set of states.
STATE_ORDER = ("probe", "refusal_storm", "box_limited", "improving", "stale", "converged")

REFUSAL_STORM_PCT = 40.0
STALE_DAYS = 7.0
TAIL_GAIN_MIN = 0.01          # 1 % tail gain -> the budget rule is still open
TAIL_FRACTION = 0.8           # compare the best-so-far at 80 % of the valid rows with the final best

_WIDEN_ACTIONS = ("widen",)


# ---------------------------------------------------------------------------- helpers

def _parse_utc(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _tail_gain(js: list[float]) -> float | None:
    """Best-so-far tail gain over an ordered list of valid J values.

    ``(best_at_80pct - best_final) / best_at_80pct``; ``None`` when there are too few rows or the
    80 % best is not positive (J is a positive objective). Mirrors WP2.1's budget rule locally.
    """
    n = len(js)
    if n < 2:
        return None
    k = max(1, int(n * TAIL_FRACTION))
    if k >= n:
        k = n - 1
    early = min(js[:k])
    final = min(js)
    if early <= 0:
        return None
    return (early - final) / early


def _valid_objectives(rows: list[dict]) -> list[float]:
    out: list[float] = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("ok"):
            continue
        v = row.get("objective")
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        f = float(v)
        if math.isfinite(f):
            out.append(f)
    return out


def _budget_open(runs: Path, line: dict, min_valid: int) -> bool:
    """True when the best run's tail is still improving by >= 1 % over enough valid rows."""
    rid = line.get("best_run_id")
    if not rid:
        return False
    try:
        rows = D.read_ndjson(Path(runs) / str(rid) / "search.ndjson")
    except OSError:
        return False
    js = _valid_objectives(rows)
    if len(js) < max(1, int(min_valid)):
        return False
    gain = _tail_gain(js)
    return gain is not None and gain >= TAIL_GAIN_MIN


def _referenced_run_id(doc: dict) -> str | None:
    """Run id a walls.json payload points at, tolerant of Windows/POSIX separators."""
    for key in ("run_id", "run", "run_dir"):
        value = doc.get(key)
        if not isinstance(value, str) or not value:
            continue
        for cls in (PureWindowsPath, PurePosixPath):
            try:
                name = cls(value).name
            except (TypeError, ValueError):
                continue
            if name:
                return name
    return None


def _widen_run_ids(runs: Path) -> set[str]:
    """Run ids whose walls analysis proposes widening a bound (read-only; never computes walls)."""
    out: set[str] = set()
    try:
        paths = Path(runs).glob("analysis/**/walls_*/walls.json")
        for p in paths:
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(doc, dict):
                continue
            proposal = doc.get("proposal")
            if not isinstance(proposal, list):
                continue
            widen = any(isinstance(item, dict)
                        and str(item.get("action") or "").lower().startswith(_WIDEN_ACTIONS)
                        for item in proposal)
            if not widen:
                continue
            rid = _referenced_run_id(doc)
            if rid:
                out.add(rid)
    except OSError:
        return out
    return out


def _min_valid(ov: dict) -> int:
    try:
        return int((ov.get("registry") or {}).get("min_valid_for_leader", 10))
    except (TypeError, ValueError, AttributeError):
        return 10


def _state_for(line: dict, *, widen_ids: set[str], runs: Path, min_valid: int,
               now: datetime) -> str:
    if line.get("probe_only"):
        return "probe"
    pct = line.get("refused_pct")
    try:
        if pct is not None and float(pct) >= REFUSAL_STORM_PCT:
            return "refusal_storm"
    except (TypeError, ValueError):
        pass
    rid = line.get("best_run_id")
    if rid and str(rid) in widen_ids:
        return "box_limited"
    if _budget_open(runs, line, min_valid):
        return "improving"
    last = _parse_utc(line.get("last"))
    if last is not None and (now - last) > timedelta(days=STALE_DAYS):
        return "stale"
    return "converged"


def _best_line_for_cell(ident: dict, card_name: Any, cell: dict) -> dict | None:
    """The line a typology cell describes: same card + rank (+ construction), else lowest rank."""
    rank = cell.get("rank")
    construction = cell.get("construction")
    lines = [ln for ln in (ident.get("lines") or []) if isinstance(ln, dict)]
    for line in lines:
        if card_name is not None and line.get("card") != card_name:
            continue
        if line.get("rank") != rank:
            continue
        if construction is not None and line.get("construction") != construction:
            continue
        return line
    ranked = [ln for ln in lines
              if (card_name is None or ln.get("card") == card_name) and ln.get("rank") is not None]
    return min(ranked, key=lambda ln: ln["rank"]) if ranked else None


# ---------------------------------------------------------------------------- public API

def annotate_states(ov: dict, runs: Path) -> dict:
    """Add ``state`` to every line, the best line's state to each typology cell, and
    ``ov["states"] = {state: count}``. Mutates and returns ``ov``; idempotent; never raises."""
    try:
        if not isinstance(ov, dict):
            return ov
        identities = ov.get("identities")
        if not isinstance(identities, list):
            return ov
        runs = Path(runs)
        min_valid = _min_valid(ov)
        widen_ids = _widen_run_ids(runs)
        now = datetime.now(timezone.utc)

        counts = {state: 0 for state in STATE_ORDER}
        for ident in identities:
            if not isinstance(ident, dict):
                continue
            lines = ident.get("lines")
            if not isinstance(lines, list):
                continue
            for line in lines:
                if not isinstance(line, dict):
                    continue
                state = _state_for(line, widen_ids=widen_ids, runs=runs,
                                   min_valid=min_valid, now=now)
                line["state"] = state
                counts[state] = counts.get(state, 0) + 1

        by_id = {str(i.get("id")): i for i in identities if isinstance(i, dict)}
        typology = ov.get("typology")
        if isinstance(typology, list):
            for card in typology:
                if not isinstance(card, dict):
                    continue
                cells = card.get("cells")
                if not isinstance(cells, dict):
                    continue
                for ident_id, cell in cells.items():
                    if not isinstance(cell, dict):
                        continue
                    ident = by_id.get(str(ident_id))
                    if ident is None:
                        continue
                    best = _best_line_for_cell(ident, card.get("card"), cell)
                    if best is not None and isinstance(best.get("state"), str):
                        cell["state"] = best["state"]

        ov["states"] = counts
        return ov
    except Exception:                       # noqa: BLE001 - a partial payload must never break the API
        return ov
