"""Hermetic tests for the one-command REAL Boundary Lab lane (no BL invocation).

The real lane itself is exercised manually with ``--real [--solve]``.  These tests cover the
pure plan/request shape, the ``--real`` refusal, and the stage -> solve call order with the
imported functions monkeypatched, so no Boundary Lab, GPU or CPU solve is ever started here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hornlab_search.search import gpulock  # noqa: E402
from hornlab_search.system import reference as REF  # noqa: E402
from hornlab_search.system.boundarylab import run as bl_run  # noqa: E402
from hornlab_search.system.boundarylab import stage as S  # noqa: E402
from hornlab_search.system.boundarylab.probe import BLRoot, BLProbeResult  # noqa: E402
from tools.system import real_bl_lane  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_cpu_lane_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Never write the repository's real CPU-lane marker during tests."""
    runs = tmp_path / "runs"
    runs.mkdir()
    monkeypatch.setattr(gpulock, "_DEFAULT_RUNS", runs)
    monkeypatch.delenv("HORNLAB_CPU_LANE_LOCK_OWNER", raising=False)
    return runs


def _fake_root(tmp_path: Path) -> BLRoot:
    root = tmp_path / "boundary-lab"
    provider = root / "geometry_providers" / "vented_enclosure"
    provider.mkdir(parents=True)
    return BLRoot(
        path=str(root),
        kind="checkout",
        version="0.5.0",
        git_head="a" * 40,
        python_executable=str(root / ".venv" / "Scripts" / "python.exe"),
        cli_entry=str(root / ".venv" / "Scripts" / "blab.exe"),
        provider_dir=str(provider),
        hashes=(),
        missing=(),
        detail={"provider_manifest": {"id": "blab.vented_enclosure", "default_source": {}}},
    )


def _probe_result(root: BLRoot) -> BLProbeResult:
    return BLProbeResult(found=True, roots=(root,), capability_missing=())


def _staged(tmp_path: Path, *, ok: bool = True, valid: bool = True) -> S.StagedProject:
    case = tmp_path / "store" / "system" / "real_bl_lane" / "case"
    case.mkdir(parents=True)
    project = case / "case.blab.json"
    project.write_text("{}", encoding="utf-8")
    return S.StagedProject(
        ok=ok,
        case_dir=case,
        project_path=project if ok else None,
        output_dir=None,
        meshes=(),
        mesh_info=None,
        validation=(bl_run.ValidationResult(
            returncode=0 if valid else 1,
            parsed={"valid": True} if valid else {"valid": False},
            stdout_tail=("{}",),
            stderr_tail=(),
            argv=("blab.exe", "project", "validate", str(project), "--json"),
        ) if ok else None),
        manifest_path=None,
        captured_log_tail=("stage ok",),
        returncode=0 if ok else 1,
        detail={"argv": ["blab-python", "runner_stage.py", "spec.json"]},
    )


# --------------------------------------------------------------------------- plan / request

def test_plan_is_cpu_only_and_targets_the_vented_voltage_port(tmp_path: Path) -> None:
    plan = real_bl_lane.build_plan(store=tmp_path / "store", solve=True, timeout_s=600.0)

    assert plan["real"] is True and plan["gpu"] is False
    assert plan["store"] == str((tmp_path / "store").resolve())
    assert plan["stage"]["function"] == "stage_reference_project"
    assert plan["stage"]["experiment_id"] == real_bl_lane.EXPERIMENT_ID

    request = plan["request"]
    assert request["schema_version"] == 1
    assert request["excitation_port_ids"] == ["vented/voltage"]
    assert request["frequencies_hz"] == [250.0, 700.0, 1100.0]
    assert len(request["probes"]) == 1
    assert request["probes"][0]["id"] == "on_axis_2m"
    assert request["probes"][0]["points_m"] == [[0, 0, 2]]

    assert plan["solve"]["backend"] == "beat_cpu"
    assert plan["solve"]["authorized_by"] == real_bl_lane.AUTHORIZED_BY
    assert plan["solve"]["lock"] == "cpu_lane_lock"
    assert plan["solve"]["gpu"] is False


def test_plan_without_solve_has_no_solve_step(tmp_path: Path) -> None:
    plan = real_bl_lane.build_plan(store=tmp_path / "store", solve=False, timeout_s=30.0)
    assert plan["solve"] is None
    assert plan["gpu"] is False


