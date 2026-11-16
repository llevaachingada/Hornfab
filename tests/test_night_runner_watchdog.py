"""Search watchdog (2026-11-16): stop a search job on high refusal rate, no gain, or a stall."""
from __future__ import annotations

import sys
import io
import subprocess
import textwrap
import time
from pathlib import Path

import pytest

import tools.run_campaign_night as night

CFG = dict(night.WATCHDOG_DEFAULTS)


def test_stdout_eof_does_not_report_success_before_exit(tmp_path, monkeypatch):
    class DelayedFailure:
        pid = 123
        stdout = io.StringIO("")
        returncode = None

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            self.returncode = 7
            return 7

    monkeypatch.setattr(night.subprocess, "Popen", lambda *args, **kwargs: DelayedFailure())
    job = night.Job(id="eof", kind="command", argv=("fake",), timeout_s=5)
    runner = night.NightRunner(repo_root=tmp_path, runs_root=tmp_path, lane="cpu")
    log = tmp_path / "eof.log"
    assert runner.run(job, log) == (7, False)
    assert "exit=7" in log.read_text(encoding="utf-8")


def test_stdout_eof_still_obeys_deadline(tmp_path, monkeypatch):
    class NeverExits:
        pid = 123
        stdout = io.StringIO("")
        returncode = None

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            if self.returncode is not None:
                return self.returncode
            raise subprocess.TimeoutExpired("fake", timeout)

        def kill(self):
            self.returncode = -1

    monkeypatch.setattr(night.subprocess, "Popen", lambda *args, **kwargs: NeverExits())
    monkeypatch.setattr(night, "_kill_tree", lambda proc: proc.kill())
    job = night.Job(id="eof_timeout", kind="command", argv=("fake",), timeout_s=0.05)
    runner = night.NightRunner(repo_root=tmp_path, runs_root=tmp_path, lane="cpu")
    assert runner.run(job, tmp_path / "timeout.log") == (124, True)


def ok(n, j):
    return {"n": n, "ok": True, "objective": j}


def bad(n):
    return {"n": n, "ok": False, "objective": 1000.0, "kind": "invalid_geometry"}


def test_refusal_rate_trips_only_after_min_attempts():
    rows = [ok(0, 5.0)] + [bad(i) if i % 2 else ok(i, 5 - i * 0.01) for i in range(1, 24)]
    assert night.watchdog_verdict(rows, CFG) is None                 # 24 < 25 attempts
    rows += [bad(24), bad(25)]
    assert "refusal rate" in night.watchdog_verdict(rows, CFG)


def test_refusal_rate_uses_recent_window():
    rows = [bad(i) for i in range(20)] + [ok(20 + i, 5 - i * 0.1) for i in range(30)]
    assert night.watchdog_verdict(rows, CFG) is None                 # last 30 all valid


def test_no_gain_when_seed_still_best():
    rows = [ok(0, 3.0)] + [ok(i, 3.5 + i * 0.01) for i in range(1, 29)]
    assert night.watchdog_verdict(rows, CFG) is None
    rows.append(ok(30, 4.0))
    assert "no gain" in night.watchdog_verdict(rows, CFG)


def test_stall_after_progress():
    rows = [ok(0, 10.0)] + [ok(i, 10 - i) for i in range(1, 8)]            # best 3.0
    rows += [ok(8 + i, 3.0 + 0.1 + i * 0.001) for i in range(39)]
    assert night.watchdog_verdict(rows, CFG) is None                 # 39 non-improving evals: not yet
    rows.append(ok(48, 3.2))
    assert "stalled" in night.watchdog_verdict(rows, CFG)


def test_improving_run_is_left_alone():
    rows = [ok(i, 10.0 / (1 + i)) for i in range(120)]
    assert night.watchdog_verdict(rows, CFG) is None


def test_resolve_merges_and_off():
    wd = dict(night._resolve_watchdog({"refusal_max": 0.5}, {"stall_valid": 60}, "x"))
    assert wd["refusal_max"] == 0.5 and wd["stall_valid"] == 60 and wd["min_attempts"] == 25
    assert night._resolve_watchdog(None, False, "x") is None
    assert night._resolve_watchdog(False, None, "x") is None
    with pytest.raises(ValueError):
        night._resolve_watchdog({"bogus": 1}, None, "x")


