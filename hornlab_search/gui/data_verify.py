"""Verify-view data layer for the GUI (WP1).

Public API (called from server.py):
  verify_sources(runs, run_id) -> list[dict] | dict
  verify_report(runs, run_id, root) -> dict          (section 6 shape)
  design_payload(runs, run_id, h, tier) -> dict

Do not import tools/.  No GPU, no solver.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path, PurePosixPath, PureWindowsPath

import numpy as np

# ── re-use helpers from data.py without circular imports ─────────────────────
from .data import (
    HASH,
    RUN_ID,
    _as_dict,
    _read_json,
    _run_dirs,
    _spearman,
    clean,
    design_curves,
    read_ndjson,
    run_gate_audit,
    run_objective_version,
)

# ── module-level scan cache ────────────────────────────────────────────────────
# key: (runs_dir_mtime_ns, ) → list of (run_dir, run.json dict) for verify runs
_VERIFY_SCAN_CACHE: dict[tuple, list[tuple[Path, dict]]] = {}


def _runs_mtime(runs: Path) -> int:
    try:
        return int(runs.stat().st_mtime_ns)
    except OSError:
        return 0


def _scan_verify_runs(runs: Path) -> list[tuple[Path, dict]]:
    """Return list of (run_dir, run_json_dict) for all runs with mode=='verify'."""
    key = (_runs_mtime(runs),)
    hit = _VERIFY_SCAN_CACHE.get(key)
    if hit is not None:
        return hit
    result = []
    for d in _run_dirs(runs):
        rj = _as_dict(_read_json(d / "run.json"))
        if rj.get("mode") == "verify":
            result.append((d, rj))
    _VERIFY_SCAN_CACHE.clear()   # keep at most one entry
    _VERIFY_SCAN_CACHE[key] = result
    return result


def _match_parent(verify_of_run: str, run_id: str, runs: Path) -> bool:
    """True when verify_of.run refers to run_id (abs path or basename match)."""
    candidate = Path(verify_of_run)
    # Absolute path match (resolved)
    target = runs / run_id
    try:
        if candidate.resolve() == target.resolve():
            return True
    except (OSError, ValueError):
        pass
    # Windows absolute path: basename fallback
    try:
        if PureWindowsPath(verify_of_run).name == run_id:
            return True
    except (ValueError, TypeError):
        pass
    # Posix basename fallback
    try:
        if PurePosixPath(verify_of_run).name == run_id:
            return True
    except (ValueError, TypeError):
        pass
    return False


def _parse_utc(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def _newest_utc(rows: list[dict]) -> str | None:
    dates = [_parse_utc(r.get("created_utc")) for r in rows]
    valid = [d for d in dates if d is not None]
    if not valid:
        return None
    return max(valid).strftime("%Y-%m-%dT%H:%M:%SZ")


def _source_status(rows: list[dict], ndjson_path: Path) -> str:
    """Heuristic run status from the ndjson's age and content."""
    if not rows:
        return "none"
    newest = _parse_utc(_newest_utc(rows))
    if newest is None:
        return "finished"
    age = dt.datetime.now(tz=dt.timezone.utc) - newest
    if age.total_seconds() < 1800:
        return "possibly_running"
    return "finished"


# ── verify_sources ─────────────────────────────────────────────────────────────

def verify_sources(runs: Path, run_id: str) -> list[dict] | dict:
    """Return verify-data sources for one run.

    For a **linked** verify run (run_id itself has mode=='verify' with
    verify_of), returns a redirect dict instead of a list.

    For other runs returns a list (possibly empty) of source dicts.
    """
    if not RUN_ID.match(run_id):
        raise ValueError(f"not a run id: {run_id!r}")

    run_dir = runs / run_id

    # Is run_id itself a verify run?
    rj = _as_dict(_read_json(run_dir / "run.json"))
    if rj.get("mode") == "verify" and "verify_of" in rj:
        # Layout B: linked verify run
        vo = _as_dict(rj.get("verify_of"))
        vo_run = vo.get("run") or ""
        # Try to find parent in this runs folder
        parent_id = None
        for d in _run_dirs(runs):
            if _match_parent(vo_run, d.name, runs):
                parent_id = d.name
                break
        parent_missing = parent_id is None
        if not parent_missing and not (runs / parent_id / "search.ndjson").exists():
            parent_missing = True
            parent_id = None
        return {"redirect_to": parent_id, "parent_missing": parent_missing}

    sources = []

    # Layout A: inline verify
    inline_ndjson = run_dir / "verify" / "search.ndjson"
    if inline_ndjson.is_file():
        rows = read_ndjson(inline_ndjson)
        sources.append({
            "kind": "inline",
            "path": f"runs/{run_id}/verify/search.ndjson",
            "run_id": run_id,
            "n_rows": len(rows),
            "newest_row_utc": _newest_utc(rows),
            "status": _source_status(rows, inline_ndjson),
        })

    # Layout B: linked verify runs that point at this run
    for vdir, vrj in _scan_verify_runs(runs):
        vo = _as_dict(vrj.get("verify_of"))
        if _match_parent(vo.get("run") or "", run_id, runs):
            rows = read_ndjson(vdir / "search.ndjson")
            sources.append({
                "kind": "linked",
                "path": f"runs/{vdir.name}/search.ndjson",
                "run_id": vdir.name,
                "n_rows": len(rows),
                "newest_row_utc": _newest_utc(rows),
                "status": vrj.get("status") or _source_status(rows, vdir / "search.ndjson"),
            })

    # Layout C: run_id itself is mode=='verify' WITHOUT verify_of (standalone)
    if rj.get("mode") == "verify" and "verify_of" not in rj:
        rows = read_ndjson(run_dir / "search.ndjson")
        sources.append({
            "kind": "standalone",
            "path": f"runs/{run_id}/search.ndjson",
            "run_id": run_id,
            "n_rows": len(rows),
            "newest_row_utc": _newest_utc(rows),
            "status": rj.get("status") or _source_status(rows, run_dir / "search.ndjson"),
        })

    return sources


