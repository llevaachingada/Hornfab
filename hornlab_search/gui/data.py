"""Read-only views of run folders, campaigns, briefs and machine state for the local GUI.

Nothing here solves, meshes or writes: every number comes from files the CLI already wrote
(``search.ndjson``, ``config.yaml``, ``designs/<hash>/{metrics.json,response.npz,mesh.msh}``,
``campaign.json``, ``leaderboard.md``). Values are JSON-safe (NaN/Inf -> None).
"""
from __future__ import annotations

import copy
import csv
import json
import math
import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-z]+-[0-9a-f]{6}$")
CAMPAIGN_ID = re.compile(r"^campaign_[0-9]{8}T[0-9]{6}Z$")
HASH = re.compile(r"^[0-9a-f]{6,40}$")
STEP_NAME = re.compile(r"^[A-Za-z0-9_\-]{1,80}_rank\d+_[0-9a-f]{6,40}\.step$")
#: Design hash at the end of an exported STEP (``<config name>_rankN_<hash>.step`` for a run,
#: ``<config name>_seed_<hash>.step`` for a config). The suffix is the loader's own 12-hex hash
#: (``types._hash``), so the trailing group is unambiguous.
STEP_HASH = re.compile(r"_([0-9a-f]{6,40})\.step$")
BRIEF_NAME = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
#: pycma's own verbose-log files (``cma/*`` and ``cma/restart_k/*``), served raw/download-only.
#: Extensions are the ones pycma writes; anything executable or unknown is refused by the route.
CMA_LOG_NAME = re.compile(r"^(?!.*\.\.)[A-Za-z0-9_][A-Za-z0-9_.\-]{0,79}\.(?:txt|dat|json2|q)$")
CMA_RESTART_DIR = re.compile(r"^restart_[0-9]+$")
TOP_K = 6                       # "pinned" = most of the TOP_K best designs within 2 % of a bound
PIN_FRAC = 0.02


# ---------------------------------------------------------------------------- helpers

_SAFE_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def _yaml_load(text: str) -> Any:
    """``yaml.safe_load`` with the libyaml C loader when available (same safe tag set, ~10x faster
    on the hundreds of configs the read-only views parse)."""
    return yaml.load(text, Loader=_SAFE_LOADER)  # noqa: S506 - SafeLoader family only


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


def _as_dict(v: Any) -> dict:
    """A mapping or an empty one (read-only readers must tolerate a wrong type, never crash)."""
    return v if isinstance(v, dict) else {}


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
        return _yaml_load((run_dir / "config.yaml").read_text(encoding="utf-8")) or {}
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
    """Memoized on the run's search.ndjson stamp: list_runs and the auto campaigns both summarize
    every run on each refresh, and a finished run's summary never changes. ``active`` is computed
    AFTER the cache lookup on every call: a live run's stamp changes with every row, but an
    inactive run's stamp never does, so only the cache-miss path would ever refresh it."""
    # The stamp carries BOTH files' identities: a resume rewrites run.json (new command/budget/
    # resumes) at session start and at finish, and at finish the ndjson goes quiet — without the
    # run.json stamp a finished resumed run could keep a pre-finish memo all night.
    try:
        st = (run_dir / "search.ndjson").stat()
        nd = (st.st_mtime_ns, st.st_size)
        nd_mtime = st.st_mtime
    except OSError:
        nd, nd_mtime = None, None
    try:
        rj = (run_dir / "run.json").stat()
        rj = (rj.st_mtime_ns, rj.st_size)
    except OSError:
        rj = None
    try:
        vst = (run_dir / "verify" / "search.ndjson").stat()
        verify_stamp = (vst.st_mtime_ns, vst.st_size)
    except OSError:
        verify_stamp = None
    stamp = (nd, rj, verify_stamp) if (nd is not None or rj is not None or verify_stamp is not None) else None
    key = str(run_dir.resolve())
    hit = _RUN_SUMMARY_CACHE.get(key)
    if stamp is not None and hit is not None and hit[0] == stamp:
        hit[1]["active"] = bool(nd_mtime is not None and (time.time() - nd_mtime) < 120.0)
        return hit[1]
    out = _run_summary(run_dir)
    out["active"] = bool(nd_mtime is not None and (time.time() - nd_mtime) < 120.0)
    if stamp is not None:
        _RUN_SUMMARY_CACHE[key] = (stamp, dict(out))
    return out


#: ``resolved run dir -> ((ndjson mtime_ns, size), run_summary dict)``.
_RUN_SUMMARY_CACHE: dict[str, tuple] = {}


def _run_summary(run_dir: Path) -> dict:
    rows = read_ndjson(run_dir / "search.ndjson")
    cfg = _config(run_dir)
    rj_sum = _as_dict(_read_json(run_dir / "run.json"))
    ok = [r for r in rows if r.get("ok")]
    best = min(ok, key=lambda r: r["objective"]) if ok else None
    brief = cfg.get("brief") if isinstance(cfg.get("brief"), dict) else None
    # WP1: verify attachment fields — additive, absent on plain screen runs.
    has_inline_verify = (run_dir / "verify" / "search.ndjson").is_file()
    verify_of_run_id: str | None = None
    if rj_sum.get("mode") == "verify" and "verify_of" in rj_sum:
        from pathlib import PureWindowsPath as _PWin, PurePosixPath as _PPosix
        vo_run = _as_dict(rj_sum.get("verify_of")).get("run") or ""
        for _cls in (_PWin, _PPosix):
            try:
                name = _cls(vo_run).name
                if name:
                    verify_of_run_id = name
                    break
            except (ValueError, TypeError):
                pass
    resumes = _resumes(run_dir)
    b = _ts(resumes[-1]) if resumes else None
    if b is not None:
        srows = [r for r in rows if (_t := _ts(r.get("created_utc"))) and _t >= b]
    else:
        srows = rows
    ok_s = [r for r in srows if r.get("ok")]
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
        "objective_version": run_objective_version(run_dir),
        "started": rows[0].get("created_utc") if rows else None,
        "last": rows[-1].get("created_utc") if rows else None,
        "has_report": (run_dir / "report.html").exists(),
        "dims": horn_dims(best),
        "budget": _command_flags(run_dir).get("max_evals") or _command_flags(run_dir).get("budget"),
        "cma_seed": _command_flags(run_dir).get("cma_seed"),
        "has_inline_verify": has_inline_verify,
        "verify_of_run_id": verify_of_run_id,
        # session accounting (2026-11-12): a resumed run's budget belongs to its CURRENT
        # invocation; session_n counts only the rows written since (see run_progress).
        "resumed": bool(resumes),
        "n_resumes": len(resumes),
        "session_n": len(srows),
        "session_best_j": min((r["objective"] for r in ok_s), default=None),
        "has_verify": (run_dir / "verify" / "search.ndjson").exists(),
    })


def list_runs(runs: Path, limit: int | None = None) -> list[dict]:
    """Every run under ``runs`` (no cap: anything a search wrote must show up)."""
    dirs = _run_dirs(runs)
    out = [run_summary(d) for d in (dirs if limit is None else dirs[:limit])]
    # Additive (GUI plan WP4): mark parents that have a linked verify run, so the Runs list can
    # badge "verified designs" without the client cross-referencing. Copies: run_summary is cached.
    parents = {s.get("verify_of_run_id") for s in out if s.get("verify_of_run_id")}
    if parents:
        out = [dict(s, has_verify_runs=True) if s.get("id") in parents else s for s in out]
    return out


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


#: wall profiles keyed by mesh path -> ((mtime, size), profile). Parsing a .msh costs ~75 ms and the
#: campaign/typology views ask for the same few hundred designs on every call.
_PROFILE_CACHE: dict[str, tuple] = {}
_PROFILE_CACHE_MAX = 2048


def _profile_from_mesh(msh: Path) -> dict:
    try:
        st = msh.stat()
        stamp = (st.st_mtime, st.st_size)
    except OSError:
        stamp = None
    key = str(msh)
    hit = _PROFILE_CACHE.get(key)
    if stamp is not None and hit and hit[0] == stamp:
        return copy.deepcopy(hit[1])
    prof = _profile_from_mesh_uncached(msh)
    if stamp is not None:
        if len(_PROFILE_CACHE) >= _PROFILE_CACHE_MAX:
            _PROFILE_CACHE.pop(next(iter(_PROFILE_CACHE)))
        _PROFILE_CACHE[key] = (stamp, copy.deepcopy(prof))
    return prof


def _profile_from_mesh_uncached(msh: Path) -> dict:
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


def design_curves(run_dir: Path, h: str, tier: str = "screen") -> dict | None:
    """Per-frequency metrics, normalised polar maps and the wall profile of one solved design.

    ``tier`` selects the design directory:
    * ``"screen"`` (default): ``run_dir / "designs" / h``
    * ``"verify"``: ``run_dir / "verify" / "designs" / h`` (inline verify layout)

    For linked/standalone verify runs the caller passes the verify run's own ``run_dir``; in that
    case use the default tier (the linked run's ``designs/`` dir is screen-layout relative to it).
    """
    if tier not in ("screen", "verify"):
        raise ValueError(f"unknown tier {tier!r}; must be 'screen' or 'verify'")
    if not HASH.match(h):
        raise ValueError(f"not a design hash: {h!r}")
    if tier == "verify":
        d = run_dir / "verify" / "designs" / h
    else:
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


def _band_meta_paths(design_dir: Path) -> list[Path]:
    """A design's top-level ``mesh_meta.json`` plus any WP8 band meshes, in band order.

    A band-split design (``mesh.band_split``) writes one mesh per band under ``band{k}/`` and no
    top-level meta; both routes put the same ``cad`` provenance block in each meta.
    """
    def _band_index(p: Path) -> int:
        m = re.match(r"band(\d+)$", p.parent.name)
        return int(m.group(1)) if m else 10 ** 9

    bands = sorted(design_dir.glob("band*/mesh_meta.json"),
                   key=lambda p: (_band_index(p), p.as_posix()))
    return [design_dir / "mesh_meta.json", *bands]


def _design_cad_block(design_dir: Path) -> dict | None:
    """The ``mesh_meta.json["cad"]`` provenance block of one design, or None.

    Read verbatim from what ``mesh/step_build.py`` wrote; no key is renamed or invented. A
    non-cad design (formula/GRID) has no ``cad`` block, so its answer is None (never fabricated).
    """
    for meta_path in _band_meta_paths(design_dir):
        cad = _as_dict(_read_json(meta_path)).get("cad")
        if isinstance(cad, dict):
            return cad
    return None


def _cad_inventory(cad: dict) -> dict | None:
    """Project the current ``mesh_meta.json["cad"]`` block onto the G4 chip inventory contract.

    The block on disk today (``mesh/step_build.py``) is:
    ``face_inventory`` = ``{label: count}`` (NOT a ``faces`` list), ``tool_sha256`` (NOT
    ``tool_sha``), ``tool_path``, and ``solid.solids`` / ``solid.all_shells_closed``. The chip
    consumer takes the sidecar-shaped ``{faces: [{label, count}], solids, closed, tool_sha256,
    tool_path}``; only fields the block actually carries are emitted (nothing invented, no empty
    key), and a block with none of them answers None.
    """
    out: dict[str, Any] = {}
    face_inventory = cad.get("face_inventory")
    if isinstance(face_inventory, dict) and face_inventory:
        out["faces"] = [{"label": str(label), "count": count}
                        for label, count in sorted(face_inventory.items())]
    solid = _as_dict(cad.get("solid"))
    if solid.get("solids") is not None:
        out["solids"] = solid["solids"]
    if solid.get("all_shells_closed") is not None:
        out["closed"] = solid["all_shells_closed"]
    for key in ("tool_sha256", "tool_path"):
        if cad.get(key) is not None:
            out[key] = cad[key]
    return out or None


def _step_inventory(step_dir: Path, p: Path) -> Any:
    """Inventory for one exported STEP: the ``<name>.inventory.json`` sidecar WINS when present
    (parsed as-is), else the design's ``mesh_meta.json["cad"]`` block projected onto the chip
    contract, else None.

    The design hash is the trailing component of the exporter's name (``<name>_<tag>_<hash>.step``,
    ``cli.py export-step``), so a formula-route STEP resolves to its design but stays null unless
    that design was meshed on the cad route.
    """
    sidecar = step_dir / f"{p.stem}.inventory.json"
    if sidecar.is_file():
        return _read_json(sidecar)
    m = STEP_HASH.search(p.name)
    if m is None:
        return None
    cad = _design_cad_block(step_dir.parent / "designs" / m.group(1))
    return None if cad is None else _cad_inventory(cad)


def cma_dynamics(run_dir: Path) -> dict:
    """Parse pycma diagnostic files from ``<run>/cma/`` into a JSON-safe structure.

    Returns ``{"available": False}`` when ``cma/fit.dat`` is absent.

    Output when available::

        {
          "available": True,
          "gens": [
            {"iter": int, "evals": int, "sigma": float, "axis_ratio": float,
             "best": float|null, "p25": float|null, "median": float|null, "iqr": float|null},
            ...
          ],
          "stddev": [[float, ...], ...],  // per-gen per-param σ (len = n_params)
          "axis_lengths": [[float, ...], ...],  // sorted principal-axis lengths
          "param_names": [str, ...]  // from parameters.json2 or config.yaml, len = n_params
        }

    ``fit.dat`` column order (from the ``%`` header):
    iter(0) evals(1) sigma(2) axis_ratio(3) bestever(4) best(5) median(6) worst(7) iqr(8) p25(9)
    Values ``≥ 1000`` are penalty sentinels and are nulled out (the failed-eval marker).
    """
    cma_dir = run_dir / "cma"
    fit_path = cma_dir / "fit.dat"
    if not fit_path.is_file():
        return {"available": False}

    _PENALTY = 999.0  # nulled when val >= this (1000.0 is the pycma penalty)

    def _parse_dat(path: Path) -> list[list[float | None]]:
        """Return data rows from a pycma .dat file; % header lines are skipped."""
        rows: list[list[float | None]] = []
        try:
            with path.open(encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("%"):
                        continue
                    parts = line.split()
                    row: list[float | None] = []
                    for p in parts:
                        try:
                            v = float(p)
                            row.append(None if v >= _PENALTY else v)
                        except ValueError:
                            row.append(None)
                    if row:
                        rows.append(row)
        except OSError:
            pass
        return rows

    fit_rows = _parse_dat(fit_path)
    gens = []
    for r in fit_rows:
        if len(r) < 7:
            continue
        def _get(i: int) -> float | None:
            return r[i] if i < len(r) else None
        # column 3 = axis_ratio direct from fit.dat (already a ratio, never a penalty)
        axis_ratio_raw = r[3] if len(r) > 3 else None
        gens.append({
            "iter": int(r[0]) if r[0] is not None else None,
            "evals": int(r[1]) if r[1] is not None else None,
            "sigma": r[2],
            "axis_ratio": axis_ratio_raw,  # not a J value, no penalty null needed
            "best": _get(5),
            "p25": _get(9),
            "median": _get(6),
            "iqr": _get(8),
        })

    # stddev.dat: cols 0=iter 1=evals 2=sigma 3=void 4=void 5..N=per-param σ.
    # Keep the columns positionally aligned with ``param_names``: dropping a null/penalty column
    # would shift every later parameter and make the GUI draw a value in the wrong row.
    stddev_rows = _parse_dat(cma_dir / "stddev.dat") if (cma_dir / "stddev.dat").is_file() else []
    stddev = [r[5:] for r in stddev_rows]

    # axlen.dat: cols 0=iter 1=evals 2=sigma 3=max 4=min 5..N=all principal axes
    axlen_rows = _parse_dat(cma_dir / "axlen.dat") if (cma_dir / "axlen.dat").is_file() else []
    axis_lengths = [r[5:] for r in axlen_rows]

    # Parameter names: try parameters.json2 first, then config.yaml bounds keys
    param_names: list[str] = []
    params_path = cma_dir / "parameters.json2"
    if params_path.is_file():
        try:
            import json as _json
            with params_path.open(encoding="utf-8") as fh:
                p_data = _json.load(fh)
            if isinstance(p_data, dict) and "variable_names" in p_data:
                param_names = [str(n) for n in p_data["variable_names"]]
        except Exception:  # noqa: BLE001
            pass
    if not param_names:
        cfg = _config(run_dir)
        param_names = [k for k, v in (cfg.get("bounds") or {}).items()
                       if isinstance(v, dict) and v.get("search", True)]

    return clean({
        "available": True,
        "gens": gens,
        "stddev": stddev,
        "axis_lengths": axis_lengths,
        "param_names": param_names,
    })


def _cma_files(run_dir: Path) -> list[dict]:
    """Every pycma log the C-5 route serves: ``cma/`` plus each ``cma/restart_k/`` directory.

    The same ``CMA_LOG_NAME`` allow-list the serving route applies, so this list and the downloadable
    files cannot disagree. Records are run-relative POSIX paths sorted by path; an absent ``cma/``
    tree is ``[]``, never an invented row.
    """
    cma = run_dir / "cma"
    if not cma.is_dir():
        return []
    dirs = [cma]
    try:
        dirs += sorted((p for p in cma.iterdir()
                        if p.is_dir() and CMA_RESTART_DIR.match(p.name)),
                       key=lambda p: p.name)
    except OSError:
        pass
    out = []
    for base in dirs:
        try:
            entries = list(base.iterdir())
        except OSError:
            continue
        for p in entries:
            if not p.is_file() or not CMA_LOG_NAME.match(p.name):
                continue
            try:
                size = int(p.stat().st_size)
            except OSError:
                continue
            out.append({"path": p.relative_to(run_dir).as_posix(),
                        "name": p.name, "size": size})
    return sorted(out, key=lambda f: f["path"])


def _verify_summary(run_dir: Path) -> dict | None:
    """The run's verify re-solves (``verify --run X`` writes ``X/verify/search.ndjson``). Rows
    carry backend/lane when the two-lane runner produced them, so the view can pair a design's
    CPU and GPU solves. Absent dir = None (the detail key stays absent)."""
    vpath = run_dir / "verify" / "search.ndjson"
    if not vpath.exists():
        return None
    rows = read_ndjson(vpath)
    return clean({"n": len(rows), "rows": [
        {"design_hash": r.get("design_hash"), "objective": r.get("objective"),
         "backend": r.get("backend"), "lane": r.get("lane"),
         "created_utc": r.get("created_utc"), "ok": r.get("ok")} for r in rows]})


def _last_row_lane(ndjson: Path) -> str | None:
    """The ``lane`` tag of a search.ndjson's LAST row (``None`` on pre-two-lane rows, malformed
    tails, or unreadable files) — how current_run tells which lane owns a run dir."""
    try:
        with open(ndjson, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - 8192))
            tail = fh.read().decode("utf-8", "replace").strip()
        if not tail:
            return None
        row = json.loads(tail.splitlines()[-1])
        lane = row.get("lane")
        return str(lane).lower() if lane else None
    except Exception:  # noqa: BLE001 - attribution must never break the run scan
        return None


