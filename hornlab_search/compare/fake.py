"""Synthetic data for BOTH sides, written in the REAL file formats, so the whole pipeline is testable offline.

The "truth" is an analytic horn-like field defined in Boundary Lab's basis (1 m/s, exp(+i w t)). Side A is written as a
Hornfab ``response.npz`` (unit ACCELERATION, exp(-i w t), theta-phi balloon, 2.5 deg cuts) using the INDEPENDENT existing
``solve.phasor.boundary_lab_to_ours`` conversion; side B is written as Boundary Lab GUI text exports and/or a headless run
folder. The importers then read those files like real ones. ``inject`` perturbs ONLY side B:

    none        clean (the verdict must be PASS)
    offset6     +6.02 dB level (half-space vs full-space style)
    slope       B driven by acceleration instead of velocity (-20 dB/decade versus A)
    conj        opposite time convention (phase mirrored)
    polarity    B inverted (phase + 180 deg)
    delay       B phase carries 0.3 ms extra delay
    mirror      B horizontal angle axis mirrored (needs the built-in asymmetric skew)
    swap        B horizontal and vertical planes interchanged
    radius      B observed at 3 m instead of 2 m
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..constants import C_AIR, REF_P
from ..solve import cache as solve_cache
from ..solve import phasor
from ..solve.base import balloon_dirs_from_angles, balloon_grid_shape
from ..types import Response
from .mshio import Mesh, write_msh

INJECTIONS = ("none", "offset6", "slope", "conj", "polarity", "delay", "mirror", "swap", "radius")
FAKE_FREQS = tuple(round(float(x), 2) for x in np.geomspace(100.0, 20000.0, 49))      # 6 per octave
FAKE_DIST_M = 2.0


def _bw(f, base_deg, spread_deg, f0):
    return base_deg + spread_deg * np.exp(-np.asarray(f, dtype=float) / f0)


def truth_norm_db(f, dirs, *, skew_db: float = 2.0) -> np.ndarray:
    """(nf, n) level re on-axis for unit vectors ``dirs`` (z forward): separable Gaussian-in-dB beam with frequency-dependent
    widths and a small x-skew (so the pattern is NOT mirror symmetric). Floored at -45 dB (smoothly: the Gaussian is already far below that behind the horn)."""
    f = np.asarray(f, dtype=float)[:, None]
    ah = np.degrees(np.arctan2(dirs[:, 0], dirs[:, 2]))[None, :]
    av = np.degrees(np.arctan2(dirs[:, 1], dirs[:, 2]))[None, :]
    bh, bv = _bw(f, 85.0, 70.0, 2500.0), _bw(f, 50.0, 55.0, 2000.0)
    lvl = -6.0206 * ((ah / (bh / 2)) ** 2 + (av / (bv / 2)) ** 2) + skew_db * np.tanh(ah / 60.0) * np.minimum(1.0, f / 1500.0)
    return np.maximum(lvl, -45.0)


def truth_axis_db(f) -> np.ndarray:
    f = np.asarray(f, dtype=float)
    return 112.0 + 4.0 * np.log10(f / 1000.0) + 1.5 * np.sin(2 * np.pi * np.log2(f / 700.0) * 0.9) + 0.6 * np.sin(2 * np.pi * np.log2(f / 5000.0) * 3.0)


def truth_p(f, dirs, *, r: float = FAKE_DIST_M, extra_delay_s: float = 0.0) -> np.ndarray:
    """Complex pressure (Pa) per 1 m/s, exp(+i w t), (nf, n). Phase = propagation + a smooth horn group delay + angle term."""
    f = np.asarray(f, dtype=float)
    mag = REF_P * 10.0 ** ((truth_axis_db(f)[:, None] + truth_norm_db(f, dirs)) / 20.0) * (FAKE_DIST_M / r)
    ah = np.arctan2(dirs[:, 0], dirs[:, 2])[None, :]
    ph = (-2 * np.pi * f[:, None] * (r / C_AIR + 1.2e-4 + extra_delay_s) + 0.35 * np.sin(2 * np.pi * np.log2(f / 900.0))[:, None]
          + 0.8 * np.sin(ah) * np.minimum(1.0, f / 2000.0)[:, None])
    return mag * np.exp(1j * ph)


def truth_z(f) -> np.ndarray:
    f = np.asarray(f, dtype=float)
    return (0.85 + 0.12 * np.sin(np.log2(f / 400.0) * 2.0) - 0.2 * np.exp(-f / 600.0)) + 1j * (-0.25 * np.exp(-f / 1500.0) + 0.1 * np.cos(np.log2(f / 800.0) * 3.0))


def arc_dirs(angles_deg, plane: str) -> np.ndarray:
    a = np.radians(np.asarray(angles_deg, dtype=float))
    z = np.cos(a)
    return np.column_stack([np.sin(a), np.zeros_like(a), z]) if plane == "H" else np.column_stack([np.zeros_like(a), np.sin(a), z])


def fibonacci(n: int) -> np.ndarray:
    i = np.arange(n, dtype=float)
    z = 1 - 2 * (i + 0.5) / n
    r = np.sqrt(1 - z * z)
    phi = np.pi * (3 - np.sqrt(5)) * i
    return np.column_stack([r * np.cos(phi), r * np.sin(phi), z])


# ------------------------------------------------------------------ side A: Hornfab files

def fake_response(freqs=FAKE_FREQS, *, angle_count: int = 73, balloon_points: int = 800, noise_db: float = 0.0, seed: int = 1) -> Response:
    """A ``types.Response`` in Hornfab's NATIVE basis (unit acceleration, exp(-i w t)) for the synthetic truth."""
    f = np.asarray(freqs, dtype=float)
    ang = np.linspace(-90.0, 90.0, angle_count)
    ang[angle_count // 2] = 0.0
    rng = np.random.default_rng(seed)

    def to_ours(p):
        q = phasor.boundary_lab_to_ours(p, f)                  # the existing, independently tested conversion
        if noise_db:
            q = q * 10 ** (rng.normal(0, noise_db, q.shape) / 20)
        return q
    ph, pv = to_ours(truth_p(f, arc_dirs(ang, "H"))), to_ours(truth_p(f, arc_dirs(ang, "V")))
    n_th, n_ph = balloon_grid_shape(balloon_points)
    th, phi = np.meshgrid(np.linspace(0, 180, n_th), np.linspace(0, 360, n_ph, endpoint=False), indexing="ij")
    dirs = balloon_dirs_from_angles(th.ravel(), phi.ravel())
    pb = to_ours(truth_p(f, dirs))
    z_ours = np.conj(truth_z(f))                               # Hornfab z_throat is exp(-i w t)
    spl = lambda p: 20 * np.log10(np.abs(p) / REF_P)           # noqa: E731
    return Response(freqs_hz=f, h_angles_deg=ang, v_angles_deg=ang.copy(), spl_h_db=spl(ph), spl_v_db=spl(pv),
                    balloon_dirs=dirs, spl_balloon_db=spl(pb), z_throat=z_ours, p_h=ph, p_v=pv, p_balloon=pb,
                    backend="fake", n_dof=1234,
                    meta={"distance_m": FAKE_DIST_M, "balloon_grid": [n_th, n_ph], "quadrants": "1", "symmetry_plane": "yz+xz",
                          "source_motion": "normal"})


def write_hornfab_side(out_dir, freqs=FAKE_FREQS, **kw) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    solve_cache.save_response(out / "response.npz", fake_response(freqs, **kw))
    (out / "reference_meta.json").write_text(json.dumps({"label": "Hornfab (synthetic)", "distance_m": FAKE_DIST_M,
                                                         "quadrants": "1", "synthetic": True}, indent=2), encoding="utf-8")
    return out


class FakeBackend:
    """Stands in for a solver backend in offline tests of the reference-solve command."""
    name = "fake"

    def __init__(self):
        self.calls = []

    def available(self):
        return True, ""

    def warm(self):
        pass

    def release(self):
        pass

    def solve(self, mesh, spec):
        from ..types import SolveOutcome
        self.calls.append((mesh, spec))
        obs = spec.observation
        r = fake_response(spec.freqs_hz, angle_count=obs.angle_count, balloon_points=max(obs.balloon_points, 6))
        r.meta["distance_m"] = obs.distance_m
        r.meta["quadrants"] = mesh.quadrants
        return SolveOutcome(True, r, 0.01, None, "")


# ------------------------------------------------------------------ side B: Boundary Lab files

def _inject_geometry(inject: str, ang):
    """Returns (angles for H truth, angles for V truth, planes swapped)."""
    if inject == "mirror":
        return -ang, ang, False
    if inject == "swap":
        return ang, ang, True
    return ang, ang, False


def _b_pressure(f, ang, inject: str):
    r = 3.0 if inject == "radius" else FAKE_DIST_M
    delay = 3e-4 if inject == "delay" else 0.0
    a_h, a_v, swap = _inject_geometry(inject, ang)
    ph, pv = truth_p(f, arc_dirs(a_h, "H"), r=r, extra_delay_s=delay), truth_p(f, arc_dirs(a_v, "V"), r=r, extra_delay_s=delay)
    if swap:
        ph, pv = pv, ph
    return ph, pv, r


def _inject_level(p, f, inject: str):
    if inject == "offset6":
        p = p * 10 ** (6.0206 / 20)
    elif inject == "slope":
        p = p / (2 * np.pi * np.asarray(f)[:, None])
    elif inject == "conj":
        p = np.conj(p)
    elif inject == "polarity":
        p = -p
    return p


def _fmt_angle(a):
    return str(int(round(a))) if abs(a - round(a)) < 1e-9 else f"{a:g}"


def write_bl_gui_side(out_dir, freqs=FAKE_FREQS, *, inject: str = "none", polar_step: float = 5.0, balloon_points: int = 1500,
                      clip=(-90.0, 30.0), with_impedance: bool = True) -> Path:
    """Boundary Lab GUI exports: polar/H *.txt (-180..180), on_axis/on_axis.txt, balloon/, impedance/impedance.txt."""
    if inject not in INJECTIONS:
        raise ValueError(f"inject must be one of {INJECTIONS}")
    out = Path(out_dir)
    f32 = np.asarray(freqs, dtype=np.float32)
    f = f32.astype(float)
    full = np.arange(-180.0, 180.0 + 0.5 * polar_step, polar_step)
    ph, pv, r = _b_pressure(f, full, inject)
    ph, pv = _inject_level(ph, f, inject), _inject_level(pv, f, inject)
    i0 = int(np.argmin(np.abs(full)))
    pol = out / "polar"
    pol.mkdir(parents=True, exist_ok=True)
    for plane, p in (("H", ph), ("V", pv)):
        norm = 20 * np.log10(np.abs(p) / np.abs(p[:, [i0]]))
        rel = np.angle(p / p[:, [i0]], deg=True)
        for j, a in enumerate(full):
            lines = [f"{f[k]:.6f}\t{norm[k, j]:.3f}\t{rel[k, j]:.3f}" for k in range(f.size)]
            (pol / f"{plane} {_fmt_angle(a)}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    ax = ph[:, i0]
    ax_al = np.angle(ax * np.exp(1j * 2 * np.pi * f * r / C_AIR), deg=True)       # BL removes distance / c
    (out / "on_axis").mkdir(exist_ok=True)
    (out / "on_axis" / "on_axis.txt").write_text("\n".join(
        f"{f[k]:.6f}\t{20 * np.log10(abs(ax[k]) / REF_P):.3f}\t{ax_al[k]:.3f}" for k in range(f.size)) + "\n", encoding="utf-8", newline="\n")
    dirs = fibonacci(balloon_points)
    pb = _inject_level(truth_p(f, dirs, r=r), f, inject)
    if inject == "mirror":
        pb = _inject_level(truth_p(f, dirs * np.array([-1, 1, 1]), r=r), f, inject)
    ref = 20 * np.log10(np.abs(ax) / REF_P)
    sph = np.clip(20 * np.log10(np.abs(pb) / REF_P) - ref[:, None], clip[0], clip[1]).astype(np.float32)
    bal = out / "balloon"
    bal.mkdir(exist_ok=True)
    th = np.arccos(dirs[:, 2])
    np.savez_compressed(bal / "topology.npz", freq_hz=f32, theta_polar_rad=th.astype(np.float32),
                        phi_azimuth_rad=np.arctan2(dirs[:, 1], dirs[:, 0]).astype(np.float32),
                        directions_xyz=dirs.astype(np.float32), triangle_indices=np.zeros((0, 3), dtype=np.int32))
    np.save(bal / "spl_db.npy", sph)
    (bal / "metadata.json").write_text(json.dumps({"schema": "boundary-lab-balloon-export", "schema_version": 2, "synthetic": True,
                                                   "db_range": {"min_db": clip[0], "max_db": clip[1]}}, indent=2), encoding="utf-8")
    if with_impedance:
        z = truth_z(f)
        if inject == "conj":
            z = np.conj(z)
        (out / "impedance").mkdir(exist_ok=True)
        rows = ["# Boundary Lab - Acoustic Impedance", "# Frequency (Hz)\tThroat source Real (Z/rho c Sd)\tThroat source Imag (Z/rho c Sd)"]
        rows += [f"{f[k]:.9g}\t{z[k].real:.9g}\t{z[k].imag:.9g}" for k in range(f.size)]
        (out / "impedance" / "impedance.txt").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    return out


def write_bl_headless_side(out_dir, freqs=FAKE_FREQS, *, inject: str = "none", polar_step: float = 5.0, balloon_points: int = 1500,
                           area_m2: float = 0.0012, rho: float = 1.21) -> Path:
    """A minimal but format-faithful ``blab project solve`` result folder (manifest v2 layout, quantity ids, domains)."""
    out = Path(out_dir)
    (out / "frequencies").mkdir(parents=True, exist_ok=True)
    f = np.asarray(freqs, dtype=float)
    full = np.arange(-180.0, 180.0 + 0.5 * polar_step, polar_step).astype(np.float32)
    ph, pv, r = _b_pressure(f, full.astype(float), inject)
    ph, pv = _inject_level(ph, f, inject), _inject_level(pv, f, inject)
    dirs = fibonacci(balloon_points)
    ps = _inject_level(truth_p(f, dirs, r=r), f, inject)
    z_gen = truth_z(f) * (rho * C_AIR * area_m2)               # generalized impedance N s / m
    th, phi = np.arccos(dirs[:, 2]), np.arctan2(dirs[:, 1], dirs[:, 0])
    doms = {"d0000_c_0000": full, "d0001_c_0000": full, "d0002_c_0000": th.astype(np.float32), "d0002_c_0001": phi.astype(np.float32),
            "d0003_c_0000": np.array([area_m2])}
    np.savez_compressed(out / "domains.npz", **doms)
    (out / "domains.json").write_text(json.dumps({"domains": [
        {"id": "observation:horizontal-polar", "kind": "polar_observation", "dimensions": ["observation"], "coordinates": {"angle_deg": "d0000_c_0000"}, "topology": {}, "metadata": {}},
        {"id": "observation:vertical-polar", "kind": "polar_observation", "dimensions": ["observation"], "coordinates": {"angle_deg": "d0001_c_0000"}, "topology": {}, "metadata": {}},
        {"id": "observation:sphere", "kind": "spherical_observation", "dimensions": ["observation"],
         "coordinates": {"theta_polar_rad": "d0002_c_0000", "phi_azimuth_rad": "d0002_c_0001"}, "topology": {}, "metadata": {}},
        {"id": "components:radiators", "kind": "component_collection", "dimensions": ["radiator"],
         "coordinates": {"effective_area_m2": "d0003_c_0000"}, "topology": {}, "metadata": {}}]}), encoding="utf-8")
    results = []
    for k, fk in enumerate(f):
        arrays = {"q0000": ph[k:k + 1], "q0001": pv[k:k + 1], "q0002": ps[k:k + 1], "q0003": np.array([z_gen[k]])}
        ids = ["acoustic:pressure:horizontal-polar", "acoustic:pressure:vertical-polar", "acoustic:pressure:sphere",
               "acoustic:radiation-impedance"]
        np.savez_compressed(out / "frequencies" / f"{k:06d}.npz", **{a: np.asarray(v, dtype=np.complex64) for a, v in arrays.items()})
        (out / "frequencies" / f"{k:06d}.json").write_text(json.dumps({
            "freq_hz": float(fk), "excitation_port_ids": ["excitation:source"], "diagnostics": {}, "arrays_file": f"{k:06d}.npz",
            "quantities": [{"key": f"q{i:04d}", "id": qid, "quantity": "pressure", "unit": "Pa", "target_id": None,
                            "axes": ["excitation", "observation"], "shape": list(arrays[f'q{i:04d}'].shape), "dtype": "complex64",
                            "metadata": {}} for i, qid in enumerate(ids)]}), encoding="utf-8")
        results.append({"freq_hz": float(fk), "metadata_file": f"frequencies/{k:06d}.json", "arrays_file": f"frequencies/{k:06d}.npz"})
    (out / "project.snapshot.blab.json").write_text(json.dumps({"schema_version": 10, "project_preferences": {
        "polar_observation_distance_m": r}}), encoding="utf-8")
    (out / "compiled-system.json").write_text(json.dumps({"regions": [{"density_kg_per_m3": rho, "sound_speed_m_per_s": C_AIR}]}),
                                              encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps({
        "schema": "boundary-lab-headless-result", "schema_version": 2, "status": "completed", "project_file": "project.snapshot.blab.json",
        "compiled_system_file": "compiled-system.json", "backend_id": "beat_cpu", "solve_kind": "exterior_bem",
        "phasor_convention": "exp(+i omega t)", "frequencies_hz": f.tolist(), "excitation_port_ids": ["excitation:source"],
        "solver_options": {}, "engine_runs": [], "meshes": [], "completion_mask": [True] * f.size, "results": results,
        "synthetic": True}), encoding="utf-8")
    return out


# ------------------------------------------------------------------ a tiny quarter mesh (no mesher needed)

def fake_quarter_mesh(n_theta: int = 6, n_z: int = 8, r_throat: float = 0.0127, r_mouth: float = 0.12, length: float = 0.15) -> Mesh:
    """Quarter (x>=0, y>=0) of a conical horn wall (tag 1) plus the quarter throat disc (tag 2); open on the symmetry planes.
    Metres. Good enough to test mirroring, areas, tags and the handoff files; it is not meant to be solved."""
    ang = np.linspace(0.0, np.pi / 2, n_theta + 1)
    zs = np.linspace(0.0, length, n_z + 1)
    rad = r_throat + (r_mouth - r_throat) * (zs / length)
    pts = [(0.0, 0.0, 0.0)]
    idx = {}
    for iz, (z, rr) in enumerate(zip(zs, rad)):
        for ia, a in enumerate(ang):
            idx[(iz, ia)] = len(pts)
            pts.append((rr * np.cos(a), rr * np.sin(a), z))
    tri, phys = [], []
    for ia in range(n_theta):                                    # throat disc fan (tag 2): normal toward -z
        tri.append([0, idx[(0, ia + 1)], idx[(0, ia)]])
        phys.append(2)
    for iz in range(n_z):                                        # wall (tag 1)
        for ia in range(n_theta):
            a, b, c, d = idx[(iz, ia)], idx[(iz, ia + 1)], idx[(iz + 1, ia + 1)], idx[(iz + 1, ia)]
            tri += [[a, b, c], [a, c, d]]
            phys += [1, 1]
    return Mesh(np.array(pts), np.array(tri, dtype=np.int64), np.array(phys, dtype=np.int64), {1: "SD1G0", 2: "SD1D1001"})


def write_fake_quarter_msh(path) -> Path:
    return write_msh(fake_quarter_mesh(), path)


def fake_sphere_quarter_mesh(level: int = 2, radius: float = 0.1) -> Mesh:
    """A CLOSED sphere (octahedron subdivided ``level`` times) reduced to x >= 0, y >= 0: open only on the two symmetry planes,
    so it passes the real surface checks. Tag 2 = the cap near +z (the 'throat'), tag 1 = the rest."""
    v = [np.array(p, float) for p in [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]]
    tris = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
    for _ in range(level):
        cache, new = {}, []

        def mid(i, j):
            key = (min(i, j), max(i, j))
            if key not in cache:
                m = v[i] + v[j]
                v.append(m / np.linalg.norm(m))
                cache[key] = len(v) - 1
            return cache[key]
        for a, b, c in tris:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            new += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        tris = new
    xyz = np.array(v) * radius
    tri = np.array(tris, dtype=np.int64)
    cen = xyz[tri].mean(axis=1)
    keep = (cen[:, 0] > 1e-12) & (cen[:, 1] > 1e-12)
    tri = tri[keep]
    phys = np.where(xyz[tri].mean(axis=1)[:, 2] > 0.85 * radius * 0.8, 2, 1).astype(np.int64)
    xyz = np.where(np.abs(xyz) < 1e-12, 0.0, xyz)
    return Mesh(xyz, tri, phys, {1: "SD1G0", 2: "SD1D1001"})
