"""Register or solve admitted full-balloon home-900 V11 fixed meshes.

Fixed fixtures have physical identities and regular run reports, without an
optimizer design space. Importing a measured response never calls the solver.
"""
from argparse import ArgumentParser
from dataclasses import asdict, replace
from hashlib import sha256
import math
from pathlib import Path
import shutil
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from hornlab_search.cli import _backend
from hornlab_search.config import load_config, mesh_spec, solve_spec
from hornlab_search.mesh.build import BBOX_MAX_M, BBOX_MIN_M, read_msh_summary
from hornlab_search.mesh.throat_check import fits_exit, throat_shape
from hornlab_search.mesh.topology import check_surface
from hornlab_search.objective.replay import _dispatch, load_brief_context
from hornlab_search.objective.scalar_v11 import CD_STATUS_CODES, V11_CD_TERM_KEYS, resolve_v11_weights
from hornlab_search.search import rundir
from hornlab_search.search.evaluate import (
    append_ndjson, collect_lib_shas, evaluation_to_row, metrics_from_response, metrics_to_json,
)
from hornlab_search.search.gpulock import gpu_lock
from hornlab_search.solve import worker
from hornlab_search.solve.base import balloon_grid_shape
from hornlab_search.solve.cache import load_response, save_response
from hornlab_search.types import Design, Evaluation, MeshResult, SolveOutcome
from tools.analysis.sculpted_v11_replay import PRIMARY

RUNS = ROOT / "runs"
CONFIG = ROOT / "examples/typologies/cd_v11_verify_2026-11-20/cd11v__crowe_x_osse_cd.yaml"
MEASUREMENTS = RUNS / "nights/hornfab_gpu8_2026-11-21/fixed"
ADMISSION = ROOT / "scratch/hornfab_gpu8_2026-11-21/fixed_meshes/admission.json"
MODE = "verify"  # The retained 51-frequency tier extends the standard verify grid.
FMAX_MESH_DOFS = 8900


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def locked_specs():
    cfg = load_config(CONFIG, brief=PRIMARY)
    spec = solve_spec(MODE, cfg)
    extra = {700., 750., 800., 850., 900., 950., 1000., 1100., 1200., 1300., 1400., 1500.,
             1650., 1800., 1950., 2100., 2250., 2400., 2550., 2700., 2850., 3000.}
    spec = replace(spec, freqs_hz=tuple(sorted(set(spec.freqs_hz) | extra)))
    if cfg.objective_version != 11 or spec.hash() != "62842a4a021e":
        raise ValueError("Resolved home-900 V11 observation or solver identity changed")
    return cfg, spec


def input_record(case, native_manifest):
    if native_manifest is not None:
        candidates = rundir.read_json(native_manifest)["candidates"]
        row = next((row for row in candidates if row["id"] == case), None)
        if (row is None or row["status"] != "source-matched"
                or not row["source_connectivity_equal"] or row["source_drift_mm"] > 0.001):
            raise ValueError(f"{case}: missing matched-source CPU admission")
        return dict(row, epw=6), native_manifest
    row = rundir.read_json(ADMISSION)["accepted"][case]
    return dict(row, mesh_sha256=row["info"]["sha256"]), ADMISSION


def physical_mesh(path, row, cfg):
    if digest(path) != row["mesh_sha256"]:
        raise ValueError("Mesh SHA does not match CPU admission")
    info, xyz, faces = read_msh_summary(path, return_arrays=True)
    if info["tag_names"] != {1: "SD1G0", 2: "SD1D1001"} or not info["tags"].get(2):
        raise ValueError("Expected quarter freestanding wall and driven source cap")
    if not BBOX_MIN_M <= max(np.ptp(xyz, axis=0)) <= BBOX_MAX_M:
        raise ValueError("Mesh coordinates outside metre-scale guard")
    fit, detail = fits_exit(throat_shape(path), 2 * cfg.brief["driver"]["exit_radius_mm"])
    if not fit or info["n_nodes_used"] > FMAX_MESH_DOFS:
        raise ValueError(f"Source fit or CUDA mesh budget failed: {detail}")
    check_surface(xyz, faces, "yz+xz")
    return MeshResult(str(path), info["n_triangles"], None, "1", "yz+xz", {}, tuple(info["bbox_m"]), 0.0)


