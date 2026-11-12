"""C.1 - plan the P0 calibration night (offline; never solves).

    .venv\\Scripts\\python.exe tools\\calibration\\plan_calibration.py ^
        --designs <run dir | csv> [--designs <run dir | csv> ...] ^
        [--top 20] --out runs\\nights\\calibration_2026-11-12.yaml

For every stored finalist design it generates one ``hornlab-search verify --designs <hash>``
night job per calibration variant:

* ``single_mesh``  control (the run's own configuration, no overrides)
* ``band_split``   ``mesh: {band_split: {edges_hz: [2000.0]}}``   (P0 new-mesh-policy probe)
* ``dist_2m``      ``solve: {distance_m: 2.0}``
* ``dist_10m``     ``solve: {distance_m: 10.0}``
* ``epw_6``        ``mesh: {epw: 6.0}``
* ``epw_9``        ``mesh: {epw: 9.0}``

Mechanism (decided): each overriding variant is a 3-6 line ``extends:`` overlay, written to
``examples/calibration/<date>/<run>__<variant>.yaml`` (PR #29 mechanism; same style as
``examples/profiles/``). The verify run needs a run directory: the planner materializes one per
(run, variant) under ``--variants-dir`` (default ``scratch/calibration_<date>/variants``) holding

* ``config.yaml``    one-line ``extends:`` chain into the overlay (control: into the run itself)
* ``search.ndjson``  the source run's rows, filtered to the selected design hashes
* ``run.json``       provenance (which run, which variant, which designs)

Every generated variant config is preflighted with ``hornlab_search.config.load_config`` so a bad
edge value or an unknown key fails at PLAN time, not mid-night. The night YAML itself is the
``tools/run_campaign_night.py`` format (``night:`` + ``jobs:``), plus a ``calibration:`` metadata
block the runner ignores and ``compare_calibration.py`` reads back (thresholds, aspect pairs,
design list, variants dir).

Acceptance thresholds (P0, NEXT_DEV_PRIORITIES): Re z +-0.03, beamwidth +-2 deg, DI +-0.2 dB.
Default ``--top 20`` (not the historical 5): the C.4 amendment verifies the top 15-20 per run and
ranks finalists by verify J only, because the coarse screen cannot rank its own finalists.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The fixed variant set of the P0 calibration (decided). ``overrides`` are merged DEEP over the
#: run's own configuration through the ``extends:`` chain, so each overlay is 3-6 lines.
VARIANTS: dict[str, dict] = {
    "single_mesh": {"kind": "control", "overrides": {}},
    "band_split": {"kind": "mesh", "overrides": {"mesh": {"band_split": {"edges_hz": [2000.0]}}}},
    "dist_2m": {"kind": "solve", "overrides": {"solve": {"distance_m": 2.0}}},
    "dist_10m": {"kind": "solve", "overrides": {"solve": {"distance_m": 10.0}}},
    "epw_6": {"kind": "mesh", "overrides": {"mesh": {"epw": 6.0}}},
    "epw_9": {"kind": "mesh", "overrides": {"mesh": {"epw": 9.0}}},
}
#: Variant order inside the night file (control first, then (a), (b), (c)).
VARIANT_ORDER = ("single_mesh", "band_split", "dist_2m", "dist_10m", "epw_6", "epw_9")

#: Which variants form one comparison pair, by aspect, for ``compare_calibration.py``.
ASPECT_PAIRS: dict[str, tuple[str, str]] = {
    "mesh_policy": ("band_split", "single_mesh"),
    "observation_distance": ("dist_2m", "dist_10m"),
    "mesh_resolution": ("epw_6", "epw_9"),
}

#: Acceptance thresholds from P0 (NEXT_DEV_PRIORITIES item 2). ``re_z`` is on the rho*c-normalised
#: real throat impedance, ``beamwidth_deg`` on H and V beamwidth, ``di_db`` on DI.
THRESHOLDS = {"re_z": 0.03, "beamwidth_deg": 2.0, "di_db": 0.2}

#: C.4 amendment: the screen is optimistic and cannot rank its own finalists, so the calibration
#: verifies the top 15-20 (this default: 20) per run -- not the historical 5 -- and finalists are
#: ranked by verify J only.
DEFAULT_TOP = 20

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

_JOB_PREFIX = "c_"

_NEW_SCREEN_GRID_PPO = 6.0  # ~7 points in 2.5-5.5 kHz (1.14 oct); the P0 "new screen grid" proposal


class PlanError(ValueError):
    """A fatal input problem: printed once, exit 2."""


# ------------------------------------------------------------------ inputs


def _safe(name: object, what: str) -> str:
    text = str(name or "").strip()
    if not _SAFE_NAME.match(text):
        raise PlanError(f"{what} must match {_SAFE_NAME.pattern!r}, got {text!r}")
    return text


def _resolve_run_dir(path: Path, repo_root: Path) -> Path:
    if path.is_dir():
        return path
    candidate = repo_root / "runs" / str(path)
    if candidate.is_dir():
        return candidate
    raise PlanError(f"--designs {path}: not a directory and not a run id under runs/")


def _read_ndjson(path: Path) -> list[dict]:
    """Parseable rows only; torn final lines are skipped (same rule as search/evaluate.py)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise PlanError(f"cannot read {path}: {exc}") from exc
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    return rows


