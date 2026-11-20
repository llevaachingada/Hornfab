"""Overview phase 2 (WP2.1): the ranked findings engine behind ``GET /api/overview/findings``.

Pure CPU, read-only over ``runs/``. It takes the phase-1 :func:`data_overview.overview` payload
(no second run scan) and only opens a run's ``search.ndjson`` for the two rules that need rows:
``budget`` (the best-so-far curve of a line's best run) and ``bounds`` (an existing ``walls.json``
proposal, never computed here).

One finding carries exactly one ``identity_id``. J is compared only inside that identity: the
payload already ranks lines per identity, and no rule here ever looks across identities.

``id`` is the first 16 hex of ``sha256(kind|identity_id|line_key|rule_version)`` so it survives a
reload and a process restart. ``apply_state`` is the documented hook for the phase-3.4 state file;
it is a no-op when given ``{}``.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import data as D

RULE_VERSION = "2026-11-19.wp2.1"
STALE_AFTER = timedelta(days=7)
KINDS = ("budget", "refusals", "bounds", "tie_verify", "stale_line", "probe_only", "registry",
         "software")
SEVERITIES = ("critical", "high", "medium", "low")
#: Primary order is the plan's (status, -score). Severity is the documented tie-breaker so a HIGH
#: finding can never sit below a MEDIUM one with the same score in the "Next solves" tab.
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITIES)}


def sort_key(f: dict) -> tuple:
    return (f.get("status") != "open", -(f.get("score") or 0.0),
            SEVERITY_RANK.get(f.get("severity"), len(SEVERITIES)))
STATUSES = ("open", "resolved", "superseded")

_CURRENCY = {"current": 1.0, "unregistered": 0.6, "diagnostic": 0.4, "legacy": 0.1}


# ---------------------------------------------------------------------------- helpers

def _parse_utc(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _finding_id(kind: str, identity_id: str, line_key: str) -> str:
    raw = f"{kind}|{identity_id}|{line_key}|{RULE_VERSION}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _best_so_far(values: list[float]) -> list[float]:
    out: list[float] = []
    best: float | None = None
    for v in values:
        best = v if best is None else min(best, v)
        out.append(best)
    return out


def _valid_objectives(rows: list[dict]) -> list[float]:
    out = []
    for r in rows:
        if not r.get("ok"):
            continue
        obj = r.get("objective")
        if isinstance(obj, bool) or not isinstance(obj, (int, float)):
            continue
        out.append(float(obj))
    return out


def _is_stale(last: str | None, now: datetime) -> bool:
    t = _parse_utc(last)
    return bool(t is not None and (now - t) > STALE_AFTER)


def _first_seen(ident: dict, ln: dict | None) -> str | None:
    """Deterministic stand-in for the phase-3.4 state file: the earliest row time the evidence
    already carries. (The state file will supply the real first-seen once it exists.)"""
    times = []
    if ln is not None:
        times = [r.get("last") for r in ln.get("runs") or [] if r.get("last")]
    else:
        for line in ident.get("lines") or []:
            times += [r.get("last") for r in line.get("runs") or [] if r.get("last")]
    return min(times) if times else None


def _impact(ident: dict, ln: dict | None, identity_level: bool) -> tuple[float, str]:
    label = ident.get("label") or ident.get("id")
    if identity_level:
        return 0.9, "identity-level"
    rank = (ln or {}).get("rank")
    if rank == 1:
        return 1.0, f"rank 1 in {label}"
    if (ln or {}).get("tie"):
        return 0.9, f"tied inside the floor in {label}"
    if rank in (2, 3):
        return 0.7, f"rank {rank} in {label}"
    return 0.4, f"outside the leaderboard in {label}"


def _confidence(n_ok: int, override: float | None = None) -> tuple[float, str]:
    if override is not None:
        return override, "all outcomes count"
    c = min(1.0, max(0, int(n_ok)) / 40.0)
    return c, (f"{n_ok} valid evals" if n_ok < 40 else "40+ valid evals")


def _currency(ident: dict, last: str | None, now: datetime) -> tuple[float, str]:
    c = _CURRENCY.get(str(ident.get("status") or "unregistered"), 0.6)
    stale = _is_stale(last, now)
    if stale:
        c *= 0.5
    why = f"{ident.get('status') or 'unregistered'} score" + (" · stale >7d" if stale else "")
    return c, why


def _make(kind: str, ident: dict, ln: dict | None, severity: str, currency: float,
          why_currency: str, n_ok: int, title: str, detail: str, evidence: list[str], *,
          identity_level: bool = False, status: str = "open",
          resolved_by: str | None = None, subject_type: str | None = None,
          subject: str | None = None, first_seen_utc: str | None = None,
          confidence_override: float | None = None) -> dict:
    impact, impact_txt = _impact(ident, ln, identity_level)
    confidence, confidence_txt = _confidence(n_ok, confidence_override)
    score = round(100.0 * impact * confidence * currency, 1)
    line_key = "" if ln is None else str(ln.get("key") or "")
    ident_id = str(ident.get("id") or "")
    default_subject = (ident.get("label") or ident_id if identity_level else
                       f"{ident.get('label') or ident_id} · {(ln or {}).get('card_label')} "
                       f"{(ln or {}).get('construction')}")
    return {
        "id": _finding_id(kind, ident_id, line_key),
        "kind": kind,
        "subject_type": subject_type or ("identity" if identity_level else "line"),
        "subject": subject or default_subject,
        "identity_id": ident_id,
        "line_key": line_key,
        "severity": severity,
        "score": score,
        "why": [impact_txt, confidence_txt, why_currency],
        "title": title,
        "detail": detail,
        "evidence": evidence,
        "status": status,
        "resolved_by": resolved_by,
        "first_seen_utc": first_seen_utc or _first_seen(ident, ln),
        "href": f"#/overview?tab=leaders&ident={ident_id}",
    }


# ---------------------------------------------------------------------------- rules

def _rule_budget(ident: dict, ln: dict, runs: Path, min_valid: int, now: datetime,
                 rows_cache: dict) -> list[dict]:
    best_id = ln.get("best_run_id")
    if not best_id:
        return []
    rows = rows_cache.get(best_id)
    if rows is None:
        rows = D.read_ndjson(Path(runs) / str(best_id) / "search.ndjson")
        rows_cache[best_id] = rows
    valid = _valid_objectives(rows)
    if not valid:
        return []
    n_ok = int(ln.get("valid") or 0)
    if n_ok < int(min_valid):
        return []
    curve = _best_so_far(valid)
    m = len(curve)
    idx = int(0.8 * (m - 1)) if m > 1 else 0          # 80th-percentile row index
    at80, final = curve[idx], curve[-1]
    if not at80:
        return []
    tail_gain = (at80 - final) / at80
    if tail_gain < 0.01:
        return []
    currency, why_cur = _currency(ident, ln.get("last"), now)

    # R4 fix: a continuation whose first row lands after the best run's last row resolves it.
    resolved_by = None
    best_last = _parse_utc((rows[-1] or {}).get("created_utc")) if rows else None
    if best_last is not None:
        candidates = []
        for r in ln.get("runs") or []:
            rid = r.get("id")
            if not rid or rid == best_id:
                continue
            cand_last = _parse_utc(r.get("last"))
            if cand_last is None or cand_last <= best_last:
                continue
            crows = rows_cache.get(rid)
            if crows is None:
                crows = D.read_ndjson(Path(runs) / str(rid) / "search.ndjson")
                rows_cache[rid] = crows
            first = _parse_utc((crows[0] or {}).get("created_utc")) if crows else None
            if first is not None and first > best_last:
                candidates.append((first, str(rid)))
        if candidates:
            resolved_by = min(candidates)[1]

    pct = round(100.0 * tail_gain, 1)
    status = "resolved" if resolved_by else "open"
    detail = (f"J fell {pct}% after the 80% mark of the best run; "
              + ("a later run in this line continued it — the finding is resolved."
                 if resolved_by else "the line still had budget left."))
    evidence = [f"best run {best_id}: best_j {final:.4f}",
                f"best-so-far at the 80% row ({idx + 1}/{m}): {at80:.4f}",
                f"tail gain {pct}% (open at >=1.0%), {n_ok} valid evals"]
    if resolved_by:
        evidence.append(f"continued by {resolved_by}")
    return [_make("budget", ident, ln, "medium", currency, why_cur, n_ok,
                  f"Budget left on the table: {ln.get('construction')}", detail, evidence,
                  status=status, resolved_by=resolved_by)]


def _rule_refusals(ident: dict, ln: dict, now: datetime) -> list[dict]:
    pct = ln.get("refused_pct")
    if pct is None or float(pct) < 25.0:
        return []
    severity = "high" if float(pct) >= 40.0 else "medium"
    currency, why_cur = _currency(ident, ln.get("last"), now)
    fails = {str(k): int(v or 0) for k, v in (ln.get("failures") or {}).items()}
    top = sorted(fails.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    kinds = ", ".join(f"{k} {v}" for k, v in top) or "no classified failure kind"
    detail = (f"{pct}% of this line's evals were refused"
              + (" (at or above the 40% high line)." if severity == "high"
                 else " (above the 25% open line).")
              + f" Top failure kinds: {kinds}.")
    evidence = [f"{ln.get('refused')} refused of {ln.get('evals')} evals ({pct}%)",
                f"top failures: {kinds}"]
    return [_make("refusals", ident, ln, severity, currency, why_cur,
                  int(ln.get("valid") or 0), f"Refusal rate {pct}%: {ln.get('construction')}",
                  detail, evidence, confidence_override=1.0)]


def _rule_tie_verify(ident: dict, now: datetime) -> list[dict]:
    n_tied = ident.get("n_tied")
    if n_tied is None or int(n_tied) < 2:
        return []
    tied = [l for l in ident.get("lines") or [] if l.get("tie")]
    severity = "high" if ident.get("status") == "current" else "medium"
    currency, why_cur = _currency(ident, ident.get("last"), now)
    n_ok = sum(int(l.get("valid") or 0) for l in ident.get("lines") or [])
    names = ", ".join(str(l.get("construction")) for l in tied)
    evidence = [f"{n_tied} lines inside floor_j {ident.get('floor_j')}",
                f"leader_j {ident.get('leader_j')}, tied: {names}"]
    evidence += [f"{l.get('construction')}: best_j {l.get('best_j')}, gap {l.get('gap')}"
                 for l in tied]
    return [_make("tie_verify", ident, None, severity, currency, why_cur, n_ok,
                  f"{n_tied} lines inside one floor",
                  "Rank them with verify solves on the same grid, not more screen evals.",
                  evidence, identity_level=True)]


def _rule_stale_line(ident: dict, ln: dict, now: datetime) -> list[dict]:
    rank = ln.get("rank")
    if ident.get("status") != "current" or rank is None or int(rank) > 3:
        return []
    last = ln.get("last")
    if not _is_stale(last, now):
        return []
    currency, why_cur = _currency(ident, last, now)
    last_dt = _parse_utc(last)
    days = (now - last_dt).days if last_dt is not None else None
    evidence = [f"last row {last}" + (f" ({days} days ago)" if days is not None else ""),
                f"rank {rank} of {sum(1 for l in ident.get('lines') or [] if l.get('rank'))}"]
    return [_make("stale_line", ident, ln, "low", currency, why_cur,
                  int(ln.get("valid") or 0),
                  f"Top-3 line is {days if days is not None else '7+'} days old",
                  "A top line has not moved in over 7 days; confirm it is finished or resume it.",
                  evidence)]


def _rule_probe_only(ident: dict, ln: dict, now: datetime, min_valid: int) -> list[dict]:
    if not ln.get("probe_only") or len(ln.get("runs") or []) < 2:
        return []
    currency, why_cur = _currency(ident, ln.get("last"), now)
    evidence = [f"{len(ln.get('runs') or [])} runs, best n_ok {ln.get('valid')}",
                f"leaderboard minimum {min_valid} valid evals"]
    return [_make("probe_only", ident, ln, "low", currency, why_cur,
                  int(ln.get("valid") or 0),
                  f"Probe-only line: {ln.get('construction')}",
                  f"Never reached the leaderboard minimum of {min_valid} valid evals.",
                  evidence)]


def _rule_registry(ident: dict, now: datetime, registry_path: str) -> list[dict]:
    if ident.get("status") != "unregistered" or int(ident.get("evals") or 0) < 100:
        return []
    currency, why_cur = _currency(ident, ident.get("last"), now)
    evidence = [f"{ident.get('evals')} evals, status unregistered",
                f"add it to {registry_path} with its floor_j"]
    return [_make("registry", ident, None, "medium", currency, why_cur,
                  int(ident.get("evals") or 0),
                  f"Unregistered score identity: {ident.get('label')}",
                  "Add it to score_identities.yaml with its floor so its J can be ranked.",
                  evidence, identity_level=True, confidence_override=1.0)]


def _walls_index(runs: Path) -> dict[str, list[Path]]:
    """``best run id -> walls.json paths`` from an existing analysis tree; never computed here."""
    out: dict[str, list[Path]] = {}
    base = Path(runs) / "analysis"
    if not base.is_dir():
        return out
    try:
        paths = list(base.rglob("walls.json"))
    except OSError:
        return out
    for p in paths:
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        run_dir = str(payload.get("run_dir") or "")
        rid = Path(run_dir.replace("\\", "/")).name
        if rid:
            out.setdefault(rid, []).append(p)
    return out


def _rule_bounds(ident: dict, ln: dict, runs: Path, walls: dict, now: datetime) -> list[dict]:
    best_id = ln.get("best_run_id")
    if not best_id:
        return []
    paths = walls.get(str(best_id)) or []
    if not paths:
        return []
    currency, why_cur = _currency(ident, ln.get("last"), now)
    for p in paths:
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        widen = [x for x in payload.get("proposal") or []
                 if str(x.get("action") or "").startswith("widen")]
        if not widen:
            continue
        keys = ", ".join(str(x.get("key")) for x in widen)
        evidence = [f"walls proposal: {p}", f"widen candidates: {keys}"]
        evidence += [f"{x.get('action')} {x.get('key')} -> [{x.get('new_lo')}, {x.get('new_hi')}]"
                     for x in widen]
        return [_make("bounds", ident, ln, "medium", currency, why_cur,
                      int(ln.get("valid") or 0),
                      f"Bound walls: {ln.get('construction')}",
                      f"Existing walls analysis widens {len(widen)} bound(s): {keys}.",
                      evidence)]
    return []


# ---------------------------------------------------------------------------- engine

def findings(ov: dict, runs: Path) -> list[dict]:
    """Ranked findings from the phase-1 overview payload (``runs`` is only for ndjson reads)."""
    now = datetime.now(timezone.utc)
    min_valid = int(((ov.get("registry") or {}).get("min_valid_for_leader")) or 10)
    registry_path = str((ov.get("registry") or {}).get("path") or "examples/score_identities.yaml")
    rows_cache: dict[str, list[dict]] = {}
    walls: dict[str, list[Path]] | None = None
    out: list[dict] = []

    for ident in ov.get("identities") or []:
        out += _rule_tie_verify(ident, now)
        out += _rule_registry(ident, now, registry_path)
        for ln in ident.get("lines") or []:
            if ln.get("rank") is not None:
                out += _rule_budget(ident, ln, runs, min_valid, now, rows_cache)
            out += _rule_refusals(ident, ln, now)
            out += _rule_stale_line(ident, ln, now)
            out += _rule_probe_only(ident, ln, now, min_valid)
            if ln.get("best_run_id"):
                if walls is None:
                    walls = _walls_index(runs)
                out += _rule_bounds(ident, ln, runs, walls, now)

    # one finding per (kind, identity_id, line_key)
    deduped: dict[tuple, dict] = {}
    for f in out:
        deduped.setdefault((f["kind"], f["identity_id"], f["line_key"]), f)
    ranked = sorted(deduped.values(), key=sort_key)
    return D.clean(ranked)


def apply_state(findings_list: list[dict], state_dict: dict) -> list[dict]:
    """Merge the phase-3.4 state file (finding id -> ``{status, resolved_by}``).

    Documented hook only: the state file does not exist yet, so ``{}`` is a no-op and the findings
    above are returned unchanged. Statuses outside the finding vocabulary are ignored, never
    guessed.
    """
    if not state_dict:
        return findings_list
    allowed = set(STATUSES) | {"dismissed", "acknowledged"}
    for f in findings_list:
        if f.get("status") == "resolved":
            continue                       # a computed resolution always outranks a stored state
        st = state_dict.get(f.get("id")) or {}
        if not isinstance(st, dict):
            continue
        status = st.get("status")
        if status in allowed:
            f["status"] = status
        if st.get("resolved_by"):
            f["resolved_by"] = st["resolved_by"]
    return findings_list
