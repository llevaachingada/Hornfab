"""Offline tests for tools/run_campaign_night.py (the overnight campaign runner).

Hermetic: no GPU, no Julia, no ``hornlab-search`` subprocess. The tool is loaded by path (it is a
script, not a package module) and its real subprocess/hygiene layer is replaced with a fake.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

from conftest import REPO

TOOL = REPO / "tools" / "run_campaign_night.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("run_campaign_night_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


night = _load_tool()

NIGHT_NAME = "smoke_2026-10-27"


# ------------------------------------------------------------------ helpers


def _night_doc(*, brief: str | None = None) -> dict:
    search = {
        "id": "t0__b1t__rosse_morph",
        "kind": "search",
        "config": "examples/typologies/campaign_2026-10-26/b1t__rosse_morph.yaml",
        "budget": 1,
        "mode": "screen",
    }
    if brief:
        search["brief"] = brief
    return {
        "night": NIGHT_NAME,
        "jobs": [
            {
                "id": "phaseB_ladder",
                "kind": "command",
                "argv": [".venv\\Scripts\\python.exe", "tools\\measure_fused_ceiling.py",
                         "--mouth-res", "3.0"],
            },
            search,
        ],
    }


def _write_night(tmp_path: Path, doc: dict | None = None) -> Path:
    path = tmp_path / "night.yaml"
    path.write_text(yaml.safe_dump(doc or _night_doc(), sort_keys=False), encoding="utf-8")
    return path


class FakeRunner:
    """Stands in for NightRunner's subprocess/hygiene layer."""

    def __init__(self, *, codes=None, logs=None, baseline=321.0, after=456.0, peak=999.0):
        self.codes = dict(codes or {})
        self.logs = dict(logs or {})
        self.baseline = baseline
        self.after = after
        self.peak = peak
        self.events: list[tuple[str, str]] = []

    def pre_hygiene(self, job, log_path):
        self.events.append(("pre", job.id))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"=== fake pre-hygiene {job.id}\n", encoding="utf-8")
        return {"baseline_mb": self.baseline, "note": ""}

    def run(self, job, log_path):
        self.events.append(("run", job.id))
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(self.logs.get(job.id, f"fake job {job.id}\n"))
        return int(self.codes.get(job.id, 0)), False

    def post_hygiene(self, job, log_path):
        self.events.append(("post", job.id))
        return {"after_mb": self.after, "peak_mb": self.peak, "note": ""}


