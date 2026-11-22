r"""CPU-only R2 native truncation probe with matched-mesh source diagnostics.

Run .venv\Scripts\python.exe tools/geometry/sculpted_roll_probe.py
Use --out scratch/sculpted_v11_roll_replay for an independent output directory.

GRID passes inner and outer point sheets to PointGridHornGeometry. It exposes
no specified-radius surface connecting the sheets. A physical roundover needs
a separate construction with verified tangent continuity and clearance.
Native tmax changes also refit R and modify the body. Station-index differences
are not physical correspondences.
"""
import argparse
from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path
import sys

import meshio
import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hornlab_search.config import mesh_spec
from hornlab_search.design.generators.grid import check_self_approach
from hornlab_search.geometry import _sculpted_rosse_v1 as sculpt
from hornlab_search.mesh.grid_build import build_grid_mesh
from tools.geometry.sculpted_meridians_study import capture_rosse, digest, geometry_metrics, mesh_data, trial_specs

OUT = ROOT / "scratch/sculpted_v11_roll"
def source(path):
    mesh = meshio.read(path)
    cells = mesh.cells_dict["triangle"]
    faces = cells[mesh.cell_data_dict["gmsh:physical"]["triangle"] == 2]
    nodes, inverse = np.unique(faces, return_inverse=True)
    return mesh.points[nodes], inverse.reshape(-1, 3)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    output_dir = args.out.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    _, block, cfg = capture_rosse()
    body = next(b for case, _, b, _ in trial_specs(block) if case == "R2")
    driver = cfg.brief["driver"]
    wall = block["wall_thickness_mm"]
    baseline = np.load(ROOT / "scratch/sculpted_meridians/study/R2/surfaces.npz")
    old = np.asarray(baseline["inner"])
    reference_mesh = ROOT / "scratch/sculpted_meridians/study/R2/mesh.msh"

    reference_nodes, reference_faces = source(reference_mesh)
    out = {"schema":"native-rosse-probe-v1", "parent":"R2", "candidates":[]}
    for tmax in (0.96, 0.95, 0.94):
        name = f"R2_tmax_{tmax:.2f}"
        row = {"id":name,"tmax":tmax,"status":"refused"}
        out["candidates"].append(row)
        try:
            inner, outer = sculpt.surface(replace(body, tmax=tmax), sculpt.Finish(),
                radius_mm=driver["exit_radius_mm"], source_angle_deg=driver["exit_angle_deg"],
                wall_mm=wall, collar_mm=(8,42), n_phi=49, n_s=97)
            geo = geometry_metrics(inner, outer, driver)
            geo["sampled_nonadjacent_gap_mm"] = check_self_approach(inner, outer, wall)
            dest = output_dir / name
            dest.mkdir(exist_ok=True)
            np.savez_compressed(dest / "surfaces.npz", inner=inner, outer=outer)
            payload = {"inner_points":inner,"outer_points":outer,"wall_thickness_mm":wall,
                       "meta":{"quarter":True,"row_span":"quarter","source_auto_angle_deg":driver["exit_angle_deg"]}}
            mesh_path = dest / "mesh.msh"
            build_grid_mesh(payload, mesh_spec("verify", cfg), mesh_path, cfg, mode="verify")
            info = mesh_data(mesh_path, 36)
            nodes, faces = source(mesh_path)
            dist, mapping = cKDTree(reference_nodes).query(nodes)
            def normalize(values):
                return sorted(map(tuple, np.sort(values, axis=1)))

            same = (len(nodes) == len(reference_nodes)
                    and len(set(mapping)) == len(mapping)
                    and normalize(mapping[faces]) == normalize(reference_faces))
            shift = np.linalg.norm(inner-old, axis=2)
            row.update(status="source-matched" if same and max(dist)*1000 < 0.001 else "source mismatch",
                       mesh=str(mesh_path.relative_to(ROOT)), mesh_sha256=digest(mesh_path),
                       experiment_id=sha256(inner.tobytes()+outer.tobytes()).hexdigest(),
                       source_drift_mm=float(max(dist)*1000), source_connectivity_equal=same,
                       geometry=geo, mesh_info=info,
                       upstream_sample_max_shift_mm=float(shift[:, :25].max()),
                       pointwise_sampling_note="station indices follow native parameter and are not physical correspondences",
                       max_sample_shift_mm=float(shift.max()),controls=asdict(replace(body,tmax=tmax)))
        except Exception as exc:
            row["error"]=f"{type(exc).__name__}: {exc}"
        print(name,row["status"],row.get("source_drift_mm"),row.get("error",""),flush=True)
    (output_dir/"manifest.json").write_text(json.dumps(out,indent=2),encoding="utf-8")


if __name__ == "__main__":
    main()
