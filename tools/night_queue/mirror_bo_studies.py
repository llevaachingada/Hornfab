"""Mirror BO/TuRBO study solves into ordinary run folders so every CMA view shows them.

A BO study writes its solves to ``runs/study-<package16>/{screen,verify}/`` with exactly the files a
CMA search writes (``search.ndjson``, ``config.yaml``, ``run.json``, ``designs/<hash>/...``), but one
folder deeper and under a name the GUI's run list does not match. This tool makes, per study, a
folder ``runs/<started>-<policy>-<package6>/`` (``<policy>`` = ``turbo``, ``scalar``, ``pareto``...)
whose files are HARD LINKS to the study's files (no copy, no extra disk), plus three small files of
its own:

* ``run.json``  - the study's screen ``run.json`` plus ``algorithm``, ``bo_seed``, ``source_study``
  and a ``command`` line, so the run page shows the policy and seed;
* ``best.json`` - the best valid screen row, in the CMA ``best.json`` shape;
* ``bo_mirror.json`` - provenance: study folder, arm folder, policy, linked file count.

The study's verify tier is linked to ``<mirror>/verify/`` (where a CMA run keeps its verify
re-solves), so the verify view works too. Nothing in the study folder is changed. BoTorch training
data comes from the dataset shards, not run folders, so a mirror cannot double-count rows.

Idempotent: re-running adds designs solved since the last pass and re-links a file a writer
replaced. ``--prune`` removes mirrors whose study folder is gone.

Usage (repo root)::

    .venv\\Scripts\\python.exe tools\\night_queue\\mirror_bo_studies.py            # all studies
    .venv\\Scripts\\python.exe tools\\night_queue\\mirror_bo_studies.py --dry-run
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STUDY_DIR = re.compile(r"^study-([0-9a-f]{16})$")
MIRROR_DIR = re.compile(r"^[0-9]{8}T[0-9]{6}Z-([a-z]+)-([0-9a-f]{6})$")
MARKER = "bo_mirror.json"
POLICY_NAME = re.compile(r"[^a-z]")


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _first_json_line(path: Path):
    try:
        with path.open(encoding="utf-8") as fh:
            return json.loads(fh.readline())
    except (OSError, ValueError):
        return None


def _read_ndjson(path: Path) -> list[dict]:
    rows = []
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        continue
    except OSError:
        pass
    return rows


def arm_index(runs: Path) -> dict[str, dict]:
    """``package_id[:16] -> {policy, seed, arm_dir, budget}`` from every arm's package.json + study DB."""
    out: dict[str, dict] = {}
    for pkg in sorted(runs.glob("*/*/package.json")):
        head = _first_json_line(pkg)
        if not isinstance(head, dict) or not isinstance(head.get("package_id"), str):
            continue
        info = {"arm_dir": pkg.parent, "policy": None, "seed": None,
                "budget": (head.get("budget") or {}).get("screen_calls")}
        db = pkg.parent / "studies.sqlite3"
        if db.is_file():
            try:
                con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
                try:
                    row = con.execute("select spec_json from revisions order by revision desc limit 1").fetchone()
                finally:
                    con.close()
                spec = json.loads(row[0]) if row else {}
                pol = spec.get("policy") if isinstance(spec.get("policy"), dict) else {}
                info["policy"] = pol.get("proposal_policy")
                info["seed"] = pol.get("seed")
            except (sqlite3.Error, ValueError, TypeError):
                pass
        out[head["package_id"][:16]] = info
    return out


