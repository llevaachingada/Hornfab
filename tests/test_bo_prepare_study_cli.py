"""CLI contract tests for ``tools/bo_compare/prepare_study.py`` (no BoTorch, no real cohort build).

The positive paths monkeypatch the training-set builder, the study service, the artifact builders and
:func:`prepare_run_package`, so these tests only assert the staged spec shape and the selected budget
profile never leave the CPU or touch a study registry root beyond ``tmp_path``.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "tools" / "bo_compare" / "prepare_study.py"
CONFIG = (REPO / "examples" / "typologies" / "campaign_2026-10-26_v4"
          / "native__ath_core_v4.yaml")
BRIEF = (REPO / "examples" / "briefs" / "campaign_2026-10-26_v4"
         / "native_ath_core_2in_v4.yaml")
TASK_NAME = "p80x60__osse_ext_throat_home700_v7_seed5678"


def _load_tool():
    spec = importlib.util.spec_from_file_location("bo_prepare_study_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


prepare_study = _load_tool()


@pytest.fixture
def cohort(tmp_path):
    cohort_dir = tmp_path / "cohort"
    cohort_dir.mkdir()
    (cohort_dir / "offline_scores.json").write_text("{}", encoding="utf-8")
    (cohort_dir / "catalog.csv").write_text("root,shard_index,row\n", encoding="utf-8")
    return cohort_dir


def _base_args(tmp_path, cohort):
    return ["--root", str(tmp_path / "study"), "--cohort", str(cohort),
            "--seed", "1", "--label", "unit"]


class _FakeTrainingSet:
    status = "ok"
    n = 500


class _FakeService:
    def __init__(self, root):
        self.root = root
        self.specs = []

    def create_study(self, spec, key):
        self.specs.append(spec)
        return {"id": "sid"}


def _patch_positive(monkeypatch, captured):
    import hornlab_search.bo.data as bo_data
    import hornlab_search.studies.builders as builders
    import hornlab_search.studies.package as package_mod
    import hornlab_search.studies.production as production
    import hornlab_search.studies.service as service_mod

    services = []

    def fake_service(root):
        service = _FakeService(root)
        services.append(service)
        return service

    def fake_prepare(service, sid, **kwargs):
        captured["prepare_kwargs"] = kwargs
        return {"package_id": "pid", "study_id": sid,
                "budget": {"screen_calls": 1, "verify_calls": 1, "total_calls": 2,
                           "attempts": 1},
                "budget_profile": kwargs.get("budget_profile"),
                "lane": kwargs.get("lane"), "deadline": kwargs.get("deadline")}

    monkeypatch.setattr(bo_data, "build_native_training_set",
                        lambda *args, **kwargs: _FakeTrainingSet())
    monkeypatch.setattr(builders, "_read_task",
                        lambda task, *, root: {"config": "patched-config.yaml"})
    for name in ("freeze_snapshot", "build_training", "build_analysis", "build_proposal"):
        monkeypatch.setattr(builders, name, lambda *args, **kwargs: {"status": "ok"})
    monkeypatch.setattr(package_mod, "prepare_run_package", fake_prepare)
    monkeypatch.setattr(production, "execution_capability",
                        lambda *args, **kwargs: {"status": "ok"})
    monkeypatch.setattr(service_mod, "StudyService", fake_service)
    captured["services"] = services


# ------------------------------------------------------------------ explicit refusals


def test_builders_step_failure_returns_one_and_names_the_step(tmp_path, cohort, monkeypatch, capsys):
    """WP 0.7 hardening (2026-11-18): a builders-step death used to exit bare rc=1 with NO cause
    line in the unbuffered job log (t_klame_turbo100/_scalar100 burned ~40 GPU minutes this way).
    The guard must name the failed step and surface the traceback before exiting."""
    import hornlab_search.studies.builders as builders
    captured = {}
    _patch_positive(monkeypatch, captured)

    def boom(service, sid, *, root):
        raise RuntimeError("cohort shard exploded")

    monkeypatch.setattr(builders, "build_training", boom)
    code = prepare_study.main(_base_args(tmp_path, cohort) + ["--config", str(CONFIG)])
    assert code == 1
    err = capsys.readouterr().err
    assert "builders step boom FAILED for study sid" in err   # names the failed step (fn.__name__)
    assert "cohort shard exploded" in err                     # and the traceback follows


def test_refuses_task_and_config_together(tmp_path, cohort, capsys):
    code = prepare_study.main(_base_args(tmp_path, cohort) + [
        "--task", TASK_NAME, "--config", str(CONFIG)])
    assert code == 2
    assert "either --task or --config" in capsys.readouterr().err


def test_refuses_brief_without_config(tmp_path, cohort, capsys):
    code = prepare_study.main(_base_args(tmp_path, cohort) + [
        "--task", TASK_NAME, "--brief", str(BRIEF)])
    assert code == 2
    assert "--brief requires --config" in capsys.readouterr().err


def test_refuses_unknown_budget_profile(tmp_path, cohort, capsys):
    code = prepare_study.main(_base_args(tmp_path, cohort) + [
        "--task", TASK_NAME, "--budget-profile", "comparison-40"])
    assert code == 2
    err = capsys.readouterr().err
    assert "unknown --budget-profile 'comparison-40'" in err
    assert "comparison-25" in err and "comparison-30" in err and "comparison-60" in err


def test_missing_task_and_config_keeps_the_legacy_default_task(tmp_path, cohort, monkeypatch):
    """The 15 Nov night files omit --task; they must keep working on the historical default."""
    captured = {}
    _patch_positive(monkeypatch, captured)
    code = prepare_study.main(_base_args(tmp_path, cohort))
    assert code == 0
    spec = captured["services"][-1].specs[-1]
    assert spec["task"] == {"name": prepare_study.DEFAULT_TASK}
    assert prepare_study.DEFAULT_TASK == "p80x60__osse_ext_throat_home700_v7_seed5678"


# ------------------------------------------------------------------ staged spec shape


def test_config_and_brief_stage_the_explicit_task_tuple(tmp_path, cohort, monkeypatch):
    captured = {}
    _patch_positive(monkeypatch, captured)
    code = prepare_study.main(_base_args(tmp_path, cohort) + [
        "--config", str(CONFIG), "--brief", str(BRIEF),
        "--budget-profile", "comparison-25"])
    assert code == 0
    spec = captured["services"][-1].specs[-1]
    assert spec["task"] == {"config": str(CONFIG.resolve()), "brief": str(BRIEF.resolve())}
    assert captured["prepare_kwargs"]["budget_profile"] == "comparison-25"
    assert json.loads((tmp_path / "study" / "package.json").read_text(encoding="utf-8"))[
        "budget_profile"] == "comparison-25"


def test_config_without_brief_resolves_the_config_brief_file(tmp_path, cohort, monkeypatch):
    captured = {}
    _patch_positive(monkeypatch, captured)
    code = prepare_study.main(_base_args(tmp_path, cohort) + ["--config", str(CONFIG)])
    assert code == 0
    task = captured["services"][-1].specs[-1]["task"]
    assert task["config"] == str(CONFIG.resolve())
    assert Path(task["brief"]).is_file()
    assert Path(task["brief"]).name == "native_ath_core_2in_v4.yaml"


def test_task_name_keeps_the_registry_shape_and_default_profile(tmp_path, cohort, monkeypatch):
    captured = {}
    _patch_positive(monkeypatch, captured)
    code = prepare_study.main(_base_args(tmp_path, cohort) + ["--task", TASK_NAME])
    assert code == 0
    spec = captured["services"][-1].specs[-1]
    assert spec["task"] == {"name": TASK_NAME}
    assert captured["prepare_kwargs"]["budget_profile"] == "comparison-60"
