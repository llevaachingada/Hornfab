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
STEP_NAME = re.compile(r"^[A-Za-z0-9_\-]{1,80}_rank\d+_[0-9a-f]{6,40}\.step$")
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


def horn_dims(row: dict | None) -> dict | None:
    """Outer size of a solved design in mm (mouth width x height, depth), shell included, from the mesh
    bounding box the search recorded. The meshed domain is a quarter for quadrants '1' (x >= 0, y >= 0),
    so the full mouth is twice the extent there."""
    if not row or not row.get("bbox_m"):
        return None
    x0, y0, z0, x1, y1, z1 = (float(v) for v in row["bbox_m"])
    q = str(row.get("quadrants") or "1234")
    w = 2 * x1 if q in ("1", "14") else x1 - x0
    h = 2 * y1 if q in ("1", "12") else y1 - y0
    return {"mouth_w_mm": round(w * 1000, 1), "mouth_h_mm": round(h * 1000, 1),
            "depth_mm": round((z1 - z0) * 1000, 1), "includes_shell": True}


_FLAG = re.compile(r"--(budget|max-evals|cma-seed)\s+(\d+)")


def _command_flags(run_dir: Path) -> dict:
    cmd = (_read_json(run_dir / "run.json") or {}).get("command") or ""
    return {k.replace("-", "_"): int(v) for k, v in _FLAG.findall(cmd)} | {"command": cmd}


def _ts(s: str | None):
    import datetime as dt
    try:
        return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        return None


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
        "dims": horn_dims(best),
        "budget": _command_flags(run_dir).get("max_evals") or _command_flags(run_dir).get("budget"),
        "cma_seed": _command_flags(run_dir).get("cma_seed"),
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


def _plane_chains(pts: np.ndarray, tris: np.ndarray, ax: int, tol: float = 1e-6) -> list[list[int]]:
    """Ordered node chains along the symmetry plane where coordinate (1 - ax) == 0 and coordinate ax >= 0.
    In a quarter-model mesh the symmetry planes are open boundaries, so the mesh edges lying in a plane
    form the horn's cross-section outline (throat cap, acoustic wall, mouth lip, outer shell, rear)."""
    on = (np.abs(pts[:, 1 - ax]) < tol) & (pts[:, ax] >= -tol)
    adj: dict[int, set[int]] = {}
    for t in tris:
        for i, j in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            if on[i] and on[j]:
                adj.setdefault(int(i), set()).add(int(j))
                adj.setdefault(int(j), set()).add(int(i))
    chains, seen = [], set()
    starts = [n for n, nb in adj.items() if len(nb) == 1] + list(adj)
    for s0 in starts:
        if s0 in seen:
            continue
        chain, prev, cur = [s0], None, s0
        seen.add(s0)
        while True:
            nxt = [n for n in adj[cur] if n != prev and n not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen.add(cur)
            chain.append(cur)
        if len(chain) > 2:
            chains.append(chain)
    return chains


def _profile_from_mesh(msh: Path) -> dict:
    """Wall cross-section in the H (x-z) and V (y-z) planes, in mm as [z, r] points.
    kind 'section': ordered outline from the plane's boundary edges (quarter meshes);
    kind 'nodes': unordered plane nodes (full meshes, where the planes are not mesh boundaries)."""
    nt = mesh_nodes_tris(msh)
    if nt is None:
        return {}
    pts, tris = nt
    prof: dict = {}
    for key, ax in (("h", 0), ("v", 1)):
        chains = _plane_chains(pts, tris, ax) if len(tris) else []
        if chains:
            chain = max(chains, key=len)
            prof[key] = [[round(float(pts[i, 2]) * 1000, 2), round(float(pts[i, ax]) * 1000, 2)] for i in chain]
            prof["kind"] = "section"
        else:
            sel = pts[np.abs(pts[:, 1 - ax]) < 1e-4]
            sel = sel[np.argsort(sel[:, 2])]
            prof[key] = [[round(float(z) * 1000, 2), round(float(a) * 1000, 2)] for a, z in zip(sel[:, ax], sel[:, 2])]
            prof.setdefault("kind", "nodes")
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
            if "z_throat" in z.files:
                zt = np.asarray(z["z_throat"], dtype=complex)
                out["z_re"], out["z_im"] = _rnd(zt.real, 3), _rnd(zt.imag, 3)   # exp(-i w t): mass-like < 0
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
        "step_files": sorted(p.name for p in (d / "step").glob("*.step") if STEP_NAME.match(p.name))
                      if (d / "step").is_dir() else [],
    })


