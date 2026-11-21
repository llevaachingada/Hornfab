"""Build the CPU-only sculpted-meridian comparison and its manifests."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hornlab_search.config import load_config, mesh_spec
from hornlab_search.design.generators import grid
from hornlab_search.geometry import _sculpted_host_v1 as host
from hornlab_search.geometry import _sculpted_rosse_v1 as sculpt
from hornlab_search.mesh import topology
from hornlab_search.mesh.build import read_msh_summary
from hornlab_search.mesh.grid_build import build_grid_mesh
from hornlab_search.mesh.throat_check import fits_exit, throat_shape
from hornlab_search.types import Design
from hornlab_mesher.icw.checks import meridian_self_intersects

REFERENCE = Path("runs/20261117T053153Z-screen-15f0e4")
FAVORITE = Path("runs/20261120T185832Z-verify-e5de4a")
REFERENCE_ID = "823dc1721a76"
FAVORITE_ID = "4140768780f0"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def capture_rosse():
    from tools.geometry import rolled_rect_cli, rosse_rect_cli

    design = read_json(REFERENCE / "designs" / REFERENCE_ID / "design.json")
    block = design["params"]["grid"]
    if rosse_rect_cli.implementation_digest() != block["rows"]["implementation_sha256"]:
        raise ValueError("archived R-OSSE implementation digest no longer matches the bridge")
    if Design(design["family"], design["params"]).hash() != REFERENCE_ID:
        raise ValueError("R-OSSE archive design identity changed")
    cfg = load_config(REFERENCE / "config.yaml")
    rosse_rect_cli.install()
    inner, _ = rolled_rect_cli._points(block, block["knobs"], cfg.brief)
    return (inner, grid.grid_outer_points(inner, block["wall_thickness_mm"])), block, cfg


def capture_crowe():
    run = read_json(FAVORITE / "run.json")
    cfg = load_config(run["config_path"])
    saved = read_json(FAVORITE / "designs" / FAVORITE_ID / "design.json")
    design = Design(saved["family"], saved["params"])
    block = design.params["grid"]
    if design.hash() != FAVORITE_ID:
        raise ValueError("Crowe archive design identity changed")
    spec = {k: v for k, v in block.items() if k != "knobs"}
    inner, _ = grid.rows_grid_points(spec, block["knobs"], cfg.brief)
    return (inner, grid.grid_outer_points(inner, block["wall_thickness_mm"])), design, cfg


def geometry_metrics(inner, outer, driver):
    rho = np.linalg.norm(inner[..., :2], axis=-1)
    z = inner[..., 2]
    phi = np.arctan2(inner[:, 0, 1], inner[:, 0, 0])
    if not np.all(np.diff(phi) > 0):
        raise ValueError("azimuth ordering is not strict")
    if not np.allclose(rho[:, 0], driver["exit_radius_mm"], rtol=0, atol=1e-9):
        raise ValueError("non-round driver ring")
    if np.any(z[:, 0] != 0):
        raise ValueError("driver ring leaves z=0")
    dz = np.diff(z, axis=1)
    positive = dz > 1e-8
    if np.any(~positive[:, :1]) or np.any(positive[:, -1:]):
        raise ValueError("missing forward entrance or backward lip")
    if np.any((~positive[:, :-1]) & positive[:, 1:]):
        raise ValueError("an azimuth has a second forward lobe after the first axial apex")
    for i, (zi, ri) in enumerate(zip(z, rho)):
        if meridian_self_intersects(zi, ri):
            raise ValueError(f"inner meridian self-intersects at {np.degrees(phi[i]):.2f} deg")

    inside = np.cross(np.diff(inner, axis=0)[:, :-1], np.diff(inner, axis=1)[:-1])
    outside = np.cross(np.diff(outer, axis=0)[:, :-1], np.diff(outer, axis=1)[:-1])
    inside_other = np.cross(np.diff(inner, axis=0)[:, 1:], np.diff(inner, axis=1)[1:])
    outside_other = np.cross(np.diff(outer, axis=0)[:, 1:], np.diff(outer, axis=1)[1:])
    dots = [np.sum(a * b, axis=2) for a, b in
            ((inside, outside), (inside_other, outside_other), (inside, inside_other),
             (outside, outside_other))]
    if any(np.any(d <= 0) for d in dots):
        raise ValueError("opposite orientation or degenerate face in a sampled cell")
    faces = [np.linalg.norm(face, axis=2) for face in (inside, inside_other, outside, outside_other)]
    norms = inside / faces[0][..., None]
    delta = outer - inner
    normal_sep = np.abs(np.sum(norms * delta[:-1, :-1], axis=2))
    distance = np.linalg.norm(delta, axis=2)
    tangent = np.diff(inner, axis=1)
    length = np.linalg.norm(tangent, axis=2)
    tangent /= length[..., None]
    angle = np.arctan2(np.linalg.norm(np.cross(tangent[:, :-1], tangent[:, 1:]), axis=2),
                       np.sum(tangent[:, :-1] * tangent[:, 1:], axis=2))
    curvature = angle / ((length[:, :-1] + length[:, 1:]) / 2)
    envelope = np.array((2 * outer[..., 0].max(), 2 * outer[..., 1].max(),
                         max(outer[..., 2].max(), z.max()) - min(outer[..., 2].min(), z.min())))
    xy = inner[:, -1, :2]
    lip_area = 2 * abs(np.sum(xy[:-1, 0] * xy[1:, 1] - xy[1:, 0] * xy[:-1, 1]))
    forward = z.max(axis=1)
    return {"sampled_outer_envelope_mm": envelope.tolist(), "forward_reach_mm": forward.tolist(),
            "lip_z_mm": z[:, -1].tolist(), "rollback_mm": (forward - z[:, -1]).tolist(),
            "forward_v_minus_h_mm": float(forward[-1] - forward[0]),
            "lip_v_minus_h_mm": float(z[-1, -1] - z[0, -1]),
            "azimuth_deg": np.degrees(phi).tolist(), "lip_projected_area_mm2": float(lip_area),
            "minimum_sampled_cell_cross_mm2": float(min(a.min() for a in faces)),
            "paired_wall_distance_mm": [float(distance.min()), float(distance.max())],
            "min_projected_wall_sep_mm": float(normal_sep.min()),
            "max_meridian_curvature_inv_mm": float(curvature.max()),
            "max_last_quarter_meridian_curvature_inv_mm": float(curvature[:, -len(curvature[0]) // 4:].max())}


def mesh_data(path, driver_diameter):
    import meshio

    stats, pts, tri = read_msh_summary(path, return_arrays=True)
    fit, explanation = fits_exit(throat_shape(path), driver_diameter)
    if not fit or stats["tags"].get(2, 0) == 0:
        raise ValueError(f"invalid excitation mesh: {explanation}")
    lower, upper = np.asarray(stats["bbox_m"]).reshape(2, 3)
    faces = pts[tri]
    stats["outer_envelope_mm"] = (1000 * (upper - lower) * (2, 2, 1)).tolist()
    stats["max_edge_mm"] = float(1000 * np.linalg.norm(faces - np.roll(faces, 1, axis=1), axis=2).max())
    stats["sha256"] = digest(path)
    stats["driver_fit"] = explanation
    physical = meshio.read(path)
    source_cells = physical.cells_dict["triangle"][physical.cell_data_dict["gmsh:physical"]["triangle"] == 2]
    source_xyz = physical.points[np.unique(source_cells)] * 1000
    z = source_xyz[:, 2]
    radial = np.linalg.norm(source_xyz[:, :2], axis=1)
    # Solve the sphere equation for a cap centred on the z axis.
    centre, intercept = np.linalg.lstsq(np.column_stack((2 * z, np.ones(len(z)))),
                                        radial**2 + z**2, rcond=None)[0]
    cap_radius = np.sqrt(intercept + centre**2)
    residual = np.hypot(radial, z - centre) - cap_radius
    stats["source_patch"] = {"nodes": len(source_xyz), "triangles": len(source_cells),
                             "z_span_mm": [float(z.min()), float(z.max())],
                             "fitted_sphere_radius_mm": float(cap_radius),
                             "sphere_max_residual_mm": float(np.max(np.abs(residual)))}
    return stats


def export_full_mesh(source, path):
    """Diagnostic export of the solver triangles in millimetres, with source tags."""
    import meshio

    source_mesh = meshio.read(source)
    original = source_mesh.points * 1000
    tri = source_mesh.cells_dict["triangle"]
    tags = source_mesh.cell_data_dict["gmsh:physical"]["triangle"]
    sheets, cells = [], []
    for x, y in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        cells.append((tri if x * y > 0 else tri[:, ::-1]) + len(sheets) * len(original))
        sheets.append(original * (x, y, 1))
    xyz, index = np.unique(np.vstack(sheets), axis=0, return_inverse=True)
    triangles = index[np.vstack(cells)]
    topology.check_surface(xyz / 1000, triangles, None)
    full_tags = np.tile(tags, len(sheets))
    meshio.write(path, meshio.Mesh(xyz, [("triangle", triangles)],
                                  cell_data={"physical_tag": [full_tags]}))
    exported = meshio.read(path)
    if not (np.array_equal(exported.points, xyz)
            and np.array_equal(exported.cells_dict["triangle"], triangles)
            and np.array_equal(exported.cell_data_dict["physical_tag"]["triangle"], full_tags)):
        raise ValueError("full-mesh diagnostic export failed lossless round trip")
    return {"path": path.as_posix(), "sha256": digest(path), "nodes": len(xyz),
            "triangles": len(triangles), "units": "mm", "lossless_round_trip": True}


def trial_specs(block):
    p = {k[2:]: v for k, v in block["knobs"].items()}
    def flat(value):
        return sculpt.Planes(value, value, value)

    base = sculpt.Body(p["width_mm"], p["height_mm"], p["rect_exponent"],
                       sculpt.Planes(p["a_h_deg"], (p["a_h_deg"] + p["a_v_deg"]) / 2, p["a_v_deg"]),
                       flat(p["m"]), flat(p["r"]), flat(p["b"]), p["tmax"], p["k"], p["q"])
    for case, label, angles in (
        ("R1", "Reduced sweep", (36.0, 31.5, 27.0)),
        ("R2", "Medium sweep", (37.0, 29.5, 23.0)),
        ("R3", "Strong sweep", (37.5, 28.0, 20.0)),
        ("R4", "Near-reference sweep", (38.0, 27.8, 17.8)),
    ):
        yield case, label, replace(base, angle_deg=sculpt.Planes(*angles)), sculpt.Finish()

    landscape = replace(base, width_mm=579.0, height_mm=401.0, exponent=3.3,
                        angle_deg=sculpt.Planes(36.0, 28.0, 18.5),
                        apex_shift=sculpt.Planes(0.86, 0.85, 0.84),
                        apex_radius=sculpt.Planes(0.34, 0.32, 0.30))
    yield "K1", "Landscape Lamé wing", landscape, sculpt.Finish()
    yield "K2", "Landscape with sculpted return", landscape, sculpt.Finish(
        axial_mm=sculpt.Planes(-8.0, -3.0, 6.0), radial_mm=sculpt.Planes(-4.0, -3.0, -1.0),
        start_arc=sculpt.Planes(0.74, 0.77, 0.80),
        roundover_mm=sculpt.Planes(1.0, 0.8, 0.6))


def run(out: Path, *, fine: bool, export_mesh: bool):
    (reference, block, cfg_r), (crowe, original_crowe, cfg_c) = capture_rosse(), capture_crowe()
    out.mkdir(parents=True, exist_ok=True)
    cases = []

    def record(case, label, make, cfg, wall, controls, *, archive=None, neutral=None):
        row = dict(id=case, label=label, controls=controls, status="refused", mesh=None, surface=None)
        cases.append(row)
        dest = out / case
        dest.mkdir(exist_ok=True)
        try:
            inner, outer = make()
            if neutral is not None and not all(np.array_equal(a, b) for a, b in zip((inner, outer), neutral)):
                raise ValueError("zero-control sheets differ from the protected host")
            surface_path = dest / "surfaces.npz"
            np.savez_compressed(surface_path, inner=inner, outer=outer)
            row["surface"] = surface_path.as_posix()
            driver = cfg.brief["driver"]
            row["geometry"] = geometry_metrics(inner, outer, driver)
            row["geometry"]["sampled_nonadjacent_gap_mm"] = grid.check_self_approach(inner, outer, wall)
            envelope = cfg.brief["envelope"]
            limits = [envelope[f"max_{name}_mm"] for name in ("mouth_w", "mouth_h", "depth")]
            if archive is None and np.any(np.asarray(row["geometry"]["sampled_outer_envelope_mm"]) > limits):
                raise ValueError("sampled outer envelope exceeds brief")
            spec = mesh_spec("verify", cfg)
            if spec.epw != 6:
                raise ValueError("reference verify mesh must use 6 epw")
            payload = {"inner_points": inner, "outer_points": outer, "wall_thickness_mm": wall,
                       "meta": {"quarter": True, "row_span": "quarter",
                                "source_auto_angle_deg": driver["exit_angle_deg"]}}
            mesh_path = dest / "mesh.msh"
            build_grid_mesh(payload, spec, mesh_path, cfg, mode="verify")
            row["mesh_6epw"] = mesh_data(mesh_path, 2 * driver["exit_radius_mm"])
            row["mesh"] = mesh_path.as_posix()
            if archive is not None:
                row["archive_mesh_sha256"] = digest(archive)
                if row["archive_mesh_sha256"] != row["mesh_6epw"]["sha256"]:
                    raise ValueError("neutral mesh differs from the archive")
            if archive is None and np.any(np.asarray(row["mesh_6epw"]["outer_envelope_mm"]) > limits):
                raise ValueError("actual meshed outer envelope exceeds brief")
            if export_mesh:
                row["triangulated_export"] = export_full_mesh(mesh_path, dest / "solver_surface_mm.vtu")
            row["status"] = "CPU mesh passed"
            if fine and case in {"R0", "R2", "R3", "K1", "C0", "C1"}:
                fine_path = dest / "mesh_8epw.msh"
                try:
                    build_grid_mesh(payload, replace(spec, epw=8), fine_path, cfg, mode="verify")
                    row["mesh_8epw"] = mesh_data(fine_path, 2 * driver["exit_radius_mm"])
                    row["fine_mesh"] = fine_path.as_posix()
                except Exception as exc:
                    row["mesh_8epw_error"] = f"{type(exc).__name__}: {exc}"
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        print(case, row["status"], row.get("geometry", {}).get("forward_v_minus_h_mm"), row.get("error", ""),
              flush=True)

    ref_mesh = REFERENCE / "verify" / "designs" / REFERENCE_ID / "mesh.msh"
    crowe_mesh = FAVORITE / "designs" / FAVORITE_ID / "mesh.msh"
    wall = block["wall_thickness_mm"]
    record("R0", "Archived R-OSSE", lambda: reference, cfg_r, wall, {"design_hash": REFERENCE_ID},
           archive=ref_mesh, neutral=reference)
    for case, label, body, finish in trial_specs(block):
        record(case, label, lambda: sculpt.surface(
            body, finish, radius_mm=cfg_r.brief["driver"]["exit_radius_mm"],
            source_angle_deg=cfg_r.brief["driver"]["exit_angle_deg"], wall_mm=wall,
            collar_mm=(8, 42), n_phi=49, n_s=97), cfg_r, wall,
            {"body": asdict(body), "finish": asdict(finish), "collar_mm": (8, 42), "grid": (49, 97)})
    record("C0", "Archived Crowe-X", lambda: host.shape_host(*crowe, {}, wall_thickness_mm=3),
           cfg_c, 3, {"design_hash": original_crowe.hash()}, archive=crowe_mesh, neutral=crowe)
    for case, label, knobs in (
        ("C1", "Crowe moderate body", {"body_h_axial_mm": -30, "body_v_axial_mm": 34,
                                        "body_h_radial_mm": 6, "body_v_radial_mm": -5}),
        ("C2", "Crowe strong body + return", {"body_h_axial_mm": -55, "body_v_axial_mm": 62,
                                               "body_h_radial_mm": 9, "body_v_radial_mm": -8,
                                               "terminal_h_radial_mm": -3, "terminal_h_axial_mm": -3,
                                               "terminal_v_axial_mm": 2}),
        ("C3", "Crowe terminal only", {"terminal_h_radial_mm": 2, "terminal_h_axial_mm": -3}),
    ):
        record(case, label, lambda: host.shape_host(*crowe, knobs, wall_thickness_mm=3), cfg_c, 3, knobs)

    # Provenance identity for research derivatives. The archive identifiers above remain separate.
    code_paths = (Path(__file__), Path(sculpt.__file__), Path(host.__file__))
    build_id = {path.name: digest(path) for path in code_paths}
    for row in cases:
        if row["surface"]:
            with np.load(row["surface"]) as capture:
                row["surface_sha256"] = {k: sha256(np.ascontiguousarray(capture[k], dtype="<f8").tobytes()).hexdigest()
                                         for k in ("inner", "outer")}
        if row["id"] not in {"R0", "C0"}:
            row["parent_design_hash"] = FAVORITE_ID if row["id"].startswith("C") else REFERENCE_ID
            row["experiment_id"] = sha256(json.dumps(
                [sculpt.SCHEMA, build_id, row["parent_design_hash"], row["controls"],
                 row.get("surface_sha256")], sort_keys=True).encode()).hexdigest()
    (out / "manifest.json").write_text(json.dumps({"schema": sculpt.SCHEMA, "code_sha256": build_id,
                                                 "cases": cases}, indent=2) + "\n", encoding="utf-8")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--out", type=Path, default=Path("scratch/sculpted_meridians/study"))
    cli.add_argument("--fine", action="store_true", help="also mesh selected arms at 8 epw")
    cli.add_argument("--export-mesh", action="store_true", help="write and replay full diagnostic VTU meshes")
    args = cli.parse_args()
    run(args.out, fine=args.fine, export_mesh=args.export_mesh)


if __name__ == "__main__":
    main()
