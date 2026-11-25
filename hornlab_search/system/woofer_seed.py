"""Stage-5 deterministic fixed-horn woofer/cabinet/XO/placement seed screen.

This module is a **CPU-only, solver-free heuristic screen**.  It never writes BEM/FEM code, never
runs a solver and never contacts a GPU.  It takes ONE saved horn asset plus a sourced driver
catalog and enumerates:

* real T/S + the fixed ``tools/bassbox.py`` vented model (via
  :mod:`hornlab_search.system.bass_reference`) for Vb/Fb/port feasibility;
* candidate crossover regions from the actual horn/woofer overlap bands computed by
  :mod:`hornlab_search.system.compatibility` (never a fixed universal window);
* mechanical placements: ``dx = 0``, zero tilt, the *derived-legal* minimum centre spacing from
  the real horn outer envelope + cabinet frame + explicit clearance, plus 1-3 modest legal
  ``dz`` offsets toward the listener;
* a multi-axis non-dominated Pareto shortlist (match error H and V, LF extension, port-velocity
  ratio, excursion headroom, cabinet footprint, mounting distance).  **No scalar winner.**

Placement coordinate convention (from ``contracts.AssemblyRanges``): cabinet-front frame,
``z = 0`` is the baffle and **+z points away from the box toward the listener**; ``x`` is the
horizontal offset and ``y`` the vertical offset.  ``mount_transform`` makes that convention
explicit and is unit-tested for sign errors.

Determinism: identical inputs produce byte-identical JSON/Markdown.  Nothing time- or
path-dependent is serialised; the optional case manifest written by the caller's tooling is the
only place a timestamp/path may appear, and it is excluded from the replay identity.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from hornlab_search.meh.drivers import ConeDriver, load_cone
from hornlab_search.system import bass_reference, compatibility, contracts as C, provenance
from hornlab_search.system import drivers as sys_drivers
from hornlab_search.system.geometry import rules as fit_rules

__all__ = [
    "SEED_SCHEMA",
    "DEFAULT_TS_DIR",
    "DEFAULT_GEOMETRY_DIR",
    "DEFAULT_DRIVER_STEMS",
    "HornEnvelope",
    "envelope_from_bbox_m",
    "validate_bbox_m",
    "derive_horn_envelope",
    "derive_min_center_spacing_mm",
    "mount_transform",
    "PlacementCheck",
    "placement_legality",
    "DriverEntry",
    "CatalogResult",
    "load_driver_catalog",
    "evaluate_box",
    "bl_panel_fit_feasible",
    "bl_panel_fit_separation",
    "select_box_sample",
    "SeedResult",
    "run_seed_screen",
    "main",
]

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TS_DIR = REPO_ROOT / "examples" / "systems" / "driver_ts"
DEFAULT_GEOMETRY_DIR = REPO_ROOT / "examples" / "systems" / "driver_geometry"

SEED_SCHEMA = "hornlab.system.woofer_seed.v1"
#: The sourced system catalog (10-inch pair added Stage 5; 12-inch pair verified Stage 0).
DEFAULT_DRIVER_STEMS: tuple[str, ...] = (
    "faitalpro_10pr300", "faitalpro_10pr320",
    "faitalpro_12pr300", "faitalpro_12pr320",
)

#: Sane mount-offset envelope [mm].  A 1000x unit mistake (metres mistakenly passed as mm)
#: is refused instead of silently producing a metres-away placement.
MAX_MOUNT_OFFSET_MM: float = 5000.0
#: A horn outer-envelope bbox must be metre-scale; this catches a mm-vs-m / 1000x mistake.
MIN_BBOX_EXTENT_M: float = 0.02
MAX_BBOX_EXTENT_M: float = 5.0
#: Explicit baffle/cabinet clearance policy used by the placement legality rule.
DEFAULT_CLEARANCE_MM: float = 10.0
#: Default modest, legal forward offsets toward the listener.
DEFAULT_DZ_OFFSETS_MM: tuple[float, ...] = (0.0, 25.0, 50.0)
#: Pareto shortlist display cap (never a single winner).
DEFAULT_SHORTLIST_SIZE: int = 6

#: Pareto axes and directions (maximise "+", minimise "-").
SEED_AXIS_DIRECTIONS: Mapping[str, str] = {
    "match_error_h_db2": "-",
    "match_error_v_db2": "-",
    "lf_f3_hz": "-",
    "port_velocity_ratio": "-",
    "excursion_margin_db": "+",
    "cabinet_footprint_m2": "-",
    "mounting_distance_mm": "-",
}


# --------------------------------------------------------------------------- numeric helpers


def _finite(value: Any, name: str) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number, got {value!r}") from None
    if not math.isfinite(x):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return x


def _round(value: Any) -> Any:
    """Deterministic JSON-safe scalar: 12-decimal floats, None for non-finite."""
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        x = float(value)
        return round(x, 12) if math.isfinite(x) else None
    if isinstance(value, Mapping):
        return {str(k): _round(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_round(v) for v in value]
    if isinstance(value, np.ndarray):
        return [_round(v) for v in value.tolist()]
    return str(value)


# --------------------------------------------------------------------------- horn envelope


@dataclass(frozen=True)
class HornEnvelope:
    """Full-domain outer envelope of the horn, in millimetres in its own axis frame."""

    x_min_mm: float
    x_max_mm: float
    y_min_mm: float
    y_max_mm: float
    z_min_mm: float
    z_max_mm: float
    source: str
    design_hash: str
    envelope_sha256: str
    #: Absolute path of the full-domain horn mesh the envelope was measured from, when
    #: known. The overhang placement policy needs the real surface, not just the bbox.
    mesh_path: str | None = None

    @property
    def width_mm(self) -> float:
        return float(self.x_max_mm - self.x_min_mm)

    @property
    def height_mm(self) -> float:
        return float(self.y_max_mm - self.y_min_mm)

    @property
    def depth_mm(self) -> float:
        return float(self.z_max_mm - self.z_min_mm)

    def to_dict(self) -> dict[str, Any]:
        return _round({
            "x_min_mm": self.x_min_mm, "x_max_mm": self.x_max_mm,
            "y_min_mm": self.y_min_mm, "y_max_mm": self.y_max_mm,
            "z_min_mm": self.z_min_mm, "z_max_mm": self.z_max_mm,
            "width_mm": self.width_mm, "height_mm": self.height_mm,
            "depth_mm": self.depth_mm, "source": self.source,
            "design_hash": self.design_hash,
            "envelope_sha256": self.envelope_sha256,
        })


def validate_bbox_m(bbox: Sequence[float]) -> float:
    """Validate a metre bbox ``(xmin,ymin,zmin,xmax,ymax,zmax)`` and return its max extent.

    A largest extent above :data:`MAX_BBOX_EXTENT_M` is reported as a unit-scale error: the
    usual cause is millimetres passed where metres are required (1000x).
    """
    if len(bbox) != 6:
        raise ValueError("bbox must have 6 values (xmin,ymin,zmin,xmax,ymax,zmax)")
    x0, y0, z0, x1, y1, z1 = (_finite(v, "bbox value") for v in bbox)
    if not (x0 <= x1 and y0 <= y1 and z0 <= z1):
        raise ValueError(f"bbox min must be <= max, got {bbox!r}")
    extent = max(x1 - x0, y1 - y0, z1 - z0)
    if extent > MAX_BBOX_EXTENT_M:
        raise ValueError(
            f"unit-scale error: largest bbox extent {extent:.6g} m > "
            f"{MAX_BBOX_EXTENT_M:g} m; values look like millimetres (1000x)")
    if extent < MIN_BBOX_EXTENT_M:
        raise ValueError(
            f"bbox largest extent {extent:.6g} m < {MIN_BBOX_EXTENT_M:g} m; "
            "empty or unit-scale error")
    return float(extent)


def envelope_from_bbox_m(
    bbox_m: Sequence[float],
    *,
    source: str,
    design_hash: str,
    mesh_path: str | None = None,
) -> HornEnvelope:
    """Build a :class:`HornEnvelope` from a metre bbox (validated; mm converted)."""
    validate_bbox_m(bbox_m)
    x0, y0, z0, x1, y1, z1 = (float(v) * 1e3 for v in bbox_m)
    digest = C.domain_sha16("system.horn_envelope_bbox_m_v1",
                            {"bbox_m": [round(float(v), 12) for v in bbox_m]})
    return HornEnvelope(
        x_min_mm=x0, x_max_mm=x1, y_min_mm=y0, y_max_mm=y1, z_min_mm=z0, z_max_mm=z1,
        source=str(source), design_hash=str(design_hash), envelope_sha256=digest,
        mesh_path=mesh_path)


def _envelope_from_provenance(path: Path, asset: C.HornAsset) -> HornEnvelope | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, Mapping):
        return None
    if data.get("design_hash_original") != asset.design_hash:
        return None
    full = (data.get("full_vs_quarter_bbox") or {}).get("full_bbox_m")
    if not isinstance(full, (list, tuple)) or len(full) != 6:
        return None
    case_tag = str(data.get("case_tag") or path.parent.name)
    full_mesh = data.get("full_mesh")
    mesh_path = None
    if isinstance(full_mesh, Mapping) and full_mesh.get("path"):
        mesh_path = str(full_mesh["path"])
    return envelope_from_bbox_m(
        [float(v) for v in full], source=f"full_domain_provenance:{case_tag}",
        design_hash=str(data.get("design_hash_full") or asset.design_hash),
        mesh_path=mesh_path)


def derive_horn_envelope(
    asset: C.HornAsset,
    *,
    full_domain_provenance: str | Path | None = None,
    search_root: str | Path | None = None,
) -> HornEnvelope:
    """Derive the real horn outer envelope from the saved full-domain rebuild or stored mesh.

    Preference order (all read-only):

    1. an explicit ``provenance.json`` from :mod:`hornlab_search.system.horn_full_domain`;
    2. the newest sorted matching ``provenance.json`` under the full-domain output root;
    3. the stored quarter ``mesh.msh`` bbox, mirrored about ``x=0``/``y=0``.

    Nothing is invented; a missing mesh/provenance is a hard :class:`DataQualityError`.
    """
    if full_domain_provenance is not None:
        env = _envelope_from_provenance(Path(full_domain_provenance), asset)
        if env is not None:
            return env
        raise C.DataQualityError(
            f"full-domain provenance {full_domain_provenance!r} does not describe asset "
            f"{asset.asset_id!r} (design_hash {asset.design_hash!r}) or lacks full_bbox_m")

    root = Path(search_root) if search_root is not None else None
    if root is None:
        from hornlab_search.system import horn_full_domain

        root = horn_full_domain.default_out_root()
    if root.is_dir():
        for prov in sorted(root.glob("*/provenance.json")):
            env = _envelope_from_provenance(prov, asset)
            if env is not None:
                return env

    if not asset.mesh_path or not Path(asset.mesh_path).is_file():
        raise C.DataQualityError(
            f"asset {asset.asset_id!r}: no full-domain provenance and no stored mesh.msh; "
            "cannot derive the real horn outer envelope (refused, not guessed)")
    from hornlab_search.mesh.build import read_msh_summary

    summary_any: Any = read_msh_summary(Path(asset.mesh_path))
    bbox = [float(v) for v in summary_any["bbox_m"]]
    validate_bbox_m(bbox)
    x_abs = max(abs(bbox[0]), abs(bbox[3]))
    y_abs = max(abs(bbox[1]), abs(bbox[4]))
    full = [-x_abs, -y_abs, bbox[2], x_abs, y_abs, bbox[5]]
    return envelope_from_bbox_m(
        full, source=f"quarter_mesh_mirrored:{asset.design_hash}",
        design_hash=asset.design_hash)


# --------------------------------------------------------------------------- placement


def derive_min_center_spacing_mm(
    envelope: HornEnvelope,
    cabinet: C.BoxPoint,
    *,
    layout: str = "separate_above",
    clearance_mm: float = DEFAULT_CLEARANCE_MM,
    woofer_frame_radius_mm: float | None = None,
    woofer_frame_center_y_mm: float = 0.0,
) -> float:
    """Derived-legal minimum horn/woofer centre spacing [mm] from real geometry.

    This deliberately does **not** use the illustrative ``woofer_center_y_mm_range``.  It uses
    the real horn envelope plus the resolved cabinet frame:

    * ``separate_above``: cabinet top ``H/2`` + horn lower half-extent + clearance;
    * ``separate_side_baffle``: cabinet half-width ``W/2`` + horn left half-extent + clearance;
    * ``flush_baffle``: woofer frame top edge (``cy + r``) + horn lower half-extent + clearance.

    ``woofer_frame_center_y_mm`` is the resolved driver mount height in the cabinet frame
    (millimetres, positive = up).  ``0.0`` is the legacy default; every real caller must pass
    the mount height BL's panel fit accepted.  It only affects ``flush_baffle``: for
    ``separate_above``/``separate_side_baffle`` the cabinet edge governs and a frame poking into
    the overhang is caught by :func:`placement_legality`'s frame check.
    """
    gap = _finite(clearance_mm, "clearance_mm")
    if gap < 0.0:
        raise ValueError(f"clearance_mm must be >= 0, got {clearance_mm!r}")
    if layout == "separate_above":
        value = float(cabinet.external_height_mm) / 2.0 - float(envelope.y_min_mm) + gap
    elif layout == "separate_side_baffle":
        value = float(cabinet.external_width_mm) / 2.0 - float(envelope.x_min_mm) + gap
    elif layout == "flush_baffle":
        if woofer_frame_radius_mm is None:
            raise ValueError(
                "flush_baffle placement needs an explicit woofer_frame_radius_mm; "
                "the frame size is not guessed")
        cy = _finite(woofer_frame_center_y_mm, "woofer_frame_center_y_mm")
        value = cy + float(woofer_frame_radius_mm) - float(envelope.y_min_mm) + gap
    else:
        raise ValueError(f"unknown horn_layout {layout!r}")
    if not (math.isfinite(value) and value > 0.0):
        raise ValueError(f"derived minimum spacing is not positive ({value!r} mm)")
    return float(value)


def _check_mount_offset(value: Any, name: str) -> float:
    x = _finite(value, name)
    if abs(x) > MAX_MOUNT_OFFSET_MM:
        raise ValueError(
            f"unit-scale error: {name}={x:g} mm exceeds the sane cabinet-scale limit "
            f"{MAX_MOUNT_OFFSET_MM:g} mm (metres mistakenly passed as mm?)")
    return x


def mount_transform(
    *,
    dx_mm: float = 0.0,
    dy_mm: float = 0.0,
    dz_mm: float = 0.0,
) -> tuple[tuple[float, float, float, float], ...]:
    """Row-major 4x4 mount transform, metres, identity rotation and zero tilt.

    ``+x`` is a positive horizontal offset, ``+y`` a positive vertical offset and **``+z`` moves
    the horn toward the listener** (away from the baffle), matching the cabinet-front frame in
    ``contracts.AssemblyRanges``.  Offsets are millimetres and are converted to metres here.
    """
    dx = _check_mount_offset(dx_mm, "dx_mm") / 1e3
    dy = _check_mount_offset(dy_mm, "dy_mm") / 1e3
    dz = _check_mount_offset(dz_mm, "dz_mm") / 1e3
    return (
        (1.0, 0.0, 0.0, dx),
        (0.0, 1.0, 0.0, dy),
        (0.0, 0.0, 1.0, dz),
        (0.0, 0.0, 0.0, 1.0),
    )


@dataclass(frozen=True)
class PlacementCheck:
    """Result of one 3-D placement legality/clearance check."""

    accepted: bool
    status: str
    reasons: tuple[str, ...]
    dy_min_mm: float
    transform: tuple[tuple[float, float, float, float], ...]
    horn_bbox_mm: tuple[float, float, float, float, float, float]
    cabinet_bbox_mm: tuple[float, float, float, float, float, float]
    gaps_mm: Mapping[str, float]
    min_clearance_mm: float
    clearance_mm: float
    #: Resolved driver mount height used for the frame solid (cabinet frame, mm, +=up).
    woofer_frame_center_y_mm: float = 0.0
    #: Non-blocking observations (e.g. an AABB overlap that the exact stage check must
    #: resolve). A note never by itself rejects a placement.
    notes: tuple[str, ...] = ()

    @property
    def aabb_overlaps(self) -> bool:
        return all(value < self.clearance_mm - 1e-9 for value in self.gaps_mm.values())

    def to_dict(self) -> dict[str, Any]:
        return _round({
            "accepted": self.accepted,
            "status": self.status,
            "reasons": list(self.reasons),
            "dy_min_mm": self.dy_min_mm,
            "transform": [list(row) for row in self.transform],
            "horn_bbox_mm": list(self.horn_bbox_mm),
            "cabinet_bbox_mm": list(self.cabinet_bbox_mm),
            "gaps_mm": dict(self.gaps_mm),
            "min_clearance_mm": self.min_clearance_mm,
            "clearance_mm": self.clearance_mm,
            "woofer_frame_center_y_mm": self.woofer_frame_center_y_mm,
            "aabb_overlaps": self.aabb_overlaps,
            "notes": list(self.notes),
        })


def _axis_gap(a_min: float, a_max: float, b_min: float, b_max: float) -> float:
    """Signed gap between two 1-D intervals (positive = separated by that distance)."""
    return max(b_min - a_max, a_min - b_max)


def placement_legality(
    envelope: HornEnvelope,
    cabinet: C.BoxPoint,
    *,
    dx_mm: float = 0.0,
    dy_mm: float,
    dz_mm: float = 0.0,
    layout: str = "separate_above",
    clearance_mm: float = DEFAULT_CLEARANCE_MM,
    woofer_frame_radius_mm: float | None = None,
    woofer_rear_depth_mm: float | None = None,
    woofer_frame_center_y_mm: float = 0.0,
    horn_points_mm: "Any" = None,
    placement_policy: str = "envelope_above",
) -> PlacementCheck:
    """Spacing + 3-D AABB collision/clearance check for one mechanical placement.

    A spacing below :func:`derive_min_center_spacing_mm` is a **FAIL** (not widened).  The horn
    envelope is translated by the mount transform; the cabinet occupies
    ``z in [-depth, 0]`` behind the baffle.  A collision requires every axis gap to be below the
    declared clearance.  The woofer frame is included as a bounded volume when its radius is
    supplied, centred on the resolved driver mount height ``woofer_frame_center_y_mm`` in the
    cabinet frame (millimetres, positive = up).  Clearance is inclusive (``>= clearance``).

    ``woofer_frame_center_y_mm`` defaults to ``0.0`` for legacy callers only; every real caller
    must pass the resolved mount height BL's panel fit accepted.
    """
    dx = _check_mount_offset(dx_mm, "dx_mm")
    dy = _check_mount_offset(dy_mm, "dy_mm")
    dz = _check_mount_offset(dz_mm, "dz_mm")
    gap = _finite(clearance_mm, "clearance_mm")
    if gap < 0.0:
        raise ValueError(f"clearance_mm must be >= 0, got {clearance_mm!r}")
    frame_cy = _finite(woofer_frame_center_y_mm, "woofer_frame_center_y_mm")
    notes: list[str] = []
    if placement_policy == "envelope_above":
        dy_min = derive_min_center_spacing_mm(
            envelope, cabinet, layout=layout, clearance_mm=gap,
            woofer_frame_radius_mm=woofer_frame_radius_mm,
            woofer_frame_center_y_mm=frame_cy)
    elif placement_policy == "seated_overhang":
        from hornlab_search.system.assembly_pose import min_legal_dy_mm

        if horn_points_mm is None:
            raise ValueError(
                "placement_policy='seated_overhang' needs the full-domain horn points; "
                "a bbox cannot show that only the throat is over the cabinet top")
        derived = min_legal_dy_mm(
            horn_points_mm, dz_mm=dz, clearance_mm=gap,
            cabinet={"external_width_mm": float(cabinet.external_width_mm),
                     "external_height_mm": float(cabinet.external_height_mm),
                     "external_depth_mm": float(cabinet.external_depth_mm)},
            dx_mm=dx)
        if derived is None:
            dy_min = math.inf
            notes.append(
                f"cantilever: dz={dz:.1f} mm leaves no horn geometry over the cabinet top; "
                "the placement needs an explicit mount, recorded at stage time")
        else:
            dy_min = derived
    else:
        raise ValueError(
            f"placement_policy must be 'envelope_above' or 'seated_overhang', "
            f"got {placement_policy!r}")

    reasons: list[str] = []
    if math.isfinite(dy_min) and dy + 1e-9 < dy_min:
        reasons.append(
            f"illegal spacing: dy={dy:.1f} mm < derived-legal minimum {dy_min:.1f} mm "
            f"(placement_policy={placement_policy}; real horn geometry + cabinet frame + "
            f"{gap:.1f} mm clearance)")

    horn_x0, horn_x1 = dx + envelope.x_min_mm, dx + envelope.x_max_mm
    horn_y0, horn_y1 = dy + envelope.y_min_mm, dy + envelope.y_max_mm
    horn_z0, horn_z1 = dz + envelope.z_min_mm, dz + envelope.z_max_mm
    horn_bbox = (horn_x0, horn_y0, horn_z0, horn_x1, horn_y1, horn_z1)

    w = float(cabinet.external_width_mm)
    h = float(cabinet.external_height_mm)
    d = float(cabinet.external_depth_mm)
    cab_bbox = (-w / 2.0, -h / 2.0, -d, w / 2.0, h / 2.0, 0.0)

    gaps = {
        "x": _axis_gap(horn_x0, horn_x1, cab_bbox[0], cab_bbox[3]),
        "y": _axis_gap(horn_y0, horn_y1, cab_bbox[1], cab_bbox[4]),
        "z": _axis_gap(horn_z0, horn_z1, cab_bbox[2], cab_bbox[5]),
    }
    if all(value < gap - 1e-9 for value in gaps.values()):
        message = (
            "3-D AABB overlap on every axis without the required "
            f"{gap:.1f} mm clearance (gaps x={gaps['x']:.1f}, y={gaps['y']:.1f}, "
            f"z={gaps['z']:.1f} mm)")
        if placement_policy == "seated_overhang":
            # Broad phase only: a mouth hanging in front of the baffle overlaps the box
            # silhouette while the solids stay apart. The exact triangle-vs-cabinet check
            # runs at stage time and is the only collision authority.
            notes.append("AABB broad-phase overlap; exact horn-vs-cabinet clearance is "
                         "required at stage time: " + message)
        else:
            reasons.append("3-D collision: horn and cabinet " + message)

    min_clearance = min(gaps.values())
    if woofer_frame_radius_mm is not None:
        radius = _finite(woofer_frame_radius_mm, "woofer_frame_radius_mm")
        rear = 0.0 if woofer_rear_depth_mm is None else _finite(
            woofer_rear_depth_mm, "woofer_rear_depth_mm")
        # The frame sits on the baffle at the driver's mounted height, not at y=0.  0.0 is the
        # legacy default; every real caller passes the resolved mount height.
        frame_bbox = (-radius, frame_cy - radius, -rear, radius, frame_cy + radius, 0.0)
        # AABB separation needs ONE axis with the required gap; the best axis is the maximum
        # signed gap (a deeply overlapping axis is not a collision if another axis separates).
        frame_gap = max(
            _axis_gap(horn_x0, horn_x1, frame_bbox[0], frame_bbox[3]),
            _axis_gap(horn_y0, horn_y1, frame_bbox[1], frame_bbox[4]),
            _axis_gap(horn_z0, horn_z1, frame_bbox[2], frame_bbox[5]),
        )
        gaps["woofer_frame"] = float(frame_gap)
        min_clearance = min(min_clearance, frame_gap)
        if frame_gap < gap - 1e-9:
            reasons.append(
                f"woofer frame clearance {frame_gap:.1f} mm < required {gap:.1f} mm")

    accepted = not reasons
    return PlacementCheck(
        accepted=accepted, status="PASS" if accepted else "FAIL",
        reasons=tuple(reasons), dy_min_mm=dy_min,
        transform=mount_transform(dx_mm=dx, dy_mm=dy, dz_mm=dz),
        horn_bbox_mm=horn_bbox, cabinet_bbox_mm=cab_bbox, gaps_mm=gaps,
        min_clearance_mm=float(min_clearance), clearance_mm=float(gap),
        woofer_frame_center_y_mm=float(frame_cy),
        notes=tuple(notes))


# --------------------------------------------------------------------------- driver catalog


@dataclass(frozen=True)
class DriverEntry:
    """One sourced driver plus its input-file provenance (never a guessed field)."""

    driver_id: str
    driver: C.WooferDriver
    ts_file: str | None
    geometry_file: str | None
    ts_sha256: str | None
    geometry_sha256: str | None
    missing_geometry_fields: tuple[str, ...]
    present_geometry_fields: tuple[str, ...]
    source_urls: tuple[str, ...]

    @property
    def cone(self) -> ConeDriver:
        return self.driver.cone

    def to_summary(self) -> dict[str, Any]:
        geometry = self.driver.geometry_mm
        return _round({
            "driver_id": self.driver_id,
            "name": self.cone.name,
            "ts_file": self.ts_file,
            "geometry_file": self.geometry_file,
            "ts_sha256": self.ts_sha256,
            "geometry_sha256": self.geometry_sha256,
            "source_urls": list(self.source_urls),
            "missing_geometry_fields": list(self.missing_geometry_fields),
            "present_geometry_fields": list(self.present_geometry_fields),
            "data_quality": dict(self.driver.data_quality),
            "sd_cm2": self.cone.sd_cm2,
            "effective_piston_radius_m": math.sqrt(self.cone.sd_m2 / math.pi),
            "fs_hz": self.cone.fs_hz,
            "re_ohm": self.cone.re_ohm,
            "p_aes_w": self.cone.p_aes_w,
            "xmax_mm": self.cone.xmax_mm,
            "depth_mm": None if geometry is None else geometry.depth_mm,
            "mounting_depth_behind_baffle_mm": (
                None if geometry is None else geometry.mounting_depth_behind_baffle_mm),
        })


@dataclass(frozen=True)
class CatalogResult:
    """Catalog load result: kept entries plus visible per-driver rejections."""

    entries: tuple[DriverEntry, ...]
    rejected: tuple[dict[str, Any], ...]


def load_driver_catalog(
    stems: Sequence[str] | None = None,
    *,
    ts_dir: str | Path | None = None,
    geometry_dir: str | Path | None = None,
) -> CatalogResult:
    """Load the sourced system driver catalog, recording missing files/fields honestly.

    T/S are read by the frozen :func:`hornlab_search.meh.drivers.load_cone`; geometry uses the
    additive system schema.  A missing geometry document is **not** an error for LF screening,
    but its missing fields are recorded and installed-tier claims stay refused.
    """
    ts_root = Path(ts_dir) if ts_dir is not None else DEFAULT_TS_DIR
    geom_root = Path(geometry_dir) if geometry_dir is not None else DEFAULT_GEOMETRY_DIR
    wanted = tuple(stems) if stems is not None else DEFAULT_DRIVER_STEMS
    entries: list[DriverEntry] = []
    rejected: list[dict[str, Any]] = []
    for stem in wanted:
        ts_path = ts_root / f"{stem}.yaml"
        if not ts_path.is_file():
            rejected.append({"driver_id": stem, "stage": "driver_catalog",
                             "reason": f"T/S file not found: {ts_path.name}"})
            continue
        try:
            cone = load_cone(stem, directory=ts_root)
        except Exception as exc:  # noqa: BLE001 - a bad source file is a visible rejection
            rejected.append({"driver_id": stem, "stage": "driver_catalog",
                             "reason": f"T/S load failed: {exc}"})
            continue
        geom_path = geom_root / f"{stem}.yaml"
        doc = None
        if geom_path.is_file():
            try:
                doc = sys_drivers.load_driver_geometry(geom_path)
            except Exception as exc:  # noqa: BLE001
                rejected.append({"driver_id": stem, "stage": "driver_geometry",
                                 "reason": f"geometry load failed: {exc}"})
                continue
        geometry = None if doc is None else doc.geometry
        present = () if doc is None else doc.present_fields
        missing = sys_drivers.missing_installed_fields(present)
        completeness = sys_drivers.geometry_completeness(present)
        data_quality = {
            "ts_source_present": bool(cone.source),
            "geometry_present": geometry is not None,
            "has_full_geometry": bool(completeness["INSTALLED_EXTERIOR_BEM"]),
            "supports_lf_ts_screening": True,
            "supports_installed_exterior_bem": bool(completeness["INSTALLED_EXTERIOR_BEM"]),
            "missing_geometry_fields": list(missing),
        }
        sources: list[str] = []
        if cone.source:
            sources.append(str(cone.source))
        if doc is not None:
            sources.extend(doc.sourced_from)
        try:
            driver = C.WooferDriver(
                driver_id=stem, cone=cone, geometry_mm=geometry,
                provenance={"ts_file": ts_path.name, "geometry_file": (
                    None if doc is None else geom_path.name),
                    "source_urls": tuple(sources),
                    "missing_geometry_fields": list(missing)},
                data_quality=data_quality)
        except C.DataQualityError as exc:
            rejected.append({"driver_id": stem, "stage": "driver_catalog",
                             "reason": str(exc)})
            continue
        entries.append(DriverEntry(
            driver_id=stem, driver=driver, ts_file=ts_path.name,
            geometry_file=(None if doc is None else geom_path.name),
            ts_sha256=provenance.file_sha256(ts_path),
            geometry_sha256=(None if doc is None else provenance.file_sha256(geom_path)),
            missing_geometry_fields=tuple(missing),
            present_geometry_fields=tuple(present),
            source_urls=tuple(dict.fromkeys(sources))))
    return CatalogResult(entries=tuple(entries), rejected=tuple(rejected))


# --------------------------------------------------------------------------- box + candidates


def evaluate_box(
    driver: C.WooferDriver,
    point: C.BoxPoint,
    *,
    f3_target_hz: float | None,
    min_wall_mm: float = fit_rules.DEFAULT_MIN_WALL_MM,
    brace_clearance_mm: float = fit_rules.DEFAULT_BRACE_CLEARANCE_MM,
) -> dict[str, Any]:
    """Evaluate one resolved box through the fixed bassbox + fabrication rules.

    A missing driver geometry field is recorded (``None``) and never guessed; the box can still
    pass a T/S + port + wall screen, but installed-boundary claims remain refused.
    """
    lf = bass_reference.lf_report_row(point, driver.cone)
    geometry = driver.geometry_mm
    statuses = {
        "port": fit_rules.check_port_fits(point, geometry),
        "driver_and_brace": fit_rules.check_driver_and_brace_clearance(
            point, geometry, brace_clearance_mm=brace_clearance_mm),
        "wall": fit_rules.check_wall_thickness(point, geometry, min_wall_mm=min_wall_mm),
    }
    fails = [f"{name}: {text}" for name, text in statuses.items() if text.startswith("FAIL")]
    skips = [f"{name}: {text}" for name, text in statuses.items() if text.startswith("skip")]
    f3 = float(lf["f3_hz"])
    target_f3 = None if f3_target_hz is None else float(f3_target_hz)
    f3_ok = (target_f3 is None) or (math.isfinite(f3) and f3 <= target_f3)
    port_velocity_fits = bool(point.fits.get("port_velocity_fits", True))
    if not f3_ok:
        assert target_f3 is not None
        fails.append(f"f3 {f3:.3f} Hz > target {target_f3:.3f} Hz")
    # Port velocity at the AES-voltage ceiling is a HEADROOM axis, not a construction gate:
    # the geometric port-fit rule above is the buildability gate.  The flag is still reported.
    present = () if geometry is None else tuple(
        f for f in sys_drivers.GEOMETRY_FIELDS if getattr(geometry, f) is not None)
    missing = sys_drivers.missing_installed_fields(present)
    rear_depth = (None if geometry is None else (
        geometry.mounting_depth_behind_baffle_mm
        if geometry.mounting_depth_behind_baffle_mm is not None else geometry.depth_mm))
    feasible = not fails
    return _round({
        "feasible": bool(feasible),
        "status": "PASS" if feasible else "FAIL",
        "reasons": fails,
        "skips": skips,
        "statuses": statuses,
        "lf": {
            "f3_hz": f3,
            "f3_target_hz": None if f3_target_hz is None else float(f3_target_hz),
            "f3_ok": bool(f3_ok),
            "port_velocity_mps_40hz": lf["port_velocity_mps_40hz"],
            "port_velocity_mps_63hz": lf["port_velocity_mps_63hz"],
            "excursion_margin_db": point.fits.get("excursion_margin_db"),
            "spl_max_40hz_db": lf["spl_max_40hz_db"],
            "spl_max_63_120hz_min_db": lf["spl_max_63_120hz_min_db"],
            "limiting_40hz": lf["limiting_40hz"],
            "limiting_63_120hz": lf["limiting_63_120hz"],
            "nfr_ignored_at_lf_tier": True,
        },
        "driver_geometry": {
            "present_fields": list(present),
            "missing_fields": list(missing),
            "mounting_depth_behind_baffle_mm": (
                None if geometry is None else geometry.mounting_depth_behind_baffle_mm),
            "rear_depth_mm_used": rear_depth,
            "installed_claims_allowed": not missing,
            "note": ("missing geometry fields are recorded as None, never guessed; "
                     "T/S-only screening remains allowed"),
        },
        "port_velocity_fits": port_velocity_fits,
        "f3_ok": bool(f3_ok),
    })


# --------------------------------------------------------------------------- BL panel fit
#
# Read-only reference: Boundary Lab's vented-enclosure generator validator,
# ``boundary-lab/geometry_providers/vented_enclosure/enclosure/parameters.py``
# (``::validate``, lines 100-109; BL git head 15f9a89245a9adfec8c2f0006c164953ce381e58,
# parameters.py sha256 51f8e82071ce9984ff651d1266a208d2ba51ff0e9df2fcb2edd22ff3cc0d78c5 as
# recorded in
# ``system_runs/system/bl_r4_tower_box/20261119T001041Z-ref_case-40216-b32bb5a2/manifest.json``).
# Nothing here imports or calls BL.
#
# BL's defaults (``FIELDS`` lines 14-26 and ``DEFAULTS`` line 33) and the hard-coded 3 mm
# ``clearance`` (line 100) are reproduced verbatim as recorded constants:
BL_DEMO_DRIVER_MOVING_DIAMETER_M: float = 0.200   # driver_diameter_m
BL_DEMO_DRIVER_Y_M: float = 0.100                 # driver_y_m
BL_DEMO_PORT_Y_M: float = -0.130                  # port_y_m
BL_DEMO_PORT_WALL_M: float = 0.003                # port_wall_m
BL_DEMO_PORT_ROUNDOVER_M: float = 0.008           # port_roundover_m
BL_DEMO_CONE_DEPTH_M: float = 0.040               # cone_depth_m
BL_VALIDATE_CLEARANCE_M: float = 0.003            # local ``clearance`` in validate()

BL_PANEL_FIT_DRIVER_WALL = "BL_PANEL_FIT_DRIVER_WALL"
BL_PANEL_FIT_PORT_WALL = "BL_PANEL_FIT_PORT_WALL"
BL_PANEL_FIT_DRIVER_PORT_SEPARATION = "BL_PANEL_FIT_DRIVER_PORT_SEPARATION"
BL_PANEL_FIT_PORT_REAR_WALL = "BL_PANEL_FIT_PORT_REAR_WALL"
BL_PANEL_FIT_CONE_REAR_WALL = "BL_PANEL_FIT_CONE_REAR_WALL"
BL_PANEL_FIT_PORT_LENGTH_UNAVAILABLE = "BL_PANEL_FIT_PORT_LENGTH_UNAVAILABLE"
BL_PANEL_FIT_PORT_AREA_INVALID = "BL_PANEL_FIT_PORT_AREA_INVALID"


def bl_panel_fit_feasible(
    box: C.BoxPoint,
    *,
    driver_moving_diameter_m: float = BL_DEMO_DRIVER_MOVING_DIAMETER_M,
    driver_y_m: float = BL_DEMO_DRIVER_Y_M,
    port_y_m: float = BL_DEMO_PORT_Y_M,
    port_wall_m: float = BL_DEMO_PORT_WALL_M,
    port_roundover_m: float = BL_DEMO_PORT_ROUNDOVER_M,
    cone_depth_m: float = BL_DEMO_CONE_DEPTH_M,
    clearance_m: float = BL_VALIDATE_CLEARANCE_M,
) -> tuple[bool, str | None]:
    """Mirror BL's vented-enclosure panel-fit validator on a resolved :class:`BoxPoint`.

    This is the CPU, solver-free twin of ``parameters.py::validate`` (lines 100-109) for the
    front-panel geometry BL compiles.  Along the panel, ``w`` is the external width, ``h`` the
    external height and ``y`` the vertical coordinate (BL's ``driver_y_m``/``port_y_m``), with
    ``t = box.wall_mm``:

    * each component must satisfy ``radius + clearance < w/2 - t`` **and**
      ``abs(y) + radius + clearance < h/2 - t`` (BL raises on ``>=``);
    * ``abs(driver_y - port_y) > driver_radius + port_outer + clearance`` (strict ``>``);
    * ``length <= t + lip + clearance`` or ``length + 2 * mouth >= d - t`` is the rear-wall
      refusal, where ``length`` is the total port length including both lips and, for ``nfr = 0``
      (the LF-tier convention), ``mouth = sqrt(port_area/pi) + lip``;
    * ``cone_depth + clearance >= d - t`` is the cone/rear-wall refusal.

    ``port_outer = mouth + port_wall_m``.  Defaults are BL's own plugin defaults, recorded above
    from the same source; they are the values the parent's staging run fed to BL.

    The returned string is one of the ``BL_PANEL_FIT_*`` tokens (or ``None`` on success).
    A panel that cannot host the two components with the required strict separation at *any*
    legal ``y`` is refused with :data:`BL_PANEL_FIT_DRIVER_PORT_SEPARATION`; that is the root
    cause the parent's R4 staging hit (the recorded 371.2 mm panel), even when the supplied
    demo ``y`` offsets trip BL's wall check first.  The function is pure and deterministic.
    """
    g = _panel_fit_geometry(
        box, driver_moving_diameter_m=driver_moving_diameter_m, driver_y_m=driver_y_m,
        port_y_m=port_y_m, port_wall_m=port_wall_m, port_roundover_m=port_roundover_m,
        cone_depth_m=cone_depth_m, clearance_m=clearance_m)
    if not (g["area_m2"] > 0.0):
        return False, BL_PANEL_FIT_PORT_AREA_INVALID
    try:
        neck_m = bass_reference.port_neck_length_mm(box) * 1e-3
    except ValueError:
        return False, BL_PANEL_FIT_PORT_LENGTH_UNAVAILABLE
    # BL's ``port_length_m`` is the total length incl. lips; the contract carries the derived
    # effective length, whose fixed-bassbox inversion (port_neck_length_mm) gives the neck.
    length_m = neck_m + 2.0 * float(g["lip_m"])
    return _panel_fit_rules(g, driver_y_m=g["driver_y_m"], port_y_m=g["port_y_m"],
                            port_length_m=length_m)


def _panel_fit_geometry(
    box: C.BoxPoint,
    *,
    driver_moving_diameter_m: float,
    driver_y_m: float | None,
    port_y_m: float | None,
    port_wall_m: float,
    port_roundover_m: float,
    cone_depth_m: float,
    clearance_m: float,
    allow_auto_y: bool = False,
) -> dict[str, Any]:
    """Validated front-baffle geometry, in metres, shared by both public panel-fit entries.

    One source of arithmetic: :func:`bl_panel_fit_feasible` and
    :func:`bl_panel_fit_separation` both build their verdict from this dict, so the numbers
    cannot drift.  ``driver_y_m``/``port_y_m`` may be ``None`` (placement not supplied); the
    caller resolves them with :func:`_max_legal_panel_y`.
    """
    w = _finite(box.external_width_mm, "external_width_mm") * 1e-3
    h = _finite(box.external_height_mm, "external_height_mm") * 1e-3
    d = _finite(box.external_depth_mm, "external_depth_mm") * 1e-3
    t = _finite(box.wall_mm, "wall_mm") * 1e-3
    if not (w > 0.0 and h > 0.0 and d > 0.0):
        raise ValueError("box external dimensions must be > 0")
    if t < 0.0:
        raise ValueError(f"wall_mm must be >= 0, got {box.wall_mm!r}")
    driver_r = _finite(driver_moving_diameter_m, "driver_moving_diameter_m") / 2.0
    if allow_auto_y:
        dy = None if driver_y_m is None else _finite(driver_y_m, "driver_y_m")
        py = None if port_y_m is None else _finite(port_y_m, "port_y_m")
    else:
        # The boolean gate always needs a concrete placement (its behaviour is frozen).
        dy = _finite(driver_y_m, "driver_y_m")
        py = _finite(port_y_m, "port_y_m")
    lip = _finite(port_roundover_m, "port_roundover_m")
    wall = _finite(port_wall_m, "port_wall_m")
    cone_depth = _finite(cone_depth_m, "cone_depth_m")
    clearance = _finite(clearance_m, "clearance_m")
    for name, value in (("driver_moving_diameter_m", driver_moving_diameter_m),
                        ("port_wall_m", port_wall_m), ("port_roundover_m", port_roundover_m),
                        ("cone_depth_m", cone_depth_m), ("clearance_m", clearance_m)):
        if float(value) < 0.0:
            raise ValueError(f"{name} must be >= 0, got {value!r}")
    area_m2 = _finite(box.port_throat_area_cm2, "port_throat_area_cm2") * 1e-4

    # nfr = 0 (straight) port profile: mouth radius = throat radius + lip roundover.
    throat = math.sqrt(area_m2 / math.pi) if area_m2 > 0.0 else float("nan")
    mouth = throat + lip
    port_outer = mouth + wall
    half_w = w / 2.0 - t
    half_h = h / 2.0 - t
    required_sep = driver_r + port_outer + clearance
    driver_budget = half_h - driver_r - clearance
    port_budget = half_h - port_outer - clearance
    return {
        "width_m": w, "height_m": h, "depth_m": d, "wall_m": t,
        "driver_r_m": driver_r, "driver_y_m": dy, "port_y_m": py,
        "lip_m": lip, "port_wall_m": wall, "cone_depth_m": cone_depth,
        "clearance_m": clearance, "area_m2": area_m2, "throat_m": throat,
        "mouth_m": mouth, "port_outer_m": port_outer,
        "half_width_m": half_w, "half_height_m": half_h,
        # Required driver/port centre separation vs the panel's own budget for it.
        "required_m": required_sep,
        "driver_budget_m": driver_budget, "port_budget_m": port_budget,
        "available_m": driver_budget + port_budget,
    }


def _max_legal_panel_y(g: Mapping[str, Any]) -> tuple[float, float]:
    """Each component at its own maximum legal ``|y|`` (the screen's placement convention)."""
    half_h = float(g["half_height_m"])
    eps = 1e-12  # stay strictly inside BL's ``>=`` wall refusal
    driver_y = max(0.0, half_h - float(g["driver_r_m"]) - float(g["clearance_m"]) - eps)
    port_y = -max(0.0, half_h - float(g["port_outer_m"]) - float(g["clearance_m"]) - eps)
    return float(driver_y), float(port_y)


def _panel_fit_rules(
    g: Mapping[str, Any],
    *,
    driver_y_m: float | None,
    port_y_m: float | None,
    port_length_m: float | None,
) -> tuple[bool, str | None]:
    """BL's panel rules on the geometry dict; ``port_length_m=None`` skips only the two
    length-dependent rear-wall rules (reported as ``PORT_LENGTH_UNAVAILABLE``)."""
    required_sep = float(g["required_m"])
    driver_r = float(g["driver_r_m"])
    port_outer = float(g["port_outer_m"])
    clearance = float(g["clearance_m"])
    half_w = float(g["half_width_m"])
    half_h = float(g["half_height_m"])
    t = float(g["wall_m"])
    lip = float(g["lip_m"])
    d = float(g["depth_m"])

    if not (float(g["area_m2"]) > 0.0):
        return False, BL_PANEL_FIT_PORT_AREA_INVALID

    # BL's rules, plus one screen-level consequence: if no y pair can satisfy the two fit
    # checks and the strict separation on this panel, the panel itself is infeasible and the
    # binding cause is the separation budget (the recorded refusal).  This never accepts a box
    # BL would refuse; it only labels the reason.
    if (float(g["driver_budget_m"]) + float(g["port_budget_m"])) <= required_sep:
        return False, BL_PANEL_FIT_DRIVER_PORT_SEPARATION

    dy = 0.0 if driver_y_m is None else float(driver_y_m)
    py = 0.0 if port_y_m is None else float(port_y_m)
    if driver_r + clearance >= half_w or abs(dy) + driver_r + clearance >= half_h:
        return False, BL_PANEL_FIT_DRIVER_WALL
    if port_outer + clearance >= half_w or abs(py) + port_outer + clearance >= half_h:
        return False, BL_PANEL_FIT_PORT_WALL
    if abs(dy - py) <= required_sep:
        return False, BL_PANEL_FIT_DRIVER_PORT_SEPARATION
    if port_length_m is None:
        # The front panel itself accepts the driver + port; the port's rear-wall clearance
        # cannot be judged without a derived effective length.  Refused, never assumed.
        return False, BL_PANEL_FIT_PORT_LENGTH_UNAVAILABLE
    if port_length_m <= t + lip + clearance or port_length_m + 2.0 * float(g["mouth_m"]) >= d - t:
        return False, BL_PANEL_FIT_PORT_REAR_WALL
    if float(g["cone_depth_m"]) + clearance >= d - t:
        return False, BL_PANEL_FIT_CONE_REAR_WALL
    return True, None


def bl_panel_fit_separation(
    box: C.BoxPoint,
    *,
    driver_moving_diameter_m: float = BL_DEMO_DRIVER_MOVING_DIAMETER_M,
    driver_y_m: float | None = None,
    port_y_m: float | None = None,
    port_wall_m: float = BL_DEMO_PORT_WALL_M,
    port_roundover_m: float = BL_DEMO_PORT_ROUNDOVER_M,
    cone_depth_m: float = BL_DEMO_CONE_DEPTH_M,
    clearance_m: float = BL_VALIDATE_CLEARANCE_M,
) -> dict[str, Any]:
    """:func:`bl_panel_fit_feasible` plus the separation numbers behind its verdict.

    Same arithmetic, same tokens, same defaults as the boolean entry point; only the output
    shape differs, so the GUI can show *why* a panel is refused beside the drawing:

    * ``required_m`` -- the centre separation BL demands: driver radius + port outer radius +
      clearance (``abs(driver_y - port_y) > required_m``);
    * ``available_m`` -- the panel's own budget for it: the driver's and the port's maximum
      legal ``|y|`` travel added together (``driver_budget + port_budget``);
    * ``driver_y_m``/``port_y_m`` -- the offsets actually checked.  ``None`` places each
      component at its own maximum legal ``|y|`` first, exactly as the screen does;
    * ``port_length_m``/``port_length_checked`` -- the total port length the rear-wall rule
      used, and whether the box carried a derived length to check at all.

    When ``required_m > available_m`` no legal placement exists and the verdict is
    :data:`BL_PANEL_FIT_DRIVER_PORT_SEPARATION`; the pair is reported even when another rule
    (e.g. the per-component wall check) would have fired first.  Pure and deterministic.
    """
    g = _panel_fit_geometry(
        box, driver_moving_diameter_m=driver_moving_diameter_m, driver_y_m=driver_y_m,
        port_y_m=port_y_m, port_wall_m=port_wall_m, port_roundover_m=port_roundover_m,
        cone_depth_m=cone_depth_m, clearance_m=clearance_m, allow_auto_y=True)
    auto_driver_y, auto_port_y = _max_legal_panel_y(g)
    dy = auto_driver_y if g["driver_y_m"] is None else float(g["driver_y_m"])
    py = auto_port_y if g["port_y_m"] is None else float(g["port_y_m"])
    length_m: float | None = None
    if float(g["area_m2"]) > 0.0:
        try:
            length_m = bass_reference.port_neck_length_mm(box) * 1e-3 + 2.0 * float(g["lip_m"])
        except ValueError:
            length_m = None
    ok, reason = _panel_fit_rules(g, driver_y_m=dy, port_y_m=py, port_length_m=length_m)
    return {
        "feasible": bool(ok),
        "reason": reason,
        "required_m": float(g["required_m"]),
        "available_m": float(g["available_m"]),
        "driver_y_m": dy,
        "port_y_m": py,
        "port_length_m": None if length_m is None else float(length_m),
        "port_length_checked": length_m is not None,
    }


def _bl_panel_fit_for_screen(point: C.BoxPoint) -> dict[str, Any]:
    """Panel-fit check for the screen, using the widest legal ``y`` placement on the panel.

    The screen does not carry BL's ``driver_y``/``port_y`` fields, so it asks the honest
    feasibility question -- can this panel host the driver and port at all? -- by placing each
    component at its own maximum legal ``|y|`` and then running the exact BL validator.  A box
    that fails is refused with the returned token; the derived offsets are reported so the
    refusal is inspectable.
    """
    sep = bl_panel_fit_separation(point)
    return {
        "accepted": bool(sep["feasible"]),
        "reason": sep["reason"],
        "driver_y_m": float(sep["driver_y_m"]),
        "port_y_m": float(sep["port_y_m"]),
    }


def select_box_sample(boxes: Sequence[C.BoxPoint], limit: int) -> tuple[C.BoxPoint, ...]:
    """Deterministic extreme+corners sample: smallest/largest volume at low/high tuning.

    With ``limit >= 4`` this keeps the LF-extension/port-velocity trade-off visible: the
    smallest and largest feasible net volumes, each at its lowest and highest feasible tuning.
    It never ranks by an acoustic score.  Smaller limits fall back to a volume-spread sample.
    """
    ordered = sorted(boxes, key=lambda b: (
        float(b.net_volume_l), float(b.derived_tuning_hz or b.requested_tuning_hz),
        float(b.port_throat_area_cm2)))
    n = max(1, int(limit))
    if len(ordered) <= n:
        return tuple(ordered)
    if n >= 4:
        volumes = sorted({float(b.net_volume_l) for b in ordered})
        levels = max(2, n // 2)
        if len(volumes) > levels:
            raw = [int(round(i * (len(volumes) - 1) / (levels - 1))) for i in range(levels)]
            chosen_volumes = [volumes[i] for i in sorted(set(raw))]
        else:
            chosen_volumes = volumes
        picks: list[C.BoxPoint] = []
        for volume in chosen_volumes:
            group = [b for b in ordered if float(b.net_volume_l) == volume]
            for candidate in (group[0], group[-1]):
                if all(candidate is not existing for existing in picks):
                    picks.append(candidate)
        if len(picks) >= n:
            return tuple(picks[:n])
        if picks:
            return tuple(picks)
    half = n // 2
    return tuple(ordered[:half] + ordered[-(n - half):])


def _candidate_id(asset_id: str, driver_id: str, point: C.BoxPoint,
                  xo_hz: float, dz_mm: float) -> str:
    return C.domain_sha16("system.woofer_seed_candidate_v1", {
        "asset_id": asset_id, "driver_id": driver_id,
        "net_volume_l": float(point.net_volume_l),
        "tuning_hz": float(point.derived_tuning_hz or point.requested_tuning_hz),
        "port_area_cm2": float(point.port_throat_area_cm2),
        "external_mm": [float(point.external_width_mm), float(point.external_height_mm),
                        float(point.external_depth_mm)],
        "xo_hz": float(xo_hz), "dz_mm": float(dz_mm),
    })


@dataclass
class SeedResult:
    """Deterministic seed-screen result (JSON/Markdown byte-stable for identical inputs)."""

    asset_summary: Mapping[str, Any]
    envelope: HornEnvelope
    catalog_summary: tuple[dict[str, Any], ...]
    catalog_rejected: tuple[dict[str, Any], ...]
    fingerprint_summary: Mapping[str, Any]
    metric_spec: Mapping[str, Any]
    xo_screens: Mapping[str, Any]
    counts: Mapping[str, int]
    kept_rows: tuple[dict[str, Any], ...]
    shortlist: tuple[dict[str, Any], ...]
    rejected_ledger: tuple[dict[str, Any], ...]
    input_sha256: Mapping[str, Any]
    study_id: str

    def to_payload(self) -> dict[str, Any]:
        return _round({
            "schema": SEED_SCHEMA,
            "study_id": self.study_id,
            "system_objective_version": C.SYSTEM_OBJECTIVE_VERSION,
            "input_sha256": dict(self.input_sha256),
            "asset": dict(self.asset_summary),
            "envelope": self.envelope.to_dict(),
            "catalog": list(self.catalog_summary),
            "catalog_rejected": list(self.catalog_rejected),
            "fingerprints": dict(self.fingerprint_summary),
            "metric_spec": dict(self.metric_spec),
            "counts": dict(self.counts),
            "xo_screens": dict(self.xo_screens),
            "kept_rows": list(self.kept_rows),
            "shortlist": list(self.shortlist),
            "rejected_ledger": list(self.rejected_ledger),
            "claim": ("heuristic fixed-horn screen; no scalar winner; not a validated ranking. "
                      "Phase/delay optimisation is refused for magnitude-only assets."),
        })

    def to_json(self) -> str:
        return json.dumps(self.to_payload(), indent=2, sort_keys=True,
                          ensure_ascii=False) + "\n"

    def to_markdown(self) -> str:
        c = self.counts
        lines = [
            "# Woofer/cabinet/XO/placement seed shortlist (heuristic screen)",
            "",
            f"schema: `{SEED_SCHEMA}`",
            f"study_id: `{self.study_id}`",
            f"asset: `{self.asset_summary.get('asset_id')}` "
            f"(design `{self.asset_summary.get('design_hash')}`, "
            f"quality `{self.asset_summary.get('quality')}`)",
            f"horn envelope: `{self.envelope.source}` "
            f"({self.envelope.width_mm:.1f} x {self.envelope.height_mm:.1f} x "
            f"{self.envelope.depth_mm:.1f} mm)",
            "",
            "## Counts",
            "",
            "| stage | count |",
            "|---|---|",
        ]
        for key in sorted(c):
            lines.append(f"| {key} | {c[key]} |")
        lines.extend([
            "",
            "## Metric specification",
            "",
            f"- overlap: +/-{float(self.metric_spec.get('half_octaves', 0)):.6f} octave around each "
            "candidate f_x (stored samples only, no interpolation)",
            f"- min band samples: {self.metric_spec.get('min_freqs')} frequencies / "
            f"{self.metric_spec.get('min_dirs')} directions",
            f"- weights: uniform f and direction weights; reporting floor "
            f"{self.metric_spec.get('floor_db')} dB; deep-null flag "
            f"{self.metric_spec.get('null_flag_db')} dB",
            f"- good-match label threshold: {self.metric_spec.get('good_match_db2')} dB^2 "
            "(provisional; 3 dB RMS)",
            "- planes: H and V evaluated separately; listening front region only; "
            "no back-hemisphere comparison",
            "- no dB power averaging; squared dB differences are averaged",
            "",
            "## Pareto shortlist (no single winner)",
            "",
            "| candidate | driver | box L | f3 Hz | xo Hz | dy mm | dz mm | E_H dB^2 | E_V dB^2 | "
            "port v/limit | footprint m^2 |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ])
        for row in self.shortlist:
            box = row["box"]
            axes = row["numeric_axes"]
            planes = row["match"]
            lines.append(
                f"| {row['candidate_id']} | {row['driver_id']} | "
                f"{box['net_volume_l']:.1f} | {axes['lf_f3_hz']:.2f} | {row['xo_hz']:.2f} | "
                f"{row['placement']['dy_mm']:.1f} | {row['placement']['dz_mm']:.1f} | "
                f"{planes['H']['e_shape_db2']:.3f} | {planes['V']['e_shape_db2']:.3f} | "
                f"{axes['port_velocity_ratio']:.3f} | {axes['cabinet_footprint_m2']:.4f} |")
        lines.extend([
            "",
            "**The shortlist is a heuristic screen, not a validated ranking.** It is not a "
            "Boundary Lab result and must be validated before any build/claim.",
            "",
        ])
        return "\n".join(lines)

    def write(self, out_dir: str | Path) -> tuple[Path, Path]:
        root = Path(out_dir)
        root.mkdir(parents=True, exist_ok=True)
        json_path = root / "woofer_seed.json"
        md_path = root / "woofer_seed.md"
        json_path.write_text(self.to_json(), encoding="utf-8")
        md_path.write_text(self.to_markdown(), encoding="utf-8")
        return json_path, md_path


def _nondominated(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    from hornlab_search.system import score

    # O(n^2) by design: the screen's kept set is bounded (<= ~126 rows on the recorded
    # studies). A dominance tree/sort is only worth the extra semantics risk if that breadth
    # grows by an order of magnitude; the front set is what callers consume.
    directions = dict(SEED_AXIS_DIRECTIONS)
    front: list[dict[str, Any]] = []
    for row in rows:
        dominated = False
        for other in rows:
            if other is row:
                continue
            if score.dominates(other, row, directions):
                dominated = True
                break
        if not dominated:
            front.append(row)
    return front


def _select_diverse(front: Sequence[dict[str, Any]], size: int) -> list[dict[str, Any]]:
    if len(front) <= size:
        return sorted(front, key=lambda r: str(r["candidate_id"]))
    chosen: dict[str, dict[str, Any]] = {}

    def add(row: dict[str, Any], reason: str) -> None:
        cid = str(row["candidate_id"])
        if cid not in chosen and len(chosen) < size:
            item = dict(row)
            item["shortlist_reason"] = reason
            chosen[cid] = item

    # One representative per driver first: the shortlist must not be a single-driver display.
    for driver in sorted({str(r["driver_id"]) for r in front}):
        group = [r for r in front if str(r["driver_id"]) == driver]
        best = min(group, key=lambda r: (
            max(float(r["numeric_axes"]["match_error_h_db2"]),
                float(r["numeric_axes"]["match_error_v_db2"])),
            float(r["numeric_axes"]["lf_f3_hz"]), str(r["candidate_id"])))
        add(best, f"driver_best:{driver}")
    for axis in sorted(SEED_AXIS_DIRECTIONS):
        direction = SEED_AXIS_DIRECTIONS[axis]
        sign = -1.0 if direction == "+" else 1.0
        best = min(front, key=lambda r: (
            sign * float(r["numeric_axes"][axis]), str(r["candidate_id"])))
        add(best, f"axis_best:{axis}")
    for row in sorted(front, key=lambda r: str(r["candidate_id"])):
        add(row, "pareto_fill")
    return sorted(chosen.values(), key=lambda r: str(r["candidate_id"]))


def run_seed_screen(
    asset: C.HornAsset,
    catalog: CatalogResult | Sequence[DriverEntry],
    *,
    cabinet: C.VentedBoxRanges,
    assembly: C.AssemblyRanges,
    target: C.SystemTargets,
    envelope: HornEnvelope | None = None,
    full_domain_provenance: str | Path | None = None,
    limit_boxes: int = 4,
    dz_offsets_mm: Sequence[float] = DEFAULT_DZ_OFFSETS_MM,
    half_octaves: float = compatibility.DEFAULT_OVERLAP_HALF_OCTAVES,
    min_band_freqs: int = compatibility.DEFAULT_MIN_BAND_FREQS,
    min_band_dirs: int = compatibility.DEFAULT_MIN_BAND_DIRS,
    good_match_db2: float = compatibility.DEFAULT_GOOD_MATCH_DB2,
    shortlist_size: int = DEFAULT_SHORTLIST_SIZE,
    clearance_mm: float = DEFAULT_CLEARANCE_MM,
    candidate_centers_hz: Sequence[float] | None = None,
    xo_range_hz: tuple[float, float] | None = None,
    placement_policy: str = "envelope_above",
) -> SeedResult:
    """Run the deterministic seed screen and return a Pareto shortlist (never one winner)."""
    entries = tuple(catalog.entries) if isinstance(catalog, CatalogResult) else tuple(catalog)
    catalog_rejected = (tuple(catalog.rejected) if isinstance(catalog, CatalogResult) else ())
    if not entries:
        raise C.DataQualityError("seed screen needs at least one loaded driver")

    listen_h = max(abs(float(target.listening_angle_h_deg[0])),
                   abs(float(target.listening_angle_h_deg[1])))
    listen_v = max(abs(float(target.listening_angle_v_deg[0])),
                   abs(float(target.listening_angle_v_deg[1])))
    fingerprints = compatibility.extract_horn_fingerprints(
        asset, listening_h_deg=listen_h, listening_v_deg=listen_v)
    if not any(fp.accepted for fp in fingerprints.values()):
        raise C.DataQualityError(
            "no usable stored horn fingerprint plane: "
            + "; ".join(r for fp in fingerprints.values() for r in fp.reasons))

    if placement_policy not in ("envelope_above", "seated_overhang"):
        raise ValueError(
            f"placement_policy must be 'envelope_above' or 'seated_overhang', "
            f"got {placement_policy!r}")
    env = envelope if envelope is not None else derive_horn_envelope(
        asset, full_domain_provenance=full_domain_provenance)
    horn_points_mm = None
    if placement_policy == "seated_overhang":
        from hornlab_search.system.assembly_pose import load_horn_points_mm

        env_mesh = getattr(env, "mesh_path", None)
        if not env_mesh or not Path(env_mesh).is_file():
            raise C.DataQualityError(
                "placement_policy='seated_overhang' needs the full-domain horn mesh; the "
                f"envelope came from {env.source!r} and carries no usable mesh_path")
        horn_points_mm = load_horn_points_mm(env_mesh)

    center_list: list[float] | None = None
    if candidate_centers_hz is not None:
        center_list = [float(x) for x in candidate_centers_hz]
    elif xo_range_hz is not None:
        lo, hi = float(xo_range_hz[0]), float(xo_range_hz[1])
        if not (math.isfinite(lo) and math.isfinite(hi) and lo <= hi):
            raise ValueError(f"xo_range_hz must be a finite lo <= hi pair, got {xo_range_hz!r}")
        reference = next(fp for fp in fingerprints.values() if fp.accepted)
        center_list = [float(f) for f in reference.freqs_hz if lo <= float(f) <= hi]
        if not center_list:
            raise C.DataQualityError(
                f"no stored horn frequency sample inside the requested XO region "
                f"[{lo:g}, {hi:g}] Hz; refused instead of interpolating")

    metric_spec = {
        "half_octaves": float(half_octaves),
        "min_freqs": int(min_band_freqs),
        "min_dirs": int(min_band_dirs),
        "good_match_db2": float(good_match_db2),
        "floor_db": compatibility.REPORT_FLOOR_DB,
        "null_flag_db": compatibility.NULL_FLAG_DB,
        "freq_weights": "uniform",
        "dir_weights": "uniform",
        "planes": "H and V separate",
        "listening_h_deg": listen_h,
        "listening_v_deg": listen_v,
        "no_interpolation": True,
        "no_db_power_averaging": True,
        "no_back_hemisphere": True,
        "clearance_mm": float(clearance_mm),
        "placement_policy": placement_policy,
        "dz_offsets_mm": [float(x) for x in dz_offsets_mm],
        "f3_target_hz": target.low_freq_f3_hz_max,
        "horn_layout": assembly.horn_layout,
        "xo_range_hz": None if xo_range_hz is None else [float(xo_range_hz[0]),
                                                         float(xo_range_hz[1])],
        "bl_panel_fit": {
            "applied": True,
            "driver_moving_diameter_m": BL_DEMO_DRIVER_MOVING_DIAMETER_M,
            "driver_y_m": BL_DEMO_DRIVER_Y_M,
            "port_y_m": BL_DEMO_PORT_Y_M,
            "port_wall_m": BL_DEMO_PORT_WALL_M,
            "port_roundover_m": BL_DEMO_PORT_ROUNDOVER_M,
            "cone_depth_m": BL_DEMO_CONE_DEPTH_M,
            "clearance_m": BL_VALIDATE_CLEARANCE_M,
            "screen_placement": "each component at its maximum legal |y|, then BL's exact check",
            "source": ("boundary-lab geometry_providers/vented_enclosure/enclosure/"
                       "parameters.py::validate L100-109"),
        },
    }

    xo_screens: dict[str, compatibility.XoScreen] = {}
    for entry in entries:
        a_m = math.sqrt(entry.cone.sd_m2 / math.pi)
        xo_screens[entry.driver_id] = compatibility.screen_xo_bands(
            fingerprints, a_m, candidate_centers_hz=center_list,
            half_octaves=half_octaves, min_freqs=min_band_freqs,
            min_dirs=min_band_dirs, good_match_db2=good_match_db2)

    counts = {
        "drivers_loaded": len(entries),
        "drivers_rejected": len(catalog_rejected),
        "boxes_considered": 0,
        "boxes_rejected": 0,
        "bl_panel_fit_rejected": 0,
        "xo_hypotheses": 0,
        "xo_rejected": 0,
        "placements_considered": 0,
        "placements_rejected": 0,
        "candidates_kept": 0,
    }
    ledger: list[dict[str, Any]] = [
        {"stage": "driver_catalog", **dict(item)} for item in catalog_rejected]
    kept: list[dict[str, Any]] = []

    for entry in entries:
        screen = xo_screens[entry.driver_id]
        a_m = math.sqrt(entry.cone.sd_m2 / math.pi)
        try:
            boxes = bass_reference.feasible_boxes(entry.cone, cabinet)
        except Exception as exc:  # noqa: BLE001
            ledger.append({"stage": "box_grid", "driver_id": entry.driver_id,
                           "reason": str(exc)})
            continue
        sample = select_box_sample(boxes, limit_boxes)
        if not sample:
            ledger.append({"stage": "box_grid", "driver_id": entry.driver_id,
                           "reason": "no feasible vented box inside the supplied ranges"})
            continue

        for point in sample:
            counts["boxes_considered"] += 1
            box_eval = evaluate_box(entry.driver, point,
                                    f3_target_hz=target.low_freq_f3_hz_max)
            if not box_eval["feasible"]:
                counts["boxes_rejected"] += 1
                ledger.append({"stage": "box_gate", "driver_id": entry.driver_id,
                               "net_volume_l": point.net_volume_l,
                               "tuning_hz": point.derived_tuning_hz,
                               "reasons": list(box_eval["reasons"]),
                               "skips": list(box_eval["skips"])})
                continue

            # Boundary Lab's own generator validator refuses a panel that cannot host the
            # driver + port with its 3 mm clearance and strict separation.  Refuse such a box
            # here instead of proposing a cabinet BL will reject at staging; the rejection stays
            # visible in the report ledger.
            panel_fit = _bl_panel_fit_for_screen(point)
            if not panel_fit["accepted"]:
                counts["boxes_rejected"] += 1
                counts["bl_panel_fit_rejected"] += 1
                ledger.append({
                    "stage": "bl_panel_fit", "driver_id": entry.driver_id,
                    "net_volume_l": point.net_volume_l,
                    "tuning_hz": point.derived_tuning_hz,
                    "external_mm": [point.external_width_mm, point.external_height_mm,
                                    point.external_depth_mm],
                    "port_throat_area_cm2": point.port_throat_area_cm2,
                    "reasons": [panel_fit["reason"]],
                    "driver_y_m": panel_fit["driver_y_m"],
                    "port_y_m": panel_fit["port_y_m"],
                    "source": ("boundary-lab geometry_providers/vented_enclosure/enclosure/"
                               "parameters.py::validate L100-109"),
                })
                continue

            frame_radius = None
            if entry.driver.geometry_mm is not None and entry.driver.geometry_mm.frame_od_mm:
                frame_radius = float(entry.driver.geometry_mm.frame_od_mm) / 2.0
            rear_depth = None
            if entry.driver.geometry_mm is not None:
                rear_depth = (entry.driver.geometry_mm.mounting_depth_behind_baffle_mm
                              or entry.driver.geometry_mm.depth_mm)
            dy_above_min = None
            if placement_policy == "envelope_above":
                dy_above_min = derive_min_center_spacing_mm(
                    env, point, layout=assembly.horn_layout, clearance_mm=clearance_mm,
                    woofer_frame_radius_mm=frame_radius,
                    woofer_frame_center_y_mm=float(panel_fit["driver_y_m"]) * 1e3)

            for xo_hz in screen.hypothesis_centers_hz:
                counts["xo_hypotheses"] += 1
                candidate = next((c for c in screen.candidates if c.f_x_hz == xo_hz), None)
                if candidate is None or not candidate.accepted:
                    counts["xo_rejected"] += 1
                    ledger.append({
                        "stage": "xo_data", "driver_id": entry.driver_id,
                        "xo_hz": float(xo_hz),
                        "reasons": [] if candidate is None else list(candidate.reasons)})
                    continue
                planes = {p: m for p, m in candidate.mismatches.items() if m.accepted}
                e_h = planes["H"].e_shape_db2 if "H" in planes else None
                e_v = planes["V"].e_shape_db2 if "V" in planes else None
                if e_h is None or e_v is None:
                    counts["xo_rejected"] += 1
                    ledger.append({"stage": "xo_data", "driver_id": entry.driver_id,
                                   "xo_hz": float(xo_hz),
                                   "reasons": ["both accepted H and V E_shape values are "
                                               "required"]})
                    continue
                e_h_val = float(e_h)
                e_v_val = float(e_v)

                for dz in dz_offsets_mm:
                    counts["placements_considered"] += 1
                    if placement_policy == "envelope_above":
                        dy_min = dy_above_min
                    else:
                        from hornlab_search.system.assembly_pose import min_legal_dy_mm

                        dy_min = min_legal_dy_mm(
                            horn_points_mm, dz_mm=float(dz), clearance_mm=clearance_mm,
                            cabinet={"external_width_mm": float(point.external_width_mm),
                                     "external_height_mm": float(point.external_height_mm),
                                     "external_depth_mm": float(point.external_depth_mm)})
                        if dy_min is None:
                            counts["placements_rejected"] += 1
                            ledger.append({
                                "stage": "placement", "driver_id": entry.driver_id,
                                "xo_hz": float(xo_hz), "dz_mm": float(dz),
                                "reasons": [
                                    f"cantilever: dz={dz:.1f} mm leaves no horn geometry "
                                    "over the cabinet top; an explicit mount would be "
                                    "needed and is not modelled by this screen"]})
                            continue
                    check = placement_legality(
                        env, point, dx_mm=0.0, dy_mm=dy_min, dz_mm=float(dz),
                        layout=assembly.horn_layout, clearance_mm=clearance_mm,
                        woofer_frame_radius_mm=frame_radius,
                        woofer_rear_depth_mm=rear_depth,
                        woofer_frame_center_y_mm=float(panel_fit["driver_y_m"]) * 1e3,
                        horn_points_mm=horn_points_mm,
                        placement_policy=placement_policy)
                    if not check.accepted:
                        counts["placements_rejected"] += 1
                        ledger.append({
                            "stage": "placement", "driver_id": entry.driver_id,
                            "xo_hz": float(xo_hz), "dz_mm": float(dz),
                            "reasons": list(check.reasons)})
                        continue

                    lf = box_eval["lf"]
                    limit_v = float(bass_reference.bassbox.PORT_AIR_MPS_MAX)
                    port_ratio = max(float(lf["port_velocity_mps_40hz"]),
                                     float(lf["port_velocity_mps_63hz"])) / limit_v
                    footprint = ((float(point.external_width_mm) / 1e3)
                                 * (float(point.external_depth_mm) / 1e3))
                    excursion = lf.get("excursion_margin_db")
                    excursion = (float(excursion) if isinstance(excursion, (int, float))
                                 and math.isfinite(float(excursion)) else 0.0)
                    numeric_axes = {
                        "match_error_h_db2": e_h_val,
                        "match_error_v_db2": e_v_val,
                        "lf_f3_hz": float(lf["f3_hz"]),
                        "port_velocity_ratio": float(port_ratio),
                        "excursion_margin_db": float(excursion),
                        "cabinet_footprint_m2": float(footprint),
                        "mounting_distance_mm": float(dy_min),
                    }
                    row = _round({
                        "candidate_id": _candidate_id(
                            asset.asset_id, entry.driver_id, point, xo_hz, float(dz)),
                        "driver_id": entry.driver_id,
                        "driver_name": entry.cone.name,
                        "box": {
                            "kind": point.kind,
                            "external_width_mm": point.external_width_mm,
                            "external_height_mm": point.external_height_mm,
                            "external_depth_mm": point.external_depth_mm,
                            "net_volume_l": point.net_volume_l,
                            "wall_mm": point.wall_mm,
                            "port_type": point.port_type,
                            "port_throat_area_cm2": point.port_throat_area_cm2,
                            "derived_tuning_hz": point.derived_tuning_hz,
                            "f3_hz": lf["f3_hz"],
                        },
                        "xo_hz": float(xo_hz),
                        "xo_band_hz": list(candidate.band_hz) if candidate.band_hz else None,
                        "placement": {
                            "dx_mm": 0.0, "dy_mm": float(dy_min), "dz_mm": float(dz),
                            "dy_min_mm": float(dy_min),
                            "translation_mm": [0.0, float(dy_min), float(dz)],
                            "placement_policy": placement_policy,
                            "support": ("seated_on_cabinet_top" if check.accepted else None),
                            "transform": [list(r) for r in check.transform],
                            "woofer_frame_center_y_mm": check.woofer_frame_center_y_mm,
                            "min_clearance_mm": check.min_clearance_mm,
                            "gaps_mm": dict(check.gaps_mm),
                            "aabb_overlaps": check.aabb_overlaps,
                            "notes": list(check.notes),
                            "requires_exact_clearance": bool(check.aabb_overlaps),
                        },
                        "match": {
                            "H": planes["H"].to_dict(),
                            "V": planes["V"].to_dict(),
                        },
                        "numeric_axes": numeric_axes,
                        "axis_directions": dict(SEED_AXIS_DIRECTIONS),
                        "feasibility": {
                            "port_fits": box_eval["statuses"]["port"].startswith("PASS"),
                            "wall": box_eval["statuses"]["wall"].startswith("PASS"),
                            "driver_clearance": not box_eval["statuses"][
                                "driver_and_brace"].startswith("FAIL"),
                            "f3_gate": bool(box_eval["f3_ok"]),
                            "bl_panel_fit": True,
                            "placement_legal": True,
                            "xo_data": True,
                        },
                        "lf": dict(lf),
                        "driver_geometry": dict(box_eval["driver_geometry"]),
                        "data_quality": (
                            "SCREEN_MAGNITUDE level-only match; LF SCREEN_MAGNITUDE; "
                            "placement derived from real envelope; no coherent/phase claim"),
                        "status": "PASS",
                    })
                    kept.append(row)
                    counts["candidates_kept"] += 1

    front = _nondominated(kept) if kept else []
    shortlist = _select_diverse(front, int(shortlist_size)) if front else []
    counts["pareto_front_rows"] = len(front)
    counts["shortlist_rows"] = len(shortlist)

    asset_summary = {
        "asset_id": asset.asset_id,
        "design_hash": asset.design_hash,
        "quality": asset.quality,
        "family": asset.geometry.family,
        "brief_id": asset.geometry.brief_id,
        "freq_lo_hz": None if not asset.freqs_hz else float(asset.freqs_hz[0]),
        "freq_hi_hz": None if not asset.freqs_hz else float(asset.freqs_hz[-1]),
        "n_freqs": len(asset.freqs_hz),
        "available_fields": sorted(asset.available_fields),
    }
    response_sha = asset.geometry.extra.get("response_sha256") if isinstance(
        asset.geometry.extra, Mapping) else None
    if not isinstance(response_sha, str) and Path(asset.response_path).is_file():
        response_sha = provenance.file_sha256(asset.response_path)
    input_sha256 = {
        "asset_response_npz": response_sha,
        "horn_envelope": env.envelope_sha256,
        "drivers": {
            entry.driver_id: {
                "ts": entry.ts_sha256,
                "geometry": entry.geometry_sha256,
            } for entry in entries
        },
    }
    study_id = C.system_study_id({
        "schema": SEED_SCHEMA,
        "asset_id": asset.asset_id,
        "design_hash": asset.design_hash,
        "driver_ids": sorted(e.driver_id for e in entries),
        "input_sha256": input_sha256,
        "metric_spec": metric_spec,
        "cabinet": {
            "kind": cabinet.kind,
            "grid": [float(cabinet.net_volume_l_range[0]), float(cabinet.net_volume_l_range[1]),
                     float(cabinet.tuning_hz_range[0]), float(cabinet.tuning_hz_range[1]),
                     float(cabinet.port_throat_area_cm2_range[0]),
                     float(cabinet.port_throat_area_cm2_range[1])],
            "wall_mm": float(cabinet.wall_mm),
        },
        "assembly": {"layout": assembly.horn_layout},
        "target": {
            "f3_max_hz": target.low_freq_f3_hz_max,
            "listen_h": list(target.listening_angle_h_deg),
            "listen_v": list(target.listening_angle_v_deg),
        },
        "limit_boxes": int(limit_boxes),
        "shortlist_size": int(shortlist_size),
        "seed": "deterministic-no-rng",
    })
    return SeedResult(
        asset_summary=asset_summary,
        envelope=env,
        catalog_summary=tuple(entry.to_summary() for entry in entries),
        catalog_rejected=catalog_rejected,
        fingerprint_summary={p: fp.summary() for p, fp in sorted(fingerprints.items())},
        metric_spec=metric_spec,
        xo_screens={k: v.to_dict() for k, v in sorted(xo_screens.items())},
        counts=counts,
        kept_rows=tuple(kept),
        shortlist=tuple(shortlist),
        rejected_ledger=tuple(ledger),
        input_sha256=input_sha256,
        study_id=study_id,
    )


# --------------------------------------------------------------------------- CLI


def _print_summary(result: SeedResult) -> None:
    print(f"study_id: {result.study_id}")
    print(f"asset: {result.asset_summary['asset_id']} "
          f"(design {result.asset_summary['design_hash']})")
    print(f"envelope source: {result.envelope.source}")
    print("counts: " + json.dumps(dict(result.counts), sort_keys=True))
    print("shortlist rows: " + str(len(result.shortlist)))
    for row in result.shortlist:
        axes = row["numeric_axes"]
        print(
            f"  {row['candidate_id']}  {row['driver_id']:<20} "
            f"Vb={row['box']['net_volume_l']:6.1f}L f3={axes['lf_f3_hz']:6.2f}Hz "
            f"xo={row['xo_hz']:7.2f}Hz dy={row['placement']['dy_mm']:6.1f}mm "
            f"dz={row['placement']['dz_mm']:5.1f}mm "
            f"EH={axes['match_error_h_db2']:7.3f} EV={axes['match_error_v_db2']:7.3f} "
            f"port={axes['port_velocity_ratio']:5.3f}")


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry: ``python -m hornlab_search.system.woofer_seed``."""
    import yaml

    from hornlab_search.system import horn_import

    parser = argparse.ArgumentParser(
        description="Deterministic fixed-horn woofer/cabinet/XO/placement seed screen "
                    "(CPU-only, no solver, no GPU).")
    parser.add_argument("--asset-id", required=True,
                        help="verified saved horn asset id (system identity)")
    parser.add_argument("--drivers", nargs="+", default=list(DEFAULT_DRIVER_STEMS),
                        help="driver stems in examples/systems/driver_ts")
    parser.add_argument("--spec", default=str(
        REPO_ROOT / "examples" / "systems" / "two_way_80x50_700_research.yaml"),
        help="system spec YAML providing cabinet/assembly/target ranges")
    parser.add_argument("--out", default=str(REPO_ROOT / "system_runs" / "woofer_seed"),
                        help="output directory for woofer_seed.json / .md")
    parser.add_argument("--runs-root", default=None,
                        help="override the read-only saved-horn runs root")
    parser.add_argument("--scan-limit", type=int, default=300)
    parser.add_argument("--full-domain-provenance", default=None)
    parser.add_argument("--limit-boxes", type=int, default=4)
    parser.add_argument("--shortlist-size", type=int, default=DEFAULT_SHORTLIST_SIZE)
    parser.add_argument("--ts-dir", default=str(DEFAULT_TS_DIR))
    parser.add_argument("--geometry-dir", default=str(DEFAULT_GEOMETRY_DIR))
    parser.add_argument("--placement-policy", default="envelope_above",
                        choices=("envelope_above", "seated_overhang"),
                        help="'envelope_above' keeps the whole horn envelope above the "
                             "cabinet top; 'seated_overhang' lets the mouth hang in front "
                             "of the baffle and derives the closest legal height from the "
                             "real horn mesh (exact clearance is still proven at stage time)")
    args = parser.parse_args(argv)

    spec_doc = yaml.safe_load(Path(args.spec).read_text(encoding="utf-8"))
    spec = C.parse_system_spec_dict(spec_doc)
    asset = horn_import.find_asset(args.asset_id, args.runs_root, scan_limit=args.scan_limit)
    catalog = load_driver_catalog(args.drivers, ts_dir=args.ts_dir,
                                  geometry_dir=args.geometry_dir)
    if not catalog.entries:
        raise C.DataQualityError("no driver could be loaded from the supplied catalog")
    result = run_seed_screen(
        asset, catalog, cabinet=spec.cabinet, assembly=spec.assembly, target=spec.target,
        full_domain_provenance=args.full_domain_provenance,
        limit_boxes=args.limit_boxes, shortlist_size=args.shortlist_size,
        xo_range_hz=spec.dsp.xo_hz_range,
        placement_policy=args.placement_policy)
    json_path, md_path = result.write(args.out)
    _print_summary(result)
    print(f"wrote: {json_path.name}, {md_path.name} under {Path(args.out)}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
