"""The self-test: the only module that compares our numbers to physics instead of to our own code.

SCOPED EXCEPTION TO HARD RULE 2 (08_TASK_PIPELINE, "search/selftest.py"): this file contains a
tiny icosphere generator and a minimal gmsh 2.2 ASCII writer, because the analytic benchmark is a
pulsating sphere and ``hornlab_mesher`` builds waveguides, not spheres. It is a TEST FIXTURE, not
design geometry. Nothing outside this file may contain mesh-writing code.

``run_analytic``   a pulsating sphere against its exact solution (CP-7a).
``run_crosscheck`` the same horn mesh through ``beat`` and ``bempp`` (CP-7b).

Neither tunes anything to make a number pass; both return the numbers and a verdict.
"""
from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path

import numpy as np

from ..constants import C_AIR, REF_P, RHO_AIR

log = logging.getLogger("hornlab_search.search.selftest")

SOURCE_TAG = 2                       # hornlab_mesher.tags.PhysicalGroup.PRIMARY_SOURCE
SOURCE_NAME = "SD1D1001"

#: ka values of the benchmark (01_CONTRACTS / 08 task): 273, 546, 1092, 2183, 4367 Hz at a=0.1 m.
KA_VALUES = (0.5, 1.0, 2.0, 4.0, 8.0)
SPHERE_RADIUS_M = 0.1
DISTANCES_M = (2.0, 4.0)
#: Full-domain dof ceiling for the CUDA backend on the 8 GB card (TOOLCHAIN M2: 5,496 ok, 9,193 OOM).
CUDA_FULL_DOMAIN_DOF_LIMIT = 5000

SPREADING_TARGET_DB = 20.0 * np.log10(2.0)          # 6.0206 dB for 2 m -> 4 m
SPREADING_TOL_DB = 0.05
OMNI_TOL_DB = 0.1


# ------------------------------------------------------------------ the sphere (a test fixture)

_PHI = (1.0 + 5.0 ** 0.5) / 2.0
_ICO_VERTS = np.array([
    (-1, _PHI, 0), (1, _PHI, 0), (-1, -_PHI, 0), (1, -_PHI, 0),
    (0, -1, _PHI), (0, 1, _PHI), (0, -1, -_PHI), (0, 1, -_PHI),
    (_PHI, 0, -1), (_PHI, 0, 1), (-_PHI, 0, -1), (-_PHI, 0, 1)], dtype=float)
