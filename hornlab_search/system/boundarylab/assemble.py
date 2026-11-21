"""Stage 4 CPU pre-work: horn-mesh assembly QA + documented BL draft project (NO solve).

Boundary Lab treats imported meshes as first-class project rows
(``ImportedMeshState``: absolute ``.msh`` path, ``scale_factor``, ``translation_mm``,
``enabled``; referenced as ``mesh:<name>``), and ``blab project validate --json`` is the
sanctioned arbiter of what an assembled project still needs. This module:

1. reads a saved HornFab horn mesh (metres!) and reports watertightness, physical groups,
   bbox and orientation — read-only QA, the "silent killer" guards included
   (``scale_factor`` MUST be 1.0 for HornFab meshes, which are already in metres);
2. builds the documented imported-mesh row + an explicit 4x4 mount transform and an
   :class:`~hornlab_search.system.contracts.AssemblyPoint`;
3. writes a DRAFT ``.blab.json`` carrying ONLY keys documented in BL's ``Inputs and
   Outputs.md``, then runs ``run.validate_project`` and records the EXACT gaps BL itself
   names — the remaining Stage-4 host-work list — never guessing schema or patch contents.

No solve is started anywhere: solve remains behind the senior/owner gate.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from hornlab_search.system import bass_reference, contracts as C, provenance
from hornlab_search.system.boundarylab import run as bl_run
from hornlab_search.system.boundarylab.probe import BLRoot, BLCapabilityError

__all__ = [
    "MeshQA", "horn_mesh_qa", "AssemblyPlan", "plan_assembly",
    "write_draft_project", "BLOCKED_BY_HOST_ASSEMBLY_ASSIGNMENTS",
]

#: The blocker token recorded while kind-assignment of imported horn groups is a human decision.
BLOCKED_BY_HOST_ASSEMBLY_ASSIGNMENTS = "BLOCKED_BY_BL_HOST_ASSEMBLY_ASSIGNMENTS"


@dataclass(frozen=True)
class MeshQA:
    path: str
    n_points: int
    n_triangles: int
    closed: bool                                   # every edge shared by exactly 2 triangles
    orientation_consistent: bool                   # every shared edge traversed once per direction
    free_edges: int
    free_edges_on_symmetry_planes: int             # x=0 and/or y=0 coordinate planes (1e-9 tol)
    symmetric_patch: bool                          # not closed, but all free edges on symmetry planes
    full_open_holes: int                           # free edges NOT explained by symmetry planes
    duplicate_points: int
    bbox_min_m: tuple[float, float, float]
    bbox_max_m: tuple[float, float, float]
    groups: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path, "n_points": self.n_points, "n_triangles": self.n_triangles,
            "closed": self.closed, "orientation_consistent": self.orientation_consistent,
            "free_edges": self.free_edges,
            "free_edges_on_symmetry_planes": self.free_edges_on_symmetry_planes,
            "symmetric_patch": self.symmetric_patch, "full_open_holes": self.full_open_holes,
            "duplicate_points": self.duplicate_points,
            "bbox_min_m": list(self.bbox_min_m), "bbox_max_m": list(self.bbox_max_m),
            "groups": list(self.groups),
        }


def horn_mesh_qa(mesh_path: str | Path) -> MeshQA:
    """Read-only QA of a HornFab horn mesh (already in metres).

    Topology classes: a fully closed surface (BL-ready for symmetry-off assemblies); or a
    fundamental-domain patch whose free edges all lie on the x=0/y=0 symmetry planes (a
    HornLab quarter model — valid for symmetric isolated solves, NOT directly consumable by
    a BL separate-mesh assembly without an explicit mirror-weld/full-domain mesh); or a mesh
    with true holes (unusable). Orientation uses directed-edge pairing.
    """
    import meshio

    path = Path(mesh_path)
    if not path.is_file():
        raise FileNotFoundError(f"horn mesh not found: {path}")
    mesh = meshio.read(path)
    tri_blocks = [np.asarray(cb.data, dtype=np.int64) for cb in mesh.cells if cb.type == "triangle"]
    if not tri_blocks:
        raise C.DataQualityError(f"no triangle blocks in horn mesh: {path}")
    tris = np.vstack(tri_blocks)
    pts = np.asarray(mesh.points, dtype=np.float64)
    uniq, inverse, counts = np.unique(np.round(pts, 9), axis=0, return_inverse=True,
                                      return_counts=True)
    dup_points = int(np.sum(counts > 1))
    t = inverse[tris]
    directed = np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]])
    und = np.sort(directed, axis=1)
    u_und, c_und = np.unique(und, axis=0, return_counts=True)
    u_dir, c_dir = np.unique(directed[:, 0].astype(np.int64) * len(uniq) + directed[:, 1],
                             return_counts=True)
    free = int(np.sum(c_und == 1))
    closed = free == 0
    on_plane = 0
    if free:
        free_mask = c_und == 1
        free_edges = u_und[free_mask]
        # free edges whose BOTH endpoints have x==0 or BOTH have y==0 (tol 1e-9).
        # NB: edge indices refer to the lexicographically sorted `uniq` array, so the
        # coordinate lookup must use `uniq`, not the original point order.
        x0 = np.abs(uniq[free_edges[:, 0], 0]) < 1e-9
        x1 = np.abs(uniq[free_edges[:, 1], 0]) < 1e-9
        y0 = np.abs(uniq[free_edges[:, 0], 1]) < 1e-9
        y1 = np.abs(uniq[free_edges[:, 1], 1]) < 1e-9
        on_plane = int(np.sum((x0 & x1) | (y0 & y1)))
    full_holes = free - on_plane
    symmetric_patch = (not closed) and full_holes == 0 and on_plane == free
    orientation = bool(np.all(c_dir == 1))
    groups = tuple(sorted(str(k) for k in (mesh.field_data or {})))
    bbox_min = (float(pts[:, 0].min()), float(pts[:, 1].min()), float(pts[:, 2].min()))
    bbox_max = (float(pts[:, 0].max()), float(pts[:, 1].max()), float(pts[:, 2].max()))
    return MeshQA(path=str(path), n_points=int(pts.shape[0]), n_triangles=int(tris.shape[0]),
                  closed=closed, orientation_consistent=orientation,
                  free_edges=free, free_edges_on_symmetry_planes=on_plane,
                  symmetric_patch=symmetric_patch, full_open_holes=full_holes,
                  duplicate_points=dup_points, bbox_min_m=bbox_min, bbox_max_m=bbox_max,
                  groups=groups)


@dataclass(frozen=True)
class AssemblyPlan:
    """Verified assembly inputs (identity-hashed); the BL draft + its validate verdict."""

    assembly_id: str
    horn_mesh: MeshQA
    imported_mesh_row: dict[str, Any]
    draft_project_path: Path | None
    validate_result: bl_run.ValidationResult | None
    blockers: tuple[str, ...]
    transform_m: tuple[tuple[float, ...], ...]
    payload: Mapping[str, Any]


def _imported_row(horn_mesh_path: Path, name: str, scale_factor: float,
                  translation_mm: tuple[float, float, float]) -> dict[str, Any]:
    """The documented ``ImportedMeshState`` payload (``Inputs and Outputs.md``)."""
    if scale_factor == 0.001:
        raise C.DataQualityError(
            "refusing scale_factor=0.001: HornFab horn meshes are already in METRES; "
            "the BL waveguide-example factor scales millimetre-designed meshes")
    return {
        "cleaned_file": None,
        "enabled": True,
        "name": name,
        "scale_factor": float(scale_factor),
        "source_file": str(Path(horn_mesh_path).resolve()),
        "translation_mm": [float(t) for t in translation_mm],
    }


def plan_assembly(
    horn_asset_mesh: str | Path,
    box: C.BoxPoint,
    *,
    horn_name: str = "horn",
    horn_mount_offset_z_mm: float = 0.0,
    out_dir: str | Path | None = None,
    experiment_id: str = "bl_assembly_prep",
    bl_root: BLRoot | None = None,
    validate_draft: bool = True,
) -> AssemblyPlan:
    """Build the verified assembly inputs and (optionally) validate a documented draft.

    ``box`` must be a feasible :class:`BoxPoint` from the LF screen. The plan records the
    explicit transform, the imported-mesh row, and — when ``validate_draft`` and a verified
    BLRoot are given — the BL ``project validate`` verdict on the DRAFT. The verdict's exact
    errors are the recorded blockers: kind-assignment of imported horn groups and the host-side
    staging of generated meshes stay deliberate human/host work (never guessed here).
    """
    qa = horn_mesh_qa(horn_asset_mesh)
    blockers: list[str] = []
    if qa.full_open_holes > 0:
        raise C.DataQualityError(
            f"horn mesh has {qa.full_open_holes} free edges NOT on symmetry planes (true "
            "holes); no BL assembly accepts it")
    if qa.symmetric_patch:
        blockers.append(
            f"BLOCKED_BY_FULL_DOMAIN_HORN_MESH: the saved horn is a {qa.free_edges}-free-edge "
            "fundamental-domain patch (HornLab quarter model); a BL separate-mesh assembly "
            "under symmetry-off needs a FULL-DOMAIN closed horn surface (HornFab full-model "
            "mesh or an explicit mirror-weld step), not an improvised closure")
    elif not qa.closed:
        blockers.append("BLOCKED_BY_OPEN_HORN_MESH")
    row = _imported_row(Path(horn_asset_mesh), horn_name, scale_factor=1.0,
                        translation_mm=(0.0, 0.0, float(horn_mount_offset_z_mm)))
    transform = (
        (1.0, 0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0, float(horn_mount_offset_z_mm) / 1000.0),
        (0.0, 0.0, 0.0, 1.0),
    )
    payload = {
        "kind": "bl_assembly_prep_v0",
        "topology": "separate_closed_meshes" if qa.closed else "blocked_topology",
        "horn_mesh": qa.to_dict(),
        "imported_mesh_row": row,
        "horn_mesh_id": f"mesh:{horn_name}",
        "vented_source": {key: float(value) for key, value in _box_to_vented_source(box).items()},
        "transform_m": [list(r) for r in transform],
        "blockers": list(blockers),
        "driver_frame_mm": {"cutout": None},
    }
    assembly_id = C.assembly_geometry_id(payload)
    draft_path = None
    validate_result = None
    if validate_draft:
        if bl_root is None:
            raise BLCapabilityError((f"{BLOCKED_BY_HOST_ASSEMBLY_ASSIGNMENTS}: "
                                     "validate_draft requires a verified BLRoot",))
        if out_dir is None:
            raise ValueError("out_dir is required when validate_draft is True")
        case_dir = provenance.new_case_dir(experiment_id, store_root=out_dir, tag="assembly")
        draft_path = write_draft_project(case_dir, row, box)
        validate_result = bl_run.validate_project(bl_root, draft_path)
        payload["draft_project"] = str(draft_path)
        if validate_result.returncode != 0 or not (validate_result.parsed or {}).get("valid"):
            errors = _extract_errors(validate_result)
            blockers = blockers + [BLOCKED_BY_HOST_ASSEMBLY_ASSIGNMENTS] + errors
        provenance.write_manifest(case_dir, payload | {"validate": _validate_dict(validate_result)})
    return AssemblyPlan(assembly_id=assembly_id, horn_mesh=qa, imported_mesh_row=row,
                        draft_project_path=draft_path, validate_result=validate_result,
                        blockers=tuple(blockers), transform_m=transform, payload=payload)


#: BL provider default ``port_roundover_m`` (``enclosure/parameters.py``), i.e. the lip added
#: at each port end. It is a Boundary Lab default, not a horn number; ``woofer_seed`` records
#: the same value as ``BL_DEMO_PORT_ROUNDOVER_M``. Keep the two in step.
_BL_PORT_ROUNDOVER_M = 0.008


def _box_to_vented_source(box: C.BoxPoint) -> dict[str, float]:
    """Map a verified BoxPoint onto BL's exact vented-source keys (verified units, mm→m).

    The vented plugin takes external W/H/D and wall; the internal air volume BL meshes is
    reported in ``mesh_info`` at generation time — the mapping here is geometry-level only.

    BL's ``port_length_m`` is the *total physical length including both lips*, while
    :class:`contracts.BoxPoint.derived_effective_port_length_m` is the lumped effective length
    (neck + bassbox's ``N_END * 0.85 * r_eq``). Passing the effective length through as the
    total length silently lengthened the BL port by the end correction; invert the bassbox
    derivation first and add the two provider-default lips (risk R17).
    """
    effective = box.derived_effective_port_length_m
    if effective is None:
        port_length_m = 0.0
    else:
        neck_m = bass_reference.port_neck_length_mm(box) * 1e-3
        port_length_m = neck_m + 2.0 * _BL_PORT_ROUNDOVER_M
    return {
        "width_m": box.external_width_mm / 1000.0,
        "height_m": box.external_height_mm / 1000.0,
        "depth_m": box.external_depth_mm / 1000.0,
        "wall_m": box.wall_mm / 1000.0,
        "port_length_m": port_length_m,
        "port_area_m2": box.port_throat_area_cm2 * 1e-4,
        "port_nfr": box.port_nfr,
    }


def write_draft_project(case_dir: Path, imported_row: Mapping[str, Any],
                        box: C.BoxPoint) -> Path:
    """A DRAFT .blab.json with ONLY documented top-level keys; BL validate is the authority.

    The draft intentionally leaves ``physical_system`` empty: region/boundary/interface kind
    assignment for the imported horn groups is a deliberate modelling decision (and the host's
    own staging owns generated-mesh artifacts). The validate verdict enumerates the gaps.
    """
    draft = {
        "schema_version": 10,
        "active_generator_document_id": "vented",
        "generator_documents": [{
            "id": "vented",
            "name": "vented",
            "provider_id": "blab.vented_enclosure",
            "provider_schema_version": 1,
            "source": {"format": "structured", "values": {}},
            "mesh_enabled": True,
            "mesh_scale_factor": 1.0,
            "mesh_translation_mm": [0, 0, 0],
            "artifact": None,
        }],
        "imported_meshes": [dict(imported_row)],
        "stitch_exterior_meshes": True,
        "physical_system": {},
        "component_channel_by_id": {},
        "observation_planes": [],
    }
    path = Path(case_dir) / "assembly_draft.blab.json"
    path.write_text(json.dumps(draft, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _extract_errors(result: bl_run.ValidationResult) -> list[str]:
    parsed = result.parsed or {}
    collected: list[str] = []
    for key in ("errors", "error", "problems"):
        value = parsed.get(key)
        if isinstance(value, list):
            collected.extend(str(e) for e in value)
        elif isinstance(value, str):
            collected.append(value)
    if not collected:
        collected.extend(result.stderr_tail[-6:])
    if not collected:
        collected.append(f"validate returncode {result.returncode}; stdout "
                         + " / ".join(result.stdout_tail[-4:]))
    return collected


def _validate_dict(result: bl_run.ValidationResult) -> dict[str, Any]:
    return {
        "returncode": result.returncode,
        "valid": None if result.parsed is None else result.parsed.get("valid"),
        "parsed_keys": (None if result.parsed is None else sorted(result.parsed)),
        "stdout_tail": list(result.stdout_tail[-6:]),
        "stderr_tail": list(result.stderr_tail[-6:]),
    }