# ── design directory resolver ─────────────────────────────────────────────────

def _design_dir(runs: Path, run_id: str, h: str, tier: str) -> Path:
    """Return the design dir for one hash/tier combo.

    tier='screen'  → runs/<run_id>/designs/<h>/
    tier='verify'  → inline: runs/<run_id>/verify/designs/<h>/
                     linked/standalone: runs/<source_run_id>/designs/<h>/
    """
    if tier not in ("screen", "verify"):
        raise ValueError(f"unknown tier {tier!r}; must be 'screen' or 'verify'")
    if not HASH.match(h):
        raise ValueError(f"not a design hash: {h!r}")
    run_dir = runs / run_id

    if tier == "screen":
        return run_dir / "designs" / h

    # tier == "verify"
    inline = run_dir / "verify" / "designs" / h
    if inline.parent.exists():
        return inline

    # linked or standalone: the design is under the verify run's own designs/
    rj = _as_dict(_read_json(run_dir / "run.json"))
    if rj.get("mode") == "verify":
        return run_dir / "designs" / h

    # Find among linked verify sources
    for vdir, _vrj in _scan_verify_runs(runs):
        vo = _as_dict(_vrj.get("verify_of"))
        if _match_parent(vo.get("run") or "", run_id, runs):
            d = vdir / "designs" / h
            if (d / "metrics.json").exists():
                return d

    # fallback: inline path (may not exist; callers check)
    return inline


# ── density reader ─────────────────────────────────────────────────────────────

def _density(design_dir: Path, row: dict | None = None) -> dict | None:
    """Read density fields from metrics.json + response.npz + the ndjson row."""
    m = _read_json(design_dir / "metrics.json")
    if m is None:
        return None
    n_freqs = len(m.get("freqs_hz") or []) or None
    balloon_grid = None
    n_points = None
    p = design_dir / "response.npz"
    if p.is_file():
        try:
            with np.load(str(p), allow_pickle=False) as z:
                meta_raw = z.get("meta", None)
                if meta_raw is not None:
                    meta = json.loads(str(meta_raw))
                    bg = meta.get("balloon_grid")
                    if isinstance(bg, list) and len(bg) == 2:
                        balloon_grid = bg
                        n_points = bg[0] * bg[1]
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            pass
    out: dict = {}
    if n_freqs is not None:
        out["n_freqs"] = n_freqs
    if balloon_grid is not None:
        out["balloon_grid"] = balloon_grid
    if n_points is not None:
        out["n_points"] = n_points
    return out or None


# ── comparability check ────────────────────────────────────────────────────────

def _metrics_band(design_dir: Path) -> tuple[float | None, float | None]:
    """Min and max Hz from metrics.json freqs_hz, or (None, None) when unavailable."""
    m = _read_json(design_dir / "metrics.json")
    if m is None:
        return None, None
    freqs = m.get("freqs_hz")
    if not isinstance(freqs, list) or not freqs:
        return None, None
    try:
        vals = [float(f) for f in freqs if f is not None]
        return (min(vals), max(vals)) if vals else (None, None)
    except (TypeError, ValueError):
        return None, None


