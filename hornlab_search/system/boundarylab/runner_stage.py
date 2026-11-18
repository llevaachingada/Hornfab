"""BL-side stage runner: executed BY Boundary Lab's own interpreter (stdlib + blab only).

Contract
--------
``runner_stage.py <spec.json>`` reads one JSON spec, reproduces the upstream generator flow
(``tests/test_vented_enclosure_generator.py``) inside Boundary Lab:

    ProviderCatalog.scan -> factory(provider, "backend") -> create_session(GenerationRequest)
    -> session.generate() -> complete_generation() -> stage_generation()
    -> PhysicalSystemCompiler().compile() -> physical_system_to_dict()
    -> generator_document_to_payload() -> write_project_file()
    -> load_headless_project() -> prepare_system_solve()

and prints NDJSON on stdout:

    {"event":"status","message":...}
    {"ok":true, "project_path":..., "meshes":[...], "mesh_info":..., "assertions":{...}}
    {"ok":false,"error_type":..., "error":..., "traceback_tail":[...]}

Exit codes: 0 success, 2 bad spec, 3 staging/generation failure, 4 assertion failure.
The HornLab adapter never imports blab; this file only runs under BL's python and writes
ONLY under ``case_dir`` (mesh artifacts land in ``case_dir/bl_output``).

Optional Stage 2 block (``spec["horn"]``): a closed horn ``.msh`` is added as an imported
``MeshPurpose.BEM_SURFACE`` resource on the SAME seeded unbounded region, one rigid boundary
per horn surface group, and one ``ideal_velocity_source`` component + ``normal_velocity``
port on the group named by the caller. Nothing is guessed: an unknown group name fails the run.
"""
from __future__ import annotations

import hashlib
import json
import sys
import traceback
from dataclasses import replace
from pathlib import Path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
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


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in str(value).strip().lower()).strip("-") or "item"


def _mesh_entries(geometry) -> list[dict]:
    entries = []
    for mesh in geometry.meshes:
        path = Path(mesh.mesh_path) if mesh.mesh_path is not None else None
        entries.append(
            {
                "id": mesh.id,
                "purpose": mesh.purpose,
                "path": None if path is None else str(path),
                "sha256": None if path is None else _sha256_file(path),
                "size_bytes": None if path is None else path.stat().st_size,
            }
        )
    return entries


