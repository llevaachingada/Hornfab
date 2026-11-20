"""P6 backend: Boundary Lab stage / validate / solve argv, refusal and option readers.

Everything here runs on a throwaway repository shaped like the real tree (a committed example spec
plus an allow-listed full-domain mesh) or reads the real store read-only.  No Boundary Lab staging
is executed, no solve is started, no GPU is touched: the real-BL lane is separate.
"""
from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.gui import data_hw_stage as HWS  # noqa: E402
from hornlab_search.gui import jobs as J  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
STORE = REPO / "system_runs"
COMMITTED_SPEC = REPO / HWS.DEFAULT_SPEC_REL
ENTRY = REPO / "tools" / "system" / "gui_system_job.py"
VENV_PY = REPO / ".venv" / "Scripts" / "python.exe"

MESH_REL = "system/ref_case/horn_full/case1/mesh.msh"


# --------------------------------------------------------------------------- fixtures


def _write_mesh(path: Path, groups: dict[str, int] | None = None) -> Path:
    """A tiny closed box double with named 2D physical groups (test wiring only, not a mesher)."""
    import meshio

    h = 0.1
    points = np.array([
        [-h, -h, -h], [h, -h, -h], [h, h, -h], [-h, h, -h],
        [-h, -h, h], [h, -h, h], [h, h, h], [-h, h, h],
    ], dtype=float)
    wall = [(0, 2, 1), (0, 3, 2), (0, 4, 7), (0, 7, 3), (1, 2, 6), (1, 6, 5),
            (0, 1, 5), (0, 5, 4), (3, 6, 2), (3, 7, 6)]
    throat = [(4, 5, 6), (4, 6, 7)]
    tris = np.array(wall + throat, dtype=np.int64)
    tags = np.array([1] * len(wall) + [2] * len(throat), dtype=np.int32)
    field = groups or {"horn_wall": [1, 2], "horn_throat": [2, 2]}
    mesh = meshio.Mesh(points=points, cells=[("triangle", tris)],
                       cell_data={"gmsh:physical": [tags]}, field_data=field)
    path.parent.mkdir(parents=True, exist_ok=True)
    meshio.write(path, mesh, file_format="gmsh22", binary=False)
    return path


def _mini_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "examples" / "systems").mkdir(parents=True)
    if COMMITTED_SPEC.is_file():
        shutil.copyfile(COMMITTED_SPEC, root / HWS.DEFAULT_SPEC_REL)
    (root / "runs").mkdir()
    (root / "system_runs" / "system" / "exp" / "case").mkdir(parents=True)
    _write_mesh(root / "system_runs" / MESH_REL)
    return root


def _jm(root: Path) -> J.JobManager:
    return J.JobManager(root, root / "runs", system_root=root / "system_runs")


def _stage_args(**over) -> dict:
    args = {"horn_mesh": MESH_REL, "source_group": "horn_throat",
            "translation_z_mm": 20, "experiment_id": "bl_gui_test", "backend": "beat_cpu"}
    args.update(over)
    return args


# --------------------------------------------------------------------------- stage argv


