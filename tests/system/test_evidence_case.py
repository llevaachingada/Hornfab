"""Tests for the derived evidence-case bridge (no Boundary Lab, no solve)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hornlab_search.system import provenance  # noqa: E402
from tools.system import evidence_case  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_cpu_lane_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Every test locks a temp runs/ dir, never the repository's real CPU-lane marker."""
    from hornlab_search.search import gpulock
    runs = tmp_path / "runs"
    runs.mkdir()
    monkeypatch.setattr(gpulock, "_DEFAULT_RUNS", runs)
    monkeypatch.delenv("HORNLAB_CPU_LANE_LOCK_OWNER", raising=False)
    return runs


def _source(tmp_path: Path) -> tuple[Path, Path, Path]:
    store = tmp_path / "system_runs"
    case = provenance.new_case_dir("src", store_root=store, tag="case")
    project = {"schema_version": 10, "generator_documents": [
        {"artifact": {"meshes": [{"id": "interior", "mesh_path": "bl_output/x/interior.msh"}]}}
    ], "physical_system": {"components": [
        {"id": "vented/driver", "kind": "electrodynamic_transducer",
         "parameters": {"re_ohm": 5.8, "bl_n_per_a": 8.0}}
    ]}, "project_preferences": {
        "freq_min_hz": 20.0, "freq_max_hz": 200.0,
        "spherical_sampling_enabled": False,
        "keep_me": "preserved",
    }}
    (case / "case.blab.json").write_text(json.dumps(project), encoding="utf-8")
    mesh = case / "bl_output" / "x" / "interior.msh"
    mesh.parent.mkdir(parents=True)
    mesh.write_text("mesh\n", encoding="utf-8")
    request = tmp_path / "request.json"
    request.write_text(json.dumps({
        "schema_version": 1,
        "frequencies_hz": [20.0, 50.0, 100.0, 200.0],
        "excitation_port_ids": ["vented/voltage"],
        "probes": [{"id": "on_axis", "coordinate_frame": "project",
                    "points_m": [[0.0, 0.0, 2.0]]}],
        "include_project_observations": True,
    }), encoding="utf-8")
    provenance.write_manifest(case, {
        "kind": "test_source",
        "project": str(case / "case.blab.json"),
        "bl_root": str(tmp_path / "boundary-lab"),
    })
    return store, case, request


def _base_args(store: Path, case: Path, request: Path) -> list[str]:
    return ["--source-case", str(case), "--experiment-id", "ev_test", "--tag", "lf",
            "--request", str(request), "--store", str(store)]


def test_dry_run_writes_nothing(tmp_path: Path, capsys) -> None:
    store, case, request = _source(tmp_path)
    rc = evidence_case.main(_base_args(store, case, request) + ["--dry-run"])
    assert rc == 0
    assert not (store / "system" / "ev_test").exists()
    out = json.loads(capsys.readouterr().out)
    assert out["would_create"] is True
    assert out["frequencies_hz"] == [20.0, 50.0, 100.0, 200.0]


def test_prepare_copies_project_request_and_bl_output(tmp_path: Path, capsys) -> None:
    store, case, request = _source(tmp_path)
    rc = evidence_case.main(_base_args(store, case, request) + ["--prepare-only"])
    assert rc == 0
    new_cases = list((store / "system" / "ev_test").iterdir())
    assert len(new_cases) == 1
    new_case = new_cases[0]
    assert (new_case / "case.blab.json").read_bytes() == (case / "case.blab.json").read_bytes()
    assert (new_case / "request.json").read_bytes() == request.read_bytes()
    assert (new_case / "bl_output" / "x" / "interior.msh").is_file()
    payload = provenance.load_manifest(new_case / "manifest.json")["payload"]
    assert payload["kind"] == "bl_derived_request_case"
    assert payload["source_project_sha256"]
    assert payload["request_sha256"]
    assert payload["authorized_by"] is None
    assert payload["copied_artifacts"] == ["bl_output"]
    assert payload["source_case"].replace("\\", "/").startswith("system/src/")


def test_solve_without_authorization_is_refused_before_writing(tmp_path: Path, capsys) -> None:
    store, case, request = _source(tmp_path)
    rc = evidence_case.main(_base_args(store, case, request) + ["--solve"])
    assert rc == 2
    assert not (store / "system" / "ev_test").exists()
    assert "authorized-by" in capsys.readouterr().err