def run_detail(runs: Path, run_id: str, root: Path | None = None) -> dict:
    d = _resolve_run(runs, run_id)
    repo_root = Path(root) if root is not None else runs.parent
    rows = read_ndjson(d / "search.ndjson")
    cfg = _config(d)
    run_json = _read_json(d / "run.json") or {}
    summ = run_summary(d)
    best_hash, seed_hash = summ["best_hash"], (rows[0]["design_hash"] if rows else None)
    seed_ok = bool(rows and rows[0].get("ok"))
    best_row = next((r for r in rows if r.get("design_hash") == best_hash and r.get("ok")), None)
    # C-1/G4: STEP files stay the existing list of names (a frozen consumer contract) and the
    # inventory is exposed additively per file; without a sidecar it falls back to the design's own
    # mesh_meta cad block, and without either it is null, never fabricated. ``step_files_detail``
    # mirrors ``step_files`` 1:1 in sorted order.
    step_dir = d / "step"
    step_files = []
    step_files_detail = []
    if step_dir.is_dir():
        for p in sorted(step_dir.glob("*.step")):
            if STEP_NAME.match(p.name):
                step_files.append(p.name)
                step_files_detail.append(
                    {"name": p.name, "inventory": _step_inventory(step_dir, p)})
    out = clean({
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
        "command": run_json.get("command"),
        "step_files": step_files,
        "step_files_detail": step_files_detail,
        "objective_version": run_objective_version(d),
    })
    # Verify re-solves (2026-11-12): ``verify --run X`` writes ``X/verify/search.ndjson``; rows may
    # pair the same design across backends (the two-lane CPU/GPU cross-checks). Absent dir =
    # absent key, never fabricated.
    ver = _verify_summary(d)
    if ver is not None:
        out["verify"] = ver
    # Gate audit: a committed CSV (docs/data/gate_audit_*/ or scratch/gate_audit_*/) carries the
    # per-design pass/fail truth. Absent audit = the key stays absent, so the view renders no column.
    gate_audit = run_gate_audit(repo_root, run_id)
    if gate_audit.get("available"):
        out["gate_audit"] = clean(gate_audit)
    # WP1: verify attachment summary — always present so the detail view can offer "Open verify report".
    out["verification"] = clean({
        "has_inline_verify": (d / "verify" / "search.ndjson").is_file(),
        "verify_of": run_json.get("verify_of") if isinstance(run_json.get("verify_of"), dict) else None,
    })
    # Continue-run control: the last invocation's stop reason tells the run detail whether a budget
    # top-up is likely to do work (budget/interrupted) or the optimizer stopped on its own terms.
    # Same convention as below: present in run.json = pass it through, absent stays absent.
    if run_json.get("stop_reason") is not None:
        out["stop_reason"] = run_json["stop_reason"]
    # run.json["mode"] is the LAST invocation's fidelity (cma._prepare rewrites it on every resume),
    # while summary.mode (rows[0]) keeps the run's original mode. The continue control must carry the
    # current mode, or the CLI's "screen" default silently rewrites a verify/final run.
    if run_json.get("mode") is not None:
        out["mode"] = run_json["mode"]
    # C-1: WP11 provenance is written by the search only for the runs that have it. Present in
    # run.json = pass it through verbatim; absent = the key is absent here too (no shape invention).
    if isinstance(run_json.get("restarts"), list):
        out["restarts"] = clean(run_json["restarts"])
    if isinstance(run_json.get("qd"), dict):
        out["qd"] = clean(run_json["qd"])
    # CMA covariance snapshot (search/cma.py::covariance_summary) — additive; absent on old runs.
    if isinstance(run_json.get("cma_covariance"), dict):
        out["cma_covariance"] = clean(run_json["cma_covariance"])
        # Live pin recommendations from the same pure rules as ``hornlab-search pin-plan``.
        try:
            from hornlab_search.search.pin_from_cma import recommend_pins
            best = _read_json(d / "best.json") or {}
            best_params = best.get("params") if isinstance(best.get("params"), dict) else {}
            plan = recommend_pins(
                run_json["cma_covariance"],
                best_params=best_params,
                sens=out.get("sens") or [],
                bounds=cfg.get("bounds") if isinstance(cfg.get("bounds"), dict) else {},
            )
            out["pin_plan"] = clean(plan)
        except Exception:  # noqa: BLE001 - never fail run_detail on a diagnostic
            pass
    if isinstance(run_json.get("pin_plan"), dict) and "pin_plan" not in out:
        out["pin_plan"] = clean(run_json["pin_plan"])
    # G1 badge strip: the same solve-group fingerprint /api/compare exposes, always present for a
    # run (backend + solved-grid identity; every other key only when non-default).
    out["solve_group"] = _solve_group_fingerprint(d)
    # WP11a schedule from the committed config.yaml. Same validation rules as config.py
    # ``_validate_restarts`` (mode ipop|bipop, max int 0..64, both keys required); a malformed
    # block is disclosed as absent, never guessed.
    restarts_cfg = _as_dict(_as_dict(cfg.get("search")).get("restarts"))
    if set(restarts_cfg) == {"mode", "max"}:
        mode, mx = restarts_cfg.get("mode"), restarts_cfg.get("max")
        if (isinstance(mode, str) and mode in ("ipop", "bipop")
                and isinstance(mx, int) and not isinstance(mx, bool) and 0 <= mx <= 64):
            out["search_restarts"] = {"mode": mode, "max": int(mx)}
    cma_dir = d / "cma"
    out["restart_dirs"] = sorted(p.relative_to(d).as_posix() for p in cma_dir.glob("restart_*")
                                 if p.is_dir()) if cma_dir.is_dir() else []
    # C-5 companion: the exact pycma log files the raw route can serve, for direct restart-card
    # file chips. Sorted run-relative paths; [] when the run has no cma/ tree.
    out["cma_files"] = _cma_files(d)
    # WP10: CMA-ES dynamics from cma/fit.dat, stddev.dat, axlen.dat.  Additive: absent when
    # cma/ is missing (available:false is still included so the GUI knows it was attempted).
    out["cma_dynamics"] = cma_dynamics(d)
    # H7: atlas link visibility — show the QD atlas btn only when the file actually exists.
    out["has_atlas"] = (d / "archive_heatmap.json").is_file()
    # S1a: the K-law feasibility preflight rides in the committed config.yaml (the merged cfg.raw
    # ``search/rundir.py::write_config_snapshot`` dumps). Pure passthrough — a truthy dict is
    # forwarded verbatim; an absent block stays absent (no shape invention).
    feasibility = cfg.get("feasibility")
    if isinstance(feasibility, dict) and feasibility:
        out["feasibility"] = clean(feasibility)
    # The active objective block rides in the same committed config.yaml. Additive passthrough
    # only: an absent block stays absent here too (no shape invention); the run-detail seed card
    # uses it to name the below-f0 scoring rule honestly.
    objective = cfg.get("objective") or (cfg.get("brief") or {}).get("objective")
    if objective is not None:
        out["objective"] = clean(objective)
    return out


def _solve_group_fingerprint(run_dir: Path) -> dict:
    """The solve group a comparison must never silently mix (GUI plan §3.9), read from the run's
    committed ``config.yaml`` + ``run.json``.

    Identity keys are always present when derivable: ``backend`` (always) and ``freqs_hz`` (the solved
    grid identity: mode + target band + verify points-per-octave). Every other key appears ONLY when
    the run deviates from the default (``rear_res_factor`` 1.0, ``cuda_fused`` false,
    ``source_motion`` normal, objective v1, ...). Nothing is parsed from solver output and no value is
    invented: an absent config key stays absent here.
    """
    cfg = _config(run_dir)
    rj = _as_dict(_read_json(run_dir / "run.json"))
    solve = _as_dict(cfg.get("solve"))
    mesh = _as_dict(cfg.get("mesh"))
    target = _as_dict(cfg.get("target"))
    grid = _as_dict(cfg.get("grid"))

    g: dict[str, Any] = {"backend": rj.get("backend") or solve.get("backend")}
    if solve.get("cuda_fused") is True:
        g["cuda_fused"] = True
    if solve.get("source_motion") not in (None, "normal"):
        g["source_motion"] = solve["source_motion"]
    alpha = solve.get("source_profile_alpha")            # WP16 ride key (committed in config.py)
    if isinstance(alpha, (int, float)) and not isinstance(alpha, bool) and float(alpha) != 0.0:
        g["source_profile_alpha"] = alpha
    # WP14: near_correction is one group key set by ANY of the three knobs; the two numbers stay
    # separate so two near-corrected runs with different cutoffs/orders still mix-warn.
    nc, nc_cut, nc_ord = (solve.get("near_correction"), solve.get("near_correction_cutoff"),
                          solve.get("near_correction_order"))
    if nc is not None or nc_cut is not None or nc_ord is not None:
        g["near_correction"] = bool(nc) if nc is not None else True
        if nc_cut is not None:
            g["near_correction_cutoff"] = nc_cut
        if nc_ord is not None:
            g["near_correction_order"] = nc_ord
    if solve.get("solve_precision") is not None:
        g["solve_precision"] = solve["solve_precision"]
    rear = mesh.get("rear_res_factor")
    try:
        rear_f = None if rear is None else float(rear)
    except (TypeError, ValueError):
        rear_f = None
    if rear_f is not None and rear_f != 1.0:
        g["rear_res_factor"] = rear
    bs = mesh.get("band_split")
    if isinstance(bs, dict) and isinstance(bs.get("edges_hz"), list) and bs["edges_hz"]:
        g["mesh_policy"] = "band_split_v1"                # the mesher's own provenance token (WP8)
        g["band_edges_hz"] = bs["edges_hz"]
    brief = _as_dict(cfg.get("brief"))
    mounting = cfg.get("mounting") or brief.get("mounting")   # WP12 key (absent until it lands)
    if isinstance(mounting, dict) and mounting:
        g["mounting"] = mounting
    obj = _as_dict(cfg.get("objective"))
    version = obj.get("version", rj.get("objective_version"))
    try:
        version_i = None if version is None else int(version)
    except (TypeError, ValueError):
        version_i = None
    if version_i is not None and version_i != 1:          # v1 is the unlabelled default
        g["objective_version"] = version_i
    mode = rj.get("mode")
    if mode is None:                                      # older run.json / fixtures: the id names it
        bits = run_dir.name.split("-")
        mode = bits[1] if len(bits) >= 3 else None
    ident: dict[str, Any] = {}
    if mode is not None:
        ident["mode"] = mode
    for key in ("band_lo_hz", "band_hi_hz"):
        if target.get(key) is not None:
            ident[key] = target[key]
    if grid.get("verify_points_per_octave") is not None:
        ident["verify_points_per_octave"] = grid["verify_points_per_octave"]
    if ident:
        g["freqs_hz"] = ident
    # WP14: a cad recipe is PER DESIGN (``Design.params["cad"]``; config.yaml carries none), so a
    # run-level marker cannot come from the config. Proxy: the cad block of the best-objective
    # SUCCESSFUL row's mesh_meta.json, or of the seed row when nothing succeeded. A non-cad run has
    # no such block, so the key stays absent (only-when-non-default).
    rows = read_ndjson(run_dir / "search.ndjson")
    wins = [r for r in rows if r.get("ok") and r.get("objective") is not None]
    proxy = min(wins, key=lambda r: r["objective"]) if wins else (rows[0] if rows else None)
    proxy_hash = str((proxy or {}).get("design_hash") or "")
    if HASH.match(proxy_hash) and _design_cad_block(run_dir / "designs" / proxy_hash) is not None:
        g["cad_route"] = True
    qd = rj.get("qd")
    if isinstance(qd, dict) and qd.get("algorithm"):
        g["qd_algorithm"] = qd["algorithm"]
    return clean(g)


def solve_group_fingerprints(run_a: Path, run_b: Path) -> tuple[dict, dict, list[str]]:
    """(``group_a``, ``group_b``, ``mixed_keys``) for ``GET /api/compare`` (C-2). ``mixed_keys`` is
    the sorted set of fingerprint keys whose values differ (a key absent on one side counts)."""
    ga, gb = _solve_group_fingerprint(run_a), _solve_group_fingerprint(run_b)
    mixed = sorted(k for k in set(ga) | set(gb) if ga.get(k) != gb.get(k))
    return ga, gb, mixed


def run_objective_version(run_dir: Path) -> int:
    """The run's objective version, with v1 as the unlabelled default.

    Reads the same two places as ``_solve_group_fingerprint``: the committed config's
    ``objective.version`` (top level or inside ``brief``) and ``run.json``'s
    ``objective_version`` sidecar. A missing or malformed value is v1, never a guess.
    """
    cfg = _config(run_dir)
    rj = _as_dict(_read_json(run_dir / "run.json"))
    obj = _as_dict(cfg.get("objective")) or _as_dict(_as_dict(cfg.get("brief")).get("objective"))
    version = obj.get("version")
    if version is None:
        version = rj.get("objective_version")
    if isinstance(version, bool):
        return 1
    try:
        return int(version) if version is not None else 1
    except (TypeError, ValueError):
        return 1


#: Recognised gate-audit columns, in display order. The committed audit writes h/v/di/bw8k/
#: load/throat; newer audits may add f11 and CD aliases. Only columns present in the CSV render.
GATE_AUDIT_COLUMNS = ("throat", "load", "f11", "cd", "cd_h", "cd_v", "h", "v", "di", "bw8k")
GATE_AUDIT_LABELS = {
    "throat": "round throat",
    "load": "loading",
    "f11": "f11",
    "cd": "CD",
    "cd_h": "CD H",
    "cd_v": "CD V",
    "h": "CD H",
    "v": "CD V",
    "di": "DI rise",
    "bw8k": "8 kHz BW",
}


def _csv_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("true", "1", "yes", "pass", "y"):
            return True
        if text in ("false", "0", "no", "fail", "n"):
            return False
    return None


def _gate_audit_paths(root: Path):
    """Gate-audit CSVs under ``docs/data/gate_audit_*`` and ``scratch/gate_audit_*`` (newest first)."""
    for rel in ("docs/data", "scratch"):
        base = root / rel
        if not base.is_dir():
            continue
        for d in sorted(base.glob("gate_audit_*"), key=lambda p: p.name, reverse=True):
            p = d / "gate_audit.csv"
            if p.is_file():
                yield p


def run_gate_audit(root: Path, run_id: str) -> dict:
    """Per-design gate pass/fail for one run, from a committed gate-audit CSV.

    Returns ``{"available": False}`` when no audit directory carries this run — the GUI must never
    invent a gate column. When available: ``source`` (run-relative path), ``gates`` (only the
    recognised columns present in the header), ``labels`` and ``designs`` mapping
    ``design_hash -> {"gates": {column: bool}, "J": float|None, "tier": str|None}``. A design's
    verify row replaces its screen row (the audit's own precedence), and the lower-J row wins a tie.
    """
    for csv_path in _gate_audit_paths(root):
        try:
            with csv_path.open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
        except OSError:
            continue
        if not rows:
            continue
        header = set(rows[0].keys())
        gates = [key for key in GATE_AUDIT_COLUMNS if key in header]
        if not gates:
            continue
        sub = [r for r in rows if (r.get("run") or "").strip() == run_id]
        if not sub:
            continue
        designs: dict[str, dict] = {}
        for r in sub:
            design = (r.get("design") or "").strip()
            if not design:
                continue
            parsed = {key: _csv_bool(r.get(key)) for key in gates}
            parsed = {key: val for key, val in parsed.items() if val is not None}
            if not parsed:
                continue
            j_raw = r.get("J")
            try:
                j = float(j_raw) if j_raw not in (None, "") else None
            except (TypeError, ValueError):
                j = None
            tier = (r.get("tier") or "").strip() or None
            # verify rows outrank screen rows; then the lower J wins (deterministic).
            score = (0 if tier == "verify" else 1, j if j is not None else float("inf"))
            prev = designs.get(design)
            if prev is None or prev["_score"] > score:
                designs[design] = {"gates": parsed, "J": j, "tier": tier, "_score": score}
        if not designs:
            continue
        for entry in designs.values():
            entry.pop("_score", None)
        try:
            source = csv_path.relative_to(root).as_posix()
        except ValueError:
            source = str(csv_path)
        return {
            "available": True,
            "source": source,
            "gates": gates,
            "labels": {key: GATE_AUDIT_LABELS.get(key, key) for key in gates},
            "designs": designs,
        }
    return {"available": False}


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


def mesh_surface(runs: Path, run_id: str, h: str, tier: str = "screen",
                 max_tris: int = 60000) -> dict:
    """Triangle surface of a solved design (mm), the meshed domain only (a quarter for quadrants '1',
    an x/y half for '14'/'12').

    ``tier`` selects the design directory (see ``design_curves`` for the convention).
    """
    if tier not in ("screen", "verify"):
        raise ValueError(f"unknown tier {tier!r}; must be 'screen' or 'verify'")
    d = _resolve_run(runs, run_id)
    if not HASH.match(h):
        raise ValueError(f"not a design hash: {h!r}")
    if tier == "verify":
        design_dir = d / "verify" / "designs" / h
    else:
        design_dir = d / "designs" / h
    nt = mesh_nodes_tris(design_dir / "mesh.msh")
    if nt is None:
        raise FileNotFoundError(f"{run_id}/{h}/mesh.msh")
    pts, tris = nt
    meta = _read_json(design_dir / "mesh_meta.json") or {}
    q = (meta.get("result") or {}).get("quadrants") or _row_quadrants(d, h) \
        or (_config(d).get("mesh") or {}).get("quadrants")
    snap_axes = {"1": (0, 1), "14": (0,), "12": (1,)}.get(str(q), ())
    out_pts, out_tris, decimated = _cluster_decimate(pts, tris, max_tris, snap_axes)
    out = {"quadrants": str(q or "1234"), "n_tris": int(len(tris)),
           "verts": np.round(out_pts * 1000, 2).ravel().tolist(),
           "tris": out_tris.ravel().tolist()}
    if decimated:
        out["decimated"] = True
    # WP12: ``mesh_meta.json["mounting"]`` (the mesher + normalized blocks) is served additively so
    # the 3D view can draw the solved mesh's own outline. Absent on every non-enclosure run — the
    # key then stays absent, never fabricated.
    mounting = meta.get("mounting")
    if isinstance(mounting, dict) and mounting:
        out["mounting"] = clean(mounting)
    return out


def _row_quadrants(run_dir: Path, h: str) -> str | None:
    """The quadrant string the search recorded for one design (mesh_meta.json may be absent — the
    GRID route writes none, see the build_mesh docstring in mesh/build.py:273 — but every evaluated
    row carries it)."""
    nd = run_dir / "search.ndjson"
    if not nd.is_file():
        return None
    for row in read_ndjson(nd):
        if row.get("design_hash") == h and row.get("quadrants"):
            return str(row["quadrants"])
    return None


# ---------------------------------------------------------------------------- balloon (W6)

#: Normalised window of the balloon display (design follows Boundary Lab's
#: JWSound/boundary-lab Balloon Plot, GPL-3.0; the implementation here is our own): 0 dB sits on
#: the on-axis direction, and anything below this floor collapses onto it.
BALLOON_MIN_DB = -30.0


def _balloon_label(design_dir: Path) -> str:
    """Short human label of one design: family, plus the wall kind the generator derived."""
    dj = _read_json(design_dir / "design.json") or {}
    fam = str(dj.get("family") or "?")
    gen = _as_dict(dj.get("generator"))
    kind = _as_dict(_as_dict(gen.get("derived")).get("h")).get("type")
    return f"{fam} · {kind}" if kind else fam


def balloon_designs(runs: Path, run_id: str) -> dict:
    """Design-picker payload for the balloon view: the run's successful designs ranked by
    objective (best first, TOP_K at most), each disclosing whether a stored-balloon
    ``response.npz`` is actually on disk. Read-only: file-existence probes only."""
    d = _resolve_run(runs, run_id)
    rows = [r for r in read_ndjson(d / "search.ndjson")
            if r.get("ok") and HASH.match(str(r.get("design_hash") or ""))]
    rows.sort(key=lambda r: float(r["objective"]) if r.get("objective") is not None else math.inf)
    seen, designs = set(), []
    for r in rows:
        h = str(r["design_hash"])
        if h in seen:
            continue
        seen.add(h)
        designs.append({"hash": h, "objective": r.get("objective"), "n": r.get("n"),
                        "has_balloon": (d / "designs" / h / "response.npz").is_file()})
        if len(designs) >= TOP_K:
            break
    return clean({"run_id": run_id, "name": _config(d).get("name"), "designs": designs})


