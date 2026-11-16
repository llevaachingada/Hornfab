"""Search watchdog (2026-11-16): stop a search job on high refusal rate, no gain, or a stall."""
from __future__ import annotations

import sys
import textwrap
import time
from pathlib import Path

import pytest

import tools.run_campaign_night as night

CFG = dict(night.WATCHDOG_DEFAULTS)


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
