"""Record shadow gate and history records (senior plan WP 3.3 + 3.4, 2026-11-17).

For every design in one or more run dirs: rebuild the canonical surface record (contract v2,
``hornlab_search.geometry.record``) WITHOUT meshing, compute signed envelope margins against the
run's brief, and compare with the stored outcome. Read-only: writes one JSONL of records and a
summary JSON to ``--out``; never touches ``runs/``.

Disagreement classes (the shadow-gate evidence an owner reads before any switch):
  * ``record_inside_but_refused``  - row refused for the envelope, record margins all >= 0
  * ``record_outside_but_ok``      - row admitted (ok or solved), record margin < 0
  * ``record_failed``              - the record could not be built (typed refusal or error)

Pre-mesh refused generator designs carry only ``_knobs``: they are re-materialised from the run's
generator block (envelope estimate bypassed) so their record can be judged.

    python tools/analysis/record_shadow.py runs/<run> [runs/<run2> ...] --out scratch/rec_shadow
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

ENVELOPE_KEYS = {"width_mm": "max_mouth_w_mm", "height_mm": "max_mouth_h_mm",
                 "depth_mm": "max_depth_mm"}


def brief_envelope(brief: dict | None) -> dict:
    env = (brief or {}).get("envelope") or {}
    return {k: float(env[v]) for k, v in ENVELOPE_KEYS.items() if v in env}


def _design_for(row_params: dict, family: str, cfg):
    from hornlab_search.design.generated import GENERATOR_ERROR_KEY, materialize
    from hornlab_search.types import Design
    if GENERATOR_ERROR_KEY in row_params:
        knobs = row_params.get("_knobs")
        if not knobs or not getattr(cfg, "generator", None):
            raise ValueError("refused generator design without knobs/generator block")
        return Design("FREEFORM", materialize(cfg.generator, knobs, cfg.brief)), "rematerialised"
    return Design(family, row_params), "stored"


def classify(kind: str, ok: bool, margins: dict, tol_mm: float = 0.5) -> str:
    vals = [v for v in margins.values() if v is not None]
    inside = all(v >= -tol_mm for v in vals)
    if kind == "invalid_envelope" and inside:
        return "record_inside_but_refused"
    if (ok or kind not in ("invalid_envelope", "invalid_geometry")) and not inside:
        return "record_outside_but_ok"
    return "agree"


def scan_run(run_dir: Path, out_f, counts: dict) -> None:
    from hornlab_search.config import load_config
    from hornlab_search.geometry import record as R
    cfg = load_config(run_dir / "config.yaml")
    env = brief_envelope(cfg.brief)
    rows = {}
    nd = run_dir / "search.ndjson"
    if nd.is_file():
        for line in nd.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.setdefault(r.get("design_hash"), r)
    for ddir in sorted((run_dir / "designs").glob("*")):
        dj = ddir / "design.json"
        if not dj.is_file():
            continue
        d = json.loads(dj.read_text(encoding="utf-8"))
        h = d.get("design_hash") or ddir.name
        row = rows.get(h) or {}
        kind, ok = str(row.get("kind") or ""), bool(row.get("ok"))
        rec_out = {"run": run_dir.name, "design_hash": h, "kind": kind, "ok": ok}
        try:
            design, how = _design_for(d.get("params") or {}, d.get("family", "FREEFORM"), cfg)
            rec = R.record_for_design(design, cfg)
            desc = R.descriptors(rec)
            acoustic = R.envelope_margins(rec, env, include_wall=False)
            build = R.envelope_margins(rec, env, include_wall=True)
            cls = classify(kind, ok, build)
            rec_out.update({"how": how, "route": rec.route, "record_digest": rec.digest(),
                            "sampler_version": rec.sampler_version,
                            "mouth_width_mm": desc["mouth_width_mm"],
                            "mouth_height_mm": desc["mouth_height_mm"],
                            "depth_mm": desc["depth_mm"], "rollback": desc["rollback"],
                            "margins_acoustic_mm": acoustic, "margins_build_mm": build,
                            "shadow": cls})
        except Exception as exc:  # noqa: BLE001 - every failure is reported, never hidden
            cls = "record_failed"
            rec_out.update({"shadow": cls, "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                            "reason": getattr(exc, "reason", None)})
        counts[cls] = counts.get(cls, 0) + 1
        out_f.write(json.dumps(rec_out, default=float) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    counts: dict = {}
    failed_runs = []
    with (a.out / "records.jsonl").open("w", encoding="utf-8") as f:
        for run in a.runs:
            try:
                scan_run(run, f, counts)
            except Exception as exc:  # noqa: BLE001
                failed_runs.append({"run": str(run), "error": f"{type(exc).__name__}: {exc}"[:300]})
    summary = {"runs": len(a.runs), "counts": counts, "failed_runs": failed_runs}
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
