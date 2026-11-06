"""gmsh ASCII 2.2 triangle meshes: read, write, and mirror a reduced mesh to the FULL domain.

Why mirror here: Hornfab usually solves a quarter (``quadrants "1"``) with the solver's native symmetry
flag. The friend should not have to set symmetry in Boundary Lab, and a full, unsymmetric mesh also tests
Hornfab's symmetry handling. Mirroring is pure numpy, needs no mesher, and keeps the exact nodes of the
mesh Hornfab solved. Winding is flipped per reflection so outward normals stay outward.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..mesh import sizing


@dataclass
class Mesh:
    xyz: np.ndarray                    # (n, 3) metres
    tri: np.ndarray                    # (m, 3) zero-based rows into xyz
    phys: np.ndarray                   # (m,) physical tag per triangle
    names: dict[int, str] = field(default_factory=dict)   # physical tag -> name (dimension 2)

    def tag_areas(self) -> dict[int, float]:
        p0, p1, p2 = (self.xyz[self.tri[:, k]] for k in range(3))
        a = 0.5 * np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1)
        return {int(t): float(a[self.phys == t].sum()) for t in np.unique(self.phys)}

    def bbox(self) -> tuple[float, float, float, float, float, float]:
        pts = self.xyz[np.unique(self.tri)]
        return tuple(float(v) for v in (*pts.min(axis=0), *pts.max(axis=0)))

    def edge_lengths(self) -> np.ndarray:
        e = np.concatenate([self.tri[:, [0, 1]], self.tri[:, [1, 2]], self.tri[:, [2, 0]]])
        return np.linalg.norm(self.xyz[e[:, 0]] - self.xyz[e[:, 1]], axis=1)


def read_msh(path) -> Mesh:
    """Parse MSH 2.x ASCII. Only 3-node triangles are kept; $PhysicalNames dimension 2 is read."""
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    idx = {ln.strip(): i for i, ln in enumerate(lines) if ln.startswith("$")}
    for need in ("$MeshFormat", "$Nodes", "$Elements"):
        if need not in idx:
            raise ValueError(f"{path}: missing {need} (not a gmsh ASCII .msh)")
    fmt = lines[idx["$MeshFormat"] + 1].split()
    if not fmt[0].startswith("2") or fmt[1] != "0":
        raise ValueError(f"{path}: only ASCII MSH 2.x is supported, got {' '.join(fmt)}")
    names: dict[int, str] = {}
    if "$PhysicalNames" in idx:
        i0 = idx["$PhysicalNames"]
        for ln in lines[i0 + 2: i0 + 2 + int(lines[i0 + 1])]:
            dim, tag, name = ln.split(None, 2)
            if int(dim) == 2:
                names[int(tag)] = name.strip().strip('"')
    i0 = idx["$Nodes"]
    n = int(lines[i0 + 1])
    raw = np.array([ln.split() for ln in lines[i0 + 2: i0 + 2 + n]], dtype=float)
    ids = raw[:, 0].astype(np.int64)
    xyz = raw[:, 1:4].copy()
    row_of = np.full(int(ids.max()) + 1, -1, dtype=np.int64)
    row_of[ids] = np.arange(n)
    i0 = idx["$Elements"]
    ne = int(lines[i0 + 1])
    tris, phys = [], []
    for ln in lines[i0 + 2: i0 + 2 + ne]:
        f = ln.split()
        if int(f[1]) != 2:
            continue
        nt = int(f[2])
        phys.append(int(f[3]) if nt >= 1 else 0)
        tris.append([int(v) for v in f[3 + nt: 6 + nt]])
    tri = row_of[np.array(tris, dtype=np.int64).reshape(-1, 3)]
    if np.any(tri < 0):
        raise ValueError(f"{path}: a triangle references an unknown node")
    return Mesh(xyz, tri, np.array(phys, dtype=np.int64), names)


def write_msh(mesh: Mesh, path) -> Path:
    """Write MSH 2.2 ASCII (the format BL's importer and Ath/our mesher use). Only used nodes are written."""
    path = Path(path)
    used = np.unique(mesh.tri)
    new_id = np.full(mesh.xyz.shape[0], -1, dtype=np.int64)
    new_id[used] = np.arange(1, used.size + 1)
    out = ["$MeshFormat", "2.2 0 8", "$EndMeshFormat"]
    if mesh.names:
        out += ["$PhysicalNames", str(len(mesh.names))]
        out += [f'2 {t} "{n}"' for t, n in sorted(mesh.names.items())]
        out += ["$EndPhysicalNames"]
    out += ["$Nodes", str(used.size)]
    out += [f"{new_id[u]} {mesh.xyz[u, 0]:.12g} {mesh.xyz[u, 1]:.12g} {mesh.xyz[u, 2]:.12g}" for u in used]
    out += ["$EndNodes", "$Elements", str(mesh.tri.shape[0])]
    for k, (t, ph) in enumerate(zip(mesh.tri, mesh.phys), start=1):
        out.append(f"{k} 2 2 {int(ph)} {int(ph)} {new_id[t[0]]} {new_id[t[1]]} {new_id[t[2]]}")
    out += ["$EndElements", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out), encoding="utf-8", newline="\n")
    return path