def _stage_horn(system, horn: dict) -> tuple[object, dict]:
    """Add a closed horn BEM mesh to the seeded unbounded region (host authoring model).

    Modelling decision (recorded in the case manifest): the horn surface is a rigid scatterer
    except for the caller-named source group, which becomes a ``moving`` boundary owned by one
    ``ideal_velocity_source`` component with a single ``normal_velocity`` excitation port.
    """
    from blab.mesh_inventory import InventoryEntry, inspect_system_meshes
    from blab.physical_model import (
        AcousticRegionKind,
        Boundary,
        BoundaryKind,
        ComponentKind,
        ExcitationPort,
        ExcitationPortKind,
        MeshPurpose,
        MeshResource,
        PhysicalComponent,
        PhysicalGroupRef,
    )

    mesh_path = Path(horn["mesh_path"])
    if not mesh_path.is_file():
        raise FileNotFoundError(f"horn mesh not found: {mesh_path}")
    name = str(horn["name"])
    scale_factor = float(horn.get("scale_factor", 1.0))
    translation_mm = tuple(float(value) for value in horn.get("translation_mm", (0.0, 0.0, 0.0)))
    source_group = str(horn["source_group"])

    entry = InventoryEntry(
        name=name,
        source_file=str(mesh_path),
        scale_factor=scale_factor,
        translation_mm=translation_mm,
        enabled=True,
    )
    inspected = inspect_system_meshes((entry,))[0]
    groups = tuple(inspected.surface_groups)
    if not groups:
        raise ValueError(f"horn mesh {mesh_path} has no 2D physical groups; cannot assign boundaries.")
    if source_group not in groups:
        raise ValueError(
            f"horn source_group {source_group!r} is not a 2D physical group of {mesh_path}; "
            f"available: {', '.join(groups)}"
        )
    if inspected.has_tetrahedra:
        raise ValueError(f"horn mesh {mesh_path} contains tetrahedra; expected a BEM surface mesh.")

    mesh_id = f"mesh:{_slug(name)}"
    system_ids = {item.id for item in system.meshes}
    if mesh_id in system_ids:
        raise ValueError(f"horn mesh id {mesh_id!r} already exists in the physical system.")

    unbounded = [region for region in system.regions if region.kind == AcousticRegionKind.UNBOUNDED_AIR]
    if len(unbounded) != 1:
        raise ValueError(f"expected exactly one unbounded region, found {len(unbounded)}")
    exterior = unbounded[0]

    resource = MeshResource(
        id=mesh_id,
        name=name,
        file=str(mesh_path.resolve()),
        purpose=MeshPurpose.BEM_SURFACE,
        scale_to_m=scale_factor,
        translation_m=tuple(value / 1000.0 for value in translation_mm),
    )

    boundaries = list(system.boundaries)
    source_boundary_id = None
    for group_name in groups:
        boundary_id = f"boundary:{_slug(name)}:{_slug(group_name)}"
        boundaries.append(
            Boundary(
                id=boundary_id,
                name=group_name,
                region_id=exterior.id,
                group=PhysicalGroupRef(mesh_id=mesh_id, dimension=2, name=group_name),
                kind=BoundaryKind.MOVING if group_name == source_group else BoundaryKind.RIGID,
            )
        )
        if group_name == source_group:
            source_boundary_id = boundary_id
    assert source_boundary_id is not None

    component_id = f"component:{_slug(name)}"
    port_id = f"excitation:{_slug(name)}"
    component = PhysicalComponent(
        id=component_id,
        name=f"{name} source",
        kind=ComponentKind.IDEAL_VELOCITY_SOURCE,
        boundary_ids=(source_boundary_id,),
        parameters={
            "motion_profile": "uniform",
            "boundary_motion_weights": {source_boundary_id: 1.0},
        },
    )
    port = ExcitationPort(
        id=port_id,
        name=f"{name} unit normal velocity",
        component_id=component_id,
        kind=ExcitationPortKind.NORMAL_VELOCITY,
    )

    updated = replace(
        system,
        meshes=(*system.meshes, resource),
        regions=tuple(
            replace(region, mesh_ids=(*region.mesh_ids, mesh_id)) if region.id == exterior.id else region
            for region in system.regions
        ),
        boundaries=tuple(boundaries),
        components=(*system.components, component),
        excitation_ports=(*system.excitation_ports, port),
    )
    imported_mesh_row = {
        "cleaned_file": None,
        "enabled": True,
        "name": name,
        "scale_factor": scale_factor,
        "source_file": str(mesh_path.resolve()),
        "translation_mm": list(translation_mm),
    }
    decision = {
        "kind": "horn_import_decisions",
        "mesh_role": str(horn.get("mesh_role", "full_domain")),
        "mesh_id": mesh_id,
        "mesh_file": str(mesh_path.resolve()),
        "mesh_sha256": _sha256_file(mesh_path),
        "mesh_name": name,
        "scale_to_m": scale_factor,
        "translation_mm": list(translation_mm),
        "imported_mesh_row": imported_mesh_row,
        "region_id": exterior.id,
        "surface_groups": list(groups),
        "rigid_groups": [group for group in groups if group != source_group],
        "moving_group": source_group,
        "source_component_id": component_id,
        "source_component_kind": ComponentKind.IDEAL_VELOCITY_SOURCE.value,
        "source_parameters": {
            "motion_profile": "uniform",
            "boundary_motion_weights": {source_boundary_id: 1.0},
        },
        "excitation_port": {"id": port_id, "kind": ExcitationPortKind.NORMAL_VELOCITY.value},
        "note": (
            "deliberate model choice: the named horn surface group is driven as an independent "
            "ideal normal-velocity source (unit m/s); every other horn group is a rigid BEM wall. "
            "No electrical port is added for the horn."
        ),
    }
    return updated, decision


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        _emit({"ok": False, "error_type": "UsageError", "error": "runner needs exactly one spec path"})
        return 2
    spec = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    try:
        _require(spec, "case_dir", "provider_root", "provider_id", "source",
                 "document_id", "document_name", "mesh_name", "case_name")
    except KeyError as exc:
        _emit({"ok": False, "error_type": "SpecError", "error": str(exc)})
        return 2

    case_dir = Path(spec["case_dir"])
    case_dir.mkdir(parents=True, exist_ok=True)
    preferences = dict(spec.get("preferences") or {})
    horn_spec = spec.get("horn")

    try:
        from blab.generators import GenerationRequest
        from blab.generators.application import stage_generation
        from blab.generators.base import complete_generation
        from blab.generators.catalog import ProviderCatalog
        from blab.generators.configuration import configuration_snapshot
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
        return 3

    try:
        catalog = ProviderCatalog([spec["provider_root"]], enabled=[spec["provider_id"]])
        catalog.scan()
        package = catalog.package(spec["provider_id"])
        backend = catalog.factory(spec["provider_id"], "backend")()
        _status(f"provider {package.manifest.id} {package.manifest.version} scanned")

        document = replace(
            new_generator_document(
                spec["document_name"],
                provider_id=spec["provider_id"],
                provider_schema_version=package.manifest.source_schema_version,
                source=dict(spec["source"]),
            ),
            id=str(spec["document_id"]),
            mesh_scale_factor=float(package.manifest.mesh_scale_factor),
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
        system = project.physical_system
        _status(
            "staged physical system: "
            f"{len(system.meshes)} meshes, {len(system.regions)} regions, "
            f"{len(system.boundaries)} boundaries, {len(system.interfaces)} interfaces, "
            f"{len(system.components)} components, {len(system.excitation_ports)} ports"
        )

        horn_decision = None
        expected_ports = 1
        if horn_spec:
            if project.symmetry != "off":
                raise ValueError("horn import requires project symmetry 'off'")
            system, horn_decision = _stage_horn(system, horn_spec)
            project.physical_system = system
            expected_ports = 2
            _status(
                "horn import applied: "
                f"groups {', '.join(horn_decision['surface_groups'])}; "
                f"rigid {', '.join(horn_decision['rigid_groups'])}; "
                f"moving {horn_decision['moving_group']}"
            )

        compiled = PhysicalSystemCompiler().compile(system)
        prepared = prepare_system_solve(
            system,
            freq_min_hz=float(preferences.get("freq_min_hz", 30.0)),
            freq_max_hz=float(preferences.get("freq_max_hz", 100.0)),
            freq_count=int(preferences.get("freq_count", 3)),
            observation_distance_m=float(preferences.get("observation_distance_m", 2.0)),
            polar_angle_step_deg=float(preferences.get("polar_angle_step_deg", 90.0)),
        )

        mesh_info_path = Path(geometry.output_dir) / "mesh_info.json"
        mesh_info = json.loads(mesh_info_path.read_text(encoding="utf-8")) if mesh_info_path.is_file() else None
        air_volume = None if mesh_info is None else mesh_info.get("air_volume_m3")
        interior = None if mesh_info is None else mesh_info.get("interior") or {}
        interior_tetrahedra = None if interior is None else interior.get("tetrahedra")

        assertions = {
            "interface_count": len(compiled.interfaces),
            "region_count": len(system.regions),
            "component_kinds": [component.kind.value for component in system.components],
            "excitation_port_kinds": [port.kind.value for port in system.excitation_ports],
            "excitation_port_ids": list(prepared.request.excitation_port_ids),
            "solve_kind": prepared.solve_kind.value,
            "bounded_region_count": sum(1 for region in system.regions if region.kind == "bounded_air"),
            "unbounded_region_count": sum(1 for region in system.regions if region.kind == "unbounded_air"),
            "air_volume_m3": air_volume,
            "interior_tetrahedra": interior_tetrahedra,
            "mesh_ids": [mesh.id for mesh in system.meshes],
            "boundary_kinds": {boundary.id: boundary.kind.value for boundary in system.boundaries},
        }

        driver = next(
            (component for component in system.components if component.kind.value == "electrodynamic_transducer"),
            None,
        )
        checks = {
            "interface_count": (len(compiled.interfaces), 1),
            "region_count": (len(system.regions), 2),
            "solve_kind": (prepared.solve_kind.value, "coupled_bem_fem"),
            "excitation_port_count": (len(prepared.request.excitation_port_ids), expected_ports),
            "electrodynamic_component": (driver is not None, True),
        }
        expectations = dict(spec.get("expectations") or {})
        if "mmd_kg" in expectations:
            checks["driver_mmd_kg"] = (
                None if driver is None else driver.parameters.get("mmd_kg"),
                float(expectations["mmd_kg"]),
            )
        if "motion_axis" in expectations:
            checks["driver_motion_axis"] = (
                None if driver is None else driver.parameters.get("motion_axis"),
                [float(value) for value in expectations["motion_axis"]],
            )
        if expectations.get("air_volume_m3_min") is not None:
            checks["air_volume_m3"] = (
                air_volume,
                ("between", float(expectations["air_volume_m3_min"]),
                 float(expectations["air_volume_m3_max"])),
            )
        if expectations.get("interior_tetrahedra_min") is not None:
            checks["interior_tetrahedra"] = (
                interior_tetrahedra,
                ("at_least", int(expectations["interior_tetrahedra_min"])),
            )

        failures = []
        for name, (actual, expected) in checks.items():
            ok = False
            if isinstance(expected, tuple) and expected and expected[0] == "between":
                ok = actual is not None and expected[1] < float(actual) < expected[2]
            elif isinstance(expected, tuple) and expected and expected[0] == "at_least":
                ok = actual is not None and float(actual) >= expected[1]
            else:
                ok = actual == expected
            if not ok:
                failures.append(f"{name}: got {actual!r}, expected {expected!r}")

        project_path = write_project_file(
            case_dir / "case.blab.json",
            {
                "schema_version": PROJECT_SCHEMA_VERSION,
                "active_generator_document_id": project.generator_documents[0].id,
                "generator_documents": [
                    generator_document_to_payload(project.generator_documents[0], absolute_paths=True)
                ],
                "imported_meshes": [horn_decision["imported_mesh_row"]] if horn_decision else [],
                "stitch_exterior_meshes": False,
                "symmetry": project.symmetry,
                "component_channel_by_id": dict(project.component_channel_by_id),
                "physical_system": physical_system_to_dict(system),
            },
        )
        _status(f"wrote project {project_path}")

        reopened = load_headless_project(project_path)
        reopened_compiled = PhysicalSystemCompiler().compile(reopened.physical_system)
        reopened_interfaces = len(reopened_compiled.interfaces)
        reopened_ports = [port.id for port in reopened.physical_system.excitation_ports]
        reopened_solve_kind = prepare_system_solve(
            reopened.physical_system,
            freq_min_hz=float(preferences.get("freq_min_hz", 30.0)),
            freq_max_hz=float(preferences.get("freq_max_hz", 100.0)),
            freq_count=int(preferences.get("freq_count", 3)),
            observation_distance_m=float(preferences.get("observation_distance_m", 2.0)),
            polar_angle_step_deg=float(preferences.get("polar_angle_step_deg", 90.0)),
        ).solve_kind.value
        checks["reopened_interface_count"] = (reopened_interfaces, 1)
        checks["reopened_solve_kind"] = (reopened_solve_kind, "coupled_bem_fem")
        checks["reopened_excitation_ports"] = (sorted(reopened_ports),
                                              sorted(assertions["excitation_port_ids"]))
        if reopened_interfaces != 1 or reopened_solve_kind != "coupled_bem_fem":
            failures.append(
                f"reopen verification failed: interfaces={reopened_interfaces}, "
                f"solve_kind={reopened_solve_kind}"
            )

        report = {
            "ok": not failures,
            "project_path": str(project_path),
            "case_dir": str(case_dir),
            "output_dir": str(geometry.output_dir),
            "meshes": _mesh_entries(geometry),
            "mesh_info": mesh_info,
            "mesh_info_sha256": _sha256_file(mesh_info_path) if mesh_info_path.is_file() else None,
            "port_mouth_diameter_m": (geometry.provider_metadata or {}).get("port_mouth_diameter_m"),
            "physical_system": {
                "id": system.id,
                "name": system.name,
                "model_version": system.model_version,
                "mesh_ids": [mesh.id for mesh in system.meshes],
                "region_ids": [region.id for region in system.regions],
                "boundary_ids": [boundary.id for boundary in system.boundaries],
                "interface_ids": [interface.id for interface in system.interfaces],
                "component_ids": [component.id for component in system.components],
                "excitation_port_ids": [port.id for port in system.excitation_ports],
            },
            "assertions": assertions,
            "verification": {
                "checks": {name: {"actual": actual, "expected": expected}
                           for name, (actual, expected) in checks.items()},
                "failures": failures,
            },
            "horn": horn_decision,
        }
        if horn_decision is not None:
            _status("horn import row recorded in the project's imported_meshes")
        (case_dir / "stage_report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
        )
        if failures:
            _emit({"ok": False, "error_type": "AssertionError",
                   "error": "; ".join(failures), "report": report})
            return 4
        _emit(report)
        return 0
    except Exception as exc:  # BL validation/meshing errors, schema gaps, missing groups
        _emit({"ok": False, "error_type": type(exc).__name__, "error": str(exc),
               "traceback_tail": "".join(traceback.format_exc()).splitlines()[-12:]})
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
