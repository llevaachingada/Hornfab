"""P7 crossover preview — per-channel filtered curves only, never a system sum.

The two channel references differ (woofer Pa per 2.83 V, horn Pa per 1 m/s) and the owner has
not answered decision 3 (calibration policy, risk R1).  This module may therefore apply the
validated analog-prototype DSP filter bank to each channel **on its own axis**, report the
``validate_dsp_point`` verdict and the locked sum panel, and nothing else.  It never imports or
calls :mod:`hornlab_search.system.combine`: no ``p_total``, no summed or combined field exists in
its payload (senior review 2026-11-20 §4 step 13; handoff §5.9).

The default DSP point comes from the committed example spec's own ranges, not a JS constant:
the first allowed crossover type, the midpoint of its XO range, 0 dB channel gains, 0 ms relative
delay, +1 woofer polarity and no PEQ bands.  A caller may pass a ``point`` overlay; the server
validates it against the same spec ranges before assembling any filter.
"""
from __future__ import annotations

import dataclasses
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import yaml

from hornlab_search.system import contracts as C
from hornlab_search.system import dsp as DSP

from . import data_hw as HW

DEFAULT_SPEC_REL = Path("examples/systems/two_way_80x50_700_research.yaml")
DEFAULT_PROBE = "observation:probe:on_axis_2m"
LOCKED_REASON = (
    "Summing needs a channel calibration policy (owner decision 3, risk R1). "
    "Woofer: Pa per 2.83 V. Horn: Pa per 1 m/s.")
CAPTIONS = (
    "Analog prototype filters, not a digital (biquad) implementation.",
    "An electrical LR4 is not an acoustic LR4.",
)
_POINT_KEYS = {"crossover_type", "xo_hz", "gain_db_woofer", "gain_db_horn",
               "relative_delay_ms", "polarity_woofer", "peq_bands_woofer"}


def _spec(root: str | Path) -> C.SystemSpecV1:
    path = Path(root) / DEFAULT_SPEC_REL
    if not path.is_file():
        # A GUI rooted at a test/temp tree still uses the committed example spec (never a JS or
        # Python constant, never an invented default).
        path = Path(__file__).resolve().parents[2] / DEFAULT_SPEC_REL
    if not path.is_file():
        raise FileNotFoundError(f"committed example spec not found: {DEFAULT_SPEC_REL.as_posix()}")
    return C.parse_system_spec_dict(yaml.safe_load(path.read_text(encoding="utf-8")) or {})


def _default_point(ranges: C.DspRanges) -> C.DspPoint:
    lo, hi = (float(ranges.xo_hz_range[0]), float(ranges.xo_hz_range[1]))
    return C.DspPoint(
        crossover_type=str(ranges.crossover_types[0]),
        xo_hz=round((lo + hi) / 2.0, 6),
        gain_db_woofer=0.0, gain_db_horn=0.0, relative_delay_ms=0.0,
        polarity_woofer=1.0, peq_bands_woofer=(),
    )


def _point(payload: Mapping[str, Any] | None, ranges: C.DspRanges) -> C.DspPoint:
    """The default point with an optional validated overlay (unknown keys refused)."""
    base = _default_point(ranges)
    raw = (payload or {}).get("point") if isinstance(payload, Mapping) else None
    if raw is None:
        return base
    if not isinstance(raw, Mapping):
        raise ValueError("point must be an object")
    unknown = sorted(set(raw) - _POINT_KEYS)
    if unknown:
        raise ValueError(f"unknown point key(s): {unknown}")
    try:
        peq = tuple((float(fc), float(gain), float(q))
                    for fc, gain, q in (raw.get("peq_bands_woofer")
                                        or base.peq_bands_woofer))
        return dataclasses.replace(
            base,
            crossover_type=str(raw.get("crossover_type") or base.crossover_type),
            xo_hz=float(raw.get("xo_hz", base.xo_hz)),
            gain_db_woofer=float(raw.get("gain_db_woofer", base.gain_db_woofer)),
            gain_db_horn=float(raw.get("gain_db_horn", base.gain_db_horn)),
            relative_delay_ms=float(raw.get("relative_delay_ms", base.relative_delay_ms)),
            polarity_woofer=float(raw.get("polarity_woofer", base.polarity_woofer)),
            peq_bands_woofer=peq,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"point is not numeric: {exc}") from None