def _reflect(mesh: Mesh, axis: int, tol: float) -> Mesh:
    """Union of the mesh and its mirror image across the plane ``coord[axis] == 0``; plane nodes shared."""
    xyz = mesh.xyz
    mirrored = xyz.copy()
    mirrored[:, axis] = -mirrored[:, axis]
    on_plane = np.abs(xyz[:, axis]) <= tol
    n = xyz.shape[0]
    new_row = np.arange(n, 2 * n)
    new_row[on_plane] = np.nonzero(on_plane)[0]          # a node on the plane is its own image
    all_xyz = np.vstack([xyz, mirrored])
    tri_img = new_row[mesh.tri][:, [0, 2, 1]]            # flip winding: a reflection reverses orientation
    return Mesh(all_xyz, np.vstack([mesh.tri, tri_img]), np.concatenate([mesh.phys, mesh.phys]), dict(mesh.names))


def mirror_to_full(mesh: Mesh, quadrants: str) -> Mesh:
    """Reduced mesh -> full mesh using the SAME table the solver flag comes from (``sizing.SYMMETRY_PLANE``).

    ``yz`` (quadrants "14") mirrors x; ``xz`` ("12") mirrors y; ``yz+xz`` ("1") mirrors both; "1234" is a no-op.
    Raises on a mesh that is not inside its fundamental domain (a convention bug, not a bad candidate).
    """
    if quadrants not in sizing.SYMMETRY_PLANE:
        raise ValueError(f"quadrants must be one of {list(sizing.SYMMETRY_PLANE)}, got {quadrants!r}")
    plane = sizing.SYMMETRY_PLANE[quadrants]
    if plane is None:
        return mesh
    ext = float(np.ptp(mesh.xyz[np.unique(mesh.tri)], axis=0).max())
    tol = max(1e-9, 1e-6 * ext)
    out = mesh
    for flag, axis in (("yz", 0), ("xz", 1)):
        if flag in plane.split("+"):
            if out.xyz[np.unique(out.tri), axis].min() < -tol:
                raise ValueError(f"reduced mesh extends to {'xy'[axis]} < 0 but quadrants {quadrants!r} "
                                 f"puts it in {'xy'[axis]} >= 0 (symmetry/quadrant mismatch)")
            out = _reflect(out, axis, tol)
    return out


def blab_symmetry(quadrants: str) -> str:
    """Boundary Lab project ``symmetry`` value for a Hornfab ``quadrants`` (one source: ``sizing.SYMMETRY_PLANE``).

    "yz+xz" -> "xy", "yz" -> "x", None -> "off". "12" (``xz`` only) has no Boundary Lab equivalent: it raises.
    """
    if quadrants not in sizing.SYMMETRY_PLANE:
        raise ValueError(f"unknown quadrants {quadrants!r}")
    plane = sizing.SYMMETRY_PLANE[quadrants]
    table = {"yz+xz": "xy", "yz": "x", None: "off"}
    if plane not in table:
        raise ValueError(f"quadrants {quadrants!r} (symmetry plane {plane!r}) has no Boundary Lab symmetry value; "
                         f"export the full mesh instead")
    return table[plane]
