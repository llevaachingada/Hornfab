"""R4: seed spread versus config gaps. Read-only. Writes SEED_SPREAD.md."""
from __future__ import annotations

import collections
import copy
import json
import pathlib
import re
import subprocess
import sys
import time

import numpy as np
import yaml

sys.path.insert(0, r"C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp")
import fable_replay_harness as H

REPO = H.REPO
OUT = REPO / "scratch" / "fable_architecture" / "SEED_SPREAD.md"
NIGHTS = REPO / "runs" / "nights"


def head_sha():
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def normalized(cfg):
    d = copy.deepcopy(cfg)
    for k in ("name", "description", "brief_file", "feasibility"):
        d.pop(k, None)
    se = d.get("search") or {}
    se.pop("seed", None)
    d["search"] = se
    d.pop("seed_params", None)
    return json.dumps(d, sort_keys=True)


def valid_rows(rows):
    return [r for r in rows
            if r.get("ok") and isinstance(r.get("objective"), (int, float))
            and np.isfinite(float(r["objective"])) and float(r["objective"]) < 900.0]


def run_meta(rd):
    p = rd / "run.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def parse_logs():
    """job id -> (status, evals, log file); plus queue YAML argv by job id."""
    jobs = {}
    for log in sorted(NIGHTS.glob("*_runner_stdout.log")):
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\[([^\]]+)\]\s+exit=(\d+)\s+evals=(\d+)\s+.*?status=(\w+)", line)
            if m:
                jobs[m.group(1)] = dict(status=m.group(4), exit=int(m.group(2)),
                                        evals=int(m.group(3)), log=log.name, raw=line.strip())
    argvs = {}
    for q in sorted(NIGHTS.glob("*.yaml")):
        try:
            doc = yaml.safe_load(q.read_text(encoding="utf-8"))
        except Exception:
            continue
        for job in (doc or {}).get("jobs") or []:
            if isinstance(job, dict) and job.get("id"):
                argvs[job["id"]] = dict(argv=job.get("argv") or [], queue=q.name)
    return jobs, argvs


def map_job_to_run(job_id, info, argvs, runs_by_meta):
    argv = (argvs.get(job_id) or {}).get("argv") or []
    text = " ".join(str(x) for x in argv)
    m = re.search(r"--resume\s+(runs[\\/][^\s]+)", text)
    if m:
        rid = pathlib.Path(m.group(1)).name
        if (REPO / "runs" / rid).is_dir():
            return rid, f"resume path in {argvs.get(job_id, {}).get('queue', '?')}"
    cm = re.search(r"--config\s+([^\s]+)", text)
    sm = re.search(r"--cma-seed\s+(\d+)", text)
    if cm and sm:
        cfg = cm.group(1).replace("\\", "/")
        seed = int(sm.group(1))
        hits = [rid for (rid, meta) in runs_by_meta.items()
                if str(meta.get("config_path") or "").replace("\\", "/") == cfg
                and meta.get("cma_seed") == seed]
        if len(hits) == 1:
            return hits[0], "config path + cma seed"
        if len(hits) > 1:
            # prefer a run whose row count matches the log's evals (new run, not resume)
            exact = [rid for rid in hits if len(valid_rows(_load_rows(REPO / "runs" / rid))) == info["evals"]]
            if len(exact) == 1:
                return exact[0], "config path + cma seed + evals count"
            return None, f"ambiguous ({len(hits)} runs)"
    return None, "no resume path and no config+seed match"


