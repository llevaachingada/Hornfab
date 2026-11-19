"""Archive finished run directories under docs/evidence/runs for cloud/GitHub review.

Copies the scoring evidence, not the whole runs tree:

  <run>/run.json, config.yaml, best.json, search.ndjson
  <run>/scores.csv                     flattened per-eval score table (terms + metric arrays)
  <run>/summary.json                   config identity, seed, searched bounds, best, warm start
  <run>/designs/<best>/{design.json, metrics.json, mesh_meta.json, status.json, mesh.msh, response.npz}

``mesh.msh``/``response.npz`` are gitignored in ``runs/`` but are force-added here by the caller
(``git add -f``); this tool only writes the files. Idempotent: re-running refreshes a run.

    .venv\\Scripts\\python.exe tools/analysis/archive_run.py --out docs/evidence/runs/<bundle> runs/<id> ...
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

BEST_FILES = ("design.json", "metrics.json", "mesh_meta.json", "status.json", "mesh.msh", "response.npz")
RUN_FILES = ("run.json", "config.yaml", "best.json", "search.ndjson")


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _rows(path: Path) -> list[dict]:
    out = []
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _cell(value):
    if isinstance(value, (list, tuple)):
        return ";".join("" if v is None else repr(v) if isinstance(v, float) else str(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return value


def write_scores_csv(rows: list[dict], path: Path) -> None:
    terms = sorted({k for r in rows for k in (r.get("terms") or {})})
    sc = sorted({k for r in rows for k in ((r.get("metrics") or {}).get("scalars") or {})})
    arrays = ("freqs_hz", "bw_h_deg", "bw_v_deg", "di_db", "ripple_h_db", "ripple_v_db",
              "on_axis_db", "z_throat_real")
    cols = ["n", "design_hash", "ok", "objective", "objective_version", "family", "lane", "backend",
            "error", "n_dof", "n_triangles", "created_utc"] + [f"term_{t}" for t in terms] + \
           [f"scalar_{s}" for s in sc] + list(arrays)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            m = r.get("metrics") or {}
            sca = m.get("scalars") or {}
            line = {c: r.get(c) for c in ("n", "design_hash", "ok", "objective", "objective_version",
                                          "family", "lane", "backend", "error", "n_dof",
                                          "n_triangles", "created_utc")}
            line.update({f"term_{k}": (r.get("terms") or {}).get(k) for k in terms})
            line.update({f"scalar_{k}": sca.get(k) for k in sc})
            line.update({k: _cell(m.get(k)) for k in arrays})
            w.writerow(line)


def summarize(run: Path, rows: list[dict]) -> dict:
    cfg = yaml.safe_load((run / "config.yaml").read_text(encoding="utf-8")) if (run / "config.yaml").is_file() else {}
    rj = _read_json(run / "run.json") or {}
    best = _read_json(run / "best.json") or {}
    valid = [r for r in rows if r.get("ok")]
    b = min(valid, key=lambda r: r["objective"]) if valid else None
    return {
        "run": run.name,
        "config_name": cfg.get("name") or rj.get("config_name"),
        "family": cfg.get("family"),
        "objective_version": rj.get("objective_version"),
        "brief_file": cfg.get("brief_file") or rj.get("brief_file"),
        "seed_params": cfg.get("seed_params"),
        "bounds": {k: v for k, v in (cfg.get("bounds") or {}).items()
                   if not isinstance(v, dict) or v.get("search", True)},
        "search": {k: v for k, v in (cfg.get("search") or {}).items() if k != "warm_start"},
        "warm_start_config": (cfg.get("search") or {}).get("warm_start"),
        "warm_start_run": rj.get("warm_start"),
        "rows": len(rows),
        "valid": len(valid),
        "best_n": None if b is None else b.get("n"),
        "best_J": None if b is None else b.get("objective"),
        "best_design_hash": None if b is None else b.get("design_hash"),
        "best_json_hash": best.get("design_hash"),
    }


def archive(run: Path, out_root: Path) -> dict:
    dest = out_root / run.name
    dest.mkdir(parents=True, exist_ok=True)
    missing = []
    for name in RUN_FILES:
        src = run / name
        if src.is_file():
            shutil.copy2(src, dest / name)
        elif name != "best.json":
            missing.append(name)
    rows = _rows(run / "search.ndjson")
    if rows:
        write_scores_csv(rows, dest / "scores.csv")
    summary = summarize(run, rows)
    summary["missing"] = missing
    best_hash = summary.get("best_design_hash") or summary.get("best_json_hash")
    if best_hash:
        src_dir = run / "designs" / best_hash
        if src_dir.is_dir():
            dd = dest / "designs" / best_hash
            dd.mkdir(parents=True, exist_ok=True)
            for name in BEST_FILES:
                if (src_dir / name).is_file():
                    shutil.copy2(src_dir / name, dd / name)
        else:
            summary["missing"].append(f"designs/{best_hash}")
    (dest / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("runs", type=Path, nargs="+")
    a = ap.parse_args(argv)
    out_root = a.out if a.out.is_absolute() else ROOT / a.out
    out_root.mkdir(parents=True, exist_ok=True)
    index = []
    for run in a.runs:
        run = run if run.is_absolute() else ROOT / run
        if not run.is_dir():
            print(f"skip (not a dir): {run}")
            continue
        s = archive(run, out_root)
        index.append(s)
        print(f"{run.name}: best J {s['best_J']} hash {s['best_design_hash']} rows {s['rows']} "
              f"valid {s['valid']} missing {s['missing']}")
    (out_root / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"wrote {len(index)} run summaries to {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
