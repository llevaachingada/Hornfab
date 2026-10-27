"""Read-only observer for an overnight campaign night.

    .venv\\Scripts\\python.exe tools\\observe_run.py --night smoke_2026-10-27

Samples GPU / CPU / phase once per ``--interval`` seconds and appends one JSON line per sample to
``runs/nights/<night>/observe.ndjson``; on exit it writes ``observe_summary.md`` with the phase
split, the utilisation histogram and the throughput (valid evaluations per hour). The point is to
answer, from a real run: how much of the wall clock the GPU was idle, which phase was running
then, and what a plausible speed-up is.

It is strictly read-only about the run: ``nvidia-smi`` queries, ``psutil`` counters, and reads of
``summary.jsonl`` / the newest job log / the newest ``search.ndjson``. It never launches a solver,
never writes into a run directory, and costs a few milliseconds per sample.

Exit: when ``summary.jsonl`` holds one line per job in the night YAML, or ``--max-hours`` elapses.
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]

GPU_QUERY = ("utilization.gpu,memory.used,memory.total,power.draw,temperature.gpu,clocks.sm"
             ",clocks.max.sm")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gpu_sample() -> dict:
    try:
        out = subprocess.run(
            ["nvidia-smi", f"--query-gpu={GPU_QUERY}", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10).stdout.strip().splitlines()
    except Exception:  # noqa: BLE001
        return {}
    if not out:
        return {}
    parts = [p.strip() for p in out[0].split(",")]

    def num(i, cast=float):
        try:
            return cast(float(parts[i]))
        except (ValueError, IndexError):
            return None

    return {"gpu_util": num(0, int), "vram_used_mb": num(1), "vram_total_mb": num(2),
            "power_w": num(3), "temp_c": num(4), "sm_clock": num(5), "sm_clock_max": num(6)}


def night_job_ids(night_yaml: Path) -> list[str]:
    try:
        import yaml
        doc = yaml.safe_load(night_yaml.read_text(encoding="utf-8")) or {}
        return [str(j.get("id")) for j in (doc.get("jobs") or []) if isinstance(j, dict)]
    except Exception:  # noqa: BLE001
        return []


def newest_job_log(night_dir: Path) -> tuple[str | None, float | None]:
    logs = [p for p in night_dir.glob("*.log")
            if not p.name.startswith(("runner_", "observe"))]
    if not logs:
        return None, None
    p = max(logs, key=lambda q: q.stat().st_mtime)
    return p.stem, round(time.time() - p.stat().st_mtime, 1)


def newest_run() -> dict:
    """The most recently touched search run dir under runs/ (read-only)."""
    best = None
    for d in ROOT.joinpath("runs").glob("20*"):
        nd = d / "search.ndjson"
        if not nd.exists():
            continue
        m = nd.stat().st_mtime
        if best is None or m > best[0]:
            best = (m, d, nd)
    if best is None:
        return {}
    _, d, nd = best
    rows = 0
    last = {}
    try:
        with open(nd, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rows += 1
                try:
                    last = json.loads(line)
                except json.JSONDecodeError:
                    pass
    except OSError:
        return {}
    sec = last.get("seconds") or {}
    return {"run": d.name, "evals": rows,
            "last_ok": last.get("ok"), "last_kind": last.get("kind"),
            "last_mesh_s": sec.get("mesh"), "last_solve_s": sec.get("solve"),
            "last_dofs": last.get("n_dof"),
            "run_age_s": round(time.time() - nd.stat().st_mtime, 1)}


def cpu_sample(first: bool) -> dict:
    total = psutil.cpu_percent(interval=None, percpu=False)
    procs = {}
    for p in psutil.process_iter(["name", "cpu_percent"]):
        try:
            n = (p.info.get("name") or "").lower()
            if n in ("python.exe", "julia.exe", "hornlab-search.exe"):
                procs[n] = round(procs.get(n, 0.0) + (p.info.get("cpu_percent") or 0.0), 1)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return {"cpu_pct": round(total, 1) if not first else None, **procs}


def phase(s: dict) -> str:
    util = s.get("gpu_util")
    if util is None:
        return "unknown"
    if util >= 60:
        return "gpu_solve"
    if s.get("last_ok") is False and (s.get("run_age_s") or 0) < 30:
        return "refusal_or_mesh"
    if (s.get("last_solve_s") or 0) > 0 and (s.get("run_age_s") or 0) < 20:
        return "between_evals"
    return "cpu_idle"


def summarise(path: Path, out: Path, job_total: int) -> None:
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    if not rows:
        return
    interval = rows[0].get("interval_s") or 5.0
    by_phase: dict[str, int] = {}
    for r in rows:
        by_phase[r.get("phase", "?")] = by_phase.get(r.get("phase", "?"), 0) + 1
    utils = [r["gpu_util"] for r in rows if r.get("gpu_util") is not None]
    vram = [r["vram_used_mb"] for r in rows if r.get("vram_used_mb") is not None]
    powers = [r["power_w"] for r in rows if r.get("power_w") is not None]
    hist = {f"{lo}-{lo + 20}%": sum(1 for u in utils if lo <= u < lo + 20)
            for lo in range(0, 100, 20)}
    evals = [r["evals"] for r in rows if r.get("evals")]
    span_h = len(rows) * interval / 3600.0
    lines = [
        f"# Observer summary - {rows[0].get('night')}",
        "",
        f"- samples: {len(rows)} every {interval:g} s  (~{span_h:.2f} h); "
        f"jobs completed: {max((r.get('summary_count') or 0) for r in rows)}/{job_total}",
        f"- **GPU utilisation**: median {statistics.median(utils) if utils else float('nan'):.0f} %, "
        f"mean {statistics.fmean(utils) if utils else float('nan'):.0f} %, "
        f"max {max(utils) if utils else 0} %",
        f"- histogram: " + ", ".join(f"{k} {v}" for k, v in hist.items()),
        f"- **time by phase** (sampled): " + ", ".join(
            f"{k} {v / len(rows):.0%}" for k, v in sorted(by_phase.items(), key=lambda kv: -kv[1])),
        f"- VRAM used: median {statistics.median(vram) if vram else 0:.0f} MiB, "
        f"max {max(vram) if vram else 0:.0f} MiB of "
        f"{max((r.get('vram_total_mb') or 0) for r in rows):.0f} MiB",
        f"- power: median {statistics.median(powers) if powers else 0:.0f} W, "
        f"max {max(powers) if powers else 0:.0f} W",
        "",
        "Reading it: `gpu_solve` is the only phase that needs the card. Every other phase is "
        "CPU-side work the GPU waits on, so `1 / gpu_solve_share` is the ceiling a CPU/GPU "
        "pipeline could reach without touching accuracy.",
        "",
        f"Raw samples: `{path.relative_to(ROOT)}`",
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=((__doc__ or "").splitlines() or ["observe an overnight campaign night"])[0])
    ap.add_argument("--night", required=True)
    ap.add_argument("--interval", type=float, default=5.0)
    ap.add_argument("--max-hours", type=float, default=12.0)
    a = ap.parse_args(argv)

    night_dir = ROOT / "runs" / "nights" / a.night
    night_yaml = night_dir.with_suffix(".yaml")
    if not night_yaml.exists():
        print(f"observe_run: no night file at {night_yaml}", file=sys.stderr)
        return 2
    night_dir.mkdir(parents=True, exist_ok=True)
    out_nd = night_dir / "observe.ndjson"
    job_ids = night_job_ids(night_yaml)
    total = len(job_ids)
    started = time.time()
    first = True
    print(f"observing {a.night}: {total} job(s), every {a.interval:g} s -> {out_nd}")

    while True:
        summary_path = night_dir / "summary.jsonl"
        count = 0
        if summary_path.exists():
            count = sum(1 for line in summary_path.read_text(encoding="utf-8").splitlines()
                        if line.strip())
        job, age = newest_job_log(night_dir)
        sample = {"t": _utc(), "night": a.night, "interval_s": a.interval,
                  "summary_count": count, "job": job, "job_log_age_s": age,
                  **gpu_sample(), **cpu_sample(first), **newest_run()}
        sample["phase"] = phase(sample)
        with open(out_nd, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(sample, ensure_ascii=False) + "\n")
        first = False
        if total and count >= total:
            break
        if (time.time() - started) / 3600.0 >= a.max_hours:
            break
        time.sleep(a.interval)

    summarise(out_nd, night_dir / "observe_summary.md", total)
    print(f"done; summary in {night_dir / 'observe_summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