def _comparability(screen_rows: list[dict], verify_rows: list[dict],
                   screen_cfg: dict, verify_cfg: dict | None,
                   screen_design_dirs: list[Path] | None = None,
                   verify_design_dirs: list[Path] | None = None) -> tuple[bool, str | None]:
    """Return (comparable, reason_or_None).

    ``screen_design_dirs`` / ``verify_design_dirs`` are sampled to read the actual
    solved frequency bands from metrics.json when config/row band fields are absent.
    """
    if verify_cfg is None:
        verify_cfg = {}

    # Check objective version
    def _obj_ver(cfg: dict) -> int | None:
        obj = _as_dict(cfg.get("objective")) or _as_dict(
            _as_dict(cfg.get("brief")).get("objective"))
        v = obj.get("version")
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    sv = _obj_ver(screen_cfg)
    vv = _obj_ver(verify_cfg)
    if sv is not None and vv is not None and sv != vv:
        return False, f"different objective versions (screen v{sv}, verify v{vv})"

    # Check band via config targets
    def _band(cfg: dict) -> tuple[int | None, int | None]:
        tgt = _as_dict(cfg.get("target")) or _as_dict(
            _as_dict(cfg.get("brief")).get("target"))
        try:
            lo = int(tgt["band_lo_hz"]) if "band_lo_hz" in tgt else None
            hi = int(tgt["band_hi_hz"]) if "band_hi_hz" in tgt else None
        except (TypeError, ValueError):
            lo, hi = None, None
        return lo, hi

    sb = _band(screen_cfg)
    vb = _band(verify_cfg)
    if None not in sb and None not in vb and sb != vb:
        return False, f"different bands (screen {sb[0]}–{sb[1]} Hz, verify {vb[0]}–{vb[1]} Hz)"

    # Check via ndjson row band fields (more reliable if config is absent)
    def _row_band(rows: list[dict]) -> tuple[int | None, int | None]:
        for r in rows:
            lo_r = r.get("band_lo_hz")
            hi_r = r.get("band_hi_hz")
            if lo_r is not None and hi_r is not None:
                try:
                    return int(lo_r), int(hi_r)
                except (TypeError, ValueError):
                    pass
        return None, None

    srb = _row_band(screen_rows)
    vrb = _row_band(verify_rows)
    if None not in srb and None not in vrb and srb != vrb:
        return False, f"different bands (screen {srb[0]}–{srb[1]} Hz, verify {vrb[0]}–{vrb[1]} Hz)"

    # Compare actual solved frequency ranges from metrics.json.
    # When both a screen target band and a verify metrics range are known, they
    # must overlap and have the same approximate extremes (within ±20 % of range).
    screen_band_lo, screen_band_hi = sb  # from config target (most authoritative)
    if screen_band_lo is None:           # fall back to screen metrics
        for sd in (screen_design_dirs or []):
            slo, shi = _metrics_band(sd)
            if slo is not None:
                screen_band_lo, screen_band_hi = slo, shi
                break

    if screen_band_lo is not None and verify_design_dirs:
        for vd in verify_design_dirs:
            vlo, vhi = _metrics_band(vd)
            if vlo is not None:
                # Tolerance: 15 % of the screen band's total span
                tol = max(50.0, (screen_band_hi - screen_band_lo) * 0.15
                          if screen_band_hi is not None else 50.0)
                lo_ok = abs(vlo - screen_band_lo) <= tol
                hi_ok = (vhi is None or screen_band_hi is None
                         or abs(vhi - screen_band_hi) <= tol)
                if not (lo_ok and hi_ok):
                    s_desc = (f"{int(screen_band_lo)}–{int(screen_band_hi)} Hz"
                              if screen_band_hi is not None
                              else f"{int(screen_band_lo)}+ Hz")
                    v_desc = (f"{int(vlo)}–{int(vhi)} Hz"
                              if vhi is not None else f"{int(vlo)}+ Hz")
                    return False, f"different bands (screen {s_desc}, verify {v_desc})"
                break  # one sample is enough

    return True, None


# ── verify_report ──────────────────────────────────────────────────────────────