def _top_designs(ndjson_rows: list[dict], top: int, run_label: str) -> list[dict]:
    """The top ``top`` distinct design hashes by best (lowest) ok objective, with that J."""
    best: dict[str, float] = {}
    for row in ndjson_rows:
        if not row.get("ok") or not row.get("design_hash"):
            continue
        try:
            j = float(row["objective"])
        except (TypeError, ValueError, KeyError):
            continue
        h = str(row["design_hash"])
        if h not in best or j < best[h]:
            best[h] = j
    if not best:
        raise PlanError(f"{run_label}: search.ndjson has no successful row to calibrate")
    ordered = sorted(best.items(), key=lambda kv: (kv[1], kv[0]))
    return [{"hash": h, "screen_j": j} for h, j in ordered[:top]]


def _load_designs(inputs: list[str], top: int, repo_root: Path) -> dict[str, list[dict]]:
    """``{run_dir_path: [{hash, screen_j}, ...]}`` from run dirs and/or CSVs.

    A CSV needs a ``design`` column and, when it stands for stored finalists, a ``run`` column
    naming the run directory that holds each hash (order in the file is not re-ranked)."""
    per_run: dict[str, dict[str, "float | None"]] = {}
    for raw in inputs:
        path = Path(raw)
        if path.is_file() or path.suffix.lower() == ".csv":
            try:
                with open(path, newline="", encoding="utf-8-sig") as handle:
                    reader = csv.DictReader(handle)
                    fields = reader.fieldnames or []
                    if "design" not in fields:
                        raise PlanError(f"{path}: CSV has no 'design' column")
                    if "run" not in fields:
                        raise PlanError(f"{path}: CSV has no 'run' column (run dir per design)")
                    for row in reader:
                        design = (row.get("design") or "").strip()
                        run = (row.get("run") or "").strip()
                        if not design or not run:
                            continue
                        resolved = _resolve_run_dir(Path(run), repo_root)
                        per_run.setdefault(str(resolved), {}).setdefault(design, None)
            except OSError as exc:
                raise PlanError(f"cannot read {path}: {exc}") from exc
        else:
            run_dir = _resolve_run_dir(path, repo_root)
            ndjson = run_dir / "search.ndjson"
            if not ndjson.is_file():
                raise PlanError(f"{run_dir}: no search.ndjson")
            found = _top_designs(_read_ndjson(ndjson), top, str(run_dir))
            for entry in found:
                per_run.setdefault(str(run_dir), {}).setdefault(entry["hash"], entry["screen_j"])
    # Fill screen J from the run's rows for every hash (CSV rows may lack it).
    out: dict[str, list[dict]] = {}
    for run, hashes in per_run.items():
        rows = _read_ndjson(Path(run) / "search.ndjson")
        best: dict[str, float] = {}
        for row in rows:
            if not row.get("ok") or not row.get("design_hash"):
                continue
            try:
                j = float(row["objective"])
            except (TypeError, ValueError, KeyError):
                continue
            h = str(row["design_hash"])
            if h in hashes and (h not in best or j < best[h]):
                best[h] = j
        missing = sorted(h for h in hashes if h not in best)
        if missing:
            raise PlanError(f"{run}: {len(missing)} requested design hash(es) have no ok row in "
                            f"search.ndjson: {', '.join(missing[:10])}")
        out[run] = [{"hash": h, "screen_j": best[h]} for h in sorted(hashes)]
    if not out:
        raise PlanError("no designs selected (empty --designs input?)")
    return out


