"""Export the exact hornlab_mesher config for a run's top designs (no solves, no meshes).

For each of the ``--top N`` designs (unique ``design_hash``, lowest ``objective`` first) this writes:

* ``<hash>.mesher.json`` - the dict ``hornlab_search`` hands to ``hornlab_mesher``. It is produced
  by :func:`hornlab_search.design.families.to_mesher_config` (the same call ``mesh/build.py`` makes),
  so no key is re-derived here;
* ``<hash>.meta.json``   - family, params, J, objective_version, terms, brief name, lib_sha (plus
  run/config labels when the run snapshot carries them).

Families the formula mesher builds from a config (OSSE, R-OSSE, ICW, FREEFORM, LOOKUP) are exported.
Generator (point-grid) and CAD designs are listed in ``skipped.json`` with the reason: their
geometry is built by ``mesh/grid_build.py`` / ``mesh/step_build.py``, not by a mesher config.

Usage (from the repo root)::

    .venv\\Scripts\\python.exe tools/export_config.py --run runs/<run_dir> --top 10
    .venv\\Scripts\\python.exe tools/export_config.py --run runs/<run_dir> --top 10 --out scratch/cfg
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hornlab_search.config import load_config, mesh_spec  # noqa: E402
from hornlab_search.dataset.record import lib_sha_key  # noqa: E402
from hornlab_search.design import families  # noqa: E402
from hornlab_search.mesh.build import mounting_of, res_mm_for_spec  # noqa: E402
from hornlab_search.types import GeometryInvalidError, Design  # noqa: E402

#: Families whose geometry a mesher config describes. ``LOOKUP`` is in the mesher's own family set
#: even though this build's search does not generate it; a stored row would still be exportable.
CONFIG_FAMILIES = ("OSSE", "R-OSSE", "ICW", "FREEFORM", "LOOKUP")


def _rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return rows
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _finite(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def select_top(rows: list[dict], top: int) -> list[dict]:
    """Top ``top`` unique design hashes by objective. Failed/non-finite rows never rank."""
    best: dict[str, tuple[float, dict]] = {}
    for row in rows:
        if not row.get("ok"):
            continue
        design_hash = row.get("design_hash")
        objective = _finite(row.get("objective"))
        if not design_hash or objective is None:
            continue
        current = best.get(str(design_hash))
        if current is None or objective < current[0]:
            best[str(design_hash)] = (objective, row)
    ordered = sorted(best.values(), key=lambda pair: (pair[0], int(pair[1].get("n") or 0)))
    return [row for _objective, row in ordered[:max(int(top), 0)]]


def skip_reason(row: dict) -> str | None:
    """Why this row is not a formula-mesher config, or None when it is."""
    family = row.get("family")
    if family not in CONFIG_FAMILIES:
        return f"family {family!r} is not built from a mesher config"
    params = row.get("params")
    if isinstance(params, dict) and "grid" in params:
        return ("point-grid (generator) design: mesh/grid_build.py builds it at mesh time; "
                "there is no families.to_mesher_config dict")
    if isinstance(params, dict) and "cad" in params:
        return ("CAD recipe design: mesh/step_build.py builds the STEP/mesh; there is no "
                "families.to_mesher_config dict")
    return None


def _brief_name(cfg) -> str:
    brief = getattr(cfg, "brief", None)
    if isinstance(brief, dict) and brief.get("name"):
        return str(brief["name"])
    return ""


def export_run(run_dir: str | Path, top: int, out: str | Path) -> dict:
    """Write the config/meta files for one run. Returns a small summary document."""
    run_dir = Path(run_dir)
    out_dir = Path(out)
    config_path = run_dir / "config.yaml"
    if not config_path.is_file():
        raise FileNotFoundError(f"{config_path} not found (a run dir needs config.yaml)")
    cfg = load_config(config_path)
    snapshot: dict = {}
    run_json = run_dir / "run.json"
    if run_json.is_file():
        try:
            snapshot = json.loads(run_json.read_text(encoding="utf-8"))
        except ValueError:
            snapshot = {}
    mode = str(snapshot.get("mode") or "screen")
    mesh = mesh_spec(mode, cfg)  # type: ignore[arg-type]
    res = res_mm_for_spec(mesh, cfg)
    mounting = mounting_of(cfg)
    lib_shas = snapshot.get("lib_shas") if isinstance(snapshot.get("lib_shas"), dict) else {}
    lib_sha = lib_sha_key(lib_shas) if lib_shas else ""
    run_id = str(snapshot.get("run_id") or run_dir.name)
    config_name = str(snapshot.get("config_name") or cfg.name or "")
    brief = _brief_name(cfg)

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    skipped: list[dict] = []
    for row in select_top(_rows(run_dir / "search.ndjson"), top):
        design_hash = str(row["design_hash"])
        reason = skip_reason(row)
        if reason:
            skipped.append({"design_hash": design_hash, "family": row.get("family"),
                            "reason": reason})
            continue
        design = Design(family=row["family"], params=dict(row.get("params") or {}))
        # The exact output path evaluate() hands to build_mesh (mesh/build.py passes
        # out_dir/"mesh.msh" for the run's design directory).
        mesher_out = run_dir / "designs" / design_hash / "mesh.msh"
        try:
            mesher_config = families.to_mesher_config(design, mesh, res, mesher_out,
                                                      mounting=mounting)
        except GeometryInvalidError as exc:
            skipped.append({"design_hash": design_hash, "family": row.get("family"),
                            "reason": f"families.to_mesher_config refused it: {exc}"})
            continue
        meta = {
            "design_hash": design_hash,
            "family": row.get("family"),
            "params": row.get("params"),
            "J": row.get("objective"),
            "objective_version": row.get("objective_version", 1),
            "terms": row.get("terms"),
            "brief": brief,
            "lib_sha": lib_sha,
            "run_id": run_id,
            "config_name": config_name,
            "mode": mode,
        }
        (out_dir / f"{design_hash}.mesher.json").write_text(
            json.dumps(mesher_config, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        (out_dir / f"{design_hash}.meta.json").write_text(
            json.dumps(meta, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        written.append(design_hash)

    (out_dir / "skipped.json").write_text(
        json.dumps(skipped, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return {"run_dir": str(run_dir), "out": str(out_dir), "written": written,
            "skipped": skipped, "mode": mode}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="export_config.py",
        description="Export exact hornlab_mesher configs for a run's top designs (offline).",
    )
    parser.add_argument("--run", type=Path, required=True, help="run directory")
    parser.add_argument("--top", type=int, default=10, help="how many designs (default 10)")
    parser.add_argument("--out", type=Path, default=None,
                        help="output directory (default <run>/export_config)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = args.out if args.out is not None else args.run / "export_config"
    doc = export_run(args.run, args.top, out)
    print(f"{len(doc['written'])} config(s), {len(doc['skipped'])} skipped -> {doc['out']}")
    for item in doc["skipped"]:
        print(f"  skipped {item['design_hash']} ({item['family']}): {item['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