def score_response(response, spec, mesh):
    obs = spec.observation
    grid = balloon_grid_shape(obs.balloon_points)
    if (response.backend != "beat_cuda" or not np.array_equal(response.freqs_hz, spec.freqs_hz)
            or response.spl_balloon_db is None or response.balloon_dirs is None
            or tuple(response.meta.get("balloon_grid", ())) != grid or len(response.balloon_dirs) != math.prod(grid)
            or len(response.h_angles_deg) != obs.angle_count or len(response.v_angles_deg) != obs.angle_count
            or any(getattr(response, field) is None for field in ("p_h", "p_v", "p_balloon", "z_throat"))):
        raise ValueError("Expected BEAT CUDA complex response on the locked cuts and full balloon")
    reference = load_response(MEASUREMENTS / "R2_6" / "response.npz")
    for axes in ("h_angles_deg", "v_angles_deg", "balloon_dirs"):
        if not np.array_equal(getattr(response, axes), getattr(reference, axes)):
            raise ValueError(f"Observation grid does not match measured R2: {axes}")
    brief = load_brief_context(PRIMARY)
    metrics = metrics_from_response(response, brief.target, mesh=mesh)
    score, terms = _dispatch(11, metrics, response, brief.target, brief.weights, brief.objective_params)
    status = next((name for name, code in CD_STATUS_CODES.items() if terms.get("cd_status_code") == code),
                  "unmeasurable")
    weights = resolve_v11_weights(brief.weights, brief.objective_params)
    weighted = {key: terms[key] * weight for key, weight in weights.items()}
    if (metrics.di_source != "balloon" or status != "balloon" or not math.isfinite(score)
            or any(not math.isfinite(weighted.get(key, math.nan)) for key in V11_CD_TERM_KEYS)
            or not math.isclose(math.fsum(weighted.values()), score, abs_tol=1e-10)):
        raise ValueError(f"Invalid V11 CD comparison: CD {status}, DI {metrics.di_source}")
    return score, terms, weighted, metrics, status


def measured_response(case, row, spec, cfg):
    saved = MEASUREMENTS / case
    result = rundir.read_json(saved / "result.json")
    driver = cfg.brief["driver"]
    source = {"mounting": "freestanding", "quarter": True, "radius_mm": driver["exit_radius_mm"],
              "cap": cfg.brief["source"]["cap"], "nominal_exit_deg": driver["exit_angle_deg"]}
    if (result is None or result["seconds"] <= 0 or result["brief_sha256"] != digest(PRIMARY)
            or result["mesh_sha256"] != row["mesh_sha256"] or result["solve_hash"] != spec.hash()
            or result["source_model"] != source):
        raise ValueError("Stored solve does not match admitted physical and score identity")
    return load_response(saved / "response.npz"), result, saved


