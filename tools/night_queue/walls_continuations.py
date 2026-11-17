"""Generate walls-relieved successor configs + queue jobs for recent runs that hit bound walls.

For each recent run with enough attempts, grouped by config name (best run of each family):
  1. ``tools/analysis/walls.py`` runs on that family's best run;
  2. every ``widen_hi`` / ``widen_lo`` proposal is applied to a COPY of the family's config
     (seed_params = the family's best knobs; bounds widened exactly per the proposal);
     zero-low proposals are NOT widened past zero automatically (kernel-legal negatives exist
     for some families, e.g. rim_sweep; handle those by hand and note them),
  3. the successor config is validated by the same search-preflight path as the parent CLI,
  4. a queue job (budget 200 valid, fresh CMA seed, same CLI as the parent command) is appended
     to the night file alongside its BO follow-up pair when the family row budget allows.

Nothing here narrows a box and nothing touches a running job; configs are written under
``examples/typologies/walls_relieved/<config-stem>/`` and jobs appended only after their config
preflights clean.
Usage:
  .venv\\Scripts\\python.exe tools/night_queue/walls_continuations.py --night cd_rrect_2026-11-17 \
      [--min-rows 30] [--days 3] [--max-items 12] [--samples 8] [--dry]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SEEDS = iter([41351 + i for i in range(200)])


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_rows(run_dir: Path) -> int:
    nd = run_dir / "search.ndjson"
    if not nd.is_file():
        return 0
    return sum(1 for _ in nd.read_text(encoding="utf-8", errors="replace").splitlines())


def _best_knobs(run_dir: Path, base: dict) -> dict | None:
    best = run_dir / "best.json"
    if not best.is_file():
        return None
    try:
        knobs = json.loads(best.read_text(encoding="utf-8"))["params"]["grid"]["knobs"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return None
    return {k: v for k, v in knobs.items()}


def _parent_cmd(run_dir: Path) -> list | None:
    rj_path = run_dir / "run.json"
    if not rj_path.is_file():
        return None
    try:
        cmd = json.loads(rj_path.read_text(encoding="utf-8")).get("command") or ""
    except json.JSONDecodeError:
        return None
    tokens = cmd.split()
    if not tokens:
        return None
    # normalise console-script forms: hornlab-search.exe search ... and python -m ... search
    if "search" in tokens:
        i = tokens.index("search")
        tokens = tokens[i:]
    return tokens


def _reseed(tokens: list, budget: str, seed: str, config_path: Path) -> list:
    out = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in ("--budget", "--cma-seed") and i + 1 < len(tokens):
            out.append(t)
            out.append(budget if t == "--budget" else seed)
            i += 2
            continue
        if t == "--config" and i + 1 < len(tokens):
            out += ["--config", str(config_path)]
            i += 2
            continue
        if t in ("--resume", "--allow-config-change"):
            i += 2 if t == "--resume" else 1
            continue
        if t == "--restarts-mode" and i + 1 < len(tokens):
            i += 2
            continue
        if t == "--brief" and i + 1 < len(tokens):
            out += [t, tokens[i + 1]]
            i += 2
            continue
        out.append(t)
        i += 1
    if "--budget" not in out:
        out += ["--budget", budget]
    if "--cma-seed" not in out:
        out += ["--cma-seed", seed]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--night", required=True)
    ap.add_argument("--min-rows", type=int, default=30)
    ap.add_argument("--days", type=float, default=3.0)
    ap.add_argument("--max-items", type=int, default=12)
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--budget", type=int, default=200)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)

    night_yaml = ROOT / "runs/nights" / f"{a.night}.yaml"
    plan = yaml.safe_load(night_yaml.read_text(encoding="utf-8"))
    queued_ids = {j["id"] for j in plan.get("jobs", [])}
    queued_cfg_text = yaml.safe_dump(plan)

    since = datetime.now(timezone.utc).timestamp() - a.days * 86400
    runs = []
    for d in (ROOT / "runs").glob("*screen*"):
        rj = d / "run.json"
        if not rj.is_file() or rj.stat().st_mtime < since:
            continue
        rows = _run_rows(d)
        if rows < a.min_rows:
            continue
        try:
            meta = json.loads(rj.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        runs.append({"dir": d, "rows": rows, "config": meta.get("config_name"),
                     "cfg_path": meta.get("config_path"), "mtime": rj.stat().st_mtime})
    hand_made = {"hl__klangfilm_lame_curved_v1_c200"}  # covered by hand-built c200w (sweep<-0, roll cap)
    by_cfg: dict[str, dict] = {}
    for r in runs:
        key = r["config"]
        if key not in by_cfg or r["mtime"] > by_cfg[key]["mtime"]:
            by_cfg[key] = r
    print(f"{len(runs)} recent runs -> {len(by_cfg)} distinct configs")

    out_root = ROOT / "examples/typologies/walls_relieved"
    added, report = [], []
    for key, r in sorted(by_cfg.items(), key=lambda kv: -kv[1]["rows"]):
        if len(added) >= a.max_items:
            break
        if key in hand_made:
            report.append(f"{key}: covered by the hand-built c200w queue job (adds negative sweep + roll cap); skipped")
            continue
        rid = f"{key.split('__', 1)[-1]}_w1"
        short = key.split("__", 1)[-1]
        base_cfg_path = ROOT / r["cfg_path"] if r["cfg_path"] and not Path(r["cfg_path"]).is_absolute() else ROOT / r["cfg_path"]
        if not base_cfg_path.is_file():
            report.append(f"{key}: parent config {r['cfg_path']} missing; skipped")
            continue
        if f"{short}_w1" in queued_cfg_text:
            report.append(f"{key}: walls job already queued; skipped")
            continue
        # walls analyse the family's best run
        wdir = ROOT / "scratch" / "walls_continuations" / short
        wdir.mkdir(parents=True, exist_ok=True)
        res = subprocess.run([sys.executable, "tools/analysis/walls.py", "--run", str(r["dir"]),
                              "--out", str(wdir)], cwd=ROOT, capture_output=True, text=True)
        if res.returncode:
            report.append(f"{key}: walls analysis failed ({res.stderr[-160:]}); skipped")
            continue
        walls, proposals = [], []
        wall_re = re.compile(r"^\|\s*`([^`]+)`\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|\s*(lo|hi)\s*\|")
        prop_re = re.compile(r"\*\*(widen_(?:lo|hi))\*\*\s*`([^`]+)`\s*->\s*\[([^,]+),\s*([^\]]+)\]")
        for md in wdir.glob("*.md"):
            for line in md.read_text(encoding="utf-8", errors="replace").splitlines():
                m = wall_re.match(line.strip())
                if m:
                    walls.append(f"{m.group(1)}@{m.group(6)}")
                pm = prop_re.search(line)
                if pm:
                    proposals.append((pm.group(1), pm.group(2), pm.group(3).strip(), pm.group(4).strip()))
        if not walls:
            report.append(f"{key}: no walls in top decile; skipped")
            continue
        # build the successor config
        cfg = yaml.safe_load(base_cfg_path.read_text(encoding="utf-8"))
        seed_knobs = _best_knobs(r["dir"], cfg)
        widened = []
        ok = True
        widened = []
        ok = True
        for kind, knob, new_lo, new_hi in proposals:
            b = cfg.get("bounds", {}).get(knob)
            if b is None or not isinstance(b, dict):
                ok = False
                report.append(f"{key}: proposal for unbounded knob {knob}; skipped")
                break
            if kind == "widen_lo":
                if not float(new_lo) < float(b.get("lo", new_lo)):
                    continue  # widening that lands inside the old bound is not a relief
                widened.append(f"{knob}.lo {b["lo"]} -> {new_lo}")
                b["lo"] = float(new_lo)
            else:
                if not float(new_hi) > float(b.get("hi", new_hi)):
                    continue
                widened.append(f"{knob}.hi {b["hi"]} -> {new_hi}")
                b["hi"] = float(new_hi)
        if not ok:
            continue
        if not ok:
            continue
        if seed_knobs:
            cfg.setdefault("seed_params", {}).update({k: v for k, v in seed_knobs.items()})
        cfg["name"] = f"{cfg['name']}_w1"
        cfg["search"] = {**cfg.get("search", {}), "budget": a.budget, "budget_counts": "valid",
                         "infeasible_penalty": "resample_strict", "max_attempts": 500,
                         "error_policy": "retry_same_then_stop"}
        succ_dir = out_root / short
        succ_dir.mkdir(parents=True, exist_ok=True)
        succ_path = succ_dir / f"{short}_w1.yaml"
        succ_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
        # preflight through the same path as the parent CLI's config loader
        pf = subprocess.run([sys.executable, "tools/search_preflight.py", str(succ_path)],
                            cwd=ROOT, capture_output=True, text=True)
        if "Result: HARD" in pf.stdout:
            succ_path.unlink(missing_ok=True)
            report.append(f"{key}: successor preflight HARD ({pf.stdout.splitlines()[-2:]}); skipped")
            continue
        seed = next(SEEDS)
        tokens = _reseed(_parent_cmd(r["dir"]) or [".venv/Scripts/hornlab-search.exe", "search"],
                         str(a.budget), str(seed), succ_path)
        rid_job = "w_" + short + "_200w1"
        job = {"id": rid_job, "kind": "command", "timeout_s": 18000, "watchdog": False, "argv": tokens}
        out_path = succ_path.relative_to(ROOT)
        report.append(f"{key}: job {rid_job} queued; walls: {'; '.join(walls) or 'near-walls only'}; "
                      f"widened: {'; '.join(widened)}")
        added.append(job)
    # de-dup against the night's queued ids and append
    appends = [j for j in added if j["id"] not in queued_ids]
    if appends and not a.dry:
        plan["jobs"].extend(appends)
        tmp = night_yaml.with_suffix(".yaml.tmp")
        tmp.write_text(yaml.safe_dump(plan, sort_keys=False, allow_unicode=True), encoding="utf-8")
        tmp.replace(night_yaml)
    stamp = _utc().replace(":", "").replace("-", "")
    outrep = ROOT / "runs/nights/refresh" / f"walls_{stamp}.md"
    outrep.parent.mkdir(parents=True, exist_ok=True)
    rep = ["# Walls-relieved continuations", "", f"- utc {_utc()}",
           f"- appended {len(appends) if not a.dry else 0} (proposed {len(added)})", "", "## Per-family", ""]
    rep += [f"- {r}" for r in report]
    outrep.write_text("\n".join(rep) + "\n", encoding="utf-8")
    (outrep.parent / "HANDOFF.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print(json.dumps({"appended": len(appends) if not a.dry else 0,
                      "proposed": len(added)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
