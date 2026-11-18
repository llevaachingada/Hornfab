"""Stage 2 fixed-horn CPU pilot: box feasibility + LF headroom + polar handoff screen.

Scope (master handoff §6/§7, mode A):
* LF: real driver T/S + the fixed ``tools/bassbox.py`` lumped vented model through
  :mod:`hornlab_search.system.bass_reference` — feasibility, F3, headroom, limiting factors.
* Polar: saved horn balloon magnitude vs the ideal-piston woofer benchmark
  (:mod:`hornlab_search.system.piston`) — noncoherent level screens ONLY. The horn side may be
  ``SCREEN_COMPLEX_APPROX`` (converted stored accelerate basis) but the woofer side here is the
  ideal piston, so NOTHING in this stage claims a coherent system response, and relative
  DSP delay is fixed at 0 with the claim explicitly refused.
* Reports: report-only per-axis rows (lane D's :mod:`hornlab_search.system.score` conventions);
  deterministic; ids stamped with the system domains; hard gates are booleans, never a scalar J.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from hornlab_search.meh.drivers import load_cone
from hornlab_search.system import bass_reference, contracts as C, score, drivers as sys_drivers
from hornlab_search.system import horn_import
from hornlab_search.system import piston
from hornlab_search.system import provenance
from hornlab_search.system.geometry import rules as fit_rules

__all__ = ["PilotResult", "run_pilot", "horn_balloon_beamwidth_curve"]

_DEFAULT_TS_DIR = Path(__file__).resolve().parents[2] / "examples" / "systems" / "driver_ts"

#: A robust polar mismatch flag threshold at the crossover band (degrees). Screening rejects
#: only large, robust mismatches (master doc §6 tier 2); it does NOT rank small differences.
BW_MISMATCH_FLAG_DEG = 30.0


@dataclass
class PilotResult:
    """All deterministic pilot outputs (rows already in lane D's report convention)."""

    spec_hash: str
    asset: C.HornAsset | None
    converted: horn_import.ConvertedHorn | None
    driver: C.WooferDriver
    boxes: tuple[C.BoxPoint, ...]
    report: Mapping[str, str]           # score.render_report output (markdown + json)
    rows: tuple[dict, ...]
    meta: dict[str, Any] = field(default_factory=dict)

    def to_manifest_payload(self) -> dict[str, Any]:
        return {
            "kind": "system_pilot_v0",
            "study_id": self.spec_hash,
            "asset": None if self.asset is None else self.asset.asset_id,
            "converted": None if self.converted is None else self.converted.to_dict(),
            "driver": {
                "driver_id": self.driver.driver_id,
                "cone_name": self.driver.cone.name,
                "source": self.driver.cone.source,
                "data_quality": dict(self.driver.data_quality),
                "provenance": dict(self.driver.provenance),
            },
            "n_boxes": len(self.boxes),
            "meta": dict(self.meta),
            "rows": list(self.rows),
        }


def horn_balloon_beamwidth_screen(converted: Any,
                                  ) -> tuple[np.ndarray, np.ndarray, str]:
    """First -6 dB angular radius per frequency from the converted balloon (screening only).

    Reference level per frequency is the balloon maximum (approximate main lobe); the returned
    angle is the smallest 3-D angle from the peak direction where the level falls 6 dB below it.
    Returned as ``(freqs_hz, beamwidth_deg, label)``; ``label`` documents the approximation.
    """
    response = converted.response
    if response.p_by_excitation is None:
        raise C.DataQualityError("no complex balloon field; magnitude screen only")
    p = response.p_by_excitation["horn"]
    dirs = response.observation_directions
    if dirs is None or p.shape[1] != dirs.shape[0]:
        raise C.DataQualityError("balloon field and directions disagree")
    db = 20.0 * np.log10(np.maximum(np.abs(p), 1e-30))
    ang = np.degrees(np.arccos(np.clip(dirs @ dirs[np.argmax(db[0])], -1.0, 1.0)))
    order = np.argsort(ang)
    ang_sorted = ang[order]
    f = response.frequencies_hz
    bw = np.full(f.shape, np.nan)
    label = ("6 dB angular radius below the strongest direction; balloon grid; "
             "screen-only approximation of the main lobe width")
    for i in range(f.size):
        curve = db[i][order]
        ref = float(curve[0])
        below = np.nonzero(curve <= ref - 6.0)[0]
        if below.size:
            j = int(below[0])
            if j == 0:
                bw[i] = 0.0
            else:  # linear interpolation between the last above-6dB and first below-6dB samples
                a0, a1 = float(ang_sorted[j - 1]), float(ang_sorted[j])
                c0, c1 = float(curve[j - 1]), float(curve[j])
                bw[i] = a0 + (a1 - a0) * ((ref - 6.0) - c0) / (c1 - c0) if c1 != c0 else a1
    return f, bw, label


def _feasibility_row(point: C.BoxPoint, driver_geometry: C.DriverGeometry | None) -> dict[str, Any]:
    """Fabrication rules return status strings (PASS:/FAIL:/skip:); skips are recorded, FAILs gate."""
    statuses = {
        "port": fit_rules.check_port_fits(point),
        "clearance": fit_rules.check_driver_and_brace_clearance(point, driver_geometry),
        "wall": fit_rules.check_wall_thickness(point),
        "horn_clearance": fit_rules.check_woofer_horn_clearance(point, driver_geometry),
    }
    reasons = [f"{name}: {text}" for name, text in statuses.items() if text.startswith("FAIL")]
    skips = [f"{name}: {text}" for name, text in statuses.items() if text.startswith("skip")]
    return {
        "passed": not reasons,          # a skip is not a gate, but it is always disclosed
        "reasons": reasons,
        "skips": skips,
        "statuses": statuses,
    }


def _xo_grid(dsp: C.DspRanges) -> list[float]:
    lo, hi = dsp.xo_hz_range
    return [lo, 0.5 * (lo + hi), hi]


def run_pilot(
    spec: C.SystemSpecV1,
    *,
    driver_stem: str | None = None,
    driver_ts_dir: str | os.PathLike[str] | None = None,
    geometry_path: str | os.PathLike[str] | None = None,
    runs_root: str | os.PathLike[str] | None = None,
    asset_id: str | None = None,
    scan_limit: int = 300,
    limit_boxes: int = 8,
    out_dir: str | os.PathLike[str] | None = None,
) -> PilotResult:
    """One fixed-horn pilot: deterministic, CPU-only, no solver, no GPU, no file writes
    except the optional case manifest under the isolated system store."""
    stem = driver_stem or spec.woofer.driver_id
    ts_dir = Path(driver_ts_dir) if driver_ts_dir is not None else _DEFAULT_TS_DIR
    directory = ts_dir if ts_dir.is_dir() else None
    cone = load_cone(stem, directory=directory)
    geometry = sys_drivers.load_driver_geometry(Path(geometry_path)) if geometry_path is not None else None
    driver = C.WooferDriver(
        driver_id=stem, cone=cone,
        geometry_mm=None if geometry is None else geometry.geometry,
        provenance={"driver_ts_dir": str(ts_dir if ts_dir.is_dir() else "examples/drivers"),
                    "source": cone.source,
                    "geometry": None if geometry is None else {
                        "driver_id": geometry.driver_id,
                        "measured_by": geometry.measured_by,
                        "sourced_from": list(geometry.sourced_from),
                        "present_fields": list(geometry.present_fields)}},
        data_quality={"ts_source_present": bool(cone.source),
                      "has_full_geometry": geometry is not None
                      and bool(geometry.completeness["INSTALLED_EXTERIOR_BEM"]),
                      "supports_lf_ts_screening": True})
    if geometry is not None:
        sys_drivers.require_fidelity(driver, "LF_TS_SCREENING")

    # 1. horn asset (optional for the LF-only path but required for the polar screen)
    asset = converted = None
    if asset_id:
        asset = horn_import.find_asset(asset_id, runs_root, scan_limit=scan_limit)
        converted = horn_import.convert_asset(asset)

    # 2. feasible boxes (deterministic grids inside bass_reference). Selection keeps a
    # VOLUME SPREAD of the feasible set (smallest half + largest half of the kept count):
    # keeping only the smallest boxes would bias the screen against LF-extension solutions
    # and hide exactly the candidates the master doc cares about ("include exploration
    # diversity"). The feasibility screen still rejects, it does not rank.
    all_boxes = bass_reference.feasible_boxes(cone, spec.cabinet)
    all_boxes.sort(key=lambda b: (b.net_volume_l, b.requested_tuning_hz))
    n = max(1, int(limit_boxes))
    if len(all_boxes) > n:
        half = n // 2
        head = all_boxes[:half]
        tail = all_boxes[-(n - half):]
        boxes = tuple(head + tail)
    else:
        boxes = tuple(all_boxes)

    # 3. polar handoff screen (noncoherent): horn balloon 6 dB width vs ideal piston
    f3_target = spec.target.low_freq_f3_hz_max
    xo_points = _xo_grid(spec.dsp)
    a_piston = math.sqrt(cone.sd_m2 / math.pi)
    horn_bw_by_xo: dict[float, float | None] = {}
    piston_bw_by_xo: dict[float, float] = {}
    mismatch_flag = False
    polar_note = "polar: magnitude screens only (horn balloon vs ideal piston); no coherent claim"
    for xo in xo_points:
        piston_bw_by_xo[xo] = piston.first_minus6db_angle(xo, a_piston)
        horn_bw_by_xo[xo] = None
        if converted is not None and converted.response.observation_directions is not None:
            f_h, bw_h, _label = horn_balloon_beamwidth_screen(converted)
            if f_h.size >= 2:
                horn_bw_by_xo[xo] = float(np.interp(math.log(xo), np.log(f_h), bw_h))
        hb, pb = horn_bw_by_xo[xo], piston_bw_by_xo[xo]
        if hb is not None and np.isfinite(pb) and abs(hb - pb) > BW_MISMATCH_FLAG_DEG:
            mismatch_flag = True
    # The ideal piston having NO -6 dB crossing inside the front half-space at a crossover
    # frequency is the master-doc 'directivity handoff' warning case (a 12-inch-class piston
    # is commonly much wider than an 80x50 horn there). A NaN piston width flags the row.
    missing_piston = [xo for xo in xo_points
                      if not np.isfinite(piston_bw_by_xo.get(xo, float("nan")))]
    if missing_piston:
        mismatch_flag = True
        polar_note += (
            "; ideal piston has no -6 dB crossing in the front half-space at xo="
            + ", ".join(f"{xo:g} Hz" for xo in missing_piston)
            + " — woofer directivity at the handoff is far wider than the horn; screening "
            "flags it (not a final system verdict)")

    rows: list[dict] = []
    for idx, point in enumerate(boxes):
        lf = bass_reference.lf_report_row(point, cone)
        fit = _feasibility_row(point, driver.geometry_mm)
        f3_ok = (f3_target is None) or (np.isfinite(lf["f3_hz"]) and lf["f3_hz"] <= f3_target)
        # LF gate: the spec's own F3 target. The bassbox margin columns (112 dB @ 40 Hz /
        # 118 dB 63-120 Hz) are the MEH mini-bass conventions carried for context only --
        # they are NOT gates for this home hi-fi pilot and never drive the axis status.
        lf_axis = "PASS" if f3_ok else "FAIL"
        feasibility = {
            "bassbox_feasible": bool(point.fits.get("feasible", True)),
            "rules_pass": fit["passed"],
            "rules_skips": fit["skips"],
            "f3_gate": bool(f3_ok),
            "horn_asset_declared": asset is not None,
        }
        xp = "PASS" if all([feasibility["bassbox_feasible"], feasibility["rules_pass"]]) else "FAIL"
        xo_axis = "FAIL" if mismatch_flag else "SCREEN"
        rows.append({
            "row_id": f"box{idx:02d}",
            "candidate": {
                "driver": cone.name, "kind": point.kind,
                "net_volume_l": point.net_volume_l,
                "external_mm": (point.external_width_mm, point.external_height_mm,
                                point.external_depth_mm),
                "derived_tuning_hz": point.derived_tuning_hz,
                "port_area_cm2": point.port_throat_area_cm2,
                "xo_points_hz": xo_points,
            },
            "sort_key": [0 if xp == "PASS" else 1, 0 if lf_axis == "PASS" else 1,
                         point.net_volume_l],
            "numeric_axes": {
                "net_volume_l": {"value": point.net_volume_l, "direction": "-"},
                "f3_hz": {"value": lf["f3_hz"], "direction": "+",
                          "nan_ok": True},
                "margin_40hz_db": {"value": lf["margin_40hz_db"], "direction": "+"},
                "margin_63_120hz_db": {"value": lf["margin_63_120hz_db"], "direction": "+"},
                "spl_max_40hz_db": {"value": lf["spl_max_40hz_db"], "direction": "+"},
            },
            "feasibility": feasibility,
            "feasibility_reasons": fit["reasons"],
            "lf_row": lf,
            "crossover_screen": {
                "horn_bw_deg": horn_bw_by_xo,
                "piston_bw_deg": piston_bw_by_xo,
                "mismatch_flag": mismatch_flag,
                "note": polar_note,
                "bw_mismatch_flag_deg": BW_MISMATCH_FLAG_DEG,
            },
            "dsp": {"crossover_types": list(spec.dsp.crossover_types),
                    "gain_db": {"horn": 0.0, "woofer": 0.0}, "relative_delay_ms": 0.0},
            "axes": {
                "feasible_construction": xp,
                "lf_headroom": lf_axis,
                "crossover_physics": xo_axis,
                "angular_field": "SCREEN",
            },
            "feasible_construction": xp,      # renderer-facing aliases (score.render_report)
            "lf_headroom": lf_axis,
            "crossover_physics": xo_axis,
            "angular_field": "SCREEN",
            "data_quality": {"lf": "SCREEN_MAGNITUDE", "polar": "SCREEN_MAGNITUDE/SCREEN_COMPLEX_APPROX"},
            "data_support": {
                "lf": "SCREEN_MAGNITUDE (lumped small-signal, free half-space)",
                "polar": ("SCREEN_COMPLEX_APPROX horn balloon (converted stored accel, "
                          "approximate) + ideal piston woofer"),
                "coherent": None,
            },
            "claims": {
                "allowed": ["lf_screening", "noncoherent_polar_screen", "box_feasibility"],
                "refused": ["coherent_sum", "delay_optimization", "absolute_pa_per_volt",
                            "installed_directivity", "system_score"],
            },
            "ids": {
                "system_score_id": C.system_score_id({
                    "candidate": point.net_volume_l, "driver": stem,
                    "objective_version": C.SYSTEM_OBJECTIVE_VERSION}),
            },
        })

    report = score.render_report(rows)
    study_hash = C.system_study_id({
        "experiment_id": spec.experiment_id, "mode": spec.mode,
        "asset_id": None if asset is None else asset.asset_id, "driver": stem,
        "n_boxes": len(boxes), "limit_boxes": limit_boxes,
        "pools": {"feasible_boxes": "bass_reference grids"},
        "seed": "deterministic-no-rng",
    })
    meta = {
        "spec_hash": C.system_study_id(asdict_safe(spec)),
        "study_id": study_hash,
        "system_objective_version": C.SYSTEM_OBJECTIVE_VERSION,
        "fidelity_cap": "screen_only",
        "gpu_or_solves_used": False,
    }

    result = PilotResult(spec_hash=study_hash, asset=asset, converted=converted,
                         driver=driver, boxes=boxes, report=report, rows=tuple(rows),
                         meta=meta)
    if out_dir is not None:
        case = provenance.new_case_dir(spec.experiment_id, store_root=out_dir, tag="pilot")
        provenance.write_manifest(case, result.to_manifest_payload())
        result.meta["case_dir"] = str(case)
    return result


def asdict_safe(spec: C.SystemSpecV1) -> dict[str, Any]:
    import dataclasses

    return dataclasses.asdict(spec)


def _unused(x: Any) -> None:  # keep typing.Any import used on module level for annotations
    return None