# ------------------------------------------------------------------ overlays / variant dirs


def _rel(target: Path, start: Path) -> str:
    return Path(os.path.relpath(Path(target).resolve(), Path(start).resolve())).as_posix()


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_overlay_text(date: str, run: str, variant: str, run_config: Path, overlay_path: Path) -> str:
    """The 3-6 line ``extends:`` overlay for one overriding variant (final version)."""
    overrides = yaml.safe_dump(VARIANTS[variant]["overrides"], default_flow_style=False,
                               sort_keys=False).rstrip("\n")
    return (f"# calibration {date}: variant {variant} of run {run}\n"
            f"# P0 calibration overlay ({VARIANTS[variant]['kind']}); base = the run's own config.\n"
            f"# Apply by extending this file (see tools/calibration/plan_calibration.py).\n"
            f"extends: {_rel(run_config, overlay_path.parent)}\n"
            f"{overrides}\n")


def build_new_screen_grid_text(date: str, run: str, run_config: Path,
                               overlay_path: Path, band_lo: float, band_hi: float) -> str:
    """PROPOSAL ONLY (C.4): the P0 "new screen grid" overlay -- band split at 2 kHz and a denser
    screen grid (~7 points in 2.5-5.5 kHz). ``solve.freq_grid`` sets the log grid density; the
    exact per-brief low-band points (0.7 f0 .. f0) need each brief's f0 and are settled after the
    calibration night. Not wired into the night jobs."""
    lo = max(500.0, float(band_lo))
    hi = min(10_000.0, float(band_hi))
    overrides = yaml.safe_dump(
        {"mesh": {"band_split": {"edges_hz": [2000.0]}},
         "solve": {"freq_grid": {"lo_hz": float(lo), "hi_hz": float(hi),
                                 "points_per_octave": _NEW_SCREEN_GRID_PPO}}},
        default_flow_style=False, sort_keys=False).rstrip("\n")
    return (f"# calibration {date}: PROPOSAL ONLY (C.4) -- the P0 'new screen grid' of run {run}.\n"
            f"# Band split at 2 kHz; screen grid at {_NEW_SCREEN_GRID_PPO:g} points/octave from\n"
            f"# {lo:g} Hz to {hi:g} Hz (~7 points in 2.5-5.5 kHz). Not a night job: settle after\n"
            f"# the calibration night, then run a SCREEN search under it. Band {band_lo:g}-{band_hi:g} Hz.\n"
            f"extends: {_rel(run_config, overlay_path.parent)}\n"
            f"{overrides}\n")


def _variant_config_text(variant: str, overlay: Path | None, variant_dir: Path,
                         run_config: Path, date: str, run: str) -> str:
    base = (f"# calibration {date}: variant {variant} for run {run}\n")
    if overlay is None:
        return base + f"# control: the run's own configuration, no overrides\nextends: {_rel(run_config, variant_dir)}\n"
    return base + (f"# resolves through the overlay examples/calibration/{date}/{overlay.name}\n"
                   f"extends: {_rel(overlay, variant_dir)}\n")


def _filtered_ndjson(rows: list[dict], hashes: set[str], path: Path) -> None:
    kept = [row for row in rows if str(row.get("design_hash") or "") in hashes]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in kept:
            handle.write(json.dumps(row, allow_nan=False, separators=(",", ":")) + "\n")


def _run_json(variant_dir_name: str, variant: str, run: str, hashes: list[str]) -> dict:
    return {
        "run_id": variant_dir_name,
        "mode": "verify",
        "status": "calibration_variant",
        "variant": variant,
        "verify_of": {"run": str(Path(run)), "designs": list(hashes)},
        "note": "materialized by tools/calibration/plan_calibration.py; not a search run",
    }


def _preflight(variant_config: Path) -> dict:
    """Load the generated variant config with the repo's own loader (validates band_split edges,
    epw, distance, the brief chain, ...). Returns the effective ``target_raw`` band."""
    repo_root = REPO_ROOT
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from hornlab_search.config import load_config  # noqa: PLC0415 - CLI-lifetime import
    try:
        cfg = load_config(variant_config)
    except Exception as exc:  # ConfigError/ValueError/OSError all mean "do not ship this config"
        raise PlanError(f"preflight failed for {variant_config}: "
                        f"{type(exc).__name__}: {exc}") from exc
    return {"band_lo_hz": cfg.target_raw.get("band_lo_hz"),
            "band_hi_hz": cfg.target_raw.get("band_hi_hz")}


