"""Offline tests for the no-GUI Boundary Lab reference-case workflow (Lane D).

The real Boundary Lab staging/validate/solve paths stay behind the established
``HORNLAB_BL_REAL_TESTS=1`` gate. Offline tests cover the typed workflow seam:

* prepare's case-directory layout, immutable manifest, geometry id and blockers;
* graph extraction/assertions against the small synthetic result fixture;
* request-overlay shape refusals;
* solve refusal without ``authorized_by`` and the exact BL argv;
* report recomposition math (polarity is an exact +/-1, delay is ``exp(-i omega tau)`` with no
  conjugation) and the honesty labels.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.system import cli  # noqa: E402
from hornlab_search.system import contracts as C  # noqa: E402
from hornlab_search.system import dsp as SYSDSP  # noqa: E402
from hornlab_search.system import provenance  # noqa: E402
from hornlab_search.system import reference as REF  # noqa: E402
from hornlab_search.system.boundarylab import bl_results as R  # noqa: E402
from hornlab_search.system.boundarylab import run as bl_run  # noqa: E402
from hornlab_search.system.boundarylab import stage as S  # noqa: E402
from hornlab_search.system.boundarylab.probe import BLRoot, probe_boundarylab  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "bl_results" / "reference_run"
REPO = Path(__file__).resolve().parents[2]
REAL_BL_ROOT = "C:/Users/hunte/Github/boundary-lab"
SMOKE_CASE = (REPO / "system_runs" / "system" / "bl_smoke"
              / "20261118T225108Z-smoke-42536-01d15001")


# --------------------------------------------------------------------------- helpers

def _fake_root(tmp_path: Path) -> BLRoot:
    return BLRoot(
        path=str(tmp_path / "boundary-lab"),
        kind="checkout",
        version="0.5.0",
        git_head="a" * 40,
        python_executable=str(tmp_path / "boundary-lab" / ".venv" / "Scripts" / "python.exe"),
        cli_entry=str(tmp_path / "boundary-lab" / ".venv" / "Scripts" / "blab.exe"),
        provider_dir=str(tmp_path / "boundary-lab" / "geometry_providers" / "vented_enclosure"),
        hashes=(),
        missing=(),
        detail={"provider_manifest": {"id": "blab.vented_enclosure", "default_source": {}}},
    )


def _fake_project(*, regions: int = 2, interfaces: int = 1) -> dict[str, Any]:
    return {
        "physical_system": {
            "id": "system:loudspeaker",
            "region_ids": ["vented/interior", "vented/exterior"][:regions],
            "regions": [
                {"id": "vented/interior", "kind": "bounded_air"},
                {"id": "vented/exterior", "kind": "unbounded_air"},
            ][:regions],
            "interfaces": [{"id": "vented/port_interface"}][:interfaces],
            "excitation_ports": [
                {"id": "vented/voltage", "kind": "voltage"},
                {"id": "excitation:horn", "kind": "normal_velocity"},
            ],
            "meshes": [
                {"id": "vented/mesh/interior", "purpose": "fem_volume", "scale_to_m": 1.0},
                {"id": "vented/mesh/exterior", "purpose": "bem_surface", "scale_to_m": 1.0},
                {"id": "mesh:horn", "purpose": "bem_surface", "scale_to_m": 1.0},
            ],
            "components": [
                {"id": "vented/driver", "kind": "electrodynamic_transducer"},
                {"id": "component:horn", "kind": "ideal_velocity_source"},
            ],
        }
    }


def _install_fake_stage(monkeypatch, *, has_horn: bool) -> dict[str, Any]:
    calls: dict[str, Any] = {}

    def common(root: BLRoot, kwargs: dict[str, Any], horn: Path | None):
        case_dir = kwargs.get("case_dir")
        spec = {
            "provider_id": "blab.vented_enclosure",
            "source": {"width_m": 0.32},
            "horn": (None if horn is None else {
                "mesh_path": str(horn), "source_group": kwargs.get("source_group"),
                "mesh_role": kwargs.get("mesh_role", "full_domain"),
                "scale_factor": kwargs.get("scale_factor", 1.0),
                "translation_mm": [0.0, 0.0, 20.0],
            }),
        }
        if not kwargs.get("run_now", True):
            return S.StagedProject(
                ok=False, case_dir=Path(case_dir) if case_dir else Path("dry"),
                project_path=None, output_dir=None, meshes=(), mesh_info=None,
                validation=None, manifest_path=None, captured_log_tail=(), returncode=-1,
                detail={"spec_dry_run": spec},
            )
        case = Path(case_dir) if case_dir else (
            Path(kwargs["store_root"]) / "system"
            / str(kwargs.get("experiment_id") or "bl_ref_case") / "case")
        case.mkdir(parents=True, exist_ok=True)
        project = case / "case.blab.json"
        project.write_text(json.dumps(_fake_project(), indent=2, sort_keys=True), encoding="utf-8")
        manifest = provenance.write_manifest(case, {
            "kind": "bl_stage_horn_project" if horn is not None else "bl_stage_reference_project",
            "bl_root": root.to_dict(),
            "spec": spec,
        })
        validation = bl_run.ValidationResult(
            returncode=0, parsed={"valid": True}, stdout_tail=("{}",), stderr_tail=(),
            argv=("blab.exe", "project", "validate", str(project), "--json"),
        )
        return S.StagedProject(
            ok=True, case_dir=case, project_path=project, output_dir=None,
            meshes=({"id": "interior", "purpose": "fem_volume", "sha256": "b" * 64},),
            mesh_info={"air_volume_m3": 0.042},
            validation=validation, manifest_path=manifest, captured_log_tail=(),
            returncode=0, detail={"spec_dry_run": spec},
        )

    if has_horn:
        def fake_horn(root, horn_mesh, **kwargs):
            calls.update(kwargs)
            return common(root, kwargs, Path(horn_mesh))
        monkeypatch.setattr(S, "stage_horn_project", fake_horn)
    else:
        def fake_vented(root, overrides=None, **kwargs):
            calls.update(kwargs)
            return common(root, kwargs, None)
        monkeypatch.setattr(S, "stage_reference_project", fake_vented)
    return calls


def _copy_run_case(tmp_path: Path) -> Path:
    case = tmp_path / "case"
    shutil.copytree(FIXTURE, case / "run")
    return case


def _fixture_compiled() -> dict[str, Any]:
    return json.loads((FIXTURE / "compiled-system.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- prepare

def test_prepare_writes_layout_geometry_id_and_blockers(tmp_path: Path, monkeypatch) -> None:
    _install_fake_stage(monkeypatch, has_horn=False)
    root = _fake_root(tmp_path)
    prepared = REF.prepare(root, store_root=tmp_path / "store", experiment_id="ref")

    assert prepared.ok is True and prepared.valid is True
    assert prepared.stage_kind == "bl_stage_reference_project"
    assert prepared.case_dir.is_dir()
    assert (prepared.case_dir / "case.blab.json").is_file()
    assert (prepared.case_dir / "manifest.json").is_file()
    assert prepared.record_path is not None
    assert prepared.record_path.name == "reference_prepare.json"
    assert len(prepared.assembly_geometry_id) == 16

    record = json.loads(prepared.record_path.read_text(encoding="utf-8"))
    payload = record["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    assert payload["kind"] == "bl_reference_case"
    assert payload["assembly_geometry_id"] == prepared.assembly_geometry_id
    assert payload["project_sha256"]
    assert payload["stage_manifest_sha256"]
    assert REF.BLOCKED_BY_FULL_DOMAIN_HORN_MESH_INPUT in payload["blockers"]


def test_prepare_is_immutable_and_never_reuses_a_case_directory(tmp_path: Path, monkeypatch) -> None:
    _install_fake_stage(monkeypatch, has_horn=False)
    root = _fake_root(tmp_path)
    prepared = REF.prepare(root, store_root=tmp_path / "store", experiment_id="ref")
    manifest = prepared.case_dir / "manifest.json"
    before = manifest.read_bytes()

    with pytest.raises(REF.ReferenceError, match="REFERENCE_CASE_EXISTS"):
        REF.prepare(root, case_dir=prepared.case_dir)
    assert manifest.read_bytes() == before  # the staging manifest was not touched


def test_prepare_dry_run_creates_nothing(tmp_path: Path, monkeypatch) -> None:
    _install_fake_stage(monkeypatch, has_horn=False)
    root = _fake_root(tmp_path)
    prepared = REF.prepare(root, store_root=tmp_path / "store", run_now=False)
    assert prepared.ok is False
    assert prepared.record_path is None
    assert REF.BLOCKED_BY_FULL_DOMAIN_HORN_MESH_INPUT in prepared.blockers
    assert not (tmp_path / "store").exists()


def test_prepare_horn_mesh_requires_an_explicit_source_group(tmp_path: Path) -> None:
    root = _fake_root(tmp_path)
    with pytest.raises(REF.ReferenceError, match="REFERENCE_SOURCE_GROUP_REQUIRED"):
        REF.prepare(root, horn_mesh=tmp_path / "horn.msh", run_now=False)


def test_prepare_horn_mesh_records_the_horn_decision(tmp_path: Path, monkeypatch) -> None:
    _install_fake_stage(monkeypatch, has_horn=True)
    root = _fake_root(tmp_path)
    mesh = tmp_path / "horn.msh"
    prepared = REF.prepare(root, horn_mesh=mesh, source_group="SD1D1001",
                           store_root=tmp_path / "store", run_now=False)
    assert prepared.stage_kind == "bl_stage_horn_project"
    assert prepared.horn_mesh == mesh
    assert prepared.source_group == "SD1D1001"
    assert prepared.mesh_role == "full_domain"
    assert REF.BLOCKED_BY_FULL_DOMAIN_HORN_MESH_INPUT not in prepared.blockers


def test_prepare_rejects_unknown_spec_keys() -> None:
    with pytest.raises(ValueError, match="unknown reference prepare keys"):
        REF.prepare({"bogus": 1})


def test_prepare_accepts_a_spec_mapping_and_paths(tmp_path: Path, monkeypatch) -> None:
    _install_fake_stage(monkeypatch, has_horn=False)
    root = _fake_root(tmp_path)
    prepared = REF.prepare({
        "root": root,
        "store_root": tmp_path / "from-spec",
        "run_now": False,
    }, paths={"store_root": tmp_path / "from-paths"})
    assert prepared.ok is False  # dry-run through the spec mapping
    assert not (tmp_path / "from-spec").exists()
    assert not (tmp_path / "from-paths").exists()


# --------------------------------------------------------------------------- graph assertions

def test_graph_summary_matches_the_synthetic_fixture() -> None:
    summary = REF.graph_summary(_fixture_compiled())
    assert summary.region_count == 1
    assert summary.region_kinds == ("unbounded_air",)
    assert summary.interface_count == 0
    assert summary.excitation_port_ids == ("excitation:woofer", "excitation:horn")
    assert summary.excitation_port_kinds == ("normal_velocity", "normal_velocity")
    assert summary.mesh_purposes == ("boundary",)
    assert summary.mesh_scales == (1.0,)
    assert summary.solve_kind is None

    with pytest.raises(REF.ReferenceError, match="GRAPH_REGION_COUNT"):
        REF.assert_graph(summary)
    ok = REF.assert_graph(
        summary, min_regions=1, min_interfaces=0,
        expected_port_ids=("excitation:woofer", "excitation:horn"),
        required_mesh_purposes=("boundary",), require_volume_mesh=False,
        expected_solve_kind=None,
    )
    assert ok["region_count"] == 1 and ok["interface_count"] == 0


def test_graph_summary_reads_a_staged_project_and_enforces_the_reference_graph() -> None:
    summary = REF.graph_summary(_fake_project(), source="project.physical_system")
    assert summary.region_count == 2
    assert summary.interface_count == 1
    ok = REF.assert_graph(summary, expected_solve_kind=None)
    assert ok["mesh_purposes"] == ["fem_volume", "bem_surface", "bem_surface"]
    assert ok["excitation_port_ids"] == ["vented/voltage", "excitation:horn"]


def test_graph_assertions_refuse_port_mismatch_and_bad_mesh_scale() -> None:
    summary = REF.graph_summary(_fake_project(), source="project.physical_system")
    bad_ports = replace(summary, excitation_port_ids=("vented/voltage",))
    with pytest.raises(REF.ReferenceError, match="GRAPH_PORT_IDS"):
        REF.assert_graph(bad_ports, expected_solve_kind=None)

    bad_scale = replace(summary, mesh_scales=(1.0, 0.001, 1.0))
    with pytest.raises(REF.ReferenceError, match="GRAPH_MESH_SCALE"):
        REF.assert_graph(bad_scale, expected_solve_kind=None)


def test_graph_assertions_refuse_a_missing_interface() -> None:
    summary = REF.graph_summary(_fake_project(interfaces=0), source="project.physical_system")
    with pytest.raises(REF.ReferenceError, match="GRAPH_INTERFACE_COUNT"):
        REF.assert_graph(summary, expected_solve_kind=None)


# --------------------------------------------------------------------------- request overlay

def test_request_overlay_is_loaded_and_shape_checked(tmp_path: Path) -> None:
    request = REF.load_request(FIXTURE / "request.json")
    assert request.schema_version == 1
    assert request.frequencies_hz == (100.0, 200.0)
    assert request.excitation_port_ids == ("excitation:woofer", "excitation:horn")
    assert request.include_project_observations is True

    payload = json.loads((FIXTURE / "request.json").read_text(encoding="utf-8"))
    payload["schema_version"] = 2
    bad = tmp_path / "bad_version.json"
    bad.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(REF.ReferenceError, match="REFERENCE_REQUEST_INVALID"):
        REF.load_request(bad)

    payload = json.loads((FIXTURE / "request.json").read_text(encoding="utf-8"))
    payload["probes"] = [{"id": "bad", "points_m": [[1.0, 2.0]]}]
    bad = tmp_path / "bad_probe.json"
    bad.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(REF.ReferenceError, match="REFERENCE_REQUEST_INVALID"):
        REF.load_request(bad)


# --------------------------------------------------------------------------- solve gate

def test_solve_refuses_without_authorized_by(tmp_path: Path) -> None:
    with pytest.raises(REF.ReferenceError, match="REFERENCE_SOLVE_UNAUTHORIZED"):
        REF.solve(tmp_path, FIXTURE / "request.json", authorized_by=None)
    with pytest.raises(REF.ReferenceError, match="REFERENCE_SOLVE_UNAUTHORIZED"):
        REF.solve(tmp_path, FIXTURE / "request.json", authorized_by="   ")


def test_build_solve_argv_matches_the_recorded_smoke_invocation() -> None:
    argv = REF.build_solve_argv("blab.exe", "case.blab.json", "req.json", "beat_cpu", "run")
    assert argv == [
        "blab.exe", "project", "solve", "case.blab.json",
        "--request", "req.json", "--backend", "beat_cpu",
        "--output", "run", "--events", "ndjson",
    ]


def test_solve_refuses_an_existing_run_directory(tmp_path: Path) -> None:
    case = _copy_run_case(tmp_path)
    (case / "case.blab.json").write_text(json.dumps(_fake_project()), encoding="utf-8")
    with pytest.raises(REF.ReferenceError, match="REFERENCE_SOLVE_RUN_EXISTS"):
        REF.solve(case, FIXTURE / "request.json", authorized_by="senior-gate-2026-11-18")


# --------------------------------------------------------------------------- report recomposition

def _bases(result: R.BLHeadlessResult, domain: str) -> tuple[np.ndarray, np.ndarray]:
    bases = result.per_excitation_bases(domain)
    return bases["excitation:woofer"], bases["excitation:horn"]


def test_recomposition_matches_the_dsp_filter_bank(tmp_path: Path) -> None:
    case = _copy_run_case(tmp_path)
    result = R.read_bl_headless_result(case / "run")
    column = REF.dsp_preset_columns((900.0,))[0]
    summed = REF.recompose_preset(result, "observation:horizontal-polar", column)

    assert summed.shared_sensitivity_reference is True
    assert summed.refusal_reason is None
    freqs = result.frequencies_hz
    bank = SYSDSP.filter_bank(column.point, freqs)
    woofer, horn = _bases(result, "observation:horizontal-polar")
    expected = woofer * bank["woofer"][:, None] + horn * bank["horn"][:, None]
    np.testing.assert_allclose(summed.total_pa, expected, rtol=0, atol=1e-15)


def test_polarity_flip_is_an_exact_minus_one_on_the_woofer() -> None:
    columns = REF.dsp_preset_columns((900.0,))
    base = columns[0].point
    flipped = columns[1].point
    freqs = np.array([100.0, 200.0])
    bank_base = SYSDSP.filter_bank(base, freqs)
    bank_flip = SYSDSP.filter_bank(flipped, freqs)
    np.testing.assert_array_equal(bank_flip["woofer"], -bank_base["woofer"])
    np.testing.assert_array_equal(bank_flip["horn"], bank_base["horn"])


def test_delay_is_exp_minus_i_omega_tau_without_conjugation(tmp_path: Path) -> None:
    columns = {column.name: column for column in REF.dsp_preset_columns((900.0,))}
    freqs = np.array([100.0, 200.0])
    positive = SYSDSP.filter_bank(columns["lr4_900_delay_p1ms"].point, freqs)
    negative = SYSDSP.filter_bank(columns["lr4_900_delay_m1ms"].point, freqs)
    reference = SYSDSP.filter_bank(columns["lr4_900_base"].point, freqs)
    tau = 1e-3
    np.testing.assert_allclose(
        positive["horn"], reference["horn"] * np.exp(-1j * 2.0 * np.pi * freqs * tau),
        rtol=0, atol=1e-15)
    np.testing.assert_allclose(
        negative["horn"], reference["horn"] * np.exp(+1j * 2.0 * np.pi * freqs * tau),
        rtol=0, atol=1e-15)
    # A conjugation bug would produce the opposite rotation; refuse that silently passing.
    assert not np.allclose(positive["horn"], reference["horn"] * np.exp(
        +1j * 2.0 * np.pi * freqs * tau))

    case = _copy_run_case(tmp_path)
    result = R.read_bl_headless_result(case / "run")
    summed = REF.recompose_preset(result, "observation:horizontal-polar",
                                  columns["lr4_900_delay_p1ms"])
    woofer, horn = _bases(result, "observation:horizontal-polar")
    delayed_bank = SYSDSP.filter_bank(columns["lr4_900_delay_p1ms"].point, freqs)
    expected = woofer * delayed_bank["woofer"][:, None] + horn * delayed_bank["horn"][:, None]
    np.testing.assert_allclose(summed.total_pa, expected, rtol=0, atol=1e-15)


def test_recomposition_records_a_mixed_per_input_refusal(tmp_path: Path) -> None:
    case = _copy_run_case(tmp_path)
    compiled_path = case / "run" / "compiled-system.json"
    compiled = json.loads(compiled_path.read_text(encoding="utf-8"))
    compiled["excitation_ports"][1]["kind"] = "voltage"
    compiled_path.write_text(json.dumps(compiled, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = R.read_bl_headless_result(case / "run")
    summed = REF.recompose_preset(result, "observation:horizontal-polar",
                                  REF.dsp_preset_columns((900.0,))[0])
    assert summed.shared_sensitivity_reference is False
    assert "SENSITIVITY_REFERENCE_MISMATCH" in (summed.refusal_reason or "")
    assert np.all(np.isfinite(summed.total_pa))


def test_report_contains_presets_lobing_and_honesty_labels(tmp_path: Path) -> None:
    case = _copy_run_case(tmp_path)
    run_manifest = case / "run" / "manifest.json"
    before = run_manifest.read_bytes()
    report = REF.report(case)
    assert run_manifest.read_bytes() == before  # reporting only reads the BL result

    assert report.domain_ids == (
        "observation:horizontal-polar", "observation:vertical-polar",
        "observation:probe:on_axis",
    )
    assert len(report.sums) == 12
    assert "lr4_700_base" in report.sums and "lr4_1100_delay_p1ms" in report.sums
    assert report.vertical_lobing["reference_label"] == "0 deg"
    markdown = report.markdown
    assert "# Boundary Lab reference case report" in markdown
    assert "never comparable as sensitivity" in markdown
    assert "2.83 V" in markdown and "1 m/s" in markdown
    assert "## Per-DSP-preset complex sums" in markdown
    assert "polarity_flip" in markdown
    assert "## Vertical lobing" in markdown


# --------------------------------------------------------------------------- CLI wiring

def test_reference_help_lists_all_subcommands(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["reference", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for name in ("prepare", "validate", "solve", "report"):
        assert name in out


def test_cli_solve_refuses_without_authorization(tmp_path: Path, capsys) -> None:
    case = _copy_run_case(tmp_path)
    (case / "case.blab.json").write_text(json.dumps(_fake_project()), encoding="utf-8")
    code = cli.main(["reference", "solve", str(case),
                     "--request", str(FIXTURE / "request.json")])
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["token"] == "REFERENCE_SOLVE_UNAUTHORIZED"


def test_cli_report_prints_markdown(tmp_path: Path, capsys) -> None:
    case = _copy_run_case(tmp_path)
    code = cli.main(["reference", "report", str(case)])
    assert code == 0
    out = capsys.readouterr().out
    assert out.startswith("# Boundary Lab reference case report")
    assert "never comparable as sensitivity" in out


# --------------------------------------------------------------------------- real BL (opt-in)

def _real_root() -> BLRoot:
    if os.environ.get("HORNLAB_BL_REAL_TESTS", "").strip() != "1":
        pytest.skip("real Boundary Lab workflow gated off (set HORNLAB_BL_REAL_TESTS=1)")
    probe = probe_boundarylab(extra_roots=[REAL_BL_ROOT], use_default_roots=False)
    if probe.verified_root is None:
        pytest.skip("verified Boundary Lab not present")
    return probe.verified_root


def test_real_bl_reference_report_on_recorded_smoke() -> None:
    """Read-only real-BL variant: the recorded smoke result still recomposes and reports."""
    _real_root()  # enforces the same env gate as the staging tests
    if not R.is_bl_headless_result_dir(SMOKE_CASE):
        pytest.skip("recorded smoke run is not present in this worktree")
    report = REF.report(SMOKE_CASE)
    assert len(report.sums) == 12
    assert "vented/voltage" in report.per_input_by_excitation
    assert report.markdown.startswith("# Boundary Lab reference case report")


def test_real_bl_reference_solve_end_to_end(tmp_path: Path) -> None:
    """Opt-in real solve of a copy of the recorded reference case through BL's own CLI."""
    _real_root()
    recorded = (REPO / "system_runs" / "system" / "bl_horn_assembly"
                / "20261118T224519Z-assembly-11000-4a85a0f8")
    request = (REPO / "system_runs" / "system" / "bl_smoke"
               / "20261118T225108Z-smoke-42536-01d15001" / "smoke_request.json")
    if not (recorded / "case.blab.json").is_file() or not request.is_file():
        pytest.skip("recorded reference case/request are not present in this worktree")
    case = tmp_path / "case"
    shutil.copytree(recorded, case)

    solved = REF.solve(case, request, authorized_by="HORNLAB_BL_REAL_TESTS",
                       out=case / "run", timeout_s=1800.0)
    assert solved.returncode == 0
    assert solved.status == "complete"
    assert R.is_bl_headless_result_dir(case / "run")
    assert solved.record_path.name == "reference_solve.json"
    report = REF.report(case)
    assert len(report.sums) == 12


