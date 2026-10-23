"""Read-only views of run folders, campaigns, briefs and machine state for the local GUI.

Nothing here solves, meshes or writes: every number comes from files the CLI already wrote
(``search.ndjson``, ``config.yaml``, ``designs/<hash>/{metrics.json,response.npz,mesh.msh}``,
``campaign.json``, ``leaderboard.md``). Values are JSON-safe (NaN/Inf -> None).
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import yaml

RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-z]+-[0-9a-f]{6}$")
CAMPAIGN_ID = re.compile(r"^campaign_[0-9]{8}T[0-9]{6}Z$")
HASH = re.compile(r"^[0-9a-f]{6,40}$")
BRIEF_NAME = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
TOP_K = 6                       # "pinned" = most of the TOP_K best designs within 2 % of a bound
PIN_FRAC = 0.02


# ---------------------------------------------------------------------------- helpers


def clean(x: Any) -> Any:
    """Recursively make a value JSON-safe: numpy -> python, NaN/Inf -> None."""
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return clean(x.tolist())
    if isinstance(x, (np.floating, float)):
        f = float(x)
        return f if math.isfinite(f) else None
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def _rnd(a, n=3):
    arr = np.asarray(a, dtype=float)
    return [None if not math.isfinite(v) else round(v, n) for v in arr.ravel().tolist()]


def _read_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def read_ndjson(p: Path) -> list[dict]:
    rows = []
    try:
        with p.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:      # a row being written right now
                        pass
    except OSError:
        pass
    return rows


def tail_text(p: Path, n: int = 40) -> list[str]:
    """Last n lines of a log; handles the UTF-16 files PowerShell's Tee-Object writes."""
    try:
        raw = p.read_bytes()
    except OSError:
        return []
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff") or raw[1:2] == b"\x00":
        txt = raw.decode("utf-16", errors="replace")
    else:
        txt = raw.decode("utf-8", errors="replace")
    return [ln.rstrip("\r") for ln in txt.lstrip("﻿").splitlines()][-n:]


def _flat(d: Any, prefix: str = "") -> dict[str, float]:
    out: dict[str, float] = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(_flat(v, f"{prefix}{k}."))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            out.update(_flat(v, f"{prefix}{i}."))
    elif isinstance(d, (int, float)) and not isinstance(d, bool):
        out[prefix[:-1]] = float(d)
    return out


def _err_kind(row: dict) -> str | None:
    e = row.get("error")
    return None if not e else str(e).split(":", 1)[0]


def _spearman(x: np.ndarray, y: np.ndarray) -> float | None:
    if len(x) < 5 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return None
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    c = np.corrcoef(rx, ry)[0, 1]
    return float(c) if math.isfinite(c) else None


# ---------------------------------------------------------------------------- runs


def _run_dirs(runs: Path) -> list[Path]:
    if not runs.is_dir():
        return []
    return sorted((p for p in runs.iterdir() if p.is_dir() and RUN_ID.match(p.name)),
                  key=lambda p: p.name, reverse=True)