def _db(v: float) -> float | None:
    v = float(v)
    return round(20.0 * math.log10(v / 20e-6), 3) if v > 0.0 and math.isfinite(v) else None


def _locked() -> dict[str, Any]:
    return {"panel": "system sum", "locked": True, "decision": 3, "risk": "R1",
            "reason": LOCKED_REASON}


def hw_dsp_preview(root: str | Path, store: str | Path, key: str,
                   payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Per-channel filtered response for one solved case, plus the locked-sum verdicts.

    ``ok`` is false (and ``channels`` empty) when the DSP point is outside the committed spec's
    ranges; the verdict carries the parser's own message.  There is no summed field, ever.
    """
    out: dict[str, Any] = {"case": key, "channels": [], "frequencies_hz": [],
                           "locked": _locked(), "captions": list(CAPTIONS), "ok": False}
    try:
        spec = _spec(root)
        point = _point(payload, spec.dsp)
    except (FileNotFoundError, C.SchemaError, ValueError) as exc:
        out["verdicts"] = [{"check": "point", "ok": False, "detail": str(exc)}]
        return out
    out["dsp"] = {
        "point": _jsonable(dataclasses.asdict(point)),
        "ranges": _jsonable(dataclasses.asdict(spec.dsp)),
        "source": DEFAULT_SPEC_REL.as_posix(),
    }
    try:
        case = HW._resolve_case(Path(store), key)
        run = HW._run_manifest(case)
        if run is None or str(run.get("status")) != "complete":
            raise FileNotFoundError(f"{key} has no solved run")
        DSP.validate_dsp_point(point, spec.dsp)
        verdicts = [{"check": "validate_dsp_point", "ok": True,
                     "detail": "DspPoint accepted against the committed spec ranges."}]
    except (FileNotFoundError, C.SchemaError, ValueError) as exc:
        out["verdicts"] = [{"check": "validate_dsp_point", "ok": False, "detail": str(exc)}]
        return out
    out["verdicts"] = verdicts

    from hornlab_search.system.boundarylab import bl_results as R

    res = R.read_bl_headless_result(case / "run")
    domain = DEFAULT_PROBE if DEFAULT_PROBE in res.observation_sets else None
    if domain is None:
        domain = next((d for d in res.domain_ids()
                       if res.observation_sets[d].kind == "point_probe"), None)
    if domain is None:
        out["verdicts"] = [{"check": "probe", "ok": False,
                            "detail": "the run records no point probe"}]
        return out
    obs = res.observation_sets[domain]
    bases = res.per_excitation_bases(domain)
    conv = {c.excitation_id: c for c in res.conversion}
    freqs = np.asarray(res.frequencies_hz, dtype=np.float64)
    try:
        filters = DSP.filter_bank(point, freqs)
    except C.SchemaError as exc:
        out["verdicts"] = [{"check": "filter_bank", "ok": False, "detail": str(exc)}]
        return out

    channels = []
    for ex, p in bases.items():
        c = conv.get(ex)
        per_input = None if c is None else c.to_per_input
        if per_input == "V_rms":
            channel, h = "woofer", filters["woofer"]
        elif per_input == "normal_velocity_mps":
            channel, h = "horn", filters["horn"]
        else:
            continue
        filtered = np.asarray(p[:, 0], dtype=np.complex128) * np.asarray(h, dtype=np.complex128)
        channels.append({
            "id": ex, "channel": channel, "per_input": per_input,
            "reference": None if c is None else c.from_per_input,
            "spl_db": [_db(v) for v in np.abs(filtered)],
            "phase_deg": [float(np.degrees(np.angle(v))) for v in filtered],
            "phase_unwrapped_deg": [float(v) for v in
                                    np.degrees(np.unwrap(np.angle(filtered)))],
        })
    out.update({
        "ok": bool(channels),
        "channels": channels,
        "frequencies_hz": [float(f) for f in freqs],
        "probe_domain": domain,
        "probe_id": (obs.metadata or {}).get("probe_id") or domain,
        "distance_m": obs.distance_m,
        "point_index": 0,
    })
    if not channels:
        out["verdicts"] = [{"check": "channels", "ok": False,
                            "detail": "no woofer/horn excitation found in the run"}]
    return out


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value
