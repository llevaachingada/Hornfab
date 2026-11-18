"""Offline tests for night-reporting truth (senior directive C1, 2026-11-17).

Two reporting bugs were measured on ``cd_rrect_2026-11-17``:

* a ``--resume`` search job showed "best J None, 0 evals" while its run dir really gained 182
  rows (159 valid) — the summary counted nothing because the log named no run dir;
* a BO study arm that made 80 screen + 2 verify calls exited 0 and was recorded as "0 evals".

These tests pin the additive summary fields written by ``tools/run_campaign_night.py`` and the
read-only fallbacks in ``tools/night_status.py``. Hermetic: run dirs, logs and a tiny study
journal live in ``tmp_path``; no GPU, solver, subprocess or real ``runs/``.
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import yaml

from conftest import REPO

RUNNER = REPO / "tools" / "run_campaign_night.py"
STATUS = REPO / "tools" / "night_status.py"

NIGHT_NAME = "cd_rrect_2026-11-17"
START = "2026-11-17T10:00:00Z"
END = "2026-11-17T11:00:00Z"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


night = _load(RUNNER, "run_campaign_night_truth_tool")
status = _load(STATUS, "night_status_truth_tool")


# ------------------------------------------------------------------ fixtures


def _row(n: int, objective: float | None, *, ok: bool, created: str) -> dict:
    out = {"n": n, "ok": ok, "created_utc": created}
    if objective is not None:
        out["objective"] = objective
    if ok:
        out["design_hash"] = f"hash{n:04d}"
    else:
        out["kind"] = "invalid_geometry"
    return out


def _write_ndjson(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


class _AppendingRunner:
    """Minimal runner seam: appends rows to the resumed run dir and returns a scripted exit."""

    def __init__(self, run_dir: Path, new_rows: list[dict], *, code: int = 1,
                 log_text: str = "warning only, no traceback\n"):
        self.run_dir = run_dir
        self.new_rows = new_rows
        self.code = code
        self.log_text = log_text
        self.last_child_tail: list[str] = []

    def pre_hygiene(self, job, log_path):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(f"=== pre-hygiene {job.id}\n")
        return {"baseline_mb": None, "note": ""}

    def run(self, job, log_path):
        existing = []
        ndjson = self.run_dir / "search.ndjson"
        if ndjson.is_file():
            existing = [json.loads(line) for line in
                        ndjson.read_text(encoding="utf-8").splitlines() if line.strip()]
        _write_ndjson(ndjson, existing + self.new_rows)
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(self.log_text)
        self.last_child_tail = self.log_text.strip().splitlines()
        return self.code, False

    def post_hygiene(self, job, log_path):
        return {"after_mb": None, "peak_mb": None, "note": ""}


class _QuietRunner(_AppendingRunner):
    """A runner seam that only writes a log (BO arm; its work is in the study root)."""

    def __init__(self, *, code: int = 0, log_text: str = ""):
        super().__init__(Path("."), [], code=code, log_text=log_text)

    def run(self, job, log_path):
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(self.log_text)
        self.last_child_tail = [line for line in self.log_text.splitlines() if line.strip()]
        return self.code, False


def _write_night(tmp_path: Path, jobs: list[dict]) -> Path:
    path = tmp_path / "night.yaml"
    path.write_text(yaml.safe_dump({"night": NIGHT_NAME, "jobs": jobs}, sort_keys=False),
                    encoding="utf-8")
    return path


def _summary_rows(runs_root: Path) -> list[dict]:
    text = (runs_root / "nights" / NIGHT_NAME / "summary.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


# ------------------------------------------------------------------ runner: search window


def test_resume_job_reports_the_rows_this_job_added(tmp_path):
    run_dir = tmp_path / "runs" / "20261115T020650Z-screen-22931c"
    run_dir.mkdir(parents=True)
    _write_ndjson(run_dir / "search.ndjson", [
        _row(n, 9.0 + n, ok=True, created=f"2026-11-15T02:0{n}:00Z") for n in range(4)
    ])
    new_rows = [
        _row(4, 0.9, ok=True, created="2026-11-17T10:10:00Z"),
        _row(5, 0.3, ok=True, created="2026-11-17T10:20:00Z"),
        _row(6, None, ok=False, created="2026-11-17T10:30:00Z"),
    ]
    doc = {"id": "cont_p80_athcore_corelaw_200", "kind": "search",
           "config": "examples/typologies/campaign_2026-10-26/b1t__rosse_morph.yaml",
           "budget": 3, "mode": "screen", "resume": str(run_dir)}
    plan = night.load_night(_write_night(tmp_path, [doc]), repo_root=tmp_path)
    runs_root = tmp_path / "runs"

    results = night.run_night(plan, repo_root=tmp_path, runs_root=runs_root,
                              runner=_AppendingRunner(run_dir, new_rows))

    row = _summary_rows(runs_root)[0]
    assert row["run_dir"] == str(run_dir)          # named by --resume even with no final summary
    assert row["evals_ndjson"] == 7                # the run dir total, historical semantics kept
    assert row["rows_before"] == 4
    assert row["rows_after"] == 7
    assert row["rows_window"] == 3                 # the work THIS job did, not 0 and not 7
    assert row["valid_rows_window"] == 2
    assert row["best_J_window"] == 0.3
    assert row["best_J"] == 0.3                    # no final summary line -> measured rows win
    assert row["stop_reason"] == night.STOP_UNEXPLAINED
    assert "stop reason: exit_nonzero_no_cause" in row["note"]
    assert "last output: warning only, no traceback" in row["note"]
    assert row["log_tail"] == ["warning only, no traceback"]
    assert results[0].rows_window == 3


def test_fresh_search_reports_its_whole_run_dir(tmp_path):
    run_dir = tmp_path / "runs" / "20261117T100000Z-screen-fresh1"
    run_dir.mkdir(parents=True)
    _write_ndjson(run_dir / "search.ndjson", [
        _row(0, 2.0, ok=True, created="2026-11-17T10:01:00Z"),
        _row(1, 1.0, ok=True, created="2026-11-17T10:02:00Z"),
    ])
    doc = {"id": "fresh", "kind": "search",
           "config": "examples/typologies/campaign_2026-10-26/b1t__rosse_morph.yaml",
           "budget": 2, "mode": "screen"}
    plan = night.load_night(_write_night(tmp_path, [doc]), repo_root=tmp_path)
    log_text = (f"search: fresh mode screen, output {run_dir}\n"
                "  seed J=2.0  best J=1.0 (improved on the seed); stop: budget\n")
    runner = _AppendingRunner(run_dir, [], code=0, log_text=log_text)
    runs_root = tmp_path / "runs"

    night.run_night(plan, repo_root=tmp_path, runs_root=runs_root, runner=runner)

    row = _summary_rows(runs_root)[0]
    assert row["rows_before"] == 0                  # a fresh job starts from nothing
    assert row["rows_after"] == 2
    assert row["rows_window"] == 2 and row["valid_rows_window"] == 2
    assert row["best_J_window"] == 1.0
    assert row["best_J"] == 1.0                     # the log's final summary still wins
    assert row["stop_reason"] == night.STOP_OK


# ------------------------------------------------------------------ runner: BO arm progress


def _study_root(tmp_path: Path) -> Path:
    root = tmp_path / "runs" / "night31_2026-11-17" / "turbo_trit80_rc2"
    root.mkdir(parents=True)
    (root / "package.json").write_text(json.dumps({
        "package_id": "abc123", "status_note": "cheap-check-passed",
        "budget": {"screen_calls": 80, "verify_calls": 2, "total_calls": 82, "attempts": 400},
    }), encoding="utf-8")
    conn = sqlite3.connect(root / "studies.sqlite3")
    conn.execute("CREATE TABLE attempts (kind TEXT, result_json TEXT)")
    conn.execute("CREATE TABLE observations (package_id TEXT)")
    conn.execute("CREATE TABLE packages (status TEXT)")
    results = [
        ("screen", {"call_status": "called", "observed_j": 5.0, "outcome": "success"}),
        ("screen", {"call_status": "called", "observed_j": 4.0, "outcome": "success"}),
        ("screen", {"call_status": "not_called", "observed_j": 1.0, "outcome": "cheap_refusal"}),
        ("verify", {"call_status": "called", "observed_j": 3.5, "outcome": "success",
                    "eligible": False}),
    ]
    conn.executemany("INSERT INTO attempts VALUES (?,?)",
                     [(kind, json.dumps(payload)) for kind, payload in results])
    conn.executemany("INSERT INTO observations VALUES (?)", [("abc123",), ("abc123",)])
    conn.execute("INSERT INTO packages VALUES ('pool_exhausted')")
    conn.commit()
    conn.close()
    return root


def test_bo_arm_records_package_progress_instead_of_zero_evals(tmp_path):
    root = _study_root(tmp_path)
    doc = {"id": "t_trit80_rc2", "kind": "command", "argv": [
        ".venv/Scripts/python.exe", "tools/night_queue/run_bo_arm.py",
        "--root", str(root), "--cohort", "runs/night31_2026-11-17/cohort_trit80_rc2",
        "--policy", "turbo", "--seed", "89011", "--config", "examples/x.yaml"]}
    plan = night.load_night(_write_night(tmp_path, [doc]), repo_root=tmp_path)
    runs_root = tmp_path / "runs"

    night.run_night(plan, repo_root=tmp_path, runs_root=runs_root, runner=_QuietRunner())

    row = _summary_rows(runs_root)[0]
    progress = row["bo_progress"]
    assert progress["source"] == "studies.sqlite3"
    assert progress["screen_calls"] == 2 and progress["verify_calls"] == 1
    assert progress["total_calls"] == 3 and progress["attempts"] == 4
    assert progress["observations"] == 2
    assert progress["best_screen_J"] == 4.0 and progress["best_verify_J"] == 3.5
    assert progress["package_status"] == "pool_exhausted"
    assert progress["budget"]["screen_calls"] == 80
    assert row["evals_ndjson"] == 3
    assert row["best_J"] == 3.5
    assert row["run_dir"] is None                  # a study root is not a search run dir
    assert "BO screen 2 verify 1 observations 2" in row["note"]
    assert row["stop_reason"] == night.STOP_OK


def test_bo_progress_log_fallback_parses_the_cli_progress_json():
    text = ('{"source": {"scores_json": "x"}}\n'
            '{"ok":true,"package_id":"abc","progress":{"attempts":82,"screen_calls":80,'
            '"total_calls":82,"verify_calls":2,"unresolved":false},'
            '"status":"pool_exhausted"}\n')
    progress = night.bo_progress_from_log(text)
    assert progress["source"] == "log"
    assert progress["screen_calls"] == 80 and progress["verify_calls"] == 2
    assert progress["total_calls"] == 82
    assert progress["package_status"] == "pool_exhausted"
    assert "best_screen_J" not in progress        # the log's progress JSON carries no best J


# ------------------------------------------------------------------ pure helpers


def test_tail_from_log_drops_runner_lines_and_caps_length():
    lines = ["=== pre-hygiene x", "gpu-clean --lane gpu rc=0", "gpu-clean: no processes",
             "gpu lock clear; VRAM baseline=1 MiB"] + [f"child {i}" for i in range(20)]
    lines.append("x" * 5000)                       # a BO prep prints a huge JSON on one line
    tail = night.tail_from_log("\n".join(lines))
    assert len(tail) == night.LOG_TAIL_LINES == 15
    assert tail[-1].endswith("...") and len(tail[-1]) <= night.TAIL_LINE_MAX_CHARS + 3
    assert tail[-2] == "child 19"
    assert all(not line.startswith(("gpu-clean", "gpu lock", "=== ")) for line in tail)


def test_classify_stop_reason_table():
    assert night.classify_stop_reason(0, False, night.STATUS_OK, []) == night.STOP_OK
    assert night.classify_stop_reason(124, True, night.STATUS_TIMEOUT, []) == night.STOP_TIMEOUT
    assert (night.classify_stop_reason(75, False, night.STATUS_WATCHDOG, [])
            == night.STOP_WATCHDOG)
    assert (night.classify_stop_reason(1, False, night.STATUS_BLOCKED,
                                       ["GPU busy: x running y"])
            == night.STOP_BLOCKED)
    assert (night.classify_stop_reason(1, False, night.STATUS_FAILED,
                                       ["Traceback (most recent call last):"])
            == night.STOP_TRACEBACK)
    assert (night.classify_stop_reason(1, False, night.STATUS_FAILED, ["RuntimeError: boom"])
            == night.STOP_ERROR_LINE)
    # 2026-11-17's silent exit-1 class: warnings only, no cause line
    assert (night.classify_stop_reason(1, False, night.STATUS_FAILED, ["12:51:21 WARNING mesher"])
            == night.STOP_UNEXPLAINED)


def test_argv_path_helpers_resolve_resume_run_and_bo_root(tmp_path):
    argv = (".venv/Scripts/hornlab-search.exe", "search", "--resume", "runs/run-a",
            "--budget", "200")
    assert night.run_dir_from_argv(argv, repo_root=tmp_path) == tmp_path / "runs" / "run-a"
    assert night.run_dir_from_argv(argv, repo_root=tmp_path).name == "run-a"

    bo_argv = ("python.exe", "tools/night_queue/run_bo_arm.py", "--root",
               "runs/night31/turbo_trit80_rc2", "--cohort", "c")
    assert night.bo_root_from_argv(bo_argv, repo_root=tmp_path) == (
        tmp_path / "runs" / "night31" / "turbo_trit80_rc2")
    assert night.bo_root_from_argv(("python.exe", "tools/other.py", "--root", "x"),
                                   repo_root=tmp_path) is None


def test_job_window_rows_prefers_the_delta_then_the_timestamp_window():
    rows = [{"n": i} for i in range(6)]
    assert [r["n"] for r in night.job_window_rows(rows, 4, START, END)] == [4, 5]
    assert night.job_window_rows(rows, 6, START, END) == []      # launched, added nothing
    stamped = [
        _row(0, 1.0, ok=True, created="2026-11-17T09:00:00Z"),   # before the job
        _row(1, 0.5, ok=True, created="2026-11-17T10:30:00Z"),
        _row(2, 0.4, ok=True, created="2026-11-17T11:30:00Z"),   # after the job
    ]
    window = night.job_window_rows(stamped, 0, START, END)       # fresh job -> all rows
    assert len(window) == 3
    assert [r["n"] for r in night.job_window_rows(stamped, 99, START, END)] == [1]


# ------------------------------------------------------------------ night_status fallbacks


def _night_dir(tmp_path: Path) -> Path:
    night_dir = tmp_path / "runs" / "nights" / NIGHT_NAME
    night_dir.mkdir(parents=True)
    return night_dir


def test_night_status_prefers_the_new_summary_fields(tmp_path):
    night_dir = _night_dir(tmp_path)
    row = {"id": "job1", "exit_code": 1, "seconds": 600, "start": START, "end": END,
           "rows_window": 12, "valid_rows_window": 9, "best_J_window": 1.25,
           "best_J": 1.0, "evals_ndjson": 40}
    truth = status.job_truth(row, night_dir, tmp_path)
    assert truth["evals"] == 12 and truth["best_J"] == 1.25
    assert truth["source"] == "summary"
    line = status.format_summary_row(row, truth)
    assert line.startswith("    job1: best J 1.25, 12 evals, 10 min")


def test_legacy_resume_row_reports_rows_inside_its_own_window(tmp_path):
    night_dir = _night_dir(tmp_path)
    run_dir = tmp_path / "runs" / "20261115T020650Z-screen-22931c"
    run_dir.mkdir(parents=True)
    _write_ndjson(run_dir / "search.ndjson", [
        _row(0, 9.0, ok=True, created="2026-11-15T02:07:59Z"),    # before the night job
        _row(1, 2.0, ok=True, created="2026-11-17T10:10:00Z"),
        _row(2, 1.5, ok=True, created="2026-11-17T10:20:00Z"),
        _row(3, None, ok=False, created="2026-11-17T10:30:00Z"),
        _row(4, 0.2, ok=True, created="2026-11-17T12:00:00Z"),    # after the night job
    ])
    (night_dir / "job1.log").write_text(
        f"=== argv: .venv/Scripts/hornlab-search.exe search --resume {run_dir} --budget 200\n",
        encoding="utf-8")
    row = {"id": "job1", "exit_code": 1, "seconds": 120, "start": START, "end": END,
           "run_dir": None, "evals_ndjson": 0, "best_J": None}

    truth = status.job_truth(row, night_dir, tmp_path)

    assert truth["evals"] == 3                       # not 0 evals and not the whole 5-row dir
    assert truth["best_J"] == 1.5
    assert truth["run_dir"] == str(run_dir)
    assert truth["detail"] == "window 3/5 rows, valid 2"


def test_legacy_resume_with_unattributable_rows_reports_unknown(tmp_path):
    night_dir = _night_dir(tmp_path)
    run_dir = tmp_path / "runs" / "20261115T020650Z-screen-22931c"
    run_dir.mkdir(parents=True)
    _write_ndjson(run_dir / "search.ndjson",
                  [_row(i, 1.0 + i, ok=True, created="2026-11-15T02:07:59Z") for i in range(4)])
    (night_dir / "job1.log").write_text(
        f"=== argv: .venv/Scripts/hornlab-search.exe search --resume {run_dir} --budget 200\n",
        encoding="utf-8")
    row = {"id": "job1", "exit_code": 1, "seconds": 120, "start": START, "end": END,
           "run_dir": None, "evals_ndjson": 0, "best_J": None}

    truth = status.job_truth(row, night_dir, tmp_path)

    assert truth["evals"] == "unknown" and truth["best_J"] == "unknown"
    assert "4 rows in run dir" in truth["detail"]
    line = status.format_summary_row(row, truth)
    assert "best J unknown, unknown evals" in line


def test_night_status_reads_bo_package_progress_for_an_old_row(tmp_path):
    night_dir = _night_dir(tmp_path)
    root = _study_root(tmp_path)
    (night_dir / "t_trit80_rc2.log").write_text(
        "=== argv: C:/x/python.exe tools/night_queue/run_bo_arm.py --root "
        f"{root} --cohort c --policy turbo --seed 1 --config examples/x.yaml\n",
        encoding="utf-8")
    row = {"id": "t_trit80_rc2", "exit_code": 0, "seconds": 7270, "start": START, "end": END,
           "run_dir": None, "evals_ndjson": 0, "best_J": None, "note": "ok; peak 1894 MiB"}

    truth = status.job_truth(row, night_dir, tmp_path)

    assert truth["evals"] == 3
    assert truth["best_J"] == 3.5
    assert truth["source"] == "package progress"
    assert truth["detail"] == "BO screen 2 verify 1 observations 2"
    line = status.format_summary_row(row, truth)
    assert "best J 3.5, 3 evals, 121 min (BO screen 2 verify 1 observations 2)" in line


def test_legacy_non_resume_row_falls_back_to_the_run_dir_total(tmp_path):
    night_dir = _night_dir(tmp_path)
    run_dir = tmp_path / "runs" / "20261117T100000Z-screen-fresh1"
    run_dir.mkdir(parents=True)
    _write_ndjson(run_dir / "search.ndjson",
                  [_row(i, 3.0 - i, ok=True, created="2026-11-17T10:0%d:00Z" % i)
                   for i in range(3)])
    (night_dir / "job1.log").write_text(f"search: job1 mode screen, output {run_dir}\n",
                                        encoding="utf-8")
    row = {"id": "job1", "exit_code": 0, "seconds": 60, "start": START, "end": END,
           "run_dir": str(run_dir), "evals_ndjson": 0, "best_J": None}

    truth = status.job_truth(row, night_dir, tmp_path)

    assert truth["evals"] == 3 and truth["best_J"] == 1.0
