"""Night refresher: every tick, look at the failed/watchdog-stopped jobs of a night and repair them.

The runner records every job attempt in ``runs/nights/<night>/summary.jsonl`` (exit codes, run dirs,
evals). This tool turns that ledger into repairs:

* generic-CLI jobs that died (exit 1/75/124) with a resumable run dir are re-appended as a
  ``hornlab-search search --resume <dir> --budget <missing>`` job; ``missing`` = the run's target
  budget minus the valid evals already in its ``search.ndjson``,
* bridge-CLI jobs (klangfilm_lame_cli / rosse_rect_cli / ...) cannot use the generic resume path when
  their config is a bridge type; they are re-appended with the SAME argv and seed, which replays the
  already-solved candidates as cross-run cache hits that do not consume budget,
* ``run_bo_arm`` (TuRBO/BO study) jobs are re-appended with fresh ``--root/--cohort`` ``_rcN``
  directories ONLY when their ``--config`` family has acquired >= ``--min-fresh-rows`` valid rows in
  the newest run dir of that config (the cohort builder refuses otherwise; see the 07:02 failure of
  ``t_rrect80`` whose CMA sibling had died first). Otherwise the repair is DEFERRED and journaled,
* a repair is attempted at most ``--max-repairs`` (default 2); beyond that the failure is journaled as
  needing manual diagnosis,
* a live foreign lock holder is never touched; it is journaled so the next manual look sees it.

It never touches a running job and never writes into the runner's own log; all actions go to
``runs/nights/refresh/<UTC>.md`` plus a rolling ``HANDOFF.md`` (latest state, for the next review).

Usage:  .venv\\Scripts\\python.exe tools/night_queue/refresh_watchdog.py --night <night> [--once]
The companion loop is ``tools/night_queue/refresh_loop.ps1`` (run detached every N minutes).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

BRIDGE_MARKERS = ("klangfilm_lame_cli", "rosse_rect_cli", "crowe_panel_cli",
                  "klangfilm_ellipse_cli", "section_pucker_cli", "rolled_rect_cli")
BO_ARM_MARKER = "run_bo_arm"
HANDLED_MAX = 50


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _valid_rows(run_dir: Path) -> int:
    nd = run_dir / "search.ndjson"
    if not nd.is_file():
        return 0
    n = 0
    for line in nd.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("ok") is True:
            n += 1
    return n


def _argv_value(argv: list, flag: str):
    for i, item in enumerate(argv):
        if str(item) == flag and i + 1 < len(argv):
            return argv[i + 1]
        if str(item).startswith(flag + "="):
            return str(item)[len(flag) + 1:]
    return None


def _config_name(config_path: str) -> str:
    try:
        return str(yaml.safe_load(Path(config_path).read_text(encoding="utf-8")).get("name", ""))
    except Exception:  # noqa: BLE001 - report-only
        return ""


def _newest_run_dirs_for_config(name: str) -> list[Path]:
    out = []
    for d in (ROOT / "runs").glob("*screen*"):
        rj = d / "run.json"
        if not rj.is_file():
            continue
        try:
            if json.loads(rj.read_text(encoding="utf-8")).get("config_name") == name:
                out.append(d)
        except json.JSONDecodeError:
            continue
    return sorted(out, key=lambda d: d.stat().st_mtime, reverse=True)


def _newest_run_rows_for_config(config_path: str) -> int:
    try:
        name = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")).get("name", "")
    except Exception:  # noqa: BLE001 - report-only
        return -1
    best_mtime, best_rows = -1.0, -1
    for d in (ROOT / "runs").glob("*screen*"):
        rj = d / "run.json"
        if not rj.is_file():
            continue
        try:
            meta = json.loads(rj.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if meta.get("config_name") != name:
            continue
        mtime = rj.stat().st_mtime
        if mtime > best_mtime:
            best_mtime = mtime
            best_rows = _valid_rows(d)
    return best_rows


def _budget_for(argv: list, spec: dict, run_dir: str | None, cfg_budget) -> int | None:
    """Missing evals for a resume (target total minus valid rows), or None to keep the argv budget."""
    if "--resume" in [str(a) for a in (argv or [])]:
        resume_dir = _argv_value(argv, "--resume") or run_dir
        if resume_dir and cfg_budget is not None:
            target = int(float(cfg_budget)) + _valid_rows(ROOT / resume_dir)
            already = _valid_rows(ROOT / resume_dir)
            missing = target - already + _valid_rows(ROOT / run_dir) if run_dir else target - already
            return max(int(missing), 1)
    return None


def refresh(night: str, min_fresh_rows: int, max_repairs: int, dry: bool) -> dict:
    night_yaml = ROOT / "runs/nights" / f"{night}.yaml"
    night_dir = ROOT / "runs/nights" / night
    summary = night_dir / "summary.jsonl"
    state_path = night_dir / "refresh_state.json"
    refresh_dir = night_dir / "refresh"
    refresh_dir.mkdir(parents=True, exist_ok=True)

    if not night_yaml.is_file():
        return {"error": f"night file missing: {night_yaml}"}
    plan = yaml.safe_load(night_yaml.read_text(encoding="utf-8"))
    jobs = list(plan.get("jobs") or [])
    by_id = {}
    for j in jobs:
        by_id.setdefault(j["id"], []).append(j)

    state = {"handled": {}, "notes": []}
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    state.setdefault("handled", {})
    state.setdefault("notes", [])

    failures: dict[str, list[dict]] = {}
    if summary.is_file():
        for line in summary.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("exit_code") not in (0, None):
                failures.setdefault(rec.get("id"), []).append(rec)

    done = set()
    qstate = night_dir / "queue_state.json"
    if qstate.is_file():
        try:
            done = set(json.loads(qstate.read_text(encoding="utf-8")).get("done") or [])
        except json.JSONDecodeError:
            pass

    actions, deferrals, inserts = [], [], []
    seen = set()
    existing_ids = {j["id"] for j in jobs}
    for job_id, attempts in sorted(failures.items()):
        base = job_id.split("_rc")[0]
        if base in seen:
            continue
        seen.add(base)
        family = [a for k, v in failures.items() if k == base or k.startswith(base + "_rc")
                  for a in v]
        # blocked attempts are lock-contention transients, not diagnosis-worthy
        hard = [a for a in family if a.get("status") != "blocked"]
        blocked = [a for a in family if a.get("status") == "blocked"]
        n_fail = len(hard) if hard else (len(blocked) if len(blocked) < 4 else 0) or 1
        spec = by_id.get(base, [None])[0]
        if spec is None:
            continue
        # already re-queued? (a *_rc job of this base exists AND is not itself a fresh failure)
        prior = [j for j in jobs if j["id"].startswith(base + "_rc") and j["id"] not in failures
                 and j["id"] in existing_ids]
        if prior:
            deferrals.append(f"{base}: waiting on repair {prior[0]['id']} (failed? "
                             f"{[f['exit_code'] for f in failures.get(prior[0]['id'], [])]})")
            continue
        label = f"{base}#{n_fail}"
        if state["handled"].get(base, 0) >= max_repairs or n_fail > max_repairs + 1:
            state["notes"].append(f"{_utc()} {label}: {n_fail} failed attempts, manual diagnosis needed")
            deferrals.append(f"{label}: manual diagnosis needed ({n_fail} attempts)")
            continue
        argv = [str(a) for a in (spec.get("argv") or [])]
        last = attempts[-1]
        config_arg = _argv_value(argv, "--config")
        resume_dir = _argv_value(argv, "--resume")
        if resume_dir:
            rd = ROOT / resume_dir if not Path(resume_dir).is_absolute() else Path(resume_dir)
        else:
            cands = _newest_run_dirs_for_config(_config_name(config_arg)) if config_arg else []
            rd = cands[0] if cands else None
        if not rd or _valid_rows(rd) == 0:
            deferrals.append(f"{label}: no run dir with rows; needs manual diagnosis "
                             f"(exit {last.get('exit_code')})")
            state["notes"].append(f"{_utc()} {label}: no run dir with rows")
            continue
        bridged = any(m in " ".join(argv) for m in BRIDGE_MARKERS)
        # duplicate-thread guard: another run of this config solving right now -> do not double-run
        name = _config_name(config_arg) if config_arg else _config_name(str(rd / "config.yaml"))
        others = [d for d in _newest_run_dirs_for_config(name) if d.resolve() != rd.resolve()]
        # defer when the thread is or will be complete elsewhere: another run of the same
        # config already holds as many valid rows as this repair's remaining target
        own_target = _argv_value(argv, "--budget")
        remaining_target = int(float(own_target)) if own_target else 10 ** 9
        complete_elsewhere = [d for d in others if _valid_rows(d) >= remaining_target]
        if complete_elsewhere:
            deferrals.append(f"{label}: deferred - {name} budget is covered by {complete_elsewhere[0].name} "
                             f"({_valid_rows(complete_elsewhere[0])} valid >= {remaining_target})")
            state["notes"].append(f"{_utc()} {label}: foreign thread {young[0].name} active")
            continue

        insert_idx = _insert_index(jobs, done)
        rc = 1 + sum(1 for j in jobs if j["id"].startswith(base + "_rc"))
        if bridged:
            missing = None
            if not any(a == "--resume" for a in argv):
                total = _argv_value(argv, "--budget")
                missing = max(int(float(total)) - _valid_rows(rd), 1) if total else None
            new_argv = list(argv) + (["--resume", str(rd)] if not any(a == "--resume" for a in argv) else [])
            if missing is not None and "--budget" not in argv:
                new_argv += ["--budget", str(missing)]
            elif missing is not None and "--resume" not in argv:
                # replace the fresh-run budget with the remaining budget for the resumed dir
                new_argv = [str(x) for x in new_argv]
                i = new_argv.index("--budget")
                new_argv[i + 1] = str(missing)
            new_spec = {"id": f"{base}_rc{rc}", "kind": "command",
                        "timeout_s": int(spec.get("timeout_s") or 10800), "watchdog": False,
                        "argv": new_argv}
            actions.append(f"{label}: bridge resume as {new_spec['id']} from {rd.name} "
                           f"(valid {_valid_rows(rd)}, budget {missing})")
        elif BO_ARM_MARKER in " ".join(argv):
            config_arg = _argv_value(argv, "--config")
            rows = _newest_run_rows_for_config(config_arg) if config_arg else -1
            if rows < max(min_fresh_rows, 1):
                deferrals.append(f"{label}: deferred - {config_arg} family has {max(rows, 0)} fresh valid "
                                 f"rows (< {min_fresh_rows}); finish its CMA leg first")
                state["notes"].append(f"{_utc()} {label}: deferred, sibling rows {max(rows, 0)}")
                continue
            new_argv, flag_next = [], False
            for item in argv:
                if flag_next:
                    new_argv.append(str(item) + f"_rc{rc}")
                    flag_next = False
                    continue
                if str(item) in ("--root", "--cohort"):
                    new_argv.append(item)
                    flag_next = True
                    continue
                new_argv.append(item)
            new_spec = {"id": f"{base}_rc{rc}", "kind": "command",
                        "timeout_s": int(spec.get("timeout_s") or 10800), "watchdog": False,
                        "argv": new_argv}
            actions.append(f"{label}: re-queued BoTorch arm as {new_spec['id']} "
                           f"(config rows now {rows} >= {min_fresh_rows})")
        else:
            already = _valid_rows(rd)
            total = _argv_value(argv, "--budget")
            budget_arg = max(int(float(total)) - already, 1) if total else 30
            new_spec = {"id": f"{base}_rc{rc}", "kind": "command",
                        "timeout_s": int(spec.get("timeout_s") or 7200), "watchdog": False,
                        "argv": [".venv/Scripts/hornlab-search.exe", "search", "--resume", str(rd),
                                 "--budget", str(budget_arg)]}
            actions.append(f"{label}: resumed as {new_spec['id']} from {rd.name} "
                           f"(valid {already}, budget {budget_arg})")
        jobs.insert(insert_idx, new_spec)
        inserts.append(new_spec["id"])

    for base in {aid.rsplit("_rc", 1)[0] for aid in inserts}:
        state["handled"][base] = state["handled"].get(base, 0) + 1

    if inserts and not dry:
        plan["jobs"] = jobs
        tmp = night_yaml.with_suffix(".yaml.tmp")
        tmp.write_text(yaml.safe_dump(plan, sort_keys=False, allow_unicode=True), encoding="utf-8")
        tmp.replace(night_yaml)

    state["notes"] = state["notes"][-HANDLED_MAX:]
    if not dry:
        state_path.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    report = {
        "utc": _utc(), "night": night, "actions": actions, "deferrals": deferrals,
        "queue_log_tail": (night_dir / ".." / f"queue_{night}.log"),
    }
    stamp = _utc().replace(":", "").replace("-", "")
    report_md = ["# Night refresher report", "", f"- utc: {_utc()}", f"- night: {night}", "", "## Actions", ""]
    report_md += [f"- {a}" for a in actions] or ["- (none)"]
    report_md += ["", "## Deferrals / journal", ""]
    report_md += [f"- {d}" for d in deferrals] or ["- (none)"]
    report_md += ["", "## Recent notes", ""]
    report_md += [f"- {nt}" for nt in state["notes"][-8:]]
    (refresh_dir / f"{stamp}.md").write_text("\n".join(report_md) + "\n", encoding="utf-8")
    (refresh_dir / "HANDOFF.md").write_text("\n".join(report_md) + "\n", encoding="utf-8")
    return report


def _insert_index(jobs: list, done: set) -> int:
    """Insert a repair right before the first not-yet-done job (repairs run before stragglers)."""
    for i, j in enumerate(jobs):
        if j["id"] not in done:
            return i
    return len(jobs)


def gate(night: str) -> dict:
    """Lane arbiter between deep ticks: pause our queue while a FOREIGN holder is solving, resume
    when the lock is free or held by our own current job. Writes runs/nights/<night>/PAUSE."""
    night_dir = ROOT / "runs/nights" / night
    lock = ROOT / "runs/.gpu.lock"
    pause = night_dir / "PAUSE"
    holder, alive, cmd = None, False, ""
    if lock.exists():
        try:
            h = json.loads(lock.read_text(encoding="utf-8"))
            holder = int(h.get("pid", -1))
            cmd = str(h.get("command", ""))
        except (json.JSONDecodeError, OSError):
            holder = None
        if holder and holder > 0:
            from hornlab_search.search.gpulock import _pid_alive
            alive = bool(_pid_alive(holder))

    running = None
    try:
        running = json.loads((night_dir / "queue_state.json").read_text(encoding="utf-8")).get("running")
    except (OSError, json.JSONDecodeError):
        pass

    ours = False
    if alive and running:
        plan = yaml.safe_load((night_dir.parent / f"{night}.yaml").read_text(encoding="utf-8"))
        spec = next((j for j in plan.get("jobs", []) if j.get("id") == running), None) or {}
        tokens = [str(t) for t in ([] if spec.get("argv") is None else spec.get("argv"))]
        tokens += [str(spec.get("resume") or ""), str(spec.get("config") or "")]
        tokens = [t for t in tokens if t]
        ours = any(t and (t in cmd or t.split("/")[-1].split("\\")[-1].split(".")[-2:] and
                           pathlib_token(cmd, t)) for t in tokens)
    paused = pause.exists()
    if alive and not ours:
        if not paused:
            pause.write_text("foreign GPU-lock holder\n", encoding="utf-8")
            return {"gate": "PAUSED (foreign holder)", "holder": cmd[:120]}
        return {"gate": "still paused (foreign holder)", "holder": cmd[:120]}
    if paused:
        pause.unlink(missing_ok=True)
        return {"gate": "RESUMED (lock free or held by our job)"}
    return {"gate": "clear", "holder": cmd[:120] if holder else None}


def pathlib_token(cmd: str, t: str) -> bool:
    base = t.replace("\\", "/").split("/")[-1]
    base = base.split(".")[0] if "." in base and not base[0].isdigit() else base
    return base and base in cmd


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--night", required=True)
    ap.add_argument("--gate", action="store_true",
                    help="lane-arbiter tick only: pause/resume the night on foreign lock holders")
    ap.add_argument("--min-fresh-rows", type=int, default=100)
    ap.add_argument("--max-repairs", type=int, default=2)
    ap.add_argument("--once", action="store_true", default=True)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    if a.gate:
        print(json.dumps(gate(a.night), indent=1))
        return 0
    report = refresh(a.night, a.min_fresh_rows, a.max_repairs, a.dry)
    print(json.dumps({k: report[k] for k in ("utc", "night", "actions", "deferrals") if k in report},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
