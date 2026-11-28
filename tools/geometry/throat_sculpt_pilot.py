"""Throat-sculpt geometry bank and matched acoustic pilot (``throat_sculpt_v1`` over an osse_rollback parent).

Research lane: ``docs/research/typologies/sculpted_throat_2026-11-25/``.  One cases file names a parent config
(its brief, seed and spec ARE the matched control) and a list of cases (ts knobs, or a pinch-ratio TARGET that
is root-found on ``ts_c2``).  Subcommands:

* ``bank``  -- CPU only: resolve every case, section the analytic inner wall, mesh it with the pinned mesher
  (the same ``mesh.grid_build.build_grid_mesh`` a search uses), section the EMITTED wall triangles (source tag
  excluded) to prove the pinch survives meshing, and write ``bank.json`` / ``bank.csv`` / ``sections_*.png``.
* ``solve`` -- BEAT CPU or CUDA, one case at a time under its lane lock, on the brief's own
  mode solve spec (``--mode verify`` = the parent's published verify identity), V11 score through the same
  ``objective.replay._dispatch`` the search uses; ``--fmax`` adds an extended-band DIAGNOSTIC solve
  (mesh f_max raised; J is NOT comparable and is not reported as J). ``--epw`` refines the mesh
  on the same frequency grid and stores the result separately from the default mesh.

No search identity is created: designs are FREEFORM ``grid`` blocks whose hash includes the family digest.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "geometry"))

import throat_sections as TS  # noqa: E402

from hornlab_search.config import load_config, mesh_spec, solve_spec  # noqa: E402
from hornlab_search.design.generators import grid, throat_sculpt_family as FAM  # noqa: E402
from hornlab_search.types import Design  # noqa: E402

Z_STATIONS = (0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0, 60.0, 80.0)


# ----------------------------------------------------------------------------- cases
def load_cases(path: Path) -> dict:
    doc = yaml.safe_load(path.read_text())
    doc["_path"] = str(path)
    return doc


def _cfg(doc):
    return load_config(ROOT / doc["parent_config"])


def _seed(doc, cfg):
    seed = dict(cfg.raw["seed_params"])
    seed.update(doc.get("parent_overrides") or {})
    return seed


def _spec(doc):
    s = doc.get("spec") or {}
    rows = {"type": FAM.KIND, "parent_rows": {"type": "osse_rollback"}}
    if "core_step_mm" in s:
        rows["core_step_mm"] = float(s["core_step_mm"])
    return {"rows": rows, "n_phi": int(s.get("n_phi", 25)), "n_s": int(s.get("n_s", 64)),
            "wall_thickness_mm": float(s.get("wall_thickness_mm", 3.0))}


def _waist_for(spec, seed, ts, brief, psi_row):
    block = FAM.design_params(spec, {**seed, **{"g_" + k: v for k, v in ts.items()}}, brief)["grid"]
    a = FAM.resolve_grid(block, brief)["meta"]["throat_sculpt_achieved"]
    return a["h_waist_min_mm"] if psi_row == "h" else a["v_waist_min_mm"]


def resolve_ts(case, spec, seed, brief, r0):
    """Case ts dict; a ``target_waist`` {plane, ratio} root-finds |ts_c2| (sign from plane)."""
    ts = dict(case.get("ts") or {})
    tgt = case.get("target_waist")
    if not tgt:
        return ts
    plane, ratio = tgt["plane"], float(tgt["ratio"])
    sign = -1.0 if plane == "h" else 1.0
    lo, hi = 0.0, 0.8
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        try:
            w = _waist_for(spec, seed, {**ts, "ts_c2": sign * mid}, brief, plane)
        except Exception:          # noqa: BLE001 - an illegal amplitude: search lower
            hi = mid
            continue
        if w / r0 > ratio:
            lo = mid
        else:
            hi = mid
    ts["ts_c2"] = round(sign * 0.5 * (lo + hi), 6)
    return ts


def build(case, doc, cfg):
    """-> (design_block, geometry dict for build_grid_mesh, ts or None)."""
    brief = cfg.brief
    seed = _seed(doc, cfg)
    if case.get("parent"):
        gen = cfg.raw["generator"]
        pspec = {k: v for k, v in gen.items() if k in ("rows", "n_phi", "n_s", "wall_thickness_mm", "span")}
        block = grid.design_params(pspec, seed, brief)["grid"]
        inner, meta = grid.rows_grid_points({k: v for k, v in block.items() if k != "knobs"}, block["knobs"], brief)
        return block, {"inner_points": inner, "meta": meta,
                       "wall_thickness_mm": float(block.get("wall_thickness_mm", 3.0))}, None
    spec = _spec(doc)
    r0 = float(brief["driver"]["exit_radius_mm"])
    ts = resolve_ts(case, spec, seed, brief, r0)
    block = FAM.design_params(spec, {**seed, **{"g_" + k: v for k, v in ts.items()}}, brief)["grid"]
    res = FAM.resolve_grid(block, brief)
    geo = {"inner_points": res["inner_points"], "meta": res["meta"],
           "wall_thickness_mm": float(block.get("wall_thickness_mm", 3.0))}
    if "outer_points" in res:
        geo["outer_points"] = res["outer_points"]
    return block, geo, ts


# ----------------------------------------------------------------------------- geometry
def analytic_sections(inner, r0, zmax):
    z = sorted(set([z for z in Z_STATIONS if z <= zmax] + list(np.arange(0.0, zmax + 1e-9, 1.0))))
    phis, R = TS.grid_r_of_z(inner, z)
    rows = []
    for zz, r in zip(z, R):
        m = TS.section_metrics(r, phis, r0)
        m["z_mm"] = float(zz)
        rows.append(m)
    return {"rows": rows, "z": np.asarray(z), "phis": phis, "r": R,
            "occlusion_fraction": TS.occlusion_fraction(R, phis, r0)}


def wall_triangles_mm(msh_path):
    """Air-facing + outer wall triangles (every physical surface EXCEPT the source tag 2), mirrored to 4 quadrants."""
    import gmsh
    gmsh.initialize(["", "-v", "0"])
    try:
        gmsh.open(str(msh_path))
        tags, coords, _ = gmsh.model.mesh.getNodes()
        xyz = np.zeros((int(tags.max()) + 1, 3))
        xyz[tags.astype(int)] = coords.reshape(-1, 3)
        tris = []
        for dim, ptag in gmsh.model.getPhysicalGroups(2):
            if ptag == 2:
                continue
            for ent in gmsh.model.getEntitiesForPhysicalGroup(dim, ptag):
                et, _et, en = gmsh.model.mesh.getElements(2, ent)
                for t, nodes in zip(et, en):
                    if t == 2:
                        tris.append(xyz[np.asarray(nodes, int).reshape(-1, 3)])
    finally:
        gmsh.finalize()
    T = np.concatenate(tris) * 1000.0
    full = [T]
    for sx, sy in ((-1, 1), (1, -1), (-1, -1)):
        full.append(T * np.array([sx, sy, 1.0]))
    return np.concatenate(full)


def mesh_case(geo, cfg, mode, out_dir, f_max=None, epw=None):
    from hornlab_search.mesh import grid_build
    ms = mesh_spec(mode, cfg)
    if f_max:
        ms = replace(ms, f_max_hz=float(f_max))
    if epw is not None:
        ms = replace(ms, epw=epw)
    out_dir.mkdir(parents=True, exist_ok=True)
    g = {k: v for k, v in geo.items()}
    return grid_build.build_grid_mesh(g, ms, out_dir / "mesh.msh", cfg, mode=mode), ms


def _row_summary(name, purpose, ts, an, em, mres, meta):
    a = meta.get("throat_sculpt_achieved") or {}
    r = {"case": name, "purpose": purpose, "ts": ts,
         "analytic_r_min_mm": min(x["r_min_mm"] for x in an["rows"]),
         "analytic_pinch_ratio": min(x["pinch_ratio"] for x in an["rows"]),
         "analytic_min_convexity": min(x["convexity"] for x in an["rows"]),
         "analytic_occlusion": an["occlusion_fraction"],
         "mesh_r_min_mm": None if em is None else min(x["r_min_mm"] for x in em["rows"]),
         "mesh_pinch_ratio": None if em is None else min(x["pinch_ratio"] for x in em["rows"]),
         "mesh_occlusion": None if em is None else em["occlusion_fraction"],
         "n_triangles": None if mres is None else mres.n_triangles,
         "res_mm": None if mres is None else dict(mres.res_mm),
         "mouth_w_mm": meta.get("mouth_w_mm"), "mouth_h_mm": meta.get("mouth_h_mm"),
         "depth_mm": meta.get("x_span_mm"), "achieved": a}
    rz = min(an["rows"], key=lambda x: x["r_min_mm"])
    r.update({"r_min_z_mm": rz["z_mm"], "r_min_phi_deg": rz["phi_r_min_deg"],
              "waist_h_mm": min(x["r_h_mm"] for x in an["rows"]), "waist_v_mm": min(x["r_v_mm"] for x in an["rows"]),
              "area_ratio_at_waist": rz["area_ratio_src"]})
    return r


def cmd_bank(args):
    doc = load_cases(Path(args.cases))
    cfg = _cfg(doc)
    r0 = float(cfg.brief["driver"]["exit_radius_mm"])
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows, resolved = [], {}
    for case in doc["cases"]:
        name = case["id"]
        if args.only and name not in args.only:
            continue
        t0 = time.time()
        try:
            block, geo, ts = build(case, doc, cfg)
        except Exception as exc:  # noqa: BLE001 - a refused case is a bank result
            rows.append({"case": name, "purpose": case.get("purpose", ""), "status": "refused",
                         "error": f"{type(exc).__name__}: {exc}"})
            print(f"{name}: REFUSED {exc}", flush=True)
            continue
        an = analytic_sections(geo["inner_points"], r0, args.zmax)
        em, mres, status, err = None, None, "geometry_ok", ""
        if not args.no_mesh:
            try:
                mres, _ms = mesh_case(geo, cfg, args.mode, out / "meshes" / name)
                tri = wall_triangles_mm(mres.path)
                zs = sorted(set([z for z in Z_STATIONS if z <= args.zmax] + list(np.arange(0.5, args.zmax + 1e-9, 1.0))))
                em = TS.analyse(tri, r0, zs)
                status = "meshed"
            except Exception as exc:  # noqa: BLE001
                status, err = "mesh_failed", f"{type(exc).__name__}: {exc}"
        row = _row_summary(name, case.get("purpose", ""), ts, an, em, mres, geo["meta"])
        row.update(status=status, error=err, design_hash=Design("FREEFORM", {"grid": block}).hash(),
                   seconds=round(time.time() - t0, 2))
        rows.append(row)
        resolved[name] = {"block": block, "ts": ts}
        TS.plot_sections(an, out / f"sections_{name}.png", r0, f"{name}: analytic inner wall")
        np.savez_compressed(out / f"radii_{name}.npz", z_mm=an["z"], phi_rad=an["phis"], r_mm=an["r"])
        print(f"{name}: {status} pinch {row['analytic_pinch_ratio']:.3f} (mesh "
              f"{row['mesh_pinch_ratio'] if row['mesh_pinch_ratio'] is None else round(row['mesh_pinch_ratio'], 3)}) "
              f"z {row['r_min_z_mm']:.1f} phi {row['r_min_phi_deg']:.0f} occl {row['analytic_occlusion']:.3f} "
              f"tri {row['n_triangles']} {row['seconds']}s {err}", flush=True)
    (out / "bank.json").write_text(json.dumps({"cases_file": doc["_path"], "parent_config": doc["parent_config"],
                                               "rows": rows, "resolved": resolved}, indent=1, default=float))
    keys = ["case", "status", "analytic_pinch_ratio", "mesh_pinch_ratio", "r_min_z_mm", "r_min_phi_deg",
            "waist_h_mm", "waist_v_mm", "area_ratio_at_waist", "analytic_min_convexity", "analytic_occlusion",
            "mesh_occlusion", "n_triangles", "design_hash", "purpose"]
    with open(out / "bank.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(keys)
        for r in rows:
            w.writerow([(f"{r.get(k):.4g}" if isinstance(r.get(k), float) else r.get(k, "")) for k in keys])
    return 0


# ----------------------------------------------------------------------------- acoustics
def _brief_path(doc):
    raw = yaml.safe_load((ROOT / doc["parent_config"]).read_text())
    return ((ROOT / doc["parent_config"]).parent / raw["brief_file"]).resolve()


def cmd_solve(args):
    from hornlab_search.cli import _backend
    from hornlab_search.objective.replay import _dispatch, load_brief_context
    from hornlab_search.search.evaluate import metrics_from_response, metrics_to_json
    from hornlab_search.search.gpulock import gpu_lock
    from hornlab_search.solve import worker
    from hornlab_search.solve.cache import save_response

    import os
    from hornlab_search.search.gpulock import cpu_lane_lock
    from hornlab_search.solve.base import get_backend

    doc = load_cases(Path(args.cases))
    cpu = args.backend in ("beat_cpu", "bempp_cpu")
    if cpu:
        # Two-lane rule: the CPU lane owns its own BEAT worker registry and never touches GPU hosts.
        os.environ.setdefault("HORNLAB_BEAT_WORKER_DIR", str(ROOT / "runs" / "lanes" / "cpu" / "workers"))
        cfg = load_config(ROOT / doc["parent_config"], backend=args.backend)
    else:
        cfg = _cfg(doc)
    brief_ctx = load_brief_context(_brief_path(doc))
    spec = solve_spec(args.mode, cfg)
    tag = args.mode + ("_cpu" if cpu else "")
    if args.fmax:
        lo = spec.freqs_hz[-1]
        extra = np.geomspace(lo, args.fmax, args.n_extra + 1)[1:]
        spec = replace(spec, freqs_hz=tuple(sorted(set(spec.freqs_hz) | {round(float(f), 2) for f in extra})))
        tag = f"{tag}_f{int(args.fmax)}"
    if args.epw is not None:
        epw_label = str(args.epw).removesuffix(".0")
        tag = f"{tag}_epw{epw_label}"
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    res_path = out / f"pilot_{tag}.json"
    done = json.loads(res_path.read_text()) if res_path.is_file() else {"solve_hash": spec.hash(), "rows": {}}
    if done["solve_hash"] != spec.hash():
        raise ValueError(f"{res_path} has a different solve grid or observation spec; choose a new --out")
    worker.install_handlers()
    try:
        lock = (cpu_lane_lock(f"throat_sculpt_pilot {tag}", runs_root=ROOT / "runs") if cpu else
                gpu_lock(f"throat_sculpt_pilot {tag}", runs_root=ROOT / "runs", policy="refuse"))
        with lock:
            backend = (get_backend(args.backend, timeout_s=float(cfg.solve.timeout_s), julia_threads=args.julia_threads)
                       if args.backend == "beat_cpu" else _backend(cfg))
            for case in doc["cases"]:
                name = case["id"]
                if (args.only and name not in args.only) or name in done["rows"]:
                    continue
                t0 = time.time()
                try:
                    block, geo, ts = build(case, doc, cfg)
                    mres, ms = mesh_case(geo, cfg, args.mode, out / f"solve_{tag}" / name,
                                         f_max=args.fmax, epw=args.epw)
                    outcome = backend.solve(mres, spec)
                    if not outcome.ok or outcome.response is None:
                        raise RuntimeError(outcome.message)
                    resp = outcome.response
                    mres.n_dof = resp.n_dof
                    metrics = metrics_from_response(resp, brief_ctx.target, mesh=mres)
                    j, terms = _dispatch(11, metrics, resp, brief_ctx.target, brief_ctx.weights,
                                         brief_ctx.objective_params)
                    save_response(out / f"solve_{tag}" / name / "response.npz", resp)
                    row = {"ok": True, "J_v11": float(j) if not args.fmax else None,
                           "J_v11_extended_band_NOT_COMPARABLE": float(j) if args.fmax else None,
                           "terms": {k: float(v) for k, v in terms.items() if isinstance(v, (int, float))},
                           "metrics": metrics_to_json(metrics), "n_dof": int(resp.n_dof),
                           "n_triangles": int(mres.n_triangles), "solve_s": float(outcome.seconds),
                           "design_hash": Design("FREEFORM", {"grid": block}).hash(), "ts": ts,
                           "mesh_f_max_hz": ms.f_max_hz, "mesh_epw": ms.epw,
                           "backend": args.backend, "solve_hash": spec.hash(), "wall_s": round(time.time() - t0, 1)}
                    z = np.asarray(resp.z_throat)
                    row["z_throat"] = {"freqs_hz": [float(f) for f in resp.freqs_hz],
                                       "re": [float(v) for v in np.real(z).reshape(-1)[: len(resp.freqs_hz)]],
                                       "im": [float(v) for v in np.imag(z).reshape(-1)[: len(resp.freqs_hz)]]}
                    print(f"{name}: J {j:.4f} dof {resp.n_dof} {outcome.seconds:.1f}s", flush=True)
                except Exception as exc:  # noqa: BLE001 - recorded, next case
                    row = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                    print(f"{name}: FAILED {exc}", flush=True)
                done["rows"][name] = row
                res_path.write_text(json.dumps(done, indent=1, default=float))
    finally:
        worker.shutdown(verify=not cpu)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bank")
    b.add_argument("cases"); b.add_argument("--out", required=True)
    b.add_argument("--mode", default="verify"); b.add_argument("--zmax", type=float, default=80.0)
    b.add_argument("--no-mesh", action="store_true"); b.add_argument("--only", nargs="*")
    s = sub.add_parser("solve")
    s.add_argument("cases"); s.add_argument("--out", required=True)
    s.add_argument("--mode", default="verify"); s.add_argument("--only", nargs="*")
    s.add_argument("--fmax", type=float, default=None); s.add_argument("--n-extra", type=int, default=8)
    s.add_argument("--epw", type=float, help="override mesh elements per wavelength")
    s.add_argument("--backend", default="beat_cuda", choices=("beat_cuda", "beat_cpu"))
    s.add_argument("--julia-threads", type=int, default=4)
    a = ap.parse_args(argv)
    if a.cmd == "solve" and a.epw is not None and (not math.isfinite(a.epw) or a.epw <= 0.0):
        s.error("--epw must be a finite positive number")
    return cmd_bank(a) if a.cmd == "bank" else cmd_solve(a)


if __name__ == "__main__":
    raise SystemExit(main())