def _load_rows(rd):
    p = rd / "search.ndjson"
    out = []
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def main():
    t0 = time.time()
    sha = head_sha()
    runs = H.load_landscape_runs()
    groups = collections.defaultdict(list)
    for r in runs:
        groups[normalized(r["cfg"])].append(r)
    qual = [rs for rs in groups.values() if len(rs) >= 3]
    qual.sort(key=lambda rs: -len(rs))

    runs_by_meta = {r["dir"].name: run_meta(r["dir"]) for r in runs}
    job_info, argvs = parse_logs()
    flagged = {}
    mapping_notes = []
    for job_id, info in job_info.items():
        if info["status"] not in ("watchdog", "failed"):
            continue
        rid, why = map_job_to_run(job_id, info, argvs, runs_by_meta)
        if rid:
            flagged.setdefault(rid, []).append(dict(job=job_id, **info, why=why))
        else:
            mapping_notes.append(f"`{job_id}` {info['status']} evals={info['evals']}: {why}")

    lines = []
    lines.append("# SEED_SPREAD")
    lines.append("")
    lines.append(f"- Repo HEAD at run: `{sha}`")
    lines.append(f"- Timestamp: `{time.strftime('%Y-%m-%dT%H:%M:%S%z')}`")
    lines.append("- Read-only against `runs/`; no solve, mesher, GPU, queue or config write.")
    lines.append(f"- Scope: the same {len(runs)} landscape-brief runs. Normalised config = all keys except "
                 "`name`, `description`, `brief_file`, `feasibility`, `search.seed` and `seed_params`.")
    lines.append(f"- Configs with at least three runs: **{len(qual)}**. "
                 + ("Proceeding (>=4)." if len(qual) >= 4 else "FEWER THAN FOUR: report and stop."))
    lines.append("- Valid row = `ok`, finite numeric `objective`, and `objective < 900` (penalty excluded). "
                 "Matched budget N = the smallest valid-row count in the config; each run uses its first N "
                 "valid rows in `search.ndjson` order.")
    lines.append("")
    if len(qual) < 4:
        lines.append("Fewer than four configs qualify under the stated rule. Stop; no spread ratio is reported.")
        OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("fewer than four configs qualify:", len(qual))
        return

    all_rows = []
    config_summary = []
    for rs in qual:
        name = str(rs[0]["cfg"].get("name"))
        per_run = []
        for r in rs:
            vr = valid_rows(r["rows"])
            per_run.append((r, vr))
        n = min(len(vr) for _, vr in per_run)
        for r, vr in per_run:
            first = vr[:n]
            best = min(first, key=lambda x: float(x["objective"]))
            per_run_entry = dict(config=name, run=r["dir"].name,
                                 seed=(r["cfg"].get("search") or {}).get("seed"),
                                 start=json.dumps(r["cfg"].get("seed_params") or {}, sort_keys=True),
                                 available=len(vr), matched=n,
                                 best_j=float(best["objective"]), best_n=best.get("n"),
                                 design=best.get("design_hash"),
                                 watchdog=bool(flagged.get(r["dir"].name)))
            all_rows.append(per_run_entry)
        bests = [x["best_j"] for x in all_rows[-len(per_run):]]
        spread = max(bests) - min(bests)
        config_summary.append(dict(config=name, n_runs=len(per_run), matched=n,
                                   best=min(bests), median=float(np.median(bests)),
                                   spread=spread, sd=float(np.std(bests, ddof=1)) if len(bests) > 1 else 0.0,
                                   flagged=sum(1 for x in all_rows[-len(per_run):] if x["watchdog"])))

    config_summary.sort(key=lambda c: c["best"])
    gaps = [config_summary[i + 1]["best"] - config_summary[i]["best"]
            for i in range(len(config_summary) - 1)]
    spreads = [c["spread"] for c in config_summary]
    num, den = float(np.median(spreads)), float(np.median(gaps)) if gaps else float("nan")
    ratio = num / den if den and np.isfinite(den) else float("nan")

    lines.append("## Per-run table")
    lines.append("")
    lines.append("| config | run | seed | start (seed_params) | valid rows | matched N | best J at N | best row | watchdog |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for x in all_rows:
        start = x["start"]
        if start in ("{}", ""):
            start = "—"
        elif len(start) > 60:
            start = start[:57] + "…"
        else:
            start = start.replace("|", "/")
        lines.append(f"| `{x['config']}` | `{x['run']}` | {x['seed']} | `{start}` | {x['available']} | "
                     f"{x['matched']} | {x['best_j']:.3f} | #{x['best_n']} `{x['design']}` | "
                     f"{'YES' if x['watchdog'] else 'no'} |")
    lines.append("")
    lines.append("## Config spread and ranking gaps")
    lines.append("")
    lines.append("| rank | config | runs | matched N | best J | median J | within spread | sd | watchdog runs |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(config_summary, 1):
        lines.append(f"| {i} | `{c['config']}` | {c['n_runs']} | {c['matched']} | {c['best']:.3f} | "
                     f"{c['median']:.3f} | {c['spread']:.3f} | {c['sd']:.3f} | {c['flagged']}/{c['n_runs']} |")
    lines.append("")
    lines.append("Adjacent gaps (rank order, best J): "
                 + ", ".join(f"{g:.3f}" for g in gaps) + ".")
    lines.append("")
    lines.append(f"**Ratio: median within-config spread / median adjacent gap = {num:.3f} / {den:.3f} = "
                 f"{ratio:.3f}.**" if np.isfinite(ratio) else
                 f"**Ratio undefined: median spread {num:.3f}, median gap {den:.3f}.**")
    lines.append("")
    lines.append("## Watchdog mapping")
    lines.append("")
    for rid, hits in sorted(flagged.items()):
        for h in hits:
            lines.append(f"- `{rid}`: {h['status']} `{h['job']}` evals={h['evals']} "
                         f"({h['log']}) — mapped by {h['why']}.")
    if mapping_notes:
        lines.append("")
        lines.append("Unmapped log entries (not attributed to a run):")
        for note in mapping_notes:
            lines.append(f"- {note}")
    lines.append("")
    lines.append(f"_Script: `scratch/fable_architecture/.tmp/r4_seed_spread.py`; runtime {time.time()-t0:.1f}s._")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("configs", len(qual), "runs", sum(len(rs) for rs in qual))
    for c in config_summary:
        print(f"{c['config'][:44]:44s} n={c['n_runs']} N={c['matched']} best={c['best']:.3f} "
              f"spread={c['spread']:.3f} flagged={c['flagged']}")
    print("gaps", [round(g, 3) for g in gaps])
    print("ratio %.3f = %.3f / %.3f" % (ratio, num, den))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
