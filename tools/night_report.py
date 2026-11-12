"""Morning report for night jobs, straight from ``summary.jsonl`` + the run dirs (D.4).

Usage (repo root)::

    .venv\\Scripts\\python.exe tools/night_report.py --night gpu_day_2026-11-12 --night cpu_day_2026-11-12 \\
        --out docs/evidence/NIGHT_2026-11-12.md

Per lane, per night it tabulates [measured] numbers straight from the night's
``summary.jsonl``, job logs and run dirs: jobs, exits, evals, valid/refused rows, best J per
run, wall time, VRAM peaks, and every blocked/failed job with the first error line from its
job log. Derived ratios (evals/hour) are marked [inferred]. Nothing is solved here: the module
is read-only and offline. Rows pre-dating the two-lane runner (before 2026-11-12) have no
``lane``/``status`` fields; lane and status are then inferred and marked accordingly.

J is comparable only WITHIN a brief (each brief has its own target and weights), so best-J
columns are never ranked across runs.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_EXIT_TIMEOUT = 124
_ERROR_LINE_RE = re.compile(
    r"(Traceback|ERROR|Error:|EngineError|FATAL|FAILED|LAUNCH FAILED|TIMEOUT after|"
    r"GPU busy|exited with code)", re.IGNORECASE)
_PEAK_RE = re.compile(r"peak ([\d.]+) MiB")


# ------------------------------------------------------------------ row helpers


def read_jsonl(path: Path) -> list[dict]:
    out = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def latest_rows(rows: list[dict]) -> list[dict]:
    """One row per job id: the LAST summary row wins (a retried job appears twice, D.2a)."""
    latest: dict[str, dict] = {}
    for row in rows:
        job_id = str(row.get("id"))
        latest[job_id] = row
    return list(latest.values())


def lane_of(row: dict, night_name: str = "") -> str:
    """The row's lane: recorded, else inferred from the backend, else from the night name."""
    lane = row.get("lane")
    if lane in ("gpu", "cpu"):
        return str(lane)
    if row.get("backend") == "beat_cpu":
        return "cpu"
    name = night_name.lower()
    if name.startswith("cpu") or "_cpu" in name or "cpu_lane" in name:
        return "cpu"
    return "gpu"


def status_of(row: dict) -> tuple[str, str]:
    """``(status, label_kind)``: recorded status fields are [measured], inferred ones are not."""
    recorded = row.get("status")
    if isinstance(recorded, str) and recorded in ("ok", "blocked", "failed", "timeout"):
        return recorded, "measured"
    exit_code = int(row.get("exit_code") or 0)
    if exit_code == _EXIT_TIMEOUT:
        return "timeout", "inferred"
    if exit_code == 0:
        return "ok", "inferred"
    if "GPU busy" in str(row.get("note") or ""):
        return "blocked", "inferred"
    return "failed", "inferred"


def parse_peak_mb(note: str | None) -> float | None:
    match = _PEAK_RE.search(note or "")
    return float(match.group(1)) if match else None


# ------------------------------------------------------------------ run dirs / job logs


def _valid_refused(run_dir: str | None, repo_root: Path) -> tuple[int, int] | None:
    """``(valid, refused)`` from the run dir's ``search.ndjson``; None when there is none."""
    if not run_dir:
        return None
    ndjson = _resolve(run_dir, repo_root) / "search.ndjson"
    try:
        text = ndjson.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    valid = refused = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("ok") is True:
            valid += 1
        elif rec.get("ok") is False:
            refused += 1
    if valid == refused == 0:
        return None
    return valid, refused


def _resolve(path_text: str, repo_root: Path) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else Path(repo_root) / path


def first_error_line(night_dir: Path, job_id: str, *, max_chars: int = 160) -> str | None:
    """The first error-looking line of ``<id>.log`` (the log's own traceback text wins)."""
    log = night_dir / f"{job_id}.log"
    try:
        text = log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        if _ERROR_LINE_RE.search(line):
            return line.strip()[:max_chars]
    return None


# ------------------------------------------------------------------ report


def _fmt(value, spec: str = ".6g") -> str:
    return "n/a" if value is None else format(value, spec)