def run_archive(runs: Path, run_id: str) -> dict:
    """The CMA-ME quality-diversity atlas of a run (WP11b), read from the search-written
    ``archive_heatmap.json``: ``{"bins": [bins_h, bins_v], "ranges": {"h": [lo, hi], "v": [lo, hi]},
    "descriptors": {"h": name, "v": name},
    "cells": [{"h_center", "v_center", "objective", "design_hash"}]}``.

    Only OCCUPIED bins appear in ``cells``; a cell centre is the descriptor mean over the solve band
    (``mean_bw_h_deg`` on the h axis, ``mean_bw_v_deg`` on the v axis) and ``objective`` is the run's
    J (lower is better). The raw ``archive.json`` is never parsed and nothing is solved. A run without
    an atlas (every plain cma run) gets the empty pattern, exactly like a run with no evaluations.
    Additive keys the file may carry (legacy ``rows``/``axis`` aliases) are ignored, not echoed."""
    d = _resolve_run(runs, run_id)
    heat = _read_json(d / "archive_heatmap.json")
    if (not isinstance(heat, dict) or not isinstance(heat.get("bins"), list)
            or not isinstance(heat.get("ranges"), dict) or not isinstance(heat.get("cells"), list)):
        return {"run_id": run_id, "available": False, "bins": None, "ranges": None, "cells": [],
                "stats": None}
    out = {"run_id": run_id, "available": True, "bins": heat["bins"], "ranges": heat["ranges"],
           "cells": heat["cells"],
           "descriptors": heat["descriptors"] if isinstance(heat.get("descriptors"), dict) else None,
           "stats": heat.get("stats") if isinstance(heat.get("stats"), dict) else None}
    for key in ("descriptor_h", "descriptor_v"):        # optional labels, absent from the pinned file
        if isinstance(heat.get(key), str):
            out[key] = heat[key]
    return clean(out)


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


def _evidence_campaigns(runs: Path) -> set[str]:
    """Campaign ids committed as evidence (docs/evidence/campaigns/<id>.campaign.json)."""
    d = runs.parent / "docs" / "evidence" / "campaigns"
    return {p.name.split(".")[0] for p in d.glob("campaign_*.campaign.json")} if d.is_dir() else set()


def superseded(runs: Path, cid: str) -> bool:
    """A campaign is superseded if it is older than the newest committed evidence campaign and is not
    itself committed evidence. The committed set is the reviewed record (campaigns before the
    2026-10-22 fixes scored native configs on their own targets without the size envelope; see
    docs/evidence/TYPOLOGY_SCREEN_2026-10-22.md); anything newer was run with the current code."""
    ev = _evidence_campaigns(runs)
    return bool(ev) and cid not in ev and cid < max(ev)


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
                          "superseded": superseded(runs, p.name),
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
        best, dims, best_run = None, None, None
        if best_job and best_job.get("run_dir"):
            rd = Path(best_job["run_dir"])
            if rd.parent.resolve() == runs.resolve() and RUN_ID.match(rd.name):
                s = run_summary(rd)
                dims, best_run = s.get("dims"), rd.name
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
            "best": best, "dims": dims, "best_run_id": best_run,
        })
    entries.sort(key=lambda e: (e["best_j"] is None, e["median_j"] if e["median_j"] is not None else 0))
    brief_raw = next((b["brief"] for b in list_briefs(runs.parent) if b["name"] == c.get("brief_name")), {})
    lb = runs / cid / "leaderboard.md"
    return clean({"id": cid, "tier": c.get("tier"), "brief": c.get("brief_name"), "seeds": c.get("seeds"),
                  "superseded": superseded(runs, cid),
                  "target": (brief_raw or {}).get("target"),       # from the brief file named by the campaign
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
    import tempfile
    p = user / f"{name}.yaml"
    text = yaml.safe_dump(body, sort_keys=False)
    with tempfile.TemporaryDirectory() as td:          # validate under the real name, outside the repo
        probe = Path(td) / f"{name}.yaml"
        probe.write_text(text, encoding="utf-8")
        load_brief(probe)                               # the CLI's own schema check; raises ConfigError
    tmp = user / f".{name}.yaml.tmp"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(p)                                      # atomic: never a half-written brief
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
        "queue_log": {"name": queue_logs[-1].name, "tail": tail_text(queue_logs[-1], 30),
                      "steps": queue_steps(queue_logs[-1])} if queue_logs else None,
        "current": run_progress(cur) if (lock and lock.get("alive") and (cur := current_run(runs))) else None,
        "watchdog_log": tail_text(ov / "watchdog.log", 10) if ov.is_dir() else [],
    })