def test_solve_calls_the_reference_path_with_the_copied_request(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    store, case, request = _source(tmp_path)
    seen: dict[str, object] = {}

    def fake_solve(case_dir, request_path, *, backend, authorized_by, timeout_s=None):
        seen.update(case_dir=Path(case_dir), request_path=Path(request_path),
                    backend=backend, authorized_by=authorized_by)
        return SimpleNamespace(run_dir=Path(case_dir) / "run", status="complete",
                               returncode=0, record_path=Path(case_dir) / "reference_solve.json")

    monkeypatch.setattr(evidence_case.reference, "solve", fake_solve)
    rc = evidence_case.main(_base_args(store, case, request)
                            + ["--solve", "--authorized-by", "owner test"])
    assert rc == 0
    assert seen["backend"] == "beat_cpu"
    assert seen["authorized_by"] == "owner test"
    assert seen["request_path"].name == "request.json"
    assert seen["request_path"].parent == seen["case_dir"]
    payload = provenance.load_manifest(Path(seen["case_dir"]) / "manifest.json")["payload"]
    assert payload["authorized_by"] == "owner test"


def test_solve_refuses_when_the_cpu_lane_is_held(
        _isolated_cpu_lane_lock: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys) -> None:
    # F6: a manual --solve takes the CPU-lane marker. With the shared policy set to refuse, a
    # live holder stops the solve and its command is named in the error.
    runs = _isolated_cpu_lane_lock
    monkeypatch.setenv("HORNLAB_GPU_LOCK", "refuse")
    (runs / ".cpu.lane.lock").write_text(json.dumps({
        "pid": os.getpid(), "user": "lane-test", "command": "night test-holder",
        "start_time": "2026-11-20T00:00:00"}), encoding="utf-8")
    store, case, request = _source(tmp_path)
    rc = evidence_case.main(_base_args(store, case, request)
                            + ["--solve", "--authorized-by", "owner test"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "CPU LANE BUSY" in err and "night test-holder" in err
    new_cases = list((store / "system" / "ev_test").iterdir())
    assert len(new_cases) == 1 and not (new_cases[0] / "run").exists()


def test_motor_patch_is_applied_validated_and_recorded(tmp_path: Path, monkeypatch,
                                                        capsys) -> None:
    store, case, request = _source(tmp_path)
    patch = tmp_path / "motor.json"
    patch.write_text(json.dumps({"component_parameters": {
        "vented/driver": {"re_ohm": 5.4, "bl_n_per_a": 14.1}}}), encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_validate(case_dir, request_path):
        seen["validate_case"] = Path(case_dir)
        return SimpleNamespace(valid=True, as_dict=lambda: {"valid": True})

    def fake_solve(case_dir, request_path, *, backend, authorized_by, timeout_s=None):
        seen["solve_case"] = Path(case_dir)
        return SimpleNamespace(run_dir=Path(case_dir) / "run", status="complete",
                               returncode=0, record_path=Path(case_dir) / "reference_solve.json")

    monkeypatch.setattr(evidence_case.reference, "validate", fake_validate)
    monkeypatch.setattr(evidence_case.reference, "solve", fake_solve)
    rc = evidence_case.main(_base_args(store, case, request)
                            + ["--motor-patch", str(patch), "--solve",
                               "--authorized-by", "owner test"])
    assert rc == 0
    new_case = Path(seen["solve_case"])
    project = json.loads((new_case / "case.blab.json").read_text(encoding="utf-8"))
    params = project["physical_system"]["components"][0]["parameters"]
    assert params["re_ohm"] == 5.4 and params["bl_n_per_a"] == 14.1
    assert (new_case / "motor_patch.json").is_file()
    assert (new_case / "reference_validate.json").is_file()
    payload = provenance.load_manifest(new_case / "manifest.json")["payload"]
    assert payload["motor_patch_component_ids"] == ["vented/driver"]
    assert payload["motor_patch_sha256"]


def test_source_outside_store_is_refused(tmp_path: Path, capsys) -> None:
    store, _case, request = _source(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    rc = evidence_case.main(["--source-case", str(outside), "--experiment-id", "ev_test",
                             "--request", str(request), "--store", str(store)])
    assert rc == 2
    assert "outside the system store" in capsys.readouterr().err


def test_invalid_request_is_refused(tmp_path: Path, capsys) -> None:
    store, case, _request = _source(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema_version": 1, "frequencies_hz": []}), encoding="utf-8")
    rc = evidence_case.main(_base_args(store, case, bad))
    assert rc == 2
    assert "frequencies_hz" in capsys.readouterr().err


# --------------------------------------------------------------------------- project preferences


def _sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_project_preferences_and_balloon_deg_merge_preserve_and_record(
        tmp_path: Path, capsys) -> None:
    store, case, request = _source(tmp_path)
    patch = tmp_path / "prefs.json"
    patch.write_text(json.dumps({
        "polar_observation_distance_m": 2.0,
        "spherical_sampling_enabled": False,   # --balloon-deg must win this convenience key
    }), encoding="utf-8")
    rc = evidence_case.main(_base_args(store, case, request)
                            + ["--project-preferences", str(patch),
                               "--balloon-deg", "5.0", "--prepare-only"])
    assert rc == 0
    new_case = next((store / "system" / "ev_test").iterdir())

    project = json.loads((new_case / "case.blab.json").read_text(encoding="utf-8"))
    prefs = project["project_preferences"]
    # patched keys
    assert prefs["polar_observation_distance_m"] == 2.0
    assert prefs["spherical_sampling_enabled"] is True
    assert prefs["balloon_angle_precision_deg"] == 5.0
    # untouched keys from the source block survive the merge
    assert prefs["freq_min_hz"] == 20.0
    assert prefs["freq_max_hz"] == 200.0
    assert prefs["keep_me"] == "preserved"
    # deterministic write
    assert (new_case / "case.blab.json").read_text(encoding="utf-8") == (
        json.dumps(project, indent=2, sort_keys=True) + "\n")
    assert (new_case / "project_preferences_patch.json").read_bytes() == patch.read_bytes()

    payload = provenance.load_manifest(new_case / "manifest.json")["payload"]
    assert payload["balloon_deg"] == 5.0
    assert payload["project_preferences_patch"] == {
        "polar_observation_distance_m": 2.0,
        "spherical_sampling_enabled": True,
        "balloon_angle_precision_deg": 5.0,
    }
    assert payload["project_preferences_patch_sha256"]
    assert payload["project_preferences_patch_file"] == str(patch.resolve())
    assert payload["project_preferences_patch_file_sha256"] == _sha256(patch)
    assert payload["source_project_sha256"] == _sha256(case / "case.blab.json")
    assert payload["derived_project_sha256"] == _sha256(new_case / "case.blab.json")
    assert payload["derived_project_sha256"] != payload["source_project_sha256"]


def test_project_preferences_validate_runs_before_solve(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    store, case, request = _source(tmp_path)
    calls: list[str] = []
    seen: dict[str, Path] = {}

    def fake_validate(case_dir, request_path):
        calls.append("validate")
        seen["case"] = Path(case_dir)
        return SimpleNamespace(valid=True, as_dict=lambda: {"valid": True})

    def fake_solve(case_dir, request_path, *, backend, authorized_by, timeout_s=None):
        calls.append("solve")
        return SimpleNamespace(run_dir=Path(case_dir) / "run", status="complete",
                               returncode=0, record_path=Path(case_dir) / "reference_solve.json")

    monkeypatch.setattr(evidence_case.reference, "validate", fake_validate)
    monkeypatch.setattr(evidence_case.reference, "solve", fake_solve)
    rc = evidence_case.main(_base_args(store, case, request)
                            + ["--balloon-deg", "5", "--solve",
                               "--authorized-by", "owner test"])
    assert rc == 0
    assert calls == ["validate", "solve"]
    new_case = seen["case"]
    assert (new_case / "reference_validate.json").is_file()
    project = json.loads((new_case / "case.blab.json").read_text(encoding="utf-8"))
    assert project["project_preferences"]["balloon_angle_precision_deg"] == 5.0


@pytest.mark.parametrize("degrees", ["0.4", "15.1"])
def test_balloon_deg_outside_bl_clamp_is_refused(
        tmp_path: Path, capsys, degrees: str) -> None:
    store, case, request = _source(tmp_path)
    rc = evidence_case.main(_base_args(store, case, request)
                            + ["--balloon-deg", degrees, "--prepare-only"])
    assert rc == 2
    assert not (store / "system" / "ev_test").exists()
    err = capsys.readouterr().err
    assert "0.5" in err and "15" in err


def test_project_preferences_must_be_a_json_object(tmp_path: Path, capsys) -> None:
    store, case, request = _source(tmp_path)
    patch = tmp_path / "prefs.json"
    patch.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    rc = evidence_case.main(_base_args(store, case, request)
                            + ["--project-preferences", str(patch), "--prepare-only"])
    assert rc == 2
    assert not (store / "system" / "ev_test").exists()
    assert "JSON object" in capsys.readouterr().err
