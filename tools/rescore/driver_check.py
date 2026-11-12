"""Driver-file readiness audit (report-only; NO code change to any driver model).

Walks ``examples/drivers/*.yaml`` and reports, for every file (``_template.yaml`` included but
flagged as a template):

* the dry-moving-mass status: ``mmd_g`` published (preferred everywhere), ``mms_g`` published
  with an ``air_load_g`` split, or Mms only (the documented LF-optimism caveat), or none;
* whether the datasheet ``source`` URL is present;
* whether a published sensitivity is present, in whichever schema the file uses:
  ``published_sensitivity_db`` (+ ``published_sensitivity_condition``) for the P12
  lumped-driver schema, ``sens_db_2v83`` for the MEH cone schema, ``sens_db_1w`` for the MEH
  compression-driver schema — with the convention named in the table;
* which repo loader(s) accept the file (``driver.compression.CompressionDriver`` = P12 lumped
  model; ``meh.drivers.ConeDriver`` / ``meh.drivers.CDSource`` = MEH C7/C8 schema).

Sensitivity prediction status (why this tool does NOT print a predicted-vs-datasheet dB table):
``hornlab_search.driver.compression.drive()`` DOES expose a sensitivity prediction (2.83 V /
``ref_distance_m`` on-axis SPL, band-averaged with ``band_mean_db``), but it needs a stored
``Response`` carrying ``meta['physical_tag_areas_m2']`` (``metrics.loudness.throat_area_m2``).
The single-channel dataset rows do not store that metadata (``shard-*.jsonl`` carries
``mesh.area_m2`` for the whole surface only), and the only rows that DO carry ``tag_areas_m2``
are the two-channel MEH rows (``channel_tags: [2, 10]``), where the single-piston ``drive()``
does not apply without a network-level model that does not exist yet. A ``pi*exit_radius^2``
stand-in for the throat area would bias the prediction by more than 2 dB (the OSSE/R-OSSE
throat is an ellipse; measured 24 x 36 mm on a 36 mm brief), so no honest dB comparison is
possible from the dataset alone tonight; a flag produced that way would be an artefact of the
approximation, not of the driver model. Owner follow-up: run the comparison inside a verify
run directory, where ``run.json`` + ``designs/*/mesh.msh`` let the real tag areas reach
``Response.meta``. Recorded in the evidence doc of 2026-11-12.

Usage (from the repo root)::

    .venv\\Scripts\\python.exe tools/rescore/driver_check.py [--out scratch/driver_check]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Callable

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DRIVERS_DIR = REPO_ROOT / "examples" / "drivers"

TEMPLATE_FILE = "_template.yaml"

#: Published-sensitivity key groups, one per schema, with the measuring convention each implies.
SENSitivity_SOURCES = (
    ("published_sensitivity_db", "2.83 V / 1 m (P12 schema; condition in published_sensitivity_condition)"),
    ("sens_db_2v83", "2.83 V / 1 m (MEH cone schema)"),
    ("sens_db_1w", "1 W / 1 m (MEH compression schema)"),
)


def _url_ok(raw: dict) -> bool:
    s = str(raw.get("source") or "").strip()
    return s.startswith(("http://", "https://"))


def _mass_status(raw: dict) -> str:
    if raw.get("mmd_g") is not None:
        return "mmd_g (dry, published)"
    if raw.get("mms_g") is None:
        return "MISSING (no mmd_g, no mms_g)"
    if raw.get("air_load_g") is not None:
        return "mms_g + air_load_g split"
    return "Mms only (Mmd missing; LF level + excursion optimistic)"


def _sensitivity(raw: dict) -> tuple[bool, str, str]:
    for key, convention in SENSitivity_SOURCES:
        if raw.get(key) is not None:
            cond = ""
            if key == "published_sensitivity_db" and raw.get("published_sensitivity_condition"):
                cond = str(raw["published_sensitivity_condition"]).strip()
            return True, f"{float(raw[key]):.1f} dB ({convention})", cond
    return False, "MISSING (no published_sensitivity_db / sens_db_2v83 / sens_db_1w)", ""


def _loader_verdict(raw: dict) -> list[str]:
    """Which repo loaders accept the file, tried with their real ``from_dict`` (report-only)."""
    okay: list[str] = []
    kind = str(raw.get("kind") or "compression")
    from hornlab_search.driver.compression import CompressionDriver
    from hornlab_search.meh.drivers import CDSource, ConeDriver

    def try_one(label: str, cls, predicate: Callable[[dict], bool]) -> None:
        if not predicate(raw):
            return
        try:
            cls.from_dict(raw)
        except Exception:  # noqa: BLE001 - a real schema mismatch is the finding
            return
        okay.append(label)

    try_one("CompressionDriver (P12)", CompressionDriver,
            lambda d: str(d.get("kind") or "compression") in ("compression", "cone")
            and d.get("re_ohm") is not None)
    try_one("ConeDriver (MEH)", ConeDriver, lambda d: d.get("kind") == "cone")
    try_one("CDSource (MEH)", CDSource, lambda d: d.get("kind") == "compression_meh")
    return okay


def audit_driver(path: Path) -> dict:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw = raw if isinstance(raw, dict) else {}
    has_sens, sens_text, cond = _sensitivity(raw)
    return {
        "file": path.name,
        "is_template": path.name == TEMPLATE_FILE,
        "name": str(raw.get("name") or ""),
        "kind": str(raw.get("kind") or "(default compression)"),
        "mass_status": _mass_status(raw),
        "mass_ok": raw.get("mmd_g") is not None,
        "source_url": "yes" if _url_ok(raw) else "MISSING",
        "source_text": str(raw.get("source") or ""),
        "has_sensitivity": has_sens,
        "sensitivity": sens_text,
        "sensitivity_condition": cond,
        "loaders": _loader_verdict(raw),
    }


def collect(drivers_dir: Path = DRIVERS_DIR) -> list[dict]:
    return [audit_driver(p) for p in sorted(drivers_dir.glob("*.yaml"))]


CSV_FIELDS = ("file", "is_template", "name", "kind", "mass_status", "mass_ok", "source_url",
              "source_text", "has_sensitivity", "sensitivity", "sensitivity_condition", "loaders")


def _loaders_cell(row: dict) -> str:
    if row["is_template"]:
        return "template"
    return ";".join(row["loaders"]) if row["loaders"] else "NO loader accepts this file"


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            csv_row = dict(row)
            csv_row["loaders"] = _loaders_cell(row)
            writer.writerow(csv_row)


def _md_cell(value: str) -> str:
    """Escape a markdown table cell (the template file's ``kind`` is literally 'compression | cone')."""
    return str(value).replace("|", "\\|")


def write_markdown(path: Path, rows: list[dict]) -> dict:
    real = [r for r in rows if not r["is_template"]]
    templates = [r for r in rows if r["is_template"]]
    lines: list[str] = []
    lines.append("## Driver-file readiness (report-only, examples/drivers/*.yaml)")
    lines.append("")
    lines.append("Generated by `tools/rescore/driver_check.py`. Readiness columns per file: "
                 "dry moving mass, datasheet source URL, published sensitivity (with the "
                 "measuring convention), and which repo loader(s) accept the file "
                 "(``CompressionDriver`` = P12 lumped model; ``ConeDriver``/``CDSource`` = MEH "
                 "C7/C8). The repo currently ships TWO driver-file schemas side by side; a file "
                 "that no loader accepts is a finding, not silently skipped.")
    lines.append("")
    lines.append("| Driver file | Kind | Dry mass | Source URL | Published sensitivity | Loader(s) |")
    lines.append("|---|---|---|---|---|---|")
    for r in real:
        loaders = _loaders_cell(r)
        lines.append(f"| `{r['file']}` | {_md_cell(r['kind'])} | {_md_cell(r['mass_status'])} | "
                     f"{r['source_url']} | {_md_cell(r['sensitivity'])} | {_md_cell(loaders)} |")
    lines.append("")
    for r in templates:
        lines.append(f"- `{r['file']}` — the documented template (not a driver); its readiness "
                     "columns are intentional placeholders and it is excluded from the counts "
                     "below.")
        lines.append("")
    lines.append(f"- Real driver files: {len(real)} (plus `_template.yaml`)")
    lines.append(f"- `mmd_g` published: {sum(1 for r in real if r['mass_ok'])}")
    lines.append(f"- Mmd MISSING (Mms only, no air-load split, or nothing): "
                 f"{sum(1 for r in real if not r['mass_ok'])}")
    lines.append(f"- Source URL present: {sum(1 for r in real if r['source_url'] == 'yes')}")
    lines.append(f"- Published sensitivity present: {sum(1 for r in real if r['has_sensitivity'])}")
    lines.append(f"- No loader accepts the file: "
                 f"{sum(1 for r in real if not r['loaders'])}")
    lines.append("")
    lines.append("### Predicted-vs-datasheet sensitivity comparison: NOT computable tonight "
                 "(status, not a score)")
    lines.append("")
    lines.append("`hornlab_search/driver/compression.py` DOES expose a sensitivity prediction: "
                 "`drive()` returns 2.83 V / 1 m on-axis SPL per frequency (`spl_onaxis_db`) "
                 "and `band_mean_db()` averages it over a window. Comparing that against the "
                 "published sensitivity needs a stored `Response` carrying the mesh's driven-"
                 "throat tag area (`metrics.loudness.throat_area_m2` reads "
                 "`meta['physical_tag_areas_m2']`). The single-channel dataset rows store no "
                 "such metadata, and the only rows that carry `tag_areas_m2` are the "
                 "two-channel MEH rows (`channel_tags: [2, 10]`), where the single-piston "
                 "`drive()` does not apply without a network-level model. Substituting a "
                 "`pi * exit_radius^2` throat area would bias the prediction by more than the "
                 "2 dB flag threshold (an OSSE/R-OSSE throat is an ellipse: measured 24 x 36 mm "
                 "on a 36 mm brief), so no dB table is printed here - a >2 dB flag produced "
                 "that way would be an artefact of the stand-in area, not of the driver model.")
    lines.append("")
    lines.append("Owner follow-up (P0 item 8, unchanged): run the comparison inside a verify "
                 "run directory, where `run.json` + `designs/*/mesh.msh` let the real tag "
                 "areas reach `Response.meta`; a single representative horn per driver exit "
                 "size is enough. THEN flag predicted-vs-published gaps > 2 dB, measured in "
                 "the driver's own stated condition (see the conventions column above - note "
                 "the MEH compression files publish 1 W/1 m, a 3 dB offset from 2.83 V/1 m at "
                 "8 ohm nominal that must be normalised before comparing).")
    lines.append("")
    for r in real:
        if r["has_sensitivity"] and r["sensitivity_condition"]:
            lines.append(f"- `{r['file']}`: {r['sensitivity']} - "
                         f"condition: {r['sensitivity_condition']}")
    text = "\n".join(lines) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {
        "files": len(real),
        "mmd_published": sum(1 for r in real if r["mass_ok"]),
        "mmd_missing": sum(1 for r in real if not r["mass_ok"]),
        "source_url_present": sum(1 for r in real if r["source_url"] == "yes"),
        "sensitivity_present": sum(1 for r in real if r["has_sensitivity"]),
        "no_loader": sum(1 for r in real if not r["loaders"]),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Driver-file readiness audit (report-only)")
    ap.add_argument("--drivers", type=Path, default=DRIVERS_DIR)
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "scratch" / "driver_check")
    args = ap.parse_args(argv)
    rows = collect(args.drivers)
    if not rows:
        print(f"error: no driver YAMLs under {args.drivers}", file=sys.stderr)
        return 2
    write_csv(args.out / "driver_check.csv", rows)
    summary = write_markdown(args.out / "driver_check.md", rows)
    print(f"wrote {len(rows)} rows to {args.out / 'driver_check.csv'} "
          f"and {args.out / 'driver_check.md'}")
    print("SUMMARY " + json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
