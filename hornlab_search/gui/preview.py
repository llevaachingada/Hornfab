"""The ONE seam over the mesher's on-demand preview primitives (sandbox geometry).

``hornlab_mesher.preview``'s underscore helpers are not stable public API, but they are the
mesher's own surface tessellator: composing them is sanctioned PRIVATE USE through this single
module, exactly the closed-issue-#9 pattern ``hornlab_search/mesh/grid.py`` uses for
``build_point_grid``. Hand-writing triangle-index loops here (or in ``gui/data.py``) would BE
writing a tessellator, which hard rule 2 forbids. This module therefore does no geometry of its
own: it transposes the canonical grid, asks the mesher for analytic normals, and asks the
mesher's own assemblers for the three preview roles.

The five names below are the pinned contract. ``tests/test_gui_preview_shape.py`` fails (never
softly skips) if any of them disappears from the installed mesher. A mesher bump that moves them
must update this module and the pin in the same commit.

Inputs are the mesher's canonical ``(n_phi, n_t, 3)`` grids in millimetres:

* ``inner_grid`` -- the inner acoustic surface;
* ``outer_grid`` -- the freestanding outer shell (``None`` is honest: no shell is fabricated);
* ``t_coordinates`` / ``phi_coordinates`` -- optional real parameter coordinates for the
  analytic-normal finite differences (``None`` lets the mesher use uniform indices);
* ``closed_phi`` -- a full ring (periodic azimuth), never a quarter/half model.
"""
from __future__ import annotations

from typing import Any

import numpy as np

#: The five mesher symbols this seam composes. The pin test fails loudly on any absence.
PINNED_NAMES = (
    "_surface_grid",                 # hornlab_mesher.preview.primitives
    "_grid_surface_from_selection",  # hornlab_mesher.preview.primitives
    "_smooth_mouth_rim",             # hornlab_mesher.preview.primitives
    "_outer_shell_surfaces",         # hornlab_mesher.preview.horn
    "analytic_grid_normals",         # hornlab_mesher.preview.fidelity
)

try:  # single import site: a mesher move fails here, loudly, never silently
    from hornlab_mesher.preview.fidelity import analytic_grid_normals
    from hornlab_mesher.preview.horn import _outer_shell_surfaces
    from hornlab_mesher.preview.primitives import (
        _grid_surface_from_selection,
        _smooth_mouth_rim,
        _surface_grid,
    )
except Exception as exc:  # noqa: BLE001 - any import shape change is the same failure
    raise RuntimeError(
        "the hornlab_mesher preview API is unavailable; the mesher pin may have changed "
        "(pinned names: " + ", ".join(PINNED_NAMES) + "; see tests/test_gui_preview_shape.py "
        "and TOOLCHAIN.md)."
    ) from exc


def _exit_direction(inner: np.ndarray) -> np.ndarray:
    """Per-phi direction the inner profile travels at the mouth (the mesher's own rule).

    Mirrors ``hornlab_mesher.preview.primitives._mouth_exit_direction`` (a one-line direction
    hint, not tessellation): the rim is the wall's end face, so a rolled-back mouth exits
    backwards and must not be forced to +z. Kept local so the pinned surface list stays the
    five names the spike sanctioned.
    """
    if inner.shape[1] < 2:
        return np.tile(np.asarray((0.0, 0.0, 1.0), dtype=np.float64), (len(inner), 1))
    direction = np.asarray(inner[:, -1, :] - inner[:, -2, :], dtype=np.float64)
    lengths = np.linalg.norm(direction, axis=1, keepdims=True)
    direction = direction / np.where(lengths > 0.0, lengths, 1.0)
    direction[lengths[:, 0] <= 1.0e-12] = (0.0, 0.0, 1.0)
    return direction


