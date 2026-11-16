"""Sampled 3-D normal offset for quarter surfaces; not a topology certificate.

Offsets can self-intersect even when their local Jacobian is nonzero; downstream
mesh and independent intersection validation remain mandatory.
"""
import math
import numpy as np


def offset_quarter_surface(inner, wall_thickness_mm):
    """Return (outer, diagnostics) in mm; reject sampled degeneracy and folds."""
    p = np.asarray(inner, dtype=float)
    if p.ndim != 3 or p.shape[2] != 3 or min(p.shape[:2]) < 3 or not np.isfinite(p).all():
        raise ValueError('expected a finite quarter surface with at least 3 x 3 points')
    if isinstance(wall_thickness_mm, bool) or not math.isfinite(float(wall_thickness_mm)) or float(wall_thickness_mm) <= 0:
        raise ValueError('wall thickness must be finite and positive')
    if not np.allclose(p[0, :, 1], 0, atol=1e-8) or not np.allclose(p[-1, :, 0], 0, atol=1e-8):
        raise ValueError('quarter surface does not lie on its symmetry planes')
    dphi = np.gradient(p, axis=0, edge_order=2)
    ds = np.gradient(p, axis=1, edge_order=2)
    # Reflect boundary tangents so the normal remains exactly in the mirror plane.
    dphi[0, :, (0, 2)] = 0
    dphi[-1, :, (1, 2)] = 0
    normal = np.cross(dphi, ds)
    mag = np.linalg.norm(normal, axis=-1)
    if np.any(mag <= 1e-10):
        raise ValueError('degenerate sampled surface normal')
    normal /= mag[..., None]
    radial_dot = np.sum(normal[:, 0, :2] * p[:, 0, :2], axis=1)
    if np.all(radial_dot < -1e-9):
        normal = -normal
    elif not np.all(radial_dot > 1e-9):
        raise ValueError('ambiguous source normal orientation')
    outer = p + float(wall_thickness_mm) * normal
    outer[0, :, 1] = 0
    outer[-1, :, 0] = 0
    # Compare oriented cell triangles: detects sampled local inversion, not
    # intersections between non-neighbouring triangles.
    def faces(a):
        u = a[1:, :-1] - a[:-1, :-1]
        v = a[:-1, 1:] - a[:-1, :-1]
        w = a[1:, 1:] - a[1:, :-1]
        x = a[:-1, 1:] - a[1:, :-1]
        return np.cross(u, v), np.cross(w, x)
    for old, new in zip(faces(p), faces(outer)):
        if np.any(np.linalg.norm(old, axis=-1) <= 1e-10) or np.any(np.sum(old * new, axis=-1) <= 0):
            raise ValueError('sampled offset cell is degenerate or inverted')
    return outer, {'min_sampled_jacobian': float(mag.min()),
                   'normal_offset_mm': float(wall_thickness_mm),
                   'global_self_intersection': 'not_checked',
                   'validity': 'sampled_local_checks_only'}