def verify_report(runs: Path, run_id: str, root: Path) -> dict:
    """Full verify report for one run (section 6 shape).

    Raises FileNotFoundError when the run does not exist in this runs folder.
    """
    if not RUN_ID.match(run_id):
        raise ValueError(f"not a run id: {run_id!r}")

    run_dir = runs / run_id
    if not run_dir.is_dir():
        raise FileNotFoundError(run_id)

    rj = _as_dict(_read_json(run_dir / "run.json"))

    # ── Handle linked verify run: redirect ───────────────────────────────────
    if rj.get("mode") == "verify" and "verify_of" in rj:
        vo = _as_dict(rj.get("verify_of"))
        vo_run = vo.get("run") or ""
        parent_id: str | None = None
        for d in _run_dirs(runs):
            if _match_parent(vo_run, d.name, runs):
                parent_id = d.name
                break
        parent_missing = (parent_id is None
                          or not (runs / parent_id / "search.ndjson").exists())
        if parent_missing:
            parent_id = None

        # For a redirect, build a minimal report pointing to parent
        return clean({
            "run_id": run_id,
            "name": _as_dict(_read_json(run_dir / "config.yaml")).get("name"),
            "kind": "redirect",
            "redirect_to": parent_id,
            "parent_missing": parent_missing,
            "objective_version": run_objective_version(run_dir),
            "band_hz": None,
            "sources": [],
            "state": rj.get("status") or "finished",
            "comparable": False,
            "comparable_reason": "linked verify run — open the parent run",
            "latest_only": False,
            "fidelity": {},
            "summary": None,
            "gate_audit": {"available": False},
            "rows": [],
        })

    # ── Load screen rows ──────────────────────────────────────────────────────
    screen_ndjson = run_dir / "search.ndjson"
    if not screen_ndjson.is_file():
        raise FileNotFoundError(run_id)

    all_screen_rows = read_ndjson(screen_ndjson)
    is_standalone = (rj.get("mode") == "verify" and "verify_of" not in rj)

    if is_standalone:
        # Layout C: single-design verification; no pairing
        screen_rows_ok: list[dict] = []
        verify_sources_list = [{"kind": "standalone",
                                 "path": f"runs/{run_id}/search.ndjson",
                                 "run_id": run_id,
                                 "n_rows": len(all_screen_rows),
                                 "newest_row_utc": _newest_utc(all_screen_rows),
                                 "status": rj.get("status") or _source_status(
                                     all_screen_rows, screen_ndjson)}]
        verify_all_rows = all_screen_rows
        source_run_id_for_hash: dict[str, str] = {
            str(r.get("design_hash", "")): run_id for r in all_screen_rows}
        source_kind_for_hash: dict[str, str] = {
            str(r.get("design_hash", "")): "standalone" for r in all_screen_rows}
        kind = "standalone"
    else:
        # Normal screen run with zero or more verify sources
        screen_rows_ok = [r for r in all_screen_rows
                          if r.get("ok") and r.get("mode") != "verify"]

        # Collect verify rows from all sources
        verify_all_rows = []
        source_run_id_for_hash: dict[str, str] = {}
        source_kind_for_hash: dict[str, str] = {}
        verify_sources_list = []

        # Inline verify
        inline_ndjson = run_dir / "verify" / "search.ndjson"
        if inline_ndjson.is_file():
            inline_rows = read_ndjson(inline_ndjson)
            for r in inline_rows:
                h = str(r.get("design_hash") or "")
                source_run_id_for_hash[h] = run_id
                source_kind_for_hash[h] = "inline"
            verify_all_rows.extend(inline_rows)
            verify_sources_list.append({
                "kind": "inline",
                "path": f"runs/{run_id}/verify/search.ndjson",
                "run_id": run_id,
                "n_rows": len(inline_rows),
                "newest_row_utc": _newest_utc(inline_rows),
                "status": _source_status(inline_rows, inline_ndjson),
            })

        # Linked verify runs
        for vdir, vrj in _scan_verify_runs(runs):
            vo = _as_dict(vrj.get("verify_of"))
            if _match_parent(vo.get("run") or "", run_id, runs):
                linked_rows = read_ndjson(vdir / "search.ndjson")
                for r in linked_rows:
                    h = str(r.get("design_hash") or "")
                    source_run_id_for_hash[h] = vdir.name
                    source_kind_for_hash[h] = "linked"
                verify_all_rows.extend(linked_rows)
                verify_sources_list.append({
                    "kind": "linked",
                    "path": f"runs/{vdir.name}/search.ndjson",
                    "run_id": vdir.name,
                    "n_rows": len(linked_rows),
                    "newest_row_utc": _newest_utc(linked_rows),
                    "status": vrj.get("status") or _source_status(
                        linked_rows, vdir / "search.ndjson"),
                })

        kind = "pairs" if verify_all_rows else "none"

    # ── Pairing: deduplicate by hash, keep highest n (tie: newest created_utc) ──
    # Per design hash, keep only the row with the highest `n`;
    # if n is equal, keep the one with the newest created_utc.
    best_verify: dict[str, dict] = {}
    had_dupes = False
    for r in verify_all_rows:
        h = str(r.get("design_hash") or "")
        if not h:
            continue
        prev = best_verify.get(h)
        if prev is None:
            best_verify[h] = r
        else:
            # Compare by n first
            n_new = r.get("n") if r.get("n") is not None else -1
            n_old = prev.get("n") if prev.get("n") is not None else -1
            if n_new > n_old:
                best_verify[h] = r
                had_dupes = True
            elif n_new == n_old:
                # Tie: newest wins
                ts_new = _parse_utc(r.get("created_utc"))
                ts_old = _parse_utc(prev.get("created_utc"))
                if ts_new and ts_old and ts_new > ts_old:
                    best_verify[h] = r
                    had_dupes = True
            else:
                had_dupes = True  # the new row is older/lower n; we dropped it

    deduped_verify = list(best_verify.values())

    # ── Build screen lookup by hash ───────────────────────────────────────────
    # Keep only ok screen rows; best-J per hash
    best_screen: dict[str, dict] = {}
    for r in screen_rows_ok:
        h = str(r.get("design_hash") or "")
        if not h:
            continue
        prev = best_screen.get(h)
        if prev is None:
            best_screen[h] = r
        else:
            new_j = r.get("objective")
            old_j = prev.get("objective")
            if new_j is not None and (old_j is None or new_j < old_j):
                best_screen[h] = r

    # ── Comparability ─────────────────────────────────────────────────────────
    screen_cfg = _as_dict(_read_json(run_dir / "config.yaml")) or {}
    # Try to load verify config from inline verify (there may not be one)
    verify_cfg: dict | None = None
    if not is_standalone:
        for src in verify_sources_list:
            if src["kind"] == "linked":
                vcfg_path = runs / src["run_id"] / "config.yaml"
                try:
                    import yaml
                    verify_cfg = yaml.safe_load(vcfg_path.read_text(encoding="utf-8")) or {}
                except (OSError, Exception):
                    pass
                break

    # Collect sample design dirs for metrics-based band comparison
    _screen_dirs: list[Path] = []
    _verify_dirs: list[Path] = []
    for h in list(best_screen.keys())[:3]:
        _d = run_dir / "designs" / h
        if (_d / "metrics.json").exists():
            _screen_dirs.append(_d)
    for r in deduped_verify[:3]:
        _h = str(r.get("design_hash") or "")
        if not _h:
            continue
        _sk = source_kind_for_hash.get(_h, "inline")
        _sr = source_run_id_for_hash.get(_h, run_id)
        if is_standalone:
            _vd = run_dir / "designs" / _h
        elif _sk == "inline":
            _vd = run_dir / "verify" / "designs" / _h
        elif _sk == "linked":
            _vd = runs / _sr / "designs" / _h
        else:
            _vd = run_dir / "verify" / "designs" / _h
        if (_vd / "metrics.json").exists():
            _verify_dirs.append(_vd)

    comparable, comparable_reason = _comparability(
        list(best_screen.values()), deduped_verify, screen_cfg, verify_cfg,
        screen_design_dirs=_screen_dirs, verify_design_dirs=_verify_dirs)

    # ── Band from screen config ───────────────────────────────────────────────
    tgt = _as_dict(screen_cfg.get("target")) or _as_dict(
        _as_dict(screen_cfg.get("brief")).get("target"))
    band_lo = tgt.get("band_lo_hz")
    band_hi = tgt.get("band_hi_hz")
    band_hz: list[int | None] | None
    if band_lo is not None and band_hi is not None:
        try:
            band_hz = [int(band_lo), int(band_hi)]
        except (TypeError, ValueError):
            band_hz = None
    else:
        band_hz = None

    # ── Objective version ─────────────────────────────────────────────────────
    obj_ver = run_objective_version(run_dir)

    # ── State ─────────────────────────────────────────────────────────────────
    if verify_sources_list:
        statuses = [s["status"] for s in verify_sources_list]
        if "possibly_running" in statuses:
            state = "possibly_running"
        elif any(s == "running" for s in statuses):
            state = "running"
        elif any(s == "none" for s in statuses):
            state = "none"
        else:
            state = "finished"
    else:
        state = "none"

    # ── Fidelity ──────────────────────────────────────────────────────────────
    fidelity = _build_fidelity(
        run_dir, deduped_verify, source_run_id_for_hash,
        source_kind_for_hash, runs, is_standalone)

    # ── Build rows and summary ────────────────────────────────────────────────
    rows, summary = _build_rows_and_summary(
        deduped_verify, best_screen, source_run_id_for_hash, source_kind_for_hash,
        run_dir, runs, is_standalone, comparable, run_id)

    # ── Gate audit ────────────────────────────────────────────────────────────
    gate_audit = run_gate_audit(root, run_id)
    # Also check using linked source run ids
    if not gate_audit.get("available"):
        for src in verify_sources_list:
            if src["kind"] == "linked":
                ga = run_gate_audit(root, src["run_id"])
                if ga.get("available"):
                    gate_audit = ga
                    break
    # Slim the gate_audit for the report (no per-design data; that's in rows)
    if gate_audit.get("available"):
        slim_gate = {
            "available": True,
            "source": gate_audit["source"],
            "labels": gate_audit.get("labels") or {},
        }
    else:
        slim_gate = {"available": False}

    return clean({
        "run_id": run_id,
        "name": screen_cfg.get("name"),
        "kind": kind,
        "redirect_to": None,
        "parent_missing": False,
        "objective_version": obj_ver,
        "band_hz": band_hz,
        "sources": verify_sources_list,
        "state": state,
        "comparable": comparable,
        "comparable_reason": comparable_reason,
        "latest_only": had_dupes,
        "fidelity": fidelity,
        "summary": summary,
        "gate_audit": slim_gate,
        "rows": rows,
    })


