"""No-GUI reference-case workflow for the horn + vented-woofer Boundary Lab system.

This module is the typed, testable seam behind ``python -m hornlab_search.system.cli reference``.
It does four things and nothing else:

``prepare``
    Delegate PhysicalSystem staging to :mod:`hornlab_search.system.boundarylab.stage` (BL's own
    host path), then record one immutable ``reference_prepare.json`` beside the case. The record
    carries the assembly-geometry identity (``contracts.assembly_geometry_id``) and every blocker
    known at prepare time. The staging manifest is never rewritten.

``validate``
    Run BL's *own* ``blab project validate --json`` (through
    :func:`hornlab_search.system.boundarylab.run.validate_project`) and assert the graph the
    reference workflow depends on: two regions, at least one interface, the declared excitation
    ports, and mesh purposes/scales. Graph facts are read from ``compiled-system.json`` when a
    solved run exists, else from the staged project's ``physical_system`` block; the source is
    recorded.

``solve``
    Refuse unless ``authorized_by`` names the approval, then invoke BL's own console entry with
    exactly the recorded smoke invocation
    (``blab project solve <case> --request <req> --backend <backend> --output <dir> --events
    ndjson``). BL writes ``<out>/manifest.json``; this module only records the invocation and
    raises loudly on a non-zero return code. It never imports or re-implements a solver and never
    touches :func:`hornlab_search.system.boundarylab.run.solve_project` (that adapter stays inert).

``report``
    Read the headless result with :func:`bl_results.read_bl_headless_result`, recompose the two
    independently solved excitation bases with :mod:`hornlab_search.system.dsp` (analog LR
    prototypes) and :mod:`hornlab_search.system.combine`, and emit a markdown report with the
    per-preset complex sums, a vertical-lobing table and the per-input honesty labels. The
    woofer permutation (Pa per 2.83 V) and the horn permutation (Pa per 1 m/s) are never presented
    as comparable sensitivities.

Nothing in this module writes into Boundary Lab, ``runs/`` or the frozen contracts.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from hornlab_search.system import combine as sys_combine
from hornlab_search.system import contracts as C
from hornlab_search.system import dsp as sys_dsp
from hornlab_search.system import provenance
from hornlab_search.system.boundarylab import bl_results as R
from hornlab_search.system.boundarylab import run as bl_run
from hornlab_search.system.boundarylab import stage as S
from hornlab_search.system.boundarylab.probe import (
    BLCapabilityError,
    BLRoot,
    probe_boundarylab,
)

__all__ = [
    "BLOCKED_BY_FULL_DOMAIN_HORN_MESH_INPUT",
    "DSP_XO_HZ",
    "GraphSummary",
    "PreparedCase",
    "PresetColumn",
    "PresetSum",
    "ReferenceError",
    "ReferenceReport",
    "ReferenceRequest",
    "ReferenceSolveResult",
    "ReferenceValidation",
    "REFERENCE_EXPECTED_PORT_IDS",
    "REFERENCE_TOKENS",
    "assert_graph",
    "build_solve_argv",
    "dsp_preset_columns",
    "graph_summary",
    "load_request",
    "prepare",
    "recompose_preset",
    "report",
    "solve",
    "validate",
]

#: Blocker token inherited from the Lane A seam (full-domain closed horn mesh absent).
BLOCKED_BY_FULL_DOMAIN_HORN_MESH_INPUT = S.BLOCKED_BY_FULL_DOMAIN_HORN_MESH_INPUT

#: The two independently driven ports the reference case must expose.
REFERENCE_EXPECTED_PORT_IDS: tuple[str, ...] = ("vented/voltage", "excitation:horn")

#: Crossover frequencies reported for the reference DSP presets (Hz).
DSP_XO_HZ: tuple[float, ...] = (700.0, 900.0, 1100.0)

#: Crossover alignment used by every preset (analog Linkwitz-Riley, dsp.filter_bank).
DSP_CROSSOVER_TYPE = "LR4"

#: Error tokens emitted by this module (``"<TOKEN>: detail"`` message form).
REFERENCE_TOKENS: tuple[str, ...] = (
    "REFERENCE_CASE_NOT_FOUND",
    "REFERENCE_CASE_INCOMPLETE",
    "REFERENCE_CASE_EXISTS",
    "REFERENCE_PROJECT_MISSING",
    "REFERENCE_RECORD_EXISTS",
    "REFERENCE_REQUEST_INVALID",
    "REFERENCE_SOLVE_UNAUTHORIZED",
    "REFERENCE_SOLVE_RUN_EXISTS",
    "REFERENCE_SOLVE_FAILED",
    "REFERENCE_RUN_INCOMPLETE",
    "REFERENCE_SOURCE_GROUP_REQUIRED",
    "REFERENCE_BL_ROOT_MISSING",
    "GRAPH_SOURCE_MISSING",
    "GRAPH_REGION_COUNT",
    "GRAPH_INTERFACE_COUNT",
    "GRAPH_PORT_IDS",
    "GRAPH_MESH_PURPOSE",
    "GRAPH_MESH_SCALE",
    "GRAPH_SOLVE_KIND",
    "REFERENCE_REPORT_DOMAIN",
)

_PREPARE_RECORD = "reference_prepare.json"
_SOLVE_RECORD = "reference_solve.json"
_PREPARE_SPEC_KEYS = frozenset({
    "root", "overrides", "horn_mesh", "source_group", "store_root", "case_dir",
    "experiment_id", "case_name", "mesh_name", "horn_name", "scale_factor",
    "translation_mm", "mesh_role", "timeout_s", "run_now",
})


class ReferenceError(RuntimeError):
    """A reference-case workflow step refused or failed with a declared token."""

    def __init__(self, token: str, detail: str) -> None:
        if token not in REFERENCE_TOKENS:
            raise AssertionError(f"undeclared reference token {token!r}")
        self.token = token
        self.detail = detail
        super().__init__(f"{token}: {detail}")


# --------------------------------------------------------------------------- small helpers

def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, token: str, what: str) -> Any:
    if not path.is_file():
        raise ReferenceError(token, f"{what} not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReferenceError(token, f"unreadable {what} {path}: {exc}") from None


def _write_record(path: Path, payload: Mapping[str, Any]) -> Path:
    """Atomic JSON record with its own canonical-payload digest; never overwrites."""
    if path.exists():
        raise ReferenceError("REFERENCE_RECORD_EXISTS", f"record already present: {path}")
    body = {
        "created_utc": _utc_now(),
        "payload_sha256": hashlib.sha256(C.canonical_json(payload).encode()).hexdigest(),
        "payload": C.canonical_json(payload),
    }
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent),
                                     delete=False, suffix=".tmp") as fh:
        json.dump(body, fh, indent=2, sort_keys=True)
        fh.write("\n")
        tmp = Path(fh.name)
    os.replace(tmp, path)
    return path


def _load_record(path: Path) -> Mapping[str, Any] | None:
    if not path.is_file():
        return None
    body = json.loads(path.read_text(encoding="utf-8"))
    payload = body.get("payload")
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, Mapping):
        return None
    digest = hashlib.sha256(C.canonical_json(payload).encode()).hexdigest()
    if digest != body.get("payload_sha256"):
        raise ReferenceError(
            "REFERENCE_RECORD_EXISTS",
            f"record integrity check failed for {path}: recorded "
            f"{body.get('payload_sha256')!r}, computed {digest!r}",
        )
    return payload


def _coerce_root(value: Any) -> BLRoot:
    if isinstance(value, BLRoot):
        return value
    if isinstance(value, (str, os.PathLike)):
        probe = probe_boundarylab(extra_roots=[str(value)], use_default_roots=False)
        if probe.verified_root is None:
            raise ReferenceError(
                "REFERENCE_BL_ROOT_MISSING",
                f"{value} is not a verified Boundary Lab root: {probe.status}",
            )
        return probe.verified_root
    if isinstance(value, Mapping):
        payload = dict(value)
        hashes = payload.get("hashes") or {}
        root = BLRoot(
            path=str(payload.get("path", "")),
            kind=str(payload.get("kind", "checkout")),
            version=None if payload.get("version") is None else str(payload.get("version")),
            git_head=None if payload.get("git_head") is None else str(payload.get("git_head")),
            python_executable=(None if payload.get("python_executable") is None
                               else str(payload.get("python_executable"))),
            cli_entry=None if payload.get("cli_entry") is None else str(payload.get("cli_entry")),
            provider_dir=(None if payload.get("provider_dir") is None
                          else str(payload.get("provider_dir"))),
            hashes=tuple((str(k), str(v)) for k, v in dict(hashes).items()),
            missing=tuple(str(m) for m in payload.get("missing") or ()),
            detail={},
        )
        if not root.verified:
            raise ReferenceError(
                "REFERENCE_BL_ROOT_MISSING",
                f"recorded Boundary Lab root is unverified: {root.path}",
            )
        return root
    raise ReferenceError("REFERENCE_BL_ROOT_MISSING", f"no usable Boundary Lab root: {value!r}")


def _load_case_manifest(case_dir: Path) -> Mapping[str, Any] | None:
    path = case_dir / "manifest.json"
    if not path.is_file():
        return None
    try:
        return provenance.load_manifest(path)["payload"]
    except (OSError, ValueError):
        return None


def _resolve_project(case_dir: Path) -> Path:
    direct = case_dir / "case.blab.json"
    if direct.is_file():
        return direct
    candidates = sorted(p for p in case_dir.glob("*.blab.json")
                        if p.name != "project.snapshot.blab.json")
    if candidates:
        return candidates[0]
    snapshot = case_dir / "run" / "project.snapshot.blab.json"
    if snapshot.is_file():
        return snapshot
    raise ReferenceError(
        "REFERENCE_PROJECT_MISSING",
        f"no staged .blab.json project under {case_dir} (expected case.blab.json)",
    )


def _resolve_run_dir(case_dir: Path, run_dir: str | os.PathLike[str] | None) -> Path:
    if run_dir is not None:
        candidate = Path(run_dir)
    elif R.is_bl_headless_result_dir(case_dir / "run"):
        candidate = case_dir / "run"
    elif R.is_bl_headless_result_dir(case_dir):
        candidate = case_dir
    else:
        candidate = None
        for child in sorted(case_dir.iterdir()) if case_dir.is_dir() else ():
            if child.is_dir() and R.is_bl_headless_result_dir(child):
                candidate = child
                break
        if candidate is None:
            raise ReferenceError(
                "REFERENCE_CASE_NOT_FOUND",
                f"no Boundary Lab headless result directory under {case_dir}",
            )
    if not R.is_bl_headless_result_dir(candidate):
        raise ReferenceError(
            "REFERENCE_CASE_NOT_FOUND",
            f"{candidate} is not a Boundary Lab headless result directory",
        )
    return candidate


def _stage_spec(staged: S.StagedProject) -> dict[str, Any]:
    dry = staged.detail.get("spec_dry_run")
    if isinstance(dry, Mapping):
        return dict(dry)
    path = staged.case_dir / "adapter_spec.json"
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    return {}


# --------------------------------------------------------------------------- prepare

@dataclass(frozen=True)
class PreparedCase:
    """Verified artifacts of one prepared reference case plus its recorded identity."""

    case_dir: Path
    ok: bool
    valid: bool
    project_path: Path | None
    manifest_path: Path | None
    assembly_geometry_id: str
    blockers: tuple[str, ...]
    horn_mesh: Path | None
    source_group: str | None
    mesh_role: str | None
    stage_kind: str
    record_path: Path | None
    returncode: int
    stage: S.StagedProject | None = field(default=None, repr=False, compare=False)

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "case_dir": str(self.case_dir),
            "ok": self.ok,
            "valid": self.valid,
            "project_path": None if self.project_path is None else str(self.project_path),
            "manifest_path": None if self.manifest_path is None else str(self.manifest_path),
            "assembly_geometry_id": self.assembly_geometry_id,
            "blockers": list(self.blockers),
            "horn_mesh": None if self.horn_mesh is None else str(self.horn_mesh),
            "source_group": self.source_group,
            "mesh_role": self.mesh_role,
            "stage_kind": self.stage_kind,
            "record_path": None if self.record_path is None else str(self.record_path),
            "returncode": self.returncode,
        }


def _assembly_identity(root: BLRoot, spec: Mapping[str, Any],
                       staged: S.StagedProject) -> tuple[str, dict[str, Any]]:
    horn = spec.get("horn") if isinstance(spec.get("horn"), Mapping) else None
    meshes = [
        {
            "id": mesh.get("id"),
            "purpose": mesh.get("purpose"),
            "sha256": mesh.get("sha256"),
        }
        for mesh in staged.meshes
        if isinstance(mesh, Mapping)
    ]
    payload: dict[str, Any] = {
        "bl_git_head": root.git_head,
        "provider_id": spec.get("provider_id"),
        "source": spec.get("source"),
        "horn": None if horn is None else {
            "mesh_path": horn.get("mesh_path"),
            "mesh_role": horn.get("mesh_role"),
            "source_group": horn.get("source_group"),
            "scale_factor": horn.get("scale_factor"),
            "translation_mm": horn.get("translation_mm"),
        },
        "meshes": meshes,
        "mesh_info": staged.mesh_info,
    }
    return C.assembly_geometry_id(payload), payload


def _merge_prepare_spec(spec: Any, paths: Mapping[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split any accepted input into a (spec mapping, explicit path mapping)."""
    spec_map: dict[str, Any] = {}
    path_map: dict[str, Any] = {}
    if spec is not None:
        if isinstance(spec, BLRoot) or isinstance(spec, (str, os.PathLike)):
            spec_map["root"] = spec
        elif isinstance(spec, Mapping):
            unknown = sorted(set(spec) - _PREPARE_SPEC_KEYS)
            if unknown:
                raise ValueError(
                    f"unknown reference prepare keys {unknown}; allowed: "
                    f"{sorted(_PREPARE_SPEC_KEYS)}"
                )
            spec_map.update(spec)
        else:
            raise TypeError(f"prepare spec must be a mapping/BLRoot/path, got {type(spec).__name__}")
    if paths:
        unknown = sorted(set(paths) - {"root", "horn_mesh", "store_root", "case_dir"})
        if unknown:
            raise ValueError(f"unknown reference path keys {unknown}")
        path_map.update({k: v for k, v in paths.items() if v is not None})
    return spec_map, path_map


