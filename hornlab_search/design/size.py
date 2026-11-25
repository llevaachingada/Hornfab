"""Dimensions and size metadata for solved geometry, independent of acoustic scoring."""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np

from ..config import ENVELOPE_PRODUCT_TOLERANCE_MM, EnvelopePolicy


def full_bbox_extents_mm(bbox_m, symmetry_plane: str | None) -> tuple[float, float, float]:
    """Measure full W/H/D along world axes using the declared mirror plane(s)."""
    x0, y0, z0, x1, y1, z1 = map(float, bbox_m)
    planes = set((symmetry_plane or "").split("+"))
    w = 2.0 * max(abs(x0), abs(x1)) if "yz" in planes else x1 - x0
    h = 2.0 * max(abs(y0), abs(y1)) if "xz" in planes else y1 - y0
    return 1000.0 * w, 1000.0 * h, 1000.0 * (z1 - z0)


def mesh_dimensions_mm(mesh) -> tuple[float, float, float]:
    return full_bbox_extents_mm(mesh.bbox_m, mesh.symmetry_plane)


def sampled_surface_extents_mm(points, symmetry_plane: str | None) -> tuple[float, float, float]:
    """Axis-projected dimensions of a sampled surface in millimetres."""
    vertices = np.asarray(points, dtype=float).reshape(-1, 3)
    bbox_mm = np.concatenate((vertices.min(axis=0), vertices.max(axis=0)))
    return full_bbox_extents_mm(bbox_mm / 1000.0, symmetry_plane)


def size_feasibility_record(mesh, policy: EnvelopePolicy, *, design_hash: str,
                            mesh_hash: str, mounted: bool) -> dict:
    """Describe the solved surface. Printed assemblies may have additional features."""
    size = None if mesh is None else mesh_dimensions_mm(mesh)
    if size is None or not all(math.isfinite(value) and value > 0.0 for value in size):
        return {"policy_id": policy.policy_id, "status": "geometry_unmeasured"}
    width, height, depth = size
    rim = getattr(mesh, "terminal_rim_wh_mm", None)
    aperture = None if rim is None else {
        "source": "sampled_terminal_inner_rim_projection", "width_mm": rim[0], "height_mm": rim[1]}
    descriptor = {
        "status": "mesh_measured",
        "source": "solved_mesh_bbox",
        "accuracy": "mesh_bounds",
        "surface_scope": "mounted_solve_domain" if mounted else "freestanding_solve_domain",
        "surface_identity": {"design_hash": design_hash, "mesh_spec_hash": mesh_hash},
        "width_mm": width, "height_mm": height, "depth_mm": depth,
        "mouth_aperture": aperture,
        "envelope_volume_mm3": width * height * depth,
        "solid_volume_mm3": None,
    }
    serial = json.dumps(descriptor, sort_keys=True, separators=(",", ":"))
    descriptor["descriptor_id"] = "mesh-size-v1-" + hashlib.sha256(serial.encode()).hexdigest()[:16]
    ratios = tuple(actual / limit for actual, limit in zip(size, policy.product_limits_mm))
    if mounted:
        product_fit = "unknown"
    else:
        fits = all(actual <= limit + ENVELOPE_PRODUCT_TOLERANCE_MM
                   for actual, limit in zip(size, policy.product_limits_mm))
        product_fit = "inside" if fits else "outside"
    return {
        "policy_id": policy.policy_id, **descriptor,
        "product_margins": dict(zip(("width", "height", "depth"), (v - 1.0 for v in ratios))),
        "max_utilization": max(ratios),
        "product_fit": product_fit,
        "candidate_fit": "inside" if all(actual <= limit for actual, limit in
                                         zip(size, policy.mesh_limits_mm)) else "outside",
        "manufacturing_feasibility": "unassessed",
        "n_dof": mesh.n_dof,
    }