def _build_fidelity(run_dir: Path, deduped_verify: list[dict],
                    source_run_id_for_hash: dict[str, str],
                    source_kind_for_hash: dict[str, str],
                    runs: Path,
                    is_standalone: bool) -> dict:
    """Compute fidelity.{verify,screen} from actual disk data."""
    verify_n_freqs = []
    verify_grids = []
    verify_dofs = []
    screen_n_freqs = []
    screen_grids = []
    screen_dofs = []

    for r in deduped_verify:
        h = str(r.get("design_hash") or "")
        if not h:
            continue
        # verify design dir
        tier = "standalone" if is_standalone else "verify"
        src_kind = source_kind_for_hash.get(h, "inline")
        src_run_id = source_run_id_for_hash.get(h, run_dir.name)

        if tier == "standalone":
            vd = runs / run_dir.name / "designs" / h
        elif src_kind == "inline":
            vd = run_dir / "verify" / "designs" / h
        elif src_kind == "linked":
            vd = runs / src_run_id / "designs" / h
        else:
            vd = run_dir / "verify" / "designs" / h

        m = _read_json(vd / "metrics.json")
        if m is not None:
            nf = len(m.get("freqs_hz") or [])
            if nf:
                verify_n_freqs.append(nf)

        p = vd / "response.npz"
        if p.is_file():
            try:
                with np.load(str(p), allow_pickle=False) as z:
                    if "meta" in z.files:
                        meta = json.loads(str(z["meta"]))
                        bg = meta.get("balloon_grid")
                        if isinstance(bg, list) and len(bg) == 2:
                            verify_grids.append(bg)
                    if "n_dof" in z.files:
                        verify_dofs.append(int(z["n_dof"]))
            except (OSError, KeyError, ValueError, json.JSONDecodeError):
                pass

        # Also try row-level n_dof
        ndof_row = r.get("n_dof")
        if ndof_row is not None and not verify_dofs:
            try:
                verify_dofs.append(int(ndof_row))
            except (TypeError, ValueError):
                pass

        # Screen fidelity (not applicable for standalone)
        if not is_standalone:
            sd = run_dir / "designs" / h
            m2 = _read_json(sd / "metrics.json")
            if m2 is not None:
                nf2 = len(m2.get("freqs_hz") or [])
                if nf2:
                    screen_n_freqs.append(nf2)
            p2 = sd / "response.npz"
            if p2.is_file():
                try:
                    with np.load(str(p2), allow_pickle=False) as z2:
                        if "meta" in z2.files:
                            meta2 = json.loads(str(z2["meta"]))
                            bg2 = meta2.get("balloon_grid")
                            if isinstance(bg2, list) and len(bg2) == 2:
                                screen_grids.append(bg2)
                        if "n_dof" in z2.files:
                            screen_dofs.append(int(z2["n_dof"]))
                except (OSError, KeyError, ValueError, json.JSONDecodeError):
                    pass

    def _uniq(lst: list) -> list:
        seen = []
        for x in lst:
            if x not in seen:
                seen.append(x)
        return seen

    def _dof_range(dofs: list[int]) -> list[int] | None:
        if not dofs:
            return None
        return [min(dofs), max(dofs)]

    out: dict = {}
    if verify_n_freqs or verify_grids:
        verify_fid: dict = {}
        if verify_n_freqs:
            verify_fid["n_freqs"] = _uniq(verify_n_freqs)
        if verify_grids:
            verify_fid["balloon_grid"] = _uniq(verify_grids)
            verify_fid["n_points"] = _uniq([g[0] * g[1] for g in verify_grids])
        dr = _dof_range(verify_dofs)
        if dr:
            verify_fid["dof_range"] = dr
        out["verify"] = verify_fid

    if screen_n_freqs or screen_grids:
        screen_fid: dict = {}
        if screen_n_freqs:
            screen_fid["n_freqs"] = _uniq(screen_n_freqs)
        if screen_grids:
            screen_fid["balloon_grid"] = _uniq(screen_grids)
            screen_fid["n_points"] = _uniq([g[0] * g[1] for g in screen_grids])
        dr2 = _dof_range(screen_dofs)
        if dr2:
            screen_fid["dof_range"] = dr2
        out["screen"] = screen_fid

    return out