def test_committed_request_is_shape_valid_and_vented_only() -> None:
    raw = json.loads(real_bl_lane.REQUEST_PATH.read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1
    assert raw["excitation_port_ids"] == ["vented/voltage"]
    assert raw["frequencies_hz"] == [250.0, 700.0, 1100.0]
    assert raw["probes"] == [{
        "id": "on_axis_2m",
        "coordinate_frame": "project",
        "points_m": [[0, 0, 2]],
    }]
    loaded = REF.load_request(real_bl_lane.REQUEST_PATH)
    assert loaded.excitation_port_ids == ("vented/voltage",)
    assert loaded.frequencies_hz == (250.0, 700.0, 1100.0)


def test_parser_exposes_no_gpu_flag() -> None:
    parser = real_bl_lane.build_parser()
    option_strings = {
        option
        for action in parser._actions
        for option in action.option_strings
    }
    assert not any("gpu" in option.lower() for option in option_strings)


# --------------------------------------------------------------------------- refusal

def test_main_refuses_without_real_and_does_not_touch_boundary_lab(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("probe must not run without --real")

    monkeypatch.setattr(real_bl_lane, "probe_boundarylab", _boom)
    store = tmp_path / "untouched-store"

    code = real_bl_lane.main(["--store", str(store)])

    captured = capsys.readouterr()
    assert code == real_bl_lane.RC_REFUSED_NO_REAL
    assert "--real" in captured.err
    assert not store.exists()
    report = json.loads(captured.out)
    assert report["refused"] and "refused" in report["refused"].lower()


def test_main_refuses_when_no_verified_bl_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        real_bl_lane,
        "probe_boundarylab",
        lambda: BLProbeResult(found=False, roots=(), capability_missing=("no BL",)),
    )
    code = real_bl_lane.main(["--real", "--store", str(tmp_path / "store")])
    captured = capsys.readouterr()
    assert code == real_bl_lane.RC_REFUSED_NO_BL
    assert "BL_CAPABILITY_MISSING" in captured.err
    report = json.loads(captured.out)
    assert report["probe"]["status"] == "BL_CAPABILITY_MISSING"
    assert not (tmp_path / "store").exists()


# --------------------------------------------------------------------------- stage -> solve

def test_real_lane_stages_then_solves_under_the_cpu_lane_lock(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _fake_root(tmp_path)
    order: list[str] = []
    seen: dict[str, Any] = {}
    staged = _staged(tmp_path)

    def fake_probe() -> BLProbeResult:
        order.append("probe")
        return _probe_result(root)

    def fake_stage(bl_root: BLRoot, *args: Any, **kwargs: Any) -> S.StagedProject:
        order.append("stage")
        seen["stage_root"] = bl_root.path
        seen["stage_kwargs"] = kwargs
        return staged

    def fake_solve(case_dir: Any, request: Any, **kwargs: Any) -> dict[str, Any]:
        order.append("solve")
        seen["solve_case_dir"] = Path(case_dir)
        seen["solve_request"] = Path(request)
        seen["solve_kwargs"] = kwargs
        # The CPU-lane marker must be held for the duration of the solve.
        assert gpulock.lane_lock_path("cpu").is_file(), "solve ran outside cpu_lane_lock"
        return {
            "status": "complete",
            "run_dir": str(Path(case_dir) / "run"),
            "returncode": 0,
            "argv": ["blab.exe", "project", "solve", str(case_dir)],
            "backend": kwargs.get("backend"),
            "manifest_path": str(Path(case_dir) / "run" / "manifest.json"),
            "record_path": str(Path(case_dir) / "reference_solve.json"),
            "stdout_tail": [],
            "stderr_tail": [],
        }

    monkeypatch.setattr(real_bl_lane, "probe_boundarylab", fake_probe)
    monkeypatch.setattr(real_bl_lane, "stage_reference_project", fake_stage)
    monkeypatch.setattr(real_bl_lane, "reference_solve", fake_solve)

    store = tmp_path / "store"
    code = real_bl_lane.main(["--real", "--solve", "--store", str(store)])

    assert code == real_bl_lane.RC_OK
    assert order == ["probe", "stage", "solve"]
    assert seen["stage_root"] == root.path
    assert seen["stage_kwargs"]["store_root"] == str(store)
    assert seen["stage_kwargs"]["experiment_id"] == real_bl_lane.EXPERIMENT_ID
    assert seen["solve_case_dir"] == staged.case_dir
    assert seen["solve_request"] == real_bl_lane.REQUEST_PATH
    assert seen["solve_kwargs"]["backend"] == "beat_cpu"
    assert seen["solve_kwargs"]["authorized_by"] == real_bl_lane.AUTHORIZED_BY

    report = json.loads(capsys.readouterr().out)
    assert report["argv"] == ["--real", "--solve", "--store", str(store)]
    assert report["gpu"] is False
    assert report["probe"]["status"] == "BL_CAPABILITY_OK"
    assert report["stage"]["case_dir"] == str(staged.case_dir)
    assert report["stage"]["ok"] is True and report["stage"]["valid"] is True
    assert report["stage"]["argv"] == ["blab-python", "runner_stage.py", "spec.json"]
    assert report["solve"]["status"] == "complete"
    assert report["solve"]["run_dir"] == str(staged.case_dir / "run")
    assert not gpulock.lane_lock_path("cpu").is_file()  # lock released after the solve


def test_invalid_stage_skips_the_solve(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _fake_root(tmp_path)

    monkeypatch.setattr(real_bl_lane, "probe_boundarylab", lambda: _probe_result(root))
    monkeypatch.setattr(
        real_bl_lane, "stage_reference_project",
        lambda *_a, **_k: _staged(tmp_path, ok=False, valid=False),
    )

    def _no_solve(*_a: Any, **_k: Any) -> None:
        raise AssertionError("solve must not run after a failed stage")

    monkeypatch.setattr(real_bl_lane, "reference_solve", _no_solve)

    code = real_bl_lane.main(["--real", "--solve", "--store", str(tmp_path / "store")])

    assert code == real_bl_lane.RC_STAGE_FAILED
    report = json.loads(capsys.readouterr().out)
    assert report["stage"]["ok"] is False
    assert report["solve"] is None
    assert "not attempted" in report["refused"]
