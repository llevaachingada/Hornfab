"""R7a screen ``E_shape`` calibration record (read-only; no recalibration).

This module builds one deterministic, read-only calibration *record* comparing the stored
stage-5 screen ``E_shape`` with the installed-boundary-BEM ``E_shape`` on the **exact common
stored direction grid**.  It does not solve, filter, sum, score, interpolate, or recalibrate
anything: the 9.0 dB² "good match" label is recorded as ``THRESHOLD_UNCHANGED_9DB2``.

What is compared
----------------
Screen side
    The stored screen horn polar levels (``spl_h_db`` / ``spl_v_db``) on the selected screen
    band, versus the analytic rigid-piston reference
    (:func:`hornlab_search.system.piston.relative_level_db`) at the selected driver's effective
    piston radius.  This is the screen's own ``E_shape`` definition.

BEM side
    The installed assembled case read through
    :func:`hornlab_search.system.boundarylab.bl_results.read_bl_headless_result`: horn relative
    level minus woofer relative level, each channel normalised at 0°.  The BEM case's woofer is
    the R2 demo 200 mm transducer shape, so the record stamps ``DEMO_SHAPE_CONFOUNDED_R2``.

Definition (uniform weights, no dB-power averaging)::

    E_shape = mean_f mean_dir (L_a,rel(f, dir) - L_b,rel(f, dir))^2    [dB^2]

Every channel is normalised at 0° independently, so absolute per-input references cancel.

Determinism
-----------
The returned dict contains only plain JSON types.  Everything is a pure function of the two
input artifacts and the explicit keyword arguments; the only non-deterministic value is
``generated_utc`` and callers may pin it.  :func:`write_calibration_record` serialises with
sorted keys and a fixed indent, so a rerun with the same ``generated_utc`` is byte-identical.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from hornlab_search.solve import cache as solve_cache
from hornlab_search.system import compatibility, piston
from hornlab_search.system import drivers as driver_data
from hornlab_search.system import horn_assets as HA
from hornlab_search.system.boundarylab import bl_results

__all__ = [
    "SCHEMA",
    "CONFOUND_DEMO_SHAPE_R2",
    "TOKEN_THRESHOLD_UNCHANGED",
    "ERROR_TOKENS",
    "CalibrationRecordError",
    "eshape_db2",
    "common_direction_grid",
    "map_frequencies",
    "build_calibration_record",
    "record_to_json",
    "write_calibration_record",
    "main",
]

#: Schema token carried by every record produced here.
SCHEMA = "hornlab.system.screen_eshape_calibration.v1"
#: The BEM woofer is the R2 demo 200 mm transducer shape while the screen piston uses the real
#: selected driver's effective area.  The factor is therefore confounded, not a correction.
CONFOUND_DEMO_SHAPE_R2 = "DEMO_SHAPE_CONFOUNDED_R2"
#: The 9.0 dB² good-match label is recorded unchanged; this record does not recalibrate it.
TOKEN_THRESHOLD_UNCHANGED = "THRESHOLD_UNCHANGED_9DB2"

#: Error tokens emitted by this module (``"<TOKEN>: detail"`` message form).
ERROR_TOKENS: tuple[str, ...] = (
    "SCREEN_CALIBRATION_INPUT_INVALID",
    "SCREEN_RESPONSE_UNRESOLVED",
    "SCREEN_RESPONSE_NOT_FOUND",
    "SCREEN_RESPONSE_SHA_MISMATCH",
    "SCREEN_FREQUENCY_BAND_UNRESOLVED",
    "SCREEN_GRID_EMPTY",
    "SCREEN_GRID_NO_ON_AXIS",
    "SCREEN_GRID_TOO_FEW_DIRECTIONS",
    "FREQUENCY_MAPPING_REFUSED",
    "FREQUENCY_MAPPING_DUPLICATE",
    "DRIVER_IDENTITY_UNRESOLVED",
    "BEM_RESULT_UNRESOLVED",
    "BEM_EXCITATION_UNRESOLVED",
    "BEM_PLANE_UNRESOLVED",
    "BEM_PRESSURE_INVALID",
    "ESHAPE_INPUT_INVALID",
)

#: Directions must agree within this tiny tolerance to count as the *same stored* direction.
#: Nothing is interpolated; the tolerance only absorbs float32 storage of an integer/2.5° grid.
_ANGLE_MATCH_TOL_DEG: float = 1e-6
#: On-axis exactness for the relative-level normalisation.
_ON_AXIS_TOL_DEG: float = 1e-9
#: Floating comparison tolerance for motor-patch -> T/S identity matching.
_TS_MATCH_REL_TOL: float = 1e-6

_H_PLANE_DOMAIN = "observation:horizontal-polar"
_V_PLANE_DOMAIN = "observation:vertical-polar"
_PLANE_DOMAIN_HINTS: Mapping[str, str] = {"H": "horizontal", "V": "vertical"}


class CalibrationRecordError(ValueError):
    """A refusal from the calibration-record builder, carrying a stable token."""

    def __init__(self, token: str, detail: str) -> None:
        if token not in ERROR_TOKENS:
            raise AssertionError(f"undeclared calibration record token {token!r}")
        super().__init__(f"{token}: {detail}")
        self.token = token
        self.detail = detail


# --------------------------------------------------------------------------- JSON helpers


def _jsonable(value: Any) -> Any:
    """Recursively convert numpy containers/scalars to plain JSON types."""
    if isinstance(value, np.ndarray):
        return [_jsonable(v) for v in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int)):
        return value
    return str(value)


def _posix(path: str | Path) -> str:
    """Repository-relative POSIX path when possible, else an absolute POSIX path."""
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(driver_data.REPO_ROOT).as_posix()
    except ValueError:
        return candidate.as_posix()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, token: str, what: str) -> Any:
    if not path.is_file():
        raise CalibrationRecordError(token, f"{what} not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CalibrationRecordError(token, f"unreadable {what} {path}: {exc}") from None


def _mapping(value: Any, token: str, what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CalibrationRecordError(token, f"{what} must be a JSON object, got "
                                            f"{type(value).__name__}")
    return value


# --------------------------------------------------------------------------- E_shape core


def eshape_db2(levels_a_rel_db: Any, levels_b_rel_db: Any) -> float:
    """``mean (a - b)^2`` in dB² over every supplied sample (frequencies x directions).

    Both arguments must be the same shape and already normalised at 0° by their caller.  The
    formula is plain mean-squared dB difference: no dB-power averaging, no weighting.
    """
    a = np.asarray(levels_a_rel_db, dtype=float)
    b = np.asarray(levels_b_rel_db, dtype=float)
    if a.shape != b.shape:
        raise CalibrationRecordError(
            "ESHAPE_INPUT_INVALID",
            f"E_shape inputs must share a shape, got {a.shape} and {b.shape}")
    if a.size == 0:
        raise CalibrationRecordError("ESHAPE_INPUT_INVALID", "E_shape inputs are empty")
    if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
        raise CalibrationRecordError(
            "ESHAPE_INPUT_INVALID", "E_shape inputs contain non-finite dB values")
    return float(np.mean(np.square(a - b)))


def _unique_sorted_angles(values: Any, what: str) -> np.ndarray:
    arr = np.asarray(values, dtype=float).reshape(-1)
    if arr.size == 0 or np.any(~np.isfinite(arr)):
        raise CalibrationRecordError(
            "SCREEN_GRID_EMPTY", f"{what} direction grid is empty or non-finite")
    arr = np.unique(np.round(arr, 9))
    return np.sort(arr)


def common_direction_grid(
    *angle_arrays: Any,
    max_deg: float = 30.0,
    match_tol_deg: float = _ANGLE_MATCH_TOL_DEG,
) -> tuple[list[float], dict[str, Any]]:
    """Exact intersection of every stored direction grid inside ``|angle| <= max_deg``.

    The first supplied grid is the reference; a direction is kept only when **every** other
    grid stores it (within ``match_tol_deg``).  Nothing is interpolated.  The grid must contain
    0° and at least five directions, otherwise the caller gets a refusal.
    """
    if not angle_arrays:
        raise CalibrationRecordError("SCREEN_GRID_EMPTY", "no direction grids were supplied")
    if not (math.isfinite(float(max_deg)) and float(max_deg) > 0.0):
        raise CalibrationRecordError(
            "SCREEN_CALIBRATION_INPUT_INVALID", f"max_deg must be finite and > 0, got {max_deg!r}")
    grids = [_unique_sorted_angles(values, f"grid[{i}]")
             for i, values in enumerate(angle_arrays)]
    reference = grids[0]
    common: list[float] = []
    for angle in reference:
        if abs(float(angle)) > float(max_deg) + float(match_tol_deg):
            continue
        if all(bool(np.any(np.abs(grid - float(angle)) <= float(match_tol_deg)))
               for grid in grids[1:]):
            common.append(float(angle))
    common = sorted(set(common))
    if not common:
        raise CalibrationRecordError(
            "SCREEN_GRID_EMPTY",
            f"no exact common stored directions inside |angle| <= {max_deg:g} deg")
    if not any(abs(a) <= _ON_AXIS_TOL_DEG for a in common):
        raise CalibrationRecordError(
            "SCREEN_GRID_NO_ON_AXIS",
            "the exact common direction grid has no stored 0 deg sample; refused instead of "
            "interpolating on axis")
    if len(common) < 5:
        raise CalibrationRecordError(
            "SCREEN_GRID_TOO_FEW_DIRECTIONS",
            f"the exact common direction grid has {len(common)} direction(s) "
            f"{common}; at least 5 are required (no interpolation)")
    record = {
        "angles_deg": common,
        "n_dirs": len(common),
        "max_deg": float(max_deg),
        "match_tol_deg": float(match_tol_deg),
        "no_interpolation": True,
        "source": "exact intersection of the stored screen H/V and BEM H/V direction grids",
        "stored_grid_counts": [int(grid.size) for grid in grids],
    }
    return common, record


def _select_angles(angles_deg: Any, target_deg: Sequence[float],
                   match_tol_deg: float = _ANGLE_MATCH_TOL_DEG) -> list[int]:
    """Indices of the stored angles that exactly match ``target_deg`` (no interpolation)."""
    stored = np.asarray(angles_deg, dtype=float).reshape(-1)
    indices: list[int] = []
    for target in target_deg:
        hits = np.nonzero(np.abs(stored - float(target)) <= float(match_tol_deg))[0]
        if hits.size != 1:
            raise CalibrationRecordError(
                "SCREEN_GRID_EMPTY",
                f"stored direction grid has {hits.size} sample(s) at {float(target):g} deg; "
                "exactly one is required and interpolation is refused")
        indices.append(int(hits[0]))
    return indices


def _relative_levels(levels_db: Any, angle_indices: Sequence[int],
                     on_axis_angle: float = 0.0, angles_deg: Any | None = None) -> np.ndarray:
    """Normalise each row at the on-axis stored sample (index resolved by angle)."""
    levels = np.asarray(levels_db, dtype=float)
    if levels.ndim != 2:
        raise CalibrationRecordError(
            "ESHAPE_INPUT_INVALID", f"levels must be (n_freqs, n_dirs), got {levels.shape}")
    if angles_deg is None:
        raise CalibrationRecordError(
            "SCREEN_GRID_EMPTY", "angles_deg is required to resolve the 0 deg sample")
    stored = np.asarray(angles_deg, dtype=float).reshape(-1)
    on_hits = np.nonzero(np.abs(stored - float(on_axis_angle)) <= _ON_AXIS_TOL_DEG)[0]
    if on_hits.size != 1:
        raise CalibrationRecordError(
            "SCREEN_GRID_NO_ON_AXIS",
            f"stored direction grid has {on_hits.size} sample(s) at {on_axis_angle:g} deg; "
            "refused instead of interpolating on axis")
    selected = levels[:, list(angle_indices)]
    on_axis_values = levels[:, int(on_hits[0])]
    rel = selected - on_axis_values[:, None]
    if not np.all(np.isfinite(rel)):
        raise CalibrationRecordError(
            "ESHAPE_INPUT_INVALID", "relative levels contain non-finite values")
    return rel


def map_frequencies(
    screen_freqs_hz: Any,
    bem_freqs_hz: Any,
    *,
    rel_tol: float = 0.02,
) -> tuple[list[dict[str, float]], dict[str, Any]]:
    """Nearest stored BEM frequency for every screen frequency, within ``rel_tol``.

    Returns the per-frequency mapping records and a summary dict.  A frequency whose nearest
    BEM sample lies outside the relative tolerance is refused with ``FREQUENCY_MAPPING_REFUSED``
    rather than interpolated.  Two screen frequencies may not collapse onto one BEM sample.
    """
    if not (math.isfinite(float(rel_tol)) and float(rel_tol) > 0.0):
        raise CalibrationRecordError(
            "SCREEN_CALIBRATION_INPUT_INVALID",
            f"rel_tol must be finite and > 0, got {rel_tol!r}")
    screen = np.asarray(screen_freqs_hz, dtype=float).reshape(-1)
    bem = np.asarray(bem_freqs_hz, dtype=float).reshape(-1)
    if screen.size == 0 or np.any(~np.isfinite(screen)) or np.any(screen <= 0.0):
        raise CalibrationRecordError(
            "SCREEN_CALIBRATION_INPUT_INVALID",
            "screen frequencies must be a non-empty finite positive list")
    if bem.size == 0 or np.any(~np.isfinite(bem)) or np.any(bem <= 0.0):
        raise CalibrationRecordError(
            "SCREEN_CALIBRATION_INPUT_INVALID",
            "BEM frequencies must be a non-empty finite positive list")

    mapping: list[dict[str, float]] = []
    failures: list[str] = []
    used: dict[int, float] = {}
    for freq in screen:
        index = int(np.argmin(np.abs(bem - float(freq))))
        mapped = float(bem[index])
        error = abs(mapped - float(freq)) / float(freq)
        if error > float(rel_tol):
            failures.append(
                f"screen {float(freq):.6g} Hz -> nearest stored BEM {mapped:.6g} Hz is "
                f"{error:.6g} relative away (> rel_tol {float(rel_tol):g})")
            continue
        if index in used:
            raise CalibrationRecordError(
                "FREQUENCY_MAPPING_DUPLICATE",
                f"screen frequencies {used[index]:.6g} Hz and {float(freq):.6g} Hz both map to "
                f"the same stored BEM frequency {mapped:.6g} Hz")
        used[index] = float(freq)
        mapping.append({
            "screen_hz": float(freq),
            "bem_hz": mapped,
            "relative_error": float(error),
        })
    if failures:
        raise CalibrationRecordError(
            "FREQUENCY_MAPPING_REFUSED",
            "no stored BEM frequency is within the tolerance for: " + "; ".join(failures) +
            ". Refused instead of interpolating the BEM frequency axis")
    mapping.sort(key=lambda row: row["screen_hz"])
    summary = {
        "rel_tol": float(rel_tol),
        "screen_freqs_hz": [float(f) for f in np.sort(screen)],
        "bem_freqs_hz": [float(f) for f in bem],
        "mapped_bem_freqs_hz": [row["bem_hz"] for row in mapping],
        "mapping": mapping,
        "relative_errors": [row["relative_error"] for row in mapping],
        "max_relative_error": max((row["relative_error"] for row in mapping), default=None),
        "no_interpolation": True,
        "selection": "nearest stored BEM frequency within rel_tol; no interpolation",
    }
    return mapping, summary


# --------------------------------------------------------------------------- input resolution


def _resolve_runs_root(screen_doc: Mapping[str, Any]) -> Path:
    for source in (screen_doc, screen_doc.get("asset")):
        if isinstance(source, Mapping):
            candidate = source.get("runs_root")
            if isinstance(candidate, str) and candidate:
                return Path(candidate)
    return HA.default_runs_root()


def _resolve_screen_response(
    screen_json: Path,
    screen_doc: Mapping[str, Any],
) -> tuple[Path, dict[str, Any]]:
    """Find the stored screen ``response.npz`` without guessing an asset identity."""
    asset = screen_doc.get("asset")
    asset = asset if isinstance(asset, Mapping) else {}
    explicit = None
    for source in (screen_doc, asset):
        for key in ("screen_response_path", "asset_response_path", "response_path"):
            value = source.get(key) if isinstance(source, Mapping) else None
            if isinstance(value, str) and value:
                explicit = value
                break
        if explicit:
            break

    hints: list[Path] = []
    if explicit:
        candidate = Path(explicit)
        if not candidate.is_absolute():
            candidate = (screen_json.parent / candidate).resolve()
        hints.append(candidate)
    else:
        design_hash = asset.get("design_hash") or screen_doc.get("design_hash")
        runs_root = _resolve_runs_root(screen_doc)
        if isinstance(design_hash, str) and design_hash:
            hints.extend(sorted(runs_root.glob(f"*/designs/{design_hash}/response.npz")))
            if not hints:
                hints.extend(sorted(runs_root.glob(f"*/*/designs/{design_hash}/response.npz")))
        if not hints:
            asset_id = asset.get("asset_id") or screen_doc.get("asset_id")
            if isinstance(asset_id, str) and asset_id:
                from hornlab_search.system import horn_import  # local import; bounded scan

                try:
                    found = horn_import.find_asset(asset_id, runs_root)
                except Exception as exc:  # noqa: BLE001 - translate into a record refusal
                    raise CalibrationRecordError(
                        "SCREEN_RESPONSE_UNRESOLVED",
                        f"could not locate a response for asset_id {asset_id!r} under "
                        f"{runs_root}: {exc}") from None
                hints.append(Path(found.response_path))

    existing = [path for path in dict.fromkeys(hints) if path.is_file()]
    if not existing:
        raise CalibrationRecordError(
            "SCREEN_RESPONSE_NOT_FOUND",
            "no stored screen response.npz was found; supply screen_response_path or a "
            f"design_hash/asset_id resolvable under {_resolve_runs_root(screen_doc)}")
    if len(existing) > 1:
        raise CalibrationRecordError(
            "SCREEN_RESPONSE_UNRESOLVED",
            f"{len(existing)} stored response.npz candidates matched "
            f"{[str(p) for p in existing]}; refusing an ambiguous identity")
    response_path = existing[0]
    sha = _sha256_file(response_path)
    declared = None
    sha_block = screen_doc.get("input_sha256")
    if isinstance(sha_block, Mapping):
        value = sha_block.get("asset_response_npz")
        if isinstance(value, str) and value:
            declared = value
    if declared is not None and declared != sha:
        raise CalibrationRecordError(
            "SCREEN_RESPONSE_SHA_MISMATCH",
            f"stored response {response_path} sha256 {sha} != declared {declared}")
    record = {
        "response_path": _posix(response_path),
        "response_sha256": sha,
        "response_sha256_declared": declared,
        "response_sha256_verified": declared is None or declared == sha,
        "resolution": ("explicit screen_response_path" if explicit
                       else "design_hash scan of the runs root" if asset.get("design_hash")
                       else "asset_id inventory scan"),
    }
    return response_path, record


def _select_screen_frequencies(
    screen_doc: Mapping[str, Any], stored_freqs_hz: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Select the stored screen band; never synthesises or interpolates a frequency."""
    stored = np.asarray(stored_freqs_hz, dtype=float).reshape(-1)
    explicit = screen_doc.get("screen_freqs_hz")
    if explicit is not None:
        requested = np.asarray(explicit, dtype=float).reshape(-1)
        if requested.size == 0 or np.any(~np.isfinite(requested)) or np.any(requested <= 0.0):
            raise CalibrationRecordError(
                "SCREEN_FREQUENCY_BAND_UNRESOLVED",
                "screen_freqs_hz must be a non-empty finite positive list")
        selected: list[float] = []
        for value in requested:
            hits = np.nonzero(np.abs(stored - float(value)) <= 1e-6 * max(1.0, float(value)))[0]
            if hits.size != 1:
                raise CalibrationRecordError(
                    "SCREEN_FREQUENCY_BAND_UNRESOLVED",
                    f"screen frequency {float(value):g} Hz is not exactly one stored sample")
            selected.append(float(stored[int(hits[0])]))
        return np.asarray(selected, dtype=float), {
            "f_x_hz": None,
            "half_octaves": None,
            "band_hz": None,
            "freqs_hz": selected,
            "selection": "explicit screen_freqs_hz (stored samples only)",
        }

    f_x = screen_doc.get("f_x_hz") or screen_doc.get("screen_f_x_hz")
    if f_x is None:
        shortlist = screen_doc.get("shortlist")
        if isinstance(shortlist, list):
            values = {float(row["xo_hz"]) for row in shortlist
                      if isinstance(row, Mapping) and row.get("xo_hz") is not None}
            if len(values) == 1:
                f_x = values.pop()
            elif len(values) > 1:
                raise CalibrationRecordError(
                    "SCREEN_FREQUENCY_BAND_UNRESOLVED",
                    f"the screen shortlist records multiple distinct crossovers {sorted(values)}; "
                    "pass screen_freqs_hz or screen_f_x_hz explicitly")
    if f_x is None:
        raise CalibrationRecordError(
            "SCREEN_FREQUENCY_BAND_UNRESOLVED",
            "the screen study does not record a unique screen band/crossover; pass "
            "screen_freqs_hz or screen_f_x_hz explicitly")

    metric_spec = screen_doc.get("metric_spec")
    half_octaves = compatibility.DEFAULT_OVERLAP_HALF_OCTAVES
    if isinstance(metric_spec, Mapping) and metric_spec.get("half_octaves") is not None:
        half_octaves = float(metric_spec["half_octaves"])
    band = compatibility.select_overlap_band(
        stored, float(f_x), half_octaves=half_octaves,
        min_freqs=compatibility.DEFAULT_MIN_BAND_FREQS)
    if not band.accepted:
        raise CalibrationRecordError(
            "SCREEN_FREQUENCY_BAND_UNRESOLVED",
            f"no stored screen band around {float(f_x):g} Hz: " + "; ".join(band.reasons))
    return np.asarray(band.freqs_hz, dtype=float), {
        "f_x_hz": float(f_x),
        "half_octaves": float(half_octaves),
        "band_hz": [float(band.f_lo_hz), float(band.f_hi_hz)],
        "freqs_hz": [float(f) for f in band.freqs_hz],
        "selection": "compatibility.select_overlap_band on stored screen frequencies",
    }