def tessellate(
    inner_grid: Any,
    outer_grid: Any = None,
    *,
    t_coordinates: Any = None,
    phi_coordinates: Any = None,
    closed_phi: bool = False,
) -> dict:
    """Tessellate one canonical grid into the three sandbox preview roles.

    Returns ``{"roles": [...], "positions": (N, 3) float64, "indices": (M, 3) int64,
    "warnings": [...]}``. The roles are emitted in render order and every surface keeps the
    mesher's own winding-vs-normal validation. ``outer_grid is None`` omits
    ``horn.outer``/``mouth_rim`` rather than inventing a shell.

    A sandbox shows shapes the search would refuse, so a wall that folds over itself is DRAWN,
    not dropped: when the inner surface fails the strict winding check it is rebuilt with the
    mesher's own ``wind_folds_individually`` repair and the folded-triangle count is reported in
    ``warnings``; a mouth rim that fails alone is left out (also reported).
    """
    inner = np.ascontiguousarray(np.asarray(inner_grid, dtype=np.float64))
    if inner.ndim != 3 or inner.shape[2] != 3:
        raise ValueError(f"inner_grid must be (n_phi, n_t, 3), got {inner.shape}")
    closed = bool(closed_phi)
    master = _surface_grid(inner)
    normals = analytic_grid_normals(
        master,
        closed_phi=closed,
        t_coordinates=None if t_coordinates is None else np.asarray(t_coordinates, dtype=np.float64),
        phi_coordinates=None if phi_coordinates is None else np.asarray(phi_coordinates, dtype=np.float64),
    )
    t_indices = np.arange(master.shape[0], dtype=np.int64)
    phi_indices = np.arange(master.shape[1], dtype=np.int64)
    selected_inner = master[np.ix_(t_indices, phi_indices)]

    warnings: list[str] = []
    try:
        inner_surface = _grid_surface_from_selection(
            "horn.inner", master, normals, t_indices, phi_indices,
            closed_phi=closed, normal_sign=-1.0)
    except ValueError as exc:
        inner_surface = _grid_surface_from_selection(
            "horn.inner", master, normals, t_indices, phi_indices,
            closed_phi=closed, normal_sign=-1.0, wind_folds_individually=True)
        folded = int((inner_surface.metadata or {}).get("foldedTriangles") or 0)
        warnings.append(f"the inner wall folds over itself ({folded} folded triangles drawn; "
                        f"strict check: {exc})")
    surfaces = [inner_surface]
    if outer_grid is not None:
        outer = np.ascontiguousarray(np.asarray(outer_grid, dtype=np.float64))
        if outer.shape != inner.shape:
            raise ValueError(f"outer_grid {outer.shape} must match inner_grid {inner.shape}")
        outer_master = _surface_grid(outer)
        selected_outer = outer_master[np.ix_(t_indices, phi_indices)]
        outer_parts = _outer_shell_surfaces(
            outer_master,
            _surface_grid(selected_inner),
            t_indices,
            phi_indices,
            closed_phi=closed,
            t_coordinates=None if t_coordinates is None else np.asarray(t_coordinates, dtype=np.float64),
            phi_coordinates=None if phi_coordinates is None else np.asarray(phi_coordinates, dtype=np.float64),
            include_curvature=False,
        )
        # The mesher may split the shell at the throat-jog crease (a shading role); the sandbox
        # contract has exactly three roles, so every shell part rides under "horn.outer".
        surfaces.extend(outer_parts)
        try:
            surfaces.append(
                _smooth_mouth_rim(
                    selected_inner[:, -1, :],
                    selected_outer[:, -1, :],
                    closed_phi=closed,
                    exit_direction=_exit_direction(selected_inner),
                    include_curvature=False,
                )
            )
        except ValueError as exc:
            warnings.append(f"mouth rim face left out ({exc})")

    positions: list[np.ndarray] = []
    triangles: list[np.ndarray] = []
    roles: list[str] = []
    offset = 0
    for surface in surfaces:
        role = "horn.outer" if surface.role.startswith(("horn.outer", "wall.")) else surface.role
        positions.append(np.asarray(surface.positions, dtype=np.float64))
        tris = np.asarray(surface.indices, dtype=np.int64).reshape(-1, 3)
        triangles.append(tris + offset)
        offset += len(surface.positions)
        if role not in roles:
            roles.append(role)
    return {
        "roles": roles,
        "positions": np.vstack(positions),
        "indices": np.vstack(triangles),
        "warnings": warnings,
    }
