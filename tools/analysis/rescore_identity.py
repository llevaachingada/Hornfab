"""Rescore stored responses under one score identity, and measure its frequency noise floor
(senior plan WP 1.4 + 1.5, 2026-11-17).

Read-only; every score goes through ``objective.replay.replay_run_dir`` (parity-exact DI, v9
dispatch, optional ``objective.score_grid``). J from different score identities is never mixed.

    # WP 1.4: per-design J and per-lane bests under a brief
    python tools/analysis/rescore_identity.py rescore --brief <brief.yaml> --out <dir> runs/<run> ...

    # WP 1.5: frequency part of the noise floor from screen/verify pairs of study runs
    #   (screen = run/designs/<h>, verify = run/verify/designs/<h>, same mesh, more frequencies)
    python tools/analysis/rescore_identity.py floor --brief <brief.yaml> --out <dir> runs/study-* --top 28
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _score(run_dir: Path, h: str, brief, config_path: Path):
    from hornlab_search.objective.replay import replay_run_dir
    r = replay_run_dir(run_dir, h, brief=brief, config_path=config_path)
    return r


def _lane(run_dir: Path) -> str:
    try:
        import yaml
        raw = yaml.safe_load((run_dir / "config.yaml").read_text(encoding="utf-8"))
        return str(raw.get("name") or run_dir.name)
    except Exception:  # noqa: BLE001
        return run_dir.name


def rescore(runs, brief, out: Path) -> dict:
    from hornlab_search.objective.replay import load_brief_context
    b = load_brief_context(brief)
    rows, ids = [], set()
    for run in runs:
        lane = _lane(run)
        for ddir in sorted((run / "designs").glob("*")):
            try:
                r = _score(run, ddir.name, b, run / "config.yaml")
                rows.append({"run": run.name, "lane": lane, "design_hash": ddir.name,
                             "status": r.status, "j": r.j, "score_id": r.score_id,
                             "reasons": list(r.reasons)})
                if r.j is not None:
                    ids.add(r.score_id)
            except Exception as exc:  # noqa: BLE001 - reported, never hidden
                rows.append({"run": run.name, "lane": lane, "design_hash": ddir.name,
                             "status": "error", "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
    out.mkdir(parents=True, exist_ok=True)
    with (out / "rescore.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, default=float) + "\n")
    best: dict = {}
    for r in rows:
        j = r.get("j")
        if j is None or not math.isfinite(float(j)):
            continue
        if r["lane"] not in best or j < best[r["lane"]]["j"]:
            best[r["lane"]] = {"j": float(j), "run": r["run"], "design_hash": r["design_hash"]}
    summary = {"brief": str(brief), "score_ids": sorted(ids), "n": len(rows),
               "scored": sum(r.get("j") is not None for r in rows),
               "status_counts": _counts(r["status"] for r in rows),
               "lane_best": dict(sorted(best.items(), key=lambda kv: kv[1]["j"]))}
    (out / "rescore_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def _counts(it):
    c: dict = {}
    for k in it:
        c[k] = c.get(k, 0) + 1
    return c


def _spearman(a, b) -> float:
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    if len(a) < 3:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def floor_stats(pairs, top: int) -> dict:
    """pairs: list of (screen_j, verify_j). The frequency part of the floor is the sd of
    (screen - verify) among the ``top`` designs by verify J (and over all)."""
    p = np.array([(s, v) for s, v in pairs if s is not None and v is not None
                  and math.isfinite(s) and math.isfinite(v)], dtype=float)
    if p.size == 0:
        return {"n_pairs": 0}
    d = p[:, 0] - p[:, 1]
    order = np.argsort(p[:, 1])[:top]
    return {"n_pairs": int(len(p)), "mean_diff_all": float(d.mean()),
            "sd_diff_all": float(d.std(ddof=1)) if len(d) > 1 else float("nan"),
            "spearman_all": _spearman(p[:, 0], p[:, 1]),
            "top": int(len(order)), "sd_diff_top": float(d[order].std(ddof=1)) if len(order) > 1 else float("nan"),
            "spearman_top": _spearman(p[order, 0], p[order, 1])}


def floor(runs, brief, out: Path, top: int) -> dict:
    from hornlab_search.objective.replay import load_brief_context
    b = load_brief_context(brief)
    pairs, ids, detail = [], set(), []
    for run in runs:
        vdir = run / "verify"
        if not (vdir / "designs").is_dir():
            continue
        for ddir in sorted((vdir / "designs").glob("*")):
            h = ddir.name
            if not (run / "designs" / h).is_dir():
                continue
            try:
                s = _score(run, h, b, run / "config.yaml")
                v = _score(vdir, h, b, run / "config.yaml")
            except Exception as exc:  # noqa: BLE001
                detail.append({"run": run.name, "design_hash": h, "error": str(exc)[:200]})
                continue
            ids.update(x.score_id for x in (s, v) if x.j is not None)
            pairs.append((s.j, v.j))
            detail.append({"run": run.name, "design_hash": h, "screen_j": s.j, "verify_j": v.j})
    stats = floor_stats(pairs, top)
    summary = {"brief": str(brief), "score_ids": sorted(ids), **stats,
               "note": "frequency part only; the mesh part comes from B1 (stage 2)"}
    out.mkdir(parents=True, exist_ok=True)
    (out / "floor_pairs.jsonl").write_text("\n".join(json.dumps(r, default=float) for r in detail) + "\n",
                                          encoding="utf-8")
    (out / "floor_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("rescore", "floor"):
        p = sub.add_parser(name)
        p.add_argument("runs", nargs="+", type=Path)
        p.add_argument("--brief", required=True)
        p.add_argument("--out", type=Path, required=True)
        if name == "floor":
            p.add_argument("--top", type=int, default=28)
    a = ap.parse_args(argv)
    res = rescore(a.runs, a.brief, a.out) if a.cmd == "rescore" else floor(a.runs, a.brief, a.out, a.top)
    print(json.dumps(res, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