def _load_ts_document(entry: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Load the T/S YAML referenced by one screen catalog entry, if present."""
    ts_file = entry.get("ts_file")
    if not isinstance(ts_file, str) or not ts_file:
        return None
    candidates = [
        driver_data.REPO_ROOT / "examples" / "systems" / "driver_ts" / ts_file,
        driver_data.REPO_ROOT / "examples" / "drivers" / ts_file,
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            import yaml  # PyYAML is already a project dependency (system.drivers)

            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(payload, Mapping):
            return payload
    return None


def _motor_patch_parameters(case_dir: Path) -> Mapping[str, float] | None:
    patch = case_dir / "motor_patch.json"
    if not patch.is_file():
        patch = case_dir.parent / "motor_patch.json"
    if not patch.is_file():
        return None
    try:
        payload = json.loads(patch.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    components = payload.get("component_parameters") if isinstance(payload, Mapping) else None
    if not isinstance(components, Mapping):
        return None
    for value in components.values():
        if not isinstance(value, Mapping):
            continue
        keys = ("re_ohm", "bl_n_per_a", "mmd_kg", "cms_m_per_n", "le_h", "rms_n_s_per_m")
        if all(isinstance(value.get(key), (int, float)) for key in keys):
            return {key: float(value[key]) for key in keys}
    return None


def _motor_matches_entry(motor: Mapping[str, float], ts: Mapping[str, Any]) -> Mapping[str, float] | None:
    pairs = (
        ("re_ohm", "re_ohm", 1.0),
        ("bl_n_per_a", "bl_tm", 1.0),
        ("mmd_kg", "mmd_g", 1.0e-3),
        ("cms_m_per_n", "cms_mm_per_n", 1.0e-3),
        ("le_h", "le_mh", 1.0e-3),
        ("rms_n_s_per_m", "rms_kg_s", 1.0),
    )
    matched: dict[str, float] = {}
    for patch_key, ts_key, scale in pairs:
        ts_value = ts.get(ts_key)
        if not isinstance(ts_value, (int, float)) or isinstance(ts_value, bool):
            return None
        expected = float(ts_value) * scale
        actual = float(motor[patch_key])
        if not math.isclose(actual, expected, rel_tol=_TS_MATCH_REL_TOL, abs_tol=1e-15):
            return None
        matched[patch_key] = actual
    return matched


def _select_driver(
    screen_doc: Mapping[str, Any],
    case_dir: Path,
    driver_id: str | None,
) -> tuple[Mapping[str, Any], dict[str, Any]]:
    """Resolve the screen piston driver and its effective radius, without guessing."""
    catalog = screen_doc.get("catalog")
    catalog = [row for row in catalog if isinstance(row, Mapping)] if isinstance(catalog, list) else []
    effective_ids = [driver_id, screen_doc.get("driver_id")]
    for wanted in (value for value in effective_ids if isinstance(value, str) and value):
        for entry in catalog:
            if entry.get("driver_id") == wanted:
                return entry, {"method": "explicit_driver_id", "driver_id": wanted}
        raise CalibrationRecordError(
            "DRIVER_IDENTITY_UNRESOLVED",
            f"driver_id {wanted!r} is not present in the screen catalog "
            f"{[e.get('driver_id') for e in catalog]}")

    if len(catalog) == 1:
        return catalog[0], {"method": "single_catalog_entry",
                            "driver_id": catalog[0].get("driver_id")}

    motor = _motor_patch_parameters(case_dir)
    if motor is not None and catalog:
        matches: list[tuple[Mapping[str, Any], Mapping[str, float]]] = []
        for entry in catalog:
            ts = _load_ts_document(entry)
            if ts is None:
                continue
            matched = _motor_matches_entry(motor, ts)
            if matched is not None:
                matches.append((entry, matched))
        if len(matches) == 1:
            entry, matched = matches[0]
            return entry, {
                "method": "motor_patch_ts_match",
                "driver_id": entry.get("driver_id"),
                "matched_patch_fields": sorted(matched),
            }
        if len(matches) > 1:
            raise CalibrationRecordError(
                "DRIVER_IDENTITY_UNRESOLVED",
                f"the BEM motor patch matches multiple screen catalog drivers "
                f"{[e.get('driver_id') for e, _ in matches]}; pass driver_id explicitly")
    raise CalibrationRecordError(
        "DRIVER_IDENTITY_UNRESOLVED",
        "cannot select the screen piston driver: the study catalog has "
        f"{len(catalog)} entries and no unique BEM motor-patch T/S match; pass driver_id "
        "explicitly or add an effective_piston_radius_m to the screen document")


def _driver_radius(entry: Mapping[str, Any], screen_doc: Mapping[str, Any]) -> tuple[float, dict[str, Any]]:
    override = screen_doc.get("piston_radius_m") or screen_doc.get("screen_piston_radius_m")
    if override is not None:
        radius = float(override)
        if not (math.isfinite(radius) and radius > 0.0):
            raise CalibrationRecordError(
                "DRIVER_IDENTITY_UNRESOLVED", f"piston radius must be finite and > 0, got {override!r}")
        return radius, {"source": "explicit screen document piston_radius_m", "sd_cm2": None}
    radius_value = entry.get("effective_piston_radius_m")
    sd_cm2 = entry.get("sd_cm2")
    if isinstance(radius_value, (int, float)) and not isinstance(radius_value, bool):
        radius = float(radius_value)
        if not (math.isfinite(radius) and radius > 0.0):
            raise CalibrationRecordError(
                "DRIVER_IDENTITY_UNRESOLVED",
                f"catalog effective_piston_radius_m must be finite and > 0, got {radius_value!r}")
        return radius, {"source": "catalog effective_piston_radius_m",
                        "sd_cm2": float(sd_cm2) if isinstance(sd_cm2, (int, float)) else None}
    if isinstance(sd_cm2, (int, float)) and not isinstance(sd_cm2, bool):
        area = float(sd_cm2) * 1e-4
        if not (math.isfinite(area) and area > 0.0):
            raise CalibrationRecordError(
                "DRIVER_IDENTITY_UNRESOLVED", f"catalog sd_cm2 must be > 0, got {sd_cm2!r}")
        return math.sqrt(area / math.pi), {"source": "catalog sd_cm2 -> radius",
                                           "sd_cm2": float(sd_cm2)}
    raise CalibrationRecordError(
        "DRIVER_IDENTITY_UNRESOLVED",
        "the selected screen driver has neither effective_piston_radius_m nor sd_cm2")


def _resolve_bem_result_dir(bem_run_dir: Path) -> Path:
    if bl_results.is_bl_headless_result_dir(bem_run_dir):
        return bem_run_dir
    nested = bem_run_dir / "run"
    if bl_results.is_bl_headless_result_dir(nested):
        return nested
    raise CalibrationRecordError(
        "BEM_RESULT_UNRESOLVED",
        f"{bem_run_dir} is neither a BL headless result directory nor a case directory "
        "containing one at run/")


def _plane_domains(result: Any) -> dict[str, str]:
    available = list(result.domain_ids())
    domains: dict[str, str] = {}
    for plane, exact, hint in (
        ("H", _H_PLANE_DOMAIN, _PLANE_DOMAIN_HINTS["H"]),
        ("V", _V_PLANE_DOMAIN, _PLANE_DOMAIN_HINTS["V"]),
    ):
        if exact in available:
            domains[plane] = exact
            continue
        matches = [domain for domain in available
                   if hint in domain.lower() and "polar" in domain.lower()]
        if len(matches) != 1:
            raise CalibrationRecordError(
                "BEM_PLANE_UNRESOLVED",
                f"expected exactly one {plane} polar domain; available {available}")
        domains[plane] = matches[0]
    return domains


def _excitation_ids(result: Any) -> tuple[str, str]:
    ids = list(result.excitation_ids)
    horn = [value for value in ids if "horn" in value.lower()]
    if len(horn) != 1:
        raise CalibrationRecordError(
            "BEM_EXCITATION_UNRESOLVED",
            f"expected exactly one horn excitation, found {horn} in {ids}")
    horn_id = horn[0]
    woofer = [value for value in ids
              if value != horn_id and ("woofer" in value.lower()
                                       or "vented" in value.lower()
                                       or "voltage" in value.lower())]
    if not woofer:
        rest = [value for value in ids if value != horn_id]
        woofer = rest if len(rest) == 1 else []
    if len(woofer) != 1:
        raise CalibrationRecordError(
            "BEM_EXCITATION_UNRESOLVED",
            f"expected exactly one woofer excitation, found {woofer} in {ids}")
    return horn_id, woofer[0]


def _db_magnitude(pressure: np.ndarray) -> np.ndarray:
    magnitude = np.abs(np.asarray(pressure, dtype=np.complex128))
    if not np.all(np.isfinite(magnitude)) or np.any(magnitude <= 0.0):
        raise CalibrationRecordError(
            "BEM_PRESSURE_INVALID",
            "BEM pressure contains a non-finite or exactly-zero magnitude; relative levels "
            "cannot be formed")
    return 20.0 * np.log10(magnitude)


def _axis_block(
    *,
    plane: str,
    domain_id: str,
    screen_rel: np.ndarray,
    piston_rel: np.ndarray,
    horn_rel: np.ndarray,
    woofer_rel: np.ndarray,
    screen_freqs_hz: np.ndarray,
    mapping: Sequence[Mapping[str, float]],
) -> dict[str, Any]:
    screen_e = eshape_db2(screen_rel, piston_rel)
    bem_e = eshape_db2(horn_rel, woofer_rel)
    screen_per_freq = np.mean(np.square(screen_rel - piston_rel), axis=1)
    bem_per_freq = np.mean(np.square(horn_rel - woofer_rel), axis=1)
    per_freq: list[dict[str, Any]] = []
    factors: list[float | None] = []
    for index, row in enumerate(mapping):
        screen_value = float(screen_per_freq[index])
        bem_value = float(bem_per_freq[index])
        factor = (bem_value / screen_value) if screen_value > 0.0 else None
        factors.append(factor)
        per_freq.append({
            "screen_hz": float(row["screen_hz"]),
            "bem_hz": float(row["bem_hz"]),
            "screen_e_shape_db2": screen_value,
            "bem_e_shape_db2": bem_value,
            "screen_to_bem_factor": factor,
        })
    defined = [float(value) for value in factors if value is not None]
    overall = (bem_e / screen_e) if screen_e > 0.0 else None
    return {
        "plane": plane,
        "bem_domain": domain_id,
        "screen_e_shape_db2": screen_e,
        "bem_e_shape_db2": bem_e,
        "screen_to_bem_factor": overall,
        "ratio": overall,
        "factor_is_ratio_of_db2": True,
        "factor_defined": overall is not None,
        "factor_spread": {
            "per_freq_factors": factors,
            "min": min(defined) if defined else None,
            "max": max(defined) if defined else None,
            "range": (max(defined) - min(defined)) if defined else None,
            "std_population": (float(np.std(defined)) if defined else None),
            "n_defined": len(defined),
        },
        "screen_e_shape_spread": {
            "per_freq_db2": [float(value) for value in screen_per_freq],
            "min": float(np.min(screen_per_freq)) if screen_per_freq.size else None,
            "max": float(np.max(screen_per_freq)) if screen_per_freq.size else None,
            "range": (float(np.max(screen_per_freq) - np.min(screen_per_freq))
                      if screen_per_freq.size else None),
            "std_population": (float(np.std(screen_per_freq)) if screen_per_freq.size else None),
        },
        "bem_e_shape_spread": {
            "per_freq_db2": [float(value) for value in bem_per_freq],
            "min": float(np.min(bem_per_freq)) if bem_per_freq.size else None,
            "max": float(np.max(bem_per_freq)) if bem_per_freq.size else None,
            "range": (float(np.max(bem_per_freq) - np.min(bem_per_freq))
                      if bem_per_freq.size else None),
            "std_population": (float(np.std(bem_per_freq)) if bem_per_freq.size else None),
        },
        "n_dirs": int(screen_rel.shape[1]),
        "n_freqs": int(screen_rel.shape[0]),
        "screen_freqs_hz": [float(value) for value in screen_freqs_hz],
        "bem_freqs_hz": [float(row["bem_hz"]) for row in mapping],
        "screen_rel_db": _jsonable(screen_rel),
        "piston_rel_db": _jsonable(piston_rel),
        "bem_horn_rel_db": _jsonable(horn_rel),
        "bem_woofer_rel_db": _jsonable(woofer_rel),
        "units": "dB^2",
        "formula": ("mean_f mean_dir (L_a,rel - L_b,rel)^2; each channel normalised at 0 deg; "
                    "uniform weights; no dB-power averaging"),
        "per_freq": per_freq,
    }


def _published_screen_values(
    screen_doc: Mapping[str, Any], driver_id: Any, f_x_hz: float | None,
) -> dict[str, Any]:
    if not isinstance(driver_id, str) or f_x_hz is None:
        return {}
    screens = screen_doc.get("xo_screens")
    if not isinstance(screens, Mapping):
        return {}
    block = screens.get(driver_id)
    candidates = block.get("candidates") if isinstance(block, Mapping) else None
    if not isinstance(candidates, list):
        return {}
    best = None
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        value = candidate.get("f_x_hz")
        if isinstance(value, (int, float)) and math.isclose(float(value), float(f_x_hz),
                                                            rel_tol=1e-9, abs_tol=1e-9):
            best = candidate
            break
    if best is None:
        return {}
    planes = best.get("planes") if isinstance(best.get("planes"), Mapping) else {}
    out: dict[str, Any] = {"f_x_hz": float(f_x_hz), "source": "stored screen xo_screens block"}
    for plane in ("H", "V"):
        plane_block = planes.get(plane) if isinstance(planes, Mapping) else None
        if isinstance(plane_block, Mapping):
            out[plane] = {
                "e_shape_db2": plane_block.get("e_shape_db2"),
                "n_dirs": plane_block.get("n_dirs"),
                "n_freqs": plane_block.get("n_freqs"),
                "band_freqs_hz": plane_block.get("band_freqs_hz"),
            }
    return out


# --------------------------------------------------------------------------- public builder


def build_calibration_record(
    screen_json: str | Path,
    bem_run_dir: str | Path,
    *,
    rel_tol: float = 0.02,
    max_deg: float = 30.0,
    driver_id: str | None = None,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    """Build the read-only screen-vs-installed-BEM ``E_shape`` calibration record.

    ``screen_json`` is the stored screen study JSON (for the real local input,
    ``system_runs/screens/system_evidence_2026-11-19/woofer_seed.json``).  ``bem_run_dir`` may
    be the BL headless result directory or its containing case directory.  ``driver_id`` and
    ``generated_utc`` are optional determinism/identity pins; when ``generated_utc`` is omitted
    the current UTC time is stamped.

    The function never writes anything; use :func:`write_calibration_record` for that.
    """
    screen_path = Path(screen_json)
    screen_doc = _mapping(_read_json(screen_path, "SCREEN_CALIBRATION_INPUT_INVALID",
                                     "screen study JSON"),
                          "SCREEN_CALIBRATION_INPUT_INVALID", "screen study JSON")
    bem_case = Path(bem_run_dir)
    result_dir = _resolve_bem_result_dir(bem_case)

    asset = screen_doc.get("asset")
    asset = asset if isinstance(asset, Mapping) else {}
    study_id = screen_doc.get("study_id")
    asset_id = asset.get("asset_id") or screen_doc.get("asset_id")
    if not isinstance(study_id, str) or not study_id:
        raise CalibrationRecordError(
            "SCREEN_CALIBRATION_INPUT_INVALID", "screen study JSON has no string study_id")
    if not isinstance(asset_id, str) or not asset_id:
        raise CalibrationRecordError(
            "SCREEN_CALIBRATION_INPUT_INVALID", "screen study JSON has no string asset_id")

    response_path, response_record = _resolve_screen_response(screen_path, screen_doc)
    try:
        screen_response = solve_cache.load_response(response_path)
    except Exception as exc:  # noqa: BLE001 - translate into a record refusal
        raise CalibrationRecordError(
            "SCREEN_RESPONSE_UNRESOLVED",
            f"could not load stored screen response {response_path}: {exc}") from None
    stored_freqs = np.asarray(screen_response.freqs_hz, dtype=float).reshape(-1)
    screen_freqs, band_record = _select_screen_frequencies(screen_doc, stored_freqs)

    driver_entry, driver_selection = _select_driver(screen_doc, bem_case, driver_id)
    radius_m, radius_record = _driver_radius(driver_entry, screen_doc)
    selected_driver_id = driver_selection.get("driver_id") or driver_entry.get("driver_id")

    try:
        result = bl_results.read_bl_headless_result(result_dir)
    except Exception as exc:  # noqa: BLE001 - translate into a record refusal
        raise CalibrationRecordError(
            "BEM_RESULT_UNRESOLVED", f"could not read BL headless result {result_dir}: {exc}") from None
    horn_id, woofer_id = _excitation_ids(result)
    domains = _plane_domains(result)

    # ---- exact common direction grid across both planes and both artifacts
    screen_h_angles = getattr(screen_response, "h_angles_deg", None)
    screen_v_angles = getattr(screen_response, "v_angles_deg", None)
    if screen_h_angles is None or screen_v_angles is None:
        raise CalibrationRecordError(
            "SCREEN_GRID_EMPTY", "the stored screen response has no H/V direction grids")
    bem_h_angles = result.observation_sets[domains["H"]].angles_deg
    bem_v_angles = result.observation_sets[domains["V"]].angles_deg
    if bem_h_angles is None or bem_v_angles is None:
        raise CalibrationRecordError(
            "SCREEN_GRID_EMPTY", "the BEM polar domains have no stored angle_deg coordinates")
    common_angles, grid_record = common_direction_grid(
        screen_h_angles, screen_v_angles, bem_h_angles, bem_v_angles, max_deg=max_deg)

    # ---- frequency nearest-map (no interpolation)
    mapping, frequency_record = map_frequencies(
        screen_freqs, result.frequencies_hz, rel_tol=rel_tol)
    screen_freqs = np.asarray([row["screen_hz"] for row in mapping], dtype=float)
    bem_freq_indices = [int(np.argmin(np.abs(result.frequencies_hz - row["bem_hz"])))
                        for row in mapping]

    # ---- screen levels and the analytic piston reference on the common grid
    screen_angle_indices_h = _select_angles(screen_h_angles, common_angles)
    screen_angle_indices_v = _select_angles(screen_v_angles, common_angles)
    piston_rel = np.asarray(
        piston.relative_level_db(screen_freqs, radius_m, np.asarray(common_angles, dtype=float)),
        dtype=float)
    if not np.all(np.isfinite(piston_rel)):
        raise CalibrationRecordError(
            "ESHAPE_INPUT_INVALID", "analytic piston reference is not finite on the grid")

    screen_levels_h = getattr(screen_response, "spl_h_db", None)
    screen_levels_v = getattr(screen_response, "spl_v_db", None)
    if screen_levels_h is None or screen_levels_v is None:
        raise CalibrationRecordError(
            "SCREEN_RESPONSE_UNRESOLVED",
            "the stored screen response has no spl_h_db/spl_v_db level arrays")
    screen_levels_h = np.asarray(screen_levels_h, dtype=float)
    screen_levels_v = np.asarray(screen_levels_v, dtype=float)
    screen_freq_indices = [int(np.argmin(np.abs(stored_freqs - f))) for f in screen_freqs]
    for plane, levels, indices in (
        ("H", screen_levels_h, screen_angle_indices_h),
        ("V", screen_levels_v, screen_angle_indices_v),
    ):
        if levels.shape[0] != stored_freqs.size or levels.shape[1] != np.asarray(
                screen_h_angles if plane == "H" else screen_v_angles).size:
            raise CalibrationRecordError(
                "SCREEN_RESPONSE_UNRESOLVED",
                f"stored {plane} level array shape {levels.shape} does not match its grids")
        del indices
    screen_rel_h = _relative_levels(screen_levels_h[screen_freq_indices, :],
                                    screen_angle_indices_h, angles_deg=screen_h_angles)
    screen_rel_v = _relative_levels(screen_levels_v[screen_freq_indices, :],
                                    screen_angle_indices_v, angles_deg=screen_v_angles)

    # ---- BEM levels per plane and excitation, on the same exact grid
    axes: dict[str, Any] = {}
    for plane, screen_rel in (("H", screen_rel_h), ("V", screen_rel_v)):
        domain_id = domains[plane]
        bem_angles = result.observation_sets[domain_id].angles_deg
        angle_indices = _select_angles(bem_angles, common_angles)
        bases = result.per_excitation_bases(domain_id)
        if horn_id not in bases or woofer_id not in bases:
            raise CalibrationRecordError(
                "BEM_EXCITATION_UNRESOLVED",
                f"domain {domain_id!r} is missing excitation {horn_id!r} or {woofer_id!r}; "
                f"present {sorted(bases)}")
        horn_db = _db_magnitude(bases[horn_id])[np.ix_(bem_freq_indices, angle_indices)]
        woofer_db = _db_magnitude(bases[woofer_id])[np.ix_(bem_freq_indices, angle_indices)]
        horn_rel = _relative_levels(horn_db, list(range(len(angle_indices))),
                                    angles_deg=np.asarray(bem_angles)[angle_indices])
        woofer_rel = _relative_levels(woofer_db, list(range(len(angle_indices))),
                                      angles_deg=np.asarray(bem_angles)[angle_indices])
        axes[plane] = _axis_block(
            plane=plane, domain_id=domain_id, screen_rel=screen_rel, piston_rel=piston_rel,
            horn_rel=horn_rel, woofer_rel=woofer_rel, screen_freqs_hz=screen_freqs,
            mapping=mapping)

    published = _published_screen_values(screen_doc, selected_driver_id, band_record.get("f_x_hz"))
    quality = ("READ-ONLY calibration check on the exact common stored grid; no solve, filter, "
               "sum, score or recalibration; the screen->BEM factors are confounded by R2 and "
               "must not be used as a correction")
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_utc": generated_utc if generated_utc is not None else _utc_now(),
        "study_id": study_id,
        "asset_id": asset_id,
        "status": "QUANTIFIED_NOT_RECALIBRATED",
        "recalibrated": False,
        "screen_study": {
            "path": _posix(screen_path),
            "study_id": study_id,
            "asset_id": asset_id,
            "design_hash": asset.get("design_hash"),
            "asset_quality": asset.get("quality"),
            "brief_id": asset.get("brief_id"),
            "family": asset.get("family"),
            "response": response_record,
            "driver": {
                "driver_id": selected_driver_id,
                "name": driver_entry.get("name"),
                "sd_cm2": radius_record.get("sd_cm2"),
                "effective_piston_radius_m": radius_m,
                "selection": driver_selection,
                "radius_source": radius_record.get("source"),
            },
            "frequency_band": band_record,
            "published_as_stored": published,
        },
        "bem": {
            "case_dir": _posix(bem_case),
            "result_dir": _posix(result_dir),
            "horn_excitation": horn_id,
            "woofer_excitation": woofer_id,
            "per_input": {field.excitation_id: field.basis.per_input
                          for field in result.fields},
            "planes": domains,
            "status": result.provenance.status,
            "source_geometry_hash": result.provenance.source_geometry_hash,
        },
        "common_grid": grid_record,
        "frequency_map": frequency_record,
        "axes": axes,
        "confound_tokens": [CONFOUND_DEMO_SHAPE_R2],
        "confounds": {
            CONFOUND_DEMO_SHAPE_R2: {
                "present": True,
                "bem_woofer_shape": "R2 demo 200 mm transducer shape",
                "screen_piston_shape": f"selected real driver {selected_driver_id!r} effective area",
                "detail": ("the installed BEM woofer uses the R2 demo 200 mm transducer shape "
                           "while the screen piston uses the selected real driver's effective "
                           "area; the screen->BEM factor is confounded and is not a calibrated "
                           "correction"),
            },
        },
        "threshold": {
            "name": "good_match_db2",
            "value_db2": float(compatibility.DEFAULT_GOOD_MATCH_DB2),
            "token": TOKEN_THRESHOLD_UNCHANGED,
            "changed": False,
            "recalibrated": False,
            "detail": ("the provisional 9.0 dB^2 good-match label is unchanged; this record "
                       "quantifies the box-axis gap and does not recalibrate the threshold"),
        },
        "tokens": [CONFOUND_DEMO_SHAPE_R2, TOKEN_THRESHOLD_UNCHANGED],
        "claim": ("screen E_shape is optimistic on the installed-BEM box axis; the factor is "
                  "confounded by R2 and a real-shape/denser-grid case is required before any "
                  "recalibration. No recalibration is claimed here."),
        "data_quality": quality,
    }
    return _jsonable(record)


def record_to_json(record: Mapping[str, Any]) -> str:
    """Stable JSON text (sorted keys, fixed indent, trailing newline)."""
    return json.dumps(_jsonable(record), sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def write_calibration_record(record: Mapping[str, Any], path: str | Path) -> Path:
    """Write one record deterministically; only ``generated_utc`` varies between runs."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record_to_json(record), encoding="utf-8", newline="\n")
    return target


# --------------------------------------------------------------------------- CLI (no cli.py edit)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m hornlab_search.system.screen_calibration",
        description="Build the read-only R7a screen-vs-installed-BEM E_shape calibration record.")
    parser.add_argument("screen_json", help="stored screen study JSON (e.g. woofer_seed.json)")
    parser.add_argument("bem_run_dir", help="BL headless result directory or its case directory")
    parser.add_argument("--out", required=True, help="output JSON path")
    parser.add_argument("--rel-tol", type=float, default=0.02)
    parser.add_argument("--max-deg", type=float, default=30.0)
    parser.add_argument("--driver-id", default=None)
    parser.add_argument("--generated-utc", default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        record = build_calibration_record(
            args.screen_json, args.bem_run_dir, rel_tol=args.rel_tol, max_deg=args.max_deg,
            driver_id=args.driver_id, generated_utc=args.generated_utc)
    except CalibrationRecordError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    target = write_calibration_record(record, args.out)
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by the explicit real-data run
    raise SystemExit(main())
