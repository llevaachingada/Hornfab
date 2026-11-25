"""One resolved three-dimensional horn-over-cabinet pose, and its legality.

The defect this module closes
-----------------------------
Three separate places used to decide "where does the horn go": the LF screen derived a
*vertical-only* offset and wrote a 4x4 transform into a CSV row, ``plan_assembly``
hard-coded a *forward-only* offset, and staging accepted whatever ``translation_mm`` the
caller happened to pass.  Nothing carried one authoritative pose from screening to the
Boundary Lab project, and the screen's ``separate_above`` rule required the horn envelope
to clear the *top face at every z*, which rejects the owner's own arrangement: a horn
seated on the cabinet whose mouth overhangs the front face and overlaps the box in the
front-view silhouette.

This module defines that pose once, resolves it from real mesh geometry, validates it
against the exact cabinet solid, and serialises it unchanged into the stage spec.

Coordinate frame (shared with :class:`contracts.AssemblyRanges`)
---------------------------------------------------------------
X = left/right, Y = up, Z = toward the listener.  The cabinet front/baffle plane is
``z = 0`` and the cabinet body occupies ``z < 0``; the horn source mesh keeps its own
origin (HornLab meshes run from the throat near ``z = 0`` to the mouth at ``+z``).

Placement policy
----------------
``seated_overhang`` (the owner's arrangement) uses the physically correct rule:

    every part of the horn that is not clearly in front of the baffle plane
    (``z + dz < clearance``) and is inside the cabinet's side walls must be above the
    cabinet top by the declared clearance.

For a rigid, non-rotated horn this gives a **closed-form minimum dy** from the real mesh:
the throat/rear cross-section governs, not the mouth radius.  The mouth may then hang
forward and below the cabinet top line, which is exactly what the photo shows.  The pose
is afterwards verified against the exact triangle-vs-box distance (:mod:`.collision`);
the policy bound never replaces that check.

``above`` keeps the older conservative rule (the whole envelope clears the top face) for
comparability with the already-solved cases.

A pose whose rear no longer overhangs the cabinet top must be carried by a bracket.  That
is recorded as ``support="unmodeled_cantilever"`` -- never silently assumed to be free.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from hornlab_search.system import contracts as C
from hornlab_search.system.boundarylab import collision

__all__ = [
    "LAYOUT_ABOVE",
    "LAYOUT_SEATED_OVERHANG",
    "PlacementIllegal",
    "AssemblyPose",
    "cabinet_box_mm",
    "load_horn_points_mm",
    "min_legal_dy_mm",
    "resolve_pose",
    "silhouette_overlap_mm",
]

#: Same sane cabinet-scale limit as ``woofer_seed.MAX_MOUNT_OFFSET_MM`` (kept local to avoid
#: importing the screen module from the pose module).
_MAX_MOUNT_OFFSET_MM = 5000.0

LAYOUT_ABOVE = "above"
LAYOUT_SEATED_OVERHANG = "seated_overhang"
_LAYOUTS = (LAYOUT_ABOVE, LAYOUT_SEATED_OVERHANG)


class PlacementIllegal(C.DataQualityError):
    """A requested pose is not mechanically legal for the resolved geometry."""


@dataclass(frozen=True)
class AssemblyPose:
    """The single authoritative placement of the horn on/above the woofer cabinet."""

    layout: str
    dx_mm: float
    dy_mm: float
    dz_mm: float
    translation_mm: tuple[float, float, float]
    transform_m: tuple[tuple[float, float, float, float], ...]
    support: str
    clearance_mm: float
    horn_mesh_path: str
    horn_mesh_sha256: str
    horn_design_hash: str
    horn_bbox_mm: tuple[float, float, float, float, float, float]
    horn_world_bbox_mm: tuple[float, float, float, float, float, float]
    cabinet_dims_mm: tuple[float, float, float]
    cabinet_bbox_mm: tuple[float, float, float, float, float, float]
    cabinet_sha256: str
    silhouette: Mapping[str, Any]
    clearance: Mapping[str, Any]
    geometry_id: str
    detail: Mapping[str, Any] = field(default_factory=dict)

    @property
    def horn_mount_offset_x_mm(self) -> float:
        return self.dx_mm

    @property
    def horn_mount_offset_y_mm(self) -> float:
        return self.dy_mm

    @property
    def horn_mount_offset_z_mm(self) -> float:
        return self.dz_mm

    @property
    def legal(self) -> bool:
        return str(self.clearance.get("status")) == collision.CLEARANCE_PASS

    def stage_translation_mm(self) -> tuple[float, float, float]:
        """Exactly what goes into ``MeshResource.translation_mm`` (BL divides by 1000)."""
        return self.translation_mm

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "horn_cabinet_pose_v1",
            "layout": self.layout,
            "dx_mm": self.dx_mm,
            "dy_mm": self.dy_mm,
            "dz_mm": self.dz_mm,
            "translation_mm": list(self.translation_mm),
            "transform_m": [list(row) for row in self.transform_m],
            "support": self.support,
            "clearance_mm": self.clearance_mm,
            "horn_mesh_path": self.horn_mesh_path,
            "horn_mesh_sha256": self.horn_mesh_sha256,
            "horn_design_hash": self.horn_design_hash,
            "horn_bbox_mm": list(self.horn_bbox_mm),
            "horn_world_bbox_mm": list(self.horn_world_bbox_mm),
            "cabinet_dims_mm": list(self.cabinet_dims_mm),
            "cabinet_bbox_mm": list(self.cabinet_bbox_mm),
            "cabinet_sha256": self.cabinet_sha256,
            "silhouette": dict(self.silhouette),
            "clearance": dict(self.clearance),
            "geometry_id": self.geometry_id,
            "legal": self.legal,
            "detail": dict(self.detail),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AssemblyPose":
        return cls(
            layout=str(data["layout"]),
            dx_mm=float(data["dx_mm"]), dy_mm=float(data["dy_mm"]), dz_mm=float(data["dz_mm"]),
            translation_mm=(float(data["translation_mm"][0]), float(data["translation_mm"][1]),
                            float(data["translation_mm"][2])),
            transform_m=tuple(tuple(float(v) for v in row) for row in data["transform_m"]),  # type: ignore[arg-type]
            support=str(data["support"]), clearance_mm=float(data["clearance_mm"]),
            horn_mesh_path=str(data["horn_mesh_path"]),
            horn_mesh_sha256=str(data["horn_mesh_sha256"]),
            horn_design_hash=str(data.get("horn_design_hash") or ""),
            horn_bbox_mm=tuple(float(v) for v in data["horn_bbox_mm"]),  # type: ignore[arg-type]
            horn_world_bbox_mm=tuple(float(v) for v in data["horn_world_bbox_mm"]),  # type: ignore[arg-type]
            cabinet_dims_mm=tuple(float(v) for v in data["cabinet_dims_mm"]),  # type: ignore[arg-type]
            cabinet_bbox_mm=tuple(float(v) for v in data["cabinet_bbox_mm"]),  # type: ignore[arg-type]
            cabinet_sha256=str(data["cabinet_sha256"]),
            silhouette=dict(data.get("silhouette") or {}),
            clearance=dict(data.get("clearance") or {}),
            geometry_id=str(data["geometry_id"]),
            detail=dict(data.get("detail") or {}),
        )


# --------------------------------------------------------------------------- helpers

def cabinet_box_mm(*, width_mm: float, height_mm: float, depth_mm: float
                   ) -> tuple[float, float, float, float, float, float]:
    w, h, d = (float(v) for v in (width_mm, height_mm, depth_mm))
    return (-w / 2.0, -h / 2.0, -d, w / 2.0, h / 2.0, 0.0)


def _cabinet_sha(width_mm: float, height_mm: float, depth_mm: float) -> str:
    payload = {"w_mm": round(float(width_mm), 9), "h_mm": round(float(height_mm), 9),
               "d_mm": round(float(depth_mm), 9), "frame": "baffle_z0_body_zneg"}
    return C.domain_sha16("system.cabinet_box_v1", payload)


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_horn_points_mm(mesh_path: str | Path) -> np.ndarray:
    """Horn surface points in millimetres (HornLab meshes are written in metres)."""
    surface = collision.read_surface(mesh_path, label="horn")
    return np.asarray(surface.points, dtype=np.float64) * 1e3


# --------------------------------------------------------------------------- policy

def min_legal_dy_mm(points_mm: np.ndarray, *, dz_mm: float, cabinet: Mapping[str, float],
                    clearance_mm: float, dx_mm: float = 0.0) -> float | None:
    """Lowest vertical offset that keeps every non-forward horn part above the cabinet top.

    ``None`` means no part of the horn would remain over the cabinet top at this ``dz``
    (the placement becomes a cantilever and needs an explicit ``dy``).
    """
    pts = np.asarray(points_mm, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 3:
        raise ValueError(f"points_mm must be (N,3), got {pts.shape}")
    gap = float(clearance_mm)
    if not (math.isfinite(gap) and gap > 0.0):
        raise ValueError(f"clearance_mm must be positive and finite, got {clearance_mm!r}")
    w = float(cabinet["external_width_mm"])
    h = float(cabinet["external_height_mm"])
    z = pts[:, 2] + float(dz_mm)
    x = pts[:, 0] + float(dx_mm)
    not_front = z < gap
    inside_walls = (x > -w / 2.0 - gap) & (x < w / 2.0 + gap)
    rear = not_front & inside_walls
    if not bool(np.any(rear)):
        return None
    return float(h / 2.0 + gap - pts[rear, 1].min())


def silhouette_overlap_mm(horn_world_bbox_mm: Sequence[float], *,
                          width_mm: float, height_mm: float) -> dict[str, Any]:
    """Front-view (x-y) overlap of the horn outline with the cabinet front face.

    Overlap here is a *drawing* relation, deliberately reported apart from collision: a
    mouth may hang in front of the baffle and overlap the box in the front view while the
    solids stay separate.
    """
    x0, y0, _z0, x1, y1, _z1 = (float(v) for v in horn_world_bbox_mm)
    w, h = float(width_mm), float(height_mm)
    ox = max(0.0, min(x1, w / 2.0) - max(x0, -w / 2.0))
    oy = max(0.0, min(y1, h / 2.0) - max(y0, -h / 2.0))
    return {
        "front_view_x_overlap_mm": float(ox),
        "front_view_y_overlap_mm": float(oy),
        "front_view_area_mm2": float(ox * oy),
        "mouth_lower_lip_below_top_mm": float(max(0.0, h / 2.0 - y0)),
        "projection_overlap_is_not_a_collision": True,
    }


def _support(points_mm: np.ndarray, *, dx_mm: float, dy_mm: float, dz_mm: float,
             cabinet: Mapping[str, float]) -> str:
    w = float(cabinet["external_width_mm"])
    h = float(cabinet["external_height_mm"])
    x = points_mm[:, 0] + dx_mm
    y = points_mm[:, 1] + dy_mm
    z = points_mm[:, 2] + dz_mm
    over_top = (z <= 0.0) & (np.abs(x) <= w / 2.0) & (y >= h / 2.0)
    return "seated_on_cabinet_top" if bool(np.any(over_top)) else "unmodeled_cantilever"


# --------------------------------------------------------------------------- resolve

def resolve_pose(
    horn_mesh: str | Path,
    *,
    cabinet: Mapping[str, float],
    dz_mm: float = 0.0,
    dy_mm: float | None = None,
    dx_mm: float = 0.0,
    layout: str = LAYOUT_SEATED_OVERHANG,
    clearance_mm: float = 3.0,
    horn_design_hash: str = "",
    compiled_exterior: str | Path | None = None,
    driver_frame: Mapping[str, float] | None = None,
    cutoff_m: float = 0.05,
) -> AssemblyPose:
    """Resolve and validate the one authoritative horn-over-cabinet pose.

    ``dy_mm=None`` derives the closest buildable height for the requested ``dz_mm`` under
    the selected policy.  The pose is then checked with the exact cabinet-solid clearance
    and :class:`PlacementIllegal` is raised if it fails -- the policy bound is never the
    final word.
    """
    if layout not in _LAYOUTS:
        raise ValueError(f"layout must be one of {_LAYOUTS}, got {layout!r}")
    gap = float(clearance_mm)
    if not (math.isfinite(gap) and gap > 0.0):
        raise ValueError(f"clearance_mm must be positive and finite, got {clearance_mm!r}")
    path = Path(horn_mesh)
    if not path.is_file():
        raise FileNotFoundError(f"horn mesh not found: {path}")
    dims = {
        "external_width_mm": float(cabinet["external_width_mm"]),
        "external_height_mm": float(cabinet["external_height_mm"]),
        "external_depth_mm": float(cabinet["external_depth_mm"]),
    }
    pts_mm = load_horn_points_mm(path)
    z_min = float(pts_mm[:, 2].min())

    if dy_mm is None:
        if layout == LAYOUT_ABOVE:
            dy_value = dims["external_height_mm"] / 2.0 - float(pts_mm[:, 1].min()) + gap
        else:
            derived = min_legal_dy_mm(pts_mm, dz_mm=float(dz_mm), cabinet=dims,
                                      clearance_mm=gap, dx_mm=float(dx_mm))
            if derived is None:
                raise PlacementIllegal(
                    f"dz_mm={dz_mm:g} puts the whole horn in front of the baffle plane "
                    f"(horn z_min={z_min:g} mm + dz > {gap:g} mm); no part remains over "
                    "the cabinet top, so dy cannot be derived - pass an explicit dy_mm "
                    "and record the support as a cantilever")
            dy_value = derived
    else:
        dy_value = float(dy_mm)

    if not (math.isfinite(dy_value) and math.isfinite(float(dx_mm))
            and math.isfinite(float(dz_mm))):
        raise PlacementIllegal("pose offsets must be finite")
    if (abs(dx_mm) > _MAX_MOUNT_OFFSET_MM or abs(dy_value) > _MAX_MOUNT_OFFSET_MM
            or abs(dz_mm) > _MAX_MOUNT_OFFSET_MM):
        raise PlacementIllegal(
            f"pose offset exceeds {_MAX_MOUNT_OFFSET_MM:g} mm; values look like metres")

    translation = (float(dx_mm), float(dy_value), float(dz_mm))
    transform = (
        (1.0, 0.0, 0.0, translation[0] / 1e3),
        (0.0, 1.0, 0.0, translation[1] / 1e3),
        (0.0, 0.0, 1.0, translation[2] / 1e3),
        (0.0, 0.0, 0.0, 1.0),
    )
    horn_surface = collision.transform_surface(
        collision.read_surface(path, label="horn"), translation_mm=translation)
    box = collision.box_from_cabinet_mm(
        width_mm=dims["external_width_mm"], height_mm=dims["external_height_mm"],
        depth_mm=dims["external_depth_mm"])
    extra_solids: list[collision.Box] = []
    if driver_frame:
        radius = float(driver_frame["frame_od_mm"]) / 2.0 / 1e3
        depth = float(driver_frame["depth_behind_baffle_mm"]) / 1e3
        cy = float(driver_frame.get("center_y_mm", 0.0)) / 1e3
        cx = float(driver_frame.get("center_x_mm", 0.0)) / 1e3
        if not (radius > 0.0 and depth > 0.0):
            raise PlacementIllegal("driver_frame frame_od_mm and depth_behind_baffle_mm "
                                   "must be positive")
        extra_solids.append(collision.Box(lo=(cx - radius, cy - radius, -depth),
                                          hi=(cx + radius, cy + radius, 0.0)))
    exterior = None
    if compiled_exterior is not None:
        exterior = collision.read_surface(compiled_exterior, label="cabinet_exterior")
    report = collision.test_horn_box_clearance(
        horn_surface, box, min_gap_m=gap / 1e3, cutoff_m=cutoff_m,
        compiled_exterior=exterior, extra_solids=extra_solids)

    world_lo = horn_surface.bounds[0] * 1e3
    world_hi = horn_surface.bounds[1] * 1e3
    world_bbox = (*world_lo.tolist(), *world_hi.tolist())
    bbox_mm = (*pts_mm.min(axis=0).tolist(), *pts_mm.max(axis=0).tolist())
    cabinet_bbox = cabinet_box_mm(
        width_mm=dims["external_width_mm"], height_mm=dims["external_height_mm"],
        depth_mm=dims["external_depth_mm"])
    silhouette = silhouette_overlap_mm(world_bbox, width_mm=dims["external_width_mm"],
                                       height_mm=dims["external_height_mm"])
    support = _support(pts_mm, dx_mm=float(dx_mm), dy_mm=dy_value, dz_mm=float(dz_mm),
                       cabinet=dims)
    horn_sha = _file_sha(path)
    cab_sha = _cabinet_sha(dims["external_width_mm"], dims["external_height_mm"],
                            dims["external_depth_mm"])
    geometry_payload = {
        "layout": layout,
        "translation_mm": [round(v, 9) for v in translation],
        "horn_mesh_sha256": horn_sha,
        "horn_design_hash": str(horn_design_hash),
        "cabinet_sha256": cab_sha,
        "clearance_mm": round(gap, 9),
    }
    geometry_id = C.assembly_geometry_id(geometry_payload)
    pose = AssemblyPose(
        layout=layout, dx_mm=float(dx_mm), dy_mm=dy_value, dz_mm=float(dz_mm),
        translation_mm=translation, transform_m=transform, support=support,
        clearance_mm=gap, horn_mesh_path=str(path.resolve()), horn_mesh_sha256=horn_sha,
        horn_design_hash=str(horn_design_hash), horn_bbox_mm=tuple(bbox_mm),
        horn_world_bbox_mm=tuple(world_bbox),  # type: ignore[arg-type]
        cabinet_dims_mm=(dims["external_width_mm"], dims["external_height_mm"],
                         dims["external_depth_mm"]),
        cabinet_bbox_mm=cabinet_bbox, cabinet_sha256=cab_sha, silhouette=silhouette,
        clearance=report.to_dict(), geometry_id=geometry_id,
        detail={"geometry_payload": geometry_payload,
                "cabinet_inputs": dict(dims),
                "driver_frame": None if not driver_frame else dict(driver_frame),
                "source_frame": "horn throat near z=0, mouth at +z, axis on x=y=0"},
    )
    if not pose.legal:
        hint = ""
        if extra_solids:
            required_dz = gap - z_min
            hint = (f"; the woofer frame occupies the plane behind the baffle, so a horn "
                    f"that overlaps it in x/y needs dz >= {required_dz:.3f} mm "
                    f"(horn z_min {z_min:g} + dz >= clearance {gap:g})")
        raise PlacementIllegal(
            f"resolved pose is not legal: status={report.status} "
            f"min_distance_m={report.min_distance_m} "
            f"reason={report.detail.get('reason')}{hint}")
    return pose
