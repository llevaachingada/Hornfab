r"""Measure sampled design-sheet distance to emitted wall triangles, on CPU.

Run with a Python containing numpy and VTK, e.g.::
  scratch\vizenv\Scripts\python.exe tools/geometry/check_sculpted_mesh_fidelity.py \
    scratch/sculpted_meridians/study/manifest.json --out scratch/sculpted_meridians/study/fidelity.json

Nearest distance is to *either* wall sheet or lip, not a correspondence test. It
is one-sided at discrete generator stations: it cannot certify intervening surface,
mesh topology, acoustic convergence, or a tolerance. Source triangles are excluded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import vtk

ROOT = Path(__file__).resolve().parents[2]


def read_wall_mesh(path):
    """Read ASCII Gmsh 2.x triangles carrying physical wall tag 1, metres to mm."""
    lines = path.read_text(encoding="utf-8").splitlines()
    section = {line.strip(): i for i, line in enumerate(lines) if line.startswith("$")}
    fmt = lines[section["$MeshFormat"] + 1].split()
    if not fmt[0].startswith("2.") or fmt[1] != "0":
        raise ValueError("expected ASCII Gmsh 2.x")
    i = section["$Nodes"]
    count = int(lines[i + 1])
    rows = [line.split() for line in lines[i + 2 : i + 2 + count]]
    ids = {int(row[0]): n for n, row in enumerate(rows)}
    xyz = np.array([[float(v) for v in row[1:4]] for row in rows]) * 1000
    i = section["$Elements"]
    count = int(lines[i + 1])
    triangles = []
    for line in lines[i + 2 : i + 2 + count]:
        row = line.split()
        ntag = int(row[2])
        if int(row[1]) == 2 and ntag and int(row[3]) == 1:
            triangles.append([ids[int(v)] for v in row[3 + ntag : 6 + ntag]])
    if not triangles:
        raise ValueError("no physical tag 1 wall triangles")
    return xyz, np.asarray(triangles, dtype=int)


def locator_for(xyz, triangles):
    points = vtk.vtkPoints()
    points.SetDataTypeToDouble()
    for point in xyz:
        points.InsertNextPoint(*point)
    cells = vtk.vtkCellArray()
    for tri in triangles:
        cells.InsertNextCell(3)
        for vertex in tri:
            cells.InsertCellPoint(int(vertex))
    poly = vtk.vtkPolyData()
    poly.SetPoints(points)
    poly.SetPolys(cells)
    locator = vtk.vtkStaticCellLocator()
    locator.SetDataSet(poly)
    locator.BuildLocator()
    return locator


def distances(locator, samples):
    values = []
    for sample in samples.reshape(-1, 3):
        closest = [0.0, 0.0, 0.0]
        cell = vtk.reference(0)
        sub = vtk.reference(0)
        dist2 = vtk.reference(0.0)
        locator.FindClosestPoint(sample, closest, cell, sub, dist2)
        values.append(float(dist2) ** 0.5)
    return np.asarray(values).reshape(samples.shape[:-1])


def stats(dist):
    worst = np.unravel_index(np.argmax(dist), dist.shape)
    return {
        "n": int(dist.size),
        "median_mm": float(np.median(dist)),
        "p95_mm": float(np.quantile(dist, 0.95)),
        "max_mm": float(dist[worst]),
        "worst_grid_index": [int(x) for x in worst],
    }


def analyze(surface, mesh, lip_stations):
    with np.load(surface) as data:
        sheets = {name: np.asarray(data[name], dtype=float) for name in ("inner", "outer")}
    xyz, tri = read_wall_mesh(mesh)
    locator = locator_for(xyz, tri)
    result = {
        "mesh": str(mesh.relative_to(ROOT)),
        "mesh_sha256": hashlib.sha256(mesh.read_bytes()).hexdigest(),
        "wall_triangles": len(tri),
        "sheets": {},
    }
    for name, sheet in sheets.items():
        if sheet.ndim != 3 or sheet.shape[-1] != 3 or not np.isfinite(sheet).all():
            raise ValueError(f"{name} must be finite (azimuth, station, 3)")
        d = distances(locator, sheet)
        count = min(lip_stations, d.shape[1])
        near = stats(d[:, -count:])
        near["worst_grid_index"][1] += d.shape[1] - count
        result["sheets"][name] = {"all": stats(d), "near_lip": near, "lip_station_count": count}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--lip-stations", type=int, default=6)
    args = p.parse_args()
    if args.lip_stations < 1:
        p.error("--lip-stations must be positive")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = {
        "schema": "sculpted-mesh-fidelity-v1",
        "manifest": str(args.manifest),
        "units": "mm",
        "vtk_version": vtk.vtkVersion.GetVTKVersion(),
        "method": "nearest physical tag 1 triangle; discrete saved sheet samples; either sheet may be nearest",
        "limitations": "one-sided and unsigned; no sampling between nodes; no topology or acoustic convergence claim",
        "cases": [],
    }
    for case in manifest["cases"]:
        row = {"id": case["id"], "surface": case.get("surface"), "meshes": {}}
        if not case.get("surface"):
            row["error"] = "surface missing"
        else:
            for key in ("mesh", "fine_mesh"):
                if case.get(key):
                    try:
                        row["meshes"][key] = analyze(
                            ROOT / case["surface"], ROOT / case[key], args.lip_stations
                        )
                    except (OSError, ValueError, KeyError) as exc:
                        row["meshes"][key] = {"error": f"{type(exc).__name__}: {exc}"}
        report["cases"].append(row)
    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
