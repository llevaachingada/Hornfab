"""Axial-section metrics of a horn's air-facing wall: reference CAD (STL / STEP) or a HornFab grid.

Built for the sculpted-throat research lane
(``docs/research/typologies/sculpted_throat_2026-11-25/00_HANDOFF_2026-11-25.md`` s3.1 / s7).
It answers one question with numbers: does the inner wall actually enter the projected source
disk (a TRUE pinch, ``r(z, phi) < r0``), where, by how much, and with what section shape.

Conventions: z = 0 at the source/flange plane, z increasing into the horn (mm). ``phi`` = 0 on
+x. Radii are found by casting rays from the axis in each z-plane and taking the FIRST wall hit
(the forward acoustic passage; outer shell / flange loops further out are ignored), so the
sections must be star-shaped from the axis -- the ray hit count is reported and a section with
a non-star (re-entrant) inner loop is flagged, never silently averaged.

Inputs never executed: STL is parsed as bytes with numpy; STEP is tessellated with OCP
(OpenCascade) at a stated deflection.  No downloaded script is run.

Usage::

    .venv\\Scripts\\python.exe tools\\geometry\\throat_sections.py stl PATH --r0 12.7 --out DIR
    .venv\\Scripts\\python.exe tools\\geometry\\throat_sections.py step PATH --r0 12.7 --out DIR
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

#: Default axial stations (mm), handoff s3.1 item 1, plus fine stations added by ``stations``.
DEFAULT_Z_MM = (0.0, 1.0, 2.0, 3.0, 5.0, 7.5, 10.0, 15.0, 20.0, 25.0, 35.0, 50.0, 70.0, 100.0)
N_PHI = 360
#: STEP faces starting beyond this z are not tessellated into the section set (speed).
STEP_ZMAX_MM = 120.0
FOURIER_ORDER = 12


# --------------------------------------------------------------------------- loaders
def load_stl(path: str | Path) -> np.ndarray:
    """Binary (or ASCII) STL -> (n, 3, 3) float triangles, file units."""
    b = Path(path).read_bytes()
    if len(b) >= 84:
        n = int(np.frombuffer(b[80:84], dtype="<u4")[0])
        if len(b) == 84 + 50 * n:
            dt = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
            return np.frombuffer(b[84:84 + 50 * n], dtype=dt)["v"].astype(float)
    verts = [list(map(float, ln.split()[1:4])) for ln in b.decode("ascii", "replace").splitlines()
             if ln.strip().startswith("vertex")]
    return np.asarray(verts, dtype=float).reshape(-1, 3, 3)


def load_step(path: str | Path, deflection_mm: float = 0.02, angular_rad: float = 0.05) -> np.ndarray:
    """Tessellate a STEP B-rep with OpenCascade (OCP) -> (n, 3, 3) triangles in mm."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS

    rd = STEPControl_Reader()
    if rd.ReadFile(str(path)) != IFSelect_RetDone:
        raise RuntimeError(f"STEP read failed: {path}")
    rd.TransferRoots()
    shape = rd.OneShape()
    BRepMesh_IncrementalMesh(shape, deflection_mm, False, angular_rad, True)
    tris = []
    ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        face = (TopoDS.Face_s if hasattr(TopoDS, "Face_s") else TopoDS.Face)(ex.Current())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if tri is not None:
            trsf = loc.Transformation()
            nodes = np.array([[p.X(), p.Y(), p.Z()] for p in
                              (tri.Node(i).Transformed(trsf) for i in range(1, tri.NbNodes() + 1))])
            # only the forward region matters for throat sections; skip faces wholly beyond it
            if nodes[:, 2].min() > STEP_ZMAX_MM:
                ex.Next()
                continue
            idx = np.array([tri.Triangle(i).Get() for i in range(1, tri.NbTriangles() + 1)]) - 1
            if face.Orientation() == TopAbs_REVERSED:
                idx = idx[:, ::-1]
            tris.append(nodes[idx])
        ex.Next()
    return np.concatenate(tris, axis=0)