def prepare(
    spec: Any = None,
    paths: Mapping[str, Any] | None = None,
    *,
    root: BLRoot | str | os.PathLike[str] | None = None,
    overrides: Mapping[str, float] | None = None,
    horn_mesh: str | os.PathLike[str] | None = None,
    source_group: str | None = None,
    store_root: str | os.PathLike[str] | None = None,
    case_dir: str | os.PathLike[str] | None = None,
    experiment_id: str | None = None,
    case_name: str | None = None,
    mesh_name: str | None = None,
    horn_name: str | None = None,
    scale_factor: float | None = None,
    translation_mm: Sequence[float] | None = None,
    assembly_pose: Any = None,
    mesh_role: str | None = None,
    timeout_s: float | None = None,
    run_now: bool | None = None,
) -> PreparedCase:
    """Stage the reference project and record its identity/blockers in the case directory.

    ``spec`` accepts either a :class:`BLRoot`, a path to a Boundary Lab root, or a mapping with
    any of the keywords below; ``paths`` is an optional mapping of the path-valued inputs. An
    explicit keyword argument wins over the same key in ``spec``/``paths``.

    With ``horn_mesh=None`` the newest full-domain horn mesh from
    :func:`stage.resolve_full_domain_horn_mesh` is used; when that is also absent the case is
    staged vented-only and ``BLOCKED_BY_FULL_DOMAIN_HORN_MESH_INPUT`` is recorded. A supplied horn
    mesh requires an explicit ``source_group`` (a guessed group is never assigned).
    """
    spec_map, path_map = _merge_prepare_spec(spec, paths)

    def pick(key: str, explicit: Any, default: Any = None) -> Any:
        if explicit is not None:
            return explicit
        if key in spec_map and spec_map[key] is not None:
            return spec_map[key]
        if key in path_map and path_map[key] is not None:
            return path_map[key]
        return default

    root_value = pick("root", root)
    if root_value is None:
        raise ReferenceError("REFERENCE_BL_ROOT_MISSING", "no Boundary Lab root supplied")
    bl_root = _coerce_root(root_value)
    if not bl_root.verified:
        raise BLCapabilityError((f"BLRoot at {bl_root.path} is not verified: "
                                 + " | ".join(bl_root.missing),))

    resolved_overrides = dict(pick("overrides", overrides, {}) or {})
    resolved_store = pick("store_root", store_root)
    resolved_case = pick("case_dir", case_dir)
    if resolved_case is not None:
        candidate = Path(resolved_case)
        if candidate.exists() and any(candidate.iterdir()):
            raise ReferenceError(
                "REFERENCE_CASE_EXISTS",
                f"case directory {candidate} already contains artifacts; a rerun must use a "
                "new case directory",
            )

    horn_value = pick("horn_mesh", horn_mesh)
    if horn_value is None:
        resolved_horn = S.resolve_full_domain_horn_mesh(resolved_store)
    else:
        resolved_horn = Path(horn_value)
    group = pick("source_group", source_group)
    role = pick("mesh_role", mesh_role, "full_domain")
    pose_value = assembly_pose
    if pose_value is None and "assembly_pose" in spec_map:
        pose_value = spec_map["assembly_pose"]
    pose_payload: dict[str, Any] | None = None
    if pose_value is not None:
        if hasattr(pose_value, "to_dict"):
            pose_payload = dict(pose_value.to_dict())
        elif isinstance(pose_value, Mapping):
            pose_payload = dict(pose_value)
        else:
            raise ReferenceError("REFERENCE_POSE_INVALID",
                                 f"assembly_pose must be an AssemblyPose or mapping, "
                                 f"got {type(pose_value).__name__}")
        if translation_mm is None:
            pose_translation = pose_payload.get("translation_mm")
            if not isinstance(pose_translation, (list, tuple)) or len(pose_translation) != 3:
                raise ReferenceError("REFERENCE_POSE_INVALID",
                                     "assembly_pose has no three-component translation_mm")
            translation_mm = tuple(float(v) for v in pose_translation)
    resolved_translation = tuple(
        float(value) for value in pick("translation_mm", translation_mm, (0.0, 0.0, 0.0)))
    if resolved_horn is not None and not group:
        raise ReferenceError(
            "REFERENCE_SOURCE_GROUP_REQUIRED",
            "a horn mesh needs an explicit source_group (a 2D physical group to drive)",
        )

    resolved_run_now = bool(pick("run_now", run_now, True))
    common = dict(
        store_root=resolved_store,
        case_dir=None if resolved_case is None else Path(resolved_case),
        experiment_id=str(pick("experiment_id", experiment_id, "bl_ref_case")),
        case_name=str(pick("case_name", case_name, "horn_assembly")),
        mesh_name=str(pick("mesh_name", mesh_name, "vented")),
        timeout_s=float(pick("timeout_s", timeout_s, 1800.0)),
        run_now=resolved_run_now,
    )
    if resolved_horn is not None:
        stage_kind = "bl_stage_horn_project"
        staged = S.stage_horn_project(
            bl_root,
            resolved_horn,
            source_group=str(group),
            overrides=resolved_overrides,
            horn_name=str(pick("horn_name", horn_name, "horn")),
            scale_factor=float(pick("scale_factor", scale_factor, 1.0)),
            translation_mm=(resolved_translation[0], resolved_translation[1],
                            resolved_translation[2]),
            mesh_role=str(role),
            pose=pose_payload,
            min_clearance_m=(
                float(pose_payload["clearance_mm"]) / 1e3
                if pose_payload and pose_payload.get("clearance_mm") else 1e-3),
            **common,
        )
    else:
        stage_kind = "bl_stage_reference_project"
        staged = S.stage_reference_project(bl_root, resolved_overrides, **common)

    stage_spec = _stage_spec(staged)
    geometry_id, geometry_payload = _assembly_identity(bl_root, stage_spec, staged)
    blockers: list[str] = []
    if resolved_horn is None:
        blockers.append(BLOCKED_BY_FULL_DOMAIN_HORN_MESH_INPUT)
    if str(role) == "test_double":
        blockers.append("HORN_MESH_IS_TEST_DOUBLE")
    if resolved_run_now and not staged.ok:
        blockers.append("REFERENCE_CASE_INCOMPLETE")
    elif resolved_run_now and not staged.valid:
        blockers.append("BL_VALIDATE_REJECTED")

    record_path: Path | None = None
    if resolved_run_now:
        record_path = _write_record(staged.case_dir / _PREPARE_RECORD, {
            "kind": "bl_reference_case",
            "schema_version": 1,
            "stage_kind": stage_kind,
            "case_dir": str(staged.case_dir),
            "project_path": None if staged.project_path is None else str(staged.project_path),
            "project_sha256": (None if staged.project_path is None
                               else _sha256_file(staged.project_path)),
            "stage_manifest": (None if staged.manifest_path is None
                               else str(staged.manifest_path)),
            "stage_manifest_sha256": (None if staged.manifest_path is None
                                      else _sha256_file(staged.manifest_path)),
            "assembly_geometry_id": geometry_id,
            "assembly_geometry_payload": geometry_payload,
            "horn_mesh": None if resolved_horn is None else str(resolved_horn),
            "source_group": None if resolved_horn is None else str(group),
            "mesh_role": None if resolved_horn is None else str(role),
            "assembly_pose": pose_payload,
            "valid": staged.valid,
            "returncode": staged.returncode,
            "blockers": blockers,
            "validate": {
                "returncode": None if staged.validation is None
                else staged.validation.returncode,
                "valid": None if staged.validation is None
                else (staged.validation.parsed or {}).get("valid"),
                "argv": None if staged.validation is None
                else list(staged.validation.argv),
            },
        })

    return PreparedCase(
        case_dir=staged.case_dir,
        ok=staged.ok,
        valid=staged.valid,
        project_path=staged.project_path,
        manifest_path=staged.manifest_path,
        assembly_geometry_id=geometry_id,
        blockers=tuple(blockers),
        horn_mesh=resolved_horn,
        source_group=None if resolved_horn is None else str(group),
        mesh_role=None if resolved_horn is None else str(role),
        stage_kind=stage_kind,
        record_path=record_path,
        returncode=staged.returncode,
        stage=staged,
    )