# ------------------------------------------------------------------ solve paths regression
# Real G6 failures recorded 2026-11-18 (parent integrator): (1) project/request paths passed
# RELATIVE were resolved by BL against cwd=<case dir>, producing a doubled case path; (2) the
# wrapper pre-created the run directory that BL's crash-tolerant HeadlessResultWriter refuses
# (FileExistsError). Both are pinned here; BL is never actually invoked.


def test_solve_builds_absolute_argv_and_writes_no_output_dir(tmp_path, monkeypatch) -> None:
    case = tmp_path / "case"
    case.mkdir()
    (case / "case.blab.json").write_text(
        json.dumps(_fake_project(), indent=2, sort_keys=True), encoding="utf-8")
    captured: dict[str, Any] = {}

    class _Proc:
        returncode = 1
        stdout = ""
        stderr = ""

    def fake_run(argv, **kwargs):
        captured["argv"] = list(argv)
        captured["cwd"] = kwargs.get("cwd")
        return _Proc()

    monkeypatch.setattr(REF, "_root_for_case", lambda root: _fake_root(tmp_path))
    monkeypatch.setattr(REF.subprocess, "run", fake_run)
    rel_case = os.path.relpath(case)
    with pytest.raises(REF.ReferenceError, match="REFERENCE_SOLVE_FAILED"):
        REF.solve(rel_case, FIXTURE / "request.json", authorized_by="regression-2026-11-18")
    argv = captured["argv"]
    assert Path(argv[3]).is_absolute() and argv[3].endswith("case.blab.json")
    assert Path(argv[5]).is_absolute()
    assert Path(argv[9]).is_absolute() and Path(argv[9]).name == "run"
    assert not (case / "run").exists()  # output dir creation belongs to BL, not this wrapper