def _rows(night_dir: Path) -> list[dict]:
    text = (night_dir / "summary.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


# ------------------------------------------------------------------ (a) parse


def test_parse_night_preserves_order_ids_and_resolves_search_argv(tmp_path):
    path = _write_night(tmp_path, _night_doc(brief="examples/briefs/foo.yaml"))
    plan = night.load_night(path, repo_root=tmp_path)

    assert plan.night == NIGHT_NAME
    assert [job.id for job in plan.jobs] == ["phaseB_ladder", "t0__b1t__rosse_morph"]

    command, search = plan.jobs
    assert command.kind == "command"
    assert command.argv == (
        ".venv\\Scripts\\python.exe", "tools\\measure_fused_ceiling.py",
        "--mouth-res", "3.0")
    assert command.timeout_s == night.COMMAND_TIMEOUT_S

    assert search.kind == "search"
    assert search.argv[0] == str(tmp_path / ".venv" / "Scripts" / "hornlab-search.exe")
    assert search.argv[1:] == (
        "search",
        "--config", "examples/typologies/campaign_2026-10-26/b1t__rosse_morph.yaml",
        "--budget", "1",
        "--mode", "screen",
        "--brief", "examples/briefs/foo.yaml",
    )
    assert search.budget == 1 and search.mode == "screen"
    assert search.timeout_s == night.SEARCH_TIMEOUT_S


def test_no_brief_flag_unless_the_job_sets_one(tmp_path):
    plan = night.load_night(_write_night(tmp_path), repo_root=tmp_path)
    assert "--brief" not in plan.jobs[1].argv


def test_invalid_night_file_rejected(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("night: two/jobs\njobs: []\n", encoding="utf-8")
    try:
        night.load_night(path, repo_root=tmp_path)
    except ValueError as exc:
        assert "night" in str(exc)
    else:  # pragma: no cover - the assertion above is the test
        raise AssertionError("invalid night name was accepted")


# ------------------------------------------------------------------ (b) dry-run


def test_dry_run_prints_jobs_and_launches_nothing(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(night, "REPO_ROOT", tmp_path)
    argv_config = tmp_path / "examples" / "typologies" / "campaign_2026-10-26" / "b1t__rosse_morph.yaml"
    argv_config.parent.mkdir(parents=True, exist_ok=True)
    argv_config.write_text("placeholder placeholder: for the dry-run argv check\n", encoding="utf-8")

    class BoomRunner:
        def __init__(self, *args, **kwargs):  # pragma: no cover - must not run
            raise AssertionError("dry-run must not construct the real runner")

    monkeypatch.setattr(night, "NightRunner", BoomRunner)

    rc = night.main(["--night", str(_write_night(tmp_path)), "--dry-run"])
    assert rc == 0

    out = capsys.readouterr().out
    assert "phaseB_ladder" in out
    assert "t0__b1t__rosse_morph" in out
    assert "kind=command" not in out          # the documented format is "[command]"
    assert "[command]" in out and "[search]" in out
    assert "--config" in out and "--budget" in out

    night_dir = tmp_path / "runs" / "nights" / NIGHT_NAME
    assert not (night_dir / "summary.jsonl").exists()
    assert not (night_dir / "SUMMARY.md").exists()


# ------------------------------------------------------------------ (c) failure isolation


def test_nonzero_job_is_recorded_and_the_next_job_still_runs(tmp_path):
    doc = {
        "night": NIGHT_NAME,
        "jobs": [
            {"id": "first", "kind": "command", "argv": ["echo", "first"]},
            {"id": "second", "kind": "command", "argv": ["echo", "second"]},
        ],
    }
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    runner = FakeRunner(codes={"first": 7})
    runs_root = tmp_path / "runs"

    results = night.run_night(
        plan, repo_root=tmp_path, runs_root=runs_root, runner=runner)

    assert [result.id for result in results] == ["first", "second"]
    assert [result.exit_code for result in results] == [7, 0]
    assert "exit code 7" in results[0].note
    assert results[1].note.startswith("ok")

    run_ids = [jid for action, jid in runner.events if action == "run"]
    assert run_ids == ["first", "second"]

    rows = _rows(runs_root / "nights" / NIGHT_NAME)
    assert [row["id"] for row in rows] == ["first", "second"]
    assert [row["exit_code"] for row in rows] == [7, 0]
    assert rows[0]["vram_baseline_mb"] == 321.0
    assert rows[0]["vram_after_mb"] == 456.0
    assert "peak 999 MiB" in rows[0]["note"]
    assert (runs_root / "nights" / NIGHT_NAME / "SUMMARY.md").is_file()


# ------------------------------------------------------------------ (d) accounting


def test_evals_come_from_search_ndjson_not_the_budget(tmp_path):
    run_dir = tmp_path / "runs" / "20261027T000000Z-screen-abc123"
    run_dir.mkdir(parents=True)
    (run_dir / "search.ndjson").write_text(
        '{"objective": 1.0}\n\n{"objective": 0.5}\n{"objective": 0.25}\n', encoding="utf-8")

    doc = {
        "night": NIGHT_NAME,
        "jobs": [{
            "id": "budget_99_but_three_rows",
            "kind": "search",
            "config": "examples/typologies/campaign_2026-10-26/b1t__rosse_morph.yaml",
            "budget": 99,
            "mode": "screen",
        }],
    }
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    assert plan.jobs[0].budget == 99

    log_text = (
        "search: t0 mode screen, budget 99 new evaluations, 4 bounded keys, "
        f"output {run_dir}\n"
        "  seed J=1.0  best J=0.42 (improved on the seed); stop: budget\n"
    )
    runner = FakeRunner(logs={"budget_99_but_three_rows": log_text})

    results = night.run_night(
        plan, repo_root=tmp_path, runs_root=tmp_path / "runs", runner=runner)

    assert results[0].run_dir == str(run_dir)
    assert results[0].evals_ndjson == 3
    assert results[0].evals_ndjson != plan.jobs[0].budget
    assert results[0].best_J == 0.42

    row = _rows(tmp_path / "runs" / "nights" / NIGHT_NAME)[0]
    assert row["evals_ndjson"] == 3
    assert row["best_J"] == 0.42
    assert row["run_dir"] == str(run_dir)


def test_missing_summary_and_bad_run_dir_degrade_to_null(tmp_path):
    doc = {
        "night": NIGHT_NAME,
        "jobs": [{"id": "no_log_output", "kind": "search",
                  "config": "examples/foo.yaml", "budget": 1}],
    }
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    results = night.run_night(
        plan, repo_root=tmp_path, runs_root=tmp_path / "runs",
        runner=FakeRunner(logs={"no_log_output": "nothing useful\n"}))

    assert results[0].run_dir is None
    assert results[0].evals_ndjson == 0
    assert results[0].best_J is None
    assert "run dir not parsed" in results[0].note
    assert "best J not in log" in results[0].note


# ------------------------------------------------------------------ (e) --only


def test_only_filters_to_one_job(tmp_path):
    doc = {
        "night": NIGHT_NAME,
        "jobs": [
            {"id": "alpha", "kind": "command", "argv": ["echo", "alpha"]},
            {"id": "beta", "kind": "command", "argv": ["echo", "beta"]},
            {"id": "gamma", "kind": "command", "argv": ["echo", "gamma"]},
        ],
    }
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    runner = FakeRunner()

    results = night.run_night(
        plan, only="beta", repo_root=tmp_path,
        runs_root=tmp_path / "runs", runner=runner)

    assert [result.id for result in results] == ["beta"]
    assert [jid for action, jid in runner.events if action == "run"] == ["beta"]
    rows = _rows(tmp_path / "runs" / "nights" / NIGHT_NAME)
    assert [row["id"] for row in rows] == ["beta"]


# ------------------------------------------------------------------ pure parsers


def test_parse_run_dir_variants_and_best_j(tmp_path):
    r1 = tmp_path / "work" / "runs" / "r1"
    r2 = tmp_path / "work" / "runs" / "r2"
    assert night.parse_run_dir(f"search: x output {r1}\n") == r1
    assert night.parse_run_dir(f"search FAILED: boom (output: {r2})\n") == r2
    assert night.parse_run_dir(
        f"search ABORTED: boom (partial results in {r2})\n") == r2
    assert night.parse_run_dir("search: nothing here\n") is None
    assert night.parse_best_j("seed J=3.0  best J=1.25 (improved)") == 1.25
    assert night.parse_best_j("best J=9.0\nbest J=2.5\n") == 2.5
    assert night.parse_best_j("no summary") is None


def test_stale_lock_helpers(tmp_path):
    # 2026-10-28: a job killed on timeout leaves runs/.gpu.lock; the runner takes it over when the
    # recorded holder is gone instead of waiting out lock_wait_s and failing the next job.
    import os
    lock = tmp_path / ".gpu.lock"
    lock.write_text(json.dumps({"pid": 999999, "command": "x"}), encoding="utf-8")
    assert night._lock_holder_pid(lock) == 999999
    assert night._pid_alive(999999) is False
    assert night._pid_alive(os.getpid()) is True
    lock.write_text("not json", encoding="utf-8")
    assert night._lock_holder_pid(lock) is None


# ------------------------------------------------------------------ (f) D.2 statuses / retry


def test_classify_status_pure_table():
    busy_log = "Traceback ... GPU busy: hunte running \"search\" (pid 123) since ...\n"
    assert night.classify_status(3, False, busy_log) == night.STATUS_BLOCKED
    # A succeeded job whose log merely carries the marker through hygiene chatter is NOT blocked
    # (gpu-clean reports "GPU busy" with rc 3, but the job that follows may be fine).
    assert night.classify_status(0, False, "gpu-clean rc=3\nGPU busy: hunte ...\n") == night.STATUS_OK
    assert night.classify_status(7, False, "boom\n") == night.STATUS_FAILED
    assert night.classify_status(1, True, "whatever") == night.STATUS_TIMEOUT
    assert night.classify_status(0, False, "") == night.STATUS_OK


def test_run_dir_and_backend_helpers():
    job = night.Job(id="c", kind="command", argv=("hornlab-search.exe", "verify",
                                                 "--run", "runs/x", "--backend", "beat_cpu"),
                    timeout_s=1.0)
    assert night.backend_of(job) == "beat_cpu"
    search = night.Job(id="s", kind="search", argv=("hornlab-search.exe", "search",
                                                   "--backend=beat_cpu"), timeout_s=1.0,
                       backend="beat_cpu")
    assert night.backend_of(search) == "beat_cpu"
    plain = night.Job(id="p", kind="command", argv=("echo", "hi"), timeout_s=1.0)
    assert night.backend_of(plain) is None


class _ScriptedRunner:
    """FakeRunner whose per-attempt behaviour is scripted [(log_text, exit_code, timed_out), ...]."""

    def __init__(self, script):
        self.script = list(script)
        self.calls: list[str] = []

    def pre_hygiene(self, job, log_path):
        self.calls.append(f"pre:{job.id}")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("", encoding="utf-8")
        return {"baseline_mb": None, "note": ""}

    def run(self, job, log_path):
        self.calls.append(f"run:{job.id}")
        text, code, timed_out = self.script.pop(0)
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(text)
        return code, timed_out

    def post_hygiene(self, job, log_path):
        return {"after_mb": None, "peak_mb": None, "note": ""}


def _single_command_doc(job_id="j", argv=("echo", "hi")):
    return {"night": NIGHT_NAME, "jobs": [{"id": job_id, "kind": "command", "argv": list(argv)}]}


def test_gpu_busy_job_is_recorded_blocked_and_retried_once(tmp_path, monkeypatch):
    """The 2026-11-12 09:35 GPU-busy cascade: nothing was retried and the next job failed the
    same way. D.2a: the blocked job is retried exactly once, after a wait (0 s here)."""
    monkeypatch.setattr(night.time, "sleep", lambda _s: None)
    doc = _single_command_doc(argv=["hornlab-search.exe", "search",
                                    "--config", "examples/foo.yaml", "--backend", "beat_cpu"])
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    busy_log = ("Traceback (most recent call last):\n"
                "GPU busy: hunte running \"search ...\" (pid 123) since 2026-11-12T09:35:23\n")
    runner = _ScriptedRunner([
        (busy_log, 3, False),                                    # attempt 1: blocked
        ("  seed J=1.0  best J=0.42; stop: budget\n", 0, False),  # attempt 2: ok
    ])
    runs_root = tmp_path / "runs"

    results = night.run_night(plan, repo_root=tmp_path, runs_root=runs_root,
                              runner=runner, retry_wait_s=0.0)

    assert runner.script == []                       # both attempts consumed, no third run
    assert [c for c in runner.calls if c.startswith("run")] == ["run:j", "run:j"]
    assert len(results) == 1
    assert results[0].status == night.STATUS_OK and results[0].exit_code == 0

    rows = _rows(runs_root / "nights" / NIGHT_NAME)
    assert [row["status"] for row in rows] == ["blocked", "ok"]
    assert [row["attempts"] for row in rows] == [1, 2]
    assert rows[0]["status"] == "blocked" and rows[0]["attempts"] == 1
    assert rows[0]["backend"] == "beat_cpu"          # --backend parsed from a COMMAND argv
    assert rows[0]["lane"] == "gpu"                  # night file sets no lane -> gpu lane
    queue_text = (runs_root / "overnight" / f"queue_{NIGHT_NAME}.log").read_text(encoding="utf-8")
    assert queue_text.count(f"START j ") == 1        # ONE START/END pair per job (one RETRY line)
    assert queue_text.count(f"END j ") == 1
    assert "RETRY j blocked (GPU busy)" in queue_text
    assert "RETRY j now (attempt 2)" in queue_text
    assert queue_text.index("RETRY") > queue_text.index("START j ") \
        and queue_text.index("RETRY") < queue_text.index("END j ")


def test_blocked_job_that_stays_blocked_is_retried_exactly_once(tmp_path):
    doc = _single_command_doc()
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    busy_log = "GPU busy: someone running \"x\" (pid 5) since 2026-11-12T10:00:00\n"
    runner = _ScriptedRunner([(busy_log, 3, False), (busy_log, 3, False)])

    results = night.run_night(plan, repo_root=tmp_path, runs_root=tmp_path / "runs",
                              runner=runner, retry_wait_s=0.0)

    assert runner.script == []
    assert len(results) == 1
    assert results[0].status == night.STATUS_BLOCKED and results[0].exit_code == 3
    rows = _rows(tmp_path / "runs" / "nights" / NIGHT_NAME)
    assert [row["status"] for row in rows] == ["blocked", "blocked"]
    assert [row["attempts"] for row in rows] == [1, 2]


def test_ok_and_failed_jobs_are_not_retried(tmp_path):
    doc = _single_command_doc()
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    runner = _ScriptedRunner([("all fine\n", 0, False)])
    results = night.run_night(plan, repo_root=tmp_path, runs_root=tmp_path / "runs_a",
                              runner=runner, retry_wait_s=0.0)
    assert results[0].status == night.STATUS_OK
    rows = _rows(tmp_path / "runs_a" / "nights" / NIGHT_NAME)
    assert len(rows) == 1 and rows[0]["attempts"] == 1

    doc = _single_command_doc()
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    runner = _ScriptedRunner([("plain crash\n", 7, False)])
    results = night.run_night(plan, repo_root=tmp_path, runs_root=tmp_path / "runs_b",
                              runner=runner, retry_wait_s=0.0)
    assert results[0].status == night.STATUS_FAILED
    rows = _rows(tmp_path / "runs_b" / "nights" / NIGHT_NAME)
    assert len(rows) == 1 and rows[0]["attempts"] == 1


def test_rows_carry_lane_backend_and_parsed_run_dir(tmp_path):
    """D.2c: lane and backend end up on the summary row for BOTH job kinds; the run dir is
    parsed for a search job and verified (the command-job form is covered above)."""
    run_dir = tmp_path / "runs" / "20261112T113000Z-screen-cafe01"
    run_dir.mkdir(parents=True)
    (run_dir / "search.ndjson").write_text('{"objective": 1.0}\n', encoding="utf-8")
    doc = {
        "night": "cpu_2026-11-12", "lane": "cpu",
        "jobs": [{
            "id": "c9_search", "kind": "search", "mode": "screen", "budget": 5,
            "backend": "beat_cpu", "config": "examples/lecleach_rollback.yaml",
        }],
    }
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    log_text = (
        f"search: c9 mode screen, budget 5 new evaluations, output {run_dir}\n"
        "  seed J=9.0  best J=4.2 (improved on the seed); stop: budget\n"
    )
    runner = _ScriptedRunner([(log_text, 0, False)])
    results = night.run_night(plan, repo_root=tmp_path, runs_root=tmp_path / "runs",
                              runner=runner, retry_wait_s=0.0)
    row = _rows(tmp_path / "runs" / "nights" / "cpu_2026-11-12")[0]
    assert row["lane"] == "cpu"
    assert row["backend"] == "beat_cpu"
    assert row["run_dir"] == str(run_dir)
    assert results[0].status == night.STATUS_OK


# ------------------------------------------------------------------ (g) D.2d dry-run path check


def test_dry_run_fails_listing_every_missing_path(tmp_path):
    doc = {
        "night": NIGHT_NAME,
        "jobs": [
            {"id": "missing_many", "kind": "command",
             "argv": ["hornlab-search.exe", "search",
                      "--config", "examples/nope.yaml",
                      "--brief", "examples/also_nope.yaml",
                      "--resume", "runs/ghost_run"], },
            {"id": "ok_paths", "kind": "command",
             "argv": ["hornlab-search.exe", "verify", "--run", "runs/real_run"]},
        ],
    }
    real = tmp_path / "runs" / "real_run"
    real.mkdir(parents=True)
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    try:
        night.run_night(plan, dry_run=True, repo_root=tmp_path)
    except ValueError as exc:
        text = str(exc)
        assert "--config" in text and "examples/nope.yaml" in text
        assert "--brief" in text and "examples/also_nope.yaml" in text
        assert "--resume" in text and "runs/ghost_run" in text
        assert "3 path(s) missing" in text
        # The ok job's path is NOT reported: the failure lists exactly the missing ones
        assert "runs/real_run" not in text
    else:  # pragma: no cover
        raise AssertionError("dry-run accepted missing argv paths")


def test_dry_run_passes_when_every_argv_path_exists(tmp_path):
    cfg = tmp_path / "examples" / "foo.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("x: 1\n", encoding="utf-8")
    doc = {
        "night": NIGHT_NAME,
        "jobs": [{"id": "fine", "kind": "command",
                  "argv": ["hornlab-search.exe", "search",
                           "--config", "examples/foo.yaml",
                           "--config=examples/foo.yaml",
                           "--brief", "examples/foo.yaml"]}],
    }
    plan = night.load_night(_write_night(tmp_path, doc), repo_root=tmp_path)
    assert night.run_night(plan, dry_run=True, repo_root=tmp_path) == []