def balloon(runs: Path, run_id: str, h: str, tier: str = "screen") -> dict:
    """One design's stored balloon (W6) for the GUI's three.js Balloon view.

    Reads only the ``response.npz`` the search already wrote. The per-direction order is
    theta-major exactly as stored (``balloon_layout``: index = i*nP + j; theta rows 0..180
    INCLUSIVE from +Z — both pole rows present, each holding the same direction for every phi;
    phi columns 0..360 counterclockwise from +X toward +Y, NO stored wrap column — the viewer
    closes the seam). Levels are relative to on-axis (the theta = 0 pole row), Float32-rounded
    and clipped to ``[BALLOON_MIN_DB, 0]`` dB — the Balloon display's window. Nothing is solved
    or interpolated here; bilinear interpolation on the grid is a viewer concern.

    ``tier`` selects the design directory (see ``design_curves`` for the convention).
    """
    if tier not in ("screen", "verify"):
        raise ValueError(f"unknown tier {tier!r}; must be 'screen' or 'verify'")
    d = _resolve_run(runs, run_id)
    if not HASH.match(h):
        raise ValueError(f"not a design hash: {h!r}")
    if tier == "verify":
        p = d / "verify" / "designs" / h / "response.npz"
    else:
        p = d / "designs" / h / "response.npz"
    if not p.is_file():
        raise FileNotFoundError(f"{run_id}/{h}/response.npz")
    try:
        with np.load(p, allow_pickle=False) as z:
            freqs = np.asarray(z["freqs_hz"], float)
            spl = np.asarray(z["spl_balloon_db"], float)
            try:
                meta = json.loads(str(z["meta"]))
            except (ValueError, TypeError):
                meta = {}
            n_dof = int(z["n_dof"]) if "n_dof" in z.files else None
    except (OSError, KeyError) as exc:
        raise ValueError(f"unreadable balloon payload: {exc}") from exc
    grid = meta.get("balloon_grid")
    if not (isinstance(grid, list) and len(grid) == 2
            and all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in grid)):
        raise ValueError(f"balloon_grid {grid!r} does not match spl_balloon_db shape {spl.shape}")
    if spl.shape != (len(freqs), grid[0] * grid[1]):
        raise ValueError(f"balloon_grid {grid!r} does not match spl_balloon_db shape {spl.shape}")
    nT, nP = int(grid[0]), int(grid[1])
    ref = spl[:, 0:nP].mean(axis=1)                      # on-axis pole row (all phi, one direction)
    raw = spl - ref[:, None]
    rel = np.clip(raw, BALLOON_MIN_DB, 0.0).astype(np.float32)
    # Rev2 3.3: the display clip at 0 dB hides off-axis hot spots. Report them, unclipped.
    with np.errstate(invalid="ignore"):
        above = np.where(np.isfinite(raw), raw, -np.inf).max(axis=1)
    above = np.where(np.isfinite(above), above, np.nan)
    return clean({
        "run_id": run_id, "design": h, "label": _balloon_label(d / "designs" / h),
        "freqs_hz": _rnd(freqs, 1),
        "balloon_grid": [nT, nP],
        "layout": str(meta.get("balloon_layout") or ""),
        "n_dof": n_dof,
        "distance_m": meta.get("distance_m") if isinstance(meta.get("distance_m"), (int, float)) else None,
        "min_db": BALLOON_MIN_DB,
        "max_above_axis_db": _rnd(above, 2),
        "clip_count_above_axis": [int(c) for c in (raw > 0.05).sum(axis=1)],
        "spl": rel.tolist(),
    })


# ---------------------------------------------------------------------------- campaigns


@dataclass
class _Snapshot:
    """One request's worth of campaign/brief filesystem reads, each performed at most once.

    One ``/api/leaders`` call used to re-walk every run dir ~43 times and re-parse every brief
    YAML ~48 times, because each campaign in the list rebuilt the auto groups and the brief list
    from scratch.  This object is built at the public entry point and threaded down
    (``list_campaigns`` -> ``_auto_groups`` -> ``_auto_campaign_detail`` -> ``campaign_detail``),
    so the walks/parses/globs happen once per call.  Every field is filled lazily, so an entry
    point that needs only the briefs never pays for the run summaries.

    Deliberately NOT cached at module level: it lives for exactly one call, so a campaign
    directory written between two requests is always seen by the next one, and a live search's
    growing ``search.ndjson`` is re-read through ``run_summary``'s own per-file stamp memo.
    """

    runs: Path
    root: Path
    _briefs: list[dict] | None = field(default=None, repr=False)
    _claimed: set[str] | None = field(default=None, repr=False)
    _run_list: list[tuple[Path, dict]] | None = field(default=None, repr=False)
    _auto: dict[str, list[tuple[Path, dict]]] | None = field(default=None, repr=False)
    _evidence: set[str] | None = field(default=None, repr=False)

    def briefs(self) -> list[dict]:
        if self._briefs is None:
            self._briefs = list_briefs(self.root)
        return self._briefs

    def brief(self, name: str | None) -> dict:
        """The raw YAML body of the brief called ``name`` ({} when no brief has that name)."""
        return next((b["brief"] for b in self.briefs() if b["name"] == name), {})

    def claimed(self) -> set[str]:
        if self._claimed is None:
            self._claimed = _campaign_run_ids(self.runs)
        return self._claimed

    def run_list(self) -> list[tuple[Path, dict]]:
        if self._run_list is None:
            self._run_list = [(d, run_summary(d)) for d in _run_dirs(self.runs)]
        return self._run_list

    def auto_groups(self) -> dict[str, list[tuple[Path, dict]]]:
        if self._auto is None:
            self._auto = _group_auto_runs(self.run_list(), self.claimed())
        return self._auto

    def evidence(self) -> set[str]:
        if self._evidence is None:
            self._evidence = _evidence_campaigns(self.runs)
        return self._evidence


def _snapshot(runs: Path, root: Path | None = None) -> _Snapshot:
    """A fresh per-request snapshot.  Never stored by the module (see ``_Snapshot``)."""
    return _Snapshot(runs=runs, root=runs.parent if root is None else root)


def _evidence_campaigns(runs: Path) -> set[str]:
    """Campaign ids committed as evidence (docs/evidence/campaigns/<id>.campaign.json)."""
    d = runs.parent / "docs" / "evidence" / "campaigns"
    return {p.name.split(".")[0] for p in d.glob("campaign_*.campaign.json")} if d.is_dir() else set()


def superseded(runs: Path, cid: str, snap: _Snapshot | None = None) -> bool:
    """A campaign is superseded if it is older than the newest committed evidence campaign and is not
    itself committed evidence. The committed set is the reviewed record (campaigns before the
    2026-10-22 fixes scored native configs on their own targets without the size envelope; see
    docs/evidence/TYPOLOGY_SCREEN_2026-10-22.md); anything newer was run with the current code.

    ``snap`` supplies the precomputed evidence set (the glob ran per campaign before)."""
    if AUTO_ID.match(cid):
        return False
    ev = snap.evidence() if snap is not None else _evidence_campaigns(runs)
    return bool(ev) and cid not in ev and cid < max(ev)


def list_campaigns(runs: Path, snap: _Snapshot | None = None) -> list[dict]:
    """Every campaign of ``runs``: the real ones (campaign.json) newest first, then the auto
    campaigns for runs no campaign.json claims.  ``snap`` is one request's shared reads."""
    snap = snap if snap is not None else _snapshot(runs)
    out = []
    if not runs.is_dir():
        return out
    for p in sorted((p for p in runs.iterdir() if p.is_dir() and CAMPAIGN_ID.match(p.name)),
                    key=lambda p: p.name, reverse=True):
        c = _read_json(p / "campaign.json")
        if not c:
            continue
        out.append(clean({"id": p.name, "tier": c.get("tier"), "brief": c.get("brief_name"),
                          "superseded": superseded(runs, p.name, snap),
                          "seeds": c.get("seeds"), "n_entries": len(c.get("entries", [])),
                          "families": [e.get("name") for e in c.get("entries", [])]}))
    # Runs that no campaign.json claims (the night runner, a hand-launched or GUI-launched search)
    # still get a per-brief leaderboard: grouped by brief and mode, listed AFTER the real
    # campaigns so a real campaign of the same tier keeps precedence in leaders().
    for cid, members in sorted(snap.auto_groups().items()):
        names = sorted({s.get("name") or d.name for d, s in members})
        out.append(clean({"id": cid, "tier": members[0][1].get("mode") or "screen",
                          "brief": members[0][1].get("brief"), "superseded": False, "seeds": None,
                          "n_entries": len(names), "families": names, "auto": True,
                          "n_runs": len(members)}))
    return out


#: Auto campaign ids: ``auto_<brief name>__<mode>`` (brief names are BRIEF_NAME-safe).
AUTO_ID = re.compile(r"^auto_([A-Za-z0-9_.\-]+)__(screen|verify|final)$")


def _campaign_run_ids(runs: Path) -> set[str]:
    """Run ids already listed by some campaign.json (those runs belong to that campaign)."""
    out: set[str] = set()
    for p in (runs.iterdir() if runs.is_dir() else ()):
        if p.is_dir() and CAMPAIGN_ID.match(p.name):
            for e in (_read_json(p / "campaign.json") or {}).get("entries", []):
                for j in e.get("jobs") or []:
                    if j.get("run_dir"):
                        out.add(Path(j["run_dir"]).name)
    return out


def _group_auto_runs(run_list: list[tuple[Path, dict]],
                     claimed: set[str]) -> dict[str, list[tuple[Path, dict]]]:
    """Group the already-summarized runs (newest first) by ``auto_<brief>__<mode>``, skipping the
    runs a campaign.json claims and the runs without a brief (they stay in the run list only).
    Pure: the walks live on ``_Snapshot``."""
    groups: dict[str, list[tuple[Path, dict]]] = {}
    for d, s in run_list:
        if d.name in claimed:
            continue
        brief, mode = s.get("brief"), s.get("mode") or "screen"
        if not brief or not s.get("n"):
            continue
        cid = f"auto_{brief}__{mode}"
        if AUTO_ID.match(cid):
            groups.setdefault(cid, []).append((d, s))
    return groups


def _auto_groups(runs: Path, snap: _Snapshot | None = None) -> dict[str, list[tuple[Path, dict]]]:
    """Every run not claimed by a campaign.json, grouped by (brief, mode).

    ``snap`` is the request's shared reads; without one this builds its own, exactly as before."""
    if snap is None:
        snap = _snapshot(runs)
    return snap.auto_groups()


def _auto_campaign_detail(runs: Path, cid: str, snap: _Snapshot | None = None,
                          curves: bool = True) -> dict:
    """One auto campaign's entries.  ``curves=False`` is the leaderboard path: it drops the
    per-design curve payload (``best``) that ``leaders()`` never reads, keeping the standings."""
    snap = snap if snap is not None else _snapshot(runs)
    members = snap.auto_groups().get(cid)
    if not members:
        raise FileNotFoundError(cid)
    by_name: dict[str, list[tuple[Path, dict]]] = {}
    for d, s in members:
        by_name.setdefault(s.get("name") or d.name, []).append((d, s))
    entries = []
    for name, rs in by_name.items():
        js = [s["best_j"] for _, s in rs if s.get("best_j") is not None]
        best_d, best_s = min(((d, s) for d, s in rs if s.get("best_j") is not None),
                             key=lambda t: t[1]["best_j"], default=(None, None))
        best = (design_curves(best_d, best_s["best_hash"])
                if curves and best_s and best_s.get("best_hash") else None)
        entries.append({
            "name": name, "group": None, "symmetry": None, "skipped": False, "skip_reason": None,
            "family": rs[0][1].get("family"),
            "best_j": min(js) if js else None,
            "median_j": float(np.median(js)) if js else None,
            "spread": (max(js) - min(js)) if len(js) > 1 else None,
            "evals": sum(s.get("n") or 0 for _, s in rs),
            "failures": dict(sum((Counter(s.get("failures") or {}) for _, s in rs), Counter())),
            "pinned": [],
            "jobs": [{"seed": s.get("cma_seed") if s.get("cma_seed") is not None else d.name[-6:],
                      "best_j": s.get("best_j"), "run_id": d.name,
                      "returncode": None, "wall_min": None} for d, s in rs],
            "best": best, "dims": best_s.get("dims") if best_s else None,
            "best_run_id": best_d.name if best_d is not None else None,
        })
    entries.sort(key=lambda e: (e["best_j"] is None, e["median_j"] if e["median_j"] is not None else 0))
    brief = members[0][1].get("brief")
    brief_raw = snap.brief(brief)
    return clean({"id": cid, "tier": members[0][1].get("mode") or "screen", "brief": brief,
                  "seeds": None, "superseded": False, "auto": True,
                  "target": (brief_raw or {}).get("target"), "entries": entries,
                  "leaderboard_md": None})


def campaign_detail(runs: Path, cid: str, snap: _Snapshot | None = None,
                    curves: bool = True) -> dict:
    """One campaign's entries and brief target.  ``curves=False`` skips the per-design curve
    payload (``best`` stays None) for the leaderboard, which reads standings only; the detail
    views keep the default full payload."""
    snap = snap if snap is not None else _snapshot(runs)
    if AUTO_ID.match(cid):
        return _auto_campaign_detail(runs, cid, snap, curves)
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
                if curves and s.get("best_hash"):
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
    brief_raw = snap.brief(c.get("brief_name"))
    lb = runs / cid / "leaderboard.md"
    return clean({"id": cid, "tier": c.get("tier"), "brief": c.get("brief_name"), "seeds": c.get("seeds"),
                  "superseded": superseded(runs, cid, snap),
                  "target": (brief_raw or {}).get("target"),       # from the brief file named by the campaign
                  "entries": entries,
                  "leaderboard_md": lb.read_text(encoding="utf-8") if lb.exists() else None})


# ---------------------------------------------------------------------------- briefs


def brief_dirs(root: Path) -> tuple[Path, Path]:
    return root / "examples" / "briefs", root / "examples" / "briefs" / "user"


def list_briefs(root: Path, cached: list[dict] | None = None) -> list[dict]:
    """Every brief under examples/briefs/ at any depth: kind ``shipped`` (top level), ``user``
    (briefs/user/) or the subfolder path (e.g. a campaign folder).

    ``cached`` lets a per-request ``_Snapshot`` hand down its one parse; there is deliberately no
    module-level cache (a brief saved between two requests must show up on the next one)."""
    if cached is not None:
        return cached
    shipped, _user = brief_dirs(root)
    out = []
    files = sorted(p for p in shipped.rglob("*.yaml") if not p.name.startswith(".")) \
        if shipped.is_dir() else []
    for p in files:
        parent = p.parent.relative_to(shipped).as_posix()
        kind = "shipped" if parent == "." else ("user" if parent == "user" else parent)
        try:
            raw = _yaml_load(p.read_text(encoding="utf-8")) or {}
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


def _lock_payload(lock_path: Path) -> dict | None:
    from hornlab_search.search.gpulock import _pid_alive, _read_lock
    lock = _read_lock(lock_path)
    if lock:
        lock = dict(lock)
        lock["alive"] = bool(lock.get("pid") and _pid_alive(int(lock["pid"])))
    return lock


def _queue_payload(log: Path) -> dict:
    """One overnight queue log as the GUI shows it: its START/END/SKIP steps + the raw tail."""
    try:
        mtime = log.stat().st_mtime
    except OSError:
        mtime = 0.0
    payload = {"name": log.name, "mtime": mtime, "steps": queue_steps(log),
               "tail": tail_text(log, 30)}
    open_step = _open_step(payload["steps"])
    if open_step:
        payload["open_step"] = clean(open_step)
    return payload


def _open_step(steps: list[dict]) -> dict | None:
    """The most recent step that STARTed but has no END yet — the job running right now."""
    for st in reversed(steps):
        if st.get("started") and not st.get("ended") and not st.get("skipped"):
            return st
    return None


def _verify_target(argv: str | None) -> int | None:
    """The design count a queued verify job will re-solve (from its own START argv)."""
    if not argv:
        return None
    m = re.search(r"--top (\d+)", argv)
    if m:
        return int(m.group(1))
    m = re.search(r"--designs ([A-Za-z0-9,]+)", argv)
    if m:
        return len([x for x in m.group(1).split(",") if x])
    return None


def _lane_hosts(runs: Path, lane: str) -> dict:
    """Live vs stale BEAT host registry entries for one lane (runs/lanes/<lane>/workers/*)."""
    from hornlab_search.search.gpulock import _pid_alive
    d = runs / "lanes" / lane / "workers"
    live = stale = 0
    if d.is_dir():
        for f in d.glob("*.json"):
            if f.name.endswith(".key.json"):
                continue
            j = _read_json(f) or {}
            pid = j.get("pid")
            if isinstance(pid, int) and pid > 0 and _pid_alive(pid):
                live += 1
            else:
                stale += 1
    return {"live": live, "stale": stale}


def _cpu_activity(runs: Path, since_local=None, run_id: str | None = None,
                  max_age_s: float = 1800, command: str | None = None) -> dict | None:
    """The CPU lane's visible verify work. With ``run_id`` (parsed from the queued job's own
    ``--run``), count THAT run's ``verify/search.ndjson`` rows since the job started — even 0 rows
    while the first design is still solving (the file may not exist yet). Without it, fall back to
    the mtime-newest verify output (within ``max_age_s``). Verify jobs write into a subdir of the
    run they verify, so plain run enumeration never sees them (2026-11-12: both tonight's CPU
    verifies were invisible on every page)."""
    import time
    if run_id:
        run_dir = runs / run_id
        cmd = command or ""
        explicit = re.search(r'--verify-dir(?:=|\s+)(?:"([^"]+)"|\'([^\']+)\'|(\S+))', cmd)
        if explicit:
            out = Path(next(v for v in explicit.groups() if v is not None))
            if not out.is_absolute():
                out = runs.parent / out
            f = out / "search.ndjson"
        else:
            backend = re.search(r'--backend(?:=|\s+)(\S+)', cmd)
            stored = (_read_json(run_dir / "run.json") or {}).get("backend")
            linked = bool(re.search(r'--brief(?:=|\s+)', cmd) or
                          (backend and backend.group(1).strip('"\'') != stored))
            if linked:
                from hornlab_search.gui.data_verify import _match_parent
                candidates = []
                for candidate in _run_dirs(runs):
                    meta = _as_dict(_read_json(candidate / "run.json"))
                    parent = _as_dict(meta.get("verify_of")).get("run")
                    if meta.get("mode") == "verify" and isinstance(parent, str) and _match_parent(parent, run_id, runs):
                        started = _ts(meta.get("started_utc"))
                        if since_local is None or (started and started >= since_local):
                            candidates.append(candidate)
                if not candidates:
                    return clean({"run_id": run_id, "mode": "verify", "n": 0, "last": None})
                f = max(candidates, key=_mt) / "search.ndjson"
            else:
                f = run_dir / "verify" / "search.ndjson"
    else:
        best_f, best_t = None, 0.0
        for p in runs.glob("*/verify/search.ndjson"):
            try:
                t = p.stat().st_mtime
            except OSError:
                continue
            if t > best_t:
                best_f, best_t = p, t
        if best_f is None or time.time() - best_t > max_age_s:
            return None
        f = best_f
    rows = read_ndjson(f) if f.exists() else []
    if since_local is not None:
        rows = [r for r in rows if (_t := _ts(r.get("created_utc"))) and _t.astimezone() >= since_local]
    return clean({"run_id": run_id or f.parent.parent.name, "mode": "verify", "n": len(rows),
                  "last": rows[-1].get("created_utc") if rows else None})


def _parse_wall_ts(s: str | None):
    """A timestamp in either of this repo's two on-disk shapes: UTC ``...Z`` (ndjson) or local
    ``YYYY-MM-DDTHH:MM:SS`` (the night runner's queue-log lines). None if unparseable."""
    t = _ts(s)
    if t is not None:
        return t
    try:
        import datetime as dt
        return dt.datetime.fromisoformat(s or "").astimezone()
    except (TypeError, ValueError):
        return None


def _cpu_search_run_dir(runs: Path, night: str | None, job_id: str | None,
                        resume_arg: str | None) -> Path | None:
    """A CPU-lane SEARCH job's run dir: ``--resume`` names it directly; a fresh search prints
    ``output <dir>`` into the night's job log the moment it begins writing."""
    if resume_arg:
        p = Path(resume_arg)
        if not p.is_absolute():
            p = runs.parent / p
        return p if p.is_dir() else None
    if not night or not job_id:
        return None
    joblog = runs / "nights" / night / f"{job_id}.log"
    if not joblog.exists():
        return None
    for ln in reversed(tail_text(joblog, 80)):
        m = re.search(r"output (\S+)", ln)
        if m:
            p = Path(m.group(1))
            if not p.is_absolute():
                p = runs.parent / p
            return p if p.is_dir() else None
    return None