# ------------------------------------------------------------------ night file


def _job_id(variant: str, run: str) -> str:
    return _JOB_PREFIX + variant + "__" + Path(run).name


def plan_calibration(*, designs: dict[str, list[dict]], top: int, out: Path, repo_root: Path,
                     date: str, variants_dir: Path | None, run_jobs: bool = False) -> dict:
    """Generate overlays + variant dirs + the night YAML. Returns a summary dict."""
    out = Path(out)
    if not out.is_absolute() and not out.exists() and not out.parent.is_dir():
        raise PlanError(f"--out parent does not exist: {out.parent}")
    night = _safe(out.stem, "night name (--out file stem)")
    date = _safe(date, "date")
    if variants_dir is None:
        variants_dir = repo_root / "scratch" / f"calibration_{date}" / "variants"
    variants_dir = Path(variants_dir)
    if not variants_dir.is_absolute():
        variants_dir = repo_root / variants_dir

    overlays_dir = repo_root / "examples" / "calibration" / date
    exe = ".venv/Scripts/hornlab-search.exe"

    jobs: list[dict] = []
    designs_meta: list[dict] = []
    runs_meta: dict[str, dict] = {}
    overlays_meta: dict[str, str] = {}
    pref_counts: dict[str, int] = {v: 0 for v in VARIANTS}

    for run, entries in sorted(designs.items()):
        run_config = Path(run) / "config.yaml"
        if not run_config.is_file():
            raise PlanError(f"{run}: no config.yaml (verify reads the run's own config)")
        hashes = [e["hash"] for e in entries]
        band = _preflight(run_config)  # the control chain == the run's own config
        runs_meta[str(run)] = {"path": str(run), "band_lo_hz": band.get("band_lo_hz"),
                               "band_hi_hz": band.get("band_hi_hz"),
                               "designs": len(entries)}

        for variant in VARIANT_ORDER:
            overlay: Path | None = None
            if VARIANTS[variant]["overrides"]:
                overlay = overlays_dir / f"{Path(run).name}__{variant}.yaml"
                _write_text(overlay, build_overlay_text(date, Path(run).name, variant,
                                                        run_config, overlay))
                overlays_meta[variant] = overlay.relative_to(repo_root).as_posix()
            vdir = variants_dir / f"{Path(run).name}__{variant}"
            vdir.mkdir(parents=True, exist_ok=True)
            _write_text(vdir / "config.yaml",
                        _variant_config_text(variant, overlay, vdir, run_config, date,
                                             Path(run).name))
            _filtered_ndjson(_read_ndjson(Path(run) / "search.ndjson"), set(hashes),
                             vdir / "search.ndjson")
            _write_text(vdir / "run.json",
                        json.dumps(_run_json(vdir.name, variant, str(run), hashes), indent=1) + "\n")
            # Preflight EVERY variant config so a bad overlay fails at plan time (offline).
            if variant != "single_mesh":
                _preflight(vdir / "config.yaml")
                pref_counts[variant] += 1
            jobs.append({
                "id": _job_id(variant, str(run)),
                "kind": "command",
                "argv": [exe, "verify", "--run", _rel(vdir, repo_root), "--designs",
                         ",".join(hashes)],
                "timeout_s": 3 * 60 * 60,
            })
        designs_meta.extend({**e, "run": str(run), "job_run": Path(run).name} for e in entries)

    # C.4 proposal overlay per run (not a night job): the P0 new screen grid.
    for run in sorted(designs):
        band = runs_meta[str(run)]
        lo, hi = band.get("band_lo_hz"), band.get("band_hi_hz")
        if not (isinstance(lo, (int, float)) and isinstance(hi, (int, float))):
            continue
        name = Path(run).name
        overlay = overlays_dir / f"{name}__new_screen_grid.yaml"
        _write_text(overlay, build_new_screen_grid_text(
            date, name, Path(run) / "config.yaml", overlay, float(lo), float(hi)))
        overlays_meta[f"{name}/new_screen_grid"] = overlay.relative_to(repo_root).as_posix()

    night_doc = {
        "night": night,
        "lane": "gpu",
        "calibration": {
            "generated_by": "tools/calibration/plan_calibration.py",
            "date": date,
            "top": top,
            "thresholds": dict(THRESHOLDS),
            "variant_order": list(VARIANT_ORDER),
            "aspect_pairs": {k: list(v) for k, v in ASPECT_PAIRS.items()},
            "overlays_dir": overlays_dir.relative_to(repo_root).as_posix()
                if overlays_dir.is_relative_to(repo_root) else str(overlays_dir),
            "overlays": overlays_meta,
            "variants_dir": variants_dir.relative_to(repo_root).as_posix()
                if variants_dir.is_relative_to(repo_root) else str(variants_dir),
            "runs": runs_meta,
            "designs": designs_meta,
        },
        "jobs": jobs,
    }
    header = (
        f"# P0 calibration night ({date}) -- generated by tools/calibration/plan_calibration.py\n"
        f"# {len(designs)} run(s), {sum(len(v) for v in designs.values())} finalist(s) per run,\n"
        f"# {len(VARIANT_ORDER)} variants per run (control | band-split 2 kHz | dist 2 m | dist 10 m\n"
        f"# | epw 6 | epw 9). Acceptance: Re z +-0.03, beamwidth +-2 deg, DI +-0.2 dB.\n"
        f"# Overlays: examples/calibration/{date}/  Variant run dirs: {variants_dir}\n"
        f"# Analyse afterwards: tools/calibration/compare_calibration.py --night runs/nights/{night}\n")
    _write_text(out, header + yaml.safe_dump(night_doc, sort_keys=False, width=100))
    return {"night": night, "night_path": str(out), "jobs": len(jobs),
            "runs": {str(k): len(v) for k, v in designs.items()},
            "overlays_dir": str(overlays_dir), "variants_dir": str(variants_dir),
            "preflighted_configs": sum(pref_counts.values())}