# --------------------------------------------------------------------------- graph assertions

@dataclass(frozen=True)
class GraphSummary:
    """Graph facts extracted from ``compiled-system.json`` or a staged project."""

    source: str
    region_ids: tuple[str, ...]
    region_kinds: tuple[str, ...]
    interface_ids: tuple[str, ...]
    excitation_port_ids: tuple[str, ...]
    excitation_port_kinds: tuple[str, ...]
    mesh_purposes: tuple[str, ...]
    mesh_scales: tuple[float | None, ...]
    component_kinds: tuple[str, ...]
    solve_kind: str | None

    @property
    def region_count(self) -> int:
        return len(self.region_ids)

    @property
    def interface_count(self) -> int:
        return len(self.interface_ids)

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "source": self.source,
            "region_count": self.region_count,
            "region_ids": list(self.region_ids),
            "region_kinds": list(self.region_kinds),
            "interface_count": self.interface_count,
            "interface_ids": list(self.interface_ids),
            "excitation_port_ids": list(self.excitation_port_ids),
            "excitation_port_kinds": list(self.excitation_port_kinds),
            "mesh_purposes": list(self.mesh_purposes),
            "mesh_scales": list(self.mesh_scales),
            "component_kinds": list(self.component_kinds),
            "solve_kind": self.solve_kind,
        }


