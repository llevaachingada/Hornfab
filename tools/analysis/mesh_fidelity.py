"""A4 mesh fidelity report (read-only).

Reports, per gmsh physical tag of one ASCII ``.msh``: triangle count, edge length p50 / p95 / max
(mm), and ``k * h_max`` at ``--fmax`` with ``k = 2*pi*f/343``. A tag is "valid" at ``--fmax`` when
``h_max <= c / (epw * fmax)`` (c = 343 m/s, default 6 elements per wavelength).

Status (``mesh_fidelity_status``):

* ``source_valid_only``    the source tag (``SD1D1001``) passes and some wall tag fails;
* ``global_max_edge_valid`` every tag passes;
* ``not_assessed``         no ``--fmax``, or a failure that the two rules above do not cover.

``CAD-checked`` and ``converged-vs-reference`` are reserved names for G4/G5 and are never emitted.

Read-only: the mesh and ``mesh_meta.json`` are read; nothing is written. Region names come from
``$PhysicalNames`` when present, otherwise ``tag_<n>``; regions are never guessed from geometry.

Usage::

    .venv\\Scripts\\python.exe tools/analysis/mesh_fidelity.py <mesh.msh or design dir> \\
        [--fmax HZ] [--epw 6] [--out text|json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hornlab_search.mesh.build import read_msh_summary  # noqa: E402

TOOL = "mesh_fidelity"
SCHEMA_VERSION = 1
C_M_S = 343.0
SOURCE_TAG_NAME = "SD1D1001"

STATUS_SOURCE_ONLY = "source_valid_only"
STATUS_GLOBAL = "global_max_edge_valid"
STATUS_NOT_ASSESSED = "not_assessed"


def _triangle_tags(path: Path) -> list[int]:
    """Physical tag of every 3-node triangle, in file order (same order as ``read_msh_summary``)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = lines.index("$Elements")
    n_el = int(lines[start + 1])
    tags: list[int] = []
    for ln in lines[start + 2: start + 2 + n_el]:
        f = ln.split()
        if int(f[1]) != 2:
            continue
        nt = int(f[2])
        tags.append(int(f[3]) if nt >= 1 else 0)
    return tags


def _tag_name(tag: int, names: dict[int, str]) -> str:
    return names.get(tag, f"tag_{tag}")


def _resolve_mesh(target: Path) -> Path:
    if target.is_dir():
        mesh = target / "mesh.msh"
    else:
        mesh = target
    if not mesh.is_file():
        raise FileNotFoundError(f"no mesh file at {mesh}")
    return mesh


def _read_meta(mesh: Path):
    meta = mesh.parent / "mesh_meta.json"
    if not meta.is_file():
        return None
    try:
        return json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"error": f"unreadable mesh_meta.json: {exc}"}


