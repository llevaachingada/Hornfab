"""Write the WP 4.2 / 4.3 solve configs for one stored design (senior plan, 2026-11-17).

From ``runs/<run>/designs/<hash>`` it builds the canonical record, the unedited CONTROL and the
seven U3 variants (``hornlab_search.geometry.edits``), checks validity, and writes one config per
arm whose seed is the explicit record body (``design/generators/record_body``), so the normal
``hornlab-search run`` CLI solves exactly that surface. Nothing is solved here.

    python tools/analysis/u3_jobs.py runs/<run> <design_hash> --out examples/studies/u3_<lane>

Order on the GPU (owner approval, C6): control (WP 4.2, compare with the stored response) and,
only if it reproduces, the variants (WP 4.3). Use the verify tier (>= 29 frequencies).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def write_jobs(run: Path, design_hash: str, out: Path, *, wall_mm: float | None = None) -> dict:
    from hornlab_search.config import load_config
    from hornlab_search.design.generators import record_body as RB
    from hornlab_search.geometry import edits as E
    from hornlab_search.geometry import record as R
    from hornlab_search.types import Design
    cfg = load_config(run / "config.yaml")
    d = json.loads((run / "designs" / design_hash / "design.json").read_text(encoding="utf-8"))
    rec = R.record_for_design(Design(d["family"], d["params"]), cfg)
    t = float(wall_mm if wall_mm is not None else (rec.wall_thickness_mm or 3.0))
    angle = E.throat_half_angle_deg(rec)
    raw = yaml.safe_load((run / "config.yaml").read_text(encoding="utf-8"))
    bf = raw.get("brief_file")
    if bf and not Path(bf).is_absolute():
        cand = (run / bf).resolve()
        raw["brief_file"] = str(cand if cand.is_file() else (REPO / bf).resolve())
    env = (cfg.brief or {}).get("envelope") or {}
    env_mm = {k: float(env[v]) for k, v in (("width_mm", "max_mouth_w_mm"),
                                             ("height_mm", "max_mouth_h_mm"),
                                             ("depth_mm", "max_depth_mm")) if v in env}
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"source_run": run.name, "design_hash": design_hash, "record_digest": rec.digest(),
                "wall_thickness_mm": t, "source_auto_angle_deg": angle, "arms": {}}
    for name, v in [("control", rec), *E.u3_variants(rec).items()]:
        val = E.validity(v, rec, envelope_mm=env_mm, wall_thickness_mm=t)
        spec = RB.spec_from_record(v, wall_thickness_mm=t, source_auto_angle_deg=angle)
        arm = dict(raw)
        arm.pop("generator", None)
        arm["name"] = f"u3__{raw.get('name', 'host')}__{name}"
        arm["family"] = "FREEFORM"
        arm["seed_params"] = {"grid": spec}
        arm["bounds"] = {}
        path = out / f"{name}.yaml"
        path.write_text(yaml.safe_dump(arm, sort_keys=False), encoding="utf-8")
        manifest["arms"][name] = {"config": path.name, "valid": val["ok"],
                                  "digest": spec["rows"]["implementation_sha256"],
                                  "reach_mm": val.get("max_rms_change_outside_last5pct_mm"),
                                  "envelope_margins_mm": val.get("envelope_margins_mm")}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=float), encoding="utf-8")
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("design_hash")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--wall-mm", type=float)
    a = ap.parse_args(argv)
    m = write_jobs(a.run, a.design_hash, a.out, wall_mm=a.wall_mm)
    print(json.dumps({k: v for k, v in m.items() if k != "arms"}, indent=1, default=float))
    for k, v in m["arms"].items():
        print(f"  {k:16s} valid={v['valid']} reach={v['reach_mm']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
