"""Offline tests for :mod:`hornlab_search.system.read_case` (contract section 2).

Every test builds a synthetic ``system_runs/system/<experiment>/<case>/`` store under
``tmp_path``.  No real store, no GPU, no solver, no Boundary Lab import.  The final test loads
``tools/data/system_cases.py`` by path and asserts the typed reader agrees with the export tool
on the fields that matter (the N1 parity requirement).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from conftest import REPO

from hornlab_search.system import provenance
from hornlab_search.system import read_case as reader

TOOL = REPO / "tools" / "data" / "system_cases.py"

RUN_MANIFEST = {
    "schema": "boundary-lab-headless-result",
    "schema_version": 2,
    "status": "complete",
    "backend_id": "beat_cpu",
    "solve_kind": "coupled_bem_fem",
    "phasor_convention": "exp(+i omega t)",
    "frequencies_hz": [250.0, 700.0, 1100.0],
    "completion_mask": [True, True, True],
    "excitation_port_ids": ["vented/voltage"],
}


# --------------------------------------------------------------------------- fixtures


def _store(root: Path) -> Path:
    return root / "system_runs"


def _write_case(
    root: Path,
    experiment: str,
    name: str,
    *,
    payload: dict | None = None,
    run_manifest: dict | None = None,
    raw_manifest: str | None = None,
    digest: str | None = None,
    files: dict[str, dict | str] | None = None,
) -> Path:
    case = _store(root) / "system" / experiment / name
    case.mkdir(parents=True)
    if raw_manifest is not None:
        (case / "manifest.json").write_text(raw_manifest, encoding="utf-8")
    else:
        provenance.write_manifest(case, payload if payload is not None else {})
        if digest is not None:
            body = json.loads((case / "manifest.json").read_text(encoding="utf-8"))
            body["manifest_payload_sha256"] = digest
            (case / "manifest.json").write_text(json.dumps(body), encoding="utf-8")
    if run_manifest is not None:
        (case / "run").mkdir()
        (case / "run" / "manifest.json").write_text(json.dumps(run_manifest), encoding="utf-8")
    for rel, content in (files or {}).items():
        path = case / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    return case


def _payload(*, result: dict | None = None, run: dict | None = None, spec: dict | None = None, **extra) -> dict:
    payload: dict = {"kind": "bl_stage_reference_project"}
    if result is not None:
        payload["result"] = result
    if run is not None:
        payload["run"] = {
            "status": run.get("status"),
            "backend_id": run.get("backend_id"),
            "solve_kind": run.get("solve_kind"),
            "frequencies_hz": run.get("frequencies_hz"),
            "completion_mask": run.get("completion_mask"),
        }
    if spec is not None:
        payload["spec"] = spec
    payload.update(extra)
    return payload


def _write_readiness(root: Path, cases: list[dict]) -> Path:
    path = root / reader.READINESS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "schema: hw_readiness_v1",
        "updated: 2026-11-19",
        "fidelity_note: synthetic fixture",
        "cases:",
    ]
    for entry in cases:
        first = True
        for key, value in entry.items():
            prefix = "  - " if first else "    "
            lines.append(f"{prefix}{key}: {json.dumps(value)}")
            first = False
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------- status rules


def test_one_case_per_status_and_status_reason(tmp_path):
    _write_case(
        tmp_path, "exp", "20261118T225108Z-solved",
        payload=_payload(result={"ok": True}, run=RUN_MANIFEST),
        run_manifest=RUN_MANIFEST,
    )
    _write_case(tmp_path, "exp", "20261118T225109Z-staged", payload=_payload())
    _write_case(
        tmp_path, "exp", "20261118T225110Z-refused",
        payload=_payload(result={"ok": False, "error": "Driver must fit inside the enclosure walls."}),
    )
    _write_case(tmp_path, "exp", "20261118T225111Z-malformed", raw_manifest="{not json")
    (_store(tmp_path) / "system" / "exp" / "20261118T225112Z-missing").mkdir(parents=True)

    store = _store(tmp_path)
    cases = {
        case.header.case: case
        for case in reader.iter_cases(store)
    }
    assert cases["20261118T225108Z-solved"].header.status == "solved"
    assert cases["20261118T225108Z-solved"].header.status_reason == "RUN_COMPLETE"
    assert cases["20261118T225109Z-staged"].header.status == "staged"
    assert cases["20261118T225109Z-staged"].header.status_reason == "MANIFEST_ONLY"
    assert cases["20261118T225110Z-refused"].header.status == "refused"
    assert cases["20261118T225110Z-refused"].header.status_reason == "CASE_REFUSED"
    assert cases["20261118T225111Z-malformed"].header.status == "invalid"
    assert cases["20261118T225111Z-malformed"].header.status_reason == "UNPARSEABLE"
    assert cases["20261118T225112Z-missing"].header.status == "invalid"
    assert cases["20261118T225112Z-missing"].header.status_reason == "NO_MANIFEST"

    solved = cases["20261118T225108Z-solved"].solve
    assert solved is not None
    assert (solved.n_frequencies, solved.freq_min_hz, solved.freq_max_hz) == (3, 250.0, 1100.0)
    assert (solved.completion_done, solved.completion_total) == (3, 3)
    assert solved.backend_id == "beat_cpu"
    assert cases["20261118T225110Z-refused"].refusals == ("CASE_REFUSED",)


def test_refused_true_and_token_are_refusals_with_tokens(tmp_path):
    _write_case(tmp_path, "exp", "20261118T225108Z-refused-flag", payload=_payload(refused=True))
    _write_case(
        tmp_path,
        "exp",
        "20261118T225109Z-token",
        payload=_payload(result={"ok": False, "error": "BL_PANEL_FIT_REJECTED: outside the panel"}),
    )
    store = _store(tmp_path)
    flag = reader.read_case(store / "system" / "exp" / "20261118T225108Z-refused-flag", store_root=store)
    token = reader.read_case(store / "system" / "exp" / "20261118T225109Z-token", store_root=store)
    assert flag.header.status == "refused"
    assert "REFUSED" in flag.refusals
    assert token.header.status == "refused"
    assert "BL_PANEL_FIT_REJECTED" in token.refusals


def test_geometry_refusals_and_bl_capability_ok_are_not_refusals(tmp_path):
    payload = _payload(
        result={"ok": True},
        spec={
            "geometry": {"refusals": {"cap_diameter_m": "GEOMETRY_FIELD_UNAVAILABLE"}},
            "bl_root": {"status": "BL_CAPABILITY_OK"},
        },
    )
    _write_case(tmp_path, "exp", "20261118T230000Z-stage", payload=payload)
    store = _store(tmp_path)
    case = reader.read_case(store / "system" / "exp" / "20261118T230000Z-stage", store_root=store)
    assert case.header.status == "staged"
    assert case.refusals == ()
    assert case.stage.ok is True


# --------------------------------------------------------------------------- integrity


def test_manifest_integrity_verified_mismatch_unknown(tmp_path):
    _write_case(tmp_path, "exp", "20261118T225108Z-verified", payload=_payload())
    _write_case(tmp_path, "exp", "20261118T225109Z-mismatch", payload=_payload(), digest="0" * 64)
    body = {"created_utc": "2026-11-18T23:23:06+00:00", "payload": {"kind": "legacy"}}
    _write_case(tmp_path, "exp", "20261118T225110Z-unknown", raw_manifest=json.dumps(body))
    store = _store(tmp_path)
    verified = reader.read_case(store / "system" / "exp" / "20261118T225108Z-verified", store_root=store)
    mismatch = reader.read_case(store / "system" / "exp" / "20261118T225109Z-mismatch", store_root=store)
    unknown = reader.read_case(store / "system" / "exp" / "20261118T225110Z-unknown", store_root=store)
    assert verified.header.manifest_integrity == "verified"
    assert mismatch.header.manifest_integrity == "mismatch"
    assert unknown.header.manifest_integrity == "unknown"
    assert any("mismatch" in item for item in mismatch.diagnostics)


def test_never_raises_on_missing_dir_or_non_object_manifest(tmp_path):
    store = _store(tmp_path)
    missing = reader.read_case(store / "system" / "exp" / "20261118T225108Z-absent", store_root=store)
    assert missing.header.status == "invalid"
    assert missing.diagnostics
    _write_case(tmp_path, "exp", "20261118T225109Z-list", raw_manifest="[1, 2, 3]")
    listed = reader.read_case(store / "system" / "exp" / "20261118T225109Z-list", store_root=store)
    assert listed.header.status == "invalid"
    assert listed.header.status_reason == "UNPARSEABLE"


# --------------------------------------------------------------------------- metadata / paths


def test_windows_path_manifest_read_on_any_os(tmp_path):
    request = {
        "horn": {
            "mesh_path": "C:\\somewhere\\lecleach_rollback_1in_v6_9e02db06ecc3\\mesh.msh",
            "mesh_sha256": "9b4057c2",
            "translation_mm": [0.0, 0.0, 10.0],
        },
        "source": {"width_m": 0.3712, "height_m": 0.5, "depth_m": 0.36},
        "mapping": {"driver_id": "FaitalPRO 12PR300"},
    }
    _write_case(
        tmp_path, "exp", "20261118T225108Z-winpath",
        payload=_payload(), files={"request.json": request},
    )
    store = _store(tmp_path)
    case = reader.read_case(store / "system" / "exp" / "20261118T225108Z-winpath", store_root=store)
    assert case.geometry is not None
    assert case.geometry.horn_mesh == "lecleach_rollback_1in_v6_9e02db06ecc3"
    assert case.geometry.horn_mesh_sha256 == "9b4057c2"
    assert case.geometry.horn_offset_mm_xyz == (0.0, 0.0, 10.0)
    assert case.geometry.box_mm == (371.2, 500.0, 360.0)
    assert case.geometry.driver_name == "FaitalPRO 12PR300"
    assert case.header.source_path == "system/exp/20261118T225108Z-winpath"
    assert all("/" in item or item.startswith("system/") for item in case.sources)
    assert case.sources[0].endswith("manifest.json")


def test_metadata_walk_order_prefers_request_over_manifest_payload(tmp_path):
    spec = {"source": {"width_m": 9.0, "height_m": 9.0, "depth_m": 9.0}}
    request = {"source": {"width_m": 0.3712, "height_m": 0.5, "depth_m": 0.36}}
    _write_case(
        tmp_path, "exp", "20261118T225108Z-order",
        payload=_payload(spec=spec), files={"request.json": request},
    )
    store = _store(tmp_path)
    case = reader.read_case(store / "system" / "exp" / "20261118T225108Z-order", store_root=store)
    assert case.geometry.box_mm == (371.2, 500.0, 360.0)


def test_clearance_and_air_volume_block(tmp_path):
    stage = {
        "assertions": {"air_volume_m3": 0.042169449931},
        "clearance": {"status": "FAIL", "min_gap_m": 0.0007, "source": "synthetic"},
    }
    _write_case(
        tmp_path, "exp", "20261118T225108Z-clear",
        payload=_payload(), files={"stage_report.json": stage},
    )
    store = _store(tmp_path)
    case = reader.read_case(store / "system" / "exp" / "20261118T225108Z-clear", store_root=store)
    assert case.geometry.net_volume_l == 42.169
    assert case.geometry.net_volume_source == "air_volume_m3"
    assert case.stage.clearance.status == "violation"
    assert case.stage.clearance.min_gap_mm == 0.7


# --------------------------------------------------------------------------- readiness


def test_readiness_declared_vs_undeclared(tmp_path):
    declared_key = "exp/20261118T225108Z-declared"
    _write_readiness(
        tmp_path,
        [
            {
                "key": declared_key,
                "ref": "#1",
                "gate": "G4 wide basis",
                "fidelity": "COUPLED_VENTED_FEM_BEM_LEM",
                "motor": "demo",
                "transducer_shape": "demo",
                "horn_source": "ideal_velocity",
                "pair_with": "exp/20261118T225109Z-other",
                "evidence": "SYNTHETIC_EVIDENCE.md section 1",
            }
        ],
    )
    _write_case(
        tmp_path, "exp", "20261118T225108Z-declared",
        payload=_payload(run=RUN_MANIFEST), run_manifest=RUN_MANIFEST,
    )
    _write_case(
        tmp_path, "exp", "20261118T225109Z-other",
        payload=_payload(motor_mapping={"bl_n_per_a": 14.1}),
    )

    readiness = reader.load_readiness(tmp_path)
    assert readiness is not None and declared_key in readiness
    store = _store(tmp_path)
    cases = {case.header.case_key: case for case in reader.iter_cases(store, readiness=readiness)}

    declared = cases[declared_key].declaration
    assert declared.declared is True
    assert declared.fidelity == "COUPLED_VENTED_FEM_BEM_LEM"
    assert declared.motor == "demo"
    assert declared.motor_source == "readiness"
    assert declared.gate == "G4 wide basis"
    assert declared.ref == "#1"
    assert declared.evidence == "SYNTHETIC_EVIDENCE.md section 1"
    assert declared.horn_source == "ideal_velocity"
    assert declared.pair_with == "exp/20261118T225109Z-other"

    other = cases["exp/20261118T225109Z-other"].declaration
    assert other.declared is False
    assert other.fidelity == "UNDECLARED"
    assert other.transducer_shape == "UNDECLARED"
    assert other.motor == "real"
    assert other.motor_source == "manifest"


def test_missing_registry_degrades_to_undeclared(tmp_path):
    _write_case(tmp_path, "exp", "20261118T225108Z-a", payload=_payload())
    assert reader.load_readiness(tmp_path) is None
    store = _store(tmp_path)
    case = reader.read_case(store / "system" / "exp" / "20261118T225108Z-a", store_root=store)
    assert case.declaration.fidelity == "UNDECLARED"
    assert case.declaration.motor == "UNDECLARED"


# --------------------------------------------------------------------------- ordering


def test_iter_cases_sorted_by_experiment_then_case(tmp_path):
    _write_case(tmp_path, "zeta", "20261118T225108Z-b", payload=_payload())
    _write_case(tmp_path, "alpha", "20261118T225109Z-z", payload=_payload())
    _write_case(tmp_path, "alpha", "20261118T225108Z-a", payload=_payload())
    _write_case(tmp_path, "alpha", "not-a-case", payload=_payload())
    _write_case(tmp_path, "alpha", "_fixtures", payload=_payload())
    keys = [case.header.case_key for case in reader.iter_cases(_store(tmp_path))]
    assert keys == [
        "alpha/20261118T225108Z-a",
        "alpha/20261118T225109Z-z",
        "zeta/20261118T225108Z-b",
    ]


# --------------------------------------------------------------------------- parity with the export tool


def _load_tool():
    spec = importlib.util.spec_from_file_location("system_cases_tool_a1_parity", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parity_with_tools_data_system_cases(tmp_path):
    """Facts (status/kind/integrity/box/horn) agree with the export tool for every case."""
    # solved: rich metadata through request.json (Windows mesh path exercises N1)
    request = {
        "odd": {"nested": {"source": {"width_m": 0.3712, "height_m": 0.5, "depth_m": 0.36}}},
        "horn": {
            "mesh_path": "C:\\somewhere\\lecleach_rollback_1in_v6_9e02db06ecc3\\mesh.msh",
            "mesh_sha256": "9b4057c2",
            "translation_mm": [0.0, 0.0, 10.0],
        },
        "mapping": {"driver_id": "FaitalPRO 12PR300"},
        "seed": {"source_record": {"net_volume_l": 115.0, "tuning_hz": 30.0}},
    }
    _write_case(
        tmp_path, "exp", "20261118T225108Z-solved",
        payload=_payload(result={"ok": True}, run=RUN_MANIFEST),
        run_manifest=RUN_MANIFEST,
        files={"request.json": request},
    )
    _write_case(tmp_path, "exp", "20261118T225109Z-staged", payload=_payload())
    _write_case(
        tmp_path, "exp", "20261118T225110Z-refused",
        payload=_payload(result={"ok": False, "error": "Driver must fit inside the enclosure walls."}),
    )
    _write_case(tmp_path, "exp", "20261118T225111Z-malformed", raw_manifest="{not json")
    (_store(tmp_path) / "system" / "exp" / "20261118T225112Z-missing").mkdir(parents=True)
    _write_case(
        tmp_path, "exp", "20261118T225113Z-mismatch", payload=_payload(), digest="0" * 64,
    )
    body = {"created_utc": "2026-11-18T23:23:06+00:00", "payload": {"kind": "legacy"}}
    _write_case(tmp_path, "exp", "20261118T225114Z-unknown", raw_manifest=json.dumps(body))

    tool = _load_tool()
    rows, _census, _diagnostics = tool.scan_cases(tmp_path, {"cases": {}})
    assert len(rows) == 7
    by_key = {row["case_key"]: row for row in rows}
    store = _store(tmp_path)

    skipped_horn_mesh: list[str] = []
    for row in rows:
        case = reader.read_case(
            store / "system" / row["experiment"] / row["case"], store_root=store
        )
        assert case.header.case_key == row["case_key"]
        assert case.header.status == row["status"]
        assert case.header.status_reason in {
            "RUN_COMPLETE", "CASE_REFUSED", "MANIFEST_ONLY", "NO_MANIFEST", "UNPARSEABLE"
        }
        assert case.header.kind == row["kind"]
        assert case.header.manifest_integrity == row["manifest_integrity"]

        geometry = case.geometry
        box = geometry.box_mm if geometry is not None else (None, None, None)
        assert box == (row["box_width_mm"], row["box_height_mm"], row["box_depth_mm"])
        assert (geometry.horn_mesh_sha256 if geometry else None) == row["horn_mesh_sha256"]
        offset = list(geometry.horn_offset_mm_xyz) if geometry and geometry.horn_offset_mm_xyz else None
        assert offset == row["horn_offset_mm_xyz"]
        assert (geometry.driver_name if geometry else None) == row["driver_name"]

        horn_mesh = geometry.horn_mesh if geometry else None
        if horn_mesh != row["horn_mesh"]:
            # The tool derives horn_mesh with pathlib (N1): on POSIX a Windows path is not split.
            skipped_horn_mesh.append(row["case_key"])
            assert horn_mesh == "lecleach_rollback_1in_v6_9e02db06ecc3"

    # The Windows-path case is the only one where the tool may differ (it is correct on Windows,
    # wrong on Linux).  On a POSIX runner this asserts the N1 fix; on Windows the list is empty.
    assert set(skipped_horn_mesh) <= {"exp/20261118T225108Z-solved"}
    solved_row = by_key["exp/20261118T225108Z-solved"]
    assert solved_row["status"] == "solved"
    assert solved_row["manifest_integrity"] == "verified"
    assert solved_row["box_width_mm"] == 371.2
    # read_case is correct on every OS even where the shared store lives on another platform.
    solved_case = reader.read_case(
        store / "system" / "exp" / "20261118T225108Z-solved", store_root=store
    )
    assert solved_case.geometry.horn_mesh == "lecleach_rollback_1in_v6_9e02db06ecc3"
    assert solved_case.header.manifest_integrity == "verified"