# --------------------------------------------------------------------------- sectioning
def section_segments(tris: np.ndarray, z: float) -> np.ndarray:
    """Plane z = const cut -> (m, 2, 2) xy segments (vectorised)."""
    d = tris[:, :, 2] - z
    hit = (d.max(1) > 0) & (d.min(1) < 0)
    T, D = tris[hit], d[hit]
    out = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        m = D[:, i] * D[:, j] < 0
        t = (D[m, i] / (D[m, i] - D[m, j]))[:, None]
        out.append((np.nonzero(m)[0], T[m, i, :2] + t * (T[m, j, :2] - T[m, i, :2])))
    pts = {}
    for idx, p in out:
        for k, q in zip(idx, p):
            pts.setdefault(int(k), []).append(q)
    segs = [v[:2] for v in pts.values() if len(v) >= 2]
    return np.asarray(segs, dtype=float).reshape(-1, 2, 2)


def ray_radii(segs: np.ndarray, phis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """First wall hit along each ray from the axis; also the number of hits per ray."""
    if segs.size == 0:
        return np.full(phis.shape, np.nan), np.zeros(phis.shape, int)
    a, b = segs[:, 0, :], segs[:, 1, :]
    e = b - a                                    # (m, 2)
    u = np.stack([np.cos(phis), np.sin(phis)], 1)  # (n, 2)
    # solve t*u = a + s*e  ->  [u, -e] [t, s]^T = a
    den = u[:, None, 0] * (-e[None, :, 1]) - u[:, None, 1] * (-e[None, :, 0])
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (a[None, :, 0] * (-e[None, :, 1]) - a[None, :, 1] * (-e[None, :, 0])) / den
        s = (u[:, None, 0] * a[None, :, 1] - u[:, None, 1] * a[None, :, 0]) / den
    ok = (np.abs(den) > 1e-12) & (s >= -1e-9) & (s <= 1 + 1e-9) & (t > 1e-9)
    tt = np.where(ok, t, np.inf)
    r = tt.min(1)
    hits = ok.sum(1)
    r[~np.isfinite(r)] = np.nan
    return r, hits


# --------------------------------------------------------------------------- metrics
def polygon_area(x: np.ndarray, y: np.ndarray) -> float:
    return 0.5 * float(np.abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def convex_hull_area(x: np.ndarray, y: np.ndarray) -> float:
    pts = sorted(set(zip(np.round(x, 9), np.round(y, 9))))
    if len(pts) < 3:
        return 0.0

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    h = np.asarray(lo[:-1] + hi[:-1])
    return polygon_area(h[:, 0], h[:, 1])


def section_metrics(r: np.ndarray, phis: np.ndarray, r0: float) -> dict:
    """Metrics of one star-shaped section r(phi) sampled on a uniform full circle."""
    x, y = r * np.cos(phis), r * np.sin(phis)
    area = polygon_area(x, y)
    hull = convex_hull_area(x, y)
    dphi = 2 * math.pi / phis.size

    def at(deg):
        return float(np.interp(math.radians(deg) % (2 * math.pi), phis, r, period=2 * math.pi))
    # signed curvature of the closed polar curve (positive = convex)
    rp = (np.roll(r, -1) - np.roll(r, 1)) / (2 * dphi)
    rpp = (np.roll(r, -1) - 2 * r + np.roll(r, 1)) / dphi ** 2
    kappa = (r ** 2 + 2 * rp ** 2 - r * rpp) / np.power(r ** 2 + rp ** 2, 1.5)
    coeff = {}
    for k in range(0, FOURIER_ORDER + 1):
        c = float(np.sum(r * np.cos(k * phis)) * dphi / (math.pi if k else 2 * math.pi))
        s = float(np.sum(r * np.sin(k * phis)) * dphi / math.pi) if k else 0.0
        coeff[f"c{k}"], coeff[f"s{k}"] = c, s
    rec = sum(coeff[f"c{k}"] * np.cos(k * phis) + coeff[f"s{k}"] * np.sin(k * phis)
              for k in range(FOURIER_ORDER + 1))
    i_min = int(np.argmin(r))
    return {
        "r_min_mm": float(r[i_min]), "phi_r_min_deg": float(np.degrees(phis[i_min])),
        "r_max_mm": float(np.max(r)), "pinch_ratio": float(r[i_min] / r0),
        "intrusion_mm": float(max(0.0, r0 - r[i_min])),
        "r_h_mm": at(0), "r_225_mm": at(22.5), "r_45_mm": at(45), "r_675_mm": at(67.5), "r_v_mm": at(90),
        "chord_h_mm": at(0) + at(180), "chord_v_mm": at(90) + at(270),
        "width_bbox_mm": float(x.max() - x.min()), "height_bbox_mm": float(y.max() - y.min()),
        "area_mm2": area, "area_ratio_src": area / (math.pi * r0 ** 2),
        "hull_area_mm2": hull, "convexity": area / hull if hull else float("nan"),
        "kappa_min_per_mm": float(np.min(kappa)), "nonconvex": bool(np.min(kappa) < -1e-6),
        "perimeter_mm": float(np.sum(np.hypot(np.diff(np.r_[x, x[0]]), np.diff(np.r_[y, y[0]])))),
        "centroid_x_mm": float(np.mean(x)), "centroid_y_mm": float(np.mean(y)),
        "fourier_resid_max_mm": float(np.max(np.abs(rec - r))),
        "fourier": coeff,
    }


def occlusion_fraction(r_stack: np.ndarray, phis: np.ndarray, r0: float, n_rho: int = 60) -> float:
    """Fraction of the source disk (area-weighted) whose straight axial ray hits the wall."""
    r_min_phi = np.nanmin(r_stack, axis=0)
    rho = (np.arange(n_rho) + 0.5) / n_rho * r0
    blocked = rho[None, :] > r_min_phi[:, None]
    w = np.broadcast_to(rho[None, :], blocked.shape)
    return float(np.sum(w * blocked) / np.sum(w))


def analyse(tris: np.ndarray, r0: float, z_list) -> dict:
    """Section stack -> per-z metrics, r(z, phi) stack, occlusion, axial summaries."""
    phis = np.linspace(0, 2 * math.pi, N_PHI, endpoint=False)
    zmin = float(tris[..., 2].min())
    rows, stack, zs = [], [], []
    for z in z_list:
        zz = max(float(z), zmin + 1e-3)
        segs = section_segments(tris, zz)
        r, hits = ray_radii(segs, phis)
        if np.isnan(r).any():
            continue
        m = section_metrics(r, phis, r0)
        m["z_mm"] = zz
        m["max_ray_hits"] = int(hits.max())
        rows.append(m)
        stack.append(r)
        zs.append(zz)
    stack = np.asarray(stack)
    return {"rows": rows, "z": np.asarray(zs), "phis": phis, "r": stack,
            "occlusion_fraction": occlusion_fraction(stack, phis, r0)}


def grid_r_of_z(inner: np.ndarray, z_list, n_phi_full: int = N_PHI) -> tuple[np.ndarray, np.ndarray]:
    """HornFab inner grid (n_phi, n_s+1, 3) mm, quarter (0..90 deg) -> r(z, phi) on a full circle.

    Each row is a single-valued r(z) on the forward core (the operator only acts there); a row
    whose z is not monotone at the queried z returns its first crossing (the forward branch).
    """
    phis_q = np.arctan2(inner[:, 0, 1], inner[:, 0, 0])
    out = []
    for z in z_list:
        rq = []
        for row in inner:
            zr = row[:, 2]
            rr = np.hypot(row[:, 0], row[:, 1])
            j = int(np.argmax(zr >= z)) if np.any(zr >= z) else len(zr) - 1
            if j == 0:
                rq.append(float(rr[0]))
            else:
                t = (z - zr[j - 1]) / (zr[j] - zr[j - 1])
                rq.append(float(rr[j - 1] + t * (rr[j] - rr[j - 1])))
        out.append(rq)
    out = np.asarray(out)                       # (nz, n_phi_quarter)
    phis = np.linspace(0, 2 * math.pi, n_phi_full, endpoint=False)
    fold = np.abs(np.arctan2(np.abs(np.sin(phis)), np.abs(np.cos(phis))))  # quarter-fold
    full = np.stack([np.interp(fold, phis_q, row) for row in out])
    return phis, full


# --------------------------------------------------------------------------- outputs
def write_outputs(res: dict, out_dir: Path, meta: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    keys = [k for k in res["rows"][0] if k != "fourier"]
    with open(out_dir / "sections.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(keys)
        for row in res["rows"]:
            w.writerow([f"{row[k]:.5g}" if isinstance(row[k], float) else row[k] for k in keys])
    with open(out_dir / "fourier.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        ks = list(res["rows"][0]["fourier"])
        w.writerow(["z_mm"] + ks)
        for row in res["rows"]:
            w.writerow([f"{row['z_mm']:.4g}"] + [f"{row['fourier'][k]:.5g}" for k in ks])
    np.savez_compressed(out_dir / "angular_radii.npz", z_mm=res["z"], phi_rad=res["phis"], r_mm=res["r"])
    summ = dict(meta)
    rmin = min(res["rows"], key=lambda r: r["r_min_mm"])
    summ.update({"occlusion_fraction": res["occlusion_fraction"],
                 "global_r_min_mm": rmin["r_min_mm"], "global_r_min_z_mm": rmin["z_mm"],
                 "global_r_min_phi_deg": rmin["phi_r_min_deg"], "global_pinch_ratio": rmin["pinch_ratio"],
                 "min_convexity": min(r["convexity"] for r in res["rows"]),
                 "any_nonconvex": any(r["nonconvex"] for r in res["rows"]),
                 "max_ray_hits": max(r["max_ray_hits"] for r in res["rows"])})
    (out_dir / "summary.json").write_text(json.dumps(summ, indent=2))


def plot_sections(res: dict, out_png: Path, r0: float, title: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(16, 5.4))
    ph = np.r_[res["phis"], res["phis"][:1]]
    cmap = plt.get_cmap("viridis")
    n = len(res["z"])
    for i, (z, r) in enumerate(zip(res["z"], res["r"])):
        rr = np.r_[r, r[:1]]
        axs[0].plot(rr * np.cos(ph), rr * np.sin(ph), lw=0.9, color=cmap(i / max(n - 1, 1)),
                    label=f"z={z:g}")
    t = np.linspace(0, 2 * math.pi, 200)
    axs[0].plot(r0 * np.cos(t), r0 * np.sin(t), "r--", lw=1.2, label="source disk")
    axs[0].set_aspect("equal"); axs[0].set_title("sections (first wall hit)")
    lim = 2.6 * r0
    axs[0].set_xlim(-lim, lim); axs[0].set_ylim(-lim, lim); axs[0].legend(fontsize=6, ncol=2)
    for deg, c in ((0, "C0"), (22.5, "C1"), (45, "C2"), (67.5, "C3"), (90, "C4")):
        j = int(round(deg / 360 * res["phis"].size))
        axs[1].plot(res["z"], res["r"][:, j], c, label=f"phi {deg:g}")
    axs[1].axhline(r0, color="r", ls="--", lw=1)
    axs[1].set_xlabel("z mm"); axs[1].set_ylabel("r mm"); axs[1].legend(); axs[1].set_title("meridian radii")
    area = [row["area_ratio_src"] for row in res["rows"]]
    conv = [row["convexity"] for row in res["rows"]]
    pr = [row["pinch_ratio"] for row in res["rows"]]
    axs[2].plot(res["z"], area, label="area / source area")
    axs[2].plot(res["z"], conv, label="convexity A/A_hull")
    axs[2].plot(res["z"], pr, label="min r / r0")
    axs[2].axhline(1.0, color="k", lw=0.6)
    axs[2].set_xlabel("z mm"); axs[2].legend(); axs[2].set_title(f"occlusion {res['occlusion_fraction']:.1%}")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("kind", choices=("stl", "step"))
    ap.add_argument("path")
    ap.add_argument("--r0", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--z", type=float, nargs="*", default=None)
    ap.add_argument("--zmax", type=float, default=100.0)
    ap.add_argument("--dz-fine", type=float, default=1.0, help="extra uniform stations up to --zmax")
    ap.add_argument("--deflection", type=float, default=0.02)
    a = ap.parse_args(argv)
    p = Path(a.path)
    tris = load_stl(p) if a.kind == "stl" else load_step(p, a.deflection)
    z = sorted(set(list(a.z or DEFAULT_Z_MM) + list(np.arange(0.0, a.zmax + 1e-9, a.dz_fine))))
    res = analyse(tris, a.r0, z)
    meta = {"source_file": p.name, "kind": a.kind, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "n_triangles": int(len(tris)), "r0_mm": a.r0,
            "bbox_mm": [tris.reshape(-1, 3).min(0).tolist(), tris.reshape(-1, 3).max(0).tolist()],
            "deflection_mm": a.deflection if a.kind == "step" else None,
            "method": "plane sections; first wall hit along rays from the axis (forward passage only)"}
    out = Path(a.out)
    write_outputs(res, out, meta)
    plot_sections(res, out / "sections.png", a.r0, f"{p.name} ({a.kind})")
    print(json.dumps(json.loads((out / "summary.json").read_text()), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