def status(root: Path, runs: Path) -> dict:
    import shutil
    from hornlab_search.search import hygiene
    from hornlab_search.search.gpulock import _lock_path, lane_lock_path
    lock = _lock_payload(_lock_path(runs))
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

    # Queue logs by RECENCY, not name: sorted-by-name picked 'v5_continue_2026-10-29' over every
    # current night because 'v' > 'g'/'c' (the Oct-29 steps shown as "the" queue all day).
    ov = runs / "overnight"
    qlogs = sorted((p for p in ov.glob("queue_*.log")),
                   key=lambda p: (_mt(p), p.name), reverse=True) if ov.is_dir() else []
    queues = [_queue_payload(p) for p in qlogs[:5]]

    # CPU second lane (2026-11-12): its lock, tonight's queue step, and live output. The lane
    # lock's command names the night ('night <name>'), which resolves the runner's own queue log
    # runs/overnight/queue_<night>.log — that log's open START line IS the running CPU job.
    # Verify jobs: rows at/after the job's start in <run>/verify/search.ndjson. Search jobs:
    # --resume names the run dir directly, a fresh search prints 'output <dir>' into the night's
    # job log the moment it starts (both feed run_progress, so session/rate/ETA carry over).
    cpu_lock = _lock_payload(lane_lock_path("cpu", runs))
    cpu_night, cpu_job = None, None
    if cpu_lock and cpu_lock.get("alive"):
        m = re.search(r"night (\S+)", str(cpu_lock.get("command") or ""))
        cpu_night = m.group(1) if m else None
        if cpu_night:
            qlog = ov / f"queue_{cpu_night}.log"
            if qlog.exists():
                step = _open_step(queue_steps(qlog))
                if step:
                    cmd = step.get("command") or ""
                    is_search = re.search(r" search --", cmd) is not None
                    m2 = re.search(r"--run (?:\"?runs[\\/])?([A-Za-z0-9_.\-\\/]+)", cmd)
                    run_id = m2.group(1).strip("\"\\/") if m2 else None
                    mbud = re.search(r"--budget (\d+)", cmd)
                    cpu_job = clean({"name": step.get("name"), "started": step.get("started"),
                                     "kind": "search" if is_search else "verify",
                                     "target": int(mbud.group(1)) if is_search and mbud else _verify_target(cmd),
                                     "run_id": run_id})
    cpu_since = _parse_wall_ts((cpu_job or {}).get("started")) if cpu_job else None
    cpu_run = (cpu_job or {}).get("run_id")
    cpu_current = None
    if cpu_lock and cpu_lock.get("alive"):
        if (cpu_job or {}).get("kind") == "search":
            rp = _cpu_search_run_dir(runs, cpu_night, (cpu_job or {}).get("name"), cpu_run)
            if rp is not None:
                p = run_progress(rp)
                cpu_current = clean({"run_id": rp.name, "mode": "screen", "n": p.get("n"),
                                     "last": p.get("last"), "session": p.get("session"),
                                     "rate_per_h": p.get("rate_per_h"), "eta_min": p.get("eta_min")})
        elif cpu_job or cpu_run:
            cpu_current = _cpu_activity(runs, since_local=cpu_since, run_id=cpu_run, command=cmd)

    gpu_hosts = _lane_hosts(runs, "gpu")
    cpu_hosts = _lane_hosts(runs, "cpu")
    return clean({
        "gpu_lock": lock, "vram_mib": vram, "julia_procs": len(procs), "disk": disk,
        "hosts": {"gpu": gpu_hosts["live"], "cpu": cpu_hosts["live"],
                  "stale": gpu_hosts["stale"] + cpu_hosts["stale"]},
        "cpu_lock": cpu_lock, "cpu_night": cpu_night, "cpu_job": cpu_job,
        "cpu_current": cpu_current,
        "queues": queues,
        # compat key, now newest-by-mtime (was sorted-by-name)
        "queue_log": queues[0] if queues else None,
        "current": run_progress(cur) if (lock and lock.get("alive") and (cur := current_run(runs))) else None,
    })


# ---------------------------------------------------------------------------- configs and catalog


def catalog(root: Path) -> list[dict]:
    try:
        raw = _yaml_load((root / "examples" / "catalog.yaml").read_text(encoding="utf-8-sig")) or {}
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


#: In-process memo for the disabled gate (ISSUES M4 local-only "GUI ``list_configs`` latency").
#: ``_config_seed_materializes`` runs the REAL generator march, and the rows kinds are brentq
#: loops (the saddle is ~25 rows), so re-materializing every seed on every refresh is the
#: visible latency the issue records.  The gate's whole input is the config file PLUS the brief
#: it names (the brief supplies the driver exit radius/angle the march starts from), so the key
#: is both files' (path, mtime_ns, size): an edited config -- or an edited brief -- re-materializes
#: on the next refresh, while an untouched pair is served from memory.  Deliberately process-local
#: (no on-disk staleness to clean up; a generator code change needs a GUI restart, exactly like
#: every other import).  Bounded by the number of config files.
_SEED_GATE_CACHE: dict[tuple, bool] = {}

# WP2b (GUI plan 2026-11-12): the march costs ~40 s cold for ~200 configs, paid on every GUI start.
# The memo is ALSO persisted to a per-user cache file OUTSIDE the repo/runs tree. To keep the
# "a generator code change needs a restart" guarantee, every entry carries a code fingerprint
# (the design/ + mesh/ sources' paths, mtimes and sizes, plus the installed mesher version): any
# code change makes every disk entry miss. HORNLAB_GUI_NO_DISK_CACHE=1 turns persistence off.
_SEED_DISK: dict | None = None
_SEED_DISK_DIRTY = False


def _seed_cache_file() -> Path | None:
    if os.environ.get("HORNLAB_GUI_NO_DISK_CACHE"):
        return None
    # Never touch the user's real cache file from the test suite unless a test opts in.
    if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("HORNLAB_GUI_DISK_CACHE_IN_TESTS"):
        return None
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "hornlab-search" / "gui_seed_gate_cache.json"


_CODE_STAMP: str | None = None


def _code_stamp() -> str:
    global _CODE_STAMP
    if _CODE_STAMP is None:
        import hashlib
        pkg = Path(__file__).resolve().parents[1]
        h = hashlib.sha256()
        for sub in ("design", "mesh", "config.py"):
            target = pkg / sub
            files = sorted(target.rglob("*.py")) if target.is_dir() else [target]
            for f in files:
                try:
                    st = f.stat()
                except OSError:
                    continue
                h.update(f"{f.relative_to(pkg).as_posix()}|{st.st_mtime_ns}|{st.st_size}\n".encode())
        try:
            from importlib.metadata import version
            h.update(("mesher=" + version("hornlab-waveguide-mesher")).encode())
        except Exception:  # noqa: BLE001 - missing metadata just narrows the fingerprint
            pass
        _CODE_STAMP = h.hexdigest()[:16]
    return _CODE_STAMP


def _seed_disk_key(key: tuple) -> str:
    return json.dumps([_code_stamp(), key])


def _seed_disk_get(key: tuple) -> bool | None:
    global _SEED_DISK
    if _SEED_DISK is None:
        _SEED_DISK = {}
        f = _seed_cache_file()
        if f is not None:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    _SEED_DISK = {k: v for k, v in data.items() if isinstance(v, bool)}
            except (OSError, ValueError):
                pass
    return _SEED_DISK.get(_seed_disk_key(key))


def _seed_disk_put(key: tuple, disabled: bool) -> None:
    global _SEED_DISK_DIRTY
    if _SEED_DISK is None:
        _seed_disk_get(key)
    _SEED_DISK[_seed_disk_key(key)] = disabled
    _SEED_DISK_DIRTY = True


def _seed_disk_flush() -> None:
    """Write the persisted memo once per list_configs call (atomic replace; failures are ignored —
    the cache is an optimisation, never a source of truth). Entries for other code stamps are
    dropped so the file cannot grow without bound."""
    global _SEED_DISK_DIRTY
    f = _seed_cache_file()
    if not _SEED_DISK_DIRTY or f is None or _SEED_DISK is None:
        return
    stamp = json.dumps(_code_stamp())
    keep = {k: v for k, v in _SEED_DISK.items() if k.startswith("[" + stamp + ",")}
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(keep), encoding="utf-8")
        os.replace(tmp, f)
        _SEED_DISK_DIRTY = False
    except OSError:
        pass


def _file_stamp(p: Path | None) -> tuple | None:
    if p is None:
        return None
    try:
        st = p.stat()
    except OSError:
        return None
    return (str(p.resolve()), st.st_mtime_ns, st.st_size)


def _seed_gate_key(p: Path, raw: dict, root: Path) -> tuple:
    """Memo key for one config: its own stamp + the stamp of the brief file it names."""
    brief = raw.get("brief_file") if isinstance(raw, dict) else None
    brief_p = None
    if isinstance(brief, str) and brief:
        for cand in (p.parent / brief, root / brief):      # cfg.load_config resolution order
            if cand.exists():
                brief_p = cand
                break
    return (_file_stamp(p), _file_stamp(brief_p))


def list_configs(root: Path) -> list[dict]:
    """Every runnable config under examples/ (not briefs, not the catalog), with its catalog entry."""
    cat = {e.get("config"): e for e in catalog(root)}
    ex = root / "examples"
    out = []
    for p in sorted(ex.rglob("*.yaml")):
        if (p.name == "catalog.yaml" or p.name.startswith(".")
                or p.relative_to(ex).parts[0] in ("briefs", "drivers")):
            continue
        try:
            raw = _yaml_load(p.read_text(encoding="utf-8-sig")) or {}
        except yaml.YAMLError:
            continue
        rel = p.relative_to(ex).as_posix()
        e = cat.get(rel, {})
        bounds = raw.get("bounds") or {}
        # honest gate: the seed materializes (never a name substring; lecleach is live).
        # Memoized on the config+brief stamps -- the march is the refresh's whole cost.
        key = _seed_gate_key(p, raw, root)
        disabled = _SEED_GATE_CACHE.get(key)
        if disabled is None:
            disabled = _seed_disk_get(key) if key[0] is not None else None
            if disabled is None:
                disabled = not _config_seed_materializes(p)
                if key[0] is not None:
                    _seed_disk_put(key, disabled)
            _SEED_GATE_CACHE[key] = disabled
        entry = clean({
            "path": p.relative_to(root).as_posix(), "name": raw.get("name") or p.stem,
            "family": raw.get("family"), "generator": isinstance(raw.get("generator"), dict),
            "brief_file": raw.get("brief_file"), "catalog_name": e.get("name"), "group": e.get("group"),
            "symmetry": e.get("symmetry"), "description": e.get("description"),
            "n_knobs": sum(1 for b in bounds.values() if isinstance(b, dict) and b.get("search", True)),
            "morph_capable": morph_capable(raw),
            "gcurve_capable": gcurve_capable(raw),
            "morph_searched": any(str(k).startswith("morph_") and isinstance(b, dict)
                                  and b.get("search", True) for k, b in bounds.items()),
            "disabled": disabled})
        # Additive, honest passthrough for the Compose wizard's hybrid views: the config's REAL
        # generator block (splice/blend/grid shapes exactly as yaml.safe_load yields) and the seed
        # geometry it previews from. Absent when the yaml has none -- never fabricated.
        gen = raw.get("generator")
        if isinstance(gen, dict) and gen:
            entry["generator_block"] = clean(gen)
        seed = raw.get("seed_params")
        if isinstance(seed, dict) and seed:
            entry["seed_params"] = clean(seed)
        if bounds:              # the sandbox's fallback when the param catalog has no entry yet
            entry["bounds"] = clean(bounds)
        out.append(entry)
    _seed_disk_flush()
    return out


# ---------------------------------------------------------------------------- live progress


def _resumes(run_dir: Path) -> list:
    """Every invocation's start UTC (run.json ``resumes``), oldest first. Empty when the run was
    never interrupted-and-resumed."""
    rj = _read_json(run_dir / "run.json") or {}
    r = rj.get("resumes")
    return r if isinstance(r, list) else []


def _span_rate(rows_or_ts, key="created_utc") -> float | None:
    """Rows per hour across the span first→last timestamp of the given rows."""
    t = [_ts(r.get(key)) for r in rows_or_ts]
    t = [x for x in t if x]
    if len(t) >= 2 and (t[-1] - t[0]).total_seconds() > 0:
        return (len(t) - 1) / (t[-1] - t[0]).total_seconds() * 3600
    return None


def run_progress(run_dir: Path) -> dict:
    """Evaluations done vs budget, best so far, rate and ETA from the run's own timestamps.

    Session-aware (2026-11-12): a resumed run's ``--budget`` (the run.json command regex) buys
    evals for the CURRENT invocation only, while ``n`` counts the run's lifetime rows. The session
    is the rows at/after the last ``run.json 'resumes'`` timestamp; a never-resumed run is its own
    session, which reproduces today's numbers exactly (rate over the whole row span, budget vs n).
    The old rate — last-40 rows — poisoned a resumed run's window with the pre-crash gap and
    reported e.g. 19/h while the session really ran at 76/h."""
    s = run_summary(run_dir)
    rows = read_ndjson(run_dir / "search.ndjson")
    resumes = _resumes(run_dir)
    b = _ts(resumes[-1]) if resumes else None
    if b is None:
        srows = rows
    else:
        srows = [r for r in rows if (_t := _ts(r.get("created_utc"))) and _t >= b]
    rate = _span_rate(srows) if len(srows) >= 2 else None
    budget = s.get("budget")
    n_s = len(srows)
    ok_s = [r for r in srows if r.get("ok")]
    left = (budget - n_s) if budget else None
    return clean({**s, "rate_per_h": rate,
                  "eta_min": (left / rate * 60) if (rate and left is not None and left > 0) else None,
                  "session": clean({"n": n_s, "budget": budget, "resumed": bool(resumes),
                                    "n_resumes": len(resumes),
                                    "started": resumes[-1] if resumes else s.get("started")}),
                  "failures_session": sum(1 for r in srows if not r.get("ok")),
                  "session_best_j": min((r["objective"] for r in ok_s), default=None)})


def current_run(runs: Path, max_age_s: float = 1800) -> Path | None:
    """The GPU lane's run folder: the ``search.ndjson`` written most recently (within ``max_age_s``)
    whose last row is NOT tagged to the CPU lane — with two live lanes, the newest-written dir can
    be the CPU lane's, and the GPU lock card must not swallow it.

    No ``[:30]`` slice: the newest-named 30 dirs are the ones a night queue is busy CREATING, so
    capping the scan hides the resumed (older-named) run it is actually appending to once ~5 new
    run dirs exist."""
    best, best_t = None, 0.0
    for d in _run_dirs(runs):
        f = d / "search.ndjson"
        try:
            m = f.stat().st_mtime
        except OSError:
            continue
        if m <= best_t:
            continue
        if _last_row_lane(f) == "cpu":
            continue
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


def _leader_run_facts(summary: dict | None) -> dict:
    """Additive leaderboard fields from the leading run's summary: whether any of its designs were
    verified (inline verify folder or a linked verify run), and its last activity (newest row)."""
    if not summary:
        return {"verified": False, "last_activity": None}
    return {"verified": bool(summary.get("has_inline_verify") or summary.get("has_verify_runs")),
            "last_activity": summary.get("last")}


def leaders(runs: Path, snap: _Snapshot | None = None) -> list[dict]:
    """Per brief, the leading family of the latest campaign of the strongest tier (compare beats
    screen; dry-run has no scores). 'clearly_ahead' applies the ranking rule: the leader's median beats
    the runner-up's by more than both spreads (screen tier has one repeat: never 'clearly').

    One snapshot for the whole call, and the per-campaign details are read with ``curves=False``:
    the leaderboard only reads standings, so the curve payloads (the bulk of the old 18 s) are
    never built.  Both are per-call, so a campaign dir created between two calls is seen by the
    second one."""
    snap = snap if snap is not None else _snapshot(runs)
    # Verification + recency per run (GUI plan WP5): one list_runs pass (summaries are cached).
    by_id = {s.get("id"): s for s in list_runs(runs)}
    chosen: dict[str, dict] = {}
    for c in list_campaigns(runs, snap):                 # newest first
        tier, brief = c.get("tier"), c.get("brief")
        if not brief or tier not in TIER_RANK or c.get("superseded"):
            continue
        cur = chosen.get(brief)
        if cur is None or TIER_RANK[tier] > TIER_RANK[cur["tier"]]:
            chosen[brief] = c
    out = []
    for brief, c in sorted(chosen.items()):
        try:
            d = campaign_detail(runs, c["id"], snap, curves=False)
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
                          "gap": gap, "clearly_ahead": clearly, "n_families": len(scored),
                          **_leader_run_facts(by_id.get(lead.get("best_run_id")))}))
    return out


# ---------------------------------------------------------------------------- typologies


def typologies(root: Path, runs: Path, snap: _Snapshot | None = None) -> list[dict]:
    """Every catalog family (classical, hybrid, Magnus-native, legacy) with: parameter count, brief
    compatibility (the CLI's own ``campaign.is_compatible``), the budgets a campaign would give it
    (``campaign.budget_for_tier``), and its best result in the latest campaign of the strongest tier per
    brief, with the best design's size and wall cross-section.

    One snapshot for the whole call; the per-campaign details keep their curve payloads (the
    profiles are part of this view)."""
    from hornlab_search.search.campaign import budget_for_tier, is_compatible
    snap = snap if snap is not None else _snapshot(runs, root)
    briefs = snap.briefs()
    cfgs = {c["catalog_name"]: c for c in list_configs(root) if c.get("catalog_name")}
    # per family: its result in the newest campaign of each scored tier per brief THAT CONTAINS IT
    # (a later campaign that re-ran only some families must not hide the others' last result)
    results: dict[str, list[dict]] = {}
    seen: set[tuple] = set()
    for c in list_campaigns(runs, snap):                 # newest first
        tier, brief = c.get("tier"), c.get("brief")
        if not brief or tier not in TIER_RANK or c.get("superseded"):
            continue
        try:
            d = campaign_detail(runs, c["id"], snap)
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
            "morph_capable": bool(cfg.get("morph_capable")),
            "morph_searched": bool(cfg.get("morph_searched")),
            "budget": {"screen": budget_for_tier("screen", k), "compare": budget_for_tier("compare", k)},
            "compat": compat, "results": results.get(e.get("name"), [])}))
    order = {"classical": 0, "hybrid": 1, "magnus": 2, "legacy": 3}
    out.sort(key=lambda t: (order.get(t["group"], 9), t["name"] or ""))
    return out


# ---------------------------------------------------------------------------- evolution (time-lapse)

EVO_VERSION = 2
M3D_VERSION = 2
M3D_DEFAULT_CAP = 30000


def _improvement_flags(rows: list[dict]) -> list[bool]:
    """Best-so-far transitions over the evaluation rows -- the ONE frame-selection rule shared by
    ``evolution()`` (2D) and ``evolution_frames3d()`` (3D), so the two players never disagree."""
    flags: list[bool] = []
    best = None
    for r in rows:
        ok = bool(r.get("ok")) and r.get("objective") is not None
        j = float(r["objective"]) if ok else None
        improved = False
        if j is not None:
            improved = best is None or j < best
            if improved:
                best = j
        flags.append(improved)
    return flags


def _decimate(pts: list, n: int) -> list:
    if len(pts) <= n:
        return pts
    step = (len(pts) - 1) / (n - 1)
    return [pts[round(i * step)] for i in range(n)]


def _cluster_once(pts: np.ndarray, tris: np.ndarray, cell: float,
                  snap_axes: tuple[int, ...]):
    """One vertex-clustering pass at grid size ``cell`` (metres): every occupied grid cell becomes
    one vertex at its members' centroid, indices are rebuilt, degenerate and duplicate triangles are
    dropped, and unused cells are compacted away. ``snap_axes`` holds the symmetry-plane axes of a
    quarter/half mesh; a cell that contains a vertex lying on such a plane keeps that coordinate at
    exactly zero, so the mirror seam stays gap-free."""
    keys = np.floor(pts / cell).astype(np.int64)
    _, inv = np.unique(keys, axis=0, return_inverse=True)
    inv = inv.ravel()
    ncell = int(inv.max()) + 1 if inv.size else 0
    sums = np.zeros((ncell, 3), dtype=float)
    np.add.at(sums, inv, pts)
    counts = np.bincount(inv, minlength=ncell).astype(float)
    reps = sums / counts[:, None]
    for ax in snap_axes:
        on = np.abs(pts[:, ax]) <= 1e-12
        if np.any(on):
            hit = np.zeros(ncell, dtype=bool)
            hit[inv[on]] = True
            reps[hit, ax] = 0.0

    t = inv[tris]
    keep = (t[:, 0] != t[:, 1]) & (t[:, 1] != t[:, 2]) & (t[:, 0] != t[:, 2])
    t = t[keep]
    if not t.size:
        return reps[:0], np.zeros((0, 3), dtype=np.int64)
    # Dedupe by sorted corner set: a collapsed quad would otherwise render as two coincident,
    # oppositely wound faces (z-fighting reads as flickering holes).
    _, first = np.unique(np.sort(t, axis=1), axis=0, return_index=True)
    t = t[np.sort(first)]
    used = np.unique(t)
    remap = -np.ones(len(reps), dtype=np.int64)
    remap[used] = np.arange(len(used))
    return reps[used], remap[t]