def build_report(target, *, fmax: float | None = None, epw: float = 6.0) -> dict:
    mesh = _resolve_mesh(Path(target))
    summary, xyz, tri = read_msh_summary(mesh, return_arrays=True)
    tags = np.asarray(_triangle_tags(mesh), dtype=np.int64)
    if tags.shape[0] != tri.shape[0]:
        raise ValueError(f"{mesh}: triangle/tag count mismatch ({tags.shape[0]} vs {tri.shape[0]})")
    names = summary["tag_names"]

    p0, p1, p2 = xyz[tri[:, 0]], xyz[tri[:, 1]], xyz[tri[:, 2]]
    edges = np.stack([
        np.linalg.norm(p1 - p0, axis=1),
        np.linalg.norm(p2 - p1, axis=1),
        np.linalg.norm(p0 - p2, axis=1),
    ], axis=1)

    limit_m = None
    k = None
    if fmax is not None:
        if not (fmax > 0 and math.isfinite(fmax)):
            raise ValueError("--fmax must be a positive finite frequency in Hz")
        if not (epw > 0 and math.isfinite(epw)):
            raise ValueError("--epw must be a positive number")
        limit_m = C_M_S / (epw * fmax)
        k = 2.0 * math.pi * fmax / C_M_S

    rows = []
    for tag in sorted(set(int(t) for t in tags)):
        e = edges[tags == tag].ravel()
        h_max = float(e.max())
        row = {
            "tag": tag,
            "name": _tag_name(tag, names),
            "n_triangles": int((tags == tag).sum()),
            "edge_mm_p50": float(np.percentile(e, 50)) * 1000.0,
            "edge_mm_p95": float(np.percentile(e, 95)) * 1000.0,
            "edge_mm_max": h_max * 1000.0,
            "k_h_max": None if k is None else k * h_max,
            "valid": None if limit_m is None else bool(h_max <= limit_m),
        }
        rows.append(row)

    status, reason = _status(rows, fmax)
    return {
        "tool": TOOL,
        "schema_version": SCHEMA_VERSION,
        "mesh": str(mesh),
        "format": summary["format"],
        "n_triangles": summary["n_triangles"],
        "bbox_m": list(summary["bbox_m"]),
        "fmax_hz": fmax,
        "epw": epw if fmax is not None else None,
        "h_max_limit_mm": None if limit_m is None else limit_m * 1000.0,
        "tags": rows,
        "mesh_fidelity_status": status,
        "status_reason": reason,
        "mesh_meta": _read_meta(mesh),
    }


def _status(rows: list[dict], fmax) -> tuple[str, str]:
    if fmax is None:
        return STATUS_NOT_ASSESSED, "no --fmax given"
    failing = [r["name"] for r in rows if not r["valid"]]
    if not failing:
        return STATUS_GLOBAL, "every physical tag has h_max <= c/(epw*fmax)"
    source = next((r for r in rows if r["name"] == SOURCE_TAG_NAME), None)
    if source is not None and source["valid"]:
        return STATUS_SOURCE_ONLY, f"source tag {SOURCE_TAG_NAME} passes; failing: {', '.join(failing)}"
    return STATUS_NOT_ASSESSED, (
        f"failing tags {', '.join(failing)}; source tag {SOURCE_TAG_NAME} "
        f"{'absent' if source is None else 'also fails'}, so no status rule applies")


def _text(report: dict) -> str:
    out = [
        f"mesh: {report['mesh']}",
        f"triangles: {report['n_triangles']}  bbox_m: "
        + ", ".join(f"{v:.4f}" for v in report["bbox_m"]),
    ]
    if report["fmax_hz"] is not None:
        out.append(f"fmax: {report['fmax_hz']:g} Hz  epw: {report['epw']:g}  "
                   f"h_max limit: {report['h_max_limit_mm']:.3f} mm")
    out.append(f"{'tag':>6}  {'name':<24} {'tris':>7} {'p50mm':>9} {'p95mm':>9} "
               f"{'maxmm':>9} {'k*h_max':>8} {'valid':>6}")
    for r in report["tags"]:
        kh = "-" if r["k_h_max"] is None else f"{r['k_h_max']:.3f}"
        va = "-" if r["valid"] is None else ("yes" if r["valid"] else "no")
        out.append(f"{r['tag']:>6}  {r['name']:<24} {r['n_triangles']:>7} {r['edge_mm_p50']:>9.3f} "
                   f"{r['edge_mm_p95']:>9.3f} {r['edge_mm_max']:>9.3f} {kh:>8} {va:>6}")
    out.append(f"mesh_fidelity_status: {report['mesh_fidelity_status']} ({report['status_reason']})")
    if report["mesh_meta"] is not None:
        out.append(f"mesh_meta.json: {json.dumps(report['mesh_meta'], sort_keys=True)}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("target", help="mesh .msh file or design directory containing mesh.msh")
    ap.add_argument("--fmax", type=float, default=None, help="highest frequency to assess, Hz")
    ap.add_argument("--epw", type=float, default=6.0, help="elements per wavelength (default 6)")
    ap.add_argument("--out", choices=("text", "json"), default="text")
    args = ap.parse_args(argv)
    report = build_report(args.target, fmax=args.fmax, epw=args.epw)
    if args.out == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