# ---------------------------------------------------------------------------- configs and catalog


def catalog(root: Path) -> list[dict]:
    try:
        raw = yaml.safe_load((root / "examples" / "catalog.yaml").read_text(encoding="utf-8-sig")) or {}
    except (OSError, yaml.YAMLError):
        return []
    return [clean(e) for e in raw.get("entries", []) if isinstance(e, dict)]


def _config_seed_materializes(p: Path) -> bool:
    """True when the config's own seed materializes (the honest runnable gate).

    The old heuristic keyed on ``"lecleach" in p.stem``; lecleach is now a verified,
    live generator, so a name substring is simply wrong.  A config whose seed cannot be
    materialized is the only thing the GUI should grey out.
    """
    try:
        from hornlab_search.config import load_config
        from hornlab_search.design.space import DesignSpace
        DesignSpace.from_config(load_config(p))
        return True
    except Exception:  # noqa: BLE001 - an unloadable/unmaterializable seed is disabled
        return False


def list_configs(root: Path) -> list[dict]:
    """Every runnable config under examples/ (not briefs, not the catalog), with its catalog entry."""
    cat = {e.get("config"): e for e in catalog(root)}
    ex = root / "examples"
    out = []
    for p in sorted(list(ex.glob("*.yaml")) + list((ex / "typologies").glob("*.yaml"))):
        if p.name == "catalog.yaml":
            continue
        try:
            raw = yaml.safe_load(p.read_text(encoding="utf-8-sig")) or {}
        except yaml.YAMLError:
            continue
        rel = p.relative_to(ex).as_posix()
        e = cat.get(rel, {})
        bounds = raw.get("bounds") or {}
        out.append(clean({
            "path": p.relative_to(root).as_posix(), "name": raw.get("name") or p.stem,
            "family": raw.get("family"), "generator": isinstance(raw.get("generator"), dict),
            "brief_file": raw.get("brief_file"), "catalog_name": e.get("name"), "group": e.get("group"),
            "symmetry": e.get("symmetry"), "description": e.get("description"),
            "n_knobs": sum(1 for b in bounds.values() if isinstance(b, dict) and b.get("search", True)),
            # honest gate: the seed materializes (never a name substring; lecleach is live)
            "disabled": not _config_seed_materializes(p)}))
    return out


# ---------------------------------------------------------------------------- live progress


def run_progress(run_dir: Path) -> dict:
    """Evaluations done vs budget, best so far, rate and ETA from the run's own timestamps."""
    s = run_summary(run_dir)
    rows = read_ndjson(run_dir / "search.ndjson")
    t = [_ts(r.get("created_utc")) for r in rows[-40:]]
    t = [x for x in t if x]
    rate = None
    if len(t) >= 2 and (t[-1] - t[0]).total_seconds() > 0:
        rate = (len(t) - 1) / (t[-1] - t[0]).total_seconds() * 3600
    left = (s["budget"] - s["n"]) if s.get("budget") else None
    return clean({**s, "rate_per_h": rate,
                  "eta_min": (left / rate * 60) if (rate and left is not None and left > 0) else None})


def current_run(runs: Path, max_age_s: float = 1800) -> Path | None:
    """The run folder written most recently (within max_age_s), i.e. the search in progress."""
    import time
    best, best_t = None, 0.0
    for d in _run_dirs(runs)[:30]:
        f = d / "search.ndjson"
        try:
            m = f.stat().st_mtime
        except OSError:
            continue
        if m > best_t:
            best, best_t = d, m
    return best if best and time.time() - best_t < max_age_s else None