def run(args):
    cfg, spec = locked_specs()
    row, manifest = input_record(args.case, args.native_manifest)
    path = ROOT / row["mesh"]
    mesh = physical_mesh(path, row, cfg)
    identity = row.get("experiment_id") or row.get("archive_design")
    design = Design("FREEFORM", {"fixed_mesh": {"case_identity": identity, "sha256": row["mesh_sha256"]}})
    key = f"{design.hash()}-{row['mesh_sha256'][:12]}-{spec.hash()}"
    index = RUNS / "fixed_sculpted_v11" / f"{key}.json"
    previous = rundir.read_json(index)
    if previous and (RUNS / previous["run_id"] / "best.json").is_file():
        print("Existing fixed-mesh observation:", RUNS / previous["run_id"])
        return
    if args.import_measured:
        response, stored, saved = measured_response(args.case, row, spec, cfg)
    if args.check:
        if args.import_measured:
            score_response(response, spec, mesh)
        print("Preflight passed:", args.case, key)
        return
    # Hold the canonical lock while checking duplicate admission and running BEM.
    # Registration imports bytes and does not need the GPU.
    from contextlib import nullcontext
    guard = nullcontext() if args.import_measured else gpu_lock(
        f"sculpted_v11 {args.case}", runs_root=RUNS, policy="refuse")
    with guard:
        previous = rundir.read_json(index)
        if previous and (RUNS / previous["run_id"] / "best.json").is_file():
            print("Existing fixed-mesh observation:", RUNS / previous["run_id"])
            return
        run_dir = rundir.new_run_dir(RUNS, MODE)
        print("Fixed V11 run:", run_dir, flush=True)
        try:
            if args.import_measured:
                outcome = SolveOutcome(True, response, stored["seconds"], stored.get("peak_vram_mib"), "")
                libs = stored["lib_shas"]
            else:
                worker.install_handlers()
                try:
                    outcome = _backend(cfg).solve(mesh, spec)
                finally:
                    worker.shutdown()
                if not outcome.ok or outcome.response is None:
                    raise RuntimeError(outcome.message)
                response, libs = outcome.response, collect_lib_shas()
            mesh.n_dof = response.n_dof
            j, terms, weighted, metrics, cd_status = score_response(response, spec, mesh)
            if args.import_measured and not math.isclose(j, stored["J"], abs_tol=1e-10):
                raise ValueError("Imported response differs from original V11 score")
            dest = run_dir / "designs" / design.hash()
            dest.mkdir(parents=True)
            shutil.copyfile(path, dest / "mesh.msh")
            if args.import_measured:
                shutil.copyfile(saved / "response.npz", dest / "response.npz")
            else:
                save_response(dest / "response.npz", response)
            rundir.write_json_atomic(dest / "design.json",
                                     {"family": design.family, "params": design.params, "design_hash": design.hash()})
            rundir.write_json_atomic(dest / "metrics.json", metrics_to_json(metrics))
            ev = Evaluation(design.hash(), design, row["mesh_sha256"][:12], spec.hash(),
                            j, terms, metrics, mesh, outcome, cached=args.import_measured)
            seconds = {"mesh": 0.0, "solve": 0.0 if args.import_measured else outcome.seconds,
                       "total": 0.0 if args.import_measured else outcome.seconds}
            cfg.raw["name"] = f"Sculpted V11 fixed mesh {args.case}"
            cfg.raw["family"] = design.family
            cfg.raw.pop("generator", None)
            cfg.raw.pop("seed_params", None)
            cfg.raw.pop("bounds", None)
            cfg.raw.pop("search", None)
            cfg.raw["brief"] = cfg.brief
            rundir.write_config_snapshot(run_dir, cfg)
            manifest_mesh_spec = replace(mesh_spec(MODE, cfg), epw=row["epw"])
            record = {"case": args.case, "geometry": row, "source": cfg.brief["source"],
                      "driver": cfg.brief["driver"], "symmetry": "yz+xz", "mounting": "freestanding",
                      "brief": cfg.brief, "brief_sha256": digest(PRIMARY), "objective_version": 11,
                      "solve_spec": asdict(spec), "solve_hash": spec.hash(), "mesh_spec": asdict(manifest_mesh_spec),
                      "cd_status": cd_status, "weighted_terms": weighted, "libs": libs,
                      "origin": str(saved) if args.import_measured else "new GPU solve",
                      "gpu_seconds": outcome.seconds, "response_sha256": digest(dest / "response.npz"),
                      "admission_manifest": str(manifest), "admission_sha256": digest(manifest)}
            rundir.write_json_atomic(dest / "fixed_mesh_provenance.json", record)
            rundir.write_json_atomic(dest / "status.json",
                                     dict(ok=True, objective=j, terms=terms, weighted_terms=weighted, key=key,
                                          mode=MODE, objective_version=11, cd_status=cd_status, seconds=seconds,
                                          cached=args.import_measured))
            row_out = evaluation_to_row(ev, MODE, 0, seconds, 11, lane="gpu", backend=spec.backend)
            row_out["fixed_candidate"] = True
            row_out["measured_in"] = record["origin"]
            append_ndjson(run_dir / "search.ndjson", row_out)
            rundir.write_best(run_dir, ev, MODE, 0)
            rundir.update_run_json(run_dir, config=cfg.raw, mode=MODE, backend=spec.backend, status="finished",
                                   algorithm="fixed_candidate", objective_version=11,
                                   best={"design_hash": design.hash(), "objective": j}, finished_utc=rundir.utc_now())
            index.parent.mkdir(exist_ok=True)
            rundir.write_json_atomic(index, {"run_id": run_dir.name, "key": key})
            print(f"run OK: {args.case} V11 J={j:.12f}, CD={cd_status}; output {run_dir}", flush=True)
        except Exception as exc:
            rundir.update_run_json(run_dir, status="failed", objective_version=11,
                                   stop_reason=f"{type(exc).__name__}: {exc}")
            raise


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("case")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--import-measured", action="store_true")
    mode_group.add_argument("--solve", action="store_true")
    parser.add_argument("--native-manifest", type=Path)
    parser.add_argument("--check", action="store_true")
    run(parser.parse_args())