def _cluster_decimate(pts: np.ndarray, tris: np.ndarray, cap: int,
                      snap_axes: tuple[int, ...] = ()):
    """Hole-free triangle decimation toward ``cap`` triangles.

    Stride subsampling (``tris[::k]``) keeps every k-th triangle of a connected sheet, so half or
    more of the surface is punched out as scattered single-triangle holes — exactly the "randomly
    transparent triangles" the owner saw. Vertex clustering instead welds neighbouring vertices,
    which coarsens the sheet but keeps it continuous. The grid size is bisected on the surface's
    own area so the result lands just under ``cap`` (and never zero unless the budget is absurd).
    Returns ``(pts, tris, decimated)``; untouched when ``len(tris) <= cap``."""
    n_full = int(len(tris))
    if n_full <= cap:
        return pts, tris, False
    a, b, c = pts[tris[:, 0]], pts[tris[:, 1]], pts[tris[:, 2]]
    area = float(np.linalg.norm(np.cross(b - a, c - a), axis=1).sum()) * 0.5
    diagonal = float(np.linalg.norm(pts.max(axis=0) - pts.min(axis=0)))
    if not np.isfinite(area) or area <= 0 or diagonal <= 0:
        return pts, tris, False
    # A sheet occupies ~area/cell^2 cells; seed loosely around the count the budget implies.
    seed = math.sqrt(area / max(1.0, cap / 2.0))
    lo = max(seed * 1e-3, diagonal * 1e-6)   # fine grid: ~everything survives
    hi = max(seed * 3.0, diagonal)           # coarse grid: ~nothing survives
    best = None
    smallest = None
    for _ in range(20):
        cell = math.sqrt(lo * hi)
        rp, rt = _cluster_once(pts, tris, cell, snap_axes)
        if len(rt) > cap:
            lo = cell
            if smallest is None or len(rt) < len(smallest[1]):
                smallest = (rp, rt)
        else:
            if len(rt) and (best is None or len(rt) > len(best[1])):
                best = (rp, rt)
            hi = cell
        if hi / lo < 1.02:
            break
    rp, rt = best if best is not None else (smallest if smallest is not None else (pts, tris))
    return rp, rt, True


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
    flags = _improvement_flags(rows)
    geo_by_hash: dict[str, dict | None] = {}
    for i, r in enumerate(rows):
        h = r.get("design_hash")
        ok = bool(r.get("ok")) and r.get("objective") is not None
        j = float(r["objective"]) if ok else None
        improved = flags[i]
        if improved and j is not None:
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


def evolution_frames3d(runs: Path, run_id: str, max_tris_per_frame: int = M3D_DEFAULT_CAP) -> dict:
    """Per-improved-frame triangle geometry for the 3D time-lapse.

    Frame selection is EXACTLY ``evolution()``'s rule, shared through ``_improvement_flags``: a row
    is a frame when it is ok and sets a new best-so-far J. Only frames whose ``designs/<hash>/mesh.msh``
    the search actually saved are returned; an improved row without a saved mesh is skipped (never
    invented) and disclosed in ``note``. A frame above ``cap`` triangles is decimated hole-free by
    vertex clustering (``_cluster_decimate``); ``decimated`` is true exactly when that happened.

    Cache: ``runs/.gui_cache/evolution_<id>_m3d.json``, keyed on ``search.ndjson`` (size, mtime) plus
    every improved frame's ``mesh.msh`` (path, mtime_ns, size) -- a grown search or a (re)written/
    deleted mesh invalidates. ``mesh_meta.json``/``config.yaml`` are static run artifacts and stay
    outside the key (the same discipline as ``evolution()``'s geometry cache). The ndjson is always
    re-read so the key can be computed; the cache saves the expensive mesh parsing. Atomic write.
    """
    d = _resolve_run(runs, run_id)
    nd = d / "search.ndjson"
    cap = max(1, int(max_tris_per_frame))
    st = nd.stat()
    rows = read_ndjson(nd)
    cfg = _config(d)
    cfg_q = _as_dict(cfg.get("mesh")).get("quadrants")
    flags = _improvement_flags(rows)
    improved = [(i, r) for i, (r, imp) in enumerate(zip(rows, flags)) if imp]

    # Cache key: search.ndjson stamp + each improved hash's mesh stamp (None tuple when absent, so a
    # mesh appearing later invalidates too). Row order is stable for an unchanged ndjson.
    stamps: list[list] = []
    for _, r in improved:
        h = r.get("design_hash")
        p = d / "designs" / str(h) / "mesh.msh" if HASH.match(h or "") else None
        try:
            ms = p.stat() if p is not None else None
        except OSError:
            ms = None
        stamps.append([str(h) if h is not None else None,
                       ms.st_mtime_ns if ms else None, ms.st_size if ms else None])

    cache = runs / ".gui_cache" / f"evolution_{run_id}_m3d.json"
    key = [M3D_VERSION, cap, st.st_size, int(st.st_mtime), stamps]
    old = _read_json(cache) if cache.exists() else None
    if isinstance(old, dict) and old.get("key") == key:
        return old["data"]

    frames: list[dict] = []
    skipped: list[str] = []
    for _, r in improved:
        h = r.get("design_hash")
        if not HASH.match(h or ""):
            skipped.append(str(h))
            continue
        design_dir = d / "designs" / str(h)
        nt = mesh_nodes_tris(design_dir / "mesh.msh")
        if nt is None:
            skipped.append(str(h))
            continue
        pts, tris = nt
        meta = _as_dict(_read_json(design_dir / "mesh_meta.json"))
        q = (_as_dict(meta.get("result")).get("quadrants") or r.get("quadrants")
             or cfg_q or "1234")
        n_full = int(len(tris))
        snap_axes = {"1": (0, 1), "14": (0,), "12": (1,)}.get(str(q), ())
        out_pts, out_tris, decimated = _cluster_decimate(pts, tris, cap, snap_axes)
        frames.append(clean({
            "n": r.get("n"),
            "objective": float(r["objective"]) if r.get("objective") is not None else None,
            "mesh_hash": h,
            "quadrants": str(q),
            "verts": np.round(out_pts * 1000, 2).ravel().tolist(),
            "tris": out_tris.ravel().tolist(),
            "n_tris_full": n_full,
            "decimated": bool(decimated),
            "n_verts": int(len(pts)),
        }))

    available = bool(frames)
    if not rows:
        note = "no evaluations recorded yet"
    elif not improved:
        note = "no successful evaluation to animate (no improved frame)"
    elif not available or skipped:
        note = f"{len(skipped)} improved frame(s) skipped: no saved mesh"
    else:
        note = None
    data = clean({"run_id": run_id, "available": available, "cap": cap, "frames": frames})
    if note:
        data["note"] = note
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".tmp")
        tmp.write_text(json.dumps({"key": key, "data": data}), encoding="utf-8")
        tmp.replace(cache)
    except OSError:
        pass
    return data


#: Bump when the UMAP/PCA cloud payload shape or subsample rule changes.
UMAP_VERSION = 1
UMAP_MAX_PLOT = 500
UMAP_UNIT_EDGES = (0.0, 0.25, 0.5, 0.75, 1.0001)
UMAP_BAND_LABELS = ("u < 0.25", "0.25–0.5", "0.5–0.75", "u ≥ 0.75")


def _pca_2d(U: np.ndarray) -> np.ndarray:
    """Unit-box designs → 2-D PCA scores (numpy only; no sklearn)."""
    Uc = U - U.mean(axis=0, keepdims=True)
    # economy SVD; columns of Vh are principal axes
    _, _, vh = np.linalg.svd(Uc, full_matrices=False)
    k = min(2, vh.shape[0])
    Z = Uc @ vh[:k].T
    if k == 1:
        Z = np.column_stack([Z[:, 0], np.zeros(len(Z))])
    return Z


def _umap_2d(U: np.ndarray) -> np.ndarray | None:
    """Optional UMAP embed; ``None`` when umap-learn is not installed."""
    try:
        import umap  # type: ignore
    except ImportError:
        return None
    n = int(U.shape[0])
    if n < 5:
        return None
    n_neighbors = int(min(15, max(2, n - 1)))
    reducer = umap.UMAP(
        n_neighbors=n_neighbors,
        min_dist=0.1,
        n_components=2,
        metric="euclidean",
        random_state=42,
        n_jobs=1,
    )
    return np.asarray(reducer.fit_transform(U), dtype=float)


def run_umap_cloud(runs: Path, run_id: str, method: str = "auto", root: Path | None = None) -> dict:
    """2-D embedding of OK designs in the searchable unit box for the run explorer.

    Coordinates are **not** acoustic loadings: PCA (always) or UMAP when ``umap-learn`` is
    installed and ``method`` is ``auto``/``umap``. Cached under ``runs/.gui_cache/`` on the
    ``search.ndjson`` stamp + resolved method, same discipline as ``evolution()``.
    """
    want = str(method or "auto").strip().lower()
    if want not in ("auto", "umap", "pca"):
        raise ValueError(f"method must be auto|umap|pca, got {method!r}")
    d = _resolve_run(runs, run_id)
    repo_root = Path(root) if root is not None else runs.parent
    nd = d / "search.ndjson"
    st = nd.stat()
    rows = read_ndjson(nd)
    cfg = _config(d)
    version = run_objective_version(d)
    gate_audit = run_gate_audit(repo_root, run_id)
    gate_designs = gate_audit.get("designs", {}) if gate_audit.get("available") else {}
    gate_stamp = None
    if gate_audit.get("available"):
        try:
            gst = (repo_root / gate_audit["source"]).stat()
            gate_stamp = (gst.st_size, int(gst.st_mtime))
        except OSError:
            gate_stamp = None
    bounds = {
        k: b for k, b in (cfg.get("bounds") or {}).items()
        if isinstance(b, dict) and "lo" in b and "hi" in b and b.get("search", True)
    }
    keys = list(bounds.keys())
    if not keys:
        return clean({
            "run_id": run_id,
            "name": cfg.get("name"),
            "objective_version": version,
            "method": "pca",
            "method_requested": want,
            "keys": [],
            "bounds": {},
            "n_ok": 0,
            "n_plot": 0,
            "points": [],
            "note": "no searchable bounds on this run",
            "unit_edges": list(UMAP_UNIT_EDGES),
            "band_labels": list(UMAP_BAND_LABELS),
        })

    U_list: list[np.ndarray] = []
    J_list: list[float] = []
    hash_list: list[str | None] = []
    phys_list: list[dict[str, float]] = []
    lo = np.array([float(bounds[k]["lo"]) for k in keys], dtype=float)
    hi = np.array([float(bounds[k]["hi"]) for k in keys], dtype=float)
    span = np.where(hi > lo, hi - lo, 1.0)
    for r in rows:
        if not r.get("ok") or r.get("objective") is None:
            continue
        kv = _knob_values(r)
        if not all(k in kv for k in keys):
            continue
        x = np.array([float(kv[k]) for k in keys], dtype=float)
        u = np.clip((x - lo) / span, 0.0, 1.0)
        U_list.append(u)
        J_list.append(float(r["objective"]))
        hash_list.append(r.get("design_hash"))
        phys_list.append({k: float(kv[k]) for k in keys})

    n_ok = len(U_list)
    if n_ok == 0:
        return clean({
            "run_id": run_id,
            "name": cfg.get("name"),
            "objective_version": version,
            "method": "pca",
            "method_requested": want,
            "keys": keys,
            "bounds": {k: {"lo": float(bounds[k]["lo"]), "hi": float(bounds[k]["hi"])} for k in keys},
            "n_ok": 0,
            "n_plot": 0,
            "points": [],
            "note": "no OK evaluations with searchable params yet",
            "unit_edges": list(UMAP_UNIT_EDGES),
            "band_labels": list(UMAP_BAND_LABELS),
        })

    # Resolve method before cache so a machine without umap does not miss a PCA cache hit.
    umap_available = False
    try:
        import umap as _umap_probe  # noqa: F401
        umap_available = True
    except ImportError:
        umap_available = False
    note = None
    if want == "pca" or not umap_available:
        resolved = "pca"
        if want == "umap" and not umap_available:
            note = "umap-learn not installed; using PCA"
        elif want == "auto" and not umap_available:
            note = "PCA (install umap-learn for UMAP)"
    else:
        resolved = "umap"

    cache = runs / ".gui_cache" / f"umap_{run_id}_{resolved}.json"
    old = _read_json(cache) if cache.exists() else None
    key = [UMAP_VERSION, st.st_size, int(st.st_mtime), resolved, want,
           version, list(gate_stamp) if gate_stamp else None]
    if old and old.get("key") == key and isinstance(old.get("data"), dict):
        return old["data"]

    U = np.asarray(U_list, dtype=float)
    J = np.asarray(J_list, dtype=float)
    if resolved == "umap":
        Z = _umap_2d(U)
        if Z is None:
            note = "UMAP failed (too few points?); fell back to PCA"
            resolved = "pca"
            Z = _pca_2d(U)
        elif want == "auto":
            note = "UMAP (umap-learn)"
    else:
        Z = _pca_2d(U)
    order = np.argsort(J)
    keep: set[int] = set(int(i) for i in order[:40])
    stride = max(1, len(order) // max(1, UMAP_MAX_PLOT - 50))
    for i in range(0, len(order), stride):
        keep.add(int(order[i]))
    keep.update(int(i) for i in order[-10:])
    idx = sorted(keep)
    best_i = int(order[0])
    points = []
    for i in idx:
        u = {keys[j]: round(float(U[i, j]), 4) for j in range(len(keys))}
        params = {k: round(float(phys_list[i][k]), 6) for k in keys}
        gate = gate_designs.get(str(hash_list[i])) if gate_designs else None
        point = {
            "x": round(float(Z[i, 0]), 4),
            "y": round(float(Z[i, 1]), 4),
            "J": round(float(J[i]), 4),
            "b": int(i == best_i),
            "hash": hash_list[i],
            "u": u,
            "params": params,
        }
        if gate and gate.get("gates"):
            point["gates"] = gate["gates"]
        points.append(point)

    data = clean({
        "run_id": run_id,
        "name": cfg.get("name"),
        "objective_version": version,
        "method": resolved,
        "method_requested": want,
        "keys": keys,
        "bounds": {k: {"lo": float(bounds[k]["lo"]), "hi": float(bounds[k]["hi"])} for k in keys},
        "n_ok": n_ok,
        "n_plot": len(points),
        "j_min": float(J.min()),
        "j_max": float(J.max()),
        "default_key": keys[0],
        "points": points,
        "unit_edges": list(UMAP_UNIT_EDGES),
        "band_labels": list(UMAP_BAND_LABELS),
        "note": note,
    })
    if gate_audit.get("available"):
        data["gate_audit"] = {
            "source": gate_audit["source"],
            "gates": gate_audit["gates"],
            "labels": gate_audit["labels"],
        }
    # Re-key cache on the method that actually ran (auto→pca fallback shares pca cache).
    cache = runs / ".gui_cache" / f"umap_{run_id}_{resolved}.json"
    key = [UMAP_VERSION, st.st_size, int(st.st_mtime), resolved, want,
           version, list(gate_stamp) if gate_stamp else None]
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".tmp")
        tmp.write_text(json.dumps({"key": key, "data": data}), encoding="utf-8")
        tmp.replace(cache)
    except OSError:
        pass
    return data


# ---------------------------------------------------------------------------- sandbox preview

#: Coarse density the 2026-10-25 sandbox spike measured for the formula/native preview route
#: (65 angular x 24 axial): 17-35 ms including 3D on the idle machine. Grid/rows kinds use the
#: config's own march arrays instead (their resolution is part of the construction).
PREVIEW_ANGULAR_SEGMENTS = 65
PREVIEW_LENGTH_SEGMENTS = 24
PREVIEW_NOTES_ENVELOPE_NATIVE = (
    "envelope estimator has FREEFORM-anchor and GRID branches only; OSSE/R-OSSE/ICW params return None"
)
PREVIEW_NOTES_CAD = (
    "CAD/STEP recipe - geometry authored by tools/cad/multicell.py; no on-demand preview in the mesher"
)


def _preview_config(root: Path, name: str) -> dict:
    """Resolve a config NAME through ``list_configs`` (never a client path); 404 when unknown.

    Process-local memo on the two config-directory stamps: a live sandbox drag calls this on
    every tick, and re-parsing ~46 YAML files per tick (measured 0.7 s under cProfile) would
    swamp the 20-30 ms geometry. Adding/removing a config file changes a directory mtime and
    rebuilds the index; file CONTENT edits do not change name -> path resolution (the seed gate
    keeps its own per-file stamp cache).
    """
    key = str(root.resolve())
    try:
        ex = root / "examples"
        signature = tuple(
            d.stat().st_mtime_ns for d in [ex, *sorted(q for q in ex.rglob("*") if q.is_dir())]
            if d.relative_to(ex).parts[:1] != ("briefs",))
    except OSError:
        signature = None
    cached = _PREVIEW_CONFIG_CACHE.get(key)
    if cached is None or signature is None or cached[0] != signature:
        cached = (signature, list_configs(root))
        _PREVIEW_CONFIG_CACHE[key] = cached
    for entry in cached[1]:
        if entry.get("name") == name:
            return entry
    # A TYPOLOGY LINK carries the catalog name (`#/typology/<catalog name>` from /api/typologies),
    # which differs from the config's own `name:` whenever examples/catalog.yaml renames it - all
    # five cone_plughorn configs are like that (catalog `cone_plughorn_7sh` vs config
    # `cone_plughorn__evo7sh_narrow`), so the link used to 404 and the page showed "preview endpoint
    # unavailable". Exact config name wins; the catalog name is the fallback.
    for entry in cached[1]:
        if entry.get("catalog_name") == name:
            return entry
    raise FileNotFoundError(f"unknown config {name!r}")


#: ``root -> (directory stamps, list_configs entries)``; see ``_preview_config``.
_PREVIEW_CONFIG_CACHE: dict[str, tuple] = {}


def _preview_brief_path(root: Path, name: str) -> Path:
    for entry in list_briefs(root):
        if entry.get("name") == name:
            return root / entry["path"]
    raise FileNotFoundError(f"unknown brief {name!r}")


def _build_viewport(mcfg: dict) -> dict:
    """The one viewport call the preview makes (monkeypatched by the silent-OSSE pin test)."""
    from hornlab_mesher.viewport import build_viewport_geometry_from_config
    return build_viewport_geometry_from_config(mcfg, point_lists=False)


#: Native families whose mesher branch takes the Ath Morph section.
MORPH_FAMILIES = ("OSSE", "R-OSSE", "ICW", "FREEFORM")


def morph_capable(raw: dict) -> bool:
    """Can this config take native Morph? Native OSSE / R-OSSE / ICW / FREEFORM (not a CAD
    recipe), or a generated typology with an elliptical mouth (the generator refuses Morph on a
    superellipse / rounded-rectangle mouth: two outline mechanisms). Rows/grid typologies make
    their mouth from the per-azimuth law, so Morph does not apply to them."""
    gen = raw.get("generator")
    if isinstance(gen, dict):
        return gen.get("name") not in ("grid",) and gen.get("mouth", "ellipse") == "ellipse"
    seed = raw.get("seed_params") or {}
    return str(raw.get("family", "")) in MORPH_FAMILIES and "cad" not in seed


try:  # the mesher's config refusal type (absent mesher -> nothing to catch)
    from hornlab_mesher.config_parser import ConfigError as _MesherConfigError
except Exception:  # noqa: BLE001
    class _MesherConfigError(Exception):
        pass


def gcurve_capable(raw: dict) -> bool:
    """Ath's OS-SE guiding curve (superellipse / superformula mouth law that sets a different
    coverage angle in every direction -- the source of Ath's creased CORE / TwinRay walls) is an
    OSSE-only mesher feature."""
    return (not isinstance(raw.get("generator"), dict) and str(raw.get("family", "")) == "OSSE"
            and "cad" not in (raw.get("seed_params") or {}))


def _preview_extra_keys(cfg) -> set[str]:
    """Knobs the sandbox may set although the config neither seeds nor bounds them: every
    numeric key the native family accepts (Morph, wall, ...), and the generator's opt-in Morph
    knobs. Rows/grid blocks take only their own keys (their mouth IS the per-azimuth law)."""
    from hornlab_search.design import families
    from hornlab_search.design.generators import registry
    gen = cfg.generator if isinstance(cfg.generator, dict) else None
    if gen is None:
        if "cad" in cfg.seed_params:
            return set()
        keys = families.FAMILY_KEYS.get(str(cfg.family), {})
        return {k for k, spec in keys.items() if spec.kind in (int, float)}
    if gen.get("name") == "grid":
        return set()
    if gen.get("name") == "plughorn":                 # every key of the CAD tool is a knob
        from hornlab_search.mesh import step_build
        return set(step_build.load_cad_tool(tool=step_build.PLUGHORN_TOOL).KEYS)
    return {k for k in registry.DEFAULT_KNOBS if k.startswith("morph_")}