_STEP = re.compile(r"^=== (\S+) (START|END|SKIP) (\S+)(?: : (.*?))?(?: exit (-?\d+))?(?: \(.*\))?$")


def queue_steps(log: Path) -> list[dict]:
    """START/END/SKIP lines of an overnight queue log as a timeline."""
    steps: dict[str, dict] = {}
    order = []
    for ln in tail_text(log, 100000):
        m = _STEP.match(ln.strip())
        if not m:
            continue
        ts, kind, name, cmd, rc = m.groups()
        if name not in steps:
            steps[name] = {"name": name, "started": None, "ended": None, "exit": None, "command": None,
                           "skipped": False}
            order.append(name)
        st = steps[name]
        if kind == "START":
            st["started"], st["command"] = ts, cmd
        elif kind == "END":
            st["ended"], st["exit"] = ts, int(rc) if rc is not None else None
        else:
            st["skipped"] = True
    return [steps[n] for n in order]


# ---------------------------------------------------------------------------- leaders

TIER_RANK = {"compare": 2, "screen": 1}


def leaders(runs: Path) -> list[dict]:
    """Per brief, the leading family of the latest campaign of the strongest tier (compare beats
    screen; dry-run has no scores). 'clearly_ahead' applies the ranking rule: the leader's median beats
    the runner-up's by more than both spreads (screen tier has one repeat: never 'clearly')."""
    chosen: dict[str, dict] = {}
    for c in list_campaigns(runs):                       # newest first
        tier, brief = c.get("tier"), c.get("brief")
        if not brief or tier not in TIER_RANK or c.get("superseded"):
            continue
        cur = chosen.get(brief)
        if cur is None or TIER_RANK[tier] > TIER_RANK[cur["tier"]]:
            chosen[brief] = c
    out = []
    for brief, c in sorted(chosen.items()):
        try:
            d = campaign_detail(runs, c["id"])
        except (FileNotFoundError, ValueError):
            continue
        scored = [e for e in d["entries"] if e.get("median_j") is not None and not e.get("skipped")]
        scored.sort(key=lambda e: e["median_j"])
        if not scored:
            continue
        lead, nxt = scored[0], (scored[1] if len(scored) > 1 else None)
        gap = (nxt["median_j"] - lead["median_j"]) if nxt else None
        sp = [x for x in ((lead.get("spread"), nxt.get("spread")) if nxt else ()) if x is not None]
        clearly = bool(nxt and d["tier"] == "compare" and len(sp) == 2 and gap > max(sp))
        out.append(clean({"brief": brief, "campaign_id": c["id"], "tier": d["tier"],
                          "family": lead["name"], "group": lead.get("group"), "median_j": lead["median_j"],
                          "best_j": lead.get("best_j"), "spread": lead.get("spread"), "dims": lead.get("dims"),
                          "best_run_id": lead.get("best_run_id"), "runner_up": nxt["name"] if nxt else None,
                          "gap": gap, "clearly_ahead": clearly, "n_families": len(scored)}))
    return out


# ---------------------------------------------------------------------------- typologies