# ------------------------------------------------------------------ CLI


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    today = "2026-11-12"
    parser = argparse.ArgumentParser(
        description="Plan the P0 calibration night (offline; writes YAML/overlays, never solves).")
    parser.add_argument("--designs", action="append", required=False, metavar="RUNDIR|CSV",
                        help="a run directory (top --top designs of its search.ndjson) or a CSV "
                             "with 'design' and 'run' columns; repeatable")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP,
                        help=f"finalists per run (default {DEFAULT_TOP}; the C.4 amendment says "
                             f"verify the top 15-20, not 5)")
    parser.add_argument("--out", required=True, metavar="YAML", help="night file to write")
    parser.add_argument("--repo-root", default=str(REPO_ROOT),
                        help="repo root (default: this checkout)")
    parser.add_argument("--date", default=today, help="calibration date (default today)")
    parser.add_argument("--variants-dir", default=None, metavar="DIR",
                        help="where the per-variant run dirs go "
                             "(default scratch/calibration_<date>/variants)")
    parser.add_argument("--list-only", action="store_true",
                        help="print the selected designs and exit; write nothing")
    args = parser.parse_args(argv)
    if not args.designs:
        parser.error("--designs is required (run dir and/or CSV, repeatable)")
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root)
    try:
        if args.top < 1:
            raise PlanError(f"--top must be >= 1, got {args.top}")
        designs = _load_designs(args.designs, args.top, repo_root)
        if args.list_only:
            for run, entries in sorted(designs.items()):
                print(f"{run}")
                for i, entry in enumerate(entries, 1):
                    print(f"  {i:2d}. {entry['hash']}  screen J={entry['screen_j']:.5f}")
            print(f"{sum(len(v) for v in designs.values())} design(s) across "
                  f"{len(designs)} run(s); --top {args.top}")
            return 0
        summary = plan_calibration(designs=designs, top=args.top, out=Path(args.out),
                                   repo_root=repo_root, date=args.date,
                                   variants_dir=None if args.variants_dir is None
                                   else Path(args.variants_dir))
    except (PlanError, OSError) as exc:
        print(f"plan_calibration: {exc}", file=sys.stderr)
        return 2
    print(f"plan_calibration: {summary['jobs']} job(s) across {len(summary['runs'])} run(s) "
          f"-> {summary['night_path']}")
    print(f"  overlays {summary['overlays_dir']}")
    print(f"  variant dirs {summary['variants_dir']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
