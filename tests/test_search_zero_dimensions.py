"""Fable WP 2.2 / D7 truth fix (cloud senior 2026-11-18): a search with zero free dimensions is
refused BEFORE pycma, by the search entry, the CLI and the night queue's ``--dry-run``.

Found 2026-11-18 (docs/evidence/throat_hv_2026-11-18/LOCAL_RESULTS_2026-11-18_part3.md): a
``kind: search`` night job whose config pins every bound reached pycma with ``x0=[]`` and died
``TypeError: ufunc 'isinf' not supported``. A single design is evaluated with ``run``.
Offline: configs are loaded, never meshed or solved.
"""
from __future__ import annotations

import importlib.util
import sys

import pytest
import yaml

from conftest import REPO
from hornlab_search.config import ConfigError, load_config
from hornlab_search.search import cma

SWEEP = REPO / "examples" / "typologies" / "throat_hv_2026-11-18" / "sweep"
PINNED = SWEEP / "throat_hv_sweep_B_ctl.yaml"          # every bound search: false (Phase 1 job)
FREE3 = SWEEP / "throat_hv_B_search40.yaml"            # the Phase 3 search: 3 free keys


def _night_tool():
    spec = importlib.util.spec_from_file_location("run_campaign_night_zero_dim",
                                                  REPO / "tools" / "run_campaign_night.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_free_keys_of_the_real_throat_configs():
    assert cma.free_search_keys(load_config(PINNED)) == []
    assert cma.free_search_keys(load_config(FREE3)) == [
        "hv_onset_frac", "section_exp_ramp", "throat_hv_ratio"]


def test_require_free_dimensions_names_the_run_command():
    with pytest.raises(ConfigError) as exc:
        cma.require_free_dimensions(load_config(PINNED), PINNED)
    text = str(exc.value)
    assert "zero free dimensions" in text and "x0=[]" in text
    assert f"hornlab-search run --config {PINNED} --mode screen" in text
    assert "--mode finalist" in text and "kind: command" in text
    assert cma.require_free_dimensions(load_config(FREE3)) == cma.free_search_keys(load_config(FREE3))


def test_search_entry_refuses_before_writing_anything(tmp_path):
    run_dir = tmp_path / "run"
    with pytest.raises(ConfigError, match="zero free dimensions"):
        cma.search(load_config(PINNED), run_dir, "screen", config_path=PINNED)
    assert not run_dir.exists()


def test_cli_search_refuses_and_leaves_no_run_dir(tmp_path, capsys, monkeypatch):
    from hornlab_search import cli
    monkeypatch.setenv("HORNLAB_BEAT_WORKER_DIR", str(tmp_path / "workers"))
    runs = tmp_path / "runs"
    runs.mkdir()
    rc = cli.main(["search", "--config", str(PINNED), "--runs-dir", str(runs),
                   "--backend", "bempp_cpu", "--budget", "1"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "search REFUSED" in out and "hornlab-search run --config" in out
    assert [p for p in runs.iterdir() if p.is_dir()] == []


def _night(tmp_path, jobs):
    path = tmp_path / "night.yaml"
    path.write_text(yaml.safe_dump({"night": "zero_dim_2026-11-18", "jobs": jobs}), encoding="utf-8")
    return path


def test_night_dry_run_refuses_a_pinned_search_job(tmp_path, capsys):
    night = _night_tool()
    plan = night.load_night(_night(tmp_path, [
        {"id": "pinned", "kind": "search", "config": str(PINNED), "budget": 1, "mode": "screen"},
        {"id": "free", "kind": "search", "config": str(FREE3), "budget": 40, "mode": "screen"},
        {"id": "single", "kind": "command",
         "argv": ["hornlab-search.exe", "run", "--config", str(PINNED), "--mode", "screen"]},
    ]), repo_root=REPO)
    with pytest.raises(ValueError) as exc:
        night.run_night(plan, dry_run=True, repo_root=REPO)
    text = str(exc.value)
    assert "1 search job(s) have zero free dimensions: pinned" in text
    assert text.split("dimensions: ")[1].split(" (")[0].split(", ") == ["pinned"]
    out = capsys.readouterr().out
    assert "ZERO-DIM job pinned" in out and "ZERO-DIM job single" not in out


def test_night_dry_run_also_catches_a_command_job_that_runs_search(tmp_path):
    night = _night_tool()
    plan = night.load_night(_night(tmp_path, [
        {"id": "cmd_search", "kind": "command",
         "argv": ["hornlab-search.exe", "search", f"--config={PINNED}", "--budget", "1"]},
    ]), repo_root=REPO)
    with pytest.raises(ValueError, match="cmd_search"):
        night.run_night(plan, dry_run=True, repo_root=REPO)


def test_night_dry_run_passes_free_search_resume_and_unloadable(tmp_path, capsys):
    night = _night_tool()
    bad = tmp_path / "bad.yaml"
    bad.write_text("x: 1\n", encoding="utf-8")
    resume = tmp_path / "runs" / "r1"
    resume.mkdir(parents=True)
    plan = night.load_night(_night(tmp_path, [
        {"id": "free", "kind": "search", "config": str(FREE3), "budget": 40},
        {"id": "resumed", "kind": "search", "config": str(PINNED), "budget": 5,
         "resume": str(resume)},
        {"id": "unloadable", "kind": "command",
         "argv": ["hornlab-search.exe", "search", "--config", str(bad)]},
    ]), repo_root=REPO)
    assert night.run_night(plan, dry_run=True, repo_root=REPO) == []
    out = capsys.readouterr().out
    assert "NOTE job unloadable: free-dimension check skipped" in out