def typologies(root: Path, runs: Path) -> list[dict]:
    """Every catalog family (classical, hybrid, Magnus-native, legacy) with: parameter count, brief
    compatibility (the CLI's own ``campaign.is_compatible``), the budgets a campaign would give it
    (``campaign.budget_for_tier``), and its best result in the latest campaign of the strongest tier per
    brief, with the best design's size and wall cross-section."""
    from hornlab_search.search.campaign import budget_for_tier, is_compatible
    briefs = [b for b in list_briefs(root) if b["kind"] == "shipped" or b["kind"] == "user"]
    cfgs = {c["catalog_name"]: c for c in list_configs(root) if c.get("catalog_name")}
    # per family: its result in the newest campaign of each scored tier per brief THAT CONTAINS IT
    # (a later campaign that re-ran only some families must not hide the others' last result)
    results: dict[str, list[dict]] = {}
    seen: set[tuple] = set()
    for c in list_campaigns(runs):                       # newest first
        tier, brief = c.get("tier"), c.get("brief")
        if not brief or tier not in TIER_RANK or c.get("superseded"):
            continue
        try:
            d = campaign_detail(runs, c["id"])
        except (FileNotFoundError, ValueError):
            continue
        ranked = sorted((e for e in d["entries"] if e.get("median_j") is not None), key=lambda e: e["median_j"])
        for e in d["entries"]:                           # ran, but nothing valid under this brief
            key = (e["name"], brief, tier)
            if e.get("median_j") is None and not e.get("skipped") and key not in seen:
                seen.add(key)
                results.setdefault(e["name"], []).append({
                    "brief": brief, "tier": d["tier"], "campaign_id": c["id"], "rank": None, "of": len(ranked),
                    "median_j": None, "no_valid": True, "failures": e.get("failures")})
        for rank, e in enumerate(ranked, 1):
            key = (e["name"], brief, tier)
            if key in seen:
                continue
            seen.add(key)
            results.setdefault(e["name"], []).append({
                "brief": brief, "tier": d["tier"], "campaign_id": c["id"], "rank": rank, "of": len(ranked),
                "median_j": e["median_j"], "spread": e.get("spread"), "dims": e.get("dims"),
                "best_run_id": e.get("best_run_id"), "pinned": e.get("pinned"),
                "profile": (e.get("best") or {}).get("profile"),
                # measured wall time per evaluation in that campaign (includes cache hits and failures)
                "s_per_eval": (sum((j.get("wall_min") or 0) for j in e.get("jobs") or []) * 60 / e["evals"])
                              if e.get("evals") else None})
    for v in results.values():
        v.sort(key=lambda r: (r["brief"], -TIER_RANK[r["tier"]]))
    out = []
    for e in catalog(root):
        cfg = cfgs.get(e.get("name"), {})
        k = int(cfg.get("n_knobs") or 0)
        compat = {}
        for b in briefs:
            ok, why = is_compatible(e, b["brief"])
            compat[b["name"]] = {"ok": ok, "reason": why}
        out.append(clean({
            "name": e.get("name"), "group": e.get("group"), "symmetry": e.get("symmetry"),
            "description": e.get("description"), "config": cfg.get("path"), "n_knobs": k,
            "disabled": bool(cfg.get("disabled")),
            "budget": {"screen": budget_for_tier("screen", k), "compare": budget_for_tier("compare", k)},
            "compat": compat, "results": results.get(e.get("name"), [])}))
    order = {"classical": 0, "hybrid": 1, "magnus": 2, "legacy": 3}
    out.sort(key=lambda t: (order.get(t["group"], 9), t["name"] or ""))
    return out


# ---------------------------------------------------------------------------- evolution (time-lapse)

EVO_VERSION = 2


def _decimate(pts: list, n: int) -> list:
    if len(pts) <= n:
        return pts
    step = (len(pts) - 1) / (n - 1)
    return [pts[round(i * step)] for i in range(n)]


