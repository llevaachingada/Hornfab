"""BL-side runner: real driver T/S through BL's sanctioned component-parameters patch.

Executed BY Boundary Lab's own interpreter (stdlib + blab only), exactly like
``runner_stage.py``. It reproduces the upstream generator flow, stages the generated
assembly, then applies a SECOND configuration patch through BL's public
``apply_configuration_patch``:

    ProviderCatalog.scan -> factory(provider, "backend") -> create_session(GenerationRequest)
    -> session.generate() -> complete_generation() -> stage_generation()
    -> apply_configuration_patch({"component_parameters": {component_id: params}})
    -> PhysicalSystemCompiler().compile() -> physical_system_to_dict()
    -> write_project_file() -> load_headless_project()

The provider hard-codes ``DRIVER_DEFAULTS`` in its own configuration patch (backend.py line 56);
this second, caller-owned patch replaces those values per component id. Nothing here imports
``hornlab_search``: the mapping is decided host-side and carried in the spec JSON.

NDJSON on stdout:
    {"event":"status","message":...}
    {"ok":true, "project_path":..., "component_parameters": {...}, ...}
    {"ok":false,"error_type":..., "error":..., "traceback_tail":[...]}
Exit codes: 0 success, 2 bad spec, 3 staging failure, 4 assertion failure.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import math
import sys
import traceback
from pathlib import Path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _emit(payload: dict) -> None:
    print(json.dumps(payload, sort_keys=True), flush=True)


def _status(message: str) -> None:
    _emit({"event": "status", "message": str(message)})


def _require(spec: dict, *keys: str) -> None:
    missing = [key for key in keys if key not in spec]
    if missing:
        raise KeyError("spec missing " + ", ".join(repr(key) for key in missing))


def _patch_sha256(patch: dict) -> str:
    """Same canonical convention as ``hornlab_search.system.contracts.canonical_json``.

    Floats round to 12 decimals, mapping keys stringify and sort, separators are compact.
    """
    def _fix(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return round(float(value), 12)
        if isinstance(value, dict):
            return {str(key): _fix(item) for key, item in
                    sorted(value.items(), key=lambda pair: str(pair[0]))}
        if isinstance(value, (list, tuple)):
            return [_fix(item) for item in value]
        return str(value)

    return hashlib.sha256(
        json.dumps(_fix(patch), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _component_from_system(system_dict: dict, component_id: str) -> dict:
    for component in system_dict.get("components", []):
        if component.get("id") == component_id:
            return component
    raise KeyError(f"component {component_id!r} missing from serialized physical_system")


def _compare(actual: object, expected: object, *, tol: float = 1e-12) -> bool:
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(_compare(a, e, tol=tol) for a, e in zip(actual, expected))
        )
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            return False
        return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=tol)
    return actual == expected


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        _emit({"ok": False, "error_type": "UsageError", "error": "runner needs exactly one spec path"})
        return 2
    spec = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    try:
        _require(spec, "case_dir", "provider_root", "provider_dir", "provider_id", "source",
                 "document_id", "document_name", "mesh_name", "case_name", "component_id",
                 "component_parameters", "expectations")
    except KeyError as exc:
        _emit({"ok": False, "error_type": "SpecError", "error": str(exc)})
        return 2

    case_dir = Path(spec["case_dir"])
    case_dir.mkdir(parents=True, exist_ok=True)
    component_id = str(spec["component_id"])
    parameters = {str(key): value for key, value in spec["component_parameters"].items()}
    expectations = dict(spec["expectations"])
    preferences = dict(spec.get("preferences") or {})

    try:
        from blab.generators import GenerationRequest
        from blab.generators.application import stage_generation
        from blab.generators.base import complete_generation, generated_mesh_id
        from blab.generators.catalog import ProviderCatalog
        from blab.generators.configuration import (
            apply_configuration_patch,
            configuration_snapshot,
            validate_patch,
        )
        from blab.headless import load_headless_project
        from blab.physical_compiler import PhysicalSystemCompiler
        from blab.physical_model import physical_system_to_dict
        from blab.project.io import PROJECT_SCHEMA_VERSION, write_project_file
        from blab.project.model import (
            ProjectDocument,
            generator_document_to_payload,
            new_generator_document,
        )
        from blab.system_solve import prepare_system_solve
    except ImportError as exc:
        _emit({"ok": False, "error_type": type(exc).__name__,
               "error": f"blab is not importable in this interpreter: {exc}"})
        return 2

    try:
        # BL's own source validator is the authority for the geometry attempt (no meshing).
        geometry_check = None
        attempt = spec.get("geometry_attempt")
        if attempt:
            provider_dir = str(Path(spec["provider_dir"]))
            if provider_dir not in sys.path:
                sys.path.insert(0, provider_dir)
            from enclosure.parameters import validate as validate_source  # type: ignore
            try:
                validate_source(dict(attempt["source"]))
                geometry_check = {"label": attempt.get("label"), "ok": True,
                                  "error_type": None, "error": None,
                                  "source_sha256": _patch_sha256(dict(attempt["source"]))}
                _status(f"geometry attempt {attempt.get('label')!r}: BL source validator ACCEPTED")
            except Exception as exc:  # BL ValueError on a physically impossible panel
                geometry_check = {"label": attempt.get("label"), "ok": False,
                                  "error_type": type(exc).__name__, "error": str(exc),
                                  "source_sha256": _patch_sha256(dict(attempt["source"]))}
                _status(f"geometry attempt {attempt.get('label')!r}: BL refused: {exc}")

        catalog = ProviderCatalog([spec["provider_root"]], enabled=[spec["provider_id"]])
        catalog.scan()
        package = catalog.package(spec["provider_id"])
        backend = catalog.factory(spec["provider_id"], "backend")()
        _status(f"provider {package.manifest.id} {package.manifest.version} scanned")

        document = replace_document(
            new_generator_document(
                spec["document_name"],
                provider_id=spec["provider_id"],
                provider_schema_version=package.manifest.source_schema_version,
                source=dict(spec["source"]),
            ),
            document_id=str(spec["document_id"]),
            mesh_scale=float(package.manifest.mesh_scale_factor),
        )
        project = ProjectDocument((document,), document.id)
        request = GenerationRequest(
            provider_id=spec["provider_id"],
            document_id=document.id,
            mesh_name=spec["mesh_name"],
            source=document.source,
            run_root=case_dir / "bl_output",
            case_name=spec["case_name"],
            configuration=configuration_snapshot(project),
        )
        session = backend.create_session(request)
        response = session.generate(status_callback=_status)
        geometry = response.geometry
        _status(f"generated {len(geometry.meshes)} meshes under {geometry.output_dir}")

        project = stage_generation(project, {}, complete_generation(request, response))
        _status(
            "staged physical system: "
            f"{len(project.physical_system.meshes)} meshes, "
            f"{len(project.physical_system.components)} components"
        )

        mesh_ids = {
            generated_mesh_id(document.id, key) for key in ("interior", "exterior")
        }
        patch = {"component_parameters": {component_id: parameters}}
        validate_patch(patch)  # BL's own patch schema check, before application
        project = apply_configuration_patch(
            project, patch, document_id=document.id, mesh_ids=mesh_ids)
        system = project.physical_system
        _status(f"component-parameters patch applied to {component_id}")

        compiled = PhysicalSystemCompiler().compile(system)
        prepared = prepare_system_solve(
            system,
            freq_min_hz=float(preferences.get("freq_min_hz", 30.0)),
            freq_max_hz=float(preferences.get("freq_max_hz", 100.0)),
            freq_count=int(preferences.get("freq_count", 3)),
            observation_distance_m=float(preferences.get("observation_distance_m", 2.0)),
            polar_angle_step_deg=float(preferences.get("polar_angle_step_deg", 90.0)),
        )
        system_dict = physical_system_to_dict(system)
        serialized = dict(_component_from_system(system_dict, component_id).get("parameters") or {})

        checks = {
            "interface_count": (len(compiled.interfaces), 1),
            "region_count": (len(system.regions), 2),
            "solve_kind": (prepared.solve_kind.value, "coupled_bem_fem"),
            "excitation_port_count": (len(prepared.request.excitation_port_ids), 1),
            "component_parameter_keys": (sorted(serialized), sorted(parameters)),
        }
        for name, expected in expectations.items():
            checks[f"component_{name}"] = (serialized.get(name), expected)

        failures = []
        for name, (actual, expected) in checks.items():
            ok = _compare(actual, expected) if not isinstance(expected, str) or name == "solve_kind" \
                else actual == expected
            if not ok:
                failures.append(f"{name}: got {actual!r}, expected {expected!r}")

        mesh_info_path = Path(geometry.output_dir) / "mesh_info.json"
        mesh_info = (json.loads(mesh_info_path.read_text(encoding="utf-8"))
                     if mesh_info_path.is_file() else None)
        air_volume = None if mesh_info is None else mesh_info.get("air_volume_m3")
        interior = None if mesh_info is None else (mesh_info.get("interior") or {})

        project_path = write_project_file(
            case_dir / "case.blab.json",
            {
                "schema_version": PROJECT_SCHEMA_VERSION,
                "active_generator_document_id": project.generator_documents[0].id,
                "generator_documents": [
                    generator_document_to_payload(
                        project.generator_documents[0], absolute_paths=True)
                ],
                "imported_meshes": [],
                "stitch_exterior_meshes": False,
                "symmetry": project.symmetry,
                "component_channel_by_id": dict(project.component_channel_by_id),
                "physical_system": system_dict,
            },
        )
        _status(f"wrote project {project_path}")

        reopened = load_headless_project(project_path)
        reopened_dict = physical_system_to_dict(reopened.physical_system)
        reopened_parameters = dict(
            _component_from_system(reopened_dict, component_id).get("parameters") or {})
        reopened_checks = {
            "reopened_mmd_kg": (reopened_parameters.get("mmd_kg"), parameters.get("mmd_kg")),
            "reopened_re_ohm": (reopened_parameters.get("re_ohm"), parameters.get("re_ohm")),
            "reopened_parameter_keys": (sorted(reopened_parameters), sorted(parameters)),
        }
        for name, (actual, expected) in reopened_checks.items():
            if not _compare(actual, expected):
                failures.append(f"{name}: got {actual!r}, expected {expected!r}")

        report = {
            "ok": not failures,
            "project_path": str(project_path),
            "case_dir": str(case_dir),
            "output_dir": str(geometry.output_dir),
            "meshes": [
                {
                    "id": mesh.id,
                    "purpose": mesh.purpose,
                    "path": None if mesh.mesh_path is None else str(mesh.mesh_path),
                    "sha256": (None if mesh.mesh_path is None
                               else _sha256_file(Path(mesh.mesh_path))),
                }
                for mesh in geometry.meshes
            ],
            "mesh_info": mesh_info,
            "air_volume_m3": air_volume,
            "interior_tetrahedra": None if interior is None else interior.get("tetrahedra"),
            "component_id": component_id,
            "component_parameters_before_patch": {
                key: value for key, value in (parameters.items())
            },
            "component_parameters_serialized": serialized,
            "component_parameters_reopened": reopened_parameters,
            "configuration_patch": patch,
            "configuration_patch_sha256": _patch_sha256(patch),
            "geometry_check": geometry_check,
            "assertions": {
                "mesh_ids": [mesh.id for mesh in system.meshes],
                "region_ids": [region.id for region in system.regions],
                "component_ids": [component.id for component in system.components],
                "excitation_port_ids": list(prepared.request.excitation_port_ids),
                "solve_kind": prepared.solve_kind.value,
            },
            "verification": {
                "checks": {name: {"actual": actual, "expected": expected}
                           for name, (actual, expected) in checks.items()},
                "reopened_checks": {
                    name: {"actual": actual, "expected": expected}
                    for name, (actual, expected) in reopened_checks.items()},
                "failures": failures,
            },
        }
        (case_dir / "stage_report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
        if failures:
            _emit({"ok": False, "error_type": "AssertionError",
                   "error": "; ".join(failures), "report": report})
            return 4
        _emit(report)
        return 0
    except Exception as exc:  # BL validation/meshing errors, schema gaps
        _emit({"ok": False, "error_type": type(exc).__name__, "error": str(exc),
               "traceback_tail": "".join(traceback.format_exc()).splitlines()[-12:]})
        return 3


def replace_document(document, *, document_id: str, mesh_scale: float):
    """Set the document id and mesh scale without importing ``dataclasses.replace`` semantics."""
    from dataclasses import replace

    return replace(document, id=document_id, mesh_scale_factor=mesh_scale)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
