import json
import sys
from types import SimpleNamespace

from tools.night_queue import run_bo_arm as wrapper


def test_refresh_prep_and_execute(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(wrapper, "REPO", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wrapper", "--root", "arm", "--cohort", "new", "--config", "config.yaml", "--refresh-cohort", "--policy", "turbo", "--seed", "7"])
    monkeypatch.setattr(wrapper.subprocess, "call", lambda cmd, **kw: calls.append(cmd) or 0)
    result = {"preflight": {"status": "ok"}, "steps": {"training": "ok"}}
    monkeypatch.setattr(wrapper.subprocess, "run", lambda cmd, **kw: calls.append(cmd) or SimpleNamespace(returncode=0, stdout=json.dumps(result)))
    assert wrapper.main() == 0
    assert calls[0][-2:] == ["--limit", "1024"]
    assert "comparison-80x2" in calls[1]
    assert "--execute" in calls[2]


def test_failed_prep_or_capability_never_executes(monkeypatch, tmp_path):
    monkeypatch.setattr(wrapper, "REPO", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wrapper", "--root", "arm", "--cohort", "new", "--config", "config.yaml", "--refresh-cohort", "--policy", "turbo", "--seed", "7"])
    calls = []
    monkeypatch.setattr(wrapper.subprocess, "call", lambda cmd, **kw: calls.append(cmd) or 0)
    monkeypatch.setattr(wrapper.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1, stdout=""))
    assert wrapper.main() == 1
    monkeypatch.setattr(wrapper.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout=json.dumps({"preflight": {"status": "blocked"}, "steps": {}})))
    assert wrapper.main() == 3
    assert len(calls) == 2


def test_changed_frozen_cohort_fails_before_prep(monkeypatch, tmp_path):
    monkeypatch.setattr(wrapper, "REPO", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wrapper", "--root", "arm", "--cohort", "missing", "--task", "task", "--policy", "scalar", "--seed", "1", "--scores-sha256", "bad", "--catalog-sha256", "bad"])
    monkeypatch.setattr(wrapper.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("unexpected prep")))
    assert wrapper.main() == 2