def _entries(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, Mapping)]


def graph_summary(system: Mapping[str, Any], *, source: str = "compiled-system.json") -> GraphSummary:
    """Extract the reference graph facts from a compiled system or a staged project.

    A staged ``.blab.json`` project nests the same block under ``physical_system``; both shapes
    are accepted so a prepared-but-unsolved case can still be inspected.
    """
    header = system.get("physical_system")
    block: Mapping[str, Any] = header if isinstance(header, Mapping) else system
    regions = _entries(block.get("regions"))
    interfaces = _entries(block.get("interfaces"))
    ports = _entries(block.get("excitation_ports"))
    meshes = _entries(block.get("meshes"))
    components = _entries(block.get("components"))
    scales: list[float | None] = []
    for mesh in meshes:
        value = mesh.get("scale_to_m", mesh.get("scale_factor"))
        scales.append(None if value is None else float(value))
    return GraphSummary(
        source=source,
        region_ids=tuple(str(region.get("id", "")) for region in regions),
        region_kinds=tuple(str(region.get("kind", "unknown")) for region in regions),
        interface_ids=tuple(str(interface.get("id", "")) for interface in interfaces),
        excitation_port_ids=tuple(str(port.get("id", "")) for port in ports),
        excitation_port_kinds=tuple(str(port.get("kind", "")) for port in ports),
        mesh_purposes=tuple(str(mesh.get("purpose", "")) for mesh in meshes),
        mesh_scales=tuple(scales),
        component_kinds=tuple(str(component.get("kind", "")) for component in components),
        solve_kind=None if block.get("solve_kind") is None else str(block.get("solve_kind")),
    )


def assert_graph(
    summary: GraphSummary,
    *,
    min_regions: int = 2,
    min_interfaces: int = 1,
    expected_port_ids: Iterable[str] | None = REFERENCE_EXPECTED_PORT_IDS,
    required_mesh_purposes: Iterable[str] = ("bem_surface",),
    forbidden_mesh_purposes: Iterable[str] = (),
    require_volume_mesh: bool | None = None,
    expected_solve_kind: str | None = "coupled_bem_fem",
    scale_tolerance: float = 1e-9,
) -> Mapping[str, Any]:
    """Assert the reference-case graph; raise :class:`ReferenceError` with a token on a gap.

    Defaults encode the horn + vented reference case: two regions, at least one FEM/BEM
    interface, the two declared ports, a ``bem_surface`` mesh and unit mesh scales. Set
    ``expected_solve_kind=None`` to skip the solve-kind check (a staged project does not carry
    it); the small synthetic fixture can relax counts explicitly.
    """
    if summary.region_count < int(min_regions):
        raise ReferenceError(
            "GRAPH_REGION_COUNT",
            f"{summary.source} declares {summary.region_count} regions "
            f"({list(summary.region_ids)}); the reference case needs at least {min_regions}",
        )
    if summary.interface_count < int(min_interfaces):
        raise ReferenceError(
            "GRAPH_INTERFACE_COUNT",
            f"{summary.source} declares {summary.interface_count} interfaces "
            f"({list(summary.interface_ids)}); at least {min_interfaces} required",
        )
    if expected_port_ids is not None:
        expected = tuple(str(port) for port in expected_port_ids)
        if summary.excitation_port_ids != expected:
            raise ReferenceError(
                "GRAPH_PORT_IDS",
                f"{summary.source} excitation ports {list(summary.excitation_port_ids)} "
                f"!= required {list(expected)}",
            )
    purposes = set(summary.mesh_purposes)
    forbidden = set(forbidden_mesh_purposes)
    if purposes & forbidden:
        raise ReferenceError(
            "GRAPH_MESH_PURPOSE",
            f"{summary.source} declares forbidden mesh purposes "
            f"{sorted(purposes & forbidden)} (allowed purposes: {sorted(purposes - forbidden)})",
        )
    missing = [purpose for purpose in required_mesh_purposes if purpose not in purposes]
    if missing:
        raise ReferenceError(
            "GRAPH_MESH_PURPOSE",
            f"{summary.source} is missing required mesh purposes {missing}; declared "
            f"{sorted(purposes)}",
        )
    if require_volume_mesh is None:
        require_volume_mesh = int(min_regions) >= 2
    if require_volume_mesh and "fem_volume" not in purposes:
        raise ReferenceError(
            "GRAPH_MESH_PURPOSE",
            f"{summary.source} has no fem_volume mesh; declared {sorted(purposes)}",
        )
    for mesh_id, scale in zip(summary.mesh_purposes, summary.mesh_scales):
        if scale is None or abs(float(scale) - 1.0) > scale_tolerance:
            raise ReferenceError(
                "GRAPH_MESH_SCALE",
                f"{summary.source} mesh {mesh_id!r} scale_to_m={scale!r}; every mesh must be "
                "declared in metres (scale 1.0)",
            )
    if (expected_solve_kind is not None and summary.solve_kind is not None
            and summary.solve_kind != expected_solve_kind):
        raise ReferenceError(
            "GRAPH_SOLVE_KIND",
            f"{summary.source} solve_kind {summary.solve_kind!r} != {expected_solve_kind!r}",
        )
    return summary.as_dict()


# --------------------------------------------------------------------------- request overlay

@dataclass(frozen=True)
class ReferenceRequest:
    """The pinned public request overlay (BL ``HEADLESS_REQUEST_VERSION == 1``)."""

    path: Path
    sha256: str
    schema_version: int
    frequencies_hz: tuple[float, ...]
    excitation_port_ids: tuple[str, ...]
    probes: tuple[Mapping[str, Any], ...]
    include_project_observations: bool
    raw: Mapping[str, Any]

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "path": str(self.path),
            "sha256": self.sha256,
            "schema_version": self.schema_version,
            "frequencies_hz": list(self.frequencies_hz),
            "excitation_port_ids": list(self.excitation_port_ids),
            "probes": [dict(probe) for probe in self.probes],
            "include_project_observations": self.include_project_observations,
        }


