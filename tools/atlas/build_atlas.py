"""Project atlas: one self-contained HTML report over every search the project has run.

Read-only over ``runs/`` (each run dir's ``run.json`` + ``search.ndjson``, inline ``verify/``,
and Bayesian ``study-*/screen``). Writes ``index.html`` (and ``atlas.json`` with ``--json``; template +
embedded data, no server, no build step) to ``--out``. Optional ``--gallery`` embeds horn
render cards (e.g. ``scratch/top2/cards`` with ``picks.json``) as cropped JPEG thumbnails.

Run after any checkpoint::

    .venv\\Scripts\\python.exe tools/atlas/build_atlas.py --out docs/atlas \\
        --gallery scratch/top2/cards

``docs/atlas/index.html`` is then live on GitHub Pages at
https://llevaachingada.github.io/Hornfab/atlas/ once pushed to main.

J is only comparable inside one objective version; every J aggregate here is grouped by
(objective version, brief). Verdicts ("lean in", "exhausted", ...) are printed heuristics
with their rule text in the page; they are prompts for a human decision, never applied.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TEMPLATE = HERE / "atlas_template.html"

#: refusal kind -> compact code used in the eval columns (0 = solved).
KIND_CODES = {"": 0, "invalid_geometry": 1, "mesh_too_large": 2, "solve_failed": 3}
FAIL_SENTINEL = 999.0  # objective >= this is the refusal penalty, never a real J
GRID = [i / 20 for i in range(21)]  # budget fractions for normalised convergence

# Verdict thresholds (shown verbatim in the page's method section).
RULES = {
    "lean_in_late_gain_pct": 1.0,      # latest run still gained > this in its last 20 %
    "exhausted_min_solves": 400,       # group spent at least this many new solves
    "exhausted_spread_pct": 3.0,       # and its >= 2 seeds' bests sit within this of each other
    "leak_refusal_share": 0.25,        # refused / attempted above this = budget leak
    "thin_max_solves": 150,            # fewer new solves than this = under-explored
    "plateau_late_gain_pct": 0.5,      # latest run gained <= this in its last 20 % = settled at this budget
    "stale_days": 10,                  # latest run older than this ...
    "legacy_max_ov": 3,                # ... on objective v<=3 = legacy
}


def _ts(s: str | None) -> float | None:
    if not s:
        return None
    try:
        return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def _finite_mean(xs: Any) -> float | None:
    if not isinstance(xs, list):
        return None
    v = [float(x) for x in xs if isinstance(x, (int, float)) and math.isfinite(x)]
    return sum(v) / len(v) if v else None


def _r(x: float | None, nd: int = 3) -> float | None:
    if x is None or not math.isfinite(x):
        return None
    return round(x, nd)


def _rows(path: Path) -> list[dict]:
    out = []
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # a live run may have a half-written last line
    except OSError:
        pass
    return out


def _solved(row: dict) -> bool:
    j = row.get("objective")
    return bool(row.get("ok")) and isinstance(j, (int, float)) and math.isfinite(j) and j < FAIL_SENTINEL


def _dims_mm(row: dict) -> tuple[int | None, int | None, int | None]:
    """Full mouth width, height and depth from the (possibly symmetry-reduced) bbox."""
    b = row.get("bbox_m")
    if not (isinstance(b, list) and len(b) == 6):
        return None, None, None
    x0, y0, z0, x1, y1, z1 = (float(v) for v in b)
    w = 2 * max(abs(x0), abs(x1)) * 1000
    h = 2 * max(abs(y0), abs(y1)) * 1000
    d = (z1 - z0) * 1000
    return round(w), round(h), round(d)


def _brief_name(cfg: dict, fallback: str) -> str:
    b = cfg.get("brief") if isinstance(cfg, dict) else None
    if isinstance(b, dict) and b.get("name"):
        return str(b["name"])
    return fallback or "unnamed"


def discover(runs_dir: Path) -> list[dict]:
    """One record per run: meta from run.json (or the study config), rows from search.ndjson."""
    found = []
    for rj in sorted(runs_dir.glob("*/run.json")):
        try:
            meta = json.loads(rj.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        found.append({"dir": rj.parent, "meta": meta, "kind": "run"})
    for cfgp in sorted(runs_dir.glob("study-*/screen/config.yaml")):
        try:
            cfg = yaml.safe_load(cfgp.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            cfg = {}
        found.append({"dir": cfgp.parent, "meta": {"config": cfg, "run_id": cfgp.parent.parent.name,
                                                    "mode": "screen", "status": "finished"}, "kind": "study"})
    return found


def build(runs_dir: Path, gallery: list[Path] | None = None, now: float | None = None) -> dict:
    now = now or datetime.now(timezone.utc).timestamp()
    runs: list[dict] = []
    ev = defaultdict(list)  # columnar eval store
    screen_j: dict[tuple, float] = {}
    verify_rows: list[tuple] = []
    unique: set = set()

    for item in discover(runs_dir):
        meta, d = item["meta"], item["dir"]
        cfg = meta.get("config") or {}
        search = cfg.get("search") or {}
        rows = _rows(d / "search.ndjson")
        if not rows:
            continue
        ov = meta.get("objective_version")
        if ov is None:
            ov = next((r.get("objective_version") for r in rows if r.get("objective_version") is not None),
                      (cfg.get("objective") or {}).get("version"))
        algo = "bayes" if item["kind"] == "study" else (search.get("algorithm") or "cma")
        mode = meta.get("mode") or rows[0].get("mode") or "screen"
        family = meta.get("family") or rows[0].get("family") or cfg.get("family") or "?"
        brief = _brief_name(cfg, meta.get("config_name") or cfg.get("name") or "")
        lib = meta.get("lib_shas") or {}
        pin = (lib.get("hornlab_beat_bem") or "")[:7] or "?"
        lane = next((r.get("lane") for r in rows if r.get("lane")), None) or (
            "cpu" if meta.get("backend") == "beat_cpu" else "gpu")
        idx = len(runs)
        times = [t for t in (_ts(r.get("created_utc")) for r in rows) if t]
        start = _ts(meta.get("started_utc") or meta.get("created_utc")) or (min(times) if times else None)
        end = _ts(meta.get("finished_utc")) or (max(times) if times else start)
        if times:
            end = max(end or 0, max(times))
        refusals: Counter = Counter()
        best = math.inf
        first_j = None
        curve_abs = []  # (new-valid index, best) change points
        n_new_valid = n_cached = n_new = 0
        gpu_s = 0.0
        for r in rows:
            cached = bool(r.get("cached"))
            solved = _solved(r)
            kind = r.get("kind") or ("" if solved else "solve_failed")
            if not solved:
                refusals[kind] += 1
            if cached:
                n_cached += 1
            else:
                n_new += 1
            sec = (r.get("seconds") or {}).get("total")
            if isinstance(sec, (int, float)) and not cached:
                gpu_s += float(sec)
            j = float(r["objective"]) if solved else None
            if solved and not cached:
                n_new_valid += 1
            if solved:
                if first_j is None:
                    first_j = j
                if j < best:
                    best = j
                    curve_abs.append([max(n_new_valid, 1), _r(j, 4)])
            m = r.get("metrics") or {}
            w, h, z = _dims_mm(r)
            t = _ts(r.get("created_utc")) or start
            ev["r"].append(idx)
            ev["t"].append(int(t // 60) if t else None)
            ev["J"].append(_r(j, 4))
            ev["k"].append(KIND_CODES.get(kind, 4) if not solved else 0)
            ev["c"].append(1 if cached else 0)
            ev["s"].append(_r(float(sec), 1) if isinstance(sec, (int, float)) else None)
            ev["d"].append(r.get("n_dof"))
            ev["bh"].append(_r(_finite_mean(m.get("bw_h_deg")), 1) if solved else None)
            ev["bv"].append(_r(_finite_mean(m.get("bw_v_deg")), 1) if solved else None)
            ev["di"].append(_r(_finite_mean(m.get("di_db")), 2) if solved else None)
            ev["w"].append(w if solved else None)
            ev["h"].append(h if solved else None)
            ev["z"].append(z if solved else None)
            if solved and not cached:
                unique.add((r.get("design_hash"), r.get("solve_hash")))
            if solved and mode == "screen" and not cached:
                key = (r.get("design_hash"), ov)
                screen_j[key] = min(screen_j.get(key, math.inf), j)
            if solved and mode == "verify":
                verify_rows.append((r.get("design_hash"), ov, j, idx))
        # inline verify rows (screen runs that carry a verify/ sub-dir)
        for r in _rows(d / "verify" / "search.ndjson"):
            if _solved(r):
                verify_rows.append((r.get("design_hash"), ov, float(r["objective"]), idx))
        if not math.isfinite(best):
            best = None
        # normalised best-so-far on the budget-fraction grid, from the new-valid curve
        norm = None
        evals_to_1pct = last20 = None
        if best is not None and first_j and n_new_valid >= 10:
            bs, cur, it = [], first_j, iter(curve_abs)
            pts = list(curve_abs)
            for g in GRID:
                lim = max(1, round(g * n_new_valid))
                while pts and pts[0][0] <= lim:
                    cur = pts.pop(0)[1]
                bs.append(_r(cur / first_j, 4))
            norm = bs
            thr = best * 1.01 if best >= 0 else best * 0.99
            evals_to_1pct = next((c[0] for c in curve_abs if c[1] <= thr), None)
            at80 = first_j
            for c in curve_abs:
                if c[0] <= 0.8 * n_new_valid:
                    at80 = c[1]
            last20 = _r((at80 - best) / abs(at80) * 100 if at80 else 0.0, 2)
        qd = meta.get("qd") or {}
        runs.append({
            "id": meta.get("run_id") or d.name, "brief": brief, "family": family, "ov": ov, "algo": algo,
            "mode": mode, "lane": lane, "pin": pin, "seed": meta.get("cma_seed") or search.get("seed"),
            "status": meta.get("status"), "start": int(start // 60) if start else None,
            "end": int(end // 60) if end else None, "rows": len(rows), "new": n_new, "cached": n_cached,
            "solved": n_new_valid, "ref": dict(refusals), "first": _r(first_j, 4), "best": _r(best, 4),
            "gpu_h": _r(gpu_s / 3600, 3), "norm": norm, "curve": curve_abs[-60:] if len(curve_abs) > 60 else curve_abs,
            "to1": evals_to_1pct, "late": last20, "qd_cov": _r(qd.get("coverage"), 4),
            "qd_bins": qd.get("occupied_bins"), "verify_of": meta.get("verify_of"),
            "config": meta.get("config_name") or cfg.get("name"),
        })

    pairs = []
    for h, ov, vj, idx in verify_rows:
        sj = screen_j.get((h, ov))
        if sj is not None and math.isfinite(sj):
            pairs.append([_r(sj, 4), _r(vj, 4), ov, idx])

    groups = summarise_groups(runs, now)
    out = {
        "generated_utc": datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rules": RULES, "kind_codes": KIND_CODES, "runs": runs, "groups": groups, "fid": pairs,
        "ev": dict(ev), "totals": {**totals(runs, ev), "unique_designs": len(unique)}, "gallery": load_gallery(gallery or []),
    }
    return out


def totals(runs: list[dict], ev: dict) -> dict:
    new = [i for i in range(len(ev["r"])) if not ev["c"][i]]
    solved = [i for i in new if ev["k"][i] == 0]
    return {
        "runs": len(runs), "screen_runs": sum(r["mode"] == "screen" for r in runs),
        "verify_runs": sum(r["mode"] == "verify" for r in runs),
        "attempts": len(new), "solved": len(solved), "refused": len(new) - len(solved),
        "gpu_h": _r(sum(r["gpu_h"] or 0 for r in runs), 1),
        "briefs": len({r["brief"] for r in runs}), "families": sorted({r["family"] for r in runs}),
        "algos": dict(Counter(r["algo"] for r in runs)), "ovs": dict(Counter(str(r["ov"]) for r in runs)),
        "first_day": min((r["start"] for r in runs if r["start"]), default=None),
        "last_day": max((r["end"] for r in runs if r["end"]), default=None),
    }


def line_name(run: dict) -> str:
    """A search line = one typology config on one brief; seeds of it are replicates."""
    name = str(run.get("config") or run.get("family") or "?")
    return re.sub(r"(_seed\d+|_s\d{3,5})$", "", name)


def summarise_groups(runs: list[dict], now: float) -> list[dict]:
    by = defaultdict(list)
    for i, r in enumerate(runs):
        if r["mode"] == "screen":
            by[(r["ov"], r["brief"], line_name(r))].append(i)
    out = []
    for (ov, brief, line), idxs in by.items():
        rs = [runs[i] for i in idxs]
        bests = [r["best"] for r in rs if r["best"] is not None]
        solved = sum(r["solved"] for r in rs)
        attempted = sum(r["new"] for r in rs)
        refused = sum(sum(r["ref"].values()) for r in rs)
        latest = max(rs, key=lambda r: r["start"] or 0)
        best_run = min((r for r in rs if r["best"] is not None), key=lambda r: r["best"], default=None)
        per_seed: dict = {}
        for r in rs:
            if r["best"] is not None and r["solved"] >= 30:
                k = r["seed"]
                per_seed[k] = min(per_seed.get(k, math.inf), r["best"])
        spread = None
        if len(per_seed) >= 2:  # resumes of one seed are not replicates
            gb = sorted(per_seed.values())
            spread = _r((gb[-1] - gb[0]) / abs(gb[0]) * 100 if gb[0] else None, 1)
        tags = []
        late = latest["late"]
        age_days = (now / 60 - (latest["end"] or latest["start"] or 0)) / 1440
        if (ov is None or (isinstance(ov, int) and ov <= RULES["legacy_max_ov"])) and age_days > RULES["stale_days"]:
            tags.append("legacy")
        else:
            if late is not None and late > RULES["lean_in_late_gain_pct"]:
                tags.append("lean_in")
            if (solved >= RULES["exhausted_min_solves"] and spread is not None
                    and spread <= RULES["exhausted_spread_pct"] and not (late and late > RULES["lean_in_late_gain_pct"])):
                tags.append("exhausted")
            if solved < RULES["thin_max_solves"]:
                tags.append("thin")
            elif (late is not None and late <= RULES["plateau_late_gain_pct"] and "exhausted" not in tags):
                tags.append("plateau")
        if attempted and refused / attempted > RULES["leak_refusal_share"]:
            tags.append("leak")
        out.append({
            "ov": ov, "brief": brief, "line": line, "runs": idxs, "n_runs": len(rs), "solved": solved,
            "attempted": attempted, "refused": refused, "best": min(bests) if bests else None,
            "best_run": runs.index(best_run) if best_run else None,
            "median_best": _r(statistics.median(bests), 4) if bests else None, "spread_pct": spread,
            "seeds": len(per_seed),
            "families": sorted({r["family"] for r in rs}), "algos": sorted({r["algo"] for r in rs}),
            "gpu_h": _r(sum(r["gpu_h"] or 0 for r in rs), 2), "latest_late": late,
            "first": min(r["start"] or 0 for r in rs), "last": max(r["end"] or 0 for r in rs), "tags": tags,
        })
    out.sort(key=lambda g: (-(g["last"] or 0)))
    return out


def load_gallery(dirs: list[Path]) -> list[dict]:
    """Horn render cards -> cropped JPEG data URIs (render rows only)."""
    if not dirs:
        return []
    try:
        from PIL import Image
    except ImportError:
        print("gallery skipped: Pillow not installed", file=sys.stderr)
        return []
    items = []
    for d in dirs:
        picks: dict = {}
        pj = d.parent / "picks.json"
        if pj.exists():  # tools/render/top2_pick.py: cards are <slug(typ)>_<rank>.png in list order
            try:
                rank: Counter = Counter()
                for p in json.loads(pj.read_text(encoding="utf-8")):
                    slug = re.sub(r"[^a-z0-9]+", "_", str(p.get("typ", "")).lower()).strip("_")
                    rank[slug] += 1
                    picks[f"{slug}_{rank[slug]}"] = p
            except (OSError, json.JSONDecodeError, AttributeError, TypeError):
                pass
        for png in sorted(d.glob("*.png")):
            try:
                im = Image.open(png).convert("RGB")
            except OSError:
                continue
            W, H = im.size
            if H > 1.15 * W:  # tall render card: keep the render row under the title
                im = im.crop((0, int(H * 0.055), W, int(H * 0.36)))
            im.thumbnail((720, 720))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=78, optimize=True)
            title = png.stem
            pick = picks.get(title)
            items.append({"name": title, "src": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(),
                          "J": _r(pick.get("J"), 3) if pick else None, "brief": pick.get("brief") if pick else None,
                          "typ": pick.get("typ") if pick else None, "job": pick.get("job") if pick else None})
    return items


def write(out_dir: Path, data: dict, with_json: bool = False) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    if with_json:
        (out_dir / "atlas.json").write_text(json.dumps(data, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    html = TEMPLATE.read_text(encoding="utf-8")
    payload = json.dumps(data, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    page = out_dir / "index.html"
    page.write_text(html.replace("/*__ATLAS_DATA__*/null", payload, 1), encoding="utf-8")
    return page


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", type=Path, default=REPO / "runs", help="runs directory (read-only)")
    ap.add_argument("--out", type=Path, required=True, help="output folder for index.html + atlas.json")
    ap.add_argument("--gallery", type=Path, action="append", default=[],
                    help="folder of horn render PNG cards to embed (repeatable)")
    ap.add_argument("--json", action="store_true", help="also write the aggregated data as atlas.json")
    a = ap.parse_args(argv)
    data = build(a.runs, a.gallery)
    page = write(a.out, data, a.json)
    t = data["totals"]
    print(f"atlas: {t['runs']} runs, {t['solved']:,} solves, {t['refused']:,} refused, {t['gpu_h']} GPU h, "
          f"{len(data['groups'])} brief groups, {len(data['fid'])} screen/verify pairs, "
          f"{len(data['gallery'])} renders -> {page} ({page.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