def _config(run_dir: Path) -> dict:
    try:
        return yaml.safe_load((run_dir / "config.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def run_summary(run_dir: Path) -> dict:
    rows = read_ndjson(run_dir / "search.ndjson")
    cfg = _config(run_dir)
    ok = [r for r in rows if r.get("ok")]
    best = min(ok, key=lambda r: r["objective"]) if ok else None
    brief = cfg.get("brief") if isinstance(cfg.get("brief"), dict) else None
    return clean({
        "id": run_dir.name,
        "name": cfg.get("name"),
        "family": cfg.get("family") or (rows[0].get("family") if rows else None),
        "generator": (cfg.get("generator") or {}).get("name") if isinstance(cfg.get("generator"), dict) else None,
        "brief": brief.get("name") if brief else None,
        "mode": rows[0].get("mode") if rows else None,
        "n": len(rows),
        "n_ok": len(ok),
        "n_cached": sum(1 for r in rows if r.get("cached")),
        "failures": dict(Counter(k for k in map(_err_kind, rows) if k)),
        "seed_j": rows[0].get("objective") if rows else None,
        "best_j": best["objective"] if best else None,
        "best_hash": best["design_hash"] if best else None,
        "started": rows[0].get("created_utc") if rows else None,
        "last": rows[-1].get("created_utc") if rows else None,
        "has_report": (run_dir / "report.html").exists(),
    })


def list_runs(runs: Path, limit: int = 300) -> list[dict]:
    return [run_summary(d) for d in _run_dirs(runs)[:limit]]


def _resolve_run(runs: Path, run_id: str) -> Path:
    if not RUN_ID.match(run_id):
        raise ValueError(f"not a run id: {run_id!r}")
    d = runs / run_id
    if not (d / "search.ndjson").exists():
        raise FileNotFoundError(run_id)
    return d


def _norm_polar(spl: np.ndarray) -> np.ndarray:
    c = spl.shape[1] // 2
    return np.maximum(spl - spl[:, c:c + 1], -40.0)


def mesh_nodes_tris(msh: Path) -> tuple[np.ndarray, np.ndarray] | None:
    """Nodes (m) and triangles (0-based) from a gmsh 2.2 ASCII file, as the mesher writes it."""
    try:
        txt = msh.read_text(errors="ignore")
    except OSError:
        return None
    mn = re.search(r"\$Nodes\s*\n(\d+)\n(.*?)\$EndNodes", txt, re.S)
    me = re.search(r"\$Elements\s*\n(\d+)\n(.*?)\$EndElements", txt, re.S)
    if not mn:
        return None
    ids, pts = [], []
    for ln in mn.group(2).strip().splitlines():
        a = ln.split()
        ids.append(int(a[0]))
        pts.append([float(a[1]), float(a[2]), float(a[3])])
    index = {nid: i for i, nid in enumerate(ids)}
    tris = []
    if me:
        for ln in me.group(2).strip().splitlines():
            a = ln.split()
            if len(a) > 3 and a[1] == "2":                     # 3-node triangle
                ntags = int(a[2])
                tris.append([index[int(v)] for v in a[3 + ntags:6 + ntags]])
    return np.asarray(pts, float), np.asarray(tris, int).reshape(-1, 3)


def _profile_from_mesh(msh: Path) -> dict:
    nt = mesh_nodes_tris(msh)
    if nt is None:
        return {}
    pts, _ = nt
    prof = {}
    for key, ax in (("h", 0), ("v", 1)):
        sel = pts[np.abs(pts[:, 1 - ax]) < 1e-4]
        sel = sel[np.argsort(sel[:, 2])]
        prof[key] = [[round(float(z) * 1000, 2), round(float(a) * 1000, 2)] for a, z in zip(sel[:, ax], sel[:, 2])]
    return prof


def design_curves(run_dir: Path, h: str) -> dict | None:
    """Per-frequency metrics, normalised polar maps and the wall profile of one solved design."""
    if not HASH.match(h):
        raise ValueError(f"not a design hash: {h!r}")
    d = run_dir / "designs" / h
    m = _read_json(d / "metrics.json")
    if m is None:
        return None
    out = {
        "hash": h,
        "freqs": _rnd(m["freqs_hz"], 1),
        "bw_h": _rnd(m["bw_h_deg"], 2), "bw_v": _rnd(m["bw_v_deg"], 2),
        "di": _rnd(m["di_db"], 3), "di_source": m.get("di_source"),
        "on_axis": _rnd(np.asarray(m["on_axis_db"], float) - np.nanmean(m["on_axis_db"]), 3),
        "rip_h": _rnd(m["ripple_h_db"], 3), "rip_v": _rnd(m["ripple_v_db"], 3),
        "z_re": _rnd(m["z_throat_real"], 3) if m.get("z_throat_real") is not None else None,
        "scalars": m.get("scalars") or {},
    }
    try:
        with np.load(d / "response.npz", allow_pickle=False) as z:
            out["angles"] = _rnd(z["h_angles_deg"], 1)
            out["polar_h"] = [_rnd(r, 2) for r in _norm_polar(np.asarray(z["spl_h_db"], float))]
            out["polar_v"] = [_rnd(r, 2) for r in _norm_polar(np.asarray(z["spl_v_db"], float))]
    except (OSError, KeyError, ValueError):
        pass
    out["profile"] = _profile_from_mesh(d / "mesh.msh")
    dj = _read_json(d / "design.json") or {}
    out["params"] = dj.get("params")
    out["generator"] = dj.get("generator")
    return clean(out)


def _knob_values(row: dict) -> dict[str, float]:
    gen = row.get("generator")
    if isinstance(gen, dict) and isinstance(gen.get("knobs"), dict):
        return {k: float(v) for k, v in gen["knobs"].items() if isinstance(v, (int, float))}
    return _flat(row.get("params") or {})


def sensitivity(rows: list[dict], bounds: dict) -> list[dict]:
    """Spearman rho of each searched knob with J over successful rows, and bound pinning of the best K."""
    ok = [r for r in rows if r.get("ok") and r.get("objective") is not None]
    if not ok or not isinstance(bounds, dict):
        return []
    vals = [_knob_values(r) for r in ok]
    J = np.array([r["objective"] for r in ok], float)
    top = np.argsort(J)[:TOP_K]
    out = []
    for key, b in bounds.items():
        if not isinstance(b, dict) or "lo" not in b or "hi" not in b or b.get("search") is False:
            continue
        x = np.array([v.get(key, np.nan) for v in vals], float)
        fin = np.isfinite(x)
        if fin.sum() < 2:
            continue
        lo, hi = float(b["lo"]), float(b["hi"])
        tol = PIN_FRAC * (hi - lo)
        xt = x[top][np.isfinite(x[top])]
        out.append({"key": key, "lo": lo, "hi": hi,
                    "rho": _spearman(x[fin], J[fin]),
                    "best": float(x[int(np.argmin(np.where(fin, J, np.inf)))]),
                    "at_lo": int(np.sum(xt <= lo + tol)), "at_hi": int(np.sum(xt >= hi - tol))})
    out.sort(key=lambda s: -abs(s["rho"] or 0))
    return clean(out)


def run_detail(runs: Path, run_id: str) -> dict:
    d = _resolve_run(runs, run_id)
    rows = read_ndjson(d / "search.ndjson")
    cfg = _config(d)
    summ = run_summary(d)
    best_hash, seed_hash = summ["best_hash"], (rows[0]["design_hash"] if rows else None)
    seed_ok = bool(rows and rows[0].get("ok"))
    best_row = next((r for r in rows if r.get("design_hash") == best_hash and r.get("ok")), None)
    return clean({
        "summary": summ,
        "target": cfg.get("target") or (cfg.get("brief") or {}).get("target"),
        "weights": cfg.get("weights") or (cfg.get("brief") or {}).get("weights"),
        "brief": cfg.get("brief"),
        "J": [r.get("objective") if r.get("ok") else None for r in rows],
        "terms_seed": rows[0].get("terms") if seed_ok else None,
        "terms_best": best_row.get("terms") if best_row else None,
        "sens": sensitivity(rows, cfg.get("bounds") or {}),
        "best": design_curves(d, best_hash) if best_hash else None,
        "seed": design_curves(d, seed_hash) if seed_ok and seed_hash and seed_hash != best_hash else None,
        "command": (_read_json(d / "run.json") or {}).get("command"),
    })


def mesh_surface(runs: Path, run_id: str, h: str, max_tris: int = 60000) -> dict:
    """Triangle surface of a solved design (mm), the meshed domain only (a quarter for quadrants '1')."""
    d = _resolve_run(runs, run_id)
    if not HASH.match(h):
        raise ValueError(f"not a design hash: {h!r}")
    nt = mesh_nodes_tris(d / "designs" / h / "mesh.msh")
    if nt is None:
        raise FileNotFoundError(f"{run_id}/{h}/mesh.msh")
    pts, tris = nt
    meta = _read_json(d / "designs" / h / "mesh_meta.json") or {}
    q = ((meta.get("result") or {}).get("quadrants")) or "1234"
    return {"quadrants": q, "n_tris": int(len(tris)),
            "verts": np.round(pts * 1000, 2).ravel().tolist(),
            "tris": tris[:max_tris].ravel().tolist()}


# ---------------------------------------------------------------------------- campaigns


def list_campaigns(runs: Path) -> list[dict]:
    out = []
    if not runs.is_dir():
        return out
    for p in sorted((p for p in runs.iterdir() if p.is_dir() and CAMPAIGN_ID.match(p.name)),
                    key=lambda p: p.name, reverse=True):
        c = _read_json(p / "campaign.json")
        if not c:
            continue
        out.append(clean({"id": p.name, "tier": c.get("tier"), "brief": c.get("brief_name"),
                          "seeds": c.get("seeds"), "n_entries": len(c.get("entries", [])),
                          "families": [e.get("name") for e in c.get("entries", [])]}))
    return out


def campaign_detail(runs: Path, cid: str) -> dict:
    if not CAMPAIGN_ID.match(cid):
        raise ValueError(f"not a campaign id: {cid!r}")
    c = _read_json(runs / cid / "campaign.json")
    if c is None:
        raise FileNotFoundError(cid)
    entries = []
    for e in c.get("entries", []):
        jobs = e.get("jobs") or []
        js = [j.get("best_j") for j in jobs if j.get("best_j") is not None]
        best_job = min((j for j in jobs if j.get("best_j") is not None), key=lambda j: j["best_j"], default=None)
        best = None
        if best_job and best_job.get("run_dir"):
            rd = Path(best_job["run_dir"])
            if rd.parent.resolve() == runs.resolve() and RUN_ID.match(rd.name):
                s = run_summary(rd)
                if s.get("best_hash"):
                    best = design_curves(rd, s["best_hash"])
        entries.append({
            "name": e.get("name"), "group": e.get("group"), "symmetry": e.get("symmetry"),
            "skipped": e.get("skipped"), "skip_reason": e.get("skip_reason"),
            "best_j": min(js) if js else None,
            "median_j": float(np.median(js)) if js else None,
            "spread": (max(js) - min(js)) if len(js) > 1 else None,
            "evals": sum((j.get("stats") or {}).get("evaluations", 0) for j in jobs),
            "failures": dict(sum((Counter((j.get("stats") or {}).get("failures_by_reason") or {}) for j in jobs),
                                 Counter())),
            "pinned": sorted({k for j in jobs for k in (j.get("pinned_bounds") or [])}),
            "jobs": [{"seed": j.get("seed"), "best_j": j.get("best_j"),
                      "run_id": Path(j["run_dir"]).name if j.get("run_dir") else None,
                      "returncode": j.get("returncode"), "wall_min": (j.get("wall_seconds") or 0) / 60}
                     for j in jobs],
            "best": best,
        })
    entries.sort(key=lambda e: (e["best_j"] is None, e["median_j"] if e["median_j"] is not None else 0))
    lb = runs / cid / "leaderboard.md"
    return clean({"id": cid, "tier": c.get("tier"), "brief": c.get("brief_name"), "seeds": c.get("seeds"),
                  "entries": entries,
                  "leaderboard_md": lb.read_text(encoding="utf-8") if lb.exists() else None})


# ---------------------------------------------------------------------------- briefs


def brief_dirs(root: Path) -> tuple[Path, Path]:
    return root / "examples" / "briefs", root / "examples" / "briefs" / "user"


def list_briefs(root: Path) -> list[dict]:
    shipped, user = brief_dirs(root)
    out = []
    for kind, d in (("shipped", shipped), ("user", user)):
        for p in sorted(d.glob("*.yaml")) if d.is_dir() else []:
            try:
                raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as exc:
                raw = {"_error": str(exc)}
            out.append(clean({"name": p.stem, "kind": kind,
                              "path": p.relative_to(root).as_posix(), "brief": raw}))
    return out


def save_user_brief(root: Path, name: str, brief: dict) -> Path:
    """Write a NEW brief to examples/briefs/user/<name>.yaml after the CLI's own validation.
    Never overwrites a shipped brief; refuses names that collide with one."""
    from hornlab_search.config import load_brief
    if not BRIEF_NAME.match(name or ""):
        raise ValueError("brief name: letters, digits, _ and - only (max 64)")
    shipped, user = brief_dirs(root)
    if (shipped / f"{name}.yaml").exists():
        raise ValueError(f"{name!r} is a shipped brief; choose another name")
    user.mkdir(parents=True, exist_ok=True)
    body = dict(brief)
    body["name"] = name
    p = user / f"{name}.yaml"
    tmp = user / f".{name}.yaml.tmp"
    tmp.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")
    try:
        load_brief(tmp)                      # the CLI's own schema check
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(p)
    return p


# ---------------------------------------------------------------------------- machine state


def status(root: Path, runs: Path) -> dict:
    import shutil
    from hornlab_search.search import hygiene
    from hornlab_search.search.gpulock import _lock_path, _pid_alive, _read_lock
    lock = _read_lock(_lock_path(runs))
    if lock:
        lock = dict(lock)
        lock["alive"] = bool(lock.get("pid") and _pid_alive(int(lock["pid"])))
    try:
        procs = hygiene.list_project_julia()
    except Exception:  # noqa: BLE001 - status must never fail on a probe
        procs = []
    try:
        vram = hygiene.vram_used_mib()
    except Exception:  # noqa: BLE001
        vram = None
    disk = None
    try:
        u = shutil.disk_usage(runs if runs.exists() else root)
        disk = {"free_gb": round(u.free / 1e9, 1), "total_gb": round(u.total / 1e9, 1)}
    except OSError:
        pass
    ov = runs / "overnight"
    queue_logs = sorted(ov.glob("queue_*.log")) if ov.is_dir() else []
    return clean({
        "gpu_lock": lock, "vram_mib": vram, "julia_procs": len(procs), "disk": disk,
        "queue_log": {"name": queue_logs[-1].name, "tail": tail_text(queue_logs[-1], 30)} if queue_logs else None,
        "watchdog_log": tail_text(ov / "watchdog.log", 10) if ov.is_dir() else [],
    })
