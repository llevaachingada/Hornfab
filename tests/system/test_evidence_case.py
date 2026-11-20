"""Tests for the derived evidence-case bridge (no Boundary Lab, no solve)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hornlab_search.system import provenance  # noqa: E402
from tools.system import evidence_case  # noqa: E402


def _source(tmp_path: Path) -> tuple[Path, Path, Path]:
    store = tmp_path / "system_runs"
    case = provenance.new_case_dir("src", store_root=store, tag="case")
    project = {"schema_version": 10, "generator_documents": [
        {"artifact": {"meshes": [{"id": "interior", "mesh_path": "bl_output/x/interior.msh"}]}}
    ]}
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
