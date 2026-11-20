"""Overview WP3.3 — software health as ranked findings (``GET /api/overview/health``).

Five read-only sources become zero-or-more ``kind: "software"`` findings with the same shape,
severity words and score vocabulary as :mod:`data_overview_findings`:

1. refusal kinds aggregated per **identity** (a line knows its own ``failures``; the identity view
   sums them) - a finding when the identity's refused share is >= 25 % or its dominant failure
   kind is not solver-related;
2. repeated ``solve_failed`` rows on the best run of a ranked line (>= 2 rows, grouped per run);
3. alerted solve lanes (``ov["lanes"]["lanes"][i]["alert"]``);
4. analysis report sets with section errors (``data.analysis_sets`` ``n_errors > 0``);
5. registry errors - the score-identity registry's own error plus every project/HW loader error.

Every finding carries exactly one ``identity_id``: the identity's id when the source names one,
otherwise ``""``. Nothing here compares J across identities. A missing source (no runs dir, no
lanes, no analysis tree, a loader that raises) is an empty list, never an error. ``id`` reuses the
findings engine's stable recipe (:func:`data_overview_findings._finding_id`); for a software
finding the third hash slot is the subject key (``refusals``, ``solver:<run>``, ``lane:<lane>``,
``analysis:<set>``, ``registry:<message>``), so ids stay unique across the five sources.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from . import data as D
from .data_overview_findings import (
    _confidence,
    _currency,
    _finding_id,
    _first_seen,
    _impact,
    sort_key,
)

KIND = "software"


# ---------------------------------------------------------------------------- helpers

def _is_solver_kind(kind: str | None) -> bool:
    k = str(kind or "").lower()
    return k.startswith("solve") or "solver" in k


def _mentions_solve_failed(row: dict) -> bool:
    if "solve_failed" in str(row.get("error") or ""):
        return True
    fails = row.get("failures")
    return isinstance(fails, dict) and any("solve_failed" in str(k) for k in fails)


def _system_score(impact: float = 0.9) -> float:
    """Lanes, analysis sets and registry errors are definitive facts: full confidence/currency."""
    return round(100.0 * impact * 1.0 * 1.0, 1)


def _make(*, ident_id: str, subject_key: str, subject_type: str, subject: str, severity: str,
          score: float, why: list[str], title: str, detail: str, evidence: list[str], href: str,
          first_seen_utc: str | None = None, status: str = "open",
          resolved_by: str | None = None) -> dict:
    return D.clean({
        "id": _finding_id(KIND, ident_id, subject_key),
        "kind": KIND,
        "subject_type": subject_type,
        "subject": subject,
        "identity_id": ident_id,
        "line_key": subject_key,
        "severity": severity,
        "score": score,
        "why": why,
        "title": title,
        "detail": detail,
        "evidence": evidence,
        "status": status,
        "resolved_by": resolved_by,
        "first_seen_utc": first_seen_utc,
        "href": href,
    })


def _identity_fails(ident: dict) -> tuple[int, int, dict[str, int]]:
    lines = ident.get("lines") or []
    evals = sum(int(ln.get("evals") or 0) for ln in lines)
    refused = sum(int(ln.get("refused") or 0) for ln in lines)
    fails: dict[str, int] = {}
    for ln in lines:
        for k, v in (ln.get("failures") or {}).items():
            fails[str(k)] = fails.get(str(k), 0) + int(v or 0)
    return evals, refused, fails


# ---------------------------------------------------------------------------- sources

def _refusal_findings(ident: dict, now: datetime) -> list[dict]:
    evals, refused, fails = _identity_fails(ident)
    ranked = sorted(fails.items(), key=lambda kv: (-kv[1], kv[0]))
    dominant = ranked[0][0] if ranked else None
    pct = round(100.0 * refused / evals, 1) if evals else None
    high_rate = pct is not None and pct >= 25.0
    non_solver = bool(dominant and not _is_solver_kind(dominant))
    if not (high_rate or non_solver):
        return []
    severity = "high" if (pct is not None and pct >= 40.0) else "medium"
    currency, why_cur = _currency(ident, ident.get("last"), now)
    _, why_conf = _confidence(0, 1.0)
    kinds = ", ".join(f"{k} {v}" for k, v in ranked[:3]) or "no classified failure kind"
    ident_id = str(ident.get("id") or "")
    label = ident.get("label") or ident_id
    parts = []
    if pct is not None and high_rate:
        parts.append(f"{pct}% of this identity's evals were refused"
                     + (" (at or above the 40% high line)." if severity == "high"
                        else " (above the 25% open line)."))
    if non_solver:
        parts.append(f"The dominant failure kind {dominant!r} is not solver-related.")
    detail = " ".join(parts) + f" Top failure kinds: {kinds}."
    # The kinds are already spelled out in ``detail``; evidence carries only the counts, so a
    # reader never sees the same sentence twice (visual QA 2026-11-20).
    evidence = [f"{refused} refused of {evals} evals across {len(ident.get('lines') or [])} line(s)"]
    return [_make(
        ident_id=ident_id, subject_key="refusals", subject_type="identity",
        subject=label, severity=severity,
        score=round(100.0 * 0.9 * 1.0 * currency, 1),
        why=["identity-level", why_conf, why_cur],
        title=f"Refusals in {label}", detail=detail, evidence=evidence,
        href=f"#/overview?tab=leaders&ident={ident_id}",
        first_seen_utc=_first_seen(ident, None),
    )]


def _solver_findings(ident: dict, runs: Path, now: datetime,
                     rows_cache: dict[str, list[dict]]) -> list[dict]:
    out: list[dict] = []
    for ln in ident.get("lines") or []:
        if ln.get("rank") is None:
            continue
        rid = ln.get("best_run_id")
        if not rid:
            continue
        rows = rows_cache.get(rid)
        if rows is None:
            rows = D.read_ndjson(Path(runs) / str(rid) / "search.ndjson")
            rows_cache[rid] = rows
        n = sum(1 for r in rows if isinstance(r, dict) and _mentions_solve_failed(r))
        if n < 2:
            continue
        currency, why_cur = _currency(ident, ln.get("last"), now)
        impact, impact_txt = _impact(ident, ln, False)
        _, why_conf = _confidence(0, 1.0)
        label = ident.get("label") or ident.get("id") or ""
        run_name = ln.get("best_run_name") or rid
        out.append(_make(
            ident_id=str(ident.get("id") or ""), subject_key=f"solver:{rid}",
            subject_type="run", subject=str(rid), severity="high",
            score=round(100.0 * impact * 1.0 * currency, 1),
            why=[impact_txt, why_conf, why_cur],
            title=f"Repeated solver failures in {run_name}",
            detail=(f"{n} rows of this run report solve_failed; the best run of the "
                    f"{ln.get('construction') or 'line'} line under {label} is not healthily "
                    f"converging."),
            evidence=[f"{n} solve_failed row(s) in {rid}",
                      f"line {ln.get('key')} rank {ln.get('rank')}, best_j {ln.get('best_j')}"],
            href=f"#/run/{rid}",
            first_seen_utc=_first_seen(ident, ln),
        ))
    return out


def _lane_findings(ov: dict) -> list[dict]:
    lanes = ov.get("lanes")
    if not isinstance(lanes, dict):
        return []
    out: list[dict] = []
    for entry in lanes.get("lanes") or []:
        if not isinstance(entry, dict):
            continue
        alert = entry.get("alert")
        if not isinstance(alert, dict):
            continue
        lane = str(entry.get("lane") or "?")
        reason = str(alert.get("reason") or "lane alert")
        out.append(_make(
            ident_id="", subject_key=f"lane:{lane}", subject_type="lane",
            subject=f"Lane {lane}", severity="high", score=_system_score(),
            why=["system-level", "all outcomes count", "current state"],
            title=f"Solve lane {lane} stalled",
            detail=reason,
            evidence=[f"lane {lane}: {reason}"],
            href="#/overview?tab=decisions",
        ))
    return out


def _analysis_findings(runs: Path | None) -> list[dict]:
    if runs is None:
        return []
    try:
        sets = D.analysis_sets(Path(runs) / "analysis")
    except Exception:                       # noqa: BLE001 - a missing/broken tree is empty, not fatal
        return []
    out: list[dict] = []
    for s in sets:
        n_errors = int(s.get("n_errors") or 0)
        if n_errors <= 0:
            continue
        sid = str(s.get("id") or ".")
        out.append(_make(
            ident_id="", subject_key=f"analysis:{sid}", subject_type="analysis",
            subject=f"Analysis set {sid}", severity="medium", score=_system_score(),
            why=["system-level", "all outcomes count", "current state"],
            title=f"{n_errors} analysis section error(s) in {sid}",
            detail=(f"{n_errors} of this report set's {int(s.get('n_sections') or 0)} section(s) "
                    f"finished with status error; the report is incomplete."),
            evidence=[f"report set {sid}: n_errors {n_errors}, "
                      f"n_sections {int(s.get('n_sections') or 0)}"],
            href=f"#/analysis/{sid}",
            first_seen_utc=str(s.get("generated_utc") or "") or None,
        ))
    return out


def _registry_findings(ov: dict, root: Path) -> list[dict]:
    messages: list[str] = []
    reg = ov.get("registry")
    if isinstance(reg, dict) and reg.get("error"):
        messages.append(str(reg["error"]))
    try:
        from . import data_overview_registry as RG
        project = RG.load_project_registry(Path(root))
        messages += [str(e) for e in (project.get("errors") or []) if e]
    except Exception:                       # noqa: BLE001 - a loader failure is not a health crash
        pass
    out: list[dict] = []
    seen: set[str] = set()
    for msg in messages:
        if msg in seen:
            continue
        seen.add(msg)
        out.append(_make(
            ident_id="", subject_key=f"registry:{msg}", subject_type="registry",
            subject=msg, severity="critical", score=_system_score(),
            why=["system-level", "all outcomes count", "current state"],
            title="Registry load error",
            detail=msg,
            evidence=[msg],
            href="#/overview?tab=decisions",
        ))
    return out


# ---------------------------------------------------------------------------- engine

def health_findings(ov: dict, root: Path, runs: Path | None = None) -> list[dict]:
    """Software-health findings from the phase-1 overview payload.

    ``root`` locates the registry files; ``runs`` (optional) locates run ndjson and the analysis
    tree. Missing sources simply contribute nothing.
    """
    ov = ov or {}
    now = datetime.now(timezone.utc)
    rows_cache: dict[str, list[dict]] = {}
    out: list[dict] = []

    for ident in ov.get("identities") or []:
        if not isinstance(ident, dict):
            continue
        out += _refusal_findings(ident, now)
        if runs is not None:
            out += _solver_findings(ident, Path(runs), now, rows_cache)

    out += _lane_findings(ov)
    out += _analysis_findings(runs)
    out += _registry_findings(ov, Path(root))

    # one finding per (kind, subject); the findings engine's ordering: open first, then score.
    deduped: dict[tuple, dict] = {}
    for f in out:
        deduped.setdefault((f["kind"], f["subject"]), f)
    ranked = sorted(deduped.values(), key=sort_key)
    return D.clean(ranked)
