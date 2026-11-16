"""Offline tests for the completed-study CMA adapter."""
import json
from pathlib import Path
from types import SimpleNamespace
import yaml
import pytest
import hornlab_search.config as config_module

from tools.night_queue import refine_study_cma as tool


@pytest.fixture(autouse=True)
def mock_config_loading(monkeypatch):
    monkeypatch.setattr(config_module, "load_config",
                        lambda path: SimpleNamespace(raw=yaml.safe_load(Path(path).read_text())))


def setup_study(tmp_path):
    package_id = "a" * 64
    study = tmp_path / "study"
    study.mkdir()
    (study / "package.json").write_text(json.dumps({"package_id": package_id}))
    screen = tmp_path / "runs" / ("study-" + package_id[:16]) / "screen"
    screen.mkdir(parents=True)
    config = {"name": "task", "family": "OSSE", "brief": {"name": "b"},
              "bounds": {"L_mm": {"lo": 1, "hi": 2}},
              "objective": {"version": 7}, "search": {"sigma0": 0.2}}
    config_path = tmp_path / "input.yaml"
    config_path.write_text(yaml.safe_dump(config))
    (screen / "config.yaml").write_text(yaml.safe_dump(config))
    (screen / "run.json").write_text(json.dumps({"package_id": package_id, "finished_utc": "done"}))
    (screen / "search.ndjson").write_text(json.dumps({"ok": True, "objective": 3.0,
                                                     "params": {"L_mm": 1.5}}) + "\n")
    return study, screen, config_path, config


def args(tmp_path, study, config):
    return ["--study-root", str(study), "--run-root", str(tmp_path / "runs"), "--config", str(config),
            "--out-config", str(tmp_path / "scratch" / "refined.yaml"), "--seed", "17"]


def test_missing_study_never_launches(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **kw: calls.append(a))
    assert tool.main(args(tmp_path, tmp_path / "absent", tmp_path / "input.yaml")) == 2
    assert not calls


def test_clones_and_forwards_only_after_preflight(tmp_path, monkeypatch):
    study, screen, config_path, original = setup_study(tmp_path)
    calls = []
    def run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout='{"warnings": []}', stderr="")
    monkeypatch.setattr(tool.subprocess, "run", run)
    assert tool.main(args(tmp_path, study, config_path)) == 0
    out = tmp_path / "scratch" / "refined.yaml"
    clone = yaml.safe_load(out.read_text())
    source = out.parent / "refined_study_source"
    assert clone["name"] == original["name"] and clone["bounds"] == original["bounds"]
    assert yaml.safe_load(config_path.read_text()) == original
    assert clone["seed_params"] == {"L_mm": 1.5}
    assert clone["search"] == {"budget": 80, "sigma0": 0.1, "budget_counts": "valid", "max_attempts": 180,
                               "warm_start": {"from_runs": [str(source)], "top_k": 10,
                                              "sigma_from_spread": True}}
    adapted = json.loads((source / "run.json").read_text())
    assert adapted["config"]["bounds"] == original["bounds"]
    assert adapted["source_study_screen"] == str(screen)
    assert "search_preflight.py" in calls[0][1] and calls[1][1] == "search"
    assert calls[1][calls[1].index("--budget") + 1] == "80"
    assert calls[1][calls[1].index("--cma-seed") + 1] == "17"


def test_failed_preflight_never_launches_solver(tmp_path, monkeypatch):
    study, _, config_path, _ = setup_study(tmp_path)
    calls = []
    def run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=1, stdout="", stderr="hard")
    monkeypatch.setattr(tool.subprocess, "run", run)
    assert tool.main(args(tmp_path, study, config_path)) == 1
    assert len(calls) == 1


def test_empty_screen_refuses(tmp_path, monkeypatch):
    study, screen, config_path, _ = setup_study(tmp_path)
    (screen / "search.ndjson").write_text("")
    calls = []
    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **kw: calls.append(a))
    assert tool.main(args(tmp_path, study, config_path)) == 2
    assert not calls


def test_better_matching_cma_seed_is_retained(tmp_path, monkeypatch):
    study, _, config_path, config = setup_study(tmp_path)
    prior = tmp_path / "runs" / "20261116T010101Z-screen-123456"
    prior.mkdir()
    (prior / "run.json").write_text(json.dumps({"config_name": "task", "family": "OSSE",
                                                "config": config}))
    (prior / "search.ndjson").write_text(json.dumps({"ok": True, "objective": 2.0,
                                                    "params": {"L_mm": 1.2}}) + "\n")
    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **kw: SimpleNamespace(
        returncode=0, stdout='{"warnings": []}', stderr=""))
    assert tool.main(args(tmp_path, study, config_path)) == 0
    clone = yaml.safe_load((tmp_path / "scratch" / "refined.yaml").read_text())
    assert clone["seed_params"] == {"L_mm": 1.2}
    assert len(clone["search"]["warm_start"]["from_runs"]) == 2


@pytest.mark.parametrize("clear_on, expected_sigma, expected_code", [(2, 0.075, 0), (None, 0.05, 2)])
def test_low_hits_retries_and_refuses_at_floor(tmp_path, monkeypatch, clear_on, expected_sigma, expected_code):
    study, _, config_path, _ = setup_study(tmp_path)
    calls = []
    def run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[1] == "search":
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        count = len(calls)
        warnings = [] if count == clear_on else [{"code": "low_hits"}]
        return SimpleNamespace(returncode=0, stdout=json.dumps({"warnings": warnings}), stderr="")
    monkeypatch.setattr(tool.subprocess, "run", run)
    assert tool.main(args(tmp_path, study, config_path)) == expected_code
    clone = yaml.safe_load((tmp_path / "scratch" / "refined.yaml").read_text())
    assert clone["search"]["sigma0"] == expected_sigma
    assert any(c[1] == "search" for c in calls) == (expected_code == 0)
