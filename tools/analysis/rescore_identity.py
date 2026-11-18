"""Rescore stored responses under one score identity, and measure its frequency noise floor
(senior plan WP 1.4 + 1.5, 2026-11-17).

Read-only; every score goes through ``objective.replay.replay_run_dir`` (parity-exact DI, v9
dispatch, optional ``objective.score_grid``). J from different score identities is never mixed.

    # WP 1.4: per-design J and per-lane bests under a brief
    python tools/analysis/rescore_identity.py rescore --brief <brief.yaml> --out <dir> runs/<run> ...

    # WP 1.5: frequency part of the noise floor from screen/verify pairs of study runs
    #   (screen = run/designs/<h>, verify = run/verify/designs/<h>, same mesh, more frequencies)
    python tools/analysis/rescore_identity.py floor --brief <brief.yaml> --out <dir> runs/study-* --top 28

    # WP 1.4 side by side (cloud senior 2026-11-18): one column per identity, NEVER pooled.
    #   --run-brief keeps only runs whose own config names that brief file (stem match), so a
    #   rescore is "the home-brief history", not every run on disk.
    python tools/analysis/rescore_identity.py rescore --brief <v10.yaml> --run-brief <stem> --out <d10> runs/*
    python tools/analysis/rescore_identity.py compare --out <dir> v7=<d7> v9=<d9> v10=<d10>
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
    return replay_run_dir(run_dir, h, brief=brief, config_path=config_path)


def _row_score_identity(r, brief, objective_block, score_code) -> str:
    """Identity of the SCORE that produced one row, WITHOUT per-design parts.

    A row's ``score_id`` folds ``metric_id`` (the design's own physical/metric arrays), so two
    designs under one brief legitimately carry different ``score_id`` values. Whether a set of
    rows shares ONE score identity is decided by (score code, objective version, weights,
    objective block, brief identity) — exactly the replay's score-payload fields minus
    ``metric_id``. 2026-11-18 (WP 1.4): the compare's ``mixed_identity`` previously counted
    distinct per-design ``score_id`` values and therefore read True on any multi-design column.
    """
    from hornlab_search.objective.replay import _hash as _replay_hash
    return _replay_hash({
        "kind": "score",
        "score_code": score_code,
        "objective_version": r.objective_version,
        "weights": r.weights,
        "objective_block": objective_block,
        "brief_hash": (brief.brief_hash() if brief is not None else None),
        "brief_name": (brief.name if brief is not None else None),
    })


def _lane(run_dir: Path) -> str:
    try:
        import yaml
        raw = yaml.safe_load((run_dir / "config.yaml").read_text(encoding="utf-8"))
        return str(raw.get("name") or run_dir.name)
    except Exception:  # noqa: BLE001
        return run_dir.name


def _run_brief_stem(run_dir: Path) -> str | None:
    """Stem of the brief file a run's own config.yaml names (None when it names none)."""
    try:
        import yaml
        raw = yaml.safe_load((run_dir / "config.yaml").read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return None
    bf = raw.get("brief_file")
    return Path(str(bf).replace("\\", "/")).stem if bf else None


def rescore(runs, brief, out: Path, run_brief: str | None = None) -> dict:
    from hornlab_search.objective.replay import load_brief_context, SCORE_CODE_VERSION
    b = load_brief_context(brief)
    rows, ids, skipped = [], set(), []
    score_identity_ids: set[str] = set()
    for run in runs:
        if not (run / "designs").is_dir():
            continue
        if run_brief is not None and _run_brief_stem(run) != run_brief:
            skipped.append(run.name)
            continue
        lane = _lane(run)
        for ddir in sorted((run / "designs").glob("*")):
            try:
                r = _score(run, ddir.name, b, run / "config.yaml")
                rows.append({"run": run.name, "lane": lane, "design_hash": ddir.name,
                             "status": r.status, "j": r.j, "score_id": r.score_id,
                             "stored_j": r.stored_j, "parity_delta": r.parity_delta,
                             "reasons": list(r.reasons)})
                if r.j is not None:
                    ids.add(r.score_id)
                    score_identity_ids.add(_row_score_identity(r, b, b.objective_block,
                                                               SCORE_CODE_VERSION))
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
    summary = {"brief": str(brief), "objective_version": int(b.objective_version),
               "run_brief_filter": run_brief, "runs_skipped_other_brief": len(skipped),
               "score_ids": sorted(ids), "n": len(rows),
               "scored": sum(r.get("j") is not None for r in rows),
               "score_identity_ids": sorted(score_identity_ids),
               "mixed_identity": len(score_identity_ids) > 1,
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


def compare(columns: dict, out: Path) -> dict:
    """Per-lane bests from several ``rescore`` outputs, one column per score identity.

    Each column is ranked only against itself (``rank_<label>``); no J from one column is ever
    compared with, subtracted from or sorted against another column's J (plan §7 invariant 7).
    A column whose summary carries more than one score_id is reported, not merged.
    """
    lanes: dict = {}
    meta: dict = {}
    for label, d in columns.items():
        summ = json.loads((Path(d) / "rescore_summary.json").read_text(encoding="utf-8"))
        # mixed_identity: prefer the rescore's own per-row score-identity count (2026-11-18 fix —
        # per-design score_id values legitimately differ inside one column). Fall back per summary
        # capability: new field -> derived; legacy summaries only -> the old (broken) semantics.
        if "score_identity_ids" in summ:
            mixed = len(summ.get("score_identity_ids", [])) > 1
        else:
            mixed = len(summ.get("score_ids", [])) > 1
        meta[label] = {"brief": summ.get("brief"), "objective_version": summ.get("objective_version"),
                       "score_ids": summ.get("score_ids", []),
                       "score_identity_ids": summ.get("score_identity_ids", []),
                       "scored": summ.get("scored"), "n": summ.get("n"),
                       "mixed_identity": mixed}
        best = summ.get("lane_best", {})
        for rank, (lane, row) in enumerate(sorted(best.items(), key=lambda kv: kv[1]["j"]), 1):
            lanes.setdefault(lane, {})[label] = {"j": row["j"], "rank": rank,
                                                 "design_hash": row["design_hash"], "run": row["run"]}
    labels = list(columns)
    out.mkdir(parents=True, exist_ok=True)
    head = ["lane"] + [f"{k}_{lab}" for lab in labels for k in ("rank", "j", "design")]
    lines = [",".join(head)]
    for lane in sorted(lanes, key=lambda ln: tuple(lanes[ln].get(lab, {}).get("rank", 10**6)
                                                   for lab in labels)):
        cells = [lane]
        for lab in labels:
            c = lanes[lane].get(lab)
            cells += ([str(c["rank"]), f"{c['j']:.6f}", c["design_hash"]] if c else ["", "", ""])
        lines.append(",".join(cells))
    (out / "lane_bests_side_by_side.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    res = {"columns": meta, "lanes": lanes,
           "rule": "ranks are within one column only; J is never compared across columns"}
    (out / "compare_summary.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return res


def discover_runs(root: Path, max_depth: int = 3) -> list[Path]:
    """Run dirs under ``root`` (a dir holding ``config.yaml`` AND ``designs/``), depth-limited,
    sorted. Avoids a command line of thousands of paths on Windows (32 767-char limit) and also
    finds night-study runs nested one or two levels down (``runs/night31_*/<id>/``)."""
    root = Path(root)
    found: list[Path] = []

    def walk(d: Path, depth: int) -> None:
        if (d / "config.yaml").is_file() and (d / "designs").is_dir():
            found.append(d)
            return
        if depth >= max_depth:
            return
        try:
            kids = sorted(p for p in d.iterdir() if p.is_dir() and p.name not in ("designs", "verify", "cma"))
        except OSError:
            return
        for k in kids:
            walk(k, depth + 1)

    walk(root, 0)
    return found


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("rescore", "floor"):
        p = sub.add_parser(name)
        p.add_argument("runs", nargs="*", type=Path)
        p.add_argument("--runs-root", type=Path, default=None,
                       help="also take every run dir found under this folder (depth <= 3)")
        p.add_argument("--brief", required=True)
        p.add_argument("--out", type=Path, required=True)
        if name == "floor":
            p.add_argument("--top", type=int, default=28)
        else:
            p.add_argument("--run-brief", default=None,
                           help="keep only runs whose config brief_file has this stem")
    p = sub.add_parser("compare")
    p.add_argument("columns", nargs="+", help="label=<rescore --out dir>")
    p.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd != "compare":
        if a.runs_root is not None:
            a.runs = list(a.runs) + discover_runs(a.runs_root)
        if not a.runs:
            ap.error("give run dirs and/or --runs-root")
    if a.cmd == "compare":
        res = compare(dict(c.split("=", 1) for c in a.columns), a.out)
    elif a.cmd == "rescore":
        res = rescore(a.runs, a.brief, a.out, a.run_brief)
    else:
        res = floor(a.runs, a.brief, a.out, a.top)
    print(json.dumps(res, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