def load_request(request_file: str | os.PathLike[str]) -> ReferenceRequest:
    """Load and locally validate a BL headless request overlay.

    This is a shape check only (schema_version 1, finite positive frequencies, port-id list,
    probe points in metres). BL remains the authority on whether the request is solvable.
    """
    path = Path(request_file)
    payload = _read_json(path, "REFERENCE_REQUEST_INVALID", "request overlay")
    if not isinstance(payload, Mapping):
        raise ReferenceError("REFERENCE_REQUEST_INVALID", f"{path} is not a JSON object")
    version = payload.get("schema_version")
    if version != 1:
        raise ReferenceError(
            "REFERENCE_REQUEST_INVALID",
            f"{path} schema_version {version!r} != 1 (BL HEADLESS_REQUEST_VERSION)",
        )
    freqs = payload.get("frequencies_hz")
    if not isinstance(freqs, list) or not freqs:
        raise ReferenceError("REFERENCE_REQUEST_INVALID",
                             f"{path} frequencies_hz must be a non-empty list")
    values: list[float] = []
    for value in freqs:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ReferenceError("REFERENCE_REQUEST_INVALID",
                                 f"{path} frequency {value!r} is not numeric")
        number = float(value)
        if not np.isfinite(number) or number <= 0.0:
            raise ReferenceError("REFERENCE_REQUEST_INVALID",
                                 f"{path} frequency {number!r} must be finite and > 0")
        values.append(number)
    ports = payload.get("excitation_port_ids")
    if not isinstance(ports, list) or not ports or not all(isinstance(p, str) and p for p in ports):
        raise ReferenceError("REFERENCE_REQUEST_INVALID",
                             f"{path} excitation_port_ids must be a non-empty string list")
    probes = payload.get("probes") or []
    if not isinstance(probes, list) or not all(isinstance(p, Mapping) for p in probes):
        raise ReferenceError("REFERENCE_REQUEST_INVALID", f"{path} probes must be a list of objects")
    for probe in probes:
        points = probe.get("points_m")
        if points is None:
            continue
        try:
            array = np.asarray(points, dtype=np.float64)
        except (TypeError, ValueError):
            raise ReferenceError("REFERENCE_REQUEST_INVALID",
                                 f"{path} probe {probe.get('id')!r} points_m is not numeric") from None
        if array.ndim != 2 or array.shape[1] != 3 or array.shape[0] == 0:
            raise ReferenceError(
                "REFERENCE_REQUEST_INVALID",
                f"{path} probe {probe.get('id')!r} points_m must be (n, 3) metres, "
                f"got {array.shape}",
            )
        if not np.all(np.isfinite(array)):
            raise ReferenceError("REFERENCE_REQUEST_INVALID",
                                 f"{path} probe {probe.get('id')!r} contains non-finite points")
    return ReferenceRequest(
        path=path,
        sha256=_sha256_file(path),
        schema_version=1,
        frequencies_hz=tuple(values),
        excitation_port_ids=tuple(ports),
        probes=tuple(probes),
        include_project_observations=bool(payload.get("include_project_observations", False)),
        raw=dict(payload),
    )


# --------------------------------------------------------------------------- validate

@dataclass(frozen=True)
class ReferenceValidation:
    """BL's own validate verdict plus this module's graph assertions."""

    case_dir: Path
    project_path: Path
    returncode: int
    valid: bool
    parsed: Mapping[str, Any] | None
    validate_argv: tuple[str, ...]
    graph: GraphSummary
    graph_assertions: Mapping[str, Any] | None
    request: ReferenceRequest | None
    blockers: tuple[str, ...]
    stdout_tail: tuple[str, ...]
    stderr_tail: tuple[str, ...]

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "case_dir": str(self.case_dir),
            "project_path": str(self.project_path),
            "returncode": self.returncode,
            "valid": self.valid,
            "parsed": None if self.parsed is None else dict(self.parsed),
            "validate_argv": list(self.validate_argv),
            "graph": self.graph.as_dict(),
            "graph_assertions": (None if self.graph_assertions is None
                                 else dict(self.graph_assertions)),
            "request": None if self.request is None else self.request.as_dict(),
            "blockers": list(self.blockers),
            "stdout_tail": list(self.stdout_tail),
            "stderr_tail": list(self.stderr_tail),
        }


def _root_for_case(case_dir: Path) -> BLRoot:
    payload = _load_case_manifest(case_dir) or {}
    recorded = payload.get("bl_root")
    if recorded is not None:
        try:
            return _coerce_root(recorded)
        except ReferenceError:
            pass
    probe = probe_boundarylab()
    if probe.verified_root is None:
        raise ReferenceError(
            "REFERENCE_BL_ROOT_MISSING",
            f"case {case_dir} records no Boundary Lab root and none is verifiable: {probe.status}",
        )
    return probe.verified_root


def _graph_for_case(case_dir: Path, project_payload: Mapping[str, Any]) -> GraphSummary:
    compiled = case_dir / "run" / "compiled-system.json"
    if not compiled.is_file():
        compiled = case_dir / "compiled-system.json"
    if compiled.is_file():
        payload = _read_json(compiled, "GRAPH_SOURCE_MISSING", "compiled-system.json")
        if isinstance(payload, Mapping):
            return graph_summary(payload, source=str(compiled))
    if isinstance(project_payload.get("physical_system"), Mapping):
        return graph_summary(project_payload, source="project.physical_system")
    raise ReferenceError(
        "GRAPH_SOURCE_MISSING",
        f"{case_dir} has neither run/compiled-system.json nor a physical_system block",
    )


def validate(
    case_dir: str | os.PathLike[str],
    request_file: str | os.PathLike[str] | None = None,
    *,
    timeout_s: float = 300.0,
    expected_port_ids: Iterable[str] | None = REFERENCE_EXPECTED_PORT_IDS,
    min_regions: int = 2,
    min_interfaces: int = 1,
    expected_solve_kind: str | None = "coupled_bem_fem",
) -> ReferenceValidation:
    """Run BL's real validate verdict and assert the reference graph.

    The project is read from ``case.blab.json``; the BL root comes from the staging manifest.
    A request overlay, when given, is shape-checked and its port ids replace the default port
    expectation. Graph facts prefer ``compiled-system.json`` and fall back to the staged
    project's ``physical_system`` block.
    """
    root = Path(case_dir)
    if not root.is_dir():
        raise ReferenceError("REFERENCE_CASE_NOT_FOUND", f"case directory not found: {root}")
    project = _resolve_project(root)
    project_payload = _read_json(project, "REFERENCE_PROJECT_MISSING", "staged project")
    if not isinstance(project_payload, Mapping):
        raise ReferenceError("REFERENCE_PROJECT_MISSING", f"{project} is not a JSON object")
    request = None if request_file is None else load_request(request_file)
    ports = (request.excitation_port_ids if request is not None
             else None if expected_port_ids is None else tuple(expected_port_ids))

    bl_root = _root_for_case(root)
    verdict = bl_run.validate_project(bl_root, project, timeout_s=timeout_s)
    parsed = verdict.parsed
    valid = bool(verdict.returncode == 0 and isinstance(parsed, Mapping)
                 and parsed.get("valid") is True)

    graph = _graph_for_case(root, project_payload)
    blockers: list[str] = []
    assertions: Mapping[str, Any] | None = None
    try:
        assertions = assert_graph(
            graph,
            min_regions=min_regions,
            min_interfaces=min_interfaces,
            expected_port_ids=ports,
            expected_solve_kind=expected_solve_kind,
        )
    except ReferenceError as exc:
        blockers.append(exc.token)
    if not valid:
        blockers.append("BL_VALIDATE_REJECTED")

    return ReferenceValidation(
        case_dir=root,
        project_path=project,
        returncode=verdict.returncode,
        valid=valid,
        parsed=None if parsed is None else dict(parsed),
        validate_argv=tuple(verdict.argv),
        graph=graph,
        graph_assertions=assertions,
        request=request,
        blockers=tuple(blockers),
        stdout_tail=tuple(verdict.stdout_tail[-12:]),
        stderr_tail=tuple(verdict.stderr_tail[-12:]),
    )


# --------------------------------------------------------------------------- solve

def build_solve_argv(cli_entry: str | os.PathLike[str],
                     project: str | os.PathLike[str],
                     request: str | os.PathLike[str],
                     backend: str,
                     out: str | os.PathLike[str]) -> list[str]:
    """Exact ``blab project solve`` argv recorded by the working smoke run (no shell)."""
    return [
        str(cli_entry), "project", "solve", str(project),
        "--request", str(request),
        "--backend", str(backend),
        "--output", str(out),
        "--events", "ndjson",
    ]


@dataclass(frozen=True)
class ReferenceSolveResult:
    """One BL headless solve invocation and the artifact it wrote."""

    case_dir: Path
    run_dir: Path
    request_path: Path
    backend: str
    authorized_by: str
    returncode: int
    argv: tuple[str, ...]
    status: str | None
    manifest_path: Path | None
    record_path: Path
    stdout_tail: tuple[str, ...]
    stderr_tail: tuple[str, ...]

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "case_dir": str(self.case_dir),
            "run_dir": str(self.run_dir),
            "request_path": str(self.request_path),
            "backend": self.backend,
            "authorized_by": self.authorized_by,
            "returncode": self.returncode,
            "argv": list(self.argv),
            "status": self.status,
            "manifest_path": None if self.manifest_path is None else str(self.manifest_path),
            "record_path": str(self.record_path),
            "stdout_tail": list(self.stdout_tail),
            "stderr_tail": list(self.stderr_tail),
        }