def _preview_knobs(cfg, overrides: dict) -> tuple[dict, list[str]]:
    """Merge requested knobs per key: valid names win, unknown names are named and ignored."""
    allowed = set(cfg.bounds_raw) | set(cfg.seed_params) | _preview_extra_keys(cfg)
    effective = copy.deepcopy(cfg.seed_params)
    notes: list[str] = []
    for key, value in overrides.items():
        if key not in allowed:
            notes.append(f"unknown knob {key!r} ignored (not in bounds or seed_params)")
            continue
        effective[key] = value
    return effective, notes


def _closest_row(angles, target: float) -> int:
    arr = np.asarray(angles, dtype=float)
    delta = np.abs(np.angle(np.exp(1j * (arr - float(target)))))
    return int(np.argmin(delta))


def _rows_angles(meta: dict, n_phi: int) -> np.ndarray:
    span = str(meta.get("row_span") or meta.get("span") or
               ("half" if meta.get("half_model") else "quarter"))
    if span == "half":
        return np.linspace(-0.5 * math.pi, 0.5 * math.pi, n_phi)
    if span == "half_xz":
        return np.linspace(0.0, math.pi, n_phi)
    if span == "full":
        return np.linspace(0.0, 2.0 * math.pi, n_phi, endpoint=False)
    return np.linspace(0.0, 0.5 * math.pi, n_phi)


def _meridian(row) -> list[list[float]]:
    arr = np.asarray(row, dtype=float)
    z = arr[:, 2]
    r = np.hypot(arr[:, 0], arr[:, 1])
    return [[round(float(a), 3), round(float(b), 3)] for a, b in zip(z, r)]


def _ring(row) -> list[list[float]]:
    arr = np.asarray(row, dtype=float)
    return [[round(float(a), 3), round(float(b), 3)] for a, b in zip(arr[:, 0], arr[:, 1])]


def _sections(inner, outer, angles) -> tuple[dict, dict]:
    """H/V meridians at phi=0 and phi=90, plus the mouth ring from the last station.

    The rows are chosen by ANGLE, not by index: the spike's aspect-ratio finding requires the
    section to come from the REAL grid row (a half model's first row is -90, and a full ring's
    last row is not the V plane). Quarter/half grids therefore give exactly row 0/last row.
    """
    inner = np.asarray(inner, dtype=float)
    outer_arr = None if outer is None else np.asarray(outer, dtype=float)
    h = _closest_row(angles, 0.0)
    v = _closest_row(angles, 0.5 * math.pi)
    section = {
        "h": {"inner": _meridian(inner[h]),
              "outer": [] if outer_arr is None else _meridian(outer_arr[h])},
        "v": {"inner": _meridian(inner[v]),
              "outer": [] if outer_arr is None else _meridian(outer_arr[v])},
    }
    mouth = {
        "inner": _ring(inner[:, -1, :]),
        "outer": [] if outer_arr is None else _ring(outer_arr[:, -1, :]),
    }
    return section, mouth


def _rows_overshoot_from_arrays(inner, meta: dict, wall_mm: float, brief: dict | None) -> float:
    """Reuse the rows march already built instead of re-marching (the spike measured 570 ms).

    The arithmetic is the same one ``registry._grid_overshoot_estimate`` applies to
    ``grid.envelope_extents``: outer width/height include the shell in full, and the depth is the
    grid's own axial span (the bend is already inside it) plus the shell. Limits are the
    registry's own constants, not copies of a number.
    """
    from hornlab_search.design.generators.registry import _ENVELOPE_MOUTH_TOLERANCE_MM
    from hornlab_search.search.evaluate import ENVELOPE_DEPTH_ALLOWANCE_MM

    env = (brief or {}).get("envelope") or {}
    if not env:
        return 0.0
    arr = np.asarray(inner, dtype=float)
    lim_w = float(env.get("max_mouth_w_mm", 1e9)) + _ENVELOPE_MOUTH_TOLERANCE_MM
    lim_h = float(env.get("max_mouth_h_mm", 1e9)) + _ENVELOPE_MOUTH_TOLERANCE_MM
    lim_d = float(env.get("max_depth_mm", 1e9)) + float(ENVELOPE_DEPTH_ALLOWANCE_MM)
    if not (lim_w > 0.0 and lim_h > 0.0 and lim_d > 0.0):
        return 0.0
    width = 2.0 * float(np.max(np.abs(arr[..., 0]))) + 2.0 * wall_mm
    height = 2.0 * float(np.max(np.abs(arr[..., 1]))) + 2.0 * wall_mm
    depth = float(np.max(arr[..., 2]) - np.min(arr[..., 2])) + wall_mm
    return max(width / lim_w - 1.0, height / lim_h - 1.0, depth / lim_d - 1.0, 0.0)


def _preview_response(*, config: str, brief: str | None, kind: str, quadrants: str,
                      available: bool, knobs: dict, section: dict, mouth: dict,
                      envelope: dict, shape3d: dict, slow: bool, timings: dict,
                      notes: list[str], rejected: list[str] | None = None,
                      dims: dict | None = None, morph_capable: bool = False,
                      gcurve_capable: bool = False) -> dict:
    return clean({
        "version": 1,
        "config": config,
        "brief": brief,
        "kind": kind,
        "units": "mm",
        "quadrants": str(quadrants),
        "available": bool(available),
        "knobs": knobs,
        "section": section,
        "mouth": mouth,
        "envelope": envelope,
        "shape3d": shape3d,
        "slow": bool(slow),
        "timings_ms": {k: round(float(v), 3) for k, v in timings.items()},
        "notes": notes,
        # Why a search would refuse this shape (envelope / self-approach). The geometry is
        # still drawn: the sandbox is for seeing what a knob does, not only what is legal.
        "rejected": list(rejected or []),
        # The full horn's measured size (outer shell when present), mm.
        "dims": dims,
        "morph_capable": bool(morph_capable),
        "gcurve_capable": bool(gcurve_capable),
    })


def _preview_dims(inner, outer) -> dict | None:
    """Full-horn width / height / depth (mm) from the preview grid, mirror-aware: a quarter or
    half model is symmetric about the planes it omits, so a one-sided extent counts twice."""
    pts = np.asarray(outer if outer is not None else inner, dtype=float).reshape(-1, 3)
    if pts.size == 0 or not np.all(np.isfinite(pts)):
        return None

    def span(v):
        lo, hi = float(v.min()), float(v.max())
        # one-sided (a mirror model) unless the far side reaches 2 % of the near side
        return hi - lo if -lo > 0.02 * max(hi, 1.0) else 2.0 * max(hi, -lo)

    return {"w": round(span(pts[:, 0]), 1), "h": round(span(pts[:, 1]), 1),
            "d": round(float(pts[:, 2].max() - pts[:, 2].min()), 1)}


def _measured_envelope(dims: dict | None, brief: dict | None) -> dict:
    """Overshoot of the measured size against the brief's envelope (native families, which
    have no estimator branch)."""
    env = (brief or {}).get("envelope") or {}
    if not dims:
        return {"available": False, "reason": "no preview geometry to measure"}
    ratios = [dims[k] / float(env[e]) for k, e in (("w", "max_mouth_w_mm"), ("h", "max_mouth_h_mm"),
                                                   ("d", "max_depth_mm"))
              if env.get(e) and float(env[e]) > 0]
    if not ratios:
        return {"available": False, "reason": "the brief has no size envelope"}
    return {"available": True, "overshoot": round(max(0.0, max(ratios) - 1.0), 6),
            "source": "measured from the preview geometry"}


def preview_shape(root: Path, config_name: str, q: dict) -> dict:
    """On-demand 2D/3D preview geometry for one typology config (sandbox backend).

    GET ``/api/preview-shape/<config>?brief=<name>&detail=2d|3d&knobs=<urlencoded JSON>``.
    Dispatch branches on the params KIND FIRST (the spike's silent-OSSE hazard): a grid block
    never reaches ``build_preview_geometry``/``to_mesher_config``; a CAD recipe returns
    ``available:false`` before ``to_mesher_config`` (which raises a bare ``KeyError: 'cad'``).
    Nothing is written and nothing is meshed: geometry only.

    ``detail=2d`` keeps the ``shape3d`` block present but ``{"available": false, "reason":
    "detail=2d"}``, so the response shape never changes with the detail flag.
    """
    from hornlab_search.config import ConfigError, load_config, mesh_spec
    from hornlab_search.design import families
    from hornlab_search.design.generators import grid as grid_gen
    from hornlab_search.design.generators import registry
    from hornlab_search.mesh.build import res_mm_for_spec
    from hornlab_search.types import Design, GeometryInvalidError
    from . import preview as seam

    started = time.perf_counter()
    t_params = t_section = t_shape = 0.0

    entry = _preview_config(root, config_name)
    cfg_path = root / entry["path"]
    detail_raw = q.get("detail") or ["2d"]
    detail = str(detail_raw[0] if isinstance(detail_raw, (list, tuple)) else detail_raw).lower()
    if detail not in ("2d", "3d"):
        raise ValueError("detail must be '2d' or '3d'")
    brief_p = None
    brief_q = q.get("brief")
    if brief_q:
        brief_name_raw = brief_q[0] if isinstance(brief_q, (list, tuple)) else brief_q
        brief_p = _preview_brief_path(root, str(brief_name_raw))

    try:
        cfg = load_config(cfg_path, brief=brief_p)
    except ConfigError as exc:
        # e.g. a config that pins its throat radius under a brief with another driver size:
        # say so on the page instead of a server error that blanks the sandbox.
        reason = f"this config cannot load under this brief: {exc}"
        return _preview_response(
            config=config_name, brief=brief_p.stem if brief_p else None, kind="native",
            quadrants="1", available=False, knobs={},
            section={"h": {"inner": [], "outer": []}, "v": {"inner": [], "outer": []}},
            mouth={"inner": [], "outer": []}, envelope={"available": False, "reason": reason},
            shape3d={"available": False, "reason": reason}, slow=False,
            timings={"total": (time.perf_counter() - started) * 1000.0}, notes=[reason])
    brief_name = (cfg.brief or {}).get("name")
    quadrants = str(cfg.mesh.quadrants)

    raw_knobs = q.get("knobs")
    knob_text = raw_knobs[0] if isinstance(raw_knobs, (list, tuple)) else raw_knobs
    if knob_text in (None, ""):
        overrides = {}
    else:
        try:
            overrides = json.loads(str(knob_text))
        except json.JSONDecodeError as exc:
            raise ValueError(f"knobs must be a JSON object: {exc}") from None
        if not isinstance(overrides, dict):
            raise ValueError("knobs must be a JSON object")

    effective, notes = _preview_knobs(cfg, overrides)
    gen = cfg.generator if isinstance(cfg.generator, dict) else None
    is_grid = bool(gen and gen.get("name") == "grid")
    is_rows = bool(is_grid and isinstance(gen.get("rows"), dict))
    kind = "rows" if is_rows else ("grid" if is_grid else
                                   ("native" if not gen else "generator"))
    slow = bool(is_rows)

    def unavailable(reason: str, *, envelope: dict | None = None) -> dict:
        timings = {"params": t_params, "section": t_section, "shape3d": t_shape,
                   "total": (time.perf_counter() - started) * 1000.0}
        return _preview_response(
            config=config_name, brief=brief_name, kind=kind, quadrants=quadrants,
            available=False, knobs=effective,
            section={"h": {"inner": [], "outer": []}, "v": {"inner": [], "outer": []}},
            mouth={"inner": [], "outer": []},
            envelope=envelope or {"available": False, "reason": reason},
            shape3d={"available": False, "reason": reason},
            slow=slow, timings=timings, notes=notes + [reason])

    # (1b) cone mid horn + axe head (tools/cad/plughorn.py): the CAD tool's own sections and solid.
    if gen and gen.get("name") == "plughorn":
        return _plughorn_preview(cfg, effective, notes, detail, config_name, brief_name, quadrants,
                                 started, unavailable)

    # (1) CAD recipe: no on-demand preview in the mesher; stop BEFORE to_mesher_config.
    if "cad" in cfg.seed_params:
        return unavailable(PREVIEW_NOTES_CAD,
                           envelope={"available": False, "reason": PREVIEW_NOTES_CAD})

    mesh = mesh_spec("screen", cfg)
    res_mm = res_mm_for_spec(mesh, cfg)
    envelope: dict
    section: dict
    mouth: dict
    rejected: list[str] = []
    inner = outer = angles = None
    t_coords = phi_coords = None
    closed_phi = False

    try:
        if is_grid:
            # (2) GRID/ROWS: the config's own march arrays. NO grid block into the preview.
            gspec = gen
            wall_mm = float(gspec.get("wall_thickness_mm", 3.0))
            inner, meta = grid_gen.grid_points(gspec, effective, cfg.brief)
            half = bool(meta.get("half_model", False))
            half_xz = str(meta.get("row_span") or meta.get("span") or "") == "half_xz"
            closed_phi = ((not bool(meta.get("quarter", True))) and not half
                          and not half_xz)
            outer = grid_gen.grid_outer_points(inner, wall_mm, half=half,
                                               half_xz=half_xz, full=closed_phi, check=False)
            try:
                grid_gen.check_self_approach(inner, outer, wall_mm)
            except registry.GeneratorError as exc:
                rejected.append(str(exc))
            angles = _rows_angles(meta, int(inner.shape[0]))
            t_params = (time.perf_counter() - started) * 1000.0
            if is_rows:
                overshoot = _rows_overshoot_from_arrays(inner, meta, wall_mm, cfg.brief)
                envelope = {"available": True, "overshoot": round(float(overshoot), 6)}
            else:
                block = grid_gen.design_params(gspec, effective, cfg.brief)
                overshoot = registry.envelope_overshoot_estimate(block, cfg.brief)
                envelope = ({"available": False,
                             "reason": "envelope estimator returned None for this grid"}
                            if overshoot is None
                            else {"available": True, "overshoot": round(float(overshoot), 6)})
            if envelope.get("available") and float(envelope["overshoot"]) > 0.0:
                rejected.append(
                    "invalid_envelope: estimated outside the brief envelope "
                    f"(max relative overshoot {float(envelope['overshoot']):.4f})")
        else:
            # (3) GENERATOR vs (4) NATIVE: materialize the mesher config, then the viewport.
            if gen:
                params = registry.materialize(gen, effective, cfg.brief)
            else:
                params = copy.deepcopy(cfg.seed_params)
                for key, value in overrides.items():
                    if key not in effective:        # an unknown name was named in notes
                        continue
                    if key in cfg.seed_params:
                        families.param_set(cfg.family, params, key, value)
                    elif "." in key:
                        notes.append(f"knob {key!r} has no resolvable seed path; ignored")
                    else:
                        params[key] = value
                effective = params
            design = Design("FREEFORM" if gen else cfg.family, params)
            mcfg = families.to_mesher_config(
                design, mesh, res_mm, Path(os.environ.get("TEMP", ".")) / "hornlab-preview.msh")
            mcfg_coarse = copy.deepcopy(mcfg)
            mesh_sec = dict(mcfg_coarse.get("mesh") or {})
            mesh_sec["angular_segments"] = PREVIEW_ANGULAR_SEGMENTS
            mesh_sec["length_segments"] = PREVIEW_LENGTH_SEGMENTS
            mcfg_coarse["mesh"] = mesh_sec
            if gen:
                overshoot = registry.envelope_overshoot_estimate(params, cfg.brief)
                envelope = ({"available": False,
                             "reason": "envelope estimator returned None for these params"}
                            if overshoot is None
                            else {"available": True, "overshoot": round(float(overshoot), 6)})
            else:
                envelope = {"available": False, "reason": PREVIEW_NOTES_ENVELOPE_NATIVE}
            t_params = (time.perf_counter() - started) * 1000.0
            if envelope.get("available") and float(envelope["overshoot"]) > 0.0:
                rejected.append(
                    "invalid_envelope: estimated outside the brief envelope "
                    f"(max relative overshoot {float(envelope['overshoot']):.4f})")
            viewport = _build_viewport(mcfg_coarse)
            grid_data = viewport["grid"]
            inner = np.asarray(grid_data["inner_grid"], dtype=float)
            outer = (None if grid_data.get("outer_grid") is None
                     else np.asarray(grid_data["outer_grid"], dtype=float))
            closed_phi = bool(grid_data.get("full_circle", True))
            angles = grid_data.get("angle_list")
            t_coords = np.asarray(grid_data["slice_map"], dtype=float)
            phi_grid = grid_data.get("phi_grid")
            phi_coords = (np.asarray(phi_grid, dtype=float).T if phi_grid is not None
                          else np.broadcast_to(np.asarray(angles, dtype=float),
                                               inner.shape[1::-1]))
    except (registry.GeneratorError, GeometryInvalidError, ConfigError, _MesherConfigError) as exc:
        # the mesher's own config refusals (e.g. a guiding curve on a non-circular cross-section)
        # are explained on the page like ours, never a server error that blanks the sandbox
        t_params = t_params or (time.perf_counter() - started) * 1000.0
        return unavailable(str(exc))

    if angles is None:
        angles = _rows_angles({}, int(np.asarray(inner).shape[0]))
    dims = _preview_dims(inner, outer)
    if kind == "native":
        envelope = _measured_envelope(dims, cfg.brief)

    t0 = time.perf_counter()
    section, mouth = _sections(inner, outer, angles)
    t_section = (time.perf_counter() - t0) * 1000.0

    if detail == "3d":
        if outer is None:
            shape3d = {"available": False,
                       "reason": "no outer shell for this design (wall_thickness_mm=0?)"}
        else:
            t0 = time.perf_counter()
            try:
                soup = seam.tessellate(
                    inner, outer, t_coordinates=t_coords, phi_coordinates=phi_coords,
                    closed_phi=closed_phi)
            except ValueError as exc:
                t_shape = (time.perf_counter() - t0) * 1000.0
                shape3d = {"available": False, "reason": str(exc)}
            else:
                t_shape = (time.perf_counter() - t0) * 1000.0
                shape3d = {
                    "available": True,
                    "warnings": list(soup.get("warnings") or []),
                    "roles": list(soup["roles"]),
                    "verts": np.round(np.asarray(soup["positions"], dtype=float), 3).ravel().tolist(),
                    "tris": np.asarray(soup["indices"], dtype=np.int64).ravel().tolist(),
                }
    else:
        shape3d = {"available": False, "reason": "detail=2d"}

    timings = {"params": t_params, "section": t_section, "shape3d": t_shape,
               "total": (time.perf_counter() - started) * 1000.0}
    return _preview_response(
        config=config_name, brief=brief_name, kind=kind, quadrants=quadrants,
        available=True, knobs=effective, section=section, mouth=mouth,
        envelope=envelope, shape3d=shape3d, slow=slow, timings=timings, notes=notes,
        rejected=rejected, dims=dims, morph_capable=morph_capable(cfg.raw),
        gcurve_capable=gcurve_capable(cfg.raw))


def _tessellate_part(part, tol: float = 1.0, ang: float = 0.3):
    """(points, triangles, skipped_faces) for the 3D preview; never raises for a valid solid.

    ``build123d``'s ``Shape.tessellate`` walks every face and assumes each one comes back with a
    triangulation, so a SINGLE face without one kills the whole payload with
    ``AttributeError: 'NoneType' object has no attribute 'NbNodes'``. That happens on a valid,
    gmsh-meshable solid: ``cone_plughorn__morph_wide_8in`` has one planar boolean-remnant face
    (634 mm^2) that no deflection/sag tolerance triangulates, while the same STEP meshes fine.
    The preview is a visual, so tessellate face by face and report what could not be drawn
    instead of blanking the viewport.
    """
    try:
        verts, tris = part.tessellate(tol, ang)
        return [[p.X, p.Y, p.Z] for p in verts], [list(t) for t in tris], 0
    except Exception:  # noqa: BLE001 - fall through to the per-face path
        pass
    pts: list[list[float]] = []
    idx: list[list[int]] = []
    skipped, base = 0, 0
    for face in part.faces():
        try:
            fv, ft = face.tessellate(tol, ang)
        except Exception:  # noqa: BLE001 - one un-triangulable face is not a blank viewport
            skipped += 1
            continue
        pts.extend([[p.X, p.Y, p.Z] for p in fv])
        idx.extend([[base + int(i) for i in tri] for tri in ft])
        base += len(fv)
    return pts, idx, skipped