def _build_rows_and_summary(
        deduped_verify: list[dict],
        best_screen: dict[str, dict],
        source_run_id_for_hash: dict[str, str],
        source_kind_for_hash: dict[str, str],
        run_dir: Path,
        runs: Path,
        is_standalone: bool,
        comparable: bool,
        run_id: str,
) -> tuple[list[dict], dict]:
    """Build the rows list and summary dict."""
    # Assign ranks
    # Screen ranks: 1-based among ok screen rows, sorted by J asc
    screen_j_list = [(h, r["objective"]) for h, r in best_screen.items()
                     if r.get("ok") and r.get("objective") is not None]
    screen_j_list.sort(key=lambda x: x[1])
    screen_rank_of: dict[str, int] = {h: i + 1 for i, (h, _) in enumerate(screen_j_list)}

    # Verify ranks: 1-based among ok verify rows, sorted by J asc
    ok_verify = [(r, r.get("objective")) for r in deduped_verify
                 if r.get("ok") and r.get("objective") is not None]
    ok_verify.sort(key=lambda x: x[1])
    verify_rank_of: dict[str, int] = {
        str(r.get("design_hash", "")): i + 1
        for i, (r, _) in enumerate(ok_verify)}

    # Build row objects
    rows = []
    for r in deduped_verify:
        h = str(r.get("design_hash") or "")
        if not h:
            continue

        ok = bool(r.get("ok"))
        verify_j = r.get("objective") if ok else None

        src_kind = source_kind_for_hash.get(h, "inline")
        src_run_id = source_run_id_for_hash.get(h, run_id)

        # Screen J (from paired screen row)
        screen_row = best_screen.get(h)
        screen_j = (screen_row.get("objective")
                    if screen_row and screen_row.get("ok") else None)

        # Delta (only when comparable and both present)
        delta_j: float | None = None
        delta_pct: float | None = None
        if comparable and screen_j is not None and verify_j is not None:
            delta_j = round(verify_j - screen_j, 4)
            if screen_j != 0:
                delta_pct = round((verify_j - screen_j) / screen_j * 100, 2)

        # Design dir for density + balloon/mesh existence
        if is_standalone:
            ddir = run_dir / "designs" / h
        elif src_kind == "inline":
            ddir = run_dir / "verify" / "designs" / h
        elif src_kind == "linked":
            ddir = runs / src_run_id / "designs" / h
        else:
            ddir = run_dir / "verify" / "designs" / h

        density = _density(ddir, r)

        # n_dof / n_triangles from row (more reliable than re-reading npz)
        n_dof_row = r.get("n_dof")
        n_tris_row = r.get("n_triangles")

        row_out: dict = {
            "hash": h,
            "family": r.get("family"),
            "screen_j": screen_j,
            "verify_j": verify_j,
            "delta_j": delta_j,
            "delta_pct": delta_pct,
            "screen_rank": screen_rank_of.get(h),
            "verify_rank": verify_rank_of.get(h),
            "ok": ok,
            "error": r.get("error") if not ok else None,
            "n": r.get("n"),
            "created_utc": r.get("created_utc"),
            "lane": r.get("lane"),
            "backend": r.get("backend"),
            "n_dof": n_dof_row,
            "n_triangles": n_tris_row,
            "density": density,
            "gates": None,  # filled below
            "source_kind": src_kind,
            "source_run_id": src_run_id,
            "has_balloon": (ddir / "response.npz").is_file(),
            "has_mesh": (ddir / "mesh.msh").is_file(),
        }
        rows.append(row_out)

    # Sort rows: verified+ok first by verify_j asc, then failed
    def _sort_key(row: dict):
        vj = row.get("verify_j")
        ok = row.get("ok", False)
        if ok and vj is not None:
            return (0, vj)
        return (1, 0.0)
    rows.sort(key=_sort_key)

    # ── Summary ───────────────────────────────────────────────────────────────
    n_verified = sum(1 for r in rows if r.get("ok") and r.get("verify_j") is not None)
    n_failed = sum(1 for r in rows if not r.get("ok"))

    pairs = [(r["screen_j"], r["verify_j"])
             for r in rows
             if r.get("ok") and r.get("screen_j") is not None
             and r.get("verify_j") is not None]
    n_pairs = len(pairs)
    n_worse = sum(1 for s, v in pairs if v > s)

    bias_median_pct: float | None = None
    if comparable and pairs:
        biases = [(v - s) / s * 100 for s, v in pairs if s != 0]
        if biases:
            biases_sorted = sorted(biases)
            n = len(biases_sorted)
            if n % 2 == 1:
                bias_median_pct = round(biases_sorted[n // 2], 2)
            else:
                bias_median_pct = round(
                    (biases_sorted[n // 2 - 1] + biases_sorted[n // 2]) / 2, 2)

    sp_all: float | None = None
    sp_top5: float | None = None
    if comparable and n_pairs >= 3:
        sx = np.array([s for s, v in pairs], float)
        sy = np.array([v for s, v in pairs], float)
        sp_all = _spearman(sx, sy)
        if n_pairs >= 5:
            sp_top5 = _spearman(sx[:5], sy[:5])

    top5_overlap: int | None = None
    if comparable and not is_standalone:
        # top-5 screen hashes vs top-5 verify hashes
        top5_screen = {h for h, _ in screen_j_list[:5]}
        top5_verify = {str(row_tuple[0].get("design_hash", ""))
                       for row_tuple in ok_verify[:5]}
        top5_overlap = len(top5_screen & top5_verify)

    # Best verify hash/J
    best_verify_hash: str | None = None
    best_verify_j: float | None = None
    if ok_verify:
        best_vr, best_vj = ok_verify[0]
        best_verify_hash = str(best_vr.get("design_hash", "")) or None
        best_verify_j = round(float(best_vj), 4) if best_vj is not None else None

    # Screen #1 verify rank
    screen1_hash: str | None = None
    screen1_verify_rank: int | None = None
    if screen_j_list:
        screen1_hash = screen_j_list[0][0]
        screen1_verify_rank = verify_rank_of.get(screen1_hash)

    summary: dict | None
    if n_verified == 0 and n_failed == 0:
        summary = None
    else:
        summary = {
            "n_verified": n_verified,
            "n_failed": n_failed,
            "n_pairs": n_pairs,
            "n_worse": n_worse,
            "bias_median_pct": bias_median_pct,
            "spearman_all": sp_all,
            "spearman_top5": sp_top5,
            "top5_overlap": top5_overlap,
            "best_verify_hash": best_verify_hash,
            "best_verify_j": best_verify_j,
            "screen1_hash": screen1_hash,
            "screen1_verify_rank": screen1_verify_rank,
        }

    return rows, summary


# ── design_payload ─────────────────────────────────────────────────────────────

def design_payload(runs: Path, run_id: str, h: str, tier: str) -> dict:
    """design_curves payload plus tier/density/gates/row for one design.

    tier must be "screen" or "verify".  Returns 400 (ValueError) for unknown tier.
    """
    if tier not in ("screen", "verify"):
        raise ValueError(f"unknown tier {tier!r}; must be 'screen' or 'verify'")
    if not HASH.match(h):
        raise ValueError(f"not a design hash: {h!r}")
    if not RUN_ID.match(run_id):
        raise ValueError(f"not a run id: {run_id!r}")

    run_dir = runs / run_id
    rj = _as_dict(_read_json(run_dir / "run.json"))
    is_standalone = (rj.get("mode") == "verify" and "verify_of" not in rj)

    if tier == "screen":
        # design dir is runs/<run_id>/designs/<h>/
        d = run_dir / "designs" / h
        if not (d / "metrics.json").exists():
            raise FileNotFoundError(f"{run_id}/{h}/metrics.json (screen)")
        curves = design_curves(run_dir, h)
    else:
        # tier == "verify"
        # Find the design directory
        if is_standalone:
            d = run_dir / "designs" / h
        else:
            # Try inline
            d_inline = run_dir / "verify" / "designs" / h
            if (d_inline / "metrics.json").exists():
                d = d_inline
            else:
                # Try linked verify runs
                d = None
                for vdir, _vrj in _scan_verify_runs(runs):
                    vo = _as_dict(_vrj.get("verify_of"))
                    if _match_parent(vo.get("run") or "", run_id, runs):
                        d_linked = vdir / "designs" / h
                        if (d_linked / "metrics.json").exists():
                            d = d_linked
                            break
                if d is None:
                    raise FileNotFoundError(f"{run_id}/{h}/metrics.json (verify)")

        # design_curves needs (run_dir, h) but reads from run_dir/designs/<h>
        # For verify, we need to read from a different base dir.
        # We call design_curves on the directory that owns the design.
        if is_standalone:
            curves = design_curves(run_dir, h)
        elif (run_dir / "verify" / "designs" / h / "metrics.json").exists():
            # Inline verify: create a temporary "run_dir" pointing at verify/
            verify_dir = run_dir / "verify"
            # design_curves reads from <base>/designs/<h>/
            curves = design_curves(verify_dir, h)
        else:
            # Linked verify run
            curves = design_curves(d.parent.parent, h)

    if curves is None:
        raise FileNotFoundError(f"{run_id}/{h} design_curves")

    # Density
    density = _density(d)

    # Gates: look up in gate_audit by run_id (and linked source ids)
    # We just pass back None when unavailable (GUI shows "not audited")
    gates_val = None
    root_path = runs.parent
    ga = run_gate_audit(root_path, run_id)
    if ga.get("available"):
        design_entry = _as_dict(ga.get("designs") or {}).get(h)
        if design_entry:
            gates_val = design_entry.get("gates")

    # Row from ndjson
    ndjson_path = (run_dir / "verify" / "search.ndjson"
                   if tier == "verify" and not is_standalone
                   else run_dir / "search.ndjson")
    row = None
    for r in read_ndjson(ndjson_path):
        if str(r.get("design_hash", "")) == h:
            row = r
            break

    return clean({
        **curves,
        "tier": tier,
        "density": density,
        "gates": gates_val,
        "row": row,
    })