# ------------------------------------------------------------------ multi-run provenance
# Senior directive 2026-11-22 §5: repeated requests in one case must produce separate,
# correctly identified, non-overwriting, replayable solve records.  BL is faked by copying
# the recorded result fixture into the requested output directory.


def _fake_solve_subprocess(monkeypatch) -> None:
    class _Proc:
        returncode = 0
        stdout = '{"event":"completed","solved_count":21,"frequency_count":21}'
        stderr = ""

    def fake_run(argv, **kwargs):
        out = Path(argv[argv.index("--output") + 1])
        shutil.copytree(FIXTURE, out)
        return _Proc()

    monkeypatch.setattr(REF.subprocess, "run", fake_run)


def _solve_case(tmp_path: Path, monkeypatch, out_name: str | None) -> REF.ReferenceSolveResult:
    _fake_solve_subprocess(monkeypatch)
    case = tmp_path / "case"
    case.mkdir(exist_ok=True)
    (case / "case.blab.json").write_text(
        json.dumps(_fake_project(), indent=2, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(REF, "_root_for_case", lambda root: _fake_root(tmp_path))
    return REF.solve(
        case, FIXTURE / "request.json", authorized_by="multi-run-test",
        out=None if out_name is None else case / out_name)


def test_two_requests_in_one_case_write_separate_records(tmp_path, monkeypatch) -> None:
    first = _solve_case(tmp_path, monkeypatch, None)
    second = _solve_case(tmp_path, monkeypatch, "run_placement_21f")

    assert first.status == "complete" and second.status == "complete"
    assert first.record_path.name == "reference_solve.json"
    assert second.record_path.name == "reference_solve_run_placement_21f.json"
    assert first.record_path.is_file() and second.record_path.is_file()
    assert first.record_path != second.record_path

    payloads = [json.loads(p.read_text(encoding="utf-8"))["payload"]
                for p in (first.record_path, second.record_path)]
    payloads = [json.loads(p) for p in payloads]
    assert [Path(p["run_dir"]).name for p in payloads] == ["run", "run_placement_21f"]
    assert all(p["authorized_by"] == "multi-run-test" for p in payloads)
    # Replayable: both the request and the project are pinned by path and digest.
    assert all(len(p["request_sha256"]) == 64 for p in payloads)
    assert all(len(p["project_sha256"]) == 64 for p in payloads)
    assert all(p["run_status"] == "complete" for p in payloads)


def test_a_completed_record_is_never_overwritten(tmp_path) -> None:
    record = tmp_path / "reference_solve.json"
    REF._write_record(record, {"kind": "first"})
    with pytest.raises(REF.ReferenceError, match="REFERENCE_RECORD_EXISTS"):
        REF._write_record(record, {"kind": "second"})
    assert json.loads(json.loads(record.read_text(encoding="utf-8"))["payload"])["kind"] == "first"
