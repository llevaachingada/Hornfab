"""LF bass reference for the system package: a thin wrapper over ``tools/bassbox.py``.

There is **no second lumped model here**. ``tools/bassbox.py`` is loaded by path (the same
pattern as ``tests/test_bassbox.py::_load_tool``) and every number is produced by its
already-fixed functions: :class:`~bassbox.Box`, :func:`~bassbox.evaluate`,
:func:`~bassbox.max_spl`, :func:`~bassbox.port_effective_length` and
:func:`~bassbox.box_dimensions_mm`. The non-unit-voltage ``z_in`` bug is fixed there (SYS-01);
this module relies on the fixed behaviour.

What this later adds is the *feasible-enclosure search contract*:

* :func:`feasible_boxes` sweeps ``net_volume_l x tuning_hz x port throat area`` and derives the
  port **neck length** from :func:`bassbox.port_effective_length`. Fb is an outcome of
  (Vb, requested fb, area) and is recorded on the contract as
  ``derived_tuning_hz`` / ``derived_effective_port_length_m``. A candidate is rejected with the
  same geometric rules ``bassbox`` uses (neck shorter than 20 mm, neck longer than the cabinet's
  usable internal depth, or the cabinet too shallow behind the driver).
* :func:`box_point_to_bassbox` turns one :class:`contracts.BoxPoint` back into a
  :class:`bassbox.Box` — no hidden state.
* :func:`lf_report_row` returns one ``REPORT_AXES`` ``"lf_headroom"`` row using the box tool's
  own conventions (1 m, half space, 2.83 V datasheet reference; targets 112 dB @ 40 Hz and
  118 dB over 63-120 Hz) and its own limiting-factor names (``"xmax"``, ``"p_aes"``, ``"port"``).

Port type at this tier
----------------------
``round_flared`` and ``round_straight`` are treated as an **area-equivalent round port** with
``bassbox``'s default ``n_end`` (two radiating mouths for a free-standing box). The passive
``port_nfr`` field is carried on :class:`contracts.BoxPoint` but **ignored** at this tier; every
row carries ``nfr_ignored_at_lf_tier: True``.

This is an LF **screening** module: it models no port turbulence/noise, no cone breakup and no
installed (baffle/horn/room) loading beyond the free-standing half-space box model.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np

from hornlab_search.meh.drivers import ConeDriver
from hornlab_search.system.contracts import BoxPoint, VentedBoxRanges

__all__ = [
    "bassbox",
    "feasible_boxes",
    "box_point_to_bassbox",
    "evaluate",
    "port_neck_length_mm",
    "lf_report_row",
    "LF_FREQS_HZ",
]

REPO_ROOT = Path(__file__).resolve().parents[2]
BASSBOX_PATH = REPO_ROOT / "tools" / "bassbox.py"

#: Mirrors ``tools/bassbox.py``'s internal 241-point 20-200 Hz logarithmic grid. This is a
#: sampling grid, not a model; the acoustics still come from ``bassbox.evaluate``.
LF_FREQS_HZ = np.geomspace(20.0, 200.0, 241)

#: Deterministic screening grid sizes (endpoints included). Small enough for CPU-only sweeps.
_N_VOLUME = 7
_N_TUNING = 7
_N_AREA = 5

#: Same short-neck screen ``bassbox.design_vented`` applies; shorter necks are not buildable.
_MIN_PORT_NECK_MM = 20.0
#: Same rear clearance ``bassbox._assess`` applies: internal depth >= driver depth + 20 mm.
_REAR_CLEARANCE_MM = 20.0


def _load_bassbox() -> ModuleType:
    """Import ``tools/bassbox.py`` by path (``tools/`` is a scripts dir, not a package)."""
    name = "hornlab_system_bassbox"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, BASSBOX_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - impossible when the file exists
        raise ImportError(f"cannot load tools/bassbox.py at {BASSBOX_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bassbox = _load_bassbox()


# --------------------------------------------------------------------------- port geometry

def _grid(lo: float, hi: float, n: int) -> np.ndarray:
    if not (math.isfinite(lo) and math.isfinite(hi)):
        raise ValueError(f"range must be finite, got [{lo!r}, {hi!r}]")
    if lo > hi:
        raise ValueError(f"range must be lo <= hi, got [{lo!r}, {hi!r}]")
    return np.linspace(float(lo), float(hi), n) if lo != hi else np.array([float(lo)])


def port_neck_length_mm(point: BoxPoint, *, n_end: float | None = None) -> float:
    """Physical port **neck** length [mm] implied by ``point``'s derived effective length.

    ``bassbox.Box.l_eff_m = neck + n_end * 0.85 * r_eq``; inverting with the same ``n_end``
    (default ``bassbox.N_END``) recovers the neck. Raises ``ValueError`` when the contract point
    has no derived effective length.
    """
    if point.derived_effective_port_length_m is None:
        raise ValueError(
            f"box point has no derived_effective_port_length_m; cannot recover neck length")
    if not (math.isfinite(point.port_throat_area_cm2) and point.port_throat_area_cm2 > 0.0):
        raise ValueError("port throat area must be finite and > 0")
    s_port_m2 = point.port_throat_area_cm2 * 1e-4
    r_eq_m = math.sqrt(s_port_m2 / math.pi)
    end = float(bassbox.N_END) if n_end is None else float(n_end)
    return (float(point.derived_effective_port_length_m) - end * 0.85 * r_eq_m) * 1e3


def box_point_to_bassbox(
    point: BoxPoint,
    *,
    q_leak: float | None = None,
    q_port: float | None = None,
    n_end: float | None = None,
) -> Any:
    """Rebuild the exact :class:`bassbox.Box` a contract :class:`BoxPoint` describes.

    The optional ``q_leak``/``q_port``/``n_end`` overrides exist for the lossless textbook
    alignment test; production callers leave them at ``bassbox``'s defaults so a round-trip
    reproduces the box that produced the point.
    """
    kwargs: dict[str, float] = {}
    if q_leak is not None:
        kwargs["q_leak"] = float(q_leak)
    if q_port is not None:
        kwargs["q_port"] = float(q_port)
    if n_end is not None:
        kwargs["n_end"] = float(n_end)

    vb_l = float(point.net_volume_l)
    if point.kind == "sealed":
        return bassbox.Box("sealed", vb_l, **kwargs)

    fb = point.derived_tuning_hz
    if fb is None:
        fb = point.requested_tuning_hz
    neck_mm = port_neck_length_mm(point, n_end=n_end)
    if not (math.isfinite(neck_mm) and neck_mm > 0.0):
        raise ValueError(
            f"derived port neck length must be > 0 mm, got {neck_mm!r}; "
            "check derived_effective_port_length_m / area")
    return bassbox.Box(
        "vented",
        vb_l,
        float(fb),
        float(point.port_throat_area_cm2),
        float(neck_mm),
        **kwargs,
    )


# --------------------------------------------------------------------------- feasibility

def _fits(cone: ConeDriver, box: Any) -> dict[str, Any]:
    """Feasibility/headroom flags for one buildable box (all numbers from ``bassbox``)."""
    # AES voltage ceiling = the p_aes_W / Re limit bassbox.max_spl uses.
    e_p = math.sqrt(cone.p_aes_w * cone.re_ohm)
    st40 = bassbox.evaluate([40.0], cone, box, volts=e_p)
    st63 = bassbox.evaluate([63.0], cone, box, volts=e_p)
    x40 = float(st40.x_peak_mm[0])
    if x40 > 0.0:
        excursion_margin_db = 20.0 * math.log10(cone.xmax_mm / x40)
    else:  # pragma: no cover - only a zero-drive box would hit this
        excursion_margin_db = float("inf")
    v40 = float(st40.port_v_peak_mps[0])
    v63 = float(st63.port_v_peak_mps[0])
    limit = float(bassbox.PORT_AIR_MPS_MAX)
    return {
        "excursion_margin_db": float(excursion_margin_db),
        "port_velocity_mps_40hz": v40,
        "port_velocity_mps_63hz": v63,
        "port_velocity_limit_mps": limit,
        "port_velocity_fits": bool(v40 <= limit and v63 <= limit),
        "neck_fits": True,
        "driver_rear_depth_fits": True,
        "nfr_ignored_at_lf_tier": True,
    }


def feasible_boxes(cone: ConeDriver, ranges: VentedBoxRanges) -> list[BoxPoint]:
    """Deterministic feasible-vented-box grid for one driver.

    Sweeps ``net_volume_l_range x tuning_hz_range x port_throat_area_cm2_range``, derives the port
    neck from :func:`bassbox.port_effective_length` and rejects candidates with
    :func:`bassbox.box_dimensions_mm` exactly as the box tool does. A non-positive Vb is
    infeasible *before any score* (SYS-10) and simply produces no point.

    Returns contract :class:`BoxPoint` objects with the derived length/tuning recorded and a
    ``fits`` mapping (excursion headroom, port velocity at 40/63 Hz, neck and rear-depth flags).
    Sealed ranges are refused: a sealed box has no port to derive.
    """
    if ranges.kind != "vented":
        raise ValueError(
            "feasible_boxes: only vented ranges; a sealed search has no port to derive "
            "(construct bassbox.Box('sealed', vb) directly)")
    if ranges.port_type == "slot":
        raise ValueError(
            "feasible_boxes: slot-port geometry is not modelled at the LF tier; use "
            "'round_flared' or 'round_straight' (both are treated as an area-equivalent "
            "round port)")
    ranges.validate()
    if cone.depth_mm is None:  # C8 requires depth_mm, so this only defends a hand-built object
        raise ValueError("cone.depth_mm is required to check rear clearance")
    driver_depth_mm = float(cone.depth_mm)

    volumes = _grid(*ranges.net_volume_l_range, _N_VOLUME)
    tunings = _grid(*ranges.tuning_hz_range, _N_TUNING)
    areas = _grid(*ranges.port_throat_area_cm2_range, _N_AREA)

    points: list[BoxPoint] = []
    for vb in volumes:
        if not (math.isfinite(float(vb)) and float(vb) > 0.0):
            continue  # SYS-10: Vb = 0/NaN is infeasible before any score
        for fb in tunings:
            if not (math.isfinite(float(fb)) and float(fb) > 0.0):
                continue
            for area in areas:
                if not (math.isfinite(float(area)) and float(area) > 0.0):
                    continue
                s_port_m2 = float(area) * 1e-4
                l_eff_m = bassbox.port_effective_length(float(vb) * 1e-3, float(fb), s_port_m2)
                r_eq_m = math.sqrt(s_port_m2 / math.pi)
                neck_mm = (l_eff_m - bassbox.N_END * 0.85 * r_eq_m) * 1e3
                if neck_mm < _MIN_PORT_NECK_MM:
                    continue
                box = bassbox.Box("vented", float(vb), float(fb), float(area), float(neck_mm))
                cabinet = bassbox.box_dimensions_mm(cone, box, wall_mm=ranges.wall_mm)
                if neck_mm > cabinet.max_port_length_mm:
                    continue
                if cabinet.d_int_mm < driver_depth_mm + _REAR_CLEARANCE_MM:
                    continue

                points.append(BoxPoint(
                    kind="vented",
                    external_width_mm=float(cabinet.ext_mm[0]),
                    external_height_mm=float(cabinet.ext_mm[1]),
                    external_depth_mm=float(cabinet.ext_mm[2]),
                    net_volume_l=float(vb),
                    wall_mm=float(ranges.wall_mm),
                    port_type=str(ranges.port_type),
                    port_throat_area_cm2=float(area),
                    # Carried for the contract but ignored at this tier (see module docstring).
                    port_nfr=float(ranges.port_nfr_range[0]),
                    requested_tuning_hz=float(fb),
                    derived_effective_port_length_m=float(l_eff_m),
                    derived_tuning_hz=float(box.tuning_hz),
                    fits=_fits(cone, box),
                ))
    return points


# --------------------------------------------------------------------------- evaluation / report

def evaluate(
    f: Any,
    cone: ConeDriver,
    point: BoxPoint,
    volts: float = 1.0,
    *,
    q_leak: float | None = None,
    q_port: float | None = None,
    n_end: float | None = None,
) -> Any:
    """``bassbox.evaluate`` for a contract :class:`BoxPoint` (identical Box, identical result)."""
    box = box_point_to_bassbox(point, q_leak=q_leak, q_port=q_port, n_end=n_end)
    return bassbox.evaluate(f, cone, box, volts=volts)


def _spl_at_db(spl: np.ndarray, f0: float) -> float:
    return float(bassbox._spl_at(LF_FREQS_HZ, spl, f0))


def lf_report_row(point: BoxPoint, cone: ConeDriver) -> dict[str, Any]:
    """One ``REPORT_AXES`` ``"lf_headroom"`` row for a feasible box.

    Conventions are the box tool's own: 1 m, half space, ``bassbox``'s 2.83 V datasheet
    reference, its 112 dB @ 40 Hz / 118 dB over 63-120 Hz targets, and its limiting-factor names
    (``"xmax"``, ``"p_aes"``, ``"port"``). ``f3_hz`` is the box tool's own -3 dB estimate.
    """
    box = box_point_to_bassbox(point)
    f = LF_FREQS_HZ
    state = bassbox.evaluate(f, cone, box, volts=1.0)
    lim = bassbox.max_spl(f, cone, box)
    spl_max = lim["spl_max_db"]
    band = bassbox.BAND_HZ
    band_mask = (f >= band[0]) & (f <= band[1])

    margin_40 = _spl_at_db(spl_max, 40.0) - float(bassbox.TARGET_40_DB)
    margin_band = (float(np.min(spl_max[band_mask])) - float(bassbox.TARGET_BAND_DB))
    limiting_40 = str(lim["limiting"][int(np.argmin(np.abs(f - 40.0)))])
    limiting_band = str(lim["limiting"][band_mask][int(np.argmin(spl_max[band_mask]))])
    f3_hz = float(bassbox._f3_hz(f, state.spl_db))

    e_p = math.sqrt(cone.p_aes_w * cone.re_ohm)
    st40 = bassbox.evaluate([40.0], cone, box, volts=e_p)
    st63 = bassbox.evaluate([63.0], cone, box, volts=e_p)

    return {
        "axis": "lf_headroom",
        "driver": cone.name,
        "kind": point.kind,
        "fidelity": "SCREEN_MAGNITUDE",
        "net_volume_l": float(point.net_volume_l),
        "tuning_hz": float(point.derived_tuning_hz
                           if point.derived_tuning_hz is not None
                           else point.requested_tuning_hz),
        "port_throat_area_cm2": float(point.port_throat_area_cm2),
        "f3_hz": f3_hz,
        "spl_max_40hz_db": _spl_at_db(spl_max, 40.0),
        "spl_max_63_120hz_min_db": float(np.min(spl_max[band_mask])),
        "margin_40hz_db": float(margin_40),
        "margin_63_120hz_db": float(margin_band),
        "limiting_40hz": limiting_40,
        "limiting_63_120hz": limiting_band,
        "port_velocity_mps_40hz": float(st40.port_v_peak_mps[0]),
        "port_velocity_mps_63hz": float(st63.port_v_peak_mps[0]),
        "spl_reference": "1 m half space (tools/bassbox.py convention)",
        "nfr_ignored_at_lf_tier": True,
    }