_ICO_FACES = [
    (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
    (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
    (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
    (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]


def icosphere(radius_m: float, subdivisions: int) -> tuple[np.ndarray, np.ndarray]:
    """Subdivided icosahedron. Exactly ``20 * 4**subdivisions`` triangles.

    sub=3 -> 1,280 tris, 642 vertices;  sub=4 -> 5,120, 2,562;  sub=5 -> 20,480, 10,242.
    Edge midpoints are deduplicated through an (edge -> vertex index) dict, so the mesh is
    watertight. Every vertex is projected to the sphere. Triangles are counter-clockwise seen
    from outside, so normals point out of the sphere (into the fluid).
    """
    if subdivisions < 0 or int(subdivisions) != subdivisions:
        raise ValueError("subdivisions must be a non-negative integer")
    pts = [tuple(v / np.linalg.norm(v)) for v in _ICO_VERTS]
    faces = [tuple(f) for f in _ICO_FACES]
    for _ in range(int(subdivisions)):
        mid: dict[tuple[int, int], int] = {}

        def midpoint(i: int, j: int) -> int:
            key = (i, j) if i < j else (j, i)
            k = mid.get(key)
            if k is None:
                p = np.add(pts[i], pts[j])
                pts.append(tuple(p / np.linalg.norm(p)))
                k = mid[key] = len(pts) - 1
            return k

        new = []
        for a, b, c in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            new += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = new
    p = np.asarray(pts, dtype=float)
    p = p / np.linalg.norm(p, axis=1, keepdims=True) * float(radius_m)    # project at the end
    t = np.asarray(faces, dtype=np.int64)
    # Make every triangle point outward (a convex star-shaped body: det(a, b, c) > 0).
    det = np.einsum("ij,ij->i", p[t[:, 0]], np.cross(p[t[:, 1]], p[t[:, 2]]))
    flip = det < 0
    t[flip] = t[flip][:, [0, 2, 1]]
    return p, t


def write_sphere_msh(points, tris, path: Path) -> None:
    """gmsh 2.2 ASCII, METRES, every triangle tagged with the PRIMARY_SOURCE physical tag
    (2, 'SD1D1001'), so the whole surface is the driven port. Node indices in $Elements are
    1-BASED."""
    pts = np.asarray(points, dtype=float)
    tri = np.asarray(tris, dtype=np.int64)
    lines = ["$MeshFormat", "2.2 0 8", "$EndMeshFormat",
             "$PhysicalNames", "1", f'2 {SOURCE_TAG} "{SOURCE_NAME}"', "$EndPhysicalNames",
             "$Nodes", str(len(pts))]
    lines += [f"{i + 1} {x:.17g} {y:.17g} {z:.17g}" for i, (x, y, z) in enumerate(pts)]
    lines += ["$EndNodes", "$Elements", str(len(tri))]
    lines += [f"{i + 1} 2 2 {SOURCE_TAG} {SOURCE_TAG} {a + 1} {b + 1} {c + 1}"
              for i, (a, b, c) in enumerate(tri)]
    lines += ["$EndElements", ""]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def analytic_magnitude(a_m, r_m, ka) -> np.ndarray:
    """|p| = rho*c*U0 * (ka / sqrt(1 + ka^2)) * (a/r), with U0 = 1."""
    ka = np.asarray(ka, dtype=float)
    return RHO_AIR * C_AIR * (ka / np.sqrt(1.0 + ka ** 2)) * (float(a_m) / float(r_m))


# ------------------------------------------------------------------ shared helpers


def _sphere_mesh_result(path: Path, points: np.ndarray, tris: np.ndarray):
    from ..types import MeshResult
    return MeshResult(
        path=str(path), n_triangles=int(len(tris)), n_dof=int(len(points)), quadrants="1234",
        symmetry_plane=None, res_mm={"throat": 0.0, "mouth": 0.0, "rear": 0.0},
        bbox_m=tuple(float(v) for v in (*points.min(axis=0), *points.max(axis=0))), seconds=0.0)


def _spec(backend_name: str, freqs, distance_m: float, cfg, balloon_points: int = 512):
    from ..types import ObservationSpec, SolveSpec
    return SolveSpec(
        mode="screen", freqs_hz=tuple(float(f) for f in freqs), backend=backend_name,
        observation=ObservationSpec(distance_m=float(distance_m),
                                    angle_count=int(cfg.solve.angle_count),
                                    balloon=balloon_points > 0, balloon_points=balloon_points),
        gmres_tol=float(cfg.solve.gmres_tol))


def _get_backend(name: str, cfg, factory=None):
    if factory is not None:
        return factory(name)
    from ..solve.base import get_backend
    return get_backend(name, timeout_s=float(cfg.solve.timeout_s))


def _shape_db(ka) -> np.ndarray:
    ka = np.asarray(ka, dtype=float)
    return 20.0 * np.log10(ka / np.sqrt(1.0 + ka ** 2))


def _solve_sphere(backend, sub: int, radius_m: float, freqs, distances, cfg, workdir: Path,
                  balloon_points: int):
    """{distance: Response} for one subdivision level. Raises RuntimeError on a failed solve."""
    pts, tris = icosphere(radius_m, sub)
    msh = Path(workdir) / f"sphere_sub{sub}.msh"
    write_sphere_msh(pts, tris, msh)
    mesh = _sphere_mesh_result(msh, pts, tris)
    out = {}
    for d in distances:
        spec = _spec(backend.name, freqs, d, cfg, balloon_points=balloon_points if d == distances[0] else 0)
        t0 = time.perf_counter()
        res = backend.solve(mesh, spec)
        if not res.ok:
            raise RuntimeError(f"sphere sub={sub} d={d} m solve failed: {res.message[:600]}")
        log.info("sphere sub=%d (%d dofs) d=%g m: %d freqs in %.1f s", sub, len(pts), d,
                 len(freqs), time.perf_counter() - t0)
        out[d] = res.response
    return out, len(pts)


def _drive_db(freqs_hz, drive: str) -> np.ndarray:
    """dB to ADD to the solved SPL so a constant-drive sphere gives a constant R(ka).

    beat drives tag 2 with a unit normal ACCELERATION (TOOLCHAIN.md C5: the 1 m/s velocity basis
    rescaled by 1/(-i omega)), so for the pulsating sphere |p| is the constant-velocity answer
    divided by omega, and the drive-independent quantity is |p| * omega. A backend that drives with
    unit velocity needs no correction (``drive='velocity'``)."""
    if drive == "velocity":
        return np.zeros(len(freqs_hz))
    if drive == "acceleration":
        return 20.0 * np.log10(2.0 * np.pi * np.asarray(freqs_hz, dtype=float))
    raise ValueError(f"drive must be 'acceleration' or 'velocity', got {drive!r}")


def _r_spread(resp, ka, drive: str = "acceleration") -> tuple[float, np.ndarray]:
    """(max - min of 20 log10 R(ka), R_db per ka), R = |p| * drive_factor / (ka / sqrt(1 + ka^2))."""
    ax = resp.axis_index
    spl = np.asarray(resp.spl_h_db)[:, ax] + _drive_db(resp.freqs_hz, drive)
    r_db = spl - _shape_db(ka)
    return float(r_db.max() - r_db.min()), r_db


# ------------------------------------------------------------------ analytic


def run_analytic(cfg, tol_db: float = 0.5, subdivisions: int = 3, *,
                 convergence_levels=(3, 4, 5), radius_m: float = SPHERE_RADIUS_M,
                 drive: str = "acceleration",
                 backend_factory=None, workdir: Path | None = None) -> dict:
    """A pulsating sphere against its exact solution.

    Sphere radius 0.1 m, ka = 0.5, 1, 2, 4, 8 (273 ... 4367 Hz), observed on axis at 2 m and 4 m.

    Asserts on the SHAPE of the frequency dependence: R(ka) = |p| / (ka / sqrt(1 + ka^2)) must be
    constant in dB across the five ka. The task text assumes the unknown drive scaling is a
    constant; for beat it is NOT: the port is driven with unit normal ACCELERATION (TOOLCHAIN.md
    C5), so |p| carries a 1/omega factor and the literal constant-velocity R(ka) falls 6.02 dB per
    octave of ka (measured: 24.06 dB spread). ``drive='acceleration'`` (default) multiplies the
    solved pressure by omega first, which uses only that documented convention; the literal,
    uncorrected spread is ALWAYS reported too (``r_spread_raw_db``). The corrected test is also
    cross-checked by an absolute comparison with the unit-acceleration sphere
    (``abs_vs_unit_accel_db`` per ka, which is the drive-independent physics).

    Verdict keys: ``passed`` (shape AND omnidirectionality AND spreading), ``checks`` (each pass/
    fail with its number), ``convergence`` (error at each subdivision level, monotone or not).
    Returns a dict; raises nothing for a numeric failure, only for an unusable backend.
    """
    ka = np.asarray(KA_VALUES, dtype=float)
    freqs = ka * C_AIR / (2.0 * np.pi * radius_m)
    workdir = Path(workdir) if workdir is not None else Path(tempfile.mkdtemp(prefix="hs-selftest-"))
    workdir.mkdir(parents=True, exist_ok=True)
    main_name = str(cfg.solve.backend)
    result: dict = {"ka": ka.tolist(), "freqs_hz": freqs.tolist(), "radius_m": radius_m,
                    "drive": drive, "backend": main_name, "subdivisions": int(subdivisions), "tol_db": tol_db,
                    "workdir": str(workdir)}

    backend = _get_backend(main_name, cfg, backend_factory)
    from ..solve import worker
    worker.warm(backend)
    resp, n_dof = _solve_sphere(backend, subdivisions, radius_m, freqs, DISTANCES_M, cfg, workdir, 512)
    r2, r4 = resp[DISTANCES_M[0]], resp[DISTANCES_M[1]]
    ax = r2.axis_index
    result["n_dof"] = n_dof
    result["n_triangles"] = 20 * 4 ** int(subdivisions)

    spread, r_db = _r_spread(r2, ka, drive)
    result["r_spread_raw_db"] = _r_spread(r2, ka, "velocity")[0]
    mean_r = float(np.mean(r_db))
    solved_rel = np.asarray(r2.spl_h_db)[:, ax] + _drive_db(freqs, drive) - mean_r   # dB re mean offset
    analytic_rel = _shape_db(ka)
    dev = solved_rel - analytic_rel
    omega = 2.0 * np.pi * freqs
    acc_ref = 20.0 * np.log10(RHO_AIR * C_AIR / omega * (ka / np.sqrt(1.0 + ka ** 2))
                              * (radius_m / DISTANCES_M[0]) / REF_P)
    abs_offset = np.asarray(r2.spl_h_db)[:, ax] - acc_ref
    result["rows"] = [{"ka": float(k), "f_hz": float(f), "analytic_db_rel": float(a),
                       "solved_db_rel": float(s), "r_dev_db": float(d),
                       "abs_vs_unit_accel_db": float(o)}
                      for k, f, a, s, d, o in zip(ka, freqs, analytic_rel, solved_rel, dev, abs_offset)]
    result["r_spread_db"] = spread

    bal = np.asarray(r2.spl_balloon_db, dtype=float) if r2.spl_balloon_db is not None else None
    omni_balloon = bal.std(axis=1) if bal is not None else None
    omni_h = np.asarray(r2.spl_h_db).std(axis=1)
    omni_v = np.asarray(r2.spl_v_db).std(axis=1)
    omni = omni_balloon if omni_balloon is not None else np.maximum(omni_h, omni_v)
    result["omni_std_db"] = {"balloon": None if omni_balloon is None else omni_balloon.tolist(),
                             "cut_h": omni_h.tolist(), "cut_v": omni_v.tolist()}
    result["omni_source"] = "balloon" if omni_balloon is not None else "cuts"

    spread_db = np.asarray(r2.spl_h_db)[:, ax] - np.asarray(r4.spl_h_db)[:, ax]
    result["spreading_db"] = spread_db.tolist()
    result["spreading_err_db"] = (spread_db - SPREADING_TARGET_DB).tolist()

    # ---- convergence: R(ka) spread at each subdivision level (2 m only for levels other than main)
    conv: dict = {int(subdivisions): {"r_spread_db": spread, "n_dof": n_dof, "backend": main_name}}
    for sub in convergence_levels:
        sub = int(sub)
        if sub in conv:
            continue
        n_v = 10 * 4 ** sub + 2
        name = main_name
        if main_name == "beat_cuda" and n_v > CUDA_FULL_DOMAIN_DOF_LIMIT:
            name = "beat_cpu"           # a full-domain 10k-dof sphere does not fit the 8 GB card
        try:
            be = backend if name == main_name else _get_backend(name, cfg, backend_factory)
            if name != main_name:
                worker.warm(be)
            rr, nd = _solve_sphere(be, sub, radius_m, freqs, (DISTANCES_M[0],), cfg, workdir, 0)
            sp, _ = _r_spread(rr[DISTANCES_M[0]], ka, drive)
            conv[sub] = {"r_spread_db": sp, "n_dof": nd, "backend": name}
        except Exception as exc:  # noqa: BLE001 - a missing level is reported, not fatal
            log.warning("convergence level %d not run: %s", sub, exc)
            conv[sub] = {"r_spread_db": None, "n_dof": n_v, "backend": name, "error": str(exc)[:300]}
    levels = sorted(conv)
    errs = [conv[s]["r_spread_db"] for s in levels]
    complete = all(e is not None for e in errs) and len(errs) >= 2
    monotone = complete and all(b < a for a, b in zip(errs, errs[1:]))
    result["convergence"] = {"levels": {str(s): conv[s] for s in levels}, "complete": complete,
                             "monotone_decreasing": bool(monotone)}

    checks = {
        "R(ka) spread": {"value_db": spread, "limit_db": tol_db, "passed": bool(spread <= tol_db)},
        "omnidirectionality": {"max_std_db": float(np.max(omni)), "limit_db": OMNI_TOL_DB,
                               "passed": bool(np.max(omni) < OMNI_TOL_DB)},
        "spreading 2m->4m": {"max_err_db": float(np.max(np.abs(spread_db - SPREADING_TARGET_DB))),
                             "limit_db": SPREADING_TOL_DB,
                             "passed": bool(np.max(np.abs(spread_db - SPREADING_TARGET_DB))
                                            <= SPREADING_TOL_DB)},
        "convergence": {"errors_db": errs, "passed": bool(monotone), "complete": complete},
    }
    result["checks"] = checks
    result["passed"] = all(checks[k]["passed"] for k in ("R(ka) spread", "omnidirectionality",
                                                         "spreading 2m->4m"))
    result["passed_with_convergence"] = bool(result["passed"] and monotone)
    # The failure signature of a port model that cannot drive a closed surface uniformly:
    # omnidirectionality fails badly while spreading passes (CP-7a "Reading a failure").
    if not checks["omnidirectionality"]["passed"] and checks["spreading 2m->4m"]["passed"]:
        result["diagnosis"] = ("omnidirectionality fails while spreading passes: the signature of "
                               "a port model that cannot impose uniform normal velocity on a "
                               "closed surface (CP-7a), not necessarily a bug in this tool.")
    return result


def format_analytic(res: dict) -> str:
    """Table 1 of CP-6 as text."""
    L = [f"analytic self-test: pulsating sphere a={res['radius_m']} m, backend {res['backend']}, "
         f"icosphere sub={res['subdivisions']} ({res['n_triangles']} tris, {res['n_dof']} dofs)",
         "  ka     f (Hz)   analytic (dB rel)  solved (dB rel)  R(ka) deviation (dB)  "
         "abs vs unit-accel sphere (dB)",
         ]
    for r in res["rows"]:
        L.append(f"  {r['ka']:<5g}  {r['f_hz']:7.0f}  {r['analytic_db_rel']:17.3f}  "
                 f"{r['solved_db_rel']:15.3f}  {r['r_dev_db']:20.3f}  {r['abs_vs_unit_accel_db']:22.3f}")
    L.append(f"  R(ka) spread (max-min) = {res['r_spread_db']:.3f} dB with the {res['drive']}-drive "
             f"correction (tolerance {res['tol_db']} dB); literal constant-velocity R(ka) spread "
             f"= {res['r_spread_raw_db']:.3f} dB")
    om = res["omni_std_db"]
    src = om["balloon"] if om["balloon"] is not None else om["cut_h"]
    L.append("  omnidirectionality, std of dB over the " + res["omni_source"] + " per ka: "
             + ", ".join(f"{v:.4f}" for v in src) + "  (limit 0.1 dB)")
    L.append("  spreading 2 m vs 4 m per ka (dB): "
             + ", ".join(f"{v:.4f}" for v in res["spreading_db"])
             + f"   (target {SPREADING_TARGET_DB:.4f} +/- {SPREADING_TOL_DB})")
    c = res["convergence"]
    L.append("  convergence, R(ka) spread (dB) by subdivision: "
             + ", ".join(f"sub{s}={('%.4f' % v['r_spread_db']) if v['r_spread_db'] is not None else 'n/a'}"
                         f" [{v['n_dof']} dofs, {v['backend']}]" for s, v in c["levels"].items())
             + f"  monotone decreasing: {c['monotone_decreasing']}")
    for k, v in res["checks"].items():
        L.append(f"  {'PASS' if v['passed'] else 'FAIL'}  {k}")
    if res.get("diagnosis"):
        L.append("  " + res["diagnosis"])
    L.append("  RESULT: " + ("PASS" if res["passed"] else "FAIL")
             + ("" if res["passed_with_convergence"] else " (convergence not demonstrated)"
                if res["passed"] else ""))
    return "\n".join(L)


# ------------------------------------------------------------------ cross-check


def _mesh_near_dofs(cfg, design, target_dofs: int, workdir: Path, mode: str = "verify"):
    """Mesh ``design`` so the solved mesh has about ``target_dofs`` dofs. Returns
    (MeshResult, f_max_hz). Chooses f_max from a coarse mesh's area through sizing.f_max_for_dofs."""
    from ..mesh import build, sizing
    from ..types import MeshSpec, MeshTooLargeError
    qf = sizing.QUADRANT_FACTOR[cfg.mesh.quadrants]
    big = 10 ** 6
    probe = build.build_mesh(design, MeshSpec(cfg.mesh.epw, 2000.0, cfg.mesh.quadrants, big), cfg,
                             workdir / "probe", mode=mode)
    area = build.read_msh_summary(Path(probe.path))["area_m2"] * qf
    f = sizing.f_max_for_dofs(target_dofs, area, cfg.mesh.epw, cfg.mesh.quadrants,
                              cfg.mesh.dof_per_triangle)
    f = float(min(max(f, 1500.0), 8000.0))
    for _ in range(4):
        try:
            m = build.build_mesh(design, MeshSpec(cfg.mesh.epw, f, cfg.mesh.quadrants, big), cfg,
                                 workdir / "xc", mode=mode)
            return m, f
        except MeshTooLargeError:
            f *= 0.85
    raise MeshTooLargeError("cross-check mesh did not fit after 4 attempts")


def run_crosscheck(cfg, n_freqs: int = 5, *, target_dofs: int = 2400, workdir: Path | None = None,
                   beat_name: str | None = None, backend_factory=None) -> dict:
    """The SAME quarter horn mesh (about ``target_dofs`` dofs, the seed design) through the beat
    backend and ``bempp_cpu``; per-frequency maximum difference in normalised dB across the
    horizontal (and vertical) cut. Nothing is tuned to make them agree; disagreement is a finding.
    If bempp is not installed the result says so and ``passed`` is None."""
    from ..design.space import DesignSpace
    from ..solve import worker
    workdir = Path(workdir) if workdir is not None else Path(tempfile.mkdtemp(prefix="hs-xcheck-"))
    workdir.mkdir(parents=True, exist_ok=True)
    design = DesignSpace.from_config(cfg).seed
    mesh, f_mesh = _mesh_near_dofs(cfg, design, target_dofs, workdir)
    f_hi = min(0.9 * f_mesh, 4000.0)
    freqs = [round(float(f), 2) for f in np.geomspace(500.0, f_hi, int(n_freqs))]
    out: dict = {"freqs_hz": freqs, "mesh_f_max_hz": f_mesh, "mesh_triangles": mesh.n_triangles,
                 "quadrants": mesh.quadrants, "symmetry_plane": mesh.symmetry_plane,
                 "mesh_path": mesh.path}
    name = beat_name or (cfg.solve.backend if str(cfg.solve.backend).startswith("beat") else "beat_cuda")
    be = _get_backend(name, cfg, backend_factory)
    try:
        bp = _get_backend("bempp_cpu", cfg, backend_factory)
    except Exception as exc:  # noqa: BLE001 - BackendUnavailableError or import failure
        out.update(available=False, reason=f"bempp_cpu unavailable: {exc}", passed=None)
        return out
    worker.warm(be)
    spec_b = _spec(be.name, freqs, 2.0, cfg, balloon_points=0)
    spec_c = _spec(bp.name, freqs, 2.0, cfg, balloon_points=0)
    ob = be.solve(mesh, spec_b)
    if not ob.ok:
        raise RuntimeError(f"{be.name} solve failed: {ob.message[:600]}")
    oc = bp.solve(mesh, spec_c)
    if not oc.ok:
        raise RuntimeError(f"bempp_cpu solve failed: {oc.message[:600]}")
    b, c = ob.response, oc.response
    ax = b.axis_index

    def norm(r, s):
        s = np.asarray(s)
        return s - s[:, ax:ax + 1]

    dh = np.abs(norm(b, b.spl_h_db) - norm(c, c.spl_h_db))
    dv = np.abs(norm(b, b.spl_v_db) - norm(c, c.spl_v_db))
    out.update(
        available=True, backend_a=be.name, backend_b=bp.name, n_dof_a=b.n_dof, n_dof_b=c.n_dof,
        formulation_b=c.meta.get("formulation"), seconds_a=ob.seconds, seconds_b=oc.seconds,
        max_diff_h_db=dh.max(axis=1).tolist(), max_diff_v_db=dv.max(axis=1).tolist(),
        mean_diff_h_db=dh.mean(axis=1).tolist(), overall_max_db=float(max(dh.max(), dv.max())),
        passed=None,        # no pass/fail threshold is defined for this check; the numbers are the result
        reading=_xc_reading(float(max(dh.max(), dv.max()))))
    return out


def _xc_reading(worst_db: float) -> str:
    """09_CHECKPOINTS CP-7b reading table."""
    if worst_db < 0.2:
        return "under 0.2 dB: both are very likely right (strongest verification available)"
    if worst_db <= 1.0:
        return "0.2 to 1 dB: plausible; check whether it grows with frequency (discretization)"
    return "over 1 dB: a real disagreement; run the analytic sphere through both solvers"


def format_crosscheck(res: dict) -> str:
    if not res.get("available", False):
        return "cross-check: NOT RUN. " + str(res.get("reason", ""))
    L = [f"cross-check: {res['backend_a']} ({res['n_dof_a']} dofs, {res['seconds_a']:.1f} s) vs "
         f"{res['backend_b']} ({res['n_dof_b']} dofs, {res['seconds_b']:.1f} s, "
         f"formulation={res['formulation_b']}), same mesh (quadrants {res['quadrants']!r}, "
         f"{res['mesh_triangles']} tris, symmetry {res['symmetry_plane']})",
         "  f (Hz)   max|dH| norm dB   max|dV| norm dB   mean|dH| norm dB"]
    for f, h, v, m in zip(res["freqs_hz"], res["max_diff_h_db"], res["max_diff_v_db"],
                          res["mean_diff_h_db"]):
        L.append(f"  {f:7.0f}  {h:14.4f}   {v:14.4f}   {m:14.4f}")
    L.append(f"  overall max {res['overall_max_db']:.4f} dB -> {res['reading']}")
    return "\n".join(L)