def test_only_search_jobs_are_watched(tmp_path):
    nf = tmp_path / "n.yaml"
    nf.write_text(textwrap.dedent("""\
        night: wd_t
        watchdog: {refusal_max: 0.4}
        jobs:
          - {id: s, kind: command, argv: [.venv/Scripts/hornlab-search.exe, search, --config, x.yaml]}
          - {id: r, kind: command, argv: [python, tools/geometry/rosse_rect_cli.py, search, --config, x.yaml]}
          - {id: v, kind: command, argv: [python, tools/geometry/rosse_rect_cli.py, verify-night, --night, n]}
          - {id: b, kind: command, argv: [python, -m, hornlab_search.studies.cli, run]}
          - {id: nowd, kind: command, watchdog: false, argv: [hornlab-search, search, --config, x.yaml]}
        """), encoding="utf-8")
    plan = night.load_night(nf, repo_root=tmp_path)
    got = {j.id: (None if j.watchdog is None else dict(j.watchdog)["refusal_max"]) for j in plan.jobs}
    assert got == {"s": 0.4, "r": 0.4, "v": None, "b": None, "nowd": None}


def test_real_subprocess_is_stopped_and_recorded(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    script = tmp_path / "fake_search.py"
    script.write_text(textwrap.dedent(f"""\
        import json, time, pathlib
        d = pathlib.Path(r"{runs}") / "20991231T000000Z-screen-abc123"
        d.mkdir()
        with open(d / "search.ndjson", "w") as f:
            for i in range(200):
                r = {{"n": i, "ok": i % 2 == 0, "objective": 5.0 if i % 2 == 0 else 1000.0}}
                f.write(json.dumps(r) + "\\n"); f.flush()
                time.sleep(0.01)
        time.sleep(60)
        """), encoding="utf-8")
    job = night.Job(id="fake", kind="command", argv=(sys.executable, str(script), "search"),
                    timeout_s=120, watchdog=tuple(sorted(CFG.items())))
    runner = night.NightRunner(repo_root=tmp_path, runs_root=runs, lane="cpu")
    runner.watchdog_poll_s = 0.5
    log = tmp_path / "fake.log"
    t0 = time.monotonic()
    code, timed_out = runner.run(job, log)
    assert time.monotonic() - t0 < 40
    assert (code, timed_out) == (night.WATCHDOG_EXIT, False)
    text = log.read_text(encoding="utf-8")
    assert "=== WATCHDOG refusal rate" in text
    assert night.classify_status(code, timed_out, text) == night.STATUS_WATCHDOG
    assert night.parse_run_dir(text, repo_root=tmp_path).name == "20991231T000000Z-screen-abc123"


def test_bound_pinning_stops():
    rows = [{"n": i, "ok": True, "objective": 10 - i * 0.1, "params": {"grid": {"knobs": {"g_fc_hz": 450.0 if i > 30 else 600.0}}}}
            for i in range(40)]
    assert "bound-pinned" in night.watchdog_verdict(rows, CFG, {"g_fc_hz": (450.0, 900.0)})
    assert night.watchdog_verdict(rows, CFG, {"g_fc_hz": (300.0, 900.0)}) is None


def test_pin_ignore_skips_hard_limit_knobs():
    rows = [{"n": i, "ok": True, "objective": 10 - i * 0.1, "params": {"g_tmax": 1.0}} for i in range(40)]
    assert "bound-pinned" in night.watchdog_verdict(rows, CFG, {"g_tmax": (0.85, 1.0)})
    cfg = dict(night._resolve_watchdog(None, {"pin_ignore": ["g_tmax"]}, "x"))
    assert night.watchdog_verdict(rows, cfg, {"g_tmax": (0.85, 1.0)}) is None
    with pytest.raises(ValueError):
        night._resolve_watchdog(None, {"pin_ignore": "g_tmax"}, "x")


def test_resumed_run_judges_only_new_rows(tmp_path):
    runs = tmp_path / "runs"; run = runs / "20990101T000000Z-screen-old001"; run.mkdir(parents=True)
    old = [{"n": i, "ok": True, "objective": 3.0} for i in range(60)]          # converged: would trip no-gain/stall
    (run / "search.ndjson").write_text("".join(__import__("json").dumps(r) + "\n" for r in old), encoding="utf-8")
    script = tmp_path / "resume_search.py"
    nd = str(run / "search.ndjson")
    lines = ["import json, time",
             f"with open({nd!r}, 'a') as f:",
             "    for i in range(60, 75):",
             "        f.write(json.dumps({'n': i, 'ok': True, 'objective': 3.0 - (i - 59) * 0.01}) + chr(10)); f.flush()",
             "        time.sleep(0.02)"]
    script.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
    job = night.Job(id="res", kind="command", argv=(sys.executable, str(script), "search", "--resume", str(run)),
                    timeout_s=60, watchdog=tuple(sorted(CFG.items())))
    runner = night.NightRunner(repo_root=tmp_path, runs_root=runs, lane="cpu")
    runner.watchdog_poll_s = 0.2
    code, timed_out = runner.run(job, tmp_path / "res.log")
    assert (code, timed_out) == (0, False)                                   # old converged rows ignored