def _bounded(text: str, limit: int = 60) -> tuple[str, ...]:
    return tuple((text or "").splitlines()[-limit:])


def solve(
    case_dir: str | os.PathLike[str],
    request: str | os.PathLike[str],
    *,
    backend: str = "beat_cpu",
    authorized_by: str | None,
    out: str | os.PathLike[str] | None = None,
    timeout_s: float | None = None,
) -> ReferenceSolveResult:
    """Invoke BL's own ``project solve``; refuse without an explicit authorization record.

    The call matches the parent's recorded smoke invocation exactly. A non-zero return code or
    a non-complete run manifest raises :class:`ReferenceError` after the invocation record is
    written, so a failed solve is never silently treated as reusable evidence.
    """
    if not isinstance(authorized_by, str) or not authorized_by.strip():
        raise ReferenceError(
            "REFERENCE_SOLVE_UNAUTHORIZED",
            "BL solve refused: pass authorized_by=<senior approval record>; no solve is started "
            "without it",
        )
    root = Path(case_dir).resolve()
    if not root.is_dir():
        raise ReferenceError("REFERENCE_CASE_NOT_FOUND", f"case directory not found: {root}")
    project = _resolve_project(root).resolve()
    request_path = Path(request).resolve()
    loaded = load_request(request_path)

    bl_root = _root_for_case(root)
    cli_entry = bl_root.cli_entry
    if not cli_entry:
        raise ReferenceError("REFERENCE_BL_ROOT_MISSING",
                             f"verified Boundary Lab root {bl_root.path} has no blab console entry")
    # argv paths must be absolute: the subprocess below runs with cwd=<case dir> and BL
    # resolves relative project/request/output paths against it (real G6 failure recorded).
    run_dir = (Path(out) if out is not None else (root / "run")).resolve()
    if (run_dir / "manifest.json").is_file():
        raise ReferenceError(
            "REFERENCE_SOLVE_RUN_EXISTS",
            f"{run_dir} already holds a BL run manifest; a rerun needs a new case directory",
        )
    # BL's HeadlessResultWriter refuses an existing output directory (crash-tolerance);
    # creation belongs to BL, not to this wrapper. Only the parent case dir must exist.
    if not run_dir.parent.is_dir():
        raise ReferenceError(
            "REFERENCE_CASE_NOT_FOUND", f"parent of output dir missing: {run_dir.parent}")
    argv = build_solve_argv(cli_entry, project, request_path, backend, run_dir)

    stdout = ""
    stderr = ""
    returncode = -1
    try:
        proc = subprocess.run(
            argv,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        returncode, stdout, stderr = proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        returncode = 124
        stderr = f"[reference] solve timed out after {timeout_s}s"

    manifest_path = run_dir / "manifest.json"
    status: str | None = None
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(manifest, Mapping):
                status = None if manifest.get("status") is None else str(manifest.get("status"))
        except (OSError, ValueError):
            status = None

    # One record per run, not per case: a case may legitimately carry several requests
    # (smoke + placement sweep) and each run needs its own authorization record.
    record_path = _write_record(
        root / (_SOLVE_RECORD if run_dir == root / "run"
                else f"reference_solve_{run_dir.name}.json"), {
        "kind": "bl_reference_solve",
        "schema_version": 1,
        "case_dir": str(root),
        "project_path": str(project),
        "project_sha256": _sha256_file(project),
        "request_path": str(request_path),
        "request_sha256": loaded.sha256,
        "request": loaded.as_dict(),
        "backend": backend,
        "authorized_by": authorized_by,
        "argv": argv,
        "returncode": returncode,
        "run_dir": str(run_dir),
        "run_manifest": str(manifest_path) if manifest_path.is_file() else None,
        "run_status": status,
        "stdout_tail": list(_bounded(stdout)),
        "stderr_tail": list(_bounded(stderr)),
        "created_utc": _utc_now(),
    })

    if returncode != 0:
        raise ReferenceError(
            "REFERENCE_SOLVE_FAILED",
            f"blab project solve exited rc={returncode}; see {record_path} and "
            f"{run_dir} (tail: {(stderr or stdout)[-800:]!r})",
        )
    if status != "complete" or not R.is_bl_headless_result_dir(run_dir):
        raise ReferenceError(
            "REFERENCE_RUN_INCOMPLETE",
            f"blab project solve returned rc=0 but {manifest_path} status={status!r} is not a "
            "complete Boundary Lab headless result",
        )
    return ReferenceSolveResult(
        case_dir=root,
        run_dir=run_dir,
        request_path=request_path,
        backend=backend,
        authorized_by=authorized_by,
        returncode=returncode,
        argv=tuple(argv),
        status=status,
        manifest_path=manifest_path,
        record_path=record_path,
        stdout_tail=_bounded(stdout),
        stderr_tail=_bounded(stderr),
    )


# --------------------------------------------------------------------------- report: presets

@dataclass(frozen=True)
class PresetColumn:
    """One DSP report column: a name plus the :class:`contracts.DspPoint` it resolves to."""

    name: str
    point: C.DspPoint
    description: str


def dsp_preset_columns(xo_hz: Sequence[float] = DSP_XO_HZ) -> tuple[PresetColumn, ...]:
    """LR4 presets at each crossover, each with base / polarity-flip / ±1 ms delay columns.

    Gain is 0 dB on both channels and the base delay is 0 ms. ``delay_m1ms`` is a negative
    relative horn delay (horn earlier); ``delay_p1ms`` is positive (horn later). The DSP
    convention itself lives in :mod:`hornlab_search.system.dsp` and is not reimplemented here.
    """
    columns: list[PresetColumn] = []
    for value in xo_hz:
        fc = float(value)
        base = C.DspPoint(
            crossover_type=DSP_CROSSOVER_TYPE, xo_hz=fc,
            gain_db_woofer=0.0, gain_db_horn=0.0,
            relative_delay_ms=0.0, polarity_woofer=1.0,
            peq_bands_woofer=(),
        )
        label = f"lr4_{int(round(fc))}"
        columns.append(PresetColumn(
            f"{label}_base", base,
            f"LR4 @ {fc:g} Hz, 0 dB, 0 ms, woofer polarity +1",
        ))
        columns.append(PresetColumn(
            f"{label}_polarity_flip", replace(base, polarity_woofer=-1.0),
            f"LR4 @ {fc:g} Hz, 0 dB, 0 ms, woofer polarity -1",
        ))
        columns.append(PresetColumn(
            f"{label}_delay_m1ms", replace(base, relative_delay_ms=-1.0),
            f"LR4 @ {fc:g} Hz, 0 dB, horn -1 ms, woofer polarity +1",
        ))
        columns.append(PresetColumn(
            f"{label}_delay_p1ms", replace(base, relative_delay_ms=1.0),
            f"LR4 @ {fc:g} Hz, 0 dB, horn +1 ms, woofer polarity +1",
        ))
    return tuple(columns)


@dataclass(frozen=True)
class PresetSum:
    """Coherent (nominal per-input) total for one domain and one DSP preset."""

    preset: str
    domain_id: str
    point: C.DspPoint
    total_pa: np.ndarray
    per_input_by_excitation: Mapping[str, str]
    shared_sensitivity_reference: bool
    refusal_reason: str | None

    def max_abs_pa(self) -> float:
        return float(np.max(np.abs(self.total_pa))) if self.total_pa.size else 0.0


def _fidelity_for(result: R.BLHeadlessResult) -> str:
    kind = result.provenance.solve_kind
    if kind == "coupled_bem_fem":
        return "COUPLED_VENTED_FEM_BEM_LEM"
    if kind == "exterior_bem":
        return "INSTALLED_EXTERIOR_BEM"
    return "SCREEN_COMPLEX_APPROX"


def _channel_for(excitation_name: str) -> str:
    """Map a BL excitation id to the DSP channel it drives (``horn`` / ``woofer``)."""
    lowered = excitation_name.lower()
    if "horn" in lowered:
        return "horn"
    if "woofer" in lowered or "voltage" in lowered or "driver" in lowered:
        return "woofer"
    raise ReferenceError(
        "REFERENCE_REPORT_DOMAIN",
        f"excitation {excitation_name!r} cannot be mapped to a horn/woofer DSP channel; "
        "expected the reference case's two channels",
    )


def _channel_bank(names: Sequence[str],
                  bank: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Re-key ``dsp.filter_bank`` output (horn/woofer) to BL excitation ids."""
    resolved: dict[str, np.ndarray] = {}
    for name in names:
        channel = _channel_for(name)
        if channel not in bank:
            raise ReferenceError("REFERENCE_REPORT_DOMAIN",
                                 f"dsp filter bank has no {channel!r} channel")
        resolved[name] = np.asarray(bank[channel], dtype=np.complex128)
    return resolved


def _nominal_sum(response: C.SystemResponse,
                 bank: Mapping[str, np.ndarray],
                 levels: Mapping[str, float]) -> np.ndarray:
    """The documented combine algebra without any spatial phase factor (phase-once rule)."""
    assert response.p_by_excitation is not None
    total: np.ndarray | None = None
    for name in response.excitation_names:
        h = np.asarray(response.p_by_excitation[name], dtype=np.complex128)
        term = h * np.asarray(bank[name], dtype=np.complex128)[:, None] * float(levels[name])
        total = term if total is None else total + term
    if total is None:
        raise ReferenceError("REFERENCE_REPORT_DOMAIN", "no excitations to sum")
    return np.asarray(total, dtype=np.complex128)


def recompose_preset(result: R.BLHeadlessResult,
                     domain_id: str,
                     column: PresetColumn,
                     *,
                     input_levels: Mapping[str, float] | None = None) -> PresetSum:
    """Recompose one domain's per-excitation bases with one DSP preset.

    :func:`combine.combine` is used when the stored bases prove one shared per-input and
    observation frame. A reference case normally stores the woofer as ``V_rms`` and the horn as
    ``normal_velocity_mps``; those bases are not comparable sensitivity references, so the
    contract refuses the sum. In that case the same linear algebra is evaluated with every
    channel at its own **nominal** input (1 unit of its declared reference) and the refusal
    reason is recorded -- never hidden.
    """
    response = R.to_system_response(result, domain_id, fidelity=_fidelity_for(result))
    names = tuple(response.excitation_names)
    levels = {name: 1.0 for name in names}
    if input_levels is not None:
        levels.update({name: float(value) for name, value in input_levels.items()})
    bank = _channel_bank(names, sys_dsp.filter_bank(column.point, result.frequencies_hz))
    per_input = {name: response.excitation_bases[name].per_input for name in names}

    shared = True
    reason: str | None = None
    total: np.ndarray | None = None
    try:
        result.assert_shared_sensitivity_reference(domain_id)
        total = sys_combine.combine(response, bank, levels).p_total
    except (C.IncompatibleBasis, C.DataQualityError, C.PhaseUnavailable) as exc:
        shared = False
        reason = str(exc)
        total = _nominal_sum(response, bank, levels)
    if total is None:  # pragma: no cover - combine always sets p_total on success
        total = _nominal_sum(response, bank, levels)
    return PresetSum(
        preset=column.name,
        domain_id=domain_id,
        point=column.point,
        total_pa=np.asarray(total, dtype=np.complex128),
        per_input_by_excitation=per_input,
        shared_sensitivity_reference=shared,
        refusal_reason=reason,
    )


# --------------------------------------------------------------------------- report

@dataclass(frozen=True)
class ReferenceReport:
    """The markdown report plus the recomposition tables it was rendered from."""

    case_dir: Path
    run_dir: Path
    markdown: str
    frequencies_hz: tuple[float, ...]
    domain_ids: tuple[str, ...]
    presets: tuple[PresetColumn, ...]
    sums: Mapping[str, Mapping[str, PresetSum]]
    per_input_by_excitation: Mapping[str, str]
    vertical_lobing: Mapping[str, Any]

    def as_dict(self) -> Mapping[str, Any]:
        def _encode(array: np.ndarray) -> list:
            return [
                [{"re": float(np.real(v)), "im": float(np.imag(v))} for v in row]
                for row in np.asarray(array)
            ]

        return {
            "case_dir": str(self.case_dir),
            "run_dir": str(self.run_dir),
            "frequencies_hz": list(self.frequencies_hz),
            "domain_ids": list(self.domain_ids),
            "presets": [{"name": p.name, "description": p.description} for p in self.presets],
            "per_input_by_excitation": dict(self.per_input_by_excitation),
            "sums": {
                preset: {domain: _encode(sums.total_pa) for domain, sums in by_domain.items()}
                for preset, by_domain in self.sums.items()
            },
            "vertical_lobing": self.vertical_lobing,
            "markdown": self.markdown,
        }


def _fmt_complex(value: complex) -> str:
    magnitude = abs(value)
    degrees = float(np.degrees(np.angle(value))) if magnitude > 0.0 else 0.0
    return f"{magnitude:.6g} Pa @ {degrees:.1f} deg"


def _fmt_db(value: float) -> str:
    if not np.isfinite(value):
        return "n/a"
    return f"{value:+.2f} dB"


def _domain_label(result: R.BLHeadlessResult, domain_id: str) -> str:
    observation = result.observation_sets.get(domain_id)
    if observation is None:
        return domain_id
    return f"{domain_id} ({observation.kind}, {observation.count} pts)"


def _elevation_deg(points: np.ndarray) -> float | None:
    array = np.asarray(points, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != 3 or array.shape[0] != 1:
        return None
    x, y, z = array[0]
    horizontal = float(np.hypot(x, y))
    if horizontal == 0.0 and z == 0.0:
        return None
    return float(np.degrees(np.arctan2(z, horizontal)))


def _vertical_series(result: R.BLHeadlessResult
                     ) -> tuple[list[tuple[str, str, int, float | None]], str | None]:
    """Vertical sample labels for the lobing table: (label, domain, column, elevation)."""
    for domain_id in result.domain_ids():
        observation = result.observation_sets.get(domain_id)
        if observation is None or observation.angles_deg is None:
            continue
        if str(observation.metadata.get("plane", "")).lower() == "vertical":
            groups = []
            for index, angle in enumerate(np.asarray(observation.angles_deg).reshape(-1)):
                groups.append((f"{float(angle):g} deg", domain_id, index, float(angle)))
            return groups, domain_id
    groups = []
    for domain_id in result.domain_ids():
        observation = result.observation_sets.get(domain_id)
        if observation is None or observation.kind != "point_probe":
            continue
        elevation = _elevation_deg(observation.points_m)
        groups.append((domain_id, domain_id, 0, elevation))
    if groups:
        return groups, None
    for domain_id in result.domain_ids():
        observation = result.observation_sets.get(domain_id)
        if observation is not None and observation.count:
            groups.append((domain_id, domain_id, 0, None))
    return groups, None


def _render_report(result: R.BLHeadlessResult,
                   case_dir: Path,
                   run_dir: Path,
                   presets: Sequence[PresetColumn],
                   sums: Mapping[str, Mapping[str, PresetSum]],
                   vertical: Mapping[str, Any]) -> str:
    freq = result.frequencies_hz
    freq_header = " | ".join(f"{float(f):g} Hz" for f in freq)
    lines: list[str] = []
    lines.append("# Boundary Lab reference case report")
    lines.append("")
    lines.append(f"- case: `{case_dir}`")
    lines.append(f"- run: `{run_dir}`")
    lines.append(f"- status: `{result.provenance.status}`; backend `{result.provenance.backend_id}`; "
                 f"solve kind `{result.provenance.solve_kind}`")
    lines.append(f"- phasors: `{result.provenance.phasor_convention}` -> "
                 f"`{C.TIME_CONVENTION}` (RMS; conjugated once only for the legacy BL label)")
    lines.append(f"- source geometry id: `{result.provenance.source_geometry_hash}`")
    lines.append("")

    lines.append("## Honesty labels")
    lines.append("")
    lines.append("- The woofer channel is normalised **per 2.83 V RMS**; the horn channel is "
                 "normalised **per 1 m/s normal velocity**. These are different input references "
                 "and are **never comparable as sensitivity** (efficiency, dB/W, or dB/V at the "
                 "same drive).")
    lines.append("- The per-preset sums below are **nominal per-input sums**: they answer "
                 "\"what pressure results when the woofer sees its declared 2.83 V reference and "
                 "the horn sees its declared 1 m/s reference, through this analog DSP\". They do "
                 "not answer which channel is louder for the same electrical or acoustic input.")
    per_input_text = ", ".join(f"`{name}` = `{per_input}`"
                               for name, per_input in result.data_quality
                               .get("per_input_by_excitation", {}).items())
    lines.append(f"- Per-input bases (from `compiled-system.json` `excitation_ports[].kind`): "
                 f"{per_input_text or 'unknown'}.")
    lines.append("- DSP presets are **analog prototypes** from `hornlab_search.system.dsp` / "
                 "`hornlab_search.meh.dsp` (LR4, gain in dB, horn-relative delay). There is no "
                 "biquad/sample-rate realisation, pre-warping or propagation model in this stage.")
    lines.append("- No spatial phase factor is applied in recombination: BL solved each excitation "
                 "in one declared observation frame and `combine` applies DSP only (phase-once "
                 "rule).")
    lines.append("")

    lines.append("## Result domains")
    lines.append("")
    for domain_id in result.domain_ids():
        observation = result.observation_sets[domain_id]
        distance = "mixed" if observation.distance_m is None else f"{observation.distance_m:g} m"
        angles = ("none" if observation.angles_deg is None
                  else ", ".join(f"{float(a):g}" for a in np.asarray(observation.angles_deg).reshape(-1)))
        lines.append(f"- `{domain_id}`: kind `{observation.kind}`, {observation.count} points, "
                     f"distance {distance}, angles_deg [{angles}]")
    lines.append("")

    lines.append("## Per-DSP-preset complex sums (nominal per-input)")
    lines.append("")
    for column in presets:
        by_domain = sums[column.name]
        lines.append(f"### `{column.name}`")
        lines.append("")
        lines.append(f"{column.description}.")
        lines.append("")
        lines.append(f"| observation | {freq_header} |")
        lines.append("|" + "---|" * (len(freq) + 1))
        for domain_id in result.domain_ids():
            total = by_domain[domain_id].total_pa
            cells = " | ".join(_fmt_complex(total[index, 0]) for index in range(total.shape[0]))
            lines.append(f"| `{_domain_label(result, domain_id)}` | {cells} |")
        lines.append("")

    lines.append("## Vertical lobing")
    lines.append("")
    lines.append(f"Reference sample: {vertical['reference_label']}. Levels are the coherent "
                 "nominal sum magnitude relative to that sample (dB).")
    lines.append("")
    for column_name, table in vertical["tables"].items():
        lines.append(f"### `{column_name}`")
        lines.append("")
        header = " | ".join(label for label, _values in table["groups"])
        lines.append(f"| frequency | {header} |")
        lines.append("|" + "---|" * (len(table["groups"]) + 1))
        for row_index, value in enumerate(table["frequencies_hz"]):
            levels = table["levels_db"][row_index]
            cells = " | ".join(_fmt_db(float(level)) for level in levels)
            lines.append(f"| {float(value):g} Hz | {cells} |")
        lines.append("")

    lines.append("## Provenance notes")
    lines.append("")
    for note in result.provenance.notes:
        lines.append(f"- {note}")
    if not result.provenance.notes:
        lines.append("- none recorded")
    lines.append("")
    lines.append(f"- BL install commit: `{result.provenance.bl_install_commit}`")
    lines.append(f"- result schema: `{result.provenance.result_schema}` v"
                 f"{result.provenance.result_schema_version}")
    lines.append("")
    return "\n".join(lines)


def report(
    case_dir: str | os.PathLike[str],
    *,
    run_dir: str | os.PathLike[str] | None = None,
    presets: Sequence[PresetColumn] | None = None,
    input_levels: Mapping[str, float] | None = None,
) -> ReferenceReport:
    """Build the markdown reference report from a real BL headless result directory.

    The files are only read. The run directory is ``<case_dir>/run`` by default.
    """
    root = Path(case_dir)
    if not root.is_dir():
        raise ReferenceError("REFERENCE_CASE_NOT_FOUND", f"case directory not found: {root}")
    resolved_run = _resolve_run_dir(root, run_dir)
    result = R.read_bl_headless_result(resolved_run)

    columns = tuple(presets) if presets is not None else dsp_preset_columns()
    domain_ids = tuple(result.domain_ids())
    sums: dict[str, dict[str, PresetSum]] = {}
    for column in columns:
        by_domain: dict[str, PresetSum] = {}
        for domain_id in domain_ids:
            by_domain[domain_id] = recompose_preset(
                result, domain_id, column, input_levels=input_levels)
        sums[column.name] = by_domain

    groups, vertical_domain = _vertical_series(result)
    reference_label = None
    reference_key: tuple[str, int] | None = None
    candidates = [(label, domain, index, elevation)
                  for label, domain, index, elevation in groups if elevation is not None]
    if candidates:
        best = min(candidates, key=lambda item: abs(item[3]))
        reference_label = best[0]
        reference_key = (best[1], best[2])
    elif groups:
        reference_label = groups[0][0]
        reference_key = (groups[0][1], groups[0][2])

    base_columns = [column for column in columns if column.name.endswith("_base")]
    tables: dict[str, Any] = {}
    for column in base_columns:
        levels_db: list[list[float]] = []
        for row in range(result.frequencies_hz.size):
            reference_value = None
            if reference_key is not None:
                reference_value = sums[column.name][reference_key[0]].total_pa[
                    row, reference_key[1]]
            row_levels: list[float] = []
            for _label, domain_id, index, _elevation in groups:
                value = sums[column.name][domain_id].total_pa[row, index]
                if reference_value is None or abs(reference_value) == 0.0:
                    row_levels.append(float("nan"))
                else:
                    row_levels.append(float(20.0 * np.log10(
                        max(abs(value), 1e-30) / abs(reference_value))))
            levels_db.append(row_levels)
        tables[column.name] = {
            "groups": [(label, []) for label, _d, _i, _e in groups],
            "frequencies_hz": [float(f) for f in result.frequencies_hz],
            "levels_db": levels_db,
        }

    vertical = {
        "domain_id": vertical_domain,
        "reference_label": reference_label,
        "groups": [
            {"label": label, "domain_id": domain_id, "column": index,
             "elevation_deg": elevation}
            for label, domain_id, index, elevation in groups
        ],
        "tables": tables,
    }

    markdown = _render_report(result, root, resolved_run, columns, sums, vertical)
    return ReferenceReport(
        case_dir=root,
        run_dir=resolved_run,
        markdown=markdown,
        frequencies_hz=tuple(float(f) for f in result.frequencies_hz),
        domain_ids=domain_ids,
        presets=columns,
        sums=sums,
        per_input_by_excitation=dict(result.data_quality.get("per_input_by_excitation", {})),
        vertical_lobing=vertical,
    )
