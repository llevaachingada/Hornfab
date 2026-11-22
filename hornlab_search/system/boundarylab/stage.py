"""Stage REAL Boundary Lab PhysicalSystems through BL's own host path (no solver).

Why this module exists
----------------------
A ``.blab.json`` whose ``physical_system`` is hand-written or empty is not a Boundary Lab
project: BL's own loader rejects it with ``Unsupported physical model_version 0.``. The only
sanctioned producer of a PhysicalSystem is BL's host path:

    ProviderCatalog -> backend.create_session(GenerationRequest) -> generate()
    -> complete_generation() -> stage_generation() -> PhysicalSystemCompiler().compile()
    -> physical_system_to_dict() -> write_project_file()

That path cannot run in the HornLab venv (``blab`` must never be imported here: license and
dependency collisions). So, exactly like :mod:`.generate`, this adapter writes a spec JSON and
executes :mod:`runner_stage` with BOUNDARY LAB'S OWN interpreter. The runner prints NDJSON; the
adapter verifies the artifacts, runs the real ``blab project validate --json`` through
:func:`hornlab_search.system.boundarylab.run.validate_project`, and records an immutable,
self-checksummed case manifest in the isolated system store.

Stage 2 (horn import) adds one closed horn ``.msh`` as an imported ``BEM_SURFACE`` resource on
the SAME seeded unbounded region, with one rigid boundary per horn surface group and one
independent ``ideal_velocity_source`` + ``normal_velocity`` port on a caller-named group. Those
kind assignments are deliberate, code-level modelling decisions and are recorded verbatim in
the case manifest under ``result.horn``.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from hornlab_search.system import provenance
from hornlab_search.system.boundarylab import run as bl_run
from hornlab_search.system.boundarylab.clearance import DEFAULT_MIN_GAP_M, body_clearance
from hornlab_search.system.boundarylab.generate import (
    _MAX_LOG_LINES,
    _build_source,
    _execute,
    _parse_final_json,
)
from hornlab_search.system.boundarylab.probe import BLCapabilityError, BLRoot

__all__ = [
    "BLOCKED_BY_FULL_DOMAIN_HORN_MESH_INPUT",
    "StagedProject",
    "build_stage_spec",
    "runner_path",
    "stage_horn_project",
    "stage_reference_project",
    "resolve_full_domain_horn_mesh",
]

#: Blocker token used when Lane A's full-domain closed horn mesh is not present yet.
BLOCKED_BY_FULL_DOMAIN_HORN_MESH_INPUT = "BLOCKED_BY_FULL_DOMAIN_HORN_MESH_INPUT"

#: BL source files whose behaviour this staging depends on (hashed into every case manifest).
_STAGE_DEPENDENCIES: tuple[str, ...] = (
    "src/blab/generators/__init__.py",
    "src/blab/generators/application.py",
    "src/blab/generators/base.py",
    "src/blab/generators/catalog.py",
    "src/blab/generators/configuration.py",
    "src/blab/headless.py",
    "src/blab/mesh_inventory.py",
    "src/blab/physical_compiler.py",
    "src/blab/physical_model.py",
    "src/blab/project/io.py",
    "src/blab/project/migration.py",
    "src/blab/project/model.py",
    "src/blab/system_solve.py",
)

#: Upstream fixture assertions for the provider's manifest-default geometry.
_DEFAULT_EXPECTATIONS: dict[str, Any] = {
    "mmd_kg": 0.035,
    "motion_axis": [0.0, 0.0, 1.0],
    "air_volume_m3_min": 0.04,
    "air_volume_m3_max": 0.043,
    "interior_tetrahedra_min": 100,
}


def runner_path() -> Path:
    """Absolute path of the BL-side stage runner (executed by Boundary Lab's own Python)."""
    return Path(__file__).with_name("runner_stage.py")


@dataclass(frozen=True)
class StagedProject:
    """Verified artifacts of one staged PhysicalSystem project plus its provenance."""

    ok: bool
    case_dir: Path
    project_path: Path | None
    output_dir: Path | None
    meshes: tuple[dict, ...]
    mesh_info: Mapping[str, Any] | None
    validation: bl_run.ValidationResult | None
    manifest_path: Path | None
    captured_log_tail: tuple[str, ...]
    returncode: int
    detail: Mapping[str, object] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        """True only when BL's own ``project validate`` said ``valid: true`` (rc 0)."""
        parsed = None if self.validation is None else self.validation.parsed
        return bool(
            self.ok
            and self.validation is not None
            and self.validation.returncode == 0
            and isinstance(parsed, dict)
            and parsed.get("valid") is True
        )


def _require_verified(root: BLRoot) -> None:
    if not root.verified:
        raise BLCapabilityError(
            (f"BLRoot at {root.path} is not verified: " + " | ".join(root.missing),))


def _provider_root(root: BLRoot) -> str:
    """Directory ProviderCatalog scans (the parent of the vented provider package)."""
    provider_dir = root.provider_dir
    if not provider_dir:
        raise BLCapabilityError(("verified BLRoot has no provider directory",))
    package_dir = Path(provider_dir)
    return str(package_dir.parent if package_dir.name == "vented_enclosure" else package_dir)


def _stage_dependency_hashes(root: BLRoot) -> dict[str, str | None]:
    base = Path(root.path)
    hashes: dict[str, str | None] = {}
    for relative in _STAGE_DEPENDENCIES:
        path = base / relative
        hashes[relative] = provenance.file_sha256(path) if path.is_file() else None
    return hashes


def build_stage_spec(
    root: BLRoot,
    overrides: Mapping[str, float] | None = None,
    *,
    case_dir: str | os.PathLike[str],
    case_name: str = "ref_case",
    mesh_name: str = "vented",
    document_id: str = "vented",
    document_name: str = "vented",
    expectations: Mapping[str, Any] | None = None,
    horn: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The BL-side spec for one staging run (pure; used by tests and dry runs).

    ``source`` is the provider manifest's own ``default_source`` merged with numeric
    overrides — BL's parameters validator stays the only geometry authority.
    """
    _require_verified(root)
    manifest = root.detail.get("provider_manifest", {})
    started = {
        "case_dir": str(Path(case_dir)),
        "provider_root": _provider_root(root),
        "provider_id": manifest.get("id"),
        "source": _build_source(root, dict(overrides or {})),
        # The numeric overrides that produced ``source``, recorded explicitly so the case
        # manifest can show what the caller asked for (``source`` is the merged result).
        "overrides": dict(overrides or {}),
        "document_id": document_id,
        "document_name": document_name,
        "mesh_name": mesh_name,
        "case_name": case_name,
        "configuration": {"symmetry_config": {"mode": "off"}},
        "preferences": {
            "freq_min_hz": 30.0,
            "freq_max_hz": 100.0,
            "freq_count": 3,
            "observation_distance_m": 2.0,
            "polar_angle_step_deg": 90.0,
        },
        "expectations": dict(_DEFAULT_EXPECTATIONS if expectations is None else expectations),
        "runner_version": "v1",
    }
    if horn is not None:
        started["horn"] = dict(horn)
        # The horn body changes region coverage but not the vented fixture's air volume.
        started["expectations"] = {
            key: value for key, value in started["expectations"].items()
            if not key.startswith("air_volume_m3")
        }
    return started


def _validate_dict(result: bl_run.ValidationResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "returncode": result.returncode,
        "valid": None if result.parsed is None else result.parsed.get("valid"),
        "parsed": None if result.parsed is None else dict(result.parsed),
        "stdout_tail": list(result.stdout_tail[-12:]),
        "stderr_tail": list(result.stderr_tail[-12:]),
        "argv": list(result.argv),
    }


def _stage(
    root: BLRoot,
    spec: dict[str, Any],
    *,
    store_root: str | os.PathLike[str] | None,
    case_dir: Path | None,
    experiment_id: str,
    tag: str,
    timeout_s: float,
    cancel_path: Path | None,
    run_now: bool,
    kind: str,
    min_clearance_m: float = DEFAULT_MIN_GAP_M,
) -> StagedProject:
    resolved_case_dir = Path(case_dir) if case_dir is not None else provenance.new_case_dir(
        experiment_id, store_root=store_root, tag=tag)
    resolved_case_dir = Path(resolved_case_dir)
    spec["case_dir"] = str(resolved_case_dir)
    if not run_now:
        return StagedProject(
            ok=False, case_dir=resolved_case_dir, project_path=None, output_dir=None,
            meshes=(), mesh_info=None, validation=None, manifest_path=None,
            captured_log_tail=(), returncode=-1, detail={"spec_dry_run": spec},
        )
    resolved_case_dir.mkdir(parents=True, exist_ok=True)
    spec_path = resolved_case_dir / "adapter_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2, sort_keys=True), encoding="utf-8")

    python = root.python_executable
    if not python:
        raise BLCapabilityError(("verified BLRoot has no python executable",))
    argv = [python, "-I", "-B", str(runner_path()), str(spec_path)]
    code, log_lines = _execute(argv, timeout_s, cancel_path)
    final = _parse_final_json(log_lines)

    staged = code == 0 and final is not None and final.get("ok") is True
    project_path = Path(final["project_path"]) if staged and final else None
    meshes: tuple[dict, ...] = tuple(final["meshes"]) if staged and final else ()
    mesh_info = final.get("mesh_info") if staged and final else None
    validation = None
    if staged and project_path is not None:
        if not project_path.is_file():
            staged = False
            log_lines.append(f"[adapter] verification failed: project file missing: {project_path}")
        else:
            validation = bl_run.validate_project(root, project_path)
            if validation.returncode != 0 or not (validation.parsed or {}).get("valid"):
                staged = False
                parsed = validation.parsed or {}
                log_lines.append(
                    "[adapter] blab project validate rejected the staged project: rc="
                    f"{validation.returncode} parsed={json.dumps(parsed, sort_keys=True)}"
                )

    # R16: BL accepts intersecting separate bodies, so the horn-to-enclosure gap is checked
    # here and recorded in the manifest; a staged two-body project without a proven gap is
    # not "ok", whatever BL's validate said.
    clearance: dict[str, Any] | None = None
    horn_spec = spec.get("horn")
    if staged and horn_spec:
        surfaces = [m["path"] for m in meshes if m.get("purpose") == "bem_surface" and m.get("path")]
        try:
            report = body_clearance(
                horn_spec["mesh_path"], surfaces,
                translation_mm=horn_spec.get("translation_mm", (0.0, 0.0, 0.0)),
                scale_factor=float(horn_spec.get("scale_factor", 1.0)),
                min_gap_m=min_clearance_m,
            )
            clearance = report.to_dict()
        except (FileNotFoundError, ValueError) as exc:
            clearance = {"kind": "body_clearance_v1", "status": "BODY_CLEARANCE_UNCHECKED",
                         "min_gap_m": min_clearance_m, "error": f"{type(exc).__name__}: {exc}"}
        if clearance["status"] != "PASS":
            staged = False
            log_lines.append(
                f"[adapter] {clearance['status']}: horn-to-enclosure clearance not proven >= "
                f"{min_clearance_m} m (aabb_gap_m={clearance.get('aabb_gap_m')}, "
                f"vertex_min_distance_m={clearance.get('vertex_min_distance_m')})"
            )

    detail = {
        "argv": argv,
        "spec_sha256": provenance.file_sha256(spec_path),
        "runner_version": spec.get("runner_version"),
        "overrides": spec.get("overrides", {}),
    }
    manifest_payload: dict[str, Any] = {
        "kind": kind,
        "bl_root": root.to_dict(),
        "bl_dependency_hashes": _stage_dependency_hashes(root),
        "runner": str(runner_path()),
        "spec": spec,
        "detail": detail,
        "result": None if final is None else final,
        "validate": _validate_dict(validation),
    }
    if clearance is not None:
        manifest_payload["clearance"] = clearance
        detail["clearance_status"] = clearance["status"]
    if staged and project_path is not None:
        manifest_payload["project_sha256"] = provenance.file_sha256(project_path)
    manifest_path = provenance.write_manifest(resolved_case_dir, manifest_payload)
    output_dir = Path(final["output_dir"]) if final and final.get("output_dir") else None
    return StagedProject(
        ok=staged, case_dir=resolved_case_dir, project_path=project_path,
        output_dir=output_dir, meshes=meshes, mesh_info=mesh_info,
        validation=validation, manifest_path=manifest_path,
        captured_log_tail=tuple(log_lines[-_MAX_LOG_LINES:]), returncode=code, detail=detail,
    )


def stage_reference_project(
    root: BLRoot,
    overrides: Mapping[str, float] | None = None,
    *,
    store_root: str | os.PathLike[str] | None = None,
    case_dir: Path | None = None,
    experiment_id: str = "bl_ref_case",
    case_name: str = "ref_case",
    mesh_name: str = "vented",
    timeout_s: float = 1800.0,
    cancel_path: Path | None = None,
    run_now: bool = True,
) -> StagedProject:
    """Stage an R0 vented-only project and validate it with BL's own CLI.

    The generation/staging happens in BL's interpreter; ``blab project validate --json`` runs
    from BL's ``blab`` entry point. ``run_now=False`` returns the would-be spec only.
    """
    _require_verified(root)
    spec = build_stage_spec(
        root, overrides, case_dir=case_dir or provenance.default_store_root(),
        case_name=case_name, mesh_name=mesh_name,
    )
    return _stage(root, spec, store_root=store_root, case_dir=case_dir,
                  experiment_id=experiment_id, tag="ref_case", timeout_s=timeout_s,
                  cancel_path=cancel_path, run_now=run_now, kind="bl_stage_reference_project")


def stage_horn_project(
    root: BLRoot,
    horn_mesh: str | os.PathLike[str],
    *,
    source_group: str,
    overrides: Mapping[str, float] | None = None,
    horn_name: str = "horn",
    scale_factor: float = 1.0,
    translation_mm: tuple[float, float, float] = (0.0, 0.0, 0.0),
    mesh_role: str = "full_domain",
    store_root: str | os.PathLike[str] | None = None,
    case_dir: Path | None = None,
    experiment_id: str = "bl_horn_assembly",
    case_name: str = "horn_assembly",
    mesh_name: str = "vented",
    timeout_s: float = 1800.0,
    cancel_path: Path | None = None,
    run_now: bool = True,
    min_clearance_m: float = DEFAULT_MIN_GAP_M,
) -> StagedProject:
    """Stage the two-body project: seeded vented system + one imported closed horn BEM mesh.

    ``source_group`` must be one of the horn mesh's 2D physical group names; it becomes a
    ``moving`` boundary driven by an independent ``ideal_velocity_source`` with a single
    ``normal_velocity`` port (the horn's own excitation, never an electrical port). Every other
    horn group is assigned ``rigid``. The exact groups used are recorded in the case manifest.

    After BL validates, the placed horn's gap to the generated enclosure surface must be proven
    ``>= min_clearance_m`` (see :mod:`.clearance`); otherwise the result is not ``ok`` and the
    manifest records ``BODY_CLEARANCE_VIOLATION`` / ``BODY_CLEARANCE_UNPROVEN``.
    """
    _require_verified(root)
    horn_path = Path(horn_mesh)
    if not horn_path.is_file():
        raise FileNotFoundError(f"horn mesh not found: {horn_path}")
    if mesh_role not in {"full_domain", "test_double"}:
        raise ValueError(f"mesh_role must be 'full_domain' or 'test_double', got {mesh_role!r}")
    spec = build_stage_spec(
        root, overrides, case_dir=case_dir or provenance.default_store_root(),
        case_name=case_name, mesh_name=mesh_name,
        horn={
            "mesh_path": str(horn_path.resolve()),
            "name": horn_name,
            "scale_factor": float(scale_factor),
            "translation_mm": [float(value) for value in translation_mm],
            "source_group": source_group,
            "mesh_role": mesh_role,
        },
    )
    return _stage(root, spec, store_root=store_root, case_dir=case_dir,
                  experiment_id=experiment_id, tag="assembly", timeout_s=timeout_s,
                  cancel_path=cancel_path, run_now=run_now,
                  kind="bl_stage_horn_project", min_clearance_m=min_clearance_m)


def resolve_full_domain_horn_mesh(
    store_root: str | os.PathLike[str] | None = None,
) -> Path | None:
    """Lane A's full-domain closed horn mesh under ``system_runs/system/ref_case/horn_full``.

    Returns the newest ``mesh.msh`` found there, or ``None`` (the recorded blocker is then
    :data:`BLOCKED_BY_FULL_DOMAIN_HORN_MESH_INPUT`). This only looks for the file; topology
    acceptance stays BL's compiler's call.
    """
    root = Path(store_root) if store_root is not None else provenance.default_store_root()
    candidates = sorted((root / "system" / "ref_case" / "horn_full").glob("*/mesh.msh"))
    return candidates[-1] if candidates else None
