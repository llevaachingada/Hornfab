"""The night BO-arm wrapper. 2026-11-18 hardening (WP 0.7): the wrapper streams the prepare
child's stdout via subprocess.Popen and, on a nonzero child rc, echoes the child tail for the
night ledger. The two tests below used to mock only subprocess.call/run — they passed when a
sibling test leaked a Popen stub and failed standalone (the two known order-dependent failures,
test_night_bo_arm_wrapper). They now mock the real child surface and pin the streaming + context
contract; no assertion is loosened."""
import io
import json
import sys
from types import SimpleNamespace

from tools.night_queue import run_bo_arm as wrapper


def _fake_popen(monkeypatch, rc, out_lines):
    stdout = io.StringIO("".join(out_lines))
    stdout.seek(0)
    proc = SimpleNamespace(stdout=stdout, wait=lambda *a, **k: rc, returncode=rc)
    monkeypatch.setattr(wrapper.subprocess, "Popen", lambda cmd, **kw: proc)
    return proc


def test_refresh_prep_and_execute(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(wrapper, "REPO", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wrapper", "--root", "arm", "--cohort", "new", "--config", "config.yaml", "--refresh-cohort", "--policy", "turbo", "--seed", "7"])
    monkeypatch.setattr(wrapper.subprocess, "call", lambda cmd, **kw: calls.append(cmd) or 0)
    result = {"preflight": {"status": "ok"}, "steps": {"training": "ok"}}
    _fake_popen(monkeypatch, 0, [json.dumps(result) + "\n"])
    assert wrapper.main() == 0
    assert calls[0][-2:] == ["--limit", "1024"]          # the refresh call
    # prepare now streams through subprocess.Popen (mocked above), so the remaining call is the run
    assert calls[1].count("--root") == 1
    assert calls[1][calls[1].index("--root") + 1] == "arm"
    assert "--package" in calls[1] and "package.json" in calls[1] and "--execute" in calls[1]


def test_failed_prep_or_capability_never_executes(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(wrapper, "REPO", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wrapper", "--root", "arm", "--cohort", "new", "--config", "config.yaml", "--refresh-cohort", "--policy", "turbo", "--seed", "7"])
    calls = []
    monkeypatch.setattr(wrapper.subprocess, "call", lambda cmd, **kw: calls.append(cmd) or 0)
    # prepare child fails rc=1 -> wrapper returns 1 WITH the child tail in its output
    _fake_popen(monkeypatch, 1, ["training rows: 200 (min 100)\n", "prepare_study: builders step build_training FAILED\n"])
    assert wrapper.main() == 1
    err = capsys.readouterr().err
    assert "child failed rc=1" in err and "child|" in err and "builders step build_training" in err
    monkeypatch.setattr(wrapper.subprocess, "Popen", lambda *a, **k: SimpleNamespace(
        stdout=io.StringIO(json.dumps({"preflight": {"status": "blocked"}, "steps": {}}) + "\n"),
        wait=lambda *a, **k: 0, returncode=0))
    assert wrapper.main() == 3
    assert len(calls) == 2            # two main() runs x one refresh call; execution never ran


def test_changed_frozen_cohort_fails_before_prep(monkeypatch, tmp_path):
    monkeypatch.setattr(wrapper, "REPO", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wrapper", "--root", "arm", "--cohort", "missing", "--task", "task", "--policy", "scalar", "--seed", "1", "--scores-sha256", "bad", "--catalog-sha256", "bad"])
    monkeypatch.setattr(wrapper.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("unexpected prep")))
    monkeypatch.setattr(wrapper.subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("unexpected prep")))
    assert wrapper.main() == 2
