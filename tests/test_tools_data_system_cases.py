"""Offline tests for ``tools/data/system_cases.py`` (system case + screen export).

Hermetic: every test builds a synthetic ``system_runs/system/<experiment>/<case>/`` store and its
own readiness registry under ``tmp_path``.  No real store, no GPU, no solver, no Boundary Lab
import.  The tool is loaded by path, matching the ``tests/test_tools_*.py`` convention.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from conftest import REPO

TOOL = REPO / "tools" / "data" / "system_cases.py"
READINESS_REL = Path("docs/research/system_woofer_2026-11-18/readiness.yaml")


def _load_tool():
    spec = importlib.util.spec_from_file_location("system_cases_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


system_cases = _load_tool()

#: Independently computed from ``hornlab_search.system.contracts.canonical_json`` over the
#: reparsed payload below.  Pins this tool's stdlib canonicalisation to the manifest writer.
FIXTURE_PAYLOAD = {
    "kind": "bl_smoke_first_bem_v1",
    "project_sha256": "abc",
    "request_sha256": "def",
    "result": '{"ok": true}',
    "run": '{"status": "complete", "frequencies_hz": [250.0, 700.0, 1100.0]}',
}
FIXTURE_PAYLOAD_SHA = "b09635f5c055929cfa53b1b347121a748345be571b7c925fac1c33ab2d39c38c"

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
    "solver_options": {"symmetry": "off"},
    "started_at_utc": "2026-11-18T22:51:56+00:00",
    "finished_at_utc": "2026-11-18T22:52:46+00:00",
    "engine_runs": [{"engine": {"name": "BEAT Engine"}, "execution": {"backend": "cpu"}}],
    "meshes": [{"id": "vented/mesh/interior", "purpose": "fem_volume"}],
}


# --------------------------------------------------------------------------- fixtures


def _readiness(root: Path, cases: list[dict]) -> None:
    path = root / READINESS_REL
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


def _payload(
    *,
    project_sha: str | None = "proj",
    result: dict | None = None,
    run: dict | None = RUN_MANIFEST,
    spec: dict | None = None,
    **extra,
) -> dict:
    payload: dict = {"kind": "bl_stage_reference_project"}
    if project_sha is not None:
        payload["project_sha256"] = project_sha
    if result is not None:
        payload["result"] = json.dumps(result)
    if run is not None:
        compact = {
            "status": run.get("status"),
            "backend_id": run.get("backend_id"),
            "solve_kind": run.get("solve_kind"),
            "phasor_convention": run.get("phasor_convention"),
            "frequencies_hz": run.get("frequencies_hz"),
            "completion_mask": run.get("completion_mask"),
        }
        payload["run"] = json.dumps(compact)
    if spec is not None:
        payload["spec"] = json.dumps(spec)
    payload.update(extra)
    return payload


def _write_case(
    root: Path,
    experiment: str,
    name: str,
    *,
    payload: dict | None = None,
    digest: str | None = None,
    run_manifest: dict | None = None,
    run_recorded_sha: bool = False,
    files: dict[str, dict | str] | None = None,
    raw_manifest: str | None = None,
) -> Path:
    case = root / "system_runs" / "system" / experiment / name
    case.mkdir(parents=True)
    if raw_manifest is not None:
        (case / "manifest.json").write_text(raw_manifest, encoding="utf-8")
        return case
    payload = payload if payload is not None else {}
    body = {
        "created_utc": "2026-11-18T23:23:06.206464+00:00",
        "manifest_payload_sha256": system_cases.payload_sha256(payload) if digest is None else digest,
        "payload": payload,
    }
    (case / "manifest.json").write_text(json.dumps(body), encoding="utf-8")
    if run_manifest is not None:
        run_dir = case / "run"
        run_dir.mkdir()
        (run_dir / "manifest.json").write_text(json.dumps(run_manifest), encoding="utf-8")
        if run_recorded_sha:
            recorded = hashlib.sha256((run_dir / "manifest.json").read_bytes()).hexdigest()
            body["payload"]["run"] = json.dumps(
                {**json.loads(body["payload"].get("run") or "{}"), "manifest_sha256": recorded}
            )
            (case / "manifest.json").write_text(json.dumps(body), encoding="utf-8")
    for rel, content in (files or {}).items():
        path = case / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    return case


def _run(root: Path, **kwargs):
    out = root / "out"
    document, screens, written, ok = system_cases.run(root=root, out_dir=out, **kwargs)
    return document, screens, written, ok, out


def _rows(document: dict) -> dict[str, dict]:
    return {row["case_key"]: row for row in document["cases"]}


def _read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


# --------------------------------------------------------------------------- status / census


def test_status_classification_and_census(tmp_path):
    _readiness(tmp_path, [])
    _write_case(
        tmp_path,
        "exp",
        "20261118T225108Z-solved-1",
        payload=_payload(result={"ok": True}),
        run_manifest=RUN_MANIFEST,
    )
    _write_case(tmp_path, "exp", "20261118T225109Z-staged-2", payload=_payload(run=None))
    _write_case(
        tmp_path,
        "exp",
        "20261118T225110Z-refused-3",
        payload=_payload(
            run=None,
            result={"ok": False, "error": "Driver must fit inside the enclosure walls with 3 mm clearance."},
        ),
    )
    _write_case(tmp_path, "exp", "20261118T225111Z-malformed-4", raw_manifest="{not json")
    # A timestamped directory with no manifest at all is a record too (invalid, not a crash).
    (tmp_path / "system_runs" / "system" / "exp" / "20261118T225112Z-missing-5").mkdir(parents=True)

    document, _screens, _written, _ok, out = _run(tmp_path)
    census = document["census"]
    assert census["scanned"] == 5
    assert census["included"] == 5
    assert census["by_status"] == {"invalid": 2, "refused": 1, "solved": 1, "staged": 1}
    assert census["solved"] == 1
    assert census["diagnostics"] == 3  # missing manifest x2 + malformed JSON
    assert (out / "system_cases.csv").is_file()

    rows = _rows(document)
    solved = rows["exp/20261118T225108Z-solved-1"]
    assert solved["status"] == "solved"
    assert solved["solved"] is True
    assert solved["n_frequencies"] == 3
    assert (solved["freq_min_hz"], solved["freq_max_hz"]) == (250.0, 1100.0)
    assert solved["completion"] == "3/3"
    assert solved["backend_id"] == "beat_cpu"
    assert solved["solve_kind"] == "coupled_bem_fem"
    assert solved["phasor_convention"] == "exp(+i omega t)"
    assert solved["authorized_by"] is None

    refused = rows["exp/20261118T225110Z-refused-3"]
    assert refused["status"] == "refused"
    assert refused["solved"] is False
    assert "must fit inside" in (refused["stage_error"] or "")

    assert rows["exp/20261118T225109Z-staged-2"]["status"] == "staged"
    assert rows["exp/20261118T225111Z-malformed-4"]["status"] == "invalid"
    assert rows["exp/20261118T225112Z-missing-5"]["status"] == "invalid"
    reasons = " ".join(item["reason"] for item in document["diagnostics"])
    assert "missing manifest.json" in reasons
    assert "JSONDecodeError" in reasons


def test_recorded_run_block_without_run_manifest_is_not_solved(tmp_path):
    """``payload.run`` claiming ``complete`` is not a solve: the run manifest must be on disk."""
    _readiness(tmp_path, [])
    case = _write_case(
        tmp_path,
        "exp",
        "20261118T225108Z-recorded-only",
        payload=_payload(),  # payload.run says complete, but no run/ tree is written
    )
    (case / "run").mkdir()  # a run directory with no manifest.json is still not a solve
    document, _screens, _written, _ok, _out = _run(tmp_path)
    row = document["cases"][0]
    assert row["status"] == "staged"
    assert row["solved"] is False
    assert row["n_frequencies"] == 3  # planned grid from the recorded run block is kept
    assert row["run"]["present"] is False


def test_geometry_field_ledger_is_not_a_refusal(tmp_path):
    """``spec.geometry.refusals`` / ``BL_CAPABILITY_OK`` must not mark a case refused."""
    _readiness(tmp_path, [])
    payload = _payload(
        result={"ok": True},
        spec={
            "geometry": {"refusals": {"cap_diameter_m": "GEOMETRY_FIELD_UNAVAILABLE"}},
            "bl_root": {"status": "BL_CAPABILITY_OK"},
        },
    )
    _write_case(tmp_path, "exp", "20261118T230000Z-staged-1", payload=payload)
    document, _screens, _written, _ok, _out = _run(tmp_path)
    assert document["cases"][0]["status"] == "staged"


# --------------------------------------------------------------------------- readiness


def test_readiness_join_and_undeclared(tmp_path):
    solved_key = "exp/20261118T225108Z-declared"
    _readiness(
        tmp_path,
        [
            {
                "key": solved_key,
                "ref": "#1",
                "gate": "G4 wide basis",
                "fidelity": "COUPLED_VENTED_FEM_BEM_LEM",
                "motor": "demo",
                "transducer_shape": "demo",
                "horn_source": "ideal_velocity",
                "pair_with": "exp/20261118T225109Z-other",
                "evidence": "SYNTHETIC_EVIDENCE.md section 1",
            },
            {
                "key": "exp/20261118T225199Z-not-on-disk",
                "ref": "R9",
                "gate": "missing",
                "fidelity": "COUPLED_VENTED_FEM_BEM_LEM",
            },
        ],
    )
    _write_case(tmp_path, "exp", "20261118T225108Z-declared", payload=_payload(), run_manifest=RUN_MANIFEST)
    # An undeclared case with a manifest motor_mapping: motor may be a fact, fidelity must NOT be.
    _write_case(
        tmp_path,
        "exp",
        "20261118T225109Z-other",
        payload=_payload(run=None, motor_mapping={"bl_n_per_a": 14.1}),
    )

    document, _screens, _written, _ok, _out = _run(tmp_path)
    rows = _rows(document)
    declared = rows[solved_key]
    assert declared["declared"] is True
    assert declared["ref"] == "#1"
    assert declared["gate"] == "G4 wide basis"
    assert declared["gate_source"] == "readiness"
    assert declared["fidelity"] == "COUPLED_VENTED_FEM_BEM_LEM"
    assert declared["motor"] == "demo"
    assert declared["transducer_shape"] == "demo"
    assert declared["horn_source"] == "ideal_velocity"
    assert declared["pair_with"] == "exp/20261118T225109Z-other"
    assert declared["evidence"] == "SYNTHETIC_EVIDENCE.md section 1"
    assert document["readiness"]["declared_cases"] == 2
    assert document["readiness"]["updated"] == "2026-11-19"

    other = rows["exp/20261118T225109Z-other"]
    assert other["declared"] is False
    assert other["fidelity"] == "UNDECLARED"
    assert other["transducer_shape"] == "UNDECLARED"
    assert other["motor"] == "real"
    assert other["motor_source"] == "manifest"

    missing = [item for item in document["diagnostics"] if item["case_key"] == "exp/20261118T225199Z-not-on-disk"]
    assert missing and "not on disk" in missing[0]["reason"]


def test_missing_registry_degrades_to_undeclared(tmp_path):
    _write_case(tmp_path, "exp", "20261118T225108Z-a", payload=_payload(), run_manifest=RUN_MANIFEST)
    document, _screens, _written, _ok, _out = _run(tmp_path)
    row = document["cases"][0]
    assert row["fidelity"] == "UNDECLARED"
    assert row["motor"] == "UNDECLARED"
    assert document["readiness"]["found"] is False
    assert any("readiness" in item["reason"] for item in document["diagnostics"])


# --------------------------------------------------------------------------- integrity


def test_manifest_payload_hash_matches_contract_canonicalisation():
    assert system_cases.payload_sha256(FIXTURE_PAYLOAD) == FIXTURE_PAYLOAD_SHA


def test_manifest_integrity_verified_mismatch_unknown(tmp_path):
    _readiness(tmp_path, [])
    _write_case(tmp_path, "exp", "20261118T225108Z-verified", payload=FIXTURE_PAYLOAD)
    _write_case(
        tmp_path,
        "exp",
        "20261118T225109Z-mismatch",
        payload=FIXTURE_PAYLOAD,
        digest="0" * 64,
    )
    body = {
        "created_utc": "2026-11-18T23:23:06+00:00",
        "payload": {"kind": "legacy_without_recorded_sha"},
    }
    _write_case(tmp_path, "exp", "20261118T225110Z-unknown", raw_manifest=json.dumps(body))

    document, _screens, _written, _ok, _out = _run(tmp_path)
    rows = _rows(document)
    assert rows["exp/20261118T225108Z-verified"]["manifest_integrity"] == "verified"
    assert rows["exp/20261118T225109Z-mismatch"]["manifest_integrity"] == "mismatch"
    assert rows["exp/20261118T225110Z-unknown"]["manifest_integrity"] == "unknown"
    assert document["census"]["manifest_integrity"] == {"mismatch": 1, "unknown": 1, "verified": 1}
    assert any("mismatch" in item["reason"] for item in document["diagnostics"])


def test_run_and_project_integrity(tmp_path):
    _readiness(tmp_path, [])
    project = {"schema_version": 10, "active_generator_document_id": "vented"}
    case = _write_case(
        tmp_path,
        "exp",
        "20261118T225108Z-run",
        payload=_payload(),
        run_manifest=RUN_MANIFEST,
        run_recorded_sha=True,
        files={"case.blab.json": project},
    )
    payload = json.loads((case / "manifest.json").read_text(encoding="utf-8"))["payload"]
    payload["project_sha256"] = hashlib.sha256((case / "case.blab.json").read_bytes()).hexdigest()
    (case / "manifest.json").write_text(
        json.dumps(
            {
                "created_utc": "2026-11-18T23:23:06+00:00",
                "manifest_payload_sha256": system_cases.payload_sha256(payload),
                "payload": payload,
            }
        ),
        encoding="utf-8",
    )

    document, _screens, _written, _ok, _out = _run(tmp_path)
    row = document["cases"][0]
    assert row["run_manifest_integrity"] == "verified"
    assert row["project_integrity"] == "verified"
    assert row["run_manifest_sha256"] == hashlib.sha256(
        (case / "run" / "manifest.json").read_bytes()
    ).hexdigest()


# --------------------------------------------------------------------------- extraction


def test_metadata_is_extracted_by_key_not_position(tmp_path):
    _readiness(tmp_path, [])
    request = {
        "odd": {
            "nested": {
                "source": {
                    "width_m": 0.3712,
                    "height_m": 0.5,
                    "depth_m": 0.36,
                    "port_area_m2": 0.002827433388,
                }
            }
        },
        "horn": {
            "mesh_path": "C:\\somewhere\\lecleach_rollback_1in_v6_9e02db06ecc3\\mesh.msh",
            "mesh_sha256": "9b4057c2",
            "translation_mm": [0.0, 0.0, 10.0],
        },
        "seed": {"source_record": {"net_volume_l": 115.0, "tuning_hz": 30.0, "port_throat_area_cm2": 45.0}},
        "mapping": {"driver_id": "FaitalPRO 12PR300"},
    }
    _write_case(
        tmp_path,
        "exp",
        "20261118T225108Z-meta",
        payload=_payload(run=None),
        files={"request.json": request},
    )
    # A second case with none of the keys: every number must be null, never guessed.
    _write_case(tmp_path, "exp", "20261118T225109Z-empty", payload=_payload(run=None))

    document, _screens, _written, _ok, _out = _run(tmp_path)
    rows = _rows(document)
    row = rows["exp/20261118T225108Z-meta"]
    assert row["box_width_mm"] == 371.2
    assert row["box_height_mm"] == 500.0
    assert row["box_depth_mm"] == 360.0
    assert row["port_area_cm2"] == 45.0
    assert row["net_volume_l"] == 115.0
    assert row["net_volume_source"] == "declared"
    assert row["tuning_hz"] == 30.0
    assert row["horn_mesh"] == "lecleach_rollback_1in_v6_9e02db06ecc3"
    assert row["horn_mesh_sha256"] == "9b4057c2"
    assert row["horn_offset_mm"] == 10.0
    assert row["horn_offset_mm_xyz"] == [0.0, 0.0, 10.0]
    assert row["driver_name"] == "FaitalPRO 12PR300"

    empty = rows["exp/20261118T225109Z-empty"]
    for field in (
        "box_width_mm",
        "box_height_mm",
        "box_depth_mm",
        "port_area_cm2",
        "net_volume_l",
        "tuning_hz",
        "horn_mesh",
        "horn_offset_mm",
        "driver_name",
    ):
        assert empty[field] is None, field


def test_air_volume_fallback_and_clearance_record(tmp_path):
    _readiness(tmp_path, [])
    stage = {
        "assertions": {"air_volume_m3": 0.042169449931},
        "clearance": {"status": "FAIL", "min_gap_m": 0.0007, "source": "synthetic"},
    }
    _write_case(
        tmp_path,
        "exp",
        "20261118T225108Z-clear",
        payload=_payload(run=None),
        files={"stage_report.json": stage},
    )
    document, _screens, _written, _ok, _out = _run(tmp_path)
    row = document["cases"][0]
    assert row["net_volume_l"] == 42.169
    assert row["net_volume_source"] == "air_volume_m3"
    assert row["clearance_status"] == "violation"
    assert row["clearance_min_mm"] == 0.7


# --------------------------------------------------------------------------- output shape


def test_deterministic_order_csv_columns_and_no_absolute_paths(tmp_path):
    _readiness(tmp_path, [])
    _write_case(tmp_path, "zeta", "20261118T225108Z-b", payload=_payload(run=None))
    _write_case(tmp_path, "alpha", "20261118T225109Z-z", payload=_payload(run=None))
    _write_case(tmp_path, "alpha", "20261118T225108Z-a", payload=_payload(), run_manifest=RUN_MANIFEST)

    first, _screens, written, _ok, out = _run(tmp_path, pretty=True)
    second, _screens2, _written2, _ok2, _out2 = _run(tmp_path, pretty=True)

    assert [row["case_key"] for row in first["cases"]] == [
        "alpha/20261118T225108Z-a",
        "alpha/20261118T225109Z-z",
        "zeta/20261118T225108Z-b",
    ]
    strip = lambda doc: {  # noqa: E731 - tiny inline helper
        key: value for key, value in doc.items() if key != "generated_utc"
    }
    assert strip(first) == strip(second)

    assert written == ["system_cases.csv", "system_cases.json", "system_screens.json"]
    header, rows = _read_csv(out / "system_cases.csv")
    assert len(rows) == 3
    for column in (
        "experiment",
        "case",
        "case_key",
        "status",
        "solved",
        "n_frequencies",
        "freq_min_hz",
        "freq_max_hz",
        "backend_id",
        "solve_kind",
        "phasor_convention",
        "completion",
        "fidelity",
        "manifest_integrity",
        "box_width_mm",
        "clearance_status",
        "source_path",
    ):
        assert column in header
    raw = (out / "system_cases.csv").read_bytes()
    assert b"\r\n" not in raw
    text = raw.decode("utf-8")
    assert str(tmp_path) not in text
    assert "C:\\" not in text
    assert rows[0]["source_path"].startswith("system_runs/system/")


def test_json_is_valid_and_keeps_nested_run_detail(tmp_path):
    _readiness(tmp_path, [])
    _write_case(tmp_path, "exp", "20261118T225108Z-run", payload=_payload(), run_manifest=RUN_MANIFEST)
    _first, _screens, _written, _ok, out = _run(tmp_path)
    document = json.loads((out / "system_cases.json").read_text(encoding="utf-8"))
    row = document["cases"][0]
    assert row["run"]["present"] is True
    assert row["run"]["frequencies_hz"] == [250.0, 700.0, 1100.0]
    assert row["run"]["completion_mask"] == {"done": 3, "total": 3, "complete": True}
    assert row["run"]["engine_runs"][0]["name"] == "BEAT Engine"
    assert row["metadata"]["sources"]
    assert document["census"]["by_status"] == {"solved": 1}


def test_screens_scan_and_no_screens_flag(tmp_path):
    _readiness(tmp_path, [])
    screen_dir = tmp_path / "system_runs" / "seed_study"
    screen_dir.mkdir(parents=True)
    shortlist = [
        {"candidate_id": "c1", "driver_id": "faitalpro_10pr300", "match": {"e_shape": 0.1}},
        {"candidate_id": "c2", "driver_id": "faitalpro_12pr300", "match": {"e_shape": 0.2}},
    ]
    screen = {
        "schema": "hornlab.system.woofer_seed.v1",
        "study_id": "abc123",
        "system_objective_version": 1,
        "claim": "synthetic",
        "input_sha256": {"drivers": "d", "horn_envelope": "e"},
        "counts": {
            "drivers_loaded": 4,
            "drivers_rejected": 1,
            "boxes_considered": 32,
            "boxes_rejected": 18,
            "candidates_kept": 14,
            "pareto_front_rows": 5,
            "shortlist_rows": 2,
            "bl_panel_fit_rejected": 3,
        },
        "envelope": {"width_mm": 320.0, "height_mm": 500.0, "depth_mm": 360.0},
        "catalog": [{"driver_id": "faitalpro_10pr300"}, {"driver_id": "faitalpro_12pr300"}],
        "kept_rows": [{"candidate_id": "c1"}, {"candidate_id": "c2"}],
        "rejected_ledger": [{"stage": "panel_fit"}],
        "shortlist": shortlist,
    }
    (screen_dir / "woofer_seed.json").write_text(json.dumps(screen), encoding="utf-8")

    document, screens, written, _ok, out = _run(tmp_path)
    assert "system_screens.json" in written
    assert (out / "system_screens.json").is_file()
    assert screens["census"]["files"] == 1
    study = screens["studies"][0]
    assert study["study_id"] == "abc123"
    assert study["path"] == "system_runs/seed_study/woofer_seed.json"
    assert study["shortlist"] == shortlist  # verbatim rows
    assert study["counts"]["drivers_loaded"] == 4
    assert study["counts"]["bl_panel_fit_rejected"] == 3
    assert study["counts"]["shortlist_rows"] == 2
    assert study["input_sha256"] == {"drivers": "d", "horn_envelope": "e"}
    assert study["kept_rows_count"] == 2
    assert study["rejected_ledger_count"] == 1
    assert study["catalog_driver_ids"] == ["faitalpro_10pr300", "faitalpro_12pr300"]
    assert document["census"]["included"] == 0

    _document, screens_off, written_off, _ok_off, out_off = _run(tmp_path, write_screens=False)
    assert screens_off is None
    assert "system_screens.json" not in written_off
    assert not (out_off / "system_screens.json").exists()


# --------------------------------------------------------------------------- CLI


def test_cli_writes_default_names_and_flags(tmp_path):
    _readiness(tmp_path, [])
    _write_case(tmp_path, "exp", "20261118T225108Z-a", payload=_payload(), run_manifest=RUN_MANIFEST)

    out = tmp_path / "cli_out"
    assert system_cases.main(["--root", str(tmp_path), "--out", str(out), "--pretty"]) == 0
    assert (out / "system_cases.csv").is_file()
    assert (out / "system_cases.json").is_file()
    assert (out / "system_screens.json").is_file()
    assert b"\r\n" not in (out / "system_cases.json").read_bytes()
    assert b"\r\n" not in (out / "system_cases.csv").read_bytes()

    out_no_csv = tmp_path / "cli_no_csv"
    assert (
        system_cases.main(
            ["--root", str(tmp_path), "--out", str(out_no_csv), "--no-csv", "--no-screens", "--quiet"]
        )
        == 0
    )
    assert not (out_no_csv / "system_cases.csv").exists()
    assert (out_no_csv / "system_cases.json").is_file()
    assert not (out_no_csv / "system_screens.json").exists()


def test_cli_strict_exit_codes(tmp_path):
    _readiness(tmp_path, [])
    _write_case(tmp_path, "exp", "20261118T225108Z-bad", raw_manifest="{broken")
    out = tmp_path / "out"

    assert system_cases.main(["--root", str(tmp_path), "--out", str(out), "--quiet"]) == 0
    assert (
        system_cases.main(["--root", str(tmp_path), "--out", str(out), "--quiet", "--strict"]) == 1
    )


# --------------------------------------------------------------------------- real bundle (optional)


def test_committed_bundle_smoke():
    """Optional: only when the generated bundle exists in this checkout."""
    data_dir = REPO / "docs" / "system_data"
    json_path = data_dir / "system_cases.json"
    if not json_path.is_file():
        pytest.skip("docs/system_data not generated in this checkout")
    document = json.loads(json_path.read_text(encoding="utf-8"))
    assert document["tool"] == "system_cases"
    assert set(document["census"]) >= {"scanned", "included", "by_status"}
    header, rows = _read_csv(data_dir / "system_cases.csv")
    assert len(rows) == len(document["cases"]) == document["census"]["included"]
    assert {"case_key", "status", "fidelity", "manifest_integrity"}.issubset(header)
    assert all(row["fidelity"] for row in document["cases"])
    assert all(row["status"] in {"solved", "staged", "refused", "invalid"} for row in document["cases"])
    assert "C:\\" not in (data_dir / "system_cases.csv").read_text(encoding="utf-8")