def test_stage_argv_is_cpu_only_and_uses_the_allow_listed_mesh(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    argv, gpu = _jm(root).build_argv("hw-stage", _stage_args())
    assert gpu is False
    assert argv == [
        "stage",
        "--horn-mesh", "system_runs/system/ref_case/horn_full/case1/mesh.msh",
        "--source-group", "horn_throat",
        "--translation-mm", "0", "0", "20",
        "--experiment-id", "bl_gui_test",
        "--out", "system_runs",
    ]
    assert "--backend" not in argv
    assert not any("cuda" in str(x).lower() or "gpu" in str(x).lower() for x in argv)


def test_stage_argv_experiment_id_defaults_to_the_date(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    argv, _ = _jm(root).build_argv("hw-stage", _stage_args(experiment_id=None))
    value = argv[argv.index("--experiment-id") + 1]
    assert value.startswith("bl_gui_") and len(value) == len("bl_gui_") + 8
    assert value[len("bl_gui_"):].isdigit()


def test_stage_argv_forwards_concrete_overrides_only(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    argv, _ = _jm(root).build_argv(
        "hw-stage", _stage_args(overrides={"width_m": 0.3712, "wall_m": 0.018}))
    payload = json.loads(argv[argv.index("--overrides") + 1])
    assert payload == {"width_m": 0.3712, "wall_m": 0.018}


def test_stage_argv_rejects_a_clearance_choice(tmp_path: Path) -> None:
    # F5: the R16 minimum is a fixed gate, not a dialog knob that silently does nothing.
    root = _mini_repo(tmp_path)
    with pytest.raises(J.JobError, match="clearance: fixed at the R16 1 mm minimum"):
        _jm(root).build_argv("hw-stage", _stage_args(clearance_m=0.002))


def test_stage_argv_accepts_an_absolute_allow_listed_mesh(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    absolute = (root / "system_runs" / MESH_REL).resolve()
    argv, _ = _jm(root).build_argv("hw-stage", _stage_args(horn_mesh=str(absolute)))
    assert argv[argv.index("--horn-mesh") + 1] == \
        "system_runs/system/ref_case/horn_full/case1/mesh.msh"


# --------------------------------------------------------------------------- stage refusals


@pytest.mark.parametrize("mesh", [
    "outside/mesh.msh",                       # outside the store
    "system/other/mesh.msh",                  # inside the store, outside ref_case/horn_full
    "../outside/mesh.msh",                    # traversal that resolves outside the allow-list
    "system/ref_case/horn_full/case1/other.msh",
    "",
    None,
])
def test_stage_refuses_a_mesh_outside_the_allow_list(tmp_path: Path, mesh) -> None:
    root = _mini_repo(tmp_path)
    _write_mesh(root / "outside" / "mesh.msh")
    _write_mesh(root / "system_runs" / "system" / "other" / "mesh.msh")
    with pytest.raises(J.JobError, match="horn_mesh"):
        _jm(root).build_argv("hw-stage", _stage_args(horn_mesh=mesh))


def test_stage_refuses_a_group_the_mesh_does_not_have(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    with pytest.raises(J.JobError, match="source_group"):
        _jm(root).build_argv("hw-stage", _stage_args(source_group="not_a_group"))


@pytest.mark.parametrize("value", [-101, 201, 1000, "abc", True])
def test_stage_refuses_an_out_of_range_translation(tmp_path: Path, value) -> None:
    root = _mini_repo(tmp_path)
    with pytest.raises(J.JobError, match="translation_z_mm"):
        _jm(root).build_argv("hw-stage", _stage_args(translation_z_mm=value))


@pytest.mark.parametrize("value", ["a/b", "../x", "a..b", "x" * 122, "with space"])
def test_stage_refuses_a_bad_experiment_id(tmp_path: Path, value) -> None:
    root = _mini_repo(tmp_path)
    with pytest.raises(J.JobError, match="experiment_id"):
        _jm(root).build_argv("hw-stage", _stage_args(experiment_id=value))


def test_stage_refuses_a_non_cpu_backend(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    with pytest.raises(J.JobError, match="backend"):
        _jm(root).build_argv("hw-stage", _stage_args(backend="beat_cuda"))


# --------------------------------------------------------------------------- validate argv


def test_validate_argv_points_at_an_existing_case(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    argv, gpu = _jm(root).build_argv("hw-validate", {"case": "exp/case"})
    assert gpu is False
    assert argv == ["validate", "system_runs/system/exp/case"]


@pytest.mark.parametrize("case", [
    "exp", "exp/case/extra", "../x/case", "exp/..", "exp/ca se", "", None,
])
def test_validate_refuses_a_bad_case_key(tmp_path: Path, case) -> None:
    root = _mini_repo(tmp_path)
    with pytest.raises(J.JobError, match="case"):
        _jm(root).build_argv("hw-validate", {"case": case})


def test_validate_refuses_a_missing_case(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    with pytest.raises(J.JobError, match="case"):
        _jm(root).build_argv("hw-validate", {"case": "exp/absent"})


# --------------------------------------------------------------------------- solve refusal (gate D)


def test_solve_is_refused_without_the_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(HWS.ENV_ALLOW_SOLVE, raising=False)
    root = _mini_repo(tmp_path)
    with pytest.raises(J.JobError, match="decision 6"):
        _jm(root).build_argv("hw-solve", {"case": "exp/case", "preset": "wide25"})


def test_solve_is_refused_with_the_env_var_when_no_decision_is_recorded(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(HWS.ENV_ALLOW_SOLVE, "1")
    root = _mini_repo(tmp_path)                     # no readiness registry -> no recorded decision
    with pytest.raises(J.JobError, match="decision 6"):
        _jm(root).build_argv("hw-solve", {"case": "exp/case", "preset": "wide25"})


def test_the_real_registry_still_refuses_the_solve(monkeypatch: pytest.MonkeyPatch) -> None:
    if not (REPO / HWS.READINESS_REL).is_file():
        pytest.skip("readiness registry absent")
    monkeypatch.setenv(HWS.ENV_ALLOW_SOLVE, "1")
    state = HWS.authorization_state(REPO)
    assert state["allowed"] is False
    assert "decision 6" in state["reason"]
    assert state["decision_recorded"] is False


def test_solve_refuses_an_unknown_preset(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    with pytest.raises(J.JobError, match="preset"):
        _jm(root).build_argv("hw-solve", {"case": "exp/case", "preset": "wide99"})


# --------------------------------------------------------------------------- authorization state


def test_authorization_state_shape() -> None:
    state = HWS.authorization_state(REPO)
    assert state["allowed"] is False
    assert state["reason"] == HWS.DECISION_REASON
    assert state["env_var"] == "HORNLAB_GUI_ALLOW_BL_SOLVE"
    assert "decision 6" in state["reason"]


# --------------------------------------------------------------------------- stage options


def test_stage_options_reads_the_allow_listed_meshes_and_groups() -> None:
    if not (STORE / "system" / "ref_case" / "horn_full").is_dir():
        pytest.skip("canonical system store is absent")
    options = HWS.stage_options(REPO, STORE)
    assert options["horn_meshes"], "recorded full-domain meshes must be listed"
    for mesh in options["horn_meshes"]:
        assert mesh["rel"].startswith("system/ref_case/horn_full/")
        assert mesh["rel"].endswith("/mesh.msh")
        assert mesh["groups"], "groups are read from the mesh file"
        assert mesh["triangles"] and mesh["triangles"] > 0
    assert any("SD1D1001" in m["groups"] for m in options["horn_meshes"])
    assert options["default_experiment_id"].startswith("bl_gui_")
    assert "clearance_m" not in options
    assert "1 mm" in options["clearance_note"]
    assert options["defaults"]["source"] == HWS.DEFAULT_SPEC_REL.as_posix()
    assert options["defaults"]["box"]["wall_mm"] == 18.0


def test_stage_options_never_reads_outside_the_allow_list(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    store = root / "system_runs"
    _write_mesh(store / MESH_REL)
    _write_mesh(store / "system" / "other" / "mesh.msh")
    _write_mesh(root / "outside" / "mesh.msh")
    options = HWS.stage_options(root, store)
    assert [m["rel"] for m in options["horn_meshes"]] == [MESH_REL]
    assert options["horn_meshes"][0]["groups"] == ["horn_throat", "horn_wall"]


# --------------------------------------------------------------------------- previews


def test_stage_preview_uses_the_real_entry_script(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    preview = _jm(root).preview("hw-stage", _stage_args())
    assert preview["gpu"] is False
    assert preview["entry"] == J.HW_ENTRY
    assert preview["command"].startswith("python tools/system/gui_system_job.py stage ")
    assert "--horn-mesh system_runs/system/ref_case/horn_full/case1/mesh.msh" in preview["command"]


def test_stage_preview_helper_matches_build_argv(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    jm = _jm(root)
    argv, _ = jm.build_argv("hw-stage", _stage_args())
    assert HWS.stage_preview(root, root / "system_runs", _stage_args())["argv"] == argv


# --------------------------------------------------------------------------- presets


def _write_recorded_run(case_dir: Path, freqs: list[float], seconds: float = 30.0) -> None:
    """A run/manifest.json shaped like the real reader's input (test wiring, not a solve)."""
    run = case_dir / "run"
    run.mkdir(parents=True)
    started = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    finished = started + datetime.timedelta(seconds=seconds)
    (run / "manifest.json").write_text(json.dumps({
        "status": "complete",
        "frequencies_hz": freqs,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": finished.isoformat(),
    }), encoding="utf-8")


def test_solve_presets_are_sourced_from_the_recorded_runs(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    store = root / "system_runs"
    _write_recorded_run(store / "system" / "proj_smoke" / "case_a", [250.0, 700.0, 1100.0], 12.0)
    _write_recorded_run(store / "system" / "proj_wide" / "case_b",
                        HWS._log_grid(200.0, 2500.0, 25), 150.0)
    data = HWS.solve_presets(root, store)
    assert [p["id"] for p in data["presets"]] == list(HWS.SOLVE_PRESETS)
    smoke, wide, low = data["presets"]
    # The grids come from the recorded manifests, never from a JS or Python constant.
    assert smoke["frequencies_hz"] == [250.0, 700.0, 1100.0]
    assert smoke["frequency_count"] == 3
    assert smoke["recorded_runs"] == ["proj_smoke/case_a"]
    assert smoke["estimate_text"].startswith("about 12 s")
    assert wide["frequency_count"] == 25
    assert min(wide["frequencies_hz"]) == 200.0 and max(wide["frequencies_hz"]) == 2500.0
    assert wide["recorded_runs"] == ["proj_wide/case_b"]
    # No LF run in the synthetic store: the documented R3 grid is offered, the estimate stays
    # unavailable, and no number is fabricated from the wide runs.
    assert low["frequency_count"] == 12
    assert low["band_hz"] == [20.0, 200.0]
    assert low["recorded_runs"] == []
    assert "unavailable" in low["estimate_text"]


def test_live_lowband_estimate_is_available_now_lf_runs_exist() -> None:
    if not STORE.is_dir():
        pytest.skip("canonical system store is absent")
    low = next(p for p in HWS.solve_presets(REPO, STORE)["presets"]
               if p["id"] == "lowband12")
    if not low["recorded_runs"]:
        pytest.skip("no LF run recorded in this store yet")
    # A fact that only grows with the evidence queue: the R3 preset now has a recorded estimate.
    assert low["frequency_count"] == 12
    assert low["band_hz"] == [20.0, 200.0]
    assert low["frequencies_source"].startswith("recorded run ")
    assert "unavailable" not in low["estimate_text"]


def test_solve_presets_say_unavailable_when_no_run_is_recorded(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "system_runs").mkdir(parents=True)
    data = HWS.solve_presets(root, root / "system_runs")
    for preset in data["presets"]:
        if preset["id"] == "lowband12":
            assert preset["frequencies_hz"] is not None
        else:
            assert preset["frequencies_hz"] is None
        assert "unavailable" in preset["estimate_text"]


# --------------------------------------------------------------------------- entry script


def test_entry_script_stage_help_runs_under_the_venv_python() -> None:
    if not VENV_PY.is_file() or not ENTRY.is_file():
        pytest.skip("venv interpreter or entry script is absent")
    proc = subprocess.run([str(VENV_PY), str(ENTRY), "stage", "--help"], cwd=str(REPO),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert proc.returncode == 0, proc.stderr
    first = proc.stdout.splitlines()[0]
    assert first.startswith("gui_system_job argv: stage --help")
    assert "prepare" in proc.stdout
