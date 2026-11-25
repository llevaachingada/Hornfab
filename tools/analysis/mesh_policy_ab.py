"""Build mesh-only policy arms for one saved design, then audit each mesh (CPU only).

This is the M0/M1/M2/M3/M4 machinery for the 2026-11-23 variable-mesh pass: the same saved
``design.json`` is rebuilt under each mesh policy, with no solver, no GPU and no cache, so the
triangle count, DOF estimate, build time and regional edge distribution are directly comparable.

Arms are written as ``FACTOR:EPW_MULTIPLIER``; the base ``epw`` comes from the run's config.yaml.
The screen frequency grid is untouched: ``f_max_hz`` follows from the selected mode exactly as
production does, and only ``mesh.epw``/``mesh.rear_res_factor`` change.

Usage::

    .venv\\Scripts\\python.exe tools/analysis/mesh_policy_ab.py \\
        --run runs/<run dir> --design <design hash> --out <scratch dir> \\
        --arms 1.0:1,1.5:1,2.0:1,1.5:1.5,1.5:2

Writes ``<out>/mesh_policy_ab.json``, ``<out>/MESH_POLICY_AB.csv`` and
``<out>/MESH_REGIONS.csv`` (one row per arm x region). Read-only with respect to runs/dataset.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hornlab_search.config import load_config, mesh_spec  # noqa: E402
from hornlab_search.mesh import build as mesh_build  # noqa: E402
from hornlab_search.types import Design  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "tools" / "analysis"))
import mesh_region_audit as region_audit  # noqa: E402

TOOL = "mesh_policy_ab"


def _parse_arms(text: str) -> list[tuple[float, float]]:
    arms = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        factor_s, epw_s = part.split(":", 1)
        factor, epw = float(factor_s), float(epw_s)
        if factor <= 0 or epw <= 0:
            raise ValueError(f"arm {part!r} needs positive factor and epw multiplier")
        arms.append((factor, epw))
    if not arms:
        raise ValueError("no arms given")
    return arms


def _load_design(run: Path, design_hash: str) -> Design:
    path = run / "designs" / design_hash / "design.json"
    if not path.is_file():
        raise FileNotFoundError(f"no design.json at {path}")
    d = json.loads(path.read_text(encoding="utf-8"))
    return Design(family=str(d["family"]), params=dict(d["params"]))


def _arm_name(factor: float, epw_mult: float) -> str:
    return f"rear{factor:g}_epw{epw_mult:g}"


def run_arm(cfg, design: Design, factor: float, epw_mult: float, out_dir: Path) -> dict:
    mesh_cfg = replace(
        cfg.mesh,
        rear_res_factor=float(factor),
        epw=float(cfg.mesh.epw) * float(epw_mult),
    )
    cfg_arm = replace(cfg, mesh=mesh_cfg)
    spec = mesh_spec("screen", cfg_arm)
    arm_dir = out_dir / _arm_name(factor, epw_mult)
    result = mesh_build.build_mesh(design, spec, cfg_arm, arm_dir, mode="screen")
    report = region_audit.build_report(arm_dir, epw=spec.epw, fmax=spec.f_max_hz,
                                      dof_per_triangle=cfg.mesh.dof_per_triangle)
    return {
        "arm": arm_dir.name,
        "rear_res_factor": float(factor),
        "epw_multiplier": float(epw_mult),
        "epw": float(spec.epw),
        "f_max_hz": float(spec.f_max_hz),
        "n_triangles": int(result.n_triangles),
        "n_vertices": int(report["n_vertices"]),
        "dof_estimate": report["dof_estimate"],
        "mesh_seconds": float(result.seconds),
        "res_mm": report["res_mm"],
        "regions": report["regions"],
        "report": report,
        "mesh_path": str(arm_dir / "mesh.msh"),
    }


def mesh_result_for(arm: dict):
    """Solver-facing MeshResult for a built arm (formula route metadata)."""
    from hornlab_search.types import MeshResult

    meta = json.loads((Path(arm["mesh_path"]).parent / "mesh_meta.json").read_text())
    result = meta.get("result") or {}
    return MeshResult(
        path=str(arm["mesh_path"]), n_triangles=int(arm["n_triangles"]), n_dof=None,
        quadrants=str(result.get("quadrants") or "1"),
        symmetry_plane=result.get("symmetry_plane"),
        res_mm=dict(result.get("res_mm") or {}),
        bbox_m=tuple(result.get("bbox_m") or (0,) * 6), seconds=0.0)


AB_COLUMNS = [
    "run", "design", "arm", "rear_res_factor", "epw_multiplier", "epw", "f_max_hz",
    "n_triangles", "n_vertices", "dof_estimate", "mesh_seconds",
    "res_throat_mm", "res_mouth_mm", "res_rear_mm",
    "inner_p50_mm", "throat_p50_mm", "mouth_p50_mm", "outer_p50_mm",
    "inner_triangles", "outer_triangles", "unknown_fraction",
]


def _region(arm: dict, name: str) -> dict:
    return next((r for r in arm["regions"] if r["region"] == name), {})


def _ab_row(run: str, design: str, arm: dict) -> dict:
    return {
        "run": run,
        "design": design,
        **{k: arm[k] for k in (
            "arm", "rear_res_factor", "epw_multiplier", "epw", "f_max_hz",
            "n_triangles", "n_vertices", "dof_estimate", "mesh_seconds")},
        "res_throat_mm": arm["res_mm"].get("throat"),
        "res_mouth_mm": arm["res_mm"].get("mouth"),
        "res_rear_mm": arm["res_mm"].get("rear"),
        "inner_p50_mm": _region(arm, "inner_bore").get("edge_mm_p50"),
        "throat_p50_mm": _region(arm, "throat_transition").get("edge_mm_p50"),
        "mouth_p50_mm": _region(arm, "mouth_lip").get("edge_mm_p50"),
        "outer_p50_mm": _region(arm, "outer_shell").get("edge_mm_p50"),
        "inner_triangles": _region(arm, "inner_bore").get("n_triangles"),
        "outer_triangles": _region(arm, "outer_shell").get("n_triangles"),
        "unknown_fraction": arm["report"]["unknown_triangle_fraction"],
    }


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run", required=True, help="run directory (holds config.yaml and designs/)")
    ap.add_argument("--design", required=True, help="design hash under <run>/designs/")
    ap.add_argument("--out", required=True, help="scratch output directory")
    ap.add_argument("--arms", default="1.0:1,1.5:1,2.0:1,1.5:1.5",
                    help="comma list FACTOR:EPW_MULTIPLIER (default M0..M3)")
    args = ap.parse_args(argv)

    run = Path(args.run).resolve()
    design = _load_design(run, args.design)
    cfg = load_config(run / "config.yaml")
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    arms = []
    for factor, epw_mult in _parse_arms(args.arms):
        print(f"building {run.name}/{args.design} arm {_arm_name(factor, epw_mult)} ...",
              flush=True)
        arm = run_arm(cfg, design, factor, epw_mult, out_dir)
        arms.append(arm)
        print(f"  {arm['n_triangles']} triangles, {arm['n_vertices']} vertices, "
              f"{arm['mesh_seconds']:.2f} s", flush=True)

    payload = {
        "tool": TOOL,
        "run": str(run),
        "design": args.design,
        "family": design.family,
        "design_hash": design.hash(),
        "config_sha": getattr(cfg, "config_sha", None),
        "arms": [{k: v for k, v in arm.items() if k != "report"} for arm in arms],
    }
    (out_dir / "mesh_policy_ab.json").write_text(
        json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")

    with (out_dir / "MESH_POLICY_AB.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=AB_COLUMNS)
        writer.writeheader()
        for arm in arms:
            row = _ab_row(run.name, args.design, arm)
            writer.writerow({k: _fmt(v) for k, v in row.items()})

    region_rows = []
    for arm in arms:
        for region in arm["report"]["regions"]:
            region_rows.append({
                "run": run.name, "design": args.design, "arm": arm["arm"],
                "rear_res_factor": arm["rear_res_factor"], "epw": arm["epw"],
                **{k: v for k, v in region.items()},
            })
    if region_rows:
        columns = list(region_rows[0].keys())
        with (out_dir / "MESH_REGIONS.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=columns)
            writer.writeheader()
            for row in region_rows:
                writer.writerow({k: _fmt(v) for k, v in row.items()})
    print(f"wrote {out_dir / 'MESH_POLICY_AB.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