def _plughorn_preview(cfg, effective, notes, detail, config_name, brief_name, quadrants, started,
                      unavailable) -> dict:
    """Sandbox preview of a ``plughorn`` design: H/V wall sections and the front opening from the
    tool's own section geometry; 3D = the tessellated CAD solid (horn + axe head + bowl), mm.

    The 3D tessellation builds the full OCC solid (~1-3 s), so the payload is marked ``slow``."""
    from hornlab_search.design.generated import plughorn_params
    from hornlab_search.mesh import step_build
    t0 = time.perf_counter()
    try:
        cad = plughorn_params(cfg.generator, effective, None)["cad"]     # envelope is reported, not refused
        tool = step_build.load_cad_tool(tool=step_build.PLUGHORN_TOOL)
        p = tool.params_from_recipe(cad)
    except (ValueError, RuntimeError) as exc:
        return unavailable(str(exc))
    t_params = (time.perf_counter() - t0) * 1000.0
    L = p.L
    h_in, v_in = [], []
    for i in range(41):
        z = L * i / 40
        sec = p.horn_section(z)
        if sec is None or len(sec) < 3:
            continue
        sec = np.asarray(sec, dtype=float)
        h_in.append([round(float(z), 3), round(float(np.abs(sec[:, 0]).max()), 3)])
        v_in.append([round(float(z), 3), round(float(np.abs(sec[:, 1]).max()), 3)])
    section = {"h": {"inner": h_in, "outer": []}, "v": {"inner": v_in, "outer": []}}
    mouth = {"inner": [[round(x, 3), round(y, 3)] for x, y, _z in p.front_octagon()], "outer": []}
    d = p.derived()
    rejected = []
    env = (cfg.brief or {}).get("envelope") or {}
    for key, val in (("max_mouth_w_mm", d["outer_w_mm"]), ("max_mouth_h_mm", d["outer_h_mm"]),
                     ("max_depth_mm", d["depth_total_mm"])):
        if key in env and val > float(env[key]) + 0.5:
            rejected.append(f"invalid_envelope: outer {key[4:-3]} {val:.0f} mm > {env[key]} mm")
    envelope = {"available": True, "overshoot": 0.0 if not rejected else 1.0}
    notes = list(notes) + [f"{k}: {v}" for k, v in d.items() if k in (
        "compression_ratio", "min_channel_area_cm2", "side_wall_angle_deg", "top_wall_angle_deg",
        "plug_clearance_mm", "rear_chamber_gross_l")]
    t_section = (time.perf_counter() - t0) * 1000.0 - t_params
    t_shape = 0.0
    if detail == "3d":
        t1 = time.perf_counter()
        try:
            part = tool.build_body(p)
            pts, idx, skipped = _tessellate_part(part)
            if not idx:
                raise RuntimeError("the solid tessellated to no triangles")
            warn = ([f"{skipped} face(s) could not be triangulated (degenerate boolean remnant) "
                     f"and are not drawn; the solid itself is valid and meshes"]
                    if skipped else [])
            shape3d = {"available": True, "warnings": warn, "roles": ["horn.inner"],
                       "verts": np.round(np.asarray(pts, dtype=float), 3).ravel().tolist(),
                       "tris": np.asarray(idx, dtype=np.int64).ravel().tolist()}
        except Exception as exc:  # noqa: BLE001 - a CAD failure is explained, never a server error
            shape3d = {"available": False, "reason": f"CAD build failed: {exc}"}
        t_shape = (time.perf_counter() - t1) * 1000.0
    else:
        shape3d = {"available": False, "reason": "detail=2d"}
    dims = {"w": d["outer_w_mm"], "h": d["outer_h_mm"], "d": d["depth_total_mm"]}
    timings = {"params": t_params, "section": t_section, "shape3d": t_shape,
               "total": (time.perf_counter() - started) * 1000.0}
    return _preview_response(
        config=config_name, brief=brief_name, kind="plughorn", quadrants=quadrants, available=True,
        knobs=effective, section=section, mouth=mouth, envelope=envelope, shape3d=shape3d, slow=True,
        timings=timings, notes=notes, rejected=rejected, dims=dims)


# ---------------------------------------------------------------------------- bounds writer


def _fmt_bound(v: float) -> str:
    return repr(float(v))


def _append_block_lines(text: str, block: str, new_lines: list[str]) -> str:
    """Append ``new_lines`` as entries at the END of the top-level ``block:`` mapping, at its own
    indentation (comment-preserving; nothing else moves). A missing block is created at the end."""
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines)
                  if re.match(rf"^{re.escape(block)}\s*:\s*(#.*)?(\r?\n)?$", ln)), None)
    if start is None:
        body = "".join(f"  {ln}{nl}" for ln in new_lines)
        sep = "" if text.endswith(("\n", "\r\n")) or not text else nl
        return text + sep + f"{block}:{nl}" + body
    indent, last = 2, start
    for j in range(start + 1, len(lines)):
        st = lines[j].strip()
        if not st or st.startswith("#"):
            continue
        if not lines[j][:1].isspace():
            break
        if last == start:
            indent = len(lines[j]) - len(lines[j].lstrip())
        last = j
    if not lines[last].endswith(("\n", "\r\n")):
        lines[last] += nl
    ins = [" " * indent + ln + nl for ln in new_lines]
    return "".join(lines[:last + 1] + ins + lines[last + 1:])


