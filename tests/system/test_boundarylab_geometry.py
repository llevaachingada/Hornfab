"""Vented generation adapter tests (SYS-03/SYS-04 semantics without invoking real BL).

The executor is stubbed (monkeypatch of generate._execute) so tests cover the adapter's
spec construction, argv hygiene, artifact verification, failure mapping and provenance
bookkeeping. The REAL generation path is exercised end-to-end only in the opt-in smoke
(tools/system/bl_smoke.py --generate-smoke --real) or when HORNLAB_BL_REAL_TESTS=1.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, cast

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.system.boundarylab import generate as G  # noqa: E402
from hornlab_search.system.boundarylab.probe import (  # noqa: E402
    BLRoot,
    probe_boundarylab,
)
from hornlab_search.system.boundarylab.run import (  # noqa: E402
    BlockedByGate,
    solve_project,
)
from hornlab_search.system import provenance  # noqa: E402


def make_fake_bl_root(tmp_path: Path) -> BLRoot:
    """Build a verified fake BLRoot with a provider manifest carrying a default_source."""
    root_dir = tmp_path / "boundary-lab"
    (root_dir / "src" / "blab").mkdir(parents=True)
    (root_dir / "pyproject.toml").write_text(
        '[project]\nname = "boundary-lab"\nversion = "9.9.9"\n', encoding="utf-8")
    for rel in ("headless.py", "project_cli.py", "generators/__init__.py", "generators/base.py"):
        path = root_dir / "src" / "blab" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# fixture\n", encoding="utf-8")
    provider = root_dir / "geometry_providers" / "vented_enclosure"
    (provider / "enclosure").mkdir(parents=True)
    defaults = {
        "width_m": 0.32, "height_m": 0.5, "depth_m": 0.36, "wall_m": 0.018,
        "driver_diameter_m": 0.2, "cone_depth_m": 0.04, "surround_width_m": 0.012,
        "cap_diameter_m": 0.05, "driver_y_m": 0.1, "port_length_m": 0.22,
        "port_area_m2": 0.002827433388, "port_nfr": 0.12, "port_roundover_m": 0.008,
        "port_wall_m": 0.003, "port_y_m": -0.13, "mesh_size_m": 0.04, "detail_size_m": 0.012,
    }
    (provider / "provider.json").write_text(json.dumps({
        "manifest_version": 1, "id": "blab.vented_enclosure", "provider_api": 1,
        "backend": "enclosure.backend:create_backend", "default_source": defaults,
    }), encoding="utf-8")
    for rel in ("parameters.py", "worker.py", "backend.py"):
        (provider / "enclosure" / rel).write_text("# fixture\n", encoding="utf-8")
    scripts = root_dir / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "python.exe").write_text("", encoding="utf-8")
    (scripts / "blab.exe").write_text("", encoding="utf-8")
    real_probe = probe_boundarylab(extra_roots=[str(root_dir)], use_default_roots=False)
    assert real_probe.verified_root is not None
    return real_probe.verified_root


# --------------------------------------------------------------------------- source building

def test_unknown_override_key_is_rejected_locally(tmp_path: Path) -> None:
    root = make_fake_bl_root(tmp_path)
    with pytest.raises(ValueError, match="unknown vented-source key"):
        G.generate_vented(root, {"bogus_m": 1.0}, store_root=tmp_path, run_now=False)


def test_override_must_be_numeric(tmp_path: Path) -> None:
    root = make_fake_bl_root(tmp_path)
    with pytest.raises(ValueError, match="must be a number"):
        G.generate_vented(root, {"width_m": cast(Any, "0.3")}, store_root=tmp_path, run_now=False)


def test_dry_run_returns_spec_without_executing(tmp_path: Path) -> None:
    root = make_fake_bl_root(tmp_path)
    result = G.generate_vented(root, {"width_m": 0.30}, store_root=tmp_path, run_now=False)
    assert result.ok is False and result.returncode == -1
    spec = cast(dict, result.detail["spec_dry_run"])
    assert spec["source"]["width_m"] == 0.30
    assert spec["source"]["port_nfr"] == 0.12          # untouched default from the manifest
    assert spec["provider_id"] == "blab.vented_enclosure"
    assert spec["configuration"] == {"symmetry_config": {"mode": "off"}}


# --------------------------------------------------------------------------- execution mapping

def _stub_ok(tmp_path: Path, case_name: str = "bl_output"):
    """Return a (calls, executor) pair simulating a successful BL generation."""
    calls: list[dict] = []

    def executor(argv, deadline_s, cancel_path, max_lines=G._MAX_LOG_LINES):
        spec_path = Path(argv[-1])
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        calls.append({"argv": list(argv), "spec": spec})
        out = Path(spec["case_dir"]) / "bl_output"
        out.mkdir(parents=True)
        for name in ("interior.msh", "exterior.msh"):
            (out / name).write_bytes(b"MESH-CONTENT\n")
        (out / "mesh_info.json").write_text(json.dumps({"volume_m3": 0.05}), encoding="utf-8")
        digest = "a" * 64
        final = {
            "ok": True, "output_dir": str(out),
            "meshes": [
                {"id": "interior", "purpose": "fem_volume", "path": str(out / "interior.msh"),
                 "sha256": digest},
                {"id": "exterior", "purpose": "bem_surface", "path": str(out / "exterior.msh"),
                 "sha256": digest},
            ],
            "mesh_info_sha256": digest,
            "mesh_info": {"volume_m3": 0.05},
            "port_mouth_diameter_m": 0.0527,
        }
        return 0, ["{\"event\":\"status\",\"message\":\"Meshing\"}", json.dumps(final, sort_keys=True)]

    return calls, executor


def test_success_path_records_verified_artifacts_and_manifest(tmp_path: Path, monkeypatch) -> None:
    root = make_fake_bl_root(tmp_path)
    calls, executor = _stub_ok(tmp_path)
    monkeypatch.setattr(G, "_execute", executor)
    result = G.generate_vented(root, {"width_m": 0.30}, store_root=tmp_path)
    assert result.ok is True
    assert result.returncode == 0
    assert len(result.meshes) == 2
    assert result.port_mouth_diameter_m == pytest.approx(0.0527)
    assert (result.case_dir / "manifest.json").is_file()
    # argv hygiene: BL's own python, runner by path, spec by path; no shell string
    argv = calls[0]["argv"]
    assert argv[0].endswith("python.exe")
    assert argv[1] == "-I" and argv[2] == "-B"
    assert argv[3] == str(G.runner_path())
    assert Path(argv[4]).is_file()
    # provenance: BL root, spec hash and the parsed result are recorded
    body = provenance.load_manifest(result.case_dir / "manifest.json")["payload"]
    assert body["kind"] == "boundarylab_vented_generation"
    assert body["bl_root"]["verified"] is True
    assert body["detail"]["spec_sha256"]


def test_missing_mesh_artifact_fails_verification(tmp_path: Path, monkeypatch) -> None:
    root = make_fake_bl_root(tmp_path)
    calls, executor = _stub_ok(tmp_path)

    def executor_without_exterior(argv, deadline_s, cancel_path, max_lines=G._MAX_LOG_LINES):
        code, lines = executor(argv, deadline_s, cancel_path, max_lines)
        final = json.loads(lines[-1])
        final["meshes"] = final["meshes"][:1]  # drop exterior artifact claim
        return code, lines[:-1] + [json.dumps(final, sort_keys=True)]

    monkeypatch.setattr(G, "_execute", executor_without_exterior)
    result = G.generate_vented(root, {}, store_root=tmp_path)
    assert result.ok is False
    assert any("verification failed" in line for line in result.captured_log_tail)


def test_bl_validate_error_becomes_structured_failure(tmp_path: Path, monkeypatch) -> None:
    root = make_fake_bl_root(tmp_path)
    payload = {"ok": False, "error_type": "ValueError",
               "error": "Driver and port must not overlap; leave at least 3 mm clearance.",
               "traceback_tail": ["Traceback..." * 0, "ValueError at validate()"]}
    monkeypatch.setattr(G, "_execute",
                        lambda argv, deadline_s, cancel_path, max_lines=G._MAX_LOG_LINES:
                        (3, [json.dumps(payload, sort_keys=True)]))
    result = G.generate_vented(root, {"driver_y_m": 0.0, "port_y_m": 0.0}, store_root=tmp_path)
    assert result.ok is False and result.returncode == 3
    assert result.manifest_path is not None
    body = provenance.load_manifest(result.case_dir / "manifest.json")["payload"]
    assert body["result"]["ok"] is False
    assert "must not overlap" in body["result"]["error"]


def test_timeout_marks_failure_and_terminates(tmp_path: Path, monkeypatch) -> None:
    root = make_fake_bl_root(tmp_path)
    monkeypatch.setattr(G, "_execute",
                        lambda argv, deadline_s, cancel_path, max_lines=G._MAX_LOG_LINES:
                        (124, ["[adapter] timeout after 0s; terminated"]))
    result = G.generate_vented(root, {}, store_root=tmp_path, timeout_s=0.0)
    assert result.ok is False and result.returncode == 124


# --------------------------------------------------------------------------- solve gate (SYS-gate)

def test_solve_project_refuses_by_default(monkeypatch) -> None:
    monkeypatch.delenv("HORNLAB_BL_ALLOW_SOLVE", raising=False)
    with pytest.raises(BlockedByGate, match="refused by gate"):
        solve_project("whatever")


def test_solve_project_refuses_even_with_env_flag_without_authorization(monkeypatch) -> None:
    monkeypatch.setenv("HORNLAB_BL_ALLOW_SOLVE", "1")
    with pytest.raises(BlockedByGate, match="authorized_by"):
        solve_project("whatever")


def test_solve_project_still_refuses_with_full_authorization(monkeypatch) -> None:
    """Stage 4 solves run with BL's own CLI behind the GPU gate — the adapter stays inert."""
    monkeypatch.setenv("HORNLAB_BL_ALLOW_SOLVE", "1")
    with pytest.raises(BlockedByGate, match="intentionally inert"):
        solve_project("whatever", authorized_by="senior-gate-2026-11-18")


# --------------------------------------------------------------------------- real BL (opt-in)

def test_real_bl_generate_smoke(tmp_path: Path, monkeypatch) -> None:
    """REAL generation through BL's own environment (CPU Gmsh only, no solver).

    Requires HORNLAB_BL_REAL_TESTS=1 and a verified local install; otherwise skips.
    """
    if os.environ.get("HORNLAB_BL_REAL_TESTS", "").strip() != "1":
        pytest.skip("real Boundary Lab generation gated off (set HORNLAB_BL_REAL_TESTS=1)")
    probe = probe_boundarylab(extra_roots=["C:/Users/hunte/Github/boundary-lab"],
                              use_default_roots=False)
    if probe.verified_root is None:
        pytest.skip("verified Boundary Lab not present")
    result = G.generate_vented(
        probe.verified_root,
        {"width_m": 0.30, "height_m": 0.44, "depth_m": 0.32, "mesh_size_m": 0.05,
         "detail_size_m": 0.02},
        store_root=tmp_path, timeout_s=900.0)
    assert result.ok is True, "\n".join(result.captured_log_tail[-20:])
    assert result.meshes and result.manifest_path is not None
    for mesh in result.meshes:
        assert Path(mesh["path"]).stat().st_size > 0