def night_section(night_dir: Path, night_name: str, repo_root: Path) -> list[str]:
    rows = read_jsonl(night_dir / "summary.jsonl")
    lines = [f"## Night `{night_name}`",
             "",
             f"[measured] rows: {len(rows)} summary row(s) in "
             f"`{(night_dir / 'summary.jsonl').relative_to(night_dir.parent.parent)}` "
             f"({night_dir})." if night_dir.is_absolute() else
             f"[measured] rows: {len(rows)} summary row(s) in {night_dir}.",
             ""]
    if not rows:
        lines.append("(no summary rows recorded)")
        return lines

    lanes: dict[str, list[dict]] = {}
    for row in latest_rows(rows):
        lanes.setdefault(lane_of(row, night_name), []).append(row)

    lines.append("| lane | id | kind | status | exit | attempts | evals | best J | "
                 "wall s | run dir | valid/refused |")
    lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---|---|")
    for lane in sorted(lanes):
        for row in lanes[lane]:
            vr = _valid_refused(row.get("run_dir"), repo_root)
            vr_text = "n/a" if vr is None else f"{vr[0]}/{vr[1]}"
            lines.append(
                f"| {lane} | `{row.get('id')}` | {row.get('kind', '?')} | "
                f"{status_of(row)[0]} | {row.get('exit_code')} | {row.get('attempts', 1)} | "
                f"{row.get('evals_ndjson', 0)} | {_fmt(row.get('best_J'))} | "
                f"{row.get('seconds', 0):.0f} | {row.get('run_dir') or 'n/a'} | {vr_text} |")

    for lane in sorted(lanes):
        lane_rows = lanes[lane]
        evals = sum(int(r.get("evals_ndjson") or 0) for r in lane_rows)
        wall_s = sum(float(r.get("seconds") or 0.0) for r in lane_rows)
        exits: dict[str, int] = {}
        for row in lane_rows:
            state = status_of(row)[0]
            exits[state] = exits.get(state, 0) + 1
        valid = refused = 0
        have_vr = False
        for row in lane_rows:
            vr = _valid_refused(row.get("run_dir"), repo_root)
            if vr is not None:
                valid += vr[0]
                refused += vr[1]
                have_vr = True
        peaks = [parse_peak_mb(r.get("note")) for r in lane_rows]
        peaks = [p for p in peaks if p is not None]
        vram = [float(r.get("vram_after_mb")) for r in lane_rows
                if r.get("vram_after_mb") is not None]
        peak_text = (
            f"[measured] VRAM peak max {max(peaks):.0f} MiB"
            if peaks else "[measured] VRAM peaks: none recorded")
        if vram:
            peak_text += f"; after max {max(vram):.0f} MiB"
        vr_text = (f"[measured] valid {valid} / refused {refused} rows"
                   if have_vr else "[measured] valid/refused: n/a (no search.ndjson)")
        rate = (evals / (wall_s / 3600.0)) if wall_s > 0 and evals else 0.0
        lines += ["",
                  f"### lane {lane}",
                  "",
                  f"[measured] jobs: {len(lane_rows)}; exits: "
                  + ", ".join(f"{key} {value}" for key, value in sorted(exits.items())),
                  f"[measured] evals (from run dirs, not budgets): {evals}; wall time: "
                  f"{wall_s / 60:.1f} min; {vr_text}; {peak_text}",
                  f"[inferred] evals/hour: {rate:.1f} (evals / wall time)",
                  ]
        problem_rows = [r for r in lane_rows if status_of(r)[0] != "ok"]
        if problem_rows:
            lines += ["",
                      f"Blocked/failed jobs ({len(problem_rows)}) with their first error line:"]
            for row in problem_rows:
                err = first_error_line(night_dir, str(row.get("id")))
                status, kind = status_of(row)
                label = status if kind == "measured" else f"~{status} (inferred)"
                lines.append(f"- `{row.get('id')}` [{label}]: " + (err or "(no error line in log)"))
    return lines


def build_report(night_names: list[str], *, runs_root: Path, repo_root: Path,
                 now: float | None = None) -> str:
    """The full markdown report for one or more nights (offline; reads only)."""
    now_text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [f"# Night report: {', '.join(night_names)}",
             "",
             f"Generated {now_text} by `tools/night_report.py` (read-only). "
             "[measured] = read from summary.jsonl / job logs / run dirs; "
             "[inferred] = derived from measured numbers. "
             "J is comparable only within a brief.",
             ]
    for name in night_names:
        night_dir = Path(runs_root) / "nights" / name
        if not night_dir.is_dir():
            lines += ["", f"## Night `{name}`", "", f"(night dir {night_dir} not found)"]
            continue
        lines += [""] + night_section(night_dir, name, repo_root)
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--night", action="append", required=True, metavar="NAME",
                    help="night name under runs/nights (repeatable)")
    ap.add_argument("--out", required=True, metavar="PATH",
                    help="output markdown file (e.g. docs/evidence/NIGHT_<date>.md)")
    ap.add_argument("--runs-root", type=Path, default=None,
                    help="runs root (default: <repo>/runs)")
    args = ap.parse_args(argv)
    runs_root = args.runs_root or REPO / "runs"
    report = build_report(args.night, runs_root=runs_root, repo_root=REPO)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
