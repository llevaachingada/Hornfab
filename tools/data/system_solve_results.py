"""Export every stored horn+woofer solve result to portable CSV for cloud review.

The system layer's `system_cases.csv` is a case *census*; it carries no pressure values.  This
tool adds three CSVs under `docs/system_data/`:

* ``system_solve_results.csv`` - long form, one row per case / excitation / observation point /
  frequency, with raw complex pressure, magnitude, relative level and phase;
* ``system_case_metrics.csv`` - one row per case / excitation / frequency with the on-axis
  reference and, when the case has a sphere, the equal-area power and DI;
* ``system_screen_rows.csv`` - the flattened shortlist rows from every stored ``woofer_seed``
  screen.

Read-only over ``system_runs/``; no solver, no GPU.  Run ``tools/data/system_cases.py`` first so
the case metadata (fidelity / motor / shape) is current.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from hornlab_search.system import balloon_metrics as BM
from hornlab_search.system.boundarylab import bl_results as R

RESULT_FIELDS = (
    "case_key", "experiment", "case", "status", "fidelity", "motor", "transducer_shape",
    "excitation_id", "per_input", "observation_id", "observation_kind", "distance_m",
    "frequency_hz", "point_index", "angle_deg", "x_m", "y_m", "z_m",
    "p_re_pa", "p_im_pa", "magnitude_pa", "phase_deg",
    "level_db_field_max", "level_db_axis",
)
METRIC_FIELDS = (
    "case_key", "experiment", "case", "status", "fidelity", "motor", "transducer_shape",
    "excitation_id", "per_input", "frequency_hz",
    "on_axis_magnitude_pa", "on_axis_level_db_rel_max", "max_magnitude_pa",
    "observation_id", "distance_m", "n_observations",
    "di_db", "power_pa2", "di_source", "quadrature", "axis_source", "axis_probe_id",
)


def _fmt(value: Any, digits: int = 9) -> str:
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return ""
    return f"{number:.{digits}g}"


def _db(value: float, reference: float) -> str:
    if reference <= 0.0 or value <= 0.0:
        return ""
    return _fmt(20.0 * math.log10(value / reference), 7)


def _metadata(cases_json: Path) -> dict[str, dict]:
    if not cases_json.is_file():
        return {}
    doc = json.loads(cases_json.read_text(encoding="utf-8"))
    return {str(row.get("case_key")): row for row in doc.get("cases", [])}


def _case_dirs(root: Path) -> list[Path]:
    base = root / "system_runs" / "system"
    if not base.is_dir():
        return []
    return sorted(path for path in base.glob("*/*") if (path / "run" / "manifest.json").is_file())


def _axis_index(observation: R.BLObservationSet) -> int | None:
    if observation.angles_deg is not None and len(observation.angles_deg):
        angles = np.asarray(observation.angles_deg, dtype=float)
        index = int(np.argmin(np.abs(angles)))
        if abs(float(angles[index])) <= 1e-9:
            return index
    if "on_axis" in observation.domain_id.lower():
        points = np.asarray(observation.points_m, dtype=float)
        norms = np.linalg.norm(points, axis=1)
        if points.size and np.all(norms > 0.0):
            return int(np.argmax((points / norms[:, None])[:, 2]))
    return None


def _axis_map(result: R.BLHeadlessResult) -> dict[tuple[str, int], float]:
    """Prefer an explicit on-axis probe; fall back to a polar 0-degree sample."""
    best: dict[tuple[str, int], tuple[int, float]] = {}
    for field in result.fields:
        index = _axis_index(field.observation)
        if index is None:
            continue
        is_probe = "probe" in field.observation.kind.lower() or "on_axis" in field.observation.domain_id.lower()
        priority = 2 if is_probe else 1
        values = np.abs(field.p_pa[:, index])
        for freq_index, magnitude in enumerate(values):
            key = (field.excitation_id, freq_index)
            if key not in best or priority > best[key][0]:
                best[key] = (priority, float(magnitude))
    return {key: value for key, (_priority, value) in best.items()}


def _sphere_metrics(result: R.BLHeadlessResult) -> tuple[dict, str]:
    spheres = [item for item in result.observation_sets.values()
               if "spherical" in str(item.kind).lower()]
    if not spheres:
        return {}, ""
    sphere = spheres[0]
    candidates = [
        item.domain_id for item in result.observation_sets.values()
        if "on_axis" in item.domain_id.lower()
        and item.distance_m is not None and sphere.distance_m is not None
        and abs(float(item.distance_m) - float(sphere.distance_m)) <= 1e-9
    ]
    axis_probe = sorted(candidates)[0] if candidates else "observation:probe:on_axis_2m"
    try:
        metrics = BM.per_excitation_metrics(result, axis_probe_id=axis_probe)
    except ValueError as exc:
        return {}, str(exc)
    return metrics, ""


def _write_results(root: Path, cases: list[Path], metadata: dict, out: Path) -> int:
    rows_written = 0
    with (out / "system_solve_results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(RESULT_FIELDS), lineterminator="\n")
        writer.writeheader()
        for case in cases:
            case_key = case.relative_to(root / "system_runs" / "system").as_posix()
            meta = metadata.get(case_key, {})
            result = R.read_bl_headless_result(case / "run")
            axes = _axis_map(result)
            for field in result.fields:
                observation = field.observation
                points = np.asarray(observation.points_m, dtype=float)
                angles = (np.asarray(observation.angles_deg, dtype=float)
                          if observation.angles_deg is not None else None)
                magnitude = np.abs(field.p_pa)
                field_max = float(np.max(magnitude)) if magnitude.size else 0.0
                for freq_index, frequency in enumerate(result.frequencies_hz):
                    axis_magnitude = axes.get((field.excitation_id, freq_index))
                    for point_index in range(magnitude.shape[1]):
                        value = complex(field.p_pa[freq_index, point_index])
                        axis_ref = axis_magnitude if axis_magnitude is not None else 0.0
                        writer.writerow({
                            "case_key": case_key,
                            "experiment": case.parent.name,
                            "case": case.name,
                            "status": "solved",
                            "fidelity": meta.get("fidelity", ""),
                            "motor": meta.get("motor", ""),
                            "transducer_shape": meta.get("transducer_shape", ""),
                            "excitation_id": field.excitation_id,
                            "per_input": getattr(field.basis, "per_input", ""),
                            "observation_id": observation.domain_id,
                            "observation_kind": observation.kind,
                            "distance_m": _fmt(observation.distance_m),
                            "frequency_hz": _fmt(frequency, 10),
                            "point_index": point_index,
                            "angle_deg": _fmt(angles[point_index]) if angles is not None else "",
                            "x_m": _fmt(points[point_index, 0]),
                            "y_m": _fmt(points[point_index, 1]),
                            "z_m": _fmt(points[point_index, 2]),
                            "p_re_pa": _fmt(value.real),
                            "p_im_pa": _fmt(value.imag),
                            "magnitude_pa": _fmt(abs(value)),
                            "phase_deg": _fmt(math.degrees(math.atan2(value.imag, value.real))),
                            "level_db_field_max": _db(abs(value), field_max),
                            "level_db_axis": _db(abs(value), axis_ref),
                        })
                        rows_written += 1
    return rows_written


def _write_metrics(root: Path, cases: list[Path], metadata: dict, out: Path) -> int:
    rows_written = 0
    with (out / "system_case_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(METRIC_FIELDS), lineterminator="\n")
        writer.writeheader()
        for case in cases:
            case_key = case.relative_to(root / "system_runs" / "system").as_posix()
            meta = metadata.get(case_key, {})
            result = R.read_bl_headless_result(case / "run")
            axes = _axis_map(result)
            sphere, sphere_error = _sphere_metrics(result)
            sphere_set = next((item for item in result.observation_sets.values()
                               if "spherical" in str(item.kind).lower()), None)
            for excitation in result.excitation_ids:
                excitation_fields = [field for field in result.fields
                                     if field.excitation_id == excitation]
                max_magnitude = max(
                    (float(np.max(np.abs(field.p_pa))) for field in excitation_fields),
                    default=0.0,
                )
                metric = sphere.get(excitation)
                per_input = (getattr(excitation_fields[0].basis, "per_input", "")
                             if excitation_fields else "")
                for freq_index, frequency in enumerate(result.frequencies_hz):
                    axis_magnitude = axes.get((excitation, freq_index))
                    di = power = axis_source = axis_probe = distance = None
                    n_observations = None
                    if metric is not None:
                        di = float(metric["di_db"][freq_index])
                        power = float(metric["power_pa2"][freq_index])
                        axis_source = metric["axis_source"]
                        axis_probe = metric["axis_probe_id"]
                        distance = metric["distance_m"]
                        n_observations = (
                            len(sphere_set.points_m) if sphere_set is not None else None
                        )
                    writer.writerow({
                        "case_key": case_key,
                        "experiment": case.parent.name,
                        "case": case.name,
                        "status": "solved",
                        "fidelity": meta.get("fidelity", ""),
                        "motor": meta.get("motor", ""),
                        "transducer_shape": meta.get("transducer_shape", ""),
                        "excitation_id": excitation,
                        "per_input": per_input,
                        "frequency_hz": _fmt(frequency, 10),
                        "on_axis_magnitude_pa": _fmt(axis_magnitude),
                        "on_axis_level_db_rel_max": _db(axis_magnitude or 0.0, max_magnitude),
                        "max_magnitude_pa": _fmt(max_magnitude),
                        "observation_id": sphere_set.domain_id if sphere_set is not None else "",
                        "distance_m": _fmt(distance if distance is not None else
                                           (sphere_set.distance_m if sphere_set is not None else None)),
                        "n_observations": n_observations if n_observations is not None else "",
                        "di_db": _fmt(di, 7),
                        "power_pa2": _fmt(power),
                        "di_source": "balloon" if di is not None else "",
                        "quadrature": BM.QUADRATURE if di is not None else "",
                        "axis_source": axis_source or "",
                        "axis_probe_id": axis_probe or "",
                    })
                    rows_written += 1
            if sphere_error:
                print(f"warning: {case_key}: sphere metrics refused: {sphere_error}")
    return rows_written


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value):
            out.update(_flatten(value[key], f"{prefix}.{key}" if prefix else str(key)))
        return out
    if isinstance(value, (list, tuple)):
        return {prefix: json.dumps(value, ensure_ascii=False)}
    return {prefix: value}


def _write_screens(root: Path, out: Path) -> int:
    paths: list[Path] = []
    base = root / "system_runs"
    if base.is_dir():
        paths = sorted(path for path in base.rglob("woofer_seed.json")
                       if "_fixtures" not in path.parts and "__pycache__" not in path.parts)
    rows: list[dict] = []
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, Mapping):
            continue
        study = str(data.get("study_id") or "")
        for row in data.get("shortlist", []) or []:
            if not isinstance(row, Mapping):
                continue
            flat = _flatten(row)
            flat["study_id"] = study
            flat["screen_path"] = path.relative_to(root).as_posix()
            rows.append(flat)
    fields = sorted({key for row in rows for key in row})
    preferred = ["study_id", "screen_path", "candidate_id", "driver_id", "driver_name"]
    fieldnames = [key for key in preferred if key in fields] + [key for key in fields if key not in preferred]
    with (out / "system_screen_rows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in sorted(rows, key=lambda item: (item.get("study_id", ""), item.get("candidate_id", ""))):
            writer.writerow({key: row.get(key, "") for key in fieldnames})
    return len(rows)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", metavar="DIR")
    parser.add_argument("--out", default="docs/system_data", metavar="DIR")
    parser.add_argument("--cases-json", default=None, metavar="JSON",
                        help="system_cases.json metadata (default <out>/system_cases.json)")
    args = parser.parse_args(list(argv) if argv is not None else None)
    root = Path(args.root).resolve()
    out = Path(args.out)
    out = out if out.is_absolute() else root / out
    out.mkdir(parents=True, exist_ok=True)
    cases_json = Path(args.cases_json) if args.cases_json else out / "system_cases.json"
    metadata = _metadata(cases_json)
    cases = _case_dirs(root)
    result_rows = _write_results(root, cases, metadata, out)
    metric_rows = _write_metrics(root, cases, metadata, out)
    screen_rows = _write_screens(root, out)
    print(f"system_solve_results: {len(cases)} solved cases, {result_rows} rows")
    print(f"system_case_metrics: {metric_rows} rows")
    print(f"system_screen_rows: {screen_rows} rows")
    print(f"output: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