def _patch_bounds_lines(text: str, updates: dict) -> tuple[str, set[str]]:
    """Comment-preserving, indentation-aware patch of ONLY the ``lo:``/``hi:`` lines.

    No YAML round trip (ruamel is not installed): the rest of the file stays byte-identical.
    Handles both block mappings (``lo: 1.0``) and a flow mapping (``{lo: 1.0, hi: 2.0}``) in a
    bounds block, because only the value token changes either way.
    """
    lines = text.splitlines(keepends=True)
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^bounds\s*:\s*(#.*)?(\r?\n)?$", line):
            start = i
            break
    if start is None:
        return text, set()

    key_indent = None
    for line in lines[start + 1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line[:1].isspace():
            break
        key_indent = len(line) - len(line.lstrip())
        break
    if key_indent is None:
        return text, set()

    patched: set[str] = set()
    key_line = re.compile(
        r"^(?P<indent>\s*)(?P<q>['\"]?)(?P<key>[^:'\"]+)(?P=q)\s*:(?P<rest>.*)$")
    leaf = re.compile(r"^(?P<lead>\s*)(?P<kind>lo|hi)\s*:\s*(?P<val>[^\s#]+)(?P<trail>.*)$")

    i = start + 1
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            indent = len(line) - len(line.lstrip())
            if indent == 0:
                break
            if indent < key_indent:
                break
        if not stripped or stripped.startswith("#") or (len(line) - len(line.lstrip())) != key_indent:
            i += 1
            continue
        m = key_line.match(line)
        if not m:
            i += 1
            continue
        key = m.group("key")
        if key not in updates:
            i += 1
            continue
        lo, hi = updates[key]
        rest = m.group("rest")
        if "{" in rest:
            new_rest = re.sub(r"(lo\s*:\s*)([^,}\s]+)", lambda mm: mm.group(1) + _fmt_bound(lo),
                              rest, count=1)
            new_rest = re.sub(r"(hi\s*:\s*)([^,}\s]+)", lambda mm: mm.group(1) + _fmt_bound(hi),
                              new_rest, count=1)
            if new_rest != rest:
                lines[i] = line[:m.start("rest")] + new_rest
                patched.add(key)
            i += 1
            continue
        found = set()
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            nxt_stripped = nxt.strip()
            nxt_indent = len(nxt) - len(nxt.lstrip())
            if nxt_stripped and not nxt_stripped.startswith("#") and nxt_indent <= key_indent:
                break
            lm = leaf.match(nxt)
            if lm and lm.group("kind") not in found:
                value = lo if lm.group("kind") == "lo" else hi
                lines[j] = (nxt[:lm.start("val")] + _fmt_bound(value) + nxt[lm.end("val"):])
                found.add(lm.group("kind"))
            j += 1
        if found == {"lo", "hi"}:
            patched.add(key)
        i = j
    return "".join(lines), patched


def save_bounds(root: Path, body: dict) -> dict:
    """Write edited search bounds back to their YAML home (owner ruling 2026-10-25).

    Resolves the config through ``list_configs``; only ``examples/typologies/**`` is writable in
    this pass (root-level ``examples/*.yaml`` is reported, never written). Every key is validated
    as a whole (all-or-nothing): unknown key, non-finite value, lo > hi, or a value outside the
    parameter catalog's hard schema limit rejects the entire request and writes nothing.
    """
    from hornlab_search.design.params import bounds_for

    if not isinstance(body, dict):
        raise ValueError("JSON object expected")
    name = body.get("config")
    updates = body.get("bounds")
    if not isinstance(name, str) or not name:
        raise ValueError("body needs a non-empty 'config' name")
    adds = body.get("add") or {}
    if updates is None:
        updates = {}
    if not isinstance(updates, dict) or not isinstance(adds, dict) or not (updates or adds):
        raise ValueError("body needs a non-empty 'bounds' or 'add' object")
    entry = _preview_config(root, name)
    rel = entry["path"]
    path = (root / rel).resolve()
    typologies = (root / "examples" / "typologies").resolve()
    notes = [
        "config_sha changes for this config; resume needs --allow-config-change",
        "a RUNNING search using this config keeps its own snapshot (run config.yaml); "
        "bounds edits apply to the next launch",
    ]
    if typologies not in path.parents:
        return {"ok": False, "applied": [],
                "rejected": [{"key": "-",
                              "reason": f"config_not_writable: {rel} is not under "
                                        "examples/typologies/; nothing written"}]}

    text = path.read_text(encoding="utf-8")
    doc = yaml.safe_load(text) or {}
    known = doc.get("bounds") if isinstance(doc.get("bounds"), dict) else {}

    rejected: list[dict] = []
    accepted: dict[str, tuple[float, float]] = {}
    applied: list[dict] = []
    for raw_key, raw_value in updates.items():
        key = str(raw_key)
        if key not in known:
            rejected.append({"key": key, "reason": "unknown_key"})
            continue
        if not isinstance(raw_value, dict) or "lo" not in raw_value or "hi" not in raw_value:
            rejected.append({"key": key, "reason": "missing_lo_hi"})
            continue
        lo_raw, hi_raw = raw_value.get("lo"), raw_value.get("hi")
        if isinstance(lo_raw, bool) or isinstance(hi_raw, bool):
            rejected.append({"key": key, "reason": "not_a_finite_number"})
            continue
        try:
            lo, hi = float(lo_raw), float(hi_raw)
        except (TypeError, ValueError):
            rejected.append({"key": key, "reason": "not_a_finite_number"})
            continue
        if not (math.isfinite(lo) and math.isfinite(hi)):
            rejected.append({"key": key, "reason": "not_a_finite_number"})
            continue
        if lo > hi:
            rejected.append({"key": key, "reason": "lo_above_hi"})
            continue
        hard = {}
        try:
            hard = (bounds_for(name, key) or {}).get("hard") or {}
        except Exception:  # noqa: BLE001 - the catalog is advisory here, never a crash
            hard = {}
        hard_lo = hard.get("lo") if isinstance(hard, dict) else None
        hard_hi = hard.get("hi") if isinstance(hard, dict) else None
        if (hard_lo is not None and lo < float(hard_lo)) or \
                (hard_hi is not None and hi > float(hard_hi)):
            lo_s = "-inf" if hard_lo is None else f"{float(hard_lo):g}"
            hi_s = "inf" if hard_hi is None else f"{float(hard_hi):g}"
            rejected.append({"key": key, "reason": f"exceeds_hard_limit {lo_s}..{hi_s}"})
            continue
        if hard_lo is None and hard_hi is None:
            notes.append(f"no hard schema limit known for {key!r}; "
                         "the config schema validates at build time")
        accepted[key] = (lo, hi)
        old = known[key] if isinstance(known[key], dict) else {}
        applied.append({"key": key,
                        "from": {"lo": old.get("lo"), "hi": old.get("hi")},
                        "to": {"lo": lo, "hi": hi}})

    added_bounds: list[str] = []
    added_seeds: list[str] = []
    if adds:
        from hornlab_search.config import ConfigError, load_config
        try:
            legal = _preview_extra_keys(load_config(path))
        except ConfigError as exc:
            legal = set()
            notes.append(f"config does not load on its own: {exc}")
        seeds = doc.get("seed_params") if isinstance(doc.get("seed_params"), dict) else {}
        for raw_key, raw_value in adds.items():
            key = str(raw_key)
            if key in known:
                rejected.append({"key": key, "reason": "already_a_bound_row (edit it instead)"})
                continue
            if key not in legal:
                rejected.append({"key": key, "reason": "not_a_legal_key_for_this_typology"})
                continue
            v = raw_value if isinstance(raw_value, dict) else {}
            try:
                lo, hi = float(v.get("lo")), float(v.get("hi"))
                seed = float(v.get("seed", (lo + hi) / 2.0))
            except (TypeError, ValueError):
                rejected.append({"key": key, "reason": "not_a_finite_number"})
                continue
            if not all(math.isfinite(x) for x in (lo, hi, seed)) or lo > hi or not lo <= seed <= hi:
                rejected.append({"key": key, "reason": "need finite lo <= seed <= hi"})
                continue
            is_int = key in ("morph_target", "morph_allow_shrinkage")
            fmt_v = (lambda x: str(int(round(x)))) if is_int else (lambda x: repr(round(x, 6)))
            pinned = bool(v.get("pinned")) or lo == hi
            added_bounds.append(f"{key}: {{lo: {fmt_v(lo)}, hi: {fmt_v(hi)}"
                                + (", search: false}" if pinned else "}"))
            if key not in seeds:
                added_seeds.append(f"{key}: {fmt_v(seed)}")
            applied.append({"key": key, "from": None,
                            "to": {"lo": lo, "hi": hi, "seed": seed, "pinned": pinned}})

    if rejected:
        return {"ok": False, "rejected": rejected, "applied": [], "notes": notes}

    new_text, patched = _patch_bounds_lines(text, accepted)
    if added_bounds:
        new_text = _append_block_lines(new_text, "bounds", added_bounds)
    if added_seeds:
        new_text = _append_block_lines(new_text, "seed_params", added_seeds)
    if adds:
        # the whole config must still load (family keys, generator rules, the brief) before a
        # single byte is written
        from hornlab_search.config import ConfigError, load_config
        probe = path.with_name("." + path.stem + ".probe.yaml")
        try:
            probe.write_text(new_text, encoding="utf-8")
            load_config(probe)
        except ConfigError as exc:
            return {"ok": False, "applied": [],
                    "rejected": [{"key": k, "reason": f"config would not load: {exc}"}
                                 for k in adds],
                    "notes": notes}
        finally:
            if probe.exists():
                probe.unlink()
        notes.append("added rows: regenerate the parameter catalog "
                     "(tools/gen_param_catalog.py --write) so every page lists them")
    missing = sorted(set(accepted) - patched)
    if missing:
        return {"ok": False, "applied": [],
                "rejected": [{"key": key,
                              "reason": "bounds lines could not be located in the YAML"} for key in missing],
                "notes": notes}
    try:
        check = (yaml.safe_load(new_text) or {}).get("bounds") or {}
        for key, (lo, hi) in accepted.items():
            if float(check[key]["lo"]) != lo or float(check[key]["hi"]) != hi:
                raise ValueError(key)
    except Exception:  # noqa: BLE001 - never leave a half-valid file behind
        return {"ok": False, "applied": [],
                "rejected": [{"key": key, "reason": "patched text did not re-parse"}
                             for key in sorted(accepted)],
                "notes": notes}

    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_text)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return {"ok": True, "file": rel, "applied": applied, "notes": notes}


# ---------------------------------------------------------------------------- lanes (E.2, day-plan D.1)
#
# A small SELF-CONTAINED duplicate of the night-status read (day-plan D.1 describes it in
# tools/night_status.py, Group D): the GUI deliberately does NOT import tools/ code. Reads
# only what the night runner and the lane scripts already wrote:
#   - queue logs ``queue_*.log`` under ``runs/overnight/`` (the runner's === START/END lines)
#     and ``runs/nights/`` (the per-lane wrappers), lane-matched by filename;
#   - per-lane night dirs ``runs/nights/<lane>*`` with ``summary.jsonl`` (completed jobs);
#   - the lane lock files ``runs/.gpu.lock`` / ``runs/.cpu.lane.lock`` (same mechanism as
#     ``search/gpulock.py``, read-only).
# Every piece is optional: an empty ``runs/`` yields idle lanes, never a crash (the live lane
# box exists only on the owner's machine).

LANE_ALERT_MIN = 30.0                # minutes without a fresh row while the job is running
LANE_IDS = ("gpu", "cpu")

#: ``--resume <p>`` / ``--run-dir <p>`` / ``--out <p>`` in a queue-log START command.
_RUN_DIR_FLAG = re.compile(r"--(?:resume|run-dir|out)[\s=]+(\"[^\"]+\"|\S+)")


def _mt(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


def _lane_lock(runs: Path, lane: str) -> dict | None:
    """The lane's lock-file holder (``runs/.gpu.lock`` / ``runs/.cpu.lane.lock``), alive or stale.
    Read-only: the file's JSON passes through, ``alive`` is the pid probe, absent file is None."""
    from hornlab_search.search.gpulock import LANE_LOCK_FILES, _pid_alive, _read_lock
    lock = _read_lock(runs / LANE_LOCK_FILES[lane])
    if not isinstance(lock, dict):
        return None
    lock = dict(lock)
    try:
        pid = int(lock.get("pid"))
    except (TypeError, ValueError):
        pid = None
    lock["alive"] = bool(pid is not None and pid > 0 and _pid_alive(pid))
    return clean(lock)


def _lane_queue_log(runs: Path, lane: str) -> Path | None:
    """The newest START/END-formatted queue log naming this lane (``runs/overnight`` first,
    then ``runs/nights``). Logs without a parseable step line are skipped."""
    for base in (runs / "overnight", runs / "nights"):
        best = None
        try:
            cands = [p for p in base.glob(f"queue_*{lane}*.log") if p.is_file()]
        except OSError:
            continue
        for log in sorted(cands, key=lambda p: (_mt(p), p.name), reverse=True):
            if queue_steps(log):
                best = log
                break
        if best is not None:
            return best
    return None


def _lane_running_step(steps: list[dict]) -> dict | None:
    """The last queue step that STARTed and never ENDed (the lane's running job), or None."""
    for st in reversed(steps):
        if st.get("started") and not st.get("ended") and not st.get("skipped"):
            return st
    return None


def _run_dir_from_command(runs: Path, command: str | None) -> Path | None:
    """The run folder a queue-log COMMAND targets (``--resume``/``--run-dir``/``--out``).
    Relative paths resolve against the repo root (``runs``' parent), as the runner invokes
    them. A fresh ``--config`` search has no resolved dir before its first row: None."""
    m = _RUN_DIR_FLAG.search(command or "")
    if not m:
        return None
    tok = m.group(1).strip('"')
    p = Path(tok)
    if not p.is_absolute():
        p = runs.parent / tok
    return p


def _newest_row_age_min(nd: Path, rows: list[dict]) -> float | None:
    """Minutes since the run's newest evaluation row (its ``created_utc``), else the ndjson's
    own mtime, else None when the file is gone."""
    for r in reversed(rows):
        t = _ts(r.get("created_utc"))
        if t is not None:
            return max(0.0, (time.time() - t.timestamp()) / 60.0)
    try:
        return max(0.0, (time.time() - nd.stat().st_mtime) / 60.0)
    except OSError:
        return None


def _lane_run_info(runs: Path, rd: Path | None) -> dict | None:
    """Row count / newest-row age / best J of the running job's run dir (read-only)."""
    if rd is None:
        return None
    nd = rd / "search.ndjson"
    rows = read_ndjson(nd)
    if not rows and not nd.is_file():
        return None
    ok = [r for r in rows if r.get("ok")]
    best = min(ok, key=lambda r: r["objective"]) if ok else None
    rid = rd.name if RUN_ID.match(rd.name) else (rd.parent.name if RUN_ID.match(rd.parent.name) else None)
    return clean({
        "id": rid, "path": str(rd), "n_rows": len(rows), "n_ok": len(ok),
        "best_j": best["objective"] if best else None,
        "newest_row_age_min": _newest_row_age_min(nd, rows),
        "last_row_utc": rows[-1].get("created_utc") if rows else None,
    })


def _lane_last_completed(runs: Path, lane: str) -> dict | None:
    """The last recorded job of the lane's newest ``runs/nights/<lane>*`` night dir (context for
    an idle lane; the queue-log running step drives alerts, never this)."""
    nights = runs / "nights"
    if not nights.is_dir():
        return None
    try:
        cands = [p for p in nights.iterdir()
                 if p.is_dir() and p.name.lower().startswith(lane)
                 and (p / "summary.jsonl").is_file()]
    except OSError:
        return None
    if not cands:
        return None
    night = max(cands, key=lambda p: _mt(p / "summary.jsonl"))
    rows = read_ndjson(night / "summary.jsonl")
    if not rows:
        return None
    job = rows[-1]
    rd = str(job.get("run_dir") or "") or None
    rid = Path(rd).name if rd and RUN_ID.match(Path(rd).name) else \
        (Path(rd).parent.name if rd and RUN_ID.match(Path(rd).parent.name) else None)
    return clean({"id": job.get("id"), "night": night.name, "start": job.get("start"),
                  "end": job.get("end"), "exit_code": job.get("exit_code"),
                  "evals_ndjson": job.get("evals_ndjson"), "best_J": job.get("best_J"),
                  "run_id": rid})


def lane_status(runs: Path) -> dict:
    """Both solve lanes (GPU + CPU) in the D.1 shape for ``GET /api/lanes``.

    Per lane: the lock holder (alive or stale), the newest queue log, the RUNNING job (the last
    queue step STARTed without END), that job's run dir row count and newest-row age, the last
    completed job of the lane's newest night dir, and the ALERT flag: the lane's newest row is
    older than :data:`LANE_ALERT_MIN` minutes (or absent) while its job is running. Missing
    files degrade to idle/None; nothing here is solved or written.
    """
    lanes, alert_lanes = [], []
    for lane in LANE_IDS:
        lock = _lane_lock(runs, lane)
        steps: list[dict] = []
        qlog = _lane_queue_log(runs, lane)
        if qlog is not None:
            steps = queue_steps(qlog)
        running = _lane_running_step(steps)
        rd = _run_dir_from_command(runs, (running or {}).get("command"))
        run = _lane_run_info(runs, rd)
        last = _lane_last_completed(runs, lane)
        alert = None
        if running is not None:
            age = (run or {}).get("newest_row_age_min")
            no_rows = run is not None and not run.get("n_rows")
            started_min = None
            if running.get("started"):
                t = _ts(running["started"] + "Z" if not str(running["started"]).endswith("Z")
                        else running["started"])
                if t is not None:
                    started_min = max(0.0, (time.time() - t.timestamp()) / 60.0)
            if no_rows and started_min is not None and started_min > LANE_ALERT_MIN:
                alert = {"job": running.get("name"), "age_min": 0,
                         "reason": f"no evaluable row yet and job {running.get('name')!r} running "
                                   f"for {round(started_min, 1)} min"}
            elif age is not None and age > LANE_ALERT_MIN:
                alert = {"job": running.get("name"),
                         "age_min": round(age, 1),
                         "reason": f"newest row {round(age, 1)} min old while job "
                                   f"{running.get('name')!r} is running"}
        entry = clean({
            "lane": lane,
            "lock": lock,
            "queue_log": {"name": qlog.name, "steps": steps[-12:]} if qlog else None,
            "job": {"name": running.get("name"), "started": running.get("started"),
                    "command": running.get("command"),
                    "run_dir": str(rd) if rd is not None else None} if running else None,
            "run": run,
            "alert": alert,
            "last_job": last,
            "note": "run dir not resolved (fresh --config job has no stored rows yet)"
                    if running is not None and rd is None else None,
        })
        if alert:
            alert_lanes.append(lane)
        lanes.append(entry)
    return {"lanes": lanes, "alert": bool(alert_lanes), "alert_lanes": alert_lanes}


# ---------------------------------------------------------------------------- analysis outputs (E.1)
#
# Read-only rendering of the Group A analysis tool outputs (tools/analysis/schema.md,
# 2026-11-12). The GUI never runs an analysis and never imports tools/ code: it lists the
# folder the tools wrote (default ``runs/analysis/``, configurable via the server's
# ``--analysis-dir`` flag / the ``App(analysis_dir=...)`` constructor) and passes each
# ``<tool>.json`` through verbatim. Unknown fields ride along (the client ignores them);
# missing fields render as "not present".

#: The tool JSONs Group A writes (schema revision 2026-11-12) plus the two frozen M1 study
#: artifacts (``bo-study-v1.1``, PARENT_M0_FREEZE.md §8). Files with other stems are disclosed
#: as ``extra_tools`` but never parsed.
ANALYSIS_TOOL_JSONS = ("convergence", "seed_variance", "sensitivity", "links", "walls",
                       "ab_compare", "lane_parity", "term_balance", "fidelity", "report_day",
                       "parameter_study", "source_fidelity")
#: REPORT.md is passed through as text (rendered in the page), capped for the API body.
ANALYSIS_REPORT_MD_MAX = 200_000
#: One report-set folder name under the analysis root ("." = the root itself).
ANALYSIS_SET_ID = re.compile(r"^[A-Za-z0-9_.\-]{1,80}$")
#: One served analysis file name (no separators, so it can never escape its base folder).
ANALYSIS_FILE_NAME = re.compile(r"^[A-Za-z0-9_.\-]{1,120}$")
#: The only analysis file kinds the GUI serves (reports, payloads, section PNGs).
ANALYSIS_FILE_SUFFIXES = (".png", ".md", ".json", ".html")


def analysis_sets(analysis_dir: Path) -> list[dict]:
    """The report sets found under ``analysis_dir``: the folder itself (id ``.``) plus every
    immediate subdirectory that holds ``*.json`` or ``REPORT.md`` output. A set carries the
    tool JSONs it holds (parsed only for their ``tool``/``generated_utc`` header — the reports
    themselves are served verbatim by :func:`analysis_report`). Nothing found = empty list.

    ``report_day.py`` writes each section into its own subdirectory, so one level of section
    subdirectories is also discovered: a subdirectory that contains a recognised
    ``<tool>.json`` counts once toward ``n_sections`` and contributes that tool to the union
    list ``tools`` (in ``ANALYSIS_TOOL_JSONS`` order). The ``.`` entry is the analysis root
    itself; its immediate subdirectories are report sets, never sections. ``n_errors`` counts
    the ``status == "error"`` entries of ``<set>/report_day.json``; a missing/unreadable/
    malformed report contributes 0 and never raises."""
    def _section_dirs(base: Path) -> list[Path]:
        try:
            children = sorted((p for p in base.iterdir() if p.is_dir()), key=lambda p: p.name)
        except OSError:
            return []
        return [sub for sub in children
                if any((sub / f"{tool}.json").is_file() for tool in ANALYSIS_TOOL_JSONS)]

    def _n_errors(base: Path) -> int:
        d = _read_json(base / "report_day.json")
        sections = d.get("sections") if isinstance(d, dict) else None
        if not isinstance(sections, list):
            return 0
        return sum(1 for s in sections if isinstance(s, dict) and s.get("status") == "error")

    def _one(sid: str, base: Path) -> None:
        files: list[str] = []
        try:
            files = sorted(p.name for p in base.iterdir()
                           if p.is_file() and (p.suffix == ".json" or p.name == "REPORT.md"))
        except OSError:
            files = []
        section_dirs = [] if sid == "." else _section_dirs(base)
        if not files and not section_dirs:
            return
        root_payloads = {tool: _read_json(base / f"{tool}.json") for tool in ANALYSIS_TOOL_JSONS}
        tools, generated = [], None
        for tool in ANALYSIS_TOOL_JSONS:
            d = root_payloads[tool]
            has_root = isinstance(d, dict) and bool(d.get("tool"))
            has_section = any((sub / f"{tool}.json").is_file() for sub in section_dirs)
            if has_root or has_section:
                tools.append(tool)
            if has_root:
                g = d.get("generated_utc")
                if isinstance(g, str) and (generated is None or g > generated):
                    generated = g
        out.append(clean({"id": sid, "files": files, "tools": tools,
                          "generated_utc": generated, "has_report_md": "REPORT.md" in files,
                          "n_sections": len(section_dirs), "n_errors": _n_errors(base)}))

    out: list[dict] = []
    if not analysis_dir.is_dir():
        return out
    _one(".", analysis_dir)
    try:
        dirs = sorted((p for p in analysis_dir.iterdir() if p.is_dir()), key=lambda p: p.name)
    except OSError:
        dirs = []
    for p in dirs:
        _one(p.name, p)
    return out


def analysis_report(analysis_dir: Path, name: str) -> dict:
    """One report set: every ``<tool>.json`` verbatim (missing/invalid JSON = absent — never
    invented), ``REPORT.md`` as capped text, and the names of unknown-tool JSONs under
    ``extra_tools`` (passed through as names only; Group A may add fields/tools at any time).
    The set id ``.`` is the analysis root itself.

    Sets written by ``report_day.py`` keep each section in its own subdirectory; those are
    returned in ``sections`` (sorted by ``ANALYSIS_TOOL_JSONS`` order then section id), with
    ``errors`` copied verbatim from ``<set>/report_day.json``, ``n_sections`` and
    ``section_index`` (tool -> section ids).

    Flat compatibility rule: a tool with exactly one section payload keeps its payload under
    the flat ``out[tool]`` key exactly as before (so flat fixtures keep working); a tool with
    two or more sections omits the flat key and is carried only by ``sections``. A tool with no
    section payload still falls back to its root-level ``<tool>.json`` when present.
    """
    if name == ".":
        base = analysis_dir
    else:
        if not ANALYSIS_SET_ID.match(name):
            raise ValueError(f"not an analysis report id: {name!r}")
        base = analysis_dir / name
    if not base.is_dir():
        raise FileNotFoundError(name)
    try:
        root_res = analysis_dir.resolve()
        base_res = base.resolve()
    except OSError:
        root_res, base_res = analysis_dir, base
    if base_res != root_res and root_res not in base_res.parents:
        raise FileNotFoundError(name)          # symlinked/..-style escapes stay refused
    out: dict = {"id": name, "base": (analysis_dir / name).as_posix()}
    payloads: dict[str, dict] = {}
    for tool in ANALYSIS_TOOL_JSONS:
        d = _read_json(base / f"{tool}.json")
        if isinstance(d, dict) and d:
            payloads[tool] = d
    out["tools"] = list(payloads)

    # report_day.py layout: <set>/<section>/<tool>.json (+ .md / .png siblings).
    try:
        subdirs = sorted((p for p in base.iterdir() if p.is_dir()), key=lambda p: p.name)
    except OSError:
        subdirs = []
    section_records: list[dict] = []
    for sub in subdirs:
        tool = next((t for t in ANALYSIS_TOOL_JSONS if (sub / f"{t}.json").is_file()), None)
        if tool is None:
            continue
        data = _read_json(sub / f"{tool}.json")
        try:
            names = sorted(p.name for p in sub.iterdir() if p.is_file())
        except OSError:
            names = []
        pngs = [n for n in names if n.lower().endswith(".png")]
        section_records.append({"id": sub.name, "tool": tool,
                                "data": data if isinstance(data, dict) else {},
                                "files": names, "has_png": bool(pngs), "pngs": pngs})
    order = {tool: i for i, tool in enumerate(ANALYSIS_TOOL_JSONS)}
    section_records.sort(key=lambda r: (order[r["tool"]], r["id"]))
    out["sections"] = section_records
    out["n_sections"] = len(section_records)
    section_index: dict[str, list[str]] = {}
    for r in section_records:
        section_index.setdefault(r["tool"], []).append(r["id"])
    out["section_index"] = section_index

    rd = _read_json(base / "report_day.json")
    raw_sections = rd.get("sections") if isinstance(rd, dict) else None
    errors: list[dict] = []
    if isinstance(raw_sections, list):
        for s in raw_sections:
            if isinstance(s, dict) and s.get("status") == "error":
                errors.append({k: s.get(k) for k in ("id", "tool", "status", "error")})
    out["errors"] = errors

    try:
        json_stems = {p.stem for p in base.glob("*.json")}
    except OSError:
        json_stems = set()
    section_stems: set[str] = set()
    for sub in subdirs:
        if not any((sub / f"{t}.json").is_file() for t in ANALYSIS_TOOL_JSONS):
            continue
        try:
            section_stems.update(p.stem for p in sub.glob("*.json"))
        except OSError:
            continue
    out["extra_tools"] = sorted((json_stems - set(payloads) - set(ANALYSIS_TOOL_JSONS))
                                | (section_stems - set(ANALYSIS_TOOL_JSONS)))
    generated = None
    for d in payloads.values():
        g = d.get("generated_utc")
        if isinstance(g, str) and (generated is None or g > generated):
            generated = g
    if generated is not None:
        out["generated_utc"] = generated

    by_tool: dict[str, list[dict]] = {}
    for r in section_records:
        by_tool.setdefault(r["tool"], []).append(r)
    flat: dict[str, dict] = {}
    for tool in ANALYSIS_TOOL_JSONS:
        chosen = by_tool.get(tool, [])
        if len(chosen) == 1:
            flat[tool] = chosen[0]["data"]
        elif not chosen and tool in payloads:
            flat[tool] = payloads[tool]
    out.update(clean(flat))
    try:
        report_md = (base / "REPORT.md").read_text(encoding="utf-8")
    except OSError:
        report_md = None
    if report_md is not None:
        truncated = len(report_md) > ANALYSIS_REPORT_MD_MAX
        if truncated:
            report_md = report_md[:ANALYSIS_REPORT_MD_MAX] \
                + f"\n\n… (truncated at {ANALYSIS_REPORT_MD_MAX} chars)"
        out["report_md"] = report_md
        out["report_md_truncated"] = truncated
    return out


# ---------------------------------------------------------------------------- elites catalog (E.3)


#: elites payload keyed by runs dir -> ((CSV paths+mtimes, runs-dir mtime), payload). A new or
#: changed audit CSV, or a run added/removed, invalidates it.
_ELITES_CACHE: dict[str, tuple] = {}


def _elite_run_info(run_dir: Path | None) -> tuple:
    """One run's facts for the elites cards, read once per catalog build (not once per CSV row):
    (has_run, objective version, {design_hash: lowest-objective atlas cell}, atlas descriptors,
    brief name, family label, brief target constraints).

    ``brief`` / ``family`` mirror ``_run_summary``: the brief's ``name`` from the run's
    ``config.yaml``, and ``config.family`` with the first ndjson row's ``family`` as the fallback.
    ``brief_target`` reads the brief's real YAML nesting — ``target.coverage_h_deg``,
    ``target.coverage_v_deg``, ``target.band_lo_hz``, ``target.band_hi_hz`` and the envelope's
    ``max_mouth_w_mm`` / ``max_mouth_h_mm`` / ``max_depth_mm`` — as the flat card shape
    ``{h_deg, v_deg, f_lo_hz, f_hi_hz, max_mm}``. ``max_mm`` is the largest envelope dimension
    (the brief's max outer size); every key is ``None`` when the brief lacks it. A missing run or
    a run without a brief gets ``None`` for all three, never a guess."""
    has_run = bool(run_dir and (run_dir / "search.ndjson").is_file())
    if not has_run:
        return False, None, {}, {}, None, None, None
    version = run_objective_version(run_dir)
    cfg = _config(run_dir)
    brief = cfg.get("brief") if isinstance(cfg.get("brief"), dict) else None
    brief_name = brief.get("name") if brief else None
    family = cfg.get("family")
    if not family:
        rows = read_ndjson(run_dir / "search.ndjson")
        family = rows[0].get("family") if rows else None
    brief_target = None
    if brief is not None:
        target = _as_dict(brief.get("target"))
        envelope = _as_dict(brief.get("envelope"))
        dims = [envelope.get(k) for k in ("max_mouth_w_mm", "max_mouth_h_mm", "max_depth_mm")]
        dims = [float(v) for v in dims if isinstance(v, (int, float)) and not isinstance(v, bool)]
        brief_target = {
            "h_deg": target.get("coverage_h_deg"),
            "v_deg": target.get("coverage_v_deg"),
            "f_lo_hz": target.get("band_lo_hz"),
            "f_hi_hz": target.get("band_hi_hz"),
            "max_mm": max(dims) if dims else None,
        }
    best: dict[str, dict] = {}
    descs: dict = {}
    heat = _read_json(run_dir / "archive_heatmap.json")
    if isinstance(heat, dict) and isinstance(heat.get("cells"), list):
        descs = heat.get("descriptors") if isinstance(heat.get("descriptors"), dict) else {}
        key = lambda c: c.get("objective") if isinstance(c.get("objective"), (int, float)) else float("inf")
        for c in heat["cells"]:
            if not isinstance(c, dict):
                continue
            h = c.get("design_hash")
            if h is not None and (h not in best or key(c) < key(best[h])):
                best[h] = c
    return True, version, best, descs, brief_name, family, brief_target


def elites_catalog(runs: Path, root: Path) -> dict:
    """The elites catalog: every design row recorded in a committed gate-audit CSV.

    Sources are the same CSVs the run-detail gate audit reads
    (``docs/data/gate_audit_*/`` and ``scratch/gate_audit_*``, newest directory first); a
    design seen in an earlier audit keeps its newest entry. Every recorded row gets a card —
    with the gate chips ONLY for columns the CSV actually carries (a failed row shows fail
    chips, never an invented pass), its J + tier, the run link when that run still exists, and
    the design's quality-diversity coverage cell (``archive_heatmap.json``) when the run has
    an atlas. Absent audit = ``{"available": False}`` and an empty catalog — nothing is
    invented. Read-only.
    """
    sources = list(_gate_audit_paths(root))
    if not sources:
        return {"available": False, "sources": [], "cards": [],
                "note": "no gate-audit CSV under docs/data/gate_audit_*/ or scratch/gate_audit_*/"}
    stamp = (tuple((str(p), _mt(p)) for p in sources), _mt(runs))
    hit = _ELITES_CACHE.get(str(runs))
    if hit and hit[0] == stamp:
        return hit[1]
    cards: list[dict] = []
    seen: set[tuple[str, str]] = set()
    run_info: dict[str, tuple] = {}            # run_id -> (has_run, version, {hash: best cell}, descriptors)
    n_pass = 0
    for csv_path in sources:
        try:
            with csv_path.open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
        except OSError:
            continue
        if not rows:
            continue
        header = set(rows[0].keys())
        gates = [k for k in GATE_AUDIT_COLUMNS if k in header]
        try:
            source = csv_path.relative_to(root).as_posix()
        except ValueError:
            source = str(csv_path)
        for r in rows:
            h = (r.get("design") or "").strip()
            run_id = (r.get("run") or "").strip()
            if not h:
                continue
            key = (run_id, h)
            if key in seen:
                continue
            seen.add(key)
            gate_vals = {k: v for k in gates if (v := _csv_bool(r.get(k))) is not None}
            j_raw = r.get("J")
            try:
                j = float(j_raw) if j_raw not in (None, "") else None
            except (TypeError, ValueError):
                j = None
            tier = (r.get("tier") or "").strip() or None
            pass_all = _csv_bool(r.get("pass_all"))
            run_dir = runs / run_id if run_id and RUN_ID.match(run_id) else None
            info = run_info.get(run_id)
            if info is None:
                info = run_info[run_id] = _elite_run_info(run_dir)
            has_run, version, heat_cells, descs, brief, family, brief_target = info
            cell = None
            hit = heat_cells.get(h) if has_run else None
            if hit is not None:
                cell = {"descriptors": {"h": descs.get("h"), "v": descs.get("v")},
                        "h_center": hit.get("h_center"), "v_center": hit.get("v_center")}
            cards.append(clean({
                "run": run_id or None, "hash": h, "J": j, "tier": tier,
                "gates": gate_vals, "pass_all": pass_all, "source": source,
                "run_linked": has_run, "objective_version": version if has_run else None,
                "coverage_cell": cell,
                "has_mesh": bool(run_dir and (run_dir / "designs" / h / "mesh.msh").is_file()),
                "brief": brief, "family": family, "brief_target": brief_target,
            }))
            if pass_all is True:
                n_pass += 1
    cards.sort(key=lambda c: (c["pass_all"] is not True,
                              c["J"] if c["J"] is not None else float("inf")))
    gate_keys: set[str] = set()
    for c in cards:
        gate_keys |= set(c["gates"])
    briefs = sorted({c["brief"] for c in cards if c["brief"] is not None}, key=str)
    families = sorted({c["family"] for c in cards if c["family"] is not None}, key=str)
    out = {"available": True, "sources": sorted({c["source"] for c in cards}),
           "labels": {k: GATE_AUDIT_LABELS.get(k, k) for k in sorted(gate_keys)},
           "cards": cards, "n_pass": n_pass,
           "briefs": briefs, "families": families}
    _ELITES_CACHE[str(runs)] = (stamp, out)
    return out