def _hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Convex hull (Andrew's monotone chain), counter-clockwise."""
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def mouth_outline(pts: np.ndarray, quadrants: str) -> list[list[float]] | None:
    """Front view of the mouth (mm): the convex outline of the mesh nodes within 1.5 % of the depth of the
    mouth plane, mirrored to the full mouth when the mesh is a quarter. Outer rim, shell included.
    (Mouths in these families are convex: round, elliptical or rounded-rectangular.)"""
    if pts is None or not len(pts):
        return None
    z0, z1 = float(pts[:, 2].min()), float(pts[:, 2].max())
    rim = pts[pts[:, 2] >= z1 - 0.015 * max(z1 - z0, 1e-9)]
    if len(rim) < 3:
        return None
    xy = [(float(x), float(y)) for x, y in rim[:, :2]]
    if str(quadrants) == "1":
        xy = xy + [(-x, y) for x, y in xy] + [(-x, -y) for x, y in xy] + [(x, -y) for x, y in xy]
    return [[round(x * 1000, 1), round(y * 1000, 1)] for x, y in _hull([(round(a, 6), round(b, 6)) for a, b in xy])]


def _frame_geometry(design_dir: Path) -> dict | None:
    nt = mesh_nodes_tris(design_dir / "mesh.msh")
    if nt is None:
        return None
    pts, tris = nt
    meta = _read_json(design_dir / "mesh_meta.json") or {}
    q = ((meta.get("result") or {}).get("quadrants")) or "1234"
    sec: dict = {}
    for key, ax in (("h", 0), ("v", 1)):
        chains = _plane_chains(pts, tris, ax) if len(tris) else []
        if chains:
            ch = max(chains, key=len)
            sec[key] = _decimate([[round(float(pts[i, 2]) * 1000, 1), round(float(pts[i, ax]) * 1000, 1)] for i in ch], 90)
            sec["kind"] = "section"
    return {"section": sec or None, "mouth": mouth_outline(pts, q)}


def evolution(runs: Path, run_id: str) -> dict:
    """Every evaluation of a run in order, for the time-lapse player: score, failure kind, normalised shape
    parameters, and (when the design was meshed) its wall cross-section and mouth outline. Geometry comes
    only from the meshes the search saved. Cached in runs/.gui_cache (GUI-owned), keyed on the run's
    search.ndjson size + mtime, so a running search is re-read as it grows."""
    d = _resolve_run(runs, run_id)
    nd = d / "search.ndjson"
    st = nd.stat()
    cache = runs / ".gui_cache" / f"evolution_{run_id}.json"
    old = _read_json(cache) if cache.exists() else None
    key = [EVO_VERSION, st.st_size, int(st.st_mtime)]
    if old and old.get("key") == key:
        return old["data"]
    rows = read_ndjson(nd)
    cfg = _config(d)
    bounds = {k: b for k, b in (cfg.get("bounds") or {}).items()
              if isinstance(b, dict) and "lo" in b and "hi" in b and b.get("search", True)}
    same_version = bool(old) and (old.get("key") or [None])[0] == EVO_VERSION
    prev = ({f["hash"]: f for f in old["data"].get("frames", []) if f.get("geo")}       # reuse geometry while
            if same_version else {})                                                    # the search grows
    frames, best = [], None
    geo_by_hash: dict[str, dict | None] = {}
    for r in rows:
        h = r.get("design_hash")
        ok = bool(r.get("ok")) and r.get("objective") is not None
        j = float(r["objective"]) if ok else None
        improved = ok and (best is None or j < best)
        if improved:
            best = j
        kv = _knob_values(r)
        knobs = {k: (None if k not in kv else round((kv[k] - float(b["lo"])) / ((float(b["hi"]) - float(b["lo"])) or 1), 4))
                 for k, b in bounds.items()}
        if h not in geo_by_hash:
            if h in prev:
                geo_by_hash[h] = prev[h]["geo"]
            elif HASH.match(h or "") and (d / "designs" / h / "mesh.msh").exists():
                geo_by_hash[h] = _frame_geometry(d / "designs" / h)
            else:
                geo_by_hash[h] = None
        frames.append({"n": r.get("n"), "hash": h, "j": j, "ok": ok, "improved": bool(improved), "best_j": best,
                       "kind": None if ok else _err_kind(r), "cached": bool(r.get("cached")),
                       "knobs": knobs, "geo": geo_by_hash[h]})
    # fixed axes for the whole run, so motion on screen is the design changing, not the scale
    ext = {"rmax": 1.0, "z0": float("inf"), "z1": float("-inf"), "mmax": 1.0}
    for f in frames:
        g = f["geo"] or {}
        for k in ("h", "v"):
            for z, r_ in ((g.get("section") or {}).get(k) or []):
                ext["rmax"] = max(ext["rmax"], abs(r_)); ext["z0"] = min(ext["z0"], z); ext["z1"] = max(ext["z1"], z)
        for x, y in (g.get("mouth") or []):
            ext["mmax"] = max(ext["mmax"], abs(x), abs(y))
    data = clean({"run_id": run_id, "name": cfg.get("name"), "bounds": {k: [b["lo"], b["hi"]] for k, b in bounds.items()},
                  "extent": ext, "frames": frames,
                  "n_improvements": sum(1 for f in frames if f["improved"])})
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".tmp")
        tmp.write_text(json.dumps({"key": key, "data": data}), encoding="utf-8")
        tmp.replace(cache)
    except OSError:
        pass
    return data