def _stamp(started: str | None, fallback: Path) -> str:
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            t = dt.datetime.strptime(str(started), fmt)
            if t.tzinfo is not None:
                t = t.astimezone(dt.timezone.utc)
            return t.strftime("%Y%m%dT%H%M%SZ")
        except (TypeError, ValueError):
            continue
    return dt.datetime.fromtimestamp(fallback.stat().st_mtime, dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _policy_tag(policy) -> str:
    tag = POLICY_NAME.sub("", str(policy or "bo").lower())
    return tag or "bo"


def _link_tree(src: Path, dst: Path, skip: set[str], dry: bool) -> int:
    """Hard-link every file under ``src`` into ``dst`` (same relative path); returns files (re)linked."""
    n = 0
    for f in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = f.relative_to(src)
        if rel.as_posix() in skip:
            continue
        t = dst / rel
        if t.exists():
            try:
                if os.path.samefile(f, t):
                    continue
            except OSError:
                pass
            if not dry:
                t.unlink()
        if not dry:
            t.parent.mkdir(parents=True, exist_ok=True)
            os.link(f, t)
        n += 1
    return n


def _best_row(rows: list[dict]) -> dict | None:
    ok = [r for r in rows if r.get("ok") and isinstance(r.get("objective"), (int, float))]
    return min(ok, key=lambda r: r["objective"]) if ok else None


def mirror_one(study: Path, runs: Path, arms: dict[str, dict], dry: bool = False) -> dict | None:
    m = STUDY_DIR.match(study.name)
    screen = study / "screen"
    if not m or not (screen / "search.ndjson").is_file():
        return None
    key = m.group(1)
    arm = arms.get(key, {})
    srj = _read_json(screen / "run.json") or {}
    policy = arm.get("policy")
    tag = _policy_tag(policy)
    name = f"{_stamp(srj.get('started_utc'), screen / 'search.ndjson')}-{tag}-{key[:6]}"
    # an older mirror of the same study under another name (e.g. policy learned later) is renamed
    existing = [p for p in runs.iterdir() if p.is_dir() and MIRROR_DIR.match(p.name)
                and MIRROR_DIR.match(p.name).group(2) == key[:6]
                and (_read_json(p / MARKER) or {}).get("study") == study.name]
    dst = runs / name
    if existing and existing[0] != dst and not dry:
        existing[0].rename(dst)
    linked = 0
    own = {"run.json", "best.json", MARKER}
    linked += _link_tree(screen, dst, own, dry)
    if (study / "verify" / "search.ndjson").is_file():
        linked += _link_tree(study / "verify", dst / "verify", set(), dry)
    rows = _read_ndjson(screen / "search.ndjson")
    best = _best_row(rows)
    seed = arm.get("seed")
    budget = arm.get("budget") or len(rows)
    rj = dict(srj)
    rj.update({
        "algorithm": tag,
        "bo_seed": seed,
        "source_study": study.relative_to(runs.parent).as_posix() if runs.parent in study.parents else str(study),
        "command": f"bo-study --policy {tag} --budget {budget}" + (f" --cma-seed {seed}" if seed is not None else ""),
    })
    marker = {
        "schema": "bo-mirror-v1",
        "study": study.name,
        "study_dir": str(study),
        "arm_dir": str(arm["arm_dir"]) if arm.get("arm_dir") else None,
        "policy": policy,
        "seed": seed,
        "package_prefix": key,
        "rows": len(rows),
        "note": "files are hard links to the study folder; regenerate with tools/night_queue/mirror_bo_studies.py",
    }
    if not dry:
        dst.mkdir(parents=True, exist_ok=True)
        (dst / "run.json").write_text(json.dumps(rj, indent=1, sort_keys=True), encoding="utf-8")
        if best is not None:
            b = {k: best.get(k) for k in ("design_hash", "family", "mode", "objective", "ok", "params", "terms",
                                          "objective_version")}
            b["eval_no"] = best.get("n")
            b["di_source"] = (best.get("metrics") or {}).get("di_source") if isinstance(best.get("metrics"), dict) else None
            (dst / "best.json").write_text(json.dumps(b, indent=1, sort_keys=True), encoding="utf-8")
        (dst / MARKER).write_text(json.dumps(marker, indent=1, sort_keys=True), encoding="utf-8")
    return {"mirror": name, "study": study.name, "policy": policy, "seed": seed, "rows": len(rows),
            "best_j": best["objective"] if best else None, "linked": linked}


def prune(runs: Path, dry: bool = False) -> list[str]:
    gone = []
    for p in runs.iterdir():
        if p.is_dir() and MIRROR_DIR.match(p.name) and (p / MARKER).is_file():
            mk = _read_json(p / MARKER) or {}
            if not (runs / str(mk.get("study", ""))).is_dir():
                gone.append(p.name)
                if not dry:
                    shutil.rmtree(p)
    return gone


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", default=str(REPO / "runs"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--prune", action="store_true", help="remove mirrors whose study folder is gone")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    runs = Path(a.runs)
    arms = arm_index(runs)
    out = [r for s in sorted(runs.glob("study-*")) if s.is_dir()
           for r in [mirror_one(s, runs, arms, a.dry_run)] if r]
    pruned = prune(runs, a.dry_run) if a.prune else []
    if a.json:
        print(json.dumps({"mirrors": out, "pruned": pruned}, indent=1))
    else:
        for r in out:
            bj = f"{r['best_j']:.4f}" if r["best_j"] is not None else "-"
            print(f"{r['mirror']}  <- {r['study']}  policy={r['policy']} seed={r['seed']} rows={r['rows']} "
                  f"best={bj} linked={r['linked']}")
        for p in pruned:
            print(f"pruned {p}")
        print(f"{len(out)} study mirror(s){' (dry run)' if a.dry_run else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
